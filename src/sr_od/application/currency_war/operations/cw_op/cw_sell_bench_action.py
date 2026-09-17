"""卖备战动作 op(SellBenchOp)——动作文件一 op 一文件拆分自
cw_action_base.py(基类留该文件,本文件只放本动作)。
"""
from __future__ import annotations

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_exec_state import (
    pad_bench,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    SellBench,
    mutate_bench_deployed,
)
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
    ShopExecEnv,
)


class SellBenchOp(ActionOp):
    """卖一张 = 一个动作 op;卖回金实收遥测 = 执行实现层(候选 a)。"""

    def execute(self, env: ShopExecEnv) -> bool:
        action: SellBench = self.action
        op, match, ledger = env.op, env.match, env.ledger
        from sr_od.application.currency_war.kernel.cw_game_state import (
            bench_slots_of,
        )
        state = env.state
        _slots = bench_slots_of(state)
        _expected = (_slots[action.bench_idx]
                     if 0 <= action.bench_idx < len(_slots) else None)
        _expected_name = (_expected.char_id if _expected is not None else None)
        # 卖牌实收回金 = 收入账 total_sell_income(计划值)。
        from sr_od.application.currency_war.prep_actions import (
            drag_bench_to_sell,
        )
        # 机械执行:拖拽零判效(源槽像素验重试已拆),发出即记账
        # 并推进 tracked 双账;落地事实归下一帧入口观察 reconcile 对账。
        # (槽位越界 = 调用方 bug,drag_bench_to_sell 守卫响亮上抛。)
        drag_bench_to_sell(op, op.ctx, action.bench_idx)
        # tracking 同步:置 None 不紧缩(ADR-0316)。ADR-0646 S1:
        # 下标直拷(pad 补 None)替代 bench_from_compact 槽号重构——S2 写回
        # 端保证 tracked 恒槽位表后本归一恒等;历史 bug 态(紧凑)下布局以
        # 列表下标为准(与 mutate 入口 pad 同构),不再按 slot 重构(陈旧
        # slot 会把卡放错槽;错位卖出由下方 mutate 代际校验拦截 no-op,
        # 安全非等价——故 S2 先于 S1 生效)。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            game_state_of,
        )
        _books = game_state_of(match.session).tracked_books
        _tracked = _books.bench
        pad_bench(_tracked)
        mutate_bench_deployed(_tracked, _books.deployed, action)
        ledger.total_sell += 1
        ledger.total_sell_income += action.income or 0
        log.info('[cw-shop] Sell bench%d %s(+%s) ✓',
                 action.bench_idx, _expected_name, action.income or '?')
        return True
