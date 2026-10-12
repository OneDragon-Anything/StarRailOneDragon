# 废弃全局节点编号(node_ordinal)落地

## 完成前常规检查(各阶段完成判据引用本节,不复述)

- `uv run ruff check` 对本阶段改动文件全部通过;
- 本阶段直接受影响测试全量一次通过(`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`;
  涉 kernel/sim 核心域的阶段加跑 `uv run pytest sr-od-test -m "not slow"` 全量);
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交;
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号;提交后 `git show --stat` 复核入库面 = 申报面;
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

> **前置闸**:invest-effects-calc/T-8(人身意外险)已落地(设计 §1.4/§2.0 基线)——T-8 未落地前本文件任何阶段不得开工。

## 3.1 序列模块键原语(纯增)

**范围**:cw_node_schedule 增 `NodePos` 类型别名与 `sequence_next` 后继原语(设计 §2.1),模块头「现役口径」段补键原语句。**边界**:不改任何既有函数、不动任何调用方(`node_pos_of` 留待 3.2 随其消费方一并退役);零行为变化,纯增量。
**设计依据**:design.md §2.0/§2.1。
**文件面**:src/sr_od/application/currency_war/kernel/cw_node_schedule.py;sr-od-test 对应测试。
**依赖**:无(仅依赖 T-8 基线在役)。
**优先级建议**:0
**完成判据**:
- `sequence_next` 行为对照 design.md §2.1(位面内后继/跨位面/末位面 None/越界 ValueError/P3 `P3UnobservedError` 直查语义);
- 既有 `node_sequence_of`/`validate_sequences`/T-8 面(`resolve_plane_node_seqs`/`node_round_cap`)行为零变化(现役测试全绿);
- 完成前常规检查(本文首节)。
**验收凭据形式**:新增后继纯函数测试(默认表 + T-8 修饰表两口径);现役 kernel 测试子集一次通过。

## 3.2 节点域换键原子批

**范围**:节点身份表示 `(位面,轮)` 键化原子切换(设计 §2.2-§2.6/§2.8 快照恢复半)——`node_ord`→`node_pos`、`node_hist_ord`→`node_hist_pos`、`effective_node_ord`→`effective_node_pos`、推进/锚定/直定/查链/账本/sim 簿记全部换元组比较;`node_ordinal_of`/`_node_key_for_ord`/`_obs_node_ordinal`/sim `_ordinal_to_node`/`_node_ordinal`/`node_pos_of` 退役;`report_node_advance` 终局事件式;schema derivation 域 bump 5;快照/恢复换形。**边界**:不含 cw_screen_battle_wait(3.3)、不含 cw_anchor 锚行槽与 journal_query 死 helper(3.4);一次提交完成,无新旧表示并存窗口(R7 原子切换先例)。
**设计依据**:design.md §2.0/§2.2/§2.3/§2.4/§2.5/§2.6/§2.8(快照恢复半)/§2.10 取舍 2。
**文件面**:kernel/cw_game_state.py、kernel/cw_projection_audit.py、kernel/cw_node_schedule.py(删 `node_pos_of`)、kernel/cw_effect_inventory.py、kernel/cw_affix_effects.py、kernel/cw_screen_report/boss_briefing.py、kernel/cw_screen_report/plane_transition.py、kernel/cw_encounter_selection.py(注释)、sim/cw_sim_backend.py、operations/cw_screen/cw_screen_prep.py、operations/cw_screen/cw_screen_supply_node.py、operations/cw_screen/cw_screen_plane_transition.py、operations/cw_op/cw_op_settle_confirm.py(注释)、operations/cw_op/cw_pick_supply_action.py(注释);sr-od-test 对应测试(node advance/effect boundary/effect inventory/game state/supply advance/sim 全链域)。
**依赖**:3.1
**优先级建议**:0
**完成判据**:
- 行为对照 design.md §2.2(两态字段/原语处置表/终局锁)、§2.3(直定与查链)、§2.4(账本三语义)、§2.5(锚定写端)、§2.6(sim 簿记/进窗/局终腿)、§2.8(快照往返/旧档忽略);
- 默认环境 sim 全链回归与现役基线逐值同(design §2.11 锁 9);修饰局回归 = T-8 既有测试面全绿;
- 本批文件内 `node_ord`/`node_hist_ord`/`node_ordinal_of`/`_node_key_for_ord`/`node_pos_of`/`effective_node_ord`/`acquired_t`/`_entered_ord`/`_window_begun_ord` 符号零残留(grep 自证,入提交说明);
- 完成前常规检查(本文首节,含 kernel/sim 全量)。
**验收凭据形式**:design §2.11 锁 1-6/8/9 对应测试;sim 默认局全链一条(基线数字对照)。

## 3.3 operations 同式岛收口

**范围**:cw_screen_battle_wait 败局闩换键门(`SETTLE_DEFEAT_LATCH_MIN_POS=(2,5)`)、killed hp 邻接门换序位后继判定(`last_outcome_pos`)、结算单调门零改动核对;cw_plane_table `node_t_of` 契约注释重定域(规划数量语义,身份消费禁入)。**边界**:不含 killed 邻接门以外的任何结算读链语义;`node_t_of` 函数本体与策略侧消费零改动。
**设计依据**:design.md §2.7(含逐值等价证明)。
**文件面**:operations/cw_screen/cw_screen_battle_wait.py、kernel/cw_plane_table.py;sr-od-test 对应测试(settle/battle wait 域)。
**依赖**:无(可与 3.2 并行;建议排后只为本批文件面清晰,非硬依赖)。
**优先级建议**:1
**完成判据**:
- 败局闩与旧 t 门逐值对拍((1,10)/(2,1)/(2,4)/(2,5) 边界,含修饰局形态);killed 邻接门同位面相邻/跨位面后继成立、跨两节点不成立(design §2.11 锁 7);
- 结算单调门(元组比较)零改动核对申报入提交说明;
- 完成前常规检查(本文首节)。
**验收凭据形式**:design §2.11 锁 7 测试;边界值对拍表。

## 3.4 遥测与载体收口

**范围**:cw_anchor 锚行 `node_seq` 槽退役(AnchorEvent 字段/to_row 键/emit_anchor 形参与幂等键槽);journal_query `node_ordinal_of` 死 helper 删除;obs/cw_observation `_node_t` 死局部删除(:2268-2273)。**边界**:不含 defects 维度词表(零改动申报面);不含快照/恢复(3.2 已含)。
**设计依据**:design.md §2.8/§2.10 取舍 6/§2.7(死局部依据)。
**文件面**:kernel/cw_anchor.py、telemetry/journal_query.py、obs/cw_observation.py;sr-od-test 对应测试(anchor/journal 域)。
**依赖**:无。
**优先级建议**:1
**完成判据**:
- `emit_anchor`/`AnchorEvent` 形状对照 design §2.8;死 helper/死局部删除后相关测试全绿(全仓零调用方依据随提交说明复证);
- 完成前常规检查(本文首节)。
**验收凭据形式**:anchor 域测试;grep 零残留自证。

## 3.5 全仓清零核对

**范围**:对照 design §2.9 改清单与 §1.1 的 14 处扫描面,全仓 grep 核对清单——符号:`node_ord`/`node_hist_ord`/`effective_node_ord`/`node_ordinal_of`/`node_pos_of`/`_node_key_for_ord`/`_obs_node_ordinal`/`acquired_t`/`_entered_ord`/`_window_begun_ord`/`last_outcome_t`/`SETTLE_DEFEAT_LATCH_MIN_T`/`AnchorEvent` 的 `node_seq`/`_node_t`;式样:`*9`/`//9`/`%9` 身份语义命中。残留学面逐处判读:叙述性历史注记(模块头版本注/退役注)合法,活代码/活契约引用 = 打回对应阶段。**边界**:纯核对,零代码改动(发现残留开修复批处理完再回到本阶段验收)。
**设计依据**:design.md §1.1(14 处底册)/§2.9(改清单)/§1.3(公式拷贝清零目标)。
**文件面**:无(核对报告入提交说明/迭代 README 进度注)。
**依赖**:3.2、3.3、3.4
**优先级建议**:0
**完成判据**:核对单逐项「零残留 / 残留定性」两态闭合;`*9` 族扫描零身份语义命中(合法剩余 = 规划量注释/历史注,逐处列出)。
**验收凭据形式**:grep 输出对照表(随提交说明)。

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本。
**设计依据**:本文件「正本更新清单」节。
**文件面**:清单所列正本文档。
**依赖**:3.1-3.5 全部
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致(正本只写键表示现形,无编号投影残句;数值/序位常量只写常量名)。
**验收凭据形式**:文档对照 review。

## 正本更新清单

- game_state/node-domain.md:§1 身份键句(`node_ordinal` 公式 → NodePos 键表示)、§2 字段表(`node_ord`/`node_hist_ord` 行 → `node_pos`/`node_hist_pos`)、生效序读口节(名称与字典序语义) ← 3.2
- game_state/node-derivation.md:§3.2 身份键节(含 `AnchorEvent.node_seq` 引注句)、§3.3 原语签名与四分支比较语义(元组字典序)、终局语义(事件式声明)补节、§① 结论节符号名 ← 3.2/3.4
- game_state/fields.md:§3.2.1 node 域(derivation 域版本 5、`node_pos` 两态规格、`node_hist_pos`、快照/恢复值形) ← 3.2
- game_state/effect-domain.md:登记时点语义(`acquired_key`)、`advance_node` 键契约、去重键 `(run_id, 生效序位)` ← 3.2
- game_state/journal.md:§2-§3 载体规范(state 行 values `node_pos`/顶层 `node_hist_pos`/effects 行 `acquired_key` 形状、锚行 `node_seq` 槽退役注) ← 3.2/3.4
- sim/sim-design.md:§3.x 节点窗(`_window_begun_pos` 幂等键、`_enter_node_window` 键签名、局终声明消费腿、`_ordinal_to_node`/`_node_ordinal` 退役注) ← 3.2
- flow/action_ops.md:§1/§4.8 `node_advance` 行推导规则句(「超真值表总长」→「`sequence_next` 无后继 = 局终声明事件式」;`effective_node_ord` → `effective_node_pos`) ← 3.2
- screens/battle_wait.md:§6 killed 兜底链行(:65,时基 `node_t_of` → 序位后继判定)、§8 败局闩行(:78,`t ≥ SETTLE_DEFEAT_LATCH_MIN_T` → 序位 ≥ `SETTLE_DEFEAT_LATCH_MIN_POS`) ← 3.3
