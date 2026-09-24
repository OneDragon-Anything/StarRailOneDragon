"""补给节点 pick 确认链动作 op(:class:`CwActionPickSupplyOp` 单类
文件,一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

机械语义:点卡选中 → 确认;确认点击后立即一口自上报完整结果
(``report_action_pick_supply_param``)+ 节点推进上报;刷新圆钮机械
点击留守画面 op。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_action_report.pick_supply import (
    report_action_pick_supply_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
    report_node_advance,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickSupplyParam,
)
from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
    OverlayPickExecEnv,
)
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl


class CwActionPickSupplyOp(CwOperation):
    """补给节点 pick 确认链(统一动作工厂批4 迁入)。

    刷新圆钮机械点击留守画面 op(刷新链 = 刷新建议动作
    ``CwActionRefreshSupplyParam`` 的执行半)——pick execute 语义 =
    点卡选中 → 确认,不含刷新臂。
    **即时上报**(契约单一源 = `flow/action_ops.md` §1 增补 2 与
    §4.5 PickSupply 行):确认点击后立即一口写全部效果逻辑态(owned 规范名
    + 单位腿 + 装备后果腿),无到账登记、无落地证据闩——确认未生效 =
    代码 bug,overlay 残留由外循环按当前画面重识别重派。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickSupplyParam,
                 env: OverlayPickExecEnv):
        CwOperation.__init__(self, ctx, op_name='CwActionPickSupplyOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_supply', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点卡 → 固定等待 → 确认 → 立即上报完整结果;零判效)。"""
        action = self.param
        env = self.env
        op = env.op
        target = env.target
        if cw_sim_ports.mechanical_io_allowed():
            op.ctx.controller.mouse_move(target)
            op.ctx.controller.click(target)
        # else sim:机械腿静默成功(直连旁路 port 检查,flow-seam §2)
        time.sleep(0.6)
        # 确认(supply 按钮-确认 area;T#103 area 化)。点击即上报推进
        # (去证据门,用户裁定 2026-09-21:动作 op 不做任何确认——点了
        # 就是上报,观察态门为唯一门;原「下一节点备战锚单探作上报时点门」
        # 随转移证据机制整体退役)。
        confirm_result = op.round_by_find_and_click_area(
            op.screenshot(), '货币战争-补给', '按钮-确认', success_wait=1.5)
        # 立即自上报完整结果(单相:owned += norm_item 规范名
        # + 单位腿 + 装备后果腿;norm_item 未解析 = 翻来源留证)。
        # 一次执行两支上报、每支出口各自紧跟一行喂入(A2 多支并喂契约 =
        # 详设 world-decl.md §4);round data 携带最后一份(node_advance,
        # 终结转移),先前声明仅经端口喂入不随 data 重复。
        world_decl: WorldDecl | None = None
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            # 支 1:pick_supply 宝钻腿上报(拒/未发出出口声明 None →
            # 喂入端口层 no-op;声明契约 = 详设 world-decl.md §2 表 #12)。
            pick_outcome = report_action_pick_supply_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
            cw_sim_ports.declare_world(pick_outcome.world_decl)
            # 支 2:节点推进上报(supply_confirm):确认点击落地即上报,重复上报
            # 被 kernel 观察态门结构性挡;局外 gs 缺席同跳过(best-effort)。
            if confirm_result.is_success:
                advance_outcome = report_node_advance(
                    gs, trigger='supply_confirm')
                world_decl = advance_outcome.world_decl
                cw_sim_ports.declare_world(world_decl)
        # 选定事实现役归宿 = journal chosen 域(handler 派发前写)。
        return self.round_success('补给选择确认链已发(结果已即时上报)',
                                  data=world_decl)
