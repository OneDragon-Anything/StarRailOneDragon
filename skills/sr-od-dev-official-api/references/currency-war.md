# 货币战争接口(攻略广场 API + 米游社 CW 图鉴频道)

> 现成采集器:`tools/cw/plaza_fetch.py`(config/lineups/icons 子命令,版本更新重跑;浏览器版 `plaza_harvest.js` 免环境粘 console)。生成器:`gen_plaza_chars.py`(角色文档+立绘库+对拍)/`gen_plaza_comps.py`/`gen_plaza_invest.py`/`gen_equip_registry.py`。

## 攻略广场 API(活动页后端,免登录公开)

来源页面:**游戏内点「攻略」打开的内嵌网页(webview)** `act.miyoushe.com/sr/event/currency-wars/`(接口从该页网络请求破解,2026-08-15;发现渠道的通用性见 SKILL.md 技巧 8)。

```
BASE = https://act-api-takumi.miyoushe.com/event/rpgcurrencywar
必需 header: x-rpc-currencywar-tourn: tourn   (缺了 retcode != 0)

GET  {BASE}/game/config?game=hkrpg        → V<x.y> 官方全量配置(角色/装备/羁绊 id 与数值)
POST {BASE}/game/lineup/index             → 攻略列表(每条含完整三阶段阵容)
GET  {BASE}/game/lineup/detail?id=<id>    → 单篇详情(列表已含同等结构,一般不用)
```

lineup/index 要点:
- body 关键字段:`order: 'Hot' | 'Recommend'`(其余值 -502);分页用 `data.next_page_token` 回传(**cursor 非页码**);page/limit 服务端封顶 10/页
- 可筛选:`role_ids: [1009,…]` / `trait_ids: [1001,…]`(id 见 config)

图片映射约定(**稳定键 = 数字 id**,如 role 1009=艾丝妲 / equip 35030102=火力风暴潮;icon URL 是 id 派生物带资源 hash,版本更新会变,名字也可能改):
1. 本地图片存 `icons/<kind>/<id>.png`(id 命名,URL/改名都不破映射)
2. id↔name↔icon_url 存 `manifest_v<版本>.json`,重跑 config 自动 diff 出 新增/移除/URL变更/改名
3. 无 id 场景(游戏截图)→ SIFT 对 icons/ 库匹配(58px 游戏图标 ↔ 128px 官方图 4/4 命中;⚠️ 特权/普通同 art 装备 SIFT 同分,需框色二次仲裁)

## 米游社 wiki CW 频道(图鉴/员工词条)

同角色接口(`references/characters.md` 的列表/详情端点),换频道号:
- `channel_id=209` = 货币战争图鉴(父频道)
- `channel_id=210` = 员工(子频道,`content/info` 单条详情;费用/站位在 ext 筛选标签)
- 注意:员工词条走社区模板,**不含 avatarId**;角色规范名以 CW 注册表(`cw_chars.py`)为准,规范名原则 = plaza 名 U+2022 统一为 ·、开拓者双形态按 id 映射(8009=欢愉 Back/8007=记忆 Front)
