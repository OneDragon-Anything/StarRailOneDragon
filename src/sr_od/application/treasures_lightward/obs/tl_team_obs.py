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
class TlTeamView:
    """编队画面单帧结构化事实。

    Attributes:
        stage_name: 右上关卡名(如 物竞天择其一)。
        environment_text: 环境效果全文(关卡名下方描述区,本期记忆紊流文本)。
        star_targets: 挑战目标行(满星条件,通常 3 行)。
        left_tab: 左侧当前激活 tab('角色列表' | '预设编队');识别失败 None。
        slot1: 队伍 1 槽位识别(4 元素,下标 = 槽位序 0 基)。
        slot2: 队伍 2 槽位识别(同上)。
        character_grid: 角色列表 tab 的可见网格;非该 tab 为 None。
        preset_teams: 预设编队 tab 的队伍组;非该 tab 为 None。
    """

    stage_name: str | None
    environment_text: str | None
    star_targets: list[str]
    left_tab: str | None
    slot1: list[MemberGuess]
    slot2: list[MemberGuess]
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


def read_team_slots(ctx: SrContext, image: MatLike) -> tuple[list[MemberGuess], list[MemberGuess]]:
    """右侧两队伍槽(各 4 位,下标 0 基 = 画面槽位序)。area 缺失的槽位记无结论。"""
    templates = ensure_avatar_templates(ctx)
    slots: list[list[MemberGuess]] = []
    for row_name in ('槽位1头像', '槽位2头像'):
        row: list[MemberGuess] = []
        for i in range(1, 5):
            rect = _get_area_rect(ctx, f'{row_name}-{i}')
            if rect is None:
                row.append(MemberGuess(char=None, confident=False, candidates=[], empty=False))
                continue
            crop = image[rect.y1:rect.y2, rect.x1:rect.x2]
            row.append(_identify_crop(crop, templates))
        slots.append(row)
    return slots[0], slots[1]


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
    slot1, slot2 = read_team_slots(ctx, image)
    return TlTeamView(
        stage_name=read_stage_name(ctx, image),
        environment_text=read_environment(ctx, image),
        star_targets=read_star_targets(ctx, image),
        left_tab=tab,
        slot1=slot1,
        slot2=slot2,
        character_grid=character_grid,
        preset_teams=preset_teams,
    )
