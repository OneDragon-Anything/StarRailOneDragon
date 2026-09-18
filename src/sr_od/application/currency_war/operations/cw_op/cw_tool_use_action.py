"""工具消耗动作 op(ToolUseOp)——备战域动作文件(统一动作工厂批3 体迁:
体自 ``prep_actions.py::PrepActionExecutor._use_tool`` 逐字迁移,原方法改
薄委托保持替身缝,design.md unified-action-factory §2.4)。

一个 op 类辖工具原子七类(R8 按消耗品各立词表类,机械半同构:owned
网格内 icon → 目标拖曳;工具名解析表 ``_TOOL_NAME_BY_CLASS`` 随体迁)。
注册表七行(每词表类一行)同指本 op,消费语义逐类一致。零消耗确认
对拍(裁决 3:原 CwOpTools 三态对拍随原子化由观察承接)。非终结。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, ClassVar

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwAction,
    FurnaceUse,
    LuckyTokenUse,
    PerfectProjectorUse,
    PrecisionWrenchUse,
    PrivilegeCardUse,
    StaffProjectorUse,
    WrenchUse,
)
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class ToolUseOp(ActionOp):
    """工具消耗单步(R8 七类共用机械半:owned 网格内 icon → 目标拖曳)。
    非终结。"""

    #: 工具词表类 → 注册名(icon 定位锚,与装备注册表同名;体迁自执行器
    #: 类属性,唯一消费 = 本 op)。
    _TOOL_NAME_BY_CLASS: ClassVar[dict[type, str]] = {
        FurnaceUse: '冶金炉',
        PrivilegeCardUse: '特权赋予卡',
        WrenchUse: '拆装扳手',
        PrecisionWrenchUse: '精密拆装扳手',
        StaffProjectorUse: '员工投影仪',
        PerfectProjectorUse: '完美投影仪',
        LuckyTokenUse: '好运令牌',
    }

    def execute(self, env: PrepExecEnv) -> bool:
        """工具消耗单步(R8 七类共用机械半:owned 网格内 icon → 目标拖曳)。

        源件 = 工具 icon(按注册名定位);目标 = equip 模式 owned 网格
        icon / char 模式角色槽位中心。零消耗确认对拍(裁决 3:原
        CwOpTools 三态对拍随原子化由观察承接)——拖后固定等待,消费
        真值 = 下一帧装备区读数;装备域容器腿 = 容器零写
        (action-logic-state.md 正本申报「消费真值归观察」,截断点独占
        发射帧零窗口,下一入口 heavy 覆盖)。
        """
        action: CwAction = self.action
        ex = env.executor
        tool_name = self._TOOL_NAME_BY_CLASS[type(action)]
        start = ex._owned_grid_locate(tool_name)
        if start is None:
            env.detail, env.emitted = (
                f'owned 网格未定位到工具 {tool_name}'
                '(模板库缺失/已消耗,下帧重派)', False)
            return True
        if getattr(action, 'target_kind', 'char') == 'equip':
            tgt_name = getattr(action, 'item_name', '')
            end = ex._owned_grid_locate(tgt_name)
            if end is None:
                env.detail, env.emitted = (
                    f'owned 网格未定位到目标件 {tgt_name}'
                    '(合成消耗/reflow,下帧重派)', False)
                return True
            tgt_desc = tgt_name
        else:
            pts = ex._front_pts if action.row == 'front' else ex._back_pts
            end = pts[action.slot - 1]
            tgt_desc = f'{action.row}-{action.slot}'
        ex._ctx.controller.mouse_move(start)   # bug#1 缓解
        time.sleep(0.2)
        ex._ctx.controller.drag_to(start=start, end=end,
                                   hold_time=0.5, duration=1.2)
        time.sleep(1.5)   # MCP drag 异步落地(memory mcp-click-async-sleep-rule)
        ex._op.park_cursor(after_wait=0.1)
        detail = f'{tool_name} → {tgt_desc} 拖曳已发(零对拍,消费归观察)'
        log.info(f'[cw][tool] {detail}')
        env.detail, env.emitted = detail, True
        return True
