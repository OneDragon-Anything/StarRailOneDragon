"""实验多路复用层 v0(redesign 29 号;ADR-0196):注册表+兼容性矩阵+窗口调度。

**诊断(29 号)**:消化终态堆积 400-600 局实机验证债(月-季度串行);每轮判据默认
「一局一判据」——无人意识到一局可同时偿还多笔判据。真正互斥的只有行为层(切流/臂/
参数/注入/对照 ≤5 域),shadow/passive/perception 三层天然全兼容。

**v0 落地**(纯函数,离线;29 号 §2 四件套最小闭环):
- ``ExperimentSpec``:注册即冻结(exp_id/claim/kind[shadow|active|passive|perception]/
  behavior_set/metrics/n_runs/deadline/status);
- ``compatible``:行为域正交判定(behavior_set 不相交 + 排斥声明);
- ``schedule_package``:局前贪心调度(信息价值×deadline 紧迫×局数残差排序,依次装入
  正交项;队列 <3 直通);**最坏退化=现状**(全互斥时退化为串行队列);
- ``pollution_check``:污染哨兵(同包内 metrics 交集 → 声明排斥显式记账,不静默)。

J1(测试+脚本):债务表登记 → ≥70% 全兼容类、行为域 ≤5;
J2:队列仿真,同 100 局预算分层重叠 vs 串行 FIFO,完成判据数 ≥3×。
"""
from __future__ import annotations

from dataclasses import dataclass

KINDS = ('shadow', 'active', 'passive', 'perception')


@dataclass(frozen=True)
class ExperimentSpec:
    """一个验证需求(登记即冻结,20 号预注册方法论)。"""

    exp_id: str
    claim: str
    kind: str                       # KINDS 之一
    behavior_set: frozenset[str]    # 行为改动集(触碰的模块/开关/参数)
    metrics: tuple[str, ...]        # 因变量
    n_runs: int                     # 统计需求
    deadline: int | None = None     # run 序 deadline(超时强制裁决)
    info_value: float = 1.0         # 信息价值/局(J1 排序输入;34 号预算表供给)
    excludes: frozenset[str] = frozenset()   # 显式排斥(统计前提被破坏的 exp_id)
    status: str = 'queued'


def compatible(a: ExperimentSpec, b: ExperimentSpec) -> bool:
    """可同局叠加 ⟺ 行为域不相交 + 无显式排斥 + (active 与任何 active 才互斥检查;
    shadow/passive/perception 类行为集为空,天然兼容)。"""
    if b.exp_id in a.excludes or a.exp_id in b.excludes:
        return False
    if not a.behavior_set or not b.behavior_set:
        return True
    return not (a.behavior_set & b.behavior_set)


def schedule_package(queue: list[ExperimentSpec], run_index: int) -> list[str]:
    """局前调度:贪心装正交包。

    排序键 = info_value × deadline 紧迫(deadline 差 ≤5 局 ×3,≤15 局 ×2,否则 ×1)
    × 局数残差(已完成局数越少越优先——v0 由调用方在 metrics 回填侧累计,此处用排队序)。
    队列 <3 → 直通全排(不做无谓调度);全互斥 → 单实验(退化=串行现状)。
    """
    live = [e for e in queue if e.status in ('queued', 'running')]
    if len(live) < 3:
        return [e.exp_id for e in live]

    def _urgency(e: ExperimentSpec) -> float:
        u = e.info_value
        if e.deadline is not None:
            d = e.deadline - run_index
            if d <= 5:
                u *= 3.0
            elif d <= 15:
                u *= 2.0
        return u

    ordered = sorted(live, key=lambda e: -_urgency(e))
    packed: list[ExperimentSpec] = []
    for e in ordered:
        if all(compatible(e, p) for p in packed):
            packed.append(e)
    return [e.exp_id for e in packed]


def pollution_check(pkg: list[ExperimentSpec]) -> list[dict]:
    """污染哨兵:同包内 metrics 交集(共因变量)= 潜在 block 污染,显式记账。"""
    flags: list[dict] = []
    for i, a in enumerate(pkg):
        for b in pkg[i + 1:]:
            shared = set(a.metrics) & set(b.metrics)
            if shared:
                flags.append({'pair': (a.exp_id, b.exp_id),
                              'shared_metrics': sorted(shared),
                              'note': '共因变量:block 效应须分层检验,判据按局聚类'})
    return flags


# ===== J1 债务登记(29 号 §1 表的 15 项映射) =====
DEBT_LEDGER: tuple[ExperimentSpec, ...] = (
    ExperimentSpec('horizon_v5', '03 切流不劣于手写门族', 'active',
                   frozenset({'horizon_seam'}), ('win_rate',), 40, info_value=3.0),
    ExperimentSpec('horizon_shadow', '03 影子 diff 常开', 'shadow',
                   frozenset(), ('goal_diff',), 50),
    ExperimentSpec('bundle_p3', '06 P3 校准 A/B', 'active',
                   frozenset({'bundle_seam'}), ('win_rate', 'formation_score'), 30),
    ExperimentSpec('belief_k0', '04 可靠性表采集', 'passive',
                   frozenset(), ('belief_residual',), 25),
    ExperimentSpec('allocator_tel', '05 telemetry 接线', 'passive',
                   frozenset(), ('adherence',), 30),
    ExperimentSpec('equip_m7', '07 M7 切流', 'active',
                   frozenset({'equip_seam'}), ('win_rate',), 30),
    ExperimentSpec('formation_f1', '08 影响量级审计', 'shadow',
                   frozenset(), ('formation_delta',), 25),
    ExperimentSpec('sovereignty_k0', '09 前提验证', 'shadow',
                   frozenset(), ('residual', 'confidence'), 30),
    ExperimentSpec('dossier_sift', '15 敌方 SIFT 采集', 'perception',
                   frozenset(), ('sift_hits',), 30),
    ExperimentSpec('pool_p0', '16 池定案', 'shadow',
                   frozenset(), ('pool_ll',), 40),
    ExperimentSpec('tribunal_j1', '20 影子回放', 'shadow',
                   frozenset(), ('verdict_rate',), 50),
    ExperimentSpec('portfolio_t1', '21 对拍', 'shadow',
                   frozenset(), ('hold_value',), 35),
    ExperimentSpec('cEM_j3', '24 冠军真局证伪', 'active',
                   frozenset({'weight_vector'}), ('win_rate',), 30, info_value=2.5),
    ExperimentSpec('exec_tel', '27 执行遥测', 'passive',
                   frozenset(), ('op_latency', 'fail_rate'), 90),
    ExperimentSpec('l1_screen', '19 结算屏建档(硬门,解锁伤害账本全部下游)', 'perception',
                   frozenset(), ('ocr_read_rate',), 50, info_value=4.0),
    # 排斥例:23 漂移注入破坏 18 λ 判据(统计前提)
    ExperimentSpec('drift_inject', '23 常数漂移注入', 'active',
                   frozenset({'injector'}), ('attribution',), 20,
                   excludes=frozenset({'lambda_j0'})),
    ExperimentSpec('lambda_j0', '18 λ 估计判据', 'passive',
                   frozenset(), ('lambda_hp',), 30,
                   excludes=frozenset({'drift_inject'})),
)


def debt_audit(ledger: tuple[ExperimentSpec, ...] = DEBT_LEDGER) -> dict:
    """J1:债务分类审计——全兼容类(shadow/passive/perception)占比(预期 ≥70%)+
    行为域数(预期 ≤5)。"""
    compat = [e for e in ledger if e.kind in ('shadow', 'passive', 'perception')]
    active = [e for e in ledger if e.kind == 'active']
    domains: set[str] = set()
    for e in active:
        domains |= e.behavior_set
    return {'n_total': len(ledger), 'n_compatible': len(compat),
            'compatible_share': round(len(compat) / len(ledger), 3),
            'behavior_domains': sorted(domains),
            'n_domains': len(domains),
            'j1_verdict': ('pass' if len(compat) / len(ledger) >= 0.7 and len(domains) <= 5
                           else 'fail')}
