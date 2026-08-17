"""策略知识编译层 v0(redesign 11 号;ADR-0201):规则数据模型 + 确定性编译管线。

**诊断(11 号)**:87 条语义绑定等「知识表」三无产品(无出处/无证据/无生命周期);
消费端越建越强,供给侧没动——「知识=代码」让每条经验永久不可检验。

**v0 落地**(纯函数,离线;11 号 §2.1/§2.2 的确定性部分):
- ``StrategyRule``:八域 scope + 受限条件 DSL(编译期静态校验,引不到实体直接拒绝)+
  五类 prescription(gate/modulator/ordering/prior/posture)+ 逐条出处 + 证据
  (支持篇数/credibility 加权/反例/版本戳)+ 四层 TrustTier(user 最高)+
  生命周期(candidate→active→degraded→retired);
- ``compile_rules``:管线 ②③④(确定性,无 LLM)——同条件跨篇归并(证据计数)/
  同条件反处方不平均·按上下文标签分叉或进人审队列/证据达阈分层;
- ①抽取(离线 LLM 批处理)与 ⑤人审门为工具链批次;user-tier 口述通道挂用户协同。

「知识=数据」:可追溯/可触发统计/可被模型推导检验推翻——推翻是降级一条数据而非返工。
"""
from __future__ import annotations

from dataclasses import dataclass, field

SCOPES = ('economy', 'tempo', 'pivot', 'star_chain', 'equip', 'trial', 'bench',
          'event', 'formation')
PRESCRIPTIONS = ('gate', 'modulator', 'ordering', 'prior', 'posture')
TIERS = ('user', 'derived_validated', 'guide_high', 'guide_low')
STATUSES = ('candidate', 'active', 'degraded', 'retired')

# 条件 DSL 允许的 GameState 字段(白名单;编译期静态校验)
CONDITION_FIELDS = ('hp', 'gold', 'level', 'plane', 'round_num', 'streak',
                    'node_type', 'target_comp', 'has_trial_unit')


@dataclass(frozen=True)
class Condition:
    """受限条件 DSL:字段 + 比较 + 上下文标签(引不到实体的条件编译期拒绝)。"""

    field: str
    op: str                  # 'lt' | 'gt' | 'eq' | 'in' | 'has_tag'
    value: object = None
    context_tag: str = ''    # 上下文分叉标签(护盾流/减益流各有各的规矩)


@dataclass(frozen=True)
class Src:
    """一条出处(逐条溯源)。"""

    kind: str        # 'plaza' | 'user' | 'telemetry'
    ref: str         # post id / session 日期 / run id
    quote: str = ''  # 原话引文(plaza/user 必带)


@dataclass(frozen=True)
class Evidence:
    """证据结构。"""

    n_support: int = 1
    n_counter: int = 0
    credibility: float = 1.0    # ln(1+use) 加权
    version: str = 'V4.4'


@dataclass
class StrategyRule:
    """一条结构化策略知识(知识=数据)。"""

    rule_id: str
    scope: str
    condition: Condition
    prescription: tuple[str, str]    # (类型, 指令)
    provenance: tuple[Src, ...] = ()
    evidence: Evidence = field(default_factory=Evidence)
    tier: str = 'guide_low'
    lifecycle: str = 'candidate'
    consumers: tuple[str, ...] = ()


def validate_condition(cond: Condition) -> bool:
    """编译期静态校验:字段在白名单 + 算子合法。"""
    return (cond.field in CONDITION_FIELDS
            and cond.op in ('lt', 'gt', 'eq', 'in', 'has_tag'))


def rule_key(r: StrategyRule) -> tuple:
    """归并键:同 condition(+上下文标签)+ prescription 视为同一知识。"""
    return (r.condition.field, r.condition.op, str(r.condition.value),
            r.condition.context_tag, r.prescription)


def compile_rules(rules: list[StrategyRule]) -> dict:
    """管线 ②③④(确定性):归并 → 冲突检测(不平均,分叉或人审)→ 分层。

    冲突定义:同 condition(含上下文标签)但 prescription 不同。
    分层:evidence.n_support ≥3 且 credibility 达阈 → guide_high;单帖 guide_low
    (只候选不生效);user 源直入 user tier(最高信度)。
    """
    merged: dict[tuple, StrategyRule] = {}
    conflicts: list[tuple[StrategyRule, StrategyRule]] = []
    for r in rules:
        if not validate_condition(r.condition):
            continue   # schema 违例即弃
        k = rule_key(r)
        if k in merged:
            m = merged[k]
            # 归并:证据计数 + 出处并
            m.evidence = Evidence(
                n_support=m.evidence.n_support + r.evidence.n_support,
                n_counter=m.evidence.n_counter + r.evidence.n_counter,
                credibility=m.evidence.credibility + r.evidence.credibility,
                version=m.evidence.version)
            m.provenance = m.provenance + r.provenance
        else:
            # 同条件(含标签)反处方 → 冲突(不平均!)
            same_cond = [x for kx, x in merged.items()
                         if (x.condition.field, x.condition.op, str(x.condition.value),
                             x.condition.context_tag)
                         == (r.condition.field, r.condition.op, str(r.condition.value),
                             r.condition.context_tag)
                         and x.prescription != r.prescription]
            if same_cond:
                conflicts.append((same_cond[0], r))
            merged[k] = r
    # 分层
    for r in merged.values():
        if any(s.kind == 'user' for s in r.provenance):
            r.tier = 'user'
        elif r.evidence.n_support >= 3 and r.evidence.credibility >= 3.0:
            r.tier = 'guide_high'
        else:
            r.tier = 'guide_low'
    return {'rules': list(merged.values()), 'n_conflicts': len(conflicts),
            'conflicts': conflicts}
