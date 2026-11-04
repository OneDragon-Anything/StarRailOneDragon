"""忘却之庭(混沌回忆)挑战节点:从编队屏发起挑战 → 进入节点画面 → 前进 → 秘技 → 开战 → 等待结果。

⚠️ 适用范围:仅忘却之庭(按钮文案「混沌回忆」、NODE_FIRST_CLICK_EMPTY 弹窗、
两波连续战斗流程均按混沌回忆实测标定)。虚构叙事/末日幻影的发起按钮文案、
弹窗与波次结构不同,不可直接套用(需另行建档)。
⚠️ 已知边界(2026-11-04 实机):两波连续自动衔接、波间无结算弹窗,本 op 的
「等待战斗结束」在第一波打完进入第二波待命时会持续等待,需人工/上层补跑第二波
(全自动循环见 .debug/temp/TODO.md 挂账条)。

前置:编队屏(``GotoTreasuresLightward`` → 点关卡水晶 → ``TlFillTeamsOp`` 填好编队)。
流程参照旧实现(``application/treasures_lightward/op/tl_battle.py`` + ``tl_wait.py``,
迁移时 ``sr.*`` 包已删):首波进入会弹 buff 说明(点击空白处关闭),等待可移动后
向前移动,用 ``StartFightForElite`` 施放秘技并开战,轮询挑战成功/战斗失败浮层,
成功后点「返回忘却之庭」(3.x 前文案为「返回逐光捡金」,两个 area 均保留兜底)回选关界面。
"""

from __future__ import annotations

from typing import ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.config.character_const import CHARACTER_LIST, Character
from sr_od.context.sr_context import SrContext
from sr_od.operations.battle.start_fight_for_elite import StartFightForElite
from sr_od.operations.sr_operation import SrOperation

_SELECT_SCREEN: str = '逐光捡金'
_TEAM_SCREEN: str = '忘却之庭-编队'


class TlStartChallengeOp(SrOperation):

    STATUS_SUCCESS: ClassVar[str] = '挑战成功'
    STATUS_FAIL: ClassVar[str] = '战斗失败'

    def __init__(self, ctx: SrContext, team_names: list[str],
                 first_node: bool = True, skip_click_start: bool = False):
        """
        Args:
            team_names: 本波编队角色中文名列表(与填充一致;秘技顺序按角色 technique_type 决策)。
            first_node: 是否第一个波次(进入时弹 buff 说明,需点空白关闭)。
            skip_click_start: 跳过点最终开始(用于已在节点画面内的恢复续跑,
                如上次 op 在点击后中途失败的现场)。
        """
        SrOperation.__init__(self, ctx, op_name='逐光捡金 开始挑战')
        self.first_node: bool = first_node
        self.skip_click_start: bool = skip_click_start
        self.team: list[Character] = []
        for name in team_names:
            char = next((c for c in CHARACTER_LIST if c.cn == name), None)
            if char is None:
                # 构造期参数错误直接 raise(调用方/run_operation 捕获后干净报错);
                # 不能用 round_fail —— 其返回值在 __init__ 里会被丢弃,op 会带着缺员队伍继续跑
                raise ValueError(f'未知角色名: {name}')
            self.team.append(char)

    @operation_node(name='点击最终开始', is_start_node=True)
    def _click_start(self) -> OperationRoundResult:
        """点击发起挑战。点击成功即进入下一节点(后续节点负责确认画面转移)——
        此处不能用 round_wait:节点重跑时按钮已随画面切换消失,会误判失败
        (2026-11-04 实测踩坑:点成功但 op 报「未找到最终开始按钮」)。"""
        click = self.round_by_find_and_click_area(
            self.last_screenshot, _TEAM_SCREEN, '按钮-最终开始', success_wait=2)
        if click.is_success:
            return self.round_success(wait=1)
        if self.skip_click_start:
            return self.round_success()
        return self.round_fail('未找到最终开始按钮')

    @node_from(from_name='点击最终开始')
    @operation_node(name='处理进入弹窗', node_max_retry_times=12)
    def _handle_popups(self) -> OperationRoundResult:
        """首波进入的 buff 说明弹窗点空白关闭;确认已离开编队屏(节点画面加载)。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'NODE_FIRST_CLICK_EMPTY').is_success:
            self.round_by_click_area(screen, _SELECT_SCREEN, 'NODE_FIRST_CLICK_EMPTY')
            return self.round_wait('关闭首波 buff 说明', wait=1)
        if self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success:
            return self.round_retry('仍在编队屏,等待跳转', wait=1)
        return self.round_success()

    @node_from(from_name='处理进入弹窗')
    @operation_node(name='向前移动')
    def _move_forward(self) -> OperationRoundResult:
        """敌人通常在入口正前方,先向前走一段(秘技施放与开战都在移动后)。"""
        self.ctx.controller.move('w', press_time=2)
        return self.round_success(wait=0.5)

    @node_from(from_name='向前移动')
    @operation_node(name='秘技与开战')
    def _start_fight(self) -> OperationRoundResult:
        op = StartFightForElite(
            self.ctx,
            character_list=self.team,
            skip_point_check=True,       # 逐光捡金秘技点固定,跳过识别
            skip_resurrection_check=True,
        )
        return self.round_by_op_result(op.execute())

    @node_from(from_name='秘技与开战')
    @operation_node(name='等待战斗结束', node_max_retry_times=200)
    def _wait_battle_end(self) -> OperationRoundResult:
        """轮询战斗结果浮层(WAIT 不计 retry;长战斗靠本节点循环等待)。"""
        screen = self.last_screenshot
        if (self.round_by_find_area(screen, _SELECT_SCREEN, 'FH_AFTER_BATTLE_SUCCESS_1').is_success
                or self.round_by_find_area(screen, _SELECT_SCREEN, 'FH_AFTER_BATTLE_SUCCESS_2').is_success):
            return self.round_success(TlStartChallengeOp.STATUS_SUCCESS)
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'FH_AFTER_BATTLE_FAIL').is_success:
            return self.round_fail(TlStartChallengeOp.STATUS_FAIL)
        return self.round_wait('战斗中', wait=3)

    @node_from(from_name='等待战斗结束')
    @operation_node(name='点击返回逐光捡金', node_max_retry_times=12)
    def _click_back(self) -> OperationRoundResult:
        """结算画面点「返回逐光捡金」回选关(快速通关弹窗等中间态由后续观察补)。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'FH_TITLE').is_success:
            return self.round_success()
        for btn_area in ('FH_AFTER_BATTLE_BACK_BTN_1', 'FH_AFTER_BATTLE_BACK_BTN_2'):
            click = self.round_by_find_and_click_area(
                screen, _SELECT_SCREEN, btn_area, success_wait=2)
            if click.is_success:
                return self.round_wait('返回逐光捡金中', wait=1)
        return self.round_retry('未找到返回按钮', wait=1)
