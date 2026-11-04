"""忘却之庭-编队画面额外识别器(per-screen recognizer)。

``analyze_screen`` 精准命中「忘却之庭-编队」后,框架按 ``screen_name`` 查表调用本识别器,
把编队画面的结构化领域事实(关卡名 / 环境效果 / 挑战目标 / 左侧激活 tab / 右侧两队伍槽
成员 / 左侧列表内容)塞进 ``extras``。识别算法、阈值标定与歧义策略见
:mod:`sr_od.application.treasures_lightward.obs.tl_team_obs`(纯读,并发安全)。
"""
from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from sr_od.application.treasures_lightward.obs.tl_team_obs import (
    SCREEN_NAME,
    collect_tl_team_info,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext


class TlTeamRecognizer(ScreenRecognizer):
    """忘却之庭-编队画面额外识别器。"""

    screen_name: str = SCREEN_NAME

    extras_doc: dict[str, str] = {
        'stage_name': '右上关卡名(如 物竞天择其一);读不到 None',
        'environment_text': '环境效果全文(本期记忆紊流文本,与选关画面紊流弹窗同文)',
        'star_targets': '挑战目标行 list(满星条件,通常 3 行)',
        'left_tab': '左侧激活 tab(角色列表|预设编队);判不出 None',
        'waves': '波次列表 list[WaveInfo](每元素 {wave_idx,weaknesses,members};每锚行=一波,'
                 '数量实读——混忆常规 2 波,其他模式可能不同)。weaknesses=该波敌人弱点属性名'
                 'list(左右序;元素图标模板匹配主判+色相仲裁,解不出的图标不进列表);'
                 'members=该波当前编队(4 元素按槽位序,MemberGuess 同老字段语义;槽位 area '
                 '未建档的行=[]);waves=[] = 锚未读到(降级)',
        'character_grid': '角色列表 tab:可见网格 list[GridCell](元素 {row,col,guess};row/col 0 基,'
                          '4 列×可见 4 行,滚动后需多帧);非该 tab 为 null',
        'preset_teams': '预设编队 tab:队伍组 list[PresetTeam](元素 {team_idx,members};team_idx 1 基从上到下,'
                        'members=4 成员绑组);非该 tab 为 null;卡内小头像歧义率高,以 candidates 为准',
    }

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,   # noqa: ARG002  本识别器经 screen_loader 读 area,未直接用入参
    ) -> dict | None:
        """读编队画面结构化事实 → dict;字段含义见 ``extras_doc``。"""
        return asdict(collect_tl_team_info(ctx, image))
