# mys（米游社账号接入：sr_od 封装与 MCP 工具）

> 正本文档：与 `src/sr_od/mys/`、`src/sr_od/backend/mcp/mys_tools.py` 实现保持一致。通用层（登录/客户端/会话）见 [one_dragon/mys README](../../../one_dragon/mys/README.md)；协议规格见 [application/account_profile/miyoushe-api-flow.md](../application/account_profile/miyoushe-api-flow.md)。

## sr_od/mys（崩铁特有封装）

`SrMysClient(client: MysClient, store: SessionStore)`——组合通用 client，提供崩铁角色列表：

- `get_characters() -> list[SrCharacter]`（轻口径，`hkrpg/api/index` 一次调用）：
  1. **过期短路**：会话已标记过期 → 直接 `MysSessionExpired`（不发注定失败的请求）
  2. 角色定位：`role.json` 缓存（`{role_id, server}`）→ 无缓存则 `ROLE_LIST_URL?game_biz=hkrpg_cn` 自动发现（is_chosen 优先、role_id 字符串化）并写缓存
  3. `hkrpg/api/index` → `data.avatar_list` 映射 `SrCharacter`（**冻结字段集**：id/name/level/rarity/rank/element/**element_cn**/base_type/**base_type_cn**/equip 光锥摘要——`element_cn`/`base_type_cn` 为接口层直出的属性/命途中文名，消费方零查表；icon 等大字段不透传）
- `get_characters_detail() -> list[CharacterDetail]`（全量明细，**`hkrpg/api/avatar/info?need_wiki=true`** 一次调用——注意与 index 是两个端点：index 只出轻名册 12 字段/角色，遗器/星魂/行迹/面板明细只在 avatar/info；`need_wiki=true` 是响应内五词典 property_info/equip_wiki/relic_wiki/recommend_property/relic_properties 的来源开关）：
  1. 过期短路同上；角色定位同上（role.json）
  2. `hkrpg/api/avatar/info` → `data.avatar_list` 映射 `CharacterDetail`（**冻结字段集**：`id/name/level/rarity/rank/element/element_cn/base_type/base_type_cn/equip/relics[]/ornaments[]/ranks[]/skills[]/properties[]`）：
     - `SrRelic`（隧洞遗器与位面饰品同构）：`name/pos/pos_cn(头部|手部|躯干|脚部|位面球|连结绳)/rarity/level/main: SrPropertyEntry/subs: list[SrPropertyEntry]`；`SrPropertyEntry = {name_cn, value, times 强化次数}`
     - `SrRank`：`pos(星魂序号 1-6，勿与遗器部位码混淆)/name/desc/is_unlocked`
     - `SrSkill`：`name(普攻|战技|终结技|天赋|秘技|额外能力|属性加成|欢愉技)/level/is_activated/stages: list[SrSkillStage{name, desc, level}]`
     - `SrPanelProperty`：`name_cn/base/add/final`（字符串数值，百分比带 %）
     - 词条/面板中文名经**三层查表**：响应原生 `property_info` 词典（优先，取 `property_name_relic` 防模板占位符）→ `sr_codes.py` 快照（56 码全集/命途 9/元素 7/部位 6）→ 「未知属性(pt=N)」兜底不抛异常（详见 `sr_codes.py`）

## MCP 工具（register_mys_tools，`backend/mcp/mys_tools.py`）

`MysAccessController`（模块级单例，进程级）：装配 SessionStore/DeviceIdentity/MysClient/AigisVerifier（requests 与 webbrowser 真实实装由控制器=运行入口传入）；状态机 `idle`/`awaiting_ticket`；验证循环上限 3（client 单轮，循环在控制器）；并发语义：awaiting 期二次 login 复用 URL 且新账密即弃、awaiting 期数据请求不裸打、awaiting 期登出取消验证且迟到票据丢弃、票据 payload.session_id 与当前挑战再比对一道。

| MCP tool | 行为 | 返回（统一信封 `{status, message, data}`） |
|---|---|---|
| `mys_login(username, password)` | 密码登录；验证触发时起本地验证页并返回 URL（后台续跑，循环≤3） | `success` / `already_logged_in` / `verification_required`（含 URL）/ `error`（-3208 密码过多、-3235 账号风险等即停） |
| `mys_logout()` | 清 session.json 与 role.json、留 device.json；幂等；awaiting 期调用取消验证 | `success` |
| `mys_get_characters()` | 过期短路 → 角色发现 → index → 冻结字段集映射 | `success` + 角色数组（含 element_cn/base_type_cn 中文名）／`session_expired`／`error`（1034 → 专属文案） |
| `mys_get_roster_detail()` | 过期短路 → 角色发现 → avatar/info(need_wiki=true) → 全量明细映射 | `success` + 全角色明细数组（遗器六件套词条/位面饰品/星魂/行迹/属性面板，均中文名）／`session_expired`／`error` |

- ⚠️ `mys_login` 描述含知情声明：密码会作为工具参数传入大模型上下文，由使用者自行决定（框架层不记录工具入参，实测 mcp 1.28.1 源码）
- **会话失效不清任何本机数据**：只写 expired 标记 + 提醒重登；数据接口触发 1034 时返回专属错误（验证链后续迭代实现）
- 会话目录：`config/<实例>/mys/`（session.json/role.json/device.json，gitignore 内）；**会话备份恢复规程 = 先停 MCP server 再离线恢复文件**（进程内滚动写会覆盖恢复文件，实测教训）

## 相关文档

- 通用层：[one_dragon/mys README](../../../one_dragon/mys/README.md)
- 协议规格：[application/account_profile/miyoushe-api-flow.md](../application/account_profile/miyoushe-api-flow.md)
- 登录验证分支规格与跨项目对照：[application/account_profile/login-verification-research.md](../application/account_profile/login-verification-research.md)
- 迭代过程：`application/account_profile/changes/mys-account-mcp/`（账号接入）、`application/account_profile/changes/mys-roster-detail/`（角色明细与中文字段）
