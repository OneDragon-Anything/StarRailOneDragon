# 米游社百科数据快照（references/data）

> skill 官方数据底座。生成：2026-11-05（V4.7 期）。**skill 自包含**——使用者的 agent 无需本项目其他文件。

## 定位（MCP 时代，2026-11-05 起）

项目 MCP 的三个查询工具（`character_lookup` / `cone_lookup` / `relic_lookup`）已承载**角色/光锥/遗器的基础信息查询**（数据固化自官方 wiki 快照，随项目版本更新）——agent 查询优先走 MCP，本目录 JSON 退居三线：

1. **版本更新管道输入**（不可删）：`relic_set_list.json`（遗器抓取 content_id 清单）、`cone_full_list.json`（光锥抓取与图标下载输入）、`character_full_list.json`（角色详情抓取输入）
2. **攻略向知识**（MCP 没有）：`char_cones.json` / `char_relics.json` / `char_teams.json`（角色页推荐表）
3. **MCP 不可用时兜底**：其余文件（`cone_details.json` 的光锥故事字段 MCP 未覆盖）

| 文件 | 内容 | 条数 | 定位 |
|---|---|---|---|
| `character_full_list.json` | 国内 wiki 角色词条列表（name+content_id） | 101 | 管道输入 |
| `cone_full_list.json` | 光锥词条列表（ch19） | 170 | 管道输入 |
| `cone_details.json` | 光锥全量详情（命途/星级/特效含叠影梯度/获取方式/故事） | 170 | 管道输入 + 故事兜底 |
| `char_cones.json` | 角色页「光锥推荐」表 | 96 | 攻略知识 |
| `char_skills.json` | 角色行迹满级数值表 | 96 | 已被 MCP `character_lookup` traces 覆盖（兜底） |
| `char_teams.json` | 角色页「配队推荐」表 | 96 | 攻略知识 |
| `char_relics.json` | 角色页「遗器推荐」表 | 97 | 攻略知识 |
| `relic_set_list.json` | 遗器套装列表（ch30） | 62 | 管道输入 |

## 版本更新流程

抓取管道脚本与解析坑见本 skill `maintenance/methodology.md`（v9/v10）与 `research-status.md`。新版本后重跑管道 → 覆盖本目录 → git diff 看官方数据变化 → 按 `maintenance/templates.md` 更新知识档；**遗器/光锥/角色详情的固化更新走项目侧管道**（私有 skill `sr-od-dev-relic-unpack` / avatar-extract 的版本更新工序，更新项目常量与 MCP 数据源）。research-status 记录新快照日期。

注意：部分字段为空=该词条模板差异或前瞻占位（百科页面三种模板形态见 methodology v10-41）。
