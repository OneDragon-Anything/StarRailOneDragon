"""出战动作 op(CwActionStartBattleOp)——出战域重设计:出战
op 只管「点击出战和弹窗」,零策略语义、零转移验证——流程卡死监控归外部
哨兵(runtime-ops 哨兵栈现役),op 内不建。

动作 op 重组 换壳(原 ``StartBattleOp``,ActionOp ABC → 框架
SrOperation;机械执行后 **op 内直调自己的上报函数**
``report_action_start_battle_param``,跳过子态事实随上报携带——免战牌
递减语义 = 上报时,op-layer.md §1.2 动作 op 契约)。执行序(单一语义;备战环 /
达标分支动作发出核 ``launch_prepared_battle`` / 恢复局锁定直出战三路径经同一
注册表分派到达本 op,禁各写一套点击段):
  1. 找按钮「按钮-出战」(备战 + 开商店两屏查;叠加帧现状逻辑)——
     免战子态 fallback 查「按钮-跳过」(同语义点它);
  2. mouse_move + click(基本单击);
  3. sleep 1.0(弹窗渲染窗);
  4. 截图一次:「货币战争-未达上限警告」→ 点「勾选-本局不再提示」
     (幂等,已勾无害)→ 点「按钮-确认」;「货币战争-提示-前台无角色」
     → 点「按钮-确认」;都没有 → 完成。点出战后的真弹窗全清单已排查,
     仅此两类(免战牌「跳过(N/N)」是按钮换形态非弹窗,属步 1);
  5. 完成 = 自上报(跳过子态事实)→ 返回主循环(备战画面 op 正常终结,
     terminal/terminal_wait 语义不变)。

**round 结果契约**(原基类已登记例外并入):``execute()`` 的成功态 =
**点击序列已执行**(找不到按钮 = round_fail 未发出;按钮/弹窗确认
area 缺失零检查 = 取值直接使用自然异常报错,QA 终裁),消费面
= runner 包络 ``last_launch_ok`` 旁路(round 结果映射,已登记例外 =
action_ops.md §2.3)。
旧发出家族(6×0.5s 转移轮询 / 备战标识消失验证 / POST_LAUNCH_BLOCKERS
拦截弹窗守卫 / 重发长按下 / 失焦守卫 / launch_dead 连败停机)随出战域
重设计整删:op 不判效,返回主循环后画面状态由外循环下一帧重判。
"""
from __future__ import annotations

import time
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
    """出战点击(点击出战/跳过 → 弹窗确认 → 自上报返回主循环;语义见模块头)。

    终结动作:发出即本备战访问终结(返回主循环战斗分支);终结等待 =
    ``terminal_wait``(消费点经注册表读类属性)。
    """

    #: 终结动作(发出即本备战访问终结)。
    terminal = True

    #: 终结返回等待秒数(备战画面 op 返回节奏,现状等价测试 =
    #: test_action_registry 终结集测试)。
    terminal_wait = 3

    #: 出战点击后的弹窗渲染等待(步 3)。单帧截图判定,不轮询(op 零判效):
    #: 弹窗未就位的帧由外循环下一帧画面分支接住(画面档现役)。
    POST_CLICK_WAIT_S: float = 1.0

    def __init__(self, ctx: SrContext, param: object,
                 env: PrepExecEnv):
        CwOperation.__init__(self, ctx, op_name='CwActionStartBattleOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='start_battle', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """出战点击序列(成功态契约 = 点击序列已执行,见模块头)。

        免战子态(2026-08-17 M72 已实测确认建档):「免战牌」策略激活时出战按钮变
        「跳过(N/N)」(直跳战斗,免战 2 次)——查不到「出战」时查子态
        「按钮-跳过」,同语义点它(推进节点)。跳过子态事实随自上报携带
        (免战次数递减语义 = 上报时,非「验证落地后」——op 已零验证)。

        ⚠️ 正交态查找(子态建模四问③,skill feedback 案例库):免战与
        「商店开」**可叠加**(跳过按钮 + 牌区展开同帧)——叠加帧识别为
        货币战争-备战-开商店(它盖基态 id_mark),按单一屏查「按钮-跳过」
        会落空。跳过/出战按钮在两屏同一位置 → 查找不锁死单一屏(备战 +
        开商店都查);按钮 area 单源归备战屏,不复制双源。

        找不到按钮 = 动作未执行(round_fail「未执行:找不到按钮」)→ 返回主循环
        重新判定(不炸;画面真未知由未知兜底链接)。
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
        # else sim:机械腿静默成功(直连旁路 port 检查,flow-seam §2)
        time.sleep(self.POST_CLICK_WAIT_S)
        detail = self._settle_post_click_popup(ex)
        # —— 自上报(机械发出后;跳过子态事实携带,免战递减 = 上报时)——
        # 上报后一行声明喂入(动作后果声明化喂入契约 = design.md §2.2
        # 契约 3;实机端口未装 = no-op,sim 装配后驱动后端 battle_resolve)。
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
        log.info('[cw][battle] %s%s → 交回外循环', detail,
                 '(跳过子态)' if skip_substate else '')
        return self.round_success(detail, data=world_decl)

    def _settle_post_click_popup(self, ex) -> str:
        """出战点击后的弹窗收尾(步 4,单帧截图判定):两类真弹窗点确认,
        都没有 = 完成。返回机械摘要(detail)。

        弹窗检查业务逻辑保留(有弹窗就确认);弹窗内确认 area 取值直接
        使用,缺失零检查 = 确认点击使用点自然异常报错(QA 终裁:建档
        缺失零防御,禁兜底坐标)。

        勾选幂等依据 = M16 死循环根因修复同款行为:只点确认
        不勾「本局不再提示」→ 人口不足时每次出战都弹此窗;对齐
        CwScreenDeployNotFull 完整行为(勾选 → 确认)。
        """
        scr = ex._op.screenshot()
        if ex._op.round_by_find_area(scr, '货币战争-未达上限警告',
                                     '标识-未达上限警告').is_success:
            check = area_center(ex._ctx, '勾选-本局不再提示',
                                '货币战争-未达上限警告')
            ex._ctx.controller.mouse_move(check)
            ex._ctx.controller.click(check)
            time.sleep(0.3)
            confirm = area_center(ex._ctx, '按钮-确认', '货币战争-未达上限警告')
            ex._ctx.controller.mouse_move(confirm)
            ex._ctx.controller.click(confirm)
            return '出战已点击(未达上限警告:勾选+确认)'
        if ex._op.round_by_find_area(scr, '货币战争-提示-前台无角色',
                                     '标识-无角色提示').is_success:
            confirm = area_center(ex._ctx, '按钮-确认',
                                  '货币战争-提示-前台无角色')
            ex._ctx.controller.mouse_move(confirm)
            ex._ctx.controller.click(confirm)
            return '出战已点击(前台无角色提示:确认)'
        return '出战已点击(无弹窗)'
