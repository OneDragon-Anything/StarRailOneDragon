"""买经验动作 op(CwActionLevelUpOp)——动作 op 重组批③ 换壳(原
``PrepLevelUpOp``,ActionOp ABC → 框架 SrOperation;机械执行后 **op 内
直调自己的上报函数** ``report_action_level_up_param``,零分派,design.md
§1.1/§1.2)。R6 定案④逐帧单击形态。非终结。

命名申报:``CwActionLevelUpParam``/``CwActionLevelUpShopParam`` 同字段双
类型共用本 op(注册表两行同指,上报 = 同一函数;原商店域
``cw_level_up_action.LevelUpOp`` 生产不可达,随批③文件删除)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.level_up import (
    report_action_level_up_param,
)
from sr_od.application.currency_war.kernel.cw_economy import (
    XP_CLICK_COST_FALLBACK,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_vocab import CwActionLevelUpParam
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionLevelUpOp(SrOperation):
    """买经验(R6 逐帧单击形态:找钮 → 单击 → 固定等待,零授权零计数)。
    非终结。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionLevelUpParam,
                 env: PrepExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionLevelUpOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='level_up', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """买经验单击(R6 逐帧单击形态:找钮 → 单击 → 固定等待)。

        执行器授权面全删(design.md unified-action-factory §2.6 粒度定案):
        授权击数推导/血闸整级授权/逐击金地板全部上移发射位(kernel
        ``clicks_to_next_level`` 现算击数 > 0 = 每帧发射前置)。升 N 击 =
        N 帧(决策循环逐帧重组,单击形态)。

        经验/等级/金真值 = 上报函数单点直写(单击击数自算 = 1;金腿 =
        ``action.cost`` 直写,cost = 发射面 xp_click_cost 现算装载)+ 下一帧
        观察对账族双通道。单击价本处现算仅作 detail 显影。
        """
        action: CwActionLevelUpParam = self.param
        env = self.env
        ex = env.executor
        match = ex._ctx.cw_match
        session = match.session if match is not None else None
        from sr_od.application.currency_war.kernel.cw_economy import (
            xp_click_cost,
        )
        btn = area_center(ex._ctx, '备战标识-购买经验') or Point(296, 860)
        # 单击价容器读口(kernel 单一源,失读回退兜底价;与假环境执行缝同式)
        _price = XP_CLICK_COST_FALLBACK
        if session is not None:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                game_state_of,
            )
            _price = xp_click_cost(game_state_of(session))
        ex._ctx.controller.mouse_move(btn)   # bug#1 缓解(review M-5)
        ex._ctx.controller.click(btn)
        # 光标 parking(审计 P0,2026-08-16 = M38 level 毒化注入点):按钮距等级显示区 18px,
        # 点击后光标压住 Lv.N 区 → 下帧 OCR 读错(4 毒化 3 位面的链头)。park 后再继续。
        ex._op.park_cursor(before_wait=0.3, after_wait=0.15)
        # W612 挂点A(升级事件;发出即登记,观测 best-effort,零决策语义)。
        try:
            if session is not None:
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    game_state_of,
                )
                game_state_of(session).effects.on_level_up()
        except Exception as e:   # noqa: BLE001  观测失败不阻塞对局
            log.warning('[cw][levelup] effect inventory 挂点失败(不阻塞): %s', e)
        # —— 自上报(机械发出后;design.md §1.1):单击击数自算 = 1 ——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_level_up_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        detail = (f'买经验单击 1 击花金{_price}'
                  '(逐帧单击形态;级真值=下一帧观察 reconcile)')
        log.info(f'[cw][levelup] {detail}')
        return self.round_success(detail)
