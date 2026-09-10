"""局后钩子(自 cw_telemetry 拆出,分包期6)——已随旧流退役收缩为桩模块。

删除波 1(用户 2026-09-10 直迁裁定)退役本模块的 runs 流两个写入端:
①崩溃兜底回填(build_recovered_summary + recover_dangling_run_summaries,
写 runs 行);②Δ池局终自动再生触发(_regenerate_delta_pool_after_run,挂
runs 行写入时点;池再生本体 = sim/cw_delta_pool_gen.regenerate_snapshot,
改手动/sim 批入口)。

W3(R5 单源直迁第三波,正本 = r5-migration-plan.md §2 W3):读侧检查族
(check_summary_write_path_coverage / run_checks_on_replay / merge_round_rows /
run_production_segment_checks)随其唯一消费面——判读 CLI ``checks`` 子命令——
同批退役:全部生产旧流读源(decisions/outcomes/runs)已于删除波 1 停写,
检查器对新局恒空/⊘(读死数据),判读走 journal 新账视图族(telemetry/
journal_query);段级检查器的 sim 账本活体 = sim/checks/(吃 sim 引擎自写
账本,归 W6 sim 切统一容器批统一处置)。

唯一保留 = :func:`recover_dangling_run_summaries` no-op 桩(防外部残留
调用炸栈,恒返回空表)。
"""

from __future__ import annotations

from pathlib import Path


def recover_dangling_run_summaries(replay_dir: Path | str | None = None) -> list[str]:
    """已随 runs 流写入端退役(删除波 1)——no-op 兼容桩。

    旧语义 = 补齐 runs.jsonl 缺行(start_run 每局起点调;写 runs 行)。
    start_run 调用点已同批删除;本桩仅为防外部残留调用炸栈,恒返回空表。
    """
    del replay_dir
    return []
