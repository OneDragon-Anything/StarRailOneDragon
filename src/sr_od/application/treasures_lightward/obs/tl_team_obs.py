"""忘却之庭-编队画面结构化识别:关卡信息 + 右侧队伍槽 + 左侧列表(角色网格/预设队伍)。

消费面:
- per-screen recognizer(``recognizers/tl_team_recognizer.py``):analyze_screen 精准命中
  「忘却之庭-编队」后把结构化事实塞进 extras,供智能体/HTTP 直读;
- 自动化 op:配队检查 / 预设应用决策直接调本模块纯函数。

**头像识别**:项目脸库 ``assets/template/character_avatar``(<英文 id>/raw.webp,98 角色,
选择头像 art)× SIFT —— 经 ``TemplateLoader`` 特征缓存 + ``cv2_utils.feature_match_for_one``,
生产范式同 ``sr_od/operations/team/check_team_members_in_world.py``。右侧队伍槽头像(74px 圆裁)
全部命中;**编队卡内小头像是「编队卡图」变体**(解包 avatariconteam),与脸库 art 存在变体差异,
歧义率显著更高(2026-11-04 实机帧:槽位 8/8 对,卡内 16 格约 5 格歧义)——歧义以候选集诚实返回
(已验证真值均落候选前二),不硬猜;根治 = 解包 avatariconteam 补变体模板库。

**阈值标定**(2026-11-04 实机帧,fixture = sr-od-test/screens/忘却之庭-编队/):
- 真实头像 confidence ≥0.766,空槽占位图标伪命中 0.588 → 门槛 0.70;
- 歧义比(top1/top2)<1.25 → 拒绝单一结论,返回候选;
- 空槽:裁片 HSV 平均 V<60(空槽 34.6 vs 实头像 85-145);
- tab 激活:标签区平均 V≥140(激活 ~178 vs 非激活 ~95-105)。

纯读约束:全部函数不写 ctx/模块全局(模板缓存为只读资源,recognizer 可与运行中 op 并发)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import cv2
import numpy as np

from one_dragon.base.screen.template_info import TemplateInfo
from one_dragon.base.screen.template_loader import TemplateLoader
from one_dragon.utils import cv2_utils
from sr_od.config.character_const import CHARACTER_LIST, Character

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.geometry.rectangle import Rect
    from sr_od.context.sr_context import SrContext

SCREEN_NAME: str = '忘却之庭-编队'

# --------------------------------------------------------------------------
# 识别判定常量(标定出处见模块 docstring;改动需过 fixture 测试)
# --------------------------------------------------------------------------
_MIN_CONFIDENCE: float = 0.70       #: 单命中置信门槛(低于 = 无识别结论)
_AMBIGUITY_RATIO: float = 1.25      #: top1/top2 歧义比门槛(低于 = 返回候选不硬猜)
_EMPTY_SLOT_MEAN_V: float = 60.0    #: 空槽判定:裁片平均 V 低于此 = 空槽
_ACTIVE_TAB_MEAN_V: float = 140.0   #: tab 激活判定:标签区平均 V 高于此 = 激活

# --------------------------------------------------------------------------
# 弱点属性(建议属性)识别:OCR 锚「建议属性」→ 标签下方图块带 → 色块检测 →
# 元素模板匹配(element_weakness 底板合成模板)主判 + 色相域交叉仲裁。
# 锚定位使识别对布局平移不敏感(环境描述行数变化会推移下方内容,固定 rect 会错位)。
# 色相域标定:2026-11-04 实机帧(物竞天择其一/其十)6 blob 全对 —— 雷 H≈122 /
# 量子 H≈144 / 冰 H≈95 / 虚数 H≈26 / 火 H≈1 / 物理=白色纹样(S<30,V>150);
# 风未见样本,按色相域预留(模板已入库,出现样本后回验)。
# --------------------------------------------------------------------------
_WEAKNESS_ANCHOR_TEXT: str = '建议属性'
_WEAKNESS_ZONE_W: int = 200          #: 图块带搜索区宽(锚点左对齐)
_WEAKNESS_ZONE_H: int = 60           #: 图块带搜索区高(标签底缘起)
_WEAKNESS_HUE_BUCKETS: tuple[tuple[str, int, int], ...] = (
    ('火', 0, 12), ('火', 168, 179), ('虚数', 15, 35), ('风', 40, 80),
    ('冰', 84, 110), ('雷', 112, 132), ('量子', 136, 158),
)
_ELEMENT_NAMES: tuple[str, ...] = ('火', '冰', '雷', '风', '量子', '虚数', '物理')
_ELEMENT_TEMPLATE_DIR: str = 'element_weakness'
_WEAKNESS_BLOB_MIN: int = 16         #: 图标色块外接框下限(px,膨胀后)
_WEAKNESS_BLOB_MAX: int = 64         #: 图标色块外接框上限
_WEAKNESS_TM_MIN: float = 0.45       #: TM 置信下限(低于 = 走色相域回退)
_WEAKNESS_MAX_ROWS: int = 4          #: 波次锚行上限(防 OCR 误检炸量;当前模式最多 2-3)

# --------------------------------------------------------------------------
# 左侧角色网格几何(相对「区域-角色网格」rect 原点;2026-11-04 实机帧标定)
# 4 列 × 可见 4 行;单元格头像子区 88x94,列距 117、行距 165。
# 网格可滚动,超出可见行的成员不在本帧结果内(跨帧合并是消费方职责)。
# --------------------------------------------------------------------------
_GRID_COLS: int = 4
_GRID_ROWS: int = 4
_GRID_CELL_X_OFF: int = 15          #: 首列头像子区 x 偏移(全图 53 - 网格区 x1 38)
_GRID_CELL_Y_OFF: int = 16          #: 首行头像子区 y 偏移(全图 186 - 网格区 y1 170)
_GRID_CELL_DX: int = 117            #: 列距(首格中心 97 → 次列 215)
_GRID_CELL_DY: int = 165            #: 行距(首行 240 → 次行 405)
_GRID_CELL_W: int = 88
_GRID_CELL_H: int = 94

# --------------------------------------------------------------------------
# 预设卡内小头像几何(相对「预设卡-N」rect 原点;2026-11-04 实机帧标定)
# 卡内 4 个头像 art 子区(避开卡框与底部「队伍N/等级」标签带),x 起点 4 个。
# --------------------------------------------------------------------------
_PRESET_MEMBER_COUNT: int = 4
_PRESET_MINI_X_OFFS: tuple[int, ...] = (5, 137, 268, 400)   #: 各头像子区 x 偏移
_PRESET_MINI_Y_OFF: int = 55                                #: 头像子区 y 偏移
_PRESET_MINI_W: int = 116
_PRESET_MINI_H: int = 70


@dataclass
class MemberGuess:
    """单头像识别结果(诚实歧义:无把握不给单一结论)。

    Attributes:
        char: 置信通过时 = 角色中文名;空槽/歧义/低置信 = None。
        confident: True = char 可信(过置信门槛且歧义比达标)。
        candidates: (角色名, confidence) 降序,歧义时供消费方裁决;空槽为 []。
        empty: True = 空槽/空格(黑色占位图标)。
    """

    char: str | None
    confident: bool
    candidates: list[tuple[str, float]]
    empty: bool = False


@dataclass
class PresetTeam:
    """预设编队卡(成员按卡内位置绑组返回)。

    Attributes:
        team_idx: 预设卡序号,1 基,画面从上到下(恒稳,卡与账号预设一一对应)。
        members: 卡内 4 个头像识别结果,按下标位序(左→右)。
    """

    team_idx: int
    members: list[MemberGuess]


@dataclass
class GridCell:
    """角色列表网格单格。

    Attributes:
        row: 行,0 基,画面从上到下(本帧可见行;滚动后坐标复用)。
        col: 列,0 基,画面从左到右。
        guess: 该格头像识别结果。
    """

    row: int
    col: int
    guess: MemberGuess


@dataclass
class WaveInfo:
    """单波次(旧代码称节点)识别结果:该波敌人弱点 + 该波当前编队成员。

    Attributes:
        wave_idx: 波次序号,1 基,画面从上到下(每波一行队伍槽;数量按「建议属性」
            锚行实读,混忆常规 2 波,其他模式/回忆章节可能不同)。
        weaknesses: 该波敌人弱点属性名(「建议属性」图标带,左右序)。
        members: 该波当前编队成员(4 元素按槽位序 0 基;该行槽位 area 未建档时 = [],
            不返回不完整列表,不编造)。
    """

    wave_idx: int
    weaknesses: list[str]
    members: list[MemberGuess]


@dataclass
class TlTeamView:
    """编队画面单帧结构化事实。

    Attributes:
        stage_name: 右上关卡名(如 物竞天择其一)。
        environment_text: 环境效果全文(关卡名下方描述区,本期记忆紊流文本)。
        star_targets: 挑战目标行(满星条件,通常 3 行)。
        left_tab: 左侧当前激活 tab('角色列表' | '预设编队');识别失败 None。
        waves: 波次列表(每波绑定 弱点 + 当前编队;锚行实读,锚未读到 = 空列表降级)。
        character_grid: 角色列表 tab 的可见网格;非该 tab 为 None。
        preset_teams: 预设编队 tab 的队伍组;非该 tab 为 None。
    """

    stage_name: str | None
    environment_text: str | None
    star_targets: list[str]
    left_tab: str | None
    waves: list[WaveInfo]
    character_grid: list[GridCell] | None
    preset_teams: list[PresetTeam] | None


def _get_area_rect(ctx: SrContext, area_name: str) -> Rect | None:
    """取本画面某 area 的 pc_rect;画面/area 缺失返 None(调用方按缺读处理)。"""
    si = ctx.screen_loader.get_screen(SCREEN_NAME)
    if si is None:
        return None
    area = next((a for a in si.area_list if a.area_name == area_name), None)
    return area.pc_rect if (area is not None and area.pc_rect is not None) else None


def _mean_v(crop: MatLike) -> float:
    """裁片 HSV 平均 V(亮度)。"""
    v = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)[:, :, 2]
    return float(v.mean())


def _ocr_lines(ctx: SrContext, image: MatLike, rect: Rect) -> list[str]:
    """rect 区域 OCR,按 行→列 排序返回各行文本(空区域返 [])。"""
    results = ctx.ocr_service.get_ocr_result_list(image=image, rect=rect)
    results.sort(key=lambda r: (round(r.y / 20), r.x))
    return [r.data for r in results if r.data]


def ensure_avatar_templates(ctx: SrContext) -> list[tuple[Character, TemplateInfo]]:
    """确保脸库模板(含 SIFT 特征)就绪;列表缓存在 ctx(只读资源,幂等,并发安全)。

    脸库缺失(目录被删等)返回空列表 —— 识别层按无模板降级(全 MemberGuess 无结论)。
    """
    templates: list[tuple[Character, TemplateInfo]] = getattr(ctx, 'tl_avatar_templates', None) or []
    if templates:
        return templates
    loader = TemplateLoader()
    for ch in CHARACTER_LIST:
        t = loader.get_template('character_avatar', ch.id)
        if t is not None:
            templates.append((ch, t))
    ctx.tl_avatar_templates = templates
    return templates


def _identify_crop(crop: MatLike, templates: list[tuple[Character, TemplateInfo]]) -> MemberGuess:
    """单头像裁片识别(诚实歧义,阈值标定见模块 docstring)。"""
    if crop is None or crop.size == 0:
        return MemberGuess(char=None, confident=False, candidates=[], empty=True)
    if _mean_v(crop) < _EMPTY_SLOT_MEAN_V:
        return MemberGuess(char=None, confident=False, candidates=[], empty=True)
    if not templates:
        return MemberGuess(char=None, confident=False, candidates=[], empty=False)
    skp, sdesc = cv2_utils.feature_detect_and_compute(crop)
    hits: list[tuple[str, float]] = []
    for ch, t in templates:
        tkp, tdesc = t.features
        mr = cv2_utils.feature_match_for_one(
            skp, sdesc, tkp, tdesc, t.raw.shape[1], t.raw.shape[0])
        if mr is not None and mr.confidence >= _MIN_CONFIDENCE:
            hits.append((ch.cn, float(mr.confidence)))
    hits.sort(key=lambda x: -x[1])
    if not hits:
        return MemberGuess(char=None, confident=False, candidates=[], empty=False)
    ratio = hits[0][1] / hits[1][1] if len(hits) >= 2 else float('inf')
    confident = ratio >= _AMBIGUITY_RATIO
    return MemberGuess(
        char=hits[0][0] if confident else None,
        confident=confident,
        candidates=hits[:3],
        empty=False,
    )


def read_stage_name(ctx: SrContext, image: MatLike) -> str | None:
    """右上关卡名(如 物竞天择其一);读不到 None。"""
    rect = _get_area_rect(ctx, '关卡名文本')
    if rect is None:
        return None
    lines = _ocr_lines(ctx, image, rect)
    return lines[0] if lines else None


def read_environment(ctx: SrContext, image: MatLike) -> str | None:
    """环境效果全文(关卡名下方大描述区;一行文本折多行 OCR 后拼接)。

    描述区下邻「挑战目标」标题,OCR det 偶发把标题并进末行框(实测混入后缀)——
    该标题为固定字面量,拼接前按行剔除。
    """
    rect = _get_area_rect(ctx, '文本-环境效果')
    if rect is None:
        return None
    lines = [line for line in _ocr_lines(ctx, image, rect) if line != '挑战目标']
    text = ''.join(lines)
    if text.endswith('挑战目标'):
        text = text[:-len('挑战目标')]
    return text if text else None


def read_star_targets(ctx: SrContext, image: MatLike) -> list[str]:
    """挑战目标各行(满星条件,通常 3 行)。"""
    rect = _get_area_rect(ctx, '文本-挑战目标')
    if rect is None:
        return []
    return _ocr_lines(ctx, image, rect)


def read_left_tab(ctx: SrContext, image: MatLike) -> str | None:
    """左侧当前激活 tab 名(亮度判激活,标定见 docstring);两个标签都读不到时 None。"""
    result: tuple[float, str] | None = None
    for tab_name in ('角色列表', '预设编队'):
        rect = _get_area_rect(ctx, f'tab-{tab_name}')
        if rect is None:
            continue
        crop = image[rect.y1:rect.y2, rect.x1:rect.x2]
        mv = _mean_v(crop)
        if result is None or mv > result[0]:
            result = (mv, tab_name)
    if result is None or result[0] < _ACTIVE_TAB_MEAN_V:
        return None
    return result[1]


def ensure_element_templates(ctx: SrContext) -> dict[str, TemplateInfo]:
    """元素弱点模板(元素名→TemplateInfo;assets/template/element_weakness/<元素>/raw.png)。

    模板源 = 客户端解包 ``IconDamageType*`` 官方图标(64px RGBA),入库前预合成到
    实采底板色(RGB 31,30,50)上 —— 与游戏内「暗色圆板 + 彩色纹样」渲染一致。
    缓存 ctx(只读资源,幂等,并发安全);缺失降级为空 dict(走色相域回退)。
    """
    cached = getattr(ctx, 'tl_element_templates', None)
    if cached:
        return cached
    loader = TemplateLoader()
    out: dict[str, TemplateInfo] = {}
    for cname in _ELEMENT_NAMES:
        t = loader.get_template(_ELEMENT_TEMPLATE_DIR, cname)
        if t is not None:
            out[cname] = t
    ctx.tl_element_templates = out
    return out


def _weakness_hue(crop: MatLike) -> int:
    """色块裁片彩色纹样像素的中位 H(S>60,V>80;无彩像素返 -1)。"""
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    s, v = hsv[:, :, 1].astype(int), hsv[:, :, 2].astype(int)
    colored = (s > 60) & (v > 80)
    if int(colored.sum()) < 15:
        return -1
    return int(np.median(hsv[:, :, 0][colored]))


def _weakness_hue_element(hue: int) -> str | None:
    """色相中位 → 元素名(域表见 _WEAKNESS_HUE_BUCKETS;域外 None)。"""
    for name, lo, hi in _WEAKNESS_HUE_BUCKETS:
        if lo <= hue <= hi:
            return name
    return None


def _classify_weakness_blob(crop: MatLike, templates: dict[str, TemplateInfo]) -> str | None:
    """弱点图块裁片 → 元素名。

    TM 主判:元素模板(底板合成图)缩放到色块尺寸后 CCOEFF_NORMED(模板已含底板,
    与游戏渲染一致;CCOEFF 去均值抑制底色差)。两道交叉:
    - 白色纹样直判:blob 内白像素占优(相邻图标边缘可能渗入少量彩像素,按占比裁断)
      → 物理(白色双剑=物理,标定 2026-11-04 实机帧);
    - 紫对仲裁:TM 最佳为 雷/量子 且色相明确落在另一域 → 按色相纠正(同色不同相,
      TM 色彩主导会互串,实机帧实测雷/量子互错);
    - 低分回退:TM < 阈值 → 色相域判定(全 blob 标定全对)。
    """
    bh, bw = crop.shape[:2]
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    s, v = hsv[:, :, 1].astype(int), hsv[:, :, 2].astype(int)
    colored_px = int(((s > 60) & (v > 80)).sum())
    white_px = int(((s < 30) & (v > 150)).sum())
    if white_px >= 30 and white_px >= colored_px * 2:
        return '物理'
    hue = int(np.median(hsv[:, :, 0][(s > 60) & (v > 80)])) if colored_px >= 15 else -1
    best_name: str | None = None
    best_score = -1.0
    for cname, t in templates.items():
        t_s = cv2.resize(t.raw, (bw, bh), interpolation=cv2.INTER_AREA)
        res = cv2.matchTemplate(crop, t_s, cv2.TM_CCOEFF_NORMED)
        res = np.nan_to_num(res, nan=0.0, posinf=0.0, neginf=0.0)
        score = float(res.max())
        if score > best_score:
            best_name, best_score = cname, score
    if best_name is None:
        return None
    if best_name in ('雷', '量子') and hue >= 0:
        hue_elem = _weakness_hue_element(hue)
        if hue_elem in ('雷', '量子') and hue_elem != best_name:
            return hue_elem
    if best_score < _WEAKNESS_TM_MIN:
        return _weakness_hue_element(hue)
    return best_name


def _detect_weakness_blobs(zone: MatLike) -> list[tuple[int, int, int, int]]:
    """图块带 → 图标外接框列表(按 x 序;彩色纹样 + 白色纹样双路,膨胀融臂去重)。"""
    hsv = cv2.cvtColor(zone, cv2.COLOR_RGB2HSV)
    s, v = hsv[:, :, 1].astype(int), hsv[:, :, 2].astype(int)
    kernel = np.ones((3, 3), np.uint8)
    boxes: list[tuple[int, int, int, int]] = []
    seen: list[tuple[int, int]] = []
    for mask_bool in ((s > 60) & (v > 80), (s < 30) & (v > 150)):
        mask = mask_bool.astype(np.uint8) * 255
        mask = cv2.dilate(mask, kernel, iterations=1)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if not (_WEAKNESS_BLOB_MIN <= w <= _WEAKNESS_BLOB_MAX
                    and _WEAKNESS_BLOB_MIN <= h <= _WEAKNESS_BLOB_MAX):
                continue
            if any(abs(x - sx) < 12 and abs(y - sy) < 12 for sx, sy in seen):
                continue
            seen.append((x, y))
            boxes.append((x, y, w, h))
    boxes.sort(key=lambda b: b[0])
    return boxes


def read_team_waves(ctx: SrContext, image: MatLike) -> list[WaveInfo]:
    """按「建议属性」锚行装配波次列表(每锚 = 一波,数量实读)。

    每波绑定:该波弱点属性(锚下方图块带)+ 该波当前编队成员(槽位 area 按行号取,
    area 未建档的行 members = [])。锚未读到 = 空列表(降级不编造)。
    """
    templates = ensure_avatar_templates(ctx)
    results = ctx.ocr_service.get_ocr_result_list(image=image)
    anchors = sorted(
        (r for r in results if _WEAKNESS_ANCHOR_TEXT in (r.data or '')),
        key=lambda r: r.y,
    )
    waves: list[WaveInfo] = []
    for idx, a in enumerate(anchors[:_WEAKNESS_MAX_ROWS], start=1):
        x1 = max(0, a.x - 15)
        y1 = a.y + a.h + 2
        zone = image[y1:y1 + _WEAKNESS_ZONE_H, x1:x1 + _WEAKNESS_ZONE_W]
        weaknesses: list[str] = []
        for (bx, by, bw, bh) in _detect_weakness_blobs(zone):
            pad = 4
            crop = zone[max(0, by - pad):by + bh + pad, max(0, bx - pad):bx + bw + pad]
            name = _classify_weakness_blob(crop, ensure_element_templates(ctx))
            if name:
                weaknesses.append(name)
        members: list[MemberGuess] = []
        area_missing = False
        for i in range(1, 5):
            rect = _get_area_rect(ctx, f'槽位{idx}头像-{i}')
            if rect is None:
                area_missing = True
                continue
            crop = image[rect.y1:rect.y2, rect.x1:rect.x2]
            members.append(_identify_crop(crop, templates))
        if area_missing:
            members = []   # 该行槽位未建档 → 不返回不完整列表
        waves.append(WaveInfo(wave_idx=idx, weaknesses=weaknesses, members=members))
    return waves


def read_character_grid(ctx: SrContext, image: MatLike) -> list[GridCell]:
    """角色列表 tab 的可见网格(4 列 × 可见 4 行;几何标定见模块 docstring)。"""
    area_rect = _get_area_rect(ctx, '区域-角色网格')
    templates = ensure_avatar_templates(ctx)
    cells: list[GridCell] = []
    if area_rect is None:
        return cells
    for row in range(_GRID_ROWS):
        for col in range(_GRID_COLS):
            x1 = area_rect.x1 + _GRID_CELL_X_OFF + col * _GRID_CELL_DX
            y1 = area_rect.y1 + _GRID_CELL_Y_OFF + row * _GRID_CELL_DY
            crop = image[y1:y1 + _GRID_CELL_H, x1:x1 + _GRID_CELL_W]
            cells.append(GridCell(row=row, col=col, guess=_identify_crop(crop, templates)))
    return cells


def read_preset_teams(ctx: SrContext, image: MatLike) -> list[PresetTeam]:
    """预设编队 tab 的队伍组(每卡 4 成员绑组;卡 rect 来自 screen_info 预设卡-N)。"""
    templates = ensure_avatar_templates(ctx)
    teams: list[PresetTeam] = []
    for team_idx in range(1, 5):
        rect = _get_area_rect(ctx, f'预设卡-{team_idx}')
        if rect is None:
            continue
        members: list[MemberGuess] = []
        for xi in _PRESET_MINI_X_OFFS:
            x1 = rect.x1 + xi
            y1 = rect.y1 + _PRESET_MINI_Y_OFF
            crop = image[y1:y1 + _PRESET_MINI_H, x1:x1 + _PRESET_MINI_W]
            members.append(_identify_crop(crop, templates))
        teams.append(PresetTeam(team_idx=team_idx, members=members))
    return teams


def collect_tl_team_info(ctx: SrContext, image: MatLike) -> TlTeamView:
    """整帧装配(按激活 tab 决定左侧列表走哪套识别;左右两块互不影响)。"""
    tab = read_left_tab(ctx, image)
    character_grid: list[GridCell] | None = None
    preset_teams: list[PresetTeam] | None = None
    if tab == '角色列表':
        character_grid = read_character_grid(ctx, image)
    elif tab == '预设编队':
        preset_teams = read_preset_teams(ctx, image)
    return TlTeamView(
        stage_name=read_stage_name(ctx, image),
        environment_text=read_environment(ctx, image),
        star_targets=read_star_targets(ctx, image),
        left_tab=tab,
        waves=read_team_waves(ctx, image),
        character_grid=character_grid,
        preset_teams=preset_teams,
    )
