# MCP 适配器

> 把 `SrBackendContext`（见 [architecture.md](architecture.md)）以 **MCP** 暴露给 MCP 客户端（AI 编码工具等）。MCP 是两个并行适配器之一，另一个是 HTTP（见 [http.md](http.md)）；两者共享同一 backend。

## 工具契约的单一源

本文档**不维护工具清单**——每个 tool 的名称、参数与返回契约，单一源是代码里各 tool 函数的 docstring（agent 经 MCP 工具列表直接读到，不会与实现脱节）。工具定义在 `src/sr_od/backend/mcp/`：注册入口 `app.py`，按资源分组在各 `*_tools.py`；自定义 op 工具另走 `operation_registry`（+ 流转查看 `operation_flow`）+ `run_slot._start`。

## 跨工具约定要点

- **返回契约（跨工具统一）**：成功标志键一律 `success`（bool）；运行类受理语义用 `started`（≠完成）；`stop_run` 的 `stopped` 表信号已发、`/health` 的 `ok` 表健康探测，是各自语义惯例。裸字符串 + `错误:` 前缀的返回已全部结构化（`capture_game_screen`/`close_game`/block 终态），调用方判错不再靠字符串匹配。
- `app.py` 放 MCP server 创建、基础 game tool 和总注册入口；`service_app.py` 放应用运行 tool 与自定义 op tool 工厂。
- backend 实例通过闭包注入 tool，不使用全局单例，也不让 FastMCP lifespan 管 backend 生命周期。
- `capture_game_screen` 落盘返回路径；`analyze_screen` 返回结构化 dataclass，由 FastMCP 序列化。
- `analyze_screen` 是 **OCR + 传统 OpenCV 模板/颜色匹配，非视觉大模型(VLM)**：只做已建档 screen_info 的客观命中，无视觉理解；tool docstring 已显式标注，防智能体把「分析」误解为「看懂画面」（要看懂 → 视觉大模型工具 / 视觉子 agent）。
- `analyze_screen(save_image=True)`（实时模式）把已截的内存图顺手存盘 + 回传 `screenshot_path`，供调用方喂 视觉大模型 double-check；默认 `false` 不落盘，离线模式忽略。
- `analyze_screen` 成功时返回 `vision_hint`：提醒本结果仅含 OCR + 模板匹配的部分识别，不等同完整视觉理解，需要全面判断画面时配合视觉工具 / 多模态再看（能力边界提示，[design-principles.md](design-principles.md) P14；防智能体把部分识别当画面全貌）。失败时为 `null`。
- `analyze_screen` 精准命中画面时返回 `extras`：若该画面注册了**额外识别器（recognizer）**,带该画面的结构化领域事实（画面特定结构,如货币战争备战画面的金币 / 阶段 / 阵营在场人数）;无注册识别器的画面为 `null`。识别器异常不中断本结果（`extras=null`,详见日志）。这是 per-screen 注册机制,新增画面识别器见 [screen-recognizers.md](screen-recognizers.md)。MCP 侧 dataclass 由 FastMCP 序列化、加字段自动生效;但 `analyze_screen` 的 **tool docstring 属 tool 描述变更,需客户端 `/mcp` 重连**智能体才能看到 `extras` 字段描述（字段本身不重连也在返回 JSON 里）。
- 所有运行（`open_game` / 一条龙 / 独立应用 / 自定义 op）经**同一个 `RunSlot`** 派发：op 路径（`open_game` / `run_operation`）槽自管 `start_running/execute/finish_running`（自然完成收尾不置停机中断一次性标志位），app 路径（`run_one_dragon` / `run_standalone_app`）委托 `run_application`（复用 GUI/CLI 共享入口）。`block=True` 用 `asyncio.wrap_future(future)` 阻塞 await 取结果，`block=False` 立刻返回已启动状态，后续用 `get_run_status` 查进度。
- `run_operation` 是**通用 operation 运行入口**（不框死为调试）：`op_id` 格式 `<dotted module path>.<ClassName>`（可从 `list_operations` 获取）；`args` 传构造参数,以 `cls(ctx, **args)` 烤进闭包——JSON 标量/列表/字典直接传;`@dataclass`+`from_dict` 参数及其 `Optional`/`list`/`dict` 容器形态传对应 JSON 结构（dict / list[dict]）,实例化前用 `coerce_params` 按单一规整源 `_coerce_value` 自动规整（校验 `validate_args` 干跑同一函数,行为不漂移）;`tuple`/`set` 参数传 list 自动转换;其余自定义类及其容器/Optional 形态拒绝（提示走 application）。先用 `describe_operation` 看参数 schema（`coercible=True` 的可传对应 JSON 结构）。SR 当前业务 op 暂无 `@dataclass`+`from_dict` 参数,该能力前置就绪。
- 配置修改工具（`get/set/add/delete/update_config_item` + `describe_config` + `list_app_configs`）按 `app_id` 路由到各 config 领域方法（`config_router.py`），写穿 ctx 缓存实例、写入前校验；已接入路由：`standalone_app` / `_group`（通用）、`trailblaze_power`（开拓力体力计划：`plan_list` 计划项增删 + `loop` 开关，`add` 的 `idx` 插入位置即一条龙执行顺位）与 `echo_of_war`（历战余响周本计划：列表由全部周本关卡全量补齐，不支持增删条目，用 `update_config_item` 按 `mission_id` 原位改挑战次数）。两者 `add/delete/update` 写穿当前实例缓存，下一次一条龙 run 立即生效无需重启；`mission_id` 格式「生存索引 {分类} {关卡} {区域}」，材料→关卡反查用 `dungeon_drop_const.find_missions_by_material`；后续接入同类 `@dataclass`+`from_dict` 配置时在 `config_router._build_routes` 补 `RouterEntry`（`add` 支持传 None = 该 config 不支持增条目，`update` 可选按 item_id 原位替换）。
- 配置刷新：app 路径在 `run_application` 前（槽线程内、`_start` 已赢锁后）刷新当前进程的 YAML 配置缓存，对齐 GUI 已保存设置；`list_applications` 与 `list_operations` 是只读路径，不刷新。
- `get_run_status` / `stop_run` 是统一入口：无论最近一次运行来自 op 路径还是 app 路径，都通过同一组工具查询和停止。
- 单进程内已有运行时会返回并发拒绝，避免同一个 backend 内重复操作游戏资源。
- MCP tool 不返回运行日志正文；客户端需要用 `get_run_status` 轮询是否完成，GUI 服务页负责展示日志。
- `close_game` / `click_game` / `key_tap` / `drag` / `input_text` 是独立同步操作，不走运行槽；`click_game` / `drag` 使用 1080p 游戏空间坐标。底层 click / key_tap / drag **无内置等待**，连续操作或 `capture` 前建议 sleep 等动画（见各 tool 描述的 ⚠️ 提醒）。
- `list_mcp_usage_guides` / `get_mcp_usage_guide` 把 prompt 模板以普通 tool 暴露，方便不会主动消费 MCP prompts 的客户端发现。
- `mys_*` 三工具走 `mys_tools.py` 的 `MysAccessController` 状态机（idle/awaiting_ticket，验证循环上限 3）；会话失效只打标记不清任何本机数据；凭据纪律与协议规格见 [mys.md](mys.md)（⚠️ `mys_login` 的密码经 LLM 上下文，工具描述含知情声明）。
- 理念：MCP 只做感知 / 操作，编码 / 调试交给 AI（[design-principles.md](design-principles.md)）。

## Instructions

`FastMCP(name, instructions=...)` 传 server 级 `instructions`，握手时返回；客户端**通常注入** system prompt（协议 Optional/MAY，Claude Code 会注入；非协议强制）。放两边共通的操作哲学（保持精炼）：工具分类（观察/操作）、操作三件套（`analyze_screen` → 操作 → 等 ~1s 后验）、实机约束（`pc_alt`）、出错查 log、安全边界。

## 引导内容三通道

引导内容分三条通道，分工互补（可见性均为客户端行为，非协议强制——spec 用 Optional/MAY）：

| 通道 | 智能体可见性 | 内容 |
|---|---|---|
| `instructions` | 客户端**通常注入** system prompt（协议 Optional/MAY；Claude Code 会） | 共通操作哲学（上节） |
| `prompts`（`@mcp.prompt()`） | 由客户端决定；Claude Code 是 slash 命令，智能体平时不自动看到 | 按场景剧本（见下） |
| help tool（`list_mcp_usage_guides` / `get_mcp_usage_guide`） | 通常可见（客户端一般暴露 tools） | 同 prompts 模板，给智能体 `--help` 入口 |

`prompts` 协议设计给人手动选，智能体平时不自动看到 → 同份模板再做成 tool 镜像补；但 tool 要智能体「想到去调」，故核心操作哲学放 `instructions`（通常注入，最贴近常驻）。guide item 带 `mode`（`user`/`dev`）：user 项（跑龙/独立应用）也有对应 prompt，dev 项（`sr_dev_validate_op`：op 实操验证 / 战斗 op 边界）只走 tool。模式差异不进 instructions（server 级全局、不支持运行时切；且两套会膨胀违背精炼）。

## Prompts

| MCP prompt | 用途 |
|---|---|
| `sr_check_status` | 引导 AI 查询运行状态、窗口状态与当前画面分析结果。 |
| `sr_run_one_dragon` | 引导 AI 按当前配置启动一条龙，并轮询 `get_run_status`。 |
| `sr_run_standalone_app(app_id=None)` | 引导 AI 列出应用、选择独立应用并启动运行。 |

要点：

- prompt 只描述调用顺序，不直接执行工具；实际执行仍由 MCP 客户端选择 tool。
- `sr_run_standalone_app` 支持传入 `app_id`，为空时提示使用 GUI「应用运行」当前选中项。
- 运行类 prompt 默认使用 `block=False` 启动，再轮询 `get_run_status`，便于客户端在长耗时任务中持续反馈状态。
- 部分 MCP 客户端不会主动展示 prompts；这时可让 agent 先调用 `list_mcp_usage_guides`，再调用 `get_mcp_usage_guide` 读取同一份模板。

## 传输与端口

- 传输：streamable-http。
- MCP 端点：`/mcp`。
- 默认本机端口：`24001`。
- MCP URL：`http://127.0.0.1:24001/mcp`。
- 健康检查：`http://127.0.0.1:24001/health`。

## 接入 MCP 客户端

主 server 是标准 streamable-http,任何 MCP 客户端都可挂载。
先通过 GUI「开发工具 -> MCP 服务」或命令行启动本机 server，再在你的 MCP 客户端新增服务器（按所用工具，见下）。

### DSH MCP 配置

项目根 `.dsh/mcp.servers.yml`（workspace-mcp 插件按 cwd 自动加载，保存热生效；不入库，每人本地建）：

```yaml
servers:
  sr_od:
    transport: streamable-http
    url: http://127.0.0.1:24001/mcp
```

### Claude Code MCP 配置

```shell
claude mcp add --transport http sr_od http://127.0.0.1:24001/mcp
```

### Codex GUI MCP 配置

| 字段 | 填写 |
|---|---|
| 名称 | `sr_od` |
| 类型 | `Streamable HTTP` |
| Bearer 令牌环境变量 | 留空 |
| URL | `http://127.0.0.1:24001/mcp` |
| 标头 | 留空；如果界面要求 JSON，填 `{}` |
| 启动命令 | 留空 |
| 参数 | 留空 |

要点：

- 当前服务只实现 streamable HTTP，不是 STDIO server；Codex 中不要选 STDIO。
- 本机接口默认无鉴权，因此不需要 Bearer token 或额外 headers。
- MCP 客户端只负责连接已启动的 HTTP MCP server；启动 / 停止 / 重启由 GUI「MCP 服务」页或命令行负责。
- 命令行启动可用 `uv run python -m sr_od.backend.entry.server --host 127.0.0.1 --port 24001`；如果项目根目录存在 `.env`，也可使用 `uv run --env-file .env python -m sr_od.backend.entry.server --host 127.0.0.1 --port 24001`。

## 开机自启(主 server)

主 server 可在登录后自动启动（Session 1 内直接拉起，**不经 daemon 派生**），与 [daemon 开机自启](remote-ssh.md#开机自启) 相互独立、可共存：

- 启动脚本：`tools/mcp/start_mcp_server.ps1`（默认 host 127.0.0.1 / port 24001，日志写 `.debug/sr_od_mcp/main_server.log`，与 GUI / daemon start tool 同路径）。
- 装自启快捷方式：`.\tools\mcp\create_mcp_server_startup_shortcut.ps1` —— 在 Startup 文件夹建 `SR OD MCP Server.lnk`，登录后自动调上面脚本（隐藏窗口）。卸载即删该 `.lnk`。
- 幂等说明：本快捷方式与 daemon 自启快捷方式各管各的；daemon 的 `start_sr_od_mcp_server` 先按命令行检测进程已存在则跳过，不会重复拉起 / 端口冲突。

## 路线图（尚未实现）

- 更多 game 感知 / 交互 tool：原 `identify_current_screen` → `analyze_screen`、`click_at_position` → `click_game`、`press_key` → `key_tap`、`drag_to` → `drag` 均已实现；后续按需补 `scroll` 等。
- 更完整的 AI 操作范式，例如失败恢复、实例切换与多步巡检。

## 相关文档

- [architecture.md](architecture.md) - backend 方法定义
- [http.md](http.md) - 并行的 HTTP 适配器
- [design-principles.md](design-principles.md) - MCP tool 设计规范
- [entry.md](entry.md) - 服务入口
