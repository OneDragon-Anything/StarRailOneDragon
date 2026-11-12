"""商店内切换兑换 tab —— 余烬兑换 / 星芒兑换。

商店默认打开在星芒兑换 tab(角色转化材料「未熄的星芒」,官方英文
Undying Starlight:换票 20 星芒/张,不限量);余烬兑换 tab 是光锥转化
材料页(「未熄的余烬」,官方英文 Undying Embers:换票 90 余烬/张,
**每月限量 5 张**)。

切换验证锚 = 目标 tab 的**选中态模板**(选中 tab 白亮字、未选中灰字,
模板按颜色可区分)——旧方案「第 1 行第 4 列槽位商品互斥文本」已废弃:
版本内商品增删会把卡片挤后移(实测 2026-11-12 该槽位从冒险记录变为
凝缩以太),商品文本锚随列表内容漂移;tab 选中态是页面结构元素,
与商品列表内容无关。实机证实切 tab 后商品列表自动回顶。

入口从跃迁页进商店见 [EnterShopFromWarpOp](enter_shop_from_warp.py)。
"""

import re

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

TAB_EMBERS: str = 'embers'
"""余烬兑换 tab(光锥转化材料「未熄的余烬」,官方英文 Undying Embers;
换票 90 余烬/张每月 5 张)"""
TAB_STARLIGHT: str = 'starlight'
"""星芒兑换 tab(角色转化材料「未熄的星芒」,官方英文 Undying Starlight;
换票 20 星芒/张不限量)"""
_ALLOWED_TABS: set[str] = {TAB_EMBERS, TAB_STARLIGHT}

_TAB_AREA: dict[str, str] = {TAB_EMBERS: 'tab-余烬兑换', TAB_STARLIGHT: 'tab-星芒兑换'}
_ANCHOR_AREA: dict[str, str] = {
    TAB_EMBERS: 'tab-余烬兑换-选中',
    TAB_STARLIGHT: 'tab-星芒兑换-选中',
}

_AREA_CURRENCY: str = '读区-货币数量'
_AREA_FIRST_SLOT_MONTHLY: str = '读区-首列月限角标'
"""第 1 行第 1 列商品卡的「可兑换 X/5」月限角标(余烬页首列=月限商品;
实机证实月限商品换光后从首列移到列表末尾,该角标读数随首列商品变化,
仅作切换后读数参考,不作硬校验)"""

_COUNT_OCR_SCALE: float = 3.0
"""数量型 area 的 OCR 放大倍数(单字符数字兜底,同 ReadWarpStatusOp 口径)"""


class ShopSwitchTabOp(SrOperation):
    """在商店页切换余烬兑换 / 星芒兑换 tab。

    切换验证用目标 tab 的选中态模板(见模块 docstring)——框架 until 模式:
    点 tab → 重入查锚 → 锚在即已在目标 tab(until_find 出现型,偶发漏检
    只会多一次无害点击,无假满足风险)。

    结果状态:
    - ``EMBERS_TAB`` / ``STARLIGHT_TAB``:目标 tab 已切换完成;
    - ``STAY_ENTRY``:tab 非法;
    失败:起点不在商店页。
    """

    def __init__(self, ctx: SrContext, tab: str = TAB_EMBERS):
        """
        :param ctx: 上下文
        :param tab: 目标 tab,``embers``=余烬兑换 / ``starlight``=星芒兑换
            (取值 = 官方英文名 Undying Embers / Undying Starlight 的主体词)
        """
        self._tab: str = tab
        SrOperation.__init__(self, ctx, op_name=gt('商店切换兑换页'),
                             node_max_retry_times=15)

    @operation_node(name='切换兑换页', is_start_node=True)
    def switch_tab(self) -> OperationRoundResult:
        """校验目标合法后点目标 tab,until 选中态模板锚出现。"""
        if self._tab not in _ALLOWED_TABS:
            return self.round_fail(
                f'不支持的 tab(STAY_ENTRY): {self._tab}(仅支持 embers/starlight)')
        if self.check_and_update_current_screen(
                screen_name_list=[_SHOP_SCREEN]) != _SHOP_SCREEN:
            return self.round_fail('起点不在商店页,请先经 EnterShopFromWarpOp 进入')
        tab_area = _TAB_AREA[self._tab]
        anchor = _ANCHOR_AREA[self._tab]
        result = self.round_by_find_and_click_area(
            self.last_screenshot, _SHOP_SCREEN, tab_area,
            until_find_all=[(_SHOP_SCREEN, anchor)],
            success_wait=1.5, retry_wait=1.5)
        if result.is_success:
            return self.round_success(status='EMBERS_TAB' if self._tab == TAB_EMBERS
                                      else 'STARLIGHT_TAB', wait=1)
        return result

    @node_from(from_name='切换兑换页', status='EMBERS_TAB')
    @node_from(from_name='切换兑换页', status='STARLIGHT_TAB')
    @operation_node(name='收尾')
    def finish(self) -> OperationRoundResult:
        """终点节点:附带读数(货币数量+首列月限角标)入 data。

        货币数量用两层取数(全图过滤→3 倍放大兜底,个位数兜底,同
        ReadWarpStatusOp);首列月限角标「可兑换：X/Y」格式:分子=本期限
        剩余次数,分母=月限总量;get_positive_digits 对「5/5」会取成 55,
        须用斜杠对正则分别取值。星芒页首列无月限商品,角标读数为 None。
        """
        tab = 'EMBERS_TAB' if self._tab == TAB_EMBERS else 'STARLIGHT_TAB'
        data: dict = {
            'tab': self._tab,
            'material_count': parse_count(self._area_count_text(
                self.last_screenshot, _SHOP_SCREEN, _AREA_CURRENCY)),
        }
        monthly_text = self._area_text(self.last_screenshot,
                                       _SHOP_SCREEN, _AREA_FIRST_SLOT_MONTHLY)
        data['first_slot_monthly_text'] = monthly_text
        if monthly_text is not None:
            m = re.search(r'(\d+)\s*/\s*(\d+)', monthly_text)
            if m is not None:
                data['first_slot_monthly_left'] = int(m.group(1))
                data['first_slot_monthly_total'] = int(m.group(2))
        return self.round_success(status=tab, data=data, wait=0.5)

    def _area_text(self, screen, screen_name: str, area_name: str) -> str | None:
        """读画面建档 area 内的 OCR 文本(空 = None)。"""
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        ocr_result_list = self.ctx.ocr_service.get_ocr_result_list(screen, rect=area.rect)
        if len(ocr_result_list) == 0:
            return None
        return ''.join(result.data for result in ocr_result_list)

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
