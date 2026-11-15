# MCP 玩家/开发双模式（mcp-mode-split）迭代设计

## 0. 元信息

- 迭代目标：MCP server 支持玩家/开发两种运行模式，单端点由启动参数决定，默认玩家模式——玩家模式下 agent 拿 MCP 工具 + skill 即可替玩家完成**全部游戏内容**（含一条龙），开发模式额外暴露自动化维护类工具。
- 需求来源：用户直接需求（2026-11 对话）。三轮拍板：①单端点 + 启动参数决定（双端点方案否决）；②玩家模式画像 =「玩家用 mcp+skill 完成所有游戏内容，人永不直接操作工具」，工具面按此划分而非按读写性质划分；③开发专属名单定稿 5 件（`update_game_config` / `get_screen_detail` / `list_screen_names` 经用户裁定划回玩家侧）。
- 状态：已落地（正本 mcp.md §1 / entry.md / remote-ssh.md / architecture.md 已同步更新；测试锁差集契约）
- 文档清单：（单文档方案，无详设——本文即完整设计）

## 1. 问题与动机

### 1.1 现状症状

- `create_mcp_server` 一条路注册全部 43 个工具，所有 MCP 消费者（玩家向 agent、开发向 agent）看到同一份全量清单。
- 玩家场景下，画面建档维护、录屏、op 节点流转图等维护类工具是纯噪音：占模型上下文（每个工具描述都占 token），且诱导玩家向 agent 误用（如误改 screen_info）。
- 引导内容层已有 user/dev 分流雏形（`prompts.py` guide item 的 `mode` 字段），但工具层从未分流——分流语义两层不一致。

### 1.2 两类消费者画像（划分基准）

- **玩家模式**：普通玩家对着 AI 助手说「帮我跑日常」「这期抽谁」「把开拓力改成刷周本」。AI 用 MCP 工具 + skill 知识包办一切：跑一条龙、执行游戏内操作（装备/养成/消费类 skill 的落地载体是 op）、查游戏知识与账号练度、调整一条龙使用配置。**人不直接操作工具，工具面按「agent 能否替玩家办完全部游戏内容」划，宁多勿缺。**
- **开发模式**：自动化项目的维护者（画面建档、op 编排调试、录屏取证）。在玩家面之上额外暴露维护类工具。

### 1.3 根因归层

**约定层**：MCP 工具暴露面从未定义「按消费者分流」的约定——注册只有「全部注册」一条路径，工具描述里的「观察类/操作类」标注是副作用口径，不是受众口径。

### 1.4 解决到哪；明确不解决

- 解决：启动参数选模式、按名单分流工具暴露面、guide 项随模式过滤、daemon 传递模式。
- 明确不解决：
  - 不做鉴权/权限系统（本机 127.0.0.1 监听，模式是暴露面分流不是安全边界）；
  - 不做运行时切换 / `notifications/tools/list_changed`（工具清单是连接级快照，运行时切换需全体客户端重拉，且玩家/开发会话并存时互相污染——用户裁定单端点，切换=重启+重连）；
  - 不动 HTTP `/game/*`（GUI 是全功能管理面，模式只作用于 MCP 工具暴露面）；
  - 不动 instructions（跨工具口径，模式无关）。

## 2. 方案

### 2.1 系统级变化

| 位置 | 变化 |
|---|---|
| `src/sr_od/backend/mcp/app.py` | `create_mcp_server(backend, mode='player')`；模块级 `DEV_ONLY_TOOLS` 名单；player 模式全量注册后按名单 `remove_tool` |
| `src/sr_od/backend/mcp/prompts.py` | `register_prompt_tools(mcp, mode)`：玩家模式 `list_mcp_usage_guides` 只回 `mode=='user'` 项 |
| `src/sr_od/backend/entry/server.py` | argparse 加 `--mode {player,dev}`（默认 player）；启动日志记 mode |
| `tools/mcp/daemon/sr_od_daemon.py` | `start` 加 mode 参数（默认 player）；`restart` 沿用当前进程 mode（解析命令行，同 port 沿用做法），显式传参则覆盖；`status` 显示 mode |
| `sr-od-test/test/sr_od/backend/test_mcp_app.py` | `_mcp_with_backend` 显式 dev 模式（保住全量工具行为测试）；新增模式契约测试 |
| `docs/develop/sr_od/backend/mcp.md` / `entry.md` / `remote-ssh.md` | 收尾阶段更新（正本） |

### 2.2 模式定义与工具归属

模式词表沿用 guide item 已有的 `user`/`dev` 语义，启动参数取值 `player` / `dev`。

**`DEV_ONLY_TOOLS`（开发专属，5 件）**——全部是「维护自动化产品」的工具，与「完成游戏内容」无关：

| 工具 | 归属理由 |
|---|---|
| `create_screen` / `upsert_screen_area` / `delete_screen_area` | 画面建档**写**操作：screen_info 是识别资产，建档是开发工序（od-dev-screen-onboarding），玩家 agent 不维护建档 |
| `describe_operation_flow` | op 节点流转图：读 op 内部编排结构，改 op 才需要；与「用 op」的 `list/describe/run_operation` 边界见 §3 |
| `record_screen` | 录屏取证，docstring 本就标 dev-only，且依赖 dev 组的 imageio-ffmpeg |

**玩家面 = 其余全部 38 件**。归属曾争议、最终定玩家侧的关键项（记录裁定依据，防回潮）：

| 工具 | 玩家侧理由 |
|---|---|
| `list_operations` / `describe_operation` / `run_operation` | 游戏内容操作（装备遗器、升级行迹、买月卡、抽卡）的载体就是 op；消费/养成类 skill 把 agent 路由到 op。「用 op」是玩家能力，不是调试特权 |
| 配置七件全量（`get/set/describe/add/delete/update_config_item` + `list_app_configs`） | 「把开拓力计划改成刷XX」「周本打几次」是玩家使用一条龙的一部分，读写都要 |
| `get_screen_detail` / `list_screen_names` | 只读；玩家 agent 导航失败时查「从当前画面能 goto 到哪」（用户裁定划回玩家） |
| `update_game_config` | 切语言是玩家级需求（用户裁定划回玩家） |
| 手动操作族（`click_game` / `key_tap` / `drag` / `input_text` / `goto_screen`） | 消费/抽卡类 skill 执行的落地工具 |
| `mys_*` 五件 | 账号练度评估是配队养成决策的数据入口（`mys_login` 密码过模型上下文的知情声明已在工具描述） |

**增量约定**：新工具**默认进玩家面**；维护类工具必须显式登记进 `DEV_ONLY_TOOLS`。方向取「默认玩家 + 显式登记开发」而非反向，因为玩家面缺工具 = 玩家任务办不成（伤主路径），玩家面多一个维护工具 = 噪音（伤洁癖）——主路径优先。名单契约由测试锁死（§2.6）。

### 2.3 注册与过滤实现

`app.py`：

```python
MCP_MODE_PLAYER = 'player'
MCP_MODE_DEV = 'dev'
# 开发专属工具名单(单一源):玩家模式不暴露;新维护类工具必须登记于此
DEV_ONLY_TOOLS: frozenset[str] = frozenset({
    'create_screen', 'upsert_screen_area', 'delete_screen_area',
    'describe_operation_flow', 'record_screen',
})

def create_mcp_server(backend, mode: str = MCP_MODE_PLAYER) -> FastMCP:
    mcp = FastMCP(name, instructions=...)
    ...全部注册(现状代码零改动)...
    register_prompt_tools(mcp, mode)
    if mode == MCP_MODE_PLAYER:
        registered = set(mcp._tool_manager._tools.keys())
        for name in DEV_ONLY_TOOLS & registered:   # 交集:名单含未注册名不炸启动
            mcp.remove_tool(name)
    return mcp
```

- **先全量注册再按名单移除**，不做条件注册：注册代码几十处零改动；名单是唯一分流依据（单一源）；测试可锁「dev 集 − player 集 == 名单」这个精确契约。
- `remove_tool` 对未注册名抛 ToolError（mcp 1.28.1 源码确认），故取交集后再删——名单登记了尚不存在的工具名时不阻断启动。
- mode 参数校验：非法值 ValueError（fail-fast，不静默回退玩家）。

### 2.4 启动参数与 daemon

- `server.py`：`--mode {player,dev}`，默认 `player`；`_serve(host, port, mode)` 透传 `create_app(backend, mode)`。启动日志加一行 mode（`mcp_server.log` 可 grep 当前进程模式，同 build_fingerprint 的可观测思路）。
- daemon：
  - `start_sr_od_mcp_server(port, mode='player')`——命令行追加 `--mode`；
  - `_get_server_mode(proc)`：从进程命令行解析 `--mode`（镜像 `_get_server_port`；缺省视为 player）；
  - `restart_sr_od_mcp_server(mode=None)`：None = 沿用当前进程解析到的 mode（对齐 port 沿用做法），显式传参覆盖；
  - `get_sr_od_mcp_server_status`：状态行加当前 mode。
  - `find_sr_od_mcp_server_process` 按 `-m sr_od.backend.entry.server` 匹配命令行，`--mode` 追加不影响进程识别。
- GUI「MCP 服务」页 / 开机自启脚本 `start_mcp_server.ps1`：启动命令不带 `--mode` → 天然默认玩家。开发者用 dev 模式时经 daemon start（mode='dev'）拉起或重启时传参。
- 切换模式 = 重启 server + MCP 客户端重连（本机既有操作习惯，`.dsh/mcp.servers.yml` 的 reconnect 记录即此流程）。

### 2.5 guide / prompts 按模式过滤

- `register_prompt_tools(mcp, mode)`：
  - `list_mcp_usage_guides`：player 模式只返回 `mode=='user'` 的 guide 项（`sr_dev_validate_op` 等开发指南不进玩家目录）；
  - `get_mcp_usage_guide`：player 模式对 dev 项名按「未知指南」处理（不渲染内容）。
- `register_prompts` 不动——本就只注册 user 向 prompt。
- `render_instructions` 不动——跨工具全局口径，模式无关。

### 2.6 测试计划

`test_mcp_app.py` 适配 + 新增：

1. `_mcp_with_backend` 改为显式 `mode='dev'` 创建——既有 40+ 条行为测试在 dev 全量面上跑，零语义变化。
2. **名单契约测试（核心）**：`dev 集 − player 集 == DEV_ONLY_TOOLS`——锁「名单=实际差集」：新维护工具忘登记 → 差集变大 → 红；误登记玩家工具 → 差集变小 → 红。
3. 玩家面关键抽样：player 集含 `run_operation` / `set_config` / `add_config_item` / `update_game_config` / `get_screen_detail` / `list_screen_names` / `mys_get_characters`（锁裁定不回潮）。
4. guide 过滤：player 模式 `list_mcp_usage_guides` 项的 `mode` 全为 `user`；dev 模式含 dev 项。
5. `create_mcp_server` 非法 mode 抛 ValueError。

daemon 是 `tools/` 脚本，无测试镜像（仓库现状惯例），行为靠 docstring + 手动验证。

## 3. 关键取舍

- **单端点启动参数 vs 同进程双端点**：双端点（`/mcp` 玩家 + `/dev/mcp` 开发，零重启切换、两模式并存）技术更优，被用户裁定否决——取单端点：模式是进程级状态、心智简单，切换=重启+重连是本机既有习惯，玩家/开发不同时在线是可接受前提。设计上留的路：模式只在 `create_mcp_server` 一处分流，未来若要双端点，同进程起两个不同 mode 的 FastMCP 即可复用全部逻辑。
- **默认玩家**：发布形态的安全默认——任何新环境（GUI 启动、自启脚本、他人按文档手动起）不带参数即玩家面，开发能力只在显式要求时出现。
- **先全量注册再移除 vs 条件注册**：见 §2.3——注册代码零改动 + 名单单一源 + 差集可锁。
- **`describe_operation_flow` 归开发而 `list/describe/run_operation` 归玩家**：边界是「用 op」vs「看 op 内部编排」。跑 op、看参数是玩家 agent 执行游戏内容；节点流转图服务于改 op 的编排审查（AGENTS.md「改 op 前先看图」是开发纪律）。
- **`get_screen_detail` / `list_screen_names` / `update_game_config` 划回玩家**：用户裁定。三者皆非建档写操作——前两者是只读导航辅助，后者是玩家级设置（切语言）。
- **guide 过滤与工具过滤同一词汇表**：guide item 已有 `mode: user/dev` 字段（引导层分流先于工具层存在），本迭代工具层沿用同一对概念，两层分流语义对齐，不另造词。
