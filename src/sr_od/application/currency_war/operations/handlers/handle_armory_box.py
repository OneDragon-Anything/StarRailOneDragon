"""货币战争 道具获得弹窗 op(「简易武装箱」类说明弹窗;2026-08-15 M19 首见停机建档,M20 实锤机制)。

机制(M20 17:37-18:05 实证,3 候选点击坐标全无反应 + × 关闭露底层屏):
- 弹窗 = **获得道具时的说明弹窗**(标题「简易武装箱」+ 说明「点击后开启…从四件简易装备中选择
  一件获得。该道具使用后消失」),叠在 3 选 1 屏(投资策略/环境)或备战上;
- 弹窗内**顶部箱图标是展示图不可点**((812,175)/(810,194)/(960,837) 三点全无反应);
- 正确动作 = **点 × 关闭**弹窗(道具进背包,备战界面箱槽走 HandleSupplyBox 开箱链路);
- 不关会挡死底层屏(M20 卡 19min/286 次 retry 实证)。

⚠️ M19 建档时曾按「点箱图标开箱→四选一」建模——错误(展示图不可点);M20 实锤后改关闭模型。
四选一逻辑不删:那是 HandleSupplyBox(备战箱槽)的职责,pick_box_card 公用函数保留。
"""
import time
from typing import ClassVar

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_observation import area_center
from sr_od.operations.sr_operation import SrOperation


class HandleArmoryBoxDialog(SrOperation):
    """道具获得说明弹窗:点 × 关闭 + 验弹窗消失(底层屏交还 loop 分支)。"""

    DIALOG_SCREEN: ClassVar[str] = '货币战争-武装箱弹窗'

    @operation_node(name='武装箱弹窗', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_find_area(
                screen, HandleArmoryBoxDialog.DIALOG_SCREEN, '标识-简易武装箱', crop_first=False).is_success:
            return self.round_fail('非武装箱弹窗')

        # 点 × 关闭(按钮-关闭 area;道具进背包,开箱走备战箱槽 HandleSupplyBox)
        _pt = area_center(self.ctx, '按钮-关闭', HandleArmoryBoxDialog.DIALOG_SCREEN)
        if _pt is None:
            return self.round_fail('武装箱弹窗缺「按钮-关闭」坐标')
        log.info(f'[cw-armbox] 关闭说明弹窗({_pt.x},{_pt.y})(道具入背包;开箱走备战箱槽)')
        self.ctx.controller.mouse_move(_pt)   # bug#1 缓解
        self.ctx.controller.click(_pt)
        time.sleep(1.0)

        # 验弹窗消失(标识不再命中 = 底层屏交还 loop)
        if self.round_by_find_area(
                self.screenshot(), HandleArmoryBoxDialog.DIALOG_SCREEN, '标识-简易武装箱',
                crop_first=False).is_success:
            log.info('[cw-armbox] 弹窗仍在 → retry')
            return self.round_retry(wait=1)
        log.info('[cw-armbox] 弹窗已关(底层屏交还 loop)')
        return self.round_success(wait=1.0)
