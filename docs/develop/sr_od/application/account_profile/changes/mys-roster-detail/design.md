# mys-roster-detail（角色明细与中文字段）迭代设计

## 0. 元信息

- 目标：①`SrCharacter` 增中文字段（`element_cn`/`base_type_cn`）—— **接口层直接出中文，消费方零查表**（用户裁定 2026-11-04）；②接入 `avatar/info` 全量明细（遗器/位面饰品/星魂/行迹/属性面板）；③新 MCP 工具 `mys_get_roster_detail`。
- 状态：草案（轻量迭代：结构沿用 mys-account-mcp 已验收的分层与契约，仅增量）
- 实测依据：`.debug/account/api/avatar_info_planner.json`（2026-11-03 avatar/info 实测快照，64 角色——**结构要点已固化进本设计与测试 fixture，摆脱易失件依赖**）；码表权威来源侦察报告：`.debug/temp/mys-roster-detail/codes-draft.md`

## 1. 实测结构要点（avatar/info 原始响应）

> **端点勘误（T-4 实机验收抓出）**：明细数据的真实端点是 **`hkrpg/api/avatar/info?need_wiki=true&role_id=<uid>&server=<srv>`**（RECORD 域，同头集同 DS；`need_wiki=true` 是 `property_info`/`equip_wiki`/`relic_wiki`/`recommend_property`/`relic_properties` 五词典的来源开关）。`hkrpg/api/index` 只出轻口径 12 字段/角色（is_chosen 在此），**不含遗器/星魂/行迹/面板**——初版设计误将规划器合并产物（index+avatar/info 两响应合并）当成 index 原始响应。规划器 trace.log 与真会话原始样本双重实证（样本固化：`.debug/temp/mys-roster-detail/raw_avatar_info_sample.json`，1.59MB/64 角色）。

- avatar/info 响应 data 层：`avatar_list[]（全量明细）+ property_info(56 码词典) + equip_wiki/relic_wiki + recommend_property + relic_properties`
- `relics[]`（套装遗器）与 `ornaments[]`（位面饰品）同构：`{id, level, pos, name(中文), desc(lore), icon, rarity, main_property, properties[]}`；词条 = `{property_type(数字码), value(字符串), times(强化次数), is_preview}`
- `ranks[]` 星魂：`{id, pos, name(中文), desc(中文), icon, is_unlocked}`
- `skills[]` 行迹：`{point_id, point_type, level, is_activated, remake(中文「普攻/战技」), skill_stages[{name(中文), desc(中文), level, …}]}`
- 角色 `properties[]` 面板：`{property_type(数字码), base, add, final}`（字符串数值）

**结论**：名称/星魂/行迹文案官方已给中文——只有四张码表需要本地固化：`property_type`→属性名（面板码与遗器词条码同表）、`base_type`→命途、`element`→属性、`pos`→部位。

## 2. 契约（定死）

1. **码表（三层查表，miss 不抛异常）**：
   - ①**响应原生词典优先**：`avatar/info` 响应自带 `data.property_info`（实测 56 条：`{property_type, name, property_name_relic, property_name_filter, icon}`，官方中文名随响应更新、自动前向兼容新码）——显示名**优先取 `property_name_relic`**（规避 `name` 的 `#1[f1]%` 模板占位符，实测 pt=36），空名码显示「未知属性(pt=N)」；
   - ②**硬编码快照兜底**：`sr_od/mys/hsr_codes.py` 固化四表（依据侦察报告 `.debug/temp/mys-roster-detail/codes-draft.md`——`PROPERTY_INFO_SNAPSHOT`（56 码全集：53 实名 + 空名占位如实标注）、`BASE_TYPE_CN`（**全集 9 个**：1毁灭/2巡猎/3智识/4同谐/5虚无/6存护/7丰饶/8记忆/9欢愉；任务书曾假设 14，侦察三源证伪）、`ELEMENT_CN`（7 条，字符串码 + element_id 掩码注释）、`RELIC_POS_CN`（1-6：头部/手部/躯干/脚部/位面球/连结绳）+ `RELIC_MAIN_AFFIX_ALLOWED`（部位→主词条可选集，作轻校验器）；
   - ③终兜底：「未知属性(pt=N)」+ warning（不抛异常，官方有预占码位习惯）；
   - **撞域纪律**：`ranks[].pos` 是星魂序号（1-6），与遗器部位码撞值域——两处**禁共用枚举**；
   - 同响应的 `relic_properties[]`（词条→面板修饰关系）随明细透传与否按消费需要定，本迭代不透传（记录在案）。
2. **`SrCharacter` v2**（契约 5 修订）：v1 八字段 + `element_cn: str` + `base_type_cn: str`
3. **`CharacterDetail` 冻结字段集**：`id, name, level, rarity, rank, element, element_cn, base_type, base_type_cn, equip: ConeSummary | None, relics: list[HsrRelic], ornaments: list[HsrRelic], ranks: list[HsrRank], skills: list[HsrSkill], properties: list[HsrPanelProperty]`
4. **子结构冻结**：
   - `SrRelic`：`name, pos, pos_cn, rarity, level, main: HsrPropertyEntry, subs: list[HsrPropertyEntry]`（不透传 desc/lore、icon、id、is_preview—— **只透传带等数值的 preview 条目照常映射**）
   - `SrPropertyEntry`：`name_cn, value, times`（times=0 的主词条照常给 0）
   - `SrRank`：`pos, name, desc, is_unlocked`（不透传 icon/id）
   - `SrSkill`：`name(remake), level, is_activated, stages: list[HsrSkillStage]`；`SrSkillStage` = `name, desc, level`（不透传 icon/URL/内部 id）
   - `SrPanelProperty`：`name_cn, base, add, final`
5. **新 MCP 工具** `mys_get_roster_detail()`：`avatar/info` 一次调用 → `success` + `list[CharacterDetail]`；`session_expired`/`error(1034)`/`awaiting_ticket` 语义与 `mys_get_characters` 完全一致（信封复用）；`mys_get_characters` 保持 v1 轻口径不变（低开销快查）
6. 明确不解决：icon/figure 等 URL 字段不透传；遗器 lore desc 不透传；servant_detail/special_skills/cur_enhanced_id 等罕见字段不透传

## 3. 测试策略

- fixture：planner 快照抽样固化进测试仓（带光锥满遗器角色 + 无遗器角色 + equip=None 角色各一）
- 码表单测：封闭集全集断言 + 锚点断言（头部主词条 705=生命值、开拓者多形态 base_type、命途全集 9 个）
- detail 映射断言：冻结字段集逐字段、词条 name_cn 映射正确、times 透传

## 4. 验收

实机：`mys_get_roster_detail` 返回 64 角色明细，抽 3 名角色与 planner 快照逐条对照遗器词条（name_cn/value/times 一致）。
