"""刷新商店动作 op(CwActionRefreshShopOp)——动作 op 重组批③ 换壳
(ActionOp ABC → 框架 SrOperation;design.md §1.1/§1.2)。一 op 一文件。

**终结跳写(收窄申报,2026-09-18 用户裁决)**:金与刷后牌面仍不写
(观察覆盖,期望态在新事实处由下段入口重观察重建);**刷新计数由本 op
自上报统一触发**(`report_action_refresh_shop_param`:付费/全量计数经
``gs.effects.record_refresh`` 单口;免费腿 = 容器字段
``gs.free_refresh_left`` Field 判定与扣减,2026-09-21 Field 化——未观察
保守按付费;本 op 零读屏喂真值,T-13 真值通道已退役)。sim/驱动器侧
照常直调同一上报函数。
"""
from __future__ import annotations

import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_economy import REFRESH_COST_BASE
from sr_od.application.currency_war.kernel.cw_vocab import CwActionRefreshShopParam
from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
    ShopExecEnv,
    _container_cards,
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

    体内零比对零验证(动作 op 机械执行纪律):免费刷新判定 = 容器 Field
    值(上报函数承载,见模块头);牌名集三值对比单一源 =
    ``cw_shop_refresh_obs.refresh_board_changed_of``,本 op 刷后只读不比、
    名集原样落账。「刷新是否生效」的判效权归观察侧 reconcile。计数自上报
    = 效果账本统一触发(见模块头);金不写,payload 随机态由上报函数
    write_logic_rand 采样(观察覆盖,观察赢)。
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
        except Exception:   # noqa: BLE001  best-effort 不阻塞买牌
            pass
        # 免费刷新对账件落账(字段坐标系与写入端声明见 ShopVisitLedger;
        # 消费与清点归后续零读屏清理批,本 op 保持只写不比)。失读字段照
        # 实落 None/空(宁缺勿造)。
        ledger.refresh_pre_gold = _pre_gold
        ledger.refresh_pre_names = list(_pre_shop_names or [])
        ledger.refresh_pending_reconcile = True
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
            # 刷后牌名集原样落账(只读不比;消费面归后续零读屏清理批)。
            ledger.refresh_post_names = [
                s.card.name for s in (_new_shop or [])
                if s.kind == 'content' and s.card and s.card.name]
        except Exception:   # noqa: BLE001  快照 best-effort 不阻塞买牌
            pass
        # 自上报 = 刷新计数统一触发 + Field 免费腿扣减 + payload 随机态
        # 采样(见模块头与上报函数 docstring)。free 传 None = 上报函数
        # Field 值判定(T-13 真值通道退役);金账不喂(生产观察覆盖)。
        from sr_od.application.currency_war.kernel.cw_action_report.refresh_shop import (
            report_action_refresh_shop_param,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            ChannelSig,
            game_state_from_ctx,
        )
        _gs_rpt = game_state_from_ctx(self.ctx)
        if _gs_rpt is not None:
            report_action_refresh_shop_param(
                _gs_rpt, self.param,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        # 终结交回:金与牌面真值不写(观察覆盖),期望态下段入口重建。
        return self.round_success(
            f'刷新已发(刷价 {_refresh_fee};终结交回,期望态下段入口重建)')
