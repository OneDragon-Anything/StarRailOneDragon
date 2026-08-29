"""判读 CLI(``python -m`` 入口,自 cw_telemetry 拆出,分包期6)。"""

from __future__ import annotations

from pathlib import Path

from sr_od.application.currency_war.kernel.cw_observe import (
    DEFAULT_REPLAY_DIR,
)
from sr_od.application.currency_war.sim.ledger_hooks import run_checks_on_replay
from sr_od.application.currency_war.telemetry.query import (
    _list_runs,
    _load_decisions_rounds,
    query_anomalies,
    query_economy,
    query_exec_events,
    query_exogenous,
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


def _cli_main() -> None:
    import argparse
    import sys
    if hasattr(sys.stdout, 'reconfigure'):   # GBK 控制台遇 ⚠/★ 崩
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(prog='cw_telemetry',
                                 description='货币战争遥测查询(复盘判读单一入口)')
    ap.add_argument('cmd', choices=['query', 'checks'])
    ap.add_argument('--run', default='', help='run_id(缺省=最近一局)')
    ap.add_argument('--recent', type=int, default=0, help='最近 N 局概览')
    ap.add_argument('--view', default='rounds',
                    choices=['rounds', 'supply', 'anomalies', 'tiers', 'planexec',
                             'hp', 'economy', 'exogenous', 'execevents',
                             'invest', 'conflicts', 'spend', 'all'])
    ap.add_argument('--replay-dir', default=str(DEFAULT_REPLAY_DIR))
    ap.add_argument('--sim-batch', default='', metavar='BATCH',
                    help='查 sim 批次账本:BATCH=批次目录名(缺省=最新;'
                         '根目录 sim_runs;"latest" 同缺省)。sim 语义差异:'
                         'board 系字段恒空(hp/tiers/rounds 视图自动回退'
                         '账本深度/核心维度);planexec 不适用(sim 无'
                         '执行层分离);ts=轮序号(生产 ISO 串)')
    args = ap.parse_args()
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
    runs = _list_runs(replay_dir)
    if args.cmd == 'checks':
        print('[checks] 生产遥测栈适配检查(coldstart)')
        print('\n'.join(run_checks_on_replay(replay_dir,
                                             args.recent or 5)))
        return
    if not runs:
        print('(无 replay 数据)')
        return
    if args.recent:
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

