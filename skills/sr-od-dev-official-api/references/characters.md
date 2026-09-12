# 角色数据接口(国内米游社 + 国际版 HoYoWiki)

> 角色维度的官方数据:游戏内数字 avatarId、中/英文名、命途/属性/星级、技能描述、养成材料、阵营/实装日期。两个平台各出一半,靠**归一化中文名**互连。

## 国内米游社(avatarId 唯一官方来源)

**列表**(channel_id=18 = 角色频道,约 98 条):

```
GET https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1/home/content/list
    ?app_sn=sr_wiki&channel_id=18&lang=zh-cn
```

返回 `data.list`(频道数组)→ `.list`(条目)。每条:`content_id`、`title`(中文名)、`ext`(JSON 字符串,内含 `c_18.filter.text` = `["星级/五星","命途/记忆","属性/风"]` 筛选标签)。其他频道:19 光锥、20 养成材料、23 敌对物种、209/210 货币战争图鉴/员工。

**详情**:

```
GET https://act-api-takumi-static.mihoyo.com/common/blackboard/sr_wiki/v1/content/info
    ?app_sn=sr_wiki&content_id=<content_id>
```

关键字段位置:
- `data.content.rpg_new_tmp_content.base.userInfo` → **`avatarId`(游戏内数字 ID,即解包头像文件名)**、`name`、`baseType`(命途类名,大小写混杂)、`elementId`(已小写)、`rarity`
- `rpg_new_tmp_content.modules` → 行迹组件(`componentId=='trace_graph'`)的 `points[]`,`tag=='秘技'` 的点含秘技名称+描述+subTag(削韧/强化/妨害等战斗标签);每个角色多技能,按 tag 找,别按位置
- `role_ascension` 组件 → 晋阶数值表与养成材料

**已知坑**:
- `lang` 参数无效,恒中文
- 少数旧词条是空壳(有页面无 avatarId,实测:椒丘/白露);`avatarId=="0"` = 占位词条(未实装,如真珠)
- **前瞻未上线过滤**:行迹模块名带「前瞻」(如「角色行迹前瞻【请以正式版本为准】」)= 未实装;只查**模块名**,正文提及「前瞻」不算(攻略区常提及,整页文本搜索会误杀已上线角色)
- `baseType` 大小写混杂(Preservation/TheHunt/remembrance…),消费前统一 lower;TheHunt→hunt
- 实装日期/阵营在 `character_info` 组件的 textMap 里(键名「实装日期」「阵营」)

## 国际版 HoYoWiki(官方英文名唯一来源)

**列表**:

```
POST https://sg-act-public-api.hoyolab.com/hoyowiki/hsr/wapi/get_entry_page_list
header: Content-Type: application/json;charset=UTF-8
        x-rpc-wiki_app: hsr
        x-rpc-language: en-us        ← 切语言改这里(en-us 出官方英文名)
body:   {"filters":[],"menu_id":"104","page_num":1,"page_size":30,"use_es":true}
```

menu_id=104 = 角色(GET `.../get_menu_filters?menu_id=104` 可拿筛选枚举)。每条:`entry_page_id`、`name`(当前语言名)、`filter_values`(path/rarity/combat_type/factions,带 `enum_string` 已是小写规范如 `memory`/`wind`/`5`)、`display_field`(1 级/80 级基础数值)。

**详情**:

```
GET https://sg-act-public-api-static.hoyolab.com/hoyowiki/hsr/wapi/entry_page?entry_page_id=<id>
header: x-rpc-wiki_app: hsr   +   x-rpc-language: <lang>
```

社区贡献模板(modules: 基本信息/画廊/晋阶/行迹/星魂/语音/故事…),`name` 即当前语言官方名。**不含 avatarId**。

详情页 URL = `wiki.hoyolab.com/pc/hsr/entry/<entry_page_id>`(`aggregate/<id>` 是列表页,列表卡片点击新开 entry 页)。

## 两边互连与已知坑

- **id 不互通**:米游社 `content_id` ≠ HoYoWiki `entry_page_id`,连表键 = **归一化中文名**(•/·/・统一、去空格)
- **同名多形态禁止裸中文名匹配**(三月七 vs 仙舟三月七会撞)——先用已知对锚定再匹配
- 英文名归一化(小写去符号)= 社区 tag 惯例("Robin • Summeretto" → `robinsummeretto`),可直接当英文 id 建议;但**不是**游戏资产内部代号(那个只在解包容器路径里)
- 开拓者各形态在两站都同名(开拓者·毁灭),男女只能靠性别信息源区分,勿按中文名合并
