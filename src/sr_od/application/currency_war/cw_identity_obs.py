# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 **备战屏 视觉身份观测**(SIFT,非 OCR)。

与 ``cw_observation``(OCR 字段)互补:本模块读 OCR 看不见的**身份** —— 备战栏 / 舞台槽内角色
立绘 → 规范名(``read_deployed_chars`` / ``read_bench_chars``),用 ``currency_war_char_id`` 的
SIFT 匹配器对模板库(生产用 ``character_cw_portrait`` 货币战争立绘库,见 ``currency_war_char_id`` docstring)。

**与 bot 跟踪的关系**(设计):``GameState.deployed`` / ``bench`` 默认由 **bot 跟踪**(buy/deploy
动作推演,``simulate`` 维护,见 ``cw_state``)—— plan-time 快、无需 SIFT。本模块的视觉 reads 是
**独立旁路**,用途:① 离线从截图重建 GameState(测试 / replay,无需跑 bot);② bot 跟踪漂移时
从画面恢复 / 校验。故**不**接进 ``read_game_state``(避免每帧 SIFT + 与 bot 跟踪双写冲突)。

槽位坐标 = screen_info 固定 area(``前排-1..4`` / ``后排-1..6`` / ``备战栏-1..9``),经
``cw_obs_core._area_rect`` 读 —— 改坐标改 yml 即可。空槽位 SIFT 内点低 → 自然落 None
(无需「槽位是否填充」预判)。

**架构:纯 CV 核心 + ctx 薄包装** —— ``identify_slots`` 只吃 (screen, templates, slots, row),
可离线硬编码 rect 测;``read_deployed_chars`` / ``read_bench_chars`` 从 ctx screen_info 取 rect
再调核心。与 ``currency_war_char_id`` 同样的「纯 CV + 外部接线」分层。

**可靠性:实测初步可用(2026-08-09 D-22)**:r1-8 备战截图 SIFT 立绘库 **6/6 有角色槽命中**(inliers
29-48)+ 空槽不误 → 立绘库可用,推翻脸库旧结论。待补:共脸变体样本 + 角色名 ground truth(见
``currency_war_char_id`` docstring)。
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from sr_od.application.currency_war.currency_war_char_id import (
    AvatarTemplates,
    identify_character,
    load_avatar_templates,
)
from sr_od.application.currency_war.cw_chars import CHARACTER_ROSTER, get_char
from sr_od.application.currency_war.cw_equipment import read_equipped_below
from sr_od.application.currency_war.cw_obs_core import _area_rect
from sr_od.application.currency_war.cw_state import BenchChar
from sr_od.config.character_const import get_character_by_id
from sr_od.context.sr_context import SrContext


def resolve_char_name(avatar_id: str) -> str | None:
    """SIFT 的 avatar_id(模板目录名)→ 货币战争规范名(``CHARACTER_ROSTER`` 成员)。

    **半身立绘库(``character_cw_portrait``)key = 中文规范名**(白框法采,含变体独立模板,如
    ``姬子·启行`` / ``千冶·刃``)→ ``identify_character`` 返回的 avatar_id 已是规范名 → 本函数
    第 54 行 ``avatar_id in CHARACTER_ROSTER`` 直接命中返。变体**可被 SIFT 区分**(D-54 验:
    deployed_p1r9 后排-2 姬子·启行 inliers=38,基础姬子 <7 连 top3 未进 —— 共脸对分数拉开,
    非无法区分;旧「脸库归一·SIFT 无法区分变体」结论是脸库时代产物,已废)。

    56-65 行(``get_character_by_id`` 英文 id→cn + 子串消歧)是 **legacy 脸库路径**(英文 id),
    半身立绘库基本不走;留作兜底。仍无 → None(SIFT 命中但不在货币战争 roster,如开拓者 roster 缺、
    脸库误匹配)。
    """
    if avatar_id in CHARACTER_ROSTER:
        return avatar_id   # CW 立绘库 key 是中文规范名(白框法采),直接返(非主游英文 id)
    c = get_character_by_id(avatar_id)
    if c is None:
        return None
    cn = c.cn
    if cn in CHARACTER_ROSTER:
        return cn
    for name in CHARACTER_ROSTER:          # 变体消歧:roster 含此 cn 名的成员
        if cn in name:
            return name
    return None


def ensure_portrait_templates(ctx: SrContext) -> AvatarTemplates | None:
    """确保 ctx 缓存 ``character_cw_portrait`` 立绘 SIFT 模板;返 templates 或 None(目录缺)。

    首次 load 缓存 ``ctx.cw_portrait_templates``;后续读缓存。**shop SIFT**(D-55,``read_shop_cards``)
    + deployed/bench SIFT 身份识别的模板加载点(deploy_bench 也读写此缓存)。**幂等**:同值重 load 无害。

    **并发安全**:只缓存只读资源(非 session/游戏状态),与运行中 operation 不竞争(同 ensure_equip_tm_templates)。
    buy 在 deploy 之前(BattlePrepCycle: buy→deploy),故 shop 不能依赖 deploy 才加载的模板 → 本函数按需加载。
    """
    templates = getattr(ctx, 'cw_portrait_templates', None)
    if templates is None:
        portrait_dir = Path(__file__).resolve().parents[4] / 'assets' / 'template' / 'character_cw_portrait'
        if not portrait_dir.is_dir():
            return None
        templates = load_avatar_templates(portrait_dir)
        ctx.cw_portrait_templates = templates
    return templates


# 金星(亮金色五角星)HSV 范围(CV 采样 4 样本 star_front_1..4 标定 2026-08-11;crop=RGB)。
# 亮金色 ≈ #FFD700:H 黄~橙(OpenCV 0-180),高 S 高 V。立绘金色装饰(衣服/腰带)也命中 → 靠位置(底部)过滤。
# HSV 金色范围;**V>150** 只抓自发光亮金星,滤暗金衣服装饰(ADR-0114,2026-08-13):
# 前排角色立绘底部有大量暗金衣服(V80-150)淹没金星,旧 V>80 把衣服抓成 area1279 大块致检测崩溃。
_STAR_GOLD_LO: tuple[int, int, int] = (10, 40, 150)
_STAR_GOLD_HI: tuple[int, int, int] = (45, 255, 255)
# TM 匹配阈值(2026-08-13:0.45。迭代:0.55→0.50 解后排-3 第2星 val0.511;0.50→0.45 解**后排-6 边槽**第2星
# val~0.45-0.50(ADR-0116)。「各槽位覆盖」发现:边槽第2星 TM val 系统性偏低(模板 a190 取自备战栏,
# 后排星透视更小 → 匹配偏弱)→ 每降一档解一个边槽(whack-a-mole;根治待**多模板 per 排**,ADR-0116 Considered)。
# 0.45 验证:立绘库 0/71 + 全 fixture 无新 FP + 所有 2★ 槽读 2 + 后排-6 读回 2(0.40 才过数噪声)。
_STAR_TM_THRESH: float = 0.45
# peak 轮廓圆度下限(ADR-0115,2026-08-13:0.25)。原 0.35 太紧 —— 真金星 circ 实测 0.34-0.50(随槽位
# 渲染微变),备战-9 边槽把同颗星 circ 压到 0.34<0.35 被误拒 → 2星读 1(假阴)。**立绘库 0/71 误判
# 不靠 circ**(area+aspect+V>150+TM 已挡死,circ>0.0 仍 0/71)+ 全 fixture 无新 FP → 放宽到 0.25 留足余量。
_STAR_CIRC_MIN: float = 0.25
# 四角星 TM 模板(单星 mask,19x19 area190,从备战栏-1 单星提取);模块级缓存避免每帧 imread。
_STAR_TMPL_CACHE: MatLike | None = None


def _load_star_tmpl() -> MatLike | None:
    """加载四角星 TM 模板(模块级缓存,首次 imread 后复用);缺失返 None(read_star fallback 1)。"""
    global _STAR_TMPL_CACHE
    if _STAR_TMPL_CACHE is None:
        p = Path(__file__).resolve().parent / 'template' / 'star_gold_tmpl.png'
        if p.exists():
            _STAR_TMPL_CACHE = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    return _STAR_TMPL_CACHE


def read_star(crop: MatLike) -> int:
    """数角色立绘底部金星(星级);``crop`` = 槽位 RGB crop(含立绘 + 底部金星)。

    金星 = **四角星**(十字星 ✦,自发光亮金黄),立绘**底部中央**(y > 0.65h);1/2/3 星 = N 颗并排。
    **TM 模板匹配法**(ADR-0114,替 ADR-0113 轮廓法):HSV V>150 抓亮金星(滤暗金衣服)→ 四角星模板
    matchTemplate → NMS 分离紧贴(2 星 gap 小)→ peak 局部 area/aspect/circ 验证滤残余装饰。

    轮廓法(ADR-0113)对 **2 星紧贴**(连通成大域 area>600 上限漏)+ **前排衣服淹没**(area1279
    把金星淹没)结构性失效。TM 各星独立滑窗匹配,紧贴亦分,V>150 滤衣服让 mask 干净 —— 治本。
    验证(2026-08-13):立绘库 71 张 0 误判 + 各位置 2星(前排-3/后排-3/备战-4)读 2 + 三月七 2星 +
    1星各槽稳读 1。**thresh 迭代(ADR-0114→0116)**:0.55→0.50 解后排-3 第2星(val0.511)→0.45 解**后排-6 边槽**
    第2星(val~0.45-0.50;边槽第2星 TM 系统性偏低,模板取自备战栏对后排透视星匹配偏弱)。「各槽位覆盖」每降一档
    解一个边槽(whack-a-mole;根治待多模板 per 排)。0.45 验:立绘库 0/71 + 全 fixture 无新 FP + 所有 2★ 读 2。
    **circ 放宽(ADR-0115)**:原 circ>0.35 太紧 —— 备战-9 边槽同颗金星 circ 渲染到 0.34 被误拒 → 2星读 1;
    放宽到 0.25(立绘库仍 0/71 + 全 fixture 无新 FP),备战-9 读回 2。

    :return: 星级(≥1);空图/无匹配/模板缺 → 1(角色必有星,fallback)。
    ⚠️ **offline 旁路**(live 走 bot tracking ``BenchChar.star``,非 read_star):comp_viability 离线
    校验用(cw_performance:185),不影响 live star_achievement。3星待 live 样本(逻辑同,数金星)。
    """
    if crop is None or crop.size == 0:
        return 1
    tmpl = _load_star_tmpl()
    if tmpl is None:
        return 1
    h, w = crop.shape[:2]
    region = crop[int(h * 0.65):, int(w * 0.15):int(w * 0.85)]  # 底部中央带(cy>0.65,盖前排0.72)
    hsv = cv2.cvtColor(region, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv, _STAR_GOLD_LO, _STAR_GOLD_HI)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    th, tw = tmpl.shape[:2]
    if mask.shape[0] < th or mask.shape[1] < tw:
        return 1
    res = cv2.matchTemplate(mask, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    if max_val < _STAR_TM_THRESH:
        return 1  # 无金星匹配 → fallback(角色必有星)
    # NMS:收集 ≥_STAR_TM_THRESH 的 peak,互距 > tw*0.6(分离紧贴 2星)
    min_dist = tw * 0.6
    ys, xs = np.where(res >= _STAR_TM_THRESH)
    pts = sorted(zip(ys, xs, strict=True), key=lambda p: res[p[0], p[1]], reverse=True)
    peaks: list[tuple[int, int]] = []
    for y, x in pts:
        if all((y - py) ** 2 + (x - px) ** 2 > min_dist ** 2 for py, px in peaks):
            peaks.append((int(y), int(x)))
    # peak 局部形状验证:四角星 area 80-320 + aspect 近方 0.80-1.20 + circ>_STAR_CIRC_MIN(滤细长/碎装饰)。
    # circ 下限见 _STAR_CIRC_MIN(ADR-0115:0.25,原 0.35 误拒备战-9 边槽真金星)。
    count = 0
    for py, px in peaks:
        local = mask[py:py + th, px:px + tw]
        if local.size < th * tw:
            continue
        lc, _ = cv2.findContours(local, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cc = max(lc, key=cv2.contourArea) if lc else None
        if cc is None:
            continue
        la = cv2.contourArea(cc)
        perim = cv2.arcLength(cc, True)
        bx, by, bw, bh = cv2.boundingRect(cc)
        aspect = bw / bh if bh > 0 else 0
        circ = 4 * np.pi * la / perim / perim if perim > 0 else 0
        if 80 <= la <= 320 and 0.80 <= aspect <= 1.20 and circ > _STAR_CIRC_MIN:
            count += 1
    return max(count, 1)


def identify_slots(
    screen: MatLike,
    templates: AvatarTemplates,
    slots: list[tuple[int, Rect]],
    row: str,
) -> list[BenchChar]:
    """纯 CV:按槽位裁切 → SIFT 识别 → BenchChar 列表(离线可测,无 ctx 依赖)。

    :param slots: ``[(slot_idx, rect), ...]``;rect = 1080p 槽位矩形(来自 screen_info 或硬编码)。
    :param row: ``"front"`` / ``"back"``(已上阵排)→ BenchChar.position_pref;``""``(备战栏)→ 用
        角色固有偏好(未上阵)。
    :return: 命中角色的 BenchChar 列表(空槽 / 低内点 / 歧义 / 非 roster → 跳过,不进列表)。

    每槽:裁 ``screen[y1:y2, x1:x2]`` → ``identify_character``(SIFT 对脸库)→ ``resolve_char_name``
    → 规范名。faction 取角色首阵营(粗;权威阵营计数看 board OCR);star = ``read_star``(立绘底部
    金星计数)。
    """
    out: list[BenchChar] = []
    for slot_idx, rect in slots:
        crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
        avatar_id, _inliers = identify_character(crop, templates)
        if avatar_id is None:
            continue
        name = resolve_char_name(avatar_id)
        if name is None:
            continue
        ch = get_char(name)
        out.append(BenchChar(
            slot=slot_idx,
            char_id=name,
            faction=ch.factions[0] if (ch is not None and ch.factions) else '?',
            star=read_star(crop),            # 立绘底部金星计数(1/2/3 星;见 read_star)
            position_pref=row if row else (ch.position_pref() if ch is not None else 'back'),
        ))
    return out


def _ctx_slots(ctx: SrContext, prefix: str, count: int) -> list[tuple[int, Rect]]:
    """从 ctx screen_info 取 ``{prefix}-1..{count}`` 的 (slot_idx, rect);area 缺失 → 跳过。"""
    out: list[tuple[int, Rect]] = []
    for i in range(1, count + 1):
        rect = _area_rect(ctx, f'{prefix}-{i}')
        if rect is not None:
            out.append((i, rect))
    return out


def read_deployed_chars(ctx: SrContext, screen: MatLike, templates: AvatarTemplates) -> list[BenchChar]:
    """舞台已上阵角色(前排 4 + 后排 6)→ list[BenchChar](position_pref=front/back)。

    空槽 / 未识别 → 不进列表。用途:离线重建 / 漂移恢复(**不进 read_game_state**;见模块 docstring)。
    """
    return (identify_slots(screen, templates, _ctx_slots(ctx, '前排', 4), 'front')
            + identify_slots(screen, templates, _ctx_slots(ctx, '后排', 6), 'back'))


def read_bench_chars(ctx: SrContext, screen: MatLike, templates: AvatarTemplates) -> list[BenchChar]:
    """备战栏角色(9 槽)→ list[BenchChar](position_pref=角色固有偏好,未上阵)。

    空槽 / 未识别 → 不进列表。用途:离线重建 / 漂移恢复。
    """
    return identify_slots(screen, templates, _ctx_slots(ctx, '备战栏', 9), '')


# ===== 穿戴装备识别(below-avatar mini icon;D-45/D-46)=====
def avatar_to_below(rect: Rect, half_w: int = 70, dy: int = 14, half_h: int = 33) -> Rect:
    """槽位 avatar rect → below-avatar icon 搜索 rect(avatar 底部下方;穿戴装备 icon 显示处)。

    前排 avatar ``[.,329,.,467]`` → below center cy=481(=y2+14;D-49 CV 实测 icon y 中心);后排/备战席
    avatar 底部 y2 不同,below 自动跟随(dy 相对 avatar 底部)。搜索区 ±half_w/half_h 覆盖固定 ~32px icon
    (D-49:icon 不随装备数变)。**half_w=70**:3件 icon 横排跨度 ~86px(cx±43),55 会切边缘 icon(D-49 修);
    70 覆盖3件且不含邻槽(front-2 在 cx+~144 外)。
    """
    cx = (rect.x1 + rect.x2) // 2
    cy = rect.y2 + dy
    return Rect(cx - half_w, cy - half_h, cx + half_w, cy + half_h)


def read_row_equipped(
    ctx: SrContext,
    screen: MatLike,
    tmpl_grays: dict[str, MatLike],
    prefix: str,
    count: int,
) -> dict[int, list[str]]:
    """某排(前排/后排/备战栏)每槽 below-avatar 已穿装备 → ``{slot_idx: [装备名]}``(纯读)。

    从 ctx screen_info 取 ``{prefix}-1..{count}`` avatar rect → ``avatar_to_below`` → ``read_equipped_below``。
    空槽 / 无命中 → 该 slot 不在 dict。与 ``read_deployed_chars``(角色身份)互补:角色 + 装备 = 完整槽位态。

    纯读(只 TM screen + templates,不写 session/全局),可进 recognizer(并发安全)。
    """
    below_rects = [(idx, avatar_to_below(r)) for idx, r in _ctx_slots(ctx, prefix, count)]
    return read_equipped_below(screen, tmpl_grays, below_rects)
