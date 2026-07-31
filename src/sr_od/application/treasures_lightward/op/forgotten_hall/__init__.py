import time
from typing import Optional, List

import cv2
import numpy as np
from cv2.typing import MatLike

from basic import Rect, Point, str_utils, cal_utils
from basic.img import MatchResult, cv2_utils, MatchResultList
from sr.context.context import Context

CHOOSE_MISSION_RECT = Rect(10, 261, 1900, 850)


def get_all_mission_num_pos(ctx: Context, screen: MatLike) -> dict[int, MatchResult]:
    """
    获取所有关卡数字对应的位置
    :param ctx: 上下文
    :param screen: 屏幕截图
    :return: 关卡数字对应的位置
    """
    part, _ = cv2_utils.crop_image(screen, CHOOSE_MISSION_RECT)

    lower_color = np.array([230, 230, 230], dtype=np.uint8)
    upper_color = np.array([255, 255, 255], dtype=np.uint8)
    white_part = cv2.inRange(part, lower_color, upper_color)
    # cv2_utils.show_image(white_part, win_name='white_part', wait=0)

    digit_rect_list: List[Rect] = []
    # 整张图片进行OCR容易出现匹配不到的情况 因为先切割再匹配
    contours, _ = cv2.findContours(white_part, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)  # 对于每个轮廓，计算外接矩形
        lt = Point(x, y) + CHOOSE_MISSION_RECT.left_top
        rb = Point(x + w, y + h) + CHOOSE_MISSION_RECT.left_top
        rect = Rect(lt.x - 5, lt.y - 5, rb.x + 5, rb.y + 5)
        # print(number_part.shape)
        if w > 40 or w < 5 or h < 25:  # 过滤过大或过小的矩阵
            continue
        # number_part, rect = cv2_utils.crop_image(screen, rect)
        # cv2_utils.show_image(number_part, win_name='number_part', wait=0)

        merged: bool = False  # 将较近距离的数字合并
        for another_rect in digit_rect_list:
            if cal_utils.distance_between(rect.center, another_rect.center) < 50:
                if rect.x1 < another_rect.x1:
                    another_rect.x1 = rect.x1
                if rect.y1 < another_rect.y1:
                    another_rect.y1 = rect.y1
                if rect.x2 > another_rect.x2:
                    another_rect.x2 = rect.x2
                if rect.y2 > another_rect.y2:
                    another_rect.y2 = rect.y2
                merged = True

        if not merged:
            digit_rect_list.append(rect)

    mission_num_pos: dict[int, MatchResult] = {}
    for rect in digit_rect_list:
        # 在矩阵中匹配数字
        number_part, rect = cv2_utils.crop_image(screen, rect)

        white_number_part = cv2.inRange(number_part, lower_color, upper_color)
        to_ocr = cv2.bitwise_and(number_part, number_part, mask=white_number_part)

        ocr_result = ctx.ocr.run_ocr_single_line(to_ocr)
        # cv2_utils.show_image(white_number_part, win_name='part', wait=0)
        digit_str = str_utils.remove_not_digit(ocr_result)
        if len(digit_str) != 2:  # 避免识别错误 只有两位数字的才认为是对的
            continue

        mission_num = str_utils.get_positive_digits(ocr_result, err=-1)
        if mission_num == -1:
            continue

        mission_num_pos[mission_num] = MatchResult(1, rect.x1, rect.y1, rect.x2 - rect.x1, rect.y2 - rect.y1)

    # 对于 10 以上的关卡 有可能只识别到单个数字 这时候要排除掉
    for i in range(3):  # 目前只可能出现 0 1 2
        if i not in mission_num_pos:
            continue
        pos1 = mission_num_pos[i].center

        for j in range(i + 1, 13):  # 对比其他更大的数字 其位置不应该在这些数字的右方
            if j not in mission_num_pos:
                continue
            pos2 = mission_num_pos[j].center

            if pos1.x > pos2.x:
                del mission_num_pos[i]
                break

    return mission_num_pos


def get_mission_num_pos(ctx: Context, target_mission_num: int, screen: MatLike,
                        drag_when_not_found: bool = False) -> Optional[MatchResult]:
    """
    获取关卡数字所在的位置
    :param ctx: 上下文
    :param target_mission_num: 关卡数字
    :param screen: 屏幕截图
    :param drag_when_not_found: 找不到后进行滑动
    :return: 数字位置
    """
    mission_num_pos = get_all_mission_num_pos(ctx, screen)

    if target_mission_num in mission_num_pos:
        return mission_num_pos[target_mission_num]
    else:
        if drag_when_not_found:  # 进行滑动
            existed_larger: bool = False  # 当前屏幕数字是否更大
            for existed_num in mission_num_pos.keys():
                if existed_num > target_mission_num:
                    existed_larger = True
                    break

            drag_from = CHOOSE_MISSION_RECT.center
            drag_to = drag_from + Point((800 if existed_larger else -800), 0)
            ctx.controller.drag_to(drag_to, drag_from, duration=0.3)
            time.sleep(0.5)
        return None


def get_mission_star(ctx: Context, mission_num: int, screen: MatLike) -> Optional[int]:
    """
    获取关卡数字所在的位置
    :param ctx: 上下文
    :param mission_num: 关卡数字
    :param screen: 屏幕截图
    :return: 星数 找不到关卡时为 None
    """
    num_pos: Optional[MatchResult] = get_mission_num_pos(ctx, mission_num, screen)

    if num_pos is None:
        return None
    else:
        return get_mission_star_by_num_pos(ctx, screen, num_pos)


def get_mission_star_by_num_pos(ctx: Context, screen: MatLike, num_pos: MatchResult) -> int:
    """
    获取数字下面星星的数量
    :param ctx: 上下文
    :param screen: 屏幕截图
    :param num_pos: 数字位置
    :return: 星数
    """
    num_center = num_pos.center

    star_rect = Rect(num_center.x - 70, num_center.y + 20, num_center.x + 90, num_center.y + 80)
    part, _ = cv2_utils.crop_image(screen, star_rect)

    lower_color = np.array([110, 200, 240], dtype=np.uint8)
    upper_color = np.array([120, 210, 255], dtype=np.uint8)
    # lower_color = np.array([140, 100, 115], dtype=np.uint8)  # 没激活的星星颜色
    # upper_color = np.array([150, 115, 130], dtype=np.uint8)
    white_part = cv2.inRange(part, lower_color, upper_color)

    template = ctx.ih.get_template('mission_star_active')
    template_result_list: MatchResultList = ctx.im.match_image(white_part, template.mask,
                                                               threshold=0.3,
                                                               only_best=False)
    # cv2_utils.show_image(part, template_result_list, wait=0)

    mini_distance = 15  # 星星间最短的距离
    star_pos_arr: List[MatchResult] = []
    for r in template_result_list:
        existed: bool = False  # 是否距离已有星星过近
        for star in star_pos_arr:
            if cal_utils.distance_between(r.center, star.center) < mini_distance:
                existed = True
                break

        if not existed:
            star_pos_arr.append(r)

    return len(star_pos_arr)
