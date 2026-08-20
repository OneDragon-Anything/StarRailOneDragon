"""货币战争 · 策略 v2(LineStrategy;Phase A Day 9;redesign §5)。

**CwStrategy 具现**——继承 DefaultCwStrategy,只覆盖策略性钩子;
执行性钩子(球/箱/典籍/腾席链骨架/encounter/supply/megastar/
partner)全继承(r225 代码盘点的复用边界)。

架构(redesign §3,每节点决策=三查):
  查战力表(能不能过)→查线库(为谁积累)→规则集(具体动作)
  状态机(cw_phase_machine)承载模式滞回/应急/追赶/守卫。

覆盖的钩子(4 个):
  on_match_start    session 扩展态初始化
  on_round_end      感知质量门(抄 default:last_hp/streak)
  update_target     信号锁线+桥线选择
  decide_prep       四象限动作表

session 扩展态(累积态清单=r220 §5.5;重启丢失语义已声明):
  v2_state     状态机元组(cw_phase_machine.initial_state)
  locked_line  锁定线 id(None=未锁)
  bridge_id    当前桥(None=无)
"""
from __future__ import annotations

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war import cw_phase_machine
from sr_od.application.currency_war.cw_bridge_pool import (
    BRIDGE_POOL,
    BRIDGE_POOL_P2,
    pick_bridge,
)
from sr_od.application.currency_war.cw_line_library_v1 import (
    line_of,
)
from sr_od.application.currency_war.cw_performance import RoundOutcome
from sr_od.application.currency_war.cw_power_table import (
    COARSE,
    STRONG,
    check,
)
from sr_od.application.currency_war.cw_signal_lock import (
    check_core_signal,
)
from sr_od.application.currency_war.cw_state import (
    BuyCard,
    GameState,
    LevelUp,
)
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.strategies.default_strategy import (
    DefaultCwStrategy,
)

#: 应急 HP 绝对档(简版;Step 5 按形态分层标定——r216)
_EMERGENCY_HP: int = 25
#: 应急保留重生基数([18] 死亡螺旋修正)
_REBIRTH_FLOOR: int = 20
#: 利息地板(50 金息律——满息;「卡30」是慢 D 期的下限档,
#: 经济模式地板取 50,战力模式 30[S4:两档见 cw_economy._xp_gold_floor
#: 同语义,Phase A 简化先统一 50/30 两数])
_INTEREST_FLOOR: int = 50
_WAR_FLOOR: int = 30
#: 位面人口基线(r191 中位;追赶判定的参照)
_POP_BASELINE: dict[int, int] = {1: 5, 2: 7, 3: 9}


class LineStrategy(DefaultCwStrategy):
    """策略 v2:战力表+线库+桥线的四象限打法(redesign Phase A)。"""

    STRATEGY_ID = 'line_v2'
    STRATEGY_NAME = '线库策略 v2'
    AUTHOR = 'OneDragon'
    VERSION = '0.1'
    DESCRIPTION = '战力表查证+信号锁线+桥线兜底(redesign Phase A)'

    # ===== 生命周期 =====

    def on_match_start(self, state: GameState, session: StrategySession,
                       config) -> None:
        """扩展态初始化(状态机/锁线/桥)。"""
        session.v2_state = cw_phase_machine.initial_state()
        session.locked_line = None
        session.bridge_id = None

    def on_round_end(self, state: GameState, session: StrategySession,
                     config, obs: RoundOutcome) -> None:
        """感知质量门(继承 default 实证链)+战斗节点事件喂状态机。"""
        super().on_round_end(state, session, config, obs)
        ev = 'node_pass'
        # 位面边界权威判定(只 boss/遭遇查表)。
        # B1:node_type 实际值是中文(cw_performance 口径)——
        # 英文 'encounter' 永不命中=遭遇判定死码,已修。
        # N2:obs.plane 比 state.plane 权威(结算时位面可能已推进)
        if obs.node_type in ('boss', '遭遇') and session.locked_line:
            line = line_of(session.locked_line)
            if line is not None:
                ph = f'P{obs.plane or state.plane}'
                form = line.p2p3_forms.get(ph, '')
                if form:
                    pop = len(state.deployed)
                    lvl, _, mp = check(form, pop, ph, self._drive_of(session))
                    ok = lvl in (STRONG, COARSE) and abs(pop - mp) <= 2
                    ev = 'E1_strong' if ok else 'E1_miss'
        self._feed(session, ev)
        # B2:追赶接线——人口 vs 位面基线(r191:P1 3-5/P2 6-7/P3 9-10)
        pop = len(state.deployed)
        baseline = _POP_BASELINE.get(obs.plane or state.plane, 7)
        low = pop < baseline - 1     # 容差(基线是中位非硬线)
        cat = session.v2_state[2]
        if low and not cat and not session.v2_state[1]:
            self._feed(session, 'E5', pop_low=low)
        elif cat and not low:
            self._feed(session, 'E6')

    # ===== 战略层:信号锁线+桥线 =====

    def update_target(self, state: GameState, session: StrategySession,
                      config) -> None:
        """v2 战略层:锁线检查(先)+桥线选择(未锁时)。

        与 default 的 select_comp/maybe_pivot 完全不同——
        不做 comp 评分/分数涌现换线([23]:换线只走
        counter/降级显式路径,Phase A 只降级装置)。
        """
        if session.locked_line is None:
            r = check_core_signal(self._visible_names(state))
            if r.locked:
                session.locked_line = r.line_id
                self._feed(session, 'E7_lock')
                log.info('[cw][v2] 锁线 %s(核心卡 %s)',
                         r.line_id, r.matched_name)
                session.bridge_id = None   # 终审 S7:锁线清桥
        # 终审 S4:v2 部署判据线内件集合——伪 comp 写 target_comp
        # (deploy_bench L248/L340 读 target_comp.factions/core_chars;
        # plan._should_deploy 同。锁线后 carry/线内件成为部署
        # 一等公民,不再只按阵营集中)
        if session.locked_line is not None:
            line = line_of(session.locked_line)
            session.target_comp = (
                _LinePseudoComp.from_line(line) if line is not None else None)
        else:
            # 未锁线:桥线选择(重合度最高;phase 按当前位面)
            ph = 'P1' if state.plane == 1 else 'P2'
            bridge = pick_bridge(self._owned_names(state), ph)
            session.bridge_id = bridge.bridge_id if bridge else None
            session.target_comp = None

    # ===== 四象限动作表 =====

    def decide_prep(self, state: GameState, session: StrategySession,
                    config) -> list:
        """v2 备战计划:应急判定→象限动作(Phase A 简化范围)。"""
        self._ensure_state(session)
        # --- 应急(存量语义,简版 HP 档) ---
        if self._emergency(state) and not session.v2_state[1]:
            self._feed(session, 'E3')
        elif session.v2_state[1] and not self._emergency(state):
            # 应急恢复走 E8_restart(状态机 E4 是 no-op——终审 S1:
            # 原喂 E4 是接口错位,应急成吸收态)
            self._feed(session, 'E8_restart',
                       pop_low=self._pop_low(state, session))
            # E8 恢复后非应急侧含追赶分支(pop_low)或正常态
        emg = session.v2_state[1]
        cat = session.v2_state[2]
        if emg:
            return self._emergency_actions(state, session)
        if cat:
            return self._catchup_actions(state, session)
        if session.v2_state[0] == cw_phase_machine.MODE_ECONOMY:
            return self._economy_actions(state, session)
        return self._war_actions(state, session)

    # ===== 内部 =====

    @staticmethod
    def _ensure_state(session: StrategySession) -> None:
        """v2_state None 归一化(续跑/replay 路径未走 on_match_start
        的守卫——终审 B1:None 喂状态机解包炸)。"""
        if session.v2_state is None:
            session.v2_state = cw_phase_machine.initial_state()

    def _feed(self, session: StrategySession, ev: str,
              pop_low: bool = True) -> None:
        """喂事件。非确定集解包规则:
        E7_lock 保留当前 mode(锁线不改模式——开局锁线应攒钱);
        E2 换线取 war(主动求战力);E8(应急恢复路径)保守取 war。
        REJECT 保持原态+日志。"""
        self._ensure_state(session)
        st = session.v2_state
        ns = cw_phase_machine.step(st, ev, pop_low=pop_low)
        if ns == 'REJECT':
            log.debug('[cw][v2] 状态机拒事件 %s(守卫期/已访问),保持原态', ev)
            return
        if isinstance(ns, set):
            want_war = ev != 'E7_lock'
            ns = next(s for s in ns
                      if (s[0] == cw_phase_machine.MODE_WAR) == want_war)
        session.v2_state = ns

    @staticmethod
    def _drive_of(session: StrategySession) -> str:
        """B3:dot_fallback → 'unknown'(查表落最保守 ×2.0——
        兜底线战力判断从严;原映射 burst 是保守性倒挂)。"""
        line = line_of(session.locked_line) if session.locked_line else None
        if line is None:
            return 'unknown'
        if line.drive_type == 'dot_fallback':
            return 'unknown'
        return line.drive_type

    @staticmethod
    def _visible_names(state: GameState) -> list[str]:
        names = [c.name for c in (state.shop or []) if c.name]
        names += [b.char_id for b in (state.bench or []) if b.char_id]
        names += [d.char_id for d in (state.deployed or [])
                  if getattr(d, 'char_id', '')]
        return names

    @staticmethod
    def _owned_names(state: GameState) -> set[str]:
        s = {b.char_id for b in (state.bench or []) if b.char_id}
        s |= {d.char_id for d in (state.deployed or [])
              if getattr(d, 'char_id', '')}
        return s

    @staticmethod
    def _emergency(state: GameState) -> bool:
        return state.hp <= _EMERGENCY_HP

    def _emergency_actions(self, state: GameState,
                           session: StrategySession) -> list:
        """应急:利息让位保留重生基数([18]);买即战力。
        终审 N1:未识别卡(name='')不买。"""
        budget = max(0, state.gold - _REBIRTH_FLOOR)
        for card in (state.shop or []):
            if not card.name:
                continue
            if self._line_wants(card, state, session) \
                    and card.cost <= budget:
                return [BuyCard(card)]
        cards = sorted((c for c in (state.shop or []) if c.name),
                       key=lambda c: -c.cost)
        if cards and cards[0].cost <= budget:
            return [BuyCard(cards[0])]
        return []

    def _catchup_actions(self, state: GameState,
                         session: StrategySession) -> list:
        """追赶(简化版):升人口置顶。"""
        from sr_od.application.currency_war.cw_economy import xp_click_cost
        cost = xp_click_cost(state)
        if state.gold >= cost:
            return [LevelUp(cost)]
        return []

    def _economy_actions(self, state: GameState,
                         session: StrategySession) -> list:
        """经济:线内件(星级三档)+压缩(地板——终审 S2 修正:
        50 是满息后不乱花,不是 50 以下不发展;未满息期地板降 10
        [11]「金<20 1息档内购买不损息」精神)。"""
        actions: list = []
        floor = _INTEREST_FLOOR if state.gold >= _INTEREST_FLOOR else 10
        rem = state.gold
        for card in (state.shop or []):
            if rem - card.cost < floor:
                continue
            if self._line_wants(card, state, session):
                actions.append(BuyCard(card))
                rem -= card.cost    # 终审 S3:逐张扣减防预算漂移
        # 压缩(1费净0)
        bought = {id(a.card) for a in actions}
        for card in (state.shop or []):
            if card.cost == 1 and rem - 1 >= floor \
                    and id(card) not in bought:
                actions.append(BuyCard(card))
                rem -= 1
        return actions

    def _war_actions(self, state: GameState,
                     session: StrategySession) -> list:
        """战力:分层补强(线内件优先;地板仍保——战力≠panic)。
        终审 S3:逐张扣减预算。"""
        actions: list = []
        rem = state.gold
        for card in (state.shop or []):
            if rem - card.cost < _WAR_FLOOR:
                continue
            if self._line_wants(card, state, session):
                actions.append(BuyCard(card))
                rem -= card.cost
                if len(actions) >= 2:
                    break
        return actions

    def _line_wants(self, card, state: GameState,
                    session: StrategySession) -> bool:
        """星级三档购买判据(r201)——Phase A 简版:
        锁线→carry+opportunistic 档;未锁→桥线 fixed/core。"""
        if session.locked_line:
            line = line_of(session.locked_line)
            if line is None:
                return False
            if card.name == line.carry:
                return True
            return card.name in line.opportunistic_cards
        if session.bridge_id:
            pool = BRIDGE_POOL if state.plane == 1 else BRIDGE_POOL_P2
            for combo in pool:
                if combo.bridge_id == session.bridge_id:
                    return card.name in combo.fixed + combo.core
        return False

    @staticmethod
    def _pop_low(state: GameState, session: StrategySession) -> bool:
        """人口 vs 位面基线(E8 恢复的 pop_low 输入)。"""
        pop = len(state.deployed)
        baseline = _POP_BASELINE.get(state.plane, 7)
        return pop < baseline - 1


class _LinePseudoComp:
    """v2 线伪 comp(deploy_bench/plan target 判定桥接——终审 S4)。

    鸨子类型面 = deploy_bench 消费的属性:name/factions/core_chars/
    all_factions/char_positions(L248/L340 与 _should_deploy)。
    不继承 cw_comps.Comp(那要求 form_tiers 等全字段,与桥接
    最小面不符;消费侧只做属性访问)。
    """

    @staticmethod
    def _parse_tiers(form: str) -> dict[str, int]:
        """'列车同行4+护盾3' → {列车同行:4, 护盾:3}。"""
        tiers: dict[str, int] = {}
        for part in form.split('+'):
            name = part.rstrip('0123456789')
            num = part[len(name):]
            if name and num.isdigit():
                tiers[name] = int(num)
        return tiers

    def __init__(self, name: str, core_chars: list[str],
                 factions: list[str], form_tiers: dict[str, int]):
        self.name = name
        self.core_chars = core_chars
        self.factions = factions       # deploy L248 直读该属性
        self.char_positions: dict[str, str] = {}
        self.form_tiers = form_tiers   # shop._form_progress 读

    @property
    def all_factions(self) -> set[str]:
        return set(self.factions)

    @classmethod
    def from_line(cls, line) -> _LinePseudoComp:
        form = line.p2p3_forms.get('P2', '')
        factions = [part.rstrip('0123456789')
                    for part in form.split('+')]
        tiers = cls._parse_tiers(form)
        return cls(name=f'v2:{line.line_id}',
                   core_chars=[line.carry] + list(line.opportunistic_cards),
                   factions=[f for f in factions if f],
                   form_tiers=tiers)
