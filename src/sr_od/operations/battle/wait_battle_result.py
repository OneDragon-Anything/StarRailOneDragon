from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import battle_screen_state, common_screen_state


class WaitBattleResult(SrOperation):

    def __init__(self, ctx: SrContext, try_attack: bool = False):
        super().__init__(ctx, op_name=gt('等待战斗结果'))

        self.try_attack: bool = try_attack
        """未进入战斗时 是否尝试攻击"""

    @operation_node(name='等待', timeout_seconds=1200, is_start_node=True)
    def wait(self) -> OperationRoundResult:
        screen = self.screenshot()

        state = battle_screen_state.get_tp_battle_screen_state(
            self.ctx, screen,
            battle_success=True,
            battle_fail=True,
            in_world=True
        )
        if state == battle_screen_state.ScreenState.BATTLE_FAIL.value:
            return self.round_success(state)
        elif state == battle_screen_state.ScreenState.BATTLE_SUCCESS.value:
            return self.round_success(state)
        elif state == common_screen_state.ScreenState.NORMAL_IN_WORLD.value:
            if self.try_attack:
                self.ctx.controller.initiate_attack()
            return self.round_retry(wait_round_time=1)
        else:
            return self.round_wait('等待战斗结束', wait=1)
