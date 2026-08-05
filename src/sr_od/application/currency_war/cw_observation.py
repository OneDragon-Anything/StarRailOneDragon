"""货币战争 OCR 观测层:备战屏截图 → GameState(``read_game_state``)。

阶段 4(strategy/05 数据接线 + 06 阶段 4):把备战屏各 HUD 字段经 OCR 读成
``GameState``,喂 ``cw_decisions.plan``。这是「之前留空(假设不能操作游戏)」的部分。

**区域单一真相源 = screen_info**(用户 2026-08-03):所有 OCR/点击区域存
``assets/game_data/screen_info/currency_war_battle_prep.yml``(screen「货币战争-备战」),
本模块经 ``ctx.screen_loader`` 读 area 的 pc_rect —— 改区域改 yml 即可,不动代码(同 DeployBench)。

设计原则(strategy/05 签名+失败语义 + 06 P2-3 sanity bounds):
- 每字段用 ``get_ocr_result_list(rect=...)`` 定区域读(**不塌缩重复文本** —— 地图版
  get_ocr_result_map 按文本聚合,两张同阵营牌会撞键丢一张;list 版保留全部)。
- OCR 失败 / 越界(sanity bounds)→ 安全默认,不抛错(plan 对默认安全降级:
  gold 默认 0 → 不买;hp 默认 100 → 不触发保血)。越界读(gold 读成 500)比读不到更危险。

v1 OCR 可读性(2026-08-03,实机多样本 + 诊断脚本确认):
- **level**:``read_level`` OCR 优先 + ``_expected_level`` 兜底;telemetry level 跨样本合理(✓)。
- **hp**:⚠️ **plan-time 读不到(保血原本未武装),根因已确认 = shop 开启时右上角 HP 区空,非读取器坏**。
  ``read_hp`` 区域 [1408,23,1498,103]:5 张 shop-**关闭**态全读到真 HP(80/80/80/29/84)、shop-**开启**态
  该区空 → 默认 100;telemetry(plan-time=shop 开)全 100 印证。**修法在 BuyShopCards:shop 关闭帧读 hp →
  覆盖 state.hp**(见 shop.buy;回归 test_read_hp_shop_state)。(gold 可读性**非严格 shop 态决定**,待更多样本。)
- **board**:⚠️ **count 解析脆 + 已加 sanity bound**。面板格式复杂(显示 "X/Y" 或激活 tier 串,非纯计数),
  ``read_board`` "最近下方数字" 偶抓 garble(telemetry ``能量:213``/``减益:2141618`` 等)。已加 count∈[1,9]
  越界默认 1 防 synergy_score 垃圾入;面板真实格式待视觉核实后重写解析。

v1 范围:读 gold/plane/round/board/shop/bench_full —— 喂 plan 的买/升/经济决策。
bench/deployed 身份不读(deploy 走 DeployBench deploy-all;buy 决策靠 board+shop+gold)。
target_comp 由上层 shop op 跨回合管理(``select_comp``/``maybe_pivot`` 已接,2026-08-04,详 cw_comps);
PerformanceTracker(comp_viability 观测)待阶段 4-5 接线。
"""
from __future__ import annotations

import difflib
import re

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.geometry.rectangle import Rect
from sr_od.application.currency_war.cw_chars import CHARACTER_ROSTER, get_char
from sr_od.application.currency_war.cw_factions import FACTIONS
from sr_od.application.currency_war.cw_state import GameState, ShopCard
from sr_od.context.sr_context import SrContext

# screen_info「货币战争-备战」(currency_war_battle_prep.yml)area 名
SCREEN_NAME: str = '货币战争-备战'
A_GOLD: str = '文本-金币数'
A_PHASE: str = '区域-阶段'
A_BOARD: str = '区域-羁绊面板'
A_SHOP_REGION: str = '商店牌区'             # 5 张牌的阵营+名文本带(整体 OCR,按 y 分阵营/名)
A_SHOP_CARD_PREFIX: str = '商店牌-'        # 商店牌-1..5(点击中心)
# 商店牌区内行分类阈值(卡牌布局固定):y < 此 = 阵营标签;>= 此 = 角色名
SHOP_FACTION_NAME_SPLIT_Y: int = 278

# sanity bounds(06 P2-3;越界 → 丢弃用默认,防误读级联:gold 读成 500 → 狂买)
GOLD_MIN, GOLD_MAX = 0, 400
HP_MIN, HP_MAX = 0, 200
LEVEL_MIN, LEVEL_MAX = 1, 10
COL_TOLERANCE: int = 100                   # 文本 x 分配到牌位的容差

# 简报屏(对局开始,词缀读取;非备战)
BRIEFING_SCREEN: str = '货币战争-简报'


def _area_rect(ctx: SrContext, name: str, screen_name: str = SCREEN_NAME) -> Rect | None:
    """从 screen_info 取 area 的 pc_rect(Rect);screen/area 缺失 → None。

    Args:
        screen_name: 画面名(默认备战);事件态画面(投资环境/投资策略等)传其画面名。
    """
    si = ctx.screen_loader.get_screen(screen_name)
    if si is None:
        return None
    area = next((a for a in si.area_list if a.area_name == name), None)
    return area.pc_rect if (area is not None and area.pc_rect is not None) else None


def area_center(ctx: SrContext, name: str, screen_name: str = SCREEN_NAME) -> Point | None:
    """从 screen_info 取 area 中心 Point(点击用);缺失 → None。

    Args:
        screen_name: 画面名(默认备战);事件态画面(投资环境/投资策略等)传其画面名。
    """
    rect = _area_rect(ctx, name, screen_name)
    return rect.center if rect is not None else None


def shop_card_click_points(ctx: SrContext) -> list[Point]:
    """商店 5 牌位点击中心(按 商店牌-1..5 顺序,screen_info);screen 缺失 → []。"""
    si = ctx.screen_loader.get_screen(SCREEN_NAME)
    if si is None:
        return []
    pts: list[Point] = []
    for i in range(1, 6):
        area = next((a for a in si.area_list if a.area_name == f'{A_SHOP_CARD_PREFIX}{i}'), None)
        if area is not None and area.pc_rect is not None:
            pts.append(area.pc_rect.center)
    return pts


def _ocr(ctx: SrContext, screen: MatLike, rect: Rect | None) -> list:
    """对 screen 的 rect 区域 OCR(rect None → [])。"""
    if rect is None:
        return []
    return ctx.ocr_service.get_ocr_result_list(image=screen, rect=rect, crop_first=False)


def _first_int(texts: list[str]) -> int | None:
    """从文本列表提取第一个整数(逐文本正则);无则 None。"""
    for t in texts:
        m = re.search(r'\d+', t)
        if m:
            return int(m.group())
    return None


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


# ===== 单字段读取(失败 → 安全默认)=====

def read_gold(ctx: SrContext, screen: MatLike) -> int:
    """当前金币(底部右侧数字)。读不到 / 越界 → 0(plan 不买,安全保守)。"""
    v = _first_int([r.data for r in _ocr(ctx, screen, _area_rect(ctx, A_GOLD))])
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


# ===== 简报观测(对局开始;affixes → state.enemy_affixes → mechanics_fit)=====
def read_affixes(ctx: SrContext, screen: MatLike) -> list[str]:
    """简报词缀行 → 敌人词缀 OCR 原名列表(每局随机,A8 最高 4 个)。

    读简报「区域-词缀行」area OCR → 词缀文字(滤数字/符号/短噪声)。下游
    ``AFFIX_MECHANIC_MAP``(cw_comps)映射机制 tag;未知词缀透传(mechanics_fit 中性)。
    读不到 / area 缺 → [](不覆盖 state.enemy_affixes)。

    OCR 名 vs competitors 数据名可能差(如 OCR「后台熄火」= competitors「前后台熄火」),
    透传原名,匹配在 AFFIX_MECHANIC_MAP(待实机校准补全,见 competitors.md 待确定)。
    """
    rect = _area_rect(ctx, '区域-词缀行', BRIEFING_SCREEN)
    if rect is None:
        return []
    affixes: list[str] = []
    for r in _ocr(ctx, screen, rect):
        name = r.data.strip()
        # 词缀名:中文为主,2-7 字(第二位面强化6/前后台熄火5/火之熄火4/同步行动4);滤数字/符号/短噪声
        if 2 <= len(name) <= 7 and re.search(r'[一-鿿]', name) and not re.search(r'\d', name):
            affixes.append(name)
    return affixes


def read_bosses(ctx: SrContext, screen: MatLike) -> list[str]:
    """简报首领行 → 3 个位面 boss 名列表(每局固定 3 boss,如 增熵能源集团/火线动力机甲/银甲武装公司)。

    3 个位面是货币战争的玩法结构(每局 3 位面 × 每位面 1 boss),**所有难度(A5/A8/A850)都 3 个,
    不随难度变**(2026-08-05 攻略 + 官方确认;难度只改敌人强度/词缀,不改位面数)。

    简报屏 3 boss 横排卡片(立绘 + 阵营标签 + 名字);读「区域-首领行」area OCR → boss 名
    (滤数字/符号/短噪声/「阵营」2 字 label)。下游 ``state.bosses`` → ``boss_fit(comp, bosses)``
    命中 ``comp.boss_weakness`` 打分。读不到 / area 缺 → [](不覆盖 state.bosses)。

    ⚠️ 数据层待补(同 competitors.md,后续浏览器/图鉴采):boss 机制 + 哪些 comp 怕哪个 boss
    (``comp.boss_weakness``)。当前 ``comp.boss_weakness`` 多为空 → boss_fit 中性 0.5;识别链路先通,
    数据层后续接上即生效。boss 阵营(红色标签内)OCR 暂不读(红底干扰,待视觉核实后再决定是否采)。
    """
    rect = _area_rect(ctx, '区域-首领行', BRIEFING_SCREEN)
    if rect is None:
        return []
    bosses: list[str] = []
    for r in _ocr(ctx, screen, rect):
        name = r.data.strip()
        # boss 名:6 字中文为主(增熵能源集团/火线动力机甲/银甲武装公司);滤「阵营」label(2字)/数字/符号
        if 4 <= len(name) <= 8 and re.search(r'[一-鿿]', name) and not re.search(r'\d', name):
            bosses.append(name)
    return bosses


# ===== 结算屏观测(P1.5 观测回路;on_round_end 输入)=====
# 结算屏(战斗后「挑战结束/数据统计/继续挑战」)展示战后小队 HP「小队生命值<N>」+ 总伤害等
# (2026-08-05 实跑 OCR 确认形态:['挑战结束','战斗','小队生命值71i','数据统计','连胜×0','继续挑战'])。
# OCR 全屏解析 hp_after;node_type/comp_tag/plane/round 由调用方(loop)传入(结算屏不暴露这些)。


def parse_settlement_hp(ocr_texts: list[str]) -> int | None:
    """结算屏「小队生命值<N>」→ hp_after(纯函数,可单测;P1.5)。

    取含「生命值」的文本,解析其**紧邻后方**的数字(``生命值\\s*(\\d+)``)—— 紧邻而非首部/尾部,
    防「每损失20点小队生命值获得5」(投资策略描述,偶同屏)误取 20/5。越界(HP_MIN..HP_MAX)→ 丢弃。
    """
    for t in ocr_texts:
        if '生命值' in t:
            m = re.search(r'生命值\s*(\d+)', t)
            if m:
                v = int(m.group(1))
                if HP_MIN <= v <= HP_MAX:
                    return v
    return None


def read_round_outcome(ctx: SrContext, screen: MatLike, *, plane: int, round_num: int,
                       comp_tag: str, node_type: str = '普通战斗'):
    """结算屏 → ``RoundOutcome``(观测回路 P1.5;``on_round_end`` 输入)。

    OCR 全屏 → ``parse_settlement_hp`` 得 hp_after;解析成功 hp_confidence=1.0(进 trend),失败 0.0
    (< ``HP_CONFIDENCE_THRESHOLD`` 不进 trend,防噪声)。plane/round_num/comp_tag/node_type 由调用方
    (loop,知当前节点 + ``session.target_comp``)传入 —— 结算屏本身不暴露这些。

    ⚠️ P1.5 组件:本函数已就位 + 单测,但 ``battle_loop`` 的 on_round_end 接线(结算检测 → 调本函数 →
    ``strategy.on_round_end``)留下局部署(避免杀当前验证 match);node_type 推断暂粗(默认普通战斗,
    boss/elite 需节点追踪,后续 refine)。
    """
    from sr_od.application.currency_war.cw_performance import RoundOutcome
    ocr_texts = [r.data for r in ctx.ocr_service.get_ocr_result_list(
        image=screen, rect=None, crop_first=False)]
    hp = parse_settlement_hp(ocr_texts)
    return RoundOutcome(
        round_num=round_num, plane=plane, node_type=node_type, comp_tag=comp_tag,
        hp_after=hp if hp is not None else 0,
        hp_confidence=1.0 if hp is not None else 0.0,
    )


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

    DeployBench 用它定位**空位**:从 stage 第 X 个槽起部署(跳过已占的前 X 个),
    否则拖到已占槽会被拒(货币战争 drag-to-occupied 不交换)→ 备战栏角色部署不上去 →
    出战(需满员/接近满员才触发)卡死。
    """
    blob = ''.join(r.data for r in _ocr(ctx, screen, _area_rect(ctx, '区域-部署数')))
    m = re.search(r'(\d+)\s*/\s*\d+', blob)
    return int(m.group(1)) if m else None


def read_board(ctx: SrContext, screen: MatLike) -> dict[str, int]:
    """OCR 左面板 → {阵营名: 在场人数}。

    每个激活阵营一行:阵营名 + 其下的激活人数(如 "3",或 "3/5" 取首数)。list OCR 不聚合
    (两阵营同人数不撞键);逐结果匹配 FACTIONS 名,取其**正下方最近**的纯数字当人数;
    有阵营名无下方数字 → 默认 1(至少 1 人在场才显示)。
    """
    results = _ocr(ctx, screen, _area_rect(ctx, A_BOARD))
    results.sort(key=lambda r: r.center.y)
    board: dict[str, int] = {}
    for i, r in enumerate(results):
        faction = next((f for f in FACTIONS if f in (r.data or '')), None)
        if faction is None or faction in board:
            continue
        count: int | None = None
        for r2 in results[i + 1:]:
            dy = r2.center.y - r.center.y
            if dy > 45:
                break
            if dy <= 0:
                continue
            data = r2.data or ''
            # count 显示为 "X/Y"(X=在场人数,Y=下个 tier 阈值,如 仙舟"1/3");优先此格式取 X。
            # 裸数字(无斜杠)多是 tier 链残留(如燃血 "2/4/6/8" → OCR "8" / "2141618")或邻行资源数,
            # 旧逻辑 grab 首位数字会把它误当 count(2026-08-04 实测 燃血:8/能量:7 喂脏 eval)→ skip。
            m_xy = re.search(r'(\d+)\s*/\s*\d+', data)
            if m_xy:
                count = int(m_xy.group(1))
                break
            # 无 "X/Y"(裸数字)→ 不当 count,继续往下找真正的 "X/Y"(可能在稍下方一行)。
        # sanity bound:count 应 1-9;越界/未找到 → 默认 1(至少 1 人在场才显示该阵营),防 synergy_score 垃圾入。
        # ⚠️ 残留风险:动画期面板只显示 tier 链(无 "X/Y")→ count=None→默认1(保守,优于脏 8)。
        board[faction] = count if (count is not None and 1 <= count <= 9) else 1
    return board


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
    state.level = read_level(ctx, screen, state.plane, state.round_num)
    state.board = read_board(ctx, screen)
    state.shop = read_shop_cards(ctx, screen)
    state.bench_full_flag = read_bench_full(ctx, screen)
    return state
