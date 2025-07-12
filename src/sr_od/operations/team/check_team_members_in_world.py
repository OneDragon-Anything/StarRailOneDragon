from cv2.typing import MatLike
from typing import List, Optional

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils, str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.config.character_const import Character, CHARACTER_LIST
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state


class CheckTeamMembersInWorld(SrOperation):

    def __init__(self, ctx: SrContext, character_list: Optional[List[Character]] = None):
        """
        需要在大世界 右侧显示4名角色头像时使用
        获取组队角色
        :param ctx: 上下文
        """
        SrOperation.__init__(self, ctx, op_name=gt('组队角色判断'))

        self.character_list: List[Character] = [None, None, None, None] if character_list is None else character_list

    @operation_node(name='画面识别', node_max_retry_times=5, is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        screen = self.screenshot()

        if not common_screen_state.is_normal_in_world(self.ctx, screen):
            return self.round_retry('未在大世界画面', wait=1)

        self._check_by_name(screen)
        self._check_by_avatar(screen)

        self.ctx.team_info.update_character_list(self.character_list)
        log.info('当前配队 %s', [i.cn if i is not None else None for i in self.character_list])
        return self.round_success(data=self.character_list)

    def _check_by_name(self, screen: MatLike):
        """
        用名字匹配
        :param screen:
        :return:
        """
        for i in range(4):
            if self.character_list[i] is not None:
                continue
            area = self.ctx.screen_loader.get_area('大世界', ('队伍-角色名称-%d' % (i + 1)))

            part = cv2_utils.crop_image_only(screen, area.rect)

            character_name = self.ctx.ocr.run_ocr_single_line(part)
            best_character: Optional[Character] = None
            best_lcs: Optional[int] = None
            for character in CHARACTER_LIST:
                lcs = str_utils.longest_common_subsequence_length(gt(character.cn, 'ocr'), character_name)
                if lcs == 0:
                    continue
                if best_character is None or lcs > best_lcs:
                    best_character = character
                    best_lcs = lcs

            self.character_list[i] = best_character

    def _check_by_avatar(self, screen: MatLike):
        """
        用头像匹配
        :param screen:
        :return:
        """
        for i in range(4):
            if self.character_list[i] is not None:
                continue
            area = self.ctx.screen_loader.get_area('大世界', ('队伍-角色头像-%d' % (i + 1)))

            part = cv2_utils.crop_image_only(screen, area.rect)
            source_kps, source_desc = cv2_utils.feature_detect_and_compute(part)

            for character in CHARACTER_LIST:
                template = self.ctx.template_loader.get_template('character_avatar', character.id)

                if template is None:
                    log.error('%s 角色头像文件缺失', character.cn)
                    continue

                template_kps, template_desc = template.features
                mr = cv2_utils.feature_match_for_one(source_kps, source_desc,
                                                     template_kps, template_desc,
                                                     template.raw.shape[1], template.raw.shape[0])

                if mr is not None:
                    self.character_list[i] = character
                    break
