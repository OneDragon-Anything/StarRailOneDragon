# 06 信息模型与注册表

> 策略的输入:观测态 `GameState`(本局动态)+ 游戏参考数据注册表(跨局静态)。原则(ADR-070):**信息层只管完整、准确地提供;用不用归策略**。

## 1. 设计原则

1. **完整优先**:游戏里能知道、可能影响决策的信息都建模;当前没用也留着(自定义策略用)。
2. **`None` = 未观测,不说谎**:OCR 没读到 → None(或容器空),不用 plausible 默认值;策略层对 None 安全降级。
3. **单一入口**:所有局内信息收口 GameState(每决策点一份快照);整局固定事实(职级/位面首领/词缀/已选环境)归 state 不散落 session。
4. **观测态与参考数据分离**:GameState 只装本局观测;跨局知识走注册表(§3),策略 import 查询。

## 2. GameState 字段语义(按组;类型与默认值以 `cw_state` 代码为单一源)

| 组 | 字段(语义) |
|---|---|
| 进度/节点 | `plane`(位面)/ `node_index`(位面内节点号)/ `node_type`(当前节点类型,节点行 CV)/ `enemy_difficulty`(当前敌难数值) |
| 整局固定事实 | `selected_difficulty`(职级,两阶难度模型:职级定起始敌难+词缀、`enemy_difficulty` 随节点递增可被持卡压低;详 [gameplay](../../../game/gameplay/currency_war.md))/ `plane_bosses`(→派生 `current_boss`)/ `enemy_affixes`(简报+节点词缀) |
| 经济 | `gold` / `level` / `level_up_cost` / `xp_progress` / `streak` / `shop_refresh_cost` |
| 棋盘 | `deployed` / `bench`(`Unit`:槽位/身份/阵营/星级/前后排/装备,装备记在角色身上)/ `front_max`·`back_max` / `bench_full_flag` / `board`(阵营激活 count + tier) |
| 商店 | `shop`(ShopCard:阵营/名/费用/星级) |
| 投资选择 | `active_env` / `active_strategies` / `megastar_char` / `partner_char` |
| 装备/资源 | `inventory`(可用装备 + 钻) |
| 生命 | `hp`(备战 shop 关态才显示) |

## 3. 注册表地图(游戏数据单一源,`src/sr_od/application/currency_war/`)

| 注册表 | 内容 | 来源/生成 |
|---|---|---|
| `cw_chars.CHARACTERS` | 角色全量(费用/阵营/站位/类型) | plaza API 生成器(`tools/cw/gen_plaza_chars.py`) |
| `cw_factions.FACTIONS` | 羁绊(类别/tiers/效果) | 米游社图鉴 |
| `cw_equipment.EQUIPMENTS` + `cw_synthesis` | 装备全量 + 合成图谱 | 米游社;API `equipment_list.compose_list` 为合成权威源候选 |
| `cw_invest_data` + `cw_investments` | 投资策略/环境全量(base)+ overlay(economy/评估分/分类) | plaza API 生成器(`gen_plaza_invest.py`,内建 diff) |
| `cw_comps.COMP_LIBRARY`(+`cw_plaza_comps`) | 阵容库 | plaza lineup 生成(勿手编) |
| `cw_shop_odds` | 刷新概率表 `REFRESH_PROB` + 牌池副本 `POOL_COPIES_PER_CARD` + D 牌期望 `expected_refreshes` | 游戏内表格实机 OCR(ADR-0091)+ V3.7 必修二(ADR-0109) |
| `cw_enemy_data` / `affix_effects_data` | 敌人词缀池 / 词缀效果原文 | 图鉴 + 运行时采集 |
| 未建模(唯一源在 game 侧) | boss 克制 / 敌人词缀全集 / 优势布局 | `docs/game/currency_war/data/{bosses,competitors,advantage_layouts}.md` |

**版本维护**:赛季制,版本更新 = 重跑生成器 → 按 diff 修 overlay → 回归测试;未建模 doc 手工同步。数据源优先级与证据分级 → [docs/game/README.md](../../../game/README.md)。

## 4. 机制克/利双向表

`MECHANIC_COUNTERS` / `MECHANIC_SYNERGIES`(词缀机制 → 克制/受利的 comp 属性;同一词缀对不同阵容方向相反,如反伤克高频、利燃血);`AFFIX_MECHANIC_MAP` 把 OCR 词缀名归一到机制键(同词缀自动泛化,ADR-0203)。consumed by mechanics_fit(02 §2)。

## 5. 边界

- 工具值(升级金价表等)是估算的地方以代码常量注释标明;权威化路径 = 游戏内图鉴提取([game/research/economy §9](../../../game/currency_war/research/economy.md) 未决数值表)。
- 商店锁定机制不存在于货币战争(字段已清);试用/本体状态不建模(02 §9)。
