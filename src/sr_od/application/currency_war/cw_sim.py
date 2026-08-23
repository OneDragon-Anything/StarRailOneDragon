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
    # Δ 池三态(⓪ 可复现基建):auto(默认,缺源 raise 不静默)/
    # snapshot(主仓提交快照,CI/跨机基准)/fallback(显式退旧
    # 模型,结果打标);A/B 对照同进程同池即可,跨日基线须核指纹。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

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

# r360(v7 分轮次裁决):实机对账残差=奖励球/节点事件金未建模,
# 随轮次增长(r1→r2 中位 +1 … r8→r9 中位 +9)。校准层注入
# (ADR-0233):按轮次经验分布采样,让 sim 金压力对齐实机
# (策略的攒息/破息行为分布依赖真实金流)。
EVENT_GOLD_BY_ROUND: dict[int, tuple[float, ...]] = {
    1: (1,), 2: (5.5,), 3: (2,), 4: (2,), 5: (2,),
    6: (2,), 7: (4,), 8: (9,),
}


def _event_gold(round_num: int, rng: random.Random) -> int:
    """奖励球/节点事件金(校准层;v7 各轮中位,±2 抖动)。"""
    base = EVENT_GOLD_BY_ROUND.get(round_num, (4,))[0]
    return max(0, int(base + rng.uniform(-2, 2)))

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
    # ⓪ 可复现基建:本局所用 Δ 池指纹与来源(裸 seed 不构成
    # 重放承诺,重放 = seed + 指纹;跨日基线对照必须同指纹)
    pool_fingerprint: str = ''
    pool_source: str = ''
    # ① 判读同构账本:每轮一行(轮内多段聚合;字段与遥测 jsonl
    # 同构 + sim 专属键挂 'sim' 下)。由 write_batch_ledger 落盘
    # sim_runs/<batch_id>/{decisions,outcomes}.jsonl 两流。
    ledger: list[dict] = field(default_factory=list)


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
# r375:引擎阵营消手抄双源——顶部 import 挂 cw_line_defs.
# ENGINE_FACTIONS(桥池 engine_bonds 派生;别名 _SIM_ENGINE_
# FACTIONS 保留,r343 源码锁与历史注释引用)。手抄副本曾三处
# 漂移:缺 持续伤害/贝洛伯格(r373 给 dot_belog 桥补了生产
# deploy 身份,sim 代理没跟 → 该桥局板深低估,ADR-0219 病),
# 多 银河学者(不在任何桥 engine_bonds)。
_DEPTH_BUCKET_W: int = 3   # 板深分桶宽

# --- Δ 池三态解析(⓪ 快照化;对抗审查一轮#1/二轮#1/#5 定谳) -----
# 校准数据可复现性纪律:
# - **缺源大声报错,禁止隐式静默回退**(实测同 seed 有池/无池可
#   翻转 hp_ge_60 判定:seed42 final 36 vs 55)——回退必须显式
#   pool='fallback',结果行打标 pool_source;
# - **指纹 = hash(池内容+桶宽+采样器版本)**,随 SimResult/批量
#   结果记录——裸 seed 不构成可重放承诺,重放 = seed+指纹;
# - 池源与 sim 落盘(sim_runs)隔离,防线在生成器源目录断言
#   (tools/cw/gen_delta_pool_snapshot.py,防 sim 数据回灌校准池)。
_SAMPLER_VERSION: int = 2   # 桶化/邻桶回退/采样语义变更时 +1(指纹输入)
# v2(ADR-0268):加防饥饿守卫——n<_BUCKET_MIN_N 的桶降级采样
# (邻桶合并/全池均匀取方差最小),不再裸采样。v1→v2 变更采样
# 语义,历史报告对旧池(v1 指纹)重放须用导出 JSON 快照。
_BUCKET_MIN_N: int = 5   # 防饥饿守卫门槛(批③ F1:battle 桶6 n=1
# 恒 -11,把跨深度 6 边界的策略臂系统性伪惩罚;建议值同报告)
# 仓根锚定(审查#7:相对路径 cwd 敏感,非仓根 cwd 的 auto 指错目录)
_AUTO_REPLAY_DIR = Path(__file__).resolve().parents[4] / '.debug' \
    / 'temp' / 'currency_war' / 'replay'


class DeltaPoolUnavailable(RuntimeError):
    """auto 模式找不到可用 Δ 池源——显式选 snapshot/fallback。"""


def pool_fingerprint(pool: dict) -> str:
    """池指纹:hash(池内容规范化 + 桶宽 + 采样器版本)。

    只哈希内容盖不住采样器语义(分桶宽/回退策略变了,同 seed
    结果变而指纹仍显示命中——二轮#5),故语义常量一并入指纹。
    """
    import hashlib
    import json as _json
    canon = _json.dumps(
        {n: {str(b): sorted(v) for b, v in sorted(buckets.items())}
         for n, buckets in sorted(pool.items())},
        ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(
        f'v{_SAMPLER_VERSION}|w{_DEPTH_BUCKET_W}|{canon}'.encode()).hexdigest()[:16]


def _pool_from_replay(replay_dir: Path) -> tuple[dict, dict]:
    """从生产 replay jsonl 构建 Δ 池 + 构成 meta。

    配对口径(r340 起):decisions 每轮取末行板深(Σboard),
    outcomes 同 run 按 (plane, round) 排序后相邻轮 hp 差分。
    半写行跳过并计数(生产 append 进行中尾行可能撕裂)。
    """
    import json as _json
    skipped: dict[str, int] = {}

    def _rows(name: str) -> list[dict]:
        out: list[dict] = []
        f = replay_dir / name
        if not f.exists():
            return out
        for ln in f.read_text(encoding='utf-8').splitlines():
            if not ln.strip():
                continue
            try:
                out.append(_json.loads(ln))
            except _json.JSONDecodeError:
                skipped[name] = skipped.get(name, 0) + 1
        return out

    boards: dict = {}
    for d in _rows('decisions.jsonl'):
        st = d.get('state') or {}
        b = st.get('board') or {}
        boards[(d.get('run_id'), d.get('plane'),
                d.get('round_num'))] = sum(b.values())
    seqs: dict[str, list] = {}
    for o in _rows('outcomes.jsonl'):
        if o.get('hp_after') is None:
            continue
        seqs.setdefault(o.get('run_id'), []).append(o)
    pool: dict = {}
    per_run_rounds: dict[str, int] = {}
    unlabeled_dropped = 0
    for run, seq in seqs.items():
        seq.sort(key=lambda o: (o.get('plane') or 0, o.get('round_num') or 0))
        per_run_rounds[str(run)] = len(seq)
        for a, b in zip(seq, seq[1:], strict=False):
            raw_nt = b.get('node_type') or ''
            nt = {'普通战斗': 'battle', '遭遇': 'encounter',
                  '奖励': 'reward', '首领': 'boss',
                  '补给': 'supply'}.get(raw_nt, raw_nt)
            if not nt:
                # 2026-08-22 retrofix(ADR-0239 配套)后历史死链标签
                # 置 None——无标签行不入池(与快照生成器 v2 同口径;
                # 审查#1:否则 auto/snapshot 两态指纹结构性永不相等,
                # 指纹相等性无法用作收敛判据)。
                unlabeled_dropped += 1
                continue
            k = (run, b.get('plane'), b.get('round_num'))
            dep = boards.get(k)
            if dep is None:
                continue
            bucket = min(dep // _DEPTH_BUCKET_W, 5) * _DEPTH_BUCKET_W
            pool.setdefault(nt, {}).setdefault(bucket, []).append(
                b['hp_after'] - a['hp_after'])
    meta = {'source_dir': str(replay_dir), 'runs': per_run_rounds,
            'skipped_lines': skipped,
            'unlabeled_dropped': unlabeled_dropped}
    return pool, meta


def _normalize_pool(raw: dict) -> dict:
    """桶键归一 int(json round-trip 会变字符串键——str 键会让
    live_delta_for 的 int 桶查询全 miss = 快照静默失效)。"""
    return {n: {int(b): list(v) for b, v in buckets.items()}
            for n, buckets in raw.items()}


_RESOLVED_CACHE: dict[str, tuple[dict, str, str]] = {}


def resolve_pool(pool: str | Path = 'auto', *,
                 auto_dir: Path | None = None) -> tuple[dict, str, str]:
    """Δ 池三态解析 → (pool_map, fingerprint, source_label)。

    - ``'auto'``(默认):生产 replay 实时构建(进程内缓存一次
      冻结);缺源/空池 raise DeltaPoolUnavailable——**不静默**;
    - ``'snapshot'``:主仓提交快照 ``cw_delta_pool_data``
      (CI/跨机可复现基准;重生成 tools/cw/gen_delta_pool_snapshot.py);
    - ``'fallback'``:显式退旧方向二元模型(结果打标,供无池
      环境的语义测试);
    - :class:`Path`:JSON 快照文件(生成器 --export-json 产物,
      历史版本重放用)。
    """
    key = repr((str(pool), str(auto_dir)))
    if key in _RESOLVED_CACHE:
        return _RESOLVED_CACHE[key]
    if pool == 'fallback':
        out = ({}, pool_fingerprint({}), 'fallback')
    elif pool == 'snapshot':
        from sr_od.application.currency_war.cw_delta_pool_data import (
            META as _META,
        )
        from sr_od.application.currency_war.cw_delta_pool_data import (
            SNAPSHOT as _SNAP_RAW,
        )
        _SNAP = _normalize_pool(_SNAP_RAW)
        if pool_fingerprint(_SNAP) != _META.get('fingerprint'):
            raise RuntimeError(
                '快照指纹失配:cw_delta_pool_data 被手改或指纹逻辑'
                '漂移——重跑 tools/cw/gen_delta_pool_snapshot.py')
        out = (_SNAP, _META['fingerprint'], 'snapshot')
    elif isinstance(pool, Path):
        doc = _json_loads_path(pool)
        snap = _normalize_pool(doc['snapshot'])
        fp = pool_fingerprint(snap)
        _meta_fp = (doc.get('meta') or {}).get('fingerprint')
        if _meta_fp is not None and _meta_fp != fp:
            # 审查#2:Path 模式校验 meta 指纹(失配 JSON 静默接受
            # = 历史重放的可信前提缺失)
            raise RuntimeError(
                f'快照文件指纹失配: {pool}(meta {_meta_fp} vs 重算 '
                f'{fp})——文件被改或导出时损坏,重导出')
        out = (snap, fp, f'path:{pool.name}')
    elif pool == 'auto':
        d = Path(auto_dir) if auto_dir else _AUTO_REPLAY_DIR
        p_map, meta = _pool_from_replay(d)
        if not p_map:
            raise DeltaPoolUnavailable(
                f'auto 池源不可用: {d.resolve()}(缺失/空/不可解析)。'
                "显式指定 pool='snapshot'(主仓提交快照)或 "
                "pool='fallback'(退旧方向二元模型,结果打标)")
        # 审查#4:半写行/整文件重写窗口 → 静默减样池——计数并入
        # source_label 披露(非空池也可见,不只覆盖空池)
        _skip = sum(meta.get('skipped_lines', {}).values()) \
            + meta.get('unlabeled_dropped', 0)
        label = 'auto' + (f'(skip{_skip})' if _skip else '')
        out = (p_map, pool_fingerprint(p_map), label)
    else:
        raise ValueError(
            f'pool 参数非法: {pool!r}(auto/snapshot/fallback/Path)')
    _RESOLVED_CACHE[key] = out
    return out


def reset_resolved_cache() -> None:
    """清空池解析缓存(审查#3:同路径文件更新后进程内仍返旧池;
    生成器/测试改写快照文件后调用,拿新指纹)。"""
    _RESOLVED_CACHE.clear()


def _json_loads_path(p: Path) -> dict:
    import json as _json
    return _json.loads(p.read_text(encoding='utf-8'))


def live_delta_for(node_type: str, depth: int,
                   rng: random.Random, *,
                   pool_map: dict | None = None) -> int | None:
    """按节点类型+板深取实机经验 Δ;无匹配桶 → None(调用方走旧模型)。

    ⓪ 起 pool_map 显式注入(resolve_pool 产物;None=auto 解析,
    缺源 raise 不静默)。r343(review E 修):邻桶回退只向**浅**侧
    (bucket-W)——深侧封顶 15 后 +W 是死码,且向深回退=偏乐观
    (深=掉血少)。

    **防饥饿守卫(ADR-0268,批③ F1)**:命中的桶 n<_BUCKET_MIN_N
    时不裸采样——n=1 的桶(如 battle 桶 6 恒 -11)等于把该深度
    锁死在唯一样本上,任何把板深推过桶边界的策略臂都被系统性
    伪惩罚(深度 6 悬崖)。降级策略:候选 = 本桶∪浅邻桶、本桶∪
    深邻桶、该节点全池均匀,取**方差最小**者采样(合并天然加权,
    样本多的邻桶主导);候选并列时按 浅邻→深邻→全池 序(确定
    性)。无任何可合并邻桶(极端小池)时退回裸样本——守卫降级
    采样,不改变「缺桶 → None」的既有两态语义。
    """
    if pool_map is None:
        pool_map = resolve_pool('auto')[0]
    _map = pool_map.get(node_type) or {}
    bucket = min(depth // _DEPTH_BUCKET_W, 5) * _DEPTH_BUCKET_W
    src_b = bucket if _map.get(bucket) else bucket - _DEPTH_BUCKET_W   # 缺桶浅侧回退(r343 E)
    samples = _map.get(src_b)
    if not samples:
        return None
    if len(samples) >= _BUCKET_MIN_N:
        return rng.choice(samples)
    cands: list[list[int]] = []
    for nb in (src_b - _DEPTH_BUCKET_W, src_b + _DEPTH_BUCKET_W):
        merged_neighbor = _map.get(nb)
        if merged_neighbor:
            cands.append(list(samples) + list(merged_neighbor))
    all_pool = [d for v in _map.values() for d in v]
    if len(all_pool) > len(samples):
        cands.append(all_pool)
    if not cands:
        return rng.choice(samples)

    def _pvar(seq: list[int]) -> float:
        import statistics
        return statistics.pvariance(seq) if len(seq) > 1 else 0.0

    best = min(cands, key=_pvar)
    return rng.choice(best)


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


def _board_factions_of(deployed) -> dict[str, int]:
    """r394:上场角色的阵营计数(生产 board 口径,flows 并计)。

    「过渡阵容凑到没有」的判据输入:recipe_tier(配方档位)/
    三人组在场上——此前 sim 账本 board 恒空,成型质量不可观测。
    """
    from sr_od.application.currency_war.cw_chars import CHARACTERS as _CH
    out: dict[str, int] = {}
    for d in (deployed or []):
        cid = getattr(d, 'char_id', '') or ''
        ch = _CH.get(cid)
        if ch is None:
            continue
        for f in (ch.factions or ()) + (ch.flows or ()):
            out[f] = out.get(f, 0) + 1
    return out


def _first_tier_round(res, tier: int) -> int | None:
    """r394:配方档位首达轮(ledger 的 board_factions 逐轮查
    recipe_tier≥tier 的最小轮;查不到=None)。"""
    from sr_od.application.currency_war.cw_line_defs import recipe_tier
    for row in res.ledger:
        bf = (row.get('state') or {}).get('board_factions') or {}
        if bf and recipe_tier(bf) >= tier:
            return row.get('round_num')
    return None


def _first_trio_round(res, target: int) -> int | None:
    """r394:核心三人组上场首达轮(deployed∩_CORE_TRIO 计数
    ≥target 的最小轮;查不到=None)。"""
    from sr_od.application.currency_war.cw_line_defs import _CORE_TRIO
    for row in res.ledger:
        dep = (row.get('state') or {}).get('deployed') or []
        cnt = sum(1 for d in dep
                  if d.get('char_id') in _CORE_TRIO)
        if cnt >= target:
            return row.get('round_num')
    return None


# r397/r399(用户定调重写 transition_combos.md;废除 r148/r149 大/中
# 引擎分层——旧词来源可疑且「大+中过不了位面1」被 895 帖数据证实):
# 过渡阵容 = **一级羁绊即有伤害**的 combat 羁绊两两组合——
# 仙舟3(召唤神舟)/列车2(星穹列车撞击)/DOT2(敌方回合超激发)。
# 人员要求:DOT2/列车2 无要求;仙舟3 用藿藿+饮月+爻光效果最好
# (功能链,95% 帖含全三人组);**希儿系**(r399 用户实战确认)=希儿
# 在场 AND(量子≥2 OR 贝≥2)——伤害在希儿技能层,量子/贝是放大器,
# 无希儿时不能独立当过渡(第四体系,单卡依赖)。
# 通用羁绊(战技点/护盾/学者/减益…)不是过渡主体——四种都不含的
# 49 帖全是直通线。
_TRANSITION_TRAITS: tuple[tuple[str, int], ...] = (
    ('持续伤害', 2), ('列车同行', 2), ('仙舟', 3),
)


def _engines_count(board_factions: dict[str, int],
                   deployed_names: frozenset[str] | set[str] = frozenset()
                   ) -> int:
    """过渡体系达成数(三选几+希儿系;两两组合=过渡成型)。

    r399:希儿系=希儿在场 AND(量子同频≥2 OR 贝洛伯格≥2)——
    与三羁绊同级可组合(列车2+希儿系 13 帖/仙舟+希儿系 3/DOT+希儿
    系 2/量贝同开 6)。
    """
    n = sum(1 for bond, tier in _TRANSITION_TRAITS
            if board_factions.get(bond, 0) >= tier)
    seele = ('希儿' in deployed_names
             and (board_factions.get('量子同频', 0) >= 2
                  or board_factions.get('贝洛伯格', 0) >= 2))
    if seele:
        n += 1
    return n


def _transition_formed(board_factions: dict[str, int],
                       deployed_names: frozenset[str] | set[str] = frozenset()
                       ) -> bool:
    """过渡阵容成型判据(transition_combos.md 2026-08-23 定稿):

    四种体系(仙舟3/列车2/DOT2/希儿系)**两两组合**=成型
    (三选二 140/328 帖;希儿系×三过渡 18 帖);
    单个=「过渡的过渡」(DOT2 可单独当起点但不等于成型)。
    """
    return _engines_count(board_factions, deployed_names) >= 2


def _first_engines_round(res, target: int) -> int | None:
    """r399:过渡体系达成数首达 target 的最小轮。

    判据走 _engines_count(四体系:仙舟3/列车2/DOT2/希儿系各算一个;
    希儿系需 deployed 含希儿——ledger 的 state.deployed 提供名单);
    target=2=过渡成型(两两组合),target=1=单体系点火
    (DOT2 单独可当「过渡的过渡」起点)。
    """
    for row in res.ledger:
        st = row.get('state') or {}
        bf = st.get('board_factions') or {}
        dep = frozenset(d.get('char_id', '')
                        for d in (st.get('deployed') or []))
        if bf and _engines_count(bf, dep) >= target:
            return row.get('round_num')
    return None


def _deployable_depth(st: GameState) -> int:
    """可 deploy 件数(① 收口:此前三处内联重算口径不一)。

    口径 r390(执行层代理落地):**读 st.deployed**(真实围栏输出,
    cw_deploy_logic.select_deployments 与 DeployBench op 同源)——
    旧口径数 bench 阵营对(r343),deploy 代理升级后两者脱钩
    (r387 变异探针差异死在这:围栏改了,板深没读)。
    depth_trail / Δ 池采样 / 账本 depth 共用本函数(单一源)。
    """
    _dep = len(st.deployed or [])
    return min(st.level, _dep)


def simulate_p1(seed: int, *, use_refresh: bool = True,
                strategy=None, session=None,
                pool: str | Path = 'auto') -> SimResult:
    """单局 P1 模拟(决策跑真策略代码)。

    :param seed: 随机种子(同 seed 同局,可复现——**须同池指纹**,
        见 ``pool``;SimResult.pool_fingerprint 记录本局所用池)
    :param use_refresh: False 时剔除 RefreshShop 动作(A/B 对照用)
    :param strategy: 注入策略(默认 LineStrategy;测试可换桩)
    :param session: 注入会话(默认新建;跨局复用场景可传)
    :param pool: Δ 池三态(⓪):'auto'(生产 replay,缺源 raise)/
        'snapshot'(主仓提交快照,CI/跨机基准)/'fallback'(显式
        退旧模型,结果打标)/Path(JSON 快照,历史重放)。
        A/B 对照同进程同池即可;**跨日基线对照须核指纹一致**。
    """
    from sr_od.application.currency_war.strategies.line_strategy import (
        LineStrategy,
    )
    pool_map, pool_fp, pool_src = resolve_pool(pool)
    rng = random.Random(seed)
    cards_pool = _Pool(rng)   # 命名避参数遮蔽(审查 minor:pool 参数)
    nodes = sample_node_sequence(rng)   # r260:本局节点序列(9 项)
    strat = strategy or LineStrategy()
    st = GameState()
    st.plane, st.level, st.gold, st.hp = 1, 3, 5, 80
    st.bench = []
    for _ in range(START_BENCH_COUNT):
        cost = rng.choices(
            [c for c, _ in START_BENCH_COST_WEIGHTS],
            weights=[w for _, w in START_BENCH_COST_WEIGHTS], k=1)[0]
        names = [n for n in cards_pool.copies
                 if CHARACTERS[n].cost == cost and cards_pool.copies[n] > 0]
        if names:
            n = rng.choice(names)
            cards_pool.take(n)
            st.bench.append(BenchChar(
                slot=len(st.bench) + 1, char_id=n,
                faction=(CHARACTERS[n].factions or ['散'])[0]))
    sess = session or StrategySession()
    sess.v2_state = ('economy', False, False, 0, 0, 0, 0, 0)
    res = SimResult(seed=seed, pool_fingerprint=pool_fp,
                    pool_source=pool_src)
    xp = 0
    streak = 0
    for rn in (1, 2, 3, 4, 5, 6, 7, 8, 9):
        st.round_num = rn
        # ① 账本:收入分解(rng 消耗序不变——event 先取后加,同原式)
        _gold_before = st.gold
        _inc_event = _event_gold(rn, rng)   # 事件金 ADR-0233
        _inc = {'base': BASE_INCOME,
                'interest': min(INTEREST_CAP, st.gold // 10),
                'streak': streak_gold(streak),   # 单一源 cw_economy(r305)
                'event': _inc_event}
        st.gold += sum(_inc.values())
        st.shop = cards_pool.draw_shop(st.level)
        _waves = [{'event': 'offer', 'gold': st.gold,
                   'cards': [{'name': c.name, 'faction': c.faction,
                              'cost': c.cost} for c in st.shop]}
                  ]   # ① 账本:牌面波(supply 视图;gold=该波时点金)
        # ① 账本:轮内聚合(段结构折叠,花销/买入逐笔记)
        _spend = {'buys': {}, 'levelup': 0, 'refresh': 0, 'sell_income': 0}
        _acts: list[dict] = []
        _segs_used = 0
        # 决策循环:刷新后同轮再决策(真 op 两阶段语义;每个
        # RefreshShop 动作后**独立重决策一段**——r270 连刷在
        # 决策层一口气输出多个 RefreshShop,但实机 op 是逐动作
        # 执行+买后重估(r251):刷→见新店→(再刷或买)。
        # r273 修:sim 逐动作消费,遇 RefreshShop 执行后立即
        # re-decide(捕捉"刷到就买"),段数上限防死循环。
        # r361b(ADR-0219 代理语义纪律,第三次命中):r358 检查点核心维
        # 读 state.deployed——sim 不建模 deployed 恒空 → 核心恒 0/2 →
        # 档位折扣恒触发(r5+ 恒走围栏,sim 行为与实机分叉)。
        # r390(用户定调「这些问题明明都可以模拟发现」):deployed 代理
        # 从「bench 引擎件直进」升级为 **deploy_bench 真实围栏逻辑**
        # (cw_deploy_logic.select_deployments 纯函数,与 DeployBench op
        # 同一源)——r373/r387 类执行层 bug 从此 sim 可发现。target 集
        # 从 session 语义取(桥期 transition_framework 阵营∪配方阵营,
        # r373 同型);未识别(char_id 空)照旧上,与 op 一致。
        from sr_od.application.currency_war import cw_deploy_logic as _dl
        _tf, _tc, _fw = frozenset(), frozenset(), frozenset()
        try:
            _tc = frozenset(getattr(sess, 'target_comp', None).core_chars
                            or ()) if getattr(sess, 'target_comp', None) else frozenset()
            _tf = frozenset(getattr(sess, 'target_comp', None).factions
                            or ()) if getattr(sess, 'target_comp', None) else frozenset()
            _fw_name = getattr(sess, 'transition_framework', '') or ''
            _fw = frozenset()
            if _fw_name:
                from sr_od.application.currency_war.cw_transition import (
                    TRANSITION_PACK,
                )
                _fw = frozenset(
                    n for n, (f, t) in TRANSITION_PACK.items()
                    if (f == _fw_name or f == '通用') and t != 'drop')
        except Exception:   # noqa: BLE001  代理 best-effort
            pass
        _up_idx, _held_idx = _dl.select_deployments(
            st.bench,
            deployed_cids=set(),
            deployed_fac=dict(st.board),
            board=dict(st.board),
            cap=st.max_units(),
            target_factions=_tf,
            target_cores=_tc,
            fw_carry=_fw,
        )
        st.deployed = [st.bench[i] for i in _up_idx if i < len(st.bench)]
        for _seg in range(8):
            strat.update_target(st, sess, None)
            acts = strat.decide_prep(st, sess, None)
            if not use_refresh:
                acts = [a for a in acts
                        if not isinstance(a, RefreshShop)]
            if not acts:
                break
            _segs_used += 1
            progressed = False
            for a in acts:
                if isinstance(a, RefreshShop):
                    res.refreshes += 1
                    _cost_r = (st.shop_refresh_cost or 2)
                    st.gold -= _cost_r
                    _spend['refresh'] += _cost_r
                    _acts.append({'__type__': 'RefreshShop', 'cost': _cost_r})
                    st.shop = cards_pool.draw_shop(st.level)
                    _waves.append(
                        {'event': 'refresh', 'gold': st.gold,
                         'cards': [{'name': c.name, 'faction': c.faction,
                                    'cost': c.cost} for c in st.shop]})
                    progressed = True
                    break          # 刷后立即 re-decide(见新店)
                if isinstance(a, BuyCard):
                    cards_pool.take(a.card.name)
                    st.gold -= a.card.cost
                    _ch = a.reason or 'unknown'
                    _spend['buys'][_ch] = \
                        _spend['buys'].get(_ch, 0) + a.card.cost
                    # 序列化形状对齐生产 serialize_action(card 嵌套;
                    # 视图读 a['card']['cost'],平铺会让 economy 算 0)。
                    # reason=**通道**(创建点语义);channel=**身份**
                    # (classify_buy——通道经济分析别混桶,审查#7)
                    from sr_od.application.currency_war.cw_line_defs import (
                        classify_buy as _cb,
                    )
                    _acts.append({'__type__': 'BuyCard',
                                  'card': {'x': a.card.x,
                                           'faction': a.card.faction,
                                           'name': a.card.name,
                                           'cost': a.card.cost},
                                  'reason': _ch,
                                  'channel': _cb(a.card, st)})
                    xp += XP_PER_BUY
                    st.bench.append(BenchChar(
                        slot=len(st.bench) + 1, char_id=a.card.name,
                        faction=a.card.faction))
                    progressed = True
                elif isinstance(a, LevelUp):
                    st.gold -= 4
                    _spend['levelup'] += 4
                    _acts.append({'__type__': 'LevelUp', 'cost': 4})
                    xp += 4
                    progressed = True
                elif isinstance(a, SellBench):
                    if 0 <= a.bench_idx < len(st.bench):
                        bc = st.bench.pop(a.bench_idx)
                        ch = CHARACTERS.get(bc.char_id)
                        _sell_v = (ch.cost if ch and ch.cost else 1)
                        st.gold += _sell_v
                        _spend['sell_income'] += _sell_v
                        _acts.append({'__type__': 'SellBench',
                                      'bench_idx': a.bench_idx,
                                      'name': bc.char_id,
                                      'income': _sell_v})
                        cards_pool.ret(bc.char_id)
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
        # r343:同修正——Δ 采样用可 deploy 深度;① 收口进
        # _deployable_depth 单一源(原三处内联口径不一)
        _dep = _deployable_depth(st)
        _ld = live_delta_for(nodes[rn - 1], _dep, rng,
                             pool_map=pool_map) \
            if nodes[rn - 1] in ('battle', 'encounter', 'boss') else None
        if _ld is not None:
            delta = _ld
        else:
            delta = node_delta(nodes[rn - 1], rn, res.dir_round, rng)
        st.hp = max(0, int(st.hp + delta))
        streak = streak + 1 if delta > 0 else 0
        res.hp_trail.append(st.hp)
        res.hp_events.append((rn, nodes[rn - 1], delta, res.dir_round <= rn))
        # ① 账本:每轮一行(轮内段聚合;depth 单一源;core_count
        # 按 target 语境路由 core_count_for——③ 攒数据地基:线库
        # core_cards/桥池 fixed+core/三人组单一口径,旧 core_trio_
        # count 绑死仙舟非仙舟线局恒 0,审查二轮#8)
        _depth = _deployable_depth(st)
        res.depth_trail.append(_depth)
        # r393(装备层执行代理):supply 节点 = 3 选 1 装备——
        # decide_supply(纯逻辑,与 run_supply_node 同源)选 →
        # 入 st.equips(owned 池);equip_allocation(纯逻辑,与
        # EquipAll 同源)分配给 deployed → 账本 equipped 字段。
        # 装备获取采样:通用装备池按 _EQUIP_VALUE 键 + 无名池
        # (OCR 漏读形态);带钻概率 15%(实机简报词缀影响的粗估,
        # 校准点)。r388 类 bug(开局乱穿)从此 sim 可见。
        _equipped_now: list[tuple[str, str]] = []
        if nodes[rn - 1] == 'supply':
            from sr_od.application.currency_war.cw_events import (
                _EQUIP_VALUE as _EV,
            )
            from sr_od.application.currency_war.cw_events import (
                SupplyOption,
                decide_supply,
            )
            _pool_names = list(_EV.keys()) + ['未知装备']
            _opts = []
            for _oi in range(3):
                _eq = rng.choice(_pool_names)
                _opts.append(SupplyOption(
                    idx=_oi, char='', equip=_eq,
                    has_diamond=rng.random() < 0.15))
            _pick = decide_supply(_opts, st, sess.target_comp, None)
            st.equips.append(_opts[_pick.idx].equip)
            if _pick.idx < len(_opts) and _opts[_pick.idx].has_diamond:
                st.equips.append('钻石')
        if st.equips and st.deployed:
            from sr_od.application.currency_war.cw_comps import (
                equip_allocation,
            )
            _equipped_now = equip_allocation(
                sess.target_comp, st.deployed, list(st.equips))
            for _who, _what in _equipped_now:
                if _what in st.equips:
                    st.equips.remove(_what)
        from sr_od.application.currency_war.cw_line_defs import (
            core_count_for,
        )
        res.ledger.append({
            'ts': rn,   # 单调轮序号(非墙钟;审查①#9)
            'plane': 1, 'round_num': rn,
            'gold': st.gold, 'hp': st.hp,
            'target_comp': (sess.locked_line or sess.bridge_id or ''),
            'state': {'board': {}, 'level': st.level,
                      # r394(过渡阵容判据接线):板面阵营档位——
                      # deployed 的 factions 计数(生产 board 口径;
                      # 旧恒空 dict 让「r几凑到配方X档/三人组上场」
                      # 在 sim 判读不可见)。recipe_tier 判据的输入。
                      'board_factions': _board_factions_of(st.deployed),
                      # bench 对齐生产 BenchChar 形状(dict 带
                      # char_id/faction——视图/检查读 b['faction']
                      # 不炸;审查#3)
                      'bench': [{'char_id': b.char_id,
                                 'faction': b.faction,
                                 'slot': b.slot}
                                for b in st.bench],
                      # r391(执行层代理配套):deployed/cap 入账本
                      # ——「开局 deploy<cap」检查项的数据源
                      # (r387 类 bug 的 sim 常态化防线)。deployed
                      # 形状对齐 rounds 视图消费(dict 带
                      # position_pref,同 bench 形状)。
                      'deployed': [{'char_id': d.char_id,
                                    'faction': d.faction,
                                    'slot': d.slot,
                                    'position_pref': d.position_pref}
                                   for d in (st.deployed or [])
                                   if getattr(d, 'char_id', '')],
                      'cap': st.max_units(),
                      # r393(装备层代理):本轮分配结果(谁穿了什么)
                      # +owned 余量——「开局零穿着/乱穿」检查项数据源。
                      'equipped': [{'char': w, 'equip': e}
                                   for w, e in _equipped_now],
                      'owned_equips': list(st.equips)},
            'actions': _acts,
            'sim': {
                'node': nodes[rn - 1], 'delta': delta,
                'gold_before': _gold_before,
                'income': _inc, 'spend': _spend,
                'depth': _depth,
                # core_count 语义=core_routed(core_count_for 按
                # target 路由;known-line-no-core=None)。**此前的
                # 账本批次是旧三人组口径,聚合端按 ledger_semantics
                # 过滤**(manifest 键;审查#2:口径混桶=③ 噪声)
                'core_count': core_count_for(
                    sess.locked_line or sess.bridge_id or '',
                    {d.char_id for d in (st.deployed or [])
                     if getattr(d, 'char_id', '')}),
                # deployed 代理名单(审查#5:tiers sim 行可渲染
                # 角色构成——比只有计数信息量高一档)
                'deployed': [d.char_id for d in (st.deployed or [])
                             if getattr(d, 'char_id', '')],
                'shop_waves': _waves,
                'dir_established': res.dir_round <= rn,
                'segments': _segs_used,
            },
        })
        if st.hp <= 0:
            break
    res.final_hp = st.hp
    res.level = st.level
    res.locked_line = sess.locked_line
    res.bridge_id = sess.bridge_id
    return res


def simulate_p1_batch(n: int = 500, *, use_refresh: bool = True,
                      seed_base: int = 0,
                      pool: str | Path = 'auto',
                      ledger: bool | Path = True,
                      checks: bool = True) -> dict:
    """批量模拟 + 统计(HP≥60 概率/方向建立分布/平均末 HP)。

    返回含 ``pool_fingerprint``/``pool_source``(⓪):跨日基线
    对照必须核对指纹一致——池随实机追加漂移,裸数字不可比。

    :param ledger: True=落两流账本到 ``sim_runs/<batch_id>/"``"
        (decisions+outcomes.jsonl,判读 CLI 可查);Path=显式目录;
        False=不落盘。batch_id 含时间戳,自动保留最近
        ``_SIM_RUNS_KEEP`` 个批次。
    :param checks: 跑完执行 cw_sim_checks 异常断言(②;默认开,
        结果挂 ``checks_violations``)。
    """
    import statistics
    results = [simulate_p1(seed_base + i, use_refresh=use_refresh,
                           pool=pool)
               for i in range(n)]
    report = {
        'n': n,
        'pool_fingerprint': results[0].pool_fingerprint,
        'pool_source': results[0].pool_source,
        'hp_ge_60': sum(1 for h in (r.final_hp for r in results) if h >= 60) / n,
        'avg_final_hp': statistics.mean(r.final_hp for r in results),
        # r370(新验收对齐,goal rev5):战斗节点败场 ≤2 概率
        # (battle/encounter/boss 计分,奖励/补给不计;hp_events
        # 的 delta<0=败)。与实机 outcomes killed+node_type 同构。
        'battle_losses_le_2': sum(
            1 for r in results
            if sum(1 for _, nt, d, _ in r.hp_events
                   if nt in ('battle', 'encounter', 'boss') and d < 0) <= 2
        ) / n,
        'dir_by_r2': sum(1 for d in (r.dir_round for r in results) if d <= 2) / n,
        'dir_by_r4': sum(1 for d in (r.dir_round for r in results) if d <= 4) / n,
        'dir_never': sum(1 for d in (r.dir_round for r in results) if d >= 99) / n,
        'avg_dir_round': (statistics.mean(
            [d for d in (r.dir_round for r in results) if d < 99])
            if any(r.dir_round < 99 for r in results) else float('nan')),
        'avg_refreshes': sum(r.refreshes for r in results) / n,
        # r394/r399(过渡阵容成型指标;判据单一源=transition_combos.md
        # 2026-08-23 定稿:四体系两两组合):
        # engines2_by_r6=四体系(仙舟3/列车2/DOT2/希儿系)达成≥2 的
        # r6 前占比——「位面1 能否顺利凑到过渡阵容」的直接度量。
        # 希儿系=希儿在场 AND(量2 OR 贝2),伤害在希儿技能层,
        # 量子/贝是放大器(单卡依赖,r399 用户实战确认)。
        'engines2_by_r6': sum(
            1 for r in results
            if _first_engines_round(r, 2) is not None
            and _first_engines_round(r, 2) <= 6) / n,
        'recipe5_by_r6': sum(
            1 for r in results
            if _first_tier_round(r, 5) is not None
            and _first_tier_round(r, 5) <= 6) / n,
        'trio3_by_r8': sum(
            1 for r in results
            if _first_trio_round(r, 3) is not None
            and _first_trio_round(r, 3) <= 8) / n,
    }
    if ledger is not False:
        out = (Path(ledger) if isinstance(ledger, Path)
               else _default_sim_runs_dir(report['pool_fingerprint'], n,
                                          seed_base))
        report['ledger_dir'] = str(write_batch_ledger(
            results, out, pool_fp=report['pool_fingerprint']))
    if checks:
        from sr_od.application.currency_war.cw_sim_checks import (
            check_delta_pool_bucket_min_n,
            check_depth_cliff_monotonicity,
            run_checks_on_ledgers,
        )
        rep_checks = run_checks_on_ledgers(
            [r.ledger for r in results])
        # ADR-0268:池级检查(桶饥饿/深崖单调)——批③ F1 的常态
        # 化防线;fallback 空池无违规属预期(池语义检查不辖旧模型)
        _pm, _, _ = resolve_pool(pool)
        rep_checks['delta_pool_bucket_min_n'] = \
            check_delta_pool_bucket_min_n(_pm)
        rep_checks['depth_cliff_monotonicity'] = \
            check_depth_cliff_monotonicity(_pm)
        # 审查#6:报告自带 seed_base/n——games 索引 → seed =
        # seed_base+idx,跨日志传阅时索引可独立解读
        for v in rep_checks.values():
            v['seed_base'] = seed_base
        report['checks_violations'] = rep_checks
    return report


# sim 账本落盘根目录(与生产 replay 隔离;写入器有目录守卫)
SIM_RUNS_DIR = _AUTO_REPLAY_DIR.parent / 'sim_runs'   # 仓根锚定(同上)
_SIM_RUNS_KEEP: int = 20   # 批次保留数(防无限累积;旧的自动清理)
_NT_TO_PROD = {'battle': '普通战斗', 'encounter': '遭遇',
               'reward': '奖励', 'boss': '首领', 'supply': '补给'}


def _default_sim_runs_dir(pool_fp: str, n: int, seed_base: int) -> Path:
    import time
    stamp = time.strftime('%Y%m%d_%H%M%S') + f'{time.monotonic_ns() % 1000:03d}'
    return SIM_RUNS_DIR / f'sim_{stamp}_n{n}_s{seed_base}_{pool_fp[:8]}'


def write_batch_ledger(results: list[SimResult], out_dir: Path, *,
                       pool_fp: str = '') -> Path:
    """两流账本落盘:``<out_dir>/{decisions,outcomes}.jsonl``。

    - decisions 每轮一行(SimResult.ledger;run_id=batch 目录名);
    - outcomes 每轮一行(OutcomeRecord 同构:生产 node_type 词表
      + hp_after + board_before/bench_count;sim 专属键挂 'sim');
    - **守卫:out_dir 不得是生产 replay 目录**(自中毒防线,
      生成器侧另有源目录断言,双保险)。
    """
    import json as _json
    out_dir = Path(out_dir)
    _prod = _AUTO_REPLAY_DIR.resolve()
    if out_dir.resolve() == _prod or _prod in out_dir.resolve().parents:
        raise RuntimeError(
            f'sim 账本禁写生产 replay 目录: {out_dir}(自中毒回路;'
            f'落盘目标只能是 {SIM_RUNS_DIR} 下或显式独立目录)')
    out_dir.mkdir(parents=True, exist_ok=True)
    base_id = out_dir.name
    with (out_dir / 'decisions.jsonl').open('w', encoding='utf-8') as f_d, \
         (out_dir / 'outcomes.jsonl').open('w', encoding='utf-8') as f_o, \
         (out_dir / 'shop_snapshots.jsonl').open('w',
                                                 encoding='utf-8') as f_s:
        for r in results:
            # 每局独立 run_id(带 seed——判读视图按 run 过滤时一局一局
            # 看,且 id 即重放地址:simulate_p1(<seed>) 重放该局)
            run_id = f'{base_id}_s{r.seed}'
            for row in r.ledger:
                row = dict(row)
                row['run_id'] = run_id
                row['schema_version'] = 1
                f_d.write(_json.dumps(row, ensure_ascii=False) + '\n')
                o = {
                    'schema_version': 1, 'ts': row['ts'],
                    'run_id': run_id, 'plane': row['plane'],
                    'round_num': row['round_num'],
                    'node_type': _NT_TO_PROD.get(
                        row['sim']['node'], row['sim']['node']),
                    'comp_tag': row['target_comp'] or '',
                    'hp_after': row['hp'],
                    'board_before': {}, 'bench_count':
                        len(row['state']['bench']),
                    'sim': {'delta': row['sim']['delta'],
                            'depth': row['sim']['depth'],
                            # killed 语义同产线=**胜**(击杀敌方;
                            # settlement_obs _won / battle_loop
                            # hp_after>=prev_hp——审查 major:killed
                            # 极性反转会把败场读成胜场)
                            'killed': row['sim']['delta'] >= 0},
                }
                f_o.write(_json.dumps(o, ensure_ascii=False) + '\n')
                # 第三流:牌面波(生产 shop_snapshots 同 schema——
                # supply 视图零改动可查 sim 批次)
                for w in row['sim'].get('shop_waves') or []:
                    f_s.write(_json.dumps({
                        'schema_version': 1, 'ts': row['ts'],
                        'run_id': run_id, 'plane': row['plane'],
                        'round_num': row['round_num'],
                        'event': w['event'], 'gold': w['gold'],
                        'shop': w['cards'],
                    }, ensure_ascii=False) + '\n')
    # manifest(审查#5:写半失败无标记 → 残批被当有效批;判读端
    # 可校验 manifest 在+行数匹配才认批)。ledger_semantics 标记
    # 账本字段语义版本(审查#2:core_count 三人组→按线路由变更
    # 无标记,新旧批次混存=③ 聚合静默混桶)。
    (out_dir / 'manifest.json').write_text(_json.dumps({
        'n': len(results),
        'seeds': [r.seed for r in results],
        'pool_fingerprint': pool_fp or (
            results[0].pool_fingerprint if results else ''),
        'rounds_rows': sum(len(r.ledger) for r in results),
        'ledger_semantics': 'core_routed',
    }, ensure_ascii=False), encoding='utf-8')
    # 保留清理(旧批次滚动删除;只清 sim_ 前缀批——用户显式传的
    # 非 sim 目录不动,审查#5)
    if SIM_RUNS_DIR.exists():
        batches = sorted(p for p in SIM_RUNS_DIR.iterdir()
                         if p.is_dir() and p.name.startswith('sim_'))
        for old in batches[:-_SIM_RUNS_KEEP]:
            import shutil
            shutil.rmtree(old, ignore_errors=True)
    return out_dir


def _cli_main() -> None:
    """④ seed 重放入口(可复现 bug 报告:seed+池指纹 → 逐轮决策)。

    用法:
        uv run python -m sr_od.application.currency_war.cw_sim \\
            replay --seed 42 --pool snapshot
    checks 报的 games 索引 → seed = seed_base + idx,同参数重放。
    池指纹不符(历史 bug 对新池)→ 提示换池版本,不硬跑(⓪ 纪律)。
    """
    import argparse
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(prog='cw_sim')
    ap.add_argument('cmd', choices=['replay', 'batch'])
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--n', type=int, default=100)
    ap.add_argument('--seed-base', type=int, default=0)
    ap.add_argument('--pool', default='snapshot',
                    help='auto/snapshot/fallback/JSON 路径')
    ap.add_argument('--expect-fingerprint', default='',
                    help='期望池指纹(不符即拒——历史报告对旧池重放)')
    args = ap.parse_args()
    pool_arg = args.pool
    if args.cmd == 'replay':
        r = simulate_p1(args.seed, pool=pool_arg)
        if args.expect_fingerprint and \
                r.pool_fingerprint != args.expect_fingerprint:
            print(f'池指纹不符: 期望 {args.expect_fingerprint} '
                  f'实得 {r.pool_fingerprint}(换池版本或 Path 快照)')
            return
        print(f"=== seed {args.seed} | 池 {r.pool_source} "
              f"{r.pool_fingerprint[:8]} | 末HP {r.final_hp} "
              f"| dir r{r.dir_round} ===")
        for row in r.ledger:
            s = row['sim']
            buys = [f"{(a.get('card') or {}).get('name')}"
                    f"({a.get('reason', '?')})"
                    for a in row['actions']
                    if a.get('__type__') == 'BuyCard']
            print(f"  r{row['round_num']} {s['node']:<9} "
                  f"Δ{s['delta']:+3d} hp={row['hp']:>3} "
                  f"g={row['gold']:>3} 深{s['depth']:>2} "
                  f"花={sum(s['spend']['buys'].values())} "
                  f"tgt={row['target_comp'] or '-'} "
                  f"买={','.join(buys) or '-'}")
    else:
        rep = simulate_p1_batch(args.n, seed_base=args.seed_base,
                                pool=pool_arg)
        for k in ('n', 'hp_ge_60', 'battle_losses_le_2', 'avg_final_hp',
                  'pool_fingerprint'):
            print(f'{k}: {rep[k]}')
        print('checks:', rep['checks_violations'])


if __name__ == '__main__':
    _cli_main()
