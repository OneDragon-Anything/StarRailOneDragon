"""后端服务入口：装配 backend + MCP + HTTP，由 uvicorn 运行。

本模块把 Task 4（MCP 适配器）与 Task 5（HTTP ``/game/*`` 适配器）装配到同一个
``FastMCP`` 实例上，并通过 ``streamable_http_app()`` 得到一个 Starlette app，
最终交给 uvicorn 在单进程内并行对外提供 MCP（``/mcp``）与 HTTP（``/game/*``）服务。
"""

import argparse
import asyncio
import contextlib
import logging
import sys
from typing import TYPE_CHECKING

import uvicorn

from one_dragon.utils.log_utils import (
    LoggerConfig,
    SafeTimedRotatingFileHandler,
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


def _configure_root_logger_single_channel() -> None:
    """root logger 抢先落到 ``mcp_server.log``(单一信道修)。

    根因:FastMCP.__init__(mcp 1.28)经 mcp.server.fastmcp.utilities.logging
    .configure_logging → ``logging.basicConfig(level=INFO, format='%(message)s',
    handlers=[StreamHandler(stderr)])`` 给 root 挂**裸 stderr handler**。本进程
    内所有 ``logging.getLogger(__name__)`` 型业务 logger(如
    cw_screen_plane_intel,无自有 handler,记录上传 root)会以裸格式写 stderr,
    被 daemon 重定向进 .debug/sr_od_mcp/main_server.log;而框架 logger('OneDragon',
    propagate=False)走 .log/mcp_server.log —— 同一子系统的日志按「模块抓哪个
    logger」分裂进两个文件,即哨兵观测的双信道漂移。

    修法:在 FastMCP 构造**之前**给 root 挂同文件 handler。①之后 FastMCP 的
    basicConfig 见 root 已有 handler 即 no-op(basicConfig 语义),裸 stderr
    handler 不再出现;②子 logger 记录统一落 mcp_server.log,单一信道。同文件
    双 handler(框架 logger 一个 + root 一个)的轮转互斥由 SafeTimedRotating
    FileHandler 的进程内同路径锁表保证。
    """
    root = logging.getLogger()
    if root.handlers:
        # 跳过必须可观测:前置条件若被 import 期第三方 basicConfig 破坏,
        # 静默跳过=双信道漂移无声回归(与单一信道修所治病同构)。
        logging.getLogger(__name__).warning(
            'root logger 已有 handler(%s),跳过单一信道配置——'
            '出现双信道日志漂移时先查此处',
            [type(h).__name__ for h in root.handlers])
        return   # root 已被配置(测试预置/未来启动方)时不覆盖,防重复 handler
    logging.basicConfig(
        level=logging.INFO,
        handlers=[SafeTimedRotatingFileHandler(
            get_log_file_path(default_name=MCP_SERVER_LOG_FILE_NAME),
            when='midnight', interval=1, backupCount=3,
            encoding='utf-8', delay=True)],
        format='[%(asctime)s.%(msecs)03d] [%(name)s %(filename)s %(lineno)d]'
               ' [%(levelname)s]: %(message)s',
        datefmt='%H:%M:%S',
    )


def _route_uvicorn_logs_to_mcp_log() -> None:
    """显式兜底 uvicorn logger 族的路由(不依赖 root 传播默认)。

    实证(2026-09-02 tmp 日志探针):主路径下 root 单一信道 handler +
    uvicorn logger ``propagate=True`` 默认 → 启动行经 root 落 mcp_server.log,
    不失明。脆弱点 = ``_configure_root_logger_single_channel`` 的跳过分支
    (root 已被外来 basicConfig 占位,如测试预置)——uvicorn 行随 propagate
    落外来 handler,mcp_server.log 缺启动块。本函数在该分支兜底:把同路径
    文件 handler 直接挂到 uvicorn logger 族并关 propagate(单目的地);同
    路径双 handler 的轮转互斥由 SafeTimedRotatingFileHandler 进程内锁表
    保证(见模块 docstring)。主路径(root 已挂本文件 handler)不重复挂——
    handler 叠加会让每行双写。
    """
    root_handlers = logging.getLogger().handlers
    if root_handlers and not any(
        isinstance(h, SafeTimedRotatingFileHandler) for h in root_handlers
    ):
        for name in ('uvicorn', 'uvicorn.error', 'uvicorn.access'):
            lg = logging.getLogger(name)
            if not lg.handlers:
                lg.addHandler(SafeTimedRotatingFileHandler(
                    get_log_file_path(default_name=MCP_SERVER_LOG_FILE_NAME),
                    when='midnight', interval=1, backupCount=3,
                    encoding='utf-8', delay=True))
                lg.propagate = False


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
    # 日志分流必须在 SrContext() 之前:上下文构造期间(地图数据/实例配置加载)
    # 就会打框架日志,分流未做时这些行走默认双写 —— console→main_server.log
    # (stdout 兜底日志混入框架日志,进程身份失真)与共享 log.txt(与 GUI 跨进程
    # 竞态窗口)。实证:main_server.log 各次重启头部都有一段框架日志泄漏。
    _configure_server_logging()
    # root 单一信道(见函数 docstring)也必须在 SrContext/FastMCP 构造前:
    # SrContext init 期间已有 getLogger(__name__) 型日志,晚了这段会走裸 stderr。
    _configure_root_logger_single_channel()
    # uvicorn logger 族路由兜底(见函数 docstring):主路径靠 root 传播即达,
    # 跳过分支(root 被外来 basicConfig 占位)时这里显式挂文件 handler。
    _route_uvicorn_logs_to_mcp_log()
    ctx = SrContext()
    backend = SrBackendContext(ctx)
    # 构建指纹守卫(W596/W593 方案①):启动首行记本进程运行的代码构建
    # (git 短 hash+脏标记;另落盘 .debug/sr_od_mcp/build_fingerprint.txt)。
    # 「改代码必须重启 server 才生效」——旧进程在飞时磁盘代码与行为错位,
    # 此行让「哪个构建的进程在跑」随时可 grep(局22 worn=0 定位成本实证)。
    from sr_od.backend.build_info import log_build_fingerprint
    log_build_fingerprint()
    try:
        framework_log.info("SR 后端：初始化 SrContext（线程池，不阻塞事件循环）……")
        await backend.start()
        app = create_app(backend)
        # GUI 会主动轮询 /health 和 /game/status；关闭 access log，避免日志被访问记录刷屏。
        # log_config=None 的真实因果(2026-09-02 tmp 日志探针实证):uvicorn 缺省
        # log_config 会给自己的 logger 族挂 stderr StreamHandler,每次重启的启动块
        # (Started server process/Uvicorn running 等)都写进被 daemon 重定向的
        # main_server.log —— 该文件 mtime 每次重启都会一度变新,哨兵按「两候选
        # mtime 最新」选活性信道时随之来回切换(日志信道漂移的另一写端)。
        # None = uvicorn 不自配 logging,其 logger 族保持默认 propagate=True →
        # 经 root 的 mcp_server.log 文件 handler 落盘(探针实证主路径不失明;
        # root 被外来占位的脆弱分支由 _route_uvicorn_logs_to_mcp_log 兜底),
        # 单一信道不破,main_server.log 保持 stdout 兜底职责。
        config = uvicorn.Config(app, host=host, port=port, log_level="info",
                                access_log=False, log_config=None)
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
