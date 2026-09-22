"""货币战争动作上报:投资环境选择(report_action_pick_invest_env_param)。

即时上报形态(action_ops.md §1 用户裁定增补 2):动作 op 机械链发出后
调用本函数,一次调用 = 完整结果写入——整支走获得链 ``gain_invest_env``
(active_env 注册 + portal 登记 + ``on_env_gained`` 环境赠卡效果枚举,
正本 = game_state/gain-chain.md)。

本包 → 容器单向依赖:名字标准化契约 = 观察层(op-layer.md §1.1「观察
标准化门」),容器 ``invest_env_opts`` 值域 = 标准注册名,本包零名字
转换、按选择序号取标准名直传链。
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


def report_action_pick_invest_env_param(
        gs: GameState, param: Any, sig: ChannelSig, *,
        session: object | None = None) -> LogicOutcome:
    """投资环境选择上报(即时形态):按成功应用完整结果。

    - 名字标准化契约 = 观察层(op-layer.md §1.1「观察标准化门」),本函数
      零名字转换:按 ``param.idx`` 从容器 ``invest_env_opts`` 取标准名
      直传链([索引定义] 坐标系 = 容器 opts 列表下标(0 基),与观察帧
      ``obs.options`` 同序,槽位表恒稳);
    - 容器缺读(None)/idx 越界 = 响亮失败(异常上抛,容器写腿零吞错
      同款——选卡链发生时观察必然已完成,此态 = 代码 bug);
    - ``session`` = 策略会话(portal 登记腿消费;``None`` = 登记腿跳过
      [局外/测试形态],容器写照常);
    - 出参 applied=True = 受理;reason = ``gain_chain_applied``。
    """
    _validate_sig(sig, ('logic_action',))
    opts = gs.invest_env_opts.value
    if not opts or not 0 <= param.idx < len(opts):
        raise ValueError(
            f'[cw!] 投资环境容器缺读/idx 越界:idx={param.idx},'
            f'invest_env_opts={opts!r}(选卡链发生时观察必然已完成)')
    gain_invest_env(gs, session, opts[param.idx], rand=False, sig=sig)
    return LogicOutcome(applied=True, reason='gain_chain_applied')
