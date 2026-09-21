"""货币战争动作上报:投资策略选择(report_action_pick_invest_strategy_param)。

即时上报形态(action_ops.md §1 用户裁定增补 2:选择动作执行按成功处理,
点完立即上报把结果写进 game state):动作 op 机械链(点选中 → 点确认)
发出后调用本函数,一次调用 = 完整结果写入——整支走获得链
``gain_invest_strategy``(无效载荷拒绝 → active_strategies 按名字去重
追加 → 效果账本登记腿 → ``on_strategy_gained`` 效果分派,正本 =
game_state/gain-chain.md)。

自 ``pick_invest.py`` 拆分(投资两屏迁移批:两屏共用一词表类 + source
字符串分流废除,每屏一词表类一上报函数;原「发射相意图遥测/落地相证据
闩」分步上报随拆分废除)。本包 → 容器单向依赖。
"""
from __future__ import annotations

import random
from typing import Any

from sr_od.application.currency_war.kernel.cw_gain_chain import (
    gain_invest_strategy,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    LogicOutcome,
    _validate_sig,
)


def _canon_invest_name(name: str) -> str:
    """归一卡名(全角冒号→半角 OCR 形变 + 注册表归一;注册表规范名键域)。
    链内入口会再 normalize(幂等)。"""
    from sr_od.application.currency_war.kernel.cw_investments import (
        normalize_invest_name,
    )
    return normalize_invest_name((name or '').replace('：', ':'))


def report_action_pick_invest_strategy_param(
        gs: GameState, param: Any, sig: ChannelSig, *,
        rng: random.Random | None = None,
        session: object | None = None) -> LogicOutcome:
    """投资策略选择上报(即时形态):按成功应用完整结果。

    - ``param.norm_name`` = 选中卡归一规范名(handler 持有 OCR 原始名);
      归一后空/'?' = 无效载荷,链内零写 + 缺陷留证;
    - ``session`` = 策略会话(效果账本登记腿消费;kernel 禁自取上下文,
      由动作 op 显式传入;``None`` = 登记腿跳过[局外/测试形态],容器写
      照常);
    - ``rng`` = 采样注入(sim 可播种;缺省链内生成);
    - 出参 applied=True = 受理;reason = ``gain_chain_applied``(获得链
      结果可辨形态,投资双支对齐)。
    """
    _validate_sig(sig, ('logic_action',))
    canon = _canon_invest_name(str(getattr(param, 'norm_name', '') or ''))
    gain_invest_strategy(gs, session, canon, rand=False, sig=sig, rng=rng)
    return LogicOutcome(applied=True, reason='gain_chain_applied')
