"""货币战争 商店开态刷新钮标价/按钮态的现场 OCR 读取(ADR-0622 + T-13)。

字段语义与写端裁决 = ADR-0622 + 字段级规格正本 =
``docs/develop/sr_od/application/currency_war/game_state/fields.md`` §3.3.4:刷新费 shop_refresh_cost 的值必须来自商店
开态刷新钮标价的**现场读数**(识别失败=None,禁兜底改值;免费帧不写,None≠标价 0)。
历史通道均不复活:面板徽标 OCR 读的是利息数值非刷价(ADR-0456,旁证 reader 在
``cw_observation.read_shop_refresh_cost``);「刷新前后金币差倒推」已随 ADR-0622
退役。本模块与徽标旁证 reader 的名字区分:**price=标价(本模块,写端权威)**,
cost=徽标(cw_observation,旁证)。

刷新钮**按钮态**读数(:func:`read_shop_refresh_button`,T-13 建档接入):单帧三态
=免费态(「免费刷新」锚+剩余次数)/付费耗尽态(「刷新」+金币图标+标价,白亮钮)/
不可用灰态(同付费渲染,按钮变暗,金<标价)。免费态次数 = §3.3.6
free_refresh_balance 的 UI 观察通道(T-15 实机取证:免费帧按钮渲染「免费刷新」+
次数数字,次数与「文本-刷新价格」rect 同位——推翻该节「画面无计数控件」旧对拍
申报,正本更新归设计批)。三态渲染规格与行为实锤出处 =
``.debug/currency_war/evidence/20260912_t15_t13_t18/``(免费帧
t13_free_refresh_available_2left_hist_w591t / 耗尽帧 t13_shop_open_refresh_
exhausted_2gold_gold61 / 灰态帧 t13_refresh_disabled_gold1_dark_button)。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from cv2.typing import MatLike

from one_dragon.base.screen import screen_utils
from one_dragon.base.screen.screen_utils import FindAreaResultEnum
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
      按失读处理,不回退基价常量;本 reader 对 0 一律拒信(见 ``_PRICE_MIN`` 注)。

    ⚠️ **免费帧会产出数字**(T-15 实机取证:免费态按钮在同 rect 渲染剩余
    次数,推翻「免费帧渲染无数字」旧假设)——免费帧调用本 reader 会把次数
    误读作标价。因此「免费帧不写」(§3.3.4)的免费判定输入 =
    :func:`read_shop_refresh_button` 的按钮态锚,**调用方必须先过按钮态闸**
    再消费本读数(现役唯一消费点 = cw_observation 商店开态喂入口,已接)。

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


# ---------------------------------------------------------------------------
# 刷新钮按钮态读数(T-13 免费刷新按钮/机制建档接入)
# ---------------------------------------------------------------------------

#: 免费态文本锚(screen_info「货币战争-备战-开商店」「标识-免费刷新」;
#: text=免费刷新,lcs_percent=0.7——付费帧「刷新」两字 LCS 2/4=0.5 不中,
#: T-15 三帧离线对账实证:免费帧命中 conf 0.999,付费/灰态帧均不命中)。
_FREE_ANCHOR_AREA: str = '标识-免费刷新'

#: 免费态次数可信域。下界 1:次数为 0 不渲染免费钮(免费钮在场即余额>0);
#: 上界 = 注册表最大一次性额度(高效决策 9999,cw_invest_data id='301701';
#: 长线/每节点族额度均 ≤11)。越界按失读(None),不猜测截位。
_COUNT_MIN: int = 1
_COUNT_MAX: int = 9999


def _parse_free_count(texts: list[str]) -> int | None:
    """免费态次数 rect OCR 文本 → int | None(纯函数可单测)。

    识别结构 = 纯数字渲染(免费帧钮内无金币图标,T-15 历史帧 w591t 实证:
    「免费刷新」+次数上下两行)——无付费帧的图标并入前缀问题,逐条取首个
    落可信域的整数;全部不可信 → None。
    """
    for t in texts:
        m = re.search(r'\d+', (t or '').upper().replace('O', '0'))
        if m is None:
            continue
        v = int(m.group())
        if _COUNT_MIN <= v <= _COUNT_MAX:
            return v
    return None


def _free_anchor_hit(ctx: SrContext, screen: MatLike) -> bool | None:
    """「免费刷新」文本锚在场判定(框架 find_area,与建档对账同源同参)。

    - True = 免费态渲染在场(免费余额>0 的 UI 事实);
    - False = 锚未命中(付费帧/灰态帧渲染「刷新」,lcs 0.7 不中);
    - None = area 缺失/识别层异常(失读,消费方须回退逻辑账,**禁当 False**
      ——免费帧 OCR 漏检被误判付费会把免费刷混进付费计数,§3.3.7 毒化)。

    crop_first=False(全图 OCR 按 rect 过滤):小而紧的裁剪会让文字检测器
    漏检,全图路径无此问题(od-dev-screen-onboarding crop-OCR 坑;全图识别
    结果同帧多 rect 查询复用缓存,无额外开销)。
    """
    try:
        r = screen_utils.find_area(ctx, screen, SHOP_SCREEN_NAME,
                                   _FREE_ANCHOR_AREA, crop_first=False)
    except Exception:   # noqa: BLE001  识别层故障 = 失读,不判 False
        return None
    if r == FindAreaResultEnum.AREA_NO_CONFIG:
        return None
    return r == FindAreaResultEnum.TRUE


@dataclass(frozen=True)
class ShopRefreshButton:
    """刷新钮单帧三态读数(T-13;纯读,无行为)。

    三态渲染规格(T-15 实机取证,证据帧见模块头):
    - **免费态**(免费余额>0):金色圆钮,钮内「免费刷新」+剩余次数数字;
    - **耗尽态**(余额 0,可负担):白亮圆钮,「刷新」+金币图标+标价;
    - **不可用灰态**(金<标价):渲染与耗尽态**逐字相同**,仅按钮变暗——
      文本面无法表达,判别 = 逻辑面对比(金现读 vs 标价,T-15 未尽事项
      方案 b;暗钮模板方案 a 留作 OCR 链失效时的后备,模板源帧已落档)。

    字段语义:
    - ``free``:True=免费态(锚命中);False=付费域(锚未中∧标价读出,
      含耗尽与灰态两形);None=判不出(area 缺失/OCR 双空),消费方按失读
      回退逻辑账,禁当 False。
    - ``free_remaining``:免费态钮内剩余次数(§3.3.6 free_refresh_balance
      的 UI 观察通道)。非免费态/失读 = None。
    - ``price``:付费态标价(§3.3.4 同源 :func:`read_shop_refresh_price`);
      免费态恒 None(免费帧不写语义在解析层结构性满足——次数 rect 读数
      不进标价通道)。
    - ``affordable``:付费态可负担 = 金现读 ≥ 标价;免费态恒 True;
      金或价失读 = None。
    """

    free: bool | None
    free_remaining: int | None
    price: int | None
    affordable: bool | None


def read_shop_refresh_button(ctx: SrContext, screen: MatLike,
                             gold: int | None = None) -> ShopRefreshButton:
    """刷新钮三态现场读数(单帧,纯读;消费方 = 刷新执行免费闸 + 余额联动对票)。

    :param screen: 商店开态整帧(RGB,controller 截图);None=测试注入态
      (mock ocr_service 不承载像素,仓内既有约定)。
    :param gold: 同帧金币现读(调用方已读则传入复用,本函数不重复读金);
      只用于灰态判别,失读传 None(→ ``affordable``=None)。
    :return: :class:`ShopRefreshButton`(判不出 = ``free``=None,**禁兜底**)。

    判定序:锚命中 → 免费态(次数从「文本-刷新价格」rect 同位读——免费帧
    该区渲染次数非标价,T-15 实证);锚未中∧标价读出 → 付费域;其余(锚
    失读/锚未中∧标价也读不出)→ 判不出。锚未中∧标价 None 不判 False:
    真免费帧双 OCR 双漏时误判付费会毒化付费计数(§3.3.7),回退逻辑账
    是接线前保守形态,行为不变。
    """
    hit = _free_anchor_hit(ctx, screen)
    price_rect = _area_rect(ctx, _PRICE_AREA_NAME, SHOP_SCREEN_NAME)
    if hit is True:
        texts = [r.data for r in _ocr_upscaled(ctx, screen, price_rect)]
        if not texts:
            texts = [r.data for r in _ocr_upscaled_binarized(ctx, screen, price_rect)]
        return ShopRefreshButton(free=True,
                                 free_remaining=_parse_free_count(texts),
                                 price=None, affordable=True)
    price = read_shop_refresh_price(ctx, screen)
    if hit is False and price is not None:
        return ShopRefreshButton(
            free=False, free_remaining=None, price=price,
            affordable=None if gold is None else gold >= price)
    return ShopRefreshButton(free=None, free_remaining=None,
                             price=price, affordable=None)

