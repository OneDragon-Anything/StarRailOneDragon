"""货币战争动作上报:刷新商店(report_action_refresh_shop_param)。

刷新动作上报分支(2026-09-21 商店刷新迭代 design §2-6/§2-9 立骨架,后续
分支随各效果建模批增补;条目序 = 建模序,执行序见函数 docstring):

- **计数分支**:付费/全量两计数经 ``gs.effects.record_refresh`` 单口触发
  (2026-09-18 裁定;免费余额在容器字段,账本只留 paid/total
  累计)。生产 = 刷新 op 自上报,sim 与生产同一段 op 代码同口自上报,落地门
  零重复触发。
- **免费分支扣减**:免费刷新剩余次数住容器字段 ``gs.free_refresh_left``
  (Field 化:观察锚定/动作扣减/发放登记三写端同格),免费帧经
  ``write_logic`` 扣减。free 判定 = Field 值 > 0;None(未观察)= 保守
  按 paid(不扣 Field——次数是记账面非决策闸,商店刷新允许性归策略面)。
- **付费刷新 XP 分支**(策略源 xp_per_refresh;仅付费帧):效果账本
  条目经鸭子类型读取(duck typing)聚合 ``payload.xp_per_refresh``
  (零卡名硬编码,后继同字段卡自动覆盖)→ ``grant_effect_refresh_xp``
  字段写操作写入经验推进对(evidence ``effect_refresh_xp``;世界腿 =
  把结果写进状态副本的实现分支)——淘金客卡面「你每次消耗金币刷新商店,
  都会获得2经验值。」。插入位置 = 免费扣减分支后、随机态分支前:
  同帧跨级后本帧发牌采样即用升级后 level(店决策按 level 读数,刷新得
  XP 立即可见);免费帧零 XP(「消耗金币」文本排免费刷)。
- **随机态分支**:计数后经 kernel 发牌采样器(:mod:`cw_shop_deal`,与 sim
  ``deal_shop`` 同源,纯采样不写容器)采 5 槽 payload,经
  ``write_logic_rand`` 随机态专用通道写商店载荷——实机上采样是猜测,
  sim 里采样即世界真值(同一上报函数两副面孔);采样表 =
  ``state_deal_probs``(轮岗感知;观测概率条真值直用,缺读逐档退基线);
  observe 覆盖差异落 ``logic_rand_outcome`` 台账、不进失配告警(通道语义
  自带)。level 缺读 = 该分支跳写(概率表按级索引,宁缺勿造)。干旱/供给族消费 observation
  only 是消费侧口径,本函数不管。
- **环境条件发放分支**(ENV_REFRESH_GRANTS 在册环境:二手市场全量域 /
  长线利好付费域):尾部触发检查
  (``check_env_refresh_grants``;登记表 =
  ``cw_investments.ENV_REFRESH_GRANTS``;发放 = 金/装备/done 三笔
  同窗)——世界发放域,不属计数/采样语义;sim 与生产同段 op 代码
  同口,单点覆盖双端。

- **策略出对条件金分支**(策略源 ON_REFRESH 经济发放首接线):随机态
  腿之后、仅 sim 装配态执行(``apply_on_refresh_pair_gold_grant``,
  登记面 = ``cw_investments.STRATEGY_EFFECTS`` ON_REFRESH∧ECONOMY 条目
  双过滤,判定 = 本次采样 payload 出同名对;发放 = 观察通道发金)——
  sim 采样即世界真值,判定输入可直接消费;live 采样是猜测,金面禁
  猜测直写(live 零写,金真值 = 下一商店入口观察覆盖;``cw_env_grants
  .on_diamond_acquired`` 同口径)。burst 免费刷腿走获得链登记腿,不经
  本分支。

- **金账扣费分支**(2026-10-16 用户裁决,推翻 2026-09-21「金仍不写、
  以实际观察为准」旧裁定):费用单一源 = ``gs.shop_refresh_cost``
  容器直读(``value or REFRESH_COST_BASE``;live 商店开态观察漏斗
  OCR / sim 开店呈现写同一字段),上报即按当次价扣金,与买牌/升级/
  卖牌同款双端逻辑态;免费帧费用清零(free 判定单一源 =
  ``gs.free_refresh_left``,推导见计数分支)。金现值缺读(None)跳写。
  容器价与实扣不符(失读帧撞刷新)由下一入口金观察失配检出,处置 =
  停机语义(cw_mismatch_policy 现行失配架构,本写端不豁免)。
  终结跳写申报仅余刷后牌面 = ``write_logic_rand`` 随机态
  (2026-09-21 用户裁定,以实际观察为准;真值 = 下一入口观察)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留在 ``kernel/cw_game_state``;依赖方向 = 本包 → 容器单向 +
本文件对 ``sim.cw_sim_ports`` 的装配判据单向腿(判据口零 kernel
import,依赖无环结构自证;kernel → sim.ports 判据消费首例,发放
函数本体仍住 kernel 包内零跨包)。
"""

from __future__ import annotations

import random
from typing import Any

from sr_od.application.currency_war.kernel.cw_economy import (
    REFRESH_COST_BASE,
)
from sr_od.application.currency_war.kernel.cw_env_grants import (
    check_env_refresh_grants,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    LogicOutcome,
    ShopActionExecuted,
    _validate_sig,
    grant_effect_refresh_xp,
    mark_gold_spent,
)
from sr_od.application.currency_war.kernel.cw_shop_deal import (
    sample_shop_deal,
    state_deal_probs,
)

_PRODUCER = 'CwActionRefreshShopParam'


def report_action_refresh_shop_param(gs: GameState, param: Any, sig: ChannelSig,
                                     executed: ShopActionExecuted | None = None,
                                     free: bool | None = None,
                                     rng: random.Random | None = None) -> LogicOutcome:
    """刷新商店上报 = 计数触发 + Field 免费分支扣减 + 商店牌随机态采样。

    - 计数(``gs.effects.record_refresh`` 单口):refresh_total 恒 +1;
      free=True 不进 paid(付费累计,长线利好阈值型,免费帧混入即毒化);
      free=False refresh_paid +1;同帧 bump 按策略触发计数
      (CounterKey.REFRESH,采购专员族门槛面)。
    - free 判定输入 = 显式 ``free`` 优先(喂入口保留,现役调用方恒 None),None
      回退 Field 值判定(``gs.free_refresh_left.value > 0``;入口观察锚定
      的剩余次数;None = 未观察 → 保守按 paid,不扣 Field)。
    - 免费分支扣减 = ``write_logic(gs.free_refresh_left, max(0, left−1))``
      (produced_by/evidence 留存证据;下限 0,禁负值漂移)。
    - 付费刷新 XP 分支 = ``grant_effect_refresh_xp(gs, 组签名)``(仅付费帧,
      执行序在免费扣减后、随机态分支前):效果账本条目鸭子类型读取
      ``payload.xp_per_refresh`` 聚合经 ``grant_xp`` 字段写推进对
      (evidence 'effect_refresh_xp';世界腿 = 把结果写进状态副本的实现
      分支,淘金客卡面「每次消耗金币刷新商店,都会获得2经验值」;None 门/
      满级跳写在原语内;免费帧零 XP,同帧跨级后本帧发牌采样即用升级后
      level)。
    - 随机态分支 = kernel 采样器采 payload → ``write_logic_rand(gs.shop, …)``
      (evidence='refresh_random_sample';观察覆盖差异 = logic_rand_outcome
      台账,非失配);策略出对条件金腿在同一分支块内、采样之后(见模块头,
      仅 sim 装配态执行)。
    - 金账扣费:费用单一源 = 容器直读 ``gs.shop_refresh_cost.value or
      REFRESH_COST_BASE``(商店画面观察写入——live 开态漏斗 OCR / sim
      开店呈现,同一字段同一写法),非免费帧按当次价扣金;与 op 花销账
      同式同源(同一动作瞬间容器未变)→ 花销账累加值 ≡ 金账扣减值,
      构造性一致。免费帧费用清零(集中在本函数执行)。``applied`` 恒 True:
      计数即职责完成,调用方仅在动作实际发出后进本口(未落地不计数)。
    """
    _validate_sig(sig, ('logic_action',))
    from dataclasses import replace as _dc_replace

    _grp_sig = (sig if sig.group_id is not None else _dc_replace(
        sig, group_id=f'act:{sig.actor}@{gs.write_seq + 1}'))

    inv = gs.effects
    _left = gs.free_refresh_left.value
    if free is not None:
        free_determined = bool(free)
    else:
        free_determined = _left is not None and int(_left) > 0
    inv.record_refresh(free=free_determined)
    if not free_determined:
        # 金币花费事件置位(存款回报条件输入,fields.md §3.3.9):非免费帧
        # = 花费事件,与账本 refresh_paid +1 同条件同口径——「未观察保守按
        # 付费」的保守性一并继承;免费帧不置位。
        mark_gold_spent(gs, produced_by=_PRODUCER, sig=_grp_sig)
    if free_determined:
        # 免费分支 Field 扣减(剩余语义,下限 0;None 基按 0 起算——
        # 显式 free=True 而 Field 未观察的形态只出现在注入测试)
        gs.write_logic(gs.free_refresh_left,
                       max(0, (0 if _left is None else int(_left)) - 1),
                       produced_by=_PRODUCER, evidence='proj_refresh_free_left',
                       sig=_grp_sig)

    if not free_determined:
        # 付费刷新 XP 分支(策略源 xp_per_refresh,世界腿 = 把结果写进
        # 状态副本的实现分支;淘金客卡面「你每次消耗金币刷新商店,都会
        # 获得2经验值。」):效果账本条目鸭子类型读取 xp_per_refresh 聚合
        # 经 grant_effect_refresh_xp 字段写(零卡名硬编码,None 门/满级
        # 跳写在 grant_xp 原语内;免费帧零 XP——「消耗金币」文本排免费刷,
        # 与计数分支 refresh_paid 同付费域口径)。插入位置在随机态分支前:
        # 同帧跨级后本帧发牌采样即用升级后 level(店决策按 level 读数,
        # 刷新得 XP 立即可见)。
        grant_effect_refresh_xp(gs, _grp_sig)

    # 随机态分支:计数后采样商店牌 5 槽 payload(与 sim 发牌同源),经
    # write_logic_rand 写随机态。level 缺读跳写(概率表按级索引)。
    _level = gs.level.value
    if _level is not None:
        from sr_od.application.currency_war.kernel.cw_action_report import (
            action_sampling_rng,
        )
        roll_rng = action_sampling_rng('refresh_shop', rng)
        payload = sample_shop_deal(gs, roll_rng, level=int(_level),
                                   probs=state_deal_probs(gs, int(_level)))
        gs.write_logic_rand(gs.shop, payload, produced_by=_PRODUCER,
                            evidence='refresh_random_sample', sig=_grp_sig)

        # 策略出对条件金腿(随机态腿后、payload 在手):仅 sim 装配态执行
        # ——sim 采样即世界真值,判定成立经观察通道发金;live 采样是猜测,
        # 金面禁猜测直写(live 零写,真值 = 下一商店入口观察覆盖)。
        # kernel → sim.ports 为 kernel 包判据消费首例(判据口零 kernel
        # import,无环结构自证);发放函数本体住 kernel 包内,惰性 import
        # 同文末诸桥纪律。挂点禁移函数尾:函数尾拿不到 payload 变量,误挂
        # 会转向读商店旧值或猜测值(两皆违设计)。level 缺读帧采样腿跳写,
        # 本腿同帧零发放(概率表按级索引,宁缺勿造同向)。
        from sr_od.application.currency_war.sim import cw_sim_ports
        if cw_sim_ports.sim_backend_installed():
            from sr_od.application.currency_war.kernel.cw_effect_inventory import (
                apply_on_refresh_pair_gold_grant,
            )
            apply_on_refresh_pair_gold_grant(gs, payload, frame='refresh')

    # 金账扣费分支:容器直读当次刷价(免费帧清零收归本函数集中执行;
    # free 判定单一源 = free_refresh_left 字段,与免费分支同一推导)。
    # 与 op 花销账同式同读、同一动作瞬间容器未被本动作改写 → 值恒等;
    # gold 未观察(None)跳写。回退基价自 cw_economy import(对本模块
    # 无环——cw_economy 不依赖本包)。
    fee = 0 if free_determined else (gs.shop_refresh_cost.value
                                     or REFRESH_COST_BASE)
    if fee > 0:
        g = gs.gold.value
        if g is not None:
            gs.write_logic(gs.gold, int(g) - fee,
                           produced_by=_PRODUCER,
                           evidence='proj_refresh_gold', sig=_grp_sig)

    # 环境条件发放分支:第 N 次刷新动作窗内尾部触发检查(计数分支已先入账,
    # 此处计数现值含本刷;世界发放域,见模块头与本函数 docstring)。
    check_env_refresh_grants(gs, _grp_sig)
    return LogicOutcome(applied=True)
