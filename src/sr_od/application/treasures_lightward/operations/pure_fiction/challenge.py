"""虚构叙事完整挑战(组合 op):编队选人 → 战意效果与荒腔走板装配 → 进入故事 →
节点战斗推进 → 结算返回。

子 op 按职责拆分(与末日幻影同构的组合模式):

- :class:`team_fill.TlPfTeamFillOp` 编队选人:清空两行 + 按目标填 8 人;
  起点 = 虚构叙事-编队,终点 = 编队屏(已填满)。
- :class:`buff_equip.TlPfBuffEquipOp` 增益装配:左栏战意效果单选 + 两行
  荒腔走板弹窗三选一装配;起点 = 编队屏(已填人),终点 = 编队屏(已装配)。
- :class:`battle.TlPfBattleOp` 节点战斗推进:进入故事 → 关卡简报关闭 →
  前进+秘技+开战 → 战斗等待 → 结算返回;起点 = 编队屏(已装配),终点 = 虚构叙事选关。
- :class:`TlPureFictionChallengeOp` 组合:入口多态 → 选人 → 装配 → 战斗推进。

前置:``GotoTreasuresLightward(TLMode.PURE_FICTION)`` 到虚构叙事选关 → 点目标
关卡纸鹤进编队屏后调用本 op(本 op 不做选关→编队的跳转)。

交互模型详见各子 op 模块 docstring(编队选人 / 增益装配 / 节点战斗)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.treasures_lightward.operations.pure_fiction.battle import (
    TlPfBattleOp,
)
from sr_od.application.treasures_lightward.operations.pure_fiction.buff_equip import (
    TlPfBuffEquipOp,
)
from sr_od.application.treasures_lightward.operations.pure_fiction.team_fill import (
    TlPfTeamFillOp,
)
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

_TEAM_SCREEN: str = '虚构叙事-编队'


class TlPureFictionChallengeOp(SrOperation):
    """虚构叙事完整挑战(组合 op):选人 → 增益装配 → 战斗推进 → 返回选关。"""

    STATUS_SUCCESS: ClassVar[str] = '挑战成功'

    def __init__(self, ctx: SrContext, team_names: list[str],
                 buff_slot: int = 1, buff_slots: list[int] | None = None):
        """
        Args:
            team_names: 按行(节点)顺序拼接的角色中文名列表,8 人(2 行×4);
                与脸库识别名一致,行 1 = 节点一队伍,行 2 = 节点二队伍。
            buff_slot: 左栏战意效果序号(1 基,按编队屏左栏可见列表上下序)。
            buff_slots: 每行荒腔走板增益序号(1 基,每行三选一,按卡片位置选择)。
        """
        SrOperation.__init__(self, ctx, op_name='虚构叙事 挑战')
        self.fill_op = TlPfTeamFillOp(ctx, team_names)
        self.equip_op = TlPfBuffEquipOp(ctx, buff_slot, buff_slots)
        self.battle_op = TlPfBattleOp(ctx)

    @operation_node(name='进入编队屏', is_start_node=True, node_max_retry_times=10)
    def _enter_team(self) -> OperationRoundResult:
        """确认在虚构叙事编队屏(前置:选关点关卡纸鹤,本 op 不做该跳转)。"""
        screen = self.last_screenshot
        if (self.round_by_find_area(screen, _TEAM_SCREEN, '标题-虚构叙事行').is_success
                and self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success):
            return self.round_success()
        return self.round_fail('不在虚构叙事编队屏(前置:选关点关卡纸鹤)')

    @node_from(from_name='进入编队屏')
    @operation_node(name='编队选人', node_max_retry_times=8)
    def _fill(self) -> OperationRoundResult:
        """组合 :class:`TlPfTeamFillOp`(清空 + 填 8 人,落位回验驱动)。"""
        op_result = self.fill_op.execute()
        return self.round_by_op_result(op_result)

    @node_from(from_name='编队选人')
    @operation_node(name='增益装配', node_max_retry_times=8)
    def _equip(self) -> OperationRoundResult:
        """组合 :class:`TlPfBuffEquipOp`(战意效果单选 + 荒腔走板装配)。"""
        op_result = self.equip_op.execute()
        return self.round_by_op_result(op_result)

    @node_from(from_name='增益装配')
    @operation_node(name='战斗推进', node_max_retry_times=8)
    def _battle(self) -> OperationRoundResult:
        """组合 :class:`TlPfBattleOp`(进入故事 → 秘技开战 → 战斗 → 结算返回)。"""
        op_result = self.battle_op.execute()
        return self.round_by_op_result(op_result)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.start_running()
    op = TlPureFictionChallengeOp(
        ctx,
        ['姬子•启行', '瓦尔特', '知更鸟', '丹恒•腾荒', '黄泉', '卡芙卡', '黑天鹅', '灵砂'],
    )
    op.execute()


if __name__ == '__main__':
    __debug()
