"""货币战争 剩余牌库派生(固定牌库 − 持有;商店发牌与效果随机授予共用的采样空间单一源)。

- 每卡副本数:1/2 费 27、3/4/5 费 9(常量单一源 =
  ``data/cw_shop_odds.py`` 的 ``POOL_COPIES_PER_CARD``;口径出处 =
  ``docs/game/currency_war/research/economy.md`` §1)——3/4/5 费同 9,
  升费换档只换桶归属、副本数不变;
- **池量按不变量派生**:剩余牌库 = 固定牌库 − 持有副本总数(held 由容器
  bench/deployed 星级派生,Σ 3^(star−1);合成不销毁,2★ 计 3 张/3★ 计
  9 张)。买/卖/合成只改容器持有态,无「卖出回池」可变计数事件;
- **双出口**(档过滤与商店过滤解耦,两出口共用一次派生无第二实现):
  商店发牌出口 :func:`drawable_names` = 档匹配 ∧ 剩余 >0 ∧ 持有 <9
  (持有某牌 ≥9 张 → 该牌不再进店 = 商店通道定谳口径;试用与自有同池
  同计数);效果随机授予出口 :func:`grant_bucket_names` = 档匹配 ∧
  剩余 >0(**不含 ≥9 过滤**——授予通道是否受清空约束无定谳,商店口径
  不无据继承,v0 披露随函数申报);
- 池构成族突变首版只建模专家入池(同费档追加 9 副本,标注待核);黑塔
  纪元特殊池/人才下沉/援军类触发时未建模。

随机量:无(池是派生状态非动作;抽名随机与随机效果收口由消费方辖——
效果批采样后经 ``logic_rand_outcome`` 行候校准,本模块只供采样空间查询)。

守恒破显式炸错语义申报:剩余出现负值即 raise(文案 = 「池派生与持有
约束不一致」),跨层后果 = 沿消费链直达运行层、run 停(效果链登记腿
best-effort 不兜容器写)。实机侧 held 为观察容器派生,观测噪声(单位
身份/星级误读)同样可触发;响停修因优于静默夹零(夹零掩盖病灶),语义
按显式暴露接受。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import POOL_COPIES_PER_CARD
from sr_od.application.currency_war.kernel.cw_economy import effective_cost
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_units_of,
    deployed_rows_of,
)

#: 专家入池追加副本数(首版建模假设,标注待核;普通卡 3/4/5 费同为 9)。
EXPERT_COPIES_ASSUMED: int = 9

#: 授予出口 v0 披露键·维度一(未实测):授予采样是否受商店「持有 ≥9
#: 清空」约束——本出口现态 = 不受;效果批消费后由 ``logic_rand_outcome``
#: 行候校准(冶金炉采样池同款先例)。
GRANT_BUCKET_NO_NINE_FILTER_V0: str = 'grant_bucket_no_nine_filter_v0'

#: 授予出口 v0 披露键·维度二(未实测):消费方抽名分布 = **按名均匀**,
#: 非按剩余副本数加权(本出口返回去重名集,不含权重信息)。
GRANT_BUCKET_UNIFORM_BY_NAME_V0: str = 'grant_bucket_uniform_by_name_v0'


def fixed_pool(*, extra_experts: dict[str, int] | None = None) -> dict[str, int]:
    """解析后固定牌库(名 → 副本数)。

    基础 = 注册表全角色 × ``POOL_COPIES_PER_CARD`` 按费取副本;专家入池
    (池构成突变首版建模的唯一突变族)= 调用方按在场环境具名追加(同费档
    ``EXPERT_COPIES_ASSUMED``,待实机核);未入注册表的角色名在此拒收
    (防拼写漂移静默造池)。纯注册表派生:剩余池按名计、费用桶只在查询
    时现分,档不进本函数签名、gs 不入纯派生。
    """
    pool: dict[str, int] = {}
    for name, ch in CHARACTERS.items():
        copies = POOL_COPIES_PER_CARD.get(ch.cost, 0)
        if copies > 0:
            pool[name] = copies
    for name, copies in (extra_experts or {}).items():
        if name not in CHARACTERS:
            raise ValueError(f'专家入池名 {name!r} 不在角色注册表'
                             '(池构成突变须具名注册表角色)')
        pool[name] = pool.get(name, 0) + copies
    return pool


def held_copies(gs: GameState) -> dict[str, int]:
    """持有副本账(名 → Σ 3^(star−1);容器 bench/deployed 星级派生)。

    单一派生口:开局手牌写入 bench 后本函数即有定义,无需可变账本;
    试用与自有角色同池同计数。同名即同档(全场同名角色费用档唯一,
    升费后含商店在架卡一律为新费用档),按名归并即完整账,与档无关。
    """
    held: dict[str, int] = {}
    front, back = deployed_rows_of(gs)
    units = list(bench_units_of(gs)) + [d for d in (*front, *back)
                                        if d is not None]
    for u in units:
        name = str(getattr(u, 'char_id', '') or '')
        if not name:
            continue
        star = max(1, int(getattr(u, 'star', 1) or 1))
        held[name] = held.get(name, 0) + 3 ** (star - 1)
    return held


def _remaining_and_held(gs: GameState, *,
                        extra_experts: dict[str, int] | None = None,
                        ) -> tuple[dict[str, int], dict[str, int]]:
    """(剩余池, held) 一次派生(剩余 = 固定 − held;守恒破显式炸错)。"""
    fixed = fixed_pool(extra_experts=extra_experts)
    held = held_copies(gs)
    remaining: dict[str, int] = {}
    for name, copies in fixed.items():
        value = copies - held.get(name, 0)
        if value < 0:
            raise ValueError(
                f'牌池守恒破:{name} 剩余 {value} < 0(固定 {copies};'
                '池派生与持有约束不一致)')
        remaining[name] = value
    return remaining, held


def remaining_pool(gs: GameState, *,
                   extra_experts: dict[str, int] | None = None) -> dict[str, int]:
    """剩余池 = 固定牌库 − held(不变量派生;负值 = 池守恒破,显式炸错)。

    负值出现即池派生与持有约束不一致(实机侧观测噪声亦可触发,跨层
    语义申报见模块头注);静默夹零会掩盖病灶,按显式暴露处置。
    """
    return _remaining_and_held(gs, extra_experts=extra_experts)[0]


def drawable_names(gs: GameState, cost: int, *,
                   extra_experts: dict[str, int] | None = None) -> list[str]:
    """某费用档当前可进店名集(商店发牌出口,sim 发牌消费)。

    三条件:费用档匹配(经 :func:`effective_cost` 档感知——银狼LV.999
    升费后当前档 = 容器 ``gs.lv999_cost_tier``,归入新费用档桶;其余角色
    恒等注册表值)∧ 剩余 > 0 ∧ held < 9(持有 ≥9 清空 = 商店发牌过滤
    定谳口径;1/2 费 27 副本下 held ≥9 时仍有剩余,两条件不可互替)。
    """
    remaining, held = _remaining_and_held(gs, extra_experts=extra_experts)
    return sorted(
        name for name, left in remaining.items()
        if left > 0 and held.get(name, 0) < 9
        and effective_cost(gs, name) == cost)


def grant_bucket_names(gs: GameState, cost: int, *,
                       extra_experts: dict[str, int] | None = None) -> list[str]:
    """某费用档当前可被随机授予名集(效果随机授予出口,效果批消费)。

    两条件:费用档匹配(:func:`effective_cost` 档感知,与商店出口同一
    过滤)∧ 剩余 > 0——**不含**商店「持有 ≥9 清空」过滤(授予通道是否
    受清空约束无定谳,商店口径不无据继承)。

    v0 口径双维披露(均未实测,效果批消费后由 ``logic_rand_outcome``
    行候校准,冶金炉采样池同款先例):
    - :data:`GRANT_BUCKET_NO_NINE_FILTER_V0`:是否受 ≥9 清空约束
      (本出口现态 = 不受);
    - :data:`GRANT_BUCKET_UNIFORM_BY_NAME_V0`:抽名分布 = 按名均匀,
      非按剩余副本数加权。

    调用时序契约(消费者侧):本函数为纯查询、held 仅容器派生——
    「先回归后重抽」定谳(2026-09-21)⇒ 消费方必须先把回归/摘除写落
    容器再采样;无工作副本派生入口,工作副本合并范式不适用于本出口。

    extra_experts 透传 = sim 兼容形态:kernel 授予调用恒缺省 None
    (专家入池 = 商店发牌概念,「专家 ∈ 授予采样空间」无定谳,调用方
    禁自填)。
    """
    remaining, _held = _remaining_and_held(gs, extra_experts=extra_experts)
    return sorted(
        name for name, left in remaining.items()
        if left > 0 and effective_cost(gs, name) == cost)
