from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guid_choose_tab import GuideChooseTab
from sr_od.interastral_peace_guide.guide_choose_category import GuideChooseCategory
from sr_od.interastral_peace_guide.guide_choose_mission import GuideChooseMission
from sr_od.interastral_peace_guide.guide_def import GuideMission
from sr_od.interastral_peace_guide.open_guide import GuideOpen
from sr_od.operations.sr_operation import SrOperation


class GuideTransport(SrOperation):

    def __init__(self, ctx: SrContext, mission: GuideMission):
        """
        使用指南进行传送
        """
        SrOperation.__init__(self, ctx, op_name='%s %s' % (gt('指南传送'), gt(mission.display_name, 'game')))

        self.mission: GuideMission = mission

    @operation_node(name='打开指南', is_start_node=True)
    def open_guide(self) -> OperationRoundResult:
        op = GuideOpen(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='打开指南')
    @operation_node(name='选择TAB')
    def choose_tab(self) -> OperationRoundResult:
        op = GuideChooseTab(self.ctx, self.mission.cate.tab)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择TAB')
    @operation_node(name='选择分类')
    def choose_category(self) -> OperationRoundResult:
        op = GuideChooseCategory(self.ctx, self.mission.cate)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择分类')
    @operation_node(name='选择副本')
    def choose_mission(self) -> OperationRoundResult:
        op = GuideChooseMission(self.ctx, self.mission)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择副本')
    @operation_node(name='等待加载', node_max_retry_times=20)
    def wait_at_last(self) -> OperationRoundResult:
        screen = self.screenshot()
        return self.round_by_find_area(screen, '星际和平指南', '等待加载-' + self.mission.cate.cn,
                                       retry_wait=1)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.init_ocr()
    ctx.start_running()

    tab = ctx.guide_data.best_match_tab_by_name('生存索引')
    category = ctx.guide_data.best_match_category_by_name('拟造花萼（金）', tab)
    mission = ctx.guide_data.best_match_mission_by_name('回忆之蕾', category, '城郊雪原')

    op = GuideTransport(ctx, mission)
    op.execute()


if __name__ == '__main__':
    __debug()
