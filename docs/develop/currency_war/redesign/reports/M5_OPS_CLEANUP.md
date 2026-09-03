# M5 运维卫生批(收窄范围版)· 执行报告

> 执行时间:2026-09-02。范围:① `.debug/temp` 磁盘清理 ② as-built 文档清欠 3 项。
> 注释清扫(~250 处)本批不做,按任务书挂账后续。代码文件零触碰。

## 一、磁盘清理

### 1.1 结果总览

| 项 | 数字 |
|---|---|
| 删除文件数 | 52,664(零失败) |
| 释放字节 | **10,597,665,930(≈9.87 GB)** |
| `.debug/temp` 现存 | 10.7 GB → **0.90 GB** |
| 删除清单留档 | `M5_deletion_manifest.csv`(52,665 行,含每文件路径+字节数,与本报告同目录) |

注:任务书口径「temp ~22GB」是早前快照——2026-09-01 卫生批已回收过 13.6 GB(截图 6.54 + temp 7.06,见当日流水),本批起点的真实存量是 ~10.7 GB(temp)+1.0 GB(images 旧截图),已全部清完。

### 1.2 删除清单(按区域)

**A. `.debug/images/` 2026-09-01 之前的截图**:458 件,917,139,745 字节(≈0.87 GB)。保留 2026-09-01 之后的 92 件(204 MB)。

**B. `.debug/temp` 顶层旧临时目录**(约 180 MB):`_quarantine_20260830`(隔离区旧档)、`cw_drag_frames`(72 MB 拖拽帧样本)、`cw_red_sweep_b`、`perf_analysis`、`sim_universe`(104 MB,非 CW 旧调试目录)、`test_audit`、`w626_parked`、`w732_head`、`webp_conv`。

**C. `.debug/temp/currency_war/` 旧批次目录**(≈9.5 GB,释放大头),保留 `redesign/`、`replay/`、`match_archive/` 三个目录,其余全删。大户:
- `shots/` 3.12 GB(旧实机截图堆)
- `w963_comp_strength_audit/` 2.52 GB(含自带 .venv/uv_cache,纯环境副本)
- `w962_sim_hunt8/` 0.59 GB、`w958_sim_hunt5/` 0.55 GB、`w959/`+`w960/` 各 0.31 GB(sim hunt 批次运行数据)
- `w761_hunt_643300/` 0.26 GB、`w770_hunt_643700/` 0.27 GB、`w733_hunt_641000/` 0.26 GB(均含 git worktree 副本)
- `w676_p1_ab/` 57 MB、`w678`~`w957` 其余批次目录、`sim_runs/` 12 MB、`affix_shots/` 17 MB、`rebuild/`、`plaza/`、`shots_archive_20260830/`、`comp_selection/`、`m4_testinfra/`、`cw_dev/` 及 ~250 个小 wNNN 批次目录

**D. `.debug/temp/currency_war/` 顶层一次性脚本/输出**:`m4_*`(测试基建批中间产物,~660 KB)、`p47_adv_r2_check.py`、`_probe2.py`/`_probe3.py`、`calib_vuh_v1_*`、`w546_gen_count_ocr_fixture.py`。

**E. `.debug/temp` 顶层一次性脚本/诊断输出**(≈1.8 MB):约 110 个 `*_diag.txt`、`w695_fix_*.py`、`w716/w732/w834_*.patch`、`match_review_*.txt`、`cw_ab3_*.py/json`、`p42/p49_*.py` 等历史批次的散件。

### 1.3 保留面(硬约束核对,全部在位)

`.debug/progress/`(账本)、`.debug/temp/currency_war/redesign/`(当前迭代工作区,818 MB)、`.debug/temp/skill_feedback.md`、`.debug/temp/TODO.md`、`.debug/temp/zzz/`、`.dsh/` 未触碰。

**超出任务书保留清单、本批刻意保留的三处**(报告留档供裁决):
1. `currency_war/replay/`(135 MB)——按局存档与复盘评审数据,单局复盘协议的输入面,删了会断复盘链;
2. `currency_war/match_archive/`(15 KB)——同上;
3. `currency_war/` 顶层哨兵状态件(`cw_sentinel.lock/.pos`、`cw_early_stop.lock`、`cw_runs_gap.lock`、`l0_andon_hook.flag`、`launch_dead_hook.flag`、`rewatch.status`)与运维文档 `cw_处置SOP.md`、`cw_loop_alert.md`——实机哨兵组现役状态件。

删除前安全核验:清单逐行查保护面正则(progress/redesign/zzz/replay/match_archive/.dsh),命中 32 行均为误中(旧批次目录内的同名子目录、库名含 sentinel 的第三方库文件),非保护面真身——保护目录在枚举层已结构性排除,未入清单。

### 1.4 范围外备注(不在本批范围,供后续治理)

`.debug` 根下另有三大头不在 temp: `sr_od_mcp/` 4.6 GB、`gps/` 3.3 GB、`edge-profile/` 0.56 GB。其中 sr_od_mcp/gps 疑似运行时日志/遥测堆积,建议另开一批判口径后再清。

## 二、as-built 文档清欠 3 项(骨架层审计 §七 附录)

审计出处:`redesign/DESIGN_MANDATE_LAYER.md` §七「同步审计附录」。任务书三项=两项改措辞+一项指针化,对应附录建议同步项 ②③④(①M3 谓词收敛属另一处置分支,不在三项内)。

**核验结论:三项已由 2026-09-02 零时的骨架层文档卫生批落地**(当日流水「骨架层文档卫生批收账:四处全清」),本批逐项复核=条目编辑在位且与 IMPL_DESIGN 现行文本一致,无需新增改动:

| # | 审计条目 | 处置方式 | 落地位 | IMPL_DESIGN 权威锚点(本批复核) |
|---|---|---|---|---|
| ② | §3.4「板面收敛度异常 → 退化线内」行,原判「疑似孤儿」 | **指针化**(行保留+指针) | DESIGN_MANDATE_LAYER §3.4 该行【R-SYNC-W 2026-09 · 文档卫生批】标 | L382 executor 内置缺省表明文收录该退化规则——孤儿判定不成立,核读成立 |
| ③ | §3.4「sell_refund 读数缺失 → 按 1★ 全额退」行叙述陈旧 | **改措辞**(现行口径:R20-4 注册表真值 `_SELL_MULT`+R36-4 分面方向) | 同文件 §3.4 sell_refund 行 | L382 executor 缺省表 sell_refund 行同口径(R36-4 打陈旧标+分面) |
| ④ | §5.3 与 ADR-0463/0503 衔接叙述陈旧(「预期永不触发」论断) | **改措辞**(按现行姿态架构改述:升档器可触发) | 同文件 §5.3 该行【R-SYNC-W】标 | L130-150 R27-1/R28-1 升档器触发语义(λ 顾问相对分位触发/血线地板),「永不触发」确已被架构演进否定 |

闭环动作:已在 `DESIGN_MANDATE_LAYER.md` §七 附录加【R-M5 2026-09 · 复核确认】标,记录本批复核结论与指向本报告。

**如实申报一处口径出入**:审计附录条目落在设计件 DESIGN_MANDATE_LAYER(temp 内),不是 docs/ 树下的 as-built 正文;但条目内容、处置方式(两改措辞/一指针化)与任务书描述逐一吻合,判定为同一组清欠项。若编排者另有所指(docs/develop/currency_war/ 下另有 3 项),请指路出处,本批随即补做。

## 三、本批写入物

- `M5_OPS_CLEANUP.md`(本报告)
- `M5_deletion_manifest.csv`(删除留档,52,665 行)
- `DESIGN_MANDATE_LAYER.md` §七 附录新增一条 M5 复核标记(仅文档,不触代码)
