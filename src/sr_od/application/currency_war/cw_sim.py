"""货币战争 P1 全流程模拟器(公共测试基建)。

诚实性分层(哪些是真机制,哪些是校准模拟——每层可独立替换):
- **真代码层**:策略决策(`LineStrategy.update_target` + `decide_prep`,
  生产逻辑直接跑)、发牌概率(`cw_shop_odds.REFRESH_PROB`,游戏内
  OCR 权威表)、有限牌池(`POOL_COPIES_PER_CARD` 27/27/9/9/9,
  买走即减/卖出回池)、角色注册表(`CHARACTERS`)、升级 XP 表
  (`XP_TO_NEXT_LEVEL` + 买牌 4XP)。
- **校准模拟层**(参数有默认、可注入覆盖):
  开局 bench 构成(4 张,65% 1费/35% 2费——遥测校准);
  每轮收入(基础 5 + 息 + 连胜奖);
  战斗结算 `battle_delta/boss_delta`(25 局 HP 轨迹校准的二元
  方向模型:方向未立=流血,已立=小胜;**板深→胜率转化未建模**,
  已知缺口,后续版本补)。

用途:策略改动先过本模拟(A/B 对照),再上实机验证(40min/局)。
典型用法::

    from sr_od.application.currency_war.cw_sim import simulate_p1

    res = simulate_p1(seed=42, use_refresh=False)   # A/B 对照
    report = simulate_p1_batch(n=500)               # 批量统计
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from sr_od.application.currency_war.cw_chars import CHARACTERS
from sr_od.application.currency_war.cw_shop_odds import (
    POOL_COPIES_PER_CARD,
    REFRESH_PROB,
)
from sr_od.application.currency_war.cw_state import (
    XP_PER_BUY,
    XP_TO_NEXT_LEVEL,
    BenchChar,
    BuyCard,
    GameState,
    LevelUp,
    RefreshShop,
    SellBench,
    ShopCard,
)
from sr_od.application.currency_war.cw_strategy import StrategySession

# 开局 bench 构成(遥测校准:开局 4 张,1 费主导)
START_BENCH_COUNT: int = 4
START_BENCH_COST_WEIGHTS: tuple[tuple[int, float], ...] = ((1, .65), (2, .35))

# 收入模型(r305 真值接入:sim 与决策共用 cw_economy 单一源)
from sr_od.application.currency_war.cw_economy import streak_gold  # noqa: E402,F401

BASE_INCOME: int = 5
INTEREST_CAP: int = 5

# 战斗结算(25 局 HP 轨迹校准;方向=锁线/桥认领)
EARLY_WIN_DELTA: int = 2            # r1-r2 弱敌小胜
WIN_DELTAS: tuple[int, ...] = (2, 2, 0, -4)   # 方向已立的轮结算
LOSS_BASE: float = 7.0              # 未立方向的 r3 基础损
LOSS_PER_ROUND: float = 4.0         # 未立方向每多一轮加重(r7≈-23 对齐观测)
# r259 二次校准(139 轮干净差分):lv7 后段观测中位 -23(无方向)/
# -31(锁线晚的弱队),原 3.5 系数低估后段流血 → 提到 4.0。
# 方向分桶样本小(4-10)且与「发牌差的队锁线晚」混杂,方向二元模型
# 保留为 v1;后续样本攒够换「板深×方向×轮次」联合模型。
#
# r260(用户指路:节点类型必须分层)——**真实节点序列**来自实跑
# read_node_sequence 日志(nodeseq):每个位面的节点行是
# battle/encounter/reward/supply 混排(奖励/补给=零战力要求不掉血;
# 遭遇=战力要求高于普通甚至 boss,遭遇三四尤其)。真实观测形态:
# `battle battle encounter reward encounter reward` /
# `reward reward battle encounter supply battle encounter reward` /
# `... encounter encounter encounter reward`(三连遭遇)。
# 模拟逐局**随机采样节点序列**(类型分布对齐观测),替代旧
# 「每轮都是战斗」假设;遭遇轮结算强度对齐 boss 或更高。
NODE_TYPE_POOL: tuple[str, ...] = (
    'battle', 'battle', 'battle', 'battle',   # 战斗为主(~44%)
    'encounter', 'encounter',                 # 遭遇(~22%)
    'reward', 'reward', 'supply',             # 奖励/补给零战力(~33%)
)
# 遭遇结算强度 = boss 档 × 1.15(用户口述:遭遇三四可比 boss 难;
# 遭遇一/二较温和 → 取均值系数,模拟无法读档位时的近似)
ENCOUNTER_MULT: float = 1.15
BOSS_BY_DIR_ROUND: tuple[tuple[int, float, float], ...] = (
    # (方向建立轮上限, boss 基础损, 抖动幅度)
    (2, 14.0, 8.0),
    (4, 22.0, 8.0),
    (6, 30.0, 8.0),
    (99, 36.0, 10.0),
)


@dataclass
class SimResult:
    """单局模拟结果。"""

    seed: int
    dir_round: int = 99             # 方向(锁线/桥)建立轮;99=未建立
    final_hp: int = 0
    hp_trail: list[int] = field(default_factory=list)
    refreshes: int = 0
    level: int = 3
    locked_line: str | None = None
    bridge_id: str | None = None
    # r338 诊断基建:逐轮事件 (round, node_type, delta, dir_established)
    hp_events: list[tuple[int, str, int, bool]] = field(default_factory=list)
    # r341 诊断基建:逐轮板深(Σbench;deployed 上场在 sim 未
    # 建模——bench 即板深代理)——杠杆实验的观测端
    depth_trail: list[int] = field(default_factory=list)


class _Pool:
    """有限牌池(真机制):每卡剩余副本,买走即减、卖出回池;
    槽抽取 = REFRESH_PROB 定费用档 → 池内均匀。"""

    def __init__(self, rng: random.Random, max_cost: int = 3):
        self.rng = rng
        self.max_cost = max_cost
        self.copies: dict[str, int] = {
            name: POOL_COPIES_PER_CARD[ch.cost]
            for name, ch in CHARACTERS.items()
            if ch.cost and ch.cost <= max_cost
        }

    def draw_shop(self, level: int) -> list[ShopCard]:
        out: list[ShopCard] = []
        for i in range(5):
            dist = REFRESH_PROB.get(level, {})
            costs = [c for c in dist
                     if c <= self.max_cost and dist[c] > 0]
            if not costs:
                continue
            cost = self.rng.choices(
                costs, weights=[dist[c] for c in costs], k=1)[0]
            names = [n for n in self.copies
                     if CHARACTERS[n].cost == cost and self.copies[n] > 0]
            if not names:
                continue
            name = self.rng.choice(names)
            out.append(ShopCard(
                x=i, faction=(CHARACTERS[name].factions or ['散'])[0],
                name=name, cost=cost))
        return out

    def take(self, name: str) -> None:
        self.copies[name] = max(0, self.copies.get(name, 0) - 1)

    def ret(self, name: str) -> None:
        base = POOL_COPIES_PER_CARD.get(CHARACTERS[name].cost, 9)
        self.copies[name] = min(base, self.copies.get(name, 0) + 1)


def battle_delta(round_num: int, dir_round: int,
                 rng: random.Random) -> int:
    """普通战斗 HP 变化(校准层;方向二元模型)。"""
    if round_num <= 2:
        return EARLY_WIN_DELTA
    if dir_round <= round_num:
        return rng.choice(WIN_DELTAS)
    loss = LOSS_BASE + LOSS_PER_ROUND * (round_num - 3) \
        + rng.uniform(-3, 4)
    return int(-loss)


# r343 实机分布(31 局 outcomes 全量差分,645 轮):
# 逐 run 差分 battle -7.3 / boss -25.1 / encounter -12.2;
# **板深条件化**(decisions board join,深=Σ阵营人次):
# battle 深[6-8] -1.0 vs [3-5] -11.3 vs [15-17] -7.1(非单调,
# 深 12+ 才稳);boss 深15+ -23.7 vs 深12 -27.9。
# 池结构:{node_type: {depth_bucket: [Δ...]}}——sim 结算按
# 当轮实deep采样(经验分布,无参数假设)。
# r343(review E 注):池在进程内懒加载一次冻结——消费方是
# sim CLI(短命),新遥测数据要重跑进程生效。
# r343(review F/J):深度代理=可 deploy 件数(阵营 count≥2
# +引擎单件,capped by level)——对齐实机 _should_deploy。
_SIM_ENGINE_FACTIONS: frozenset[str] = frozenset(
    ('仙舟', '狼狩', '银河学者', '列车同行'))
_LIVE_DELTA_POOL: dict | None = None
_DEPTH_BUCKET_W: int = 3   # 板深分桶宽


def live_delta_pool() -> dict:
    """懒加载板深条件化实机 Δ 池;无数据退空(走旧模型)。"""
    global _LIVE_DELTA_POOL
    if _LIVE_DELTA_POOL is None:
        import json
        from pathlib import Path
        pool: dict = {}
        try:
            rep = Path('.debug/temp/currency_war/replay')
            # 该轮末 board 深度(同轮多行 decisions 取最后)
            boards: dict = {}
            for ln in (rep / 'decisions.jsonl').read_text(
                    encoding='utf-8').splitlines():
                if not ln.strip():
                    continue
                d = json.loads(ln)
                st = d.get('state') or {}
                b = st.get('board') or {}
                boards[(d.get('run_id'), d.get('plane'),
                        d.get('round_num'))] = sum(b.values())
            seqs: dict[str, list] = {}
            for ln in (rep / 'outcomes.jsonl').read_text(
                    encoding='utf-8').splitlines():
                if not ln.strip():
                    continue
                o = json.loads(ln)
                if o.get('hp_after') is None:
                    continue
                seqs.setdefault(o.get('run_id'), []).append(o)
            for run, seq in seqs.items():
                for a, b in zip(seq, seq[1:], strict=False):
                    k = (run, b.get('plane'), b.get('round_num'))
                    dep = boards.get(k)
                    if dep is None:
                        continue
                    nt = b.get('node_type') or ''
                    nt = {'普通战斗': 'battle', '遭遇': 'encounter',
                          '奖励': 'reward', '首领': 'boss',
                          '补给': 'supply'}.get(nt, nt)
                    bucket = min(dep // _DEPTH_BUCKET_W, 5) * _DEPTH_BUCKET_W
                    pool.setdefault(nt, {}).setdefault(bucket, []).append(
                        b['hp_after'] - a['hp_after'])
        except Exception:   # noqa: BLE001  离线/无数据 → 空池(走旧模型)
            pass
        _LIVE_DELTA_POOL = pool
    return _LIVE_DELTA_POOL


def live_delta_for(node_type: str, depth: int,
                   rng: random.Random) -> int | None:
    """按节点类型+板深取实机经验 Δ;无匹配桶 → None(调用方走旧模型)。

    r343(review E 修):邻桶回退只向**浅**侧(bucket-W)——
    深侧封顶 15 后 +W 是死码,且向深回退=偏乐观(深=掉血少)。
    """
    _map = live_delta_pool().get(node_type) or {}
    bucket = min(depth // _DEPTH_BUCKET_W, 5) * _DEPTH_BUCKET_W
    pool = _map.get(bucket)
    if not pool:
        pool = _map.get(bucket - _DEPTH_BUCKET_W)   # 浅侧回退
    return rng.choice(pool) if pool else None


def boss_delta(dir_round: int, rng: random.Random,
               multiplier: float = 1.0) -> int:
    """P1 boss(r9)HP 变化(校准层;按方向建立早晚分档)。

    multiplier>1 用于遭遇轮(用户口述:遭遇三四可比 boss 难)。"""
    for cap, base, jitter in BOSS_BY_DIR_ROUND:
        if dir_round <= cap:
            return int(-(base * multiplier
                         + rng.uniform(0, jitter)))
    return int(-(36.0 * multiplier + rng.uniform(0, 10.0)))


def sample_node_sequence(rng: random.Random) -> list[str]:
    """P1 节点序列(r306b 实证统计:25 开局帧众数表)。

    典型表(每帧读全,用户指路):reward/reward/battle/battle/
    supply/battle/encounter/reward/boss——slot1/2/4/7 全帧
    一致(25/25);**slot3/5/6 是变异位**(24/25、23/25、24/25
    主型,余为策略效果改节点:战斗→遭遇/补给)。
    用户定调:位面节点基本固定,特殊策略才改;实机以实时
    识别为权威,本表用于模拟骨架/策略预知(如 r7 遭遇→
    r6 备战破息)。"""
    seq = ['reward', 'reward', 'battle', 'battle', 'supply']
    # slot5(r6):battle 主(23/25),策略效果位
    seq.append(rng.choices(('battle', 'encounter'), (0.92, 0.08))[0])
    # slot6(r7):encounter 主(24/25)
    seq.append(rng.choices(('encounter', 'supply'), (0.96, 0.04))[0])
    seq.append('reward')
    seq.append('boss')
    return seq


def node_delta(node: str, round_num: int, dir_round: int,
               rng: random.Random) -> int:
    """按节点类型的 HP 变化(r260 分层):
    reward/supply 零战力要求 → 不掉血(小胜 +2 长线作战回血观测);
    battle → 方向二元模型;
    encounter → boss 档 × ENCOUNTER_MULT(档位不可观,均值近似);
    boss → boss 档。"""
    if node in ('reward', 'supply'):
        return EARLY_WIN_DELTA
    if node == 'encounter':
        return boss_delta(dir_round, rng, multiplier=ENCOUNTER_MULT)
    if node == 'boss':
        return boss_delta(dir_round, rng)
    return battle_delta(round_num, dir_round, rng)


def _direction_established(session: StrategySession) -> bool:
    """方向判据 = 策略自身认领(锁线/桥),与遥测 target 字段一致。"""
    return bool(session.locked_line or session.bridge_id)


def simulate_p1(seed: int, *, use_refresh: bool = True,
                strategy=None, session=None) -> SimResult:
    """单局 P1 模拟(决策跑真策略代码)。

    :param seed: 随机种子(同 seed 同局,可复现)
    :param use_refresh: False 时剔除 RefreshShop 动作(A/B 对照用)
    :param strategy: 注入策略(默认 LineStrategy;测试可换桩)
    :param session: 注入会话(默认新建;跨局复用场景可传)
    """
    from sr_od.application.currency_war.strategies.line_strategy import (
        LineStrategy,
    )
    rng = random.Random(seed)
    pool = _Pool(rng)
    nodes = sample_node_sequence(rng)   # r260:本局节点序列(9 项)
    strat = strategy or LineStrategy()
    st = GameState()
    st.plane, st.level, st.gold, st.hp = 1, 3, 5, 80
    st.bench = []
    for _ in range(START_BENCH_COUNT):
        cost = rng.choices(
            [c for c, _ in START_BENCH_COST_WEIGHTS],
            weights=[w for _, w in START_BENCH_COST_WEIGHTS], k=1)[0]
        names = [n for n in pool.copies
                 if CHARACTERS[n].cost == cost and pool.copies[n] > 0]
        if names:
            n = rng.choice(names)
            pool.take(n)
            st.bench.append(BenchChar(
                slot=len(st.bench) + 1, char_id=n,
                faction=(CHARACTERS[n].factions or ['散'])[0]))
    sess = session or StrategySession()
    sess.v2_state = ('economy', False, False, 0, 0, 0, 0, 0)
    res = SimResult(seed=seed)
    xp = 0
    streak = 0
    for rn in (1, 2, 3, 4, 5, 6, 7, 8, 9):
        st.round_num = rn
        st.gold += BASE_INCOME + min(INTEREST_CAP, st.gold // 10) \
            + streak_gold(streak)   # r296 用户口述分段(0-1→0,2-4→2,5+→3)
        st.shop = pool.draw_shop(st.level)
        # 决策循环:刷新后同轮再决策(真 op 两阶段语义;每个
        # RefreshShop 动作后**独立重决策一段**——r270 连刷在
        # 决策层一口气输出多个 RefreshShop,但实机 op 是逐动作
        # 执行+买后重估(r251):刷→见新店→(再刷或买)。
        # r273 修:sim 逐动作消费,遇 RefreshShop 执行后立即
        # re-decide(捕捉"刷到就买"),段数上限防死循环。
        for _seg in range(8):
            strat.update_target(st, sess, None)
            acts = strat.decide_prep(st, sess, None)
            if not use_refresh:
                acts = [a for a in acts
                        if not isinstance(a, RefreshShop)]
            if not acts:
                break
            progressed = False
            for a in acts:
                if isinstance(a, RefreshShop):
                    res.refreshes += 1
                    st.gold -= (st.shop_refresh_cost or 2)
                    st.shop = pool.draw_shop(st.level)
                    progressed = True
                    break          # 刷后立即 re-decide(见新店)
                if isinstance(a, BuyCard):
                    pool.take(a.card.name)
                    st.gold -= a.card.cost
                    xp += XP_PER_BUY
                    st.bench.append(BenchChar(
                        slot=len(st.bench) + 1, char_id=a.card.name,
                        faction=a.card.faction))
                    progressed = True
                elif isinstance(a, LevelUp):
                    st.gold -= 4
                    xp += 4
                    progressed = True
                elif isinstance(a, SellBench):
                    if 0 <= a.bench_idx < len(st.bench):
                        bc = st.bench.pop(a.bench_idx)
                        ch = CHARACTERS.get(bc.char_id)
                        st.gold += (ch.cost if ch and ch.cost else 1)
                        pool.ret(bc.char_id)
                        progressed = True
            if not progressed:
                break
        while st.level < 9 and xp >= XP_TO_NEXT_LEVEL.get(st.level, 999):
            xp -= XP_TO_NEXT_LEVEL[st.level]
            st.level += 1
        if res.dir_round == 99 and _direction_established(sess):
            res.dir_round = rn
        # r260:按本局采样的真实节点类型结算(奖励/补给不掉血;
        # 遭遇=boss×1.15;战斗=方向二元;boss=boss 档)
        # r340:板深条件化实机 Δ 池优先(经验分布重放——
        # 深[6-8] -1.0 vs [3-5] -11.3 的板深效应入 sim);
        # 无匹配桶回退旧方向二元模型。
        # r343:同修正——Δ 采样用可 deploy 深度(口径同上)
        from collections import Counter as _C2
        _fc2 = _C2(b.faction for b in st.bench)
        _dep = min(st.level, sum(c for f, c in _fc2.items() if c >= 2)
                   + sum(c for f, c in _fc2.items()
                         if c == 1 and f in _SIM_ENGINE_FACTIONS))
        _ld = live_delta_for(nodes[rn - 1], _dep, rng) \
            if nodes[rn - 1] in ('battle', 'encounter', 'boss') else None
        if _ld is not None:
            delta = _ld
        else:
            delta = node_delta(nodes[rn - 1], rn, res.dir_round, rng)
        st.hp = max(0, int(st.hp + delta))
        streak = streak + 1 if delta > 0 else 0
        res.hp_trail.append(st.hp)
        res.hp_events.append((rn, nodes[rn - 1], delta, res.dir_round <= rn))
        # r343(review F/J 修:深度代理对齐实机 deploy 口径)——
        # 散件 drop 实机不上场(_should_deploy 的阵营 count≥2/
        # 框架件判据),「bench 数」代理系统性高估。改为
        # **可 deploy 件数**(阵营 count≥2 的 bench 卡数, capped
        # by level;框架件近似=引擎阵营)。
        from collections import Counter as _C
        _fc = _C(b.faction for b in st.bench)
        _deployable = sum(cnt for f, cnt in _fc.items() if cnt >= 2)
        _deployable += sum(cnt for f, cnt in _fc.items()
                           if cnt == 1 and f in _SIM_ENGINE_FACTIONS)
        res.depth_trail.append(min(st.level, _deployable))
        if st.hp <= 0:
            break
    res.final_hp = st.hp
    res.level = st.level
    res.locked_line = sess.locked_line
    res.bridge_id = sess.bridge_id
    return res


def simulate_p1_batch(n: int = 500, *, use_refresh: bool = True,
                      seed_base: int = 0) -> dict:
    """批量模拟 + 统计(HP≥60 概率/方向建立分布/平均末 HP)。"""
    import statistics
    results = [simulate_p1(seed_base + i, use_refresh=use_refresh)
               for i in range(n)]
    hps = [r.final_hp for r in results]
    dirs = [r.dir_round for r in results]
    established = [d for d in dirs if d < 99]
    return {
        'n': n,
        'hp_ge_60': sum(1 for h in hps if h >= 60) / n,
        'avg_final_hp': statistics.mean(hps),
        'dir_by_r2': sum(1 for d in dirs if d <= 2) / n,
        'dir_by_r4': sum(1 for d in dirs if d <= 4) / n,
        'dir_never': sum(1 for d in dirs if d >= 99) / n,
        'avg_dir_round': (statistics.mean(established)
                          if established else float('nan')),
        'avg_refreshes': sum(r.refreshes for r in results) / n,
    }
