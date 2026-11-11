"""末日幻影退出当前节点战斗/结算态,回到末日幻影选关。

背景:挑战链只覆盖「往前打」,弃赛/换队场景没有退出路径——只能等
行动值自然耗尽(低分结算)或手动点击(禁用)。v1 覆盖结算态:节点结算页
点「退出」回选关;最终结算页同位按钮文本轮换为「返回末日幻影」,同键
处理。战斗内暂停退出(右上暂停 II → 结束战斗)待战斗帧建档后补(登记成待办:
本地待办 AS 条)。起点 = 末日幻影-节点结算(「挑战结束」命中),终点 =
末日幻影-选关。"""
from __future__ import annotations

from typing import ClassVar

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.operations.sr_operation import SrOperation

_SELECT_SCREEN: str = '末日幻影-选关'
_RESULT_SCREEN: str = '末日幻影-节点结算'


class TlAsBattleExitOp(SrOperation):
    """退出当前节点战斗/结算态,回到末日幻影选关。

    背景:挑战链只覆盖「往前打」,弃赛/换队场景没有退出路径——只能等
    行动值自然耗尽(低分结算)或手动点击(禁用)。v1 覆盖结算态:节点结算页
    点「退出」回选关;最终结算页同位按钮文本轮换为「返回末日幻影」,同键
    处理。战斗内暂停退出(右上暂停 II → 结束战斗)待战斗帧建档后补(登记成待办:
    本地待办 AS 条)。起点 = 末日幻影-节点结算(「挑战结束」命中),终点 =
    末日幻影-选关。"""

    STATUS_DONE: ClassVar[str] = '退出完成'

    @operation_node(name='退出循环', is_start_node=True, node_max_retry_times=12)
    def _exit_loop(self) -> OperationRoundResult:
        """按画面分流:已在选关 = 完成;结算页点「退出」/「返回末日幻影」。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _SELECT_SCREEN, '标题-末日幻影行').is_success:
            return self.round_success(self.STATUS_DONE, wait=0.5)

        if self.round_by_find_area(screen, _RESULT_SCREEN, '标题-挑战结束').is_success:
            click = self.round_by_find_and_click_area(
                screen, _RESULT_SCREEN, '按钮-退出',
                until_not_find_all=[(_RESULT_SCREEN, '标题-挑战结束')],
                pre_delay=0.5, retry_wait=1.5)
            if click.is_success:
                return self.round_wait('点退出', wait=2)
            # 最终结算页无「退出」:同位按钮文本轮换为「返回末日幻影」
            click = self.round_by_find_and_click_area(
                screen, _RESULT_SCREEN, '按钮-返回末日幻影',
                until_not_find_all=[(_RESULT_SCREEN, '标题-挑战结束')],
                pre_delay=0.5, retry_wait=1.5)
            if click.is_success:
                return self.round_wait('返回末日幻影', wait=2)
            return self.round_retry('结算按钮未命中(确认弹窗?)', wait=1.5)

        return self.round_retry(
            '不在选关也不在结算页(战斗内退出 v2 候补:需战斗帧建档)', wait=2)
