"""开秘密典籍动作 op(CwActionOpenTomeOp)——容器槽位直点形态:op 对
画面零识别(动作 op 无论执行前还是执行后都不做观察识别,规范 =
flow/action_ops.md 用户裁定),机械链 = 参数校验 → 槽号解析 → 建档坐标
直查 → mouse_move+click → 自上报 → round_success。机械执行后 **op 内
直调自己的上报函数** ``report_action_open_tome_param``,零分派,
op-layer.md §1.2 动作 op 契约。非终结:单击开典籍后星徽四选一 overlay
弹出,选卡交外循环 CwScreenBookcard 接管(overlay 检出走环中止交外环
handler,非本动作终结语义)。单击化 = 用户确认 2026-09-25 游戏实际 =
点典籍槽一次即弹(原双击序列的第二击落在已弹出的弹窗上有误触风险)。"""
from __future__ import annotations

import time
from dataclasses import replace
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.open_tome import (
    report_action_open_tome_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_vocab import CwActionOpenTomeParam
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv

#: slot=None 现算消费的容器占席 kind(坐标系 = 容器 BenchSlot.kind)。
#: 现算规则 = 容器 bench 首个该 kind 槽(下标 + 1);决策层
#: (mandate_v1/entry.py 消耗品臂)与上报层(本动作上报函数内)各有一份
#: 同型现算,三处语义必须一致(同容器同规则),提取公共函数归另批。
_TOME_BENCH_KIND = 'tome'


class CwActionOpenTomeOp(CwOperation):
    """开秘密典籍:槽号解析 → 单击典籍槽(建档坐标)→ 固定动画等待。
    非终结。

    单击化(用户确认 游戏实际 = 单击
    即弹;原双击序列的第二击落在已弹出的弹窗上有误触风险):
    实机核凭据 = 待实机局 journal(代码批先落地,实机验证随迭代收尾,
    )。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionOpenTomeParam,
                 env: PrepExecEnv):
        CwOperation.__init__(self, ctx, op_name='CwActionOpenTomeOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='open_tome', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """槽号解析 → 单击典籍槽即开启(单击化 = 用户确认 游戏实际,
        双击序列的第二击落在已弹弹窗上有误触风险;实机核凭据 = 待实机
        局 journal);弹窗后外循环分发 CwScreenBookcard
        接管选卡(本动作不选 —— 选卡是策略决策,板上阵营匹配在 CwScreenBookcard)。
        等待归产生动画的操作,弹窗就位与否交下一帧观察(外循环分发重判)。
        """
        action: CwActionOpenTomeParam = self.param
        env = self.env
        ex = env.executor
        if action.slot is not None and not (1 <= action.slot <= len(ex._bench_pts)):
            # 参数违法由 op 自判(flow/action_ops.md §1 决策侧参数现算
            # 契约):slot = 画面物理槽 1 基(可选参数,None = 容器现算
            # 首件槽),越界响亮暴露零点击。
            raise AssertionError(
                f'CwActionOpenTomeParam slot={action.slot} 越界'
                f'(1-{len(ex._bench_pts)})')
        gs = None
        if action.slot is None:
            # slot=None 缺省语义 = game state 容器现算首件槽号(消费决策
            # 数据,与决策层同源,非画面识别);双出口守卫断言(gs 缺席 /
            # 容器无该 kind 首槽)与越界同款响亮暴露零点击。
            gs = game_state_from_ctx(self.ctx)
            if gs is None:
                raise AssertionError(
                    'CwActionOpenTomeParam slot=None 现算失败:game state '
                    '缺席(无局/容器供给 None),零点击')
            view = gs.bench.value
            slots = list(view.slots) if view is not None else []
            idx = next((i for i, s in enumerate(slots)
                        if s is not None and s.kind == _TOME_BENCH_KIND), None)
            if idx is None:
                raise AssertionError(
                    'CwActionOpenTomeParam slot=None 现算失败:容器 bench 无 '
                    f'kind={_TOME_BENCH_KIND} 首件槽,零点击')
            slot = idx + 1
            # 落地机制 = 以现算 resolved slot 重建 param(不改写入参对象):
            # 上报/journal/round 摘要显影显式槽号。
            action = replace(action, slot=slot)
        else:
            slot = action.slot
        # 建档坐标直查(点击点 = 槽位本体中心,screen_info 单一真相源,
        # 禁 fallback 推算——area 缺失 = 取值直接使用,点击消费点自然
        # 异常,零防御口径)。
        center = area_center(ex._ctx, f'备战栏-{slot}')
        if cw_sim_ports.mechanical_io_allowed():
            ex._ctx.controller.mouse_move(center)   # 防吞点击
            ex._ctx.controller.click(center)        # 单击:开启即弹
        # else sim:机械执行分支静默成功(直连旁路 port 检查,flow-seam §2)
        # 固定动画等待(等待归产生动画的操作;弹窗就位与否交下一帧观察)
        from sr_od.application.currency_war.prep_actions import (
            _OVERLAY_ANIM_WAIT_S,
        )
        time.sleep(_OVERLAY_ANIM_WAIT_S)
        log.info(f'[cw][tome] 开典籍槽{slot} → 单击已发(选卡交 CwScreenBookcard)')
        # —— 自上报(机械发出后;op-layer.md §1.2):开件腾位 ——
        if gs is None:
            gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_open_tome_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        return self.round_success(f'开典籍槽{slot}')
