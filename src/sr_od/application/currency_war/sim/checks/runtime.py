"""执行画面类检查(liveness/hp/boss_round 等运行态哨兵,分包期6 拆分)。"""

from __future__ import annotations

from sr_od.application.currency_war.sim.checks.pool import _rung_of_row

# =====================================================================
# --- ADR-0289 检查项清偿批:批级聚合 / 条件披露 / 语料级 / 锚登记 ---
# 批级入口 = run_batch_level_checks(ledgers, report, pool_map);
# runner.simulate_p1_batch 的接线随 worker X 合流后并入(冲突隔离:
# 本批不碰 cw_sim.py)。全部为披露型/哨兵型(violations 语义见
# 各 docstring),新发现红条目按 ADR-0289「新发现待裁」清单流转。
# =====================================================================


def _combat_streak_by_round(rows: list[dict]) -> dict[int, int]:
    """重算逐轮「进轮时连胜数」(批⑫ streak_break_interest_fires /
    成型批 no_streak_buy_freeze 的决策侧连胜口径)。

    近似声明:sim 结算写 session.last_streak(cw_sim 批⑤ F4 段)
    但**不进账本**——本重放按战斗类轮(battle/encounter/boss)
    delta≥0=胜 累积连胜;奖励/补给轮不动 streak(生产 streak
    只在战斗结算变)。与 session.last_streak 的差 = 重放口径
    边界,方向披露不裁。
    """
    streak = 0
    out: dict[int, int] = {}
    for row in rows:
        out[row.get('round_num') or 0] = streak
        s = row.get('sim') or {}
        if s.get('node') in ('battle', 'encounter', 'boss'):
            streak = streak + 1 if (s.get('delta') or 0) >= 0 else 0
    return out



def check_late_deploy_full(ledgers: list[list[dict]]) -> dict:
    """成型批 late_deploy_full(末段部署欠员观测;披露型)。

    判据(设计表原文):r7+ 每轮 deployed==cap 或 bench 无 ≥2
    同阵营 → 现状(设计时)159 欠员实例/59 局,先建观测。披露
    计数(违规语义待观测分布定型后再裁——设计表原文「先建观测」)。
    """
    short = tot = 0
    for rows in ledgers:
        for row in rows:
            if (row.get('round_num') or 0) < 7:
                continue
            st = row.get('state') or {}
            dep_n = len(st.get('deployed') or [])
            if dep_n >= (st.get('cap') or 99):
                continue
            tot += 1
            facs: dict[str, int] = {}
            for b in st.get('bench') or []:
                f = b.get('faction')
                if f:
                    facs[f] = facs.get(f, 0) + 1
            if not any(v >= 2 for v in facs.values()):
                continue   # bench 无 ≥2 同阵营 = 合法形态
            short += 1
    return {'violations': 0, 'late_rounds': tot, 'short_instances': short}



def check_late_board_short_idle(ledgers: list[list[dict]]) -> dict:
    """F5 断言门(末窗板位缺口的执行侧零动作;缺陷锚 = late_deploy_full
    85 实例 + 「买到仍缺型」bench 囤积不上板)。

    判据:r≥7 帧 deployed < cap ∧ bench 存在同名禁双合法可上件
    (char_id 不在 deployed 名册)∧ 帧无 DeployMove → 计入 idle 实例。
    **披露型**(沿 late_deploy_full 同款生命周期:先观测后定阈)——
    供给侧修复(F5 top-K 扩展)后首批实测残余 25 局/300,归因 =
    采纳层(scoring 对弱件部署的非正分门),该层修复后本检查升格
    断言门(那时 violations 才有意义)。
    """
    violations = 0
    games: list[int] = []
    for gi, rows in enumerate(ledgers):
        hit = False
        for row in rows:
            if not isinstance(row, dict):
                continue   # 检查网入参容错:异构行(测试夹具/披露行)跳过
            if (row.get('round_num') or 0) < 7:
                continue
            st = row.get('state') or {}
            if not isinstance(st, dict):
                continue
            dep = st.get('deployed') or []
            cap = st.get('cap') or 99
            if len(dep) >= cap:
                continue
            dep_names = {(b.get('char_id') or b.get('name'))
                         if isinstance(b, dict) else b
                         for b in dep}
            bench_ok = any(
                ((b.get('char_id') or b.get('name'))
                 if isinstance(b, dict) else b) not in dep_names
                for b in (st.get('bench') or []))
            if not bench_ok:
                continue
            has_deploy = any(isinstance(a, dict)
                             and a.get('__type__') == 'DeployMove'
                             for a in row.get('actions') or [])
            if not has_deploy:
                violations += 1
                hit = True
        if hit:
            games.append(gi)
    return {'violations': 0, 'idle_instances': violations, 'games': games}


def check_no_streak_buy_freeze(ledgers: list[list[dict]]) -> dict:
    """成型批 no_streak_buy_freeze(连胜期买入冻结观测;披露型)。

    判据(设计表原文):连胜≥5 的决策轮 buys 金 >0(或板面投资
    >0)——现状(设计时)0.11/轮,先观测后定阈。连胜口径 =
    _combat_streak_by_round 重放(批⑤ F4:session.last_streak 不
    进账本,重放近似,边界见该函数)。
    """
    hot = frozen = 0
    for rows in ledgers:
        streaks = _combat_streak_by_round(rows)
        for row in rows:
            if streaks.get(row.get('round_num') or 0, 0) < 5:
                continue
            hot += 1
            buys = ((row.get('sim') or {}).get('spend') or {}) \
                .get('buys') or {}
            if not sum(buys.values()):
                frozen += 1
    return {'violations': 0, 'streak5_rounds': hot,
            'zero_buy_rounds': frozen,
            'freeze_share': round(frozen / hot, 3) if hot else None}



def check_hoard_gold_no_engine(ledgers: list[list[dict]]) -> dict:
    """成型批 hoard_gold_no_engine(r6 囤金无引擎观测;披露型)。

    判据(设计表原文):r6 结束金≥40 且 engines<2 → 报观测项
    (与 levelup_interest_engine_gate 联动)——现状(设计时)
    48/60。engines 口径 = _rung_of_row 四体系数(同步镜像)。
    """
    n = tot = 0
    for rows in ledgers:
        for row in rows:
            if (row.get('round_num') or 0) != 6:
                continue
            tot += 1
            if (row.get('gold') or 0) >= 40 \
                    and _rung_of_row(row) < 2:
                n += 1
    return {'violations': 0, 'r6_rounds': tot, 'hoard_no_engine': n}



def check_second_engine_deadline(ledgers: list[list[dict]]) -> dict:
    """成型批 second_engine_deadline(次引擎期限观测;披露型)。

    判据(设计表原文):首引擎后 ≤3 轮内达次引擎或记原因——
    现状(设计时)gap=8 存在(2/11)。sim 账本无原因字段 →
    披露 gap 分布(engines 口径=_rung_of_row;「引擎」=四体系
    数≥1/≥2 的首达轮)。
    """
    gaps: list[int] = []
    for rows in ledgers:
        first = second = None
        for row in rows:
            r = _rung_of_row(row)
            rn = row.get('round_num') or 0
            if first is None and r >= 1:
                first = rn
            if first is not None and second is None and r >= 2:
                second = rn
                break
        if first is not None:
            gaps.append((second - first) if second is not None else 99)
    miss = sum(1 for g in gaps if g > 3)
    return {'violations': 0, 'first_engine_games': len(gaps),
            'deadline_miss': miss,
            'avg_gap': round(sum(gaps) / len(gaps), 2) if gaps else None}



def check_endgold_residue_channel_probe(ledgers: list[list[dict]]) -> dict:
    """批⑫ endgold_residue_channel_probe(末段零买入轮分流归因;披露)。

    判据(设计表原文):末段零买入轮(r≥7、无 BuyCard、金≥10)
    分流归因:bench 满 / 无可负担牌 / 有牌有位不买(围栏)——
    本批(设计时)基线 739:0:2。判读:卖出/囤件侧策略改动后
    bench 满占比下降且末金比值向 1.5 收敛。
    """
    ch = {'bench_full': 0, 'no_affordable': 0, 'has_card_room_no_buy': 0}
    for rows in ledgers:
        for row in rows:
            if (row.get('round_num') or 0) < 7 \
                    or (row.get('gold') or 0) < 10:
                continue
            if any(a.get('__type__') == 'BuyCard'
                   for a in row.get('actions') or []):
                continue
            st = row.get('state') or {}
            if len(st.get('bench') or []) >= 9:
                ch['bench_full'] += 1
                continue
            affordable = any(
                (w.get('gold') or 0) >= (c.get('cost') or 99)
                for w in (row.get('sim') or {}).get('shop_waves') or []
                for c in w.get('cards') or [])
            if affordable:
                ch['has_card_room_no_buy'] += 1
            else:
                ch['no_affordable'] += 1
    return {'violations': 0, **ch}



def check_formation_gradient_sentinel(ledgers: list[list[dict]]) -> dict:
    """批⑫ formation_gradient_sentinel(rung0 vs rung1 hp 梯度;哨兵)。

    判据(设计表原文):rung0 vs rung1 段 final_hp 差(设计时
    +0.2≈0);战斗 Δ 池按成型分桶拟合落地后应转正,否则耦合仍
    只有 boss 门槛。小批护栏同 ADR-0286(任一侧 <5 局只披露)。
    """
    r0: list[int] = []
    r1: list[int] = []
    for rows in ledgers:
        if not rows:
            continue
        hp = rows[-1].get('hp')
        if hp is None:
            continue
        (r1 if any(_rung_of_row(r) >= 1 for r in rows) else r0) \
            .append(int(hp))
    diff = (sum(r1) / len(r1) - sum(r0) / len(r0)) \
        if r0 and r1 else None
    small_n = r0 and r1 and min(len(r0), len(r1)) < 5
    violations = 1 if (diff is not None and diff <= 0
                       and not small_n) else 0
    out = {'violations': violations, 'rung0_n': len(r0),
           'rung1_n': len(r1),
           'rung0_hp': round(sum(r0) / len(r0), 2) if r0 else None,
           'rung1_hp': round(sum(r1) / len(r1), 2) if r1 else None,
           'diff': round(diff, 2) if diff is not None else None}
    if small_n:
        out['note'] = '样本不足(<5/侧)只披露不判定'
    return out



def check_streak_break_interest_fires(ledgers: list[list[dict]]) -> dict:
    """批⑫ streak_break_interest_fires(破息门行为观测;条件披露)。

    判据(设计表原文):连胜≥2 当轮的买入/破息动作计数进账本
    (或遥测字段),验证 last_streak 接线的行为效果——设计时仅
    日志可见、账本无字段。**依赖标注**:账本无 last_streak 字段
    → 用 _combat_streak_by_round 重放(边界:与 session 真值可能
    差奖励轮口径);依赖在(未来接线 sim.last_streak)则本检查
    自动切真值口径(优先读字段,缺则重放)。
    """
    hot = acted = 0
    streak_source = 'replay'
    for rows in ledgers:
        streaks: dict[int, int] | None = None
        for row in rows:
            s = row.get('sim') or {}
            if streaks is None:
                if isinstance(s.get('last_streak'), dict):
                    streaks = s['last_streak']
                    streak_source = 'ledger'
                else:
                    streaks = _combat_streak_by_round(rows)
            if streaks.get(row.get('round_num') or 0, 0) < 2:
                continue
            hot += 1
            spend = (s.get('spend') or {})
            if sum((spend.get('buys') or {}).values()) \
                    or spend.get('levelup') or spend.get('refresh'):
                acted += 1
    return {'violations': 0, 'streak2_rounds': hot,
            'acted_rounds': acted,
            'act_share': round(acted / hot, 3) if hot else None,
            'streak_source': streak_source}



def check_encounter_rung_sample_budget(pool_map: dict) -> dict:
    """批⑬ encounter_rung_sample_budget(encounter rung 样本预算;条件)。

    判据(设计表原文):encounter rung 桶 n 追踪(r1=9 距 10 仅
    差 1;设计时 4/9/2/0);达标(rung 各桶 n≥10)即并入 battle
    同法分桶。**依赖标注**:encounter 仍 depth 分桶(批⑬ F1
    边界声明)→ 桶键全落 depth 域(≥6)时披露「rung 分桶未
    启用」,不判违规;桶键落 rung 域(≤4)时逐桶披露 n。
    """
    enc = pool_map.get('encounter') or {}
    if not enc:
        return {'violations': 0, 'note': 'encounter 池空不辖'}
    rung_like = {int(b): len(v) for b, v in enc.items() if int(b) <= 4}
    if not rung_like:
        return {'violations': 0,
                'note': 'encounter 仍 depth 分桶(批⑬ 边界声明),'
                        'rung 预算追踪不辖;桶键域 '
                        f'{sorted(int(b) for b in enc)[:6]}'}
    ready = all(n >= 10 for n in rung_like.values())
    return {'violations': 0, 'rung_buckets': rung_like,
            'all_ge_10': ready,
            'note': '达标可并入 battle 同法分桶(批⑬ 设计)'}



def check_mc_faction_calib(ledgers: list[list[dict]]) -> dict:
    """批⑭ d_mc_faction_calib(发牌阵营分布校准;披露型)。

    判据(设计表原文):`_sample_shop` 阵营分布改为按 CHARACTERS
    档内构成采样;judgment = MC 目标阵营单格命中概率/档内真实
    密度 ∈ 1.0±0.1(设计时基线 0.40-0.85×,MC 低估)。**前置
    依赖**:cw_sim 采样器修复未落地(worker X 辖区)→ 本检查
    先披露 sim 批次全波卡池的阵营经验分布 vs 注册表期望密度
    (按经验费用构成加权)的逐阵营比值;修复落地后升格判据带
    (比值出 0.9-1.1 即违规)。
    """
    from collections import Counter

    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    obs = Counter()
    cost_mix = Counter()
    draws = 0
    for rows in ledgers:
        for row in rows:
            for w in (row.get('sim') or {}).get('shop_waves') or []:
                for c in w.get('cards') or []:
                    f = c.get('faction')
                    if f:
                        obs[f] += 1
                        cost_mix[c.get('cost') or 0] += 1
                    draws += 1
    if not draws:
        return {'violations': 0, 'note': '无波数据不辖'}
    total_cost = sum(cost_mix.values())
    exp: dict[str, float] = {}
    norm = 0.0
    for _n, ch in CHARACTERS.items():
        if ch.factions:
            f = ch.factions[0]
            w = cost_mix.get(ch.cost, 0) / (total_cost or 1)
            exp[f] = exp.get(f, 0.0) + w
            norm += w
    if norm > 0:
        exp = {f: v / norm for f, v in exp.items()}
    ratios = {f: round(obs[f] / (exp[f] * draws), 2)
              for f in sorted(exp) if exp[f] > 0.01 and obs.get(f)}
    out_of_band = [f for f, r in ratios.items()
                   if not 0.9 <= r <= 1.1]
    return {'violations': 0,   # 披露:采样器修复落地前不判
            'draws': draws, 'ratios': ratios,
            'out_of_band': out_of_band,
            'note': '前置=_sample_shop 修复(批⑭ F1);落地后'
                    'out_of_band 非空即违规'}





def check_streak_combat_only_income(ledgers: list[list[dict]]) -> dict:
    """连胜金收入口径断言(ADR-0439 收入口径修正后的精确重算锁)。

    口径(cw_sim 收入段镜像;实机 gold 差分实证 108 局/767 轮):
    - 补给轮 ``income.streak`` 必须为 0(实发口径未钉死,仍按 ADR-0351
      零发放建模——补给多发残差 = base+利息照发,见 ``supply_rows``/
      ``supply_issued_extra`` 披露面挂账,待直读样本转正后修正);
    - 奖励轮 streak 分量照发 ``streak_gold(进轮连胜)``(含 counter0=1;
      ADR-0351「奖励轮不发金」半句被全量数据推翻),base 须与
      REWARD_BASE_GOLD_BY_ROUND 成对(cw_sim 收入段已成对,本检查
      锁 streak 侧);
    - 战斗轮 streak==0 且上一轮为败掉的战斗类节点 → 须发
      ``LOSS_GOLD_BY_NODE[上一轮节点]``(败轮金路径精确重算,
      ``loss_gold_rows`` 披露命中数);其余发 ``streak_gold(进轮连胜)``。

    任一行 ``income.streak != 精确重算`` 即违规(双向:少发/多发都报)。

    缺键守卫:账本行 schema 演化(如 node→node_type)时裸
    `.get()` 静默读 None → 断言永久失明、全量仍绿。生产账本
    (cw_sim 收入段)每行必带 sim.node 与 sim.income.streak →
    缺任一键 = 数据异常,计入 violations 并经 missing_key_rows
    披露,不静默绿(锁:test_cw_sim_checks_streak_income)。
    """
    from sr_od.application.currency_war.kernel.cw_economy import (
        LOSS_GOLD_BY_NODE,
        streak_gold,
    )
    violations = ledger_sum = recompute_sum = 0
    missing_key_rows = loss_gold_rows = supply_rows = 0
    supply_issued_extra = 0
    for rows in ledgers:
        # 进轮连胜重放:win 判据 **delta>0**,镜像 cw_sim 结算段——不用
        # _combat_streak_by_round(其 delta>=0 口径为决策侧重放近似,
        # delta==0 战斗轮两者分叉;本检查是精确重算,须与生产逐位一致)
        enter_streaks: dict[int, int] = {}
        _st = 0
        for _row in rows:
            enter_streaks[_row.get('round_num') or 0] = _st
            _s = _row.get('sim') or {}
            if _s.get('node') in ('battle', 'encounter', 'boss'):
                _st = _st + 1 if (_s.get('delta') or 0) > 0 else 0
        _prev: tuple[int, str, int] | None = None   # (rn, node, delta)
        for row in rows:
            sim = row.get('sim')
            inc = sim.get('income') if isinstance(sim, dict) else None
            if (not isinstance(sim, dict) or 'node' not in sim
                    or not isinstance(inc, dict) or 'streak' not in inc):
                missing_key_rows += 1   # schema 异常:计入违规,不静默跳过
                _prev = None
                continue
            node = sim['node']
            inc_streak = inc['streak'] or 0
            ledger_sum += inc_streak
            rn = row.get('round_num') or 0
            enter_streak = enter_streaks.get(rn, 0)
            # 精确重算(镜像 cw_sim 收入段分支;败态判据 delta<=0 与
            # sim 结算段 win=delta>0 一致)
            if node == 'supply':
                expect = 0
                supply_rows += 1
                supply_issued_extra += ((inc.get('base') or 0)
                                        + (inc.get('interest') or 0))
            elif node == 'reward':
                expect = streak_gold(enter_streak)
            elif (enter_streak == 0 and _prev is not None
                    and _prev[1] in LOSS_GOLD_BY_NODE and _prev[2] <= 0):
                expect = LOSS_GOLD_BY_NODE[_prev[1]]
                loss_gold_rows += 1
            else:
                expect = streak_gold(enter_streak)
            if inc_streak != expect:
                violations += 1
            recompute_sum += expect
            _prev = (rn, node, sim.get('delta') or 0)
    return {'violations': violations + missing_key_rows,
            'ledger_streak_income': ledger_sum,
            'combat_only_streak_income': recompute_sum,
            'delta': recompute_sum - ledger_sum,
            'missing_key_rows': missing_key_rows,
            'loss_gold_rows': loss_gold_rows,
            'supply_rows': supply_rows,
            'supply_issued_extra': supply_issued_extra}



def check_shop_distinct_names_invariant(ledgers: list[list[dict]]) -> dict:
    """批⑱ F4 shop_distinct_names_invariant(同波名字唯一性;披露)。

    判据(设计表原文):同波 cards 名字唯一性断言——真值裁决
    「允许/禁止」后启用其一(禁→违规;允→删除本检查)。**悬置
    待 F4 裁决** → 披露计数(重复名波数),violations 恒 0;
    裁决后按裁决侧切换。
    """
    dup_waves = tot = 0
    for rows in ledgers:
        for row in rows:
            for w in (row.get('sim') or {}).get('shop_waves') or []:
                names = [c.get('name') for c in w.get('cards') or []
                         if c.get('name')]
                tot += 1
                if len(names) != len(set(names)):
                    dup_waves += 1
    return {'violations': 0, 'waves': tot, 'dup_name_waves': dup_waves,
            'note': '悬置待批⑱ F4 真值裁决(允许/禁止)'}



def check_supply_agent_semantics(ledgers: list[list[dict]]) -> dict:
    """批⑲ supply_agent_semantics(supply 子账本披露;条件披露)。

    判据(设计表原文):supply 事件披露 pick_reason / refresh 分支
    是否真执行 / char 通道缺失标记(sim.supply 子账本)。**依赖
    标注**:sim.supply 子账本未接线(cw_sim 侧,worker X)→
    字段在则披露计数,不在则披露跳过(依赖断裂不静默)。
    """
    with_supply = 0
    for rows in ledgers:
        if any('supply' in (row.get('sim') or {}) for row in rows):
            with_supply += 1
    if with_supply:
        return {'violations': 0, 'games_with_supply_ledger': with_supply,
                'note': 'sim.supply 子账本在位,细节披露随接线补'}
    return {'violations': 0, 'games_with_supply_ledger': 0,
            'note': '依赖未接线:sim.supply 子账本(cw_sim 侧)'
                    '——披露跳过,不判'}



def check_refresh_cost_channel(ledgers: list[list[dict]]) -> dict:
    """批⑲ refresh_cost_channel(刷新成本通道;披露型)。

    判据(设计表原文):sim 按真值分布(或至少显式披露「恒 2
    假设」)更新 shop_refresh_cost;0/3/5 语义先由实机/数据裁决。
    **悬置待语义裁决** → 披露账本观测到的刷新成本取值集(期望
    {2}=恒 2 假设在用;出现 0/3/5 = 真值分布已接,届时随裁决
    判读)。
    """
    costs: set[int] = set()
    n = 0
    for rows in ledgers:
        for row in rows:
            for a in row.get('actions') or []:
                if a.get('__type__') == 'RefreshShop':
                    n += 1
                    c = a.get('cost')
                    if c is not None:
                        costs.add(int(c))
    return {'violations': 0, 'refreshes': n,
            'observed_costs': sorted(costs),
            'note': '恒 2 假设在用' if costs == {2} else
                    '成本取值偏离恒 2——真值分布可能已接,随批⑲ '
                    'F4 裁决判读'}



def check_hp_readable_disclosure(ledgers: list[list[dict]]) -> dict:
    """批⑳ sim_hp_readable_disclosure(hp_readable 字段;条件披露)。

    判据(设计表原文):sim 账本行补 `hp_readable: true`(或文档
    声明 sim 侧隐含完美观测,免跨侧 join 误读 absent)。**依赖
    标注**:字段未接线(cw_sim 侧)→ 本检查即「文档声明」载体:
    sim 侧 hp 隐含完美观测(结算真值,无 OCR 读失败),跨侧
    join 时 absent ≠ 读失败;字段接线后本检查转计数披露。
    """
    with_field = sum(
        1 for rows in ledgers for row in rows
        if 'hp_readable' in (row.get('sim') or {}))
    return {'violations': 0, 'rows_with_field': with_field,
            'note': 'sim 侧 hp 隐含完美观测(结算真值);'
                    'hp_readable 接线前以此声明为准(批⑳ F4)'}



def check_briefing_pipeline_liveness(ledgers: list[list[dict]]) -> dict:
    """批㉓ briefing_pipeline_liveness(简报管线活跃度;条件披露)。

    判据(设计表原文):line_v2/decision_v2 栈批结果披露「comp_score 系调用
    次数」(设计时恒 0=简报管线休眠标);策略栈切换时本披露自动
    翻转语义,防「管线复活没人知道」。**依赖标注**:comp_score
    计数未进账本(cw_sim 侧)→ 字段在则披露,不在则披露休眠标
    (依赖断裂不静默)。
    """
    calls = sum(
        (row.get('sim') or {}).get('comp_score_calls', 0)
        for rows in ledgers for row in rows
        if isinstance((row.get('sim') or {})
                      .get('comp_score_calls'), int))
    has_field = any('comp_score_calls' in (row.get('sim') or {})
                    for rows in ledgers for row in rows)
    return {'violations': 0,
            'comp_score_calls': calls,
            'note': ('计数披露(管线活跃度)'
                     if has_field else
                     '依赖未接线:comp_score_calls 不在账本——'
                     '按批㉓ F1 计数包装口径,当前树恒 0'
                     '(简报管线休眠标)')}



def check_deploy_cap_reader_noise(ledgers: list[list[dict]]) -> dict:
    """迁移审计批 deploy_cap_reader_noise(cap<level 冲突族;条件披露)。

    判据(设计表原文):cap<level 冲突族治理:diff≥2 判读错
    (diff=1 留「诅咒」空档)、复现阈值实化;读链守卫(与 level
    交叉)。生产侧为读链质量门;sim 账本侧披露 cap<level 行计数
    (sim cap=max_units() 与 level 同源,理论恒 0;>0 = cap 写入
    通道回归/宝钻通道接线后的语义变化,先披露后裁)。
    """
    n = tot = 0
    for rows in ledgers:
        for row in rows:
            st = row.get('state') or {}
            cap, level = st.get('cap'), st.get('level')
            if cap is None or level is None:
                continue
            tot += 1
            if cap < level:
                n += 1
    return {'violations': 0, 'rows': tot, 'cap_lt_level': n,
            'note': 'sim 侧理论恒 0;>0 = cap 写入通道变化,'
                    '批㉔ F5 读链守卫侧另辖'}



def check_calibration_dead_knob_disclosure(report: dict | None) -> dict:
    """批㉗ calibration_dead_knob_disclosure(死旋钮绕过标;披露)。

    判据(设计表原文):死旋钮族(WIN/LOSS/ENCOUNTER_MULT/
    NODE_TYPE_POOL)在 snapshot 批报告打「被 Δ 池绕过」标,防
    误读(F5:死旋钮改动不改 snapshot 行为)。**依赖标注**:
    report 标记键由 cw_sim 接线(worker X)→ 无 report / 无标记
    时披露提醒(判读 snapshot 批勿读死旋钮),不判违规。
    """
    if report is None:
        return {'violations': 0,
                'note': '无报告对象;判读提醒:snapshot 口径下 '
                        'WIN/LOSS/ENCOUNTER_MULT/NODE_TYPE_POOL 被 '
                        'Δ 池绕过(批㉗ F1/F5)'}
    if report.get('dead_knob_bypassed'):
        return {'violations': 0, 'marked': True}
    return {'violations': 0, 'marked': False,
            'note': '报告缺「被 Δ 池绕过」标(cw_sim 接线待合流);'
                    '判读 snapshot 批勿读死旋钮'}



def check_reward_heal_fat_tail(ledgers: list[list[dict]]) -> dict:
    """批㉗ reward_heal_fat_tail(奖励胖尾生效哨兵;披露型)。

    判据(设计表原文):奖励/补给轮结算由恒 +2 改经验分布采样
    (语料 41 样本 F4 分布;至少加「17% 概率 +20~39」混合);A/B
    预测 avg_final_hp +15~25——**上移量即裂口归因份额,改前先
    留基线**。**前置依赖**:sim 结算改造未落地(cw_sim,worker
    X)→ 本哨兵披露 reward/supply 轮 Δ 分布:全 ≤2 = 胖尾未落
    地(基线态);出现 >5 = 已落地(与 hp_upper_bound_truth
    联动,ADR-0287)。
    """
    deltas: list[int] = []
    for rows in ledgers:
        for row in rows:
            s = row.get('sim') or {}
            if s.get('node') in ('reward', 'supply') \
                    and s.get('delta') is not None:
                deltas.append(int(s['delta']))
    if not deltas:
        return {'violations': 0, 'note': '无奖励轮样本'}
    big = sum(1 for d in deltas if d > 5)
    return {'violations': 0, 'rounds': len(deltas),
            'max_delta': max(deltas),
            'gt5_share': round(big / len(deltas), 3),
            'fat_tail_landed': big > 0,
            'note': '未落地=恒 +2 基线态(批㉗ F3/F4 修复前置)'}



def check_boss_win_curve_sample_gate(ledgers: list[list[dict]]) -> dict:
    """批㉗ boss_win_curve_sample_gate(boss 胜局样本门;披露)。

    判据(设计表原文):boss 胜率表扩锚点前置条件=实机 boss 胜局
    样本(rung 分桶 n≥3/桶);到点前 boss 族 A/B 结论只标「单点
    外推敏感度」,不作策略裁决依据。本检查披露 sim 批 boss 轮
    的 rung 分桶 n(观察面;实机样本门在 outcomes 侧另行统计)。
    """
    buckets: dict[int, int] = {}
    for rows in ledgers:
        for row in rows:
            if (row.get('sim') or {}).get('node') != 'boss':
                continue
            b = _rung_of_row(row)
            buckets[b] = buckets.get(b, 0) + 1
    gate = all(n >= 3 for n in buckets.values()) if buckets else False
    return {'violations': 0, 'rung_buckets': buckets,
            'gate_met': gate,
            'note': 'sim 侧观察面;实机 boss 胜局样本门(批㉗ F6)'
                    '到点前 boss 族 A/B 只标单点外推敏感度'}



def check_pool_hit_rate_disclosure(ledgers: list[list[dict]]) -> dict:
    """批㉗ pool_hit_rate_disclosure(池命中率三数;条件披露)。

    判据(设计表原文):批报告加 battle/encounter/boss 池命中率
    三数;fallback 池模式下三数应为 0/0/0——命中率>0 却标
    fallback = 配置回归哨兵。**依赖标注**:池命中率计数未进
    账本(cw_sim wrap,批㉗ F2 探针法)→ sim.pool_hits 字段在
    则披露三数,不在则披露跳过。
    """
    for rows in ledgers:
        for row in rows:
            ph = (row.get('sim') or {}).get('pool_hits')
            if isinstance(ph, dict):
                agg: dict[str, int] = {}
                for rows2 in ledgers:
                    for row2 in rows2:
                        h = (row2.get('sim') or {}).get('pool_hits')
                        if isinstance(h, dict):
                            for k, v in h.items():
                                agg[k] = agg.get(k, 0) + int(v)
                return {'violations': 0, 'pool_hits': agg}
    return {'violations': 0,
            'note': '依赖未接线:sim.pool_hits(cw_sim 批㉗ F2 '
                    'wrap 法)——披露跳过,不判'}



def check_shop_cost_conformance(ledgers: list[list[dict]]) -> dict:
    """批④ shop_cost_conformance(发牌费用分布符合性;混合判据)。

    判据(设计表原文):sim 逐 level 发牌成本分布 vs REFRESH_PROB
    (按 sim 实际 max_cost 口径)最大偏差 ≤0.01,且「池内存在某
    费档但 0 供给」= 0——设计时现状 lv9 4费偏差 .30(0 供给,
    旧池截断;ADR-0272 已修)。**口径声明**:①0.01 带是 MC 专用
    (专用大样本),批级经验分布带 MC 噪声 → 偏差只披露不判;
    ②等级 join 用行末 state.level,26% 行有 XP 重放偏差(批⑭
    解析自纠)——zero-supply 判据用 p≥0.05 且该级抽牌 ≥200 的
    强条件压制两类噪声;违反 = 池截断回归(ADR-0272)。
    """
    from sr_od.application.currency_war.data.cw_shop_odds import REFRESH_PROB
    by_level: dict[int, dict[int, int]] = {}
    for rows in ledgers:
        for row in rows:
            level = (row.get('state') or {}).get('level')
            if not level:
                continue
            d = by_level.setdefault(level, {})
            for w in (row.get('sim') or {}).get('shop_waves') or []:
                for c in w.get('cards') or []:
                    d[c.get('cost') or 0] = d.get(c.get('cost') or 0, 0) + 1
    issues: list[str] = []
    max_dev = 0.0
    for level, d in sorted(by_level.items()):
        tot = sum(d.values())
        if tot < 200:
            continue
        for cost, p in (REFRESH_PROB.get(level) or {}).items():
            emp = d.get(cost, 0) / tot
            max_dev = max(max_dev, abs(emp - p))
            if p >= 0.05 and emp == 0:
                issues.append(
                    f'lv{level} {cost}费 p={p} 但 0 供给'
                    f'(池截断回归——批④/ADR-0272)')
    return {'violations': len(issues), 'issues': issues[:5],
            'max_dev': round(max_dev, 4),
            'note': 'max_dev 含 MC 噪声+XP 重放偏差,只披露;判据'
                    '只辖 zero-supply 强条件'}





def check_boss_round_real_actions(ledgers: list[list[dict]]) -> dict:
    """自由批 boss_round_real_actions(r9 金足零真实动作;披露)。

    判据(设计表原文):boss 轮(r9)8 段中非振荡的 Buy/LevelUp
    ≥1(或金≥cost 时必有真实动作)——设计时现状 seed4 r9 金101
    全振荡。**口径降级声明**:sim 每轮单决策段(8 段生产语义
    sim 不建模)→ 账本口径 = r9 轮内「波里有可负担件且金≥10
    且零 Buy/LevelUp」局计数;r408 后振荡已由 no_same_round_
    buy_sell 辖,本检查盯「金足全静默」形态——设计为断言式,
    但「策略不花末段金」是批⑦ endgame_gold_sink 立项(归档)
    的已知面 → 先披露计数,红量大时按 math_proofs 立项裁决。
    """
    stalls = tot = 0
    for rows in ledgers:
        for row in rows:
            if (row.get('round_num') or 0) != 9:
                continue
            tot += 1
            if (row.get('gold') or 0) < 10:
                continue
            if any(a.get('__type__') in ('BuyCard', 'LevelUp')
                   for a in row.get('actions') or []):
                continue
            affordable = any(
                (w.get('gold') or 0) >= (c.get('cost') or 99)
                for w in (row.get('sim') or {}).get('shop_waves') or []
                for c in w.get('cards') or [])
            if affordable:
                stalls += 1
    return {'violations': 0, 'r9_rounds': tot,
            'gold_affordable_no_action': stalls,
            'note': '披露口径;末段金出口裁决归 math_proofs 立项'
                    '(批⑦ endgame_gold_sink)'}



# --- 清偿批:语料级检查(outcomes/summary dict,调用方显式调) ----

def check_attach_run_detector(outcome_rows: list[dict]) -> list[str]:
    """批⑬ attach_run_detector(run 接管段标签;语料级)。

    判据(设计表原文):首条 exogenous 行 plane=1 且 round>1 →
    runs 打 attach 标签;判读/池生成默认排除。吃 outcomes 行
    (run_id/plane/round_num 键),按 run 分组判首行形态。
    接管段遥测降权纪律(skill)的机械化前置。
    """
    seen_first: set[str] = set()
    out: list[str] = []
    for row in outcome_rows:
        rid = row.get('run_id')
        if rid is None or rid in seen_first:
            continue
        seen_first.add(rid)
        if (row.get('plane') or 0) == 1 \
                and (row.get('round_num') or 0) > 1:
            out.append(f'{rid}: 首行 plane=1 r{row.get("round_num")}'
                       f'>1(attach 接管段——判读/池生成默认排除,'
                       f'批⑬)')
    return out



def check_hp_monotonic_sentinel(outcome_rows: list[dict]) -> list[str]:
    """批⑬ hp_monotonic_sentinel(同 run hp 只降不升;语料级)。

    判据(设计表原文):同 run outcomes hp_after 序列出现上升 →
    报警(HP 只降不升;run154910 71→100 接管帧实证——重启接管
    段 hp 一律不可作判据的机械化哨兵)。hp_after 缺失行跳过。
    """
    last: dict[str, int] = {}
    out: list[str] = []
    for row in outcome_rows:
        rid = row.get('run_id')
        hp = row.get('hp_after')
        if rid is None or hp is None:
            continue
        if rid in last and hp > last[rid]:
            out.append(
                f'{rid}: hp {last[rid]}→{hp} 上升(接管帧错值/'
                f'读链毒化——批⑬,该段判读降权)')
        last[rid] = int(hp)
    return out



def check_plane_reached_consistency(summary: dict,
                                    outcome_rows: list[dict]) -> list[str]:
    """批⑧ F4 plane_reached_consistency(summary↔outcomes 对拍)。

    判据(设计表原文):summary 的 plane_reached 与 outcomes 末条
    plane 对拍(run_20260823_105348 实锤:runs 记 3 / outcomes
    真值 2)。不一致 = summary 写入路径口径可疑(FAIL/崩溃/
    重启兜底缺失族,批⑧ F2)。
    """
    last_plane: dict[str, int] = {}
    for row in outcome_rows:
        rid = row.get('run_id')
        if rid is not None and row.get('plane') is not None:
            last_plane[rid] = int(row['plane'])
    out: list[str] = []
    rid = summary.get('run_id') or summary.get('runId')
    claimed = summary.get('plane_reached')
    if rid is None or claimed is None:
        return out
    truth = last_plane.get(rid)
    if truth is not None and int(claimed) != truth:
        out.append(
            f'{rid}: summary plane_reached={claimed} vs outcomes '
            f'末条 plane={truth}(汇总写入路径不一致——批⑧ F4)')
    return out

