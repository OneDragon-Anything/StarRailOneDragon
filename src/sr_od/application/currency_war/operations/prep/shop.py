# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

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
    read_hp,
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
    plan / char_quality / comp core check 知 bot 自有角色。**SIFT 立绘识别现已可行**(71 CW
    立绘库,D-8/D-10/D-12 验证)—— deploy op 后用 SIFT 真实身份纠 tracking 漂(deploy_bench
    ``_reconcile_tracking``,D-12);buy 期 bench 仍用 OCR 名跟踪(buy 改变 bench,SIFT 单帧跟不上)。
    """
    from sr_od.application.currency_war.cw_chars import get_char
    out: list[BenchChar] = []
    for i, n in enumerate(names):
        if not n:
            continue
        ch = get_char(n)
        out.append(BenchChar(
            slot=i, char_id=n,
            faction=(ch.factions[0] if (ch is not None and ch.factions) else '?'),
        ))
    return out


class BuyShopCards(SrOperation):
    """备战阶段:开商店 → ``plan`` 驱动买牌/升等级 → 关商店。

    接战术层 ``cw_decisions.plan``(阶段键控 eval + 硬门贪心 + 蒙特卡洛 D牌):OCR 读真实
    ``gold/level/round/plane/board/shop`` → ``plan`` → 执行返回的 ``BuyCard``/``LevelUp``。

    v1 接线范围(2026-08-03,见 ``docs/develop/currency_war/strategy/05_data_wiring.md``):
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
            time.sleep(0.4)
            screen = self.screenshot()
        hp_value = read_hp(self.ctx, screen)
        # round9 同款读对 29 —— 间歇时序,非持续)→ 重读 2 次取真值。防 maybe_pivot hp_safe 信号失效
        # (误判满血不保血 → 不必要失血死)。真满血重读仍 HP_MAX(无害);HP 区持续空(罕见)→ 维持 100 兜底。
        if hp_value >= HP_MAX:
            for _ in range(2):
                time.sleep(0.4)
                _v = read_hp(self.ctx, self.screenshot())
                if _v < HP_MAX:
                    hp_value = _v
                    break

        # 开商店(gold/shop/board 须 shop 开才显示;HP 此时被遮但上面已读过)
        if not self.round_by_find_area(self.screenshot(), SHOP_SCREEN_NAME, '按钮-收起').is_success:
            if not self.round_by_find_and_click_area(self.screenshot(), '货币战争-备战', '按钮-商店', success_wait=1.5).is_success:
                return self.round_retry('找不到商店/收起按钮', wait=1)
            time.sleep(0.5)

        # 牌位/升级/刷新中心从 screen_info 读(缺失兜底)。target 由 strategy.update_target 管理(下方)。
        config = CurrencyWarConfig(self.ctx.current_instance_idx)
        click_pts = shop_card_click_points(self.ctx)
        level_btn = area_center(self.ctx, BuyShopCards.BUY_EXP_AREA) or BuyShopCards.LEVEL_UP_FALLBACK
        refresh_btn = area_center(self.ctx, '按钮-刷新', SHOP_SCREEN_NAME) or BuyShopCards.REFRESH_FALLBACK

        # 无强信号保持 —— 等价旧 _target_comp class-attr 逻辑,但状态进 session 跨回合持久)。用 shop 关闭帧
        # hp 覆盖的 state(M6 钉死行为等价:hp 真值 → maybe_pivot 的 hp_safe 信号正确触发,非 shop 开帧的假 100)。
        match = self.ctx.cw_match
        # live round4 读 100 实际 58)→ 保血/maybe_pivot 信号失效。结算屏「小队生命值NN」可靠 → 用它
        # 给 prep state.hp(HP 结算→下回合 prep 不变)。round1 无结算 → None → 退 read_hp(round1 读对)。
        if match is not None and match.session.last_hp is not None:
            log.info(f'[cw] hp 用结算屏真值 {match.session.last_hp}(prep read_hp={hp_value} 不可靠,覆盖)')
            hp_value = match.session.last_hp
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
            state = read_game_state(self.ctx, self.screenshot())
            state.hp = hp_value   # shop 开帧 hp 区空(read_game_state 给 100)→ 用 shop 关闭帧真值覆盖
            # gold-robust:gold 数字 stylized,paddle OCR det 间歇漏(同帧读 3/0/空;实锤 click-test
            # 买牌成功 gold≥1 但 reader 读 0,见 process_log)→ 读 0 时重读几帧取首个 >0(deterministic 同帧
            # 重读无意义,故重截图)。不根治(stylized 漏读),但把「读 0 不买」概率降到「连读 0 才认 0」。
            if state.gold == 0:
                for _ in range(4):
                    time.sleep(0.4)
                    gv = read_gold(self.ctx, self.screenshot())
                    if gv > 0:
                        state.gold = gv
                        break
            # task#105:优先 tracked_bench_chars(带 star+merge,mutate 同步);空(首轮)退 tracked_bench(旧 star 恒1)。
            if match.session.tracked_bench_chars:
                state.bench = deepcopy(match.session.tracked_bench_chars)  # copy 防下游 plan 污染持久态
                log.info(f'[cw] tracked_bench_chars(seed)={[(c.char_id, c.star) for c in state.bench]}')
            elif match.session.tracked_bench:
                state.bench = _tracked_bench_chars(match.session.tracked_bench)
                log.info(f'[cw] tracked_bench(旧 seed)={match.session.tracked_bench}')
            # 读 comp 成型度 —— overlay 时 board 不可读,用上次备战读的近似。
            match.session.last_state = state
            actions = match.strategy.decide_prep(state, match.session, config)
            # A2:target 由 session 管理(update_target 写),日志/telemetry 直接读 session.target_comp。
            target_name = match.session.target_comp.name if match.session.target_comp is not None else ''

            _fp_v = _form_progress(match.session.target_comp, state) if match.session.target_comp is not None else -1.0
            log.info(f'[cw] state gold={state.gold} hp={state.hp} lv={state.level} '
                     f'plane={state.plane} round={state.round_num} board={state.board} '
                     f'target={target_name!r} fp={_fp_v:.2f} bench={len(state.bench)}')
            log.info(f'[cw] shop={[(c.faction, c.name, c.cost) for c in state.shop]} '
                     f'plan={[self._fmt_action(a) for a in actions]}')
            cw_telemetry.record_decision(state, target_name, {}, {}, actions)   # 写本地 decisions.jsonl(含 A2 target)

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
                    time.sleep(0.8)   # 刷新动画
                    total_refresh += 1
                    did_refresh = True
            if not did_refresh:
                break   # 本轮无刷新(或硬墙)→ 买完收工

        # plan() 在最后一轮(无 refresh)的完整 actions 里含 DeployMove —— 取最后一次完整 plan 的 deploy moves。
        deploy_moves = [a for a in actions if isinstance(a, DeployMove)]
        if match is not None:
            match.session.pending_deploys = deploy_moves
            log.info(f'[cw-shop] 存 {len(deploy_moves)} 个 DeployMove 到 session(pending_deploys)')

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
        """
        if not self.round_by_ocr(screen, '备战席已满').is_success:
            return False
        level_btn = area_center(self.ctx, BuyShopCards.BUY_EXP_AREA) or BuyShopCards.LEVEL_UP_FALLBACK
        for _ in range(8):
            self.ctx.controller.click(level_btn)
            time.sleep(0.3)
        for sell_i in range(3):
            fresh = self.screenshot()
            if not self.round_by_ocr(fresh, '备战席已满').is_success:
                break
            bench_x = 438 + sell_i * 125  # bench-1..3 中心(横间距 ~125)
            self.ctx.controller.drag_to(end=Point(70, 846), start=Point(bench_x, 912), duration=0.8)
            time.sleep(1)
            for _ in range(4):
                self.ctx.controller.click(level_btn)
                time.sleep(0.3)
        return True
