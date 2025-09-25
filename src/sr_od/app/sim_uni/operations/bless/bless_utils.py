from typing import List, Optional

from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.utils import str_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.app.sim_uni.sim_uni_challenge_config import SimUniChallengeConfig
from sr_od.app.sim_uni.sim_uni_const import (
    SimUniBless,
    SimUniBlessEnum,
    SimUniBlessLevel,
    SimUniPath,
)
from sr_od.context.sr_context import SrContext


class SimUniBlessPos:

    def __init__(self, bless: SimUniBless, rect: Rect):
        self.bless: SimUniBless = bless
        self.rect: Rect = rect
        self.find_path: bool = False  # 是否匹配到命途


def get_bless_pos(ctx: SrContext, screen: MatLike) -> list[SimUniBlessPos]:
    """
    识别画面上的祝福位置

    Args:
        ctx: 上下文
        screen: 游戏画面

    Returns:
        list[SimUniBlessPos]: 识别到的祝福列表
    """
    result_list: list[SimUniBlessPos] = []

    ocr_result_list = ctx.ocr_service.get_ocr_result_list(screen)
    merged_ocr_result_list = merge_ocr_result(ocr_result_list)

    bless_list: list[SimUniBless] = [i.value for i in SimUniBlessEnum if i.value.level != SimUniBlessLevel.WHOLE]
    bless_word_list: list[str] = [gt(i.title, 'game') for i in bless_list]

    # 找到祝福名称
    for ocr_result in merged_ocr_result_list:
        ocr_word: str = ocr_result.data
        bless_idx: int = str_utils.find_best_match_by_difflib(ocr_word, bless_word_list)
        if bless_idx is None or bless_idx < 0:
            continue

        pos = SimUniBlessPos(
            bless=bless_list[bless_idx],
            rect=Rect(
                ocr_result.rect.x1,
                ocr_result.rect.y1,
                ocr_result.rect.x2,
                ocr_result.rect.y2
            )
        )
        result_list.append(pos)

    # 正下方需要有命途名称
    path_list: list[str] = [i.value for i in SimUniPath]
    path_word_list: list[str] = [gt(i, 'game') for i in path_list]
    for ocr_result in merged_ocr_result_list:
        ocr_word: str = ocr_result.data
        path_idx: int = str_utils.find_best_match_by_difflib(ocr_word, path_word_list)
        if path_idx is None or path_idx < 0:
            continue

        path_rect: Rect = ocr_result.rect

        # 找到横坐标最接近的祝福
        target_bless_idx: int = -1
        target_dis_x: int = 9999
        for bless_idx, bless_pos in enumerate(result_list):
            if bless_pos.bless.path.value != path_list[path_idx]:  # 命途匹配不上的
                continue
            if bless_pos.rect.y2 >= path_rect.y1:  # 命途要在祝福正下方
                continue
            if path_rect.center.x > bless_pos.rect.x2 or path_rect.center.x < bless_pos.rect.x1:  # 命途要在祝福正下方
                continue

            current_dis = abs(bless_pos.rect.center.x - path_rect.center.x)
            if target_bless_idx == -1 or current_dis < target_dis_x:
                target_bless_idx = bless_idx
                target_dis_x = current_dis

        if target_bless_idx == -1:
            continue

        result_list[target_bless_idx].find_path = True

    result_list = [i for i in result_list if i.find_path]
    log.info('识别到祝福 %s', [i.bless.title for i in result_list])

    return result_list


def merge_ocr_result(ocr_result_list: list[MatchResult]) -> list[MatchResult]:
    """
    对OCR结果进行合并

    部分祝福中间空格过大 OCR识别会拆分成两部分 这里手动进行合并

    Args:
        ocr_result_list: 原OCR结果

    Returns:
        list[MatchResult]: 合并后的OCR结果
    """
    merged_ocr_result_list: list[MatchResult] = []

    left_word_list: list[str] = [
        gt(i, 'game')
        for i in [
            '命途回响：'
        ]
    ]

    for left in ocr_result_list:
        if left.data is None:  # 被合并了
            continue
        left_word_idx = str_utils.find_best_match_by_difflib(left.data, left_word_list)
        if left_word_idx is None or left_word_idx < 0:  # 需要命中特殊的词
            continue
        for right in ocr_result_list:
            if left == right:
                continue

            if right.data is None:  # 被合并了
                continue

            if abs(left.center.y - right.center.y) > min(left.rect.height, right.rect.height) * 0.3: # 不在同一行
                continue

            if not (abs(right.rect.x1 - left.rect.x2) < max(left.rect.width, right.rect.width) * 0.3): # 不是左右相邻
                continue

            left.data = left.data + right.data
            left.x = min(left.x, right.x)
            left.y = min(left.y, right.y)
            left.w = max(left.x, right.x) - left.x
            left.h = max(left.y, right.y) - left.y

            right.data = None

    merged_ocr_result_list = [i for i in ocr_result_list if i.data is not None]
    return merged_ocr_result_list


def get_bless_by_priority(bless_list: List[SimUniBless], config: Optional[SimUniChallengeConfig], can_reset: bool,
                          asc: bool) -> Optional[int]:
    """
    根据优先级选择对应的祝福
    :param bless_list: 可选的祝福列表
    :param config: 挑战配置
    :param can_reset: 当前是否可以重置
    :param asc: 升序取第一个 最高优先级
    :return: 选择祝福的下标
    """
    idx_priority: List[int] = [99 for _ in bless_list]
    cnt = 0  # 优先级

    if config is not None:
        for priority_id in config.bless_priority:
            bless = SimUniBlessEnum[priority_id]
            if bless.name.endswith('000'):  # 命途内选最高级的祝福
                for bless_level in SimUniBlessLevel:
                    for idx, opt_bless in enumerate(bless_list):
                        if opt_bless.level == bless_level and opt_bless.path == bless.value.path:
                            if idx_priority[idx] == 99:
                                idx_priority[idx] = cnt
                                cnt += 1
            else:  # 命中优先级的
                for idx, opt_bless in enumerate(bless_list):
                    if opt_bless == bless.value:
                        if idx_priority[idx] == 99:
                            idx_priority[idx] = cnt
                            cnt += 1

        if not can_reset:
            for priority_id in config.bless_priority_2:
                bless = SimUniBlessEnum[priority_id]
                if bless.name.endswith('000'):  # 命途内选最高级的祝福
                    for bless_level in SimUniBlessLevel:
                        for idx, opt_bless in enumerate(bless_list):
                            if opt_bless.level == bless_level and opt_bless.path == bless.value.path:
                                if idx_priority[idx] == 99:
                                    idx_priority[idx] = cnt
                                    cnt += 1
                else:  # 命中优先级的
                    for idx, opt_bless in enumerate(bless_list):
                        if opt_bless == bless.value:
                            if idx_priority[idx] == 99:
                                idx_priority[idx] = cnt
                                cnt += 1

    if not can_reset:
        # 优先级无法命中的情况 随便选最高级的祝福
        for bless_level in SimUniBlessLevel:
            for idx, opt_bless in enumerate(bless_list):
                if opt_bless.level == bless_level:
                    if idx_priority[idx] == 99:
                        idx_priority[idx] = cnt
                        cnt += 1

    target_idx: Optional[int] = None
    target_priority: Optional[int] = None

    for idx in range(len(bless_list)):
        if can_reset and idx_priority[idx] == 99:
            continue
        if target_idx is None or \
                (asc and target_priority > idx_priority[idx]) or \
                (not asc and target_priority < idx_priority[idx]):
            target_idx = idx
            target_priority = idx_priority[idx]

    return target_idx