# 羁绊数据域 v4.7 重建 迭代设计（总纲）

## 0. 元信息

- 迭代目标：货币战争 v4.7 换赛季（「入画奇航」S2）后，羁绊数据域按官方口径全量重建——数据层回归纯官方数据（字段名对齐 plaza API）、生成器恢复生成职责并以三源交叉对拍闭环、消费点迁移至新数据层。承接 = 版本适配总流程（skill `sr-od-dev-currency-war` references/version-update.md）§2 Checklist 第 4 步「羁绊域」（§3.2）；用户架构裁定（2026-11-13 会话）：框架数据层只放官方数据、命名与官方 API 统一、策略特判归策略实现层。
- 状态：**草案**
- 文档清单：
  - `details/trait-data-layer.md` —— 数据层结构与生成器：Trait 结构、聚合算法、翻译规则、count_mode 口径取舍
  - `details/consumer-migration.md` —— 消费点迁移：旧羁绊名→新羁绊名映射、逐文件迁移清单、退役清单

## 1. 问题与动机

- **现状症状**：
  1. v4.7 换赛季为「重做级」（官方赛季说明：员工羁绊/费用/前后台定位全量重制，全新羁绊 29 个；config_v4.7 实测角色 63 名单与旧注册表 76 名大面积不重合，费用几乎全员重排）——旧注册表 `cw_factions.FACTIONS`（32 羁绊，V4.4 口径）与官方新名单结构性脱节：羁绊名大换血（仙舟→仙舟舰队、量子同频/贝洛伯格/列车同行/燃血/战技点/盛会之星等消失、千星商会等 17 个新增）。
  2. 旧数据层混入判断层内容：`FactionInfo.category`（四分类）存在 1 处真实消费（`cw_gain_chain.py:2741` 策略卡发放判据 `category != 'independent'`——迁移语义重定义见 consumer-migration.md §2.1），`note` 为人判注记——违反「数据层纯官方」新原则。
  3. 羁绊数据采集链断裂：旧上游采集器（`.debug/temp` 内 trait_detail 采集脚本）已随临时区清理销毁，`gen_factions.py` 对拍器失去数据源。
  4. 官方数据源形态升级：config API 的 `trait_info_list` 34 条骨架中名字/图标/类型有值而 layers/role_ids 空（空壳，11 种参数变体实测一致）；完整数据在攻略帖 `role_stages[].traits[]`（实测 1000 篇 Hot 全量帖聚合可覆盖 29/34）与米游社 wiki 羁绊频道（27 词条，详情带分级效果全文）。
- **根因归层**：约定层——旧数据层「官方数据 + 人判字段混合存放」的约定不适应「官方重做 + 多源采集」的新形态；采集链把上游脚本放临时目录的约定脆弱。
- **解决到哪**：29 个常规羁绊（trait_type 0/1/2）的数据层重建、生成器重建、消费点迁移。
- **明确不解决**：
  - trait_type=3（400xxx 五个：连携追击/四维狂潮/星狩誓言/救世主/从师）——主角光环专属效果（config spot_light 授予，官方赛季说明口径「全新羁绊共计 29 个」不含它们），归主角光环域另立；
  - 策略实现层的任何特判（category 分类的策略侧重建、评级）——用户裁定暂缓；
  - 阵容知识层（final_comps/聚类）——等攻略沉淀，按 version-update.md §4.3 时间缓冲；
  - 装备贡献表（L2）的类别词适配——已登记挂账板，随装备域重建批；
  - 实机值采集（刷新概率/门槛表）——实机窗口另批。

## 2. 方案

### 2.1 系统级变化（读一遍知全貌）

1. **数据层换模块**：`data/cw_factions.py`（`FactionInfo` 手维护判断层）退役 → `data/cw_traits_data.py`（生成器产物，纯官方，结构见详设 trait-data-layer.md §1）：`Trait{trait_id, trait_name, trait_type, layers, members, simple_desc, trait_icon, count_mode}`，提供 `TRAITS`（id 索引）与 `trait_by_name`（名字索引，消费侧兼容）。`category`/`note` 不建（category 零消费点；note 语义由 `simple_desc`/`layers[].trait_desc` 官方全文承接）。
2. **生成器换职责与数据源**：`skills/sr-od-dev-currency-war/scripts/gen_factions.py` 从「纯对拍器」恢复为「聚合生成器 + 三源对拍」——数据源 = 本地拉取缓存 `.debug/game_data/currency_war/plaza/lineups_Hot.jsonl`（1000 篇 v4.7 帖，2026-11-13 实采）聚合 + `config_v4.7.json` 骨架过滤（34 条取 trait_type 0/1/2 共 29 条）+ wiki 频道 240 交叉验证（27 词条 diff 报告）。旧 `.debug/temp` trait_detail.json 通道废弃。
3. **消费点迁移**：`FACTIONS[name].tiers/desc/members()` → 新数据层投影，实测引用面 55 文件 / 355 处（含注释字面；2026-11-13 grep，清单按 consumer-migration.md §问题与约束的实测命令与分组判据动态生成）；旧羁绊名硬编码逐点迁移（映射表见 consumer-migration.md §1——沿用 10、疑似改名 2、消失 20、新增 17，消失项对应消费逻辑标注「需重写」）。
4. **机制死代码清理**（与消费点迁移同批）：开拓者双形态（`is_trailblazer/trailblazer_form/trailblazer_row_unit` 等）与布洛妮娅选边（`SIDE_PICK_DUAL_BONDS/side_pick_bond`）在新名单无持有者，随本批删除（用户裁定 2026-11-13；挂账板 `.debug/progress/CW跨迭代挂账.md` §一.0 条款批归属以本设计 landing 为准回写）。
5. **count_mode 口径建模（本迭代只建模不接线）**（用户裁定：千星商会按官方文本建模）：`Trait.count_mode` 字段（`TOTAL` 总上场人数 / `STAR3` 三星上场数），千星商会 = `STAR3`（官方 desc 原文「每上场1位3星【千星商会】角色，将激活1级羁绊效果」），其余 28 个 = `TOTAL`。**接线（板面计数侧并行产出三星计数、激活判定按 count_mode 选取）归策略暂缓批恢复后的首个策略迭代**——本迭代策略层无运行时消费（用户裁定暂缓），先落数据字段；接线设计随该策略迭代另立。取舍论证见 trait-data-layer.md §4。

### 2.2 详设划分与跨详设接口契约

- 详设一 `trait-data-layer.md`：数据层结构 + 生成器（聚合/翻译/对拍）。
- 详设二 `consumer-migration.md`：消费点迁移映射与清单。
- **跨详设接口契约**（唯一总纲定死的接口，两详设共同遵守）：
  - **数据层对外形态**（迁移详设的迁移目标 = 此契约）：
    - `TRAITS: dict[str, Trait]`——键 = `trait_id`；
    - `trait_by_name: dict[str, Trait]`——键 = `trait_name`（官方中文名，消费侧标签体系的既有键型）；
    - `Trait.tiers` 便捷属性 = `tuple(layer.layer for layer in self.layers)`（官方 layers[].layer 投影，兼容 20+ 处激活判定消费）；
    - **`Trait.members` 为 dataclass 字段**（`tuple[str, ...]` 成员角色名，生成期由官方 role_ids 翻译落定）——旧 `FactionInfo.members()` 方法不保留，唯一无参调用点 `telemetry/cw_win_model.py:49` 迁移为字段读；
    - 羁绊标签键型不变 = `trait_name` 中文名（板面计数/遥测/成型判定的既有键型，迁移消费点只换数据来源不改键型）。
  - **count_mode 契约（建模不接线）**：本迭代数据层落 `count_mode` 字段（总纲 §2.1-5）；板面计数并行三星计数与激活判定口径选取**不在本迭代范围**（归策略暂缓批恢复后的首个策略迭代，理由见 §2.1-5）。
  - **迁移批次边界**：消费点迁移阶段动 `cw_bond_equips` 时**同时承担**开拓者/选边死代码删除（前置 = 角色注册表重建批已落，注册表无开拓者条目）；角色注册表条目本身的删改归角色会话批，不在本迭代文件面。

### 2.3 依赖与顺序

- **前置（外部）**：角色注册表 v4.7 重建（另一会话进行中）——本迭代三个硬依赖：①生成器 members 翻译（role_ids → 角色名查表）；②成员对拍（官方名单 vs 自报派生）；③**查表契约**（第一轮对抗 A15 立项）：角色批须暴露「plaza id → 角色规范名」索引符号（形态 = `dict[str plaza_id, str 规范名]` 或等价；具体符号名以角色批交付为准）——缺失或形态不符时本批停手，回角色批对齐，禁自行补建平行索引。聚合器构建与消费点映射表梳理不受阻，可先行。
- **并行**：装备域/投资域重建与本迭代文件面不相交（装备 = cw_equipment_data，投资 = cw_invest_data），可并行。
