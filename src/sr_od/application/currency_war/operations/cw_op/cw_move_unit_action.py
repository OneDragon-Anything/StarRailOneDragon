"""统一拖动动作 op(CwActionMoveUnitOp)——部署统一批(用户指令
2026-10-30「统一拖动角色 Op」):全域移动四元组载荷,机械拖拽源点位 →
目标点位。坐标参数面迁移形态:机械半自持(op 内静态解析点位表,零
executor 点表零 gs 读),拖点 = row_area_centers 裸中心(角色拖动族权威
派生式,拖点权威分域申报见 prep_actions.row_area_centers docstring)。
非终结。

机械执行零判效:拖后不做像素验证,落地事实归观察侧 reconcile 对账;
拖拽静默不生效属执行环境噪声,由下一入口 heavy 实读对账暴露,重试 =
决策循环按新观察自然重派。换位交互提示(单局实机样本申报):占槽换位
存在「前排未生效/后排成功」的不一致样本(未钉结论)——本 op 不判断
占位、不拒、禁静默换槽(拖拽语义 = 游戏规则),失败治理归计划执行期
拖动与重观察交替 + 级联卡死出口 + 决策循环重派,零动作层补丁。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.move_unit import (
    report_action_move_unit_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionMoveUnitParam
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.prep_actions import (
    drag_char_guarded,
    drag_overlay_block_status,
    prep_drag_overlay_gate,
    row_area_centers,
)
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionMoveUnitOp(CwOperation):
    """统一拖动(front/back/bench 任意源 → 任意目标)。非终结。
    起点:货币战争-备战画面(动作执行时);终点:拖动一个角色到目标位;动作已发出并上报逻辑态,停留原画面(判效归下一帧观察)。

    参数面(词表 CwActionMoveUnitParam 为单一源):四元组载荷
    (src_domain/src_slot/dst_domain/dst_slot,bench 0 基、front/back
    排内 1 基画面槽号)+ back_slot_count(后排槽位画面物理总数 6-9,
    src/dst 域均非 back 时忽略,可省缺省 6;直调后排槽按当帧 extras
    deploy_cap−4 传)+ reason/expect(归因记录与代际防线,词表 docstring
    申报)。记账 = 槽位反查产物形态(记账路径总契约第三适用者,
    词表 docstring 申报)。

    与 DragCwChar(operations/actions 域,通用拖拽原语)基差异:其
    from_idx/to_idx 恒 1 基画面物理槽位(不分域);本 op 四元组按域分基
    (bench 0 基槽位表下标 / front·back 排内 1 基画面槽号)——同族拖动
    动作两类基不同,跨类传参先对表,勿互填参数(DragCwChar 类 docstring
    已有对称声明)。

    :param param: 统一拖动动作参数(字段语义与取值时机见词表类 docstring)。
    :param env: 备战域执行环境(代码内组装传入;可省 = 缺省 None,本 op
        机械半自持后零 env 消费,形参保留 = 注册表构造签名兼容)。
    """

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionMoveUnitParam,
                 env: PrepExecEnv | None = None):
        CwOperation.__init__(self, ctx, op_name='CwActionMoveUnitOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='move_unit', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """统一拖动:源点位 → 目标点位机械拖拽。

        执行坐标边(op 自持):bench = 备战栏 area 序(状态容器下标 =
        area 序,0 基)/ front = 前排 area 序(排内 1 基画面槽号 - 1)/
        back = back_slot_count 布局档 area 序(扩格 7-9 槽按档位表解析)。
        静态合法域(bench 0-8 / front 1-4 / back 1-画面后排槽数;域枚举
        外)守卫断言 AssertionError 响亮暴露零拖拽(越界 fail-closed;
        负下标回环 = 静默错点同防,下界显式闭合)。
        """
        action: CwActionMoveUnitParam = self.param
        from sr_od.application.currency_war.obs.cw_back_layout import (
            _layout_prefixes,
        )
        # —— 守卫断言(参数语义唯一所有者 = op;违法响亮暴露零拖拽,
        # 禁兜底坐标/禁负下标回环静默错点)——
        back_needed = 'back' in (action.src_domain, action.dst_domain)
        if back_needed and action.back_slot_count not in _layout_prefixes():
            raise AssertionError(
                f'CwActionMoveUnitParam back_slot_count='
                f'{action.back_slot_count} 域外(6-9,布局档键域)')

        def _pt(domain: str, slot: int):
            if domain == 'bench':
                pts = row_area_centers(self.ctx, '备战栏')
                if not 0 <= slot < len(pts):
                    raise AssertionError(
                        f'CwActionMoveUnitParam bench slot={slot} 越界'
                        f'(0-{len(pts) - 1})')
                return pts[slot]
            if domain == 'front':
                pts = row_area_centers(self.ctx, '前排')
                if not 1 <= slot <= len(pts):
                    raise AssertionError(
                        f'CwActionMoveUnitParam front slot={slot} 越界'
                        f'(1-{len(pts)})')
                return pts[slot - 1]
            if domain == 'back':
                pts = row_area_centers(
                    self.ctx, _layout_prefixes()[action.back_slot_count])
                if not 1 <= slot <= len(pts):
                    raise AssertionError(
                        f'CwActionMoveUnitParam back slot={slot} 越界'
                        f'(1-{len(pts)};back_slot_count='
                        f'{action.back_slot_count})')
                return pts[slot - 1]
            raise AssertionError(
                f'CwActionMoveUnitParam domain={domain!r} 非法'
                '(front/back/bench)')

        src = _pt(action.src_domain, int(action.src_slot))
        dst = _pt(action.dst_domain, int(action.dst_slot))
        if cw_sim_ports.mechanical_io_allowed():
            # 浮层守卫(执行前输入契约拒绝):合成确认浮层/角色详情面板在场
            # 时拖拽被游戏静默吞,先拦(动作没发出,受阻码走回执映射)。
            # sim 门内 = sim 零触及。
            overlay_hit = prep_drag_overlay_gate(self)
            if overlay_hit is not None:
                log.info('[cw][move] 浮层在场(%s)→ 拖拽未发出', overlay_hit)
                return self.round_fail(
                    status=drag_overlay_block_status(overlay_hit))
            # 实机机械段(失焦守卫 + 统一拖拽原语,中心拖 + hold0)。
            drag_char_guarded(self, self.ctx, src, dst)
            # 拖动触发的羁绊徽章动画口径(screen_flow_timing #10「都等 2s」
            # 简单方案;固定时长等待,非判效)。
            time.sleep(2.0)
        else:
            # sim:机械拖拽静默跳过(直连旁路 port 检查,sim-design.md
            # §6.5);自上报照走(两执行面同源)。
            pass
        # —— 自上报(机械发出后;槽位反查记账,op 零感知)——
        outcome = None
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            outcome = report_action_move_unit_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        detail = (f'拖动{action.src_domain}{action.src_slot}'
                  f'->{action.dst_domain}{action.dst_slot} ✓'
                  '(发出即记账,落地归观察对账)')
        if outcome is not None and not outcome.applied:
            # 记账拒单如实进 round detail(直调方经 round 结果感知拒单;
            # 机械成功语义不变——拖拽确实已发生;不分支重试、不读屏验证,
            # 零判效/零重试纪律不受触及)。
            detail += f'；记账拒单:{outcome.reason}(拖拽已发生,账未落)'
        log.info(f'[cw][move] {detail}')
        return self.round_success(detail)
