# SR OD Main MCP Server 启动脚本
#
# 拉起后端主 server(``sr_od.backend.entry.server``,默认端口 24001),
# 日志重定向到 ``.log/stdout.log``(与 GUI / daemon start tool 同路径)。
# 开机自启快捷方式(``create_mcp_server_startup_shortcut.ps1``)以隐藏窗口调本脚本;
# 主 server 在登录会话(Session 1)内直接启动,**不经 daemon 派生**。
#
# 使用方式:
#   .\start_mcp_server.ps1                       # 默认 host 127.0.0.1 / port 24001 / dev 模式
#   .\start_mcp_server.ps1 -Mode player          # 玩家模式工具面
#   .\start_mcp_server.ps1 -Port 24002           # 自定义端口
#   .\start_mcp_server.ps1 -NoWait               # 不等待就绪标志,发出即返回
#
# 行为(用户裁定:先确定没东西在跑,再重启):
#   1. 预检清理:发现旧 server 进程(命令行含 entry.server)→ 全部停止,等端口释放;
#      15 秒未释放 → 中止启动(避免双实例抢端口/抢日志文件)
#   2. 分离启动:server 挂独立进程树(隐藏窗口),本脚本**启动后即退出**,不挂前台
#   3. 就绪等待:轮询日志至出现「Uvicorn running」(冷启动 30~60 秒,上限 90 秒);
#      出现绑定失败/异常退出标志则提前报错
# 退出码:0 = 已就绪(或 -NoWait 已发出);1 = 清理失败;2 = 就绪等待超时。
# 注意:重启会杀死运行中的 op——重启前先经 MCP `get_run_status` 确认无运行中 run。

param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 24001,
    [ValidateSet("player", "dev")]
    [string]$Mode = "dev",
    [switch]$NoWait
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
$LogPath = Join-Path $ProjectRoot ".log\stdout.log"
$LogDir = Split-Path $LogPath -Parent
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}
Write-Host "Log: $LogPath"
Write-Host "============================================================"  -ForegroundColor Cyan
Write-Host ""

Set-Location $ProjectRoot

# ── 0. 并发单飞锁:两会话同时跑本脚本时,彼时对方的 server 进程尚未发出, ──
# 预检互相看不到 → 双双放行 → 双实例(实测事故形态)。锁文件独占打开
# (FileShare.None)保证同一时刻只有一个脚本实例走「清理+启动」全流程,后来者排队。
$LockPath = Join-Path $ProjectRoot ".log\mcp_start.lock"
$lockStream = $null
$lockDeadline = (Get-Date).AddSeconds(150)
while ($true) {
    try {
        $lockStream = [System.IO.File]::Open($LockPath, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
        break
    } catch [System.IO.IOException] {
        if ((Get-Date) -gt $lockDeadline) {
            Write-Host "[lock] 150 秒内未取得启动锁(另一脚本实例长时间占锁),中止启动" -ForegroundColor Red
            exit 1
        }
        Start-Sleep -Seconds 3
    }
}
Write-Host "[lock] 启动锁已取得"
try {

# ── 1. 预检清理:停止旧 server 进程,等端口释放(双实例会抢端口+互锁日志文件) ──
function Get-ServerProcesses {
    Get-CimInstance Win32_Process -Filter "Name='python.exe' or Name='uv.exe'" |
        Where-Object { $_.CommandLine -match 'entry\.server' }
}

$oldProcs = Get-ServerProcesses
if ($oldProcs) {
    Write-Host "[pre] 发现旧 server 进程,停止:" -ForegroundColor Yellow
    foreach ($p in $oldProcs) {
        Write-Host "    pid=$($p.ProcessId) ($($p.Name))"
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    # 端口释放判定(进程退出≠端口立即可绑,TIME_WAIT/句柄释放有延迟)
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 500
        $listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        $alive = Get-ServerProcesses
        if (-not $listening -and -not $alive) { break }
    }
    $listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listening -or (Get-ServerProcesses)) {
        Write-Host "[pre] 旧 server 15 秒未退净(端口 $Port 仍占用),中止启动" -ForegroundColor Red
        exit 1
    }
    Write-Host "[pre] 旧进程已清,端口 $Port 已释放"
} else {
    Write-Host "[pre] 无旧 server 进程"
}
Write-Host ""

# ── 2. 分离启动:server 挂独立进程树,本脚本启动后即退出 ──
# 经 cmd /c 重定向:stdout/stderr 合并写字节流
# (对齐 daemon subprocess.Popen(stdout=file, stderr=STDOUT);规避 PS 原生重定向编码问题)
$EnvArg = if (Test-Path ".env" -PathType Leaf) { "--env-file .env" } else { "" }
$CmdLine = "uv run $EnvArg python -m sr_od.backend.entry.server --host $HostName --port $Port --mode $Mode > `"$LogPath`" 2>&1"
Start-Process -FilePath "cmd.exe" -ArgumentList "/c $CmdLine" `
    -WorkingDirectory $ProjectRoot -WindowStyle Hidden
Write-Host "[start] server 进程已发出(独立进程树,隐藏窗口)"

# ── 3. 就绪等待:日志出现「Uvicorn running」即就绪(冷启动 30~60 秒,上限 90 秒) ──
# 就绪标志在框架日志 mcp_server.log(uvicorn logger 落框架日志);stdout.log 只收崩溃输出
$FrameworkLog = Join-Path $ProjectRoot ".log\mcp_server.log"
if ($NoWait) {
    Write-Host "[done] -NoWait 模式:未等待就绪,详情查 $FrameworkLog"
    exit 0
}
$deadline = (Get-Date).AddSeconds(90)
$ready = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 3
    foreach ($logFile in @($FrameworkLog, $LogPath)) {
        $tail = Get-Content $logFile -Tail 8 -ErrorAction SilentlyContinue
        if ($tail -match 'Uvicorn running') { $ready = $true; break }
        if ($tail -match 'error while attempting to bind|exited with code') { break }
    }
    if ($ready) { break }
    # 兜底:端口已在监听 = 就绪(日志轮转/编码丢失时也不空等)
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
        $ready = $true; break
    }
}
if ($ready) {
    Write-Host "[ready] server 已就绪 http://${HostName}:${Port}/mcp" -ForegroundColor Green
    exit 0
}
Write-Host "[warn] 90 秒内未观察到就绪标志(可能仍在冷启动或已失败),详情查 $FrameworkLog" -ForegroundColor Yellow
exit 2
} finally {
    # 退出路径(exit 0/1/2)统一经此释放锁文件句柄,放行排队中的后续启动
    if ($lockStream) { $lockStream.Dispose() }
}
