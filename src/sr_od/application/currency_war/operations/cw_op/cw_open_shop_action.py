"""开店动作 op(OpenShopOp)——备战域动作文件(统一动作工厂批3;注册行 =
terminal 承载行,design.md unified-action-factory §2.4 显式裁定)。

**本 op 的 execute 在正常路径不可达**:OpenShop 的流程编排是画面 op 流程
职责(``cw_screen_prep._act_execute_default`` 截流 → ``_open_shop_phase``),
按「流程编排留守」划分不进动作 op;注册行的用途 = 终结判定/等待时长经
注册表读类属性(terminal/terminal_wait)。可达(经注册表分派到本 op 执行)
= 分派漏斗被绕过,AssertionError 响亮暴露防静默复活。read_only 两形态 =
动作字段 ``OpenShop.read_only`` 承载,消费在流程层编排,与注册表无关。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class OpenShopOp(ActionOp):
    """开店(注册行 = terminal 承载行;execute 抛 AssertionError)。

    终结动作:开店切商店画面(非帧稳定)→ 本备战访问终结,交回外循环
    重识别;终结等待 = ``terminal_wait``(与原决策循环 ``wait=1.0`` 逐字
    等价,等价测试锁 = test_cw_unified_action_3)。
    """

    terminal = True

    #: 终结交回等待秒数(与原决策循环 wait=1.0 逐字等价)。
    terminal_wait = 1.0

    def execute(self, env: PrepExecEnv) -> bool:
        raise AssertionError(
            'OpenShop 不经动作 op 执行(流程层编排:cw_screen_prep.'
            '_act_execute_default 截流 → _open_shop_phase);本注册行 = '
            'terminal 承载行,正常路径不可达,可达即分派漏斗被绕过'
            '(design.md unified-action-factory §2.4)')
