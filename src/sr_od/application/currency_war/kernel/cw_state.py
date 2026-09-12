"""货币战争 旧路径转发壳(cw_vocab 改居过渡壳;T-7 W8 候裁7/9)。

正名后 cw_state 旧路径仅服务并行在飞批文件(其 import 面落库后由
收尾段 sweep 改指 cw_vocab/cw_game_state 并删除本壳)。禁新增消费。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_vocab import (  # noqa: F401
    Action,  # noqa: F401
    BuyCard,  # noqa: F401
    CloseShop,  # noqa: F401
    CompTransaction,  # noqa: F401
    CwWorkFrame,  # noqa: F401
    DeployMove,  # noqa: F401
    FillSpec,  # noqa: F401
    LevelUp,  # noqa: F401
    LevelUpShop,  # noqa: F401
    PickEvent,  # noqa: F401
    RefreshShop,  # noqa: F401
    SELL_BENCH_CONVERT_REASONS,  # noqa: F401
    SellBench,  # noqa: F401
    SellDeployed,  # noqa: F401
    ShopCard,  # noqa: F401
    SwapDeploy,  # noqa: F401
    _apply_comp_transaction,  # noqa: F401
    _bench_char_cost,  # noqa: F401
    _bench_clear_by_identity,  # noqa: F401
    _card_to_bench,  # noqa: F401
    _deployed_clear_by_identity,  # noqa: F401
    _layout_unknown_reset,  # noqa: F401
    _log_action,  # noqa: F401
    _remove_by_identity,  # noqa: F401
    _resolve_comp_transaction,  # noqa: F401
    _tx_state_view,  # noqa: F401
    bench_clear,  # noqa: F401
    deployed_clear,  # noqa: F401
    mutate_bench_deployed,  # noqa: F401
    reset_layout_unknown_state,  # noqa: F401
    simulate,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_exec_state import (  # noqa: F401
    BENCH_CAPACITY,  # noqa: F401
    DEPLOYED_BACK_CAPACITY,  # noqa: F401
    DEPLOYED_CAPACITY,  # noqa: F401
    DEPLOYED_FRONT_CAPACITY,  # noqa: F401
    PlaneNodeLedger,  # noqa: F401
    BenchChar,  # noqa: F401
    _apply_row_to_char,  # noqa: F401
    bench_from_compact,  # noqa: F401
    bench_occupied,  # noqa: F401
    bench_place,  # noqa: F401
    deployed_from_compact,  # noqa: F401
    deployed_occupied,  # noqa: F401
    deployed_place,  # noqa: F401
    deployed_slot_no,  # noqa: F401
    fill_boss_by_position,  # noqa: F401
    get_node_ledger,  # noqa: F401
    iter_deployed_slots,  # noqa: F401
    iter_occupied,  # noqa: F401
    iter_occupied_deployed,  # noqa: F401
    ledger_node_type,  # noqa: F401
    ledger_update_plane,  # noqa: F401
    pad_bench,  # noqa: F401
    pad_deployed,  # noqa: F401
    rebuild_deployed_from_board,  # noqa: F401
    snapshot_copy,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_merge_simulate import (  # noqa: F401
    _apply_full_bench_merge_buy,  # noqa: F401
    _merge_bench,  # noqa: F401
    count_merge_material_blocked,  # noqa: F401
    merge_buy_completes,  # noqa: F401
    merge_buy_k,  # noqa: F401
    merge_material_reject_reason,  # noqa: F401
    merge_material_stale_names,  # noqa: F401
    same_star_count,  # noqa: F401
    star_base_copies,  # noqa: F401
    will_merge_on_buy,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_economy import (  # noqa: F401
    DIFFICULTY_HP_TABLE,  # noqa: F401
    HP_SAFE_THRESHOLD,  # noqa: F401
    MAX_PLAYER_LEVEL,  # noqa: F401
    REFRESH_COST_BASE,  # noqa: F401
    XP_CLICK_COST_FALLBACK,  # noqa: F401
    XP_PER_BUY,  # noqa: F401
    XP_TO_NEXT_LEVEL,  # noqa: F401
    bench_char_cost,  # noqa: F401
    card_cost,  # noqa: F401
    effective_hp_threshold,  # noqa: F401
    sell_refund,  # noqa: F401
    xp_apply_clicks,  # noqa: F401
    xp_clicks_to_level,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_bond_equips import (  # noqa: F401
    _recount_board,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_deploy_logic import (  # noqa: F401
    board_unique_key,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_run_allocator import (  # noqa: F401
    MatchOutcome,  # noqa: F401
)

#: 旧内部名别名续存(外部 ~14 文件含在飞,删除随 sweep 段)。
_bench_char_cost = bench_char_cost
