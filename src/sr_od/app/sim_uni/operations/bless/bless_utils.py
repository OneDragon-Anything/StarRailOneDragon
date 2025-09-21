from typing import Optional, List

from cv2.typing import MatLike

from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.utils import str_utils
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni.sim_uni_challenge_config import SimUniChallengeConfig
from sr_od.app.sim_uni.sim_uni_const import SimUniBless, SimUniBlessEnum, SimUniBlessLevel
from sr_od.context.sr_context import SrContext


def get_bless_pos(ctx: SrContext, screen: MatLike) -> list[MatchResult]:
    """
    获取屏幕上的祝福的位置
    :param ctx: 上下文
    :param screen: 游戏画面
    :return: MatchResult.data 中是对应的祝福 Bless
    """
    result_list: list[MatchResult] = []

    ocr_result_list = ctx.ocr_service.get_ocr_result_list(screen)

    bless_list: list[SimUniBless] = [i.value for i in SimUniBlessEnum if i.value.level != SimUniBlessLevel.WHOLE]
    bless_word_list: list[str] = [gt(i.title, 'game') for i in bless_list]

    for ocr_result in ocr_result_list:
        ocr_word: str = ocr_result.data
        bless_idx: int = str_utils.find_best_match_by_difflib(ocr_word, bless_word_list)
        if bless_idx is None or bless_idx < 0:
            continue

        result_list.append(
            MatchResult(
                c=ocr_result.confidence,
                x=ocr_result.x,
                y=ocr_result.y,
                w=ocr_result.w,
                h=ocr_result.h,
                data=bless_list[bless_idx]
            )
        )

    # 如果没找到选项, 直接找固定高度范围内的字, 直接点
    if len(result_list) == 0:
        rect = [100, 400, 1700, 900]
        for ocr_result in ocr_result_list:
            if ocr_result.rect.x1 > rect[0] and ocr_result.rect.y1 > rect[1] \
                    and ocr_result.rect.x2 < rect[2] and ocr_result.rect.y2 < rect[3]:
                result_list.append(
                    MatchResult(
                        c=ocr_result.confidence,
                        x=ocr_result.x,
                        y=ocr_result.y,
                        w=ocr_result.w,
                        h=ocr_result.h,
                        data=ocr_result.data
                    )
                )

    return result_list


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
                try:
                    if opt_bless.level == bless_level:
                        if idx_priority[idx] == 99:
                            idx_priority[idx] = cnt
                            cnt += 1
                except:
                    pass


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