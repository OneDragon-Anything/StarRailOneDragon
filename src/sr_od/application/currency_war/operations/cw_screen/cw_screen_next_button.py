"""货币战争 前进按钮 op(空决策形态;ADR-0584,A10)。

简报等画面的「下一步」前进按钮(分支 5)的处理迁移:OCR 找到即点,
无验效,序位近外循环尾(兜底点击)。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation;
推进型空决策骨架逐屏内联,无共享基类——模式一致即重复):观察 node =
入口门(OCR「下一步」,与外循环分支 5 判定同源同参、默认 lcs 0.5;
miss 未发 = round_fail 交回外循环重判,「下一帧重判」是外循环职责)+
obs{on_screen} 挂实例属性(空决策形态无 report:本屏零容器写点,obs 类
住 kernel/cw_screen_report/next_button.py,import 构造即可)。决策动作
node = 重入裁决顶部(点击已发 → OCR miss = 已离开本画面 → success 交回
——出口 = 入口观察的合法重判,非动作层判效;在 = 再推进)→
``round_by_ocr_and_click`` 再定位点击(入口与点击两次 OCR 扫描,申报:
该帧型每局出现次数少,成本可接受;success_wait=2 同原分支内联值)→
round_wait 循环(不烧节点重试预算,不收敛 = 动作 bug 响亮暴露,无防御
上限;「推进动作未落地」= round_fail 如实交回)。本类入口信号 = 自有
OCR 判定(覆写形态),重入裁决有观察信号可用,无「免锚发出即 success」
出口。
"""
from cv2.typing import MatLike

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_screen_report.next_button import (
    CwScreenNextButtonObs,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenNextButton(SrOperation):
    """前进按钮:OCR「下一步」→ 点击(简报等画面的兜底推进)。"""

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-前进按钮')
        # 推进已发标志(验证废除形态):区分「首发 miss = 误分发 fail 交回」
        # 与「重入 miss = 已离开本画面 success 交回」(实例级,单 op 生命周期)。
        self._advanced_once: bool = False
        # 观察结果(观察 node 产物,决策动作 node 消费;空决策形态无 report)。
        self._obs: CwScreenNextButtonObs | None = None

    def entry_ok(self, screen: MatLike | None) -> bool:
        """入口观察:OCR「下一步」(与外循环分支 5 判定同源同参,默认 lcs)。"""
        return self.round_by_ocr(screen, '下一步').is_success

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口门 + obs{on_screen} 装载(空决策形态无 report)。

        门 miss = 首发误分发(分发判定帧命中 ∧ op 新帧门 miss 的过渡帧):
        fail 交回外循环重判,不在 op 内等待重探。"""
        screen = self.last_screenshot
        if not self.entry_ok(screen):
            return self.round_fail(
                f'{self.op_name}入口锚未命中(交回外循环重判)')
        self._obs = CwScreenNextButtonObs(on_screen=True, screen=screen)
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=2)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 单次推进 → round_wait(预算 = 现役值 2 保留)。"""
        if self._advanced_once and not self.entry_ok(self.last_screenshot):
            # 重入裁决(验证废除形态):重入 miss = 已离开本画面 → success
            # 交回;旗标清(实例级,单 op 生命周期语义)。
            self._advanced_once = False
            return self.round_success(
                f'{self.op_name}已推进(重入观察:已离开本画面)', wait=1)
        if not self.progress_once():
            return self.round_fail(f'{self.op_name}推进动作未落地')
        self._advanced_once = True
        # 循环推进 = round_wait(不烧节点重试预算;不收敛 = 动作 bug 响亮
        # 暴露,无防御上限)。
        return self.round_wait(f'{self.op_name}推进已发,重入观察裁决', wait=1)

    def progress_once(self) -> bool:
        """推进处理:OCR 再定位点击(success_wait=2 同原分支内联值)。"""
        return self.round_by_ocr_and_click(
            self.last_screenshot, '下一步', success_wait=2).is_success
