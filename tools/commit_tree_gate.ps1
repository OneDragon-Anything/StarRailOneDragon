# 提交管线落库完整性门(并行批提交后必跑;立项依据=T-7 r1 验收核2:
# 段3/段4/段5 三笔同型缺陷——新载体文件从未入树,fresh checkout 不可运行)
# 用法: pwsh -File tools/commit_tree_gate.ps1 -Repo <repo根> -Expected <预期文件清单文件,每行一路径>
#   或 -Paths <逗号分隔路径>。三件核验:name-status 对账 + 新文件 cat-file + 树内不再含已删路径。
param(
    [Parameter(Mandatory)][string]$Repo,
    [string]$Expected,
    [string]$Paths,
    [string]$Commit = 'HEAD'
)
$ErrorActionPreference = 'Stop'
Set-Location $Repo
$expect = @()
if ($Expected) { $expect = @(Get-Content $Expected | Where-Object { $_.Trim() }) }
elseif ($Paths) { $expect = @($Paths -split ',' | ForEach-Object { $_.Trim() }) }
else { throw '须给 -Expected 清单文件或 -Paths' }

$actual = @(git show --name-status --format="" $Commit | ForEach-Object {
    # name-status 行:状态\t路径[\t旧路径];取最后一字段为新态路径
    $parts = $_ -split "`t"
    $parts[-1]
})
$missingInCommit = @($expect | Where-Object { $actual -notcontains $_ })
$extraInCommit = @($actual | Where-Object { $expect -notcontains $_ })
# 新增文件(A)必须真实在树
$added = @(git show --name-status --format="" $Commit | Where-Object { $_ -match '^A\t' } |
    ForEach-Object { ($_ -split "`t")[-1] })
$catFail = @()
foreach ($f in $added) {
    git cat-file -e "${Commit}:$f" 2>$null
    if ($LASTEXITCODE -ne 0) { $catFail += $f }
}
# 已删路径(D)必须不在树
$deleted = @(git show --name-status --format="" $Commit | Where-Object { $_ -match '^D\t' } |
    ForEach-Object { ($_ -split "`t")[-1] })
$ghost = @()
foreach ($f in $deleted) {
    git cat-file -e "${Commit}:$f" 2>$null
    if ($LASTEXITCODE -eq 0) { $ghost += $f }
}
$fail = $false
if ($missingInCommit.Count -gt 0) { Write-Host "FAIL 预期未入库: $($missingInCommit -join ', ')"; $fail = $true }
if ($extraInCommit.Count -gt 0) { Write-Host "FAIL 入库集外卷入: $($extraInCommit -join ', ')"; $fail = $true }
if ($catFail.Count -gt 0) { Write-Host "FAIL 新增文件不在树(cat-file): $($catFail -join ', ')"; $fail = $true }
if ($ghost.Count -gt 0) { Write-Host "FAIL 已删文件仍在树: $($ghost -join ', ')"; $fail = $true }
if ($fail) { throw '落库完整性门未过:禁 push' }
Write-Host "落库完整性门 PASS: 预期 $($expect.Count) 文件,新增 cat-file 全过,已删出树核全过"
