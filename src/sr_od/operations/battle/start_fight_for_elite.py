from typing import ClassVar, Optional, List

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.config.character_const import Character, TECHNIQUE_BUFF, TECHNIQUE_AREA, TECHNIQUE_ATTACK, \
    is_attack_character, TECHNIQUE_BUFF_ATTACK, SILVERWOLF, TECHNIQUE_BUFF_ATTACK_DISAPPEAR
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.team.check_team_members_in_world import CheckTeamMembersInWorld
from sr_od.operations.team.switch_member import SwitchMember
from sr_od.operations.technique import CheckTechniquePoint, UseTechnique, UseTechniqueResult
from sr_od.screen_state import common_screen_state


class StartFightForElite(SrOperation):

    STATUS_DONE: ClassVar[str] = '使用完毕'

    def __init__(self, ctx: SrContext,
                 character_list: Optional[List[Character]] = None,
                 skip_point_check: bool = False,
                 skip_resurrection_check: bool = False):
        """
        对不会主动攻击的精英怪开战 上BUFF之后进入战斗
        优先使用上BUFF不触发战斗的秘技 最后再使用开战技能
        适用于
        - 逐光捡金
        - 模拟宇宙 精英怪
        :param ctx:
        :param character_list: 当前配队 无传入时自动识别 但不准
        :param skip_point_check: 跳过使用秘技时检测秘技点 逐光捡金可用
        :param skip_resurrection_check: 跳过切换角色时检测复活 逐光捡金可用
        """
        SrOperation.__init__(self, ctx, op_name=gt('使用秘技 进入战斗'),)
        self.character_list_from_param: Optional[List[Character]] = character_list
        self.character_list: List[Character] = []
        self.technique_order: List[int] = []
        self.need_attack_finally: bool = True  # 最后需要攻击
        self.skip_point_check: bool = skip_point_check  # 跳过检测秘技点
        self.technique_point: int = 5  # 秘技点
        self.technique_idx: int = 0  # 当前到哪一个角色使用
        self.skip_resurrection_check: bool = skip_resurrection_check  # 跳过切换角色时检测复活

    def handle_init(self) -> Optional[OperationRoundResult]:
        """
        执行前的初始化 由子类实现
        注意初始化要全面 方便一个指令重复使用
        可以返回初始化后判断的结果
        - 成功时跳过本指令
        - 失败时立刻返回失败
        - 不返回时正常运行本指令
        """
        self.character_list = []
        self.technique_order = []
        self.need_attack_finally = True
        self.technique_idx: int = 0  # 当前到哪一个角色使用

        return None

    @node_from(from_name='获取施放顺序')
    @operation_node(name='检测秘技点')
    def _check_technique_point(self) -> OperationRoundResult:
        """
        检测秘技点 并固定
        :return:
        """
        if self.skip_point_check:
            self.technique_point = 5
        else:
            op = CheckTechniquePoint(self.ctx)
            op_result = op.execute()
            if op_result.success:
                self.technique_point = op_result.data
            else:
                self.technique_point = 0  # 识别失败时直接认为是0

        # 秘技点不够的时候 减少使用
        if self.technique_point < len(self.technique_order):
            self.technique_order = self.technique_order[:self.technique_point]

        log.info(f'最后秘技顺序 {self.technique_order}')
        return self.round_success()

    @operation_node(name='获取角色列表', is_start_node=True)
    def _get_character_list(self) -> OperationRoundResult:
        """
        获取当前队伍的角色
        :return:
        """
        if self.character_list_from_param is None:
            op = CheckTeamMembersInWorld(self.ctx)
            op_result = op.execute()
            if op_result.success:
                self.character_list = self.ctx.team_info.character_list
            return self.round_by_op_result(op_result)
        else:
            for c in self.character_list_from_param:
                self.character_list.append(c)

            return self.round_success()

    @node_from(from_name='获取角色列表')
    @operation_node(name='获取施放顺序')
    def _get_technique_order(self) -> OperationRoundResult:
        """
        根据当前队伍的角色 获取施放秘技的顺序
        :return:
        """
        for i in range(4):  # 优先使用普通BUFF 无冲突可叠加的
            if self.character_list[i] is None:
                continue
            if self.character_list[i].technique_type == TECHNIQUE_BUFF:
                self.technique_order.append(i)

        for i in range(4):  # 使用结界类 只能一个
            if self.character_list[i] is None:
                continue
            if self.character_list[i].technique_type == TECHNIQUE_AREA:
                self.technique_order.append(i)
                break

        # 任何攻击类只能有一个 选择之后就可以返回了
        for i in range(4):  # 输出角色 攻击类
            if self.character_list[i] is None:
                continue
            if not is_attack_character(self.character_list[i].id):
                continue
            if self.character_list[i].technique_type in [TECHNIQUE_ATTACK, TECHNIQUE_BUFF_ATTACK, TECHNIQUE_BUFF_ATTACK_DISAPPEAR]:
                self.technique_order.append(i)
                return self.round_success()

        for i in range(4):  # 银狼攻击
            if self.character_list[i] is None:
                continue
            if self.character_list[i] == SILVERWOLF:
                self.technique_order.append(i)
                return self.round_success()

        for i in range(4):  # 普通角色 攻击类
            if self.character_list[i] is None:
                continue
            if self.character_list[i].technique_type in [TECHNIQUE_ATTACK, TECHNIQUE_BUFF_ATTACK, TECHNIQUE_BUFF_ATTACK_DISAPPEAR]:
                self.technique_order.append(i)
                return self.round_success()

        # 可能存在没有攻击类的角色 此时也需要兜底返回
        return self.round_success()

    @node_from(from_name='检测秘技点')
    @node_from(from_name='使用秘技')
    @operation_node(name='切换角色')
    def _switch_member(self) -> OperationRoundResult:
        """
        切换角色
        :return:
        """
        if self.technique_idx >= len(self.technique_order):
            return self.round_success(StartFightForElite.STATUS_DONE)
        idx = self.technique_order[self.technique_idx]  # 从0开始
        op = SwitchMember(self.ctx, idx + 1, skip_first_screen_check=True,
                          skip_resurrection_check=self.skip_resurrection_check)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='切换角色')
    @operation_node(name='使用秘技')
    def _use_technique(self) -> OperationRoundResult:
        """
        使用秘技
        :return:
        """
        op = UseTechnique(self.ctx)
        op_result = op.execute()
        use_tech = False
        if op_result.success:
            op_result_data: UseTechniqueResult = op_result.data
            use_tech = op_result_data.use_tech
            idx = self.technique_order[self.technique_idx]
            self.need_attack_finally = self.character_list[idx].technique_type != TECHNIQUE_ATTACK
        self.technique_idx += 1

        wait_time = 0
        if self.technique_idx < len(self.technique_order) and use_tech:
            # 还需要切换人物使用秘技的情况
            # 如果这次使用了秘技 要等待一下后摇消失后 再进行下一步操作
            wait_time = 1.5
        return self.round_by_op_result(op_result, wait=wait_time)

    @node_from(from_name='切换角色', status=STATUS_DONE)
    @operation_node(name='攻击')
    def _attack(self) -> OperationRoundResult:
        """
        发起攻击
        :return:
        """
        screen = self.screenshot()
        # 仍在大世界的话 就尝试攻击
        if common_screen_state.is_normal_in_world(self.ctx, screen) \
                or common_screen_state.is_mission_in_world(self.ctx, screen):
            self.ctx.controller.initiate_attack()
            return self.round_retry('未进入战斗 尝试攻击', wait=1)
        else:
            return self.round_success()