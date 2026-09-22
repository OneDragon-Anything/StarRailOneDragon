"""货币战争 商店发牌采样器(kernel 侧纯采样,零容器写)。

算法本体自 ``sim/cw_sim_shop.py::deal_shop`` 迁入(2026-09-21 商店刷新
迭代 design §2-9/详设 §2.9「上报回调腿·刷新随机态」):刷新上报随机态
腿与 sim 发牌共用同一发牌代码——实机上采样是猜测(上报函数经
``write_logic_rand`` 写随机态,观察覆盖差异 = 预期内),sim 里采样即世界
真值(sim ``deal_shop`` 经 ``gs.observe`` 真值直写)。「两执行面同源」=
期望态两执行面同源原则(flow/projection_contract.md §3.6)在商店 payload
上的落地。

纯度边界:**只采样返回 payload,零容器写**——写通道各执行面自理(实机 =
刷新上报函数 ``report_action_refresh_shop_param`` 的 ``write_logic_rand``
腿 / sim = ``deal_shop`` 内 ``gs.observe``);``gs`` 仅作只读输入(剩余
牌库派生),禁在本模块写容器——把容器写搬进本函数会用随机态替换 sim 真
值路径,干旱/供给族消费门口径在 sim 全局跳拍(attack R6f 定谳)。

数据源 = ``data/cw_shop_odds.py`` 概率注册表(REFRESH_PROB/SHOP_SLOTS)
+ ``kernel/cw_pool.py`` 剩余牌库派生(drawable_names 商店发牌出口)。
逐槽独立:费用档按 ``probs`` 加权掷点 → 档内可进店名集均匀抽名;同帧
允许重复同名(U13:无去重记载,无依据不加规则);直出 2/3 星概率 = 0
(U12 首版口径,仅明确效果触发的变费/升星机制建模)。
"""
from __future__ import annotations

import random

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import (
    REFRESH_PROB,
    SHOP_SLOTS,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    ShopCard,
    ShopPayload,
    ShopSlot,
)
from sr_od.application.currency_war.kernel.cw_pool import drawable_names


def sample_shop_deal(gs: GameState, rng: random.Random, *, level: int,
                     probs: dict[int, float] | None = None,
                     extra_experts: dict[str, int] | None = None) -> ShopPayload:
    """整店 5 槽发牌采样(纯函数;返回 payload,零容器写——纯度边界见
    模块头)。

    逐槽独立:费用档按 ``probs``(缺省基线表 ``REFRESH_PROB[level]``)
    加权掷点 → M06 可进店名集(:func:`drawable_names`)内均匀抽名;名集
    空(该档池被清空/低等级无该档)→ 槽留空(定长 5 槽三态模型的 empty
    槽,买后留空同款语义)。``extra_experts`` 透传剩余牌库派生(专家入池,
    sim 兼容形态)。
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
    return ShopPayload(cards=slots,
                       refresh_probs={int(k): float(v)
                                      for k, v in (probs or dist).items()
                                      if v > 0})
