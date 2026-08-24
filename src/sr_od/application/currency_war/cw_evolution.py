"""货币战争 阵容演进引擎(契约包 C3,步 4 第一批;2026-08-25 W33)。

**单一源**:`.debug/temp/currency_war/cw_dev/deep_read/转型讨论.md`(演进法则:
替换三条件/统一入口四步/两步解耦/空位规则/中断恢复)+ `strategy_v4.md` 点6/点11。
本模块是「任何时刻、任何档位规模的阵容替换通用法则」的决策侧实现——
过渡 1 档换终局 2 档、插件档换副羁绊档、插件换单卡,全部同构走同一入口。

统一入口四步(冻结:任何阵容改进步动走这里):
``propose_upgrades``(枚举可上新羁绊机会)→ ``evaluate_upgrade``
(①效果判断/②核心校验/③人口检查)→ ``execute_replacement``(④-1 整档替换
CompTransaction,决策在执行前一次敲定)→ ``fill_gap_after``(④-2 数人口缺口,
按空位规则填位:插件优先/替班核心例外/真核心 bench 等档)。

执行载体 = W26 动作集 v2(``CompTransaction``/``FillSpec``,cw_state 单一源);
本模块**不**自己迁移状态,全部经 ``cw_state.simulate`` 对拍验证。

W32 依赖(cw_system_cards,C2):**已交付,直连消费**——体系卡注册表
``SYSTEM_CARDS``/件数 ``card_pieces``/引擎完备 ``card_engine_complete``;
卡的判据阵营→目标档映射本模块自持(``_CARD_FACTION_TIER``,tier 阈值派生
自 FACTIONS 注册表单一源)。

边界(六矛盾裁决 6):演进引擎 v1 的替换决策**不消费 bench 装备字段**
(替换按角色身份+羁绊档判断,装备只随人走)。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sr_od.application.currency_war.cw_chars import CHARACTERS
from sr_od.application.currency_war.cw_comps import (
    COMP_LIBRARY,
    Comp,
    get_comp,
)
from sr_od.application.currency_war.cw_factions import FACTIONS
from sr_od.application.currency_war.cw_plugins import (
    PLUGIN_LIBRARY,
    plugin_disabled,
)
from sr_od.application.currency_war.cw_state import (
    BENCH_CAPACITY,
    Action,
    BenchChar,
    CompTransaction,
    FillSpec,
    GameState,
    simulate,
)
from sr_od.application.currency_war.cw_system_cards import (
    SYSTEM_CARDS,
    card_engine_complete,
    card_pieces,
)

# 体系卡 →(判据阵营, 目标档);tier 阈值派生自 FACTIONS 注册表(单一源,
# 版本更新自动传导;希儿系双分支取量子侧作演进目标锚)。
_CARD_FACTION_TIER: dict[str, tuple[str, int]] = {
    'xianzhou3': ('仙舟', FACTIONS['仙舟'].tiers[0]),
    'dot2': ('持续伤害', FACTIONS['持续伤害'].tiers[0]),
    'train2': ('列车同行', FACTIONS['列车同行'].tiers[0]),
    'seele': ('量子同频', FACTIONS['量子同频'].tiers[0]),
}


# ===== 评分常量(草案级,效果判断代理;值只进代码) =====
_TIER_WEIGHT: float = 1.0        # 每档 1 点(档位阈值代理)
_CORE_BONUS: float = 2.0         # 核心在手(carry/替班)
_ENGINE_BONUS: float = 1.0       # 引擎完备(铁三角到齐类)追加
_CORE_ON_BOARD_W: float = 0.5    # 现状代理:板上核心折算
_TIER_TIER_ORDER: dict[str, int] = {'T1': 0, 'T2': 1, 'T3': 2}


# ===== 数据结构(C3 契约形状) =====

@dataclass
class UpgradeOption:
    """一次「可上新羁绊」机会(新档或原档升级)。"""
    kind: str                 # 'new_faction' | 'tier_up'
    faction: str
    target_tier: int
    effect_score: float       # ①效果判断的量化(草案级:评分可调)
    core_present: bool        # ②核心校验结果(引擎/替班核心在手)
    # 草案级扩字段(枚举溯源;不改契约形状)
    comp_name: str = ''       # 来源 Comp 名(空=体系卡/纯板面档)
    source: str = ''          # 'card' | 'comp' | 'board'


@dataclass
class UpgradeVerdict:
    """``evaluate_upgrade`` 的裁决记录(三条件逐项可审计)。"""
    option: UpgradeOption
    effect_ok: bool           # ① 新档成型效果 > 现状(2换1 的具体化)
    core_ok: bool             # ② 核心输出(carry/替班)在手
    population_ok: bool       # ③ 摆得下(信息位——③不阻断,摆不下也上)
    execute: bool             # 综合裁决 = ①∧②(发令枪:档齐∧核心到)
    detail: str = ''          # 裁决叙述(未触发原因:bench 等/不拆/窗口)


@dataclass
class EvolutionState:
    """演进引擎的跨步记忆(中断恢复/谷底回滚;挂调用方,session 载体批接)。

    - ``pending``:冻结打断的「还没开始的那次」(遭遇/boss 前 1 轮不启动新替换);
      恢复 = 下个非遭遇轮 ``evolution_step`` 入口三条件重校验,成立则当轮执行。
    - ``paused``:谷底回滚后的放缓标志(下个非遭遇轮解暂停再续,不重演整组合)。
    - ``last_deployed``/``last_retained``:上次替换的新档上场名单/旧档 bench 保留
      名单(回滚窗 1-2 轮的消费锚,rollback_weakest 用)。
    """
    pending: UpgradeOption | None = None
    paused: bool = False
    last_deployed: list[str] = field(default_factory=list)
    last_retained: list[str] = field(default_factory=list)
    last_reason: str = ''


def _identity_index(pool: list[BenchChar], target: BenchChar) -> int:
    """按身份取索引(同名同星 dataclass 值相等会 index 错对象;W26 纪律)。"""
    return next(i for i, y in enumerate(pool) if y is target)


# ===== 观测 helper(纯逻辑;不 import cw_observation 保持离线可测) =====

def _char_factions(bc: BenchChar) -> set[str]:
    """角色的羁绊全集(阵营+流派;开拓者按当前 char_id 归一形态)。"""
    c = CHARACTERS.get(bc.char_id) if bc.char_id else None
    if c is not None:
        return set(c.factions) | set(c.flows)
    return {bc.faction} if bc.faction and bc.faction != '?' else set()


def _owned_names(state: GameState) -> set[str]:
    """在手角色名全集(bench ∪ deployed;「到手」口径)。"""
    return {bc.char_id for bc in (*state.bench, *state.deployed) if bc.char_id}


def _faction_in_hand(state: GameState, faction: str) -> int:
    """该羁绊在手人数(bench ∪ deployed;2换1 的「目标羁绊档」按在手计)。"""
    return sum(1 for bc in (*state.bench, *state.deployed)
               if faction in _char_factions(bc))


def _board_tier(state: GameState, faction: str) -> int:
    return state.board.get(faction, 0)


def _shop_has_faction_member(state: GameState, faction: str) -> bool:
    """再遇窗口代理(草案级):当轮店里可见该羁绊成员。"""
    for card in state.shop:
        c = CHARACTERS.get(card.name) if card.name else None
        fs = (set(c.factions) | set(c.flows)) if c is not None else (
            {card.faction} if card.faction and card.faction != '?' else set())
        if faction in fs:
            return True
    return False


def _comp_formed(comp: Comp, state: GameState) -> bool:
    """comp 主档(form_tiers 下限)已在板上成型。"""
    return all(_board_tier(state, f) >= t for f, t in comp.form_tiers.items())


def _core_names(opt: UpgradeOption) -> tuple[list[str], list[str]]:
    """(核心名单, 替班核心名单)——opt 溯源解析。

    - 体系卡来源:核心 = ``engine_required``(仙舟铁三角;无引擎卡核心=空,
      DOT2/列车2 类随意凑数层无核心概念——羁绊成员即本体);
    - Comp 来源:核心 = ``core_chars``;替班 = ``substitute_plan`` 替班者。
    """
    if opt.source == 'card':
        card = SYSTEM_CARDS.get(opt.comp_name)
        return (list(card.engine_required) if card is not None
                and card.engine_required else []), []
    comp = get_comp(opt.comp_name) if opt.comp_name else None
    if comp is None:
        return [], []
    subs = [p.get('替班者', '') for p in comp.substitute_plan]
    return list(comp.core_chars), [s for s in subs if s]


def _engine_complete_of(comp_name: str, source: str,
                        owned: set[str]) -> bool:
    """引擎完备(空壳判定的对偶):卡=W32 ``card_engine_complete``;Comp=核心全到手。"""
    if source == 'card':
        card = SYSTEM_CARDS.get(comp_name)
        return card_engine_complete(card, owned) if card is not None else False
    comp = get_comp(comp_name) if comp_name else None
    if comp is None or not comp.core_chars:
        return False
    return all(n in owned for n in comp.core_chars)


# ===== ① propose:枚举可上新羁绊机会 =====

def _effect_score(state: GameState, faction: str, target_tier: int,
                  core_in_hand: bool, engine_complete: bool,
                  extra_pieces: int = 0) -> float:
    """①效果判断的量化代理(草案级:档位阈值+核心在场)。

    投影 = 在手能摆出的档位(≤ target_tier)+ 窗口件(再遇窗口可见的缺口
    张,2换1 条件 1 的组成部分)+ 核心在手加成 + 引擎完备加成。
    """
    in_hand = _faction_in_hand(state, faction)
    return (min(in_hand + extra_pieces, target_tier) * _TIER_WEIGHT
            + (_CORE_BONUS if core_in_hand else 0.0)
            + (_ENGINE_BONUS if engine_complete else 0.0))


def _window_pieces(state: GameState, faction: str, target_tier: int) -> int:
    """再遇窗口代理(草案级):缺口张数内当轮店里可见的成员数(≤1 计)。"""
    gap = max(0, target_tier - _faction_in_hand(state, faction))
    if gap >= 1 and _shop_has_faction_member(state, faction):
        return 1
    return 0


def _status_quo_score(state: GameState) -> float:
    """现状代理:板上最强档 + 板上核心折算(与投影同量纲)。"""
    best_tier = max(state.board.values(), default=0)
    owned = _owned_names(state)
    core_n = sum(1 for comp in COMP_LIBRARY
                 if comp.core_chars and comp.core_chars[0] in owned
                 and any(n in {d.char_id for d in state.deployed}
                         for n in comp.core_chars[:1]))
    return best_tier * _TIER_WEIGHT + core_n * _CORE_ON_BOARD_W


def propose_upgrades(state: GameState, session=None) -> list[UpgradeOption]:
    """枚举当前全部可上新羁绊机会(来源 = C2 体系卡 + C4 Comp + 当前板)。

    - 体系卡(C2,桩):四卡目标羁绊,在手 ≥2(2换1 门槛在 evaluate 再校);
    - Comp(C4):每套主档各羁绊,在手人数 ≥2 且板面档 < 目标档 → 机会;
    - 当前板:板上已有羁绊在手人数 > 当前板档 → 升 1 档机会(加深)。
    session.target_comp(意向同向)作 tie-break 加权,非一票否决(C2 语义)。
    """
    opts: list[UpgradeOption] = []
    owned = _owned_names(state)

    def _mk(kind: str, faction: str, target: int, comp_name: str,
            source: str) -> None:
        cores, _subs = _core_names(UpgradeOption(
            kind, faction, target, 0.0, False, comp_name, source))
        core_in_hand = any(n in owned for n in cores) if cores else True
        engine_complete = _engine_complete_of(comp_name, source, owned)
        score = _effect_score(state, faction, target,
                              core_in_hand, engine_complete,
                              _window_pieces(state, faction, target))
        if session is not None and getattr(session, 'target_comp', None) \
                is not None and comp_name == session.target_comp.name:
            score += _TIER_WEIGHT   # 意向同向 tie-break(C2:非一票否决)
        opts.append(UpgradeOption(kind, faction, target, score,
                                  core_in_hand, comp_name, source))

    # 来源1:C2 体系卡(W32)
    for card in SYSTEM_CARDS.values():
        mapping = _CARD_FACTION_TIER.get(card.card_id)
        if mapping is None:
            continue
        faction, target = mapping
        if card.card_id == 'seele' and '希儿' not in owned:
            continue   # 希儿卡:引擎不在手无机会
        if card_pieces(card, state) < 1:
            continue   # 零件局:无可上机会
        _mk('new_faction' if _board_tier(state, faction) == 0 else 'tier_up',
            faction, target, card.card_id, 'card')
    # 来源2:C4 Comp 主档
    for comp in COMP_LIBRARY:
        for faction, tier in comp.form_tiers.items():
            if _faction_in_hand(state, faction) >= 2 \
                    and _board_tier(state, faction) < tier:
                _mk('new_faction' if _board_tier(state, faction) == 0
                    else 'tier_up', faction, tier, comp.name, 'comp')
    # 来源3:当前板(已有羁绊在手可加深 1 档)
    covered = {o.faction for o in opts}
    for faction, board_n in state.board.items():
        in_hand = _faction_in_hand(state, faction)
        if faction not in covered and in_hand > board_n and in_hand >= 2:
            _mk('tier_up', faction, board_n + 1, '', 'board')
    return opts


# ===== ② evaluate:三条件裁决 =====

def evaluate_upgrade(opt: UpgradeOption, state: GameState) -> UpgradeVerdict:
    """①效果判断/②核心校验/③人口检查(替换三条件的决策侧)。

    - ①效果:新档成型投影 > 现状代理(2换1 的具体化);
    - ②核心:carry 或替班核心在手——核心到档未齐 → bench 等(不出事务);
      档齐核心未到 → 不拆过渡档;**最后到齐的那个是发令枪**;
    - ③人口:摆得下→直接上;摆不下→**也上**(替换优先于人口保守——不阻断)。
    2换1:目标羁绊在手 ≥2(到 2 档)才替换过渡 1 档;缺口≤1 张时以
    「当轮店里有成员」作再遇窗口代理(草案级)。
    """
    cores, subs = _core_names(opt)
    owned = _owned_names(state)
    core_in_hand = any(n in owned for n in (*cores, *subs))
    # 无核心概念的档(DOT2/列车2 类随意凑数层):羁绊成员即本体,②恒过
    core_ok = core_in_hand or (not cores and not subs)
    engine_complete = _engine_complete_of(opt.comp_name, opt.source, owned)
    in_hand = _faction_in_hand(state, opt.faction)

    # 条件1:目标核心羁绊 2 档成型(2换1)
    gap = max(0, opt.target_tier - in_hand)
    tier_ok = in_hand >= 2 and gap <= 1 \
        and (gap == 0 or _shop_has_faction_member(state, opt.faction))
    # 条件2:核心输出在场(carry 或替班)
    # 条件1+2 的发令枪交叉语义
    if tier_ok and not core_ok:
        return UpgradeVerdict(opt, True, False, True, False,
                              '档齐核心未到:不拆过渡档(核心是发令枪)')
    if core_ok and not tier_ok:
        return UpgradeVerdict(opt, True, True, True, False,
                              '核心到档未齐:bench 等(档是发令枪)')
    # 条件1+2 齐备 → ①效果判断(投影含窗口件:缺口≤1 张且店里可见)
    effect_ok = _effect_score(state, opt.faction, opt.target_tier,
                              core_ok, engine_complete,
                              1 if (tier_ok and gap >= 1) else 0) \
        > _status_quo_score(state)
    if not effect_ok:
        return UpgradeVerdict(opt, False, core_ok, True, False,
                              '投影不大于现状(2换1 未占优)')
    # ③人口(信息位,不阻断:替换优先于人口保守)
    population_ok = state.deployed_count() <= state.max_units()
    return UpgradeVerdict(opt, True, core_ok, population_ok, True, '三条件齐备')


# ===== ③ execute:整档替换事务(两步执行第 1 步) =====

def _deploy_row(bc: BenchChar, comp: Comp | None,
                front_left: int, back_left: int) -> str:
    """上场排:comp 阵型覆盖 > 注册表站位 > 容量兜底。"""
    pref = bc.position_pref or 'back'
    if comp is not None and bc.char_id in comp.char_positions:
        pref = comp.char_positions[bc.char_id]
    if pref == 'front' and front_left <= 0:
        return 'back'
    if pref == 'back' and back_left <= 0:
        return 'front'
    return pref


def execute_replacement(verdict: UpgradeVerdict, state: GameState,
                        memory: EvolutionState | None = None) -> list[Action]:
    """④-1 生成整档替换 CompTransaction(决策在执行前一起定)。

    完整方案一次敲定:新档成员上场(核心优先)+ 旧档整档解除(羁绊不在目标
    集且非目标成员者下场)+ 被换下成员去向(bench 保留优先——保回滚窗
    1-2 轮(点6 谷底预案),bench 溢出才卖)。DOT 同体线自然退化为加深
    (旧档空 → undeploy/sell 空,纯 deploy)。
    """
    if not verdict.execute:
        return []
    opt = verdict.option
    comp = get_comp(opt.comp_name) if opt.source == 'comp' else None
    cores, subs = _core_names(opt)
    target_member_names = set(cores) | set(subs)
    if comp is not None:
        target_member_names |= set(comp.core_chars) | set(comp.shared_chars)
        for p in comp.substitute_plan:
            if p.get('替班者'):
                target_member_names.add(p['替班者'])
    target_factions = ({opt.faction} | set(comp.form_tiers)) if comp \
        else {opt.faction}

    # 新档成员:在手目标羁绊成员(核心/目标成员优先,bench 源上场)
    def _is_new_line(bc: BenchChar) -> bool:
        return (opt.faction in _char_factions(bc)) \
            or (bc.char_id in target_member_names)

    bench_new = [bc for bc in state.bench if _is_new_line(bc)]
    bench_new.sort(key=lambda bc: (
        0 if bc.char_id in target_member_names else 1, -bc.star))
    deployed_keep = [d for d in state.deployed if _is_new_line(d)]
    # 旧档:非新线成员整档解除
    old_line = [d for d in state.deployed if not _is_new_line(d)]
    # 人口上限内的上场数(③摆不下也上:先换掉旧档,超 cap 再裁非核心新件)
    room = state.max_units() - len(deployed_keep)
    bench_new = bench_new[:max(0, room)]

    # 去向:旧档下场进 bench 保回滚窗(高星/高费优先保留),溢出卖出
    bench_free = BENCH_CAPACITY - (len(state.bench) - len(bench_new))
    retained = sorted(old_line, key=lambda d: (
        -d.star, -(CHARACTERS[d.char_id].cost
                   if CHARACTERS.get(d.char_id) else 0)))
    retained = retained[:max(0, bench_free)]
    sold = [d for d in old_line if not any(d is r for r in retained)]

    # 索引(按事务前状态解析,契约口径;身份索引——同名同星 dataclass
    # 值相等会让 list.index 删错对象,同 cw_state._remove_by_identity 纪律)
    undeploy_idx = [_identity_index(state.deployed, d) for d in retained]
    sell_entries = [(_identity_index(state.deployed, d), 'deployed')
                    for d in sold]
    # 排容量核算(下场后排空出;上限校验由 simulate 权威做,这里选排)
    front_left = state.front_max - state.front_count() \
        + sum(1 for d in (*retained, *sold) if d.position_pref == 'front')
    back_left = state.back_max - state.back_count() \
        + sum(1 for d in (*retained, *sold) if d.position_pref == 'back')
    deploy_entries = []
    for bc in bench_new:
        row = _deploy_row(bc, comp, front_left, back_left)
        if row == 'front':
            front_left -= 1
        else:
            back_left -= 1
        deploy_entries.append((_identity_index(state.bench, bc), row))

    old_label = '/'.join(sorted(f for f, n in state.board.items()
                                 if f not in target_factions)) or '加深'
    if opt.source == 'card':
        card = SYSTEM_CARDS.get(opt.comp_name)
        new_label = card.display_name if card is not None else opt.comp_name
    else:
        new_label = comp.name if comp is not None \
            else f'{opt.faction}{opt.target_tier}'
    reason = f'evolve:{old_label}→{new_label}'
    if not deploy_entries and not undeploy_idx and not sell_entries:
        return []   # 无替换内容(纯加深/纯填位)→ 非演进步,归常规通道(围栏/空位规则)
    if memory is not None:
        memory.pending = None
        memory.last_deployed = [bc.char_id for bc in bench_new]
        memory.last_retained = [d.char_id for d in retained]
        memory.last_reason = reason
    tx = CompTransaction(deploy=deploy_entries, undeploy=undeploy_idx,
                         sell=sell_entries, fill=None, reason=reason)
    return [tx]


# ===== ④-2 fill:人口缺口填位(空位规则) =====

def _plugin_rank(bc: BenchChar, state: GameState,
                 family: str) -> tuple[int, int] | None:
    """插件填位排序键(能开新档=0 < 单卡效果=1 < 散件=2;None=不进插件序)。

    - 小羁绊插件:加它能把该羁绊顶到注册档(「能开新档」)→ rank 0;
    - 单卡插件(kind='unit')→ rank 1;
    - 散件(非插件)→ rank 2(由调用方作兜底,本函数返回 None);
    - 禁用矩阵命中 / 过半线(majority_lines 含当前家族=该线是骨架非插件)→ 排除。
    """
    name = bc.char_id
    if not name or name not in PLUGIN_LIBRARY:
        return None
    entry = PLUGIN_LIBRARY[name]
    if family and (family in entry.majority_lines
                   or plugin_disabled(name, family) is not None):
        return None
    if entry.kind == 'small_faction':
        # plugin_id 形如 '列车2':羁绊=去尾档数字,档=尾数字
        tier = int(name[-1]) if name[-1].isdigit() else 2
        faction = name[:-1] if name[-1].isdigit() else name
        cur = _faction_in_hand(state, faction)
        return (0 if cur + 1 >= tier else 3, _TIER_TIER_ORDER[entry.tier])
    return (1, _TIER_TIER_ORDER[entry.tier])


def _is_waiting_true_core(name: str, state: GameState) -> bool:
    """真核心 bench 等档(点11:上场时机=新档成型时机,不是到手时机)。

    判定:某套 comp 的 carry(core_chars[0])、该套主档未在板上成型、
    且本人不是插件(插件身份优先——互补不重叠规则)。
    """
    if not name or name in PLUGIN_LIBRARY:
        return False
    return any(comp.core_chars and comp.core_chars[0] == name
               and not _comp_formed(comp, state) for comp in COMP_LIBRARY)


def _substitute_candidates(state: GameState,
                           target: Comp | None) -> list[BenchChar]:
    """替班核心例外名单(带自己的低档一起上——她们当家的时间段)。"""
    names: set[str] = set()
    if target is not None:
        names = {p.get('替班者', '') for p in target.substitute_plan}
    else:
        board_factions = set(state.board)
        for comp in COMP_LIBRARY:
            if comp.substitute_plan and comp.form_tiers:
                primary = next(iter(comp.form_tiers))
                if primary in board_factions:
                    names |= {p.get('替班者', '') for p in comp.substitute_plan}
    names.discard('')
    return [bc for bc in state.bench if bc.char_id in names]


def _fill_candidates(state: GameState, target: Comp | None) -> list[BenchChar]:
    """空位规则排序后的 bench 填位候选(插件优先/替班例外/真核心除外)。"""
    subs = {bc.char_id for bc in _substitute_candidates(state, target)}
    family = target.family if target is not None and target.family else ''
    ranked: list[tuple[tuple[int, int], int, BenchChar]] = []
    for i, bc in enumerate(state.bench):
        if _is_waiting_true_core(bc.char_id, state):
            continue   # 真核心 bench 等档:不填散位
        if bc.char_id in subs:
            ranked.append(((-1, 0), i, bc))   # 替班核心例外:最高优先
            continue
        if bc.char_id in PLUGIN_LIBRARY and family \
                and plugin_disabled(bc.char_id, family) is not None:
            continue   # 禁用矩阵=硬冲突(见了不买),不降级为散件兜底
        rank = _plugin_rank(bc, state, family)
        if rank is not None:
            ranked.append((rank, i, bc))
        else:
            ranked.append(((4, 0), i, bc))   # 散件兜底
    ranked.sort(key=lambda t: (t[0], t[1]))
    return [bc for _, _, bc in ranked]


def _target_of(state: GameState) -> Comp | None:
    """从事后状态推断目标 comp(fill_gap_after 无显式 target 时的草案级推断)。"""
    if not state.board:
        return None
    dom = max(state.board, key=lambda f: state.board[f])
    best: Comp | None = None
    for comp in COMP_LIBRARY:
        if dom in comp.form_tiers and comp.family and comp.family != 'legacy':
            if best is None or comp.form_tiers[dom] > best.form_tiers[dom]:
                best = comp
    return best


def fill_gap_after(tx: CompTransaction, state: GameState,
                   target: Comp | None = None) -> list[FillSpec]:
    """④-2 数人口缺口,按空位规则重新选择填位。

    ``state`` = **事务后状态**(``simulate(state_pre, tx)`` 的产物——后置
    bench 正是 FillSpec bench 源的解析域,C1 口径);``target`` 草案级可选参
    (缺省从板上优势羁绊推断——替班/禁用矩阵需要目标 comp 语境)。
    多个 bench 源填位的 ``idx`` 按 ``_apply_comp_transaction`` 的 pop 语义
    逐个左移修正(第 k 个已选前的候选已被 pop)。
    """
    gap = state.max_units() - state.deployed_count()
    if gap <= 0:
        return []
    comp = target if target is not None else _target_of(state)
    cands = _fill_candidates(state, comp)
    fills: list[FillSpec] = []
    removed: set[int] = set()   # 已选 bench 源的原始下标(pop 语义左移修正)
    front_left = state.front_max - state.front_count()
    back_left = state.back_max - state.back_count()
    for bc in cands:
        if len(fills) >= gap:
            break
        row = bc.position_pref or 'back'
        if row == 'front' and front_left <= 0:
            row = 'back'
        if row == 'back' and back_left <= 0:
            row = 'front'
        if row == 'front':
            front_left -= 1
        else:
            back_left -= 1
        orig = _identity_index(state.bench, bc)
        # ``_apply_comp_transaction`` 对 fill 按序 pop:第 k 个填位的 idx =
        # 其原始下标左侧尚未被 pop 的元素数(逐选左移,契约草案级口径)
        idx = sum(1 for j in range(orig) if j not in removed)
        removed.add(orig)
        fills.append(FillSpec('bench', idx, row))
    # bench 候选枯竭 → shop 插件(单卡)补位(金够且不禁用)
    if len(fills) < gap:
        family = comp.family if comp is not None and comp.family else ''
        for i, card in enumerate(state.shop):
            if len(fills) >= gap:
                break
            if not card.name or card.name not in PLUGIN_LIBRARY:
                continue
            entry = PLUGIN_LIBRARY[card.name]
            if entry.kind != 'unit' or (family and (
                    family in entry.majority_lines
                    or plugin_disabled(card.name, family) is not None)):
                continue
            cost = card.cost or 3
            if state.gold < cost:
                continue
            fills.append(FillSpec('shop', i, 'back'))
    return fills


def fill_slot_policy(state: GameState,
                     family: str = '') -> list[FillSpec]:
    """空位规则入口(点11;升人口/扩容空位,无事务语境)。

    空位即填:插件优先(能开新档 > 单卡效果 > 散件)/替班核心例外
    (带自己的低档一起上)/真核心 bench 等档(上场时机=新档成型时机)。
    ``family`` 可选:目标家族键(禁用矩阵/过半线判定;缺省不查)。
    """
    gap = state.max_units() - state.deployed_count()
    if gap <= 0:
        return []
    target = _target_of(state)
    if family:
        comp = target
        if comp is None or comp.family != family:
            comp = next((c for c in COMP_LIBRARY if c.family == family), None)
        target = comp
    return fill_gap_after(CompTransaction([], [], [], reason='slot_policy'),
                          state, target)


# ===== 统一入口 + 中断恢复/谷底回滚(冻结语义) =====

_ENCOUNTER_NODES = {'遭遇', 'boss'}   # 冻结扩到遭遇前:不启动新替换


def evolution_step(state: GameState, session=None,
                   memory: EvolutionState | None = None) -> list[Action]:
    """统一入口(冻结:任何阵容改进步动走这里)。

    propose → evaluate →(最优 verdict)execute → fill;返回待执行动作序列
    (含 CompTransaction 与 FillSpec 填位)。DOT 同体线自然退化为加深无替换
    (旧档空 → 纯 deploy 事务)。中断恢复:替换是原子动作,冻结打断的是
    「还没开始的那次」——恢复 = pending 三条件重校验,成立则当轮执行;
    谷底回滚暂停(``memory.paused``)= 回滚一件最弱替换位后放缓
    (``rollback_weakest``),下个非遭遇轮再续,不重演整组合。
    ``memory`` 草案级可选参(缺省每次新建=无记忆;session 挂载归载体批)。
    """
    mem = memory if memory is not None else EvolutionState()
    # 恢复语义:谷底暂停 → 下个非遭遇轮解暂停再续
    if mem.paused:
        if state.node_type in _ENCOUNTER_NODES:
            return []
        mem.paused = False
    # 冻结扩到遭遇前:不启动新替换(pending 记下,恢复时重校验)
    frozen = state.node_type in _ENCOUNTER_NODES

    def _try(opt: UpgradeOption) -> list[Action]:
        verdict = evaluate_upgrade(opt, state)   # 三条件重校验(恢复语义)
        if not verdict.execute:
            return []
        actions = execute_replacement(verdict, state, mem)
        if not actions:
            return []
        tx = actions[0]
        assert isinstance(tx, CompTransaction)
        post = simulate(state, tx)
        if post.action_log and post.action_log[-1].get('result') == 'applied':
            fills = fill_gap_after(tx, post)
            if fills:
                tx.fill = fills
                re = simulate(state, tx)
                if not (re.action_log and
                        re.action_log[-1].get('result') == 'applied'):
                    tx.fill = None   # 填位拖垮原子性 → 剥离,另轮走常规填位
        return [tx]

    if mem.pending is not None:
        actions = _try(mem.pending)
        if actions:
            return actions
        mem.pending = None   # 重校验失败:那次替换作废,回到常规枚举

    if frozen:
        # 本轮不启动新替换;可执行的最优机会登记为 pending(下次恢复重校验)
        best = _best_option(state, session)
        if best is not None:
            mem.pending = best
        return []

    best = _best_option(state, session)
    if best is None:
        return []
    return _try(best)


def _best_option(state: GameState, session=None) -> UpgradeOption | None:
    """可执行机会里的最优(effect_score 降序;无 → None)。"""
    best: UpgradeOption | None = None
    for opt in propose_upgrades(state, session):
        verdict = evaluate_upgrade(opt, state)
        if not verdict.execute:
            continue
        if best is None or opt.effect_score > best.effect_score:
            best = opt
    return best


def rollback_weakest(state: GameState,
                     memory: EvolutionState) -> Action | None:
    """谷底回滚(点6:转型中单场掉血>15 触发,调用方观测)。

    回滚**一件最弱替换位**后放缓(``memory.paused=True``),下个非遭遇轮
    再续,不重演整组合:上次替换的新档上场名单里挑最弱(星级→费用),
    有旧档保留件(bench 回滚窗)→ SwapDeploy 换回;无 → SellDeployed 退役。
    """
    if not memory.last_deployed:
        return None
    deployed_of_new = [d for d in state.deployed
                       if d.char_id in memory.last_deployed]
    if not deployed_of_new:
        return None

    def _weak_key(d: BenchChar) -> tuple[int, int]:
        c = CHARACTERS.get(d.char_id)
        return (d.star, c.cost if c is not None else 0)

    weakest = min(deployed_of_new, key=_weak_key)
    d_idx = next(i for i, d in enumerate(state.deployed) if d is weakest)
    retained = [b for b in state.bench
                if b.char_id in memory.last_retained]
    if retained:
        b_idx = next(i for i, b in enumerate(state.bench)
                     if b is retained[0])
        memory.paused = True
        return _swap_action(d_idx, b_idx)
    memory.paused = True
    return _sell_action(d_idx)


def _swap_action(d_idx: int, b_idx: int) -> Action:
    from sr_od.application.currency_war.cw_state import SwapDeploy
    return SwapDeploy(d_idx, b_idx, reason='valley_rollback')


def _sell_action(d_idx: int) -> Action:
    from sr_od.application.currency_war.cw_state import SellDeployed
    return SellDeployed(d_idx, reason='valley_rollback')
