# 关联本地星铁安装：驱动原生「选择文件夹」对话框完成游戏目录定位
# 用法：pwsh -File locate_game.ps1 -GameDir "<直接包含 StarRail.exe 的目录>"
# 前提：启动器已带 --remote-debugging-port=9222 启动且在星铁页面；页面点了「定位游戏」或已显示
#       「未查找到 StarRail.exe」弹窗（本脚本会自己点「定位游戏」，两种状态都能接住）。
# 流程：关「位置不可用」报错 → 取消叠加的选择框 → 点「定位游戏」（需要时再点「选择目录」）
#       → 等选择框出现 → 填路径（WM_SETTEXT 写入、WM_GETTEXT 回读校验）→ 点「选择文件夹」→ 轮询关闭。
param(
  [Parameter(Mandatory = $true)]
  [string]$GameDir
)
$ErrorActionPreference = 'Continue'

Add-Type -AssemblyName System.Windows.Forms
Add-Type @'
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public class HypWin {
  public delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);
  public delegate bool EnumChildProc(IntPtr hwnd, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc proc, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr hwnd, EnumChildProc proc, IntPtr lParam);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassName(IntPtr hWnd, StringBuilder sb, int max);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder sb, int max);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
  // 注意：EntryPoint 必须显式指定，CharSet.Unicode 下封送器会找 <方法名>W
  [DllImport("user32.dll", CharSet = CharSet.Unicode, EntryPoint = "SendMessageW")] public static extern IntPtr SendText(IntPtr hWnd, int msg, IntPtr wParam, string lParam);
  [DllImport("user32.dll", EntryPoint = "SendMessage")] public static extern IntPtr SendMsgPtr(IntPtr hWnd, int msg, IntPtr wParam, IntPtr lParam);
  [DllImport("user32.dll", CharSet = CharSet.Unicode, EntryPoint = "SendMessageW")] public static extern IntPtr SendMsgSB(IntPtr hWnd, int msg, IntPtr wParam, StringBuilder lParam);

  public static string GetTextViaMsg(IntPtr h) {
    // GetWindowText 跨进程读不到公共对话框 Edit 的内容，必须 WM_GETTEXT(0x000D) 回读
    int len = (int)SendMsgPtr(h, 0x000E, IntPtr.Zero, IntPtr.Zero).ToInt64();
    if (len <= 0) return "";
    var sb = new StringBuilder(len + 2);
    SendMsgSB(h, 0x000D, (IntPtr)(len + 1), sb);
    return sb.ToString();
  }
  public static List<string> TopDialogs(uint pid) {
    var list = new List<string>();
    EnumWindows((h, l) => {
      uint p; GetWindowThreadProcessId(h, out p);
      if (p == pid) {
        var cb = new StringBuilder(256); GetClassName(h, cb, 256);
        var tb = new StringBuilder(256); GetWindowText(h, tb, 256);
        if (cb.ToString() == "#32770" && IsWindowVisible(h)) list.Add(h.ToInt64() + "|" + tb.ToString());
      }
      return true;
    }, IntPtr.Zero);
    return list;
  }
  public static List<string> Children(long parent) {
    var list = new List<string>();
    EnumChildWindows((IntPtr)parent, (h, l) => {
      var cb = new StringBuilder(256); GetClassName(h, cb, 256);
      var tb = new StringBuilder(256); GetWindowText(h, tb, 256);
      list.Add(h.ToInt64() + "|" + cb.ToString() + "|" + tb.ToString());
      return true;
    }, IntPtr.Zero);
    return list;
  }
  public static void SetText(long h, string s) { SendText((IntPtr)h, 0x000C, IntPtr.Zero, s); }  // WM_SETTEXT
  public static void Click(long h) { SendMsgPtr((IntPtr)h, 0x00F5, IntPtr.Zero, IntPtr.Zero); }  // BM_CLICK
}
'@

$hyp = Get-Process HYP -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $hyp) { Write-Host 'FAIL: HYP (launcher) not running'; exit 1 }
$clickBtn = Join-Path $PSScriptRoot 'hyp_click_btn.mjs'

function Invoke-ClickButton([string]$text) {
  node $clickBtn $text
}

# 关掉所有「位置不可用」报错弹窗（选择框记住的历史路径可能指向不存在的盘，会反复弹）
function Clear-ErrorDialogs {
  param([int]$MaxRounds = 8)
  for ($i = 0; $i -lt $MaxRounds; $i++) {
    $dlgs = [HypWin]::TopDialogs($hyp.Id)
    $errDlg = $dlgs | Where-Object { $_ -match '\|位置不可用' } | Select-Object -First 1
    if (-not $errDlg) { return $true }
    $ech = [HypWin]::Children([int64]($errDlg -split '\|')[0])
    foreach ($line in $ech) {
      $p = $line -split '\|'
      if ($p[1] -eq 'Button' -and $p[2] -match '确定|OK') { [HypWin]::Click([int64]$p[0]); Start-Sleep -Milliseconds 700 }
    }
  }
  return $false
}

# 取消所有叠加的「选择文件夹」选择框（多次触发会叠层，确认信号会被吞）
function Clear-StackedPickers {
  for ($i = 0; $i -lt 10; $i++) {
    $dlgs = [HypWin]::TopDialogs($hyp.Id)
    $pickers = @($dlgs | Where-Object { $_ -match '\|选择文件夹' })
    if ($pickers.Count -eq 0) { return }
    foreach ($pk in $pickers) {
      $ech = [HypWin]::Children([int64]($pk -split '\|')[0])
      foreach ($line in $ech) {
        $p = $line -split '\|'
        if ($p[1] -eq 'Button' -and $p[2] -match '^取消') { [HypWin]::Click([int64]$p[0]); Start-Sleep -Milliseconds 700; break }
      }
    }
  }
}

Clear-ErrorDialogs | Out-Null
Clear-StackedPickers

# 打开选择框：点「定位游戏」；若页面走的是「未查找到」重试弹窗，则再点「选择目录」
$picker = $null
for ($round = 0; $round -lt 3; $round++) {
  Invoke-ClickButton '定位游戏' | Out-Null
  for ($i = 0; $i -lt 12; $i++) {
    Start-Sleep -Milliseconds 500
    Clear-ErrorDialogs | Out-Null
    $dlgs = [HypWin]::TopDialogs($hyp.Id)
    $picker = $dlgs | Where-Object { $_ -match '\|选择文件夹' } | Select-Object -First 1
    if ($picker) { break }
  }
  if ($picker) { break }
  # 页面大概率弹了「未查找到 StarRail.exe」重试弹窗，点其中的「选择目录」
  Invoke-ClickButton '选择目录' | Out-Null
  Start-Sleep -Seconds 2
}
if (-not $picker) { Write-Host 'FAIL: folder picker did not open'; exit 1 }
$pickerHwnd = [int64]($picker -split '\|')[0]
Write-Host "picker: $picker"

# 找「文件夹:」标签旁的 Edit 输入框
$ch = [HypWin]::Children($pickerHwnd)
$editH = 0
$prevLabel = $false
foreach ($line in $ch) {
  $p = $line -split '\|'
  if ($prevLabel -and $p[1] -eq 'Edit') { $editH = [int64]$p[0]; break }
  $prevLabel = ($p[1] -eq 'Static' -and $p[2] -match '文件夹')
}
if ($editH -eq 0) { Write-Host 'FAIL: path edit not found'; exit 1 }

# 填路径并回读校验
[HypWin]::SetText($editH, $GameDir)
Start-Sleep -Milliseconds 500
$cur = [HypWin]::GetTextViaMsg([IntPtr]$editH)
Write-Host "edit content: '$cur'"
if ($cur -ne $GameDir) { Write-Host 'FAIL: set path failed'; exit 1 }

# 点「选择文件夹」确认
$confirmH = 0
foreach ($line in $ch) {
  $p = $line -split '\|'
  if ($p[1] -eq 'Button' -and $p[2] -match '^选择文件夹') { $confirmH = [int64]$p[0] }
}
if ($confirmH -eq 0) { Write-Host 'FAIL: confirm button not found'; exit 1 }
[HypWin]::Click($confirmH)
Write-Host 'confirmed, waiting picker to close ...'
for ($i = 0; $i -lt 10; $i++) {
  Start-Sleep -Seconds 2
  Clear-ErrorDialogs | Out-Null
  $dlgs = [HypWin]::TopDialogs($hyp.Id)
  $still = $dlgs | Where-Object { $_ -match '\|选择文件夹' }
  if (-not $still) { Write-Host "picker closed after $($i * 2 + 2)s"; break }
}

# 打印页面状态（应出现「定位本地游戏：为您找到以下游戏资源 ...」或关联成功提示）
node (Join-Path $PSScriptRoot 'hyp_state.mjs')
