# 投资环境选择决策升级 落地

> 阶段唯一源纪律：本文件 = 账本阶段唯一源；设计改 → 本文件改 → 账本跟着改，禁两处各自演化。
> 通用工程门 = od-dev-progress-tracking §12（含 `ruff check` 仅改动文件、测试纪律；各阶段完成判据统一引用，不逐条复述）。
> 符号锚纪律：行号随代码漂移，一律以符号为准；各段批首按符号 grep 复核一次。
> 在飞互斥总注：`kernel/cw_events.py`（3.1/3.5）、`kernel/cw_comps.py`（3.1/3.4）与统一 state 迁移在飞面（账本 T-96 cw_events 容器切换 / T-109 cw_comps 中间态收尾）及兄弟迭代 `2026-09-12-strategy-universe-gate` 3.2（cw_events/cw_comps）同文件——同文件阶段互斥、编排者排序，禁并行。

## 3.1 候选全集门 + 单帧锁

**范围**：`kernel/cw_comps.py` 新增 `candidate_faction_universe`（COMP_LIBRARY 派生 helper 区）；`kernel/cw_events.py` env 分支全集门（裸分支前置谓词 + `env-off-universe` 归因串 + 循环外全集单帧单读）；新建 `test_cw_env_universe.py`（U1-U6 + fixture 漂移断言）。边界：不含经济建模、不含送卡/品质改写型、不含正本更新。

**设计依据**：design.md §2.1（全集派生/落码面/正交性）/ §2.7 U1-U6

**文件面**：`src/sr_od/application/currency_war/kernel/cw_comps.py`、`src/sr_od/application/currency_war/kernel/cw_events.py`、`sr-od-test/test/sr_od/app/currency_war/test_cw_env_universe.py`（新建）

**依赖**：无（同文件在飞互斥见头注）

**优先级建议**：5

**完成判据**：
- U1-U6 全绿（行为对照 design.md §2.7 全集门锁表逐行）
- `test_cw_invest_refresh.py` 回归全绿
- §12 通用工程门（引用，不复述）

**验收凭据形式**：测试名清单（U1-U6 + 回归文件）+ ruff check

## 3.2 经济 schema + A 类精确通道 + 价值函数

**范围**：`kernel/cw_investments.py` 新增 `EnvEconomyEffect` schema + `ENV_ECONOMY` 表（A 类四条：增发货币/蓝海/成功经验/策略大师，白名单制 + 决策 3 六条防错装逐条对账记录）+ `InvestmentEnv.economy` 字段；新建 `kernel/cw_env_economy.py` 价值函数 `env_economy_value`（A 类精确部分 + 估算参数接口——B/C 参数 3.3 落表前按 resolved=False 消化缺参）。边界：不含 B/C 估值、不含品质改写分派、不含 decide_event 集成、不含登记端。

**设计依据**：design.md §2.2.2（schema）/ §2.2.3（价值函数）

**文件面**：`src/sr_od/application/currency_war/kernel/cw_investments.py`、`src/sr_od/application/currency_war/kernel/cw_env_economy.py`（新建）、`sr-od-test/test/sr_od/app/currency_war/test_cw_env_economy.py`（新建）

**依赖**：无（与 3.1 文件域不交，可并行）

**优先级建议**：5

**完成判据**：
- E1/E2 锁全绿（design.md §2.7 经济锁表）：精确通道估值、未入模恒 `(0, False)`、缺参 fail-closed（E2 构造按注入口径，design §2.7 表）
- `ENV_ECONOMY` 孤儿键校验 + 六条防错装对账记录（批报告内）
- §12 通用工程门（引用，不复述）

**验收凭据形式**：测试名清单 + ruff check

## 3.3 估算注册表 + B/C 类估值（数据批）

**范围**：对局档案遥测统计（位面到达率 / 刷新次数分布 / bonus node 扑满化增益），落 `ENV_ECONOMY_ESTIMATES`（逐参数值+CI+来源+截止）；`ENV_ECONOMY` 补 B 类两条（长线利好/二手市场）+ C 类两条（经济过热/经济严重过热）；fail-closed 门（design.md §2.2.4 参数级定义：CI 两端点下 `expected_gold > 0` 方向翻转 → resolved=False）；`ECON_VALUE_NORM` 按值域上界注册；轮岗/人才下沉「待建模」条目显式在册；增发货币晶矿开启机制实采项登记（design.md §2.2.1 假设登记行的验证项）。边界：不碰 decide_event。

**设计依据**：design.md §2.2.4（估算治理与参数清单）/ §2.2.1（B/C 条目与假设登记）

**文件面**：`src/sr_od/application/currency_war/kernel/cw_env_economy.py`、`src/sr_od/application/currency_war/kernel/cw_investments.py`、数据批脚本（`tools/cw/` 或 `.debug` 临时产物）、`sr-od-test/test/sr_od/app/currency_war/test_cw_env_economy.py`（增锁）

**依赖**：3.2

**优先级建议**：5

**完成判据**：
- 估算注册表逐参数落表（值/CI/来源/截止）+ 统计口径说明随批（样本量、滤波规则、π_offer 归一口径申报）
- E2 增补锁（CI 翻转 fail-closed）+ 轮岗/人才下沉「待建模」在册断言
- §12 通用工程门（引用，不复述）

**验收凭据形式**：注册表落表对照 + 数据批口径文档 + 测试名清单

## 3.4 送卡型结构（GiftGrant/ENV_GIFTS/角色全集）

**范围**：`kernel/cw_investments.py` 新增 `GiftGrant` + `ENV_GIFTS` 白名单表（11 条，效果原文对账 id 125-129/1201/1202/141/142/143/148）+ 构建期断言 `ENV_GIFTS ∩ ENV_ECONOMY = ∅`（与 `ENV_POOL_REWRITE` 的互斥断言由 3.6 建表时收全）+ 孤儿键/角色名漂移 import 校验；`kernel/cw_comps.py` 新增 `candidate_char_universe` + `gift_hit_tier`（全集派生 helper 区，跨迭代单一源声明见 design.md §1.3-2）；新建 `test_cw_env_gift.py`（G1 分档表直调锁 + G2 失格门构造锁 + G8 互斥断言半边）。边界：不碰 `cw_events.py`（消费支归 3.5）。

**设计依据**：details/env-value-models.md §2.1.1（语义盘点）/ §2.1.2（估值形态与档位阶梯）/ §2.1.3（结构与落码面）

**文件面**：`src/sr_od/application/currency_war/kernel/cw_investments.py`、`src/sr_od/application/currency_war/kernel/cw_comps.py`、`sr-od-test/test/sr_od/app/currency_war/test_cw_env_gift.py`（新建）

**依赖**：3.1（helper 同区与全集机器先落）；同文件在飞互斥见头注

**优先级建议**：5

**完成判据**：
- G1/G2 锁全绿：11 条逐条档位 = 详设 §2.1.2 落点表（含量子同频契约=shared 条件降档；公司契约按 faction 门击杀不发档位断言，仅作 gift_hit_tier=core 机器对账行）+ G2 失格门行为
- 构建期断言（孤儿键/角色名漂移/∩ENV_ECONOMY）import 炸验证
- §12 通用工程门（引用，不复述）

**验收凭据形式**：测试名清单 + ruff check

## 3.5 env 分支汇合集成（含环境刷新判据 kernel 侧）

**范围**：env 分支按 design.md §2.3 次序汇合——全集门（3.1 产物）+ 裸分 + **送卡静态档 max() 消费支**（`ENV_GIFTS`/`gift_hit_tier` 消费，`gift-core`/`gift-shared`/`advisor-core`/`env-gift-off-universe` 归因串）+ 经济域带（`ECON_ENGINE_BAND_BASE/SPAN` 复用、`env-econ` 归因串、`ECON_VALUE_NORM` 归一）+ 阵营 floor + steering 的最终次序对拍；E3/E4 联合锁、G3-G7 消费锁；**环境刷新判据 kernel 侧**（design.md §2.8：槽级顶级/零价值/被禁分类 + `refresh_slots` 产出，取代 F9 env 帧恒空规则；R1-R5 + R7 锁，落 `test_cw_invest_refresh.py` 同主题仓）。边界：不碰策略卡分支与 T-162 策略侧刷新判据；不碰品质改写 ΔV 分派（3.6）；handler 执行链归 3.8。

**设计依据**：design.md §2.3（汇合次序单一真源）/ §2.7（E3/E4）/ §2.8（判据与 R 组）；details/env-value-models.md §2.1.3（消费位）/ §2.3（集成汇总）

**文件面**：`src/sr_od/application/currency_war/kernel/cw_events.py`、`sr-od-test/test/sr_od/app/currency_war/test_cw_env_economy.py`（E3/E4 增锁）、`test_cw_env_gift.py`（G3-G7 消费锁）、`test_cw_env_universe.py`（如需联合断言增补）、`test_cw_invest_refresh.py`（R 组）

**依赖**：3.1、3.3、3.4（三块产物在本阶段汇合；cw_events env 分支物理互斥由本依赖序保证）；同文件在飞互斥见头注

**优先级建议**：5

**完成判据**：
- E3/E4 锁全绿：域带压过 floor 78 帧（reason=env-econ）、估算缺失退裸分、全集外 faction 环境结构性不复活、经济环境全集门恒放行
- G3-G7 消费锁全绿（详设 §2.1.5 逐行，含 G7 evicted 传导）
- R1-R5 + R7 锁全绿（design.md §2.8：零价值槽可刷/顶级保护/priority 豁免/未知名 fail-closed/被禁槽恒可刷）
- `test_cw_invest_refresh.py` 回归全绿（含策略侧既有刷新锁）；U1-U6 持续绿（全集门行为不被集成扰动）
- §12 通用工程门（引用，不复述）

**验收凭据形式**：测试名清单 + 回归文件 + ruff check

## 3.6 品质改写型结构与分派（StrategyPoolRewrite/ENV_POOL_REWRITE）

**范围**：`kernel/cw_investments.py` 新增 `StrategyPoolRewrite` + `ENV_POOL_REWRITE` 表（恰 7 条，pending_notes 必填校验）+ `∩ ENV_GIFTS ∧ ∩ ENV_ECONOMY` 互斥断言收全；`kernel/cw_env_economy.py` 价值函数内 ΔV 分派（`name ∈ ENV_POOL_REWRITE` → ΔV 公式，读 `STRAT_POOL_ECON_MEANS`/`OFFER_QUALITY_DIST`，任一缺参 → resolved=False，v1 恒然）；新建 `test_cw_env_pool_rewrite.py`（Q1-Q6）。边界：不碰 decide_event（Q2 的 decide_event 回归帧为测试直调断言）、不建估算参数数据（层 E 转正数据批另行立项）。

**设计依据**：details/env-value-models.md §2.2.1（语义盘点）/ §2.2.2（两层拆分与裁决）/ §2.2.3（难度腿辖域）/ §2.2.4（数量通道）/ §2.2.5（结构与落码面）/ §2.2.6（Q 组）

**文件面**：`src/sr_od/application/currency_war/kernel/cw_investments.py`、`src/sr_od/application/currency_war/kernel/cw_env_economy.py`、`sr-od-test/test/sr_od/app/currency_war/test_cw_env_pool_rewrite.py`（新建）

**依赖**：3.3（同文件 cw_env_economy.py/cw_investments.py 串行互斥）

**优先级建议**：5

**完成判据**：
- Q1-Q6 锁全绿（详设 §2.2.6 逐行：结构表 7 条/fail-closed 恒然+裸分回归帧/公式算术注入/准入方向/数量通道零消费/互斥断言）
- §12 通用工程门（引用，不复述）

**验收凭据形式**：测试名清单 + ruff check

## 3.7 portal 登记端

**范围**：`cw_effect_inventory.py` payload 联合扩 `EnvEconomyEffect` + 经济环境 EffectSpec 条目（source=SOURCE_PORTAL，孤儿/id 校验沿 `_validate_strategy_effects` 同款）；`CwScreenInvestEnv._decide_and_act` 确认链接 `register_portal`；未入模环境 `UnitBuffRef` 占位登记，G 组环境占位 notes 附 `GiftGrant` 摘要（详设 §2.3）。边界：不接经济判据消费面（design.md §1.3-5）、不启用环境侧刷新。

**设计依据**：design.md §2.4 / §2.7 E5；details/env-value-models.md §2.3（portal 登记端行）

**文件面**：`src/sr_od/application/currency_war/kernel/cw_effect_inventory.py`、`src/sr_od/application/currency_war/operations/cw_screen/cw_screen_invest_env.py`、`sr-od-test/test/sr_od/app/currency_war/`（登记锁，文件名批首 grep 对齐既有 effect inventory 锁聚居地）

**依赖**：3.2（schema）、3.4（GiftGrant notes）；与 3.3/3.5/3.6 文件域不交可并行

**优先级建议**：4

**完成判据**：
- E5 锁全绿：ActiveEffect 在册（portal 源）、payload 类型正确、未入模环境占位登记（含 G 组 notes 摘要）
- `cw_screen_invest_env` 相关既有锁回归全绿
- §12 通用工程门（引用，不复述）

**验收凭据形式**：测试名清单 + 回归文件 + ruff check

## 3.8 环境刷新执行链（handler）

**范围**：`CwScreenInvestEnv` 刷新执行链——`read_invest_refresh_counts('env')` 观察通道转正为执行闸、槽序循环（计数闸 → 文本锚定刷新钮 → 等 1.5s → 验效双通道（计数扣减权威/卡名变化兜底，双输即停）→ 重分类）、停止条件（无零价值槽/计数耗尽/不可分类）、最终名集重调 `decide_invest`（G1）；R6 端到端锁。刷新钮 screen_info 锚点若缺，先按 od-dev-screen-onboarding 建档再接线（坐标单一源纪律）。边界：不碰策略侧 handler；不碰 active_env 写入/台账变异窗时序。

**设计依据**：design.md §2.8（执行链与 R6）

**文件面**：`src/sr_od/application/currency_war/operations/cw_screen/cw_screen_invest_env.py`、`assets/game_data/screen_info/currency_war_invest_env.yml`（若需新增刷新钮锚点）、`sr-od-test/test/sr_od/app/currency_war/test_cw_invest_refresh.py`（R6）

**依赖**：3.5、3.7（两者同文件 cw_screen_invest_env.py，串行互斥由本依赖序保证）

**优先级建议**：4

**完成判据**：
- R6 端到端锁全绿：计数现读闸/验效双输停/最终重决策入口=G1（design.md §2.8）
- `cw_screen_invest_env` 相关既有锁回归全绿
- §12 通用工程门（引用，不复述）

**验收凭据形式**：测试名清单 + ruff check

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：3.1、3.2、3.3、3.4、3.5、3.6、3.7、3.8；与兄弟迭代 `2026-09-12-strategy-universe-gate` 末阶段同正本行（`08_events.md` E2/`13_pick_family.md` §1）互斥，编排者排序
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单

- `strategy-docs/13_pick_family.md` §1 `decide_invest` 行（判据格一次性补四块语义：候选全集门 + 送卡静态档 + 经济域带（含品质改写层 E 转正指针）；门谓词/全集定义/失格形态/归因串/域带结构/正交边界）+ §2 E1 行 ← 3.1/3.5/3.6
- `strategy-docs/08_events.md` E1/E2 行：挂账落定改判据状态（通道清单/估值形态/两型消费入口分型/域带集成指针）← 3.2/3.3/3.5/3.6
- `strategy-docs/11_shop_decisions.md` §8 评分框架节：环境经济域带与策略 S2 域带共享结构的申报行 ← 3.5
- `docs/develop/sr_od/application/currency_war/game_state/effect-domain.md`：SOURCE_PORTAL 登记端语义行 ← 3.7
- `kernel/cw_investments.py` 模块 docstring 评估表清单行（补 ENV_ECONOMY/ENV_ECONOMY_ESTIMATES/ENV_GIFTS/ENV_POOL_REWRITE）← 3.2/3.3/3.4/3.6
- `docs/develop/sr_od/application/currency_war/flow/outer_loop.md` §2.2（overlay 分支）：环境刷新执行链接入行 ← 3.8
