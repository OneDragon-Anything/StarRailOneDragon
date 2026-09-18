"""部署动作 op(DeployMoveOp)——备战域动作文件(统一动作工厂批3 体迁:
体自 ``prep_actions.py::PrepActionExecutor._deploy_move`` 逐字迁移,原
方法改薄委托保持替身缝,design.md unified-action-factory §2.4)。

bench → 上阵单步拖拽(腾席链专用;R2 原子通路发射形态 = 决策核逐帧
按 kernel 计划逐 move 发本动作)。非终结。

机械执行零判效(用户裁定「动作 op = 机械执行」,落地判定归观察侧
reconcile 对账):发出即记账(tracked 记上阵),拖后不做像素验证。
拖拽静默不生效属执行环境噪声,由下一入口 heavy 实读对账显影(账实
失配 → 安灯停 → 按真 bug 修),重试 = 决策循环按新观察自然重派。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    game_state_of,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionDeployMoveParam
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class DeployMoveOp(ActionOp):
    """bench → 上阵单步拖拽(腾席链专用;统一词表 CwActionDeployMoveParam)。非终结。"""

    def execute(self, env: PrepExecEnv) -> bool:
        """bench → 上阵单步拖拽(腾席链专用;统一词表 CwActionDeployMoveParam)。

        执行坐标边:源拖点 = ``bench_idx`` 备战栏 area 序直取(容器下标 =
        area 序,零换算);落位排 = ``to_row``,落位物理槽 = tracked 占用
        现读首空位(kernel ``empty_deploy_slots`` 单一源,与发射位
        ``assign_deploy_slots`` 选排规则逐位同构——首选排满 fallback 另一排)。
        两排全满 = 未发出(False,观察重派);faction 字段不入执行(sim
        board 计数消费)。

        发出即记账(用户裁定「动作 op = 机械执行」):拖拽发出后 tracked
        记上阵;拖后零落地判定,静默不生效由下一入口观察对账显影,重试 =
        决策循环按新观察自然重派。
        """
        action: CwActionDeployMoveParam = self.action
        ex = env.executor
        match = ex._ctx.cw_match
        session = match.session if match is not None else None
        from sr_od.application.currency_war.kernel.cw_deploy_logic import (
            empty_deploy_slots,
        )
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            pad_deployed,
        )
        tracked = (pad_deployed(list(
            game_state_of(session).tracked_books.deployed))
            if session is not None else [])
        front_empty, back_empty = empty_deploy_slots(
            tracked, front_total=len(ex._front_pts),
            back_total=max(1, len(ex._back_pts)))
        chosen, fallback = ((front_empty, back_empty)
                            if action.to_row == 'front'
                            else (back_empty, front_empty))
        if chosen:
            row, slot_no = action.to_row, chosen[0]
        elif fallback:
            row = 'back' if action.to_row == 'front' else 'front'
            slot_no = fallback[0]
        else:
            env.detail, env.emitted = \
                '部署落位无空槽(两排全满,观察重派)', False
            return True
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
        if _overlay:
            env.detail, env.emitted = \
                ('部署已发,盛会之星 overlay 弹出(外环接管)', True)
            return True
        env.detail = (f'部署槽{action.bench_idx + 1}→{row}{slot_no} ✓'
                      '(发出即记账,落地归观察对账)')
        env.emitted = True
        return True
