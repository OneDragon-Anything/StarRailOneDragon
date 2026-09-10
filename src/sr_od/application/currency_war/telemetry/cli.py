"""判读 CLI(``python -m`` 入口,自 cw_telemetry 拆出,分包期6)。"""

from __future__ import annotations

import json
from pathlib import Path

from sr_od.application.currency_war.kernel.cw_observe import (
    DEFAULT_REPLAY_DIR,
)
from sr_od.application.currency_war.sim.ledger_hooks import run_checks_on_replay
from sr_od.application.currency_war.telemetry import journal_query as _jq
from sr_od.application.currency_war.telemetry import match_archive as _arch
from sr_od.application.currency_war.telemetry.query import (
    _list_runs,
    _load_decisions_rounds,
    query_anomalies,
    query_economy,
    query_exec_events,
    query_exogenous,
    query_gold_flow,
    query_hp,
    query_invest_cards,
    query_obs_conflicts,
    query_plan_vs_exec,
    query_rounds,
    query_spend_ledger,
    query_supply,
    query_tiers,
    read_jsonl,
)

#: 新账专属视图(--source journal;旧 12 流无同名视图)
_JOURNAL_ONLY_VIEWS: frozenset[str] = frozenset({'gold', 'events', 'snapshot'})

#: 新账视图族全集(--source journal 的合法 --view)
_JOURNAL_VIEWS: frozenset[str] = frozenset(
    {'rounds', 'gold', 'hp', 'events', 'snapshot', 'all'})


def _len_rounds(archive: dict | None) -> int:
    """档案逐轮表行数(None 安全;assemble 回显用)。"""
    return len((archive or {}).get('rounds') or [])


def _match_view_lines(slice_dir: Path, segments: list[str],
                      view: str) -> list[tuple[str, list[str]]]:
    """档案切片目录 → 逐视图行(与 query 主路径同函数同参数,单源)。"""
    out: list[tuple[str, list[str]]] = []
    if view in ('rounds', 'all'):
        out.append(('[rounds]', [ln for s in segments
                                 for ln in query_rounds(slice_dir, s)]))
    if view in ('supply', 'all'):
        out.append(('[supply]', [ln for s in segments
                                 for ln in query_supply(slice_dir, s)]))
    if view in ('tiers', 'all'):
        out.append(('[tiers]', [ln for s in segments
                                for ln in query_tiers(slice_dir, s)]))
    if view in ('anomalies', 'all'):
        # 逐段与 query 主路径同构(空段同样打 ✓ 行,保证与 --run 逐字节一致)
        out.append(('[anomalies]',
                    [ln for s in segments
                     for ln in (query_anomalies(slice_dir, s)
                                or ['  ✓ 无异常标记'])]))
    if view in ('hp', 'all'):
        out.append(('[hp]', [ln for s in segments
                             for ln in query_hp(slice_dir, s)]))
    if view in ('economy', 'all'):
        out.append(('[economy]', [ln for s in segments
                                  for ln in query_economy(slice_dir, s)]))
    if view in ('goldflow', 'all'):
        out.append(('[goldflow]', [ln for s in segments
                                   for ln in query_gold_flow(slice_dir, s)]))
    return out


def _print_journal_views(rows: list[dict], run_id: str, view: str) -> None:
    """新账视图族输出(view ∈ _JOURNAL_VIEWS;all = 全族)。"""
    views = {'rounds': _jq.view_rounds, 'gold': _jq.view_gold,
             'hp': _jq.view_hp, 'events': _jq.view_events,
             'snapshot': _jq.view_snapshot}
    for fn in (views.values() if view == 'all' else [views[view]]):
        for ln in fn(rows, run_id):
            print(ln)


def _journal_source(args, replay_dir: Path) -> None:
    """``--source journal`` 读面(query 专属;设计 §3.6.2 判读 CLI 行:新视图族
    从账本按行读 + 行间差分,零重放;与旧流读面并存至 M5)。"""
    rows = _jq.read_journal(replay_dir)
    if not rows:
        print(f'(无统一 state 新账: {_jq.journal_path(replay_dir)} 不存在或为空'
              '——新账由影子开关 config.state_journal 接通(缺省关),'
              '开启后与旧流并行写)')
        return
    if args.recent:
        print(f"—— 最近 {args.recent} 局(新账 {_jq.JOURNAL_REL})——")
        for rid in _jq.journal_runs(rows)[-args.recent:]:
            seg = _jq.rows_of(rows, rid)
            last = seg[-1]
            vals = _jq.state_values(last)
            node = vals.get('node')
            node_s = (f"P{node.get('plane')}r{node.get('round_num')}"
                      if isinstance(node, dict) else '?')
            print(f"{rid}: 行={len(seg)} 节点={node_s}"
                  f" | 末ts={_jq.row_ts(last)}"
                  f" hp={vals.get('hp', '?')} gold={vals.get('gold', '?')}")
        return
    if args.match:
        # --match + 新账:档案切片已含 state/journal.jsonl(v12 装配器),
        # 物化后读同一相对路径(与 --run 同一读面实现,单一源)
        archive = _arch.load_archive(replay_dir, args.match)
        if archive is None:
            print(f'(档案不存在: {args.match}——先 assemble --game {args.match})')
            return
        import atexit
        import shutil
        import tempfile
        tmp_root = Path(tempfile.mkdtemp(prefix='cw_match_j_'))
        atexit.register(shutil.rmtree, tmp_root, ignore_errors=True)
        _arch.materialize_slice(archive, tmp_root)
        jrows = _jq.read_journal(tmp_root)
        segs = [s.get('run_id') for s in (archive.get('segments') or [])]
        print(f"=== {archive.get('game_id')} (新账视图) ==="
              f" [{' + '.join(segs)}] 行={len(jrows)}")
        if not jrows:
            print('(档案切片无新账行——装配时点新账不在产物目录(影子未开);'
                  '需补切片可 assemble --game 重装配)')
            return
        _print_journal_views(jrows, '', args.view)
        return
    rid = args.run or (_jq.journal_runs(rows) or [''])[-1]
    if not rid:
        print('(新账行缺 run_id——无 run 归属行可读)')
        return
    print(f"=== {rid} (新账 {_jq.JOURNAL_REL}) ===")
    _print_journal_views(rows, rid, args.view)


def _cli_main() -> None:
    import argparse
    import sys
    if hasattr(sys.stdout, 'reconfigure'):   # GBK 控制台遇 ⚠/★ 崩
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(prog='cw_telemetry',
                                 description='货币战争遥测查询(复盘判读单一入口)')
    ap.add_argument('cmd', choices=['query', 'checks', 'assemble'])
    ap.add_argument('--run', default='', help='run_id(缺省=最近一局)')
    ap.add_argument('--recent', type=int, default=0, help='最近 N 局概览'
                    '(matches/index.jsonl 存在时改读档案索引)')
    ap.add_argument('--match', default='', metavar='GAME_ID',
                    help='直读按局档案(g_*;视图自档案切片计算,与 --run 聚合同源)')
    ap.add_argument('--game', default='', metavar='GAME_ID',
                    help='assemble 子命令:点名装配指定局(补装配/崩溃局兜底,'
                         '绕过水位线;缺省=只装水位线后的新局)')
    ap.add_argument('--view', default='rounds',
                    choices=['rounds', 'supply', 'anomalies', 'tiers', 'planexec',
                             'hp', 'economy', 'goldflow', 'exogenous', 'execevents',
                             'invest', 'conflicts', 'spend', 'all',
                             'gold', 'events', 'snapshot'])
    ap.add_argument('--source', default='old', choices=['old', 'journal'],
                    help='query 读面选择:old=旧 12 流视图(缺省,现状不变);'
                         'journal=统一 state 新账视图族(state/journal.jsonl'
                         ' 行行自足,宽容读取;并存期并存面,设计 §3.6.2 判读'
                         ' CLI 行——旧视图只读保留至 M5)')
    ap.add_argument('--replay-dir', default=str(DEFAULT_REPLAY_DIR))
    ap.add_argument('--sim-batch', default='', metavar='BATCH',
                    help='查 sim 批次账本:BATCH=批次目录名(缺省=最新;'
                         '根 telemetry/sim;"latest" 同缺省)。sim 语义差异:'
                         'board 系字段恒空(hp/tiers/rounds 视图自动回退'
                         '账本深度/核心维度);planexec 不适用(sim 无'
                         '执行层分离);ts=轮序号(生产 ISO 串)')
    args = ap.parse_args()
    # 读面配对校验(显式拒绝优于静默回落:静默 = 判读人以为在读新账实际在读旧流)
    if args.cmd == 'query' and args.source == 'journal':
        if args.view not in _JOURNAL_VIEWS:
            ap.error(f'--source journal 不支持视图 {args.view}'
                     f'(新账族 = {sorted(_JOURNAL_VIEWS)})')
    elif args.view in _JOURNAL_ONLY_VIEWS:
        ap.error(f'--view {args.view} 属新账视图族,须搭配 --source journal')
    if args.source == 'journal' and args.cmd != 'query':
        ap.error('--source journal 只辖 query 读面(checks/assemble 单路径;'
                 '装配切片面已自动含新账)')
    if args.sim_batch:
        # ⑤:sim 批次便捷入口——批次目录结构与生产 replay 同构
        # ({decisions,outcomes,shop_snapshots}.jsonl),视图零分叉
        from sr_od.application.currency_war.sim.runner import SIM_RUNS_DIR
        if args.sim_batch == 'latest':
            batches = sorted(p for p in SIM_RUNS_DIR.iterdir()
                             if p.is_dir())
            if not batches:
                print('(无 sim 批次——先跑 simulate_p1_batch)')
                return
            replay_dir = batches[-1]
        else:
            replay_dir = SIM_RUNS_DIR / args.sim_batch
        print(f"[sim 批次] {replay_dir.name}")
    else:
        replay_dir = Path(args.replay_dir)
    if args.source == 'journal':
        # 新账读面(query 专属;checks/assemble 已在配对校验拦下)
        _journal_source(args, replay_dir)
        return
    runs = _list_runs(replay_dir)
    if args.cmd == 'checks':
        print('[checks] 生产遥测栈适配检查(coldstart)')
        print('\n'.join(run_checks_on_replay(replay_dir,
                                             args.recent or 5)))
        return
    if args.cmd == 'assemble':
        # 按局存档装配(离线兜底入口):缺省=水位线后的新局(与局终钩子
        # 同入口);--game 点名 = 补装配/崩溃局,不问水位线
        if args.game:
            a = _arch.assemble_game(replay_dir, args.game)
            print(f"[assemble] {args.game}: "
                  + ('装配完成 ' f"({_len_rounds(a)} 轮)"
                     if a else '游戏不存在(检查 game_id,--recent 看索引)'))
        else:
            done = _arch.assemble_pending(replay_dir)
            print(f"[assemble] 新装配 {len(done)} 局: {', '.join(done) or '(无)'}")
        return
    if not runs:
        print('(无 replay 数据)')
        return
    if args.recent:
        idx = _arch.matches_dir(replay_dir) / 'index.jsonl'
        if idx.exists() and not args.run and not args.match:
            # 概览改读档案索引(一行一局摘要,视图零计算)
            entries = [json.loads(ln) for ln in
                       idx.open('r', encoding='utf-8') if ln.strip()]
            print(f"—— 最近 {args.recent} 局(档案索引)——")
            for e in entries[-args.recent:]:
                seg_s = '+'.join(e.get('segments') or [])
                abn = ' abandoned' if e.get('abandoned') else ''
                print(f"{e.get('game_id')} [{seg_s}] {e.get('start_ts')}"
                      f" → P{e.get('plane_reached')}r{e.get('rounds_survived')}"
                      f" result={e.get('result')}{abn}"
                      f" hp={e.get('final_hp')} 轮={e.get('n_rounds')}"
                      f" 败场={e.get('n_loss_nodes')}")
            return
        print(f"—— 最近 {args.recent} 局 ——")
        for rid in runs[-args.recent:]:
            best = _load_decisions_rounds(replay_dir, rid)
            abn = query_anomalies(replay_dir, rid)
            outs = read_jsonl(replay_dir / 'outcomes.jsonl')
            mine = [o for o in outs if o.get('run_id') == rid]
            deepest = max(((o.get('plane') or 1, o.get('round_num') or 1) for o in mine),
                          default=(1, 1))
            last = mine[-1] if mine else {}
            print(f"{rid}: P{deepest[0]}r{deepest[1]} | 决策{len(best)}轮 | 异常 {len(abn)} 条"
                  f" | 末态 hp={last.get('hp_after')} comp={last.get('comp_tag')}")
        return
    rid = args.run or runs[-1]
    if args.match:
        # --match 直读按局档案:切片物化到临时目录后走同一套视图函数
        # (与 --run 聚合输出逐字节一致,单一源不建第二套视图实现)
        archive = _arch.load_archive(replay_dir, args.match)
        if archive is None:
            print(f'(档案不存在: {args.match}——先 assemble --game {args.match})')
            return
        import atexit
        import shutil
        import tempfile
        tmp_root = Path(tempfile.mkdtemp(prefix='cw_match_'))
        atexit.register(shutil.rmtree, tmp_root, ignore_errors=True)
        _arch.materialize_slice(archive, tmp_root)
        segs = [s.get('run_id') for s in (archive.get('segments') or [])]
        endgame = archive.get('endgame') or {}
        print(f"=== {archive.get('game_id')} ==="
              f" [{' + '.join(segs)}]"
              f" {archive.get('start_ts')} → {archive.get('end_ts')}"
              f" result={endgame.get('result')}"
              f"{'(abandoned)' if endgame.get('abandoned') else ''}")
        # 行为观测计数(v7 档案字段):None=无计数流(旧局/计数流缺失,
        # 数据缺失可区分);空 dict=真实零计数
        _ct = archive.get('cw4_counters')
        if _ct is None:
            print('[cw4_counters] (无计数流:本批改动前落的局/流缺失)')
        else:
            print('[cw4_counters] ' + (', '.join(
                f'{k}={v}' for k, v in sorted(_ct.items())) or '(零计数)'))
        for view_name, seg in _match_view_lines(tmp_root, segs, args.view):
            print(view_name)
            print('\n'.join(seg))
        return
    print(f"=== {rid} ===")
    if args.view in ('rounds', 'all'):
        print('[rounds]')
        print('\n'.join(query_rounds(replay_dir, rid)))
    if args.view in ('supply', 'all'):
        print('[supply]')
        print('\n'.join(query_supply(replay_dir, rid)))
    if args.view in ('tiers', 'all'):
        print('[tiers]')
        print('\n'.join(query_tiers(replay_dir, rid)))
    if args.view in ('planexec', 'all'):
        print('[planexec]')
        print('\n'.join(query_plan_vs_exec(replay_dir, rid)))
    if args.view in ('anomalies', 'all'):
        print('[anomalies]')
        abn = query_anomalies(replay_dir, rid)
        print('\n'.join(abn) if abn else '  ✓ 无异常标记')
    if args.view in ('hp', 'all'):
        print('[hp]')
        print('\n'.join(query_hp(replay_dir, rid)))
    if args.view in ('economy', 'all'):
        print('[economy]')
        print('\n'.join(query_economy(replay_dir, rid)))
    if args.view in ('goldflow', 'all'):
        print('[goldflow](模态期金去向对账: economy 残差 − modality 逐笔 = 未解释;⚠=未挂钩金变动)')
        print('\n'.join(query_gold_flow(replay_dir, rid)))
    # 迁移审计 w315(git 历史)(审计 G3)四条旁路流视图
    if args.view in ('exogenous', 'all'):
        print('[exogenous]')
        print('\n'.join(query_exogenous(replay_dir, rid)))
    if args.view in ('execevents', 'all'):
        print('[execevents]')
        print('\n'.join(query_exec_events(replay_dir, rid)))
    if args.view in ('invest', 'all'):
        print('[invest]')
        print('\n'.join(query_invest_cards(replay_dir, rid)))
    if args.view in ('conflicts', 'all'):
        print('[conflicts](跨局采集,--run 不生效)')
        print('\n'.join(query_obs_conflicts(replay_dir, rid)))
    if args.view in ('spend', 'all'):
        print('[spend](购买单元金账:三态计数+大额失配;obs_conflicts 跨局采集,冲突行按 ts 邻近窗消歧)')
        print('\n'.join(query_spend_ledger(replay_dir, rid)))



if __name__ == '__main__':
    _cli_main()

