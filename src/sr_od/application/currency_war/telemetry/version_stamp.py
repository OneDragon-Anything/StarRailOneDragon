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
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sr_od.application.currency_war.kernel.cw_registry import DEFAULT_REGISTRY

#: 仓库根(telemetry/x.py → currency_war → application → sr_od → src → 根)
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]


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
    dict 排序键输出)。"""
    if isinstance(o, dict):
        return {str(k): _normalize(v) for k, v in sorted(
            ((str(k), v) for k, v in o.items()), key=lambda kv: kv[0])}
    if isinstance(o, (set, frozenset)):
        return sorted(_normalize(x) for x in o)
    if isinstance(o, (list, tuple)):
        return [_normalize(x) for x in o]
    return o


def registry_fingerprint() -> str:
    """决策注册表内容指纹(sha256 前 12 位;注册表值变更即变)。"""
    payload = json.dumps(_normalize(asdict(DEFAULT_REGISTRY)),
                         sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:12]


def current_version_stamp() -> dict[str, str]:
    """写入时点版本戳(runs.jsonl summary 行 / 档案 strategy_version 的源)。"""
    return {'code_commit': code_commit(),
            'registry_fingerprint': registry_fingerprint()}
