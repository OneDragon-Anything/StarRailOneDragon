
import contextlib
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import (
    HP_MAX,
    SHOP_SCREEN_NAME,
    area_center,
)
from sr_od.application.currency_war.obs.cw_observation import (
    read_game_state,
    read_gold,
    read_gold_settled,
)
from sr_od.application.currency_war.obs.cw_observation_gate import (
    PHASE_PREP_CLEAN,
)
from sr_od.application.currency_war.operations.prep.buy_cards import (
    BUY_EXP_AREA,
    LEVEL_UP_FALLBACK,
    MAX_REFRESH,
    REFRESH_FALLBACK,
    _apply_hp,
    _tracked_bench_chars,
    build_post_buy_incremental_state,
    expected_gold_after_actions,
    run_buy_waves,
)
from sr_od.application.currency_war.operations.prep.close_shop import close_shop
from sr_od.application.currency_war.operations.prep.open_shop import open_shop
from sr_od.application.currency_war.prep_actions import (
    SHOP_CLOSE_ANIM_S,
    sell_point,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class BuyShopCards(SrOperation):
    """备战阶段:开商店 → 决策驱动买牌/升等级 → 关商店。

    W970 批 A 原子化编排壳:``OpenShopOp`` → ``BuyCardsOp``(波循环,
    经 :func:`run_buy_waves` 宿主直调)→ ``CloseShopOp``,外部调用接口
    (director/battle_prep 调用点)与返回语义不变——行为等价是本批硬约束。
    原子核心以「宿主 op 直调」方式复用壳的 round_by_* 判定与测试替身桩;
    三个原子 op 类(open_shop/buy_cards/close_shop 模块)另可独立跑。

    接战术层 ``match.strategy.decide_prep``(DecisionV2Strategy 四层:候选→过滤→评分→仲裁):
    OCR 读真实 ``gold/level/round/plane/board/shop`` → 执行返回的 ``BuyCard``/``LevelUp``。

    接线范围(见 ``docs/develop/currency_war/strategy/05_observation.md``):
    - 执行 ``BuyCard``(点牌)/ ``LevelUp``(点「购买经验」)/ ``RefreshShop``(点「刷新」,两阶段 plan)。
    - **跳过** ``DeployMove`` —— deploy 走 ``DeployBench``(deploy-all,游戏按等级封顶;
      避开 plan 的 bench_idx→物理槽映射复杂度)。
    - **D牌两阶段(r6 F8)**:plan emit RefreshShop 后,simulate 不换牌 → 其后的 BuyCard 是旧 shop
      失效决策。故每轮执行**至首个 RefreshShop(含)**,刷新后重 OCR shop + 重 plan(MAX_REFRESH 硬墙)。
    - **SellBench(迁移审计 w62(git 历史) 件2/ADR-0329 起执行)**:d2 卖通道
      (liquidity/carry_gate/arbiter)发射的 ``SellBench(bench_idx)`` 在波循环内执行
      (防误卖轻守卫 + 拖 备战栏-(idx+1) → 出售区,详见 buy_cards.run_buy_waves)。

    HP 只在 shop 关闭帧可读:壳内前置段先关店(若开)→ 关帧 HP 读链
    (新鲜度门/结算真值/r1 重试/fail-closed,W970 §4.3.4 批 C 迁流程层备战
    观察)→ 交波循环做值位同写覆盖。买后重估与 gold 对拍等关店帧后处理
    留守本壳(W970 §4.3.4 时序锚 = 收起点击后)。

    前置:已在「货币战争-备战」。买完关商店,交上层 deploy。
    """

    # 「购买经验」按钮 area 名/兜底/刷新硬墙:单一源在 buy_cards(波循环消费),
    # ClassVar 别名保留外部引用面(BuyShopCards.BUY_EXP_AREA 等)不破。
    BUY_EXP_AREA: ClassVar[str] = BUY_EXP_AREA
    LEVEL_UP_FALLBACK: ClassVar[Point] = LEVEL_UP_FALLBACK
    REFRESH_FALLBACK: ClassVar[Point] = REFRESH_FALLBACK
    MAX_REFRESH: ClassVar[int] = MAX_REFRESH

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-商店买牌')

    @operation_node(name='商店买牌', is_start_node=True)
    def buy(self) -> OperationRoundResult:
        screen = self.last_screenshot
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
        # 事件 overlay 兜底:全走 screen_info 标题 area(位置判,结构性不误匹配,T#103 化债:
        # 遭遇/伙伴/巨星原为「遭遇其一/选择伙伴/确认选择」全屏 OCR + 高 lcs,已按各自画面档 area 化;
        # 确认选择 catch-all 由 overlay 标题锚取代 —— 同屏均另有独有标题锚,全屏扫无必要)。
        for _scr, _area, _evt in (
            ('货币战争-投资策略', '标识-请选择投资策略', '投资策略'),
            ('货币战争-投资环境', '标识-投资环境', '投资环境'),
            ('货币战争-补给', '标识-补给阶段', '补给阶段'),   # 2026-08-13:补给建档后从全屏 OCR 移到 area(位置判 [893,120,1027,230])——治备战「返回补给阶段」按钮文本假阳 → 死循环
            ('货币战争-遭遇节点', '标识-遭遇节点', '遭遇'),   # T#103:原全屏 OCR「遭遇其一」(lcs=0.9 卡标题截断 miss 前科,battle_loop 0c 同源 anchor)
            ('货币战争-列车同行', '标识-选择伙伴', '选择伙伴'),   # T#103:原全屏 OCR「选择伙伴/确认选择」
            ('货币战争-盛会之星', '标识-盛会之星', '盛会之星'),   # T#103:「确认选择」事件里唯一有画面档的巨星 overlay 改走标题锚(battle_loop 0b 同源)
        ):
            if self.round_by_find_area(screen, _scr, _area).is_success:
                return self.round_fail(f'备战被事件 overlay({_evt})叠,交主循环处理')


        # HP 只在 shop **关闭**时显示在右上角(shop 开启时该位置被遮/空 → read_hp 返 100,
        # telemetry plan-time 全 100 即此;2026-08-03 2 图诊断)。gold 相反(shop 开才显示右下)。
        # 故:若 shop 开着先「收起」关 → 关闭帧读 hp 真值 → 再开 shop 读 gold/shop/board。
        if self.round_by_find_area(screen, SHOP_SCREEN_NAME, '按钮-收起').is_success:
            # DD-011 操作完成自等动画:收起动画时长由 op 显式等待承担(screen_flow_timing
            # #15 实测 ~1s),等待结束 = 画面承诺稳定;gate(测量驱动)在此退役。
            # 后继读数动画尾帧风险由既有防线兜:hp 新鲜度门/重读确认循环、round retry。
            self.round_by_find_and_click_area(screen, SHOP_SCREEN_NAME, '按钮-收起')
            time.sleep(SHOP_CLOSE_ANIM_S)
            screen = self.screenshot()
        # r317(ADR-0213 批次2):read_hp 裸调用迁 read_hp_opt
        # (miss→None 显式化);None 走结算真值链(⚠ r322 修:
        # **带新鲜度门**——陈旧 last_hp 不当真值,防「陈 hp
        # 冻结毒化」从 miss 路径回流,与下方 L249 段同判据)。
        # `w580_hp_trust_defense/`:无新鲜结算真值→**不产值**(hp_value=None)——旧裸 100
        # 兜底只允许喂「重读确认循环」与日志;喂决策 state 的值必须来自
        # 真读或新鲜结算真值,否则不覆盖、保留对账层值+位(fail-closed)。
        # 旧「>=HP_MAX 重读 2 次」保留(None≠100 分流后,
        # 该循环只处理真满血误读,语义更纯)。
        from sr_od.application.currency_war.obs.cw_observation import (
            read_hp_opt,
            read_phase_round,
        )
        match = self.ctx.cw_match   # r317:提前(None 兜底链要用)
        _hp_raw = read_hp_opt(self.ctx, screen)
        _hp_readable = _hp_raw is not None
        _hp_trusted = _hp_readable   # 真读帧两位皆 True(对齐 read_game_state 真读口径)
        _hp_r1 = False   # r1 帧标记(见 miss 分支注释)
        if _hp_raw is None:
            _pr = read_phase_round(self.ctx, screen)
            _now_t = ((_pr[0] - 1) * 9 + _pr[1]) if (_pr and _pr[0] and _pr[1]) else None
            _hp_t = getattr(match.session, 'last_hp_t', None) if match is not None else None
            _fresh = (_now_t is not None and _hp_t is not None
                      and _now_t - _hp_t == 1)
            _hp_r1 = (_pr is not None and _pr[0] == 1 and _pr[1] == 1)
            if (match is not None and _fresh
                    and getattr(match.session, 'last_hp', None) is not None):
                _hp_raw = match.session.last_hp
                _hp_trusted = True   # 结算真值:trusted 位=True;非本帧真读,readable 位保持 False
            elif _hp_r1:
                # r1 备战帧(用户修正前提,ADR-0282 开局兜底在 r1 废除):
                # 血量固定但不恒 100(随当局难度/词缀变),真值源=画面显示值。
                # miss=时序抖动 → 重试;仍 miss → hp 不产值(诚实未知),
                # 严禁 100 兜底。r2+ 不走此臂(仍 fail-closed)。
                from sr_od.application.currency_war.operations.prep.buy_cards import (
                    _r1_retry_read_hp,
                )
                _rv = _r1_retry_read_hp(
                    lambda: read_hp_opt(self.ctx, self.screenshot()))
                if _rv is not None:
                    _hp_raw = _rv
                    _hp_readable = True
                    _hp_trusted = True
            else:
                _hp_raw = None
            log.info('[cw][shop] HP 区 miss→%s(fresh=%s 结算真值/r1=%s/不覆盖)',
                     _hp_raw, _fresh, _hp_r1)
        hp_value = _hp_raw
        # round9 同款读对 29 —— 间歇时序,非持续)→ 重读 2 次取真值。防 maybe_pivot hp_safe 信号失效
        # (误判满血不保血 → 不必要失血死)。真满血重读仍 HP_MAX(无害);HP 区持续空(罕见)→ hp_value=None 不覆盖。
        if hp_value is not None and hp_value >= HP_MAX:
            for _ in range(2):
                time.sleep(0.4)
                _v = read_hp_opt(self.ctx, self.screenshot())
                if _v is not None and _v < HP_MAX:
                    hp_value = _v
                    break

        # 开商店(原子 op:gold/shop/board 须 shop 开才显示;HP 此时被遮但上面已读过)。
        # 幂等:店已开直接过;未开点「按钮-商店」→ 固定等待 + 「按钮-收起」
        # fail-closed 验证(open_shop 核心)。
        _r_open = open_shop(self)
        if not _r_open.is_success:
            return _r_open

        # 无强信号保持 —— 等价旧 _target_comp class-attr 逻辑,但状态进 session 跨回合持久)。用 shop 关闭帧
        # hp 覆盖的 state(M6 钉死行为等价:hp 真值 → maybe_pivot 的 hp_safe 信号正确触发,非 shop 开帧的假 100)。
        # (match 已在 HP 读段提前取——r317)
        # live round4 读 100 实际 58)→ 保血/maybe_pivot 信号失效。结算屏「小队生命值NN」可靠 → 用它
        # 给 prep state.hp(HP 结算→下回合 prep 不变)。round1 无结算 → None → 退 read_hp(round1 读对)。
        # ⚖️ r68 review 新鲜度门(单源 helper cw_strategy.gated_hp;director 环入口同门):
        # 结算 hp 只在「紧邻上一节点」才可覆盖 —— 低 conf 结算轮 last_hp 残留陈值,无条件覆盖 =
        # 陈 hp 冻结毒化每回合 prep(保血/转型永不触发,P1 boss 赢→P2 秒死 ×3 的观测链根因)。
        from sr_od.application.currency_war.decision.cw_strategy import gated_hp
        from sr_od.application.currency_war.obs.cw_observation import read_phase_round
        _pr = read_phase_round(self.ctx, screen)
        _now_t = ((_pr[0] - 1) * 9 + _pr[1]) if (_pr and _pr[0] and _pr[1]) else None
        _hp_t = getattr(match.session, 'last_hp_t', None) if match is not None else None
        _hp_fresh = (_now_t is not None and _hp_t is not None and _now_t - _hp_t == 1)
        if match is not None and match.session.last_hp is not None and _hp_fresh:
            # 观察冲突审计 #7(2026-08-16):「结算→下回合 prep 不变」是本文件自述契约 → prep 读与
            # 结算真值不等 = 双源分歧事件,留证(兼测 prep read_hp 毒化率与结算屏误读,双向有用);
            # 裁决仍采新(结算屏是权威源,契约本身允许 prep 读噪声)。
            if (hp_value is not None and hp_value != match.session.last_hp
                    and hp_value < HP_MAX):
                from sr_od.application.currency_war.kernel.cw_observe import (
                    obs_conflict,
                )
                obs_conflict('hp', match.session.last_hp, hp_value, None,
                             verdict='采新-结算真值覆盖(prep读≠结算,留证测毒化率)',
                             source='prep_read_hp_vs_settlement')
            log.info(f'[cw] hp 用结算屏真值 {match.session.last_hp}(prep read_hp={hp_value} 不可靠,覆盖)')
            hp_value = gated_hp(hp_value, match.session, _now_t)   # 单源门(此处恒取结算值;陈旧分支在 elif)
        elif match is not None and match.session.last_hp is not None:
            log.info('[cw] hp 结算值陈久跳过覆盖(last_hp=%s t=%s, now t=%s)→ 用 prep 现读 %s(防冻结毒化)',
                     match.session.last_hp, _hp_t, _now_t, hp_value)

        # 买牌波循环(原子 op 核心:读牌面 → d2 决策 → 买/卖/刷/升 → 刷新重判;
        # 遥测写点/观测自检网原样随迁 buy_cards.run_buy_waves,决策逻辑零改动)。
        _rr, outcome = run_buy_waves(self, match,
                                     hp_value, _hp_readable, _hp_trusted)
        if _rr is not None or outcome is None:
            # 未识别卡停机钩子触发(留证 round_fail)——与原实现同语义直接退出
            return _rr if _rr is not None else self.round_fail('买牌波循环无产出')

        # 关商店(原子 op:「按钮-收起」→ 固定等待 SHOP_CLOSE_ANIM_S → 「收起消失」
        # 验证;close_shop 核心,DD-011 操作完成自等动画)。
        _r_close = close_shop(self)
        if not _r_close.is_success:
            return _r_close

        state = outcome.state
        config = outcome.config
        total_buy = outcome.total_buy
        total_level = outcome.total_level
        total_refresh = outcome.total_refresh
        total_sell = outcome.total_sell
        total_sell_income = outcome.total_sell_income
        _spend_executed = outcome.spend_executed
        gold_open = outcome.gold_open
        _plan_truncated = outcome.plan_truncated
        _refresh_skipped = outcome.refresh_skipped
        _refresh_attempted = outcome.refresh_attempted
        _refresh_board_changed = outcome.refresh_board_changed
        _buy_purchases = outcome.buy_purchases
        _buy_has_sell = outcome.buy_has_sell
        _buy_unidentified = outcome.buy_unidentified
        _buy_pre_bench = outcome.buy_pre_bench
        _buy_pre_deployed = outcome.buy_pre_deployed
        # r251 修 A(买后同轮重估):update_target 原只在买前跑——买桥件
        # 当轮桥不认领,deploy 当轮无方向(第六局 r4 买藿藿/爻光但
        # target='' 仙舟件全坐板凳,散 pair 白挨打 -8/-12/-28)。
        # 买完用最新 bench 重估一次:桥/锁线当轮生效,紧随的 deploy
        # 就有方向。幂等(update_target 是纯重估,已锁线不漂移)。
        try:
            if match is not None and (total_buy or total_level or total_refresh):
                _post = None
                if not total_level:
                    # 执行边界压缩·买后验证增量:本单元动作(无升级)只改
                    # gold/bench(plane/round/board 等机制不变量,构造单一源 =
                    # build_post_buy_incremental_state)→ 单区金真读 + tracked
                    # 重播,替代整帧 OCR。fail-closed 双维回退全量读:金失读
                    # (None)/tracked 空(真空与丢跟踪不可区分,见构造点契约)。
                    # 金读走稳定门(read_gold_settled):关店帧入账计数器可能
                    # 仍在跳,单帧会采到入账前旧值(误读维度造值;门=两帧一致
                    # 才采信,不一致取末帧+留证)。
                    _inc_gold = None
                    with contextlib.suppress(Exception):
                        _inc_gold = read_gold_settled(self.ctx, self.screenshot())
                    if _inc_gold is not None:
                        _post = build_post_buy_incremental_state(
                            state, _inc_gold,
                            (match.session.tracked_bench_chars
                             or _tracked_bench_chars(match.session.tracked_bench)),
                            match.session.last_node_type or None,
                            hp_value, _hp_readable, _hp_trusted)
                if _post is None:
                    _post = read_game_state(self.ctx, self.screenshot(),
                                            phase=PHASE_PREP_CLEAN)   # ADR-0462 关店后=干净备战基线
                    _apply_hp(_post, hp_value, _hp_readable, _hp_trusted)
                    if match.session.last_node_type:
                        _post.node_type = match.session.last_node_type
                match.strategy.update_target(_post, match.session, config)
        except Exception as e:   # noqa: BLE001  重估失败不阻塞买牌
            log.debug('[cw] 买后重估失败(不阻塞): %s', e)
        # `w536_merge_expect/`:单元购买意图 → 期望态,暂存 session 供 PrepDirector 主环在
        # RunBuyPhase 后的 heavy 定型帧上消费对账(surface='bench',
        # kind='buy_expect_mismatch';零决策记账)。含卖出/未识别牌不建
        # (见单元头注释);计算失败静默跳过(best-effort,不阻塞买牌)。
        if match is not None and _buy_purchases \
                and not _buy_has_sell and not _buy_unidentified:
            with contextlib.suppress(Exception):

                from sr_od.application.currency_war.kernel.cw_prep_expect import (
                    compute_buy_expect,
                )
                _buy_expect = compute_buy_expect(
                    _buy_purchases, _buy_pre_bench, _buy_pre_deployed)
                if _buy_expect is not None:
                    match.session.pending_buy_expect = _buy_expect
        # gold 差值双源对拍(观察冲突审计 #6 P2,2026-08-17):动作账(逐动作执行时
        # 累计的 _spend_executed:买价+升级费+当次刷价)vs 关店后实际读数 ——
        # expected = 开店首读金 − 全程执行花金 + 全程卖入。基线必须取首读快照
        # 而非末波重读值(后者已净含各波花销,再减全程账 = 跨波重复扣,多波
        # 刷新场景期望恒偏低,量级=前面各波刷新费合计)。(read_gold stylized
        # 间歇漏,但差值对拍容忍 ±2:收入/连胜金不可观项混入)。不等 → 一方有
        # 毒(stylized 漏读 / cost 错 / 未观收入),留证统计毒化率;机制核对器
        # (r9)另有 REFRESH_COST 专项,此处只管 gold 总账。
        if total_buy or total_level or total_refresh or total_sell:
            _spend = _spend_executed
            _final_gold = read_gold(self.ctx, self.screenshot())
            # 金面收口:关店实读金无条件暂存(无论对拍是否冲突)——director
            # 单元关闭落账时经 record_spend_unit 消费,填 spend_ledger 预留
            # 字段 gold_close。此前只有 mismatch 才落冲突行,「对拍通过」与
            # 「read_gold 失读」离线不可分(三态判定 unknown 面);失读(None)
            # 照记(trusted=False),unknown 占比降到读失败率。分类器零改动。
            from sr_od.application.currency_war.telemetry import state as _cw_tel
            _cw_tel.set_unit_gold_close(_final_gold)
            # 迁移审计 w62(git 历史) 件2(ADR-0329):gold 差值对拍纳入卖入——卖出接线后,卖轮实际金 =
            # 开店金 − 花出 + 卖入(游戏侧卖出入账);旧口径不含卖入与实读金恒差
            # income → 每卖轮误报 gold_delta 冲突留证(design 章2.7 必改项)。
            _expected = expected_gold_after_actions(
                gold_open if gold_open is not None else state.gold,
                _spend, total_sell_income)
            if _final_gold is not None and abs(_final_gold - _expected) > 2:
                from sr_od.application.currency_war.kernel.cw_observe import (
                    obs_conflict as _oc,
                )
                _oc('gold_delta', _expected, _final_gold, None,
                    verdict='留证-动作账vs读数不等(stylized漏读/cost错/未观收入)',
                    source='shop_spend_audit', plane=state.plane, round_num=state.round_num,
                    spend=_spend)
        # `w577_refresh_fee_and_andon/`:「计划≠尝试」执行事实 → 单元账暂存(director 落账时经模块级
        # record_spend_unit 消费进 spend_ledger;与 set_unit_gold_close 同槽
        # 模式)。全缺省不调(免残留噪声);best-effort 不阻塞收工。
        if _plan_truncated or _refresh_attempted \
                or _refresh_skipped is not None:
            with contextlib.suppress(Exception):
                # 遥测模块显式别名(裸 state=GameState 变量,误绑会被
                # suppress 吞成执行事实静默断流,同 free_refresh 留证段)
                from sr_od.application.currency_war.telemetry import state as _cw_tel
                _cw_tel.set_unit_exec_facts(
                    plan_truncated=_plan_truncated,
                    refresh_skipped=_refresh_skipped,
                    refresh_attempted=_refresh_attempted,
                    refresh_board_changed=_refresh_board_changed)
        return self.round_success(
            f'plan 买{total_buy}张 升{total_level}次 刷{total_refresh}次 '
            f'卖{total_sell}张(+{total_sell_income}金,守卫拦{outcome.total_sell_skip}) '
            f'(gold={state.gold} lv={state.level} plane={state.plane})'
        )

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
        level_btn = area_center(self.ctx, BUY_EXP_AREA) or LEVEL_UP_FALLBACK
        # ADR-0129:每击 +4 XP;6→7 级需 40 XP = 10 击(盖全等级段,原 8 击不够)
        for _ in range(10):
            self.ctx.controller.click(level_btn)
            time.sleep(0.3)
        for sell_i in range(5):
            fresh = self.screenshot()
            if not self.round_by_ocr(fresh, '备战席已满').is_success:
                break
            bench_x = 438 + sell_i * 125  # bench-1..5 中心(横间距 ~125;溢出时多卖)
            # 迁移审计 w62(git 历史) 件2(ADR-0329):出售区落点单一源(screen_info「区域-出售区」,兜底常量)
            self.ctx.controller.drag_to(end=sell_point(self.ctx),
                                        start=Point(bench_x, 912), duration=0.8)
            time.sleep(1)
            for _ in range(4):
                self.ctx.controller.click(level_btn)
                time.sleep(0.3)
        # 光标 parking(审计 R1c):本函数点击密集(购买经验×10+,距等级区 18px),收尾不 park
        # 则污染**跨 op** 的下一读(Director heavy observe read_game_state)。
        self.park_cursor(after_wait=0.1)
        return True
