"""货币战争 阿哈装备选择 overlay op(空决策形态,A5)。

投资策略「阿哈大悦」装备选择(为阿哈选 1 件简易装备)overlay(0g)的
处理迁移:点第 1 装备自动关 overlay,无验效。**固定策略申报**:点首件 =
现行为(原分支注释「先关 overlay 推进」),按 key_equips 择优属策略面
后续批(契约改版另立,为它设 decide 接口 = 给无选择面
画面造空选择,违契约收缩方向)。背景:bot 不选 → overlay 持续
卡备战(2026-08-07 实跑 plane1 1-3 卡此 overlay 666s)。

首件点击坐标已 area 化(``货币战争-备战``/``按钮-简易装备首件``,矩形
中心 = 原 Point(626,250)「幸运星位」);原分支无 mouse_move,保持。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation;
推进型空决策骨架逐屏内联,无共享基类——模式一致即重复):观察 node =
入口锚门(「标识-简易装备」,与外循环 0g 分发判定同源同参;miss 未发 =
round_fail 交回外循环重判,「下一帧重判」是外循环职责)+ obs{on_screen}
挂实例属性(空决策形态无 report:本屏零容器写点,obs 类住
kernel/cw_screen_report/aha_equip_pick.py,import 构造即可)。决策动作
node = 重入裁决顶部(点首件已发 → 锚 miss = 已离开本画面 → success 交回
——出口 = 入口观察的合法重判,非动作层判效;锚在 = 再推进)→ area 读
「按钮-简易装备首件」+ click 单次推进 → round_wait 循环(不烧节点重试
预算,不收敛 = 动作 bug 响亮暴露,无防御上限;「推进动作未落地」=
round_fail 如实交回)。
"""
from cv2.typing import MatLike

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_screen_report.aha_equip_pick import (
    CwScreenAhaEquipPickObs,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenAhaEquipPick(SrOperation):
    """阿哈装备选择:点第 1 装备(固定策略申报,见模块头)。"""

    FIRST_EQUIP_AREA = '按钮-简易装备首件'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-阿哈装备选择')
        # 画面档名/入口锚(与外循环 0g 分发判定同源同参;实例属性)
        self._screen_name: str = '货币战争-备战'
        self._entry_area: str = '标识-简易装备'
        # 推进已发标志(验证废除形态):区分「首发锚 miss = 误分发 fail 交回」
        # 与「重入锚 miss = 已离开本画面 success 交回」(实例级,单 op 生命周期)。
        self._advanced_once: bool = False
        # 观察结果(观察 node 产物,决策动作 node 消费;空决策形态无 report)。
        self._obs: CwScreenAhaEquipPickObs | None = None

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
        self._obs = CwScreenAhaEquipPickObs(on_screen=True, screen=screen)
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
        """推进处理:读「按钮-简易装备首件」center → click(缺失 = False
        如实交回;原分支无 mouse_move,保持)。"""
        first = area_center(self.ctx, self.FIRST_EQUIP_AREA, self._screen_name)
        if first is None:
            return False
        self.ctx.controller.click(first)
        return True
