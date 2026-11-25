"""合成确认浮层观察域(备战画面的子态)= 成对配对定位 + 框内装备读取。

浮层是「把一件装备拖到另一件装备上」弹出的确认条:一行三格(原料 1 + 原料 2 =
产物预览),下方一左一右两颗按钮(✕ 取消、✓ 确认)。它没有独立画面身份——
在场时备战画面的识别标志照样全中;位置纵向随目标装备所在行浮动、横坐标不变,
所以不能用固定搜索框表示。读法:在装备栏内分别找 ✕、✓ 两颗按钮的候选峰,按固定
间距配成一对,由 ✓ 的命中位置派生两颗按钮的点击坐标与三个装备格的位置,再读三个
格里的装备图标。

本模块的识别函数是纯函数、没有状态(识别器的模块头约定它是纯读;按帧缓存归各自的
调用方,不放在这里)。入参缺失(按钮模板或搜索矩形取不到)抛 ``SynthesisOverlayInputError``
而不判「不在场」——判成不在场的话,所有浮层帧都会被当成干净的备战帧走常规路径,
点击全被游戏丢弃,而且没有任何告警。

调用方:备战画面 op 的观察节点、备战 extras 识别器(``read_prep_extras``)、
停机钩子门(``cw_obs_core.is_prep_like_frame``)、退出链的「可安全交还」判定、
装备读帧刷新原语的拒写门。各消费面统一走 :func:`read_synthesis_overlay_of`
(按运行上下文备料后调纯函数);只有测试直接调纯函数、自己备料。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import cv2
import numpy as np
from cv2.typing import MatLike

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.obs.cw_equipment import _EQUIP_SCALES_FAST

if TYPE_CHECKING:
    from one_dragon.base.geometry.rectangle import Rect
    from one_dragon.base.screen.template_info import TemplateInfo
    from sr_od.context.sr_context import SrContext

# 两颗按钮的模板目录名(模板目录两层同名)。画面档退役后这两个模板不再被任何画面档
# 引用,由本模块的调用方按目录名直取:
# ``ctx.template_loader.get_template(目录名, 目录名)``。
OK_TEMPLATE_DIR: str = 'cw_synthesis_confirm_ok'
CANCEL_TEMPLATE_DIR: str = 'cw_synthesis_confirm_cancel'

# 识别四态(返回值 ``state``)。
STATE_ABSENT: str = 'none'          # 不在场:两颗按钮都没有候选
STATE_PRESENT: str = 'present'      # 在场:恰有一对 ✕/✓
STATE_AMBIGUOUS: str = 'ambiguous'  # 歧义:两对及以上
STATE_UNPAIRED: str = 'unpaired'    # 有候选但配不成对

# 按钮候选阈值(带掩码模板匹配分)。三张测试仓浮层样本帧上真按钮 0.99 以上,
# 一颗按钮的模板打在另一颗上的交叉峰 0.59–0.61,干净帧的装备栏区域内最高 0.41
# (样本 = sr-od-test/screens/货币战争-备战/rail_badge_absent_r2.webp、
# 货币战争-备战-合成确认/合成确认浮层.webp、合成确认浮层-局B.webp,
# 对照 = 货币战争-备战/deployed_2star.webp)。
BUTTON_THR: float = 0.80
# 同一颗按钮内的峰合并半径(像素):半径内只留最高峰。不合并的话,同一按钮内的分数
# 平台期会产出相邻的多组「配对」,把在场帧误判成歧义(每颗按钮过阈值的相邻点有
# 9–16 个)。40 小于两颗按钮的间距下限,✕ 与 ✓ 的候选不会互相吞掉。
BUTTON_MERGE_RADIUS: int = 40

# 配对容差(坐标 = 两颗按钮各自命中框的左上角):✕ 在 ✓ 左侧。
# 三张测试仓浮层样本帧(覆盖浮层的三个纵向档位)上两钮横向间距都是 115、纵向差都是 0;
# 各留 ±10 / ±6 的余量。分辨率或界面缩放变化导致间距变了就配不成对——那是有意留的
# 形态(「有候选但配不成对」),不是静默漏。
PAIR_DX_MIN: int = 105
PAIR_DX_MAX: int = 125
PAIR_DY_MAX: int = 6

# 三个装备格的中心相对 ✓ 命中框左上角 (ox, oy) 的偏移(1080p 像素;画面档表达不了
# 相对量,所以是代码常量)。次序 = (原料 1, 原料 2, 产物预览)。
# 出处:测试仓三张浮层样本帧上各格图标按模板库多尺度匹配的命中中心;中档、最低档两帧
# 与最高档帧的实测中心相差 4 像素,取其一——按这组常量比按各帧实测中心分数至多低
# 0.038,名字与过不过线的结论不变。
_INPUT1_OFFSET: tuple[int, int] = (-140, -46)
_INPUT2_OFFSET: tuple[int, int] = (-41, -46)
_PRODUCT_OFFSET: tuple[int, int] = (66, -49)
# 装备格裁片半宽(像素):裁片 68×68。
SLOT_HALF: int = 34

# 框内装备名的过线条件:最高分 ≥ 阈值,且最高分与次高分之差 ≥ 差值(库内歧义不可
# 分辨时判未识别)。两种格的阈值不同,因为渲染不同——产物预览格的渲染与装备栏图标
# 不同源,绝对分低、次高分也低。
# 原料格:测试仓三张浮层样本帧上已识别格的最高分 0.85 以上、次高分 0.67 以下。
INPUT_NAME_THR: float = 0.80
INPUT_NAME_MARGIN: float = 0.10
# 产物预览格:同三帧上已识别格的最高分 0.63 以上、次高分 0.28 以下。
PRODUCT_NAME_THR: float = 0.50
PRODUCT_NAME_MARGIN: float = 0.15

# 浮层外接范围相对 ✓ 命中框左上角的偏移 [x1, y1, x2, y2](三个装备格与两颗按钮的
# 外包,左右各留约 30 像素;信息性,供文档与排查,流程不消费)。
_PANEL_RECT_OFFSET: tuple[int, int, int, int] = (-175, -75, 100, 62)


class SynthesisOverlayInputError(ValueError):
    """识别入参缺失:按钮模板或装备栏搜索矩形取不到。调用方按各自的异常通道响应。"""


@dataclass(frozen=True)
class ButtonCandidate:
    """一颗按钮的一个候选峰(合并后)。

    ``x`` / ``y`` = 命中框(= 模板尺寸的矩形)左上角在帧内的坐标,1080p 像素,
    识别当帧现读;``score`` = 该处的带掩码模板匹配分。
    """

    x: int
    y: int
    score: float

    def detail(self) -> str:
        """日志用的一颗候选明细:位置 + 分数。"""
        return f'({self.x},{self.y})分{self.score:.3f}'


@dataclass(frozen=True)
class OverlayPair:
    """配成的一对按钮候选。"""

    ok: ButtonCandidate
    cancel: ButtonCandidate


@dataclass(frozen=True)
class SynthesisSlotReading:
    """框内一个装备格的读数。

    ``name`` = 装备图标模板库的模板名;未识别(分数或分差不过线、模板库缺席)= ``None``。
    ``conf`` = 最高分,未识别时照报(模板库缺席时 0.0)。
    ``cx`` / ``cy`` = 该格中心的帧内坐标,1080p 像素,识别当帧现读。
    """

    name: str | None
    conf: float
    cx: int
    cy: int


@dataclass(frozen=True)
class SynthesisOverlayResult:
    """一次识别的结果。

    ``state`` = 四态之一(模块常量 ``STATE_*``)。
    ``reading`` = 仅在场时有值,其余三态为 ``None``;结构 =
    ``{'ok_xy': (x, y), 'cancel_xy': (x, y), 'panel_rect': [x1, y1, x2, y2],
    'inputs': [槽读数, 槽读数], 'product': 槽读数}``(槽读数 =
    ``{'name', 'conf', 'cx', 'cy'}``;坐标都是 1080p 游戏空间的帧内坐标)。
    ``ok_candidates`` / ``cancel_candidates`` / ``pairs`` = 本次的候选明细,
    供「读不准」的帧写日志与失败文案。
    """

    state: str
    reading: dict | None
    ok_candidates: tuple[ButtonCandidate, ...]
    cancel_candidates: tuple[ButtonCandidate, ...]
    pairs: tuple[OverlayPair, ...]

    def candidates_detail(self) -> str:
        """本次的候选明细文本(哪颗按钮、位置、分数;歧义时带全部候选对),给失败文案用。"""
        def one(pair: OverlayPair) -> str:
            return f'[✕{pair.cancel.detail()} ✓{pair.ok.detail()}]'

        return (f'✓候选[{",".join(c.detail() for c in self.ok_candidates)}] '
                f'✕候选[{",".join(c.detail() for c in self.cancel_candidates)}] '
                f'候选对[{"".join(one(p) for p in self.pairs)}]')


def _template_images(template: TemplateInfo | None, label: str) -> tuple[MatLike, MatLike]:
    """取按钮模板的原图与掩码;取不到就抛入参异常。"""
    if template is None or template.raw is None or template.mask is None:
        raise SynthesisOverlayInputError(f'按钮模板缺失({label})')
    if template.mask.shape[:2] != template.raw.shape[:2]:
        raise SynthesisOverlayInputError(f'按钮模板掩码与原图尺寸不一致({label})')
    return template.raw, template.mask


def find_button_candidates(screen: MatLike, raw: MatLike, mask: MatLike,
                           search_rect: Rect) -> list[ButtonCandidate]:
    """在装备栏搜索矩形内找一颗按钮的全部候选峰,按 (y, x) 排序。

    匹配在「搜索矩形向下外扩一个模板高」的范围上做,但只有命中框左上角落在原搜索
    矩形内的峰才算候选——矩形只用来过滤峰的位置,不用来裁剪待匹配的图。不外扩的
    话,模板左上角的纵坐标最大只到「矩形下沿 − 模板高」,目标装备在装备行最末一行时
    按钮的左上角已经在那条线以下,整帧会被判「不在场」。

    先在整段匹配范围内合并峰、再按矩形过滤:同一次合并里最高峰说了算,不因为它落在
    矩形外就换成旁边的次高峰当候选。

    非有限分数一并丢弃:带掩码匹配在纯色区会得到无穷大,那样的点不是命中。
    """
    x1, y1, x2, y2 = search_rect.x1, search_rect.y1, search_rect.x2, search_rect.y2
    th, tw = raw.shape[:2]
    h, w = screen.shape[:2]
    part = screen[y1:min(y2 + th, h), x1:min(x2, w)]
    if part.shape[0] < th or part.shape[1] < tw:
        raise SynthesisOverlayInputError(
            f'搜索矩形外扩后仍小于按钮模板(矩形{search_rect}, 模板高x宽={th}x{tw})')
    res = cv2.matchTemplate(part, raw, cv2.TM_CCOEFF_NORMED, mask=mask)
    ys, xs = np.nonzero((res >= BUTTON_THR) & np.isfinite(res))
    # 峰很少(一颗按钮至多十几个过阈值的相邻点),按分数降序贪心合并即可
    order = np.lexsort((xs, ys, -res[ys, xs]))
    merged: list[ButtonCandidate] = []
    for i in order:
        cand = ButtonCandidate(x=int(xs[i]) + x1, y=int(ys[i]) + y1,
                               score=float(res[ys[i], xs[i]]))
        if any((cand.x - k.x) ** 2 + (cand.y - k.y) ** 2 <= BUTTON_MERGE_RADIUS ** 2
               for k in merged):
            continue
        merged.append(cand)
    kept = [c for c in merged if x1 <= c.x < x2 and y1 <= c.y < y2]
    kept.sort(key=lambda c: (c.y, c.x))
    return kept


def pair_button_candidates(ok_candidates: list[ButtonCandidate],
                           cancel_candidates: list[ButtonCandidate]) -> list[OverlayPair]:
    """按固定间距把 ✓ 候选与 ✕ 候标配对(✕ 在 ✓ 左侧);不修改入参的候选。"""
    pairs: list[OverlayPair] = []
    for ok in ok_candidates:
        for cancel in cancel_candidates:
            if (PAIR_DX_MIN <= ok.x - cancel.x <= PAIR_DX_MAX
                    and abs(ok.y - cancel.y) <= PAIR_DY_MAX):
                pairs.append(OverlayPair(ok=ok, cancel=cancel))
    pairs.sort(key=lambda p: (p.ok.y, p.ok.x, p.cancel.x))
    return pairs


def _best_template_score(crop: np.ndarray, gray: np.ndarray) -> float:
    """一张装备模板在各尺度上对裁片的最高分;尺度集沿用装备栏读数的那一档快集。

    缩放写成显式目标尺寸(与装备栏穿戴读链的缩放同一种写法,两种写法同样缩到 65×65
    像素却略有不同,分数差 0.01 上下)。缩放后任一边不小于裁片的尺度跳过——裁片
    68×68、模板 98×98 时只有 0.66 一档参与。没有可用尺度或分数非有限 = -1。
    """
    best = -1.0
    for scale in _EQUIP_SCALES_FAST:
        nw = max(8, int(round(gray.shape[1] * scale)))
        nh = max(8, int(round(gray.shape[0] * scale)))
        if nh >= crop.shape[0] or nw >= crop.shape[1]:
            continue
        res = cv2.matchTemplate(crop, cv2.resize(gray, (nw, nh), interpolation=cv2.INTER_AREA),
                                cv2.TM_CCOEFF_NORMED)
        finite = res[np.isfinite(res)]
        if finite.size > 0:
            best = max(best, float(finite.max()))
    return best


def read_overlay_slot(screen: MatLike, cx: int, cy: int,
                      equip_grays: dict[str, MatLike] | None, *,
                      is_product: bool = False) -> SynthesisSlotReading:
    """读框内一个装备格:格中心取固定窗口裁片,对装备图标灰度模板库多尺度匹配。

    原料格与产物预览格的过线条件不同(常量区 ``INPUT_NAME_*`` / ``PRODUCT_NAME_*``)。
    模板库缺席(目录不存在或没有模板)时返回未识别、分数 0.0——配对定位不依赖装备
    模板库,没有库也必须能把浮层收起。

    :param screen: 备战画面截图(RGB,1080p)
    :param cx: 格中心的帧内横坐标
    :param cy: 格中心的帧内纵坐标
    :param equip_grays: 装备图标灰度模板库(``{模板名: 灰度图}``),可为 ``None``
    :param is_product: 是否产物预览格(用产物格的过线条件)
    """
    if not equip_grays:
        return SynthesisSlotReading(name=None, conf=0.0, cx=cx, cy=cy)
    x1, y1 = cx - SLOT_HALF, cy - SLOT_HALF
    crop = screen[y1:y1 + SLOT_HALF * 2, x1:x1 + SLOT_HALF * 2]
    # 裁片越出画面时 numpy 切片静默返回小图或空图(负下标从尾部取),不会报错;
    # 小裁片会改变尺度守卫的结果,所以形状不对就当入参异常抛出
    if crop.shape[:2] != (SLOT_HALF * 2, SLOT_HALF * 2):
        raise SynthesisOverlayInputError(
            f'装备格裁片越出画面(格中心({cx},{cy}), 帧{screen.shape[1]}x{screen.shape[0]})')
    crop = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)   # screen 为 RGB
    scores = sorted(((name, _best_template_score(crop, gray)) for name, gray in equip_grays.items()),
                    key=lambda item: (-item[1], item[0]))
    top_name, top_score = scores[0]
    second_score = scores[1][1] if len(scores) > 1 else -1.0
    thr, margin = ((PRODUCT_NAME_THR, PRODUCT_NAME_MARGIN) if is_product
                   else (INPUT_NAME_THR, INPUT_NAME_MARGIN))
    passed = top_score >= thr and top_score - second_score >= margin
    return SynthesisSlotReading(name=top_name if passed else None, conf=top_score, cx=cx, cy=cy)


def _slot_dict(reading: SynthesisSlotReading) -> dict:
    return {'name': reading.name, 'conf': reading.conf, 'cx': reading.cx, 'cy': reading.cy}


def read_synthesis_overlay(screen: MatLike, ok_template: TemplateInfo | None,
                           cancel_template: TemplateInfo | None,
                           search_rect: Rect | None,
                           equip_grays: dict[str, MatLike] | None) -> SynthesisOverlayResult:
    """识别合成确认浮层:成对配对定位 + 框内装备读取。

    :param screen: 备战画面截图(RGB,1080p)
    :param ok_template: ✓ 按钮模板(``OK_TEMPLATE_DIR``),取不到时传 ``None``
    :param cancel_template: ✕ 按钮模板(``CANCEL_TEMPLATE_DIR``),取不到时传 ``None``
    :param search_rect: 装备栏搜索矩形(画面档「区域-道具装备」的 pc_rect),
        取不到时传 ``None``
    :param equip_grays: 装备图标灰度模板库(``ensure_equip_tm_templates`` 的返回值),
        目录缺席时传 ``None``
    :return: 四态与读数,见 ``SynthesisOverlayResult``
    :raises SynthesisOverlayInputError: 按钮模板或搜索矩形取不到——不判「不在场」
    """
    if search_rect is None:
        raise SynthesisOverlayInputError('装备栏搜索矩形缺失(画面档取不到「区域-道具装备」)')
    ok_raw, ok_mask = _template_images(ok_template, '✓')
    cancel_raw, cancel_mask = _template_images(cancel_template, '✕')

    ok_candidates = find_button_candidates(screen, ok_raw, ok_mask, search_rect)
    cancel_candidates = find_button_candidates(screen, cancel_raw, cancel_mask, search_rect)
    pairs = pair_button_candidates(ok_candidates, cancel_candidates)
    result = SynthesisOverlayResult(
        state=STATE_ABSENT, reading=None,
        ok_candidates=tuple(ok_candidates), cancel_candidates=tuple(cancel_candidates),
        pairs=tuple(pairs))
    if not ok_candidates and not cancel_candidates:
        return result
    if len(pairs) != 1:
        return SynthesisOverlayResult(
            state=STATE_AMBIGUOUS if pairs else STATE_UNPAIRED, reading=None,
            ok_candidates=tuple(ok_candidates), cancel_candidates=tuple(cancel_candidates),
            pairs=tuple(pairs))

    if not equip_grays:
        log.warning('[cw] 合成确认浮层在场,但装备图标模板库缺席:三个装备格读不出名字(不影响定位与收起)')
    ok, cancel = pairs[0].ok, pairs[0].cancel
    ox, oy = ok.x, ok.y
    inputs = tuple(read_overlay_slot(screen, ox + dx, oy + dy, equip_grays)
                   for dx, dy in (_INPUT1_OFFSET, _INPUT2_OFFSET))
    product = read_overlay_slot(screen, ox + _PRODUCT_OFFSET[0], oy + _PRODUCT_OFFSET[1],
                                equip_grays, is_product=True)
    px1, py1, px2, py2 = _PANEL_RECT_OFFSET
    reading = {
        'ok_xy': (ox + ok_raw.shape[1] // 2, oy + ok_raw.shape[0] // 2),
        'cancel_xy': (cancel.x + cancel_raw.shape[1] // 2, cancel.y + cancel_raw.shape[0] // 2),
        'panel_rect': [ox + px1, oy + py1, ox + px2, oy + py2],
        'inputs': [_slot_dict(inputs[0]), _slot_dict(inputs[1])],
        'product': _slot_dict(product),
    }
    return SynthesisOverlayResult(
        state=STATE_PRESENT, reading=reading,
        ok_candidates=tuple(ok_candidates), cancel_candidates=tuple(cancel_candidates),
        pairs=tuple(pairs))


#: 装备栏搜索矩形在备战画面档里的区域名(矩形本身以画面档为单一真相源)。
SEARCH_AREA_NAME: str = '区域-道具装备'


def read_synthesis_overlay_of(ctx: SrContext, screen: MatLike) -> SynthesisOverlayResult:
    """按运行上下文备料,再调 :func:`read_synthesis_overlay`——各消费面的统一入口。

    备料三样:两颗按钮的模板(模板目录两层同名)、搜索矩形(备战画面档
    ``SEARCH_AREA_NAME`` 的 pc_rect)、装备图标灰度模板库。五个消费面(备战画面 op 的
    观察节点、备战 extras 识别器、停机钩子门、退出链的可交还判定、装备读帧刷新原语)
    都从这里进,备料写法只有这一份。按钮模板或搜索矩形取不到时照常抛
    ``SynthesisOverlayInputError``,由各消费面按自己的异常通道响应。
    """
    from sr_od.application.currency_war.kernel.cw_obs_core import (
        SCREEN_NAME,
        _area_rect,
    )
    from sr_od.application.currency_war.obs.cw_equipment import (
        ensure_equip_tm_templates,
    )
    return read_synthesis_overlay(
        screen,
        ctx.template_loader.get_template(OK_TEMPLATE_DIR, OK_TEMPLATE_DIR),
        ctx.template_loader.get_template(CANCEL_TEMPLATE_DIR, CANCEL_TEMPLATE_DIR),
        _area_rect(ctx, SEARCH_AREA_NAME, SCREEN_NAME),
        ensure_equip_tm_templates(ctx))
