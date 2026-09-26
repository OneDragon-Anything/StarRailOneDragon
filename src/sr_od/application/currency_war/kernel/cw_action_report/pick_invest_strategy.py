"""货币战争动作上报:投资策略选择(report_action_pick_invest_strategy_param)。

即时上报形态(action_ops.md §1 用户裁定增补 2:选择动作执行按成功处理,
点完立即上报把结果写进 game state):动作 op 机械链(点选中 → 点确认)
发出后调用本函数,一次调用 = 完整结果写入——整支走获得链
``gain_invest_strategy``(无效载荷拒绝 → active_strategies 按名字去重
追加 → 效果账本登记腿 → ``on_strategy_gained`` 效果分派,正本 =
game_state/gain-chain.md)。本包 → 容器单向依赖。

**后果声明**(动作后果声明化详设 world-decl.md §2 表 #8):applied 出口
构造 ``WorldDecl``(trigger = ``pick_invest_strategy``;``next_screen`` =
备战屏,权威 = sim ``_on_invest_picked`` 交回;offer 日程耦合注同
pick_invest_env),转移事件广播随本动作单轨切换摘除。
"""
from __future__ import annotations

import random
from typing import Any

from sr_od.application.currency_war.kernel.cw_gain_chain import (
    gain_invest_strategy,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    SCREEN_PREP_FRAME,
    ChannelSig,
    GameState,
    LogicOutcome,
    _validate_sig,
)
from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl

#: 投资策略声明的推进分派类别(详设 §2 表 #8;封闭集单一源 = sim 后端
#: advance 分派表键集,值零新词沿用现役动作名)。
_DECL_TRIGGER: str = 'pick_invest_strategy'


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
      结果可辨形态,投资双支对齐);出口构造后果声明
      (:data:`_DECL_TRIGGER`,交回备战)。
    """
    _validate_sig(sig, ('logic_action',))
    canon = _canon_invest_name(str(getattr(param, 'norm_name', '') or ''))
    from sr_od.application.currency_war.kernel.cw_action_report import (
        action_sampling_rng,
    )
    gain_invest_strategy(
        gs, session, canon, rand=False, sig=sig,
        rng=action_sampling_rng('pick_invest_strategy', rng))
    # 阿哈直登(用户确认:选中
    # 「阿哈大悦」确认后弹简易装备四选一,唯一路径 = 本上报)。
    if canon == '阿哈大悦':
        from sr_od.application.currency_war.kernel.cw_overlay_register import (
            KIND_SCREEN_NAMES,
            register_screen_change,
        )
        register_screen_change(
            gs, 'aha', KIND_SCREEN_NAMES['aha'],
            source='s5_pick@pick_invest_strategy')
    return LogicOutcome(
        applied=True, reason='gain_chain_applied',
        world_decl=WorldDecl(next_screen=SCREEN_PREP_FRAME,
                             trigger=_DECL_TRIGGER))
