"""决策框架 v2 纪律族(载体批 W35;自旧 line_strategy 移植+语义重接,
ADR-0336 后 line_strategy 已删,本包为唯一纪律族)。

**单一源**:`.debug/temp/currency_war/cw_dev/deep_read/strategy_v4.md` 点4(掉血
报警三臂/处置梯度时限)/点7(血线分级动作侧/位面末 ALL IN 限定)/点12(保血通道/
奖励关三态护栏)+ 裁决终版「第三选项」(纪律族移植,locked_line 派生改意向分层
输入——本模块**不 import** 线库/桥池,方向输入一律是
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
- catchup(_catchup_actions/E5/E6)→ **已随 W126/ADR-0349 退场**(用户
  2026-08-25 裁决 F6/Q4:人口落后=阵容没上满的表现——通道 2 人口位
  ([33])+通道 4 概率等级窗([3])+EV 总账涌现承接;兜底局由 form_score
  按上场计算承接「人口别落后」的观察);
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

常量值镜像旧 line_strategy 同名初值(地板族);注册表化后独立演进
(旧两臂 A/B 语义随 ADR-0336 结束)。
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

# ===== 纯谓词族(v1 移植;不依赖线库/桥池,ADR-0336 后无旧件) =====


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
    不进可卖集(跨轮窗;同轮 ≥2 份=3合1 素材语境豁免)。

    W88(ADR-0339 件3):cnt≥2 豁免加**实际持有对账**(star_weighted_
    copies≥2)——采纳处登记可能在同轮重复计数(采纳后被执行层否决的
    买入也留痕,seed16 姬子·启行单买 cnt=2 实证),幻影 cnt 会静默解除
    种子保护 → 买/卖互踩;以「真持有 ≥2 份」为素材语境判据。
    """
    name = getattr(bc, 'char_id', '')
    if not name or session is None:
        return False
    rec = (getattr(session, 'v2_seed_bought', None) or {}).get(name)
    if rec is None:
        return False
    key, cnt = rec
    if key[0] != state.plane:
        return False
    if not 0 <= state.round_num - key[1] <= 2:
        return False
    if cnt < 2:
        return True
    # cnt≥2:素材语境豁免仅当**真持有** ≥2 份;幻影计数(登记重复/
    # 执行层否决留痕)不解除保护
    return star_weighted_copies(name, state) < 2


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
    None = 无方向信息(旧载体垫片已随 ADR-0336 删除——生产恒走意向源)。
    """
    ist = getattr(session, 'v3_intention', None)
    if ist is not None and isinstance(ist, IntentionState) \
            and ist.phase == 'locked' and ist.locked_comp:
        from sr_od.application.currency_war.cw_comps import get_comp
        comp = get_comp(ist.locked_comp)
        if comp is not None:
            return set(comp.form_tiers) | set(comp.sub_tiers)
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
    # 意向锁定=意向线主/副档羁绊(旧载体 locked_line 垫片已删,
    # ADR-0336——生产恒走意向源)。
    ist = getattr(session, 'v3_intention', None)
    has_direction = (
        ist is not None and isinstance(ist, IntentionState)
        and ist.phase == 'locked' and ist.locked_comp)
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

#: 25/40 两档并存口径(W52/S2 顺手 docstring;两线不是二选一):
#: - **25 = 应急清仓线**(``registry.emergency_hp``):hp≤25 触发应急
#:   覆盖态(rebirth 地板 20,层2 应急过滤,危机囤金态)——低于此线
#:   已不是「报警」而是「应急」,处置=清仓止损;
#: - **40 = 报警降档线**(``BLOOD_MARGIN_LOW_HP``):hp<40 使掉血报警
#:   的处置梯度跳过①自然补强窗直入②弃息 D 保血(war+硬节点放行
#:   refresh)——报警语义([18] hp 低是运营质量报警),不触发 ALL IN。
#: 两线并存:报警(40 线)是处置梯度切换的加速条件,应急(25 线)是
#: 覆盖态触发;补偿机制(ADR-0326)只消费资源门槛事件,两线都只作
#: 辖域授权条件,不是补偿触发器。


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
      'mode'(判读/遥测锚点;追赶态 'catchup' 已随 W126/ADR-0349 退场);
    - ``mode``:'war'|'economy'(filters/interest_rule 消费);
    - ``allin``:位面末最后一战([18] 限定)——**唯一**清零地板的路径;
    - ``allow_refresh_in_war``:保血通道(点12)——报警+硬节点放行 refresh
      (remediation S2 消费;层2 的 war 标签集已含 refresh,W126/ADR-0349
      「war 滤 refresh」废除——本字段只剩补偿辖域语义);
    - ``war_floor_override``:boss_breaker 破息窗地板(v1 r278/r308 EV 移植)。
    """

    coverage: str
    mode: str
    allin: bool = False
    allow_refresh_in_war: bool = False
    war_floor_override: int | None = None

    def arbiter_registry(self, registry: DecisionV2Registry
                         ) -> DecisionV2Registry:
        """层4 仲裁用注册表视图(地板按纪律调整;评分仍用原表)。"""
        reg = registry
        if self.allin:
            # [18] 位面末最后一战 ALL IN:地板全清零(唯一路径;hp 报警
            # 不是 ALL IN 的触发——报警态下此窗开通是位面末授权,
            # 非「报警触发」)
            reg = replace(reg, interest_floor=0, war_floor=0,
                          rebirth_floor=0, boss_floor=0)
        elif self.war_floor_override is not None:
            reg = replace(reg, war_floor=self.war_floor_override)
        return reg


def boss_window_active(state: GameState, session: StrategySession,
                       registry: DecisionV2Registry) -> bool:
    """boss 破息窗统一口径(W113 §8-2;W119/ADR-0347)。

    主判据=**节点图**:node_type ∈ boss_round_node_types(boss 节点)。
    轮数口径**全仓只在此处保留**,且仅作 node_type 缺读兜底:P1 位面末
    r≥boss_window_fallback_round(9)且节点类型不可读 → 按 boss 窗处理
    (P1 末节点恒为 boss 的节点图先验)。

    旧双口径收编说明:discipline 旧「P1 r≥5 遭遇预备窗」(无论节点
    类型一律 war)与 arbiter/remediation 旧「P1 r≥9」三处轮数口径
    一次收进本函数——节点图可读且非 boss 时不再按轮数入窗(W115-B2
    审计:轮数代理是 boss 临近的双口径漂移源)。
    消费点:arbiter._active_floor/_round_state_dims/interest_rule/
    boss_levelup_ban、remediation._compensate_slot、本模块 assess_
    discipline。
    """
    node = getattr(session, 'node_type_current', None) or state.node_type or ''
    if node:
        return node in registry.boss_round_node_types
    return (state.plane == 1
            and state.round_num >= registry.boss_window_fallback_round)


def _hard_node(state: GameState, session: StrategySession) -> bool:
    """硬节点分类(掉血风险节点;W119/ADR-0347 单一源)。

    = encounter/boss/遭遇 ∪ 普通战斗且位面内剩余 ≤3(boss 临近)。
    消费点:_streak_floor(连胜 EV 地板)与 assess_discipline 保血
    通道的 hard 判定(两处同源,禁散写)。

    **扑满节点(过热局 reward)不辖**(ADR-0348 口述定谒 2026-08-26:
    扑满关不掉血——真损失是「打不过没奖励」,处置=确保伤害阵容去拿
    奖励,**不深花保血**)——「低危战斗」的战斗向买/刷开放在 scoring
    侧(refresh 轮界豁免,`ev.reward_node_is_battle`),地板不降。
    """
    node = getattr(session, 'node_type_current', None) or state.node_type or ''
    if node in ('encounter', 'boss', '遭遇'):
        return True
    remaining = max(0, NODES_PER_PLANE - state.round_num)
    return node in ('battle', '战斗') and remaining <= 3


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
    remaining = max(0, NODES_PER_PLANE - state.round_num)
    tier_now = streak_gold(streak) if streak >= 2 else 0
    ev_reward = (tier_now - 1) * remaining      # 断了回到 1 档
    ev_interest = 0.25                           # 一次性息损失
    hard_node = _hard_node(state, session)
    if streak >= 2 and hard_node and ev_reward > ev_interest:
        return 5
    return base_floor


def assess_discipline(state: GameState, session: StrategySession,
                      registry: DecisionV2Registry) -> DisciplineView:
    """纪律族评估(覆盖态优先序:应急 > 掉血报警 > boss_breaker > 模式;
    追赶态已随 W126/ADR-0349 退场——人口落后由通道 2/4+EV 涌现承接)。

    语义重接要点(strategy_v4 点4/点7/点12):
    - 应急(hp≤emergency_hp):rebirth 地板由层4 ``_active_floor`` 分派
      (is_emergency 优先),此处只标 coverage/mode;
    - 掉血报警(三臂):**报警不是触发**——处置梯度①自然补强窗
      (mode=economy)→②弃息 D 保血(war+硬节点放行 refresh);
      不动地板;ALL IN 仅当位面末(``plane_last_battle``,[18] 授权);
    - boss_breaker:boss 节点(boss_window_active 统一口径,W119/ADR-0347:
      节点图为主,轮数只作 node_type 缺读兜底),war 模式+破息地板 10
      (连胜 EV 5);
    - ALL IN:仅 ``plane_last_battle``([18] 位面末最后一战限定)。
    """
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
        # hard=硬节点分类单一源(_hard_node;扑满守卫 ADR-0348 在彼接线:
        # 过热局 reward 节点按战斗节点处理→保血通道辖)
        hard = _hard_node(state, session)
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
    if boss_window_active(state, session, registry):
        floor = _streak_floor(state, session, registry, registry.boss_floor)
        return DisciplineView(
            coverage='boss_breaker', mode='war',
            allin=plane_last_battle(state, session),
            war_floor_override=floor)
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
    # ④ 降保护集:off-line 价值最低件(统一弱序 sell_priority_key,
    # ADR-0327——absent_mergeable/超上限归 redundancy=0;加权副本≥2
    # 的 3合1 进行中素材由键统一挡,AD9-2-3)
    cands: list[tuple[tuple, int, object]] = []
    # 种子 2 轮窗(ADR-0289 §5)**绝对不让位**(W88/ADR-0339 件3 裁决):
    # 旧版 W51「carry 死锁豁免」在唯可卖=新鲜种子时仍卖种子买 carry
    # ——买侧见即买 engine_seed 与卖侧 carry_gate 互踩(seed16 姬子·启行
    # r4 买 r6 卖 r7 再买,检查器 0 容忍与设计豁免矛盾)。裁决:窗口内
    # 种子赢过 carry 腾位(卖种子换 carry 的期望=再遇窗口双倍化,[22]③
    # 弃购代价),本轮不腾、carry 延后——窗口 ≤2 轮自然解锁,死锁有界。
    for i, b in enumerate(bench):
        if b is None or not b.char_id or b.char_id == carry:
            continue
        if seed_age_blocked(b, state, session):
            continue
        key = sell_priority_key(b, state, session, protect, registry)
        if key is None:
            continue   # r408 同轮已买/加权副本≥2(AD9-2-3)/未识别统一挡
        cands.append((key, i, b))
    if not cands:
        return []   # 唯一可卖=窗口内种子:carry_gate 让位延后(上注)
    cands.sort(key=lambda c: c[0])
    _k, idx, weakest = cands[0]
    refund = None
    ch = CHARACTERS.get(weakest.char_id)
    if ch is not None and ch.cost:
        refund = sell_refund(getattr(weakest, 'star', 1) or 1, ch.cost)
    log.info('[cw][d2][carry-gate] r%d 腾位:降保护集卖 %s 买意向核心 %s',
             state.round_num, weakest.char_id, carry)
    register_round_sold([weakest.char_id], state, session)   # r408 对称臂
    # ADR-0328:腾位买即登记同轮已买集(登记点=动作采纳处,非 decide_prep
    # 尾)——carry_gate 先于 arbitrate 执行,不登记则同趟 arbitrate 内
    # SELL carry(段首旧副本)候选的 r408 守卫仍读空已买集,双双过。
    register_round_bought([carry], state, session)
    return [SellBench(bench_idx=idx, income=refund),
            BuyCard(carry_card, reason='carry_gate')]


# ===== 金不足变现通道(已收编,W52/ADR-0326)=====
# liquidity_actions + LIQUIDITY_BUY_TAGS 已删——语义收编进
# decision_v2/remediation.py 的 _compensate_gold(通用回连机制,
# 触发源从层3 预测 state.gold 换层4 实际 working.gold);
# remedy_buy_tags(含 carry_gate)迁 registry。既有测试锁语义化
# 重写见 test_cw_w35_decision_v2_carrier.py(liquidity → 补偿器)。

# ===== S5 统一卖件弱序(W52/ADR-0327;纪律族单一源)=====
# 四卖件通道(carry_gate ④/两补偿器/层3 off_target 评分)统一消费
# sell_priority_key——禁各通道手搓弱序(双源漂移温床,设计 §4)。


def _sell_expected_loss(cost: int, registry: DecisionV2Registry) -> float:
    """[22]③ 再遇代价 × W4 终局贯穿率(点5 键静态近似;ADR-0327)。

    loss = remeet_rounds(cost) × through_rate(cost)——费级表在
    registry(remeet_window_rounds/through_rate,sim 校准域)。
    """
    remeet = registry.remeet_window_rounds.get(cost, 30)
    through = registry.through_rate.get(cost, 0.15)
    return remeet * through


def sell_priority_key(bc, state: GameState,
                      session: StrategySession,
                      protect: set[str] | None = None,
                      registry: DecisionV2Registry | None = None,
                      ) -> tuple | None:
    """统一卖件弱序键(升序=最先卖;None=不可卖,调用方跳过)。

    键结构(逐位比较;前段=既有豁免/守卫的复合,后段=点5 期望损失键):
      (in_protect,          # 保护集外最先进(保护集成员垫底)
       redundancy,          # 0=冗余最弱(超上限/absent_mergeable,
                            #   carry_gate ④ 同档),1=常态
       expected_loss,       # 再遇代价×终局贯穿率(点5 键;静态近似)
       net0_rank,           # 净0 件(1星/1费,全额退)置 0 最先
       cost, star)          # 同档按费升序/星升序(确定性兜底)

    守卫(复用既有谓词,不重定义;任一命中 → None):
      round_sell_blocked(r408 同轮已买)/seed_age_blocked(ADR-0289 §5
      年龄窗;种子单列兜底逻辑由 carry_gate ④/补偿器保留在外——
      豁免是专属时序,键不管)/未识别(空名)/**加权副本 ≥2**(3合1
      进行中素材与完整份,AD9-2-3/ADR-0327——防补偿/腾位通道拆
      合成进度)。

    槽位模型(ADR-0316):入参 bc=BenchChar(None 槽由调用方枚举时
    跳过);返回键不含槽位号——发射时由调用方带槽位号(置 None 语义)。
    ``registry`` 可选(期望损失表;缺省用模块默认注册表——A/B 注入
    时调用方显式传)。
    """
    from sr_od.application.currency_war.decision_v2.registry import (
        DEFAULT_REGISTRY,
    )
    reg = registry if registry is not None else DEFAULT_REGISTRY
    name = getattr(bc, 'char_id', '') or ''
    if not name:
        return None    # 未识别(空名)
    if name not in CHARACTERS:
        return None    # 未识别(注册表外——费级/回金/合成进度不可估)
    if round_sell_blocked(bc, state, session):
        return None
    if seed_age_blocked(bc, state, session):
        return None
    if star_weighted_copies(name, state) >= 2:
        return None    # 3合1 进行中素材/完整份不卖(AD9-2-3)
    ch = CHARACTERS.get(name)
    cost = ch.cost if ch is not None and ch.cost else 3
    star = max(1, int(getattr(bc, 'star', 1) or 1))
    cp = star_weighted_copies(name, state)
    deployed_names = {getattr(d, 'char_id', '') for d in
                      (state.deployed or [])}
    absent_mergeable = (name not in deployed_names and cp >= 2)
    in_protect = 1 if (protect and name in protect) else 0
    redundancy = 0 if (cp > 3 or absent_mergeable) else 1
    loss = _sell_expected_loss(cost, reg)
    net0 = 0 if star == 1 else 1
    return (in_protect, redundancy, loss, net0, cost, star)


def sell_score_weight(cost: int,
                      registry: DecisionV2Registry) -> float:
    """卖分缩放权重(S5 评分侧;ADR-0327):w=sell_key_weight_scale×
    (1+min_loss)/(1+loss),封顶 1.0。

    净0 件(1费,min-loss 档)w=1、升星沉淀件(高再遇代价)w→小——
    只改同通道内卖件**相对序**,不改「卖不卖」的正分门槛
    (纯占位件 val=bias×w>0 仍可卖)。scale=1 即回退均一 bias(A/B)。
    """
    min_loss = min(_sell_expected_loss(c, registry)
                   for c in registry.remeet_window_rounds)
    loss = _sell_expected_loss(cost, registry)
    return min(1.0, registry.sell_key_weight_scale
               * (1.0 + min_loss) / (1.0 + loss))


def register_round_sold(names, state: GameState,
                        session: StrategySession) -> None:
    """卖出件入同轮已卖集(r408 对称臂;带轮键自校验,防跨轮误写)。

    四卖件通道统一走本 helper(设计 §4):carry_gate ④/两补偿器/
    arbiter 主循环(采纳处,ADR-0328)。
    """
    key = (state.plane, state.round_num)
    if getattr(session, 'v2_round_key', None) != key:
        return    # 轮键不匹配(跨轮误写防御;set 下轮重置)
    sold = getattr(session, 'v2_round_sold', None)
    if sold is None:
        session.v2_round_sold = sold = set()
    for n in names:
        if n:
            sold.add(n)


def register_round_bought(names, state: GameState,
                          session: StrategySession) -> None:
    """买入件入同轮已买集(r408 主臂;带轮键自校验,防跨轮误写)。

    ADR-0328 时序修复:登记点从 decide_prep 尾部(arbitrate 之后)
    前移到**动作采纳处**(同一事务域)——同趟 arbitrate 内先采纳
    BUY X 后,后续 SELL X(段首旧副本)候选的守卫立即可见
    (no_same_round_buy_sell 回归 96/400 的根因:r408 守卫读的是
    上一段已买集,同趟 buy+sell 双双过)。三买发射点统一走本
    helper:arbiter 主循环采纳/补偿趟受益买重发/carry_gate 腾位买。
    """
    key = (state.plane, state.round_num)
    if getattr(session, 'v2_round_key', None) != key:
        return    # 轮键不匹配(跨轮误写防御;set 下轮重置)
    bought = getattr(session, 'v2_round_bought', None)
    if bought is None:
        session.v2_round_bought = bought = set()
    for n in names:
        if n:
            bought.add(n)
