"""货币战争 商店开态刷新钮标价的现场 OCR 读取(ADR-0622 现场识别通道)。

字段语义与写端裁决 = ADR-0622 + 字段级规格正本 =
``docs/develop/currency_war/game_state/fields.md`` §3.3.4:刷新费 shop_refresh_cost 的值必须来自商店
开态刷新钮标价的**现场读数**(识别失败=None,禁兜底改值;免费帧不写,None≠标价 0)。
历史通道均不复活:面板徽标 OCR 读的是利息数值非刷价(ADR-0456,旁证 reader 在
``cw_observation.read_shop_refresh_cost``);「刷新前后金币差倒推」已随 ADR-0622
退役。本模块与徽标旁证 reader 的名字区分:**price=标价(本模块,写端权威)**,
cost=徽标(cw_observation,旁证)。
"""
from __future__ import annotations

import re

from cv2.typing import MatLike

from sr_od.application.currency_war.kernel.cw_obs_core import (
    SHOP_SCREEN_NAME,
    _area_rect,
)
from sr_od.application.currency_war.obs.cw_observation import (
    _ocr_upscaled,
    _ocr_upscaled_binarized,
)
from sr_od.context.sr_context import SrContext

#: 标价 OCR area(screen_info「货币战争-备战-开商店」;坐标单一真相源=screen_info,
#: bbox 依据与取框余量见该 area 建档,shop_open.webp 等归档帧可离线复核)。
_PRICE_AREA_NAME: str = '文本-刷新价格'

#: 标价可信域。下界 1:付费刷新无 0 金价态(0 金即免费),OCR 产出 0 一律拒信——
#: 产出 0 的两种形态都不是标价:①金币图标无数字并入态('GO' 经 O→0 映射);
#: ②免费帧渲染。拒信保证「免费帧读不到 ≠ 标价 0」(§3.3.4 字段语义)。
#: 上界 9:钮内标价为一位数字渲染;注册表在册改价效果仅长线利好(cw_invest_data
#: PlazaPortal id='120',30 次付费刷新后刷价降为 1 金),两位数无在册证据,
#: 越界按失读(None),不猜测截位。
_PRICE_MIN: int = 1
_PRICE_MAX: int = 9


def _parse_price_digit(texts: list[str]) -> int | None:
    """标价 rect OCR 文本 → int | None(纯函数可单测)。

    字段先验:rect 内恒为 金币图标+一位标价数字。金币图标被 OCR 系统性并入
    数字前缀(徽标 reader 同构实证 ``cw_observation._parse_coin_fee_digit``:
    'GO'/'G0'/'G2',G=图标)→ 归一大写后把残留字母 O 映射为 0(图标旁数字 0
    的形变),再逐条取首个整数。逐条扫描而非首条定生死:图标与数字常被拆成
    两条('GO' + '2'),首条产出 0 落可信域外时须继续扫(否则丢真值);全部
    不可信 → None。
    """
    for t in texts:
        m = re.search(r'\d+', (t or '').upper().replace('O', '0'))
        if m is None:
            continue
        v = int(m.group())
        if _PRICE_MIN <= v <= _PRICE_MAX:
            return v
    return None


def read_shop_refresh_price(ctx: SrContext, screen: MatLike) -> int | None:
    """商店开态「刷新」圆钮标价现场读数(ADR-0622 字段写端;纯读)。

    :param screen: 商店开态整帧(RGB,controller 截图);None=测试注入态
      (mock ocr_service 不承载像素,仓内既有约定,同 ``cw_observation``)。
    :return: 标价(1-9);读不到/不可信 → None。**禁兜底**:调用方拿 None
      按失读处理,不回退基价常量;免费帧不写由调用方按 §3.3.6 免费刷新余额
      判定,本 reader 对 0 一律拒信(见 ``_PRICE_MIN`` 注)。

    管线两级(与 ``cw_observation.read_level_up_cost`` 同形):标价为小字目标,
    全帧 det 必漏(归档帧离线对拍实证:analyze_screen 全帧 OCR 对标价数字
    零命中),裁 area 后 3x 放大读;读空再 OTSU 二值化重试(低对比渲染变异帧
    保底;二值化伤彩色小字,不作第一级)。区域 = screen_info
    「货币战争-备战-开商店」屏「文本-刷新价格」area(坐标单一真相源)。
    """
    rect = _area_rect(ctx, _PRICE_AREA_NAME, SHOP_SCREEN_NAME)
    texts = [r.data for r in _ocr_upscaled(ctx, screen, rect)]
    if not texts:
        texts = [r.data for r in _ocr_upscaled_binarized(ctx, screen, rect)]
    return _parse_price_digit(texts)
