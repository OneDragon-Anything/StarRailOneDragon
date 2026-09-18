
"""货币战争 出战确认弹窗(「可出战角色人数未达上限」)处理 op(从主循环拆出)。

勾「本局不再提示」+ 确认,解除 bench-full 警告阻塞出战。

勾选/确认坐标进 screen_info(``currency_war_deploy_not_full``):``勾选-本局不再提示`` +
``按钮-确认``,task#20 已完成;本 op 经 ``cw_obs_core.area_center`` 读,缺失才用兜底常量。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation,
轻屏统一形态):观察 node = 标识门(id_mark「标识-未达上限警告」,miss
未发 = round_fail 交编排壳按步分流)+ 门内 obs{on_screen} → 调占位
``report_screen_deploy_not_full_obs``(统一形态;本屏现役零容器写点,
接口为占位,match/gs 缺席跳过)→ obs 挂实例属性进决策 node。决策动作
node = 重入裁决顶部(确认已发 → 锚不在 = 弹窗已关 → success 交回;锚在
= 确认未落地 → 重做勾选确认)→ 勾「勾选-本局不再提示」safe_click+0.3s
→ 确认 emit_overlay_confirm → 置位 → round_wait 循环推进(不烧节点重试
预算;不收敛 = 动作 bug 响亮暴露,无防御上限)。原单 node 形态「miss
分支内先查 pending 后 fail」的裁决位序随两 node 拆分自然消解(门在观察
node 先行,裁决住决策 node 顶部;判据红线 = id_mark「标识-未达上限警告」
位置区分,防「能量上限」共享「上限」误匹配,原注释原位保留)。本屏
sim 腿 = 不适用(sim 无对应画面段),等价判据主承重 = 实机在册行为锁
(test_cw_obs_arch_closing_screens.py)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_screen_report.deploy_not_full import (
    CwScreenDeployNotFullObs,
    report_screen_deploy_not_full_obs,
)
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    emit_overlay_confirm,
    safe_click,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenDeployNotFull(SrOperation):
    """出战人数未达上限弹窗:勾本局不再提示 + 确认。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-未达上限警告'   # screen_info 画面(currency_war_deploy_not_full.yml)
    # 勾选/确认:screen_info center(task#20);常量=screen_info 缺失兜底。
    CHECKBOX_NO_PROMPT: ClassVar[Point] = Point(912, 589)   # 兜底;首选 area_center('勾选-本局不再提示')
    BTN_CONFIRM: ClassVar[Point] = Point(1159, 653)          # 兜底;首选 area_center('按钮-确认')

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-未达上限确认')
        # 确认已发待重入裁决标志(单 op 生命周期):区分「首发锚 miss = 误分发
        # fail 交回」与「重入锚 miss = 弹窗已关 success 交回」(验证废除形态:
        # 用户裁定 2026-09-10 动作 op 禁验证,落地由下一轮重入入口观察裁决)。
        self._confirm_pending: bool = False
        # 观察结果(观察 node 产物;门早退轮不装载)。
        self._obs: CwScreenDeployNotFullObs | None = None

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """标识门 + obs{on_screen} → 占位 report 接线。

        门 miss = round_fail 早退交编排壳按步分流(现役首闸同 status);
        门 hit → obs 装载 + 占位 report(match/gs 缺席跳过)。"""
        screen = self.last_screenshot
        # 用 screen_info id_mark area(标识-未达上限警告)位置区分,非全屏 LCS:防「能量上限」(投资策略描述)
        # 与「未达上限」共享「上限」(2/4=0.5)误匹配(见 cw_loop 0d)。area 位置不同 → 不命中。
        if not self.round_by_find_area(
                screen, CwScreenDeployNotFull.SCREEN_NAME,
                '标识-未达上限警告').is_success:
            return self.round_fail('非未达上限弹窗')
        obs = CwScreenDeployNotFullObs(on_screen=True, screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_deploy_not_full_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=10)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 勾选 + 确认 → round_wait。

        重入裁决(观察驱动,验证废除形态):上轮确认已发 → 锚不在 = 弹窗
        已关(落地与否归下一帧观察侧重分发;此处只认「本画面处理完结」)
        → success 交回;锚在 = 确认未落地 → 重做勾选确认。循环推进 =
        round_wait(不烧节点重试预算;不收敛 = 动作 bug 响亮暴露,无防御
        上限)。"""
        if self._confirm_pending:
            self._confirm_pending = False
            if not self.round_by_find_area(
                    self.last_screenshot, CwScreenDeployNotFull.SCREEN_NAME,
                    '标识-未达上限警告').is_success:
                return self.round_success('未达上限弹窗已关(重入观察裁决)', wait=3.0)
        return self._confirm_and_dismiss()

    def _confirm_and_dismiss(self) -> OperationRoundResult:
        """勾选 + 确认体:勾「勾选-本局不再提示」(``safe_click``+0.3s)→ 确认
        (``emit_overlay_confirm``)→ 置位(落地判定归下一轮重入裁决)→
        round_wait 循环推进。"""
        _check = area_center(self.ctx, '勾选-本局不再提示', CwScreenDeployNotFull.SCREEN_NAME) or CwScreenDeployNotFull.CHECKBOX_NO_PROMPT
        _confirm = area_center(self.ctx, '按钮-确认', CwScreenDeployNotFull.SCREEN_NAME) or CwScreenDeployNotFull.BTN_CONFIRM
        safe_click(self, _check, tag='cw-deploywarn')
        time.sleep(0.3)
        # 确认 + 机械交回(验证废除:不读屏判「弹窗关没关」,落地由下一轮重入
        # 入口观察裁决;锚仍在 = 重做一次)。原「点了就 success」
        # 不观察 → bug#1/勾选未生效 flat-loop 防线由重入裁决承接。
        self._confirm_pending = True
        emit_overlay_confirm(self, confirm_point=_confirm, entry_keyword='未达上限',
                             lcs_percent=0.8, success_wait=3.0, tag='cw-deploywarn')
        return self.round_wait(wait=1)
