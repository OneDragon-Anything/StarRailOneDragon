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

星铁角色养成明细（光锥/遗器/行迹逐角色）接口未验证（前置受阻，见下）；成功时结构预期与社区文档一致。

## 错误码分诊

| 码 | 语义 | 处置 |
|---|---|---|
| `-10001` invalid request | 头缺失/DS 格式错 | 核对头表与 DS2 算法（注意 DS1 是另一变体：r 为 6 位字母数字、q/b 不参与，勿混用） |
| `10001` Please login | cookie 未到达 | 查 cookie 域（前置第 2 步） |
| `10035`（星铁 index/note 特有，账号从未开通过战绩数据时） | 星铁战绩数据功能未开通 | 游戏内打开一次「漫游签证 → 战绩展示」tab 激活后实测变为 `10041`；已排除：签名、版本、Origin、设备指纹、隐私开关（判据：原神同调用返回 1034 而非 10035，链路本身正确） |
| `10041`（星铁 index/note 特有，激活后仍返回） | 语义未知，当前未解 | 与签名/头/隐私开关无关（同上对照实验）；待查米游社 App 侧是否有额外开通动作。规避：走游戏内画面读取 |
| `1034` | 风控验证码 | 换时间重试；频繁出现则降频（请求间隔拉大） |
| `1009` | 目标 UID 未公开数据 | 查错对象（他人 UID） |

## 排障序

1. 先用卡片接口确认凭据链路（它最宽松）。
2. 用原神 index 做对照：原神通而星铁不通 = 星铁功能未开通（10035 分支）；原神也 -10001 = 签名/头问题；都 1034 = 风控，降频。
3. 签名自查顺序：DS 格式 → salt → cookie 域 → UA 模拟。
