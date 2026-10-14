"""货币战争动作上报:投资环境选择(report_action_pick_invest_env_param)。

即时上报形态(action_ops.md §1 用户裁定增补 2):动作 op 机械链发出后
调用本函数,一次调用 = 完整结果写入——整支走获得链 ``gain_invest_env``
(active_env 注册 + portal 登记 + ``on_env_gained`` 环境赠卡效果枚举,
正本 = game_state/gain-chain.md)。

本包 → 容器单向依赖:名字标准化契约 = 观察层(op-layer.md §1.1「观察
标准化门」),容器 ``invest_env_opts`` 值域 = 标准注册名,本包零名字
转换、按选择序号取标准名直传链。随机支采样 rng(环境登记
chars_random_immediate 时)经 ``action_sampling_rng`` 条件解析注入
(先例 = pick_invest_strategy 的 rng 形参;同包查 ENV_GIFTS 先例 =
pick_planner)。

**后果声明**(动作后果声明化详设 world-decl.md §2 表 #7):applied 出口
构造 ``WorldDecl``(trigger = ``pick_invest_env``;``next_screen`` =
备战屏,权威 = sim ``_on_invest_picked`` 结束本次访问 + 开局判别推导见详设 §3),
转移事件广播随本动作单轨切换摘除。⚠️ 备战值隐性耦合现役 offer 日程
(日程节点均 battle/reward → 备战;日程扩面时须随节点 kind 推导化)。
"""
from __future__ import annotations

import random
from typing import Any

from sr_od.application.currency_war.kernel.cw_gain_chain import (
    gain_invest_env,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    SCREEN_PREP_FRAME,
    ChannelSig,
    GameState,
    LogicOutcome,
    _validate_sig,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    ENV_GIFTS,
)
from sr_od.application.currency_war.kernel.cw_world_decl import WorldDecl

#: 投资环境声明的推进分派类别(详设 §2 表 #7;封闭集单一源 = sim 后端
#: advance 分派表键集,值零新词沿用现役动作名)。
_DECL_TRIGGER: str = 'pick_invest_env'


def report_action_pick_invest_env_param(
        gs: GameState, param: Any, sig: ChannelSig, *,
        rng: random.Random | None = None,
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
    - ``rng`` = 环境随机支(chars_random_immediate)采样注入,**条件解析**:
      仅选中环境登记了随机支才经 ``action_sampling_rng('pick_invest_env',
      rng)`` 解析(显式传入 > 注入槽 > 自掷);无随机支环境透传 None
      (零解析)。条件解析的理由:注入槽是每次调用即推序号的全局计数器
      (cw_sim_backend install_backend),无条件解析会使任何环境选卡都
      推号、后继动作采样流键整体位移 = 跨版本 sim A/B 无关变量噪声;
      条件解析把位移收窄到「真发放随机支的局」,「默认环境局 rng 消耗
      序列逐位不变」严格成立;
    - 出参 applied=True = 受理;reason = ``gain_chain_applied``;出口
      构造后果声明(:data:`_DECL_TRIGGER`,结束本次访问备战)。
    """
    _validate_sig(sig, ('logic_action',))
    opts = gs.invest_env_opts.value
    if not opts or not 0 <= param.idx < len(opts):
        raise ValueError(
            f'[cw!] 投资环境容器缺读/idx 越界:idx={param.idx},'
            f'invest_env_opts={opts!r}(选卡链发生时观察必然已完成)')
    _name = opts[param.idx]
    # 条件解析(见 docstring):ENV_GIFTS 查表判定随机支在场才解析采样
    # rng——容器值域 = 标准注册名(观察标准化门),零转换直查
    _grant = ENV_GIFTS.get(_name)
    _rng = rng
    if _grant is not None and _grant.chars_random_immediate:
        from sr_od.application.currency_war.kernel.cw_action_report import (
            action_sampling_rng,
        )
        _rng = action_sampling_rng('pick_invest_env', rng)
    gain_invest_env(gs, session, _name, rand=False, sig=sig, rng=_rng)
    return LogicOutcome(
        applied=True, reason='gain_chain_applied',
        world_decl=WorldDecl(next_screen=SCREEN_PREP_FRAME,
                             trigger=_DECL_TRIGGER))
