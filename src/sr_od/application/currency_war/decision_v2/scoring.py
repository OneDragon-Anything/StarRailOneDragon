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

from sr_od.application.currency_war.cw_line_defs import (
    RECIPE_BASE,
    recipe_tier,
)
from sr_od.application.currency_war.cw_state import (
    GameState,
    bench_occupied,
    simulate,
)
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.candidates import Candidate
from sr_od.application.currency_war.decision_v2.filters import (
    crisis_hoard_active,
)
from sr_od.application.currency_war.decision_v2.registry import (
    DecisionV2Registry,
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
    from sr_od.application.currency_war.cw_sim import _engines_count
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
    from sr_od.application.currency_war.cw_chars import CHARACTERS as _CH
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
    from sr_od.application.currency_war.cw_sim import (
        _TRANSITION_TRAITS,
        _engines_count,
    )
    fac, _main, dep = _held_form_weights(state, registry)
    engines = _engines_count(fac, dep)
    progress = sum(min(fac.get(b, 0.0) / tier, 1.0)
                   for b, tier in _TRANSITION_TRAITS)
    return max(0.0, progress - engines)


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
    # 计罚,合法买入被评负分全弃(smoke 实证);单一源对齐
    interest = (min(registry.interest_cap, (state.gold or 0) // 10)
                * registry.interest_rounds
                if (state.gold or 0) >= registry.interest_floor else 0.0)
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
            'eng_frac': round(eng_frac, 3)}


def _deployable_depth(state: GameState) -> int:
    """可用深度=min(level, deployed+bench)(板面形态维,非单卡拆分)。

    持有件对 cap 的覆盖:bench 件是「可上场深度」的储备(经部署
    管线显影);骨架初版曾用 min(level, deployed)——囤 bench 的买
    与升级在 cap 未放开时恒 0 分被「非正分」拒,决策活性死(升级
    买经验通道全灭)。未标定。
    """
    return min(state.level,
               len(state.deployed or []) + bench_occupied(state.bench or []))


def _deploy_pipeline(state: GameState,
                     session: StrategySession) -> None:
    """轻量 apply 的部署管线:围栏序把 bench 可上件推到 cap(就地)。

    与生产 DeployBench/sim 部署块同一源(select_deployments);
    只服务评分(改 deployed/board 维),不产生动作。
    """
    from sr_od.application.currency_war import cw_deploy_logic as dl
    from sr_od.application.currency_war.cw_sim import _board_counts_of
    for _ in range(3):
        deployed_cids = {d.char_id for d in (state.deployed or [])
                         if getattr(d, 'char_id', '')}
        from sr_od.application.currency_war.cw_sim import (
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
                    state.deployed.append(bc)
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

    W47 统一化:阵营/引擎名改读 ``cw_system_cards`` 派生 helper
    (``system_judge_factions``/``engine_char_names``,与诊断口径同源
    靠 import 不靠手抄——第五张体系卡加入自动传导)。
    """
    from sr_od.application.currency_war.cw_chars import CHARACTERS as _CH
    from sr_od.application.currency_war.cw_system_cards import (
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


def _engines_formed(state: GameState,
                    registry: DecisionV2Registry) -> int:
    """整数引擎数(混合域权重口径;与 board_rung_x 同源)。"""
    from sr_od.application.currency_war.cw_sim import _engines_count
    fac, _main, dep = _held_form_weights(state, registry)
    return _engines_count(fac, dep)


def score_candidate(cand: Candidate, state: GameState,
                    session: StrategySession,
                    registry: DecisionV2Registry,
                    ) -> tuple[float, dict]:
    """单候选评分:apply 后板面查表 − 基线板面查表(相对值)。

    禁止单卡边际拆分——差值全部来自板面形态维(档位/战力/息)与
    即时金流(卖出回金/刷新费经息档与 refresh_ev 常量显影)。
    """
    base = score_state(state, registry, session)
    if cand.tag == 'refresh':
        # 刷新的板面形态不可预知(新店随机)→ 查表外常量 EV
        # (未标定=0:骨架版不主动刷新;标定 gate 后接 P(hit) 期望)。
        # 轮界门(registry.refresh_max_round):早期方向刷新(v1 r258
        # 同语义),中后期恒刷会抽干金流挤死升级通道(标定批诊断);
        # 金保底门(refresh_min_gold):防刷后 re-decide 链把金抽干
        # 至 <10,中期够不到满息平台锁死 [12] 息引擎(标定批诊断)
        if (state.round_num > registry.refresh_max_round
                or (state.gold or 0) < registry.refresh_min_gold):
            val = -cand.action.cost or -1.0
        else:
            ev = registry.refresh_ev
            # ADR-0297 评分侧联动(方案 b):金低于追级饥饿阈值时
            # refresh_ev 打折(1.0=关闭)——排序自然让位给追级/买入,
            # 与约束侧(层4 refresh_budget)互斥使用的通道
            if (registry.refresh_starve_discount < 1.0
                    and (state.gold or 0) < registry.refresh_starve_gold):
                ev *= registry.refresh_starve_discount
            val = ev - (cand.action.cost or 0)
        # ADR-0302 危机囤金修复(应急段):危机态(hp≤25 且金≥40)
        # 的刷新=定向搜战力件(常规轮界门辖不到 r7+ 危机窗;批㉝
        # F3 实证:seed 75 危机尾段店无战力件,囤金无变现通道)。
        # 止步线=囤金线 40(<40 crisis 态解除→回常规门,r7+ 恒负分);
        # 买侧息崖仍在(52→49 的买不被翻越)——危机搜牌属 [18]
        # 「位面末最后一战 ALL IN」例外域
        if crisis_hoard_active(state, registry):
            val = max(val,
                      registry.refresh_ev - (cand.action.cost or 0))
        # ADR-0301 成型找件通道(域 b):未成型+店无引擎件时刷新=
        # 定向找件,独立轮界/金门(常规门辖不到 r7 找件窗);
        # 饥饿折扣同辖(防找件链在低金抽干金流)
        if (registry.form_refresh_ev > 0
                and state.round_num <= registry.form_refresh_max_round
                and (state.gold or 0) >= registry.form_refresh_min_gold
                and _engines_formed(state, registry)
                < registry.form_refresh_engines_target
                and not _shop_has_engine_card(state)):
            ev_f = registry.form_refresh_ev
            if (registry.refresh_starve_discount < 1.0
                    and (state.gold or 0) < registry.refresh_starve_gold):
                ev_f *= registry.refresh_starve_discount
            val = max(val, ev_f - (cand.action.cost or 0))
        return val, {'base': base, 'after': None, 'refresh_ev': val}
    after_state = apply_for_score(cand, state, session)
    if after_state is None:
        return 0.0, {'base': base, 'after': None}
    after = score_state(after_state, registry, session)
    val = sum(after.values()) - sum(base.values())
    if cand.tag in ('off_target', 'for_gold', 'free_bench'):
        # 弱件换金偏置(registry.off_target_sell_bias):持有域溢出
        # 件的卖分本为 0(被「非正分」拒),偏置让占位件可换金
        # 供刷新/买入(ADR-0291 遗留,ADR-0293 标定)
        val += registry.off_target_sell_bias
    if (cand.tag in registry.crisis_buy_tags
            and crisis_hoard_active(state, registry)):
        # ADR-0302 危机囤金修复(应急段):危机态(hp≤25 且金≥40,
        # 批㉝ F3 指纹)战力买候选板面差分恒 0.00 被仲裁器「非正分」
        # 拒 → 金囤 85+ 板濒死零动作。偏置只顶 0 分差分为正——
        # 金 52→49 的息崖(-25)不被翻越,危机花费止于满息平台
        # ([17]「>50 该买就买」+[18]「不为苟住破息」)。常量在
        # registry(crisis_buy_bias/crisis_buy_tags;ADR-0303 上移)。
        val += registry.crisis_buy_bias
    if (cand.tag in registry.goldrich_buy_tags
            and val == 0.0
            and (state.gold or 0) >= registry.goldrich_min_gold):
        # ADR-0305 件3:金充裕买偏置(常态域;crisis 偏置的邻域
        # 对偶)——金充裕段 0 分板面差分的成型/凑对/核心件顶成正
        # 分,金滞留换成型素材。同 crisis 语义只顶 0 分(val==0
        # 守卫:负息崖差分不翻越);0=关闭(bias 常量,registry)。
        val += registry.goldrich_buy_bias
    return val, {'base': base, 'after': after}


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
