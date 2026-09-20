"""买牌动作 op(CwActionBuyCardOp)——动作 op 重组批③ 换壳
(ActionOp ABC → 框架 SrOperation,构造 = (ctx, param, env);机械执行后
**op 内直调自己的上报函数** `report_action_buy_card_param`,零分派,
design.md §1.1/§1.2)。一 op 一文件。

机械执行零判效(用户裁定「动作 op = 机械执行」,落地判定归观察侧
reconcile 对账):点击后零像素验证,发出即记账。点击静默不生效属执行
环境噪声,由下一入口 heavy 实读对账显影(shop+gold 失配 → 安灯停 →
按真 bug 修),重试 = 决策循环按新观察自然重派。买前裁片 = 纯留证零判效。
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
    _area_rect,
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
        from one_dragon.base.geometry.point import Point as _Pt
        action: CwActionBuyCardParam = self.param
        env = self.env
        op, match, ledger, state = env.op, env.match, env.ledger, env.state
        # 点击定位 = 牌自带物理槽号 slot(读链写入)→ screen_info
        # 「商店牌-N」现取(W6 波 4 双 ShopCard 归一:容器牌无 x 坐标,
        # 坐标单一真相源 = screen_info,设计件 §2.5-5)。身份匹配优先
        # 同一性(action 由决策核自 payload 产出),退化按 (name, star)
        # ——匹配下标仅作槽号缺失时的兜底锚,见下方点击解析。
        # 槽号主源 = payload 定长槽阵列位置(三态模型:数组下标+1 =
        # 物理槽;身份同一性优先,退化 (name, star));card.slot 兼容
        # 字段降为最后兜底(退役面审计)。
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
        # 点击坐标 = 牌自带实测槽位(观察期读链写入的物理槽号)→ screen_info
        # 「商店牌-N」中心。紧凑下标只在牌行满列期与物理槽位等价:游戏买入
        # 后不压缩剩余卡位(牌行打洞),紧凑列表全体下标偏离物理槽位,按下标
        # 取固定槽坐标 = 点击落空槽框(实机局实证:1 槽空、卡在 2-5 槽时恒打
        # 1 槽框,「买牌点击不注册」根因;布局双源同族 = ADR-0646 bench 布局
        # 错位的商店牌行版)。槽号缺省(0 = sim/离线构造、修复前旧档)退回
        # 紧凑下标映射(旧行为)。
        _slot_no = _slot_no_matched
        if _slot_no is None:
            # 兼容兜底:旧档/sim 构造牌的 slot 字段(退役过渡期保留)
            _slot_no = int(getattr(action.card, 'slot', 0) or 0)
        if 1 <= _slot_no <= len(env.click_pts):
            pt = env.click_pts[_slot_no - 1]
        else:
            pt = (_Pt(0, 288) if not env.click_pts else env.click_pts[0])
        # 买前裁该片矩形拷贝(纯留证零判效:`w536_merge_expect/`「买了什么」
        # 的像素级证据,随期望态带到对账点;一帧原则,必须 copy 防帧缓存
        # 覆写)。
        _card_crop = None
        _frame = None
        with contextlib.suppress(Exception):
            _frame = op.screenshot()
            for _i in range(1, 6):
                _r = _area_rect(op.ctx,
                                f'{A_SHOP_CARD_PREFIX}{_i}',
                                SHOP_SCREEN_NAME)
                if _r is not None and _r.x1 <= pt.x <= _r.x2:
                    if _frame is not None:
                        _card_crop = _frame[_r.y1:_r.y2, _r.x1:_r.x2].copy()
                    break
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
            # (unit+占位件均占席,与旧 bench_slots_of→bench_occupied 同式);
            # 旧执行缝腿的数据源 = tracked 主账(_books)。
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
                count=_cnt, unit_cost=action.card.cost or 0,
                crop=_card_crop))
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
