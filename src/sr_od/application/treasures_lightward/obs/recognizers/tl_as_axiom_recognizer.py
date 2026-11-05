"""末日幻影-终焉公理弹画面额外识别器(per-screen recognizer)。

``analyze_screen`` 精准命中「末日幻影-终焉公理」后按 ``screen_name`` 查表调用,
把 buff 装配弹窗的结构化事实(当前节点 / 三选一增益的名称与装备态)塞进
``extras``——增益名称随期轮换不可锚定,按卡片位置(建档 rect)裁片 OCR 读取;
「装备中」角标只出现在当前装备卡的右上角(实机帧标定),据此判装备态。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from one_dragon.utils import str_utils

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext

SCREEN_NAME: str = '末日幻影-终焉公理'

#: 增益卡片建档 rect(与 screen_info 卡片-增益N 一致;y1 即卡片顶)
_CARD_RECTS: list[tuple[int, int, int, int]] = [
    (665, 185, 1875, 305),
    (665, 320, 1875, 462),
    (665, 480, 1875, 612),
]

#: 卡内名称行裁窗(x 固定 820-1100;y 相对卡片顶)
_NAME_X1, _NAME_X2 = 820, 1100
_NAME_DY1, _NAME_DY2 = 0, 50
#: 「装备中」角标裁窗(x 固定 1755-1880;y 相对卡片顶;实测标签 y 顶+10~+52)
_TAG_X1, _TAG_X2 = 1755, 1880
_TAG_DY1, _TAG_DY2 = 0, 70
_EQUIPPED_TEXT: str = '装备中'


@dataclass
class AxiomBuffOption:
    """单条增益卡片读取结果。

    Attributes:
        slot: 增益卡片序号(画面从上到下 1 基;装配点击按此序)。
        name: 增益名称(卡片标题行 OCR;读不出 None)。
        equipped: 是否当前装备(卡片右上角「装备中」角标命中)。
        desc: 增益效果描述(卡片内除名称/角标外的文本合并;读不出空串)。
    """

    slot: int
    name: str | None
    equipped: bool
    desc: str = ''


@dataclass
class AxiomView:
    """终焉公理弹窗单帧结构化事实。

    Attributes:
        node_no: 弹窗对应的节点号(左栏「节点一/节点二」;读不出 None)。
        boss_name: 该节点首领名(节点行 OCR;读不出 None)。
        buffs: 三条增益选项(按画面上下序;items 全量返回,无编辑裁剪)。
    """

    node_no: int | None
    boss_name: str | None
    buffs: list[AxiomBuffOption] = field(default_factory=list)


def _first_short_line(lines: list[str]) -> str | None:
    """取第一行短文本作名称(名称 ≤6 字;描述长行/含标点行过滤)。"""
    for line in lines:
        stripped = line.replace(' ', '')
        if 0 < len(stripped) <= 6 and '。' not in stripped and '，' not in stripped:
            return stripped
    return None


class TlAsAxiomRecognizer(ScreenRecognizer):
    """终焉公理弹窗画面额外识别器。"""

    screen_name: str = SCREEN_NAME

    extras_doc: dict[str, str] = {
        'node_no': '弹窗对应节点号(1/2;左栏「节点一/节点二」OCR;读不出 None)',
        'boss_name': '该节点首领名(节点行右侧 OCR;读不出 None)',
        'buffs': '增益三选一 list[{slot,name,equipped,desc}];slot=卡片序号(1 基,'
                 '装配点击按此序);equipped=右上角「装备中」角标命中;名称/描述随期'
                 '轮换按卡片位置实读',
    }

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,   # noqa: ARG002  area 经 screen_loader 读,未直接用入参
    ) -> dict | None:
        """读弹窗结构化事实 → dict;字段含义见 ``extras_doc``。"""
        results = ctx.ocr_service.get_ocr_result_list(image=image)
        view = AxiomView(node_no=None, boss_name=None)

        node_line_y: int | None = None
        for r in results:
            text = (r.data or '').replace(' ', '')
            for no, key in ((1, '节点一'), (2, '节点二')):
                if key in text:
                    view.node_no = no
                    node_line_y = r.y
                    # 常态:节点号与首领名在同一条 OCR 行,行内去掉「节点N」即首领名
                    remainder = text.replace(key, '', 1)
                    if len(remainder) >= 4:
                        view.boss_name = remainder
                    break
            if view.node_no is not None:
                break
        if view.boss_name is None and view.node_no is not None and node_line_y is not None:
            # 兜底:节点行与首领名被拆成两条(节点行 y±15 内、x 在节点行右侧的最长行)
            for r in results:
                text = (r.data or '').replace(' ', '')
                if not text or '节点' in text:
                    continue
                if abs(r.y - node_line_y) <= 15 and len(text) >= 4:
                    view.boss_name = text
                    break

        for slot, (x1, y1, x2, y2) in enumerate(_CARD_RECTS, start=1):
            name = _read_card_name(ctx, image, y1)
            equipped = _read_card_equipped(ctx, image, y1)
            desc = _read_card_desc(results, x1, y1, x2, y2, exclude=name)
            view.buffs.append(AxiomBuffOption(
                slot=slot, name=name, equipped=equipped, desc=desc))

        from dataclasses import asdict
        return asdict(view)


def _read_card_name(ctx: SrContext, image: MatLike, card_y1: int) -> str | None:
    """卡片名称行裁片 OCR → 短行名称。"""
    crop = image[card_y1 + _NAME_DY1:card_y1 + _NAME_DY2, _NAME_X1:_NAME_X2]
    results = ctx.ocr_service.get_ocr_result_list(image=crop)
    return _first_short_line([r.data or '' for r in results])


def _read_card_equipped(ctx: SrContext, image: MatLike, card_y1: int) -> bool:
    """卡片右上角裁片 OCR 是否含「装备中」。"""
    crop = image[card_y1 + _TAG_DY1:card_y1 + _TAG_DY2, _TAG_X1:_TAG_X2]
    results = ctx.ocr_service.get_ocr_result_list(image=crop)
    texts = [r.data or '' for r in results]
    return str_utils.find_best_match_by_lcs(_EQUIPPED_TEXT, texts, 0.5) is not None


def _read_card_desc(results: list, x1: int, y1: int, x2: int, y2: int,
                    exclude: str | None) -> str:
    """卡片 rect 内 OCR 文本(滤名称行与角标行)按 y 序合并为描述。"""
    lines: list[tuple[int, str]] = []
    for r in results:
        text = (r.data or '').strip()
        if not text:
            continue
        if not (x1 <= r.x and r.x + r.w <= x2 + 40 and y1 <= r.y and r.y + r.h <= y2 + 10):
            continue
        if exclude and exclude.replace(' ', '') in text.replace(' ', ''):
            continue
        if '装备中' in text:
            continue
        lines.append((r.y, text))
    lines.sort(key=lambda t: t[0])
    return ' '.join(t[1] for t in lines)
