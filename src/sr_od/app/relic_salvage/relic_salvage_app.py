from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sr_application import SrApplication
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus


class RelicSalvageApp(SrApplication):

    def __init__(self, ctx: SrContext):
        SrApplication.__init__(self, ctx, 'relic_salvage', op_name=gt('遗器分解'),
                               run_record=ctx.relic_salvage_run_record, need_notify=True)

    @operation_node(name='开始前返回', is_start_node=True)
    def back_at_first(self) -> OperationRoundResult:
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='开始前返回')
    @operation_node(name='前往分解画面')
    def goto_salvage(self) -> OperationRoundResult:
        return self.round_by_goto_screen(screen_name='背包-遗器分解', retry_wait=1)

    @node_from(from_name='前往分解画面')
    @operation_node(name='快速选择')
    def click_filter(self) -> OperationRoundResult:
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '背包-遗器分解', '按钮-快速选择',
                                                 success_wait=1, retry_wait=1)

    @node_from(from_name='快速选择')
    @operation_node(name='选择等级')
    def choose_level(self) -> OperationRoundResult:
        screen = self.screenshot()
        return self.round_by_find_and_click_area(
            screen, '背包-遗器分解-快速选择', self.ctx.relic_salvage_config.salvage_level,
            success_wait=1, retry_wait=1
        )

    @node_from(from_name='选择等级')
    @operation_node(name='选择弃置')
    def choose_abandon(self) -> OperationRoundResult:
        if self.ctx.relic_salvage_config.salvage_abandon:
            screen = self.screenshot()
            return self.round_by_find_and_click_area(screen, '背包-遗器分解-快速选择', '全选已弃置',
                                                     success_wait=1, retry_wait=1)
        else:
            return self.round_success('无需选择')

    @node_from(from_name='选择等级', success=False)
    @node_from(from_name='选择弃置')
    @node_from(from_name='选择弃置', success=False)
    @operation_node(name='快速选择确认')
    def click_filter_confirm(self) -> OperationRoundResult:
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '背包-遗器分解-快速选择', '按钮-确认',
                                                 success_wait=1, retry_wait=1)

    @node_from(from_name='快速选择确认')
    @operation_node(name='点击分解')
    def click_salvage(self) -> OperationRoundResult:
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '背包-遗器分解', '按钮-分解',
                                                 success_wait=1, retry_wait=1)

    @node_from(from_name='点击分解')
    @operation_node(name='点击分解确认')
    def click_salvage_confirm(self) -> OperationRoundResult:
        screen = self.screenshot()
        return self.round_by_find_and_click_area(screen, '背包-遗器分解', '按钮-分解确认',
                                                 success_wait=1, retry_wait=1)

    @node_from(from_name='点击分解确认')
    @node_from(from_name='点击分解确认', success=False)  # 可能没有需要分解的
    @operation_node(name='完成后返回')
    def back_at_last(self) -> OperationRoundResult:
        self.notify_screenshot = self.save_screenshot_bytes()  # 结束后通知的截图
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_by_op_result(op.execute())


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    app = RelicSalvageApp(ctx)
    app.execute()


if __name__ == '__main__':
    __debug()