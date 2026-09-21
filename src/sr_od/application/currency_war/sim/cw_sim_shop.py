"""sim 重做·商店系统(M05)。

设计正本 = ``docs/develop/sr_od/application/currency_war/changes/
2026-09-15-sim-redesign/design.md`` §2.2 M05(依据 ``research/economy.md``
§2/§2.1):

- 备战商店恒 5 槽(``SHOP_SLOTS``;昔涟诗篇改槽数未证实,U27 附注不建模);
- 发牌 = 逐槽独立:先按概率表定费用档 → M06 剩余池内均匀抽名(旧
  ``draw_shop`` 骨架平移);同帧允许重复同名(U13:无去重记载,无依据
  不加规则);直出 2/3 星概率 = 0(U12 首版口径,仅明确效果触发的
  变费/升星机制建模);
- 手动刷新 2 金/次恒定(``REFRESH_COST_BASE`` 多局对账定谳);免费刷
  额度先行(效果账本免费余额);刷新重置整店 5 槽;
- 节点切换自动全刷零继承 / 升级不触发刷新 / 整店锁(锁定后跨节点不
  自动刷)——推进时机由引擎相位机承载,本模块只供发牌与刷价;
- 轮岗环境(重做设计稿 M02 挂钩):每备战阶段重掷翻倍档 = kernel
  ``roll_rotation_per_stage``(机制 = 100% 重掷;翻倍档分布 1/5 均匀系
  建模假设待核,假设档随披露面申报)。

随机流键(引擎侧装配):发牌 ``M05/deal/{plane}/{round}``、
轮岗档 ``M05/rotation/{plane}/{round}``。
"""
from __future__ import annotations

import random

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import (
    REFRESH_PROB,
    SHOP_SLOTS,
)
from sr_od.application.currency_war.kernel.cw_battle_calib import (
    roll_rotation_per_stage,
)
from sr_od.application.currency_war.kernel.cw_economy import REFRESH_COST_BASE
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    ShopCard,
    ShopPayload,
    ShopSlot,
)
from sr_od.application.currency_war.kernel.cw_pool import drawable_names
from sr_od.application.currency_war.sim.cw_sim_base import obs_sig, sim_evidence

#: 轮岗建模假设档披露键(1/5 均匀系假设,实机待核;随局披露面消费)。
ROTATION_ASSUMPTION_DISCLOSURE: str = 'rotation_tier_assumed_uniform'


def effective_deal_probs(level: int, rng: random.Random, *,
                         rotation_on: bool) -> dict[int, float]:
    """本备战期发牌概率表(基线 = ``REFRESH_PROB[level]``;轮岗环境在场
    = 每阶段重掷翻倍档)。"""
    if not rotation_on:
        return dict(REFRESH_PROB.get(level, {}))
    rolled = roll_rotation_per_stage(rng, level)
    return dict(rolled) if rolled is not None \
        else dict(REFRESH_PROB.get(level, {}))


def refresh_cost_for(gs: GameState) -> int:
    """本次刷新实付金(免费刷额度先行 → 0;否则基价 2 恒定)。

    免费余额域 = 效果账本(2026-09-18 迁入裁决:
    ``gs.effects.free_refresh_balance``;效果发放 +/刷新执行 −,0 起)。
    """
    return 0 if gs.effects.free_refresh_balance > 0 else REFRESH_COST_BASE


def deal_shop(gs: GameState, rng: random.Random, *, level: int,
              probs: dict[int, float] | None = None,
              extra_experts: dict[str, int] | None = None,
              tag: str = 'shop:deal') -> None:
    """整店发牌并写容器商店载荷(obs 渠道;刷新/节点切换/开局进场共用)。

    逐槽独立:费用档按 ``probs``(缺省基线表)加权掷点 → M06 可进店
    名集内均匀抽名;名集空(该档池被清空/低等级无该档)→ 槽留空
    (定长 5 槽三态模型的 empty 槽,买后留空同款语义)。
    """
    dist = probs if probs is not None else REFRESH_PROB.get(level, {})
    costs = [c for c, p in dist.items() if p > 0]
    slots: list[ShopSlot] = []
    for i in range(SHOP_SLOTS):
        card: ShopCard | None = None
        if costs:
            cost = rng.choices(costs, weights=[dist[c] for c in costs],
                               k=1)[0]
            names = drawable_names(gs, cost, extra_experts=extra_experts)
            if names:
                name = rng.choice(names)
                ch = CHARACTERS[name]
                card = ShopCard(
                    name=name, faction=(ch.factions or ('散',))[0],
                    cost=cost, star=1, cost_source='roster', slot=i + 1)
        slots.append(ShopSlot(kind='content' if card is not None
                              else 'empty', card=card))
    gs.observe(gs.shop,
               ShopPayload(cards=slots,
                           refresh_probs={int(k): float(v)
                                          for k, v in (probs or dist).items()
                                          if v > 0}),
               evidence=sim_evidence(tag), sig=obs_sig(group_id=f'sim:{tag}'))


def empty_shop_slots(gs: GameState) -> int:
    """当前商店空槽数(诊断/判读披露用;买后留空不紧缩的派生读数)。

    payload 离屏(None)= 0(无店非空店,双义防混:消费方按 shop.value
    is None 另行判定,本函数只在开态语义下调用)。
    """
    payload = gs.shop.value
    if payload is None:
        return 0
    return sum(1 for s in payload.cards if s.kind == 'empty')
