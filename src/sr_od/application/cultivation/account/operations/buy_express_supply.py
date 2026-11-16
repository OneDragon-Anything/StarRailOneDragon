"""列车补给凭证(小月卡)充值 op —— 从任意画面到扫码支付弹窗。

职责:导航 手机菜单 → 商店 → 列车补给凭证详情页;可选打开扫码支付弹窗
(并可切微信渠道)。终点态供调用方转告用户扫码完成真实支付。

消耗门:
- ``open_qr=False``(默认)止步详情页,零消耗;
- ``open_qr=True`` 打开扫码弹窗(摆付款码),语义 = 发起购买,调用方须先向
  用户确认购买意愿;
- bot 永不代付:扫码支付由用户完成,本 op 不触碰「确认放弃本次支付?」以外
  的任何支付确认控件。

交互事实(画面建档见 ``docs/game/screens/store.md``):
- 菜单点「商店」有较长开屏过场(黑屏加载),核对到店节点按宽等待轮询;
- 详情页点「购买/续订 ¥30.00」直接弹扫码支付(无中间确认步;生效中按钮为「续订」,
  左侧栏凭证项角标显示剩余天数,且购买后该项会漂移到侧栏末位 —— 入口 area
  按整条侧栏建,文本命中即点击文字位置,不依赖槽位);
- 扫码弹窗默认支付宝码,「其他支付方式」切微信,「返回支付宝扫码」切回,
  两按钮同槽位互斥,可作渠道态判据;
- 月卡生效 ≥179 天时游戏禁购,购买/续订按钮可能不出现 → 显式失败并注明该可能。
"""

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen import screen_utils
from one_dragon.base.screen.screen_utils import FindAreaResultEnum
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.menu import phone_menu_const
from sr_od.operations.menu.click_phone_menu_item import ClickPhoneMenuItem
from sr_od.operations.menu.open_phone_menu import OpenPhoneMenu
from sr_od.operations.sr_operation import SrOperation

# 列车补给凭证与扫码支付弹窗都在推荐商店页(顶部「推荐商店」tab 选中态),
# 命名空间 = 商店-推荐商店 屏;商店 屏专指常驻商店·兑换商店菜单态
_STORE_SCREEN: str = '商店-推荐商店'

PAY_CHANNEL_ALIPAY: str = 'alipay'
PAY_CHANNEL_WECHAT: str = 'wechat'
_PAY_CHANNELS: set[str] = {PAY_CHANNEL_ALIPAY, PAY_CHANNEL_WECHAT}


def _area_hit(ctx: SrContext, screen, screen_name: str, area_name: str) -> bool:
    """区域命中判定(真值判定封装,缩短节点内分支)。"""
    return screen_utils.find_area(ctx, screen, screen_name, area_name) == FindAreaResultEnum.TRUE


class BuyExpressSupplyPassOp(SrOperation):
    """导航到列车补给凭证(小月卡)详情页,可选打开扫码支付弹窗摆付款码。
    起点:任意可控画面;终点:凭证详情页(open_qr=False)/扫码支付弹窗已
    打开且渠道就绪(open_qr=True,等用户扫码)。
    副作用:open_qr=True 语义为发起购买(真实支付由用户扫码完成,bot 不代付);
    False 为零消耗浏览。

    结果状态:
    - ``ON_PAGE``:已到详情页(open_qr=False,零消耗);
    - ``QR_OPENED``:扫码支付弹窗已打开且渠道就绪(open_qr=True),
      等用户扫码付款;
    失败:菜单/商店导航失败、商店内找不到凭证入口、购买按钮缺失
    (可能生效 ≥179 天禁购)、扫码弹窗渠道按钮异常。
    """

    def __init__(self, ctx: SrContext, open_qr: bool = False,
                 pay_channel: str = PAY_CHANNEL_ALIPAY):
        """
        :param ctx: 上下文
        :param open_qr: 是否打开扫码支付弹窗(True = 发起购买,摆付款码给用户)
        :param pay_channel: 支付渠道(PAY_CHANNEL_ALIPAY / PAY_CHANNEL_WECHAT),
            仅 open_qr=True 时生效;默认支付宝(游戏默认渠道)
        """
        if pay_channel not in _PAY_CHANNELS:
            raise ValueError(f'不支持的支付渠道: {pay_channel},可选 {_PAY_CHANNELS}')
        self._open_qr: bool = open_qr
        self._pay_channel: str = pay_channel
        SrOperation.__init__(self, ctx, op_name=gt('购买列车补给凭证'),
                             node_max_retry_times=20)

    @operation_node(name='打开菜单', is_start_node=True)
    def open_menu(self) -> OperationRoundResult:
        """保证手机菜单已展开(任意画面起始,内部含回大世界)。"""
        op = OpenPhoneMenu(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='打开菜单')
    @operation_node(name='点商店菜单项')
    def click_store(self) -> OperationRoundResult:
        """菜单项模板匹配点「商店」(语言无关,找不到会自动滚动菜单)。"""
        op = ClickPhoneMenuItem(self.ctx, phone_menu_const.STORE)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='点商店菜单项')
    @operation_node(name='核对到店')
    def check_store(self) -> OperationRoundResult:
        """画面级判定到店(顶栏 tab 双锚);开屏过场长,宽等待轮询。"""
        if _area_hit(self.ctx, self.last_screenshot, _STORE_SCREEN, 'tab-推荐商店') \
                and _area_hit(self.ctx, self.last_screenshot, _STORE_SCREEN, 'tab-常驻商店'):
            return self.round_success(status='IN_STORE', wait=1.5)
        return self.round_retry('商店未加载完成(tab 锚未命中),等待开屏过场', wait=2)

    @node_from(from_name='核对到店', status='IN_STORE')
    @operation_node(name='选列车补给凭证')
    def select_pass(self) -> OperationRoundResult:
        """进凭证详情页;已在页幂等;商店落在常驻商店时先切推荐商店。"""
        if _area_hit(self.ctx, self.last_screenshot, _STORE_SCREEN, '标题-列车补给凭证'):
            return self.round_success(
                status='ON_PAGE' if not self._open_qr else 'OPEN_QR', wait=0.5)
        if _area_hit(self.ctx, self.last_screenshot, _STORE_SCREEN, '入口-列车补给凭证'):
            area = self.ctx.screen_loader.get_area(_STORE_SCREEN, '入口-列车补给凭证')
            self.ctx.controller.click(area.rect.center)
            return self.round_retry('已点凭证入口,等详情页加载', wait=1.5)
        if _area_hit(self.ctx, self.last_screenshot, _STORE_SCREEN, 'tab-推荐商店'):
            area = self.ctx.screen_loader.get_area(_STORE_SCREEN, 'tab-推荐商店')
            self.ctx.controller.click(area.rect.center)
            return self.round_retry('商店落在常驻商店,已切推荐商店', wait=1.5)
        return self.round_fail('商店内未找到列车补给凭证入口(左侧栏可能随版本轮换,需重验建档)')

    @node_from(from_name='选列车补给凭证', status='OPEN_QR')
    @operation_node(name='打开扫码支付')
    def open_qr(self) -> OperationRoundResult:
        """点「购买/续订 ¥30.00」打开扫码弹窗;按钮缺失先判禁购态再报失败。

        按钮文案随凭证状态二态:无生效凭证 =「购买」,生效中 =「续订」
        (同槽位,OCR 二选一)。
        """
        if _area_hit(self.ctx, self.last_screenshot, _STORE_SCREEN, '标题-扫码支付'):
            return self.round_success(status='QR_SHOWN', wait=1)
        buy_area_name: str | None = None
        for name in ('按钮-购买', '按钮-续订'):
            if _area_hit(self.ctx, self.last_screenshot, _STORE_SCREEN, name):
                buy_area_name = name
                break
        if buy_area_name is None:
            return self.round_fail('未找到购买/续订按钮(月卡生效 ≥179 天时游戏禁购,或页面异常)')
        area = self.ctx.screen_loader.get_area(_STORE_SCREEN, buy_area_name)
        self.ctx.controller.click(area.rect.center)
        return self.round_retry(f'已点{buy_area_name},等扫码弹窗', wait=2)

    @node_from(from_name='打开扫码支付', status='QR_SHOWN')
    @operation_node(name='核对支付渠道')
    def check_channel(self) -> OperationRoundResult:
        """确保扫码弹窗停留在调用方要的渠道(支付宝默认,微信需切一次)。"""
        alipay_state = _area_hit(self.ctx, self.last_screenshot,
                                 _STORE_SCREEN, '按钮-其他支付方式')
        wechat_state = _area_hit(self.ctx, self.last_screenshot,
                                 _STORE_SCREEN, '按钮-返回支付宝扫码')
        if self._pay_channel == PAY_CHANNEL_ALIPAY and alipay_state:
            return self.round_success(status='QR_OPENED', wait=0.5)
        if self._pay_channel == PAY_CHANNEL_WECHAT:
            if wechat_state:
                return self.round_success(status='QR_OPENED', wait=0.5)
            if alipay_state:
                area = self.ctx.screen_loader.get_area(_STORE_SCREEN, '按钮-其他支付方式')
                self.ctx.controller.click(area.rect.center)
                return self.round_retry('已切微信支付,等二维码刷新', wait=1.5)
        return self.round_fail('扫码弹窗渠道按钮均未命中(弹窗异常,需现场核查)')
