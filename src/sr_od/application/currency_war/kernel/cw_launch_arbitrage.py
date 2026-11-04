"""动作发出帧受限消费仲裁·判定核(金出口族出口 B;金出口族 DESIGN v1.1 §3.2,

**治什么**:达标分支 出战就绪(线成型)动作发出帧短路备战动作链后,
金出口在动作发出帧整族不可达——sim/实机双证成型后金逐轮净积累(终局金中位
96-196,boss 轮零动作)。本模块承载受限消费政策的**判定语义单一源**
(flow 层仲裁段已停用,消费位 = 策略决策入口自限,分层依据 =
flow/README.md §1 决策控制分层铁律):

- 数学授权 = P70 动作发出帧溢出段支配(已证,proofs/
  p70-launch-frame-overflow-spend-dominance.md:动作发出帧窗内剩余备战决策
  数 = 0 ⇒ 溢出段息损恒零 ⇒ 任一 ΔV≥0 的合法即时消费弱支配留存);
- 适用范围 = 溢出量预算 g − g* 内的 Δ息=0 帧;**花穿利息线部分不适用**(p70
  边界 1「出溢出段即失效」)——带内段(g ≤ g*)挂 L1' 独立命题,
  fail-closed 证不出不花(与 P68 同构不同号禁并键,p70 单篇「带内段
  声明」段);
- 花什么仍由 shop 出口族既有评估栈(策略器 decide_shop_action 单动作核)
  按既有资格与评估序裁决,预算闸只提供「这帧有多少零息死仓金可花」——
  不新造第二套评估语义(金出口族 DESIGN v1.1 红线 1/红线 5)。

**两面接入调用拓扑(防生产/sim 分叉三层,DESIGN v1.1 §3.2 载体)**:

1. 判定语义单一源 = 本模块(:func:`in_launch_spend_zone` 在
   ``kernel/cw_economy`` 与富余段共享 g* 链;单动作预算闸
   :func:`launch_arbitration_gate`;分键名常量 = GATE_BLOCKED_REASON/
   KEY_GATE_BLOCKS,两面直调禁字面量散写)。
2. 位次契约:动作发出帧仲裁段(flow 层特殊路径)已停用(受控决策分层
   铁律:决策闸门必须在策略侧,见 flow/README.md §1)——现役生产
   消费点 = 策略决策入口自限(flow.decide_shop_action 唯一提案产出后经
   :func:`launch_arbitration_gate` 谓词检,拒 = 决策改发 CloseShop 收
   访问);分键名常量现役 = GATE_BLOCKED_REASON/KEY_GATE_BLOCKS 两个
   (原其余 ``launch_arbitrage_*`` 分键常量已随死代码清偿移除,
   存量 cw4_counters 中的历史键名仅作历史数据判读),生产写点现役仅
   KEY_GATE_BLOCKS(策略侧受阻分键)。
   动作发出核本身零改动(生产发出调用面内部屏态复验保留
   作纵深防线)。
3. 对账基准各守拓扑:N-1 三选一裁决(**如实降格**)= 生产侧遥测载体只有
   局终快照 ``cw4_counters``,无逐轮粒度 ⇒ 生产侧「闸命中帧仲裁零消费」
   互斥读数降格为**总量弱对账**;原 sim 侧逐帧强断言(哨兵
   ``sim/checks/launch.py``,「决策段零执行 ∧ 仲裁段外零消费」)已停用拆除。

**执行皮肤不在本模块**:消费动作的执行/逻辑态直写是两面各自的循环体
(生产 = 商店画面 op 单动作循环既有守卫链;sim 与实机同一段动作 op
执行链),与
「动作发出核 launch_prepared_battle 留 operations 不动」同判据(两面差异全部
属执行/观测皮肤,判定语义恰此处一份——cw_launch_admission 同款先例)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )

#: 预算闸拒因键(单一面;调用侧计数消费,禁第二字面量)。
GATE_BLOCKED_REASON: str = 'launch_arbitrage_budget_blocked'
#: 预算闸拦截动作数(花穿利息线部分不适用的落地暴露)。
KEY_GATE_BLOCKS: str = 'launch_arbitrage_gate_blocked'


def launch_spend_cost(action) -> int:
    """动作逻辑态成本(预算闸用;零新判据,成本字段随动作类单一来源)。

    - CwActionBuyCardParam:``card.cost``(缺省 3 中费保守估,与评估栈 check_affordable
      同口径);
    - CwActionLevelUpParam:``cost`` 属性(策略器发出时写入的
      整批单击金;缺省 0 = 无成本动作不覆盖闸);
    - CwActionRefreshShopParam:``cost``(刷价现读随动作;缺省 0);
    - 其余(卖出/部署事务族):0——卖出回金不减仓,部署事务金效应
      预算闸不覆盖(闸覆盖「花」,不覆盖「换手」)。
    """
    from sr_od.application.currency_war.kernel.cw_vocab import (
        CwActionBuyCardParam,
        CwActionLevelUpParam,
        CwActionRefreshShopParam,
    )
    if isinstance(action, CwActionBuyCardParam):
        return int(getattr(getattr(action, 'card', None), 'cost', 0) or 3)
    if isinstance(action, (CwActionLevelUpParam, CwActionRefreshShopParam)):
        return int(getattr(action, 'cost', 0) or 0)
    return 0


def launch_arbitration_gate(action, gold: int,
                            session: StrategySession | None) -> tuple[bool, str]:
    """单动作预算闸(P70 Δ息=0 形:花后金位 ≥ g*;两面共用的判定核)。

    判定式:``gold − launch_spend_cost(action) ≥ saturation_line(
    cap_resolved_of_session(session))`` ——花穿利息线部分不适用(p70 边界 1),
    闸拒 = 该动作不执行(消费终止,非跳过续试:评估序 = 既有优先序,
    跳过高位动作改试低位 = 重排,违红线 5;消费机会用尽即收,方向保守)。

    g* 每次闸检现读 session resolved 链(不缓存帧首值):判定与富余段/
    R1/R2 的 g* 同源同帧语义;cap 在动作发出帧内不变(利息帽覆写只随投资卡
    变,投资卡选择不在动作发出帧发生),现读仅为单一源纪律不为缓存规避。

    返回 (放行,拒因);拒因恒 :data:`GATE_BLOCKED_REASON`(调用侧计数
    :data:`KEY_GATE_BLOCKS`)。零成本动作(sell/部署族)恒放行。
    """
    from sr_od.application.currency_war.kernel.cw_economy import (
        cap_resolved_of_session,
        saturation_line,
    )
    cost = launch_spend_cost(action)
    if cost <= 0:
        return True, ''
    if gold - cost >= saturation_line(cap_resolved_of_session(session)):
        return True, ''
    return False, GATE_BLOCKED_REASON
