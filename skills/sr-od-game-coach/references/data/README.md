# 角色页推荐表（references/data）

> 本目录存**攻略知识与官方数据快照**（MCP 不提供的数据），**skill 自包含**。生成：2026-11-05（V4.7 期）起。

| 文件 | 内容 | 条数 |
|---|---|---|
| `char_cones.json` | 角色页「光锥推荐」表 | 96 |
| `char_relics.json` | 角色页「遗器推荐」表 | 97 |
| `char_teams.json` | 角色页「配队推荐」表 | 96 |

- **角色晋阶材料表 / 副本产出材料表已转代码常量**（单一源，不在本目录）：`src/sr_od/config/character_ascension_const.py`（92 角色分段材料 + `get_character_ascension` 查询）、`src/sr_od/config/dungeon_drop_const.py`（副本产出 + `find_dungeon_by_material` 反查）。生成与刷新：`skills/sr-od-dev-character-data/scripts/generate_ascension_const.py`（官方 wiki 直拉）。

## 数据源现状（2026-11-05 起）

- **基础信息查询走 MCP**：角色（定义/行迹满级/星魂）→ `character_lookup`；光锥（星级/命途/特效/获取）→ `cone_lookup`；遗器（套装效果/单件）→ `relic_lookup`。原基础信息 JSON 快照（清单/详情/行迹数值表）已删除——MCP 常量为权威且随项目版本更新。
- **兜底 = 官方 wiki API 直查**（`sr-od-dev-official-api` skill 的 REST 接口，channel 18/19/30），任何环境可用，注意词条存在错字风险、解析有三类模板形态（见 `maintenance/methodology.md`）。
- **版本更新**：攻略推荐表重跑刷新（脚本在维护机 `.debug/temp/`，见 `research-status.md`）；遗器/光锥/角色详情的常量固化走项目侧管道（私有 skill `sr-od-dev-equip-data` / avatar-extract 的版本更新工序）。
