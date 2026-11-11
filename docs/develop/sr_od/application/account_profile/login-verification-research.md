# 国服密码登录人机验证规格调研（loginByPassword → x-rpc-aigis 链）

> 状态：调研件（2026-11-04 定稿）。回答「新 passport 端点密码登录触发人机验证时怎么办」。
> 证据分级约定：**实证** = 多个独立实现互证，或带日期的真机流量记录；**文档** = 单一来源代码/文档（官方前端反混淆代码按实证对待——它是官方行为的第一手载体）；**推测** = 本调研推理，无直接出处，实现前须实测。
>
> 本文档与 [miyoushe-api-flow.md](miyoushe-api-flow.md) §5（game_record 的 1034/createVerification 链）互补：**两套是不同体系**，对照见 §7。

---

## 0. 结论速览（先读这个）

| 问题 | 结论 | 分级 |
|---|---|---|
| 触发时响应长什么样 | HTTP 200；body `retcode=-3101`、message 为模糊文案（实测出现过「请求频繁，请稍后再试」——**不能按文案判断**）；挑战不在 body（body 为空），在**响应头 `x-rpc-aigis`**（JSON 字符串） | 实证（官方前端代码 + 真机实测互证） |
| 验证机制 | 极验人机验证；官方登录页当前**只加载极验 v4 组件**（gt4）；aigis 数据里的 `use_v4` 字段决定 gt3/gt4 分流，gt3 分支在官方代码中保留但当前页面不可达 | 实证 |
| 票据怎么提交 | **没有独立 verify 端点**。把 `{session_id};{base64(JSON(极验票据))}` 放进**请求头 `x-rpc-aigis`**，**原样重发 loginByPassword**（官方前端在 axios 拦截器里自动重发） | 实证（三源互证） |
| 成功后怎么继续登录 | 重发的请求成功即 `retcode=0` + `Set-Cookie` 直接入登录态（ltoken_v2 族，同成功路径）；验证环节本身不单独下发凭据 | 实证 |
| 与 game_record 1034 链的关系 | **完全不同构**：端点、凭证头（`x-rpc-aigis` vs `x-rpc-challenge`）、票据载体（头 vs body）、验证绑定方式（session_id vs challenge_path/trace）都不同 | 实证 |
| 邮件/短信验证码在密码登录链吗 | 国服 web 密码登录链**无邮件验证**；短信验证码登录是**平行链**（另一对端点），共用同一套 x-rpc-aigis 机制；邮件验证（ActionTicket）只见于国际服 app 登录 | 实证 |

---

## 1. 调研源清单

| # | 源 | 形态 | 本文引用简称 |
|---|---|---|---|
| S1 | 米游社官方登录页前端 login-platform（`https://user.miyoushe.com/login-platform/`，chunk `5823.9f588959.js` / `login.35d0ab6d.js`） | 官方反混淆代码（2026-11-04 抓取） | **官方前端** |
| S2 | 米哈游官方账号 SDK `https://webstatic.mihoyo.com/dora/biz/mihoyo-account-sdk/main.js`（583 KB） | 官方代码（2026-11-04 抓取） | **官方 SDK** |
| S3 | seriaati/genshin.py `genshin/client/components/auth/subclients/web.py`、`models/auth/geetest.py`、`utility/auth.py`、`client/components/auth/client.py`、`client/routes.py`、`constants.py`、`errors.py`、`utility/ds.py`（master） | 第三方实现（登录链成熟实现） | **genshin.py** |
| S4 | Marchen-orz/MiyoQian `miyouqian/auth/login.py`、`core/captcha.py`、`webui/app.js`（master） | 第三方实现（短信登录链，含 webui 人工解题） | **MiyoQian** |
| S5 | nekwken/mhy-QRscanner `crates/mhy-qrscanner-mihoyo/src/aigis.rs` | 第三方实现（Rust；头注释声明 2026-09-11 对照官方 Android SDK 行为 + 真机流量核验） | **QRscanner** |
| S6 | IKUNHEIHIE/miyoushe-checkin `接口验证记录.md` | **真机实测记录**（2026-10-23/26，全新设备触发验证全链路） | **实测记录 S6** |
| S7 | UIGF-org/mihoyo-api-collect `hoyolab/login/password_passport.md`、`other/error_code.md` | 社区文档 | **UIGF** |
| S8 | box-opener/zzz-calculator `web/miyoushe.py`；CMHopeSunshine/LittlePaimon `get_cookie.py` | 第三方实现（旁证） | 旁证 |
| S9 | 参考实现 `teyvat-resin-planner`（成功路径基准；上游与 commit 锚见 miyoushe-api-flow.md 卷首与 §8.1） | 本项目实测 | **参考实现** |

排除性结论：**MihoyoBBSTools（Womsxd）无密码登录**（`login.py` 只做 cookie/stoken 维护）；**SeelieEx（KeyPJ）无登录模块**（全树只有凭已有 cookie 的读数 adapter/crawler，是参考实现设备指纹模板的出处，不涉及登录验证）。

---

## 2. 触发形态：响应结构（问题 1）

### 2.1 触发时的完整响应

- HTTP 状态 **200**（不是 4xx）；
- body JSON：`retcode = -3101`，`message` 为**模糊文案**——实测记录 S6 中为「请求频繁，请稍后再试」（官方另有专门的 `RequestFrequencyLimit = -3006` 码，文案近似；**绝不能按 message 文案分流**）；
- **body 无挑战数据**（QRscanner S5 头注释：「the challenge travels in the response header x-rpc-aigis (the body is empty)」）；
- 挑战在**响应头 `x-rpc-aigis`**，值是 JSON 字符串（分级：实证——官方前端拦截器 `JSON.parse(headers["x-rpc-aigis"])`、QRscanner、genshin.py、MiyoQian 四源一致）。

### 2.2 x-rpc-aigis 头的结构

```jsonc
// 外层 JSON（官方前端：JSON.parse 一次）
{
  "session_id": "<服务端签发的验证会话 ID>",
  "data": "<内层 JSON 的字符串形态>"   // 或直接是内嵌对象（两形态都出现过，解析须兼容）
  // 10034 ticket 场景的外层还可能出现 "mmt_type"（0=无需验证 1=需要）
}
// 内层 data（官方前端：再 JSON.parse 一次）—— 极验挑战参数：
// gt4 形态: { "gt": "<captcha_id>", "risk_type": "slide|icon|...", "success": 1, "new_captcha": 1, "use_v4": true }
// gt3 形态: { "gt": "<captcha_id>", "challenge": "<流水号>", "success": 1, "new_captcha": 1 }
```

出处：官方前端拦截器（S1：`const n=JSON.parse(e),{session_id:c}=n,s=JSON.parse(n.data)`）；解析兼容双形态：QRscanner `parse()` 对 `data` 做 `String→json.loads / Object→原样` 双分支（S5），genshin.py `BaseMMT.__parse_data` 同样处理（S3 `geetest.py`），MiyoQian `completeAigisChallenge` 同构（S4）。

### 2.3 触发与失败两个码（语义辨析，重要）

| retcode | 官方命名（S1 枚举表） | 语义 | 分级 |
|---|---|---|---|
| **-3101** | `NeedAigis` | **初次触发**人机验证；aigis 头携带挑战 | 实证（官方枚举 + 实测记录 S6 + QRscanner） |
| **-3102** | genshin.py `errors.py` 映射 `GeetestFailed`（"The provided aigis payload is invalid"） | **提交的验证票据校验失败**（实测 message「图片验证码失败」，出现在已提交票据的重发请求上）→ 需重新走一遍验证（新会话） | 实证（genshin.py 映射 + 实测记录 S6 互证） |

⚠️ genshin.py 的 `_cn_web_login` 把 **-3102** 当「Captcha triggered」处理（web.py 注释 `# Captcha triggered`）——按上述两源证据，**-3102 更准确的语义是「票据无效」而非「初次触发」**。对实现的实际影响为零（两者处置相同：重新验证再重发），但监控/日志语义应区分。genshin.py 把 -3101 归类 `ActionInCooldown` 是受其模糊文案误导的命名（其 OTP 流程代码里 -3101 实际也按验证触发处理），不采纳该命名。

---

## 3. 验证机制与组件（问题 2）

### 3.1 gt3 还是 gt4？

- **当前官方登录页只加载极验 v4**：`https://user.miyoushe.com/login-platform/index.html` 的 script 清单中极验只有 `https://webstatic.mihoyo.com/dora/lib/geetest/v4/gt4.js`，无 gt3 脚本（2026-11-04 抓取，实证）。
- 分流键 = 挑战数据的 **`use_v4` 字段**：官方 SDK `Ps=function(e,t){var c=e.use_v4||false; if(c){…initGeetest4…}else{…initGeetest…}}`；官方前端 S1 同构（`const c=e=>e.use_v4, d=s(e)`）。MiyoQian 用等价启发式 `"challenge" in data`（gt3 数据才有 challenge）。
- gt3 分支在官方代码中**保留但当前不可达**（页面无 initGeetest 全局，遇到 use_v4=false 会解题失败）——据此判定：**国服新 passport 登录链当前实际形态 = 极验 v4**（实测记录 S6：「会话指示使用极验 v4」）。gt3 作为降级兜底保留实现（成本极低）。

### 3.2 组件调用参数（可直接照抄）

**gt4（当前主形态）**——官方前端（S1，product="bind"）与官方 SDK（S2，product 来自配置）：

```js
initGeetest4({
  captchaId: data.gt,
  riskType:  data.risk_type,          // 缺省按 "icon"（QRscanner S5）
  language:  "zho",
  product:   "bind",                  // 官方前端；官方 SDK 用配置传入（社区用 "popup" 亦可）
  hideSuccess: true,
  userInfo:  JSON.stringify({ session_id: <session_id> }),   // ★ 必须：session_id 传进组件
  timeout:   10000,
  https: true, protocol: "https",
})
captchaObj.onSuccess(() => resolve(captchaObj.getValidate()))
```

**gt3（兜底形态）**——官方 SDK（S2）+ 社区三源：

```js
initGeetest({
  gt: data.gt, challenge: data.challenge, new_captcha: data.new_captcha,
  offline: !data.success,             // 官方 SDK 原文 `offline:!S`
  product: "popup",                   // 社区用 "custom"/"popup" 均实测可用
  api_server: "apiv6.geetest.com",    // 官方 SDK 用 apiv6；参考实现用 api.geetest.com 亦实测可用（miyoushe-api-flow.md §5.3）
  https: true, lang: "zh-cn",
})
captchaObj.onSuccess(() => resolve(captchaObj.getValidate()))  // 产出 geetest_challenge/geetest_validate/geetest_seccode 三元组
```

组件脚本来源（任选其一）：
- 官方托管副本（国内直连稳）：`https://webstatic.mihoyo.com/dora/lib/geetest/v4/gt4.js`（官方登录页在用）；
- 极验官方 CDN：`https://static.geetest.com/static/js/gt.0.4.9.js`（MiyoQian）/ `gt.0.5.0.js`（参考实现、genshin.py）/ `https://static.geetest.com/v4/gt4.js`。

### 3.3 无感验证（v4 adaptive）

极验 v4 的适应性验证**经常无感通过**（用户毫无知觉即完成）——QRscanner S5 头注释「it often passes invisibly, as it does in the official app」。含义：即使触发验证，多数情况下组件一初始化就直接 onSuccess，不出现滑块 UI。我们实现时**必须走真组件**（不能跳过初始化），但用户体验上多数是一次静默通过。

### 3.4 触发条件（问题 2 后半）

社区无系统性总结。已确认的点：

| 条件 | 证据 | 分级 |
|---|---|---|
| 全新设备上下文（随机新 device_id、无 device_fp、无历史 Cookie）触发验证 | 实测记录 S6 第二轮（2026-10-23）：新设备首发 `createLoginCaptcha` 即返回 -3101 + aigis；同账号沿用原设备指纹时不触发（第一轮） | 实证 |
| 已登录过的设备重复密码登录不触发 | 参考实现 2026-11-03 两次登录零验证通过（miyoushe-api-flow.md 实测背书） | 实证 |
| 请求频率异常 | 官方码表有 `RequestFrequencyLimit = -3006`；-3101 的模糊文案也是「请求频繁」类 | 文档 |
| 密码错误次数过多 | 官方码 `AccountPwdLoginTryTooMuch = -3208`（官方前端对它有专门 UI 分支：≥3 次弹「账号或密码错误」并跳忘记密码） | 文档 |
| 账号风险/封禁态 | `AccountRisky = -3235`、`AccountForbidden = -3201`、`AccountSafelyForbidden = -3254`、`AccountLocked = -4400`、扫码风控 `QRLoginRisky = -3506` | 文档 |
| 换 IP 触发 | 无直接证据 | 推测（与「新设备」同属风控特征漂移，合理但未实测） |

---

## 4. 票据提交与重试时序（问题 3、4）

### 4.1 官方前端拦截器原文语义（S1 去混淆伪代码）

```js
// axios 响应拦截器（官方 login-platform，覆盖包括 loginByPassword 在内的全部 passport API）
const retcode = body.retcode;
if (retcode === -3101 /* NeedAigis */) {
  const aigis = JSON.parse(headers["x-rpc-aigis"]);        // 外层
  const { session_id } = aigis;
  const challenge = JSON.parse(aigis.data);                 // 内层（兼容字符串/对象）
  const result = await renderGeetest(challenge, aigis);     // 极验组件人工/无感解题 → getValidate()
  const b64 = btoa(JSON.stringify(result));                 // 票据 JSON → base64
  // ★ 原请求重发：config 原样，仅追加 x-rpc-aigis 头
  return axios({ ...config, headers: { ...config.headers, "x-rpc-aigis": `${session_id};${b64}` } });
}
```

### 4.2 票据组装格式

- 回传头值 = **`{session_id};{base64(JSON(票据对象))}`**（分号分隔，base64 为标准 base64）。
  实证三源一致：官方前端（S1：`${c};${s}`，s=`btoa(JSON.stringify(o))`）、官方 SDK 语境（QRscanner S5 注释「byte-compatible with what the official SDK sends」）、genshin.py（`get_aigis_header` = `f"{session_id};{base64(json.dumps(mmt_data))}"`）、MiyoQian（`${aigis.session_id};${base64Json(validate)}`）。
- **v4 票据字段**：极验 v4 `getValidate()` 原生产出 `lot_number / captcha_output / pass_token / gen_time / captcha_id`。QRscanner（S5，对照官方 SDK）额外补插两字段：
  ```
  result["captcha_id"] = <挑战里的 gt>       // 组件一般已带；缺则补
  result["userInfo"]   = {"session_id": <session_id>}
  ```
  MiyoQian 与 genshin.py 的模型（`SessionMMTv4Result`）不含 `userInfo` 也能被接受（它们的短信链在用）——推断服务端只强校验核心四元组 + session_id 绑定，字段集宽容。**建议照 QRscanner 规格（补两字段）实现，精确复刻官方行为**。
- **gt3 票据字段**：`geetest_challenge / geetest_validate / geetest_seccode` 三元组原样（genshin.py `SessionMMTResult`；参考实现 game_record 链同款字段名，实测可用）。

### 4.3 完整时序（可照此实现，8 步）

```
[1] POST https://passport-api.miyoushe.com/account/ma-cn-passport/web/loginByPassword
    （请求规格 = 成功路径不变：body {account:RSA, password:RSA}、登录 DS、十个头，见 miyoushe-api-flow.md §2）
[2] 响应 200 + retcode=-3101 + 响应头 x-rpc-aigis   → 进入验证分支
    （retcode=-3102 → 同样进验证分支，但日志记「票据无效」；其他 retcode → 按普通错误上抛）
[3] 解析 aigis：JSON.parse(头值) → {session_id, data}；data 若为字符串再 JSON.parse
[4] 按 data.use_v4 分流 → 加载对应极验组件 → 以 §3.2 参数初始化 → 等待 onSuccess（多数为无感通过）
[5] 票据组装：v4 = getValidate() + 补 captcha_id + userInfo；gt3 = getValidate() 三元组
[6] 组装 x-rpc-aigis 请求头 = `${session_id};${base64(JSON.stringify(票据))}`
[7] 原样重发 [1]（body、其余头全部不变，仅新增 x-rpc-aigis 头；官方前端在拦截器里自动做）
[8] 重发响应：
    retcode=0  → 成功；Set-Cookie 照成功路径收取（ltoken_v2 族直入登录态，验证环节不单独下发凭据）
    retcode=-3102 → 票据被拒：回到 [3]，用**新会话**重新验证（禁止复用旧验证结果——实测记录 S6 约束）
    其余 retcode → 按普通错误上抛
```

**DS 是否随重发刷新**：官方前端重发时保留原 config.headers（含旧 `ds`）——照官方行为可不刷新（分级：文档）；服务端 DS 时间窗对重发宽容这一点未实测，**保守建议重发时重新生成 DS**（分级：推测，成本为零）。

### 4.4 与 game_record 风控链（1034）的对照（问题：是否同构）

| 维度 | 登录验证链（本文档） | game_record 风控链（miyoushe-api-flow.md §5） |
|---|---|---|
| 触发码 | -3101（触发）/ -3102（票据无效） | 1034（+同族 10035/10041/5003；10034 走 x-rpc-verify ticket 支线） |
| 挑战获取 | 不需要：挑战随被拒响应**直接下发**在 `x-rpc-aigis` 头 | 需要主动调 `createVerification`（带 challenge_path/trace 头） |
| 票据载体 | **请求头 `x-rpc-aigis`**：`{session_id};{base64}` | **POST body** 三元组 → `verifyVerification` |
| 会话绑定 | aigis 内的 `session_id`（服务端签发、随挑战下发） | create 时 `challenge` 与 verify 返回的**新 challenge**（startsWith 校验） |
| 成功后携带 | 只在**重发的原请求**上带 aigis 头（官方前端）；后续业务请求不携带 | 后续**所有**业务请求持久携带 `x-rpc-challenge`（参考实现口径） |
| 时效 | 未发现显式 600s 类限制（但实测记录 S6 提示会话可过期，第一次提交失败后需换新会话） | create→verify ≤600 秒 |

结论：**两套体系完全不同构**，实现为两个独立模块，不可复用 createVerification/verifyVerification 代码路径。

---

## 5. 官方错误码表（login-platform 前端枚举，与登录直接相关部分）

出处：S1（chunk 5823 枚举表），分级：文档（官方代码）。UIGF `other/error_code.md` **未收录** passport 验证族码（仅 1034/-10001 等）——文档缺口已实证，UIGF 在这块帮不上忙。

| retcode | 官方名 | 语义/处置 |
|---|---|---|
| -3101 | NeedAigis | 触发人机验证（本文档主题） |
| -3102 | （genshin.py: GeetestFailed） | 验证票据无效/图片验证码失败 → 重新验证 |
| -3006 | RequestFrequencyLimit | 请求过于频繁 |
| -3208 | AccountPwdLoginTryTooMuch | 密码错误次数过多（官方前端 ≥3 次引导找回密码） |
| -3235 | AccountRisky | 账号风险 |
| -3201 / -3254 / -4400 | AccountForbidden / AccountSafelyForbidden / AccountLocked | 封禁/冻结/锁定 |
| -3257 | AccountSelfLoginRestriction / AccountInForceGameCtrl | 登录受限 |
| -3003 | ActionTicketInvalid | ActionTicket 无效（邮件验证态） |
| -3501～-3506 | QRLoginExpired / DeviceInconsistent / UserInconsistent / UserCanceled / QRLoginRisky | 扫码登录族（旁证：扫码链同受风控管辖） |
| -100 | TokenInvalid | 登录态失效 |

---

## 6. 邮件/短信验证码形态（问题 6）

- **国服 web 密码登录链内不存在邮件验证**：官方前端密码登录 catch 分支只处理 -3208（密码错误）与透传其余错误；「验证码」只指极验。分级：文档（官方前端代码路径）。
- **短信验证码登录是平行链**（不是密码登录的后备验证步），端点（多源一致，实证）：
  - 发送：`POST /account/ma-cn-verifier/verifier/createLoginCaptcha`（body：RSA 加密的 mobile + area_code；响应含 `action_type`/`countdown`，触发验证时同样回 -3101 + aigis 头）；
  - 登录：`POST /account/ma-cn-passport/web/loginByMobileCaptcha`（web 形态；MiyoQian 用 `/app/loginByMobileCaptcha` app 形态，两形态并存）body：mobile/area_code（RSA）+ `captcha`（用户输入的短信码）+ `action_type`（发送响应带回，须保存回传）。
  - 该链共用同一套 x-rpc-aigis 机制与组件（官方前端同一拦截器；MiyoQian 的完整 webui 人工解题实现就在这条链上）。
- **邮件验证（ActionTicket）**：只见于国际服 app 密码登录（genshin.py `login_with_app_password`：新设备首登触发邮箱验证码，`createEmailCaptchaByActionTicket`/`verifyActionTicketPartly`）。国服链路无此形态。分级：文档。
- 实测记录 S6 对短信链的端到端实证：新设备 → -3101 + 极验 v4 → 人工验证 → 提交 → -3102（首次格式不符）→ 修正重验 → retcode 0 → 短信登录 retcode 0（登录本身未再要求验证）。

---

## 7. 社区实测案例（问题 5）

| 案例 | 日期 | 内容 | 价值 |
|---|---|---|---|
| 实测记录 S6（IKUNHEIHIE/miyoushe-checkin 接口验证记录.md） | 2026-10-23/26 | 短信链：新设备触发 -3101 → 极验 v4 人工验证 → **首次提交回 -3102「图片验证码失败」** → 核对官方前端格式、换新会话重验 → 0 → 短信登录成功 → 换 ltoken/cookie_token/签到全通 | **唯一直接观察到 -3101/-3102/重试验证/aigis 提交格式的真机往返记录** |
| QRscanner S5（aigis.rs 头注释） | 2026-09-11 | 声明对照官方 Android SDK 行为 + 真机流量核验了 aigis 契约（含票据补字段的「逐字节兼容」规格） | 票据组装的最精确口径 |
| genshin.py 登录链 | 长期维护 | -3102 触发分支 + aigis 回传 + 本地 webserver 人工解题；`login_with_password` 为公开 API（社区用户跑通过国服） | 实现级成熟度证据 |
| MiyoQian webui | 活跃维护 | 短信链完整人工解题 UI（gt3/gt4 双组件、递归重发、-3102 后换新会话） | 实现级互证 + 回传组装代码 |
| zzz-calculator | — | 把 -3102 与 1034/10035/10041/5003 并列归入「要求验证码验证」族 | 旁证 |

未找到专门记录**密码登录（loginByPassword）本体**触发验证的博客/issue（genshin.py issue 检索 aigis/3102 只命中 PR 与代码）。密码登录的验证分支证据 = 官方前端拦截器（覆盖该端点）+ genshin.py 实现级别；「端到端真机往返」只在短信链上被公开记录过（S6）。**这是本调研最大的证据缺口**，见 §8。

---

## 8. 对我们实现的建议

### 8.1 可直接设计的部分（证据充分）

1. **响应分诊**：`-3101`/`-3102` → 验证分支；其余非 0 → 普通错误上抛。**不看 message 文案**。
2. **aigis 头解析**：外层 JSON（session_id + data），data 兼容「字符串/对象」双形态（四源一致）。
3. **组件分流**：`use_v4` 字段 → initGeetest4（主）/ initGeetest（兜底），参数照 §3.2。**两个组件脚本都加载**（MiyoQian 手法），防服务端下发 gt3 形态时组件缺失。
4. **票据组装**：`{session_id};{base64(JSON(票据))}`；v4 票据 = getValidate() + 补 `captcha_id` + `userInfo={"session_id":…}`（QRscanner 口径）。
5. **重发**：原 body/头不变 + 新 x-rpc-aigis 头；成功路径（Set-Cookie 收取）与 miyoushe-api-flow.md §2.5 完全一致——**验证分支只是成功路径的前置插曲，不改变登录态收取逻辑**。
6. **-3102 处置**：换新会话重新验证，禁止复用旧票据；限制重试次数（建议 2 次）后上抛人工处理。
7. **人工解题通路**：复用本机专用调试 Edge（项目 AGENTS.md §7）加载极验组件完成人工/无感验证——形态同参考实现 verify.js（本地页 + 官方组件），替换渲染宿主即可；不接打码平台（MiyoQian 的打码狗路线不采纳）。
8. **不做的事**：不实现 create_mmt 老端点流程（UIGF 描述的是旧 webapi 端点体系，与 passport 端点无关，miyoushe-api-flow.md §6 对照表已裁定）；不在验证分支引入 x-rpc-challenge（那是 game_record 体系的头）。

### 8.2 必须实测补证的部分

| # | 待证项 | 现状 | 实测方法 |
|---|---|---|---|
| 1 | **密码登录本体的 -3101/-3102 往返**（含响应头形态、data 内字段、gt3/gt4 实际下发） | 端到端真机记录只存在于短信链（S6）；密码链只有代码级证据 | §8.3 触发方法 |
| 2 | 重发时 DS 刷新与否 | 官方前端不刷新（文档）；服务端是否校验 DS 时窗未实测 | 两种形态各试一次 |
| 3 | v4 票据字段最小集（含/不含 userInfo 均可？） | 三种组装口径并存且各自声称可用（§4.2） | 同一会话先按 QRscanner 口径提交；若 -3102 再降级试裸 validate |
| 4 | 验证会话时效（类似 game_record 的 600s 是否存在） | 无文档 | 触发验证后故意延迟提交，观察报错形态 |

### 8.3 触发方法与风险

- **方法（实测记录 S6 同构）**：全新随机 `device_id`（UUID v4）+ 不带 `x-rpc-device_fp` + 空 Cookie jar → 发起登录。S6 在短信链上必然触发；密码链合理推断同敏感（推测，待证）。若不触发，可多次更换设备指纹/间隔重试（注意 §8.3 风险 2）。
- **风险**：
  1. `-3208` 密码错误锁定：实测务必用正确密码，禁暴力尝试；
  2. 风控等级拉高（`-3235` AccountRisky / 后续更严验证）：低频触发（建议 ≥1 天间隔），不反复制造验证事件；
  3. 账号安全策略：触发验证本身是官方风控的正常表现，人工完成即可，**不绕验、不接打码平台**——绕验行为可能升级账号处置。
- **降级设计**：验证分支失败（组件加载失败/用户取消/连续 -3102）→ 上抛结构化错误（stage=login_verification），不阻塞「已登录会话」的其他功能路径。

### 8.4 实现落点（对接 miyoushe-api-flow.md §7.2 模块划分）

- `miyoushe_auth.py`：loginByPassword 响应分诊增加 -3101/-3102 分支，返回结构化「验证需求」对象（session_id + 挑战数据 + 原请求快照）；
- 新增 `miyoushe_login_verification.py`：aigis 解析（§2.2）、组件分流参数（§3.2）、票据组装（§4.2）、回传头构造（§4.2）、重发编排（§4.3 时序 7-8）；
- 人工验证 UI 通路：本机调试 Edge 打开本地页，页内加载 gt3+gt4 组件与挑战数据，回传票据给 Python 侧（形态参考参考实现 verify.js / genshin.py server.py 的本地 webserver 模式）。

---

## 9. 出处索引

官方（2026-11-04 抓取，均为线上现行版本）：
- 官方登录页入口：`https://user.miyoushe.com/` → 重定向 `#/login?is_from_legacy=1` → login-platform 前端
- 官方前端拦截器与错误码枚举：`https://user.miyoushe.com/login-platform/js/5823.9f588959.js`（aigis 拦截器、`NeedAigis=-3101` 枚举表、极验渲染 `use_v4` 分流）
- 官方前端密码登录：`https://user.miyoushe.com/login-platform/js/login.35d0ab6d.js`（`/account/ma-cn-passport/web/loginByPassword`、RSA encrypt、`x-rpc-source="v2.webLogin"`、-3208 分支）
- 官方 SDK：`https://webstatic.mihoyo.com/dora/biz/mihoyo-account-sdk/main.js`（`/common/aigis/api/createBySmartCaptchaTicket` + `checkSmartCaptcha`、`Ps` 极验分流、gt4 `userInfo` 带 session_id）
- 官方 gt4 组件副本：`https://webstatic.mihoyo.com/dora/lib/geetest/v4/gt4.js`

第三方实现：
- genshin.py（master）：`genshin/client/components/auth/subclients/web.py`（-3102 分支 + aigis 回传 + 重发）、`genshin/models/auth/geetest.py`（MMT 族模型 + `to_aigis_header`）、`genshin/utility/auth.py`（`get_aigis_header`、CN_LOGIN_HEADERS、RSA 公钥）、`genshin/client/components/auth/client.py`（`cn_login_with_password` 编排 + `login_with_mobile_number`）、`genshin/client/routes.py`（CN_WEB_LOGIN_URL/MOBILE_OTP_URL/MOBILE_LOGIN_URL、VERIFY_MMT_URL 仅国际服）、`genshin/constants.py`（DS_SALT["cn_signin"]=LyD1rXqMv2GJhnwdvCBjFOKGiKuLY3aO、"cn_passport"=JwYDpKvLj6MrMqqYU6jTKF17KNO2PXoS）、`genshin/errors.py`（-3102: GeetestFailed）
- MiyoQian（master）：`miyouqian/auth/login.py`（`ensure_ok_or_aigis`、RSA 模数与参考实现同钥——本调研 DER 解析比对实证）、`miyouqian/webui/app.js:2649-2790`（`completeAigisChallenge`/`showGeetestDialog`：gt3/gt4 分流 + 回传组装 + 递归重发）、`miyouqian/constants.py`（passport 端点表）
- QRscanner：`crates/mhy-qrscanner-mihoyo/src/aigis.rs`（契约注释 2026-09-11 真机核验 + `build_response_header` 补字段规格）
- zzz-calculator：`web/miyoushe.py`（-3102 归入验证码族、challenge_path/trace 绑定手法）
- 实测记录：IKUNHEIHIE/miyoushe-checkin `接口验证记录.md`（2026-10-23/26）

社区文档：
- UIGF `hoyolab/login/password_passport.md`（老端点 webapi create_mmt 前置流程 + gt3/gt4 mmt_data 结构——老体系参考）、`other/error_code.md`（未收录 -3101/-3102，缺口实证）

本地基准：
- `miyoushe-api-flow.md`（成功路径 + game_record 风控链 §5 + 模块划分 §7.2）

---

## 10. 崩铁开源项目登录处理对照（2026-11-04 外部交叉调研）

> 目的：用崩铁/米哈游生态的开源项目实现，对本文档 §1-§9 的登录验证分支规格做独立互证。此前证据 = 官方前端反混淆 + genshin.py + 一条短信链真机记录（S6），缺少「第三方桌面工具」侧的独立互证；本章补齐。
>
> 方法：GitHub code search（`x-rpc-aigis` / `NeedAigis` / `ma-cn-passport`+`aigis` / `loginByPassword` 组合检索）定位命中项目，逐个在线读源码（gh api raw），逐项与本规格对照。全部为源码逐行引用级证据，另注可信度限定。
>
> 证据分级沿用本文档开头约定；每条结论附仓库与文件路径（持久索引）。

### 10.1 首要事实：官方 Snap.Hutao 主仓库已不可访问

调研开始时按任务预期克隆 `DGP-Studio/Snap.Hutao`，得到 **404**（2026-11-04 实测，`gh api repos/DGP-Studio/Snap.Hutao`）。现存的可用来源：

| 来源 | 状态 | 说明 |
|---|---|---|
| `SnapHutaoRemasteringProject/Snap.Hutao.Remastered` | 活跃（913 星，2026-11-01 推送） | 社区维护的重制版，本章 Snap.Hutao 结论基于它 |
| `DGP-Studio/SnapHutaoArchive` | 官方存档 | DGP-Studio 组织名下的存档仓 |
| `wangdage12/Snap.Hutao` | 旧版完整存档（122 星） | 抽查其 `HoyoPlayPassportClient.cs` 的 `LoginByPasswordAsync` 与 Remastered 一样为国服 `NotSupportedException`，两版在密码登录上行为一致 |

### 10.2 项目对照总表

「崩铁相关」按三类标注：**崩铁核心**（崩铁专用/主力支持 hkrpg）、**全家桶**（米哈游多游戏工具，含星铁）、**通用米游社**（账号链跨游戏通用，记作互证源）。

| 项目 | 语言/形态 | 与崩铁关系 | 密码登录 | -3101/aigis 验证分支 | 极验组件 | 人工解题 UI | 会话/凭据持久化 | 出处（仓库 → 文件） |
|---|---|---|---|---|---|---|---|---|
| Snap.Hutao（Remastered） | C#/WinUI3 | 全家桶 | **国服无**（接口+国际服实现，国服方法体 `NotSupportedException`）；国际服 body 带 `token_type:2` | 短信链有：读响应头 `X-Rpc-Aigis` → `TryVerifyAigisSessionAsync` → 票据回填**单次重试**；码表 `-3101`+`-3202` | **仅 gt3**（`GeetestWebView2ContentProvider` 加载 gt.0.5.2.js） | WebView2 内嵌窗口；先试胡桃云打码（用户可配 URL），失败再人工 | SQLite `users` 表，Cookie 序列化存 SToken/LToken/CookieToken 三列，未见字段级加密 | SnapHutaoRemasteringProject/Snap.Hutao.Remastered → `Web/Hoyolab/Passport/{PassportClient,HoyoPlayPassportClient,HoyoPlayPassportClientOversea}.cs`、`Service/Geetest/{GeetestService,AigisSession}.cs`、`Web/Response/KnownReturnCode.cs`、`ApiEndpoints.csv` |
| Starward（官方） | C#/WinUI3 | 全家桶 | 无（零 API 登录） | 无自有处理（aigis 全仓检索 0 命中） | —（验证由官方登录页自带） | WebView2 打开 `www.miyoushe.com` + 注入 JS 自动点开官方登录框，用户人工登录，完成后 CookieManager 抓全量 cookie | cookie 串 → GameRecordService → SQLite | Scighost/Starward → `src/Starward/Features/GameRecord/LoginPage.xaml.cs` |
| Moonward（Starward 系增强 fork） | C# | 全家桶 | 无（只做短信链） | **有，最完整**：`SendPassportAsync` 每响应读 `x-rpc-aigis` 头 → 上层 `result.Aigis is not null` 即重试（**不看 retcode**），3 次循环上限 | **gt3+gt4 双脚本同载**（gt.0.4.9.js + gt4.js），分流键 = data 内有无 `challenge` 字段 | WebView2 内嵌弹层（`GeetestVerifyPopup`），HTML 由 `GeetestHelper.BuildHtml` 现拼，配置 base64 传参防转义 | 设备 id/fp 与米游社 App（Hyperion）配置共享；cookie 串（v1/v2 全键名拼装）交 GameRecordService 入库 | TurmoilZoom/Moonward → `src/Starward.Core/GameRecord/Passport/{MihoyoPassportClient,CaptchaAigis}.cs`、`src/Starward/Features/GameRecord/{CaptchaLoginService,CaptchaLoginDialog.xaml.cs,GeetestHelper}.cs` |
| March7thAssistant | Python | 崩铁核心 | **无**（排除确认：全仓树检索 login/mihoyo/api 仅命中截图资源，无任何米游社 API 登录代码；登录=游戏内画面自动化） | 无 | — | — | — | moesnow/March7thAssistant → git trees 检索（2026-11-04） |
| pompom-webext | TS/浏览器扩展 | 崩铁核心 | 无（依赖浏览器登录态，任务预期确认） | 无登录验证；处理 **game_record 1034 链**（createVerification/verifyVerification） | 官方页面环境里的组件 | 触发风控 → 后台 `tabs.create` 打开官方战绩 H5 页（`webstatic.mihoyo.com/app/community-game-records/rpg/`）→ content-script 在官方页面上下文触发极验 → `finish_captcha` 消息回传三元组 → verifyVerification；自动解题代码已注释弃用 | chrome.storage；`declarativeNetRequest` 对目标 API 剥 `Set-Cookie` 防污染扩展上下文 | daidr/pompom-webext → `src/background/index.ts`、`src/utils/networkHook.ts` |
| Venus | Java/Android | 全家桶 | **国服 app 形态全实现**（`/account/ma-cn-passport/app/loginByPassword`） | 有：`retcode==-3101 ‖ aigis 头非空` 双条件 → 抛 `AigisRequiredException`；**无解题 UI**（直接报错停，验证分支是它的实现门槛） | —（未实现） | —（抛异常给用户指引） | Android 本地按用户名存 stoken/mid/aid（`tools.write`） | MuxiaoWF/Venus → `app/src/main/java/com/muxiao/Venus/User/PasswordLogin.java`、`common/HeaderManager.java`、`common/{Constants,MiHoYoBBSConstants}.java`、`User/UserLoginActivity.java` |
| TRSS-Plugin | JS（Node） | 通用米游社 | **国服 app 形态全实现** | 有：`retcode===-3101` → 解 aigis 头 → gt3 解题 → 票据重发 | gt3 | 聊天里发第三方手动解题页链接（`challenge.minigg.cn/manual/index.html?gt=&challenge=`） | 框架托管（未细查） | TimeRainStarSky/TRSS-Plugin → `Apps/miHoYoLogin.js` |
| helloTiKi/mysApi | JS | 通用米游社 | **国服 web 形态**（`passport-api.miyoushe.com/.../web/loginByPassword`，与本规格端点一致）；body 带 `token_type:4` | 有：`retcode==-3101` → 本地 geetest.js 解题 → `{session_id};{btoa(validate)}` 重发 | gt3 | 本地 node 组件（`geetest.js`，代码质量一般，整体可信度低） | 内存 cookie 对象 | helloTiKi/mysApi → `login/weblogin.js` |
| FurinaChronicle | C# | 通用米游社（原神向） | 国服无；国际服 app 形态全实现（同 Snap.Hutao 国际服：`token_type:2` + aigis/verify 双头） | 国服短信链有（aigis 头回读透传上层）；国际服密码登录有（aigis+verify 双挑战解析） | gt3 | 未内嵌（票据组装 `CompleteGeetestChallenge` 提供，解题宿主在外部） | 未细查 | DaKang233/FurinaChronicle → `FurinaChronicle.Infrastructure/Passport/MiHoYoPassportClient.cs` |
| TeyvatGuide | TS（Tauri） | 通用米游社（原神向） | 无（短信+扫码+换票） | 短信链有（aigis 参数贯穿发码/登录/换票）；**换票接口 `getCookieAccountInfoBySToken` 也支持 aigis** | 双形态（Moonward 的参考对象） | 应用内（未逐行查） | 应用自管理 | BTMuli/TeyvatGuide → `src/request/passportReq.ts` |
| BennettChina/mihoyo-login | TS | 通用米游社 | 无（扫码链） | 发码链有：`-3101` → 返回 aigis 头 | — | 外部解题 API 服务（config.captcha.apiUrl，把 challenge 发给外部拿 validate） | 未细查 | BennettChina/mihoyo-login → `util/api.ts` |

补充命中（检索命中但未逐行调研，仅记录）：`QooLianyi/PaimonsNotebook`（Kotlin，`NeedAigis` 字样命中）、`ky3-studio/ky3-Launcher` 与 `lihua123123/ellen.launcher`（Snap.Hutao 同构 fork）、`FufuLauncher/FufuLauncher`、`nekwken/MihoyoBBSAutoSigner`、`nekwken/mhy-QRscanner`（即本文档 S5，已有记录）。

### 10.3 与本规格（§0-§8）的逐项互证清单

以下条目为本章独立证据**支持**本规格的部分（互证计数：**10 项**）：

| # | 本规格条目 | 本章互证源 | 判定 |
|---|---|---|---|
| 1 | -3101 = NeedAigis，验证触发码 | Snap.Hutao `KnownReturnCode.RET_NEED_AIGIS = -3101`；Venus `RETCODE_NEED_AIGIS = -3101`；TRSS/helloTiKi/BennettChina 按 `-3101` 分支。**五个独立实现同值** | ✅ 互证强化 |
| 2 | 挑战在响应头 `x-rpc-aigis`，body 为空 | 全部带验证分支的实现（Snap.Hutao/Moonward/TRSS/helloTiKi/Venus/FurinaChronicle）无一例外从**响应头**读取；无任何项目从 body 读挑战 | ✅ 互证强化 |
| 3 | aigis 头外层结构 `{session_id, mmt_type, data}` | Snap.Hutao `AigisSession` 与 Moonward `CaptchaAigis` 两模型字段名完全一致（session_id/mmt_type/data 字符串） | ✅ 互证强化 |
| 4 | 票据回传格式 `{session_id};{base64(JSON)}` | 全部验证实现同格式（Snap.Hutao `$"{SessionId};{b64}"`、Moonward `FormatAigisHeader`、TRSS/helloTiKi 同构） | ✅ 互证强化 |
| 5 | 原样重发 loginByPassword（body/头不变 + aigis 头） | TRSS（同 data 同 headers 再 post）、helloTiKi（同）、Moonward（aigisHeader 参数重入同一函数）、Snap.Hutao（`SetXrpcAigis` 后重入）、FurinaChronicle 同构 | ✅ 互证强化 |
| 6 | gt4 组件 `userInfo` 必须携带 `{"session_id":…}`（§3.2） | Moonward `GeetestHelper` gt4 分支 `userInfo: JSON.stringify({ session_id: sessionId })`——独立实现复现了官方前端行为 | ✅ 互证强化 |
| 7 | gt3/gt4 组件脚本都加载（§8.1.3） | Moonward 同页加载 `gt.0.4.9.js` + `gt4.js` 双脚本（与 MiyoQian 手法同）；Snap.Hutao 仅 gt3 为**反例**（见 §10.4-5） | ✅ 互证（Moonward 侧） |
| 8 | 登录请求头 app_id=`bll8iq97cem8`、game_biz=`bbs_cn`、device_id+device_fp 必带 | Venus/TRSS/BennettChina/helloTiKi/TeyvatGuide/FurinaChronicle 全一致 | ✅ 互证强化 |
| 9 | RSA 公钥 1024-bit 原文（§2.2，miyoushe-api-flow.md） | Snap.Hutao（注明出处 UIGF-org/Hoyolab.Salt）、Venus、helloTiKi、TeyvatGuide 四家逐字一致 | ✅ 互证强化 |
| 10 | 重发时重新生成 DS（本规格 §4.3 保守建议） | Moonward/Snap.Hutao/TRSS 的 DS 均为**请求时现算**（无缓存复用写法）——「重发刷新 DS」是社区实现的自然默认行为，无一项目尝试保留旧 DS 重发 | ✅ 保守建议升级为多源一致实践 |

### 10.4 矛盾与待实测仲裁清单

以下条目为外部实现与本规格**不一致或需限定**的部分（矛盾/待仲裁计数：**6 项**）：

| # | 争议点 | 各方口径 | 状态与仲裁建议 |
|---|---|---|---|
| 1 | **票据失败的 retcode：-3102 还是 -3202** | 本规格：-3102 = 票据无效（genshin.py 映射 + 实测记录 S6 真机往返）；Snap.Hutao 码表：`RET_AIGIS_FAILED = -3202`（注释「极验失败」），**码表无 -3102 条目** | **显式矛盾，需实测仲裁**。可能两码并存（-3102 aigis 票据无效 / -3202 极验验证失败），也可能 Snap.Hutao 码表滞后。实测方法：故意提交畸形票据，记录实际返回码。实现层面建议两码都按「换新会话重新验证」处理（处置相同，不影响流程） |
| 2 | **「gt4 为主」的适用范围** | 本规格 §3.1：「国服新 passport 登录链当前实际形态 = 极验 v4」（依据官方 web 登录页）；但 app 形态（client_type 2/3）的社区实现**全部按 gt3 处理**：TRSS/helloTiKi/Snap.Hutao/FurinaChronicle 的 aigis data 均解出 `gt+challenge` 走 gt3 | **本规格结论需加限定**：gt4 是 **web 形态**（官方登录页）的现状；app 形态下发的 aigis data 在社区实现中普遍为 gt3 形态。若我们走 app 形态端点（§10.5-1），gt3 是主要预期。Moonward 的「data 内有无 challenge」分流是形态不可知的安全写法，建议照抄为兜底判据（与 use_v4 判据并联） |
| 3 | **web 形态登录 DS salt 是否唯一** | 本规格（miyoushe-api-flow.md §2.3）：`LyD1rXqMv2GJhnwdvCBjFOKGiKuLY3aO` 无 b/q（参考实现实测背书）；helloTiKi web 形态用 `OeLQMQksh16hrSTrOZiEjjhDFAJZNdr9` 无 b/q（单源，代码质量一般，可能未经真机验证） | 低可信度矛盾，不推翻实测结论。列入待实测（若 LyD1 失效再试 OeLQ）。另注意 genshin.py `constants.py` 里 `cn_signin`（LyD1…）与 `cn_passport`（JwYDp…）双 salt 并存的命名，暗示 salt 按端点形态分族 |
| 4 | **登录 body 的 token_type 字段** | 本规格 web 形态：仅 `{account, password}`（实测通过）；helloTiKi web 形态带 `token_type:4`；国际服 app 形态带 `token_type:2`（Snap.Hutao Oversea + FurinaChronicle 一致）；**国服 app 形态不带**（Venus/TRSS，均实测自述可用） | 字段宽容（服务端可缺省），非硬矛盾。补充结论：国际服必须带 token_type:2，国服 app/web 均可缺省。我们走国服 web 形态保持两字段即可 |
| 5 | **gt3 票据的 `\|jordan` 后缀** | 本规格裁定不引入（参考实现裸三元组实测可用）；TRSS/FurinaChronicle 在 gt3 票据 seccode 拼 `validate+"|jordan"`；Snap.Hutao 在 **game_record 三头注入**（`x-rpc-challenge`+`x-rpc-validate`+`x-rpc-seccode=validate|jordan`，见 `HoyolabHttpRequestMessageBuilderExtension.SetXrpcChallenge(challenge, validate)`）也用 jordan | 场景不同不能强裁。对登录链：仅当 gt3 兜底被触发时才相关，实测时先裸值后 jordan（本规格 §4.2 的建议维持）。旁证：Snap.Hutao 的三头注入形态（validate/seccode 作为请求头而非 body）是 game_record 风控链的另一种提交变体，与 miyoushe-api-flow.md §5 的 verifyVerification body 形态并存 |
| 6 | **验证分诊依据：码值还是头** | 本规格 §8.1.1：按 `-3101`/`-3102` 码值分诊、不看文案；Moonward/Snap.Hutao 短信链：**只看 aigis 头是否非空**（不看码）；Venus：码值 + 头**双条件**（`retcode==-3101 ‖ aigis头非空`） | 非矛盾，是实现策略光谱。头判定更鲁棒（免疫码表变动），码判定语义更清晰（-3102 与初次触发可区分日志）。建议采纳 Venus 的双条件：码值命中**或**头非空都进验证分支 |

### 10.5 对我们 `one_dragon/mys/` 实现的新增可借鉴细节

按价值排序，均为前九章未覆盖的增量信息：

1. **端点双形态的分野要显式建模**（多源收敛的事实表）：
   - web 形态：`passport-api.miyoushe.com/account/ma-cn-passport/web/loginByPassword`，client_type=4，DS=salt `LyD1…` 三段式无 b，响应 **Set-Cookie 直下登录态**（零 token 交换）——本规格现状；
   - app 形态：`passport-api.mihoyo.com/account/ma-cn-passport/app/loginByPassword`，client_type=2，DS=salt `JwYDpKvLj6MrMqqYU6jTKF17KNO2PXoS` **五段式带 b=body**（Venus 注释「已用真实抓包 DS 反算命中验证」+ TRSS client_type=2 注释 + genshin.py `cn_passport` salt 三源一致），响应 **body 返回 `data.token.token`（stoken）+ `user_info.{aid,mid}`**，需走 stoken 换票链（getLTokenBySToken/getCookieAccountInfoBySToken，且换票接口自身也可能触发 aigis，TeyvatGuide 为 aigis 参数留位）；
   - 国服登录域 `passport-api.mihoyo.com` 与 `passport-api.miyoushe.com` 双域名并存（Snap.Hutao/TeyvatGuide/Venus/TRSS 用前者，helloTiKi/我们参考实现用后者），同一服务。实现时选定一个域名常量即可，不必双支持。
2. **Venus 的 -3101 双条件判定**（码值 OR aigis 头非空）照抄——免疫官方码表语义漂移（对应 §10.4-6）。
3. **Moonward `GeetestHelper.BuildHtml` 的验证页工程手法**（与我们 §8.4 的调试 Edge 本地页直接对标）：
   - 挑战配置与 session_id **base64 编码后嵌入 HTML**，页内 `b64ToUtf8` 解码——避免 gt/challenge 里的特殊字符破坏 HTML/JS（我们的本地页传参照抄）；
   - `onReady` 即 `verify()`/`showCaptcha()` 自动弹出 + `onClose`/`onError` → 回传 `cancel`——取消路径闭环（C# 侧收到 cancel 返回 null → 上层抛 `OperationCanceledException`）；
   - 登录对话框不动、验证弹独立层（`GeetestVerifyPopup.ShowAsync`）——UI 分层参考。
4. **验证重试上限**：Moonward 用 3 次循环（本规格 §8.1.6 建议 2 次）——取 2-3 均可，关键是循环上限防死循环，Moonward 的 `attempt < 3` + 超限抛 `miHoYoApiException(-1, "Aigis verification failed too many times.")` 写法可直接借鉴。
5. **Snap.Hutao 的两层验证设计**：云打码优先 → 失败再 WebView2 人工。我们不接打码平台（§8.3 红线维持），但「**先无感/自动、失败再人工**」的分层与极验 v4 adaptive 特性（§3.3 多数静默通过）天然契合：初始化组件即自动尝试，onSuccess 直接回传；仅 `onClose`/超时才升级为人工滑块 UI。
6. **pompom 的「官方页面做验证宿主」**：后台开官方 H5 页 tab + content-script 在官方页面上下文触发极验——组件版本与 api_server 配置天然永远正确，零组件维护成本。若我们调试 Edge 方案遇组件加载失败，这是备选形态（打开官方任意带登录/验证能力的页面做宿主）。
7. **device_fp 宽容度**：Venus 真实 getFp（platform="2" 安卓口径）；Moonward 默认占位 `"0000000000000"`；TRSS `random_string(13)` 随机假值——三种形态均有实现自述可用，登录链对 device_fp **非硬校验**。与我们参考实现「fp 缺失降级不带头」（miyoushe-api-flow.md §3.3）一致方向：真实值最优、假值/缺省可用。实现时保持「能取则取、取不到降级」即可。
8. **头集增量**（app 形态头集，Venus `get_password_headers` 全集）：`x-rpc-sdk_version` + `x-rpc-account_version`（同值，Venus 用 `2.42.0`）与 `x-rpc-lifecycle_id`（进程启动时生成一次的 UUID）三个头为 web 形态头集（miyoushe-api-flow.md §2.4）之外的新成员；`x-rpc-aigis` 头**空值也带**（首次请求传 `""`，Moonward/TeyvatGuide/Venus/TRSS 四源一致写法）——比「缺省不带」更贴官方客户端行为，建议照抄。
9. **实名认证分支**（Venus 独有处理）：登录响应可能含 `realname_info.required` / `need_realperson` 布尔——触发时需实名流程，本规格与 miyoushe-api-flow.md 均未覆盖。解析响应时预留这两个字段的识别与结构化报错（stage=login_realname），防止静默失败。
10. **签名串与发包串逐字节一致的再实证**：Venus 注释「参与签名的 body 必须与实际发出的 body 逐字节一致」（Gson 会把 `=` 转义 `\u003d` 与官方 App 行为一致）——Python 侧照本规格 §4.1 的「b=实际发送串」原则实现即可，注意 `json.dumps` 的分隔符/ensure_ascii 选择确定后 DS 与 body 共用同一字符串变量，不要两次序列化。
11. **BennettChina 扫码链域名补充**：`passport-api.miyoushe.com/account/ma-cn-passport/web/createQRLogin`（web 形态扫码端点存在，TRSS 同款）——若未来做扫码兜底，web/app 双形态端点都有现成实现可参照。

### 10.6 本章结论摘要

1. **没有崩铁核心项目实现了国服密码登录**：Snap.Hutao 国服密码登录方法体为 `NotSupportedException`（国际服才实现）、Starward 官方零 API 登录（webview 官方页）、March7thAssistant 纯游戏内自动化、pompom-webext 不做登录。本规格的密码登录验证分支在崩铁专用项目群中**找不到独立互证**——这一缺口由全家桶/通用米游社项目（Venus、TRSS-Plugin、helloTiKi）补上。
2. **验证分支机制本身获多源强互证**：-3101 码值、x-rpc-aigis 响应头、`{session_id};{base64}` 票据、原样重发四要素在 6 个独立实现中完全一致（§10.3）。
3. **需要实测仲裁的矛盾 1 项**（-3102 vs -3202，§10.4-1），**规格需加限定 1 处**（gt4 为主仅适用 web 形态，app 形态社区实现普遍 gt3，§10.4-2），其余差异为实现策略光谱。
4. **最大增量收获**是端点 web/app 双形态的完整分野表（§10.5-1）与 Moonward 的验证页工程手法（§10.5-3），二者可直接落入 §8.4 的实现落点。
