"""银狼策划 pick 确认链动作 op(:class:`CwActionPickPlannerOp` 单类
文件,一 op 一文件 = op-layer.md :48;族契约与共享 env 见
``cw_overlay_pick_env``)。

机械语义:点卡选中 → 确认(建档「按钮-骇入确认」查找点击,确认钮查找
全族统一 = ``round_by_find_and_click_area``);确认点击后立即自上报完整
效果腿(``report_action_pick_planner_param``,leg_type/norm_item 经 env 透传)。
"""
from __future__ import annotations

import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_action_report.pick_planner import (
    report_action_pick_planner_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwActionPickPlannerParam,
)
from sr_od.application.currency_war.operations.cw_op.cw_overlay_pick_env import (
    OverlayPickExecEnv,
)
from sr_od.application.currency_war.operations.cw_screen.cw_screen_yinlang import (
    CwScreenYinLang,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwActionPickPlannerOp(SrOperation):
    """银狼策划 pick 确认链(统一动作工厂批4 迁入)。

    点卡选中(避开卡内「详情」按钮区的选中点几何归决策半 ``_card_point``
    单一源)→ 确认(建档「按钮-骇入确认」查找点击,全族统一;详情面板
    防御已拆,面板若真弹出归下一帧外循环自愈——用户裁定
    2026-09-14)。**即时上报**(action_ops.md §1 增补 2):确认点击后立即
    一口写完整效果腿(equip 入栏+后果链 / upgrade 变换+档行 / unknown
    留证 / unrouted 兜底零写),无发射/落地两相、无证据闩——确认未生效
    = 代码 bug,overlay 残留由外循环按当前画面重识别重派。"""

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionPickPlannerParam,
                 env: OverlayPickExecEnv):
        SrOperation.__init__(self, ctx, op_name='CwActionPickPlannerOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='pick_planner', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """机械执行(点卡 → 选中动画等待 → 确认)+ 立即上报完整结果。"""
        action = self.param
        env = self.env
        op = env.op
        target = env.target
        # 3. 点卡选中(⚠️ 避开卡内「详情」按钮区 x~880-950/y~420-450——手动
        # 点验 (755,400) 触发详情面板的实证;点卡身上部 y=310)
        op.ctx.controller.mouse_move(target)
        op.ctx.controller.click(target, press_time=op.CLICK_PRESS_TIME)
        time.sleep(1.2)   # 等选中动画
        # 点卡 = 机械单发(用户裁定 2026-09-14:详情面板检测拆;用户定性
        # = 详情弹出 = 点错所致,该面归选中点几何治理,面板检测是症状侧
        # 补丁)。面板若真弹出,后果归下一帧:本屏分发即门,外循环按当前画面
        # 重分派(详情 overlay 族分支/本 op 重走链)自愈。
        # 4. 点确认 = 建档「按钮-骇入确认」查找点击(round_by_find_and_click_area
        # 全族统一,用户裁定 2026-09-22;不带 until = 动作 op 禁验证——防线
        # 语义由外循环重识别+预算耗尽 bail 承接,验关半拆除——用户裁定
        # 2026-09-10;area 缺失 = 显式失败交框架轮次,兜底常量 CONFIRM 随批
        # 退役)。
        env.round_result = op.round_by_find_and_click_area(
            op.screenshot(), CwScreenYinLang.CARD_AREA_SCREEN, '按钮-骇入确认',
            success_wait=1.0)
        # 立即自上报完整结果(确认点击后一口写
        # 腿型分派效果——增补 2:点完即按成功上报,零判效零证据闩;
        # leg_type/norm_item 经 env kwargs 形态保持)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_pick_planner_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'),
                leg_type=env.leg_type, norm_item=env.norm_item)
        return self.round_success('策划选择确认链已发(结果已即时上报)')
