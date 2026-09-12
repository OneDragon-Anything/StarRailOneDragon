"""CW 资产完整性哨兵 v1(运行时资产基线对比;只报不修)。

## 背景(为什么要它)

OCR 模型 / avatar 脸库等运行时资产目录多次被外部清空(最近一例:onnx_ocr/ppocrv5
被清;模型目录 `models/` 在 .gitignore 内、git 恢复不了,每次靠人工/框架下载链
事后恢复,恢复前运行时 OCR 链直接断)。本哨兵对这批资产做**基线对比看门**:
首跑落基线快照,之后每轮扫描对比,变更分级报警。纯 watchdog 零副作用——
**禁自恢复下载**,恢复仍走人工/框架链,哨兵只报不修。

## 监控面(路径反查自识别链 load 处,出处见 build_targets 各 target 的 source)

- OCR 模型:`assets/models/onnx_ocr/ppocrv5`(缺省在用档,**实测是 junction 指向
  外部模型库**,junction 悬空/目标侧被清是真实清空形态,必须能抓)+ `ppocrv6`
  (GUI 可选档,非缺省 → watch 档不即退)。关键文件清单 = det/rec/cls/simfang.ttf
  + `<模型名>_dict.txt`(语义 = onnx_ocr_matcher.get_final_file_list 下载完成判定)。
- CW 立绘 SIFT 模板库 `assets/template/currency_war/portrait_plaza`(唯一库,git 管内)
- CW 首领头像库 `assets/template/currency_war/boss_avatar`(git 管内)

## 分级(学 cw_sentinel v5.2 的 HIT 分级形态)

- **critical 即退**:`[ASSET-HIT]` 打印 + 证据文件 + **exit 3**(非 0 = 警报,
  经会话后台任务信道送达编排者)。判 critical 的形态(仅 level=critical 监控面):
  ①目录丢失(含 junction 悬空——基线在、现在 exists=False);②目录被清空
  (文件数 >0 → 0);③关键模型文件缺失(半清态:目录在、det/rec/dict 没了)。
- **general 驻留续侦**:`[ASSET-HIT-CONT]` 首见打印 + 证据整体重写
  (`asset_hit_alert.md`,纪元内同签名去重,恢复时 `[ASSET-OK]` 收账)——
  非退出事件,消费方核读证据即可,不重武。覆盖:部分文件缺失(非关键)/
  新文件/大小变化/链接形态变化/目录恢复出现。
- watch 档监控面(ppocrv6)任何变更都只走 general:它丢了不破运行时,只提示。

## 快照粒度(为什么轻量)

存在性 + 关键文件清单 + 文件数 + 逐文件大小。不做校验和:mtime 在恢复/下载后
不稳定不能作锚,校验和能多抓「同大小内容替换」形态,但逐轮全量哈希 50MB+ 的
CPU 成本对 60s 轮询不划算,且已实证的清空形态都是「数量/大小级」变化,大小
快照已覆盖。

## 与哨兵族的接缝

- 单实例锁 `cw_asset_sentinel.lock`(形态同 cw_sentinel._acquire_lock,陈旧锁自愈);
- 活性心跳 `cw_asset_sentinel.pos`(每轮无条件写,值 = unix 秒,消费方按 mtime 判活,
  同 runtime-ops「哨兵活性回读」口径);
- 查旧/杀净经 `tools/cw/rewatch.py`(其 WATCHER_CMD_NAMES 已纳管本脚本)。

## 用法(PowerShell,项目根;武装 = 会话后台任务信道起,退出码即警报)

  $env:PYTHONUTF8='1'; uv run python tools/cw/cw_asset_sentinel.py            # 驻留(缺省 60s/轮)
  uv run python tools/cw/cw_asset_sentinel.py --once                          # 单轮体检即退
  uv run python tools/cw/cw_asset_sentinel.py --rebaseline                    # 显式重建基线(可穿越损坏态)
  uv run python tools/cw/cw_asset_sentinel.py --interval 300                  # 巡检间隔(秒)

环境变量重定向(自测/多树隔离):CW_ASSET_SENTINEL_ROOT(资产根,缺省仓库根)、
CW_ASSET_SENTINEL_BASELINE / _EVIDENCE / _LOCK / _POS(四个运行态文件路径)、
CW_ASSET_SENTINEL_INTERVAL(巡检间隔秒)。
--selftest:内置合成树回归(不碰真实资产与 .debug)。

退出码:0=干净/正常退出;2=基线损坏等配置态错误(仅无 --rebaseline 时,损坏态
显式重建走 --rebaseline 穿越重建);3=[ASSET-HIT]。
"""
import argparse
import contextlib
import json
import os
import shutil
import stat
import sys
import tempfile
import time
from pathlib import Path

import psutil

# 本模块会被测试仓进程内 import(pytest 捕获的 stdout 无 reconfigure),
# 与哨兵族子进程直跑两种形态都要活 → 抑制不支持态而非裸调
with contextlib.suppress(AttributeError, ValueError):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

# 仓库根(本脚本在 tools/cw/ 下);env 重定向仅供自测/多树隔离
REPO_ROOT = Path(os.environ.get(
    'CW_ASSET_SENTINEL_ROOT', str(Path(__file__).resolve().parents[2])))
WATCH_DIR = REPO_ROOT / '.debug' / 'temp' / 'currency_war'
BASELINE_PATH = Path(os.environ.get(
    'CW_ASSET_SENTINEL_BASELINE', str(WATCH_DIR / 'asset_baseline.json')))
EVIDENCE_PATH = Path(os.environ.get(
    'CW_ASSET_SENTINEL_EVIDENCE', str(WATCH_DIR / 'asset_hit_alert.md')))
LOCK_PATH = Path(os.environ.get(
    'CW_ASSET_SENTINEL_LOCK', str(WATCH_DIR / 'cw_asset_sentinel.lock')))
POS_PATH = Path(os.environ.get(
    'CW_ASSET_SENTINEL_POS', str(WATCH_DIR / 'cw_asset_sentinel.pos')))
POLL_SEC = float(os.environ.get('CW_ASSET_SENTINEL_INTERVAL', 60))

# 即退退出码:3 与家族内 rewatch 的 1(核岗失败)/2(杀净失败)区分,
# 任何非 0 都被会话后台任务信道当警报送达
EXIT_CRITICAL = 3

SNAPSHOT_VERSION = 1
# Python 3.11 无 Path.is_junction();junction 探测走 lstat 的 reparse tag
# (Windows 专属属性,其他平台恒 0 → 恒判「非链接」,探测天然可移植)
_REPARSE_MOUNT_POINT = getattr(stat, 'IO_REPARSE_TAG_MOUNT_POINT', 0xA000_0003)

# OCR 关键模型文件(语义 = onnx_ocr_matcher.get_final_file_list 的下载完成判定
# 清单;字典文件按模型名推导,同 get_ocr_model_dict_name 的 *_dict.txt 扫描语义)
OCR_KEY_FILES: tuple[str, ...] = ('det.onnx', 'rec.onnx', 'cls.onnx', 'simfang.ttf')


def build_targets() -> dict[str, dict]:
    """监控面清单(单一源)。路径反查自识别链 load 处,出处记在各 target 的
    source(持久索引:文件路径 + 符号名);增删监控面只改这里,基线按
    target key 对齐,清单变化经 spec_drift 变更可见。"""
    targets: dict[str, dict] = {}
    for model_name, level in (('ppocrv5', 'critical'), ('ppocrv6', 'watch')):
        targets[f'ocr_{model_name}'] = {
            'label': f'OCR 模型 {model_name}',
            'path': ['assets', 'models', 'onnx_ocr', model_name],
            # ppocrv5 = BasicModelConfig.ocr 缺省值(实际加载档,丢 = OCR 链断);
            # ppocrv6 = GUI 可选档(丢不破缺省运行时)→ watch 档
            'level': level,
            'key_files': list(OCR_KEY_FILES) + [f'{model_name}_dict.txt'],
            'source': 'one_dragon/base/matcher/ocr/onnx_ocr_matcher.py'
                      '(get_ocr_model_dir/get_final_file_list)+'
                      'one_dragon/base/config/basic_model_config.py(BasicModelConfig.ocr)',
        }
    targets['cw_portrait_plaza'] = {
        'label': 'CW 立绘 SIFT 模板库(唯一库)',
        'path': ['assets', 'template', 'currency_war', 'portrait_plaza'],
        'level': 'critical',
        # 无单文件关键清单:库内任一角色模板缺失只降该角色识别率(运行不断),
        # 走 general 证据;目录消失/清空才是 critical
        'key_files': [],
        'source': 'sr_od/application/currency_war/obs/currency_war_char_id.py'
                  '(load_avatar_templates 生产路径;cw_identity_obs/'
                  'cw_op_deploy/cw_screen_partner 同源加载)',
    }
    targets['cw_boss_avatar'] = {
        'label': 'CW 首领头像 SIFT 模板库',
        'path': ['assets', 'template', 'currency_war', 'boss_avatar'],
        'level': 'critical',
        'key_files': [],
        'source': 'sr_od/application/currency_war/obs/cw_observation.py + '
                  'cw_node_reader.py(boss 大图标 SIFT 对拍库)',
    }
    return targets


def _probe_reparse_dir(path: Path) -> tuple[bool, str | None]:
    """探测目录本体是否 junction/mount point;返回 (是否链接, 链接目标原文)。
    目标悬空时 lstat 仍成功(链接项本身在),readlink 仍可取目标原文——
    「junction 悬空」由此与「目录真没了」区分(前者可修链接,后者要重下)。"""
    try:
        st = os.lstat(path)
    except OSError:
        return False, None
    if getattr(st, 'st_reparse_tag', 0) != _REPARSE_MOUNT_POINT:
        return False, None
    try:
        return True, os.readlink(path)
    except OSError:
        return True, None


def _list_files(root: Path) -> dict[str, int]:
    """递归列出 root 下全部普通文件 → {相对路径(POSIX 斜杠): 大小字节}。

    嵌套重解析点(junction/符号链接目录)不递归:当前监控面无嵌套链接,
    递归进外部链接有环与越界风险,遇跳过(其丢失表现为 file_missing,
    不会漏报目录级清空)。"""
    out: dict[str, int] = {}
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            with os.scandir(d) as it:
                entries = list(it)
        except OSError:
            continue   # 无权限/竞态删除:该子树按空处理,下轮扫描自愈
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    if getattr(entry.stat(follow_symlinks=False),
                               'st_reparse_tag', 0) == _REPARSE_MOUNT_POINT:
                        continue
                    stack.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    rel = Path(entry.path).relative_to(root).as_posix()
                    out[rel] = entry.stat(follow_symlinks=False).st_size
            except OSError:
                continue
    return out


def scan_target(root: Path, spec: dict) -> dict:
    """单监控面快照(轻量:存在性+链接形态+逐文件大小)。spec 的 level/
    key_files/source 一并嵌入快照——diff 因此是纯函数(只吃两个快照 dict),
    基线自描述,不依赖生成时的代码版本。"""
    abs_path = root.joinpath(*spec['path'])
    is_link, link_target = _probe_reparse_dir(abs_path)
    # exists 跟随 junction:悬空 junction → False(与 is_link=True 组合即悬空态)
    exists = abs_path.exists()
    snap: dict = {
        'path': '/'.join(spec['path']),
        'label': spec['label'],
        'level': spec['level'],
        'key_files': list(spec['key_files']),
        'source': spec['source'],
        'exists': exists,
        'is_link': is_link,
        'link_target': link_target,
        'files': {},
        'file_count': 0,
        'total_bytes': 0,
    }
    if exists:
        files = _list_files(abs_path)
        snap['files'] = files
        snap['file_count'] = len(files)
        snap['total_bytes'] = sum(files.values())
    return snap


def snapshot_all(root: Path) -> dict:
    """全监控面快照(基线与每轮扫描同构,差异只在 created_at)。"""
    return {
        'version': SNAPSHOT_VERSION,
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'root': str(root),
        'targets': {key: scan_target(root, spec)
                    for key, spec in sorted(build_targets().items())},
    }


def _finding(kind: str, key: str, rel: str, detail: str, severity: str) -> dict:
    return {'kind': kind, 'key': key, 'path': rel, 'detail': detail,
            'severity': severity}


def finding_signature(finding: dict) -> str:
    """纪元内同签名去重键。size_changed 不含大小值:同文件反复变大小算同一
    签名(首见必报、复见静默),防高频写文件每轮刷屏;证据文件里始终有最新值。"""
    return f"{finding['kind']}|{finding['key']}|{finding['path']}"


def has_critical(findings: list[dict]) -> bool:
    return any(f['severity'] == 'critical' for f in findings)


def diff_targets(baseline: dict, current: dict) -> list[dict]:
    """基线 vs 当前快照 → 变更 findings(纯函数,无 IO)。

    severity 规则:critical 仅两种来源——①level=critical 监控面的目录级
    丢失/清空(dir_missing/dir_emptied);②critical 监控面的关键文件缺失。
    watch 档与一般文件级变更一律 general(驻留续侦)。"""
    findings: list[dict] = []
    base_targets = baseline.get('targets', {})
    curr_targets = current.get('targets', {})
    for key in sorted(set(base_targets) | set(curr_targets)):
        findings.extend(_diff_one(key, base_targets.get(key), curr_targets.get(key)))
    return findings


def _diff_one(key: str, base: dict | None, curr: dict | None) -> list[dict]:
    if base is None or curr is None:
        # 同版本代码监控面恒定;单侧缺失 = 基线由不同监控面版本的代码生成,
        # 一般变更(--rebaseline 收敛,详见 finding detail)
        return [_finding('spec_drift', key, '',
                         '基线与当前扫描的监控面清单不一致(基线跨版本?)', 'general')]
    out: list[dict] = []
    level = curr.get('level') or base.get('level') or 'watch'

    def sev(bump: bool) -> str:
        """bump=True 的形态在 critical 档监控面上升为即退;watch 档恒 general。"""
        return 'critical' if (bump and level == 'critical') else 'general'

    if base.get('exists') and not curr.get('exists'):
        link_note = (f'(junction {base.get("link_target")} 悬空?)'
                     if base.get('is_link') else '')
        return [_finding('dir_missing', key, base['path'],
                         f'目录丢失{link_note}', sev(True))]
    if (not base.get('exists')) and curr.get('exists'):
        return [_finding('dir_restored', key, curr['path'],
                         '目录出现(基线时刻缺失)', 'general')]
    if not curr.get('exists'):
        return []   # 基线缺失且当前仍缺失:持续缺失不逐轮重复报(基线已如实记录)
    if (base.get('is_link') != curr.get('is_link')
            or base.get('link_target') != curr.get('link_target')):
        out.append(_finding(
            'link_changed', key, curr['path'],
            f'链接形态变化 is_link {base.get("is_link")}→{curr.get("is_link")}, '
            f'target {base.get("link_target")}→{curr.get("link_target")}', 'general'))
    base_files: dict = base.get('files', {})
    curr_files: dict = curr.get('files', {})
    key_files = set(curr.get('key_files') or base.get('key_files') or [])
    if curr_files and base.get('file_count', 0) == 0:
        # 空目录回填与 dir_emptied 对称:目录级翻转只在目录级报一条,
        # 不再逐文件重复 file_added(同因噪声)
        out.append(_finding('dir_refilled', key, curr['path'],
                            f'空目录出现内容({curr["file_count"]} 文件)', 'general'))
        return out
    if base_files and not curr_files:
        # 目录级清空吞并逐文件缺失(每文件再报一条是同因噪声,证据一条够定位)
        out.append(_finding('dir_emptied', key, curr['path'],
                            f'目录被清空(基线 {base.get("file_count")} → 0 文件)',
                            sev(True)))
        return out
    for name in sorted(set(base_files) - set(curr_files)):
        is_key = name in key_files
        out.append(_finding(
            'file_missing', key, name,
            f'文件缺失{"(关键模型文件)" if is_key else ""}',
            sev(is_key)))
    for name in sorted(set(curr_files) - set(base_files)):
        out.append(_finding('file_added', key, name,
                            f'新文件({curr_files[name]} 字节)', 'general'))
    for name in sorted(set(base_files) & set(curr_files)):
        if base_files[name] != curr_files[name]:
            out.append(_finding('size_changed', key, name,
                                f'大小变化 {base_files[name]} → {curr_files[name]} 字节',
                                'general'))
    return out


def evidence_body(findings: list[dict], first_seen: dict[str, str]) -> list[str]:
    """证据文件正文(整体重写式,同 cw_sentinel v5.2 CONT 证据形态:
    当前全部未决签名 + 首见时刻 + 处置指引)。"""
    criticals = [f for f in findings if f['severity'] == 'critical']
    generals = [f for f in findings if f['severity'] == 'general']
    lines = [
        f'- 快照时刻: {time.strftime("%Y-%m-%d %H:%M:%S")}',
        f'- critical 数: {len(criticals)};一般变更数: {len(generals)}',
        '',
        '## 变更明细(kind|监控对象|路径: 详情[严重度] [首见时刻])',
    ]
    for f in findings:
        seen = first_seen.get(finding_signature(f))
        mark = f' [首见 {seen}]' if seen else ''
        lines.append(f'- {f["kind"]}|{f["key"]}|{f["path"]}: '
                     f'{f["detail"]}[{f["severity"]}]{mark}')
    lines += [
        '',
        '## 判读与处置(哨兵只报不修,恢复走既有链路)',
        '1. OCR 模型目录/关键文件缺失 → 框架下载链恢复(GUI 模型页;'
        'OnnxOcrMatcher 下载器),完成后 --rebaseline 收敛基线',
        '2. 模板库(portrait_plaza/boss_avatar)缺损 → git 管内资产,'
        '`git status assets/template` 核对后 checkout 恢复',
        '3. junction 悬空/链接形态变化 → 先看明细里的 link_target(外部模型库侧'
        '被清或链接被删),修链接或恢复库本体后 --rebaseline',
        '4. 一般变更(新文件/大小变化/非关键缺失)非必处置:来路正当(版本更新、'
        '重采)即 --rebaseline 吸收;来路不明按事故排查',
    ]
    return lines


def write_evidence(path: Path, title: str, body: list[str]) -> None:
    """证据落盘(失败只打印不抛,报警不能因 IO 丢;形态同 cw_sentinel)。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join([f'# {title}', ''] + body) + '\n', encoding='utf-8')
    except OSError as e:
        print(f'[asset-sentinel] 证据文件写入失败: {e!r}', flush=True)


def load_baseline(path: Path) -> dict | None:
    """读基线;不存在返 None(调用方走首跑生成)。损坏 → exit 2 禁静默重建:
    基线是对比锚,坏了自动重建会把「已发生的清空」钉成新正常态。"""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        print(f'[asset-sentinel] 基线文件损坏({e!r})——基线是对比锚,禁静默重建;'
              f'确认资产恢复完成后用 --rebaseline 显式重建', flush=True)
        raise SystemExit(2) from e
    if not isinstance(data, dict) or not isinstance(data.get('targets'), dict):
        print('[asset-sentinel] 基线文件结构非法(缺 targets)——同上,'
              '用 --rebaseline 显式重建', flush=True)
        raise SystemExit(2)
    return data


def save_baseline(path: Path, snapshot: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True),
                    encoding='utf-8')


def _acquire_lock() -> bool:
    """单实例锁(形态同 cw_sentinel):活实例在岗 → False;陈旧锁(pid 死/
    被复用为非本脚本进程)自动覆盖。"""
    if LOCK_PATH.exists():
        try:
            old = psutil.Process(int(LOCK_PATH.read_text().strip()))
            if 'cw_asset_sentinel' in ' '.join(old.cmdline()).lower():
                print(f'[asset-sentinel] 已有实例在岗 pid={old.pid},'
                      f'本次退出(防重复武装)', flush=True)
                return False
        except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied,
                psutil.ZombieProcess):
            pass   # 陈旧锁 → 覆盖
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.write_text(str(os.getpid()), encoding='utf-8')
    return True


def process_round(baseline: dict, snapshot: dict,
                  outstanding: dict[str, tuple[str, str]]) -> int | None:
    """一轮对比+分级处置(快照由调用方扫描传入,纯决策层可离线测)。
    返回 None=继续驻留;返回 int=即退退出码。

    critical → 逐条 [ASSET-HIT] + 证据 + EXIT_CRITICAL;general 首见 →
    [ASSET-HIT-CONT] + 证据整体重写(纪元内同签名去重);已恢复签名 →
    [ASSET-OK] 收账 + 证据重写。outstanding 原地维护(签名 → (摘录, 首见时刻))。"""
    findings = diff_targets(baseline, snapshot)
    if has_critical(findings):
        for f in (x for x in findings if x['severity'] == 'critical'):
            print(f'[ASSET-HIT] {f["key"]}|{f["path"]}: {f["detail"]}', flush=True)
        write_evidence(EVIDENCE_PATH, '[ASSET-HIT] 关键资产缺失(即退报警)',
                       evidence_body(findings, outstanding))
        return EXIT_CRITICAL
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    general_sigs = {finding_signature(f) for f in findings}
    new_general = [f for f in findings if finding_signature(f) not in outstanding]
    resolved = [sig for sig in outstanding if sig not in general_sigs]
    for f in new_general:
        sig = finding_signature(f)
        outstanding[sig] = (f'{f["key"]}|{f["path"]}: {f["detail"]}', now)
        print(f'[ASSET-HIT-CONT] {f["detail"]}({sig})', flush=True)
    for sig in resolved:
        excerpt, _t0 = outstanding.pop(sig)
        print(f'[ASSET-OK] 已恢复: {excerpt}', flush=True)
    if new_general or resolved:
        write_evidence(EVIDENCE_PATH, '[ASSET-HIT-CONT] 一般资产变更证据(驻留续侦)',
                       evidence_body(findings, outstanding))
    return None


def _baseline_summary(snapshot: dict) -> str:
    parts = []
    for key, t in snapshot.get('targets', {}).items():
        state = f'{t["file_count"]} 文件' if t.get('exists') else '缺失'
        link = '(junction)' if t.get('is_link') else ''
        parts.append(f'{key}={state}{link}')
    return ' '.join(parts)


def _selftest() -> int:
    """内置回归:合成树上走「基线生成 → 各类变更 → 对比分级 → 恢复收账」全链。
    零真实资产/零 .debug 写(证据路径临时重定向到 OS 临时目录,finally 还原)。"""
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = '') -> None:
        print(f'  {"✅" if ok else "❌"} {name}{(": " + detail) if detail and not ok else ""}',
              flush=True)
        if not ok:
            failures.append(name)

    tmp = Path(tempfile.mkdtemp(prefix='cw_asset_selftest_'))
    global EVIDENCE_PATH
    saved_evidence = EVIDENCE_PATH
    EVIDENCE_PATH = tmp / 'evidence.md'
    try:
        # 合成 OCR 模型面(目录结构仿 ppocrv5:关键件+普通件)
        model_dir = tmp / 'assets' / 'models' / 'onnx_ocr' / 'ppocrv5'
        model_dir.mkdir(parents=True)
        for name, size in (('det.onnx', 100), ('rec.onnx', 200),
                           ('ppocrv5_dict.txt', 10), ('extra.bin', 5)):
            (model_dir / name).write_bytes(b'x' * size)
        spec = {'label': 't', 'path': ['assets', 'models', 'onnx_ocr', 'ppocrv5'],
                'level': 'critical',
                'key_files': ['det.onnx', 'rec.onnx', 'ppocrv5_dict.txt'],
                'source': 'selftest'}

        def scan_now() -> dict:
            return {'targets': {'t': scan_target(tmp, spec)}}

        snap1 = scan_target(tmp, spec)
        check('基线扫描清点', snap1['file_count'] == 4 and snap1['total_bytes'] == 315,
              f'got {snap1["file_count"]}/{snap1["total_bytes"]}')
        # 满配基线(4 件)在此后各场景复用为对比锚;每次先抓基线再变更,
        # 否则基线与扫描同态,diff 恒空(场景全失效)
        full_base = {'targets': {'t': snap1}}

        # ① 关键文件缺失 → critical
        (model_dir / 'det.onnx').unlink()
        f1 = diff_targets(full_base, scan_now())
        check('关键文件缺失=critical', has_critical(f1)
              and f1[0]['kind'] == 'file_missing' and f1[0]['severity'] == 'critical')
        (model_dir / 'det.onnx').write_bytes(b'x' * 100)   # 还原,场景隔离

        # ② 非关键文件缺失 → general;签名稳定(复见同签名)
        (model_dir / 'extra.bin').unlink()
        f2 = diff_targets(full_base, scan_now())
        g2 = [f for f in f2 if f['kind'] == 'file_missing']
        check('非关键缺失=general', len(g2) == 1 and g2[0]['severity'] == 'general'
              and not has_critical(f2))
        check('同变更签名稳定', (finding_signature(g2[0])
                              == finding_signature({'kind': 'file_missing', 'key': 't',
                                                    'path': 'extra.bin'})))
        (model_dir / 'extra.bin').write_bytes(b'x' * 5)   # 还原

        # ③ 清空目录 → critical(dir_emptied,且吞并逐文件缺失不双报)
        for p in list(model_dir.iterdir()):
            p.unlink()
        f3 = diff_targets(full_base, scan_now())
        check('清空目录=critical', has_critical(f3)
              and any(f['kind'] == 'dir_emptied' for f in f3)
              and not any(f['kind'] == 'file_missing' for f in f3))

        # ④ 空目录基线下回填 → dir_refilled general;满配基线下新增文件 → general
        empty_base = {'targets': {'t': scan_target(tmp, spec)}}   # 目录此刻为空
        (model_dir / 'rec.onnx').write_bytes(b'y' * 200)
        f4 = diff_targets(empty_base, scan_now())
        check('空目录回填=general', not has_critical(f4)
              and any(f['kind'] == 'dir_refilled' for f in f4))
        for name, size in (('det.onnx', 100), ('ppocrv5_dict.txt', 10),
                           ('extra.bin', 5)):
            (model_dir / name).write_bytes(b'x' * size)
        (model_dir / 'new.bin').write_bytes(b'n' * 7)   # 满配态外新文件
        f4b = diff_targets(full_base, scan_now())
        added = [f for f in f4b if f['kind'] == 'file_added']
        check('新文件=general', not has_critical(f4b) and len(added) == 1
              and added[0]['path'] == 'new.bin')

        # ⑤ 大小变化 → general(满配基线含 new.bin 缺席,一并 general)
        (model_dir / 'ppocrv5_dict.txt').write_bytes(b'z' * 20)
        f5 = diff_targets(full_base, scan_now())
        check('大小变化=general', not has_critical(f5)
              and any(f['kind'] == 'size_changed' and f['path'] == 'ppocrv5_dict.txt'
                      for f in f5))
        # ⑥ 基线缺失的目录恢复出现 → dir_restored general
        empty_spec = {'label': 'e', 'path': ['nowhere'], 'level': 'critical',
                      'key_files': [], 'source': 'selftest'}
        b_missing = {'targets': {'e': scan_target(tmp, empty_spec)}}
        (tmp / 'nowhere').mkdir()
        f6 = diff_targets(b_missing, {'targets': {'e': scan_target(tmp, empty_spec)}})
        check('目录恢复=general', not has_critical(f6)
              and any(f['kind'] == 'dir_restored' for f in f6))

        # ⑦ process_round 驻留/收账/即退全链(证据重定向到 tmp)
        round_dir = tmp / 'watched'
        round_dir.mkdir()
        round_spec = {'label': 'w', 'path': ['watched'], 'level': 'critical',
                      'key_files': [], 'source': 'selftest'}
        round_base = {'targets': {'w': scan_target(tmp, round_spec)}}
        outstanding: dict[str, tuple[str, str]] = {}
        (round_dir / 'a.txt').write_text('hello')
        rc = process_round(round_base, {'targets': {'w': scan_target(tmp, round_spec)}},
                           outstanding)
        check('一般变更轮驻留', rc is None and len(outstanding) == 1, f'rc={rc}')
        check('证据文件落盘', EVIDENCE_PATH.exists())
        (round_dir / 'a.txt').unlink()
        rc2 = process_round(round_base, {'targets': {'w': scan_target(tmp, round_spec)}},
                            outstanding)
        check('恢复轮收账+继续驻留', rc2 is None and len(outstanding) == 0, f'rc={rc2}')
        round_dir.rmdir()   # 目录消失(critical 档)= dir_missing
        rc3 = process_round(round_base, {'targets': {'w': scan_target(tmp, round_spec)}},
                            outstanding)
        check('critical 轮返回即退码', rc3 == EXIT_CRITICAL, f'got {rc3}')

        # ⑧ junction 探测:真 junction 建立与悬空识别(Windows 可达形态)
        try:
            import _winapi
            store = tmp / 'store' / 'm1'
            store.mkdir(parents=True)
            (store / 'a.onnx').write_bytes(b'z')
            link = tmp / 'link_m1'
            _winapi.CreateJunction(str(store), str(link))
            link_spec = {'label': 't', 'path': ['link_m1'], 'level': 'critical',
                         'key_files': [], 'source': 'selftest'}
            ls1 = scan_target(tmp, link_spec)
            check('junction 识别+穿透清点', ls1['is_link'] and ls1['file_count'] == 1,
                  f'is_link={ls1["is_link"]} n={ls1["file_count"]}')
            shutil.rmtree(store)
            ls2 = scan_target(tmp, link_spec)
            check('junction 悬空=exists False 且 is_link True',
                  (not ls2['exists']) and ls2['is_link'])
            fb = {'targets': {'t': ls1}}
            fc = {'targets': {'t': ls2}}
            check('悬空判 critical(dir_missing)',
                  has_critical(diff_targets(fb, fc)))
        except (ImportError, OSError) as e:
            print(f'  ⏭️ junction 用例跳过(平台不支持: {e!r})', flush=True)
    finally:
        EVIDENCE_PATH = saved_evidence
        shutil.rmtree(tmp, ignore_errors=True)
    print(f'[selftest] {"全部通过" if not failures else f"失败 {len(failures)} 例: {failures}"}',
          flush=True)
    return 0 if not failures else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description='CW 资产完整性哨兵(运行时资产基线对比;只报不修)')
    parser.add_argument('--interval', type=float, default=None,
                        help=f'巡检间隔秒(缺省读 CW_ASSET_SENTINEL_INTERVAL,'
                             f'再缺省 {POLL_SEC})')
    parser.add_argument('--once', action='store_true',
                        help='单轮体检即退(0=干净,3=ASSET-HIT;首跑先落基线)')
    parser.add_argument('--rebaseline', action='store_true',
                        help='以当前状态重建基线(资产恢复/正当变更后收敛用)')
    parser.add_argument('--selftest', action='store_true',
                        help='合成树内置回归(不碰真实资产与 .debug)')
    args = parser.parse_args()

    if args.selftest:
        sys.exit(_selftest())

    if not _acquire_lock():
        sys.exit(0)

    # 显式重建(--rebaseline)必须能穿越损坏基线:损坏态唯一出路就是重建,
    # 若先 load 会在损坏时 exit 2 把重建口也堵死——报错与证据指引都说
    # 「用 --rebaseline 重建」,堵死即指引自指死循环(T-173-r1 验收缺陷 A)。
    # 无 --rebaseline 时损坏仍经 load_baseline exit 2 拒静默重建(防把已
    # 发生的清空钉成新正常态,该语义不变)。
    baseline = None if args.rebaseline else load_baseline(BASELINE_PATH)
    if args.rebaseline or baseline is None:
        snapshot = snapshot_all(REPO_ROOT)
        save_baseline(BASELINE_PATH, snapshot)
        baseline = snapshot
        verb = '重建' if args.rebaseline else '生成'
        print(f'[ASSET-BASELINE] 基线{verb}: {BASELINE_PATH}', flush=True)
    print(f'[asset-sentinel] armed 监控 {_baseline_summary(baseline)}'
          f'(间隔 {args.interval if args.interval is not None else POLL_SEC}s;'
          f'基线={BASELINE_PATH})', flush=True)

    outstanding: dict[str, tuple[str, str]] = {}
    while True:
        snapshot = snapshot_all(REPO_ROOT)
        code = process_round(baseline, snapshot, outstanding)
        # 活性心跳无条件每轮写(值 = unix 秒,消费方按 mtime 判活,
        # 同 cw_sentinel.pos 口径——哨兵活性回读纪律)
        POS_PATH.parent.mkdir(parents=True, exist_ok=True)
        POS_PATH.write_text(str(int(time.time())), encoding='utf-8')
        if code is not None:
            sys.exit(code)
        if args.once:
            print('[asset-sentinel] --once 单轮完成,干净退出', flush=True)
            sys.exit(0)
        time.sleep(args.interval if args.interval is not None else POLL_SEC)


if __name__ == '__main__':
    main()
