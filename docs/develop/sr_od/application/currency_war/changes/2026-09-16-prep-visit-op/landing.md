# 备战访问编排 op 化 落地

> 阶段拆分原则：3.1 执行器合一先行（唯一执行路就位）；3.2 策略发射位（决策进策略层）；3.3 op 接管 + cw_loop 收敛（原子切换，同提交）；3.4 正本更新。3.2 先于 3.3——策略会发发射意图了，op 才接管执行。

## 3.1 出战执行器合一
**范围**：审计 `readiness_battle_launch`（cw_loop）与 `_start_battle`（prep_actions）+ StartBattleOp 逐项差异 → 合一为单一出战执行器（落 prep_actions.py）；恢复局面调用点改调统一执行器；`readiness_battle_launch` 退役。边界：不动达标臂分支（其随 3.3 迁移）、不动 mandate_v1。
**设计依据**：design.md §2 方案 2 与接口契约（执行器条款）。
**文件面**：`src/sr_od/application/currency_war/operations/prep_actions.py`；`src/sr_od/application/currency_war/operations/cw_loop.py`（恢复局面调用点）；相关测试。
**依赖**：无。
**优先级建议**：5
**完成判据**：
- 审计清单交付：两执行路径逐项行为对照（屏态复验/重发长按/失败计数复位/连败停机/免战子态），每项标注归属与合并语义；
- 合一后：达标臂/恢复局面/策略终点三个调用面走同一执行函数（grep 无第二实现）；既有出战行为锁全绿（含免战牌、重发、连败停机锁）；
- 日志标签审计输出（供 3.4 哨兵/正本对照）；
- §12 通用工程门（引用，不复述）。
**验收凭据形式**：审计清单 + 测试名 + ruff。

## 3.2 策略发射位（发射决策入 mandate_v1，简单实现）
**范围**：mandate decide 入口新增前置发射位（骨架 pass 之前，直线判定）：消费 kernel `readiness_launch_decision` → armed ∧ 金 > 息线 → 产出受限商店访问意图序（OpenShop 携预算闸）；armed ∧ 金 ≤ 息线 → 产出 StartBattle 终点意图；非 armed → 原三遍编排零变化。边界：不重构三遍化结构；`cw_launch_admission` 不动。
**设计依据**：design.md §2 方案 3。
**文件面**：`src/sr_od/application/currency_war/strategies/impl/mandate_v1/`（entry/mandate 任一契合位）；`sr-od-test/test/sr_od/app/currency_war/`（单帧锁随迁）。
**依赖**：无（与 3.1 并行可行）。
**优先级建议**：5
**完成判据**：
- 单帧锁：armed 帧 → StartBattle 意图（14_p1 §7.2 达标臂锁组 W2-① 随迁新载体）；armed ∧ 金超息线帧 → 受限访问意图（非发射）；非 armed 帧 → 意图序与迁移前逐项一致（W2-① 非达标帧零变化锁随迁）；
- 息线值源 = kernel 派生（断言经 cw_economy 读口，非手写常数——零调参纪律）；
- 全量 CW 测试绿（含 mandate 既有锁组）；
- §12 通用工程门（引用，不复述）。
**验收凭据形式**：单帧锁名 + ruff。

## 3.3 op 接管 + cw_loop 备战分支收敛（原子切换，同一提交）
**范围**：达标臂四段从 cw_loop 备战分支退役（判定消费随 3.2 入策略；浮层闸由 op 清场职责 + 零判效重判承载；仲裁由 3.2 意图序承载）；受限商店访问执行按意图预算闸接入；交回契约落地（`launch_fired` + loop 战斗窗置位改读契约）；`_prep_anchors_hit` 仲裁预检退役（双锚守卫由 op 入口承接）。边界：恢复局面直通形态不变（调统一执行器）、`cw_launch_admission` 不动。
**设计依据**：design.md §2 方案 1/4/5、行为变化申报四条、接口契约。
**文件面**：`src/sr_od/application/currency_war/operations/cw_loop.py`；`src/sr_od/application/currency_war/operations/cw_screen/cw_screen_prep.py`；相关测试。
**依赖**：3.1、3.2
**优先级建议**：5
**完成判据**：
- 定向回归：达标帧发射恰一次（跨帧形态 = 受限访问帧 + 次帧发射帧，两帧合计恰一次，W2 锁面）；非达标帧备战序零变化；浮层命中帧不发射且次帧重判；
- 交回契约：op 发射后 loop 正确置战斗窗；
- 恢复局面回归：锁定局直通行为零变化（闩只辖恢复局面的既有锁保持）；
- 全量 CW 测试绿；grep 达标臂特征符号在 cw_loop 备战分支零残留；
- §12 通用工程门（引用，不复述）。
**验收凭据形式**：测试名 + grep 输出。

## 3.4 正本更新
**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：3.3
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致。
**验收凭据形式**：文档对照 review。

## 正本更新清单
- `flow/outer_loop.md`：§3 进入序收敛（达标臂行删除，改「派发备战访问 op + 交回契约置战斗窗」短行；发射决策指针 → 策略层前置发射位）← 3.3
- `strategy-docs/26_battle_settlement.md`：「发射帧受限消费仲裁归流程层」改写为「发射决策 = mandate_v1 前置发射位（仲裁意图序），受限访问执行 = 备战访问 op」← 3.3
- `strategy-docs/14_p1_consume_arms.md`：§9.6 发射位宿主注记（cw_loop → mandate_v1 前置发射位 + 备战访问 op 执行；C1 执行器合一后单一执行路符号）← 3.3
- `game_state/logic-updates/start-battle.md`：执行器行（合一后统一执行器符号）+ 战斗窗置位通道（交回契约）← 3.3
- `screens/op-layer.md`：五段生命周期 decide 段补注（发射决策 = mandate_v1 前置发射位，CwScreenPrep 决策面收编）← 3.3
