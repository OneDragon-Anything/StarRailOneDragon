"""末日幻影完整挑战(组合 op):编队选人 → 终焉公理装配 → 前往挑战 →
节点战斗推进(前进+秘技+开战) → 最终结算 → 返回选关。

拆分为多个可独立 ``run_operation`` 的 op(人类老莫 2026-11-06 指示:不同场景
用不同 op,挑战 op 组合它们);实现按职责拆文件(本文件 = 组合入口 + re-export):

- :class:`tl_as_team_fill.TlAsTeamFillOp` 编队选人:清空两/三行 + 按目标填 8/12 人
  (星启整页批量点卡,双节点逐人回验驱动);
  起点 = 末日幻影-编队,终点 = 编队屏(已填满)。
- :class:`tl_as_buff_equip.TlAsAxiomEquipOp` 终焉公理装配:两行右端圆圈 → 弹窗选卡
  → 装配效果;起点 = 编队屏(已填人),终点 = 编队屏(已装配)。
- :class:`tl_as_battle.TlAsBattleOp` 节点战斗推进:简报关闭 → 前进+秘技+开战 →
  战斗等待 → 节点结算推进 → 最终结算;起点 = 首领简报横幅或节点画面,
  终点 = 最终结算点「返回末日幻影」后。
- :class:`tl_as_battle_exit.TlAsBattleExitOp` 退出当前节点战斗/结算(弃赛/换队场景)。
- :class:`TlApocalypticShadowChallengeOp` 组合:入口多态 → 选人 → 装配 →
  前往挑战 → 战斗推进 → 返回选关。

前置:``GotoTreasuresLightward(TLMode.APOCALYPTIC_SHADOW)`` 到末日幻影选关屏;
难度选择不在本 op 内(自动化默认打当前可打的最高难度——3 星通关最高难度视同
通关全部前置难度,奖励由「快速通关」弹窗补发)。

编队交互模型(与虚构叙事编队的差异见各节点注释):

- 两行各 4 槽对应两个节点;点槽位语义按列表展开态分三种:收起态点槽位 =
  展开列表 + 选中该行;展开态点**当前选中行**的已入队槽位 = 移除该角色;
  展开态点**非选中行**槽位 = 不改编队、仅收起列表;
- 清空编队不靠垃圾桶(顶部垃圾桶在此屏无清空功能),用「点已入队槽位」逐个
  移除,由落位回验(行成员实读)驱动收敛;
- 行 boss 卡内的「坚防守备/阵地转移」等按钮 = **敌方特性条款查看入口**,
  点击仅弹说明、不改变任何装配(实机验证);真正的增益装配入口 = 行右端
  圆形按钮(编入角色后出现)→「终焉公理」弹窗(增益三选一,名称随期轮换,
  按位置选择后点「装配效果」,弹窗自动关闭);
- 「前往挑战」在校验不通过(编队不满 / 含不可用角色)时点击无反应——填充
  与装配节点保证到达时编队合法;修改已挑战编队会先弹「更换编队确认」;
- 「前往挑战」点击生效后先弹**首领简报横幅**(「点击空白处关闭」,不点也会
  自动消失)→ 节点画面(大世界,pc_alt 模式,左栏锚与忘却之庭节点画面同构,
  复用其 area);
- 两节点**逐个开战**:节点一战斗结束出节点结算页(积分明细 + 「前往节点二」)
  → 节点二简报横幅 → 节点二战斗 → 最终结算页(通关奖励 + 「返回末日幻影」);
- 节点画面开战顺序 = **前进接近 → 施放秘技 → 点击开战**(复用框架
  :class:`~sr_od.operations.technique.UseTechnique`;攻击型秘技施放即入战斗,
  增益型秘技施放后再点击开战);自动战斗由游戏继承上一次设置,op 不接管;
- 战斗以「剩余行动值」计分,行动值耗尽 = 低分结算,不视为失败流程。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.treasures_lightward.obs.tl_team_common import (
    get_area_center_point,
)
from sr_od.application.treasures_lightward.operations.tl_as_battle import TlAsBattleOp
from sr_od.application.treasures_lightward.operations.tl_as_battle_exit import (
    TlAsBattleExitOp,
)
from sr_od.application.treasures_lightward.operations.tl_as_buff_equip import (
    TlAsAxiomEquipOp,
)
from sr_od.application.treasures_lightward.operations.tl_as_team_fill import (
    TlAsTeamFillOp,
)
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

_SELECT_SCREEN: str = '末日幻影-选关'
_TEAM_SCREEN: str = '末日幻影-编队'
_BANNER_SCREEN: str = '末日幻影-首领简报'
_RESULT_SCREEN: str = '末日幻影-节点结算'
_NODE_SCREEN: str = '忘却之庭-节点画面'

__all__ = [
    'TlAsTeamFillOp',
    'TlAsAxiomEquipOp',
    'TlAsBattleOp',
    'TlAsBattleExitOp',
    'TlApocalypticShadowChallengeOp',
]


class TlApocalypticShadowChallengeOp(SrOperation):
    """末日幻影完整挑战(组合 op):选人 → 装配 buff → 前往挑战 → 战斗推进 → 返回选关。"""

    STATUS_SUCCESS: ClassVar[str] = '挑战成功'

    def __init__(self, ctx: SrContext, team_names: list[str],
                 buff_slots: tuple[int, ...] | list[int] = (1, 1)):
        """
        Args:
            team_names: 按行(节点)顺序拼接的角色中文名列表,8 人(2 行×4,
                双节点 01-03)或 12 人(3 行×4,星启 04);与脸库识别名一致,
                行 1 = 节点一队伍,以此类推。队伍须避开带警告标记的角色
                (命途/养成警告,如当期试用角色)——此类角色可落位,但「前往
                挑战」校验不通过(点击无反应)。
            buff_slots: 每行装配的终焉公理增益序号(1 基;增益名称随期轮换,
                按卡片位置选择)。2 项 = 双节点,3 项 = 星启。默认全 1。
        """
        SrOperation.__init__(self, ctx, op_name='末日幻影 挑战')
        self.fill_op = TlAsTeamFillOp(ctx, team_names)
        self.equip_op = TlAsAxiomEquipOp(ctx, buff_slots)
        self.battle_op = TlAsBattleOp(ctx)

    @operation_node(name='进入编队屏', is_start_node=True, node_max_retry_times=10)
    def _enter_team(self) -> OperationRoundResult:
        """从选关屏进编队屏;已在编队屏则直接通过。

        选关屏入口按钮随难度状态变形:未通关难度 = 中央「前往挑战」大按钮;
        已通关难度 = 节点分数卡下的「重新挑战」(两态同屏,前者消失)。
        首领简报横幅可见 = 挑战已发起(编队满员态进编队屏游戏会自动弹简报),
        返回 BANNER_UP 直连战斗推进,跳过填充/装配。节点画面(左栏「查看详情」)
        可见 = 挑战进行中,返回 BATTLE_ONGOING 直连战斗推进。"""
        screen = self.last_screenshot
        if (self.round_by_find_area(screen, _TEAM_SCREEN, '标题-末日幻影行').is_success
                and self.round_by_find_area(screen, _TEAM_SCREEN, '标题-编队行').is_success):
            # 难度与目标人数匹配校验(星启 04 三行/双节点 01-03 两行,由
            # read_team_nodes 锚行数实读)——不匹配在填充防御处显式失败
            return self.round_success()
        if self.round_by_find_area(screen, _BANNER_SCREEN, '提示-点击空白处关闭').is_success:
            return self.round_success('BANNER_UP')
        if self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success:
            return self.round_success('BATTLE_ONGOING')
        if self.round_by_find_area(
                screen, _SELECT_SCREEN, '按钮-更换编队确认').is_success:
            self.ctx.controller.click(
                get_area_center_point(self.ctx, _SELECT_SCREEN, '按钮-更换编队确认'),
                press_time=0.15)
            return self.round_retry('确认更换编队弹窗', wait=2.5)
        if self.round_by_find_area(screen, _SELECT_SCREEN, '按钮-更换编队').is_success:
            self.ctx.controller.click(
                get_area_center_point(self.ctx, _SELECT_SCREEN, '按钮-更换编队'),
                press_time=0.15)
            return self.round_retry('选关屏点更换编队', wait=2.5)
        if self.round_by_find_area(screen, _SELECT_SCREEN, '按钮-重新挑战').is_success:
            self.ctx.controller.click(
                get_area_center_point(self.ctx, _SELECT_SCREEN, '按钮-重新挑战'),
                press_time=0.15)
            return self.round_retry('选关屏点重新挑战', wait=2.5)
        if self.round_by_find_area(screen, _SELECT_SCREEN, '按钮-前往挑战').is_success:
            self.ctx.controller.click(
                get_area_center_point(self.ctx, _SELECT_SCREEN, '按钮-前往挑战'),
                press_time=0.15)
            return self.round_retry('选关屏点前往挑战', wait=2.5)
        return self.round_retry('画面异常(既非选关屏也非编队屏)', wait=1.5)

    @node_from(from_name='进入编队屏')
    @operation_node(name='编队选人', node_max_retry_times=8)
    def _fill(self) -> OperationRoundResult:
        """组合 :class:`TlAsTeamFillOp`(清空 + 填 8 人,落位回验驱动)。"""
        op_result = self.fill_op.execute()
        return self.round_by_op_result(op_result)

    @node_from(from_name='编队选人')
    @operation_node(name='终焉公理装配', node_max_retry_times=8)
    def _equip(self) -> OperationRoundResult:
        """组合 :class:`TlAsAxiomEquipOp`(两行圆圈 → 弹窗选卡 → 装配效果)。"""
        op_result = self.equip_op.execute()
        return self.round_by_op_result(op_result)

    @node_from(from_name='终焉公理装配')
    @operation_node(name='前往挑战', node_max_retry_times=10)
    def _start(self) -> OperationRoundResult:
        """点「前往挑战」→ 到达验证:首领简报横幅或节点画面出现。

        简报横幅不点击会在数秒内自动关闭进入节点画面,两种到达态都认;
        修改已挑战编队会先弹「更换编队确认」(与选关屏同名弹窗同构)。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _BANNER_SCREEN, '文本-首领特性').is_success:
            return self.round_success()
        if self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success:
            return self.round_success()
        if self.round_by_find_area(
                screen, _SELECT_SCREEN, '按钮-更换编队确认').is_success:
            self.ctx.controller.click(
                get_area_center_point(self.ctx, _SELECT_SCREEN, '按钮-更换编队确认'),
                press_time=0.15)
            return self.round_retry('确认更换编队弹窗', wait=2.5)
        if self.round_by_find_area(screen, _TEAM_SCREEN, '按钮-前往挑战').is_success:
            # 点击位 = 编队屏实测点击区(area「点击-前往挑战」);其文本识别区
            # 偏宽,中心与实测点击位不同,点击区独立建档
            self.ctx.controller.click(
                get_area_center_point(self.ctx, _TEAM_SCREEN, '点击-前往挑战'),
                press_time=0.15)
            return self.round_retry('点击前往挑战', wait=2.5)
        return self.round_retry('画面异常(不在编队屏也未见简报)', wait=1.5)

    @node_from(from_name='前往挑战')
    @node_from(from_name='进入编队屏', status='BANNER_UP')
    @node_from(from_name='进入编队屏', status='BATTLE_ONGOING')
    @operation_node(name='战斗推进', node_max_retry_times=8)
    def _battle(self) -> OperationRoundResult:
        """组合 :class:`TlAsBattleOp`(简报 → 秘技开战 → 战斗 → 结算推进)。"""
        op_result = self.battle_op.execute()
        return self.round_by_op_result(op_result)

    @node_from(from_name='战斗推进', status=TlAsBattleOp.STATUS_DONE)
    @operation_node(name='返回选关', node_max_retry_times=12)
    def _click_back(self) -> OperationRoundResult:
        """最终结算点「返回末日幻影」已在战斗推进内点击;本节点处理快速通关
        奖励弹窗 → 选关屏。

        3 星通关最高难度时游戏弹「快速通关」补发前置难度奖励(确认 + 一层
        「点击空白处关闭」提示),两步都处理后到达选关屏。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _SELECT_SCREEN, '标题-末日幻影行').is_success:
            return self.round_success(TlApocalypticShadowChallengeOp.STATUS_SUCCESS)
        if self.round_by_find_area(
                screen, _SELECT_SCREEN, 'AFTER_BATTLE_QUICK_PASS_CONFIRM').is_success:
            self.ctx.controller.click(
                get_area_center_point(
                    self.ctx, _SELECT_SCREEN, 'AFTER_BATTLE_QUICK_PASS_CONFIRM'),
                press_time=0.15)
            return self.round_wait('领取快速通关奖励', wait=2)
        click = self.round_by_find_and_click_area(
            screen, _RESULT_SCREEN, '按钮-返回末日幻影', success_wait=2)
        if click.is_success:
            return self.round_wait('返回末日幻影中', wait=2)
        return self.round_retry('等待返回按钮', wait=1.5)


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    ctx.start_running()
    op = TlApocalypticShadowChallengeOp(
        ctx,
        ['姬子•启行', '瓦尔特', '知更鸟', '丹恒•腾荒', '黄泉', '卡芙卡', '黑天鹅', '灵砂'],
        (3, 3),
    )
    op.execute()


if __name__ == '__main__':
    __debug()
