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

from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from sr_od.application.currency_war.currency_war_char_id import (
    AvatarTemplates,
    identify_character,
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
    → 规范名。faction 取角色首阵营(粗;权威阵营计数看 board OCR);star 暂默认 1(胸前金星视觉
    计数待补)。
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
            star=1,                          # 星级视觉读待补(胸前金星计数);暂默认 1
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
