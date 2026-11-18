"""穿装备动作 op(CwActionWearEquipOp)——坐标参数化机械动作(显式起点,
坐标兼记账反查键;op 机械面零读屏零定位:拖拽起点 = 参数 src_cx/src_cy,
目标拖点 = 槽位参数 + back_slot_count 静态解析,零截图选档)。机械执行后
**op 内直调自己的上报函数** ``report_action_wear_equip_param``(零分派;
上报侧按坐标伴随域反查记账,op 零感知)。非终结。

机械执行零判效(用户裁定「动作 op = 机械执行」,落地判定归观察侧
reconcile 对账):发出即记账,拖后零读屏零落地判定。拖拽静默不生效属
执行环境噪声,由下一入口 heavy 实读对账暴露,重派 = 决策循环按新观察
自然承接。装备域状态容器分支 = 上报函数单点(owned −1 + 目标域整表重建)。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.wear_equip import (
    report_action_wear_equip_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionWearEquipParam
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.prep_actions import (
    PREP_DRAG_SETTLE_WAIT_S,
    drag_overlay_block_status,
    prep_drag_overlay_gate,
    row_drag_points,
)
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionWearEquipOp(CwOperation):
    """穿装备动作 op——坐标参数化机械动作(显式起点,坐标兼记账反查键)。
    起点:货币战争-备战画面;终点:装备拖至目标角色排槽穿上,停留原画面。
    非终结(terminal=False);机械执行零判效:发出即记账,拖后零读屏,
    落地归下一入口 heavy 实读对账,重派 = 决策循环按新观察自然承接。

    参数面三分法(词表 cw_vocab.CwActionWearEquipParam 为单一源):
    - 动态坐标:src_cx/src_cy = owned 装备条目格心(1080p),从最近一帧
      analyze_screen extras.owned_equips 元素 cx/cy 取(读完立刻用;连穿
      多件时框架侧每件穿后重观察刷新,读数以最近一帧 extras 为准);
      记账 = 按此坐标反查(用户裁定「动作 op 上报坐标,game state 根据坐标
      找到内容」)——反查不到 = 记账拒单(wear_item_xy_unresolved),账不落
      (处置见下方契约 3:禁止补拖,交还框架决策循环);
    - 半固定槽位:row('front'|'back') + slot(排内画面物理槽位 1 基,
      前排 1-4/后排 1-N,记账目标定位键 = 该槽现任单位) + back_slot_count
      (后排槽数 6-9,front 行可省);
    - 语义参数(纯日志,机械面与记账面均零消费,可省):item_name/char_name
      仅进日志与 round detail,传不传不影响执行与记账。

    [记账反查契约(三条)]
    1. 反查时序不变式:上报反查消费拖前快照;重观察刷新必须晚于上报;
    2. 记账后→重观察前的坐标伴随域陈旧条目窗口禁消费(框架侧由穿戴/
       重观察交替保证);
    3. 反查唯一性前提:同一快照内坐标↔装备一一对应(观察路径 = 单格单件
       逐格分类保证);反查不到 = 记账拒单(wear_item_xy_unresolved,拖拽
       已发生、账未落;round detail 会带拒单码)。**拒单后禁止补拖**(拖拽
       已发生,再拖 = 二次拖拽)——处置 = 交还框架决策循环(由框架观察链
       刷新对照表后自然重派),勿自行换坐标重试(重读 extras 取新坐标解不了
       对照表陈旧,恒拒单);用旧坐标重试 = 盲拖错格+错账。反查命中但名单
       缺条目 = 禁消费窗口违反,以异常响亮暴露,非拒单路径。
       直调方无对照表刷新手段(观察工具只读不写状态)→ **连穿场景每件之间
       需要一次对照表刷新,无刷新手段则按单件会话使用**(一坐标一调用一
       观察对账,连穿交还框架)。

    MCP run_operation 示例:
      args={"src_cx":1740,"src_cy":210,"row":"front","slot":2,
            "back_slot_count":6,"item_name":"量产型装甲","char_name":"银狼"}

    守卫断言:row 非法/slot 越界/back_slot_count 域外 = AssertionError,
    禁兜底坐标。同名多条:候选按 extras.owned_equips 出现序,每次调用消费
    一个坐标;直调方按单件会话使用(连穿交还框架决策循环,见上方契约 3)。

    :param param: 穿装动作参数(词表 CwActionWearEquipParam;字段语义与
        取值时机见词表类 docstring)。
    :param env: 备战域执行环境(代码内组装传入;可省 = 缺省 None,本 op
        机械半自持后零 env 消费,形参保留 = 注册表构造签名兼容)。
    """

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionWearEquipParam,
                 env: PrepExecEnv | None = None):
        CwOperation.__init__(self, ctx, op_name='CwActionWearEquipOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='wear_equip', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """穿装备单步。

        流程 = 守卫断言三形 → 拖点静态解析(row/slot/back_slot_count,
        零截图)→ 实机机械段(mouse_move 防吞点击 → 拖前固定等待 → 单次
        拖拽 → 拖后固定等待)→ park_cursor → 自上报。机械执行零判效:
        发出即记账,拖后零读屏零落地判定;拖拽静默不生效由下一入口观察
        对账暴露,重派 = 决策循环按新观察自然承接。

        [索引定义] 拖拽坐标 = src_cx/src_cy(参数显式传入,owned 装备
        条目格心 1080p)→ 目标排 avatar 拖点(screen_info 建档派生,
        slot = 排内画面物理槽位 1 基)。
        """
        action: CwActionWearEquipParam = self.param
        # —— 守卫断言三形(参数语义唯一所有者 = op;违法响亮暴露零拖拽,
        # 禁兜底坐标/禁负下标回环静默错点)——
        if action.row not in ('front', 'back'):
            raise AssertionError(
                f'CwActionWearEquipParam row={action.row!r} 非法(front/back)')
        # 后排布局档前缀静态解析(back_slot_count → 布局档键域;键域外 =
        # 无 area 档可解析,禁静默按 6 兜底)。现役 6-9 档全量已建档,
        # 后排 slot 7-9 自本形态起可用(旧守卫表长只匹配基线 6 的潜在
        # bug 随静态解析一并消灭)。
        from sr_od.application.currency_war.obs.cw_back_layout import (
            _layout_prefixes,
        )
        if action.row == 'back' \
                and action.back_slot_count not in _layout_prefixes():
            raise AssertionError(
                f'CwActionWearEquipParam back_slot_count='
                f'{action.back_slot_count} 域外(6-9,布局档键域)')
        prefix = ('前排' if action.row == 'front'
                  else _layout_prefixes()[action.back_slot_count])
        pts = row_drag_points(self.ctx, prefix)
        if not (1 <= action.slot <= len(pts)):
            raise AssertionError(
                f'CwActionWearEquipParam slot={action.slot} '
                f'越界(1-{len(pts)};row={action.row} '
                f'back_slot_count={action.back_slot_count})')
        target = pts[action.slot - 1]
        start = Point(int(action.src_cx), int(action.src_cy))
        if cw_sim_ports.mechanical_io_allowed():
            # 浮层守卫(执行前输入契约拒绝):合成确认浮层/角色详情面板在场
            # 时拖拽被游戏静默吞或退化为点卡开面板(H3 退化链),先拦
            #(动作没发出,受阻码走回执映射)。sim 门内 = sim 零触及。
            overlay_hit = prep_drag_overlay_gate(self)
            if overlay_hit is not None:
                log.info('[cw][wear] 浮层在场(%s)→ 拖拽未发出', overlay_hit)
                return self.round_fail(
                    status=drag_overlay_block_status(overlay_hit))
            # 实机机械段(等待全部固定时长常量,非判效;拖拽参数与等待
            # 逐字沿用既有口径)。
            self.ctx.controller.mouse_move(start)   # 防吞点击(截图前移光标)
            time.sleep(PREP_DRAG_SETTLE_WAIT_S)   # 拖前固定等待(非判效)
            self.ctx.controller.drag_to(start=start, end=target,
                                        hold_time=0.5, duration=1.5)
            time.sleep(1.5)   # MCP drag 异步落地(memory mcp-click-async-sleep-rule)
        else:
            # sim:占位坐标不被机械消费(环境快照通道),机械拖拽静默
            # 跳过(直连旁路 port 检查,sim-design.md §6.5);自上报照走。
            pass
        self.park_cursor(after_wait=0.1)
        # —— 自上报(机械发出后;上报侧坐标反查记账,op 零感知)——
        outcome = None
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            outcome = report_action_wear_equip_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        detail = (f'穿戴 {action.item_name}/{action.char_name}'
                  f' → ({action.row}-{action.slot}) 已发(发出即记账,'
                  '落地归观察对账)')
        if outcome is not None and not outcome.applied:
            # 记账拒单如实进 round detail(直调方经 round 结果感知拒单;
            # 机械成功语义不变——拖拽确实已发生;不分支重试、不读屏验证,
            # 零判效/零重试纪律不受触及)。
            detail += f'；记账拒单:{outcome.reason}(拖拽已发生,账未落)'
        log.info(f'[cw][wear] {detail}')
        return self.round_success(detail)
