# 米游社账号接入 MCP 三工具 迭代设计（总纲）

## 0. 元信息

- 迭代目标：提供米游社账号的登录/登出 MCP 工具与崩铁角色列表 MCP 工具。用户裁定（§0 末所载四项）：登录方式 = 密码登录（方案 A）；凭据存放 = `config/0N/mys/`；MCP 登录工具描述必须带知情说明（密码会传入大模型，由使用者自行决定）；登录模块归 `one_dragon/mys/`（跨游戏通用），游戏专属 client 归各游戏包。
- 状态：定稿（三轮对抗收敛：23 + 17 + R 系列，全部处置；试读通过）
- 文档清单：无详设（单文档方案，本文件即完整设计；协议细节的权威出处 = 正本区两份调研文档，见 §2.7 依据清单）

## 1. 问题与动机

- 现状症状：
  1. 账号练度数据只有两条路——游戏内逐格扫描 app（约 1 小时/次，2026-10-22 实测）或临时借道外部规划器进程（非自有代码、不可编程调用）；
  2. 米游社账号 API 客户端在本仓零实现（2026-11-03 代码审计缺口①：网络栈/登录/设备身份/DS/风控链全缺位；`src/sr_od/sr_map/mys/` 仅无登录的地图静态资源请求，不构成账号 API 先例）。
- 根因归层：**能力缺位**（不是表示/约定/流程/语义任何一层的缺陷，是新能力建设；无「治本」对象可修）。
- 解决到哪：
  1. `one_dragon/mys/` 通用包：密码登录、登出、设备身份、DS 签名、cookie 罐、aigis 验证分支、会话持久化、通用 mys 请求客户端；
  2. `sr_od/mys/`：崩铁 hkrpg 角色列表接口封装（基于 one_dragon client）；
  3. `sr_od/backend/mcp/`：注册 3 个 MCP 工具。
- 明确不解决（防范围外溢）：
  1. GUI 登录卡片（后续迭代）；
  2. `avatar/info` 全练度获取与 `account_profile_scan.json` 格式转换（后续迭代，本次只做角色列表）；
  3. 扫码登录、短信登录（平行链，规格已调研未实现）；
  4. 验证的自动化绕过（人工解题是设计承诺，见 §2.6 纪律）；
  5. app 形态端点（client_type 2/3 + stoken 换票链，login-verification-research.md §10.5-1 已记录备查，本次只实现 web 形态）；
  6. ZZZ 侧接入（`one_dragon/mys/` 包位置即为预留，不写任何 ZZZ 代码）；
  7. **game_record 1034 风控验证链**（createVerification/verifyVerification/`x-rpc-challenge` 持久携带，flow.md §5 全节）：与登录 aigis 链完全不同构（research §4.4），须独立模块，后续迭代实现；本迭代内 `request()` 触发 1034 时按裸 `MysApiError(1034)` 结构化返回、无解题出路（§2.2 request 注明，3.5 实机留观察点）。

## 2. 方案

### 2.1 系统级变化与分层

```
sr_od/backend/mcp/mys_tools.py   ← 3 个 MCP 工具 + MysAccessController（状态机/验证循环/线程编排）
        │ 使用
sr_od/mys/hsr_mys_client.py      ← 崩铁特有：角色自动发现 + hkrpg 角色列表
        │ 组合
one_dragon/mys/mys_client.py     ← 通用：登录/登出/aigis 单轮分诊与重发/通用 mys 请求
one_dragon/mys/{mys_const,mys_signing,mys_http,mys_session,mys_device,aigis_verifier}.py
        │ 落盘
config/0N/mys/{session.json, device.json, role.json}   ← 实例私有，gitignore 已覆盖
```

职责分界（总纲定死）：**验证的「单轮」在 client**（解析挑战 → 交出挑战等票据 → 票据组装 → 重发 → 观察结果），**验证的「循环」在控制器**（MysAccessController：持有 verifier、计数上限、每轮重开验证页）。one_dragon 层不持有 verifier、不做跨请求编排。

### 2.2 `one_dragon/mys/` 模块设计

#### `mys_const.py`（常量，零逻辑）

全部内联自 miyoushe-api-flow.md §2/§3/§4（该文档常量均经源码逐行核对 + 实测流量校对）：

- 端点：`LOGIN_URL = https://passport-api.miyoushe.com/account/ma-cn-passport/web/loginByPassword`；`GET_FP_URL = https://public-data-api.mihoyo.com/device-fp/api/getFp`；`ROLE_LIST_URL = https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie`；game_record 基座 `https://api-takumi-record.mihoyo.com/game_record/app/`（崩铁子路径由 sr_od 侧拼接）
- salt：登录 `LOGIN_SALT = 'LyD1rXqMv2GJhnwdvCBjFOKGiKuLY3aO'`（三段式 salt&t&r）；game_record `RECORD_SALT = 'xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs'`（DS2，q 排序、r∈[100001,200000]）
- RSA 公钥：**1024 位**（PEM 原文按 flow.md §2.2 复制；与参考实现及四家社区实现逐字一致，research §10.3-9）
- 头常量：
  - 登录头「十件套」= 5 个显式头（`x-rpc-app_id=bll8iq97cem8`、`x-rpc-client_type=4`、`x-rpc-source=v2.webLogin`、`x-rpc-game_biz=bbs_cn`、`x-rpc-sdk_version=2.31.0`）+ 设备头三件（device_id/device_fp 系，§2.2 mys_device）+ `Content-Type: application/json` + `ds`
  - game_record 头：`x-rpc-app_version=2.11.1`、`x-rpc-client_type=5`、`Referer=https://webstatic.mihoyo.com/`、`Content-Type: application/json`、桌面 Chrome UA（依据 account-client.mjs:47 实发口径，含 Content-Type）
- 主机白名单：`{'passport-api.miyoushe.com', 'api-takumi.mihoyo.com', 'api-takumi-record.mihoyo.com', 'public-data-api.mihoyo.com'}`（与参考实现 ALLOWED 的差异：换入 `public-data-api.mihoyo.com` 供 getFp；弃 `bbs-api.miyoushe.com`——本迭代无该域请求。角色发现走 api-takumi，本就在名单内）

#### `mys_signing.py`（签名与加密）

- `ds_login(t: int | None = None, r: str | None = None) -> str`：`f"{t},{r},{md5(salt=LOGIN_SALT&t={t}&r={r})}"`；t 默认秒级时间戳、r 默认 6 位 hex；t/r 可注入供测试向量断言（依据 flow.md §2，实测口径）
- `ds_record(query: dict, t: int | None = None, r: int | None = None) -> str`：DS2——`q` = query 按 key 字母序排序后 **URL 编码（percent-encoding，与参考实现 URLSearchParams.toString() 同规则）** 拼接，`b` = 空串（GET）（依据 flow.md §4.1/§6 对照表第 8 行）
- `rsa_encrypt(plain: str) -> str`：RSA-PKCS1 + 公钥，返回 base64（依据 flow.md §2.2）

#### `mys_http.py`（HTTP 抽象与 requests 实装）

- `HttpSendResult`（dataclass）：`status: int`、`headers: list[tuple[str, str]]`（**保序、保重复**——多条 Set-Cookie 不合并；取值用模块提供的 `header_get(headers, name)` 大小写不敏感助手）、`body: bytes`
- `HttpSend = Callable[[str, str, dict[str, str], bytes | None], HttpSendResult]`（url, method, headers, body）
- `RequestsHttpSend`（requests 实装类，运行入口装配时显式传入；**不是任何组件的默认值**）：Set-Cookie 全量经 `response.raw.headers.getlist('Set-Cookie')` 口径取（dict 合并视图会丢重复头）；**redirect 禁用、超时 25 秒**（口径照 flow.md §2.1/§4.2，与参考实现 redirect:'error' 一致）

#### `mys_session.py`（会话与设备持久化 + 异常）

- `session.json` 字段级 schema（定死）：`{"schema_version": 1, "saved_at": "<ISO8601>", "expired": true|null, "cookies": {"<name>": "<value>"}}`——`expired` 缺省视为 false
- `SessionStore(session_dir: Path, lock: threading.Lock)`（**store 实例由装配层构建并注入**，同一实例贯穿 client/controller——同锁互斥是 mark_expired 与滚动写不撞车的保证）：
  - 所有写操作 = 同目录临时文件 + `os.replace` 原子替换 + 权限尽力 `0o600`（POSIX；Windows 依 ACL 继承，尽力语义）；全部入口持 `lock`
  - `save_cookies(cookies: dict[str, str])`：滚动续存——更新 `saved_at` 与 `cookies`，**保留既有 `expired` 标记**
  - `save_session_full(cookies: dict[str, str])`：**整体覆盖**——重写 `session.json`（不含 `expired` 键）；仅「登录成功」与「验证成功重发成功」两个场景使用
  - `mark_expired()`：给 `session.json` 合并写入 `expired: true`（cookies 原样保留）；**文件不存在时幂等无操作**（没有会话就没有「过期」概念）
  - `load_cookies() -> dict[str, str]`：文件缺失/损坏返回空 dict
  - `is_expired() -> bool`：读 `expired` 标记
  - `clear()`：删除 `session.json` **与 `role.json`**（仅用户显式登出时调用；`device.json` **保留**——设备锚不随登出轮换）
  - `save_role(role: dict)` / `load_role() -> dict | None`：`role.json` = `{"role_id": "<字符串>", "server": "<区服>"}`（与 session.json 同锁）
  - `save_device(device_id: str)` / `load_device() -> str | None`：`device.json` = `{"schema_version": 1, "device_id": "<uuid>"}`（与 session.json 同锁；供 mys_device 读写设备锚）
- 异常：`MysApiError(code: int, message: str)`；`MysSessionExpired(MysApiError)`
- 会话失效映射（**单一常量** `SESSION_EXPIRED_RETCODES = frozenset({10001, -100})`，便于实测定案后修订）：`10001`（Please login，依据 skills/sr-od-account-inspection/references/api.md 错误码分诊表 2026-10-14 实测）、`-100`（TokenInvalid，依据 login-verification-research.md §5）；两权威源均未记载空罐打 game_record 的实际返回码，**以 3.5 实机首验定案**（landing 3.5 观察点）

#### `mys_device.py`（设备身份）

- `DeviceIdentity(store: SessionStore, http_send: HttpSend)`（两参必填，无默认）：
  - `device_id`：`device.json` 存在即用（**正常路径严禁轮换**——设备信誉锚，依据 research §3.4：已登录设备重复登录不触发验证）；文件**损坏（解析失败/字段非法）为唯一例外**：重新生成 + warning 留痕（损坏件已无法提供信誉，重生成是止损非轮换）
  - `get_headers() -> dict`：组装设备头；`device_fp` 走 `getFp`：内存缓存 24h；失败后 30 分钟冷却，冷却期内**降级不带头**（与参考实现一致，flow.md §3.3）
  - getFp 成功判据（**四条同时满足**）：HTTP ok + `retcode==0` + `data.code==200` + fp 匹配 `/^[a-z0-9]{6,100}$/i`（依据 flow.md §3.3 四判据 + account-device.mjs:34；「仅 retcode=0 不够」）；请求体 = device_id + 20 字段固定指纹模板（照抄 flow.md §3，不读真实硬件）

#### `mys_client.py`（核心客户端）

- 构造：`MysClient(store: SessionStore, device: DeviceIdentity, http_send: HttpSend)`——三参**全部必填无默认**（AGENTS.md §7：禁「默认没传入就自动用真实现」；requests 实装 `RequestsHttpSend` 由运行入口即 MCP 装配层传入，测试注入剧本式假实现，测试不注入则构造即失败——零副作用）
- **`login(username: str, password: str) -> LoginResult`**（单轮语义，无内部循环）：
  1. 组装登录头（十件套）与加密 body（`account`/`password` 均 RSA 加密）
  2. POST LOGIN_URL → 分诊（**双条件**：`retcode==-3101` **或** aigis 响应头非空 → 验证分支；message 文案一律不参与分诊，依据 research §10.4-6）：
     - `retcode==0` 且 Set-Cookie 非空 → `ok`（全量收 cookie 入罐并 **`save_session_full` 整体覆盖落盘**——覆盖任何 expired 标记；**并清除 role.json**——登录态换绑后强制重新发现角色定位）
     - 验证分支 → `need_verification` + `AigisChallenge`（解析：`JSON.parse(响应头 x-rpc-aigis)` → 外层 `{session_id, mmt_type, data}`；`data` 兼容字符串/对象双形态再 parse，依据 research §2.2 四源一致）
     - `-3102`/`-3202` 在 login 首轮不应出现（无票据可拒）；若出现按未知码抛 `MysApiError`
     - `-3208` → `MysApiError(-3208)`（密码错误过多，停止）；`-3235` → `MysApiError(-3235)`（账号风险，停止）；其它 → `MysApiError(code)`
- **`complete_verification(challenge: AigisChallenge, ticket: dict) -> LoginResult`**（单轮语义，**无内部循环**——循环归控制器 §2.4）：
  1. 组装票据（v4 = `getValidate()` + 补 `captcha_id` + `userInfo={"session_id":…}`；gt3 = 三元组原值**不加 |jordan**，依据 research §4.2/§10.5）
  2. 回传头 `x-rpc-aigis: f"{session_id};{base64(json.dumps(票据))}"` 塞**请求头**，原样重发 loginByPassword（body/其余头不变），**DS 重新生成**（多源一致默认，research §10.3-10）
  3. 分诊：`retcode==0` → **收取 Set-Cookie 全量入罐 + `save_session_full` 整体覆盖落盘**（与 login 成功路径同一收取逻辑，依据 research §4.3[8]）→ `ok`；`-3101` 或 aigis 头非空 → `need_verification` + **新 challenge**（从该响应的 aigis 头解析）；`-3102`/`-3202` → 票据被拒——若该响应携带新 aigis 头则解析为新挑战返回 `need_verification`，未携带则**自动补发一次裸 loginByPassword**（无票据）取 `-3101` 新挑战后返回 `need_verification`（两路都把「新会话」交给控制器重开验证）；`-3208`/`-3235`/其它同 login 分诊
- **`logout() -> None`**：仅本地清除（SessionStore.clear = 删 session.json 与 role.json + 内存 jar 清空）。**不调用任何官方登出端点**——flow.md §1 链路图与 research §9 出处索引均无登出端点记载，不引入未验证请求
- **`request(path_or_url: str, query: dict) -> dict`**：通用 mys GET——`path_or_url` 为 **绝对 URL（主机须在白名单）或 RECORD 基座相对路径**（前者供 binding/getFp 等非 record 域请求，如角色发现；后者供 game_record）；头 = 对应域头（record 域用 game_record 头 + DS2 `ds_record(query)`；binding 域用 game_record 头同款 + DS2，角色发现实测同管线同头集，依据 account-client.mjs:74 + trace 第 2 条）+ 设备头 + Cookie 罐全量；非 0 retcode 抛 `MysApiError`（`1034` 按裸 `MysApiError(1034)` 抛出——1034 验证链本迭代不实现，§1 明确不解决第 7 项）；`SESSION_EXPIRED_RETCODES` 映射 `MysSessionExpired`；响应 Set-Cookie 滚动入罐（滚动走 `save_cookies`，保留 expired 标记）
- **`AigisChallenge`**（dataclass，结构化）：`session_id: str`、`mmt_type: int | None`、`data: dict`（已二次解析）、`raw_header: str`

#### `aigis_verifier.py`（本地验证页，跨游戏通用）

- `AigisVerifier(open_browser: Callable[[str], None] | None = None)`：绑定**随机空闲端口**（port=0）；`open_browser` 为可注入的打开浏览器回调（**默认 None = 不自动打开**，仅返回 URL——AGENTS.md §7 同类纪律，测试不注入则不弹真实浏览器；MCP 装配层传 `webbrowser.open`）
- **挑战不下沉到 URL**：URL 仅 `http://127.0.0.1:<port>/verify`（无挑战参数）；服务端持有「当前 pending 挑战」，页面加载/刷新时 `GET /challenge` 取**最新** pending 挑战——刷新即换新挑战，不存在「旧 URL 刷旧题」
- `start(challenge: AigisChallenge) -> str`：挂载 pending 挑战、起服务（已起则复用）并返回 URL；`open_browser` 非空时调用之
- 页面 = 内嵌 HTML 模板（模块内常量，无外部文件）：**gt4 脚本（webstatic.mihoyo.com/dora/lib/geetest/v4/gt4.js）+ gt3 脚本（static.geetest.com/static/js/gt.0.5.0.js）双载**；JS 分流——`use_v4` 真值 → `initGeetest4`（product=popup）；否则 data 含 `challenge` 字段 → `initGeetest`（api_server 必传 `api.geetest.com`，`<meta name="referrer" content="no-referrer">`）；**两键双缺 → 页面显示结构化错误并按取消语义回传 `{"session_id": "...", "cancelled": true}`**（控制器收到即复位 idle，不猜组件，依据 research §10.4-2 并联仍可能双缺）；`onSuccess` → `POST http://127.0.0.1:<port>/ticket`，JSON `{"session_id": "...", "ticket": {…极验票据原对象}}`；`onClose/onError` → 同格式 `cancelled: true`
- `POST /ticket` 防线与配对：校验 `sec-fetch-site` 非 `cross-site` / Origin 为本端口页面（照参考实现 server.mjs:16 手法），不合格 403；**校验 payload.session_id 与当前 pending.session_id 一致**，不一致 409 丢弃（防旧页面解旧题的迟到票据污染新一轮挑战）
- 票据回传契约（页面 → 进程，仅 127.0.0.1 回环）：`{"session_id", "ticket"}` 或 `{"session_id", "cancelled": true}`
- `wait_ticket(timeout_sec: float = 300) -> dict | None`：阻塞等待（GUI/CLI 场景用）；**超时仅结束等待调用本身，不改变控制器状态与 pending 挑战**（页面仍有效可继续解）；MCP 场景不用阻塞式，用回调属性 `on_ticket`
- 生命周期：`close()` 释放端口；验证页 CSP 白名单（geetest/mihoyo/webstatic 域）照抄规划器 verify.html policy

### 2.3 `sr_od/mys/` 模块设计

#### `hsr_mys_client.py`

- `HsrMysClient(client: MysClient, store: SessionStore)`：组合通用 client（不继承）
- `get_characters() -> list[HsrCharacter]`：
  1. **过期短路**：`store.is_expired()` 为真 → 直接抛 `MysSessionExpired`（不发起注定失败的请求）
  2. 角色定位：读 `role.json` 缓存（`{role_id, server}`，**server 用缓存值**，不硬编码）；无缓存则 `client.request(ROLE_LIST_URL, {'game_biz': 'hkrpg_cn'})`（绝对 URL 形态）自动发现（过滤 hkrpg 区服，`is_chosen` 优先、否则首个），`role_id` **一律字符串化**（依据 flow.md §4.3），写入 `role.json`；发现失败抛 `MysApiError`
  3. `client.request('hkrpg/api/index', {'role_id': …, 'server': <缓存/发现值>})` → `data.avatar_list`
  4. 映射为 `HsrCharacter`（dataclass，**字段集冻结**）：`id: int`、`name: str`、`level: int`、`rarity: int`、`rank: int`（星魂数）、`element: str`、`base_type: int`（命途 id）、`equip: ConeSummary | None`（光锥 `name/level/rank/rarity`）——字段集被 index 实测响应覆盖（依据 trace.log hkrpg index 条目，2026-11-03 实测；index 结构快照以 fixture 固化进测试仓，摆脱易失件依赖）；icon 等大体积字段**不透传**
- `MysSessionExpired` 直接透传给上层（MCP 工具层翻译成「请重新登录」）

### 2.4 MCP 工具设计（`sr_od/backend/mcp/mys_tools.py`）

注册：`register_mys_tools(mcp: FastMCP, backend: SrBackendContext) -> None`，由 `app.py` 的 `create_mcp_server` 调用（与既有 register_prompts 模式一致）。会话目录 = 当前实例目录 + `mys`。

**`MysAccessController`**（模块级单例，进程级生命周期）——装配与验证循环持有者：

- 装配：构建 `SessionStore`（实例 mys 目录 + 进程级 `threading.Lock`）→ `DeviceIdentity(store, RequestsHttpSend())` → `MysClient(store, device, RequestsHttpSend())` → `AigisVerifier(open_browser=webbrowser.open)`——**requests 真实实装由本控制器（运行入口）传入**（AGENTS.md §7：真实现由运行入口传入；测试构建控制器时注入假 http_send）
- 状态：`idle` / `awaiting_ticket`（控制器入口持控制器锁串行化；SessionStore 内部另有同实例锁防落盘撞车）
- 验证循环（控制器所有，client 单轮）：
  1. `mys_login` 提交账密 → `need_verification(challenge)` → 状态 `awaiting_ticket`，`verifier.start(challenge)` 得 URL，attempt = 1，返回 `verification_required` 信封
  2. 页面回传票据（后台 daemon 线程，持控制器锁）→ `complete_verification`：
     - `ok` → 会话已由 client 落盘，状态 `idle`（后续 `mys_get_characters` 即成功）
     - `need_verification(新挑战)` 且 attempt < 3 → `verifier.start(新挑战)`（同端口更新 pending + 自动开浏览器），attempt += 1，仍 `awaiting_ticket`——用户看到新题，再解一次
     - `need_verification` 且 attempt ≥ 3 → 状态 `idle`，verifier `close()`，记录错误（信封在用户下次调用时体现 `error`）
     - `-3208`/`-3235`/超限异常 → 状态 `idle`，verifier `close()`，错误留档
  3. `cancelled: true` 回传 → 状态 `idle`、verifier `close()`
  4. **迟到票据防护**：回传处理入口检查状态 == `awaiting_ticket` 才处理；`idle` 状态下的任何回传直接丢弃（覆盖用户显式登出后迟到票据的场景）
- 并发语义（状态机定死）：
  - `awaiting_ticket` 期间再调 `mys_login`：**不重复登录**——立即丢弃新传入的账密参数（不存储不加密），返回现存 `verification_required` 信封 + 现存 URL
  - `awaiting_ticket` 期间调 `mys_get_characters`：无有效会话 → 返回 `verification_required` 信封（附现存 URL），不裸打请求
  - `awaiting_ticket` 期间调 `mys_logout`：执行登出（清会话）+ 状态回 `idle` + `verifier.close()`；**迟到票据被状态检查丢弃**（用户显式登出后，任何迟到的验证结果不得静默重建会话）
  - `wait_ticket` 超时（仅阻塞式场景）：只结束等待调用本身，不改状态、不关 verifier（页面仍有效）；MCP 异步场景无此路径
  - MCP server 重启：verifier 端口死亡，用户侧页面 POST 失败表现为页面错误；用户重新 `mys_login` 即新建 verifier（会话已落盘**且未标记过期** → `already_logged_in`；已标记过期 → 跳过判定走正常登录）
- 工具返回统一信封：`{"status": str, "message": str | None, "data": any}`；`status ∈ {'success', 'already_logged_in', 'verification_required', 'session_expired', 'error'}`

#### `mys_login`

- 参数：`username: str`、`password: str`
- **描述（知情声明为用户裁定原文，必须完整写入）**：
  > 登录米游社账号（国服）。⚠️ 知情说明：需要在参数中提供账号与密码——**密码会作为工具参数传入大模型上下文，存在泄露风险，是否继续由使用者自行决定**。成功后仅落盘 cookie 会话（config/当前实例/mys/session.json），密码不落盘。
- 「已登录」判定（定死）：`session.json` 存在且 cookies 非空 **且 `is_expired()` 为假** → `already_logged_in`；**已标记过期 → 跳过 already_logged_in 走正常登录**（成功后 `save_session_full` 整体覆盖 session.json，标记随覆盖消失）。**不主动探测官方接口**（避免每次登录工具调用都打真实请求）；**会话失效永不清除任何落盘文件**——过期只打标记 + 提醒重登，重登失败（错密/风控）时旧文件原样保留
- 流程：已登录 → `already_logged_in`；`awaiting_ticket` → 复用现存信封（见状态机）；否则 `client.login`：
  - `ok` → `success`（返回值**不含任何 cookie/token**）
  - `need_verification` → 进验证循环（见状态机），返回 `{"status": "verification_required", "message": "请在浏览器打开以下地址完成人机验证；若被要求再次验证请重复解题（最多 3 次），完成后用 mys_get_characters 验证登录结果", "data": {"url": …}}`

#### `mys_logout`

- 无参数；描述：「登出米游社账号：清除本机保存的登录会话与角色定位缓存」。流程：状态机语义（含 `awaiting_ticket` 期取消）→ `client.logout()` → `success`（无会话也返回 success，幂等）

#### `mys_get_characters`

- 无参数；描述：「获取崩坏:星穹铁道角色列表（等级/稀有度/星魂数/命途/光锥摘要）；会话过期时返回 session_expired 并提示重新登录，不清除任何本机数据」
- 流程：`awaiting_ticket` → `verification_required` 信封；`HsrMysClient.get_characters()` → `success` + 角色数组；`MysSessionExpired` → **控制器置过期标记 +** `session_expired` + 「数据已过期，请重新登录（mys_login）；本机数据不受影响」；`MysApiError(1034)` → `error` + 明确文案「数据接口触发风控验证，本版本未实现该验证链，请稍后重试或反馈」；其它 `MysApiError` → `error` + code

### 2.5 跨层接口契约（总纲定死，实现不得擅改）

1. `LoginResult`：`status: Literal['ok', 'need_verification']`；`challenge: AigisChallenge | None`（need_verification 时必有 challenge——**验证循环所需的全部输入**）
2. `MysClient.login(username, password)` / `complete_verification(challenge, ticket)` 均为**单轮语义**（成功路径统一走「Set-Cookie 全量入罐 + `save_session_full`」）；重试循环归 `MysAccessController`（上限 3，计数在控制器）
3. `HttpSend` / `HttpSendResult` 契约如 §2.2 mys_http（headers 为 `list[tuple[str, str]]` 保序保重复；http_send 全链路**必填无默认**，真实实装由运行入口传入）；`SessionStore` 实例同样注入式贯穿 client/controller（同实例 = 同锁）
4. `AigisVerifier.start(challenge) -> str`（URL，port=0 随机，URL 不含挑战参数）；票据/取消回传 payload = `{"session_id", "ticket"}` / `{"session_id", "cancelled": true}`；`GET /challenge` 返回当前 pending 挑战
5. `HsrMysClient.get_characters() -> list[HsrCharacter]`；`HsrCharacter` 字段集冻结如 §2.3
6. MCP 信封结构如 §2.4（三工具共用）
7. 会话文件布局：`config/0N/mys/{session.json, device.json, role.json}` 三文件、JSON 格式、原子写 + 0600 尽力；`session.json` 字段 schema 定死（§2.2 mys_session）；登出清 session.json 与 role.json、保留 device.json；**会话失效不清任何文件**（只打 expired 标记）

### 2.6 凭据与安全

- **密码**：仅存在于 `mys_login` 调用栈内存；加密后进请求体；不落盘、不写日志；`awaiting_ticket` 期间重复调用 mys_login 时新账密**即收即弃**
- **cookie**：落盘 `session.json`；每次 API 响应滚动续存（保留 expired 标记）；登录/验证成功时 `save_session_full` 整体覆盖（清 expired 标记）；**cookie 与一切请求头不进任何日志、异常文本与 MCP 错误信封**（与密码同级的红线，landing 3.2 有同款断言）；落盘 = 原子写（临时文件 + `os.replace`）+ 权限尽力 `0o600`
- **device_id**：落盘 `device.json`；正常路径严禁轮换（设备信誉锚）；**唯一例外** = 文件损坏（解析失败/字段非法）时重生成并 warning 留痕
- **备份/同步盘声明**：`session.json` 为明文凭据文件，gitignore 只管 git——用户使用同步盘/备份工具覆盖 `config/` 时会被带走，风险由使用者自担；后续迭代可评估加密存储
- **路线声明**：本迭代为**持久凭据路线**（用户裁定），区别于 sr-od-account-inspection skill 浏览器路线的「凭据不落盘、一次性流转」纪律——两条路线并存，skill 纪律不约束本路线
- **会话失效不清数据**：过期只打标记 + 提醒重登（§2.4），不清除任何落盘文件（session.json/role.json，以及将来任何数据快照）；清除仅发生于用户显式登出，或被成功登录整体覆盖。理由：重登可能失败（错密/风控），清了旧数据用户就一无所有（用户裁定 2026-11-04）。**登录成功删除 role.json** 属缓存重建（成功会话下立即自动重发现，无数据损失），不在「不清除」约束内
- **知情声明**：`mys_login` 描述必含（§2.4 原文）
- **纪律红线**：不绕验证、不接打码平台；验证重试上限即停；`-3208`/`-3235` 即停并明示用户；票据不是凭据——登录信息只从成功登录的 Set-Cookie 取

### 2.7 依据清单

- 正常路径（登录头/加密/DS/cookie 收取/成功判据）：[miyoushe-api-flow.md](../../miyoushe-api-flow.md) §2/§3/§4（源码逐行 + 实测流量校对）
- 验证分支（-3101/-3102/-3202 分诊、aigis 双层解析、gt3/gt4 分流、票据组装、重发、上限）：[login-verification-research.md](../../login-verification-research.md) §1-§4、§10.3（互证 10 项）/§10.4（矛盾 6 项及处置）/§10.5（可借鉴细节）
- 会话失效码：skills/sr-od-account-inspection/references/api.md 错误码分诊表（10001）+ login-verification-research.md §5（-100）；空罐实测定案见 landing 3.5
- index 响应数据结构：hkrpg index 实测条目（2026-11-03 trace 校对；结构快照以 fixture 固化进测试仓，字段集冻结于 §2.3）
- 决策出处：§0 元信息所载用户裁定

### 2.8 关键取舍

| 决策点 | 选定 | 备选与放弃理由 |
|---|---|---|
| 登录方式 | 密码登录（方案 A） | 扫码：未被参考实现实证，需重走调研验证；会话导入（方案 C）：依赖外部规划器进程，不可编程、不自主 |
| 端点形态 | web 形态（对照 app 形态分野：login-verification-research.md §10.5-1） | app 形态：stoken 换票链 + 专用 salt，实现面更大；web 形态已被参考实现与本机实测双重验证。会话生命周期：web 形态 cookie 无续期链，失效即需密码重登（密码周期性进入 LLM 上下文的知情风险面已知，见 §2.4 知情声明）——3.5 实机记录失效时间作为运维依据 |
| HTTP 栈 | `requests` 同步 | httpx/aiohttp：全仓既有惯例为 requests（`import requests` 文件数 28，实测属实），低频场景无并发需求；TLS 指纹经实验排除为变量（api.md TLS 节，curl_cffi 对照）；requests 直连 passport/game_record 未单独实测，由 3.5 实机首验兜底 |
| http_send 默认值 | **必填无默认** | 默认 requests 实装：违反 AGENTS.md §7「禁默认没传入就自动用真实现」（外部 IO 硬约束，规范原文优先级高于仓内惯例如 push channels 直调写法）；fail-fast 哨兵折中但不如必填直白 |
| 会话格式 | JSON 三文件 | YamlConfig 单文件：凭据文件与普通配置隔离更清晰，且与参考实现实证形态同构、便于脚本与未来工具直接复用 |
| 过期处置 | 打标记不清理（整体覆盖时标记自然消失） | 清会话文件：重登失败时用户一无所有（用户裁定否决）；内存态标记：server 重启即失忆，过期会话重新被误判已登录 |
| 登出语义 | 仅本地清除（含 role.json） | 调官方登出端点：flow.md/research 全文无登出端点记载，不引入未验证请求（后续有实证可加） |
| 验证页载体 | 本地 HTTP 服务 + 浏览器打开 | Qt WebEngine 内嵌：GUI 未在本迭代范围，且本地页模式已被规划器与浏览器实测双重验证 |
| 验证页挑战传递 | 服务端持有 pending、页面 GET 取最新 | URL 内嵌挑战参数：刷新旧 URL 解旧题，烧重试上限（两模式互斥，取刷新安全侧） |
| 验证交互（MCP） | 异步两段式（返回 URL，后台续跑，循环在控制器） | 同步阻塞等人工解题：MCP 调用挂起数分钟不可取；client 内部循环：解题宿主在控制器层，client 循环拿不到下一张票据（拓扑不可实现） |
| 角色定位 | 自动发现 + role.json 缓存（登出与换绑登录时清） | 固定配置手填：多账号/换服需手动维护；自动发现一次调用即得 |
| aigis 分流缺省 | 两键双缺 → 页面报错 + cancelled 回传 | 按 gt4 + 缺省 riskType 硬走：无权威依据，错组件提交必被拒且烧重试上限 |
