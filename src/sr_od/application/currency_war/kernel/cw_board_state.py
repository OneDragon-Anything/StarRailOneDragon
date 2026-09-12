"""货币战争 旧路径转发壳(cw_game_state 改居过渡壳;T-7 W8 候裁7)。

「cw_board_state」旧模块路径与「BoardState」旧类名(别名随壳导出)仅
服务并行在飞批文件,其 import 面落库后由收尾段 sweep 改指 cw_game_state
并删除本壳与别名。禁新增消费。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_game_state import (  # noqa: F401
    BATTLE_WAIT_CONTEXT,  # noqa: F401
    BENCH_CAPACITY_DEFAULT,  # noqa: F401
    BS_SCHEMA_VERSION,  # noqa: F401
    BenchSlot,  # noqa: F401
    BenchView,  # noqa: F401
    CHANNEL_FAMILIES,  # noqa: F401
    COST_SOURCE_BADGE,  # noqa: F401
    COST_SOURCE_REGISTRY,  # noqa: F401
    ChainQuery,  # noqa: F401
    ChannelSig,  # noqa: F401
    DEFAULT_BS_SCHEMA,  # noqa: F401
    EncounterPayload,  # noqa: F401
    FINAL_ABNORMAL,  # noqa: F401
    FINAL_LOSS,  # noqa: F401
    FINAL_STOPPED,  # noqa: F401
    FINAL_WIN,  # noqa: F401
    Field,  # noqa: F401
    FieldSource,  # noqa: F401
    FrameObsLevel,  # noqa: F401
    LOGIC_MODES,  # noqa: F401
    MATCH_FINAL_FIELD,  # noqa: F401
    MATCH_FINAL_TYPES,  # noqa: F401
    MatchFinal,  # noqa: F401
    NodeKey,  # noqa: F401
    OBS_EVENT_EVENTS,  # noqa: F401
    OBS_MODES,  # noqa: F401
    PREP_PROJECTION_DOMAINS,  # noqa: F401
    RECEIPTS_WINDOW_CAP,  # noqa: F401
    REGISTERED_ACTORS,  # noqa: F401
    SCREEN_BOSS_BRIEFING,  # noqa: F401
    SCREEN_CONTEXT_GUARD_PREV,  # noqa: F401
    SCREEN_CONTEXT_POPUP_FAMILY,  # noqa: F401
    SCREEN_NODE_TYPE_DIRECT,  # noqa: F401
    SCREEN_PLANE_TRANSITION,  # noqa: F401
    SCREEN_PREP_FRAME,  # noqa: F401
    SHOP_PROJECTION_DOMAINS,  # noqa: F401
    SIM_SYNTHESIZED,  # noqa: F401
    Settlement,  # noqa: F401
    ShopActionExecuted,  # noqa: F401
    ShopCard,  # noqa: F401
    ShopPayload,  # noqa: F401
    SphereSight,  # noqa: F401
    SupplyPayload,  # noqa: F401
    Unit,  # noqa: F401
    actor_registered,  # noqa: F401
    apply_effect_burst_grant,  # noqa: F401
    apply_prep_action_logic,  # noqa: F401
    apply_settlement_cover,  # noqa: F401
    apply_shop_action_logic,  # noqa: F401
    apply_shop_merge_leg,  # noqa: F401
    archive_snapshot,  # noqa: F401
    back_capacity_of,  # noqa: F401
    back_count_of,  # noqa: F401
    bench_free_slots,  # noqa: F401
    bench_is_full,  # noqa: F401
    bench_slots_of,  # noqa: F401
    bench_slots_to_legacy,  # noqa: F401
    bench_view_from_obs,  # noqa: F401
    bench_view_of_slots,  # noqa: F401
    board_next_tier_of,  # noqa: F401
    board_state_bridge,  # noqa: F401
    board_state_from_ctx,  # noqa: F401
    board_state_of,  # noqa: F401
    chain_node_type,  # noqa: F401
    consume_defect_sink,  # noqa: F401
    cost_source_group,  # noqa: F401
    current_run_id_safe,  # noqa: F401
    deployed_count_of,  # noqa: F401
    deployed_rows_from_obs,  # noqa: F401
    deployed_slots_of,  # noqa: F401
    detect_merge_upgrade,  # noqa: F401
    effective_node_ord,  # noqa: F401
    feed_sim_truth,  # noqa: F401
    front_count_of,  # noqa: F401
    GameState,  # noqa: F401
    gold_of,  # noqa: F401
    grant_effect_node_refresh_balance,  # noqa: F401
    level_of,  # noqa: F401
    max_units_of,  # noqa: F401
    mutate_bench_deployed_local,  # noqa: F401
    node_kind_of,  # noqa: F401
    node_ordinal_of,  # noqa: F401
    note_action_receipt,  # noqa: F401
    note_board_state_heartbeat,  # noqa: F401
    plane_of,  # noqa: F401
    project_effect_capacity,  # noqa: F401
    record_refresh_execution,  # noqa: F401
    register_sig_actors,  # noqa: F401
    restore_state_snapshot,  # noqa: F401
    round_num_of,  # noqa: F401
    set_defect_sink,  # noqa: F401
    set_match_final_listener,  # noqa: F401
    set_run_id_provider,  # noqa: F401
    set_state_journal_sink,  # noqa: F401
    shop_card_to_container,  # noqa: F401
    shop_cards_to_legacy,  # noqa: F401
    slot_occupies,  # noqa: F401
    synthesize_from_game_state,  # noqa: F401
    unit_rows_to_deployed,  # noqa: F401
    write_match_final,  # noqa: F401
)

# 旧类名别名(过渡期;生命周期同本壳,见模块 docstring)。
BoardState = GameState  # noqa: F401
