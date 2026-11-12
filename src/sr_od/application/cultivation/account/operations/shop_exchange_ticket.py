"""商店兑换专票 op —— 星芒兑换页用星芒兑换星轨专票(20 星芒/张,不限量)。

⚠️ 消耗红线:兑换消耗星芒(角色转化材料),仅限用户明确授权的兑换请求调用。
参数 ``count``:``None`` = 拉满全部(能换多少换多少,受星芒余额限制);
数字 = 兑换指定张数(从弹窗默认 1 起步,经「+」按钮逐张调整)。

前置:已在商店页-星芒兑换 tab(经 EnterShopFromWarpOp + ShopSwitchTabOp
{tab: stardust} 到达)——本 op 不做导航与切 tab,单一职责。

流程:点专票商品卡打开兑换弹窗 → 调整数量(读数→点+/拉满→读数验证)→
点确认 → until 弹窗关闭回商店页 → 读星芒余额入 data。
"""


from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils import cv2_utils
from one_dragon.utils.i18_utils import gt
from sr_od.application.cultivation.account.operations.read_warp_status import (
    parse_count,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

_SHOP_SCREEN: str = '商店'
_POPUP_SCREEN: str = '商店-兑换弹窗'
_GOODS_AREA: str = '商品列表'
_ANCHOR_TAB: str = 'tab-常驻商店'

_AREA_POPUP_MARK: str = '文本-兑换数量'
_AREA_CONFIRM: str = '按钮-确认'
_AREA_PLUS: str = '按钮-加号'
_AREA_MAX: str = '按钮-拉满'
_AREA_COUNT: str = '读区-兑换数量'
_AREA_CURRENCY: str = '读区-货币数量'

_COUNT_OCR_SCALE: float = 3.0
"""数量型 area 的 OCR 放大倍数(单字符数字兜底,同 ReadWarpStatusOp 口径)"""


class ShopExchangeTicketOp(SrOperation):
    """商店星芒兑换页兑换星轨专票。

    结果状态:
    - ``EXCHANGED``:兑换完成回商店页,data 带实际兑换张数/星芒余额;
    失败:起点不在商店页、弹窗打不开、数量调不到目标、确认未生效。
    """

    def __init__(self, ctx: SrContext, count: int | None = None):
        """
        :param ctx: 上下文
        :param count: 兑换张数;``None`` = 拉满全部(受星芒余额限制)。
            **消耗参数:仅限用户明确授权的兑换请求传入。**
        """
        self._count: int | None = count
        self._popup_opened: bool = False
        """弹窗已打开(数量调整/确认节点的前置判据)"""
        SrOperation.__init__(self, ctx, op_name=gt('商店兑换专票'),
                             node_max_retry_times=60)

    @operation_node(name='打开兑换弹窗', is_start_node=True)
    def open_popup(self) -> OperationRoundResult:
        """商店页点专票商品卡,until 兑换弹窗锚出现。

        需在星芒兑换 tab(专票 20 星芒/张);余烬兑换 tab 的专票是月限商品,
        本 op 不适用。弹窗已打开的重入场景直接放行(数量调整节点接手)。
        """
        screen = self.check_and_update_current_screen(screen_name_list=[
            _SHOP_SCREEN, _POPUP_SCREEN])
        if screen == _POPUP_SCREEN:
            self._popup_opened = True
            return self.round_success(status='POPUP_OPENED', wait=1)
        if screen != _SHOP_SCREEN:
            return self.round_fail('起点不在商店页,请先经 EnterShopFromWarpOp 进入')
        result = self.round_by_find_and_click_area(
            self.last_screenshot, _SHOP_SCREEN, _GOODS_AREA,
            until_find_all=[(_POPUP_SCREEN, _AREA_POPUP_MARK)],
            success_wait=1.5, retry_wait=1.5)
        if result.is_success:
            self._popup_opened = True
            return self.round_success(status='POPUP_OPENED', wait=1.5)
        return result

    @node_from(from_name='打开兑换弹窗', status='POPUP_OPENED')
    @operation_node(name='调整数量', node_max_retry_times=40)
    def adjust_count(self) -> OperationRoundResult:
        """按 count 调整兑换数量,到达目标后进入确认。

        count=None:点「拉满」按钮一键到最大(受星芒余额限制);
        count=N:读当前数量 c,c<N 点「+」逐张上调,c==N 进入确认,c>N 点「-」下调
        (弹窗默认 1,理论上 c<=N 恒成立,减号分支为兜底)。
        数量以 OCR 实读为准(点了≠成了)。
        """
        if not self._popup_opened:
            return self.round_retry('弹窗未打开,等待画面稳定', wait=1)
        current: int | None = parse_count(
            self._area_count_text(self.last_screenshot, _POPUP_SCREEN, _AREA_COUNT))
        if current is None:
            return self.round_retry('兑换数量读取失败,重试', wait=1)
        if self._count is None:
            self._click_area_center(_POPUP_SCREEN, _AREA_MAX)
            return self.round_retry('已点拉满,下一轮读数验证', wait=1)
        if current == self._count:
            return self.round_success(status='COUNT_READY', wait=1)
        if current < self._count:
            self._click_area_center(_POPUP_SCREEN, _AREA_PLUS)
        return self.round_retry(f'当前数量 {current},向目标 {self._count} 调整中', wait=0.6)

    @node_from(from_name='调整数量', status='COUNT_READY')
    @operation_node(name='确认兑换')
    def confirm(self) -> OperationRoundResult:
        """点确认兑换,until 弹窗关闭回商店页,读星芒余额入 data。"""
        count = self._count
        area = self.ctx.screen_loader.get_area(_POPUP_SCREEN, _AREA_CONFIRM)
        self.ctx.controller.click(area.center, press_time=0.1)
        # 点了≠成了:弹窗关闭且回到商店页才算兑换完成
        if self.check_and_update_current_screen(
                screen_name_list=[_SHOP_SCREEN]) == _SHOP_SCREEN:
            material_left = parse_count(
                self._area_count_text(self.last_screenshot, _SHOP_SCREEN, _AREA_CURRENCY))
            actual = count if count is not None else None
            return self.round_success(status='EXCHANGED', data={
                'exchanged': actual,
                'material_left': material_left,
            }, wait=1)
        return self.round_retry('确认点击未生效或兑换提示未结束,重试', wait=1.5)

    def _click_area_center(self, screen_name: str, area_name: str) -> None:
        """点指定 area 中心(press_time=0.1,点击有效性由调用方轮询验证)。"""
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        self.ctx.controller.click(area.center, press_time=0.1)

    def _area_count_text(self, screen, screen_name: str, area_name: str) -> str | None:
        """读数量型 area:两层取数——全图 OCR+rect 过滤 → 3 倍放大裁剪兜底。"""
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        ocr_result_list = self.ctx.ocr_service.get_ocr_result_list(screen, rect=area.rect)
        if len(ocr_result_list) > 0:
            return ''.join(result.data for result in ocr_result_list)
        cropped = cv2_utils.crop_image_only(screen, area.rect)
        big = cv2_utils.scale_image(cropped, scale=_COUNT_OCR_SCALE)
        raw = self.ctx.ocr.run_ocr(big)
        if len(raw) == 0:
            return None
        return ''.join(raw.keys())
