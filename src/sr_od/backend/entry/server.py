"""后端服务入口：装配 backend + MCP + HTTP，由 uvicorn 运行。

本模块把 Task 4（MCP 适配器）与 Task 5（HTTP ``/game/*`` 适配器）装配到同一个
``FastMCP`` 实例上，并通过 ``streamable_http_app()`` 得到一个 Starlette app，
最终交给 uvicorn 在单进程内并行对外提供 MCP（``/mcp``）与 HTTP（``/game/*``）服务。
"""

import argparse
import asyncio
import contextlib
import sys
from typing import TYPE_CHECKING

import uvicorn

from one_dragon.utils.log_utils import (
    LoggerConfig,
    configure_logger,
    get_log_file_path,
)
from one_dragon.utils.log_utils import (
    log as framework_log,
)
from sr_od.backend.backend_context import SrBackendContext
from sr_od.backend.http.routes import register_http_routes
from sr_od.backend.mcp.app import create_mcp_server
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from starlette.applications import Starlette

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 24001

# MCP server 进程的框架日志专属文件。
# 职责划分(2026-08-24 定):一个进程一个日志文件,文件即进程身份——
# GUI/调度器写 .log/log.txt,MCP server 写 .log/mcp_server.log,
# main_server.log 只留 stdout 兜底(uvicorn 启动行/print/traceback)。
# 修前:server 的框架日志默认双写(log.txt + console→main_server.log),
# 与 GUI 同写 log.txt 混进程身份,且轮转(midnight rename)双进程竞态;
# main_server.log 还会被继承 stdout fd 的直驱进程混写,不可作运行日志载体。
MCP_SERVER_LOG_FILE_NAME = 'mcp_server.log'


def _configure_server_logging() -> None:
    """把框架 logger 切到 MCP server 专属文件并关闭 console 输出。

    关 console 后,本进程框架日志不再打 stdout → 不进 main_server.log
    (它回归 daemon 重定向的 stdout 兜底职责);查 server 的 op 运行日志
    改看 .log/mcp_server.log(prompts.py 的 AI 指引同步指向)。
    """
    configure_logger(
        framework_log,
        LoggerConfig(
            log_file_path=get_log_file_path(default_name=MCP_SERVER_LOG_FILE_NAME),
            add_console_handler=False,
            propagate=False,
        ),
    )


def create_app(backend: SrBackendContext) -> "Starlette":
    """装配应用：同一 FastMCP 同时挂 MCP tool 与 ``/game/*`` custom_route。

    先创建 MCP 服务器（注册 11 个 game 工具），再把 ``/game/*`` HTTP 端点挂到
    同一实例上，最后返回 ``streamable_http_app()`` 产生的 Starlette app。
    这样 MCP ``/mcp`` 端点与 HTTP ``/game/*`` 端点同进程、同 app 共存。

    Args:
        backend: 已就绪的 ``SrBackendContext``，提供 game 切片能力。

    Returns:
        挂载好 MCP 与 ``/game/*`` 路由的 Starlette 应用。
    """
    mcp = create_mcp_server(backend)
    register_http_routes(mcp, backend)
    return mcp.streamable_http_app()


async def _serve(host: str, port: int) -> None:
    """启动后端服务：初始化 backend → 装配 app → uvicorn 运行。

    构造 ``SrContext`` 与 ``SrBackendContext``，在线程池中完成 ``SrContext`` 的
    同步初始化（``backend.start()``，不阻塞事件循环），随后装配 app 并交给
    uvicorn 持续对外服务；无论正常退出还是异常，最终都会调用 ``backend.shutdown()``
    释放资源。

    Args:
        host: 监听地址。
        port: 监听端口。
    """
    ctx = SrContext()
    backend = SrBackendContext(ctx)
    # 日志分流必须最先做:后续所有 log.* 的落点由它决定
    # (切到 mcp_server.log + 关 console;见 _configure_server_logging 注释)。
    _configure_server_logging()
    try:
        framework_log.info("SR 后端：初始化 SrContext（线程池，不阻塞事件循环）……")
        await backend.start()
        app = create_app(backend)
        # GUI 会主动轮询 /health 和 /game/status；关闭 access log，避免日志被访问记录刷屏。
        config = uvicorn.Config(app, host=host, port=port, log_level="info", access_log=False)
        server = uvicorn.Server(config)
        framework_log.info(f"SR 后端监听: http://{host}:{port}/mcp 与 /game/*")
        await server.serve()
    finally:
        await backend.shutdown()


def main() -> None:
    """命令行入口：解析参数并启动后端服务。

    通过 argparse 解析 ``--host`` / ``--port``（默认 ``127.0.0.1`` / ``24001``），
    随后 ``asyncio.run`` 驱动 ``_serve`` 完成整个生命周期。
    """
    # stdout/stderr 被 daemon 重定向到 main_server.log 时,Windows 默认用 locale(GBK)
    # 编码 → 中文(op 名/OCR)写进 UTF-8 文件变 mojibake,日志不可读。强制 UTF-8。
    for _stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            _stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description="启动 SR 后端服务（MCP + HTTP）")
    parser.add_argument("--host", default=DEFAULT_HOST, help="监听地址")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="监听端口")
    args = parser.parse_args()
    asyncio.run(_serve(args.host, args.port))


if __name__ == "__main__":
    main()
