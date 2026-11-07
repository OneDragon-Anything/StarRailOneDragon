"""任意画面 → 角色详情画面(不经过角色列表)的导航 operation。

角色养成系列 op 的入口步(与负责人对齐的四步分工):本 op 只负责到达详情画面,
停在进入时的默认角色;打开列表选角色、切等级画面、升级动作由后续 op 承担。

设计:
- 主路径:大世界右上角角色头像按钮直达详情(2026-11-07 实机验证——不经角色列表,
  详情显示头像对应的队伍角色);关闭该画面经右上按钮-关闭返回原场景(建档 goto_list
  记录为菜单,实测从大世界进入时落回大世界)。
- 链上画面:角色-详情(终点)/ 五个子页(光锥/行迹/遗器/星魂/信息——与详情同框,
  点 TAB-详情 切回)/ 大世界;不在链上的画面交给 BackToNormalWorldPlus 回大世界
  再走主路径(兜底 op 内含公告/各玩法退出分支,与 goto_treasures_lightward 同源)。
- 大世界为锁光标画面(screen 级 pc_alt=true),框架 find_and_click_area 按
  area.pc_alt 自动按住 Alt,代码无需手动处理。

画面证据:docs/game/screens/ 角色相关 doc;2026-11-07 实机:末日幻影选关 →关闭X
→ 大世界 →右上头像→ 详情 全链走通。
"""

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_DETAIL_SCREEN: str = '角色-详情'
_WORLD_SCREEN: str = '大世界'
_WORLD_BASIC_SCREEN: str = '大世界-普通'

# 角色域子页:画面名 → 子页 id_mark。子页顶部大标题随 TAB 变化
# (如「角色光锥」),与详情标题互斥命中,判定不混淆。
_SUB_TAB_SCREENS: list[tuple[str, str]] = [
    ('角色-光锥', '标题-角色光锥'),
    ('角色-行迹', '标题-行迹'),
    ('角色-遗器', '标题-遗器着装'),
    ('角色-星魂', '标题-星魂同调'),
    ('角色-信息', '标题-首次邂逅'),
]


class GotoCharacterDetail(SrOperation):
    """导航到角色详情画面(详情 TAB,不经过角色列表)。

    终点状态:角色-详情画面·详情 TAB·无弹窗,停留在进入时默认选中的角色
    (队伍头像对应角色/上次查看角色);选角色由后续 op 负责。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name=gt('前往角色详情'))

    @operation_node(name='识别当前画面', is_start_node=True, node_max_retry_times=5)
    def classify(self) -> OperationRoundResult:
        """按角色域链优先级识别当前位置,分流到对应接续节点。

        判序:子页 → 详情终点 → 大世界 → 其他(OFF_PATH 兜底);
        子页与详情标题互斥命中,先后不敏感,先判子页是表达"详情的变体态"语义。"""
        screen = self.last_screenshot

        for screen_name, area_name in _SUB_TAB_SCREENS:
            if self.round_by_find_area(screen, screen_name, area_name).is_success:
                return self.round_success(status='AT_SUB_TAB')

        if self.round_by_find_area(screen, _DETAIL_SCREEN, '标题-角色详情').is_success:
            return self.round_success(status='AT_DETAIL')

        if self.round_by_find_area(screen, _WORLD_SCREEN, '角色图标').is_success:
            return self.round_success(status='AT_WORLD')

        return self.round_success(status='OFF_PATH')

    @node_from(from_name='识别当前画面', status='OFF_PATH')
    @operation_node(name='回大世界', node_max_retry_times=3)
    def back_to_world(self) -> OperationRoundResult:
        """不在角色域链上:交给兜底 op 回大世界。

        延迟导入:BackToNormalWorldPlus 模块级导入会级联拉起货币战争全图,
        本 op 的导入不应被其传递依赖绑架(同 goto_treasures_lightward)。"""
        from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus

        op = BackToNormalWorldPlus(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_success(status='AT_WORLD', wait=1.5)
        return self.round_retry(wait=2)

    @node_from(from_name='识别当前画面', status='AT_SUB_TAB')
    @operation_node(name='子页切回详情', node_max_retry_times=6)
    def sub_tab_to_detail(self) -> OperationRoundResult:
        """子页(光锥/行迹/遗器/星魂/信息)点 TAB-详情 切回详情面板。

        until=按钮-属性详情:子页与详情同框、顶部标题在切换动画期两态都可能
        可见,不能作切换证据;「属性详情」按钮只在详情 TAB 面板出现。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _DETAIL_SCREEN, 'TAB-详情',
            until_find_all=[(_DETAIL_SCREEN, '按钮-属性详情')],
            pre_delay=0.5, success_wait=1, retry_wait=1.5,
        )

    @node_from(from_name='识别当前画面', status='AT_WORLD')
    @node_from(from_name='回大世界')
    @operation_node(name='大世界进详情', node_max_retry_times=6)
    def world_to_detail(self) -> OperationRoundResult:
        """大世界点右上角角色头像直达详情(不经过角色列表)。

        until=详情标题:头像按钮点击落空(动画期/焦点丢失)时重入轮重试;
        锁光标点击由框架按 area.pc_alt 自动按住 Alt。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _WORLD_BASIC_SCREEN, '右上图标-角色详情',
            until_find_all=[(_DETAIL_SCREEN, '标题-角色详情')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='大世界进详情')
    @node_from(from_name='识别当前画面', status='AT_DETAIL')
    @operation_node(name='详情收尾', node_max_retry_times=4)
    def detail_settle(self) -> OperationRoundResult:
        """到达验证收尾:详情标题 + 属性详情按钮双锚(详情 TAB 激活态)命中即成功。

        从子页/头像进入都落在本节点统一验证;若进入时有弹窗盖住锚点,
        重试轮持续等待(弹窗分支待实测暴露后在此补充处理)。"""
        screen = self.last_screenshot
        if (self.round_by_find_area(screen, _DETAIL_SCREEN, '标题-角色详情').is_success
                and self.round_by_find_area(screen, _DETAIL_SCREEN, '按钮-属性详情').is_success):
            return self.round_success()
        return self.round_retry('详情-等待画面', wait=1.5)
