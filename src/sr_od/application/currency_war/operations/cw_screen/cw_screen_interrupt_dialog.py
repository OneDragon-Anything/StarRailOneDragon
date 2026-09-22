"""货币战争 中断挑战 dialog op(空决策形态,A9)。

ESC 误按/误点左上角弹出的「是否中断挑战」真模态(1g,历史 3 次实锤;
2026-08-17 建档替原停机钩子)的处理迁移:点右上 X 关回备战,单尝试合同
(验证废除批拆 op 内新帧重试:C10——X 不在(旧帧)的重试由外循环重派
承载,重派即新帧)。**刻意不用 ESC**(bug#2,原分支注释随迁,
禁在 op 内「顺手统一」成 ESC):面板已关时 ESC 落备战弹「中断挑战」;
X 是弹窗内坐标永远安全。背景:2026-08-17 M53 停机建档。

**语义红线(原分支注释随迁)**:点遮罩无效;bot 策略 = 点右上 X 关闭继续
对局——不点「暂时离开」免中断对局,**绝不点「放弃并结算」**(不可逆放弃
进度)。弹窗内「小队生命值」为 HP 真值快照,顺带对账备用,暂不消费。
exogenous popup 行随 op 迁移(r378b 测量链 review B1:误触弹窗是外生事件
高频源,bug#2 ESC 三次实锤)。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation;
推进型空决策骨架逐屏内联,无共享基类——模式一致即重复):观察 node =
入口锚门(「标识-中断挑战」,与外循环 1g 分发判定同源同参;miss 未发 =
round_fail 交回外循环重判,「下一帧重判」是外循环职责)+ obs{on_screen}
挂实例属性(空决策形态无 report:本屏零容器写点,obs 类住
kernel/cw_screen_report/interrupt_dialog.py,import 构造即可)。决策动作
node = 重入裁决顶部(点 X 已发 → 锚 miss = 已离开本画面 → success 交回
——出口 = 入口观察的合法重判,非动作层判效;锚在 = 再推进)→ 点
「按钮-关闭」单次推进(单尝试合同,见模块头)→ round_wait 循环(不烧
节点重试预算,不收敛 = 动作 bug 响亮暴露,无防御上限;「推进动作未
落地」= round_fail 如实交回)。
"""
from cv2.typing import MatLike

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_screen_report.interrupt_dialog import (
    CwScreenInterruptDialogObs,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenInterruptDialog(SrOperation):
    """中断挑战 dialog:点右上 X 关闭(失败新帧重试),绝不点放弃并结算。"""

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-中断挑战弹窗')
        # 画面档名/入口锚(与外循环 1g 分发判定同源同参;实例属性)
        self._screen_name: str = '货币战争-中断挑战弹窗'
        self._entry_area: str = '标识-中断挑战'
        # 推进已发标志(验证废除形态):区分「首发锚 miss = 误分发 fail 交回」
        # 与「重入锚 miss = 已离开本画面 success 交回」(实例级,单 op 生命周期)。
        self._advanced_once: bool = False
        # 观察结果(观察 node 产物,决策动作 node 消费;空决策形态无 report)。
        self._obs: CwScreenInterruptDialogObs | None = None

    def entry_ok(self, screen: MatLike | None) -> bool:
        """入口观察:本画面锚校验(area 键原语,与分发判定同源同参)。"""
        return self.round_by_find_area(
            screen, self._screen_name, self._entry_area,
            crop_first=False).is_success

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口锚门 + obs{on_screen} 装载(空决策形态无 report)。

        门 miss = 首发误分发(分发判定帧命中 ∧ op 新帧锚 miss 的过渡帧):
        fail 交回外循环重判,不在 op 内等待重探。"""
        screen = self.last_screenshot
        if not self.entry_ok(screen):
            return self.round_fail(
                f'{self.op_name}入口锚未命中(交回外循环重判)')
        self._obs = CwScreenInterruptDialogObs(on_screen=True, screen=screen)
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=2)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 单次推进 → round_wait(预算 = 现役值 2 保留)。"""
        if self._advanced_once and not self.entry_ok(self.last_screenshot):
            # 重入裁决(验证废除形态):重入锚 miss = 已离开本画面 → success
            # 交回;旗标清(实例级,单 op 生命周期语义)。
            self._advanced_once = False
            return self.round_success(
                f'{self.op_name}已推进(重入观察:已离开本画面)', wait=1)
        if not self.progress_once():
            return self.round_fail(f'{self.op_name}推进动作未落地')
        self._advanced_once = True
        # 空锚 = 免锚出口(无「已离开」观察信号,发出即 success);本屏锚
        # 非空,分支结构性不可达,逐位保留空锚语义(参数化屏 = 备战暗色
        # 锁定为可达形态)。否则循环推进 = round_wait(不烧节点重试预算;
        # 不收敛 = 动作 bug 响亮暴露,无防御上限)。
        if not self._entry_area:
            return self.round_success(f'{self.op_name}推进已发(免锚)')
        return self.round_wait(f'{self.op_name}推进已发,重入观察裁决', wait=1)

    def progress_once(self) -> bool:
        """推进处理:点「按钮-关闭」。

        单尝试合同(验证废除,C10 拆 op 内新帧重试):一次 find+click,
        按钮不在(旧帧/已自关)不再原地新帧重找——False 交 fail,外循环
        重派 = 新帧重试在 loop 级承载(重派即新帧,语义等价)。"""
        _btn = self.round_by_find_and_click_area(
            self.last_screenshot, self._screen_name, '按钮-关闭')
        if _btn.is_success:
            self.park_cursor(after_wait=0.1)
        return _btn.is_success
