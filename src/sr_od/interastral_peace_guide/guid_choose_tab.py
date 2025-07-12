from cv2.typing import MatLike

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guide_def import GuideTab
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state


class GuideChooseTab(SrOperation):

    def __init__(self, ctx: SrContext, target: GuideTab):
        """
        使用前需要已经打开【星际和平指南】

        选择对应的TAB
        """
        SrOperation.__init__(self, ctx, op_name='%s %s' % (
                gt('指南TAB'), gt(target.cn)
        ))

        self.target: GuideTab = target  # 需要选择的TAB

    @operation_node(name='选择', node_max_retry_times=5, is_start_node=True)
    def choose(self) -> OperationRoundResult:
        screen: MatLike = self.screenshot()

        if not common_screen_state.in_secondary_ui(self.ctx, screen, '星际和平指南'):
            return self.round_retry(status='等待指南加载', wait=1)

        if common_screen_state.in_secondary_ui(self.ctx, screen, self.target.cn):
            return self.round_success()

        result = self.round_by_find_and_click_area(screen, '星际和平指南', 'TAB-' + self.target.cn)
        if result.is_success:
            return self.round_wait(result.status, wait=1)
        else:
            return self.round_retry(result.status, wait=1)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_ocr()
    ctx.start_running()

    op = GuideChooseTab(ctx, ctx.guide_data.best_match_tab_by_name('生存索引'))
    op.execute()


if __name__ == '__main__':
    __debug()
