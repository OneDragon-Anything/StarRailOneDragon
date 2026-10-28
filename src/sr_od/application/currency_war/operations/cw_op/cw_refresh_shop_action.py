"""刷新商店动作 op(CwActionRefreshShopOp)——动作 op 重组换壳
(ActionOp ABC → 框架 SrOperation;op-layer.md §1.2 动作 op 契约)。一 op 一文件。

**终结跳写申报**:金账扣费 = 上报函数容器直读当次刷价(费用单一源 =
``gs.shop_refresh_cost`` 容器;2026-10-16 用户裁决:刷新与买牌/升级/
卖牌同款,上报即按当次价扣金,双端逻辑态——推翻 2026-09-21「金仍不写」
旧裁定;环境刷新触发器的发放金 = 环境通道,见 kernel/cw_env_grants);
刷后牌面 = ``write_logic_rand`` 随机态
(用户裁定,以实际观察为准;真值 = 下一入口观察)。**刷新计数由本
op 自上报统一触发**(``report_action_refresh_shop_param``:付费/全量
计数经 ``gs.effects.record_refresh`` 单口;免费分支 = 容器字段
``gs.free_refresh_left`` Field 值判定与扣减,未观察保守按付费——次数
是记账面非决策闸,判定职能收尾观察边界,本 op 零读屏)。sim 与生产
同一段 op 代码同口自上报同一上报函数(驱动器不执行刷新——终结动作
截停序列后由消费侧 op 执行,刷新事实唯一生产点 = 本 op 的自上报)。
"""
from __future__ import annotations

import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_economy import REFRESH_COST_BASE
from sr_od.application.currency_war.kernel.cw_vocab import CwActionRefreshShopParam
from sr_od.application.currency_war.operations.cw_op.cw_shop_action_ops import (
    ShopExecEnv,
)
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

# 刷新点击后固定等待(重掷动画收敛):固定时长即收的时长常量,与买牌
# 点击后固定 sleep 同风格。等待不是判效——牌面/金真值判读不在动作内
# 自证,交下一入口观察对账。
REFRESH_CLICK_SETTLE_WAIT_S: float = 1.0


class CwActionRefreshShopOp(CwOperation):
    """刷新 = 终结 op(唯一引入新事实的动作,期望态必须在新事实处重建
    ——终结后返回主循环,下一段入口重观察)。

    体内零读屏零比对零验证(action_ops §1 动作 op 无论执行前后
    不做观察识别,点击链之外零截图零识别):免费刷新判定 = 容器 Field
    值(上报函数承载,见模块头);「刷新是否生效」的判效权归下一入口
    观察对账。计数自上报 = 效果账本统一触发(见模块头);金账扣费与
    payload 随机态采样均由上报函数承载(金 = 容器直读当次刷价,
    2026-10-16 用户裁决,见模块头)。
    """

    #: 终结动作(执行即本画面访问结束,返回主循环)。
    terminal = True
    #: 结束本次访问等待秒数(无转移动画等待语义)。
    terminal_wait = 0.0

    def __init__(self, ctx: SrContext, param: CwActionRefreshShopParam,
                 env: ShopExecEnv):
        CwOperation.__init__(self, ctx, op_name='CwActionRefreshShopOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='refresh_shop', is_start_node=True)
    def run(self) -> OperationRoundResult:
        env = self.env
        op, _match, ledger, state = (env.op, env.match, env.ledger,
                                     env.state)
        if cw_sim_ports.mechanical_io_allowed():
            op.ctx.controller.click(env.refresh_btn)
        log.info(f'[cw-shop] Refresh click @({env.refresh_btn.x},'
                 f'{env.refresh_btn.y})')
        time.sleep(REFRESH_CLICK_SETTLE_WAIT_S)
        # 当次刷价进花销账(免费帧累加 0——修复免费帧虚记既有缺陷:
        # 免费刷真路径实扣 0,旧形态无条件记容器价;谓词与上报函数同源
        # 同式 = free_refresh_left 值判定,镜像漂移由测试等值断言看住)。
        # 非免费帧容器刷价在场用现值,未观察/0 = 回基价。读数必须走
        # .value 读口——Field 直接进算术 = TypeError(实机 04:37 刷新
        # 首击即崩实证,店 env 容器化后此读点漏迁移)。
        _left = state.free_refresh_left.value
        _free_frame = _left is not None and int(_left) > 0
        _refresh_fee = 0 if _free_frame else (
            state.shop_refresh_cost.value or REFRESH_COST_BASE)
        ledger.spend_executed += _refresh_fee
        ledger.total_refresh += 1
        # 自上报 = 刷新计数统一触发 + Field 免费分支扣减 + payload 随机态
        # 采样(见模块头与上报函数 docstring)。free 传 None = 上报函数
        # Field 值判定;金账不喂(生产观察覆盖)。
        from sr_od.application.currency_war.kernel.cw_action_report.refresh_shop import (
            report_action_refresh_shop_param,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            ChannelSig,
            game_state_from_ctx,
        )
        _gs_rpt = game_state_from_ctx(self.ctx)
        if _gs_rpt is not None:
            report_action_refresh_shop_param(
                _gs_rpt, self.param,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        # 结束本次访问:真值不写(观察覆盖),期望态下段入口重建。
        return self.round_success(
            f'刷新已发(刷价 {_refresh_fee};终结交回,期望态下段入口重建)')
