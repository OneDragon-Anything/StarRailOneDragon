# one_dragon/mys（米游社账号通用客户端）

> 正本文档：与 `src/one_dragon/mys/` 实现保持一致。协议权威出处 = [sr_od/application/account_profile/miyoushe-api-flow.md](../sr_od/application/account_profile/miyoushe-api-flow.md)（端点/签名/头集/验证分支逐项规格）；本文件只写「怎么用、怎么存、哪些红线」。

## 包定位

米哈游通行证（国服）账号接入的**跨游戏通用层**：密码登录、登出、设备身份、DS 签名、cookie 罐、aigis 人机验证分支、会话持久化、通用 mys 请求客户端。不包含任何游戏专属接口（各游戏在各自包里组合本 client，如 `sr_od/mys/`）。

## 模块与职责

| 模块 | 职责 |
|---|---|
| `mys_const.py` | 端点/两个 salt/RSA 公钥/头集/主机白名单常量（零逻辑，出处 flow.md §2/§3/§4） |
| `mys_signing.py` | `ds_login`（三段式 salt&t&r）/ `ds_record`（DS2，q 排序 + URL 编码）/ `rsa_encrypt`；t/r 可注入供测试向量 |
| `mys_http.py` | `HttpSend`/`HttpSendResult` 契约（headers 保序保重复）+ `header_get` 助手 + `RequestsHttpSend`（redirect 禁用、超时 25s、Set-Cookie 走 raw 全量收取） |
| `mys_session.py` | `SessionStore`（session.json/role.json/device.json 三文件原语，原子写 + 0600 尽力 + 全入口持锁）+ `MysApiError`/`MysSessionExpired` + `SESSION_EXPIRED_RETCODES = {10001, -100}` |
| `mys_device.py` | `DeviceIdentity(store, http_send)`：device_id 持久化（正常路径严禁轮换；文件损坏重生成留痕为唯一例外）、getFp（24h 缓存/失败 30min 冷却/冷却期降级不带头/四判据校验） |
| `mys_client.py` | `MysClient(store, device, http_send)`：`login`/`complete_verification`（均**单轮语义**）/`logout`/`request`（绝对 URL 或 RECORD 相对路径，DS2，白名单）；aigis 单轮分诊内嵌 |
| `aigis_verifier.py` | `AigisVerifier(open_browser=None)`：本地验证页（127.0.0.1 随机端口、gt4+gt3 双脚本、服务端持有 pending 挑战、GET /challenge 取最新、POST /ticket 回传票据/取消、sec-fetch-site+session_id 配对双防线） |

## 使用方式（最小组合）

```python
store = SessionStore(mys_dir, threading.Lock())
device = DeviceIdentity(store, RequestsHttpSend())
client = MysClient(store, device, RequestsHttpSend())

result = client.login(username, password)      # 'ok' 或 'need_verification'+challenge
# need_verification → AigisVerifier.start(challenge) 弹本地验证页，人工过验后
result = client.complete_verification(challenge, ticket)   # 仍可能 need_verification(新挑战)——循环与上限归调用方（≤3）
data = client.request('hkrpg/api/index', {'role_id': …, 'server': …})   # 或绝对 URL（白名单内）
client.logout()                                # 仅本地清除（清 session.json/role.json，留 device.json）
```

- **http_send/store/device 必填无默认**：requests 真实实装由运行入口传入（测试注入假实现）——零副作用纪律。
- `login`/`complete_verification` 成功路径统一：Set-Cookie 全量入罐 + `save_session_full` 整体覆盖落盘。

## 会话文件布局与语义（`config/<实例>/mys/`）

| 文件 | 内容 | 生命周期 |
|---|---|---|
| `session.json` | `{schema_version, saved_at, expired?, cookies}` | 登录/验证成功整体覆盖；接口响应滚动续存（保留 expired 标记）；**会话失效只打 expired 标记不清文件** |
| `role.json` | `{role_id, server}` 角色定位缓存 | 登出清除；登录成功清除（换绑强制重发现）；会话失效**保留** |
| `device.json` | `{schema_version, device_id}` | 永久保留（设备信誉锚；文件损坏重生成留痕为唯一例外） |

- **会话失效不清数据**：过期只打标记 + 提醒重登——重登失败时旧文件原样保留（用户裁定 2026-11-04）。
- 已标记过期的会话：`login` 自动跳过「已登录」判定走正常登录；成功覆盖后标记消失。

## 会话备份恢复操作规程（实测教训）

**恢复 session.json 备份必须先停使用该会话的进程（如 MCP server）再离线恢复文件**——进程内存罐在登出后已清空，进程存活期间恢复的文件会被下一次响应的滚动续存（内存罐内容）覆盖（2026-11-04 实测：恢复文件未停进程 → 被 2 个滚动件覆盖丢失 10 cookie）。恢复后重启进程，罐从文件重新播种即恢复可用。

## 纪律红线

- 密码仅在登录调用栈内存中存在，不落盘不写日志；
- cookie 是凭据：不进日志/异常文本/对外返回；落盘文件不入 git（config 实例目录已 gitignore）；
- 不绕人机验证、不接打码平台；验证重试上限即停；
- 票据不是凭据——登录信息只从成功登录的 Set-Cookie 取。
