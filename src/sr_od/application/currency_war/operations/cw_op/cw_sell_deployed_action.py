"""卖上阵角色动作 op(CwActionSellDeployedOp)——动作 op 重组换壳
(原 ``SellDeployedOp``)。参数面迁移形态:机械半自持(op 内现读点位表
+ 模块级 ``drag_char_guarded`` 原语 + ``sell_point`` 出售区单一源,零
executor 点表零 gs 读——cap 守卫改 back_slot_count 参数静态闭合,
决策侧参数现算契约),拖点 = row_area_centers 裸中心(角色拖动族权威
派生式,拖点权威分域申报见 prep_actions.row_area_centers docstring)。
机械执行后 op 内直调自己的上报函数 ``report_action_sell_deployed_param``
(零分派,op-layer.md §1.2 动作 op 契约)。非终结。

机械执行零判效:拖后不做像素验证,落地事实归观察侧 reconcile 对账;
拖拽静默不生效属执行环境噪声,由下一入口观察对账暴露,重试 = 决策
循环按新观察自然重派。记账拒单帧(越界/陈旧提案 = 账未落但拖拽已
发出)如实进 round detail,直调方按 detail 感知后处置 = 重读板面按
新状态重派,禁补拖(补拖会双卖)。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.sell_deployed import (
    report_action_sell_deployed_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionSellDeployedParam
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.prep_actions import (
    drag_char_guarded,
    row_area_centers,
    sell_point,
)
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionSellDeployedOp(CwOperation):
    """卖上阵角色:drag 排槽中心 → 出售区(落点经 ``sell_point`` 单一源)。
    起点:货币战争-备战画面(动作执行时);终点:拖动上阵角色到出售区卖出;动作已发出并上报逻辑态,停留原画面(判效归下一帧观察)。
    非终结。

    参数面(词表 CwActionSellDeployedParam 为单一源):deployed_idx
    (deployed 视图统一槽位表下标,前排 0-3 / 后排 4+ 排内 1 基——
    排内槽号 = deployed_idx 固定双射内联换算,禁传二元组) +
    back_slot_count(后排槽位画面物理总数 6-9,deployed_idx < 4 前排
    域忽略,可省缺省 6;直调后排槽按当帧 extras deploy_cap−4 传)+
    income/reason/expect(记录与代际防线字段,词表 docstring 申报)。
    记账 = 槽位反查产物形态(记账路径总契约第四适用者,词表 docstring
    申报)。

    :param param: 卖上阵动作参数(字段语义与取值时机见词表类 docstring)。
    :param env: 备战域执行环境(代码内组装传入;可省 = 缺省 None,本 op
        机械半自持后零 env 消费,形参保留 = 注册表构造签名兼容)。
    """

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionSellDeployedParam,
                 env: PrepExecEnv | None = None):
        CwOperation.__init__(self, ctx, op_name='CwActionSellDeployedOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='sell_deployed', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """卖上阵角色:排槽中心 → 出售区机械拖拽。

        执行坐标边(op 自持):deployed_idx → (row,排内 1 基物理槽号)
        固定双射内联算术(0-3=前排 1-4;4+=后排 1-N,拖点按
        back_slot_count 布局档静态解析——扩格帧后排 7-9 可直卖)。
        静态合法域(0 ≤ deployed_idx < 前排容量+back_slot_count;槽号
        ≤ 画面该排点位表)守卫断言 AssertionError 响亮暴露零拖拽
        (越界 fail-closed;负下标回环 = 静默错点同防,下界显式闭合)。
        """
        action: CwActionSellDeployedParam = self.param
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            DEPLOYED_FRONT_CAPACITY,
        )
        from sr_od.application.currency_war.obs.cw_back_layout import (
            _layout_prefixes,
        )
        # —— 守卫断言(参数语义唯一所有者 = op;违法响亮暴露零拖拽,
        # 禁兜底坐标/禁负下标回环静默错点)——
        idx = int(action.deployed_idx)
        if idx >= DEPLOYED_FRONT_CAPACITY \
                and action.back_slot_count not in _layout_prefixes():
            # 布局档键域外禁静默按 6 兜底(前排域不查——域不涉则忽略,
            # MoveUnit 同式)。
            raise AssertionError(
                f'CwActionSellDeployedParam back_slot_count='
                f'{action.back_slot_count} 域外(6-9,布局档键域)')
        cap_total = DEPLOYED_FRONT_CAPACITY + action.back_slot_count
        if not (0 <= idx < cap_total):
            # cap 上界 = 参数静态闭合(原 gs 现读 back_capacity_of 中途
            # 读数已拔除,机械路径零 gs 依赖)。
            raise AssertionError(
                f'CwActionSellDeployedParam deployed_idx={idx} '
                f'越界(0-{cap_total - 1};back_slot_count='
                f'{action.back_slot_count})')
        row = 'front' if idx < DEPLOYED_FRONT_CAPACITY else 'back'
        slot_no = (idx + 1 if row == 'front'
                   else idx - DEPLOYED_FRONT_CAPACITY + 1)
        prefix = '前排' if row == 'front' \
            else _layout_prefixes()[action.back_slot_count]
        pts = row_area_centers(self.ctx, prefix)
        if not (1 <= slot_no <= len(pts)):
            raise AssertionError(
                f'CwActionSellDeployedParam {row}槽号 {slot_no} 超出画面'
                f'点位表({len(pts)} 槽——扩格帧需 screen_info 补建档)')
        src = pts[slot_no - 1]
        if cw_sim_ports.mechanical_io_allowed():
            # 实机机械段(失焦守卫 + 统一拖拽原语,中心拖 + hold0;
            # 落点 = 出售区单一源,sell_point 的 area 缺失 RuntimeError
            # 上抛 = 建档漂移哨,共享原语既有形态保留)。
            drag_char_guarded(self, self.ctx, src, sell_point(self.ctx))
            # 卖出动画固定等待(用户口述口径 #21:卖出动画 1s;非判效)。
            time.sleep(1.0)
        else:
            # sim:机械拖拽静默跳过(直连旁路 port 检查,sim-design.md
            #);自上报照走(两执行面同源)。
            pass
        # —— 自上报(机械发出后;槽位反查记账,op 零感知)——
        outcome = None
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            outcome = report_action_sell_deployed_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        detail = f'卖{row}排{slot_no} ✓(发出即记账,落地归观察对账)'
        if outcome is not None and not outcome.applied:
            # 记账拒单如实进 round detail(直调方经 round 结果感知拒单;
            # 机械成功语义不变——拖拽确实已发生;禁补拖:拒单 = 账未落,
            # 补拖会双卖,处置 = 重读板面按新状态重派)。
            detail += f'；记账拒单:{outcome.reason}(拖拽已发生,账未落)'
        log.info(f'[cw][sell_deployed] {detail}')
        return self.round_success(detail)
