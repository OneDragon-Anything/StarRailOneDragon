"""货币战争 事件节点决策:投资策略/环境 3 选 1(decide_event;ADR-0143/0144 pick_value)+ 遭遇(decide_encounter)+ 补给(decide_supply)+ 巨星/伙伴选项类型。

自 cw_decisions.py 一次性拆分而来(ADR-0145;纯移动零行为变化,函数名/签名不变)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sr_od.application.currency_war.cw_comps import (
    AFFIX_MECHANIC_MAP,
    AUGMENT_COMP_AFFINITY,
    MECHANIC_COUNTERS,
    form_progress,
    mechanics_fit,
)
from sr_od.application.currency_war.cw_investments import (
    ENV_FACTION_MATCH_FLOOR,
    ENV_SURVIVAL_BONUS,
    EQUIP_FLOW_PICKS,
    INVESTMENT_STRATEGIES,
    SURVIVAL_PICKS,
    EconomyEffect,
    get_env,
    get_strategy,
    pick_value_of,
    strategy_bindings,
)
from sr_od.application.currency_war.cw_state import (
    GameState,
    PickEvent,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.cw_comps import Comp

# 注册表名列表缓存(ADR-0141 _option_rarity LCS 兜底用;模块级避免每选项重建)
INVESTMENT_STRATEGIES_KEYS: list[str] = list(INVESTMENT_STRATEGIES)



# ===== 事件 =====
# decide_boss_priority(阵营降权)已删(2026-08-12):boss 克制是 comp-vs-boss 机制级(走 boss_fit/
# comp.countered_by_bosses + task#73 机制建模),非阵营级。原 faction 降权是错模型 + 从不派发的死代码。

def _option_rarity(opt: str) -> str:
    """投资策略选项的品质(ADR-0141 复查 #6):注册表精确查 → LCS 相似兜底(ADR-0138 通道);未知返 ''。

    品质→敌难度(核心机制 38-40):金 +3 / 棱彩 +6 —— 高品质 = 高风险高回报,难度惩罚项的输入。
    """
    s = get_strategy(opt)
    if s is not None:
        return s.rarity
    from one_dragon.utils.str_utils import find_best_match_by_lcs
    names = list(INVESTMENT_STRATEGIES_KEYS) if INVESTMENT_STRATEGIES_KEYS else []
    idx = find_best_match_by_lcs(opt, names, lcs_percent_threshold=0.6)
    return INVESTMENT_STRATEGIES[names[idx]].rarity if idx is not None else ''


# 「克 DoT/减益」的机制属性集合(与 MECHANIC_COUNTERS 值域对齐;ADR-0203)
_DOT_PUNISHED_MECHS: frozenset[str] = frozenset({'DoT', '减益'})


def _opt_counters_dot(opt: str) -> bool:
    """选项(词缀/环境名)是否克制 DoT/减益主派 —— 机制注册表单一源(ADR-0203)。

    名 → ``AFFIX_MECHANIC_MAP`` 机制 tag → ``MECHANIC_COUNTERS`` 克制属性,与「净化身心」
    同类的任意 anti-DoT 词缀/环境都覆盖(不止单点名);子串包含匹配保留旧 OCR 容错语义
    (旧 config dot_punish_envs 名单已删 —— 游戏客观数据非用户偏好,版本全量一致)。
    未知名(不在映射)→ False(不惩罚)。
    """
    for affix, tag in AFFIX_MECHANIC_MAP.items():
        if affix in opt and not _DOT_PUNISHED_MECHS.isdisjoint(MECHANIC_COUNTERS.get(tag, ())):
            return True
    return False



# 建议刷新的分数下限(ADR-0146:低于此 = 烂手牌,免费刷新期望为正;tuning 候选)
EVENT_REFRESH_SCORE_FLOOR: float = 50.0

# 用户转向轴(投资策略/环境;develop config.md §3):priority 软加分 + forbid 重罚。
STEERING_PRIORITY_BONUS: float = 30.0     # soft:倾向选,可被 comp-hit(65-110)/增强定义(120)压过
STEERING_FORBID_PENALTY: float = 10000.0  # hard−:有替代永不选;全被禁 → 分数落刷新阈值下自然建议刷新


def decide_event(options: list[str], config, state: GameState,
                  target_comp=None) -> PickEvent:
    """事件选项打分(投资策略/环境 3 选 1)。

    分值来源优先级表(每项只在**高于当前分**时覆盖;ADR-0143/0144/0144b 后的完整语义):
    1. comp 命中(45×N+20,双命中 110):选项绑定∩target_comp(策略侧;成型加速压倒一切)
    2. 策略评估分 pick_value(12-75,ADR-0143;替裸品质先验,「分数为纲」)
       / 品质先验回落(50/30/10+economy20,仅未评估卡)
    3. eval-lcs(策略 OCR 形变裸分;**env 名跳过**——0144b 守卫,83 env 名 29 个 LCS 误中策略名)
    4. env 分支(_st is None 且 env 命中):env 裸分(28-72)/ 阵营 floor(概念股 78/邀请 70/契约 72)
       / HP 钩子(+15/+10);**env 无品质不吃难度惩罚**(0144b)
    叠加项(全部之后):品质难度惩罚(-12/-6,HP<40 加倍;仅策略)/ 机制克制惩罚(-100 档,
    MECHANIC_COUNTERS 单一源,ADR-0203)/ 用户转向轴(策略/环境 priority +30 soft、forbid −10000
    hard−,config.md §3)/ 生存钩子(+15,仅策略 SURVIVAL_PICKS)。未注册非 env = 0 分。
    (原 config event_whitelist 恒最高 boost 已删,ADR-0204:priority/forbid 覆盖用户语义,
    「指定具体分值」是引擎调参非用户偏好。)
    """
    strategy_priority = list(getattr(config, 'strategy_priority', []) or [])
    strategy_forbid = list(getattr(config, 'strategy_forbid', []) or [])
    env_priority = list(getattr(config, 'env_priority', []) or [])
    env_forbid = list(getattr(config, 'env_forbid', []) or [])
    on_dot = sum(state.board.get(f, 0) for f in ('持续伤害', '减益')) >= 2
    penalty = 100
    _rarity_prior: dict[str, float] = {'棱彩': 50.0, '金': 30.0, '银': 10.0}
    _tgt_factions: set[str] = set(target_comp.factions) if target_comp is not None else set()
    _tgt_chars: set[str] = set(target_comp.core_chars) if target_comp is not None else set()

    best_idx, best_score = 0, -1.0
    best_reason = ''
    for i, opt in enumerate(options):
        score = 0.0
        reason = 'eval'
        _st = get_strategy(opt)
        _env = get_env(opt)   # 提前查 env 表(防跨表污染,见下 eval-lcs/惩罚两处守卫)
        _pv = None if _env is not None else pick_value_of(opt)
        # ↑ ADR-0144b 跨表污染守卫:83 env 名中 29 个会 LCS 误中策略名(全量扫描实测:列车同行概念股→
        # 列车同行星徽28/增发货币→超发货币55 等)——env 名走 env 分支评分,不进策略 LCS 兜底。
        # ADR-0152(评审🔴3a)augment 定义型 comp:黑塔纪元/飞光等拿到即改写本局玩法(216 张黑塔
        # 入商店/师徒变身)—— 评分压过一切常规项(仅低于用户白名单;M1 资源入口:拿到 = 换打法)。
        if opt in AUGMENT_COMP_AFFINITY:
            score = max(score, 120.0)
            reason = 'augment-defining'
        _comp_hit = 0
        if _st is not None:
            _fs, _cs = strategy_bindings(_st)
            _comp_hit = len((_fs & _tgt_factions) | (_cs & _tgt_chars))
            if _comp_hit:
                score = max(score, 45.0 * _comp_hit + 20.0)
                reason = f'comp-hit×{_comp_hit}'
            # ADR-0143:评估基准分替裸品质先验 —— 同品质内有先后(鲜血阶梯75 vs 数值碾压35)。
            # 评估分已含经济价值 → economy +20 只在回落路径加(防双计)。
            if _pv is not None:
                _prior = float(_pv)
            else:
                _prior = _rarity_prior.get(_st.rarity, 0.0)
                if _st.economy is not None and _st.economy != EconomyEffect():
                    _prior += 20.0
            if _prior > score:
                score, reason = _prior, ('eval' if _pv is not None else f'prior-{_st.rarity}')
        elif _pv is not None and float(_pv) > score:
            # 精确名 miss 但 LCS 命中评估表(OCR 形变)→ 裸评估分(comp/economy 修饰不可靠)
            score, reason = float(_pv), 'eval-lcs'
        # ADR-0144(环境侧评估分):env 名不在策略注册表(原恒 0 分 → fallback 恒选第一张);
        # 基准分 + 阵营定向条件分(概念股/邀请/契约 faction ∩ target_comp)+ HP 钩子。
        # OCR 形变的 env 名(如 尾彩•变体)不进策略 LCS(上方 _env 精确查 miss 时仍可能污染 ——
        # 但 OCR 只出现在 handler 层归一名后才进决策,形变 env 名实际不达此处;守卫以精确查为准)。
        if _st is None and _env is not None:
            if _env.pick_value > 0 and float(_env.pick_value) > score:
                score, reason = float(_env.pick_value), 'env-eval'
            if _env.faction and _env.faction in _tgt_factions:
                _floor = ENV_FACTION_MATCH_FLOOR.get(_env.category, 70.0)
                if _floor > score:
                    score, reason = _floor, f'env-faction:{_env.faction}'
            if state.hp < 40:
                score += ENV_SURVIVAL_BONUS.get(_env.name, 0.0)
        # 用户转向轴(develop config.md §3):投资策略/环境 priority 软加分 + forbid 重罚。
        # 选项归属:env 注册表命中走 env 轴,其余(策略/未注册)走 strategy 轴 —— env 名经 handler
        # 归一后才进决策(ADR-0144b),未注册项按事件主流(投资策略)处理。子串匹配与白名单一致(OCR 容错)。
        _pri = env_priority if _env is not None else strategy_priority
        if any(p in opt for p in _pri):
            score += STEERING_PRIORITY_BONUS
            reason = 'user-priority'
        _forbid = env_forbid if _env is not None else strategy_forbid
        if any(p in opt for p in _forbid):
            score -= STEERING_FORBID_PENALTY
            reason = 'user-forbid'
        # ADR-0143 HP 分档:低血(<40)生存类 +15(评估表 notes 钩子:恢复/免战/降难度)
        if state.hp < 40 and _st is not None and _st.name in SURVIVAL_PICKS:
            score += 15.0
        # r255(P2 断崖装备缺失):P2 期装备流策略 +25——
        # 11 局实锤 P2 板面 equips 全空(裸件打仗,首战
        # -14~-41);军火类(每节点刷装备)是 P2 生存关键
        # 通道,P1 期不加(P1 板面成型优先)。
        if (state.plane >= 2 and _st is not None
                and _st.name in EQUIP_FLOW_PICKS):
            score += 25.0
        # ADR-0141(复查 #6):品质→敌难度(核心机制 38-40:金+3/棱彩+6)—— 高品质策略提升敌人难度,
        # A8 高难下难度膨胀追不平强度 → 按当前难度动态惩罚:棱彩 -12 / 金 -6(Hp 危险时加倍;难度可从
        # state.enemy_difficulty 读但选卡时常空,用 A8 常态先验)。银/未知不罚。
        # env 无品质分级(图鉴亦无,ADR-0144 评估实证)→ 不吃品质难度惩罚(否则 _option_rarity
        # 的 LCS 兜底会让 env 名误中策略品质,列车同行概念股→列车同行星徽棱彩→-12 污染)。
        _rar = _st.rarity if _st is not None else ('' if _env is not None else _option_rarity(opt))
        if _rar == '棱彩':
            score -= 12.0 if state.hp >= 40 else 24.0
        elif _rar == '金':
            score -= 6.0 if state.hp >= 40 else 12.0
        if on_dot and _opt_counters_dot(opt):
            score -= penalty
        if score > best_score:
            best_score, best_idx, best_reason = score, i, reason
    # ADR-0146(缺口1):三张最优 < 阈值 → 建议刷新(免费次数;handler 读「刷新次数N」决定真刷否)。
    # 阈值 50 ≈ 评估分中位(12-75;白名单 78+/comp-hit 65+ 天然不触发)—— 烂手牌换新期望。
    _want_refresh = best_score < EVENT_REFRESH_SCORE_FLOOR
    return PickEvent(option_idx=best_idx, refresh=_want_refresh,
                     reason=f"{best_reason} score={best_score:.0f}" + ("|suggest-refresh" if _want_refresh else ""))


# ===== 遭遇节点(decide_encounter,design 08;✅ 已接 HandleEncounter:55 + read_encounter_options)=====

@dataclass

class EncounterOption:
    """一个遭遇分支:难度档 + 敌人词缀 + 奖励(OCR 读,``read_encounter_options`` 阶段5)。

    difficulty:难度档 1=易/2=中/3=难(越高奖励越好但敌人越凶)。
    affixes:敌人词缀 OCR 原名(经 ``AFFIX_MECHANIC_MAP`` → 机制 tag,再 ``mechanics_fit`` 判 comp 克/利)。
    rewards:奖励(钻/装备/金币;带钻最优,详 design 08 / cw_comps MECHANIC 表)。
    """
    idx: int
    difficulty: int = 1
    affixes: list[str] = field(default_factory=list)
    rewards: list[str] = field(default_factory=list)


@dataclass

class EncounterPick:
    """decide_encounter 返回:选哪个分支 + 是否刷新避开。"""
    idx: int
    refresh: bool = False
    reason: str = ""



def _option_mechanics(option: EncounterOption, target_comp: Comp | None) -> float:
    """该分支词缀对 target_comp 的契合(``mechanics_fit`` 0..1;<0.4 克、>0.5 利 debuff=buff)。

    无 target_comp / 无词缀信号(mechanics_fit 返 None,ADR-0107)→ 中性 0.5(纯按难度选,不触发刷新)。
    """
    if target_comp is None:
        return 0.5
    mechs = {AFFIX_MECHANIC_MAP.get(a, a) for a in option.affixes}
    fit = mechanics_fit(target_comp, mechs)
    return fit if fit is not None else 0.5


def _reward_value(rewards: list[str]) -> float:
    """奖励文本 → 价值分 0..1(2026-08-17 用户指路「看奖励」接进选档)。

    OCR 奖励带已读(read_encounter_options rewards);文本启发:
    - 棱彩/金装备类关键词 > 银类 > 无文本(OCR 漏/无奖励带);
    - 经验/金币给基础分(量小);
    - 无奖励文本 → 0.5 中性(不因 OCR 漏惩罚该档)。
    实玩校准点;先验表在代码单一源。
    """
    if not rewards:
        return 0.5
    text = ''.join(rewards)
    if any(k in text for k in ('棱彩', '特权')):
        return 1.0
    if any(k in text for k in ('进阶', '黄金', '宝钻')):
        return 0.8
    if any(k in text for k in ('简易', '白银', '银')):
        return 0.65
    if any(k in text for k in ('经验', '金币', '装备')):
        return 0.6
    return 0.5


# 敌方血量随难度缩放:base × 1.052^d(🟡 米游社拟合,competitors.md;19 号 D≥E 不等式地基)。
# 遭遇选档用:档差 → 血量比 → 相对斩杀压力。
_ENEMY_HP_GROWTH: float = 1.052


def _difficulty_hp_ratio(tier_delta: int) -> float:
    """档位差 → 敌方血量比(d 高 2 档 ≈ ×1.107 血)。"""
    return _ENEMY_HP_GROWTH ** tier_delta



def decide_encounter(options: list[EncounterOption], state: GameState,
                     target_comp: Comp | None, config, refresh_used: bool = False) -> EncounterPick:
    """遭遇节点选难度档 + 是否刷新(纯逻辑,design 08)。✅ 已接:``HandleEncounter``(L55 调本函数)+
    ``read_encounter_options``(cw_node_obs,OCR 卡标题「遭遇其X」→ difficulty)。affix 分支 N/A
    (选项 UI 不显词缀,战后才显)。原 docstring「handler 待阶段5 接」过期(2026-08-12 代码核实已接)。

    决策(观测驱动 + comp 相关,debuff=buff):
    1. **未成型**(deployed 不足 / target 成型度低)→ 偏低难度(生存优先)。
    2. **词缀按 comp 判**(``mechanics_fit``):全分支都克 comp + 刷新未用 → **刷新换批**避开;
       存在不克的分支 → 选最利 comp 的。
    3. **成型 + 词缀利 comp**(debuff=buff)→ 挑高难度拿奖励(奖励权重随成型度)。
    4. 刷新已用 → 不再刷,按 1-3 选最优分支。

    config 预留(未来对策装备映射 / 偏好;当前未用)。
    """
    if not options:
        return EncounterPick(idx=0, reason="no-options")
    mechs = [_option_mechanics(o, target_comp) for o in options]
    form = form_progress(target_comp, state) if target_comp is not None else 0.5
    formed = form >= 0.4 and state.deployed_count() >= max(2, state.max_units() // 2)

    # 全分支词缀都克 comp(mechanics_fit < 0.4)+ 刷新未用 → 刷新换批(避开高危)
    if not refresh_used and target_comp is not None and all(m < 0.4 for m in mechs):
        return EncounterPick(idx=options[0].idx, refresh=True,
                             reason=f"全分支词缀克 comp(mech_max={max(mechs):.2f}),刷新换批")

    # 评分:词缀契合(利 comp 加分)+ 难度档定价(P9 接 36 号账本:场合三态替代固定 ±0.3)
    def _score(o: EncounterOption, m: float) -> float:
        from sr_od.application.currency_war.cw_survey19_hooks import (
            encounter_tier_score,
        )
        s = m
        # 0..1 clamp(难度 1→0、3→1;「其四」=4 越界 1.5 → 钳回,ADR-0130)
        diff_norm = min(max((o.difficulty - 1) / 2.0, 0.0), 1.0)
        # 奖励价值(2026-08-17 用户指路;OCR 奖励带已读)——与难度联动:
        # 只有「敢难」时奖励差才兑现,不敢难时好奖励也白搭(不独立加分)
        rv = _reward_value(o.rewards)
        if state.plane == 3:
            # ADR-0130(复查 #3):P3 永避高难遭遇(一次 -70 血无回报,成型也不赌)。
            s -= 0.5 * diff_norm
            s -= 0.1 * (1.0 - rv)   # P3 不为奖励冒险,仅轻微 tiebreak
        else:
            # P9(用户口径「阵容足够强才敢难」):压 −2 档价值作风险计——
            # 碾压(form≥0.9,gap≤−36,bell→0)敢难白拿;其余保守保血。
            gap = (0.4 - form) * 60
            press_v = encounter_tier_score(d_now=100.0, tier_delta=-2,
                                           gap=gap, plane=state.plane)
            dare = press_v < 0.05
            s += (0.3 + 0.2 * (rv - 0.5)) * diff_norm if dare else -0.3 * diff_norm
        return s

    scored = sorted(zip(options, mechs, strict=True), key=lambda om: _score(om[0], om[1]), reverse=True)
    best_o, best_m = scored[0]
    return EncounterPick(idx=best_o.idx, refresh=False,
                          reason=(f"mech={best_m:.2f} formed={formed} diff={best_o.difficulty} "
                                  f"reward={_reward_value(best_o.rewards):.2f}"))



# ===== 补给节点(decide_supply,design 07/08;✅ 已接 run_supply_node:56 + read_supply_options)=====

# 通用装备价值(V4.4 meta 先验;**值在代码单一源,不进 strategy doc**;实玩校准)。
# 设计原则:带钻 > 鞋(找鞋战争;速度 comp 命脉)> 电池 > 花/通用。具体值随版本。
# ADR-0298(批㉛ F2 数据债清偿):键必须 ⊆ EQUIPMENT_ROSTER(注册表单一源)——
# 旧表 3 死名已核游戏语料裁决为表残留删除(超级电池=超充站 buff 词非装备/
# 能量饮料=全语料零出现/翁瓦克=局外遗器名被 ADR-0130 误收);翁瓦克 4 分
# 按功能对位转投蓄能帆(行动值回能,同为充能系;0 分→4 分)。
_EQUIP_VALUE: dict[str, int] = {
    "反重力皮靴": 5, "轮滑鞋": 4,
    "永动机": 4, "光能电池": 3,
    "物质分解液": 3, "绝对热量": 2, "蓄能帆": 4,
    # ADR-0130(复查 #7,各阵容装备段 + 核心机制:56):核心输出装补缺 —— 旧表缺失 = 全 0 分 →
    # 补给/装备决策系统性低估 core 装备(火力风暴潮 = 伤害征服核心乘区,最高优先)。
    # (ADR-0298:本行原含「翁瓦克」= 局外遗器死名,已删,见表头注释。)
    "火力风暴潮": 6, "高周波电锯": 5, "冷笑话引擎": 4,
}


@dataclass

class SupplyOption:
    """一个补给选项:角色 + 装备 + 是否带钻(OCR/视觉读,``read_supply_options`` 阶段5)。

    has_diamond:带红/蓝钻(视觉判定;钻 = 拿到基本赢,碾压一切)。
    equip:装备名(OCR;``key_equips`` 契合 + 通用价值排序用)。
    """
    idx: int
    char: str = ""
    equip: str = ""
    has_diamond: bool = False


@dataclass

class SupplyPick:
    """decide_supply 返回:选哪个 + 是否刷新找钻。"""
    idx: int
    refresh: bool = False
    reason: str = ""



def _equip_value(equip: str) -> int:
    """装备通用价值(0=未知/无;V4.4 先验,见 ``_EQUIP_VALUE``)。"""
    return _EQUIP_VALUE.get(equip, 0)



def decide_supply(options: list[SupplyOption], state: GameState,
                  target_comp: Comp | None, config, refresh_used: bool = False) -> SupplyPick:
    """补给节点选装备 + 是否刷新(纯逻辑,design 07/08)。✅ 已接:``run_supply_node``:56 调本函数 +
    ``read_supply_options``(cw_node_obs,OCR 每列角色+装备)。原「handler 待阶段5 接」过期(2026-08-12 核实)。

    决策(comp 相关 + 钻优先):
    1. **带钻**(红/蓝)→ 选它(拿到基本赢,碾压)。
    2. **全无钻 + 刷新未用** → **刷新找钻**(钻价值远超装备)。
    3. **刷新已用 / 有钻** → 按 ``target_comp.key_equips`` 契合(命脉级,+10 碾压)+ 通用装备价值
       (鞋>电池>花)选。
    """
    if not options:
        return SupplyPick(idx=0, reason="no-options")
    # 1) 带钻 → 选第一个带钻的(基本赢)
    diamond = [o for o in options if o.has_diamond]
    if diamond:
        return SupplyPick(idx=diamond[0].idx, reason="带钻(基本赢)")
    # 2) 全无钻 + 刷新未用 → 刷新找钻
    if not refresh_used:
        return SupplyPick(idx=options[0].idx, refresh=True, reason="无钻,刷新找钻")
    # 3) 刷新已用 → key_equips 契合(命脉,+10)+ 通用装备价值
    key_equips = set(target_comp.key_equips) if target_comp is not None else set()

    def _score(o: SupplyOption) -> int:
        s = _equip_value(o.equip)
        if o.equip in key_equips:
            s += 10   # 契合 target_comp 命脉装备(碾压通用价值)
        return s

    scored = sorted(options, key=_score, reverse=True)
    best = scored[0]
    return SupplyPick(idx=best.idx, reason=f"equip={best.equip or '?'} key_fit={best.equip in key_equips}")


# ===== 巨星节点(decide_megastar;✅ 已派发 run_megastar_node:75,按 target.core_chars 选;⚠️ 候选 char_id OCR 限时 fallback idx0)=====

@dataclass

class MegastarOption:
    """一个巨星候选(OCR/SIFT 读角色名,``read_megastar`` 阶段5;/§11.3.4⑥)。

    char_id:候选角色名(空 = OCR 未就绪,匹配恒失败 → 默认 idx=0 = 今天盲点左候选)。
    """
    idx: int
    char_id: str = ""


@dataclass

class MegastarPick:
    """decide_megastar 返回:选第几个候选 + 原因。"""
    idx: int
    reason: str = ""


# ===== 选择伙伴节点(decide_partner;✅ 已派发 handle_select_partner:96,T#99;⚠️ 候选只立绘 char_id=label→多 idx0,真接需 SIFT 立绘)=====

@dataclass

class PartnerOption:
    """一个伙伴候选(OCR/SIFT 读角色名,``read_partner`` 阶段5;/§11.3.4⑦)。

    char_id:候选角色名(空 = OCR 未就绪 → 默认 idx=0 = 今天盲点 stage 立绘)。
    """
    idx: int
    char_id: str = ""


@dataclass

class PartnerPick:
    """decide_partner 返回:选第几个候选 + 原因。"""
    idx: int
    reason: str = ""


# ===== 银狼策划事件(decide_planner;r104 用户定调「接入策略模块,由策略模块定」;
#      机制见 docs/game/gameplay/currency_war.md 银狼策划事件节)=====

@dataclass
class PlannerOption:
    """一个策划选项(OCR 卡文字)。

    text:卡描述全文(如「提升费用至4费,变为1星银狼LV.999」/「使后续节点【弱化】…」/
    装备名+效果)。「提升费用」字样判升费卡由本模块打分表达,handler 不写死。
    """
    idx: int
    text: str = ''


@dataclass
class PlannerPick:
    """decide_planner 返回:选第几张卡 + 原因。"""
    idx: int
    reason: str = ''


def decide_planner(options: list[PlannerOption], state: GameState,
                   target_comp: Comp | None = None) -> PlannerPick:
    """银狼「我来当策划」二选一策略(r104)。

    用户定调(2026-08-20):**必接策略模块由它定**(handler 不写死默认),虽结论
    几乎总是升费——打分走通用原则,让「何时升费不是最优」可被策略表达:

    - **升费卡**(「提升费用」):银狼成长滚动投资前提(升费→新费档刷商店→3星5费
      滚强度)。基础 100;target 银狼线(狼尊欢愉/量子系)再 +30;**例外降权**:
      target 不含银狼线且银狼确定不在场(board 有信息但无银狼)→ -60(投资无处兑现)。
    - **弱化类**(「弱化」/「降低敌人」):全场即时战力,基础 55;HP<40 +20。
    - **装备类**(其余):_equip_value 回落(装备注册表);target key_equip 命中 +15。
    - 未识别文字:0 分(idx 顺序兜底)。
    """
    _tgt_chars = set(target_comp.core_chars) if target_comp is not None else set()
    _tgt_factions = set(target_comp.factions) if target_comp is not None else set()
    has_wolf_line = bool(_tgt_chars & {'银狼LV.999'}) or bool(
        _tgt_factions & {'欢愉', '量子同频'})
    # 在场判定:bench+deployed 的 char_id(信息缺失=空列表→不降权,保守)
    _pool = list(getattr(state, 'deployed', None) or []) + \
        [b for b in (state.bench or []) if b is not None]
    _owned = {getattr(bc, 'char_id', '') for bc in _pool
              if getattr(bc, 'char_id', '')}
    wolf_owned = ('银狼LV.999' in _owned) if _owned else True

    best_idx, best_score, best_reason = 0, -1.0, ''
    for opt in options:
        score, reason = 0.0, ''
        t = opt.text
        if '提升费用' in t:
            score, reason = 100.0, '升费(滚动投资前提)'
            if has_wolf_line:
                score += 30.0
                reason += '+银狼线'
            elif not wolf_owned:
                score -= 60.0
                reason += '-银狼不在场无处兑现'
        elif '弱化' in t or '降低敌人' in t:
            score, reason = 55.0, '全场弱化(即时战力)'
            if state.hp < 40:
                score += 20.0
                reason += '+低血保命'
        else:
            score = float(_equip_value(t)) if t else 0.0
            reason = f'装备({t[:8]})' if t else '未识别'
            if t and target_comp is not None:
                _ke = getattr(target_comp, 'key_equips', None) or []
                if any(e in t for e in _ke):
                    score += 15.0
                    reason += '+key_equip'
        if score > best_score:
            best_idx, best_score, best_reason = opt.idx, score, reason
    return PlannerPick(idx=best_idx, reason=best_reason or '全部未识别,兜底左卡')
