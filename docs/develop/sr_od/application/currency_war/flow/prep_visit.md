# 备战访问（prep_visit）

> 反向规格化来源 = `operations/cw_screen/cw_screen_prep.py`（CwScreenPrep）。职责：一次备战画面访问的完整编排——入口观察→对账→单动作决策循环（执行→逻辑态直写），直到终结 op 交还外循环。路径根 = `src/sr_od/application/currency_war/`。逻辑态 = 动作执行后不经观察、按游戏规则推算并直写容器的预期状态;真值以下一帧观察为准(观察赢)。

## 1. 单轮形态（W971 P3b：外循环是唯一循环,本 op 无内环;单动作化）

`run()`（`cw_screen_prep.py::CwScreenPrep.run`）每调用执行一轮：

```
run()
 ├─ 前置：session.last_prep_action_sig=None（守卫动作腿清零）+ 缓存复位 + config 构造
 ├─ ①观察（入口单次 heavy）：_clear_entry_overlays（清场）→ _try_collapse_open_shop（开商店态收起）
 │    → _observe(heavy=True)（期望态重建的唯一读屏点 = 入口对账）
 │    ├─ obs.event_overlay 非空 → round_success 交回外循环分发（不计数）
 │    └─ 接管局补采 _takeover_collect_if_needed（session.briefing_bosses 空 ∧ 节点条可读 → 位面详情情报采集；2 次失败放弃）
 ├─ ②对账段：上一访问逐动作暂存的期望态记账（session.cw_prep_pending_accts）在此时点
 │    统一 _v2_post_frame_accounting 消费后清空（入口观察即对账——per-action heavy
 │    重读契约已灭,逐动作零读屏,期望态由逻辑态直写承载推进;错卖类不可逆损害窗口的收窄
 │    手段 = 执行侧 tracked 账随动,同商店线双账口径）+ 空动作账（pending_buy_expect 留证族）
 ├─ 决策前置：
 │    ├─ 席满破墙 _bench_full_break_round（M16：备战席满警告模态 → 破墙动作优先，见 §4）
 │    └─ 观察终饰：dual 态拷回（committed_from 唯一读端）+ gated_hp 覆写
 │      （方向重估已内化进策略器决策入口,由帧代次标注 full 触发）
 └─ ③④⑤单动作决策循环 for _vi in range(VISIT_ACTION_CAP=16)（循环内零读屏）：
      action = strategy.decide_prep_screen(session, config) 取输出首项（单动作选择序,
      三遍编排序保持——决策核输出逐帧取首项;空批合法 → 交回外循环重观察）
      → F3 validate（参数非法 → 拒绝执行 + 交回留证）
      → 期望态计算（drag/equip/dep 记账,动作发出点）→ 执行（OpenShop 走流程层商店编排）
      → acct 暂存 session.cw_prep_pending_accts（对账归下一入口时点）
      → StartBattle ∧ progressed → round_success('出战')，交回外循环战斗分支
      → not progressed → fail-stop：恢复原语一次 → 交回外循环
      → OpenShop ✓ → 终结,交回外循环重识别
      → 逻辑态直写 _project_prep_obs（纯计算零读屏）:已建模面（OpenBox/OpenTome 腾席/
        ClickSpheres 保守清空/SellBench 摘槽）→ 黑板推进 session.prep_obs_frame,
        下一动作决策读逻辑态;未建模面（DeployMove/SellDeployed/LevelUp/RunDeploy/
        RunEquip）→ None = 保守回退:本访问终结交回外循环重观察（重观察语境禁猜;「验证阶梯」为旧波批设计遗留概念,现行防线 = 入口单次 heavy + 逻辑态直写）
      → 达 VISIT_ACTION_CAP = 防御上界（决策循环不收敛 = 逻辑态或策略 bug,交回外循环
        由 stall 防线接管,不静默续跑）
```

### 1.1 观察分层（F1/F2 契约）

- **heavy**（入口单次；单动作循环迁移后 = 画面 op 入口唯一读屏点——期望态重建,即对账。调用点 = 单轮入口 / OpenShop(read_only) 开态 gold 真值刷新）：SIFT 身份（bench/deployed）+ GameState 全量 + cap 读取 + 装备域三路（owned 件名池〔全量含工具〕/occupied 已穿明细/后排布局选档;P4 观察接线,T-171——原分发段 `_build_equip_wear_plan` 三路现读退役,采集单一源 = `obs.cw_observe_full.observe_full` heavy,写端 = 本 op 入口观察装配点 bs.equips observe + session 镜像全量重写）;光标 parking 先行（防 OCR/SIFT 污染）。旧「每个执行过的游戏动作后必调 heavy」契约已随单动作循环退役（逐动作零读屏,期望态由逻辑态直写纯计算推进;执行侧读数性通道的局部 park 由动作实现层自理,`_observe` docstring 载）。组装单一源 = `obs.cw_observe_full.observe_full`（tier='heavy'），director 只保留副作用编排（session 写/审计/缓存——单写者原则）。`PrepObservation` 字段清单 = `kernel/cw_prep_actions.py::PrepObservation`。
- **装备穿戴计划产出位**（`prep_actions._build_equip_wear_plan`）：改读入口观察产物（P4 接线,T-171）——三路事实源 = `session.prep_obs_frame` 装备域字段,产出位零读屏;识别域资源未就绪（字段 None）走 fail 通道（未发出闩不置）。kernel 判据单一源求值不变;「执行时刻屏态复验」(`_guard_screen_mismatch` 派发前置闸)职权留守分发层。
- **light**（兼容形态,现生产无调用方）：轻字段（球/箱/典籍/overlay/占用/shop_open）每步现读；heavy 字段沿用缓存。
- **可信门（F2/F5）**：gold 仅 shop 开态可信（`obs.state_gold_trusted = obs.shop_open`，关态读空）；hp 写 session 前过 `gated_hp` 新鲜度门（结算真值仅在可信窗口覆盖现读；`cw_strategy.py::gated_hp`）。
- 黑板写路径：obs 直写 `session.prep_obs_frame`（写者白名单 = 入口观察段/循环逻辑态直写步；读者 = decide_prep_screen；`cw_screen_prep.py`）。

### 1.2 观察段的对账接线（零决策记账）

heavy 帧消费：tracking 对账（SIFT 真值重置 session tracking，漂移留证）、期望态覆盖点 `prep_obs` 清账（条目绑覆盖点，gold 仅可信读清账）、cap<level 留证、deployed 双源对拍。期望态族（买/拖/经验/羁绊/商店池/合成预览/装备）细则 = `cw_screen_prep.py` 对账段（动作级对账经 `cw_prep_pending_accts` 暂存,消费帧 = 下一入口 heavy）。全部 best-effort，不阻塞环。

## 2. 备战决策核：live 链（mandate_v1）

**live 决策链（as-built，亲验）**：`cw_screen_prep.py`（主流程/破墙段）→ `strategies/impl/mandate_v1/bridge.py::MandateV1Strategy.decide_prep_screen`（黑板读 `session.prep_obs_frame`，缺失即抛错）→ `bridge.py::decide_from_turn`（纯函数：调 emit）→ `entry.py::emit`（决策入口三遍编排）。

`entry.emit` 编排序（docstring 与代码体一致）：① prep 实体面（boxes→OpenBox / tomes→OpenTome / spheres→席满让路门——席自由(free>0)照常 ClickSpheres,席满(free==0)按 `entry.SPHERE_DEFER_PROBE_K` 单探针后让路 fall-through 落后续步骤序,优先于三遍）→ ② 证明 pass（信号臂/K/stop_flag/线级状态机/换线）→ ③ 升档器求值位 → ④ 骨架 pass（M1-M7，`mandate.py`）→ ⑤ EV pass（criteria，臂①旁路）→ ⑥ 无动作 ⇒ StartBattle（序列终点 = 备战环正常出口）。动作词表 = emit/adapter 自有的 OpenBox/OpenTome/ClickSpheres/RunDeploy/RunEquip/StartBattle 等（`adapter.py::_OP_SPECS` 全集映射表），输出 `list[PrepAction]`——单动作循环取**首项**消费（执行序 = 逐帧取首项,即单动作选择序）。

### 2.1 旧备战骨架：已删除（迁移批死码清理）

以下旧骨架在 live 链上无入口（零生产调用,测试直调不算）,**已随单动作循环迁移批物理删除**（`flow.py` 模块头 docstring「旧备战骨架已删」节载清单）：`_decide_prep_action_impl`（步级决策序）/ `_main_flow_step`（prep_phase 相位机,原 §2.2）/ `_free_bench_step`（腾席链 a/a2/b/c/d,原 §3）/ `_deploy_up_candidates` / `_bench_junk_idx` / `_pseudo_state` / `_fresh_state` 及私有 helper（`_is_boss_round` / `_cap_shortfall` / `_levelup_engine_ok`）。传递性死码 `kernel/cw_deploy_seat` 整模块（`_should_deploy` 族——同名禁双不变量的存活载体 = `cw_state.board_unique_key`,部署谓词载体 = `cw_deploy_logic`）与 session 暂存字段 `prep_phase` / `prep_phase_retry` / `free_bench_gold_wait` 同批清除。腾席功能现由 mandate_v1 M4 骨架义务承载（`../strategy-docs/02_mandate_layer.md` §3）。

## 3. 完成判定与交还外循环

- **出战** = 唯一完成态：`StartBattle` 落地（progressed）→ round_success(wait=3) → 外循环置战斗窗口（`cw_loop.py::CwLoop.loop` 备战分支出口置位段）。
- 非完成交回（合法）：overlay 交回、空批、fail-stop 后交回、OpenShop 编排返回。每轮外循环重识别保证稳定性；无进展防线 = 外循环 G3 守卫（guards.md §1）。
- **环级预算**（旧内环机制已拆）：原 MAX_STEPS=60/STALL_LIMIT=5/连败→恢复→屏蔽随内环拆除（`cw_screen_prep.py::CwScreenPrep` 类常量 MAX_STEPS/STALL_LIMIT 保留为历史锚；现行防线 = 外循环）。

## 4. 席满破墙单轮（M16；`cw_screen_prep.py` `_bench_full_break_round`）

备战席满警告模态挡拖拽/出战 → 破墙优先：破墙 obs 用 `dataclasses.replace` 从真 obs 派生（free=0、vacancy=0 强制走链 b/c）→ 写黑板 → decide_prep_screen 取首项逐动作执行（fail-stop）→ 遥测记 `BenchFull_*` 行。警告解除 → 等待计数清零。

## 5. ⚠️ 现状违宪待改标记

- ~~⚠️ **谷底回滚 hp 消费**~~（**已销案**）：`VALLEY_ROLLBACK_LOSS=15` 单场掉血门曾触发 `rollback_weakest` 回滚动作——hp 掉量作质量信号驱动动作，不在 hp 授权对账表（`../strategy-docs/04_survival_budget.md` §7）；且 15 无三形态标注（宪法第 1/4 条）。**已裁定退役（2026-09-04 用户裁定：未经数学证明即退役；04 §7 #7），代码删除已随 T-64+T-183 退役批执行（零行为,载体全删）。**
- （旧备战骨架的位面字面门 `round_num >= 9` 与息引擎门双源漂移两项 ⚠️ 随单动作循环迁移批死码清除消失——载体 `_is_boss_round`/`_levelup_engine_ok` 已删,见 §2.1。）
