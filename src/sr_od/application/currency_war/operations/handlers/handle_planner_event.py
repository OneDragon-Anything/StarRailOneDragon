# live-verified 2026-08-20:局29 P2r6 银狼策划事件 41min 卡死后建;坐标来自当场实测
# (左卡中心 (755,400) 命中选中;详情面板 × 归一化 775,245→(1488,265))。机制见
# docs/game/gameplay/currency_war.md「银狼我来当策划事件」节(用户口述)。

"""货币战争 银狼「我来当策划」策划事件 overlay 处理 op(r103)。

银狼首次升 2 星(及 5 费升 2 星)触发的二选一 overlay:
- 首次:选项含「升费」(提升费用至 4 费,变为 1 星银狼)vs 其他(破解芯片/专属装备)
  → **默认选升费**(成长滚动投资前提;用户口述:选了升费新费档银狼刷进商店,
  不选则停留当前费用——机会只有一次);
- 5 费升 2 星:两选项都是装备(无法升费),任选其一。

识别:OCR 左/右卡区域,找「提升费用」字样 → 那张是升费卡;无 → 任选(左)。
选卡后可能自动弹「属性详情」面板 → 点右上 × 关闭。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandlePlannerEvent(SrOperation):
    """银狼策划事件 overlay:OCR 两卡 → 选升费卡(默认) → 确认 → 关详情面板。"""

    # 卡片中心(局29 实测:左卡区 x500-980/y280-560,点 (755,400) 命中选中)
    CARD_LEFT: ClassVar[Point] = Point(755, 400)
    CARD_RIGHT: ClassVar[Point] = Point(1260, 400)
    # 升费卡判定文字(用户口述:升费卡带「提升费用」字样)
    UPGRADE_COST_TEXT: ClassVar[str] = '提升费用'
    # 卡文字 OCR 过滤带(卡描述在 y~330-370;标题 y~376)
    CARD_TEXT_Y_LO: ClassVar[int] = 300
    CARD_TEXT_Y_HI: ClassVar[int] = 420
    # 选卡后自动弹的「属性详情」面板关闭按钮(归一化 775,245 → 1080p)
    DETAIL_CLOSE: ClassVar[Point] = Point(1488, 265)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-策划事件')

    @operation_node(node_name='处理策划事件', is_start_node=True, node_max_retry_times=5)
    def handle(self) -> OperationRoundResult:
        screen = self.screenshot()
        # 1. OCR 两卡区域,找升费卡
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        left_hit = False
        right_hit = False
        for text, mrl in ocr_map.items():
            if mrl.max is None or self.UPGRADE_COST_TEXT not in text:
                continue
            cy = mrl.max.center.y
            if not (self.CARD_TEXT_Y_LO <= cy <= self.CARD_TEXT_Y_HI):
                continue
            cx = mrl.max.center.x
            if cx < 960:
                left_hit = True
            else:
                right_hit = True
        if left_hit:
            target = self.CARD_LEFT
            pick = '左卡(升费)'
        elif right_hit:
            target = self.CARD_RIGHT
            pick = '右卡(升费)'
        else:
            # 无升费卡(5费升2星=全装备)→ 任选左
            target = self.CARD_LEFT
            pick = '左卡(无升费,装备任选)'
        # 2. 点卡选中
        self.ctx.controller.click(target)
        time.sleep(1.2)   # 等选中动画
        # 3. 点确认(screen_info 按钮-骇入确认 区中心;若确认已自动跳过此点无害)
        self.ctx.controller.click(Point(960, 615))
        time.sleep(1.5)   # 等面板
        # 4. 若弹出「属性详情」面板 → 关闭
        screen2 = self.screenshot()
        ocr2 = self.ctx.ocr_service.get_ocr_result_map(
            image=screen2, rect=None, color_range=None, crop_first=False,
        )
        if any('属性详情' in t for t in ocr2):
            self.ctx.controller.click(self.DETAIL_CLOSE)
            time.sleep(0.8)
            log.info('[cw][planner] 策划事件:%s → 已选+确认+关详情面板', pick)
        else:
            log.info('[cw][planner] 策划事件:%s → 已选+确认(无详情面板)', pick)
        return self.round_success(status=f'策划事件已处理({pick})')
