# 米游社账号接入 MCP 三工具 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check`（仅本阶段改动文件）全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/ -m "not slow"` 相关子集）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面；
- 触碰 `src/sr_od/backend/**` 的阶段：提交后需重启项目 MCP server 方生效（项目 AGENTS.md §6）；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

### 3.1 one_dragon/mys 通用基础件

**范围**：`mys_const.py`（端点/salt/公钥/头/白名单常量）、`mys_signing.py`（登录 DS、game_record DS2 含 URL 编码、RSA 加密）、`mys_http.py`（HttpSendResult/HttpSend 契约、header 助手、RequestsHttpSend 实装）、`mys_session.py`（SessionStore 全原语 + MysApiError/MysSessionExpired + 会话失效码常量 + session.json 字段 schema）、`mys_device.py`（设备身份 + getFp 四判据与降级）及 `__init__.py`（默认不暴露模块）；对应单测。**边界**：不含 MysClient、aigis 分支、验证页、任何 sr_od 文件。
**设计依据**：design.md §2.2（mys_const/mys_signing/mys_http/mys_session/mys_device 五小节）；协议出处 = miyoushe-api-flow.md §2/§3/§4
**文件面**：`src/one_dragon/mys/**`、`sr-od-test/test/one_dragon/mys/**`
**依赖**：无
**优先级建议**：5
**完成判据**：
- 签名函数 t/r 注入式单测：期望 DS 值以 **fixture 固化进测试仓**（测试向量自造、期望值人工推演固定——登录 DS 按 flow.md §2.3 口径、DS2 按 §4.1 口径；禁止测试运行时读本机易失文件）——含 q 的 URL 编码断言（保留字符参数用例）；
- HttpSendResult 多值 Set-Cookie 契约单测：同名字头两条不合并、header_get 大小写不敏感；RequestsHttpSend 以本机回环临时 HTTP 服务（port=0 + 短超时护栏）验证多值 Set-Cookie 取全，并断言 redirect 禁用与 25s 超时口径；
- session.json 字段级 schema 断言：save_cookies 滚动更新保留 expired 标记；save_session_full 整体覆盖且产物无 expired 键；mark_expired 合并写入且**文件缺失时幂等无操作**；
- SessionStore 原子写/读取/清空（clear 删 session.json 与 role.json、保留 device.json）、device 损坏重生成留痕单测（落盘走 tmp_path，零真实副作用）；
- getFp 四判据单测（HTTP 非 ok / retcode≠0 / 内层 code≠200 / fp 正则不符各一例）与冷却降级不带头单测；
- 会话失效码常量 `SESSION_EXPIRED_RETCODES = {10001, -100}` 存在且被引用（定案修订只改此常量）；
- 完成前常规检查（本节首节）。
**验收凭据形式**：`sr-od-test/test/one_dragon/mys/` 下单测全绿（test_mys_signing.py / test_mys_http.py / test_mys_session.py / test_mys_device.py）。

### 3.2 MysClient 正常路径 + 登出

**范围**：`mys_client.py` 构造（store/device/http_send 三参必填）、login 成功路径（save_session_full 整体覆盖落盘 + role.json 清除）、非验证码分诊（-3208/-3235/其它）、`request()`（绝对 URL/相对路径双形态 + DS2 + 白名单 + 1034 裸错误语义 + 会话失效映射）、`logout()`（清 session.json 与 role.json、留 device.json）；异常映射。**边界**：aigis 验证分支与验证页（3.3）、hkrpg 封装与 MCP（3.4）。
**设计依据**：design.md §2.2 mys_client 小节 + §2.5 契约 3/7 + §2.6
**文件面**：`src/one_dragon/mys/mys_client.py`、`sr-od-test/test/one_dragon/mys/test_mys_client.py`
**依赖**：3.1
**优先级建议**：5
**完成判据**：
- 构造缺任一必填参数 → TypeError（无默认路径存在性断言）；
- mock http_send 剧本单测：登录成功——Set-Cookie **登录响应层名单（10 项）** 以 fixture 固化断言入罐；落盘断言为 `save_session_full` 形态（**产物无 expired 键**、cookies 与登录响应一致）；acw_tc 等滚动件以「会话滚动后 jar ⊇ 登录名单 + 滚动件」第二层断言（登录响应下发与滚动后集合是两个集合，分别对账）；登录成功同时清除 role.json（登录态换绑强制重新发现）；
- 先 `mark_expired` 再登录成功 → 产物无 expired 键（标记随整体覆盖消失）；
- `-3208`/`-3235`/其它非 0 → `MysApiError` 且**不落盘不清文件**；
- `request()`：相对路径拼基座断言、绝对 URL 直用断言、白名单外主机拒绝、DS2 按 q 排序 + URL 编码断言、`SESSION_EXPIRED_RETCODES` 各码 → `MysSessionExpired`、`1034` → `MysApiError(1034)` 裸错误、响应 Set-Cookie 滚动入罐且**保留 expired 标记**；
- `logout()`：session.json 与 role.json 删除、device.json 保留、内存罐清空、幂等；
- **密码与 cookie 不出现在任何落盘文件、异常文本与错误信封**（断言）；
- 完成前常规检查。
**验收凭据形式**：test_mys_client.py 全绿。

### 3.3 aigis 验证单轮分支 + 本地验证页

**范围**：`mys_client.py` 的验证分诊（双条件）、aigis 双层解析、票据组装（v4 补字段 / gt3 原值）、`x-rpc-aigis` 回传头、**单轮**重发与结果观察（`complete_verification` 含成功路径的 Set-Cookie 收取与落盘）；`aigis_verifier.py` 本地验证页服务（pending 挑战服务端持有模式）；对应单测。**边界**：验证循环与状态机（3.4 控制器）、hkrpg 封装与 MCP 注册（3.4）、人工解题的真实触发（3.5 实机）。
**设计依据**：design.md §2.2 mys_client「complete_verification」与 aigis_verifier 小节 + §2.5 契约 2/4；协议出处 = login-verification-research.md §10.3（互证）/§10.4-2（分流缺省）/§10.5-3（Moonward 工程手法）
**文件面**：`src/one_dragon/mys/mys_client.py`、`src/one_dragon/mys/aigis_verifier.py`、`sr-od-test/test/one_dragon/mys/test_mys_client_aigis.py`、`sr-od-test/test/one_dragon/mys/test_aigis_verifier.py`
**依赖**：3.2
**优先级建议**：6
**完成判据**：
- 分诊双条件单测：码值 -3101、或 aigis 头非空（码值不同）两剧本都进验证分支；message 文案不参与分诊；
- 双层解析：data 为字符串 / 为对象两 fixture 均解出 challenge；
- 回传头字节级断言：`{session_id};{base64(JSON(票据))}`；v4 剧本断言补 `captcha_id`+`userInfo`，gt3 剧本断言三元组原值无 `|jordan`；
- **单轮语义**：`complete_verification` 剧本单测——重发 `retcode 0` → `ok` 且 **Set-Cookie 全量入罐 + `save_session_full` 整体覆盖落盘（无 expired 键）**；重发 `-3101`/aigis 头非空 → `need_verification` + **新 challenge**；`-3102`/`-3202` 携带新 aigis 头 → `need_verification` + 新 challenge；`-3102` 未携带新 aigis 头 → 自动补发裸 loginByPassword 取新挑战后 `need_verification`；**断言 complete_verification 内部不存在循环**（每剧本带票据重发恰一次）；
- 缺省分支：两键双缺 fixture → 页面回传 `{cancelled: true}`（控制器复位 idle）且不发起重发；
- verifier：`start` 绑定随机空闲端口（port=0）返回 `http://127.0.0.1:<port>/verify`（**URL 不含挑战参数**）；页面经 `GET /challenge` 取当前 pending 挑战；`start` 二次调用（新挑战）后 `GET /challenge` 返回新挑战（刷新取新题语义）；`POST /ticket` 回环解析 `{session_id, ticket}`；`POST /ticket` 的 `payload.session_id` 与 pending 不一致 → 409 丢弃；`sec-fetch-site`/Origin 校验（不合格 403）；双缺挑战 → 页面回传 `{cancelled: true}`；`close` 释放端口（落盘走 tmp_path，open_browser 注入记录器断言不弹真实浏览器）；
- 完成前常规检查。
**验收凭据形式**：test_mys_client_aigis.py / test_aigis_verifier.py 全绿。

### 3.4 sr_od/mys 封装 + MCP 三工具 + 控制器

**范围**：`hsr_mys_client.py`（过期短路 + 角色自动发现 + index 角色列表映射 + index 快照 fixture）；`mys_tools.py` 的 `MysAccessController`（装配、状态机 idle/awaiting_ticket、验证循环上限 3、并发语义：二次登录复用 URL/awaiting 期数据请求/awaiting 期登出取消/迟到票据丢弃/超时不改状态）与三工具 + `register_mys_tools` + `app.py` 挂载；`mys_login` 描述知情声明；RequestsHttpSend 与 open_browser 装配；工具入参日志脱敏核查。**边界**：GUI、avatar/info 全练度、正本更新（末阶段）；存量平铺测试文件不搬动。
**设计依据**：design.md §2.3/§2.4（含状态机与并发语义）+ §2.5 契约 4/5 + §2.6 知情声明原文
**文件面**：`src/sr_od/mys/**`、`src/sr_od/backend/mcp/mys_tools.py`、`src/sr_od/backend/mcp/app.py`、`sr-od-test/test/sr_od/mys/test_hsr_mys_client.py`、`sr-od-test/test/sr_od/backend/mcp/test_mys_tools.py`、`sr-od-test/test/fixtures/`（index 快照 fixture；新建镜像子目录 `test/sr_od/backend/mcp/`，`src/sr_od/backend/mcp/` 与测试树的既有平铺文件保持既有布局不动）
**依赖**：3.3
**优先级建议**：6
**完成判据**：
- get_characters 单测：过期短路（is_expired 直接 MysSessionExpired 不发请求）→ 角色自动发现（绝对 URL 形态、is_chosen 优先 + role.json 缓存、server 取缓存值、role_id 字符串化）→ index 快照 fixture 映射出 `HsrCharacter` 冻结字段集（契约 §2.5-5，字段增删即判据失败）；
- **控制器状态机单测**（序列化剧本）：`mys_login` → verification_required（attempt=1）；票据回传 `ok` → idle + 会话落盘（save_session_full）；票据回传 `need_verification(新挑战)` → 同端口新挑战 + attempt 递增（≤3）；attempt≥3 → idle + verifier 关闭 + error 留档；`cancelled` → idle + verifier 关闭；`awaiting_ticket` 期间二次 `mys_login` → 复用现存 URL 且新账密即弃（不产生第二次登录请求）；`awaiting_ticket` 期间 `mys_get_characters` → verification_required 信封不裸打请求；`awaiting_ticket` 期间 `mys_logout` → 清会话 + idle + verifier 关闭 + **迟到票据被丢弃**（不静默重建会话）；
- **过期标记序列单测**：`mys_get_characters` 收到 `MysSessionExpired` → session.json **保留**（仅 expired 标记写入）且 role.json **保留** → 信封 session_expired；此后 `mys_login` **不再返回 already_logged_in**（走正常登录路径）；登录失败（如 -3208）旧文件原样保留；登录成功 `save_session_full` 整体覆盖、标记消失；
- 装配断言：控制器构造的 MysClient/DeviceIdentity 持有传入的 RequestsHttpSend 实例与同一 SessionStore 实例（无默认路径、同实例同锁）；
- 三工具信封单测：`success` / `already_logged_in` / `verification_required`（含 URL）/ `session_expired` / `error` 五态（含 `MysApiError(1034)` → 专属文案）；
- `mys_login` 工具 description 包含知情声明关键句（「密码会作为工具参数传入大模型上下文」）——行为断言（经注册函数取 description 文本）；
- 核查 FastMCP 框架层对工具入参的日志行为并按需脱敏，结论写入阶段交付说明；
- 完成前常规检查（含 MCP server 重启生效项）。
**验收凭据形式**：单测全绿 + description 文本断言 + 状态机序列单测 + 脱敏核查结论。

### 3.5 实机端到端验收

**范围**：经 MCP 工具真实登录（用户在场提供凭据，知情声明已确认）→ 角色列表 → 登出全链；实测暴露的缺陷修复。**边界**：不做 avatar/info、不做重复压测、不故意触发风控（1034/aigis 真实触发属顺带观察，不主动构造）。
**设计依据**：design.md §2.4/§2.6/§2.8（端点形态与会话生命周期行）；对照基准 = miyoushe-api-flow.md §2（登录响应 cookie 名单 10 项）与 §8.2（校对记录）
**文件面**：`src/one_dragon/mys/**`、`src/sr_od/**`（仅实测缺陷修复）；`config/0N/mys/**`（运行产物）
**依赖**：3.1-3.4
**优先级建议**：8
**完成判据**：
- `mys_login` 真实成功（如触发验证，经本地验证页人工通过后成功）→ `config/0N/mys/session.json` 落盘（无 expired 键），登录响应 cookie 名单对照 flow.md §2 **登录响应层 10 项口径**；
- `mys_get_characters` 返回 ≥64 角色，字段集与契约一致（对照 2026-11-03 index 实测口径）；
- `mys_logout` 后 `mys_get_characters` 返回 `session_expired`；
- **观察点**：①空罐/登出后打 game_record 的实际返回码（定案 `SESSION_EXPIRED_RETCODES` 常量）；②1034 是否出现（出现则按裸错误文案确认用户可读）；③**会话时效**：记录登录时刻与会话失效时刻（web 形态无续期链，失效时间即密码重登周期依据）；
- 实测响应行为与规格不符时：以实证为准修订 login-verification-research.md 对应节，并回改实现；
- 完成前常规检查。
**验收凭据形式**：MCP 工具调用记录 + session.json 核对 + 角色数对照 + 观察点结论记录。

### 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：3.1-3.5 全部完成。
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `sr-od-test/README.md`（测试目录口径定案：新增镜像子目录 `test/sr_od/mys/`、`test/sr_od/backend/mcp/` 不带 `__init__.py` 的取舍说明）← 3.4 交付后的验收移交项
- `docs/develop/one_dragon/mys/README.md`（新增正本：包结构/模块职责/配置文件布局/使用方式）← 3.1-3.3
- `docs/develop/sr_od/backend/mys.md`（新增正本：sr_od/mys 封装说明与接口）← 3.4
- `docs/develop/sr_od/backend/mcp.md`（工具清单节追加三工具）← 3.4
- `docs/develop/sr_od/application/account_profile/miyoushe-api-flow.md` §2.5（**cookie 名单两层表述修订**：登录响应下发 10 项、acw_tc 系会话滚动件）← 3.2/3.5
- `docs/develop/sr_od/application/account_profile/miyoushe-api-flow.md` §8.2（追加自家实现的往返校对记录；有出入则同步修订规格）← 3.5
