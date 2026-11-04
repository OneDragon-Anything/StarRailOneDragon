"""货币战争 商店发牌采样器(kernel 侧纯采样,零字段写)。

本模块 = 发牌算法单一源,sim ``deal_shop``(sim/cw_sim_backend)与实机
刷新上报随机态分支(kernel/cw_action_report/refresh_shop)共用同一发牌
代码(2026-09-21 商店刷新 design §2-9/详设 §2.9「上报回调分支·刷新随机
态」):实机上采样是猜测(上报函数经 ``write_logic_rand`` 写随机态,观察
覆盖差异 = 预期内),sim 里采样即状态副本真值(sim ``deal_shop`` 经
``gs.observe`` 真值直写)。「两执行面同源」= 期望态两执行面同源原则
(flow/projection_contract.md §3.6)在商店 payload 上的落地。

纯度边界:**只采样返回 payload,零字段写**——写通道各执行面自理(实机 =
刷新上报函数 ``report_action_refresh_shop_param`` 的 ``write_logic_rand``
分支 / sim = ``deal_shop`` 内 ``gs.observe``);``gs`` 仅作只读输入(剩余
牌库派生 + active_env 直出概率查表),禁在本模块写状态容器——把字段写搬进
本函数会用随机态替换 sim 真值路径,干旱/供给族消费门口径在 sim 全局跳拍
(attack R6f 定案)。

数据源 = ``data/cw_shop_odds.py`` 概率注册表(REFRESH_PROB/SHOP_SLOTS)
+ ``kernel/cw_pool.py`` 剩余牌库派生(drawable_names 商店发牌出口)
+ ``kernel/cw_investments.ENV_SHOP_TWO_STAR_DEAL_PROB``(2★ 直出概率,
环境白名单)。
逐槽独立:费用档按 ``probs`` 加权掷点 → 档内可进店名集均匀抽名;同帧
允许重复同名(U13:无去重记载,无依据不加规则);直出 2 星概率 = 环境
注册表 ``ENV_SHOP_TWO_STAR_DEAL_PROB``(表外恒 0;首例人才下沉 0.2 =
用户占位 2026-10-16,非 desc 真值,披露键
``shop_two_star_deal_prob_user_placeholder``);直出 3 星概率 = 0(U12
口径维持,仅明确效果触发的变费/升星机制建模)。
强制费用档整店发牌(:func:`sample_shop_deal_forced`)= 卡面「开启一个
由N个独特M费角色组成的商店」的显式例外通道(费用档定死 + unique 去
重均为卡面明文,不占基线 U13 先例)。
"""
from __future__ import annotations

import random

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.data.cw_shop_odds import (
    REFRESH_PROB,
    SHOP_SLOTS,
)
from sr_od.application.currency_war.kernel.cw_economy import effective_refresh_prob
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    ShopCard,
    ShopPayload,
    ShopSlot,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    ENV_SHOP_TWO_STAR_DEAL_PROB,
)
from sr_od.application.currency_war.kernel.cw_pool import drawable_names


def sample_shop_deal(gs: GameState, rng: random.Random, *, level: int,
                     probs: dict[int, float] | None = None) -> ShopPayload:
    """整店 5 槽发牌采样(纯函数;返回 payload,零字段写——纯度边界见
    模块头)。

    逐槽独立:费用档按 ``probs``(缺省基线表 ``REFRESH_PROB[level]``)
    加权掷点 → M06 可进店名集(:func:`drawable_names`)内均匀抽名;名集
    空(该档池被清空/低等级无该档)→ 槽留空(定长 5 槽三态模型的 empty
    槽,买后留空同款语义)。专家顾问入池由 ``drawable_names`` 从状态容器
    ``gs.unlocked_experts`` 派生(获得链解锁写入),本层零透传。

    2★ 直出分支:``ENV_SHOP_TWO_STAR_DEAL_PROB`` 命中当前 ``active_env``
    时,每个非空槽在抽名后独立掷 ``rng.random() < p``,命中则该卡升 2★
    (cost = 基准费×3,徽章读数口径 = merge_mechanics §2.6;买价 ×3 实付/
    卖回 ×3/池账 +3 副本经既有通用链自动正确;翻星在名集过滤后,不改名集
    语义)。掷点仅在 p>0 时进行(短路)——表外环境的随机数消耗序列与无
    本分支实现逐位一致。
    """
    dist = probs if probs is not None else REFRESH_PROB.get(level, {})
    costs = [c for c, p in dist.items() if p > 0]
    two_star_p = ENV_SHOP_TWO_STAR_DEAL_PROB.get(
        str(gs.active_env.value or ''), 0.0)
    slots: list[ShopSlot] = []
    for i in range(SHOP_SLOTS):
        card: ShopCard | None = None
        if costs:
            cost = rng.choices(costs, weights=[dist[c] for c in costs],
                               k=1)[0]
            names = drawable_names(gs, cost)
            if names:
                name = rng.choice(names)
                ch = CHARACTERS[name]
                star = 1
                if two_star_p > 0 and rng.random() < two_star_p:
                    star = 2
                    cost = cost * 3
                card = ShopCard(
                    name=name, faction=(ch.factions or ('散',))[0],
                    cost=cost, star=star, cost_source='roster', slot=i + 1)
        slots.append(ShopSlot(kind='content' if card is not None
                              else 'empty', card=card))
    return ShopPayload(cards=slots,
                       refresh_probs={int(k): float(v)
                                      for k, v in (probs or dist).items()
                                      if v > 0})


def state_deal_probs(gs: GameState, level: int) -> dict[int, float]:
    """GameState 感知的发牌概率表(逐档经 cw_economy.effective_refresh_prob
    单一源;观测概率条在场 = 真值直用——轮岗翻倍档含在内,缺读/缺键/≤0
    逐档退基线)。零新语义:优先级链单一源不复制。"""
    probs = {cost: effective_refresh_prob(gs, level, cost)
             for cost in range(1, 6)}
    return {cost: p for cost, p in probs.items() if p > 0}


def sample_shop_deal_forced(gs: GameState, rng: random.Random, *, cost: int,
                            unique: bool, level: int) -> ShopPayload:
    """强制费用档整店发牌采样(纯函数;零字段写,纯度边界同模块头)。

    卡面语 =「开启一个由5个独特N费角色组成的商店」(首条目 公司严选
    301401,EconomyEffect.shop_rewrite_forced_cost/unique 承载)。与
    基线 :func:`sample_shop_deal` 的两处分叉均为卡面明文直读,非先例
    例外:①费用档定死不掷点;②``unique=True`` 同帧去重(基线 U13
    「无去重记载不加规则」辖基线;卡面「5个独特4费角色」为 desc 自载
    的显式例外)。

    名集 = :func:`drawable_names`(商店发牌出口单一源,≥9 过滤与已
    解锁专家口径自动跟随,零透传)。unique 分支 = ``rng.sample`` 无放回
    一次抽 min(SHOP_SLOTS, len(名集)) 名(单次调用,消耗随机数序列随
    种子重放确定);非 unique 分支 = 逐槽 ``rng.choice``(现役无调用形,
    预留对称——与基线逐槽独立同构)。名集空 → 5 槽全 empty;不足 →
    填尽量多、余槽留 empty(基线空槽语义),短缺由调用方披露计数
    (短缺口径 = 事件,非缺槽数)。

    2★ 直出翻星腿与基线共享(裁决 = 环境卡面「商店中有概率出现2星角色」
    辖商店全量,强制店同为商店发牌,豁免需另立排除规则无卡面依据):
    ``ENV_SHOP_TWO_STAR_DEAL_PROB`` 命中 active_env 时,每个非空槽在
    抽名后独立掷 ``rng.random() < p``,命中升 2★(cost×3,名集语义
    不变——unique 去重以名集为界,翻星不改名)。unique 分支抽名与翻星
    掷点的相对序 = 先全量抽名再逐槽掷(单次 sample 的结构使然,与基线
    逐槽交错形不同——两函数各自种子重放确定,跨函数序列无对账约定);
    非 unique 分支与基线逐槽同序(抽名→翻星),同种子同序列可对账。

    ``refresh_probs`` = :func:`state_deal_probs` 现值真值(刷新概率显示
    面与本卡无关,维持现值;已知差异:该函数无观测概率条时逐档退基线表
    不带轮岗翻倍,与节点窗全刷的重掷形可不同——仅显示面,登记为已知
    差异)。逐名 ShopCard 构造沿基线(faction = 注册表首阵营或'散',
    star = 翻星结果,cost_source='roster',slot = 序)。
    """
    names = drawable_names(gs, cost)
    two_star_p = ENV_SHOP_TWO_STAR_DEAL_PROB.get(
        str(gs.active_env.value or ''), 0.0)
    slots: list[ShopSlot] = []
    picked = (rng.sample(names, min(SHOP_SLOTS, len(names)))
              if unique and names else [])
    for i in range(SHOP_SLOTS):
        card: ShopCard | None = None
        if i < len(picked):
            name = picked[i]
            card_cost = cost
        elif not unique and names:
            name = rng.choice(names)
            card_cost = cost
        else:
            slots.append(ShopSlot(kind='empty'))
            continue
        ch = CHARACTERS[name]
        star = 1
        if two_star_p > 0 and rng.random() < two_star_p:
            star = 2
            card_cost = cost * 3
        card = ShopCard(
            name=name, faction=(ch.factions or ('散',))[0],
            cost=card_cost, star=star, cost_source='roster', slot=i + 1)
        slots.append(ShopSlot(kind='content', card=card))
    return ShopPayload(cards=slots,
                       refresh_probs=state_deal_probs(gs, level))
