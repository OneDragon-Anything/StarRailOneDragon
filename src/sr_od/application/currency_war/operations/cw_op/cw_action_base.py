"""动作 op 基类文件:通用基类 ``ActionOp`` + 执行环境协议
``ActionExecEnv``(统一动作工厂批1;原商店域 ShopActionOp 升格,零行为
更名)。词表→op 工厂单一注册在 ``cw_action_registry.py``(批1 自
cw_shop_actions 迁入;消费面 ``shop_action_op_for`` 薄委托口径不变)。

具体动作 op 在各自 ``cw_<action>_action.py`` 文件(商店域 + 备战域批3
收编件)。本文件只放跨动作共享件(terminal/terminal_wait 类属性语义、
execute 单方法契约、env 协议),**禁 import 具体动作文件**(反向循环);
账本/域执行环境留各域模块(ShopExecEnv = cw_shop_action_ops 单一源不迁;
PrepExecEnv = prep_actions,批3;各自以公共字段 op/match/config 结构化
满足 ActionExecEnv 协议)。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, Protocol

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_vocab import Action
    from sr_od.operations.sr_operation import SrOperation


class ActionExecEnv(Protocol):
    """动作 op 执行环境协议(design.md §2.2):域 env 结构化满足(不继承
    ——协议仅静态契约面,运行时不检查)。

    商店域 ``ShopExecEnv``(cw_shop_action_ops,公共字段 op/match/config
    + 域私有字段)现役即满足;备战域 ``PrepExecEnv``(prep_actions,批3)
    同构满足。动作 op 子类覆写 ``execute`` 可窄化为本域 env 类型(运行时
    不检查参数类型,项目既有风格)。
    """

    op: SrOperation
    match: object
    config: object


class ActionOp(ABC):
    """通用动作 op 基类(execute 单方法;原 project 逻辑态推算半已删
    (前身契约),纯规则路线——期望态推进 = 容器逻辑态直写,模块头
    申报)。

    基类契约:``execute`` 返回恒 True(终裁:发出即职责完成,零
    判效——落地事实归下一帧入口观察 reconcile 对账,不据执行侧判定
    改道)。**例外登记口**:在册例外 = StartBattleOp(返回值 = 点击序列
    已执行,非恒 True——找不到按钮/area 缺失 = False;消费面 = runner
    包络 last_launch_ok 旁路;design.md §2.4,批3 落款生效;语义收缩 =
    T-286 出战域重设计)。prep 域 ``(detail, emitted)``
    语义经 PrepExecEnv 旁路字段承载,不进返回值。
    """

    #: 终结动作(执行即本画面访问结束,交回外循环;决策 4)
    terminal: bool = False

    #: 终结交回等待秒数(动作转移语义时长,随 op 类承载;仅 terminal=True
    #: 的 op 有语义。消费点经注册表读类属性,禁消费点私表——design.md
    #: §2.4 终结判定对齐。现役值:StartBattleOp=3 / OpenShopOp=1.0 /
    #: OpenBoxOp 与 prep_actions._OVERLAY_ANIM_WAIT_S 等价;等价测试锁 =
    #: sr-od-test test_cw_unified_action_3)。
    terminal_wait: ClassVar[float] = 0.0

    def __init__(self, action: Action):
        self.action = action

    @abstractmethod
    def execute(self, env: ActionExecEnv) -> bool:
        """机械执行;返回恒 True(终裁:发出即职责完成,零判效——
        落地事实归下一帧入口观察 reconcile 对账,不据执行侧判定改道;
        在册例外与旁路语义见类 docstring 例外登记口)。"""
