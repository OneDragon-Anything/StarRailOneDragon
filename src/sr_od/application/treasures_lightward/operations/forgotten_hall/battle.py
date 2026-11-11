"""忘却之庭(混沌回忆)节点战斗:编队屏点「混沌回忆」按钮后调用,全自动跑完两节点。

⚠️ 适用范围:仅忘却之庭(按钮文案/记忆紊流弹窗/两波连续流程均按混沌回忆实测标定);
虚构叙事/末日幻影的发起与节点结构不同,不可套用,需另行建档。

流程契约(人类老莫 2026-11-04 定义):
- 调用方在编队屏点击「混沌回忆」按钮后调用本 op(本 op 不点按钮);
- 先判断是否已进入节点画面(锁光标大世界场景,屏级 pc_alt=true);
- 有弹窗(记忆紊流说明)就关弹窗;
- 前进 → 秘技 → 发起战斗;
- 判断战斗结束 → 下个节点循环;
- 出现「挑战成功」→ 点「返回忘却之庭」收尾。

实现要点(2026-11-04 实机):两节点连续自动衔接、节点间无结算弹窗——单节点状态机
每轮按画面特征分流:结算浮层 → 收尾;节点待命态(节点画面三锚齐:剩余轮/状态效果/
查看详情,战斗中左栏被战斗 UI 替换故三锚不齐)→ 节点流程;其余 → 等待。
节点队伍按 ``node_teams`` 顺序消费(第 N 次待命态 = 第 N 节点),StartFightForElite
按各波角色 technique_type 决策秘技顺序。
"""

from __future__ import annotations

from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.config.character_const import CHARACTER_LIST, Character
from sr_od.context.sr_context import SrContext
from sr_od.operations.battle.start_fight_for_elite import StartFightForElite
from sr_od.operations.sr_operation import SrOperation

_SELECT_SCREEN: str = '逐光捡金'
_TEAM_SCREEN: str = '忘却之庭-编队'
_NODE_SCREEN: str = '忘却之庭-节点画面'


class TlFhBattleOp(SrOperation):

    STATUS_SUCCESS: ClassVar[str] = '挑战成功'
    STATUS_FAIL: ClassVar[str] = '战斗失败'

    def __init__(self, ctx: SrContext, node_teams: list[list[str]]):
        """
        Args:
            node_teams: 每节点编队的角色中文名列表(外层=节点顺序,内层 4 人按槽位序;
                与 TlFhTeamFillOp 填充一致,秘技顺序按角色 technique_type 决策)。
        """
        SrOperation.__init__(self, ctx, op_name='逐光捡金 节点战斗')
        self.teams: list[list[Character]] = []
        for names in node_teams:
            team: list[Character] = []
            for name in names:
                char = next((c for c in CHARACTER_LIST if c.cn == name), None)
                if char is None:
                    # 构造期参数错误直接 raise(run_operation 捕获后干净上报);
                    # 不能用 round_fail —— 其返回值在 __init__ 里会被丢弃
                    raise ValueError(f'未知角色名: {name}')
                team.append(char)
            self.teams.append(team)
        self._node_idx: int = 0            #: 当前待填充的节点(0 基,按待命态出现顺序消费)

    @operation_node(name='等待进入节点画面', is_start_node=True, node_max_retry_times=30)
    def _wait_enter(self) -> OperationRoundResult:
        """确认已离开编队屏并进入节点画面(或其首波弹窗);加载过渡则等待。"""
        screen = self.last_screenshot
        if self._is_node_standby(screen) or self._popup_visible(screen):
            return self.round_success()
        if self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success:
            return self.round_retry('仍在编队屏(按钮未生效或调用方未点击)', wait=1)
        return self.round_wait('节点画面加载中', wait=1)

    @node_from(from_name='等待进入节点画面')
    # 循环由 round_wait/round_retry 机制自动重跑本节点,不声明自环(自环出边会吞成功结果)
    @operation_node(name='节点循环', node_max_retry_times=240)
    def _node_loop(self) -> OperationRoundResult:
        """按画面特征分流的节点状态机(结算 → 收尾;弹窗 → 关闭;待命 → 开战;其余 → 等待)。

        弹窗检查独立于待命态判定且必须前置:记忆紊流说明弹窗全屏暗化会遮蔽
        待命态三锚(剩余轮/状态效果/查看详情),埋进待命态分支内将永远不可达
        (2026-11-04 实机踩坑)。
        """
        screen = self.last_screenshot

        # 1. 结算浮层优先
        if (self.round_by_find_area(screen, _SELECT_SCREEN, 'FH_AFTER_BATTLE_SUCCESS_1').is_success
                or self.round_by_find_area(screen, _SELECT_SCREEN, 'FH_AFTER_BATTLE_SUCCESS_2').is_success):
            return self.round_success(TlFhBattleOp.STATUS_SUCCESS)
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'FH_AFTER_BATTLE_FAIL').is_success:
            return self.round_fail(TlFhBattleOp.STATUS_FAIL)

        # 2. 弹窗(全屏暗化,遮蔽三锚)→ 关闭
        if self._popup_visible(screen):
            # 不走 round_by_click_area:框架点击 press_time=0(短按),锁光标场景
            # 需非零按压才生效(实机 0.1s+ 有效,0s 落空);坐标从建档 area 中心取
            rect = self._area_rect(_NODE_SCREEN, 'NODE_FIRST_CLICK_EMPTY')
            if rect is not None:
                center = Point((rect.x1 + rect.x2) // 2, (rect.y1 + rect.y2) // 2)
                self.ctx.controller.click(center, press_time=0.15, pc_alt=True)
            return self.round_wait('关闭记忆紊流说明', wait=1)

        # 3. 节点待命态 → 节点流程(前进→秘技→开战)
        if self._is_node_standby(screen):
            if self._node_idx >= len(self.teams):
                return self.round_fail(f'节点待命但队伍预算用尽(共 {len(self.teams)} 节点)')
            team = self.teams[self._node_idx]
            self.ctx.controller.move('w', press_time=2)
            op = StartFightForElite(
                self.ctx,
                character_list=team,
                skip_point_check=True,       # 逐光捡金秘技点固定,跳过识别
                skip_resurrection_check=True,
            )
            op_result = op.execute()
            if not op_result.success:
                return self.round_fail(f'节点 {self._node_idx + 1} 开战失败: {op_result.status}')
            self._node_idx += 1
            return self.round_wait(f'节点 {self._node_idx} 开战指令完成', wait=3)

        # 4. 战斗进行中 / 加载过渡
        return self.round_wait('战斗进行中', wait=3)

    @node_from(from_name='节点循环', status=STATUS_SUCCESS)
    @operation_node(name='点击返回忘却之庭', node_max_retry_times=12)
    def _click_back(self) -> OperationRoundResult:
        """结算画面点返回(3.x 文案「返回忘却之庭」,旧文案「返回逐光捡金」兜底)。

        首次 3 星通关最高解锁关会先弹「快速通关」补发列表(视同 3 星通关所有前置,
        前置奖励自动领取)→ 点确认 → 获得物品页(点击空白关闭)→ 之后才是结算返回。
        (2026-11-04 其十首通实机:弹窗盖住返回按钮,op 需依次处理。)
        """
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'FH_TITLE').is_success:
            return self.round_success()
        # 快速通关补发列表 → 点确认
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'AFTER_BATTLE_QUICK_PASS_TITLE').is_success:
            click = self.round_by_find_and_click_area(
                screen, _SELECT_SCREEN, 'AFTER_BATTLE_QUICK_PASS_CONFIRM', success_wait=2)
            if click.is_success:
                return self.round_wait('确认快速通关补发', wait=1.5)
            return self.round_retry('快速通关弹窗未找到确认按钮', wait=1)
        # 获得物品页(点击空白关闭)→ 点页面空白区
        if self.round_by_find_area(screen, _SELECT_SCREEN, 'AFTER_BATTLE_QUICK_PASS_EMPTY').is_success:
            rect = self._area_rect(_SELECT_SCREEN, '按钮-获得物品空白')
            if rect is not None:
                self.ctx.controller.click(
                    Point((rect.x1 + rect.x2) // 2, (rect.y1 + rect.y2) // 2),
                    press_time=0.15)
            return self.round_wait('关闭获得物品页', wait=1.5)
        for btn_area in ('FH_AFTER_BATTLE_BACK_BTN_2', 'FH_AFTER_BATTLE_BACK_BTN_1'):
            click = self.round_by_find_and_click_area(
                screen, _SELECT_SCREEN, btn_area, success_wait=2)
            if click.is_success:
                return self.round_wait('返回忘却之庭中', wait=1)
        return self.round_retry('未找到返回按钮', wait=1)

    def _is_node_standby(self, screen) -> bool:
        """节点待命态判定:节点画面三锚齐(剩余轮+状态效果+查看详情)。

        战斗中左栏被战斗 UI 替换,三锚不齐故不会误判;加载过渡亦不齐。
        """
        return (self.round_by_find_area(screen, _NODE_SCREEN, '标识-剩余轮行').is_success
                and self.round_by_find_area(screen, _NODE_SCREEN, '面板-状态效果').is_success
                and self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success)

    def _area_rect(self, screen_name: str, area_name: str):
        """某画面某 area 的 pc_rect(点击坐标来源;屏/area 缺失 None)。"""
        si = self.ctx.screen_loader.get_screen(screen_name)
        if si is None:
            return None
        area = next((a for a in si.area_list if a.area_name == area_name), None)
        return area.pc_rect if (area is not None and area.pc_rect is not None) else None

    def _popup_visible(self, screen) -> bool:
        """记忆紊流说明弹窗是否可见(首波进入时)。"""
        return self.round_by_find_area(screen, _NODE_SCREEN, 'NODE_FIRST_CLICK_EMPTY').is_success
