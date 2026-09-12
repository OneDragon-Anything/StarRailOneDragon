"""cw4 决策入口(entry 三遍编排 + 帧稳定截断发射器)。

换核批 1 结构签名(R189-4;迁移序原文已删档,取回口径=ADR-0644):

    def _emit(turn) -> list[PrepAction]:
        actions += self._mandate_pass(turn)    # 骨架动作流,逐条 mandate=True
        actions += self._criteria_pass(turn)   # EV 追加动作流,mandate=False
        return truncate_frame_stable(actions)  # 帧稳定截断(契约 v2 §3.2)

三遍编排(02_mandate_layer §3 骨架执行序):证明 pass → 升档器求值位 → 骨架 pass → EV pass。
ev_arm 模式参数(skeleton_only/full,R1-1)决定 EV 发射面旁路集
(criteria/__init__.py BYPASS_TABLE 单一源)
并写遥测行(bridge 侧)。

truncate_frame_stable 判 = 契约 v2 §3.2 备战线域 18 类逐类表(词表
as-built 权威 = docs/develop/sr_od/application/currency_war/flow/action_exec.md §1——
契约正本 CONTRACT_SERIES_DECISION.md 工作副本灭失(全仓零命中,
.debug 不入 git),§1 即该词表行的首次文档落档,权威链重锚申报 =
ADR-0585 §5 + flow/action_exec.md §1 正本)+ §3.3 fail-closed(词表外/无分类
动作 ⇒ 截断 + 计数披露,禁静默丢弃)。发射器实现期增补条目须回契约
改版,禁只改代码。R196 修复批(症5)对齐:ClickSpheres=条件判(末批
可能掉箱 ⇒ 其后截断)、conditional 五类名-槽一致性复检(推不出即截断,
计数 ``emitter_conditional_truncated``)、BailToOuter=退役·终点(判型
标签对齐契约 §3.2 行,发射行为等价)。

R197 修复批(症1)发射序规格:同一 decide 输出内,EV 卖面
(line_switch_sell/funding_support)与骨架动作按**依赖拓扑**重排——
EV 卖面全部系 bench 域操作(画面零迁移,契约 §2 可续),而骨架的开店
意图(OpenShop)系截断点;EV 卖面插到首个截断点/终点动作**之前**
(``_merge_ev_before_frame_end``),否则换线生效帧(M2 对新线缺口发
OpenShop 的典型帧)的塌缩出口发射会落在截断点之后被静默丢弃
(IMPL_ADV_R197 症1;「EV 只追加」的义务先行语义=02_mandate_layer §2/§7
权限划界,其追加面=发射
组织面,执行序按依赖拓扑承载)。截断器丢弃尾动作一律计数
``emitter_post_truncation_dropped``(零静默披露;键写点=本模块计数器,
登记节原文已删档,取回口径=ADR-0644)。

R197 修复批(症2)影子面声明:A/B 期换线权威 = decision_v2 意向状态机
(方向重估经 flow 层方向刷新,ADR-0583 内化,两臂同源恒等);本模块
``switch.event`` 只登记
回锁窗遥测与 switchline_event 计数,**不写 target_comp**——cw4 的
should_switch/回锁窗/干旱计数全部为影子面(实装接线=过线后批)。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    bench_slots_of,
    board_state_of,
    deployed_slots_of,
    gold_of,
    level_of,
    max_units_of,
    node_kind_of,
    plane_of,
    round_num_of,
)
from sr_od.application.currency_war.kernel.cw_comps import get_comp
from sr_od.application.currency_war.kernel.cw_economy import (
    blood_xp_gate_for,
    in_must_spend_zone,
)
from sr_od.application.currency_war.kernel.cw_hp_policy import decision_hp
from sr_od.application.currency_war.kernel.cw_intention import (
    locked_buy_cap_hold,
)
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    BailToOuter,
    ClickSpheres,
    DeferSpheres,
    DeployMove,
    EnsureShopClosed,
    EnsureShopOpen,
    LevelUp,
    OpenBox,
    OpenShop,
    OpenTome,
    PickBoxCard,
    PrepAction,
    RunBuyPhase,
    RunDeploy,
    RunEquip,
    RunTools,
    SellBench,
    SellDeployed,
    StartBattle,
)
from sr_od.application.currency_war.kernel.cw_reward_node import (
    reward_node_suppressed,
)
from sr_od.application.currency_war.kernel.cw_exec_state import BENCH_CAPACITY
from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
    mandate,
    proof,
    sell_gate,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import contracts
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
    levelup as crit_levelup,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
    sell as crit_sell,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import predicates

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_prep_actions import (
        PrepObservation,
    )
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        Emitted,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.turn_state import (
        TurnState,
    )

#: ev_arm 值域(R1-1:skeleton_only=臂① EV 发射面旁路;full=臂② 全开)
EV_ARM_VALUES: tuple[str, ...] = ('skeleton_only', 'full')

#: 球内容占席颜色集(迁移 B 球谓词第二腿的判定输入;ADR-0596 §4.9③)。
#: CV 颜色域 = {'gold','blue','gray'}(cw_identity_obs 圆心 HSV 分类),
#: 但「颜色 → 内容是否占席」的玩法机制面待实机实证——现役缺省 = 空集
#(球均按不占席,宁多收球不误卖:点击失败可自愈、SellBench 不可逆,
#: 与 adapter.snapshot_to_obs 对 free_bench_slots None→BENCH_CAPACITY
#: 的在库裁决同向;占席球面的损失面由 2026-09-02 席满球裁定
#: screen_flow_timing #16「部分没点开自然回补」容忍语义承载)。实证
#: 落地后在此登记占席颜色,谓词第二腿自动收紧(腾席先于点球)。
SPHERE_OCCUPYING_COLORS: frozenset[str] = frozenset()


def _sphere_bench_free(obs: PrepObservation) -> int:
    """席自由槽读数(球谓词第一腿输入;缺省方向 = adapter.py 在库裁决
    对齐:free_bench_slots None/缺读 → BENCH_CAPACITY,宁多收球不误卖,
    非 0 值按物理现读)。"""
    _free = getattr(obs, 'free_bench_slots', None)
    return BENCH_CAPACITY if _free is None else max(0, int(_free))


#: 席满让路门探针预算 K(预注册 = 1;ADR-0642;T-281 方案稿 §3.3 夹逼,
#: 非自由调参):上界 K≤2 源于无进展守卫阈值 3 的竞速约束
#(守卫 tick 读 last_prep_action_sig 在备战 op 返回后,第 4 环决策先于
#: 该环 tick——K≥3 时让路环恰逢守卫触发环,让路只剩单环机会);下界
#: K≥1 = 保留单次探针区分「机制性拒绝」vs「单帧偶发落空」,并对
#: 「席满全阻断」建档注释假设保留最小实证敞口(色→内容映射未证,
#: ADR-0596 §4.9③);K=2 无信息增益仅多 1 环延迟。零新拍定值:由
#: 守卫常量与在册机制假设夹逼出可行域后取 1。
SPHERE_DEFER_PROBE_K: int = 1

#: 单批点球上界(收编自旧 decision 核的发射形态值,统一迁移批随
#: entry.py 入 mandate_v1;判读底稿低危项3补三形态归属标注):
#: **归属 = 框架流程防线常量,非三形态决策值**(同 WANTED_REOPEN_CAP
#: 豁免类——它上界化单帧发射的点击预算,不作任何做/不做闸门)。
#: 机制依据 = 席满时球点不动(docs/game/screens/currency_war_prep.md
#: 奖励球节):每球内容可能占席,批式连点越过自由席位数即空点,批间由
#: 球计数自然回补(screen_flow_timing #16「部分没点开自然回补」用户
#: 裁定容忍语义)。层位关系:执行层硬帽 = prep_actions.
#: PrepActionExecutor.SPHERE_MAX_CLICKS=12(防识别抖动死循环,不互替);
#: kernel ``ClickSpheres.max_k`` 缺省 1 = 保守缺省,本发射位显式覆写
#: 为本常量(单一源,禁再内联字面 3)。
SPHERE_CLICK_BATCH_MAX_K: int = 3


def _sphere_progress_sig(bs: GameState,
                         obs: PrepObservation) -> int:
    """席满让路门成效计数签名((轮次, 席计数, 球计数) 压缩整型;ADR-0642)。

    载体 = 容器 bs(prep 链容器化段 1:签名切 bs)。轮次经
    ``round_num_of`` 读口——未观察帧缺省 1 镜像旧「state is None → 1」
    分支(波 1 读口等价契约,单一源 = 读口 docstring),分支退役零行为差。
    三分量全部 bs/obs 现成字段,零新识别;压缩进 int 保持 cw4_counters
    数值账本面(sim 轮差分对逐值做 int() 算术,sim/engine_p1.py,禁存
    tuple/str)。装箱域:席/球计数各 4 bit,>15 回绕 = 误判「有成效」
    → 多一环探针点击,良性偏置。噪声口径:刻意不采 raw gold(OCR 噪声
    会误复位使门失效,ADR-0554 修订节 5 同源教训);球计数经 Hough 检出
    存在抖动,每次误变只多一环探针,无进展守卫(阈值 3)仍兜底。
    """
    _round = round_num_of(bs)
    _bench_n = len(getattr(obs, 'bench_chars', None) or ())
    _sphere_n = len(getattr(obs, 'spheres', None) or ())
    return ((_round * 16) + (_bench_n & 0xF)) * 16 + (_sphere_n & 0xF)

log = logging.getLogger(__name__)

# ===== 帧稳定截断分类(契约 v2 §3.2 备战线域逐类)=====

#: 截断点(该动作可作序列最后一个动作发出,其后截断)
_TRUNCATION_POINTS: tuple[type, ...] = (
    OpenBox, OpenTome, PickBoxCard, OpenShop,
    EnsureShopOpen, EnsureShopClosed,      # 退役类兼容面保守判=截断点
    RunBuyPhase,                           # 退役类兼容面保守判=截断点
)
#: 终点(只能作序列最后一个动作;StartBattle=出战环出口;BailToOuter=
#: 退役·终点——中止本环交外环按序列终点语义,契约 §3.2 行,R196 症5 标签对齐)
_TERMINAL: tuple[type, ...] = (StartBattle, BailToOuter)
#: 可续(画面零迁移/坐标不变)
_CONTINUE: tuple[type, ...] = (LevelUp, DeferSpheres)
#: 条件续(bench 索引结构恒稳+名-槽一致性复检;board 空位/星级合成按
#: 前序动作累积静态推出,推不出即截断——契约 §3.2 五行+ClickSpheres 行;
#: 组合动作类(SellDeployed/RunDeploy/RunEquip)按发射期计划静态推出成立
#: [ADR-0316],复检不适用,经 _CONDITIONAL fallthrough 达成同效——
#: R197 症8:独立死常量 _CONDITIONAL_COMPOSITE 已删,分类语义不变)
_CONDITIONAL: tuple[type, ...] = (
    SellBench, SellDeployed, DeployMove, RunDeploy, RunEquip,
    RunTools,                             # 组合类(ADR-0532 工具执行批):同组合语义
    ClickSpheres,                          # 条件:常态可续;末批可能掉箱后截断
)


def classify_frame_stability(action: PrepAction) -> str:
    """单动作帧稳定分类(契约 v2 §3.2 逐类判的机器可读形式)。

    返回:'continue' / 'conditional' / 'truncation' / 'terminal' /
    'unknown'(词表外/无分类 ⇒ §3.3 fail-closed)。
    """
    for t in _TERMINAL:
        if isinstance(action, t):
            return 'terminal'
    for t in _TRUNCATION_POINTS:
        if isinstance(action, t):
            return 'truncation'
    for t in _CONDITIONAL:
        if isinstance(action, t):
            return 'conditional'
    for t in _CONTINUE:
        if isinstance(action, t):
            return 'continue'
    return 'unknown'


def truncate_frame_stable(actions: list[PrepAction],
                          session: StrategySession | None = None,
                          *, bench_slots: set[int] | None = None,
                          ) -> list[PrepAction]:
    """帧稳定截断发射器(契约 §2 帧稳定域 + §3 分域枚举 + §3.3)。

    逐动作判「本动作执行后的画面状态能否静态推出」:可续/条件续 →
    继续发射;截断点 → 该动作作为序列最后一个动作发出;终点 → 序列
    终点(其后必须截断);unknown(词表外/无分类)→ fail-closed 截断
    + 计数披露(``emitter_unknown_action_truncated``;键登记单一源=
    本写点,原 design_telemetry 键节已删档、取回口径=ADR-0644——
    契约禁成遥测键第二登记源)。

    conditional 类的复检(R196 症5,契约 §3.2 依据列「名-槽一致性复检/
    前序累积静态推出,推不出即截断」):

    - ``SellBench``/``DeployMove``:bench 槽位引用对 ``bench_slots``
      (生成期观察的占用槽位集)复检 + 前序同序列卖出/拖出累积投影
      (槽位卖出后从投影集移除)——引用空槽/未知槽 ⇒ 推不出 ⇒ 该动作
      处截断 + ``emitter_conditional_truncated`` 计数。``bench_slots``
      缺省 None = 复检语境缺失,按条件成立续发(发射器自身产序列时
      引用即生成期观察,生产路径 bridge 总是供给语境)。
    - ``ClickSpheres``:末批判——同序列其后还有 ClickSpheres 批次 ⇒
      非末批,常态分支可续;本批为序列内最后一批 ClickSpheres(可能
      掉箱,掉箱弹 overlay 不可静态预测)⇒ 其后截断(契约 §3.2
      ClickSpheres 行;末批截断系判型内语义,非失败,不计
      ``emitter_conditional_truncated``)。
    - 组合类(SellDeployed/RunDeploy/RunEquip):内部成员按部署/装备
      计划静态推出,发射器序列内成立(ADR-0316)⇒ 可续。

    尾动作丢弃计数(R197 症1②):任一截断路径(词表外/复检失败/截断点/
    终点/ClickSpheres 末批)丢弃的后续动作逐个计数
    ``emitter_post_truncation_dropped``——截断本身系契约语义(非失败),
    但「丢弃了什么」必须可观测,禁零计数静默(EV 发射被截断丢弃时
    遥测可辨「评估了不发射」vs「发射被丢弃」)。
    """
    counters: dict | None = None
    if session is not None:
        got = getattr(state_of(session), 'cw4_counters', None)
        if isinstance(got, dict):
            counters = got

    def _count(key: str, n: int = 1) -> None:
        if counters is not None:
            counters[key] = counters.get(key, 0) + n

    out: list[PrepAction] = []
    slots: set[int] | None = set(bench_slots) if bench_slots is not None else None

    def _cut() -> list[PrepAction]:
        # 截断收口:丢弃尾动作逐个计数(零静默披露,R197 症1②)
        _count('emitter_post_truncation_dropped', len(actions) - len(out))
        return out

    for i, a in enumerate(actions):
        kind = classify_frame_stability(a)
        if kind == 'unknown':
            _count('emitter_unknown_action_truncated')
            return _cut()       # 词表外:该动作处截断(不猜测分类)
        if kind == 'conditional':
            if isinstance(a, ClickSpheres):
                has_later_batch = any(
                    isinstance(a2, ClickSpheres) for a2 in actions[i + 1:])
                out.append(a)
                if not has_later_batch:
                    return _cut()  # 末批可能掉箱 ⇒ 其后截断(判型内语义)
                continue
            if isinstance(a, SellBench):
                if slots is not None and a.slot not in slots:
                    _count('emitter_conditional_truncated')
                    return _cut()  # 名-槽一致性复检失败:推不出即截断
                out.append(a)
                if slots is not None:
                    slots.discard(a.slot)
                continue
            if isinstance(a, DeployMove):
                if slots is not None and a.from_slot not in slots:
                    _count('emitter_conditional_truncated')
                    return _cut()
                out.append(a)
                if slots is not None:
                    slots.discard(a.from_slot)
                continue
            # 组合类(SellDeployed/RunDeploy/RunEquip):按计划静态推出成立
            out.append(a)
            continue
        out.append(a)
        if kind in ('truncation', 'terminal'):
            return _cut()
    return out


# ===== 三遍编排 =====

@dataclass
class UpgraderSignals:
    """升档器求值位输出(R27-1②:证明 pass 后、骨架 pass 前每备战期
    现读;信号位必须先于 F7/M3 消费位产出)。

    标定落地(用户裁定=按 15,撤销 R29-1/R36-2 None 期影子维持声明):
    血线阈值单一源 = lambda_death.HP_BAND_NEAR_DEATH(=15,
    BLOODLINE_HP_THRESHOLD provisional 源退役);hp≤阈值 ⇒ 解锁包三件
    (F7 禁令/M3 分流/arm2 门)武装,行为介入开启。λ 顾问:标定前置
    影子维持声明同批撤销——p 注入形态触发即真键武装(行为介入),
    ``lambda_shadow``/``bloodline_shadow`` 影子键保留为对照(同条件
    置位,禁删)。

    R196 症3 载体:``lambda_armed``(真键 ``advisor_lambda_armed``)/
    ``lambda_shadow``(对照键)。
    """

    f7_ban_armed: bool = False
    neardeath_unlock: bool = False
    arm2_gate_open: bool = False
    lambda_shadow_armed: bool = False
    lambda_armed: bool = False
    bloodline_shadow_armed: bool = False


def _lambda_quantile_armed(bs: GameState, hp: int | None,
                           p_value: float) -> bool | None:
    """λ 顾问相对分位触发谓词(R28-1;R196 症3 影子/真键共用求值体)。

    载体 = 容器 bs(prep 链容器化段 1:签名切 bs)。域读:node 经
    ``node_kind_of`` 读口(None=未识别镜像旧 getattr 缺省 '')/
    difficulty 直读容器值(None=未读透传,λ 键 None 域语义不变)/plane
    经 ``plane_of`` 读口(缺省 1 镜像)。旧「state is None → 不评估」
    前置分支退役——生产不可达(heavy 观察恒产出视图帧,light 兼容
    形态现生产无调用方),分支退役与引导窗缺省镜像逐位一致 = 设计件
    changes/2026-09-12-prep-chain-containerization/design/
    prep链容器化方案.md §2.2② 行为差申报面。
    求值 = 当前帧 PL 键的 λ 点估计(CI 上端,排序键同 ``lambda_u_order``
    的全序口径)在 C 集合可消费格 λ_U 降序全序中的分位序 ≤ p ⇒ 触发。
    键观测量缺失/域外/不可消费格 → None(不评估;域外同判 R52-4a)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import (
        lambda_death,
    )
    node = node_kind_of(bs) or ''
    key = lambda_death.make_key(bs.enemy_difficulty.value,
                                hp, plane_of(bs), node)
    ci = lambda_death.lambda_ci(key)
    if ci is None:
        return None
    order = lambda_death.lambda_u_order()
    if not order:
        return None
    # 降序全序中的序位:取同值首址(饱和并列组按最危端,保守)
    idx = next((i for i, v in enumerate(order) if v <= ci[1]), None)
    if idx is None:
        return None
    return (idx + 1) / len(order) <= p_value


def _upgrader_evaluate(session: StrategySession, bs: GameState,
                       hp: int | None) -> UpgraderSignals:
    """升档器求值(§2.0-3 判危口径①②;本批 None 期 = 结构位 + 影子计数)。

    载体 = 容器 bs(prep 链容器化段 1);死参 ``gold`` 删除(现体零消费,
    设计件 prep链容器化方案.md §2.2③)。委托 λ 谓词形态不变;血线硬
    地板判断(hp ≤ ``HP_BAND_NEAR_DEATH``)零改,hp 形参保留(调用方
    供给,非本函数域读)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
        provisional,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn import (
        lambda_death,
    )
    sig = UpgraderSignals()
    # λ 顾问:R28-1 相对分位触发。标定前置影子维持声明按用户裁定撤销
    #(死亡线标定落地批):p 在场即求值,触发 ⇒ 真键武装(行为介入开启);
    # lambda_shadow 保留为对照键(同条件置位,禁删)。p=None ⇒ 不求值。
    p = provisional.get('P_LAMBDA_QUANTILE')
    if p is not None:
        armed = _lambda_quantile_armed(bs, hp, float(p.value))
        if armed:
            sig.lambda_armed = True
            sig.lambda_shadow_armed = True   # 对照键保留
    # 血线硬地板(标定落地,用户裁定=按 15):阈值单一源 =
    # lambda_death.HP_BAND_NEAR_DEATH(BLOODLINE_HP_THRESHOLD provisional
    # 源退役,两源归一);hp ≤ 阈值 ⇒ 解锁包三件武装(F7 禁令/M3 分流/
    # arm2 门,行为介入开启);影子键保留对照。
    if hp is not None and hp <= lambda_death.HP_BAND_NEAR_DEATH:
        sig.neardeath_unlock = True
        sig.arm2_gate_open = True     # R28-2 解锁包:g*→0(arm2 金下限)
        sig.f7_ban_armed = True
        sig.bloodline_shadow_armed = True   # 对照键保留
    return sig


def emit(obs: PrepObservation, turn: TurnState, session: StrategySession,
         config: object, *, ev_arm: str = 'full',
         registry: DecisionV2Registry | None = None) -> list[Emitted]:
    """决策入口三遍编排(R189-4 结构签名;返回 Emitted 列表交桥截断发射)。

    编排:① prep 实体面(箱选卡/球/箱/典籍——控制流与 overlay 切换
    优先于三遍)→ ①′ wanted 闭环消费臂(迁移 A;义务优先)→ ② 证明
    pass(信号臂/K/stop_flag/线级状态机/换线)→ ②′ 工具消费发射位
    (迁移 C,物理移出自 run_mandate)→ ③ 升档器求值位 → ④ 骨架 pass
    (M1-M7)→ ⑤ EV pass(criteria,臂①旁路)→ ⑥ 无动作 ⇒ StartBattle
    (序列终点=备战环正常出口)。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        Emitted,
    )

    if getattr(state_of(session), 'cw4_counters', None) is None:
        state_of(session).cw4_counters = {}

    # prep 链容器化段 2:决策判据载体一次置顶(五处签名、prep 域全簇与
    # K 空窗回退全部直连容器单例,obs.state 视图槽随黑板槽退役消亡;
    # 同帧同视图纪律 =《商店黑板容器化方案》§2.2-1,禁函数内二次取容器)。
    bs = board_state_of(session)
    _round_num = round_num_of(bs)

    # ① prep 实体面
    if getattr(obs, 'box_overlay_open', False):
        # 武装箱选择对话框在场 ⇒ 选卡动作闭环(本臂 = 选卡决策唯一发射点:
        # OpenBox 动作纯机械执行不内联选卡,ADR-0601)。第十八局停场修复
        # (g_20260905_175220 备战 2-2):此前 OpenBox→弹窗后决策面无臂
        # 消费 box_overlay_open,OpenBox 重开空转 15 分钟(执行器
        # _pick_box_card/期望态投影/适配器注册均早在库,独缺发射位)。
        return [Emitted(PickBoxCard(), True, 'prep_box_pick')]
    if obs.boxes:
        return [Emitted(OpenBox(slot=obs.boxes[0][0]), True, 'prep_box')]
    if obs.tomes:
        return [Emitted(OpenTome(slot=obs.tomes[0][0]), True, 'prep_tome')]
    if obs.spheres:
        # 席满让路门(T-297 落码;ADR-0642;方案正本 = T-281 修复方案稿
        # v2.1,重写自 ADR-0596 §4.9③ 迁移 B 两腿谓词的收球行为,结构
        # 保活面见下方死码块)。门显式条件化(方案 §3.2/B5):
        # - 格3 席自由(free>0):自愈形态(screen_flow_timing #16),
        #   行为等价——动作序列与状态迁移与改前一致,新增仅 streak 归零
        #   记账写入;单帧偶发失败由既有逐帧重试自愈,不让路不计数。
        # - 格1/格2 席满(free==0):机制性拒绝形态(2026-09-11 实机
        #   12 击零消失实证,与 cw_identity_obs.py 建档注释一致)——
        #   每搁浅情节首环发单探针(K=1 预注册,区分「机制性拒绝」vs
        #   「单帧偶发落空」),次环起让路 fall-through:球分支零发射、
        #   不 return,落入 ①′→②→③⑤→⑥ 常规链(席满帧常规链恢复
        #   求值;三 SellBench 发射位受既有 sell_gate 契约核验与息线
        #   冻结门辖域,非本批新判据;空批 → ⑥ StartBattle 合法交回)。
        # - 成效重置:席自由化 ∨ 成效计数签名变化(轮次/席计数/球计数
        #   任一,见 _sphere_progress_sig)。设计动机(B5 对偶面):若
        #   「席满可点开」形态真实存在(金球内容即时入账方向),每次成功
        #   点开必减球计数 → 重置 → 连续收球不被打断——宁多收球在门
        #   语义层保住。
        # 遥测键登记(单一源 = 本写点;design_telemetry.md 已随文档树
        # 重组灭失,键节落写点旁):sphere_defer_streak(席满搁浅情节内
        # 探针计数,成效重置;会话级=局级,接管局冷建=保守侧恢复点击)/
        # sphere_defer_progress_sig(成效签名快照,门簿记账非行为计数)/
        # sphere_defer_yield(让路帧计数)/ sphere_blocked_bench_full
        #(死码块内,现状恒零写)。与 exec_state.defer_count 零读写关系
        #(该字段为既有死词汇,纠偏见 cw_exec_state.py;方案 §3.6/B7)。
        _ct_sp = state_of(session).cw4_counters
        _sf_free = _sphere_bench_free(obs)
        if _sf_free > 0:
            if isinstance(_ct_sp, dict):
                _ct_sp['sphere_defer_streak'] = 0
            return [Emitted(ClickSpheres(
                        max_k=min(SPHERE_CLICK_BATCH_MAX_K, len(obs.spheres))),
                        True, 'prep_spheres')]
        _prog_sig = _sphere_progress_sig(bs, obs)
        _streak = 0
        if isinstance(_ct_sp, dict) \
                and _ct_sp.get('sphere_defer_progress_sig') == _prog_sig:
            _streak = int(_ct_sp.get('sphere_defer_streak', 0) or 0)
        _streak += 1
        if isinstance(_ct_sp, dict):
            _ct_sp['sphere_defer_streak'] = _streak
            _ct_sp['sphere_defer_progress_sig'] = _prog_sig
        if _streak <= SPHERE_DEFER_PROBE_K:
            # 单探针:同发射形态 = 现状 prep_spheres 动作(零新动作类)。
            return [Emitted(ClickSpheres(
                        max_k=min(SPHERE_CLICK_BATCH_MAX_K, len(obs.spheres))),
                        True, 'prep_spheres')]
        if isinstance(_ct_sp, dict):
            _ct_sp['sphere_defer_yield'] = \
                _ct_sp.get('sphere_defer_yield', 0) + 1
        # 让路 fall-through:不发球动作,落入下方常规步骤序(ADR-0642)。
        # —— 旧谓词第二腿 + 腾席臂(迁移 B 原案;ADR-0596 §4.9③「结构
        # 保活」明文):**保留原位,当前不可达**(结构性死码,非退役)。
        # 触发条件 `_sf_occupied` 要求 SPHERE_OCCUPYING_COLORS 非空(见
        # 模块头:现役缺省空集 = 宁多收球不误卖),整块不可达;备选A
        # 激活(晶矿 odds 采集批登记占席色,方案 §4)时恢复可达 = 让路
        # 帧腾席先于收球。禁删除:退役-复活双倍审面(方案稿 §7.1 编排者
        # 终态;读者陷阱以本标注显影,与 defer_count 纠偏同批零行为代价)。
        _sf_occupied = any(
            (color or '') in SPHERE_OCCUPYING_COLORS
            for color, _pt, _r in obs.spheres)
        if _sf_occupied:
            _sf_k = predicates.line_members(
                getattr(state_of(session), 'target_comp', None))
            _sf_excl = sell_gate.sell_exclusions(
                session, _sf_k, channel='m4_fuel',
                cap_hold=locked_buy_cap_hold(bs),
                current_round=_round_num)
            _sf_cands = mandate.fuel_sell_candidates(
                list(obs.bench_chars), _sf_k, state=bs,
                exclude_names=_sf_excl,
                counters=state_of(session).cw4_counters,
                dedup_names=set())
            if _sf_cands:
                # 轮内卖出登记(泄金阶梯档 2 新鲜度排除写端,ADR-0604 §3;
                # 球路径 M4 腾席与 prep/shop 域 M4 同口径——漏记 = 卖X 后同轮
                # 压库买回 X 的净零自旋在该路径残余可达)。
                mandate.record_round_sold(session, bs,
                                          _sf_cands[0].char_id or '')
                return [Emitted(SellBench(slot=_sf_cands[0].slot), True,
                                'm4_fuel_sell')]
            _ct_sf = state_of(session).cw4_counters
            if isinstance(_ct_sf, dict):
                _ct_sf['sphere_blocked_bench_full'] = \
                    _ct_sf.get('sphere_blocked_bench_full', 0) + 1
            # 球残留跳过:不 return,落入下方常规步骤序(下帧 ① 再尝试)
    if obs.event_overlay:
        return [Emitted(BailToOuter(reason=obs.event_overlay), True,
                        'event_overlay')]

    # ①′ wanted 闭环消费臂(T-159 迁移 A;位次 = ①实体面后、②证明 pass
    # 前——wanted 是未完成义务,滞留越久损失越大,方案 §5.2)。非空返回
    # = 臂动作即本帧发射(单动作环直通);空返回 = 臂无发射(门 0 失效/
    # 门 1 S1 已清/放弃态),照常落回常规步骤序。deploy_cap 真值链与
    # ④ 骨架帧同源(max_units_of 读口派生,R4 单一真值源)。
    _arm_out = mandate.wanted_closure_emit(
        session, bs, list(obs.bench_chars), list(obs.deployed_chars),
        max_units_of(bs), _round_num)
    if _arm_out:
        return _arm_out

    # 帧级复位(与 posture_release.attach_spend_authorization 同口径):
    # 每决策段「入口=无声明、段尾=本段真值」,防 posture_unfulfilled 旧值
    # 跨帧滞留成假信号(病灶②修法的正确性前提)。
    state_of(session).v3_posture_unfulfilled = None
    k = getattr(state_of(session), 'target_comp', None)
    k_members = predicates.line_members(k)
    # K 空窗回退(准备域;经济冻结批病灶①保险层):shop.py 商店域已有
    # 同款回退,准备域(mandate pass)旧形态 K=None ⇒ k_members=() ⇒
    # M2 无目标、dominance/M6 停手、引擎只剩 M7,0 买 0 刷经济冻结
    # (实机局 g_20260904_042657 p1r7-r9)。回退单一源 = cw_intention
    # (与 shop.py 同源消费,禁复制四体系全集/兜底逻辑);ist 缺失 =
    # 意向供给缺帧,保守侧不回退(与 shop.py 同款 fail 方向)。
    if k is None:
        from sr_od.application.currency_war.kernel import cw_intention
        _ist = getattr(state_of(session), 'v3_intention', None)
        if _ist is not None:
            # session/registry 透传(P86;落地审 F-2):甲臂 G 门按 plane
            # 真值视界与当帧注册表判定,与商店域同源(两域禁分叉)。
            # W6 波3 贯通 + prep 链容器化段 1 消桥:kernel 已容器签名,
            # 直传置顶 bs(旧帧经桥装箱面消亡)。旧「state 非 None」前置
            # 随 obs.state 槽退役消亡(段 2:heavy 观察恒供数,该分支
            # 生产不可达——设计件 §2.2② 同款申报)。
            _fb, _band = cw_intention.k_empty_window_fallback(
                bs, _ist, session=session, registry=registry)
            if _fb:
                k_members = tuple(sorted(_fb))
                state_of(session).cw4_counters[f'prep_k_fallback_{_band}'] = \
                    state_of(session).cw4_counters.get(f'prep_k_fallback_{_band}', 0) + 1
    bench = list(obs.bench_chars)
    deployed = list(obs.deployed_chars)
    bench_names = [b.char_id or '' for b in bench]
    deployed_names = [b.char_id or '' for b in deployed]

    # ② 证明 pass(信号臂 R11-3:两臂同开不旁路;命中=直通线语境,计数披露)
    if proof.signal_arm(session) is not None:
        _ct_sig = state_of(session).cw4_counters
        _ct_sig['signal_arm_direct'] = _ct_sig.get('signal_arm_direct', 0) + 1
    stop_flag = None
    # 契约核验(FIX_REVIEW R1 漏接位补齐):stop_buy 消费位经
    # ensure_contract(前提恒真 None 登记,违例路径仅剩未登记键);
    # 弃权侧=保守停买(fail-closed,支配买/溢余面不因缺核验开闸)
    if contracts.ensure_contract(
            ('proof', 'stop_buy'), contracts.ContractCtx(),
            state_of(session).cw4_counters):
        stop_flag = proof.stop_buy(k, bench_names, deployed_names)
    else:
        stop_flag = True
    proof.update_line_state(session, k, bench_names, deployed_names)
    skeleton_only = (ev_arm == 'skeleton_only')
    switch = proof.should_switch(
        bs, session, config, registry, skeleton_only=skeleton_only)
    # 换线事件本帧只登记,K 变更下一备战期生效(R1-3):登记 = 撤线窗口
    # 步进 + 换线遥测;K 翻转由方向重估(下帧决策入口)承载(ADR-0583)。
    # 【R197 症2 影子面声明(编排者裁=方案 a)】A/B 期 target_comp 权威
    # = decision_v2 意向状态机(经 flow 层方向刷新,两臂同源恒等);本
    # 登记只写回锁窗状态与计数,不写 target_comp——cw4 换线判据族
    # (should_switch/回锁窗/干旱计数)=影子面,实装接线=过线后批。
    if switch.event:
        proof.register_eviction(session, getattr(k, 'name', ''))
        counters = state_of(session).cw4_counters
        counters['switchline_event'] = counters.get('switchline_event', 0) + 1
    # 证据门影子评估(接线批 T-213/ADR-0637;R197 症2 影子面同族):
    # 输出只进 cw4_counters 分键,返回值不被消费做行为——封印期(Δ/ε₂/
    # V_ms/Δλ【拟】全 None)恒「不可评」诚实显影,绝不向骨架层渗漏为
    # 否决(NMF §6/§5.3);权威面切换候标定落地另案裁决批。
    proof.evaluate_evidence_gate(bs, session)
    # k_switched 实值化(R196 症1):上一备战期线名快照 vs 本帧生效 K 名
    # ——不同即换线已在本帧生效(塌缩出口评估条件,line_switch_sell 只在
    # K 已更新的备战期评,§2.7);旧线成员自 COMP_LIBRARY 按名取回。
    prev_name = getattr(state_of(session), 'cw4_prev_line_name', '') or ''
    cur_name = getattr(k, 'name', '') if k is not None else ''
    k_switched = bool(prev_name) and prev_name != cur_name
    old_line_members = predicates.line_members(get_comp(prev_name)) \
        if k_switched else ()

    # ②′ 工具消费发射位(T-159 迁移 C,审 A1 主案:物理移出自
    # run_mandate M7.5 块,防双发射由 mandate 侧删块承载)。判据单一源
    # = kernel/cw_equip_env.evaluate_tool_actions + admitted_tool_actions
    # (G1 准入)原样;工具期闩 cw4_tools_phase 同 phase 一次语义原样
    #(写点 mark_tools_pass_executed 在执行位,发射位只读不写)。发射
    # 语义 = 判据/准入通过的 RunTools 挂起,骨架 pass 输出后前置合并
    #(见下方 ④ 合流)——RunTools 投影未建模,当帧 visit 终结,消耗品
    # 给的经验/金经下一 visit 入口 heavy 进 M3;前移真正消除的是
    # 「旧输入 LevelUp 先执行→错误升级照发」面(编者⑤ 裁决输入新鲜度;
    # 收益路径口径 = 方案 §4 猎点 12 v2.1 更正)。
    from sr_od.application.currency_war.kernel.cw_equip_env import (
        admitted_tool_actions as _admit_tools,
    )
    from sr_od.application.currency_war.kernel.cw_equip_env import (
        evaluate_tool_actions as _eval_tools,
    )
    _tools_emitted: list[Emitted] = []
    _tools_phase = (plane_of(bs), _round_num)
    # owned 快照源 = 黑板帧 owned_equips(P4 观察接线,T-171;旧
    # session.last_owned_equips 陈旧快照读点退役——评估输入与计划产出位
    # 同帧同源,开箱新件经下一入口观察进帧)。
    _owned_snap = list(getattr(obs, 'owned_equips', None) or [])
    if _owned_snap:
        _ct_tools = state_of(session).cw4_counters
        _tool_actions = _eval_tools(
            _owned_snap, getattr(state_of(session), 'target_comp', None))
        _tool_admitted = _admit_tools(_tool_actions)
        # 评估即留痕(二十四局复盘候选⑤:评估过但拒与未评估不可辨):
        # owned 快照在场即计已评估帧;零可执行件帧按拟执行动作分键显影
        #(m7_5_reject_{action},action = 判据面稳定标识;reason 是中文
        # 判读文本非键面,禁直拼)。无任何条目产出计 m7_5_reject_none。
        # 观测面零策略语义:工具动作放行判定(any usable)与闩不变。
        _ct_tools['m7_5_evaluated'] = _ct_tools.get('m7_5_evaluated', 0) + 1
        if not any(a.usable for a in _tool_admitted):
            if any(a.usable for a in _tool_actions):
                # 判据放行但准入拒(执行通道未就绪形态)——禁混入判据拒桶
                _ct_tools['m7_5_reject_g1_not_admitted'] = \
                    _ct_tools.get('m7_5_reject_g1_not_admitted', 0) + 1
            else:
                _m75_rejs = sorted({a.action for a in _tool_actions
                                    if not a.usable})
                for _r in _m75_rejs:
                    _ct_tools[f'm7_5_reject_{_r}'] = \
                        _ct_tools.get(f'm7_5_reject_{_r}', 0) + 1
                if not _m75_rejs:
                    _ct_tools['m7_5_reject_none'] = \
                        _ct_tools.get('m7_5_reject_none', 0) + 1
        for _ta in _tool_admitted:
            log.info('[cw!][tools] tool=%s action=%s usable=%s reason=%s',
                     _ta.tool, _ta.action, _ta.usable, _ta.reason or '-')
        if any(a.usable for a in _tool_admitted):
            if getattr(state_of(session), 'cw4_tools_phase',
                       None) == _tools_phase:
                _ct_tools['tools_latch_skip'] = \
                    _ct_tools.get('tools_latch_skip', 0) + 1
            else:
                _tools_emitted.append(
                    Emitted(RunTools(), True, 'm7_5_tool_consume'))

    # ③ 升档器求值位(先于一切卖面判据评估,§3.1;载体 = 置顶 bs,
    # hp 调用方供给 = decision_hp 政策读口(门前真值+消费侧施门单一源;
    # 旧视图帧 hp 直读随 obs.state 槽退役消亡,§2.4-2 hp 消费统一收口))
    _sig = _upgrader_evaluate(session, bs, decision_hp(bs, session))
    _ct = state_of(session).cw4_counters
    if _sig.lambda_shadow_armed:
        _ct['advisor_lambda_shadow_armed'] = \
            _ct.get('advisor_lambda_shadow_armed', 0) + 1
    if _sig.lambda_armed:
        _ct['advisor_lambda_armed'] = \
            _ct.get('advisor_lambda_armed', 0) + 1
    if _sig.bloodline_shadow_armed:
        _ct['advisor_bloodline_shadow_armed'] = \
            _ct.get('advisor_bloodline_shadow_armed', 0) + 1
    if _sig.neardeath_unlock:
        _ct['advisor_bloodline_armed'] = \
            _ct.get('advisor_bloodline_armed', 0) + 1
        _ct['neardeath_unlock'] = _ct.get('neardeath_unlock', 0) + 1

    # ④ 骨架 pass
    # cap 真值源=max_units_of 读口派生链(R4 统一,FIX_REVIEW ②-1 双源
    # 漂移修复:旧 ``obs.deploy_vacancy + len(deployed)`` 观察复合废弃
    # ——与 shop 侧 arm1 消费位同链单源)
    # 部署面 membership 消费口径声明(评估出处 = 策略审查报告 20260905-093104-strategy-review/策略审查-第十二跳.md):本帧 k_members
    # = predicates.line_members(core∪shared,部署语义口径)——部署/升级
    # 授权只量可上阵阵容;买入义务面口径 = buy_members(shop 域,含锁定
    # 采购集超集)——两口径分域 = 有意设计(编排者存-2 裁决:囤腿件走
    # 合成→上板,部署面只量可部署现量)。分层归属:transition_pair 维持
    # ADR-0367 二级囤货(locked_buy_membership 已排除,不入部署/买入义务);
    # F3(全 2★ 旧线重锚)经编排者裁决驳回(前提事实错误:第十局板面为
    # 全 1★ 旧线;§9.5 单一源资格已覆盖该病例),全 2★ 形态另案观察。
    frame = mandate.MandateFrame(
        gold=gold_of(bs),
        level=level_of(bs),
        bench=bench, deployed=deployed,
        deploy_cap=max_units_of(bs),
        node_type=getattr(session, 'node_type_current', None),
        stop_flag=stop_flag, k_members=k_members,
        round_num=_round_num,
        # 装备域 owned 件名池直传(P4 观察接线,T-171):M7 装备穿戴放行
        # 判定输入与计划产出位同帧同源(None = 识别域未就绪,门按空保守关)。
        owned_equips=getattr(obs, 'owned_equips', None))
    # registry 下传骨架 pass(等级帽单一源,ADR-0565 收口 = ADR-0606:
    # M3 链 lv9_stop/level_spend_blocked 消费注入表,与 ④′ 姿态对账
    # 同一注入链)。
    out: list[Emitted] = mandate.run_mandate(frame, session, state=bs,
                                             registry=registry)
    # ④ 合流(迁移 C):工具发射前置 = 同帧 LevelUp+RunTools 形态执行序
    # = RunTools 先于 LevelUp(编者⑤ 升级裁决输入新鲜度;行为锚 =
    # test_cw_prep_flag_machine::test_runtools_emit_position)。RunTools
    # 投影未建模 ⇒ 当帧 visit 在工具消费后终结,其后动作下一帧带新输入
    # 重评。M7 发射序回排块(run_mandate 内)已不见 RunTools,零特例叠加。
    if _tools_emitted:
        out = _tools_emitted + out

    # ⑤ EV pass(臂①旁路集=§4.2.1 显式清单;仅 criteria 真 EV 项)。
    # R197 症1:EV 输出先收进独立列表,经 _merge_ev_before_frame_end
    # 按依赖拓扑并入(EV 卖面=bench 域可续动作,插到骨架首个截断点/
    # 终点动作之前——否则换线生效帧的塌缩出口发射落在 OpenShop 之后
    # 被截断器静默丢弃)。
    ev_out: list[Emitted] = []
    if not skeleton_only:
        ev_out = _criteria_pass(frame, session, bs, k_members,
                                k_switched=k_switched,
                                old_line_members=old_line_members,
                                skeleton_out=out)
    else:
        # 支付支撑通道(两臂同开,R13-5):金不足侧筹资变现;同槽冲突
        # 先到先得丢弃(R196 症2,与骨架 M4 已发射槽位比对)
        sold_slots = {e.action.slot for e in out
                      if isinstance(e.action, SellBench)}
        missing = [m for m in k_members
                   if m not in set(bench_names) | set(deployed_names)]
        # 判据契约核验(单一源=criteria/contracts.py):前提不成立 ⇒ 本帧弃权
        # + criteria_contract_violation 计数,禁静默执行
        if missing and contracts.ensure_contract(
                ('sell', 'funding_support_sell'),
                contracts.ContractCtx(gold=gold_of(bs)), _ct):
            # 排除集 = 统一装配 A 全量形态(单一入口 sell_gate;ADR-0585,
            # 方案 v3 §2.9 新格 A):本位旧形态**空排除**——锁线宽集成员
            # (zero_overlap 只拦窄 k_members)可被 prep funding 卖 → shop
            # 域 M2 重买 = 义务换手;义务基座(锁线宽窄解析单点)∪ 静态
            # 持有两集(P78-4)∪ 窗口段(批 3)在此并入。
            _f_round = _round_num
            _f_excl = sell_gate.sell_exclusions(session, k_members,
                                                channel='funding',
                                                cap_hold=locked_buy_cap_hold(
                                                    bs),
                                                current_round=_f_round)
            _f_need = mandate.cheapest_member_cost(frame)
            slots, _why = crit_sell.funding_support_sell(
                gold_of(bs), _f_need, bench,
                k_members, state=bs,
                exclude_names=_f_excl,
                counters=_ct,
                dedup_names=set())   # C1 事件口径:单帧去重(单调用语境)
            # 兜底豁免(P78-5:主路径空 ∧ 仍需筹资;池定义单一源 =
            # sell_gate.funding_hold_fallback;减法①读到的是上一 visit
            # 买入名,方向偏保守无害,V2-10)。
            _f_fallback = []
            if not slots and gold_of(bs) < _f_need:
                _f_fallback = sell_gate.funding_hold_fallback(
                    session, k_members, bench, gold=gold_of(bs),
                    need=_f_need, a_exclusions=_f_excl,
                    deployed=deployed_slots_of(bs),
                    cap_hold=locked_buy_cap_hold(bs))
            for s in slots:
                if s in sold_slots:
                    _ct['ev_conflict_dropped'] = \
                        _ct.get('ev_conflict_dropped', 0) + 1
                    continue
                # 纯归因载体填充/plain 分键计数已随 2026-09-08 用户归因
                # 遥测删除指令拆除:reason/标记缺省 '' 未标,发射行为零面。
                ev_out.append(Emitted(
                    SellBench(slot=s), False, funding_support=True))
            for bc in _f_fallback:
                if bc.slot in sold_slots:
                    _ct['ev_conflict_dropped'] = \
                        _ct.get('ev_conflict_dropped', 0) + 1
                    continue
                # 卖出销账(出口①;单笔即止,need 即止)。兜底分键计数/
                # 载体填充已随 2026-09-08 用户归因遥测删除指令拆除
                #(reason/标记缺省 '' 未标)。
                sell_gate.consume_on_sell(session, bc.char_id or '')
                ev_out.append(Emitted(
                    SellBench(slot=bc.slot), False, funding_support=True))
                break
    out = _merge_ev_before_frame_end(out, ev_out)

    # ⑤′ 姿态兑现对账(经济冻结批病灶②):预算核姿态(spend_mode='level')
    # 授权了本轮升级而发射序列无 LevelUp ⇒ posture_unfulfilled 显式置位
    # + 姿态降级声明 + 计数/日志。旧形态=守卫字段接而不用:授权面
    # (get_node_goal,确定性预算核单一供给)与执行面(M3:arm1 存在性 +
    # spend_unified 整批纪律)判定不一致时零对账,session.v3_posture_
    # unfulfilled 恒 None(实机局 g_20260904_042657 p1r7-r9 posture=
    # 'level' 全程零 LevelUp)。本对账只声明不兜底花钱(禁重引入「乱花」
    # 对立面:P56 下界语义零触碰,升级仍由 M3 判据独裁)。
    _reconcile_posture_authorization(session, bs, out, k_members,
                                     registry=registry)

    # 形态⑥观测(纯观测零行为,fail-closed 期只记不判):target 空窗
    # ∧ 濒死带(p1/p2 域谓词,血带结构锚单一源在谓词内)∧ 域外(裸金
    # 判定)∧ 持金 ∧ 本帧零金消费——金滞留入败局的形态显影。键声明 =
    # supply_arbitration_design/DESIGN.md §5.1 terminal_targetless_idle
    # (不分位面,键名从其申报);设计出处 = p2_blood_band_unified_design/
    # DESIGN.md §2.1 fail-closed 观测面。载体辖域申报 = 备战决策帧主通道
    # (emit ①/①′ 实体面提前返回帧不入键);OpenShop 计入消费面
    #(开店即买入意图,金将在店帧消费,非滞留)。判定面零行为:计数不改
    # 发射序列,守卫锁 = test_cw_p2_blood_band.py。载体 = 置顶 bs(段 2:
    # 裸金判定经 gold_of 读口,缺省 0 镜像;旧 state-None 守卫消亡)。
    if (gold_of(bs) > 0
            and getattr(state_of(session), 'target_comp', None) is None
            and not in_must_spend_zone(gold_of(bs), session)
            and not any(isinstance(e.action, (LevelUp, OpenShop))
                        for e in out)
            and (predicates.p1_blood_floor(bs)
                 or predicates.p2_blood_floor(bs))):
        _ct['terminal_targetless_idle'] = \
            _ct.get('terminal_targetless_idle', 0) + 1

    # ⑥ 无动作 ⇒ 出战(序列终点)
    # F1(T-167)后本出口的可达面恢复:无方向态 M1″ 换阵臂被「换阵可
    # 兑现」谓词(kernel swap_realizable)弃权,不再发射执行面必然空转的
    # 幻影 RunDeploy(实证:run_20260908_210431 发射 53 次、执行 0 次,
    # 交替活锁把本出口堵死 15 分钟)——闩闭帧序列归空,StartBattle 自然
    # 可达(支配性论证:备战等待边际收益恒 0,见 cw_loop 收益耗尽判据
    # docstring)。有向态语义不变(计划非空照发,计划空本就达本出口)。
    if not out:
        out.append(Emitted(StartBattle(), True, 'battle'))
    state_of(session).cw4_prev_line_name = cur_name   # 下帧 k_switched 判定基准
    return out


def _reconcile_posture_authorization(session: StrategySession,
                                     bs: GameState,
                                     emitted: list[Emitted],
                                     k_members: tuple[str, ...] = (),
                                     registry: DecisionV2Registry | None = None,
                                     ) -> dict | None:
    """姿态兑现对账(经济冻结批病灶②;授权面与执行面的唯一仲裁点)。

    载体 = 容器 bs(prep 链容器化段 2:签名与域读全容器形态,域读经读口族,
    体内无第二视图装配)。
    hp 消费经 ``decision_hp`` 政策读口(门前真值+消费侧施门单一源,
    禁直读 ``bs.hp.value`` 引入施门旁路——《商店黑板容器化方案》
    §2.2-2 同锚;视图帧 hp 直读面随载体切换退役)。

    授权面 = ``get_node_goal`` 确定性预算核(spend_mode 单一供给,遥测
    dp_posture 同源);执行面 = M3 升级链(arm1 存在性 → lv9 停 →
    spend_unified 整批纪律 → 可负担)。spend_mode='level'(本轮授权升级)
    而发射序列无 LevelUp ⇒ 逐门评估定位未兑现原因,显式声明:
    - ``state_of(session).v3_posture_unfulfilled`` 置位(遥测 posture_unfulfilled
      消费;形状与 decision_v2.posture_release.reconcile_spend 同构);
    - 计数键 ``posture_unfulfilled_level``(state_of(session).cw4_counters);
    - log.info(带未兑现原因,判读可直接归因;auth_id/日志串的 plane/
      round 取读口值,格式不变)。

    只声明不兜底:不因授权未兑现而改发射(升级发射仍由 M3 判据独裁,
    P56 下界语义零触碰)。授权形态非 level / 已发射 LevelUp ⇒ 返回
    None(且入口帧级复位保证无声明滞留)。
    """
    _plane = plane_of(bs)
    _round = round_num_of(bs)
    _gold = gold_of(bs)
    _level = level_of(bs)
    _hp = decision_hp(bs, session)
    # 上下文注册表(判据出处纠错批:等级帽单一源接线;emit 注入链 =
    # MandateV1Strategy.registry,sim 帧注入视图随链到达)。None→缺省表
    # 兜底与 shop 栈 _reg 同款通道约定,直调/测试面兼容;生产链恒注入。
    _reg = registry
    if _reg is None:
        from sr_od.application.currency_war.kernel.cw_registry import (
            DEFAULT_REGISTRY,
        )
        _reg = DEFAULT_REGISTRY
    from sr_od.application.currency_war.kernel.cw_economy import get_node_goal
    ng = get_node_goal(_plane, _round, gold=_gold,
                       level=_level, hp=_hp,
                       strategies=list(bs.active_strategies.value or [])
                       or None)
    if getattr(ng, 'spend_mode', '') != 'level':
        return None
    if any(isinstance(e.action, LevelUp) for e in emitted):
        return None
    # T-115 规则① 消费位4(ADR-0580):奖励帧抑制授权面让位 = 显式降级,
    # 防奖励帧被「逐门定位未兑现原因」当故障链走(与 crisis_yield 修复
    # 前的噪声同型;范式 = 下方 crisis 让位三键结构,不另造让位机制)。
    # 位次钉死(方案 D2)= 授权链**首位**:先于危机让位与血闸镜像求值
    # ——置于血闸之后时,血本位奖励帧先命中 blood_xp_gate_blocked 提前
    # return,本分键永不可达;抑制先行声明 = 方案 §0.2(抑制 = 结构性
    # 无授权,支付能力检查无须求值)。判据单一源 = kernel.cw_reward_node
    # (与 M3 三消费位同谓词,None fail-open)。载体 = 置顶 bs 直传
    #(prep 链容器化段 1 消桥)。
    if reward_node_suppressed(bs):
        un = {'auth_id': f'{_plane}-{_round}',
              'channel': 'levelup',
              'reason': 'reward_node_no_power_need',
              'channels': {'levelup': 'reward_node_no_power_need'},
              'action': 'reward_node_yield'}
        state_of(session).v3_posture_unfulfilled = un
        counters = getattr(state_of(session), 'cw4_counters', None)
        if isinstance(counters, dict):
            counters['posture_reward_node_defer'] = \
                counters.get('posture_reward_node_defer', 0) + 1
        log.info('[cw][cw4] posture level 授权奖励帧让位 '
                 '(plane=%s r%s): %s',
                 _plane, _round, un['reason'])
        return un
    # 候选③:危机带经验授权让位 = 显式降级而非「未兑现故障」——
    # M3 发射位(mandate/shop)被 level_spend_blocked 挂起时,授权面
    # 按 crisis_yield 声明(P48 λ>0 段转化优先;判据单一源同 M3 消费位),
    # 不落逐门故障定位(那些门本轮根本未被求值)。
    if contracts.ensure_contract(
            ('levelup', 'level_spend_blocked'),
            contracts.ContractCtx(), getattr(state_of(session), 'cw4_counters',
                                             None) or {}) \
            and crit_levelup.level_spend_blocked(bs, session, _reg):
        un = {'auth_id': f'{_plane}-{_round}',
              'channel': 'levelup',
              'reason': 'crisis_level_spend_blocked',
              'channels': {'levelup': 'crisis_level_spend_blocked'},
              'action': 'crisis_yield'}
        state_of(session).v3_posture_unfulfilled = un
        counters = getattr(state_of(session), 'cw4_counters', None)
        if isinstance(counters, dict):
            counters['posture_crisis_level_defer'] = \
                counters.get('posture_crisis_level_defer', 0) + 1
        log.info('[cw][cw4] posture level 授权危机让位 '
                 '(hp=%s, plane=%s r%s): %s',
                 _hp, _plane, _round,
                 un['reason'])
        return un
    # [40]② 血闸镜像(ADR-0578):发射位闸拒 → 授权面 crisis_yield 同款让位
    # 语义(支付能力检查独立于停付线,不可被域/地板豁免;金本位恒 True 直通)。
    # kernel 闸波 2 已切容器签名(hp 经政策层读口);载体 = 置顶 bs 直传
    #(prep 链容器化段 1 消桥:旧帧经桥装箱面消亡,视图→桥→容器往返恒等)。
    if not blood_xp_gate_for(bs, session):
        un = {'auth_id': f'{_plane}-{_round}',
              'channel': 'levelup',
              'reason': 'blood_xp_gate_blocked',
              'channels': {'levelup': 'blood_xp_gate_blocked'},
              'action': 'crisis_yield'}
        state_of(session).v3_posture_unfulfilled = un
        counters = getattr(state_of(session), 'cw4_counters', None)
        if isinstance(counters, dict):
            counters['posture_blood_xp_gate_defer'] = \
                counters.get('posture_blood_xp_gate_defer', 0) + 1
        log.info('[cw][cw4] posture level 授权血闸让位 '
                 '(hp=%s, plane=%s r%s): %s',
                 _hp, _plane, _round,
                 un['reason'])
        return un
    # 逐门定位未兑现原因(与 run_mandate M3 链同序同判据,复用判据本体
    # 禁第二实现;M3 未发射时这些门的求值是纯函数,零副作用)。
    from sr_od.application.currency_war.kernel.cw_economy import (
        clicks_to_next_level,
        xp_click_cost,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
        levelup,
    )
    cap = max_units_of(bs)
    if levelup.lv9_stop(_level, _reg.level_max):
        reason = 'lv9_stop'
    elif cap is None:
        reason = 'contract_cap_missing'
    elif not predicates.arm1_existence(
            len([d for d in deployed_slots_of(bs) if d is not None]),
            [b.char_id or '' for b in bench_slots_of(bs) if b is not None],
            [d.char_id or '' for d in deployed_slots_of(bs)
             if d is not None], cap):
        reason = 'arm1_board_not_full'
    else:
        # 成本计算 = 容器(W6 波 4 接缝族切容器帧后帧形态不再可喂;
        # level/xp/level_up_cost 与本帧同源=观察漏斗写端,读容器单例;
        # 原体内 board_state_of(session) ×2 随签名切 bs 复用形参消点)
        clicks = clicks_to_next_level(bs)
        cost = xp_click_cost(bs)
        if not levelup.spend_unified(clicks, _gold, cost):
            reason = 'spend_unified_batch_unaffordable'
        elif _gold < clicks * cost:
            reason = 'unaffordable'
        else:
            # P72 (3) 全段预算闸镜像(ADR-0576;与 run_mandate M3 链
            # 同序同判据,复用判据本体禁第二实现):闸拒归因 = budget_gate
            # 族独立拒因,禁落 contract_other 兜底桶(prep 侧降级归因
            # 全错形态,方案审 B4)。cap_resolved 用 resolved 口径单一源。
            _gate_ok, _gate_why = (False, '')
            if contracts.ensure_contract(
                    ('levelup', 'levelup_budget_gate'),
                    contracts.ContractCtx(gold=_gold, deploy_cap=cap),
                    getattr(state_of(session), 'cw4_counters', None) or {}):
                from sr_od.application.currency_war.kernel.cw_economy import (
                    cap_resolved_of_session,
                )
                _gate_ok, _gate_why = levelup.levelup_budget_gate(
                    bs, session, _gold,
                    cap_resolved_of_session(session),
                    k_members, bench_slots_of(bs),
                    deployed_slots_of(bs), clicks, cost)
            reason = (_gate_why if not _gate_ok and _gate_why
                      else 'contract_other')
    un = {'auth_id': f'{_plane}-{_round}',
          'channel': 'levelup',
          'reason': reason,
          'channels': {'levelup': reason},
          'action': 'downgrade'}
    state_of(session).v3_posture_unfulfilled = un
    counters = getattr(state_of(session), 'cw4_counters', None)
    if isinstance(counters, dict):
        counters['posture_unfulfilled_level'] = \
            counters.get('posture_unfulfilled_level', 0) + 1
    log.info('[cw4][posture] level 授权未兑现(p%sr%s g=%s lv=%s):%s '
             '(posture_unfulfilled 置位,显式降级,不兜底花钱)',
             _plane, _round, _gold, _level, reason)
    return un


def _merge_ev_before_frame_end(skeleton: list[Emitted],
                               ev: list[Emitted]) -> list[Emitted]:
    """EV 卖面与骨架动作的依赖拓扑合并(R197 症1;执行序=02_mandate_layer §3)。

    EV 卖面(line_switch_sell/funding_support 的 SellBench)系 bench 域
    操作(画面零迁移,契约 §2 可续类);骨架的开店意图(OpenShop)系
    截断点。合并规则:EV 发射整体插到骨架序列中**首个截断点/终点动作
    之前**,骨架内部相对序与 EV 内部序均不变;骨架无截断点/终点 ⇒ EV
    追加尾部(与 R196 前行为一致)。「EV 只追加」(02_mandate_layer §7 权限划界)的追加面=
    发射组织面;执行序按依赖拓扑承载——不重排则换线生效帧(K 已翻为
    K′、新线有缺口 ⇒ M2 发 OpenShop 的典型帧)的塌缩出口发射全部落
    在截断点之后,被截断器静默丢弃(IMPL_ADV_R197 症1)。
    """
    if not ev:
        return skeleton
    idx = next(
        (i for i, e in enumerate(skeleton)
         if classify_frame_stability(e.action)
         in ('truncation', 'terminal')),
        len(skeleton))
    return skeleton[:idx] + ev + skeleton[idx:]


def _criteria_pass(frame: mandate.MandateFrame, session: StrategySession,
                   bs: GameState, k_members: tuple[str, ...], *,
                   k_switched: bool,
                   old_line_members: tuple[str, ...],
                   skeleton_out: list[Emitted] | None = None) -> list[Emitted]:
    """EV pass:criteria 七面按 §2 映射逐面追加(只增不减,§3.4)。

    载体 = 容器 bs(prep 链容器化段 1:签名切 bs)。域读:金/轮次经
    ``gold_of``/``round_num_of`` 读口(缺省 0/1 镜像旧帧直读,金轮位
    读口 = 设计件 prep链容器化方案.md §2.2⑤ 行为差申报面);兜底上阵
    输入 = ``deployed_slots_of(bs)``(换算单一源)。旧 `state is None`
    守卫随载体退役——bs 恒存在,生产帧视图恒非 None(heavy 观察恒产出)。

    None 期缺省姿态:各面内部 fail-closed(未标定不发射);本函数
    只做发射面组织。冲突处理(R196 症2 落地):EV 项与已发射动作冲突
    (同槽 SellBench——M4 已卖槽/同 pass 内重复提案)⇒ 先到先得丢弃
    + 记遥测(``ev_conflict_dropped``):第二笔执行必 progressed=False
    触发 fail-stop,整序列后半被一帧废动作截断(契约 §2),禁重发。
    """
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        Emitted,
    )
    counters = getattr(state_of(session), 'cw4_counters', None)
    if not isinstance(counters, dict):
        counters = {}
        state_of(session).cw4_counters = counters
    # 先到先得冲突域:骨架 pass 已发射的 SellBench 槽位(席位冲突面)
    sold_slots = {e.action.slot for e in (skeleton_out or [])
                  if isinstance(e.action, SellBench)}
    # 拦截事件去重集(C1 口径:同一备战帧内同一素材名只计 1;跨通道共享,
    # 单一源 = cw_state.count_merge_material_blocked)
    _mm_dedup: set[str] = set()
    out: list[Emitted] = []
    # line_switch_sell(换线塌缩出口:k_switched 时对旧线件重评;
    # 契约核验(单一源=criteria/contracts.py),前提不成立 ⇒ 本帧弃权+计数;
    # 拒因分键接线(D1 整改):本位曾静默 continue,现同键计数显影)
    if contracts.ensure_contract(
            ('sell', 'line_switch_sell'),
            contracts.ContractCtx(k_members=k_members), counters):
        slots, _key = crit_sell.line_switch_sell(
            old_line_members, k_members, frame.bench, frame.deployed, bs,
            k_switched=k_switched, counters=counters,
            dedup_names=_mm_dedup)
    else:
        slots = []
    for s in slots:
        if s in sold_slots:
            counters['ev_conflict_dropped'] = \
                counters.get('ev_conflict_dropped', 0) + 1
            continue
        out.append(Emitted(SellBench(slot=s, reason='line_switch_collapse'),
                           False, 'line_switch_collapse'))
        sold_slots.add(s)
    # 凑息档 EV 面 / 压库 / 装备精修 / 付费刷新:商店线辖域或【拟】
    # None 期 fail-closed,prep 帧无追加发射(判据本体已落
    # criteria/*,商店线接线随步6 前接线批——STEP34_REPORT 裁量呈报)。
    # 支付支撑通道(两臂同开;载体 = 置顶 bs,金/轮位经读口)
    missing = [m for m in k_members
               if m not in set(frame.bench_names) | set(frame.deployed_names)]
    if missing and contracts.ensure_contract(
            ('sell', 'funding_support_sell'),
            contracts.ContractCtx(gold=gold_of(bs)), counters):
        # T3 同轮保留集读端(第四消费位,与店侧 shop.py funding 发射位
        # 同款口径):被保垫件仅降序放行(转化类,非禁卖),命中卖出分键
        # funding_support_stall_convert + 卖出销账。
        _t3_protect = mandate.stall_protect_active(
            session, round_num_of(bs),
            counters=counters)
        # 排除集 = 统一装配 A 全量形态(单一入口 sell_gate;ADR-0585,
        # 新格 A 同根格——与上方 skeleton_only 分支及店侧 funding 发射位
        # 三位同源,空排除形态在此闭死;批 3 窗口段生效)。
        _f_excl = sell_gate.sell_exclusions(
            session, k_members, channel='funding',
            cap_hold=locked_buy_cap_hold(bs),
            current_round=round_num_of(bs))
        fslots, _why = crit_sell.funding_support_sell(
            gold_of(bs), mandate.cheapest_member_cost(frame), frame.bench,
            k_members, state=bs,
            exclude_names=_f_excl,
            counters=counters,
            defer_names=_t3_protect,
            dedup_names=_mm_dedup)
        # 兜底豁免(P78-5:主路径空 ∧ 仍需筹资;pool 单一源同上)。
        _fb_need = mandate.cheapest_member_cost(frame)
        _f_fallback = []
        if not fslots and gold_of(bs) < _fb_need:
            _f_fallback = sell_gate.funding_hold_fallback(
                session, k_members, frame.bench, gold=gold_of(bs),
                need=_fb_need, a_exclusions=_f_excl,
                deployed=deployed_slots_of(bs),
                cap_hold=locked_buy_cap_hold(bs))
        for s in fslots:
            if s in sold_slots:
                counters['ev_conflict_dropped'] = \
                    counters.get('ev_conflict_dropped', 0) + 1
                continue
            # T3 转化类卖出销账(店侧同款)。转化/plain 分键计数与载体
            # 归因填充已随 2026-09-08 用户归因遥测删除指令拆除——prep
            # 卖出恒先于本轮买入,同轮买卖检查豁免面对本位结构性不可达,
            # reason/标记缺省 '' 未标,销账行为面保留。
            _fbc = next((b for b in frame.bench if b.slot == s), None)
            _fname = (_fbc.char_id or '') if _fbc is not None else ''
            if _fname in _t3_protect:
                mandate.stall_buys_consume(session, _fname)
            out.append(Emitted(SellBench(slot=s), False,
                               funding_support=True))
            sold_slots.add(s)
        for bc in _f_fallback:
            if bc.slot in sold_slots:
                counters['ev_conflict_dropped'] = \
                    counters.get('ev_conflict_dropped', 0) + 1
                continue
            # 卖出销账(出口①;单笔即止,need 即止)。兜底分键计数/载体
            # 填充已随 2026-09-08 用户归因遥测删除指令拆除(缺省 '' 未标)。
            sell_gate.consume_on_sell(session, bc.char_id or '')
            out.append(Emitted(
                SellBench(slot=bc.slot), False, funding_support=True))
            sold_slots.add(bc.slot)
            break
    return out
