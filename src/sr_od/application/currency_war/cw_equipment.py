"""cw_equipment 装备视觉识别(**手维护,非生成**)。

数据模型(Equipment / EQUIPMENTS / get_equip)在 ``cw_equipment_data``(由
``tools/cw/gen_equip_registry.py`` 从 ``docs/game/currency_war/data/equipment.md`` 生成)。
本文件含:装备区**逐格分类**(``read_equip_grid`` / ``read_equips`` / ``read_equip_count``)
与穿戴装备 TM 识别(``read_equipped_below``)。
**拆分目的(R16 P0-1)**:生成器只写 ``cw_equipment_data``,永不覆盖本文件。

装备区识别演进:全域 SIFT(单应变换天然单实例,同模板多格重复只锁一格 → 占用召回 62%)
→ **网格几何 + 逐格 TM 分类**(格几何按 28 帧真值实测标定;同模板多实例问题随逐格独立消失)。
标定与对拍基线:``.debug/temp/currency_war/w540_equip_grid/REPORT.md``(171 真值格)。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
from cv2.typing import MatLike

from sr_od.application.currency_war.cw_equipment_data import (
    EQUIPMENT_ROSTER,
    EQUIPMENTS,
    Equipment,
    get_equip,
)
from sr_od.application.currency_war.cw_observe import cw_log, cw_shot

if TYPE_CHECKING:
    from one_dragon.base.geometry.rectangle import Rect
    from sr_od.context.sr_context import SrContext

# 公开 API:re-export 数据(Equipment/EQUIPMENTS/get_equip 来自 cw_equipment_data)+ 装备区逐格识别
# + 穿戴装备 TM 识别(read_equipped_below)
# __all__ 告知 ruff 这些 re-export 非 unused(F401)
__all__ = ['Equipment', 'EQUIPMENTS', 'EQUIPMENT_ROSTER', 'get_equip', 'load_equip_templates', 'read_equips',
           'read_equip_grid', 'read_equip_count', 'EquipCell',
           'load_equip_tm_grays', 'read_equipped_below', 'ensure_equip_tm_templates', 'ensure_equip_sift_templates']

_EQUIP_SIFT = cv2.SIFT_create()  # type: ignore[attr-defined]  # cv2 stubs 不含 SIFT(实际存在)
_EQUIP_MATCHER = cv2.BFMatcher()

# ①-a 全程 VLM 误判「装饰球体」的教训:VLM 不懂游戏,装备 icon 识别易误判。
# 装备身份以模板匹配为准;别依赖 VLM 推断游戏事实,游戏知识以用户/图鉴为准。


def load_equip_templates(equip_dir: Path) -> dict[str, tuple[MatLike, tuple, np.ndarray]]:
    """加载 cw_equip 模板库(``<名>.png`` → SIFT 关键点/描述子)。

    cw_equip 是单 png(非 ``<id>/raw.png`` 结构),直接读 png → gray → SIFT。
    返回 ``{name: (gray, keypoints, descriptors)}``(同 ``load_avatar_templates`` 结构)。
    """
    templates: dict[str, tuple[MatLike, tuple, np.ndarray]] = {}
    for png in sorted(equip_dir.glob('*.png')):
        img = cv2.imdecode(np.fromfile(str(png), np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        kp, desc = _EQUIP_SIFT.detectAndCompute(gray, None)
        if desc is not None and len(kp) >= 4:
            templates[png.stem] = (gray, kp, desc)
    return templates


# ===== 装备区网格几何(W540 28 帧真值实测标定)=====
# 实测格距 ~75px;旧注释「行距 ~98px」是模板素材尺寸(plaza 统一 98px),非格距 —— 勘误随本批生效。
_EQUIP_COL_ROW1: tuple[int, ...] = (1693, 1768, 1843)  # row1 材料堆叠带三列(格心 x,1080p 绝对坐标)
_EQUIP_COL_EQ: tuple[int, ...] = (1768, 1843)          # 装备行两列(左列 x1693 仅 row1 存在)
_EQUIP_ROW1_Y: int = 160                               # row1 格心 y(无横幅基准)
_EQUIP_ROW0_EQ_Y: int = 247                            # 首个装备行格心 y
_EQUIP_ROW_STEP: int = 75                              # 行距 = 列距(等距网格)
_EQUIP_EQ_ROWS: int = 6                                # 装备行数(y 247..622,实测最大 14 格未溢出)
_EQUIP_PATCH: int = 56                                 # 逐格裁片半宽(TM 搜索窗;容纳 ±~20px 格心抖动)
# TM 尺度档:icon 实际 ~70px / 模板素材 98px → 基准 ~0.71;快档覆盖常规,慢档兜异常渲染
_EQUIP_SCALES_FAST: tuple[float, ...] = (0.66, 0.70, 0.74)
_EQUIP_SCALES_FULL: tuple[float, ...] = tuple(round(0.60 + 0.02 * i, 2) for i in range(10))
# 占用阈值:28 帧真值实测占用格最低 0.659 / 空格最高 0.584,0.62 取中留双向余量
_EQUIP_OCC_THR: float = 0.62
# 横幅自适应:「装备追踪」横幅帧全网格整体下移 ~25-30px → δ 扫描取全格响应和最大者(不写死)
_EQUIP_DY_SCAN: tuple[int, ...] = tuple(range(-8, 45, 4))
_EQUIP_DY_SCALE: float = 0.70                          # δ 扫描用单一尺度(降耗;全库模板)

# 详情面板遮挡:面板打开时盖装备区左下(实测 char_detail 帧;probe 区面板态 V~50 / 常态 V≥217)
_EQUIP_PANEL_PROBE: tuple[int, int, int, int] = (1660, 560, 1740, 640)  # x1,y1,x2,y2(1080p)
_EQUIP_PANEL_V_THR: float = 120.0                      # probe 区 HSV V 均值低于此 = 面板开
_EQUIP_PANEL_RECT: tuple[int, int, int, int] = (1620, 350, 1872, 710)   # 面板覆盖区(同源实测)


@dataclass
class EquipCell:
    """装备区一格的识别结果(15 槽全量返回;占用/空/遮挡三态)。

    坐标系:``row`` = 物理行,0 = row1 材料堆叠带(带数量数字),1-6 = 其下装备行(自上而下);
    ``col`` = 物理列 0-2(左→右);row1 合法列 = 0/1/2,装备行合法列 = 1/2(左列无格)。
    ``cx/cy`` = 格心 1080p 绝对坐标(TM 峰心,非名义格点)。
    """
    row: int
    col: int
    cx: int
    cy: int
    name: str | None      # 占用 = 模板规范名;空/遮挡 = None
    score: float          # TM 最高响应(TM_CCOEFF_NORMED);占用判定阈 = _EQUIP_OCC_THR
    count: str | None = None  # row1 堆叠数量('1'-'5'/'∞');仅 read_equip_count 填充
    occluded: bool = False    # 详情面板遮挡格(score 未达占用阈且格落在面板区内)


def _equip_slot_centers(dy: int) -> list[tuple[int, int, int, int]]:
    """全部格心 ``(row, col, cx, cy)``(名义格点 + 横幅位移 dy)。"""
    out = [(0, c, x, _EQUIP_ROW1_Y + dy) for c, x in enumerate(_EQUIP_COL_ROW1)]
    for r in range(_EQUIP_EQ_ROWS):
        y = _EQUIP_ROW0_EQ_Y + _EQUIP_ROW_STEP * r + dy
        # 装备行列号 1/2(col 0 = 左列,仅 row1 存在;坐标系见 EquipCell)
        out.extend((r + 1, c + 1, x, y) for c, x in enumerate(_EQUIP_COL_EQ))
    return out


def _scaled_template_cache(templates: dict) -> dict[float, list[tuple[str, np.ndarray]]]:
    """模板多尺度预缩放缓存(键 = templates dict 身份;持强引用保 id 稳定,~8MB)。"""
    cached = _SCALED_CACHE.get(id(templates))
    if cached is not None:
        return cached[1]
    names = sorted(templates)
    scaled: dict[float, list[tuple[str, np.ndarray]]] = {}
    for s in _EQUIP_SCALES_FULL:
        lst = []
        for n in names:
            g = templates[n][0] if isinstance(templates[n], tuple) else templates[n]
            nw = max(8, int(round(g.shape[1] * s)))
            nh = max(8, int(round(g.shape[0] * s)))
            lst.append((n, cv2.resize(g, (nw, nh), interpolation=cv2.INTER_AREA)))
        scaled[s] = lst
    _SCALED_CACHE[id(templates)] = (templates, scaled)  # 强引用 templates 防 id 复用
    return scaled


_SCALED_CACHE: dict[int, tuple] = {}


def _gray_crop(screen: MatLike, cx: int, cy: int) -> np.ndarray:
    """格心 ±``_EQUIP_PATCH`` 裁片 → 灰度(sr_od screen 为 RGB)。"""
    h, w = screen.shape[:2]
    x1, y1 = max(0, cx - _EQUIP_PATCH), max(0, cy - _EQUIP_PATCH)
    x2, y2 = min(w, cx + _EQUIP_PATCH), min(h, cy + _EQUIP_PATCH)
    return cv2.cvtColor(screen[y1:y2, x1:x2], cv2.COLOR_RGB2GRAY)


def _classify_cell(crop: np.ndarray, scaled: dict[float, list[tuple[str, np.ndarray]]],
                   scales: tuple[float, ...]) -> tuple[str | None, float, int, int]:
    """单格 TM 全库分类 → ``(name, score, 命中中心相对格心偏移 dx, dy)``;全库低于阈 → name=None。"""
    best: tuple[str | None, float, int, int] = (None, -1.0, 0, 0)
    for s in scales:
        for n, tg in scaled[s]:
            th, tw = tg.shape
            if th >= crop.shape[0] or tw >= crop.shape[1]:
                continue
            r = cv2.matchTemplate(crop, tg, cv2.TM_CCOEFF_NORMED)
            _, mx, _, mloc = cv2.minMaxLoc(r)
            if mx > best[1]:
                best = (n, float(mx), mloc[0] + tw // 2 - crop.shape[1] // 2,
                        mloc[1] + th // 2 - crop.shape[0] // 2)
    return best


def _detect_zone_dy(screen: MatLike, scaled: dict[float, list[tuple[str, np.ndarray]]]) -> int:
    """横幅下移自适应:δ 扫描,取全部格 best-score 总和最大的 δ(单尺度全库,~秒级)。"""
    best_dy, best_total = 0, -1.0
    for dy in _EQUIP_DY_SCAN:
        total = 0.0
        for _row, _col, cx, cy in _equip_slot_centers(dy):
            total += _classify_cell(_gray_crop(screen, cx, cy), scaled, (_EQUIP_DY_SCALE,))[1]
        if total > best_total:
            best_total, best_dy = total, dy
    return best_dy


def _panel_open(screen: MatLike) -> bool:
    """详情面板是否打开(probe 区 HSV V 均值;面板态平坦深灰 V~50,常态紫蓝纹理 V≥217)。"""
    x1, y1, x2, y2 = _EQUIP_PANEL_PROBE
    hsv = cv2.cvtColor(screen[y1:y2, x1:x2], cv2.COLOR_RGB2HSV)
    return float(hsv[..., 2].mean()) < _EQUIP_PANEL_V_THR


def _cell_in_panel(cx: int, cy: int) -> bool:
    """格整框(±35px)是否落在面板覆盖区内(判定为遮挡格的几何条件)。"""
    px1, py1, px2, _py2 = _EQUIP_PANEL_RECT
    return cx + 35 <= px2 and cy - 35 >= py1 and cx - 35 >= px1


# 特权变体仲裁:基础/·特权 变体仅框色不同(灰 vs 金),灰度 TM 分不开(实测 随便骰子对:
# 基础 0.925 vs 特权 0.854 而 GT=特权)。环带饱和度仲裁:金框 S~175 / 其余 ≤92,阈 130。
_EQUIP_VARIANT_SUFFIX: str = '·特权'
_EQUIP_GOLD_RING_S: float = 130.0


def _variant_arbitrate(screen: MatLike, cx: int, cy: int, name: str,
                       template_names: set[str]) -> str:
    """特权变体判别(格心 ±26..36 方环 HSV S 均值;金框=·特权,灰框=基础)。"""
    has_sp = name + _EQUIP_VARIANT_SUFFIX in template_names
    is_sp = name.endswith(_EQUIP_VARIANT_SUFFIX)
    if not has_sp and not is_sp:
        return name
    h, w = screen.shape[:2]
    x1, y1 = max(0, cx - 36), max(0, cy - 36)
    x2, y2 = min(w, cx + 36), min(h, cy + 36)
    hsv = cv2.cvtColor(screen[y1:y2, x1:x2], cv2.COLOR_RGB2HSV)
    mask = np.zeros((y2 - y1, x2 - x1), np.uint8)
    cv2.rectangle(mask, (cx - 36 - x1, cy - 36 - y1),
                  (cx + 36 - x1, cy + 36 - y1), 255, -1)
    cv2.rectangle(mask, (cx - 26 - x1, cy - 26 - y1),
                  (cx + 26 - x1, cy + 26 - y1), 0, -1)
    s_mean = float(hsv[..., 1][mask > 0].mean())
    gold = s_mean >= _EQUIP_GOLD_RING_S
    if gold and has_sp:
        return name + _EQUIP_VARIANT_SUFFIX
    if not gold and is_sp and name[:-len(_EQUIP_VARIANT_SUFFIX)] in template_names:
        return name[:-len(_EQUIP_VARIANT_SUFFIX)]
    return name


def read_equip_grid(screen: MatLike,
                    templates: dict[str, tuple[MatLike, tuple, np.ndarray]]) -> list[EquipCell]:
    """装备区**逐格分类**:网格几何分格 → 逐格 TM 全库 → 15 槽全量三态(占用/空/遮挡)。

    同模板多实例问题随逐格独立消失(全域 SIFT 单应只锁一格,是旧实现 62% 召回的根因)。
    格几何 = 实测等距网格(75px;row1 三列材料带 + 其下六行两列装备列),横幅帧 δ 自适应扫描兜住。
    占用格低分时全尺度回扫一次(个别渲染态快档 < 阈、慢档过阈;实测 精密拆装扳手 依赖此兜底)。

    :param screen: 备战画面截图(RGB,1080p;``cv2_utils.read_image`` 约定)。
    :param templates: ``load_equip_templates`` 结果(只用其 gray,复用同一份缓存)。
    :return: 15 格 ``EquipCell``(占用格 name/score 有值;空格 name=None;面板遮挡格 occluded=True)。

    纯读(不写 session/全局;``_SCALED_CACHE`` 是只读资源缓存),可进 recognizer / op。
    """
    scaled = _scaled_template_cache(templates)
    dy = _detect_zone_dy(screen, scaled)
    panel = _panel_open(screen)
    cells: list[EquipCell] = []
    for row, col, cx, cy in _equip_slot_centers(dy):
        crop = _gray_crop(screen, cx, cy)
        name, score, dx, dy2 = _classify_cell(crop, scaled, _EQUIP_SCALES_FAST)
        if score < _EQUIP_OCC_THR:
            name2, score2, dx2, dy22 = _classify_cell(crop, scaled, _EQUIP_SCALES_FULL)
            if score2 > score:
                name, score, dx, dy2 = name2, score2, dx2, dy22
        occupied = name is not None and score >= _EQUIP_OCC_THR
        if occupied:
            name = _variant_arbitrate(screen, cx, cy, name, set(templates))
        occluded = (not occupied) and panel and _cell_in_panel(cx, cy)
        cells.append(EquipCell(
            row=row, col=col,
            cx=cx + (dx if occupied else 0), cy=cy + (dy2 if occupied else 0),
            name=name if occupied else None, score=float(score),
            occluded=occluded,
        ))
    return cells


# ===== row1 数量数字 OCR(两级管线;手法同源 cw_observation._ocr_upscaled / cw_faction_obs._read_badge_digit)=====
# row1 材料(扳手/炉/投影仪/骰子)同格堆叠,右下角白字数量(1-5 或 ∞)。
# 两级 = ① 紧裁白字 + 灰度反相(黑字白底,paddle rec 习惯)+ 6x 放大白边填充;② 失读 → 低阈掩码形状变体重试。
# 数量合法域 1-5 与 ∞(28 帧实测);越域读数 = 误读,按失读处理。
_EQUIP_COUNT_REGIONS: tuple[tuple[int, int, int, int], ...] = (
    (16, 48, 12, 44),   # 基准档:数字在格心右下(+16..+48, +12..+44)
    (2, 42, 2, 42),     # 左挂档:∞ 等宽字形左挂时(实测 shop_closed 精密拆装扳手 ∞)
)
_EQUIP_COUNT_UPSCALE: int = 6
_EQUIP_COUNT_PAD: int = 40
_EQUIP_COUNT_WHITE_THR: int = 170   # 白字 min(RGB) 阈;数字纯白 ≥200,灰框 ~180-210 靠紧裁 + 组件尺寸过滤排除


def _parse_equip_count(text: str | None) -> str | None:
    """数量 OCR 文本 → ``'1'-'5' | '∞' | None``(纯函数可单测;越域/杂讯 = 失读)。"""
    t = (text or '').strip()
    if not t:
        return None
    if '∞' in t:
        return '∞'
    low = t.lower()
    if low in ('oo', '0o', 'o0', 'co', 'oc', '8', 'ao', 'oa'):  # ∞ 常见误读形(双环)
        return '∞'
    digits = ''.join(ch for ch in t if ch.isdigit())
    if len(digits) == 1 and '1' <= digits <= '5':
        return digits
    if len(t) == 1 and t in 'lIi|!':   # 独字符 l/I/i/| 是数字 1 的常见误读(合法域内无歧义)
        return '1'
    return None


def _tight_count_crop(crop_rgb: MatLike) -> MatLike | None:
    """搜索区内白字最大连通域紧裁(留 2px 余量);过小/无 → None。"""
    mask = (crop_rgb.min(axis=2) > _EQUIP_COUNT_WHITE_THR).astype(np.uint8)
    n, _lab, stats, _cent = cv2.connectedComponentsWithStats(mask, 8)
    if n < 2:
        return None
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, _a = stats[i]
    if w < 3 or h < 5:
        return None
    hh, ww = crop_rgb.shape[:2]
    return crop_rgb[max(0, y - 2):min(hh, y + h + 2), max(0, x - 2):min(ww, x + w + 2)]


def _count_ocr_variants(crop_rgb: MatLike) -> list[MatLike]:
    """紧裁数字 → OCR 输入变体列表(① 反相灰度;② 低阈掩码形状,作二级重试)。"""
    tight = _tight_count_crop(crop_rgb)
    if tight is None:
        return []
    out: list[MatLike] = []
    for src in (tight, None):
        if src is None:
            sub = ((crop_rgb.min(axis=2) > 150).astype(np.uint8)) * 255
        else:
            sub = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY)
        inv = 255 - sub
        up = cv2.resize(inv, (inv.shape[1] * _EQUIP_COUNT_UPSCALE, inv.shape[0] * _EQUIP_COUNT_UPSCALE),
                        interpolation=cv2.INTER_CUBIC)
        up = cv2.copyMakeBorder(up, _EQUIP_COUNT_PAD, _EQUIP_COUNT_PAD, _EQUIP_COUNT_PAD, _EQUIP_COUNT_PAD,
                                cv2.BORDER_CONSTANT, value=255)
        out.append(cv2.cvtColor(up, cv2.COLOR_GRAY2RGB))
    return out


def _looks_infinity(crop_rgb: MatLike) -> bool:
    """紧裁白字是否 ∞ 形(结构预判,纯 CV):双孔,或单孔且宽扁(w/h>1.15)。

    数量合法域 1-5 均不满足(4 单孔但 w/h<1;1-5 无双孔)→ 无误判源;
    兜 OCR det 对独字 ∞ 的系统性失读(实测 shop_closed ∞ 两种裁片 OCR 均空)。
    """
    mask = (crop_rgb.min(axis=2) > _EQUIP_COUNT_WHITE_THR).astype(np.uint8)
    cnts, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hier is None:
        return False
    holes = sum(1 for i, hh in enumerate(hier[0])
                if hh[3] >= 0 and cv2.contourArea(cnts[i]) > 4)
    h, w = mask.shape
    return holes >= 2 or (holes >= 1 and w / max(h, 1) > 1.15)


def read_equip_count(ctx: SrContext, screen: MatLike, cx: int, cy: int) -> str | None:
    """读 row1 一格的堆叠数量数字(``'1'-'5' | '∞'``;失读返 None,不硬判)。

    :param ctx: 提供 ``ctx.ocr_service.get_ocr_result_list``(真 OCR 引擎;测试可注入 mock)。
    :param cx, cy: 占用格心(``EquipCell.cx/cy``,TM 峰心)。
    """
    ocr = ctx.ocr_service.get_ocr_result_list
    h, w = screen.shape[:2]
    for x1, x2, y1, y2 in _EQUIP_COUNT_REGIONS:
        rx1, ry1 = max(0, cx + x1), max(0, cy + y1)
        rx2, ry2 = min(w, cx + x2), min(h, cy + y2)
        crop = screen[ry1:ry2, rx1:rx2]
        if crop.size == 0:
            continue
        tight = _tight_count_crop(crop)
        if tight is not None and _looks_infinity(tight):
            return '∞'
        for img in _count_ocr_variants(crop):
            try:
                results = ocr(image=img)
            except Exception:   # noqa: BLE001  OCR 异常按失读,继续下一级
                continue
            for r in results or []:
                v = _parse_equip_count(getattr(r, 'data', None))
                if v is not None:
                    return v
    return None


_EQUIP_ZONE_DEFAULT: tuple[int, int, int, int] = (1620, 90, 1918, 710)  # 「区域-道具装备」screen_info 同值


def read_equips(
    screen: MatLike,
    templates: dict[str, tuple[MatLike, tuple, np.ndarray]],
    equip_rect: tuple[int, int, int, int] = _EQUIP_ZONE_DEFAULT,
    min_inliers: int = 7,
    cluster_radius: int = 20,
) -> list[tuple[str, tuple[int, int], int]]:
    """装备区 owned icon ``[(name, (cx, cy), inliers)]``(按置信降序)。

    默认区域(= 装备区标准格 ``(1620,90,1918,710)``)走**逐格分类**(``read_equip_grid``):
    28 帧真值对拍召回 171/171、零误检;第三元素语义由 SIFT inliers 改为 ``int(score*100)``
    (同为置信度量,消费方仅用于排序)。row1 材料格与装备格一并列出(与旧输出口径一致)。

    **非默认 equip_rect 走全域 SIFT 旧路径**(``_read_equips_sift``,行为不变)——
    任意区域/任意模板子集的调用方(如 cw_node_obs 奖励区三钻)依赖 SIFT 语义,网格几何不适用。

    :param min_inliers: 仅旧路径生效(SIFT RANSAC inlier 阈)。
    :param cluster_radius: 仅旧路径生效(同坐标簇聚合半径)。
    """
    if tuple(equip_rect) != _EQUIP_ZONE_DEFAULT:
        return _read_equips_sift(screen, templates, equip_rect, min_inliers, cluster_radius)
    cells = read_equip_grid(screen, templates)
    hits = [(c.name, (c.cx, c.cy), int(round(c.score * 100)))
            for c in cells if c.name is not None]
    hits.sort(key=lambda h: -h[2])
    return hits


def _read_equips_sift(
    screen: MatLike,
    templates: dict[str, tuple[MatLike, tuple, np.ndarray]],
    equip_rect: tuple[int, int, int, int],
    min_inliers: int,
    cluster_radius: int,
) -> list[tuple[str, tuple[int, int], int]]:
    """全域 SIFT 旧路径(逐格分类落地前的原实现;任意区域/模板子集调用方专用)。

    三处健全性:centroid 用 RANSAC inlier 子集;``cluster_radius`` 簇聚合;``min_inliers=7``。
    已知结构局限:单应变换天然单实例,同模板多格重复至多识别一格(装备区已改走逐格分类)。
    """
    x1, y1, x2, y2 = equip_rect
    zone = screen[y1:y2, x1:x2]
    gray = cv2.cvtColor(zone, cv2.COLOR_RGB2GRAY)  # sr_od screen RGB
    kp_z, desc_z = _EQUIP_SIFT.detectAndCompute(gray, None)
    raw_hits: list[tuple[str, tuple[int, int], int]] = []
    if desc_z is None or len(kp_z) < 4:
        return raw_hits
    for name, (_tgray, tkp, tdesc) in templates.items():
        matches = _EQUIP_MATCHER.knnMatch(tdesc, desc_z, k=2)
        good = [mm[0] for mm in matches if len(mm) >= 2 and mm[0].distance < 0.75 * mm[1].distance]
        if len(good) >= 8:
            src = np.float32([tkp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst = np.float32([kp_z[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            _, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
            if mask is None:
                continue
            inliers = int(mask.sum())
            if inliers < min_inliers:
                continue
            # centroid 用 RANSAC inlier(非全部 good —— outlier 偏移中心)
            inlier_pts = [kp_z[good[i].trainIdx].pt for i in range(len(good)) if mask[i]]
            cx = int(np.median([p[0] for p in inlier_pts])) + x1
            cy = int(np.median([p[1] for p in inlier_pts])) + y1
            raw_hits.append((name, (cx, cy), inliers))
    # 簇聚合:同坐标 cluster_radius 内多命中归一到 inliers 最高
    raw_hits.sort(key=lambda h: -h[2])  # inliers 降序,高者优先保留
    clustered: list[tuple[str, tuple[int, int], int]] = []
    for name, (cx, cy), inliers in raw_hits:
        if any(abs(cx - ocx) <= cluster_radius and abs(cy - ocy) <= cluster_radius
               for _, (ocx, ocy), _ in clustered):
            continue  # 已被更高 inliers 命中吞并(去重)
        clustered.append((name, (cx, cy), inliers))
    _check_owned_order(clustered, screen, equip_rect)
    return clustered


#: owned 栏同一行的 cy 容差(行内抖动实测 ~10px;仅 SIFT 旧路径的跳格检测用)
_OWNED_ROW_DY: int = 45


def _owned_order_anomaly(pts: list[tuple[int, int]]) -> str | None:
    """owned 栏**行内**跳格检测(纯函数;仅 SIFT 旧路径诊断用)。

    布局:多列网格,行内从右到左连续填充。**跳格只在行内有意义**:某行相邻 icon 的
    x 间距 > 1.8×行内中位步距 = 该行有漏检槽位。
    换行跳变(x 从左列跳回右列)不是跳格 —— 旧欧氏全局中位实现每逢跨行必误报,已废。
    ⚠️ 已知盲区(纯遥测灵敏度限制):行内恰 3 icon 且漏 1 槽时中位不稳检不出;接受现状。
    """
    if len(pts) < 4:
        return None   # 太少无法判连续性
    srt = sorted(pts, key=lambda p: (p[1], -p[0]))
    # 行聚类:cy 与当前行末点差 ≤ _OWNED_ROW_DY → 同行;否则新行
    rows: list[list[tuple[int, int]]] = []
    for p in srt:
        if rows and abs(p[1] - rows[-1][-1][1]) <= _OWNED_ROW_DY:
            rows[-1].append(p)
        else:
            rows.append([p])
    for row in rows:
        if len(row) < 3:
            continue   # 两点无中位可判(首行独立布局常见,直接放行)
        xs = sorted(p[0] for p in row)
        gaps = [b - a for a, b in zip(xs, xs[1:], strict=False)]
        med = sorted(gaps)[len(gaps) // 2]
        if med <= 0:
            continue
        for i, g in enumerate(gaps):
            if g > 1.8 * med:
                return (f'跳格 行内x[{xs[i]}]->[{xs[i + 1]}] 间距{g}>1.8×中位{med}'
                        f'(该行可能漏检)')
    return None


def _check_owned_order(
    equips: list[tuple[str, tuple[int, int], int]],
    screen: MatLike,
    equip_rect: tuple[int, int, int, int],
) -> None:
    """owned 栏顺序异常检测(诊断留证,无行为影响;仅 SIFT 旧路径):行内跳格记 ``[cw!]`` + 存图。"""
    pts = [(e[1][0], e[1][1]) for e in equips]
    anomaly = _owned_order_anomaly(pts)
    if anomaly is None:
        return
    x1, y1, x2, y2 = equip_rect
    cw_log('read_equips', step='order', target='owned', attn=True,
           anomaly=anomaly, count=len(equips),
           shot=cw_shot(screen[y1:y2, x1:x2], 'owned_anomaly'))


# ===== 穿戴装备识别(below-avatar icon;multi-scale TM 替 SIFT)=====
# below-avatar icon = 角色已穿装备的小图标(头像下方)。**icon 固定 ~32px,不随装备数变**;
# SIFT patch 天花板对 32px 小 icon 失效 → multi-scale TM(98px 模板缩到 ~32px)+ NMS(同位置取最高,
# 防合成材料误匹配:滑轮鞋/折叠小刀同 icon 位置)。实测:3件全中 0.745-0.781 @ scale0.33;
# threshold 0.6 baseline。
_EQUIP_TM_SCALES: tuple[float, ...] = (0.30, 0.33, 0.35, 0.37)  # 98px→29-36px;icon 32-34px 随位置变(梯形视角:前排~32px/后排最右~34px)
# below-avatar icon 横排布局:icon 相对 below cx 的 offset,件数决定。
# 1件{0} / 2件{-21,+21} / 3件{-43,0,+43};候选点(5个)覆盖所有可能。
_EQUIP_CANDIDATES: tuple[int, ...] = (-43, -21, 0, 21, 43)
_EQUIP_LAYOUTS: tuple[tuple[int, ...], ...] = ((-43, 0, 43), (-21, 21), (0,))  # 3件/2件/1件,大到小(完整布局优先)


def load_equip_tm_grays(equip_dir: Path) -> dict[str, MatLike]:
    """加载 cw_equip 模板为 gray dict(``{name: gray}``;TM 用)。

    与 ``load_equip_templates`` 互补:本函数返简单 gray(TM matchTemplate 用),后者返 SIFT 预计算
    (keypoints/descriptors)。两套并存 —— 装备区 icon 大(~70px)与 below-avatar mini icon 小
    (~35px,SIFT 失效用 TM)各取所长。
    """
    grays: dict[str, MatLike] = {}
    for png in sorted(equip_dir.glob('*.png')):
        img = cv2.imdecode(np.fromfile(str(png), np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        grays[png.stem] = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return grays


def read_equipped_below(
    screen: MatLike,
    tmpl_grays: dict[str, MatLike],
    below_rects: list[tuple[int, Rect]],
    scales: tuple[float, ...] = _EQUIP_TM_SCALES,
    threshold: float = 0.6,
    nms_radius: int = 18,
    miss_threshold: float = 0.55,
) -> dict[int, list[str]]:
    """每槽 below-avatar 区 multi-scale TM + NMS → ``{slot_idx: [装备名]}``(纯 CV,可离线测)。

    识别**角色已穿装备**(头像下方 icon),与 ``read_equips``(装备区 owned)互补。

    **icon ~32-34px 随位置变**:不随装备数变,但随角色位置/梯形视角略变(前排 ~32px /
    后排最右 ~34px)。multi-scale 枚举覆盖,每个 icon 在最接近 scale 命中最高 val;
    NMS 防同位置多命中(合成材料:滑轮鞋/折叠小刀)。

    :param screen: 备战画面截图(RGB,1080p;sr_od ``cv2_utils.read_image`` 约定,非 BGR)。
    :param tmpl_grays: ``load_equip_tm_grays`` 结果(``{name: gray}``,98px 大图模板)。
    :param below_rects: ``[(slot_idx, Rect), ...]`` —— 每槽 below-avatar 搜索区(调用方从 screen_info
        槽 rect 算:avatar 底部下方,icon y 中心 ≈ avatar_y2 + 14,见 ``cw_identity_obs.avatar_to_below``)。
    :param scales: 98px 模板缩放档(覆盖 ~32-34px icon)。
    :param threshold: TM 命中阈值;0.6(实测 top1 0.74+,保守留余量)。
    :param nms_radius: 同位置去重半径(icon 间距 ~35px → 18)。
    :param miss_threshold: MISS 日志阈值;val 在 [miss_threshold, threshold) 的近命中记 MISS(可能漏检)。
        MISS 经 ``cw_observe.cw_log`` 记(``[cw!]``),grep ``\\[cw!\\].*MISS`` 找。
    :return: ``{slot_idx: [装备名]}``;空槽 / 无命中 → 该 slot 不在 dict。

    纯读(只 TM screen + templates,不写 session/全局),可进 recognizer / op(并发安全)。
    """
    out: dict[int, list[str]] = {}
    for slot_idx, rect in below_rects:
        crop = cv2.cvtColor(screen[rect.y1:rect.y2, rect.x1:rect.x2], cv2.COLOR_RGB2GRAY)  # sr_od screen 是 RGB(cv2_utils.read_image),非 BGR
        raw: list[tuple[str, float, int]] = []  # (name, val, icon_center) 命中(>=threshold)
        near: dict[str, float] = {}  # 近命中(name->max val, miss_threshold<=val<threshold),MISS 日志用
        # 大图模板 multi-scale TM(icon ~32-34px 随位置变;缩到 29-36px 覆盖)。
        # scales 语义 = 相对 98px 基准;混合库(plaza 官方烘焙已统一 98px)
        # 归一换算保留作防御(模板若非 98 尺寸仍等效目标像素)。
        for name, tgray in tmpl_grays.items():
            th, tw = tgray.shape
            k = 98.0 / max(tw, th)   # 模板宽→98 基准的换算系数
            for s in scales:
                nw, nh = int(tw * s * k), int(th * s * k)
                if nw < 12 or nh < 12 or nw >= crop.shape[1] or nh >= crop.shape[0]:
                    continue
                resized = cv2.resize(tgray, (nw, nh), interpolation=cv2.INTER_AREA)
                r = cv2.matchTemplate(crop, resized, cv2.TM_CCOEFF_NORMED)
                _, mx, _, mloc = cv2.minMaxLoc(r)
                if mx >= threshold:
                    raw.append((name, float(mx), mloc[0] + nw // 2))  # icon 中心(模板左 + 半宽)
                elif mx >= miss_threshold and mx > near.get(name, 0.0):
                    near[name] = float(mx)
        # NMS:按 icon 中心聚类(±nms_radius),每簇取 val 最高(同 icon 多模板/多尺度命中去重)
        raw.sort(key=lambda t: -t[1])
        kept: list[tuple[str, float, int]] = []  # (name, val, icon_center)
        for name, val, icon_center in raw:
            if any(abs(icon_center - kc) <= nms_radius for _, _, kc in kept):
                continue
            kept.append((name, val, icon_center))
        # 布局约束:icon 中心归候选点(cx±43/±21/0),取最大完整 1/2/3件布局,剔孤立误检 + 缺候选 MISS。
        equipped = _select_equipped_layout(kept, crop.shape[1] // 2, slot_idx, screen, rect)
        if equipped:
            out[slot_idx] = equipped
        # icon 数守卫:角色 below 最多3件,>3 = 误检/邻槽串入
        if len(kept) > 3:
            cw_log('read_equipped', target=f'slot={slot_idx}', attn=True,
                   anomaly=f'icon数{len(kept)}>3(误检/邻槽串入)', equips=str([n for n, _, _ in kept]),
                   shot=cw_shot(screen[rect.y1:rect.y2, rect.x1:rect.x2], f'over3_slot{slot_idx}'))
        # MISS 日志:近命中(val 刚低于 threshold)可能是漏检。
        # ⚠️ 分级([cw!]=需关注/[cw]=普通,语义详 ``cw_observe``):清晰读(val_top≥0.7)的 near-MISS 是被拒候选
        # (噪声,非漏检)→ [cw] 普通;疑似漏检(val_top<0.7 / kept 空)→ [cw!] 需关注。
        if near:
            kept_names = {n for n, _, _ in kept}
            miss_items = sorted(((n, v) for n, v in near.items() if n not in kept_names), key=lambda t: -t[1])
            if miss_items:
                miss_str = ','.join(f'{n}({v:.2f})' for n, v in miss_items[:5])
                val_top = kept[0][1] if kept else 0.0
                shot = cw_shot(screen[rect.y1:rect.y2, rect.x1:rect.x2], f'miss_slot{slot_idx}')
                cw_log('read_equipped', target=f'slot={slot_idx}', attn=val_top < 0.7,
                       equips=str([n for n, _, _ in kept]), val_top=f'{val_top:.2f}',
                       MISS=f'[{miss_str}]', shot=shot)
    return out


def _select_equipped_layout(
    kept: list[tuple[str, float, int]],
    below_cx: int,
    slot_idx: int,
    screen: MatLike,
    rect: Rect,
) -> list[str]:
    """布局约束选装备:kept icon 中心归候选点(cx±43/±21/0),取最大完整 1/2/3件布局。

    - icon 中心归最近候选(±11 内);非候选 = 孤立(误检,不取)。
    - 命中候选取最大完整布局(3件{-43,0,+43} > 2件{-21,+21} > 1件{0};候选 ⊆ 命中)→ 该布局装备。
    - 更大布局部分中(缺候选)= MISS(漏检)``[cw!]``;无完整布局 = 异常 ``[cw!]`` + 截图。
    """
    cand_name: dict[int, str] = {}
    for name, _val, icon_center in kept:
        off = icon_center - below_cx
        nearest = min(_EQUIP_CANDIDATES, key=lambda c: abs(c - off))
        if abs(nearest - off) <= 11:
            cand_name.setdefault(nearest, name)  # NMS 已 val 降序,首个=最高
    hit = set(cand_name)
    chosen = next((lay for lay in _EQUIP_LAYOUTS if set(lay) <= hit), None)
    if chosen is not None:
        return [cand_name[o] for o in chosen]
    # 无完整布局:CW 每角色最多3件,1/2/3件布局覆盖全部合法配置;无完整布局 = 误检
    # → 返 [] 不返 fallback 候选(防把不可靠候选当 occupied)。anomaly + MISS 日志保留(诊断)。
    if hit:
        cw_log('read_equipped', target=f'slot={slot_idx}', attn=True,
               anomaly=f'无完整1/2/3件布局(命中候选{sorted(hit)})→判空(误检,不返)',
               equips=str([cand_name[o] for o in sorted(cand_name)]),
               shot=cw_shot(screen[rect.y1:rect.y2, rect.x1:rect.x2], f'nolayout_slot{slot_idx}'))
    # MISS:更大布局部分中(缺候选 = 漏检)
    for lay in _EQUIP_LAYOUTS:
        partial = set(lay) & hit
        if partial and not set(lay) <= hit:
            missing = [c for c in lay if c not in hit]
            cw_log('read_equipped', target=f'slot={slot_idx}', attn=True,
                   MISS=f'布局{lay}缺候选{missing}(漏检)',
                   shot=cw_shot(screen[rect.y1:rect.y2, rect.x1:rect.x2], f'layoutmiss_slot{slot_idx}'))
            break
    return []


def ensure_equip_tm_templates(ctx: SrContext) -> dict[str, MatLike] | None:
    """确保 ctx 缓存 cw_equip TM 模板(98px grays);返 ``grays`` 或 None(目录缺)。

    首次 load 缓存 ``ctx.cw_equip_tm_grays``;后续读缓存。recognizer 装备识别的 templates 加载点
    (装备区模板由 ``equip_all._get_templates`` 另加载,不冲突)。

    **并发安全**:幂等(同值重 load 无害);只缓存只读资源(非 session/游戏状态),与运行中 operation 不竞争。
    """
    grays = getattr(ctx, 'cw_equip_tm_grays', None)
    if grays is None:
        base = Path(__file__).resolve().parents[4] / 'assets' / 'template'
        equip_dir = base / 'currency_war' / 'equip_plaza'   # 混合库(plaza 官方 + 手工补充;生成器 gen_plaza_chars.py 产物)
        if not equip_dir.is_dir():
            equip_dir = base / 'currency_war' / 'equip_legacy'   # 回退:旧手工库
        if not equip_dir.is_dir():
            return None
        grays = load_equip_tm_grays(equip_dir)
        ctx.cw_equip_tm_grays = grays
    return grays


def ensure_equip_sift_templates(ctx: SrContext) -> dict[str, tuple[MatLike, tuple, np.ndarray]] | None:
    """确保 ctx 缓存 cw_equip 模板(``read_equips`` / ``read_equip_grid`` 用);返 ``templates`` 或 None(目录缺)。

    首次 ``load_equip_templates`` 缓存 ``ctx.cw_equip_sift_templates``;后续读缓存。

    **并发安全**:幂等(同值重 load 无害);只缓存只读资源(非 session/游戏状态),与运行中 operation 不竞争。
    """
    templates = getattr(ctx, 'cw_equip_sift_templates', None)
    if templates is None:
        base = Path(__file__).resolve().parents[4] / 'assets' / 'template'
        equip_dir = base / 'currency_war' / 'equip_plaza'   # 混合库(同 ensure_equip_tm_templates)
        if not equip_dir.is_dir():
            equip_dir = base / 'currency_war' / 'equip_legacy'   # 回退:旧手工库
        if not equip_dir.is_dir():
            return None
        templates = load_equip_templates(equip_dir)
        ctx.cw_equip_sift_templates = templates
    return templates
