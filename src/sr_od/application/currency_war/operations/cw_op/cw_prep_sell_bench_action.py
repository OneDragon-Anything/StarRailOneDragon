"""卖备战席角色动作 op(CwActionSellBenchOp)——参数面迁移形态:op 机械面
全自持(op 内现读点位表 + 模块级 ``drag_char_guarded`` 原语 + ``sell_point``
出售区单一源,零 executor 点表零 gs 读),拖点 = row_area_centers 裸中心
(角色拖动族权威派生式,拖点权威分域申报见 prep_actions.row_area_centers
docstring)。机械执行后 op 内直调自己的上报函数
``report_action_sell_bench_param``(零分派,op-layer.md §1.2 动作 op 契约)。
非终结。

双域词表动作(备战域经 ``PrepExecEnv``、商店域经 ``ShopExecEnv`` 执行链):
env 仅消费两处元数据——``executor.screen_name``(域坐标权威画面分派)与
``ledger``(商店访问账卖出计数),其余零消费。``executor=None`` 形态 =
缺省备战档 + ledger 照走(getattr 容缺读):现役装配面恒注入完整 executor,
None = MCP 直调等「无 env 可用」的合法形态,不触发 ShopExecEnv docstring
所述「端口未注入即 AttributeError」(该描述针对旧「op 经 env.executor 消费
_ctx/_op 点表」形态,本 op 已零消费 executor)。

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
from sr_od.application.currency_war.kernel.cw_action_report.sell_bench import (
    report_action_sell_bench_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_obs_core import SCREEN_NAME
from sr_od.application.currency_war.kernel.cw_vocab import CwActionSellBenchParam
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.prep_actions import (
    drag_char_guarded,
    drag_overlay_block_status,
    prep_drag_overlay_gate,
    row_area_centers,
    sell_point,
)
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
        ShopExecEnv,
    )
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionSellBenchOp(CwOperation):
    """卖备战槽角色:drag 槽中心 → 出售区(落点经 ``sell_point`` 单一源)。
    起点:货币战争-备战或货币战争-备战-开商店画面(动作执行时,域坐标
    权威画面经 env 元数据分派);终点:拖动备战槽角色到出售区卖出;动作已
    发出并上报逻辑态,停留原画面(判效归下一帧观察)。非终结。

    参数面(词表 CwActionSellBenchParam 为单一源):bench_idx(bench 槽位表
    下标 0-8 定长 9 槽,固定槽位形态零布局档参数)+ income/expect/reason/
    convert_reason/route_tag(记录/代际防线/归因字段,词表 docstring 申报)。
    记账 = 槽位反查产物形态(记账路径总契约第五适用者,词表 docstring 申报)。

    双域执行说明:备战域经 ``PrepExecEnv``、商店域经 ``ShopExecEnv``——
    env 仅消费两处元数据:①``executor.screen_name``(域坐标权威画面分派:
    备战 runner 无该属性缺省回落备战画面档,商店域 = 商店开画面档,两档
    自备同名 备战栏/出售区 area);②``ledger``(商店访问账卖出计数,备战
    env 无该字段跳过)。其余零消费——点位表 op 内现读(row_area_centers)、
    守卫双域统一生效(商店域不再 getattr 容缺跳过越界守卫)。
    ``executor=None`` 形态 = 缺省备战档 + ledger 照走(getattr 容缺读):
    现役装配面恒注入完整 executor,None = MCP 直调等「无 env 可用」的
    合法形态,不触发 ShopExecEnv docstring 所述 AttributeError。

    :param param: 卖备战席动作参数(字段语义与取值时机见词表类 docstring;
        直调传参 = 当帧 extras ``bench.slots`` 下标 0-8,kind=unit 才有
        角色,口径同 CwSellBenchBySlot;expect 可选代际防线)。
    :param env: 执行环境(代码内组装传入;可省 = 缺省 None,按备战画面档
        解析坐标——单件会话直调场景 op 跑在备战画面语义正确;商店画面
        直调卖备战席需传带 ShopActionExecutor 的 env 以按商店档解析)。
    """

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionSellBenchParam,
                 env: PrepExecEnv | ShopExecEnv | None = None):
        CwOperation.__init__(self, ctx, op_name='CwActionSellBenchOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='sell_bench', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """卖备战槽角色:drag 槽中心 → 出售区机械拖拽。

        执行坐标边(op 自持):bench_idx = 状态容器槽位表下标直取备战栏-N
        area 序(零换算)。守卫断言 AssertionError 响亮暴露零拖拽(越界
        fail-closed;负下标回环 = 静默错点同防,下界显式闭合;空点表 =
        建档漂移哨语义同断言)。
        """
        action: CwActionSellBenchParam = self.param
        idx = int(action.bench_idx)
        # —— 域坐标权威画面(env 元数据分派;零副作用元数据读)——
        _screen_name = str(getattr(
            getattr(self.env, 'executor', None), 'screen_name', SCREEN_NAME))
        # —— 点位现读(screen_info 静态档;零截图零识别零 gs)——
        pts = row_area_centers(self.ctx, '备战栏', screen_name=_screen_name)
        if not (0 <= idx < len(pts)):
            # 参数违法由 op 自判(flow/action_ops.md §1 决策侧参数现算
            # 契约):越界 = 决策逻辑 bug,守卫断言响亮暴露零拖拽(禁兜底
            # 坐标/禁负下标回环);len(pts)==0 = 画面档缺失/档案损坏
            # (建档漂移哨,同断言响亮暴露)。
            raise AssertionError(
                f'CwActionSellBenchParam bench_idx={idx} 越界'
                f'(0-{len(pts) - 1};画面档={_screen_name})')
        if cw_sim_ports.mechanical_io_allowed():
            # 浮层守卫(执行前输入契约拒绝):合成确认浮层/角色详情面板在场
            # 时拖拽被游戏静默吞,先拦(动作没发出,受阻码走回执映射)。
            # sim 门内 = sim 零触及。
            overlay_hit = prep_drag_overlay_gate(self)
            if overlay_hit is not None:
                log.info('[cw][sell-bench] 浮层在场(%s)→ 拖拽未发出',
                         overlay_hit)
                return self.round_fail(
                    status=drag_overlay_block_status(overlay_hit))
            # 实机机械段(失焦守卫 + 统一拖拽原语,中心拖 + hold0;
            # 落点 = 出售区单一源,sell_point 的 area 缺失 RuntimeError
            # 上抛 = 建档漂移哨,共享原语既有形态保留)。
            drag_char_guarded(self, self.ctx, pts[idx],
                              sell_point(self.ctx, screen_name=_screen_name))
            # 卖出动画固定等待(用户口述口径 #21:卖出动画 1s;非判效)。
            time.sleep(1.0)
        else:
            # sim:机械拖拽静默跳过(直连旁路 port 检查,sim-design.md
            #);自上报照走(两执行面同源)。
            pass
        # 商店访问账(shop 域 visit 汇总口径;备战 env 无 ledger 字段 =
        # 备战域无访问账概念,跳过——发出即记账,与买/刷 op 同位)。
        _led = getattr(self.env, 'ledger', None)
        if _led is not None:
            _led.total_sell += 1
        # —— 自上报(机械发出后;槽位反查记账,op 零感知)——
        outcome = None
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            outcome = report_action_sell_bench_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        detail = f'卖备战槽{idx + 1} ✓(发出即记账,落地归观察对账)'
        if outcome is not None and not outcome.applied:
            # 记账拒单如实进 round detail(直调方经 round 结果感知拒单;
            # 机械成功语义不变——拖拽确实已发生;禁补拖:拒单 = 账未落,
            # 补拖会双卖,处置 = 重读板面按新状态重派)。
            detail += f'；记账拒单:{outcome.reason}(拖拽已发生,账未落)'
        log.info(f'[cw][sell_bench] {detail}')
        return self.round_success(detail)
