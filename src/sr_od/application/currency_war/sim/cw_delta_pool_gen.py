"""货币战争 · Δ池快照生成核心(生产 live 流 → 主仓提交快照数据层)。

2026-08-25 W109(ADR-0344)起本模块是生成器的**唯一核心**(原
tools/cw/gen_delta_pool_snapshot.py 迁入;tools 侧保留 CLI 壳)——
实机局终自动再生管线(cw_telemetry 局终钩子)与 CLI 共用此入口,
「生成器是池的唯一入口」防线随核心走。

数据源:telemetry/live/{decisions,outcomes}.jsonl(.debug/currency_war
下,2026-09-07 布局裁定;生产遥测 append 流)。配对口径与
pool._pool_from_replay **单件
同源**(ADR-0582:双方共同消费 pool.pair_outcome_rows_to_pool,
「行级过滤+配对」单一实现,禁再长镜像循环):decisions 每轮取
末行板深,outcomes 同 run 相邻行 hp 差分;合成行
(source='synthetic_supply')与低可信行(hp_confidence<0.9)不作
差分端点——移行桥接重配对(ADR-0582;快照不是事件,判据语义
= ADR-0577 装配端 _settlement_hp_usable 延伸到 Δ池消费面)。
桶键(ADR-0279,批⑬):battle=成型度 rung(结算前 board_before +
decisions deployed join);reward/supply=深度桶;**boss=
净星深桶(ADR-0404,W240:上场件 Σ(star−1),deployed_star_depth
同式——修 W238 实证的 Σboard 键升星方向冲突)**;
**encounter=rung 桶(v11,ADR-0407,W250:键查证后 depth 键下
期望伤害真平而 rung 键梯度显著,与 battle 同源 _engines_count
(单一源=cw_deploy_logic.engines_count,W279 上移;cw_sim 侧为薄委托),
解批⑬ F1「样本不足暂缓」)**。
**plane 维(ADR-0362,W157)**:桶键外再加位面层——差分归属
「后行位面」(P1r9→P2r1 跨位面差分归 plane=2),P1/P2 桶彻底
分离;修 W156 发现的既有 P1 池 P2 污染(44 条 plane=2 差分混在
无位面维的池里,含 16 条跨位面差分)。

产出:src/sr_od/application/currency_war/data/cw_delta_pool_data.py ——
SNAPSHOT {节点: {位面: {桶键: [Δ]}}} + META(构成/过滤/指纹)。
主仓提交(先例:REFRESH_PROB 实测概率表在 cw_shop_odds);CI 与
跨机可复现基准靠它(裸 .debug 池随实机追加漂移,不可作基准)。

防自中毒(对抗审查定谳):**源目录断言 ≠ sim 批根** —— sim 批量
落盘(telemetry/sim)若混进池源即「sim 校准 sim」回路;生成器是池的
唯一入口,防线落在这里,不靠调用方自觉。防线三道(池数据防线
一脉,ADR-0582):①目录守卫(_assert_guards,源 ≠ sim 批根);
②run 级隔离(前缀规则 + 显式名单,拦「进错目录的 run」——
2026-09-08 假游戏局 run_id=fake_20260908 落进 live 生产流实证,
目录守卫对此失明);③塌缩守卫(源行数账较现提交快照塌缩即拒绝
覆写、保留现快照——同日微型语料三次静默覆盖提交快照,对账
正本 = ADR-0595 与 2026-09-08 对账记录)。

半写行容错:生产 append 进行中尾行可能撕裂(JSONDecodeError)——
跳过+计数告警,不中断、不静默(计数进 META)。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from one_dragon.utils.file_utils import get_project_root
from sr_od.application.currency_war.kernel.cw_observe import (
    DEFAULT_REPLAY_DIR as REPLAY_DIR,  # 生产流根单一源(telemetry/live)
)
from sr_od.application.currency_war.kernel.cw_observe import (
    SIM_ROOT as SIM_RUNS_DIR,  # sim 批根单一源(telemetry/sim)
)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

REPO = get_project_root()
DATA_PY = REPO / 'src/sr_od/application/currency_war/data/cw_delta_pool_data.py'

# 写目标白名单守卫(同 gen_factions 范式):本生成器只允许写
# _data.py 数据层文件;判断层/策略文件永不在此列。
WRITABLE_TARGETS = (DATA_PY,)

#: 退役第一步冻结标志(战斗分支切 cw_coarse_battle 后置位):
#: True = regenerate_snapshot 一律 raise,快照停更。
#: F6 语料治理批(编排者任务书,Δ池 P1 桶重损治理)裁决撤销:
#: 快照仍辖 reward/supply 池与 delta 对照臂消费,含伪影毒行的旧
#: 快照必须重生成治理,停更约束随之解除(战斗类主路径消费已摘,
#: 再生只影响校准数据面,不触策略行为)。
_DELTA_POOL_FROZEN: bool = False


class DeltaPoolFrozen(RuntimeError):
    """Δ池快照再生已被冻结标志拦下(退役第一步,见模块内标志注)。"""


# 节点类型归一表单一源 = pool.NT_MAP(ADR-0582 随共享配对件收拢;
# 本模块经 build_pool 内惰性 import 消费,保持模块级轻载——局终
# 钩子 ledger_hooks 直接 import 本模块)。
DEPTH_BUCKET_W = 3   # 与 cw_sim._DEPTH_BUCKET_W 同值(指纹输入)
# ADR-0306:桶覆盖披露门槛(检查项 delta_pool_bucket_coverage 判据)
# —— 各桶 n≥10 或进 bucket_poverty 显式披露;n<10 的桶真值方向
# 不可靠,消费方(胜率外推/方向判断)须声明边界。
BUCKET_COVERAGE_MIN_N = 10
# ADR-0306:battle rung 键域(0-4,与 pool.live_delta_for 同域);
# 域内缺失的 rung 桶也进贫困披露(「缺」≠「空桶可忽略」)。
BATTLE_RUNG_DOMAIN = range(0, 5)


def _assert_guards(src_dir: Path) -> None:
    """写目标白名单 + 源目录 ≠ sim 批根(防 sim 数据回灌校准池)。"""
    for t in WRITABLE_TARGETS:
        if t.suffix == '.py' and not t.name.endswith('_data.py'):
            raise RuntimeError(f'生成器写目标非法: {t}(只写 _data.py 数据层)')
    src_resolved = src_dir.resolve()
    sim_resolved = SIM_RUNS_DIR.resolve()
    if src_resolved == sim_resolved or sim_resolved in src_resolved.parents:
        raise RuntimeError(
            f'池源目录非法: {src_resolved} 位于 sim 批根下——'
            'sim 产出回灌校准池 = 自中毒回路(对抗审查定谳);'
            '池源只能是生产 live 流根(telemetry/live)')


# ===== run 级隔离机制(池数据防线,机制化双轨)=====
# 为什么机制化:逐条名单每类新污染源都要先出一次事故再补条目,
# 防线永远追着事故跑;前缀规则按「来源类别」拦截,显式名单只留
# 不成类的一次性事故局。为什么必须落到 run 粒度:目录守卫
# (_assert_guards)只辖源目录,拦不住写进生产 live 流的非真实
# run——2026-09-08 假游戏局 fake_20260908 混在 live 源里触发局终
# 自动再生(ADR-0595),是本机制的直接实证。
# 关联:ADR-0582(池生成器数据防线一脉);新增类别在
# QUARANTINED_RUN_PREFIXES 登记(带一句来源语义)。

#: 前缀规则(类别级隔离):run_id 以这些前缀开头的 run 一律不入池。
#: 消费统一走 _run_quarantine_reason,禁散写 startswith/in 判断。
QUARANTINED_RUN_PREFIXES: dict[str, str] = {
    # 假游戏/调试注入局:行内 hp/板深是造数非屏面观测,入池即
    # 「用编造的对局校准真实策略」。
    'fake_': '假游戏/调试注入局(非真实对局观测)',
    # sim 批 run(sim/runner.write_batch_ledger 以批目录名为 run_id
    # 前缀,目录形如 sim_<stamp>_n..._s...):sim 产出回灌池 =
    # 「sim 校准 sim」自中毒回路(对抗审查定谳,与 _assert_guards
    # 目录守卫同一裁决的 run 粒度延伸)。
    'sim_': 'sim 批 run(sim 校准 sim 回路,同 _assert_guards 裁决)',
}

# 显式名单(个例级,不成类故不走前缀):这些 run 的遥测被判定不可信
# (双进程写侧竞争/观测链断),生成器**默认物理排除**防回灌
# (只「作废判读信任」不排池,下次全量重生成会悄悄流回快照)。
# 增删条目在此登记(带一句事故原因),源头治理靠 daemon 修复。
QUARANTINED_RUNS: dict[str, str] = {
    # 2026-08-22 双进程事故:18:56 restart orphan 残留,两代
    # server 并行写 outcomes(killed 全 None=写侧竞争表征)。
    'run_20260822_185613': '双进程写竞争事故局(局55)',
    'run_20260822_191028': '双进程写竞争事故局(局56/57 重启交错)',
}


def _run_quarantine_reason(run_id: object) -> str | None:
    """run 隔离判据单一源:前缀规则优先(类别级),显式名单兜底(个例级)。

    返回隔离原因(命中,不入池)或 None(放行);快照生成器
    build_pool 与 auto 池 pool._pool_from_replay 的 decisions/outcomes
    两循环共用(ADR-0595:适用范围含 auto 池),禁再散写名单判断。
    """
    rid = run_id if isinstance(run_id, str) else ''
    for prefix, reason in QUARANTINED_RUN_PREFIXES.items():
        if rid.startswith(prefix):
            return reason
    explicit = QUARANTINED_RUNS.get(rid)
    return explicit if explicit else None


# ===== 塌缩守卫(池数据防线)=====
# 为什么需要:遥测流是 append-only,正常局终再生只会让源行数账
# 上升;一旦再生源比提交快照的行数账大幅缩水(语料被截断/迁移
# 丢失/换根后新树只有微型语料),再生会拿残缺语料静默覆盖全量
# 快照。实证:2026-09-08 池再生源迁 telemetry/live 后仅 3 run
# 144 行,假游戏局触发局终再生把 16391 行全量语料的提交快照
# 覆写成微语料快照(行数账 144/18637≈0.8%,当日 11:54-12:05 三次;
# 对账正本 = ADR-0595 与 2026-09-08 对账记录)——
# 既有目录守卫与 run 隔离都
# 不辖「量」,必须有独立的量级守卫。
#: 阈值 = 源行数账 < 现快照行数账 × 此比例 → 拒绝再生覆写。
#: 为什么取 50%:合法下跌只剩「语料归档/显式裁剪」两类人工操作,
#: 都应显式申报而非被再生静默吞掉;50% 把微语料覆盖(实测 0.8%)
#: 与正常局终增量(每次 ≥99%)分在两侧,同时留足单次数据清洗
#: (合理裁剪 ~10-30%)不误伤的余量。
#: 边界:守卫按两流行数「总和」比较——单流截断(decisions 砍半时
#: 总和约 56%)可过闸,由 META unlabeled_dropped/桶贫困披露兜底
#: 显影;单流全灭则先撞「池为空」拒绝。
#: 基线来源(2026-09-09 穿透定谳,ADR-0612):必须是 git HEAD 提交版
#: 而非盘面文件——盘面可能已被一次未提交的塌缩再生改写,若以盘面
#: 为基线,塌缩件自我延续(微语料 vs 微语料永过闸;2026-09-08 三次
#: 静默覆写后 286/48 微语料再生在守卫在场下持续放行即实证),守卫
#: 语义与 ADR-0595「提交快照持续受保护」的申报才真正对齐。无 HEAD
#: 版本(首次再生/仓外写目标)退回盘面读取,放行语义不变。
SNAPSHOT_COLLAPSE_MIN_RATIO: float = 0.5


class SourceCorpusCollapse(RuntimeError):
    """再生源语料较现提交快照塌缩,守卫拒绝覆写(语义见阈值常量注)。"""


def _head_data_py_text(data_py: Path) -> str | None:
    """读 git HEAD 提交版数据文件文本(塌缩守卫基线来源,见常量块注)。

    只读 ``git show HEAD:<相对路径>``;任何失败(仓外写目标/未跟踪/
    无 git/超时)返回 None,由调用方退回盘面读取——退回通道即旧行为,
    测试仓 tmp_path 写目标(仓外)全部经此通道维持原语义。
    """
    try:
        rel = data_py.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return None
    try:
        proc = subprocess.run(
            ['git', 'show', f'HEAD:{rel}'], cwd=str(REPO),
            capture_output=True, encoding='utf-8', errors='replace',
            timeout=10)
    except Exception:   # noqa: BLE001 无 git 环境/进程异常一律退回盘面
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    return proc.stdout


def _committed_source_rows(data_py: Path) -> dict[str, int] | None:
    """读守卫基线里的语料行数账:git HEAD 提交版优先,盘面文件兜底。

    基线语义 = 「不许比提交真值少」(2026-09-09 穿透定谳,ADR-0612:
    旧实现读盘面,盘面被未提交塌缩改写后守卫即对提交真值失明)。
    两处都拿不到行数账(首次再生无现状可保护/老快照无此披露)→
    None,守卫无从比对即放行——守卫语义是「不许比提交真值少」,不是
    「必须比某阈值多」。为什么 exec 读文本而非 import:import 拿
    进程内已加载模块,长跑进程里与磁盘现态可能脱节(他进程已重写
    文件);exec 文本(HEAD 版或盘面产物,自包含)才是被比对的真值
    (测试仓 exec 产物先例同法)。
    """
    text = _head_data_py_text(data_py)
    if text is None:
        if not data_py.exists():
            return None
        text = data_py.read_text(encoding='utf-8')
    ns: dict = {}
    exec(text, ns)   # noqa: S102 只执行本生成器产物
    rows = (ns.get('META') or {}).get('source_rows')
    return rows if isinstance(rows, dict) else None


def _assert_no_source_collapse(data_py: Path,
                               source_rows: dict[str, int]) -> None:
    """塌缩守卫:源行数账低于现快照行数账的阈值比例 → raise 拒绝覆写。

    现快照原样保留(不写 data_py),差异申报进异常文案;局终钩子
    的 best-effort 捕获(ADR-0344:再生失败只记警告不阻塞对局)
    就是告警日志通道,文案自含两侧数字供申报对账。
    """
    baseline = _committed_source_rows(data_py)
    if baseline is None:
        return
    base_total = sum(int(v) for v in baseline.values())
    src_total = sum(int(v) for v in source_rows.values())
    if base_total <= 0 or src_total >= SNAPSHOT_COLLAPSE_MIN_RATIO * base_total:
        return
    raise SourceCorpusCollapse(
        f'再生源语料塌缩: 源行数账 {src_total} < 现快照行数账 '
        f'{base_total} × {SNAPSHOT_COLLAPSE_MIN_RATIO}(塌缩阈值,'
        '理由见 cw_delta_pool_gen 常量注)——已保留现快照未覆写;'
        f'源 {dict(sorted(source_rows.items()))} vs 快照基线 '
        f'{dict(sorted(baseline.items()))}。先核查语料去向(迁移/'
        '裁剪/流被截断)并显式申报,再恢复再生')


def _iter_jsonl(path: Path, skipped: dict) -> list[dict]:
    """逐行解析 jsonl;半写行(撕裂尾行)跳过+计数,不静默。"""
    out: list[dict] = []
    if not path.exists():
        skipped[str(path.name)] = skipped.get(str(path.name), 0)
        return out
    for ln in path.read_text(encoding='utf-8').splitlines():
        if not ln.strip():
            continue
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            skipped[path.name] = skipped.get(path.name, 0) + 1
    return out


def _star_depth_of(rows) -> int:
    """净星深 = cw_battle_calib._star_depth_from_rows 单一源(W240/ADR-0404
    boss 桶键;防池侧/sim 侧双公式漂移)。"""
    from sr_od.application.currency_war.kernel.cw_battle_calib import (
        _star_depth_from_rows,
    )
    return _star_depth_from_rows(rows)


def _raw_line_count(path: Path) -> int:
    """非空行计数(含半写撕裂行——增量盘点的原始账,配对口径另计)。"""
    if not path.exists():
        return 0
    return sum(1 for ln in path.read_text(encoding='utf-8').splitlines()
               if ln.strip())


def _win_stats(deltas: list, killed_list: list) -> dict:
    """ADR-0306:battle 桶胜率双口径统计(权威=killed,对照=Δ≥0)。

    - ``win_killed``:killed 已知行中 killed=True 占比(**权威口径**,
      消费方 = cw_sim.boss_win_p 的 rung≥3 外推);
    - ``win_delta``:全样本 Δ≥0 占比(旧口径,对照披露);
    - ``killed_known``/``killed_unknown``:胜率分母披露;
    - ``sign_disagree``:killed 已知行中两口径判定异号数。
    """
    known = [k for k in killed_list if k is not None]
    n_known = len(known)
    win_k = sum(1 for k in known if k)
    win_d = sum(1 for d in deltas if d >= 0)
    disagree = sum(
        1 for d, k in zip(deltas, killed_list, strict=False)
        if k is not None and bool(k) != (d >= 0))
    return {
        'win_killed': round(win_k / n_known, 4) if n_known else None,
        'win_delta': round(win_d / len(deltas), 4) if deltas else None,
        'killed_known': n_known,
        'killed_unknown': len(killed_list) - n_known,
        'sign_disagree': disagree,
    }


def _poverty_list(pool: dict, battle_killed: dict) -> list[str]:
    """ADR-0306 件2:桶贫困披露(n<10 的桶 + battle rung 域缺桶)。

    ADR-0362(W157):battle rung 域/贫困披露只辖 **plane=1** 桶
    (检查项 delta_pool_bucket_coverage 的判据消费 plane-1 视图,
    键格式不变);plane≥2 桶整体贫困(语料 44 行,条件化分桶
    不做)以 ``p2:`` 前缀单列披露,不进 plane-1 判据。
    """
    out: list[str] = []
    p1 = (pool.get('battle') or {}).get(1) or {}
    for rg in BATTLE_RUNG_DOMAIN:
        v = p1.get(rg) or []
        if len(v) >= BUCKET_COVERAGE_MIN_N:
            continue
        out.append(f'battle:桶{rg}(n={len(v)})'
                   if v else f'battle:桶{rg}(缺)')
    for nt, planes in sorted((pool or {}).items()):
        for plane in sorted(k for k in planes if int(k) >= 2):
            for b, v in sorted(planes[plane].items(),
                               key=lambda x: int(x[0])):
                if len(v) < BUCKET_COVERAGE_MIN_N:
                    out.append(f'p2:{nt}:桶{b}(n={len(v)})')
        if nt == 'battle':
            continue   # battle 已按 rung 域单独披露
        buckets = planes.get(1) or {}
        for b, v in sorted(buckets.items(), key=lambda x: int(x[0])):
            if len(v) < BUCKET_COVERAGE_MIN_N:
                out.append(f'{nt}:桶{b}(n={len(v)})')
    return out


def build_pool(src_dir: Path, runs_filter: set[str] | None = None,
               ) -> tuple[dict, dict]:
    """构建 {节点: {位面: {桶键: [Δ]}}} + 构成 meta(auto 池同配对件)。

    桶键语义(ADR-0279,批⑬):battle=成型度 rung(结算前
    board_before + decisions deployed join 算希儿系);encounter/
    reward/supply=深度桶(批⑬ F1 encounter rung 样本不足暂沿用);
    boss=净星深桶(W240/ADR-0404:上场件 Σ(star−1),修 Σboard 键
    3合1 升星方向冲突)。
    plane 维(ADR-0362,W157):差分归属后行位面,P1/P2 分桶。
    行级过滤(ADR-0582):合成行/低可信行不作 hp 差分端点,移行
    桥接重配对——语义与实现单一源 =
    pool.pair_outcome_rows_to_pool(本函数只做读取/runs 过滤/
    run 隔离与 META 组装,禁再长配对逻辑)。

    守卫在函数体内生效(审查#4:只在 main 锁不住 import 复用)。
    """
    _assert_guards(src_dir)
    _source_rows = {
        'decisions.jsonl': _raw_line_count(src_dir / 'decisions.jsonl'),
        'outcomes.jsonl': _raw_line_count(src_dir / 'outcomes.jsonl'),
    }
    skipped: dict[str, int] = {}
    quarantined_hits: set[str] = set()
    boards: dict = {}
    star_depths: dict = {}   # W240/ADR-0404:boss 桶键=净星深
    deployed_names: dict = {}
    for d in _iter_jsonl(src_dir / 'decisions.jsonl', skipped):
        if runs_filter and d.get('run_id') not in runs_filter:
            continue
        if _run_quarantine_reason(d.get('run_id')) is not None:
            quarantined_hits.add(d.get('run_id'))
            continue
        st = d.get('state') or {}
        b = st.get('board') or {}
        k = (d.get('run_id'), d.get('plane'), d.get('round_num'))
        boards[k] = sum(b.values())
        star_depths[k] = _star_depth_of(st.get('deployed'))
        deployed_names[k] = frozenset(
            x.get('char_id') or '' for x in (st.get('deployed') or [])
            if isinstance(x, dict))
    seqs: dict[str, list[dict]] = {}
    for o in _iter_jsonl(src_dir / 'outcomes.jsonl', skipped):
        if o.get('hp_after') is None:
            continue
        if runs_filter and o.get('run_id') not in runs_filter:
            continue
        if _run_quarantine_reason(o.get('run_id')) is not None:
            quarantined_hits.add(o.get('run_id'))
            continue
        seqs.setdefault(o.get('run_id'), []).append(o)
    # 共享配对件(ADR-0582:与 pool._pool_from_replay 单件同源;
    # 惰性 import 保持本模块轻载——局终钩子经 ledger_hooks 直连)。
    from sr_od.application.currency_war.sim.pool import (
        pair_outcome_rows_to_pool,
    )
    pool, stats = pair_outcome_rows_to_pool(
        seqs, boards=boards, star_depths=star_depths,
        deployed_names=deployed_names)
    battle_killed: dict = stats['battle_killed']
    meta = {
        'source_dir': str(src_dir),
        'runs': stats['runs'],
        'runs_filter': (sorted(runs_filter) if runs_filter else 'all'),
        'skipped_lines': skipped,
        'unlabeled_dropped': stats['unlabeled_dropped'],
        'hp0_transient_dropped': stats['hp0_transient_dropped'],
        # ADR-0582:端点资格过滤剔除账(与 hp0_transient_dropped
        # 并列如实披露)——synthetic=补给合成行(快照鬼值);
        # hp_conf=低可信真实行(本语料全部是终局 loss_page hp=0
        # 死亡腿,连带剔除其配对腿约 75 对)。
        'synthetic_supply_dropped': stats['synthetic_supply_dropped'],
        'hp_conf_dropped': stats['hp_conf_dropped'],
        # r378b:隔离清单实际命中的 run(没命中=清单过期,该清理)
        'quarantined_hits': sorted(quarantined_hits),
        'depth_bucket_w': DEPTH_BUCKET_W,
        # ADR-0279(批⑬):battle 桶键=rung(真值表随重生成锁定;
        # cw_sim_checks.BATTLE_RUNG_TRUTH 漂移报警消费此表口径)。
        # ADR-0306:逐桶胜率统计——权威口径 killed(结算屏 extras),
        # Δ≥0 仅作对照披露;killed=None 行只入 Δ 分布不入胜率
        # (killed_known 为分母);sign_disagree=killed 已知行中
        # 两口径判定不同号的样本数(实测 0/61,ADR-0306 件3)。
        'battle_rung': {
            str(b): dict(
                {'n': len(v), 'mean': round(sum(v) / len(v), 2)},
                **_win_stats(v, battle_killed.get(b, [])))
            for b, v in sorted(
                ((pool.get('battle') or {}).get(1) or {}).items())},
        # ADR-0306 件1:语料行数账(重生成时的增量盘点基准)——
        # 下次扩容批以 outcomes/decisions 现行数 vs 本值为增量。
        'source_rows': dict(_source_rows),
        # ADR-0306 件2:桶贫困显式披露(n<10 或 battle rung 域缺桶)
        # —— 检查项 delta_pool_bucket_coverage 消费;「语料不足」
        # 如实报,不虚构样本。
        'bucket_poverty': _poverty_list(pool, battle_killed),
        'note': 'v2 只收可信标签行(2026-08-22 retrofix 后:死链'
                '历史 node_type 置 None 已丢弃计数);事故局物理排除'
                '(QUARANTINED_RUNS,r378b);跨策略版本混杂'
                '已知(一轮#10),过滤走 --runs 重生成;'
                'sampler v3(ADR-0279,批⑬)battle 桶键 depth→rung'
                '(成型度一维分桶),encounter/boss 维持 depth 桶;'
                'v4(ADR-0292,批㉗)reward/supply 改 Δ池经验分布采样;'
                'v5(ADR-0306)胜判定权威口径=killed(结算屏 extras;'
                'Δ 为派生量,异号实证 0——0305 的「3/9 异号」系'
                'tier×core 与 rung 两分桶错位对照的伪影;2026-08-25'
                '全量复审计 killed 已知行 84 条异号 0),META 逐桶'
                '双口径胜率+桶贫困披露+语料行数账;'
                'v6(ADR-0308,W37)回退层胜负面换 W31 实测阶梯'
                '(池内容不变仅语义变,指纹随版本重算);'
                'v7(ADR-0312,W50)采样键 _deployable_depth 改 Σboard'
                '全集口径(与池语料同口径,池内容不变);'
                'v7 内容扩容(ADR-0334,W73):2026-08-25 夜间实机 5 局'
                '新增 45 行重生成,boss 桶真值锚——池内容变(指纹'
                '重算),采样语义不变(版本仍 7);'
                'v8(ADR-0344,W109)生成核心迁入 src(cw_delta_pool_gen)'
                '+实机局终自动再生管线+池新鲜度检查——池内容与采样'
                '语义不变(指纹不变);生成器头注与 CLI 壳双入口;'
                'v9(ADR-0362,W157)Δ池 plane 维键化(SNAPSHOT 形状'
                '{节点:{位面:{桶:[Δ]}}})——差分归属后行位面,P1/P2'
                '桶分离;顺手清除既有 P1 池 P2 污染(44 条 plane=2 '
                '差分混入,含 16 条跨位面差分,W156 勘察 §5.1);'
                'P1 桶语料随污染清除小幅变化(指纹重算,锚重记;'
                'P2 桶 n<5 全贫困,条件化分桶不做,采样走位面内'
                '全池合并兜底/回退层掉血带);'
                '⚠️ 版本号勘误(W240):上条 v9 在 pool._SAMPLER_VERSION'
                ' 里=8(生成器 note 链自 W109 批起与采样器常量错位+1),'
                '自 v10 起两链对齐;'
                'v10(ADR-0404,W240)boss 桶键 Σboard→净星深(上场件'
                ' Σ(star−1),ADR-0399 star_depth 同源口径;修 W238 实证'
                '的升星方向冲突——3合1 使 Σboard −2/次落浅桶而浅桶期望'
                '伤害更大,sim 判升星升 boss 伤害与 [27] 机制相反);'
                'P1 boss 语料 49 行全落桶 0(旧 9/12/15 桶条件性=键口径'
                '伪影);encounter/reward/supply 桶键不动;池内容变'
                '(指纹重算),W238 常数表随批重标定(registry '
                'handoff_boss_e_damage 键域 {9,12,15}→{0});'
                'sampler 常量同步 8→10(_SAMPLER_VERSION,META '
                'sampler_version 对齐 note 链);'
                'v11(ADR-0407,W250)encounter 桶键 depth→rung'
                '(与 battle 同源 _engines_count;批⑬ F1「样本不足暂缓」'
                '的解禁——扩容后 r0/r1 主桶 n=23/27 达标且梯度单调显著,'
                'dep/sd 键下期望伤害真平 p=0.87);boss 净星深/reward/'
                'supply depth 键不动;池内容变(指纹重算);'
                'v12(F6 语料治理,编排者批)非终局 hp_after==0 行'
                '判定为结算瞬时伪读数(伪影拆出 -84/+71 型毒对;对局'
                '档案真值语料 P1 未删失最大单轮损 36)——配对前剔除,'
                '计数 hp0_transient_dropped;池内容变(指纹重算);'
                'v13(ADR-0582,Δ池生成器治理)合成行'
                "(source='synthetic_supply')与低可信行(hp_confidence"
                '<0.9,判据=telemetry.query._outcome_hp_trusted)不作'
                ' hp 差分端点——移行桥接重配对(v12 hp0 瞬态同法),'
                '剔除计数 synthetic_supply_dropped/hp_conf_dropped 入'
                ' META;治镜像律毒(supply 域均值≈上一轮战败取反,'
                '复核 155/170=91.2%):supply P1 128→1/P2 47→0(域'
                '消失),battle P1 均值 -7.70→-6.27,conf 门另剔终局 '
                'loss_page hp=0 死亡腿 101 行(连带配对 -75 对);'
                '配对语义收拢单件 pool.pair_outcome_rows_to_pool'
                '(auto/snapshot 同口径);battle rung 真值锚随批用'
                '过滤后语料重推(sim.checks.pool.BATTLE_RUNG_TRUTH,'
                'ADR-0582);池内容变(指纹重算);'
                'v14(池数据防线)run 隔离机制化:前缀规则 fake_/sim_'
                '(类别级)+显式名单(个例级)双轨统一判据 '
                '_run_quarantine_reason,假游戏/sim 批 run 不入池;'
                '塌缩守卫:源行数账 < 现快照行数账×0.5 拒绝再生覆写、'
                '保留现快照(2026-09-08 假游戏局 fake_20260908 触发'
                '微语料三次静默覆写提交快照的实证防线)',
    }
    return pool, meta


def build_pool_from_journal(src_dir: Path | None = None,
                            runs_filter: set[str] | None = None,
                            ) -> tuple[dict, dict]:
    """journal 新账语料 → (Δ池, 构成 meta)(波 5 语料源切 journal)。

    语料源 = ``<src_dir>/state/journal.jsonl``(统一 state 流水,行行自足;
    读面单一源 = journal_query,轮归组 = round_state_snapshots)。旧
    decisions/outcomes 双流已随删除波 1 停写(读死数据),本函数是切源后
    的生成器读源;配对语义共用 pool.pair_outcome_rows_to_pool 单件
    (禁第二镜像循环,ADR-0582 同律)。

    - 轮真值 = 每轮最后一次写入的快照:hp_after=values.hp、node_type=
      values.node.kind、Σboard/净星深/上场名单由 front_row/back_row Unit
      序列化形态直算(与 decisions join 的键口径同义,boss 桶键 = 净星深
      ADR-0404 同式);
    - journal 无合成行/置信位概念 → synthetic_supply_dropped/
      hp_conf_dropped 恒 0(四类剔除计数如实为零,非缺报);
    - **再生门不动**:快照停更冻结(``_DELTA_POOL_FROZEN``)照常生效,
      本函数只供切源后的语料审计与抽样对拍;重启再生须先经编排者裁决。
    """
    from sr_od.application.currency_war.telemetry.journal_query import (
        JOURNAL_REL,
        read_journal_stats,
        round_state_snapshots,
    )
    src = Path(src_dir) if src_dir is not None else REPLAY_DIR
    rows, read_stats = read_journal_stats(src)   # 读入口已拼 JOURNAL_REL
    snaps = round_state_snapshots(rows)
    boards: dict = {}
    star_depths: dict = {}
    deployed_names: dict = {}
    seqs: dict[str, list[dict]] = {}
    for (run, plane, rnd), snap in sorted(snaps.items()):
        if runs_filter and run not in runs_filter:
            continue
        if _run_quarantine_reason(run) is not None:
            continue
        values = snap.get('values') if isinstance(snap.get('values'), dict) \
            else {}
        node = values.get('node') if isinstance(values.get('node'), dict) \
            else {}
        hp = values.get('hp')
        if hp is None:
            continue   # 无结算真值轮不入差分序列(诚实缺位)
        board = values.get('board') or {}
        units = [u for k in ('front_row', 'back_row')
                 for u in (values.get(k) or []) if isinstance(u, dict)]
        key = (run, plane, rnd)
        boards[key] = sum(int(v) for v in board.values())
        star_depths[key] = sum(max(0, int(u.get('star') or 1) - 1)
                               for u in units)
        deployed_names[key] = frozenset(
            str(u.get('char_id') or '') for u in units if u.get('char_id'))
        seqs.setdefault(run, []).append({
            'run_id': run, 'plane': plane, 'round_num': rnd,
            'hp_after': int(hp), 'node_type': str(node.get('kind') or ''),
        })
    from sr_od.application.currency_war.sim.pool import (
        pair_outcome_rows_to_pool,
    )
    pool, stats = pair_outcome_rows_to_pool(
        seqs, boards=boards, star_depths=star_depths,
        deployed_names=deployed_names)
    battle_killed: dict = stats['battle_killed']
    meta = {
        'source': 'journal(state/journal.jsonl;波 5 语料源切 journal)',
        'source_dir': str(src),
        'runs': stats['runs'],
        'runs_filter': (sorted(runs_filter) if runs_filter else 'all'),
        'skipped_lines': {
            'journal_bad_json': read_stats.bad_json_lines,
            'journal_non_dict': read_stats.non_dict_lines,
            'journal_byte_repair': read_stats.byte_repair_lines,
        },
        'unlabeled_dropped': stats['unlabeled_dropped'],
        'hp0_transient_dropped': stats['hp0_transient_dropped'],
        'synthetic_supply_dropped': stats['synthetic_supply_dropped'],
        'hp_conf_dropped': stats['hp_conf_dropped'],
        'quarantined_hits': [],
        'depth_bucket_w': DEPTH_BUCKET_W,
        'battle_rung': {
            str(b): dict(
                {'n': len(v), 'mean': round(sum(v) / len(v), 2)},
                **_win_stats(v, battle_killed.get(b, [])))
            for b, v in sorted(
                ((pool.get('battle') or {}).get(1) or {}).items())},
        'source_rows': {'journal_rounds': len(snaps)},
        'bucket_poverty': _poverty_list(pool, battle_killed),
        'note': 'journal 源构建器;快照停更冻结期间仅作语料审计'
                '与抽样对拍,快照覆写仍走 regenerate_snapshot 冻结门。',
    }
    return pool, meta


def regenerate_snapshot(src_dir: Path | None = None,
                        runs_filter: set[str] | None = None,
                        export_json: str | Path | None = None,
                        *, quiet: bool = False) -> str:
    """重生成快照并写 DATA_PY(CLI 与局终自动再生共用的唯一入口)。

    **已冻结(退役第一步)**:战斗类节点结算已切粗参数两态模型
    (cw_coarse_battle),快照停更——本函数一律 raise,CLI 壳与
    局终自动再生(ADR-0344)随之停跑(局终钩子 best-effort 捕获,
    只留日志不阻塞对局)。保留代码文件,删除归退役清理批;重启
    再生须先撤销 ``_DELTA_POOL_FROZEN`` 并经编排者裁决。

    返回新池指纹。空池 raise(调用方 best-effort 捕获;局终钩子
    不让异常外传)。生成纪律:头部勿手编警告+写目标白名单守卫在
    :func:`build_pool` / :func:`_assert_guards` 内生效;run 级隔离
    在 :func:`build_pool` 行循环内生效(前缀规则 + 显式名单);
    塌缩守卫 :func:`_assert_no_source_collapse` 在覆写前生效——
    源语料较基线塌缩即 raise :class:`SourceCorpusCollapse`,
    盘面快照原样保留(池数据防线,理由见各守卫注释;基线 =
    git HEAD 提交版优先、盘面兜底,ADR-0612)。
    """
    if _DELTA_POOL_FROZEN:
        raise DeltaPoolFrozen(
            'Δ池已冻结(退役第一步):战斗类节点已切粗参数两态模型'
            '(cw_coarse_battle),快照停更;重启再生需先撤销'
            ' cw_delta_pool_gen._DELTA_POOL_FROZEN(编排者裁决)')
    src = Path(src_dir) if src_dir is not None else REPLAY_DIR
    _assert_guards(src)
    pool, meta = build_pool(src, runs_filter)
    # 塌缩守卫先于空池判定:微语料源给「塌缩」诊断(可行动:查语料
    # 去向),比笼统的「池为空」多申报两侧行数账差异。
    _assert_no_source_collapse(DATA_PY, meta['source_rows'])
    if not pool:
        raise RuntimeError(f'池为空: {src} 无可配对样本(decisions 板深 × outcomes 差分)')


    from sr_od.application.currency_war.sim.pool import (
        _SAMPLER_VERSION,
        pool_fingerprint,
    )
    meta['sampler_version'] = _SAMPLER_VERSION
    fp = pool_fingerprint(pool)
    meta['fingerprint'] = fp

    lines = [
        '"""Δ池快照(生成产物——勿手编)。',
        '',
        '本文件由 src/sr_od/application/currency_war/cw_delta_pool_gen.py 生成',
        '(CLI 壳 tools/cw/gen_delta_pool_snapshot.py;实机局终自动再生 ADR-0344)。',
        '重跑: uv run python tools/cw/gen_delta_pool_snapshot.py',
        '手改会被下次生成覆盖,且指纹校验(resolve_pool)会拒绝失配数据。',
        '消费方:pool.resolve_pool(\'snapshot\')(CI/跨机可复现基准);',
        '判断层勿直接 import 本模块。',
        '',
        'W109 形态注:META/SNAPSHOT 以 JSON 串存储+导入时 loads——',
        'json.dumps 字面量含 null/true/false 时不是合法 Python(池含',
        'killed 全 None 桶即触发,产物不可 import=管线自毒);JSON 串',
        'repr 安全且保持 sort_keys 的 diff 稳定性。',
        '"""',
        'from __future__ import annotations',
        '',
        'import json as _json',
        '',
        '_META_JSON: str = ' + repr(json.dumps(
            meta, ensure_ascii=False, indent=2, sort_keys=True)),
        '_SNAPSHOT_JSON: str = ' + repr(json.dumps(
            pool, ensure_ascii=False, sort_keys=True)),
        'META: dict = _json.loads(_META_JSON)',
        'SNAPSHOT: dict = _json.loads(_SNAPSHOT_JSON)',
        '',
    ]
    DATA_PY.write_text('\n'.join(lines), encoding='utf-8')
    n = sum(len(v) for planes in pool.values()
            for b in planes.values() for v in b.values())
    if not quiet:
        print(f'快照已写 {DATA_PY.name}: 节点×{len(pool)} 样本×{n} '
              f'指纹 {fp} 跳过行 {meta["skipped_lines"]}')
    if export_json:
        ej = Path(export_json)
        if ej.suffix != '.json':
            raise RuntimeError(f'--export-json 只接受 .json: {ej}')
        ej.write_text(json.dumps(
            {'meta': meta, 'snapshot': pool}, ensure_ascii=False, indent=1,
            sort_keys=True), encoding='utf-8')
        if not quiet:
            print(f'JSON 快照已导出: {ej}')
    return fp
