"""货币战争 **节点选项观测**:遭遇/补给/伙伴 overlay 截图 → ``EncounterOption`` 等
(喂 ``cw_events.decide_*`` / 策略 ``decide_encounter`` 等钩子)。

与 ``cw_observation``(备战屏 reads)分模块:本模块只管**节点 overlay 的选项读取**(decide_* 的输入)。
决策接线 audit(2026-08-07,``.debug/temp/currency_war/decision_wiring_audit.md``):这些 decide_*
策略钩子早已就绪,缺的是 **reader** —— 本模块补 reader,handler 才能调 decide_* 用真数据(非硬编码默认)。

每 reader 纯函数(可单测,喂 fixture OCR);坐标/带状过滤来自实机建档
(``docs/game/screens/currency_war_encounter.md`` 等)。
"""
from __future__ import annotations

import re

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from sr_od.application.currency_war.kernel.cw_events import (
    EncounterOption,
    SupplyOption,
)
from sr_od.application.currency_war.kernel.cw_obs_core import _area_rect
from sr_od.context.sr_context import SrContext

# 遭遇卡标题「遭遇其X」→ X 中文数字 → 难度档(其一=1 易 … 其六=6);decide_encounter 按难度选。
# ⚠️ 「一」笔画细,paddle OCR 常**漏读**(左卡=易卡=其一,OCR 成「遭遇其」无数字,实机 baseline 核实
# 2026-08-07)→ 数字设**可选**:无数字 → 默认难度 1(即漏了「一」的易卡)。其四(四 笔画清)读得稳。
_CN_NUM: dict[str, int] = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6}
_TITLE_RE = re.compile(r'遭遇其([一二三四五六])?')
# 奖励文本带(「奖励预览」标签 y≈568 下方,y≈600-690;排除标签本身)。实机 baseline 核实(2026-08-07)。
_REWARD_Y_LO, _REWARD_Y_HI = 600, 695
_REWARD_LABEL = '奖励预览'


def read_encounter_options(ctx: SrContext, screen: MatLike) -> list[EncounterOption]:
    """OCR 遭遇屏两张(或多)卡 → ``EncounterOption`` 列表(difficulty 从标题其X;reward 从奖励带)。

    遭遇**选项 UI 不显词缀**(词缀战后才显;design 08 的 affix 分支对此屏 N/A)→ ``affixes=[]``。
    按 title center-x 左→右排序 → ``idx``。decide_encounter 用 difficulty + comp 成型度选(formed→高难度拿好奖励,
    未成型→低难度保生存)。读不到 title(OCR 漏/非遭遇屏)→ 返 [](handler 退默认 idx0)。
    """
    ocr_map = ctx.ocr_service.get_ocr_result_map(
        image=screen, rect=None, color_range=None, crop_first=False,
    )
    # 1) 找卡标题「遭遇其X」(X 可选,漏读「一」→ 无数字)→ (center_x, difficulty)
    cards: list[tuple[int, int]] = []
    for text, mrl in ocr_map.items():
        if mrl.max is None:
            continue
        m = _TITLE_RE.search(text)
        if m is None:
            continue
        num_str = m.group(1)
        num = _CN_NUM.get(num_str) if num_str else 1   # 无数字 = 「一」漏读 → 难度 1(易卡)
        cards.append((mrl.max.center.x, num))
    cards.sort(key=lambda c: c[0])
    if not cards:
        return []
    # 2) 奖励文本(奖励带内、≥2 字、非标签)→ 按 x 就近归卡
    rewards: list[tuple[int, str]] = []
    for text, mrl in ocr_map.items():
        if mrl.max is None or text == _REWARD_LABEL or len(text) < 2:
            continue
        cy = mrl.max.center.y
        if _REWARD_Y_LO <= cy <= _REWARD_Y_HI:
            rewards.append((mrl.max.center.x, text))
    opts: list[EncounterOption] = []
    for idx, (cx, diff) in enumerate(cards):
        nearest = min(rewards, key=lambda r: abs(r[0] - cx))[1] if rewards else ''
        opts.append(EncounterOption(
            idx=idx, difficulty=diff, affixes=[],
            rewards=[nearest] if nearest else [],
        ))
    return opts


# 「剩余次数：N」(底行,「选择」按钮左侧;其左的圆箭头图标 = 分支刷新按钮)。分支刷新 =
# 优势布局「分支刷新」授予的能力(每局 1 次,重置两卡难度与奖励;bwiki 优势布局表,
# docs/game/currency_war/data/advantage_layouts.md;competitors.md 节点表同口径)。
# 未激活该布局时此行是否显示未采证 → 读不到按无刷新处理(失败安全)。
_REMAIN_RE = re.compile(r'剩余次数\s*[：:]\s*(\d+)')
# 计数行 OCR 带(归档帧 sr-od-test/screens/货币战争-遭遇节点/default.webp:文本 ≈(730-845,900)。
# x 上界收到 1000:避开「选择」按钮文本区;正则本身已滤非「剩余次数」文本,带只是省 OCR 量)。
_REMAIN_RECT = Rect(300, 840, 1000, 960)


def read_encounter_refresh_count(ctx: SrContext, screen: MatLike) -> tuple[int, tuple[int, int]] | None:
    """OCR「剩余次数:N」→ ``(剩余次数, 文本中心点)``;读不到 → ``None``。

    文本中心供 handler **文本锚定**分支刷新圆钮(圆钮 = 文本左侧固定偏移,与投资策略
    ``_try_click_refresh`` 同模式——单帧证据不足判文本位置漂移形态,固定 area 不可行)。
    全角/半角冒号都认(OCR 渲染不一)。纯读。
    """
    ocr_map = ctx.ocr_service.get_ocr_result_map(
        image=screen, rect=_REMAIN_RECT, color_range=None, crop_first=False,
    )
    for text, mrl in ocr_map.items():
        if mrl.max is None:
            continue
        m = _REMAIN_RE.search(text)
        if m is None:
            continue
        return int(m.group(1)), (int(mrl.max.center.x), int(mrl.max.center.y))
    return None


# ===== 投资策略/投资环境 刷新计数 reader(观察通道)=====
# 两屏交互模型不同构(归档帧实证,三张):策略屏逐卡刷新(每卡一组
# 「刷新圆钮 icon + 刷新次数N」,N 独立扣减)/ 环境屏整组重掷(单个全局钮 +
# 剩余次数:N)。正则族两支 = 两屏冒号/无冒号形态(策略屏「刷新次数1」无冒号、
# 环境屏「剩余次数：1」全角冒号,均为在册 OCR 实证)。
_INVEST_REMAIN_RE = re.compile(r'剩余次数\s*[：:]\s*(\d+)')
_INVEST_REFRESH_COUNT_RE = re.compile(r'刷新次数\s*(\d+)')
# 计数行 OCR 带:单一真相源 = screen_info(策略屏「区域-刷新次数行」/环境屏
# 「区域-剩余次数行」,读经 ``_area_rect``;缺失/读失败回退下方同值兜底常量,
# 失败安全)。带只裁 OCR 量,不承点击坐标真相——点击走文本锚定偏移,非本带。
# - 策略屏:三组「刷新次数N」文本 y≈841-869、x≈421-1530(归档帧 CV/OCR 实测;
#   旧 docstring 记 y≈841 与归档帧一致)。
# - 环境屏:「剩余次数：N」文本 x≈703-842、y≈969-997;x 上界 1000 避开「确认」
#   (x≥1054)文本区。
_INVEST_STRATEGY_COUNT_RECT = Rect(300, 830, 1560, 880)
_INVEST_ENV_COUNT_RECT = Rect(300, 955, 1000, 1010)
# kind → (画面名, area 名, 兜底 rect);未知 kind 沿 env 支(与原三元选择同语义)。
_COUNT_RECT_SPECS: dict[str, tuple[str, str, Rect]] = {
    'strategy': ('货币战争-投资策略', '区域-刷新次数行',
                 _INVEST_STRATEGY_COUNT_RECT),
    'env': ('货币战争-投资环境', '区域-剩余次数行', _INVEST_ENV_COUNT_RECT),
}


def read_invest_refresh_counts(
        ctx: SrContext, screen: MatLike,
        kind: str) -> list[tuple[int, int, int]]:
    """OCR 投资屏刷新计数 → ``[(count, 文本中心x, 文本中心y), ...]``(纯读)。

    kind = 'strategy'(逐卡计数,可多条)/ 'env'(全局计数,至多一条;正则同
    支兼容「剩余次数:0」等形态)。读不到 → [](无授予/读缺的判定归调用方,
    失败安全)。OCR 裁剪带取 screen_info 对应 area(缺失回退同值兜底常量)。
    文本中心供 handler 文本锚定刷新圆钮(单帧证据不足判文本漂移
    形态,固定 area 不可行——遭遇屏先例同款)。计数 0 的灰置态可读(归档帧
    card3_refreshed 实证:灰置但清晰,对比度 ~150 仍在 OCR 可读域)。
    **走 list 形态 API**(get_ocr_result_list 非 map):策略屏三卡计数常态同文
    (「刷新次数1」×3),map 按文本为键会收敛成一_entry 丢位(ocr_service.
    convert_list_to_map),list 按检测逐条保留位置——三槽计数齐读的前提。
    """
    _screen_name, _area_name, _fallback = _COUNT_RECT_SPECS.get(
        kind, _COUNT_RECT_SPECS['env'])
    try:
        rect = _area_rect(ctx, _area_name, _screen_name) or _fallback
    except Exception:   # noqa: BLE001  画面档读取失败安全,回退兜底带
        rect = _fallback
    pattern = (_INVEST_REFRESH_COUNT_RE if kind == 'strategy'
               else _INVEST_REMAIN_RE)
    results = ctx.ocr_service.get_ocr_result_list(
        image=screen, rect=rect, color_range=None, crop_first=False,
    )
    out: list[tuple[int, int, int]] = []
    for r in results:
        m = pattern.search(r.data or '')
        if m is None:
            continue
        c = r.center
        out.append((int(m.group(1)), int(c.x), int(c.y)))
    out.sort(key=lambda t: t[1])
    return out


# x 就近配对容差(执行层几何常量,非策略数值):三卡槽锚 x ≈{460,960,1460}
# (槽距 ~500px),计数文本实测距槽锚 ≤ ~20px(归档帧 V7)——取半槽距 250 为
# 「这条计数属于这槽」的布局推导上界;超界 = 读缺形态(如中槽文本漏读时其右
# 邻文本相距 514px)→ 落 None,防邻槽计数被误配颠覆「计数>0 才点」的权威闸
# (fail-closed 方向:误配最坏多试一次点击)。
_PAIR_X_TOL = 250


def pair_refresh_counts_to_slots(
        counts: list[tuple[int, int, int]],
        slot_xs: list[int]) -> list[tuple[int, int, int] | None]:
    """把逐卡计数文本按 x 就近配对到画面槽(策略屏三槽;纯函数可单测)。

    每槽取 x 距离最近的一条计数文本,一条只配一槽(防同文本重复消费);
    距离超 ``_PAIR_X_TOL``(半槽距)→ 该槽落 None = 读缺。槽序 = slot_xs 下标
    (画面左→右,与 CwActionPickEventParam.refresh_slots 同坐标系)。计数条数 ≠ 槽数
    (读缺/碎片)时缺口落 None,调用方按无授予处理(失败安全)。
    """
    remaining = list(range(len(counts)))
    out: list[tuple[int, int, int] | None] = []
    for sx in slot_xs:
        if not remaining:
            out.append(None)
            continue
        best = min(remaining, key=lambda k: abs(counts[k][1] - sx))
        if abs(counts[best][1] - sx) > _PAIR_X_TOL:
            out.append(None)
            continue
        remaining.remove(best)
        out.append(counts[best])
    return out


# 补给选项 y 带。2026-08-26 多样本核对(66 帧存档离线 OCR 对拍)两种布局:
# ① 单装备行:角色名 cy513-567 / 装备名 cy~648-716;② 双装备行(每列 角色+2 装备):
# 第一行 y≈648、**第二行 y≈748-749** —— 旧上界 735 使②整行漏读(10 选只读出 4,
# decide_supply 建模残缺)。上界放宽到 780:实测各帧 750-780 无任何文本中心
# (最近下方元素「已选择/确认」在 y≥920,余量充足);①布局帧放宽前后结果逐一相同。
_SUPPLY_CHAR_Y: tuple[int, int] = (500, 600)
_SUPPLY_EQUIP_Y: tuple[int, int] = (640, 780)
_SUPPLY_CARD_CLICK_Y: int = 550   # 卡身选中 y(沿用 CwScreenSupplyNode.CARD_BODY;点卡身不开对话直接选中)
_SUPPLY_COL_X_TOL: int = 150      # 角色-装备同列 x 容差(配对用)
# 钻装备名集合(文本兜底;主通道 = SIFT——用户 2026-08-17:装备图已采集,SIFT 稳,
# OCR 艺术字有形变史,钻价值极高,漏判丢钻/误判浪费刷新,代价不对称)。
# 财富宝钻同类高价值。「红钻/蓝钻」补给角色穿戴出现,advantage「钻石闪耀」同源。
DIAMOND_EQUIP_NAMES: frozenset[str] = frozenset({'红钻', '蓝钻', '财富宝钻'})


def _equip_is_diamond(equip_name: str) -> bool:
    """文本兜底:装备名精确匹配三钻(非子串——防「虫洞掘进钻头」类带钻字误判)。"""
    return equip_name in DIAMOND_EQUIP_NAMES


def _sift_detect_diamonds(ctx: SrContext, screen: MatLike,
                          columns: list[tuple[int, int]]) -> set[int]:
    """SIFT 主通道:补给卡装备 icon 区扫三钻模板 → 带钻列索引集合。

    复用 read_equips 的模板匹配(ensure_equip_sift_templates 全量装备库,含三钻);
    扫描区 = 各列的 x 范围并集 × 装备区 y 带。模板库缺/无命中 → 空集(调用方落文本兜底)。纯读。

    ✅ 实测对拍(2026-08-17,31 张存档补给画面):4 张命中(3 蓝钻 1 红钻,
    y≈705-716 icon 带,x 归列正确),27 张零误报;红钻样本三方对拍一致
    (SIFT@x506y716 inliers9 = VLM「第2列红宝石」= OCR 装备名「红钻」)。
    """
    if not columns:
        return set()
    from sr_od.application.currency_war.obs.cw_equipment import (
        ensure_equip_sift_templates,
        read_equips,
    )
    templates = ensure_equip_sift_templates(ctx)
    if not templates:
        return set()
    diamond_tms = {n: t for n, t in templates.items() if n in DIAMOND_EQUIP_NAMES}
    if not diamond_tms:
        return set()
    # 扫描带:所有列的 x 范围并集 × 装备区 y 带(r1 review#5:y 带 580-780 加宽
    # 覆盖实测命中 705-716 + 布局微变余量;右界由 screen 实宽派生,不假定 1920)
    x1 = max(0, min(cx for cx, _ in columns) - 160)
    x2 = min(screen.shape[1] - 1, max(cx for cx, _ in columns) + 160)
    hits = read_equips(screen, diamond_tms, equip_rect=(x1, 580, x2, 780))
    # 命中归列(最近列心)
    out: set[int] = set()
    for _name, (hx, _hy), _inl in hits:
        best = min(range(len(columns)), key=lambda i: abs(columns[i][0] - hx))
        if abs(columns[best][0] - hx) <= _SUPPLY_COL_X_TOL:
            out.add(best)
    return out


def read_supply_options(ctx: SrContext, screen: MatLike) -> list[tuple[SupplyOption, Point]]:
    """OCR 补给选项(每列 = 角色卡 + 装备)→ ``[(SupplyOption, 卡身点击点)]``,按 x 左→右。

    布局:**列数动态探测**(通常 4 选 1;「全都要」类效果减 2 列、「人身意外险」类加补给
    阶段可增列,augment 改写下实测见 3-5 不等——历史 docstring 的「3 选 1」「实测 5」均为
    特例表述,勿写死),每列 = 角色名(y≈545)+ 装备名(y≈680),点卡身(y≈550)选中 +
    右下「确认」。**刷新圆钮实存**(「剩余次数」文本锚左侧固定偏移点击,宿主 = 画面 op
    留守臂 ``cw_screen_supply_node.py``;本读链只读选项,不读刷新剩余——
    剩余读数闸 = 容器 ``supply_refresh_left`` 剩余语义观察真值,由画面 op
    观察 node 同帧读经 report 摄入,全域规范 = ``screens/op-layer.md`` §1.4)。
    钻识别双通道 ✅(2026-08-17):主 = SIFT(装备 icon 区 y600-760 扫三钻模板,装备图已采集);
    兜底 = 装备名精确匹配。

    装备行定义列(每装备名 = 1 选项),角色按最近 x 配对(``get_char`` roster 校验,滤噪)。读不到 → []
    (handler 退默认 ``CARD_BODY``)。
    """
    from sr_od.application.currency_war.data.cw_chars import get_char
    ocr_map = ctx.ocr_service.get_ocr_result_map(
        image=screen, rect=None, color_range=None, crop_first=False,
    )
    equips: list[tuple[int, str]] = []   # (cx, name)
    chars: list[tuple[int, str]] = []    # (cx, name) roster-validated
    for text, mrl in ocr_map.items():
        if mrl.max is None or not text:
            continue
        cx, cy = mrl.max.center.x, mrl.max.center.y
        if _SUPPLY_EQUIP_Y[0] <= cy <= _SUPPLY_EQUIP_Y[1]:
            equips.append((cx, text))
        elif _SUPPLY_CHAR_Y[0] <= cy <= _SUPPLY_CHAR_Y[1] and get_char(text) is not None:
            chars.append((cx, text))
    equips.sort(key=lambda e: e[0])
    # 钻识别双通道:主 = SIFT(装备 icon 区扫三钻模板,稳);兜底 = 装备名精确匹配
    # (OCR 艺术字形变风险;两通道任一命中即钻)。
    _sift_diamonds = _sift_detect_diamonds(ctx, screen, [(ex, 0) for ex, _n in equips])
    out: list[tuple[SupplyOption, Point]] = []
    for i, (ex, ename) in enumerate(equips):
        ch = ''
        if chars:
            ncx, nname = min(chars, key=lambda c: abs(c[0] - ex))
            if abs(ncx - ex) < _SUPPLY_COL_X_TOL:
                ch = nname
        has_d = (i in _sift_diamonds) or _equip_is_diamond(ename)
        out.append((SupplyOption(idx=i, char=ch, equip=ename, has_diamond=has_d),
                    Point(ex, _SUPPLY_CARD_CLICK_Y)))
    return out
