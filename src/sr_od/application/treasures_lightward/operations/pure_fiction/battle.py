"""虚构叙事节点战斗推进:进入故事 → 简报关闭 → 前进+秘技+开战 → 战斗等待 → 结算返回。

起点 = 虚构叙事-编队屏(已装配);终点 = 结算「返回虚构叙事」后到达选关。"""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.treasures_lightward.obs.tl_team_common import (
    get_area_center_point,
)
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.technique import UseTechnique

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

_SELECT_SCREEN: str = '逐光捡金'
_TEAM_SCREEN: str = '虚构叙事-编队'
_NODE_SCREEN: str = '忘却之庭-节点画面'  # 节点画面左栏锚(查看详情)与 FH 同构,复用其 area


class TlPfBattleOp(SrOperation):
    """节点战斗推进:进入故事 → 简报关闭 → 前进+秘技+开战 → 战斗等待 → 结算返回。

    起点 = 虚构叙事-编队屏(已装配);终点 = 结算「返回虚构叙事」后到达选关。"""

    STATUS_DONE: ClassVar[str] = '挑战完成'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='虚构叙事 节点战斗')
        self._tech_used: bool = False  #: 当前节点秘技已施放(节点自动衔接共 2 节点
                                       #  一场连续战斗,全程只需一次)

    @operation_node(name='进入故事', is_start_node=True, node_max_retry_times=10)
    def _start(self) -> OperationRoundResult:
        """点「进入故事」→ 到达验证:关卡简报横幅或节点画面出现。"""
        screen = self.last_screenshot
        if (self.round_by_find_area(screen, _SELECT_SCREEN, 'NODE_FIRST_CLICK_EMPTY').is_success
                or self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success):
            return self.round_success()
        if self.round_by_find_area(screen, _TEAM_SCREEN, '按钮-进入故事').is_success:
            self.ctx.controller.click(
                get_area_center_point(self.ctx, _TEAM_SCREEN, '按钮-进入故事'),
                press_time=0.2)
            return self.round_retry('点击进入故事', wait=2)
        return self.round_retry('画面异常(既非编队屏也未见简报/节点)', wait=1.5)

    @node_from(from_name='进入故事')
    @operation_node(name='关卡简报处理', node_max_retry_times=8)
    def _brief(self) -> OperationRoundResult:
        """关卡简报横幅(本期战斗机制说明页)→ 点空白关闭;节点画面 → 进入战斗循环。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'NODE_FIRST_CLICK_EMPTY').is_success:
            self.ctx.controller.click(
                get_area_center_point(self.ctx, _SELECT_SCREEN, '区域-简报空白关闭点'),
                press_time=0.15)
            return self.round_wait('关闭关卡简报', wait=2)
        if self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success:
            return self.round_success()
        return self.round_retry('等待节点画面', wait=1.5)

    @node_from(from_name='关卡简报处理')
    @operation_node(name='节点战斗循环', node_max_retry_times=360)
    def _battle_loop(self) -> OperationRoundResult:
        """单循环按画面特征每轮分流:结算 → 收尾;待命 → 秘技开战;其余 → 战斗中等待。

        待命态判据 = 节点画面左栏「查看详情」(PF 与 FH 节点画面同构);
        战斗中左栏被战斗 UI 替换故不误判。节点间自动衔接(游戏自动切队伍到
        下一节点出生点),一场连续战斗,秘技全程施放一次。"""
        screen = self.last_screenshot

        if (self.round_by_find_area(screen, _SELECT_SCREEN, 'PF_AFTER_BATTLE_SUCCESS_1').is_success
                or self.round_by_find_area(screen, _SELECT_SCREEN, 'PF_AFTER_BATTLE_SUCCESS_2').is_success):
            return self.round_success(TlPfBattleOp.STATUS_DONE)
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'PF_AFTER_BATTLE_FAIL').is_success:
            return self.round_fail('战斗失败')

        if self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success:
            if not self._tech_used:
                # 未施秘技:前进接近后施放(攻击型秘技施放即入战斗,本轮结束
                # 重新分流走战斗等待;增益型下一轮走到点击开战分支)
                self.ctx.controller.move('w', press_time=2)
                tech_op = UseTechnique(self.ctx)
                tech_op.execute()
                self._tech_used = True
                return self.round_retry('施放秘技', wait=3)
            # 秘技已施放:前进 + 框架标准开战(initiate_attack = 点击画面中心)
            self.ctx.controller.move('w', press_time=2)
            self.ctx.controller.initiate_attack()
            return self.round_retry('发起战斗', wait=5)

        # 战斗中等待(一局 2 节点 6 波正常 ~60 轮内,360 轮 = 30 分钟兜底退出)
        return self.round_retry('战斗进行中', wait=5)

    @node_from(from_name='节点战斗循环', status=STATUS_DONE)
    @operation_node(name='返回虚构叙事', node_max_retry_times=12)
    def _click_back(self) -> OperationRoundResult:
        """结算画面点「返回虚构叙事」→ 虚构叙事选关。

        首次 3 星通关会弹「快速通关」确认(视同通关所有前置难度,点确认领取),
        先处理再判定到达选关。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'PF_TITLE').is_success:
            return self.round_success()
        if self.round_by_find_area(
                screen, _SELECT_SCREEN, '按钮-快速通关确认').is_success:
            self.ctx.controller.click(
                get_area_center_point(self.ctx, _SELECT_SCREEN, '按钮-快速通关确认'),
                press_time=0.15)
            return self.round_wait('领取快速通关奖励', wait=2)
        click = self.round_by_find_and_click_area(
            screen, _SELECT_SCREEN, 'PF_AFTER_BATTLE_BACK_BTN', success_wait=2)
        if click.is_success:
            return self.round_wait('返回虚构叙事中', wait=1.5)
        return self.round_retry('未找到返回按钮', wait=1)
