"""逐光捡金编队识别:预设编队 tab(预设卡内 4 成员小头像)。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.treasures_lightward.obs.tl_team_common import (
    MemberGuess,
    PresetTeam,
    get_area_rect,
    identify_crop,
)
from sr_od.config.avatar_templates import iter_avatar_templates

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from sr_od.context.sr_context import SrContext

# --------------------------------------------------------------------------
# 预设卡内小头像几何(相对「预设卡-N」rect 原点;实机帧标定)
# 卡内 4 个头像 art 子区(避开卡框与底部「队伍N/等级」标签带),x 起点 4 个。
# --------------------------------------------------------------------------
_PRESET_MEMBER_COUNT: int = 4
_PRESET_MINI_X_OFFS: tuple[int, ...] = (5, 137, 268, 400)   #: 各头像子区 x 偏移
_PRESET_MINI_Y_OFF: int = 55                                #: 头像子区 y 偏移
_PRESET_MINI_W: int = 116
_PRESET_MINI_H: int = 70


def read_preset_teams(ctx: SrContext, image: MatLike) -> list[PresetTeam]:
    """预设编队 tab 的队伍组(每卡 4 成员绑组;卡 rect 来自 screen_info 预设卡-N)。"""
    templates = iter_avatar_templates(ctx)
    teams: list[PresetTeam] = []
    for team_idx in range(1, 5):
        rect = get_area_rect(ctx, f'预设卡-{team_idx}')
        if rect is None:
            continue
        members: list[MemberGuess] = []
        for xi in _PRESET_MINI_X_OFFS:
            x1 = rect.x1 + xi
            y1 = rect.y1 + _PRESET_MINI_Y_OFF
            crop = image[y1:y1 + _PRESET_MINI_H, x1:x1 + _PRESET_MINI_W]
            members.append(identify_crop(crop, templates))
        teams.append(PresetTeam(team_idx=team_idx, members=members))
    return teams
