"""刷新商店动作 op(CwActionRefreshShopOp)——动作 op 重组批③ 换壳
(ActionOp ABC → 框架 SrOperation;design.md §1.1/§1.2)。一 op 一文件。

**终结跳写语义长在动作自己身上**(design.md §1.1):本 op 是终结动作
(执行即本画面访问结束,期望态在新事实处由下段入口重观察重建),体内
**不调上报**(原「终结动作生产不写逻辑态」申报语义);sim/驱动器侧
照常直调上报函数(不经 op)。

免费刷新判定 = 对账类(比对收口纪律:判定随对账走,不随动作走):
本 op 只把刷前金/牌名与「待对账」标记落 ledger(坐标系与写入端声明见
ShopVisitLedger 字段注);比对与存证由下一段入口观察的对账点承接。
"""
from __future__ import annotations

import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_economy import REFRESH_COST_BASE
from sr_od.application.currency_war.kernel.cw_vocab import CwActionRefreshShopParam
from sr_od.application.currency_war.obs import cw_shop_refresh_obs
from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
    ShopExecEnv,
    _container_cards,
    _plane_of,
    _round_of,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

# 刷新点击后固定等待(重掷动画收敛):两帧指纹等稳门废弃后的
# 等待语义——固定时长即收,与买牌点击后固定 sleep 同风格的时长常量;
# 牌面/金真值判读不在动作内自证,交下一段入口观察(对账点)。
REFRESH_CLICK_SETTLE_WAIT_S: float = 1.0


class CwActionRefreshShopOp(SrOperation):
    """刷新 = 终结 op(决策 7:唯一引入新事实的动作,期望态必须在新事实
    处重建——终结后外循环入口重观察)。

    比对收口(裁决3):体内**零比对**——①免费刷新判定 = 对账类,只落
    对账件进 ledger,由下一段入口观察对账;②牌名集三值对比单一源 =
    ``cw_shop_refresh_obs.refresh_board_changed_of``,本 op 刷后只读不比、
    名集原样落账;③刷新期望对账迁入口观察对账点。「刷新是否生效」的
    判效权归观察侧 reconcile。体内不调上报(终结跳写,见模块头)。
    """

    #: 终结动作(执行即本画面访问结束,交回外循环)。
    terminal = True
    #: 终结交回等待秒数(无转移动画等待语义)。
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionRefreshShopParam,
                 env: ShopExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionRefreshShopOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='refresh_shop', is_start_node=True)
    def run(self) -> OperationRoundResult:
        # 读函数经 cw_op_buy_cards 模块属性路由(该模块的读点替身缝,
        # 测试 monkeypatch 面;自本模块直接 import 会绕开替身)。
        from sr_od.application.currency_war.operations.cw_screen import (
            cw_screen_buy_cards as _buy_cards_mod,
        )
        from sr_od.application.currency_war.operations.cw_screen.cw_screen_prep import (
            build_refresh_expect,
        )
        env = self.env
        op, _match, ledger, state = (env.op, env.match, env.ledger,
                                     env.state)
        ledger.refresh_attempted = True
        # 刷前现读两口径(执行边界压缩·连击共享往返):「仅刷新段」
        # (段内零先行动作)复用段顶整帧读;其余段点击前一帧现读金+牌名集
        # (`w592_free_refresh_fix/`:波内买卡不从 state.shop 摘已买牌,
        # plan 读 vs 点击后实读集合必不等,真落空会被洗成免费生效)。
        _pre_shop_names: list[str] | None = None
        _pre_gold: int | None = None
        _refresh_expect = None
        try:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                gold_of,
            )
            if ledger.refresh_first_action:
                _pre_gold = gold_of(state) if gold_of(state) > 0 else None
                _pre_shop_names = [c.name for c in _container_cards(state)
                                   if c.name]
            else:
                _pre_shot = op.screenshot()
                _pre_gold = _buy_cards_mod.read_gold_opt(op.ctx, _pre_shot)
                _pre_shop_names = [
                    s.card.name for s in (
                        _buy_cards_mod.read_shop_cards(op.ctx, _pre_shot)
                        or [])
                    if s.kind == 'content' and s.card and s.card.name]
            _refresh_expect = build_refresh_expect(
                _pre_gold, REFRESH_COST_BASE,
                [(c.name, c.star) for c in _container_cards(state)],
                _plane_of(state), _round_of(state))
        except Exception:   # noqa: BLE001  best-effort 不阻塞买牌
            _refresh_expect = None
        # 免费刷新对账件落账(判定收口到观察侧对账点,本 op 零比对;
        # 字段坐标系与写入端声明见 ShopVisitLedger)。失读字段照实落
        # None/空,对账点按腿判空放行(宁缺勿造)。期望 = 随账本
        # 外发(消费点 = 入口观察对账点 refresh_expect_mismatch 腿)。
        ledger.refresh_pre_gold = _pre_gold
        ledger.refresh_pre_names = list(_pre_shop_names or [])
        ledger.refresh_pending_reconcile = True
        ledger.refresh_expect = _refresh_expect
        # 刷前刷新钮真值读(读链接入):按钮三态 + 免费态剩余次数。
        # 经模块属性路由 = 测试替身缝(同 _buy_cards_mod 约定)。best-effort:
        # 识别层故障不阻塞执行链,ledger 字段保持 None = 免费闸回退逻辑账。
        _btn = None
        try:
            _btn = cw_shop_refresh_obs.read_shop_refresh_button(
                op.ctx, op.screenshot(), gold=_pre_gold)
        except Exception:   # noqa: BLE001  best-effort 不阻塞执行
            _btn = None
        if _btn is not None:
            ledger.refresh_free_truth = _btn.free
            ledger.refresh_free_remaining_truth = _btn.free_remaining
            log.info('[cw-shop] refresh button truth: free=%s remaining=%s '
                     'price=%s affordable=%s',
                     _btn.free, _btn.free_remaining, _btn.price, _btn.affordable)
        op.ctx.controller.click(env.refresh_btn)
        log.info(f'[cw-shop] Refresh click @({env.refresh_btn.x},'
                 f'{env.refresh_btn.y})')
        time.sleep(REFRESH_CLICK_SETTLE_WAIT_S)
        # 当次刷价进花销账(ADR-0456:实付恒基价;容器刷价在场用现值,
        # 未观察/0 = 回基价)。读数必须走 .value 读口——Field 直接进算术
        # = TypeError(实机 04:37 刷新首击即崩实证,店 env 容器化后此读
        # 点漏迁移)。
        _refresh_fee = state.shop_refresh_cost.value or REFRESH_COST_BASE
        ledger.spend_executed += _refresh_fee
        ledger.total_refresh += 1
        ledger.did_refresh = True
        try:
            _new_shop = _buy_cards_mod.read_shop_cards(op.ctx, op.screenshot())
            # 牌面现役归宿 = journal 快照行自带 shop 域。
            # 刷后牌名集原样落账(裁决3 比对收口:零比对——三值对比
            # 单一源 = cw_shop_refresh_obs.refresh_board_changed_of,消费方
            # = 刷新回执 extra(安灯豁免判定输入)与入口观察对账点免费腿;
            # 本 op 只读不比)。
            ledger.refresh_post_names = [
                s.card.name for s in (_new_shop or [])
                if s.kind == 'content' and s.card and s.card.name]
        except Exception:   # noqa: BLE001  快照 best-effort 不阻塞买牌
            pass
        # 终结跳写:体内不调上报(模块头申报;计数组由商店落地门接线)。
        return self.round_success(
            f'刷新已发(刷价 {_refresh_fee};终结交回,期望态下段入口重建)')
