from typing import List, Optional, Callable

from cv2.typing import MatLike

from basic.i18_utils import gt
from sr.const.character_const import Character
from sr.context.context import Context
from sr.image.sceenshot import screen_state
from sr.image.sceenshot.screen_state_enum import ScreenState
from sr.operation import Operation, OperationResult, StateOperation, StateOperationNode, StateOperationEdge, \
    OperationOneRoundResult
from sr.operation.battle.start_fight import StartFightForElite
from sr.operation.unit.move import MoveToEnemy, MoveForward
from sr.screen_area.screen_treasures_lightward import ScreenTreasuresLightWard
from sr.treasures_lightward.op.tl_wait import TlWaitNodeStart
from sr.treasures_lightward.treasures_lightward_const import TreasuresLightwardTypeEnum


class TlNodeFight(StateOperation):

    def __init__(self, ctx: Context,
                 is_first_node: bool,
                 schedule_type: TreasuresLightwardTypeEnum,
                 team: Optional[List[Character]] = None,
                 op_callback: Optional[Callable[[OperationResult], None]] = None
                 ):
        """
        需要已经在逐光捡金节点内的页面
        移动到敌人身边后
        使用秘技并攻击敌人
        完成战斗后 返回战斗结果
        :param ctx:
        :param is_first_node: 是否第一个节点 第一个节点开始时会显示一个buff
        :param team: 当前节点使用的配队 无传入时自动识别 但不准
        :param op_callback: 节点结束后的回调
        """
        edges: List[StateOperationEdge] = []

        node_start = StateOperationNode('等待节点开始', op=TlWaitNodeStart(ctx, is_first_node))

        move = StateOperationNode('向敌人移动', op=MoveToEnemy(ctx))
        edges.append(StateOperationEdge(node_start, move))

        move_towards = StateOperationNode('向前移动', op=MoveForward(ctx, 2))  # 有可能红点在比较远 先向前移动看看
        edges.append(StateOperationEdge(move, move_towards, success=False, status=MoveToEnemy.STATUS_ENEMY_NOT_FOUND))
        edges.append(StateOperationEdge(move_towards, move))

        enter_fight = StateOperationNode('进入战斗',
                                         op=StartFightForElite(ctx, character_list=team,
                                                               skip_point_check=True,
                                                               skip_resurrection_check=True))
        edges.append(StateOperationEdge(move, enter_fight))

        check_screen = StateOperationNode('检测画面', self._check_screen)
        edges.append(StateOperationEdge(enter_fight, check_screen))

        super().__init__(ctx, try_times=10,
                         op_name=gt('逐光捡金 节点挑战'),
                         edges=edges,
                         timeout_seconds=600,
                         op_callback=op_callback)

        self.schedule_type: TreasuresLightwardTypeEnum = schedule_type
        self.last_state: Optional[str] = None

    def _check_screen(self) -> OperationOneRoundResult:
        """
        开始战斗后 检查当前画面并判断战斗是否结束
        :return:
        """
        screen = self.screenshot()
        state = self._get_screen_state(screen)
        if state is not None:
            if self.last_state is not None and self.last_state == state:
                return self.round_success(state)
            else:
                self.last_state = state
                return self.round_retry('画面在改变', wait=1)
        else:
            return self.round_wait('战斗中', wait=1)

    def _get_screen_state(self, screen: MatLike) -> Optional[str]:
        """
        获取当前屏幕状态
        :param screen:
        :return:
        """
        if self.schedule_type == TreasuresLightwardTypeEnum.FORGOTTEN_HALL:
            area_list = [
                ScreenTreasuresLightWard.FH_AFTER_BATTLE_SUCCESS_1.value,
                ScreenTreasuresLightWard.FH_AFTER_BATTLE_SUCCESS_2.value,
                ScreenTreasuresLightWard.FH_AFTER_BATTLE_FAIL.value,
                ScreenTreasuresLightWard.EXIT_BTN.value,
            ]
        else:
            area_list = [
                ScreenTreasuresLightWard.PF_AFTER_BATTLE_SUCCESS_1.value,
                ScreenTreasuresLightWard.PF_AFTER_BATTLE_SUCCESS_2.value,
                ScreenTreasuresLightWard.PF_AFTER_BATTLE_FAIL.value,
                ScreenTreasuresLightWard.EXIT_BTN.value,
            ]
        for area in area_list:
            if self.find_area(area, screen):
                return area.status

        return None


class TlAfterNodeFight(StateOperation):

    def __init__(self, ctx: Context, schedule_type: TreasuresLightwardTypeEnum):
        """
        需要已经在逐光捡金节点战斗结算的页面
        点击【返回逐光捡金】
        :param ctx: 上下文
        """
        edges = []

        click_back = StateOperationNode('点击返回', self._click_back)
        check_screen = StateOperationNode('检测画面', self._check_screen)
        edges.append(StateOperationEdge(click_back, check_screen))

        quick_confirm = StateOperationNode('快速通关确认', self._click_quick_confirm)
        edges.append(StateOperationEdge(check_screen, quick_confirm, status=ScreenTreasuresLightWard.AFTER_BATTLE_QUICK_PASS_TITLE.value.text))
        edges.append(StateOperationEdge(quick_confirm, check_screen))

        quick_empty_close = StateOperationNode('快速通关点击空白', self._click_quick_empty)
        edges.append(StateOperationEdge(check_screen, quick_empty_close, status=ScreenTreasuresLightWard.AFTER_BATTLE_QUICK_PASS_EMPTY.value.text))
        edges.append(StateOperationEdge(quick_empty_close, check_screen))

        super().__init__(ctx, try_times=10,
                         op_name=gt('逐光捡金 结算后返回', 'game'),
                         edges=edges
                         )
        self.phase: int = 0
        self.schedule_type: TreasuresLightwardTypeEnum = schedule_type

    def _click_back(self):
        screen = self.screenshot()

        if self.schedule_type == TreasuresLightwardTypeEnum.FORGOTTEN_HALL:
            area_list = [
                ScreenTreasuresLightWard.FH_AFTER_BATTLE_BACK_BTN_1.value,
                ScreenTreasuresLightWard.FH_AFTER_BATTLE_BACK_BTN_2.value,
            ]
        else:
            area_list = [
                ScreenTreasuresLightWard.PF_AFTER_BATTLE_BACK_BTN.value,
            ]

        for area in area_list:
            click = self.find_and_click_area(area, screen)
            if click == Operation.OCR_CLICK_SUCCESS:
                return self.round_success(wait=1)

        return self.round_retry('点击%s失败' % area_list[0].text, wait=1)

    def _check_screen(self):
        """
        检测画面状态
        :return:
        """
        screen = self.screenshot()
        state = self._get_screen_state(screen)

        if state is None:
            return self.round_retry('未知画面', wait=1)
        else:
            return self.round_success(state)

    def _get_screen_state(self, screen: MatLike) -> Optional[str]:
        """
        获取当前画面状态
        :param screen:
        :return:
        """
        if screen_state.in_secondary_ui(screen, self.ctx.ocr, ScreenState.FORGOTTEN_HALL.value):
            return ScreenState.FORGOTTEN_HALL.value

        if self.schedule_type == TreasuresLightwardTypeEnum.FORGOTTEN_HALL:
            area_list = [
                ScreenTreasuresLightWard.FH_TITLE.value,
                ScreenTreasuresLightWard.AFTER_BATTLE_QUICK_PASS_TITLE.value,
                ScreenTreasuresLightWard.AFTER_BATTLE_QUICK_PASS_EMPTY.value,
            ]
        else:
            area_list = [
                ScreenTreasuresLightWard.PF_TITLE.value,
                ScreenTreasuresLightWard.AFTER_BATTLE_QUICK_PASS_TITLE.value,
                ScreenTreasuresLightWard.AFTER_BATTLE_QUICK_PASS_EMPTY.value,
            ]
        for area in area_list:
            if self.find_area(area, screen):
                return area.text

        return None

    def _click_quick_confirm(self):
        """
        快速通关确认
        :return:
        """
        area = ScreenTreasuresLightWard.AFTER_BATTLE_QUICK_PASS_CONFIRM.value
        click = self.find_and_click_area(area)
        if click == Operation.OCR_CLICK_SUCCESS:
            return self.round_success(wait=1)
        else:
            return self.round_retry('点击%s失败' % area.text, wait=1)

    def _click_quick_empty(self):
        """
        快速通关确认
        :return:
        """
        area = ScreenTreasuresLightWard.AFTER_BATTLE_QUICK_PASS_EMPTY.value
        click = self.find_and_click_area(area)
        if click == Operation.OCR_CLICK_SUCCESS:
            return self.round_success(wait=1)
        else:
            return self.round_retry('点击%s失败' % area.text, wait=1)
