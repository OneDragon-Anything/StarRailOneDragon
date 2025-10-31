from qfluentwidgets import FluentIcon

from one_dragon_qt.view.devtools.devtools_image_analysis_interface import DevtoolsImageAnalysisInterface
from one_dragon_qt.view.devtools.devtools_screen_manage_interface import DevtoolsScreenManageInterface
from one_dragon_qt.view.devtools.devtools_template_helper_interface import DevtoolsTemplateHelperInterface
from one_dragon_qt.view.devtools.devtools_image_analysis_interface import DevtoolsImageAnalysisInterface
from one_dragon_qt.widgets.pivot_navi_interface import PivotNavigatorInterface
from sr_od.context.sr_context import SrContext


class SrDevtoolsInterface(PivotNavigatorInterface):

    def __init__(self,
                 ctx: SrContext,
                 parent=None):
        self.ctx: SrContext = ctx
        PivotNavigatorInterface.__init__(self, object_name='sr_devtools_interface', parent=parent,
                                         nav_text_cn='开发工具', nav_icon=FluentIcon.DEVELOPER_TOOLS)

    def create_sub_interface(self):
        """
        创建下面的子页面
        :return:
        """
        self.add_sub_interface(DevtoolsImageAnalysisInterface(self.ctx))
        self.add_sub_interface(DevtoolsTemplateHelperInterface(self.ctx))
        self.add_sub_interface(DevtoolsScreenManageInterface(self.ctx))
        self.add_sub_interface(DevtoolsImageAnalysisInterface(self.ctx))
