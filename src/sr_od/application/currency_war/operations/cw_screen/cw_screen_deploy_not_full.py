
"""货币战争 出战确认弹窗(「可出战角色人数未达上限」)处理 op(从主循环拆出)。

勾「本局不再提示」+ 确认,解除 bench-full 警告阻塞出战。

勾选/确认坐标进 screen_info(``currency_war_deploy_not_full``):``勾选-本局不再提示`` +
``按钮-确认``,task#20 已完成;本 op 经 ``cw_obs_core.area_center`` 读,缺失才用兜底常量。

统一观察架构逐屏迁移(收尾五屏;架构设计 §9.1 并存纪律):本类是
CwScreenOpBase 子类,handle 顶部装配点分流(重入裁决**之后**,先例锚 =
cw_screen_encounter.py :241-251 重入裁决 / :252-258 装配点分流;总纲契约 6):
cw_game_ports 两端口完整在场 → 五段生命周期新路径;缺省 None = 生产直连
旧路径(原序列,生产行为零变化)。五段形态:observe = 标识门(miss 未发 →
fail;命中 → 清旗标)+ 帧引用(实机适配器① = 轻观察封口,简报屏同式;
重入裁决不在本段,总纲契约 6:留守 handle 分流前共享段);reconcile = 空申
报;decide+act 内聚 ``_confirm_and_dismiss``(勾「勾选-本局不再提示」
safe_click+0.3s → 确认 emit_overlay_confirm → 置位,两路径共享零转录);
on_outcome = 无登记件(注册表缺席 = 零动作,__init__ 申报)。本屏裁决位序
= miss 分支内先查 pending 后 fail(与位面过渡/武装箱的 pending 先行序不同,
逐字保真禁统一,收尾屏详设 §3;判据红线 = id_mark「标识-未达上限警告」
位置区分,防「能量上限」共享「上限」误匹配,原注释原位保留)。本屏 sim 腿
= 不适用(F11 例外清单:sim 无对应画面段),等价判据主承重 = 实机在册行为
锁 + 新路径行为锁(test_cw_obs_arch_closing_screens.py)。
"""
import time
from dataclasses import dataclass
from typing import Any, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.cw_game_ports import action_sink, observation_source
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    emit_overlay_confirm,
    safe_click,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_op_base import (
    CwScreenOpBase,
)
from sr_od.context.sr_context import SrContext


@dataclass
class DeployNotFullObservation:
    """未达上限弹窗观察 payload(五段之段1产物;实机转录形态)。

    中断弹窗族轻观察(收尾屏详设 §3):标识门判定在段内(门失败 →
    round_fail 早退交编排壳按步分流);payload 仅携带稳定帧引用(实机
    识别域载体,不出端口——sim 适配器落位时该域 = None 帧语义,F11
    例外清单本批不建)。
    """

    screen: Any = None


class DeployNotFullLiveObservationAdapter:
    """实机适配器①(观察端口;架构设计 §2.3 识别链封口)。

    轻观察封口(先例 = 简报屏轻观察适配器):标识门须在段内产出早退
    轮次,归 ``lifecycle_observe``;适配器仅装配稳定帧引用。sim 实现 =
    不适用(F11 例外清单),本批不建。
    """

    def observe(self, op: 'CwScreenDeployNotFull') -> DeployNotFullObservation:
        return DeployNotFullObservation(screen=op.last_screenshot)


class CwScreenDeployNotFull(CwScreenOpBase):
    """出战人数未达上限弹窗:勾本局不再提示 + 确认。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-未达上限警告'   # screen_info 画面(currency_war_deploy_not_full.yml)
    # 勾选/确认:screen_info center(task#20);常量=screen_info 缺失兜底。
    CHECKBOX_NO_PROMPT: ClassVar[Point] = Point(912, 589)   # 兜底;首选 area_center('勾选-本局不再提示')
    BTN_CONFIRM: ClassVar[Point] = Point(1159, 653)          # 兜底;首选 area_center('按钮-确认')

    def __init__(self, ctx: SrContext):
        CwScreenOpBase.__init__(self, ctx, op_name='货币战争-未达上限确认')
        # 适配器位缺省装配(先例 = 五相位屏):观察口 = 实机适配器
        #(轻观察封口);动作口 = None = 直连现役确认链(基类「None = 子类
        # 缺省实现自担」)。on_outcome 注册表:本屏无登记件(注册表缺席 =
        # 零动作)。
        self._observation_adapter = DeployNotFullLiveObservationAdapter()
        # 确认已发待重入裁决标志(单 op 生命周期):区分「首发锚 miss = 误分发
        # fail 交回」与「重入锚 miss = 弹窗已关 success 交回」(验证废除形态:
        # 用户裁定 2026-09-10 动作 op 禁验证,落地由下一轮重入入口观察裁决)。
        self._confirm_pending: bool = False

    @operation_node(name='未达上限确认', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # 用 screen_info id_mark area(标识-未达上限警告)位置区分,非全屏 LCS:防「能量上限」(投资策略描述)
        # 与「未达上限」共享「上限」(2/4=0.5)误匹配(见 cw_loop 0d)。area 位置不同 → 不命中。
        _hit = self.round_by_find_area(
            screen, CwScreenDeployNotFull.SCREEN_NAME, '标识-未达上限警告').is_success
        # 重入裁决(观察驱动):上轮确认已发 → 锚不在 = 弹窗已关(落地与否归
        # 下一帧观察侧重分发;此处只认「本画面处理完结」)。两路径共用(分流
        # 前挂,先于五段 lifecycle 的 observe 门;总纲契约 6)。裁决位序 = miss
        # 分支内先查 pending 后 fail(与位面过渡/武装箱序不同,逐字保真禁统一)。
        if not _hit:
            if self._confirm_pending:
                self._confirm_pending = False
                return self.round_success('未达上限弹窗已关(重入观察裁决)', wait=3.0)
        # 装配点分流(统一观察架构 §9.1 并存期;先例 = CwScreenPrep.run/
        # CwScreenEncounter.handle):两端口完整在场(= 测试 harness 显式装配)
        # → 五段生命周期新路径;缺省 None = 生产直连旧路径(下方原序列,
        # 生产行为零变化)。
        if observation_source() is not None and action_sink() is not None:
            return self.run_lifecycle()
        # 旧路径原序列(§9.1 并存期逐位保留):
        if not _hit:
            return self.round_fail('非未达上限弹窗')
        self._confirm_pending = False
        return self._confirm_and_dismiss()

    def _confirm_and_dismiss(self) -> OperationRoundResult:
        """勾选 + 确认体(五段 decide+act 两路径共享零转录;旧 handle :54-63
        逐位平移):勾「勾选-本局不再提示」(``safe_click``+0.3s)→ 确认
        (``emit_overlay_confirm``,success_wait=3.0)→ 置位(落地判定归
        下一轮重入裁决)。"""
        _check = area_center(self.ctx, '勾选-本局不再提示', CwScreenDeployNotFull.SCREEN_NAME) or CwScreenDeployNotFull.CHECKBOX_NO_PROMPT
        _confirm = area_center(self.ctx, '按钮-确认', CwScreenDeployNotFull.SCREEN_NAME) or CwScreenDeployNotFull.BTN_CONFIRM
        safe_click(self, _check, tag='cw-deploywarn')
        time.sleep(0.3)
        # 确认 + 机械交回(验证废除:不读屏判「弹窗关没关」,落地由下一轮重入
        # 入口观察裁决;锚仍在 = 重做一次,计节点预算)。原「点了就 success」
        # 不观察 → bug#1/勾选未生效 flat-loop 防线由重入裁决 + 预算耗尽 bail 承接。
        self._confirm_pending = True
        return emit_overlay_confirm(self, confirm_point=_confirm, entry_keyword='未达上限',
                                    lcs_percent=0.8, success_wait=3.0, tag='cw-deploywarn')

    # ---- 五段生命周期(统一观察架构 §5.1;先例 = 简报屏)----

    def lifecycle_observe(self
                          ) -> tuple[DeployNotFullObservation,
                                     OperationRoundResult | None]:
        """段1 observe:标识门(id_mark「标识-未达上限警告」miss 未发 →
        round_fail 早退交编排壳按步分流;命中 → 清旗标,旧 handle :53 逐位)
        → 轻观察 payload。重入裁决不在本段(总纲契约 6:留守 handle 分流前
        共享段;裁决位序 = miss 分支内先查 pending 后 fail)。"""
        _adp = self._observation_port()
        obs = (_adp.observe(self) if _adp is not None
               else DeployNotFullObservation(screen=self.last_screenshot))
        _hit = self.round_by_find_area(
            self.last_screenshot, CwScreenDeployNotFull.SCREEN_NAME,
            '标识-未达上限警告').is_success
        if not _hit:
            return obs, self.round_fail('非未达上限弹窗')
        self._confirm_pending = False
        return obs, None

    def lifecycle_decision_cycle(self, payload: DeployNotFullObservation
                                 ) -> OperationRoundResult:
        """段3-5(单动作决策循环):decide+act 内聚 ``_confirm_and_dismiss``
        (勾选 + 确认体,两路径共享零转录);on_outcome = 本屏无登记件
        (注册表缺席 = 零动作,__init__ 申报)。轮次终结出口 = 机械交回
        (emit_overlay_confirm 的 retry 形态;落地判定归下一轮重入裁决,
        验证废除形态)。"""
        self._lifecycle_mark('decide')
        self._lifecycle_mark('act')
        rs = self._confirm_and_dismiss()
        self._lifecycle_mark('on_outcome')
        return rs
