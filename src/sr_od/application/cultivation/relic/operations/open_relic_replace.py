"""遗器 TAB → 打开替换遗器列表(浏览/换装的列表前置导航 op)。

职责单一:确保画面停在「遗器-替换」列表、部位筛选 = 目标部位且列表滚回
顶部 —— 浏览清单(清单由调用方经 MCP analyze_screen 的 extras 读取)与
换装 op(EquipRelicOp,自含导航无需此前置)之外的场景前置,如强化选件
前的清单查看。

交互事实(与 EquipRelicOp 同源实机摸底):着装页**点目标遗器位直达该部位
的替换界面**(部位筛选已锁定);着装页「按钮-替换」仅替换当前选中件,不进
浏览列表。已在替换界面时**重入的筛选部位可能与目标不符**(实机复现:
EquipRelicOp 教训)—— 用部位筛选 tab 的白条判据读当前部位(与
RelicReplaceRecognizer 同一识别链),不符先点返回回着装页再点目标位。

前置:遗器着装页(由 GotoCharacterDetail + SelectCharacterOp +
SwitchCharacterTabOp('遗器') 保证);已在正确部位的替换列表则幂等成功。
入口与转移一律画面级判定,禁单区域命中。
"""

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.mys.sr_codes import RELIC_POS_CN
from sr_od.operations.equip_list_recognizer import RelicReplaceRecognizer
from sr_od.operations.sr_operation import SrOperation

_RELIC_TAB_SCREEN: str = '角色-遗器'
_REPLACE_SCREEN: str = '遗器-替换'
_ENTRY_SCREENS: list[str] = [_RELIC_TAB_SCREEN, _REPLACE_SCREEN]
# 打开后滚回列表顶的拖拽次数(浏览从头看;每轮一次,轮间画面判定兜底)
_RESET_TOP_DRAGS: int = 4


class OpenRelicReplaceOp(SrOperation):
    """打开指定部位的替换遗器列表并滚回顶部,终点 = 遗器-替换(部位正确)。

    结果状态:OPENED(列表已开、部位筛选正确、在顶部)。
    失败:不在遗器着装页 / 替换列表(前置导航缺失或异常画面)。
    """

    def __init__(self, ctx: SrContext, pos: int):
        """
        :param pos: 部位号 1-6(1=头部 2=手部 3=躯干 4=脚部 5=位面球
            6=连结绳,与 SrRelicPieceDef.pos 同坐标系)。
        """
        if pos not in (1, 2, 3, 4, 5, 6):
            raise ValueError(f'部位 pos={pos} 超出 1-6')
        self.pos: int = pos
        self._reset_drags_left: int = _RESET_TOP_DRAGS  #: 剩余滚顶拖拽次数(每轮一次)
        SrOperation.__init__(self, ctx,
                             op_name=gt('打开替换遗器列表') + f'({RELIC_POS_CN[pos]})',
                             node_max_retry_times=12)

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """画面级判定当前屏:已在替换列表时读部位筛选——目标部位幂等进入
        打开节点,不符先点返回回着装页(重入部位不符,EquipRelicOp 实机教训)。"""
        current = self.check_and_update_current_screen(
            self.last_screenshot, screen_name_list=_ENTRY_SCREENS)
        if current == _REPLACE_SCREEN:
            current_pos = RelicReplaceRecognizer()._detect_pos_from_tabs(
                self.ctx, self.last_screenshot)
            if current_pos == self.pos:
                return self.round_success(status='IN_REPLACE')
            back_area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '按钮-返回')
            self.ctx.controller.click(back_area.rect.center)
            return self.round_retry(
                f'已在替换列表但部位筛选不符(筛选={current_pos},目标={self.pos}),'
                f'点返回回着装页', wait=1.5)
        if current != _RELIC_TAB_SCREEN:
            return self.round_fail(f'不在遗器着装页(当前画面判定: {current};'
                                   f'前置:进详情 + 选角色 + 切「遗器」页签)')
        return self.round_success(status='ON_TAB')

    @node_from(from_name='入口核对')
    @node_from(from_name='入口核对', status='ON_TAB')
    @node_from(from_name='入口核对', status='IN_REPLACE')
    @operation_node(name='打开列表', node_max_retry_times=12)
    def open_list(self) -> OperationRoundResult:
        """画面级判定循环:着装页点目标遗器位(转移由下轮画面判定确认);
        已在列表则滚顶(浏览从头看)。"""
        current = self.check_and_update_current_screen(
            self.last_screenshot, screen_name_list=_ENTRY_SCREENS)
        if current == _RELIC_TAB_SCREEN:
            slot_name = f'遗器位-{RELIC_POS_CN[self.pos]}'
            # 遗器位是纯坐标区(无文本/模板,find 不命中,EquipRelicOp 实机教训)
            # —— 直接坐标点击,转移由下轮画面判定确认
            slot = self.ctx.screen_loader.get_area(_RELIC_TAB_SCREEN, slot_name)
            self.ctx.controller.click(slot.rect.center)
            # 点遗器位后立即查标题必查不到(过渡动画中,EquipRelicOp 实机复现)
            return self.round_retry('已点击遗器位,等待进入替换界面', wait=1.5)
        if current != _REPLACE_SCREEN:
            return self.round_fail(f'异常画面,无法打开替换列表(当前判定: {current})')
        if self._reset_drags_left > 0:
            list_area = self.ctx.screen_loader.get_area(_REPLACE_SCREEN, '区域-遗器列表')
            center = list_area.rect.center
            self.ctx.controller.drag_to(Point(center.x, center.y + 400),
                                        Point(center.x, center.y - 400))
            self._reset_drags_left -= 1
            return self.round_retry(f'滚回列表顶部(剩 {self._reset_drags_left} 次拖拽)', wait=1)
        return self.round_success(status='OPENED')
