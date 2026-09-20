"""部署动作 op(CwActionDeployMoveOp)——动作 op 重组批③ 换壳(原
``DeployMoveOp``,ActionOp ABC → 框架 SrOperation;机械执行后 **op 内
直调自己的上报函数** ``report_action_deploy_move_param``,零分派,
design.md §1.1/§1.2)。bench → 上阵单步拖拽(腾席链专用)。非终结。

机械执行零判效(用户裁定「动作 op = 机械执行」,落地判定归观察侧
reconcile 对账):拖后不做像素验证。拖拽静默不生效属执行环境噪声,由
下一入口 heavy 实读对账显影,重试 = 决策循环按新观察自然重派。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.deploy_move import (
    report_action_deploy_move_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionDeployMoveParam
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionDeployMoveOp(SrOperation):
    """bench → 上阵单步拖拽(腾席链专用;统一词表 CwActionDeployMoveParam)。
    非终结。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionDeployMoveParam,
                 env: PrepExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionDeployMoveOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='deploy_move', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """bench → 上阵单步拖拽。

        执行坐标边:源拖点 = ``bench_idx`` 备战栏 area 序直取(容器下标 =
        area 序,零换算);落位 = 载荷 (to_row, to_slot) 直指——排内 1 基
        画面槽号 → 对应排 area 序 ``to_slot - 1`` 取拖点(落位意图全部在
        载荷,执行边零现读零决定)。拖拽语义 = 游戏规则:目标槽空 = 放置,
        有人 = 交换交互——执行层不判断占位、不拒、禁静默换槽,唯一失败
        形态 = 拖拽未生效(机械发出零判效,由下一入口 heavy 实读对账
        显影,重试 = 决策循环按新观察自然重派);载荷槽越出画面槽位数 =
        陈旧载荷未发出(round_fail,观察重派)。faction 字段不入执行。

        发出即记账(用户裁定「动作 op = 机械执行」):拖拽发出后 tracked
        按载荷落位记账(tracked 同步与容器写侧同源,``_track_move_
        deployed``)+ 上报函数落容器;拖后零落地判定,静默不生效由下一
        入口观察对账显影。
        """
        action: CwActionDeployMoveParam = self.param
        env = self.env
        ex = env.executor
        row = action.to_row
        slot_no = int(action.to_slot)
        pts = ex._front_pts if row == 'front' else ex._back_pts
        if not (1 <= slot_no <= len(pts)):
            return self.round_fail(
                f'落位载荷越界(to_row={row}, to_slot={slot_no}, '
                f'画面槽位数={len(pts)};陈旧载荷,观察重派)')
        src = ex._bench_pts[action.bench_idx]
        dst = pts[slot_no - 1]
        ex._drag(src, dst)
        # 用户口述口径(screen_flow_timing.md #10,2026-09-02):拖动触发
        # 羁绊阶段变更时角色头顶徽章动画 ~2s——拖完立即返回会让批尾
        # heavy 观察打在徽章动画帧上(SIFT/对账读脏,「对账纠漂」日志
        # 噪声源之一)。按「都等 2s」简单方案落(批尾/中间的区分不做)。
        time.sleep(2.0)
        # 用户口述口径(#24,2026-09-02):羁绊达标触发的 overlay(盛会之星
        # 等)在徽章动画后再 ~2s 才弹出——固定等待覆盖不住。执行端等待后
        # 快查一次触发型 overlay 锚(模板毫秒级),命中 → detail 标注(拖拽
        # 本身已发出);批尾 heavy 的 event_overlay 检测将看到它并 bail 交
        # 外环 handler——防「decide 的下一步动作打在 overlay 上」。清单
        # 可扩(圣杯/银狼升星等实测出现时加锚)。
        _post = ex._op.screenshot()
        _overlay = ex._op.round_by_find_area(
            _post, '货币战争-盛会之星', '标识-盛会之星',
            crop_first=False).is_success
        if _overlay:
            log.info('[cw][deploy] 拖后检出盛会之星 overlay(羁绊达标触发)')
        # 发出即记账:拖拽发出即 tracked 按载荷落位记账(机械执行零判效;
        # 载荷槽 = 拖点,与容器写侧同源)。
        ex._track_move_deployed(action.bench_idx, row, slot_no)
        # —— 自上报(机械发出后;design.md §1.1)——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_deploy_move_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        if _overlay:
            return self.round_success('部署已发,盛会之星 overlay 弹出(外环接管)')
        return self.round_success(
            f'部署槽{action.bench_idx + 1}→{row}{slot_no} ✓'
            '(发出即记账,落地归观察对账)')
