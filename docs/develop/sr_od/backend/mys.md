# mys（米游社账号接入：sr_od 封装与 MCP 工具）

> 正本文档：与 `src/sr_od/mys/`、`src/sr_od/backend/mcp/mys_tools.py` 实现保持一致。通用层（登录/客户端/会话）见 [one_dragon/mys README](../../../one_dragon/mys/README.md)；协议规格见 [application/account_profile/miyoushe-api-flow.md](../application/account_profile/miyoushe-api-flow.md)。

## sr_od/mys（崩铁特有封装）

`HsrMysClient(client: MysClient, store: SessionStore)`——组合通用 client，提供崩铁角色列表：

- `get_characters() -> list[HsrCharacter]`：
  1. **过期短路**：会话已标记过期 → 直接 `MysSessionExpired`（不发注定失败的请求）
  2. 角色定位：`role.json` 缓存（`{role_id, server}`）→ 无缓存则 `ROLE_LIST_URL?game_biz=hkrpg_cn` 自动发现（is_chosen 优先、role_id 字符串化）并写缓存
  3. `hkrpg/api/index` → `data.avatar_list` 映射 `HsrCharacter`（**冻结字段集**：id/name/level/rarity/rank/element/base_type/equip 光锥摘要；icon 等大字段不透传）

## MCP 工具（register_mys_tools，`backend/mcp/mys_tools.py`）

`MysAccessController`（模块级单例，进程级）：装配 SessionStore/DeviceIdentity/MysClient/AigisVerifier（requests 与 webbrowser 真实实装由控制器=运行入口传入）；状态机 `idle`/`awaiting_ticket`；验证循环上限 3（client 单轮，循环在控制器）；并发语义：awaiting 期二次 login 复用 URL 且新账密即弃、awaiting 期数据请求不裸打、awaiting 期登出取消验证且迟到票据丢弃、票据 payload.session_id 与当前挑战再比对一道。

| MCP tool | 行为 | 返回（统一信封 `{status, message, data}`） |
|---|---|---|
| `mys_login(username, password)` | 密码登录；验证触发时起本地验证页并返回 URL（后台续跑，循环≤3） | `success` / `already_logged_in` / `verification_required`（含 URL）/ `error`（-3208 密码过多、-3235 账号风险等即停） |
| `mys_logout()` | 清 session.json 与 role.json、留 device.json；幂等；awaiting 期调用取消验证 | `success` |
| `mys_get_characters()` | 过期短路 → 角色发现 → index → 冻结字段集映射 | `success` + 角色数组 / `session_expired` / `error`（1034 → 专属文案） |

- ⚠️ `mys_login` 描述含知情声明：密码会作为工具参数传入大模型上下文，由使用者自行决定（框架层不记录工具入参，实测 mcp 1.28.1 源码）
- **会话失效不清任何本机数据**：只写 expired 标记 + 提醒重登；数据接口触发 1034 时返回专属错误（验证链后续迭代实现）
- 会话目录：`config/<实例>/mys/`（session.json/role.json/device.json，gitignore 内）；**会话备份恢复规程 = 先停 MCP server 再离线恢复文件**（进程内滚动写会覆盖恢复文件，实测教训）

## 相关文档

- 通用层：[one_dragon/mys README](../../../one_dragon/mys/README.md)
- 协议规格：[application/account_profile/miyoushe-api-flow.md](../application/account_profile/miyoushe-api-flow.md)
- 登录验证分支规格与跨项目对照：[application/account_profile/login-verification-research.md](../application/account_profile/login-verification-research.md)
- 迭代过程：`application/account_profile/changes/mys-account-mcp/`
