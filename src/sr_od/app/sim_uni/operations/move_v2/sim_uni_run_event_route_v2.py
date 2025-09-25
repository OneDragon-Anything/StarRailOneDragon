from typing import Optional

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils
from one_dragon.yolo import detect_utils
from sr_od.app.sim_uni.operations.move_v1.sim_uni_move_to_interact_by_detect import SimUniMoveToInteractByDetect
from sr_od.app.sim_uni.operations.move_v2.sim_uni_run_route_base_v2 import SimUniRunRouteBaseV2
from sr_od.app.sim_uni.operations.sim_uni_event import SimUniEvent
from sr_od.app.sim_uni.sim_uni_const import SimUniLevelType, SimUniLevelTypeEnum
from sr_od.context.sr_context import SrContext
from sr_od.operations.interact.move_interact import MoveInteract
from sr_od.operations.move.move_without_pos import MoveWithoutPos
from sr_od.operations.sr_operation import SrOperation
from sr_od.sr_map import mini_map_utils
from sr_od.sr_map.mini_map_info import MiniMapInfo


class SimUniRunEventRouteV2(SimUniRunRouteBaseV2):

    def __init__(self, ctx: SrContext, level_type: SimUniLevelType = SimUniLevelTypeEnum.EVENT.value):
        """
        区域-事件
        1. 识别小地图上是否有事件图标 有的话就移动
        2. 小地图没有事件图标时 识别画面上是否有事件牌 有的话移动
        3. 交互
        4. 进入下一层
        :param ctx:
        """
        SimUniRunRouteBaseV2.__init__(self, ctx, level_type=level_type)
        self.move_by_mm_time: int = 0  # 按小地图移动的次数
        self.mm_icon_pos: Optional[Point] = None  # 小地图上事件的坐标
        self.event_handled: bool = False  # 已经处理过事件了

    @operation_node(name='区域开始前', is_start_node=True)
    def before_route(self) -> OperationRoundResult:
        """
        路线开始前
        1. 按照小地图识别初始的朝向
        :return:
        """
        screen = self.screenshot()
        self.check_angle(screen)
        return self.round_success()

    @node_from(from_name='区域开始前')
    @node_from(from_name='移动超时脱困')
    @node_from(from_name='转动找目标')  # 转动完重新开始目标识别
    @operation_node(name='识别小地图事件')
    def _check_mm_icon(self) -> OperationRoundResult:
        """
        识别小地图上的事件图标
        :return:
        """
        if self.move_by_mm_time >= 2:
            # 如果移动了2次都没有交互完 说明小地图没有这个图标 只是识别错了
            self.event_handled = True
        if self.event_handled:  # 已经交互过事件了
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_HAD_EVENT)

        screen = self.screenshot()
        mm = mini_map_utils.cut_mini_map(screen, self.ctx.game_config.mini_map_pos)
        mm_info: MiniMapInfo = mini_map_utils.analyse_mini_map(mm)
        mrl = self.ctx.tm.match_template(mm_info.raw_del_radio, 'sim_uni', 'mm_sp_event', threshold=0.7)
        if mrl.max is not None:
            self.mm_icon_pos = mrl.max.center
            if self.ctx.env_config.is_debug:  # 按小地图图标已经成熟 调试时强制使用yolo
                return self.round_success(status=SimUniRunRouteBaseV2.STATUS_NO_MM_EVENT)
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_WITH_MM_EVENT)
        else:
            if not self.event_handled and not self.is_level_type_correct(screen):
                # 如何没有交互过 又没有小地图图标 可能是之前楼层类型判断错了
                return self.round_fail(status=SimUniRunRouteBaseV2.STATUS_WRONG_LEVEL_TYPE)
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_NO_MM_EVENT)

    @node_from(from_name='识别小地图事件', status=SimUniRunRouteBaseV2.STATUS_WITH_MM_EVENT)
    @operation_node(name='按小地图朝事件移动')
    def _move_by_mm(self) -> OperationRoundResult:
        """
        按小地图的图标位置机械移动
        :return:
        """
        self.move_by_mm_time += 1
        self.nothing_times = 0
        self.moved_to_target = True
        op = MoveWithoutPos(self.ctx, start=self.ctx.game_config.mini_map_pos.mm_center, target=self.mm_icon_pos)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='识别小地图事件', status=SimUniRunRouteBaseV2.STATUS_NO_MM_EVENT)
    @operation_node(name='识别画面事件')
    def _detect_screen(self) -> OperationRoundResult:
        """
        识别游戏画面上是否有事件牌
        :return:
        """
        self.detect_entry = False
        self._view_down()
        screen = self.screenshot()

        frame_result = self.ctx.yolo_detector.sim_uni_yolo.run(screen)

        with_event: bool = False
        for result in frame_result.results:
            if result.detect_class.class_category == '模拟宇宙事件':
                with_event = True
            elif result.detect_class.class_category == '模拟宇宙下层入口':
                self.detect_entry = True

        if with_event and not self.event_handled:
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_WITH_DETECT_EVENT)
        elif self.detect_entry:
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_WITH_ENTRY)
        elif self.event_handled:  # 已经交互过事件了
            return self.round_success(status=SimUniRunRouteBaseV2.STATUS_HAD_EVENT)
        else:
            if self.ctx.env_config.is_debug:
                if self.nothing_times == 1:
                    self.save_screenshot()
                cv2_utils.show_image(detect_utils.draw_detections(frame_result), win_name='SimUniRunEventRouteV2')
            return self.round_success(SimUniRunRouteBaseV2.STATUS_NO_DETECT_EVENT)

    @node_from(from_name='识别画面事件', status=SimUniRunRouteBaseV2.STATUS_WITH_DETECT_EVENT)
    @operation_node(name='按画面朝事件移动', timeout_seconds=20)
    def _move_by_detect(self) -> OperationRoundResult:
        """
        根据画面识别结果走向事件
        :return:
        """
        self.nothing_times = 0
        self.moved_to_target = True
        op = SimUniMoveToInteractByDetect(self.ctx,
                                          interact_class='模拟宇宙事件',
                                          interact_word='事件',
                                          interact_during_move=True)
        op_result = op.execute()
        if op_result.success:
            self.detect_move_timeout_times = 0
        return self.round_by_op_result(op_result)

    @node_from(from_name='按画面朝事件移动', status=SrOperation.STATUS_TIMEOUT)
    @operation_node(name='移动超时脱困')
    def after_detect_timeout(self) -> OperationRoundResult:
        return SimUniRunRouteBaseV2.after_detect_timeout(self)

    @node_from(from_name='按小地图朝事件移动')
    @node_from(from_name='按画面朝事件移动', status=SimUniMoveToInteractByDetect.STATUS_ARRIVAL)  # 走到了就进行交互
    @operation_node(name='交互')
    def _interact(self) -> OperationRoundResult:
        """
        尝试交互
        进入这里代码已经识别到事件了 则必须要交互才能进入下一层
        :return:
        """
        op = MoveInteract(self.ctx, '事件', lcs_percent=0.1, single_line=True)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='按画面朝事件移动', status=SimUniMoveToInteractByDetect.STATUS_INTERACT)  # 移动时已经按了交互键
    @node_from(from_name='交互')
    @operation_node(name='事件')
    def _handle_event(self) -> OperationRoundResult:
        """
        事件处理
        :return:
        """
        self.event_handled = True
        op = SimUniEvent(self.ctx, skip_first_screen_check=False)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='事件')  # 交互之后前往下层
    @node_from(from_name='识别画面事件', status=SimUniRunRouteBaseV2.STATUS_NO_DETECT_EVENT)  # 识别不到事件 尝试识别下层入口
    @node_from(from_name='识别小地图事件', status=SimUniRunRouteBaseV2.STATUS_HAD_EVENT)  # 之前已经处理过事件了 尝试识别下层入口
    @node_from(from_name='识别画面事件', status=SimUniRunRouteBaseV2.STATUS_HAD_EVENT)  # 之前已经处理过事件了 尝试识别下层入口
    @operation_node(name='识别下层入口')
    def check_next_entry(self) -> OperationRoundResult:
        return SimUniRunRouteBaseV2.check_next_entry(self)

    @node_from(from_name='识别下层入口', status=SimUniRunRouteBaseV2.STATUS_WITH_ENTRY)  # 找到了下层入口就开始移动
    @node_from(from_name='识别画面事件', status=SimUniRunRouteBaseV2.STATUS_WITH_ENTRY)  # 找到了下层入口就开始移动
    @operation_node(name='向下层移动')
    def move_to_next(self) -> OperationRoundResult:
        return SimUniRunRouteBaseV2.move_to_next(self)

    @node_from(from_name='识别下层入口', status=SimUniRunRouteBaseV2.STATUS_NO_ENTRY)
    @node_from(from_name='向下层移动', success=False)  # 移动可能走过头了 尝试转一圈识别
    @operation_node(name='转动找目标')
    def turn_when_nothing(self) -> OperationRoundResult:
        return SimUniRunRouteBaseV2.turn_when_nothing(self)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_ocr()

    op = SimUniRunEventRouteV2(ctx)
    ctx.start_running()
    op.execute()
    ctx.stop_running()


if __name__ == '__main__':
    __debug()