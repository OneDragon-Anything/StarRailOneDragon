"""货币战争 DirectorV2 备战决策循环(阶段2批②;契约单一源 = 同包 contracts.py)。

快照驱动执行环:``decide(snapshot, session) -> Decision`` 契约的框架侧循环 +
生命周期六件套(步数预算/stall 门/连败→恢复→屏蔽/defer 计数/bail 计数与
ping-pong 停机/W209j 停机刹车),母本 = ``prep_director.py`` 现役六件套;
**逐件清零时机单一源 = ADR-0458**(锁 = sr-od-test test_cw_w588_director_v2
时机锁两条)。

形态:纯循环引擎 + 端口注入——零 IO、零识别调用、零 SrOperation 依赖;
全部外部交互经构造期端口(显式参数),出口为 ``LoopOutcome`` 值
(SrOperation 轮次语义 round_success/retry 的映射归阶段2批③适配器)。
规则中立:框架只消费 ``AtomOp.op_key``(幂等/屏蔽键)与 ``domain``
(同域批校验),不解释 op 语义;op 枚举与 prep_actions 动作族对账归批③。

本模块与现役循环并行、未接线(无消费点),默认零行为影响;接线与
配置开关归批③。
"""
from __future__ import annotations

import enum
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.decision_v2.contracts import (
    AtomOp,
    Bail,
    Decision,
    Defer,
    Snapshot,
    require_schema_version,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.cw_strategy import StrategySession


class LoopOutcomeKind(enum.Enum):
    """循环出口种类(值出口;到 SrOperation 轮次语义的映射归批③适配器)。"""

    BATTLE = 'battle'                    # 出战成功(环正常出口)
    BATTLE_FORCED = 'battle_forced'      # F5 强制出战(步数预算/stall 门)
    BAIL = 'bail'                        # 环让位外环
    PINGPONG_STOP = 'pingpong_stop'      # 同因 bail≥3 停机(ping-pong 安全网)
    BRAKE_STOPPED = 'brake_stopped'      # W209j 刹车(停机标志已设,收口不发动作)
    EVIDENCE_STOP = 'evidence_stop'      # 分类不 confident 有界重试耗尽,留证停机
    FAIL = 'fail'                        # 策略异常/执行异常等环失败


@dataclass(frozen=True)
class LoopOutcome:
    """循环出口值:frozen dataclass(kind + reason)。"""

    kind: LoopOutcomeKind
    reason: str = ''


@dataclass(frozen=True)
class _DirectorPorts:
    """外部交互端口集(构造期注入;全部必填,禁默认实现——接线缺失显式炸)。"""

    decide: Callable[[Snapshot, StrategySession], Decision]
    observe: Callable[[bool], Snapshot]              # heavy=True 结构重观察
    execute: Callable[[AtomOp], tuple[bool, str]]    # (progressed, detail)
    recover: Callable[[], bool]                      # 恢复原语;返回是否关过已知弹层
    force_battle: Callable[[], bool]                 # F5 强制出战
    is_stopped: Callable[[], bool]                   # W209j 刹车判据(现读,不缓存)
    stop_with_evidence: Callable[[str], None]        # 留证停机接口位(本批注入点)
    record_defect: Callable[[str, str], None]        # 框架异常面缺陷台账


class DirectorV2:
    """备战决策循环引擎(纯逻辑,可离线驱动;生命周期六件套所有者)。

    六件套计数载体与清零时机(权威表 = ADR-0458,与 prep_director 现役逐件对照):
    1 步数预算 ``_steps``:环入口清零;2 stall ``_stall``:环入口清 + 任一 op
    progressed 即清;3 连败链 ``_fail_counts/_blocked/_recovered``:环入口重建 +
    恢复发放/屏蔽落定各清 fail_counts[key](recovered/blocked 环内存活);
    4 ``session.defer_count``:环入口清、步间不清、失败链 ``max`` 抬升;
    5 ``session.bail_reason_counts``:**只增不清**(局级,唯一清零点 = 外环
    handler 成功消化,职责在 battle_loop,本模块不迁);6 W209j 刹车:非计数,
    双查点(环顶每步 + execute 前)现读 ``is_stopped`` 端口。
    """

    # 环级预算常量(值与现役 prep_director 同源;批③切换前旧值为单一源,本处
    # 复制并在此注明;CONF_RETRY_LIMIT = 分类有界重试上限,对齐 gate 3-strike)。
    MAX_STEPS: int = 60
    STALL_LIMIT: int = 5
    FAIL_TO_RECOVER: int = 2
    BAIL_SAME_REASON_DIAG: int = 3
    CONF_RETRY_LIMIT: int = 3

    def __init__(self, ports: _DirectorPorts) -> None:
        self._p = ports
        # 环级计数(run() 重入即重建;局级态只在 session,引擎不持有)
        self._steps = 0
        self._stall = 0
        self._fail_counts: dict[str, int] = {}
        self._blocked: set[str] = set()
        self._recovered: set[str] = set()
        self._recovery_tried = False
        self._recovery_closed_known: dict[str, bool] = {}

    # ------------------------------------------------------------------ run

    def run(self, session: StrategySession) -> LoopOutcome:
        """环主体:环入口清零 → 观察 → decide/execute 循环 → 出口值。"""
        # —— 环入口计数清零(权威表 ADR-0458 件 1/2/3/4;bail 局级计数不清)——
        session.defer_count = 0
        session.prep_phase = 0
        self._steps = 0
        self._stall = 0
        self._fail_counts = {}
        self._blocked = set()
        self._recovered = set()
        self._recovery_tried = False
        self._recovery_closed_known = {}
        conf_retry = 0   # 分类不 confident 的连续重试计数(环内)

        snapshot = self._p.observe(heavy=True)
        if snapshot.event_overlay is not None:
            return self._bail(session, f'事件overlay:{snapshot.event_overlay}')

        while True:
            # —— W209j 刹车·查点 1(环顶每步):停机标志已设 → 立即收口,
            # 不再发任何动作(停机后仍发出战按钮的事故防线,ADR-0388)。
            if self._p.is_stopped():
                return LoopOutcome(LoopOutcomeKind.BRAKE_STOPPED, '停机标志已设')
            self._steps += 1
            if self._steps > self.MAX_STEPS:
                self._p.force_battle()
                return LoopOutcome(LoopOutcomeKind.BATTLE_FORCED, '步数预算耗尽')

            # —— schema_version 执行点(唯一指定写入点,契约
            # require_schema_version):版本不匹配显式抛错,禁静默回退。
            # 入口快照与本环内全部重观察结果都流经环顶,单查点全覆盖。
            require_schema_version(snapshot)

            # —— 分类可信度门(W583 Schema §三):非 confident 不进 decide,
            # 有界重试(重观察)→ 耗尽 → 留证停机接口位。分类错误 = decide 的
            # 世界模型错 = 全链错,必须显式暴露而非静默(结构性实证:分类锚对
            # 真值帧可整批失配,ADR-0269 前因)。
            if not snapshot.classification.confident:
                conf_retry += 1
                if conf_retry <= self.CONF_RETRY_LIMIT:
                    snapshot = self._p.observe(heavy=True)
                    continue
                self._p.stop_with_evidence(
                    f'分类不confident×{conf_retry}'
                    f'(name={snapshot.classification.name},'
                    f'evidence={",".join(snapshot.classification.evidence) or "无"})')
                return LoopOutcome(LoopOutcomeKind.EVIDENCE_STOP,
                                   f'分类不confident×{conf_retry}')
            conf_retry = 0

            try:
                decision = self._p.decide(snapshot, session)
            except Exception as e:  # noqa: BLE001  策略异常:本环 fail(对齐现役)
                return LoopOutcome(LoopOutcomeKind.FAIL, f'策略决策异常: {e}')

            # —— 控制流通道(不经 execute 验证链;control 与 ops 同发时
            # control 优先 + 记缺陷,契约 Decision 注释的框架语义)——
            if decision.control is not None and decision.ops:
                self._p.record_defect(
                    'control_with_ops',
                    f'control={type(decision.control).__name__} '
                    f'与 {len(decision.ops)} 个 op 同发 → control 优先')
            if isinstance(decision.control, Defer):
                session.defer_count += 1   # 门=2 由策略读;框架只计(契约注释)
                snapshot = self._p.observe(heavy=False)   # 控制流走轻观察(现役同)
                continue
            if isinstance(decision.control, Bail):
                return self._bail(session, decision.control.reason or '未注明')

            # —— 批语义(W561 攻击6 修法):限同域 + fail-stop + 批内轻观察
            # 批尾 heavy。空批 = 合法「本步零进展」,计 stall(W561 攻击1 修法1:
            # decide 返回空不设防线 = 活锁重灾区)。
            if not decision.ops:
                self._stall += 1
                gate = self._stall_gate()
                if gate is not None:
                    return gate
                snapshot = self._p.observe(heavy=False)
                continue
            if len({op.domain for op in decision.ops}) > 1:
                self._stall += 1   # MED-3:拒绝路径同样过 stall 门
                gate = self._stall_gate()
                if gate is not None:
                    return gate
                snapshot = self._p.observe(heavy=False)
                continue

            aborted = False
            for i, op in enumerate(decision.ops):
                key = op.op_key
                # 屏蔽命中:拒绝执行 + 计 stall(确定性重提案防线;屏蔽集生命周期
                # = 本环。现役 StartBattle 豁免属动作类型知识,新契约无出战类 op,
                # 豁免条目挂批③对账——见 ADR-0458「批③挂账」)。
                if key in self._blocked:
                    self._stall += 1
                    gate = self._stall_gate()
                    if gate is not None:
                        return gate
                    aborted = True   # 批中止(fail-stop 同型:余下 op 丢弃)
                    break
                # —— W209j 刹车·查点 2(execute 前):op 已出 decide 未落地,
                # 停机标志现读(双查点之二是「停机后仍落地动作」的精确防线)。
                if self._p.is_stopped():
                    return LoopOutcome(LoopOutcomeKind.BRAKE_STOPPED, '停机标志已设')
                try:
                    progressed, _detail = self._p.execute(op)
                except Exception as e:  # noqa: BLE001  执行异常:本环 fail(现役同)
                    return LoopOutcome(LoopOutcomeKind.FAIL, f'执行异常 {key}: {e}')
                if progressed:
                    # 零进展链断点:stall 清零 + per-key 连败清零(权威表件 2/3)
                    self._stall = 0
                    self._fail_counts.pop(key, None)
                else:
                    result = self._on_fail(op, session)
                    if result is not None:
                        return result
                    aborted = True   # fail-stop:批中止,余下 op 丢弃并经快照回报
                    break
                # 批内轻观察,批尾 heavy(单 op 批 = 批尾 heavy,行为等价现役
                # 「每执行一个游戏动作 → heavy 重观察」)。
                snapshot = self._p.observe(heavy=(i == len(decision.ops) - 1))
            if aborted:
                # 中止批:批尾未达 → 此处补 heavy 重观察(失败/拒绝后状态未知,
                # 对齐现役失败路径也 heavy 的口径)。
                snapshot = self._p.observe(heavy=True)
            # 动作后浮出事件 overlay(mid-prep 弹出挡操作)→ 环让位外环(现役同)
            if snapshot.event_overlay is not None:
                return self._bail(session, f'事件overlay:{snapshot.event_overlay}')

    # ------------------------------------------------------- 生命周期机制(私有)

    def _stall_gate(self) -> LoopOutcome | None:
        """环级强制出战门:stall≥STALL_LIMIT 且恢复已试尽 → F5(MED-3:所有计
        stall 路径统一过本门,防屏蔽后确定性重提案空转到步数预算才兜住)。"""
        if self._stall >= self.STALL_LIMIT and self._recovery_tried:
            self._p.force_battle()
            return LoopOutcome(LoopOutcomeKind.BATTLE_FORCED, 'stall+恢复试尽')
        return None

    def _on_fail(self, op: AtomOp, session: StrategySession) -> LoopOutcome | None:
        """执行失败链:连败计数 → 恢复原语(一次/op_key)→ 仍败分型(关过已知
        弹层 = 弹层顽固 → bail 交外环;无弹层 = 状态类 → 屏蔽,策略须换路)。

        类型特判不迁框架(规则中立):现役 ClickSpheres 例外、defer 门 max 抬升、
        DeployMove 失败记忆均按动作类型分支 = 策略/规则侧知识,归批③经
        session.reject_ledger 回灌(W561 攻击4 修法的通用化通道)。
        """
        key = op.op_key   # 屏蔽/幂等键(契约 AtomOp;失败链全按 key 记)
        self._fail_counts[key] = self._fail_counts.get(key, 0) + 1
        fails = self._fail_counts[key]
        self._stall += 1   # 失败 = 零进展,计 stall(件 2「不清」侧)
        if fails >= self.FAIL_TO_RECOVER and key not in self._recovered:
            # 首次连败门:恢复原语一次/实例,清连败计数给恢复后重试窗
            # (不清 = 恢复即永久屏蔽,权威表件 3 清零点②)。
            closed_known = self._p.recover()
            self._recovered.add(key)
            self._recovery_closed_known[key] = closed_known
            self._recovery_tried = True
            self._fail_counts[key] = 0
            return None
        if fails >= self.FAIL_TO_RECOVER and key in self._recovered:
            # 恢复后仍连败(恢复无效)→ 分型:关过已知弹层 = 弹层顽固(游戏侧
            # 阻塞未消)→ bail 交外环弹层分支;无已知弹层 = 状态/识别类 → 本环
            # 屏蔽(策略换路)。屏蔽落定清连败计数:屏蔽后同 key 重提案走
            # 「拒绝 + stall」路径,残留计数会重复触发恢复分支(权威表件 3
            # 清零点③;recovered/blocked 本身不清,环内存活)。
            if self._recovery_closed_known.get(key, False):
                return self._bail(session, f'恢复无效-弹层:{key}')
            self._blocked.add(key)
            self._fail_counts[key] = 0
            return self._stall_gate()
        return self._stall_gate()

    def _bail(self, session: StrategySession, reason: str) -> LoopOutcome:
        """环让位:同因计数只增不清(局级);同因 ≥3 = 外环 3 次未消化该因
        (bail↔重入 ping-pong)→ 留证停机接口位(ping-pong 安全网,常驻语义;
        清零唯一时点 = 外环 handler 成功消化,职责在 battle_loop 不在本模块)。"""
        counts = session.bail_reason_counts
        counts[reason] = counts.get(reason, 0) + 1
        n = counts[reason]
        if n >= self.BAIL_SAME_REASON_DIAG:
            self._p.stop_with_evidence(f'同因 bail ×{n}: {reason}(ping-pong)')
            return LoopOutcome(LoopOutcomeKind.PINGPONG_STOP,
                               f'同因 bail ×{n}({reason}) 停机待建档')
        return LoopOutcome(LoopOutcomeKind.BAIL, reason)
