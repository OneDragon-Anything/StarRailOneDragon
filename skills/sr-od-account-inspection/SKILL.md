---
name: sr-od-account-inspection
description: 需要查询崩坏:星穹铁道账号的米游社数据（角色列表：等级/稀有度/星魂数/命途/光锥摘要；全量明细：遗器词条/星魂/行迹/属性面板）时用——通过 mys MCP 四工具（mys_login/mys_logout/mys_get_characters/mys_get_roster_detail）直连米游社官方接口，秒级返回。凡是「查角色」「看账号」「拉账号数据」「看遗器」都用。英文：inspect Star Rail account via mys MCP tools。
---

# 崩铁账号查询（米游社 MCP 四工具）

账号数据的唯一路线：`sr_od` MCP server 上的四个工具（`backend/mcp/mys_tools.py`），直连米游社官方接口。

## 前置

- MCP server（sr_od）已启动；改动 `src/sr_od/backend/**` 后需重启 server 才生效
- 会话与设备文件在 `config/<实例>/mys/`（session.json = cookie 会话、role.json = 角色定位缓存、device.json = 设备身份；gitignore 内，不入库）

## 工具

### 1. `mys_login(username, password)` —— 密码登录

⚠️ **知情声明（调用前必须向使用者转达）**：密码作为工具参数会传入大模型上下文，存在泄露风险，是否继续由使用者自行决定。

返回统一信封 `{status, message, data}`，按 status 处置：

| status | 含义 | 处置 |
|---|---|---|
| `success` | 登录成功（session.json 落盘，密码不落盘） | 直接用 `mys_get_characters` |
| `already_logged_in` | 会话有效 | 直接用 `mys_get_characters` |
| `verification_required` | 极验触发 | 打开 `data.url` 本地验证页，**人工**完成滑块/点选（最多 3 次），后台自动续跑；完成后用 `mys_get_characters` 验证 |
| `session_expired` | 旧会话已标记过期 | 直接重试 `mys_login` 即可 |
| `error` | -3208 密码错误过多 / -3235 账号风险等 | **即停勿重试**，按 message 提示使用者 |

### 2. `mys_get_characters()` —— 角色列表（轻口径）

- 返回 `success` + 角色数组：`id` / `name` / `level` / `rarity` / `rank`(星魂数) / `element` / `element_cn`(属性中文) / `base_type`(命途码) / `base_type_cn`(命途中文) / `equip`(光锥摘要 name/level/rank/rarity)
- 秒级返回；会话过期时返回 `session_expired`（**不清除任何本机数据**，只提示重新登录）

### 3. `mys_get_roster_detail()` —— 全角色名册明细（遗器/星魂/行迹/面板）

- 返回 `success` + 每名角色的完整明细（数据量大，64 角色全量一次返回）：
  - `relics[]`(隧洞遗器) / `ornaments[]`(位面饰品)：`name` / `pos_cn`(部位中文) / `rarity` / `level` / `main`(主词条 name_cn+value+times 强化次数) / `subs[]`(副词条同构)
  - `ranks[]` 星魂：`pos` / `name` / `desc` / `is_unlocked`
  - `skills[]` 行迹：`name`(普攻/战技/…/欢愉技) / `level` / `is_activated` / `stages[]`(name/desc/level)
  - `properties[]` 属性面板：`name_cn` / `base` / `add` / `final`
- 载荷较大（数百 KB），只要角色概况时优先用 `mys_get_characters`；会话过期语义同上

### 4. `mys_logout()` —— 登出

- 清除本机 `session.json` 与 `role.json`（保留 `device.json`）；幂等

## 会话管理

- 会话持久化在 `config/<实例>/mys/session.json`，每次调用滚动续期；失效时**只打过期标记，不清除任何数据文件**，重新登录即恢复
- **备份/恢复会话文件必须先停 MCP server 再离线操作**——进程存活期间恢复的文件会被下一次调用的滚动续存覆盖（实测教训，详见 `docs/develop/sr_od/backend/mys.md`）

## 边界

- 本版本只提供角色列表；全练度明细（星魂/遗器/词条，`avatar/info`）与数据接口 1034 风控验证链为后续迭代
- 游戏内逐格扫描路线已移除（效率原因，2026-11-04）；`config/idx/` 下的旧档案文件为历史留存

## 相关文档（实现与协议规格，按需查阅）

- `docs/develop/sr_od/backend/mys.md` —— sr_od 封装与三工具正本
- `docs/develop/one_dragon/mys/README.md` —— 通用登录客户端正本（会话/验证/红线全量说明）
- `docs/develop/sr_od/application/account_profile/miyoushe-api-flow.md` —— 米游社协议规格（端点/签名/验证分支）
