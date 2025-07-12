from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni import sim_uni_screen_state
from sr_od.app.sim_uni.operations.bless.sim_uni_choose_bless import SimUniChooseBless
from sr_od.app.sim_uni.operations.bless.sim_uni_drop_bless import SimUniDropBless
from sr_od.app.sim_uni.operations.curio.sim_uni_choose_curio import SimUniChooseCurio, SimUniDropCurio
from sr_od.app.sim_uni.operations.sim_uni_event import SimUniEvent
from sr_od.app.sim_uni.operations.sim_uni_exit import SimUniExit
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state


class BackToNormalWorldPlus(SrOperation):

    def __init__(self, ctx: SrContext):
        """
        返回普通大世界 增强版
        需要在任何情况下使用都能顺利地返回手机菜单 用于应用结束后 确保不会卡死下一个应用
        已考虑场景如下
        :param ctx:
        """
        SrOperation.__init__(self, ctx, op_name=gt('返回普通大世界'))

    @operation_node(name='画面识别', node_max_retry_times=20, is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        screen = self.screenshot()

        # 先看看左上角是否退出按钮
        result = self.round_by_find_area(screen, '模拟宇宙', '大世界返回按钮')
        if result.is_success:
            # 判断是否在模拟宇宙内
            sim_uni_level_type = sim_uni_screen_state.get_level_type(self.ctx, screen)
            if sim_uni_level_type is not None:
                return self.sim_uni_exit()

            # 如果有返回按钮 又不是在模拟宇宙 则就是在逐光捡金内
            result = self.round_by_find_and_click_area(screen, '模拟宇宙', '大世界返回按钮')
            if result.is_success:
                return self.round_wait(wait=1)

            # 都不在的话 暂时不支持返回大世界
            return self.round_fail('未支持的副本画面')

        # 在可以移动的画面 - 普通大世界
        result = self.round_by_find_area(screen, '大世界', '角色图标')
        if result.is_success:  # 右上角有角色图标
            return self.round_success()

        # 手机菜单
        result = self.round_by_find_area(screen, '菜单', '开拓等级')
        if result.is_success:
            self.round_by_click_area('菜单', '右上角返回')
            return self.round_wait(wait=1)

        # 模拟宇宙内的画面
        sim_uni_state = sim_uni_screen_state.get_sim_uni_screen_state(
            self.ctx, screen,
            event=True,
            bless=True,
            drop_bless=True,
            curio=True,
            drop_curio=True
        )

        if sim_uni_state == sim_uni_screen_state.ScreenState.SIM_BLESS.value:
            return self.sim_uni_choose_bless()

        if sim_uni_state == sim_uni_screen_state.ScreenState.SIM_DROP_BLESS.value:
            return self.sim_uni_drop_bless()

        if sim_uni_state == sim_uni_screen_state.ScreenState.SIM_CURIOS.value:
            return self.sim_uni_choose_curio()

        if sim_uni_state == sim_uni_screen_state.ScreenState.SIM_DROP_CURIOS.value:
            return self.sim_uni_drop_curio()

        if sim_uni_state == sim_uni_screen_state.ScreenState.SIM_EVENT.value:
            return self.sim_uni_event()

        # 对话框 - 逐光捡金 退出确认
        result = self.round_by_find_and_click_area(screen, '逐光捡金', '退出对话框确认')
        if result.is_success:
            return self.round_wait(wait=5)

        # 列车补给 - 点击空白处继续
        if common_screen_state.is_express_supply(self.ctx, screen):
            common_screen_state.claim_express_supply(self.ctx)
            return self.round_wait(wait=2)

        # 战斗中 点击右上角后出现的画面 需要需要退出
        battle_exit_area_list = [
            ('模拟宇宙', '终止战斗并结算'),  # 模拟宇宙
        ]
        for area in battle_exit_area_list:
            result = self.round_by_find_and_click_area(screen, area[0], area[1])
            if result.is_success:
                return self.round_wait(result.status, wait=1)

        # 战斗结束后 出现的退出关卡
        result = self.round_by_find_and_click_area(screen, '战斗画面', '退出关卡按钮')
        if result.is_success:
            return self.round_wait(result.status, wait=2)

        # 其他情况 - 均点击右上角触发返回上一级
        result = self.round_by_click_area('菜单', '右上角返回')
        return self.round_wait(result.status, wait=1)

    def sim_uni_exit(self) -> OperationRoundResult:
        op = SimUniExit(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)

    def sim_uni_event(self) -> OperationRoundResult:
        op = SimUniEvent(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)

    def sim_uni_choose_bless(self) -> OperationRoundResult:
        op = SimUniChooseBless(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)

    def sim_uni_drop_bless(self) -> OperationRoundResult:
        op = SimUniDropBless(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)

    def sim_uni_choose_curio(self) -> OperationRoundResult:
        op = SimUniChooseCurio(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)

    def sim_uni_drop_curio(self) -> OperationRoundResult:
        op = SimUniDropCurio(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_wait(wait=1)
        else:
            return self.round_retry(wait=1)
