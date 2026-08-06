"""货币战争 选择伙伴 overlay 处理 op(从主循环拆出)。

「选择伙伴」overlay 会挡住出战 → stall。OCR 候选阵营标签定位候选 → 点候选立绘选中 → 确认选择。
必须在「确认选择/巨星」(HandleMegastar)之前判断 —— 选择伙伴也有「确认选择」但候选是
stage 立绘(横排,阵营 label 行),非巨星的左候选(822,333)。

TODO:策略化选伙伴(按 target_comp.core_chars 评估候选,现取最左)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleSelectPartner(SrOperation):
    """选择伙伴 overlay:OCR 候选 → 点候选立绘选中 → 确认选择。"""

    # 候选阵营标签行 y 过滤带(候选 label 在 y~362;排除标题 64 / 指令 130 / 详情 445 / 确认 582)。
    # 实测(2026-08-06 1-7 节点):候选 label 护盾/能量 在 y≈362;放宽 [340,400] 容变。
    LABEL_CY_LO: ClassVar[int] = 340
    LABEL_CY_HI: ClassVar[int] = 400
    # 候选立绘在 label 上方约 60px(label 362 → 立绘 302;实测点 (1127,300) 命中选中)。
    PORTRAIT_DY_ABOVE_LABEL: ClassVar[int] = 60
    # OCR 无候选时兜底(点画面中央立绘区;2026-08-06 实测 2 候选间隙 x≈1010,中央 x=960 可能落间隙,
    # 但兜底比 stall 强;真无候选极少)。
    FALLBACK_PORTRAIT: ClassVar[Point] = Point(960, 300)
    _EXCLUDE: ClassVar[set[str]] = {'选择伙伴', '攻略', '确认选择', '详情', '角色', '装备'}

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-选择伙伴')

    def _read_candidates(self, screen) -> list[tuple[str, int, int]]:
        """OCR 候选 ``(阵营名, label center-x, label center-y)``,按 label 行 y 过滤 + 左→右排序。

        候选 label 是 2-4 字阵营名(护盾/能量/仙舟/列车同行...)在固定 y 行;排除标题/指令/详情等。
        """
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        opts: list[tuple[str, int, int]] = []
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            cy = mrl.max.center.y
            if (HandleSelectPartner.LABEL_CY_LO <= cy <= HandleSelectPartner.LABEL_CY_HI
                    and 2 <= len(text) <= 4 and text not in HandleSelectPartner._EXCLUDE):
                opts.append((text, mrl.max.center.x, cy))
        opts.sort(key=lambda t: t[1])
        return opts

    @operation_node(name='选择伙伴', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_ocr(screen, '选择伙伴').is_success:
            return self.round_fail('非选择伙伴屏')
        # D-60:OCR 候选 label 定位(原硬编码 STAGE_PORTRAIT=(1048,299) 落 2 候选间隙 → 点不中 →
        # 确认选择无效 → flat-loop iter131+,2026-08-06 实跑)。点候选立绘(label_x, label_y-60)选中。
        cands = self._read_candidates(screen)
        if cands:
            _name, cx, cy = cands[0]   # 取最左候选(TODO:策略化按 target_comp.core_chars 选)
            portrait = Point(cx, cy - HandleSelectPartner.PORTRAIT_DY_ABOVE_LABEL)
            log.info(f'[cw-partner] candidates={[c[0] for c in cands]} chose={_name}@{portrait}')
        else:
            portrait = HandleSelectPartner.FALLBACK_PORTRAIT
            log.info(f'[cw-partner] no candidate OCR, fallback@{portrait}')
        self.ctx.controller.click(portrait)
        time.sleep(0.6)
        self.round_by_ocr_and_click(self.screenshot(), '确认选择', success_wait=2)
        return self.round_success(wait=2)
