# SR OD Main MCP Server 启动脚本
#
# 直接拉起后端主 server(``sr_od.backend.entry.server``,默认端口 24001),
# 日志重定向到 ``.debug/sr_od_mcp/main_server.log``(与 GUI / daemon start tool 同路径)。
# 开机自启快捷方式(``create_mcp_server_startup_shortcut.ps1``)以隐藏窗口调本脚本;
# 主 server 在登录会话(Session 1)内直接启动,**不经 daemon 派生**。
#
# 使用方式:
#   .\start_mcp_server.ps1              # 默认 host 127.0.0.1 / port 24001
#   .\start_mcp_server.ps1 -Port 24002  # 自定义端口

param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 24001
)

$ErrorActionPreference = "Stop"

# 本脚本位于 tools/mcp/,向上 2 级到项目根
$ProjectRoot = Split-Path -Path (Split-Path -Path $PSScriptRoot -Parent) -Parent

Write-Host "============================================================"  -ForegroundColor Cyan
Write-Host "SR OD Main MCP Server" -ForegroundColor Cyan
Write-Host "============================================================"  -ForegroundColor Cyan
Write-Host ""
Write-Host "Project Root: $ProjectRoot"
Write-Host "Listen URL: http://${HostName}:${Port}/mcp"
Write-Host ""

# 日志路径(与 GUI / daemon start tool 一致);确保目录存在
$LogPath = Join-Path $ProjectRoot ".debug\sr_od_mcp\main_server.log"
$LogDir = Split-Path $LogPath -Parent
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}
Write-Host "Log: $LogPath"
Write-Host "============================================================"  -ForegroundColor Cyan
Write-Host ""

# 切换到项目根目录
Set-Location $ProjectRoot

# --env-file 仅在 .env 是普通文件时传(目录或缺失都不传;缺失时 uv 启动失败导致自启起不来)
$EnvArg = if (Test-Path ".env" -PathType Leaf) { "--env-file .env" } else { "" }
try {
    # 经 cmd /c 重定向:stdout/stderr 合并写同一文件为原始字节(对齐
    # daemon subprocess.Popen(stdout=file, stderr=STDOUT);规避 PS 原生重定向编码问题)
    cmd /c "uv run $EnvArg python -m sr_od.backend.entry.server --host $HostName --port $Port > `"$LogPath`" 2>&1"
    # cmd /c 的非零退出码不会触发 catch(ErrorActionPreference 对原生命令无效),手动检查避免启动失败仍报成功
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Main MCP Server exited with code $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
} catch {
    Write-Host "[ERROR] Main MCP Server failed to start: $_" -ForegroundColor Red
    exit 1
}
