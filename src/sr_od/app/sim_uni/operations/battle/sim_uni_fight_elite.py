import time
from typing import ClassVar, Optional

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.app.sim_uni.operations.sim_uni_enter_fight import SimUniEnterFight
from sr_od.app.sim_uni.sim_uni_challenge_config import SimUniChallengeConfig
from sr_od.context.sr_context import SrContext
from sr_od.operations.battle.start_fight_for_elite import StartFightForElite
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.team.switch_member import SwitchMember


class SimUniFightElite(SrOperation):

    STATUS_ENEMY_NOT_FOUND: ClassVar[str] = '没有敌人'

    def __init__(self, ctx: SrContext, config: Optional[SimUniChallengeConfig] = None):
        """
        模拟宇宙 - 挑战精英、首领
        """
        SrOperation.__init__(self, ctx,
                             op_name='%s %s' % (
                                 gt('模拟宇宙', 'game'),
                                 gt('挑战精英首领'),
                             ),
                             )
        self.config: Optional[SimUniChallengeConfig] = ctx.sim_uni_challenge_config if config is None else config

    @operation_node(name='检测敌人', is_start_node=True)
    def _check_enemy(self) -> OperationRoundResult:
        """
        判断当前是否有敌人
        :return:
        """
        now = time.time()
        screen = self.screenshot()
        result = self.round_by_find_area(screen, '模拟宇宙', '怪物上方等级')

        if result.is_success:
            return self.round_success(status=result.status)

        # 使用 YOLO 判断红色锁定
        if self.ctx.yolo_detector.should_attack_in_world(screen, now):
            return self.round_success(status="检测到攻击锁定")

        return self.round_retry(SimUniFightElite.STATUS_ENEMY_NOT_FOUND, wait=1)

    @node_from(from_name='检测敌人')
    @operation_node(name='秘技进入战斗')
    def _technique_fight(self) -> OperationRoundResult:
        op = StartFightForElite(self.ctx)
        return self.round_by_op_result(op.execute(), wait=1)

    @node_from(from_name='秘技进入战斗')
    @node_from(from_name='秘技进入战斗', success=False)
    @operation_node(name='战斗')
    def _fight(self) -> OperationRoundResult:
        screen = self.screenshot()
        result = self.round_by_find_area(screen, '模拟宇宙', '怪物上方等级')
        if result.is_success:  # 还没有进入战斗 可能是使用近战角色没有攻击到
            self.ctx.controller.initiate_attack()
            return self.round_retry('尝试攻击进入战斗画面', wait=1)
        else:
            op = SimUniEnterFight(self.ctx, config=self.config, no_attack=True)  # 前面已经进行攻击了 这里不需要 且不额外使用秘技
            return self.round_by_op_result(op.execute())

    @node_from(from_name='检测敌人', status=STATUS_ENEMY_NOT_FOUND, success=False)
    @node_from(from_name='战斗')
    @operation_node(name='切换1号位')
    def _switch_1(self) -> OperationRoundResult:
        op = SwitchMember(self.ctx, 1)
        return self.round_by_op_result(op.execute())
