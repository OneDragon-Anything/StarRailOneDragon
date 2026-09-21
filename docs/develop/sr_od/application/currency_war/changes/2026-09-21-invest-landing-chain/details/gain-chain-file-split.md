# 获得链模块拆文件(详设)

## 问题与约束

- 边界:本篇只管 `kernel/cw_gain_chain.py` 的文件拆分;原语/回调的语义契约(总纲 §2.4)不变,拆分 = 零行为(纯搬家 + import 面)。
- 现状:573 行单文件(gain-chain 迭代产物),承载:链内工作池/单级合成(`_WorkPool`/`merge_step_once` 等)、三原语、三枚举回调、`GainOutcome`、defect kind。本迭代扩员装入:「获得投资策略」原语 + `on_strategy_gained` 回调 + `PICK_INVEST_EFFECTS` 效果表 + 骇客采样池(自上报包迁入,~+200 行)→ 单文件 ~800 行。
- 后续增长主力 = **效果面**:`on_character_gained` 收敛点(新触发型效果核实后加分支)、效果表扩员(新策略卡核实);过程面(原语/合成/回调枚举骨架)形态已齐、稳定。用户判断:该文件后续也会很大,设计拆文件。
- 约束:①kernel 惯例 = 平铺模块(包先例仅 cw_screen_report/cw_action_report 两个上报族);②「`__init__.py` 默认不暴露模块」(项目 AGENTS.md §7);③消费方 import 面改动最小;④效果函数体要调链原语、`on_strategy_gained`(链)要查效果表——存在天然双向需求,拆文件必须破环。

## 方案

**平铺拆两模块,边界 = 过程语义 ∥ 效果内容**:

| 模块 | 装什么 | 增长预期 |
|---|---|---|
| `kernel/cw_gain_chain.py`(保留现名,消费方 import 零改动) | `GAIN_CHAIN_PRODUCER`/defect kind 常量/`JOY_PROVISIONAL_KIND`/`GainOutcome`/链内工作池与单级合成(`_entry_ident`/`_entry_equips`/`_bump_carrier`/`merge_step_once`/`_slot_sig`/`_dep_sig`/`_WorkPool`/`_build_pool`/`_overflow_occupied`/`_write_merge_step`/`_ChainAcc`/`_gain_character_core`)/四原语(`gain_invest_env`/`gain_character`/`gain_equipment`/`gain_invest_strategy`)/四枚举回调骨架(`on_env_gained`/`on_character_gained`/`on_equipment_gained`/`on_strategy_gained`——枚举与分派在链,查表)。表未逐名穷举的其余 `_` 前缀链内私有助手随过程面同迁、不出链模块 | 稳定(~450 行量级) |
| `kernel/cw_gain_effects.py`(新) | 骇客采样池(`HACKER_MOD_POOL_V0`/`HACKER_MOD_ASSUMPTION_KEYS`/`roll_hacker_mod`/`_HACKER_MARK_DOMAINS`/`_HACKER_BENCH_GRANT`)/效果函数体(`_apply_effect_hacker_wolf`)/效果注册表 `PICK_INVEST_EFFECTS` | 随效果核实扩员(主增长面) |

**import 方向(单向,环破除)**:

- `cw_gain_chain` →(模块级)→ `cw_gain_effects`:`from cw_gain_effects import PICK_INVEST_EFFECTS`(`on_strategy_gained` 查表用);
- `cw_gain_effects` →(**函数体内惰性**)→ `cw_gain_chain`:效果体调 `gain_character`/`gain_equipment`/`gain_invest_env` 原语在函数运行时 import。

环安全性:两模块任一加载序都无初始化死锁——先加载 chain:chain 模块级加载 effects(其模块级零 chain import)→ effects 完成 → chain 完成;effects 运行时惰性 import 已完成的 chain。先加载 effects:其模块级零 chain import → 完成;运行时 import chain → chain 模块级 import effects(sys.modules 命中,已完成)→ chain 完成。依据 = Python import 机制(模块级 import 需对方初始化完成,函数内运行时 import 无此约束);项目惰性 import 纪律先例 = `cw_effect_inventory.py` 大量函数内 import 及其注释「game_state_of 运行期函数内 import:GameState 容器模块头反向 import 本模块…保持本函数可离线单测(惰性纪律)」。

## 关键取舍

- **否决:包化(`kernel/cw_gain_chain/` 四文件 primitives/merge/callbacks/effects)**。理由:①过程面(primitives/merge/callbacks)形态稳定不增长,按它切包是给稳定面付包管理成本;②包化把全部消费方 import 路径改写,或引入 `__init__` 暴露面(项目约束 `__init__` 不暴露模块);③callbacks 与 primitives 互调(原语触发回调、回调递归原语)拆开即成模块级双向依赖,环破除成本比两模块方案更高(两方案都靠惰性 import,但包化要在 3 处用,两模块方案只 1 处)。
- **否决:效果表原地留在上报包**。链要查表 = 反向 import 上报包,包依赖方向禁止(上报包 → kernel 单向)。
- **否决:`on_strategy_gained` 连同效果表一起搬 effects**。回调枚举收敛点必须在链模块(gain-chain.md §3 裁定②「枚举即收敛」;分裂 = 未来 on_character_gained 扩员时两个家)。
- 演进路径:若 `on_character_gained` 未来大量扩员,效果体已全在 `cw_gain_effects`,链模块停留稳定量级,届时再评估;本批不预留空目录。
