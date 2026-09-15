"""货币战争战斗校准与板面聚合函数族(自 cw_sim.py 下沉;DESIGN §3.3-②/§4.3;
等价锚=同 seed 决策序列既有锁面)。

下沉闭包 = DESIGN §4.3「校准+聚合族」:回退层胜负面(node_win_p/
battle_delta/boss_delta/boss_settle_delta/node_delta)、结算成型度键
(_settle_rung/deployed_star_depth)、P2 参数化存活层(p2_* 族,注入
P2CombatCalib)、板面聚合族(_board_factions_of/_board_counts_of/
_engines_count/_transition_formed/_first_*_round/
_battles_before_engines/_deployable_depth/_roll_rotation)。

sim 重做删除面收口(sim-redesign design.md §2.4.1/§2.4.4):节点序列
采样 sample_node_sequence(U19:42 局零反例,序列用地面真值表)与
方向观测判据 _direction_established/_target_comp_label(判据本属
策略器;删时 src/测试仓已零消费方)随裁定删除——kernel 只留特征
函数;节点序列真值 = sim/cw_sim_plane_schedule.py。

下沉理由:decision_v2(scoring/candidates/handoff/phase)与 cw_evolution/
cw_line_switch 以函数消费本族,留 sim 桶成 decision→sim / kernel→sim
违规边。本模块(kernel 桶)零 sim 依赖:纯值来自 data/cw_battle_tables,
计数底座在 cw_state/cw_deploy_logic/cw_line_defs(kernel);
SimResult 等类型仅鸭子读取。

桩点契约:消费方函数内懒 import 本模块符号(属性动态解析),
monkeypatch 钉本模块符号(锁改判裁决=N7,禁 shim)。
"""
from __future__ import annotations

import random

from sr_od.application.currency_war.data.cw_battle_tables import (
    BOSS_BY_DIR_ROUND,
    BOSS_WIN_DELTA,
    EARLY_WIN_DELTA,
    ENCOUNTER_MULT,
    LOSS_BASE,
    LOSS_PER_ROUND,
    NODE_WIN_P_BY_TYPE,
    NODE_WIN_P_LADDER,
    P2_BATTLE_WIN_P,
    P2_LOSS_BAND,
    WIN_DELTAS,
    P2CombatCalib,
)
from sr_od.application.currency_war.data.cw_shop_odds import (
    REFRESH_PROB,
    ROTATION_CHANCE,
    rotation_probs,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    deployed_slots_of,
    level_of,
    round_num_of,
)


def deployed_star_depth(bs: GameState) -> int:
    """净星深 = 上场件 Σ(star−1)(全量口径,同 ADR-0399
    HandoffSnapshot star_sum−deployed_n;纯 state 可算、生产/sim/
    离线回放三面同式)。

    消费点:p2_form_key 星级分量(ADR-0401)与 **Δ池 boss 桶键**
    (ADR-0404,替代 Σboard——修 3合1 升星使 Σboard −2/次键落
    浅桶的方向冲突;净星深下 1★→2★ 合并键 +1 永不落浅桶,买 bench
    副本不扰动)。已知边界:2★→3★ 合并键 −1(3 副本 Σ(star−1)=3 →
    载体 2),仅当键恰为 3 的倍数时跨桶——高级合并当前语料零样本,
    语料攒厚后复核。
    """
    return sum(
        int(getattr(d, 'star', 1) or 1) - 1
        for d in deployed_slots_of(bs) if d is not None)


def _star_depth_from_rows(rows) -> int:
    """净星深(replay 行口径):decisions ``state.deployed`` 条目
    (dict 形态)Σ(star−1)——与 :func:`deployed_star_depth` 同式,
    池语料侧(_pool_from_replay;原 cw_delta_pool_gen 已随 sim 重做
    删除面退役)共用,防双源。"""
    return sum(int(x.get('star') or 1) - 1
               for x in (rows or []) if isinstance(x, dict))


def p2_form_key(bs: GameState, calib: P2CombatCalib) -> float:
    """form=板面质量键(ADR-0377:engines+level 折算;
    ADR-0401 扩展:+星级深度折算)。

    engines = ``_settle_rung`` 同源(deployed 口径四体系达成数,0-4);
    P2 实测:deployed 口径与掉血对应最干净、板深无区分度。
    star_depth = ``deployed_star_depth`` 单一源(core2 维/board_tier
    的星级分量因果通道,交接 sim 报告 §⑥/交接门报告挂账的 sim 建模缺口)。
    """
    star_depth = deployed_star_depth(bs)
    return (float(_settle_rung(bs)) + calib.form_level_weight * (
        level_of(bs) - calib.form_level_base)
        + calib.form_star_weight * star_depth)


def p2_win_p(bs: GameState, node: str, round_num: int,
             calib: P2CombatCalib) -> float:
    """参数化胜率:clip(p0 + β·form − γ·drift(round))。

    drift = max(0, round−1)(r1 无漂移;敌人强度逐轮增长的最小参数化)。
    """
    lo, hi = calib.win_p_clip
    form = p2_form_key(bs, calib)
    drift = max(0, round_num - 1)
    return min(hi, max(lo, calib.p0 + calib.beta * form
                       - calib.gamma * drift))


def p2_loss_band(node: str, round_num: int,
                 calib: P2CombatCalib) -> tuple[int, int]:
    """分段掉血带路由(battle 按 r1/r2-r3/r4+ 分段;encounter/boss 独立)。"""
    if node == 'battle':
        if round_num == 1:
            return calib.band_battle_r1
        if round_num <= 3:
            return calib.band_battle_early
        return calib.band_battle_late
    if node == 'encounter':
        return calib.band_encounter
    return calib.band_boss


def p2_combat_delta(bs: GameState, node: str, round_num: int,
                    rng: random.Random,
                    calib: P2CombatCalib) -> tuple[int, float]:
    """P2 战斗类节点参数化结算(胜→win_delta/负→分段带内均匀)。

    返回 (delta, win_p)——win_p 随账本披露(检查器带锚/敏感性判读消费)。
    """
    wp = p2_win_p(bs, node, round_num, calib)
    if rng.random() < wp:
        return calib.win_delta, wp
    lo, hi = p2_loss_band(node, round_num, calib)
    return -rng.randint(lo, hi), wp


def node_win_p(node_type: str, round_num: int = 0) -> float:
    """节点胜率单一取值口(ADR-0308;回退层胜负面)。

    (node, round) 实测组合优先(``NODE_WIN_P_LADDER``),缺组合退
    节点类型边际(``NODE_WIN_P_BY_TYPE``)。语料边界见常量注释:
    旧策略病局镜像、无成型度条件性——新策略语料攒够后重标。
    """
    if node_type in ('reward', 'supply'):
        return NODE_WIN_P_BY_TYPE[node_type]
    v = NODE_WIN_P_LADDER.get((node_type, round_num))
    if v is None:
        v = NODE_WIN_P_BY_TYPE.get(node_type, 0.0)
    return v


def battle_delta(round_num: int, dir_round: int,
                 rng: random.Random) -> int:
    """普通战斗 HP 变化(校准层回退;ADR-0308)。

    胜负面 = 实机实测阶梯 ``node_win_p('battle', round_num)``
    (n=192;旧方向二元门控「已立→胜」废弃——胜率从未按节点实测,
    语料实测方向已立后战斗胜率仍 ~0.29);胜 → ``WIN_DELTAS``,
    负 → 旧损益幅度层(LOSS_BASE/LOSS_PER_ROUND,25 局轨迹校准,
    保留)。``dir_round`` 保留签名兼容,不再参与胜负判定。
    """
    if round_num <= 2:
        return EARLY_WIN_DELTA
    if rng.random() < node_win_p('battle', round_num):
        return rng.choice(WIN_DELTAS)
    loss = LOSS_BASE + LOSS_PER_ROUND * (round_num - 3) \
        + rng.uniform(-3, 4)
    return int(-loss)


def boss_delta(dir_round: int, rng: random.Random,
               multiplier: float = 1.0) -> int:
    """P1 boss(r9)HP 变化(校准层;按方向建立早晚分档)。

    multiplier>1 用于遭遇轮(用户口述:遭遇三四可比 boss 难)。"""
    for cap, base, jitter in BOSS_BY_DIR_ROUND:
        if dir_round <= cap:
            return int(-(base * multiplier
                         + rng.uniform(0, jitter)))
    return int(-(36.0 * multiplier + rng.uniform(0, 10.0)))


def _settle_rung(bs: GameState) -> int:
    """ADR-0279:结算时点成型度 rung(boss_settle_delta 与 battle/
    encounter(v11,ADR-0407)Δ池 rung 分桶的采样键**单一源**)。

    口径 = _engines_count(四体系达成数:仙舟3/列车2/DOT2/希儿系),
    输入 = **board 全集口径**(ADR-0312,口径统一源=_recount_board——对齐生产
    outcomes board_before 的全集+星徽口径;旧 _board_factions_of 输入
    缺星徽贡献,星徽局 rung 系统性偏低落错桶)+上场名单(希儿系单卡判据)。
    """
    from sr_od.application.currency_war.kernel.cw_bond_equips import _recount_board
    _bf = _recount_board(deployed_slots_of(bs))
    _names = frozenset(d.char_id for d in deployed_slots_of(bs)
                       if getattr(d, 'char_id', ''))
    return _engines_count(_bf, _names)


def boss_settle_delta(bs: GameState, dir_round: int,
                      rng: random.Random) -> int:
    """ADR-0308:boss Δ池桶不可达时的回退结算(胜负面=实测阶梯)。

    胜 → ``BOSS_WIN_DELTA`` 小额(掷 ``node_win_p('boss', round)``,
    n=192 实测 0.05);负 → 旧 ``boss_delta`` 档(幅度层保留)。
    旧 rung 条件胜率(ADR-0277/0306 的 0/0/0.25 + rung2 外推)已被
    实测边际替换——语料是旧策略病局镜像,无条件性可标(成型度
    条件性等新策略语料,见 ``NODE_WIN_P_LADDER`` 注释)。
    仅当 ``live_delta_for`` 返 None(无可及桶)时由调用方使用;
    Δ池可及桶命中时经验分布优先(池是实机真值,sim 规则表是补洞)。
    """
    if rng.random() < node_win_p('boss', round_num_of(bs)):
        return BOSS_WIN_DELTA
    return boss_delta(dir_round, rng)


def node_delta(node: str, round_num: int, dir_round: int,
               rng: random.Random, *, plane: int = 1) -> int:
    """按节点类型的 HP 变化(分层;ADR-0292 起 reward/supply 的
    **池回退档**——Δ池可及时结算侧优先池采样;ADR-0308 起战斗类
    节点回退档胜负面 = 实机实测阶梯 ``node_win_p``):
    reward/supply 零战力要求 → 不掉血(回退档 +2 长线作战回血观测,
    池真值同分布);
    battle → 阶梯掷胜(实机实测:n=192,~0.29),胜 WIN_DELTAS/负旧幅度;
    encounter → 阶梯掷胜(0.04),胜 +2/负 boss 档 × ENCOUNTER_MULT
    (档位不可观,均值近似);
    boss → 阶梯掷胜(0.05),胜 +2/负 boss 档。

    plane≥2(ADR-0362):battle 回退档换 **P2 掉血带**——
    胜率 P2_BATTLE_WIN_P(0.11)/负 -15~-17 均匀带(语料实证,
    P1 阶梯的 r3/r4 战斗胜率与幅度带都不辖 P2);encounter/boss
    沿用 P1 档+标注(P2 语料 3/2 行不足,池可及时优先池采样)。"""
    if node in ('reward', 'supply'):
        return EARLY_WIN_DELTA
    if node == 'encounter':
        if rng.random() < node_win_p('encounter', round_num):
            return EARLY_WIN_DELTA
        return boss_delta(dir_round, rng, multiplier=ENCOUNTER_MULT)
    if node == 'boss':
        if rng.random() < node_win_p('boss', round_num):
            return BOSS_WIN_DELTA
        return boss_delta(dir_round, rng)
    if plane >= 2:
        # ADR-0362:P2 battle 回退档(掉血带 15-17,语料实证)
        if rng.random() < P2_BATTLE_WIN_P:
            return rng.choice(WIN_DELTAS)
        return -rng.randint(P2_LOSS_BAND[0], P2_LOSS_BAND[1])
    return battle_delta(round_num, dir_round, rng)


def _board_factions_of(deployed) -> dict[str, int]:
    """上场角色的阵营计数(生产 board 口径,flows 并计)。

    「过渡阵容凑到没有」的判据输入:recipe_tier(配方档位)/
    三人组在场上——sim 账本 board 不可恒空,否则成型质量不可观测。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS as _CH
    out: dict[str, int] = {}
    for d in (deployed or []):
        if d is None:   # ADR-0392 槽位表空槽
            continue
        cid = getattr(d, 'char_id', '') or ''
        ch = _CH.get(cid)
        if ch is None:
            continue
        for f in (ch.factions or ()) + (ch.flows or ()):
            out[f] = out.get(f, 0) + 1
    return out


#: 公开别名(单一源语义:成型/镜像类消费一律经此名,与旧层兜底门
#: 同一板面计数口径;私有名仅供本模块历史调用点)。
board_factions_of = _board_factions_of


def _board_counts_of(deployed) -> dict[str, int]:
    """board 全集计数(ADR-0312,口径统一)。

    **= ``cw_state._recount_board`` 本体**(alias import,单一源)——
    「主阵营逐件累加」口径不可用:state.board 消费方(recipe 门/
    在场阵营集合/意向②信号)若读压掉流派/独立羁绊/
    星徽贡献的窄口径,与实机 board_from_tracked(左面板真值)系统性
    分叉(审计项 Q4)。未识别(char_id 空)回退 faction 字段(生产 OCR
    空板同形)。"""
    from sr_od.application.currency_war.kernel.cw_bond_equips import _recount_board
    return _recount_board(deployed)


def _first_tier_round(res, tier: int) -> int | None:
    """配方档位首达轮(ledger 的 board_factions 逐轮查
    recipe_tier≥tier 的最小轮;查不到=None)。"""
    # 符号解耦:改接 knowledge/cw_line_facts 权威副本,
    # 不再依赖 kernel/cw_line_defs(迁移挂账文件)
    from sr_od.application.currency_war.knowledge.cw_line_facts import recipe_tier
    for row in res.ledger:
        bf = (row.get('state') or {}).get('board_factions') or {}
        if bf and recipe_tier(bf) >= tier:
            return row.get('round_num')
    return None


def _first_trio_round(res, target: int) -> int | None:
    """核心三人组上场首达轮(deployed∩_CORE_TRIO 计数
    ≥target 的最小轮;查不到=None)。"""
    # 符号解耦:改接 knowledge/cw_line_facts 权威副本
    from sr_od.application.currency_war.knowledge.cw_line_facts import _CORE_TRIO
    for row in res.ledger:
        dep = (row.get('state') or {}).get('deployed') or []
        cnt = sum(1 for d in dep
                  if d.get('char_id') in _CORE_TRIO)
        if cnt >= target:
            return row.get('round_num')
    return None


def _engines_count(board_factions: dict[str, int],
                   deployed_names: frozenset[str] | set[str] = frozenset()
                   ) -> int:
    """过渡体系达成数(三选几+希儿系;两两组合=过渡成型)。

    本体 = cw_deploy_logic.engines_count(单一源);
    符号解耦后权威副本 = knowledge/cw_engine_facts.engines_count
    (cw_deploy_logic 迁移挂账,本薄委托改接新家);历史消费点
    (decision_v2/cw_evolution 等的懒 import)不动,原 cw_delta_pool_gen
    消费点已随 sim 重做删除面退役。
    希儿系=希儿在场 AND(量子同频≥2 OR 贝洛伯格≥2)——
    与三羁绊同级可组合。
    """
    # 符号解耦:改接 knowledge/cw_engine_facts 权威副本
    #(机制事实判据,不依赖迁移挂账的 kernel/cw_deploy_logic)
    from sr_od.application.currency_war.knowledge.cw_engine_facts import (
        engines_count as _impl,
    )
    return _impl(board_factions, deployed_names)


def _transition_formed(board_factions: dict[str, int],
                       deployed_names: frozenset[str] | set[str] = frozenset()
                       ) -> bool:
    """过渡阵容成型判据(transition_combos.md 2026-08-23 定稿):

    四种体系(仙舟3/列车2/DOT2/希儿系)**两两组合**=成型
    (三选二 140/328 帖;希儿系×三过渡 18 帖);
    单个体系点火不等于成型(门槛低的体系如 DOT2 可单独当起点)。
    """
    return _engines_count(board_factions, deployed_names) >= 2


def _first_engines_round(res, target: int) -> int | None:
    """过渡体系达成数首达 target 的最小轮。

    判据走 _engines_count(四体系:仙舟3/列车2/DOT2/希儿系各算一个;
    希儿系需 deployed 含希儿——ledger 的 state.deployed 提供名单);
    target=2=过渡成型(两两组合),target=1=单体系点火
    (门槛低的体系如 DOT2 可单独当起点)。
    """
    for row in res.ledger:
        st = row.get('state') or {}
        bf = st.get('board_factions') or {}
        dep = frozenset(d.get('char_id', '')
                        for d in (st.get('deployed') or []))
        if bf and _engines_count(bf, dep) >= target:
            return row.get('round_num')
    return None


def _battles_before_engines(res, target: int = 2) -> int | None:
    """首达 target 引擎数前经历的战斗结算数(口径修正件)。

    背景:0304 附带观察「v1 到达 rung2 的战斗轮次 30 vs v2 10」的
    口径未在代码定义(一次性诊断数字),0305 复测(20 局配对,seed
    500-519)两臂几乎相等(53 vs 50)——该数字不可再引用。本函数
    把口径钉死:**hp_events 中 round < _first_engines_round(target)
    的战斗类节点(battle/encounter/boss)计数**;未达 target 返 None
    (与 _first_engines_round 同 None 语义,均值只对达成局算)。
    """
    e2 = _first_engines_round(res, target)
    if e2 is None:
        return None
    return sum(1 for rn, nt, _, _ in res.hp_events
               if rn < e2 and nt in ('battle', 'encounter', 'boss'))


def _deployable_depth(bs: GameState) -> int:
    """板深 = **Σboard(全集口径)**(ADR-0312,桶键统一)。

    池语料的板深 = decisions 行 state.board 求和(实机全集口径,双标签
    角色每人贡献 ≥2)——sim 采样键若用 ``min(level, len(deployed))``
    与池语料不同口径:同一局面在池里落深桶、sim 查询落浅桶,采样系统性
    偏向低桶/miss(审计项 Q4:「隐患最重的消费端缺陷」)。本函数是 Δ 池采样
    键/depth_trail/账本 depth 的单一源,与池语料同口径(Σboard,不加
    level 上限——池侧同样无上限,桶键在 live_delta_for 侧统一分桶)。
    「读 deployed 不数 bench」语义由 board=_recount_board
    (deployed 派生)间接保留。
    **辖域(v11 后)**:reward/supply 桶键与观测面(depth_trail/账本);
    boss 桶键=净星深(ADR-0404,deployed_star_depth);encounter
    桶键=rung(v11/ADR-0407,_settle_rung 同源;depth 键下期望伤害
    真平——P1 配对实证「主通道断裂」的 encounter 维由扩容+键查证裁决:
    板深维不可兑换,rung 维可辨)。
    """
    return sum((bs.board.value or {}).values())


def _roll_rotation(rng: random.Random, level: int) -> dict[int, float] | None:
    """本备战期轮岗事件(ADR-0286;审计项 F4):概率 ROTATION_CHANCE 掷中 →
    随机一档(基线 0<p<0.5 才可能被翻倍)×2 → 完整概率表;
    未掷中/该等级无可翻倍档 → None(基线表,生产「未读到概率条」同态)。

    ⚠️ 语义已勘误(01_strategy_layer.md §4.10 概率表族,DESIGN_FINAL_ATTACK
    阻断-2):「20%」是 replay 观测在场频率,非机制概率——运行时被测体
    (sim engine_p1)已改用 ``roll_rotation_per_stage``(对已选环境条件化,
    每阶段 100% 重掷)。本函数保留作旧树 replay 对拍口径,勿在新消费点接线。
    """
    if rng.random() >= ROTATION_CHANCE:
        return None
    base = REFRESH_PROB.get(level, {})
    tiers = [c for c, p in base.items() if 0 < p < 0.5]
    if not tiers:
        return None
    return rotation_probs(level, rng.choice(tiers))


def roll_rotation_per_stage(rng: random.Random, level: int) -> dict[int, float] | None:
    """已选轮岗环境的本备战期概率表(勘误后机制建模,engine_p1 运行时口径)。

    机制(游戏原文 cw_invest_data id=114「每个备战阶段重新随机」):选择后
    **每备战阶段 100% 生效、每阶段重掷翻倍档**;翻倍档分布 = 费用档 1/5
    均匀系**建模假设,实机待核**(01 §4.10 概率表族)。翻倍档不可行档
    (基线 p=0 或 2p≥1)在该级不存在翻倍语义 → 从可行档内均匀重掷
    (对 1/5 假设的可行档截断;全不可行 → None 退基线,同生产「低级帧
    无轮岗」)。生产真值仍是读屏概率条(parse_prob_bar),本函数只服务
    sim 抽店。
    """
    base = REFRESH_PROB.get(level, {})
    tiers = [c for c, p in base.items() if 0 < p < 0.5]
    if not tiers:
        return None
    return rotation_probs(level, rng.choice(tiers))
