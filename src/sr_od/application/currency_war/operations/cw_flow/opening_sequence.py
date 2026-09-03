"""货币战争 开局编排壳(W971 P3a:壳 + 首帧分流骨架;01-opening §2/§2.1)。

开局序列 = BriefingOp → PlaneTransitionOp → InvestEnvOp → WaitOneOneOp,
跑完(1-1 备战就绪)交常态循环。本批只建壳与分流骨架,**接线进主循环归 P3b**
(cw_loop 开局分支不动)。

步骤分流语义(01-opening §2.1):
- 干净开局:首帧 = 简报 → 从第 0 步顺序走;
- 接管局/重入:首帧已是序列中后段画面 → 从该步续走(resume_step_index);
- 各步 round_fail = 该步画面不适用(已过/未到)或步内失败 → 记录后继续下一步,
  终步 WaitOneOneOp 决定序列成败(1-1 备战就绪 = 序列成功)。

投资环境步复用现役 ``HandleInvestEnv`` 完整逻辑(节点台账重读/刷新流随 op 迁移
是 P3b 的事,本批薄封装委托,现状复用源不动)。
"""
from collections.abc import Callable
from typing import ClassVar

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_screen_state import get_in_match_screen_name
from sr_od.application.currency_war.operations.cw_flow.briefing_op import BriefingOp
from sr_od.application.currency_war.operations.cw_flow.plane_transition_op import (
    PlaneTransitionOp,
)
from sr_od.application.currency_war.operations.cw_flow.wait_one_one_op import (
    WaitOneOneOp,
)
from sr_od.application.currency_war.operations.handlers.handle_invest_env import (
    HandleInvestEnv,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

#: 步骤工厂类型(ctx → 子 op)。
StepFactory = Callable[[SrContext], SrOperation]


def resume_step_index(screen_name: str | None) -> int:
    """首帧分流:当前画面名 → 应续走步骤下标(纯函数,单测锁)。

    识别不中(未知/过渡帧)→ 0 从头走:各步自带入口识别,不适用步自身 fail 跳过,
    与干净开局同一条代码路径(无独立接管分支)。
    """
    step_screens: tuple[str, ...] = (
        BriefingOp.SCREEN_NAME,          # 0 简报
        PlaneTransitionOp.SCREEN_NAME,   # 1 位面过渡
        '货币战争-投资环境',              # 2 投资环境(现役 handler 屏名)
        WaitOneOneOp.PREP_SCREEN,        # 3 备战(1-1 就绪判定)
    )
    if screen_name in step_screens:
        return step_screens.index(screen_name)
    return 0


class OpeningSequence(SrOperation):
    """开局编排壳:四步顺序执行,终步(WaitOneOneOp)成功 = 序列成功交常态循环。"""

    #: 默认步骤表(下标与 resume_step_index 的 step_screens 对齐);
    #: 实例属性 ``steps`` 可整体替换(测试注替身步骤,P3b 接线时也只动这里)。
    DEFAULT_STEPS: ClassVar[list[tuple[StepFactory, str]]] = [
        (BriefingOp, '简报'),
        (PlaneTransitionOp, '位面过渡'),
        (HandleInvestEnv, '投资环境'),
        (WaitOneOneOp, '等待1-1'),
    ]

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-开局序列')
        self.steps: list[tuple[StepFactory, str]] = list(self.DEFAULT_STEPS)

    @operation_node(name='开局序列', is_start_node=True)
    def run(self) -> OperationRoundResult:
        screen = self.screenshot()
        _screen_name = get_in_match_screen_name(self.ctx, screen)
        start_idx = resume_step_index(_screen_name)
        if start_idx > 0:
            log.info('[cw-flow-opening] 首帧分流: %s → 从第 %d 步(%s)续走',
                     _screen_name, start_idx, self.steps[start_idx][1])
        result: OperationRoundResult | None = None
        for _factory, _name in self.steps[start_idx:]:
            _sub = _factory(self.ctx)
            result = self.round_by_op_result(_sub.execute())
            log.info('[cw-flow-opening] 步骤[%s] → %s', _name, result.status)
            # 各步 fail 不中断:该步画面不适用(分流)或步内失败,交下一步重新判定;
            # 终步成败即序列成败。
        if result is None:
            return self.round_fail('开局序列步骤表为空')
        return result
