"""T-198-2:动作文件重组——中立聚合点 cw_action_base.py(基类+跨面板动作)。

纯移动零行为:ShopActionOp 基类与 LevelUpOp/SellBenchOp 自
cw_shop_actions.py 迁入(跨面板动作与商店面板独占动作分离,默认策略
收缩 T-198 切片 2);cw_shop_actions.py 转为商店面板独占动作 + 工厂,
经本文件导入保持词表聚合(消费面 __init__ 再导出零变化)。
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_exec_state import (
    exec_state_of,
    pad_bench,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    LevelUp,
    SellBench,
    mutate_bench_deployed,
)
from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
    ShopExecEnv,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_vocab import Action


class ShopActionOp(ABC):
    """商店动作 op 基类(execute 单方法;原 project 投影半已删,T-163
    纯规则路线——期望态推进 = 容器投影直写,模块头申报)。"""

    #: 终结动作(执行即本画面访问结束,交回外循环;决策 4)
    terminal: bool = False

    def __init__(self, action: Action):
        self.action = action

    @abstractmethod
    def execute(self, env: ShopExecEnv) -> bool:
        """机械执行;返回恒 True(T-223 终裁:发出即职责完成,零判效——
        落地事实归下一帧入口观察 reconcile 对账,不据执行侧判定改道)。"""


class LevelUpOp(ShopActionOp):
    """买经验 = 一个动作 op(单击「购买经验」=+XP_PER_BUY 经验,**非整级**;
    升级 = XP 累积过门槛表的结果,真实等级变化以读屏为准)。单动作形态下
    每帧恰发一击,多击序列由决策循环逐帧重组(ADR-0517 §权衡构造性消解)。"""

    def execute(self, env: ShopExecEnv) -> bool:
        action: LevelUp = self.action
        op, ledger = env.op, env.ledger
        op.ctx.controller.click(env.level_btn)
        log.info(f'[cw-shop] LevelUp click @({env.level_btn.x},'
                 f'{env.level_btn.y})')
        # 用户口述口径(screen_flow_timing.md #22,2026-09-02):购买经验
        # 动画 ~1s(原 0.6s 不足;光标遮挡由段顶 park_cursor 防)。
        time.sleep(1.0)
        # 单击「购买经验」= +XP_PER_BUY 经验(4金/击,游戏文档 xp-rules.md
        # §2),**非整级**——升级是 XP 累积过门槛表的结果,真实等级变化以
        # 读屏为准;本计数只数「买经验击数」。
        # (血购执行回执行挂点已随 exogenous 流写入端退役删除——删除波 1;
        #  血本位单点击扣血的机械事实面不变。)
        ledger.total_xp_buy += 1
        ledger.spend_executed += action.cost
        return True


class SellBenchOp(ShopActionOp):
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
        # T-192 机械执行:拖拽零判效(源槽像素验重试已拆),发出即记账
        # 并推进 tracked 双账;落地事实归下一帧入口观察 reconcile 对账。
        # (槽位越界 = 调用方 bug,drag_bench_to_sell 守卫响亮上抛。)
        drag_bench_to_sell(op, op.ctx, action.bench_idx)
        # tracking 同步:置 None 不紧缩(ADR-0316)。T-308/ADR-0646 S1:
        # 下标直拷(pad 补 None)替代 bench_from_compact 槽号重构——S2 写回
        # 端保证 tracked 恒槽位表后本归一恒等;历史 bug 态(紧凑)下布局以
        # 列表下标为准(与 mutate 入口 pad 同构),不再按 slot 重构(陈旧
        # slot 会把卡放错槽;错位卖出由下方 mutate 代际校验拦截 no-op,
        # 安全非等价——故 S2 先于 S1 生效)。
        _tracked = exec_state_of(match.session).tracked_bench_chars
        pad_bench(_tracked)
        mutate_bench_deployed(_tracked, exec_state_of(match.session).tracked_deployed, action)
        # ADR-0328 执行域对齐:卖出件入同轮已卖集(执行成功是卖出事实的
        # 权威,register_round_sold 带轮键自校验)。
        # 换源 T-146(登记集消点):轮键源 = session 容器单例(node = 本
        # 节点备战帧写端,与波内帧 plane/round 同节点同值);旧过渡桥装箱
        # 退役。register_round_sold 消费面 = plane/round 轮键(轮键不匹配
        # 自拒 = 原防御语义不变)。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            board_state_of,
        )
        from sr_od.application.currency_war.kernel.cw_round_ledger import (
            register_round_sold,
        )
        register_round_sold([_expected_name],
                            board_state_of(match.session),
                            match.session)
        ledger.total_sell += 1
        ledger.buy_has_sell = True   # 含卖出 → 本单元期望态不建(`w536`)
        ledger.total_sell_income += action.income or 0
        log.info('[cw-shop] Sell bench%d %s(+%s) ✓',
                 action.bench_idx, _expected_name, action.income or '?')
        return True
