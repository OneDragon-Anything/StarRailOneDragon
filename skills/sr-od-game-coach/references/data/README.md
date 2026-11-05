# 角色页推荐表（references/data）

> 本目录现仅存**角色页推荐表**（攻略知识，MCP 不提供）：光锥推荐 / 遗器推荐 / 配队推荐。生成：2026-11-05（V4.7 期）。**skill 自包含**。

| 文件 | 内容 | 条数 |
|---|---|---|
| `char_cones.json` | 角色页「光锥推荐」表 | 96 |
| `char_relics.json` | 角色页「遗器推荐」表 | 97 |
| `char_teams.json` | 角色页「配队推荐」表 | 96 |

## 数据源现状（2026-11-05 起）

- **基础信息查询走 MCP**：角色（定义/行迹满级/星魂）→ `character_lookup`；光锥（星级/命途/特效/获取）→ `cone_lookup`；遗器（套装效果/单件）→ `relic_lookup`。原基础信息 JSON 快照（清单/详情/行迹数值表）已删除——MCP 常量为权威且随项目版本更新。
- **兜底 = 官方 wiki API 直查**（`sr-od-dev-official-api` skill 的 REST 接口，channel 18/19/30），任何环境可用，注意词条存在错字风险、解析有三类模板形态（见 `maintenance/methodology.md`）。
- **版本更新**：攻略推荐表重跑刷新（脚本在维护机 `.debug/temp/`，见 `research-status.md`）；遗器/光锥/角色详情的常量固化走项目侧管道（私有 skill `sr-od-dev-relic-unpack` / avatar-extract 的版本更新工序）。
