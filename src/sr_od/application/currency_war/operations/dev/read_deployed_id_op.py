"""probe:deployed 身份读取(点槽→详情面板→OCR 名→关面板)。

验证「角色详情面板 = ground truth 身份源」机制(2026-08-09 佩佩实测:点已部署角色→
右侧弹面板显示角色名+阵营+星级+装备)。这是 #109(deployed 身份感知)的入口,替代不可靠的
SIFT 半身识别。

**临时 debug op**(机制验明后转正式身份读取,集成进备战 flow / cw_identity_obs)。
slot 传要读的槽中心;运行时应由 currency_war_cv.detect_board_slots(空板 plane-start 缓存)
+ deploy 跟踪(知哪些槽已占)提供。出口点面板外空白关(勿 ESC = bug#2 中断挑战)。
"""
import time

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

# 详情面板角色名区(面板开时固定;panel ~x1400-1840,y370-780)。名 OCR 有字 = 面板开。
NAME_RECT: Rect = Rect(1470, 380, 1680, 440)
# 关面板:点面板外空白(空前台区)。⚠️ 勿 ESC(bug#2:备战屏 ESC→中断挑战 dialog)。
PANEL_CLOSE: Point = Point(700, 400)
# 默认读的槽(佩佩位,probe 用;正式流程由 detect_board_slots + deploy 跟踪提供)
DEFAULT_SLOT: Point = Point(1390, 668)


class ReadDeployedIdProbe(SrOperation):
    """临时:读单个 deployed 槽的身份(点槽→面板→OCR 名→关)。"""

    def __init__(self, ctx: SrContext, slot: Point = DEFAULT_SLOT):
        SrOperation.__init__(self, ctx, op_name='cw-read-deployed-id')
        self.slot: Point = slot

    @operation_node(name='read-deployed-id', is_start_node=True)
    def read_id(self) -> OperationRoundResult:
        # 1. 点槽开面板
        self.ctx.controller.click(self.slot)
        time.sleep(1.2)
        screen = self.screenshot()
        # 2. OCR 名区(有字 = 面板开 + 即身份)
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=NAME_RECT, color_range=None, crop_first=False
        )
        names = [k for k, m in ocr_map.items() if m.max is not None]
        if not names:
            log.info(f'[cw-read-id] 无面板 @ slot{self.slot}(空槽 / 坐标错 / 面板未开)')
            return self.round_fail('no panel')
        name = max(names, key=len)  # 角色名通常最长
        log.info(f'[cw-read-id] slot{self.slot} -> 身份="{name}" (名区 OCR: {names})')
        self.save_screenshot(prefix='cw_read_id')
        # 3. 关面板(点面板外空白;勿 ESC)
        self.ctx.controller.click(PANEL_CLOSE)
        time.sleep(0.8)
        return self.round_success(f'id={name}')


_EXPORT = ReadDeployedIdProbe
