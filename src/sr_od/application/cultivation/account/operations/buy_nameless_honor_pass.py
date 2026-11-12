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
- 未购买态购买入口唯一:主面板奖励 tab 右下「解锁无名客的荣勋」;**未购买态
  判据 = 「解锁立即获得」提示条**(已购买态按钮仍在但提示条消失,2026-11-12
  实购后实证);
- 主面板点「解锁无名客的荣勋」→ 落「无名勋礼-购买档位页」(2026-11-12 实机):
  两档价格卡(荣勋￥68.00 / 奖章￥128.00,原价￥146 划线),op 点荣勋档 ¥68 按钮
  → 扫码支付弹窗;
- 扫码支付弹窗(2026-11-12 实机,挂「无名勋礼-购买档位页」屏建档):渠道为
  并排 tab(支付宝[推荐] | 微信支付),默认支付宝码;与商店版「其他支付方式」
  按钮不同构,当前渠道以二维码下方标注判(支付宝态=「支付宝扫码」/微信态=
  「微信扫码」,同位互斥);二维码有时效,过期态中央出刷新按钮点击重出码;
- 支付完成后(用户扫码)落「获得物品:星琼×680」弹窗(点击空白处关闭),
  回主面板即已购买态。
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
# 购买档位页与其上的扫码支付弹窗 area 同屏挂载(弹窗只在档位页上出现)
_PURCHASE_PAGE_SCREEN: str = '无名勋礼-购买档位页'

PAY_CHANNEL_ALIPAY: str = 'alipay'
PAY_CHANNEL_WECHAT: str = 'wechat'
_PAY_CHANNELS: set[str] = {PAY_CHANNEL_ALIPAY, PAY_CHANNEL_WECHAT}


def _area_hit(ctx: SrContext, screen, screen_name: str, area_name: str) -> bool:
    """区域命中判定(真值判定封装,缩短节点内分支)。"""
    return screen_utils.find_area(ctx, screen, screen_name, area_name) == FindAreaResultEnum.TRUE


class BuyNamelessHonorPassOp(SrOperation):
    """导航到无名勋礼(大月卡)购买入口,可选点击购买打开付款弹窗摆付款码。
    起点:任意可控画面;终点:主面板购买入口可见(open_pay=False)/付款弹窗
    已打开且渠道就绪(open_pay=True,等用户扫码)。
    副作用:open_pay=True 语义为发起购买(真实支付由用户扫码完成,bot 不代付);
    False 为零消耗浏览。

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
        # 奖励 tab 切换尝试标记(执行期,单次运行内):True=已点过 tab-奖励——
        # 主面板会记忆上次离开的 tab,进面板先无条件点一次奖励 tab(幂等,已在
        # 奖励 tab 时点击无变化),点过仍无购买入口才能判定「入口缺失」
        self._reward_tab_clicked: bool = False
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
        """确保在奖励 tab 并判定未购买态购买入口。

        未购买态判据 =「解锁立即获得」提示条(唯一可靠):已购买态(2026-11-12
        实证)购买按钮仍在(可去档位页升奖章档)但提示条消失,故按钮不作判据。
        """
        hint_hit = _area_hit(self.ctx, self.last_screenshot,
                             _HONOR_SCREEN, '标识-解锁立即获得')
        if hint_hit:
            if not self._open_pay:
                return self.round_success(status='AT_ENTRY', wait=0.5)
            return self.round_success(status='ENTRY_READY', wait=0.5)
        if self._reward_tab_clicked:
            if _area_hit(self.ctx, self.last_screenshot,
                         _HONOR_SCREEN, '按钮-解锁无名客的荣勋'):
                return self.round_fail('已处于已购买态(按钮在但提示条消失),无需购买荣勋档')
            return self.round_fail('奖励 tab 下未找到购买入口(面板异常,现场核查)')
        # 主面板记忆上次离开的 tab,先切奖励 tab 再判购买入口
        area = self.ctx.screen_loader.get_area(_HONOR_SCREEN, 'tab-奖励')
        self.ctx.controller.click(area.rect.center)
        self._reward_tab_clicked = True
        return self.round_retry('已点奖励 tab,等购买入口出现', wait=1.5)

    @node_from(from_name='核对购买入口', status='ENTRY_READY')
    @operation_node(name='打开购买档位页')
    def open_pay(self) -> OperationRoundResult:
        """点主面板「解锁无名客的荣勋」→ 落购买档位页(2026-11-12 实机:
        点解锁按钮不直接弹扫码,先落「无名勋礼-购买档位页」两档价格卡)。
        """
        if _area_hit(self.ctx, self.last_screenshot,
                     '无名勋礼-购买档位页', '文本-无名客的奖章') \
                and _area_hit(self.ctx, self.last_screenshot,
                              '无名勋礼-购买档位页', '按钮-购买荣勋68'):
            return self.round_success(status='PURCHASE_PAGE', wait=1)
        area = self.ctx.screen_loader.get_area(_HONOR_SCREEN, '按钮-解锁无名客的荣勋')
        self.ctx.controller.click(area.rect.center)
        return self.round_retry('已点购买按钮,等档位页加载', wait=2)

    @node_from(from_name='打开购买档位页', status='PURCHASE_PAGE')
    @operation_node(name='选荣勋档')
    def select_honor(self) -> OperationRoundResult:
        """点「￥68.00」(荣勋档)发起支付 —— 奖章档(￥128)是更高消费档,
        op 只建模识别永不点击。
        """
        if _area_hit(self.ctx, self.last_screenshot, _PURCHASE_PAGE_SCREEN, '标题-扫码支付'):
            return self.round_success(status='PAY_SHOWN', wait=1)
        area = self.ctx.screen_loader.get_area('无名勋礼-购买档位页', '按钮-购买荣勋68')
        self.ctx.controller.click(area.rect.center)
        return self.round_retry('已点￥68.00(荣勋档),等扫码弹窗', wait=2)

    @node_from(from_name='选荣勋档', status='PAY_SHOWN')
    @operation_node(name='核对支付渠道')
    def check_channel(self) -> OperationRoundResult:
        """确保扫码弹窗停留在调用方要的渠道(默认支付宝,微信需点 tab 切一次)。

        无名勋礼弹窗渠道为并排 tab(支付宝[推荐] | 微信支付),与商店版
        「其他支付方式」按钮不同构;当前渠道判据 = 二维码下方标注,两文本
        同位互斥(2026-11-12 实证):支付宝态 =「支付宝扫码」,微信态 =「微信扫码」。
        """
        if not _area_hit(self.ctx, self.last_screenshot,
                         _PURCHASE_PAGE_SCREEN, '标题-扫码支付'):
            return self.round_fail('扫码支付弹窗未出现(弹窗异常,现场核查)')
        alipay_qr = _area_hit(self.ctx, self.last_screenshot,
                              _PURCHASE_PAGE_SCREEN, '文本-支付宝扫码')
        wechat_qr = _area_hit(self.ctx, self.last_screenshot,
                              _PURCHASE_PAGE_SCREEN, '文本-微信扫码')
        if self._pay_channel == PAY_CHANNEL_ALIPAY and alipay_qr:
            return self.round_success(status='PAY_OPENED', wait=0.5)
        if self._pay_channel == PAY_CHANNEL_WECHAT and wechat_qr:
            return self.round_success(status='PAY_OPENED', wait=0.5)
        tab_name = 'tab-支付宝' if self._pay_channel == PAY_CHANNEL_ALIPAY else 'tab-微信支付'
        area = self.ctx.screen_loader.get_area(_PURCHASE_PAGE_SCREEN, tab_name)
        self.ctx.controller.click(area.rect.center)
        return self.round_retry(f'当前非目标渠道,已点{tab_name},等二维码刷新', wait=1.5)
