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

行为纪律(strategy_v4 逐条;W51 语义修复批对齐 R1 审查 leader 裁决,
报警语义 why 详 ADR-0313,carry_gate 弱序/变现通道详 ADR-0314):
- **hp 报警语义**(点4/[W10 D8-5]):掉血三臂判据是**报警不是触发**——
  报警激活处置梯度(①自然凑羁绊上界 1 个战斗节点 → ②弃息 D 保血),
  **永不单独触发 ALL IN**;位面末最后一战的 ALL IN 由
  ``plane_last_battle`` 授权([18]——报警态下位面末同样开通,
  报警只是不作为 ALL IN 的触发条件);
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
    bench_occupied,
    sell_refund,
)
from sr_od.application.currency_war.cw_strategy import StrategySession

# ===== 体系卡引擎件(铁三角+希儿;C2 单一源 import 不复制)=====
# W47 统一化:engine_char_names 函数本体上移至 cw_system_cards(注册表旁),
# 本模块 import 复用——消费点(candidates/engine_seed_wants/carry 保护集)零变化。
from sr_od.application.currency_war.cw_system_cards import engine_char_names
from sr_od.application.currency_war.decision_v2.registry import (
    DecisionV2Registry,
)

# ===== 纯谓词族(v1 line_strategy 移植;不依赖线库/桥池) =====


def star_weighted_copies(name: str, state: GameState) -> int:
    """同名星级加权副本数(bench+deployed;2★=2 份,3★=3 份)。"""
    n = sum(getattr(b, 'star', 1) or 1
            for b in (state.bench or []) if b is not None
            and b.char_id == name)
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
    if bench_occupied(state.bench or []) >= BENCH_CAPACITY:
        return False   # r408:满员不种(ADR-0267 F1 容量门;ADR-0316 占用数)
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
    if any(b is not None and b.char_id == card.name
           for b in (state.bench or [])):
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
        if b is not None and b.faction and b.faction != '?':
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

#: [19]② 血量安全边际低线:hp < 此值 = 报警档([W10 D8-5] hp<40 语义
#: 同源)——掉血报警分支里血边际已低时处置梯度直接生效(跳过①自然窗)
BLOOD_MARGIN_LOW_HP: int = 40
#: 处置梯度①「自然凑羁绊」的自然补强窗上界(战斗节点数;strategy_v4
#: 点4 S4「上界 1 轮」——1 个战斗节点自然补强未达标 → 直入②弃息 D)
BLOOD_GRADIENT_NATURAL_BATTLES: int = 1


@dataclass
class BloodAlarmTracker:
    """掉血三臂判据的跨步记忆(挂 session.v3_alarm;重启丢 session 保守重置)。

    - ``recent_losses``:(全局节点号, 战斗净掉血)滚动窗——窗口单位=
      **连续战斗节点**(W51 语义修复:战斗节点计数器,非日历轮;点4
      「3 轮内」按战斗语义读作「最近 3 个战斗节点」);②最近 3 个
      战斗节点累计 ≥20(急性)/③最近 5 个战斗节点累计 ≥30(慢性漂移);
      **跨位面重置**(慢性臂横跨整个位面的按轮漂移根修);
    - ``consec_battle_fails``:①连续 2 场战斗失败;
    - ``alarm_battles``:处置梯度计时——报警激活期间累计喂入的战斗
      节点数(=1 → ①自然补强窗内;>1 → 窗耗尽未达标;报警解除清零);
    - 非战斗节点:不入窗、不清臂(点4 冻结语义)。
    """

    recent_losses: deque = field(default_factory=lambda: deque(maxlen=5))
    consec_battle_fails: int = 0
    alarm_battles: int = 0
    plane: int | None = None

    _BATTLE_NODES: frozenset[str] = frozenset(
        {'battle', '普通战斗', 'boss', '精英', '遭遇'})

    def record(self, node_type: str, hp_before: int, hp_after: int,
               t: int, plane: int | None = None) -> None:
        """on_round_end 喂入(结算真值;hp_after 为空帧跳过)。

        ``plane`` 传入时做跨位面重置判定(位面变更 → 三臂全清,
        不带旧位面的掉血趋势进新位面)。
        """
        if plane is not None and plane != self.plane:
            self.plane = plane
            self.recent_losses.clear()
            self.consec_battle_fails = 0
            self.alarm_battles = 0
        if node_type not in self._BATTLE_NODES:
            return   # 非战斗节点不计入也不重置任何一臂
        loss = max(0, hp_before - hp_after)
        self.recent_losses.append((t, loss))
        # ①连续失败代理:单场净掉血 ≥10 视为该节点实际打输(r246 口径;
        # W51 标注:「失败」是代理语义——高难打赢但大掉血场也计入,
        # 阈值属 sim 校准域,实机语料积累后校准)
        if loss >= 10:
            self.consec_battle_fails += 1
        else:
            self.consec_battle_fails = 0
        # 处置梯度①计时(S4 上界 1 轮):报警激活期间累计的战斗节点数
        if self.alarm_active():
            self.alarm_battles += 1
        else:
            self.alarm_battles = 0

    def alarm_active(self) -> bool:
        """三臂并集:①连续 2 场战斗失败;②最近 3 个战斗节点累计 ≥20;
        ③最近 5 个战斗节点累计 ≥30(阈值=设计推断,sim 校准,W10 摆动域)。"""
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
            # 不是 ALL IN 的触发——报警态下此窗开通是位面末授权,
            # 非「报警触发」)
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
    - 掉血报警(三臂):**报警不是触发**——处置梯度①自然补强窗
      (mode=economy)→②弃息 D 保血(war+硬节点放行 refresh);
      不动地板;ALL IN 仅当位面末(``plane_last_battle``,[18] 授权);
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
        # 处置梯度三步(strategy_v4 点4 S4;W51 补全时限与血边际):
        # ①自然凑羁绊——上界 1 个战斗节点(报警激活后首个战斗节点窗
        # 内 mode=economy,不弃息,给自然补强机会);
        # 窗耗尽未达标(alarm_battles>BLOOD_GRADIENT_NATURAL_BATTLES)
        # 或血边际已低([19]② hp<BLOOD_MARGIN_LOW_HP——血 <40 本就是
        # 报警档,梯度直接生效)→ ②弃息 D 保血(war+硬节点放行
        # refresh,点12 保血通道);
        # ③位面末最后一战 ALL IN(allin=plane_last_battle——[18]/点4
        # 授权;报警不是 ALL IN 的触发,位面末才是)。
        # [19]③「来牌顺不顺」未消费(欠账声明:定性变量,sim 层无载体,
        # 挂实机语料后补)。
        hard = node in ('encounter', 'boss', '遭遇')
        escalated = (tracker.alarm_battles > BLOOD_GRADIENT_NATURAL_BATTLES
                     or state.hp < BLOOD_MARGIN_LOW_HP)
        if escalated:
            return DisciplineView(
                coverage='blood_alarm', mode='war',
                allin=plane_last_battle(state, session),
                allow_refresh_in_war=hard)
        return DisciplineView(
            coverage='blood_alarm', mode='economy',
            allin=plane_last_battle(state, session))
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


def _line_protect_set(comp) -> set[str]:
    """意向线正料保护集(核心+共享+替班+引擎件;carry_gate 与金不足
    变现通道共用单一源——防两处各自派生漂移)。"""
    protect = set(comp.core_chars) | set(comp.shared_chars)
    for p in comp.substitute_plan:
        if p.get('替班者'):
            protect.add(p['替班者'])
    protect |= engine_char_names()
    return protect


def carry_gate_actions(state: GameState, session: StrategySession,
                       registry: DecisionV2Registry,
                       bought: set[str] | None = None) -> list:
    """carry 腾位门(v1 ADR-0280 r416 移植;语义重接):

    v1:carry=``line_of(locked_line).carry``;v2:carry=意向核心
    (``intention_core`` of COMP_LIBRARY v2 锁定套)。门(全过才腾位):
    ①收益域 P1 r≤carry_gate_max_round;②意向锁定且核心在店、未持有、
    金足(不破 war 地板);③bench 满(≥9)且无直接可卖件(保护集外
    且非近轮种子);④降保护集挑 off-line 价值最低件(弱序:非保护 >
    副本冗余/超上限;3合1 完整份不动;r416b absent_mergeable
    [上场份缺席的 ≥2 加权副本]弱序等同超上限冗余=最弱级;种子
    2 轮窗件单列兜底——唯一可卖=种子时豁免放行防 carry 死锁,
    仍选最弱,ADR-0289 §5 年龄保护在降保护集阶段让位于 carry);
    ⑤卖出件入同轮已卖集不回买。

    保护集口径(W51 声明修正,与实际实现对齐):**意向线正料派生**
    = core_chars ∪ shared_chars ∪ 替班者 ∪ 引擎件(engine_char_names)
    ——非 ``session.v3_hoard`` 全集(后者含跨线骨架/装备材料,口径
    更宽);跨线囤件不在保护集,可被降级卖出腾位买核心。
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
    if bench_occupied(bench) < BENCH_CAPACITY:
        return []   # 未满 → 常规买通道可达(ADR-0316:容量=占用数)
    # 保护集 = 意向线核心+共享+替班(正料不卖)+引擎件(种子)
    protect = _line_protect_set(comp)
    # ③ 直接卖通道可用 → 不降保护集
    board_factions = set(state.board.keys())
    for b in bench:
        if (b is not None and b.char_id and b.char_id not in protect
                and b.faction not in board_factions
                and not round_sell_blocked(b, state, session)
                and not seed_age_blocked(b, state, session)):
            return []
    # ④ 降保护集:off-line 价值最低件
    # r416b absent_mergeable:该角色上场份缺席(deployed 无同名)且
    # 架内加权副本 ≥2 → 「合成份缺席场」冗余——纯 bench 合成素材,
    # 卖 1 份仍留副本,弱序等同超上限冗余(最弱级)。
    # (W51 适配说明:v1 原条件「carry 在场」与本门②的「carry 未持有」
    # 前置互斥=死码;按 r416b 意图(缺席场的冗余副本)改判「该角色
    # 上场份缺席」,依据 ADR-0314。)
    deployed_names = {getattr(d, 'char_id', '') for d in state.deployed or []}
    cands: list[tuple[tuple, int, object]] = []
    # 种子 2 轮窗(ADR-0289 §5)候选单列:bench 真满且无非种子可卖时
    # 兜底放行(仍选最弱)——不腾则 carry 死锁,豁免让位给 carry
    # (v1 _seed_cands 同式移植,W51 补)
    seed_cands: list[tuple[tuple, int, object]] = []
    for i, b in enumerate(bench):
        if b is None or not b.char_id or b.char_id == carry:
            continue
        if round_sell_blocked(b, state, session):
            continue
        cp = star_weighted_copies(b.char_id, state)
        if cp == 3:
            continue   # 3合1 完整份不腾
        absent_mergeable = (b.char_id not in deployed_names and cp >= 2)
        key = (b.char_id in protect,
               0 if (cp > 3 or absent_mergeable) else 1,   # 冗余最弱
               cp)
        if seed_age_blocked(b, state, session):
            seed_cands.append((key, i, b))
            continue
        cands.append((key, i, b))
    if not cands:
        cands = seed_cands   # 唯一可卖=种子:carry 死锁豁免(仍选最弱)
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


# ===== 金不足变现通道(压库件凑金;leader 追加 2026-08-25) =====

#: 变现通道辖的买侧标签(守卫②:不为非目标件变现——只有更高优先级
#: 购买才配动用压库资产:目标件三标签+引擎件+插件;pair/copy/
#: bond_fallback 凑数凑对类与 refresh/levelup 不辖)
LIQUIDITY_BUY_TAGS: frozenset[str] = frozenset({
    'line_carry', 'line_opportunistic', 'bridge_core',
    'engine_seed', 'plugin',
})


def liquidity_actions(state: GameState, session: StrategySession,
                      registry: DecisionV2Registry,
                      scored: list[tuple]) -> list:
    """金不足变现通道(压库件=「活期存款」,双重身份的收益兑现侧)。

    设计依据:压库件占池(买入动机)之外还是可变现资产——金不足时
    卖压库件不是损失,是压库策略的收益兑现。现状缺口:gold_short
    直接拒绝购买,无主动变现路径。

    流程:层3 分数序里选**最高分的金不足优先买**(gold-cost<地板),
    检查 bench 可变现资产——卖件序(strategy_v4 点5 的通道内简化):
    净0 件(1星/1费,全额退)最先 → 低费散件 → 升星沉淀件最后
    (同档按费升序);变现到够则同轮顺序动作组 [Sell…, Buy] 执行
    (卖先于买,序保证金到位)。

    守卫:
    - ②不为非目标件变现:只辖 ``LIQUIDITY_BUY_TAGS`` 的金不足买;
    - 保护集(``_line_protect_set``,意向线正料+引擎件)不卖——
      卖的是压库件不是正料;无锁定意向时仅引擎件受护;
    - 同轮已买(r408)/种子年龄窗(ADR-0289 §5)/3合1 完整份不动;
    - 变现不足额时**整体放弃**(不半途而废卖一半);
    - 每轮最多救援一笔(最高分金不足买)。

    边界(声明):绕过层4 仲裁直发(carry_gate 同模式)——层4 工作
    态不感知变现金,对同轮其余候选保守(可能漏接次优先买,可接受);
    买候选的 copies_cap/同名互斥由生成期保证。
    """
    from sr_od.application.currency_war.decision_v2.arbiter import (
        _active_floor,
    )
    floor = _active_floor(state, session, registry)
    target = None
    for cand, val, _bd in sorted(scored, key=lambda t: -t[1]):
        if val <= 0:
            continue
        a = cand.action
        if cand.tag not in LIQUIDITY_BUY_TAGS \
                or not isinstance(a, BuyCard):
            continue
        if a.card.name in (getattr(session, 'v2_round_sold', None) or ()):
            continue   # r408:同轮已卖不回买
        if state.gold - (a.card.cost or 3) < floor:
            target = (cand, a.card.cost or 3)
            break
    if target is None:
        return []
    cand, cost = target
    shortfall = floor + cost - state.gold
    if shortfall <= 0:
        return []
    ist = getattr(session, 'v3_intention', None)
    comp = None
    if isinstance(ist, IntentionState) and ist.phase == 'locked':
        from sr_od.application.currency_war.cw_comps import get_comp
        comp = get_comp(ist.locked_comp)
    protect = _line_protect_set(comp) if comp is not None \
        else set(engine_char_names())
    buy_name = cand.action.card.name
    sellable: list[tuple[tuple, int, object, int]] = []
    for i, b in enumerate(state.bench or []):
        if b is None or not b.char_id or b.char_id == buy_name:
            continue
        if b.char_id in protect:
            continue
        if round_sell_blocked(b, state, session) \
                or seed_age_blocked(b, state, session):
            continue
        if star_weighted_copies(b.char_id, state) == 3:
            continue   # 3合1 完整份不动
        ch = CHARACTERS.get(b.char_id)
        if ch is None or not ch.cost:
            continue   # 未知费级回金不可估,不入变现序
        star = getattr(b, 'star', 1) or 1
        refund = sell_refund(star, ch.cost)
        net0 = refund >= ch.cost
        key = (0 if net0 else 1, ch.cost, star)
        sellable.append((key, i, b, refund))
    sellable.sort(key=lambda s: s[0])
    sells: list = []
    got = 0
    for _key, idx, _b, refund in sellable:
        if got >= shortfall:
            break
        sells.append(SellBench(bench_idx=idx, income=refund))
        got += refund
    if got < shortfall:
        return []   # 变现不足额 → 整体放弃(不卖一半)
    log.info('[cw][d2][liquidity] r%d 变现 %d 件凑金 %d 买 %s(%s)',
             state.round_num, len(sells), shortfall,
             buy_name, cand.tag)
    for s in sells:
        nm = state.bench[s.bench_idx].char_id
        if nm:
            session.v2_round_sold.add(nm)   # r408 对称臂(原索引读
            # state.bench——与发射序无关:bench_idx 是生成期原索引,
            # 本函数不 mutate state)
    # ADR-0316 槽位模型下 SellBench 置 None 不移位,任意发射序零漂移
    # ——旧降序重排(紧缩表 pop 左移的症状补丁)已删,发射序 = 弱序选择序。
    return [*sells, BuyCard(cand.action.card, reason='d2_' + cand.tag)]
