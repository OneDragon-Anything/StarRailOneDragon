"""检查聚合入口 run_checks_on_ledgers/run_batch_level_checks 与 _BATCH_CHECKS 注册表(分包期6 拆分)。"""

from __future__ import annotations

from sr_od.application.currency_war.sim.checks.calib import (
    check_p2_precache_gate_closure,
)
from sr_od.application.currency_war.sim.checks.corpus import (
    check_anchor_lowchannel_registry,
    check_anchor_seed_portability_n600,
)
from sr_od.application.currency_war.sim.checks.ledger import (
    check_bench_capacity_invariant,
    check_bench_full_deadlock_probe,
    check_buys_at_full_bench,
    check_coldstart_seed_squander,
    check_comp_tx_atomicity,
    check_core_ruling_seat_violation,
    check_degrade_recover_mutex,
    check_deploy_after_buy_semantics,
    check_deploy_fills_cap,
    check_deployed_schema_filter,
    check_directed_refresh_game_cap,
    check_equip_supply_wear_closure,
    check_equip_value_strategy_key_coverage,
    check_equip_value_table_roster_coherence,
    check_equip_worn_in_battle,
    check_gold_nonneg_invariant,
    check_hp1_dead_end_candidate,
    check_hp_ge60_frame_lock,
    check_hp_upper_bound_truth,
    check_ledger_consistency,
    check_ledger_deploy_lag_disclosure,
    check_levelup_budget_gate,
    check_levelup_flat4_ledger_lock,
    check_levelup_interest_engine_gate,
    check_no_same_round_buy_sell,
    check_observation_keys_live,
    check_oscillation_xp_cap,
    check_overflow_gold_zero_buy_streak,
    check_phantom_equip_no_wear,
    check_phantom_rebuy_disclosure,
    check_refresh_roll_cap_frame,
    check_shop_slot_consumption,
    check_skip_fence_pairing,
    check_streak_propagation_live,
    check_supply_pool_roster_purity,
)
from sr_od.application.currency_war.sim.checks.pool import check_engine_seed_not_resold
from sr_od.application.currency_war.sim.checks.runtime import (
    check_boss_round_real_actions,
    check_boss_win_curve_sample_gate,
    check_briefing_pipeline_liveness,
    check_calibration_dead_knob_disclosure,
    check_deploy_cap_reader_noise,
    check_encounter_rung_sample_budget,
    check_endgold_residue_channel_probe,
    check_formation_gradient_sentinel,
    check_hoard_gold_no_engine,
    check_hp_readable_disclosure,
    check_late_board_short_idle,
    check_late_deploy_full,
    check_mc_faction_calib,
    check_no_streak_buy_freeze,
    check_pool_hit_rate_disclosure,
    check_refresh_cost_channel,
    check_reward_heal_fat_tail,
    check_second_engine_deadline,
    check_shop_cost_conformance,
    check_shop_distinct_names_invariant,
    check_streak_break_interest_fires,
    check_streak_combat_only_income,
    check_supply_agent_semantics,
)

_BATCH_CHECKS = {
    'ledger_consistency': check_ledger_consistency,
    'coldstart_direction': check_coldstart_seed_squander,
    'deploy_fills_cap': check_deploy_fills_cap,
    'equip_worn_in_battle': check_equip_worn_in_battle,
    'levelup_interest_engine_gate': check_levelup_interest_engine_gate,
    # P71-b 溢余段预算闸(ADR-0560):m3_batch 升级批穿线 = 绕闸违规
    'levelup_budget_gate': check_levelup_budget_gate,
    'no_same_round_buy_sell': check_no_same_round_buy_sell,
    'bench_full_deadlock_probe': check_bench_full_deadlock_probe,
    'shop_slot_consumption': check_shop_slot_consumption,
    'phantom_rebuy_disclosure': check_phantom_rebuy_disclosure,
    'deploy_after_buy_semantics': check_deploy_after_buy_semantics,
    'ledger_deploy_lag_disclosure': check_ledger_deploy_lag_disclosure,
    'hp_upper_bound_truth': check_hp_upper_bound_truth,
    # 迁移审计 w120(git 历史) P9:HP=1 死局/早停候选标记(披露型,violations 恒 0)
    'hp1_dead_end_candidate': check_hp1_dead_end_candidate,
    # --- ADR-0289 检查项清偿批(逐局违规锁) ---
    'gold_nonneg': check_gold_nonneg_invariant,
    'bench_capacity': check_bench_capacity_invariant,
    'deployed_schema_filter': check_deployed_schema_filter,
    'engine_seed_not_resold': check_engine_seed_not_resold,
    'overflow_gold_zero_buy_streak': check_overflow_gold_zero_buy_streak,
    # 观测态补齐哨兵(观测态补齐批):P1 带符号 streak 传播断线=死输入
    'streak_propagation_live': check_streak_propagation_live,
    # 观测硬依赖键面哨兵(W793 后继批):bench_full_flag/board_next_tier/
    # alloc_frame 三键写端断线=判读死输入(锁#10/#11 与 Δp_tier 标定)
    'observation_keys_live': check_observation_keys_live,
    'buys_at_full_bench': check_buys_at_full_bench,
    'oscillation_xp_cap': check_oscillation_xp_cap,
    'levelup_flat4_lock': check_levelup_flat4_ledger_lock,
    'phantom_equip_no_wear': check_phantom_equip_no_wear,
    'degrade_recover_mutex': check_degrade_recover_mutex,
    'hp_ge60_frame_lock': check_hp_ge60_frame_lock,
    'supply_pool_roster_purity': check_supply_pool_roster_purity,
    'equip_value_table_roster_coherence':
        check_equip_value_table_roster_coherence,
    'equip_supply_wear_closure': check_equip_supply_wear_closure,
    'equip_value_strategy_key_coverage':
        check_equip_value_strategy_key_coverage,
    # --- 动作 v2(契约包 C1,步2):显式动作一致性/围栏配对 ---
    'comp_tx_atomicity': check_comp_tx_atomicity,
    'skip_fence_pairing': check_skip_fence_pairing,
    # --- T-115 恒买腾席判红检测器(写端位出口键完备性;ADR-0580)---
    # seen 帧零出口键 = 席满静默违复活(计数式轮级回退红则,残注①)
    'core_ruling_seat_violation': check_core_ruling_seat_violation,
    # --- 刷新预算帽族(刷帽检查;两口径各自的常量单一源见各 docstring) ---
    'directed_refresh_game_cap_lock': check_directed_refresh_game_cap,
}



def run_checks_on_ledgers(ledgers: list[list[dict]]) -> dict[str, dict]:
    """批量执行 generic 检查 → {检查名: {violations: n, games: [idx...]}}。

    违规局数与前 5 个局索引(供 seed 重放定位:simulate_p1(
    seed_base+idx) 重放该局)。
    """
    report: dict[str, dict] = {}
    for name, fn in _BATCH_CHECKS.items():
        games: list[int] = []
        for idx, rows in enumerate(ledgers):
            if fn(rows):
                games.append(idx)
        report[name] = {
            'violations': len(games),
            'games': games[:5],
        }
    return report



# --- 清偿批:批级聚合入口(cw_sim 接线随 worker X 合流) ---------

def run_batch_level_checks(ledgers: list[list[dict]],
                           report: dict | None = None,
                           pool_map: dict | None = None) -> dict:
    """清偿批批级聚合入口:披露/哨兵/条件型检查一次跑全。

    逐局违规锁已在 _BATCH_CHECKS(run_checks_on_ledgers 自动扫);
    本入口辖批级聚合(吃全批账本)、池级条件(encounter 预算)、
    报告级披露(死旋钮/锚登记)。simulate_p1_batch 的接线归
    cw_sim.py(worker X 合流后;冲突隔离,本批不碰 cw_sim)。
    """
    from sr_od.application.currency_war.sim.checks.launch import (
        check_sim_launch_short_circuit as _launch_sentinel,
    )
    from sr_od.application.currency_war.sim.checks.ledger import (
        core_ruling_seat_bucket_disclosure,
    )
    out: dict[str, dict] = {
        'late_deploy_full': check_late_deploy_full(ledgers),
        # F5 部署供给观测(W956;披露型——采纳层修复后升格 _BATCH_CHECKS 断言门)
        'late_board_short_idle': check_late_board_short_idle(ledgers),
        'no_streak_buy_freeze': check_no_streak_buy_freeze(ledgers),
        'hoard_gold_no_engine': check_hoard_gold_no_engine(ledgers),
        'second_engine_deadline': check_second_engine_deadline(ledgers),
        'endgold_residue_channel_probe':
            check_endgold_residue_channel_probe(ledgers),
        'p2_precache_gate_closure':
            check_p2_precache_gate_closure(ledgers),
        'formation_gradient_sentinel':
            check_formation_gradient_sentinel(ledgers),
        'streak_break_interest_fires':
            check_streak_break_interest_fires(ledgers),
        'refresh_roll_cap_frame': check_refresh_roll_cap_frame(ledgers),
        'mc_faction_calib': check_mc_faction_calib(ledgers),
        'streak_combat_only_income':
            check_streak_combat_only_income(ledgers),
        'shop_distinct_names_invariant':
            check_shop_distinct_names_invariant(ledgers),
        'supply_agent_semantics': check_supply_agent_semantics(ledgers),
        'refresh_cost_channel': check_refresh_cost_channel(ledgers),
        'hp_readable_disclosure': check_hp_readable_disclosure(ledgers),
        'briefing_pipeline_liveness':
            check_briefing_pipeline_liveness(ledgers),
        'deploy_cap_reader_noise':
            check_deploy_cap_reader_noise(ledgers),
        'calibration_dead_knob_disclosure':
            check_calibration_dead_knob_disclosure(report),
        'reward_heal_fat_tail': check_reward_heal_fat_tail(ledgers),
        'boss_win_curve_sample_gate':
            check_boss_win_curve_sample_gate(ledgers),
        'pool_hit_rate_disclosure':
            check_pool_hit_rate_disclosure(ledgers),
        'shop_cost_conformance': check_shop_cost_conformance(ledgers),
        'boss_round_real_actions':
            check_boss_round_real_actions(ledgers),
        # sim 决策下沉两小批②:发射短路行为哨兵(反假阴性;守卫移除即红
        # ——发射帧决策照常/金照花 = 金出口族 A/B 假阴性形态回归)
        'sim_launch_short_circuit':
            _launch_sentinel(ledgers),
        # T-115 恒买腾席支出口键分布披露(数据面;非违规——seen 开火性
        # × buy_hit/seat_swap 转化 × no_fuel/双 unaffordable 桶分布,
        # 方案 v2 §11.2 种子批验收线)
        'core_ruling_seat_buckets':
            core_ruling_seat_bucket_disclosure(ledgers),
        # (v2 四层/press/供给标签六检查项已随 decision_v2 退役链删除——统一迁移批 ② MAP B 类/A9。)
    }
    if pool_map is not None:
        out['encounter_rung_sample_budget'] = \
            check_encounter_rung_sample_budget(pool_map)
    if report is not None:
        out['anchor_seed_portability_n600'] = \
            check_anchor_seed_portability_n600(report)
        out['anchor_lowchannel_registry'] = \
            check_anchor_lowchannel_registry(report)
    return out
