"""无名客的荣勋(大月卡)购买 op —— 从任意画面到购买入口/扫码支付弹窗。

职责:导航 手机菜单 → 无名勋礼主面板(默认奖励 tab),处理版本周期首进的
推广页/等级加速弹窗前置链;可选点击「解锁无名客的荣勋」打开付款弹窗。
终点态供调用方转告用户扫码完成真实支付。

消耗门:
- ``open_pay=False``(默认)止步购买入口,零消耗;
- ``open_pay=True`` 点击购买按钮(摆付款码),语义 = 发起购买,调用方须先
  向用户确认购买意愿;
- bot 永不代付:扫码支付由用户完成,本 op 不触碰「确认放弃本次支付?」以外
  的任何支付确认控件。

交互事实(画面建档见 ``docs/game/screens/无名勋礼.md``):
- 版本周期内第一次进无名勋礼先落整屏「购买推广页」,点「开启无名勋礼」是
  查看/继续语义不会付费(用户裁决,2026-08-27 实机走通退出链);经
  「等级加速弹窗」(点弹窗内提示位关闭,点外部无效)才到主面板;
- 未购买态购买入口唯一:主面板奖励 tab 右下「解锁无名客的荣勋」
  (上方伴生「解锁立即获得」提示条,双锚判未购买态);已购买态该入口消失;
- 付款弹窗按与商店扫码支付弹窗同构建模(同一游戏支付组件,全屏居中):
  默认支付宝码,「其他支付方式」切微信,「返回支付宝扫码」切回 —— 该段
  建档/交互待实机验证后回填(2026-11-12 摸索时未发起购买)。
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

_HONOR_SCREEN: str = '无名勋礼'
# 支付弹窗 area 建在商店屏(同款全屏支付组件);跨屏文本 area 按 rect 内容命中,
# 不依赖画面 id_mark。待实机验证无名勋礼场景下坐标一致后回填独立建档。
_PAY_DIALOG_SCREEN: str = '商店'

PAY_CHANNEL_ALIPAY: str = 'alipay'
PAY_CHANNEL_WECHAT: str = 'wechat'
_PAY_CHANNELS: set[str] = {PAY_CHANNEL_ALIPAY, PAY_CHANNEL_WECHAT}


def _area_hit(ctx: SrContext, screen, screen_name: str, area_name: str) -> bool:
    """区域命中判定(真值判定封装,缩短节点内分支)。"""
    return screen_utils.find_area(ctx, screen, screen_name, area_name) == FindAreaResultEnum.TRUE


class BuyNamelessHonorPassOp(SrOperation):
    """导航到无名勋礼购买入口,可选点击购买打开付款弹窗。

    结果状态:
    - ``AT_ENTRY``:已到主面板且未购买态购买入口可见(open_pay=False,零消耗);
    - ``PAY_OPENED``:付款弹窗已打开且渠道就绪(open_pay=True),
      等用户扫码付款;
    失败:菜单/无名勋礼导航失败、周期首进退出链异常、未购买态入口缺失
    (可能本期已解锁付费轨)、付款弹窗渠道按钮异常。
    """

    def __init__(self, ctx: SrContext, open_pay: bool = False,
                 pay_channel: str = PAY_CHANNEL_ALIPAY):
        """
        :param ctx: 上下文
        :param open_pay: 是否点击购买(True = 发起购买,摆付款码给用户)
        :param pay_channel: 支付渠道(PAY_CHANNEL_ALIPAY / PAY_CHANNEL_WECHAT),
            仅 open_pay=True 时生效;默认支付宝(与商店支付弹窗同构假设)
        """
        if pay_channel not in _PAY_CHANNELS:
            raise ValueError(f'不支持的支付渠道: {pay_channel},可选 {_PAY_CHANNELS}')
        self._open_pay: bool = open_pay
        self._pay_channel: str = pay_channel
        SrOperation.__init__(self, ctx, op_name=gt('购买无名客的荣勋'),
                             node_max_retry_times=20)

    @operation_node(name='打开菜单', is_start_node=True)
    def open_menu(self) -> OperationRoundResult:
        """保证手机菜单已展开(任意画面起始,内部含回大世界)。"""
        op = OpenPhoneMenu(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='打开菜单')
    @operation_node(name='点无名勋礼菜单项')
    def click_honor(self) -> OperationRoundResult:
        """菜单项模板匹配点「无名勋礼」(语言无关,找不到会自动滚动菜单)。"""
        op = ClickPhoneMenuItem(self.ctx, phone_menu_const.NAMELESS_HONOR)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='点无名勋礼菜单项')
    @operation_node(name='核对到主面板')
    def check_honor(self) -> OperationRoundResult:
        """推进到主面板:周期首进先落推广页,经等级加速弹窗再到主面板。

        三分支逐帧重识别(点击可能不落地);推广页点「开启无名勋礼」为
        查看/继续语义(用户裁决,不付费);加速弹窗必须点弹窗内
        「点击空白处关闭」提示位,点弹窗外部无效。
        """
        if _area_hit(self.ctx, self.last_screenshot, _HONOR_SCREEN, '标识-无名勋礼') \
                and _area_hit(self.ctx, self.last_screenshot, _HONOR_SCREEN, '按钮-规则说明'):
            return self.round_success(status='ON_PANEL', wait=1)
        if _area_hit(self.ctx, self.last_screenshot, '无名勋礼-购买推广页', '按钮-开启无名勋礼'):
            area = self.ctx.screen_loader.get_area('无名勋礼-购买推广页', '按钮-开启无名勋礼')
            self.ctx.controller.click(area.rect.center)
            return self.round_retry('周期首进推广页,已点开启', wait=2)
        if _area_hit(self.ctx, self.last_screenshot, '无名勋礼-等级加速弹窗', '标识-等级加速'):
            area = self.ctx.screen_loader.get_area('无名勋礼-等级加速弹窗', '按钮-点击空白处关闭')
            self.ctx.controller.click(area.rect.center)
            return self.round_retry('等级加速弹窗,已点提示位关闭', wait=2)
        return self.round_retry('无名勋礼未加载完成(三态锚均未命中),等待', wait=2)

    @node_from(from_name='核对到主面板', status='ON_PANEL')
    @operation_node(name='核对购买入口')
    def check_purchase_entry(self) -> OperationRoundResult:
        """判定未购买态购买入口(按钮+提示条双锚);已购态两锚均消失。"""
        button_hit = _area_hit(self.ctx, self.last_screenshot,
                               _HONOR_SCREEN, '按钮-解锁无名客的荣勋')
        hint_hit = _area_hit(self.ctx, self.last_screenshot,
                             _HONOR_SCREEN, '标识-解锁立即获得')
        if button_hit and hint_hit:
            if not self._open_pay:
                return self.round_success(status='AT_ENTRY', wait=0.5)
            return self.round_success(status='ENTRY_READY', wait=0.5)
        if not button_hit and not hint_hit:
            return self.round_fail('未找到购买入口(可能本期已解锁付费轨,或面板异常)')
        return self.round_retry('购买入口单锚命中(另一锚未识别),重试', wait=1)

    @node_from(from_name='核对购买入口', status='ENTRY_READY')
    @operation_node(name='打开付款弹窗')
    def open_pay(self) -> OperationRoundResult:
        """点「解锁无名客的荣勋」发起购买(调用方须已获用户同意)。

        弹窗形态按与商店扫码支付弹窗同构建模,待实机验证后回填。
        """
        if _area_hit(self.ctx, self.last_screenshot, _PAY_DIALOG_SCREEN, '标题-扫码支付'):
            return self.round_success(status='PAY_SHOWN', wait=1)
        area = self.ctx.screen_loader.get_area(_HONOR_SCREEN, '按钮-解锁无名客的荣勋')
        self.ctx.controller.click(area.rect.center)
        return self.round_retry('已点购买按钮,等付款弹窗', wait=2)

    @node_from(from_name='打开付款弹窗', status='PAY_SHOWN')
    @operation_node(name='核对支付渠道')
    def check_channel(self) -> OperationRoundResult:
        """确保付款弹窗停留在调用方要的渠道(支付宝默认,微信需切一次)。"""
        alipay_state = _area_hit(self.ctx, self.last_screenshot,
                                 _PAY_DIALOG_SCREEN, '按钮-其他支付方式')
        wechat_state = _area_hit(self.ctx, self.last_screenshot,
                                 _PAY_DIALOG_SCREEN, '按钮-返回支付宝扫码')
        if self._pay_channel == PAY_CHANNEL_ALIPAY and alipay_state:
            return self.round_success(status='PAY_OPENED', wait=0.5)
        if self._pay_channel == PAY_CHANNEL_WECHAT:
            if wechat_state:
                return self.round_success(status='PAY_OPENED', wait=0.5)
            if alipay_state:
                area = self.ctx.screen_loader.get_area(_PAY_DIALOG_SCREEN, '按钮-其他支付方式')
                self.ctx.controller.click(area.rect.center)
                return self.round_retry('已切微信支付,等二维码刷新', wait=1.5)
        return self.round_fail('付款弹窗渠道按钮均未命中(弹窗形态待实机核查或异常)')
