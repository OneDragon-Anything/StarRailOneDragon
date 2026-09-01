"""策略版本戳(match archive 二期②):「跑这局的代码版本」的取值单一源。

为什么在写入时点打戳:决策明细(v3_intention/candidate_scores/eval_breakdown
等)的语义随策略代码版本解读——装配端(可能在版本变更后离线跑)不能替运行
端作证,只有 recorder 写局终 summary 时点取到的版本才是「跑这局的版本」。
装配端(match_archive)只透传 runs 行里的戳,不重算;旧行无字段 = 版本未知。

两个维度:
- ``code_commit``:主仓 git 短哈希(best-effort;非 git 环境/离线打包 = '')。
- ``registry_fingerprint``:决策注册表(cw_registry.DEFAULT_REGISTRY)内容
  指纹——注册表是策略可调参数与显式注册结构的单一注入点,值变更即指纹变;
  哈希口径 = dataclass 全字段 asdict → JSON(sort_keys, set 排序列化)→ sha256
  前 12 位。不追 git 历史(工作区未提交改动也反映在指纹里,这正是想要的:
  「这局实际跑的参数」)。
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from sr_od.application.currency_war.kernel.cw_registry import DEFAULT_REGISTRY


def _find_repo_root() -> Path:
    """仓库根稳健定位(相对本模块向上搜索,不依赖 cwd)。

    锚点 = 含 ``pyproject.toml`` 的最近祖先(src-layout 单一锚点);找到即用,
    布局变化(目录加深/整体搬迁)自动跟随。找不到(非标准 checkout,如
    单独拷出 src)退回 src 层 parents[4] —— 此退路下 git 命令大概率失败,
    code_commit 按 best-effort 契约返回 '',不会串仓版本(退路只损可用性,
    不产错误值)。
    """
    module_path = Path(__file__).resolve()
    for cand in module_path.parents:
        if (cand / 'pyproject.toml').is_file():
            return cand
    # 兜底:telemetry → currency_war → application → sr_od → src
    return module_path.parents[4]


#: 仓库根(模块相对定位,见 _find_repo_root;禁用 cwd 依赖——server/GUI
#: 的工作目录不可信)
_REPO_ROOT: Path = _find_repo_root()


def code_commit() -> str:
    """当前 checkout 的 git 短哈希(best-effort;失败/非 git = '')。"""
    try:
        r = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return str(r.stdout).strip()
    except Exception:   # noqa: BLE001  观测 best-effort:版本戳失败不阻塞采集
        pass
    return ''


def _normalize(o: Any) -> Any:
    """递归规范化为可稳定 JSON 化的结构:dict 键 str 化(JSON 键域限制,
    注册表有 tuple 键的映射)+ 排序(set/frozenset 无序,repr 不稳定;
    dict 排序键输出)+ dataclass 转 dict。

    dataclass 分支的必要性:asdict 对 set/set 字段只做整体 deepcopy,
    不递归成员——集合装数据类时 asdict 后成员仍是实例,不在此转 dict
    就透传到终 json.dumps(无 default)再次炸。
    """
    if is_dataclass(o) and not isinstance(o, type):
        return _normalize(asdict(o))
    if isinstance(o, dict):
        return {str(k): _normalize(v) for k, v in sorted(
            ((str(k), v) for k, v in o.items()), key=lambda kv: kv[0])}
    if isinstance(o, (set, frozenset)):
        # 集合元素规范化后可能是 dict(含 dataclass)/混合类型,Python 原生
        # sorted 直接比较会 TypeError(炸点在局终写档,runs 行整行丢失)。
        # 先试原生排序(存量注册表=纯标量集合,输出与旧口径逐位一致,指纹
        # 值不因本修复跳变);不可比再退 JSON 串排序键(恒全序,default=repr
        # 兜住透传的任意对象)。
        elems = [_normalize(x) for x in o]
        try:
            return sorted(elems)
        except TypeError:
            return sorted(elems, key=lambda x: json.dumps(
                x, sort_keys=True, ensure_ascii=False, default=repr))
    if isinstance(o, (list, tuple)):
        return [_normalize(x) for x in o]
    return o


def registry_fingerprint() -> str:
    """决策注册表内容指纹(sha256 前 12 位;注册表值变更即变)。

    终 dumps 挂 default=repr 兜底:_normalize 不识别的任意对象(注册表
    未来字段的未知形态)序列化为 repr 而非 TypeError——调用点在局终
    写档且无异常保护,这里炸 = runs 行整行丢失(对局白跑无 summary)。
    """
    payload = json.dumps(_normalize(asdict(DEFAULT_REGISTRY)),
                         sort_keys=True, ensure_ascii=False, default=repr)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:12]


def current_version_stamp() -> dict[str, str]:
    """写入时点版本戳(runs.jsonl summary 行 / 档案 strategy_version 的源)。"""
    return {'code_commit': code_commit(),
            'registry_fingerprint': registry_fingerprint()}
