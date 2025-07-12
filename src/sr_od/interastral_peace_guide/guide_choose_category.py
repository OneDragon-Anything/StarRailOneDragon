from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guide_def import GuideCategory
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state import common_screen_state


class GuideChooseCategory(SrOperation):

    def __init__(self, ctx: SrContext, target: GuideCategory,
                 skip_wait: bool = True):
        """
        在 星际和平指南 画面中使用
        选择左方的一个类目
        :param ctx: 上下文
        :param target: 目标类目
        :param skip_wait: 跳过等待加载
        """
        SrOperation.__init__(self, ctx, op_name='%s %s' % (gt('指南'), gt(target.cn)))

        self.target: GuideCategory = target
        self.skip_wait: bool = skip_wait

    @operation_node(name='等待画面加载', node_max_retry_times=5, is_start_node=True)
    def wait_screen(self) -> OperationRoundResult:
        screen = self.screenshot()

        if self.skip_wait or common_screen_state.in_secondary_ui(self.ctx, screen, self.target.tab.cn):
            return self.round_success()
        else:
            return self.round_retry('未在画面 %s' % self.target.tab.cn, wait=1)

    @node_from(from_name='等待画面加载')
    @operation_node(name='选择')
    def choose(self) -> OperationRoundResult:
        screen = self.screenshot()
        area = self.ctx.screen_loader.get_area('星际和平指南', '分类列表')

        # 下方的小文本可以区分花萼金/赤
        result = self.round_by_ocr_and_click(screen, self.target.remark_in_game, area=area)
        if result.is_success:
            return self.round_success(result.status, wait=1)

        result = self.round_by_ocr_and_click(screen, self.target.cn, area=area)
        if result.is_success:
            return self.round_success(result.status, wait=1)

        log.info('生存索引中未找到 %s 尝试滑动', self.target.cn)
        # 没有目标时候看要往哪个方向滚动
        other_before_target: bool = True  # 由于这里每次打开都是在最顶端 所以应该只需往下滑就好了

        point_from = area.rect.center
        point_to = point_from + (Point(0, -200) if other_before_target else Point(0, 200))
        self.ctx.controller.drag_to(point_to, point_from)
        return self.round_retry(result.status, wait=1)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_ocr()
    ctx.start_running()

    tab = ctx.guide_data.best_match_tab_by_name('生存索引')
    category = ctx.guide_data.best_match_category_by_name('侵蚀隧洞', tab)

    op = GuideChooseCategory(ctx, category)
    op.execute()


if __name__ == '__main__':
    __debug()

