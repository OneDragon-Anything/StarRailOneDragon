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


class ChooseSupport(SrOperation):

    STATUS_SUPPORT_NOT_FOUND: ClassVar[str] = '未找到支援角色'
    STATUS_SUPPORT_NEEDED: ClassVar[str] = '需要支援角色'

    def __init__(self, ctx: SrContext, character_id: Optional[str], skip_check_screen: bool = False):
        """
        在角色列表页 选择对应支援角色
        如果不传入支援角色 则直接返回成功
        :param ctx:
        :param character_id:
        """
        SrOperation.__init__(self, ctx, op_name=gt('选择支援'))

        self.character_id: str = character_id
        """需要选择的角色ID"""

        self.skip_check_screen: bool = skip_check_screen
        """跳过开始的识别画面 即默认已经打开了支援角色页面"""

        self.found_character: bool = False
        """是否找到支援角色"""

    @operation_node(name='识别画面', is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        """
        等待加载 左上角有【支援】
        :return:
        """
        if self.character_id is None:
            return self.round_success('无需支援')

        screen = self.screenshot()
        return self.round_by_find_area(screen, '队伍', '左上角标题-队伍', retry_wait=1)

    @node_from(from_name='识别画面', status='左上角标题-队伍')
    @operation_node(name='选择支援角色')
    def choose_support(self) -> OperationRoundResult:
        """
        点击头像
        :return:
        """
        screen = self.screenshot()
        round_result = ChooseSupport.click_avatar(self, screen, self.character_id)
        if round_result.is_success:
            self.found_character = True
        return round_result

    @node_from(from_name='选择支援角色')
    @operation_node(name='点击入队')
    def click_join(self) -> OperationRoundResult:
        """
        点击入队 点击后会返回上级画面
        :return:
        """
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '队伍', '按钮-入队',
                                                 success_wait=1, retry_wait=1)

    @node_from(from_name='识别画面', status='无需支援')
    @node_from(from_name='选择支援角色', success=False)
    @operation_node(name='返回')
    def back(self) -> OperationRoundResult:
        """
        返回
        :return:
        """
        self.round_by_click_area('队伍', '按钮-关闭')

        if self.character_id is None:
            return self.round_success('无需支援')
        elif self.found_character:
            return self.round_success(wait_round_time=1.5)
        else:
            return self.round_fail(ChooseSupport.STATUS_SUPPORT_NOT_FOUND, wait_round_time=1.5)

    @staticmethod
    def click_avatar(op: SrOperation, screen: MatLike, character_id: str) -> OperationRoundResult:
        """
        点击头像
        :return:
        """
        pos = ChooseSupport.get_character_pos(op, screen, character_id)

        if pos is None:
            area = op.ctx.screen_loader.get_area('队伍', '角色列表')
            drag_from = area.center
            drag_to = drag_from + Point(0, -400)
            op.ctx.controller.drag_to(drag_to, drag_from)
            return op.round_retry(ChooseSupport.STATUS_SUPPORT_NOT_FOUND, wait=2)
        else:
            click = op.ctx.controller.click(pos.center)
            if click:
                return op.round_success(wait=0.5)
            else:
                return op.round_retry('点击头像失败', wait=0.5)

    @staticmethod
    def get_character_pos(op: SrOperation, screen: MatLike, character_id: str) -> Optional[MatchResult]:
        """
        找到角色头像的位置
        :return:
        """
        area = op.ctx.screen_loader.get_area('队伍', '角色列表')
        part = cv2_utils.crop_image_only(screen, area.rect)

        # 先找到UID的位置
        ocr_result_map = op.ctx.ocr.match_words(part, words=['等级'], lcs_percent=0.1)
        if len(ocr_result_map) == 0:
            log.error('找不到等级')
            return None

        template = op.ctx.template_loader.get_template('character_avatar', character_id)
        if template is None:
            log.error('找不到角色头像模板 %s', character_id)
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