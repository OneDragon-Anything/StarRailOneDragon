"""补给节点 pick 确认链动作 op(:class:`CwActionPickSupplyOp` 单类
文件,一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

机械语义:点卡选中 → 确认;确认点击后立即一口自上报完整结果
(``report_action_pick_supply_param``);动作回执簿记
(``_note_receipt``,两出口全簿记)照开/关商店动作 op 同形;刷新圆钮机械
点击留在画面 op。节点推进归出战动作(2026-10-29 流程模型对齐,见
run docstring)。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.pick_supply import (
    report_action_pick_supply_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
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
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl


def _note_receipt(op: SrOperation, reason: str, detail: str = '') -> None:
    """补给动作回执(receipts 域,渠道②,唯一写点 = kernel 口
    ``note_action_receipt``;reason = 动作事实码,'' = 已正常发出,
    词表见 kernel docstring)。

    两出口全簿记(每动作 op 恰一条回执行):确认点击已发 = reason='';
    实机确认定位缺失(动作没发出)= reason=定位缺失(按钮-确认)——
    失败可见性(exec_events 并入),journal 唯一直接痕迹。发出即簿记
    非验证(不读屏核验);journal 常开回执写入无条件,无局跳过在
    kernel 口。回执 op 名/actor 硬编码 ``'CwActionPickSupplyOp'``
    (journal 词表稳定,渲染器词表与类删除解耦);回执 screen = 动作
    发出画面(补给屏,全回执域统一语义,契约单一源 =
    game_state/fields.md 回执契约节)。detail = 机械摘要(idx +
    内容摘要)。
    """
    try:
        from sr_od.application.currency_war.kernel.cw_game_state import (
            game_state_from_ctx,
            note_action_receipt,
        )
        gs = game_state_from_ctx(getattr(op, 'ctx', None))
        if gs is None:
            return
        note_action_receipt(gs, op='CwActionPickSupplyOp',
                            reason=reason, screen='货币战争-补给',
                            actor='CwActionPickSupplyOp', detail=detail)
    except Exception as e:  # noqa: BLE001  回执失败不阻塞动作链
        log.warning('[cw][receipt] 补给回执写入失败(不阻塞): %s', e)


class CwActionPickSupplyOp(CwOperation):
    """补给节点 pick 确认链(统一动作工厂 迁入)。

    刷新圆钮机械点击留在画面 op(刷新链 = 刷新建议动作
    ``CwActionRefreshSupplyParam`` 的执行半)——pick execute 语义 =
    点卡选中 → 确认,不含刷新分支。
    **即时上报**(契约单一源 = `flow/action_ops.md` §1  与
    §4.5 PickSupply 行):确认点击后立即一口写全部效果逻辑态(owned 规范名
    + 单位入账分支 + 装备后果分支),无到账登记、无落地证据标志——确认未生效 =
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
        # else sim:机械执行分支静默成功(直连旁路 port 检查,flow-seam §2)
        time.sleep(0.6)
        # 确认(supply 按钮-确认 area;T#103 area 化)。点击即上报推进
        # (去证据门,用户裁定:动作 op 不做任何确认——点了
        # 就是上报,观察态门为唯一门;原「下一节点备战锚单探作上报时点门」
        # 随转移证据机制整体停用)。
        confirm_result = op.round_by_find_and_click_area(
            op.screenshot(), '货币战争-补给', '按钮-确认', success_wait=1.5)
        # 动作回执簿记(两出口全簿记,每执行恰一条回执行;形态先例 =
        # cw_op_open_shop.py::_note_receipt):实机确认定位缺失 =
        # 未发出事实码;sim 点击经端口受理恒按已发出簿记(reason='',
        # 不读 confirm 结果判读——屏门 retry 是转移后可见性语义)。
        # detail = idx + 内容摘要(char/norm_item,可空场景照实省略)。
        if cw_sim_ports.mechanical_io_allowed():
            receipt_reason = ('' if confirm_result.is_success
                              else '定位缺失(按钮-确认)')
        else:
            receipt_reason = ''
        detail = f'idx={action.idx}'
        if action.char_name:
            detail += f' char={action.char_name}'
        if action.norm_item:
            detail += f' item={action.norm_item}'
        _note_receipt(self, receipt_reason, detail)
        # 立即自上报完整结果(单相:owned += norm_item 规范名
        # + 单位入账分支 + 装备后果分支;norm_item 未解析 = 翻来源留存证据)。
        # 2026-10-29 流程模型对齐:确认后**不再上报节点推进**——游戏行为 =
        # 补给选完关闭 overlay 回备战并自动弹店,出战动作才完成节点
        #(流程模型单一源 = screen_flow_timing.md 口述流程模型节,#14);
        # 旧「确认点击落地即 report_node_advance(supply_confirm)」随该
        # 语义废止。round data 携带 pick_supply 声明(落点 = 商店档)。
        world_decl: WorldDecl | None = None
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            pick_outcome = report_action_pick_supply_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
            world_decl = pick_outcome.world_decl
            cw_sim_ports.declare_world(world_decl)
        # 选定事实现役归宿 = journal chosen 域(handler 派发前写)。
        return self.round_success('补给选择确认链已发(结果已即时上报)',
                                  data=world_decl)
