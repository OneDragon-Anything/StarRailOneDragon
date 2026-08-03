"""SR OD 后端管理 daemon。

轻量级管理服务器,长期运行在游戏本机 Session 1(交互式桌面、管理员权限),
用于管理主 MCP server(``sr_od.backend.entry.server``,默认端口 24001)的启停。

远程 SSH 场景下,Claude Code 挂载本 daemon(默认端口 24000),经它的 tool
间接 start/stop/restart/status 主 server——主 server 由 daemon 在 Session 1
拉起、继承管理员权限,才能操作游戏(绕开 SSH 的 Session 0 隔离)。
"""

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil
import uvicorn
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SR OD Server Manage")

# 配置
# 本文件位于 tools/mcp/daemon/，向上 3 级到项目根
PROJECT_ROOT = Path(__file__).resolve().parents[3]
# 主 MCP server 默认端口（start tool 的 port 参数默认值；区别于 daemon 自身监听端口）
MCP_SERVER_PORT = 24001
# 本 daemon 自身监听 host/port(__main__ 启动时回填,restart_daemon 自重启沿用)
# 注:不在此处加类型注解,否则 __main__ 里 `global` 声明会 SyntaxError(annotated name can't be global)
_DAEMON_HOST = '127.0.0.1'
_DAEMON_PORT = 24000

# start/stop 主 server 的互斥锁:防「检查进程/端口 → Popen」TOCTOU 竞态(并发调用起重复进程/端口冲突)
_start_lock = threading.Lock()


def find_sr_od_mcp_server_process() -> psutil.Process | None:
    """按命令行匹配查找运行中的主 MCP server 进程。

    通过全局进程枚举按命令行特征(``sr_od.backend.entry.server``)匹配,
    不依赖易失的 ``Popen`` handle,故 daemon 自身重启后仍能找回主 server。

    Returns:
        主 server 进程;未找到时返回 ``None``。
    """
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            cmdline = proc.info['cmdline']
            if not cmdline:
                continue
            for i, arg in enumerate(cmdline):
                if arg == '-m' and i + 1 < len(cmdline) and cmdline[i + 1] == 'sr_od.backend.entry.server':
                    return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def _get_server_port(proc: psutil.Process) -> int | None:
    """从主 server 进程命令行解析 ``--port``。

    Args:
        proc: 主 server 进程。

    Returns:
        解析到的端口;解析失败或无法读取时返回 ``None``。
    """
    try:
        cmdline = proc.cmdline()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None
    for i, arg in enumerate(cmdline):
        if arg == '--port' and i + 1 < len(cmdline):
            try:
                return int(cmdline[i + 1])
            except ValueError:
                return None
    return None


def is_port_in_use(port: int) -> bool:
    """检查端口是否处于监听状态。"""
    for conn in psutil.net_connections(kind='inet'):
        if conn.laddr and conn.laddr.port == port and conn.status == 'LISTEN':
            return True
    return False


@mcp.tool()
def start_sr_od_mcp_server(port: int = MCP_SERVER_PORT) -> str:
    """启动主 MCP server(游戏操作),在 Session 1 拉起。

    Args:
        port: 主 server 监听端口,默认 24001。

    Returns:
        启动结果信息。
    """
    with _start_lock:
        existing_proc = find_sr_od_mcp_server_process()
        if existing_proc:
            return f"[OK] 主 MCP server 已在运行 (PID: {existing_proc.pid})"

        if is_port_in_use(port):
            return f"[WARN] 端口 {port} 已被占用，可能有其他程序在使用"

        try:
            # 输出重定向到日志文件:长驻 server 若用 PIPE 且不持续消费,buffer 满会阻塞子进程
            log_path = PROJECT_ROOT / '.debug' / 'sr_od_mcp' / 'main_server.log'
            log_path.parent.mkdir(parents=True, exist_ok=True)
            cmd = ['uv', 'run']
            # .env 存在才追加 --env-file（对齐 GUI 的 mcp_service_interface._server_command，
            # 避免新人未建 .env 时 uv run 报 "No such file or directory"）
            if (PROJECT_ROOT / '.env').is_file():
                cmd.extend(['--env-file', '.env'])
            cmd.extend(['python', '-m', 'sr_od.backend.entry.server', '--port', str(port)])
            # with 关闭父进程的日志句柄;子进程已继承 fd 继续写日志,避免失败/异常路径泄漏 fd
            with open(log_path, 'w', encoding='utf-8') as log_file:
                process = subprocess.Popen(
                    cmd,
                    cwd=str(PROJECT_ROOT),
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                )

            time.sleep(2)

            if process.poll() is None:
                return f"[SUCCESS] 主 MCP server 启动成功 (PID: {process.pid})\n端口: {port}\n日志: {log_path}"
            return f"[ERROR] 启动失败(返回码 {process.returncode})\n日志: {log_path}"

        except Exception as e:
            return f"[ERROR] 启动异常: {e}"


@mcp.tool()
def stop_sr_od_mcp_server() -> str:
    """停止主 MCP server(含其子进程)。"""
    proc = find_sr_od_mcp_server_process()

    if not proc:
        if is_port_in_use(MCP_SERVER_PORT):
            return f"[WARN] 未找到主 MCP server 进程，但端口 {MCP_SERVER_PORT} 被占用"
        return "[OK] 主 MCP server 未运行"

    try:
        children = proc.children(recursive=True)
        for child in children:
            child.terminate()
        proc.terminate()

        gone, alive = psutil.wait_procs([proc] + children, timeout=5)

        if alive:
            for p in alive:
                p.kill()

        return f"[SUCCESS] 主 MCP server 已停止 (PID: {proc.pid})"

    except psutil.NoSuchProcess:
        return "[OK] 主 MCP server 已停止"
    except Exception as e:
        return f"[ERROR] 停止失败: {e}"


@mcp.tool()
def restart_sr_od_mcp_server() -> str:
    """重启主 MCP server(先停再启,沿用原监听端口)。"""
    # 停止前读取当前端口,重启后沿用,避免非默认端口被静默改回 24001
    proc = find_sr_od_mcp_server_process()
    port = _get_server_port(proc) if proc else None

    stop_result = stop_sr_od_mcp_server()

    if "[ERROR]" in stop_result:
        return f"[ERROR] 重启失败 - 停止阶段出错:\n{stop_result}"

    time.sleep(2)

    start_result = (
        start_sr_od_mcp_server(port) if port is not None
        else start_sr_od_mcp_server()
    )

    return f"[RESTART]\n{stop_result}\n{start_result}"


@mcp.tool()
def get_sr_od_mcp_server_status() -> str:
    """查看主 MCP server 运行状态。"""
    proc = find_sr_od_mcp_server_process()

    if not proc:
        port_status = "占用" if is_port_in_use(MCP_SERVER_PORT) else "空闲"
        return f"[STATUS] 主 MCP server 未运行\n端口 {MCP_SERVER_PORT}: {port_status}"

    try:
        with proc.oneshot():
            pid = proc.pid
            create_time = time.ctime(proc.create_time())
            cpu_percent = proc.cpu_percent(interval=0.1)
            memory_info = proc.memory_info()
            children = len(proc.children(recursive=True))
            server_port = _get_server_port(proc)

            return f"""[STATUS] 主 MCP server 运行中
PID: {pid}
启动时间: {create_time}
CPU 使用: {cpu_percent}%
内存使用: {memory_info.rss / 1024 / 1024:.2f} MB
子进程数: {children}
端口: {server_port if server_port is not None else '未知(见进程命令行)'}"""

    except Exception as e:
        return f"[STATUS] 主 MCP server 运行中 (PID: {proc.pid})\n[ERROR] 无法获取详细信息: {e}"


# 自重启协调器(detached 子进程跑,不随旧 daemon 退出而死)。
# 只杀 daemon 本身(不 /T → 不波及主 server 子进程,主 server 被 orphan 后继续跑)→
# 等 daemon 端口释放 → 用同样命令拉起新 daemon。
_RESTARTER_SCRIPT = """\
import time, sys, os, socket, subprocess
delay = float(sys.argv[1]); pid = int(sys.argv[2])
host = sys.argv[3]; port = int(sys.argv[4]); script = sys.argv[5]; cwd = sys.argv[6]
time.sleep(delay)
try:
    os.system('taskkill /PID {} /F'.format(pid))   # 只杀 daemon 本身,不带 /T(不波及主 server 子进程)
except Exception:
    pass
for _ in range(60):                                # 等 daemon 端口释放
    s = socket.socket()
    try:
        s.bind((host, port)); s.close(); break
    except OSError:
        s.close(); time.sleep(0.5)
subprocess.Popen([sys.executable, script, '--host', host, '--port', str(port)],
                 cwd=cwd, creationflags=0x00000008)  # DETACHED_PROCESS
"""


@mcp.tool()
def restart_daemon(delay: float = 2.0) -> str:
    """重启本 daemon(自重启)。改了 daemon 自身代码(``sr_od_daemon.py``)后用本 tool 加载新代码。

    后台 detached restarter → 延迟 ``delay`` 秒(让本响应先回)→ 杀旧 daemon(只杀本 pid,
    不波及主 server 子进程,主 server 被 orphan 后继续跑)→ 等 daemon 端口释放 → 用同样命令拉起新 daemon。

    ⚠️ 首次使用前需手动重启 daemon 一次(本 tool 属新代码,旧 daemon 没有);之后改 daemon 代码
    即可用本 tool 自重启。若失败(新进程没起来),需手动重启 daemon。重启期间客户端到本 daemon 的连接会短暂断开。

    Args:
        delay: restarter 杀旧进程前的等待(秒)。

    Returns:
        重启计划(host/port/旧 pid)。
    """
    host = _DAEMON_HOST
    port = _DAEMON_PORT
    script = str(Path(__file__))
    cwd = str(PROJECT_ROOT)
    pid = os.getpid()
    creationflags = (getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
                     | getattr(subprocess, 'DETACHED_PROCESS', 0)
                     | getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    subprocess.Popen([sys.executable, '-c', _RESTARTER_SCRIPT,
                      str(delay), str(pid), host, str(port), script, cwd],
                     cwd=cwd, creationflags=creationflags,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return (f"[RESTART] daemon 计划自重启(host={host}, port={port}, old_pid={pid})\n"
            f"restarter 将在 {delay}s 后杀旧进程并拉起新 daemon。本 daemon 连接会短暂断开,属正常。")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='SR OD 后端管理 daemon')
    parser.add_argument('--host', default='127.0.0.1', help='监听地址')
    parser.add_argument('--port', type=int, default=24000, help='监听端口')
    args = parser.parse_args()
    # 回填本 daemon 监听 host/port(模块级赋值天然改全局,无需 global;restart_daemon 自重启沿用)
    _DAEMON_HOST = args.host
    _DAEMON_PORT = args.port

    print("=" * 60)
    print("SR OD 后端管理 daemon")
    print("=" * 60)
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"\n管理服务器地址: http://{args.host}:{args.port}/mcp")
    print("\n可用工具:")
    print("  - start_sr_od_mcp_server: 启动主 MCP server")
    print("  - stop_sr_od_mcp_server: 停止主 MCP server")
    print("  - restart_sr_od_mcp_server: 重启主 MCP server")
    print("  - get_sr_od_mcp_server_status: 查看主 MCP server 状态")
    print("\n" + "=" * 60)

    app = mcp.streamable_http_app()
    uvicorn.run(app, host=args.host, port=args.port)
