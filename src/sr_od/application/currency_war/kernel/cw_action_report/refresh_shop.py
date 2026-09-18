"""货币战争动作上报:刷新商店(report_action_refresh_shop_param)。

刷新动作上报 = 计数统一触发点(2026-09-18 用户裁决:GameState 刷新
三字段 free_refresh_balance/paid_refresh_count/total_refresh_count 迁入
效果账本 ActiveEffectInventory 统一计算,本函数经
``gs.effects.record_refresh`` 单口触发;生产 = 刷新 op 自上报,sim =
委托串直调,落地门零重复触发)。金账 −实付仅 sim 喂
``executed.refresh_paid`` 时写(生产不喂;刷后牌面 = 续段重观察,
payload 不写——终结跳写申报收窄为「金与 payload 不写,计数照触发」)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    LogicOutcome,
    ShopActionExecuted,
    _validate_sig,
)


def report_action_refresh_shop_param(gs: GameState, param: Any, sig: ChannelSig,
                                     executed: ShopActionExecuted | None = None,
                                     free: bool | None = None) -> LogicOutcome:
    """刷新商店上报 = 计数统一触发(效果账本)+ (sim)金账扣减。

    计数(``gs.effects.record_refresh`` 单口,行为口径见其 docstring):
    - refresh_total 恒 +1;free=True 扣免费余额(下限 0)/free=False
      refresh_paid +1;同帧 bump 按策略触发计数(CounterKey.REFRESH,
      采购专员族门槛面)。
    - free 判定输入 = 显式 ``free`` 优先(生产 op 喂刷前按钮态 UI 真值,
      T-13 真值通道),None 回退账本余额 > 0(余额未建模局恒 paid 的
      保守形态,与迁移前逐位一致)。

    金账:仅 ``executed.refresh_paid`` 在场时写(−实付;免费帧 0 不写)
    ——生产 op 不喂,sim 引擎显式喂(免费刷额度先行 ``refresh_cost_for``;
    实付金含免费刷注入等引擎差异,不可自算)。``applied`` 恒 True:
    计数即职责完成,调用方仅在动作实际发出后进本口(未落地不计数)。
    """
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    inv = gs.effects
    free_determined = bool(free) if free is not None \
        else (inv.free_refresh_balance > 0)
    inv.record_refresh(free=free_determined)

    paid = executed.refresh_paid if executed is not None else None
    if paid is not None:
        paid = max(0, int(paid))
        if paid > 0:
            g = gs.gold.value
            if g is not None:
                gs.write_logic(gs.gold, int(g) - paid,
                               produced_by='CwActionRefreshShopParam',
                               evidence='proj_refresh_gold', sig=_grp_sig)
    return LogicOutcome(applied=True)
