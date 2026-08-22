"""Δ池快照(生成产物——勿手编)。

本文件由 tools/cw/gen_delta_pool_snapshot.py 生成;重跑:
    uv run python tools/cw/gen_delta_pool_snapshot.py
手改会被下次生成覆盖,且指纹校验(resolve_pool)会拒绝失配数据。
消费方:cw_sim.resolve_pool('snapshot')(CI/跨机可复现基准);
判断层勿直接 import 本模块。
"""
from __future__ import annotations

META: dict = {
  "depth_bucket_w": 3,
  "fingerprint": "942d3f79c09e2eb5",
  "note": "v2 只收可信标签行(2026-08-22 retrofix 后:死链历史 node_type 置 None 已丢弃计数);事故局物理排除(QUARANTINED_RUNS,r378b);跨策略版本混杂已知(一轮#10),过滤走 --runs 重生成",
  "quarantined_hits": [],
  "runs": {
    "run_20260822_170001": 4,
    "run_20260822_175526": 4,
    "run_20260822_194626": 6,
    "run_20260822_211037": 3,
    "run_20260822_214910": 4,
    "run_20260822_221109": 6
  },
  "runs_filter": "all",
  "sampler_version": 1,
  "skipped_lines": {},
  "source_dir": "D:\\code\\workspace\\StarRailOneDragon\\.debug\\temp\\currency_war\\replay",
  "unlabeled_dropped": 0
}

SNAPSHOT: dict = {"battle": {"6": [-11], "9": [-7, -11, 2, -13, -13, -13, 2, 2, -13], "12": [-8, -8, -11]}, "encounter": {"6": [-28], "9": [2], "12": [-10]}, "reward": {"6": [2, 2, 2, 2, 2]}}
