"""货币战争 阵容库 + 战略层评分(comp_score / select_comp;纯逻辑,可测,不碰游戏)。

战略层(阶段 2,A2):从「reactive 加深领先」升级到「围绕目标阵容 commit + 转型 + 巨星」。
auto-chess 胜负手 = commit 哪个阵容 + 何时转型 + 巨星绑谁;本模块给**可配置 + 自适应**的选目标机制。

数据与设计依据(详 ``docs/game/currency_war/strategy/03_comp_planning.md`` +
``10_battle_and_enemies.md`` + ``docs/game/currency_war/data/comp_library.md``):
- ``COMP_LIBRARY``:起步 roster(~8 套,覆盖易/中/难成型 + 各机制,含 debuff=buff 的燃血)。
  依据 strategy_research §10(meta 横评)+ docs/game/currency_war/data/characters.md / factions.md(米游社 V4.4)。
- ``comp_score`` / ``select_comp``:按场面(gold/轮次/boss/已持牌/环境/词缀)多维打分选 target。

**核心原则(用户 2026-08-03,贯彻全程)**:
1. **一切 comp 相关** —— equip/mechanics 都挂钩目标阵容,无孤立评分(不设通用 equip_score/词缀表)。
   反重力皮靴对昼神阿雅(需 2 靴)是命脉、对别的 comp 不一定;正当防卫词缀对万敌燃血是利、对阿雅是克。
2. **debuff 可能是 buff** —— 同一词缀对不同阵容方向相反(mechanics_fit 双向:counter 降 + synergy 升)。
3. **COMP_LIBRARY 多维打分 + 运行时按场面选** —— 不锁死一套,按成型难度/boss/环境/词缀灵活选易成型又够强的。
4. **经济统一论** —— 每 comp 自带 ``level_plan``(成型路线),驱动战术层花超额金(接法见 cw_decisions,待接)。

⚠️ meta(版本依赖):core_chars/form_tiers/strength/form_difficulty 是 V4.4 起步估值,replay + 实玩迭代。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sr_od.application.currency_war.cw_investments import INVESTMENT_ENVS
from sr_od.application.currency_war.cw_state import GameState

if TYPE_CHECKING:
    from sr_od.application.currency_war.cw_performance import PerformanceTracker


def clamp(x: float, lo: float, hi: float) -> float:
    """限幅(lo..hi)。"""
    return lo if x < lo else (hi if x > hi else x)


# ===== 数据结构 =====

@dataclass
class LevelGoal:
    """某玩家等级该做什么(成型路线的一站;经济统一论驱动战术花超额金)。

    曲线随 COMP_LIBRARY 填(用户选 B:框架先定,曲线建库时填)。
    """
    action: str            # "level_up"(攒金升下一级,解锁更高费刷新率)/ "roll"(D 找核心)/ "stable"(稳住吃息)
    target_cost: int = 0   # roll 时重点找几费核心(0=不限;随等级升:前期1费/中期4费/后期5费)
    target_chars: list[str] = field(default_factory=list)   # 这级该找谁(core_chars 子集)
    star_goals: dict[str, int] = field(default_factory=dict)  # 角色名 → 目标星级(如 1费→3星、5费→2星)


@dataclass
class Comp:
    """一套目标阵容(meta 数据,V4.4 起步估值待实玩校准)。"""
    name: str                    # "巡击青雀"/"昼神阿雅"/"万敌单C"(roster 见 docs/game/currency_war/data/comp_library.md)
    factions: list[str]          # 核心阵营组合 ["仙舟","追击"](查 FACTIONS)
    core_chars: list[str]        # 核心角色(名)["青雀","知更鸟"]
    form_tiers: dict[str, int]   # 成型 tier 目标 {"仙舟":5,"追击":3}(几人激活算成型)
    strength: str                # "S"/"A"/"B" 综合强度(版本强度;2026-08-03:不标"邪道" —— 邪道非必需)
    form_difficulty: str         # "easy"/"medium"/"hard" 成型难度(用户:关键维度)
    level_plan: dict[int, LevelGoal] = field(default_factory=dict)  # 成型路线(玩家等级→该做什么);建库时填
    key_equips: list[str] = field(default_factory=list)      # 关键装备(可含重复,如阿雅需 2 反重力皮靴)
    boss_weakness: list[str] = field(default_factory=list)   # 克这阵容的 boss 名(boss_fit 用)
    mechanic_attributes: list[str] = field(default_factory=list)  # comp 机械属性 tag(mechanics_fit 经 MECHANIC 表判)
    shared_chars: list[str] = field(default_factory=list)    # 与其他 comp 共享的 core(转型可复用)
    transition_chars: list[str] = field(default_factory=list)  # 早期打工牌(后期卖)
    typical_form_round: int = 0  # 大致成型所需轮次(level_plan 粗估汇总)
    version_tag: str = "V4.4"    # 版本维护用


@dataclass
class ScoreContext:
    """select_comp / comp_score 的每回合上下文(避免长参数列表)。"""
    bosses: list[str] = field(default_factory=list)              # 当前/将遇 boss 名(boss_fit)
    mechanics: set[str] = field(default_factory=set)             # 激活机制 tag(current_enemy_mechanics)
    env: str = ""                                                # 已选投资环境名(env_fit)
    plane: int = 1
    round_num: int = 1
    gold: int = 0


# ===== 机制表(双向:克 + 利;debuff=buff)=====
# 来源:docs/game/currency_war/data/competitors.md(V4.4 ~50 敌人词缀全集,米游社玩家攻略统计 🟡)+ factions.md(燃血角斗场原文)。
# 机制名跨版本稳;具体词缀属哪个机制随版本变(随 competitors.md 实机 OCR 更新)。
# 只建模"对某类 comp 方向相反"的词缀(策略相关);纯数值怪强化(首领强化等)无 comp 交互,不入表。

MECHANIC_COUNTERS: dict[str, list[str]] = {
    # 机制 tag → 它克制的 comp 机械属性
    "反伤": ["高频低单次"],        # 正当防卫:克高频低单次(反甲白厄式)
    "冻结": ["慢速", "战技点依赖"],  # 极速制冷/坠入陷阱/冷冻冬眠:克慢速 + 战技点消耗队
    "净化": ["DoT", "减益"],       # 净化身心:克 DoT/减益主派(config dot_punish_envs)
    "掉血削上限": ["燃血"],        # 永久创伤:克燃血(掉血→减上限双损)⚠️ 燃血的反例 counter
    "治疗削弱": ["治疗护盾"],      # 重症难题:克治疗/护盾主坦队
    "幸运削弱": ["幸运一击"],      # 丢失幸运:克幸运一击/群攻(知更鸟)
    "属性熄火": ["单属性队"],      # 风/火/冰/雷/物理/量子/虚数熄火:克纯色/单属性队
    "速度抑制": ["速度依赖"],      # 忽快忽慢:克极端高速(昼神阿雅鞋队)
    "装备依赖": ["依赖合成装备"],  # 变宝为废:克依赖合成的装备流
}
MECHANIC_SYNERGIES: dict[str, list[str]] = {
    # 机制 tag → 它受利的 comp 机械属性(用户:debuff=buff)
    "反伤": ["燃血"],             # 正当防卫:反伤让燃血掉血 → 角斗场记录 → 伤害更高(万敌例,debuff=buff 典型)
    "爆发机会": ["爆发速杀"],     # 紧急止血:敌进战受 20% 上限伤 → 利爆发速杀
    "高费审美": ["高费队"],       # 高费审美:4 费及以上 +5%(V4.4)
    "低费审美": ["低费队"],       # 低费审美:3 费及以下 +5%(V4.4)
    "成型羁绊利好": ["成型羁绊队"],  # 形单影只:羁绊全则不受罚(V4.4)
}

# 敌人词缀(OCR 原名)→ 机制 tag 映射(V4.4 competitors.md;未知词缀原样当 tag 透传)
AFFIX_MECHANIC_MAP: dict[str, str] = {
    "正当防卫": "反伤", "反伤": "反伤",
    "极速制冷": "冻结", "急速制冷": "冻结",   # 急速制冷=旧称/笔误变体,兼容
    "坠入陷阱": "冻结", "冷冻冬眠": "冻结",
    "净化身心": "净化",
    "永久创伤": "掉血削上限",
    "重症难题": "治疗削弱",
    "丢失幸运": "幸运削弱",
    "忽快忽慢": "速度抑制",
    "变宝为废": "装备依赖",
    "紧急止血": "爆发机会",
    "高费审美": "高费审美", "低费审美": "低费审美",
    "形单影只": "成型羁绊利好",
    # 属性熄火(7):对应属性我方伤害 1 点(4 次后解除),克纯色队
    "风之熄火": "属性熄火", "火之熄火": "属性熄火", "冰之熄火": "属性熄火",
    "雷之熄火": "属性熄火", "物理熄火": "属性熄火", "量子熄火": "属性熄火", "虚数熄火": "属性熄火",
    # 其余词缀(首领强化/复仇心切/倒计时类等)为纯数值/无 comp 交互,不入表;实机 OCR 按需补
}

# ===== 环境 → 阵营/comp 亲和(P1-2 T0 env 近乎硬绑 + R2-9 env→faction)=====
# ENV_FACTION_MAP 从投资环境注册表派生(单一真相源:概念股/邀请的 faction 字段;改注册表自动传导)
ENV_FACTION_MAP: dict[str, list[str]] = {
    name: [e.faction] for name, e in INVESTMENT_ENVS.items() if e.faction
}
ENV_COMP_AFFINITY: dict[str, dict[str, float]] = {
    # T0 env → {comp_name: 亲和权重} —— 拿到应近乎硬绑该 comp(research §10.3:env 是 run 内最大单一决策)
    "昼之半神概念股": {"昼神阿雅": 1.0},   # 送阿雅+鞋+刷新率 → 近乎硬绑昼神
    # 其余 T0 env 待实玩补
}


# ===== COMP_LIBRARY(起步 roster;V4.4 估值,待实玩校准)=====
# 详 docs/game/currency_war/data/comp_library.md。form_tiers 用 FACTIONS tier 设"成型"里程碑;data 待实玩精确。

COMP_LIBRARY: list[Comp] = [
    Comp(
        name="列车同行", factions=["列车同行"], core_chars=["姬子·启行", "三月七", "花火", "瓦尔特"],
        form_tiers={"列车同行": 4}, strength="S", form_difficulty="easy",
        # V4.4 权威评级(76807134):姬子·启行 = S 级真神;A850 挂机流(76824096):全程自动/不凹开局/适应任何负面环境 → bot 默认首选
        # 成型 8 人口:前台 姬子·启行+花火+瓦尔特+记忆主,后台 三月七+刻律德菈+千冶·刃+符玄/缇宝
        key_equips=["冷笑话引擎", "火力风暴潮", "高周波电锯", "掩体生成枪"],   # 输出装(非反甲;攻略明言"不需要刷反甲")
        boss_weakness=[], mechanic_attributes=["护盾"],   # 三月七护盾+列车光轨反伤;重症难题(护盾削弱)克
        shared_chars=["三月七"], typical_form_round=5,
    ),
    Comp(
        name="巡击青雀", factions=["仙舟", "追击"], core_chars=["青雀", "知更鸟"],
        form_tiers={"仙舟": 5, "追击": 3}, strength="B", form_difficulty="medium",
        # V4.4 评级(76807134):追击 = B 级(纯后期需 9 追击)
        shared_chars=["知更鸟"], typical_form_round=6,
    ),
    Comp(
        name="昼神阿雅", factions=["昼之半神"], core_chars=["阿格莱雅", "风堇", "昔涟"],
        form_tiers={"昼之半神": 4}, strength="B", form_difficulty="hard",
        # V4.4 评级(76807134):阿雅 = B 级(试用难玩;需反重力皮靴×2+速度投资,V3.8 最轮椅→V4.4 降 B)
        key_equips=["反重力皮靴", "反重力皮靴"],   # 2 靴("找鞋战争");光速螺旋桨由 3 昼之半神自动获得,非 find gate
        boss_weakness=["电视机"], mechanic_attributes=["速度依赖"],   # 电视机禁速克速度依赖
        shared_chars=["风堇"], typical_form_round=8,
    ),
    Comp(
        name="击破流萤", factions=["击破"], core_chars=["流萤"],
        form_tiers={"击破": 6}, strength="A", form_difficulty="hard",
        # V4.4 评级(76807134):击破(波提欧)= A 级(V4.4 加强);流萤/波提欧/姬子领队变体
        mechanic_attributes=["击破"], typical_form_round=7,
    ),
    Comp(
        name="贝洛伯格召唤", factions=["贝洛伯格"], core_chars=["布洛妮娅"],
        form_tiers={"贝洛伯格": 4}, strength="A", form_difficulty="medium",
        mechanic_attributes=["召唤"], shared_chars=["布洛妮娅"], typical_form_round=5,
    ),
    Comp(
        name="万敌单C", factions=["夜之半神", "燃血"], core_chars=["万敌", "长夜月"],
        form_tiers={"夜之半神": 4, "燃血": 4}, strength="B", form_difficulty="medium",
        # V4.4 评级(76807134):万敌 = B 级;【debuff=buff 典型】反伤/AoE/持续伤害 利燃血
        mechanic_attributes=["燃血"],
        key_equips=["热血沸腾拳", "高周波电锯", "火力风暴潮"],   # meta(71465721)万敌核心装备
        shared_chars=["风堇", "长夜月"], typical_form_round=6,
    ),
    Comp(
        name="DOT队", factions=["持续伤害", "减益"], core_chars=["卡芙卡", "桑博", "黄泉"],
        form_tiers={"持续伤害": 4, "减益": 4}, strength="B", form_difficulty="easy",
        # V4.4 评级(76807134):dot(持续伤害)= B;减益(黄泉)= A 级(本 comp 含减益,黄泉是减益核心)
        mechanic_attributes=["DoT"], typical_form_round=4,
    ),
    Comp(
        name="反甲白厄", factions=["毁灭"], core_chars=["白厄"],
        form_tiers={"毁灭": 4}, strength="A", form_difficulty="hard",
        key_equips=["以牙还牙甲", "以牙还牙甲", "以牙还牙甲"],   # meta:反甲流需 3 以牙还牙甲
        boss_weakness=["红绿灯", "酒杯怪", "琥珀王", "死龙"],   # meta:怕红绿灯 + 酒杯怪
        mechanic_attributes=["高频低单次"], typical_form_round=7,
        # ⚠️ "毁灭" 不在 FACTIONS(data gap;form_progress 返回 0,待实机 OCR 确认白厄实际羁绊)
    ),
    Comp(
        name="命运圣杯红A", factions=["命运圣杯"], core_chars=["Archer", "远坂凛"],
        form_tiers={"命运圣杯": 3}, strength="S", form_difficulty="medium",
        # V4.4 评级(76807134):Archer(红A)95 = S 级真神;攻略(76924524):高倍率九五核心,加远坂凛+圣杯→+150%攻击+战技点
        # 阵容:Archer(双电锯+风暴潮)+凛+瓦尔特+开拓者·记忆 + 4战技点(花火/刻律)+刃(2减益)+缇宝/符玄/知更鸟
        # ⚠️ core_chars 必须用图鉴规范名(characters.md,OCR/char_id 匹配靠它):"Archer" 非"红A"
        key_equips=["高周波电锯", "高周波电锯", "火力风暴潮"],   # 攻略:"双电锯+风暴潮"(通用 find 装;命运改件由圣杯祈愿自动给,非 find gate)
        mechanic_attributes=["高倍率单核"], typical_form_round=6,
    ),
]


def get_comp(name: str) -> Comp | None:
    """按名取 Comp;无则 None。"""
    for c in COMP_LIBRARY:
        if c.name == name:
            return c
    return None


# ===== 评分 helper(comp 相关)=====

def _owned_chars(state: GameState) -> set[str]:
    """已持有的角色名集合(bench + deployed)。"""
    return {bc.char_id for bc in (*state.bench, *state.deployed) if bc.char_id}


def form_progress(comp: Comp, state: GameState) -> float:
    """成型度 0..1:各核心阵营 tier 进度的均值(min(board,form_tiers)/form_tiers)。

    10 的 helper(comp_viability 先验用);纯阵营 tier,不含角色(避免与 char_quality 三重计分)。
    """
    if not comp.form_tiers:
        return 0.0
    total = 0.0
    n = 0
    for f, tier in comp.form_tiers.items():
        if tier <= 0:
            continue
        total += min(state.board.get(f, 0), tier) / tier
        n += 1
    if n == 0:
        return 0.0
    return clamp(total / n, 0.0, 1.0)


def progress(comp: Comp, state: GameState) -> float:
    """comp_score 用:0.6 阵营 tier 进度 + 0.4 核心角色持有(归一化 0..1)。

    与 form_progress 区别:progress 加了 core_char 持有项(选 target 时评估契合用);
    eval 驱动买牌用 target_progress(只度量剩余进度,去三重,详 cw_decisions 待接)。
    """
    fp = form_progress(comp, state)
    owned = _owned_chars(state)
    core_frac = (sum(1 for c in comp.core_chars if c in owned) / len(comp.core_chars)) if comp.core_chars else 0.0
    return clamp(0.6 * fp + 0.4 * core_frac, 0.0, 1.0)


def equip_fit(comp: Comp, state: GameState) -> float:
    """装备契合度(comp 相关,0..1):持有 comp.key_equips 越多越高(超线性 ^0.7 奖励集齐)。

    ⚠️ comp 驱动(用户):不设通用 equip_score,一切从 target_comp.key_equips 出发。
    key_equips 可含重复(阿雅需 2 反重力皮靴)→ 按 multiplicity 匹配持有数。
    无装备数据(state.equips 空)/ comp 无关键装备 → 中性 0.5(纯靠 form/mechanics 先验)。
    """
    equips = list(getattr(state, 'equips', []) or [])
    if not comp.key_equips or not equips:
        return 0.5
    remaining = list(equips)
    held = 0
    for ke in comp.key_equips:
        if ke in remaining:
            held += 1
            remaining.remove(ke)
    if held == 0:
        return 0.3   # 持有装备但无该 comp 关键件 → 略低(装备不契合)
    return clamp((held / len(comp.key_equips)) ** 0.7, 0.0, 1.0)


def mechanics_fit(comp: Comp, mechanics: set[str]) -> float:
    """机制契合(comp 相关,双向 0..1):命中 counter(克这 comp)→ 降;命中 synergy(利这 comp)→ 升。

    ⚠️ comp 驱动(用户 debuff=buff):同一词缀对不同 comp 方向相反。经 comp.mechanic_attributes
    查全局 MECHANIC_COUNTERS/SYNERGIES 判(数据驱动,comp 不必逐词缀列举)。无机制信息 → 中性 0.5。
    典型:万敌[燃血] + 反伤 → synergy 升(debuff=buff);阿雅[速度依赖] + 禁速 → counter 降。
    """
    if not mechanics or not comp.mechanic_attributes:
        return 0.5
    score = 0.5
    for mech in mechanics:
        countered_attrs = MECHANIC_COUNTERS.get(mech, [])
        synergy_attrs = MECHANIC_SYNERGIES.get(mech, [])
        n_counter = sum(1 for a in comp.mechanic_attributes if a in countered_attrs)
        n_synergy = sum(1 for a in comp.mechanic_attributes if a in synergy_attrs)
        score -= 0.25 * n_counter    # 每命中一个 counter 降 0.25
        score += 0.20 * n_synergy    # 每命中一个 synergy 升 0.20(debuff=buff 利好)
    return clamp(score, 0.0, 1.0)


def boss_fit(comp: Comp, bosses: list[str]) -> float:
    """boss 克制(boss 名维度):命中 comp.boss_weakness → 降。无 boss 信息 → 中性 0.5。"""
    if not bosses or not comp.boss_weakness:
        return 0.5
    n_hit = sum(1 for b in comp.boss_weakness if b in bosses)
    return clamp(0.5 - 0.5 * n_hit, 0.0, 1.0) if n_hit else 0.5


def env_fit(comp: Comp, env: str) -> float:
    """投资环境契合:① T0 env 近乎硬绑(P1-2 ENV_COMP_AFFINITY);② env 加成对应阵营(R2-9)。无 env → 0.5。"""
    if not env:
        return 0.5
    # P1-2: T0 env 近乎硬绑某 comp
    if env in ENV_COMP_AFFINITY:
        affinity = ENV_COMP_AFFINITY[env].get(comp.name, 0.0)
        if affinity > 0:
            return clamp(0.5 + 0.5 * affinity, 0.0, 1.0)
    # R2-9: env 加成对应阵营
    boosted = ENV_FACTION_MAP.get(env, [])
    if boosted and any(f in comp.factions for f in boosted):
        return 1.0
    return 0.5


def strength_base(comp: Comp) -> float:
    """research meta 强度先验:{S:1.0, A:0.7, B:0.4}。"""
    return {"S": 1.0, "A": 0.7, "B": 0.4}.get(comp.strength, 0.5)


def current_enemy_mechanics(state: GameState) -> set[str]:
    """当前敌人机制 tag 集合(从 state.enemy_affixes 经 AFFIX_MECHANIC_MAP 映射;未知词缀原样透传)。"""
    return {AFFIX_MECHANIC_MAP.get(a, a) for a in state.enemy_affixes}


def make_score_context(state: GameState, bosses: list[str] | None = None) -> ScoreContext:
    """从 GameState 快速构造 ScoreContext(常用入口)。bosses 由外部 OCR 传入。"""
    return ScoreContext(
        bosses=bosses or list(state.bosses),
        mechanics=current_enemy_mechanics(state),
        env=state.active_env,
        plane=state.plane, round_num=state.round_num, gold=state.gold,
    )


# ===== comp_score(候选 comp 综合分)=====
# 权重 V4.4 research meta 先验(占位,待实玩校准);归一化 sum=1.0。开发者阶段 6 手调(内部,非用户 GUI)。
W_PROG: float = 0.35    # 成型进度(form + core_char)
W_MECH: float = 0.20    # 机制契合(双向 debuff=buff)
W_ENV: float = 0.15     # 投资环境契合
W_BOSS: float = 0.10    # boss 克制
W_EQUIP: float = 0.10   # 装备契合(comp 相关)
W_STR: float = 0.10     # research meta 强度


def comp_score(comp: Comp, state: GameState, ctx: ScoreContext) -> float:
    """候选 comp 综合分(select_comp 评分 candidate 用;无观测项 —— 未 commit 的 candidate 无观测)。

    多维度 comp 相关(用户:一切挂钩目标阵容):成型进度 + 机制双向 + 环境 + boss + 装备 + 强度。
    评 **current 已 commit** comp 用 cw_performance.comp_viability(加观测 blend),不用本函数。
    """
    return (
        W_PROG * progress(comp, state)
        + W_MECH * mechanics_fit(comp, ctx.mechanics)
        + W_ENV * env_fit(comp, ctx.env)
        + W_BOSS * boss_fit(comp, ctx.bosses)
        + W_EQUIP * equip_fit(comp, state)
        + W_STR * strength_base(comp)
    )


# 用户 4 轴 steer(README A):优先/禁止/build_around。阶段 2 用 getattr 防御读取(config 字段待加)。

def _passes_steering(comp: Comp, config) -> bool:
    """用户 steer 硬过滤:build_around 必含、forbid 必不含。不满足 → 排除出候选。"""
    build_around = getattr(config, 'character_build_around', []) or []
    if build_around and not any(c in comp.core_chars for c in build_around):
        return False
    char_forbid = getattr(config, 'character_forbid', []) or []
    if any(c in comp.core_chars for c in char_forbid):
        return False
    faction_forbid = getattr(config, 'faction_forbid', []) or []
    return not any(f in comp.factions for f in faction_forbid)


def _priority_boost(comp: Comp, config) -> float:
    """用户 steer 软加权:命中 priority 角色/阵营 → 加分(tiebreak 偏向用户偏好)。"""
    boost = 0.0
    char_pri = getattr(config, 'character_priority', []) or []
    for c in comp.core_chars:
        if c in char_pri:
            boost += 0.05 * (len(char_pri) - char_pri.index(c)) / max(len(char_pri), 1)
    faction_pri = getattr(config, 'faction_priority', []) or []
    for f in comp.factions:
        if f in faction_pri:
            boost += 0.05 * (len(faction_pri) - faction_pri.index(f)) / max(len(faction_pri), 1)
    return boost


def _difficulty_phase_factor(comp: Comp, state: GameState) -> float:
    """阶段感知成型难度因子(用户:成型难度是关键维度):早期/穷 → 偏 easy 成型。"""
    early = state.round_num <= 3 or state.gold < 30
    if not early:
        return 1.0
    return {"easy": 1.15, "medium": 1.0, "hard": 0.85}.get(comp.form_difficulty, 1.0)


def select_comp(state: GameState, ctx: ScoreContext, config,
                top_n: int = 1) -> list[Comp]:
    """按 comp_score 选 target(分数降序,返回 top_n)。

    评分 = comp_score(多维)+ 用户 4 轴 steer(硬过滤 build_around/forbid + 软加权 priority)
    + 阶段成型难度因子(早期偏 easy)。optionality 时传 top_n=2-3 备选几套(P1-1:核心来了再 commit)。
    """
    scored: list[tuple[float, Comp]] = []
    for comp in COMP_LIBRARY:
        if not _passes_steering(comp, config):
            continue
        s = comp_score(comp, state, ctx) + _priority_boost(comp, config)
        s *= _difficulty_phase_factor(comp, state)
        scored.append((s, comp))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [c for _s, c in scored[:top_n]]


def comp_score_breakdown(comp: Comp, state: GameState, ctx: ScoreContext) -> dict[str, float]:
    """comp_score 的特征分解(telemetry 采集用:给人肉眼复盘 + 未来 ML side door)。

    schema 稳定(字段名跨版本不变);数值随版本/实玩变。详 cw_telemetry。
    """
    return {
        "progress": progress(comp, state),
        "mechanics_fit": mechanics_fit(comp, ctx.mechanics),
        "env_fit": env_fit(comp, ctx.env),
        "boss_fit": boss_fit(comp, ctx.bosses),
        "equip_fit": equip_fit(comp, state),
        "strength": strength_base(comp),
        "form_progress": form_progress(comp, state),
    }


# ===== 转型(pivot)+ 巨星(select_megastar)=====

def maybe_pivot(state: GameState, ctx: ScoreContext, config, target: Comp | None,
                tracker: PerformanceTracker | None = None) -> Comp | None:
    """是否转型到新 target(返回新 Comp 或 None 不转)。

    转型信号(比较型,03 正确性-4):
    1. 更优 comp 涌现:存在 B 使 comp_score(B) 持续 > target + 阈值(本回合单次比较;跨回合连续性待接)。
    2. ceiling 不可达:target.typical_form_round > 剩余轮次估算。
    3. 保命转型:hp < 30 → 切成型最快的 comp(低 typical_form_round)。

    ⚠️ 阶段 2 启发式:转型成本用规则估算,不用多步搜索(03 正确性-5)。tracker 用于保命判断的观测。
    """
    PIVOT_SCORE_GAP: float = 0.10   # 更优涌现阈值(占位,待实玩校准)
    candidates = select_comp(state, ctx, config, top_n=len(COMP_LIBRARY))
    if not candidates:
        return None
    best = candidates[0]
    # 信号 1:更优涌现
    if target is None or best.name != target.name:
        target_score = comp_score(target, state, ctx) if target is not None else 0.0
        if comp_score(best, state, ctx) > target_score + PIVOT_SCORE_GAP:
            return best
    # 信号 2:ceiling 不可达(target 成型轮次 > 剩余轮次)
    if target is not None and target.typical_form_round > 0:
        # 位面内剩余轮次粗估(每位面 6 轮,3 位面 = 18 轮;已过 round_num + (plane-1)*6)
        elapsed = state.round_num + (state.plane - 1) * 6
        remaining = max(18 - elapsed, 0)
        if target.typical_form_round > remaining:
            # 切成型最快的(easy 优先)
            easy = [c for c in candidates if c.form_difficulty == "easy"] or candidates
            return min(easy, key=lambda c: c.typical_form_round or 99)
    # 信号 3:保命转型
    if state.hp < 30:
        easy = [c for c in candidates if c.form_difficulty == "easy"] or candidates
        fastest = min(easy, key=lambda c: c.typical_form_round or 99)
        if target is None or fastest.name != target.name:
            return fastest
    return None


# 盛会之星巨星 buff 表(米游社 factions.md 原文;select_megastar 按 target_comp 选,不单独评分)
MEGASTAR_BUFF: dict[str, str] = {
    # 巨星角色 → 适合的 comp 机械属性(粗估,实玩校准)
    "知更鸟": "幸运一击", "花火": "战技点", "星期日": "前后台强度",
    "黑天鹅": "5费增伤", "大丽花": "击破",
}
MEGASTAR_BY_ATTRIBUTE: dict[str, str] = {
    # comp 机械属性 → 推荐巨星(反向;粗估)
    "幸运一击": "知更鸟", "击破": "大丽花", "5费增伤": "黑天鹅",
}


def select_megastar(state: GameState, target: Comp | None,
                    available_megastars: list[str]) -> str | None:
    """选 1 名盛会之星作巨星(盛会之星羁绊核心决策;按 target_comp 选,不单独评分)。

    - 若 target.core_chars 含盛会之星且在可选里 → 绑该角色(如「知更鸟 comp」→ 知更鸟)。
    - 否则按 buff 契合 target.mechanic_attributes 推。
    - 无 target / 无可选 → None(退回 naive 默认,调用方处理)。
    """
    if not available_megastars:
        return None
    if target is not None:
        for c in target.core_chars:
            if c in available_megastars:
                return c
        for attr in target.mechanic_attributes:
            star = MEGASTAR_BY_ATTRIBUTE.get(attr)
            if star and star in available_megastars:
                return star
    return available_megastars[0]
