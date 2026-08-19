# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 **备战屏**观测:备战截图 → ``GameState``(``read_game_state``)。

本模块只管**备战屏** reads(gold/hp/level/phase_round/board[+next_tier]/shop/bench_full)+ 组合入口
``read_game_state``。简报 reads 在 ``cw_briefing_obs``、结算 reads 在 ``cw_settlement_obs``、
共享 helper/常量在 ``cw_obs_core``;本模块 **re-export** 简报/结算的公开函数,故
``from cw_observation import read_affixes / parse_settlement_hp / ...`` 向后兼容(2026-08-06 拆分,)。

备战字段采集按 doc 06(``strategy/06_input_model.md``)逐簇推进(board tier 已接,余待采:
active_strategies/enemy_difficulty/level_up_cost/inventory 等;icon/身份类阻塞于 vision/SIFT 库)。

**区域单一真相源 = screen_info**(用户 2026-08-03):``assets/game_data/screen_info/currency_war_battle_prep.yml``
(screen「货币战争-备战」),经 ``cw_obs_core._area_rect`` 读 area 的 pc_rect —— 改区域改 yml 即可,不动代码。

设计原则(strategy/05_observation(签名+失败语义+sanity bounds)):
- 每字段用 ``_ocr(rect=...)`` 定区域读(**不塌缩重复文本** —— 地图版 get_ocr_result_map 按文本聚合,
  两张同阵营牌会撞键丢一张;list 版保留全部)。
- OCR 失败 / 越界(sanity bounds)→ 安全默认,不抛错(plan 对默认安全降级:
  gold 默认 0 → 不买;hp 默认 100 → 不触发保血)。越界读(gold 读成 500)比读不到更危险。

v1 OCR 可读性(2026-08-03,实机多样本 + 诊断脚本确认):
- **level**:``read_level`` OCR 优先 + ``_expected_level`` 兜底;telemetry level 跨样本合理(✓)。
- **hp**:⚠️ **plan-time 读不到(保血原本未武装),根因已确认 = shop 开启时右上角 HP 区空,非读取器坏**。
  ``BuyShopCards`` 在 shop 关闭帧读 hp → 覆盖 state.hp(见 shop.buy;回归 test_read_hp_shop_state)。
- **board**:count 解析曾脆(全屏 OCR 把 "2/3" 误读 "213");改用 ``_board_pairs`` 聚焦解析 X/Y,
  count=X + next_tier=Y(``read_board_next_tier``),根因(全屏密度)解决。
"""
from __future__ import annotations

import re

import cv2
from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.utils.log_utils import log

# re-export 简报 + 结算 reads(向后兼容:from cw_observation import read_affixes/parse_settlement_hp 等仍可用)
from sr_od.application.currency_war.cw_briefing_obs import (  # noqa: F401
    load_affix_effects_from_file,
    read_affix_effect,
    read_affixes,
    read_affixes_with_pos,
    read_bosses,
    save_affix_screenshot,
    write_affix_effects,
)
from sr_od.application.currency_war.cw_chars import get_char
from sr_od.application.currency_war.cw_factions import FACTIONS
from sr_od.application.currency_war.cw_identity_obs import (
    ensure_portrait_templates,
    identify_character,
    resolve_char_name,
)
from sr_od.application.currency_war.cw_obs_core import (
    A_BOARD,
    A_GOLD,
    A_PHASE,
    A_SHOP_CARD_PREFIX,
    GOLD_MAX,
    GOLD_MIN,
    HP_MAX,
    HP_MIN,
    LEVEL_MAX,
    LEVEL_MIN,
    SHOP_SCREEN_NAME,
    _area_rect,
    _first_int,
    _ocr,
    area_center,  # noqa: F401 (re-export:importer 经 cw_observation.area_center 用)
)
from sr_od.application.currency_war.cw_observe import obs_conflict
from sr_od.application.currency_war.cw_settlement_obs import (  # noqa: F401
    parse_settlement_hp,
    read_round_outcome,
)
from sr_od.application.currency_war.cw_state import (
    XP_TO_NEXT_LEVEL,
    GameState,
    ShopCard,
    rebuild_deployed_from_board,
)
from sr_od.context.sr_context import SrContext


def _expected_level(plane: int, round_num: int) -> int:
    """阶段期望等级(**单一源 cw_economy._expected_level**;参数序 (plane, round_num) 转接)。

    level 不可 OCR 时作兜底:≈ 真实等级,使 economy level_val≈0(不误判欠等级 → 不滥升)
    + max_units≈ 真实(模拟 deploy 容量合理)。
    ⚠️ r90 审计必修:此副本曾与 economy 侧漂移(改刻度忘了这里)——统一 import 单一源,
    本函数只做参数序转接(消费方按 (plane, round) 调)。
    """
    from sr_od.application.currency_war.cw_economy import (
        _expected_level as _econ_expected_level,
    )
    return _econ_expected_level(round_num, plane)


# ===== 备战单字段读取(失败 → 安全默认)=====
def read_gold(ctx: SrContext, screen: MatLike) -> int:
    """当前金币(底部右侧数字)。读不到 / 越界 → 0(plan 不买,安全保守)。

    gold 数字小 + stylized,paddle native det 几乎总漏(读 0/空,实锤见 process_log)→
    裁 area 后 **放大 3x** 再 OCR(破小目标 det 天花板)。area 已收紧到只含 gold 数字
    (排除隔壁 G0/0 货币;2026-08-07 实测 [1610,890,1690,945] 放大后稳读 3/2)。
    """
    rect = _area_rect(ctx, A_GOLD)
    if rect is None:
        return 0
    crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
    if crop.size == 0:
        return 0
    up = cv2.resize(crop, (crop.shape[1] * 3, crop.shape[0] * 3), interpolation=cv2.INTER_CUBIC)
    v = _first_int([r.data for r in ctx.ocr_service.get_ocr_result_list(image=up)])
    if v is None or not (GOLD_MIN <= v <= GOLD_MAX):
        return 0
    return v


def read_refresh_probs(ctx: SrContext, screen: MatLike) -> dict[int, float] | None:
    """商店开态的概率条 → {费用档 1-5: 概率}(r77 轮岗接线;读不到 → None 退基线)。

    **为什么读屏**(用户 2026-08-19 点题「轮岗」):投资环境轮岗每备战阶段随机翻倍
    一个费用档(基线 lv6 30/40/25/5 → 1费翻倍变 60/22/15/3,实测吻合)——概率条
    直接印在商店面板上,OCR 即真值,无需建模哪个档被随机翻倍、也覆盖其他概率类
    环境。消费方:plan._sample_cost(D 牌蒙特卡洛)/ refresh 价值评估。
    """
    from sr_od.application.currency_war.cw_obs_core import SHOP_SCREEN_NAME, _area_rect
    rect = _area_rect(ctx, '按钮-刷新概率表', SHOP_SCREEN_NAME)   # 概率条在开商店子态屏
    if rect is None:
        return None
    crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
    if crop.size == 0:
        return None
    from sr_od.application.currency_war.cw_shop_odds import parse_prob_bar
    texts = [r.data for r in ctx.ocr_service.get_ocr_result_list(image=crop)]
    return parse_prob_bar(texts)


def read_hp_opt(ctx: SrContext, screen: MatLike) -> int | None:
    """read_hp 的保真版:读不到/越界 → None(默认值由调用方定)。

    遥测用(insights 2026-08-15「hp=100 默认值毒化遥测」):read_hp 的 100 默认是决策层
    安全设计(不触发保血),但遥测记录里「真 100」与「读不到兜底 100」不可区分 → 复盘误判
    (M19 曾误读「P1 零损」)。遥测/复盘侧用本函数区分。
    """
    v = _first_int([r.data for r in _ocr(ctx, screen, _area_rect(ctx, '文本-剩余血量'))])
    if v is None or not (HP_MIN <= v <= HP_MAX):
        return None
    return v


def read_hp(ctx: SrContext, screen: MatLike) -> int:
    """小队剩余血量(备战屏右上角 ``文本-剩余血量``)。读不到/越界 → 100(健康先验)。

    **plan-time 读不到,根因已多样本确认(2026-08-03):HP 只在 shop 关闭态显示右上角;shop 开启态该区空。**
    5 张 shop-关闭态全读到真 HP(80/80/80/29/84)、shop-开启态该区空 → 默认 100。本函数正确 ——
    ``BuyShopCards`` 在 shop 关闭帧读 hp 覆盖 state.hp(见 shop.buy)。回归:``test_read_hp_shop_state``。
    """
    v = read_hp_opt(ctx, screen)
    return 100 if v is None else v


def read_level(ctx: SrContext, screen: MatLike, plane: int, round_num: int) -> int:
    """玩家等级(= 可上阵数上限,封顶 10)。

    OCR ``文本-等级``(screen_info 区域已排除下方 XP "0/6" 与「购买经验金币」,
    仅含等级数字 + "LV." 标签)→ 取首个数字。读不到 → ``_expected_level`` 启发式兜底
    (≈ 真实等级,使 economy level_val≈0 不误判欠等级)。

    注:部分截图 OCR 漏读等级数字(如测试图 currency_war_shop.png 只出 "LV."),此时走兜底。
    """
    v = _first_int([r.data for r in _ocr(ctx, screen, _area_rect(ctx, '文本-等级'))])
    if v is not None and (LEVEL_MIN <= v <= LEVEL_MAX):
        return v
    return _expected_level(plane, round_num)


# 备战顶部节点类型标签 → 关键词。doc 13 §13.2A node_type。⚠️ 仅 boss(首领)实机核实;
# 其它节点类型(补给/遭遇/巨星/投资/战斗/精英/奖励)的标签措辞待多子态实机核实补全。
_NODE_TYPE_KEYWORDS: dict[str, str] = {
    '首领': 'boss', '补给': 'supply', '遭遇': 'encounter', '巨星': 'megastar',
    '战斗': 'battle', '精英': 'elite', '奖励': 'reward', '投资': 'invest',
}


def _node_type_label(ctx: SrContext, screen: MatLike) -> tuple[str | None, int | None]:
    """节点行标签带 OCR → ``(node_type, 标签中心 x 全屏)``;无已知关键词 → (None, None)。

    r80(审计 P0-1):标签**不止出现在当前节点下方** —— 2-7 备战实证「首领」出现在
    **即将到来的 boss 节点**下方(x≈1341,当前节点在行中部 x≈900)→ 旧 read_node_type
    只查关键词不看位置,把非 boss 轮误判 boss(boss_spend 提前花光资源,HP17 惨胜实证)。
    本函数带位置返回,调用方做锚定校验。
    """
    results = _ocr(ctx, screen, Rect(500, 65, 1700, 115))
    for r in results:
        for kw, nt in _NODE_TYPE_KEYWORDS.items():
            if kw in r.data:
                return nt, int(r.x + r.w / 2)
    return None, None


#: 标签 x 与当前槽 cx 容差(节点槽距 ~90px + 标签中心偏差;超过 = 标签属于别的节点)
_NODE_LABEL_X_TOL: int = 110
#: boss 语义门:首领 = 位面**最后**节点(基础 9 轮,boss=第 9;r80 审计 a 收紧:人身意外险
#: 在首领前+补给 → boss ≥10)→ round < 9 时读到的「首领」必是**即将到来**的 boss 节点
#: 标签(2-7 实证),不是当前节点。取 9(非 10)= 无环境加节点时的下限,宁紧勿松。
_BOSS_MIN_ROUND: int = 9


def gate_node_type(node_type: str | None, round_num: int | None,
                   label_x: int | None = None, current_cx: int | None = None) -> str | None:
    """无锚定 OCR 读到的 node_type 语义门(r80 审计 P0;纯函数可测)。

    两道门,任一不过 → None(不覆盖):
    1. **boss 轮次门**:node_type=='boss' 且 round_num < ``_BOSS_MIN_ROUND`` → 即将到来
       的 boss 节点标签(2-7 实证),非当前节点 → None。
    2. **标签位置门**(给了锚点时):|label_x - current_cx| > ``_NODE_LABEL_X_TOL`` →
       标签在别的节点下方(张冠李戴)→ None。
    """
    if node_type is None:
        return None
    if node_type == 'boss' and (round_num or 0) < _BOSS_MIN_ROUND:
        return None
    if label_x is not None and current_cx is not None \
            and abs(label_x - current_cx) > _NODE_LABEL_X_TOL:
        return None
    return node_type


def read_node_type(ctx: SrContext, screen: MatLike) -> str | None:
    """备战顶部「当前节点类型」标签 → node_type(boss/补给/遭遇/...;doc 13 §13.2A)。

    ⚠️ **无锚定的宽松读**(r80):「首领」等标签也会出现在**即将到来的节点**下方
    (2-7 实证)→ 本函数返回值**不可直接当当前节点类型**;消费方必须过
    ``gate_node_type`` 语义门(read_game_state boss 轮次门 / read_node_sequence
    标签位置门)。仅 boss(首领)实机核实;其它节点类型标签措辞待多子态实机核实。
    """
    t, _lx = _node_type_label(ctx, screen)
    return t


# 节点类型模板 Hu 矩缓存(module-level;``read_node_sequence`` 首调从 assets 加载)。
_NODE_TYPE_TEMPLATES: dict | None = None
# clean 备战帧的最少圆数门:基础行 8 槽 + invest-env 增(人身意外险+1 → 9);shop 开 / 过渡 / overlay
# 遮挡时 HoughCircles 只检出 1-3 个。n < 此 → 非 clean 帧(reader 数据不可信:坏帧 Hu 畸变 → 假未识别),
# 返 None 跳过等下轮重读。容许 2 漏检(8→6),排除所有观测到的坏帧(n≤3)。
_MIN_CLEAN_CIRCLES: int = 6


def read_node_sequence(ctx: SrContext, screen: MatLike) -> list | None:
    """备战顶部「节点行」→ 节点槽列表(``cw_node_reader.NodeSlot``);每次备战调(invest-env 增/改节点 → 重识别)。

    组装纯 CV 核心(``cw_node_reader.classify_node_row``):HoughCircles 动态定圆 + HSV 三态(已过/当前/未来)+
    未来 Hu 矩匹配 4 模板;**当前节点**类型用 OCR 标签(``read_node_type``,只有当前节点有文字标签)覆盖。
    **首领** = 位面最后节点(按位置判,不在节点行模板内;调用方按 round 推断)。未来圆 Hu 距离 >
    ``cw_node_reader.HU_DIST_UNRECOGNIZED`` → 未识别(扑满/新类型,调用方可触发采集)。

    ⚠️ screen 为框架 RGB;S/V/Hu 对 RGB/BGR 无关 → 直传 classify。
    返回 None:模板未加载 / 非 clean 备战帧(圆数 < ``_MIN_CLEAN_CIRCLES``:shop 开 / 过渡 / overlay
    遮挡 → 坏帧 Hu 畸变不可信)。调用方遇 None 跳过,等下个 clean 备战帧重读。详 ``cw_node_reader`` docstring。
    """
    global _NODE_TYPE_TEMPLATES
    from pathlib import Path

    from sr_od.application.currency_war.cw_node_reader import (
        NODE_ROW_RECT,
        classify_node_row,
        load_node_type_templates,
    )
    if _NODE_TYPE_TEMPLATES is None:
        _d = Path(__file__).resolve().parents[4] / 'assets' / 'game_data' / 'cw_node_types'
        _NODE_TYPE_TEMPLATES = load_node_type_templates(_d) or {}
    if not _NODE_TYPE_TEMPLATES:
        return None
    _x0, _y0, _x1, _y1 = NODE_ROW_RECT
    _slots = classify_node_row(screen[_y0:_y1, _x0:_x1], _NODE_TYPE_TEMPLATES)
    if len(_slots) < _MIN_CLEAN_CIRCLES:
        return None  # 非 clean 备战帧(shop 开 / 过渡 / overlay 遮挡 → 圆数少);数据不可信,跳过等下轮重读
    # r80(审计 P0-1):OCR 标签**带位置**锚定校验 —— 「首领」等标签会出现在即将到来的
    # 节点下方(2-7 实证 x1341 vs 当前槽 cx≈900)→ 标签 x 与当前槽 cx 对拍,错位不覆盖。
    _t, _lx = _node_type_label(ctx, screen)
    if _t:
        _cur_slot = next((s for s in _slots if s.state == 'current'), None)
        if _cur_slot is None:
            pass   # 无当前锚(罕见)→ 不覆盖
        elif gate_node_type(_t, None, label_x=_lx,
                            current_cx=_cur_slot.cx + _x0) is None:
            from one_dragon.utils.log_utils import log as _log
            _log.info('[cw!][nodeseq] 标签x错位不覆盖:type=%s 标签x=%d vs 当前槽cx=%d'
                      '(标签属即将到来的节点,如 boss 前夕「首领」)', _t, _lx or -1,
                      _cur_slot.cx + _x0)
        else:
            _cur_slot.node_type = _t
    return _slots


def read_xp_progress(ctx: SrContext, screen: MatLike) -> tuple[int, int] | None:
    """购买经验进度 ``(cur_xp, xp_to_next_level)``,购买经验按钮下方 "X/Y"(备战字段采集)。

    OCR 购买经验(y848)下方 ~y935 的 "X/Y"(如 "4/20")→ (4, 20)。读不到 / 越界 → None。
    level 升级时机决策用(cur 接近 next → 即将升级,影响 level_plan/买经验优先级)。

    OCR ``文本-升级所需经验`` 的 "X/Y"(如 "4/20")→ (4, 20)。读不到 / 越界 → None。
    """
    blob = ''.join(r.data for r in _ocr(ctx, screen, _area_rect(ctx, '文本-升级所需经验')))
    m = re.search(r'(\d+)\s*/\s*(\d+)', blob)
    if m:
        cur, nxt = int(m.group(1)), int(m.group(2))
        if 0 <= cur <= nxt <= 100:      # sanity:cur≤next,XP 上限合理(封顶 10 级,每级 XP 个位~十几)
            return cur, nxt
    return None


def read_enemy_difficulty(ctx: SrContext, screen: MatLike) -> int | None:
    """当前敌人难度(左上角 ``文本-难度``;boss 血量 ≈ base×1.052^难度,doc 13 §13.7)。

    OCR ``文本-难度`` → int。⚠️ 难度数字 **stylized,OCR 常空** → None(可靠读需 vision / digit-CV,
    后续;现 area + scaffold 就位,OCR 能读到即生效)。读不到 / 越界 → None。
    """
    v = _first_int([r.data for r in _ocr(ctx, screen, _area_rect(ctx, '文本-难度'))])
    if v is not None and 0 <= v <= 300:
        return v
    return None


def read_level_up_cost(ctx: SrContext, screen: MatLike) -> int | None:
    """买一次经验的花费(``文本-购买经验金币数``;替代 ``LEVEL_UP_COST_TABLE`` 估,doc 13 §13.2C)。

    OCR ``文本-购买经验金币数`` → int。读不到(shop 态不显 / stylized)→ None(plan 用 ``LEVEL_UP_COST_TABLE`` 兜底)。
    """
    v = _first_int([r.data for r in _ocr(ctx, screen, _area_rect(ctx, '文本-购买经验金币数'))])
    if v is not None and 0 <= v <= 20:
        return v
    return None


def read_shop_refresh_cost(ctx: SrContext, screen: MatLike) -> int:
    """刷新商店一次的花费(``文本-刷新金币数``;默认 2,投资策略可减免;未读到保 2)。"""
    v = _first_int([r.data for r in _ocr(ctx, screen, _area_rect(ctx, '文本-刷新金币数'))])
    if v is not None and 0 <= v <= 10:
        return v
    return 2


def read_streak(ctx: SrContext, screen: MatLike) -> int | None:
    """连胜/连败数(``文本-连胜数``;**正负语义待核**(正=连胜?),现读 magnitude;None=未读到)。"""
    v = _first_int([r.data for r in _ocr(ctx, screen, _area_rect(ctx, '文本-连胜数'))])
    if v is not None and 0 <= v <= 20:      # magnitude(符号待核);连胜/连败一般 ≤20
        return v
    return None


def parse_damage_value(s: str) -> int | None:
    """伤害值文本 → int('126.5万'→1265000 / '1439282'→1439282 / '89.8亿'→...;无数字/异常 → None)。

    战斗实时屏右侧「伤害」列角色明细 parse(总伤害 = 各角色求和,**无单独字段**;2026-08-12 视觉大模型确认)。
    """
    s = (s or '').strip()
    if not s:
        return None
    mult = 1
    if s.endswith('万'):
        mult = 10_000
        s = s[:-1]
    elif s.endswith('亿'):
        mult = 100_000_000
        s = s[:-1]
    try:
        return int(round(float(s) * mult))
    except ValueError:
        return None


def read_total_damage(ctx: SrContext, screen: MatLike, rect: tuple[int, int, int, int]) -> int | None:
    """战斗实时屏右侧「伤害」列各角色明细 → 求和(总伤害)。

    ⚠️ **fragile 时机**:战斗中读(敌方/我方行动中,伤害实时增)→ 读的是当时累计,非最终。诊断用
    (stage7 输出诊断;hp_trend 已隐含输出主路径 ``is_run_dead``)。**战斗实时屏未建档**(``screens=[]``,
    ``rect`` 调用方传固定坐标临时;TODO 战斗屏建档后改 area)。3.5.4 reader 就位,接线(战斗时机 + 建档)待 stage7。
    无单独总伤害字段 → 角色明细求和(2026-08-12 视觉大模型确认)。
    """
    x1, y1, x2, y2 = rect
    crop = screen[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    ocr = ctx.ocr_service.get_ocr_result_list(image=crop)
    vals = [v for v in (parse_damage_value(r.data) for r in ocr) if v is not None]
    return sum(vals) if vals else None


# 难度确认屏 reader(开局读本局职级;非备战屏,放本模块集中 OCR readers)
_DIFFICULTY_CONFIRM_SCREEN: str = '货币战争-难度确认'


def parse_selected_difficulty(texts: list[str]) -> str:
    """难度确认屏 OCR 文字 → 本局职级(``A\\d+(-\\d+)?``,如 A8 / A5 / A8-1..A8-50)。

    正则 + 全匹配过滤非职级文字(财富造物主 / 当前职级难度效果 等)。纯函数可单测。
    无匹配 → ""(``effective_hp_threshold`` 回退默认阈值,行为不变;cw_state:253)。
    """
    for t in texts:
        m = re.fullmatch(r'A(\d+)(?:-(\d+))?', t.strip())
        if m:
            return t.strip()
    return ''


def read_selected_difficulty(ctx: SrContext, screen: MatLike) -> str:
    """难度确认屏 → 本局职级(``标识-当前难度职级`` area OCR → parse)。

    AX label 在画面左上(x~87,y~305,紧邻「财富造物主」)。A8 高难 → ``effective_hp_threshold``
    保血阈值调高(D-32;cw_state.DIFFICULTY_HP_TABLE 代码常量,ADR-0204)。读不到 → ""(回退默认)。
    接线已通(3.5.1,d841d1a1):StartCurrencyWarMatch 难度确认段调本函数 → ctx.cw_selected_difficulty
    → battle_loop copy session → default_strategy 填 state → effective_hp_threshold D-32 激活。
    """
    rect = _area_rect(ctx, '标识-当前难度职级', _DIFFICULTY_CONFIRM_SCREEN)
    texts = [r.data for r in _ocr(ctx, screen, rect)]
    return parse_selected_difficulty(texts)


# last-known-good (plane, round):plane 单调递增、round 同位面内递增;过渡帧 OCR 失败时
# 返回上次成功值,避免 fallback (1,1) 误导 level_plan/支出 gate(2026-08-04 实跑发现:
# plane=4 lv=9 后过渡帧读成 plane=1 lv=4 兜底)。跨局由 reset_phase_round_cache 清空。
_last_phase_round: tuple[int, int] | None = None


def reset_phase_round_cache() -> None:
    """新对局开始时清空 last-known-good(防跨局复用上局 plane/round)。"""
    global _last_phase_round
    _last_phase_round = None


def read_phase_round(ctx: SrContext, screen: MatLike) -> tuple[int, int]:
    """位面 + 轮次(顶栏「X-Y」= 位面-轮次,如 "1-3" = 位面1 第3轮)。

    :return: (plane, round_num)。读不到 → 返回上次成功值(过渡帧兜底);无历史 → (1, 1)。

    单调守卫(审计 P0,2026-08-16,M38 同款毒化面):plane 局内单调递增、round 同位面内递增,
    读到**倒退值**(如 plane3 → plane2)= OCR 假阳 → 保旧 + obs_conflict 留证(毒化面:
    level_plan/支出 gate/P2P3 概率表/_expected_level 兜底全歪)。digits fallback 抓首个数字
    对噪声极敏感,是倒退误读的主要来源 —— fallback 路径读出的倒退一律拒。
    """
    global _last_phase_round
    blob = ''.join(r.data for r in _ocr(ctx, screen, _area_rect(ctx, A_PHASE)))
    m = re.search(r'(\d)\s*-\s*(\d)', blob)          # "1-3"
    if m:
        new = (int(m.group(1)), int(m.group(2)))
    else:
        plane_m = re.search(r'第\s*(\d)\s*位面', blob)
        new = (int(plane_m.group(1)), int(plane_m.group(1))) if plane_m else None
    if new is not None:
        # ⚠️ 值域守卫(2026-08-17 M70 假 win 根因):plane 只有 1-3,读出 8(恢复对局时顶栏被
        # overlay 遮,OCR 抓到 A8 难度/Lv.8 的"8")→ last_state.plane=8 → 局终判定 8>=3 →
        # 假 win 假通关。值域外 = OCR 假阳,当 miss 处理(走 last-known/兜底),不进缓存。
        if not (1 <= new[0] <= 3 and 1 <= new[1] <= 9):
            obs_conflict('phase_round', _last_phase_round, new, screen,
                         verdict='拒-值域外(plane∈1-3/round≤9,OCR抓错源如A8难度)', source='ocr_range')
            new = None
    if new is not None:
        if _last_phase_round is not None and (new[0] < _last_phase_round[0]
                                              or (new[0] == _last_phase_round[0] and new[1] < _last_phase_round[1])):
            obs_conflict('phase_round', _last_phase_round, new, screen,
                         verdict='保旧-单调守卫(plane/round 倒退=OCR假阳)', source='ocr')
            return _last_phase_round
        _last_phase_round = new
        return _last_phase_round
    digits = re.findall(r'\d', blob)
    if digits:
        d = int(digits[0])
        # fallback 单数字:首数字同时当 plane/round 本就是强假设(仅开局 (1,1) 合法)——
        # ⚠️ 值域守卫(M70 根因同上):"8" 来自 A8/Lv.8 泄漏,不是位面。只接受 1(开局 1-1)。
        if d == 1:
            new = (1, 1)
        else:
            obs_conflict('phase_round', _last_phase_round, (d, d), screen,
                         verdict='拒-fallback数字非1(单数字仅开局1-1合法,A8/Lv泄漏)', source='ocr_digits_fallback')
            new = None
        if new is not None:
            if _last_phase_round is not None and (new[0] < _last_phase_round[0]
                                                  or (new[0] == _last_phase_round[0] and new[1] < _last_phase_round[1])):
                obs_conflict('phase_round', _last_phase_round, new, screen,
                             verdict='保旧-单调守卫(fallback数字倒退拒)', source='ocr_digits_fallback')
                return _last_phase_round
            _last_phase_round = new
            return _last_phase_round
    # OCR 失败(过渡帧)→ 返回上次成功值,避免 (1,1) 误导 level_plan
    if _last_phase_round is not None:
        return _last_phase_round
    return 1, 1


def _read_deploy_paddle(ctx: SrContext, screen: MatLike) -> tuple[int | None, int | None]:
    """舞台上方中央「X/Y」指示 → (X 已部署角色数, Y deploy cap);读不到 → (None, None)。

    **原生 OCR,不放大**(D-53):字体够大,放大反致 paddle det 把 "X/Y" 拆成两框(读成 "5")。
    关键是 **screen_info ``区域-部署数`` pc_rect 给足 padding** —— paddle det 需文字周围有背景才把
    "X/Y" 当**一个整体 box** 出;pc_rect 太紧(旧 [790,185,1060,240] 终点 y240 切在文字 y244 之上 +
    无 padding)→ det 拆 / 丢斜杠(读成 "15/"/"16")→ 全 None。padding 给足(D-53 改 [820,210,1060,280])
    → 原生即稳读 "5/5"(5 fixture 全中)。

    **整串识别 + 提取**(用户 D-53 指点):OCR 整个 region → join 成一串 → 正则提取 X/Y,不拆开识。
    **斜杠特殊处理**(用户 D-53):``/`` 常被识成 ``1``/``l``/``I``/``i``/``|`` → 把「数字间的非数字单字符」
    normalize 成 ``/`` 再正则(``re.sub(r'(?<=\\d)\\D(?=\\d)', '/', blob)``);slash→``1`` 致 X 虚高由 X>Y guard 兜。

    **cap = level**(D-53 实测核正):无钻石/宝钻/诅咒时 deploy cap = 团队等级(5 fixture 跨 lv3/4/5/7 核:
    5/5@lv5、4/4@lv4、3/4@lv4、0/3@lv3、6/7@lv7,Y 恒=level)。钻石/财富宝钻 +1 团队槽 → cap=level+1
    (>level 即钻石加成,recognizer 据此告警 D-50)。⚠️ 旧注「cap≠level(lv4-5 3/3、lv6 5/5)」自主推进期错数据,已废。

    X(deployed)sanity:deployed 不可能 > cap;X>cap 时(如 a8_start "10/3",真值 0/3,slash 噪声致 X 虚高)
    X 不可信 → 返 (None, Y)(deployed 未知走 fallback,但 cap Y 仍准)。
    """
    rect = _area_rect(ctx, '区域-部署数')
    if rect is None:
        return None, None
    crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
    if crop.size == 0:
        return None, None
    blob = ''.join(r.data for r in ctx.ocr_service.get_ocr_result_list(image=crop))
    norm = re.sub(r'(?<=\d)\D(?=\d)', '/', blob)      # 数字间非数字单字符 → /(slash 误识兜底,用户 D-53)
    m = re.search(r'(\d+)\s*/\s*(\d+)', norm)
    if not m:
        return None, None
    x, y = int(m.group(1)), int(m.group(2))
    if x > y:                                   # deployed > cap 不可能 → X 是 OCR 噪声(slash→1 等),Y 仍可信
        return None, y
    return x, y


def read_deployed_count(ctx: SrContext, screen: MatLike) -> int | None:
    """舞台上方中央「X/Y」指示 → X(已部署角色数);读不到 → None。

    DeployBench 用它定位**空位**:d(cap_remaining)+ e(offset)依赖它;读不到 → fallback
    → 部分 churn。实现见 ``_read_deploy_paddle``(同时给 cap Y,见 ``read_deploy_cap``)。
    """
    return _read_deploy_paddle(ctx, screen)[0]


def read_deploy_cap(ctx: SrContext, screen: MatLike) -> int | None:
    """舞台上方中央「X/Y」指示 → Y(deploy cap 真值);读不到 → None(调用方退 level 估)。

    实机 **cap=level**(D-53 实测核正:5 fixture 跨 lv3/4/5/7,Y 恒=level;无钻石/宝钻/诅咒时)。
    钻石/财富宝钻加成时 cap=level+1(>level 即钻石加成,recognizer 据此告警 D-50,后排可能>6)。
    DeployBench 应用本 Y 非 level 估 cap_remaining。读不到 → 退 level 估(fallback;cap=level 故 fallback 仍准)。
    旧注「cap≠level(lv4-5 3/3、lv6 5/5)」自主推进期错数据,已废。reader 实现细节/根因见 ``_read_deploy_paddle``。
    """
    return _read_deploy_paddle(ctx, screen)[1]


def _board_pairs(ctx: SrContext, screen: MatLike, max_count: int = 9) -> dict[str, tuple[int, int]]:
    """OCR 左面板 → {阵营: (count, next_tier)},从 "X/Y" 解析(X=在场人数,Y=下个 tier 阈值)。

    聚焦裁切 OCR 才稳读 "X/Y"(全屏把 "2/3" 误读 "213"→ 旧 read_board 显脆,实为全屏密度问题;
    区域裁切可读对)。next_tier 未解析到 → 记 0(未知,read_board_next_tier 滤掉)。
    """
    results = _ocr(ctx, screen, _area_rect(ctx, A_BOARD))
    results.sort(key=lambda r: r.center.y)
    pairs: dict[str, tuple[int, int]] = {}
    for i, r in enumerate(results):
        faction = next((f for f in FACTIONS if f in (r.data or '')), None)
        if faction is None or faction in pairs:
            continue
        xy: tuple[int, int] | None = None
        for r2 in results[i + 1:]:
            dy = r2.center.y - r.center.y
            if dy > 45:
                break
            if dy <= 0:
                continue
            # count 显示为 "X/Y"(X=在场人数,Y=下个 tier 阈值,如 仙舟"1/3");取 X=count + Y=next_tier。
            # 裸数字(无斜杠)多是 tier 链残留(如燃血 "2/4/6/8" → OCR "8")或邻行资源数,不当 count → skip。
            m_xy = re.search(r'(\d+)\s*/\s*(\d+)', r2.data or '')
            if m_xy:
                xy = (int(m_xy.group(1)), int(m_xy.group(2)))
                break
        if xy is not None:
            cnt, nt = xy
            # sanity:count 1-max_count(默认 9;read_game_state 传 level —— faction count ≤ deployed ≤ level,
            # count>level 必是 OCR 误读,如 狼狩:7@lv4);next_tier 1-12。越界 → 兜底 count=1。
            cnt = cnt if 1 <= cnt <= max(max_count, 1) else 1
            nt = nt if 1 <= nt <= 12 else 0
            pairs[faction] = (cnt, nt)
        else:
            # 无 "X/Y"(动画期只显 tier 链等)→ count 默认 1(至少 1 人在场才显示该阵营),无 next_tier。
            pairs[faction] = (1, 0)
    return pairs


def read_board(ctx: SrContext, screen: MatLike) -> dict[str, int]:
    """OCR 左面板 → {阵营名: 在场人数}(= ``_board_pairs`` 的 X;向后兼容)。

    每个激活阵营一行:阵营名 + 其下的 "X/Y"(X=在场人数,Y=下个 tier 阈值)。详见 ``_board_pairs``。
    """
    return {f: c for f, (c, _nt) in _board_pairs(ctx, screen).items()}


def board_from_tracked(tracked: list) -> dict[str, int] | None:
    """从 tracked_deployed(身份可靠时)**计算** board 阵营计数(用户 2026-08-16 定:以算为准)。

    OCR 左面板的坑:激活阵营多时**一页显示不全要滚动** → OCR 只读可视区,滚出屏的静默漏
    (board 是 form_progress/pivot/economy 的地基,漏阵营 = 半成型误判)。角色注册表
    (``cw_chars.CHARACTERS``)已有全量阵营数据 → 每个已上场已知身份角色贡献其全部阵营,
    计数天然是全集,不受滚动/遮挡/OCR 误读影响。

    Returns:
        {阵营: 在场人数};**tracked 空 或 含未知身份(char_id 空/'?'/不在注册表)→ None**
        (混合态不切,OCR 兜底——未知角色的阵营贡献算不出,半算比漏算更毒;观察冲突留证会暴露
        混合频率)。**无阵营已知角色不 bail**(2026-08-17):白厄「救世主」复制效果不计人数
        (官方 trait 3005)→ 跳过零贡献即精确;布洛妮娅(factions 空flows 燃血)正常贡献 flows;
        独立羁绊行计入(与左面板显示同口径)。
    """
    if not tracked:
        return None
    counts: dict[str, int] = {}
    for bc in tracked:
        cid = getattr(bc, 'char_id', '') or ''
        if not cid or cid == '?':
            return None
        # 开拓者形态归一(用户 2026-08-16):前台=记忆/后台=欢愉,拖排即切换;羁绊按「当前排」
        # 的形态计(欢愉形态被拖上前排 → 欢愉羁绊消失)。position_pref 即当前排(simulate/
        # mutate DeployMove 写 to_row;identify_slots 上阵排写 row)。
        from sr_od.application.currency_war.cw_chars import (
            is_trailblazer,
            trailblazer_form,
        )
        if is_trailblazer(cid):
            cid = trailblazer_form(cid, getattr(bc, 'position_pref', '') or 'back')
        ch = get_char(cid)
        if ch is None:
            return None
        # 独立羁绊(救世主/领航员/挚爱之人…)左面板显示为一行(14:52 live OCR 实证含「救世主」)
        # → 计入保持与面板同口径;否则 computed_vs_ocr 对拍每帧误报「OCR有computed无」留证噪声。
        # comp 层消费只查 comp.factions,不受该键影响。
        if ch.independent:
            counts[ch.independent] = counts.get(ch.independent, 0) + 1
        # 羁绊 = 阵营类(factions)+ 流派类(flows:能量/欢愉/击破…)都进左面板计数(OCR board
        # 同口径 —— 只数 factions 会系统性漏流派羁绊;开拓者「欢愉」正是 flows,实测暴露)。
        for f in (*ch.factions, *ch.flows):
            counts[f] = counts.get(f, 0) + 1
        if not (ch.factions or ch.flows or ch.independent):
            return None  # 三者皆空 = 注册表数据异常,保守退 OCR
        # 无阵营但有独立羁绊(白厄「救世主」)或 factions 空 flows 非空(布洛妮娅 燃血):身份已知
        # 不 bail,上方已计入各自贡献。白厄复制效果不计人数(官方 trait 3005)→ 零阵营贡献即精确
        # (2026-08-17 修:旧版 not ch.factions 即 None,白厄/布洛妮娅上场整链误退 OCR,
        # 恰丢掉计算路径的抗滚动优势)。
    return counts


def read_board_next_tier(ctx: SrContext, screen: MatLike) -> dict[str, int]:
    """OCR 左面板 → {阵营名: 下个 tier 阈值}(= ``_board_pairs`` 的 Y;doc 13 ``FactionState.next_tier``)。

    只含 Y 解析到的阵营(0/未显阈值的不进 dict)。聚焦裁切 OCR 才稳(见 ``_board_pairs``)。
    """
    return {f: nt for f, (_c, nt) in _board_pairs(ctx, screen).items() if nt > 0}


def read_shop_cards(ctx: SrContext, screen: MatLike) -> list[ShopCard]:
    """SIFT 商店 5 张牌肖像 → list[ShopCard](x + faction + name + cost)。

    每张牌:裁 screen_info ``商店牌-N``(**肖像区**,D-55 经 VLM 定位改自文字带)→ ``identify_character``
    SIFT 对 ``currency_war/portrait_plaza`` 官方立绘库 → ``resolve_char_name`` 规范名;faction/cost 从 roster 派生。
    未识别(低内点/歧义/不在 roster)→ name='' faction='?' cost=0(仍占位保 5 张,len 不变)。

    **D-55 由 OCR 改 SIFT**:OCR 牌名对开拓者(玩家自定义名,如 "Momojie")等读不到/匹配错;SIFT 看
    肖像更稳。⚠️ 模板目录名须用**规范名**「开拓者·记忆/欢愉」非玩家 ID(2026-08-15 修:旧目录 Momojie/
    → resolve_char_name 落 legacy 路径返 None = 「开拓者 roster 缺」根因;玩家 ID 随账号变,规范名不变);
    肖像更稳(实测 shop_open 5/5 内点 33-68,VLM 定位肖像区)。faction 由 OCR 牌标签 → roster factions[0]
    (SIFT 读不了文字标签;**board OCR 仍是阵营计数权威**)。**faction 语义(2026-08-17)**:
    ``'?'``=未知(name 空/不在注册表);``''``=已知无阵营(白厄「救世主」类)。立绘库经
    ``ensure_portrait_templates`` 按需加载
    (buy 在 deploy 前,BattlePrepCycle: buy→deploy,故不依赖 deploy 才加载的缓存)。
    """
    templates = ensure_portrait_templates(ctx)
    # 商店开态前置门(M37/M38 误停机根因,2026-08-16):read_shop_cards 无脑裁牌区 rect 做 SIFT,
    # 商店收起/未展开帧(牌区=节点进度条+功能按钮)上全 miss → 采集钩子把「非商店帧的空读」
    # 误判「真有未识别卡」→ flag → shop.py 停机(实测:存证截图 analyze_screen 命中备战屏非
    # 商店开态,VLM 客观描述证实 y70-260 无卡)。门:商店开态锚「按钮-收起」(text area,框架
    # find_area_in_screen OCR+LCS)不命中 → 返空列表(「没有牌」≠「未识别」,不写 flag)。
    _si = ctx.screen_loader.get_screen(SHOP_SCREEN_NAME)
    _collapse_area = next((a for a in _si.area_list if a.area_name == '按钮-收起'), None) if _si else None
    if _collapse_area is None:
        # r9 review:锚缺失时门被静默跳过(fail-open)→ M37/M38 误停机回归无告警(改名/删 area)。
        from one_dragon.utils import log_utils
        log_utils.log.warning('[cw!] read_shop_cards 商店开态锚「按钮-收起」缺失(fail-open)→ 检查 yml')
    if _collapse_area is not None:
        from one_dragon.base.screen.screen_utils import find_area_in_screen
        # ⚠️ r7 review P0-A:旧 `is not True` 恒真(FindAreaResultEnum.TRUE.value 是 int 1,
        # `1 is not True` 恒成立)→ 门无条件返空 → read_shop_cards 自 e7bbd711(08-16 11:49)
        # 起**全局恒空**(decisions 实证:此前 1031/1031 行 shop 非空,之后 234/234 shop=[]
        # 且 0 BuyCard)——M46 起所有「一张不买」的真根因。改枚举等值比较。
        if find_area_in_screen(ctx, screen, _collapse_area).value != 1:
            return []
    cards: list[ShopCard] = []
    for i in range(1, 6):
        rect = _area_rect(ctx, f'{A_SHOP_CARD_PREFIX}{i}', SHOP_SCREEN_NAME)
        if rect is None:
            continue
        crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
        # r13:空槽检测(六边形占位,SIFT inliers≈3 vs 真卡 30-120)——低等级商店后槽未解锁
        # 是常态,空槽不是「未识别卡」(c1888c7d 帧实证:牌4/5 空槽 inliers=3 触发假 unknown)。
        # r15 review:跳过不可静默(假空槽=买不到该卡且不可见)——55-75 灰带 [cw!] 留证
        # (实测真卡 min 67.4 vs 空槽 19.5,余量 11%;采到暗卡击穿即闭环降阈值)。
        _mean = float(crop.mean())
        if _mean < 60:
            if _mean >= 50:   # 灰带:可能是被特效/裁切偏移压暗的真卡
                from one_dragon.utils import log_utils
                log_utils.log.info(f'[cw!][read_shop_cards] 牌{i} 均值{_mean:.1f}(灰带 50-60,'
                              f'疑暗卡被误判空槽,采到即闭环降阈值)')
            continue
        avatar_id, _inliers = (identify_character(crop, templates)
                               if templates is not None else (None, 0))
        name = resolve_char_name(avatar_id) if avatar_id else ''
        ch = get_char(name) if name else None
        cards.append(ShopCard(
            x=(rect.x1 + rect.x2) // 2,
            # '?'=未知(名未识别/不在注册表);''=已知无阵营(白厄类;2026-08-17 与 shop/identity 同语义)
            faction=(ch.factions[0] if (ch is not None and ch.factions)
                     else ('' if ch is not None else '?')),
            name=name,
            cost=(ch.cost if ch is not None else 0),
            star=1,
        ))
    # ~~shop_unknown_card 采集钩子已删(2026-08-17 归因闭环)~~:38 张存档样本离线对拍全识别
    # (73-119 内点,plaza 库)——全部是刷新动画/settle 瞬时帧 miss,非真未知卡;阮·梅/白厄挂账
    # 同归因闭环(瞬时帧,非光照变体/库缺)。flag 写入无消费端(shop.py 停机判定走重读防抖,
    # L287-299,保留作真未知防护),纯积压源,按「采完即删」约定移除。
    return cards


def read_bench_full(ctx: SrContext, screen: MatLike) -> bool | None:
    """「备战席已满」警告(True=满,需破;None=未观察到)。"""
    for kw in ('备战席已满', '出售或提升等级'):
        if any(kw in (r.data or '')
               for r in _ocr(ctx, screen, Rect(600, 360, 1320, 540))):
            return True
    return None


# ===== 组合入口 =====
def _level_from_xp(xp_progress: tuple[int, int] | None) -> int | None:
    """XP 条分母反推当前等级(ADR-0129):"cur/need" 的 need = 当前级→下一级门槛,反查
    ``XP_TO_NEXT_LEVEL``。1-2 级门槛不在表(用户表从 LV.3 起)→ None(调用方不覆盖,安全)。"""
    if not xp_progress:
        return None
    _inv = {v: k for k, v in XP_TO_NEXT_LEVEL.items()}
    return _inv.get(xp_progress[1])


def _resolve_level(
    ocr_raw: int | None,
    heuristic: int,
    xp_level: int | None,
    last_level: int,
) -> tuple[int, list[tuple[str, int, int, str, str]], bool]:
    """等级三源解析(纯函数,2026-08-18 治本重构:live M-cw 乒乓根因)。

    输入:
    - ``ocr_raw``:「文本-等级」区直读(**无兜底**;None=失读);
    - ``heuristic``:``_expected_level`` 启发式(ocr_raw 失读时的兜底值);
    - ``xp_level``:XP 条分母反推(ADR-0129,独立源;None=失读);
    - ``last_level``:session 上次值(``last_level_obs``;0=新局无历史)。

    返回 ``(level, events, authoritative)``:events = [(kind, old, new, verdict, source)]
    (供调用方记 [cw!]/obs_conflict);authoritative = 本帧等级是否来自真实观测
    (OCR 或 XP 至少一源可读;False=纯启发式,**调用方不得写回 last_level_obs** —— 毒化防线)。

    解析序(信源主权从高到低):
    1. 基值 = ocr_raw(可读)否则 heuristic;
    2. XP 覆盖(ADR-0129「信 XP 分母」):xp_level 可读且 ≠ 基值 → 采 XP;
    3. 单调守卫:较 last 下降 → **XP 主权豁免**(live 2026-08-18 实证:OCR 失读→启发式 6
       被写进 last_level_obs 毒化,XP 反推 5 每帧被单调守卫打回 → level 乒乓 6↔5,
       策略全程跑假等级);XP 未确认的下降仍是 OCR 误读 → 保旧;
    4. 跳变守卫:较 last 跳 >+2 且 XP 未确认 → OCR 单源假阳 → 保旧(M38 语义)。
    """
    level = ocr_raw if ocr_raw is not None else heuristic
    events: list[tuple[str, int, int, str, str]] = []
    # XP 覆盖:真实双源分歧(OCR 可读)才留证;OCR 失读时的例行为「兜底让位 XP」
    # (ADR-0129 设计常态,逐帧记 [cw!] 是遥测噪声 —— live 10:47-10:48 每帧 2 冲突实证)。
    if xp_level is not None and xp_level != level and ocr_raw is not None:
        events.append(('xp_override', level, xp_level, '采新-XP分母反推', 'xp_denominator'))
    if xp_level is not None and xp_level != level:
        level = xp_level
    if last_level:
        _xp_sovereign = xp_level is not None and level == xp_level
        if level < last_level:
            if _xp_sovereign:
                # 上次值疑似被启发式/误读毒化,XP 独立源向下校正(乒乓根治)。
                events.append(('xp_down', last_level, level,
                               '采新-XP下行校正(上次值疑似毒化)', 'xp_denominator'))
            else:
                events.append(('mono', last_level, level,
                               '保旧-单调守卫(下降强可疑)', 'ocr'))
                level = last_level
        elif level > last_level + 2:
            if _xp_sovereign:
                events.append(('jump_ok', last_level, level,
                               '采新-XP确认真跳变放行', 'ocr+xp_denominator'))
            else:
                events.append(('jump', last_level, level,
                               '保旧-跳变守卫(单源跳变拒,XP未确认)', 'ocr'))
                level = last_level
    authoritative = ocr_raw is not None or xp_level is not None
    return level, events, authoritative


#: _resolve_level 事件 → 日志格式({o}=旧值,{n}=新值;消费方 read_game_state)
_LV_LOG_FMT: dict[str, str] = {
    'xp_override': '[cw!] level 修正:OCR 读 {o},XP 分母反推 {n}(以 XP 为准)',
    'xp_down': '[cw!] level XP下行校正:上次 {o}(疑似兜底毒化) → XP 反推 {n}(乒乓根治)',
    'mono': '[cw] level 单调守卫:OCR 读 {n} < 上次 {o}(误读)→ 用 {o}',
    'jump': '[cw!] level 跳变守卫:OCR 读 {n} > 上次 {o}+2(疑似 XP 数字混入) → 用 {o}(误读不锁死)',
    'jump_ok': '[cw] level 真跳变放行:{o} → {n}(XP 分母独立确认)',
}


def read_game_state(ctx: SrContext, screen: MatLike) -> GameState:
    """一战前备战屏(商店已开)→ GameState(喂 plan)。

    各字段 OCR 失败 → 安全默认(见各 reader)。level 不可 OCR → ``_expected_level`` 兜底;
    hp 不可 OCR → 默认 100。v1 不读 bench/deployed 身份(buy 决策靠 board+shop+gold;
    deploy 走 DeployBench)。
    """
    state = GameState()
    state.gold = read_gold(ctx, screen)
    _hp_opt = read_hp_opt(ctx, screen)
    state.hp = 100 if _hp_opt is None else _hp_opt
    state.hp_readable = _hp_opt is not None   # 遥测保真(insights hp=100 毒化)
    state.plane, state.round_num = read_phase_round(ctx, screen)
    # r80(审计 P0):boss 轮次语义门 —— 「首领」标签在 boss 前夕也会出现在即将到来的
    # boss 节点下方(2-7 实证),round<8 时必是张冠李戴 → 拒(boss=位面最后节点 ≥9 轮)
    state.node_type = gate_node_type(read_node_type(ctx, screen), state.round_num)
    # 等级三源解析(2026-08-18 治本重构):OCR 直读(无兜底)/XP 分母反推/启发式兜底
    # 经 ``_resolve_level`` 统一仲裁 —— 旧内联链在「OCR 失读 + XP 可读」态每帧乒乓
    # (XP 采新 5 → 单调守卫用毒化 last 6 打回,live 10:47-10:48 三连发实证),
    # 且把启发式兜底值写回 last_level_obs(毒源)。纯函数语义/事件/防线详见其 docstring。
    state.xp_progress = read_xp_progress(ctx, screen)
    _lv_raw = _first_int([r.data for r in _ocr(ctx, screen, _area_rect(ctx, '文本-等级'))])
    if _lv_raw is not None and not (LEVEL_MIN <= _lv_raw <= LEVEL_MAX):
        _lv_raw = None
    _xp_lv = _level_from_xp(state.xp_progress)
    _match = getattr(ctx, 'cw_match', None)
    _last_lv = 0
    if _match is not None and _match.session is not None:
        _last_lv = getattr(_match.session, 'last_level_obs', 0)
    state.level, _lv_events, _lv_authoritative = _resolve_level(
        _lv_raw, _expected_level(state.plane, state.round_num), _xp_lv, _last_lv)
    for _kind, _old, _new, _verdict, _src in _lv_events:
        _fmt = _LV_LOG_FMT.get(_kind)
        if _fmt is not None:
            _msg = _fmt.format(o=_old, n=_new)
            if _kind in ('xp_override', 'xp_down', 'jump'):
                log.warning(_msg)
            else:
                log.info(_msg)
        else:
            log.warning(f'[cw!] level {_kind}:{_old}->{_new}')
        obs_conflict('level', _old, _new, screen, verdict=_verdict, source=_src,
                     plane=state.plane, round_num=state.round_num)
    # 毒化防线(2026-08-18):纯启发式兜底值(OCR 与 XP 双失读)不写回 last_level_obs
    # —— live 实证:兜底 6 被写入后,XP 反推 5 被单调守卫打回(乒乓),且下一帧继续毒化。
    if _match is not None and _match.session is not None and _lv_authoritative:
        _match.session.last_level_obs = state.level
    # enemy_difficulty:优先 session.enemy_difficulty(简报「敌人难度N」读,3.5.2);fallback 备战 read(常 null)
    _ed = getattr(getattr(_match, 'session', None), 'enemy_difficulty', None) if _match is not None else None
    state.enemy_difficulty = _ed if _ed is not None else read_enemy_difficulty(ctx, screen)
    state.level_up_cost = read_level_up_cost(ctx, screen)
    state.shop_refresh_cost = read_shop_refresh_cost(ctx, screen)
    # streak:优先 session.last_streak(结算「连胜×N」带符号,方向可靠;fixture 核实 2026-08-11);
    # 无 session(离线/测试)→ read_streak 备战 magnitude fallback。
    # 双源留证(观察冲突审计 #8 P2,2026-08-17):结算真值(带符号)与备战 magnitude 独立可对拍
    # —— |结算|≠备战 且 非结算重置边缘(胜→连胜≥1/败→连败≤-1 或 0)→ 一方误读,留证统计毒化率
    # (read_streak magnitude OCR 间歇误读的量化数据,此前无通道)。
    _sess = getattr(getattr(ctx, 'cw_match', None), 'session', None)
    if _sess is not None:
        state.streak = _sess.last_streak
        _prep_streak = read_streak(ctx, screen)
        if (_prep_streak is not None and _sess.last_streak != 0
                and abs(_sess.last_streak) != _prep_streak):
            obs_conflict('streak', _sess.last_streak, _prep_streak, screen,
                         verdict='留证-双源不等(结算带符号 vs 备战magnitude,一方误读)',
                         source='settlement_vs_prep', plane=state.plane, round_num=state.round_num)
    else:
        state.streak = read_streak(ctx, screen) or 0
    # board 双源(用户 2026-08-16 定:羁绊多时左面板一页显示不全要滚动 → OCR 只读可视区,
    # 滚出屏的静默漏;游戏数据(角色注册表)已全量 → **tracked 有身份时以计算为准**,OCR 只做
    # 可见子集对拍留证):
    # - computed(tracked 全已知身份)= 全集(每人贡献其全部阵营),不受滚动/遮挡影响 → state.board;
    # - OCR 可见行 f 若在 computed 中两者应相等(不等 = tracked 漂移或 OCR 误读,留证);
    #   OCR 可见但 computed 无 = tracked 漏该阵营角色(强信号留证);computed 有而 OCR 不可见
    #   = 滚动截断(正常,不算错)。
    # - tracked 空/含未知 → None → OCR 兜底(现状;混合态半算比漏算更毒)。
    _match = getattr(ctx, 'cw_match', None)
    _tracked_dep = (_match.session.tracked_deployed
                    if (_match is not None and _match.session is not None) else None)
    _computed = board_from_tracked(_tracked_dep)
    _bp = _board_pairs(ctx, screen, state.level)
    _ocr_board = {f: c for f, (c, _nt) in _bp.items()}
    if _computed is not None:
        for _f, _ocr_c in _ocr_board.items():
            _calc_c = _computed.get(_f)
            if _calc_c is None:
                obs_conflict('board', {'ocr': _ocr_board, 'computed': _computed}, f'OCR有computed无:{_f}',
                             screen, verdict='留证-tracked漏阵营角色(OCR可见但计算无)',
                             source='computed_vs_ocr')
            elif _calc_c != _ocr_c:
                obs_conflict('board', {'ocr': _ocr_c, 'computed': _calc_c}, f'count不等:{_f}',
                             screen, verdict='采新-computed(可见行count不等,tracked漂移或OCR误读)',
                             source='computed_vs_ocr', faction=_f)
        state.board = _computed
        # next_tier 从注册表 tier 表算(>count 的最小 tier;无更高档 → 0)
        state.board_next_tier = {}
        for _f, _c in _computed.items():
            _tiers = FACTIONS[_f].tiers if _f in FACTIONS else ()
            _nt = next((t for t in _tiers if t > _c), 0)
            if _nt:
                state.board_next_tier[_f] = _nt
    else:
        state.board = _ocr_board
        state.board_next_tier = {f: nt for f, (_c, nt) in _bp.items() if nt > 0}
    # 旧不填 deployed → 恒 [] → deployed_count() 恒 0 → _saving_for_interest 永不触发(不攒息散买 gold→0)
    # + 买/deploy 门失效。identity/前后排近似(计数门用,实际槽位 DeployBench SIFT 处理)。
    # 不破坏):tracked 漂移时(sell 位置式 / deploy SIFT char_id='?' 未识别)截断多的 / 补 rebuild 无身份差额。
    # active_strategies:session(持久宿主,handle_invest_strategy 写)→ state(_refresh_cap 等消费;
    # live 修复 2026-08-15,原接线只加 GameState 字段无来源恒空)。
    if _match is not None and _match.session is not None:
        state.active_strategies = list(_match.session.active_strategies)
    if _tracked_dep:
        import copy
        state.deployed = copy.deepcopy(_tracked_dep)
        _board_n = min(sum(state.board.values()), state.level)
        if len(state.deployed) > _board_n:
            # 观察冲突审计 #10(2026-08-16):截断=双源分歧(tracked 多计于 board OCR,如 deploy SIFT 漂移)
            # —— 静默截断毒化部署近似;留证供毒化率统计。
            obs_conflict('deployed_align', len(state.deployed), _board_n, screen,
                         verdict='截断-tracked多计(board OCR 为准)', source='tracked_vs_board')
            state.deployed = state.deployed[:_board_n]   # 截断(tracked 多计,如 deploy SIFT 漂移)
        elif len(state.deployed) < _board_n:
            obs_conflict('deployed_align', len(state.deployed), _board_n, screen,
                         verdict='补齐-tracked少计(rebuild 无身份)', source='tracked_vs_board')
            _rebuild = rebuild_deployed_from_board(state.board, state.back_max, max_count=state.level)
            state.deployed.extend(_rebuild[len(state.deployed):])   # 补无身份(tracked 少计,如 sell 漂移)
    else:
        state.deployed = rebuild_deployed_from_board(state.board, state.back_max, max_count=state.level)
    state.shop = read_shop_cards(ctx, screen)
    # r77(轮岗接线):商店开态顺手读概率条真值(60/22/15/3/0 类)——read 失败(None)时
    # 消费方(_sample_cost)自动退基线表;成功时 D 牌蒙特卡洛用实际分布。
    state.refresh_probs = read_refresh_probs(ctx, screen)
    state.bench_full_flag = read_bench_full(ctx, screen)
    # [停机钩子·已删(2026-08-17 M72 采全)] star≥3 停机采集:19 位 fixture 已采全
    # (star3_slots/),read_star 全位置断言 3 测试过(test_star3_positions)。⚠️ 教训存档:
    # ①「停 bot 保画面」在备战不成立——备战有倒计时,到期自动出战推进(bot 停游戏不停),
    #   M72 停机后游戏自己打完了 P2-9;此类需当场交互的采集,现场窗口=倒计时前,分小批+
    #   批间验证落位;②事件 overlay(选择伙伴)盖棋盘时拖拽全部静默失败,批次必须验证;
    # ③VLM 看不清星数(开商店帧误报"银狼3星"),定位 3 星用 read_star 全帧扫描。
    return state


# → 无法可靠选 deploy comp 卡 + pref 定位。pixel-diff(buy 前/后 bench 截图 diff)找新占槽 = bought 卡落点,
BENCH_SLOT_DIFF_THRESHOLD: float = 10.0   # absdiff 均值阈值;新 char icon 显著 > 此(校准待实跑)


def new_bench_slots(ctx: SrContext, before: MatLike, after: MatLike) -> list[int]:
    """buy 前/后 bench 哪些物理槽(1..9)新被占(pixel-diff:新 char icon 出现 → 高 absdiff 均值)。

    char→slot 感知根解。返回新占槽 idx 列表(**left-to-right 升序** = buy 顺序,因 bench 从左到右填)。
    调用方(buy op)把本结果与同轮 bought 卡名(buy 顺序)zip → char→slot map。无需角色身份(纯像素,可靠)。
    """
    log.info('[cw-bench-diff] new_bench_slots CALLED')
    si = ctx.screen_loader.get_screen('货币战争-备战')
    if si is None:
        return []
    changed: list[int] = []
    for i in range(1, 10):
        area = next((a for a in si.area_list if a.area_name == f'备战栏-{i}'), None)
        if area is None or area.pc_rect is None:
            continue
        _r = area.pc_rect   # Rect 对象(有 .x1/.y1/.x2/.y2 属性,非可迭代;旧 `x1,y1,x2,y2=pc_rect` 致 TypeError)
        x1, y1, x2, y2 = _r.x1, _r.y1, _r.x2, _r.y2
        b = before[y1:y2, x1:x2]
        a = after[y1:y2, x1:x2]
        if b.size == 0 or a.size == 0:
            continue
        diff = float(cv2.absdiff(b, a).mean())   # 新 icon → 多像素变化 → 高均值
        if diff > 1.0:
            log.info(f'[cw-bench-diff] slot{i} diff={diff:.1f}')
        if diff > BENCH_SLOT_DIFF_THRESHOLD:
            changed.append(i)
    return changed   # 已 left-to-right(slot idx 升序,range 1..9)
