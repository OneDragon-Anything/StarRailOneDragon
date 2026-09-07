"""货币战争 推进型画面 op 基类(空决策形态;ADR-0584,用户架构裁定 2026-09-07)。

**空决策形态合同**(screen_op.md §8.3 判据总表;T-121 方案 §2.1):纯推进画面
(无选择面 ∧ 无投影账)的画面 op 只做「入口观察 + 推进处理 + 交回」——零策略器
问询、零期望态、零决策行。合同强度:**新 op 一律单尝试**(``node_max_retry_times=1``,
节点内零重试),重试预算归外循环(包装 ``on_fail_retry`` 映射 loop 级 round_retry,
消费同一 retry 池);既有 op 的 as-built 重试语义不在本合同辖内(如
``CwScreenPlaneTransition`` 自带 8 次内部重试)。

事实参照形 = ``CwScreenPlaneTransition``(入口锚校验 → 点空白 → 验提示消失 →
交回)。本基类只统一「入口观察→推进→验效→返回」骨架与日志;**不承担 op_journal
与决策帧留证**——那两样是 dispatch 包装(``cw_loop.CwLoop._dispatch_screen_op``)
的职责,journal 记的是「分发了谁」,属外循环视角(ADR-0584 §2.2/§2.3)。
"""
from typing import ClassVar

from cv2.typing import MatLike

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwProgressionScreenOp(SrOperation):
    """推进型画面 op 基类:入口观察 + 单次推进 + 可选验效 + 如实交回。"""

    #: 画面档名(screen_info 的 screen_name);子类常量,参数化子类可经构造覆写
    SCREEN_NAME: ClassVar[str] = ''
    #: 入口锚 area 名(与外循环分发判定同源同参;空串 = 免锚,由子类自证)
    ENTRY_AREA: ClassVar[str] = ''
    #: 验效锚 area 名(非空 = 推进后新帧该锚消失才算成功;空 = 无验效)
    VERIFY_AREA: ClassVar[str] = ''

    def __init__(self, ctx: SrContext, op_name: str,
                 screen_name: str | None = None,
                 entry_area: str | None = None,
                 verify_area: str | None = None):
        """构造参数可覆写类常量(参数化子类先例 = ``CwScreenBattleWait(ctx, st, config)``)。

        :param ctx: 运行上下文
        :param op_name: op 名(journal/日志读面)
        :param screen_name: 画面档名;None = 用类常量 SCREEN_NAME
        :param entry_area: 入口锚;None = 用类常量 ENTRY_AREA
        :param verify_area: 验效锚;None = 用类常量 VERIFY_AREA
        """
        SrOperation.__init__(self, ctx, op_name=op_name)
        self._screen_name: str = screen_name if screen_name is not None \
            else self.SCREEN_NAME
        self._entry_area: str = entry_area if entry_area is not None \
            else self.ENTRY_AREA
        self._verify_area: str = verify_area if verify_area is not None \
            else self.VERIFY_AREA

    def entry_ok(self, screen: MatLike | None) -> bool:
        """入口观察:本画面锚校验(缺省 = area 键原语;与分发判定同源)。

        不命中返回 False → 节点 fail 交回外循环重判——**不在 op 内等待重探**,
        「下一帧重判」是外循环职责(环让位重入契约,outer_loop.md §3-12)。
        申报(方案审 N8,ADR-0584):这道入口重验是 op 化新增的失败模式
        (分发判定帧命中 ∧ op 新帧入口锚 miss 的过渡帧),经包装映射交回
        重判后收敛等价,行为对账按新失败模式单独计。
        """
        if not self._entry_area:
            return True
        return self.round_by_find_area(
            screen, self._screen_name, self._entry_area,
            crop_first=False).is_success

    def progress_once(self) -> bool:
        """推进处理:单次固定推进动作(点击/按键)。

        :return: True = 动作已发出;False = 动作未落地(如点击目标未命中)
        """
        raise NotImplementedError

    def verify_dismissed(self, screen: MatLike | None) -> bool:
        """验效:推进后画面确已离开(缺省无验效 = 恒 True;验不消失 = fail)。"""
        if not self._verify_area:
            return True
        return not self.round_by_find_area(
            screen, self._screen_name, self._verify_area,
            crop_first=False).is_success

    @operation_node(name='推进处理', is_start_node=True, node_max_retry_times=1)
    def handle(self) -> OperationRoundResult:
        """空决策形态单节点:入口观察 → 推进(单尝试)→ 验效 → 如实返回。

        失败一律 ``round_fail``(节点内零重试);重试预算由外循环包装的
        ``on_fail_retry`` 映射承接。
        """
        if not self.entry_ok(self.last_screenshot):
            return self.round_fail(f'{self.op_name}入口锚未命中(交回外循环重判)')
        if not self.progress_once():
            return self.round_fail(f'{self.op_name}推进动作未落地')
        if not self.verify_dismissed(self.screenshot()):
            return self.round_fail(f'{self.op_name}推进后画面未消失')
        return self.round_success(f'{self.op_name}已推进')
