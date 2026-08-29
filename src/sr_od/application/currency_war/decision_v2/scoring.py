"""决策框架 v2 层3:板面查表评分(ADR-0290 对抗修订①)。

评分对象=**候选后板面**:apply 候选到 state 副本(轻量 apply——买/升级
后接部署管线,只改评分需要的维)→ 查「板面形态→期望」表。

**禁止单卡边际拆分**(P3 证的是 e0→e1/e1→e2 档位边际,非单卡;
e2 格 n=9/±30%)——本模块对板面只看形态维(过渡体系数/配方档/金),
不做任何「这张卡值多少」的拆分。

查表项(初版,registry 注入可 A/B;**未标定**——标定 gate 见
ADR-0290 实施序③):
- 档位×P3 系数(rung_value:e0→e1 +1.4 / e1→e2 +1.6 金/轮累计);
- 息律 EV([17]:min(5, gold//10) × 剩余轮);
- H3 战力表插值(胜率阶梯 × 掉血期望 × HP 金价)。
score 返回 (value, breakdown)——每轮候选×分数表判读可直接读。
"""
from __future__ import annotations

from dataclasses import dataclass

from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.candidates import Candidate
from sr_od.application.currency_war.decision_v2.filters import (
    crisis_hoard_active,
    is_emergency,
)
from sr_od.application.currency_war.kernel.cw_line_defs import (
    RECIPE_BASE,
    recipe_tier,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_state import (  # ADR-0392 helper 导入
    BuyCard,
    GameState,
    SellBench,
    bench_occupied,
    deployed_occupied,
    deployed_place,
    simulate,
)


def _interp(table: dict[int, float], x: float) -> float:
    """阶梯表线性插值(键 0/1/2;x 超界取端点值)。"""
    xs = sorted(table)
    if x <= xs[0]:
        return table[xs[0]]
    if x >= xs[-1]:
        return table[xs[-1]]
    for lo, hi in zip(xs, xs[1:], strict=False):
        if lo <= x <= hi:
            frac = (x - lo) / (hi - lo)
            return table[lo] * (1 - frac) + table[hi] * frac
    return table[xs[-1]]


def board_rung_x(state: GameState,
                 registry: DecisionV2Registry) -> float:
    """板面形态维 x:过渡体系数(整数档)+ 配方档小数(H3 插值用)。

    形态域=**混合域**(ADR-0295:deployed 星级×1.0 主导 + bench 星级
    ×registry.bench_form_weight 折减)。ADR-0293 标定残差根因:持有域
    (deployed∪bench 等权)形态代理在 r7-r8 全顶格而真实战力弱
    (bench 囤种子件撑满代理 → 一切买入 0.00 分,seed 900032 实证)。
    折减后 bench 件仍是形态期权(买入经部署管线上板即全额显影),
    但囤 bench 不再封顶 rung。体系判定与 sim/判读同源
    (cw_sim._engines_count:仙舟3/列车2/DOT2/希儿系;希儿系要求
    希儿 deployed 在场——bench 希儿不算引擎,deployed 主导语义);
    配方档小数 =recipe_tier/RECIPE_BASE × 系数(未标定)。
    """
    from sr_od.application.currency_war.kernel.cw_battle_calib import _engines_count
    fac, main, dep_names = _held_form_weights(state, registry)
    engines = _engines_count(fac, dep_names)
    frac = min(recipe_tier(main) / RECIPE_BASE, 1.0)
    return min(2.0, float(engines)
               + registry.rung_frac_per_recipe_tier * frac)


def _held_form_weights(state: GameState,
                       registry: DecisionV2Registry
                       ) -> tuple[dict[str, float], dict[str, float],
                                  frozenset[str]]:
    """混合域加权聚合:(factions+flows 计数, 主阵营计数, deployed 名集)。

    deployed 件按星级全额(与星级加权展开同口径),bench 件按
    星级×bench_form_weight 折减(ADR-0295);聚合口径与 cw_sim
    ._board_factions_of / _board_counts_of 同构(此处加权复刻而非
    复用——cw_sim 计数函数按件数 +1,不支持分数权重)。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS as _CH
    fac: dict[str, float] = {}
    main: dict[str, float] = {}
    dep_names: set[str] = set()

    def _add(d, w: float) -> None:
        ch = _CH.get(getattr(d, 'char_id', '') or '')
        if ch is not None:
            for f in (ch.factions or ()) + (ch.flows or ()):
                fac[f] = fac.get(f, 0.0) + w
        f0 = getattr(d, 'faction', '') or ''
        if f0 and f0 != '?':
            main[f0] = main.get(f0, 0.0) + w

    for d in state.deployed or []:
        if d is None:   # ADR-0392 槽位表空槽
            continue
        star = max(1, int(getattr(d, 'star', 1) or 1))
        _add(d, float(star))
        if getattr(d, 'char_id', ''):
            dep_names.add(d.char_id)
    for d in state.bench or []:
        if d is None:
            continue   # ADR-0316 槽位表空槽
        star = max(1, int(getattr(d, 'star', 1) or 1))
        _add(d, star * registry.bench_form_weight)
    return fac, main, frozenset(dep_names)


def _held_star_weighted(state: GameState) -> list:
    """持有域(deployed∪bench)的星级加权展开:2★ 计 2 份、3★ 计 3 份。

    3合1 合并(3 副本→1 件升星)在件数计数上是「掉件」,星级不
    加权时合并触发买被评负分(买入→合并→引擎/配方计数反降,
    smoke 实证 -13 分全弃)——星级加权让合并的战力显影为计数。
    ADR-0295 后仅服务目标件持有进度项(形态 rung 已换混合域加权,
    见 _held_form_weights)。
    """
    held: list = []
    for d in (state.deployed or []) + [b for b in (state.bench or [])
                                       if b is not None]:
        star = max(1, int(getattr(d, 'star', 1) or 1))
        held.extend([d] * star)
    return held


def _engine_frac_remainder(state: GameState,
                           registry: DecisionV2Registry) -> float:
    """过渡体系进度小数余量(ADR-0301 成型进度项)。

    progress=Σ min(加权计数/tier, 1)(三羁绊,混合域权重同
    board_rung_x);engines=整数引擎数(含希儿系)。余量
    =max(0, progress−engines):未跨越阈值的进度部分。买入
    进度件(bench ×0.35 / deployed ×1.0)推高余量 → 评分显影;
    阈值跨越瞬间余量清零、值转进 rung_value(整数档)——与
    rung 互补不双计。希儿系是 deployed 二元判定,无小数进度,
    不参与本项。
    """
    from sr_od.application.currency_war.kernel.cw_battle_calib import (
        _engines_count,
    )
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        TRANSITION_TRAITS as _TRANSITION_TRAITS,
    )
    fac, _main, dep = _held_form_weights(state, registry)
    engines = _engines_count(fac, dep)
    progress = sum(min(fac.get(b, 0.0) / tier, 1.0)
                   for b, tier in _TRANSITION_TRAITS)
    return max(0.0, progress - engines)


def _core_star_count(state: GameState, session: StrategySession,
                     registry: DecisionV2Registry) -> float:
    """核心升星持有量(迁移审计 w88(git 历史)/ADR-0339,[13] 三件套第三件的评分显影)。

    持有域内 star≥2 且∈目标集(意向目标∪引擎件——引擎件任何模式下
    都是方向件)的件数;deployed 全额、bench ×registry.bench_form_weight
    折减(ADR-0295 混合域同式)。star 此前只在阵营计数(star×权重)与
    targets 星级加权显影,engines 封顶后 2★ 分差≈0——换阵卖 2★ 不罚分
    /凑合副本 ≈0 分(第六局 run_20260825_115418:r1 三月七 2★ 达成、
    r6 换阵卖出、boss 板全 1★,-32 伤害罚款残留)。
    """
    from sr_od.application.currency_war.decision_v2.candidates import (
        _target_names,
    )
    tset = _target_names(state, session)
    if not tset:
        return 0.0
    n = 0.0
    for d in (state.deployed or []):
        if d is not None and getattr(d, 'star', 1) >= 2 \
                and getattr(d, 'char_id', '') in tset:
            n += 1.0
    for b in (state.bench or []):
        if b is not None and getattr(b, 'star', 1) >= 2 \
                and getattr(b, 'char_id', '') in tset:
            n += registry.bench_form_weight
    return n


def _merge_progress_count(state: GameState, session: StrategySession,
                          registry: DecisionV2Registry) -> float:
    """3合1 中间进度项(迁移审计 w96(git 历史)/ADR-0340,[13] 副本凑合 × [17] 溢余该花)。

    目标集内、尚无 star≥2 持有的名字,其 1★ 副本份数的中间进度:
    每名只计第 2 份(份数 1→2 = 1 进度;第 3 份 merge 成 2★ 后由
    core_star 承接,star≥2 持有则本项对该名让位,两侧不双计)。
    域权重 ADR-0295 同式:该名有 deployed 副本 ×1.0,纯 bench 副本
    ×bench_form_weight 折减。修的是 迁移审计 w93(git 历史) 断买根因①:目标件第 2 份
    (1★)买入在 targets(集合隶属封顶)/eng_frac(只辖三过渡体系)/
    core_star(star≥2 门)/rung(整数档)全维度零 delta → 仲裁层
    「非正分」拒 → 金 59→90 溢出趴三轮([17] >50 每一分都该花)。
    """
    from sr_od.application.currency_war.decision_v2.candidates import (
        _target_names,
    )
    tset = _target_names(state, session)
    if not tset:
        return 0.0
    dep_c: dict[str, int] = {}
    ben_c: dict[str, int] = {}
    star2: set[str] = set()
    for d in (state.deployed or []):
        name = getattr(d, 'char_id', '') or ''
        if d is None or name not in tset:
            continue
        star = getattr(d, 'star', 1) or 1
        if star >= 2:
            star2.add(name)
        else:
            dep_c[name] = dep_c.get(name, 0) + 1
    for b in (state.bench or []):
        name = getattr(b, 'char_id', '') or ''
        if b is None or name not in tset:
            continue
        star = getattr(b, 'star', 1) or 1
        if star >= 2:
            star2.add(name)
        else:
            ben_c[name] = ben_c.get(name, 0) + 1
    n = 0.0
    for name in set(dep_c) | set(ben_c):
        if name in star2:
            continue    # 已 2★:core_star 承接,本项让位
        copies = dep_c.get(name, 0) + ben_c.get(name, 0)
        if copies >= 2:
            n += 1.0 if dep_c.get(name, 0) > 0 else registry.bench_form_weight
    return n




def score_state(state: GameState, registry: DecisionV2Registry,
                session: StrategySession | None = None) -> dict[str, float]:
    """板面形态→期望 查表(评分的单一真值;只看形态维)。"""
    x = board_rung_x(state, registry)
    rung = _interp(registry.rung_value, x) * registry.rounds_left_est
    win = _interp(registry.h3_win_rate, x)
    power = (win * registry.expected_battle_loss
             * registry.hp_to_gold * registry.battles_left_est)
    # 息 EV 只在满息平台(≥interest_floor)上计值——平台由层4 阶梯
    # 地板/interest_rule 维护;<50 金的政策是「档内全花,息让位配方」
    # (v1 同式),评分若对 <50 的档位跨越扣息 EV = 与地板政策双重
    # 计罚,合法买入被评负分全弃(smoke 实证);单一源对齐。
    # war 破息窗的 50 平台破碎(50→49)只付真实息损的平滑见
    # score_candidate 的 ADR-0332 息崖平滑段(不动本项绝对值)。
    # release 帧泄息义务激活(判据单一源=posture_release.spend_gate_active
    # 读 session.v3_release)时息 EV 整项计 0:溢余段预算=g−interest_floor
    # 已裁定必花,「卖出涨息加分/跌破平台扣分」的计值与泄息意图对冲
    # (凑档卖息的对冲面);base/after 同置 0 → 候选排序中本项静默,
    # 开关关(基线臂)时零漂移。
    _rel_gate = False
    if session is not None:
        from sr_od.application.currency_war.decision_v2.posture_release import (
            spend_gate_active,
        )
        _rel_gate = spend_gate_active(session, registry)
    interest = 0.0
    if not _rel_gate and (state.gold or 0) >= registry.interest_floor():
        interest = (min(registry.interest_cap, (state.gold or 0) // 10)
                    * registry.interest_rounds)
    # 目标件持有进度(集合隶属计数:持有域内∈目标集的星级加权
    # 件数/基线,封顶——形态维之一;cap 饱和时目标件的持有期权
    # 在此项显影,未标定)。ADR-0295:天花板折减(target_hold_
    # cap_frac)——持有进度顶格不再=满形态(残差根因的配套修)
    targets = 0.0
    if session is not None:
        from sr_od.application.currency_war.decision_v2.candidates import (
            _target_names,
        )
        tset = _target_names(state, session)
        if tset:
            held = _held_star_weighted(state)
            n = sum(1 for d in held
                    if getattr(d, 'char_id', '') in tset)
            targets = (min(registry.target_hold_cap_frac,
                           n / max(1, registry.target_hold_base))
                       * registry.target_hold_value)
    depth = _deployable_depth(state) * registry.depth_unit_value
    # 引擎分数进度(ADR-0301):未跨越整数档的进度余量 × 单位值
    # (P3 期权价值;0=关闭——A/B 基线臂)
    eng_frac = (_engine_frac_remainder(state, registry)
                * registry.engine_frac_unit)
    # 核心升星价值(ADR-0339):[13] 过渡核心 2★ 的独立伤害维显影
    # (rung/engines 只辖羁绊计数,power 只按 engines 档插值——2★ 的
    # [27] 伤害减罚此前零显影);0=关闭
    core_star = (_core_star_count(state, session, registry)
                 * registry.core_star_unit)
    # 3合1 中间进度(ADR-0340):目标件第 2 份(1★)的期权显影
    # ——core_star 的 star≥2 门之前的爬坡段;0=关闭(A/B 基线臂)
    merge_progress = (_merge_progress_count(state, session, registry)
                      * registry.merge_progress_unit)
    # 追级 EV(ADR-0290 层2 查表项):小数等级 = level + xp 进度比
    # (单击经验不整级,按进度分数计值——整级制下单击恒 0 分被
    # 「非正分」拒,升级通道死,cap 恒 5 → 一切买入板面价值归零)
    _xp = state.xp_progress or (0, 1)
    _xp_cur = _xp[0]
    _xp_need = _xp[1] if len(_xp) > 1 and _xp[1] > 0 else 1
    level_frac = state.level + min(1.0, _xp_cur / max(1, _xp_need))
    level_ev = level_frac * registry.level_unit_value
    return {'rung': round(rung, 3), 'power': round(power, 3),
            'interest': round(float(interest), 3),
            'depth': round(depth, 3), 'level': round(level_ev, 3),
            'targets': round(targets, 3),
            'eng_frac': round(eng_frac, 3),
            'core_star': round(core_star, 3),
            'merge_progress': round(merge_progress, 3)}


def _deployable_depth(state: GameState) -> int:
    """可用深度=min(level, deployed+bench)(板面形态维,非单卡拆分)。

    持有件对 cap 的覆盖:bench 件是「可上场深度」的储备(经部署
    管线显影);骨架初版曾用 min(level, deployed)——囤 bench 的买
    与升级在 cap 未放开时恒 0 分被「非正分」拒,决策活性死(升级
    买经验通道全灭)。未标定。
    """
    return min(state.level,
               deployed_occupied(state.deployed or [])   # ADR-0392
               + bench_occupied(state.bench or []))


def _deploy_pipeline(state: GameState,
                     session: StrategySession) -> None:
    """轻量 apply 的部署管线:围栏序把 bench 可上件推到 cap(就地)。

    与生产 DeployBench/sim 部署块同一源(select_deployments);
    只服务评分(改 deployed/board 维),不产生动作。
    """
    from sr_od.application.currency_war.kernel import cw_deploy_logic as dl
    from sr_od.application.currency_war.kernel.cw_battle_calib import _board_counts_of
    for _ in range(3):
        deployed_cids = {d.char_id for d in (state.deployed or [])
                         if getattr(d, 'char_id', '')}
        from sr_od.application.currency_war.kernel.cw_battle_calib import (
    _board_factions_of,
)
        tc = getattr(session, 'target_comp', None)
        up_idx, _ = dl.select_deployments(
            [b for b in (state.bench or []) if b is not None],
            deployed_cids=deployed_cids,
            deployed_fac=_board_factions_of(state.deployed),
            board=dict(state.board or {}),
            cap=state.max_units(),
            target_factions=frozenset(getattr(tc, 'factions', None) or ()),
            target_cores=frozenset(getattr(tc, 'core_chars', None) or ()),
        )
        if not up_idx:
            return
        # ADR-0316:up_idx 是紧缩占用序 → 回映射槽位下标后置 None
        _occ = [i for i, b in enumerate(state.bench or [])
                if b is not None]
        for i in sorted(up_idx, reverse=True):
            if i < len(_occ):
                bc = state.bench[_occ[i]]
                if bc is not None:
                    deployed_place(state.deployed, bc)   # ADR-0392 槽位落位
                    state.bench[_occ[i]] = None
        state.board = _board_counts_of(state.deployed)


def apply_for_score(cand: Candidate, state: GameState,
                    session: StrategySession,
                    ) -> GameState | None:
    """轻量 apply:候选→state 副本(只改评分需要的维)。

    买/升级/部署后接部署管线(买件的板面价值经「买入→上场」链显影);
    卖/刷新为原子 apply;None=该候选不查表(refresh EV 恒走常量)。
    """
    s = simulate(state, cand.action)
    if cand.tag == 'refresh':
        return None
    if cand.tag in _PIPELINE_TAGS:
        _deploy_pipeline(s, session)
    return s


#: 经部署管线显影板面价值的标签(买/升级/部署);卖=原子 apply
#: (ADR-0300:pair/copy 买件同走管线——bench 折减权重下纯囤件
#: 显影不足,买入→上场链让凑对/副本的板面形态价值可评)
_PIPELINE_TAGS = frozenset({
    'line_carry', 'line_opportunistic', 'bridge_core',
    'bond_fallback', 'carry_gate', 'levelup', 'deploy',
    'pair', 'copy',
})


def _shop_has_engine_card(state: GameState) -> bool:
    """店内是否有引擎件(过渡体系阵营/希儿;ADR-0301 找件判据)。

    迁移审计 w47(git 历史) 统一化:阵营/引擎名改读 ``cw_system_cards`` 派生 helper
    (``system_judge_factions``/``engine_char_names``,与诊断口径同源
    靠 import 不靠手抄——第五张体系卡加入自动传导)。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS as _CH
    from sr_od.application.currency_war.kernel.cw_system_cards import (
        engine_char_names,
        system_judge_factions,
    )
    _eng_facs = system_judge_factions()
    _eng_names = engine_char_names()
    for c in (state.shop or []):
        if not c.name:
            continue
        if c.name in _eng_names:
            return True
        ch = _CH.get(c.name)
        if ch is not None and (_eng_facs & (set(ch.factions or ())
                                            | set(ch.flows or ()))):
            return True
    return False


def vd_target_core(state: GameState,
                   session: StrategySession) -> str:
    """V_D 的目标件(单一目标,与 P5 概率表的「找谁」一致):

    意向锁定线的具名核心(``intention_core``,撤销计数③同源)——
    [3]「看自己核心在几级刷新概率大」的 D 找件对象就是核心;
    [31] 硬约束:非目标件不为凑羁绊 D(填充件只搭自然刷新便车)。
    未锁线/核心不可解析 → ''(D 通道关闭——V_D 需要具名目标,
    兜底局无概率表语境)。
    """
    from sr_od.application.currency_war.kernel.cw_intention import (
        IntentionState,
        intention_core,
    )
    ist = getattr(session, 'v3_intention', None)
    if not isinstance(ist, IntentionState) or ist.phase != 'locked' \
            or not ist.locked_comp:
        return ''
    from sr_od.application.currency_war.kernel.cw_comps import get_comp
    comp = get_comp(ist.locked_comp)
    if comp is None:
        return ''
    return intention_core(comp)


def p1_battle_loss_est(state: GameState, registry: DecisionV2Registry,
                       rung: int | None = None) -> float:
    """P1 收益侧单场战斗期望掉血=**条件败局伤害**(ADR-0425,math_proofs
    P15 检验点②;替换 V_D 收益式骨架值 expected_battle_loss=10 的
    「未标定」位)。

        loss(r) = max(0, vd_p1_loss_intercept + vd_p1_loss_slope_rung × r)

    出处=遥测拟合(`w324_coarse_battle/` 战斗粗模型冻结语料,battle 节点败局伤害线性
    拟合,battle n=278/73 局聚类稳健;registry 字段注释带产物指针)。
    **语义必须是条件伤害**:V_D 收益式的该因子与 Δwin_rate 相乘(额外
    胜场避免的掉血),故取「打了但输了」的条件期望;误用全样本(胜+
    败)无条件均值拟合则胜率已进均值、再乘 Δwin_rate = 双计(P15 的
    口径命题)。rung 缺省=state 当前成型档(_engines_formed,0-2),
    成型跳变账消费时显式传**成型后**档(避免的掉血发生在完成之后);
    域钳制 0-3(拟合的 rung 域)。
    """
    if rung is None:
        rung = _engines_formed(state, registry)
    r = min(3, max(0, int(rung)))
    return max(0.0, registry.vd_p1_loss_intercept
               + registry.vd_p1_loss_slope_rung * r)


def engine_jump_gold(eng_from: int, state: GameState,
                     registry: DecisionV2Registry,
                     session: StrategySession | None = None) -> float:
    """单级引擎跳变(e→e+1)的金值(`w131_a2n_arm/`/ADR-0352,买侧 V 的量纲基准)。

    与 vd_refresh_score 的收益侧**同式同源**(ADR-0349 金口径):

        jump(e) = Δrung_value(e→e+1) × R(跨位面剩余节点)
                  + Δh3_win_rate(e→e+1) × p1_battle_loss_est(成型后档)
                    × hp_to_gold × battles_left_plane(state 推导)

    战斗数与掉血两因子的骨架值治理(ADR-0425,math_proofs P15):战斗
    数从 plane_node_table 槽序表逐轮推导(P12 的 P2 手法同法;表缺退
    registry.battles_left_est,故 session=None 时行为=骨架缺省),
    掉血=条件败局伤害遥测拟合。诊断背景(`w131_a2n_arm/`):收益侧原骨架视界
    battles_left_est=5 与 interest_rule 的 C_interest 视界 R(≈20-23)
    错档一整个量级是买侧 EV 门恒拒的主因——R 项自 ADR-0352 起按 C 的
    同一视界折金,战斗项本批跟上;e≥2(封顶档)无跳变,返回 0。
    """
    if eng_from < 0 or eng_from + 1 > 2:
        return 0.0
    from sr_od.application.currency_war.decision_v2.ev import (
        battles_left_plane,
        cross_plane_remaining_nodes,
    )
    r = cross_plane_remaining_nodes(state)
    drung = (registry.rung_value.get(eng_from + 1, 0.0)
             - registry.rung_value.get(eng_from, 0.0))
    dwin = (registry.h3_win_rate.get(eng_from + 1, 0.0)
            - registry.h3_win_rate.get(eng_from, 0.0))
    return (drung * r + dwin * p1_battle_loss_est(state, registry,
                                                  rung=eng_from + 1)
            * registry.hp_to_gold
            * battles_left_plane(state, session, registry))


def formation_gold_account(base: GameState, after: GameState,
                           registry: DecisionV2Registry,
                           session: StrategySession | None = None) -> float:
    """买候选对阵容完成度的贡献,**按组合跳变计值**(`w131_a2n_arm/`/ADR-0352)。

    与 ADR-0349 D 侧「核心 2★ 完成按整跳变计值」同思路——买件的
    完成度贡献不是单件散分(层3 的 targets/eng_frac 族,O(1-3) 的
    未标定分单位),而是它推进的组合跳变金值:

    - 候选 apply 后**跨越整数引擎档**(deploy 管线显影):每跨一级
      计该级全额跳变金(engine_jump_gold);
    - 未跨档:**小数进度增量 × 下一级跳变金**(组合计值:一件进度
      件的价值=它在通往跳变的路上占的份额;全部进度件凑齐时份额
      之和=全额跳变,与「余量清零、值转进整数档」的 rung/eng_frac
      互补语义一致,不双计)。

    session 透传 engine_jump_gold(战斗数槽序表推导,ADR-0425;None=
    骨架缺省兜底)。

    消费点:score_candidate 写入 bd['form_gold'],arbiter.interest_rule
    的买侧 V 取 max(层3 分剥离息分量, 本账)(单一 EV 账内取大者,
    不与层3 序分叠加——层3 分继续辖候选排序/正分门)。
    """
    e0 = _engines_formed(base, registry)
    e1 = _engines_formed(after, registry)
    gold = 0.0
    for e in range(e0, min(e1, 2)):
        gold += engine_jump_gold(e, base, registry, session)
    if e1 == e0 and e1 < 2:
        d_rem = (_engine_frac_remainder(after, registry)
                 - _engine_frac_remainder(base, registry))
        if d_rem > 0:
            gold += d_rem * engine_jump_gold(e0, base, registry, session)
    return gold


def _vd_p1_pair(state: GameState, session: StrategySession,
                registry: DecisionV2Registry) -> float | None:
    """P1 体系对缺件找牌账(`w170_p1_vd/`/ADR-0369,候选 b;P2 分支不辖)。

    授权语义(每次放行答得出「找什么」=具名缺件,[31] 刷新金只用于找
    目标件——锁定帧体系对成员即二级目标件,ADR-0367):

    - **窗**:``transition_pair``/``p1_pair`` 非空(锁定帧副方向/配方锁)
      ∧ 缺件 ≥1(对成员集有未持有者)∧ **金 ≥ interest_floor + 刷价 +
      缺件买价**([3]「刷新后还能买之后保证 50 金」的单次逐字口径;
      [17] 守息边界由该前提表达,不设常量金门之外的第二道门);
    - **收益**:e_cur<2 时=下一档引擎跳变金值(engine_jump_gold 同式同源,
      [13] 过渡成型≈过 P1 的完成度账);e_cur≥2(已成型)→ 无对象;
    - **成本**:批口径 E₁×刷价(E₁=当前等级刷出 1 张该缺件的期望刷新数,
      k=1)——E 的概率表即 [3]「到概率等级才 D」的载体:错等级(如 1费
      @lv6)E 膨胀 → 账自然负 → 拒(「没到就少刷新」),溢余段也不为
      低概率搜刮放行(刷是找目标件,不是为刷而刷);
    - 缺件取账最大者(多缺件时找「最容易到手且账最优」的一件)。
    """
    if state.plane != 1 or not registry.vd_p1_pair_enabled:
        return None
    from sr_od.application.currency_war.kernel.cw_intention import (
        IntentionState,
        _pair_members,
    )
    ist = getattr(session, 'v3_intention', None)
    if not isinstance(ist, IntentionState):
        return None
    pair = (tuple(getattr(ist, 'transition_pair', ()) or ())
            or tuple(getattr(ist, 'p1_pair', ()) or ()))
    if not pair:
        return None
    owned = ({getattr(d, 'char_id', '') for d in state.deployed or ()}
             | {getattr(b, 'char_id', '')
                for b in (state.bench or []) if b is not None})
    missing = _pair_members(pair) - owned
    if not missing:
        return None
    e_cur = _engines_formed(state, registry)
    if e_cur >= 2:
        return None    # 已成型([13] 停手线)→ 找件对象消失
    benefit = engine_jump_gold(e_cur, state, registry, session)
    if benefit <= 0:
        return None
    import math

    from sr_od.application.currency_war.data.cw_chars import CHARACTERS as _CH
    from sr_od.application.currency_war.data.cw_shop_odds import (
        DISTINCT_CARDS_PER_COST,
        POOL_COPIES_PER_CARD,
        expected_refreshes,
        refresh_prob,
    )
    refresh_cost = state.shop_refresh_cost or 2
    best: float | None = None
    for name in missing:
        ch = _CH.get(name)
        if ch is None or not ch.cost:
            continue
        p = refresh_prob(state.level, ch.cost)
        if p <= 0:
            continue    # 该等级刷不到此费 → 无对象
        e1 = expected_refreshes(
            p, DISTINCT_CARDS_PER_COST.get(ch.cost, 13),
            POOL_COPIES_PER_CARD.get(ch.cost, 9), 0, 1, 0)
        if math.isinf(e1) or e1 <= 0:
            continue
        # [3] 单次预算前提:一次刷 + 买入后仍 ≥ 满息地板
        if (state.gold or 0) < registry.interest_floor() + refresh_cost \
                + ch.cost:
            continue
        val = benefit - e1 * refresh_cost
        if best is None or val > best:
            best = val
    return best


def vd_refresh_score(state: GameState, session: StrategySession,
                     registry: DecisionV2Registry) -> float | None:
    """V_D 批口径评分(`w126_b_arm/`/ADR-0349,经济循环总模型步③;P5 主定理)。

    **金口径总账**(迁移审计 w113(git 历史) §3.2(c)⟲R2 / P5 检验点①):

        V_D = 收益 − 成本
        收益 = 2★核心完成的成型跳变金值(F15 战力折算,registry 单一源):
               Δrung_value(e1→e2) × R(跨位面剩余节点)
               + Δh3_win_rate × 条件败局伤害(p1_battle_loss_est 遥测拟合)
                 × hp_to_gold × 剩余战斗节点(battles_left_plane 槽序表推导)
        成本 = expected_refreshes_for_card(level, cost, star=2, owned=j)
               × 刷价 —— **批口径**(找到 k 张的总期望刷金;
               ``cw_shop_odds`` 现成,禁单次边际口径——P5 已证对
               k≥3 目标系统性低估 D 通道)

    语义要点:
    - 收益按「核心 2★ 完成」计值(成型三件套第三件收口,整跳变的
      兑现绑定件);j 张已持时成本侧自动放大(E 随剩余张数增长),
      远未齐时 V_D 自然为负(攒自然刷新,不硬 D)——P5 边界语义;
    - **目标等级窗二分**([3]/迁移审计 w113(git 历史) §3.3 冲突消解):level_plan 目标说
      ``level_up``(窗外)→ 返回 None(D 让位给升,「没到就少刷新、
      多买经验」);``roll``/``stable``(窗内/峰值停留)→ V_D 生效
      (判据=``_resolve_level_goal`` 单一源,comp 自带 level_plan 优先);
      **P2 修订(`w154_p2d/`/ADR-0361)**:窗二分改消费 DP ``refresh_budget``
      授权(升级与 D 并行;DP 异常保守回退 level_plan 门);
    - **P2 段成本/收益口径**(`w154_p2d/`/ADR-0361,P11/P12):成本=机会成本
      C_dec(Δinterest×min(R, recovery_rounds_p2)+ρ·s,替换批口径面值;
      [17] 溢余即花)+ 预算硬界 s≤g−boss_floor;release 门辖帧息损项计 0
      (单一源=posture_release.spend_gate_active,同 score_state 息 EV 项);收益=存活语境参数
      (loss_p2/battles_left_p2 state 推导)。P1 收益侧同法治理
      (ADR-0425:战斗数槽序表推导+掉血遥测拟合,P15);`w170_p1_vd/`/
      ADR-0369 为 P1 增 pair 缺件找牌通道(vd_p1_pair_enabled 辖,见 _vd_p1_pair);
    - 金 50/51 边界的守息纪律不由本函数辖——由 arbiter.interest_rule
      的 C_interest 表达(P5⑤ 已证=定理退化输出,G2:不设常量金门);
    - 峰值以上停留(P5 边界 b):E(L) 已是当前等级真值,升级收益侧的
      对照账在 ev.levelup_refresh_saving(ΔE≤0 时自然为 0)。
    """
    import math

    core = vd_target_core(state, session)
    if not core:
        # `w170_p1_vd/`/ADR-0369:core 无对象(未锁 comp/配方锁局 p1_pair 帧)时
        # pair 缺件通道仍可评估(配方锁局的 p1_pair 帧本就无 locked_comp;
        # P2/未锁无对帧由 _vd_p1_pair 自身辖域回 None)
        return _vd_p1_pair(state, session, registry)
    # 概率窗二分([3]/迁移审计 w113(git 历史) §3.3;`w154_p2d/`/ADR-0361 P2 修订):
    # - P1 core 通道:goal 说 level_up(窗外)→ core 让位(「没到就少刷新、
    #   多买经验」);`w170_p1_vd/`/ADR-0369 起 level_plan 窗**只辖 core 通道**,
    #   pair 缺件通道(_vd_p1_pair)自带独立窗(缺件∧[3] 单次预算前提);
    # - P2(plane≥2 且 vd_p2_enabled):窗二分消费刷新预算——升级与 D 是
    #   并行授权(储备线已把 level_cost 算进 R*),level_plan 互斥把 D 预算
    #   整个吞掉 = 评分层让一拍变让整个位面(`w152_p2d/` 断点②:13/14 帧打空)。
    #   预算收权批(ADR-0465)(`w623_batch3_pre-mortem/` D2):判据显式改**预算函数口径**——
    #   refresh_ev_budget>0 → 窗开;=0(储备段/应急停手=合法 0 帧)→ 让位。
    from sr_od.application.currency_war.kernel.cw_economy import (
        _resolve_level_goal,
    )
    goal = _resolve_level_goal(
        state, getattr(session, 'target_comp', None))
    if state.plane >= 2 and registry.vd_p2_enabled:
        from sr_od.application.currency_war.kernel.cw_economy import (
            refresh_ev_budget,
        )
        if refresh_ev_budget(state, session, registry) <= 0:
            return None
    elif goal is not None and goal.action == 'level_up':
        # `w170_p1_vd/`/ADR-0369:level_plan 窗只辖 core 通道(core 让位给升,
        # 「没到就少刷新、多买经验」);pair 缺件通道走自己的窗(缺件∧
        # [3] 单次预算前提,见 _vd_p1_pair)——P2 分支(上方)不受此辖
        return _vd_p1_pair(state, session, registry)
    # 核心已完成 2★(任一份 star≥2)→ 找件目标消失
    copies = [d for d in list(state.deployed or [])
              + [b for b in (state.bench or []) if b is not None]
              if getattr(d, 'char_id', '') == core]
    if not copies or max(getattr(d, 'star', 1) or 1 for d in copies) >= 2:
        # core 副本 0(从未入手)/已 2★ → core 找件对象消失;pair 缺件
        # 通道仍可评估(`w170_p1_vd/`/ADR-0369:never-2 局的主形态=core copies0)
        return _vd_p1_pair(state, session, registry)
    j = len(copies)   # 全 1★ 的基础副本数(2★ 已在上面短路)
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS as _CH
    ch = _CH.get(core)
    if ch is None or not ch.cost:
        return None
    from sr_od.application.currency_war.data.cw_shop_odds import (
        expected_refreshes_for_card,
    )
    e = expected_refreshes_for_card(
        state.level, ch.cost, target_star=2, owned=j)
    if math.isinf(e) or e <= 0:
        return None    # 该等级刷不到此费(p=0)→ D 无对象
    # 收益侧:F15 成型跳变金值(registry 常量单一源,零新魔数)
    from sr_od.application.currency_war.decision_v2.ev import (
        cross_plane_remaining_nodes,
    )
    r = cross_plane_remaining_nodes(state)
    drung = (registry.rung_value.get(2, 0.0)
             - registry.rung_value.get(1, 0.0))
    dwin = (registry.h3_win_rate.get(2, 0.0)
            - registry.h3_win_rate.get(1, 0.0))
    spend = e * (state.shop_refresh_cost or 2)
    if state.plane >= 2 and registry.vd_p2_enabled:
        # `w154_p2d/`/ADR-0361 P2 段口径(P11 成本侧 + P12 收益侧);P1 收益侧
        # 骨架值治理见 ADR-0425:
        #   benefit^P2 = Δrung×R + Δh3_win × loss_p2 × hp_to_gold
        #                × battles_left_plane(state 推导,非缺省 5)
        #   C_dec(g,s) = Δinterest × min(R, recovery_rounds_p2)
        #                + ρ × s        —— 替换批口径面值 spend(P11:
        #   溢余段金堆到死,面值成本高估 ≥20×;[17] 溢余即花)
        # 预算硬界必须在(P11 推论):C_dec→0 后 EV 不再是约束,约束移到
        # 预算层——批口径期望刷金 s ≤ g − boss_floor,防「C=0 无限刷」。
        from sr_od.application.currency_war.decision_v2.ev import (
            battles_left_plane,
        )
        benefit = (drung * r + dwin * registry.vd_p2_loss
                   * registry.hp_to_gold
                   * battles_left_plane(state, session, registry))
        if spend > state.gold - registry.boss_floor:
            return None
        # release 帧泄息义务激活(判据单一源=posture_release.spend_gate_active
        # 读 session.v3_release,与 score_state 息 EV 项同判据)时息损项计 0:
        # 溢余段预算=g−interest_floor 已裁定必花,D 的息账罚分与花钱义务
        # 对冲(罚分过重时 V_D 回负 → D 候选让位,泄息意图在 D 通道仍被
        # 息账对冲);只拆息损项,流动性成本 ρ·spend 是真实刷金代价保留。
        # 开关关(基线臂)时零漂移。
        _rel_gate = False
        if session is not None:
            from sr_od.application.currency_war.decision_v2.posture_release import (
                spend_gate_active,
            )
            _rel_gate = spend_gate_active(session, registry)
        d_int = 0.0
        if not _rel_gate:
            d_int = (min(state.gold // 10, registry.interest_cap)
                     - min(int(state.gold - spend) // 10,
                           registry.interest_cap))
        c_dec = (max(0, d_int) * min(r, registry.vd_p2_recovery_rounds)
                 + registry.vd_p2_liquidity_rho * spend)
        return benefit - c_dec
    from sr_od.application.currency_war.decision_v2.ev import (
        battles_left_plane,
    )
    benefit = (drung * r + dwin * p1_battle_loss_est(state, registry,
                                                     rung=2)
               * registry.hp_to_gold
               * battles_left_plane(state, session, registry))
    p1_core = benefit - spend
    # `w170_p1_vd/`/ADR-0369:roll/stable 窗内 core 与 pair 缺件两本找件总账取大
    # (同一 RefreshShop 动作的两种具名「找什么」,core 语义逐位保留)
    pair_v = _vd_p1_pair(state, session, registry)
    return p1_core if pair_v is None else max(p1_core, pair_v)


def _engines_formed(state: GameState,
                    registry: DecisionV2Registry) -> int:
    """整数引擎数(混合域权重口径;与 board_rung_x 同源)。"""
    from sr_od.application.currency_war.kernel.cw_battle_calib import _engines_count
    fac, _main, dep = _held_form_weights(state, registry)
    return _engines_count(fac, dep)


def _cand_is_engine_piece(cand: Candidate) -> bool:
    """候选是否为过渡体系引擎件(factions∪flows∩TRANSITION_TRAITS 或 希儿)。

    与 cw_sim._engines_count 的体系判定同源(四体系成员;引擎判定单源
    在 cw_deploy_logic.TRANSITION_TRAITS);希儿系=单卡判定——买入囤
    bench 是成型路径(部署后才成引擎,[13] 成型进度),与计数语义
    (deployed 在场才算引擎)互补不冲突。
    """
    return bool(_cand_system_bonds(cand))


def _off_lock_demotion(cand: Candidate, state: GameState,
                       session: StrategySession,
                       registry: DecisionV2Registry) -> str:
    """`w150_buy_lock/`/ADR-0359 买侧通道锁定目标约束的降级裁决。

    锁定帧(``cw_intention.locked_buy_scope`` 非 None)时,
    ``registry.off_lock_buy_tags`` 辖的买候选中「目标件 ∉ 锁定目标
    体系集」者降级——约束是**方向**不是绞索(`w147_evolve/` 基调:优先级/围栏
    式非禁换):

    - ``'demote'``:层3 评分减 off_lock_buy_penalty(降级非禁绝,
      板面差分显著为正仍可过;[31]④ 填充不变量——填充件可回收,
      通道保持可买,只让位目标件);
    - ``'final_fence'``:位面末轮 boss 窗的 line_opportunistic 非目标
      件直接拒(`w143_formation/` strict 型联判的末轮面;目标件+填充不辖);
    - ``''``:无锁定帧/目标件在域/非辖标签/应急态([18] hp 报警时
      战力优先方向次要)→ 不降级。

    A/B 通道:``registry.buy_lock_constraint_enabled`` False=回 `w145_recipe_lock/`
    后行为(恒 '')。
    """
    if not registry.buy_lock_constraint_enabled:
        return ''
    if cand.tag not in registry.off_lock_buy_tags:
        return ''
    if is_emergency(state, registry):
        return ''
    from sr_od.application.currency_war.kernel.cw_intention import (
        IntentionState,
        locked_buy_scope,
    )
    ist = getattr(session, 'v3_intention', None)
    if not isinstance(ist, IntentionState):
        return ''
    scope = locked_buy_scope(ist)
    if scope is None:
        return ''
    name = getattr(getattr(cand.action, 'card', None), 'name', '') or ''
    if not name or name in scope:
        return ''
    if cand.tag == 'line_opportunistic' \
            and registry.off_lock_final_fence_enabled:
        from sr_od.application.currency_war.decision_v2.discipline import (
            boss_window_active,
        )
        from sr_od.application.currency_war.kernel.cw_plane_table import (
            nodes_of_plane,
        )
        # ADR-0366:位面末轮门按本位面真值(P2=7→r7 即末轮;旧按 9 计
        # P2 的 final_fence 永不触发,与 ADR-0359 的「位面末」语义不符)
        if state.round_num >= nodes_of_plane(session) \
                and boss_window_active(state, session, registry):
            return 'final_fence'
    return 'demote'


def _cand_system_bonds(cand: Candidate) -> frozenset[str]:
    """候选卡所属的过渡体系键集(TRANSITION_TRAITS 键;希儿系单列)。

    ``_cand_is_engine_piece`` 的键来源:TRANSITION_TRAITS (bond, tier)
    解包(与 cw_sim._engines_count 体系判定同源);希儿系以 '希儿系'
    哨兵键返回(单卡二元判定,不进三羁绊的档位计数口径)。
    返回空集 = 非配方件。
    """
    a = cand.action
    if not isinstance(a, BuyCard):
        return frozenset()
    name = getattr(a.card, 'name', '') or ''
    if name == '希儿':
        return frozenset({'希儿系'})
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS as _CH
    ch = _CH.get(name)
    if ch is None:
        return frozenset()
    from sr_od.application.currency_war.kernel.cw_deploy_logic import (
        TRANSITION_TRAITS as _TRANSITION_TRAITS,
    )
    eng_bonds = {b for b, _t in _TRANSITION_TRAITS}
    return frozenset((set(ch.factions or ()) | set(ch.flows or ()))
                     & eng_bonds)


def score_candidate(cand: Candidate, state: GameState,
                    session: StrategySession,
                    registry: DecisionV2Registry,
                    ) -> tuple[float, dict]:
    """单候选评分:apply 后板面查表 − 基线板面查表(相对值)。

    禁止单卡边际拆分——差值全部来自板面形态维(档位/战力/息)与
    即时金流(卖出回金);refresh 候选走 V_D 批口径金账
    (vd_refresh_score,`w126_b_arm/`/ADR-0349)。
    """
    base = score_state(state, registry, session)
    if cand.tag == 'o1_bench_fill':
        # `w611_econ_cycle/` O1 备战空位填补(ADR-0463):板面差分对该通道构造性零维
        # (bench 囤件不进形态维)→ 评 0 中性,放行语义由义务证明背书
        # (溢余段买 1★ 退全款+息帽截断:已实现成本 0、收益 ≥0,弱占优
        # 参数无关,w611_econ_cycle/DESIGN.md §1.3)——arbiter 非正分门
        # 凭义务豁免越过(copy 零维豁免同判例),金可行性(g_after≥R*)
        # 由 gold_floor 的 o1 地板加深处辖。int_emb=0(无息分量可剥离)。
        return 0.0, {'base': base, 'after': None, 'o1_bench_fill': True,
                     'int_emb': 0.0}
    if cand.tag == 'refresh':
        # `w126_b_arm/`/ADR-0349 V_D 批口径(P5 检验点①):refresh 附庸闸
        # (refresh_max_round 轮界/refresh_min_gold 金门/refresh_ev 常量
        # /饥饿折扣/危机 max 分支/成型找件通道)整体退场——D 候选
        # 评分=vd_refresh_score 的金口径总账(收益=核心 2★ 完成的
        # 成型跳变金值,成本=expected_refreshes×刷价批口径)。
        # 迁移审计 w119(git 历史)/ADR-0347:bd['int_emb']=0(刷新分内无息分量——EV 授权
        # 剥离用,arbiter.interest_rule 消费;金 50/51 拒 D 是 C_interest
        # 在 50 档边界的自然输出,P5⑤,不设常量金门(G2))。
        # ADR-0348 扑满低危战斗(口述定谒 2026-08-26)×迁移审计 w120(git 历史) P8 上限
        # (迁移审计 w122(git 历史) F-01):过热局 reward 节点按「奖励型战斗」处理——轻投入
        # 凑羁绊刷伤害拿奖励,**禁深花保血**。凑羁绊 D 不是 V_D 的
        # 核心找件语境(找件=核心概率表,凑羁绊=店内羁绊件),走
        # piggy_refresh_ev 独立小额账;受 P8 上限辖:s≤0.277R(采前
        # R=6-9 → s≤2金)→ 豁免限 piggy_refresh_round_cap 次/节点,
        # 超出按无证拒(V_D 不足以放行时回负分)。
        from sr_od.application.currency_war.decision_v2.ev import (
            reward_node_is_battle,
        )
        vd = vd_refresh_score(state, session, registry)
        _piggy = (reward_node_is_battle(state)
                  and getattr(session, 'v2_round_refreshes', 0)
                  < registry.piggy_refresh_round_cap)
        if _piggy:
            val = registry.piggy_refresh_ev \
                - (cand.action.cost or 0)
            if vd is not None:
                val = max(val, vd)
        elif vd is not None:
            val = vd
        else:
            # 无目标语境(未锁线/核心已齐/窗外/该等级刷不到):
            # D 让位——刷新金只用于找目标件/保血急救([31] 硬约束)
            val = -(cand.action.cost or 2)
        return val, {'base': base, 'after': None, 'refresh_ev': val,
                     'int_emb': 0.0}
    after_state = apply_for_score(cand, state, session)
    if after_state is None:
        return 0.0, {'base': base, 'after': None, 'int_emb': 0.0}
    after = score_state(after_state, registry, session)
    val = sum(after.values()) - sum(base.values())
    # `w131_a2n_arm/`/ADR-0352 买侧组合跳变金账:买候选对完成度的贡献按组合跳变
    # 计值(与 V_D 收益侧同式同源,R 视界),供 interest_rule 的买侧 V
    # 消费(max 取大,不进层3 序分——序分继续辖排序/正分门)。
    form_gold = 0.0
    if isinstance(cand.action, BuyCard):
        form_gold = formation_gold_account(state, after_state, registry,
                                           session)
    # 迁移审计 w119(git 历史)/ADR-0347:bd['int_emb'] = 本候选分数内**实际嵌入的息分量**
    # (EV 授权的 V 剥离单一源——arbiter.interest_rule 消费:
    # V = val − int_emb)。默认=息差;ADR-0332 平滑生效时改写为
    # 真实档损(平滑后的净嵌入),两处保持同值。
    int_emb = after.get('interest', 0.0) - base.get('interest', 0.0)
    _rel_gate = False
    if session is not None:
        from sr_od.application.currency_war.decision_v2.posture_release import (
            spend_gate_active,
        )
        _rel_gate = spend_gate_active(session, registry)
    if (state.plane == 1 and state.round_num >= 5
            and not is_emergency(state, registry)
            and not _rel_gate
            and (state.gold or 0) >= registry.interest_floor()
            and (after_state.gold or 0) < registry.interest_floor()):
        # ADR-0332 息崖平滑(war 破息窗):买入跌破 50 满息平台时,评分
        # 原扣全平台消失(-25),而同一窗口纪律侧(boss_breaker r≥5 P1,
        # floor 10 / 保血弃息)授权破 50 花费——双重计罚让 gold 50-53
        # 带买入恒死(实机「金 42→71 攒息期零买」的评分侧机制)。此处把
        # 息损修正为**真实档位损失**(跨档数×interest_rounds,[17] 息律),
        # 50→49 只付 -5;emergency 保持 -25([18] 不为苟住破息,ADR-0302
        # 锁);经济态(<50 政策)与 war 窗非破平台带不受影响。
        # release 帧旁路(_rel_gate):泄息义务=花溢余段跌破平台的**意图
        # 本体**,息损罚则与义务直接对冲;义务预算的有界性由 arbiter 收尾
        # 块(authorize_release_refresh 逐笔扣账)自辖,评分侧不重复计罚。
        _gb = state.gold or 0
        _ga = after_state.gold or 0
        _orig_pen = (after.get('interest', 0.0) - base.get('interest', 0.0))
        _real_loss = -(_gb // 10 - _ga // 10) * registry.interest_rounds
        val += _real_loss - _orig_pen
        int_emb = float(_real_loss)
    if cand.tag in ('off_target', 'for_gold', 'free_bench'):
        # 弱件换金偏置(registry.off_target_sell_bias):持有域溢出
        # 件的卖分本为 0(被「非正分」拒),偏置让占位件可换金
        # 供刷新/买入(ADR-0291 遗留,ADR-0293 标定)。
        # S5(ADR-0327):均一 bias 改按键缩放——w=sell_score_weight
        # (期望损失归一化:净0 件 w=1、升星沉淀件 w→小);只改同通道
        # 内卖件**相对序**,不改「卖不卖」的正分门槛(纯占位件
        # val=bias×w>0 仍可卖;未知费级件 w=1 保底)。
        w = 1.0
        if isinstance(cand.action, SellBench):
            _bc = (state.bench[cand.action.bench_idx]
                   if 0 <= cand.action.bench_idx < len(state.bench or [])
                   else None)
            if _bc is not None:
                from sr_od.application.currency_war.data.cw_chars import (
                    CHARACTERS as _CH,
                )
                _c = _CH.get(getattr(_bc, 'char_id', '') or '')
                if _c is not None and _c.cost:
                    from sr_od.application.currency_war.decision_v2.discipline import (
                        sell_score_weight,
                    )
                    w = sell_score_weight(_c.cost, registry)
        val += registry.off_target_sell_bias * w
    if (cand.tag in registry.crisis_buy_tags
            and crisis_hoard_active(state, registry)):
        # ADR-0302 危机囤金修复(应急段):危机态(hp≤25 且金≥40,
        # 迁移审计批(可解释性遥测) F3 指纹)战力买候选板面差分恒 0.00 被仲裁器「非正分」
        # 拒 → 金囤 85+ 板濒死零动作。偏置只顶 0 分差分为正——
        # 金 52→49 的息崖(-25)不被翻越,危机花费止于满息平台
        # ([17]「>50 该买就买」+[18]「不为苟住破息」)。常量在
        # registry(crisis_buy_bias/crisis_buy_tags;ADR-0303 上移)。
        val += registry.crisis_buy_bias
    if (registry.forming_bias > 0
            and state.plane == 1 and state.round_num >= 5
            and not is_emergency(state, registry)
            and _engines_formed(state, registry) < 2
            and _cand_is_engine_piece(cand)
            and -registry.interest_rounds <= val
            <= registry.forming_bias_val_max):
        # ADR-0332 成型补充偏置(成型度权重;迁移审计 w64(git 历史) Ring3 同族评分活性修):
        # P1 破息窗 + 板面未成型(引擎<2,[13] 成型即停手的前提不满足=应
        # 继续买配方件)时,引擎件买入的「成型期权」显影——cap 饱和/冗余
        # 档位下买入不改评分维(base==after)被「非正分」拒(ADR-0301
        # 残余),而 [27] 每场质量战把中期投资在全节点持续变现。偏置只顶
        # val∈[-interest_rounds, +0.5](单档真实息损内;emergency 的 -25
        # 息崖([18])与深负分不被翻越),量级=引擎完成期权(win 跳升×剩余
        # 战斗),registry 注入可 A/B;成型后(引擎≥2)偏置关闭 → 停手攒息。
        val += registry.forming_bias
    # copy_press 评分路由已随 ADR-0427 增补节定谳清理(策略开关生命周期
    # 第 4 态;悬置实证与删除清单=该增补节):copy_press 候选不再有
    # 独立给分偏置,评分只由通用板面维决定——标签生成与通道守卫/
    # [11] 豁免臂/双 cap(实证收益承载)不动。
    # 定谳清理(策略开关生命周期第 4 态):goldrich_buy_bias(ADR-0305
    # 件3,三窗否决+ADR-0408 同构复证)、early_pace 五字段偏置(ADR-0408,
    # 三窗无一致正方向)、filler_star 期权分与方向门豁免(ADR-0402,
    # `w504_filler_star_adr0402/` 开臂 A/B wash)的评分消费块均已删除,删除清单与证据链见各
    # ADR 定谳/清理节。
    # `w150_buy_lock/`/ADR-0359 买侧通道锁定目标约束:末段施加(净降级——
    # forming_bias 等偏置先行计入,本约束最后收口,防
    # 偏置把非目标件重新顶回)。bd['off_lock'] 记降级依据(判读可读)。
    off_lock = _off_lock_demotion(cand, state, session, registry)
    if off_lock == 'final_fence':
        val = min(val, 0.0) - 1.0   # 末轮围栏:可靠非正分拒(仲裁层
        # 「非正分」收口,log 可见)
    elif off_lock:
        val -= registry.off_lock_buy_penalty
    out_bd = {'base': base, 'after': after, 'int_emb': int_emb,
              'form_gold': round(form_gold, 3)}
    if off_lock:
        out_bd['off_lock'] = off_lock
    return val, out_bd


def score_all(cands: list[Candidate], state: GameState,
              session: StrategySession,
              registry: DecisionV2Registry,
              ) -> list[tuple[Candidate, float, dict]]:
    """全候选评分(层3 入口;返回 (候选, 分, breakdown) 列表)。"""
    out: list[tuple[Candidate, float, dict]] = []
    for c in cands:
        v, bd = score_candidate(c, state, session, registry)
        out.append((c, round(v, 4), bd))
    return out


# ===== R5 数据平表 + EffectSpec 打分偏置通道(`w628_migration_b2/` 迁移迁移批 2(方向层接管)(方向层接管) 效果层归位)=====
# 蓝图 §4.2-R5:拍值打分钩子(box_card/star_tome/wish_trial,原 default_
# strategy 内联魔数)降为「名字→标定权重」数据平表;本表 = 唯一标定源,
# 钩子消费面读表取值(数值原样迁移,行为零漂移;战场族条目推迟挂账)。
@dataclass(frozen=True)
class PickBiasTable:
    """单帧单发采购拍值平表(R5;数值出处 = 退役前策略钩子内联值,git prior art)。"""
    # 星徽秘典四选一(decide_star_tome)
    tome_target_faction: float = 40.0     # 终局线需要的阵营星徽
    tome_board_hit: float = 8.0           # 板上已有该阵营(每件;边际高)
    tome_framework_faction: float = 15.0  # 过渡配方框架阵营(双轨期)
    # 祈愿试炼选卡(decide_wish_trial)
    wish_gold: float = 25.0               # 金币类(直接经济,阵容无关)
    wish_faction: float = 20.0            # target/框架阵营相关词
    wish_operation: float = 10.0          # 刷新/购买操作向(与 DP 攒息协同)
    # 武装箱四选一(decide_box_card)
    box_key_equip: float = 100.0          # target.key_equips 命中(成型加速)
    box_key_material: float = 30.0        # key_equip 合成材料(两跳)
    # 材料通用性 _material_value 表维持其模块单一源(生命周期/配方数)不变


PICK_BIAS = PickBiasTable()


def effect_pick_bias(session: StrategySession, option_name: str) -> float:
    """EffectSpec → 拍值偏置通道(迁移迁移批 2(方向层接管)(方向层接管) 消费接入;R5 消费面)。

    - 输入 = session.effect_inventory 在场效果条目;按条目 spec 的
      ``notes`` 声明偏置选项名(平表外挂,数值随实采/sim 标定批填,
      **缺省 0 = 无偏置**,不猜值——strategy-work「决策规则数学先行」门);
    - 战场族(BATTLEFIELD category)推迟:战场改写类偏置语义待执行预判批
      (`w610_gold_digger_spec/` P2-2)定义,本通道暂只认 ECONOMY/STATE 族;
    - pending=True 条目不参与(二义未定谳,消费端走保守支,cw_effect_
      inventory 契约)。
    """
    del option_name   # 通道预留:选项名级偏置随标定批启用(当前 spec 级=0)
    inv = getattr(session, 'effect_inventory', None)
    if inv is None:
        return 0.0
    bias = 0.0
    for entry in getattr(inv, 'entries', ()):
        spec = getattr(entry, 'spec', None)
        if spec is None or getattr(spec, 'pending', False):
            continue
        if getattr(spec, 'category', None) is not None:
            if getattr(spec.category, 'value', '') not in ('economy', 'state'):
                continue   # 战场族推迟(设计挂账,不猜语义)
    return bias
