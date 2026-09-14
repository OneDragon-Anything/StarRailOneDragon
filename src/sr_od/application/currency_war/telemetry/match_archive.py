"""按局存档(cw match archive):终局旁路装配单局档案。

来源:2026-09-07 单局复盘实证的摩擦(规格件见当次任务书,设计要点)——
复盘一局需要在查询侧手工做四件事:跨 run 拼段(server 重启切段)、滤
hp=100 备帧假值、grep 跨 run 帧流、多源现算拼视图。本模块把这套机制化:

- **档案 = 终局旁路产物**:只读 live 流根的 *.jsonl(与判读 CLI 同源同层),
  写 ``telemetry/matches/``(布局单一源 = kernel/cw_observe 根常量块);对
  运行时零侵入(不改任何内存态/决策路径,
  触发点 try 包裹失败不阻塞局终收口)。
- **触发双路**:①局终钩子(cw_loop 局终收口分支调
  ``assemble_pending``,正常局自动装配);②CLI 离线装配(崩溃局/补装配,
  ``--game`` 点名绕过水位线)。旧数据不回填:首次装配以水位线记账
  (``.watermark.json``),只装水位线之后结束的局。
- **game_id 跨段继承**:段首帧非 (p1,r1) 起 = 续局,继承上一段所在局;
  game_id = 首段 run_id 时间戳派生(``g_YYYYMMDD_HHMMSS``)——纯数据派生,
  跨重启稳定,不依赖生成时进程状态。
- **自包含切片**:档案内嵌该局全部关联 jsonl 行切片(W3 起为 op_journal +
  统一 state 新账两项;旧 12 流切片键已随删除波 1 写入端退役拆除——存量
  档案 v12 及以前内嵌的旧流切片照常可读,裸数据归档只读),``--match``
  视图把切片物化到临时目录后走 journal_query 视图族读新账。
  obs_conflicts.jsonl 例外:跨局 journal 无 run_id 键且体积大,不入切片。
- **派生输入回源流(重装配保真)**:派生列(rounds/loss_nodes/departures/
  opening/resume_reconciliation 等)的输入吃旧流键,不在 v12 切片契约内
  ——装配时切片缺键回源流文件按段过滤补读(``_load_derived_inputs``;
  源流在 = 无损重装配,消除 v7 注申报的「重装配无益有损」;源流已清 =
  空列表诚实退化)。档案 ``slices`` 载荷不变(仍两文件契约)。
- **归局骨架(W3 起三源)**:journal 实机形态段(``run_YYYYMMDD_HHMMSS``,
  过滤 sim/测试段——journal 单文件多写者,哨兵同口径)+ 旧流段(存量语料
  重装配仍可归局);两源段按段首 ts 合并进同一时序插位。装配收尾走跨档
  归属收敛守卫(``_converge_cross_archive_ownership``):档案段集中「当前
  分组归他局」的段全部摘除(源流在 = 整体重装配自愈;源流失 = 定向剪枝 +
  ``pruned_segments`` 显影),保证同一 journal 段只归属一个档案——旧口径
  时代写入的存量档案错误持有续段时(跨档双计,T-242 实证),靠水位线/
  读端重装配都够不到,守卫是唯一收敛路径。
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
import re
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from one_dragon.utils import log_utils
from sr_od.application.currency_war.kernel.cw_exec_state import (
    DEPLOYED_CAPACITY,
    DEPLOYED_FRONT_CAPACITY,
    deployed_slot_no,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    MATCH_FINAL_FIELD,
)
from sr_od.application.currency_war.kernel.cw_observe import (
    LIVE_DIR,
    MATCHES_ROOT,
)
from sr_od.application.currency_war.telemetry.journal_query import (
    JOURNAL_REL,
    ROW_WRITE,
    node_key_of,
    read_journal_stats,
    row_kind,
)
from sr_od.application.currency_war.telemetry.query import (
    HP_CONF_TRUSTED,
    _outcome_hp_trusted,
    read_jsonl,
)
from sr_od.application.currency_war.telemetry.schema import (
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
#: v7 注(W4 流删退役,r5-migration-plan.md §2 W4):该顶层字段
#: 已随流载体 ``cw4_counters.jsonl`` 写端/装配面整体拆除——新装配档案无
#: 此键;局终级全键聚合收编载体 = 局终域行载荷 ``MatchFinal.cw4_counters``
#: (档案显影位 ``endgame.match_final.final.cw4_counters``)。**不 bump
#: SCHEMA_VERSION 申报**:bump 会触发存量档案 load 时重装配,把已落盘的
#: 旧字段整批抹掉(读侧宽容缺键,重装配无益有损);存量档案字段只读保留,
#: 重装配旧档案该字段消失(裸 ``cw4_counters.jsonl`` 归档数据在盘可考古)。
#: 先例 = endgame.match_final 键的不 bump 申报(本文件其注)。
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
#: v10(T-109①场上件离场逐件落账批,ADR-0605):+顶层 ``departures``(离场
#: 事件派生列,装配端纯读派生、零新运行时写入)。缺口实锤(g_20260907_075840
#: p1r1,Saber):执行期 deploy 换血卖出(CwScreenDeploy._sell_offtarget_deployed)
#: 的逐件身份只在 log 行与匿名计数键(sell_offtarget_*),无遥测行——场上件
#: 「无卖出动作而消失」挡 pivot 判读。决策时点卖出(SellBench/SellDeployed)
#: 本就逐件在案(actions+期望态快照),不在本列重复;本列吃的是帧间差分:
#: 相邻决策帧 state.deployed 身份多重集相减,通道分键 sell_recorded(帧动作
#: SellDeployed 槽位解析命中)/ merge_promoted(同名更高星在场=买牌合成链)/
#: unexplained(= 换血卖出信号通道;感知纠噪也可能落入,判读并读 obs_conflicts)。
#: 旧档案经 load_archive 版本检查自动重装配补齐。加法字段。
#: v11(零结算段自标识批,ADR-0615):+段条目 ``settlement_gap``(装配端纯读
#: 派生;见 ``_settlement_gap``),并修 assign_games 决策独有段时序插位(见其
#: docstring)。锚点病灶:段摘要 rounds_survived 取自收口时点 state.round_num
#: (备战停滞段可带非零冻结值),「rounds_survived=N 且本段零 outcome 行」
#: 曾被判读成「结算遥测断流」(实证:g_20260908_165445 续段 run_20260908_
#: 210431,79 决策帧全冻结 p2-r6、零 StartBattle 发射、rounds_survived=6;
#: g_20260909_012536,4 次出战尝试未成战后无进展守卫停机,rounds_survived=1
#: ——两段本就零结算,非遥测丢失)。本字段在场 = 本段零结算,判读直接可见。
#: 旧档案经 load_archive 版本检查自动重装配补齐。加法字段。
#: v12(统一 state 消费方迁移批 R3-1,设计 §3.6.2 档案行「装配器 v12+:切片
#: = 两文件」):+切片 ``state/journal.jsonl``(统一 state 新账,行行自足
#: 快照行;写端 = kernel/cw_state_journal,无条件常开(R5 W1/ADR-0634)——
#: 新账在产物目录才入切片,缺席 = 空切片,判读可区分「无对局产物」与
#: 「无行」)。加法切片,旧档案经 load_archive 版本检查自动重装配补齐;
#: 设计清单的第二文件(策略侧决策行)候其落地批再加切片,防空引用。
SCHEMA_VERSION: int = 12

#: 档案目录名(telemetry/matches;生产布局见 matches_dir)
MATCHES_DIRNAME: str = 'matches'

#: 水位线文件名(旧数据不回填的记账锚)
_WATERMARK_NAME: str = '.watermark.json'

# 结算屏真值链可信门槛 = HP_CONF_TRUSTED(query.py,单一源;语义与边界见其注释)

#: 入切片的 jsonl 流(按 run_id 过滤)。W3(R5 直迁第三波):旧 12 流切片
#: 键随删除波 1 写入端退役拆除——保留 op_journal(工程诊断保留流)与统一
#: state 新账两项;旧流文件缺 = 空切片(存量档案内嵌切片不受影响,裸数据
#: 归档只读可考古)。
_SLICE_FILES: tuple[str, ...] = (
    'op_journal.jsonl', 'state/journal.jsonl',
)

#: 派生列输入消费的旧流文件(rounds/loss_nodes/departures/opening/
#: resume_reconciliation/final_snapshot/hp_events 的真函数消费面编译自
#: 各派生函数的 slice_rows 键)。v12 切片契约外——装配时切片缺键回
#: 源流按段补读(语义见 ``_load_derived_inputs``);journal 新账键恒在
#: 切片内,不入本集。
_DERIVED_INPUT_FILES: tuple[str, ...] = (
    'decisions.jsonl', 'outcomes.jsonl', 'shop_snapshots.jsonl',
    'exogenous.jsonl', 'invest_cards.jsonl',
)

#: journal 段归局的 run_id 实机形态(段过滤单一判据;与哨兵脚本组
#: cw_sentinel/cw_runs_gap/cw_early_stop 的 RUN_ID_RE 同口径——journal
#: 单文件多写者,sim/测试段 fake_/sim_ 前缀与 harness 短 id 段不采信,
#: T-257 实证 live journal 混有 sim fake 段)。
_JOURNAL_RUN_ID_RE = re.compile(r'^run_[0-9]{8}_[0-9]{6}$')

#: 终局结果的完结值域;非此值(如 'stopped')= abandoned(ADR-0235 口径:
#: 中断局也装配,标 abandoned 供判读分型)
_TERMINAL_RESULTS: frozenset[str] = frozenset({'win', 'loss'})


def matches_dir(replay_dir: Path | str) -> Path:
    """档案目录:生产 live 流根 → 兄弟目录 ``telemetry/matches``(单一源 =
    kernel/cw_observe 的根常量块,2026-09-07 用户裁定布局);其余目录
    (测试合成流目录/sim 批目录等)保持旧子目录语义 ``<replay_dir>/matches``
    ——测试夹具以 tmp 流目录自洽构造,生产布局只有 live 一个入口。"""
    rd = Path(replay_dir)
    if rd == LIVE_DIR:
        return MATCHES_ROOT
    return rd / MATCHES_DIRNAME


def game_id_from_run(run_id: str) -> str:
    """run_id(``run_YYYYMMDD_HHMMSS``)→ game_id(``g_YYYYMMDD_HHMMSS``)。

    非标准 run_id 原样加 ``g_`` 前缀兜底(容错,不抛)。
    """
    ts = run_id[len('run_'):] if run_id.startswith('run_') else run_id
    return f'g_{ts}'


def _row_ts(r: dict[str, Any]) -> str:
    """行时间戳统一读取(排序键;缺失回空串保序)。"""
    return str(r.get('ts') or '')


def _settlement_gap(dec_rows: list[dict[str, Any]],
                    outcome_rows: list[dict[str, Any]],
                    run_id: str,
                    summary: dict[str, Any] | None) -> dict[str, Any]:
    """零结算段自标识(v11 加法,装配端纯读;非零结算段返回空 dict = 键缺省)。

    - 触发条件 = 本段决策帧 ≥1 且结算行(outcomes)= 0:本段全程没有
      任何一场战斗走到结算屏(备战停滞 / 出战失败后被守卫或人工停机)。
    - 为什么要在装配端显影:段摘要的 rounds_survived 写自收口时点的
      state.round_num(备战环里的 state 可能多环冻结),零结算段可以带
      非零 claimed 值——「claimed=N 而 outcome 行 0」形态曾被判读成
      「结算遥测断流」(实证局见 SCHEMA_VERSION v11 注)。本字段在场
      即「零结算是事实而非丢数据」,claimed 值随行给出仅供对照。
    - 边界:仅决策帧为 0 的空段(如被代码闸拦下、一行未写)不标注
      (无判读价值);有任一 outcome 行(含 synthetic_supply/recovered/
      loss_page 来源)即视为「有结算记录」,不标注。收口终局行
      (T-185,source='terminal_closure')**不入**该判定——它不是战斗
      结算行,恰是「本段零场战斗走到结算屏」的证据行(ADR-0615 的
      零结算语义):计它入「有结算记录」会让零结算停机段的终局行
      静默关闭本自标识(T-185 落地审建议-2),判读者按协议读到的是
      「有 outcome 行的普通段」,零结算事实从此不可见。
    """
    has_decisions = any(r.get('run_id') == run_id for r in dec_rows)
    if not has_decisions:
        return {}
    if any(r.get('run_id') == run_id
           and r.get('source') != 'terminal_closure'
           for r in outcome_rows):
        return {}
    n_dec = sum(1 for r in dec_rows if r.get('run_id') == run_id)
    return {'settlement_gap': {'decision_frames': n_dec,
                               'claimed_rounds_survived':
                                   (summary or {}).get('rounds_survived')}}


# ===== 局终行识别(R5 W2;局终域 match_final,retirement.md §2 runs 行)=====

# 局终行的 field 值单一源 = kernel MATCH_FINAL_FIELD(随写口声明;
# 模块顶部统一 import,本节不再复制字面量)。


def extract_match_final_rows(
        journal_rows: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    """从统一 state 账本行识别局终行(段级;局边界判定的识别半)。

    识别判据(封闭):``row=='write'`` ∧ ``field=='match_final'`` ∧ run_id
    非空。返回 ``{run_id: 行}``——局终域 = 一段一行(写口段内幂等,写前
    查重),同 run_id 多行(跨写口版本演进的理论形态)取 v 最大行,不抛;
    无局终行(段未收口/旧产物无账本)= 空 dict,判读可区分「未收口」与「无产物」。
    """
    out: dict[str, dict[str, Any]] = {}
    for r in journal_rows or []:
        if row_kind(r) != ROW_WRITE:
            continue
        if str(r.get('field') or '') != MATCH_FINAL_FIELD:
            continue
        rid = str(r.get('run_id') or '')
        if not rid:
            continue
        cur = out.get(rid)
        if cur is None or (r.get('v') or 0) >= (cur.get('v') or 0):
            out[rid] = r
    return out


def match_final_view(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """局终行 → 档案视图(载荷 + 归属;None 透传)。after 载荷 = MatchFinal
    序列化形态(final_type/at_version/终局快照/duration_s/backfilled);行
    级来源注记随行内嵌 state 快照自带(切片在档可回查),视图不复制。"""
    if row is None:
        return None
    after = row.get('after')
    return {
        'run_id': row.get('run_id'),
        'v': row.get('v'),
        'ts': row.get('ts') or '',
        'note': str(row.get('note') or ''),
        'final': after if isinstance(after, dict) else {},
    }


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
    """按局分组全量段(journal 实机段 + 旧流段三源骨架,段首 ts 插回时序位)
    → 有序列表。

    返回元素:``{game_id, segments: [run_id...], start_ts, end_ts}``。
    分组规则:段首帧 = (p1,r1) → 新局(继承规则的主判据);否则续局并入
    上一局。孤立续局(上一局不在库,如首段丢失)自成一体,game_id 取
    本段首段——档案内 ``continuity_note`` 留痕(装配时补)。
    plane/round/hp 连续性只作复核素材,不作分组判据(首帧判据已覆盖
    实证形态;连续性兜底留给未来出现「续局段恰好从 (p1,r1) 误读起」时)。

    段骨架三源(W3):journal 实机形态段(唯一活账;`_JOURNAL_RUN_ID_RE`
    过滤 sim/测试段)+ outcomes 首现序 + decisions 独有段——journal 时代
    旧流恒空(删除波 1 停写),历史目录重装配走旧流段路径,新局全走
    journal 段路径;两源段按段首 ts 统一插位,去重(journal 段优先)。
    时序插位(v11 修,ADR-0615):旧法把决策独有段排序后整体**补尾**,
    续局归组「并入 games[-1]」无时序门 → 该段被错组到时间上晚于它的最后
    一局名下(实证:run_20260908_210431 曾被组到比其段末帧晚 8.5 小时的
    g_20260909_053235 名下,锚点档案 g_20260908_165445 静默丢段)。按段首
    ts(跨源最小行 ts)插回时序位后,后继带 outcome 新局入流不再夺走前局
    的续段。边界:段首 ts 缺失(空串)的段无法比较,保持补尾退化(旧行为);
    同 ts 平手按 run_id 字典序保确定性。
    """
    outcomes = read_jsonl(Path(replay_dir) / 'outcomes.jsonl')
    decisions = read_jsonl(Path(replay_dir) / 'decisions.jsonl')
    runs = read_jsonl(Path(replay_dir) / 'runs.jsonl')
    # 新账段(W3 唯一活账;宽容消费单一源 read_journal_stats,同流两读法
    # 两契约曾致装配端崩——R3.1 落地审 F1;只采实机形态段,见常量注)
    jrows, _jstats = read_journal_stats(replay_dir)
    j_seg_order = [rid for rid in _journal_run_order(jrows)
                   if _JOURNAL_RUN_ID_RE.match(rid)]
    j_first_ts: dict[str, str] = {}
    j_first_frame: dict[str, tuple[int, int] | None] = {}
    for rid in j_seg_order:
        seg_rows = [r for r in jrows if r.get('run_id') == rid]
        ts_list = sorted(_row_ts(r) for r in seg_rows if _row_ts(r))
        j_first_ts[rid] = ts_list[0] if ts_list else ''
        j_first_frame[rid] = _journal_first_frame(seg_rows)
    # 段出现序骨架:outcomes 首现序
    seg_order: list[str] = []
    for o in outcomes:
        rid = o.get('run_id')
        if rid and (not seg_order or seg_order[-1] != rid) and rid not in seg_order:
            seg_order.append(rid)
    # 段首 ts 单遍账(run_id → 最小行 ts;跨 decisions/outcomes/journal,
    # 排序与插位共用;journal 段 ts 预先入账)
    _first_ts: dict[str, str] = dict(j_first_ts)
    for r in (*decisions, *outcomes):
        _rid = r.get('run_id')
        _ts = _row_ts(r)
        if not _rid or not _ts:
            continue
        _cur = _first_ts.get(_rid)
        if _cur is None or _ts < _cur:
            _first_ts[_rid] = _ts
    known = set(seg_order)
    # 插位候选 = 旧流决策独有段 ∪ journal 实机段(与骨架段去重;按段首 ts
    # 时序插位)
    extra = sorted(({r for r in {d.get('run_id') for d in decisions}
                     if r and r not in known}
                    | {r for r in j_seg_order if r not in known}),
                   key=lambda r: (_first_ts.get(r, ''), r))
    for rid in extra:
        _rid_ts = _first_ts.get(rid, '')
        _pos = len(seg_order)
        if _rid_ts:
            for _i, _cur in enumerate(seg_order):
                _cur_ts = _first_ts.get(_cur, '')
                if _cur_ts and _rid_ts < _cur_ts:
                    _pos = _i
                    break
        seg_order.insert(_pos, rid)
    games: list[dict[str, Any]] = []
    for rid in seg_order:
        fk = (_first_frame_key(decisions, rid)
              or _first_frame_key(outcomes, rid)
              or j_first_frame.get(rid))
        is_continuation = (fk is not None and fk != (1, 1)) and bool(games)
        if is_continuation:
            games[-1]['segments'].append(rid)
        else:
            games.append({'game_id': game_id_from_run(rid), 'segments': [rid]})
    for g in games:
        segs = set(g['segments'])
        all_ts = sorted(_row_ts(r) for src in (decisions, outcomes, runs)
                        for r in src if r.get('run_id') in segs and _row_ts(r))
        # journal 段行 ts 并入起止窗(旧流停写后新局的段窗唯一来源)
        all_ts += [j_first_ts[rid] for rid in sorted(segs)
                   if j_first_ts.get(rid, '')]
        all_ts.sort()
        g['start_ts'] = all_ts[0] if all_ts else ''
        g['end_ts'] = all_ts[-1] if all_ts else ''
    return games


def _journal_run_order(jrows: list[dict[str, Any]]) -> list[str]:
    """journal 行流内的段首现序(段 = run_id 变化处开新段;保序去重)。"""
    order: list[str] = []
    for r in jrows:
        rid = r.get('run_id')
        if rid and rid not in order:
            order.append(rid)
    return order


def _journal_first_frame(seg_rows: list[dict[str, Any]],
                         ) -> tuple[int, int] | None:
    """journal 段首帧键(段内最早带节点派生的行的 node 键;与旧流首帧判据
    同型——(p1,r1) = 新局)。行 ts 升序取首;无节点行(纯 receipts/事件段)
    = None(判新局,保守——续局段恒带备战帧节点)。"""
    best: tuple[str, tuple[int, int]] | None = None
    for r in seg_rows:
        ts = _row_ts(r)
        if not ts:
            continue
        if best is not None and ts >= best[0]:
            continue
        key = node_key_of(r)
        if key is not None:
            best = (ts, key)
    return best[1] if best else None


def _load_slice(replay_dir: Path, segments: set[str]) -> dict[str, list[dict[str, Any]]]:
    """按段集合过滤各 jsonl 流(只读;文件缺 = 空列表)。

    统一 state 新账键(``state/journal.jsonl``)走宽容读单一源
    (``journal_query.read_journal_stats``,与判读 CLI 同一契约——同流
    两读法两契约曾致装配端在截断尾上崩,R3.1 落地审 F1):半行/坏行 =
    逐行跳过 + 计数 log 申报(设计 §3.3 撕裂行消费契约;申报语义先例 =
    cw_loop ``_run_has_outcome_at``),非零计数才告警(常态零噪音)。
    旧 12 流仍走严格 ``read_jsonl``:框架自写行,坏行 = 事故,静默跳过
    会藏事故;字节层宽容只属新账(其物理截断可劈开多字节字符)。
    """
    out: dict[str, list[dict[str, Any]]] = {}
    for name in _SLICE_FILES:
        if name == JOURNAL_REL:
            rows, stats = read_journal_stats(replay_dir)
            if stats.total_skipped or stats.byte_repair_lines:
                log.warning(
                    '[cw][archive] %s(根 %s)宽容读取:跳过坏行 %d'
                    '(JSON 层 %d + 非对象 %d),字节层替换修复 %d 行'
                    '(设计 §3.3 撕裂行契约:截断尾 = 崩溃丢失窗合法形态,'
                    '跳过不解析)', name, replay_dir, stats.total_skipped,
                    stats.bad_json_lines, stats.non_dict_lines,
                    stats.byte_repair_lines)
        else:
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


def _load_derived_inputs(rd: Path, segments: set[str],
                         slice_rows: dict[str, list[dict[str, Any]]],
                         ) -> dict[str, list[dict[str, Any]]]:
    """派生列输入行集(重装配保真的输入供给,装配主路径在册函数)。

    - 为什么存在:v12 切片契约只含两文件(op_journal + state/journal),
      而 ``_build_rounds`` / ``_derive_departures`` 等派生函数的输入吃
      旧流键——不回源流,任何重装配(load_archive 版本迁移 /
      assemble_pending 段集增长 / 跨档守卫整体重装配)都会把
      rounds/loss_nodes/departures 等派生列全量清空(v7 注申报的
      「重装配无益有损」;T-242 真实双档重放实证)。
    - 供给语义:切片在档且非空的键原样透传(切片优先);缺键回源流文件
      按段集过滤读取——源流在 = 无损重装配;源流已清 = 空列表(与
      ``_load_slice`` 旧流「文件缺 = 空切片」同契约,诚实退化不猜测)。
    - 边界:产物只作装配端派生输入,不进档案 ``slices`` 载荷(v12 两
      文件契约不回填旧流键,裸数据考古归源流归档)。
    """
    out = dict(slice_rows)
    refilled: list[str] = []
    for name in _DERIVED_INPUT_FILES:
        if out.get(name):
            continue
        out[name] = [r for r in read_jsonl(rd / name)
                     if r.get('run_id') in segments]
        if out[name]:
            refilled.append(name)
    if refilled:
        log.info('[cw][archive] 派生列输入切片缺键,回源流补读 %s'
                 '(重装配保真路径)', refilled)
    return out


def _best_decision_frame(dec_rows: list[dict[str, Any]],
                         key: tuple[int, int]) -> dict[str, Any] | None:
    """同轮取 actions 最多、并列取 ts 最晚的决策帧(档案装配自持一份,
    不与判读读面共享私有函数)。"""
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
    """全集取 ts 最晚一帧(「ts 最晚行」扫描单一源,批审计消双源)。

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
      晚」选**决策帧**(计划动作最全的时点,先于 CwScreenDeploy/CwOpEquipAll
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
    文件名 tag=p{plane}-r{round},落 live 流根;可选证据,缺 = 空列表)。"""
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


# ===== 离场事件派生列(v10,T-109①,ADR-0605;装配端纯读) =====

#: 离场通道闭集(单一源;键语义见 _derive_departures docstring)
DEPARTURE_CHANNELS: tuple[str, ...] = (
    'sell_recorded',      # 该帧动作 SellDeployed 按 deployed_idx 换算解析命中此件(决策时点卖出)
    'merge_promoted',     # 同名更高星在后帧在场(买牌合成链,1★ 副本离场)
    'unexplained',        # 无卖出动作而消失 = 执行期 deploy 换血卖出信号通道
)


def _deployed_multiset(frame: dict[str, Any]) -> Counter | None:
    """帧 → 场上身份多重集 {(char_id, star): n};deployed 缺席/非列表 → None。

    None 语义 = 该帧场上身份不可知(旧数据/未采集),差分对这对帧跳过——
    宁缺勿造(与 hp 链「不可信不入链」同纪律);空列表是合法帧(开局板空)。
    """
    dep = (frame.get('state') or {}).get('deployed')
    if not isinstance(dep, list):
        return None
    ms: Counter = Counter()
    for e in dep:
        if isinstance(e, dict) and e.get('char_id'):
            try:
                star = int(e.get('star') or 1)
            except (TypeError, ValueError):
                star = 1
            ms[(str(e['char_id']), star)] += 1
    return ms


def _sell_deployed_target_names(frame: dict[str, Any]) -> set[str]:
    """帧动作里 SellDeployed 的卖出目标名集合(按同帧 deployed 解析槽位身份)。

    解析键 = 动作 ``deployed_idx``(= state.deployed 槽位表下标 0-9,
    ADR-0392)——这是唯一能落帧的生产形状:全仓唯一构造点 = kernel
    cw_state.SellDeployed(cw_evolution 谷底回滚 / sim engine,序列化字段
    deployed_idx/income/reason/expect,无 row/slot);cw_prep_actions 的
    同名 row+slot 类零构造点、且策略辖外声明不发射(test_cw_shop_line
    辖外锁),不会出现在 decisions 帧。

    换算命中而非下标直取:serialize_state 落遥测的 deployed 是**紧缩
    占用序**(ADR-0392,None 空槽剔除),帧内列表下标 ≠ 槽位表下标;
    deployed_idx→(排,排内槽号) 是固定双射(0-3=前排 1-4,4-9=后排
    1-6,deployed_slot_no 单一源),条目级 position_pref/slot 信息位随
    序列化保留、由 deployed_place 落位归一,按此对上。键缺失/越界 =
    解析不出身份,不入集合(该件落 unexplained,宁缺勿造不炸)。
    SellBench 卖的是备战席,不解释场上离场,不入集合。
    """
    names: set[str] = set()
    dep = (frame.get('state') or {}).get('deployed') or []
    for a in frame.get('actions') or []:
        if not isinstance(a, dict) or a.get('__type__') != 'SellDeployed':
            continue
        idx = a.get('deployed_idx')
        if isinstance(idx, bool) or not isinstance(idx, int) \
                or not 0 <= idx < DEPLOYED_CAPACITY:
            continue
        row = 'front' if idx < DEPLOYED_FRONT_CAPACITY else 'back'
        slot_no = deployed_slot_no(idx)
        for e in dep:
            if (isinstance(e, dict) and e.get('char_id')
                    and e.get('position_pref') == row
                    and e.get('slot') == slot_no):
                names.add(str(e['char_id']))
    return names


def _derive_departures(dec: list[dict[str, Any]],
                       segments: list[str]) -> list[dict[str, Any]]:
    """顶层 ``departures`` 派生列(v10,ADR-0605;纯读,零运行时写入)。

    - 缺口与实锤:执行期 deploy 换血卖出(CwScreenDeploy._sell_offtarget_deployed)
      逐件身份只在 log 行与匿名计数键,无遥测行——复盘实证 g_20260907_075840
      p1r1 Saber(08:00:18 帧 [椒丘,藿藿,Saber] → 08:00:42 帧 [椒丘,艾丝妲,
      藿藿],无任何 Sell 动作)。决策时点卖出(SellBench/SellDeployed)本就
      逐件在案(actions+期望态快照,决策迹),不在本列重复。
    - 派生口径:段内相邻决策帧(第 1 基,ts 升序)的 state.deployed 身份
      多重集差;任一侧身份不可知(缺/非列表)整对跳过。战斗不改场上
      (部署/买卖只发生在备战期),帧间差分即备战动作净效果。
    - 通道分键(closed set = DEPARTURE_CHANNELS):
      sell_recorded = 该帧 SellDeployed 按 deployed_idx 换算解析命中
      (解析口径见 _sell_deployed_target_names);merge_promoted =
      同名更高星在后帧在场(买牌 3 合 1 的 1★ 副本离场);unexplained =
      其余,首义 = 换血卖出(离场常伴 1:1 到场,行内 same_window_arrivals
      可并读)。感知纠噪(SIFT 翻转)也可能落入 unexplained——本列不与
      obs_conflicts 交叉裁决(跨局流不入切片),判读并读。
    - 行形状:{run_id, plane, round, ts, char, star, count, channel,
      same_window_arrivals};按 ts 全局升序。末帧无后继,终局前最后一段
      备战窗的离场不可见(诚实边界,判读申报)。
    """
    out: list[dict[str, Any]] = []
    for rid in segments:
        frames = sorted((d for d in dec if d.get('run_id') == rid),
                        key=_row_ts)   # 稳定排序:同秒保文件追加序
        # strict=False:相邻对滑动窗口,两序列长度有意差一
        for fr_a, fr_b in zip(frames, frames[1:], strict=False):
            ms_a = _deployed_multiset(fr_a)
            ms_b = _deployed_multiset(fr_b)
            if ms_a is None or ms_b is None:
                continue   # 身份不可知帧对:宁缺勿造
            departed = ms_a - ms_b
            if not departed:
                continue
            arrived = ms_b - ms_a
            arr_names = sorted({name for (name, _s) in arrived})
            sell_names = _sell_deployed_target_names(fr_a)
            next_top_star: dict[str, int] = {}
            for (name, star) in ms_b:
                next_top_star[name] = max(next_top_star.get(name, 0), star)
            for (name, star), cnt in sorted(departed.items()):
                if name in sell_names:
                    channel = 'sell_recorded'
                elif next_top_star.get(name, 0) > star:
                    channel = 'merge_promoted'
                else:
                    channel = 'unexplained'
                out.append({
                    'run_id': rid, 'plane': fr_a.get('plane'),
                    'round': fr_a.get('round_num'), 'ts': _row_ts(fr_a),
                    'char': name, 'star': star, 'count': cnt,
                    'channel': channel, 'same_window_arrivals': arr_names})
    out.sort(key=_row_ts)
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
    dec = slice_rows.get('decisions.jsonl') or []
    outs = slice_rows.get('outcomes.jsonl') or []
    snaps = slice_rows.get('shop_snapshots.jsonl') or []
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
        # 同轮全帧动作合并(流内序;口径以本实现为唯一载体,判读读面不共享):
        # 代表帧只承载字段展示,动作计数不能只看代表帧——载体帧与决策帧
        # 同为单动作时「并列取末帧」让载体帧胜出,该轮买/升/刷全计 0
        # (实证 g_20260903_232823 p1r1/r2;计划口径边界见 query.plan_gold_flow
        #  docstring「口径边界」)。
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
            # (_best_decision_frame:决策时点,先于 CwScreenDeploy/CwOpEquipAll
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
    for r in slice_rows.get('exogenous.jsonl') or []:
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
    dec = slice_rows.get('decisions.jsonl') or []
    outs = slice_rows.get('outcomes.jsonl') or []
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


def build_archive(replay_dir: Path | str, game: dict[str, Any]) -> dict[str, Any]:
    """装配单局档案 dict(纯读 + 内存组装;不落盘)。

    ``game`` = ``assign_games`` 的元素(game_id/segments/start_ts/end_ts)。
    """
    rd = Path(replay_dir)
    segments: list[str] = list(game['segments'])
    seg_set = set(segments)
    slice_rows = _load_slice(rd, seg_set)
    # 派生列输入供给(重装配保真):v12 切片无旧流键,缺键回源流补读,
    # 消除「重装配派生列全空」(语义见 _load_derived_inputs)
    derived_rows = _load_derived_inputs(rd, seg_set, slice_rows)
    runs_rows = [r for r in read_jsonl(rd / 'runs.jsonl')
                 if r.get('run_id') in seg_set]
    runs_by_seg = {r.get('run_id'): r for r in runs_rows}
    last_summary = runs_by_seg.get(segments[-1]) if segments else {}
    result = str((last_summary or {}).get('result') or '')
    # abandoned 判定:末段无 runs 摘要(收口路径没走)或 result 非完结值域
    abandoned = (not result) or (result not in _TERMINAL_RESULTS)
    rounds, loss_nodes, boundaries, hp_pay_defects = _build_rounds(
        rd, derived_rows, segments, result)
    seg_summaries = [
        {'run_id': rid,
         'first_frame': _first_frame_key(derived_rows.get('decisions.jsonl') or [], rid)
         or _first_frame_key(derived_rows.get('outcomes.jsonl') or [], rid),
         'summary': runs_by_seg.get(rid),
         # 零结算段自标识(v11 加法,见 _settlement_gap;非零结算段键缺省)
         **_settlement_gap(derived_rows.get('decisions.jsonl') or [],
                           derived_rows.get('outcomes.jsonl') or [], rid,
                           runs_by_seg.get(rid))}
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
    # 局终行识别(R5 W2):game 终局 = 段序末段的局终行(局终域 = 段级
    # 事实,恢复局跨段多行,聚合取末行);末段无局终行 = None(旧档案/
    # 旧产物无账本形态,判读按「新账无终局行」对待)。加法键不 bump
    # SCHEMA_VERSION 申报:本键只能派生自新账行,存量档案源流已清无法
    # 经重装配获得(bump 只产生无效重装配尝试),读侧宽容缺键。
    _final_rows = extract_match_final_rows(slice_rows.get(JOURNAL_REL))
    return {
        'schema_version': SCHEMA_VERSION,
        'game_id': game['game_id'],
        # (顶层 ``cw4_counters`` 已随 R5 W4 流删拆除:流载体
        #  ``cw4_counters.jsonl`` 写端/装配面整体退役,局终级全键聚合
        #  收编载体 = 局终域行载荷 ``MatchFinal.cw4_counters``,档案显影
        #  位 = ``endgame.match_final.final.cw4_counters``;存量已装配
        #  档案的旧顶层字段是已落盘数据,本端不删不改,读侧宽容缺键。)
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
            _resume_reconciliation(segments, derived_rows), boundaries),
        'rounds': rounds,
        'loss_nodes': loss_nodes,
        # hp 变化事件显影列(v9 加法,装配端纯读;旧档案恒空 = 采集面修复
        # 只及新局)与 modeled 期望账对账偏差列(v9 加法,留证不阻塞)
        'hp_events': _hp_pay_events(derived_rows.get('exogenous.jsonl') or []),
        'hp_pay_defects': hp_pay_defects,
        # 离场事件派生列(v10 加法,ADR-0605;装配端纯读,旧档案重装配补齐):
        # 执行期 deploy 换血卖出逐件落账缺口(075840 Saber 实锤)的判读面。
        'departures': _derive_departures(derived_rows.get('decisions.jsonl') or [],
                                         segments),
        'opening': _build_opening(derived_rows, runs_by_seg),
        'endgame': {'result': result or 'abandoned',
                    'abandoned': abandoned,
                    'plane_reached': (last_summary or {}).get('plane_reached'),
                    'rounds_survived': (last_summary or {}).get('rounds_survived'),
                    'final_hp': (last_summary or {}).get('final_hp'),
                    'difficulty': (last_summary or {}).get('difficulty'),
                    # 局级终局快照(M2 增强批 ③;None=零决策迹局):
                    # 终局阵容/金/等级,取值口径见 _final_snapshot。
                    'final_snapshot': _final_snapshot(
                        derived_rows.get('decisions.jsonl') or []),
                    # 局终行(局终域识别,R5 W2;None=末段无局终行):
                    # runs 收编载体的档案显影位,局边界判定读此键。
                    'match_final': match_final_view(
                        _final_rows.get(segments[-1]) if segments else None),
                    'segment_summaries': seg_summaries},
        'slices': slice_rows,
    }


def _build_opening(slice_rows: dict[str, list[dict[str, Any]]],
                   runs_by_seg: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """开局面:词缀/难度/投资卡简报(invest_cards 全行带 chosen 位)。"""
    briefing = [r for r in slice_rows.get('exogenous.jsonl') or []
                if (r.get('kind') or '') == 'briefing']
    invest = slice_rows.get('invest_cards.jsonl') or []
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


# 装配主体(不带跨档守卫;公开入口 assemble_game/assemble_pending 收尾统一
# 走 _converge_cross_archive_ownership,守卫内部重装配也走本函数防递归套娃)


def _assemble_game_once(replay_dir: Path | str,
                        game_id: str) -> dict[str, Any] | None:
    """装配指定局主体(不问水位线;游戏不存在 → None)。"""
    rd = Path(replay_dir)
    game = next((g for g in assign_games(rd) if g['game_id'] == game_id), None)
    if game is None:
        return None
    archive = build_archive(rd, game)
    _atomic_write_json(archive_path(rd, game_id), archive)
    rebuild_index(rd)
    return archive


def find_cross_archive_segment_dups(
        replay_dir: Path | str) -> list[dict[str, Any]]:
    """跨档案段归属核验(纯读):同段 run_id 出现在多个档案的段集即违例。

    违例形态即「跨档段重复入账」:同一 journal 行集被两个档案各自内嵌
    切片,跨档对照同时段会双计(T-232 验收实证:run_20260908_210431 曾
    同时在 g_20260908_165445 与 g_20260909_084216 的切片里)。核验单位 =
    段级(档案 segments 的 run_id):档案切片由 build_archive 严格按段集
    过滤(单一写端契约),「同段跨档案」⇒「同段行跨档案」,段级判据即
    行级双计的充分条件;行级逐行对账是档案完整性问题(手改/半截),不属
    本核验辖域。返回 ``[{run_id, archives: [game_id...]}]``,空 = 通过。
    """
    md = matches_dir(replay_dir)
    owners: dict[str, list[str]] = {}
    for p in sorted(md.glob('match_*.json')):
        try:
            with p.open('r', encoding='utf-8') as f:
                a = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue   # 半截/损坏档案跳过(与 rebuild_index 同契约)
        gid = str(a.get('game_id') or '')
        if not gid:
            continue
        for s in a.get('segments') or []:
            rid = str(s.get('run_id') or '')
            if not rid:
                continue
            owners.setdefault(rid, [])
            if gid not in owners[rid]:
                owners[rid].append(gid)
    return [{'run_id': rid, 'archives': gids}
            for rid, gids in sorted(owners.items()) if len(gids) > 1]


def _warn_cross_archive_dups(rd: Path) -> list[dict[str, Any]]:
    """装配收尾核验:违例逐条 WARNING 显影(判读可见,不阻塞装配)。"""
    dups = find_cross_archive_segment_dups(rd)
    for d in dups:
        log.warning('[cw][archive] 段 %s 同时存在于 %d 个档案 %s——'
                    '跨档段重复入账,跨档对照会双计(装配守卫未能收敛,'
                    '常见于双档源流均已清理、归属无法重派生的孤立形态)',
                    d['run_id'], len(d['archives']), d['archives'])
    return dups


#: 剪枝记录的成因常量(唯一调用点 = 源流失档案的定向剪枝;被剪段仍在
#: live 流、归属可重派生时走整体重装配,不产生本记录)
_PRUNE_REASON = 'foreign_segment_owned_elsewhere'


def _prune_foreign_segments(path: Path, archive: dict[str, Any],
                            foreign: list[str],
                            owner: dict[str, str]) -> list[str]:
    """源流失档案的定向剪枝:摘除归属他局的段条目与全部切片行。

    为什么是剪枝不是重装配:该局的源流行已被清理(assign_games 分不出
    本局),build_archive 无从重派生;剪枝只动「归属错误」的面(段集 +
    切片),rounds/loss_nodes 等派生列基于剪枝前段集、保留不动——档案
    级 ``pruned_segments`` 显影记录声明这一局限,判读跨档对照以被剪段
    的归属局档案为准。schema_version 不动(不宣称按当前口径全量重派生)。
    """
    foreign_set = set(foreign)
    archive['segments'] = [s for s in archive.get('segments') or []
                           if str(s.get('run_id') or '') not in foreign_set]
    slices = archive.get('slices')
    if isinstance(slices, dict):
        for k, rows in slices.items():
            if isinstance(rows, list):
                slices[k] = [r for r in rows
                             if r.get('run_id') not in foreign_set]
    record = [{'run_id': rid, 'owned_by': owner.get(rid, ''),
               'reason': _PRUNE_REASON} for rid in foreign]
    # 追加式(与 criteria 同纪律):多次剪枝的历史共存,不覆盖前记录
    archive['pruned_segments'] = list(archive.get('pruned_segments') or []) \
        + record
    archive['archived_at'] = datetime.now().isoformat(timespec='seconds')
    _atomic_write_json(path, archive)
    return foreign


def _converge_cross_archive_ownership(
        rd: Path, games: list[dict[str, Any]]) -> list[str]:
    """跨档案归属收敛守卫:档案段集中「当前分组归他局」的段全部摘除。

    根因(T-242):旧装配口径时代的存量档案可能错误持有后续才归前局的
    续段(如 g_20260909_084216 持有 run_20260908_210431),而该档案常落
    水位线以下(end_ts <= wm 被 assemble_pending 永久跳过)、判读又直读
    JSON 不经 load_archive 的读端重装配——错误归属永续,跨档双计。本
    守卫在每次装配收尾按当前口径全局对账:
    - 本局仍在分组(源流在)→ 整体重装配(build_archive 按当前口径
      重派生,派生列一并自愈);
    - 本局已不在分组(源流失)→ 定向剪枝(:func:`_prune_foreign_segments`)。
    分组判定为「该段活着且归他局」才触发;分组无此段(孤本形态,live 流
    已清且无第二档案持有)不辖——孤本是唯一存档,禁动。
    返回被收敛(重装配或剪枝)的 game_id 列表。收敛方向单向(每次触发
    严格减少全局多余段数),循环内联处理全部违例档案,不递归套守卫。
    """
    owner: dict[str, str] = {}
    for g in games:
        for rid in g['segments']:
            owner[rid] = g['game_id']
    known_games = {g['game_id'] for g in games}
    md = matches_dir(rd)
    touched: list[str] = []
    for p in sorted(md.glob('match_*.json')):
        try:
            with p.open('r', encoding='utf-8') as f:
                a = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        gid = str(a.get('game_id') or '')
        if not gid:
            continue
        foreign = [rid for rid in (str(s.get('run_id') or '')
                                   for s in a.get('segments') or [])
                   if rid and owner.get(rid, gid) != gid]
        if not foreign:
            continue
        if gid in known_games:
            rebuilt = _assemble_game_once(rd, gid)
            if rebuilt is not None:
                touched.append(gid)
                log.info('[cw][archive] 档案 %s 段集与当前归属口径不符'
                         '(多余段 %s)——按当前口径整体重装配收敛',
                         gid, foreign)
                continue
            log.warning('[cw][archive] 档案 %s 有多余段 %s 且本局在分组'
                        '但重装配失败——保持原样交核验显影', gid, foreign)
            continue
        pruned = _prune_foreign_segments(p, a, foreign, owner)
        touched.append(gid)
        log.info('[cw][archive] 档案 %s(源流已清)定向剪枝多余段 %s'
                 '(归属见档案内 pruned_segments 记录)', gid, pruned)
    if touched:
        rebuild_index(rd)
    return touched


def assemble_game(replay_dir: Path | str, game_id: str) -> dict[str, Any] | None:
    """装配指定局(补装配入口:不问水位线;游戏不存在 → None)。

    收尾走跨档归属收敛守卫 + 核验(:func:`_converge_cross_archive_ownership`
    / :func:`_warn_cross_archive_dups`):本局装配可能收编其他存量档案
    错误持有的段,守卫保证「同一 journal 段只归属一个档案」。
    """
    rd = Path(replay_dir)
    archive = _assemble_game_once(rd, game_id)
    if archive is None:
        return None
    _converge_cross_archive_ownership(rd, assign_games(rd))
    _warn_cross_archive_dups(rd)
    return archive


def _read_watermark(replay_dir: Path) -> str:
    p = matches_dir(replay_dir) / _WATERMARK_NAME
    try:
        with p.open('r', encoding='utf-8') as f:
            return str(json.load(f).get('archived_through') or '')
    except (OSError, json.JSONDecodeError, AttributeError):
        return ''


def _write_watermark(replay_dir: Path, through_ts: str) -> None:
    p = matches_dir(replay_dir) / _WATERMARK_NAME
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
    装配的 game_id 列表。收尾走跨档归属收敛守卫与核验(含水位线以下的
    存量档案——双计档案的收敛不问水位线,见模块 docstring 归局骨架节)。
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
        # 首跑目录也可能有手工放置的存量档案,跨档守卫不因早退缺席
        _converge_cross_archive_ownership(rd, games)
        _warn_cross_archive_dups(rd)
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
    # 跨档归属收敛 + 核验(T-242):水位线上方新装配的局可能收编存量档案
    # 错误持有的续段(该档案常落水位线以下,只随本守卫收敛,双计才可消)
    _converge_cross_archive_ownership(rd, games)
    _warn_cross_archive_dups(rd)
    return done


def materialize_slice(archive: dict[str, Any], tmp_root: Path) -> Path:
    """档案切片 → 临时 replay 目录(供 ``--match`` 复用 query_* 视图)。

    写切片文件后原目录可直接传给 query 视图函数——与 ``--run`` 走同一套
    实现,输出保证一致(单一源)。相对路径切片(v12 ``state/journal.jsonl``)
    按同名相对路径落盘,新账读面(telemetry.journal_query)读同一相对位置。
    """
    tmp_root.mkdir(parents=True, exist_ok=True)
    for name, rows in (archive.get('slices') or {}).items():
        out_p = tmp_root / name
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with out_p.open('w', encoding='utf-8') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False,
                                   separators=(',', ':')) + '\n')
    return tmp_root
