from typing import Optional

from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.matcher.match_result import MatchResult, MatchResultList
from one_dragon.utils import cv2_utils
from sr_od.context.sr_context import SrContext
from sr_od.operations.menu.phone_menu_const import PhoneMenuItem

MENU_ITEMS_PART = Rect(1270, 300, 1810, 1070)  # 菜单选项
MENU_ITEMS_AT_RIGHT_PART = Rect(1810, 230, 1915, 1030)  # 菜单侧栏选项

SUPPORT_CHARACTER_PART = Rect(940, 140, 1700, 520)  # 支援角色的框

NAMELESS_HONOR_TAB_PART = Rect(810, 30, 1110, 100)  # 无名勋礼上方的tab

GUIDE_TRAINING_TASK_RECT = Rect(290, 470, 1560, 680)  # 指南-实训 任务框
GUIDE_TRAINING_REWARD_CLAIM_RECT = Rect(420, 270, 1670, 370)  # 指南-实训 奖励领取框


def get_phone_menu_item_pos(ctx: SrContext, screen: MatLike, item: PhoneMenuItem, alert: bool = False) -> Optional[MatchResult]:
    """
    获取菜单中某个具体选项的位置
    :param ctx: 上下文
    :param screen: 屏幕截图
    :param item:
    :param alert: 是否有感叹号红点
    :return:
    """
    part, _ = cv2_utils.crop_image(screen, MENU_ITEMS_PART)
    result_list: MatchResultList = ctx.tm.match_template(part, 'phone_menu', item.template_id, only_best=True)
    result: MatchResult = result_list.max

    if result is None:
        return None

    result.x += MENU_ITEMS_PART.x1
    result.y += MENU_ITEMS_PART.y1

    if alert:
        if is_item_with_alert(ctx, screen, result, (50, -50)):
            return result
        else:
            return None
    else:
        return result


def get_phone_menu_item_pos_at_right(ctx: SrContext, screen: MatLike, item: PhoneMenuItem, alert: bool = False) -> Optional[MatchResult]:
    """
    获取菜单侧栏中某个具体选项的位置
    :param ctx: 上下文
    :param screen: 屏幕截图
    :param item:
    :param alert: 是否有感叹号红点
    :return:
    """
    part, _ = cv2_utils.crop_image(screen, MENU_ITEMS_AT_RIGHT_PART)
    result_list: MatchResultList = ctx.tm.match_template(part, 'phone_menu', item.template_id, only_best=True)
    result: MatchResult = result_list.max

    if result is None:
        return None

    result.x += MENU_ITEMS_AT_RIGHT_PART.x1
    result.y += MENU_ITEMS_AT_RIGHT_PART.y1

    if alert:
        if is_item_with_alert(ctx, screen, result, (50, -50)):
            return result
        else:
            return None
    else:
        return result


def get_phone_menu_ellipsis_pos(ctx: SrContext, screen: MatLike, alert: bool = False):
    """
    获取菜单上方省略号的位置
    :param ctx: 上下文
    :param screen: 屏幕截图
    :param alert: 是否有感叹号红点
    :return:
    """
    area = ctx.screen_loader.get_area('菜单', '更多按钮')
    part = cv2_utils.crop_image_only(screen, area.rect)
    # cv2_utils.show_image(part, win_name='ELLIPSIS_PART')
    result_list: MatchResultList = ctx.tm.match_template(part, 'phone_menu', 'ui_ellipsis', only_best=True, threshold=0.3)
    result: MatchResult = result_list.max

    if result is None:
        return None

    result.x += area.rect.x1
    result.y += area.rect.y1

    if alert:
        if is_item_with_alert(ctx, screen, result, (50, -50)):
            return result
        else:
            return None
    else:
        return result


def get_phone_menu_ellipsis_item_pos(ctx: SrContext, screen: MatLike, item_cn: str, alert: bool = False):
    """
    获取菜单上方省略号弹出的选项位置
    :param ctx: 上下文
    :param screen: 屏幕截图
    :param item_cn: 需要选择的选项中文
    :param alert: 是否有感叹号红点
    :return:
    """
    area = ctx.screen_loader.get_area('菜单', '更多按钮')
    part = cv2_utils.crop_image_only(screen, area.rect)

    ocr_map = ctx.ocr.match_words(part, words=[item_cn], lcs_percent=0.55)
    if len(ocr_map) == 0:
        return None

    result: MatchResult = ocr_map.popitem()[1].max

    result.x += area.rect.x1
    result.y += area.rect.y1

    if alert:
        if is_item_with_alert(ctx, screen, result, (130, -50)):
            return result
        else:
            return None
    else:
        return result


def is_item_with_alert(ctx: SrContext, screen: MatLike, item_result: MatchResult, offset: tuple) -> bool:
    """
    图标右上角是否有感叹号
    :param ctx: 上下文
    :param screen: 屏幕截图
    :param item_result: 图标匹配结果
    :param offset: 感叹号在图标右上角的偏移量 x应该为正数 y应该为负数
    :return:
    """
    x1, y1 = item_result.x, item_result.y + offset[1]
    x2, y2 = item_result.x + item_result.w + offset[0], item_result.y + item_result.h
    alert_result: MatchResultList = get_alert_pos(ctx, screen, Rect(x1, y1, x2, y2))
    return alert_result.max is not None


def get_alert_pos(ctx: SrContext, screen: MatLike, rect: Rect) -> MatchResultList:
    """
    获取省略号的位置
    :param ctx: 上下文
    :param screen: 屏幕截图
    :param rect: 屏幕的特定范围
    :return: 省略号的位置
    """
    part, _ = cv2_utils.crop_image(screen, rect)
    # cv2_utils.show_image(part, win_name='get_alert_pos')
    return ctx.tm.match_template(part, 'phone_menu', 'ui_alert', threshold=0.7)


def get_nameless_honor_tab_pos(ctx: SrContext, screen: MatLike, tab: int, alert: bool = False) -> Optional[MatchResult]:  # TODO 下个版本再测试红点
    """
    获取 无名勋礼 页面上方 tab图标 的位置
    :param ctx: 上下文
    :param screen: 屏幕截图
    :param tab: 第几个tab
    :param alert: 是否有感叹号红点
    :return: tab的位置
    """
    part, _ = cv2_utils.crop_image(screen, NAMELESS_HONOR_TAB_PART)
    result_list = ctx.tm.match_template(part, 'phone_menu', 'nameless_honor_%d' % tab, only_best=True)

    result: MatchResult = result_list.max

    if result is None:
        return None

    result.x += NAMELESS_HONOR_TAB_PART.x1
    result.y += NAMELESS_HONOR_TAB_PART.y1

    if alert:
        if is_item_with_alert(ctx, screen, result, (50, -50)):
            return result
        else:
            return None
    else:
        return result


def get_training_reward_claim_btn_pos(ctx: SrContext, screen: MatLike) -> Optional[MatchResult]:
    """
    指南实训页面 获取奖励领取按钮的位置 多个时返回最右边的一个
    :param ctx: 上下文
    :param screen:
    :return:
    """
    part, _ = cv2_utils.crop_image(screen, GUIDE_TRAINING_REWARD_CLAIM_RECT)

    result_list: MatchResultList = ctx.tm.match_template(part, 'phone_menu', 'training_reward_gift', ignore_template_mask=True)

    if len(result_list) == 0:
        return None

    result: Optional[MatchResult] = None
    for i in result_list:
        if result is None or i.x > result.x:
            result = i

    result.x += GUIDE_TRAINING_REWARD_CLAIM_RECT.x1
    result.y += GUIDE_TRAINING_REWARD_CLAIM_RECT.y1

    return result


def is_training_reward_completed(ctx: SrContext, screen: MatLike) -> bool:
    """
    指南实训页面 获取领完的奖励个数
    :param ctx: 上下文
    :param screen:
    :return:
    """
    part, _ = cv2_utils.crop_image(screen, GUIDE_TRAINING_REWARD_CLAIM_RECT)

    result_list: MatchResultList = ctx.tm.match_template(part, 'phone_menu', 'training_reward_completed', only_best=False, ignore_template_mask=True)

    return len(result_list) >= 5
