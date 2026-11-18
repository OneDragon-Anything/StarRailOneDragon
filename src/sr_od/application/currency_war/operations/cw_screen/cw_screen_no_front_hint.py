"""货币战争 前台无角色提示弹窗处理 op(从主循环内联分支拆出的独立画面 op)。

确认关闭「前台区域无角色」提示弹窗,解除出战阻塞。零恢复动作语义:确认
即结束本次访问交回主循环,不重部署不补发出——「前台无角色」根因处置归
部署面决策,弹窗分支不自愈;弹窗残留 = 主循环下一帧重判再入本 op,天然
幂等。

形态(画面 op 两段式:观察 node → 决策动作 node,继承 CwOperation,
轻屏统一形态,先例 = ``CwScreenDeployNotFull``):观察 node = 标识门
(id_mark「标识-无角色提示」,miss = round_fail 交编排壳按步分流)+ 门内
obs{on_screen} → 调占位 ``report_screen_no_front_obs``(统一形态;本屏
现役零状态容器写点,接口为占位,match/gs 缺席跳过)→ obs 挂实例属性进
决策 node。决策动作 node = 落地复查顶部(确认已发 → 识别标志不在 = 弹窗
已关 → success 返回主循环;识别标志在场 = 确认未落地 → 重做确认)→ 点
「按钮-确认」→ round_wait 循环推进(不烧节点重试预算;不收敛 = 动作 bug
响亮暴露,无防御上限)。本屏 sim 分支不适用:后端画面状态机不建模本屏,
弹窗帧恒不派发到本 op。
"""
from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_screen_report.no_front import (
    CwScreenNoFrontObs,
    report_screen_no_front_obs,
)
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext


class CwScreenNoFrontHint(CwOperation):
    """前台无角色提示弹窗:确认关闭,交回主循环(零恢复动作)。
    起点:货币战争-提示-前台无角色弹窗出现;终点:已点确认(弹窗是否落地
    由下一帧观察裁决,本 op 只认「本画面处理完结」)。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-提示-前台无角色'   # screen_info 画面(currency_war_toast_no_front.yml)

    def __init__(self, ctx: SrContext):
        CwOperation.__init__(self, ctx, op_name='货币战争-前台无角色确认')
        # 确认已发待落地复查标志(单 op 生命周期):区分「首发识别标志 miss =
        # 误分发 fail 返回主循环」与「重入识别标志 miss = 弹窗已关 success 返回
        # 主循环」(零验证形态:动作层不做效果验证,判效归下一帧观察)。
        self._confirm_pending: bool = False
        # 观察结果(观察 node 产物;门早退轮不装载)。
        self._obs: CwScreenNoFrontObs | None = None

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """标识门 + obs{on_screen} → 占位 report 接入调用。

        门 miss = round_fail 早退交编排壳按步分流(与未达上限弹窗 op 同
        status 语义);门 hit → obs 装载 + 占位 report(match/gs 缺席跳过)。"""
        screen = self.last_screenshot
        # 门 = screen_info id_mark area 实测:主循环身份分发与 op 执行之间画面
        # 可能已切换,重验防在已切换画面上盲点确认。
        if not self.round_by_find_area(
                screen, CwScreenNoFrontHint.SCREEN_NAME,
                '标识-无角色提示').is_success:
            return self.round_fail('非前台无角色弹窗')
        obs = CwScreenNoFrontObs(on_screen=True, screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_no_front_obs(_gs, obs)
        self._obs = obs
        return self.round_success(wait=0)

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=10)
    def act(self) -> OperationRoundResult:
        """落地复查(顶部)→ 点确认 → round_wait。

        落地复查(观察驱动,零验证形态):上轮确认已发 → 识别标志不在 = 弹窗
        已关(落地与否归下一帧观察侧重分发;此处只认「本画面处理完结」)
        → success 返回主循环;识别标志在场 = 确认未落地 → 重做确认。循环
        推进 = round_wait(不烧节点重试预算;不收敛 = 动作 bug 响亮暴露)。"""
        if self._confirm_pending:
            self._confirm_pending = False
            if not self.round_by_find_area(
                    self.last_screenshot, CwScreenNoFrontHint.SCREEN_NAME,
                    '标识-无角色提示').is_success:
                return self.round_success('前台无角色弹窗已关(重入观察裁决)',
                                          wait=1.5)
        return self._confirm_and_dismiss()

    def _confirm_and_dismiss(self) -> OperationRoundResult:
        """确认体:点「按钮-确认」→ 置位(落地判定归下一轮落地复查)→
        round_wait 循环推进。点击落空/失败 = 透传 round_retry(计节点预算,
        有界终止单;按钮永久不可点 = 动作 bug 响亮暴露)。"""
        click_res = self.round_by_find_and_click_area(
            self.last_screenshot, CwScreenNoFrontHint.SCREEN_NAME,
            '按钮-确认', pre_delay=0.3, success_wait=1, retry_wait=1)
        if not click_res.is_success:
            return click_res
        self._confirm_pending = True
        return self.round_wait(wait=1)
