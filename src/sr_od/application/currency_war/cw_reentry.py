"""重入层 v0(redesign 31 号;ADR-0198):journal 四族词表 + 纯投影 + 三级重入语义。

**诊断(31 号)**:世界态接手已解决,策略态失忆零投入——StrategySession「每局新建,
局终销毁」;重启丢 target_comp/tracked_bench/active_strategies/20 预注册/22 批准/15 个
影子模块 session 态。telemetry 是胚胎(enabled=False 生产关/词表只有决策迹/零消费)——
「死档案」不是「事实源」。14/28/13/29 的输入结构上不存在。

**v0 落地**(纯函数,离线;31 号 §2.1/§2.2/§2.3 核心):
- ``JournalEvent``:四族词表(动作/观测/外生/随机数消费)+ projection_version pinning;
- ``project``:journal 前缀 → 状态纯投影(world_state 字段重导;对账=投影内部推导规则);
- ``reentry_level``:三级判定(热=journal 完整/温=有缺口/冷=无 journal);
- 架构纪律:任何模块不得持有不可重导的隐藏可变状态——要么投影,要么显式事件。

J1(测试):合成 journal 热重入逐字段精确恢复;温重入缺口检测+加宽语义(信念变宽非变准);
随机数消费重放决定性。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

# 四族事件词表(封闭;扩词走版本 bump)
EVENT_FAMILIES = ('action', 'observation', 'exogenous', 'rng')
PROJECTION_VERSION = 1


@dataclass(frozen=True)
class JournalEvent:
    """一条 journal 事件(一等事实源;run_id+round 为 join 键)。"""

    family: str          # EVENT_FAMILIES 之一
    kind: str            # 族内类型(如 'action:BuyCard' / 'obs:gold' / 'exo:crash' / 'rng:draw')
    run_id: str
    round_num: int
    payload: dict = field(default_factory=dict)
    projection_version: int = PROJECTION_VERSION


def project(events: list[JournalEvent]) -> dict:
    """journal 前缀 → world_state 投影(纯函数;增量投影=追加重导,等价现状性能)。

    world_state 字段从事件重导:gold/hp/level/plane 以最后观测值为准(obs 事件);
    bench/deployed/board 由 action 事件重放;rng 序号计数。缺某族 = 字段缺省(显式,
    不假装知道)。
    """
    world: dict = {'gold': None, 'hp': None, 'level': None, 'plane': None,
                   'bench': [], 'deployed': [], 'board': {}, 'rng_consumed': 0,
                   'last_round': 0}
    for e in events:
        world['last_round'] = max(world['last_round'], e.round_num)
        if e.family == 'observation':
            for k in ('gold', 'hp', 'level', 'plane'):
                if k in e.payload:
                    world[k] = e.payload[k]
        elif e.family == 'action':
            kind = e.kind.split(':', 1)[-1]
            if kind == 'BuyCard':
                world['bench'] = world['bench'] + [e.payload.get('char', '')]
            elif kind == 'SellBench':
                idx = e.payload.get('bench_idx')
                if isinstance(idx, int) and 0 <= idx < len(world['bench']):
                    world['bench'] = world['bench'][:idx] + world['bench'][idx + 1:]
            elif kind == 'DeployMove':
                idx = e.payload.get('bench_idx')
                if isinstance(idx, int) and 0 <= idx < len(world['bench']):
                    ch = world['bench'][idx]
                    world['bench'] = world['bench'][:idx] + world['bench'][idx + 1:]
                    world['deployed'] = world['deployed'] + [ch]
                    fac = e.payload.get('faction', '?')
                    world['board'][fac] = world['board'].get(fac, 0) + 1
        elif e.family == 'rng':
            world['rng_consumed'] += 1
    return world


def reentry_level(events_by_round: dict[int, list[JournalEvent]],
                  current_round_reported: int) -> str:
    """三级重入判定:热(journal 完整至当前)/温(有缺口)/冷(空 journal)。

    缺口 = current_round_reported 超出 journal 覆盖的 max round ≥1(人代打了 N 回合)。
    """
    if not events_by_round:
        return 'cold'
    j_max = max(events_by_round)
    if current_round_reported <= j_max:
        return 'hot'
    return 'warm'


def widen_beliefs_on_gap(gap_rounds: int) -> dict:
    """温重入加宽语义:人的 D 牌/买入不可观测 → 缺席证据不可记,分布加宽
    (诚实原则:重入后信念变宽,不是变准)。v0 返回加宽参数(消费端 04/16 接)。"""
    return {'gap_rounds': gap_rounds,
            'pool_variance_multiplier': 1.0 + 0.15 * gap_rounds,
            'note': '缺席证据不可记;分布加宽非假装知道'}


def replay_rng(seed: int, n_consumed: int) -> random.Random:
    """随机数消费重放:session 种子 + 已消费序号 → 恢复到断点的 rng 流
    (决定性重放前提;重放 n 次 dummy draw)。"""
    rng = random.Random(seed)
    for _ in range(n_consumed):
        rng.random()
    return rng
