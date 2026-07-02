import time
from typing import List, Callable, Optional, ClassVar

from basic.i18_utils import gt
from sr.const.character_const import Character, CharacterCombatType
from sr.context.context import Context
from sr.operation import Operation, OperationSuccess, OperationResult, StateOperation, StateOperationEdge, \
    StateOperationNode, OperationOneRoundResult
from sr.operation.unit.forgotten_hall.choose_mission import ChooseMission
from sr.operation.unit.forgotten_hall.choose_team_in_fh import ChooseTeamInForgottenHall
from sr.screen_area.screen_treasures_lightward import ScreenTreasuresLightWard
from sr.treasures_lightward.op.check_mission_star import CheckMissionStar
from sr.treasures_lightward.op.tl_battle import TlNodeFight, TlAfterNodeFight
from sr.treasures_lightward.treasures_lightward_const import TreasuresLightwardTypeEnum


class ChallengeTreasuresLightwardMission(StateOperation):

    STATUS_ALL_NODE_DONE: ClassVar[str] = '所有节点已完成'

    def __init__(self, ctx: Context, schedule_type: TreasuresLightwardTypeEnum,
                 mission_num: int, node_cnt: int,
                 cal_team_func: Callable[[List[List[CharacterCombatType]]], Optional[List[List[Character]]]],
                 op_callback: Optional[Callable[[OperationResult], None]] = None
                 ):
        """
        需要已经在逐光捡金选择关卡的页面
        选择目标关卡并挑战
        最后返回状态为星数
        :param ctx: 上下文
        :param mission_num: 关卡编号
        :param node_cnt: 节点数量
        :param cal_team_func:
        """
        edges: List[StateOperationEdge] = []

        wait_in_hall = StateOperationNode('等待界面加载', self._wait)

        check_star = StateOperationNode('检查星数', op=CheckMissionStar(ctx, mission_num))
        edges.append(StateOperationEdge(wait_in_hall, check_star))

        full_star = StateOperationNode('满星结束', op=OperationSuccess(ctx, '3', data=3))
        edges.append(StateOperationEdge(check_star, full_star, status='3'))  # 3颗满了就可以跳过本次挑战了

        enter_mission = StateOperationNode('选择关卡', op=ChooseMission(ctx, mission_num))
        edges.append(StateOperationEdge(check_star, enter_mission, ignore_status=True))  # 未满星就进行挑战

        choose_team = StateOperationNode('选择配队角色', self._choose_team_members)
        edges.append(StateOperationEdge(enter_mission, choose_team))

        choose_cacophony = StateOperationNode('选择增益效果', self._choose_cacophony)
        edges.append(StateOperationEdge(choose_team, choose_cacophony, status=TreasuresLightwardTypeEnum.PURE_FICTION.value))
        edges.append(StateOperationEdge(choose_cacophony, choose_cacophony, ignore_status=True))  # 循环选择增益效果

        click_challenge = StateOperationNode('开始挑战', self._start_challenge)
        edges.append(StateOperationEdge(choose_team, click_challenge, ignore_status=True))  # 选择配队后无特殊处理的情况
        edges.append(StateOperationEdge(choose_cacophony, click_challenge, status=ChallengeTreasuresLightwardMission.STATUS_ALL_NODE_DONE))  # 选择完增益效果后进入

        node_fight = StateOperationNode('节点战斗', self._node_fight)
        edges.append(StateOperationEdge(click_challenge, node_fight))
        edges.append(StateOperationEdge(node_fight, node_fight, ignore_status=True))  # 进入下一个节点战斗

        back_to_hall = StateOperationNode('战斗结算后返回', op=TlAfterNodeFight(ctx, schedule_type))
        # 无论出现 挑战成功 还是 战斗失败 都是返回
        edges.append(StateOperationEdge(node_fight, back_to_hall, status=ScreenTreasuresLightWard.FH_AFTER_BATTLE_SUCCESS_1.value.text))  # 所有节点通过
        edges.append(StateOperationEdge(node_fight, back_to_hall, status=ScreenTreasuresLightWard.FH_AFTER_BATTLE_FAIL.value.text))  # 某一个节点失败了

        check_star_2 = StateOperationNode('挑战后再检查星数', op=CheckMissionStar(ctx, mission_num))
        edges.append(StateOperationEdge(back_to_hall, check_star_2))

        super().__init__(ctx, op_name='%s %d' % (gt('逐光捡金 挑战关卡'), mission_num),
                         edges=edges, op_callback=op_callback)

        self.node_cnt: int = node_cnt
        """总共有多少个节点"""
        self.teams: Optional[List[List[Character]]] = None
        """各个节点的配队"""
        self.current_node_idx: int = 0
        """当前进行的节点"""
        self.schedule_type: TreasuresLightwardTypeEnum = schedule_type
        """当前挑战类型"""
        self.cal_team_func: Callable[[List[List[CharacterCombatType]]], Optional[List[List[Character]]]] = cal_team_func
        """计算配队的函数"""

    def handle_init(self) -> Optional[OperationOneRoundResult]:
        """
        执行前的初始化 由子类实现
        注意初始化要全面 方便一个指令重复使用
        可以返回初始化后判断的结果
        - 成功时跳过本指令
        - 失败时立刻返回失败
        - 不返回时正常运行本指令
        """
        self.teams = None
        self.current_node_idx = 0

    def _wait(self) -> OperationOneRoundResult:
        if self.schedule_type == TreasuresLightwardTypeEnum.FORGOTTEN_HALL:
            area = ScreenTreasuresLightWard.FH_TITLE.value
        else:
            area = ScreenTreasuresLightWard.PF_TITLE.value

        if self.find_area(area):
            return self.round_success()
        else:
            return self.round_retry('未在%s画面' % area.status, wait=1)

    def _choose_team_members(self) -> OperationOneRoundResult:
        """
        选择角色配队
        :return:
        """
        self.ctx.tl_info.character_scroll = 0
        self.ctx.tl_info.character_scroll_direction = 1

        op = ChooseTeamInForgottenHall(self.ctx, self.cal_team_func, self._on_team_calculated)
        op_result = op.execute()
        if op_result.success:
            return self.round_success(self.schedule_type.value)
        else:
            return self.round_retry('选择配队失败', wait=1)

    def _on_team_calculated(self, teams: List[List[Character]]):
        """
        更新配队
        :param teams:
        :return:
        """
        self.teams = teams

    def _choose_cacophony(self) -> OperationOneRoundResult:
        """
        选择增益效果 - 虚构叙事专用
        :return:
        """
        node_to_click_list = [
            ScreenTreasuresLightWard.PF_CACOPHONY_NODE_1.value,
            ScreenTreasuresLightWard.PF_CACOPHONY_NODE_2.value
        ]

        self.ctx.controller.click(node_to_click_list[self.current_node_idx].rect.center)
        time.sleep(1)

        opt_list = [
            ScreenTreasuresLightWard.PF_CACOPHONY_OPT_1.value,
            ScreenTreasuresLightWard.PF_CACOPHONY_OPT_2.value,
            ScreenTreasuresLightWard.PF_CACOPHONY_OPT_3.value
        ]

        self.ctx.controller.click(opt_list[self.current_node_idx].rect.center)
        time.sleep(0.25)

        click = self.find_and_click_area(ScreenTreasuresLightWard.PF_CACOPHONY_CONFIRM.value)

        if click == Operation.OCR_CLICK_SUCCESS:
            self.current_node_idx += 1
            if self.current_node_idx >= self.node_cnt:
                self.current_node_idx = 0
                return self.round_success(ChallengeTreasuresLightwardMission.STATUS_ALL_NODE_DONE, wait=1)
            else:
                return self.round_success(wait=1)
        else:
            return self.round_retry('选择增益效果失败')

    def _start_challenge(self) -> OperationOneRoundResult:
        """
        选择配队后 开始挑战
        :return:
        """
        if self.schedule_type == TreasuresLightwardTypeEnum.FORGOTTEN_HALL:
            area = ScreenTreasuresLightWard.FH_START_CHALLENGE.value
        else:
            area = ScreenTreasuresLightWard.PF_START_CHALLENGE.value

        click = self.find_and_click_area(area)
        if click == Operation.OCR_CLICK_SUCCESS:
            return self.round_success(wait=5)
        else:
            return self.round_retry('点击%s失败', area.status, wait=1)

    def _node_fight(self) -> OperationOneRoundResult:
        """
        进行某个节点的战斗
        :return:
        """
        idx = self.current_node_idx
        team = None if self.teams is None or idx >= len(self.teams) else self.teams[idx]
        op = TlNodeFight(self.ctx, idx == 0, schedule_type=self.schedule_type,
                         team=team, op_callback=self._after_node)
        return self.round_by_op(op.execute())

    def _after_node(self, op_result: OperationResult):
        """
        节点完成后的回调
        :return:
        """
        self.current_node_idx += 1
