"""货币战争 合成确认浮层收尾 op(点 ✓ 完成已发起合成)。

装备拖装备发起合成后弹出的 ✓/✕ 确认浮层(驻留不自动消失,期间游戏丢弃
浮层外全部输入)的框架接管面:双锚其一命中即接管,点「按钮-合成浮层通过」
单次推进,落地复查浮层消失后结束本次访问。

形态(画面 op 两段式,对齐 CwScreenRoleDetailOverlay 先例):观察 node =
入口门(双锚其一;miss 未发 = round_fail 交回主循环重新判定);决策动作
node = 落地复查顶部(点 ✓ 已发 → 双锚 miss = 已离开本画面 → success——出口 =
入口观察的合法重判,非动作层判效;在 = 再推进)→ 点 ✓ 单次推进
(success_wait 等关闭/合成动画)→ round_wait 循环(不烧节点重试预算,不收敛
= 动作 bug 响亮暴露)。「首发门 miss = 误分发 fail」与「重入 miss = 已离开
success」的语义区分 = ``_advanced_once`` 旗标(先例同款)。

✕ 取消语义不在本 op(自动取消 = 丢弃已发起意图,零收益场景;人工口径已够)。
"""
from cv2.typing import MatLike

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext


class CwScreenSynthesisConfirm(CwOperation):
    """合成确认浮层收尾:双锚其一命中即接管,点 ✓ 完成已发起合成,落地复查消失后结束。
    起点:货币战争-备战-合成确认浮层在场;终点:浮层已消失(合成完成,两件变一件)。
    消耗:合成输入两件(完成已发起合成的意图;✕ 取消语义不在本 op,禁自动取消)。

    双消费面:cw_loop 身份分发 handler + MCP 直调(run_operation 一键收尾)。
    入口判据 = 双锚其一(✓ ∨ ✕,比身份分发双锚全中宽一档——接管面比分发宽,
    变体帧经重入观察自愈,同守卫「宁误拦」不对称口径);误分发的失败出口 =
    首发门 miss round_fail 交回主循环重判,无死锁。本 op 无业务参数(构造仅 ctx)。
    """

    #: 画面档名(双锚所在建档,与外循环身份分发同画面档)。
    SCREEN_NAME: str = '货币战争-备战-合成确认'

    def __init__(self, ctx: SrContext):
        CwOperation.__init__(self, ctx, op_name='货币战争-合成确认浮层')
        # 推进已发标志(零验证形态):区分「首发识别标志 miss = 误分发 失败结束
        # 本次访问」与「重入识别标志 miss = 已离开本画面 success 结束本次访问」
        #(实例级,单 op 生命周期)。
        self._advanced_once: bool = False

    def entry_ok(self, screen: MatLike | None) -> bool:
        """入口观察:双锚其一(✓ ∨ ✕;与分发双锚全中的宽度差见类 docstring)。"""
        return (self.round_by_find_area(screen, self.SCREEN_NAME,
                                        '按钮-合成浮层通过',
                                        crop_first=False).is_success
                or self.round_by_find_area(screen, self.SCREEN_NAME,
                                           '按钮-合成浮层取消',
                                           crop_first=False).is_success)

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口门(双锚其一)。

        门 miss = 首发误分发(分发判定帧命中 ∧ op 新帧门 miss 的过渡帧/
        浮层已被人工消掉):失败结束本次访问,返回主循环重新判定,不在
        op 内等待重探。"""
        if not self.entry_ok(self.last_screenshot):
            return self.round_fail(
                f'{self.op_name}入口识别标志未命中(交回外循环重判)')
        return self.round_success(wait=0)

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=2)
    def act(self) -> OperationRoundResult:
        """落地复查(顶部)→ 点 ✓ 单次推进 → round_wait 循环。"""
        if self._advanced_once and not self.entry_ok(self.last_screenshot):
            # 落地复查(零验证形态):重入双锚 miss = 已离开本画面(✓ 已生效,
            # 浮层关闭)→ success 结束本次访问;旗标清(实例级语义)。
            self._advanced_once = False
            return self.round_success(
                f'{self.op_name}已推进(重入观察:浮层已消失)', wait=1)
        if not self.progress_once():
            return self.round_fail(f'{self.op_name}推进动作未落地')
        self._advanced_once = True
        # 循环推进 = round_wait(不烧节点重试预算;不收敛 = 动作 bug 响亮暴露)。
        return self.round_wait(f'{self.op_name}点 ✓ 已发,重入观察裁决', wait=1)

    def progress_once(self) -> bool:
        """推进处理:点「按钮-合成浮层通过」(success_wait 等合成/关闭动画,
        裸 click 无等待 → 截图落动画窗口假失败自愈循环)。"""
        return self.round_by_find_and_click_area(
            self.last_screenshot, self.SCREEN_NAME, '按钮-合成浮层通过',
            success_wait=1.5).is_success
