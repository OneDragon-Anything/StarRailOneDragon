# 米游社官方接口全链路规格（以 teyvat-resin-planner 为对照基准）

> 目的：在自家仓库（Python）实现「密码登录 → game_record 数据读取（原神/星铁通用管线）」能力前，把已被实测证明可跑通的参考实现逐行摸清并固化成规格。
>
> 参考实现：`teyvat-resin-planner`（MIT，Node 22 零依赖），本机克隆于 `.debug/temp/teyvat-resin-planner/`（不入 git）。本文所有 `文件名:行号` 均指该目录下文件；所有常量已内联，无需翻参考仓库。
>
> 实测背书（2026-11-03）：密码登录 → 原神 game_record 全链路 3 接口零错误；同一会话探测星铁 hkrpg `index`/`note`/`avatar/info` 全部一次通过、零人机验证（过程记录见 `skills/sr-od-account-inspection/references/api.md`「复核实验」节）。
>
> 外部交叉验证源：UIGF-org/mihoyo-api-collect（https://github.com/UIGF-org/mihoyo-api-collect ，本文引用其 `other/authentication.md`、`hoyolab/login/password_passport.md`、`other/error_code.md`、`hoyolab/user/token.md`，下文简称「UIGF 文档」）。与 UIGF 不一致处以「⚠️」标注并给参考实现的实测依据。

---

## 1. 总览：链路图（文字版）

整条链路共 11 步，分 5 个环节：

```
环节 A：设备身份（可离线，先于登录）
  [1] 加载/生成设备 ID（device.json 持久化）
  [2] 注册设备指纹 getFp → 得 x-rpc-device_fp（可选，失败降级为无 fp）
环节 B：登录（一次性，产出会话）
  [3] 密码登录 loginByPassword（RSA 加密账号密码 + 登录专用 DS）
  [4] 收取响应 Set-Cookie → 内存 cookie jar（全量透传）
环节 C：game_record 业务请求（每次刷新）
  [5] 查绑定角色 getUserGameRolesByCookie（api-takumi 域）
  [6] 逐接口拉数据：dailyNote / character/list / character/detail（DS2 签名）
环节 D：风控验证链（仅 1034 触发时）
  [7] 记录被拒请求（path + x-trace-id）
  [8] createVerification（带 challenge_path/trace 头，得 gt/challenge）
  [9] 浏览器端极验组件人工验证（initGeetest → getValidate）
  [10] verifyVerification（提交 geetest 三元组）→ 换回已验证 challenge
  [11] 后续业务请求带 x-rpc-challenge 头重试
环节 E：数据规范化落盘
  （参考实现 normalizeAccount/mergeAccount；我们仓库自定义为 YML/JSON 档案）
```

星铁（hkrpg）与原神走同一管线：同样的设备头、同样的 DS2、同样的 cookie jar，仅 URL 路径与 query 参数不同（`game_record/app/hkrpg/api/*`、`server=prod_gf_cn`）。参考实现用「本地实验补丁」`account-controller.mjs:26-32`（`hkrpgProbe`）复用通用 `request()` 管线探测星铁接口，证明该管线与游戏分区无关。

---

## 2. 登录流程

### 2.1 端点与请求

- **URL**：`POST https://passport-api.miyoushe.com/account/ma-cn-passport/web/loginByPassword`（`account-client.mjs:23`）
- **body**（紧凑 JSON，无空格）：`{"account":"<RSA密文>","password":"<RSA密文>"}`
- **加密**：账号与密码**都**做 RSA 加密（`account-client.mjs:22-23`）：`RSA PKCS1 padding` + base64。
- **连接策略**：`redirect: 'error'`，超时 20 秒（`account-client.mjs:23`）。

### 2.2 RSA 公钥（原文，1024-bit）

`account-client.mjs:4-9`：

```
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDDvekdPMHN3AYhm/vktJT+YJr7
cI5DcsNKqdsx5DZX0gDuWFuIjzdwButrIYPNmRJ1G8ybDIF7oDW2eEpm5sMbL9zs
9ExXCdvqrn51qELbqj0XxtMTIpaCHFSI50PfPpTFV9Xt/hmyVwokoOXFlAEgCn+Q
CgGs52bFoYMtyi+xEQIDAQAB
-----END PUBLIC KEY-----
```

与 UIGF 文档 `hoyolab/login/password_passport.md` 的 Python 示例公钥**逐字一致**（UIGF 注明出处为其仓库 issue #1）。Python 对应实现：`cryptography` 或 `pycryptodome` 的 `PKCS1_v1_5`（即 PKCS#1 v1.5 padding）。

### 2.3 登录专用 DS（与 game_record 的 4X salt 不同！）

`account-client.mjs:21`：

- **salt**：`LyD1rXqMv2GJhnwdvCBjFOKGiKuLY3aO`（登录专用，32 字符）
- **签名串**：`salt=LyD1rXqMv2GJhnwdvCBjFOKGiKuLY3aO&t={t}&r={r}`（只有 t/r 两段，**无 b/q**）
- `t` = 秒级 Unix 时间戳；`r` = `crypto.randomBytes(4).toString('hex').slice(0,6)`，即 **6 位小写十六进制**
- `digest` = md5(签名串) 的小写 hex；DS 头值 = `{t},{r},{digest}`
- 头名小写 `ds`（`account-client.mjs:23`，HTTP 头大小写不敏感）

⚠️ **与 UIGF 的关系**：UIGF `authentication.md` 把「无 b/q 的三段式」归为 DS1（并称其 r 为「6 位大小写字母+数字」）。参考实现用 6 位 hex（是字母数字集合的子集）+ 登录专用 salt，实测通过。UIGF 文档本身不含此 salt（其 salt 清单放在仓库 issue），「登录 salt 是独立的、与 4X 不同」这一事实由参考实现硬编码 + 实测佐证。

### 2.4 登录请求头全集（`account-client.mjs:23`）

| 头 | 值 |
|---|---|
| `x-rpc-device_id` | 设备 UUID v4（小写），见 §3 |
| `x-rpc-device_fp` | getFp 返回的指纹；**获取失败时不带此头**（降级） |
| `x-rpc-platform` | `4` |
| `Content-Type` | `application/json` |
| `x-rpc-app_id` | `bll8iq97cem8`（米游社应用 ID；UIGF `token.md` 的 getTokenBySToken 条目同样要求 `x-rpc-app_id: bll8iq97cem8`，互为印证） |
| `x-rpc-client_type` | `4`（UIGF：网页端） |
| `x-rpc-source` | `v2.webLogin` |
| `x-rpc-game_biz` | `bbs_cn` |
| `x-rpc-sdk_version` | `2.31.0` |
| `ds` | 上节登录 DS |

参考实现登录时**不带** `X-Requested-With`、不带 `Referer`、UA 用 Node fetch 默认（未覆盖）——见 §6 不一致清单。

### 2.5 Set-Cookie 与会话管理

- **收取规则**（`account-client.mjs:26`）：遍历响应全部 `Set-Cookie` 行，每行取 `;` 前的第一个 `k=v` 对，存入内存 `Map`；后续所有请求按 `k1=v1; k2=v2; ...` 拼进 `Cookie` 头（`account-client.mjs:31`）。
- **不维护 cookie 名单**：全量透传，不区分 ltoken/stoken/mid。登录成功判据 = `retcode === 0` 且 cookie jar 非空（`account-client.mjs:24`）。
- loginByPassword 下发的具体 cookie 名清单：**两层口径**（2026-11-04 实测修订）——**登录响应层下发 10 个**：`aliyungf_tc`、`uni_web_token`、`cookie_token_v2`、`account_mid_v2`、`account_id_v2`、`ltoken_v2`、`ltmid_v2`、`ltuid_v2`、`account_id`、`ltuid`（核心凭据 = `ltoken_v2` + `cookie_token_v2` + 三个 v2 身份件）；`acw_tc` 不在登录响应层，系**后续业务响应的滚动件**（2026-11-03 session.json 曾计 11 个 = 10 + acw_tc 滚入）。对账时两层分别计数，勿按 11 对登录响应。UIGF `authentication.md` Cookie 节的米游社 cookie 族可作对照名单。
- ⚠️ **与 UIGF 的差异**：UIGF `password_passport.md`/`token.md` 描述的是「login_by_password → Login Ticket → getMultiTokenByLoginTicket → getTokenBySToken → …」的**多步 token 交换链**；参考实现**零 token 交换**——登录响应 Set-Cookie 直接入 jar 后即可直连 game_record，实测成立。我们实现时照参考实现（简单且被实测证明）。
- cookie 域：参考实现不分域全量携带。其主机白名单（`account-client.mjs:11`）为 `passport-api.miyoushe.com`、`api-takumi.mihoyo.com`、`api-takumi-record.mihoyo.com`、`bbs-api.miyoushe.com`（只允许 https，`account-client.mjs:28`）。

---

## 3. 设备身份（`account-device.mjs`）

### 3.1 device.json 结构与 device_id 生成

- 存储文件：`.private/device.json`，结构 `{"schemaVersion":1,"deviceId":"<uuid-v4>"}`（写入于 `account-device.mjs:25`；本机实测文件即此结构，deviceId 已脱敏不录）。
- 生成规则：`crypto.randomUUID()`（UUID v4）；读取时用正则 `/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i` 校验，不合法则重新生成并落盘（`account-device.mjs:9,25`）。UIGF `authentication.md` 对 PC 侧的建议同为 `uuid4()`，一致。
- 写盘安全措施：先写临时文件再 rename（`account-device.mjs:22`）。

### 3.2 getFp 请求（`account-device.mjs:6,13-18,31`）

- **URL**：`POST https://public-data-api.mihoyo.com/device-fp/api/getFp`（UIGF `authentication.md` x-rpc-device_fp 节同款端点，一致）
- **请求头**：`Content-Type: application/json`、`Referer: https://act.mihoyo.com/`、`User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36`（`account-device.mjs:8,31`）
- **body**（`fingerprintBody`，`account-device.mjs:13-18`）：

```json
{
  "seed_id": "<每次随机 16 位 hex>",
  "device_id": "<deviceId 大写>",
  "platform": "1",
  "seed_time": "<Date.now() 毫秒字符串>",
  "ext_fields": "<下述 JSON 的字符串化>",
  "app_name": "bbs_cn",
  "device_fp": "38d7ee834d1e9"
}
```

- **ext_fields 指纹模板**（固定兼容参数，**不是**本机真实硬件读数；出处 SeelieEx，MIT，见 `THIRD_PARTY_NOTICES.md:9`，上游固定参考提交 `c298631e9858ef6088b62c9b4c872ddd52c677a7`）。字段清单（20 个，值原文内联）：

| 字段 | 值 |
|---|---|
| `proxyStatus` | `0` |
| `accelerometer` | `-0.159515x-0.830887x-0.682495` |
| `ramCapacity` | `3746` |
| `IDFV` | `<deviceId 大写>`（唯一动态字段） |
| `gyroscope` | `-0.191951x-0.112927x0.632637` |
| `isJailBreak` | `0` |
| `model` | `iPhone12,5` |
| `ramRemain` | `115` |
| `chargeStatus` | `1` |
| `networkType` | `WIFI` |
| `vendor` | `--` |
| `osVersion` | `17.0.2` |
| `batteryStatus` | `50` |
| `screenSize` | `414×896` |
| `cpuCores` | `6` |
| `appMemory` | `55` |
| `romCapacity` | `488153` |
| `romRemain` | `157348` |
| `cpuType` | `CPU_TYPE_ARM64` |
| `magnetometer` | `-84.426331x-89.708435x-37.117889` |

### 3.3 fp 校验、缓存与降级（`account-device.mjs:32-37`）

- 成功判据（**四条同时满足**）：HTTP ok、`retcode===0`、`data.code===200`、fp 匹配 `/^[a-z0-9]{6,100}$/i`。注释明言「仅 retcode=0 不够：FP 服务仍可能返回 data.code=403」（`account-device.mjs:33-34`）。
- 缓存 24 小时（86400000 ms）；失败则 fp 置空、30 分钟（1800000 ms）内不重试（`account-device.mjs:35-36`）。
- 降级策略：fp 拿不到就**不带** `x-rpc-device_fp` 头，其余请求照发（实测登录与 game_record 在有/无 fp 两种形态下均可用；fp 缺失在星铁明细上曾观察到 10041→10035 的分层风控效应，见 `skills/sr-od-account-inspection/references/api.md` 错误码节）。

### 3.4 设备头产出口径（`account-device.mjs:39`）

每次请求实时返回：

```
x-rpc-device_id: <deviceId 小写>
x-rpc-device_fp: <fp>        # 仅成功获取时携带
x-rpc-platform: 4
```

登录（client_type=4 网页）与 game_record（client_type=5）**共用同一套设备头**——参考实现刻意保持「platform-1 的 FP 注册」与「platform-4 的请求头」分离（`account-device.mjs:11-12` 注释），即 getFp body 里 `platform:'1'` 是注册口径，请求头 `x-rpc-platform:'4'` 是使用口径，两者不矛盾。

---

## 4. game_record 签名请求规范

### 4.1 DS2 算法（`account-client.mjs:13`）

- **salt**：`xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs`（即社区通称「4X salt」；UIGF `authentication.md` DS2 示例同一常量；`skills/sr-od-account-inspection/references/api.md:15` 同款，三源一致）
- `t` = 秒级 Unix 时间戳
- `r` = `crypto.randomInt(100001, 200001)`，取值域 **[100001, 200000]** 闭区间整数
  - ⚠️ UIGF 主流程写「100000~200000 随机，抽到 100000 则改为 642367」，但其注释同时给出等价简化式 `random.randint(100001, 200000)`——参考实现即该简化式，实测通过。
- **q**：GET 的 URL 参数按 key 字母序排序后做 URL 编码拼接（`new URLSearchParams(Object.entries(query).sort(([a],[b])=>a.localeCompare(b))).toString()`）。无参数时为空串。POST 请求 `q` 同样取其 URL 参数（body 与 query 不同时存在）。
- **b**：POST 的 body **实际发送字符串**（见下）；GET 时为空串。
- `digest` = md5(`salt={salt}&t={t}&r={r}&b={b}&q={q}`) 小写 hex
- DS 头值 = `{t},{r},{digest}`

**b 的关键细节**（`account-client.mjs:30`）：实际发送的 body = `JSON.stringify(body).replace(/,/g,', ').replace(/:/g,': ')`——即紧凑 JSON 再把 `,`→`, `、`:`→`: `（带空格分隔符的 JSON），DS 的 b 与发送 body 用**同一个字符串**。⚠️ UIGF 示例用「key 排序后的紧凑 JSON」，参考实现不排序 key、且带空格——两种都被服务端接受（实测）。理解：服务端重算 DS 时按收到的内容规范化（解析 query/JSON 后重排重算），客户端只需保证 b/q 与实际发送内容自洽。

**GET/POST 差异**：GET 时 `b=''`、q 必须覆盖全部 URL 参数；POST 时 b=完整 body 串、q=URL 参数串（无 URL 参数则空串）。`body??''` 兜底（`account-client.mjs:13`）。

### 4.2 请求头全集（`account-client.mjs:31`）

| 头 | 值 |
|---|---|
| `x-rpc-device_id` / `x-rpc-device_fp` / `x-rpc-platform` | 同 §3.4 |
| `Content-Type` | `application/json` |
| `Cookie` | jar 全量 `k=v; k2=v2` |
| `x-rpc-app_version` | `2.11.1` |
| `x-rpc-client_type` | `5` |
| `Referer` | `https://webstatic.mihoyo.com/`（UIGF：client_type 5 → webstatic，一致） |
| `User-Agent` | `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36`（桌面 Chrome 形态） |
| `ds` | DS2 结果 |
| `x-rpc-challenge` | 仅风控验证通过后携带（§5） |

⚠️ **与 UIGF 的差异**（均为「UIGF 说要、参考实现没有、实测照过」）：
1. UIGF 要求 UA 为安卓 webview 形态（`...Mobile Safari/537.36 miHoYoBBS/<版本>`）；参考实现用桌面 Chrome UA。实测通过。我们 skill 侧 `api.md` 的浏览器路线则须用安卓 UA（那是「官方 H5 页面」的前提，与直接 API 调用是两条路）。
2. UIGF 要求 DS 类请求带 `X-Requested-With: com.mihoyo.hyperion`；参考实现全程不带。实测通过。
3. UIGF 称 `x-rpc-app_version` 与 salt 按版本配套；参考实现恒定 `2.11.1` 配 4X salt。实测通过（我们 skill 侧浏览器路线用 `2.69.1` 同样通过——该头当前不被严格校验）。

连接策略：`redirect: 'error'`，超时 25 秒（`account-client.mjs:37`）；非 2xx 视为失败（`account-client.mjs:38`）。

### 4.3 业务端点清单（原神实测 + 星铁同管线）

| 端点 | 方法 | query / body | 出处 |
|---|---|---|---|
| `https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie?game_biz=hk4e_cn` | GET | query `game_biz` | `account-client.mjs:57` |
| `.../game_record/app/genshin/api/dailyNote` | GET | query `role_id`(字符串), `server` | `account-client.mjs:65` |
| `.../game_record/app/genshin/api/character/list` | POST | body `{role_id, server}` | `account-client.mjs:66` |
| `.../game_record/app/genshin/api/character/detail` | POST | body `{role_id, server, character_ids:[int]}` | `account-client.mjs:74` |
| `.../game_record/app/hkrpg/api/index`、`/note`、`/avatar/info`（星铁） | GET | query `role_id`, `server=prod_gf_cn`；`avatar/info` 加 `need_wiki=true` | `account-controller.mjs:28-32` + `skills/sr-od-account-inspection/references/api.md` 接口清单节（2026-11-03 实测全通过） |

`role_id` 一律字符串化（`account-client.mjs:61` `params={role_id:String(role.game_uid),...}`）。

### 4.4 响应处理与成功结构（`account-client.mjs:39-43`）

- 每次响应（无论成败）都收取 Set-Cookie 更新 jar（服务端会滚动下发新值）。
- 成功 = JSON `retcode===0`，业务数据在 `data` 字段（`request()` 返回 `data.data`）。
- 实测消费到的成功结构（由 `account-model.js:49-65` 的字段消费反推，均为真实字段名）：
  - `getUserGameRolesByCookie` → `data.list[]`: `game_biz, game_uid, region, region_name, nickname, level, is_chosen`
  - `dailyNote` → `data`: `current_resin, max_resin, resin_recovery_time, current_home_coin, max_home_coin, finished_task_num, total_task_num, remain_resin_discount_num, resin_discount_num_limit, expeditions[]{status, remained_time}`
  - `character/list` → `data.list[]`: 角色 base 概要（`id, name, level, rarity, element, ...`）
  - `character/detail` → `data.list[]`: `base{...}` + `weapon{...}` + `relics[]/skills[]` 等完整面板
  - 星铁 `avatar/info` → 全角色完整练度（等级/星魂/行迹/光锥/遗器词条/属性面板），2026-11-03 实测 64 角色明细到手
- 失败路径：`retcode!==0` 抛错（stage/retcode/message 三元组，`account-client.mjs:12`）；特定 retcode 走风控分支（§5）。

---

## 5. 风控验证链（`record-verification.mjs`）

### 5.1 触发时机与触发码

| retcode | 语义 | 参考实现处置 | 出处 |
|---|---|---|---|
| `1034` | game_record 明细被风控（UIGF `error_code.md`：「请求遇到验证码」） | 记录被拒请求（path + trace），等待验证链解封后重试 | `account-client.mjs:41` |
| `10034` | 养成计算器接口（`/e20200928calculate/`）风控 | 读响应头 `x-rpc-verify`（JSON：`ticket`+`token`），走独立的官方 SDK 弹窗分支 | `account-client.mjs:40` |
| `10035` / `10041` / `5003` | 同族极验触发码（genshin.py `GEETEST_RETCODES = {10035,5003,10041,1034}` 口径） | 参考实现把它们归入「同步中止」名单（`calculator-sync.mjs:5`），不入 challenge 链 | `skills/sr-od-account-inspection/references/api.md` 风控节交叉印证 |
| `verificationRequired` 判定 | errors 中任一 code ∈ {1034,10034,10035,5003,10041} | 数据快照标记需验证 | `account-model.js:65` |

注意边界：1034 记录分支只认 `/app/genshin/api/` 路径（`account-client.mjs:41`），hkrpg 路径的 1034 不会进入验证链（星铁探测失败只返回结构化错误码，`account-controller.mjs:31`）。

### 5.2 createVerification（`record-verification.mjs:7-12`）

- **URL**：`GET https://api-takumi-record.mihoyo.com/game_record/card/wapi/createVerification?is_high=true`
- **额外头**（`recordChallengeHeaders`，`record-verification.mjs:3-6`）——声明「本次验证为哪个被拒请求而发」：

```
x-rpc-challenge_game: 2
x-rpc-challenge_path: <被拒请求 pathname 去掉 /game_record 前缀，如 /app/genshin/api/character/list>
x-rpc-challenge_trace: <被拒响应的 x-trace-id 头值，可为空串>
x-rpc-page: /ys
```

  path 来源：业务请求被 1034 拒时记录 `pathname.replace(/^\/game_record/,'')` 与 `x-trace-id` 响应头（`account-client.mjs:41`）；优先级 `notes` → `characters` → 任意第一个（`account-client.mjs:48`）。
- **返回**：`{gt, challenge, new_captcha}`（`gt` = 极验 captchaId，`challenge` = 验证流水号）；缺失即抛错（`record-verification.mjs:10`）。
- 该请求走通用 `request()` 管线：带完整设备头 + DS2 + cookie。

### 5.3 浏览器端人工验证（`verify.js:31-36`）

参考实现不在后端解验证，把 `{gt, challenge, new_captcha}` 交给前端极验第三代组件：

```js
initGeetest({gt, challenge, new_captcha, product:'popup', offline:false,
             https:true, lang:'zh-cn', api_server:'api.geetest.com'}, captcha => {...})
```

用户人工完成后 `captcha.getValidate()` 产出三元组 `geetest_challenge / geetest_validate / geetest_seccode`，POST 回本地服务。`api_server` 必须显式传 `api.geetest.com`（漏传连国际服务器必失败，`skills/sr-od-account-inspection/references/api.md` 备忘节同款结论）。

**`|jordan` 后缀**：参考实现全仓库无此字符串（全文检索确认）——它是 MihoyoBBSTools 的手法（seccode 值尾拼 `|jordan`）。参考实现用真实极验组件 `getValidate()` 原值提交，实测可行；我们实现时无需引入 `|jordan`。

### 5.4 verifyVerification（`record-verification.mjs:13-21`）

- **URL**：`POST https://api-takumi-record.mihoyo.com/game_record/card/wapi/verifyVerification`
- **body**：`{"geetest_challenge":"...","geetest_validate":"...","geetest_seccode":"..."}`（三元组逐一校验：非空字符串且长度 ≤2048）
- **额外头**：与 createVerification **完全相同**的那套 `challenge_game/challenge_path/challenge_trace/page` 头（pending.headers 原样复用，`record-verification.mjs:18`）
- **绑定校验**：提交的 `geetest_challenge` 必须**以** create 时拿到的 `challenge` 开头（`record-verification.mjs:17`），防错配。
- **返回**：`{challenge}`——这是服务端签发的**已验证** challenge（与 create 时的原始 challenge 不是同一个值），缺失即抛错。
- 有效期：从 create 到 verify 提交 ≤ 600 秒（`record-verification.mjs:14`）。

### 5.5 challenge 与业务请求的绑定关系

1. create/verify 两步都用 `challenge_path`/`challenge_trace` 头声明目标被拒请求；
2. verify 成功后，**已验证 challenge** 存入客户端会话（`account-client.mjs:53`）；
3. 此后**所有**业务请求自动携带 `x-rpc-challenge: <已验证challenge>` 头（`account-client.mjs:33`），直到会话结束；被拒记录在对应业务成功（retcode 0）后清除（`account-client.mjs:42`）；
4. 业务请求本身不携带 `challenge_path/trace`——那两个头只出现在 create/verify 两步上。

### 5.6 计算器支线（补充，非 game_record 主链）

retcode 10034 时响应头 `x-rpc-verify` 内嵌 JSON `{ticket, token}`（`account-client.mjs:40`）；浏览器端用米游社官方账号 SDK 弹窗 `miHoYoAccountSdk.verifier.geetest({ticket})`（`verify.js:29`），验证成功后 token 作为 `x-rpc-risk_token` 头携带（`account-client.mjs:35,52`），有效期同为 600 秒。星铁链路用不到此支线，记录备查。

---

## 6. 逐项对照表（我们仓库现状 vs 参考实现 vs UIGF）

我们仓库现状的事实源：`tools/account/merge_profile.py`、`tools/account/clean_account_profile.py`、`src/sr_od/application/account_profile/`（app/config/const/core/factory）、`skills/sr-od-account-inspection/references/api.md`。

| # | 项目 | 参考实现 | 我们仓库现状 | UIGF 文档 | 判定 |
|---|---|---|---|---|---|
| 1 | 密码登录端点 | `passport-api.miyoushe.com/account/ma-cn-passport/web/loginByPassword`（`account-client.mjs:23`） | **无实现**（浏览器路线靠人扫码，skill api.md 前置节明言 agent 不代输密码） | `webapi.account.mihoyo.com/Api/login_by_password`（老端点，需先 create_mmt） | ⚠️ 不一致：照参考实现（实测通过），UIGF 为旧流程 |
| 2 | RSA 公钥 | 见 §2.2 | 无 | 同款公钥 | ✅ 一致 |
| 3 | 登录加密 | 账号+密码都 RSA-PKCS1-base64 | 无 | 仅说密码加密可选、body 带 `is_crypto` | ⚠️ 参考实现连账号也加密且无 is_crypto 字段，实测通过 |
| 4 | 登录 DS salt | `LyD1rXqMv2GJhnwdvCBjFOKGiKuLY3aO`，三段式无 b/q | 无（skill api.md 只记了 4X salt） | 文档不含此 salt（放 issue）；DS1 语义近似但 r 形态描述不同 | ⚠️ salt 与 4X 不同为实测事实 |
| 5 | game_record DS2 salt | `xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs` | skill api.md:15 同款（浏览器路线已在用） | 同款 | ✅ 三源一致 |
| 6 | DS2 的 r 取值域 | [100001,200000]（`account-client.mjs:13`） | skill api.md:13 写 `100001~200000` | 100000~200000 + 特例，注释给等价简化式 | ✅ 等价 |
| 7 | DS2 的 b 形态 | 实际发送串（带空格 JSON，key 不排序） | skill api.md 写「按 key 排序 stringify」 | key 排序紧凑 JSON | ⚠️ 三种形态实测都过；我们实现时贴参考实现（发送串自洽） |
| 8 | DS2 的 q 形态 | URLSearchParams(key 排序 + URL 编码)（`account-client.mjs:13`） | skill api.md 写「按 key 字母序排序拼接」 | key 字母序拼接 | ✅ 基本一致（参考实现多做一层 URL 编码） |
| 9 | 请求头 app_version | 恒 `2.11.1` | skill api.md 用 `2.69.1` | 按版本配套 salt | ⚠️ 该头当前不严格校验，两值实测均过；建议恒定一个值 |
| 10 | UA | 桌面 Chrome | skill api.md 用安卓 webview UA（那是 H5 页面路线的前提） | 安卓 + miHoYoBBS 形态 | ⚠️ 直连 API 场景桌面 UA 实测通过；照参考实现 |
| 11 | X-Requested-With | 不带 | skill api.md 带 `com.mihoyo.hyperion` | 要求带 | ⚠️ 参考实现不带也过；可带可不带，建议贴参考实现少一个变量 |
| 12 | 设备头 | device_id(UUIDv4) + device_fp(getFp) + platform=4，login 与 record 共用 | 无实现；skill api.md 的 device_fp 走「抄官方网页现成的」捷径 | device_id=uuid4、getFp 端点同款 | ✅ 方向一致；我们实现应自带 getFp（不再依赖抄网页） |
| 13 | cookie 管理 | Set-Cookie 全量透传 jar，零 token 交换 | 无实现（浏览器路线手动搬 cookie 且不落盘） | 多步 token 交换链 | ⚠️ 照参考实现 |
| 14 | 风控触发码 | 1034（record）/10034（calculator）记 blocked；10035/10041/5003 归同步中止 | skill api.md：10035/10041 为极验族，2026-10 系列实验 + 2026-11-03 结论（新鲜密码登录会话直接放行） | error_code.md 仅明确 1034 | ⚠️ UIGF 覆盖不全；以参考实现 + skill 实测为准 |
| 15 | 验证链端点 | `game_record/card/wapi/createVerification?is_high=true` + `verifyVerification` | 无实现（skill api.md 记录过自建验证页实验：票据不被 10035 网关接受） | 未收录此二端点 | ⚠️ UIGF 缺失，以参考实现为准 |
| 16 | `x-rpc-challenge` 携带 | verify 后所有业务请求自动带（`account-client.mjs:33`） | 无 | authentication.md 列为「少数 API 才需要」的头 | ⚠️ 以参考实现的「全请求携带」为准 |
| 17 | `\|jordan` seccode 后缀 | 不使用（真实 getValidate 原值） | skill api.md 提及 MihoyoBBSTools 用之（该实验未解除 10035） | 未提及 | 结论：非必需，不引入 |
| 18 | hkrpg 星铁支持 | 本地补丁 `hkrpgProbe` 复用通用管线（`account-controller.mjs:26-32`） | 无 API 实现；有游戏内画面扫描 app（`account_profile_app.py`，产出 `account_profile_scan.json`） | 星铁仅公告文档，无 game_record 规格 | ⚠️ 参考实现实测全通过；我们实现时把 hkrpg 列为一等公民 |
| 19 | 数据落盘格式 | JSON 快照（normalizeAccount/mergeAccount，`account-model.js:49-72`） | `config/idx/account_profile_scan.json`（游戏内扫描，字段为中文展示名口径）+ `config/idx/account_profile.yml`（roster，VLM 判读口径） | — | ⚠️ 两套数据口径需桥接，见 §7 缺口② |

**与 UIGF 不一致的显式结论**（§6 表中 ⚠️ 项的汇总）：UIGF 文档描述的登录流程（老端点 + create_mmt + 多步 token 交换）、请求头强约束（安卓 UA / X-Requested-With / app_version-salt 配套）在参考实现里**全部没有照做**，且 2026-11-03 实测全链路通过——这些 UIGF 条目对应的是官方旧版 web 流程或「部分客户端」的口径，对「新 passport 端点 + 桌面直连」这一路线不适用。照参考实现实现即可，不要按 UIGF 补这些头。

---

## 7. 我们自己实现时的模块划分与验收标准

### 7.1 现有资产盘点（与 API 数据格式的衔接缺口）

- `src/sr_od/application/account_profile/`：游戏内逐格扫描 app（`account_profile_app.py:1-9`），产出 `config/idx/account_profile_scan.json`（`account_profile_app.py:44,631-639`）。数据字段是**游戏内画面口径**：中文展示名（`cn`）、`level/eidolon_count/relics[]`（词条为 OCR 原文串）。
- `tools/account/clean_account_profile.py:19-45`：对 scan JSON 做名字白名单归一/去重，产物仍是同一 JSON。
- `tools/account/merge_profile.py:52-67`：把 **VLM 判读的 roster_raw.json**（字段 `name/level/rarity/confidence`）合并进 `config/idx/account_profile.yml` 的 `roster` 节——这是第三套口径（截图判读）。
- 缺口①：**完全没有网络栈**——无 HTTP 客户端、无登录、无设备身份、无 DS、无风控链（`src/` 全树确认无任何米游社请求代码）。
- 缺口②：**数据口径不桥接**——API 口径（数字游戏 id + `avatar/info` 全练度结构）与画面扫描口径（中文名 + OCR 文本词条）无映射层。应建立 `avatar_id ↔ cn 名称` 桥（`account_profile_core.py` 已有 `characters-full.json` 映射表基础设施，`account_profile_core.py:27-29,83-118`，可复用）。
- 缺口③：**凭据存储缺位**——账号密码/会话 cookie 的落盘位置与加密策略未定义（参考实现用 `.private/` + 0600 权限 + 临时文件 rename 原子写，`account-device.mjs:22`、`account-controller.mjs:5`）。

### 7.2 建议模块划分（全部放 `src/sr_od/application/account_profile/` 或其 `api/` 子包）

| 模块 | 职责 | 逐字对齐项（禁改） | 可自由实现项 |
|---|---|---|---|
| `miyoushe_device.py` | 设备身份：deviceId 持久化 + getFp 注册 | 公钥外的所有常量：getFp URL、ext_fields 20 字段模板、body 七字段、成功四判据、24h/30min 缓存策略、三个头名与取值 | 文件路径（放 config/ 或 .debug 私有区）、并发锁实现 |
| `miyoushe_auth.py` | 密码登录 | 登录 URL、RSA 公钥原文、PKCS1 padding、登录 salt `LyD1rXqMv2GJhnwdvCBjFOKGiKuLY3aO`、三段式签名串、十个请求头及值、body 结构（仅 account/password 两字段） | 凭据来源（配置/交互输入）、密码不落盘策略 |
| `miyoushe_sign.py` | DS 签名（登录 DS + DS2 两个纯函数） | 4X salt、r 取值域 [100001,200000]、签名串格式、md5 拼接顺序、b/q 的取材规则（b=实际发送串） | 函数形态、时间源注入（便于测试） |
| `miyoushe_client.py` | HTTP 会话：cookie jar、域白名单、公共头、retcode 分诊、超时/重定向策略 | 四域白名单、公共头表（§4.2）、encoded body 规则、retcode!==0 抛错语义、每次响应收 Set-Cookie | httpx/requests 选型、重试与限频策略 |
| `miyoushe_verification.py` | 风控链：1034 记录、createVerification/verifyVerification、challenge 注入 | 两端点、extra 头四件套、body 三字段名、startsWith 绑定校验、600s 时效、x-rpc-challenge 全请求携带 | 人工验证的 UI 通路（参考实现用本地 web 页；我们可走本机专用调试 Edge，`AGENTS.md` §7 的 CDP 浏览器） |
| `miyoushe_records.py` | 业务接口封装：roles/index/note/avatar/info | 各端点 URL、方法、参数（role_id 字符串化、server 值、need_wiki=true） | 返回 dataclass 结构定义 |
| `account_profile_merge_api.py` | API 口径 → 档案口径桥 | — | 全部（复用 `normalize_cn_name` 与映射表做 id↔cn 桥） |

### 7.3 验收标准（可观测行为口径）

1. **设备身份**：首次运行生成 deviceId 文件且为 UUID v4；二次运行不重新生成；getFp 成功时后续请求头含 `x-rpc-device_fp` 且 24h 内不重复调用 getFp（网络层观察：仅一次 getFp 请求）。
2. **签名正确性**：任一构造的 DS 值满足 `{t},{r},{md5}` 且 r ∈ [100001,200000]；同一 (t,r,b,q) 重算 md5 结果稳定（纯函数单测锁定，喂参考实现同输入比对输出一致）。
3. **登录**：`login()` 返回 retcode 0 且 cookie jar 非空；错误密码返回非 0 retcode 并上抛（不吞错）。
4. **会话请求**：凭登录会话调用 `getUserGameRolesByCookie(game_biz=hk4e_cn)` 返回 retcode 0 且 `list` 非空。
5. **game_record（原神对照）**：`dailyNote` 调用返回 retcode 0（含 `current_resin` 字段）；`character/list` 返回 retcode 0 且 `list` 非空。
6. **星铁明细（主目标）**：`avatar/info`（`need_wiki=true&role_id=<uid>&server=prod_gf_cn`）调用返回 retcode 0，且返回的角色列表覆盖画面扫描档案中的已知角色集合（数量 ≥ 画面扫描 count）。
7. **风控链**：人为构造 1034 场景（或以 mock retcode 驱动）时：先记录 path/trace，createVerification 返回 gt/challenge；提交三元组后后续请求头出现 `x-rpc-challenge`；600 秒超时后拒绝提交并要求重建挑战。
8. **数据桥**：对同一账号，`avatar/info` 的角色 id 集合经映射后与 `account_profile_scan.json` 的 cn 名集合交集 ≥ 已扫描角色的既知命中率（映射表覆盖内应 100%）；无映射命中时产出明确的未匹配清单而非静默丢弃。

---

## 8. 附录

### 8.1 参考实现 commit SHA

```
965672384105a4bc40959beffad51f9e5581ebe2
```

（`git -C .debug/temp/teyvat-resin-planner rev-parse HEAD` 实测输出。）

### 8.2 实测流量校对记录

**实测流量轨迹（2026-11-03 抓取）**：`.debug/temp/teyvat-resin-planner/.private/trace.log`（JSONL，10 条，cookie 值脱敏）：loginByPassword ×1、原神 getUserGameRolesByCookie/dailyNote/character/list ×6、hkrpg index/note/avatar-info ×3，**全部 retcode 0**。登录 Set-Cookie 名单已据此补全（见「2. 密码登录」节）。仍待定向补抓的两段：getFp 真实响应（登录命中 24h 缓存未发起，待 fp 缓存过期后的登录补录）；createVerification/verifyVerification 完整往返（会话未触发风控，需人为构造 1034 场景补录）。

**自家实现端到端校对（2026-11-04）**：按本规格实现的 `one_dragon/mys/`（登录/aigis 分支/通用请求）+ `sr_od/mys/`（崩铁角色列表）已在真机 MCP 环境端到端跑通并验收（迭代 mys-account-mcp，T-5 实机报告）：密码登录两次均零人机验证通过、角色发现 + index 返回 64 角色、空罐/登出后打接口实测命中会话失效映射（码值经信封脱敏未透出）、1034 未出现。规格与实现零出入。

### 8.3 外部出处

- UIGF-org/mihoyo-api-collect（CC BY-NC 4.0）：鉴权 `other/authentication.md`、密码登录 `hoyolab/login/password_passport.md`、错误码 `other/error_code.md`、Token `hoyolab/user/token.md`——https://github.com/UIGF-org/mihoyo-api-collect
- 设备指纹模板与请求头底座出处：SeelieEx（MIT，KeyPJ），固定参考提交 `c298631e9858ef6088b62c9b4c872ddd52c677a7`，许可与适配声明见参考仓 `THIRD_PARTY_NOTICES.md`
- 我们仓库既有实测记录：`skills/sr-od-account-inspection/references/api.md`（2026-10 排查链 + 2026-11-03 解锁结论）
