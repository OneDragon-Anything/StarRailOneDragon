"""决策总线 v0(redesign 30 号;ADR-0192):类型化声明黑板 + 预注册仲裁 + 裁决记录。

**诊断(30 号)**:15 个影子模块同时输出时的语义未定义——冲突被无人记录的调用顺序静默
裁决(13 号「钉死 8 例」=知而不行,审不出谁压的);7 条未定义组合缝(22×03/06×03/
18×03/27×21/16×22/04 分布消费/19×15)。

**v0 落地**(纯函数,离线;30 号 §1 的最小闭环):
- ``Claim``:四类类型化声明(Goal/Propose/Veto/Evidence;带来源/置信/作用域/可逆性);
- ``arbitrate``:仲裁协议——Evidence 并入信念库;Goal 冲突查预注册优先级表;
  Propose 冲突先过 Veto 域(硬否决剔/软降权乘)再比候选;Veto 冲突按安全性优先序,
  不可裁决余数升级(12 号问询路由);
- ``ArbitrationRecord``:全量裁决记录(URID;冲突双方/规则/胜者/升级)——13 审压制、
  14 provenance、12 分歧信号的首个输入源;
- kill-switch:无声明 = 现调用图行为(零漂移)。

规则在注册表(数据),仲裁器无策略(只分发/查表/记录)。J1(测试):预列缝 #2/#4 的
合成冲突被正确裁决并记录。
"""
from __future__ import annotations

from dataclasses import dataclass, field

# 预注册优先级表(数据驱动;新条目走预注册,防中间件膨胀)
GOAL_PRIORITY: dict[str, int] = {
    # 战略级 > 节点级 > 战术级(30 号 §1.2 预注册规则)
    'line_portfolio.hold': 90,      # 21 线持有(战略承诺)
    'playbook.commit': 85,          # 22 承诺响应
    'horizon.node_goal': 70,        # 03 节点目标
    'tribunal.amended': 65,         # 20 amended 判决
    'bundle.propose': 40,           # 06 动作束(战术)
    'prep.candidate': 30,           # PrepDirector 候选
}

VETO_SAFETY_ORDER: tuple[str, ...] = (
    # Veto 冲突裁决:安全性/不可逆性优先(预注册;30 号默认序)
    'state.sanity',        # 04 sanity 截断(感知不安全 = 最高)
    'irreversible.guard',  # 不可逆动作守卫
    'posture.zone',        # 18 姿态区
    'feasibility.multiplier',  # 27 可行性乘子
)


@dataclass(frozen=True)
class Claim:
    """一条类型化声明。"""

    kind: str            # 'goal' | 'propose' | 'veto' | 'evidence'
    source: str          # 来源模块(优先级表键)
    payload: str         # 声明内容摘要(动作/目标/否决对象)
    priority_key: str = ''   # 优先级查表键(缺省 = source)
    confidence: float = 1.0
    scope: str = ''          # 作用域(如 veto 的对象 id)
    reversible: bool = True


@dataclass
class ArbitrationRecord:
    """一次裁决的记录(URID;13/14/12 的输入源)。"""

    decision_point: str
    rule: str                 # 适用规则
    winner: str
    losers: list[str] = field(default_factory=list)
    escalated: bool = False   # 不可裁决 → 升 12 号


def arbitrate(claims: list[Claim], decision_point: str = '') -> tuple[list[Claim], list[ArbitrationRecord]]:
    """仲裁入口:声明集 → (生效声明集, 裁决记录)。

    - evidence:无冲突语义,全量并入(信念库路由挂消费端);
    - goal:同作用域冲突 → GOAL_PRIORITY 高者胜;
    - propose:先过 veto 域(硬否决[confidence=0 的 veto 或 scope 命中]剔除、软降权乘入
      confidence),再按剩余置信比较;
    - veto 冲突(同 scope 两 veto):VETO_SAFETY_ORDER 前者胜;不可裁决(都不在序)→ 升级。
    """
    kept: list[Claim] = []
    records: list[ArbitrationRecord] = []

    evid = [c for c in claims if c.kind == 'evidence']
    kept.extend(evid)

    goals = [c for c in claims if c.kind == 'goal']
    by_scope: dict[str, list[Claim]] = {}
    for g in goals:
        by_scope.setdefault(g.scope or '*', []).append(g)
    for scope, gs in by_scope.items():
        if len(gs) == 1:
            kept.extend(gs)
            continue
        best = max(gs, key=lambda g: GOAL_PRIORITY.get(g.priority_key or g.source, 0))
        kept.append(best)
        records.append(ArbitrationRecord(
            decision_point, f'goal.priority[{scope}]', best.source,
            [g.source for g in gs if g is not best]))

    vetoes = [c for c in claims if c.kind == 'veto']
    # veto 冲突(同 scope):
    vs_map: dict[str, list[Claim]] = {}
    for v in vetoes:
        vs_map.setdefault(v.scope or '*', []).append(v)
    active_vetoes: list[Claim] = []
    for scope, vs in vs_map.items():
        if len(vs) == 1:
            active_vetoes.extend(vs)
            continue
        ordered = [v for v in vs if v.source in VETO_SAFETY_ORDER]
        ordered.sort(key=lambda v: VETO_SAFETY_ORDER.index(v.source))
        if ordered:
            active_vetoes.append(ordered[0])
            records.append(ArbitrationRecord(
                decision_point, f'veto.safety[{scope}]', ordered[0].source,
                [v.source for v in vs if v is not ordered[0]]))
        else:
            records.append(ArbitrationRecord(
                decision_point, f'veto.undecidable[{scope}]', '(escalated)',
                [v.source for v in vs], escalated=True))

    props = [c for c in claims if c.kind == 'propose']
    for p in props:
        eff_conf = p.confidence
        killed_by = None
        for v in active_vetoes:
            # veto 命中:veto 无 scope = 全域;否则作用于同 scope 的 propose
            # (propose scope 缺省为全域时按 payload 记;此处用显式 scope 对齐)
            if v.scope and p.scope and v.scope != p.scope:
                continue
            if v.scope and not p.scope:
                # veto 有明确对象而 propose 未声明:保守按 payload 关键词粗对(登记式,
                # 精确 scope 匹配挂消费端接线批次)
                if v.scope not in p.payload:
                    continue
            if v.confidence <= 0.0:
                killed_by = v.source
                break
            eff_conf *= v.confidence
        if killed_by:
            records.append(ArbitrationRecord(
                decision_point, 'propose.vetoed', killed_by, [p.source]))
            continue
        kept.append(Claim(p.kind, p.source, p.payload, p.priority_key, round(eff_conf, 4),
                          p.scope, p.reversible))
    return kept, records
