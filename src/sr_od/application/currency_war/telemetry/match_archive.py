"""按局存档(cw match archive):终局旁路装配单局档案。

来源:2026-09-07 单局复盘实证的摩擦(规格件见当次任务书,设计要点)——
复盘一局需要在查询侧手工做四件事:跨 run 拼段(server 重启切段)、滤
hp=100 备帧假值、grep 跨 run 帧流、多源现算拼视图。本模块把这套机制化:

- **档案 = 终局旁路产物**:只读 replay/*.jsonl(与判读 CLI 同源同层),
  写 ``replay/matches/``;对运行时零侵入(不改任何内存态/决策路径,
  触发点 try 包裹失败不阻塞局终收口)。
- **触发双路**:①局终钩子(cw_loop 在 ``on_match_end`` 调用点之后调
  ``assemble_pending``,正常局自动装配);②CLI 离线装配(崩溃局/补装配,
  ``--game`` 点名绕过水位线)。旧数据不回填:首次装配以水位线记账
  (``.watermark.json``),只装水位线之后结束的局。
- **game_id 跨段继承**:段首帧非 (p1,r1) 起 = 续局,继承上一段所在局;
  game_id = 首段 run_id 时间戳派生(``g_YYYYMMDD_HHMMSS``)——纯数据派生,
  跨重启稳定,不依赖生成时进程状态。
- **自包含切片**:档案内嵌该局全部关联 jsonl 行切片(decisions/outcomes/
  shop_snapshots/exogenous/invest_cards/spend_ledger),``--match`` 视图
  把切片物化到临时目录后走**同一套** query_* 视图函数——与 ``--run``
  聚合输出保证一致(单一源,不建第二套视图实现)。
  obs_conflicts.jsonl 例外:跨局 journal 无 run_id 键且体积大,不入切片。
- **写盘原子性**:档案与 index 均 tmp 写入 + ``os.replace`` 原子改名,
  并发/中断读者不会读到半截 JSON。

保留策略(先记账不实现):档案体积 ≈ 单局 decisions 切片(百 KB~MB 级),
按局线性增长;方案 = index.jsonl 永久保留(每局一行,KB 级),match_*.json
超保留窗口(如 90 天或目录总量上限)时删档留 index 行(摘要仍可查,
细节回源 replay 原始 jsonl 重装配)。落地时加配置项,本批不实现。
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from one_dragon.utils import log_utils
from sr_od.application.currency_war.kernel.cw_strategy_session import strategy_state_of
from sr_od.application.currency_war.telemetry.query import (
    HP_CONF_TRUSTED,
    _outcome_hp_trusted,
    read_jsonl,
)
from sr_od.application.currency_war.telemetry.schema import (
    append_jsonl,
    terminal_state_summary,
)

log = log_utils.log

#: 档案 schema 版本(字段变更时递增;消费端按版本分支)
#: v2(match archive 二期批):+rounds[].decision_detail(v3_intention/
#: candidate_scores/eval_breakdown/dp_posture 逐帧明细显形;全帧本就在
#: slices.decisions 切片里,v2 只是把判读高频字段提到逐轮表)+ rounds[].bench
#: /equips(备战席逐张/装备栏 owned)+ 顶层 strategy_version(策略版本戳,
#: 取自 runs 行;旧档案无此键 = 版本未知)。全部加法字段,旧档案向后兼容。
#: v3(战后终态列,w936_deploy_fill 移交①):+rounds[].terminal/
#: terminal_ts/terminal_source——「执行后」快照与决策帧列并列,根除
#: 「把决策帧当战后板面读」的时序误读。terminal = 该轮决策迹流内最晚 ts
#: 帧的板面计数(schema.terminal_state_summary 单一源),装配端派生、
#: 零新运行时写入,故对存量档案同样生效。
#: v4(w943 审计 P2-5 返修):+rounds[].terminal_closure(收口类型):
#: 'start_battle'=末帧动作含出战(该帧观察=全部备战动作执行后的定型帧,
#: terminal 可信为执行后账面)/'mid_prep'=末帧为普通备战动作(轮经强制
#: 出战/bail/停机等异常出口收口,terminal 滞后一个动作=执行前末观察,
#: 判读须降权)。旧档案缺此键 → load_archive 版本检查自动重装配补齐
#:(P2-4 返修:版本迁移读端不再静默缺列)。
#: v5(M2 遥测增强批 ③):+endgame.final_snapshot(局级终局快照列:
#: 终局阵容/金/等级取全局最晚决策迹帧的 state,装配端派生、零新运行时
#: 写入;旧档案经 load_archive 版本检查自动重装配补齐)。加法字段。
#: v6(活局续段数据治理批):+顶层 resume_reconciliation(恢复态对账列:
#: 每个续局段「恢复帧读数 vs 前段末帧账面」的 hp/gold/plane/round 对账,
#: 装配端纯读派生;单段局恒空列表,旧档案经 load_archive 版本检查自动
#: 重装配补齐)。加法字段。装配器选型依据:并段与对账本质是「读侧把
#: 已落库的 run 段拼成一局」,写入端已如实落库无需改;恢复帧读数与终值
#: 不符时两侧都是真读,装配器无权裁哪边是真值,只做显影交判读定谳。
#: v7(行为观测计数落盘批):+顶层 ``cw4_counters``(策略行为观测计数
#: 局终快照;写入端 = cw_loop 局终收口把 ``strategy_state_of(session).cw4_counters`` 经
#: ``record_cw4_counters_snapshot`` 落 ``cw4_counters.jsonl``,装配端按
#: 局时间窗纯读派生归局)。旧档案/无计数流经 load_archive 版本检查自动
#: 重装配补齐(无窗内行 → None=数据缺失;空 dict=局内真实零计数)。
#: 加法字段。
#: v8(C8 遥测缺陷批):loss_nodes 逐结算行化——一条目对一个掉血结算行
#: (战斗腿口径;ADR-0567)。同轮「补给回血+战斗掉血」不再被轮级净额
#: 抵减/整条漏记(实证 g_20260906_182456 p2r4:净额 −19 vs 战斗腿 −33);
#: 单结算可信轮条目形状不变(同键同序),新增加法键 outcome_source/ts
#: (回落条目取值契约见 _build_rounds docstring)。rounds 逐轮表零变化
#: (仍单槽净额)。旧档案经 load_archive 版本检查自动重装配(loss_nodes
#: 净额→战斗腿原地修复);旧不变量「loss_nodes 条目集 ≡
#: {rounds.hp_delta<0 的轮}」自 v8 解除,分歧形态见 _build_rounds。
#: v9(T-100 遥测数据病统一件,ADR-0577):hp 真值链的「事件模型」落地,
#: 四机制一次到位——①事件步进链:结算步进链扩为 hp 变化步进链,可信结算
#: 行 ∪ hp_pay 事件行按 ts 全局交织走行,事件只推进游标不出条目;②段界
#: 重锚:换段取该段恢复帧 hp 重锚两链游标,续段首槽 hp_delta 从「跨段净额」
#: 变「段内变化」(读端可见口径变化),重锚差落 resume_reconciliation 扩展
#: 字段(unexplained_delta/consumed_by_chain)不进 loss_nodes;③合成行
#: (synthetic_supply)一律退出步进链(先验「陈旧直到证伪」,v8 的 0 值
#: 防御升格;rounds 槽/query_hp 显示行为不变);④终局腿:result='loss' 且
#: 步进游标未到 0 → runs.final_hp=0 结构真值兜底出 hp_source='endgame_
#: final' 条目。顶层新增加法列 hp_events(事件行显影)/hp_pay_defects
#: (modeled 期望账 vs 结算真值偏差)。旧档案经版本检查自动重装配。
SCHEMA_VERSION: int = 9

#: 档案子目录(replay/matches/)
MATCHES_DIRNAME: str = 'matches'

#: 水位线文件名(旧数据不回填的记账锚)
_WATERMARK_NAME: str = '.watermark.json'

# 结算屏真值链可信门槛 = HP_CONF_TRUSTED(query.py,单一源;语义与边界见其注释)

#: 入切片的 jsonl 流(按 run_id 过滤;obs_conflicts 为跨局 journal 不入)
_SLICE_FILES: tuple[str, ...] = (
    'decisions.jsonl', 'outcomes.jsonl', 'shop_snapshots.jsonl',
    'exogenous.jsonl', 'invest_cards.jsonl', 'spend_ledger.jsonl',
    'op_journal.jsonl',
)

#: 行为观测计数流(cw4_counters 局终快照;跨局 journal 无 run_id——
#: 归局靠 ts 时间窗匹配,故不进按 run_id 过滤的 _SLICE_FILES)
COUNTERS_FILE: str = 'cw4_counters.jsonl'

#: 终局结果的完结值域;非此值(如 'stopped')= abandoned(ADR-0235 口径:
#: 中断局也装配,标 abandoned 供判读分型)
_TERMINAL_RESULTS: frozenset[str] = frozenset({'win', 'loss'})


def matches_dir(replay_dir: Path | str) -> Path:
    """档案目录:``<replay_dir>/matches``。"""
    return Path(replay_dir) / MATCHES_DIRNAME


def game_id_from_run(run_id: str) -> str:
    """run_id(``run_YYYYMMDD_HHMMSS``)→ game_id(``g_YYYYMMDD_HHMMSS``)。

    非标准 run_id 原样加 ``g_`` 前缀兜底(容错,不抛)。
    """
    ts = run_id[len('run_'):] if run_id.startswith('run_') else run_id
    return f'g_{ts}'


def _row_ts(r: dict[str, Any]) -> str:
    """行时间戳统一读取(排序键;缺失回空串保序)。"""
    return str(r.get('ts') or '')


def _first_frame_key(rows: list[dict[str, Any]], run_id: str) -> tuple[int, int] | None:
    """段首帧的 (plane, round_num)(decisions 优先,outcomes 兜底)。

    判「续局」的依据:一局正常从 (p1,r1) 起;server 重启续打的段首帧
    落在局中某轮 → 该段是上一局的延续。
    """
    best: tuple[int, int] | None = None
    best_ts = ''
    for src in (rows, ):   # 单遍:decisions/outcomes 已由调用方合并传入
        for r in src:
            if r.get('run_id') != run_id:
                continue
            try:
                k = (int(r.get('plane') or 1), int(r.get('round_num') or 0))
            except (TypeError, ValueError):
                continue
            ts = _row_ts(r)
            if best is None or k < best or (k == best and ts < best_ts):
                best, best_ts = k, ts
    return best


def assign_games(replay_dir: Path | str) -> list[dict[str, Any]]:
    """按局分组全量段(outcomes 出现序)→ 有序列表。

    返回元素:``{game_id, segments: [run_id...], start_ts, end_ts}``。
    分组规则:段首帧 = (p1,r1) → 新局(继承规则的主判据);否则续局并入
    上一局。孤立续局(上一局不在库,如首段丢失)自成一体,game_id 取
    本段首段——档案内 ``continuity_note`` 留痕(装配时补)。
    plane/round/hp 连续性只作复核素材,不作分组判据(首帧判据已覆盖
    实证形态;连续性兜底留给未来出现「续局段恰好从 (p1,r1) 误读起」时)。
    """
    outcomes = read_jsonl(Path(replay_dir) / 'outcomes.jsonl')
    decisions = read_jsonl(Path(replay_dir) / 'decisions.jsonl')
    runs = read_jsonl(Path(replay_dir) / 'runs.jsonl')
    # 段出现序:outcomes 首现序;无 outcome 的段(decisions 有帧)按 ts 补尾
    seg_order: list[str] = []
    for o in outcomes:
        rid = o.get('run_id')
        if rid and (not seg_order or seg_order[-1] != rid) and rid not in seg_order:
            seg_order.append(rid)
    known = set(seg_order)
    extra = sorted({d.get('run_id') for d in decisions
                    if d.get('run_id') and d.get('run_id') not in known},
                   key=lambda r: min((_row_ts(d) for d in decisions
                                      if d.get('run_id') == r), default=''))
    seg_order.extend(r for r in extra if r)
    games: list[dict[str, Any]] = []
    for rid in seg_order:
        fk = _first_frame_key(decisions, rid) or _first_frame_key(outcomes, rid)
        is_continuation = (fk is not None and fk != (1, 1)) and bool(games)
        if is_continuation:
            games[-1]['segments'].append(rid)
        else:
            games.append({'game_id': game_id_from_run(rid), 'segments': [rid]})
    for g in games:
        segs = set(g['segments'])
        all_ts = sorted(_row_ts(r) for src in (decisions, outcomes, runs)
                        for r in src if r.get('run_id') in segs and _row_ts(r))
        g['start_ts'] = all_ts[0] if all_ts else ''
        g['end_ts'] = all_ts[-1] if all_ts else ''
    return games


def _load_slice(replay_dir: Path, segments: set[str]) -> dict[str, list[dict[str, Any]]]:
    """按段集合过滤各 jsonl 流(只读;文件缺 = 空列表)。"""
    out: dict[str, list[dict[str, Any]]] = {}
    for name in _SLICE_FILES:
        rows = read_jsonl(replay_dir / name)
        out[name] = [r for r in rows if r.get('run_id') in segments]
    _annotate_orphan_op_rows(out.get('op_journal.jsonl'))
    return out


def _annotate_orphan_op_rows(rows: list[dict[str, Any]] | None) -> None:
    """op journal 孤儿 enter 行标注(方案 C4):行序内无同 op exit 配对的
    enter 行标注 ``outcome='orphan'`` = 进程中断证据,容缺非缺陷。exit 行
    与已配对 enter 不动。"""
    if not rows:
        return
    open_stack: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r.get('kind') != 'op':
            continue
        op = str(r.get('op') or '')
        if r.get('event') == 'enter':
            open_stack.setdefault(op, []).append(r)
        elif r.get('event') == 'exit':
            open_stack.get(op, []).clear()
    for pending in open_stack.values():
        for r in pending:
            r['outcome'] = 'orphan'


def _best_decision_frame(dec_rows: list[dict[str, Any]],
                         key: tuple[int, int]) -> dict[str, Any] | None:
    """同轮取 actions 最多、并列取 ts 最晚的决策帧(口径与
    ``query._load_decisions_rounds`` 一致,档案装配自持一份避免私有函数耦合)。"""
    best: dict[str, Any] | None = None
    for d in dec_rows:
        try:
            k = (int(d.get('plane') or 0), int(d.get('round_num') or 0))
        except (TypeError, ValueError):
            continue
        if k != key:
            continue
        if (best is None
                or len(d.get('actions') or []) > len(best.get('actions') or [])
                or (len(d.get('actions') or []) == len(best.get('actions') or [])
                    and _row_ts(d) >= _row_ts(best))):
            # 同 ts 取流内后行(追加写序即时钟;前提 = decisions.jsonl
            # 单调追加,同 _last_decision_frame 的显式声明)
            best = d
    return best


def _latest_ts_frame(dec_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """全集取 ts 最晚一帧(「ts 最晚行」扫描单一源,DD-006 批审计消双源)。

    ts 并列取流内后行(追加写序即时钟;前提 = decisions.jsonl **单调追加**,
    同 ``_last_decision_frame`` 的显式声明);零行 → None。防漂移说明:本环
    原在 ``_last_decision_frame``/``_final_snapshot`` 各抄一份,一处改阈值
    另一处忘改即静默分叉,故收拢于此;键过滤版(同轮)经调用方先滤后传。
    """
    best: dict[str, Any] | None = None
    for d in dec_rows:
        if best is None or _row_ts(d) >= _row_ts(best):
            best = d
    return best


def _last_decision_frame(dec_rows: list[dict[str, Any]],
                         key: tuple[int, int]) -> dict[str, Any] | None:
    """同轮取 ts 最晚的决策迹帧(含执行步进帧)——「战后终态」的取帧端。

    - 为什么不是 ``_best_decision_frame``:后者按「actions 最多、并列取
      晚」选**决策帧**(计划动作最全的时点,先于 CwOpDeploy/CwOpEquipAll
      执行);终态要的恰是**执行后**的最晚账面,故只按 ts 取最晚帧。
    - 取值时机边界:最晚帧落在本轮备战执行后、战斗前;战斗不改板面
      (部署/装备/买卖只发生在备战期),故该帧板面 = 该轮战后终态。
      帧值是 bot tracking 账面(与决策帧列同认知地位,非画面重读);
      同轮中途的 tracking 翻转噪声按「以最晚帧为准」收敛。
    - ts 并列取流内后见者(同秒多帧 = 执行步进密集,后见者更晚)。
      「流内序 = 文件序」依赖 decisions.jsonl **单调追加**这一未成文不变量
      (w943 审计 P3-7 在此显式声明):append-only jsonl 下二者等价;若未来
      出现段间回写/乱序合并,本函数需改为显式按 (ts, 文件序) 双键排序。
    """
    rows: list[dict[str, Any]] = []
    for d in dec_rows:
        try:
            k = (int(d.get('plane') or 0), int(d.get('round_num') or 0))
        except (TypeError, ValueError):
            continue
        if k == key:
            rows.append(d)
    return _latest_ts_frame(rows)


def _terminal_closure(last_frame: dict[str, Any] | None) -> str | None:
    """终态收口类型(w943 审计 P2-5):末帧动作计划是否含出战。

    - 步进帧的记录时点 = 动作**执行前**的最近观察(cw_screen_prep
      ``_decide_port`` → ``_record_step(acct['last_obs'], …)``)。末帧动作
      含 StartBattle ⇒ 该帧观察在全部备战动作执行之后(出战决策以定型
      观察为输入)→ terminal 可信为执行后账面('start_battle');
      末帧是普通备战动作 ⇒ 轮经强制出战/bail/停机等**异常出口**收口
      (出战没走 decide 记录)→ terminal 滞后一个动作('mid_prep')。
    - 判据 = 末帧 actions 的 ``__type__`` 字符串匹配(serialize_action
      产物);装配端纯读判定,零运行时改动。None = 无末帧(仅结算行轮)。
    """
    if last_frame is None:
        return None
    for a in last_frame.get('actions') or []:
        if isinstance(a, dict) and a.get('__type__') == 'StartBattle':
            return 'start_battle'
    return 'mid_prep'


def _hp_entry(dec_frame: dict[str, Any] | None,
              outcome: dict[str, Any] | None) -> dict[str, Any]:
    """逐轮 hp 真值链:结算屏(outcomes.hp_after)优先,备帧兜底,带可信位。

    - source='settlement':结算屏真值(trusted = hp_confidence ≥ 0.9);
    - source='frame':决策备帧 hp(trusted = hp_readable 且 state.hp_trusted
      非 False——readable=False 时 hp 是 read_hp miss 沿用值/兜底值,不可信
      必须显影。r1 备战帧例外:血量固定但不恒 100,读失败帧顶层 hp=None
      (recorder 诚实未知口径)自然落 source='none',不再以兜底 100 混入)。
    两源皆缺 → hp=None, trusted=False。
    """
    if outcome is not None and outcome.get('hp_after') is not None:
        conf = outcome.get('hp_confidence')
        return {'hp': outcome['hp_after'], 'source': 'settlement',
                'trusted': isinstance(conf, (int, float))
                and conf >= HP_CONF_TRUSTED}
    if dec_frame is not None and dec_frame.get('hp') is not None:
        st = dec_frame.get('state') or {}
        trusted = (dec_frame.get('hp_readable') is True
                   and st.get('hp_trusted') is not False)
        return {'hp': dec_frame['hp'], 'source': 'frame', 'trusted': trusted}
    return {'hp': None, 'source': 'none', 'trusted': False}


def _settlement_hp_usable(row: dict[str, Any]) -> bool:
    """结算行 hp 可否作步进链锚(v8 可信门;v9 合成行一律退出,ADR-0577)。

    - 可信门 = query._outcome_hp_trusted 单一源:OCR miss 兜底行
      (hp_confidence<0.9,hp_after 落 0)不入链不推游标——伪值入链会伪造
      「掉血 −prev」条目并把游标打穿到 0、毒化后续全部战斗腿(纪律同
      query_hp「伪值不推进链」)。
    - 合成行一律退出步进链(v9,升格自 v8 的仅 0 值防御):补给合成行 hp
      是 last_state 快照,**快照不是事件**——先验按「陈旧,直到证伪」。
      双实证:g_20260906_182456 p2r4 合成行 45 陈旧了一整轮战斗(−14,最后
      观察支持 18:53:49、18:57:42 已结算 31),v8 给合成行步进资格的唯一
      立案见证经帧序复核为鬼值;g_20260907_025608 p2r4 合成行 18 vs 结算
      真值 1。降权不回退:「新鲜回血合成行」若被未来取证证实,回血可见性
      走 hp_receipt 类**事件**写点(另立批),不走快照。降权只及步进链:
      rounds 槽/query_hp/anomalies 对合成行的既有显示行为不变。
    """
    if row.get('source') == 'synthetic_supply':
        return False
    return _outcome_hp_trusted(row)


def _action_counts(actions: list[dict[str, Any]]) -> dict[str, int]:
    """序列化动作清单 → 类型计数(键 = __type__)。"""
    counts: dict[str, int] = {}
    for a in actions or []:
        if isinstance(a, dict) and a.get('__type__'):
            counts[a['__type__']] = counts.get(a['__type__'], 0) + 1
    return counts


def _evidence_links(replay_dir: Path, key: tuple[int, int]) -> list[str]:
    """buy_expect 留证 webp 按轮索引(cw_screen_prep 只在对账不一致时落盘,
    文件名 tag=p{plane}-r{round},落 replay 根;可选证据,缺 = 空列表)。"""
    tag = f'p{key[0]}-r{key[1]}_'
    base = Path(replay_dir)
    if not base.exists():
        return []
    return sorted(p.name for p in base.glob(f'buy_expect_{tag}*'))


def _segment_resume_frame(dec: list[dict[str, Any]],
                          outs: list[dict[str, Any]],
                          rid: str) -> dict[str, Any] | None:
    """段恢复帧单一源:该段最早 ts 决策迹帧;零决策帧段(采集缺口)→ 最早
    结算行兜底(hp_after/hp_confidence 归一为帧 hp/hp_readable 口径)。

    两处消费必须同源(v9):_resume_reconciliation 的对账对象与段界重锚的
    锚值——否则「重锚用的恢复帧」与「对账列显影的恢复帧」分叉,判读对不上。
    """
    rows = [d for d in dec if d.get('run_id') == rid]
    resume = min(rows, key=_row_ts) if rows else None
    if resume is None:
        o_rows = sorted((o for o in outs if o.get('run_id') == rid),
                        key=_row_ts)
        if o_rows:
            o = o_rows[0]
            conf = o.get('hp_confidence')
            resume = {'run_id': rid, 'plane': o.get('plane'),
                      'round_num': o.get('round_num'), 'ts': o.get('ts'),
                      'hp': o.get('hp_after'),
                      'hp_readable': (isinstance(conf, (int, float))
                                      and conf >= HP_CONF_TRUSTED)}
    return resume


def _resume_hp_anchorable(resume: dict[str, Any] | None) -> int | None:
    """恢复帧 hp 可否作重锚值:帧在 ∧ hp 非 None ∧ hp_readable 非 False
    (与 _resume_reconciliation 的 readable 守卫同判——恢复帧该字段不可信
    即不判不锚)。可锚 → 返回 int hp;不可锚 → None(诚实退化:游标维持
    跨段携带,与 v8 行为一致)。"""
    if resume is None:
        return None
    hp = resume.get('hp')
    if hp is None or resume.get('hp_readable') is False:
        return None
    try:
        return int(hp)
    except (TypeError, ValueError):
        return None


def _hp_pay_events(exo_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """顶层 hp_events 派生列(v9,加法,装配端纯读):kind='hp_pay' 事件行
    显影——非结算血变(血购支付)的可见面。行字段从 choice 载荷平铺
    (plane/round 显式入 choice 是写点契约,顶层 plane 恒 None);旧档案
    恒空列表 = 装配端救不回没有写入的数据(采集面修复只及新局)。"""
    out: list[dict[str, Any]] = []
    for r in exo_rows:
        if (r.get('kind') or '') != 'hp_pay':
            continue
        ch = r.get('choice') or {}
        out.append({'run_id': r.get('run_id'), 'ts': r.get('ts'),
                    'plane': ch.get('plane'), 'round': ch.get('round_num'),
                    'currency': ch.get('currency'),
                    'hp_delta': ch.get('hp_delta'), 'mode': ch.get('mode'),
                    'clicks': ch.get('clicks'), 'basis': ch.get('basis')})
    out.sort(key=_row_ts)   # 稳定:同秒保文件追加序
    return out


def _build_rounds(replay_dir: Path, slice_rows: dict[str, list[dict[str, Any]]],
                  segments: list[str] | None = None,
                  endgame_result: str = '',
                  ) -> tuple[list[dict[str, Any]], list[dict[str, Any]],
                             dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """装配逐轮表 + 败场节点列表。

    逐轮表键 = (plane, round_num)(位面内序,与全部视图同坐标系);
    每轮聚合:node_type(结算屏真值优先)/ hp 真值链 / 金 / 等级 / 动作
    (计数+全量序列化)/ shop 快照全波(offer/refresh)/ 配对(sess_p1_pair)/
    姿态(dp_posture,decision_v2 决策帧口径)/ b_t(form_score 替代披露
    口径;form_score 已退役,历史数据只读透传)/ 证据链接 /
    战后终态(terminal,该轮最晚帧板面计数——与决策帧列并列的「执行后」快照)。
    败场节点(loss_nodes,v8 起)= hp 链上掉血的**结算行**(战斗腿口径;
    ADR-0567);v9(ADR-0577)步进链升格为 **hp 变化事件步进链**:

    - 两链分工:rounds 链 = 轮级血面变化(单槽取末结算行,净额,无可信
      门——「本轮账面变化」的本职);步进链 = hp 变化走行,可信结算行
      (可信门,判据见 _settlement_hp_usable;v9 起合成行一律退出)∪
      hp_pay 事件行(批1 写点产物)按 **ts 全局交织**各成一步:结算步出
      掉血条目,事件步只推进游标不出条目(保 ADR-0567「一条目=掉血结算
      行」口径纯度,新增加法来源 hp_source='endgame_final' 除外)。
    - 段界重锚(v9):跨段停机时游标不再携带前段值——走行遇换段(以及
      rounds 链到达续段首 key)取该段恢复帧 hp(_segment_resume_frame
      单一源,与 resume_reconciliation 同一帧)重锚;重锚差 |游标−resume|≠0
      → 边界差落 boundaries(进 resume_reconciliation 扩展字段
      unexplained_delta/consumed_by_chain,不进 loss_nodes)。恢复帧不可锚
      (缺帧/hp None/readable False)→ 不锚维持跨段携带(诚实退化)。
      续段首槽 hp_delta 语义从「跨段净额」变「段内变化」(读端可见口径
      变化,跨局对照跨段槽位数字会变,ADR-0577 申报)。
    - 真值对账(v9,hp_pay 建模账):事件只作期望账;下一**可信结算行**
      与「游标(已含事件推进)」偏差≠0 → hp_pay_defects 落一行(留证不
      阻塞),游标照取结算值自愈——建模错账最多污染到下一结算并当场显影。
    - 走行序(F5 三边界,ADR-0577):ts 单源 = 记录时点墙钟,排序键字符
      串比较;①同秒并列:事件物料前置拼接 + Python 稳定排序 → 同秒事件
      先于结算(备战先于战斗的物理先序),结算/回落保持 v8 遍历序(key
      升序、key 内 ts 稳定)= 单段局逐字节退化的技术前提;②缺 ts 行:
      排序键回空串会错位到全局最前 → 守卫为不进步进链(该行步进资格让位
      回落,hp_events 列仍显影);③时钟回拨/NTP 步进:走行序失真,诚实
      退化(错位条目)与恢复帧不可锚退化并列申报。
    - 终局腿(v9,C-主,加法零新运行时写入):链走完后 result='loss' 且
      步进游标≠0 → 追加 {hp:0, delta:−游标, hp_source:'endgame_final',
      outcome_source:'runs.final_hp'}(runs 行结构保证死亡真值);游标已
      到 0(含回落路径到达)守卫不重复,win/abandoned 局零终局腿,游标
      None(全程无可锚行)→ 无 delta 可算诚实跳过。
    - 单步回落(v8 语义保留):该轮无(入链的)可信结算行 → 用轮槽 hp_e
      成一步(hp_source 沿用轮槽口径,游标推进同 rounds 链 prev_hp,凡非
      None 即推进),保住「无结算行轮备帧掉血也入 loss_nodes」的既有行为。
    - 条目形状:{plane, round, node_type, hp, delta, hp_source} 同键同序 +
      加法键 outcome_source/ts:恒指认条目 hp 的**直接来源结算行**
      (outcome_source = 行 source 字段,''=屏面真值行;'synthetic_supply'
      =合成行;ts = 行 ts);回落条目 hp 来源非结算行(备帧)时两者为 None。
    - 旧不变量「loss_nodes 条目集 ≡ {rounds.hp_delta<0 的轮}」自 v8 解除,
      两链在「同轮可信行在前+不可信行在后」形态分叉:游标停可信行、轮槽
      取不可信末行,后续轮条目按游标计算(与 query_hp「伪值不推进链」同
      纪律,方向正确非回归);净额≥0 的轮因战斗腿<0 仍必有条目。判读侧
      勿按旧直觉假设 loss_nodes ⊆ rounds 掉血轮(ADR-0567 §边界申报)。
    返回:(rounds, loss_nodes, boundaries, hp_pay_defects)。boundaries =
    {run_id: {unexplained_delta, consumed_by_chain}}(v9 段界重锚差显影)。
    """
    dec = slice_rows['decisions.jsonl']
    outs = slice_rows['outcomes.jsonl']
    snaps = slice_rows['shop_snapshots.jsonl']
    keys: set[tuple[int, int]] = set()
    for r in dec + outs:
        try:
            keys.add((int(r.get('plane') or 1), int(r.get('round_num') or 0)))
        except (TypeError, ValueError):
            continue
    # 同轮多结算行全保留(v8,ADR-0567):按 ts 升序遍历内逐行 append——
    # append 必须留在本排序遍历内,轮槽 [-1] 才与旧「后写覆盖」取到同一行
    # (rounds 表逐字节不变的技术前提),步进链也天然得 ts 序
    outs_by_key: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for o in sorted(outs, key=_row_ts):
        try:
            outs_by_key.setdefault(
                (int(o.get('plane') or 1), int(o.get('round_num') or 0)),
                []).append(o)
        except (TypeError, ValueError):
            continue
    snap_by_key: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for s in snaps:
        try:
            snap_by_key.setdefault(
                (int(s.get('plane') or 1), int(s.get('round_num') or 0)), []).append(s)
        except (TypeError, ValueError):
            continue
    # 每轮决策迹帧计数(复盘「零决策行」缺口一眼可见,免翻原始 jsonl;
    # 已知形态:补给轮只有首补给 detour 一次性快照,后续补给轮 = 0,
    # 写入端接线归 operations 面——W941 返修 REPORT 判定节)
    dec_count: dict[tuple[int, int], int] = {}
    for d in dec:
        try:
            k = (int(d.get('plane') or 1), int(d.get('round_num') or 0))
        except (TypeError, ValueError):
            continue
        dec_count[k] = dec_count.get(k, 0) + 1
    # —— v9 段界重锚准备:续局段首 key(该段最早 ts 行的 (plane, round))——
    # rounds 链锚点判据:per-key 循环到达该 key 即换锚(此时前段全部行已
    # 处理完;本局 (2,1) 槽两段行共存时,槽 hp_e 取 ts 末行,前段行天然让位)。
    anchor_seg_by_key: dict[tuple[int, int], str] = {}
    if segments and len(segments) > 1:
        for rid in segments[1:]:
            seg_rows = [r for r in dec + outs if r.get('run_id') == rid]
            if not seg_rows:
                continue
            first = min(seg_rows, key=_row_ts)
            try:
                anchor_seg_by_key[(int(first.get('plane') or 1),
                                    int(first.get('round_num') or 0))] = rid
            except (TypeError, ValueError):
                continue
    resume_cache: dict[str, dict[str, Any] | None] = {}
    boundaries: dict[str, dict[str, Any]] = {}
    rounds: list[dict[str, Any]] = []
    prev_hp: int | None = None
    loss_nodes: list[dict[str, Any]] = []
    # v9 步进链物料:walk_items 按 v8 遍历序收集(key 升序、key 内 ts 稳定),
    # 循环后与事件物料合并做全局 ts 稳定排序走行(见循环后注释)
    walk_items: list[dict[str, Any]] = []
    node_type_by_key: dict[tuple[int, int], str | None] = {}
    for key in sorted(keys):
        frame = _best_decision_frame(dec, key)
        # 同轮全帧动作合并(流内序;口径同 query._load_decisions_rounds):
        # 代表帧只承载字段展示,动作计数不能只看代表帧——载体帧与决策帧
        # 同为单动作时「并列取末帧」让载体帧胜出,该轮买/升/刷全计 0
        # (实证 g_20260903_232823 p1r1/r2;计划口径边界同 query 侧 docstring)。
        round_actions: list[dict[str, Any]] = []
        for d in dec:
            try:
                if (int(d.get('plane') or 1), int(d.get('round_num') or 0)) == key:
                    round_actions.extend(d.get('actions') or [])
            except (TypeError, ValueError):
                continue
        outs_k = outs_by_key.get(key) or []
        # 轮槽 outcome = ts 最末结算行(同轮多行时后行胜出,与旧「后写
        # 覆盖」同一行;_hp_entry 仍收单行,签名语义不变)
        outcome = outs_k[-1] if outs_k else None
        st = (frame or {}).get('state') or {}
        hp_e = _hp_entry(frame, outcome)
        # —— v9 段界重锚(rounds 链):到达续局段首 key → 取该段恢复帧 hp
        # 重锚轮级游标(prev_hp 从「前段末值」换锚「本段恢复读数」)。重锚差
        # 显影归走行段界处统一落(见走行注释:步进链游标含事件推进,是
        # 「事件已解释边界差」的唯一知情者);恢复帧不可锚 → 不锚维持携带。
        _aid = anchor_seg_by_key.get(key)
        if _aid is not None:
            if _aid not in resume_cache:
                resume_cache[_aid] = _segment_resume_frame(dec, outs, _aid)
            _rhp = _resume_hp_anchorable(resume_cache[_aid])
            if _rhp is not None:
                prev_hp = _rhp
        delta = None
        if hp_e['hp'] is not None and prev_hp is not None:
            delta = int(hp_e['hp']) - int(prev_hp)
        if hp_e['hp'] is not None:
            prev_hp = int(hp_e['hp'])
        # 姿态:该轮 decision_v2 决策帧的 dp_posture 标签集(载体帧是
        # str(dict) 形态天然不命中,与 _release_frame_counts 同口径)
        dp_tags: list[str] = []
        for d in dec:
            try:
                if ((int(d.get('plane') or 0), int(d.get('round_num') or 0)) == key
                        and (d.get('strategy_id') or '') == 'decision_v2'
                        and isinstance(d.get('dp_posture'), str)
                        and d.get('dp_posture')):
                    dp_tags.append(d['dp_posture'])
            except (TypeError, ValueError):
                continue
        # b_t:同轮末帧时点值(无决策帧 → outcome 无此字段 → None)
        nt_out = (outcome or {}).get('node_type')
        nt_state = st.get('node_type')
        # 决策流程明细(二期①)显形:该轮最优决策帧的意向/打分/分解/姿态。
        # 全量决策帧本就在 slices.decisions.jsonl 切片(逐帧全字段),这里只
        # 提判读高频字段进逐轮表,免「查明细先翻切片」—— None = 该轮无决策帧。
        detail = None
        if frame is not None:
            detail = {'v3_intention': frame.get('v3_intention'),
                      'candidate_scores': frame.get('candidate_scores'),
                      'eval_breakdown': frame.get('eval_breakdown'),
                      'dp_posture': frame.get('dp_posture') or None,
                      'shop_rejects': frame.get('shop_rejects') or None}
        # 战后终态取帧:该轮最晚 ts 决策迹帧(执行后;口径见函数注)
        last_frame = _last_decision_frame(dec, key)
        _terminal = (terminal_state_summary(last_frame.get('state'))
                     if last_frame is not None else None)
        rounds.append({
            'plane': key[0], 'round': key[1],
            'node_type': nt_out or nt_state,
            'node_type_source': 'settlement' if nt_out else (
                'frame' if nt_state else 'none'),
            'hp': hp_e['hp'], 'hp_source': hp_e['source'],
            'hp_trusted': hp_e['trusted'], 'hp_delta': delta,
            'gold': (frame or {}).get('gold'),
            'gold_readable': (frame or {}).get('gold_readable'),
            'level': st.get('level'),
            'xp_progress': st.get('xp_progress'),
            'actions': round_actions,
            'action_counts': _action_counts(round_actions),
            'shop_snapshots': snap_by_key.get(key, []),
            'sess_p1_pair': (frame or {}).get('sess_p1_pair'),
            'dp_postures': sorted(set(dp_tags)),
            # b_t:同轮末帧时点值(form_score 替代披露口径;form_score
            # 已退役历史只读——新帧无该键恒 None,旧行仍透传)
            'b_t': (frame or {}).get('b_t'),
            'form_score': (frame or {}).get('form_score'),
            'form_ok': (frame or {}).get('form_ok'),
            'target_comp': (frame or {}).get('target_comp'),
            'board': st.get('board'),
            # 以下 deployed/bench/equips/board 三四列 = **决策帧**快照
            # (_best_decision_frame:决策时点,先于 CwOpDeploy/CwOpEquipAll
            # 执行)——判读「执行后板面」必须并读 terminal 列,勿把本列
            # 当战后实况(w936_deploy_fill 移交①:g_20260831_032006 r9
            # 决策帧 4/6 被误读为部署停驻,实机已填到 6/6)。
            'deployed': st.get('deployed'),
            # 备战席逐张 + 装备栏 owned(二期③⑤):帧 state 全量快照里本就
            # 有,提到逐轮表与 board/deployed 并读——阵容质量三维的 bench 维
            # 此前只能翻切片。None = 无决策帧/字段缺(旧数据)。
            'bench': st.get('bench'),
            'equips': st.get('equips'),
            'decision_detail': detail,
            # 决策迹帧数(v4):0 = 该轮采集缺口(已知形态=非首补给轮;
            # 判读结合 outcome.source='synthetic_supply' 分型)
            'n_decision_frames': dec_count.get(key, 0),
            # —— 战后终态(v3):该轮最晚帧板面计数(执行后、战斗前;
            # 战斗不改板面)= 「执行后」快照,与上方「决策时」列并列对照。
            # None/terminal_source='none' = 该轮无决策迹帧(仅结算行轮,
            # 旧数据容忍)。计数口径单一源 = schema.terminal_state_summary。
            'terminal': _terminal,
            'terminal_ts': _row_ts(last_frame) if last_frame else None,
            'terminal_source': ('last_decision_frame' if last_frame
                                else 'none'),
            # 收口类型(v4):start_battle=执行后定型帧可信 / mid_prep=
            # 异常出口,terminal 滞后一个动作须降权(语义见函数注)。
            'terminal_closure': _terminal_closure(last_frame),
            'outcome': outcome,
            'evidence': _evidence_links(replay_dir, key),
        })
        # —— v9 步进链物料收集(走行在循环后):结算/回落按 v8 遍历序
        # (key 升序、key 内 ts 稳定)收集;缺 ts 行不进步进链(F5② 守卫:
        # 空串排序键会错位到全局最前;该行步进资格让位回落,hp_events 列
        # 仍显影)——落条目的构造规则与 v8 逐字一致,仅执行位后移到走行处
        node_type_by_key[key] = nt_out or nt_state
        key_step_rows = [o for o in outs_k
                         if o.get('hp_after') is not None
                         and _row_ts(o)
                         and _settlement_hp_usable(o)]
        for o in key_step_rows:
            walk_items.append({'_kind': 'settle', 'row': o, 'key': key,
                               'node_type': o.get('node_type') or (nt_out or nt_state),
                               'run_id': o.get('run_id') or '',
                               'row_ts': _row_ts(o)})
        if not key_step_rows and hp_e['hp'] is not None:
            # 单步回落物料(v8 语义:该轮无入链可信结算行 → 轮槽 hp_e 成
            # 一步;游标推进同 rounds 链凡非 None 即推进)。走行序键取来源
            # 行 ts(帧来源取帧 ts);条目 ts 契约不变(帧来源 = None)。
            # 缺 ts 来源行 → 同 F5② 守卫不进链(ts 走行无位可置,v8 键位
            # 内联无此依赖;该轮条目丢失是缺 ts 数据的诚实代价)。
            # 回落来源守卫(ADR-0577「合成行一律退出步进链」的回落侧补执):
            # 来源行 = outcome 时同用 _settlement_hp_usable 判据(synthetic
            # 标记/conf 门一并辖),frame 来源用 _hp_entry 可信位(可读位)
            # ——不满足即同缺 ts 行走「不进链」通道,条目缺失 = 缺数据的
            # 诚实代价。纯补给轮(唯一 outcome=合成行,补给节点天然无结算
            # 屏)被 settle 路挡下的快照鬼值不再经本路复活回步进链;
            # hp=0/conf=1.0 兜底合成行伪造死亡条目的缝隙同封——loss 局
            # 死亡真值由终局腿(runs.final_hp 结构保证)兜底,不因本守卫丢失。
            from_outcome = hp_e['source'] == 'settlement'
            _fb_row = outcome if from_outcome else frame
            _fb_ts = (_row_ts(outcome) if from_outcome
                      else (_row_ts(frame) if frame is not None else ''))
            _fb_trusted = (_settlement_hp_usable(outcome) if from_outcome
                           else bool(hp_e['trusted']))
            if _fb_ts and _fb_trusted:
                walk_items.append({
                    '_kind': 'fallback', 'hp': int(hp_e['hp']),
                    'hp_source': hp_e['source'],
                    'outcome_source': (outcome.get('source') or ''
                                       if from_outcome else None),
                    'entry_ts': (outcome.get('ts') if from_outcome else None),
                    'key': key, 'node_type': nt_out or nt_state,
                    'run_id': (_fb_row or {}).get('run_id') or '',
                    'row_ts': _fb_ts})

    # —— v9 全局 ts 事件走行:结算/回落物料 ∪ hp_pay 事件物料 ——
    # 事件物料前置拼接 + 稳定排序 ⇒ 同秒并列时事件先于结算(备战先于战斗
    # 的物理先序,F5① tiebreaker);结算/回落保持 v8 遍历序 = 单段局(无
    # 事件/无重锚形态)逐字节退化的技术前提。
    event_items: list[dict[str, Any]] = []
    for r in slice_rows['exogenous.jsonl']:
        if (r.get('kind') or '') != 'hp_pay':
            continue
        ch = r.get('choice') or {}
        try:
            delta_ev = int(ch.get('hp_delta'))
        except (TypeError, ValueError):
            continue   # F5② 守卫:畸形事件不进链(hp_events 列仍显影)
        if not _row_ts(r):
            continue   # F5② 守卫:缺 ts 行错位防御
        event_items.append({'_kind': 'event', 'hp_delta': delta_ev,
                            'key': None, 'node_type': None,
                            'run_id': r.get('run_id') or '',
                            'row_ts': _row_ts(r)})
    step_prev: int | None = None
    # 步进链当前段(v9 段界重锚判据;None = 走行首行,不重锚)
    walk_seg: str | None = None
    pending_pay = 0        # 上一可信结算以来 modeled 支付累计(hp_delta 和)
    pending_pay_n = 0      # 未决事件笔数(0 = 无待对账)
    hp_pay_defects: list[dict[str, Any]] = []
    for it in sorted(event_items + walk_items, key=lambda x: x['row_ts']):
        rid = it.get('run_id') or ''
        if walk_seg is None:
            walk_seg = rid
        elif rid and rid != walk_seg:
            # 段界重锚(步进链):换段 → 该段恢复帧 hp 重锚游标。重锚差
            # ≠0 → 边界差显影(本处单一落点:步进链游标含 hp_pay 事件推进,
            # 是「事件已解释边界差 → 重锚 no-op」的唯一知情者,§2.3 形态②;
            # rounds 链锚点静默换锚)。跨段未决对账随重锚落账不追溯。
            walk_seg = rid
            if rid not in resume_cache:
                resume_cache[rid] = _segment_resume_frame(dec, outs, rid)
            _rhp = _resume_hp_anchorable(resume_cache[rid])
            if _rhp is not None:
                if step_prev is not None and _rhp != step_prev:
                    boundaries[rid] = {'unexplained_delta': _rhp - step_prev,
                                       'consumed_by_chain': True}
                step_prev = _rhp
                pending_pay, pending_pay_n = 0, 0
        if it['_kind'] == 'event':
            # 事件步:只推进游标不出条目(ADR-0567「一条目=掉血结算行」
            # 纯度);游标未锚(None)时事件无基準不可推进也不进对账。
            if step_prev is not None:
                step_prev += it['hp_delta']
                pending_pay += it['hp_delta']
                pending_pay_n += 1
            continue
        if it['_kind'] == 'settle':
            o = it['row']
            step_hp = int(o['hp_after'])
            # 真值对账(v9):modeled 期望账(游标已含事件推进)vs 结算
            # 真值,偏差≠0 落 defect 行(留证不阻塞);游标照取结算值自愈。
            if pending_pay_n and step_prev is not None:
                _gap = step_hp - step_prev
                if _gap != 0:
                    hp_pay_defects.append({
                        'plane': it['key'][0], 'round': it['key'][1],
                        'expected_hp': step_prev, 'actual_hp': step_hp,
                        'gap': _gap, 'modeled_paid': pending_pay,
                        'ts': o.get('ts')})
                pending_pay, pending_pay_n = 0, 0
            step_delta = step_hp - step_prev \
                if step_prev is not None else None
            step_prev = step_hp
            if step_delta is not None and step_delta < 0:
                loss_nodes.append({
                    'plane': it['key'][0], 'round': it['key'][1],
                    'node_type': it['node_type'],
                    'hp': step_hp, 'delta': step_delta,
                    'hp_source': 'settlement',
                    'outcome_source': o.get('source') or '',
                    'ts': o.get('ts')})
        else:
            # 单步回落步(v8 语义原样:凡非 None 即推进;掉血出条目)
            fb_hp = it['hp']
            fb_delta = fb_hp - step_prev if step_prev is not None else None
            if fb_delta is not None and fb_delta < 0:
                loss_nodes.append({
                    'plane': it['key'][0], 'round': it['key'][1],
                    'node_type': it['node_type'],
                    'hp': it['hp'], 'delta': fb_delta,
                    'hp_source': it['hp_source'],
                    'outcome_source': it['outcome_source'],
                    'ts': it['entry_ts']})
            step_prev = fb_hp
    # —— v9 终局腿(C-主,加法零新运行时写入):result='loss' 且步进游标
    # 未到 0 → runs.final_hp=0 结构保证真值兜底出死亡条目;游标已到 0(含
    # 回落路径到达)守卫不重复,win/abandoned 局零终局腿,游标 None(全程
    # 无可锚行)无 delta 可算诚实跳过(ADR-0577)。
    if (endgame_result == 'loss' and step_prev is not None
            and step_prev != 0 and keys):
        lk = max(keys)
        loss_nodes.append({
            'plane': lk[0], 'round': lk[1],
            'node_type': node_type_by_key.get(lk),
            'hp': 0, 'delta': -step_prev,
            'hp_source': 'endgame_final',
            'outcome_source': 'runs.final_hp', 'ts': None})
    return rounds, loss_nodes, boundaries, hp_pay_defects


def _resume_reconciliation(segments: list[str],
                           slice_rows: dict[str, list[dict[str, Any]]]
                           ) -> list[dict[str, Any]]:
    """恢复态对账列(v6,装配端纯读派生):每个续局段「恢复帧读数 vs
    前段末帧账面」逐字段对账。

    - 对账对象:续局段(首帧非 (p1,r1))的**恢复帧** = 该段最早 ts 的
      决策迹帧(无决策帧时最早结算行兜底,hp_after/hp_confidence 归一为
      帧 hp/hp_readable 口径,金/等级结算行不采 → aligned=None);
      **前段末帧** = 该段之前全部段的最晚 ts 决策迹帧(≈ 停机时刻账面,
      与 endgame.final_snapshot 同源口径)。比对 hp/gold/level(带
      readable 可信位)与 plane/round 接续点。
    - aligned 语义:两侧都有值 → 是否相等;任一侧缺值或不可信(readable
      明确 False)→ None = 不可判,不猜。readable 守卫只查 resume 侧:
      prev 侧「不可信」依赖 decision_assembly 对 readable=False 帧写
      hp=None 的远端约定(值缺失即 aligned=None),本处不再重复守卫。
      装配器**不裁真值**:两侧都是诚实读数,不符只显影交判读定谳
      (2026-09-05 夜第八局实证:恢复帧 hp14/金68 vs 档案终值 hp29/金36,
      判读侧需此列才免手工翻流对账)。
    - 单段局 / 无续局段 → 空列表(判读「无恢复事件」与「未装配」以
      schema_version ≥ 6 区分)。
    """
    dec = slice_rows['decisions.jsonl']
    outs = slice_rows['outcomes.jsonl']
    by_seg: dict[str, list[dict[str, Any]]] = {}
    for d in dec:
        rid = d.get('run_id')
        if rid in segments:
            by_seg.setdefault(rid, []).append(d)
    out: list[dict[str, Any]] = []
    for i, rid in enumerate(segments):
        if i == 0:
            continue
        # 恢复帧 = _segment_resume_frame 单一源(v9:与段界重锚同帧定义,
        # 防两处「恢复帧」分叉;零决策帧段的结算行兜底语义原样内聚其中)
        resume = _segment_resume_frame(dec, outs, rid)
        prev_rows = [r for seg in segments[:i] for r in by_seg.get(seg, [])]
        prev = _latest_ts_frame(prev_rows) if prev_rows else None
        if resume is None and prev is None:
            continue
        resume_st = (resume or {}).get('state') or {}
        prev_st = (prev or {}).get('state') or {}

        def _pair(key: str, resume_row: dict[str, Any] | None,
                  prev_row: dict[str, Any] | None,
                  readable_key: str | None = None) -> dict[str, Any]:
            rv = (resume_row or {}).get(key)
            pv = (prev_row or {}).get(key)
            aligned: bool | None
            if (readable_key is not None
                    and (resume_row or {}).get(readable_key) is False):
                aligned = None   # 恢复帧该字段不可信,不判
            elif rv is None or pv is None:
                aligned = None
            else:
                aligned = rv == pv
            return {'resume': rv, 'prev_final': pv, 'aligned': aligned}

        out.append({
            'run_id': rid,
            'resume_ts': _row_ts(resume) if resume else None,
            'prev_final_ts': _row_ts(prev) if prev else None,
            'resume_frame': {'plane': (resume or {}).get('plane'),
                             'round_num': (resume or {}).get('round_num')},
            'hp': _pair('hp', resume, prev, 'hp_readable'),
            'gold': _pair('gold', resume, prev, 'gold_readable'),
            'level': _pair('level', resume_st, prev_st),
        })
    return out


def _merge_boundary_records(
        recon: list[dict[str, Any]],
        boundaries: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """段界重锚差并入恢复态对账行(v9,ADR-0577):unexplained_delta =
    resume − 重锚前游标(负 = 停机间隙真掉血),consumed_by_chain=True =
    该差已被重锚消费、不进 loss_nodes。无重锚差的续段行零新增键。"""
    for row in recon:
        b = boundaries.get(row.get('run_id'))
        if b is not None:
            row['unexplained_delta'] = b['unexplained_delta']
            row['consumed_by_chain'] = True
    return recon


def _match_counters(rd: Path, start_ts: str, end_ts: str) -> dict[str, Any] | None:
    """局时间窗内的计数快照归并(纯读派生;v7 顶层 ``cw4_counters``)。

    - 写入端每局终落一行 ``{ts, counters}``(局终收口时点,``ts`` 与
      runs 行同秒级 ISO 格式且早于/等于局 end_ts——cw_loop 两收口路径
      均先落计数再写 runs summary)。归局判据 = ``start_ts <= ts <=
      end_ts`` 闭区间;窗内多行(理论不出现,防御性容忍)按 ts 升序
      dict-merge(后写覆盖同键)。
    - 返回语义:**None = 窗内无计数行**(本批改动前落的局/计数流缺失,
      数据缺失可区分);**空 dict = 局内真实零计数**(写入端无计数也
      落空快照)。续局段重开进程会丢前段 session 计数——快照只含当前
      进程生命周期内的计数,诚实缺省不补猜。
    """
    if not start_ts:
        return None
    rows = [r for r in read_jsonl(rd / COUNTERS_FILE)
            if start_ts <= _row_ts(r) <= end_ts]
    if not rows:
        return None
    merged: dict[str, Any] = {}
    for r in sorted(rows, key=_row_ts):
        c = r.get('counters')
        if isinstance(c, dict):
            merged.update(c)
    return merged


def record_cw4_counters_snapshot(replay_dir: Path | str,
                                 counters: dict[str, Any] | None) -> dict[str, Any]:
    """落一行行为观测计数局终快照(``cw4_counters.jsonl`` 写端唯一入口)。

    - 数据源 = 局内 session 的 ``cw4_counters``(策略侧计数载体,键登记
      见 strategies/impl/mandate_v1/design_telemetry 键节;sim 侧抽取
      先例 = ab_core_swap.cw4_disclosure_from_session,本写端落**全量**
      键——披露键族是它的子集,归档面不预筛,筛桨留给消费端)。
    - 调用时序契约:必须在局终 runs summary **之前**写(行 ts 参与归局
      时间窗,晚于 end_ts 会掉出窗外 = 计数丢失;cw_loop 两收口路径已按
      此序接线)。
    - ``counters=None/缺`` → 落空 dict 快照(与「无计数流」可区分;
      ``_match_counters`` 返回语义见其注释)。返回实际写入的快照 dict。
    """
    snapshot = dict(counters or {})
    append_jsonl(Path(replay_dir) / COUNTERS_FILE, {
        'ts': datetime.now().isoformat(timespec='seconds'),
        'counters': snapshot,
    })
    return snapshot


def record_cw4_counters_from_match(replay_dir: Path | str,
                                   match: Any) -> dict[str, Any]:
    """从对局载体(CurrencyWarMatch)提取计数快照并落盘(cw_loop 收口用)。

    ``match`` 无 session / session 无 cw4_counters(策略未初始化计数,
    如 default 栈)→ 落空快照;异常由调用方 best-effort 包裹。
    """
    session = getattr(match, 'session', None)
    return record_cw4_counters_snapshot(
        replay_dir, getattr(strategy_state_of(session), 'cw4_counters', None))


def build_archive(replay_dir: Path | str, game: dict[str, Any]) -> dict[str, Any]:
    """装配单局档案 dict(纯读 + 内存组装;不落盘)。

    ``game`` = ``assign_games`` 的元素(game_id/segments/start_ts/end_ts)。
    """
    rd = Path(replay_dir)
    segments: list[str] = list(game['segments'])
    seg_set = set(segments)
    slice_rows = _load_slice(rd, seg_set)
    runs_rows = [r for r in read_jsonl(rd / 'runs.jsonl')
                 if r.get('run_id') in seg_set]
    runs_by_seg = {r.get('run_id'): r for r in runs_rows}
    last_summary = runs_by_seg.get(segments[-1]) if segments else {}
    result = str((last_summary or {}).get('result') or '')
    # abandoned 判定:末段无 runs 摘要(收口路径没走)或 result 非完结值域
    abandoned = (not result) or (result not in _TERMINAL_RESULTS)
    rounds, loss_nodes, boundaries, hp_pay_defects = _build_rounds(
        rd, slice_rows, segments, result)
    seg_summaries = [
        {'run_id': rid,
         'first_frame': _first_frame_key(slice_rows['decisions.jsonl'], rid)
         or _first_frame_key(slice_rows['outcomes.jsonl'], rid),
         'summary': runs_by_seg.get(rid)}
        for rid in segments]
    # 孤立续局(本段是续局但上一局不在库)留痕:首段首帧非 (p1,r1)
    first_fk = seg_summaries[0]['first_frame'] if seg_summaries else None
    continuity_note = ('孤立续局段(上一段不在库,game_id 取本段)'
                       if first_fk is not None and first_fk != (1, 1) else '')
    # 策略版本戳(二期②):runs 行在写入时点已打戳(version_stamp),此处
    # 只透传——段序倒查取首个非空(末段优先=终局时点版本);各段各自版本
    # 在 segments[].summary 里可查。None = 旧数据无戳(消费端读「版本未知」)。
    strategy_version: dict[str, str] | None = None
    for s in reversed(seg_summaries):
        row = s.get('summary') or {}
        if row.get('code_commit') or row.get('registry_fingerprint'):
            strategy_version = {'code_commit': row.get('code_commit') or '',
                                'registry_fingerprint':
                                    row.get('registry_fingerprint') or ''}
            break
    return {
        'schema_version': SCHEMA_VERSION,
        'game_id': game['game_id'],
        # 行为观测计数局终快照(v7;None=无计数流,判读按「数据缺失」)
        'cw4_counters': _match_counters(rd, game.get('start_ts') or '',
                                        game.get('end_ts') or ''),
        'strategy_version': strategy_version,
        'segments': seg_summaries,
        'start_ts': game.get('start_ts') or '',
        'end_ts': game.get('end_ts') or '',
        'archived_at': datetime.now().isoformat(timespec='seconds'),
        'continuity_note': continuity_note,
        # 恢复态对账列(v6)+ 段界重锚差扩展字段(v9,ADR-0577):
        # boundaries 按 run_id 并入对应续段行(unexplained_delta/consumed_
        # by_chain),不进 loss_nodes——重锚差是「段界间隙变化」显影非战斗腿。
        'resume_reconciliation': _merge_boundary_records(
            _resume_reconciliation(segments, slice_rows), boundaries),
        'rounds': rounds,
        'loss_nodes': loss_nodes,
        # hp 变化事件显影列(v9 加法,装配端纯读;旧档案恒空 = 采集面修复
        # 只及新局)与 modeled 期望账对账偏差列(v9 加法,留证不阻塞)
        'hp_events': _hp_pay_events(slice_rows['exogenous.jsonl']),
        'hp_pay_defects': hp_pay_defects,
        'opening': _build_opening(slice_rows, runs_by_seg),
        'endgame': {'result': result or 'abandoned',
                    'abandoned': abandoned,
                    'plane_reached': (last_summary or {}).get('plane_reached'),
                    'rounds_survived': (last_summary or {}).get('rounds_survived'),
                    'final_hp': (last_summary or {}).get('final_hp'),
                    'difficulty': (last_summary or {}).get('difficulty'),
                    # 局级终局快照(M2 增强批 ③;None=零决策迹局):
                    # 终局阵容/金/等级,取值口径见 _final_snapshot。
                    'final_snapshot': _final_snapshot(
                        slice_rows['decisions.jsonl']),
                    'segment_summaries': seg_summaries},
        'slices': slice_rows,
    }


def _build_opening(slice_rows: dict[str, list[dict[str, Any]]],
                   runs_by_seg: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """开局面:词缀/难度/投资卡简报(invest_cards 全行带 chosen 位)。"""
    briefing = [r for r in slice_rows['exogenous.jsonl']
                if (r.get('kind') or '') == 'briefing']
    invest = slice_rows['invest_cards.jsonl']
    return {
        'difficulty': next((r.get('difficulty') for r in runs_by_seg.values()
                            if r.get('difficulty')), ''),
        'briefing_rows': briefing,
        'invest_cards': invest,
        'chosen_env': [r.get('name') for r in invest
                       if r.get('kind') == 'env' and r.get('chosen')],
        'chosen_strategies': [r.get('name') for r in invest
                              if r.get('kind') == 'strategy' and r.get('chosen')],
    }


def _final_snapshot(dec_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """局级终局快照(M2 增强批 ③:endgame.final_snapshot 单一源;纯读派生)。

    - 取值 = 本局全部决策迹行中 **ts 最晚**的一帧的 state(终局阵容/金/
      等级快照列)。与逐轮 terminal 同口径家族:决策帧列是「决策时」,
      terminal 是「该轮执行后」,本列是「全局限最晚帧」——非收尾战斗帧,
      与 endgame.final_hp(结算屏真值)并列可读,判读终局板面以此列为准、
      勿再上翻逐轮表。
    - 时序边界(与 terminal_state_summary 的 w943 P2-5 边界同判):最晚帧
      若是普通备战动作(mid_prep 收口),快照滞后一个动作;可信度随附
      closure(start_battle=执行后定型 / mid_prep=执行前末观察降权)。
    - 字段:deployed/bench/board 终局阵容三维 + gold(_readable)+
      level(_readable, False=启发式兜底帧「兜底 4」非真读)+
      terminal(板面计数)+ ts/closure/source。None = 本局零决策迹行
      (仅结算行局,旧数据容忍)。
    """
    best = _latest_ts_frame(dec_rows)
    if best is None:
        return None
    st = best.get('state') or {}
    return {
        'ts': _row_ts(best),
        'source': 'last_decision_frame',
        'closure': _terminal_closure(best),
        'deployed': st.get('deployed'),
        'bench': st.get('bench'),
        'board': st.get('board'),
        'gold': best.get('gold'),
        'gold_readable': best.get('gold_readable'),
        'level': st.get('level'),
        'level_readable': best.get('level_readable'),
        'terminal': terminal_state_summary(st),
    }


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """原子写 JSON:tmp 同目录写入 + ``os.replace`` 改名(防半截读)。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent),
                               prefix=path.name + '.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def archive_path(replay_dir: Path | str, game_id: str) -> Path:
    return matches_dir(replay_dir) / f'match_{game_id}.json'


def load_archive(replay_dir: Path | str, game_id: str,
                 *, auto_rebuild: bool = True) -> dict[str, Any] | None:
    """读单局档案;不存在 → None。

    版本迁移读端(w943 审计 P2-4 返修):档案 ``schema_version`` < 当前
    SCHEMA_VERSION 时默认**就地重装配一次**(``assemble_game``:从 replay
    源流重派生加法字段并原子写回)——存量 v2/v3 档案经 ``--match`` 读出
    不再静默缺 terminal 族键。重装配失败(源 jsonl 已清/游戏分组不存在)
    → 退回旧档案并 log 警告(消费端显式知道列可能缺,不猜)。
    ``auto_rebuild=False`` 关闭自动迁移(纯只读审计场景)。
    """
    rd = Path(replay_dir)
    p = archive_path(rd, game_id)
    if not p.exists():
        return None
    with p.open('r', encoding='utf-8') as f:
        archive = json.load(f)
    try:
        stale = int(archive.get('schema_version') or 0) < SCHEMA_VERSION
    except (TypeError, ValueError):
        stale = True
    if stale and auto_rebuild:
        rebuilt = assemble_game(rd, game_id)
        if rebuilt is not None:
            return rebuilt
        log.warning(
            '[cw][archive] 档案 %s schema_version=%s < %s 且源流缺失无法'
            '重装配——terminal 族键可能缺列,判读按旧 schema 口径',
            game_id, archive.get('schema_version'), SCHEMA_VERSION)
    return archive


def rebuild_index(replay_dir: Path | str) -> None:
    """从全部档案重建 index.jsonl(一行一局摘要;原子写)。

    摘要字段刻意最小(游戏面身份 + 终局 + 轮数),细节回档案。
    """
    md = matches_dir(replay_dir)
    entries: list[dict[str, Any]] = []
    for p in sorted(md.glob('match_*.json')):
        try:
            with p.open('r', encoding='utf-8') as f:
                a = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue   # 半截/损坏档案不进 index(原子写使概率极低)
        endgame = a.get('endgame') or {}
        entries.append({
            'game_id': a.get('game_id'),
            'segments': [s.get('run_id') for s in (a.get('segments') or [])],
            'start_ts': a.get('start_ts'), 'end_ts': a.get('end_ts'),
            'result': endgame.get('result'),
            'abandoned': endgame.get('abandoned'),
            'plane_reached': endgame.get('plane_reached'),
            'rounds_survived': endgame.get('rounds_survived'),
            'final_hp': endgame.get('final_hp'),
            'n_rounds': len(a.get('rounds') or []),
            'n_loss_nodes': len(a.get('loss_nodes') or []),
            # 策略版本戳(二期②):''=旧档案/未采 = 版本未知
            'code_commit': (a.get('strategy_version') or {}).get('code_commit') or '',
            'registry_fingerprint': (a.get('strategy_version') or {})
            .get('registry_fingerprint') or '',
        })
    entries.sort(key=lambda e: e.get('start_ts') or '')
    md.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(md), prefix='index.jsonl.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False,
                                   separators=(',', ':')) + '\n')
        os.replace(tmp, md / 'index.jsonl')
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def assemble_game(replay_dir: Path | str, game_id: str) -> dict[str, Any] | None:
    """装配指定局(补装配入口:不问水位线;游戏不存在 → None)。"""
    rd = Path(replay_dir)
    game = next((g for g in assign_games(rd) if g['game_id'] == game_id), None)
    if game is None:
        return None
    archive = build_archive(rd, game)
    _atomic_write_json(archive_path(rd, game_id), archive)
    rebuild_index(rd)
    return archive


def _read_watermark(replay_dir: Path) -> str:
    p = Path(replay_dir) / MATCHES_DIRNAME / _WATERMARK_NAME
    try:
        with p.open('r', encoding='utf-8') as f:
            return str(json.load(f).get('archived_through') or '')
    except (OSError, json.JSONDecodeError, AttributeError):
        return ''


def _write_watermark(replay_dir: Path, through_ts: str) -> None:
    p = Path(replay_dir) / MATCHES_DIRNAME / _WATERMARK_NAME
    _atomic_write_json(p, {'archived_through': through_ts})


def _latest_end_ts(games: list[dict[str, Any]]) -> str:
    """全量局的最晚 ``end_ts``(水位线推进的唯一锚)。

    不能取 ``games[-1]``:``assign_games`` 把「无 outcomes 出现序的孤立
    段」追加在列表尾部,列表末元素不是时间序最晚局——曾致水位线冻结在
    某个旧孤立段的 end_ts(2026-09-05 夜实证:冻结在 06:56:29,其后
    正常局只能靠 CLI 点名装配,水位线永远不动)。
    """
    return max((g.get('end_ts') or '' for g in games), default='')


def _archive_covers_segments(archive: dict[str, Any],
                             segments: list[str]) -> bool:
    """已落盘档案的段集合是否与当前分组一致(续段归并检测)。

    档案存在且 schema 最新 ≠ 内容最新:活局续段被 ``assign_games`` 并入
    既有局后,该局 end_ts 越过水位线,但 schema 不变——若只按版本跳过,
    续段永远进不了档案(2026-09-05 夜实证:g_20260905_080023 档案停在
    单段,084407/090407 两续段只活在 assign_games 的内存分组里)。
    """
    archived = [s.get('run_id') for s in archive.get('segments') or []]
    return archived == list(segments)


#: 落后水位线且未入档的局的告警窗(小时):水位线 = 历史最大 end_ts 单调
#: 锚,时钟回拨/DST 回拨段结束的局 end_ts < wm 会被 ``<=`` 判定永久跳过
#: (漏装);该形态的局必然落在 wm 附近,而「旧数据不回填」的存量局落后
#: wm 几天/几周属设计态——用时间窗区分两者,防告警被存量局永久刷屏。
_BEHIND_WARN_WINDOW_HOURS: float = 48.0


def _ts_hours_between(later: str, earlier: str) -> float | None:
    """两个 ISO 秒级本地时间戳的小时差(later−earlier);解析失败 → None。"""
    try:
        return (datetime.fromisoformat(later)
                - datetime.fromisoformat(earlier)).total_seconds() / 3600.0
    except (TypeError, ValueError):
        return None


def assemble_pending(replay_dir: Path | str) -> list[str]:
    """装配「水位线之后结束、尚未入档」的局(局终钩子/CLI 缺省入口)。

    旧数据不回填:首次调用只落水位线(= 全量局最晚 end_ts,见
    ``_latest_end_ts``),不装任何存量局;此后每次只装 end_ts > 水位线的
    局并推进水位线。崩溃局没走钩子也被下次任一触发点补装(end_ts 仍
    > 水位线);更早的漏网局用 ``assemble_game`` 点名补装配。
    段集合有增长的局(活局续段并入)随版本检查一并重装,不丢不重:
    重装 = 从源流全量重派生后原子覆盖,续段并入即唯一变化。返回本次
    装配的 game_id 列表。
    观测面:水位线是历史最大值锚——end_ts < wm 的局被静默跳过且永不
    自动装配(时钟回拨/DST 回拨段的真实形态)。此类局若未入档且落后
    wm 在告警窗内(``_BEHIND_WARN_WINDOW_HOURS``),落 WARNING 带溯源
    (game_id/end_ts/wm),防「回拨期间新局连续漏装」无感。
    """
    rd = Path(replay_dir)
    games = assign_games(rd)
    if not games:
        return []
    wm = _read_watermark(rd)
    done: list[str] = []
    if not wm:
        # 首次启用:只记账不回填(边界:旧段 shop 刷新波已丢,回填也残缺)
        _write_watermark(rd, _latest_end_ts(games))
        return done
    for g in games:
        if (g['end_ts'] or '') <= wm:
            behind_hours = _ts_hours_between(wm, g['end_ts'] or '')
            if (g['end_ts'] or '') < wm and not archive_path(
                    rd, g['game_id']).exists() and (
                    behind_hours is None
                    or behind_hours <= _BEHIND_WARN_WINDOW_HOURS):
                log.warning(
                    '[cw][archive] 局 %s end_ts=%s 落后水位线 %s 且未入档'
                    '(时钟回拨/DST/漏装形态)——水位线为历史最大值锚,该局'
                    '不会被自动装配,需 CLI assemble --game 点名补装',
                    g['game_id'], g['end_ts'], wm)
            continue
        p = archive_path(rd, g['game_id'])
        if p.exists():
            # schema 过期也重装:装配端修复(如全帧动作合并)落地前生成的
            # 存量档案若只靠读端 load_archive auto_rebuild 迁移,直读 JSON
            # 的离线消费端(判读脚本)永远吃到欠列档案——在此随水位线推进
            # 自愈一次,与「新局装配」同一原子写路径。
            try:
                with p.open('r', encoding='utf-8') as f:
                    old = json.load(f)
                stale = (int(old.get('schema_version') or 0) < SCHEMA_VERSION)
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                # 损坏/缺失版本号的档案 → old=None → 段集视为未知
                # (_archive_covers_segments 对空档案恒 False)→ 落入重装,
                # 由 build_archive 从源流全量重派生后原子覆盖 = 自愈;
                # 仅当源流也不可读时 build_archive 才抛,向上传播不吞。
                stale = False
                old = None
            if not stale and _archive_covers_segments(old or {},
                                                      g['segments']):
                continue   # 已入档、版本最新、段集无增长——不重复写
        _atomic_write_json(p, build_archive(rd, g))
        done.append(g['game_id'])
    if done:
        rebuild_index(rd)
        _write_watermark(rd, _latest_end_ts(games))
    return done


def materialize_slice(archive: dict[str, Any], tmp_root: Path) -> Path:
    """档案切片 → 临时 replay 目录(供 ``--match`` 复用 query_* 视图)。

    写切片文件后原目录可直接传给 query 视图函数——与 ``--run`` 走同一套
    实现,输出保证一致(单一源)。
    """
    tmp_root.mkdir(parents=True, exist_ok=True)
    for name, rows in (archive.get('slices') or {}).items():
        with (tmp_root / name).open('w', encoding='utf-8') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False,
                                   separators=(',', ':')) + '\n')
    return tmp_root
