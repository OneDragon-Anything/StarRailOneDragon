"""Δ池快照(生成产物——勿手编)。

本文件由 tools/cw/gen_delta_pool_snapshot.py 生成;重跑:
    uv run python tools/cw/gen_delta_pool_snapshot.py
手改会被下次生成覆盖,且指纹校验(resolve_pool)会拒绝失配数据。
消费方:cw_sim.resolve_pool('snapshot')(CI/跨机可复现基准);
判断层勿直接 import 本模块。
"""
from __future__ import annotations

META: dict = {
  "battle_rung": {
    "0": {
      "killed_known": 31,
      "killed_unknown": 9,
      "mean": -11.75,
      "n": 40,
      "sign_disagree": 0,
      "win_delta": 0.0,
      "win_killed": 0.0
    },
    "1": {
      "killed_known": 24,
      "killed_unknown": 7,
      "mean": -5.9,
      "n": 31,
      "sign_disagree": 0,
      "win_delta": 0.4194,
      "win_killed": 0.5
    },
    "2": {
      "killed_known": 6,
      "killed_unknown": 3,
      "mean": -7.44,
      "n": 9,
      "sign_disagree": 0,
      "win_delta": 0.4444,
      "win_killed": 0.6667
    }
  },
  "bucket_poverty": [
    "battle:桶2(n=9)",
    "battle:桶3(缺)",
    "battle:桶4(缺)",
    "boss:桶9(n=2)",
    "boss:桶12(n=7)",
    "boss:桶15(n=8)",
    "encounter:桶6(n=1)",
    "encounter:桶9(n=7)",
    "encounter:桶15(n=3)",
    "reward:桶9(n=7)",
    "reward:桶15(n=3)"
  ],
  "depth_bucket_w": 3,
  "fingerprint": "886f8a39c87c8c6b",
  "note": "v2 只收可信标签行(2026-08-22 retrofix 后:死链历史 node_type 置 None 已丢弃计数);事故局物理排除(QUARANTINED_RUNS,r378b);跨策略版本混杂已知(一轮#10),过滤走 --runs 重生成;v3(ADR-0279,批⑬)battle 桶键 depth→rung(成型度一维分桶),encounter/boss 维持 depth 桶;v4(ADR-0306)胜判定权威口径=killed(结算屏 extras;Δ 为派生量,异号实证 0/61 killed 已知行——0305 的「3/9 异号」系 tier×core 与 rung 两分桶错位对照的伪影),META 逐桶双口径胜率+桶贫困披露+语料行数账",
  "quarantined_hits": [],
  "runs": {
    "run_20260822_170001": 4,
    "run_20260822_175526": 4,
    "run_20260822_194626": 6,
    "run_20260822_211037": 3,
    "run_20260822_214910": 4,
    "run_20260822_221109": 6,
    "run_20260822_230241": 2,
    "run_20260823_033757": 8,
    "run_20260823_041711": 8,
    "run_20260823_044908": 8,
    "run_20260823_052153": 9,
    "run_20260823_082152": 8,
    "run_20260823_092218": 8,
    "run_20260823_095944": 11,
    "run_20260823_105348": 14,
    "run_20260823_120538": 8,
    "run_20260823_124802": 10,
    "run_20260823_135725": 8,
    "run_20260823_145233": 3,
    "run_20260823_151050": 1,
    "run_20260823_151913": 1,
    "run_20260823_154910": 7,
    "run_20260823_162622": 7,
    "run_20260823_165501": 1,
    "run_20260823_171444": 11,
    "run_20260823_180955": 8,
    "run_20260823_184237": 8,
    "run_20260823_192617": 8,
    "run_20260823_200621": 7
  },
  "runs_filter": "all",
  "sampler_version": 5,
  "skipped_lines": {},
  "source_dir": "D:\\code\\workspace\\StarRailOneDragon\\.debug\\temp\\currency_war\\replay",
  "source_rows": {
    "decisions.jsonl": 1921,
    "outcomes.jsonl": 191
  },
  "unlabeled_dropped": 0
}

SNAPSHOT: dict = {"battle": {"0": [-11, -8, -13, -13, -13, -13, -13, -10, -13, -6, -10, -13, -13, -13, -13, -13, -4, -4, -11, -13, -13, -13, -13, -13, -13, -13, -9, -13, -13, -9, -13, -11, -13, -13, -13, -13, -13, -13, -13, -13], "1": [-7, -11, 2, -8, -11, 2, 2, 2, -5, -8, -11, 0, -12, 2, 2, -5, -17, -15, -21, -11, -19, -6, 2, 2, 2, 2, -4, -18, -16, 0, 2], "2": [2, 2, -6, 2, 2, -21, -14, -15, -19]}, "boss": {"9": [-13, -18], "12": [-21, -34, -19, -13, -30, -22, -33], "15": [-36, -34, -14, 2, -26, -24, -14, -33]}, "encounter": {"6": [-28], "9": [2, -28, -9, -8, -28, -28, -26], "12": [-10, -26, -24, -24, -28, -10, -22, -28, -9, -6, -10], "15": [-28, -9, -18]}, "reward": {"6": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2], "9": [2, 2, 2, 2, 2, 2, 2], "12": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2], "15": [2, 2, 2]}}
