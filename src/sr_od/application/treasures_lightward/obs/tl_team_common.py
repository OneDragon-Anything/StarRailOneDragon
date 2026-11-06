"""逐光捡金编队识别公共底座:共享阈值 / 区域工具 / 单格头像识别 / 全部识别数据类。

各识别域按文件拆分(见同目录 tl_stage_info_obs / tl_weakness_obs /
tl_character_list_obs / tl_preset_obs),聚合入口与消费方 import 路径见 tl_team_obs。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import cv2

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils import cv2_utils
from sr_od.config.avatar_templates import AvatarTemplate
from sr_od.config.character_const import Character

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from sr_od.context.sr_context import SrContext

SCREEN_NAME: str = '忘却之庭-编队'

# --------------------------------------------------------------------------
# 识别判定常量(标定出处见 tl_team_obs 模块 docstring;改动需过 fixture 测试)
# --------------------------------------------------------------------------
MIN_CONFIDENCE: float = 0.70       #: 单命中置信门槛(低于 = 无识别结论)
AMBIGUITY_RATIO: float = 1.25      #: top1/top2 歧义比门槛(低于 = 返回候选不硬猜)
EMPTY_SLOT_MEAN_V: float = 60.0    #: 空槽判定:裁片平均 V 低于此 = 空槽
ACTIVE_TAB_MEAN_V: float = 140.0   #: tab 激活判定:标签区平均 V 高于此 = 激活


def get_area_rect(ctx: SrContext, area_name: str,
                  screen_name: str = SCREEN_NAME) -> Rect | None:
    """取指定画面某 area 的 pc_rect;画面/area 缺失返 None(调用方按缺读处理)。

    screen_name 可指定其他逐光捡金编队屏(如虚构叙事-编队)——行结构同构、
    槽位 area 按各屏独立建档(跨屏复用他屏槽位 rect 会裁错位置,脸库识别全空)。"""
    si = ctx.screen_loader.get_screen(screen_name)
    if si is None:
        return None
    area = next((a for a in si.area_list if a.area_name == area_name), None)
    return area.pc_rect if (area is not None and area.pc_rect is not None) else None


def mean_v(crop: MatLike) -> float:
    """裁片 HSV 平均 V(亮度)。"""
    v = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)[:, :, 2]
    return float(v.mean())


def ocr_lines(ctx: SrContext, image: MatLike, rect: Rect) -> list[str]:
    """rect 区域 OCR,按 行→列 排序返回各行文本(空区域返 [])。"""
    results = ctx.ocr_service.get_ocr_result_list(image=image, rect=rect)
    results.sort(key=lambda r: (round(r.y / 20), r.x))
    return [r.data for r in results if r.data]


def get_area_center_point(ctx: SrContext, screen_name: str, area_name: str) -> Point:
    """按建档 rect 取 area 中心点击点(坐标单一真相源在 screen_info)。

    与 :func:`get_area_rect` 不同,area 缺失直接 raise——点击点缺失时
    静默返 None 会让调用方把「没点」当「点了」。"""
    si = ctx.screen_loader.get_screen(screen_name)
    area = next((a for a in si.area_list if a.area_name == area_name), None) if si else None
    if area is None or area.pc_rect is None:
        raise ValueError(f'area 缺失: {screen_name}/{area_name}')
    rect = area.pc_rect
    return Point((rect.x1 + rect.x2) // 2, (rect.y1 + rect.y2) // 2)


def identify_crop(crop: MatLike, templates: list[AvatarTemplate]) -> MemberGuess:
    """单头像裁片识别(诚实歧义,阈值标定见 tl_team_obs 模块 docstring)。"""
    if crop is None or crop.size == 0:
        return MemberGuess(char=None, confident=False, candidates=[], empty=True)
    if mean_v(crop) < EMPTY_SLOT_MEAN_V:
        return MemberGuess(char=None, confident=False, candidates=[], empty=True)
    if not templates:
        return MemberGuess(char=None, confident=False, candidates=[], empty=False)
    skp, sdesc = cv2_utils.feature_detect_and_compute(crop)
    hits: list[tuple[str, float]] = []
    for entry in templates:
        tkp, tdesc = entry.info.features
        mr = cv2_utils.feature_match_for_one(
            skp, sdesc, tkp, tdesc, entry.info.raw.shape[1], entry.info.raw.shape[0])
        if mr is not None and mr.confidence >= MIN_CONFIDENCE:
            hits.append((entry.character.cn, float(mr.confidence)))
    hits.sort(key=lambda x: -x[1])
    if not hits:
        return MemberGuess(char=None, confident=False, candidates=[], empty=False)
    ratio = hits[0][1] / hits[1][1] if len(hits) >= 2 else float('inf')
    confident = ratio >= AMBIGUITY_RATIO
    return MemberGuess(
        char=hits[0][0] if confident else None,
        confident=confident,
        candidates=hits[:3],
        empty=False,
    )


def read_left_tab(ctx: SrContext, image: MatLike) -> str | None:
    """左侧当前激活 tab 名(亮度判激活,标定见 tl_team_obs 模块 docstring);两个标签都读不到时 None。"""
    result: tuple[float, str] | None = None
    for tab_name in ('角色列表', '预设编队'):
        rect = get_area_rect(ctx, f'tab-{tab_name}')
        if rect is None:
            continue
        crop = image[rect.y1:rect.y2, rect.x1:rect.x2]
        mv = mean_v(crop)
        if result is None or mv > result[0]:
            result = (mv, tab_name)
    if result is None or result[0] < ACTIVE_TAB_MEAN_V:
        return None
    return result[1]


@dataclass
class MemberGuess:
    """单头像识别结果(诚实歧义:无把握不给单一结论)。

    Attributes:
        char: 置信通过时 = 角色中文名;空槽/歧义/低置信 = None。
        confident: True = char 可信(过置信门槛且歧义比达标)。
        candidates: (角色名, 分值) 降序,歧义时供消费方裁决;空槽为 []。
            分值量纲随识别路径不同(整页路径 = 内点率,裁片路径 = SIFT 置信),
            仅供排序与展示。
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
class AnchorCell:
    """角色列表锚点识别单元(等级文本锚驱动,滚动停驻位置无关)。

    Attributes:
        center: 头像点击中心(全图坐标)。
        guess: 该卡头像识别结果。
        rect: 头像区矩形(全图坐标,即 center 所在裁片区)。供按格命中判定,
            如「队伍N」标记框中心是否落在某卡头像区内 = 该卡已入队。
    """

    center: Point
    guess: MemberGuess
    rect: Rect | None = None


@dataclass
class PageHit:
    """整页匹配单模板命中(见 tl_character_list_obs 的 ``_match_page_characters``)。

    Attributes:
        character: 命中角色(皮肤条目指向本体角色)。
        template_id: 命中模板目录名(可区分默认/皮肤变体)。
        inliers: RANSAC 内点数(置信量纲,越大越可信)。
        inlier_ratio: 内点数 / 比值测试通过数(0-1)。
        rect: 模板四角经单应矩阵投影到页面的外接框(全图坐标)。
    """

    character: Character
    template_id: str
    inliers: int
    inlier_ratio: float
    rect: Rect


@dataclass
class NodeInfo:
    """单节点识别结果:该节点敌人弱点 + 该节点当前编队成员。

    节点 = 关卡的一段战斗(编队屏一行队伍槽 = 一支 4 人队;常规关卡 2 节点、
    星启关卡 3 节点,术语定案见 skill sr-od-treasures-lightward references/gameplay.md)。

    Attributes:
        node_idx: 节点序号,1 基,画面从上到下(每节点一行队伍槽;数量按「建议属性」
            锚行实读,混忆常规 2 节点,星启 3 节点,其他模式可能不同)。
        weaknesses: 该节点敌人弱点属性名(「建议属性」图标带,左右序)。
        members: 该节点当前编队成员(4 元素按槽位序 0 基;该行槽位 area 未建档时 = [],
            不返回不完整列表,不编造)。
    """

    node_idx: int
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
        nodes: 节点列表(每节点绑定 弱点 + 当前编队;锚行实读,锚未读到 = 空列表降级)。
        character_grid: 角色列表 tab 的可见网格;非该 tab 为 None。
        preset_teams: 预设编队 tab 的队伍组;非该 tab 为 None。
    """

    stage_name: str | None
    environment_text: str | None
    star_targets: list[str]
    left_tab: str | None
    nodes: list[NodeInfo]
    character_grid: list[GridCell] | None
    preset_teams: list[PresetTeam] | None
