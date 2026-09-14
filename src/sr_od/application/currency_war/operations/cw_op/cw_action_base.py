"""动作 op 基类文件:仅 ShopActionOp 共享基类(T-201 一 op 一文件拆分)。

六个具体动作 op 在各自 ``cw_<action>_action.py`` 文件;词表→op 工厂
聚合注册在 ``cw_shop_actions.py``(聚合注册文件,非 op 文件)。本文件
只放跨动作共享件(terminal 类属性语义、execute 单方法契约),**禁
import 具体动作文件**(反向循环);账本/执行环境留 cw_shop_action_ops
(ShopExecEnv 单一源不迁)。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

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
