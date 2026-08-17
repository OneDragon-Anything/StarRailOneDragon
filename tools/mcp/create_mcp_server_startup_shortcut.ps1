# Create SR OD MCP Server Startup Shortcut
#
# 在 Windows Startup 文件夹建快捷方式,使主 MCP server(端口 24001)登录后自动启动,
# **不经 daemon 派生**。与 daemon 自启快捷方式(``tools/mcp/daemon/create_startup_shortcut.ps1``)
# 相互独立、可共存:daemon 管 server 生命周期(启停/重启),本快捷方式让 server 登录后即就绪。
# 两者幂等:daemon 的 start 工具先检测进程已存在则跳过,不会重复拉起 / 端口冲突。
# 卸载即删该 ``.lnk``。

$ErrorActionPreference = "Stop"

# 本脚本位于 tools/mcp/,向上 2 级到项目根
$ProjectRoot = Split-Path -Path (Split-Path -Path $PSScriptRoot -Parent) -Parent
$StartScript = Join-Path $ProjectRoot "tools\mcp\start_mcp_server.ps1"

# Startup 文件夹
$StartupFolder = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$ShortcutPath = Join-Path $StartupFolder "SR OD MCP Server.lnk"

Write-Host "============================================================"  -ForegroundColor Cyan
Write-Host "SR OD MCP Server - Startup Shortcut Creator" -ForegroundColor Cyan
Write-Host "============================================================"  -ForegroundColor Cyan
Write-Host ""
Write-Host "Project Root: $ProjectRoot"
Write-Host "Start Script: $StartScript"
Write-Host "Shortcut Path: $ShortcutPath"
Write-Host "============================================================"  -ForegroundColor Cyan
Write-Host ""

# 检查 start_mcp_server.ps1 存在
if (-not (Test-Path $StartScript)) {
    Write-Host "[ERROR] start_mcp_server.ps1 not found: $StartScript" -ForegroundColor Red
    exit 1
}

# 创建 WScript.Shell 对象
$WshShell = New-Object -ComObject WScript.Shell

# 创建快捷方式
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$StartScript`""
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.Description = "SR OD MCP Server - backend main server (game operation)"
$Shortcut.Save()

# 释放 COM 对象
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($WshShell) | Out-Null

Write-Host "[SUCCESS] Shortcut created!" -ForegroundColor Green
Write-Host ""
Write-Host "Shortcut location: $ShortcutPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "SR OD MCP Server will now automatically start when you log in." -ForegroundColor Green
Write-Host ""
Write-Host "To remove:" -ForegroundColor Yellow
Write-Host "  Delete the shortcut file: $ShortcutPath"
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
