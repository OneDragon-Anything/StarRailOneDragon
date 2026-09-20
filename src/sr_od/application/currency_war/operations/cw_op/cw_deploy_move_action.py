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
    game_state_of,
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
        area 序,零换算);落位排 = ``to_row``,落位物理槽 = tracked 占用
        现读首空位(§2.1 下标派生口径:tracked deployed = 定长 10 下标表,
        空槽 = 表项 None,排内槽号 = ``deployed_slot_no`` 派生——与上报
        函数 ``place_unit_in_deployed`` 选排规则逐位同构:首选排满
        fallback 另一排)。两排全满 = 未发出(round_fail,观察重派);
        faction 字段不入执行。

        发出即记账(用户裁定「动作 op = 机械执行」):拖拽发出后 tracked
        记上阵 + 上报函数落容器;拖后零落地判定,静默不生效由下一入口
        观察对账显影。
        """
        action: CwActionDeployMoveParam = self.param
        env = self.env
        ex = env.executor
        match = ex._ctx.cw_match
        session = match.session if match is not None else None
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            DEPLOYED_BACK_CAPACITY,
            DEPLOYED_FRONT_CAPACITY,
            deployed_slot_no,
        )
        tracked = (list(game_state_of(session).tracked_books.deployed)
                   if session is not None else [])
        front_total = min(len(ex._front_pts), DEPLOYED_FRONT_CAPACITY)
        back_total = min(max(1, len(ex._back_pts)), DEPLOYED_BACK_CAPACITY)
        # 空槽读数 = 下标派生(迁移过渡口径 §2.2,行为等价:旧
        # ``empty_deploy_slots`` 按条目信息位 (position_pref, slot) 判定,
        # P1 起条目无信息位冗余、表下标即权威——禁对快照条目 getattr
        # 柔取旧字段)。
        front_empty = [deployed_slot_no(i) for i in range(front_total)
                       if i >= len(tracked) or tracked[i] is None]
        back_empty = [deployed_slot_no(i)
                      for i in range(DEPLOYED_FRONT_CAPACITY,
                                     DEPLOYED_FRONT_CAPACITY + back_total)
                      if i >= len(tracked) or tracked[i] is None]
        chosen, fallback = ((front_empty, back_empty)
                            if action.to_row == 'front'
                            else (back_empty, front_empty))
        if chosen:
            row, slot_no = action.to_row, chosen[0]
        elif fallback:
            row = 'back' if action.to_row == 'front' else 'front'
            slot_no = fallback[0]
        else:
            return self.round_fail('部署落位无空槽(两排全满,观察重派)')
        src = ex._bench_pts[action.bench_idx]
        dst = (ex._front_pts if row == 'front' else ex._back_pts)[slot_no - 1]
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
        # 发出即记账:拖拽发出即 tracked 记上阵(机械执行零判效)。
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
