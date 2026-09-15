"""点奖励球动作 op(ClickSpheresOp)——备战域动作文件(统一动作工厂
批3 体迁:体自 ``prep_actions.py::PrepActionExecutor._click_spheres``
逐字迁移,原方法改薄委托保持替身缝,design.md unified-action-factory
§2.4;一 op 一文件沿用 T-201 约定)。

R4 改形定形(批2):载荷 = kernel ``select_sphere_clicks`` 产出的有序
点击列,本 op 纯机械逐个点。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_vocab import ClickSpheres
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class ClickSpheresOp(ActionOp):
    """点奖励球:零读屏零排序零截断(挑选归决策侧 kernel 单一源),
    席满时部分球可能没点开由后续观察回补。非终结。"""

    def execute(self, env: PrepExecEnv) -> bool:
        """逐坐标点球(R4 机械执行半;载荷 = kernel ``select_sphere_clicks``
        产出的有序点击列)。

        大球优先/上界挑选归决策侧 kernel 单一源(发射位构造载荷),本方法
        纯机械逐个点(2026-09-02 用户指导 screen_flow_timing.md #16:奖励球
        飞行动画最长 ~2s → 点完等满动画;去向 = 备战/商店/装备栏)。零读屏
        零排序零截断(原读屏选球与 max_k 截断半随改形退役);席满时部分球
        可能没点开——由后续 heavy 观察自然回补(球仍在 → 下轮再派)。
        掉箱感知随之删除(掉箱归下一帧观察 → OpenBox 臂)。
        """
        action: ClickSpheres = self.action
        ex = env.executor
        for _x, _y in action.points:
            center = Point(_x, _y)
            ex._ctx.controller.mouse_move(center)   # bug#1 缓解
            ex._ctx.controller.click(center)
            ex._op.park_cursor(after_wait=0.1)
        # 用户口径:飞行动画最长 ~2s → 等满(固定等待归产生动画的操作)
        time.sleep(2.0)
        detail = (f'点球 {len(action.points)} 个(载荷机械点;'
                  f'动画等待 2s,球未消由下一帧观察回补)')
        log.info(f'[cw][sphere] {detail}')
        env.detail = detail
        env.emitted = True
        return True
