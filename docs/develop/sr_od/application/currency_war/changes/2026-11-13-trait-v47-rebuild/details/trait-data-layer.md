# 数据层结构与生成器（详设）

> 总纲划给本篇：Trait 数据结构、生成器（聚合/翻译/对拍）的全部设计。消费点迁移见 consumer-migration.md。

## 问题与约束

- 输入源四份：`config_v4.7.json` 骨架（trait_info_list：trait_id/trait_name/trait_icon/trait_type 有值，layers/role_ids/simple_desc 空——11 种参数变体实测一致，勿再试）；`config_v4.7.json` 角色条目 `role_list[].trait_details[]`（count_mode 引文源——千星商会三星原文在此，trait_info_list 的 simple_desc 实测为空串不可用；trait_details[].id 与 trait_id 对齐）；`lineups_Hot.jsonl`（1000 篇 v4.7 Hot 帖，2026-11-13 实采于 `.debug/game_data/currency_war/plaza/`）；米游社 wiki 频道 240（27 词条，content/info 详情 `contents[].text` HTML 内嵌「羁绊分级效果」全文——社区维护，质量未逐条核验）。
- trait_type=3（400xxx 五条）不进本数据域（主角光环专属，总纲 §1 范围外）：聚合器读 config 骨架时按 `trait_type in (0, 1, 2)` 过滤 → 29 条。
- 翻译依赖角色注册表 v4.7 版（id → 规范名查表）；成员对拍依赖角色自报（factions/schools/independent）。前置 = 角色会话批已落。
- 落点纪律：拉取缓存已统一 `.debug/game_data/currency_war/plaza/`（temp 清理不波及）；生成器脚本住 `skills/sr-od-dev-currency-war/scripts/`。

## 方案

### 1. 数据层结构（`data/cw_traits_data.py`，生成器产物，勿手编）

```python
@dataclass(frozen=True)
class TraitLayer:
    layer: int        # 官方 layers[].layer：激活所需人数档
    quality: int      # 官方 layers[].quality：档品质
    trait_desc: str   # 官方 layers[].trait_desc：分层效果全文（富文本已渲染为纯文本）

@dataclass(frozen=True)
class Trait:
    trait_id: str                  # 官方 trait_id（稳定机器键：跨版本 diff/对拍/资产映射）
    trait_name: str                # 官方 trait_name（消费侧标签键型）
    trait_type: int                # 官方 trait_type：0 阵营 / 1 流派 / 2 独立
    layers: tuple[TraitLayer, ...]
    members: tuple[str, ...]       # 成员角色规范名（官方 role_ids 经角色注册表翻译；同名多档合并）
    simple_desc: str               # 官方总效果简述
    trait_icon: str                # 官方 trait_icon URL
    count_mode: str = "TOTAL"      # 激活计数控：TOTAL=总上场人数 / STAR3=三星上场人数（见 §4）

    @property
    def tiers(self) -> tuple[int, ...]:
        return tuple(layer.layer for layer in self.layers)

TRAITS: dict[str, Trait] = {...}          # 键 = trait_id
trait_by_name: dict[str, Trait] = {...}   # 键 = trait_name（模块级派生索引）

# members 口径（第二轮复攻 B2）：可组队员口径 = is_hide 过滤后的角色（召唤型
# 单位不算成员——腾荒类 is_hide=True 帖内上场 0 次，板面计数消费链天然只触
# 可组队员）；与官方 role_ids 的差集（召唤物）进成员对拍例外清单人裁。
# 召唤型激活特例登记（与 count_mode 接线同批归策略批）：双龙吟类激活 =
# 上场成员 + 后台召唤物，通用人数计数不适用，板面计数接线批须按羁绊特例处理。
```

- `members` 数据口径见上方代码块内声明（可组队员口径 + 召唤型特例登记）；旧消费若以方法调用（`FACTIONS[x].members()`）存在，迁移时改为读 `trait.members` 字段；按名查询 = `trait_by_name[name].members`（members_of 兼容函数不建——唯一调用点已定为字段读迁移，零消费接口不建，第二轮复攻 B3）。
- 生成器文件头固定声明：「本文件由 `gen_traits.py` 生成（v4.7 帖子聚合 + config 骨架 + wiki 交叉），勿手编；重跑命令」——同 `cw_invest_data.py` 既有模式。生成器更名 gen_factions → **gen_traits**（第二轮复攻 B6：factions 是旧翻译词，官方口径 = trait，与数据模块 cw_traits_data 对齐；正本更新清单指针随 3.2 同步）。

### 2. 聚合算法（生成器核心）

1. **骨架基座**：读 `config_v4.7.json.trait_info_list`，过滤 `trait_type in (0,1,2)` → 29 条基座（trait_id/trait_name/trait_icon/trait_type 直接采用；官方字段，零转写）。
2. **帖子聚合**：遍历 `lineups_Hot.jsonl` 每帖 `tourn_detail.role_stages[].traits[]`（键集实测 = trait_id/trait_name/trait_icon/trait_type/current_role_count/layers/remarks/role_ids/simple_desc；**remarks 字段不采**——实测均为空或冗余引文，无消费价值）：
   - 按 trait_id 分桶；**去重规则**：每 trait 取 `len(layers)` 最大的帖（并列时取 `created_at` 新者）——防旧帖降级快照（实测例：100602 旧帖仅 1 层且 desc 空串，调研报告 trait_api_research.md §跨帖验证节）；
   - `role_ids` 取各帖并集（成员名单跨帖互补；不同帖激活档不同不影响成员集）；
   - `simple_desc` 同 layers 最大帖（与 layers 同源一致）；
   - **渲染管线沿用**：`layers[].trait_desc` 富文本 → 纯文本渲染复用旧 `gen_factions.py` 的 `render_rich` 逻辑（`<property type=X display=all>` → config `role_property_list` 属性中文名 / `display=icon` 删除 / `<color>` 删除；未知 property type 保留原标签 + 打印警告不静默）。
3. **翻译**：`role_ids` → 角色规范名——查角色注册表（运行期派生映射 `{c.source: c.name for c in cw_chars.CHARACTERS}`，**查表契约=派生形态，见 consumer-migration.md「跨迭代查表契约」——映射须含升格高费档等例外档 id，生成器保留覆盖对拍守卫**）；规则：
   - **同名多档合并**：同一角色的多费用档 id（如星神★阿哈 151112/151122/151132，帖内三档均有出场——实测 149/21/81 帖）翻译为同一规范名后去重（成员是「角色」非「档位」）；
   - **隐藏条目过滤（可组队员口径，第二轮复攻 B2）**：config `is_hide=true` 的角色条目不翻译（现役仅腾荒一条 = 双龙吟召唤物，帖内上场 0 次）——members 落「可组队员」口径；被过滤 id 计入对拍差异报告人裁（召唤物不算成员的裁决与差集声明见 §1）；
   - **查表失败即 fail-closed**：role_ids 中任一 id 翻译失败（角色未建/已删，且不属于同名多档合并可归并的档位）→ 生成器打印该 id 并非零退出——禁静默丢弃（成员缺失 = 对拍与策略双双失真）。
4. **count_mode 判定**：生成器内 29 条默认 `TOTAL`，显式覆盖表仅一行：`{"千星商会": "STAR3"}`（依据 = 官方 desc 原文「每上场1位3星【千星商会】角色，将激活1级羁绊效果」，**引文源 = config `role_list[].trait_details[]`（role id 150302，trait_detail id 100602）**——trait_info_list 的 simple_desc 为空串不可用；用户裁定 2026-11-13「按最新的文本模式来建模」）。覆盖表逐条带 desc 引文校验：desc 与覆盖表不符即非零退出（防版本文案变化后口径过期）。**接线边界**：板面三星并行计数与激活判定口径选取不在本迭代（总纲 §2.1-5「建模不接线」，归策略暂缓批恢复后的首个策略迭代）。
5. **wiki 交叉验证（报告，不落数据）**：wiki 频道 240 的 27 词条（content_id 实测清单 8210-8236，3.1 执行时顺带复核 id 连续性与缺收清单——第一轮对抗 A24）拉详情，解析「羁绊分级效果」文本与聚合 `layers[].trait_desc` 做**包含性比对**（wiki 文本为社区改写，不要求逐字相等；比对维度 = 档数一致 + 关键数值词命中——**数值词 = 双方文本中「数字（含小数）+ 可选百分号」串的集合**，第二轮复攻 B7）；差异输出到三源报告供人裁，**不自动写数据**。wiki 缺收的 2 条（守护/治疗，实测）与帖内独有的差集同报。

### 3. 对拍设计（生成器末段，非零退出语义）

| 对拍 | 左源 | 右源 | 判据 |
|---|---|---|---|
| 骨架对拍 | 聚合产物 trait_name/trait_type | config 骨架 | 逐键相等；基座有而聚合无 layers 的条目 = 报警（覆盖不足） |
| 成员对拍 | `trait.members` | 角色注册表自报派生（`factions+schools+independent` 含该羁绊名的角色集合） | 集合全等；差异逐条列出（官方多出的 = 隐藏条目或注册表漏建；自报多出的 = 官方 role_ids 未含，均人裁后进例外清单固化进生成器） |
| 全覆盖对拍 | 聚合产物 29 条 | config 34 条 − type3(5) | 条数与 id 集合相等 |

例外清单形态 = 生成器内常量表（键 = (trait_id, role_id)，值 = 裁决理由），同旧 `MEMBER_EXCEPTIONS` 模式。首版例外为空，跑首聚后按差异人裁填充。

### 4. 关键取舍

- **members 存名字而非 role_ids**（用户裁定 2026-11-13）：消费链（板面计数/策略标签/成型判定）全按角色中文名走，数据层存 id 则每消费方多一跳翻译；id 的机器键职责由 `trait_id` 字段承担（跨版本 diff/对拍/资产映射不受影响）。
- **count_mode 进数据层而非策略层特判**：激活判定位于 kernel（玩法规则复现层），规则口径是官方事实（desc 原文），非策略决策；先例 = 装备 `stacking` 字段（desc 判读的结构化元数据，在 `cw_equipment_data` 数据层）。策略层将来若要「按口径做决策」（如优先凑三星），那是策略逻辑，不在本字段。
- **生成器恢复生成职责而非维持纯对拍**：数据源从单一官方 config 变为「骨架 + 帖子聚合」多源加工（去重/翻译规则不可省），纯对拍器形态无法承载；旧「对拍器形态」的历史成因（判断层手维护、防生成器复活平行数据层）随「数据层 = 生成器产物」新原则消失。
- **聚合数据源用帖子而非 dynamic_traits 登录接口**：后者需登录态（调研实测免登录 retcode=-100）且为阵容计算接口非图鉴；1000 篇帖子聚合已全覆盖 29/34（100 帖实测全覆盖），零登录依赖。
