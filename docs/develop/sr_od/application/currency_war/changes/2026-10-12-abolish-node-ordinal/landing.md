# 废弃全局节点编号(node_ordinal)落地

> **行号基准**:本文件 file:line = T-8 落地后工作树(2026-10-12);行号漂移按符号名定位。

## 完成前常规检查(各阶段完成判据引用本节,不复述)

- `uv run ruff check` 对本阶段改动文件全部通过;
- 本阶段直接受影响测试全量一次通过(`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`;
  涉 kernel/sim 核心域的阶段加跑 `uv run pytest sr-od-test -m "not slow"` 全量);
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交;
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号;提交后 `git show --stat` 复核入库面 = 申报面;
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

> **前置闸:已满足**——invest-effects-calc/T-8 已落地(2026-10-12 树核验:场字段/修饰层/killed 门删除全部在位,含裁决点 7 前半;设计 §2.0 落地态对齐申报三处)。落地批开工前复核 T-8 收尾状态(正本更新清零/账本终态)即可。

## 3.1 序列模块键原语(纯增)

**范围**:cw_node_schedule 增 `NodePos` 类型别名与 `sequence_next` 后继原语(设计 §2.1),模块头「现役口径」段补键原语句。**边界**:不改任何既有函数、不动任何调用方(`node_pos_of` 留待 3.2 随其消费方一并退役);零行为变化,纯增量。
**设计依据**:design.md §2.0/§2.1。
**文件面**:src/sr_od/application/currency_war/kernel/cw_node_schedule.py;sr-od-test 对应测试。
**依赖**:无(仅依赖 T-8 基线在役)。
**优先级建议**:0
**完成判据**:
- `sequence_next` 四态契约对照 design.md §2.1(位面内后继/跨位面/pos 位面无表 None/位面末下位面无表 None/越界 ValueError);
- 既有 `node_sequence_of`/`validate_sequences`/T-8 面(`resolve_plane_node_seqs`/`node_round_cap`)行为零变化(现役测试全绿);
- 完成前常规检查(本文首节)。
**验收凭据形式**:新增后继纯函数测试(默认表 + T-8 修饰表两口径 + P3 边界);现役 kernel 测试子集一次通过。

## 3.2 节点域换键原子批

**范围**:节点身份表示 `(位面,轮)` 键化原子切换(设计 §2.2-§2.6/§2.8 快照恢复半)——`node_ord`→`node_pos`、`node_hist_ord`→`node_hist_pos`、`effective_node_ord`→`effective_node_pos`、推进/锚定/直定/查链/账本/sim 簿记全部换元组比较;`node_ordinal_of`/`_node_key_for_ord`/`_obs_node_ordinal`/sim `_ordinal_to_node`/`_node_ordinal`/`node_pos_of` 退役;`report_node_advance` 终局事件式(applied 语义扩展随 docstring 修订);schema derivation 域 bump 5;快照/恢复换形;效果账本登记链含 cw_gain_chain 直连消费点。**边界**:不含 cw_screen_battle_wait(3.3)、不含 cw_anchor 锚行槽与 journal_query 死 helper(3.4)、不含视界族(3.5);一次提交完成,无新旧表示并存窗口(R7 原子切换先例)。
**设计依据**:design.md §2.0/§2.2/§2.3/§2.4/§2.5/§2.6/§2.8(快照恢复半)/§2.10 取舍 2。
**文件面**:kernel/cw_game_state.py、kernel/cw_projection_audit.py、kernel/cw_node_schedule.py(删 `node_pos_of`)、kernel/cw_effect_inventory.py、kernel/cw_affix_effects.py、kernel/cw_gain_chain.py(`_portal_acquired_key` import/调用/注释)、kernel/cw_screen_report/boss_briefing.py、kernel/cw_screen_report/plane_transition.py、kernel/cw_encounter_selection.py(注释)、sim/cw_sim_backend.py、operations/cw_screen/cw_screen_prep.py、operations/cw_screen/cw_screen_supply_node.py、operations/cw_screen/cw_screen_plane_transition.py、operations/cw_op/cw_op_settle_confirm.py(注释);sr-od-test 对应测试(node advance/effect boundary/effect inventory/game state/gain chain/supply advance/sim 全链域)。
**依赖**:3.1
**优先级建议**:0
**完成判据**:
- 行为对照 design.md §2.2(两态字段/原语处置表/终局锁)、§2.3(直定与查链)、§2.4(账本三语义 + cw_gain_chain 消费)、§2.5(锚定写端)、§2.6(sim 簿记/进窗/局终腿)、§2.8(快照往返/旧档忽略);
- 默认环境 sim 全链回归与现役基线逐值同(design §2.11 锁 9);修饰局回归 = T-8 既有测试面全绿;
- 本批文件内 `node_ord`/`node_hist_ord`/`node_ordinal`/`_node_key_for_ord`/`node_pos_of`/`effective_node_ord`/`acquired_t`/`_portal_acquired_t`/`_entered_ord`/`_window_begun_ord` 符号零残留(grep 自证,入提交说明;`node_ordinal` 裸词覆盖 `node_ordinal_of` 与 `tick_node` 旧形参名);
- 完成前常规检查(本文首节,含 kernel/sim 全量)。
**验收凭据形式**:design §2.11 锁 1-6/8/9 对应测试;sim 默认局全链一条(基线数字对照)。

## 3.3 同式岛收口(败局闩)

**范围**:cw_screen_battle_wait 败局闩换键门(`SETTLE_DEFEAT_LATCH_MIN_POS=(2,5)`,设计 §2.7);结算单调门零改动核对;killed-hp 兜底门/`last_outcome_t` 零接触核对(T-8 裁决点 7 前半已删,断言符号不存在);killed 判定注释的 `node_t_of` 历史引用(:467 区)去符号化改写(注释级,语义不变;防 3.5 退役后成无主残留)。**边界**:不含结算读链其余语义;不含 cw_plane_table(3.5)。
**设计依据**:design.md §2.7(含逐值等价证明)。
**文件面**:operations/cw_screen/cw_screen_battle_wait.py;sr-od-test 对应测试(settle/battle wait 域)。
**依赖**:无(可与 3.2 并行;建议排后只为本批文件面清晰,非硬依赖)。
**优先级建议**:1
**完成判据**:
- 败局闩与旧 t 门逐值对拍((1,10)/(2,1)/(2,4)/(2,5) 边界,含修饰局形态;design §2.11 锁 7);
- 结算单调门(元组比较)与 killed 门零接触核对申报入提交说明;
- 完成前常规检查(本文首节)。
**验收凭据形式**:design §2.11 锁 7 测试;边界值对拍表。

## 3.4 遥测与载体收口

**范围**:cw_anchor 锚行 `node_seq` 槽退役(AnchorEvent 字段/to_row 键/emit_anchor 形参与幂等键槽);journal_query `node_ordinal_of` 死 helper 删除;cw_reconcile `reconcile_hp` 的 `node_t` 死形参删除(:456,守卫删除后零消费)。**边界**:不含 defects 维度词表(零改动申报面);不含快照/恢复(3.2 已含);obs `_node_t` 死局部已随 T-8 漏斗改造删除(设计 §2.7 零接触申报),不在本阶段。
**设计依据**:design.md §2.8/§2.10 取舍 6。
**文件面**:kernel/cw_anchor.py、telemetry/journal_query.py、kernel/cw_reconcile.py;sr-od-test journal 域既有测试(test_cw_journal_assembly_guard.py 等)。
**依赖**:无。
**优先级建议**:1
**完成判据**:
- `emit_anchor`/`AnchorEvent` 形状对照 design §2.8;删除后 journal 域既有测试全绿;
- `emit_anchor`/`node_seq`(锚行槽)/`node_ordinal_of`/`node_t`(reconcile 形参)生产面与测试面双向 grep 零残留(自证入提交说明);
- 完成前常规检查(本文首节)。
**验收凭据形式**:journal 域既有测试全绿;双向 grep 零残留自证。

## 3.5 视界族与 9 制几何层清扫

**范围**:T-8 裁决点 9 指派面(details/horizon-cleanup.md 全量)——cw_plane_table 几何层 11 符号退役(node_t_of/schedule_of/r_remaining/r_global/r_remaining_in_plane/plane_offsets/plane_end_slots/NODES_PER_PLANE/TOTAL_NODES/DEFAULT_PLANE_LENGTHS/PLANE_FALLBACK_PRIORS)+ nodes_of_plane 回退再基;策略门面 horizon.py 场字段重基(签名不变);proof/budget/levelup import 改道;strategy_economy boss 通道 kind 化;kernel 判据点(cw_economy/cw_intention/cw_comps)就地迁移;audit/标定域再基。**边界**:策略选卡估值/打分不动;`shop.py`/`statefn/odds.py`/`nodes_of_plane` 消费族零改动;行为变化以 details §8 申报为准。
**设计依据**:design.md §2.7(视界族段)+ details/horizon-cleanup.md(全篇)。
**文件面**:kernel/cw_plane_table.py、kernel/cw_economy.py、kernel/cw_intention.py、kernel/cw_comps.py、kernel/cw_registry.py(注释)、strategies/impl/mandate_v1/statefn/horizon.py、strategies/impl/mandate_v1/proof.py、strategies/impl/mandate_v1/statefn/budget.py、strategies/impl/mandate_v1/criteria/levelup.py、strategies/impl/mandate_v1/criteria/refresh.py(注释)、strategies/impl/mandate_v1/strategy_economy.py、strategies/impl/mandate_v1/audit/derived.py、strategies/impl/mandate_v1/audit/calibration.py、operations/cw_screen/cw_screen_prep.py(节点行消费位 docstring 的「位面日程真值(schedule_of)」句;与 3.2 同文件,依赖 3.2 防在飞冲突);sr-od-test 对应测试(策略域 + 受影响 kernel 域)。
**依赖**:3.2(同文件在飞面防冲突;非符号依赖);前置闸(T-8 场字段在役)。
**优先级建议**:1
**完成判据**:
- 门面/就地迁移行为对照 details §3-§6(签名不变/语义逐字保留/禁新公共视界口);
- 行为变化对照 details §8 申报面(修饰局视界修正/P3 虚拟轮移除/boss 计数 kind 化/标定域收紧);
- design §2.11 锁 10 对应测试;
- 退役 11 符号全仓 grep 零残留(自证入提交说明);
- 完成前常规检查(本文首节,含 kernel/sim 全量)。
**验收凭据形式**:design §2.11 锁 10 测试;门面默认表与现役 schedule_of 逐值对照表。

## 3.6 全仓清零核对

**范围**:对照 design §2.9 改清单与 §1.1 底册(14 处公式 + 具名常量几何层),全仓 grep 核对清单——编号族符号:`node_ord`/`node_hist_ord`/`effective_node_ord`/`node_ordinal_of`/`node_pos_of`/`_node_key_for_ord`/`_obs_node_ordinal`/`acquired_t`/`_portal_acquired_t`/`_entered_ord`/`_window_begun_ord`/`SETTLE_DEFEAT_LATCH_MIN_T`/`AnchorEvent` 的 `node_seq`;视界族符号:`node_t_of`/`schedule_of`/`r_remaining`/`r_global`/`r_remaining_in_plane`/`plane_offsets`/`plane_end_slots`/`NODES_PER_PLANE`/`TOTAL_NODES`/`DEFAULT_PLANE_LENGTHS`/`PLANE_FALLBACK_PRIORS`;式样:`*9`/`//9`/`%9` 身份语义命中。残留学面逐处判读:叙述性历史注记(模块头版本注/退役注)合法,活代码/活契约引用 = 打回对应阶段。**合法剩余预登记**:test_cw_battle_wait_defeat_latch.py 对拍测试内嵌的旧门公式 `(p-1)*9+r` = 对拍参照(锁 7 逐值等价证明的载体),非残留,勿开修复批;`node_t_of` 的「历史消费点已删」docstring 句(cw_plane_table,T-8 落地注)同属合法历史注。**边界**:纯核对,零代码改动(发现残留开修复批处理完再回到本阶段验收)。
**设计依据**:design.md §1.1(底册)/§2.9(改清单)/§1.3(清零目标)/§2.7(视界族)。
**文件面**:无(核对报告入提交说明/迭代 README 进度注)。
**依赖**:3.2、3.3、3.4、3.5
**优先级建议**:0
**完成判据**:核对单逐项「零残留 / 残留定性」两态闭合;`*9` 族与具名常量族扫描零身份/几何语义命中(合法剩余 = 规划量注释/历史注,逐处列出)。
**验收凭据形式**:grep 输出对照表(随提交说明)。

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本。
**设计依据**:本文件「正本更新清单」节。
**文件面**:清单所列正本文档。
**依赖**:3.1-3.6 全部
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致(正本只写键表示现形,无编号投影残句;数值/序位常量只写常量名)。
**验收凭据形式**:文档对照 review。

## 正本更新清单

- game_state/node-domain.md:§1 身份键句(`node_ordinal` 公式 → NodePos 键表示)、§2 字段表(`node_ord`/`node_hist_ord` 行 → `node_pos`/`node_hist_pos`)、生效序读口节(名称与字典序语义) ← 3.2
- game_state/node-derivation.md:§3.2 身份键节(含 `AnchorEvent.node_seq` 引注句)、§3.3 原语签名与四分支比较语义(元组字典序)、终局语义(事件式声明)补节、§3.5 锚行载荷 `node_seq` 槽退役注、§① 结论节符号名 ← 3.2/3.4
- game_state/fields.md:§3.6.2 节点域字段(`node_pos` 两态规格、`node_hist_pos`)+ §3.7.1(derivation 域版本 5)+ §3.2.1(node 域)快照/恢复值形如涉 ← 3.2
- game_state/effect-domain.md:登记时点语义(`acquired_key`)、`advance_node` 键契约、去重键 `(run_id, 生效序位)`、读口实例句(`effective_node_ord()` → `effective_node_pos()`) ← 3.2
- game_state/strategy-env-impacts.md:读口实例句(`effective_node_ord()` → `effective_node_pos()`,「首两个实例」列表内) ← 3.2
- game_state/journal.md:§4 自足快照行(state 行 values `node_pos`/顶层 `node_hist_pos`/effects 行 `acquired_key` 值形键名) ← 3.2
- game_state/README.md:§2 节点序例句(`node_ord` 逻辑层措辞)、§3.2 节点生效序摘要行(:89)、§3.3 域清单行(`node_ord`/`node_hist_ord`) ← 3.2
- sim/sim-design.md:§3.x 节点窗(`_window_begun_pos` 幂等键、`_enter_node_window` 键签名、局终声明消费腿、`_ordinal_to_node`/`_node_ordinal` 退役注)+ §6 `node_advance` 推导规则句(`effective_node_ord`/「超真值表总长」→ 终局声明事件式;与 action_ops.md §4.8 同文双锚,两处同改) ← 3.2
- flow/action_ops.md:§1 `applied` 义务句补终局出口语义(`match_end` 事件式);§4.8 `node_advance` 行推导规则句(「超真值表总长」→「`sequence_next` 无后继 = 局终声明事件式」;`effective_node_ord` → `effective_node_pos`) ← 3.2
- screens/battle_wait.md:§8 败局闩行(:78,`t ≥ SETTLE_DEFEAT_LATCH_MIN_T` → 序位 ≥ `SETTLE_DEFEAT_LATCH_MIN_POS`) ← 3.3
- strategy-docs/01_math_framework.md:§5 R_全局 行(:139,长度真值源 schedule_of → 场字段自算) ← 3.5
- strategy-docs/29_invest_strategy_screen.md:剩余口径单一源句(:26,`cw_plane_table.schedule_of`/`r_remaining` → 策略门面场字段自算;`total_remaining_nodes` 禁消费句随缺陷修正复核) ← 3.5
- strategy-docs/12_line_and_intention.md:P84 门 r_remaining 读法句(:71/:73,kernel 读法 → 策略门面读法) ← 3.5
