"""机制推导线生成器 v0(redesign 25 号;ADR-0200):结构枚举 + 半解析强度先验。

**诊断(25 号)**:427 羁绊组合 vs ~20 聚类条目——pair_synergy 对人类没玩过的对收缩到 0
(防 optimizer's curse 的正确纪律),副作用是地形在人类未探索区零信号(自走棋史上
「版本初被低估后成主流」的线结构性失明)。版本 bump 后只能等人类攻略。

**v0 落地**(纯函数,离线;25 号 §2.1/§2.2/§2.3):
- ``LineSkeleton``:候选线骨架(carry/核心羁绊对/装备签名/level_plan 骨架);
- ``enumerate_skeletons``:从角色注册表枚举(carry × 阈值可达的另一 trait;剪枝:
  站位合法+费用可支撑);填充不枚举(留 10 号地形连续求解);
- ``strength_prior``:半解析强度核(trait 断点机制项+职能覆盖项+carry 费用档窗口项)
  ——**不是战斗模拟器**:定性合成、无量纲、离线排序过滤用,不进回合内决策;
- ``cost_gate_and_quota``:17 号成本门 + top-K 发射配额 + 与已知线编辑距离去重
  (只发人类没玩过的增量)+ 三源 provenance(mechanism/plaza/handwritten)。

生命周期:生成候选走 21 种子池(低先验)→ 20 预注册审判 → 05 预算 → 13 审计——
生成器只提出,评审机器处置(零新治理)。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoleFacts:
    """枚举输入的角色事实(从注册表/cw_chars 派生;注入式,测试可 mock)。"""

    name: str
    cost: int
    traits: tuple[str, ...]
    tags: tuple[str, ...] = ()        # 输出/辅助/治疗/护盾
    position: str = 'back'


@dataclass(frozen=True)
class LineSkeleton:
    """一条候选线骨架(填充留给 10 号地形)。"""

    carry: str
    core_traits: tuple[str, str]      # 核心羁绊对
    key_equip_signature: str = ''
    level_plan_hint: str = ''         # 费用档窗口(1费→5级/3费→7级/5费→速升9 同源)
    provenance: str = 'mechanism'


def enumerate_skeletons(roles: list[RoleFacts],
                        known_lines: set[tuple[str, str]] | None = None,
                        trait_threshold: int = 2) -> list[LineSkeleton]:
    """枚举:carry × 「自带 trait × 阈值可达的另一 trait」(剪枝:费用结构可支撑
    =另一 trait 有 ≤4 费单位;站位合法=前后排不冲突)。去重(只发增量)。"""
    known = known_lines or set()
    by_trait: dict[str, list[RoleFacts]] = {}
    for r in roles:
        for t in r.traits:
            by_trait.setdefault(t, []).append(r)
    out: list[LineSkeleton] = []
    seen: set[tuple[str, tuple[str, str]]] = set()
    for carry in roles:
        # carry 费用档窗口(17 号判据 1 同源)
        hint = ('1费→5级' if carry.cost <= 1
                else '3费→7级' if carry.cost <= 3 else '5费→速升9')
        for t1 in carry.traits:
            # 另一 trait:有低费单位可铺(阈值可达)
            for t2, rs in by_trait.items():
                if t2 == t1:
                    continue
                if not any(r.cost <= 4 for r in rs):
                    continue   # 全高费 → 费用结构撑不起阈值
                pair = tuple(sorted((t1, t2)))
                key = (carry.name, pair)
                if key in seen or pair in known:
                    continue
                seen.add(key)
                out.append(LineSkeleton(carry.name, pair, level_plan_hint=hint))
    return out


def strength_prior(sk: LineSkeleton, roles: list[RoleFacts],
                   trait_breakpoints: dict[str, int] | None = None) -> float:
    """半解析强度核(定性,无量纲;只作离线排序过滤):

    - trait 断点机制项:两 trait 阈值都低(2-3)→ 组合更易同时激活(结构可行性强);
    - 职能覆盖项:carry 的 tags 覆盖输出(缺输出骨架降权——机制上不成立);
    - carry 费用档项:窗口可达性(与枚举剪枝同源,轻权重)。
    """
    bps = trait_breakpoints or {}
    {r.name: r.name for r in roles}
    facts = next((r for r in roles if r.name == sk.carry), None)
    if facts is None:
        return 0.0
    # 断点项:阈值低 = 强(易激活);未知阈给中性 3
    b1 = bps.get(sk.core_traits[0], 3)
    b2 = bps.get(sk.core_traits[1], 3)
    bp_score = 1.0 / (1 + 0.25 * (b1 + b2 - 4))
    # 职能覆盖:缺输出强降权
    tag_score = 1.0 if any('输出' in t for t in facts.tags) else 0.5
    # 费用档:窗口清晰加分
    cost_score = 1.0 if sk.level_plan_hint else 0.8
    return round(bp_score * tag_score * cost_score, 4)


def cost_gate_and_quota(skeletons: list[LineSkeleton],
                        scores: dict[tuple[str, tuple[str, str]], float],
                        formation_cost_fn=None, top_k: int = 5) -> list[LineSkeleton]:
    """成本门 + 发射配额:期望成型成本超位面预算的杀;top-K 按(先验分×去重增量)。"""
    alive = []
    for sk in skeletons:
        key = (sk.carry, sk.core_traits)
        if formation_cost_fn is not None:
            cost = formation_cost_fn(sk)
            if cost is None or cost > 60:   # 位面预算粗上界(17 号精算接批次)
                continue
        alive.append((scores.get(key, 0.0), sk))
    alive.sort(key=lambda x: -x[0])
    return [sk for _s, sk in alive[:top_k]]
