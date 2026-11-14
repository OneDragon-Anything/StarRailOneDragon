# 投资域 v4.7 数据层重建 迭代设计（总纲）

## 0. 元信息

- 迭代目标：货币战争投资策略/投资环境的 base 数据与人工建模层的键空间、存活卡数值对齐 plaza API V4.7（S2「入画奇航」换赛季）。用户裁定（2026-11-13 会话）：「能做的先做，不能做的后续再适配」——本迭代只做**数据层能做的**，建模登记等实机流程摸底后另行适配。
- 状态：定稿（三轮对抗收敛：A1-A8 + R1-R3 共 11 条发现全部闭环，报告 = attack.md）
- 文档清单：
  - `details/orphan_scan.txt` —— overlay 孤儿登记键清单（V1，dict 表面、退场名集未剔同名复活；[EQUIPMENTS] 段为扫描器误报，处置见 §1 不解决 6；本附件仅存档，执行以 v3 为准）
  - `details/design_scan_v2.txt` —— 修订扫描（元组名单增删清单/例外表退场键/同名存活具名触点/补遗级联/套组派生依赖）
  - `details/design_scan_v3.txt` —— 同名复活切割扫描（§2.3-A 组执行清单单一源：净退场名集/三表剔除逐名名单/修正后逐表键数/DELAYED 孤儿核实）
  - `details/touchpoint_scan.txt` —— 24 条效果变卡的 overlay 触点行号 + 测试仓/正本区引用面统计

## 1. 问题与动机

- 现状症状（依据 = plaza config V4.7 缓存 `.debug/game_data/currency_war/plaza/config_v4.7.json` 与本迭代落盘对照分析 `.debug/game_data/currency_war/invest_v4.7.json` + `.debug/temp/cw_invest_v47/diff_v44_v47.md`）：
  1. base 层 `cw_invest_data.py` 停在 V4.4（策略 334 + 环境 83）；V4.7 官方全量为策略 298 + 环境 73：策略 +77/−113/存活 221 条中 24 条效果文本变（全为数值调整，零结构变化），环境 +37/−47/存活条目零文本漂移。
  2. 建模增量层 `cw_investments.py` 的 overlay 引用 id 级退场条目 160 个——其中 28 个名字被 V4.7 同名新卡复用（**同名复活卡**：S1 id 退场、V4.7 换 id 同名，其登记条目不删、按 §2.4-B 重审同步），净退场名 132。手维护面待删量 = **22 张 dict 登记表 211 键 + 1 张名字元组 `_ENV_SUFFIX_DERIVED_NAMES` 31 个 S1-only 名 + 补遗删除的 1 条级联条目**（清单 = details/design_scan_v3.txt）。base 更新后合并层孤儿守卫 import 即炸，执行序上第一道炸点 = `_build_strategies()` 内的 STRATEGY_ECONOMY 孤儿守卫（cw_investments.py L2952-2954，先于 STRATEGY_BINDINGS 守卫 L3298-3300 执行）。
  3. 24 条效果变卡的已登记建模数值过期（如成长基金 40→36 金），sim/策略层会按旧值算错账。
  4. 同名跨赛季存活卡的具名登记（发放物/绑定）内容过期——其中同名复活卡（id 换代）内容可疑度最高，如「追击星徽套组」S1 发放『飞霄』、V4.7 卡文为『托帕&账账』。重审面合计 **66 触点**（STRATEGY_GRANTS 35 + STRATEGY_DELAYED_GRANTS 11 + _STRATEGY_BINDINGS_EXPLICIT 9 + ENV_GIFTS 11；其中 36 键为同名复活卡条目——从 §2.3-A 删除清单剔除、保留条目强制重审，30 键为同 id 存活卡条目——轻量核对；逐名列 = details/design_scan_v3.txt §A + details/design_scan_v2.txt §C，处置规则 = §2.4-B）。
  5. 星徽套组绑定派生 `_derive_megastar_set_bindings()`（cw_investments.py L3270-3291）对注册表内每张 `星徽套组` 卡强制要求 `_STRATEGY_BINDINGS_EXPLICIT` 存在对应单件条目（缺失 raise）；V4.7 base 有 20 张套组卡，其中 12 张的单件 explicit 缺失（details/design_scan_v2.txt §E）——不补条目则 import 必炸，这是「挂账不登记」边界的强制例外（处置 = §2.3-C）。
- 根因归层：语义层——游戏版本换代（S1→S2 官方数据集换血），非代码缺陷。数据层版本锚定更新 + 派生机制的最小名单维护，无架构改动。
- 解决到哪：base 重建为 V4.7 全量；overlay 键空间对齐（退场键清除 + 派生名单重写 + 派生依赖补齐）；存活卡已登记面数值/发放物/文本镜像与 V4.7 官方文本对齐。
- **明确不解决**（挂账，等实机流程摸底后的建模期适配，防止范围外溢）：
  1. 新增 77 策略 + 37 环境的**效果建模登记**（期货族/发放族/战斗自算面等——通道大多已有先例，登记属建模判断，用户裁定等实机摸底；未登记卡在选卡评估中无分，是可接受中间态）。§2.3-C 的星徽单件绑定条目是防炸的机械事实登记（阵营 = 星徽名去尾、角色 = 官方卡文直读，零效果判断），不属于本项；V4.7 新增的非后缀环境分类同样不登记（`_build_envs` 对未登记分类落「未分类」默认值，cw_investments.py L2964，不炸）。
  2. 四个新系统域建模：主角光环域（片场解散/换角开演/刷新连锁/提前登场/光环采购——光环刷新是新金币消费点，交互画面未建档）、奇美能量+商店升级（奇美成长记，机制未知）、开拓力/列车（全速开拓，机制未知）、装备出售（装备变现，执行层新动作）。
  3. 决策层新约束建模：终身雇佣（板面锁定）、扩张的代价（策略卡源团队上限）、人才大礼包族（招募保底改写）。
  4. 建模知识文档版本重写：`docs/game/currency_war/research/invest_effects.md`（人工维护的建模分类知识，V4.4 基准）、strategy-docs 28/29 号稿的选卡评序。
  5. 正本区先例叙述的退场卡引用清扫（details/touchpoint_scan.txt §C 命中 49 文件——多为「首例/先例」机制叙述，机制代码仍在，挂建模期统一重审；仅「全量 N 条」计数型引用随本迭代修正，清单见 landing.md 正本更新清单）。
  6. `cw_equipment_data.EQUIPMENTS`——orphan_scan V1 的 [EQUIPMENTS] 8 键段为**扫描器误报**（扫描器遍历 `cw_investments` 模块命名空间时把跨模块 import 进来的装备注册表也纳入匹配，8 个命中键是装备名与 S1 投资卡名的同名碰撞，装备本体在 V4.7 均存活）——本迭代不辖装备注册表（归 `2026-11-13-cw-equip-v47-adaptation` 迭代），orphan_scan.txt V1 附件不更新该段，以本节声明为准。
  7. cw_investments.py 注释中存量 `cw_invest_data.py:NNN` 行号引用（base 重生成后行号漂移）——行号引用本属存量注释债，挂注释收敛批；本迭代触点条目不新增行号引用。

## 2. 方案

### 2.1 生成器落点修正（单产物化）

`skills/sr-od-dev-currency-war/scripts/gen_plaza_invest.py` 删除人读版文档产出（`DOC_MD` 常量、`render_doc()`、main 中写盘与输出行），头注释同步。依据：
- `DOC_MD` 目标 `docs/game/currency_war/data/invest_cards.md` 已废弃——文件不存在；`cw_invest_data.py` 头注释（L3）声明「原同源生成表格已删」，现行人工维护的人读版 = `docs/game/currency_war/research/invest_effects.md`（建模分类知识，非生成器产物）。
- 不修正则 base 重建阶段会在 `docs/game/currency_war/data/` 复活一个已删除的文件形态。
- 同文件在本会话早前的在飞改动 `CACHE_GLOB`（`.debug/temp/`→`.debug/game_data/`，落点迁移的收尾）随本阶段一并入库。
- 生成器自带 diff 报告逻辑保留（`diff_report()` 对比旧 data 文件打印新增/移除/效果变，是 3.2 的核对凭据）。

### 2.2 base 数据层重建

重跑 `uv run python skills/sr-od-dev-currency-war/scripts/gen_plaza_invest.py --cache`（用 V4.7 config 缓存），产出 `cw_invest_data.py` V4.7（策略 298 + 环境 73）。canon 归一与富文本清洗逻辑不变（`•`→`·`、全角→半角、`{NICKNAME}`→「开拓者」等，规则见生成器 docstring）。核对凭据 = 生成器 diff 输出与本迭代 diff 分析一致（+77/−113/24 效果变/环境 +37/−47）。

### 2.3 overlay 孤儿清理与派生适配

**手维护面分类判据**（依据 = cw_investments.py 各表赋值形态；执行清单 = details/design_scan_v3.txt + design_scan_v2.txt）：

**退场名集判据（R1 修正）**：退场名 = id 级退场 且 名字 ∉ V4.7 存活名——净 132 名。S1 id 退场但 V4.7 有同名新卡的 28 个**同名复活名**不属退场（design_scan_v3.txt 顶部逐名列），其登记条目**不删**、按 §2.4-B 重审同步；同名复活键 ∩ 具名登记表 = 36 键（GRANTS 16 + EXPLICIT 9 + ENV_GIFTS 11，design_scan_v3.txt §A 逐名列），已从下方 A 组数字中剔除。

- **A 组·dict 登记表（删孤儿键，211 键）**：`STRATEGY_ECONOMY`(11)、`STRATEGY_EFFECTS`(19)、`_STRATEGY_BINDINGS_EXPLICIT`(57)、`_STRATEGY_GRANTS_SCAN_EXCLUSIONS`(3)、`STRATEGY_GRANTS`(71)、`ENV_GIFTS`(26)、`STRATEGY_DELAYED_GRANTS`(3)、`STRATEGY_DELAYED_OFFERS`(2)、`STRATEGY_MERGE_GRANTS`(2)、`ENV_MERGE_GRANTS`(1)、`ENV_INTEREST_GRANTS`(1)、`ENV_BATTLE_GRANTS`(1)、`ENV_DELAYED_ITEM_GRANTS`(1)、`STRATEGY_BENCH_LEAVE_GOLD_GRANTS`(1)、`STRATEGY_EQUIP_COUNT_XP_GRANTS`(1)、`STRATEGY_FACTION_COUNT_GRANTS`(1)、`STRATEGY_PERFECT_RESCUE_GRANTS`(1)、`STRATEGY_PLANE_BOSS_GRANTS`(1)、`STRATEGY_PLANE_START_CHAR_GRANTS`(1)、`STRATEGY_REWARD_NODE_GRANTS`(1)、`_ENV_CATEGORY_EXCEPTIONS`(5)、`_ENV_FACTION_EXCEPTIONS`(1)。
- **B 组·名字元组（按 V4.7 名单重写）**：`_ENV_SUFFIX_DERIVED_NAMES`（L2875-2888，ENV_CATEGORY/ENV_FACTION 的派生真源——派生函数遍历本元组而非 base，cw_investments.py L2912-2927）：删 31 个 S1-only 名、保留 11 个跨赛季存活名、追加 21 个 V4.7 新后缀名（逐名列 = design_scan_v2.txt §A）。V4.7 后缀环境实有 32 名（概念股族 15——含 id 1015 同名环境、邀请族 18；R3 修正：非「19+19」）；重写后元组 = 42 − 31 + 21 = 32 名，与 V4.7 后缀环境一一对应。**同名覆盖披露**：官方 33 张后缀环境卡有 32 个独立 canon 名（「群攻概念股」id 1015/2208 同名双 id），注册表按 canon 名键空间取一名（元组段注释声明），两版本文本差异与覆盖方向裁归建模期（挂账）；环境注册表键数 = 72 非 73。重写后元组语义不变：仅收「概念股/邀请/契约」三类后缀环境名；V4.7 无契约族 → 契约段为空。
- **C 组·星徽套组派生依赖（补 20 条单件 explicit 绑定）**：V4.7 base 的 20 张 `X星徽套组` 卡在 `_derive_megastar_set_bindings()` 派生时逐张查 `_STRATEGY_BINDINGS_EXPLICIT['X星徽']`，缺失即 raise（L3287-3289）。20 张单件卡（8 张跨赛季存活 + 12 张 V4.7 新增）全部按 **机械事实** 登记绑定条目：阵营绑定 = 星徽名去「星徽」尾（官方语义「星徽装备者加入【X】羁绊」，星徽名与羁绊名一一对应）；角色绑定 = V4.7 官方卡文「和1个【角色名】」直读。**依据与边界**：绑定内容为官方卡文机械直读，零效果建模判断——它不是 §1 不解决 1 的效果登记豁免，而是派生机制强制的最小事实登记；「阵营绑定进选卡方向分」的行为效应归建模期复核（登记时条目旁注释声明此边界）。8 张存活单件的既有条目内容按 V4.7 卡文重审（旧内容可能过期，见 §2.4-B）。
- **D 组·补遗（删 1 条 + 级联 1 条）**：`_MANUAL_EXTRAS` 的「追击星徽套组(二)」(id 6302) 删——依据：该条目是 S1 plaza 双卡缺陷的补录（同效果卡 plaza 只收一张，cw_investments.py L2935 注释自证）；V4.7 plaza 已改为单张形态且 id 6302 ∉ V4.7 base（补遗条目若保留将触发 `_build_strategies` 的 setdefault 合入后无 base 对应物）。**级联**：`STRATEGY_GRANTS['追击星徽套组(二)']`（L4330）随补遗删除同步删（删补遗后该键不在注册表 → STRATEGY_GRANTS 孤儿守卫炸）。
- **E 组·反扫闭集守卫的直读发放补登记（裁定 2026-11-13，落地期设计扩充）**：`_validate_strategy_grants` 反扫闭集守卫（效果文本含「获得…角色名」直读候选 ⊆ `STRATEGY_GRANTS` ∪ 记因排除表）在 V4.7 base 换血后暴露 27 张未登记直读发放卡（24 星徽系单件/套组对 + 欢愉星徽套组直读形态 + 伙伴总动员 + 奇美成长记）。处置 = 全量补登记 `chars_immediate=(V4.7 卡文角色名,)`——与 C 组同构的防炸机械事实登记（卡文直读、零效果建模判断，不挂 economy、估值无分，不越 §1 不解决 1 的红线）；伙伴总动员注释声明佩佩=系统单位挂账建模期、奇美成长记注释声明奇美能量域未建模挂账；卡文装备半句（星徽/进阶装备）不在 GRANTS 辖域不登记。GRANTS 终态 62 = 107 − 71(A 组) − 1(D 组级联) + 27。设计期未预见的根因：v2/v3 扫描均在 V4.4 base 下跑（守卫当时闭合），机械验证链初版漏列反扫守卫——落地首验即暴露，防线语义保持完整。
- **派生表（不手删，自动跟随）**：`INVESTMENT_STRATEGIES`/`INVESTMENT_ENVS`（`_build_strategies()`/`_build_envs()` 构建，L2975-2976）、`ENV_CATEGORY`/`ENV_FACTION`（`_derive_env_tables()` 派生，L2930）、`STRATEGY_BINDINGS`（派生 + 合并，L3294-3297）。
- **不碰**：`cw_equipment_data.EQUIPMENTS`（§1 不解决 6，扫描误报）。

**删除手法**：
- 按键删整个条目语句块（dict 键行至块结束的逗号/右括号），条目**紧邻且专属**的注释行（紧贴键行上方、内容只讲该卡的注释）随块删除；分节注释（`# ===== ... =====` 或多卡共享的段落头）保留。边界判据：一条注释被两条以上卡条目共享 = 共享注释，不删。
- 策略名与环境名在登记键空间不重叠（canon 名唯一），但删除时按「键名 + 所在表辖域」（STRATEGY_* 只辖策略、ENV_* 只辖环境）双确认，防同名误删。

**机械验证链**（完成判据，全部满足才算删净）：
1. `import cw_investments` 成功——`_build_strategies` STRATEGY_ECONOMY 孤儿守卫（L2952）、`_build_envs` ENV 孤儿守卫（L2969）、`_derive_env_tables` 不可派生 KeyError（L2926）、`_derive_megastar_set_bindings` 缺单件 raise（L3288）、`STRATEGY_BINDINGS` 孤儿守卫（L3298）全部通过；
2. 重跑 v3 扫描（`.debug/temp/cw_invest_v47/scan_design_v3.py`）：§B 逐表键数与 §2.3-A 组清单一致且清理后各表归零——注（N1）：v3 §B 汇总行「合计 481」含 5 张派生表（96/36/32/36/70 = 270 键）的归零核验信息行，A 组执行口径 = 22 张手维护 dict 表 211 键；重跑 v2 扫描（`.debug/temp/cw_invest_v47/scan_design_v2.py`）§A「删」清零、§D 级联清零、§E 20 套组单件 explicit 全有；
3. 逐表键数对账：清理后源表键数 = 清理前键数 − 该表 A 组退场键数（防误删存活键与 §2.4-B 保留键；清理前键数清理时实测记录）。

### 2.4 存活卡数值与具名内容重审

**A 部分·24 条效果变对照表**（依据 = details/touchpoint_scan.txt §A 触点行号；效果原文核对源 = `.debug/game_data/currency_war/invest_v4.7.json`）。边界判据：只改「已有登记触点」的数值与文本镜像；未建模面**不新增登记**（挂账建模期，见 §1 不解决 1）。

| # | 卡(id) | 文本变 | 触点 | 动作 |
|---|---|---|---|---|
| 1 | 成长基金(101701) | 40→36 金 | STRATEGY_ECONOMY L785；STRATEGY_EFFECTS L1624 | `gold_at_level=40`→`36`；EffectSpec 的文本面若引旧文本同步 |
| 2 | 全员晋升(102701) | 扳手 2→3 | STRATEGY_EFFECTS L1043 | 条目无扳手面（未建模）→ 无字段动作；紧邻注释若引旧卡文同步 |
| 3 | 免费升舱(103901) | 删「立刻获得4金币」尾句 | STRATEGY_ECONOMY L752 | `EconomyEffect(instant_gold=4)` → `EconomyEffect()`（空值占位保留键） |
| 4 | 先亏后盈(130701) | hp −20→−10、delay 4→3 | STRATEGY_ECONOMY L828；STRATEGY_DELAYED_GRANTS L6744 | `hp_instant=-20`→`-10`；`delay_nodes=4`→`3` |
| 5 | 好运令牌·银(130901) | delay 3→6 | STRATEGY_DELAYED_GRANTS L6753 | `delay_nodes=3`→`6` |
| 6 | 完美开局(150501) | 关卡进度 40%→50% | STRATEGY_EFFECTS L1993 | `UnitBuffRef.effect_text` 同步 V4.7 原文 |
| 7 | 基层贡献(150701) | 3%→6%、2%→4% | STRATEGY_EFFECTS L2037 | effect_text 同步 |
| 8 | 延迟收益(200701) | 100→60 行动值 | STRATEGY_EFFECTS L2128 | effect_text 同步 |
| 9 | 大裁员(202101) | 免费刷 6→9 | STRATEGY_ECONOMY L731；STRATEGY_EFFECTS L1069 | `free_refresh_burst=6`→`9`；L1069 条目与紧邻注释引文（「获得6次免费刷新」）同步 |
| 10 | 大扩招(203101) | 16→10 金 | STRATEGY_ECONOMY L722 | `instant_gold=16`→`10` |
| 11 | 秘密典籍(230901) | 8→4 金 | STRATEGY_ECONOMY L745；STRATEGY_GRANTS L4443 | `instant_gold=8`→`4`；GRANTS 条目 `items_immediate=('星徽秘典',)` 与 V4.7 卡文核对（发放物未变 → 无动作，登记核对一致） |
| 12 | 秘密典籍+(230902) | 12→8 金 | STRATEGY_ECONOMY L744；STRATEGY_GRANTS L4447 | `instant_gold=12`→`8`；GRANTS 条目核对（V4.7 卡文发放物 = 星徽秘典 → 无动作，登记核对一致） |
| 13 | 好运令牌·金(231501) | 「1件随机简易装备」→「3金币」 | 无键命中（发放面 S1 起未建模） | 无动作；挂账建模期（新文本以 V4.7 base 为准） |
| 14 | 好运来(231601) | 尾句「2件随机简易装备」→「1件+3金币」 | STRATEGY_EQUIP_GAIN_CONVERSIONS L6186（改写规则本体不变） | 无字段动作；尾句发放面未建模挂账 |
| 15 | 人海战术(250101) | 10→15%、20→25% | STRATEGY_EFFECTS L2229 | effect_text 同步 |
| 16 | 中产阶级(250501) | 新增尾句「额外获得3金币」 | STRATEGY_EFFECTS L2281 | effect_text 同步；`instant_gold` 未建模**不新增**（挂账） |
| 17 | 三三三(250701) | 20%→25% | STRATEGY_EFFECTS L1309 | effect_text 同步 |
| 18 | 概率事件(300401) | 45%→50% | STRATEGY_ECONOMY L866；STRATEGY_EFFECTS L2423 | `refresh_free_chance=0.45`→`0.50`（消费侧期望折算注释若引 0.45 同步）；effect_text 同步 |
| 19 | 高效决策(301701) | 45s→50s | `STRATEGY_ECONOMY` L628（burst=9999 不变）；`cw_mismatch_policy.py` L72-92 六处 reason 字面量 | reason 文本「45s」→「50s」（机械字面同步，语义不变） |
| 20 | 控制规模(302901) | 40→32 金 | STRATEGY_ECONOMY L677 | `instant_gold=40`→`32`（level_cap_override=7、宝钻发放不变） |
| 21 | 幸运之子(350101) | 40%→60% | STRATEGY_EFFECTS L2560 | effect_text 同步 |
| 22 | 三五成群(350901) | 10%/50%→15%/65% | STRATEGY_EFFECTS L2656 | effect_text 同步 |
| 23 | 打通上下游·彩(351301) | 每节点 +3%→+4% | STRATEGY_EFFECTS L2704 | effect_text 同步 |
| 24 | 攻防一体(351601) | 25%→33%（措辞微调） | STRATEGY_EFFECTS L2752 | effect_text 同步 |

**B 部分·同名跨赛季存活卡的具名登记重审**（依据 = details/design_scan_v2.txt §C + details/design_scan_v3.txt §A；触点集合计 **66 键** = STRATEGY_GRANTS 35 + STRATEGY_DELAYED_GRANTS 11 + _STRATEGY_BINDINGS_EXPLICIT 9 + ENV_GIFTS 11）。分层构成：36 键为**同名复活卡**条目（design_scan_v3.txt §A 逐名列——已从 §2.3-A 删除清单剔除，条目保留、强制重审）；30 键为**同 id 存活卡**条目（本不在删除清单，轻量核对）。处置规则（逐条机械对照，非建模判断）：
- 对照源 = V4.7 base 官方卡文（invest_v4.7.json）；发放物名单（chars_immediate/items_immediate/延时发放物）与绑定内容（阵营/角色）逐条与卡文直读比对。
- 不一致 → 按卡文直读同步（例：「追击星徽套组」GRANTS `chars_immediate=('飞霄',)` → V4.7 卡文『托帕&账账』）；一致 → 登记核对一致（条目不改）。
- 卡文无法直读的形态（如发放概率/条件发放语义）→ 保持原样并条目旁注释声明挂账（禁猜）。名单型新卡文角色（如『托帕&账账』）按卡文字面登记。
- ENV_GIFTS 11 键的发放物 = 星徽道具名，道具在 V4.7 装备注册表全部同名存活（对抗复审实证）——对照与同步仅涉道具名与 V4.7 卡文的一致性，不涉装备注册表。
- 范围红线：本部分只辖「名单/绑定内容」与官方文本的对齐，不新增登记面、不做效果建模。

**注释同步规则**：触点条目的紧邻注释若引用旧官方卡文（引号原文或行内数值），随 V4.7 新官方文本同步；非触点条目注释一律不动（挂 §1 不解决 7）。`effect_text` 镜像的同步以 invest_v4.7.json 的 V4.7 官方原文为准，逐字复制，不手工改写。

### 2.5 测试判断准则

范围 = `sr-od-test/test/sr_od/application/currency_war/`（details/touchpoint_scan.txt §B：退场∪24 卡引号形命中 186 文件，为量级参考非逐个必改清单）。逐个判断分类处置：

- **a. 断言旧版本数据值**（期望值 = V4.4 官方值）：按 §2.4 对照表 / V4.7 官方值更新期望（数据换版本是合法变更，依据 = plaza V4.7 官方 config）。
- **b. fixture/断言引用退场卡名**，按测试目标分：
  - 测试目标 = 注册表数据（卡存在性/键集/评序表）→ 更新为 V4.7 等价卡或删用例；
  - 测试目标 = 机制桥函数（发放桥/check 函数——本迭代不删机制代码，只删登记键）→ fixture 与注册表解耦（测试内直接构造 payload/条目，不查注册表），保持锁机制行为。依据：机制桥是活代码（后续赛季可复用），其行为语义未变。
  - 已知大块 fixture 面：`sr-od-test/.../faction_migration_snapshots.json` 等迁移快照类 fixture（details/touchpoint_scan.txt §B 未单独列出，测试修复阶段按本规则处置——快照锁的是 S1 数据集，按 a 类换 V4.7 基准重生成或按 b 类解耦）。
- **c. 守卫测试**（孤儿校验/键集一致性/BENCH_ITEM_KINDS 闭集等）应自动跟随——红 = 3.3 清理有漏或派生逻辑异常，回修 src 不改期望。
- **d. 主分支存量旧红 2 个**（卖出候选序断言）不碰、不计入本批判据；登记依据 = `.debug/progress/CW跨迭代挂账.md`（存量旧红挂账行），红名单载体 = 该挂账板。
- 全部改动文件 `ruff check` 通过；测试仓同步改动随本迭代提交。

### 2.6 提交切分

每阶段独立 commit（逐文件点名 add）：3.1 生成器修正 → 3.2 base 重建 → 3.3 孤儿清理与派生适配 → 3.4 数值与具名内容重审 → 3.5 测试修复（可按红点簇拆多个 commit）→ 正本更新。
