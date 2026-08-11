# 已接入 battle_loop:255(2026-08-08 实测:bot 卡此 overlay 68min 后接入检测 + HandleWishTrial 点卡+确认+验关;出战不再被 overlay 卡,D-87~89 闭环)。整局遇祈愿(随机,命运圣杯/特定节点)live 再验。选试炼策略 naive 第1张(策略层 TODO:OCR objective+reward 选)。

"""货币战争 祈愿试炼 overlay 处理 op(事件长尾:2026-08-08 实跑发现,bot 卡此 overlay 68min)。

「祈愿试炼」= **节点级 quest 选择 overlay**(出现在特定节点前,如「再临仪式-二」「遭遇战」):
选 1 个试炼 → 该节点/本局完成 objective(如「累计刷新10次」「进行一场难度3+遭遇节点战斗」)
→ 得奖励(金币 / 阵营星徽)。overlay 叠在备战上,**挡备战分支**(购买经验透出命中 → BattlePrepCycle
误派 → shop 被遮失败 → 死循环)→ 必须在备战分支(1)前检测处理。

交互(2026-08-08 实测):ESC **不关**;点试炼卡身 → 选中(金色边框 + 「请选择」提示消失 +
确认选择亮)→ 点「确认选择」→ overlay 关回备战。候选卡数/内容随节点变(实测 2 张;「1/2」疑分页,
未深究),现固定点第 1 张卡身。

TODO(策略):现取第 1 张卡(MVP 解卡);后续可 OCR 各卡 objective + reward,按「易完成度 / 契合 comp」
选(如「累计刷新10次」bot 本就刷新 → 易完成 → 优先;「难度3+遭遇节点」需遇遭遇节点 → 看本局走法)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleWishTrial(SrOperation):
    """祈愿试炼 overlay:点第 1 张试炼卡选中 → 确认选择 → 验证 overlay 关。"""

    # 第 1 张试炼卡 body center(2026-08-08 实测:左卡「金币/累计刷新10次」点 (660,340) 命中选中,
    # 金色边框 + 确认选择转亮)。候选卡位置随节点变,固定第 1 张 = MVP;策略化读 objective 后再定选哪张。
    FIRST_CARD: ClassVar[Point] = Point(660, 340)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-祈愿试炼')

    @operation_node(name='祈愿试炼', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_find_area(screen, '货币战争-祈愿试炼', '标识-祈愿试炼').is_success:
            return self.round_fail('非祈愿试炼屏')
        # 点第 1 张卡选中(bug#1 缓解:mouse_move 先,零移动落 click,防 before_screenshot 移光标)。
        self.ctx.controller.mouse_move(HandleWishTrial.FIRST_CARD)
        self.ctx.controller.click(HandleWishTrial.FIRST_CARD)
        time.sleep(1.0)
        # 确认选择(本屏 area 位置;祈愿试炼 独有检测在前,不与 partner/megastar 的「确认选择」撞)。
        self.round_by_find_and_click_area(
            self.screenshot(), '货币战争-祈愿试炼', '按钮-确认选择', success_wait=1.5)
        # 验 overlay 关(标识-祈愿试炼 消失 = 推进);没关 → retry(confirm 未落地,bug#1 / 选中未生效)。
        if self.round_by_find_area(self.screenshot(), '货币战争-祈愿试炼', '标识-祈愿试炼').is_success:
            log.info('[cw-wish] 确认后 overlay 仍在 → round_retry')
            return self.round_retry(wait=1)
        log.info('[cw-wish] 祈愿试炼 overlay 关 → 回备战')
        return self.round_success(wait=2)
