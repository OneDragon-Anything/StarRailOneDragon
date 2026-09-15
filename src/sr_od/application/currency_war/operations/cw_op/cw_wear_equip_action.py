"""穿装备动作 op(WearEquipOp)——备战域动作文件(统一动作工厂批3 体迁:
体自 ``prep_actions.py::PrepActionExecutor._wear_equip`` 逐字迁移,原方法
改薄委托保持替身缝,design.md unified-action-factory §2.4)。

WearEquip 原子通路机械半(R2);零比对出生(裁决 3)。非终结。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_vocab import WearEquip
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class WearEquipOp(ActionOp):
    """穿装备单步(WearEquip 原子通路机械半;零比对出生,裁决 3)。非终结。"""

    def execute(self, env: PrepExecEnv) -> bool:
        """穿装备单步(WearEquip 原子通路机械半;零比对出生,裁决 3)。

        流程 = 稳帧确认(动画收尾输入条件化,非判效)→ owned 网格按名
        定位源件 → 单次拖拽 → 发出即登记。零 CV-diff 零验穿零补救链——
        穿没穿归观察写入边对账(装备期望态对账族下一入口暴露);落空由
        下一入口观察重派承接(重算计划 = 天然重试)。逻辑态(owned 摘件)
        在观察侧 ``_project_prep_obs`` 直写。
        """
        action: WearEquip = self.action
        ex = env.executor
        target = ex._equip_slot_drag_point(action.row, action.slot)
        if target is None:
            env.detail, env.emitted = (
                f'装备槽位坐标缺失:{action.row}-{action.slot}'
                '(建档漂移,禁兜底坐标)', False)
            return True
        start = ex._owned_grid_locate(action.item_name)
        if start is None:
            env.detail, env.emitted = (
                f'owned 网格未定位到 {action.item_name}'
                '(模板库缺失/计划失效,下帧重派重算)', False)
            return True
        ex._wait_stable_frame()
        ex._ctx.controller.mouse_move(start)   # bug#1 缓解
        time.sleep(0.2)
        ex._ctx.controller.drag_to(start=start, end=target,
                                   hold_time=0.5, duration=1.5)
        time.sleep(1.5)   # MCP drag 异步落地(memory mcp-click-async-sleep-rule)
        ex._op.park_cursor(after_wait=0.1)
        detail = (f'穿戴 {action.item_name} → {action.char_name or "前排空槽"}'
                  f'({action.row}-{action.slot}) 已发(零比对,落地归观察对账)')
        log.info(f'[cw][wear] {detail}')
        env.detail, env.emitted = detail, True
        return True
