# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 **节点选项观测**:遭遇/补给/巨星/伙伴 overlay 截图 → ``EncounterOption`` 等
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
from sr_od.application.currency_war.cw_events import (
    EncounterOption,
    MegastarOption,
    SupplyOption,
)
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


# 巨星候选标题「盛会之星一X先生/女士!」→ X = 角色名(花火/星期日…)。实测 OCR 核实(2026-08-07 cw_megastar)。
# 先生/女士 + 全/半角叹号容错(OCR 渲染不一)。
_MEGASTAR_RE = re.compile(r'盛会之星一(.+?)(先生|女士)[!！]?')


def read_megastar_options(ctx: SrContext, screen: MatLike) -> list[MegastarOption]:
    """OCR 巨星节点候选 → ``MegastarOption`` 列表(char_id 从「盛会之星一X先生/女士!」解析)。

    巨星候选 = 盛会之星 bond(花火/星期日…)给全队 buff。按候选名 center-x 左→右排序 → ``idx``。
    候选名位置 = 点击位置(实测 RunMegastarNode 点 (822,333) 命中花火;名 = 卡身选中区)。decide_megastar
    按 target.core_chars 选(含盛会之星 → 绑该角色;否则 buff 契合)。读不到 → [](handler 退默认 idx0)。
    """
    ocr_map = ctx.ocr_service.get_ocr_result_map(
        image=screen, rect=None, color_range=None, crop_first=False,
    )
    cands: list[tuple[int, str]] = []   # (center_x, char_id)
    for text, mrl in ocr_map.items():
        if mrl.max is None:
            continue
        m = _MEGASTAR_RE.search(text)
        if m is None:
            continue
        cands.append((mrl.max.center.x, m.group(1)))
    cands.sort(key=lambda c: c[0])
    return [MegastarOption(idx=i, char_id=name) for i, (_cx, name) in enumerate(cands)]


# 补给选项 y 带(实捕 round1-5:角色名 y≈545 / 装备名 y≈680;TODO 多样本核,布局可能随补给类型微变)。
_SUPPLY_CHAR_Y: tuple[int, int] = (500, 600)
_SUPPLY_EQUIP_Y: tuple[int, int] = (640, 735)
_SUPPLY_CARD_CLICK_Y: int = 550   # 卡身选中 y(沿用 RunSupplyNode.CARD_BODY;点卡身不开对话直接选中)
_SUPPLY_COL_X_TOL: int = 150      # 角色-装备同列 x 容差(配对用)


def read_supply_options(ctx: SrContext, screen: MatLike) -> list[tuple[SupplyOption, Point]]:
    """OCR 补给选项(每列 = 角色卡 + 装备)→ ``[(SupplyOption, 卡身点击点)]``,按 x 左→右。

    布局(实捕 round1-5 补给,视觉大模型 + OCR 核实):N 列(实测 5;docstring 旧「3 选 1」过时),每列 =
    角色名(y≈545)+ 装备名(y≈680),点卡身(y≈550)选中 + 右下「确认」。**无刷新按钮**(decide_supply
    调用方传 ``refresh_used=True`` 跳过刷新逻辑)。钻(红/蓝 = 基本赢)视觉判定待补(``has_diamond`` 恒 False,TODO)。

    装备行定义列(每装备名 = 1 选项),角色按最近 x 配对(``get_char`` roster 校验,滤噪)。读不到 → []
    (handler 退默认 ``CARD_BODY``)。
    """
    from sr_od.application.currency_war.cw_chars import get_char
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
    out: list[tuple[SupplyOption, Point]] = []
    for i, (ex, ename) in enumerate(equips):
        ch = ''
        if chars:
            ncx, nname = min(chars, key=lambda c: abs(c[0] - ex))
            if abs(ncx - ex) < _SUPPLY_COL_X_TOL:
                ch = nname
        out.append((SupplyOption(idx=i, char=ch, equip=ename, has_diamond=False),
                    Point(ex, _SUPPLY_CARD_CLICK_Y)))
    return out
