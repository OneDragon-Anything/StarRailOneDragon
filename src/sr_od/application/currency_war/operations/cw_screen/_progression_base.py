"""货币战争 推进型画面 op 基类(空决策形态;ADR-0584,用户架构裁定 2026-09-07)。

**空决策形态合同**(screen_op.md §8.3 判据总表;T-121 方案 §2.1):纯推进画面
(无选择面 ∧ 无逻辑态账)的画面 op 只做「入口观察 + 推进处理 + 交回」——零策略器
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

**只读/导航变体收编**(统一观察架构·画面op基类收编;ADR-0584 空决策
合同逐字保留,11 子类零改动):本类改挂 ``CwScreenOpBase`` 作只读/导航
变体(B4 选项②形态,decide 空申报 = 本屏无策略消费的合同声明)——
``handle`` 顶部装配点分流(架构设计 §9.1 并存纪律:``cw_game_ports``
两端口完整在场 → ``run_lifecycle()`` 走变体五段;缺省 None = 现役骨架
逐位执行,生产行为零变化)。空决策骨架映射为变体五段:observe = 入口/
重入观察裁决(重入出口随骨架住本段——推进型不属「裁决留守分流前」
定谳辖域,该定谳针对「已发旗标 + 确认/点击待重入」形态)、reconcile =
空申报(空决策形态无对账面)、decide = 空申报、act = ``progress_once``
推进半、on_outcome = 无登记件(注册表缺席 = 零动作)。两路径共享
``entry_ok``/``progress_once`` 单一实现(子类覆写在两条路径同样生效)。
"""
from typing import Any, ClassVar

from cv2.typing import MatLike

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.cw_game_ports import (
    action_sink,
    observation_source,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext


class CwProgressionScreenOp(CwScreenOpBase):
    """推进型画面 op 基类:入口观察 + 单次推进 + 重入观察裁决交回(验证废除)。

    统一观察架构只读/导航变体(B4 选项②形态;ADR-0584 空决策合同逐字
    保留,11 子类零改动)。
    """

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
        CwScreenOpBase.__init__(self, ctx, op_name=op_name)
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

        装配点分流(架构设计 §9.1 并存期;只读/导航变体收编):两端口完整
        在场 → ``run_lifecycle()`` 走变体五段(下方钩子);缺省 None =
        生产直连下方现役骨架(原序列逐位保留,生产行为零变化)。两路径
        轮次语义同形,节点预算归本装饰器、不随路径变。

        轮次语义(验证废除形态,用户裁定 2026-09-10):
        - 首发:锚 miss = 误分发 → fail 交回外循环重判;
        - 推进已发 → ``round_retry``(机械交回,不读屏判效);
        - 重入:锚 miss = 已离开本画面 → success 交回(出口 = 入口观察的
          合法重判,M7 同化先例);锚仍在 = 再做一次推进(计节点预算);
        - 预算(=2)耗尽 → FAIL 交回(有界终止单;其余重试归外循环)。
        """
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
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

    # ---- 变体五段(空决策骨架的段映射;两路径共享零转录)----

    def lifecycle_observe(self) -> tuple[Any, OperationRoundResult | None]:
        """段1 observe:入口/重入观察裁决(现役骨架锚 miss 两分支逐位转录)。

        - 锚 miss + 未推进 = 首发(误分发)→ ``round_fail`` 早退交回
          外循环重判(ADR-0584 外循环守卫语义原样);
        - 锚 miss + 已推进 = 已离开本画面 → 清旗标、``round_success``
          (wait=1)早退——重入裁决出口 = ``entry_ok`` 的合法观察,随
          骨架五段映射住本段;
        - 命中 → 不早退,进后续段(payload = ``None``:空决策形态无观察
          产物,act 半经 ``progress_once`` 自取 ``last_screenshot``)。
        """
        if not self.entry_ok(self.last_screenshot):
            if self._advanced_once:
                self._advanced_once = False
                return None, self.round_success(
                    f'{self.op_name}已推进(重入观察:已离开本画面)', wait=1)
            return None, self.round_fail(
                f'{self.op_name}入口锚未命中(交回外循环重判)')
        return None, None

    def lifecycle_reconcile(self, payload: Any) -> None:
        """段2 reconcile:空申报(空决策形态无对账面,ADR-0584)。"""
        return None

    def lifecycle_decision_cycle(self, payload: Any) -> OperationRoundResult:
        """段3-5:decide 空申报 + act 推进半 + on_outcome 无登记件。

        decide 空申报 = 本屏无策略消费的合同声明(B4 选项②原语义;非
        缺省缺位——ADR-0584 零策略器问询,将来某推进屏长出策略消费时
        按总纲 §2.1-2 规则改直迁全五段形态,属行为变更批单独申报);
        act = ``progress_once`` 推进半(现役骨架逐位转录);on_outcome =
        无登记件(注册表缺席 = 零动作,推进型无 §6.4 收编面)。"""
        self._lifecycle_mark('decide')
        self._lifecycle_mark('act')
        if not self.progress_once():
            rs = self.round_fail(f'{self.op_name}推进动作未落地')
        else:
            self._advanced_once = True
            if not self._entry_area and type(self).entry_ok \
                    is CwProgressionScreenOp.entry_ok:
                # 免锚 op(空锚且未覆写 entry_ok = 无「已离开」观察信号):
                # 重入裁决不可达 → 发出即 success 交回(原无验效形态;有界性
                # 归外循环重派/分发,bail 计数消费零漂移)。覆写 entry_ok 的
                # 子类(双锚其一形态)有裁决信号,正常走重入裁决。
                rs = self.round_success(f'{self.op_name}推进已发(免锚)')
            else:
                rs = self.round_retry(f'{self.op_name}推进已发,重入观察裁决',
                                      wait=1)
        self._lifecycle_mark('on_outcome')
        return rs
