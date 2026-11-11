"""光锥 TAB → 打开替换光锥列表(浏览/换装的列表前置导航 op)。

职责单一:确保画面停在「光锥-替换」列表且列表滚回顶部 —— 浏览清单
(清单由调用方经 MCP analyze_screen 的 extras 读取)与换装 op
(EquipLightConeOp,起点要求在列表画面)的前置。

交互事实:光锥 TAB 底部「替换」按钮 → 光锥替换界面;替换界面无独立关闭
按钮建档,退出靠界面左上返回控件(未建档,浏览收尾用 analyze_screen 定位
后 click_game)。

前置:光锥 TAB(由 GotoCharacterDetail + SelectCharacterOp +
SwitchCharacterTabOp('光锥') 保证);已在替换列表则幂等成功(仍滚顶)。
入口与转移一律画面级判定,禁单区域命中 —— 两屏左上角标题「角色光锥 /
光锥替换」同位形近,单区域 OCR 相似度可互判命中(实机事故:未点按钮即
认定已在列表)。
"""

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen import screen_utils
from one_dragon.base.screen.screen_utils import FindAreaResultEnum
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_LC_TAB_SCREEN: str = '角色-光锥'
_REPLACE_SCREEN: str = '光锥-替换'
_ENTRY_SCREENS: list[str] = [_LC_TAB_SCREEN, _REPLACE_SCREEN]
# 打开后滚回列表顶的拖拽次数(浏览从头看;每轮一次,轮间画面判定兜底)
_RESET_TOP_DRAGS: int = 4


class OpenLightConeReplaceOp(SrOperation):
    """打开替换光锥列表并滚回顶部,终点 = 光锥-替换(列表在顶部)。

    结果状态:OPENED(列表已开且在顶部)。
    失败:不在光锥 TAB / 替换列表(前置导航缺失或异常画面)。
    """

    def __init__(self, ctx: SrContext):
        self._reset_drags_left: int = _RESET_TOP_DRAGS  #: 剩余滚顶拖拽次数(每轮一次)
        SrOperation.__init__(self, ctx, op_name=gt('打开替换光锥列表'),
                             node_max_retry_times=12)

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """画面级判定当前屏:已在替换列表幂等进入打开节点;TAB 继续点按钮。"""
        current = self.check_and_update_current_screen(
            self.last_screenshot, screen_name_list=_ENTRY_SCREENS)
        if current == _REPLACE_SCREEN:
            return self.round_success(status='IN_REPLACE')
        if current != _LC_TAB_SCREEN:
            return self.round_fail(f'不在光锥 TAB(当前画面判定: {current};'
                                   f'前置:进详情 + 选角色 + 切「光锥」页签)')
        return self.round_success(status='ON_TAB')

    @node_from(from_name='入口核对')
    @node_from(from_name='入口核对', status='ON_TAB')
    @node_from(from_name='入口核对', status='IN_REPLACE')
    @operation_node(name='打开列表', node_max_retry_times=12)
    def open_list(self) -> OperationRoundResult:
        """画面级判定循环:在 TAB 点「替换」按钮(转移由下轮画面判定确认);
        已在列表则滚顶(浏览从头看,换装起点也以顶部为干净起点)。"""
        current = self.check_and_update_current_screen(
            self.last_screenshot, screen_name_list=_ENTRY_SCREENS)
        if current == _LC_TAB_SCREEN:
            if screen_utils.find_area(self.ctx, self.last_screenshot,
                                      _LC_TAB_SCREEN, '按钮-替换') != FindAreaResultEnum.TRUE:
                return self.round_retry('未找到替换按钮', wait=2)
            self.ctx.controller.click(
                self.ctx.screen_loader.get_area(_LC_TAB_SCREEN, '按钮-替换').rect.center)
            return self.round_retry('已点击替换按钮,等待进入替换界面', wait=2)
        if current != _REPLACE_SCREEN:
            return self.round_fail(f'异常画面,无法打开替换列表(当前判定: {current})')
        if self._reset_drags_left > 0:
            list_area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '区域-光锥列表')
            center = list_area.rect.center
            self.ctx.controller.drag_to(Point(center.x, center.y + 400),
                                        Point(center.x, center.y - 400))
            self._reset_drags_left -= 1
            return self.round_retry(f'滚回列表顶部(剩 {self._reset_drags_left} 次拖拽)', wait=1)
        return self.round_success(status='OPENED')
