
import contextlib
import time
from copy import deepcopy
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war import cw_telemetry
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_obs_core import (
    HP_MAX,
    SHOP_SCREEN_NAME,
    shop_card_click_points,
)
from sr_od.application.currency_war.cw_observation import (
    area_center,
    new_bench_slots,
    read_game_state,
    read_gold,
    read_shop_cards,
)
from sr_od.application.currency_war.cw_state import (
    BenchChar,
    BuyCard,
    DeployMove,
    LevelUp,
    RefreshShop,
    SellBench,
    mutate_bench_deployed,
)
from sr_od.application.currency_war.cw_strategy import CurrencyWarMatch
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


def _form_progress(comp, state) -> float:
    """fp 遥测helper(review 要求:fp 轨迹可观测;comp None 时不调)。"""
    from sr_od.application.currency_war.cw_comps import form_progress
    return form_progress(comp, state)


def _tracked_bench_chars(names: list[str]) -> list[BenchChar]:
    """tracked_bench(buy OCR 的角色名)→ BenchChar 列表(跨轮 seed state.bench)。

    buy 时 ``read_shop_cards`` OCR 的规范名(T#92 验证可靠)持久化,跨轮 seed bench →
    plan / char_quality / comp core check 知 bot 自有角色。**SIFT 立绘识别现已可行**(plaza
    官方立绘库,D-8/D-10/D-12 验证)—— deploy op 后用 SIFT 真实身份纠 tracking 漂(deploy_bench
    ``_reconcile_tracking``,D-12);buy 期 bench 仍用 OCR 名跟踪(buy 改变 bench,SIFT 单帧跟不上)。
    """
    from sr_od.application.currency_war.cw_chars import get_char
    out: list[BenchChar] = []
    for i, n in enumerate(names):
        if not n:
            continue
        ch = get_char(n)
        # faction 语义(2026-08-17 清理):'?' = 未知(名不在注册表);'' = 已知无阵营(白厄「救世主」类,
        # 复制效果不计阵营人数)。旧版两者混填 '?',日志无法区分"识别失败"与"本来就无阵营"。
        out.append(BenchChar(
            slot=i, char_id=n,
            faction=(ch.factions[0] if (ch is not None and ch.factions)
                     else ('' if ch is not None else '?')),
        ))
    return out


class BuyShopCards(SrOperation):
    """备战阶段:开商店 → ``plan`` 驱动买牌/升等级 → 关商店。

    接战术层 ``cw_plan.plan``(阶段键控 eval + 硬门贪心 + 蒙特卡洛 D牌):OCR 读真实
    ``gold/level/round/plane/board/shop`` → ``plan`` → 执行返回的 ``BuyCard``/``LevelUp``。

    v1 接线范围(2026-08-03,见 ``docs/develop/currency_war/strategy/05_observation.md``):
    - 执行 ``BuyCard``(点牌)/ ``LevelUp``(点「购买经验」)/ ``RefreshShop``(点「刷新」,两阶段 plan)。
    - **跳过** ``DeployMove`` —— deploy 走 ``DeployBench``(deploy-all,游戏按等级封顶;
      避开 plan 的 bench_idx→物理槽映射复杂度)。
    - **D牌两阶段(r6 F8)**:plan emit RefreshShop 后,simulate 不换牌 → 其后的 BuyCard 是旧 shop
      失效决策。故每轮执行**至首个 RefreshShop(含)**,刷新后重 OCR shop + 重 plan(MAX_REFRESH 硬墙)。
    - **跳过** ``SellBench`` —— v1 不读 bench 身份;「备战席已满」由本 op 前置处理(位置式)覆盖。

    牌位点击中心从 screen_info ``商店牌-1..5`` 读(cw_observation.shop_card_click_points)。
    前置:已在「货币战争-备战」(商店未开)。买完关商店,交上层 deploy。
    """

    # 「购买经验」按钮(= 买经验升等级)screen_info area 名;中心运行时读(area_center)
    BUY_EXP_AREA: ClassVar[str] = '备战标识-购买经验'
    LEVEL_UP_FALLBACK: ClassVar[Point] = Point(296, 860)   # screen_info 缺失时兜底
    REFRESH_FALLBACK: ClassVar[Point] = Point(1592, 472)   # 「刷新」按钮兜底(screen_info 按钮-刷新)
    # D牌(刷新)硬上限:plan 的 _refresh_cap 是单次 plan 软上限;两阶段循环里再加硬墙防死循环
    MAX_REFRESH: ClassVar[int] = 4

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-商店买牌')

    @operation_node(name='商店买牌', is_start_node=True)
    def buy(self) -> OperationRoundResult:
        screen = self.last_screenshot
        _bought_names: list[str] = []
        # 前置:备战席已满 → 升等级(+卖前几个 bench)清警告解锁购买(位置式,不需身份)
        if self._handle_bench_full(screen):
            return self.round_success('备战席已满,升等级(+卖角色)清警告')

        # 回合事件叠层守卫(2026-08-04 plane2 实测卡死):投资策略/投资环境/补给/遭遇/巨星等
        # 事件可能在备战中途叠上来 → 此时非备战屏(无「购买经验」锚点)。本 op 处理不了 →
        # round_fail 快速退出(不 retry),让上层 BattlePrepCycle 中止、主循环 loop 接手处理事件
        # (loop 的 0/0b/4 分支)。否则 round_retry 在非商店屏死循环 → 对局卡死。
        # 备战锚点「购买经验」= 底部买经验按钮,shop 开/关均可见(本 op 开 shop 后仍点它升等级)。
        if not self.round_by_find_area(screen, '货币战争-备战', '备战标识-购买经验').is_success:
            return self.round_fail('非备战屏(回合事件叠层?),交主循环处理')
        # 事件 overlay 兜底(2026-08-04):投资策略/环境/补给等 overlay 叠在备战上,「购买经验」会
        # 透出(底部左下未遮)→ 上面 guard 误放行 → overlay 遮商店 → "找不到商店"死循环。
        # 主循环已事件前置检测(正常不到这),这是 BuyShopCards 自身的兜底:overlay 在 → fail 交主循环。
        # 事件 overlay 兜底:有 screen_info 标题区的走区域识别(结构性不误匹配,T#103);
        # 无区的 overlay(补给/遭遇/选择伙伴/确认选择 —— screen_info 待建 text area)暂留全屏 OCR + 高 lcs。
        for _scr, _area, _evt in (
            ('货币战争-投资策略', '标识-请选择投资策略', '投资策略'),
            ('货币战争-投资环境', '标识-投资环境', '投资环境'),
            ('货币战争-补给', '标识-补给阶段', '补给阶段'),   # 2026-08-13:补给建档后从全屏 OCR 移到 area(位置判 [893,120,1027,230])——治备战「返回补给阶段」按钮文本假阳 → 死循环
        ):
            if self.round_by_find_area(screen, _scr, _area).is_success:
                return self.round_fail(f'备战被事件 overlay({_evt})叠,交主循环处理')
        for _evt in ('遭遇其一', '选择伙伴', '确认选择'):  # TODO(T#103) 待建 area
            if self.round_by_ocr(screen, _evt, lcs_percent=0.8).is_success:
                return self.round_fail(f'备战被事件 overlay({_evt})叠,交主循环处理')

        # HP 只在 shop **关闭**时显示在右上角(shop 开启时该位置被遮/空 → read_hp 返 100,
        # telemetry plan-time 全 100 即此;2026-08-03 2 图诊断)。gold 相反(shop 开才显示右下)。
        # 故:若 shop 开着先「收起」关 → 关闭帧读 hp 真值 → 再开 shop 读 gold/shop/board。
        if self.round_by_find_area(screen, SHOP_SCREEN_NAME, '按钮-收起').is_success:
            self.round_by_find_and_click_area(screen, SHOP_SCREEN_NAME, '按钮-收起', success_wait=1.0)
            # r335(批次3)+r347(旧路径删除):gate 无条件化——
            # 超时=fail-closed retry(收起动画未稳,重试整轮);
            # 异常=放行(离线契约,原 _legacy_poll 轮询已删,
            # 对拍验证过新路径)。r346(review M1):接收 gate
            # 稳定帧而非布尔后重截(丢弃帧=OCR 缓存作废+HP 读
            # 在未验证帧)。
            from sr_od.application.currency_war.cw_observation_gate import (
                PROFILE_CLOSED,
                wait_stable_frame,
            )
            log.info('[cw][gate] path=new(shop 买前收起)')
            # ADR-0264 终裁加速器②:收起动画=操作段(2s 基线重置点)
            try:
                _gf = wait_stable_frame(
                    self, profile=PROFILE_CLOSED, segment='op_settle')
                if _gf is not None:
                    screen = _gf
                else:
                    return self.round_retry('收起后关态未稳定(gate 超时)',
                                            wait=1)
            except Exception:   # noqa: BLE001  离线契约:放行
                pass
        # r317(ADR-0213 批次2):read_hp 裸调用迁 read_hp_opt
        # (miss→None 显式化);None 走结算真值链(⚠ r322 修:
        # **带新鲜度门**——陈旧 last_hp 不当真值,防「陈 hp
        # 冻结毒化」从 miss 路径回流,与下方 L249 段同判据);
        # 无新鲜结算值→100 兜底+log。
        # 旧「>=HP_MAX 重读 2 次」保留(None≠100 分流后,
        # 该循环只处理真满血误读,语义更纯)。
        from sr_od.application.currency_war.cw_observation import (
            read_hp_opt,
            read_phase_round,
        )
        match = self.ctx.cw_match   # r317:提前(None 兜底链要用)
        _hp_raw = read_hp_opt(self.ctx, screen)
        if _hp_raw is None:
            _pr = read_phase_round(self.ctx, screen)
            _now_t = ((_pr[0] - 1) * 9 + _pr[1]) if (_pr and _pr[0] and _pr[1]) else None
            _hp_t = getattr(match.session, 'last_hp_t', None) if match is not None else None
            _fresh = (_now_t is not None and _hp_t is not None
                      and _now_t - _hp_t == 1)
            _hp_raw = (match.session.last_hp
                       if (match is not None and _fresh
                           and getattr(match.session, 'last_hp', None)
                           is not None) else 100)
            log.info('[cw][shop] HP 区 miss→%s(fresh=%s 结算真值/兜底)',
                     _hp_raw, _fresh)
        hp_value = _hp_raw
        # round9 同款读对 29 —— 间歇时序,非持续)→ 重读 2 次取真值。防 maybe_pivot hp_safe 信号失效
        # (误判满血不保血 → 不必要失血死)。真满血重读仍 HP_MAX(无害);HP 区持续空(罕见)→ 维持 100 兜底。
        if hp_value >= HP_MAX:
            for _ in range(2):
                time.sleep(0.4)
                _v = read_hp_opt(self.ctx, self.screenshot())
                if _v is not None and _v < HP_MAX:
                    hp_value = _v
                    break

        # 开商店(gold/shop/board 须 shop 开才显示;HP 此时被遮但上面已读过)
        if not self.round_by_find_area(self.screenshot(), SHOP_SCREEN_NAME, '按钮-收起').is_success:
            if not self.round_by_find_and_click_area(self.screenshot(), '货币战争-备战', '按钮-商店', success_wait=1.5).is_success:
                return self.round_retry('找不到商店/收起按钮', wait=1)
            # r312(ADR-0213 批次1;开向站)+r347(旧路径删除):
            # 旧 sleep(0.5) 后即读=半开帧(开店动画 ~3s,终验 P1②);
            # gate 无条件化,异常=放行(离线契约)。
            from sr_od.application.currency_war.cw_observation_gate import (
                PROFILE_OPEN,
                wait_stable_frame,
            )
            log.info('[cw][gate] path=new(shop 开店)')
            # ADR-0264 终裁加速器②:开店动画=操作段(2s 基线重置点)
            with contextlib.suppress(Exception):   # 离线契约:放行
                wait_stable_frame(self, profile=PROFILE_OPEN,
                                  segment='op_settle')

        # 牌位/升级/刷新中心从 screen_info 读(缺失兜底)。target 由 strategy.update_target 管理(下方)。
        config = CurrencyWarConfig(self.ctx.current_instance_idx)
        click_pts = shop_card_click_points(self.ctx)
        level_btn = area_center(self.ctx, BuyShopCards.BUY_EXP_AREA) or BuyShopCards.LEVEL_UP_FALLBACK
        refresh_btn = area_center(self.ctx, '按钮-刷新', SHOP_SCREEN_NAME) or BuyShopCards.REFRESH_FALLBACK

        # 无强信号保持 —— 等价旧 _target_comp class-attr 逻辑,但状态进 session 跨回合持久)。用 shop 关闭帧
        # hp 覆盖的 state(M6 钉死行为等价:hp 真值 → maybe_pivot 的 hp_safe 信号正确触发,非 shop 开帧的假 100)。
        # (match 已在 HP 读段提前取——r317)
        # live round4 读 100 实际 58)→ 保血/maybe_pivot 信号失效。结算屏「小队生命值NN」可靠 → 用它
        # 给 prep state.hp(HP 结算→下回合 prep 不变)。round1 无结算 → None → 退 read_hp(round1 读对)。
        # ⚖️ r68 review 新鲜度门(单源 helper cw_strategy.gated_hp;director 环入口同门):
        # 结算 hp 只在「紧邻上一节点」才可覆盖 —— 低 conf 结算轮 last_hp 残留陈值,无条件覆盖 =
        # 陈 hp 冻结毒化每回合 prep(保血/转型永不触发,P1 boss 赢→P2 秒死 ×3 的观测链根因)。
        from sr_od.application.currency_war.cw_observation import read_phase_round
        from sr_od.application.currency_war.cw_strategy import gated_hp
        _pr = read_phase_round(self.ctx, screen)
        _now_t = ((_pr[0] - 1) * 9 + _pr[1]) if (_pr and _pr[0] and _pr[1]) else None
        _hp_t = getattr(match.session, 'last_hp_t', None) if match is not None else None
        _hp_fresh = (_now_t is not None and _hp_t is not None and _now_t - _hp_t == 1)
        if match is not None and match.session.last_hp is not None and _hp_fresh:
            # 观察冲突审计 #7(2026-08-16):「结算→下回合 prep 不变」是本文件自述契约 → prep 读与
            # 结算真值不等 = 双源分歧事件,留证(兼测 prep read_hp 毒化率与结算屏误读,双向有用);
            # 裁决仍采新(结算屏是权威源,契约本身允许 prep 读噪声)。
            if hp_value != match.session.last_hp and hp_value < HP_MAX:
                from sr_od.application.currency_war.cw_observe import obs_conflict
                obs_conflict('hp', match.session.last_hp, hp_value, None,
                             verdict='采新-结算真值覆盖(prep读≠结算,留证测毒化率)',
                             source='prep_read_hp_vs_settlement')
            log.info(f'[cw] hp 用结算屏真值 {match.session.last_hp}(prep read_hp={hp_value} 不可靠,覆盖)')
            hp_value = gated_hp(hp_value, match.session, _now_t)   # 单源门(此处恒取结算值;陈旧分支在 elif)
        elif match is not None and match.session.last_hp is not None:
            log.info('[cw] hp 结算值陈久跳过覆盖(last_hp=%s t=%s, now t=%s)→ 用 prep 现读 %s(防冻结毒化)',
                     match.session.last_hp, _hp_t, _now_t, hp_value)
        _tgt_state = read_game_state(self.ctx, self.screenshot())
        _tgt_state.hp = hp_value
        if match is None:
            # 防御:无对局态(独立 run_operation 调本 op)→ 临时 default match,不挂 ctx(局外不复用)
            from sr_od.application.currency_war.strategies.default_strategy import (
                DefaultCwStrategy,
            )
            _def = DefaultCwStrategy()
            match = CurrencyWarMatch(_def, _def.create_session(config))
        match.strategy.update_target(_tgt_state, match.session, config)

        total_buy = total_level = total_refresh = 0
        # 两阶段 plan(r6 F8):simulate(RefreshShop) 不换牌 → plan 在 RefreshShop 之后的 BuyCard
        # 是旧 shop 的失效决策。故每轮:plan → 执行至**首个 RefreshShop(含)** → 若刷新了则重 OCR + 重 plan。
        # 硬墙 MAX_REFRESH 防死循环(plan _refresh_cap 是单次软上限,每轮 plan 重置)。
        # _after_shot(同为 shop-OPEN)做 pixel-diff,差值才只反映 buy 带来的 bench 占位变化。旧代码用
        _buy_baseline = self.screenshot()
        for _ in range(BuyShopCards.MAX_REFRESH + 1):
            time.sleep(0.3)  # 等 board 面板 settle(买牌/shop 开 → panel 动画显示 tier 链"2/4/6/8"→ OCR 误读)
            # 光标 parking(审计 P0,2026-08-16):上轮 BuyCard/LevelUp/Refresh 点击后光标停在按钮上
            # (购买经验距等级区 18px/牌位=识别区本身)→ 污染本帧 read_game_state;park 后再读。
            self.park_cursor(after_wait=0.1)
            state = read_game_state(self.ctx, self.screenshot())
            state.hp = hp_value   # shop 开帧 hp 区空(read_game_state 给 100)→ 用 shop 关闭帧真值覆盖
            # r7 review P0-①:shop 开帧节点行被遮 node_type 恒 None(plan 路径 1700/1706 None 实证,
            # boss 判定死码)→ 拷 Director shop 关态真值(仿 hp_value 同法)。
            if match is not None and match.session.last_node_type:
                state.node_type = match.session.last_node_type
            # r73 review RC3 修(dual_track_phase 战术层接线断裂):update_target 写在
            # _tgt_state(每轮首对象),循环内 read_game_state 新建 state 默认 False →
            # ADR-0209 双轨买门/stash 放行/DP 攒息压制在实跑买牌路径**从未执行**
            # (遥测指纹:每轮首条 True、循环内全 False)。修:dual 态单一源挂 session
            # (cw_strategy),循环态每轮从 session 拷贝(仿 hp/node_type 同法)。
            state.dual_track_phase = getattr(match.session, 'dual_track_phase', False)
            if getattr(match.session, 'transition_framework', ''):
                state.focus_factions = getattr(match.session, 'focus_factions', set())
            # gold-robust:gold 数字 stylized,paddle OCR det 间歇漏(同帧读 3/0/空;实锤 click-test
            # 买牌成功 gold≥1 但 reader 读 0,见 process_log)→ 读 0 时重读几帧取首个 >0(deterministic 同帧
            # 重读无意义,故重截图)。不根治(stylized 漏读),但把「读 0 不买」概率降到「连读 0 才认 0」。
            # 观察冲突审计 #6(2026-08-16):救援结果留证 —— 救回(首读假 0)/连读 0(真 0 或持续漏),
            # 统计 stylized 漏读率,为 gold 双源(购买差值)排期供数据。
            if state.gold == 0:
                _gold_rescued = None
                for _ in range(4):
                    time.sleep(0.4)
                    gv = read_gold(self.ctx, self.screenshot())
                    if gv > 0:
                        state.gold = gv
                        _gold_rescued = gv
                        break
                from sr_od.application.currency_war.cw_observe import obs_conflict
                obs_conflict('gold', 0, _gold_rescued if _gold_rescued is not None else 0,
                             None, verdict=('采新-救援成功(首读假0,stylized漏)' if _gold_rescued is not None
                                            else '确认真0(4帧连读0)'),
                             source='shop_rescue')
            # task#105:优先 tracked_bench_chars(带 star+merge,mutate 同步);空(首轮)退 tracked_bench(旧 star 恒1)。
            if match.session.tracked_bench_chars:
                state.bench = deepcopy(match.session.tracked_bench_chars)  # copy 防下游 plan 污染持久态
                log.info(f'[cw] tracked_bench_chars(seed)={[(c.char_id, c.star) for c in state.bench]}')
            elif match.session.tracked_bench:
                state.bench = _tracked_bench_chars(match.session.tracked_bench)
                log.info(f'[cw] tracked_bench(旧 seed)={match.session.tracked_bench}')
            # 读 comp 成型度 —— overlay 时 board 不可读,用上次备战读的近似。
            match.session.last_state = state
            # r95 审计必修②:plan 异常也要留证(run16 模式:7 个买牌回合 record_decision
            # 整体缺席 + 40s 无 op 记录 = decide_prep 抛错被上层吞,事后不可诊断)。
            # 异常时仍写一条 decisions(Error 占位)+ 完整栈到 log,再向上抛(行为不变)。
            try:
                actions = match.strategy.decide_prep(state, match.session, config)
            except Exception:
                import traceback

                from sr_od.application.currency_war.cw_telemetry import (
                    record_decision as _rd_err,
                )
                _tb = traceback.format_exc()
                log.error('[cw!][plan] decide_prep 异常(留证后上抛):\n%s', _tb)
                with contextlib.suppress(Exception):
                    # eval_breakdown 是 dict[str,float],错误信号用 len(_tb) 数值占位
                    # (异常本体全文在 log,此处只留"该回合 plan 崩了"的可检索标记)
                    _rd_err(state, match.session.target_comp.name if match.session.target_comp else '',
                            {}, {'plan_error': 1.0, 'plan_error_len': float(len(_tb))}, [])
                raise
            # A2:target 由 session 管理(update_target 写),日志/telemetry 直接读 session.target_comp。
            target_name = match.session.target_comp.name if match.session.target_comp is not None else ''

            _fp_v = _form_progress(match.session.target_comp, state) if match.session.target_comp is not None else -1.0
            # r295(用户定调:判读必须看节点类型——判读人看日志时
            # 备战帧没有节点上下文,r8"+2 回升"会被误读成遭遇段
            # 胜利):state 行带 node(本节点类型)+next(下节点,
            # 左移推断源)——判读一眼看出"这轮备战的是什么节点"。
            _node = getattr(match.session, 'node_type_current', None) or '?'
            _upc = getattr(match.session, 'upcoming_types', None) or []
            _next = _upc[0] if _upc else '?'
            log.info(f'[cw] state gold={state.gold} hp={state.hp} lv={state.level} '
                     f'plane={state.plane} round={state.round_num} node={_node} '
                     f'next={_next} board={state.board} '
                     f'target={target_name!r} fp={_fp_v:.2f} bench={len(state.bench)}')
            log.info(f'[cw] shop={[(c.faction, c.name, c.cost) for c in state.shop]} '
                     f'plan={[self._fmt_action(a) for a in actions]}')
            # r97 供给快照(进店首见):全波牌面真值源之一 —— 只记 decisions 会丢 refresh 波
            cw_telemetry.record_shop_snapshot('offer', state.shop, state.gold,
                                              state.plane, state.round_num)
            _cand = dict(getattr(match.session, 'last_candidate_scores', {}) or {})
            if getattr(match.session, 'last_candidate_scores_round', None) != state.round_num:
                _cand = {}   # r3 review②:非本轮回合的分数是陈旧值(仅选线轮写入)→ 清空防 close_call 污染
            # r73 RC6:fp 落遥测(form_progress 此前只在日志,P1→P2 断崖审计只能从 board 推)
            _eb: dict[str, float] = {}
            if match.session.target_comp is not None:
                _eb['fp'] = round(_form_progress(match.session.target_comp, state), 3)
            # r101 session 态快照(redesign/102:完整决策输入落盘,回放/快照回归用)
            _sess = match.session
            _extra = {
                'sess_framework': getattr(_sess, 'transition_framework', '') or '',
                'sess_dual_track': bool(getattr(_sess, 'dual_track_phase', False)),
                'sess_drought': getattr(_sess, 'target_drought', None),
                'sess_pivot_cooldown': getattr(_sess, 'pivot_cooldown_until', None),
                'sess_commit_scores': dict(getattr(getattr(_sess, 'commit_signals', None), 'scores', {}) or {}),
                'sess_active_env': getattr(_sess, 'active_env', '') or '',
                # r226 策略 v2 字段(正式字段直接读,B1 修正:
                # default 局 v2_state=None → v2_mode 落空串,
                # 「v2_* 全空=default」判读规则成立)
                'strategy_id': getattr(config, 'strategy_id', 'default'),
                'v2_mode': (_sess.v2_state[0] if _sess.v2_state else ''),
                'v2_locked_line': _sess.locked_line or '',
                'v2_bridge': _sess.bridge_id or '',
                # r359(回放忠实化,ADR-0231):v2 相位机元组全量落盘
                # ——应急/追赶 latch 决定 decide_prep 走哪条分支,
                # 缺它重放系统性偏差(同 r101 当年补 sess_* 的理由)。
                'sess_v2_state': list(_sess.v2_state)
                if getattr(_sess, 'v2_state', None) else None,
            }
            cw_telemetry.record_decision(state, target_name, _cand, _eb, actions, extra=_extra)

            # 执行至首个 RefreshShop(含);无 RefreshShop 则执行全部(DeployMove/SellBench 仍跳过)
            refresh_idx = next((i for i, a in enumerate(actions) if isinstance(a, RefreshShop)), None)
            prefix = actions if refresh_idx is None else actions[:refresh_idx + 1]
            bought_x: set[int] = set()
            did_refresh = False
            for action in prefix:
                if isinstance(action, BuyCard):
                    # plan sim 不从 shop 移除已买牌 → 可能重复 emit 同 x;执行侧按 x 去重
                    if action.card.x in bought_x:
                        continue
                    bought_x.add(action.card.x)
                    pt = (min(click_pts, key=lambda p: abs(p.x - action.card.x))
                          if click_pts else Point(action.card.x, 288))
                    self.ctx.controller.click(pt)
                    log.info(f'[cw-shop] Buy click @({pt.x},{pt.y}) '
                             f'{action.card.faction}/{action.card.name}/{action.card.cost}')
                    time.sleep(0.4)
                    total_buy += 1
                    if action.card.name:
                        match.session.tracked_bench.append(action.card.name)
                        _bought_names.append(action.card.name)
                    mutate_bench_deployed(match.session.tracked_bench_chars, match.session.tracked_deployed, action)
                elif isinstance(action, LevelUp):
                    self.ctx.controller.click(level_btn)
                    log.info(f'[cw-shop] LevelUp click @({level_btn.x},{level_btn.y})')
                    time.sleep(0.6)   # 升级动画/扣金
                    total_level += 1
                elif isinstance(action, RefreshShop):
                    if total_refresh >= BuyShopCards.MAX_REFRESH:
                        continue   # 硬墙:不再刷新(本轮当未刷新 → 收工)
                    self.ctx.controller.click(refresh_btn)
                    log.info(f'[cw-shop] Refresh click @({refresh_btn.x},{refresh_btn.y})')
                    # r325(P1⑤ 等画面审查):刷新后固定 sleep(1.0)
                    # 改**两帧一致门**——牌行区指纹连续两帧一致才
                    # 采快照/重 plan(刷新动画帧上的 SIFT miss 是
                    # r97/38 样本实证的根因;基元=cv2_utils
                    # fingerprint_in_rects/same,r324 下沉件)。
                    # 超时 2.5s 回退旧 sleep 语义(不阻塞买牌)。
                    from one_dragon.base.geometry.rectangle import Rect
                    from one_dragon.utils import cv2_utils as _cvu
                    _rects = (Rect(300, 228, 1560, 326),)   # 商店牌行
                    _base = None
                    _stable = False
                    import time as _t3
                    for _ in range(8):   # ≤2s@0.25s 步长
                        _t3.sleep(0.25)
                        # r327(终审 D):截图裸调会炸 refresh 分支
                        # (离线 mock/瞬断)——与同文件快照段/gate
                        # 调用同契约:suppress 降级为继续等,
                        # 循环尽=超时回退旧 sleep 语义。
                        _fp = None
                        try:
                            _shot = self.screenshot()
                            _fp = _cvu.fingerprint_in_rects(_shot, _rects)
                        except Exception:   # noqa: BLE001  离线契约
                            _fp = None
                        if _fp is not None and _base is not None \
                                and _cvu.fingerprint_same(_fp, _base):
                            _stable = True
                            break
                        if _fp is not None:
                            _base = _fp
                    if not _stable:
                        _t3.sleep(0.5)   # 超时回退(≈旧 1.0s 总量)
                    total_refresh += 1
                    did_refresh = True
                    # r97 供给快照(refresh 波):刷出来的新牌面落盘(局18 教训:只记进店帧
                    # → 「配方件来没来」复盘断章取义,健康线被误判断供弃线)。
                    try:
                        _new_shop = read_shop_cards(self.ctx, self.screenshot())
                        cw_telemetry.record_shop_snapshot(
                            'refresh', _new_shop, state.gold - 2 * total_refresh,
                            state.plane, state.round_num)
                    except Exception:   # noqa: BLE001  快照 best-effort 不阻塞买牌
                        pass
            if not did_refresh:
                break   # 本轮无刷新(或硬墙)→ 买完收工

        # [停机钩子·临时,采完删(用户 2026-08-15 指示)]未购买(含刷新后仍未购买)且商店有
        # 未识别卡(SIFT miss:昔涟诗篇等非角色内容/立绘缺的角色)→ 停机留画面给 AI 建档。
        # read_shop_cards 的采集钩子已存整屏+flag;此处只做停机判定(方案 D:stop_running+保画面)。
        # 立绘缺(开拓者·欢愉/加拉赫)会持续触发——现场采到立绘原料后即不再触发,一石二鸟。
        #
        # 📋 调研档案(2026-08-17 阮·梅/白厄单帧 miss 归因闭环,下次触发先读这段):
        # - 历史触发(r16-r17 留 38 样本 + 当天 14:52/14:54 两次)**全部是刷新动画/settle 瞬时帧**:
        #   ①离线 plaza 库对拍 38 样本全识别(73-119 内点,无一真未知——注意 cw_shot_unique 存的
        #   是检测后另截的稳定帧,≠ miss 当帧,「同图全识别」不能证伪);②本 hook 防抖重读两次均
        #   自愈 → 瞬时性实锤。非光照变体、非立绘库缺。
        # - 已做:刷新后等待 0.8→1.0s(上方 RefreshShop);cw_observation 内嵌 flag 写入钩子已删
        #   (无消费端纯积压)。本 hook 保留:真未知(新版本新卡/昔涟诗篇类非角色内容)仍需它兜底。
        # - 下次触发排查序:①看防抖重读是否自愈(自愈=瞬时帧,考虑再调等待);②未自愈 → 对停机
        #   画面跑 analyze_screen + 离线 SIFT 对拍(真实rect 商店牌-1..5)确认真未知 → 建档/补库。
        # M35 防抖(2026-08-16):全槽 unknown 但 Fate 角色全在库 → 判商店开态动画/settle 瞬时读失败
        # (0.3s sleep 偶不够)——停机前重读 2 帧(各 1s),仍 unknown 才真停(真缺模板不会因重读消失)。
        # f570a76e 审查#1 修:**去 total_buy 门**——「买了≥1 张+仍有未识别槽」
        # 恰是在残缺牌面上做了买牌决策(ADR-0244 裁决理由本尊),原门让它
        # 零留证通过 = 暗门;防抖重读对任何未识别残留都该跑。
        if any(not c.name for c in state.shop):
            _unk = [i + 1 for i, c in enumerate(state.shop) if not c.name]
            for _ in range(2):
                time.sleep(1.0)
                _reshop = read_shop_cards(self.ctx, self.screenshot())
                _unk = [i + 1 for i, c in enumerate(_reshop) if not c.name]
                if not _unk:
                    log.info('[cw-shop][hook] 重读后全识别(动画/settle 瞬时)→ 不停机')
                    break
            if _unk:
                # [停机钩子·恢复]r34 曾降级为留证不停机(理由:连续两局
                # 阻断实跑);2026-08-24 用户裁决**不能降级,恢复停机**——
                # 未识别卡按非 target 跳过 = 带病跑:错过新内容建档窗口
                # 且买牌决策在残缺牌面上做(潜在新卡/新版本内容不可见)。
                # 代价已知会(阻断实跑),用户明示接受。
                _shot = self.save_screenshot(prefix=f'shop_unk_slot{_unk[0]}')
                from datetime import datetime as _dt
                from pathlib import Path as _P
                # 绝对路径锚仓根(审查#4:相对路径在 daemon spawn 的
                # 非 CWD 进程里落错地方,AI 巡检靠 flag 发现停机会失明)
                _fp = _P(__file__).resolve().parents[5] / '.debug' / 'temp' \
                    / 'currency_war' / 'shop_unk.flag'
                _fp.parent.mkdir(parents=True, exist_ok=True)
                _fp.write_text(
                    f'[HOOK-STOP] shop 未识别卡停机钩子(方案D,恢复):operations/prep/shop.py buy\n'
                    f'触发:未购买且商店槽{_unk}未识别(防抖重读 2 帧后仍 miss)——\n'
                    f'   新版本新卡/昔涟诗篇类非角色内容/立绘缺。r34 降级已被用户否决\n'
                    f'   (2026-08-24:未识别不能降级,带病跑错过建档窗口)。\n'
                    f'处理步骤:1. 看 shot={_shot};对停机画面跑 analyze_screen\n'
                    f'   + 离线 SIFT 对拍(真实rect 商店牌-1..5)确认真未知;\n'
                    f'   2. 新卡 → 建档(screen_info/立绘库);瞬时帧类 → 调上方\n'
                    f'   RefreshShop 后等待;3. 删本 flag + 重启 MCP server 重跑。\n'
                    f'删除条件:连续多局零触发(未知内容建模收敛)后按 skill\n'
                    f'   od-dev-stop-hooks 生命周期判据评估删除。\n'
                    f'ts={_dt.now().strftime("%m-%d %H:%M:%S")}\n',
                    encoding='utf-8')
                log.warning('[cw!] [shop] 未识别卡槽%s(重读后仍 miss)→ 停机留画面'
                            '待建档 shot=%s(用户裁决恢复:未识别不能降级)', _unk, _shot)
                self.ctx.run_context.stop_running(reason='hook:shop_unknown_card')
                return self.round_fail(status=f'shop 未识别卡槽{_unk},停机留证')

        # plan() 在最后一轮(无 refresh)的完整 actions 里含 DeployMove —— 取最后一次完整 plan 的 deploy moves。
        # ⚖️ pending_deploys 写入已删(2026-08-16 review D16/TOP4:0 读者,DeployBench 实读
        # last_state.board;只写不读 = 腐化名单)。留日志行(计划可见性)。

        # → 新占槽 = bought 卡落点(left-to-right = buy 顺序,bench 从左到右填)。**两帧同 shop-OPEN 状态**
        # 自修正:deployed 后 deploy_bench 删该 slot;空槽 drag bench-count 不降 → retry-stick skip)。
        if _bought_names:
            _after_shot = self.screenshot()
            _new_slots = new_bench_slots(self.ctx, _buy_baseline, _after_shot)
            if _new_slots and match is not None:
                _slot_map = dict(zip(_bought_names, _new_slots, strict=False))
                if not hasattr(match, 'bench_slot_map') or match.bench_slot_map is None:
                    match.bench_slot_map = {}
                match.bench_slot_map.update(_slot_map)   # 合并(跨回合累积),非覆盖
                log.info(f'[cw-shop] char→slot(pixel-diff,合并):{_slot_map} → 全 map={match.bench_slot_map}')

        # 关商店(「收起」)
        time.sleep(0.4)
        self.round_by_find_and_click_area(self.screenshot(), SHOP_SCREEN_NAME, '按钮-收起', success_wait=1.0)
        # r312(ADR-0213 批次1;买后收起站)+r347(旧路径删除):
        # 现状买后零等待——click+~1.4s 即 read_game_state(L466
        # 重估)+read_gold(L484 差值对拍),而关店动画 ~3s(r299
        # 实测)→ 重估与对拍读在半开帧(与局31 买前同构)。
        # gate 无条件化(异常=放行,离线契约)。
        from sr_od.application.currency_war.cw_observation_gate import (
            PROFILE_CLOSED,
            wait_stable_frame,
        )
        log.info('[cw][gate] path=new(shop 买后收起)')
        # r346:contextlib 已模块级(同上,H1 雷)
        with contextlib.suppress(Exception):   # 离线契约:放行
            wait_stable_frame(self, profile=PROFILE_CLOSED)
        # r251 修 A(买后同轮重估):update_target 原只在买前跑——买桥件
        # 当轮桥不认领,deploy 当轮无方向(第六局 r4 买藿藿/爻光但
        # target='' 仙舟件全坐板凳,散 pair 白挨打 -8/-12/-28)。
        # 买完用最新 bench 重估一次:桥/锁线当轮生效,紧随的 deploy
        # 就有方向。幂等(update_target 是纯重估,已锁线不漂移)。
        try:
            if match is not None and (total_buy or total_level or total_refresh):
                _post = read_game_state(self.ctx, self.screenshot())
                _post.hp = hp_value
                if match.session.last_node_type:
                    _post.node_type = match.session.last_node_type
                match.strategy.update_target(_post, match.session, config)
        except Exception as e:   # noqa: BLE001  重估失败不阻塞买牌
            log.debug('[cw] 买后重估失败(不阻塞): %s', e)
        # gold 差值双源对拍(观察冲突审计 #6 P2,2026-08-17):动作账(cost 由注册表/reader 估)vs
        # 关店后实际读数 —— expected = 开店金 − Σ买价 − 升级费 − 刷新费(read_gold stylized 间歇漏,
        # 但差值对拍容忍 ±2:收入/连胜金不可观项混入)。不等 → 一方有毒(stylized 漏读 / cost 错 /
        # 未观收入),留证统计毒化率;机制核对器(r9)另有 REFRESH_COST 专项,此处只管 gold 总账。
        if total_buy or total_level or total_refresh:
            _spend = (sum(a.card.cost for a in actions if isinstance(a, BuyCard) and a.card.x in bought_x)
                      + sum(a.cost for a in actions if isinstance(a, LevelUp))
                      + total_refresh * (state.shop_refresh_cost or 2))
            _final_gold = read_gold(self.ctx, self.screenshot())
            _expected = state.gold - _spend
            if _final_gold is not None and abs(_final_gold - _expected) > 2:
                from sr_od.application.currency_war.cw_observe import (
                    obs_conflict as _oc,
                )
                _oc('gold_delta', _expected, _final_gold, None,
                    verdict='留证-动作账vs读数不等(stylized漏读/cost错/未观收入)',
                    source='shop_spend_audit', plane=state.plane, round_num=state.round_num,
                    spend=_spend)
        return self.round_success(
            f'plan 买{total_buy}张 升{total_level}次 刷{total_refresh}次 '
            f'(gold={state.gold} lv={state.level} plane={state.plane})'
        )

    def _fmt_action(self, a) -> str:
        """单 Action → 紧凑日志串(调试/复盘读 plan 用)。"""
        if isinstance(a, BuyCard):
            return f'Buy({a.card.faction}/{a.card.name}/{a.card.cost})'
        if isinstance(a, LevelUp):
            return f'LvUp({a.cost})'
        if isinstance(a, DeployMove):
            return f'Deploy(bench{a.bench_idx}->{a.to_row})'
        if isinstance(a, RefreshShop):
            return 'Refresh'
        if isinstance(a, SellBench):
            return f'Sell(bench{a.bench_idx})'
        return type(a).__name__

    def _handle_bench_full(self, screen) -> bool:
        """备战席已满 → 升等级 + 循环卖前几个 bench 清警告(位置式,不需角色身份)。

        游戏提示「出售或提升等级」:升等级加 XP(解锁更高费刷新/上阵数)+ sell 给 gold →
        bench 槽位空出 → 警告消失 → 解锁购买。返回是否处理了(处理了则本回合跳过买牌)。
        ⚠️ 溢出感知(2026-08-16 用户实证机制):奖励给的角色在席满时**悬浮在备战栏上方**,
        卖出 1 个 → 溢出落位 → 席仍满(净空位 0)。旧循环卖 3 次固定 bench-1..3 在有溢出时
        可能次次"卖完还满"耗尽预算。修:卖后重验,仍满且**检测到溢出立绘**(备战上方带
        高边缘)→ 继续卖(上限提到 5);无溢出 → 原逻辑。
        """
        if not self.round_by_ocr(screen, '备战席已满').is_success:
            return False
        level_btn = area_center(self.ctx, BuyShopCards.BUY_EXP_AREA) or BuyShopCards.LEVEL_UP_FALLBACK
        # ADR-0129:每击 +4 XP;6→7 级需 40 XP = 10 击(盖全等级段,原 8 击不够)
        for _ in range(10):
            self.ctx.controller.click(level_btn)
            time.sleep(0.3)
        for sell_i in range(5):
            fresh = self.screenshot()
            if not self.round_by_ocr(fresh, '备战席已满').is_success:
                break
            bench_x = 438 + sell_i * 125  # bench-1..5 中心(横间距 ~125;溢出时多卖)
            self.ctx.controller.drag_to(end=Point(70, 846), start=Point(bench_x, 912), duration=0.8)
            time.sleep(1)
            for _ in range(4):
                self.ctx.controller.click(level_btn)
                time.sleep(0.3)
        # 光标 parking(审计 R1c):本函数点击密集(购买经验×10+,距等级区 18px),收尾不 park
        # 则污染**跨 op** 的下一读(Director heavy observe read_game_state)。
        self.park_cursor(after_wait=0.1)
        return True
