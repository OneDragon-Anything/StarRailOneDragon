"""逐光捡金编队识别:右上关卡信息(关卡名 / 环境效果 / 挑战目标)。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.treasures_lightward.obs.tl_team_common import (
    get_area_rect,
    ocr_lines,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from sr_od.context.sr_context import SrContext


def read_stage_name(ctx: SrContext, image: MatLike) -> str | None:
    """右上关卡名(如 物竞天择其一);读不到 None。"""
    rect = get_area_rect(ctx, '关卡名文本')
    if rect is None:
        return None
    lines = ocr_lines(ctx, image, rect)
    return lines[0] if lines else None


def read_environment(ctx: SrContext, image: MatLike) -> str | None:
    """环境效果全文(关卡名下方大描述区;一行文本折多行 OCR 后拼接)。

    描述区下邻「挑战目标」标题,OCR det 偶发把标题并进末行框(实测混入后缀)——
    该标题为固定字面量,拼接前按行剔除。
    """
    rect = get_area_rect(ctx, '文本-环境效果')
    if rect is None:
        return None
    lines = [line for line in ocr_lines(ctx, image, rect) if line != '挑战目标']
    text = ''.join(lines)
    if text.endswith('挑战目标'):
        text = text[:-len('挑战目标')]
    return text if text else None


def read_star_targets(ctx: SrContext, image: MatLike) -> list[str]:
    """挑战目标各行(满星条件,通常 3 行)。"""
    rect = get_area_rect(ctx, '文本-挑战目标')
    if rect is None:
        return []
    return ocr_lines(ctx, image, rect)
