# logic-rand-sampling 落地

## 3.1 内核写面（merge 步回调 + board 继承 + 污染判定口）
**范围**：design.md §2.2 四项——① `_merge_bench` 可选步回调 `on_step`（缺省 None = 现行为）；② `_write_logic_frame` 行域写为随机态时 board 派生写继承 `logic_rand`；③ `GameState.any_logic_rand(field_names)` 读口；④ `write_logic_rand` 与模块 docstring「逻辑随机态」段的采样语义修订。边界：不动 collect_ore、不动买牌行为路径、不动 observe() 旁路。
**设计依据**：design.md §2.2 / §2.1
**文件面**：`src/sr_od/application/currency_war/kernel/cw_merge_simulate.py`、`src/sr_od/application/currency_war/kernel/cw_game_state.py`；测试仓对应测试文件
**依赖**：无
**优先级建议**：5
**完成判据**：
- `on_step` 缺省零行为：既有全量（含买牌投影直锁 `test_cw_shop_projection_logic`）绿
- 步回调触发次数 = 合并级数（连锁两级 = 2 次调用，行为锁）；回调后调用侧按「受该级影响域各落一行」写（bench+行域双域变更 = 两行同号，行为锁）
- 行域 `write_logic_rand` 后 board 派生行 `source == 'logic_rand'`；行域 `write_logic` 后 board 仍 logic（回归腿）
- `any_logic_rand` 真值表（空集/含 rand/全非 rand）
- `_write_logic_frame` docstring「board 恒走 write_logic 不随行域随机态扩散」句与 `_resync_board_delta` docstring 写入口指针同步修订（与行为一致，禁注释打架）
- §12 通用工程门（ruff 改动文件 + L1 快速集绿）
**验收凭据形式**：测试名 + 命令复跑（`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`）

## 3.2 采样器 + 点晶矿上报改造 + sim 接线
**范围**：design.md §2.3–§2.5——`kernel/cw_ore_reward.py` 采样器（roll_ore_reward + `ORE_ASSUMPTION_KEYS` 披露表 + 假设档披露键 §0.1）；`collect_ore.py` 重写（逐点顺序推演：守卫/独立采样/逐步写/未抽中域标记/角色分支合成链逐步行/None 域边界/席满即该点无效，深拷贝防别名）；sim 引擎前置分派新增 `_apply_collect_ore`（炉先例旁路直调，`eng.ore_uses` 计数，流键 `M1x/ore/{uses}`）。边界：其他动作零改动（apply_player_action 主表不动）、策略器零改动、晶矿识别读链零改动。
**设计依据**：design.md §2.3 / §2.4 / §2.5 / §0 裁决 2/3/7/8 / §0.1
**文件面**：`src/sr_od/application/currency_war/kernel/cw_ore_reward.py`（新）、`kernel/cw_action_report/collect_ore.py`、`sim/cw_sim_engine.py`；测试仓对应测试文件
**依赖**：3.1
**优先级建议**：5
**完成判据**：
- 多点逐点锁：批载荷 N 点 → 逐点独立采样与写行、evidence 点序 `#ore<k>` 递增、同组 group_id
- 席满即止锁：前点角色耗掉空位后，后续点晶矿留在 spheres（不摘除不采样），已开点照常入账
- 三分支写序锁：行序列 / 每行来源（rand/logic 依 §2.4 表）/ evidence 词表逐行断言
- 角色分支触发合成：受影响域各落一行（双域变更 = 两行同号）、evidence `proj_ore_merge#<级>#ore<k>`、board 派生行随行继承 rand
- None 边界锁：None 域跳写不标记；抽中域 None 跳采样写；bench 未观察整批拒 `'bench_unobserved'`
- 拒分支：level 缺读 → `'level_unread'` 整批拒（先于任何写）
- 观察收口锁：等值观察静默翻回 observation、零缺陷行；差异观察出 `logic_rand_outcome`
- 采样器支撑集锁：gold ∈ 1..5、equip ∈ 简易池全集、char ∈ `chars_by_cost`（按注入 rng 定种子断言）；`ORE_ASSUMPTION_KEYS` 与 §0.1 表键名一致
- sim 接线锁：前置分派拦截 CollectOre、`eng.ore_uses` 拒分支不耗序、流键 `M1x/ore/{uses}`、apply_player_action 主表零改动
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
- `docs/develop/sr_od/application/currency_war/game_state/fields.md` §4.2 ClickSpheres（「记录层面=不改席占位、全部等后续观察覆盖」改采样+标记+逐步写新形态）← 3.2
- `docs/develop/sr_od/application/currency_war/game_state/action-logic-state.md` §1.1（两态制段补采样）、§1.2（随机面两档落法改写为采样语义）、§3.6 ClickSpheres（同 §4.2 口径改写）← 3.2
- `docs/develop/sr_od/application/currency_war/game_state/README.md` §3.1（write_logic_rand 行改采样语义）← 3.2
- `docs/develop/sr_od/application/currency_war/game_state/logic-updates/collect-ore.md`（点晶矿新写序：逐点推演/守卫/三分支/逐步行/标记集/None 边界/假设档披露）← 3.2
- `src/sr_od/application/currency_war/kernel/cw_game_state.py` 模块 docstring「逻辑随机态」段 ← 3.1
- `src/sr_od/application/currency_war/kernel/cw_projection_audit.py` `gold` 行已知缺口措辞（晶矿随机金改走随机态；投资卡授予缺口措辞保留）← 3.2
- `docs/game/currency_war/research/sphere_rewards.md`（新建，晶矿掉落规则篇：临时建模口径 v0 + 在册冲突调和 + 假设档与披露键 + 校准状态；证据分级 = 用户临时拍定 2026-09-20，非核实游戏事实，待采集数据校准）← 3.3
