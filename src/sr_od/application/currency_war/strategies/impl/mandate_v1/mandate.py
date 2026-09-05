"""cw4 骨架义务执行器(M1-M7)——IMPL_DESIGN §6.4-R 步4,§3 执行序。

单一 executor(每备战期骨架 pass),执行序(§3.1):
crisis_refresh_invariant(结构位)→ M5(开局板)→ dominance_buy
(M2 前置支配买入,mandate 邻位)→ M2(线成员买入)→ M4(腾席卖出)
→ M1(同帧部署)→ M3(升级整批)→ M1′(新人口位补部署)→ M6
(溢余转压库)→ M7(装备转移)。

四硬约束检查点(§3.2 唯一合法拦截集,封闭于①-④):①可负担(金域
g≥c,整批合计)/②席位(board/bench 槽位、等级 cap、同名同星≤1)/
③S 预留(整买目标预留金不被非 S 组成动作吃掉;辖 EV 买入面+M6+
dominance_buy)/④不可逆护栏(卖出线内/骨架/插件件不在骨架动作集)。
HP 不进任何检查点([39])。

M2→M4 重试环(R8-8/R11-5):买入遇 bench 满触发 M4 腾席,单帧闭环,
重试上限 ≤B=9(bench 容量注册表直读);M4 本次 0 发射 ⇒ 立即放弃
+遥测(不再重调)。dominance_buy/M6 席位失败=单帧单评不入环
(R12-2/R21-4)。

动作标记:骨架动作 mandate=True(遥测可分离统计;R14-4:mandate=
pass 归属单一语义)。

D-C44(共根组 1):部署/买入意图的输入契约 = **买入结算后 bench/cap/
dup 黑板全量现读**——本执行器每帧从 PrepObservation 现读重建,不以
跨帧快照/旧集为输入(与 dd-016 执行守卫互补:守卫管动作,估值管判断,
D-dup 谓词 = kernel.cw_deploy_logic.has_deployable 同源去重,dd-037 单一源)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.kernel.cw_economy import (
    clicks_to_next_level,
    in_must_spend_zone,
    xp_click_cost,
)
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    LevelUp,
    OpenShop,
    PrepAction,
    RunDeploy,
    RunEquip,
    SellBench,
)
from sr_od.application.currency_war.kernel.cw_state import (
    BENCH_CAPACITY,
    REFRESH_COST_BASE,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
    contracts,
    levelup,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import predicates
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.interest import (
    saturation_line,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_state import BenchChar, GameState
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )

# M1″ seam 门开关常量(唯一写点的值源;出处 = ADR-0530)。True = 开闸
# 置位态(现役缺省):两侧输入逐字段对齐证据(发射=决策帧黑板 vs 执行=
# last_state+SIFT 分轨,14 字段:9 对齐 / 4 分轨有据)+ fresh 生产写点
# 接线(shop.py 买入发射位 _emit_buy)两项开闸前置义务已兑付。回滚路径
# = 本常量写回 False——门关回即恢复现役 fail-closed(m1p_input_seam_
# pending 重新显影),fresh 载体 phase 键式跨轮自动失效,无持久状态。
M1P_SEAM_VERIFIED: bool = True

# bench 容量 B(R8-8 重试上限;kernel/cw_state.BENCH_CAPACITY 单一源,
# R196 症6:本地重定义删除,消费=import 符号名——第二源构成快照巧合双源)


@dataclass
class Emitted:
    """发射项(动作 + 标记面;mandate=pass 归属,R14-4)。"""

    action: PrepAction
    mandate: bool = True
    reason: str = ''
    funding_support: bool = False


@dataclass
class MandateFrame:
    """骨架 pass 输入帧(D-C44:黑板全量现读,每帧重建、零跨帧快照)。

    字段取值时机=生成期快照(从 PrepObservation 现读拷贝);坐标系:
    bench slot=物理槽位 1-9。``deploy_cap`` 真值源=``GameState.
    max_units()`` 派生链(R4 统一:level+宝钻、封顶 10,与 shop 侧
    同链单源;FIX_REVIEW_20260903 ②-1 双源漂移修复——旧观察复合
    ``obs.deploy_vacancy+len(deployed)`` 已废),state 缺读=None。
    """

    gold: int
    level: int
    bench: list[BenchChar]
    deployed: list[BenchChar]
    deploy_cap: int | None
    node_type: str | None
    stop_flag: bool
    k_members: tuple[str, ...]
    round_num: int = 1      # 位面内轮次(M5 开局板辖域=开局帧;GameState 直读)

    @property
    def bench_free(self) -> int:
        return max(0, BENCH_CAPACITY - len(self.bench))

    @property
    def deploy_vacancy(self) -> int:
        """板面空位(cap 缺读=0 保守侧:R4 单一真值源改造后 cap 可 None,
        缺读不虚构空位——fail 方向与 predicates.arm1_existence 的
        None 兜底保守端一致)。"""
        if self.deploy_cap is None:
            return 0
        return max(0, self.deploy_cap - len(self.deployed))

    @property
    def bench_names(self) -> list[str]:
        return [b.char_id or '' for b in self.bench]

    @property
    def deployed_names(self) -> list[str]:
        return [b.char_id or '' for b in self.deployed]


# ===== 四硬约束检查点(§3.2;唯一合法拦截集)=====

def check_affordable(gold: int, cost: int, *, batch_cost: int | None = None,
                     ) -> tuple[bool, str]:
    """①可负担:资源余额 ≥ 动作成本(金域 g≥c;整批成本按 M3 批量合计)。"""
    need = batch_cost if batch_cost is not None else cost
    if gold < need:
        return False, f'gold {gold} < cost {need}'
    return True, ''


def check_seats(bench_free: int, deploy_vacancy: int, needs_bench: bool,
                needs_board: bool, name: str, deployed_names: list[str],
                ) -> tuple[bool, str]:
    """②席位:board/bench 槽位、等级 cap、同名同星≤1(穷举对象列:
    M1/M2/M3/M5/M6/dominance_buy,R21-4/R32-3)。"""
    if needs_bench and bench_free <= 0:
        return False, 'bench_full'
    if needs_board and deploy_vacancy <= 0:
        return False, 'board_full'
    if name and name in deployed_names:
        return False, 'same_name_on_board'   # 同名上阵禁(游戏拒收;D-dup 面)
    return True, ''


def check_s_reserve(gold: int, cost: int, s_reserve: int,
                    ) -> tuple[bool, str]:
    """③S 预留:待执行整买目标的预留金不被非 S 组成动作吃掉
    (辖 EV 买入面序 3-5+M6+dominance_buy;M2 序 1/2 义务不受限,[41])。"""
    if gold - cost < s_reserve:
        return False, 's_reserve'
    return True, ''


def check_irreversible(name: str, k_members: tuple[str, ...]) -> tuple[bool, str]:
    """④不可逆护栏:M4 候选过滤——卖出线内/骨架/插件件不在骨架动作集
    (留在 EV 层 fail-closed)。线内件(∈K)禁卖。"""
    if name and name in k_members:
        return False, 'line_member'
    return True, ''


# ===== M4 判据(燃料件支配卖出;P41 零参数,mandate 邻位,R2-2)=====

def fuel_sell_candidates(bench: list[BenchChar],
                         k_members: tuple[str, ...],
                         state: GameState | None = None,
                         *,
                         exclude_names: frozenset[str] | set[str] = frozenset(),
                         ) -> list[BenchChar]:
    """fuel_sell 对象集:1★ ∧ 与锁线零重叠 ∧ 边际贡献≈0
    (R17-2 扩维口径:板面作战边际+bench 后台效果维边际合计构造性 0
    ——1★ 无后台效果件 ⇒ bench 维边际构造性 0,精确 0 界)。

    ``exclude_names``(P60 治本):买面义务集成员禁入燃料集,消费端注入
    ``locked_buy_membership`` 产物(与 EV 排除集同款)。排除后
    Fuel ∩ B = ∅ ⟹ 换手循环势函数 Φ=|owned∩B| 单调不减、循环
    ≤|B∖k| 次收敛;|B|>容量时诚实停摆(m2_retry_exhausted 计数,金
    累积可判读)优于不可见换手。锁线帧 buy_members ⊋ k_members,不
    注入时 bench 上的 hoard 非核心件是合法燃料 → M4 卖 1 买 1 永恒
    换手(伪装进展:net≈0 + drought 被买动作重置)。

    bench_effect_qualified 件(挂后台效果资格,例外①②显式枚举)不入
    燃料集——语境经 ``predicates.bench_effect_context(state, unit,
    k_members)`` 共享装配从 state 现读(IMPL_ADV_R200 症3:三卖面通道
    统一消费;``state=None`` 缺读 ⇒ 装配函数缺省保守保护端)。带默认
    排序:slot 升序(确定性)。
    """
    out = []
    for b in bench:
        name = b.char_id or ''
        if name in exclude_names:
            continue
        if b.star != 1:
            continue
        if not predicates.zero_overlap(name, k_members):
            continue
        try:
            if predicates.bench_effect_qualified(
                    name,
                    predicates.bench_effect_context(state, b, k_members)):
                continue
        except Exception:   # noqa: BLE001  注册表查无此名:类级默认(低费燃料)可判
            pass
        out.append(b)
    return out


def dominance_buy_eligible(gold: int, bench_free: int,
                           stop_flag: bool, cap_resolved: int,
                           ) -> bool:
    """dominance_buy 资格门(P24 零参数;M2 前置支配买入,mandate=true):
    1★ 燃料/可退件 ∧ 档内 ∧ 金>g* ∧ 无 S 目标(线成型 stop_flag)。
    金位阈值 g*=10×cap_resolved 参数化(R70-1;字面 50 实现即红)。"""
    return gold > saturation_line(cap_resolved) and bench_free > 0 and stop_flag


# ===== executor 本体 =====

def run_mandate(frame: MandateFrame,
                session: StrategySession,
                state: GameState | None = None,
                ) -> list[Emitted]:
    """骨架 pass(§3.1 执行序;返回发射列表,执行序=列表序)。

    ``state`` = 决策帧黑板(R4/FIX_REVIEW R1:arm1 消费位的 cap 真值
    在消费点现读 ``state.max_units()`` 派生链——单一真值源,与 shop 侧
    同链;state 缺席(旧调用面/手工帧)= 契约前提 ``deploy_cap=None``
    ⇒ arm1 弃权+违例计数,固定常数/观察复合 cap 喂入不再可达判据)。

    计数键(session.cw4_counters,登记见 design_telemetry 键节):
    m2_retry_exhausted / dominance_bench_wait / m6_bench_full /
    m6_overflow_strand / bench_full_buy_abandon(R196 症4 落地:M2 bench
    满放弃买入帧的「bench 满拒买」事件计数,与 m2_retry_exhausted 的
    环终止计数分键——前者量事件帧,后者量重试环耗竭)/
    shop_latch_skip_dominance_buy / shop_latch_skip_m2_buy /
    shop_latch_skip_m6_stock(备战期开店闩跳过计数,分站记)/
    equip_latch_skip_m7(装备期闩跳过计数,dd-027 门②)。

    备战期开店闩(``session.cw4_shopped_phase``):同一备战期内开店意图
    只消费一次。为什么是决策的推论而非限制:①商店域决策发生在店内一次
    访问内闭环(买/升/刷/卖四字段=店内决策输出,刷新后当场再评估),
    骨架不二次发店;②期内重开无信息量——输入逐项不可变:店面五张
    (无店内刷新则恒定)、金(店外只因 M3 买经验减少不会增加,候选集
    单调变小决策不可能翻新)、席位(M4 卖席只在 M2 同帧)、K 线(换线
    下一备战期生效);同一帧状态重发同一动作=备战环活锁(2026-09-03
    实机首局 1-1 卡死根因:M2 每帧重燃 OpenShop 截断点,StartBattle
    永不可达;sim 每回合单次决策,该活环只在实机多帧备战环可见)。
    边界:闩置位在**商店决策访问位**(mandate_v1/shop.decide_shop_action
    入口=开店动作真执行、商店域决策已发生的时点),不在发射位——
    备战环是单动作环,同发射列表里 dd-027 回排后的 RunEquip(可续类)
    先执行即投影未建模终结本环,发射列表中其后的 OpenShop 意图未执行;
    若发射即置闩,闩烧而店未开,后续环重跑 mandate 被闩挡死 ⇒ 空批
    StartBattle(2026-09-05 单动作备战环实机停机局的扩展诊断定谳:同局
    备战环连续三轮经济冻结后空批出战,「闩置位在发射位而非执行位」;
    dd-027 修发射序回排后本闩置位时机是同型残留)。闩未置时发射位
    照常重发(下帧重试);位面/轮次推进=新键自动失效(新店内容
    重新决策)。旧核 step1 RunBuyPhase 的每备战期一次店内完整决策与本
    闩同构,佐证非理由。
    """
    counters = getattr(session, 'cw4_counters', None)
    if not isinstance(counters, dict):
        counters = {}
        session.cw4_counters = counters

    # M1″ seam 门唯一写点(session 属性;值源 = M1P_SEAM_VERIFIED 常量,
    # 出处与回滚路径见该常量注释,ADR-0530)。
    session.cw4_m1p_seam_verified = M1P_SEAM_VERIFIED

    def _count(key: str) -> None:
        counters[key] = counters.get(key, 0) + 1

    # 备战期键(位面,轮次):state 缺 plane 时退化为 (None, round)。
    phase = (getattr(state, 'plane', None), frame.round_num)
    shopped = getattr(session, 'cw4_shopped_phase', None) == phase

    def _emit_open_shop(tag: str) -> None:
        """开店意图发射位(备战期闩消费点):闩命中=跳过+分站计数;
        闩未命中=发射但不置闩——置闩在商店决策访问位
        (mandate_v1/shop.decide_shop_action,开店动作真执行时点),
        理由见本函数 docstring「备战期开店闩」节边界段。"""
        if shopped:
            _count(f'shop_latch_skip_{tag}')
            return
        out.append(Emitted(OpenShop(read_only=False), True, tag))

    out: list[Emitted] = []
    k = frame.k_members

    # crisis_refresh_invariant(P36-a 结构位;刷新域=商店线,prep 帧无对象,
    # 结构位在 executor——此处为序位声明,判据本体 refresh.crisis_refresh_invariant)
    # M5 开局板(§2.9 无数学面:开局帧(round_num≤1)板空且有 bench 件;
    # K 直通线开局配方归 TRANSITION_SYSTEMS 第五类,本批载体 = RunDeploy
    # 现读重建[D-C44])
    deploy_intent_emitted = False
    if (frame.round_num <= 1 and not frame.deployed and frame.bench
            and _deployable(frame, session, state)):
        out.append(Emitted(RunDeploy(), True, 'm5_opening_board'))
        deploy_intent_emitted = True

    # dominance_buy(M2 前置,mandate 邻位;席位失败=单帧单评不入 M2 重试环 R12-2)
    if dominance_buy_eligible(frame.gold, frame.bench_free, frame.stop_flag,
                              cap_resolved=_cap_of(session)):
        ok, why = check_seats(frame.bench_free, frame.deploy_vacancy,
                              needs_bench=True, needs_board=False,
                              name='', deployed_names=frame.deployed_names)
        if ok:
            ok3, _ = check_s_reserve(frame.gold, 0,
                                     _s_reserve(frame, session))
            if ok3:
                # 支配买对象(店面 1★ 燃料/可退件)在商店域:prep 帧载体 =
                # OpenShop 意图(截断点,序列在此收口,商店线执行候选评估)
                _emit_open_shop('dominance_buy')
            else:
                _count('dominance_bench_wait')
        else:
            _count('dominance_bench_wait')

    # M2 线成员买入(+M2→M4 重试环 R8-8)
    missing = [m for m in k
               if m not in set(frame.bench_names) | set(frame.deployed_names)]
    if shopped and missing and not frame.stop_flag:
        _count('shop_latch_skip_m2_buy')
    if missing and not frame.stop_flag and not shopped:
        ok, _why = check_seats(frame.bench_free, frame.deploy_vacancy,
                               needs_bench=True, needs_board=False,
                               name='', deployed_names=frame.deployed_names)
        if not ok:
            # 现场腾席:M4 fuel_sell(R8-8:环内意图=线内件(序 1/2)独占)
            retries = 0
            freed = False
            bench = list(frame.bench)
            while retries < BENCH_CAPACITY:
                cands = fuel_sell_candidates(bench, k, state=state)
                if not cands:
                    break       # 0 发射 ⇒ 立即放弃(状态未变,重放必再失败)
                victim = cands[0]
                ok4, _ = check_irreversible(victim.char_id or '', k)
                if not ok4:
                    break
                out.append(Emitted(SellBench(slot=victim.slot), True,
                                   'm4_fuel_sell_for_m2'))
                bench = [b for b in bench if b.slot != victim.slot]
                freed = True
                retries += 1
                # 腾席后席位复检(静态:卖 1 件 ⇒ bench_free+1)
                if BENCH_CAPACITY - len(bench) > 0:
                    break
            if not freed or BENCH_CAPACITY - len(bench) <= 0:
                _count('m2_retry_exhausted')
                _count('bench_full_buy_abandon')   # 环终止仍满 ⇒ 事件帧
            else:
                _emit_open_shop('m2_buy')
        else:
            ok1, _ = check_affordable(frame.gold, cheapest_member_cost(frame))
            if ok1:
                _emit_open_shop('m2_buy')
            # 金不足侧:funding_support 变现通道在 EV pass(criteria/sell)

    # M1 同帧部署(买入完成后立即评估成对上阵;P24 零支出补部署严格支配)
    if (not deploy_intent_emitted and frame.deploy_vacancy > 0
            and _deployable(frame, session, state)):
        out.append(Emitted(RunDeploy(), True, 'm1_deploy'))

    # M3 升级整批(触发信号 = arm1_existence(statefn/predicates);
    # arm2 调度门只延迟不否决;P48 整买纪律 D-BUYNOTE 内嵌)。
    # cap 接线=消费点现读 state.max_units()(R4 单一真值源:level+宝钻、
    # 封顶 10,与 shop 侧同链;FIX_REVIEW ②-1 双源漂移修复——旧观察复合
    # cap 已废)——板满按当前 cap 判,非固定槽表常数(2026-09-03 零刷新
    # 诊断批定谳的域错位形态)。契约核验(FIX_REVIEW R1 漏接位补齐):
    # arm1/lv9_stop/spend_unified 三消费位经 ensure_contract;固定常数/
    # 无 state 喂入(对抗复验=FIX_REVIEW 场景 A)⇒ deploy_cap=None 前提
    # 违例 ⇒ 弃权+计数,判据不可达。
    _cap_now = state.max_units() if state is not None else None
    _arm1 = (contracts.ensure_contract(
        ('predicates', 'arm1_existence'),
        contracts.ContractCtx(deploy_cap=_cap_now), counters)
        and _cap_now is not None
        and predicates.arm1_existence(len(frame.deployed), frame.bench_names,
                                      frame.deployed_names, _cap_now))
    # arm0 升级授权回补(14号稿 §4.2 A4 现量版):等级落后于上阵人数需求
    #(need = 期望态现量,排除谓词 (名,星) 口径 Y3);level 消费只认
    # authoritative 可信位(level_readable,C4)——不可信帧 fail 向不触发
    # + arm0_level_unreadable 分键(W6:15 号稿 T-8 锁读链合一,消费端
    # fail 向零静默)。与 arm1 并联触发(任一成立即进 M3 判据链)。
    _arm0 = False
    if contracts.ensure_contract(
            ('predicates', 'arm0_level_lag'),
            contracts.ContractCtx(), counters):
        _arm0, _arm0_key = predicates.arm0_level_lag(
            frame.level,
            bool(getattr(state, 'level_readable', True))
            if state is not None else True,
            frame.deployed, frame.bench, k, _cap_now)
        if not _arm0 and _arm0_key == 'level_unreadable':
            _count('arm0_level_unreadable')
        elif _arm0 and _cap_now is None:
            _count('arm0_cap_unreadable')   # 存-3(落地审清单 20260905_cp1_landing_review/问题清单.md):cap 不可读静默弃权补分键
            _arm0 = False
    # pop_slot(D-lv7 满编+富金+候补升 cap;落地审应-B:与商店栈同判据
    # 同单一源,三臂并联)——备战帧店面不可读 ⇒ buyable_candidate 腿
    # 只在商店栈生效(双栈分域声明);备战帧独有触发域 = 满编+富金+
    # bench 有线内候补,否向理由留决策迹字段(D-lv7 纪律)。
    _pop = False
    if contracts.ensure_contract(
            ('levelup', 'pop_slot'), contracts.ContractCtx(), counters):
        _bench_cand = sum(1 for n in frame.bench_names if n in k)
        _pop, _pop_why = levelup.pop_slot(
            len(frame.deployed),
            _cap_now if _cap_now is not None else 0,
            frame.gold, _bench_cand,
            saturation_line(_cap_of(session)) if _cap_now is not None else 0)
        session.cw4_pop_slot_why = _pop_why
    # L3 必花域第三触发源(20 号稿 §3.1-L3/§3.5,备战栈接入;判定单一源
    # = in_must_spend_zone,与 shop 栈同源禁第二套语义;应-C 偏高必收:
    # 备战必花帧不再被停付线否决——域内让位 = ADR-0528,域外照旧)。
    _zone_hit = in_must_spend_zone(frame.gold, session) and (
        state is None
        or bool(getattr(state, 'level_readable', True)))   # 等级不可信帧 fail 向(资格硬闸)
    _arms_hit = _arm1 or _arm0 or _pop
    if (_arms_hit or _zone_hit) and _cap_now is not None:
        # 候选③危机带经验授权让位(g_20260904_054904 p2r1:hp=1 帧
        # 9×LevelUpShop 36g 零本帧收益):血预算停升级门(P21)此前只有
        # decision_v2 侧消费,cw4 M3 未接 = 双栈语义断层;判据单一源 =
        # levelup.level_spend_blocked(blood_budget_levelup_blocked ∪
        # p2_crisis_band,P48 λ>0 段转化优先)。让位=挂起本批经验支出,
        # 授权面降级由 entry._reconcile_posture_authorization 显式声明。
        # 必花域帧停付线让位(裁定覆盖,ADR-0528):域内本门不否决 L3。
        # 停付判据提取为局部变量;域内豁免时记 must_spend_zone_defer_overridden
        # 显影分键(与 shop 侧 must_spend_r1_account_yielded 对称)——归因时
        # 区分「本来就不该停」与「停付被域裁压掉」,crisis_level_spend_defer
        # 原语义不变(仍只辖域外命中帧)。
        _level_spend_blocked = (
            state is not None
            and contracts.ensure_contract(
                ('levelup', 'level_spend_blocked'),
                contracts.ContractCtx(), counters)
            and levelup.level_spend_blocked(state, session))
        if _level_spend_blocked and not _zone_hit:
            _count('crisis_level_spend_defer')
        else:
            if _level_spend_blocked:
                # 域内豁免显影分键(与 shop 侧 must_spend_r1_account_yielded
                # 对称):本会停付但被必花域裁定压掉(ADR-0528),归因时
                # 区分「本来就不该停」与「停付被域裁压掉」。
                _count('must_spend_zone_defer_overridden')
            if contracts.ensure_contract(
                    ('levelup', 'lv9_stop'),
                    contracts.ContractCtx(), counters) \
                    and not levelup.lv9_stop(frame.level):
                clicks = clicks_to_next_level(_state_view(frame, session))
                cost = xp_click_cost(_state_view(frame, session))
                if contracts.ensure_contract(
                        ('levelup', 'spend_unified'),
                        contracts.ContractCtx(gold=frame.gold), counters) \
                        and levelup.spend_unified(clicks, frame.gold, cost):
                    ok1, _ = check_affordable(frame.gold, 0,
                                              batch_cost=clicks * cost)
                    if ok1:
                        # auth_basis 分键(可归因,与商店栈同序 arm1>arm0>pop;
                        # 三臂全空时 = 必花域触发源,分键 must_spend)
                        if _arms_hit:
                            _arm_tag = 'arm1' if _arm1 else (
                                'arm0' if _arm0 else 'pop')
                        else:
                            _arm_tag = 'must_spend'
                            _count('must_spend_l3_prep_trigger')
                        out.append(Emitted(LevelUp(), True,
                                           f'm3_levelup_batch:{_arm_tag}'))

    # M1′(M3 后新人口位补部署;R6-6/R8-1:迭代至不动点——RunDeploy
    # 执行侧现读重建输入(D-C44),发射即覆盖升级增量空位的部署重评)
    if frame.deploy_vacancy > 0 and _deployable(frame, session, state):
        has_levelup = any(isinstance(e.action, LevelUp) for e in out)
        if has_levelup:
            out.append(Emitted(RunDeploy(), True, 'm1_prime_redeploy'))

    # M1″(板满换阵补部署意图;发射序 = M1′ 后、M6 前)。语义出处 =
    # ADR-0530(board-full swap redeploy;判据单一源 =
    # kernel.cw_deploy_logic.select_swap_plan,组合语义:cap 满占用数
    # 口径 ∧ 义务集/轮内新鲜度排除后存在合格 victim ∧ 卖出后假想状态
    # 复用 select_deployments 判 up 非空——底线留置件不作上序候选,
    # 零新启发式)。发射载体 = RunDeploy(条件续类,entry.
    # classify_frame_stability,不触发截断、不受 dd-027 回排辖);
    # 卖谁由执行侧 CwOpDeploy 卖出臂现读仲裁(发射=存在性,执行=逐件;
    # 执行侧同吃义务集∪新鲜度排除,swap_sell_exclusion_reason 单一判定)。
    # 同帧 LevelUp 抑制(m1p_defer_levelup):升级开新 vacancy,下帧
    # M1′ 以零卖出成本接管——卖出不可逆 > 等一帧。
    # 发射位门(session.cw4_m1p_seam_verified):装配两侧(发射⇔执行)
    # 输入对齐核对通过前置 False = 发射关闭、m1p_input_seam_pending 显影
    # (ADR-0530:接线核对通过前不许发射,对齐证据 = 开闸前置义务;
    # 唯一写点 = 核对完成后的接线批,缺省关 = fail-closed,与 dd-037
    # 留 bench 合法稳态同向)。
    if not any(isinstance(e.action, RunDeploy) for e in out):
        from sr_od.application.currency_war.kernel.cw_deploy_logic import (
            assemble_swap_plan_inputs,
            select_swap_plan,
        )
        _m1p = select_swap_plan(assemble_swap_plan_inputs(
            session, state=state, deployed=list(frame.deployed),
            bench=list(frame.bench), cap=frame.deploy_cap))
        if _m1p.abstain == 'cap_unreadable':
            _count('m1p_cap_unreadable')
        elif _m1p.abstain == 'membership_unreadable':
            _count('m1p_membership_unreadable')
        elif _m1p.abstain == 'input_missing':
            _count('m1p_input_missing')   # 供给缺失 ≠ 真计划空,禁混桶
        elif _m1p.nonempty:
            if any(isinstance(e.action, LevelUp) for e in out):
                _count('m1p_defer_levelup')
            elif not getattr(session, 'cw4_m1p_seam_verified', False):
                _count('m1p_input_seam_pending')
            else:
                out.append(Emitted(RunDeploy(), True, 'm1_swap_redeploy'))
                _count('m1p_fired')
        else:
            _count('m1p_plan_empty')

    # M6 溢余转压库(存在性=金>g* ∧ 无 S 目标;档匹配 fail-closed ⇒ 不买
    # +溢余滞留遥测;席位失败=单帧单评,R21-4)
    if frame.gold > saturation_line(_cap_of(session)) and frame.stop_flag:
        ok, _ = check_seats(frame.bench_free, frame.deploy_vacancy,
                            needs_bench=True, needs_board=False,
                            name='', deployed_names=frame.deployed_names)
        if not ok:
            _count('m6_bench_full')
        else:
            from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
                provisional,
            )
            if provisional.is_none('T_SEARCH_A'):
                _count('m6_overflow_strand')
            else:
                _emit_open_shop('m6_stock')

    # M7 装备转移(常态:关键装备穿上场单位;D-B 释放门 =
    # criteria/equipment.wear_release 消费;基础载体 = RunEquip)。
    # 发射门 = 变换可能性两件套(dd-027,2026-09-03 实机 RunEquip 备战环
    # 活锁定谳修法):
    # ①可穿存在性(m7_wearable_exists):owned 快照里有注册表已登记且非
    #   工具类的件。旧「last_owned_equips 非空即发」是持有面谓词,而快照
    #   按 ADR-0387 全量含工具件(扳手/冶金炉等不可穿)——工具-only 库存
    #   谓词永真 ⇒ 每帧重发 RunEquip 且 0 穿 ⇒ 空批出口(StartBattle)
    #   永不可达,备战环活锁(实机 1-6 卡死,签名「序列完成(RunEquip)」)。
    # ②备战期闩(cw4_m7_equipped_phase):同 (plane, round) 备战期只发一次
    #   ——执行侧一次完整穿戴 pass 信息完备(内含补救链/拉黑/分配归因,
    #   cw_op_equip_all),期内重开输入不变结果不变(与开店闩同构论证);
    #   位面/轮次推进=新键自动失效(新发放件重评)。闩置位在**执行位**
    #   (mark_equip_pass_executed,唯一写点由 prep_actions 执行入口在
    #   RunEquip 组合 op 成功返回时调用),不在发射位——发射位只读不写,
    #   理由与本函数 docstring「备战期开店闩」节同型(单动作环下发射
    #   列表中 RunEquip 之前的可续类动作先执行即终结本环,RunEquip
    #   意图未执行,发射即置闩会让闩烧而装备未穿、后续环被闩挡死)。
    if getattr(session, 'last_owned_equips', None) \
            and m7_wearable_exists(session.last_owned_equips):
        if getattr(session, 'cw4_m7_equipped_phase', None) == phase:
            _count('equip_latch_skip_m7')
        else:
            out.append(Emitted(RunEquip(), True, 'm7_equip_transfer'))

    # M7 发射序回排(dd-027 修订;实机局 g_20260904_010335 1-6/1-7 漏发
    # 定谳):M7 在执行序末位评估,发射落在同帧开店意图(OpenShop=帧稳定
    # 契约 §3.2 截断点)之后 ⇒ 截断器 truncate_frame_stable 其后必截,
    # RunEquip 被静默丢弃而门②闩已在发射位消耗——同帧「开店 ∧ 可穿件」
    # 形态下装备滞留整个备战期(闩挡死后续帧重评,1-8 无开店面才首穿)。
    # 修法 = 发射组织面回排:RunEquip 系可续类(conditional,装备 pass
    # 画面零迁移),插到首个截断点/终点之前,两动作均保留、执行序
    # (先穿后开店)与发射序一致;门①谓词不变。闩置位时机已移执行位
    # (mark_equip_pass_executed,与开店闩置位时机修复同批)——回排
    # 语义仍保证 RunEquip 落在执行序前段、先于截断点被消费。分类单一
    # 源 = entry.classify_frame_stability(函数内延迟 import 防模块环)。
    if any(isinstance(e.action, RunEquip) for e in out):
        from sr_od.application.currency_war.strategies.impl.mandate_v1.entry import (
            classify_frame_stability,
        )
        equips = [e for e in out if isinstance(e.action, RunEquip)]
        rest = [e for e in out if not isinstance(e.action, RunEquip)]
        cut = next((i for i, e in enumerate(rest)
                    if classify_frame_stability(e.action)
                    in ('truncation', 'terminal')), len(rest))
        out = rest[:cut] + equips + rest[cut:]

    return out


def mark_equip_pass_executed(session: StrategySession,
                             state: GameState | None) -> None:
    """M7 备战期装备闩唯一写点(置位=执行位)。

    调用点 = 执行入口(prep_actions.PrepActionExecutor.execute)在
    RunEquip 组合 op 成功返回时——「一次完整穿戴 pass 已落地」的记账
    时点(含 0 穿完成态:候选全拉黑/hold 过滤后的完成 pass 信息完备,
    dd-027 门②论证不变)。为什么不在发射位:备战环是单动作环,发射
    列表中排在 RunEquip 之前的可续类动作(RunDeploy 等)先执行即投影
    未建模终结本环,RunEquip 意图未执行而闩已烧 → 后续环
    equip_latch_skip 挡死,装备滞留整个备战期(与开店闩置位时机修复
    同型,见 run_mandate docstring「备战期开店闩」节)。键式与
    run_mandate 的 phase 同构(同一 state 读出,含缺省退化)。执行
    失败(ok=False)不经本函数=不置闩,下帧照常重发;意图持续不落地
    由 DD-030 环级守卫兜底,非本闩职责。
    """
    if session is None:
        return
    session.cw4_m7_equipped_phase = (getattr(state, 'plane', None),
                                     getattr(state, 'round_num', 1))


def m7_wearable_exists(owned: list[str]) -> bool:
    """M7 发射门①:owned 存在穿戴类件(注册表已登记 ∧ 非工具类)。

    为什么不是「owned 非空」:快照写端按 ADR-0387 全量含工具件,持有面
    非空 ≠ 存在可穿件;谓词必须是变换面(穿上会改变装备分布)存在性。
    未登记名(识别对齐缺失)按不可穿保守侧处理——与执行侧 wearable 过滤
    同口径(EQUIPMENTS.get 命中才进穿戴决策)。工具类名单一源 =
    ``cw_equipment_data.EQUIP_TOOL_CATEGORY``(执行侧同源消费)。
    """
    from sr_od.application.currency_war.data.cw_equipment_data import (
        EQUIP_TOOL_CATEGORY,
        EQUIPMENTS,
    )
    return any(
        (eq := EQUIPMENTS.get(n)) is not None
        and eq.category != EQUIP_TOOL_CATEGORY
        for n in owned)


def _cap_of(session: StrategySession) -> int:
    """cap_resolved 现读(单一源 = kernel.cw_economy.cap_resolved_of_
    session,ADR-0516 cap 三源归一:商店线 R1/R2 的 g*、schedule_upgrade
    ② 前置、U_L 检验 loss_exact cap 共用同一式;投资覆写语境归一)。"""
    from sr_od.application.currency_war.kernel.cw_economy import (
        cap_resolved_of_session,
    )
    return cap_resolved_of_session(session)


def _s_reserve(frame: MandateFrame, session: StrategySession) -> int:
    """S 预留下界 = s_line 组装值(s_line 单一源,P48 ② 结构形状)。

    R196 症6 实装(替换旧 ``b_target(0, 0, 0)`` 退化形):S = B + 息饱和线
    分量 + Σ_w 窗口预留卡价 + E[刷费]×2,逐分量现读——

    - B(整买目标批成本):prep 帧 xp 未观测(frame 无 xp 快照)⇒ 整买
      目标未立 ⇒ B=0。**非静默 0**——分量级 None 期申报:xp_progress
      是 heavy 读字段,MandateFrame 未载;载入批落位前 B 构造性 0;
    - 息饱和线分量 = ``saturation_line(cap_resolved)``(canonical 行 10⑤⑥
      条件式的调用方供给 resolved 值,默认局 50);
    - 窗口预留卡价:窗口预留槽未标定 ⇒ 空列表(缺输入不计,保守下界);
    - E[刷费]×2 = 双刷预算,按 ``shop_refresh_cost`` 基价(REFRESH_COST_BASE
      建模常量,GameState 字段口径:值恒基价 2)。

    默认局 = 0+50+0+4 = 54(旧值恒 0 系 b_target 零参退化,非规格)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.s_line import (
        s_line,
    )
    return s_line(0, _cap_of(session), [], REFRESH_COST_BASE)


def cheapest_member_cost(frame: MandateFrame) -> int:
    """线成员最廉成本(注册表派生,R196 症6:字面量 3 改单一源)。

    = K 成员在 CHARACTERS 注册表的最低 cost;成员全部未注册 ⇒
    ``bench_char_cost`` 同款保守估 3(未知名中费估,注册表先例)。
    消费面 = 硬约束①的金需求侧(entry 支付支撑通道)。
    """
    costs = [ch.cost for m in frame.k_members
             if (ch := CHARACTERS.get(m)) is not None and ch.cost]
    if costs:
        return min(costs)
    # 成员全部未注册(探针/语料名)⇒ 中费保守估 3(bench_char_cost 同款
    # 注册表先例:未知名 → 3)
    return 3


def _deployable(frame: MandateFrame, session: StrategySession,
                state: GameState | None = None) -> bool:
    """RunDeploy 提案合法门(ADR-0517 决策 2:合法性=提议侧约束)。

    谓词单一源 = ``kernel.cw_deploy_logic.has_deployable``(dd-037):
    与执行方 CwOpDeploy 计划构造(select_deployments)同源同参语义
    ——围栏/去重/cap/配方底线全在谓词内。计划空(含「候选全被规则
    留 bench」形态)⇒ False,不提案 RunDeploy(序内取下一动作)。

    事件语义(本守卫触发形态):2026-09-06 实机首局(单动作架构,
    ADR-0518)00:08:25 备战环无进展守卫以「连续 3 环同签名动作批
    ['RunDeploy'] ∧ 零推进」停机留证——决策核每轮提案 RunDeploy,
    执行方计划空报 no-op 成功,RunDeploy 投影未建模(保守回退)交回
    外循环,重进再提案,3 环零推进。守卫行为正确,根因 = 本发射位
    漏接抑制谓词。禁第二实现:判空一律走 kernel;本函数只做输入装配
    (与 CwOpDeploy 同款,经 kernel deploy_target_sets /
    deployed_bond_counts 单一源)。
    """
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        deploy_target_sets,
        deployed_bond_counts,
        has_deployable,
    )
    from sr_od.application.currency_war.kernel.cw_intention import (
        locked_faction_scope,
    )
    _comp = getattr(session, 'target_comp', None)
    _tgt, _fw_carry = deploy_target_sets(
        _comp, getattr(session, 'transition_framework', '') or '')
    _cids = {d.char_id for d in frame.deployed if d.char_id}
    return has_deployable(
        frame.bench,
        deployed_cids=_cids,
        deployed_fac=deployed_bond_counts(_cids),
        board=dict(getattr(state, 'board', None) or {}),
        cap=(frame.deploy_cap if frame.deploy_cap and frame.deploy_cap > 0
             else 10 ** 6),
        target_factions=_tgt,
        target_cores=set(getattr(_comp, 'core_chars', None) or ()),
        fw_carry=_fw_carry,
        locked_factions=(locked_faction_scope(
            getattr(session, 'v3_intention', None)) or frozenset()),
    )


def _state_view(frame: MandateFrame, session: StrategySession) -> object:
    """M3 成本计算的 GameState 视图(level/xp 现读;clicks_to_next_level
    消费面;duck-typed 局部视图,返回 object 注解=不对 kernel 契约撒谎)。"""
    class _Lv:
        pass
    v = _Lv()
    v.level = frame.level
    v.xp_progress = None
    v.level_up_cost = None
    v.active_strategies = list(getattr(session, 'active_strategies', []) or [])
    return v
