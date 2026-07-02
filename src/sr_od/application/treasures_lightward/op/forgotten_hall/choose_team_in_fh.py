import time
from typing import Callable, ClassVar, Optional, List

import cv2
import numpy as np
from cv2.typing import MatLike

from basic import Rect, Point
from basic.i18_utils import gt
from basic.img import cv2_utils
from basic.log_utils import log
from sr.const.character_const import CharacterCombatType, CHARACTER_COMBAT_TYPE_LIST, Character
from sr.context.context import Context
from sr.operation import Operation, OperationOneRoundResult
from sr.operation.combine import CombineOperation
from sr.operation.unit.click import ClickPoint
from sr.treasures_lightward.op.choose_character import TlChooseCharacter


class SessionInfo:  # 关卡的信息

    def __init__(self, num: int, combat_type_rect_list: List[Rect], character_rect_list: List[Rect]):

        self.num: int = num
        """关卡编码"""

        self.combat_type_rect_list: List[Rect] = combat_type_rect_list
        """属性框"""

        self.character_rect_list: List[Rect] = character_rect_list
        """角色框"""


class ChooseTeamInForgottenHall(Operation):

    SESSION_1: ClassVar[SessionInfo] = SessionInfo(
        num=1,
        combat_type_rect_list=[
            Rect(1112, 760, 1142, 790),
            Rect(1142, 760, 1172, 790),
            Rect(1172, 760, 1202, 790),
        ],
        character_rect_list=[
            Rect(1380, 695, 1455, 765),
            Rect(1480, 695, 1555, 765),
            Rect(1580, 695, 1655, 765),
            Rect(1680, 695, 1755, 765),
        ]
    )

    SESSION_2: ClassVar[SessionInfo] = SessionInfo(
        num=2,
        combat_type_rect_list=[
            Rect(1112, 870, 1142, 900),
            Rect(1142, 870, 1172, 900),
            Rect(1172, 870, 1202, 900),
        ],
        character_rect_list=[
            Rect(1380, 795, 1455, 865),
            Rect(1480, 795, 1555, 865),
            Rect(1580, 795, 1655, 865),
            Rect(1680, 795, 1755, 865),
        ]
    )

    CLEAR_ALL_CHARACTERS: ClassVar[Point] = Point(1829, 676)

    ALL_SESSION_LIST: ClassVar[List[SessionInfo]] = [SESSION_1, SESSION_2]

    def __init__(self, ctx: Context, cal_team_member_func: Callable,
                 choose_team_callback: Optional[Callable[[List[List[Character]]], None]] = None):
        """
        需要已经在
        :param ctx:
        :param cal_team_member_func:
        :param choose_team_callback: 计算得到配队后的回调
        """
        super().__init__(ctx, op_name=gt('逐光捡金 选择配队'))
        self.cal_team_func: Callable = cal_team_member_func
        self.phase: int = 0
        self.teams: List[List[Character]] = []
        self.choose_team_callback: Optional[Callable[[List[List[Character]]], None]] = choose_team_callback

    def _execute_one_round(self) -> OperationOneRoundResult:
        if self.phase == 0:  # 按照BOSS属性计算配队
            if self._cal_team_member():
                self.phase += 1
                return self.round_wait()
            else:
                time.sleep(1)
                return self.round_retry('自动配队失败')
        elif self.phase == 1:  # 取消原有的角色选择
            if self._cancel_all_chosen():
                self.phase += 1
                return self.round_wait()
            else:
                return self.round_retry('取消原有选择失败')
        elif self.phase == 2:  # 选择配队:
            if self._choose_character():
                self.phase += 1
                return self.round_success()
            else:
                return self.round_retry('选择新角色失败')

        return self.round_retry('unknown')

    def _cal_team_member(self) -> bool:
        """
        按照BOSS属性计算配队
        :return:
        """
        screen: MatLike = self.screenshot()
        combat_type_in_session = self._get_all_node_combat_types(screen)

        self.teams = self.cal_team_func(combat_type_in_session)
        if self.teams is None:
            return False
        for t in self.teams:
            if t is None:
                return False

        if self.choose_team_callback is not None:
            self.choose_team_callback(self.teams)

        return True

    def _get_all_node_combat_types(self, screen: Optional[MatLike] = None) -> List[List[CharacterCombatType]]:
        """
        获取全部BOSS对应的属性
        :param screen: 屏幕截图
        :return:
        """
        if screen is None:
            screen = self.screenshot()
        node_combat_types = []
        for session in ChooseTeamInForgottenHall.ALL_SESSION_LIST:
            combat_types = []
            for rect in session.combat_type_rect_list:
                t = self._get_boss_combat_type(screen, rect)
                if t is not None:
                    combat_types.append(t)
            node_combat_types.append(combat_types)
        log.info('识别所需属性为 %s', [i.cn for combat_types in node_combat_types for i in combat_types])
        return node_combat_types

    def _get_boss_combat_type(self, screen: MatLike, rect: Rect) -> Optional[CharacterCombatType]:
        """
        获取BOSS对应的属性
        :param screen: 屏幕截图
        :param rect: 属性区域
        :return:
        """
        part, _ = cv2_utils.crop_image(screen, rect)

        # b, g, r = cv2.split(part)
        # print(np.mean(b), np.mean(g), np.mean(r))
        # cv2_utils.show_image(part, win_name='part', wait=0)

        gray = cv2.cvtColor(part, cv2.COLOR_BGR2GRAY)
        _, bw = cv2.threshold(gray, np.mean(gray), 255, cv2.THRESH_BINARY)
        bw = cv2_utils.connection_erase(bw, threshold=30)
        origin, mask = cv2_utils.convert_to_standard(part, bw, width=55, height=55, bg_color=(0, 0, 0))  # 扣出属性图标

        source_kps, source_desc = cv2_utils.feature_detect_and_compute(origin, mask)
        # cv2_utils.show_image(origin, win_name='_get_boss_combat_type_source')

        for t in CHARACTER_COMBAT_TYPE_LIST:
            template = self.ctx.ih.get_character_combat_type(t.id)
            if template is None:
                log.error('找不到属性模板 %s', t.id)
                continue
            # cv2_utils.show_image(template.origin, win_name='_get_boss_combat_type_template')

            # 模板匹配试一次 不过这里会有坑 就是模板必须从这个页面截取
            result_list = self.ctx.im.match_template(origin, t.id, template_sub_dir='character_combat_type')
            if len(result_list) > 0:
                return t

            # TODO 改用颜色平均值匹配 这个应该简单准确率又高

        # 特征匹配准确率不够高
        for t in CHARACTER_COMBAT_TYPE_LIST:
            template = self.ctx.ih.get_character_combat_type(t.id)
            if template is None:
                log.error('找不到属性模板 %s', t.id)
                continue

            template_kps, template_desc = template.features
            pos = cv2_utils.feature_match_for_one(
                source_kps, source_desc,
                template_kps, template_desc,
                template.origin.shape[1], template.origin.shape[0],
                source_mask=mask,
                knn_distance_percent=0.7)

            if pos is not None:
                return t

        return None

    def _cancel_all_chosen(self) -> bool:
        """
        取消原有的所有选择
        :return:
        """
        return self.ctx.controller.click(ChooseTeamInForgottenHall.CLEAR_ALL_CHARACTERS)

    def _choose_character(self) -> bool:
        ops: List[Operation] = []

        idx: int = -1
        for session in ChooseTeamInForgottenHall.ALL_SESSION_LIST:
            idx += 1
            team = self.teams[idx]
            ops.append(ClickPoint(self.ctx, session.character_rect_list[0].center))
            for character in team:
                if character is not None:
                    ops.append(TlChooseCharacter(self.ctx, character.id))
        op = CombineOperation(
            self.ctx,
            ops=ops,
            op_name='逐光捡金 选择角色'
        )
        return op.execute().success
