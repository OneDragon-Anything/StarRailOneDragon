"""货币战争动作上报:刷新商店(report_action_refresh_shop_param)。

刷新动作上报三腿(2026-09-21 商店刷新迭代 design §2-6/§2-9):

- **计数腿**:付费/全量两计数经 ``gs.effects.record_refresh`` 单口触发
  (2026-09-18 迁入裁决;免费余额半随 Field 化迁出,账本只留 paid/total
  累计)。生产 = 刷新 op 自上报,sim = 委托串直调,落地门零重复触发。
- **免费腿扣减**:免费刷新剩余次数住容器字段 ``gs.free_refresh_left``
  (Field 化:观察锚定/动作扣减/发放登记三写端同格),免费帧经
  ``write_logic`` 扣减。free 判定 = Field 值 > 0;None(未观察)= 保守
  按 paid(不扣 Field——次数是记账面非决策闸,商店刷新允许性归策略面)。
- **随机态腿**:计数后经 kernel 发牌采样器(:mod:`cw_shop_deal`,与 sim
  ``deal_shop`` 同源,纯采样不写容器)采 5 槽 payload,经
  ``write_logic_rand`` 随机态专用通道写商店载荷——实机上采样是猜测,
  sim 里采样即世界真值(同一上报函数两副面孔);observe 覆盖差异落
  ``logic_rand_outcome`` 台账、不进失配安灯(通道语义自带)。level 缺读
  = 该腿跳写(概率表按级索引,宁缺勿造)。干旱/供给族消费 observation
  only 是消费侧口径,本函数不管。

金账 −实付仅 sim 喂 ``executed.refresh_paid`` 时写(生产不喂)。
终结跳写申报:金仍不写;刷后牌面 = ``write_logic_rand`` 随机态
(2026-09-21 用户裁定,观察赢;真值 = 下一入口观察)。

动作上报函数族拆分件(每动作一文件;族规约与解析入口 = 包
``cw_action_report.__init__`` docstring)。容器、写入口与观察
写端留守 ``kernel/cw_game_state``,本包 → 容器单向依赖。
"""

from __future__ import annotations

import random
from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    LogicOutcome,
    ShopActionExecuted,
    _validate_sig,
)
from sr_od.application.currency_war.kernel.cw_shop_deal import sample_shop_deal

_PRODUCER = 'CwActionRefreshShopParam'


def report_action_refresh_shop_param(gs: GameState, param: Any, sig: ChannelSig,
                                     executed: ShopActionExecuted | None = None,
                                     free: bool | None = None,
                                     rng: random.Random | None = None) -> LogicOutcome:
    """刷新商店上报 = 计数触发 + Field 免费腿扣减 + 商店牌随机态采样。

    - 计数(``gs.effects.record_refresh`` 单口):refresh_total 恒 +1;
      free=True 不进 paid(付费累计,长线利好阈值型,免费帧混入即毒化);
      free=False refresh_paid +1;同帧 bump 按策略触发计数
      (CounterKey.REFRESH,采购专员族门槛面)。
    - free 判定输入 = 显式 ``free`` 优先(sim 免费刷额度先行自喂),None
      回退 Field 值判定(``gs.free_refresh_left.value > 0``;入口观察锚定
      的剩余次数;None = 未观察 → 保守按 paid,不扣 Field)。
    - 免费腿扣减 = ``write_logic(gs.free_refresh_left, max(0, left−1))``
      (produced_by/evidence 留证;下限 0,禁负值漂移)。
    - 随机态腿 = kernel 采样器采 payload → ``write_logic_rand(gs.shop, …)``
      (evidence='refresh_random_sample';观察覆盖差异 = logic_rand_outcome
      台账,非失配)。
    - 金账:仅 ``executed.refresh_paid`` 在场时写(−实付;免费帧 0 不写)
      ——生产 op 不喂,sim 引擎显式喂(实付金含免费刷注入等引擎差异,不可
      自算)。``applied`` 恒 True:计数即职责完成,调用方仅在动作实际发出
      后进本口(未落地不计数)。
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
    if free_determined:
        # 免费腿 Field 扣减(剩余语义,下限 0;None 基按 0 起算——
        # 显式 free=True 而 Field 未观察的形态只出现在注入测试)
        gs.write_logic(gs.free_refresh_left,
                       max(0, (0 if _left is None else int(_left)) - 1),
                       produced_by=_PRODUCER, evidence='proj_refresh_free_left',
                       sig=_grp_sig)

    # 随机态腿:计数后采样商店牌 5 槽 payload(与 sim 发牌同源),经
    # write_logic_rand 写随机态。level 缺读跳写(概率表按级索引)。
    _level = gs.level.value
    if _level is not None:
        roll_rng = rng if rng is not None else random.Random()
        payload = sample_shop_deal(gs, roll_rng, level=int(_level))
        gs.write_logic_rand(gs.shop, payload, produced_by=_PRODUCER,
                            evidence='refresh_random_sample', sig=_grp_sig)

    paid = executed.refresh_paid if executed is not None else None
    if paid is not None:
        paid = max(0, int(paid))
        if paid > 0:
            g = gs.gold.value
            if g is not None:
                gs.write_logic(gs.gold, int(g) - paid,
                               produced_by=_PRODUCER,
                               evidence='proj_refresh_gold', sig=_grp_sig)
    return LogicOutcome(applied=True)
