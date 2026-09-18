"""sim 重做·玩家动作应用面与经验账本(M07/M08/M09)。

设计正本 = ``docs/develop/sr_od/application/currency_war/changes/
2026-09-15-sim-redesign/design.md`` §2.2 M07/M08/M09:

- **动作应用单一源**:动作语义全部住 kernel 上报函数族
  (kernel/cw_action_report,每动作一个具名接口);本入口 = 「一行委托
  分支串」引擎(动作 op 重组批④,design.md §2——分派只允许出现在
  手里攥着任意 param 流的引擎入口);拒绝语义在腿内(``LogicOutcome``
  出参,禁引擎自判拒绝);部署 = ``CwActionDeployMoveParam`` 同串直调
  上报函数。sim 自喂 ``executed`` 决定量(refresh_paid = refresh_cost_for、
  levelup_clicks=1;买牌 k 自算,满栏合成买在函数内);
- **LEVEL_CAP 分歧反转**(§2.4.2):真值 cap=10、lv10 拒付(旧 sim
  冻结 lv9 的 sim-only 差异删除);kernel 上报函数满级门单一源即
  ``MAX_PLAYER_LEVEL=10``,本模块不再设第二把尺;
- **XP 权威账本在引擎**(M08,机制口径 = ``research/xp-rules.md``):
  节点基础经验 战斗/奖励/遭遇 +2、补给 +0、BOSS +12(U17 定稿口径:
  位面末一次性);**买牌不产经验**(M08 机制口径;旧引擎「买牌累加
  XP」口径随重做废弃);升级结转规则与 ``xp_apply_clicks`` 单一源
  同式,通用量版(节点经验含非 4 倍数)在本模块承载;
- 升级不触发刷新 / 买后槽位留空不紧缩 = 上报函数与发牌面既有语义,
  引擎相位机承载。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_action_report.buy_card import (
    report_action_buy_card_param,
)
from sr_od.application.currency_war.kernel.cw_action_report.close_shop import (
    report_action_close_shop_param,
)
from sr_od.application.currency_war.kernel.cw_action_report.deploy_move import (
    report_action_deploy_move_param,
)
from sr_od.application.currency_war.kernel.cw_action_report.level_up import (
    report_action_level_up_param,
)
from sr_od.application.currency_war.kernel.cw_action_report.level_up_shop import (
    report_action_level_up_shop_param,
)
from sr_od.application.currency_war.kernel.cw_action_report.refresh_shop import (
    record_refresh_execution,
    report_action_refresh_shop_param,
)
from sr_od.application.currency_war.kernel.cw_action_report.sell_bench import (
    report_action_sell_bench_param,
)
from sr_od.application.currency_war.kernel.cw_action_report.sell_deployed import (
    report_action_sell_deployed_param,
)
from sr_od.application.currency_war.kernel.cw_action_report.swap_deploy import (
    report_action_swap_deploy_param,
)
from sr_od.application.currency_war.kernel.cw_economy import (
    MAX_PLAYER_LEVEL,
    XP_TO_NEXT_LEVEL,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    LogicOutcome,
    ShopActionExecuted,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwAction,
    CwActionBuyCardParam,
    CwActionCloseShopParam,
    CwActionDeployMoveParam,
    CwActionLevelUpParam,
    CwActionLevelUpShopParam,
    CwActionRefreshShopParam,
    CwActionSellBenchParam,
    CwActionSellDeployedParam,
    CwActionSwapDeployParam,
)
from sr_od.application.currency_war.sim.cw_sim_base import (
    logic_sig,
    obs_sig,
    sim_evidence,
)
from sr_od.application.currency_war.sim.cw_sim_shop import refresh_cost_for

#: 节点基础经验表(M08,依据 xp-rules.md;BOSS +12 = U17 定稿口径,
#: 构成/改道候实机数据,披露键 = 'node_xp_pending_u17')。
NODE_XP_BY_TYPE: dict[str, int] = {
    'battle': 2,
    'reward': 2,
    'encounter': 2,
    'supply': 0,
    'boss': 12,
}

#: U17 余项披露键(BOSS +12 构成/P3 低难度经验/改道类,候实机数据)。
NODE_XP_PENDING_U17: str = 'node_xp_pending_u17'


def apply_player_action(gs: GameState, action: CwAction, *,
                        node_tag: str = 'prep') -> LogicOutcome | None:
    """玩家动作 → 上报函数委托分支串(sim 引擎唯一动作入口;动作 op 重组
    批④,design.md §2——分派只允许出现在引擎入口,逐类型一行委托)。

    - ``CwActionDeployMoveParam``:直调上阵上报(出参忽略,返 None;
      陈旧提案守卫/落位拒绝在腿内)。
    - 商店族(买/卖备战/卖上阵/换位/购买经验含商店屏双类型/刷新/关店):
      逐类型直调对应上报函数;sim 自喂 ``executed`` 决定量——刷新实付金
      = ``refresh_cost_for``(免费刷额度先行),购买经验击数恒 1(单动作
      形态,腾席链多击归策略器多发动作),买牌 k 自算(满栏合成买在
      函数内)。
    - 应用成功且为刷新 → 刷新执行事实组记账(§3.3.6-8:免费帧闸;
      record_refresh_execution 挂 outcome.applied 原位保留)。
    - 词表外/集外动作 = applied=False 'unsupported_action_type'(原聚合
      口拒绝语义逐位平移,禁静默吞)。
    """
    sig = logic_sig(group_id=f'act:sim@{node_tag}')
    if isinstance(action, CwActionDeployMoveParam):
        report_action_deploy_move_param(gs, action, sig)
        return None
    executed = ShopActionExecuted(levelup_clicks=1)
    if isinstance(action, CwActionBuyCardParam):
        return report_action_buy_card_param(gs, action, sig, executed=executed)
    if isinstance(action, CwActionSellBenchParam):
        return report_action_sell_bench_param(gs, action, sig)
    if isinstance(action, CwActionSellDeployedParam):
        return report_action_sell_deployed_param(gs, action, sig)
    if isinstance(action, CwActionSwapDeployParam):
        return report_action_swap_deploy_param(gs, action, sig)
    if isinstance(action, CwActionLevelUpShopParam):
        return report_action_level_up_shop_param(gs, action, sig,
                                                 executed=executed)
    if isinstance(action, CwActionLevelUpParam):
        return report_action_level_up_param(gs, action, sig, executed=executed)
    if isinstance(action, CwActionRefreshShopParam):
        executed = ShopActionExecuted(
            refresh_paid=refresh_cost_for(gs), levelup_clicks=1)
        outcome = report_action_refresh_shop_param(gs, action, sig,
                                                   executed=executed)
        if outcome.applied:
            record_refresh_execution(gs, free=(executed.refresh_paid == 0),
                                     frame=node_tag)
        return outcome
    if isinstance(action, CwActionCloseShopParam):
        return report_action_close_shop_param(gs, action, sig)
    return LogicOutcome(applied=False, reason='unsupported_action_type')


def xp_apply_amount(level: int, xp_cur: int, amount: int) -> tuple[int, int]:
    """任意经验量推进 ``(level, xp_cur)``(升级结转与 ``xp_apply_clicks``
    单一源同式:攒满门槛即升级、溢出结转;cap = ``MAX_PLAYER_LEVEL``,
    满级零推进——lv10 分母未定,按 U18 口径不再累计)。

    通用量版理由:节点基础经验含非单击倍数(+2/+12),无法折成
    「购买经验击数」走既有算子。
    """
    if amount <= 0 or level >= MAX_PLAYER_LEVEL:
        return level, xp_cur
    cur = xp_cur + amount
    while level < MAX_PLAYER_LEVEL:
        need = XP_TO_NEXT_LEVEL.get(level, 4)
        if cur < need:
            break
        cur -= need
        level += 1
    return level, cur


def apply_node_xp(gs: GameState, *, node_type: str) -> int:
    """节点结算基础经验入账(M08;补给 +0 = 表内显式档)。

    写容器 xp = (当前级已攒, 升下一级所需);集外节点型 = 0 经验不入账
    (词表漂移在调用方暴露)。返回本节点实际入账经验量。
    """
    amount = NODE_XP_BY_TYPE.get(node_type, 0)
    if amount <= 0:
        return 0
    xp_field = gs.xp.value
    level_field = gs.level.value
    if xp_field is None or level_field is None:
        return 0
    level, cur = xp_apply_amount(int(level_field), int(xp_field[0]), amount)
    need = XP_TO_NEXT_LEVEL.get(level, int(xp_field[1]))
    sig = obs_sig(group_id='sim:xp')
    gs.observe(gs.level, level, evidence=sim_evidence('xp:node'), sig=sig)
    gs.observe(gs.xp, (cur, need), evidence=sim_evidence('xp:node'), sig=sig)
    return amount
