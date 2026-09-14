"""买经验动作 op(LevelUpOp)——动作文件一 op 一文件拆分自
cw_action_base.py(基类留该文件,本文件只放本动作)。
"""
from __future__ import annotations

import time

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_vocab import LevelUp
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ShopActionOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
    ShopExecEnv,
)


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
