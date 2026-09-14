"""动作 op 基类文件:通用基类 ``ActionOp`` + 执行环境协议
``ActionExecEnv``(统一动作工厂批1;原商店域 ShopActionOp 升格,零行为
更名)。词表→op 工厂单一注册在 ``cw_action_registry.py``(批1 自
cw_shop_actions 迁入;消费面 ``shop_action_op_for`` 薄委托口径不变)。

六个具体商店动作 op 在各自 ``cw_<action>_action.py`` 文件。本文件只放
跨动作共享件(terminal 类属性语义、execute 单方法契约、env 协议),
**禁 import 具体动作文件**(反向循环);账本/域执行环境留
cw_shop_action_ops(ShopExecEnv 单一源不迁;其以公共字段 op/match/config
结构化满足 ActionExecEnv 协议,批2 增 PrepExecEnv 同构满足)。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_vocab import Action
    from sr_od.operations.sr_operation import SrOperation


class ActionExecEnv(Protocol):
    """动作 op 执行环境协议(design.md §2.2):域 env 结构化满足(不继承
    ——协议仅静态契约面,运行时不检查)。

    商店域 ``ShopExecEnv``(cw_shop_action_ops,公共字段 op/match/config
    + 域私有字段)现役即满足;批2 备战域 ``PrepExecEnv`` 同构满足。动作
    op 子类覆写 ``execute`` 可窄化声明为本域 env 类型(运行时不检查参数
    类型,项目既有风格)。
    """

    op: SrOperation
    match: object
    config: object


class ActionOp(ABC):
    """通用动作 op 基类(execute 单方法;原 project 逻辑态推算半已删
    (前身契约),T-163 纯规则路线——期望态推进 = 容器逻辑态直写,模块头
    申报)。

    基类契约:``execute`` 返回恒 True(T-223 终裁:发出即职责完成,零
    判效——落地事实归下一帧入口观察 reconcile 对账,不据执行侧判定
    改道)。**例外登记口**:在册例外 = StartBattleOp(返回值 = 发射位
    内部事实非恒 True,design.md §2.4,批3 落款收编;批1 仅占位登记,
    零行为)。
    """

    #: 终结动作(执行即本画面访问结束,交回外循环;决策 4)
    terminal: bool = False

    def __init__(self, action: Action):
        self.action = action

    @abstractmethod
    def execute(self, env: ActionExecEnv) -> bool:
        """机械执行;返回恒 True(T-223 终裁:发出即职责完成,零判效——
        落地事实归下一帧入口观察 reconcile 对账,不据执行侧判定改道;
        在册例外见类 docstring 例外登记口)。"""
