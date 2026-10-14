# 米游社官方数据接口操作手册（国服 game_record）

> 全部条目来自 2026-10 实测。签名体系基于社区公开文档（UIGF-org/mihoyo-api-collect）与 `@mihoyo-kit/api` 的国服 salt 表。

## 前置与凭据

1. 专用调试 Edge（CDP 19999）里需有米游社（www.miyoushe.com）登录态；过期则让用户在该浏览器扫码重新登录，**agent 不代输密码**。
2. 登录后 cookie 落在 `miyoushe.com` 域，而数据接口在 `api-takumi-record.mihoyo.com`（`.mihoyo.com` 域）——直接 fetch 会报 `Please login`。处理：从米游社页面发出的任一 XHR 的请求头里读完整 cookie（网络面板可见 HttpOnly 值），再在任一 `.mihoyo.com` 页面上下文用 `document.cookie = 'k=v; domain=.mihoyo.com; path=/; max-age=...'` 写入。全程不落盘。
3. `.mihoyo.com` 域下可停留的页面：`https://api-takumi.mihoyo.com/<任意路径>`（404 页即可，不重定向；`bbs.mihoyo.com` 会 302 回 miyoushe 不可用）。

## 请求签名（DS，必带）

- 算法 **DS2**：`t = 秒级时间戳`，`r = 100001~200000 随机整数`，`digest = md5("salt={4X}&t={t}&r={r}&b={body}&q={query}")`，DS 头 = `"{t},{r},{digest}"`。
- `query`：URL 参数按 key 字母序排序后拼接（如 `role_id=xxx&server=prod_gf_cn`）；`body`：POST 的 JSON 按 key 排序后 stringify；GET 时 `b` 为空串。
- 4X salt（版本恒定）：`xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs`。
- md5 在本地算（Node `crypto` / Python `hashlib`），算好把 DS 字符串塞进浏览器 fetch 的头里；时间窗口宽裕，两步间隔数秒无碍。

## 请求头

| 头 | 值 | 说明 |
|---|---|---|
| `DS` | 见上 | 必带；格式错报 `-10001` |
| `x-rpc-app_version` | `2.69.1` | 与 4X salt 配套的 Hoyolab 版本号，实测可用 |
| `x-rpc-client_type` | `5` | webview 客户端类型 |
| `x-requested-with` | `com.mihoyo.hyperion` | 国服米游社 App 标识 |
| `Cookie` | 浏览器自动携带 | 需要 `ltoken_v2` 有效 |

配套措施：把浏览器 UA 模拟成安卓 webview（`Mozilla/5.0 (Linux; Android 13; ...) ... Mobile Safari/537.36 miHoYoBBS/2.69.1`）再发请求（chrome-devtools `emulate` 的 `userAgent`）；官方战绩 H5 页在 Windows UA 下只出宣传落地页，安卓 UA 下才进真实页面。

## 接口清单（国服）

| 接口 | 方法 | 参数 | 返回 |
|---|---|---|---|
| `https://api-takumi-record.mihoyo.com/game_record/app/card/wapi/getGameRecordCard` | GET | `uid={米游社UID}` | 全部绑定游戏卡片：区服/游戏UID/等级/活跃天数/角色数/成就数/数据开关。**探测用第一步**，老接口校验宽松 |
| `.../game_record/app/hkrpg/api/index` | GET | `role_id={游戏UID}&server=prod_gf_cn` | 账号概览 + 全角色列表（id/等级/命途/稀有度） |
| `.../game_record/app/hkrpg/api/note` | GET | 同上 | 实时便签：开拓力/委托/每日实训进度/历战余响剩余 |
| `.../game_record/app/genshin/api/index` | GET | `role_id={原神UID}&server=cn_gf01` | 原神同构数据（对照实验用） |

星铁角色养成明细的**正确端点是 `avatar/info`**（2026-10-14 经 genshin.py 源码确认，非 `index`）：

| 接口 | 方法 | 参数 | 返回 |
|---|---|---|---|
| `.../game_record/app/hkrpg/api/avatar/info` | GET | `need_wiki=true&role_id={游戏UID}&server=prod_gf_cn` | **全角色完整练度**：等级/星魂/行迹/光锥/遗器（含副词条）/属性面板/忆灵。用自己的 cookie 查自己 = 全量；查他人 uid 只返回简化数据（无行迹/遗器词条） |
| `https://api-takumi-record.mihoyo.com/game_record/app/card/wapi/changeDataSwitch` | POST | `{"switch_id":N,"is_public":true,"game_id":6}` | 数据开关。N：1=战绩公开、2=角色详情公开、3=实时便签；星铁 game_id=6。**DS 签 body** |
| `https://public-data-api.mihoyo.com/device-fp/api/getFp` | POST | 设备信息 JSON（device_id/seed_id/ext_fields 等） | `x-rpc-device_fp` 设备指纹。本地简版 body 会返回空 fp；米游社官方网页（www.miyoushe.com）自己调用 getFp 时带完整浏览器指纹 ext_fields，从其网络面板直接抄真实 fp 最省事 |

实测数据开关三件套已全部经 API 打开成功（retcode 0），开关不是阻塞项。

## 风控（极验）——当前的真正阻塞

**genshin.py 权威定义**（`constants.py`）：`GEETEST_RETCODES = {10035, 5003, 10041, 1034}` —— **10035 和 10041 都是极验验证码触发码**，不是「功能未开通」（此前归因有误，特此修正）。

实测链路（2026-10-14，含人工验证对照实验）：
1. 不带 `x-rpc-device_fp` → `10041`
2. 带官方网页真实 device_fp → `10041` 变 `10035`（过了第一层设备风控）
3. 开全部数据开关、换 Referer → 仍 `10035`
4. **人工极验对照实验**：按 genshin.py 规格自建验证页（gt.0.5.0.js + api_server=api.geetest.com + no-referrer + 专用 DS `q=is_high=false` + create 头带 x-rpc-page/tool-version）成功弹出点选题，真人鼠标完成验证拿到 validate/seccode，随后带 `x-rpc-challenge/validate/seccode` 头重试 index/note/avatar-info → **仍 10035**
5. 同凭证对照：卡片接口 getGameRecordCard 稳定 retcode 0，明细接口族（index/note/avatar-info）统一 10035

结论：10035 对明细接口族是**网关级拒绝**（IP/环境信誉评分），人工极验+票据不解除；开源项目的极验处理流程（genshin.py auth/server.py 全套）可完整复现但同样无效。排查方向只剩环境：更换出口 IP（如手机热点）后低频重试，或长期等 IP 信誉恢复。**规避：走游戏内画面读取路线。**

关键规格备忘（下次重试直接用）：
- create_mmt 头：`x-rpc-app_version: 2.60.1`、`x-rpc-client_type: 5`、`x-rpc-challenge_game: 6`、`x-rpc-page: v1.4.1-rpg_#/rpg`、`x-rpc-tool-version: v1.4.1-rpg`；DS 的 `q=` 恒为 `is_high=false`
- 验证页：`https://static.geetest.com/static/js/gt.0.5.0.js`（版本敏感）+ `<meta name="referrer" content="no-referrer"/>` + initGeetest 必传 `api_server: "api.geetest.com"`（漏传连国际服务器必失败）

## 错误码分诊

| 码 | 语义 | 处置 |
|---|---|---|
| `-10001` invalid request | 头缺失/DS 格式错 | 核对头表与 DS2 算法（注意 DS1 是另一变体：r 为 6 位字母数字、q/b 不参与，勿混用） |
| `10001` Please login | cookie 未到达 | 查 cookie 域（前置第 2 步） |
| `10035` / `10041` | **极验验证码触发**（同 1034 一族） | 带 device_fp 可过第一层（10041→10035）；彻底解除需 App 侧过一次验证。规避走路线二 |
| `1034` | 风控验证码 | 换时间重试；频繁出现则降频（请求间隔拉大） |
| `1009` | 目标 UID 未公开数据 | 查错对象（他人 UID） |

## 排障序

1. 先用卡片接口确认凭据链路（它最宽松）。
2. 明细接口先带 device_fp（官方网页 getFp 抄现成的），再确认数据开关已开（changeDataSwitch 幂等，直接全开）。
3. 仍 10035/10041 = 极验环节，转路线二；签名自查顺序：DS 格式 → GET/POST 的 q/b 选择 → cookie 域。
