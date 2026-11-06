"""末日幻影节点战斗推进:简报关闭 → 前进+秘技+开战 → 战斗等待 → 结算推进。

单节点大循环按画面特征每轮重新分流(实机验证过的结构,避免子节点边冲突)。
起点 = 首领简报横幅(挑战发起后弹出)或节点画面(大世界);终点 = 最终结算页
点「返回末日幻影」(STATUS_DONE)。"""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.operations.sr_operation import SrOperation
from sr_od.operations.technique import UseTechnique

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext

_SELECT_SCREEN: str = '末日幻影-选关'
_BANNER_SCREEN: str = '末日幻影-首领简报'
_RESULT_SCREEN: str = '末日幻影-节点结算'
_NODE_SCREEN: str = '忘却之庭-节点画面'  # 节点画面左栏锚(查看详情)与 FH 同构,复用其 area


class TlAsBattleOp(SrOperation):
    """节点战斗推进(单循环):简报关闭 → 前进+秘技+开战 → 战斗等待 → 结算推进。

    起点 = 首领简报横幅(挑战发起后弹出)或节点画面(大世界);终点 = 最终
    结算页点「返回末日幻影」(STATUS_DONE)。单节点大循环按画面特征每轮
    重新分流(实机验证过的结构,避免子节点边冲突)。节点画面开战顺序 =
    前进接近 → 施放秘技(复用框架 :class:`UseTechnique`;攻击型秘技施放即
    入战斗,增益型秘技施放后下一轮点击开战)→ 点击画面中心开战。"""

    STATUS_DONE: ClassVar[str] = '最终结算完成'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='末日幻影 节点战斗')
        # 命名避开框架 Operation._current_node(执行期被赋为当前节点对象,撞名
        # 会让本记录被覆盖,日志打出对象 repr)
        self._brief_node_no: int = 0     #: 简报标题实读的当前节点号(1/2;简报外为 0)
        self._brief_pending: bool = False  #: 简报已确认待进节点画面(首战开战守卫)
        self._tech_used: bool = False    #: 当前节点秘技已施放(防增益型秘技重复施放;
                                         #  「前往节点二」推进时重置,新节点新秘技点)

    @operation_node(name='战斗循环', is_start_node=True, node_max_retry_times=720)
    def _battle_loop(self) -> OperationRoundResult:
        """单节点大循环,按画面特征每轮重新分流:

        1. 结算页 → 「前往节点二」(重置秘技标记)或「返回末日幻影」(STATUS_DONE);
        2. 首领简报横幅 → 实读节点号 + 点空白关闭;
        3. 节点画面(左栏「查看详情」;战斗中左栏被战斗 UI 替换故不误判):
           未施秘技 = 前进接近 + 施放秘技(攻击型施放即入战斗,本轮结束重新
           分流);已施 = 前进 + 点击画面中心开战;
        4. 其余 = 战斗中等待(每 5s 一轮;720 轮 ≈ 1 小时兜底,防异常卡死)。"""
        screen = self.last_screenshot

        if self.round_by_find_area(screen, _RESULT_SCREEN, '标题-挑战结束').is_success:
            if self.round_by_find_area(screen, _RESULT_SCREEN, '按钮-返回末日幻影').is_success:
                self.ctx.controller.click(Point(1240, 949), press_time=0.15)
                return self.round_success(TlAsBattleOp.STATUS_DONE, wait=2.5)
            # 「前往节点二/三」按钮同位(结算页布局恒定,文本随节点轮换)——
            # 统一按区域点击并重置秘技标记(新节点新秘技点)
            self.ctx.controller.click(Point(1243, 949), press_time=0.15)
            self._tech_used = False
            return self.round_retry('前往下一节点', wait=3)

        if self.round_by_find_area(screen, _BANNER_SCREEN, '提示-点击空白处关闭').is_success:
            # 简报标题区的「节点一/二/三」位置恒定(说明行数只影响下方区域),
            # 实读记入状态——节点流转的判定锚比结算页按钮文本更稳
            if self.round_by_find_area(screen, _BANNER_SCREEN, '标题-节点二行').is_success:
                self._brief_node_no = 2
                self._brief_pending = True
            elif self.round_by_find_area(screen, _BANNER_SCREEN, '标题-节点三行').is_success:
                self._brief_node_no = 3
                self._brief_pending = True
            elif self.round_by_find_area(screen, _BANNER_SCREEN, '标题-节点一行').is_success:
                self._brief_node_no = 1
                self._brief_pending = True
            self.ctx.controller.click(Point(960, 950), press_time=0.15)
            return self.round_retry(f'关闭首领简报(节点{self._brief_node_no})', wait=2.5)

        if self.round_by_find_area(screen, _NODE_SCREEN, '面板-查看详情').is_success:
            self._brief_pending = False
            if not self._tech_used:
                # 未施秘技:前进接近后施放(攻击型秘技施放即入战斗,本轮结束
                # 重新分流走战斗等待;增益型下一轮走到点击开战分支)
                self.ctx.controller.move('w', press_time=2)
                tech_op = UseTechnique(self.ctx)
                tech_op.execute()
                self._tech_used = True
                return self.round_retry('施放秘技', wait=3)
            self.ctx.controller.move('w', press_time=2)
            self.ctx.controller.click(Point(960, 540), press_time=0.1)
            return self.round_retry(f'节点{self._brief_node_no} 发起战斗', wait=5)

        return self.round_wait('战斗进行中', wait=5)
