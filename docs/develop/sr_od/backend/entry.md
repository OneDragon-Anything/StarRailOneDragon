# 服务入口

> `SrBackendContext` 的进程入口：装配 backend + MCP / HTTP 适配器，uvicorn 运行。本地 headless 入口见下；远程 SSH daemon（管本入口启停）见 [remote-ssh.md](remote-ssh.md)。

## 运行

```shell
uv run --env-file .env python -m sr_od.backend.entry.server --host 127.0.0.1 --port 24001
```

启动流程：`SrContext()` → `SrBackendContext` → `await backend.start()`（线程池初始化，不阻塞事件循环）→ 装配 MCP（`/mcp`）+ HTTP（`/game/*`）到同一 app → `uvicorn.serve` → 关闭时 `backend.shutdown()`。

CLI：`--host`（默认 `127.0.0.1`）、`--port`（默认 **24001**）。

## 进程模型

- 独立 headless 入口，自己持有 `SrContext`；GUI 是另一个入口，二者择一（同 onedragon headless 模式）。
- 每进程独占一个 `SrContext` → `gpu_executor` / 窗口句柄天然不冲突。
- 常驻 `SrContext`，规避冷启动（OCR / YOLO 装载数秒）。

## 依赖（dev 组）

- `mcp`（FastMCP / streamable-http）、`uvicorn`（ASGI server）。

## 远程 SSH

远程 SSH 场景经 daemon 管 server 启停（daemon 已实现,详见 [remote-ssh.md](remote-ssh.md)）。**RDP / SSH 限制**:输入注入需管理员 + 交互式桌面会话;远程场景靠 daemon 绕开 Windows 会话隔离。

## 相关文档

- [architecture.md](architecture.md) — backend 生命周期
- [mcp.md](mcp.md) — 主服务器 tool
- [http.md](http.md) — HTTP 端点
