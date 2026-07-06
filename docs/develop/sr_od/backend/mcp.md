# MCP 适配器

> 把 `SrBackendContext`（见 [architecture.md](architecture.md)）以 **MCP** 暴露给 MCP 客户端（AI 编码工具等）。MCP 是两个并行适配器之一，另一个是 HTTP（见 [http.md](http.md)）；两者共享同一 backend。

## 工具

11 个 `@mcp.tool`，各自委托一个 backend 方法：

| MCP tool | 委托 | 返回 |
|---|---|---|
| `check_game_window` | `backend.check_window()` | 状态文本（`str`） |
| `capture_game_screen` | `backend.capture()` | 截图绝对路径（落盘 `.debug/sr_od_mcp/screenshot/`） |
| `analyze_screen` | `backend.analyze()` | `AnalyzeScreenResult`（结构化 JSON；FastMCP 据返回注解自动生成 output schema） |
| `upsert_screen_area(screen_name, area_name, pc_rect, ...)` | `backend.upsert_screen_area()` | `{success, screen_name, area_name, action, area_count, error}`（新增/更新 area，写 yml + reload） |
| `delete_screen_area(screen_name, area_name)` | `backend.delete_screen_area()` | `{success, ...`（按名删 area；不存在则 `success=False`） |
| `open_game(enter=True, block=True)` | `backend.start_run('mcp', op_factory)`（`enter=False`→`OpenGame`，`enter=True`→`OpenAndEnterGame`） | `block=True`：结果文本（`str`，按 enter 分「成功打开游戏(未登录)」/「成功打开并进入星穹铁道游戏」）；`block=False`：已启动 JSON；并发拒绝时返错误 JSON |
| `click_game(x, y, press_time=0)` | `backend.click_game()` | `{success, x, y, in_window}`（坐标不在窗口内 → `in_window=False`） |
| `input_text(text, use_clipboard=None)` | `backend.input_text()` | `{success, method, masked_text}`（`use_clipboard=None` 跟 `game_config.type_input_way`；返回脱敏文本） |
| `get_run_status` | `backend.query_status()` | `RunStatusResult`（运行中返当前节点/重试；终态返结果/失败定位） |
| `stop_run` | `backend.stop()` | `{"stopped": bool, ...}`（仅表信号已发出，过渡期 `get_run_status` 仍显示 running） |
| `close_game` | `backend.close_game()` | 文本（`str`，已发送关闭信号；controller 吞异常，用 `check_game_window` 验证） |

要点：

- backend 实例**注入**（闭包捕获），不用全局单例，也不用 FastMCP lifespan 管 backend 生命周期（由入口管）。
- `capture_game_screen` 落盘返路径,客户端读取该图片;`analyze_screen` 返结构化 dataclass,FastMCP 序列化为带嵌套 `OcrText` 的 JSON。
- 长耗时 operation（`open_game`）经 backend 共享 `RunSlot` 派发：`block=True` 用 `asyncio.wrap_future(future)` 阻塞 await 取结果，`block=False` 立刻返回已启动状态，后续用 `get_run_status` 查进度。`enter=False` 只打开+等窗口就绪（停「打开游戏」ready 态，不登录），供调用方分步驱动登录流程。MCP 与 HTTP（见 [http.md](http.md)）**对称暴露**这套运行态三件套（[design-principles.md](design-principles.md) P11）。
- **中断安全**：`block=True` 时若调用方取消 await，中断的只是本次 await，底层 `RunSlot._run` 继续执行、结果入槽，可用 `get_run_status` 查到终态。
- 单跑道：已有运行在进行时 `open_game` 返回并发拒绝（含 `source` + 提示），保证同进程独占资源不冲突。
- `close_game` / `click_game` / `input_text` **独立同步**（不走 RunSlot）：镜像 `check_window` / `analyze` 同步模式，直调 backend 切片；与 `open_game`（走 RunSlot 长耗时）非对称（耗时量级不同）。`click_game` 用 **1080p 游戏空间坐标**（同源 screen_info `pc_rect`，控制器自动缩放到真实屏幕）。
- 理念：MCP 只做感知 / 操作，编码 / 调试交给 AI（[design-principles.md](design-principles.md)）。

## 传输与端口

- 传输 streamable-http，端点 `/mcp`，与 HTTP `/game/*` 同进程共存。
- 默认端口 **24001**。

## 接入 MCP 客户端

主 server 是标准 streamable-http,任何 MCP 客户端都可挂载。以 Claude Code 为例:

```shell
claude mcp add --transport http sr_od http://127.0.0.1:24001/mcp
```

注册后重启客户端生效。

## 路线图

- 原 `identify_current_screen` → 已由 `analyze_screen` 实现；`click_at_position` → 已由 `click_game` 实现。后续按需补 `press_key`（单键，如 Esc/Enter）、`scroll` / `drag_to` 等更多交互 tool。

## 相关文档

- [architecture.md](architecture.md) — backend 方法定义
- [http.md](http.md) — 并行的 HTTP 适配器
- [design-principles.md](design-principles.md) — MCP tool 设计规范（P1–P12）
- [entry.md](entry.md) — 服务入口
