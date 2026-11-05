# 米游社百科数据快照（wiki_snapshot）

> 知识库 `sr-od-team-coach` 的官方数据底座快照。生成：2026-11-05（V4.7 期）。
> 用途：换机不丢 / 版本间 diff / 重跑比对。数据源与管道技术路径见 `skills/sr-od-team-coach/maintenance/methodology.md`（v9/v10）与 `research-status.md`。

| 文件 | 内容 | 条数 | 生成脚本（.debug/temp/，gitignore） |
|---|---|---|---|
| `character_full_list.json` | 国内 wiki 角色词条列表（name+content_id） | 101 | fetch_mhy_newchars（一期） |
| `cone_full_list.json` | 光锥词条列表（ch19） | 170 | fetch_cone_list.py |
| `cone_details.json` | 光锥全量详情（命途/星级/特效含叠影梯度/获取方式） | 170 | fetch_all_cones.py |
| `char_cones.json` | 角色页「光锥推荐」表（专武名/面板/推荐度/特效） | 96 | fetch_char_cones.py |
| `char_skills.json` | 角色行迹满级数值表 | 96 | fetch_char_skills.py |
| `char_teams.json` | 角色页「配队推荐」表 | 96 | fetch_char_teams.py |
| `char_relics.json` | 角色页「遗器推荐」表 | 97 | fetch_char_relics.py |
| `relic_set_list.json` | 遗器套装列表（ch30） | 62 | fetch_relic_sets.py（一期） |

## 版本更新流程

新版本后：把 .debug/temp/ 对应脚本重跑（脚本幂等有缓存，先删旧缓存 JSON）→ 覆盖本目录快照 → git diff 看官方数据变化 → 按 `skills/sr-od-team-coach/maintenance/templates.md` 更新知识档。

## 注意

- 百科页面有三种模板形态（新 rpg 模块/旧页签富文本/形态角色分词条）——解析坑见 methodology v10-41。
- 部分字段为空=该词条模板差异或前瞻占位，不是数据丢失。
