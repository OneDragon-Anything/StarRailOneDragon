"""sim 重做·牌池(M06 不变量派生池)。

设计正本 = ``docs/develop/sr_od/application/currency_war/changes/
2026-09-15-sim-redesign/design.md`` §2.2 M06 / §2.4.2(牌池行):

- 每卡副本数 1/2 费 27、3/4/5 费 9(``POOL_COPIES_PER_CARD``,V3.7 口径
  收案,依据 ``research/economy.md`` §1);
- **池量按不变量派生**:剩余牌库 = 固定牌库 − 手上持有副本总数
  (held 由容器 bench/deployed 星级派生,Σ 3^(star−1);合成不销毁,
  2★ 计 3 张/3★ 计 9 张)。买/卖/合成只改容器持有态,禁「卖出回池」
  可变计数事件(替换旧 ``_Pool.take/ret`` 可变模型);
- ≥9 清空:持有某牌 ≥9 张 → 该牌不再进店(发牌过滤,U11 定稿口径:
  「后续发牌过滤」建模;试用与自有同池同计数);
- 池构成族突变(U10 定稿口径):首版只建模专家入池(同费档追加 9 副本,
  标注待核);黑塔纪元特殊池/人才下沉/援军类触发时披露未建模。

随机量:无(池是派生状态;抽名的随机在 M05 发牌流)。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import POOL_COPIES_PER_CARD
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_slots_of,
    deployed_slots_of,
)

#: 专家入池追加副本数(U10 首版假设,标注待核;普通卡 3/4/5 费同为 9)。
EXPERT_COPIES_ASSUMED: int = 9


def fixed_pool(*, extra_experts: dict[str, int] | None = None) -> dict[str, int]:
    """解析后固定牌库(名 → 副本数)。

    基础 = 注册表全角色 × ``POOL_COPIES_PER_CARD`` 按费取副本;专家入池
    (U10 首版建模的唯一突变族)= 调用方按在场环境具名追加(同费档
    ``EXPERT_COPIES_ASSUMED``,待实机核);未入注册表的角色名在此拒收
    (防拼写漂移静默造池)。
    """
    pool: dict[str, int] = {}
    for name, ch in CHARACTERS.items():
        copies = POOL_COPIES_PER_CARD.get(ch.cost, 0)
        if copies > 0:
            pool[name] = copies
    for name, copies in (extra_experts or {}).items():
        if name not in CHARACTERS:
            raise ValueError(f'专家入池名 {name!r} 不在角色注册表'
                             '(U10:池构成突变须具名注册表角色)')
        pool[name] = pool.get(name, 0) + copies
    return pool


def held_copies(gs: GameState) -> dict[str, int]:
    """持有副本账(名 → Σ 3^(star−1);容器 bench/deployed 星级派生)。

    单一派生口:开局手牌写入 bench 后本函数即有定义(M06「首个写端」
    语义 = 派生自此不再需要可变账本);试用与自有同池同计数(U11)。
    """
    held: dict[str, int] = {}
    units = [b for b in bench_slots_of(gs) if b is not None]
    units += [d for d in deployed_slots_of(gs) if d is not None]
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
                'held 派生与发牌约束不一致,sim 内部 bug)')
        remaining[name] = value
    return remaining, held


def remaining_pool(gs: GameState, *,
                   extra_experts: dict[str, int] | None = None) -> dict[str, int]:
    """剩余池 = 固定牌库 − held(不变量派生;负值 = 池守恒破,显式炸错)。

    负值不可能由合法动作产生(买上限受池约束);出现即 sim 内部 bug,
    静默夹零会掩盖病灶,按显式暴露处置。
    """
    return _remaining_and_held(gs, extra_experts=extra_experts)[0]


def drawable_names(gs: GameState, cost: int, *,
                   extra_experts: dict[str, int] | None = None) -> list[str]:
    """某费用档当前可进店名集(剩余 > 0 且 held < 9;≥9 清空 = 发牌
    过滤,U11 定稿口径——1/2 费 27 副本下 held ≥9 时仍有剩余,两条件
    不可互替)。"""
    remaining, held = _remaining_and_held(gs, extra_experts=extra_experts)
    return sorted(
        name for name, left in remaining.items()
        if left > 0 and held.get(name, 0) < 9
        and CHARACTERS[name].cost == cost)
