"""商店画面识别器:兑换商店列表页的结构化读数(走识别通道,不造读数 op)。

消费方 = MCP 画面识别(analyze_screen 的 extras):agent 不进弹窗即可答
「本月还能换啥 / 当前余额多少」。app 主链不依赖本识别器(购买 op 自带
月限与余额判定并经 data 返回)。

机制:声明 screen_name='商店' 被框架自动扫描注册(无参实例化);
analyze_screen 精准命中画面后调用 recognize。字段纪律(CW 样板):
extras_doc 键集 = 返回键集,读不出如实 None,不硬塞。

约束:识别器**不滚动列表**——月限三件套可用排前、售罄沉底(flow.md
§3),当前视口不可见即如实 visible=False;滚动属交互行为,识别器保持
快速无副作用。
"""

from typing import TYPE_CHECKING

from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from sr_od.application.cultivation.account.operations.read_warp_status import (
    parse_count,
)
from sr_od.application.cultivation.account.operations.shop_goods_scan import (
    MONTHLY_TRIO,
    badge_rect,
    locate_cards,
    ocr_rect_text,
    parse_exchange_pair,
    read_count_two_pass,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.operation.one_dragon_context import OneDragonContext
    from one_dragon.base.screen.screen_info import ScreenInfo


class StoreExchangeRecognizer(ScreenRecognizer):

    screen_name = '商店'

    extras_doc: dict[str, str] = {
        'currency': '当前渠道货币余额(随选中 tab 显示星芒/余烬;OCR 读不出为 null)',
        'active_tab': ('当前兑换子 tab:embers=余烬兑换 / starlight=星芒兑换 / '
                       'light_cone_manifest=光锥呈现;都不命中为 null'),
        'goods': ('三件套角标读数,键=special_pass/pass/tracks_of_destiny;单项 '
                  '{remaining,total} =「可兑换X/Y」解析(读不出 null)、'
                  'sold_out=角标含已售罄、visible=当前视口可见(售罄沉底不可见时 '
                  'false 且其余字段不塞);识别器不滚动列表'),
    }

    def recognize(self, ctx: 'OneDragonContext', image: 'MatLike',
                  screen_info: 'ScreenInfo') -> dict:
        """读当前视口的余额 / 选中 tab / 三件套角标(字段语义见 extras_doc)。"""
        result: dict = {
            'currency': None,
            'active_tab': None,
            'goods': {},
        }

        # 货币余额:随 tab 切换显示当前渠道货币(星芒页=星芒,余烬页=余烬)
        area = ctx.screen_loader.get_area(self.screen_name, '读区-货币数量')
        if area is not None:
            text = read_count_two_pass(ctx.ocr_service, ctx.ocr, image, area)
            if text is not None:
                result['currency'] = parse_count(text)

        # 选中 tab:三个选中态 area(OCR+color_range 锁白)恰好命中一个
        for anchor, tab in (('tab-余烬兑换-选中', 'embers'),
                            ('tab-星芒兑换-选中', 'starlight'),
                            ('tab-光锥呈现-选中', 'light_cone_manifest')):
            anchor_area = ctx.screen_loader.get_area(self.screen_name, anchor)
            if anchor_area is None:
                continue
            text = ocr_rect_text(ctx.ocr_service, image, anchor_area.rect)
            if text is not None and anchor_area.text in text:
                result['active_tab'] = tab
                break

        # 三件套角标:当前视口一次 OCR,按卡面关键词定位卡再读角标
        list_area = ctx.screen_loader.get_area(self.screen_name, '商品列表')
        if list_area is not None:
            ocr_result_list = ctx.ocr_service.get_ocr_result_list(
                image, rect=list_area.rect)
            cards = locate_cards(ocr_result_list, set(MONTHLY_TRIO.values()))
            for goods_id, keyword in MONTHLY_TRIO.items():
                item: dict = {'remaining': None, 'total': None,
                              'sold_out': None, 'visible': False}
                card_rect = cards.get(keyword)
                if card_rect is not None:
                    item['visible'] = True
                    badge = ocr_rect_text(ctx.ocr_service, image,
                                          badge_rect(card_rect))
                    if badge is not None:
                        if '已售罄' in badge:
                            item['sold_out'] = True
                        else:
                            pair = parse_exchange_pair(badge)
                            if pair is not None:
                                item['remaining'], item['total'] = pair
                result['goods'][goods_id] = item
        return result
