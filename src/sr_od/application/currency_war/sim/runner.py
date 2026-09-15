"""sim 批量运行/对照/账本落盘/CLI(自 cw_sim 拆出,分包期6)。

批量入口 simulate_p1_batch(含 P1 段辖域切片 _Plane1View 与满级拒付
按 plane 披露)、A/B 与敏感性对照、sim 账本落盘(SIM_RUNS_DIR = telemetry/sim,
与生产 live 流根隔离,写入器有目录守卫)、快照合成与 ``python -m`` CLI。
"""

from __future__ import annotations

import random
from pathlib import Path

from sr_od.application.currency_war.data.cw_battle_tables import (
    P2_COMBAT_DEFAULT,
    P2CombatCalib,
)

# 血预算停手·终止分支账本决策位(设计 迁移审计 w659(git 历史) v2 §5.1 R4;ADR-0469)——
# 账本行 'terminal_release' 键的写入侧单一源 =
# sim/checks/segments.terminal_release_bit(sim 引擎轮入口调用,本模块
# 只消费行键不作记账面)。
from sr_od.application.currency_war.kernel.cw_battle_calib import (
    _battles_before_engines,
    _first_engines_round,
    _first_tier_round,
    _first_trio_round,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    STRATEGY_EFFECTS,
    EconomyEffect,
    normalize_invest_name,
)
from sr_od.application.currency_war.sim.cw_sim_invest import (
    SimInvestProfile,
)

# 开局 bench 构成(遥测校准:开局 4 张,1 费主导)
START_BENCH_COUNT: int = 4
START_BENCH_COST_WEIGHTS: tuple[tuple[int, float], ...] = ((1, .65), (2, .35))


def _overlay_xp_per_refresh(strategy_names: list[str]) -> int:
    """付费刷新产经验数值(单一源 = ``cw_investments.STRATEGY_EFFECTS`` overlay)。

    - 逐持卡名(先 normalize_invest_name 归一 OCR 分隔符形变)查 overlay 的
      EffectSpec,payload 为 EconomyEffect 时累加 xp_per_refresh;未入 overlay
      的卡不供值 —— overlay 是该查询键的唯一供数面,overlay 值变更 sim 跟随。
    - pending 条目(verdict=None)保守支:其 payload 数值本身即按保守支建模
      (现均无 xp_per_refresh,与旧 STRATEGY_ECONOMY 聚合路径同值);verdict
      定谳若引入新语义(如 经验就是财富 改道),须回本查询点同步。
    """
    total = 0
    for n in strategy_names:
        spec = STRATEGY_EFFECTS.get(normalize_invest_name(n))
        if spec is None or not isinstance(spec.payload, EconomyEffect):
            continue
        total += spec.payload.xp_per_refresh
    return total

# 收入模型(r305 真值接入:sim 与决策共用 cw_economy 单一源;
# ADR-0439 收入口径修正:败轮节点金 + 奖励轮 base/streak 成对查表)
from sr_od.application.currency_war.kernel.cw_economy import (  # noqa: E402,F401
    BASE_INCOME,
    ECONOMY_CALIB_VERSION,
    LOSS_GOLD_BY_NODE,
    REWARD_BASE_GOLD_BY_ROUND,
    streak_gold,
)
from sr_od.application.currency_war.sim.engine_p1 import (  # noqa: E402
    simulate_p1,
)
from sr_od.application.currency_war.sim.pool import (  # noqa: E402
    _AUTO_REPLAY_DIR,
    SimResult,
    _Pool,
    plane_view,
    resolve_pool,
)


class _Plane1View:
    """P1 段辖域切片(ADR-0362,`w157_p2/`):planes>=2 批次的 P1 锚定指标
    只消费 plane=1 行;planes=1 时视图 ≡ 原结果(零漂移)。

    hp_events 的 P1 行 ts∈1-9、P2 行 ts≥10(P2_NODE_SEQUENCE 首轮
    ts=10)——按 ts 切片;ledger 按 plane 字段切片。
    """

    def __init__(self, r: SimResult):
        self.ledger = [row for row in r.ledger
                       if (row.get('plane') or 1) == 1]
        self.hp_events = [e for e in r.hp_events if e[0] <= 9]
        self.dir_round = r.dir_round
        self.final_hp = r.final_hp



def _cap_rejects_by_plane(results: list) -> dict[int, int]:
    """满级 LevelUp 拒付按 plane 分解(键=plane,值=拒付次数)。

    为什么:lv≥9 态在实机只见 plane 2/3(实机 P1 等级上限 7),拒付
    总量把「P1 等级虚高噪声」与「P2/P3 真实语义分歧」混在一起,无法
    为 LEVEL_CAP 放开批提供干净读数。逐轮账本行自带 plane 字段,聚合
    端按行分组即可,逐轮执行路径零改动(纯披露面)。键缺省=该 plane
    无拒付(不补 0,保持稀疏)。
    """
    by_plane: dict[int, int] = {}
    for r in results:
        for row in r.ledger:
            n = (row.get('sim') or {}).get('level_cap_rejects', 0)
            if n:
                p = int(row.get('plane') or 1)
                by_plane[p] = by_plane.get(p, 0) + n
    return dict(sorted(by_plane.items()))



def simulate_p1_batch(n: int = 500, *, use_refresh: bool = True,
                      seed_base: int = 0,
                      pool: str | Path = 'auto',
                      ledger: bool | Path = True,
                      checks: bool = True,
                      planes: int = 1,
                      invest: SimInvestProfile | bool = False,
                      invest_arm: str = 'sink',
                      p2_combat: P2CombatCalib | None = None,
                      max_rounds: int | None = None,
                      synthesis_chain: bool = False,
                      equip_wear_effect: float = 0.0) -> dict:
    """批量模拟 + 统计(HP≥60 概率/方向建立分布/平均末 HP)。

    :param max_rounds: 段级窗口(迁移审计 w278(git 历史) sim 段级短跑批;None=整局,既有
        行为**逐位不变**)。设 K 后,各局的**前 K 轮逐轮决策流**
        (decisions/actions/gold/board/spend,state 快照带当时值)作为
        ``segment_checks`` 的输入——截断以**账本切片**实现:逐轮执行
        是因果序的(轮 k 的 state/决策只依赖轮 <k,rng 消耗按轮顺序),
        前缀行与真跑到第 K 轮停下的决策流完全一致(同 seed 同池下
        零差异),无需真正中断模拟循环。报告带 ``max_rounds`` 键披露
        窗口(None=整局)。

    :param planes: 透传 ``simulate_p1``(1=P1 段——历史口径逐位不变;
        2=追加 P2 段,报告增 P2 headline 四联,ADR-0362/`w157_p2/`)。
    :param invest: 透传 ``simulate_p1``(`w162_inject/`/ADR-0364;注入批报告增
        invest headline 三联:环境注入率/持卡均值/P1 锁定轮——含 D 的
        P1 侧结论自此批起以注入口径为基准)。
    :param invest_arm: 透传 ``simulate_p1``(投资选卡双臂批;'sink'=基线臂
        真实判据(缺省)| 'freq'=旧频次注入对照臂);批报告以
        ``invest_arm`` 键披露(双臂报告同形,缺臂标 = 无法对账)。

    返回含 ``pool_fingerprint``/``pool_source``(⓪):跨日基线
    对照必须核对指纹一致——池随实机追加漂移,裸数字不可比。

    :param ledger: True=落两流账本到 ``telemetry/sim/<batch_id>/``"
        (decisions+outcomes.jsonl,判读 CLI 可查);Path=显式目录;
        False=不落盘。batch_id 含时间戳,自动保留最近
        ``_SIM_RUNS_KEEP`` 个批次。
    :param checks: 跑完执行 cw_sim_checks 异常断言(②;默认开,
        结果挂 ``checks_violations``)。
    """
    import statistics
    results = [simulate_p1(seed_base + i, use_refresh=use_refresh,
                           pool=pool, planes=planes, invest=invest,
                           invest_arm=invest_arm,
                           p2_combat=p2_combat,
                           synthesis_chain=synthesis_chain,
                           equip_wear_effect=equip_wear_effect)
               for i in range(n)]
    # ADR-0362(`w157_p2/`):P1 过程指标的辖域切片——planes>=2 时账本含
    # P2 段行,P1 锚定指标(成型/败场/引擎)只算 plane=1 行;
    # planes=1 时视图 ≡ 原结果(零漂移)。
    views = [_Plane1View(r) for r in results]
    _entered = [r for r in results if r.p2_entered]
    report = {
        'n': n,
        'pool_fingerprint': results[0].pool_fingerprint,
        'pool_source': results[0].pool_source,
        'hp_ge_60': sum(1 for h in (r.final_hp for r in results) if h >= 60) / n,
        'avg_final_hp': statistics.mean(r.final_hp for r in results),
        # r370(新验收对齐,goal rev5):战斗节点败场 ≤2 概率
        # (battle/encounter/boss 计分,奖励/补给不计;hp_events
        # 的 delta<0=败)。与实机 outcomes killed+node_type 同构。
        'battle_losses_le_2': sum(
            1 for v in views
            if sum(1 for _, nt, d, _ in v.hp_events
                   if nt in ('battle', 'encounter', 'boss') and d < 0) <= 2
        ) / n,
        'dir_by_r2': sum(1 for d in (r.dir_round for r in results) if d <= 2) / n,
        'dir_by_r4': sum(1 for d in (r.dir_round for r in results) if d <= 4) / n,
        'dir_never': sum(1 for d in (r.dir_round for r in results) if d >= 99) / n,
        'avg_dir_round': (statistics.mean(
            [d for d in (r.dir_round for r in results) if d < 99])
            if any(r.dir_round < 99 for r in results) else float('nan')),
        'avg_refreshes': sum(r.refreshes for r in results) / n,
        # ===== P2 headline 四联(ADR-0362,`w157_p2/`;planes>=2 有意义)=====
        # 存活轮/P2 胜率/hp0 率/D 次数——P2 修法(ADR-0361 V_D)
        # 的行为分布验证场;比率分母=进场 P2 的局(P1 段死局不计,
        # 与实机「活过 P1 才有 P2」幸存口径一致,迁移审计 w156(git 历史) §3 风险声明)。
        'p2_entered_rate': len(_entered) / n,
        'avg_p2_rounds': (round(statistics.mean(
            [r.p2_rounds for r in _entered]), 2)
            if _entered else None),
        'p2_win_rate': (round(sum(r.p2_combat_wins for r in _entered)
                              / max(1, sum(r.p2_combat_total
                                           for r in _entered)), 4)
            if any(r.p2_combat_total for r in _entered) else None),
        'p2_hp0_rate': (sum(1 for r in _entered if r.p2_hp0)
                        / len(_entered) if _entered else None),
        'avg_p2_refreshes': (round(statistics.mean(
            [r.p2_refreshes for r in _entered]), 2)
            if _entered else None),
        # ===== P2 校准层与判读观测 headline(`w193_p2sim/`/ADR-0377;判读同构
        # 口径对齐 `w182_p2/`/`w183_carry/`:金带走量/carry 笔数价格带/意向切换/lv 到达)=====
        'p2_combat_calibrated': bool(
            _entered and _entered[0].p2_combat_calibrated),
        'avg_p2_gold_carried': (round(statistics.mean(
            [r.p2_gold_carried for r in _entered
             if r.p2_gold_carried is not None]), 2)
            if any(r.p2_gold_carried is not None for r in _entered)
            else None),
        'p2_carry_buys': {k: sum(r.p2_buys_by_cost.get(k, 0)
                                 for r in _entered)
                          for k in ('1-2', '3', '4-5')},
        'avg_p2_carry_buys': (round(statistics.mean(
            [sum(r.p2_buys_by_cost.values()) for r in _entered]), 2)
            if _entered else None),
        'p2_switch_rate': (sum(1 for r in _entered if r.p2_switch_events)
                           / len(_entered) if _entered else None),
        'avg_p2_first_switch_round': (round(statistics.mean(
            [r.p2_switch_events[0][0] for r in _entered
             if r.p2_switch_events]), 2)
            if any(r.p2_switch_events for r in _entered) else None),
        'p2_lv7_reach_rate': (sum(1 for r in _entered
                                  if r.p2_lv7_round is not None)
                              / len(_entered) if _entered else None),
        # `w193_p2sim/`/ADR-0377:校准层上下文(检查器带锚消费;bands=本批实参)
        'p2_calib': {
            'win_delta': (p2_combat or P2_COMBAT_DEFAULT).win_delta,
            'bands': {
                'battle_r1':
                    list((p2_combat or P2_COMBAT_DEFAULT).band_battle_r1),
                'battle_early':
                    list((p2_combat or P2_COMBAT_DEFAULT).band_battle_early),
                'battle_late':
                    list((p2_combat or P2_COMBAT_DEFAULT).band_battle_late),
                'encounter':
                    list((p2_combat or P2_COMBAT_DEFAULT).band_encounter),
                'boss': list((p2_combat or P2_COMBAT_DEFAULT).band_boss),
            },
        },
        # ===== invest headline 三联(`w162_inject/`/ADR-0364;invest 注入时有意义)=====
        # 环境注入率/P1 持卡均值/P1 锁定轮分布(①资格通道激活直证:
        # 无注入语料下 invest_p1_lock_rate 恒 0——`w161_refresh/` 缺口闭合对照键)
        # 双臂批:invest_arm 键 = 批的臂标(双臂报告同形,缺臂标 = 无法对账)
        'invest_arm': (invest_arm if invest else None),
        'invest_env_rate': (sum(1 for r in results if r.invest_env) / n
                            if invest else None),
        'avg_invest_strategies': (round(statistics.mean(
            [len(r.invest_strategies) for r in results]), 2)
            if invest else None),
        'invest_p1_lock_rate': (sum(
            1 for r in results if r.p1_locked_rounds > 0) / n
            if invest else None),
        'avg_p1_locked_rounds': (round(statistics.mean(
            [r.p1_locked_rounds for r in results]), 2)
            if invest else None),
        # r394/r399(过渡阵容成型指标;判据单一源=transition_combos.md
        # 2026-08-23 定稿:四体系两两组合):
        # engines2_by_r6=四体系(仙舟3/列车2/DOT2/希儿系)达成≥2 的
        # r6 前占比——「位面1 能否顺利凑到过渡阵容」的直接度量。
        # 希儿系=希儿在场 AND(量2 OR 贝2),伤害在希儿技能层,
        # 量子/贝是放大器(单卡依赖,r399 用户实战确认)。
        'engines2_by_r6': sum(
            1 for v in views
            if _first_engines_round(v, 2) is not None
            and _first_engines_round(v, 2) <= 6) / n,
        'recipe5_by_r6': sum(
            1 for v in views
            if _first_tier_round(v, 5) is not None
            and _first_tier_round(v, 5) <= 6) / n,
        'trio3_by_r8': sum(
            1 for v in views
            if _first_trio_round(v, 3) is not None
            and _first_trio_round(v, 3) <= 8) / n,
        # ADR-0305 件2:到达 e2 前的战斗结算数(口径钉死,防 0304
        # 「30 vs 10」类未定义口径误读;None=未达 e2 不计入均值)
        'avg_battles_before_e2': (round(statistics.mean(
            [b for b in (_battles_before_engines(v, 2) for v in views)
             if b is not None]), 2)
            if any(_first_engines_round(v, 2) is not None
                   for v in views) else None),
        # ADR-0283(批⑰ F6)+ `w566_sim_guard/` 语义收窄:全批满栏**非合成**拒买
        # 总次数(合成买已执行不计入;0=守卫兜底未介入,>0 = 满仓态
        # 买门判读须对照此计数)
        'bench_full_skipped_buys': sum(
            (row.get('sim') or {}).get('bench_full_skipped_buys', 0)
            for r in results for row in r.ledger),
        # ADR-0285(批㉑ F3):守卫拦截买折算金总额(净滞留口径输入)
        'bench_full_skipped_gold': sum(
            (row.get('sim') or {}).get('bench_full_skipped_gold', 0)
            for r in results for row in r.ledger),
        # ADR-0284(批㉒ F1/F5):幻影再买提案与池 take 地板命中
        # (真策略批次双 0;>0 = 槽消费回归/池守恒破)
        'phantom_rebuys': sum(r.phantom_rebuys for r in results),
        # 满级 LevelUp 拒付总次数(执行层 cap 守卫全批披露)
        'level_cap_rejects': sum(
            (row.get('sim') or {}).get('level_cap_rejects', 0)
            for r in results for row in r.ledger),
        # 血预算停手·停升级拒付总次数(决策层门;设计件 12/ADR-0448
        # ——语义生效面披露:0=停手线全批未触发,P1 早中期恒 0)
        'blood_budget_levelup_rejects': sum(
            (row.get('sim') or {}).get('blood_budget_levelup_rejects', 0)
            for r in results for row in r.ledger),
        # 血预算停手·搜索型刷新停付拒付总次数(决策层门;设计件 12
        # §2.3-P1-c/§3.2/ADR-0451——语义生效面披露:0=停手面全批未触发)
        'blood_budget_refresh_rejects': sum(
            (row.get('sim') or {}).get('blood_budget_refresh_rejects', 0)
            for r in results for row in r.ledger),
        # 满级拒付按 plane 分解(口径见 _cap_rejects_by_plane);总量键
        # 保留=旧消费者(测试锁/判读脚本)兼容,两者和恒等。
        'level_cap_rejects_by_plane': _cap_rejects_by_plane(results),
        # ADR-0294 件2:supply 带钻选中总数(占位实体披露;带钻
        # 是词缀元数据不进 owned 池,此计数是它唯一的 sim 痕迹)
        'phantom_supply_picks': sum(
            r.phantom_supply_picks for r in results),
        # `w213_sim_supply/`/ADR-0394:P1 出口 key_equips 命中率(有 key 需求局
        # 的均值;两步语义修复后应显著高于旧「恒 idx0」形态的基线)
        'p1_key_hit_rate': (round(statistics.mean(
            [r.p1_key_hit_hits / r.p1_key_hit_total
             for r in results if r.p1_key_hit_total > 0]), 3)
            if any(r.p1_key_hit_total > 0 for r in results) else None),
        'p1_key_hit_runs': sum(
            1 for r in results if r.p1_key_hit_total > 0),
        'pool_floor_hits': sum(r.pool_floor_hits for r in results),
        # ADR-0287(批㉘ F1):全批残留可上件总数(买后部署语义下
        # 应 0;>0 = 部署时序回归/围栏漏上,检查项扫出)
        'deploy_lag_units': sum(
            (row.get('sim') or {}).get('deploy_lag_units', 0)
            for r in results for row in r.ledger),
        # 动作 v2(契约包 C1,步2):显式动作拒绝/围栏跳过全批披露
        # (真策略不发显式动作 → 双 0;演进引擎 C3 接入后作决策质量信号)
        'explicit_action_rejects': sum(
            r.explicit_action_rejects for r in results),
        'fence_skips': sum(r.fence_skips for r in results),
    }
    if ledger is not False:
        out = (Path(ledger) if isinstance(ledger, Path)
               else _default_sim_runs_dir(report['pool_fingerprint'], n,
                                          seed_base))
        report['ledger_dir'] = str(write_batch_ledger(
            results, out, pool_fp=report['pool_fingerprint']))
    if checks:

        from sr_od.application.currency_war.sim.checks.pool import (
            check_battle_rung_pool_bucket_lock,
            check_delta_pool_bucket_coverage,
            check_delta_pool_bucket_min_n,
            check_depth_cliff_monotonicity,
            check_reward_delta_pool_bucket_lock,
        )
        from sr_od.application.currency_war.sim.checks.runner import (
            run_checks_on_ledgers,
        )
        rep_checks = run_checks_on_ledgers(
            [v.ledger for v in views])
        # ADR-0268:池级检查(桶饥饿/深崖单调)——批③ F1 的常态
        # 化防线;fallback 空池无违规属预期(池语义检查不辖旧模型)
        # ADR-0362:池级检查消费 plane=1 视图(判据全 P1 语料口径,
        # plane≥2 桶贫困走 META ``p2:`` 前缀披露,不进判据)
        _pm, _, _ = resolve_pool(pool)
        _pm = plane_view(_pm)
        rep_checks['delta_pool_bucket_min_n'] = \
            check_delta_pool_bucket_min_n(_pm)
        rep_checks['depth_cliff_monotonicity'] = \
            check_depth_cliff_monotonicity(_pm)
        # ADR-0279(批⑬):battle rung 分桶锁(真值表/边界声明/
        # 池域覆盖);fallback 空池不辖
        rep_checks['battle_rung_pool_bucket_lock'] = \
            check_battle_rung_pool_bucket_lock(_pm)
        # ADR-0306 件5:桶覆盖披露(n≥10 或 META bucket_poverty 显式
        # 披露)——snapshot 池带 META 披露;auto/fallback 无披露载体,
        # 贫困桶计违规(可见性优先)
        _meta = None
        if pool == 'snapshot':
            from sr_od.application.currency_war.data.cw_delta_pool_data import (
                META as _META_SNAP,
            )
            _meta = _META_SNAP
        rep_checks['delta_pool_bucket_coverage'] = \
            check_delta_pool_bucket_coverage(_pm, meta=_meta)
        # ADR-0292(批㉗ F3/F4):reward/supply Δ 分布入池 + 均值对拍
        # 语料真值(含跨 run 配对伪影哨兵)
        rep_checks['reward_delta_pool_bucket_lock'] = \
            check_reward_delta_pool_bucket_lock(_pm)
        # 迁移审计 w109(git 历史)(ADR-0344):池新鲜度——snapshot/auto 池与本机生产
        # replay 落后 ≥2 局 = 再生管线断(池停 12h 零报警事故的
        # 常设防线);fallback 无池语义不辖;无本机 replay(CI)跳过。
        if pool in ('snapshot', 'auto'):

            from sr_od.application.currency_war.sim.checks.pool import (
                check_pool_freshness,
            )
            rep_checks['pool_freshness'] = check_pool_freshness()
        # ADR-0272:池构造无费用截断(单局已硬断言;批级披露)

        from sr_od.application.currency_war.sim.checks.ledger import (
            check_sim_pool_no_cost_truncation as _chk_pool,
        )
        rep_checks['sim_pool_no_cost_truncation'] = \
            _chk_pool(_Pool(random.Random(0)).copies)
        # 批⑩/批⑪ 检查项(ADR-0276/0277):批级聚合检查——boss 胜率
        # 校准/成型-hp 耦合哨兵/升级 binding/末段刷新闭合/末金校准/
        # 锚登记制;吃全批账本(跨局聚合,不进 _BATCH_CHECKS 的逐局循环)
        # ADR-0362:辖 P1 段账本(views;planes=1 时 ≡ 全量零漂移)

        from sr_od.application.currency_war.sim.checks.calib import (
            check_anchor_registry_n300,
            check_sim_endgold_calib,
        )
        from sr_od.application.currency_war.sim.checks.pool import (
            check_boss_win_calibration,
            check_formation_hp_coupling_sentinel,
            check_levelup_binding,
            check_r5plus_refresh_closure,
        )
        _ledgers = [v.ledger for v in views]
        rep_checks['boss_win_calibration'] = \
            check_boss_win_calibration(_ledgers)
        rep_checks['formation_hp_coupling_sentinel'] = \
            check_formation_hp_coupling_sentinel(_ledgers)
        rep_checks['levelup_binding_check'] = check_levelup_binding(_ledgers)
        rep_checks['r5plus_refresh_closure'] = \
            check_r5plus_refresh_closure(_ledgers)
        rep_checks['sim_endgold_calib'] = check_sim_endgold_calib(_ledgers)
        # `w493_income_calib/`(ADR-0447):金分布/费用曲线对拍进标准报告——金均值越出
        # 实机带软告警(校准总闸漂移),费用曲线纯披露(等级轨迹差已知根)

        from sr_od.application.currency_war.sim.checks.calib import (
            check_gold_dist_calib,
            check_shop_cost_curve,
        )
        rep_checks['gold_dist_calib'] = check_gold_dist_calib(_ledgers)
        rep_checks['shop_cost_curve'] = check_shop_cost_curve(_ledgers)
        rep_checks['anchor_registry_n300'] = \
            check_anchor_registry_n300(report)
        # ADR-0294 件3(ADR-0289 接线欠账):批级聚合入口并入——
        # 清偿批的批级披露/哨兵/条件型检查一次跑全(逐局锁已由
        # run_checks_on_ledgers 自动扫;worker X 合流后本欠账清偿)

        from sr_od.application.currency_war.sim.checks.runner import (
            run_batch_level_checks,
        )
        # ADR-0629:second_engine_deadline 是「局终」语义检查,经
        # full_ledgers 吃 results 原账本(P1+P2 全行)——_ledgers 的
        # P1 段截断口径会把 P2 内形成的二引擎记成 never(归因
        # 「never 21 超带」假警报根因);planes=1 批两者恒同零漂移。
        # 其余批级检查判据轮域 P1 段锚定,维持 _ledgers 辖域(ADR-0362)。
        rep_checks.update(run_batch_level_checks(
            _ledgers, report=report, pool_map=_pm,
            full_ledgers=[r.ledger for r in results]))
        # ADR-0362(`w157_p2/`):P2 段检查器最小集——金轨迹非负 + 段形状
        # (辖 planes>=2 批次的 P2 段行;P1 批无 plane=2 行恒绿)

        from sr_od.application.currency_war.sim.checks.calib import (
            check_p2_gold_nonneg,
            check_p2_segment_shape,
        )
        _ledgers_p2 = [r.ledger for r in results]
        rep_checks['p2_gold_nonneg'] = check_p2_gold_nonneg(_ledgers_p2)
        rep_checks['p2_segment_shape'] = check_p2_segment_shape(_ledgers_p2)
        # `w193_p2sim/`/ADR-0377:P2 战斗存活层检查器(掉血带覆盖锚 + 胜率带锚;
        # 辖 calibrated 批——uncalibrated 批恒绿跳过,legacy 档不辖)

        from sr_od.application.currency_war.sim.checks.calib import (
            check_p2_loss_band_anchor,
            check_p2_win_rate_band,
        )
        rep_checks['p2_loss_band_anchor'] = check_p2_loss_band_anchor(
            _ledgers_p2, report=report)
        rep_checks['p2_win_rate_band'] = check_p2_win_rate_band(
            _ledgers_p2, report=report)
        # 审查#6:报告自带 seed_base/n——games 索引 → seed =
        # seed_base+idx,跨日志传阅时索引可独立解读
        for v in rep_checks.values():
            v['seed_base'] = seed_base
        report['checks_violations'] = rep_checks
    # 迁移审计 w278(git 历史) sim 段级短跑批:段级检查表(默认内嵌,只增报不改行为
    # ——纯账本消费零 rng,headline/checks_violations 不受影响;
    # 辖域独立于 checks 开关;max_rounds=None 时窗口=整局,输出与
    # 整局语义一致)

    from sr_od.application.currency_war.sim.checks.segments import run_segment_checks
    _win = max_rounds if (max_rounds is not None and max_rounds > 0) \
        else None
    report['max_rounds'] = _win
    _seg_ledgers = [
        ([row for row in v.ledger
          if row.get('round_num', 10 ** 9) <= _win]
         if _win is not None else list(v.ledger))
        for v in views]
    report['segment_checks'] = run_segment_checks(
        _seg_ledgers, seed_base=seed_base)
    return report



def simulate_p1_ab(n: int = 300, *, pool: str | Path = 'snapshot',
                   seed_base: int = 0) -> dict:
    """A/B 对照报告(同 seed 配对双臂 + 分辨率底;ADR-0285 件4)。

    批㉒ F4 实测:单流 RNG 共享只消掉约 1/3 方差(耦合比 0.675,
    n=300 底 ±1.93hp)——**|Δavg_hp| < 95% 底的差值在噪声带内,
    不得叙述为方向性结论**(报告带 ``noise_band`` 标注;底按本批
    配对差 sd 现算,勿写死 1.93)。默认 A=刷新开/B=刷新关,同
    seed 配对。
    """

    from sr_od.application.currency_war.sim.checks.calib import (
        check_ab_resolution_floor,
    )
    res_a = [simulate_p1(seed_base + i, use_refresh=True, pool=pool)
             for i in range(n)]
    res_b = [simulate_p1(seed_base + i, use_refresh=False, pool=pool)
             for i in range(n)]
    # 双臂 headline(直接从 results 聚合)
    import statistics
    hps_a = [r.final_hp for r in res_a]
    hps_b = [r.final_hp for r in res_b]
    return {
        'n': n, 'pool_fingerprint': res_a[0].pool_fingerprint,
        'avg_hp_a': round(statistics.mean(hps_a), 2),
        'avg_hp_b': round(statistics.mean(hps_b), 2),
        'hp_ge_60_a': sum(1 for h in hps_a if h >= 60) / n,
        'hp_ge_60_b': sum(1 for h in hps_b if h >= 60) / n,
        'ab_resolution_floor': check_ab_resolution_floor(hps_a, hps_b),
    }



def _first_ledger_diff(ledger_a: list[dict],
                       ledger_b: list[dict]) -> dict:
    """两账本流首个差异行描述(零漂移门定位锚;无差异返回 {})。

    逐行扫到第一处不等行,报行号/轮次/该行内取值不同的键集;行数不等
    时报长度差(短的前缀相等 = 差异在追加/缺失行)。只报定位信息不报
    全量值——hp 类数值会随环境重拟合漂移,锁的是「同环境同输入下逐位
    相等」这个事实本身,不是任何具体数字。
    """
    if len(ledger_a) != len(ledger_b):
        # 前缀仍可能有行内差异,先扫公共前缀
        common = min(len(ledger_a), len(ledger_b))
    else:
        common = len(ledger_a)
    for idx in range(common):
        row_a, row_b = ledger_a[idx], ledger_b[idx]
        if row_a == row_b:
            continue
        changed = sorted(k for k in set(row_a) | set(row_b)
                         if row_a.get(k) != row_b.get(k))
        return {'row_idx': idx,
                'round_num': row_a.get('round_num'),
                'changed_keys': changed}
    if len(ledger_a) != len(ledger_b):
        return {'len_a': len(ledger_a), 'len_b': len(ledger_b),
                'note': '公共前缀逐位相等,差异在行数'}
    return {}


def simulate_core_ab(old_strategy_factory=None,
                     new_strategy_factory=None,
                     n: int = 100, *,
                     pool: str | Path = 'snapshot',
                     seed_base: int = 0, planes: int = 1,
                     use_refresh: bool = True,
                     invest: SimInvestProfile | bool = False,
                     invest_arm: str = 'sink',
                     p2_combat: P2CombatCalib | None = None,
                     synthesis_chain: bool = False,
                     equip_wear_effect: float = 0.0) -> dict:
    """策略对象双臂换核 A/B harness(换核对拍基建;纯新增入口)。

    双臂 = 同 seed_base/同池(核对 ``pool_fingerprint``,含 simulate_p1
    内追加的 ``+eqgN`` 位)/同 planes/同 invest/invest_arm/p2_combat/
    synthesis_chain/equip_wear_effect/use_refresh,唯一差异 = 注入的
    策略对象。``*_strategy_factory`` 为无参可调用,返回策略对象;
    **传 None = 该臂走 simulate_p1 默认构造**(不传 strategy 参数,
    即每局在引擎内新造
    ``DecisionV2Strategy(registry=sim_decision_registry())``)。

    设计约束(违反任一 = 对拍不公平,见 sim 决策接口消费面测绘
    §③「公平对拍判据」,`.debug/temp/currency_war/core_swap/
    SIM_CONSUMPTION_MAP.md`):

    - **工厂每局各调一次**(而非整臂复用单例):与 simulate_p1 默认
      分支「每局新构造」对齐——若策略对象持有跨局可变状态,复用
      单例的臂会与默认构造臂产生与「核差异」无关的行为差,污染
      零漂移门。工厂本身必须确定性、不消费局内 rng 流(会话流
      派生是 seed 契约,simulate_p1 内 StrategySession rng 从
      ``f'sim-p1-{seed}'`` 派生)。
    - **两臂注册表视图由调用方保证同源**(建议均从
      ``sim_decision_registry()`` 派生,sim 环境 level_max 语义);
      注入策略无 ``registry`` 属性时引擎观测键回退 sim 视图,行为
      不受影响但观测口径混。
    - 聚合口径:B1(planes=1)= avg_final_hp/hp_ge_60/avg_refreshes;
      B2(planes=2)= p2_hp0_rate 等 p2_* 族,分母 = 进场局
      (``p2_entered``),与 sim 基线 v3(``.debug/temp/currency_war/
      sim_baseline_20260902_v3/SUMMARY.md``)的指标定义一致。
    - 零漂移门(换核 A/B 前置):``old`` 臂 = 现役核工厂、``new``
      臂传 None(直接默认构造),同 seed 配对逐局比 ``ledger``
      逐位相等——先例 = simulate_p1 docstring 的 planes=1 回归门
      (同 seed 同池 diff={})。红了 = 注入路径引入额外 rng 消耗/
      调用时点漂移,先修 harness 再谈 A/B。
    - 噪声带:配对 final_hp 差过 ``check_ab_resolution_floor``
      (n<30 不判);|Δavg| < 95% 底 = 噪声带内,不得叙述方向性
      结论(simulate_p1_ab 同款纪律)。
    """
    import logging
    import statistics

    from sr_od.application.currency_war.sim.checks.calib import (
        check_ab_resolution_floor,
    )
    logging.disable(logging.CRITICAL)   # 批量跑静音(决策日志逐段刷屏)
    try:

        def _run_arm(factory) -> list[SimResult]:
            results: list[SimResult] = []
            for i in range(n):
                if factory is None:
                    results.append(simulate_p1(
                        seed_base + i, pool=pool, planes=planes,
                        use_refresh=use_refresh, invest=invest,
                        invest_arm=invest_arm,
                        p2_combat=p2_combat,
                        synthesis_chain=synthesis_chain,
                        equip_wear_effect=equip_wear_effect))
                else:
                    results.append(simulate_p1(
                        seed_base + i, pool=pool, planes=planes,
                        use_refresh=use_refresh, invest=invest,
                        invest_arm=invest_arm,
                        p2_combat=p2_combat,
                        synthesis_chain=synthesis_chain,
                        equip_wear_effect=equip_wear_effect,
                        strategy=factory()))
            return results

        res_a = _run_arm(old_strategy_factory)
        res_b = _run_arm(new_strategy_factory)
    finally:
        logging.disable(logging.NOTSET)

    fps = ({r.pool_fingerprint for r in res_a}
           | {r.pool_fingerprint for r in res_b})
    if len(fps) != 1:
        raise RuntimeError(
            f'双臂池指纹不一致(对拍不公平): {sorted(fps)}')

    def _headline(results: list[SimResult]) -> dict:
        entered = [r for r in results if r.p2_entered]
        combat_t = sum(r.p2_combat_total for r in entered)
        return {
            'avg_final_hp': round(statistics.mean(
                [r.final_hp for r in results]), 2),
            'hp_ge_60': sum(1 for r in results
                            if r.final_hp >= 60) / len(results),
            'avg_refreshes_p1': round(statistics.mean(
                [r.refreshes for r in results]), 2),
            'p2_entered_rate': len(entered) / len(results),
            'p2_hp0_rate': (sum(1 for r in entered if r.p2_hp0)
                            / len(entered) if entered else None),
            'p2_win_rate': (round(sum(r.p2_combat_wins
                                      for r in entered) / combat_t, 4)
                            if combat_t else None),
            'avg_p2_rounds': (round(statistics.mean(
                [r.p2_rounds for r in entered]), 2) if entered else None),
            'avg_p2_refreshes': (round(statistics.mean(
                [r.p2_refreshes for r in entered]), 2)
                if entered else None),
        }

    # 零漂移门读数:逐局 ledger 逐位比(行序敏感)+ 全字段恒等对计数
    # (自配对校验:同工厂双臂应 identical=n)。
    diff_pairs = 0
    first_diff: dict | None = None
    for ra, rb in zip(res_a, res_b, strict=True):
        if ra.ledger == rb.ledger:
            continue
        diff_pairs += 1
        if first_diff is None:
            first_diff = {'seed': ra.seed}
            first_diff.update(
                _first_ledger_diff(ra.ledger, rb.ledger))
    identical_pairs = sum(1 for ra, rb
                          in zip(res_a, res_b, strict=True) if ra == rb)
    hps_a = [r.final_hp for r in res_a]
    hps_b = [r.final_hp for r in res_b]
    return {
        'n': n, 'planes': planes,
        'pool_fingerprint': res_a[0].pool_fingerprint,
        'headline_a': _headline(res_a),
        'headline_b': _headline(res_b),
        'avg_hp_a': round(statistics.mean(hps_a), 2),
        'avg_hp_b': round(statistics.mean(hps_b), 2),
        # 配对差值 + 噪声带判定(check_ab_resolution_floor:n<30 不判)
        'hp_resolution_floor': check_ab_resolution_floor(hps_a, hps_b),
        # 零漂移门:ledger 逐位相等的配对数(=n 即过门)
        'ledger_diff_pairs': diff_pairs,
        'ledger_first_diff': first_diff,
        # 自配对校验:SimResult 全字段(dataclass eq)恒等的配对数
        'identical_result_pairs': identical_pairs,
    }



# ---- `w227_handoff_gate/`/迁移审计 w238(git 历史) 承接门 A/B 批 harness(simulate_handoff_ab)已随
# ---- ADR-0411 flag 家族清理删除(四臂 off/gate/proj/proj_only 的对照
# ---- 结构建在已删除的 registry 布尔字段上);验证史数字见 ADR-0400/
# ---- 0403/0411。承接门行为的单帧回归锁 = test_cw_w227/w238/w242/w252。


def simulate_p2_sensitivity(n: int = 100, *, pool: str | Path = 'snapshot',
                            seed_base: int = 0, planes: int = 2,
                            betas: tuple[float, ...] = (0.0, 0.04, 0.08, 0.15),
                            gammas: tuple[float, ...] = (0.0, 0.02, 0.05, 0.10),
                            event_gold_arms: tuple[str, ...] = ('p1', 'zero'),
                            form_level_weights: tuple[float, ...] = (0.25,),
                            form_star_weights: tuple[float, ...] = (0.5,),
                            ) -> dict:
    """β/γ/事件金/form 权重敏感性扫描(`w193_p2sim/`/ADR-0377;**裁决口径**)。

    语料不足以点估计 β(迁移审计 w186(git 历史) §3)——P2 修法的 sim 分布结论必须呈报
    本扫描:**修法在某(β,γ)网格点翻正、在带端点(β=0 / β=0.15 /
    γ=0 / γ=0.10 / 事件金双臂)一致翻正才裁「分布级」**;单点翻正
    = 不可裁。headline:存活轮/胜率/hp0 率/金带走量(判读同构)。

    ``form_level_weights``(`w199_anchor/`/迁移审计 w196(git 历史) 发现③):β 扫描只缩放整条
    form(engines + w·(lv−6) 同乘 β),分辨不了 engines:lv 构成比
    ——lv 投资型修法(金流改道升级)的存活收益显影取决于 lv 项
    真实权重,故 w 入网格(端点 0=lv 零贡献 / 高档 0.5/1.0);
    默认 (0.25,) = P2_COMBAT_DEFAULT 单值,行为向后兼容。
    ``form_star_weights``(`w230_star_form/`/ADR-0401,同型):星级投资型修法
    (承接门/`w227_handoff_gate/`)的存活收益显显取决于 star_depth 项真实权重
    (真值分帧只定向不定量)——端点 0(星级零贡献=旧 form 形态)/
    0.25 / 1.0;默认 (0.5,) = 单值。
    """
    import dataclasses
    import logging
    import statistics

    logging.disable(logging.CRITICAL)
    try:
        table = []
        for eg in event_gold_arms:
            for b in betas:
                for g in gammas:
                    for w in form_level_weights:
                        for ws in form_star_weights:
                            calib = dataclasses.replace(
                                P2_COMBAT_DEFAULT, beta=b, gamma=g, event_gold=eg,
                                form_level_weight=w, form_star_weight=ws)
                            rs = [simulate_p1(seed_base + i, pool=pool,
                                              planes=planes, p2_combat=calib)
                                  for i in range(n)]
                            entered = [r for r in rs if r.p2_entered]
                            ct = sum(r.p2_combat_total for r in entered)
                            cw = sum(r.p2_combat_wins for r in entered)
                            carried = [r.p2_gold_carried for r in entered
                                       if r.p2_gold_carried is not None]
                            table.append({
                                'event_gold': eg, 'beta': b, 'gamma': g,
                                'form_level_weight': w, 'form_star_weight': ws,
                                'p2_entered_rate': len(entered) / n,
                                'avg_p2_rounds': round(statistics.mean(
                                    [r.p2_rounds for r in entered]), 2)
                                if entered else None,
                                'p2_win_rate': round(cw / ct, 4) if ct else None,
                                'p2_hp0_rate': (sum(1 for r in entered
                                                    if r.p2_hp0)
                                                / len(entered))
                                if entered else None,
                                'avg_p2_gold_carried': round(statistics.mean(
                                    carried), 2) if carried else None,
                                'avg_final_hp': round(statistics.mean(
                                    [r.final_hp for r in rs]), 2),
                            })
    finally:
        logging.disable(logging.NOTSET)
    return {
        'n': n, 'planes': planes,
        'pool_fingerprint': resolve_pool(pool)[1],
        'grid': table,
    }



# sim 账本落盘根(telemetry/sim/<batch_id>/,2026-09-07 布局裁定;
# 单一源 = kernel/cw_observe 根常量块,与生产 live 流根隔离;
# write_batch_ledger 另有禁写生产 live 目录守卫,双保险)
from sr_od.application.currency_war.kernel.cw_observe import (  # noqa: E402
    SIM_ROOT,
)

SIM_RUNS_DIR: Path = SIM_ROOT

_SIM_RUNS_KEEP: int = 20   # 批次保留数(防无限累积;旧的自动清理)

#: 锚定标记文件(批目录内)。滚动清理跳过含本文件的批——A/B 对照批、
#: 测量基线批等复现链锚点免清理(评估表相位 2a 报告 §6:keep=20 滚动
#: 清理曾把冻结池与 364c773a 对照批一起删掉,A/B 复现链断裂)。
#: 形态依据:批目录名即账本 run_id 前缀与重放地址(改名会断既有消费
#: 端引用,故不用前缀改名);标记随目录自包含、随批生存,无中央清单
#: 的漂移面;人工 `rmtree` 之外的清理路径也只认这一个真相源。
_ANCHOR_FILENAME: str = 'anchored.json'


def anchor_batch(batch_dir: Path, reason: str) -> Path:
    """给 sim 批目录打锚定标记(免滚动清理)。

    :param batch_dir: sim 批目录(telemetry/sim 下的批目录;不校验存在——
        存量补救可对即将生成的目录预置;清理时只看标记文件)
    :param reason: 锚定原因(写入标记,审计可读;如 'A/B 对照批 364c773a')
    """
    import json as _json
    import time as _time

    batch_dir = Path(batch_dir)
    batch_dir.mkdir(parents=True, exist_ok=True)
    marker = batch_dir / _ANCHOR_FILENAME
    marker.write_text(_json.dumps({
        'reason': reason,
        'anchored_at': _time.strftime('%Y-%m-%dT%H:%M:%S'),
    }, ensure_ascii=False), encoding='utf-8')
    return marker


def is_anchored(batch_dir: Path) -> bool:
    """批目录是否带锚定标记(清理跳过判据的单一源)。"""
    return (Path(batch_dir) / _ANCHOR_FILENAME).is_file()

_NT_TO_PROD = {'battle': '普通战斗', 'encounter': '遭遇',
               'reward': '奖励', 'boss': '首领', 'supply': '补给'}



def _default_sim_runs_dir(pool_fp: str, n: int, seed_base: int) -> Path:
    import time
    stamp = time.strftime('%Y%m%d_%H%M%S') + f'{time.monotonic_ns() % 1000:03d}'
    return SIM_RUNS_DIR / f'sim_{stamp}_n{n}_s{seed_base}_{pool_fp[:8]}'



def _prune_sim_runs() -> None:
    """sim 批滚动清理(telemetry/sim):窗口外的非锚定批删除,锚定批跳过。

    只清 sim_ 前缀批(用户显式传的非 sim 目录不动,审查#5);锚定批
    (带 anchored.json:A/B 对照批/测量基线批等复现链锚点)免清理。
    根 = telemetry/sim(2026-09-07 布局裁定;历史批已由
    tools/cw/migrate_telemetry_tree.py 一次性迁入)。
    """
    if not SIM_RUNS_DIR.exists():
        return
    batches = sorted(p for p in SIM_RUNS_DIR.iterdir()
                     if p.is_dir() and p.name.startswith('sim_'))
    for old in [b for b in batches[:-_SIM_RUNS_KEEP] if not is_anchored(b)]:
        import shutil
        shutil.rmtree(old, ignore_errors=True)


def write_batch_ledger(results: list[SimResult], out_dir: Path, *,
                       pool_fp: str = '') -> Path:
    """两流账本落盘:``<out_dir>/{decisions,outcomes}.jsonl``。

    - decisions 每轮一行(SimResult.ledger;run_id=batch 目录名);
    - outcomes 每轮一行(OutcomeRecord 同构:生产 node_type 词表
      + hp_after + board_before/bench_count + boss_names 槽位(恒
      None,见行内注);sim 专属键挂 'sim');
    - **守卫:out_dir 不得是生产 live 流根,也不得是退役旧根**(本函数
      以 'w' 截断模式开三流文件名,写错位置 = 把目标处既有同名词整份
      清零——2026-09-07 22:20:52 空批写退役旧根截断历史三流实证,
      对账裁定 = ADR-0586;生成器侧另有源
      目录断言,双保险)。
    """
    import json as _json

    from sr_od.application.currency_war.kernel import cw_coarse_battle as _cb
    from sr_od.application.currency_war.kernel.cw_observe import (
        RETIRED_SIM_ROOT,
        RETIRED_STREAMS_ROOT,
    )
    out_dir = Path(out_dir)
    _resolved = out_dir.resolve()
    _forbidden_roots: tuple[Path, ...] = (
        _AUTO_REPLAY_DIR.resolve(),   # 生产 live 流根(自中毒回路)
        RETIRED_STREAMS_ROOT.resolve(),   # 退役旧流根(历史数据封存地)
        RETIRED_SIM_ROOT.resolve(),   # 退役旧 sim 批根(同上)
    )
    for _root in _forbidden_roots:
        if _resolved == _root or _root in _resolved.parents:
            raise RuntimeError(
                f'sim 账本禁写受保护目录: {out_dir}(命中 {_root};'
                f'本函数以截断模式开流文件,写错位置 = 清零既有数据;'
                f'落盘目标只能是 {SIM_RUNS_DIR} 下或显式独立目录)')
    out_dir.mkdir(parents=True, exist_ok=True)
    base_id = out_dir.name
    with (out_dir / 'decisions.jsonl').open('w', encoding='utf-8') as f_d, \
         (out_dir / 'outcomes.jsonl').open('w', encoding='utf-8') as f_o, \
         (out_dir / 'shop_snapshots.jsonl').open('w',
                                                 encoding='utf-8') as f_s:
        for r in results:
            # 每局独立 run_id(带 seed——判读视图按 run 过滤时一局一局
            # 看,且 id 即重放地址:simulate_p1(<seed>) 重放该局)
            run_id = f'{base_id}_s{r.seed}'
            for row in r.ledger:
                row = dict(row)
                row['run_id'] = run_id
                row['schema_version'] = 1
                f_d.write(_json.dumps(row, ensure_ascii=False) + '\n')
                o = {
                    'schema_version': 1, 'ts': row['ts'],
                    'run_id': run_id, 'plane': row['plane'],
                    'round_num': row['round_num'],
                    'node_type': _NT_TO_PROD.get(
                        row['sim']['node'], row['sim']['node']),
                    'comp_tag': row['target_comp'] or '',
                    'hp_after': row['hp'],
                    # ADR-0271:board 真值(deployed 主阵营聚合;
                    # 旧恒空 dict 让 rounds/economy 视图板面恒缺)
                    'board_before': dict(
                        (row['state'] or {}).get('board') or {}),
                    'bench_count':
                        len(row['state']['bench']),
                    # 件②:boss 身份槽位与生产 OutcomeRecord 同键
                    # 同构。sim 未建模简报面 → 恒 None(「未建模」显式
                    # 缺省,区别于旧数据的键缺失,消费端 .get 可辨);
                    # boss 伤害双峰按敌型混合重标定的实采数据源 = 生产
                    # outcomes(w253 起 boss_names 有真值,单一源 =
                    # cw_registry.handoff_boss_e_damage 注)。
                    'boss_names': None,
                    'sim': {'delta': row['sim']['delta'],
                            'depth': row['sim']['depth'],
                            # killed 语义同产线=**胜**(击杀敌方;
                            # settlement_obs _won / cw_loop
                            # hp_after>=prev_hp——审查 major:killed
                            # 极性反转会把败场读成胜场)
                            'killed': row['sim']['delta'] >= 0},
                }
                f_o.write(_json.dumps(o, ensure_ascii=False) + '\n')
                # 第三流:牌面波(生产 shop_snapshots 同 schema——
                # supply 视图零改动可查 sim 批次)。w919(R-A 批1):
                # 行附 rho_obs(ρ 实测单帧分子;生产 rec 路 pair 自
                # session 意向取,sim 无 session 方向态恒 ''——方向
                # join 走同批 decisions 行 sess_p1_pair)。计算失败
                # → None,行照写(观测不炸账本)。
                for w in row['sim'].get('shop_waves') or []:
                    from sr_od.application.currency_war.telemetry.schema import (
                        rho_shop_obs,
                    )
                    try:
                        _rho = rho_shop_obs(w['cards'])
                    except Exception:   # noqa: BLE001  观测 best-effort
                        _rho = None
                    f_s.write(_json.dumps({
                        'schema_version': 1, 'ts': row['ts'],
                        'run_id': run_id, 'plane': row['plane'],
                        'round_num': row['round_num'],
                        'event': w['event'], 'gold': w['gold'],
                        'shop': w['cards'],
                        'rho_obs': _rho,
                    }, ensure_ascii=False) + '\n')
    # manifest(审查#5:写半失败无标记 → 残批被当有效批;判读端
    # 可校验 manifest 在+行数匹配才认批)。ledger_semantics 标记
    # 账本字段语义版本(审查#2:core_count 三人组→按线路由变更
    # 无标记,新旧批次混存=③ 聚合静默混桶)。
    (out_dir / 'manifest.json').write_text(_json.dumps({
        'n': len(results),
        'seeds': [r.seed for r in results],
        'pool_fingerprint': pool_fp or (
            results[0].pool_fingerprint if results else ''),
        'rounds_rows': sum(len(r.ledger) for r in results),
        'ledger_semantics': 'core_routed',
        # 粗模型校准结构版本(局终指纹核对锚):跨批次对比先核本值,
        # 防「结构改了、披露没跟上」的混池污染(cw_coarse_battle 单一源)
        'coarse_calib_version': (
            _cb.COARSE_CALIB_VERSION if results else None),
        # 收入口径版本(ADR-0439;独立于粗模型战斗引擎版本——收入口径
        # 在 cw_economy/cw_sim 收入段,另一子系统,版本号不共占)
        'economy_calib_version': (
            ECONOMY_CALIB_VERSION if results else None),
    }, ensure_ascii=False), encoding='utf-8')
    # 保留清理(滚动删除,语义见 _prune_sim_runs)
    _prune_sim_runs()
    return out_dir



def _cli_main() -> None:
    """④ seed 重放入口(可复现 bug 报告:seed+池指纹 → 逐轮决策)。

    用法:
        uv run python -m sr_od.application.currency_war.sim.runner \\
            replay --seed 42 --pool snapshot
    checks 报的 games 索引 → seed = seed_base + idx,同参数重放。
    池指纹不符(历史 bug 对新池)→ 提示换池版本,不硬跑(⓪ 纪律)。
    """
    import argparse
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(prog='cw_sim')
    ap.add_argument('cmd', choices=['replay', 'batch'])
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--n', type=int, default=100)
    ap.add_argument('--planes', type=int, default=1,
                    help='1=P1 段;2=追加 P2 段(ADR-0362)')
    ap.add_argument('--seed-base', type=int, default=0)
    ap.add_argument('--pool', default='snapshot',
                    help='auto/snapshot/fallback/JSON 路径')
    ap.add_argument('--expect-fingerprint', default='',
                    help='期望池指纹(不符即拒——历史报告对旧池重放)')
    ap.add_argument('--max-rounds', type=int, default=None,
                    help='段级窗口 K(前 K 轮决策流进段级检查表;'
                         '不传=整局,既有行为不变)')
    args = ap.parse_args()
    pool_arg = args.pool
    if args.cmd == 'replay':
        r = simulate_p1(args.seed, pool=pool_arg, planes=args.planes)
        if args.expect_fingerprint and \
                r.pool_fingerprint != args.expect_fingerprint:
            print(f'池指纹不符: 期望 {args.expect_fingerprint} '
                  f'实得 {r.pool_fingerprint}(换池版本或 Path 快照)')
            return
        print(f"=== seed {args.seed} | 池 {r.pool_source} "
              f"{r.pool_fingerprint[:8]} | 末HP {r.final_hp} "
              f"| dir r{r.dir_round} ===")
        for row in r.ledger:
            s = row['sim']
            buys = [f"{(a.get('card') or {}).get('name')}"
                    f"({a.get('reason', '?')})"
                    for a in row['actions']
                    if a.get('__type__') == 'BuyCard']
            print(f"  p{row['plane']}r{row['round_num']} {s['node']:<9} "
                  f"Δ{s['delta']:+3d} hp={row['hp']:>3} "
                  f"g={row['gold']:>3} 深{s['depth']:>2} "
                  f"花={sum(s['spend']['buys'].values())} "
                  f"tgt={row['target_comp'] or '-'} "
                  f"买={','.join(buys) or '-'}")
    else:
        rep = simulate_p1_batch(args.n, seed_base=args.seed_base,
                                pool=pool_arg, planes=args.planes,
                                max_rounds=args.max_rounds)
        for k in ('n', 'hp_ge_60', 'battle_losses_le_2', 'avg_final_hp',
                  'p2_entered_rate', 'avg_p2_rounds', 'p2_win_rate',
                  'p2_hp0_rate', 'avg_p2_refreshes',
                  'pool_fingerprint'):
            print(f'{k}: {rep[k]}')
        print('checks:', rep['checks_violations'])
        # 迁移审计 w278(git 历史) 段级检查表摘要(事件全量在 rep['segment_checks'])
        print('segment:', {
            k: v['count'] for k, v in
            rep.get('segment_checks', {}).items() if k != '_summary'},
            '| max_rounds:', rep.get('max_rounds'))





if __name__ == '__main__':
    _cli_main()
