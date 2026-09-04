# 备战访问（prep_visit）

> 反向规格化来源 = `operations/cw_screen/cw_screen_prep.py`（CwScreenPrep，2016 行）+ `strategies/impl/flow.py`（备战主流程栈与腾席链）。职责：一次备战画面访问的完整编排——观察→对账→决策→期望态→执行，直到出战（StartBattle 落地）交还外循环。路径根 = `src/sr_od/application/currency_war/`。

## 1. 单轮五段（W971 P3b：外循环是唯一循环，本 op 无内环）

`run()`（`cw_screen_prep.py:1205-1398`）每调用执行一轮：

```
run()
 ├─ 前置：session.last_prep_action_sig=None（守卫动作腿清零）+ 缓存复位 + config 构造
 ├─ ①观察：_clear_entry_overlays（清场）→ _try_collapse_open_shop（开商店态收起）→ _observe(heavy=True)
 │    ├─ obs.event_overlay 非空 → round_success 交回外循环分发（不计数）
 │    └─ 接管局补采 _takeover_collect_if_needed（session.briefing_bosses 空 ∧ 节点条可读 → 位面详情情报采集；2 次失败放弃）
 ├─ ②对账段 _v2_post_frame_accounting（空动作账：消费 pending_buy_expect + 留证族）
 ├─ 决策前置：
 │    ├─ 席满破墙 _bench_full_break_round（M16：备战席满警告模态 → 破墙动作优先，见 §5）
 │    ├─ 意向驱动 drive_intention（每 game-round 恰一次，v3_intention_key 段级重入守卫；失败沿用旧方向）
 │    └─ update_target（异常沿用旧 target，不阻塞步级决策）
 ├─ ③决策：actions = strategy.decide_prep_screen(session, config)【待 ADR-0517 迁移：序列返回 + 逐动作消费在目标态改单动作循环，prep_phase 相位机已随 mandate_v1 接线退出 live（§2.1 死码标注；screen_op.md §8.2）】
 │    ├─ 异常 → round_fail（外循环 retry 链兜）
 │    ├─ 输出非 list[PrepAction] → round_fail（F3）
 │    ├─ session.last_prep_action_sig = 动作类型元组（守卫动作腿）
 │    └─ 空批 → round_success 交回外循环重观察（连续空批 stall 兜底归外循环）
 └─ ④⑤序列消费：逐动作（见 action_exec.md §3）：
      DeferSpheres/BailToOuter = 控制流（计数/交回，不进验证链）
      → F3 validate → 期望态计算（drag/equip/dep 计账）→ 执行（OpenShop 走流程层商店编排）
      → 执行后 heavy 重观察 + _v2_post_frame_accounting
      → StartBattle ∧ progressed → round_success('出战')，交回外循环战斗分支
      → not progressed → fail-stop：恢复原语一次 → 交回外循环
      → OpenShop ✓ → 序列终点交回外循环重识别
```

### 1.1 观察分层（F1/F2 契约）

- **heavy**（环入口 + 每个执行过的游戏动作后）：SIFT 身份（bench/deployed）+ GameState 全量 + cap 读取；光标 parking 先行（防 OCR/SIFT 污染）。组装单一源 = `obs.cw_observe_full.observe_full`（tier='heavy'），director 只保留副作用编排（session 写/审计/缓存——单写者原则）。`PrepObservation` 字段清单 = `kernel/cw_prep_actions.py:167-202`。
- **light**（控制流/拒绝步后）：轻字段（球/箱/典籍/overlay/占用/shop_open）每步现读；heavy 字段沿用缓存。
- **可信门（F2/F5）**：gold 仅 shop 开态可信（`obs.state_gold_trusted = obs.shop_open`，关态读空）；hp 写 session 前过 `gated_hp` 新鲜度门（结算真值仅在可信窗口覆盖现读；`cw_strategy.py:263-287`）。
- 黑板写路径：obs 直写 `session.prep_obs_frame`（写者白名单 = 本装配点；读者 = decide_prep_screen；`cw_screen_prep.py:641-648`）。

### 1.2 观察段的对账接线（零决策记账）

heavy 帧消费：tracking 对账（SIFT 真值重置 session tracking，漂移留证）、期望态覆盖点 `prep_obs` 清账（条目绑覆盖点，gold 仅可信读清账）、cap<level 留证、deployed 双源对拍。期望态族（买/拖/经验/羁绊/商店池/合成预览/装备）细则 = `cw_screen_prep.py:666-1188`（动作级对账在动作完成后同帧消费）。全部 best-effort，不阻塞环。

## 2. 备战决策核：live 链（mandate_v1）

**live 决策链（as-built，亲验）**：`cw_screen_prep.py:1278/1477`（主流程/破墙段）→ `strategies/impl/mandate_v1/bridge.py:80 decide_prep_screen`（黑板读 `session.prep_obs_frame`，缺失即抛错）→ `bridge.py:146 decide_from_turn`（纯函数：调 emit 后做帧稳定截断）→ `entry.py:325 emit`（决策入口三遍编排）。

`entry.emit` 编排序（docstring 与代码体一致）：① prep 实体面（boxes→OpenBox / tomes→OpenTome / spheres→ClickSpheres / event_overlay→BailToOuter，优先于三遍）→ ② 证明 pass（信号臂/K/stop_flag/线级状态机/换线）→ ③ 升档器求值位 → ④ 骨架 pass（M1-M7，`mandate.py`）→ ⑤ EV pass（criteria，臂①旁路）→ ⑥ 无动作 ⇒ StartBattle（序列终点 = 备战环正常出口）。动作词表 = emit/adapter 自有的 OpenBox/OpenTome/ClickSpheres/RunDeploy/RunEquip/StartBattle 等（`adapter.py:173-187`），输出 `list[PrepAction]`（执行序 = 列表序，帧稳定截断见 `README.md` §2.2）。

### 2.1 死码簇：旧备战骨架（`flow.py`，零生产调用，挂收敛批）

以下旧骨架在 live 链上无入口（`_decide_prep_action_impl` 仅测试直调；其余成员互相调用闭环），随死码收敛批裁决去留——as-built 如下如实保留，**不再是现行机制**：

### 2.2 备战相位机（prep_phase，`flow.py:794-849` `_main_flow_step`）【死码】

阶段位在**出动作时**前移（策略看不到执行结果；失败由框架 fail/恢复链兜住）。prep_phase 唯一写点即本段（`flow.py:801-845`），live 无消费（仅 battle_wait 复位，`cw_screen_battle_wait.py:480-482`）：

| prep_phase | 进入条件 | 发射 | 语义 |
|---|---|---|---|
| 0→1 | 入口 | free_bench_slots≤0（M-6 门）→ 先过腾席链 a/b/c 破满席（链 d 不入——无球时 defer 无意义；链全空 → 直落部署段）；否则 `OpenShop()` | 买牌段 = 显式开店意图，流程层 `_open_shop_phase` 编排（shop_visit.md） |
| 1→2 | 买牌段返回 | **dd-037 部署发射门**：`_deploy_up_candidates`（与执行方同源的 kernel 纯函数 `cw_deploy_logic.select_deployments` 算"谁该上场"）非空 → `RunDeploy()`；空 → 跳过直发 `RunEquip()` | 计划空（候选全被配方底线/去重/cap 留 bench）时不发射 RunDeploy——bench 稳态合法，消除"发射方谓词与执行方不同源 → 空计划 → 环级零推进"死循环形态 |
| 2→3 | 部署段返回 | `RunEquip()` | 全员装备（M7 骨架地板） |
| 3 | 装备段返回 | **空板出战守卫**：deployed=0 ∧ bench>0 ∧ retry<2 → prep_phase=1 回部署段重试；否则 `StartBattle()` | 板上 0 人 = 部署失败（空板出战在强节点掉 24-29 血，r23 实证） |

### 2.3 步级决策序（`_decide_prep_action_impl`，`flow.py:501-530`）【死码：仅测试直调】

```
box_overlay_open → PickBoxCard（P1 执行器默认选卡）
tomes ∧ defer_count<2 → OpenTome（defer 门：执行器连败置 defer 后放弃，防活锁）
boxes → OpenBox
spheres ∧ free>0：
   shop_open → OpenShop(read_only=True)（商店开态假球误检 → 先编排关店取清洁面板）
   defer_count≥2 → 主流程（球疑假检放弃）
   否则 ClickSpheres(max_k=min(free, len(spheres)))
spheres ∧ free=0 ∧ defer<2 → _free_bench_step（腾席链）
否则 → _main_flow_step（相位机）
```

## 3. 腾席链（`flow.py:601-723` `_free_bench_step`；bench 满时按序尝试）【死码：属 §2.1 死码簇，零生产调用】

| 链 | 动作 | 判据 |
|---|---|---|
| **a** deploy 空位 | `DeployMove(from_slot, row, slot)` | `deploy_legal`（同名在场守卫，kernel 单一源）∧ 失败记忆（同角色拖拽被游戏拒过 → 跳过）∧ `_should_deploy` ∧ `_pick_deploy_row` 有空位。零成本最优 |
| **a2** 卖杂件 | `SellBench(slot)` | target≠None 时 `_bench_junk_idx`：off-target（`_card_supports_target` False）∧ 3合1 重复件保护 ∧ `_bench_sell_value` 最低价值。ADR-0274"腾席优先用卖件解决" |
| **b** 升级扩容 | `LevelUp()` | **三前置**（ADR-0274）：①非 boss 轮（`_is_boss_round`，⚠️ 见 §6）②真缺人口（`_cap_shortfall≥1`：想上场而被 cap 卡住的 bench 件数，现有空位先扣）③息引擎门 `_levelup_engine_ok`（⚠️ 见 §6）。gold 需可信（F2）：首等 = OpenShop(read_only) 开态重读；同环第 2 次仍无真值 = 无进展环 → stale gold 试算 gate（level_up_cost 缺省 4【注】），gate 拒才落链 c |
| **c** 卖最弱 | `SellBench(slot)` | `_weakest_bench_idx`（含 3合1 重复件保护）；全保护 ∧ b 等待超限 → 强制卖 bench 首个非在场件（保护是优化不是死锁理由，r364） |
| **d** 留置 | `DeferSpheres()` | 全是有用角色 → 球留置交回外循环（框架计 defer_count，门=2） |

升级门 committed 从 `committed_from` 权威派生显式传入（ADR-0466/0467/0469 C5 换源：fresh 帧不依赖装配边界回填）。

## 4. 完成判定与交还外循环

- **出战** = 唯一完成态：`StartBattle` 落地（progressed）→ round_success(wait=3) → 外循环置战斗窗口（`cw_loop.py:1321-1328`）。
- 非完成交回（合法）：overlay 交回、空批、fail-stop 后交回、OpenShop 编排返回。每轮外循环重识别保证稳定性；无进展防线 = 外循环 G3 守卫（guards.md §1）。
- **环级预算**（旧内环机制已拆）：原 MAX_STEPS=60/STALL_LIMIT=5/连败→恢复→屏蔽随内环拆除（`cw_screen_prep.py:393-405` 类常量保留为历史锚；现行防线 = 外循环）。

## 5. 席满破墙单轮（M16，ADR-0136；`cw_screen_prep.py:1454-1504`）

备战席满警告模态挡拖拽/出战 → 破墙优先：破墙 obs 用 `dataclasses.replace` 从真 obs 派生（free=0、vacancy=0 强制走链 b/c）→ 写黑板 → decide_prep_screen → 逐动作执行（fail-stop）→ 遥测记 `BenchFull_*` 行。警告解除 → 等待计数清零。

## 6. ⚠️ 现状违宪待改标记

- ⚠️ **`_is_boss_round` 的 `round_num >= 9` 先验**（`flow.py:542`）：boss 轮判定 = node_type=='boss'（权威源 = 备战节点行）∨ round≥9 先验（supply 例外）。round≥9 是 P1 九节点假设的位面字面量（位面 2 为 7 节点时段内误判），违反宪法第 2 条"位面只作参数"。**修正方向**：节点数表（`cw_plane_table.schedule_of` / NODES_PER_PLANE）作查表键派生位面末节点判定，round 先验退役。
- ⚠️ **`_levelup_engine_ok` 息引擎门**（`flow.py:559-572`）：lv≥5 要求"本局曾达满息 latch ∨ 升级总成本花完后金≥50"。①与 mandate 现行 arm2 结构守息门 g*=10×cap_resolved（`../strategy-docs/02_mandate_layer.md` §3 M3）不同源 = 双源漂移；②"未达满息局整局禁升"有压制发展嫌疑（宪法第 3 条）。**修正方向**：升级调度门单一源收口到 arm2 g* 门（只延迟不否决语义），v2 形态随退役链删除。
- ⚠️ **谷底回滚 hp 消费**（`flow.py:118,224-234`，on_round_end 段）：`VALLEY_ROLLBACK_LOSS=15` 单场掉血门触发 `rollback_weakest` 回滚动作——hp 掉量作质量信号驱动动作，不在 hp 授权对账表（`../strategy-docs/04_survival_budget.md` §7）；且 15 无三形态标注（宪法第 1/4 条）。**已裁定退役（2026-09-04 用户裁定：未经数学证明即退役；04 §7 #7）**——代码删除随迁移后批次执行。
