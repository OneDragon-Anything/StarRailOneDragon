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

    @operation_node(name='等待', timeout_seconds=1200, node_max_retry_times=99, is_start_node=True)
    def wait(self) -> OperationRoundResult:
        screen = self.screenshot()

        # 等待战斗期间弹出的提示类弹窗(如饰品提取首次进入的「当前不存在任何
        # 存档,是否直接开始战斗?」)会盖住战斗画面 → 本节点只认三种状态会
        # 干等至超时。弹窗语义=确认继续战斗:直接点确认,下轮重判(关闭动画
        # 期间确认按钮会消失,不能用「点到了确认」当成功判据——实证误判 FAIL)。
        if self.round_by_find_area(screen, '挑战副本', '提示弹框-标题').is_success:
            self.round_by_click_area('挑战副本', '提示弹框-确认')
            return self.round_wait(wait=1)

        state = battle_screen_state.get_tp_battle_screen_state(
            self.ctx, screen,
            battle_success=True,
            battle_fail=True,
            in_world=True
        )
        if state == battle_screen_state.ScreenState.BATTLE_FAIL.value or state == battle_screen_state.ScreenState.BATTLE_SUCCESS.value:
            return self.round_success(state)
        elif state == common_screen_state.ScreenState.NORMAL_IN_WORLD.value:
            if self.try_attack:
                self.ctx.controller.initiate_attack()
            return self.round_retry(wait_round_time=1)
        else:
            return self.round_wait('等待战斗结束', wait=1)
