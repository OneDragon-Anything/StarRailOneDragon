"""判读 CLI(``python -m`` 入口,自 cw_telemetry 拆出,分包期6)。

W3(R5 单源直迁第三波,正本 = docs/develop/currency_war/game_state/
r5-migration-plan.md §2 W3):``--source`` 双读面拆除——旧 12 流视图族随
流写入端退役(删除波 1)一并删除,journal(\\*:读面 = journal_query)成为
``query`` 唯一读面;``checks`` 子命令(sim/ledger_hooks 读生产旧流的检查
器)同批退役;``--sim-batch`` 入口随旧视图删除(sim 批目录无 journal,
批判读桥期 = skills 侧 cw_batch_stats,journal 侧 sim 视图候 W6 sim 切
统一容器批)。``assemble`` 按局档案装配入口保留(切片含 journal,v12+)。
"""

from __future__ import annotations

from pathlib import Path

from sr_od.application.currency_war.kernel.cw_observe import (
    DEFAULT_REPLAY_DIR,
)
from sr_od.application.currency_war.telemetry import journal_query as _jq
from sr_od.application.currency_war.telemetry import match_archive as _arch

#: 新账视图族全集(``query`` 的合法 --view;all = 全族)
_JOURNAL_VIEWS: frozenset[str] = frozenset(
    {'rounds', 'gold', 'hp', 'events', 'snapshot', 'final', 'all'})


def _len_rounds(archive: dict | None) -> int:
    """档案逐轮表行数(None 安全;assemble 回显用)。"""
    return len((archive or {}).get('rounds') or [])


def _print_journal_views(rows: list[dict], run_id: str, view: str) -> None:
    """新账视图族输出(view ∈ _JOURNAL_VIEWS;all = 全族)。"""
    views = {'rounds': _jq.view_rounds, 'gold': _jq.view_gold,
             'hp': _jq.view_hp, 'events': _jq.view_events,
             'snapshot': _jq.view_snapshot, 'final': _jq.view_match_final}
    for fn in (views.values() if view == 'all' else [views[view]]):
        for ln in fn(rows, run_id):
            print(ln)


def _query_source(args, replay_dir: Path) -> None:
    """``query`` 唯一读面 = 统一 state 新账(journal 行行自足,宽容读取;
    设计 §3.6.2 判读 CLI 行:从账本按行读 + 行间差分,零重放)。"""
    rows = _jq.read_journal(replay_dir)
    if not rows:
        print(f'(无统一 state 新账: {_jq.journal_path(replay_dir)} 不存在或为空'
              '——journal 无条件常开(R5 W1/ADR-0634),空 = 本目录无对局产物'
              '或账本未随局产生)')
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
        # str 守卫(F2,R3.1 落地审):畸形/未来格式档案的段条目缺 run_id 时
        # join 不 TypeError——降级显示 None(判读可见档案畸形),禁静默丢段
        segs = [str(s.get('run_id')) for s in (archive.get('segments') or [])]
        print(f"=== {archive.get('game_id')} (新账视图) ==="
              f" [{' + '.join(segs)}] 行={len(jrows)}")
        if not jrows:
            print('(档案切片无新账行——装配时点账本不在产物目录;'
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
    ap.add_argument('cmd', choices=['query', 'assemble'])
    ap.add_argument('--run', default='', help='run_id(缺省=最近一局)')
    ap.add_argument('--recent', type=int, default=0,
                    help='最近 N 局概览(新账段概览)')
    ap.add_argument('--match', default='', metavar='GAME_ID',
                    help='直读按局档案(g_*;新账视图自档案切片读,'
                         '与 --run 同一读面实现)')
    ap.add_argument('--game', default='', metavar='GAME_ID',
                    help='assemble 子命令:点名装配指定局(补装配/崩溃局兜底,'
                         '绕过水位线;缺省=只装水位线后的新局)')
    ap.add_argument('--view', default='rounds',
                    choices=sorted(_JOURNAL_VIEWS),
                    help='新账视图族(W3 起唯一读面)')
    ap.add_argument('--replay-dir', default=str(DEFAULT_REPLAY_DIR))
    args = ap.parse_args()
    replay_dir = Path(args.replay_dir)
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
    _query_source(args, replay_dir)


if __name__ == '__main__':
    _cli_main()
