"""角色详情画面左侧 TAB 切换的通用 operation(详情/光锥/行迹/遗器/星魂/信息)。

角色养成系列 op 第三步(与负责人对齐的四步分工):选角色后切到目标 TAB 画面
(如「详情」TAB = 等级显示与升级入口所在);第四步升级动作由后续 op 承担。

本 op 只覆盖**无遮挡可直接点击**的情况(与负责人对齐:遮挡态分支后续补):
- 已知遮挡态「列表浮层开着」在入口核对显式失败(列表开着时点击会被浮层
  拦截,需先收列表——收列表动作归 SelectCharacterOp 收尾,调用方保证);
- 其他未预期遮挡(弹窗等)由 until 验证兜住:点击后目标锚不出现会重试,
  超预算显式失败,不盲点。

到达验证锚 = 各子页画面建档的 id_mark(顶部大标题随 TAB 变化,六态互斥);
「详情」TAB 无独立画面建档,锚用「按钮-属性详情」(详情面板独有按钮,
goto_character_detail 收尾同款)。点击 area 坐标单一真相源在
screen_info「角色-详情」的 TAB-* area。
"""

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_DETAIL_SCREEN: str = '角色-详情'
_LIST_SCREEN: str = '角色-列表'

# tab 名 → (点击 area 名, 到达验证锚(画面, area))
# 到达锚必须目标 TAB 独有:「详情」用属性详情按钮(其余 TAB 面板无此按钮),
# 其余五 TAB 用各自子页 id_mark(标题随 TAB 变化,详情态不命中子页锚)
_TAB_ANCHORS: dict[str, tuple[str, tuple[str, str]]] = {
    '详情': ('TAB-详情', (_DETAIL_SCREEN, '按钮-属性详情')),
    '光锥': ('TAB-光锥', ('角色-光锥', '标题-角色光锥')),
    '行迹': ('TAB-行迹', ('角色-行迹', '标题-行迹')),
    '遗器': ('TAB-遗器', ('角色-遗器', '标题-遗器着装')),
    '星魂': ('TAB-星魂', ('角色-星魂', '标题-星魂同调')),
    '信息': ('TAB-信息', ('角色-信息', '标题-首次邂逅')),
}

# 子页画面 → 子页 id_mark(判定"在角色域"用,与 TAB 名解耦——域判定不关心具体哪个 TAB)
_SUB_TAB_SCREENS: list[tuple[str, str]] = [
    ('角色-光锥', '标题-角色光锥'),
    ('角色-行迹', '标题-行迹'),
    ('角色-遗器', '标题-遗器着装'),
    ('角色-星魂', '标题-星魂同调'),
    ('角色-信息', '标题-首次邂逅'),
]


class SwitchCharacterTabOp(SrOperation):
    """在角色详情画面切换左侧 TAB 到目标页。

    终点状态:目标 TAB 激活(到达验证锚可见)。前置:角色详情画面(列表
    已收起)——由 GotoCharacterDetail / SelectCharacterOp 保证;遮挡态
    与域外起点显式失败,不替调用方补导航。"""

    def __init__(self, ctx: SrContext, tab_name: str):
        """
        :param ctx: 上下文
        :param tab_name: 目标 TAB 名(详情/光锥/行迹/遗器/星魂/信息)
        """
        self.tab_name: str = tab_name.strip()
        if self.tab_name not in _TAB_ANCHORS:
            raise ValueError(f'未知 TAB 名: {tab_name}(可选: {"/".join(_TAB_ANCHORS)})')
        SrOperation.__init__(self, ctx, op_name=gt('切换角色页签') + '-' + self.tab_name)

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """入口核对与快路径分流:列表遮挡 → 失败;已在目标 TAB → 直接结束;
        在角色域 → 去换 tab;域外 → 失败(前置导航归调用方)。"""
        screen = self.last_screenshot

        if self.round_by_find_area(screen, _LIST_SCREEN, '标题-角色列表').is_success:
            return self.round_fail('列表浮层开着(遮挡态,本 op 未覆盖):先由调用方收列表')

        anchor_screen, anchor_area = _TAB_ANCHORS[self.tab_name][1]
        if self.round_by_find_area(screen, anchor_screen, anchor_area).is_success:
            return self.round_success(status='ALREADY')

        in_domain = self.round_by_find_area(
            screen, _DETAIL_SCREEN, '按钮-属性详情').is_success
        if not in_domain:
            for screen_name, area_name in _SUB_TAB_SCREENS:
                if self.round_by_find_area(screen, screen_name, area_name).is_success:
                    in_domain = True
                    break
        if in_domain:
            return self.round_success(status='IN_DOMAIN')
        return self.round_fail('不在角色详情画面(前置:前往角色详情 / 选择角色 op)')

    @node_from(from_name='入口核对', status='IN_DOMAIN')
    @operation_node(name='切换页签', node_max_retry_times=6)
    def switch_tab(self) -> OperationRoundResult:
        """点击目标 TAB,until=到达验证锚。

        until 命中 = 目标 TAB 激活 → 本节点 success 无出边,op 结束;
        点击落空(动画期/被遮挡)时重入轮重试,超预算显式失败。"""
        screen = self.last_screenshot
        click_area, (anchor_screen, anchor_area) = _TAB_ANCHORS[self.tab_name]
        result = self.round_by_find_and_click_area(
            screen, _DETAIL_SCREEN, click_area,
            until_find_all=[(anchor_screen, anchor_area)],
            pre_delay=0.5, success_wait=1, retry_wait=1.5,
        )
        if result.is_success:
            log.info('切换页签: %s 到达验证通过', self.tab_name)
        return result
