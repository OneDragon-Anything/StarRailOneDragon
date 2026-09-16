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
        # (卖出前 gold 基数读数 _gold_before 已随 sell_income 外生行退役删除
        #  ——删除波 1;卖牌实收回金 = 收入账 total_sell_income(计划值)。)
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
        # ADR-0328 执行域对齐:卖出件入同轮已卖集(执行成功是卖出事实的
        # 权威,register_round_sold 带轮键自校验)。
        # 换源(登记集消点):轮键源 = session 容器单例(node = 本
        # 节点备战帧写端,与波内帧 plane/round 同节点同值);旧过渡桥装箱
        # 退役。register_round_sold 消费面 = plane/round 轮键(轮键不匹配
        # 自拒 = 原防御语义不变)。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            game_state_of,
        )
        from sr_od.application.currency_war.kernel.cw_round_ledger import (
            register_round_sold,
        )
        register_round_sold([_expected_name],
                            game_state_of(match.session),
                            match.session)
        ledger.total_sell += 1
        ledger.buy_has_sell = True   # 含卖出 → 本单元期望态不建(`w536`)
        ledger.total_sell_income += action.income or 0
        log.info('[cw-shop] Sell bench%d %s(+%s) ✓',
                 action.bench_idx, _expected_name, action.income or '?')
        return True
