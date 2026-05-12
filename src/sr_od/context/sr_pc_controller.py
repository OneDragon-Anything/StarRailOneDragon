import ctypes
import time

import cv2
from cv2.typing import MatLike
from typing import Optional, ClassVar

from one_dragon.base.controller.pc_controller_base import PcControllerBase
from one_dragon.base.geometry.point import Point
from one_dragon.utils import cal_utils
from one_dragon.utils.log_utils import log
from sr_od.config.game_config import GameConfig


class SrPcController(PcControllerBase):

    MOVE_INTERACT_TYPE: ClassVar[int] = 0
    TALK_INTERACT_TYPE: ClassVar[int] = 1

    def __init__(self, game_config: GameConfig,
                 screenshot_method: str,
                 standard_width: int = 1920,
                 standard_height: int = 1080):
        PcControllerBase.__init__(self,
                                  screenshot_method=screenshot_method,
                                  standard_width=standard_width,
                                  standard_height=standard_height)

        self.game_config: GameConfig = game_config
        self.turn_dx: float = self.game_config.turn_dx
        self.run_speed: float = 30
        self.walk_speed: float = 20
        self.is_moving: bool = False
        self.is_running: bool = False  # 是否在疾跑
        self.start_move_time: float = 0

    def close_game(self):
        """
        关闭游戏
        适配新版本游戏,需要多次点击关闭按钮才能成功关闭
        :return:
        """
        win = self.game_win.get_win()
        if win is None:
            return
        try:
            # 尝试多次点击关闭按钮,新版本游戏需要多次点击才能关闭
            for i in range(5):
                try:
                    win.close()
                    time.sleep(0.5)
                except Exception as e:
                    # 窗口已关闭会抛出异常,这是正常的
                    log.debug('窗口关闭循环中断: %s', str(e))
                    break
            log.info('关闭游戏成功')
        except Exception:
            log.error('关闭游戏失败', exc_info=True)

    def fill_uid_black(self, screen: MatLike) -> MatLike:
        lt = (30, 1030)
        rb = (200, 1080)
        cv2.rectangle(screen, lt, rb, (114, 114, 114), -1)
        return screen

    def before_screenshot(self) -> None:
        self.mouse_move(Point(30, 1030))

    def esc(self) -> bool:
        self.btn_tap(self.game_config.key_esc)
        return True

    def open_map(self) -> bool:
        self.btn_tap(self.game_config.key_open_map)
        return True

    def move(self, direction: str, press_time: float = 0, run: bool = False):
        """
        往固定方向移动
        :param direction: 方向 wsad
        :param press_time: 持续秒数
        :param run: 是否启用疾跑
        :return:
        """
        if direction not in ['w', 's', 'a', 'd']:
            log.error('非法的方向移动 %s', direction)
            return False
        self.start_move_time = time.time()
        if press_time > 0:
            self.btn_press(direction)
            self.is_moving = True
            self.enter_running(run)
            time.sleep(press_time)
            self.btn_release(direction)
            self.stop_moving_forward()
        else:
            self.btn_tap(direction)
        return True

    def enter_running(self, run: bool):
        """
        进入疾跑模式
        :param run: 是否进入疾跑
        :return:
        """
        if run and not self.is_running:
            time.sleep(0.02)
            self.btn_tap('mouse_right')
            self.is_running = True
        elif not run and self.is_running:
            time.sleep(0.02)
            self.btn_tap('mouse_right')
            self.is_running = False

    def get_move_time(self) -> float:
        """
        获取跑动的时间
        :return:
        """
        return time.time() - self.start_move_time if self.is_moving else 0

    def start_moving_forward(self, run: bool = False):
        """
        开始往前走
        :param run: 是否启用疾跑
        :return:
        """
        if self.is_moving:
            return
        self.is_moving = True
        self.btn_press('w')
        self.enter_running(run)

    def stop_moving_forward(self):
        if not self.is_moving:
            return
        self.btn_release('w')
        self.is_moving = False
        self.is_running = False

    def move_towards(self, pos1: Point, pos2: Point, angle: float, run: bool = False) -> bool:
        """
        朝目标点行走
        :param pos1: 起始点
        :param pos2: 目标点
        :param angle: 当前角度
        :param run: 是否疾跑
        :return:
        """
        if angle is None:
            log.error('当前角度为空 无法判断移动方向')
            return False
        self.turn_by_pos(pos1, pos2, angle)
        log.info('寻路中 当前点: %s 目标点: %s ', pos1, pos2)
        self.start_moving_forward(run=run)
        return True

    def turn_by_pos(self, current_pos: Point, target_pos: Point, current_angle: float):
        """
        朝目标点转向
        :param current_pos: 起始点
        :param target_pos: 目标点
        :param current_angle: 当前角度
        :return:
        """
        target_angle = cal_utils.get_angle_by_pts(current_pos, target_pos)
        self.turn_from_angle(current_angle, target_angle)

    def turn_from_angle(self, from_angle: float, to_angle: float):
        """
        从一个角度转向到另一个角度
        :param from_angle: 原来的角度
        :param to_angle: 新的角度
        :return:
        """
        delta_angle = cal_utils.angle_delta(from_angle, to_angle)
        log.info('当前角度: %.2f度 目标角度: %.2f度 转动朝向: %.2f度', from_angle, to_angle, delta_angle)
        self.turn_by_angle(delta_angle)

    def turn_by_angle(self, angle: float):
        """
        按角度旋转
        :param angle: 正数往右转 人物角度增加；负数往左转 人物角度减少
        :return:
        """
        self.turn_by_distance(self.turn_dx * angle)

    def turn_by_distance(self, d: float):
        """
        横向转向 按距离转
        :param d: 正数往右转 人物角度增加；负数往左转 人物角度减少
        :return:
        """
        self.move_mouse_relative(d, 0)

    def turn_down(self, distance: float):
        """
        视角上下移动
        :param distance: 正往下 负往上
        :return:
        """
        self.move_mouse_relative(0, distance * self.turn_dx)

    def move_mouse_relative(self, dx: float, dy: float) -> None:
        if dx == 0 and dy == 0:
            return
        ctypes.windll.user32.mouse_event(self.MOUSEEVENTF_MOVE, int(dx), int(dy))

    def cal_move_distance_by_time(self, seconds: float):
        """
        根据时间计算移动距离
        :param seconds: 秒
        :return:
        """
        return self.run_speed * seconds

    def switch_character(self, idx: int):
        """
        切换角色
        :param idx: 第几位角色 从1开始
        :return:
        """
        log.info('切换角色 %s', str(idx))
        self.btn_tap(str(idx))

    def initiate_attack(self):
        """
        主动发起攻击
        :return:
        """
        # 虽然在大世界指定坐标点击没有用 但这可以防止准备攻击时候被怪攻击 导致鼠标可以点到游戏窗口外
        self.click(Point(self.standard_width // 2, self.standard_height // 2))

    def interact(self, pos: Optional[Point] = None, interact_type: int = 0) -> bool:
        """
        交互
        :param pos: 如果是模拟器的话 需要传入交互内容的坐标
        :param interact_type: 交互类型
        :return:
        """
        if interact_type == SrPcController.MOVE_INTERACT_TYPE:
            self.btn_tap(self.game_config.key_interact)
        else:
            self.click(pos)
        return True

    def use_technique(self) -> bool:
        self.btn_tap(self.game_config.key_technique)
        return True

    def gameplay_interact(self, press_time: float = 0):
        if press_time > 0:
            self.btn_press(self.game_config.key_gameplay_interaction, press_time)
        else:
            self.btn_tap(self.game_config.key_gameplay_interaction)