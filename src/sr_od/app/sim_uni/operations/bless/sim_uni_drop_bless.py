import time
from typing import ClassVar, List, Optional

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.app.sim_uni.operations.bless import bless_utils
from sr_od.app.sim_uni.operations.bless.bless_utils import SimUniBlessPos
from sr_od.app.sim_uni.operations.bless.sim_uni_choose_bless import SimUniChooseBless
from sr_od.app.sim_uni.sim_uni_challenge_config import SimUniChallengeConfig
from sr_od.app.sim_uni.sim_uni_const import SimUniBless
from sr_od.context.sr_context import SrContext
from sr_od.operations.click_dialog_confirm import ClickDialogConfirm
from sr_od.operations.sr_operation import SrOperation


class SimUniDropBless(SrOperation):

    STATUS_RETRY: ClassVar[str] = '重试其他祝福位置'

    def __init__(self, ctx: SrContext,
                 config: Optional[SimUniChallengeConfig] = None,
                 skip_first_screen_check: bool = True
                 ):
        """
        按照优先级选择祝福
        :param ctx:
        :param config: 挑战配置
        :param skip_first_screen_check: 是否跳过第一次的画面状态检查
        """
        SrOperation.__init__(
            self,
            ctx,
            op_name='%s %s' % (gt('模拟宇宙', 'game'), gt('丢弃祝福')),
        )

        self.config: Optional[SimUniChallengeConfig] = config
        self.skip_first_screen_check: bool = skip_first_screen_check  # 是否跳过第一次的画面状态检查 用于提速

    def handle_init(self) -> Optional[OperationRoundResult]:
        """
        执行前的初始化 由子类实现
        注意初始化要全面 方便一个指令重复使用
        可以返回初始化后判断的结果
        - 成功时跳过本指令
        - 失败时立刻返回失败
        - 不返回时正常运行本指令
        """
        self.first_screen_check = True  # 是否第一次检查画面状态
        self.bless_cnt_type: int = 3  # 祝福数量类型

        return None

    @operation_node(name='画面识别', is_start_node=True)
    def check_screen_state(self):
        screen = self.screenshot()

        if self.first_screen_check and self.skip_first_screen_check:
            self.first_screen_check = False
            return self.round_success(sim_uni_screen_state.ScreenState.SIM_DROP_CURIOS.value)

        state = sim_uni_screen_state.get_sim_uni_screen_state(self.ctx, screen, self.ctx.ocr, drop_bless=True)

        if state is not None:
            return self.round_success(state)
        else:
            return self.round_retry('未在丢弃祝福页面', wait=1)

    @node_from(from_name='画面识别')
    @operation_node(name='选择祝福')
    def choose_bless(self) -> OperationRoundResult:
        screen = self.screenshot()

        bless_pos_list: List[SimUniBlessPos] = bless_utils.get_bless_pos(self.ctx, screen)
        if len(bless_pos_list) == 0:
            return self.round_retry('未识别到祝福', wait=1)

        bless_list: list[SimUniBless] = [i.bless for i in bless_pos_list]
        target_idx: int = bless_utils.get_bless_by_priority(bless_list, self.config, can_reset=False, asc=False)
        self.ctx.controller.click(bless_pos_list[target_idx].rect.center)
        time.sleep(0.25)
        self.ctx.controller.click(SimUniChooseBless.CONFIRM_BTN.center)
        return self.round_success(wait=1)

    @node_from(from_name='选择祝福')
    @operation_node(name='确认')
    def confirm(self) -> OperationRoundResult:
        """
        确认丢弃
        :return:
        """
        op = ClickDialogConfirm(self.ctx, wait_after_success=1)
        op_result = op.execute()
        if op_result.success:
            return self.round_success()
        else:
            self.bless_cnt_type -= 1
            if self.bless_cnt_type > 0:
                return self.round_success(status=SimUniDropBless.STATUS_RETRY)
            else:
                return self.round_fail(op_result.status)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_ocr()
    ctx.start_running()

    op = SimUniDropBless(ctx)
    op.execute()
    ctx.stop_running()


if __name__ == '__main__':
    __debug()