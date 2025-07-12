from cv2.typing import MatLike
from typing import Optional, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class ChooseSupportInTeam(SrOperation):

    STATUS_SUPPORT_NOT_FOUND: ClassVar[str] = '未找到支援角色'
    STATUS_SUPPORT_NEEDED: ClassVar[str] = '需要支援角色'

    def __init__(self, ctx: SrContext, character_id: Optional[str]):
        """
        需要在管理配队页面使用 选择对应支援角色
        如果不传入支援角色 则直接返回成功
        :param ctx:
        :param character_id:
        """
        SrOperation.__init__(self, ctx, op_name=gt('选择支援'))

        self.character_id: Optional[str] = character_id
        self.no_find_character_times: int = 0

    @operation_node(name='等待画面加载', node_max_retry_times=10, is_start_node=True)
    def wait_at_first(self) -> OperationRoundResult:
        """
        等待加载 左上角有【队伍】
        :return:
        """
        screen = self.screenshot()
        result = self.round_by_find_area(screen, '挑战副本', '队伍标题')
        if result.is_success:
            if self.character_id is None:
                return self.round_success()
            else:
                return self.round_success(ChooseSupportInTeam.STATUS_SUPPORT_NEEDED)
        else:
            return self.round_retry(result.status, wait=1)

    @node_from(from_name='等待画面加载', status=STATUS_SUPPORT_NEEDED)
    @operation_node(name='点击支援')
    def click_support(self) -> OperationRoundResult:
        """
        点击支援按钮
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '挑战副本', '支援按钮',
                                                 success_wait=1, retry_wait=1)

    @node_from(from_name='点击支援')
    @operation_node(name='点击头像', node_max_retry_times=10)
    def click_avatar(self) -> OperationRoundResult:
        """
        点击头像
        :return:
        """
        screen = self.screenshot()
        pos = self._get_character_pos(screen)

        if pos is None:
            self.no_find_character_times += 1
            if self.no_find_character_times >= 5:
                # 找不到支援角色 点击右边返回 按特殊状态返回成功
                self.round_by_click_area('挑战副本', '支援按钮')
                return self.round_fail(ChooseSupportInTeam.STATUS_SUPPORT_NOT_FOUND, wait=1.5)

            area = self.ctx.screen_loader.get_area('挑战副本', '支援角色列表')
            drag_from = area.center
            drag_to = drag_from + Point(0, -400)
            self.ctx.controller.drag_to(drag_to, drag_from)
            return self.round_retry(ChooseSupportInTeam.STATUS_SUPPORT_NOT_FOUND, wait=2)
        else:
            click = self.ctx.controller.click(pos.center)
            if click:
                return self.round_success(wait=0.5)
            else:
                return self.round_retry('点击头像失败', wait=0.5)

    @node_from(from_name='点击头像')
    @operation_node(name='点击入队')
    def click_join(self) -> OperationRoundResult:
        """
        点击入队
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '挑战副本', '支援入队按钮',
                                                 success_wait=1, retry_wait=1)

    def _get_character_pos(self, screen: Optional[MatLike] = None) -> Optional[MatchResult]:
        """
        找到角色头像的位置
        :return:
        """
        if screen is None:
            screen: MatLike = self.screenshot()

        area = self.ctx.screen_loader.get_area('挑战副本', '支援角色列表')
        part = cv2_utils.crop_image_only(screen, area.rect)

        # 先找到UID的位置
        ocr_result_map = self.ctx.ocr.match_words(part, words=['等级'], lcs_percent=0.1)
        if len(ocr_result_map) == 0:
            log.error('找不到等级')
            return None

        template = self.ctx.template_loader.get_template('character_avatar', self.character_id)
        if template is None:
            log.error('找不到角色头像模板 %s', self.character_id)
            return None

        for k, v in ocr_result_map.items():
            for pos in v:
                center = area.rect.left_top + pos.center
                avatar_rect = Rect(center.x - 42, center.y - 100, center.x + 55, center.y - 10)
                avatar_part = cv2_utils.crop_image_only(screen, avatar_rect)
                # cv2_utils.show_image(avatar_part, wait=0)
                source_kps, source_desc = cv2_utils.feature_detect_and_compute(avatar_part)
                template_kps, template_desc = template.features

                character_pos = cv2_utils.feature_match_for_one(
                    source_kps, source_desc,
                    template_kps, template_desc,
                    template.raw.shape[1], template.raw.shape[0],
                    knn_distance_percent=0.5
                )

                if character_pos is not None:
                    character_pos.x += avatar_rect.left_top.x
                    character_pos.y += avatar_rect.left_top.y
                    return character_pos

        return None

    @node_from(from_name='点击入队')
    @node_from(from_name='点击入队', success=False)
    @operation_node(name='选择后等待画面加载')
    def wait_at_last(self) -> OperationRoundResult:
        screen = self.screenshot()
        result = self.round_by_find_area(screen, '挑战副本', '队伍标题')
        if result.is_success:
            return self.round_success()
        else:
            return self.round_retry(result.status, wait=1)
