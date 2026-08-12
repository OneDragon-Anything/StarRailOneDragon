# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 **备战屏**观测:备战截图 → ``GameState``(``read_game_state``)。

本模块只管**备战屏** reads(gold/hp/level/phase_round/board[+next_tier]/shop/bench_full)+ 组合入口
``read_game_state``。简报 reads 在 ``cw_briefing_obs``、结算 reads 在 ``cw_settlement_obs``、
共享 helper/常量在 ``cw_obs_core``;本模块 **re-export** 简报/结算的公开函数,故
``from cw_observation import read_affixes / parse_settlement_hp / ...`` 向后兼容(2026-08-06 拆分,)。

备战字段采集按 doc 13(``strategy/13_input_model.md``)逐簇推进(board tier 已接,余待采:
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
    _area_rect,
    _first_int,
    _ocr,
    area_center,  # noqa: F401 (re-export:importer 经 cw_observation.area_center 用)
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

    ⚠️ screen 为框架 RGB;S/V/Hu 对 RGB/BGR 无关(见 CLAUDE.md RGB 约定)→ 直传 classify。
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
    _cur = read_node_type(ctx, screen)
    if _cur:
        for _s in _slots:
            if _s.state == 'current':
                _s.node_type = _cur
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
    保血阈值调高(D-32,cw_state:253 + config.difficulty_hp_override)。读不到 → ""(回退默认)。
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


def read_board_next_tier(ctx: SrContext, screen: MatLike) -> dict[str, int]:
    """OCR 左面板 → {阵营名: 下个 tier 阈值}(= ``_board_pairs`` 的 Y;doc 13 ``FactionState.next_tier``)。

    只含 Y 解析到的阵营(0/未显阈值的不进 dict)。聚焦裁切 OCR 才稳(见 ``_board_pairs``)。
    """
    return {f: nt for f, (_c, nt) in _board_pairs(ctx, screen).items() if nt > 0}


def read_shop_cards(ctx: SrContext, screen: MatLike) -> list[ShopCard]:
    """SIFT 商店 5 张牌肖像 → list[ShopCard](x + faction + name + cost)。

    每张牌:裁 screen_info ``商店牌-N``(**肖像区**,D-55 经 VLM 定位改自文字带)→ ``identify_character``
    SIFT 对 ``character_cw_portrait`` 立绘库 → ``resolve_char_name`` 规范名;faction/cost 从 roster 派生。
    未识别(低内点/歧义/不在 roster)→ name='' faction='?' cost=0(仍占位保 5 张,len 不变)。

    **D-55 由 OCR 改 SIFT**:OCR 牌名对开拓者(玩家自定义名,如 "Momojie")等读不到/匹配错;SIFT 看
    肖像更稳(实测 shop_open 5/5 内点 33-68,VLM 定位肖像区)。faction 由 OCR 牌标签 → roster factions[0]
    (SIFT 读不了文字标签;**board OCR 仍是阵营计数权威**)。立绘库经 ``ensure_portrait_templates`` 按需加载
    (buy 在 deploy 前,BattlePrepCycle: buy→deploy,故不依赖 deploy 才加载的缓存)。
    """
    templates = ensure_portrait_templates(ctx)
    cards: list[ShopCard] = []
    for i in range(1, 6):
        rect = _area_rect(ctx, f'{A_SHOP_CARD_PREFIX}{i}')
        if rect is None:
            continue
        crop = screen[rect.y1:rect.y2, rect.x1:rect.x2]
        avatar_id, _inliers = (identify_character(crop, templates)
                               if templates is not None else (None, 0))
        name = resolve_char_name(avatar_id) if avatar_id else ''
        ch = get_char(name) if name else None
        cards.append(ShopCard(
            x=(rect.x1 + rect.x2) // 2,
            faction=(ch.factions[0] if (ch is not None and ch.factions) else '?'),
            name=name,
            cost=(ch.cost if ch is not None else 0),
            star=1,
        ))
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
    # 单调守卫(level-robust,2026-08-09 自审 §4):等级局内**只升不降**(CW 无降级机制)。
    # read_level OCR 间歇误读(实测 r1 lv4→r2 lv5→r3 lv4 倒退;lv4 非 _expected_level 兜底[=5] → 是 OCR 把
    # 5/6 读成 4)→ level 字段不可信 → max_units/cap/economy 全跟着错。守卫:读出 < session 上次真值 = 误读,
    # 用上次真值(单调不降);新局 session 重置 last_level_obs=0 自然从首读起。
    _match = getattr(ctx, 'cw_match', None)
    if _match is not None and _match.session is not None:
        _last_lv = getattr(_match.session, 'last_level_obs', 0)
        if _last_lv and state.level < _last_lv:
            log.info(f'[cw] level 单调守卫:OCR 读 {state.level} < 上次 {_last_lv}(误读)→ 用 {_last_lv}')
            state.level = _last_lv
        _match.session.last_level_obs = state.level
    state.xp_progress = read_xp_progress(ctx, screen)
    # enemy_difficulty:优先 session.enemy_difficulty(简报「敌人难度N」读,3.5.2);fallback 备战 read(常 null)
    _ed = getattr(getattr(_match, 'session', None), 'enemy_difficulty', None) if _match is not None else None
    state.enemy_difficulty = _ed if _ed is not None else read_enemy_difficulty(ctx, screen)
    state.level_up_cost = read_level_up_cost(ctx, screen)
    state.shop_refresh_cost = read_shop_refresh_cost(ctx, screen)
    # streak:优先 session.last_streak(结算「连胜×N」带符号,方向可靠;fixture 核实 2026-08-11);
    # 无 session(离线/测试)→ read_streak 备战 magnitude fallback。
    _sess = getattr(getattr(ctx, 'cw_match', None), 'session', None)
    if _sess is not None:
        state.streak = _sess.last_streak
    else:
        state.streak = read_streak(ctx, screen) or 0
    # 单次 OCR 填 board(count) + board_next_tier(下个 tier 阈值,Y);doc 13 FactionState。
    _bp = _board_pairs(ctx, screen, state.level)
    state.board = {f: c for f, (c, _nt) in _bp.items()}
    state.board_next_tier = {f: nt for f, (_c, nt) in _bp.items() if nt > 0}
    # 旧不填 deployed → 恒 [] → deployed_count() 恒 0 → _saving_for_interest 永不触发(不攒息散买 gold→0)
    # + 买/deploy 门失效。identity/前后排近似(计数门用,实际槽位 DeployBench SIFT 处理)。
    # 不破坏):tracked 漂移时(sell 位置式 / deploy SIFT char_id='?' 未识别)截断多的 / 补 rebuild 无身份差额。
    _match = getattr(ctx, 'cw_match', None)
    _tracked_dep = (_match.session.tracked_deployed
                    if (_match is not None and _match.session is not None) else None)
    if _tracked_dep:
        import copy
        state.deployed = copy.deepcopy(_tracked_dep)
        _board_n = min(sum(state.board.values()), state.level)
        if len(state.deployed) > _board_n:
            state.deployed = state.deployed[:_board_n]   # 截断(tracked 多计,如 deploy SIFT 漂移)
        elif len(state.deployed) < _board_n:
            _rebuild = rebuild_deployed_from_board(state.board, state.back_max, max_count=state.level)
            state.deployed.extend(_rebuild[len(state.deployed):])   # 补无身份(tracked 少计,如 sell 漂移)
    else:
        state.deployed = rebuild_deployed_from_board(state.board, state.back_max, max_count=state.level)
    state.shop = read_shop_cards(ctx, screen)
    state.bench_full_flag = read_bench_full(ctx, screen)
    # 采集钩子(临时,采完即删;3.5.3 read_star 2-3星验证):tracking star≥2 的 deployed/bench char
    # → 存备战屏(含立绘底部金星)供离线 read_star 2-3星验。screen=RGB,存图 RGB→BGR(cv2-utils 约定)。
    _hook_stars = [bc.star for bc in (*state.deployed, *getattr(state, 'bench', []))
                   if getattr(bc, 'star', 0) >= 2]
    if _hook_stars:
        try:
            import hashlib
            from pathlib import Path
            _mx = max(_hook_stars)
            _h = hashlib.md5(screen.tobytes()).hexdigest()[:8]
            _p = Path('.debug/temp/currency_war/shots') / f'star{_mx}__{_h}.png'
            if not _p.exists():
                _ok, _arr = cv2.imencode('.png', cv2.cvtColor(screen, cv2.COLOR_RGB2BGR))
                if _ok:
                    _arr.tofile(str(_p))
        except Exception:  # noqa: BLE001  采集失败不阻塞读 state
            pass
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
