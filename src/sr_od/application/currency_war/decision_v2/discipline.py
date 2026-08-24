"""决策框架 v2 纪律族(载体批 W35;自 line_strategy 移植+语义重接)。

**单一源**:`.debug/temp/currency_war/cw_dev/deep_read/strategy_v4.md` 点4(掉血
报警三臂/处置梯度时限)/点7(血线分级动作侧/位面末 ALL IN 限定)/点12(保血通道/
奖励关三态护栏)+ 裁决终版「第三选项」(纪律族移植,locked_line 派生改意向分层
输入——本模块**不 import** line_strategy/线库/桥池,方向输入一律是
``cw_intention`` 的意向态与 ``session.v3_*`` 视图)。

移植清单(v1 → v2 语义重接对照,详 W35_报告):
- 应急(_emergency/_emergency_actions)→ ``emergency_hp`` 绝对档+``rebirth_floor``
  保留重生基数([18]):v1 同名常量移植,触发与地板语义不变;
- boss_breaker(_boss_breaker_actions)→ 破息窗地板(10/连胜 EV 5)+ P1 r5-r8
  遭遇预备窗口:围栏从 RECIPE_FACTIONS 换**意向线 form_tiers∪sub_tiers∩板面**
  (体系卡/意向线本体论);
- carry_gate(_carry_bench_gate)→ bench 满+意向核心在店+金足 → 降保护集卖最弱
  件买核心:carry 从 ``line_of(locked_line).carry`` 换 ``intention_core``(
  COMP_LIBRARY v2 的 plaza_carry/core_chars[0]);保护集从桥池名单换
  hoard 目标集;
- catchup(_catchup_actions / E5/E6)→ ``pop_baseline``+``catchup_min_level``
  等级门:判定语义原样移植(r232);执行侧由层2 过滤(catchup_tags)+层4
  地板承载,不再走独立动作分支;
- 同轮互斥/种子年龄豁免(r408/ADR-0289 §5)→ 纯谓词移植(不依赖线库)。

行为纪律(strategy_v4 逐条):
- **hp 报警语义**(点4/[W10 D8-5]):掉血三臂判据是**报警不是触发**——
  报警激活处置梯度(弃息 D 保血),**永不单独触发 ALL IN**;
- **位面末 ALL IN 限定**(点7/[18]):「花光提质量」仅位面末最后一战
  (boss 节点+轮=位面节点数)——``allin_window`` 是唯一把地板清零的路径;
- **保血通道**(点12):遭遇前战力不足+战斗语义掉血趋势 → 弃息 D 保血
  (放行 refresh 搜牌),三态护栏(贴息态/守息态)由层4 interest_rule 承载。

常量值镜像 line_strategy 同名初值(地板族);注册表化后两臂可故意不同(A/B)。
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, replace

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_chars import CHARACTERS
from sr_od.application.currency_war.cw_economy import streak_gold
from sr_od.application.currency_war.cw_horizon import NODES_PER_PLANE
from sr_od.application.currency_war.cw_intention import (
    IntentionState,
    intention_core,
)
from sr_od.application.currency_war.cw_state import (
    BENCH_CAPACITY,
    BuyCard,
    GameState,
    SellBench,
    sell_refund,
)
from sr_od.application.currency_war.cw_strategy import StrategySession

# ===== 体系卡引擎件(铁三角+希儿;C2 单一源 import 不复制)=====
from sr_od.application.currency_war.cw_system_cards import SYSTEM_CARDS
from sr_od.application.currency_war.decision_v2.registry import (
    DecisionV2Registry,
)


def engine_char_names() -> frozenset[str]:
    """四体系卡的引擎件名全集(铁三角三人组+希儿;点3 见即买名单)。"""
    out: set[str] = set()
    for card in SYSTEM_CARDS.values():
        out.update(card.engine_required)
    return frozenset(out)


# ===== 纯谓词族(v1 line_strategy 移植;不依赖线库/桥池) =====


def star_weighted_copies(name: str, state: GameState) -> int:
    """同名星级加权副本数(bench+deployed;2★=2 份,3★=3 份)。"""
    n = sum(getattr(b, 'star', 1) or 1
            for b in (state.bench or []) if b.char_id == name)
    n += sum(getattr(d, 'star', 1) or 1
             for d in (state.deployed or [])
             if getattr(d, 'char_id', '') == name)
    return n


def in_round_sold(name: str, state: GameState,
                  session: StrategySession) -> bool:
    """r408(ADR-0267 对称臂):该卡名本轮是否刚被卖出(买通道回读)。"""
    if not name:
        return False
    return (getattr(session, 'v2_round_key', None)
            == (state.plane, state.round_num)
            and name in (getattr(session, 'v2_round_sold', None) or ()))


def round_sell_blocked(bc, state: GameState,
                       session: StrategySession) -> bool:
    """r408(ADR-0267,F1 振荡):同轮已买的卡名禁卖;3合1 让位豁免(≥3 份)。"""
    if not getattr(bc, 'char_id', ''):
        return False
    if getattr(session, 'v2_round_key', None) \
            != (state.plane, state.round_num):
        return False
    if bc.char_id not in (getattr(session, 'v2_round_bought', None) or ()):
        return False
    return star_weighted_copies(bc.char_id, state) < 3


def seed_age_blocked(bc, state: GameState,
                     session: StrategySession | None) -> bool:
    """ADR-0289 §5:engine_seed 年龄豁免——买入 ≤2 轮且同轮份数 <2 的种子
    不进可卖集(跨轮窗;同轮 ≥2 份=3合1 素材语境豁免)。"""
    name = getattr(bc, 'char_id', '')
    if not name or session is None:
        return False
    rec = (getattr(session, 'v2_seed_bought', None) or {}).get(name)
    if rec is None:
        return False
    key, cnt = rec
    if key[0] != state.plane:
        return False
    return 0 <= state.round_num - key[1] <= 2 and cnt < 2


def engine_seed_wants(card, state: GameState,
                      session: StrategySession | None = None) -> bool:
    """体系方向件放行门(点1/点3;v1 ADR-0260 门的语义重接):

    两路放行(OR):
    ① **C2 引擎件名单**(铁三角+希儿——见即买,点3 本体论名单);
    ② 过渡体系阵营件(仙舟/列车同行/持续伤害)未持有(v1 ADR-0260
       「引擎乐高第一块砖」门——体系方向件=对当前体系羁绊贡献>0 的件,
       定义节 class1 口径,窄化到引擎名单会漏 21% 买入面,ADR-0299 锁)。
    共同门:P1 过渡期;未持有同名;bench 满员不触发(r408 容量门);
    同轮已卖不回买。金够/不破息档由层4 gold_floor 辖(本门不加价)。
    """
    if not card.name or state.plane != 1:
        return False
    if len(state.bench or []) >= BENCH_CAPACITY:
        return False   # r408:满员不种(ADR-0267 F1 容量门)
    if session is not None and in_round_sold(card.name, state, session):
        return False
    if has_same_name_copy(card, state):
        return False
    if card.name in engine_char_names():
        return True    # ① C2 引擎件名单
    # ② 过渡体系阵营(v1 门语义)
    from sr_od.application.currency_war.cw_chars import CHARACTERS
    from sr_od.application.currency_war.cw_deploy_logic import (
        TRANSITION_TRAITS,
    )
    ch = CHARACTERS.get(card.name)
    card_bonds = (set(ch.factions) | set(ch.flows)) if ch \
        else {card.faction}
    return bool(card_bonds & {f for f, _t in TRANSITION_TRAITS})


def has_same_name_copy(card, state: GameState) -> bool:
    """r383b:已拥有同名卡(bench/deployed 任一)→ 副本素材真。"""
    if not card.name:
        return False
    if any(b.char_id == card.name for b in (state.bench or [])):
        return True
    return any(getattr(d, 'char_id', '') == card.name
               for d in (state.deployed or []))


def _char_bonds(name: str, faction: str = '') -> set[str]:
    ch = CHARACTERS.get(name)
    if ch is not None:
        return set(ch.factions) | set(ch.flows)
    return {faction} if faction and faction != '?' else set()


def _direction_factions(session: StrategySession) -> set[str] | None:
    """方向期阵营门(v1 r350 的语义重接):意向锁定 = 意向线主/副档羁绊;

    无方向(未锁/弱意向/兜底)= 过渡体系阵营(仙舟/列车同行/持续伤害)。
    A/B 窗兼容垫片:旧载体形态(``v3_intention`` 缺失且 ``locked_line``
    已设)回退线库形态羁绊(步 5 锁迁移后删)。None = 无方向信息。
    """
    ist = getattr(session, 'v3_intention', None)
    if ist is not None and isinstance(ist, IntentionState) \
            and ist.phase == 'locked' and ist.locked_comp:
        from sr_od.application.currency_war.cw_comps import get_comp
        comp = get_comp(ist.locked_comp)
        if comp is not None:
            return set(comp.form_tiers) | set(comp.sub_tiers)
    if ist is None and getattr(session, 'locked_line', None):
        # 旧载体垫片:锁线形态羁绊(v1 r350 同式)
        from sr_od.application.currency_war.cw_line_library_v1 import (
            line_of,
        )
        line = line_of(session.locked_line or '')
        if line is not None:
            form = line.p2p3_forms.get('P2', '')
            allow = {p.rstrip('0123456789') for p in form.split('+')}
            allow.discard('')
            if allow:
                return allow
    from sr_od.application.currency_war.cw_deploy_logic import (
        TRANSITION_TRAITS,
    )
    return {f for f, _t in TRANSITION_TRAITS}


def pair_wants(card, state: GameState,
               session: StrategySession | None = None) -> bool:
    """凑对搭档件放行门(v1 _pair_wants 语义重接,方向输入=意向分层):

    - 方向期阵营门:意向线主/副档羁绊(锁定)/过渡体系阵营(未锁);
    - 冷启动(无已有阵营 或 P1 r≤2):只放行引擎件∪同名副本∪方向阵营件
      (v1 r368/r371b/r383b——买进来的每一张都是方向件);
    - A5 spread 门:已有阵营 ≥3 不开新阵营;
    - 常态:同阵营凑对;r408 同轮已卖不回买。
    """
    if not card.name or not card.faction or card.faction == '?':
        return False
    if session is not None and in_round_sold(card.name, state, session):
        return False
    # 方向期阵营门(仅**有方向**时辖——v1 r350 同式:无方向不过滤):
    # 意向锁定=意向线主/副档羁绊;旧载体锁线=线形态羁绊(垫片);
    # 有桥=过渡体系阵营。
    ist = getattr(session, 'v3_intention', None)
    has_direction = (
        (ist is not None and isinstance(ist, IntentionState)
         and ist.phase == 'locked' and ist.locked_comp)
        or (ist is None and bool(getattr(session, 'locked_line', None)
                                 or getattr(session, 'bridge_id', None))))
    allow: set[str] | None = None
    if has_direction:
        allow = _direction_factions(session)
        if allow is not None \
                and not (_char_bonds(card.name, card.faction) & allow):
            return False
    owned_factions = set(state.board.keys())
    for b in (state.bench or []):
        if b.faction and b.faction != '?':
            owned_factions.add(b.faction)
    if not owned_factions or (state.plane == 1 and state.round_num <= 2):
        # 冷启动:引擎件 ∪ 同名副本 ∪ 方向阵营件(classify_buy 单一源)
        if has_same_name_copy(card, state):
            return True
        if card.name in engine_char_names():
            return True
        if allow is not None and card.faction in allow:
            return True
        from sr_od.application.currency_war.cw_line_defs import classify_buy
        return classify_buy(card, state) in ('bridge_seed', 'engine')
    if card.faction not in owned_factions and len(owned_factions) >= 3:
        return False    # A5:阵营上限
    return card.faction in owned_factions


def copy_swap_useless(card, state: GameState,
                      session: StrategySession) -> bool:
    """r410(ADR-0267 同族):同名跨副本无效换卡守卫(镜像 deploy 侧保留
    判据;target_comp 在新载体=COMP_LIBRARY v2 真 Comp,属性面兼容)。"""
    if not card.name:
        return False
    dep_copies = [d for d in (state.deployed or [])
                  if getattr(d, 'char_id', '') == card.name]
    if not dep_copies:
        return False
    _tc = getattr(session, 'target_comp', None)
    t_fac = set(getattr(_tc, 'factions', ()) or ()) if _tc else set()
    t_core = set(getattr(_tc, 'core_chars', ()) or ()) if _tc else set()
    for d in dep_copies:
        if d.char_id in t_core:
            return False   # core 显式保留 → 买副本合法
        if _char_bonds(d.char_id, d.faction) & t_fac:
            return False   # target 阵营单位保留 → 凑对合法
    return True


# ===== 掉血报警三臂(点4〔修A2 勿动〕;战斗语义,非战斗节点不计入不重置)=====


@dataclass
class BloodAlarmTracker:
    """掉血三臂判据的跨步记忆(挂 session.v3_alarm;重启丢 session 保守重置)。

    - ``recent_losses``:(全局节点号, 战斗净掉血)滚动窗——②滚动 3 节点
      累计 ≥20(急性)/③滚动 5 节点累计 ≥30(慢性漂移);
    - ``consec_battle_fails``:①连续 2 场战斗失败;
    - 非战斗节点:不入窗、不清臂(点4 冻结语义)。
    """

    recent_losses: deque = field(default_factory=lambda: deque(maxlen=5))
    consec_battle_fails: int = 0

    _BATTLE_NODES: frozenset[str] = frozenset(
        {'battle', '遭遇', 'boss', '精英'})

    def record(self, node_type: str, hp_before: int, hp_after: int,
               t: int) -> None:
        """on_round_end 喂入(结算真值;hp_after 为空帧跳过)。"""
        if node_type not in self._BATTLE_NODES:
            return   # 非战斗节点不计入也不重置任何一臂
        loss = max(0, hp_before - hp_after)
        self.recent_losses.append((t, loss))
        # ①连续失败代理:单场净掉血 ≥10 视为该节点实际打输(r246 口径)
        if loss >= 10:
            self.consec_battle_fails += 1
        else:
            self.consec_battle_fails = 0

    def alarm_active(self) -> bool:
        """三臂并集:①连续 2 场战斗失败;②滚动 3 节点累计 ≥20;
        ③滚动 5 节点累计 ≥30(阈值=设计推断,sim 校准,W10 摆动域)。"""
        if self.consec_battle_fails >= 2:
            return True
        losses = [loss for _t, loss in self.recent_losses]
        if len(losses) >= 3 and sum(losses[-3:]) >= 20:
            return True
        return len(losses) >= 5 and sum(losses) >= 30


# ===== 纪律族评估(decide_prep 每轮入口消费)=====


@dataclass(frozen=True)
class DisciplineView:
    """一轮的纪律族裁决(层2/层4 的视图输入)。

    - ``coverage``:'emergency' | 'blood_alarm' | 'boss_breaker' |
      'catchup' | 'mode'(判读/遥测锚点);
    - ``mode``:'war'|'economy'(filters/interest_rule 消费);
    - ``allin``:位面末最后一战([18] 限定)——**唯一**清零地板的路径;
    - ``allow_refresh_in_war``:保血通道(点12)——报警+硬节点放行 refresh;
    - ``war_floor_override``:boss_breaker 破息窗地板(v1 r278/r308 EV 移植)。
    """

    coverage: str
    mode: str
    allin: bool = False
    allow_refresh_in_war: bool = False
    war_floor_override: int | None = None

    def arbiter_registry(self, registry: DecisionV2Registry
                         ) -> DecisionV2Registry:
        """层4 仲裁用注册表视图(地板/标签集按纪律调整;评分仍用原表)。"""
        reg = registry
        if self.allin:
            # [18] 位面末最后一战 ALL IN:地板全清零(唯一路径;hp 报警
            # 不触发 ALL IN——alarm 路径永远到不了这里)
            reg = replace(reg, interest_floor=0, war_floor=0,
                          rebirth_floor=0, boss_floor=0,
                          refresh_min_gold=0)
        elif self.war_floor_override is not None:
            reg = replace(reg, war_floor=self.war_floor_override)
        if self.allow_refresh_in_war:
            reg = replace(reg, war_tags=reg.war_tags | frozenset({'refresh'}))
        return reg


def plane_last_battle(state: GameState, session: StrategySession) -> bool:
    """位面末最后一战([18]):当前节点=boss 且轮=位面节点数。"""
    node = getattr(session, 'node_type_current', None) or state.node_type or ''
    return node in ('boss',) and state.round_num >= NODES_PER_PLANE


def _streak_floor(state: GameState, session: StrategySession,
                  registry: DecisionV2Registry,
                  base_floor: int) -> int:
    """boss_breaker 连胜 EV 地板(v1 r308 移植):连胜 ≥2 + 硬节点 +
    EV(保连胜奖励 × 剩余节点)> 一次性息损失 → 地板降 5。"""
    streak = getattr(session, 'last_streak', 0) or 0
    node = getattr(session, 'node_type_current', None) or ''
    remaining = max(0, NODES_PER_PLANE - state.round_num)
    tier_now = streak_gold(streak) if streak >= 2 else 0
    ev_reward = (tier_now - 1) * remaining      # 断了回到 1 档
    ev_interest = 0.25                           # 一次性息损失
    hard_node = node in ('encounter', 'boss', '遭遇') or \
        (node in ('battle', '战斗') and remaining <= 3)
    if streak >= 2 and hard_node and ev_reward > ev_interest:
        return 5
    return base_floor


def assess_discipline(state: GameState, session: StrategySession,
                      registry: DecisionV2Registry) -> DisciplineView:
    """纪律族评估(覆盖态优先序:应急 > 掉血报警 > boss_breaker > 追赶 > 模式)。

    语义重接要点(strategy_v4 点4/点7/点12):
    - 应急(hp≤emergency_hp):rebirth 地板由层4 ``_active_floor`` 分派
      (is_emergency 优先),此处只标 coverage/mode;
    - 掉血报警(三臂):**报警不是触发**——处置=war 模式+保血通道
      (硬节点放行 refresh 弃息 D),不动地板、不 ALL IN;
    - boss_breaker:P1 r≥5 遭遇预备窗/boss 节点,war 模式+破息地板 10
      (连胜 EV 5);
    - ALL IN:仅 ``plane_last_battle``([18] 位面末最后一战限定)。
    """
    node = getattr(session, 'node_type_current', None) or state.node_type or ''
    if state.hp <= registry.emergency_hp:
        return DisciplineView(coverage='emergency', mode='war',
                              allin=plane_last_battle(state, session))
    tracker = getattr(session, 'v3_alarm', None)
    if tracker is not None and tracker.alarm_active():
        # 点12 保血通道:遭遇/boss 前弃息 D 保血(报警语义:处置梯度,
        # 非 ALL IN——allin 恒 False 由本分支字面保证)
        hard = node in ('encounter', 'boss', '遭遇')
        return DisciplineView(coverage='blood_alarm', mode='war',
                              allin=False, allow_refresh_in_war=hard)
    boss_window = (node in registry.boss_round_node_types
                   or (state.plane == 1 and state.round_num >= 5))
    if boss_window:
        floor = _streak_floor(state, session, registry, registry.boss_floor)
        return DisciplineView(
            coverage='boss_breaker', mode='war',
            allin=plane_last_battle(state, session),
            war_floor_override=floor)
    from sr_od.application.currency_war.decision_v2.filters import is_catchup
    if is_catchup(state, session, registry):
        return DisciplineView(coverage='catchup', mode='economy')
    return DisciplineView(coverage='mode', mode='economy')


# ===== carry_gate(bench 满腾位买意向核心;v1 r416 语义重接)=====


def carry_gate_actions(state: GameState, session: StrategySession,
                       registry: DecisionV2Registry,
                       bought: set[str] | None = None) -> list:
    """carry 腾位门(v1 ADR-0280 r416 移植;语义重接):

    v1:carry=``line_of(locked_line).carry``;v2:carry=意向核心
    (``intention_core`` of COMP_LIBRARY v2 锁定套)。门(全过才腾位):
    ①收益域 P1 r≤carry_gate_max_round;②意向锁定且核心在店、未持有、
    金足(不破 war 地板);③bench 满(≥9)且无直接可卖件(保护集外
    且非近轮种子);④降保护集挑 off-line 价值最低件(弱序:非保护>
    非核心>副本冗余;3合1 完整份不动);⑤卖出件入同轮已卖集不回买。
    """
    ist = getattr(session, 'v3_intention', None)
    if not isinstance(ist, IntentionState) or ist.phase != 'locked':
        return []
    from sr_od.application.currency_war.cw_comps import get_comp
    comp = get_comp(ist.locked_comp)
    if comp is None:
        return []
    carry = intention_core(comp)
    if not carry:
        return []
    if state.plane != 1 or state.round_num > registry.carry_gate_max_round:
        return []
    if bought and carry in bought:
        return []
    carry_card = next((c for c in (state.shop or [])
                       if c.name == carry), None)
    if carry_card is None:
        return []
    if has_same_name_copy(carry_card, state) \
            or any(d.char_id == carry for d in (state.deployed or [])):
        return []
    if in_round_sold(carry, state, session):
        return []
    if state.gold - carry_card.cost < registry.war_floor:
        return []
    bench = state.bench or []
    if len(bench) < BENCH_CAPACITY:
        return []   # 未满 → 常规买通道可达
    # 保护集 = 意向线核心+共享+替班(正料不卖)+引擎件(种子)
    protect = set(comp.core_chars) | set(comp.shared_chars)
    for p in comp.substitute_plan:
        if p.get('替班者'):
            protect.add(p['替班者'])
    protect |= engine_char_names()
    # ③ 直接卖通道可用 → 不降保护集
    board_factions = set(state.board.keys())
    for b in bench:
        if (b.char_id and b.char_id not in protect
                and b.faction not in board_factions
                and not round_sell_blocked(b, state, session)
                and not seed_age_blocked(b, state, session)):
            return []
    # ④ 降保护集:off-line 价值最低件
    cands: list[tuple[tuple, int, object]] = []
    for i, b in enumerate(bench):
        if not b.char_id or b.char_id == carry:
            continue
        if round_sell_blocked(b, state, session):
            continue
        cp = star_weighted_copies(b.char_id, state)
        if cp == 3:
            continue   # 3合1 完整份不腾
        key = (b.char_id in protect,
               0 if cp > 3 else 1,   # 超上限冗余最弱
               cp)
        cands.append((key, i, b))
    if not cands:
        return []
    cands.sort(key=lambda c: c[0])
    _k, idx, weakest = cands[0]
    refund = None
    ch = CHARACTERS.get(weakest.char_id)
    if ch is not None and ch.cost:
        refund = sell_refund(getattr(weakest, 'star', 1) or 1, ch.cost)
    log.info('[cw][d2][carry-gate] r%d 腾位:降保护集卖 %s 买意向核心 %s',
             state.round_num, weakest.char_id, carry)
    session.v2_round_sold.add(weakest.char_id)   # r408 对称臂
    return [SellBench(bench_idx=idx, income=refund),
            BuyCard(carry_card, reason='carry_gate')]
