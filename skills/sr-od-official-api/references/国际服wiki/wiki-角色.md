# 国际服 HoYoWiki·角色数据接口(官方英文名唯一来源)

> wiki.hoyolab.com 的 HSR wiki。官方英文名从这拿(米游社国内站只有中文名);不含 avatarId(游戏内数字 ID 走米游社,见 `../米游社/wiki-角色.md`;两平台连表见 `../平台互连.md`)。

## 列表

```
POST https://sg-act-public-api.hoyolab.com/hoyowiki/hsr/wapi/get_entry_page_list
header: Content-Type: application/json;charset=UTF-8
        x-rpc-wiki_app: hsr
        x-rpc-language: en-us        ← 切语言改这里(en-us 出官方英文名)
body:   {"filters":[],"menu_id":"104","page_num":1,"page_size":30,"use_es":true}
```

menu_id=104 = 角色(GET `.../get_menu_filters?menu_id=104` 可拿筛选枚举)。每条:`entry_page_id`、`name`(当前语言名)、`filter_values`(path/rarity/combat_type/factions,带 `enum_string` 已是小写规范如 `memory`/`wind`/`5`)、`display_field`(1 级/80 级基础数值)。响应结构 `data.list` 直接是条目数组(无国内版的频道树层)。

**已知坑**:纯 API 头(Content-Type + x-rpc-*)会被 WAF 403——必须带浏览器级头 `Origin: https://wiki.hoyolab.com` + `Referer` + 真实浏览器 `User-Agent`。

## 详情

```
GET https://sg-act-public-api-static.hoyolab.com/hoyowiki/hsr/wapi/entry_page?entry_page_id=<id>
header: x-rpc-wiki_app: hsr   +   x-rpc-language: <lang>
```

社区贡献模板(modules: 基本信息/画廊/晋阶/行迹/星魂/语音/故事…),`name` 即当前语言官方名。**不含 avatarId**。

详情页 URL = `wiki.hoyolab.com/pc/hsr/entry/<entry_page_id>`(`aggregate/<id>` 是列表页,列表卡片点击新开 entry 页)。
