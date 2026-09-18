# 2026-09-18-screen-op-flat-report 落地

> 阶段唯一源;立任务照各节 `dag.py add`。每阶段含本阶段测试同步(§2.8),验证 = ruff(改动文件)+ 本族测试;T-7/T-8 收口跑 L1 全量,末尾 L3。
> 屏文件辖域(design §2.3):各迁移批除写点转录外,顺带把**该屏**的更新/对账特判(类型化载荷之上、无像素依赖)收编进自己的屏文件——一屏一议,不搞大爆炸;要摸帧的逻辑留守观察侧。

## 3.1 kernel 基座(cw_screen_report 包:每画面一文件 obs+report)

**范围**：新建 `kernel/cw_screen_report/` 包(**每画面一文件**,§2.6 全表 35+2 屏各一文件:obs 类 + `report_screen_*_obs` 函数同居;推进型/商店框屏文件只含 obs 类与「无 report」声明——用户裁定⑦一律直接拆到位,避免后续再拆);函数体 = 各画面现役观察性写点逐位转录(sig/family/actor/evidence 沿用原写点原值,REGISTERED_ACTORS 零扩面,其余语义零改动)。**纯新增,零行为切换**——本阶段无任何 op 改道,`cw_game_state.py` 零触碰。
**设计依据**：design.md §2.2/§2.3/§2.6。
**文件面**：`kernel/cw_screen_report/`（新建包）、`sr-od-test` 对应测试；**禁碰** `cw_game_state.py`/`cw_action_report/`/`cw_screen_buy_cards.py`/`sim/`（并行会话在飞面）。
**依赖**：无。
**优先级建议**：9。
**完成判据**：
- report 接口签名/辖域对照 design.md §2.3（动作事实/chosen_*/刷新计数三边界不越）；
- `uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 全绿（纯新增不破坏现役）。
**验收凭据形式**：新测试（report 接口逐域写入断言，桩 gs 直驱）+ 全量 L1。

## 3.2 事件屏·节点循环族迁移（8 屏）

**范围**：megastar / equip_pick / partner / planner / fortune / wish_trial / bookcard / expert_invite 改两 node 形态（§2.1）；删适配器/分流/生命周期方法；写点按 §2.6 切 report；测试同步改单路径驱动。
**设计依据**：design.md §2.1/§2.3/§2.6；先例模板 = megastar。
**文件面**：上述 8 个 `cw_screen_*.py`、`sr-od-test` 对应测试。
**依赖**：T-1。
**优先级建议**：7。
**完成判据**：
- 8 屏形态对照 §2.1（两 node、round_wait 循环、无防御上限、出口三语义）；
- 写点迁移对照 §2.6（懒读保真/chosen 留守逐条）；
- 本族测试全绿。
**验收凭据形式**：本族测试 + ruff。

## 3.3 事件屏·带面板/刷新链族迁移（5 屏）

**范围**：encounter / supply_node / invest_strategy / invest_env / armory_box 同构迁移；刷新计数按 §2.4 出辖处置（钩子退役不转录、读端原样）。
**设计依据**：design.md §2.1/§2.3/§2.4/§2.6。
**文件面**：上述 5 个 `cw_screen_*.py`、`sr-od-test` 对应测试。
**依赖**：T-1。
**优先级建议**：7。
**完成判据**：同 3.2 判据结构 + §2.4 出辖三条逐条对照。
**验收凭据形式**：本族测试 + ruff。

## 3.4 阶段/简报/过渡族迁移（6 屏）

**范围**：briefing / boss_briefing / wait_one_one / plane_transition / plane_intel / deploy_not_full 同构迁移。
**设计依据**：design.md §2.1/§2.3/§2.6。
**文件面**：上述 6 个 `cw_screen_*.py`、`sr-od-test` 对应测试。
**依赖**：T-1。
**优先级建议**：6。
**完成判据**：同 3.2 判据结构。
**验收凭据形式**：本族测试 + ruff。

## 3.5 重型屏迁移（prep / 买牌 + 商店框 / 战斗等待）

**范围**：CwScreenPrep / CwScreenBuyCards / CwScreenBattleWait / CwOpOpenShop / CwOpCloseShop 迁移；漏斗内部不动（§2.3）；买牌波循环两处端口消费改直连现役链；op 层写点按 §2.6 收编 report。
**设计依据**：design.md §2.1/§2.3/§2.6。
**文件面**：`cw_screen_prep.py`、`cw_screen_buy_cards.py`、`cw_screen_battle_wait.py`、`cw_op/cw_op_open_shop.py`、`cw_op/cw_op_close_shop.py`、`sr-od-test` 对应测试。
**依赖**：T-1。
**优先级建议**：6。
**完成判据**：
- 漏斗调用链零改动（read_game_state 签名/写端）；端口消费点删净；
- 行为锁（prep 决策循环/买牌波循环/结算链）语义逐位保留。
**验收凭据形式**：prep/商店/结算测试族全绿 + ruff。
**风险注记**：`cw_op/` 目录有并行会话在飞改动（动作 op 侧），动该目录两文件前先 `git status` 核对；冲突即停手上报。

## 3.6 推进型 12 屏内联 + box_pick

**范围**：12 推进型屏骨架内联（§2.1 末条，无 report）+ CwScreenBoxPick 补 obs/report。
**设计依据**：design.md §2.1/§2.2/§2.6。
**文件面**：12 个推进型 `cw_screen_*.py`、`cw_screen_box_pick.py`、`sr-od-test` 对应测试。
**依赖**：T-1。
**优先级建议**：5。
**完成判据**：12 屏内联后入口/推进/重入语义与现役 `_progression_base.py::handle` 逐位等价；box_pick 写点收编。
**验收凭据形式**：closing/phase 测试族全绿 + ruff。

## 3.7 退役批

**范围**：删 `cw_screen_op_base.py`、`_progression_base.py`、`cw_game_ports.py`、`decision_frame_hooks.py` 假环境分支、残余适配器/旧观察类名；AST 收口锁改形（「cw_screen/ 顶层 op 类必直继承 SrOperation」）；`_cw_helpers.py` 端口桩清理、`test_cw_game_ports` 删。
**设计依据**：design.md §2.5/§2.8。
**文件面**：上述文件 + 全树 grep 兜底（基类/端口/段迹符号零残余）。
**依赖**：T-2、T-3、T-4、T-5、T-6。
**优先级建议**：8。
**完成判据**：
- 退役面符号全树 grep 零命中（`CwScreenOpBase|CwProgressionScreenOp|cw_game_ports|observation_source|action_sink|_lifecycle_trace|register_outcome_hook|XxxObservation 旧名`，多行形态模式核对）；
- L1 全量绿。
**验收凭据形式**：grep 归零输出 + L1。

## 末阶段 3.8 正本更新

**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：T-7。
**优先级建议**：0。
**完成判据**：清单清零；正本与实现一致；L3 全量绿。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `docs/develop/sr_od/application/currency_war/screens/op-layer.md`：全文重写（基类机制 §2/§4 退役 → 两 node 形态 + report 接口 + 出辖申报）← T-2..T-7
- `docs/develop/sr_od/application/currency_war/flow/README.md`：§1 总图（画面指挥层描述）、§2.5 生命周期注、§3 导读表 ← T-7
- `docs/develop/sr_od/application/currency_war/screens/README.md`：能力矩阵与形态列 ← T-2..T-6
- `docs/develop/sr_od/application/currency_war/game_state/fields.md`：report 接口摄入映射（若有字段级增改）← T-1/T-3/T-5
- `docs/develop/sr_od/application/currency_war/flow/guards.md`：商店未识别卡停机载体描述核对 ← T-5
- `docs/develop/sr_od/application/currency_war/flow/outer_loop.md`：分发表述若提及基类/段迹 ← T-7
- `kernel/cw_screen_report/` 全部屏文件 docstring：**changes/ 引用清理——铁律「代码禁引 changes/」**,改为正本 op-layer.md 锚或就地内联语义 ← T-1(交付时引了 design.md §2.2/§2.3/§2.4)/T-2..T-6 同批面
