# logic-rand-sampling 落地

## 3.1 内核写面（merge 步回调 + board 继承 + 污染判定口）
**范围**：design.md §2.2 四项——① `_merge_bench` 可选步回调 `on_step`（缺省 None = 现行为）；② `_write_logic_frame` 行域写为随机态时 board 派生写继承 `logic_rand`；③ `GameState.any_logic_rand(field_names)` 读口；④ `write_logic_rand` 与模块 docstring「逻辑随机态」段的采样语义修订。边界：不动 collect_ore、不动买牌行为路径、不动 observe() 旁路。
**设计依据**：design.md §2.2 / §2.1
**文件面**：`src/sr_od/application/currency_war/kernel/cw_merge_simulate.py`、`src/sr_od/application/currency_war/kernel/cw_game_state.py`；测试仓对应测试文件
**依赖**：无
**优先级建议**：5
**完成判据**：
- `on_step` 缺省零行为：既有全量（含买牌投影直锁 `test_cw_shop_projection_logic`）绿
- 步回调触发次数 = 合并级数（连锁两级 = 2 次调用，行为锁）
- 行域 `write_logic_rand` 后 board 派生行 `source == 'logic_rand'`；行域 `write_logic` 后 board 仍 logic（回归腿）
- `any_logic_rand` 真值表（空集/含 rand/全非 rand）
- §12 通用工程门（ruff 改动文件 + L1 快速集绿）
**验收凭据形式**：测试名 + 命令复跑（`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`）

## 3.2 采样器 + 点晶矿上报改造 + sim 接线
**范围**：design.md §2.3–§2.5——`kernel/cw_ore_reward.py` 采样器（roll_ore_reward，假设档披露键 §0.1）；`collect_ore.py` 重写（守卫前置 → 采样 → 逐步写：spheres 确定面 + 三分支 + 未抽中域标记 + 角色分支合成链逐步行/深拷贝）；sim CollectOre 委托分支传流键 rng（`M1x/ore`）。边界：其他动作零改动、策略器零改动、晶矿识别读链零改动。
**设计依据**：design.md §2.3 / §2.4 / §2.5 / §0 裁决 2/3/7/8
**文件面**：`src/sr_od/application/currency_war/kernel/cw_ore_reward.py`（新）、`kernel/cw_action_report/collect_ore.py`、`sim/cw_sim_actions.py`；测试仓对应测试文件
**依赖**：3.1
**优先级建议**：5
**完成判据**：
- 三分支写序锁：行序列 / 每行来源（rand/logic 依 §2.4 表）/ evidence 词表逐行断言
- 角色分支触发合成：bench/行域逐步多行同组、evidence `proj_ore_merge#N` 递增、board 派生行随行继承 rand
- 未抽中域标记行：值不变、来源 `logic_rand`；等值观察后静默翻回 observation、零流水缺陷行；差异观察出 `logic_rand_outcome`
- 拒分支：bench 无空位 → `bench_full_no_open` 零写；level 缺读 → `level_unread` 零写（均先于 spheres 摘除）
- 采样器支撑集锁：gold ∈ 1..5、equip ∈ 简易池全集、char ∈ `chars_by_cost`（按注入 rng 定种子断言）
- sim 分支：CollectOre 委托携带流键 rng（桩记录）
- 既有 collect_ore 相关测试更新至新写序；§12 通用工程门（ruff + L1 绿）
**验收凭据形式**：测试名 + 命令复跑（同上，另加采样器单测）

## 3.3 正本更新 + 全量验证
**范围**：按「正本更新清单」逐条更新正本；L3 全量。
**设计依据**：本文件「正本更新清单」节 + design.md §2.1 采样语义
**文件面**：清单所列正本文档与代码注释
**依赖**：3.1、3.2
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致（无「无可写口径禁走本口编值」类旧口径残留）；`uv run pytest sr-od-test/ -m "not slow"` 全量绿
**验收凭据形式**：文档对照 review + 全量命令复跑

## 正本更新清单
- `docs/develop/sr_od/application/currency_war/game_state/fields.md` §2.1（logic_rand 定义改采样语义三形态）、§2.3（旁路措辞补采样）、§2.5（「无可写口径禁走本口编值」改采样口径）← 3.1/3.2
- `docs/develop/sr_od/application/currency_war/game_state/action-logic-state.md` §1.1（两态制段补采样）、§1.2（随机面两档落法改写为采样语义）← 3.2
- `docs/develop/sr_od/application/currency_war/game_state/README.md` §3.1（write_logic_rand 行改采样语义）← 3.2
- `docs/develop/sr_od/application/currency_war/game_state/logic-updates/collect-ore.md`（点晶矿新写序：守卫/三分支/逐步行/标记集/假设档披露）← 3.2
- `src/sr_od/application/currency_war/kernel/cw_game_state.py` 模块 docstring「逻辑随机态」段 ← 3.1
- `src/sr_od/application/currency_war/kernel/cw_projection_audit.py` `gold` 行已知缺口措辞（晶矿随机金改走随机态；投资卡授予缺口措辞保留）← 3.2
- `docs/game/currency_war/research/` 晶矿掉落规则补档（金 1–5 / 简易池 / 概率表，证据分级 = 用户口述 2026-09-20；归入在册晶矿/奖励相关篇或新建）← 3.3
