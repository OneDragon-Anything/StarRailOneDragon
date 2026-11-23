"""开拓商店(银轨商店)面板读数层:余额 / 四商品槽结构化读卡 / 帕姆王进度。

``analyze_screen`` 对「货币战争-备战-开拓商店」的 extras 读数主体(obs/recognizers
注册的 :class:`~sr_od.application.currency_war.obs.recognizers.train_shop_recognizer.
TrainShopPanelRecognizer` 与后续画面 op 共用本模块,单一实现)。结构仿金币商店
``read_shop_cards`` 同构:定长槽数组 + {kind, card} 元素,差异面:

- 槽带 = 定长 4 槽商品混合池;「全部刷新」钮**轮转占位**——可占 1-4 任一槽
  (槽 1 = 第十一局实测;槽 4 = 第二十四局 2-4 实拍「1 力/次」),也可不在场
  (1-6 实拍四槽全商品;金币商店 5 牌无此形态);刷新钮按名行文本识别其槽位,
  不按固定槽位锚定;
- 身份双源:SIFT 立绘识别(角色卡)优先,名行文字 OCR 兜底(属性加成卡无立绘,
  只走 OCR——金币商店纯 SIFT,本面板卡面有属性文字卡故双源);
- 费用 = 名行行尾数字 OCR(开拓力标价;金币商店的费用徽章两级管线不适用,
  本面板标价渲染在卡底名行,无独立徽章);
- 星级恒 None:卡面无星级徽标,入场星级规则未建模(字段与金币商店 ShopCard
  对齐预留);试用标记沿用金币商店「试用」标签统一判别(实测 4 槽 5 帧
  零命中——列车商店未见试用形态,字段保留)。

**模式二态**(面板有两种呈现形态,fixture = sr-od-test/screens/货币战争-备战-开拓商店/
panel_slots_{a,b,c}_r13、panel_slots_{d,e}_r15、panel_showcase_r13、
panel_showcase_deadlock_r13):

- ``slots``(常规槽带态):详情按钮锚命中 ≥ 2(每槽卡底「详情」钮,实测恒 4/4);
  槽 1-4 逐槽读,刷新钮所在槽(名行「全部刷新」锚)kind=refresh,其余商品;
- ``showcase``(中央展示卡态):**四信号齐才判**——详情命中 ≤ 1(展示卡自带
  「详情」钮落「按钮-详情-3」区,实测恒 1)+ 展示卡有名行 + 槽 1 亮度落暗带
  + 名行 1/2/4 全空,缺一 unknown 不猜。实测两帧(第十一局首开帧 013105 与
  第十三局恢复态死锁帧 122630)画面同构——本态 = 玩家卡「首开空池软锁态」
  (银轨首次开张自动弹面板)或恢复态死锁(游戏侧缺陷已登记),读层无法也不必
  区分二者,如实产出展示卡读数与点击坐标,处置语义归调用方(玩家卡操作节:
  解锁 = 点中央展示卡)。
  旧判定(「槽 1 名行 = 全部刷新」单锚 + 展示卡有名行 + 槽 1 暗三信号)对
  四槽全商品形态失效,已实测双重误触发:商品卡槽 1 亮度 50.6/40.7 落暗带
  (< 55),展示卡 rect(940-1150)与商品卡-3 rect(933-1153)近同位读到商品
  文字——单锚架构整体退役,详情按钮锚与槽位无关,是两态间唯一实测稳定的
  区分信号(证据帧 = cw-live-r15 game24-r15b_railshop_*.png,第二十四局)。

帕姆王进度 = 「读区-帕姆王进度」OCR「N/500」(N = 本局累计消费,满 500 送帕姆王,
每局从 0 重起);分母恒 500 实测,非 500 判误读返 None(保守不猜)。注意:首开
空池帧(013105)实测帕姆块整体未渲染读 None,与玩家卡「软锁态全程可读」(另局
2026-11-20 口径)两样本并存——读层只报实读,不裁口径。
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from one_dragon.utils import str_utils
from sr_od.application.currency_war.data.cw_chars import get_char
from sr_od.application.currency_war.kernel.cw_obs_core import (
    PIONEER_SHOP_SCREEN_NAME,
    _area_rect,
    _ocr,
)
from sr_od.application.currency_war.obs.currency_war_char_id import (
    identify_character,
)
from sr_od.application.currency_war.obs.cw_identity_obs import (
    ensure_portrait_templates,
    resolve_char_name,
)
from sr_od.application.currency_war.obs.cw_observation import (
    _trial_badge_hit_in_crop,
)

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from sr_od.context.sr_context import SrContext

# 画面档 area 名(单一真相源 = currency_war_battle_prep_pioneer_shop.yml)
A_TS_CARD_PREFIX: str = '商品卡-'          # 商品卡-1..4(槽带)+ 商品卡-展示(展示卡)
A_TS_NAME_PREFIX: str = '商品名行-'        # 商品名行-1..4(卡底名行 OCR 带)
A_TS_DETAIL_PREFIX: str = '按钮-详情-'      # 按钮-详情-1..4(槽带态锚;showcase 态
#                                           仅展示卡自带「详情」钮落按钮-详情-3)
A_TS_REFRESH_COST: str = '读区-刷新费用'    # 槽 1 名行行尾「1」窄窗(宽带 det 漏检,先裁路径可读)
A_TS_BALANCE: str = '读区-星穹列车币'       # 顶部开拓力余额(area 名沿用建档旧称,货币名 = 开拓力)
A_TS_PAM: str = '读区-帕姆王进度'          # 右侧帕姆王进度环数字
A_TS_SHOWCASE_CARD: str = '商品卡-展示'     # 中央展示卡(showcase 态唯一卡)

#: 「全部刷新」锚文本(刷新钮名行 text;op 守卫与读层共用)
REFRESH_ANCHOR_TEXT: str = '全部刷新'
#: 详情按钮锚文本(槽带态判定;与画面档 area text 同值)
DETAIL_ANCHOR_TEXT: str = '详情'

#: 槽带态判定阈:详情按钮 OCR 命中数 ≥ 2。槽带态每槽卡底一枚「详情」钮,
#: 实测恒 4/4(1-6 两帧 + r13 三 slots 帧);showcase 态仅展示卡自带一枚落
#: 「按钮-详情-3」,实测恒 1——阈 2 取两组样本间隔中点(fixture 见模块 docstring)。
#: 公开常量:买/刷 op 守卫同源消费(判据单一源,禁 op 侧复刻)。
PANEL_DETAIL_HIT_MIN: int = 2
#: showcase 态判定的槽 1 亮度阈(showcase 态同区暗底 40.8-40.9;阈 55。
#: 注意:商品卡槽 1 亮度 40.7-50.6 同落暗带——本阈只作 showcase 四信号之一,
#: 不可单独作槽带态判定)
_SHOWCASE_SLOT1_BRIGHT_MAX: float = 55.0
_BALANCE_MAX: int = 99999
#: 帕姆王解锁阈值(分母真值;实测 0/500、15/500、60/500、136/500;非 500 = 误读)
PAM_TARGET: int = 500

# OCR 名行读音修复:属性加成卡名的档位后缀罗马数字「Ⅰ」被 OCR 读成
# 「|」/「l」/「I」/「1」(实测「后台强度Ⅰ」→「后台强度|」),按已知结构修复
# (AGENTS §8 识别结构已知文本应用规则修复);非空 CJK 结尾才改写,不碰英文名。
_ATTR_TAIL_FIX = re.compile(r'^(.+[\u4e00-\u9fff])[|lI1]$')


def normalize_attr_name(name: str) -> str:
    """OCR 名行文本 → 规范商品名(纯函数):档位后缀「|」等误读修复为「Ⅰ」。"""
    m = _ATTR_TAIL_FIX.match(name.strip())
    return f'{m.group(1)}Ⅰ' if m else name.strip()


def split_name_cost(entries: list[tuple[str, int]]) -> tuple[str, int | None]:
    """名行 OCR 条目 → ``(规范名, 标价 | None)``(纯函数)。

    ``entries`` = (文本, 中心 x) 列表;按 x 排序后行尾纯数字条目 = 标价
    (开拓力数字渲染在名行右端,货币图标在名字与数字之间,OCR 不产出),
    其余条目拼接 = 名字。无数字条目 → cost None(不猜)。
    """
    if not entries:
        return '', None
    ordered = sorted(entries, key=lambda t: t[1])
    cost: int | None = None
    name_parts: list[str] = []
    for text, _x in ordered:
        t = (text or '').replace(' ', '')
        if not t:
            continue
        if t.isdigit():
            cost = int(t)
        else:
            name_parts.append(t)
    return normalize_attr_name(''.join(name_parts)), cost


def is_refresh_anchor(texts: list[str]) -> bool:
    """名行 OCR 文本 → 「全部刷新」锚命中(纯函数;lcs 0.7 与画面档同域)。"""
    return any(str_utils.find_by_lcs(REFRESH_ANCHOR_TEXT, t or '', percent=0.7)
               for t in texts)


def parse_pam_text(texts: list[str]) -> tuple[int, int] | None:
    """帕姆王读区 OCR 文本 → ``(当前进度, 目标)``(纯函数);读不到/形态不符 → None。

    分母恒 ``PAM_TARGET``(500):非 500 = OCR 误读,保守返 None 不猜。
    """
    for t in texts:
        m = re.search(r'(\d+)\s*/\s*(\d+)', t or '')
        if m is None:
            continue
        cur, target = int(m.group(1)), int(m.group(2))
        if target == PAM_TARGET and 0 <= cur <= target:
            return cur, target
    return None


@dataclass
class TrainShopCard:
    """开拓商店单张卡面读数(JSON 经 asdict 展开;字段对齐金币商店 ShopCard 差异面)。

    ``slot`` 坐标系 = 商品卡区物理槽位 1-4(左→右,= screen_info「商品卡-N」序号,
    生成期快照);``x`` = 槽卡 rect 中心 x(点击用,坐标新鲜度归调用方)。
    ``item_type``:char = SIFT 命中注册表角色;other = 非角色卡(属性加成/列车
    改件/刷新钮,身份来自名行 OCR);faction:registry 首阵营 / '?'=未识别
    (非注册角色,与金币商店同语义)。``star`` 恒 None(卡面无星级,未建模)。
    """

    slot: int
    x: int
    name: str
    faction: str
    cost: int | None
    star: int | None
    trial: bool
    item_type: str


@dataclass
class TrainShopSlot:
    """单槽三态:{kind, card}(仿金币商店 ShopSlot)。

    kind:refresh = 「全部刷新」钮(轮转占位,可在 1-4 任一槽,按名行锚识别)/
    content = 商品卡 / unknown = 应有内容但识别失败(决策一律跳过);槽带态
    槽位常满(买一补一),未观测到空槽形态,不设 empty 态(出现即 unknown 留证)。
    """

    kind: str
    card: TrainShopCard | None


def read_trainshop_balance(ctx: SrContext, screen: MatLike) -> int | None:
    """开拓力余额(读区-星穹列车币,先裁后 OCR——单字符「0」全图路径漏检实测)。

    读不到/越界(> ``_BALANCE_MAX``)→ None(不猜;软锁态两帧实测同样可读)。
    """
    rect = _area_rect(ctx, A_TS_BALANCE, PIONEER_SHOP_SCREEN_NAME)
    if rect is None:
        return None
    for r in _ocr(ctx, screen, rect, crop_first=True):
        m = re.search(r'\d+', r.data or '')
        if m is None:
            continue
        v = int(m.group())
        return v if v <= _BALANCE_MAX else None
    return None


def read_pam_progress(ctx: SrContext, screen: MatLike) -> tuple[int, int] | None:
    """帕姆王累计消费进度(N/500;软锁/死锁帧实测帕姆块缺席 → None)。"""
    rect = _area_rect(ctx, A_TS_PAM, PIONEER_SHOP_SCREEN_NAME)
    if rect is None:
        return None
    return parse_pam_text([r.data or '' for r in
                           _ocr(ctx, screen, rect, crop_first=True)])


def _refresh_cost_from_entries(entries: list[tuple[str, int]]) -> int | None:
    """刷新钮名行条目 → 标价(纯函数):按 x 序首个含数字条目取首个数字串。

    「1 力/次」混合条目(OCR 不拆货币字)与纯数字条目同判;纯文字条目跳过。
    无任何数字 → None(不猜)。
    """
    for text, _x in sorted(entries, key=lambda t: t[1]):
        m = re.search(r'\d+', text or '')
        if m is not None:
            return int(m.group())
    return None


def _count_detail_hits(ctx: SrContext, screen: MatLike) -> int:
    """四「按钮-详情-N」area OCR「详情」锚命中数(lcs 0.5 与画面档同域)。

    area 缺失(建档漂移)按未命中计——命中数不足自然落 showcase/unknown
    分支,不猜。
    """
    hits = 0
    for idx in range(1, 5):
        rect = _area_rect(ctx, f'{A_TS_DETAIL_PREFIX}{idx}',
                          PIONEER_SHOP_SCREEN_NAME)
        if rect is None:
            continue
        if any(str_utils.find_by_lcs(DETAIL_ANCHOR_TEXT, r.data or '',
                                     percent=0.5)
               for r in _ocr(ctx, screen, rect, crop_first=True)):
            hits += 1
    return hits


def _read_showcase(ctx: SrContext, screen: MatLike) -> dict | None:
    """中央展示卡读数 → {name, cost, cx, cy} | None(展示卡有名行才产出)。"""
    rect = _area_rect(ctx, A_TS_SHOWCASE_CARD, PIONEER_SHOP_SCREEN_NAME)
    if rect is None:
        return None
    crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
    if crop.size == 0:
        return None
    entries = [(r.data or '', r.center.x)
               for r in _ocr(ctx, screen, rect, crop_first=True)]
    name, cost = split_name_cost(entries)
    if not name:
        return None
    return {'name': name, 'cost': cost,
            'cx': (rect.x1 + rect.x2) // 2, 'cy': (rect.y1 + rect.y2) // 2}


def _read_slot(ctx: SrContext, screen: MatLike, idx: int,
               templates) -> TrainShopSlot:
    """读单槽(idx 1-4):刷新钮/名行/SIFT 三源判 kind,身份 SIFT 优先 OCR 兜底。

    刷新钮按名行「全部刷新」锚识别(轮转占位,任意槽位):费用 = 名行条目
    数字提取(「1 力/次」形态);名行无数字且槽 1 时走「读区-刷新费用」窄窗
    fallback(r13 形态单字符「1」宽带 det 漏检,先裁路径可读)。
    """
    rect = _area_rect(ctx, f'{A_TS_CARD_PREFIX}{idx}', PIONEER_SHOP_SCREEN_NAME)
    band_rect = _area_rect(ctx, f'{A_TS_NAME_PREFIX}{idx}', PIONEER_SHOP_SCREEN_NAME)
    if rect is None or band_rect is None:
        return TrainShopSlot(kind='unknown', card=None)   # 建档漂移:不猜留缺口
    crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
    entries = [(r.data or '', r.center.x)
               for r in _ocr(ctx, screen, band_rect, crop_first=True)]
    name_raw, cost = split_name_cost(entries)
    if is_refresh_anchor([t for t, _ in entries]):
        refresh_cost = _refresh_cost_from_entries(entries)
        if refresh_cost is None and idx == 1:
            rc_rect = _area_rect(ctx, A_TS_REFRESH_COST, PIONEER_SHOP_SCREEN_NAME)
            if rc_rect is not None:
                for r in _ocr(ctx, screen, rc_rect, crop_first=True):
                    m = re.search(r'\d+', r.data or '')
                    if m is not None:
                        refresh_cost = int(m.group())
                        break
        return TrainShopSlot(kind='refresh', card=TrainShopCard(
            slot=idx, x=(rect.x1 + rect.x2) // 2, name=REFRESH_ANCHOR_TEXT,
            faction='?', cost=refresh_cost, star=None, trial=False,
            item_type='other'))
    avatar_id, _inliers = (identify_character(crop, templates)
                           if (templates is not None and crop.size > 0)
                           else (None, 0))
    name = resolve_char_name(avatar_id) if avatar_id else ''
    if name:
        ch = get_char(name)
        faction = (ch.factions[0] if (ch is not None and ch.factions)
                   else ('' if ch is not None else '?'))
        card_name, item_type = name, 'char'
    elif name_raw:
        card_name, faction, item_type = name_raw, '?', 'other'
    else:
        return TrainShopSlot(kind='unknown', card=None)
    trial = (_trial_badge_hit_in_crop(crop)
             if crop.size > 0 else False)
    return TrainShopSlot(kind='content', card=TrainShopCard(
        slot=idx, x=(rect.x1 + rect.x2) // 2, name=card_name,
        faction=faction, cost=cost, star=None, trial=trial,
        item_type=item_type))


def _side_name_lines_empty(ctx: SrContext, screen: MatLike) -> bool:
    """名行 1/2/4 全空判定(showcase 第四信号):三 rect 任一 OCR 有内容 → False。

    槽带态名行实测恒可读(黑底白字稳),showcase 态 1/2/4 实测全空(仅名行-3
    落展示卡名)——防槽带 OCR 抖动帧(详情锚偶发低命中)误入 showcase。
    area 缺失(建档漂移)→ False(四信号不齐,判 unknown 不猜)。
    """
    for idx in (1, 2, 4):
        band_rect = _area_rect(ctx, f'{A_TS_NAME_PREFIX}{idx}',
                               PIONEER_SHOP_SCREEN_NAME)
        if band_rect is None:
            return False
        if any((r.data or '').strip()
               for r in _ocr(ctx, screen, band_rect, crop_first=True)):
            return False
    return True


def read_trainshop_panel(ctx: SrContext, screen: MatLike) -> dict:
    """面板全量读数 → {mode, shop_cards, refresh_slot, showcase_card}
    (识别器 extras 主体)。

    - mode='slots':shop_cards = 定长 4 槽(下标 0-3 ↔ 物理槽 1-4,刷新钮
      所在槽 kind='refresh');refresh_slot = 刷新钮物理槽号(不在场 None);
      showcase_card=None;
    - mode='showcase':槽带不在场(shop_cards/refresh_slot=None),showcase_card
      = 中央展示卡读数(解锁点击点 cx/cy);
    - mode='unknown':三键 None(四信号不全,不猜)。
    立绘模板经 ``ensure_portrait_templates`` 幂等加载(缺失 → 槽身份只走
    OCR 名行,角色卡降级 item_type=other,不中断)。
    """
    if _count_detail_hits(ctx, screen) >= PANEL_DETAIL_HIT_MIN:
        templates = ensure_portrait_templates(ctx)
        slots = [_slot_to_json(_read_slot(ctx, screen, i, templates))
                 for i in range(1, 5)]
        refresh_slot = next((s['card']['slot'] for s in slots
                             if s['kind'] == 'refresh'
                             and s['card'] is not None), None)
        return {'mode': 'slots', 'shop_cards': slots,
                'refresh_slot': refresh_slot, 'showcase_card': None}
    # 详情锚 ≤1:showcase 四信号判定(展示卡有名行 + 槽 1 暗带 + 名行 1/2/4
    # 全空),缺一 unknown。
    showcase = _read_showcase(ctx, screen)
    slot1_rect = _area_rect(ctx, f'{A_TS_CARD_PREFIX}1', PIONEER_SHOP_SCREEN_NAME)
    slot1_dark = False
    if slot1_rect is not None:
        crop = screen[slot1_rect.y1:slot1_rect.y2, slot1_rect.x1:slot1_rect.x2]
        slot1_dark = (crop.size > 0
                      and float(crop.mean()) < _SHOWCASE_SLOT1_BRIGHT_MAX)
    if (showcase is not None and slot1_dark
            and _side_name_lines_empty(ctx, screen)):
        return {'mode': 'showcase', 'shop_cards': None, 'refresh_slot': None,
                'showcase_card': showcase}
    return {'mode': 'unknown', 'shop_cards': None, 'refresh_slot': None,
            'showcase_card': None}


def find_refresh_slot(ctx: SrContext, screen: MatLike) -> int | None:
    """逐槽名行找「全部刷新」钮 → 物理槽号 1-4;不在场 → None(常态可不在场)。

    单一消费源 = 刷新 op 守卫定位(轮转占位,点击随槽位)——禁止在 op 内散写
    逐槽扫描。刷新钮费用等完整读数走 :func:`read_trainshop_panel` 的
    shop_cards refresh 槽。
    """
    for idx in range(1, 5):
        band_rect = _area_rect(ctx, f'{A_TS_NAME_PREFIX}{idx}',
                               PIONEER_SHOP_SCREEN_NAME)
        if band_rect is None:
            continue
        if is_refresh_anchor([r.data or ''
                              for r in _ocr(ctx, screen, band_rect,
                                            crop_first=True)]):
            return idx
    return None


def read_trainshop_slot_line(ctx: SrContext, screen: MatLike,
                             idx: int) -> tuple[str, int | None]:
    """单槽名行轻读 → ``(规范名, 标价 | None)``(零 SIFT;op 补位验证用的
    轻量前后对照源,完整读卡走 :func:`read_trainshop_panel`)。
    rect 缺失(建档漂移)→ ``('', None)``。"""
    band_rect = _area_rect(ctx, f'{A_TS_NAME_PREFIX}{idx}', PIONEER_SHOP_SCREEN_NAME)
    if band_rect is None:
        return '', None
    entries = [(r.data or '', r.center.x)
               for r in _ocr(ctx, screen, band_rect, crop_first=True)]
    return split_name_cost(entries)


def _slot_to_json(slot: TrainShopSlot) -> dict:
    """TrainShopSlot → JSON dict(仿金币商店 _shop_slots_to_json)。"""
    return {'kind': slot.kind,
            'card': asdict(slot.card) if slot.card is not None else None}
