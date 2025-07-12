from typing import Optional

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.app.sim_uni.operations.bless.sim_uni_choose_bless import SimUniChooseBless
from sr_od.app.sim_uni.operations.curio.sim_uni_choose_curio import SimUniChooseCurio
from sr_od.app.sim_uni.sim_uni_challenge_config import SimUniChallengeConfig
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state


class SimUniWaitLevelStart(SrOperation):

    def __init__(self, ctx: SrContext,
                 config: Optional[SimUniChallengeConfig] = None,
                 wait_after_success: Optional[int] = None
                 ):
        """
        模拟宇宙 等待某一层的开始
        :param ctx:
        :param wait_after_success: 进入后等待秒数
        """
        SrOperation.__init__(self, ctx,
                             op_name='%s %s' %
                                     (gt('模拟宇宙', 'game'),
                                      gt('等待楼层加载'))
                             )

        self.config: Optional[SimUniChallengeConfig] = ctx.sim_uni_challenge_config if config is None else config
        self.wait_after_success: Optional[int] = wait_after_success
        self.first_bless_chosen = False

    @operation_node(name='画面识别', node_max_retry_times=20, is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        screen = self.screenshot()

        state = sim_uni_screen_state.get_sim_uni_screen_state(
            self.ctx, screen,
            in_world=True,
            bless=True,
            curio=True,
            sim_uni=True
        )
        if state == common_screen_state.ScreenState.NORMAL_IN_WORLD.value:
            # 移动进入下一层后 小地图会有缩放 稍微等一下方便小地图匹配
            return self.round_success(wait=self.wait_after_success)
        elif (state == sim_uni_screen_state.ScreenState.SIM_BLESS.value  # 刚进入模拟宇宙时 会需要选择开拓祝福
              or state == sim_uni_screen_state.ScreenState.SIM_TYPE_NORMAL.value):  # 2.3版本改了 开头会显示模拟宇宙
            op = SimUniChooseBless(self.ctx, self.config,
                                   skip_first_screen_check=True,
                                   before_level_start=not self.first_bless_chosen)
            op_result = op.execute()
            if op_result.success:
                self.first_bless_chosen = True
                return self.round_wait(wait=1)
            else:
                return self.round_fail(status=op_result.status, data=op_result.data)
        elif state == sim_uni_screen_state.ScreenState.SIM_CURIOS.value:
            op = SimUniChooseCurio(self.ctx, self.config)
            op_result = op.execute()
            if op_result.success:
                return self.round_wait()
            else:
                return self.round_by_op_result(op_result)
        else:
            return self.round_retry('无法判断当前画面状态', wait=1)
