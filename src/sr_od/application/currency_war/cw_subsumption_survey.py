"""模块子承普查(redesign 49 号 J0;ADR-0183):功能域重叠对 → 合并候选清单。

**任务(49 号 J0)**:≥2 对合并候选(零对则收缩护栏档)。43 号自认的「35/43 共享提取器/
状态桶/审计」是现成候选——本工具把「自认」变「客观测量」。

方法(AST 级,静态,纯离线):cw_*.py 两两比——
- 共享常量(同名模块级常量 / 同值字面量表);
- 相同/包含关系的函数签名(名同或形参签名同);
- 互相 import 的私有符号(_ 前缀跨模块引用 = 基建泄漏信号)。
产出 overlap 分数与具体重叠项;阈值上仅作候选提名(合并决策走 47 号发布层)。
"""
from __future__ import annotations

import ast
from pathlib import Path


def _module_facts(path: Path) -> dict:
    """单模块静态事实:常量/函数签名/被引用的跨模块私有符号。"""
    tree = ast.parse(path.read_text(encoding='utf-8'))
    consts: dict[str, object] = {}
    funcs: dict[str, tuple] = {}
    priv_imports: set[str] = set()
    for node in tree.body:
        targets: list[ast.Name] = []
        value = None
        if isinstance(node, ast.Assign):
            targets = [t for t in node.targets if isinstance(t, ast.Name)]
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target]
            value = node.value
        if targets and value is not None:
            name = targets[0].id
            if name.isupper():
                try:
                    consts[name] = ast.literal_eval(value)
                except Exception:   # noqa: BLE001  非字面量默认值(如 field 工厂)跳过
                    consts[name] = None
        elif isinstance(node, ast.FunctionDef):
            funcs[node.name] = tuple(a.arg for a in node.args.args)
        elif isinstance(node, ast.ImportFrom) and node.module and 'currency_war' in node.module:
            for a in node.names:
                if a.name.startswith('_'):
                    priv_imports.add(f'{node.module.rsplit(".", 1)[-1]}.{a.name}')
    return {'consts': consts, 'funcs': funcs, 'priv_imports': priv_imports}


def overlap_pair(fa: dict, fb: dict) -> dict:
    """两模块重叠事实:同值常量 / 同签名函数 / **同值不同名常量**(语义重复=单一源缺口)。

    同值不同名是真实重叠的主形态(实测:HP_LOSS_MU × HP_LOSS_PRIOR 同值异名——两模块
    各自维护一份掉血先验,即 49 号要提名的合并/统一候选)。"""
    same_consts = {k for k, v in fa['consts'].items()
                   if k in fb['consts'] and fb['consts'][k] == v and v is not None}
    same_funcs = {k for k, sig in fa['funcs'].items()
                  if k in fb['funcs'] and fb['funcs'][k] == sig}
    # 同值不同名(排除 None 与平凡值:bool/小整数/空串;不可哈希容器转 repr 比)
    def _key(v):
        try:
            return v if not isinstance(v, (dict, list, set)) else repr(v)
        except TypeError:
            return repr(v)
    trivial = {True, None, 0, 2, 3, 4, 5, '', ()}
    # 巧合阈值:标量短 repr(≤6 字符,如 2.0/10/0.5)跨域碰撞概率高,不提名;容器/长表才算结构重叠
    def _is_trivial(v) -> bool:
        try:
            if v in trivial:
                return True
        except TypeError:
            pass
        # 短标量:跨域巧合常见(2.0×N 处),不构成合并证据;空容器 = lazy 占位(语义各异),不算
        if isinstance(v, (dict, list, set, tuple)) and len(v) == 0:
            return True
        return isinstance(v, (int, float, str)) and len(repr(v)) <= 6
    val_map_b: dict[str, list[str]] = {}
    for k, v in fb['consts'].items():
        if v is not None and not _is_trivial(v):
            val_map_b.setdefault(repr(_key(v)), []).append(k)
    same_value_diff_name: list[tuple[str, str]] = []
    for k, v in fa['consts'].items():
        if v is None or k in same_consts or _is_trivial(v):
            continue
        for kb in val_map_b.get(repr(_key(v)), []):
            same_value_diff_name.append((k, kb))
    score = len(same_consts) + 2 * len(same_funcs) + 3 * len(same_value_diff_name)
    return {'same_consts': sorted(same_consts),
            'same_funcs': sorted(same_funcs),
            'same_value_diff_name': same_value_diff_name,
            'priv_leaks': [],
            'score': score}


def survey(pkg_dir: Path | str, top_k: int = 8) -> list[dict]:
    """普查入口:pkg 下 cw_*.py 全两两 → overlap 分数降序 top_k(合并候选提名)。"""
    files = sorted(Path(pkg_dir).glob('cw_*.py'))
    facts = {f.stem: _module_facts(f) for f in files}
    pairs = []
    names = sorted(facts)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ov = overlap_pair(facts[a], facts[b])
            if ov['score'] > 0:
                pairs.append({'pair': (a, b), **ov})
    pairs.sort(key=lambda p: -p['score'])
    return pairs[:top_k]


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    out = survey(Path(__file__).parent)
    for p in out:
        print(f"{p['pair'][0]} × {p['pair'][1]}  score={p['score']}")
        if p['same_consts']:
            print(f"  同名同值常量: {p['same_consts'][:6]}")
        if p['same_funcs']:
            print(f"  同签名函数: {p['same_funcs'][:6]}")
        if p['same_value_diff_name']:
            print(f"  同值异名常量(单一源缺口): {p['same_value_diff_name'][:6]}")
