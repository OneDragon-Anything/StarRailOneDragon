# 米游社 wiki·角色数据接口

> 角色维度的官方中文数据:游戏内数字 avatarId、中文名、命途/属性/星级、技能描述、养成材料、阵营/实装日期。国际服(官方英文名)见 `../国际服wiki/wiki-角色.md`,两平台连表见 `../平台互连.md`。

## 列表(channel_id=18 = 角色频道,约 98 条)

```
GET https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1/home/content/list
    ?app_sn=sr_wiki&channel_id=18&lang=zh-cn
```

返回 `data.list`(频道数组)→ `.list`(条目)。每条:`content_id`、`title`(中文名)、`ext`(JSON 字符串,内含 `c_18.filter.text` = `["星级/五星","命途/记忆","属性/风"]` 筛选标签)。其他频道:19 光锥、20 养成材料、23 敌对物种、209/210 货币战争图鉴/员工。

## 详情

```
GET https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1/content/info
    ?app_sn=sr_wiki&content_id=<content_id>
```

关键字段位置:
- `data.content.rpg_new_tmp_content.base.userInfo` → **`avatarId`(游戏内数字 ID)**、`name`、`baseType`(命途类名,大小写混杂)、`elementId`(已小写)、`rarity`
- `rpg_new_tmp_content.modules` → 行迹组件(`componentId=='trace_graph'`)的 `points[]`,`tag=='秘技'` 的点含秘技名称+描述+subTag(削韧/强化/妨害等战斗标签);每个角色多技能,按 tag 找,别按位置
- `role_ascension` 组件 → 晋阶数值表与养成材料

## 已知坑

- `lang` 参数无效,恒中文
- 少数旧词条是空壳(有页面无 avatarId,实测:椒丘/白露);`avatarId=="0"` = 占位词条(未实装,如真珠)
- **前瞻未上线过滤**:行迹模块名带「前瞻」(如「角色行迹前瞻【请以正式版本为准】」)= 未实装;只查**模块名**,正文提及「前瞻」不算(攻略区常提及,整页文本搜索会误杀已上线角色)
- `baseType` 大小写混杂(Preservation/TheHunt/remembrance…),消费前统一 lower;TheHunt→hunt
- 实装日期/阵营在 `character_info` 组件的 textMap 里(键名「实装日期」「阵营」)
