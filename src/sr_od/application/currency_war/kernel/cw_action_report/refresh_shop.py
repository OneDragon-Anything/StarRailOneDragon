"""货币战争动作上报:刷新商店(report_action_refresh_shop_param)
+ 刷新执行计数组(record_refresh_execution,§3.3.6-§3.3.8;
计数组语义同主,与刷新上报同文件单源)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。
语义正本 = 函数 docstring(自 cw_game_state 逐字迁移)。
"""

from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    Field,
    GameState,
    LogicOutcome,
    ShopActionExecuted,
    _validate_sig,
)


def report_action_refresh_shop_param(gs: GameState, param: Any, sig: ChannelSig,
                                     executed: ShopActionExecuted | None = None) -> LogicOutcome:
    """刷新商店上报:gold −刷新费(免费帧 paid=0 −0/不写);刷后牌面 =
    续段重观察(payload 不写)。executed 缺 refresh_paid = applied=False
    跳写(实付金含免费刷注入等引擎差异,不可自算——sim 引擎显式喂)。"""
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    def _w(target: Field, value: Any, evidence: str) -> None:
        gs.write_logic(target, value, produced_by='CwActionRefreshShopParam',
                       evidence=evidence, sig=_grp_sig)

    paid = executed.refresh_paid if executed is not None else None
    if paid is None:
        return LogicOutcome(applied=False, reason='refresh_paid_not_fed')
    paid = max(0, int(paid))
    if paid > 0:
        g = gs.gold.value
        if g is not None:
            _w(gs.gold, int(g) - paid, 'proj_refresh_gold')
    return LogicOutcome(applied=True)


def record_refresh_execution(gs: GameState, free: bool,
                             frame: str = '') -> None:
    """CwActionRefreshShopParam op 执行回执 → 刷新计数组逻辑写入(§3.3.6-§3.3.8,
    写入=仅逻辑;接线点 = cw_op_buy_cards 执行落地门,迁移批次二)。

    行为口径(§4 CwActionRefreshShopParam 行为申报配套):
    - total_refresh_count 恒 +1(§3.3.8:付费+免费全量);
    - free=True(免费帧):**不写** paid_refresh_count(§3.3.7 该键=付费
      累计,长线利好触发载体,免费帧混入即计数毒化)并消耗免费余额
      (§3.3.6 余额 −1,下限 0);
    - free=False:paid_refresh_count +1;
    - 计数从未写过(值 None)按 0 基线起算——计数器是局内单调累计,
      0 基线是构造事实非观察兜底(与「禁兜底改值」的观察域无关)。

    免费判定输入 = 调用方(执行侧按免费余额/效果账本判定后传入;
    余额未建模局恒 paid = 现状保守形态,行为与接线前逐位一致)。
    frame = 轮键留证(写入 evidence)。
    """
    _ev = f'refresh_exec@{frame}' if frame else 'refresh_exec'
    # 渠道②签名(§3.2.1:actor = 执行动作的 op 类名;组 id = 同一次刷新
    # 执行的三笔计数写共享 act 组;R5 W1 起签名必填,ADR-0634)。
    _sig = ChannelSig(family='logic_action', actor='CwScreenBuyCards',
                      mode='compute',
                      group_id=f'act:CwScreenBuyCards@{gs.write_seq + 1}')
    total = gs.total_refresh_count.value or 0
    gs.write_logic(gs.total_refresh_count, int(total) + 1,
                   produced_by='CwActionRefreshShopParam', evidence=_ev, sig=_sig)
    if free:
        balance = gs.free_refresh_balance.value or 0
        gs.write_logic(gs.free_refresh_balance, max(int(balance) - 1, 0),
                       produced_by='CwActionRefreshShopParam', evidence=_ev, sig=_sig)
    else:
        paid = gs.paid_refresh_count.value or 0
        gs.write_logic(gs.paid_refresh_count, int(paid) + 1,
                       produced_by='CwActionRefreshShopParam', evidence=_ev, sig=_sig)

