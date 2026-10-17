"""买经验动作 op(CwActionLevelUpOp)——动作 op 重组换壳(原
``PrepLevelUpOp``,ActionOp ABC → 框架 SrOperation;机械执行后 **op 内
直调自己的上报函数** ``report_action_level_up_param``,零分派,op-layer.md
§1.2 动作 op 契约)。

**整批连点形态**(迭代-prep-shop-workflow-redesign;
line_and_upgrade §2.2「一次买齐」):动作参数携带授权批击数
(``CwActionLevelUpParam.clicks``),本 op 单次执行内连点该击数——
决策帧零介入 = 授权后不再逐帧重闸,「买一半」缺陷(逐帧单击 × 静态
阈值逐帧重闸,血支付中血量跌回阈值之下即停止发出)的机制级修复。
缺省 clicks=1 兼容历史单击调用面。非终结。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.level_up import (
    report_action_level_up_param,
)
from sr_od.application.currency_war.kernel.cw_economy import (
    XP_CLICK_COST_FALLBACK,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    ShopActionExecuted,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    area_center,
)
from sr_od.application.currency_war.kernel.cw_vocab import CwActionLevelUpParam
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
        ShopExecEnv,
    )
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionLevelUpOp(CwOperation):
    """买经验(整批连点形态:找钮 → 连点授权击数 → 等待;授权批击数
    由决策侧预授权携带,执行零重闸)。非终结。

    双域执行(商店执行链端口接线):备战域经 ``PrepExecEnv.executor``
    (PrepActionExecutor)、商店域经 ``ShopExecEnv.executor``
    (ShopActionExecutor);按钮坐标在商店域优先取 env 已锚定的
    ``level_btn``(商店画面 op 观察 node 的 area 锚定产物),回落自读
    备战画面档 area;坐标取值直接使用,缺失零检查 = 使用点自然异常
    报错(禁兜底坐标)。
    """

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionLevelUpParam,
                 env: PrepExecEnv | ShopExecEnv):
        CwOperation.__init__(self, ctx, op_name='CwActionLevelUpOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='level_up', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """买经验整批(line_and_upgrade §2.2 一次买齐:授权批击数在
        决策侧预授权帧算定,执行帧不再重闸——实付上界 = 授权值)。

        执行 = 单次 op 内连点 ``clicks`` 击(决策循环零介入,防「逐帧
        单击 × 静态阈值逐帧重闸」的部分级复发);击数缺省 1 = 历史单击
        调用面兼容。经验/等级/金真值 = 上报函数单点直写(击数 =
        ``executed.levelup_clicks`` 喂实际连点数;金腿 = ``action.cost``
        ×clicks 直写,cost = 动作发出面 xp_click_cost 现算装载)+ 下一帧
        观察对账族双通道。单击价本处现算仅作 detail 暴露。
        """
        action: CwActionLevelUpParam = self.param
        env = self.env
        ex = env.executor
        match = ex._ctx.cw_match
        session = match.session if match is not None else None
        from sr_od.application.currency_war.kernel.cw_economy import (
            xp_click_cost,
        )
        btn = getattr(env, 'level_btn', None)
        if btn is None:
            # 商店域 env 已带观察 node 锚定的 level_btn;无锚定(备战域
            # env / 商店域锚定缺席)→ 自读 area(area 自读回落 = 业务
            # 定位逻辑,保留)。取值直接使用:按钮坐标缺失零检查,使用点
            # 自然异常报错(禁兜底坐标静默点击)。
            btn = area_center(
                ex._ctx, '备战标识-购买经验',
                screen_name=str(getattr(ex, 'screen_name', SCREEN_NAME)))
        clicks = max(1, int(getattr(action, 'clicks', 1) or 1))
        # 单击价容器读口(kernel 单一源,失读回退兜底价;与假环境执行缝同式)
        _price = XP_CLICK_COST_FALLBACK
        if session is not None:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                game_state_of,
            )
            _price = xp_click_cost(game_state_of(session))
        if cw_sim_ports.mechanical_io_allowed():
            ex._ctx.controller.mouse_move(btn)   # 防吞点击(review M-5)
            for _ in range(clicks):
                ex._ctx.controller.click(btn)
        # else sim:机械腿静默成功(直连旁路 port 检查,flow-seam §2)
        # 商店访问账(shop 域 visit 汇总口径;备战 env 无 ledger 字段 =
        # 备战域无访问账概念,跳过——发出即记账,与买/刷 op 同位)。
        _led = getattr(env, 'ledger', None)
        if _led is not None:
            _led.total_xp_buy += clicks
        # 光标 parking(审计 P0 = M38 level 毒化注入点):按钮距等级显示区 18px,
        # 点击后光标压住 Lv.N 区 → 下帧 OCR 读错(4 毒化 3 位面的链头)。park 后再继续。
        ex._op.park_cursor(before_wait=0.3, after_wait=0.15)
        #  挂点A(升级事件;发出即登记,观测 best-effort,零决策语义)。
        try:
            if session is not None:
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    game_state_of,
                )
                game_state_of(session).effects.on_level_up()
        except Exception as e:   # noqa: BLE001  观测失败不阻塞对局
            log.warning('[cw][levelup] effect inventory 挂点失败(不阻塞): %s', e)
        # —— 自上报(机械发出后;op-layer.md §1.2):击数 = 本批实际连点数 ——
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            report_action_level_up_param(
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'),
                executed=ShopActionExecuted(levelup_clicks=clicks))
        detail = (f'买经验整批 {clicks} 击花金{_price * clicks}'
                  f'(单价{_price};级真值=下一帧观察 reconcile)')
        log.info(f'[cw][levelup] {detail}')
        return self.round_success(detail)
