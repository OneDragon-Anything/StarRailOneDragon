"""criteria/levelup——升级面判据(§2.3;M3 触发信号 arm1_existence 在
statefn/predicates,不在本域)。

D-BUYNOTE(修复池执行层附注,随批收编):新核买牌/升级发射器内嵌
P48 整买纪律常量判据——``spend_unified`` = XP 仅整批够升级时放行
(181254 r7/r8 各 4 金散买 XP 零收益的防复发锚)。
D-lv7(OPEN 检查点):``pop_slot`` 对「满编+富金+bench 有候补」的
覆盖核查——本模块 ``pop_slot`` 落位并显式给不触发理由进决策迹。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )
    from sr_od.application.currency_war.kernel.cw_state import (
        GameState,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )


def lv9_stop(level: int, level_max: int | None = None) -> bool:
    """等级上限停(义务侧消费)。历史键名 'lv9_stop':cap=9 旧语义时代
    命名,现语义 =「等级达注册表 level_max 即拒发升级」——键串保留
    不改名(改键牵连判读脚本与历史档案可比性,纯改名无收益,ADR-0565)。

    单一源 = 注册表 ``level_max``(kernel/cw_registry.py,实机真值 10,
    与 cw_state.xp_apply_clicks「封顶 10」live 机制语义同源);sim 侧
    经 ``sim_decision_registry`` 注入视图(=9)保持建模冻结,策略零
    感知、sim 行为零漂移。⚠ 与同文件 ``cap_resolved``(利息上限)毫无
    数值或语义关联,禁接错源。

    ``level_max`` 由消费位传上下文注册表的 ``.level_max``(禁裸常数);
    缺省 None 回读 DEFAULT_REGISTRY 是**过渡兼容**,仅覆盖 mandate.py
    备战 L3 消费位(ADR-0565 落码时该文件属并行在飞文件面未接线;该位
    仅 live prep 可达,sim 决策只走 shop 栈注入视图,不经此处,故回读
    缺省表 = live 真值、无 sim 路径)——mandate 侧接线完成后本参收严
    为必填,禁新消费位依赖缺省。
    """
    if level_max is None:
        from sr_od.application.currency_war.kernel.cw_registry import (
            DEFAULT_REGISTRY,
        )
        level_max = DEFAULT_REGISTRY.level_max
    return level >= level_max


def arm2_schedule(gold: int, cap_resolved: int, *, gate_open: bool = False,
                  ) -> bool:
    """arm2 调度门(R5-4 范畴定谳:门,无发射;臂①=门关闭恒 false)。

    结构守息门(R26-H1 后保留成分):金下限 g*=10×cap_resolved
    (L-R3-3 引理 1 同源,零 λ 依赖)——arm2 触发的调度类批金条件。
    ``gate_open`` = 升档器信号位(血线地板触发帧解锁:g*→0,R28-2;
    λ 顾问触发帧延迟 arm2 调度类批 ⇒ false)。
    """
    floor = 0 if gate_open else saturation_floor(cap_resolved)
    return gold >= floor


def saturation_floor(cap_resolved: int) -> int:
    """守息线 g* = 10×cap_resolved(单一源=statefn/interest.saturation_line
    的重导出消费口,禁另算)。"""
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.interest import (
        saturation_line,
    )
    return saturation_line(cap_resolved)


def spend_unified(clicks_to_next: int, gold: int, click_cost: int) -> bool:
    """P48 整买纪律(D-BUYNOTE):整批 XP 放行判据。

    仅当「一次买齐到下一级」的金够付时放行(clicks×click_cost ≤ gold)
    ——散买 XP(买不够升级)零收益,拦截。M3 义务侧消费(不旁路)。
    """
    if clicks_to_next <= 0:
        return False
    return gold >= clicks_to_next * click_cost


def levelup_budget_gate(state: GameState, session: StrategySession | None,
                        gold: int, cap_resolved: int,
                        k_members: tuple[str, ...], bench: list,
                        deployed: list, clicks: int,
                        click_cost: int) -> tuple[bool, str]:
    """P72 (3) 全段预算闸(ADR-0576):升级支出 s 的量闸(全段辖域)。

    判据式(证明 = docs/develop/currency_war/proofs/
    p72-full-band-budget-gate.md;P71-b (3) 辖域的全段化推广非推翻,
    溢余段逐字退化零漂移):

    ``g − s ≥ 10·τ(g) + ρ + Σ预留``(P72 (3a) 强读式;τ(g) =
    min(⌊g/10⌋, cap_resolved),s = clicks×click_cost 整批成本)

    - 息档零侵蚀 + 购买力保底:花后金位不低于「当前息档最低金位 +
      一张命中卡 + 下帧窗口预留」——升级不花「正在生息的钱」;
    - g > g* 帧 10·τ(g) = g*,逐字退化回 P71-b (3)(证明 §1 退化
      一致性,已落码溢余段行为零漂移);
    - g ≤ g* 帧(中间段)不再空过放行:旧 ``gold <= g_star`` vacuous
      分支即 T-93 签名 A 真洞——「义务买牌先花钱 + 逐击发射」组合
      把金潜到息线以下(30 局插桩 20% 局息损潜行,fix_p71_bypass/
      方案设计 §2.3);全段化后中间段逐帧管账。

    三分量口径(全部已证单一源,P72 §6 零新自由参数核对表):
    - τ(g) = ``kernel.cw_economy.interest(gold, cap_resolved)`` 直消费
      (息律档数分量单一源,禁第二实现;cap_resolved 必须传
      cap_resolved_of_session 口径——投资覆写语境裸 level 推 cap 会
      错线,消费位禁偷懒);
    - ρ = ``refresh.r2_card_reserve``(合格集最低费卡价,P54 §②);
    - Σ预留 = 下帧窗口一张命中卡价——与 ρ 消费**同一函数同参**
      (P54 A2 单刷波粒度整数下界)。⚠ 两分量并存是语义角色差异,
      多数帧数值相同不是重复项、禁删一:ρ = 本轮升级后买卡臂对一张
      命中卡的即时购买力;Σ预留 = 下帧窗口的购买力预留(ADR-0560
      三分量声明承继,并存保判据式与证明同形)。
    等级过滤口径:ρ/Σ预留取当前级(闸在升级授权前评估,与 P54 floor
    同帧同等级);R1 形式二的 L* 目标级重估是刷新语境,不辖本闸。

    ALL IN 豁免支(P72 §2.5,新增交互):位面末 boss 末战帧 R=0 ⟹
    L(g,s,0,Ī)≡0 且息/购买力无消费主体,(3a) 的保护对象(未来息流)
    不存在——机会成本恒零,预算闸前提不成立,放行花光。豁免谓词 =
    ``plane_last_battle`` 单一源(经本模块 ``_plane_last_battle`` 重导出
    委托),与 level_spend_blocked 的 (2) 支 ALL IN 豁免同谓词同帧
    判定(证明 §2.5 合取序,禁「(2) 豁免了 (3) 还拦」的分裂);
    ``session`` 参数即为其 nodes_of_plane 真值链新增。

    支A(C_realize=1 兑现链放行):板满 ∧ bench 有 2★ 等待件 = 升级
    人口位增量当帧可兑现——谓词与 ``kernel.cw_economy.schedule_upgrade``
    ①臂 / ``_upgrade_ul_threshold_ok`` ΔV_pop 指示项**成同步锚对**
    (同一 P39 指示项,改谓词多处同改,见 ``_realize_chain_ready``)。
    P39 ②「骨架义务 M3,arm2 无权否决存在性」:全段化若缺本支,
    arm1 帧会被量闸否决存在性——本支是 P72 消解该否决的 sanctioned
    机制(证明 §1 支A 姿态声明,沿 schedule_upgrade ①臂短路先例)。

    ⚠ P39 接缝处置(落码批核对点 B,ADR-0576 §判据):(3b) 数值完备
    账支(``ΔV_band ≥ s + L + 尖括号欠账``,C_realize=0 帧)**本批
    不落码**——math_proofs P39 明载 ΔV_band「窗口前提证伪的重锚
    ……禁单独作闸门」,该支在 C_realize=0 帧的收益侧承担项正是
    ΔV_band 独自,落码即以边界带未裁决量(sim 对拍项 2 在册)作
    决定性闸门。替代构造 = 承担项换位:全段化放行域由 (3a)(注册表
    量)∪ 支A(零标定构造谓词)承载,证明辖域内其余帧 fail-closed
    推迟(缺支B 只收窄放行域、永不放宽;防恒拒由 (3a) 开局结构性
    宽松承载,证明 §3)。支B 与支A②支(has_deployable 部署面接线,
    C_realize 完整评价面)挂账随 P39 sim 对拍项 2 裁决落码
    (01 §6 三要素 3:owner=编排者,期限=一个对局周期;P72 §5
    边界 3/5 同族观察)。

    行为语义:拒 = 该批升级**整批推迟**(攒到 10·τ(g)+ρ+Σ预留+s 的
    帧一次买齐)——禁「按闸值截断击数」的部分买(P48 整买 (1) 辖域);
    推迟目标随金位上移但 g 越过 g* 后固定为 g*+ρ+Σ预留+U_L,存在
    不动点无「追着息档永远攒不够」的发散(证明 §1 收敛性,禁误读为
    移动靶)。常开无开关(证明已闭环,strategy-work §3 第 1 档);
    pop_slot 升级臂不入闸(P71-a 是收益侧分域命题,ADR-0560 承继)。

    返回 (可行, 拒因);拒因恒 'levelup_budget_gate_blocked'(发射位
    分键同名,三处发射位共键)。s ≤ 0(无批可发)恒可行:闸辖「升级
    支出的量」,不制造支出。
    """
    if clicks * click_cost <= 0:
        return True, ''
    if _plane_last_battle(state, session):
        return True, ''      # ALL IN 豁免(P72 §2.5:R=0 机会成本恒零)
    if _realize_chain_ready(state, bench, deployed):
        return True, ''      # 支A:兑现链当帧可兑现(P39 ①臂姿态)
    from sr_od.application.currency_war.kernel.cw_economy import interest
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria.refresh import (
        r2_card_reserve,
    )
    rho = r2_card_reserve(k_members, bench, deployed, state)
    window_reserve = r2_card_reserve(k_members, bench, deployed, state)
    tau = interest(gold, cap_resolved)
    if gold - clicks * click_cost >= tau * 10 + rho + window_reserve:
        return True, ''
    return False, 'levelup_budget_gate_blocked'


def _realize_chain_ready(state: GameState, bench: list,
                         deployed: list) -> bool:
    """P72 支A 谓词:C_realize=1 判定(升级收益的兑现链当帧可兑现)。

    板满(deployed_occupied ≥ max_units)∧ bench 有 2★ 等待件——与
    ``kernel.cw_economy.schedule_upgrade`` ①臂及
    ``_upgrade_ul_threshold_ok`` ΔV_pop 指示项成同步锚对(同一 P39
    指示项的第三消费位,改谓词多处同改;禁止判据体外的平行实现,
    本注释与 contracts 锚为登记面非实现副本)。两支全断 ⟹
    C_realize=0 构造性精确零(证明 §2.3)。模块私有:非判据面公开
    函数,不入契约/旁路枚举表(契约由 levelup_budget_gate 键承载)。

    C_realize ②支(部署面合格谓词 ``kernel.cw_deploy_logic.has_deployable``
    接线)随支B 挂账(ADR-0576 §判据):谓词真源已在 kernel,接线需
    闸+检查器双面重建部署语境,随 C_realize 完整评价面批落码;早稿
    pop_slot 放宽支系「融资腿」非合格判据(P72 §2.3 勘误锚承继)。
    """
    from sr_od.application.currency_war.kernel.cw_state import (
        deployed_occupied,
    )
    cap = state.max_units()
    if cap is None:
        return False
    if deployed_occupied(list(deployed or [])) < cap:
        return False
    return any(b is not None and (getattr(b, 'star', 1) or 1) >= 2
               for b in (bench or []))


def batch_form(level: int, target_level: int) -> bool:
    """批量成型判据(M3 批形态:目标级差>0 才有批;义务侧消费)。"""
    return level < target_level


def level_spend_blocked(state: GameState, session: StrategySession,
                        registry: DecisionV2Registry | None = None) -> bool:
    """危机带内整批经验授权让位保命面(实机复盘 g_20260904_054904
    p2r1 候选③:hp=1 败即死帧 9×LevelUpShop 36g,m3_batch 批授权把
    67% 金转为本帧零收益经验)。M3 发射位(mandate/shop 两域)消费。

    两支,全部单一源判据,零新自由参数:
    - ``discipline.blood_budget_levelup_blocked``(decision_v2 同源,
      P21 已证:hp ≤ 停升级线内升级收益到账 ≥1 战之后,EV=−C−I 严格
      负,敏感网格全负域免 β)——cw4 栈 M3 此前未消费该门,同帧
      decision_v2 侧已停、cw4 侧照发 = 双栈语义断层(p2r1 实证帧);
    - P2 危机带 ``discipline.p2_crisis_band``(hp ≤ ceil(2×vd_p2_loss)
      ≈41 = P21 d=2「到账更慢」档;经验收益兑现链 ≥2 战,与危机带
      搜索停付同一判据、同一血线单一源——P48 三段管辖 λ>0 段
      「转化优先、S 线降级」;与 arbiter._crisis_buy_gate_open 同语义
      族成对:停未来面、开当轮转化面)。
    ALL IN 豁免(位面末 boss 战花光,[18])两支共享——blood_budget_
    levelup_blocked 内含,危机支同判让位(末战花光是时机不是血线
    判断)。hp 不可信帧由 blood_budget 支 fail-closed 拒付(危机会
    在内)。

    血线硬地板解锁包件①(≤15 族在册授权,00§3/NMF 在册「不影响发展
    为主线」条件):死亡线帧(判据单一源 = predicates.p1_blood_floor,
    阈值常量 = lambda_death.HP_BAND_NEAR_DEATH)M3 破息批**解锁至
    饱和线下**——p1_levelup_stop_hp 停付线(≈11 ⊂ ≤15 重叠域)以地板
    为准重裁让位(14号稿 N3①);ALL IN 豁免族同型语义 = 深血线花光
    是转化时机判断,非血线判断。不可信帧地板 fail 向不判线,停付维持
    既有 fail-closed。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.predicates import (
        p1_blood_floor,
    )
    if p1_blood_floor(state):
        return False    # 死亡线:转化优先,停付线让位(解锁包件①)
    from sr_od.application.currency_war.kernel.cw_discipline_rules import (
        blood_budget_levelup_blocked,
        p2_crisis_band,
    )
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    reg = registry if registry is not None else DEFAULT_REGISTRY
    if blood_budget_levelup_blocked(state, session, reg):
        return True
    if _plane_last_battle(state, session):
        return False    # ALL IN 窗:停手让位(与血预算支同一豁免序)
    return p2_crisis_band(state, reg)


def _plane_last_battle(state: GameState, session: StrategySession) -> bool:
    """位面末最后一战判定(cw4 消费面;单一源 =
    decision_v2.discipline.plane_last_battle 的重导出委托,禁第二实现;
    模块私有——非判据面函数,不入契约/旁路枚举表)。"""
    from sr_od.application.currency_war.kernel.cw_discipline_rules import (
        plane_last_battle as _plb,
    )
    return _plb(state, session)


def pop_slot(deployed_count: int, deploy_cap: int, gold: int,
             bench_candidates: int, floor_gold: int, *,
             buyable_candidate: bool = False, bench_free: int = 0,
             ) -> tuple[bool, str]:
    """D-lv7(OPEN 检查点):「满编+富金+bench 有候补 → 升 cap 上人」覆盖。

    返回 (是否发射升 cap 意图, 决策迹理由——不触发时显式理由,
    R189-5 D-lv7 行:「判据合法不触发须显式理由进决策迹」)。

    前置放宽(14号稿 §4.3,零参数):「bench_candidates > 0」改为
    「bench 有候选 ∨ 买入面有可即时买入的线内候选(affordable ∧
    bench_free ≥ 1)」——从「已持有候补」放宽到「买得起候补」;臂①落地
    后 bench 空帧大幅减少,本修正兜剩余帧(满编+空 bench+富金末段)。
    """
    if deployed_count < deploy_cap:
        return False, 'not_full'          # 未满编:普通 M1 部署辖
    has_candidate = bench_candidates > 0 or (buyable_candidate
                                             and bench_free >= 1)
    if not has_candidate:
        return False, 'no_bench_candidate'
    if gold < floor_gold:
        return False, 'gold_below_floor'
    return True, 'full_rich_with_candidate'
