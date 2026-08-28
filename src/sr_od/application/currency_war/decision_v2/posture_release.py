"""未成型期姿态:泄息通道(release)——FLIP 谓词/预算三方合并/slot 守卫。

设计=唯一规格:`.debug/temp/currency_war/w328_unformed_posture/DESIGN.md`
(设计终版,对抗修订二轮已吸收)。结论先行:参数无关的确定结论是
「>50 溢余段持有边际恒为 0(息封顶截断)→ 泄息通道必须结构性存在,
通道静默关闭是确定性缺陷」;方向性结论(hold vs spend 的 EV 排序)在诚实
参数带内不稳——本模块只实现「通道开+预算内按 EV 排序」的中性行为,
不预设方向(k(hp)/Δhp/boss 税标定归 sim 批,参数见 registry)。

辖域与覆盖关系(DESIGN §②):
- hp ≤ emergency_hp(25)→ 应急态全权接管(清仓/保命优先),release 让位;
  两谓词辖区不相交([25,∞) 归 FLIP 评估,≤25 归应急);
- FLIP = 可信 hp ∧ P1/P2 ∧ g>50 ∧ hp>25 ∧(末窗: 投影命中
  hp−boss 税位面锚<25,战后必入应急带的机制理由——保命义务相位无关;
  ∨ FORM 相位 ∧ 非末窗: hp<40,持续兑现逻辑);
  hp<40 依据分级:社区攻略通行的中盘健康线(非口述标准值;口述 [18] 明确
  hp=报警量不设触发标准值),作用=非末窗臂的持续兑现资格判,调参归 sim 批;
- 末窗 = boss 破息窗(``discipline.boss_window_active`` 统一口径=boss 首买
  相位;round 臂「r≥NODES_PER_PLANE−1」实证双失效已废除——过宽(r8 非 boss
  轮套 boss 税语义错误)/全盲(短位面局 r≥8 永不触发),DESIGN §② N1);
- latch 窗口单位=boss 窗单轮:命中即激活本窗,窗内不回退(防 hp 39↔41
  抖动姿态振荡);假帧(100 兜底帧=开局全无真值,hp_readable/hp_trusted
  皆 False)不评估;shop 开态沿用 last_hp_real 的帧放行(ADR-0428);
  辖域=P1/P2 未成型期(P3 不辖,DESIGN §附5)。

三方刷金预算合并(DESIGN §②规则4,同一帧三个独立预算来源):
| 来源 | 语义 | 值 |
| release 溢余预算 | 必须花的下界(地板) | g−50(折刷数÷刷价) |
| DP refresh_budget | DP 授权可刷上界(动作码 1/2/3=2/4/6 刷) | ``_ROLLS_OF_ACTION`` |
| plan 层 _refresh_cap | 评分层可刷上界(自带 HP-gate 与档金表) | cw_evaluate._refresh_cap |
合并规则:FLIP 未命中帧维持现状(许可取交);FLIP 命中帧 release 预算覆盖
``budget = max(g−50, DP refresh_budget)``,_refresh_cap 的 HP-gate 让位
(血量维度已由 FLIP 谓词评估,同一维度只评一次防双主),其档金表仍作刷价
合法性校验保留。一句话:release 是义务(下界),DP/plan 是许可(上界),
义务激活时义务优先,未激活时许可取交。成型帧末窗投影臂的义务预算
消费定向化:预算保留但只许花在找件/升级、禁盲刷(门=
authorize_release_refresh 按 ReleaseDirective.directed_only/find_ok;
slot 守卫第三路径注入不辖——定向化会重新造出泄息通道静默面)。

slot 守卫与 rush_level 的同轮裁决(DESIGN §②规则1-3):
1. slot 守卫先于姿态选择:末窗 ``deployed<cap``(有空位)时追级的人口
   解锁边际本窗=0(新槽位下位面才兑现)→ rush_level 不生效,输出 release
   (run48 r9 deployed 5/6 即此帧);
2. cap 满员 ∧ bench 有可上阵件:追级与泄息同轮并存,同一笔溢余预算
   (Posture 保留 level_up=True,refresh_budget 取合并值);
3. 第三路径显式注入:DP 姿态可为纯 level_up(refresh_budget=0)——slot
   守卫压 level 后若落默认顺序判会掉 hold(泄息通道静默关闭),故显式注入
   ``release_budget = max(g−50, DP refresh_budget×刷价)``(DP 已有授权时
   不缩水,纯 level_up 帧取 g−50),预算>0 → 姿态强制输出 release。

消费点:``strategy.decide_prep``(每轮入口包装 DP 姿态写 session)→
``arbiter`` 刷新收尾块(release 义务预算的有界放行)→ 活栈消费门
``spend_gate_active``(decision_v2.scoring 息 EV 中性 / candidates 凑息向
卖候选抑制,判据单一源=本模块读 ``session.v3_release``)。
``NodeGoal.spend_mode='release'`` 是**预留档位,当前无生产者**——
``cw_horizon._horizon_node_goal`` 只产 level/adaptive/interest;FLIP 是
带 latch 的帧级态,不进 horizon 纯函数(否则同轮多次查询随 gold/hp 快照
翻转,且绕开唯一 latch 所有者造第二判定源)。v1 栈两消费点
(``cw_evaluate._economy_mode_for``/``cw_plan._maybe_sell_for_interest``)
不在活决策路径上(活栈 ``DecisionV2Strategy.decide_prep`` 全量覆写
default 栈),其 release 档映射已删。release 帧行为的单一源=本模块经
session 通道。
"""
from __future__ import annotations

from dataclasses import dataclass

from sr_od.application.currency_war.cw_horizon import Posture
from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.registry import (
    DecisionV2Registry,
)


@dataclass(frozen=True)
class ReleaseDirective:
    """release 帧的泄息指令(轮内派生量,写 ``session.v3_release``)。

    budget_gold: 泄息预算(金;= max(g−interest_floor, DP 预算×刷价)),
    刷新累计花费不得越过(arbiter 收尾块逐笔扣账);
    rolls: 预算折刷数(÷刷价,向下取整);
    third_path: True=slot 守卫压 level 的显式注入(DESIGN §②规则3;
    False=FLIP 命中帧,DP 姿态保持原样仅合并预算)。
    directed_only: True=成型帧末窗投影臂——义务预算消费定向化:只许
    花在找件(店内存在可找名集件,find_ok=指令创建帧的存在性快照)与
    升级(走既有升级授权链,不经本预算门),禁盲刷(店内无可找件时
    authorize_release_refresh 拒;boss 窗 latch 单位=单轮、arbiter 每轮
    至多一次收尾刷新,快照陈旧面有界)。
    find_ok: directed_only 帧的找件存在性快照(创建帧店内扫描;非
    directed_only 帧恒 True=本门不辖)。
    """

    budget_gold: int
    rolls: int
    third_path: bool = False
    directed_only: bool = False
    find_ok: bool = True


def refresh_cost_of(state: GameState) -> int:
    """刷价实读(缺失兜底 2;与 ``state.shop_refresh_cost`` 默认一致)。"""
    return state.shop_refresh_cost or 2


def slot_guard_blocks_level(state: GameState) -> bool:
    """slot 守卫:deployed<cap(有空位)∧ bench 有可上阵件。

    语义=追级的人口解锁边际本窗为 0(新槽位下位面才兑现;[32](b)
    「空位再升纯浪费」同判据族)——此时 rush_level 不生效。
    """
    from sr_od.application.currency_war.cw_state import (
        bench_occupied,
        deployed_occupied,
    )
    return (deployed_occupied(state.deployed or []) < state.max_units()
            and bench_occupied(state.bench or []) > 0)


def hp_decision_trusted(state: GameState) -> bool:
    """hp 决策可信位(单一源):``state.hp_readable or state.hp_trusted``。

    同模块(及跨模块引用点)禁再手写双位判定(W393 A1.1 单一源纪律):
    语义=ADR-0282 对账层「沿用真值帧放行 vs 兜底假值帧拒」(ADR-0428
    收紧口径)——100 兜底帧(开局全无真值,两位皆 False)不评估,
    shop 开态沿用 last_hp_real 的帧(hp_readable=False ∧ hp_trusted=True)
    放行。新增 hp 守卫消费点一律走本 helper。
    """
    return state.hp_readable or state.hp_trusted


def flip_hit(state: GameState, session: StrategySession,
             registry: DecisionV2Registry, phase_value: str) -> bool:
    """FLIP 谓词(攒息 → 花钱的翻转条件;DESIGN §②)。

    phase_value 由调用方传每轮入口派生的相位('FORM'=form_ok False,
    未成型判定口径=决策相机 phase=FORM;handoff.engines<2 是局后口径,
    禁混用)。辖区:[emergency_hp,∞) 归本谓词,≤emergency_hp 归应急。
    辖域例外:末窗投影臂相位无关——「boss 战后必入应急带」是保命义务,
    与成型分期无关(实机进店帧实证:phase=SPEND/hp=38/gold>50/boss 窗
    激活/投影命中,曾被 FORM 相位门挡死致泄息通道结构性静默)。
    """
    if not hp_decision_trusted(state):
        return False    # 假帧不评估:仅 100 兜底帧(开局无真值)拒;shop 开态
                        # 沿用 last_hp_real 的帧 hp 是可信值,放行(ADR-0428;
                        # 可信位语义=ADR-0282 对账层「沿用真值 vs 兜底假值」;
                        # 判定单一源=hp_decision_trusted)
    if state.plane > 2:
        return False    # 辖域 P1/P2 未成型期(DESIGN §附5)
    floor = registry.interest_floor
    if (state.gold or 0) <= floor:
        return False    # 只消费溢余段(预算恒=g−50,不新增破息例外)
    if state.hp <= registry.emergency_hp:
        return False    # 应急辖区,release 让位(双触发防护)
    if boss_first_buy_phase(state, session, registry):
        # 末窗投影臂(相位无关):hp − boss 税位面锚 < emergency_hp
        # (防战后坠入应急带;保命义务与成型相位无关,持续兑现臂才辖 FORM)。
        # 锚单一源=registry.boss_tax_p75_by_plane(与 filters 投影安全带
        # 同源同款取数):本函数上方 plane>2 已拒,此处 plane ∈ {1,2},
        # 两键必有槽位,直接字典访问、无需标量兜底。
        # 旧标量 boss_tax_p75 自此(ADR-0441 接线)无运行时消费点,
        # 保留理由与退役结论见 registry 字段注释。
        return (state.hp
                - registry.boss_tax_p75_by_plane[state.plane]
                < registry.emergency_hp)
    if phase_value != 'FORM':
        return False    # 持续兑现臂维持 FORM 辖域(DESIGN §②原文)
    # 持续兑现臂:报警带 hp<blood_margin_low_hp(血边际已低,溢余该花)
    return state.hp < registry.blood_margin_low_hp


def boss_first_buy_phase(state: GameState, session: StrategySession,
                         registry: DecisionV2Registry) -> bool:
    """末窗 = boss 首买相位(单臂锚;discipline.boss_window_active 单一源)。

    复用既有统一口径(节点图 node_type∈boss_round_node_types 为主,
    r≥9 轮数仅作 node_type 缺读兜底)——不另造第二 boss 窗判据。
    """
    from sr_od.application.currency_war.decision_v2.discipline import (
        boss_window_active,
    )
    return boss_window_active(state, session, registry)


def _findable_in_shop(state: GameState, session: StrategySession,
                      registry: DecisionV2Registry) -> bool:
    """找件存在性:店内有可找的名集件(目标∪高费强件)。

    名集单一源=decision_v2.filters._refreshable_names(定向刷新同款
    名单,只作存在性判与评分先验,买谁由 EV 层定价)。
    """
    from sr_od.application.currency_war.decision_v2.filters import (
        _refreshable_names,
    )
    names = _refreshable_names(state, session, registry)
    return any((getattr(card, 'name', '') or '') in names
               for card in (state.shop or []))


def release_directive(state: GameState, session: StrategySession,
                      registry: DecisionV2Registry, phase_value: str,
                      posture: Posture) -> ReleaseDirective | None:
    """本帧的泄息指令(FLIP 命中 ∨ slot 守卫第三路径;None=维持原姿态)。

    纯函数(不写 session;latch 由调用方 ``evaluate_release`` 承担)。
    """
    if not registry.release_enabled:
        return None
    cost = refresh_cost_of(state)
    overflow = max(0, (state.gold or 0) - registry.interest_floor)
    # 第三路径(DESIGN §②规则1/3)先于 FLIP 判定:末窗 slot 守卫压 level
    # → 显式注入泄息预算,强制输出 release 不落 hold(防泄息通道静默关闭)。
    # 辖域=末窗(规则1 原文「末窗评估 deployed<cap 时 rush_level 豁免
    # 不生效」);规则1 的理由(新槽位下位面才兑现)与成型相位无关,故
    # 末窗投影臂相位无关后必须仍先于此处之下的 FLIP 规则2 判定,否则
    # 已成型末窗帧会被 FLIP 遮蔽、追级人口解锁边际=0 的压制丢失。
    # 非末窗的持续兑现由 FLIP 持续臂承担。
    # hp 守卫走可信位 helper(与 FLIP 门同源):实机 shop 帧 readable 恒
    # False,hp 是沿用真值(trusted=True)时第三路径 slot 压制必须照常
    # 生效——严格 hp_readable 曾使第三路径在实机主消费面结构性失效;
    # 100 兜底帧(两位皆 False)仍拒,兜底语义不变(ADR-0428)。
    if (posture.level_up
            and boss_first_buy_phase(state, session, registry)
            and hp_decision_trusted(state)
            and state.plane <= 2
            and state.hp > registry.emergency_hp
            and overflow > 0
            and slot_guard_blocks_level(state)):
        budget_gold = max(overflow, posture.refresh_budget * cost)
        return ReleaseDirective(budget_gold=budget_gold,
                                rolls=budget_gold // cost if cost else 0,
                                third_path=True)
    if flip_hit(state, session, registry, phase_value):
        # FLIP 命中帧:release 预算覆盖(义务优先);DP 已有授权时不缩水。
        # cap 满员时(slot 守卫 False,不走上段)posture.level_up 保留
        # (追级与泄息同轮并存,同一笔溢余预算,DESIGN §②规则2);预算表:
        # rule2 的 level 费用硬界由升级授权链(ev.levelup_ev_basis 可负担性)
        # 自辖,不在此重复扣。
        # 成型帧末窗投影臂义务预算消费定向化:成型帧(form_ok=True,
        # phase≠FORM)的泄息期望收益未论证,预算保留但只许花在找件/升级,
        # 禁盲刷——盲刷授权在 authorize_release_refresh 按 find_ok 拒。
        # 第三路径(slot 守卫注入)不辖:其语义=防泄息通道静默关闭,
        # 定向化会重新造出静默面。
        directed_only = (boss_first_buy_phase(state, session, registry)
                         and phase_value != 'FORM')
        find_ok = (_findable_in_shop(state, session, registry)
                   if directed_only else True)
        budget_gold = max(overflow, posture.refresh_budget * cost)
        return ReleaseDirective(budget_gold=budget_gold,
                                rolls=budget_gold // cost if cost else 0,
                                directed_only=directed_only,
                                find_ok=find_ok)
    return None


def wrap_posture(posture: Posture, directive: ReleaseDirective) -> Posture:
    """DP 姿态 → release 姿态(spend_mode 状态机新档 'release' 的载体)。

    - FLIP 帧(third_path=False):level_up 保留(并存裁决),refresh_budget
      取 max(DP, release 折刷)(合并规则:义务激活时义务优先);
    - 第三路径帧:level_up 压掉(slot 边际=0),强制输出 release。
    下游消费(scoring P2 窗二分/gold_floor DP 花费授权/levelup 'dp' 臂)
    读同一 Posture,无需各自感知 release;tag='release' 同时是遥测披露面
    (dp_posture 影子行可判读)。
    """
    return Posture(save=False,
                   level_up=False if directive.third_path
                   else posture.level_up,
                   refresh_budget=max(posture.refresh_budget,
                                      directive.rolls),
                   v=posture.v,
                   tag='release')


def evaluate_release(state: GameState, session: StrategySession,
                     registry: DecisionV2Registry, phase_value: str,
                     posture: Posture) -> tuple[Posture, ReleaseDirective | None]:
    """轮入口包装:算指令 + latch(窗内不回退)+ 姿态合并。

    latch 语义:同轮(键=plane,round)内已激活的指令不因 hp 重读抖动
    回退(DESIGN §②防间隙);轮键变化自然失效(boss 窗单轮单位,无跨轮
    语义)。每轮首段消费方须先重置 ``v3_release_spent``(预算逐轮清零)。
    """
    key = (state.plane, state.round_num)
    directive = release_directive(state, session, registry, phase_value,
                                  posture)
    if directive is None and registry.release_enabled \
            and getattr(session, 'v3_release_round', None) == key:
        prev = getattr(session, 'v3_release', None)
        if prev is not None:
            directive = prev    # latch:窗内不回退
    if directive is not None:
        session.v3_release = directive
        session.v3_release_round = key
        return wrap_posture(posture, directive), directive
    return posture, None


def spend_gate_active(session: StrategySession,
                      registry: DecisionV2Registry) -> bool:
    """release 帧活栈消费门(scoring 息 EV 中性 / 凑息向卖抑制的统一判据)。

    判据单一源 = ``session.v3_release``(evaluate_release 每轮入口写入,
    与义务预算/latch 同源)——消费面(decision_v2.scoring/candidates)经此
    读 release 态,不在各自层重算 FLIP(防第二判定源绕开 latch)。
    ``registry.release_spend_gate_enabled``=False(默认)时恒 False =
    消费门未接线时的行为逐位一致(A/B 基线臂零漂移);开臂时机=A/B 裁决
    收口后(registry 字段注释)。
    """
    return (registry.release_spend_gate_enabled
            and getattr(session, 'v3_release', None) is not None)


def authorize_release_refresh(session: StrategySession,
                              working_gold: int, cost: int,
                              registry: DecisionV2Registry) -> str:
    """release 义务预算的刷新放行裁决(arbiter 刷新收尾块消费)。

    返回授权说明串(空串=不放行)。有界放行:累计刷金 ≤ 预算 ∧ 花后金
    ≥ boss_floor(P1 出口金生存边际,与 M-A 定向刷新同款兜底)。
    语义=「通道开+预算内按 EV 排序」的中性行为(DESIGN §⑤):预算是
    义务下界,不强制花满——正分 V_D 刷新走既有路径,本门只放行被
    息纪律门拦住的负分刷新(搜索成本显式裁定,同 W249 病灶修法)。
    directed_only 帧(成型帧末窗投影臂)消费定向化:find_ok=False
    (店内无可找件)拒——禁盲刷;找件帧放行,升级不经本门不受辖。
    """
    directive = getattr(session, 'v3_release', None)
    if directive is None or cost <= 0:
        return ''
    if directive.directed_only and not directive.find_ok:
        return ''   # 成型帧定向化:店内无可找件,盲刷不构成泄息义务的合规消费
    spent = getattr(session, 'v3_release_spent', 0)
    if spent + cost > directive.budget_gold:
        return ''
    if working_gold - cost < registry.boss_floor:
        return ''
    session.v3_release_spent = spent + cost
    return (f'release 泄息预算放行(累计{spent}+{cost}'
            f'/{directive.budget_gold}金,third_path={directive.third_path})')
