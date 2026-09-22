"""买牌动作 op(CwActionBuyCardOp)——动作 op 重组批③ 换壳
(ActionOp ABC → 框架 SrOperation,构造 = (ctx, param, env);机械执行后
**op 内直调自己的上报函数** `report_action_buy_card_param`,零分派,
design.md §1.1/§1.2)。一 op 一文件。

机械执行零判效(用户裁定「动作 op = 机械执行」,落地判定归观察侧
reconcile 对账):点击后零像素验证零读屏,发出即记账。点击静默不生效属
执行环境噪声,由下一入口 heavy 实读对账显影(shop+gold 失配 → 安灯停 →
按真 bug 修),重试 = 决策循环按新观察自然重派。
"""
from __future__ import annotations

import contextlib
import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.buy_card import (
    report_action_buy_card_param,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    BENCH_CAPACITY,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    ShopActionExecuted,
    game_state_from_ctx,
    shop_payload_content_cards,
)
from sr_od.application.currency_war.kernel.cw_merge_simulate import merge_buy_k
from sr_od.application.currency_war.kernel.cw_obs_core import (
    A_SHOP_CARD_PREFIX,
    SHOP_SCREEN_NAME,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import (
    strategy_state_of,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionBuyCardParam,
    mutate_bench_deployed,
)
from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
    ShopExecEnv,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwActionBuyCardOp(SrOperation):
    """买一张 = 一个动作 op(满栏例外下一击多张仍一个 op,张数由游戏
    规则定、上报按 merge_buy_k 计——方案 A 补裁)。

    自上报(design.md §1.1):机械发出后直调
    ``report_action_buy_card_param``,executed.bought_count 直接取
    ``ledger.buy_purchases[-1]``(执行落地事实,单一源);出参
    LogicOutcome 忽略(live 调用点忽略出参 = 行为零变化)。
    """

    #: 非终结动作(每类显式声明,无基类缺省;design.md §1.1)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionBuyCardParam,
                 env: ShopExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionBuyCardOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='buy_card', is_start_node=True)
    def run(self) -> OperationRoundResult:
        action: CwActionBuyCardParam = self.param
        env = self.env
        op, match, ledger, state = env.op, env.match, env.ledger, env.state
        # 点击定位解析恰两档 = 契约(action_exec.md §4 / action_ops.md
        # §4.1 同口径):①payload 定长槽阵列身份同一性(action 由决策核自
        # payload 产出,`is` 匹配)②(name, star) 退化。槽号主源 = payload
        # 定长槽阵列位置(三态模型:数组下标+1 = 物理槽)。card.slot 旧档
        # 字段兜底已删:静默兜底把「payload 无此牌」的提案数据 bug 掩盖成
        # 错槽点击,显式失败促数据修正(错槽根因家族 = 布局双源:旧档
        # 下标 ≠ 物理槽位)。
        _slot_no_matched = None
        _payload = state.shop.value
        _slots = (_payload.cards if _payload is not None else [])
        for _i, _s in enumerate(_slots):
            if _s.kind == 'content' and _s.card is not None \
                    and _s.card is action.card:
                _slot_no_matched = _i + 1
                break
        if _slot_no_matched is None:
            for _i, _s in enumerate(_slots):
                if _s.kind == 'content' and _s.card is not None \
                        and (_s.card.name or '') == (action.card.name or '') \
                        and int(_s.card.star or 1) == int(action.card.star or 1):
                    _slot_no_matched = _i + 1
                    break
        # 点击坐标 = payload 槽号 → screen_info「商店牌-N」中心。紧凑下标
        # 只在牌行满列期与物理槽位等价:游戏买入后不压缩剩余卡位(牌行
        # 打洞),紧凑列表全体下标偏离物理槽位,按下标取固定槽坐标 = 点击
        # 落空槽框(实机局实证:1 槽空、卡在 2-5 槽时恒打 1 槽框,「买牌
        # 点击不注册」根因;布局双源同族 = bench 布局错位的商店牌行版)。
        _slot_no = _slot_no_matched
        if _slot_no is None:
            # 槽解析失败(①②双未命中)= payload 无此牌,提案数据 bug
            # 响亮暴露:round_fail = 未发出事实(action_ops.md §2.1),
            # 零动作级重试,决策循环按下一帧观察自然重派。
            return self.round_fail(
                '商店牌槽解析失败:slot_no=None'
                '(身份未命中 ∧ (name,star) 未命中),禁兜底点击')
        if not (1 <= _slot_no <= len(env.click_pts)):
            # 槽号越界/点位缺失 = 槽号-点表不一致(建档漂移/数据漂移上游
            # 显影),显式 round_fail(信息带 area 名,与 level_btn/refresh_btn
            # 同款纪律),禁兜底坐标静默点击(坐标单一真相源)。
            return self.round_fail(
                f'商店牌槽号越界/点位缺失:{A_SHOP_CARD_PREFIX}'
                f'{_slot_no}({SHOP_SCREEN_NAME}),slot={_slot_no} '
                f'click_pts={len(env.click_pts)}(槽号-点表不一致),'
                f'禁兜底点击')
        pt = env.click_pts[_slot_no - 1]
        op.ctx.controller.click(pt)
        log.info(f'[cw-shop] Buy click slot={_slot_no} @({pt.x},{pt.y}) '
                 f'{action.card.faction}/{action.card.name}/'
                 f'{action.card.cost}')
        time.sleep(0.4)
        ledger.total_buy += 1
        ledger.spend_executed += action.card.cost
        if action.card.name:
            ledger.bought_names.append(action.card.name)
            # 撤销操作证据留存(纯观测,零行为变更):体系成员买入不重置
            # 干旱计数(重置单一源 = 商店可见性 _update_pair_drought),
            # 解锁流程审计面落台账。复用 defect_ledger,异常不阻断买入。
            with contextlib.suppress(Exception):
                _ist_e = getattr(strategy_state_of(match.session), 'v3_intention', None)
                _pd = getattr(_ist_e, 'pair_drought', None)
                if isinstance(_pd, dict):
                    from sr_od.application.currency_war.kernel.cw_intention import (
                        members_in_shop,
                    )
                    from sr_od.application.currency_war.telemetry.undo_evidence import (
                        record_drought_buy_no_reset,
                    )
                    for _sys, _d in _pd.items():
                        if _d and _sys and members_in_shop(
                                _sys, {action.card.name}):
                            record_drought_buy_no_reset(
                                member=action.card.name,
                                system=_sys, drought=_d)
        # tracking 同步:满栏合成买与逻辑态直写同分支单一源(shop 视图
        # 进 tracked mutate,满栏完成合成的买入在 tracked 侧同样合成腾槽
        # ——旧丢件行为使 tracked 漏记合成,同 visit 下一动作守卫对拍
        # 误炸;2026-09-09 05:52 运行局双响事故)。
        _payload_cards = (shop_payload_content_cards(state.shop.value)
                          if state.shop.value is not None else [])
        from sr_od.application.currency_war.kernel.cw_game_state import (
            game_state_of as _gso_buy,
        )
        _books = _gso_buy(match.session).tracked_books
        mutate_bench_deployed(_books.bench, _books.deployed,
                              action, shop=_payload_cards)
        if action.card.name:
            _cnt = 1
            # 满栏判定(容器原生读):席占用 = BenchView 槽 kind ≠ empty
            # (unit+占位件均占席);旧执行缝腿的数据源 = tracked 主账(_books)。
            _view = state.bench.value
            _bench_occ = (sum(1 for s in _view.slots if s.kind != 'empty')
                          if _view is not None else 0)
            if _bench_occ >= BENCH_CAPACITY:
                # 满栏例外(merge_mechanics §2.5 方案 A):一击多张,张数
                # 单一源 = merge_buy_k(禁执行侧重算);金账无折扣 = 总价
                # k×单价,执行账补差 (k−1)×单价。
                _cnt = max(1, merge_buy_k(
                    action.card.name, action.card.star or 1,
                    (list(_view.slots) if _view is not None else []),
                    _books.deployed,
                    _payload_cards))
                ledger.spend_executed += (action.card.cost or 0) * (_cnt - 1)
            from sr_od.application.currency_war.kernel.cw_prep_expect import (
                BuyPurchase,
            )
            ledger.buy_purchases.append(BuyPurchase(
                name=action.card.name, star=action.card.star,
                count=_cnt, unit_cost=action.card.cost or 0))
        # —— 自上报(机械发出后;design.md §1.1):k 取执行落地事实 ——
        _k = 1
        if action.card.name and ledger.buy_purchases:
            _k = max(1, int(ledger.buy_purchases[-1].count or 1))
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_buy_card_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'),
                executed=ShopActionExecuted(bought_count=_k))
        return self.round_success(
            f'买牌 slot={_slot_no} {action.card.name or "?"}×{_k}')
