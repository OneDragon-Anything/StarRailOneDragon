# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 **备战屏**观测:备战截图 → ``GameState``(``read_game_state``)。

本模块只管**备战屏** reads(gold/hp/level/phase_round/board[+next_tier]/shop/bench_full)+ 组合入口
``read_game_state``。简报 reads 在 ``cw_briefing_obs``、结算 reads 在 ``cw_settlement_obs``、
共享 helper/常量在 ``cw_obs_core``;本模块 **re-export** 简报/结算的公开函数,故
``from cw_observation import read_affixes / parse_settlement_hp / ...`` 向后兼容(2026-08-06 拆分,D-70)。

备战字段采集按 doc 13(``strategy/13_input_model.md``)逐簇推进(D-69 board tier 已接,余待采:
active_strategies/enemy_difficulty/level_up_cost/inventory 等;icon/身份类阻塞于 vision/SIFT 库)。

**区域单一真相源 = screen_info**(用户 2026-08-03):``assets/game_data/screen_info/currency_war_battle_prep.yml``
(screen「货币战争-备战」),经 ``cw_obs_core._area_rect`` 读 area 的 pc_rect —— 改区域改 yml 即可,不动代码。

设计原则(strategy/05 签名+失败语义 + 06 P2-3 sanity bounds):
- 每字段用 ``_ocr(rect=...)`` 定区域读(**不塌缩重复文本** —— 地图版 get_ocr_result_map 按文本聚合,
  两张同阵营牌会撞键丢一张;list 版保留全部)。
- OCR 失败 / 越界(sanity bounds)→ 安全默认,不抛错(plan 对默认安全降级:
  gold 默认 0 → 不买;hp 默认 100 → 不触发保血)。越界读(gold 读成 500)比读不到更危险。

v1 OCR 可读性(2026-08-03,实机多样本 + 诊断脚本确认):
- **level**:``read_level`` OCR 优先 + ``_expected_level`` 兜底;telemetry level 跨样本合理(✓)。
- **hp**:⚠️ **plan-time 读不到(保血原本未武装),根因已确认 = shop 开启时右上角 HP 区空,非读取器坏**。
  ``BuyShopCards`` 在 shop 关闭帧读 hp → 覆盖 state.hp(见 shop.buy;回归 test_read_hp_shop_state)。
- **board**:count 解析曾脆(全屏 OCR 把 "2/3" 误读 "213");D-69 改用 ``_board_pairs`` 聚焦解析 X/Y,
  count=X + next_tier=Y(``read_board_next_tier``),根因(全屏密度)解决。
"""
from __future__ import annotations

import difflib
import re

import cv2
from cv2.typing import MatLike

from one_dragon.base.geometry.rectangle import Rect

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
from sr_od.application.currency_war.cw_chars import CHARACTER_ROSTER, get_char
from sr_od.application.currency_war.cw_factions import FACTIONS
from sr_od.application.currency_war.cw_obs_core import (
    A_BOARD,
    A_GOLD,
    A_PHASE,
    A_SHOP_REGION,
    COL_TOLERANCE,
    GOLD_MAX,
    GOLD_MIN,
    HP_MAX,
    HP_MIN,
    LEVEL_MAX,
    LEVEL_MIN,
    SHOP_FACTION_NAME_SPLIT_Y,
    _area_rect,
    _first_int,
    _ocr,
    area_center,  # noqa: F401 (re-export:importer 经 cw_observation.area_center 用)
    shop_card_click_points,
)
from sr_od.application.currency_war.cw_settlement_obs import (  # noqa: F401
    parse_settlement_hp,
    read_round_outcome,
)
from sr_od.application.currency_war.cw_state import (
    GameState,
    ShopCard,
    rebuild_deployed_from_board,
)
from sr_od.context.sr_context import SrContext


def _expected_level(plane: int, round_num: int) -> int:
    """阶段期望等级(前期 4-6、中期 6-8、后期 8-10;同 cw_decisions._expected_level)。

    level 不可 OCR 时作兜底:≈ 真实等级,使 economy level_val≈0(不误判欠等级 → 不滥升)
    + max_units≈ 真实(模拟 deploy 容量合理)。
    """
    if plane <= 1:
        return min(4 + round_num // 2, 6)
    if plane == 2:
        return min(6 + (round_num - 1) // 2, 8)
    return min(8 + (round_num - 1) // 3, 10)


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


def read_hp(ctx: SrContext, screen: MatLike) -> int:
    """小队剩余血量(备战屏右上角 ``文本-剩余血量``)。读不到/越界 → 100(健康先验)。

    **plan-time 读不到,根因已多样本确认(2026-08-03):HP 只在 shop 关闭态显示右上角;shop 开启态该区空。**
    5 张 shop-关闭态全读到真 HP(80/80/80/29/84)、shop-开启态该区空 → 默认 100。本函数正确 ——
    ``BuyShopCards`` 在 shop 关闭帧读 hp 覆盖 state.hp(见 shop.buy)。回归:``test_read_hp_shop_state``。
    """
    v = _first_int([r.data for r in _ocr(ctx, screen, _area_rect(ctx, '文本-剩余血量'))])
    if v is None or not (HP_MIN <= v <= HP_MAX):
        return 100
    return v


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


def read_node_type(ctx: SrContext, screen: MatLike) -> str | None:
    """备战顶部「当前节点类型」标签 → node_type(boss/补给/遭遇/...;doc 13 §13.2A)。

    OCR 顶部节点行下方的类型标签带 → 关键词映射(首领→boss 等)。读不到 / 无已知关键词 → None。
    标签在当前节点图标下方(x 随当前节点位置变),故扫整条节点行宽。

    ⚠️ 仅 boss(首领)实机核实;其它节点类型标签措辞待多子态实机核实(现 map 覆盖常见词,
    命中即返,未核实的不影响 boss 检测)。区域暂硬编码(同 read_xp_progress,后续移 screen_info)。
    """
    blob = ''.join(r.data for r in _ocr(ctx, screen, Rect(500, 65, 1700, 115)))
    for kw, nt in _NODE_TYPE_KEYWORDS.items():
        if kw in blob:
            return nt
    return None


def read_xp_progress(ctx: SrContext, screen: MatLike) -> tuple[int, int] | None:
    """购买经验进度 ``(cur_xp, xp_to_next_level)``,购买经验按钮下方 "X/Y"(D-69 备战字段采集)。

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
    """
    global _last_phase_round
    blob = ''.join(r.data for r in _ocr(ctx, screen, _area_rect(ctx, A_PHASE)))
    m = re.search(r'(\d)\s*-\s*(\d)', blob)          # "1-3"
    if m:
        _last_phase_round = (int(m.group(1)), int(m.group(2)))
        return _last_phase_round
    plane_m = re.search(r'第\s*(\d)\s*位面', blob)
    if plane_m:
        _last_phase_round = (int(plane_m.group(1)), int(plane_m.group(1)))
        return _last_phase_round
    digits = re.findall(r'\d', blob)
    if digits:
        _last_phase_round = (int(digits[0]), int(digits[0]))
        return _last_phase_round
    # OCR 失败(过渡帧)→ 返回上次成功值,避免 (1,1) 误导 level_plan
    if _last_phase_round is not None:
        return _last_phase_round
    return 1, 1


def read_deployed_count(ctx: SrContext, screen: MatLike) -> int | None:
    """舞台中央「X/Y」指示 → X(已部署角色数);读不到 → None。

    DeployBench 用它定位**空位**:D-108d(cap_remaining)+ D-108e(offset)依赖它;读不到 → fallback
    → 部分 churn。**small stylized「X/Y」paddle det 常漏**(同 gold/cost,T-96)→ crop + 3x 放大破 det
    天花板(read_gold 同法,T-92)。仍读不到 → None(调用方 fallback)。
    """
    rect = _area_rect(ctx, '区域-部署数')
    if rect is None:
        return None
    crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
    if crop.size == 0:
        return None
    up = cv2.resize(crop, (crop.shape[1] * 3, crop.shape[0] * 3), interpolation=cv2.INTER_CUBIC)
    blob = ''.join(r.data for r in ctx.ocr_service.get_ocr_result_list(image=up))
    m = re.search(r'(\d+)\s*/\s*\d+', blob)
    return int(m.group(1)) if m else None


def _board_pairs(ctx: SrContext, screen: MatLike) -> dict[str, tuple[int, int]]:
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
            # sanity:count 1-9;next_tier 1-12(阵营 tier 最高 ~9,留余量)。越界 → 兜底。
            cnt = cnt if 1 <= cnt <= 9 else 1
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


def read_board_next_tier(ctx: SrContext, screen: MatLike) -> dict[str, int]:
    """OCR 左面板 → {阵营名: 下个 tier 阈值}(= ``_board_pairs`` 的 Y;doc 13 ``FactionState.next_tier``)。

    只含 Y 解析到的阵营(0/未显阈值的不进 dict)。聚焦裁切 OCR 才稳(见 ``_board_pairs``)。
    """
    return {f: nt for f, (_c, nt) in _board_pairs(ctx, screen).items() if nt > 0}


def _match_char(text: str) -> str:
    """OCR 牌名 → CHARACTER_ROSTER 规范名(精确 → 子串 → difflib 近似);无则 ''。"""
    t = (text or '').strip()
    if not t:
        return ''
    if t in CHARACTER_ROSTER:
        return t
    for name in CHARACTER_ROSTER:           # 子串(OCR 多读/少读字符)
        if name in t or t in name:
            return name
    matches = difflib.get_close_matches(t, CHARACTER_ROSTER, n=1, cutoff=0.6)
    return matches[0] if matches else ''


def read_shop_cards(ctx: SrContext, screen: MatLike) -> list[ShopCard]:
    """OCR 商店 5 张牌 → list[ShopCard](x + faction + name + cost)。

    牌位 x 从 screen_info 商店牌-1..5 中心读;整体 OCR 商店牌区 → 按 y 分阵营标签
    (< ``SHOP_FACTION_NAME_SPLIT_Y``)/ 角色名(>= 该 y)→ 按 x 分配到最近牌位。name 经
    CHARACTER_ROSTER 匹配 → 顺带得 cost;name 未知 → cost=0(card_cost 兜底 3)。商店须已打开。
    """
    centers = shop_card_click_points(ctx)
    shop_rect = _area_rect(ctx, A_SHOP_REGION)
    if not centers or shop_rect is None:
        return []
    faction_by_x: dict[int, str] = {}
    name_by_x: dict[int, str] = {}
    for r in _ocr(ctx, screen, shop_rect):
        cx, cy = r.center.x, r.center.y
        nearest = min(centers, key=lambda p: abs(p.x - cx))
        if abs(nearest.x - cx) > COL_TOLERANCE:
            continue
        x = int(nearest.x)
        if cy < SHOP_FACTION_NAME_SPLIT_Y:           # 阵营标签行
            f = next((f for f in FACTIONS if f in (r.data or '')), None)
            if f and x not in faction_by_x:
                faction_by_x[x] = f
        else:                                        # 角色名行
            name = _match_char(r.data or '')
            if name and x not in name_by_x:
                name_by_x[x] = name
    cards: list[ShopCard] = []
    for pt in centers:
        x = int(pt.x)
        ch = get_char(name_by_x.get(x, '')) if name_by_x.get(x) else None
        cost = ch.cost if ch is not None else 0
        cards.append(ShopCard(x=x, faction=faction_by_x.get(x, '?'),
                              name=name_by_x.get(x, ''), cost=cost, star=1))
    return cards


def read_bench_full(ctx: SrContext, screen: MatLike) -> bool | None:
    """「备战席已满」警告(True=满,需破;None=未观察到)。"""
    for kw in ('备战席已满', '出售或提升等级'):
        if any(kw in (r.data or '')
               for r in _ocr(ctx, screen, Rect(600, 360, 1320, 540))):
            return True
    return None


# ===== 组合入口 =====
def read_game_state(ctx: SrContext, screen: MatLike) -> GameState:
    """一战前备战屏(商店已开)→ GameState(喂 plan)。

    各字段 OCR 失败 → 安全默认(见各 reader)。level 不可 OCR → ``_expected_level`` 兜底;
    hp 不可 OCR → 默认 100。v1 不读 bench/deployed 身份(buy 决策靠 board+shop+gold;
    deploy 走 DeployBench)。
    """
    state = GameState()
    state.gold = read_gold(ctx, screen)
    state.hp = read_hp(ctx, screen)
    state.plane, state.round_num = read_phase_round(ctx, screen)
    state.node_type = read_node_type(ctx, screen)
    state.level = read_level(ctx, screen, state.plane, state.round_num)
    state.xp_progress = read_xp_progress(ctx, screen)
    state.enemy_difficulty = read_enemy_difficulty(ctx, screen)
    state.level_up_cost = read_level_up_cost(ctx, screen)
    state.shop_refresh_cost = read_shop_refresh_cost(ctx, screen)
    state.streak = read_streak(ctx, screen)
    # 单次 OCR 填 board(count) + board_next_tier(下个 tier 阈值,Y);doc 13 FactionState。
    _bp = _board_pairs(ctx, screen)
    state.board = {f: c for f, (c, _nt) in _bp.items()}
    state.board_next_tier = {f: nt for f, (_c, nt) in _bp.items() if nt > 0}
    # D-107(RC1,治 T#97 战术层 desync):deployed 从 board 真值重建 → deployed_count() 对齐实际阵上数。
    # 旧不填 deployed → 恒 [] → deployed_count() 恒 0 → _saving_for_interest 永不触发(不攒息散买 gold→0)
    # + 买/deploy 门失效。identity/前后排近似(计数门用,实际槽位 DeployBench SIFT 处理)。
    state.deployed = rebuild_deployed_from_board(state.board, state.back_max)
    state.shop = read_shop_cards(ctx, screen)
    state.bench_full_flag = read_bench_full(ctx, screen)
    return state
