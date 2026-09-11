"""起局前置码哈希结构闸(ADR-0581):T-106 混合码事故(run6 部署失败×7)的结构防线。

设计口径/覆盖边界/豁免申报的持久单一源 = ADR-0581
(docs/develop/sr_od/application/currency_war/decisions/0581-start-match-code-hash-gate.md);
实施批账本行(T-107,.debug/progress/ 易失)仅为辅助出处。

语义(如实申报):闸比对「当前工作树文件内容」与「git HEAD 内容」,工作树 ≠ HEAD
即拒绝起局——含义是「你即将运行的码 ≠ 已提交的码」。server 为常驻进程,其模块
加载态 = import 时快照,进程内存不可回读;故以 sys.modules 中 currency_war 前缀
模块的文件集合近似「server 实际使用的码面」,再逐文件做现盘内容 vs HEAD 内容
哈希比对:在飞编辑/未提交批次存在时,磁盘与 HEAD 必然分叉,闸即拦截。
覆盖边界(ADR-0581 §2.2):延迟加载模块起局时刻不在 sys.modules(实测覆盖 ≈43%
包文件),闸是纪律防线不是完备机制,「在飞批禁起局」人工纪律不因此解除。

豁免:已知合法不一致走默认豁免名单(锚定完整相对路径匹配,防同尾缀路径
静默漏扫)。唯一在册豁免 `src/sr_od/application/currency_war/data/
cw_delta_pool_data.py`:该文件由局终自动再生管线写入(生成器唯一核心
sim/cw_delta_pool_gen.py,实机局终钩子调用,ADR-0344),磁盘内容 ≠ HEAD 属
设计内稳态而非编辑污染;残余风险申报——针对该文件的在飞编辑批闸无法区分,
由该文件自身的快照指纹机制(sim/pool.py resolve_pool 指纹失配校验)另行看守。
豁免名单可参数化扩展,新增豁免须逐条给理由,禁宽豁免。

零行为副作用:闸只拦起局并输出结构化不一致清单,不改任何游戏逻辑;可经
`CurrencyWarConfig.code_hash_gate` 配置关闭(缺省开)。git 自身不可用
(含 git 二进制缺失)按 fail-closed 处理(安全闸宁拦勿放),reason 如实申报;
即 git 缺失 = 起局被拒,git 是起局硬依赖(ADR-0581 §2.4)。
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from one_dragon.utils.file_utils import get_project_root

# 闸辖域:currency_war 应用模块前缀(sys.modules 过滤用)
MODULE_PREFIX: str = 'sr_od.application.currency_war'

# 默认豁免名单(锚定完整相对路径,仓库根相对——非后缀匹配:endswith 会让辖域内
# 未来任何同尾缀路径静默漏扫,ADR-0581 §2.3):Δ池快照由局终自动再生管线写入
# (生成器唯一核心 sim/cw_delta_pool_gen.py,ADR-0344),磁盘 ≠ HEAD 属设计稳态。
# 残余风险(该文件在飞编辑批闸不感知)由 sim/pool.py 快照指纹校验另行看守。
DEFAULT_EXEMPTION_PATHS: tuple[str, ...] = (
    'src/sr_od/application/currency_war/data/cw_delta_pool_data.py',
)

# 不一致类别
_KIND_MODIFIED = 'modified'  # 在 HEAD 中但工作树内容不同
_KIND_UNTRACKED = 'untracked'  # HEAD 中不存在(新文件)
_KIND_MISSING_ON_DISK = 'missing_on_disk'  # 已加载但盘上已被删(码只存在于进程内存)


@dataclass
class GateResult:
    """闸判定结果。ok=True 放行;False 时 mismatches 列出不一致码面。"""

    ok: bool
    scanned: int = 0
    mismatches: list[dict[str, str]] = field(default_factory=list)
    reason: str = ''


def collect_currency_war_module_files() -> list[Path]:
    """从 sys.modules 收集 currency_war 前缀已加载模块的文件集合(去重稳定序)。

    闸运行于 server 进程内,此刻 sys.modules 即 server 实际加载的模块面——
    这是「server 用的码」的最近真值近似(常驻进程无内存回读手段,见模块 docstring)。
    """
    files: set[Path] = set()
    for name, mod in list(sys.modules.items()):
        if not name.startswith(MODULE_PREFIX):
            continue
        f = getattr(mod, '__file__', None)
        if f:
            files.add(Path(f).resolve())
    return sorted(files)


def default_head_reader(repo_root: Path, rel: str) -> bytes | None:
    """读 git HEAD 中 rel 路径的原始内容;不在 HEAD 返回 None;git 故障抛 RuntimeError。

    git 二进制缺失(subprocess 抛 FileNotFoundError)统一包成 RuntimeError,
    让调用方只需面对单一故障类型即能 fail-closed。
    """
    try:
        # LC_ALL=C 固定 git 报文语言:untracked 判据认英文报文子串,非英文 locale
        # 的报文本地化会让判据失配(失配去向是 fail-closed 拦截——安全不受损,
        # 但「合法新文件」退化成硬拦,可用性受损;ADR-0581 §2.1)。
        _env = dict(os.environ)
        _env['LC_ALL'] = 'C'
        proc = subprocess.run(
            ['git', '-C', str(repo_root), 'show', f'HEAD:{rel}'],
            capture_output=True,
            env=_env,
        )
    except OSError as e:
        raise RuntimeError(f'git 不可用:{e}') from e
    if proc.returncode == 0:
        return proc.stdout
    # untracked 判定:git 对「HEAD 中无此路径」的报文随版本有两种形态——
    # "path 'x' does not exist in 'HEAD'" 与 "path 'x' exists on disk, but
    # not in 'HEAD'"(后者 = 实机演练实测形态);公共子串 in 'HEAD' 同判,
    # 误判会把合法新文件当 git 故障、闸永远走不到真比对。判据只认 rc=128
    # 且报文指认 HEAD 内缺失,其余故障仍 fail-closed 抛 RuntimeError。
    if proc.returncode == 128 and b"in 'HEAD'" in (proc.stderr or b''):
        return None
    raise RuntimeError(f'git show HEAD:{rel} 失败 rc={proc.returncode}: {(proc.stderr or b"")[:200]!r}')


def check_workspace_matches_head(
    module_files: list[Path] | None = None,
    repo_root: Path | None = None,
    head_reader: Callable[[Path, str], bytes | None] | None = None,
    exemption_paths: tuple[str, ...] = DEFAULT_EXEMPTION_PATHS,
) -> GateResult:
    """比对工作树内容与 git HEAD;不一致=拒绝起局。

    参数均可注入以便测试:module_files=None 时从 sys.modules 收集;
    repo_root=None 时取项目根;head_reader=None 时用真实 git。
    """
    root = repo_root if repo_root is not None else get_project_root()
    reader = head_reader if head_reader is not None else default_head_reader
    files = module_files if module_files is not None else collect_currency_war_module_files()

    mismatches: list[dict[str, str]] = []
    scanned = 0
    for f in files:
        try:
            rel = f.relative_to(root).as_posix()
        except ValueError:
            # 模块文件不在项目根下(安装态/编辑器缓存)——超出「工作树 vs HEAD」
            # 比对语义,如实跳过并计数
            scanned += 1
            continue
        if rel in exemption_paths:
            continue
        scanned += 1
        try:
            head = reader(root, rel)
        except (RuntimeError, OSError) as e:
            # OSError 兜底:注入的自定义 reader 抛文件系统级异常同样按
            # git 不可用处理——闸语义是安全闸,任何「无法比对」都宁拦勿放
            return GateResult(ok=False, scanned=scanned,
                              reason=f'git 不可用无法比对(fail-closed):{e}')
        try:
            disk_sha = _sha(_normalize_eol(f.read_bytes()))
        except OSError:
            # 已加载模块盘上被删:进程内存是唯一副本,盘/HEAD 对不上「即将
            # 运行的码」,按不一致拦(与 untracked 同级的结构脏)
            mismatches.append({'path': rel, 'kind': _KIND_MISSING_ON_DISK})
            continue
        if head is None:
            mismatches.append({'path': rel, 'kind': _KIND_UNTRACKED})
        elif _sha(_normalize_eol(head)) != disk_sha:
            mismatches.append({'path': rel, 'kind': _KIND_MODIFIED})
    if mismatches:
        return GateResult(ok=False, scanned=scanned, mismatches=mismatches,
                          reason=f'工作树与 HEAD 不一致 {len(mismatches)} 个文件')
    return GateResult(ok=True, scanned=scanned)


def _normalize_eol(b: bytes) -> bytes:
    """CRLF→LF 归一后再哈希(实机演练实测教训):Windows checkout
    (core.autocrlf)下盘上 CRLF、HEAD blob LF 是稳态而非编辑——raw 字节
    比对会对 git status 判净的文件全量假阳性,洁净树也被拦死,防线等于
    永久误报。归一口径与 git 自身一致:纯换行差异不算改动,内容改动
    (含换行之外的任何字节差)照拦。
    """
    return b.replace(b'\r\n', b'\n')


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()
