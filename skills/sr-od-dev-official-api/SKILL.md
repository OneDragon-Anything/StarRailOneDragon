---
name: sr-od-dev-official-api
description: 需要米哈游官方数据(角色/物品等游戏内容:数字 ID、中英文名、命途/属性/稀有度、技能描述、养成材料等)时用——官方 wiki 有大量可直接调的 REST API,先打官方接口,不要先翻第三方仓(StarRailRes/Dimbreath 系均有 DMCA 或停更风险)。SKILL.md 只讲两个平台入口与公共技巧;具体接口与参数按主题在 references/ 索引。英文:official HSR/miHoYo API, wiki endpoints, character data。
---

# 米哈游官方 API·入口与公共技巧

> 两个平台是同一套内容体系的国内/国际版,**内容互补**:国内出中文数据,国际版切语言出其他语言。都是纯 REST、无需登录、米哈游自营(无 DMCA/停更风险,但仍遵守依赖纪律,见下)。

## 平台入口

| | 国内 | 国际 |
|---|---|---|
| 页面 | bbs.mihoyo.com/sr/wiki | wiki.hoyolab.com |
| 业务 API 域 | act-api-takumi-static.mihoyo.com | sg-act-public-api.hoyolab.com(列表)/ sg-act-public-api-static.hoyolab.com(详情) |
| 语言 | `lang` 查询参数(实测无效,恒中文) | header `x-rpc-language`(zh-cn / en-us,实测有效) |

## 公共技巧(怎么发现与调用)

1. **从页面反向找接口**:打开目标内容页面 → DevTools/CDP 网络面板看它调了什么(域名、路径、GET/POST、body)→ 照抄参数直接调。页面本身就是现成的接口文档。
2. **页面不显示 ≠ API 没有**:渲染层常丢弃字段,原始响应里更多(实例:角色详情 API 里有游戏内数字 `avatarId`,页面完全不展示)。判断「有没有用」要看 API 响应,不能只看页面。
3. **详情比列表富**:列表接口给索引与筛选标签;逐条详情才有完整字段(数值表、技能描述、养成材料)。先列表拿 id,再逐条拉详情。
4. **幂等 GET 直连即可**(web_fetch/Invoke-RestMethod 都行);POST 的 body 参数从页面实际请求照抄,自造参数会 405/参数异常。
5. **米哈游 API 家族约定**:`retcode: 0` = 成功;`x-rpc-wiki_app`/`x-rpc-language` 类头控制应用与语言;静态 CDN 域(`-static`)与业务域分家,详情常走 static 域。
6. **依赖纪律**:拉到的数据**先快照进自有资产**(skill references / 仓库数据文件)再消费——官方接口也可能改版,快照即单一事实源;刷新是可选动作。
7. **内容是官方模板 + 社区维护**:新内容上线快,但存在空壳词条(字段缺失/占位值),消费前逐条校验关键字段。
8. **游戏内嵌网页(webview)是接口富矿**:游戏里点「攻略」「活动」等入口弹出的网页,后端就是官方接口(实例:货币战争攻略广场 API,见 references/currency-war.md)。发现渠道:①游戏里打开页面时抓其网络请求;②事后从游戏目录 `StarRail_Data/webCaches/<游戏版本>/Cache/Cache_Data/` 的 HTTP 缓存 grep URL(与社区抽卡链接提取同机制)。边界:缓存按版本轮换,只能找到**实际打开过**的页面——`/sr/event/` 命名空间下还有更多活动页未被发现,每次游戏里弹出新活动网页都值得记一笔。

## references 索引(具体接口与参数按主题分文档)

- `references/characters.md` — 角色数据:列表/详情接口、avatarId 位置、技能描述抽取、双语连表方式
- `references/currency-war.md` — 货币战争:攻略广场 API(活动页后端)、CW 图鉴频道、icon 库映射约定
- `references/map.md` — 观测枢大地图(srmap):地图树/楼层底图/锚点点位接口、官方坐标系换算、锄大地新地图产线素材源
