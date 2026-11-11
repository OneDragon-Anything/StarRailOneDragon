"""语料抽取器(旧流 decisions/outcomes → 训练样本行;sim-power-model §8-1)。

canonical 口径单一源 = sim-power-model §5.1(join 键/快照规则/去重与
降级/坏局排除/标签);特征算术 = 同包 :mod:`features`(双侧同源,本模
块只做行适配)。产物落 ``.debug/currency_war/sim_power_model_v1/
extraction/``(gitignored 区),零主流程副作用;本模块仅在显式运行
(``python -m ...corpus_extract``)时读遥测与写产物,import 无副作用。

三铁律落点(sim-power-model §1):
- 铁律 2(sim 永不进训练集)= 三道防线:①目录守卫(源目录禁在
  sim 批根下,先例 = 已停用 Δ池生成器 ``_assert_guards``);②具名
  文件白名单(许可集恰为各源目录的 ``decisions.jsonl``/``
  outcomes.jsonl`` 两个解析后绝对路径,禁目录级 glob——同目录旁路
  .jsonl 众多,glob 会双计/卷脏数据,权威版本 §8-1);③run 级隔离
  (``fake_``/``sim_`` 前缀规则 + 显式事故名单,run 粒度拦「进错目录
  的 run」,先例同 Δ池生成器)。
- 铁律 3(HP 不入胜负模型)= 训练样本行零 HP 字段;HP 量只进幅度
  样本表(幅度层,供直方估计,不回喂胜负模型;sim-power-model §6.1)。

产物头部 = 源指纹(输入文件集 sha256 + 抽取器版本)+ 三数重钉
(战斗类结局/有标签/胜事件)+ 丢弃分桶(source×位面)+ MNAR 缺失率
+ target_comp 覆盖率与值域构成 + 许可集普查记录。
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from one_dragon.utils.file_utils import get_project_root
from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY
from sr_od.application.currency_war.kernel.cw_observe import (
    LIVE_DIR,
    SIM_ROOT,
)
from sr_od.application.currency_war.sim.power_model.features import (
    BATTLE_NODE_TYPES,
    FEATURE_NAMES,
    FeatureVector,
    features_from_decision_row,
    normalize_node_type,
)
from sr_od.application.currency_war.telemetry.cw_replay_reader import (
    load_decisions,
    load_outcomes,
)

#: 抽取器版本(产物头部指纹域;特征/口径语义变更时递增)。
#: v2 = required-deployed-retirement:final_form_progress 特征语义变更
#: (点名件折条源 = 定义件/core 统一表达式;含 best_line argmax 的
#: core_star_depth 连带漂移)——语料需按新版本重建。
EXTRACTOR_VERSION: str = 'v2'

#: 产物默认落点(gitignored 区;sim-power-model §8-1 指定)。
DEFAULT_OUT_DIR: Path = (get_project_root() / '.debug' / 'currency_war'
                         / 'sim_power_model_v1' / 'extraction')

#: 默认许可源 = 已核实实机流根(待盘点候选经普查裁定
#: sim 后不进许可集,裁定记录随产物)。
DEFAULT_LICENSE_DIRS: tuple[Path, ...] = (LIVE_DIR,)

#: 具名文件白名单(许可集恰为各源目录下这两个文件;权威版本 §8-1)。
LICENSED_BASENAMES: frozenset[str] = frozenset(
    {'decisions.jsonl', 'outcomes.jsonl'})

#: run 隔离·前缀规则(类别级;先例 = 已停用 Δ池生成器
#: QUARANTINED_RUN_PREFIXES,考古走 git 历史)。消费统一走
#: :func:`run_quarantine_reason`,禁散写 startswith 判断。
QUARANTINED_RUN_PREFIXES: dict[str, str] = {
    # 假游戏/调试注入局:行内数值是造数非屏面观测,入训练集 =
    # 「用编造的对局训练真实策略模型」(2026-09-08 假游戏局
    # run_id=fake_20260908 混入 live 生产流事故同类,对账记录见
    # 当期 ADR-0595 时代档案;前缀规则按类别拦截,不逐例登记)。
    'fake_': '假游戏/调试注入局(非真实对局观测)',
    # sim 批 run(sim 批以批目录名为 run_id 前缀,目录形如
    # sim_<stamp>_n..._s...):sim 产出进训练集 = 「sim 校准 sim」
    # 自中毒回路(sim-power-model 铁律 2)。
    'sim_': 'sim 批 run(铁律 2:sim 永不进训练集)',
}

#: run 隔离·显式名单(个例级事故局;按当期事故局记录重建,先例 =
#: Δ池生成器时代 QUARANTINED_RUNS。双进程写竞争事故局来自旧遥测根,
#: 保留条目防历史文件回流许可集)。
QUARANTINED_RUNS: dict[str, str] = {
    'run_20260822_185613': '双进程写竞争事故局(局55)',
    'run_20260822_191028': '双进程写竞争事故局(局56/57 重启交错)',
}

#: outcomes source 档次(权威版本 §5.1-4:带标签行内按 source 档次,
#: 小值优先):'' 与缺失(旧 schema 真值)> loss_page(败页回填)>
#: 其余回填族。
_SOURCE_TIER: dict[str, int] = {'': 0, 'loss_page': 1}


def source_tier(source: str | None) -> int:
    """source → 档次值(小值优先;未登记 source 归「其余回填族」)。"""
    return _SOURCE_TIER.get(str(source if source is not None else ''), 2)


def run_quarantine_reason(run_id: object) -> str | None:
    """run 隔离判据单一源:前缀规则优先(类别级),显式名单兜底。

    返回隔离原因(命中,不入训练集)或 None(放行)。"""
    rid = run_id if isinstance(run_id, str) else ''
    for prefix, reason in QUARANTINED_RUN_PREFIXES.items():
        if rid.startswith(prefix):
            return reason
    return QUARANTINED_RUNS.get(rid)


# ===== 输入守卫(解析后路径精确相等断言;先例 = 权威版本 §8-1)=====

def assert_input_guards(license_dirs: list[Path] | tuple[Path, ...],
                        sim_root: Path | None = None) -> dict[Path, dict[str, Path]]:
    """输入守卫:逐许可目录断言两文件解析后路径,返回许可路径集。

    三道断言(全部按 ``Path.resolve()`` 后比较,防符号链/相对段穿透
    文件名检查):
    1. 目录守卫:源目录不得等于 sim 批根、不得位于其下(sim 批回灌 =
      自中毒回路,先例 = Δ池生成器 ``_assert_guards``);
    2. 具名白名单:许可集恰为 ``{dir}/decisions.jsonl`` 与
      ``{dir}/outcomes.jsonl``,调用方传入的其他文件名一律拒绝;
    3. 路径存在性由读端处理(缺文件 = 空流,规范读端语义),守卫只辖
      「名字与位置」。

    :param sim_root: sim 批根(默认取 :data:`SIM_ROOT`;测试经 monkeypatch
        换桩,禁在测试中触真实 .debug)。
    :raises RuntimeError: 任一断言失败(响亮失败,不静默收窄)。
    """
    resolved_root = (sim_root or SIM_ROOT).resolve()
    licensed: dict[Path, dict[str, Path]] = {}
    for d in license_dirs:
        src_resolved = Path(d).resolve()
        if src_resolved == resolved_root or resolved_root in src_resolved.parents:
            raise RuntimeError(
                f'抽取源目录非法: {src_resolved} 位于 sim 批根 '
                f'{resolved_root} 下——sim 产出进训练集 = 铁律 2 违例')
        licensed[src_resolved] = {
            name: (src_resolved / name).resolve()
            for name in sorted(LICENSED_BASENAMES)
        }
    return licensed


# ===== 载入与源指纹 =====

@dataclass
class CorpusInput:
    """一个许可目录的两流(行 + 源指纹)。"""
    dir_path: Path
    decisions_rows: list[dict[str, Any]]
    outcomes_rows: list[dict[str, Any]]
    file_sha256: dict[str, str] = field(default_factory=dict)
    raw_row_counts: dict[str, int] = field(default_factory=dict)


def _sha256_of(path: Path) -> str:
    """文件字节 sha256(源指纹域;流式读,不整载)。"""
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_licensed_corpus(license_dirs: list[Path] | tuple[Path, ...],
                         sim_root: Path | None = None) -> list[CorpusInput]:
    """守卫后载入各许可目录两流(规范读端;缺文件 = 空流)。

    行保留裸 dict 形态(规范读端类型化对象经 ``asdict`` 还原——读端
    负责缺字段/未知键归一,管线按 ``.get`` 宽容读历史行形态);源指纹
    = 逐文件 sha256 + 原始行数(守卫在指纹之前——被守卫拒收的目录不
    产生指纹)。"""
    licensed = assert_input_guards(license_dirs, sim_root)
    out: list[CorpusInput] = []
    for src, files in licensed.items():
        dec_rows = [asdict(r) for r in
                    load_decisions(files['decisions.jsonl'])]
        out_rows = [asdict(r) for r in
                    load_outcomes(files['outcomes.jsonl'])]
        out.append(CorpusInput(
            dir_path=src,
            decisions_rows=dec_rows,
            outcomes_rows=out_rows,
            file_sha256={
                name: _sha256_of(p) for name, p in files.items() if p.exists()
            },
            raw_row_counts={
                'decisions': len(dec_rows), 'outcomes': len(out_rows),
            },
        ))
    return out


def source_fingerprint(inputs: list[CorpusInput]) -> dict[str, Any]:
    """产物头部源指纹:抽取器版本 + 逐文件哈希/行数 + 组合哈希。

    组合哈希 = 按「路径:哈希」行排序后拼接再 sha256(输入文件集哈希;
    防同目录旁路文件/映射漂移两类静默污染,权威版本 §5.1 末条)。"""
    entries = [
        {'dir': str(inp.dir_path), 'file': name,
         'sha256': inp.file_sha256.get(name, ''),
         'rows': inp.raw_row_counts.get(
             'decisions' if name == 'decisions.jsonl' else 'outcomes', 0)}
        for inp in inputs for name in sorted(LICENSED_BASENAMES)
    ]
    combo = hashlib.sha256(
        '\n'.join(f"{e['dir']}:{e['file']}:{e['sha256']}" for e in entries)
        .encode('utf-8')).hexdigest()
    return {
        'extractor_version': EXTRACTOR_VERSION,
        'inputs': entries,
        'combined_sha256': combo,
    }


# ===== canonical 对齐(权威版本 §5.1)=====

def _join_key(row: dict[str, Any]) -> tuple[str, int, int]:
    """三元 join 键 (run_id, plane, round_num)(round_num 按位面重置,
    两段键会跨位面撞——权威版本 §5.1-1)。"""
    return (str(row.get('run_id') or ''), int(row.get('plane') or 0),
            int(row.get('round_num') or 0))


def _bucket(source: str | None, plane: int) -> str:
    """丢弃分桶键(f'{source族}|plane{p}';source 族 = 原值或'missing')。"""
    src = 'missing' if source is None else str(source)
    return f'{src}|plane{int(plane)}'


@dataclass
class CanonicalAlignment:
    """canonical 对齐产物:逐键权威 outcome + 全量漏斗计数。"""
    #: 键 → 权威 outcome 行(经去重与降级;含全部键,战斗过滤后消费)
    canonical: dict[tuple[str, int, int], dict[str, Any]]
    #: 键 → 该键参与去重的 outcome 行数(去重残余披露)
    key_row_counts: dict[tuple[str, int, int], int]
    funnel: dict[str, Any] = field(default_factory=dict)


def canonical_align(outcome_rows: list[dict[str, Any]],
                    quarantine_counts: dict[str, int]) -> CanonicalAlignment:
    """outcomes 行 → 逐键权威 outcome(权威版本 §5.1-4 去重与降级)。

    规则(逐键):
    1. 剔除 recovered 行(schema 注释明言「训练侧可剔」);
    2. 带标签行优先(killed≠None 的行存在时只在其中选——晚行 None 会
       系统性覆盖早行标签,且丢的偏向负局);
    3. 带标签行内按 source 档次('' /缺失 > loss_page > 其余回填族);
    4. 同档并行取 ts 最新(ISO 字符串字典序 = 时序;并列取流内后行,
       append-only 下即后写);
    5. 全行 killed=None 才丢标签(降级自然吸收:优先档行 None 而低档行
       有标签时低档行胜出,挽回数单列披露)。
    """
    by_key: dict[tuple[str, int, int], list[tuple[int, dict[str, Any]]]] = (
        defaultdict(list))
    recovered_dropped = 0
    quarantined_rows = 0
    for idx, row in enumerate(outcome_rows):
        reason = run_quarantine_reason(row.get('run_id'))
        if reason is not None:
            quarantined_rows += 1
            continue
        if str(row.get('source') or '') == 'recovered':
            recovered_dropped += 1
            continue
        by_key[_join_key(row)].append((idx, row))

    canonical: dict[tuple[str, int, int], dict[str, Any]] = {}
    key_row_counts: dict[tuple[str, int, int], int] = {}
    dup_keys = 0
    rescues = 0
    for key, rows in by_key.items():
        key_row_counts[key] = len(rows)
        if len(rows) > 1:
            dup_keys += 1
        labeled = [(i, r) for i, r in rows if r.get('killed') is not None]
        pool = labeled if labeled else rows
        if labeled and min(source_tier(r.get('source')) for _i, r in pool) \
                > min(source_tier(r.get('source')) for _i, r in rows):
            rescues += 1
        best = max(pool, key=lambda x: (
            -source_tier(x[1].get('source')),
            str(x[1].get('ts') or ''),
            x[0],
        ))
        canonical[key] = best[1]

    funnel = {
        'outcome_rows_quarantined': quarantined_rows,
        'recovered_rows_dropped': recovered_dropped,
        'outcome_keys_total': len(by_key),
        'outcome_keys_duplicate': dup_keys,
        'label_priority_rescues': rescues,
        'quarantined_runs': dict(quarantine_counts),
    }
    return CanonicalAlignment(canonical, key_row_counts, funnel)


def align_decisions_snapshots(
    decision_rows: list[dict[str, Any]],
) -> tuple[dict[tuple[str, int, int], dict[str, Any]], int]:
    """decisions 行 → (逐键末帧快照, 隔离行数)(权威版本 §5.1-3:快照 = 该键
    最后一帧,不问帧的 node_type——持卡改节点局恰是最会改节点的局,
    按帧类型过滤 = 选择偏差)。"""
    by_key: dict[tuple[str, int, int], tuple[int, dict[str, Any]]] = {}
    quarantined = 0
    for idx, row in enumerate(decision_rows):
        if run_quarantine_reason(row.get('run_id')) is not None:
            quarantined += 1
            continue
        by_key[_join_key(row)] = (idx, row)
    return {k: v[1] for k, v in by_key.items()}, quarantined


# ===== 训练样本行与幅度样本表 =====

def is_censored_hp(hp_after: int) -> bool:
    """删失判定单一口径:hp_after ∈ {0,1} 即删失。

    伤害被血量吸收——归零行与首保底剩 1 行均属截断观测(真实采样值
    ≥ 观测值);偶然落在 {0,1} 的未截断行会被误标,误标率如实披露。
    """
    return int(hp_after) in (0, 1)

def _snapshot_features(snapshot: dict[str, Any],
                       node_type: str) -> FeatureVector:
    """快照行 + 权威 node_type → 特征向量(行侧适配单一入口)。"""
    return features_from_decision_row(snapshot, node_type=node_type)


def extract_training_corpus(
    inputs: list[CorpusInput],
) -> dict[str, Any]:
    """canonical 全管线:对齐 → 战斗过滤 → join → 标签 → 特征行。

    返回产物 dict(training_rows/amplitude_samples/meta 三件的内容);
    落盘由 :func:`write_artifacts` 负责(纯函数可测,零写副作用)。
    """
    decisions_all: list[dict[str, Any]] = []
    outcomes_all: list[dict[str, Any]] = []
    quarantine_counts: dict[str, int] = defaultdict(int)
    for inp in inputs:
        decisions_all.extend(inp.decisions_rows)
        outcomes_all.extend(inp.outcomes_rows)
    for row in (*decisions_all, *outcomes_all):
        reason = run_quarantine_reason(row.get('run_id'))
        if reason is not None:
            rid = str(row.get('run_id') or '')
            quarantine_counts[f'{rid}({reason})'] += 1

    align = canonical_align(outcomes_all, dict(quarantine_counts))
    snapshots, dec_quarantined = align_decisions_snapshots(decisions_all)

    drop_buckets: dict[str, int] = defaultdict(int)

    def drop(row: dict[str, Any], reason: str) -> None:
        src = row.get('source')
        bucket = _bucket(src, int(row.get('plane') or 0))
        drop_buckets[f'{reason}@{bucket}'] += 1

    battle_keys = 0
    battle_rows = 0
    labeled_rows: list[dict[str, Any]] = []
    amplitude: list[dict[str, Any]] = []
    mnar: dict[str, dict[str, int]] = defaultdict(lambda: {'keys': 0, 'missing': 0})
    amp_excluded = {'hp_after_none': 0, 'hp_before_none': 0}
    keys_no_label = 0
    keys_no_frames = 0

    for key, outcome in align.canonical.items():
        node_raw = outcome.get('node_type')
        node_type = normalize_node_type(node_raw)
        if node_type not in BATTLE_NODE_TYPES:
            drop(outcome, 'non_battle_key')
            continue
        battle_keys += 1
        battle_rows += align.key_row_counts.get(key, 1)
        # source 族标签:'' = 旧 schema 真值族(设计期敏感性表口径
        # 「真值行」;规范读端保证键在场且缺省 '');None 防御同 ''。
        src_family = str(outcome.get('source') or '')
        mnar[src_family]['keys'] += 1

        snapshot = snapshots.get(key)
        if snapshot is None:
            keys_no_frames += 1
            drop(outcome, 'no_decisions_frames')
            continue

        killed = outcome.get('killed')
        if killed is None:
            keys_no_label += 1
            drop(outcome, 'no_label_key')
            # MNAR 缺失率只计「标签缺失」键(无帧丢弃是另一类丢弃,
            # 不混入缺失率分母语义;权威版本 §5.1 敏感性表口径)。
            mnar[src_family]['missing'] += 1
            continue

        vec = _snapshot_features(snapshot, node_type)
        labeled_rows.append({
            'run_id': key[0], 'plane': key[1], 'round_num': key[2],
            'node_type': node_type,
            'label': bool(killed),
            'source': str(outcome.get('source') or ''),
            'target_comp_snapshot': str(snapshot.get('target_comp') or ''),
            'features': vec.as_dict(),
        })

        if not killed:
            hp_after = outcome.get('hp_after')
            hp_before = (snapshot.get('state') or {}).get('hp')
            if hp_after is None:
                amp_excluded['hp_after_none'] += 1
            elif hp_before is None:
                amp_excluded['hp_before_none'] += 1
            else:
                hp_after_i = int(hp_after)
                hp_before_i = int(hp_before)
                amplitude.append({
                    'run_id': key[0], 'plane': key[1], 'round_num': key[2],
                    'node_type': node_type,
                    'hp_before': hp_before_i, 'hp_after': hp_after_i,
                    'damage': hp_before_i - hp_after_i,
                    'censored': is_censored_hp(hp_after_i),
                    'hp_confidence': outcome.get('hp_confidence'),
                    'source': str(outcome.get('source') or ''),
                    'features': vec.as_dict(),
                })

    labeled_keys = len(labeled_rows)
    win_keys = sum(1 for r in labeled_rows if r['label'])
    meta = {
        'schema': 'sim_power_model_v1.extraction',
        'funnel': {
            **align.funnel,
            'decisions_rows_quarantined': dec_quarantined,
            'battle_keys': battle_keys,
            'battle_rows': battle_rows,
            'labeled_keys': labeled_keys,
            'win_keys': win_keys,
            'keys_no_decisions_frames': keys_no_frames,
            'keys_no_label': keys_no_label,
            'amplitude_rows': len(amplitude),
            'amplitude_excluded': amp_excluded,
        },
        'three_numbers_repin': {
            'battle_outcomes_rows': battle_rows,
            'battle_outcomes_keys': battle_keys,
            'labeled_keys': labeled_keys,
            'win_events': win_keys,
            'param_budget_floor': win_keys // 10,
            'budget_gate_triggered': (win_keys // 10) < 6,
            'caliber_note': '预算 = 胜事件键数/10 向下取整(sim-power-model §4.3;'
                            '行级 battle_outcomes_rows 为 raw 参考口径)',
        },
        'drop_buckets_by_source_plane': dict(sorted(drop_buckets.items())),
        'mnar_missing_by_source': {
            k: {**v, 'missing_rate': (v['missing'] / v['keys'])
                if v['keys'] else None}
            for k, v in sorted(mnar.items())
        },
        'feature_names': list(FEATURE_NAMES),
    }
    return {
        'training_rows': labeled_rows,
        'amplitude_samples': amplitude,
        'meta': meta,
    }


# ===== target_comp 统计 =====

#: 组合标签族前缀(「过渡配方·X(+Y)」形态;取大定义 = :func:`best_line`)。
_TRANSITION_LABEL_PREFIX = '过渡配方·'


def target_comp_stats(decision_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """顶层 target_comp 覆盖率与值域构成(两族 + 其他逐值披露)。

    覆盖率 = 非空行数 / 总行数;值域两族 = 注册套名(COMP_LIBRARY
    注册名)/ 组合标签(「过渡配方·」前缀);两族都不命中 = 其他
    (逐值计数,不猜归类)。"""
    comp_names = {c.name for c in COMP_LIBRARY}
    total = 0
    non_null = 0
    registered: dict[str, int] = defaultdict(int)
    transition_labels: dict[str, int] = defaultdict(int)
    other: dict[str, int] = defaultdict(int)
    for row in decision_rows:
        total += 1
        val = row.get('target_comp')
        if val is None or str(val) == '':
            continue
        non_null += 1
        s = str(val)
        if s in comp_names:
            registered[s] += 1
        elif s.startswith(_TRANSITION_LABEL_PREFIX):
            transition_labels[s] += 1
        else:
            other[s] += 1
    return {
        'rows_total': total,
        'rows_non_null': non_null,
        'coverage': (non_null / total) if total else None,
        'registered_comp_name': {
            'rows': sum(registered.values()),
            'distinct_values': len(registered),
            'values': dict(sorted(registered.items(),
                                  key=lambda x: -x[1])),
        },
        'transition_recipe_label': {
            'rows': sum(transition_labels.values()),
            'distinct_values': len(transition_labels),
            'values': dict(sorted(transition_labels.items(),
                                  key=lambda x: -x[1])[:20]),
        },
        'other': {
            'rows': sum(other.values()),
            'values': dict(sorted(other.items(), key=lambda x: -x[1])),
        },
    }


# ===== 许可集普查(逐目录 source 裁定)=====

def survey_directory(dir_path: Path) -> dict[str, Any]:
    """单目录普查证据(首尾行 run_id/ts/schema 指纹;缺文件如实标注)。

    裁定规则(证据 → source):run_id 带 ``sim_`` 前缀 = sim 批;
    state 子键含 ``board_factions`` = sim 批(该键名仅见于 sim 批产物,
    );两证皆无 = 实机。拿不准(证据缺失/矛盾)→ 标
    pending 并给证据。本函数是运行时普查工具,只读不写。"""
    dec_path = dir_path / 'decisions.jsonl'
    out_path = dir_path / 'outcomes.jsonl'
    evidence: dict[str, Any] = {
        'decisions_exists': dec_path.exists(),
        'outcomes_exists': out_path.exists(),
        'decisions_rows': None, 'outcomes_rows': None,
        'first_run_id': None, 'last_run_id': None,
        'first_ts': None, 'first_ts_is_iso': None,
        'state_has_board_factions': None,
        'manifest_has_seeds': (dir_path / 'manifest.json').exists(),
    }
    if dec_path.exists():
        lines = [ln for ln in dec_path.read_text(encoding='utf-8')
                 .splitlines() if ln.strip()]
        evidence['decisions_rows'] = len(lines)
        try:
            first = json.loads(lines[0])
            last = json.loads(lines[-1])
            evidence['first_run_id'] = first.get('run_id')
            evidence['last_run_id'] = last.get('run_id')
            evidence['first_ts'] = first.get('ts')
            ts = first.get('ts')
            evidence['first_ts_is_iso'] = isinstance(ts, str) and \
                'T' in ts and len(ts) >= 19
            state = first.get('state') or {}
            evidence['state_has_board_factions'] = \
                isinstance(state, dict) and 'board_factions' in state
        except json.JSONDecodeError:
            evidence['parse_error'] = True
    if out_path.exists():
        with out_path.open(encoding='utf-8') as f:
            evidence['outcomes_rows'] = sum(1 for ln in f if ln.strip())
    return evidence


def adjudicate_source(evidence: dict[str, Any]) -> str:
    """普查证据 → source 裁定('sim' / 'live' / 'pending')。"""
    rid = str(evidence.get('first_run_id') or '')
    if rid.startswith('sim_'):
        return 'sim'
    if evidence.get('state_has_board_factions'):
        return 'sim'
    if evidence.get('first_ts_is_iso') and rid.startswith('run_'):
        return 'live'
    return 'pending'


def build_survey_record() -> dict[str, Any]:
    """许可集普查记录(sim-power-model §8-1 第①步;运行时读候选目录证据)。

    覆盖面:已核实实机(live)/ 待盘点候选(p3_ab 4 目录 + gs1 smoke
    2 目录)/ 默认排除面(sim 批根逐文件计数,铁律 2)。"""
    root = get_project_root()
    candidates = [
        root / '.debug' / 'currency_war' / 'p3_ab' / 'ab_base_head',
        root / '.debug' / 'currency_war' / 'p3_ab' / 'ab_new_p3',
        root / '.debug' / 'currency_war' / 'p3_ab' / 'probe_base',
        root / '.debug' / 'currency_war' / 'p3_ab' / 'probe_new',
        root / '.debug' / 'currency_war' / '2026-09-21-gs1-exit-channel-ab'
        / 'smoke_base',
        root / '.debug' / 'currency_war' / '2026-09-21-gs1-exit-channel-ab'
        / 'smoke_fix',
    ]
    entries: list[dict[str, Any]] = []
    for d in (*candidates,):
        ev = survey_directory(d) if d.exists() else {'missing': True}
        entries.append({
            'path': str(d.relative_to(root)),
            'source': adjudicate_source(ev),
            'disposition': 'excluded(候选裁定 sim,铁律 2)',
            'evidence': ev,
        })
    sim_files = sorted(SIM_ROOT.glob('*/decisions.jsonl')) \
        if SIM_ROOT.exists() else []
    entries.insert(0, {
        'path': str(LIVE_DIR.resolve().relative_to(root)),
        'source': 'live',
        'disposition': 'licensed(已核实实机)',
        'evidence': survey_directory(LIVE_DIR) if LIVE_DIR.exists() else {},
    })
    entries.append({
        'path': str(SIM_ROOT.resolve().relative_to(root)),
        'source': 'sim',
        'disposition': 'excluded(sim 批根,铁律 2:全目录默认排除;'
                       f'decisions 文件数 = {len(sim_files)})',
        'evidence': {'decisions_file_count': len(sim_files)},
    })
    return {'rule': '逐目录裁定 source(实机/sim);判定证据 = 首行 '
                    'run_id 前缀 / state.board_factions 键 / ts 形态',
            'entries': entries}


# ===== 产物落盘与运行入口 =====

def write_artifacts(result: dict[str, Any], out_dir: Path,
                    extra_meta: dict[str, Any]) -> list[Path]:
    """三件产物落盘(meta.json / training_rows.jsonl /
    amplitude_samples.jsonl);返回写入路径。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {**result['meta'], **extra_meta}
    meta_path = out_dir / 'meta.json'
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                         encoding='utf-8')
    rows_path = out_dir / 'training_rows.jsonl'
    with rows_path.open('w', encoding='utf-8') as f:
        for row in result['training_rows']:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    amp_path = out_dir / 'amplitude_samples.jsonl'
    with amp_path.open('w', encoding='utf-8') as f:
        for row in result['amplitude_samples']:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    return [meta_path, rows_path, amp_path]


def post_quarantine_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """行集的 run 隔离过滤(统计口径单一入口;run_extraction 的
    target_comp 统计传隔离后行 = 抽取语料口径)。"""
    return [r for r in rows
            if run_quarantine_reason(r.get('run_id')) is None]


def run_extraction(license_dirs: list[Path] | tuple[Path, ...],
                   out_dir: Path,
                   sim_root: Path | None = None) -> dict[str, Any]:
    """一次完整抽取(守卫 → 载入 → 管线 → 指纹 → 落盘)。"""
    inputs = load_licensed_corpus(license_dirs, sim_root)
    result = extract_training_corpus(inputs)
    extra = {
        'source_fingerprint': source_fingerprint(inputs),
        'survey': build_survey_record(),
        'target_comp': target_comp_stats(post_quarantine_rows(
            [row for inp in inputs for row in inp.decisions_rows])),
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'license_dirs': [str(Path(d).resolve()) for d in license_dirs],
    }
    paths = write_artifacts(result, out_dir, extra)
    return {'meta': {**result['meta'], **extra}, 'paths': paths}


def main() -> None:
    """CLI 入口(默认许可 = live 流根;产物落 .debug 指定目录)。"""
    parser = argparse.ArgumentParser(
        description='CW 战力模型语料抽取器(旧流;'
                    'sim-power-model §8-1)')
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT_DIR,
                        help='产物目录(默认 .debug gitignored 区)')
    parser.add_argument('--license-dir', type=Path, action='append',
                        default=None,
                        help='许可源目录(可重复;缺省 = telemetry/live)')
    args = parser.parse_args()
    dirs = args.license_dir or list(DEFAULT_LICENSE_DIRS)
    result = run_extraction(dirs, args.out)
    t = result['meta']['three_numbers_repin']
    print(f"[extract] 产物: {[str(p) for p in result['paths']]}")
    print(f"[extract] 三数重钉: 战斗类结局(键)= {t['battle_outcomes_keys']}"
          f" / 有标签 = {t['labeled_keys']} / 胜事件 = {t['win_events']}"
          f" → 参数预算 = {t['param_budget_floor']}"
          f"(重钉门{'触发' if t['budget_gate_triggered'] else '未触发'})")


if __name__ == '__main__':
    main()
