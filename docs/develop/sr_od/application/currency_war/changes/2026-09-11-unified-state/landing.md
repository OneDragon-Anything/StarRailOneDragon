# 2026-09-11-unified-state 落地

> **追认式声明**：账本先于本文件存在（`.debug/progress/2026-09-11-cw-clear-run/dag.jsonl`）；
> 完成判据单一源 = 账本各任务 criteria 预注册，本文阶段小节与账本同步演化自此起——
> 阶段小节改 → 账本 criteria 同步改，禁止两处各自演化。

### 3.1 阶段1：W4 键收编链（T-1+T-2+T-3+T-4）
**范围**：cw4_counters 逐 key 审计+键收编落码+cw4 流删除；边界=不含效果域内容语义设计件成文（候裁 8 前置，见 r5-migration-plan §7）。
**设计依据**：r5-migration-plan §2 W4 行；详设 §7（效果面完备性判据）。
**文件面**：strategies/kernel 分键写点、operations/cw_loop.py、telemetry/match_archive.py、telemetry/cli.py（r5-migration-plan §6 P4）。
**依赖**：无（审计段可先行）。
**优先级建议**：8
**完成判据**：账本 T-1/T-2/T-3/T-4 criteria 预注册（dag.jsonl）。
**验收凭据形式**：账本各任务 criteria 所列凭据（键全集封闭性锁+落地审+实机窗口，r5-migration-plan §2 W4）。

### 3.2 阶段2：W6 决策面切统一容器（T-5）
**范围**：生产决策面签名与字段读切换统一容器、sim 内部模型切换、投影 cw_bs_view 退役；边界=不含旧 GameState 本体删除（归阶段4）。
**设计依据**：r5-migration-plan §2 W6 行；详设 §8.7（迁移批次二消费切换落位面）。
**文件面**：kernel 决策簇、strategies/impl（mandate_v1）、sim（engine_p1/engine_p2/cw_replay/runner）、decision_assembly/cw_game_ports、kernel/cw_bs_view.py 删除（r5-migration-plan §6 P6）。
**依赖**：阶段1；W5 透传域建模绿（r5-migration-plan §2 W6 进入门）。
**优先级建议**：7
**完成判据**：账本 T-5 criteria 预注册（dag.jsonl）。
**验收凭据形式**：零引用锁（src+测试仓旧 GameState=0）+决策行为锁族+回放语料逐位等价（r5-migration-plan §2 W6）。

### 3.3 阶段3：W7 剩余旧流写面删除（T-6）
**范围**：处置表定案流写点全部下线（recorder 旧流方法/散布写点/battle_done 旧写/board_state_archive 写点）+retirement.md 影子框架重构文档批；边界=旧流数据文件不删不写（归档只读）。
**设计依据**：r5-migration-plan §2 W7 行。
**文件面**：telemetry/recorder.py、operations/cw_loop.py 与 ops 散布写点、cw_screen_battle_wait.py、sim/ledger_hooks.py、retirement.md（r5-migration-plan §6 P7）。
**依赖**：阶段1-2；W1-W3 验收绿（r5-migration-plan §2 W7 进入门）。
**优先级建议**：6
**完成判据**：账本 T-6 criteria 预注册（dag.jsonl）。
**验收凭据形式**：旧流文件名全仓零写点 grep 锁+全量测试绿+实机 ≥2 完整局（r5-migration-plan §2 W7）。

### 3.4 阶段4：W8 本体删除+BoardState 正名 GameState（T-7）
**范围**：cw_state.py 切割删除（旧 GameState 数据类+专属方法；共享词汇类型居所按候裁 9）+正名 BoardState→GameState（先删后名两段，模块文件名候裁 7）；边界=居所与文件名只执行既有裁定候选，不重裁。
**设计依据**：r5-migration-plan §2 W8 行+§3（改名时机）；详设头部命名对应注。
**文件面**：kernel/cw_state.py（切割）、kernel/cw_board_state.py（正名）、全仓 import 面+测试仓、D1 锁常量、game_state 目录命名注（r5-migration-plan §6 P8）。
**依赖**：阶段3。
**优先级建议**：5
**完成判据**：账本 T-7 criteria 预注册（dag.jsonl）。
**验收凭据形式**：旧本体全仓零引用锁+全量测试绿+正名后 1 完整局（r5-migration-plan §2 W8）。

### 3.5 阶段5：效果账本结算挂点接线（T-9）
**范围**：效果账本 effect_inventory 结算挂点（on_battle_end）接线；边界=五在产挂点（选卡登记/节点 tick/计数 bump/跳过递减/升级标记）不重做。
**设计依据**：详设 §5（§5.1 在场效果激活账本·挂点清单）。
**文件面**：kernel/cw_effect_inventory.py、kernel/cw_board_state.py、battle 结算链挂点（cw_screen_battle_wait/cw_loop）。
**依赖**：效果账本载体在产（已落地批次，详设 §5.1）。
**优先级建议**：5
**完成判据**：账本 T-9 criteria 预注册（dag.jsonl）。
**验收凭据形式**：账本 criteria 所列凭据（挂点行为锁）。

### 3.6 阶段6：board_rewrite 板面重写落码（T-10）
**范围**：EffectSpec.board_rewrite 面（全员晋升/人力重组/卖全场族）落码执行；边界=随机替换面的非确定性后果仍走观察覆盖收口（详设 §5.3 归属判据）。
**设计依据**：详设 §5（§5.3 板面重写族各行）。
**文件面**：kernel/cw_effect_inventory.py、kernel/cw_board_state.py、备战执行链应用点。
**依赖**：效果账本载体在产（详设 §5.1）。
**优先级建议**：4
**完成判据**：账本 T-10 criteria 预注册（dag.jsonl）。
**验收凭据形式**：账本 criteria 所列凭据（确定性面行为锁）。

### 3.7 阶段7：条件型免费刷新结构化（T-11）
**范围**：条件型免费发放结构化入计数域；边界=非条件族（per_node/NODE_ENTER/burst 已在册）不重做。
**设计依据**：详设 §3.3.6（商店免费刷新余额）。
**文件面**：kernel/cw_board_state.py（计数域）、kernel/cw_effect_inventory.py、刷新执行免费闸消费面。
**依赖**：免费刷新结构化字段族在册（详设 §3.3.5）。
**优先级建议**：4
**完成判据**：账本 T-11 criteria 预注册（dag.jsonl）。
**验收凭据形式**：账本 criteria 所列凭据（计数行为锁）。

### 3.8 阶段8：词缀 affix 建模（T-12）
**范围**：affix_effects_data 词缀（成长的烦恼/变宝为废等）结构化建模、ActiveEffect.source='affix' 启用；边界=玩法机制原文归 game 子树，不复制进 state。
**设计依据**：详设 §3.4.4/§5.3（§5.2 词缀缺口登记辖）。
**文件面**：affix_effects_data.py（注册表）、kernel/cw_effect_inventory.py、kernel/cw_board_state.py。
**依赖**：无（ActiveEffect.source='affix' 预留在册，详设 §5.2）。
**优先级建议**：3
**完成判据**：账本 T-12 criteria 预注册（dag.jsonl）。
**验收凭据形式**：账本 criteria 所列凭据（改写面归属锁）。

### 3.9 阶段9：备战席星级观察采证（T-15）
**范围**：备战席星级/装备图标观察面采证（负探针复核）；边界=建线与接线归后续批，本阶段只采证定口径。
**设计依据**：详设 §3.2.18（星级与装备子字段·备战席装备图标负探针）。
**文件面**：obs/ 识别面（battle_prep_recognizer/cw_identity_obs）、画面建档 assets/game_data/screen_info（如需补档）。
**依赖**：无（观察线在役：read_star/cw_identity_obs）。
**优先级建议**：3
**完成判据**：账本 T-15 criteria 预注册（dag.jsonl）。
**验收凭据形式**：账本 criteria 所列凭据（采证记档+探针复核记录）。

## 末阶段：正本更新
**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：game_state/（README 总纲+分篇，含新建 fields.md）与清单所列代码 docstring
**依赖**：全部阶段
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单
> 终态：正本家 = docs/develop/currency_war/game_state/（总纲+分篇）；本迭代全部设计语义最终归宿于此，详设件是过程载体。
- game_state/fields.md（**新建分篇**，承载字段级规格——来源=详设 §3 画面字段清单/§4 决策 op 写入面/§5 效果族归属；拆分粒度=归拢时定，可按画面或域拆多篇）← 阶段5-8
- game_state/README.md §3.3 域清单字段面收全 ← 阶段5-8
- game_state/README.md §1/§5 过渡注清除（详设归拢后）← 末阶段
- 六处代码 docstring 引用改指正本 game_state/（入口=总纲，字段级面指分篇；cw_board_state/cw_bs_view/cw_observation/cw_shop_refresh_obs/engine_p1/cw_anchor）← 末阶段

## 排除声明
- T-8 属统一观察架构迭代，不在本迭代面；
- T-13/T-14/T-16..T-28 非本迭代面（归属各自所属迭代的账本辖）。
