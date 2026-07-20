import time

import cv2
from typing import Tuple, Optional

from one_dragon.base.geometry.point import Point
from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.utils import cal_utils
from one_dragon.utils.log_utils import log
from sr_od.application.world_patrol.world_patrol_route import WorldPatrolRoute, WorldPatrolRouteOperation
from sr_od.config import operation_const
from sr_od.context.sr_context import SrContext
from sr_od.operations.move import cal_pos_utils
from sr_od.operations.move.cal_pos_utils import VerifyPosInfo
from sr_od.sr_map import mini_map_utils, large_map_utils
from sr_od.sr_map.sr_map_def import Region


def can_change_tp(route: WorldPatrolRoute) -> bool:
    """
    当前是否允许修改传送点
    :param route:
    :return:
    """
    return route is None or route.empty_op


def get_last_pos(ctx: SrContext, route: WorldPatrolRoute) -> Tuple[Region, Point]:
    """
    获取路线的最后一个点
    :param ctx: 上下文
    :param route: 路线
    :return:
    """
    region = route.tp.region
    pos = route.tp.tp_pos
    if route.route_list is None or len(route.route_list) == 0:
        return region, pos
    for op in route.route_list:
        if op.op in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE, operation_const.OP_UPDATE_POS]:
            pos = Point(op.data[0], op.data[1])
            if len(op.data) > 2:
                region = ctx.map_data.region_with_another_floor(region, op.data[2])
        elif op.op == operation_const.OP_ENTER_SUB:
            region = ctx.map_data.get_sub_region_by_cn(region, op.data[0], int(op.data[1]))
            pos = None

    return region, pos


def cal_pos_by_screenshot(ctx: SrContext, route: WorldPatrolRoute, debug: bool = False) -> Tuple[Optional[Region], Optional[Point]]:
    region, last_pos = get_last_pos(ctx, route)
    log.info(f'使用上一个坐标 %s', last_pos)
    lm_info = ctx.map_data.get_large_map_info(region)
    next_region = region

    if not ctx.controller.game_win.is_win_active:
        ctx.controller.active_window()
        time.sleep(1)
    screen = ctx.controller.screenshot(True)
    mm = mini_map_utils.cut_mini_map(screen, ctx.game_config.mini_map_pos)
    mm_info = mini_map_utils.analyse_mini_map(mm)

    next_pos: Optional[MatchResult] = None

    for move_time in range(1, 10):
        move_distance = ctx.controller.cal_move_distance_by_time(move_time)
        possible_pos = (last_pos.x, last_pos.y, move_distance)
        lm_rect = large_map_utils.get_large_map_rect_by_pos(lm_info.gray.shape, mm.shape[:2], possible_pos)

        verify = VerifyPosInfo(last_pos=last_pos, max_distance=move_distance)

        next_pos = cal_pos_utils.cal_character_pos(
            ctx, lm_info, mm_info,
            lm_rect=lm_rect, retry_without_rect=False,
            running=True,
            real_move_time=move_time,
            verify=verify,
            show=debug
        )

        # 暂时不计算其他楼层 会乱飞
        # if next_pos is None and region.floor != 0:
        #     region_list = ctx.map_data.get_region_with_all_floor(region)
        #     for another_floor_region in region_list:
        #         if another_floor_region.floor == region.floor:
        #             continue
        #
        #         next_lm_info = ctx.map_data.get_large_map_info(another_floor_region)
        #         next_pos = cal_pos_utils.cal_character_pos(
        #             ctx, next_lm_info, mm_info,
        #             lm_rect=lm_rect, retry_without_rect=False,
        #             running=True,
        #             real_move_time=move_time,
        #             verify=verify,
        #             show=debug
        #         )
        #
        #         if next_pos is not None:
        #             next_region = another_floor_region
        #             break

        if next_pos is not None:
            break

    if next_pos is not None:
        return next_region, next_pos.center
    else:
        return None, None


def get_route_image(ctx: SrContext, route: WorldPatrolRoute):
    """
    获取路线的图片
    :param ctx: 上下文
    :param route: 路线 在传送点还没有选的时候 可能为空
    :return:
    """
    to_display_region, _ = get_last_pos(ctx, route)
    current_region = route.tp.region

    display_image = ctx.map_data.get_large_map_info(to_display_region).raw.copy()

    last_point = None
    if route.tp is not None:
        last_point = route.tp.tp_pos.tuple()
        if current_region.pr_id == to_display_region.pr_id:  # 只画出最后一个区域的地图
            cv2.circle(display_image, route.tp.lm_pos.tuple(), 15, color=(100, 255, 100), thickness=2)
            cv2.circle(display_image, route.tp.tp_pos.tuple(), 5, color=(0, 255, 0), thickness=2)
    for route_item in route.route_list:
        if route_item.op in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE, operation_const.OP_NO_POS_MOVE]:
            if route_item.op == operation_const.OP_NO_POS_MOVE:
                pos = [route_item.data[0] + last_point[0], route_item.data[1] + last_point[1]]
            else:
                pos = route_item.data
            if current_region.pr_id == to_display_region.pr_id:
                cv2.circle(display_image, pos[:2], 5, color=(0, 0, 255), thickness=-1)
                if last_point is not None:
                    cv2.line(display_image, last_point[:2], pos[:2],
                             color=(255, 0, 0) if route_item.op == operation_const.OP_MOVE else (255, 255, 0),
                             thickness=2)
                cv2.putText(display_image, str(route_item.idx), (pos[0] - 5, pos[1] - 13),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1, cv2.LINE_AA)
            last_point = pos
        elif route_item.op == operation_const.OP_PATROL:
            if current_region.pr_id == to_display_region.pr_id:
                if last_point is not None:
                    cv2.circle(display_image, last_point[:2], 10, color=(0, 255, 255), thickness=2)
        elif route_item.op == operation_const.OP_DISPOSABLE:
            if current_region.pr_id == to_display_region.pr_id:
                if last_point is not None:
                    cv2.circle(display_image, last_point[:2], 10, color=(67, 34, 49), thickness=2)
        elif route_item.op in [operation_const.OP_INTERACT, operation_const.OP_CATAPULT, operation_const.OP_GAMEPLAY_INTERACT]:
            if current_region.pr_id == to_display_region.pr_id:
                if last_point is not None:
                    cv2.circle(display_image, last_point[:2], 12, color=(255, 0, 255), thickness=2)
        elif route_item.op == operation_const.OP_WAIT:
            if current_region.pr_id == to_display_region.pr_id:
                if last_point is not None:
                    cv2.circle(display_image, last_point[:2], 14, color=(255, 255, 255), thickness=2)
        elif route_item.op == operation_const.OP_UPDATE_POS:
            pos = route_item.data
            if current_region.pr_id == to_display_region.pr_id:
                cv2.circle(display_image, pos[:2], 5, color=(0, 0, 255), thickness=-1)
                cv2.putText(display_image, str(route_item.idx), (pos[0] - 5, pos[1] - 13),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1, cv2.LINE_AA)
            last_point = pos
            if len(pos) > 2:
                current_region = ctx.map_data.region_with_another_floor(current_region, int(pos[2]))
        elif route_item.op == operation_const.OP_ENTER_SUB:
            current_region = ctx.map_data.get_sub_region_by_cn(cn=route_item.data[0], region=current_region, floor=int(route_item.data[1]))
        elif route_item.op in [operation_const.OP_BAN_TECH, operation_const.OP_ALLOW_TECH]:
            pass

    return display_image


def add_move(ctx: SrContext, route: WorldPatrolRoute, x: int, y: int, floor: int):
    """
    在最后添加一个移动的指令
    :param x: 横坐标
    :param y: 纵坐标
    :param floor: 楼层
    :return:
    """
    last_region, last_pos = get_last_pos(ctx, route)

    if last_region.floor == floor:
        to_add = WorldPatrolRouteOperation(op=operation_const.OP_MOVE, data=(x, y))
    else:
        to_add = WorldPatrolRouteOperation(op=operation_const.OP_MOVE, data=(x, y, floor))

    route.route_list.append(to_add)
    route.init_idx()


def pop_last(route: WorldPatrolRoute):
    """
    取消最后一个指令
    :return:
    """
    if len(route.route_list) > 0:
        route.route_list.pop()


def mark_last_move_as_slow(route: WorldPatrolRoute):
    """
    将最后一个移动标记成慢走 或从慢走标记成可疾跑
    :return:
    """
    if route.empty_op:
        return

    last_op = route.route_list[len(route.route_list) - 1]
    if last_op.op not in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE]:
        return

    if last_op.op == operation_const.OP_MOVE:
        last_op.op = operation_const.OP_SLOW_MOVE
    else:
        last_op.op = operation_const.OP_MOVE


def mark_last_move_as_no_pos(ctx: SrContext, route: WorldPatrolRoute) -> None:
    """
    将最后一个移动标记成模拟按键移动
    """
    if route.empty_op:
        return

    last_op = route.route_list[-1]
    if last_op.op not in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE]:
        return

    last_op = route.route_list.pop()
    _, last_pos = get_last_pos(ctx, route)
    if last_pos is None:
        route.route_list.append(last_op)
        return

    x = last_op.data[0] - last_pos.x
    y = last_op.data[1] - last_pos.y
    move_time = cal_utils.distance_between(Point(0, 0), Point(x, y)) // ctx.controller.walk_speed
    new_op = WorldPatrolRouteOperation(op=operation_const.OP_NO_POS_MOVE, data=[x, y, move_time])
    route.route_list.append(new_op)

    route.route_list.append(last_op)
    mark_last_move_as_update(route)
    route.init_idx()

def mark_last_move_as_update(route: WorldPatrolRoute):
    """
    将最后一个指令变更为更新位置
    :return:
    """
    if route.empty_op:
        return

    idx = len(route.route_list) - 1
    if route.route_list[idx].op in [operation_const.OP_MOVE, operation_const.OP_SLOW_MOVE]:
        route.route_list[idx].op = operation_const.OP_UPDATE_POS


def add_patrol(route: WorldPatrolRoute):
    """
    增加攻击指令
    :return:
    """
    to_add = WorldPatrolRouteOperation(op=operation_const.OP_PATROL)
    route.route_list.append(to_add)
    route.init_idx()

def add_disposable(route: WorldPatrolRoute):
    """
    增加攻击可破坏物指令
    :return:
    """
    to_add = WorldPatrolRouteOperation(op=operation_const.OP_DISPOSABLE)
    route.route_list.append(to_add)
    route.init_idx()


def add_interact(route: WorldPatrolRoute, interact_text: str):
    """
    增加交互指令
    :param interact_text: 交互文本
    :return:
    """
    to_add = WorldPatrolRouteOperation(op=operation_const.OP_INTERACT, data=interact_text)
    route.route_list.append(to_add)
    route.init_idx()

def add_wait(route: WorldPatrolRoute, wait_type: str, wait_timeout: int):
    """
    增加等待指令
    :return:
    """
    to_add = WorldPatrolRouteOperation(op=operation_const.OP_WAIT, data=[wait_type, wait_timeout])
    route.route_list.append(to_add)
    route.init_idx()


def add_sub_region(route: WorldPatrolRoute, region: Region):
    """
    增加切换子区域的指令
    :param route: 路线
    :param region: 子区域
    :return:
    """
    route.route_list.append(WorldPatrolRouteOperation(op=operation_const.OP_ENTER_SUB, data=[region.cn, str(region.floor)]))


def add_ban_tech(route: WorldPatrolRoute):
    """
    增加禁止使用技能指令
    :return:
    """
    to_add = WorldPatrolRouteOperation(op=operation_const.OP_BAN_TECH)
    route.route_list.append(to_add)
    route.init_idx()


def add_allow_tech(route: WorldPatrolRoute):
    """
    增加允许使用技能指令
    :return:
    """
    to_add = WorldPatrolRouteOperation(op=operation_const.OP_ALLOW_TECH)
    route.route_list.append(to_add)
    route.init_idx()


def add_gameplay_interact(route: WorldPatrolRoute, seconds: int):
    """
    增加玩法交互指令
    :param seconds: 持续秒数
    :return:
    """
    to_add = WorldPatrolRouteOperation(op=operation_const.OP_GAMEPLAY_INTERACT, data=[seconds])
    route.route_list.append(to_add)
    route.init_idx()


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    tp = ctx.map_data.best_match_sp_by_all_name('空间站「黑塔」', '主控舱段', '监察域', 0)
    chosen_route = ctx.world_patrol_route_data.create_new_route(tp, '')
    cal_pos_by_screenshot(ctx, chosen_route, debug=True)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    __debug()
