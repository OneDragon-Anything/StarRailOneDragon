"""遭遇节点 pick 确认链动作 op(:class:`CwActionPickEncounterOp` 单类
文件,一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

机械语义:点卡选中(建档「遭遇卡-其一/其二」area 取点,取值直接
使用——area 缺失零检查,使用点自然异常报错)→ 确认
机械部分完成即结束本次访问;机械链发出后直调自上报单口
``report_action_pick_encounter_param``(发出即写)。
"""
from __future__ import annotations

import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_action_report.pick_encounter import (
    report_action_pick_encounter_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickEncounterParam,
)
from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
    OverlayPickExecEnv,
)
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.operations.cw_screen._overlay_confirm import (
    safe_click,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_encounter import (
    CwScreenEncounter,
)
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext


class CwActionPickEncounterOp(CwOperation):
    """遭遇节点 pick 确认链(机械语义单一源,统一动作工厂 迁入)。

    点卡选中(建档「遭遇卡-其一/其二」area 取点,取值直接使用,area
    缺失零检查 = 使用点自然异常,禁兜底坐标)→ 确认步机械完成即结束本次访问
    (零验证(用户裁定:动作层不做效果验证,判效归下一帧观察):不读屏判「overlay 关没关」,落地由外循环重识别重派承载;
    「插空白点击取消选中→死循环」风险的防线 = 固定顺序确认链本身——
    机械语义单一源随体迁入本类)。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickEncounterParam,
                 env: OverlayPickExecEnv):
        CwOperation.__init__(self, ctx, op_name='CwActionPickEncounterOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_encounter', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行;轮次结果经 ``env.round_result`` 旁路回传。"""
        action = self.param
        env = self.env
        op = env.op
        idx = action.idx
        card_area = '遭遇卡-其一' if idx == 0 else '遭遇卡-其二'
        card = area_center(op.ctx, card_area, CwScreenEncounter.SCREEN_NAME)
        safe_click(op, card, tag='cw-encounter')
        time.sleep(0.8)
        # 确认 = 建档「按钮-选择」查找点击(round_by_find_and_click_area 全族
        # 统一,用户裁定;不带 until = 动作 op 禁验证;area 缺失
        # = 显式失败交框架轮次)。
        env.round_result = op.round_by_find_and_click_area(
            op.screenshot(), CwScreenEncounter.SCREEN_NAME, '按钮-选择',
            success_wait=1.0)
        # 发出即写(遭遇扩围批,用户裁定):机械链发出后立即
        # 写 chosen_encounter(值组装自容器 encounter payload 槽;暂态
        # 假值窗由外循环重派覆盖自愈,兑现回调消费防线 = 兑现后清)。
        # 上报后一行声明喂入(动作后果声明化喂入契约 = design.md §2.2
        # 契约 3;实机端口未装 = no-op,sim 装配后驱动后端 battle_resolve
        # ——遭遇「点击发出后即结束本次访问」选档落地即结算)。
        world_decl = None
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            outcome = report_action_pick_encounter_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
            world_decl = outcome.world_decl
            cw_sim_ports.declare_world(world_decl)
        return self.round_success('遭遇选择确认链已发(结果经旁路回传)',
                                  data=world_decl)
