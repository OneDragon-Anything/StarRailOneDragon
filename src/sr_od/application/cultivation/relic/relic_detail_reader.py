"""遗器替换屏右侧详情面板的读区结构化解析（词缀读取单一实现点）。

供 ``ScanRelicCandidatesOp``（候选扫描）与 ``EquipRelicOp``（词缀约束判定）
共用；读区 area 全部取自 screen_info「遗器-替换」（坐标单一真相源）。

解析依据（2026-11-12 摸底帧实证，帧 = sr-od-test/screens/遗器-替换/
候选详情词缀.webp 与 候选详情词缀平坦值.webp，S2 单测 fixture）：

- 副词条行 = 词条名（左，OCR 名框）+ 数值（右对齐，OCR 值框）+ 强化次数
  角标（独立元素）。名框/值框由 OCR 以独立文本框返回，y 中心对齐同行
  （实测 |Δy| ≤ 3px）。
- **次数判读只信角标几何，不信任行级 OCR 尾数**（F19/F20）：角标字符会被
  OCR 拼进数值串且读法不稳定——同一元素两种实证误读「6.9%0」（绿标 1 读成
  裸 0）「55②」（绿标 2 读成 ②）。角标 = 亮青绿填充圆（实测采样 RGB
  ≈(118,221,188)/(101,183,173)，OpenCV HSV 色相 ≈78），直径 ≈24px，中心
  x 恒 ≈1867；次数 ≥1 才渲染，0 次无角标。检测 = 行值框 y 带 × x[1845,1895]
  内 HSV 连通域；数字 = 圆区 4x 放大 OCR（两帧 5 圆全读对：1/1/3/2/2）。
- 数值串清洗：% 词条截到最后一个 ``%``（「9.1%0」→「9.1%」，拼入的角标
  字符随截断剔除）；平坦词条取头部连续数字（「55②」→「55」）。平坦值被
  OCR 拼入裸数字的形态（如「55」→「552」）不可检测，不在清洗范围——由
  OCR 高置信度兜底，约束判定只用次数不比数值，不受影响。
- 词条名 → 标准名经 ``sr_od.mys.sr_relic_stats.resolve_roster_stat``（与
  名册侧同一解析；平坦/% 同名异义按清洗后数值串的 ``%`` 后缀消歧），未
  识别词原样保留（``stat=None``）由调用方显式处置。
- ``times_confirmed=False`` 仅出现在「有角标但圆内数字 OCR 失败」——该行
  约束判定按不满足处理（宁漏装不误装）；无角标 = times=0 且 confirmed=True
  （0 次由几何确证）。

零点击、零副作用：只读截图，不操作游戏。
"""

import re

import cv2
from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils import str_utils
from sr_od.context.sr_context import SrContext
from sr_od.mys.sr_relic_stats import resolve_roster_stat

_SCREEN: str = '遗器-替换'

#: 强化次数角标的检测色彩范围（OpenCV HSV）；出处见模块 docstring 实测段
_BADGE_HSV_LOW: tuple[int, int, int] = (70, 80, 120)
_BADGE_HSV_HIGH: tuple[int, int, int] = (95, 255, 255)

#: 角标连通域最小面积（px²）：实测满圆 area≈305-414，60 为 5 倍裕量下限
_BADGE_MIN_AREA: int = 60

#: 角标搜索带 x 范围（实测圆 bbox x≈1855-1879、中心恒 1867）
_BADGE_BAND_X: tuple[int, int] = (1845, 1895)

#: 行配对的 y 中心距阈值（实测名/值框 |Δy|≤3px；行高 ≈38px，20 取半行）
_ROW_MATCH_Y_TOL: int = 20

#: 值框/名框的分界 x（实测名框 x≈1530-1533、值框 x≈1777-1819）
_VALUE_BOX_X_MIN: int = 1700

#: 名框带下界 x（词条行左端的图标 x≈1490-1525，OCR 会把图标误读成数字——
#: % 帧实证图标框「0」(x=1497) 以更近的 y 中心抢走行配对；名框恒在图标右侧）
_NAME_BOX_X_MIN: int = 1528

#: 角标数字放大倍数（圆直径 ≈24px → 96px，实测 4x 全读对）
_BADGE_OCR_SCALE: int = 4

#: 部位中文枚举（「读区-部位等级」首行文本的匹配词表；与替换屏部位 TAB 同序）
_POS_CN_LIST: list[str] = ['头部', '手部', '躯干', '脚部', '位面球', '连结绳']

#: 强化等级提取（「+15」形态；OCR 对「+」的读法已实测稳定）
_LEVEL_PATTERN: re.Pattern = re.compile(r'\+(\d+)')


def _find_badges(screen: MatLike, rect: Rect, y_center: int | None = None,
                 y_tol: int = _ROW_MATCH_Y_TOL) -> list[tuple[int, int, int, int]]:
    """在 screen 的 rect 子区内检测强化次数角标圆，返回 bbox 列表。

    Args:
        screen: RGB 全帧截图。
        rect: 检测区域（1080p 坐标）。
        y_center: 传入时只保留 y 中心距该值 ±y_tol 的圆（单行判读）；
            None = 全区检测。
        y_tol: y 带半宽。

    Returns:
        bbox 列表，元素 (x1, y1, x2, y2)，1080p 全帧坐标。
    """
    x1, y1 = int(rect.x1), int(rect.y1)
    crop = screen[y1:int(rect.y2), x1:int(rect.x2)]
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv, _BADGE_HSV_LOW, _BADGE_HSV_HIGH)
    n, _, stats, centroids = cv2.connectedComponentsWithStats(mask)
    result: list[tuple[int, int, int, int]] = []
    for i in range(1, n):
        bx, by, bw, bh, area = stats[i]
        if area < _BADGE_MIN_AREA:
            continue
        cx = x1 + centroids[i][0]
        cy = y1 + centroids[i][1]
        if y_center is not None and abs(cy - y_center) > y_tol:
            continue
        result.append((int(cx - bw / 2), int(cy - bh / 2), int(cx + bw / 2), int(cy + bh / 2)))
    return result


def _ocr_badge_times(ctx: SrContext, screen: MatLike, bbox: tuple[int, int, int, int]) -> int | None:
    """角标圆内数字的放大 OCR。返回 None = 读不出（调用方降级 times_confirmed）。

    圆区外扩 2px 后 4x 放大再 OCR——角标直径 ≈24px，原尺寸数字不可读。"""
    x1, y1, x2, y2 = bbox
    pad = 2
    crop = screen[max(0, y1 - pad):y2 + pad, max(0, x1 - pad):x2 + pad]
    big = cv2.resize(crop, None, fx=_BADGE_OCR_SCALE, fy=_BADGE_OCR_SCALE,
                     interpolation=cv2.INTER_CUBIC)
    for ocr_result in ctx.ocr_service.get_ocr_result_list(image=big):
        digits = re.sub(r'[^0-9]', '', ocr_result.data)
        if digits:
            return int(digits)
    return None


def _clean_value_text(raw: str) -> str:
    """行级 OCR 数值串清洗（拼入的角标字符剔除，规则见模块 docstring）。"""
    pct_idx = raw.rfind('%')
    if pct_idx >= 0:
        return raw[:pct_idx + 1]
    match = re.match(r'[0-9.]+', raw)
    return match.group(0) if match else raw


def _match_row_value_boxes(boxes: list) -> list[tuple[object, object]]:
    """副词条区 OCR 框按行配对：值框（x ≥ 分界）为锚，取 y 中心最近的名框。

    Returns:
        (值框, 名框 | None) 列表，按值框 y 升序。无名框配对的行保留
        （name 缺失由调用方置 None），不静默丢行。
    """
    value_boxes = [b for b in boxes if b.x >= _VALUE_BOX_X_MIN]
    name_boxes = [b for b in boxes if _NAME_BOX_X_MIN <= b.x < _VALUE_BOX_X_MIN]
    rows: list[tuple[object, object]] = []
    for value_box in sorted(value_boxes, key=lambda b: b.y):
        vc = value_box.y + value_box.h / 2
        best_name = None
        best_dist = _ROW_MATCH_Y_TOL
        for name_box in name_boxes:
            dist = abs(name_box.y + name_box.h / 2 - vc)
            if dist < best_dist:
                best_dist = dist
                best_name = name_box
        if best_name is not None:
            name_boxes.remove(best_name)
        rows.append((value_box, best_name))
    return rows


def _read_level_and_pos(ctx: SrContext, screen: MatLike) -> tuple[str | None, int | None]:
    """读「读区-部位等级」区：返回 (部位名, 强化等级)。

    部位名按词表 LCS 匹配（OCR 误读容差）；等级取首个「+N」。"""
    area = ctx.screen_loader.get_area(_SCREEN, '读区-部位等级')
    pos_cn: str | None = None
    level: int | None = None
    for ocr_result in ctx.ocr_service.get_ocr_result_list(image=screen, rect=area.rect):
        if pos_cn is None:
            for pos in _POS_CN_LIST:
                # exact 优先；LCS 0.9 兜底 OCR 近似（两字部位名共享「部」字，
                # 0.5 阈值下头部/脚部/手部全部互通——平坦帧「脚部」误判「头部」
                # 实证，宁可 None 不误判）
                if ocr_result.data == pos or str_utils.find_by_lcs(pos, ocr_result.data, percent=0.9):
                    pos_cn = pos
                    break
        if level is None:
            match = _LEVEL_PATTERN.search(ocr_result.data)
            if match:
                level = int(match.group(1))
    return pos_cn, level


def read_detail(ctx: SrContext, screen: MatLike | None = None) -> dict | None:
    """读替换屏右侧详情面板，返回结构化词缀档案。

    Args:
        ctx: 运行上下文（读区 area 与 OCR 服务）。
        screen: RGB 全帧截图；None 则自截（调用方持帧时传入可复用整帧
            OCR 缓存）。

    Returns:
        ``{'piece', 'pos_cn', 'level', 'main', 'subs'}``；main =
        ``{'name', 'stat', 'value'}``，subs 元素 =
        ``{'name', 'stat', 'value', 'times', 'times_confirmed'}``（value
        为清洗后字符串；stat 为标准名，未识别为 None）。详情面板不在
        （主词条区读不到词条名）时返回 None，由调用方决定重试语义。
    """
    if screen is None:
        screen = ctx.controller.get_screenshot()

    pos_cn, level = _read_level_and_pos(ctx, screen)

    piece_area = ctx.screen_loader.get_area(_SCREEN, '读区-遗器名')
    piece: str | None = None
    for ocr_result in ctx.ocr_service.get_ocr_result_list(image=screen, rect=piece_area.rect):
        piece = ocr_result.data
        break  # 取该区第一条（件名单行）

    main_area = ctx.screen_loader.get_area(_SCREEN, '读区-主词条')
    main_boxes = ctx.ocr_service.get_ocr_result_list(image=screen, rect=main_area.rect)
    main: dict | None = None
    main_rows = _match_row_value_boxes(main_boxes)
    if main_rows:
        value_box, name_box = main_rows[0]
        value_text = _clean_value_text(value_box.data)
        name_text = name_box.data if name_box is not None else None
        main = {
            'name': name_text,
            'stat': resolve_roster_stat(name_text, value_text) if name_text else None,
            'value': value_text,
        }
    if main is None or main['name'] is None:
        return None  # 主词条读不到 = 详情面板不在（面板存在时主词条必有文本）

    subs_area = ctx.screen_loader.get_area(_SCREEN, '读区-副词条')
    subs_boxes = ctx.ocr_service.get_ocr_result_list(image=screen, rect=subs_area.rect)
    subs: list[dict] = []
    for value_box, name_box in _match_row_value_boxes(subs_boxes):
        value_text = _clean_value_text(value_box.data)
        name_text = name_box.data if name_box is not None else None
        row_y = int(value_box.y + value_box.h / 2)
        badges = _find_badges(screen, subs_area.rect, y_center=row_y)
        times = 0
        times_confirmed = True
        if badges:
            badge_times = _ocr_badge_times(ctx, screen, badges[0])
            if badge_times is None:
                # 有角标但数字读不出：按不满足处理并标记（宁漏装不误装）
                times_confirmed = False
            else:
                times = badge_times
        subs.append({
            'name': name_text,
            'stat': resolve_roster_stat(name_text, value_text) if name_text else None,
            'value': value_text,
            'times': times,
            'times_confirmed': times_confirmed,
        })

    return {'piece': piece, 'pos_cn': pos_cn, 'level': level, 'main': main, 'subs': subs}
