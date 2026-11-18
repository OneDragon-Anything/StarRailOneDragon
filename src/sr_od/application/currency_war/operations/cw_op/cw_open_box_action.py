"""开简易武装箱动作 op(CwActionOpenBoxOp)——参数面迁移形态:op 机械面
全自持(守卫上界 op 内现读 ``row_area_centers(ctx,'备战栏')`` 静态档,
点击点 = ``area_center`` 按名直查建档坐标;机械执行路径零 game state
依赖零 executor 点表窥探),单击族形态(mouse_move 防吞点击 + click,
与 OpenTome/OpenBookcard/CollectOre 同族口径,零拖拽原语消费)。机械
执行后 **op 内直调自己的上报函数** ``report_action_open_box_param``,
零分派(op-layer.md §1.2 动作 op 契约)。

参数面(slot 必填,None 语义已废除——参数面迁移批申报,词表类 docstring
为单一源):slot = 备战栏物理槽 1 基;MCP ``run_operation`` 直调传
``{"slot": N}``,N 双口径任一:当帧 extras ``bench.slots`` 中
kind='supply_box' 槽的下标 + 1(与发出点 entry._consumable_open_action
同源口径),或当帧 extras ``armory_boxes`` 元素的 ``slot`` 字段直接传
(无需 +1——``_ctx_slots`` 1 基实证,与前一口径同一物理槽位号语义
等价);env 缺省 None = 缺省备战画面档(OpenBox 单域备战动作,op 体零
env 消费)。缺 slot 键 = from_dict 构造面 TypeError;显式传 null = op
守卫 AssertionError(文案指向参数契约)。

[记账路径总契约第八适用者](契约正文 = flow/action-op.md L32「记账路径
总契约」条款):**零写占位形态**——状态容器零写 + box_card 登记 +
``_decl_bottom(gs,'open_box')`` 转移声明,腾位归下一入口 heavy 实读
整表重建。与 OpenTome/OpenBookcard 的「腾位直址写零身份反查」不同构:
本件零键域零反查(上报函数零 param 字段消费、零状态容器写端),总契约
三条(反查时序/陈旧窗口/反查唯一性)在本域整族退化——陈旧窗口由终结
转移结构性消除(上报后 op 立即经终结口交回主循环,武装箱选择模态压住
备战画面期间决策环不再消费 bench 槽位表)。**零拒单出口**(零写族恒
applied=True,无 slot 校验):直调错传 slot 的后果 = 点错槽开启失败,
外循环按实读重派,非静默错账。

终结动作(R7 终结化):点完「开启」本动作即返回主循环,武装箱选择
画面由外循环按 box_card 登记分发独立画面 op 选卡。terminal_wait = 开箱
动画等待,与 runner 包络 ``_OVERLAY_ANIM_WAIT_S`` 等价(等价测试 =
test_action_registry 终结集测试)。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.zero_writes import (
    report_action_open_box_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    area_center,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionOpenBoxParam
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.prep_actions import row_area_centers
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionOpenBoxOp(CwOperation):
    """开简易武装箱:slot 必填/越界双形守卫 → 点「武装箱开启位-N」开启钮
    (建档坐标)→ 固定动画等待。
    起点:货币战争-备战画面(动作执行时);终点:点击开启武装箱;动作已
    发出并上报逻辑态,停留原画面(判效归下一帧观察)。终结动作(动作发出
    点 = 策略器 entry ① prep 实体面卡片分支与第 0 步溢出自救态共用
    ``_consumable_open_action``;武装箱选择画面由外循环按画面分发
    :mod:`cw_screen_box_pick` 选卡,选卡决策单一源 = 策略 ``decide_box_card``
    契约)。

    :param param: 开简易武装箱动作参数(slot 必填,字段语义与取值时机见
        词表类 docstring;直调传参双口径 = 当帧 extras ``bench.slots`` 中
        kind='supply_box' 槽的下标 + 1,或 extras ``armory_boxes`` 元素的
        ``slot`` 字段直接传)。
    :param env: 执行环境(代码内组装传入;可省 = 缺省 None,按缺省备战
        画面档解析坐标——单件会话直调场景 op 跑在备战画面语义正确)。
    """

    #: 终结动作(开箱即引入新事实,返回主循环分发选卡)。
    terminal = True

    #: 返回等待 = 开箱动画等待值(与 prep_actions._OVERLAY_ANIM_WAIT_S
    #: 逐字等价,漂移由等价测试暴露)。
    terminal_wait = 1.8

    def __init__(self, ctx: SrContext, param: CwActionOpenBoxParam,
                 env: PrepExecEnv | None = None):
        CwOperation.__init__(self, ctx, op_name='CwActionOpenBoxOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='open_box', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """开简易武装箱:slot 必填/越界双形守卫 → 点开启钮 → 固定动画等待。

        守卫两形(校验落点契约 = flow/action-op.md L55;缺席与越界同款
        守卫,gate 外 = sim/实机两执行面同守):slot=None 显式拒绝(废除
        语义申报,文案自教新契约含 kind='supply_box' 双口径指引)与越界
        (下界 1 显式闭合禁负下标回环;空点表 = 建档漂移哨同断言)。守卫
        上界取备战栏点表(槽位域),点击点走「武装箱开启位-{slot}」直查
        (有意不并入点表下标直取:点表下标在 area 族缺档时静默错位,按名
        直查缺档自然异常更防建档漂移误点;守卫读表长、点击读单名,两读
        并存 = 有意形态)。点完开启本动作即终结——武装箱选择画面由外循环
        按 box_card 登记分发 ``CwScreenBoxPick`` 选卡(选卡决策不在本执行
        链);弹窗就位与否交下一帧观察。
        """
        action: CwActionOpenBoxParam = self.param
        if action.slot is None:
            raise AssertionError(
                'CwActionOpenBoxParam slot 必填(备战栏物理槽 1-9 基 1;'
                '直调按当帧 extras bench.slots kind=supply_box 槽下标+1 或 '
                'extras.armory_boxes 元素 slot 字段直传;slot=None 现算语义'
                '已随参数面迁移批废除,现算归发出点 '
                'entry._consumable_open_action),零点击')
        slot = int(action.slot)
        # 守卫上界 op 内现读(screen_info 静态档;原 executor 构造期缓存
        # → op 执行期现读同一档案,值逐位同,零 env 消费)。
        pts = row_area_centers(self.ctx, '备战栏')
        if not (1 <= slot <= len(pts)):
            # 参数违法由 op 自判(flow/action-op.md L55 校验落点契约):
            # 越界 = 决策逻辑 bug,守卫断言响亮暴露零点击(禁兜底坐标/禁
            # 负下标回环——下界 1 显式闭合)。
            raise AssertionError(
                f'CwActionOpenBoxParam slot={slot} 越界'
                f'(1-{len(pts)};画面档={SCREEN_NAME})')
        # 建档坐标直查(点击点 = 武装箱开启位-N 开启按钮区,与备战栏-N
        # 槽位本体是两族 area——箱体占槽、开启钮独立布局,area 族不同名
        # 是游戏交互结构的如实镜像;screen_info 单一真相源,禁 fallback
        # 推算——area 缺失 = 取值直接使用,点击消费点自然异常,零防御
        # 口径)。
        open_point = area_center(self.ctx, f'武装箱开启位-{slot}')
        if cw_sim_ports.mechanical_io_allowed():
            # 实机机械段(点击 + 固定动画等待同 gate:sim 局零白睡;等待
            # 归产生动画的操作,固定等待族 = flow/action-op.md §3;判效
            # 交下一帧观察)。
            self.ctx.controller.mouse_move(open_point)   # 防吞点击
            self.ctx.controller.click(open_point)
            from sr_od.application.currency_war.prep_actions import (
                _OVERLAY_ANIM_WAIT_S,
            )
            time.sleep(_OVERLAY_ANIM_WAIT_S)
        # else sim:机械执行分支静默成功(直连旁路 port 检查,sim-design.md §6.5)
        detail = (f'开箱槽{slot} ✓(发出即上报:零写族+登记+声明,'
                  '落地归下一入口heavy实读)')
        # —— 自上报(机械发出后;op-layer.md §1.2 动作 op 契约):零写族
        # ——box_card 登记 + 底层屏声明(trigger='open_box'),状态容器
        # 零写,腾位归下一入口 heavy 实读。上报后一行声明喂入(实机端口
        # 未装 = no-op,sim 装配后驱动后端 open_box 分派);round data 携
        # 声明(journal 记账面)。gs 缺席 = 无处记账跳过(零上报零声明零
        # 异常,既有行为保留)。零拒单段(零写族恒 applied=True,无 slot
        # 校验出口)。
        world_decl = None
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            outcome = report_action_open_box_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
            world_decl = outcome.world_decl
            cw_sim_ports.declare_world(world_decl)
        log.info(f'[cw][box] {detail}')
        return self.round_success(detail, data=world_decl)
