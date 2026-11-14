"""兑换商店商品卡扫描与角标解析的单一源模块。

消费方:购买 op([shop_buy_goods])与商店识别器
([store_exchange_recognizer])共用网格几何 / 卡定位 / 角标读取管线;
斜杠对解析与两层取数在此收拢——原两 op 各持一份实现且已漂移
(shop_switch_tab 两层取数为弱化版:首层非空即返回;shop_buy_goods 为
强化版:非数字一律放大重试),同族第二件升单一源,统一强化版口径。
"""

import re

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils import cv2_utils
from sr_od.application.cultivation.account.operations.read_warp_status import (
    parse_count,
)

_GRID_COL_WINDOWS: list[tuple[int, int]] = [
    (305, 560), (550, 805), (795, 1050),
    (1040, 1295), (1285, 1540), (1530, 1785),
]
"""商品网格几何(1080p):6 列 × N 行,列距 245、卡宽约 216。列位置固定不随
滚动变,行位置随滚动吸附态漂移(常规行距 325,列表底部对齐态行位偏移)——
目标卡定位 = 名字文本中心归列 + 名字中心反推卡顶(商品名在卡内垂直偏移
恒定,与滚动态无关),任意吸附态均可定位。"""
CARD_WIDTH: int = 216
CARD_HEIGHT: int = 285
NAME_OFFSET_FROM_TOP: int = 195
"""商品名文本框中心相对卡顶的垂直偏移(1080p 实测标定,标定样本见
test_shop_buy_goods 流程测试素材)"""
LIST_Y_MIN: int = 110
"""卡顶反推的合理上界(列表区上沿之上视为异帧残留,拒绝)"""
# 卡左上角限额角标区(「可兑换 X/Y」/「已达上限」/「已售罄」/「未解锁」),
# 按卡槽 rect 推演;角标为悬挂样式(文字框左缘超出卡左缘约 25px,实拍标定),
# x1 需左移容纳;窗口 y 不盖住角标下方的倒计时文本框
BADGE_OFFSET: tuple[int, int, int, int] = (-25, 8, 175, 52)

MONTHLY_TRIO: dict[str, str] = {
    # 英文标识符 → 卡面商品名 OCR 关键词(唯一子串,防 OCR 抖动)
    'special_pass': '星轨专票',
    'pass': '星轨通票',
    'tracks_of_destiny': '命运的足迹',
}

BADGE_UNAVAILABLE_KEYWORDS: tuple[str, ...] = ('已售罄', '已达上限', '未解锁')
# 卡不可购态角标关键词:命中即 fail,不进弹窗(售罄弹窗确认按钮禁用,进了也无法购买)

COUNT_OCR_SCALE: float = 3.0
"""数量型 area 的 OCR 放大倍数(单字符数字兜底,同 ReadWarpStatusOp 口径)"""


def locate_window(value: float,
                  windows: list[tuple[int, int]]) -> int | None:
    """值落在哪个窗口,返回下标;都不在返回 None。"""
    for idx, (low, high) in enumerate(windows):
        if low <= value <= high:
            return idx
    return None


def locate_cards(ocr_result_list: list,
                 names: set[str]) -> dict[str, Rect]:
    """一次列表区 OCR 结果按名字定位多张商品卡。

    商品名用**包含匹配**——不引入模糊兜底:同名易混对(星轨通票/星轨
    专票一字之差)模糊匹配会误命中,后果是读错卡的角标甚至点错卡,
    比漏扫(诚实失败)严重。一个 OCR 框只归属一个名字(关键词互不为
    子串,首个命中即定)。
    """
    cards: dict[str, Rect] = {}
    for result in ocr_result_list:
        text = result.data or ''
        for name in names:
            if name not in text:
                continue
            center = result.center
            col = locate_window(center.x, _GRID_COL_WINDOWS)
            if col is None:
                # 商品名文字不在任何列窗口(异帧残留等),跳过
                continue
            card_top = int(center.y) - NAME_OFFSET_FROM_TOP
            if card_top < LIST_Y_MIN:
                continue
            col_center = sum(_GRID_COL_WINDOWS[col]) // 2
            cards[name] = Rect(col_center - CARD_WIDTH // 2, card_top,
                               col_center + CARD_WIDTH // 2,
                               card_top + CARD_HEIGHT)
            break
    return cards


def parse_exchange_pair(text: str | None) -> tuple[int, int] | None:
    """「可兑换 X/Y」角标文本 → (剩余次数 X, 期限总量 Y)。

    斜杠对须用 ``\\d+\\s*/\\s*\\d+`` 分别取值——get_positive_digits 对
    「5/5」会取成 55;本函数是全仓斜杠对解析的单一源(购买 op 与
    ShopSwitchTabOp.finish 的同款正则收拢于此)。解析失败(文本空/无
    斜杠对)返回 None,调用方按软读数缺失处理。
    """
    if not text:
        return None
    m = re.search(r'(\d+)\s*/\s*(\d+)', text)
    if m is None:
        return None
    return int(m.group(1)), int(m.group(2))


def parse_monthly_left(text: str | None) -> int | None:
    """「可兑换 X/Y」角标文本 → 剩余次数 X(单一源薄包装,取首值)。"""
    pair = parse_exchange_pair(text)
    return pair[0] if pair is not None else None


def badge_rect(card_rect: Rect) -> Rect:
    """卡槽位 rect → 左上角限额角标区 rect(窗口不盖住角标下方倒计时)。"""
    return Rect(card_rect.x1 + BADGE_OFFSET[0],
                card_rect.y1 + BADGE_OFFSET[1],
                card_rect.x1 + BADGE_OFFSET[2],
                card_rect.y1 + BADGE_OFFSET[3])


def ocr_rect_text(ocr_service, screen, rect: Rect) -> str | None:
    """读指定 rect 的 OCR 文本(空 = None)。"""
    ocr_result_list = ocr_service.get_ocr_result_list(screen, rect=rect)
    if len(ocr_result_list) == 0:
        return None
    return ''.join(result.data for result in ocr_result_list)


def read_count_two_pass(ocr_service, ocr, screen, area) -> str | None:
    """读数量型 area:两层取数——全图 OCR+rect 过滤 → 非数字时 3 倍放大裁剪兜底。

    全图 OCR 对单个小数字易出噪声字形(实测兑换数量 4 全图读成 'a'/'O',
    静态 rect 命中非空但不可解析),只判空会漏触发兜底;非数字结果一律走
    放大裁剪二次识别,数字可读性显著更好。本实现 = 原 shop_buy_goods
    强化版口径(shop_switch_tab 的弱化版已收拢至此统一)。
    """
    ocr_result_list = ocr_service.get_ocr_result_list(screen, rect=area.rect)
    if len(ocr_result_list) > 0:
        joined = ''.join(result.data for result in ocr_result_list)
        if parse_count(joined) is not None:
            return joined
    cropped = cv2_utils.crop_image_only(screen, area.rect)
    big = cv2_utils.scale_image(cropped, scale=COUNT_OCR_SCALE)
    raw = ocr.run_ocr(big)
    if len(raw) == 0:
        return None
    return ''.join(raw.keys())
