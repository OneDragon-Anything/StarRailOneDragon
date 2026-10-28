# executor-gold-delta-retire 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 直接受影响测试全量一次通过（sim 子集 + operations 子集 + tools，`-m "not slow"`）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段名；提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 执行缝金差链退役 + 渲染器兼容 + 对账生产者补齐

**范围**：①`prep_actions.py` 删金差链五件 + 文本面六触点 + 同源死代码（`_pre_bench`/`_bench_occupied_count`）+ `last_launch_ok` 冗余赋值收编 + `Unit` unused import（design §2.1 表）；②`tools/cw/replay_to_md.py` 两处 extra 排除表（:1010/:1534，缺一不可）追加 `'gold_delta'`；③**账实金对账生产者补齐**（design §2.3：备战帧 gold 读点账实对比 → `obs_conflict('gold_delta', 账面, 实读)` → 复活 `cw_observe.py:224` 分级告警，阈值复用 `GOLD_DELTA_ALARM_GAP`）；④测试面三迁移点（design/终审实证）：`test_replay_render.py:376` 断言翻转（gold_delta 不显影）+ 旧 journal 兼容正例、`test_prep_action_ops.py:367/:1063` last_gold_delta 断言删除、`:354` docstring 同步。边界：LogicOutcome 契约不动、容器金账写点不动、cw_exec_state._advance_gold 与 shop_session.apply_gold_delta 核查分账不混本批、观察侧告警门本体不动（只补生产者）。
**设计依据**：design.md §2.1-§2.4。
**文件面**：`src/sr_od/application/currency_war/prep_actions.py`；`src/sr_od/application/currency_war/kernel/cw_observe.py`（生产者如落在告警门旁）或 gold 观察读点所在文件；`tools/cw/replay_to_md.py`；测试仓三迁移文件。
**依赖**：无。
**优先级建议**：0
**完成判据**：
- sim 驱动整局收口（`terminal=death|p3_enter`，fail_streak<5）；
- 新局渲染：回执 extra 无 `gold_delta` 键；旧 journal（`.debug/currency_war/telemetry/live/state/journal.jsonl`，44MB，含 applied+gold_delta 双键）重渲染零异常且字样零显影；
- 账实对账生产者可达：fixture/驱动局可构造 gap>10 场景 → `[cw!][alarm][gold_delta]` 行出现；
- grep 清零（范围 = src/ + tools/ + sr-od-test/）：`_executed_gold_delta`/`_pre_sell_target_bc`/`last_gold_delta` 零命中；回执域 `gold_delta` 键清零（豁免面预填 = design §4 清单，逐命中归属）；
- 全量测试过（sr-od-test 相关子集）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：双局渲染对照 + grep 清零记录（含豁免面归属表）+ 告警行样本 + 测试名清单。

## 3.2 正本更新 + 分账登记

**范围**：①`game_state/fields.md` 回执契约节核对（extra 语义不含金差）；②`game_state/journal.md` 回执键历史集核对（gold_delta 键退役）；③`game_state/retirement.md` 登记金差证据分支退役（−2 倒挂事故架构收尾）；④`screens/shop.md`/`logic-updates/sell-bench.md`/`logic-updates/level-up.md`/`game_state/action-logic-state.md`/`logic-updates/prep-executor-actions.md`/`logic-updates/op-effects.md` 金差表述清退（attack 点名六文件）；⑤账本登记分账三项（design §2.4：_advance_gold 核查 / shop_session.apply_gold_delta 归属 / write_logic docstring produced_by 申报修正）；⑥README 进度收尾。闭合法 = 退役符号正本树全域 grep 逐命中归属（obs 告警门豁免列出）+ 语义闭清（金差/执行点金差表述逐处核对）。
**设计依据**：design.md §0/§2.3/§2.4。
**文件面**：`docs/develop/sr_od/application/currency_war/game_state/fields.md`；`docs/develop/sr_od/application/currency_war/game_state/journal.md`；`docs/develop/sr_od/application/currency_war/game_state/retirement.md`；`docs/develop/sr_od/application/currency_war/game_state/action-logic-state.md`；`docs/develop/sr_od/application/currency_war/game_state/logic-updates/{close-shop.md 已清,prep-executor-actions.md,op-effects.md,level-up.md,sell-bench.md}`；`docs/develop/sr_od/application/currency_war/screens/shop.md`；本迭代 README。
**依赖**：3.1。
**优先级建议**：0
**完成判据**：退役符号正本树 grep 逐命中归属清零（obs 告警门豁免列出）+ 语义闭清记录；文档与代码现状一致；README 终态。
**验收凭据形式**：grep 记录 + 文档对照 review。

## 正本更新清单

- `game_state/fields.md` 回执契约节核对 ← 3.2
- `game_state/journal.md` 回执键历史集核对 ← 3.2
- `game_state/retirement.md` 金差证据分支退役登记 ← 3.2
- `game_state/action-logic-state.md` / `logic-updates/{prep-executor-actions,op-effects,level-up,sell-bench}.md` 金差表述清退 ← 3.2
- `screens/shop.md` 核对 ← 3.2
