"""局后钩子:Δ池自动再生与重放检查聚合(自 cw_telemetry 拆出,分包期6)。

归属 sim 桶:Δ池再生直接调 sim 生成器;恢复/覆盖检查族与 run_checks
聚合是 run 收口面,telemetry 的 state.start_run/recorder 经由本模块调用
(模块级 import 无环:hooks→query/schema/checks,state 不在模块级反依)。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sr_od.application.currency_war.kernel.cw_intention import _to_jsonable
from sr_od.application.currency_war.telemetry.query import (
    _list_runs,
    check_strategy_live_streak,
    read_jsonl,
)
from sr_od.application.currency_war.telemetry.schema import RunSummary, append_jsonl
from sr_od.application.currency_war.telemetry import state as _telstate
from sr_od.application.currency_war.telemetry.state import log

# ===== 局终 summary 多路径兜底(ADR-0273;批⑧ F2 runs.jsonl 断流)=====
# 写端三路径:① 3c 回大厅(正常终局 win/loss);② 迁移审计 w75(git 历史) after_operation_done
# 收口(停止/超时/异常退出 result='stopped'/'abandoned',battle_loop.py 类注);
# ③ 本兜底(进程崩溃/重启杀局,start_run 每局起点补 source='recovered')。
# r363 曾在 loop() 顶查 is_context_stop —— 但 operation.execute() 每轮前
# (operation.py:408)先查 stop,stop 到达后 loop() 不再被调,原检查几乎永不
# 触发(MCP stop 四局 [RUNS-GAP] 实锤),故收口迁 after_operation_done(ADR-0335)。

def _runs_summarized(replay_dir: Path) -> set[str]:
    """runs.jsonl 已有 summary 行的 run_id 集(幂等判据单一源)。"""
    return {r.get('run_id') for r in read_jsonl(replay_dir / 'runs.jsonl')
            if r.get('run_id')}



def build_recovered_summary(replay_dir: Path, run_id: str) -> RunSummary | None:
    """从 outcomes/decisions 重建一局 summary(ADR-0273 数据治理:补算回填)。

    - 末条真值按 (plane, round) 排序取最后(round_num 是位面内编号,跨位面
      重建须按 (plane, round) 排序——批⑧边界声明);
    - final_hp 取 conf≥0.9 末条 hp_after(镜像 loop `_last_true_hp` 语义:
      死局 hp 读不到时兜底 100 毒化,高置信真值优先);final_hp≤0 → 'loss'
      (战败结算屏 hp=0 补录链),否则 'abandoned'(FAIL/崩溃/重启局无终局判定);
    - 无 outcomes → None(留缺口,不造伪值)。
    """
    outcomes = [o for o in read_jsonl(replay_dir / 'outcomes.jsonl')
                if o.get('run_id') == run_id]
    if not outcomes:
        return None
    outcomes.sort(key=lambda o: (o.get('plane') or 1, o.get('round_num') or 0,
                                 o.get('ts') or ''))
    last = outcomes[-1]
    plane_reached = max((o.get('plane') or 1) for o in outcomes)
    _conf_rows = [o for o in outcomes if (o.get('hp_confidence') or 0) >= 0.9]
    final_hp = int((_conf_rows[-1] if _conf_rows else last).get('hp_after') or 0)
    result = 'loss' if final_hp <= 0 else 'abandoned'
    decisions = [d for d in read_jsonl(replay_dir / 'decisions.jsonl')
                 if d.get('run_id') == run_id]
    difficulty = next((d.get('difficulty') for d in decisions if d.get('difficulty')), '')
    # gold 轨迹:每 (plane, round) 首采样(镜像 recorder 内存去重键 r363)
    gold_traj: list[int] = []
    _seen: set = set()
    for d in decisions:
        k = (d.get('plane'), d.get('round_num'))
        if k in _seen:
            continue
        _seen.add(k)
        gold_traj.append(int(d.get('gold') or 0))
    # pivot:target_comp 序列连续去重后的转移数(内存 _comms 同语义)
    comms: list[str] = []
    for d in decisions:
        t = d.get('target_comp') or ''
        if t and (not comms or comms[-1] != t):
            comms.append(t)
    return RunSummary(
        ts=datetime.now().isoformat(timespec='seconds'),
        run_id=run_id, difficulty=difficulty,
        result=result, plane_reached=plane_reached,
        rounds_survived=int(last.get('round_num') or 0),
        final_hp=final_hp, comps_committed=comms,
        pivot_count=max(0, len(comms) - 1),
        gold_trajectory=gold_traj,
        notes='recovered:FAIL/crash/restart 兜底(ADR-0273)',
        source='recovered',
    )



def recover_dangling_run_summaries(replay_dir: Path | str | None = None) -> list[str]:
    """补齐 runs.jsonl 缺行(幂等;start_run 每局起点调,盖 FAIL/崩溃/重启路径)。

    returns 本次补写的 run_id 列表(已 summaried 的不重复;无 outcomes 的跳过)。
    """
    d = Path(replay_dir) if replay_dir is not None else _telstate.get_recorder().replay_dir
    if not (d / 'outcomes.jsonl').exists():
        return []
    known = _runs_summarized(d)
    ids: list[str] = []
    _seen: set = set()
    for o in read_jsonl(d / 'outcomes.jsonl'):
        rid = o.get('run_id')
        if rid and rid not in known and rid not in _seen:
            _seen.add(rid)
            ids.append(rid)
    rec = _telstate.get_recorder()
    recovered: list[str] = []
    for rid in ids:
        summary = build_recovered_summary(d, rid)
        if summary is None:
            continue
        append_jsonl(d / 'runs.jsonl', _to_jsonable(summary))
        # 内存累积同步清理(防跨 run 泄漏;语义同 record_run_summary 尾部)
        rec._gold_trajectory.pop(rid, None)
        rec._comms.pop(rid, None)
        rec._difficulty.pop(rid, None)
        recovered.append(rid)
    if recovered:
        log.info('[cw][telemetry] summary 兜底回填 %d 局(ADR-0273):%s',
                 len(recovered), ','.join(recovered))
        # 迁移审计 w109(git 历史)(ADR-0344):兜底行也是 runs.jsonl 新增——同样触发池再生
        # (崩溃恢复局的语料此刻才齐,不等到下一局正常局终)。
        _regenerate_delta_pool_after_run()
    return recovered



def _regenerate_delta_pool_after_run() -> None:
    """迁移审计 w109(git 历史)(ADR-0344):局终→Δ池快照自动再生 + 新鲜度自检。

    事故背景:2026-08-25 查实池快照停在凌晨(41 局),当天 4 局未入
    池——sim encounter/boss 零胜例把 P1 后段钉死全败,管线断 12
    小时无任何报警。治本 = 再生随 runs.jsonl 写入端走(正常局终
    record_run_summary + 崩溃兜底 recover_dangling_run_summaries),
    加新鲜度检查项双端挂(sim 批 + 生产自检)。

    best-effort 纪律:再生/自检失败只记日志,**绝不向局终收尾传播
    异常**(遥测基建故障不许影响对局本体)。
    """
    try:
        from sr_od.application.currency_war.sim.cw_delta_pool_gen import (
            regenerate_snapshot,
        )
        fp = regenerate_snapshot(quiet=True)
    except Exception as e:   # noqa: BLE001
        log.warning('[cw][pool-pipeline] Δ池再生失败(不阻塞局终,ADR-0344): %s', e)
        return
    log.info('[cw][pool-pipeline] 局终自动再生 Δ池快照: %s', fp)
    try:

        from sr_od.application.currency_war.sim.checks.pool import check_pool_freshness
        verdict = check_pool_freshness()
        if verdict.get('violations'):
            # 再生刚成功却仍滞后 = 新局语料没进池(如 outcomes 缺行)
            # ——正是新鲜度检查要抓的病态,留痕不抛。
            log.warning('[cw][pool-pipeline] 再生后池新鲜度仍滞后'
                        '(ADR-0344): %s', verdict)
    except Exception as e:   # noqa: BLE001
        log.warning('[cw][pool-pipeline] 新鲜度自检异常(不阻塞): %s', e)



def check_summary_write_path_coverage(replay_dir: Path, recent: int = 10) -> list[str]:
    """检查项 ``summary_write_path_coverage``(批⑧设计,ADR-0273 入栈)。

    判据 = 最近 N 个(有 outcomes 的)run 全部有 summary 行(含 source=recovered
    兜底行)。违规行带 run_id 溯源;连续 10 局 100% = 修复验收线。
    """
    ids: list[str] = []
    for o in read_jsonl(replay_dir / 'outcomes.jsonl'):
        rid = o.get('run_id')
        if rid and (not ids or ids[-1] != rid):
            ids.append(rid)
    recent_ids = ids[-recent:]
    if not recent_ids:
        return ['[coverage] ⊘ 无 outcomes 语料,无法判']
    known = _runs_summarized(replay_dir)
    missing = [rid for rid in recent_ids if rid not in known]
    if missing:
        return [f'[coverage] ⚠ summary_write_path_coverage {len(missing)}/{len(recent_ids)} 局缺行:'
                + ','.join(missing)]
    return [f'[coverage] ✓ summary_write_path_coverage 最近 {len(recent_ids)} 局 100%']



#: 段级生产检查集(生产决策帧合并行可判的段级检查子集):
# - seg_overflow_idle_spend(P1 [17]):判据只吃 gold/actions/state formed_stop
#   /engines 代理,生产合并行同构;
# - seg_p2_bleed_gold_stack(P2 [17] 延伸,ADR-0479):只吃 gold/hp 及其
#   可读位。
# 其余段级检查消费 sim 专有键(shop_waves 牌面波/income/spend 分解),
# 生产决策迹无同构数据源,接入即失明或误报,不在本子集(缺口已声明,
# 待 shop_snapshots join 通路后再扩)。
_PRODUCTION_SEGMENT_CHECKS = (
    'seg_overflow_idle_spend',
    'seg_p2_bleed_gold_stack',
)

_SPEND_ACTION_TYPES = ('BuyCard', 'LevelUp', 'RefreshShop')


def merge_round_rows(rows: list[dict]) -> list[dict]:
    """生产决策帧(一帧一行,一轮多帧)→ 轮合并行(ledger 同构形状)。

    段级检查的输入口径 = 一轮一行(sim 账本);生产 decisions.jsonl
    一轮 5-12 帧(pre-refresh/post-refresh/buy/deploy/equip 各一帧,
    每帧 gold 是决策时点金)。合并口径:
    - gold/hp/gold_readable/hp_readable = 本轮**首帧**(决策时点;
      与段级 ``_seg_gold0``「首波 gold」同口径——末帧 gold 已含本轮
      花销,拿去判「溢余未泄」会系统性偏小);
    - actions = 全帧**花费类**动作并集(BuyCard/LevelUp/RefreshShop;
      生产 wrapper 动作 RunBuyPhase/RunDeploy/StartBattle 等非花费,
      不入——段级 ``_seg_spent`` 按 __type__ 白名单判,混入无害但
      并集只留花费类更省);
    - formed_stop = 全帧或;
    - state = 首帧 state 派生:board→board_factions(engines 代理的
      生产同构键;生产 GameState 快照无 board_factions 键)、
      deployed/bench/level/cap 照抄;
    - sim.bench_full_skipped_buys = 任一帧 state.bench_full_flag 置 1
      (bench 满想买买不了的段级豁免面,生产无 sim 计数键,用旗标
      作保守镜像——旗标在 = 该轮存在满栏语境,宁豁免不误报)。
    排序按 (plane, round, ts);纯读,不改输入行。
    """
    merged: dict[tuple, dict] = {}
    for d in sorted(rows, key=lambda r: ((r.get('plane') or 0),
                                         (r.get('round_num') or 0),
                                         (r.get('ts') or ''))):
        pl = d.get('plane') or 1
        rn = d.get('round_num') or 0
        key = (pl, rn)
        st = d.get('state') or {}
        if key not in merged:
            merged[key] = {
                'plane': pl, 'round_num': rn,
                'gold': d.get('gold'),
                'gold_readable': d.get('gold_readable', True),
                'hp': d.get('hp'),
                'hp_readable': d.get('hp_readable', True),
                'formed_stop': bool(d.get('formed_stop')),
                'actions': [], 'target_comp': d.get('target_comp') or '',
                'state': {
                    'board_factions': dict(st.get('board') or {}),
                    'deployed': st.get('deployed') or [],
                    'bench': st.get('bench') or [],
                    'level': st.get('level'),
                    'cap': st.get('deploy_cap'),
                },
                'sim': {
                    'node': st.get('node_type') or '',
                    'bench_full_skipped_buys':
                        1 if st.get('bench_full_flag') else 0,
                },
            }
        else:
            m = merged[key]
            m['formed_stop'] = m['formed_stop'] or bool(d.get('formed_stop'))
            if d.get('target_comp'):
                m['target_comp'] = d['target_comp']
            if st.get('bench_full_flag'):
                m['sim']['bench_full_skipped_buys'] = 1
        merged[key]['actions'].extend(
            a for a in d.get('actions') or []
            if a.get('__type__') in _SPEND_ACTION_TYPES)
    return [merged[k] for k in sorted(merged)]


def run_production_segment_checks(rows: list[dict]) -> list[str]:
    """对单局轮合并行跑段级生产子集 → 判读行(⚠ 事件 / ✓ 无违规)。

    只读观测报警:检查器事件走 defect 通道供判读消费,**不触发任何
    决策动作、不自动停线**(立案A 边界:检查器补覆盖只动 telemetry/
    sim 检查栈,决策层零触碰)。开销 = 纯 dict 扫描,百帧局毫秒级;
    挂在判读 CLI(checks)按需跑,对局运行时零开销。
    """
    from sr_od.application.currency_war.sim.checks.segments import (
        run_segment_checks,
    )
    merged = merge_round_rows(rows)
    rep = run_segment_checks([merged], seed_base=0)
    events: list[tuple[str, dict]] = []
    for name in _PRODUCTION_SEGMENT_CHECKS:
        for ev in rep.get(name, {}).get('events', []):
            events.append((name, ev))
    rid = rows[0].get('run_id', '?') if rows else '?'
    if not events:
        return [f'{rid}: [段级] ✓ 无违规']
    counts = {n: sum(1 for nm, _ in events if nm == n)
              for n in _PRODUCTION_SEGMENT_CHECKS}
    head = f'{rid}: [段级] ⚠ {len(events)} 条(' \
           + ', '.join(f'{n}={c}' for n, c in counts.items() if c) + ')'
    lines = [head]
    for name, ev in events:
        lines.append(f'    [{name}] p{ev.get("plane")}r{ev.get("round_num")}'
                     f' {ev.get("detail")}')
    return lines


def run_checks_on_replay(replay_dir: Path, recent: int = 5) -> list[str]:
    """生产遥测接 checks(决策项 1):对最近 N 局跑栈适配的检查集。

    - 判栈(逐局):strategy_id∈{'line_v2'[历史,ADR-0336 已删],
      'decision_v2'} 或开局轮 BuyCard reason 含 v2 词表
      (line/bridge_seed/engine/pair/off) → v2 栈(reason 词表与
      coldstart 检查集同辖);
      reason 全 'plan'/空 → default 栈(cw_plan,不辖 r368 门);
      非空未知 sid → 显式跳过(未来新栈不盲跑,审查#5);
    - **开局轮逐行全检**(审查#3:_load_decisions_rounds 的
      max-actions 单行选取是有损投影——生产开局轮实测 5-6 行,
      pre-refresh 波的违规买牌可被 post-refresh 大行静默挤掉;
      checks 只聚合开局轮 r≤2 的**全部行**的 BuyCard);
    - **可判性声明**(审查#2:开局轮买牌 reason 缺失=打标不全
      时代数据,输出 ⊘ 无法判 而非 ✓——不把不可判伪装成健康);
    - ledger_consistency 不跑(需 sim 键;生产金对账归
      econ_reconcile 工具链,不重复造轮子);
    - 输出行化(判读 CLI 风格),违规局带 run_id 可溯源;
    - ADR-0273:头部附 ``summary_write_path_coverage``(runs.jsonl 断流守卫,
      与逐局检查正交——它是「分母完整性」,先于一切逐局判读)。
    """

    from sr_od.application.currency_war.sim.checks.ledger import (
        check_coldstart_seed_squander,
    )
    lines: list[str] = list(check_summary_write_path_coverage(replay_dir))
    # ADR-0260:engine_seed=P1 未持有引擎件放行通道(v2 栈
    # [line_v2/decision_v2] 合法词)
    _V2_REASONS = {'line', 'bridge_seed', 'engine', 'engine_seed', 'pair',
                   'off', 'p2_core', 'board_focus', 'emergency', 'swap'}
    runs = _list_runs(replay_dir)[-recent:]
    for rid in runs:
        # 开局轮逐行(plane1 r≤2;不走 max-actions reducer——审查#3)
        rows = [d for d in read_jsonl(replay_dir / 'decisions.jsonl')
                if d.get('run_id') == rid
                and (d.get('plane') or 1) == 1
                and (d.get('round_num') or 9) <= 2]
        rows.sort(key=lambda d: ((d.get('round_num') or 0),
                                 (d.get('ts') or '')))
        all_rows = [d for d in read_jsonl(replay_dir / 'decisions.jsonl')
                    if d.get('run_id') == rid]
        # 迁移审计 w103(git 历史) 件2(ADR-0342):策略失活检查先行(不依赖判栈——失活局
        # 恰恰 strategy_id='' 无法判栈,不能被栈跳过逻辑连坐)。
        _dead = check_strategy_live_streak(all_rows)
        if _dead:
            lines.append(f'{rid}: [策略失活] ⚠ {"; ".join(_dead)}')
        # 段级检查生产接线(ADR-0479):栈无关([17] 族是口述判据非栈
        # 语义),任何栈的局都跑;只读报警,见
        # run_production_segment_checks docstring。
        lines.extend(run_production_segment_checks(all_rows))
        # 判栈:strategy_id 字段优先,退开局 reason 词表(逐行)
        sid = next((d.get('strategy_id') for d in all_rows
                    if d.get('strategy_id')), '')
        early_buys = [a for d in rows for a in (d.get('actions') or [])
                      if a.get('__type__') == 'BuyCard']
        early_reasons = {(a.get('reason') or '') for a in early_buys}
        if sid in ('line_v2', 'decision_v2'):
            stack = 'v2'
        elif sid and sid != 'default':
            lines.append(f'{rid}: [未知栈 {sid}] coldstart 跳过'
                         '(ADR-0245:新栈不盲跑)')
            continue
        elif early_reasons & _V2_REASONS:
            stack = 'v2'
        elif early_reasons & {'plan'}:
            stack = 'default'
        elif early_buys:
            stack = 'v2'   # 有买但 reason 全空(旧栈时代?);可判性另行声明
        else:
            stack = '?'    # 开局轮零买牌,无法判栈;跑检查无害(无买=无违规)
        if stack == 'default':
            lines.append(f'{rid}: [default 栈] coldstart 跳过(cw_plan '
                         '不辖 r368 门)')
            continue
        # 可判性:开局轮买牌 reason 缺失数(审查#2——✓ 必须真可判)
        untagged = sum(1 for a in early_buys
                       if not (a.get('reason') or '').strip())
        v = check_coldstart_seed_squander(rows)
        tag = f'[{stack} 栈]' if stack != 'v2' else '[v2]'
        if untagged and not v:
            lines.append(f'{rid}: {tag} coldstart ⊘ 无法判'
                         f'({untagged} 笔开局买未打标——旧数据;'
                         f'ba7ce6f3 后新局可判)')
            continue
        lines.append(f'{rid}: {tag} coldstart '
                     + ('✓ 无违规' if not v else f'⚠ {len(v)} 条'))
        for item in v:
            lines.append(f'    {item}')
    return lines

