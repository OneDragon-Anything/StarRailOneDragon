"""货币战争 · Δ池快照生成器 CLI 壳(生成核心在 src,ADR-0344)。

核心逻辑(regenerate_snapshot / build_pool / 写目标白名单与
sim_runs 防自中毒守卫)位于
src/sr_od/application/currency_war/cw_delta_pool_gen.py——
实机局终自动再生管线(cw_telemetry 局终钩子)与本 CLI 共用同一
入口与防线(「生成器是池的唯一入口」随核心走)。

用法: uv run python tools/cw/gen_delta_pool_snapshot.py
      [--runs id1,id2] [--export-json PATH]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))

from sr_od.application.currency_war.cw_delta_pool_gen import (  # noqa: E402
    regenerate_snapshot,
)


def main() -> None:
    ap = argparse.ArgumentParser(
        description='Δ池快照生成器(CLI 壳;核心 cw_delta_pool_gen)')
    ap.add_argument('--runs', default='',
                    help='逗号分隔 run_id 白名单(默认全部)')
    ap.add_argument('--export-json', default='',
                    help='另存 JSON 快照(cw_sim.resolve_pool(Path) 重放用)')
    args = ap.parse_args()
    runs_filter = {r.strip() for r in args.runs.split(',') if r.strip()} or None
    regenerate_snapshot(runs_filter=runs_filter,
                        export_json=args.export_json or None)


if __name__ == '__main__':
    main()
