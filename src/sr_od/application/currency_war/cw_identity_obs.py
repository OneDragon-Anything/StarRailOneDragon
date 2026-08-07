# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 **备战屏 视觉身份观测**(SIFT,非 OCR)。

与 ``cw_observation``(OCR 字段)互补:本模块读 OCR 看不见的**身份** —— 备战栏 / 舞台槽内角色
立绘 → 规范名(``read_deployed_chars`` / ``read_bench_chars``),用 ``currency_war_char_id`` 的
SIFT 匹配器对 ``character_avatar`` 脸近景库。

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

**2026-08-06 实测**(D-75):脸近景库对 4 个面部独特角色强命中(佩拉 / 黑塔 / Saber / 藿藿);
配饰角色 / 货币战争变体待多样本核(见 ``currency_war_char_id`` docstring)。
"""
from __future__ import annotations

from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from sr_od.application.currency_war.currency_war_char_id import (
    AvatarTemplates,
    identify_character,
)
from sr_od.application.currency_war.cw_chars import CHARACTER_ROSTER, get_char
from sr_od.application.currency_war.cw_obs_core import _area_rect
from sr_od.application.currency_war.cw_state import BenchChar
from sr_od.config.character_const import get_character_by_id
from sr_od.context.sr_context import SrContext


def resolve_char_name(avatar_id: str) -> str | None:
    """SIFT 的 avatar_id(主游英文 id,如 ``pela``)→ 货币战争规范名(如 ``佩拉``)。

    路径:``get_character_by_id(avatar_id).cn`` 得主游 cn 名 → 若在 ``CHARACTER_ROSTER`` 直接用;
    否则(货币战争变体共脸异名,如脸库归一到「姬子」但 roster 有「姬子·启行」+「姬子」)→ 取 roster
    中含该 cn 的成员(子串消歧);仍无 → None(SIFT 命中了主游角色但不在货币战争 roster,如脸库误匹配
    或货币战争未收录角色)。

    ⚠️ 变体消歧对「基础名 + 变体名并存」的 roster(姬子/姬子·启行、刃/千冶·刃)子串命中**第一个**,
    可能不准 —— 变体与基础角色共脸,SIFT 本身无法区分,需结合星级 / 阵营等旁证(待多样本核)。
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
