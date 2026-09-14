"""整档替换事务动作 op(CompTransactionOp)——动作文件一 op 一文件
拆分自 cw_shop_actions.py(该文件转聚合注册,本文件只放本动作)。
"""
from __future__ import annotations

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ShopActionOp,
)
from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
    ShopExecEnv,
)


class CompTransactionOp(ShopActionOp):
    """整档替换事务 = 复合动作类(ADR-0517 §复合动作类):一个 op、
    原子投影、C1 前置合法性(任一子步资源不足 ⇒ 整体不提案)。

    **终结邻接 fallback(现行档)**:合成建模验证未过(非满栏一击张数
    = research 知识缺口,模块头申报)⇒ 执行后本画面访问结束交回外循环
    重观察(= 旧截断点语义,禁半档中间态)。商店单动作决策核现行不提案
    CompTransaction(词表保留;提案面在备战域),本 op 为词表完备性落位。
    """

    terminal = True

    def execute(self, env: ShopExecEnv) -> bool:
        log.info('[cw-shop] CompTransaction(终结邻接 fallback:'
                 '执行后交回外循环重观察,ADR-0517 §复合动作类)')
        return True
