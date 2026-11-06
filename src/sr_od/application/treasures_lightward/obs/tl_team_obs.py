"""忘却之庭-编队画面结构化识别:关卡信息 + 右侧队伍槽 + 左侧列表(角色网格/预设队伍)。

⚠️ 适用范围:识别标定(槽位坐标/建议属性/预设卡/阈值)全部基于**混沌回忆**的编队屏
实机帧;逐光捡金其余玩法(虚构叙事/末日幻影)的编队屏布局若不同,需另行建档识别,
不可直接复用本模块的常量与 area(人类老莫明确:其他类型的填充可能不一样)。

消费面:
- per-screen recognizer(``recognizers/tl_team_recognizer.py``):analyze_screen 精准命中
  「忘却之庭-编队」后把结构化事实塞进 extras,供智能体/HTTP 直读;
- 自动化 op:配队检查 / 预设应用决策直接调本模块纯函数。

**头像识别**:项目脸库 ``assets/template/character_avatar``(<英文 id>/raw.webp,98 角色,
选择头像 art)× SIFT —— 经 ``TemplateLoader`` 特征缓存 + ``cv2_utils.feature_match_for_one``,
生产范式同 ``sr_od/operations/team/check_team_members_in_world.py``。右侧队伍槽头像(74px 圆裁)
全部命中;**编队卡内小头像是「编队卡图」变体**(解包 avatariconteam),与脸库 art 存在变体差异,
歧义率显著更高(实机帧标定:槽位 8/8 对,卡内 16 格约 5 格歧义)——歧义以候选集诚实返回
(已验证真值均落候选前二),不硬猜;根治 = 解包 avatariconteam 补变体模板库。

**阈值标定**(实机帧,fixture = sr-od-test/screens/忘却之庭-编队/):
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

from one_dragon.base.config.yaml_operator import YamlOperator
from one_dragon.base.geometry.point import Point
from one_dragon.base.screen.template_info import TemplateInfo
from one_dragon.base.screen.template_loader import TemplateLoader
from one_dragon.utils import cv2_utils, os_utils
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
# 弱点属性(建议属性)识别:OCR 锚「建议属性」→ 图块带 → 色块检测 →
# 元素模板匹配(element_weakness 底板合成模板)主判 + 色相域交叉仲裁。
# 锚定位使识别对布局平移不敏感(环境描述行数变化会推移内容,固定 rect 会错位)。
# 图块带相对锚行有两种布局(weakness_layout):
# - 'below':图块带在锚行正下方(忘却之庭/虚构叙事编队屏);
# - 'inline':图块带与锚文字同行、紧贴其右(末日幻影编队屏 boss 卡)。
# 色相域标定:实机帧(物竞天择其一/其十)6 blob 全对 —— 雷 H≈122 /
# 量子 H≈144 / 冰 H≈95 / 虚数 H≈26 / 火 H≈1 / 物理=白色纹样(S<30,V>150);
# 风未见样本,按色相域预留(模板已入库,出现样本后回验)。
# --------------------------------------------------------------------------
_WEAKNESS_ANCHOR_TEXT: str = '建议属性'
_WEAKNESS_LAYOUT_BELOW: str = 'below'    #: 图块带在锚行正下方
_WEAKNESS_LAYOUT_INLINE: str = 'inline'  #: 图块带与锚文字同行、紧贴其右
_WEAKNESS_INLINE_X_OFF: int = 90     #: inline 图标带起点相对锚行左缘偏移
                                     # (「建议属性」4 字宽+间隙;OCR det 框常把首图标
                                     #  粘进文本框,框右缘不可用,实机帧标定)
_WEAKNESS_INLINE_ZONE_W: int = 100   #: inline 图标带搜索区宽(4 图标带+余量,
                                     #  不及右侧相邻元素防误检,实机帧标定)
_WEAKNESS_INLINE_BLOB_MAX: int = 40  #: inline 图标外接框上限(两图标粘连拦截)
_WEAKNESS_ZONE_W: int = 200          #: below 图块带搜索区宽(锚点左对齐)
_WEAKNESS_ZONE_H: int = 60           #: 图块带搜索区高(below:标签底缘起;inline:锚行框扩)
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
_BOSS_WEAKNESS_FILE: str = 'tl_boss_weaknesses.yml'  #: boss 弱点表(assets/game_data 下)

# --------------------------------------------------------------------------
# 左侧角色网格几何(相对「区域-角色网格」rect 原点;实机帧标定)
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
# 等级文本锚驱动识别(角色列表,滚动停驻位置无关):
# 每张卡下方有「等级NN」文本条,OCR 找锚 → 锚上方裁头像区 → 脸库匹配。
# 固定网格几何(read_character_grid)在滚动停半格时行列偏移裁错位——锚跟随
# 卡片实际位置,任意停驻都可识别。裁片几何按实机帧标定:
# 锚(x)=卡左缘+5,锚(y)=等级条文本顶;头像区 = 锚上方 95px 高、卡宽 90px。
# --------------------------------------------------------------------------
_LEVEL_ANCHOR_TEXT: str = '等级'
_LEVEL_ANCHOR_AVATAR_W: int = 90
_LEVEL_ANCHOR_AVATAR_H: int = 95
_LEVEL_ANCHOR_DX: int = -5            #: 头像区 x1 相对锚 x 偏移
_LEVEL_ANCHOR_DY: int = -97           #: 头像区 y1 相对锚 y 偏移

# --------------------------------------------------------------------------
# 预设卡内小头像几何(相对「预设卡-N」rect 原点;实机帧标定)
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
class AnchorCell:
    """角色列表锚点识别单元(等级文本锚驱动,滚动停驻位置无关)。

    Attributes:
        center: 头像点击中心(全图坐标)。
        guess: 该卡头像识别结果。
    """

    center: Point
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


def _get_area_rect(ctx: SrContext, area_name: str,
                   screen_name: str = SCREEN_NAME) -> Rect | None:
    """取指定画面某 area 的 pc_rect;画面/area 缺失返 None(调用方按缺读处理)。

    screen_name 可指定其他逐光捡金编队屏(如虚构叙事-编队)——行结构同构、
    槽位 area 按各屏独立建档(跨屏复用他屏槽位 rect 会裁错位置
    裁错位置,脸库识别全空)。"""
    si = ctx.screen_loader.get_screen(screen_name)
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


def ensure_boss_weakness_map(ctx: SrContext) -> dict[str, list[str]]:
    """boss 名 → 弱点属性表(全玩法扁平;assets/game_data/tl_boss_weaknesses.yml)。

    弱点主路径:「建议属性」图标过小且 boss 卡底板带 tint,雷紫/量子蓝色相域
    跨场景渲染重叠,像素颜色识别无法稳定仲裁紫色系;boss 名为大字高置信 OCR,
    以名查表为弱点唯一来源,颜色识别仅作表未收录 boss 的降级。表未命中 = 空
    dict(纯降级,不报错)。缓存 ctx(只读资源,幂等,并发安全)。
    """
    cached = getattr(ctx, 'tl_boss_weakness_map', None)
    if cached is not None:
        return cached
    path = os_utils.get_path_under_work_dir('assets', 'game_data', _BOSS_WEAKNESS_FILE)
    data = YamlOperator(path).data or {}
    out: dict[str, list[str]] = {}
    for mode_bosses in data.values():
        if isinstance(mode_bosses, dict):
            out.update(mode_bosses)
    ctx.tl_boss_weakness_map = out
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
      → 物理(白色双剑=物理,实机帧标定);
    - 紫对仲裁:TM 最佳为 雷/量子 且色相明确落在另一域 → 按色相纠正(同色不同相,
      TM 色彩主导会互串,实机帧实测雷/量子互错);
    - 低分回退:TM < 阈值 → 色相域判定(全 blob 标定全对)。
    """
    bh, bw = crop.shape[:2]
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    s, v = hsv[:, :, 1].astype(int), hsv[:, :, 2].astype(int)
    colored_px = int(((s > 60) & (v > 80)).sum())
    white_px = int(((s < 60) & (v > 130)).sum())
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


def _detect_weakness_blobs(zone: MatLike,
                           blob_max: int = _WEAKNESS_BLOB_MAX) -> list[tuple[int, int, int, int]]:
    """图块带 → 图标外接框列表(按 x 序;彩色纹样 + 白色纹样双路,膨胀融臂去重)。

    白色路放宽到 S<60,V>130:底板带 tint 的画面(如末日幻影 boss 卡)会把
    物理白色纹样压灰(S 40-60),过严会整图标漏检;彩色图标(S>60)不受影响。
    """
    hsv = cv2.cvtColor(zone, cv2.COLOR_RGB2HSV)
    s, v = hsv[:, :, 1].astype(int), hsv[:, :, 2].astype(int)
    kernel = np.ones((3, 3), np.uint8)
    boxes: list[tuple[int, int, int, int]] = []
    seen: list[tuple[int, int]] = []
    for mask_bool in ((s > 60) & (v > 80), (s < 60) & (v > 130)):
        mask = mask_bool.astype(np.uint8) * 255
        mask = cv2.dilate(mask, kernel, iterations=1)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if not (_WEAKNESS_BLOB_MIN <= w <= blob_max
                    and _WEAKNESS_BLOB_MIN <= h <= blob_max):
                continue
            if any(abs(x - sx) < 12 and abs(y - sy) < 12 for sx, sy in seen):
                continue
            seen.append((x, y))
            boxes.append((x, y, w, h))
    boxes.sort(key=lambda b: b[0])
    return boxes


_WEAKNESS_BOSS_MAX_DY: int = 300      #: boss 名行与其波次锚行的最大纵向距离
                                     # (同 boss 卡内;超出视为跨卡,不覆盖)

# --------------------------------------------------------------------------
# 星启(三节点)布局槽位标定:锚(「建议属性」OCR det 框)相对槽位裁片的偏移。
# 双节点布局(难度 01-03)槽位用静态 screen_info area;星启(难度 04)行位置
# 整体上移(行距 282→217),静态 area 仅行1 同位、行2/行3 错位(实测空编队
# 裁片亮度异常)——锚行数 >2 时全行改按锚偏移计算 rect(行1 实测同位收敛)。
# --------------------------------------------------------------------------
_SLOTS_ANCHOR_DY: int = -11          #: 槽位裁片顶相对锚 det 框顶偏移(星启帧标定,
                                     # 行1 -11 与行3 推算一致)
_SLOTS_XS: tuple[int, ...] = (988, 1071, 1153, 1236)  #: 4 槽裁片左缘(与静态 area 同 x)
_SLOT_SIZE: int = 74                 #: 槽位裁片边长(方,与静态 area 同尺寸)


def _match_boss_weaknesses(ocr_results: list,
                           anchor_y: int,
                           mapping: dict[str, list[str]]) -> list[str] | None:
    """锚行上方的 boss 名 OCR 文本 → 弱点表值;未命中返回 None。

    boss 名行(「节点N | boss名」标题行)在其波次锚行上方同一 boss 卡内;
    OCR 可能将「节点一」与 boss 名粘为一条,故按「文本含表名」匹配,
    多命中取距锚最近者(同一卡内唯一,跨卡由距离上限拦截)。
    """
    best_name: str | None = None
    best_dy: int | None = None
    for r in ocr_results:
        text = (r.data or '').strip()
        if not text or r.y >= anchor_y:
            continue
        dy = anchor_y - r.y
        if dy > _WEAKNESS_BOSS_MAX_DY:
            continue
        for boss_name in mapping:
            if boss_name in text and (best_dy is None or dy < best_dy):
                best_name, best_dy = boss_name, dy
                break
    if best_name is None:
        return None
    return list(mapping[best_name])


def read_team_waves(ctx: SrContext, image: MatLike,
                    screen_name: str = SCREEN_NAME,
                    weakness_layout: str = _WEAKNESS_LAYOUT_BELOW,
                    boss_weakness_map: dict[str, list[str]] | None = None) -> list[WaveInfo]:
    """按「建议属性」锚行装配波次列表(每锚 = 一波,数量实读)。

    每波绑定:该波弱点属性 + 该波当前编队成员(槽位 area 按行号取,
    area 未建档的行 members = [])。锚未读到 = 空列表(降级不编造)。
    screen_name:槽位 area 的归属屏——逐光捡金各编队屏行结构同构但槽位坐标
    逐屏独立建档(FH=忘却之庭-编队 / PF=虚构叙事-编队 / AS=末日幻影-编队,
    槽间距 90px vs 65px)。
    weakness_layout:弱点图块带相对锚行的布局,'below'=锚行正下方(忘却之庭/
    虚构叙事), 'inline'=与锚文字同行紧贴其右(末日幻影 boss 卡);
    布局错配 = 图块带落在搜索区外,弱点恒为空列表(不报错,降级语义)。
    boss_weakness_map:boss 名 → 弱点表(ensure_boss_weakness_map)。命中时
    覆盖该波颜色识别结果(主路径);boss 名取锚行上方同卡标题行的 OCR 文本
    (含即命中,最近优先,距离上限 300px 防跨卡误配)。"""
    templates = ensure_avatar_templates(ctx)
    results = ctx.ocr_service.get_ocr_result_list(image=image)
    anchors = sorted(
        (r for r in results if _WEAKNESS_ANCHOR_TEXT in (r.data or '')),
        key=lambda r: r.y,
    )
    # 锚行数 >2 = 星启三节点布局:槽位 rect 走锚偏移(静态 area 仅双节点标定)
    multi_row = len(anchors) > 2
    waves: list[WaveInfo] = []
    for idx, a in enumerate(anchors[:_WEAKNESS_MAX_ROWS], start=1):
        if weakness_layout == _WEAKNESS_LAYOUT_INLINE:
            # 同行布局:OCR det 框可能粘进首图标,起点用固定偏移绕开;
            # 带宽只盖图标带(不及右侧相邻元素防误检)
            x1 = a.x + _WEAKNESS_INLINE_X_OFF
            y1 = max(0, a.y - 8)
            zone_w, zone_h = _WEAKNESS_INLINE_ZONE_W, a.h + 16
            blobs = _detect_weakness_blobs(image[y1:y1 + zone_h, x1:x1 + zone_w],
                                           blob_max=_WEAKNESS_INLINE_BLOB_MAX)
        else:
            x1 = max(0, a.x - 15)
            y1 = a.y + a.h + 2
            zone_w, zone_h = _WEAKNESS_ZONE_W, _WEAKNESS_ZONE_H
            blobs = _detect_weakness_blobs(image[y1:y1 + zone_h, x1:x1 + zone_w])
        weaknesses: list[str] = []
        for (bx, by, bw, bh) in blobs:
            pad = 4
            zone = image[y1:y1 + zone_h, x1:x1 + zone_w]
            crop = zone[max(0, by - pad):by + bh + pad, max(0, bx - pad):bx + bw + pad]
            name = _classify_weakness_blob(crop, ensure_element_templates(ctx))
            if name:
                weaknesses.append(name)
        if boss_weakness_map:
            mapped = _match_boss_weaknesses(results, a.y, boss_weakness_map)
            if mapped is not None:
                weaknesses = mapped
        members: list[MemberGuess] = []
        if multi_row:
            y1 = max(0, a.y + _SLOTS_ANCHOR_DY)
            for xs in _SLOTS_XS:
                crop = image[y1:y1 + _SLOT_SIZE, xs:xs + _SLOT_SIZE]
                members.append(_identify_crop(crop, templates))
        else:
            area_missing = False
            for i in range(1, 5):
                rect = _get_area_rect(ctx, f'槽位{idx}头像-{i}', screen_name)
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
    """角色列表 tab 的可见网格(4 列 × 可见 4 行;几何标定见模块 docstring)。

    ⚠️ 仅列表停驻位置与标定帧一致时可靠;滚动任意停驻(半格)用
    ``read_character_cells_by_level``(锚点驱动,位置无关)。"""
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


def read_character_cells_by_level(ctx: SrContext, image: MatLike) -> list[AnchorCell]:
    """等级文本锚驱动的角色列表识别(滚动停驻位置无关)。

    OCR 找列表区全部「等级」文本锚(每张卡下方一条「等级NN」),每锚上方裁
    头像区做脸库匹配,取匹配结果。返回按 (y, x) 排序(自上而下、自左而右)。"""
    area_rect = _get_area_rect(ctx, '区域-角色网格')
    templates = ensure_avatar_templates(ctx)
    cells: list[AnchorCell] = []
    if area_rect is None:
        return cells
    results = ctx.ocr_service.get_ocr_result_list(image=image, rect=area_rect)
    for r in results:
        if _LEVEL_ANCHOR_TEXT not in (r.data or ''):
            continue
        ax = r.x + _LEVEL_ANCHOR_DX
        ay = r.y + _LEVEL_ANCHOR_DY
        if (ax < 0 or ay < 0
                or ay + _LEVEL_ANCHOR_AVATAR_H > image.shape[0]
                or ax + _LEVEL_ANCHOR_AVATAR_W > image.shape[1]):
            continue  # 裁片出界跳过
        crop = image[ay:ay + _LEVEL_ANCHOR_AVATAR_H, ax:ax + _LEVEL_ANCHOR_AVATAR_W]
        guess = _identify_crop(crop, templates)
        cells.append(AnchorCell(
            center=Point(ax + _LEVEL_ANCHOR_AVATAR_W // 2,
                         ay + _LEVEL_ANCHOR_AVATAR_H // 2),
            guess=guess))
    cells.sort(key=lambda c: (c.center.y, c.center.x))
    return cells


def grid_cell_center(ctx: SrContext, row: int, col: int) -> Point | None:
    """角色网格单元格点击中心(1080p 全图坐标;区域缺失 None)。"""
    area_rect = _get_area_rect(ctx, '区域-角色网格')
    if area_rect is None:
        return None
    x = area_rect.x1 + _GRID_CELL_X_OFF + col * _GRID_CELL_DX + _GRID_CELL_W // 2
    y = area_rect.y1 + _GRID_CELL_Y_OFF + row * _GRID_CELL_DY + _GRID_CELL_H // 2
    return Point(x, y)


def wave_row_select_point(ctx: SrContext, wave_idx: int) -> Point | None:
    """波次行选中点击点(该行敌人预览区中心,非交互控件;1 基 wave_idx;缺失 None)。

    点击该行任意非控件区即选中该行(白框态),后续点角色卡填入本行 —— 交互实测
    点预设套用前点行选中生效。
    """
    rect = _get_area_rect(ctx, f'槽位{wave_idx}头像-1')
    if rect is None:
        return None
    return Point(rect.x1 - 180, rect.y1 + 46)


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

