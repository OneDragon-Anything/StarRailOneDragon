---
name: sr-od-official-api
description: 需要直连官方接口查游戏数据时用——查当期跃迁卡池(这期 UP 是谁/卡池起止/UP 概率)、角色/光锥/物品的官方数据(数字 ID、官方英文名、命途属性、技能描述、养成材料)、大地图区域与锚点点位、货币战争官方配置——先打官方接口,别先翻第三方仓(StarRailRes/Dimbreath 系有 DMCA 或停更风险)。本 skill 是 API 索引手册:按平台(米游社/国际服 wiki/BWIKI)分目录,每份文档含端点、入参、出参结构、请求示例、特殊 id 映射规则与已知坑;探索过的新接口往这里沉淀。静态定义查询优先走 MCP 工具(character_lookup 等),MCP 未覆盖的动态内容走本手册。英文:official miHoYo API, wiki endpoints, gacha banner UP, character data, srmap。
---

# 游戏 API 索引手册(sr-od-official-api)

> 官方与权威站点接口的单一沉淀池:探索过一个接口就放一份文档(端点/入参/出参/示例/id 映射/坑)。数据管道与生成器不在此手册(归开发侧的数据维护流程,它们引用本手册取接口说明)。

## 与 MCP 查询工具的分工

| 查什么 | 走哪 |
|---|---|
| 角色/光锥/遗器的静态定义(已固化数据) | MCP `character_lookup` / `cone_lookup` / `relic_lookup`(零 IO,不需要登录) |
| 当期卡池 UP 与概率、图鉴原文、大地图点位等 MCP 未覆盖的动态内容 | 本手册,按平台查目录 |

## 平台目录

| 平台 | 目录 | 说明 |
|---|---|---|
| 米游社(国内) | `references/米游社/` | bbs.mihoyo.com/sr/wiki 系,业务 API 域 act-api-takumi(-static).mihoyo.com,中文数据 |
| 国际服 HoYoWiki | `references/国际服wiki/` | wiki.hoyolab.com,sg-act-public-api 域,header `x-rpc-language` 切语言(官方英文名唯一来源) |
| BWIKI | `references/BWIKI/` | wiki.biligame.com/sr(第三方社区 wiki,非官方),补官方 wiki 没有的数据 |

米游社与国际服是同一套内容体系的国内/国际版,**内容互补**:国内出中文数据,国际版切语言出其他语言,靠归一化中文名互连(见 `references/平台互连.md`)。

## 公共技巧(怎么发现与调用)

1. **从页面反向找接口**:打开目标内容页面 → DevTools/CDP 网络面板看它调了什么(域名、路径、GET/POST、body)→ 照抄参数直接调。页面本身就是现成的接口文档。
2. **页面不显示 ≠ API 没有**:渲染层常丢弃字段,原始响应里更多(实例:角色详情 API 里有游戏内数字 `avatarId`,页面完全不展示)。判断「有没有用」要看 API 响应,不能只看页面。
3. **详情比列表富**:列表接口给索引与筛选标签;逐条详情才有完整字段(数值表、技能描述、养成材料)。先列表拿 id,再逐条拉详情。
4. **幂等 GET 直连即可**(web 读取工具/Invoke-RestMethod 都行);POST 的 body 参数从页面实际请求照抄,自造参数会 405/参数异常。
5. **米哈游 API 家族约定**:`retcode: 0` = 成功;`x-rpc-wiki_app`/`x-rpc-language` 类头控制应用与语言;静态 CDN 域(`-static`)与业务域分家,详情常走 static 域。
6. **依赖纪律**:拉到的数据**先快照留档**再消费——官方接口也可能改版,快照即单一事实源;刷新是可选动作。
7. **内容是官方模板 + 社区维护**:新内容上线快,但存在空壳词条(字段缺失/占位值),消费前逐条校验关键字段。
8. **游戏内嵌网页(webview)是接口富矿**:游戏里点「攻略」「活动」等入口弹出的网页,后端就是官方接口(实例:货币战争攻略广场 API,见 `米游社/货币战争.md`)。发现渠道:①游戏里打开页面时抓其网络请求;②事后从游戏目录 `StarRail_Data/webCaches/<游戏版本>/Cache/Cache_Data/` 的 HTTP 缓存 grep URL(与社区抽卡链接提取同机制)。边界:缓存按版本轮换,只能找到**实际打开过**的页面——`/sr/event/` 命名空间下还有更多活动页未被发现,每次游戏里弹出新活动网页都值得记一笔。

## references 索引

- `references/米游社/wiki-角色.md` — 角色列表/详情接口、avatarId 位置、技能描述抽取、频道号清单
- `references/米游社/卡池.md` — 当期角色池 UP(含 UP 角色名二跳)、单池全量 JSON(光锥池/概率)、gacha_id 缓存提取
- `references/米游社/大地图.md` — 观测枢大地图(srmap):地图树/楼层底图/锚点点位接口、官方坐标系换算
- `references/米游社/货币战争.md` — 攻略广场 API(活动页后端)、CW 图鉴频道、icon 库映射约定
- `references/国际服wiki/wiki-角色.md` — 国际版 HoYoWiki 角色列表/详情(官方英文名唯一来源)、WAF 头要求
- `references/平台互连.md` — 两平台 id 不互通、归一化中文名连表、同名多形态坑
- `references/BWIKI/光锥晋阶材料.md` — 光锥晋阶材料页(官方 wiki 无此数据,BWIKI 独有)
