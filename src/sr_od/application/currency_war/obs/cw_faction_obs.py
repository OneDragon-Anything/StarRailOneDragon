"""货币战争 备战帧左侧羁绊面板·显示侧识别器 + 与计算侧羁绊计数的对账(W545)。

**裁决口径(用户定)**:羁绊状态以我方逻辑计算为主源
(``cw_observation.board_from_tracked``),左侧面板显示只作**对账票**
——显示不全(列表可滚动+底部截断)与灰字档位梯难读是当初选逻辑计算
为源的原因,故本识别器**不读灰色档位梯**,只读每条目的:
- 羁绊名(大幅白字,清晰)→ 名称锚点;
- 圆形徽章数字(图标左下,白字黑底单数字 = 该羁绊当前单位数)→ 当前数。

条目结构(16 帧 fixture 亲读实测,坐标系 1080p):
每条目 = 菱形图标(x≈40-108)+ 图标左下徽章数字(x≈75-110,与灰梯同行)+
羁绊名(x≥112 大白字)+ 名下灰色档位梯(含 ``/``,不读)。条目行距不固定
(特殊态领航员更高、列表可滚动)→ 逐条 y 不写死,用名称锚点 + 徽章数字
的相对 y 配对定位。

**截断口径**:只列 ≥1 的羁绊;面板视口(约到 y≈772)会裁掉最后一条的
徽章(名字仍可见)→ 最后一条名称锚点无徽章 = truncated,如实标记,
该条目不进对账(防「显示侧没有 = 计算侧多」的截断嫌疑误报放大)。

对账纯函数 :func:`compare_factions`:逐名三态(一致/不一致/显示侧不可判);
OCR 失读条目跳过并计数(不算不一致);computed 有而显示没有 = 截断嫌疑,
单独计数不判错。接线:cw_screen_prep 主环 heavy 帧调 ``compare_factions``
并经 :func:`report_faction_reconcile` 落台账(对账网家族羁绊子网)。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import cv2
from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils import str_utils
from sr_od.application.currency_war.data.cw_factions import FACTIONS
from sr_od.application.currency_war.kernel.cw_obs_core import A_BOARD, SCREEN_NAME

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

# 面板区域 = screen_info「区域-羁绊面板」pc_rect 为基(单一真相源),
# 底边延到 830——截断条目的名字可见带(名底可到 ~y770)之下还可能有
# 部分徽章残留,延边只为如实判截断,不改变条目定位逻辑。
# 区域缺档 = 建档漂移 → 空读数(不猜,语义见 read_displayed_factions)。
_PANEL_Y2_EXT: int = 830

# 名称带裁切左界(实测名 x≈112 起,留余量;徽章/图标都在左侧,灰梯虽同
# x 带但无中文,解析层按「含中文且无斜杠」过滤,不依赖 x 硬切)。
_NAME_RECT_X1: int = 100
# 徽章圆中心(全帧实测 cx≈88-91;特殊态领航员徽章右移到 cx≈120)。
_BADGE_CX: int = 91
_BADGE_CX_SPECIAL: int = 120
#: 徽章相对名称锚点 cy 的候选偏移(实测 +29~+38,逐档重试取首个纯数字读)。
_BADGE_DY_CANDS: tuple[int, ...] = (35, 29, 32, 38)
#: 徽章内字框半宽/半高(数字 ~11x14 居中于圆;框避开圆环——环被 rec 读成 '0')。
_BADGE_BOX_DX: int = 8
_BADGE_BOX_DY: int = 8
#: 徽章小图 OCR 放大倍数(6x 三次插值 + 白边填充,原生 det 读不出小字)。
_BADGE_UPSCALE: int = 6
# 徽章相对名称锚点的 y 配对窗(实测徽章中心 ≈ 名中心 +22~+37)。
_BADGE_DY_MIN: int = 8
_BADGE_DY_MAX: int = 65
# 徽章数字合法域:单羁绊单位数 ≤ 前后台总部署上界 13;越界 = OCR 误读。
_BADGE_COUNT_MAX: int = 12
# 名称 LCS 兜底阈值(白字大名 OCR 通常精确,仅兜小形变;阈值取高防
# 「昼之半神/夜之半神」这类仅一字差的邻项误配)。
_NAME_LCS_THRESHOLD: float = 0.5

_DIGIT_RE = re.compile(r'^\d{1,2}$')


@dataclass
class FactionPanelReading:
    """左侧羁绊面板一次读取的结果(显示侧)。

    ``entries``:可读条目 [(羁绊名, 当前单位数)],按显示序(名→注册表规范名)。
    ``unreadable``:名可对上注册表但徽章数字失读的条目名(不评口径,只计数)。
    ``unmatched``:OCR 出的名称文本对不上注册表的条目(截断残名/艺术字形变),
    存 OCR 原文(不评口径,只计数)。
    ``truncated``:最后一条名称锚点无徽章 = 视口截断形态在场(底部还有条目
    被面板裁掉,截断条目本身已按上述两类计数)。
    """
    entries: list[tuple[str, int]] = field(default_factory=list)
    unreadable: list[str] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)
    truncated: bool = False


@dataclass
class FactionReconcileRow:
    """单条羁绊的对账行(逐名三态)。"""
    faction: str
    computed: int | None  # 计算侧(主源);None = 计算侧无此羁绊(显示侧多出)
    displayed: int | None  # 显示侧;None = 显示侧失读(display_unreadable)
    verdict: str  # 'match' | 'mismatch' | 'display_unreadable' | 'computed_missing'


@dataclass
class FactionReconcileResult:
    """羁绊对账结果(纯数据,无行为)。"""
    rows: list[FactionReconcileRow] = field(default_factory=list)
    #: 显示侧 OCR 失读条目名(跳过不评,只计数)
    ocr_skipped: list[str] = field(default_factory=list)
    #: 截断嫌疑:computed 有而显示没有的羁绊(单独计数,不判错)
    truncation_suspects: list[str] = field(default_factory=list)

    @property
    def mismatch_count(self) -> int:
        return sum(1 for r in self.rows if r.verdict == 'mismatch')


def _match_faction(raw: str) -> str | None:
    """OCR 名称文本 → 注册表羁绊名;对不上 → None。

    精确优先(大字白名 OCR 通常精确);LCS 兜底要求唯一 argmax——
    「昼之半神/夜之半神」仅一字差,并列/低比例一律不猜(返回 None 进
    unmatched 计数,宁缺勿错配)。
    """
    if raw in FACTIONS:
        return raw
    names = list(FACTIONS)
    best = str_utils.find_best_match_by_lcs(
        raw, names, lcs_percent_threshold=_NAME_LCS_THRESHOLD)
    if best is None:
        return None
    best_pct = (str_utils.longest_common_subsequence_length(raw, names[best])
                / len(names[best]))
    # 并列 argmax → 不唯一 → 不猜
    ties = [i for i, n in enumerate(names)
            if str_utils.longest_common_subsequence_length(raw, n) / len(n)
            >= best_pct - 1e-9]
    if len(ties) > 1 or best_pct < _NAME_LCS_THRESHOLD:
        return None
    return names[best]


def _extract_anchors(name_tokens: list[tuple[str, int, int, int, int]]
                     ) -> list[tuple[int, int, str | None, str]]:
    """名称带 token → 条目锚点 [(cy, y2, 规范名|None, 原文)],按显示序。

    锚点 = 含中文且无斜杠的 token(名 x≈105 起;徽章数字/灰梯无中文,
    灰梯含 ``/``,均被滤除——不依赖 x 硬切)。
    """
    anchors: list[tuple[int, int, str | None, str]] = []
    for text, _x1, y1, _x2, y2 in sorted(name_tokens, key=lambda t: t[2]):
        if '/' in text or not str_utils.with_chinese(text):
            continue
        anchors.append(((y1 + y2) // 2, y2, _match_faction(text), text))
    return anchors


def parse_panel_tokens(name_tokens: list[tuple[str, int, int, int, int]],
                       badge_tokens: list[tuple[str, int, int, int, int]]) -> FactionPanelReading:
    """解析层(纯函数):名称带 token + 徽章 token → 面板读数。

    token = (text, x1, y1, x2, y2)(画面绝对坐标)。名称分类已由
    :func:`_extract_anchors` 口径完成,徽章 = 纯 1-2 位数字;本层只做
    配对与语义解析,便于用构造 token 做真值表测试。
    """
    reading = FactionPanelReading()
    anchors = _extract_anchors(name_tokens)
    badges: list[tuple[int, int, int]] = []  # (cy, count, x1)
    for text, x1, y1, _x2, y2 in badge_tokens:
        if _DIGIT_RE.match(text or ''):
            cnt = int(text)
            if 1 <= cnt <= _BADGE_COUNT_MAX:
                badges.append(((y1 + y2) // 2, cnt, x1))
    used: set[int] = set()
    for i, (cy, _y2, fac, raw) in enumerate(anchors):
        cands = [(bx1, j, bcnt)
                 for j, (bcy, bcnt, bx1) in enumerate(badges) if j not in used
                 and _BADGE_DY_MIN <= bcy - cy <= _BADGE_DY_MAX]
        is_last = i == len(anchors) - 1
        if not cands:
            # 无徽章:最后一条 = 截断形态(名的可匹配性只决定它进哪类计数);
            # 中间条 = 徽章失读(名对上)或残名
            if fac is None:
                reading.unmatched.append(raw)
            else:
                reading.unreadable.append(fac)
            if is_last:
                reading.truncated = True
            continue
        # 取最左:徽章圆在灰梯左侧;灰梯被误读成 ≤2 位纯数字时 x1 更大,
        # 最左优先压其误配(特殊态领航员徽章右移但其条目无灰梯,仍最左)。
        _x, j, cnt = min(cands)
        used.add(j)
        if fac is None:
            reading.unmatched.append(raw)
        else:
            reading.entries.append((fac, cnt))
    return reading


def read_displayed_factions(ctx: SrContext, screen: MatLike) -> FactionPanelReading:
    """OCR 备战帧左侧羁绊面板 → 显示侧读数(可见条目;截断如实标记)。

    两次聚焦裁切 OCR(名称带 / 徽章带分开,防「徽章数字 + 灰梯同行」
    被 OCR 合并成混串);区域 = screen_info「区域-羁绊面板」底边延至
    ``_PANEL_Y2_EXT``。区域缺失(screen_info 无档)→ 空读数(不猜)。
    """
    base = ctx.screen_loader.get_screen(SCREEN_NAME) if ctx.screen_loader else None
    rect: Rect | None = None
    if base is not None:
        area = next((a for a in base.area_list if a.area_name == A_BOARD), None)
        if area is not None and area.pc_rect is not None:
            rect = area.pc_rect
    if rect is None:
        # 区域缺档(screen 无档/area 无 rect)→ 空读数:reader 既有 no-read
        # 语义(不抛不猜,对账侧按显示侧无条目计数),禁回退硬编码 rect
        # 静默对陈旧区域 OCR(坐标单一真相源)。
        return FactionPanelReading()
    full = Rect(rect.x1, rect.y1, rect.x2, max(rect.y2, _PANEL_Y2_EXT))

    name_rect = Rect(_NAME_RECT_X1, full.y1, full.x2, full.y2)
    ocr = ctx.ocr_service.get_ocr_result_list

    def _toks(r: Rect) -> list[tuple[str, int, int, int, int]]:
        return [(t.data or '', t.x, t.y, t.x + t.w, t.y + t.h)
                for t in ocr(image=screen, rect=r, crop_first=True)]

    name_toks = _toks(name_rect)
    return parse_panel_tokens(name_toks, _badge_tokens(ctx, screen, name_toks))


def _read_badge_digit(ctx: SrContext, screen: MatLike,
                      cy: int, cx: int) -> tuple[str, int, int, int, int] | None:
    """定位读单个徽章数字:徽章圆内字框裁切 → 反相 → 放大 → OCR。

    返回纯数字 token(全帧坐标)或 None(各偏移档均读不出)。反相 =
    白字黑底 → 黑字白底(paddle rec 习惯);框半宽避开圆环(环被读成
    '0',16 帧对拍实测);多偏移档覆盖徽章相对名行的 +29~+38 抖动。
    """
    ocr = ctx.ocr_service.get_ocr_result_list
    for dy0 in _BADGE_DY_CANDS:
        y1, y2 = cy + dy0 - _BADGE_BOX_DY, cy + dy0 + _BADGE_BOX_DY + 1
        crop = screen[y1:y2, cx - _BADGE_BOX_DX:cx + _BADGE_BOX_DX]
        if crop.size == 0:
            continue
        gray = 255 - cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        s = _BADGE_UPSCALE
        up = cv2.resize(gray, (gray.shape[1] * s, gray.shape[0] * s),
                        interpolation=cv2.INTER_CUBIC)
        up = cv2.copyMakeBorder(up, 40, 40, 40, 40,
                                cv2.BORDER_CONSTANT, value=255)
        try:
            res = ocr(image=cv2.cvtColor(up, cv2.COLOR_GRAY2RGB))
        except Exception:   # noqa: BLE001  OCR 异常按该档失读,继续下一档
            continue
        if res and (res[0].data or '').strip().isdigit():
            text = res[0].data.strip()
            return (text, cx - _BADGE_BOX_DX, y1, cx + _BADGE_BOX_DX, y2)
    return None


def _badge_tokens(ctx: SrContext, screen: MatLike,
                  name_toks: list[tuple[str, int, int, int, int]]
                  ) -> list[tuple[str, int, int, int, int]]:
    """逐锚点定位读徽章数字(常规 cx=91;特殊态回退 cx=120)。

    特殊态守卫:仅当锚点窗口内**无灰梯 token**(含 ``/`` 的名称带 token,
    如 '3/5/7/10')时才试 cx=120——常规条目必有灰梯且其首数字恰落在
    cx=120 窗内,无守卫会把灰梯数字误当徽章;无灰梯 = 独立羁绊条目
    (如领航员,徽章右移、无梯)。
    """
    anchors = _extract_anchors(name_toks)
    out: list[tuple[str, int, int, int, int]] = []
    for cy, _y2, _fac, _raw in anchors:
        tok = _read_badge_digit(ctx, screen, cy, _BADGE_CX)
        if tok is not None:
            out.append(tok)
            continue
        has_ladder = any('/' in t and cy + 5 <= (y1 + y2) // 2 <= cy + _BADGE_DY_MAX
                         for t, _x1, y1, _x2, y2 in name_toks)
        if has_ladder:
            continue
        tok = _read_badge_digit(ctx, screen, cy, _BADGE_CX_SPECIAL)
        if tok is not None:
            out.append(tok)
    return out


def compare_factions(computed: dict[str, int],
                     displayed: list[tuple[str, int]],
                     unreadable: list[str] | None = None) -> FactionReconcileResult:
    """对账纯函数:计算侧(主源)vs 显示侧 → 逐名三态 + 不评口径计数。

    - 逐名三态:一致(match)/ 不一致(mismatch)/ 显示侧不可判
      (display_unreadable,即徽章失读;OCR 失败跳过不算不一致);
    - computed 有而 displayed 没有 → 截断嫌疑(单独计数,不判错;
      显示只列可见条目,底部截断是常态);
    - displayed 有而 computed 没有 → computed_missing(显式第四态:
      计算侧是全集主源,该形态= 计算侧漏贡献或名称配错,判 mismatch
      同级留证但单独命名便于归因)。
    """
    res = FactionReconcileResult()
    shown: set[str] = set()
    for fac, cnt in displayed:
        shown.add(fac)
        if fac not in computed:
            res.rows.append(FactionReconcileRow(fac, None, cnt, 'computed_missing'))
        elif computed[fac] == cnt:
            res.rows.append(FactionReconcileRow(fac, computed[fac], cnt, 'match'))
        else:
            res.rows.append(FactionReconcileRow(fac, computed[fac], cnt, 'mismatch'))
    res.ocr_skipped = list(unreadable or [])
    res.truncation_suspects = [f for f in computed if f not in shown]
    return res


def report_faction_reconcile(result: FactionReconcileResult, **kwargs) -> int:
    """把 mismatch 行落缺陷台账(kind=``faction_display_mismatch``)。

    已接线:生产调用方 = cw_screen_prep 羁绊对账段(与 ``compare_factions``
    串同一链路;行为锁见测试仓 faction_reconcile/faction_wire 两锁文件)。
    函数本身保持纯转发:
    逐 mismatch 调 ``record_defect``(kernel/cw_telemetry_exit 出口钩子位,
    分包期 4 起零直依 telemetry;run_id 门控/分级/安灯语义单一源在 telemetry),
    返回落账行数。
    """
    from sr_od.application.currency_war.kernel.cw_telemetry_exit import record_defect
    n = 0
    for r in result.rows:
        if r.verdict != 'mismatch':
            continue
        record_defect(
            surface='board', kind='faction_display_mismatch',
            expected=str(r.computed), observed=str(r.displayed),
            note=f'faction={r.faction}', **kwargs)
        n += 1
    return n
