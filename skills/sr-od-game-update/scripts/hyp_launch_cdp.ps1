# 经 explorer 委托以用户桌面上下文启动带 CDP 调试口的米哈游启动器
# 用法：pwsh -File hyp_launch_cdp.ps1 -LauncherPath "F:\miHoYo Launcher\launcher.exe" [-Biz hkrpg_cn] [-Port 9222]
# 原理：explorer 常驻于用户桌面上下文（非提权），让它"打开"一个 .lnk 即以它的令牌启动目标——
#       从提权 shell 直接启动会让启动器界面读不出已保存的游戏关联（列表缺游戏），必须走本脚本。
# explorer 的"打开"不转发应用参数，参数要内嵌进 .lnk 的 Arguments 字段。
# 调试口工具（hyp_state.mjs 等）默认连 9222。
param(
  [Parameter(Mandatory = $true)]
  [string]$LauncherPath,
  [string]$Biz = '',
  [int]$Port = 9222
)
$ErrorActionPreference = 'Stop'

if (-not (Test-Path $LauncherPath)) { Write-Host "FAIL: launcher not found: $LauncherPath"; exit 1 }

$argString = '--remote-debugging-port=' + $Port
if ($Biz) { $argString = "--game=$Biz " + $argString }

$ws = New-Object -ComObject WScript.Shell
$lnkPath = Join-Path $env:TEMP ('hyp_cdp_' + [guid]::NewGuid().ToString('N').Substring(0, 8) + '.lnk')
$lnk = $ws.CreateShortcut($lnkPath)
$lnk.TargetPath = $LauncherPath
$lnk.Arguments = $argString
$lnk.WorkingDirectory = Split-Path $LauncherPath
$lnk.Save()
Write-Host "lnk: $lnkPath ($argString)"

Start-Process explorer.exe -ArgumentList ('"' + $lnkPath + '"')

# 等启动器起来并确认调试口
$deadline = (Get-Date).AddSeconds(40)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 2
  $hyp = Get-Process HYP -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($hyp) { break }
}
if (-not $hyp) { Write-Host 'FAIL: HYP did not start'; exit 1 }
$deadline = (Get-Date).AddSeconds(20)
while ((Get-Date) -lt $deadline) {
  try {
    Invoke-WebRequest ('http://127.0.0.1:' + $Port + '/json/version') -UseBasicParsing -TimeoutSec 2 | Out-Null
    Write-Host "OK: HYP pid=$($hyp.Id) CDP port $Port open"
    exit 0
  } catch { Start-Sleep -Seconds 2 }
}
Write-Host 'FAIL: CDP port did not open'
exit 1
