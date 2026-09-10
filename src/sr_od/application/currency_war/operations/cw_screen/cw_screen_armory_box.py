"""货币战争 道具获得弹窗 op(「简易武装箱」类说明弹窗;2026-08-15 M19 首见停机建档,M20 实锤机制)。

机制(M20 17:37-18:05 实证,3 候选点击坐标全无反应 + × 关闭露底层屏):
- 弹窗 = **获得道具时的说明弹窗**(标题「简易武装箱」+ 说明「点击后开启…从四件简易装备中选择
  一件获得。该道具使用后消失」),叠在 3 选 1 屏(投资策略/环境)或备战上;
- 弹窗内**顶部箱图标是展示图不可点**((812,175)/(810,194)/(960,837) 三点全无反应);
- 正确动作 = **点 × 关闭**弹窗(道具进背包,备战界面箱槽走 prep_actions 的
  OpenBox→PickBoxCard 开箱链路);
- 不关会挡死底层屏(M20 卡 19min/286 次 retry 实证)。

⚠️ M19 建档时曾按「点箱图标开箱→四选一」建模——错误(展示图不可点);M20 实锤后改关闭模型。
四选一选卡职责在备战箱槽链(prep_actions.PrepActionExecutor._pick_box_card),本 op 只关弹窗。
"""
import time
from typing import ClassVar

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenArmoryBox(SrOperation):
    """道具获得说明弹窗:点 × 关闭 + 重入观察裁决交回(验证废除)。"""

    DIALOG_SCREEN: ClassVar[str] = '货币战争-武装箱弹窗'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-武装箱弹窗')
        # 点 × 已发待重入裁决标志(验证废除形态):标识不在 + 已发 = 弹窗已关
        #(道具进背包)→ success 交回;标识在 = 重点(计节点预算)。
        self._click_pending: bool = False

    @operation_node(name='武装箱弹窗', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        _hit = self.round_by_find_area(
            screen, CwScreenArmoryBox.DIALOG_SCREEN, '标识-简易武装箱', crop_first=False).is_success
        # 重入裁决(观察驱动):上轮点 × 已发 → 标识不在 = 弹窗已关(底层屏
        # 交还 loop)→ success;标识在 = 点击未落地 → 重点。
        if self._click_pending:
            self._click_pending = False
            if not _hit:
                log.info('[cw-armbox] 弹窗已关(重入观察裁决,底层屏交还 loop)')
                return self.round_success(wait=1.0)
        if not _hit:
            return self.round_fail('非武装箱弹窗')

        # 点 × 关闭(按钮-关闭 area;道具进背包,开箱走备战箱槽 OpenBox 链路)
        _pt = area_center(self.ctx, '按钮-关闭', CwScreenArmoryBox.DIALOG_SCREEN)
        if _pt is None:
            return self.round_fail('武装箱弹窗缺「按钮-关闭」坐标')
        log.info(f'[cw-armbox] 关闭说明弹窗({_pt.x},{_pt.y})(道具入背包;开箱走备战箱槽)')
        self.ctx.controller.mouse_move(_pt)   # bug#1 缓解
        self.ctx.controller.click(_pt)
        time.sleep(1.0)
        # 机械交回(验证废除):弹窗消失与否由下一轮重入观察裁决(本方法顶部)。
        self._click_pending = True
        return self.round_retry('点 × 已发,重入观察裁决', wait=1)
