import os
import time
from typing import List, Optional

import numpy as np
import pyautogui
from cv2.typing import MatLike

from one_dragon.base.config.yaml_operator import YamlOperator
from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils, os_utils
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.app.large_map_recorder import large_map_recorder_utils
from sr_od.app.sim_uni.sim_uni_const import SimUniLevelTypeEnum
from sr_od.app.sr_application import SrApplication
from sr_od.config import game_const, operation_const
from sr_od.context.sr_context import SrContext
from sr_od.sr_map import large_map_utils
from sr_od.sr_map.operations.choose_floor import ChooseFloor
from sr_od.sr_map.operations.choose_planet import ChoosePlanet
from sr_od.sr_map.operations.choose_region import ChooseRegion
from sr_od.sr_map.operations.open_map import OpenMap
from sr_od.sr_map.sr_map_def import Region

_FLOOR_LIST = [-4, -3, -2, -1, 0, 1, 2, 3, 4]


DRAG_NEXT_START = Point(1350, 300)  # 大地图右方的空白区域 防止点击到地图的点 导致拖拽有问题


class RegionRecorderCheckPoint(YamlOperator):

    def __init__(
            self,
            region: Region,
    ):
        YamlOperator.__init__(self, _get_checkpoint_path(region))

    @property
    def max_row(self) -> int:
        return self.data.get('max_row')

    @max_row.setter
    def max_row(self, new_value: int) -> None:
        self.update('max_row', new_value)

    @property
    def max_column(self) -> int:
        return self.data.get('max_column')

    @max_column.setter
    def max_column(self, new_value: int) -> None:
        self.update('max_column', new_value)

def _get_checkpoint_path(region: Region) -> str:
    """
    获取检查点文件位置

    Args:
        region: 区域

    Returns:
        检查点文件位置
    """
    return os.path.join(
        os_utils.get_path_under_work_dir('.debug', 'world_patrol', region.pr_id, 'recorder_checkpoint'),
        f'{region.prl_id}.yml'
    )


class LargeMapRecorder(SrApplication):
    """
    开发用的截图工具 只支持PC版

    把整个大地图记录下来
    """

    def __init__(
            self,
            ctx: SrContext,
            region: Region,
            drag_distance_to_next_col: int = 300,
            drag_distance_to_next_row: int = 300,
            floor_list_to_record: Optional[List[int]] = None,
            row_list_to_record: Optional[List[int]] = None,
            col_list_to_record: Optional[List[int]] = None,
            fix_width_rows: list[int] = None,
            debug: bool = False,
    ):
        SrApplication.__init__(self, ctx, 'large_map_recorder', op_name='大地图录制 %s' % region.cn)

        self.ck: RegionRecorderCheckPoint = RegionRecorderCheckPoint(region)

        self.debug: bool = debug  # 调试模式 会显示很多图片

        self.region: Region = region
        self.row: int = 1  # 下标从1开始
        self.col: int = 1

        self.drag_distance_to_next_col: int = drag_distance_to_next_col
        self.drag_distance_to_next_row: int = drag_distance_to_next_row

        self.row_list_to_record: Optional[List[int]] = row_list_to_record  # 需要重新录制的行数
        self.col_list_to_record: Optional[List[int]] = col_list_to_record  # 需要重新录制的列数
        self.floor_list_to_record: Optional[List[int]] = floor_list_to_record  # 需要重新录制的楼层

        self.region_list: List[Region] = []
        for floor in _FLOOR_LIST:
            if self.floor_list_to_record is not None and floor not in self.floor_list_to_record:
                continue
            current_region = self.ctx.map_data.best_match_region_by_name(
                gt(self.region.cn, 'game'),
                planet=self.region.planet,
                target_floor=floor
            )
            if current_region is None:
                continue
            if current_region.pr_id != self.region.pr_id:
                continue
            self.region_list.append(current_region)

        self.current_region_idx: int = 0
        self.current_region: Optional[Region] = None

        self.fix_width_rows: list[int] = fix_width_rows  # 固定使用重叠众数宽度的行

    @operation_node(name='打开地图', is_start_node=True)
    def open_map(self) -> OperationRoundResult:
        op = OpenMap(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='打开地图')
    @operation_node(name='选择星球')
    def choose_planet(self) -> OperationRoundResult:
        op = ChoosePlanet(self.ctx, self.region.planet)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择星球')
    @operation_node(name='选择区域')
    def choose_region(self) -> OperationRoundResult:
        op = ChooseRegion(self.ctx, self.region)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择区域')
    @operation_node(name='识别最大行列数')
    def detect_max_row_col(self) -> OperationRoundResult:
        if self.ck.max_column is None:
            self.back_to_left_top()
            self.drag_to_get_max_column()


        if self.ck.max_row is None:
            self.back_to_left_top()
            self.drag_to_get_max_row()

        return self.round_success()

    @node_from(from_name='识别最大行列数')
    @operation_node(name='截图')
    def do_screenshot(self) -> OperationRoundResult:
        if self.current_region_idx >= len(self.region_list):
            return self.round_success()

        self.current_region = self.region_list[self.current_region_idx]

        op = ChooseFloor(self.ctx, self.current_region.floor)
        op_result = op.execute()
        if not op_result.success:
            return self.round_fail('选择区域失败')

        self._screenshot_whole_floor()
        if self.row_list_to_record is not None:
            while True:
                img = large_map_recorder_utils.get_part_image(self.current_region, self.row, 0)
                if img is None:
                    break
                else:
                    self.row += 1
            while True:
                img = large_map_recorder_utils.get_part_image(self.current_region, 0, self.col)
                if img is None:
                    break
                else:
                    self.col += 1

        self.current_region_idx += 1
        return self.round_wait()

    def _screenshot_whole_floor(self):
        """
        对整个楼层进行截图
        先拉到最左上角 然后一行一行地截图 最后再拼接起来。
        :return:
        """
        self.back_to_left_top()
        while True:
            if not self.ctx.is_context_running:
                return False
            if self.row_list_to_record is not None and self.row > np.max(self.row_list_to_record):
                break
            if self.row_list_to_record is not None and self.row not in self.row_list_to_record:
                self.drag_to_next_row()
                continue

            self._screenshot_one_row()  # 对一行进行水平的截图

            to_next_row: bool = False
            if self.row < self.ck.max_row:
                to_next_row = True

            if to_next_row:
                self.drag_to_next_row()
                self.back_to_left()
            else:
                break

    def _screenshot_one_row(self):
        """
        对一行进行截图
        水平滚动地截取地图部分 并落盘保存
        :return: 拼接好的图片
        """
        img = []
        # 每秒往右拉一段距离截图
        while True:
            if not self.ctx.is_context_running:
                return
            log.info('当前截图 %02d行 %02d列' % (self.row, self.col))
            screen = self.screenshot()
            screen_map_rect = large_map_utils.get_screen_map_rect(self.region)
            map_part = cv2_utils.crop_image_only(screen, screen_map_rect)
            if self.col_list_to_record is None or self.col in self.col_list_to_record:
                large_map_recorder_utils.save_part_image(self.current_region, self.row, self.col, map_part)
            img.append(map_part)

            to_next_col: bool = self.col < self.ck.max_column

            if to_next_col:
                self.drag_to_next_col()
            else:
                break

    @node_from(from_name='截图')
    @operation_node(name='合并大地图')
    def merge_screenshot(self) -> OperationRoundResult:
        # best_mys_resize: int = large_map_recorder_mys_utils.get_best_mys_image_resize_for_all(self.region_list, row, col)

        for region in self.region_list:
            merge = large_map_recorder_utils.merge_parts_into_one(
                region,
                max_row=self.ck.max_row,
                max_col=self.ck.max_column
            )
            large_map_recorder_utils.save_floor_image(region, merge)

        return self.round_success()

    @node_from(from_name='合并大地图')
    @operation_node(name='调整地图大小')
    def adjust_size(self) -> OperationRoundResult:
        # 先对四周进行拓展
        for region in self.region_list:
            large_map_recorder_utils.expand_large_map(
                region,
                self.ctx.game_config.mini_map_pos
            )

        # 不断寻找大小不一致的地图 进行调整
        while True:
            adjust: bool = False
            # 找到最大的楼层
            for i in range(len(self.region_list)):
                for j in range(i + 1, len(self.region_list)):
                    adjust = large_map_recorder_utils.adjust_to_sames_size(self.region_list[i], self.region_list[j])
                    if adjust:
                        break
                if adjust:
                    break

            if not adjust:
                break

        return self.round_success()

    @node_from(from_name='调整地图大小')
    @operation_node(name='保存')
    def do_save(self) -> OperationRoundResult:
        for region in self.region_list:
            large_map_recorder_utils.save_region(self.ctx, region)

        return self.round_success()

    def back_to_left_top(self):
        """
        回到左上角
        """
        log.info('开始滑动到左上角')
        center = game_const.STANDARD_CENTER_POS
        rt = center + center + Point(-10, -10)

        last_map_part: MatLike | None = None  # 上一次截图的地图部分
        empty_times: int = 0  # 空白次数
        while True:
            if not self.ctx.is_context_running:
                break
            screen = self.screenshot()
            screen_map_rect = large_map_utils.get_screen_map_rect(self.region)
            map_part = cv2_utils.crop_image_only(screen, screen_map_rect)

            if large_map_recorder_utils.is_empty_part(map_part):
                empty_times += 1
                log.info(f'当前地图部分接近空白 次数: {empty_times}')
                if empty_times >= 3:
                    break
            else:
                empty_times = 0
                if last_map_part is not None and cv2_utils.is_same_image(last_map_part, map_part):
                    log.info('当前地图部分无变化 已经到左上角了')
                    break

            last_map_part = map_part

            self.ctx.controller.drag_to(end=rt, start=center, duration=0.2)  # 先拉到左上角
            time.sleep(1.5)

        log.info('已经滑动到左上角 重置行列坐标')
        self.col = 1
        self.row = 1

    def back_to_top(self):
        """
        回到正上方
        """
        center = game_const.STANDARD_CENTER_POS
        bottom = Point(center.x, center.y + center.y - 10)
        for _ in range(6):
            if not self.ctx.is_context_running:
                break
            self.ctx.controller.drag_to(end=bottom, start=center, duration=1)  # 往上拉到尽头
            time.sleep(1.5)
        self.row = 1

    def back_to_left(self):
        """
        回到正左方
        """
        if self.ck.max_column <= 1:
            return

        log.info('开始滑动到最左方')
        center = game_const.STANDARD_CENTER_POS
        right = Point(center.x + center.x - 10, center.y)

        for i in range(self.ck.max_column):  # 先按列数 往左拉
            if not self.ctx.is_context_running:
                break
            self.ctx.controller.drag_to(end=right, start=center, duration=0.2)
            time.sleep(0.5)

        last_map_part: MatLike | None = None  # 上一次截图的地图部分
        empty_times: int = 0  # 空白次数

        while True:
            if not self.ctx.is_context_running:
                break
            screen = self.screenshot()
            screen_map_rect = large_map_utils.get_screen_map_rect(self.region)
            map_part = cv2_utils.crop_image_only(screen, screen_map_rect)

            if large_map_recorder_utils.is_empty_part(map_part):
                empty_times += 1
                log.info(f'当前地图部分接近空白 次数: {empty_times}')
                if empty_times >= 3:
                    break
            else:
                empty_times = 0
                if last_map_part is not None and cv2_utils.is_same_image(last_map_part, map_part):
                    log.info('当前地图部分无变化 已经到最左方了')
                    break

            last_map_part = map_part

            self.ctx.controller.drag_to(end=right, start=center, duration=0.2)  # 往左拉到尽头
            time.sleep(1)

        log.info('已经滑动到最左方 重置列坐标')
        self.col = 1

    def _drag_to_not_empty_row(self) -> None:
        """
        滑动到一个非空白行 进来的时候肯定是一个空白

        Returns:
            None
        """
        go_down: bool = True  # 是否往下拉
        empty_times_max: int = 3  # 允许出现空白的次数
        empty_times: int = 0  # 拖动后出现空白的次数

        while True:
            if not self.ctx.is_context_running:
                break

            # 进来的时候肯定是一个空白 所以先拖动再截图
            start = DRAG_NEXT_START
            end = start + Point(0, (-self.drag_distance_to_next_row if go_down else self.drag_distance_to_next_row))
            self.ctx.controller.drag_to(start=start, end=end)
            time.sleep(1)

            screen = self.screenshot()
            map_part = large_map_utils.get_screen_map_part(screen, self.region)
            if not large_map_recorder_utils.is_empty_part(map_part):
                break

            empty_times += 1
            if empty_times >= empty_times_max:
                go_down = not go_down
                empty_times_max += 3
                empty_times = 0

    def _drag_to_not_empty_col(self) -> None:
        """
        滑动到一个非空白列 进来的时候肯定是一个空白

        Returns:
            None
        """
        go_right: bool = True  # 是否往右拉
        empty_times_max: int = 3  # 允许出现空白的次数
        empty_times: int = 0  # 出现空白的次数

        while True:
            if not self.ctx.is_context_running:
                break

            # 进来的时候肯定是一个空白 所以先拖动再截图
            start = DRAG_NEXT_START
            end = start + Point(-self.drag_distance_to_next_col if go_right else self.drag_distance_to_next_col, 0)
            self.ctx.controller.drag_to(start=start, end=end)
            time.sleep(1)

            screen = self.screenshot()
            map_part = large_map_utils.get_screen_map_part(screen, self.region)
            if not large_map_recorder_utils.is_empty_part(map_part):
                break

            empty_times += 1
            if empty_times >= empty_times_max:
                go_right = not go_right
                empty_times_max += 3
                empty_times = 0

    def drag_to_next_row(self):
        """
        往下拖到下一行
        """
        center = Point(1350, 800)  # 大地图右方的空白区域 防止点击到地图的点 导致拖拽有问题
        top = center + Point(0, -self.drag_distance_to_next_row)
        self.special_drag_to(start=center, end=top)  # 往下拉一段
        time.sleep(1)
        self.row += 1

    def drag_to_next_col(self):
        """
        往右拖到下一列
        """
        start = DRAG_NEXT_START  # 大地图右方的空白区域 防止点击到地图的点 导致拖拽有问题
        # center = game_const.STANDARD_CENTER_POS
        end = start + Point(-self.drag_distance_to_next_col, 0)
        self.special_drag_to(start=start, end=end)  # 往右拉一段
        time.sleep(1)
        self.col += 1

    def fix_all_after_map_record(self, region: Region, dx: int, dy: int):
        """
        大地图重新绘制后 修改对应的文件
        :param region: 区域
        :param dx: 新地图与旧地图的偏移量
        :param dy: 新地图与旧地图的偏移量
        :return:
        """
        self.fix_world_patrol_route_after_map_record(region, dx, dy)
        self.fix_sim_uni_route_after_map_record(region, dx, dy)

    def fix_world_patrol_route_after_map_record(self, region: Region, dx: int, dy: int):
        """
        大地图重新绘制后 修改对应的路线
        :param region: 区域
        :param dx: 新地图与旧地图的偏移量
        :param dy: 新地图与旧地图的偏移量
        :return:
        """

        to_fix_op = [
            operation_const.OP_MOVE,
            operation_const.OP_SLOW_MOVE,
            operation_const.OP_NO_POS_MOVE,
            operation_const.OP_UPDATE_POS
        ]

        for floor in _FLOOR_LIST:
            floor_region = self.ctx.map_data.best_match_region_by_name(
                gt(region.cn, 'game'),
                planet=region.planet,
                target_floor=floor
            )
            if floor_region is None:
                continue

            all_route_list = self.ctx.world_patrol_route_data.load_all_route()

            for route in all_route_list:
                if route.tp.region != floor_region:
                    continue
                for route_item in route.route_list:
                    if route_item.op in to_fix_op:
                        route_item.data[0] += dx
                        route_item.data[1] += dy
                route.save()

    def fix_sim_uni_route_after_map_record(self, region: Region, dx: int, dy: int):
        """
        大地图重新绘制后 修改模拟宇宙对应的路线
        :param region: 区域
        :param dx: 新地图与旧地图的偏移量
        :param dy: 新地图与旧地图的偏移量
        :return:
        """

        to_fix_op = [
            operation_const.OP_MOVE,
            operation_const.OP_SLOW_MOVE,
            operation_const.OP_NO_POS_MOVE,
            operation_const.OP_UPDATE_POS
        ]

        for floor in _FLOOR_LIST:
            floor_region = self.ctx.map_data.best_match_region_by_name(
                gt(region.cn, 'game'),
                planet=region.planet,
                target_floor=floor
            )
            if floor_region is None:
                continue

            for level_type_enum in SimUniLevelTypeEnum:
                level_type = level_type_enum.value
                if level_type.route_id != level_type.type_id:
                    continue
                route_list = self.ctx.sim_uni_route_data.get_route_list(level_type)
                for route in route_list:
                    if route.region != floor_region:
                        continue

                    if route.op_list is not None and len(route.op_list) > 0:
                        for route_item in route.op_list:
                            if route_item.op in to_fix_op:
                                route_item.data[0] += dx
                                route_item.data[1] += dy

                    if route.start_pos is not None:
                        route.start_pos += Point(dx, dy)
                    if route.reward_pos is not None:
                        route.reward_pos += Point(dx, dy)
                    if route.next_pos_list is not None and len(route.next_pos_list) > 0:
                        for pos in route.next_pos_list:
                            pos.x += dx
                            pos.y += dy
                    route.save()

    def drag_to_get_max_column(self) -> None:
        """
        在最左方开始 尝试往右滑动 看最多需要滑动多少次到底
        遇到空白块时 上下滑动找非空白块
        """
        log.info('开始匹配最大列数')
        self.col = 1
        last_map_part: MatLike | None = None  # 上一次截图的大地图部分
        while True:
            if not self.ctx.is_context_running:
                break
            log.info(f'正在截图 列{self.col}')

            screen = self.screenshot()
            map_part = large_map_utils.get_screen_map_part(screen, self.region)

            if large_map_recorder_utils.is_empty_part(map_part):
                log.info(f'当前地图部分接近空白 尝试换行')
                self._drag_to_not_empty_row()
                continue

            if last_map_part is not None and cv2_utils.is_same_image(last_map_part, map_part, threshold=0.9):
                log.info(f'已经到达最右端 列数为{self.col - 1}')
                break

            last_map_part = map_part
            self.drag_to_next_col()

        self.ck.max_column = self.col - 1
        self.col = 1

    def drag_to_get_max_row(self) -> None:
        """
        在最上方开始 尝试往下滑动 看最多需要滑动多少次到底
        遇到空白块时 左右滑动找非空白块
        """
        log.info('开始匹配最大行数')
        self.row = 1
        last_map_part: MatLike | None = None  # 上一次截图的大地图部分
        while True:
            if not self.ctx.is_context_running:
                break
            log.info(f'正在截图 行{self.row}')

            screen = self.screenshot()
            map_part = large_map_utils.get_screen_map_part(screen, self.region)

            if large_map_recorder_utils.is_empty_part(map_part):
                log.info(f'当前地图部分接近空白 尝试换列')
                self._drag_to_not_empty_col()
                continue

            if last_map_part is not None and cv2_utils.is_same_image(last_map_part, map_part, threshold=0.9):
                log.info(f'已经到达最下端 行数为{self.row - 1}')
                break

            last_map_part = map_part
            self.drag_to_next_row()

        self.ck.max_row = self.row - 1
        self.row = 1

    def special_drag_to(self, start: Point, end: Point) -> None:
        """
        特殊实现的拖动 拖动前 先按下鼠标一段时间
        """
        start_pos = self.ctx.controller.game_win.game2win_pos(start)
        end_pos = self.ctx.controller.game_win.game2win_pos(end)

        pyautogui.moveTo(start_pos.x, start_pos.y)
        time.sleep(0.2)
        pyautogui.mouseDown()
        time.sleep(0.2)
        pyautogui.dragTo(end_pos.x, end_pos.y, duration=1)
        time.sleep(0.2)
        pyautogui.mouseUp()
        time.sleep(0.2)

def __debug(planet_name, region_name, run_mode: str = 'all'):
    ctx = SrContext()

    planet = ctx.map_data.best_match_planet_by_name(gt(planet_name, 'game'))
    region = ctx.map_data.best_match_region_by_name(gt(region_name, 'game'), planet=planet)

    key = f'{region.planet.cn} {region.cn}'
    log.info('当前录制 %s', key)
    sc = {
        'ctx': ctx,
        'region': region,
        # 'floor_list_to_record': [1],
        # 'row_list_to_record': [10, 11, 12],
        # 'col_list_to_record': [1, 2, 3]
    }

    app = LargeMapRecorder(**sc)

    ctx.init_by_config()
    ctx.init_for_world_patrol()

    if run_mode == 'all':
        app.execute()  # 正常录制
    elif run_mode == 'screenshot':  # 只进行截图
        ctx.start_running()
        app.open_map()
        app.choose_planet()

        app.current_region_idx = 0
        app.choose_region()
        app.do_screenshot()
        app.merge_screenshot()

        ctx.stop_running()
    elif run_mode == 'merge':
        # app.debug = True
        app.merge_screenshot()
    elif run_mode == 'adjust_size':
        app.adjust_size()
    elif run_mode == 'save':
        app.do_save()
    elif run_mode == 'fix':
        app.fix_all_after_map_record(region, 0, +231)
    else:
        pass


if __name__ == '__main__':
    __debug('翁法罗斯', '「永恒圣城」奥赫玛', 'save')

