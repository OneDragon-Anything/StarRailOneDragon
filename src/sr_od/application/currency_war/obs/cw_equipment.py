"""cw_equipment 装备视觉识别(**手维护,非生成**)。

数据模型(Equipment / EQUIPMENTS / get_equip)在 ``cw_equipment_data``
(生成器 = ``skills/sr-od-dev-currency-war/scripts/gen_equip_registry.py``;该生成文件为单一源)。
本文件含:装备区**逐格分类**(``read_equip_grid`` / ``read_equips`` / ``read_equip_count``)
与穿戴装备 TM 识别(``read_equipped_below``:头像下方小图标,第一读 + 数字旁 / 火光下两处补读,读不清报 ``EQUIP_UNKNOWN``)。
**拆分目的(R16 P0-1)**:生成器只写 ``cw_equipment_data``,永不覆盖本文件。

装备区识别演进:全域 SIFT(单应变换天然单实例,同模板多格重复只锁一格 → 占用召回 62%)
→ **网格几何 + 逐格 TM 分类**(格几何按 28 帧真值实测标定;同模板多实例问题随逐格独立消失)。
标定与交叉核对基线:``.debug/temp/currency_war/w540_equip_grid/REPORT.md``(171 真值格)。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
from cv2.typing import MatLike

from one_dragon.utils.file_utils import get_project_root
from sr_od.application.currency_war.data.cw_equipment_data import (
    EQUIPMENT_ROSTER,
    EQUIPMENTS,
    Equipment,
    get_equip,
)
from sr_od.application.currency_war.kernel.cw_observe import cw_log, cw_shot

if TYPE_CHECKING:
    from one_dragon.base.geometry.rectangle import Rect
    from sr_od.context.sr_context import SrContext

# 公开 API:re-export 数据(Equipment/EQUIPMENTS/get_equip 来自 cw_equipment_data)+ 装备区逐格识别
# + 穿戴装备 TM 识别(read_equipped_below)
# __all__ 告知 ruff 这些 re-export 非 unused(F401)
__all__ = ['Equipment', 'EQUIPMENTS', 'EQUIPMENT_ROSTER', 'get_equip', 'load_equip_templates', 'read_equips',
           'read_equip_grid', 'read_equip_count', 'EquipCell',
           'EQUIP_UNKNOWN', 'equip_icon_top_y',
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


# ===== 装备区网格几何(28 帧真值实测标定)=====
# 实测格距 ~75px(plaza 模板素材的 ~98px 是素材尺寸,非格距)。
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
# 横幅两态:右上「装备追踪中」标签出现时装备栏整体下移一个定值(存档帧
# 实测 20/24/28 为同一真实值 ±4px 扫描量化噪声,取 24),无标签帧 δ=0。每帧按候选
# 档逐档分类、以占用格峰心偏移自验对齐,两档皆不对齐才回退 _detect_zone_dy 全档扫
# 描兜底——替代旧「每帧 14 档 × 15 格 × 全库」扫描(单帧 ~7-11s 降至常态 1 档分类 ~2s)。
_EQUIP_DY_CANDIDATES: tuple[int, ...] = (0, 24)
# 兜底全档扫描(仅在候选档自验全败时触发;覆盖未知第三布局态,真值域实测 -8..+28)
_EQUIP_DY_SCAN: tuple[int, ...] = tuple(range(-8, 45, 4))
_EQUIP_DY_SCALE: float = 0.70                          # δ 扫描用单一尺度(降耗;全库模板)


@dataclass
class EquipCell:
    """装备区一格的识别结果(15 槽全量返回;占用/空两态)。

    坐标系:``row`` = 物理行,0 = row1 材料堆叠带(带数量数字),1-6 = 其下装备行(自上而下);
    ``col`` = 物理列 0-2(左→右);row1 合法列 = 0/1/2,装备行合法列 = 1/2(左列无格)。
    ``cx/cy`` = 格心 1080p 绝对坐标(TM 峰心,非名义格点)。

    前置契约:输入必须是干净备战画面(调用方经建档画面判定保证,面板遮挡态各有
    独立建档、不会命中备战)——识别器不做画面状态判断,遮挡帧不进本管线。
    """
    row: int
    col: int
    cx: int
    cy: int
    name: str | None      # 占用 = 模板规范名;空 = None
    score: float          # TM 最高响应(TM_CCOEFF_NORMED);占用判定阈 = _EQUIP_OCC_THR
    count: str | None = None  # row1 堆叠数量('1'-'5'/'∞');仅 read_equip_count 填充


def _equip_slot_centers(dy: int) -> list[tuple[int, int, int, int]]:
    """全部格心 ``(row, col, cx, cy)``(名义格点 + 横幅位移 dy)。"""
    out = [(0, c, x, _EQUIP_ROW1_Y + dy) for c, x in enumerate(_EQUIP_COL_ROW1)]
    for r in range(_EQUIP_EQ_ROWS):
        y = _EQUIP_ROW0_EQ_Y + _EQUIP_ROW_STEP * r + dy
        # 装备行列号 1/2(col 0 = 左列,仅 row1 存在;坐标系见 EquipCell)
        out.extend((r + 1, c + 1, x, y) for c, x in enumerate(_EQUIP_COL_EQ))
    return out


def _fill_order_slots(dy: int) -> tuple[list[tuple[int, int, int, int]], list[tuple[int, int, int, int]]]:
    """栏内**填充序**格点,分两段(各段独立做「首空即停」剪枝)。

    填充规律(用户口述·权威;知识档 equipment_mechanics.md §5):
    ① row1 消耗品带右→左;② 装备区右列自上而下、再左列自上而下;获得按序 append,
    栏内无空洞 → 每段扫描遇首空即停(其后必空,剪枝;异常由装备期望态对账暴露)。

    :return: ``(tool_slots, equip_slots)``,各为 ``(row, col, cx, cy)`` 列表。
    """
    tool = [(0, c, x, _EQUIP_ROW1_Y + dy)
            for c, x in sorted(enumerate(_EQUIP_COL_ROW1), key=lambda t: -t[1])]
    equip = []
    for c, x in sorted(enumerate(_EQUIP_COL_EQ), key=lambda t: -t[1]):
        for r in range(_EQUIP_EQ_ROWS):
            equip.append((r + 1, c + 1, x, _EQUIP_ROW0_EQ_Y + _EQUIP_ROW_STEP * r + dy))
    return tool, equip


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


# 对齐自验阈:候选档 ±4px 量化域的 2 倍。TM 分数不能作对齐判据(归一化互相关平移
# 不变,错位 28px 帧部分重叠格仍 0.93+,实测「攻略已应用」δ=0 档);峰心偏移才是
# 几何对齐的直接测量——对齐档 ≈0,错位档系统偏 ~20-28px。
_EQUIP_DY_ALIGN_TOL: int = 8


def _classify_grid(screen: MatLike, scaled: dict[float, list[tuple[str, np.ndarray]]],
                   dy: int, tmpl_names: set[str]) -> tuple[list[EquipCell], list[int]]:
    """按填充序逐格分类,各段首空格即停(剪枝;分段规律见 ``_fill_order_slots``)。

    row1 消耗品带只匹配**工具模板子集**(注册表 category='工具';全库分类与穿戴
    决策都不涉及消耗品,子集 ~10 模板 vs 全库 157)——owned 全量快照仍含工具
    (采集写端契约不变,快照消费 cells 的 name 集合)。

    :return: ``(cells, dy_offs)``;``dy_offs`` = 占用格 TM 峰心垂直偏移绝对值列表
        (候选档对齐自验用,见 ``_EQUIP_DY_ALIGN_TOL``)。
    """
    tool_names = {n for n in tmpl_names
                  if _registry_category(n.removesuffix(_EQUIP_VARIANT_SUFFIX)) == '工具'}
    tool_scaled = {s: [tg for tg in scaled[s] if tg[0] in tool_names] for s in scaled}
    cells: list[EquipCell] = []
    dy_offs: list[int] = []

    def _scan(slots: list[tuple[int, int, int, int]], pool: dict) -> None:
        """单段填充序扫描:遇首空停(本段后续格不扫,另段不受影响)。"""
        for row, col, cx, cy in slots:
            crop = _gray_crop(screen, cx, cy)
            name, score, dx, dy2 = _classify_cell(crop, pool, _EQUIP_SCALES_FAST)
            if score < _EQUIP_OCC_THR:
                name2, score2, dx2, dy22 = _classify_cell(crop, pool, _EQUIP_SCALES_FULL)
                if score2 > score:
                    name, score, dx, dy2 = name2, score2, dx2, dy22
            occupied = name is not None and score >= _EQUIP_OCC_THR
            if not occupied:
                break   # 填充序首空 → 其后必空(剪枝;异常由装备期望态对账暴露)
            name = _variant_arbitrate(screen, cx, cy, name, tmpl_names)
            dy_offs.append(abs(dy2))
            cells.append(EquipCell(
                row=row, col=col,
                cx=cx + dx, cy=cy + dy2,
                name=name, score=float(score),
            ))

    tool_slots, equip_slots = _fill_order_slots(dy)
    _scan(tool_slots, tool_scaled)
    _scan(equip_slots, scaled)
    return cells, dy_offs


def _registry_category(name: str) -> str:
    """模板名 → 注册表 category(未登记 = 空串;·特权 变体已由调用方去后缀)。"""
    from sr_od.application.currency_war.data.cw_equipment_data import get_equip
    eq = get_equip(name)
    return eq.category if eq is not None else ''


def read_equip_grid(screen: MatLike,
                    templates: dict[str, tuple[MatLike, tuple, np.ndarray]]) -> list[EquipCell]:
    """装备区**逐格分类**:网格几何分格 → 按填充序逐格 TM 全库 → 占用格集(至首空格)。

    **前置契约(外层判干净)**:输入必须是干净备战画面——无任何面板/浮窗/overlay
    遮挡,由调用方经建档画面判定保证(``货币战争-备战`` id_mark 含右下「出战」按钮,
    恰被角色详情面板覆盖,面板态天然识别不成备战;角色详情/装备详情/装备浮窗/
    开商店各有独立建档)。识别器内不做任何画面状态判断。

    同模板多实例问题随逐格独立消失(全域 SIFT 单应只锁一格,是旧实现 62% 召回的根因)。
    格几何 = 实测等距网格(75px;row1 三列材料带 + 其下六行两列装备列);「装备追踪中」
    标签的两态位移由候选档逐档自验兜住(见 ``_EQUIP_DY_CANDIDATES``);扫描按栏内
    填充序、首空格即停(填充规律见 ``_fill_order_slots``)。
    占用格低分时全尺度回扫一次(个别渲染态快档 < 阈、慢档过阈;实测 精密拆装扳手 依赖此兜底)。

    :param screen: 干净备战画面截图(RGB,1080p;``cv2_utils.read_image`` 约定)。
    :param templates: ``load_equip_templates`` 结果(只用其 gray,复用同一份缓存)。
    :return: 占用格 ``EquipCell`` 列表(按填充序,至首空格;空格不返回——
        消费方按 name 计数/遍历,无需空格槽位)。

    纯读(不写 session/全局;``_SCALED_CACHE`` 是只读资源缓存),可进 recognizer / op。
    """
    scaled = _scaled_template_cache(templates)
    tmpl_names = set(templates)
    for _dy in _EQUIP_DY_CANDIDATES:
        cells, dy_offs = _classify_grid(screen, scaled, _dy, tmpl_names)
        # 对齐自验:占用格峰心垂直偏移中位 ≤ 容忍域 = 该档对齐(判据见 _EQUIP_DY_ALIGN_TOL)
        if dy_offs and sorted(dy_offs)[len(dy_offs) // 2] <= _EQUIP_DY_ALIGN_TOL:
            return cells
    # 两档候选皆不对齐:未知第三布局态或装备区真空 → 全档扫描兜底 + [cw!] 留痕
    # (游戏改布局时从这里第一时间暴露;真空帧输出仍为空,与旧扫描语义一致)
    dy = _detect_zone_dy(screen, scaled)
    cw_log('read_equip_grid', step='dy_fallback', attn=True,
           anomaly=f'候选档{_EQUIP_DY_CANDIDATES}皆不对齐 → 全档扫描 δ={dy}')
    cells, _offs = _classify_grid(screen, scaled, dy, tmpl_names)
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
    28 帧真值交叉核对召回 171/171、零误检;第三元素语义由 SIFT inliers 改为 ``int(score*100)``
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
    """owned 栏顺序异常检测(诊断保留证据,无行为影响;仅 SIFT 旧路径):行内跳格记 ``[cw!]`` + 存图。"""
    pts = [(e[1][0], e[1][1]) for e in equips]
    anomaly = _owned_order_anomaly(pts)
    if anomaly is None:
        return
    x1, y1, x2, y2 = equip_rect
    cw_log('read_equips', step='order', target='owned', attn=True,
           anomaly=anomaly, count=len(equips),
           shot=cw_shot(screen[y1:y2, x1:x2], 'owned_anomaly'))


# ===== 穿戴装备识别(below-avatar icon;multi-scale TM + 两处补读)=====
# below-avatar icon = 角色已穿装备的小图标(头像下方)。**icon 固定 ~32px,不随装备数变**;
# SIFT patch 天花板对 32px 小 icon 失效 → multi-scale TM(98px 模板缩到 ~32px)+ NMS(同位置取最高,
# 防合成材料误匹配:滑轮鞋/折叠小刀同 icon 位置)。
# 小图标上常叠着别的东西——数量数字贴在左下角、被高亮卡片的火光压住顶边、整张卡片带高亮框。叠住时真图标的
# 峰分掉到 0.40–0.57,而空槽底板上的假峰能到 0.64(空槽底板偏蓝时「碎星斩舰刀」的背景假峰),单看分数分不开。
# 读链因此分三读一合并:
# ① 整条比一遍,峰过「矩形判空」「峰尖锐度」两道门;
# ② 数字旁补读——找到数量数字,把数字框排除后只在它贴着的图标位置附近重比;
# ③ 火光下补读——认出火光,把图标顶边以上几行排除后只在 5 个候选位置附近重比;
# ④ 合并去重,按布局取最大完整的一套。分数不到可信线的名字、有装备线索却读不全的格子,报 EQUIP_UNKNOWN。
# 尖锐度 = 峰值减去相关图上距峰 _EQUIP_TM_PEAK_RING 环带内的最大值——真图标是定位到 32px 小方图上的尖峰,
# 背景花纹与模板的相关是宽泛的,平移几像素分数几乎不掉。标定依据与回归样本见 sr-od-test/test/sr_od/application/currency_war/obs/test_cw_equipment.py。
_EQUIP_TM_SCALES: tuple[float, ...] = (0.30, 0.33, 0.35, 0.37)  # 98px→29-36px;icon 32-34px 随位置变(梯形视角:前排~32px/后排最右~34px)
# below-avatar icon 横排布局:icon 相对 below cx 的 offset,件数决定。
# 1件{0} / 2件{-21,+21} / 3件{-43,0,+43};候选点(5个)覆盖所有可能。
_EQUIP_CANDIDATES: tuple[int, ...] = (-43, -21, 0, 21, 43)
_EQUIP_LAYOUTS: tuple[tuple[int, ...], ...] = ((-43, 0, 43), (-21, 21), (0,))  # 3件/2件/1件,大到小(完整布局优先)
#: 读不清的占位名,不是装备名:某位置有装备但名字没认出来,或该格子有装备线索却读不全。消费方按「看不清」处理。
EQUIP_UNKNOWN: str = 'unknown'
#: 第一读的峰分下限(TM_CCOEFF_NORMED)。被叠住的真图标峰分最低量到 0.40 一带,所以下限放这里;
#: 低分放进来的空槽假峰由下面两道门挡。
_EQUIP_TM_ACCEPT: float = 0.40
#: 名字可信线:第一读里峰分不到这条线的名字不报,该位置报 ``EQUIP_UNKNOWN``;补读只收过线的峰。
#: 依据:已入库模板能命名的干净真图标最低峰 0.59;0.40–0.58 一段里读过对的名字,也读错过名字。
_EQUIP_TM_TRUST: float = 0.58
#: 峰尖锐度门槛(第一读与数字旁补读同用)。标定(328 帧实机备战画面普查,空槽 3107 个):第一读配 0.20 时空槽零误读,
#: 放到 0.15 出 7 个空槽误读。
_EQUIP_TM_PEAK_SHARP: float = 0.20
#: 火光下补读的尖锐度门槛:火光下的真图标尖锐度量到 0.18–0.62,门槛随之下移;只在该补读内生效。
_EQUIP_FLAME_PEAK_SHARP: float = 0.15
#: 尖锐度环带的内、外半径(像素,相关图坐标系);越界处按存在部分取。全向环——纵向环 / 十字远环都把
#: 空槽假峰抬到与真图标同量级,分不开。
_EQUIP_TM_PEAK_RING: tuple[int, int] = (5, 14)
#: 矩形判空:命中矩形内「棋盘底色」像素占比的上限。棋盘底色 = 搜索区底边左右各 30 像素合起来的中位色,与它
#: 各通道差都不超过 ``_EQUIP_BG_TOL`` 的像素算底色。空槽上的假峰整个矩形落在底板上(占比接近 1),真图标不超过 0.09。
_EQUIP_BG_TOL: int = 25
_EQUIP_BG_MAX: float = 0.05
#: 图标中心离最近候选点不超过这么多像素才归到该候选点上;更远的算孤立误检,不取。
_EQUIP_LAYOUT_TOL: int = 11

# ----- 数量数字(贴在图标左下角的白字黑边数字)-----
#: 白字:三个通道都不低于 ``_EQUIP_BADGE_WHITE``;黑边:三个通道都不高于 ``_EQUIP_BADGE_BLACK``。
_EQUIP_BADGE_WHITE: int = 225
_EQUIP_BADGE_BLACK: int = 40
#: 一个数字白块的高、宽(像素)和最少像素数。
_EQUIP_DIGIT_H: tuple[int, int] = (16, 20)
_EQUIP_DIGIT_W: tuple[int, int] = (3, 13)
_EQUIP_DIGIT_AREA: int = 25
#: 数字白块顶边所在的行不小于这个值(上面还放得下一个图标);数字的纵向位置随前后排变,所以不限固定行。
_EQUIP_BADGE_MIN_Y: int = 12
#: 数字白块外扩 2 像素的一圈里,黑像素数达到白字像素数的这个倍数才算数量数字(图标自带的白色块接近 0)。
_EQUIP_BADGE_RING_BLACK: float = 0.25
#: 一个数量数字(几位数字合起来)的总宽范围(像素);同一个数字里相邻两位之间的空隙上限(像素)。
_EQUIP_BADGE_W: tuple[int, int] = (9, 42)
_EQUIP_BADGE_GAP: int = 8
#: 图标左上角相对数字框左上角的偏移(像素):数字贴在图标左下角。
_EQUIP_BADGE_ICON_DX: int = 1
_EQUIP_BADGE_ICON_DY: int = -19

# ----- 补读(数字旁 / 火光下):在期望位置附近,把叠住图标的像素排除后重比 -----
#: 图标左上角在期望位置周围 ``_EQUIP_EXTRA_SEARCH`` 像素内找峰;相关图取期望位置周围 ±``_EQUIP_EXTRA_WINDOW``
#: 的一块来算(要盖住尖锐度环带)。
_EQUIP_EXTRA_SEARCH: int = 7
_EQUIP_EXTRA_WINDOW: int = 21
#: 数字框外扩几像素一起排除出比对。
_EQUIP_BADGE_OUTLINE: int = 3
#: 补读里参与比对的像素占模板像素的比例下限:只剩一小撮像素时分数不可信。
_EQUIP_EXTRA_MIN_KEPT: float = 0.5
#: 认火光:搜索区上半部(前 ``_EQUIP_FLAME_ROWS`` 行)、图标横向范围(中线两侧各 ``_EQUIP_FLAME_HALF_W`` 像素)内,
#: R、G、B 分别不低于 / 不低于 / 不高于 ``_EQUIP_FLAME_RGB`` 的像素达到 ``_EQUIP_FLAME_MIN_PIXELS`` 个。
#: 标定:带火光的格子 249–433 个,其余格子最多 138 个。
_EQUIP_FLAME_ROWS: int = 20
_EQUIP_FLAME_HALF_W: int = 55
_EQUIP_FLAME_RGB: tuple[int, int, int] = (240, 200, 215)
_EQUIP_FLAME_MIN_PIXELS: int = 200
#: 火光下补读排除的行数:图标顶边以上(含顶边)这么多行不参与比对——火光横穿图标上沿,只盖住最上面三四行;
#: 排到 8 行、12 行开始出假读。
_EQUIP_FLAME_CUT_ROWS: int = 5
#: 图标顶边在搜索区里的行号,按排取(前排卡片更靠下,图标也更靠下)。
_EQUIP_ICON_TOP_Y_FRONT: int = 19
_EQUIP_ICON_TOP_Y_BACK: int = 10
#: 典型图标(34 像素)的半宽:把「图标中心在某个候选位置」换算成「模板左上角的期望横坐标」时用。
_EQUIP_ICON_HALF: int = 17
#: 局部峰枚举:相关图与该核的最大值滤波结果逐点相等 = 11×11 邻域内的局部极大值。
_EQUIP_PEAK_MAX_FILTER_KERNEL: np.ndarray = np.ones((11, 11), np.uint8)
#: 局部峰枚举:彼此欧氏距离小于该像素数的峰只留最高者;每模板每尺度最多取 _EQUIP_PEAK_MAX 个。
#: 同一裁片里某模板的宽泛假峰可能高于它的真图标峰,只看最高峰会把真图标挡在尖锐度评估之外,故枚举多个。
_EQUIP_PEAK_MIN_DIST: int = 5
_EQUIP_PEAK_MAX: int = 5


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


def _peak_sharpness(corr: np.ndarray, peak_xy: tuple[int, int]) -> float:
    """单个相关峰的尖锐度 = 峰值 − 距峰 ``_EQUIP_TM_PEAK_RING`` 环带内(全向、越界按存在部分取)的最大值。

    非有限值按 −1 处理(环带内有非有限值时整体返回 −1)。供实现与回归测试复算共用。
    """
    lx, ly = peak_xy
    peak = corr[ly, lx]
    if not np.isfinite(peak):
        return -1.0
    h, w = corr.shape
    yy, xx = np.ogrid[:h, :w]
    d2 = (yy - ly) ** 2 + (xx - lx) ** 2
    r_in, r_out = _EQUIP_TM_PEAK_RING
    ring = corr[(d2 >= r_in * r_in) & (d2 <= r_out * r_out)]
    if ring.size == 0 or not np.all(np.isfinite(ring)):
        return -1.0
    return float(peak - ring.max())


def _local_peaks(corr: np.ndarray) -> list[tuple[int, int, float]]:
    """相关图里 ≥ ``_EQUIP_TM_ACCEPT`` 的局部极大值(11×11 最大值滤波平台点),按分降序。

    彼此欧氏距离 < ``_EQUIP_PEAK_MIN_DIST`` 的只留最高者,最多 ``_EQUIP_PEAK_MAX`` 个。
    返回 ``[(x, y, 分), ...]``,坐标为相关图坐标(模板左上角)。
    """
    plateau = (corr >= _EQUIP_TM_ACCEPT) & (corr == cv2.dilate(corr, _EQUIP_PEAK_MAX_FILTER_KERNEL))
    ys, xs = np.nonzero(plateau)
    if len(ys) == 0:
        return []
    kept: list[tuple[int, int, float]] = []
    for j in np.argsort(-corr[ys, xs], kind='stable'):
        x, y = int(xs[j]), int(ys[j])
        if any((x - kx) ** 2 + (y - ky) ** 2 < _EQUIP_PEAK_MIN_DIST ** 2 for kx, ky, _ in kept):
            continue
        kept.append((x, y, float(corr[y, x])))
        if len(kept) >= _EQUIP_PEAK_MAX:
            break
    return kept


def _board_mask_integral(crop_rgb: MatLike) -> np.ndarray:
    """矩形判空用的积分图:棋盘底色像素记 1,其余记 0(判据与棋盘底色的取法见 ``_EQUIP_BG_MAX`` 注释)。

    :param crop_rgb: below-avatar 搜索区(RGB)。
    :return: ``cv2.integral`` 的结果;矩形 (x, y, w, h) 内的底色像素数 =
        ``ii[y + h, x + w] - ii[y, x + w] - ii[y + h, x] + ii[y, x]``。
    """
    bottom = np.vstack([crop_rgb[-1, :30], crop_rgb[-1, -30:]]).astype(np.int16)
    board = (np.abs(crop_rgb.astype(np.int16) - np.median(bottom, axis=0)[None, None, :]).max(axis=2) <= _EQUIP_BG_TOL)
    return cv2.integral(board.astype(np.uint8))


def _find_count_badges(crop_rgb: MatLike) -> list[tuple[int, int, int, int]]:
    """搜索区里的数量数字,返回每个数字的框 ``[(x1, y1, x2, y2), ...]``(含端点)。

    一位数字 = 白字连通块,高、宽、像素数在 ``_EQUIP_DIGIT_*`` 范围内,且外扩 2 像素的一圈里黑像素够多
    (见 ``_EQUIP_BADGE_RING_BLACK``);同一个数字的几位是一行里相邻的白块,按行合并后总宽要在 ``_EQUIP_BADGE_W`` 内。

    :param crop_rgb: below-avatar 搜索区(RGB)。
    """
    white = (crop_rgb.min(axis=2) >= _EQUIP_BADGE_WHITE).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(white, connectivity=8)
    black = (crop_rgb.max(axis=2) <= _EQUIP_BADGE_BLACK)
    digits: list[list[int]] = []
    for i in range(1, count):
        x, y, w, h, area = (int(v) for v in stats[i])
        if not (_EQUIP_DIGIT_H[0] <= h <= _EQUIP_DIGIT_H[1] and _EQUIP_DIGIT_W[0] <= w <= _EQUIP_DIGIT_W[1]
                and area >= _EQUIP_DIGIT_AREA and y >= _EQUIP_BADGE_MIN_Y):
            continue
        comp = (labels == i)
        ring = (cv2.dilate(comp.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0) & ~comp
        if int((black & ring).sum()) < _EQUIP_BADGE_RING_BLACK * area:
            continue
        digits.append([x, y, x + w - 1, y + h - 1])
    digits.sort()
    merged: list[list[int]] = []
    for digit in digits:
        if (merged and 0 <= digit[0] - merged[-1][2] - 1 <= _EQUIP_BADGE_GAP
                and abs(digit[1] - merged[-1][1]) <= 3):
            merged[-1][0] = min(merged[-1][0], digit[0])
            merged[-1][2] = max(merged[-1][2], digit[2])
        else:
            merged.append(list(digit))
    return [tuple(b) for b in merged if _EQUIP_BADGE_W[0] <= b[2] - b[0] + 1 <= _EQUIP_BADGE_W[1]]


def _is_flame(crop_rgb: MatLike) -> bool:
    """这条搜索区是否压着被高亮卡片的火光(判据见 ``_EQUIP_FLAME_MIN_PIXELS`` 注释)。输入 RGB。"""
    cx = crop_rgb.shape[1] // 2
    top = crop_rgb[:min(_EQUIP_FLAME_ROWS, crop_rgb.shape[0]), cx - _EQUIP_FLAME_HALF_W:cx + _EQUIP_FLAME_HALF_W].astype(np.int16)
    r_min, g_min, b_max = _EQUIP_FLAME_RGB
    return int(((top[:, :, 0] >= r_min) & (top[:, :, 1] >= g_min) & (top[:, :, 2] <= b_max)).sum()) >= _EQUIP_FLAME_MIN_PIXELS


def equip_icon_top_y(row_prefix: str) -> int:
    """这一排的装备图标顶边在 below-avatar 搜索区里的行号(火光下补读按它定从哪一行开始比)。

    :param row_prefix: 画面建档里的排前缀(前排 / 后排 / 后排 N 槽 / 备战栏);前排取 ``_EQUIP_ICON_TOP_Y_FRONT``,
        其余取 ``_EQUIP_ICON_TOP_Y_BACK``。
    """
    return _EQUIP_ICON_TOP_Y_FRONT if row_prefix == '前排' else _EQUIP_ICON_TOP_Y_BACK


def _resized_templates(
    tmpl_grays: dict[str, MatLike],
    scales: tuple[float, ...],
) -> dict[tuple[int, int], list[tuple[str, MatLike]]]:
    """模板按各尺度缩好,按缩放后的 (高, 宽) 分组:``{(高, 宽): [(名字, 灰度图), ...]}``。一次读链只缩一遍,第一读与补读共用。"""
    out: dict[tuple[int, int], list[tuple[str, MatLike]]] = {}
    for name, tgray in tmpl_grays.items():
        th, tw = tgray.shape
        k = 98.0 / max(tw, th)   # 模板宽→98 基准的换算系数;scales 语义 = 相对 98px 基准
        for s in scales:
            nw, nh = int(tw * s * k), int(th * s * k)
            if nw < 12 or nh < 12:
                continue
            out.setdefault((nh, nw), []).append((name, cv2.resize(tgray, (nw, nh), interpolation=cv2.INTER_AREA)))
    return out


def _masked_ncc(patches: np.ndarray, keep: np.ndarray, templ: np.ndarray) -> np.ndarray:
    """逐位置的遮罩归一化相关:只在参与像素上做零均值归一化,与 TM_CCOEFF_NORMED 同义。

    :param patches: (位置数, 像素数) 灰度小块。
    :param keep: (位置数, 像素数) 布尔阵,True = 该像素参与比对。
    :param templ: (模板数, 像素数) 模板灰度。
    :return: (位置数, 模板数);分母为 0 的位置记 -1。
    """
    p = patches * keep
    nk = keep.sum(axis=1).astype(np.float32)
    cross = p @ templ.T
    sum_p = p.sum(axis=1)
    sum_p2 = (p * p).sum(axis=1)
    kf = keep.astype(np.float32)
    sum_t = kf @ templ.T
    sum_t2 = kf @ (templ * templ).T
    num = cross - sum_p[:, None] * sum_t / nk[:, None]
    var_p = sum_p2 - sum_p * sum_p / nk
    var_t = sum_t2 - sum_t * sum_t / nk[:, None]
    den = np.sqrt(np.maximum(var_p, 0)[:, None] * np.maximum(var_t, 0))
    return np.where(den > 1e-6, num / np.maximum(den, 1e-6), -1.0)


def _extra_peaks(
    gray: MatLike,
    ex_lx: int,
    ex_ly: int,
    excl: np.ndarray,
    resized: dict[tuple[int, int], list[tuple[str, MatLike]]],
    min_sharp: float,
    min_kept: float = 0.0,
) -> list[tuple[str, float, int]]:
    """补读:在期望位置附近逐位置做「``excl`` 标记的像素不参与」的归一化相关,每块模板取分数最高的一处。

    :param gray: 搜索区灰度图。
    :param ex_lx: 图标左上角的期望横坐标(相关图坐标)。
    :param ex_ly: 图标左上角的期望纵坐标(相关图坐标)。
    :param excl: 与 ``gray`` 同形的布尔阵,True = 该像素不参与比对(数字框、火光盖住的行)。
    :param resized: ``_resized_templates`` 的结果。
    :param min_sharp: 尖锐度门槛;峰分门槛固定用 ``_EQUIP_TM_TRUST``。
    :param min_kept: 参与比对的像素占模板像素的比例下限(见 ``_EQUIP_EXTRA_MIN_KEPT``)。
    :return: 过门的 ``[(名字, 峰分, 图标中心 x)]``,按峰分降序;每块模板最多一处。
    """
    best: dict[str, tuple[float, int]] = {}
    win = _EQUIP_EXTRA_WINDOW
    r_in, r_out = _EQUIP_TM_PEAK_RING
    for (h, w), items in resized.items():
        if h >= gray.shape[0] or w >= gray.shape[1]:
            continue
        lxs = np.arange(max(0, ex_lx - win), min(gray.shape[1] - w, ex_lx + win) + 1)
        lys = np.arange(max(0, ex_ly - win), min(gray.shape[0] - h, ex_ly + win) + 1)
        if lxs.size == 0 or lys.size == 0:
            continue
        windows = np.lib.stride_tricks.sliding_window_view(gray, (h, w))
        patches = windows[np.ix_(lys, lxs)].reshape(lys.size * lxs.size, h * w).astype(np.float32)
        gx = lxs[None, :, None, None] + np.arange(w)[None, None, None, :]
        gy = lys[:, None, None, None] + np.arange(h)[None, None, :, None]
        keep = (~excl[gy, gx]).reshape(lys.size * lxs.size, h * w)
        templ = np.stack([t.reshape(-1) for _name, t in items]).astype(np.float32)
        with np.errstate(invalid='ignore', divide='ignore'):
            ncc = _masked_ncc(patches, keep, templ).reshape(lys.size, lxs.size, len(items))
        central = ((np.abs(lys[:, None] - ex_ly) <= _EQUIP_EXTRA_SEARCH)
                   & (np.abs(lxs[None, :] - ex_lx) <= _EQUIP_EXTRA_SEARCH))
        kept = keep.mean(axis=1).reshape(lys.size, lxs.size)
        for j, (name, _t) in enumerate(items):
            m = ncc[:, :, j]
            iy, ix = np.unravel_index(int(np.argmax(np.where(central, m, -2.0))), m.shape)
            val = float(m[iy, ix])
            if val < _EQUIP_TM_TRUST or kept[iy, ix] < min_kept:
                continue
            dd = (lys[:, None] - lys[iy]) ** 2 + (lxs[None, :] - lxs[ix]) ** 2
            ring = m[(dd >= r_in * r_in) & (dd <= r_out * r_out)]
            if ring.size == 0 or val - float(ring.max()) < min_sharp:
                continue
            if name not in best or val > best[name][0]:
                best[name] = (val, int(lxs[ix] + w // 2))
    return sorted(((name, val, icon_cx) for name, (val, icon_cx) in best.items()), key=lambda t: -t[1])


def read_equipped_below(
    screen: MatLike,
    tmpl_grays: dict[str, MatLike],
    below_rects: list[tuple[int, Rect]],
    icon_top_y: int,
    scales: tuple[float, ...] = _EQUIP_TM_SCALES,
    nms_radius: int = 18,
) -> dict[int, list[str]]:
    """每槽 below-avatar 区:第一读 + 两处补读 → 去重 → 布局约束 → ``{slot_idx: [装备名]}``(纯 CV,可离线测)。

    识别**角色已穿装备**(头像下方 icon),与 ``read_equips``(装备区 owned)互补。流程与标定依据见本函数上方
    「穿戴装备识别」块注释,这里只列契约:

    - **第一读**:每模板每尺度枚举相关图的局部极大值(``_local_peaks``,峰分 ≥ ``_EQUIP_TM_ACCEPT``),逐个峰过
      ① 矩形判空(``_EQUIP_BG_MAX``)② 尖锐度 ≥ ``_EQUIP_TM_PEAK_SHARP``;峰分不到 ``_EQUIP_TM_TRUST`` 的名字不可信。
    - **数字旁补读**:每个数量数字,若第一读没在它贴着的图标位置读到可信的名字,就把数字框排除后在该位置附近重比。
    - **火光下补读**:认出火光时,把图标顶边以上 ``_EQUIP_FLAME_CUT_ROWS`` 行排除,在 5 个候选位置附近各重比一遍。
    - **合并**:三读的峰按峰分降序做同位置去重(图标中心横向相距 ≤ ``nms_radius`` 留最高),再取最大完整布局。

    :param screen: 备战画面截图(RGB,1080p;sr_od ``cv2_utils.read_image`` 约定,非 BGR)。
    :param tmpl_grays: ``load_equip_tm_grays`` 结果(``{name: gray}``,98px 大图模板)。
    :param below_rects: ``[(slot_idx, Rect), ...]`` —— 每槽 below-avatar 搜索区(调用方从 screen_info
        槽 rect 算:avatar 底部下方,icon y 中心 ≈ avatar_y2 + 14,见 ``cw_identity_obs.avatar_to_below``)。
        同一次调用里的槽位应当同属一排(见 ``icon_top_y``)。
    :param icon_top_y: 这一排图标顶边在搜索区里的行号(``equip_icon_top_y``);火光下补读用它定排除到哪一行。
    :param scales: 98px 模板缩放档(覆盖 ~32-34px icon)。
    :param nms_radius: 同位置去重半径(icon 间距 ~35px → 18)。
    :return: ``{slot_idx: [装备名]}``;空槽 → 该 slot 不在 dict。名字不可信的位置、有装备线索(候选位置命中 /
        认出数量数字 / 认出火光)却凑不出完整布局的格子,对应位置是 ``EQUIP_UNKNOWN``(后者整格只报一个)。

    日志(经 ``cw_observe.cw_log``):``unknown``(读清的格子里有 ``EQUIP_UNKNOWN``,需关注,带搜索区截图)、
    ``anomaly``(图标数 >3,需关注)。

    纯读(只 TM screen + templates,不写 session/全局),可进 recognizer / op(并发安全)。
    """
    out: dict[int, list[str]] = {}
    resized = _resized_templates(tmpl_grays, scales)
    for slot_idx, rect in below_rects:
        crop_rgb = screen[rect.y1:rect.y2, rect.x1:rect.x2]  # sr_od screen 是 RGB(cv2_utils.read_image),非 BGR
        gray = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2GRAY)
        below_cx = gray.shape[1] // 2
        badges = _find_count_badges(crop_rgb)
        flame = _is_flame(crop_rgb)
        # (名字, 峰分, 图标中心 x, 名字是否可信);图标中心 x = 模板左上角 x + 半宽
        raw: list[tuple[str, float, int, bool]] = []
        rejected: list[tuple[str, float, float]] = []  # (名字, 峰分, 尖锐度) 过了矩形判空、被尖锐度门拒掉的峰,日志用
        board_ii = _board_mask_integral(crop_rgb)
        # 第一读:先判空再算尖锐度——空槽上的峰绝大多数整个落在底板上,判空只要四次取值。
        for (h, w), items in resized.items():
            if h >= gray.shape[0] or w >= gray.shape[1]:
                continue
            for name, resized_t in items:
                r = cv2.matchTemplate(gray, resized_t, cv2.TM_CCOEFF_NORMED)
                r = np.where(np.isfinite(r), r, -1.0)
                for lx, ly, val in _local_peaks(r):
                    board_n = board_ii[ly + h, lx + w] - board_ii[ly, lx + w] - board_ii[ly + h, lx] + board_ii[ly, lx]
                    if board_n / (h * w) > _EQUIP_BG_MAX:
                        continue
                    sharp = _peak_sharpness(r, (lx, ly))
                    if sharp >= _EQUIP_TM_PEAK_SHARP:
                        raw.append((name, val, lx + w // 2, val >= _EQUIP_TM_TRUST))
                    else:
                        rejected.append((name, val, sharp))
        # 火光下补读:5 个候选位置各找一遍;排除 = 图标顶边以上 _EQUIP_FLAME_CUT_ROWS 行 + 各数字框
        if flame:
            excl = _digit_exclusion(gray.shape, badges)
            excl[:icon_top_y + _EQUIP_FLAME_CUT_ROWS, :] = True
            for off in _EQUIP_CANDIDATES:
                raw.extend((name, val, icon_cx, True) for name, val, icon_cx in _extra_peaks(
                    gray, below_cx + off - _EQUIP_ICON_HALF, icon_top_y, excl, resized,
                    _EQUIP_FLAME_PEAK_SHARP, _EQUIP_EXTRA_MIN_KEPT))
        # 数字旁补读:第一读已经在这个数字贴着的图标位置读到可信名字的,不用补读
        for x1, y1, x2, _y2 in badges:
            icon_cx0 = x1 - _EQUIP_BADGE_ICON_DX + _EQUIP_ICON_HALF
            if any(abs(icon_cx - icon_cx0) <= _EQUIP_LAYOUT_TOL and trusted for _n, _v, icon_cx, trusted in raw):
                continue
            raw.extend((name, val, icon_cx, True) for name, val, icon_cx in _extra_peaks(
                gray, x1 - _EQUIP_BADGE_ICON_DX, y1 + _EQUIP_BADGE_ICON_DY, _digit_exclusion(gray.shape, [(x1, y1, x2, _y2)]),
                resized, _EQUIP_TM_PEAK_SHARP))
        # 同位置去重:按峰分降序,图标中心横向相距 ≤ nms_radius 的只留最高(同一图标被多块模板 / 多个尺度 / 多读命中)
        raw.sort(key=lambda t: -t[1])
        kept: list[tuple[str, float, int, bool]] = []
        for name, val, icon_cx, trusted in raw:
            if any(abs(icon_cx - k[2]) <= nms_radius for k in kept):
                continue
            kept.append((name, val, icon_cx, trusted))
        equipped = _select_equipped_layout(kept, below_cx, has_evidence=bool(badges) or flame)
        if equipped:
            out[slot_idx] = equipped
        # icon 数守卫:角色 below 最多3件,>3 = 误检/邻槽串入
        if len(kept) > 3:
            cw_log('read_equipped', target=f'slot={slot_idx}', attn=True,
                   anomaly=f'icon数{len(kept)}>3(误检/邻槽串入)', equips=str([n for n, _, _, _ in kept]),
                   shot=cw_shot(screen[rect.y1:rect.y2, rect.x1:rect.x2], f'over3_slot{slot_idx}'))
        # unknown 日志:记下没认出来的低分名字、被尖锐度门拒掉的最高几个峰,以及这一格是不是带数字 / 火光。
        if EQUIP_UNKNOWN in equipped:
            low = [(n, v) for n, v, _c, trusted in kept if not trusted]
            flat = sorted(((v, n, sh) for n, v, sh in rejected), reverse=True)[:3]
            cw_log('read_equipped', step='unknown', target=f'slot={slot_idx}', attn=True,
                   equips=str(equipped), flame=flame, badges=len(badges),
                   low_score=f'[{",".join(f"{n}({v:.2f})" for n, v in low[:3])}]',
                   sharp_rejected=f'[{",".join(f"{n}({v:.2f}/{sh:.2f})" for v, n, sh in flat)}]',
                   shot=cw_shot(screen[rect.y1:rect.y2, rect.x1:rect.x2], f'unknown_slot{slot_idx}'))
    return out


def _digit_exclusion(
    shape: tuple[int, ...],
    badges: list[tuple[int, int, int, int]],
) -> np.ndarray:
    """数字框的排除阵:框本身、外扩 ``_EQUIP_BADGE_OUTLINE`` 像素、以及框顶以下同几列的全部像素(数字可能比检出的白字更宽)。

    :param shape: 搜索区的 (高, 宽)。
    :param badges: ``_find_count_badges`` 的结果。
    :return: (高, 宽) 布尔阵,True = 不参与比对。
    """
    excl = np.zeros(shape[:2], bool)
    o = _EQUIP_BADGE_OUTLINE
    for x1, y1, x2, _y2 in badges:
        excl[max(0, y1 - o):, max(0, x1 - o):x2 + o + 1] = True
    return excl


def _select_equipped_layout(
    kept: list[tuple[str, float, int, bool]],
    below_cx: int,
    has_evidence: bool,
) -> list[str]:
    """布局约束选装备:图标中心归候选点(中线 ±43 / ±21 / 0),取最大完整的一套布局。

    :param kept: 同位置去重后的命中 ``(名字, 峰分, 图标中心 x, 名字是否可信)``,已按峰分降序。
    :param below_cx: 搜索区中线横坐标。
    :param has_evidence: 这一格有没有装备线索(认出数量数字 / 认出火光)。
    :return: 最大完整布局各位置的名字,名字不可信的位置是 ``EQUIP_UNKNOWN``;凑不出完整布局时,
        有候选位置命中或有装备线索 → ``[EQUIP_UNKNOWN]``,都没有 → ``[]``(读空)。
    """
    cand: dict[int, tuple[str, bool]] = {}
    for name, _val, icon_cx, trusted in kept:
        off = icon_cx - below_cx
        nearest = min(_EQUIP_CANDIDATES, key=lambda c: abs(c - off))
        if abs(nearest - off) <= _EQUIP_LAYOUT_TOL:
            cand.setdefault(nearest, (name, trusted))  # kept 已按峰分降序,首个 = 最高
    hit = set(cand)
    chosen = next((lay for lay in _EQUIP_LAYOUTS if set(lay) <= hit), None)
    if chosen is not None:
        return [cand[o][0] if cand[o][1] else EQUIP_UNKNOWN for o in chosen]
    # 每角色最多 3 件,1 / 2 / 3 件布局覆盖全部合法排法;凑不出完整布局时,读到的名字不可靠,一个都不报。
    return [EQUIP_UNKNOWN] if hit or has_evidence else []


def ensure_equip_tm_templates(ctx: SrContext) -> dict[str, MatLike] | None:
    """确保 ctx 缓存 cw_equip TM 模板(98px grays);返 ``grays`` 或 None(目录缺)。

    首次 load 缓存 ``ctx.cw_equip_tm_grays``;后续读缓存。recognizer 装备识别的 templates 加载点。

    **并发安全**:幂等(同值重 load 无害);只缓存只读资源(非 session/游戏状态),与运行中 operation 不竞争。
    """
    grays = getattr(ctx, 'cw_equip_tm_grays', None)
    if grays is None:
        base = get_project_root() / 'assets' / 'template'
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
        base = get_project_root() / 'assets' / 'template'
        equip_dir = base / 'currency_war' / 'equip_plaza'   # 混合库(同 ensure_equip_tm_templates)
        if not equip_dir.is_dir():
            equip_dir = base / 'currency_war' / 'equip_legacy'   # 回退:旧手工库
        if not equip_dir.is_dir():
            return None
        templates = load_equip_templates(equip_dir)
        ctx.cw_equip_sift_templates = templates
    return templates
