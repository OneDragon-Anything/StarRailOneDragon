#Requires -Version 7.0
<#
.SYNOPSIS
  worktree 批隔离生命周期工具:一个 change 一棵树——建树 / 自检 / 重放 / 并入 / 清场。

.DESCRIPTION
  规范正本 = docs/develop/harness/agent_worktrees.md。本脚本是该规范的机械动作实现:
    · 主仓树  <仓库根>/.debug/worktrees/<change-id>/   分支 wt/<change-id>(从集成分支切)
    · 测试仓  <仓库根>/sr-od-test(独立仓库)配对检出到 <主仓树>/sr-od-test/,同名分支
    · 建树时把仓库根 .env 硬链接进树根(失败退化为复制)

  全程零 junction / 零 symlink:树内不共享任何目录。树内执行的遥测写在树自己的 .debug,
  由 land 搬回主仓(重名报错不覆盖);remove 前若树内 .debug 非空则拒绝删除。

  land 会前移集成分支并改写主工作区文件,故仓库路径与集成分支名可参数化,
  端到端冒烟在一性次 scratch 仓库里做。

.EXAMPLE
  pwsh tools/wt.ps1 new 2026-09-11-unified-state
.EXAMPLE
  pwsh tools/wt.ps1 check 2026-09-11-unified-state
.EXAMPLE
  pwsh tools/wt.ps1 rebase 2026-09-11-unified-state
.EXAMPLE
  pwsh tools/wt.ps1 land 2026-09-11-unified-state
.EXAMPLE
  pwsh tools/wt.ps1 remove 2026-09-11-unified-state
.EXAMPLE
  pwsh tools/wt.ps1 list
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('new', 'check', 'rebase', 'land', 'remove', 'list')]
    [string]$Action,

    [Parameter(Position = 1)]
    [string]$ChangeId,

    [string]$RepoPath,
    [string]$TestRepoName = 'sr-od-test',
    [string]$IntegrationBranch,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

function Fail([string]$Message, [int]$Code = 1) {
    Write-Host "[wt] $Message" -ForegroundColor Red
    exit $Code
}

function Info([string]$Message) {
    Write-Host "[wt] $Message"
}

function Warn([string]$Message) {
    Write-Host "[wt] $Message" -ForegroundColor Yellow
}

function Invoke-Git {
    param(
        [string]$Repo,
        [string[]]$Arguments,
        [switch]$AllowFail
    )
    $out = & git -C $Repo @Arguments 2>&1
    $code = $LASTEXITCODE
    $lines = @($out | ForEach-Object { "$_" })
    if ($code -ne 0 -and -not $AllowFail) {
        throw ("git -C $Repo " + ($Arguments -join ' ') + " 失败(exit $code):" + [Environment]::NewLine + ($lines -join [Environment]::NewLine))
    }
    return [pscustomobject]@{ Code = $code; Out = $lines }
}

function Test-ReparsePoint([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    $item = Get-Item -LiteralPath $Path -Force
    return [bool]($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)
}

function Get-DirtyPaths {
    param([string]$Tree, [switch]$IgnoreTestGitlink)
    if (-not (Test-Path -LiteralPath $Tree)) { return @() }
    $res = Invoke-Git -Repo $Tree -Arguments @('status', '--porcelain') -AllowFail
    $lines = @($res.Out | Where-Object { $_.Trim() -ne '' })
    $kept = [System.Collections.Generic.List[string]]::new()
    foreach ($line in $lines) {
        # porcelain v1 形状:XY<空格>路径
        $pathPart = if ($line.Length -gt 3) { $line.Substring(3).Trim().Trim('"') } else { '' }
        # 树内 .debug 是设计内的遥测空间(由 land 抢救搬回,remove 前另有非空守卫),不算脏
        if ($pathPart -eq '.debug' -or $pathPart.StartsWith('.debug/') -or $pathPart.StartsWith('.debug\')) { continue }
        # 主仓以 gitlink 指针引用测试仓,树内该条目恒显示为 modified / deleted / 未跟踪目录——属预期噪声
        if ($IgnoreTestGitlink) {
            $probe = $pathPart.TrimEnd('/', '\')
            if ($probe -eq $TestRepoName -or $probe.StartsWith("$TestRepoName/") -or $probe.StartsWith("$TestRepoName\")) { continue }
        }
        $kept.Add($line)
    }
    return $kept.ToArray()
}

function Get-CurrentBranch([string]$Tree) {
    $res = Invoke-Git -Repo $Tree -Arguments @('rev-parse', '--abbrev-ref', 'HEAD')
    return $res.Out[0].Trim()
}

function Show-Tree {
    Write-Host "主仓树  :$wtPath"
    Write-Host "测试树  :$testWtPath"
    Write-Host "主仓分支:$branch(集成分支 $mainIntegration)"
    Write-Host "测试分支:$branch(集成分支 $testIntegration)"
}

# ---------- 动作实现 ----------

function Do-New {
    if (Test-Path -LiteralPath $wtPath) {
        if (Test-Path -LiteralPath (Join-Path $wtPath '.git')) {
            Info '树已存在,跳过创建(幂等)'
            Show-Tree
            return
        }
        Fail "目标路径已存在但不是 worktree:$wtPath" 2
    }
    Info "主仓建树:$wtPath(分支 $branch,基线 $mainIntegration)"
    Invoke-Git -Repo $repo -Arguments @('worktree', 'add', $wtPath, '-b', $branch, $mainIntegration) | Out-Null
    Info "测试仓建树:$testWtPath(分支 $branch,基线 $testIntegration)"
    Invoke-Git -Repo $testRepo -Arguments @('worktree', 'add', $testWtPath, '-b', $branch, $testIntegration) | Out-Null

    $srcEnv = Join-Path $repo '.env'
    $dstEnv = Join-Path $wtPath '.env'
    if (Test-Path -LiteralPath $srcEnv) {
        try {
            New-Item -ItemType HardLink -Path $dstEnv -Target $srcEnv -ErrorAction Stop | Out-Null
            Info '.env 已硬链接进树根'
        }
        catch {
            Copy-Item -LiteralPath $srcEnv -Destination $dstEnv -Force
            Warn '硬链接 .env 失败,已退化为复制(主仓 .env 后续改动不会自动同步到本树)'
        }
    }
    else {
        Info '仓库根无 .env,跳过'
    }
    Show-Tree
}

function Do-Check {
    $problems = [System.Collections.Generic.List[string]]::new()
    $mainDirty = Get-DirtyPaths -Tree $wtPath -IgnoreTestGitlink
    if ($mainDirty.Count -gt 0) {
        $problems.Add("主仓树不干净($($mainDirty.Count) 项未提交/未跟踪,gitlink $TestRepoName 已忽略):")
        foreach ($d in $mainDirty) { $problems.Add("    $d") }
    }
    $testDirty = Get-DirtyPaths -Tree $testWtPath
    if ($testDirty.Count -gt 0) {
        $problems.Add("测试树不干净($($testDirty.Count) 项未提交/未跟踪):")
        foreach ($d in $testDirty) { $problems.Add("    $d") }
    }
    if ($problems.Count -gt 0) {
        Write-Host "[wt] 不干净(合并前必须为零):" -ForegroundColor Red
        foreach ($p in $problems) { Write-Host $p }
        exit 1
    }
    Info '两仓干净'
}

function Do-Rebase {
    $targets = @(
        [pscustomobject]@{ Name = '主仓'; Tree = $wtPath; Base = $mainIntegration },
        [pscustomobject]@{ Name = '测试仓'; Tree = $testWtPath; Base = $testIntegration }
    )
    foreach ($t in $targets) {
        Info "$($t.Name):把 $($t.Base) 重放到 $branch"
        $res = Invoke-Git -Repo $t.Tree -Arguments @('rebase', $t.Base) -AllowFail
        if ($res.Code -ne 0) {
            $conflicts = (Invoke-Git -Repo $t.Tree -Arguments @('diff', '--name-only', '--diff-filter=U') -AllowFail).Out
            Write-Host "[wt] $($t.Name) 重放冲突(需由该批 worker 在自己的树里解决):" -ForegroundColor Red
            foreach ($c in $conflicts) { Write-Host "    $c" }
            exit 1
        }
    }
    Info '两仓重放完成'
}

function Move-TreeDebug {
    $srcDebug = Join-Path $wtPath '.debug'
    if (-not (Test-Path -LiteralPath $srcDebug)) { Info '树内无 .debug,无需抢救'; return }
    $files = @(Get-ChildItem -LiteralPath $srcDebug -Recurse -File -Force)
    if ($files.Count -eq 0) { Info '树内 .debug 为空,无需抢救'; return }
    $dstRoot = Join-Path $repo '.debug'
    $moved = 0
    foreach ($f in $files) {
        $rel = $f.FullName.Substring($srcDebug.Length).TrimStart('\', '/')
        $dst = Join-Path $dstRoot $rel
        if (Test-Path -LiteralPath $dst) {
            Fail "遥测抢救冲突:目标已存在 $dst(不覆盖,请人工处置后重跑)" 1
        }
        $dstDir = Split-Path -Parent $dst
        if (-not (Test-Path -LiteralPath $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
        Move-Item -LiteralPath $f.FullName -Destination $dst
        $moved++
    }
    Info "遥测抢救完成:$moved 个文件搬回主仓 .debug"
}

function Do-Land {
    $onBranch = Get-CurrentBranch $wtPath
    if ($onBranch -ne $branch) { Fail "批树不在 $branch 上(当前 $onBranch),拒绝并入" 1 }
    $dirty = @(Get-DirtyPaths -Tree $wtPath -IgnoreTestGitlink) + @(Get-DirtyPaths -Tree $testWtPath)
    if ($dirty.Count -gt 0) { Fail "批树不干净,拒绝并入(先提交或清理,再由合并者重跑 check)" 1 }

    # 抢救先于并入:抢救冲突时集成分支尚未被前移,不留「已并入但遥测没搬回」的半状态;
    # 并入若被主工作区存量脏文件挡住,遥测已在主仓(重试时抢救为空操作),同样安全
    Move-TreeDebug

    Info "主仓快进:$mainIntegration <- $branch"
    $mainMerge = Invoke-Git -Repo $repo -Arguments @('merge', '--ff-only', $branch) -AllowFail
    if ($mainMerge.Code -ne 0) {
        $joined = $mainMerge.Out -join ' '
        if ($joined -match 'local changes|would be overwritten') {
            Write-Host "[wt] 受阻:主工作区存量未提交改动与本次并入文件面相交(git 拒绝快进)。记录后留待重试,禁 stash/reset/强行 checkout。" -ForegroundColor Red
        }
        else {
            Write-Host "[wt] 主仓快进失败(非快进或不满足前置):" -ForegroundColor Red
        }
        foreach ($o in $mainMerge.Out) { Write-Host "    $o" }
        exit 1
    }

    Info "测试仓快进:$testIntegration <- $branch"
    $testMerge = Invoke-Git -Repo $testRepo -Arguments @('merge', '--ff-only', $branch) -AllowFail
    if ($testMerge.Code -ne 0) {
        Write-Host '[wt] 测试仓快进失败:' -ForegroundColor Red
        foreach ($o in $testMerge.Out) { Write-Host "    $o" }
        exit 1
    }

    $mainHead = (Invoke-Git -Repo $repo -Arguments @('rev-parse', '--short', 'HEAD')).Out[0]
    $testHead = (Invoke-Git -Repo $testRepo -Arguments @('rev-parse', '--short', 'HEAD')).Out[0]
    Info "并入完成:主仓 $mainIntegration=$mainHead,测试仓 $testIntegration=$testHead"
}

function Find-ReparsePointsInTree([string]$Root) {
    if (-not (Test-Path -LiteralPath $Root)) { return @() }
    # PS7 的 -Recurse 默认不跟进 reparse point,故扫描本身不会穿透
    return @(Get-ChildItem -LiteralPath $Root -Recurse -Directory -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Attributes -band [System.IO.FileAttributes]::ReparsePoint } |
        ForEach-Object { $_.FullName })
}

function Do-Remove {
    if (-not (Test-Path -LiteralPath $wtPath) -and -not (Test-Path -LiteralPath $testWtPath)) {
        Info '两仓树均不存在,无需删除'
        return
    }
    # 守卫 1:reparse point 一律拒绝——树根本身,以及树内任何一处(后者会被 git 递归删树时穿透)
    foreach ($p in @($wtPath, $testWtPath)) {
        if (Test-ReparsePoint $p) { Fail "$p 是 reparse point(junction/symlink),拒绝删除" 1 }
    }
    foreach ($p in @($wtPath, $testWtPath)) {
        $links = Find-ReparsePointsInTree $p
        if ($links.Count -gt 0) {
            Write-Host '[wt] 树内存在 reparse point(junction/symlink),递归删除可能穿透到目标(可能是主仓共享目录),拒绝删除(-Force 也不放行):' -ForegroundColor Red
            foreach ($l in $links) { Write-Host "    $l" }
            Write-Host '[wt] 处置:先用 cmd 的 rmdir 删掉这些链接(只删链接不动目标),再重跑 remove' -ForegroundColor Red
            exit 1
        }
    }
    # 守卫 2:树内 .debug 非空 = 有未抢救遥测
    $srcDebug = Join-Path $wtPath '.debug'
    if ((Test-Path -LiteralPath $srcDebug) -and @(Get-ChildItem -LiteralPath $srcDebug -Recurse -File -Force).Count -gt 0) {
        if (-not $Force) {
            Fail "树内 .debug 非空(有未抢救的遥测):先 land 搬回主仓,或人工处置;确要丢弃加 -Force" 1
        }
        Warn '-Force:丢弃树内 .debug 内容'
    }
    # 守卫 3:两仓工作树干净
    foreach ($pair in @([pscustomobject]@{ Tree = $wtPath; Name = '主仓树' }, [pscustomobject]@{ Tree = $testWtPath; Name = '测试树' })) {
        if (-not (Test-Path -LiteralPath $pair.Tree)) { continue }
        $d = Get-DirtyPaths -Tree $pair.Tree -IgnoreTestGitlink:($pair.Tree -eq $wtPath)
        if ($d.Count -gt 0 -and -not $Force) {
            Write-Host "[wt] $($pair.Name) 不干净,拒绝删除(先提交或清理;确要强删加 -Force):" -ForegroundColor Red
            foreach ($x in $d) { Write-Host "    $x" }
            exit 1
        }
    }

    # 先删测试树(它位于主仓树内部),再删主仓树。
    # 两处都用 --force 交给 git:真实脏(.debug 未抢救 / 工作树不干净)已由上面三道守卫拦下;
    # git 自家的检查会把「嵌套测试树目录消失导致的 gitlink 删除态」也判成脏——那是本方案的预期噪声。
    $forceArgs = @('--force')

    # 先删测试树(它位于主仓树内部),再删主仓树
    if (Test-Path -LiteralPath $testWtPath) {
        Info "删除测试树:$testWtPath"
        Invoke-Git -Repo $testRepo -Arguments (@('worktree', 'remove') + $forceArgs + @($testWtPath)) | Out-Null
    }
    if (Test-Path -LiteralPath $wtPath) {
        Info "删除主仓树:$wtPath"
        Invoke-Git -Repo $repo -Arguments (@('worktree', 'remove') + $forceArgs + @($wtPath)) | Out-Null
    }

    # 分支:先试安全删除(-d 拒绝未合并分支,防丢引用),失败且未 -Force 则保留并报错
    foreach ($pair in @([pscustomobject]@{ Repo = $repo; Name = '主仓' }, [pscustomobject]@{ Repo = $testRepo; Name = '测试仓' })) {
        $exists = (Invoke-Git -Repo $pair.Repo -Arguments @('branch', '--list', $branch) -AllowFail).Out
        if (-not ($exists -join '').Trim()) { continue }
        $del = Invoke-Git -Repo $pair.Repo -Arguments @('branch', '-d', $branch) -AllowFail
        if ($del.Code -ne 0) {
            if (-not $Force) {
                Write-Host "[wt] $($pair.Name) 分支 $branch 尚未并入集成分支,已保留(删掉会失去未合并提交的引用);确要删加 -Force" -ForegroundColor Red
                exit 1
            }
            Invoke-Git -Repo $pair.Repo -Arguments @('branch', '-D', $branch) | Out-Null
        }
    }
    Info '清场完成(两仓树与分支均已删除)'
}

function Do-List {
    $res = Invoke-Git -Repo $repo -Arguments @('worktree', 'list', '--porcelain')
    $blocks = [System.Collections.Generic.List[hashtable]]::new()
    $cur = @{}
    foreach ($line in $res.Out) {
        if ($line -match '^worktree (.+)$') {
            if ($cur.Count -gt 0) { $blocks.Add($cur) }
            $cur = @{ Path = $Matches[1] }
        }
        elseif ($line -match '^branch (.+)$') {
            $cur['Branch'] = $Matches[1]
        }
        elseif ($line -match '^detached') {
            $cur['Branch'] = '(detached)'
        }
    }
    if ($cur.Count -gt 0) { $blocks.Add($cur) }

    $trees = @($blocks | Where-Object { $_.Path -match '[\\/]\.debug[\\/]worktrees[\\/]' })
    if ($trees.Count -eq 0) { Info '当前无已登记的批隔离树'; return }
    Info "已登记 $($trees.Count) 棵树:"
    foreach ($t in $trees) {
        $id = [System.IO.Path]::GetFileName($t.Path)
        $testTree = Join-Path $t.Path $TestRepoName
        $mainState = if (@(Get-DirtyPaths -Tree $t.Path -IgnoreTestGitlink).Count -gt 0) { '主仓树脏' } else { '主仓树净' }
        $testState = if (-not (Test-Path -LiteralPath $testTree)) { '无测试树' }
        elseif (@(Get-DirtyPaths -Tree $testTree).Count -gt 0) { '测试树脏' }
        else { '测试树净' }
        Write-Host ("  {0}`n    路径  :{1}`n    分支  :{2}`n    状态  :{3} / {4}" -f $id, $t.Path, ($t.Branch -replace '^refs/heads/', ''), $mainState, $testState)
    }
}

# ---------- 入口 ----------

$repo = if ($RepoPath) { (Resolve-Path -LiteralPath $RepoPath).Path } else { Split-Path -Parent $PSScriptRoot }

if (-not (Test-Path -LiteralPath (Join-Path $repo '.git'))) {
    Fail "仓库根不存在或不是 git 仓库:$repo" 2
}

$testRepo = Join-Path $repo $TestRepoName
if ($Action -ne 'list' -and -not (Test-Path -LiteralPath $testRepo)) {
    Fail "测试仓不存在:$testRepo(独立仓库需先放在仓库根;可 -TestRepoName 改名)" 2
}

if ($Action -ne 'list' -and [string]::IsNullOrWhiteSpace($ChangeId)) {
    Fail "缺少 change-id(用法:pwsh tools/wt.ps1 <$Action> <change-id>)" 2
}

$mainIntegration = if ($IntegrationBranch) { $IntegrationBranch } else { Get-CurrentBranch $repo }
$testIntegration = if ($Action -eq 'list') { '' } else { Get-CurrentBranch $testRepo }
$branch = "wt/$ChangeId"
$wtPath = Join-Path (Join-Path $repo '.debug\worktrees') $ChangeId
$testWtPath = Join-Path $wtPath $TestRepoName

switch ($Action) {
    'new' { Do-New }
    'check' { Do-Check }
    'rebase' { Do-Rebase }
    'land' { Do-Land }
    'remove' { Do-Remove }
    'list' { Do-List }
}
