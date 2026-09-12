# 提交管线落库完整性门(并行批 commit 后 push 前必跑;集成协议见 sr-od-test/README.md
# 「并行批 commit 口径」第 10 步。立项依据=批量提交管线三笔同型缺陷:新载体文件从未
# 入树(提交脚本解析 git status 的 R 行伪路径+吞错),本地验证全绿纯靠工作树 untracked
# 文件撑着(验证视角与缺陷视角错位),fresh checkout 不可运行。
# 用法: pwsh -File tools/commit_tree_gate.ps1 -Repo <repo根> -Expected <预期文件清单文件,每行一路径>
#   或 -Paths <逗号分隔路径>。三件核验:name-status 对账 + 新文件 cat-file + 树内不再含已删路径。
#   第四件(fresh 冒烟,-SmokeTests 给测试目录时启用):临时 worktree 检出该笔,在 worktree 内
#   pytest --collect-only;收集错误命中本批改动面(改动路径或其 src 模块点分名)即红——
#   查「文件在树但锁-源不同步/导入断裂」这类文件级核验查不出的问题。
#   -SmokeTests 路径相对 -Repo 根(主仓调用给 sr-od-test/test/...,测试仓调用给 test/...):
#   主仓调用=worktree 镜像当前 sr-od-test 工作树,验 committed src + 现役测试;测试仓调用=
#   直接收集 worktree 里的 committed 测试树,PYTHONPATH 取主仓 src。两仓各跑各的门,
#   合起来盖住新载体缺树缺陷的两个半边(主仓 src 载体/测试仓测试载体)。
# 并行环境:-Commit 必须给本笔提交 hash(九步协议的 $new),禁裸 HEAD——门运行时 HEAD
#   可能已被并行批推进,裸 HEAD 验到的是别人的提交。预期集口径=name-status 新态路径
#   (改名文件申报 R 行新路径;旧路径若同笔删除则另列申报)。
param(
    [Parameter(Mandatory)][string]$Repo,
    [string]$Expected,
    [string]$Paths,
    [string]$Commit = 'HEAD',
    [string]$SmokeTests,
    [string]$PyExe = 'python'
)
$ErrorActionPreference = 'Stop'
Set-Location $Repo
$expect = @()
if ($Expected) { $expect = @(Get-Content $Expected | Where-Object { $_.Trim() }) }
elseif ($Paths) { $expect = @($Paths -split ',' | ForEach-Object { $_.Trim() }) }
else { throw '须给 -Expected 清单文件或 -Paths' }

$actual = @(git show --name-status --format="" $Commit | ForEach-Object {
    # name-status 行:状态\t路径[\t旧路径];取最后一字段为新态路径(改名=R 行取新路径)
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

# 第四件:fresh worktree 冒烟。失败处置:本批改动面出现收集错误=禁 push(修复以新提交
# 收口,并行期禁 amend/rebase);其余收集错误只报告,归兄弟在飞面人工复核。
# worktree 检出失败必须显式炸,禁静默降级成「跑主仓工作树」的假 fresh——那会复制
# 「本地绿纯靠工作树撑着」的验证视角错位,冒烟结论整体失真。
if ($SmokeTests) {
    $mainRoot = $Repo
    if (-not (Test-Path (Join-Path $mainRoot 'src'))) { $mainRoot = Split-Path -Parent $Repo }
    $wt = Join-Path $mainRoot ".debug\temp\gate-smoke-wt-$PID"
    git worktree remove $wt --force 2>$null | Out-Null
    git worktree add $wt $Commit 2>&1 | Out-Null
    if (-not (Test-Path $wt)) { throw "fresh 冒烟:worktree 检出失败($Commit),禁静默降级,先排查上方 git worktree 输出" }
    $prevPyPath = $env:PYTHONPATH
    try {
        # PYTHONPATH 锚:主仓调用=worktree 内 committed src;测试仓调用=主仓 src
        $srcAnchor = Join-Path $wt 'src'
        if (-not (Test-Path $srcAnchor)) { $srcAnchor = Join-Path $mainRoot 'src' }
        if (-not (Test-Path $srcAnchor)) { throw 'fresh 冒烟:定位不到 src(PYTHONPATH 锚),检查 -Repo 布局' }
        $env:PYTHONPATH = $srcAnchor
        if (Test-Path (Join-Path $Repo 'sr-od-test')) {
            # 测试仓随主仓走:镜像当前工作树态(含其独立 git 的尖端)——先于冒烟路径解析,
            # 主仓调用的 worktree 本身不含 sr-od-test,镜像后才有
            robocopy (Join-Path $Repo 'sr-od-test') (Join-Path $wt 'sr-od-test') /MIR /NFL /NDL /NJH /NJS | Out-Null
        }
        # 冒烟路径相对 -Repo 根,解析进 worktree;worktree 内不存在=路径给错,炸
        $wtTests = @()
        foreach ($t in @($SmokeTests -split ',' | ForEach-Object { $_.Trim() })) {
            $p = Join-Path $wt $t
            if (-not (Test-Path $p)) { throw "fresh 冒烟:worktree 内无该测试路径: $t" }
            $wtTests += $p
        }
        # 本批改动面归因集:改动路径(正斜杠) + src 文件的点分模块名
        # (导入断裂时错误文本出现的是模块名而非路径,两形态都要能归因)
        $mods = @($actual | Where-Object { $_ -match '^src/' } |
            ForEach-Object { ($_ -replace '\\', '/') -replace '^src/', '' -replace '\.py$', '' -replace '/', '.' })
        Push-Location $wt
        try {
            $out = & $PyExe -m pytest $wtTests -m "not slow" -q --co -p no:cacheprovider --continue-on-collection-errors 2>&1 |
                Out-String
        } finally { Pop-Location }
        $errs = @($out -split "`n" | Where-Object { $_ -match '^ERROR ' })
        $batchHit = @($errs | Where-Object {
            $ln = $_ -replace '\\', '/'
            $hit = $false
            foreach ($c in $actual) { if ($c -and $ln.Contains($c)) { $hit = $true; break } }
            if (-not $hit) { foreach ($m in $mods) { if ($ln.Contains($m)) { $hit = $true; break } } }
            $hit
        })
        Write-Host "fresh 冒烟: collected 行=$(($out -split "`n" | Where-Object { $_ -match 'collected' }) -join ';'); 收集错误 $($errs.Count) 条(本批面 $($batchHit.Count) 条)"
        $errs | ForEach-Object { Write-Host "  ERROR $_" }
        if ($batchHit.Count -gt 0) { throw 'fresh 冒烟:本批改动面出现收集错误,禁 push' }
        Write-Host 'fresh 冒烟 PASS(本批改动面零收集错误;余下错误归兄弟在飞面,人工复核)'
    } finally {
        git worktree remove $wt --force 2>$null | Out-Null
        if ($null -ne $prevPyPath) { $env:PYTHONPATH = $prevPyPath } else { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue }
    }
}
