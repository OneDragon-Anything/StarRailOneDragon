# 米游社百科数据快照（references/data）

> skill 官方数据底座。生成：2026-11-05（V4.7 期）。**skill 自包含**——使用者的 agent 无需本项目其他文件。

| 文件 | 内容 | 条数 |
|---|---|---|
| `character_full_list.json` | 国内 wiki 角色词条列表（name+content_id） | 101 |
| `cone_full_list.json` | 光锥词条列表（ch19） | 170 |
| `cone_details.json` | 光锥全量详情（命途/星级/特效含叠影梯度/获取方式） | 170 |
| `char_cones.json` | 角色页「光锥推荐」表 | 96 |
| `char_skills.json` | 角色行迹满级数值表 | 96 |
| `char_teams.json` | 角色页「配队推荐」表 | 96 |
| `char_relics.json` | 角色页「遗器推荐」表 | 97 |
| `relic_set_list.json` | 遗器套装列表（ch30） | 62 |

## 版本更新流程

抓取管道脚本与解析坑见本 skill `maintenance/methodology.md`（v9/v10）与 `research-status.md`（脚本在维护机 `.debug/temp/`）。新版本后重跑管道 → 覆盖本目录 → git diff 看官方数据变化 → 按 `maintenance/templates.md` 更新知识档。

注意：部分字段为空=该词条模板差异或前瞻占位（百科页面三种模板形态见 methodology v10-41）。
