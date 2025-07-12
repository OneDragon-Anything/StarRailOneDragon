from typing import Optional, Callable

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.matcher.match_result import MatchResult
from one_dragon.base.operation.operation_base import OperationResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.app.sim_uni.operations.sim_uni_enter_fight import SimUniEnterFight
from sr_od.app.sim_uni.sim_uni_challenge_config import SimUniChallengeConfig
from sr_od.context.sr_context import SrContext
from sr_od.operations.move import cal_pos_utils
from sr_od.operations.move.cal_pos_utils import VerifyPosInfo
from sr_od.operations.move.move_directly import MoveDirectly
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state, battle_screen_state
from sr_od.sr_map.large_map_info import LargeMapInfo
from sr_od.sr_map.mini_map_info import MiniMapInfo


class MoveDirectlyInSimUni(MoveDirectly):
    """
    从当前位置 朝目标点直线前行
    有简单的脱困功能

    模拟宇宙专用
    - 不需要考虑特殊点
    - 战斗后需要选择祝福
    """
    def __init__(self, ctx: SrContext, lm_info: LargeMapInfo,
                 start: Point, target: Point,
                 next_lm_info: Optional[LargeMapInfo] = None,
                 config: Optional[SimUniChallengeConfig] = None,
                 stop_afterwards: bool = True,
                 no_run: bool = False,
                 no_battle: bool = False,
                 op_callback: Optional[Callable[[OperationResult], None]] = None
                 ):
        MoveDirectly.__init__(
            self,
            ctx, lm_info,
            start, target,
            next_lm_info=next_lm_info, stop_afterwards=stop_afterwards,
            no_run=no_run, no_battle=no_battle,
            op_callback=op_callback)
        self.op_name = '%s %s' % (gt('模拟宇宙', 'game'), gt('移动 %s -> %s', 'game') % (start, target))
        self.config: SimUniChallengeConfig = config

    def get_fight_op(self, in_world: bool = True) -> SrOperation:
        """
        移动过程中被袭击时候处理的指令
        :return:
        """
        if in_world:
            first_state = common_screen_state.ScreenState.NORMAL_IN_WORLD.value
        else:
            first_state = battle_screen_state.ScreenState.BATTLE.value
        return SimUniEnterFight(self.ctx, config=self.config, first_state=first_state)

    def do_cal_pos(self, mm_info: MiniMapInfo,
                   lm_rect: Rect, verify: VerifyPosInfo) -> Optional[MatchResult]:
        """
        真正的计算坐标
        :param mm_info: 当前的小地图信息
        :param lm_rect: 使用的大地图范围
        :param verify: 用于验证坐标的信息
        :return:
        """
        try:
            real_move_time = self.ctx.controller.get_move_time()
            next_pos = cal_pos_utils.sim_uni_cal_pos(
                self.ctx, self.lm_info, mm_info,
                lm_rect=lm_rect,
                running=self.ctx.controller.is_moving,
                real_move_time=real_move_time,
                verify=verify)
            if next_pos is None and self.next_lm_info is not None:
                next_pos = cal_pos_utils.sim_uni_cal_pos(
                    self.ctx, self.next_lm_info, mm_info,
                    lm_rect=lm_rect,
                    running=self.ctx.controller.is_moving,
                    real_move_time=real_move_time,
                    verify=verify)
        except Exception:
            next_pos = None
            log.error('识别坐标失败', exc_info=True)

        return next_pos