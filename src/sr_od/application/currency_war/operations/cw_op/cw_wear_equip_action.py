"""穿装备动作 op(WearEquipOp)——备战域动作文件(统一动作工厂批3 体迁:
体自 ``prep_actions.py::PrepActionExecutor._wear_equip`` 逐字迁移,原方法
改薄委托保持替身缝,design.md unified-action-factory §2.4)。

WearEquip 原子通路机械半(R2)。非终结。

机械执行零判效(用户裁定「动作 op = 机械执行」,落地判定归观察侧
reconcile 对账):发出即记账(env.emitted = True),拖后不做像素验证。
拖拽静默不生效属执行环境噪声,由下一入口 heavy 实读对账显影(账实失配
→ 安灯停 → 按真 bug 修),重试 = 决策循环按新观察自然重派。
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
    """穿装备单步(WearEquip 原子通路机械半)。非终结。"""

    def execute(self, env: PrepExecEnv) -> bool:
        """穿装备单步(WearEquip 原子通路机械半)。

        流程 = 稳帧确认(动画收尾输入条件化等待,非判效)→ owned 网格
        按名定位源件 → 单次拖拽。机械执行零判效:发出即记账
        (emitted=True),拖后零读屏零落地判定;拖拽静默不生效由下一
        入口观察对账显影(账实失配 → 安灯停 → 按真 bug 修),重派重算
        = 决策循环按新观察自然承接。装备域容器腿 = 容器零写
        (action-logic-state.md 正本申报「消费真值归观察」,截断点独占
        发射帧零窗口,下一入口 heavy 覆盖)。

        [索引定义] 拖拽坐标 = owned 网格定位点(格心 = read_equips 逐格
        分类现读)→ 目标排 avatar 拖点(screen_info 建档派生)。
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
                  f'({action.row}-{action.slot}) 已发(发出即记账,'
                  '落地归观察对账)')
        log.info(f'[cw][wear] {detail}')
        env.detail, env.emitted = detail, True
        return True
