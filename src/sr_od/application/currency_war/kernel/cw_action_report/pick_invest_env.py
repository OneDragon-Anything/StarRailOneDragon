"""货币战争动作上报:投资环境选择(report_action_pick_invest_env_param)。

即时上报形态(action_ops.md §1 用户裁定增补 2):动作 op 机械链发出后
调用本函数,一次调用 = 完整结果写入——整支走获得链 ``gain_invest_env``
(active_env 注册 + portal 登记 + ``on_env_gained`` 环境赠卡效果枚举,
正本 = game_state/gain-chain.md)。

自 ``pick_invest.py`` 拆分(投资两屏迁移批;portal 支先于此批已走获得链,
本拆分仅按屏别独立成文件并废除分步形参)。
"""
from __future__ import annotations

from typing import Any

from sr_od.application.currency_war.kernel.cw_gain_chain import (
    gain_invest_env,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    LogicOutcome,
    _validate_sig,
)


def _canon_invest_name(name: str) -> str:
    """归一卡名(全角冒号→半角 OCR 形变 + 注册表归一;链内再 normalize
    幂等)。"""
    from sr_od.application.currency_war.kernel.cw_investments import (
        normalize_invest_name,
    )
    return normalize_invest_name((name or '').replace('：', ':'))


def report_action_pick_invest_env_param(
        gs: GameState, param: Any, sig: ChannelSig, *,
        session: object | None = None) -> LogicOutcome:
    """投资环境选择上报(即时形态):按成功应用完整结果。

    - ``param.norm_name`` = 选中环境归一规范名;归一后空 = 零写 noop
      (选择事实缺名禁写,旧 portal 支防御逐位平移);
    - ``session`` = 策略会话(portal 登记腿消费;``None`` = 登记腿跳过
      [局外/测试形态],容器写照常);
    - 出参 applied=True = 受理;reason = ``gain_chain_applied``。
    """
    _validate_sig(sig, ('logic_action',))
    canon = _canon_invest_name(str(getattr(param, 'norm_name', '') or ''))
    if not canon:
        return LogicOutcome(applied=True, reason='landing_noop')
    gain_invest_env(gs, session, canon, rand=False, sig=sig)
    return LogicOutcome(applied=True, reason='gain_chain_applied')
