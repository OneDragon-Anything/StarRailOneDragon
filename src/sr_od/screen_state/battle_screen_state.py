from cv2.typing import MatLike
from enum import Enum

from one_dragon.base.screen import screen_utils
from one_dragon.base.screen.screen_utils import FindAreaResultEnum
from sr_od.context.sr_context import SrContext
from sr_od.screen_state import common_screen_state


class ScreenState(Enum):

    BATTLE: str = '战斗'
    BATTLE_FAIL: str = '战斗失败'
    BATTLE_SUCCESS: str = '挑战成功'


def is_battle_fail(ctx: SrContext, screen: MatLike) -> bool:
    """
    是否在战斗失败画面
    :param ctx: 上下文
    :param screen: 游戏画面
    :return:
    """
    return (
            screen_utils.find_area(ctx, screen, '战斗画面', '战斗失败-有奖励') == FindAreaResultEnum.TRUE
            or screen_utils.find_area(ctx, screen, '战斗画面', '战斗失败-双倍奖励') == FindAreaResultEnum.TRUE
            or screen_utils.find_area(ctx, screen, '战斗画面', '战斗失败-无奖励') == FindAreaResultEnum.TRUE
    )


def get_tp_battle_screen_state(
        ctx: SrContext,
        screen: MatLike,
        in_world: bool = False,
        battle_success: bool = False,
        battle_fail: bool = False
) -> str:
    """
    获取开拓力副本战斗的画面状态
    :param ctx: 上下文
    :param screen: 游戏画面
    :param in_world: 可能在大世界
    :param battle_success: 可能在战斗
    :param battle_fail: 可能在战斗失败
    :return:
    """
    if in_world and common_screen_state.is_normal_in_world(ctx, screen):
        return common_screen_state.ScreenState.NORMAL_IN_WORLD.value

    if battle_success:
        success_area_list = [
            '挑战成功-有奖励',
            '挑战成功-双倍奖励',
            '挑战成功-无奖励',
            '挑战成功-遗器自动分解的双倍奖励',
        ]

        for area_name in success_area_list:
            result = screen_utils.find_area(ctx, screen, '战斗画面', area_name)
            if result == FindAreaResultEnum.TRUE:
                return ScreenState.BATTLE_SUCCESS.value

    if battle_fail:
        fail_area_list = [
            '战斗失败-有奖励',
            '战斗失败-双倍奖励',
            '战斗失败-无奖励',
        ]

        for area_name in fail_area_list:
            result = screen_utils.find_area(ctx, screen, '战斗画面', area_name)
            if result == FindAreaResultEnum.TRUE:
                return ScreenState.BATTLE_FAIL.value

    return ScreenState.BATTLE.value