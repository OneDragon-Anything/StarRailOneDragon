"""商店导航:任意画面 → 常驻商店·兑换商店列表页。

效果:一条无参导航链(画面判定 → 开菜单 → 点入口-商店 → 点tab-常驻商店),
画面停在兑换商店列表页;落点子 tab 不指定(菜单会记住上次子 tab),业务
方用 [ShopSwitchTabOp](shop_switch_tab.py) 自行切换——「去哪个子 tab」
是业务决策,不进导航 op。

用途:
- app 导航段复用(一处维护);
- MCP agent 单独调用即可到兑换商店(无参构造,registry 可直接实例化;
  对照 ClickPhoneMenuItem 的 PhoneMenuItem 参数无法经 MCP 构造)。

流转(全部点击带 until 转移验证,点了 ≠ 成了):
    [任意画面] --画面级判定(已在商店→跳到末跳)--> [非商店]
      --OpenPhoneMenu(内部:在菜单=成功/大世界=按菜单键/其他=兜底回大世界)--> 菜单
      --点 入口-商店, until tab-常驻商店 可见(过场 ≤9s,建档 8-10s)--> 商店·推荐页
      --点 tab-常驻商店, until tab-余烬兑换 可见--> 商店·兑换商店列表页 [结束]

健壮性:「点击恒成功但锚恒不出现」在框架里是 round_wait 无界(WAIT 不烧
重试预算)——两个点击跳各自设连等封顶,超限诚实 FAIL,不挂死一条龙。

红线:无真实消耗、无不可逆操作(纯导航)。
"""

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.menu.open_phone_menu import OpenPhoneMenu
from sr_od.operations.sr_operation import SrOperation

_STORE_SCREEN: str = '商店'
_MENU_SCREEN: str = '菜单'
_ENTER_MAX_WAIT_ROUNDS: int = 12
"""入口-商店点击后商店页未出现的连等封顶(轮;每轮 ≥1.5s,覆盖建档 8-10s
过场再留余量;超限 = 点击未生效或被遮挡,继续等无意义)"""
_SWITCH_MAX_WAIT_ROUNDS: int = 12
"""tab-常驻商店点击后兑换列表页未出现的连等封顶(同上)"""


class OpenExchangeShop(SrOperation):
    """从任意画面导航到常驻商店·兑换商店列表页。
    起点:任意画面(已在商店页时直接跳到末跳,幂等);终点:商店页兑换商店
    列表页(子 tab 为菜单记忆态,未指定)。
    无参数、无消耗。

    结果状态:
    - ``ARRIVED``:已到兑换商店列表页;
    失败:画面识别失败 / 打开菜单失败 / 点击后锚超时未出现(连等封顶)。
    """

    def __init__(self, ctx: SrContext):
        """
        :param ctx: 上下文
        """
        self._enter_click_rounds: int = 0
        """入口-商店已点后的连等轮数(达 _ENTER_MAX_WAIT_ROUNDS 判点击未生效)"""
        self._switch_click_rounds: int = 0
        """tab-常驻商店已点后的连等轮数(达 _SWITCH_MAX_WAIT_ROUNDS 同上)"""
        SrOperation.__init__(self, ctx, op_name=gt('打开兑换商店'),
                             node_max_retry_times=10)

    @operation_node(name='到达商店判定', is_start_node=True)
    def check_screen(self) -> OperationRoundResult:
        """入口画面级判定:已在商店页 → 直接末跳(幂等);否则经菜单前往。

        不做逐 area 试命中推断,画面级判定后交 OpenPhoneMenu 兜底任意起点。
        """
        screen = self.check_and_update_current_screen(
            screen_name_list=[_STORE_SCREEN])
        if screen == _STORE_SCREEN:
            return self.round_success(status='ON_STORE_PAGE')
        op = OpenPhoneMenu(self.ctx)
        result = op.execute()
        if not result.success:
            return self.round_fail(f'打开菜单失败: {result.status}')
        return self.round_success(status='MENU_READY', wait=1)

    @node_from(from_name='到达商店判定', status='MENU_READY')
    @operation_node(name='进商店')
    def enter_store(self) -> OperationRoundResult:
        """点菜单 入口-商店,until 商店页顶栏(tab-常驻商店)出现。

        过场期间点击目标消失走 retry 预算(≤9s 过场,10 次预算足够);
        点击持续生效但锚不出现走连等封顶(防 WAIT 无界挂死)。
        """
        if self.node_clicked:
            self._enter_click_rounds += 1
            if self._enter_click_rounds > _ENTER_MAX_WAIT_ROUNDS:
                return self.round_fail('已点入口-商店但商店页未出现(连等封顶)')
        return self.round_by_find_and_click_area(
            self.last_screenshot, _MENU_SCREEN, '入口-商店',
            until_find_all=[(_STORE_SCREEN, 'tab-常驻商店')],
            pre_delay=0.5, success_wait=1.5, retry_wait=1.5)

    @node_from(from_name='到达商店判定', status='ON_STORE_PAGE')
    @node_from(from_name='进商店')
    @operation_node(name='切常驻商店')
    def switch_to_exchange(self) -> OperationRoundResult:
        """点 tab-常驻商店进兑换商店,until 兑换子 tab(tab-余烬兑换)出现。

        推荐页/兑换页顶栏均有 tab-常驻商店(点击幂等:已在兑换页时锚立即
        满足);tab-余烬兑换 未选中白字常显,作「兑换列表页已打开」证据。
        """
        if self.node_clicked:
            self._switch_click_rounds += 1
            if self._switch_click_rounds > _SWITCH_MAX_WAIT_ROUNDS:
                return self.round_fail('已点tab-常驻商店但兑换列表页未出现(连等封顶)')
        result = self.round_by_find_and_click_area(
            self.last_screenshot, _STORE_SCREEN, 'tab-常驻商店',
            until_find_all=[(_STORE_SCREEN, 'tab-余烬兑换')],
            pre_delay=0.5, success_wait=1.5, retry_wait=1.5)
        if result.is_success:
            # 终态语义化:对外契约状态 ARRIVED(内部 helper 成功态=区域名,不外泄)
            return self.round_success(status='ARRIVED', wait=1)
        return result
