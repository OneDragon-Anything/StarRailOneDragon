"""货币战争 推进型画面 op 基类(空决策形态;ADR-0584,用户架构裁定 2026-09-07)。

**空决策形态合同**(screen_op.md §8.3 判据总表;T-121 方案 §2.1):纯推进画面
(无选择面 ∧ 无投影账)的画面 op 只做「入口观察 + 推进处理 + 交回」——零策略器
问询、零期望态、零决策行。重试预算:节点预算 = 1 次推进 + 1 次重入观察裁决
(``node_max_retry_times=2``);裁决仍不落地 → FAIL 交回,其余重试归外循环
(包装 ``on_fail_retry`` 映射 loop 级 round_retry,消费同一 retry 池)。

**验证段退役**(用户裁定 2026-09-10:动作 op 只管机械执行,禁止做任何验证):
原「推进后验效(锚消失才算成功)」骨架半拆除——落地判定归下一轮重入的入口
观察(重入锚不在 = 已离开本画面 → success 交回;在 = 再做一次推进,计节点
预算)。重入出口 = ``entry_ok`` 的合法观察(M7 同化先例:循环顶「已离开本
节点画面?」→success),非动作层判效。首发锚 miss(误分发)仍 fail 交回,
外循环守卫语义(P4R3 误分发计数等)原样。

事实参照形 = ``CwScreenPlaneTransition``(入口锚校验 → 点空白 → 重入观察
裁决 → 交回)。本基类只统一「入口观察→推进→重入裁决」骨架与日志;**不承担
op_journal 与决策帧留证**——那两样是 dispatch 包装(``cw_loop.CwLoop
._dispatch_screen_op``)的职责,journal 记的是「分发了谁」,属外循环视角
(ADR-0584 §2.2/§2.3)。
"""
from typing import ClassVar

from cv2.typing import MatLike

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwProgressionScreenOp(SrOperation):
    """推进型画面 op 基类:入口观察 + 单次推进 + 重入观察裁决交回(验证废除)。"""

    #: 画面档名(screen_info 的 screen_name);子类常量,参数化子类可经构造覆写
    SCREEN_NAME: ClassVar[str] = ''
    #: 入口锚 area 名(与外循环分发判定同源同参;空串 = 免锚,由子类自证)
    ENTRY_AREA: ClassVar[str] = ''

    def __init__(self, ctx: SrContext, op_name: str,
                 screen_name: str | None = None,
                 entry_area: str | None = None):
        """构造参数可覆写类常量(参数化子类先例 = ``CwScreenBattleWait(ctx, st, config)``)。

        :param ctx: 运行上下文
        :param op_name: op 名(journal/日志读面)
        :param screen_name: 画面档名;None = 用类常量 SCREEN_NAME
        :param entry_area: 入口锚;None = 用类常量 ENTRY_AREA
        """
        SrOperation.__init__(self, ctx, op_name=op_name)
        self._screen_name: str = screen_name if screen_name is not None \
            else self.SCREEN_NAME
        self._entry_area: str = entry_area if entry_area is not None \
            else self.ENTRY_AREA
        # 推进已发标志(验证废除形态):区分「首发锚 miss = 误分发 fail 交回」
        # 与「重入锚 miss = 已离开本画面 success 交回」(实例级,单 op 生命周期)。
        self._advanced_once: bool = False

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

    @operation_node(name='推进处理', is_start_node=True, node_max_retry_times=2)
    def handle(self) -> OperationRoundResult:
        """空决策形态单节点:入口观察 → 推进(单尝试)→ 重入观察裁决 → 交回。

        轮次语义(验证废除形态,用户裁定 2026-09-10):
        - 首发:锚 miss = 误分发 → fail 交回外循环重判;
        - 推进已发 → ``round_retry``(机械交回,不读屏判效);
        - 重入:锚 miss = 已离开本画面 → success 交回(出口 = 入口观察的
          合法重判,M7 同化先例);锚仍在 = 再做一次推进(计节点预算);
        - 预算(=2)耗尽 → FAIL 交回(有界终止单;其余重试归外循环)。
        """
        _hit = self.entry_ok(self.last_screenshot)
        if not _hit:
            if self._advanced_once:
                self._advanced_once = False
                return self.round_success(
                    f'{self.op_name}已推进(重入观察:已离开本画面)', wait=1)
            return self.round_fail(f'{self.op_name}入口锚未命中(交回外循环重判)')
        if not self.progress_once():
            return self.round_fail(f'{self.op_name}推进动作未落地')
        self._advanced_once = True
        if not self._entry_area and type(self).entry_ok \
                is CwProgressionScreenOp.entry_ok:
            # 免锚 op(空锚且未覆写 entry_ok = 无「已离开」观察信号):
            # 重入裁决不可达 → 发出即 success 交回(原无验效形态;有界性
            # 归外循环重派/分发,bail 计数消费零漂移)。覆写 entry_ok 的
            # 子类(双锚其一形态)有裁决信号,正常走重入裁决。
            return self.round_success(f'{self.op_name}推进已发(免锚)')
        return self.round_retry(f'{self.op_name}推进已发,重入观察裁决', wait=1)
