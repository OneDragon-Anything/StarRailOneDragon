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
#: 追赶触发的等级门(r232 实跑:level 3-5 期人口 3<基线-1 触发
#: 追赶 → 恒 LevelUp 不买牌——P1 早期人口低于基线是常态不是
#: 落后;只有等级已够高(人口上限打开)仍低于基线才算追赶)
_CATCHUP_MIN_LEVEL: int = 6


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
        # B2:追赶接线——人口 vs 位面基线(r232 修正:加等级门
        # _CATCHUP_MIN_LEVEL——P1 早期 pop<基线是常态,等级不够
        # 升人口也无意义(上限锁着),此时不进追赶;只有等级
        # 打开人口上限仍低于基线才算真落后[用户实跑观察])
        pop = len(state.deployed)
        baseline = _POP_BASELINE.get(obs.plane or state.plane, 7)
        low = (pop < baseline - 1
               and state.level >= _CATCHUP_MIN_LEVEL)
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
            # ⑧-1 修复:锁信号加「可负担/已持有」门——商店可见
            # 但买不起的 CARRY 不锁(对抗8:金<3 刷出姬子即锁线
            # → 之后只认名单卡,桥件停买,空过挨打)。
            # owned(bench+deployed)的名字不受此门(已在手)
            names = self._visible_names(state)
            affordable = self._affordable_cores(state)
            owned = self._owned_names(state)
            r = check_core_signal(
                [n for n in names if n in owned or n in affordable])
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
                _LinePseudoComp.from_line(line, state.plane)
                if line is not None else None)
        else:
            # ⑧-2 修复:DOT 兜底可达性——P2 起未锁线(无信号无桥)
            # 落兜底线(对抗8:core_cards=[] 使 check_core_signal
            # 永远返回不了 dot_fallback,「兜底」实为「不可达」)
            if state.plane >= 2:
                session.locked_line = 'dot_fallback'
                self._feed(session, 'E7_lock')
                log.info('[cw][v2] P%d 未锁线 → 落 DOT 兜底',
                         state.plane)
                line = line_of('dot_fallback')
                session.target_comp = (
                    _LinePseudoComp.from_line(line, state.plane)
                    if line is not None else None)
            else:
                # 未锁线:桥线选择(重合度最高;phase 按当前位面)
                ph = 'P1' if state.plane == 1 else 'P2'
                bridge = pick_bridge(self._owned_names(state), ph)
                session.bridge_id = bridge.bridge_id if bridge else None
                session.target_comp = None
        # B2(审计):双轨态/过渡框架写入——继承执行钩子
        # (_should_deploy 框架件分支/_free_bench_step)读这些
        # session 字段,v2 从不设 → 桥 carry 单卡囤 bench 不上场。
        # 语义:未锁线+P1 = 双轨期(过渡),framework = 桥名映射
        session.dual_track_phase = (session.locked_line is None
                                    and state.plane < 2)
        _BRIDGE_FW_MAP = {
            'xianzhou_dot': '仙舟', 'xianzhou_train': '仙舟',
            'train_dot': '列车',
            'train4_shield3': '列车',
        }
        session.transition_framework = (
            _BRIDGE_FW_MAP.get(session.bridge_id or '', ''))

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
        E2 换线取 war(主动求战力);E8(应急恢复)**保留当前 mode**
        (状态机 E8 的三个候选全保持 mode,按 war 过滤会
        StopIteration——模拟局 P0 实证;恢复后的追赶分支
        由 pop_low 在候选内选择)。
        REJECT 保持原态+日志。"""
        self._ensure_state(session)
        st = session.v2_state
        ns = cw_phase_machine.step(st, ev, pop_low=pop_low)
        if ns == 'REJECT':
            log.debug('[cw][v2] 状态机拒事件 %s(守卫期/已访问),保持原态', ev)
            return
        if isinstance(ns, set):
            cur_mode = st[0]
            if ev == 'E8_restart':
                # E8 三候选全保持 mode → mode 过滤剩 3 个,按
                # 集合迭代序随机挑 = 3/4 概率锁死应急(r235 模拟
                # 实证:PYTHONHASHSEED 0-3 四跑三 FAIL)。
                # 正确解包:排除「留在应急」分支,按 pop_low 选
                ns = next(s for s in ns
                          if s[0] == cur_mode and not s[1]
                          and s[2] == bool(pop_low))
            else:
                ns = next(s for s in ns if s[0] == cur_mode)
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
        """追赶(简化版):升人口置顶(模拟局观察#3 修复:留
        _WAR_FLOOR 地板——追赶不等于花光,人口未凑钱先攒着)。"""
        from sr_od.application.currency_war.cw_economy import xp_click_cost
        cost = xp_click_cost(state)
        if state.gold - cost >= _WAR_FLOOR:
            return [LevelUp(cost)]
        return []

    def _economy_actions(self, state: GameState,
                         session: StrategySession) -> list:
        """经济象限——显式动作序(r239 审计治本:升→刷→买→卖off→卖息;
        v2 覆盖 decide_prep 丢了 default plan() 的动作面,同类病
        已犯三次[r232/r236/r238],按序重排防第四个):
        ① 升人口(A1):溢出金放行——gold≥50+单击价时买 XP
           白嫖人口(r85 语义,default 实证修);
        ② 买(floor 三档 r236:满息 50/中间保档 g%10/低位 0);
        ③ 卖 off-target(A3):锁线后非保护 bench 件 cap 2/轮;
        ④ 卖散凑息(r238:组合跨档)。"""
        actions: list = []
        # ① 溢出金升人口(A1 修复;level_up_gate 单一源)
        from sr_od.application.currency_war.cw_economy import xp_click_cost
        xp = xp_click_cost(state)
        if state.gold - xp >= _INTEREST_FLOOR and xp > 0:
            actions.append(LevelUp(xp))
        if state.gold >= _INTEREST_FLOOR:
            floor = _INTEREST_FLOOR
        elif state.gold >= 10:
            floor = state.gold % 10    # 保息档,档内全花
        else:
            floor = 0                  # 低位金零息,全花
        rem = state.gold - (xp if actions else 0)
        for card in (state.shop or []):
            if rem - card.cost < floor:
                continue
            if not self._buy_guards(card, state, len(actions)):
                continue    # A4:副本/容量守卫
            if self._line_wants(card, state, session) \
                    or self._bridge_seed(card, state):
                actions.append(BuyCard(card))
                rem -= card.cost    # 终审 S3:逐张扣减防预算漂移
        # 压缩(1费净0)
        bought = {id(a.card) for a in actions if isinstance(a, BuyCard)}
        for card in (state.shop or []):
            if card.cost == 1 and rem - 1 >= floor \
                    and id(card) not in bought:
                if not self._buy_guards(card, state, len(actions)):
                    continue
                if self._line_wants(card, state, session) \
                        or self._bridge_seed(card, state) \
                        or self._pair_wants(card, state):
                    actions.append(BuyCard(card))
                    rem -= 1
        # ③ 卖 off-target(A3:锁线后死库存回收)
        actions.extend(self._sell_off_target(state, session, cap=2))
        # ④ 卖散凑息(r238)
        actions.extend(self._sell_for_interest(state, session))
        return actions

    @staticmethod
    def _maybe_refresh(state: GameState, session: StrategySession,
                       rem: int) -> list:
        """A2 修复:D 牌刷新——shop 无线内件可买时刷一次
        (「卡30慢D」的 D;免费额度优先,预算门,单轮一次)。"""
        from sr_od.application.currency_war.cw_state import RefreshShop
        # shop 里还有 line-wants 可买 → 不刷
        if state.shop:
            has_target = False
            for card in state.shop:
                if card.name and card.cost <= rem:
                    has_target = True
                    break
            if has_target:
                return []
        cost = state.shop_refresh_cost or 2
        if rem - cost < 10:      # 刷新后至少保 10(低位不刷)
            return []
        return [RefreshShop(cost)]

    def _sell_off_target(self, state: GameState,
                         session: StrategySession, cap: int = 2) -> list:
        """A3 修复:锁线后卖非保护 bench 件(死库存回收,
        default _sell_offline_for_focus 的 v2 版;保护集与
        _sell_for_interest 同源)。"""
        from sr_od.application.currency_war.cw_state import SellBench
        if session.locked_line is None:
            return []
        protect = self._protect_set(session)
        close = set(state.board.keys())
        out: list = []
        for i, bc in enumerate(state.bench):
            if len(out) >= cap:
                break
            if bc.char_id and bc.char_id not in protect \
                    and bc.faction not in close:
                out.append(SellBench(bench_idx=i))
        return out

    @staticmethod
    def _protect_set(session: StrategySession) -> set[str]:
        """保护集(卖出双路径共享:线 carry+opportunistic+桥名单)。"""
        protect: set[str] = set()
        for pool in (BRIDGE_POOL, BRIDGE_POOL_P2):
            for combo in pool:
                protect.update(combo.fixed + combo.core)
        if session.locked_line:
            line = line_of(session.locked_line)
            if line is not None:
                protect.add(line.carry)
                protect.update(line.opportunistic_cards)
        return protect

    def _sell_for_interest(self, state: GameState,
                           session: StrategySession) -> list:
        """卖散凑息:v2 版 _maybe_sell_interest(保护名单语义
        换 v2:桥 fixed/core+锁线 opportunistic 不卖)。"""
        from sr_od.application.currency_war.cw_state import (
            SellBench,
            sell_refund,
        )
        out: list = []
        cur_gold = state.gold
        if cur_gold >= _INTEREST_FLOOR or not state.bench:
            return out
        # 保护集:桥名单+锁线名单
        protect = self._protect_set(session)
        close = set(state.board.keys())    # 在场阵营不拆
        # 费用查注册表(_bench_char_cost 同语义;本地实现避免
        # 私有函数依赖)
        from sr_od.application.currency_war.cw_chars import CHARACTERS
        # 可卖候选(退款降序——大退款优先)
        candidates: list[tuple[int, int]] = []   # (refund, bench_idx)
        for i, bc in enumerate(state.bench):
            if bc.char_id in protect or bc.faction in close \
                    or not bc.char_id:
                continue
            ch = CHARACTERS.get(bc.char_id)
            cost = ch.cost if (ch and ch.cost) else 3
            refund = sell_refund(bc.star, cost)
            candidates.append((refund, i))
        if not candidates:
            return out
        candidates.sort(reverse=True)
        # 组合语义(r238):贪心累计退款,跨档即停。
        # default 单张判 28+1=29 永不触发;用户「卖两张凑30」
        # ——组合退款才是对的。上限 3 张防清空 bench。
        sold: list = []
        total = 0
        for refund, idx in candidates[:3]:
            new_total = total + refund
            if state.gold + new_total > _INTEREST_FLOOR:
                break                    # 超满息线不再加
            sold.append(SellBench(bench_idx=idx))
            total = new_total
            if (state.gold + total) // 10 > state.gold // 10:
                break                    # 组合跨档,最小卖出集
        # 全程没跨档(白卖)→ 撤销
        if sold and (state.gold + total) // 10 == state.gold // 10:
            sold = []
        return sold

    def _war_actions(self, state: GameState,
                     session: StrategySession) -> list:
        """战力:分层补强(线内件优先;地板仍保——战力≠panic)。
        终审 S3:逐张扣减预算。⑧-3:冷启动兜底(同 economy
        的 _pair_wants——P2 未锁线+war 不再恒 0 买)。
        r239:A2 刷新(shop 无线内件时 D 一次)+A4 守卫。"""
        actions: list = []
        rem = state.gold
        for card in (state.shop or []):
            if rem - card.cost < _WAR_FLOOR:
                continue
            if not self._buy_guards(card, state, len(actions)):
                continue
            if self._line_wants(card, state, session) \
                    or self._pair_wants(card, state) \
                    or self._bridge_seed(card, state):
                actions.append(BuyCard(card))
                rem -= card.cost
                if len(actions) >= 2:
                    break
        # A2:shop 无线内件可买 → D 一次
        if not any(isinstance(a, BuyCard) for a in actions):
            actions.extend(self._maybe_refresh(state, session, rem))
        return actions

    @staticmethod
    def _bridge_seed(card, state: GameState) -> bool:
        """r234 桥种子:未锁线时,卡∈当前位面任一桥的
        fixed∪core → 值得买(第一块砖;桥选择要求 owned 已有
        fixed 是鸡生蛋——种子件先入手才能成桥)。

        与 _pair_wants 的分工:seed 面向**引擎配方件**(三大
        桥的名单,买了就有方向),pair 面向任意同阵营凑对
        (散板止血)。"""
        if not card.name:
            return False
        pool = BRIDGE_POOL if state.plane <= 1 else BRIDGE_POOL_P2
        for combo in pool:
            if card.name in combo.fixed or card.name in combo.core:
                return True
        return False

    @staticmethod
    def _affordable_cores(state: GameState) -> set[str]:
        """⑧-1:当前金买得起的核心卡名(shop∩gold 门)。"""
        return {c.name for c in (state.shop or [])
                if c.name and c.cost <= state.gold}

    @staticmethod
    def _pair_wants(card, state: GameState) -> bool:
        """冷启动凑对(模拟局 P1 修复):卡与已持有(board+bench)
        同阵营 → 1 费可买(deploy 成对上场判据同源:
        同阵营 count≥2 上场凑过渡羁绊)。
        A5(spread 门):已有阵营 ≥3 时不再开新阵营——
        default M25 spread-lock 实证的防线。"""
        if not card.name or not card.faction or card.faction == '?':
            return False
        owned_factions = set(state.board.keys())
        for b in (state.bench or []):
            if b.faction and b.faction != '?':
                owned_factions.add(b.faction)
        if card.faction not in owned_factions \
                and len(owned_factions) >= 3:
            return False    # A5:阵营上限
        return card.faction in owned_factions

    @staticmethod
    def _buy_guards(card, state: GameState,
                    planned_buys: int) -> bool:
        """A4(审计):买牌守卫——同名副本 ≤3(3合1 上限,
        第4张纯浪费)+ bench 容量(已提案数计入)。"""
        if not card.name:
            return False
        copies = sum(1 for b in (state.bench or [])
                     if b.char_id == card.name)
        copies += sum(1 for d in (state.deployed or [])
                      if getattr(d, 'char_id', '') == card.name)
        if copies >= 3:
            return False
        # bench 容量:9 槽(保守 8 留合成空间)
        return len(state.bench or []) + planned_buys < 8

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
        # B1(审计+实跑实证 22:59「no attribute level_plan」):
        # 继承链(default 钩子/cw_plan/level_up_gate)按真 Comp
        # 消费的完整属性面——逐个 grep 消费点补齐,防下一个
        # AttributeError
        self.key_equips: list[str] = []            # decide_box_card/装备转移
        self.flex_factions: list[str] = []         # all_factions 外的弹性
        self.transition_chars: list[str] = []      # 卖出保护(打工牌)
        self.shared_chars: list[str] = []          # 转型共享
        self.level_plan: dict = {}                 # level_up_gate 读
        self.strength: str = 'S'
        self.form_difficulty: str = 'medium'
        self.early_power: str = '中'
        self.countered_by_bosses: list[str] = []
        self.mechanic_attributes: list[str] = []
        self.typical_form_round: int = 5
        self.version_tag: str = 'v2'
        self.plaza_carry: str = core_chars[0] if core_chars else ''
        self.weak_planes: tuple = ()

    @property
    def all_factions(self) -> set[str]:
        return set(self.factions)

    @classmethod
    def from_line(cls, line, plane: int = 1) -> _LinePseudoComp:
        """按当前位面选形态键(⑧-4:P1 期锁姬子不用 P2 的
        列车4+护盾3 当 target——那会把仙舟桥件判 off-target)。"""
        ph = 'P1' if plane <= 1 else ('P2' if plane == 2 else 'P3')
        form = line.p2p3_forms.get(ph) or line.p2p3_forms.get('P2', '')
        factions = [part.rstrip('0123456789')
                    for part in form.split('+')]
        tiers = cls._parse_tiers(form)
        return cls(name=f'v2:{line.line_id}',
                   core_chars=[line.carry] + list(line.opportunistic_cards),
                   factions=[f for f in factions if f],
                   form_tiers=tiers)
