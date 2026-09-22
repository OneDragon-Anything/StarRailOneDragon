"""货币战争 道具获得弹窗 op(「简易武装箱」类说明弹窗;2026-08-15 M19 首见停机建档,M20 实锤机制)。

机制(M20 17:37-18:05 实证,3 候选点击坐标全无反应 + × 关闭露底层屏):
- 弹窗 = **获得道具时的说明弹窗**(标题「简易武装箱」+ 说明「点击后开启…从四件简易装备中选择
  一件获得。该道具使用后消失」),叠在 3 选 1 屏(投资策略/环境)或备战上;
- 弹窗内**顶部箱图标是展示图不可点**((812,175)/(810,194)/(960,837) 三点全无反应);
- 正确动作 = **点 × 关闭**弹窗(道具进背包,备战界面箱槽走 prep_actions 的
  CwActionOpenBoxParam 开箱链路;四选一选卡职责在独立画面 op
  ``cw_screen_box_pick.py::CwScreenBoxPick``,本 op 只关弹窗);
- 不关会挡死底层屏(M20 卡 19min/286 次 retry 实证)。

形态(迭代 2026-09-18-screen-op-flat-report):观察 node + 决策动作 node 两段
直继承 SrOperation(轻屏统一形态)。观察 node = 标识门(id_mark「标识-简易
武装箱」,miss 未发 = round_fail 交编排壳按步分流)+ obs{on_screen} → 调
占位 ``report_screen_armory_box_obs``(统一形态;本屏现役零容器写点,接口
为占位,match/gs 缺席跳过)→ obs 挂实例属性进决策 node。决策动作 node =
重入裁决顶部(点 × 已发 → 锚不在 = 弹窗已关(道具进背包)→ success 交回;
锚在 = 点击未落地 → 重点)→ 点 × 关闭 → ``round_wait`` 循环推进(不烧节点
重试预算;不收敛 = 动作 bug 响亮暴露,无防御上限)。本屏 sim 腿 = 不适用(sim 无对应画面段),
等价判据主承重 = 实机在册行为锁。
"""
import time
from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_screen_report.armory_box import (
    CwScreenArmoryBoxObs,
    report_screen_armory_box_obs,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenArmoryBox(SrOperation):
    """道具获得说明弹窗:点 × 关闭 + 重入观察裁决交回(验证废除)。"""

    DIALOG_SCREEN: ClassVar[str] = '货币战争-武装箱弹窗'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-武装箱弹窗')
        # 点 × 已发待重入裁决标志(验证废除形态):锚不在 + 已发 = 弹窗已关
        #(道具进背包)→ success 交回;锚在 = 点击未落地 → 重点。
        self._click_pending: bool = False
        # 观察结果(观察 node 产物,决策动作 node 消费)。
        self._obs: CwScreenArmoryBoxObs | None = None

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """标识门 + obs{on_screen} → 占位 report 接线。

        门 miss = round_fail 早退交编排壳按步分流(现役首闸同 status)。
        门 hit → obs 装载 + ``report_screen_armory_box_obs`` 占位调用(本屏
        现役零容器写点,接口为统一形态占位;match/gs 缺席跳过)。"""
        screen = self.last_screenshot
        _hit = self.round_by_find_area(
            screen, CwScreenArmoryBox.DIALOG_SCREEN, '标识-简易武装箱', crop_first=False).is_success
        if not _hit:
            return self.round_fail('非武装箱弹窗')
        obs = CwScreenArmoryBoxObs(on_screen=True, screen=screen)
        _match = getattr(self.ctx, 'cw_match', None)
        _gs = getattr(_match, 'gs', None) if _match is not None else None
        if _gs is not None:
            report_screen_armory_box_obs(_gs, obs)
        self._obs = obs
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=8)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 点 × 关闭 → round_wait。

        重入裁决(观察驱动,验证废除形态):上轮点 × 已发 → 锚不在 = 弹窗
        已关(底层屏交还 loop)→ success;锚在 = 点击未落地 → 清标志重点。
        循环推进 = round_wait(不烧节点重试预算;不收敛 = 动作 bug 响亮
        暴露,无防御上限)。"""
        if self._click_pending:
            self._click_pending = False
            if not self.round_by_find_area(
                    self.last_screenshot, CwScreenArmoryBox.DIALOG_SCREEN,
                    '标识-简易武装箱', crop_first=False).is_success:
                log.info('[cw-armbox] 弹窗已关(重入观察裁决,底层屏交还 loop)')
                return self.round_success(wait=1.0)
        return self._close_dialog()

    def _close_dialog(self) -> OperationRoundResult:
        """点 × 关闭体:读「按钮-关闭」center(缺失 → fail 缺坐标;道具进背包,
        开箱走备战箱槽 CwActionOpenBoxParam 链路)→ mouse_move+click+1s → 置位
        (落地判定归下一轮重入裁决)。"""
        _pt = area_center(self.ctx, '按钮-关闭', CwScreenArmoryBox.DIALOG_SCREEN)
        if _pt is None:
            return self.round_fail('武装箱弹窗缺「按钮-关闭」坐标')
        log.info(f'[cw-armbox] 关闭说明弹窗({_pt.x},{_pt.y})(道具入背包;开箱走备战箱槽)')
        self.ctx.controller.mouse_move(_pt)   # 防吞点击(截图前移光标)
        self.ctx.controller.click(_pt)
        time.sleep(1.0)
        # 机械交回(验证废除):弹窗消失与否由下一轮重入观察裁决(act 顶部)。
        self._click_pending = True
        return self.round_wait('点 × 已发,重入观察裁决', wait=1)
