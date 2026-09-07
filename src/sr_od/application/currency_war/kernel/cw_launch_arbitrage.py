"""发射帧受限消费仲裁·判定核(金出口族出口 B;金出口族 DESIGN v1.1 §3.2,
落码裁决 = ADR-0566)。

**治什么**:达标臂 armed(线成型)发射帧短路备战动作链(ADR-0557)后,
金出口在发射帧整族不可达——sim/实机双证成型后金逐轮净积累(终局金中位
96-196,boss 轮零动作)。本模块承载仲裁段的**判定语义单一源**:

- 数学授权 = P70 发射帧溢出段支配(已证,proofs/
  p70-launch-frame-overflow-spend-dominance.md:发射帧窗内剩余备战决策
  数 = 0 ⇒ 溢出段息损恒零 ⇒ 任一 ΔV≥0 的合法即时消费弱支配留存);
  **域①扩展(T-143 落码)** = math_proofs P81(S2′ 终局清算弱占优)
  ——L1' 带内命题的域①终局子域已证,豁免行三件套(带内解除/地板
  降 0/段帽处置)见 :func:`endgame_liquidation_frame` 与
  :func:`launch_arbitration_gate` 注;
- 辖域 = 溢出量预算 g − g* 内的 Δ息=0 帧;**花穿息线部分出辖**(p70
  边界 1「出溢出段即失效」)——带内段(g ≤ g*)挂 L1' 独立命题,
  fail-closed 证不出不花(与 P68 同构不同号禁并键,p70 单篇「带内段
  声明」段;域①帧除外 = P81 豁免行);
- 花什么仍由 shop 出口族既有评估栈(策略器 decide_shop_action 单动作核)
  按既有资格与评估序裁决,仲裁只提供「这帧有多少零息死仓金可花」——
  不新造第二套评估语义(金出口族 DESIGN v1.1 红线 1/红线 5)。

**两面接线拓扑(防生产/sim 分叉三层,DESIGN v1.1 §3.2 载体)**:

1. 判定语义单一源 = 本模块(:func:`in_launch_spend_zone` 在
   ``kernel/cw_economy`` 与必花域共享 g* 链;单动作预算闸
   :func:`launch_arbitration_gate`;分键名常量族);含全部
   ``launch_arbitrage_*`` 分键名,两面直调禁字面量散写。
2. 位次契约单一源 = 「armed 判定通过 ∧ 闸通过(生产为浮层在场闸 +
   ``_prep_anchors_hit`` 预检;sim 结构等价物恒真,盲区如实申报)∧
   决策段/发射核之前」——生产调用点 = ``operations/cw_loop.py``
   发射帧仲裁段(sim 同构 = ``sim/engine_p1.py`` 发射建模块立模后);
   发射核本身零改动(生产 ``readiness_battle_launch`` 内部屏态复验保留
   作纵深防线)。
3. 对账锚各守拓扑:N-1 三选一裁决(**如实降格**)= 生产侧遥测载体只有
   局终快照 ``cw4_counters``,无逐轮粒度 ⇒ 生产侧「闸命中帧仲裁零消费」
   互斥读数降格为**总量弱对账**;sim 侧逐帧强断言(哨兵
   ``sim/checks/launch.py``,「决策段零执行 ∧ 仲裁段外零消费」)。

**执行皮肤不在本模块**:消费动作的执行/投影是两面各自的循环体(生产 =
``run_buy_waves`` 单动作循环既有守卫链;sim = 引擎动作转录),与
「发射核 launch_prepared_battle 留 operations 不动」同判据(两面差异全部
属执行/观测皮肤,判定语义恰此处一份——cw_launch_admission 同款先例)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )

#: 发射帧仲裁段段数帽(sim 侧;结构常量非策略值——与生产 run_buy_waves
#: 访问段帽同构对齐:MAX_REFRESH=4 硬墙 + 1 段 = 5 段,每段以终结动作
#: (刷新)收尾后重观察。kernel 桶禁 import operations,故在此以常量 +
#: 派生注释对齐,两面漂移由本注释与 ADR-0566 对账申报辖。
LAUNCH_ARBITRAGE_SEGMENT_CAP: int = 5

#: 预算闸拒因键(单一面;调用侧计数消费,禁第二字面量)。
GATE_BLOCKED_REASON: str = 'launch_arbitrage_budget_blocked'

# ===== 域①终局清算豁免(P81;T-143 落码,方案 v2 §4 落点一)=====
# 数学授权:math_proofs P81(S2′ 终局清算弱占优)= L1' 带内命题在域①
# (终局帧)子域的证明——终局帧持金未来效用≡0(A1-A4 锚定链)且消费
# 纯金流成本≡0 ⟹ 当帧可兑现消费弱支配持金。豁免语义单一源在本模块
# (判定核先例),消费位两面接线:带内解除 = ``cw_economy.
# in_launch_spend_zone``(zone 判定单一源,两面直调);地板降 0 =
# 本模块 :func:`launch_arbitration_gate`(P70 边界 1「花穿息线出辖」
# 的域①豁免行——息线地板的保护对象(未来息流)在域①不存在)。
#: 生产本局位面数(gameplay.md「开拓者需要在 3 个位面」结构真值【注】;
#: 位面数只能作参数入场——宪法 00 §1 第 2 条形态,禁字面量散写)。
PRODUCTION_PLANE_COUNT: int = 3
#: 载体声明「本局位面数」的 session 属性名(sim 假局载体=1 由声明方
#: 写入;生产缺省不写 → 回退结构真值 3)。载体声明批(sim A/B runner)
#: 接线义务见 ADR(T-143 落码批)两面申报节。
RUN_PLANE_COUNT_ATTR: str = 'run_plane_count'

# ===== launch_arbitrage_* 分键名族(生产 cw4_counters / sim 同名写入;
# ===== 禁散写第二字面量;判读口径逐键见各写入点注释)=====
#: 仲裁段进入的发射帧数(溢出段,消费授权成立)。
KEY_ZONE_FRAMES: str = 'launch_arbitrage_frames'
#: 带内发射帧数(g ≤ g*,fail-closed 不花;显影防止「零消费」被误读为
#: 溢出帧无机会——带内是授权缺位,非机会缺位)。
KEY_INBAND_CLOSED: str = 'launch_arbitrage_inband_closed'
#: 溢出帧上零消费帧数(预算 > 0 但评估栈无合格消费机会)。
KEY_ZERO_CONSUME: str = 'launch_arbitrage_zero_consume'
#: 预算闸拦截动作数(花穿息线部分出辖的落地显影)。
KEY_GATE_BLOCKS: str = 'launch_arbitrage_gate_blocked'
#: 仲裁消费后弃射帧数(生产 defect 分键:仲裁段已消费、发射核屏态复验
#: 未过 ⇒ 走既有 stale 分支弃射;可辨识残量,从「非发射帧 digest 零变化」
#: 锚辖域显式豁免,禁静默——DESIGN v1.1 §3.2 载体)。
KEY_ABANDONED_LAUNCH: str = 'launch_arbitrage_abandoned_launch'
#: 花后跌破 g* 残量计数(后验检测:合并多买等投影外成本使实际花穿线;
#: 正常恒 0,>0 = 预算闸投影成本与执行侧真实成本存在模型差,响亮暴露)。
KEY_CROSS_LINE: str = 'launch_arbitrage_cross_line'
#: 仲裁开店失败帧数(生产;店未开成即收,不消费)。
KEY_OPEN_FAILED: str = 'launch_arbitrage_open_failed'
#: 仲裁预检未过帧数(生产;``_prep_anchors_hit`` 预检失败 = 屏态存疑,
#: 仲裁段不进入,交发射核既有 stale 分支裁定)。
KEY_PRECHECK_SKIP: str = 'launch_arbitrage_precheck_skip'
#: 域①终局清算发射帧数(落点一仲裁扩展分键;P81 豁免行接通的带内
#: 发射帧——与落点二决策臂 ``endgame_liquidation_frame`` 分键分开计数,
#: A/B 主判据①清算发射率按两落点分键分别读。写入点 = zone 判定单一源
#: ``in_launch_spend_zone`` 域①释放支,两面各恰一次/帧)。
KEY_ENDGAME_FRAMES: str = 'launch_arbitrage_endgame_frames'


def run_plane_count_of(session: StrategySession | None) -> int:
    """本局位面数(载体声明输入;方案 v2 §4 B1 修法路线 (a))。

    生产 = 缺省回退 :data:`PRODUCTION_PLANE_COUNT`(3 位面结构真值);
    sim 假局载体 = 声明方在 session 写 ``run_plane_count = 1``(位面数
    随载体喂)。**不动 ``schedule_of``**:其恒补齐 3 位面(sim P1-only
    载体判不出末位面 = B1 载体不相容),本函数与之正交,既有消费面
    零感知。位面数来自载体声明或结构真值,禁由 ``plane_lengths_seen``
    长度推断(生产 P1 帧该序列长度=1 而本局仍 3 位面,推断即域③破防)。
    """
    declared = getattr(session, RUN_PLANE_COUNT_ATTR, None)
    if isinstance(declared, int) and declared > 0:
        return int(declared)
    return PRODUCTION_PLANE_COUNT


def is_final_plane(state, session: StrategySession | None) -> bool:
    """本位面 = 本局末位面(独立判定;方案 v2 §4 B1 修法)。

    域②的「非末位面」半边同函数取反消费。plane 只作参数入场
    (宪法 00 §1 第 2 条形态),不写字面量。
    """
    plane = int(getattr(state, 'plane', 0) or 0)
    if plane <= 0:
        return False
    return plane >= run_plane_count_of(session)


def endgame_liquidation_frame(state, session: StrategySession | None) -> bool:
    """域①终局帧谓词(P81 主定理辖域;判定语义单一源)。

    = ``plane_last_battle``(位面末 boss 备战帧,单一源
    ``cw_discipline_rules``)∧ ``is_final_plane``(本位面=本局末位面)。
    决策时点可判「本帧战后对局必然终结」——清算臂(落点二)与仲裁
    豁免(落点一)共用的辖域判据;**辖域判据独立于 arm1 板满谓词**
    (三跑 N2 实证:20260958/76 发射量挂 arm1,lv5 cap 松开即停 = 48/50
    金死,``.debug/temp/currency_war/t120_sim_redesign/找问题-第三跑.md``
    §五/§六)。

    帧态不全(``round_num`` 缺 = 黑板残帧/部分桩)→ False fail-closed:
    谓词不可判域出辖,与「查询不可得 fail 向」消费位同向。
    """
    if state is None:
        return False
    if getattr(state, 'round_num', None) is None:
        return False
    try:
        from sr_od.application.currency_war.kernel.cw_discipline_rules import (
            plane_last_battle,
        )
        if not plane_last_battle(state, session):
            return False
    except AttributeError:
        return False
    return is_final_plane(state, session)


def arbitration_frame_state(session: StrategySession | None):
    """仲裁语境帧态解析(域①谓词的 state 输入;两面调用语境差异)。

    生产调用语境(session 无黑板帧)→ ``last_state`` 备战快照
    (cw_screen_prep 每备战帧写,发射帧现读);sim 引擎语境(不写
    last_state)→ ``shop_state_frame`` 黑板帧(引擎同对象逐轮原地推进,
    轮次/节点现值)。双缺 = 不可判帧(发射前无任何读)→ None,谓词
    fail-closed 判 False。
    """
    if session is None:
        return None
    st = getattr(session, 'last_state', None)
    if st is not None:
        return st
    return getattr(session, 'shop_state_frame', None)


def bump_endgame_frame(session: StrategySession | None) -> None:
    """落点一分键计数(:data:`KEY_ENDGAME_FRAMES`;best-effort 遥测,
    与两面循环体 ``_launch_arb_counter`` 同模式)。

    写入位申报:zone 判定单一源(``in_launch_spend_zone`` 域①释放支)
    是两面循环体之外唯一共用缝——生产 cw_loop / sim engine 仲裁段循环
    本体零改动(落码批文件面),分键写入随判定语义同源落位。判定核
    零写端纪律的让步已随 ADR 申报(计数 = 遥测 best-effort,容器缺席
    静默跳过,不影响判定输出)。
    """
    try:
        from sr_od.application.currency_war.kernel.cw_strategy_session import (
            strategy_state_of,
        )
        counters = getattr(strategy_state_of(session), 'cw4_counters', None)
        if isinstance(counters, dict):
            counters[KEY_ENDGAME_FRAMES] = \
                counters.get(KEY_ENDGAME_FRAMES, 0) + 1
    except Exception:   # noqa: BLE001  遥测 best-effort,不阻塞判定
        pass


def launch_spend_cost(action) -> int:
    """动作投影成本(预算闸用;零新判据,成本字段随动作类单一来源)。

    - BuyCard:``card.cost``(缺省 3 中费保守估,与评估栈 check_affordable
      同口径);
    - LevelUp 族(含 LevelUpShop):``cost`` 属性(策略器发射时写入的
      整批单击金;缺省 0 = 无成本动作不辖闸);
    - RefreshShop:``cost``(刷价现读随动作;缺省 0);
    - 其余(卖出/部署事务族):0——卖出回金不减仓,部署事务金效应
      预算闸不辖(闸辖「花」,不辖「换手」)。
    """
    from sr_od.application.currency_war.kernel.cw_state import (
        BuyCard,
        LevelUp,
        RefreshShop,
    )
    if isinstance(action, BuyCard):
        return int(getattr(getattr(action, 'card', None), 'cost', 0) or 3)
    if isinstance(action, (LevelUp, RefreshShop)):
        return int(getattr(action, 'cost', 0) or 0)
    return 0


def launch_arbitration_gate(action, gold: int,
                            session: StrategySession | None) -> tuple[bool, str]:
    """单动作预算闸(P70 Δ息=0 形:花后金位 ≥ g*;两面共用的判定核)。

    判定式:``gold − launch_spend_cost(action) ≥ saturation_line(
    cap_resolved_of_session(session))`` ——花穿息线部分出辖(p70 边界 1),
    闸拒 = 该动作不执行(消费终止,非跳过续试:评估序 = 既有优先序,
    跳过高位动作改试低位 = 重排,违红线 5;消费机会用尽即收,方向保守)。

    g* 每次闸检现读 session resolved 链(不缓存帧首值):判定与必花域/
    R1/R2 的 g* 同源同帧语义;cap 在发射帧内不变(息帽覆写只随投资卡
    变,投资卡选择不在发射帧发生),现读仅为单一源纪律不为缓存规避。

    返回 (放行, 拒因);拒因恒 :data:`GATE_BLOCKED_REASON`(调用侧计数
    :data:`KEY_GATE_BLOCKS`)。零成本动作(sell/部署族)恒放行。

    **域①终局豁免行(P70 边界 1 的域①豁免;P81 已证)**:域①帧上
    息线地板的保护对象(未来息流)不存在,地板降 0——花后金位 ≥0 即
    放行(清算终止由金尽承载,方案 v2 §4 豁免语义单一源)。非域①帧
    逐字走既有 g* 地板(零漂移)。
    """
    from sr_od.application.currency_war.kernel.cw_economy import (
        cap_resolved_of_session,
        saturation_line,
    )
    cost = launch_spend_cost(action)
    if cost <= 0:
        return True, ''
    _st = arbitration_frame_state(session)
    if _st is not None and endgame_liquidation_frame(_st, session):
        return (gold - cost >= 0, '')
    if gold - cost >= saturation_line(cap_resolved_of_session(session)):
        return True, ''
    return False, GATE_BLOCKED_REASON
