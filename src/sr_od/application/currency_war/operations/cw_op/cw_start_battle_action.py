"""出战动作 op(CwActionStartBattleOp)——单击原子形态:定位动作本体 →
单击一次 → 自上报,零收尾零验证——点击后世界什么样(弹窗渲染/画面转移)
op 不管,交回主循环下一帧重新识别(点击后弹窗归独立弹窗 op,经主循环
阶段一身份分发接管)。机械执行后 op 内直调自己的上报函数
``report_action_start_battle_param``(动作 op 契约:逻辑推进 = 上报时,
跳过子态事实随上报携带)。

备战环 / 达标分支动作发出核 / 恢复局锁定直出战三路径经同一注册表分派
到达本 op,禁各写一套点击段。执行序(单一语义):
  1. 槽位双形态定位(动作本体定位豁免,非段间识别):查「按钮-出战」
     (货币战争-备战 + 货币战争-备战-开商店两屏同查)——免战牌激活时
     出战按钮变「跳过(N/N)」(直跳战斗),查不到「出战」时 fallback 查
     「按钮-跳过」(同语义点它);
  2. ``mechanical_io_allowed()`` 门下 mouse_move + click 单击一次(sim
     装配后机械分支静默跳过,状态副本反应由自上报承接);
  3. 自上报(跳过子态事实携带;上报后一行声明喂入,实机端口未装 = no-op,
     sim 装配后驱动后端 battle_resolve / battle_skip);
  4. round_success 返回主循环(备战画面 op 正常终结,终结等待 =
     ``terminal_wait``)。

**round 结果契约**:``execute()`` 的成功态 = **点击已执行**(找不到按钮 =
round_fail 未发出,交回主循环重新判定;按钮 area 缺失零检查 = 取值直接
使用自然异常报错,禁兜底坐标),消费面 = runner 包络 ``last_launch_ok``
旁路(round 结果映射)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.start_battle import (
    report_action_start_battle_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    area_center,
)
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionStartBattleOp(CwOperation):
    """出战单击(点击出战/跳过 → 自上报返回主循环;语义见模块头)。
    起点:货币战争-备战画面(动作执行时);终点:点击已执行并上报逻辑态,
    停留原画面(弹窗渲染/画面转移归下一帧观察,判效零内建)。

    终结动作:发出即本备战访问终结(返回主循环战斗分支);终结等待 =
    ``terminal_wait``(消费点经注册表读类属性;出战点击后的弹窗渲染窗由
    本等待覆盖,弹窗处理归独立弹窗 op)。
    """

    #: 终结动作(发出即本备战访问终结)。
    terminal = True

    #: 终结返回等待秒数(覆盖出战点击后的弹窗渲染窗;消费点经注册表读
    #: 类属性)。
    terminal_wait = 3

    def __init__(self, ctx: SrContext, param: object,
                 env: PrepExecEnv):
        CwOperation.__init__(self, ctx, op_name='CwActionStartBattleOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='start_battle', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """出战单击序列(成功态契约 = 点击已执行,见模块头)。

        免战子态:「免战牌」策略激活时出战按钮变「跳过(N/N)」(直跳战斗,
        免战 2 次)——查不到「出战」时查「按钮-跳过」,同语义点它(推进
        节点)。跳过子态事实随自上报携带(免战次数递减语义 = 上报时,非
        「验证落地后」——op 零验证)。

        ⚠️ 正交态查找:免战与「商店开」**可叠加**(跳过按钮 + 牌区展开
        同帧)——叠加帧识别为货币战争-备战-开商店(它盖基态 id_mark),
        按单一屏查「按钮-跳过」会落空。跳过/出战按钮在两屏同一位置 →
        查找不锁死单一屏(备战 + 开商店都查);按钮 area 单源归备战屏,
        不复制双源。

        找不到按钮 = 动作未执行(round_fail「未执行:找不到按钮」)→ 返回
        主循环重新判定(不炸;画面真未知由未知兜底链接)。
        """
        action = self.param
        env = self.env
        ex = env.executor
        screen = ex._op.screenshot()
        btn_screens: list[str] = [SCREEN_NAME, '货币战争-备战-开商店']
        btn_area = '按钮-出战'
        btn_found = any(
            ex._op.round_by_find_area(screen, _sc, btn_area).is_success
            for _sc in btn_screens)
        if not btn_found:
            if any(ex._op.round_by_find_area(screen, _sc, '按钮-跳过',
                                             crop_first=False).is_success
                   for _sc in btn_screens):
                btn_area = '按钮-跳过'
                log.info('[cw][battle] 出战按钮为子态「跳过」(免战牌激活)→ 点跳过')
            else:
                log.warning('[cw!][battle] 未执行:找不到按钮'
                            '(备战+开商店两屏查空)→ 交回外循环重判')
                return self.round_fail('未执行:找不到按钮')
        btn = area_center(ex._ctx, btn_area)
        skip_substate = btn_area == '按钮-跳过'
        env.skip_substate = skip_substate   # 回执 extra 保留证据消费(runner 包络)
        if cw_sim_ports.mechanical_io_allowed():
            ex._ctx.controller.mouse_move(btn)
            ex._ctx.controller.click(btn)
        # else sim:机械执行分支静默成功(直连旁路 port 检查,状态副本反应
        # 由紧随的自上报承接)
        # —— 自上报(机械发出后;跳过子态事实携带,免战递减 = 上报时)——
        # 上报后一行声明喂入(动作后果声明化喂入契约;实机端口未装 = no-op,
        # sim 装配后驱动后端 battle_resolve)。
        world_decl: WorldDecl | None = None
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            outcome = report_action_start_battle_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'),
                session=getattr(getattr(self.ctx, 'cw_match', None),
                                'session', None),
                skip_substate=skip_substate)
            world_decl = outcome.world_decl
            cw_sim_ports.declare_world(world_decl)
        log.info('[cw][battle] 出战已点击%s → 交回外循环',
                 '(跳过子态)' if skip_substate else '')
        return self.round_success('出战已点击', data=world_decl)
