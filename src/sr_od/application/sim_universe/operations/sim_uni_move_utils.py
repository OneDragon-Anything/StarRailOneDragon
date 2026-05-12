from one_dragon.base.geometry.point import Point
from one_dragon.utils import cal_utils
from one_dragon.yolo.detect_utils import DetectObjectResult
from sr_od.context.sr_context import SrContext

_MAX_TURN_ANGLE = 15  # 由于目标识别没有纵深 判断的距离方向不准 限定转向角度慢慢转过去
_CHARACTER_POS = Point(960, 920)  # 人物脚底


def delta_angle_to_detected_object(obj: DetectObjectResult) -> float:
    """
    转向识别物体需要的偏移角度
    :param obj:
    :return: 偏移角度 正数往右转 负数往左转
    """
    obj_pos = Point((obj.x1 + obj.x2) / 2, obj.y2)  # 识别框底部

    # 小地图用的角度 正右方为0 顺时针为正
    mm_angle = cal_utils.get_angle_by_pts(_CHARACTER_POS, obj_pos)

    # 与画面正前方的偏移角度 就是需要转的角度
    turn_angle = mm_angle - 270

    return turn_angle


def turn_to_detected_object(ctx: SrContext, obj: DetectObjectResult) -> float:
    """
    转向一个识别到的物体
    :param ctx: 上下文
    :param obj: 检测物体
    :return: 转向角度 正数往右转 负数往左转
    """
    turn_angle = delta_angle_to_detected_object(obj)
    return turn_by_angle_slowly(ctx, turn_angle)


def turn_by_angle_slowly(ctx: SrContext, turn_angle: float) -> float:
    """
    缓慢转向 有一个最大的转向角度
    :param ctx: 上下文
    :param turn_angle: 转向角度
    :return: 真实转向角度
    """
    # 由于目前没有距离的推测 不要一次性转太多角度
    if turn_angle > _MAX_TURN_ANGLE:
        turn_angle = _MAX_TURN_ANGLE
    if turn_angle < -_MAX_TURN_ANGLE:
        turn_angle = -_MAX_TURN_ANGLE

    ctx.controller.turn_by_angle(turn_angle)
    return turn_angle
