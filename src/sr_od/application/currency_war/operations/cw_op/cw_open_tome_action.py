"""开秘密典籍动作 op(CwActionOpenTomeOp)——参数面迁移形态:op 机械面
全自持(守卫上界 op 内现读 ``row_area_centers(ctx,'备战栏')`` 静态档,
点击点 = ``area_center`` 按名直查建档坐标;机械执行路径零 game state
依赖零 executor 点表窥探),单击族形态(mouse_move 防吞点击 + click,
与 OpenBox/Bookcard/CollectOre 同族口径,零拖拽原语消费)。机械执行后
**op 内直调自己的上报函数** ``report_action_open_tome_param``,
零分派,op-layer.md §1.2 动作 op 契约。

参数面(slot 必填,None 语义已废除——参数面迁移批申报,词表类 docstring
为单一源):slot = 备战栏物理槽 1 基;MCP ``run_operation`` 直调传
``{"slot": N}``,N = 当帧 extras ``bench.slots`` 中 kind='tome' 槽的
下标 + 1(与发出点 entry._consumable_open_action 同源口径);env 缺省
None = 缺省备战画面档(tome 单域备战动作,op 体零 env 消费)。缺
slot 键 = from_dict 构造面 TypeError;显式传 null = op 守卫
AssertionError(文案指向参数契约)。

[记账路径总契约第七适用者](契约正文 = flow/action-op.md L32「记账路径
总契约」条款):记账键 = 槽位下标,腾位 = 直址写(kind 'tome' →
empty)零身份反查退化形态。记账拒单帧(``tome_slot_missing`` =
目标槽非 tome kind,决策陈旧帧/直调错传可达)如实进 round
detail——拒单 = 腾位账未落但点击已发生,**禁补点**(补点会重复开典籍),
处置 = 交还决策循环重读板面按新状态重派。

零转移声明:本动作 = 非转移动作(action-op.md 转移动作终表无 OpenTome
行),上报零 ``WorldDecl`` 构造、round 结果零 data(无声明喂入行)——
星徽四选一画面的出现事实由上报内 star_tome 登记承载,与纯转移声明的
OpenBookcard 不同构,两边各自正确。

非终结:单击开典籍后星徽四选一 overlay 弹出,交接走 director 环
overlay-pending 通用路径交回外循环,选卡由外循环按画面分发
CwScreenBookcard 接管(overlay 检出走环中止交外环 handler,非本动作
终结语义)。单击化 = 用户确认 2026-09-25 游戏实际 =
点典籍槽一次即弹(原双击序列的第二击落在已弹出的弹窗上有误触风险)。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.open_tome import (
    report_action_open_tome_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    area_center,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionOpenTomeParam
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.prep_actions import row_area_centers
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionOpenTomeOp(CwOperation):
    """开秘密典籍:slot 必填/越界双形守卫 → 点槽中心(建档坐标)→ 固定动画等待。
    起点:货币战争-备战画面(动作执行时);终点:单击秘密典籍槽开启;动作已发出并上报逻辑态,停留原画面(判效归下一帧观察)。
    非终结(星徽四选一弹窗经 director 环 overlay-pending 通用路径交回
    外循环分发 CwScreenBookcard 选卡,非终结口驱动)。

    单击化(用户确认 游戏实际 = 单击
    即弹;原双击序列的第二击落在已弹出的弹窗上有误触风险):
    实机核凭据 = 待实机局 journal(代码批先落地,实机验证随迭代收尾,
    )。

    :param param: 开秘密典籍动作参数(slot 必填,字段语义与取值时机见词表
        类 docstring;直调传参 = 当帧 extras ``bench.slots`` 中
        kind='tome' 槽的下标 + 1)。
    :param env: 执行环境(代码内组装传入;可省 = 缺省 None,按缺省备战
        画面档解析坐标——单件会话直调场景 op 跑在备战画面语义正确)。
    """

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionOpenTomeParam,
                 env: PrepExecEnv | None = None):
        CwOperation.__init__(self, ctx, op_name='CwActionOpenTomeOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='open_tome', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """开秘密典籍:slot 必填/越界双形守卫 → 点槽中心 → 固定动画等待。

        守卫两形(校验落点契约 = flow/action-op.md L55;缺席与越界同款
        守卫,gate 外 = sim/实机两执行面同守):slot=None 显式拒绝(废除
        语义申报,文案自教新契约)与越界(下界 1 显式闭合禁负下标回环;
        空点表 = 建档漂移哨同断言)。点击点 = ``area_center`` 按名直查
        (有意不并入点表下标直取:点表下标在 area 族缺档时静默错位,按名
        直查缺档自然异常更防建档漂移误点;守卫读表长、点击读单名,两读
        并存 = 有意形态)。单击开启即弹(等待归产生动画的操作);弹窗后
        外循环分发 CwScreenBookcard 接管选卡(本动作不选——选卡是策略
        决策,板上阵营匹配在 CwScreenBookcard),弹窗就位与否交下一帧
        观察(外循环分发重判)。
        """
        action: CwActionOpenTomeParam = self.param
        if action.slot is None:
            raise AssertionError(
                'CwActionOpenTomeParam slot 必填(备战栏物理槽 1-9 基 1;'
                '直调按当帧 extras bench.slots kind=tome 槽下标+1 传;'
                'slot=None 现算语义已随参数面迁移批废除,现算归发出点 '
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
                f'CwActionOpenTomeParam slot={slot} 越界'
                f'(1-{len(pts)};画面档={SCREEN_NAME})')
        # 建档坐标直查(点击点 = 槽位本体中心,screen_info 单一真相源,
        # 禁 fallback 推算——area 缺失 = 取值直接使用,点击消费点自然
        # 异常,零防御口径)。
        center = area_center(self.ctx, f'备战栏-{slot}')
        if cw_sim_ports.mechanical_io_allowed():
            # 实机机械段(点击 + 固定动画等待同 gate:sim 局零白睡;等待
            # 归产生动画的操作,固定等待族 = flow/action-op.md §3;判效
            # 交下一帧观察)。
            self.ctx.controller.mouse_move(center)   # 防吞点击(同开箱/采晶矿口径)
            self.ctx.controller.click(center)        # 单击:开启即弹
            from sr_od.application.currency_war.prep_actions import (
                _OVERLAY_ANIM_WAIT_S,
            )
            time.sleep(_OVERLAY_ANIM_WAIT_S)
        # else sim:机械执行分支静默成功(直连旁路 port 检查,sim-design.md §6.5)
        detail = f'开典籍槽{slot} ✓(发出即记账,落地归观察对账)'
        # —— 自上报(机械发出后;op-layer.md §1.2 动作 op 契约):开典籍
        # 腾位 + star_tome 登记。零声明喂入行(非转移动作,round 结果零
        # data);gs 缺席 = 无处记账跳过(零上报零异常,既有行为保留)。
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            outcome = report_action_open_tome_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
            if not outcome.applied:
                # 记账拒单如实进 round detail(直调方经 round 结果感知
                # 拒单;机械成功语义不变——点击确实已发生;禁补点:拒单 =
                # 腾位账未落,补点会重复开典籍,处置 = 重读板面按新状态
                # 重派)。
                detail += f'；记账拒单:{outcome.reason}(点击已发生,账未落)'
        log.info(f'[cw][tome] {detail}')
        return self.round_success(detail)
