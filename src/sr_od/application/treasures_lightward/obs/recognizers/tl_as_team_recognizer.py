"""末日幻影-编队画面额外识别器(per-screen recognizer)。

``analyze_screen`` 精准命中「末日幻影-编队」后按 ``screen_name`` 查表调用本识别器,
把编队画面的结构化领域事实(难度徽章 / 列表展开态 / 两队伍槽成员 / 左侧列表内容)
塞进 ``extras``。识别算法与歧义策略见
:mod:`sr_od.application.treasures_lightward.obs.tl_team_obs`(纯读,并发安全);
槽位/页签/徽章 area 按末日幻影屏独立建档(与忘却之庭-编队同命名规范)。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from one_dragon.base.screen.screen_utils import (
    FindAreaResultEnum,
    find_area_in_screen,
)
from sr_od.application.treasures_lightward.obs.tl_team_obs import (
    ensure_boss_weakness_map,
    read_character_cells_by_level,
    read_team_waves,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.application.treasures_lightward.obs.tl_team_obs import (
        AnchorCell,
        WaveInfo,
    )
    from sr_od.context.sr_context import SrContext

SCREEN_NAME: str = '末日幻影-编队'


@dataclass
class AsTeamView:
    """末日幻影-编队画面单帧结构化事实。"""

    difficulty: str | None
    list_open: bool
    waves: list[WaveInfo] = field(default_factory=list)
    character_cells: list[AnchorCell] = field(default_factory=list)


class TlAsTeamRecognizer(ScreenRecognizer):
    """末日幻影-编队画面额外识别器。"""

    screen_name: str = SCREEN_NAME

    extras_doc: dict[str, str] = {
        'difficulty': '难度徽章(难度03|难度04);读不出 None(列表展开会遮住徽章,展开态恒 None)。'
                      '04 为三节点布局,04 下 waves 恒 3 行且槽位走锚偏移识别',
        'list_open': '左侧角色列表是否展开(「角色列表」页签命中);填充前必须展开',
        'waves': '队伍槽 list[WaveInfo](每元素 {wave_idx,weaknesses,members};每节点行=一波,'
                 '数量按「建议属性」锚行实读)。weaknesses 主路径 = boss 名查静态弱点表'
                 '(assets/game_data/tl_boss_weaknesses.yml,详情页人工仲裁),'
                 '表未收录 boss 降级为图标颜色识别(紫色系雷/量子不可仲裁,可能误判)。'
                 'members=该节点当前编队(4 元素按槽位序,'
                 'MemberGuess 同老字段语义;槽位 art+候选诚实返回,AS 槽位渲染特写个别角色'
                 '置信不过门槛时 char=None);waves=[] = 锚未读到(降级)。'
                 '槽位 rect 取法:锚行 ≤2 用静态 screen_info area(01-03),'
                 '>2(星启)全行按锚偏移标定计算',
        'character_cells': '列表可见角色 list[AnchorCell](元素 {center,guess};center=点击中心,'
                           'guess 同 MemberGuess;滚动停驻位置无关,滚动后需多帧合并);列表未展开 = []',
    }

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,   # noqa: ARG002  本识别器经 screen_loader 读 area,未直接用入参
    ) -> dict | None:
        """读编队画面结构化事实 → dict;字段含义见 ``extras_doc``。"""

        def _hit(badge: str) -> bool:
            return find_area_in_screen(
                ctx, image, ctx.screen_loader.get_area(SCREEN_NAME, badge)
            ) is FindAreaResultEnum.TRUE

        difficulty: str | None = None
        # 04 先判:两徽章同 rect,「难度04」帧对 03 徽章 lcs 0.75,靠 area 阈值
        # (0.85)拦截;顺序倒转作第二道防(旧帧实测 03 先判误命中)
        for badge in ('难度04', '难度03'):
            if _hit(f'徽章-{badge}'):
                difficulty = badge
                break

        tab_area = ctx.screen_loader.get_area(SCREEN_NAME, '列表-角色列表页签')
        list_open = find_area_in_screen(ctx, image, tab_area) is FindAreaResultEnum.TRUE

        view = AsTeamView(
            difficulty=difficulty,
            list_open=list_open,
            # AS boss 卡弱点图标与「建议属性」文字同行(≠忘却之庭的下方布局);
            # 弱点主路径 = boss 名查静态表(小图标+tint 下紫色系颜色不可仲裁)
            waves=read_team_waves(ctx, image, screen_name=SCREEN_NAME,
                                  weakness_layout='inline',
                                  boss_weakness_map=ensure_boss_weakness_map(ctx)),
        )
        result = asdict(view)
        # AnchorCell.center 为 Point 对象,JSON 序列化前转坐标数组
        result['character_cells'] = [
            {
                'center': [cell.center.x, cell.center.y],
                'guess': {
                    'char': cell.guess.char,
                    'confident': cell.guess.confident,
                    'candidates': [list(t) for t in cell.guess.candidates],
                    'empty': cell.guess.empty,
                },
            }
            for cell in read_character_cells_by_level(ctx, image)
        ]
        return result
