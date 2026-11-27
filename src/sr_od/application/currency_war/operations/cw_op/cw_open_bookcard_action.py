"""开书册卡动作 op(CwActionOpenBookcardOp)——参数面迁移形态:op 机械面
全自持(守卫上界 op 内现读 ``row_area_centers(ctx,'备战栏')`` 静态档,
点击点 = ``area_center`` 按名直查建档坐标;机械执行路径零 game state
依赖零 executor 点表窥探),单击族形态(mouse_move 防吞点击 + click,
与 OpenBox/OpenTome/CollectOre 同族口径,零拖拽原语消费)。机械执行后
**op 内直调自己的上报函数** ``report_action_open_bookcard_param``,
零分派(op-layer.md §1.2 动作 op 契约)。

参数面(slot 必填,None 语义已废除——参数面迁移批申报,词表类 docstring
为单一源):slot = 备战栏物理槽 1 基;MCP ``run_operation`` 直调传
``{"slot": N}``,N = 当帧 extras ``bench.slots`` 中 kind='bookcard' 槽的
下标 + 1(与发出点 entry._consumable_open_action 同源口径);env 缺省
None = 缺省备战画面档(bookcard 单域备战动作,op 体零 env 消费)。缺
slot 键 = from_dict 构造面 TypeError;显式传 null = op 守卫
AssertionError(文案指向参数契约)。

[记账路径总契约第六适用者](契约正文 = flow/action-op.md L32「记账路径
总契约」条款):记账键 = 槽位下标,腾位 = 直址写(kind 'bookcard' →
empty)零身份反查退化形态。记账拒单帧(``bookcard_slot_missing`` =
目标槽非 bookcard kind,决策陈旧帧/直调错传可达)如实进 round
detail——拒单 = 腾位账未落但点击已发生,**禁补点**(补点会重复开卡),
处置 = 交还决策循环重读板面按新状态重派。

终结动作(开卡时机归策略器,动作发出点 = entry ① prep 实体面卡片分支,
screens/README §5.5):点完开启即引入新事实(专家邀请函弹窗在场)→
本动作终结返回主循环,弹窗由外循环按画面分发 ``CwScreenExpertInvite``
选卡(分发判定单一源 = skills/sr-od-dev-currency-war/references/flow/loop.md §2 阶段一身份分发)。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.open_bookcard import (
    report_action_open_bookcard_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    area_center,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionOpenBookcardParam
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.prep_actions import row_area_centers
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionOpenBookcardOp(CwOperation):
    """开书册卡:slot 必填/越界双形守卫 → 点槽中心(建档坐标)→ 固定动画等待
    起点:货币战争-备战画面(动作执行时);终点:点击书册卡槽开启;动作已发出并上报逻辑态,停留原画面(判效归下一帧观察)。
    (纯机械执行)。终结动作(动作发出点 = 策略器 entry ① prep 实体面卡片
    分支,screens/README §5.5;弹专家邀请函 = 新事实 → 结束本次访问,与
    OpenBox 终结化同构,规范基准 = op-layer.md §1.4)。

    :param param: 开书册卡动作参数(slot 必填,字段语义与取值时机见词表
        类 docstring;直调传参 = 当帧 extras ``bench.slots`` 中
        kind='bookcard' 槽的下标 + 1)。
    :param env: 执行环境(代码内组装传入;可省 = 缺省 None,按缺省备战
        画面档解析坐标——单件会话直调场景 op 跑在备战画面语义正确)。
    """

    #: 终结动作(专家邀请函弹窗在场 = 新事实,返回主循环重新分发选卡)。
    terminal = True

    #: 结束本次访问等待 = 开卡动画等待值(与 prep_actions._OVERLAY_ANIM_WAIT_S
    #: 逐字等价,漂移由等价测试暴露)。
    terminal_wait = 1.8

    def __init__(self, ctx: SrContext, param: CwActionOpenBookcardParam,
                 env: PrepExecEnv | None = None):
        CwOperation.__init__(self, ctx, op_name='CwActionOpenBookcardOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='open_bookcard', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """开书册卡:slot 必填/越界双形守卫 → 点槽中心 → 固定动画等待。

        守卫两形(校验落点契约 = flow/action-op.md L55;缺席与越界同款
        守卫,gate 外 = sim/实机两执行面同守):slot=None 显式拒绝(废除
        语义申报,文案自教新契约)与越界(下界 1 显式闭合禁负下标回环;
        空点表 = 建档漂移哨同断言)。点击点 = ``area_center`` 按名直查
        (有意不并入点表下标直取:点表下标在 area 族缺档时静默错位,按名
        直查缺档自然异常更防建档漂移误点;守卫读表长、点击读单名,两读
        并存 = 有意形态)。点完开启本动作即结束本次访问——专家邀请函弹窗
        由外循环按画面分发 ``CwScreenExpertInvite`` 选卡(选卡决策不在本
        执行链);弹窗就位与否交下一帧观察。
        """
        action: CwActionOpenBookcardParam = self.param
        if action.slot is None:
            raise AssertionError(
                'CwActionOpenBookcardParam slot 必填(备战栏物理槽 1-9 基 1;'
                '直调按当帧 extras bench.slots kind=bookcard 槽下标+1 传;'
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
                f'CwActionOpenBookcardParam slot={slot} 越界'
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
            self.ctx.controller.click(center)
            from sr_od.application.currency_war.prep_actions import (
                _OVERLAY_ANIM_WAIT_S,
            )
            time.sleep(_OVERLAY_ANIM_WAIT_S)
        # else sim:机械执行分支静默成功(直连旁路 port 检查,sim-design.md §6.5)
        detail = f'开书册卡槽{slot} ✓(发出即记账,落地归观察对账)'
        # —— 自上报(机械发出后;op-layer.md §1.2 动作 op 契约):开卡腾位 ——
        # 上报后一行声明喂入(动作后果声明化喂入契约;实机端口未装 = no-op,
        # sim 装配后驱动后端纯转移分支呈现专家邀请函);round data 携带声明
        # (journal 记账面)。gs 缺席 = 无处记账跳过(零上报零声明零异常,
        # 既有行为保留)。
        world_decl = None
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            outcome = report_action_open_bookcard_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
            world_decl = outcome.world_decl
            cw_sim_ports.declare_world(world_decl)
            if not outcome.applied:
                # 记账拒单如实进 round detail(直调方经 round 结果感知拒单;
                # 机械成功语义不变——点击确实已发生;禁补点:拒单 = 腾位账
                # 未落,补点会重复开卡,处置 = 重读板面按新状态重派)。
                detail += f'；记账拒单:{outcome.reason}(点击已发生,账未落)'
        log.info(f'[cw][bookcard] {detail}')
        return self.round_success(detail, data=world_decl)
