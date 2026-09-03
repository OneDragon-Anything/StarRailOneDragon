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
D-dup 谓词 = vopt.dup_power_qualified)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.decision.cw4.criteria import contracts, levelup
from sr_od.application.currency_war.decision.cw4.statefn import predicates
from sr_od.application.currency_war.decision.cw4.statefn.interest import (
    saturation_line,
)
from sr_od.application.currency_war.decision.cw4.statefn.vopt import (
    dup_power_qualified,
)
from sr_od.application.currency_war.kernel.cw_economy import (
    clicks_to_next_level,
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

if TYPE_CHECKING:
    from sr_od.application.currency_war.decision.cw_strategy import (
        StrategySession,
    )
    from sr_od.application.currency_war.kernel.cw_state import BenchChar, GameState

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
                         ) -> list[BenchChar]:
    """fuel_sell 对象集:1★ ∧ 与锁线零重叠 ∧ 边际贡献≈0
    (R17-2 扩维口径:板面作战边际+bench 后台效果维边际合计构造性 0
    ——1★ 无后台效果件 ⇒ bench 维边际构造性 0,精确 0 界)。

    bench_effect_qualified 件(挂后台效果资格,例外①②显式枚举)不入
    燃料集——语境经 ``predicates.bench_effect_context(state, unit,
    k_members)`` 共享装配从 state 现读(IMPL_ADV_R200 症3:三卖面通道
    统一消费;``state=None`` 缺读 ⇒ 装配函数缺省保守保护端)。带默认
    排序:slot 升序(确定性)。
    """
    out = []
    for b in bench:
        name = b.char_id or ''
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
    只发一次。为什么是决策的推论而非限制:①商店域决策发生在店内一次
    访问内闭环(买/升/刷/卖四字段=店内决策输出,刷新后当场再评估),
    骨架不二次发店;②期内重开无信息量——输入逐项不可变:店面五张
    (无店内刷新则恒定)、金(店外只因 M3 买经验减少不会增加,候选集
    单调变小决策不可能翻新)、席位(M4 卖席只在 M2 同帧)、K 线(换线
    下一备战期生效);同一帧状态重发同一动作=备战环活锁(2026-09-03
    实机首局 1-1 卡死根因:M2 每帧重燃 OpenShop 截断点,StartBattle
    永不可达;sim 每回合单次决策,该活环只在实机多帧备战环可见)。
    边界:发射时才置闩——店未开成(席位失败/燃料耗竭,本帧无 OpenShop
    发射)不置闩,下帧照常重试;位面/轮次推进=新键自动失效(新店内容
    重新决策)。旧核 step1 RunBuyPhase 的每备战期一次店内完整决策与本
    闩同构,佐证非理由。
    """
    counters = getattr(session, 'cw4_counters', None)
    if not isinstance(counters, dict):
        counters = {}
        session.cw4_counters = counters

    def _count(key: str) -> None:
        counters[key] = counters.get(key, 0) + 1

    # 备战期键(位面,轮次):state 缺 plane 时退化为 (None, round)。
    phase = (getattr(state, 'plane', None), frame.round_num)
    shopped = getattr(session, 'cw4_shopped_phase', None) == phase

    def _emit_open_shop(tag: str) -> None:
        """开店意图发射位(备战期闩消费点):闩命中=跳过+分站计数;
        首发置闩。见本函数 docstring「备战期开店闩」节。"""
        if shopped:
            _count(f'shop_latch_skip_{tag}')
            return
        session.cw4_shopped_phase = phase
        out.append(Emitted(OpenShop(read_only=False), True, tag))

    out: list[Emitted] = []
    k = frame.k_members

    # crisis_refresh_invariant(P36-a 结构位;刷新域=商店线,prep 帧无对象,
    # 结构位在 executor——此处为序位声明,判据本体 refresh.crisis_refresh_invariant)
    # M5 开局板(§2.9 无数学面:开局帧(round_num≤1)板空且有 bench 件;
    # K 直通线开局配方归 TRANSITION_SYSTEMS 第五类,本批载体 = RunDeploy
    # 现读重建[D-C44])
    deploy_intent_emitted = False
    if frame.round_num <= 1 and not frame.deployed and frame.bench:
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
            and _deployable(frame)):
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
    if contracts.ensure_contract(
            ('predicates', 'arm1_existence'),
            contracts.ContractCtx(deploy_cap=_cap_now), counters) \
            and _cap_now is not None \
            and predicates.arm1_existence(len(frame.deployed), frame.bench_names,
                                 frame.deployed_names, _cap_now):
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
                    out.append(Emitted(LevelUp(), True, 'm3_levelup_batch'))

    # M1′(M3 后新人口位补部署;R6-6/R8-1:迭代至不动点——RunDeploy
    # 执行侧现读重建输入(D-C44),发射即覆盖升级增量空位的部署重评)
    if frame.deploy_vacancy > 0 and _deployable(frame):
        has_levelup = any(isinstance(e.action, LevelUp) for e in out)
        if has_levelup:
            out.append(Emitted(RunDeploy(), True, 'm1_prime_redeploy'))

    # M6 溢余转压库(存在性=金>g* ∧ 无 S 目标;档匹配 fail-closed ⇒ 不买
    # +溢余滞留遥测;席位失败=单帧单评,R21-4)
    if frame.gold > saturation_line(_cap_of(session)) and frame.stop_flag:
        ok, _ = check_seats(frame.bench_free, frame.deploy_vacancy,
                            needs_bench=True, needs_board=False,
                            name='', deployed_names=frame.deployed_names)
        if not ok:
            _count('m6_bench_full')
        else:
            from sr_od.application.currency_war.decision.cw4.audit import (
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
    #   位面/轮次推进=新键自动失效(新发放件重评)。发射时才置闩。
    if getattr(session, 'last_owned_equips', None) \
            and m7_wearable_exists(session.last_owned_equips):
        if getattr(session, 'cw4_m7_equipped_phase', None) == phase:
            _count('equip_latch_skip_m7')
        else:
            session.cw4_m7_equipped_phase = phase
            out.append(Emitted(RunEquip(), True, 'm7_equip_transfer'))

    return out


EQUIP_TOOL_CATEGORY: str = '工具'
"""注册表装备分类学里的「工具」类名(不可 drag 穿戴,只能拖到装备/角色上
消耗使用)。分类全集单一源 = ``cw_equipment_data.Equipment.category`` 字段
注释;穿戴类过滤的执行侧平行消费 = ``cw_op_equip_all._TOOL_CATEGORIES``
(同值,文件面不含该文件,单一源化归后续批)。"""


def m7_wearable_exists(owned: list[str]) -> bool:
    """M7 发射门①:owned 存在穿戴类件(注册表已登记 ∧ 非工具类)。

    为什么不是「owned 非空」:快照写端按 ADR-0387 全量含工具件,持有面
    非空 ≠ 存在可穿件;谓词必须是变换面(穿上会改变装备分布)存在性。
    未登记名(识别对齐缺失)按不可穿保守侧处理——与执行侧 wearable 过滤
    同口径(EQUIPMENTS.get 命中才进穿戴决策)。
    """
    from sr_od.application.currency_war.data.cw_equipment_data import (
        EQUIPMENTS,
    )
    return any(
        (eq := EQUIPMENTS.get(n)) is not None
        and eq.category != EQUIP_TOOL_CATEGORY
        for n in owned)


def _cap_of(session: StrategySession) -> int:
    """cap_resolved 现读(interest_cap_resolved;投资覆写语境归一)。"""
    from sr_od.application.currency_war.decision.cw4.statefn.interest import (
        interest_cap_resolved,
    )
    override = getattr(session, 'cw4_cap_override', None)
    return interest_cap_resolved(override)


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
    from sr_od.application.currency_war.decision.cw4.statefn.s_line import (
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


def _deployable(frame: MandateFrame) -> bool:
    """可部署候选存在(board 空位 ∧ bench 件非场上 dup[D-dup 估值修正]
    ∧ 同名禁双)。"""
    deployed_names = set(frame.deployed_names)
    for b in frame.bench:
        name = b.char_id or ''
        if not name:
            continue
        if name in deployed_names:
            continue    # 场上 dup ≠ 可部署战力(游戏拒同名上阵)
        if not dup_power_qualified(name, 0):
            continue
        return True
    return False


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
