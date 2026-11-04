"""开补给箱动作 op(CwActionOpenBoxOp)——状态容器槽位直点形态:op 对画面
零识别(动作 op 无论执行前还是执行后都不做观察识别,规范 =
flow/action_ops.md 用户裁定),机械链 = 参数校验 → 槽号解析 → 建档坐标
直查 → mouse_move+click → 自上报 → round_success。机械执行后 **op 内
直调自己的上报函数** ``report_action_open_box_param``(零写族),零分派,
op-layer.md §1.2 动作 op 契约。

终结动作(R7 终结化):点完「开启」本动作即返回主循环,武装箱选择
画面由外循环按画面分发独立画面 op 选卡。terminal_wait = 开箱动画等待,
与 runner 包络 ``_OVERLAY_ANIM_WAIT_S`` 等价(等价测试 =
test_action_registry 终结集测试)。
"""
from __future__ import annotations

import time
from dataclasses import replace
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.zero_writes import (
    report_action_open_box_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_vocab import CwActionOpenBoxParam
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv

#: slot=None 现算消费的状态容器占席 kind(坐标系 = 状态容器 BenchSlot.kind,
#: 简易武装箱历史代号保留)。现算规则 = 状态容器 bench 首个该 kind 槽
#: (下标 + 1);决策层(mandate_v1/entry.py 消耗品臂)与上报层
#: (kernel/cw_action_report/open_tome.py 等)各有一份同型现算,三处
#: 语义必须一致(同状态容器同规则),提取公共函数归另批。
_BOX_BENCH_KIND = 'supply_box'


class CwActionOpenBoxOp(CwOperation):
    """开箱:槽号解析 → 点「开启」建档坐标 → 固定动画等待(纯机械执行)。

    选卡动作不在本执行链(R7 定形):点完开启本动作即终结
    ——武装箱选择画面由外循环按画面分发独立画面 op(:mod:`cw_screen_box_pick`)
    选卡(选卡决策单一源 = 策略 ``decide_box_card`` 契约 / 局外 kernel
    ``pick_equipment`` 机器)。等待归产生动画的操作,弹窗就位与否交
    下一帧观察。
    """

    #: 终结动作(开箱即引入新事实,返回主循环分发选卡)。
    terminal = True

    #: 返回等待 = 开箱动画等待值(与 prep_actions._OVERLAY_ANIM_WAIT_S
    #: 逐字等价,漂移由等价测试暴露)。
    terminal_wait = 1.8

    def __init__(self, ctx: SrContext, param: CwActionOpenBoxParam,
                 env: PrepExecEnv):
        CwOperation.__init__(self, ctx, op_name='CwActionOpenBoxOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='open_box', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行;终结动作(返回等待归消费点按 ``terminal_wait`` 读)。"""
        action: CwActionOpenBoxParam = self.param
        env = self.env
        ex = env.executor
        if action.slot is not None and not (1 <= action.slot <= len(ex._bench_pts)):
            # 参数违法由 op 自判(flow/action_ops.md §1 决策侧参数现算
            # 契约):slot = 画面物理槽 1 基(可选参数,None = 状态容器现算
            # 首件槽),越界响亮暴露零点击。
            raise AssertionError(
                f'CwActionOpenBoxParam slot={action.slot} 越界'
                f'(1-{len(ex._bench_pts)})')
        gs = None
        if action.slot is None:
            # slot=None 缺省语义 = game state 状态容器现算首件槽号(消费决策
            # 数据,与决策层同源,非画面识别);双出口守卫断言(gs 缺席 /
            # 状态容器无该 kind 首槽)与越界同款响亮暴露零点击。
            gs = game_state_from_ctx(self.ctx)
            if gs is None:
                raise AssertionError(
                    'CwActionOpenBoxParam slot=None 现算失败:game state '
                    '缺席(无局/容器供给 None),零点击')
            view = gs.bench.value
            slots = list(view.slots) if view is not None else []
            idx = next((i for i, s in enumerate(slots)
                        if s is not None and s.kind == _BOX_BENCH_KIND), None)
            if idx is None:
                raise AssertionError(
                    'CwActionOpenBoxParam slot=None 现算失败:容器 bench 无 '
                    f'kind={_BOX_BENCH_KIND} 首件槽,零点击')
            slot = idx + 1
            # 落地机制 = 以现算 resolved slot 重建 param(不改写入参对象):
            # 上报/journal/round 摘要显示显式槽号。
            action = replace(action, slot=slot)
        else:
            slot = action.slot
        # 建档坐标直查(「点哪能开」= 开启按钮位置,实测定准进建档;
        # screen_info 单一真相源,禁 fallback 推算——area 缺失 = 取值
        # 直接使用,点击消费点自然异常,零防御口径)。
        open_point = area_center(ex._ctx, f'武装箱开启位-{slot}')
        if cw_sim_ports.mechanical_io_allowed():
            ex._ctx.controller.mouse_move(open_point)   # 防吞点击
            ex._ctx.controller.click(open_point)
        # else sim:机械执行分支静默成功(直连旁路 port 检查,flow-seam §2)
        # 固定动画等待(等待归产生动画的操作;弹窗就位与否交下一帧观察)
        from sr_od.application.currency_war.prep_actions import (
            _OVERLAY_ANIM_WAIT_S,
        )
        time.sleep(_OVERLAY_ANIM_WAIT_S)
        log.info(f'[cw][box] 开箱槽{slot} → 点开启已发(交回外循环,武装箱'
                 '选择画面分发选卡)')
        # —— 自上报(机械发出后;零写族,op-layer.md §1.2)——
        # 上报后一行声明喂入(动作后果声明化喂入契约 = design.md §2.2
        # 契约 3;实机端口未装 = no-op,sim 装配后驱动后端 open_box);
        # round data 携带声明(journal 记账面)。
        world_decl = None
        if gs is None:
            gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            outcome = report_action_open_box_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
            world_decl = outcome.world_decl
            cw_sim_ports.declare_world(world_decl)
        return self.round_success(f'开箱槽{slot}', data=world_decl)
