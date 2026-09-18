"""sim 重做·玩家动作应用面与经验账本(M07/M08/M09)。

设计正本 = ``docs/develop/sr_od/application/currency_war/changes/
2026-09-15-sim-redesign/design.md`` §2.2 M07/M08/M09:

- **动作应用单一源**:买/卖/刷/升级/换位全部经 kernel 单一转移函数
  ``apply_shop_action_logic``(拒绝语义在腿内,``LogicOutcome`` 出参;
  禁引擎自判拒绝);部署 = ``CwActionDeployMoveParam`` 经 ``apply_prep_action_logic``
  (kernel 平移契约:CwActionDeployMoveParam 不入商店转移口)。满栏合成买/连锁合成
  在转移函数内(sim 传 ``executed=None`` 自算 k;刷新实付金由引擎侧
  ``refresh_paid`` 显式喂——免费刷额度先行的申报差异 #2 参数通道);
- **LEVEL_CAP 分歧反转**(§2.4.2):真值 cap=10、lv10 拒付(旧 sim
  冻结 lv9 的 sim-only 差异删除);kernel 转移函数满级门单一源即
  ``MAX_PLAYER_LEVEL=10``,本模块不再设第二把尺;
- **XP 权威账本在引擎**(M08,机制口径 = ``research/xp-rules.md``):
  节点基础经验 战斗/奖励/遭遇 +2、补给 +0、BOSS +12(U17 定稿口径:
  位面末一次性);**买牌不产经验**(M08 机制口径;旧引擎「买牌累加
  XP」口径随重做废弃);升级结转规则与 ``xp_apply_clicks`` 单一源
  同式,通用量版(节点经验含非 4 倍数)在本模块承载;
- 升级不触发刷新 / 买后槽位留空不紧缩 = 转移函数与发牌面既有语义,
  引擎相位机承载。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_action_report.refresh_shop import (
    record_refresh_execution,
)
from sr_od.application.currency_war.kernel.cw_economy import (
    MAX_PLAYER_LEVEL,
    XP_TO_NEXT_LEVEL,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    LogicOutcome,
    ShopActionExecuted,
    apply_prep_action_logic,
    apply_shop_action_logic,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwAction,
    CwActionDeployMoveParam,
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
    """玩家动作 → 单一转移函数应用(sim 引擎唯一动作入口)。

    - 商店族(CwActionBuyCardParam/CwActionSellBenchParam/CwActionSellDeployedParam/CwActionSwapDeployParam/CwActionLevelUpShopParam/
      CwActionRefreshShopParam/CwActionCloseShopParam):经 ``apply_shop_action_logic``;刷新实付
      金 = ``refresh_cost_for``(免费刷额度先行)显式喂 ``executed``;
      买牌 k 自算(满栏合成买在转移函数内);CwActionLevelUpShopParam 击数恒 1
      (单动作形态,腾席链多击归策略器多发动作)。
    - ``CwActionDeployMoveParam``:经 ``apply_prep_action_logic``(无出参,返 None;
      同名守卫/落位拒绝在腿内)。
    - 应用成功且为刷新 → 刷新执行事实组记账(§3.3.6-8:免费帧闸)。
    """
    if isinstance(action, CwActionDeployMoveParam):
        apply_prep_action_logic(gs, action, produced_by='SimEngineV2',
                                sig=logic_sig(group_id=f'act:sim@{node_tag}'))
        return None
    paid: int | None = None
    from sr_od.application.currency_war.kernel.cw_vocab import CwActionRefreshShopParam
    if isinstance(action, CwActionRefreshShopParam):
        paid = refresh_cost_for(gs)
    outcome = apply_shop_action_logic(
        gs, action, produced_by='SimEngineV2',
        sig=logic_sig(group_id=f'act:sim@{node_tag}'),
        executed=(ShopActionExecuted(refresh_paid=paid, levelup_clicks=1)
                  if paid is not None else ShopActionExecuted(levelup_clicks=1)))
    if outcome.applied and paid is not None:
        record_refresh_execution(gs, free=(paid == 0), frame=node_tag)
    return outcome


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
