from cv2.typing import MatLike
from enum import Enum

from sr_od.context.sr_context import SrContext
from sr_od.screen_state import common_screen_state, fast_recover_screen_state, battle_screen_state


class WorldPatrolScreenState(Enum):

    NORMAL_IN_WORLD = '大世界'
    BATTLE_FAIL = '战斗失败'
    FAST_RECOVER = '快速恢复'


def get_world_patrol_screen_state(
        ctx: SrContext, screen: MatLike,
        in_world: bool = False,
        battle: bool = False,
        battle_fail: bool = False,
        fast_recover: bool = False,
        express_supply: bool = False,
):
    """
    获取锄大地的画面状态
    注意 战斗中出现的技能文本 可能会被识别出来 因此lcs阈值应该最少为0.5
    :param ctx: 上下文
    :param screen: 屏幕截图
    :param in_world: 可能在大世界
    :param battle: 可能在战斗
    :param battle_fail: 可能在战斗失败
    :param fast_recover: 可能在快速恢复
    :param express_supply: 可能在列车补给
    :return:
    """
    if in_world and common_screen_state.is_normal_in_world(ctx, screen):
        return WorldPatrolScreenState.NORMAL_IN_WORLD.value

    if battle_fail and battle_screen_state.is_battle_fail(ctx, screen):
        return battle_screen_state.ScreenState.BATTLE_FAIL.value

    if fast_recover and fast_recover_screen_state.is_fast_recover(ctx, screen):
        return WorldPatrolScreenState.FAST_RECOVER.value

    if express_supply and common_screen_state.is_express_supply(ctx, screen):
        return common_screen_state.ScreenState.EXPRESS_SUPPLY.value.status

    if battle:  # 有判断的时候 不在前面的情况 就认为是战斗
        return battle_screen_state.ScreenState.BATTLE.value

    return None
