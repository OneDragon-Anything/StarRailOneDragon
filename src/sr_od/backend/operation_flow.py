"""operation 节点流转的静态提取、诊断与渲染。

类级纯反射读取 ``@operation_node`` / ``@node_from`` 挂在函数属性上的注解,
不实例化任何 operation:实例化路径的编排校验要等 ``execute`` 触发
``Operation._init_network`` 才执行(写错 ``from_name`` 要跑起来才炸),且
``SrOperation.__init__`` 会构造 ``OpenAndEnterGame`` 等副作用依赖。
提取语义逐条镜像 ``Operation._analyse_node_annotations`` /
``Operation._init_network`` / ``Operation._get_next_node``,让静态图与运行时
行为一致;静态比运行时多做的只有结构诊断(不可达 / 兜底边冗余 / 边挂非节点)。

供 ``describe_operation_flow``(MCP / HTTP 同契约)与全量回归测试共用,
单一提取源。
"""
import inspect
from collections import deque
from dataclasses import dataclass

from one_dragon.base.operation.operation_edge import OperationEdgeDesc
from one_dragon.base.operation.operation_node import OperationNode
from sr_od.backend.operation_registry import (
    _short_name_not_found_error,
    match_short_name,
    resolve_op_class,
)

_NOTES: list[str] = [
    '无出边节点：返回成功即整个 op 成功、返回失败即整个 op 失败',
    '框架是否在起点前注入「检测游戏窗口→打开并进入游戏」前缀取决于实例构造参数 need_check_game_win（默认 True），本图未画出',
]


@dataclass
class _NodeEntry:
    """静态扫描得到的一个节点条目。

    同名节点会产出多条条目(payload 全保留、靠 method 区分),图论键控一律
    用 ``cn`` —— 与运行时 ``_node_edges_map`` / ``_node_map`` 的键一致。
    """

    cn: str
    method: str
    annotation: OperationNode


@dataclass
class _RawEdge:
    """边注解的原始形态(from 未解析、ignore_status 未归一)。"""

    from_name: str
    to_cn: str
    success: bool
    status: str | None
    ignore_status_desc: bool


@dataclass
class _EdgeEntry:
    """解析后的边。

    ``from_cn`` 为 None 表示断名边(``from_name`` 匹配不到任何节点);
    ``ignore_status`` 已按 ``OperationEdge.__init__`` 的归一语义处理。
    """

    from_name: str
    from_cn: str | None
    to_cn: str
    success: bool
    status: str | None
    ignore_status: bool


@dataclass
class _Analysis:
    """提取主流程的中间产物(渲染与 payload 共用)。"""

    start_cn: str | None
    """唯一起点名;multiple_start / no_start 时为 None。"""

    start_cns: list[str]
    """BFS 起点集(cn 字母序):唯一起点时单元素;自动判定多起点时全部入度 0 节点。"""

    cn_order: list[str]
    """节点输出序:可达部分 BFS 首次发现序 + 不可达部分 cn 字母序垫底。"""

    grouped: dict[str, list[_NodeEntry]]
    ordered_edges: list[_EdgeEntry]
    """from 节点 BFS 序 × 组内构建序;断名边统一垫底(组内构建序)。"""

    from_rank: dict[str, int]
    reachable: set[str]
    diagnostics: list[dict]


def _scan_class_annotations(
        cls: type) -> tuple[list[_NodeEntry], list[_RawEdge], list[str]]:
    """类级遍历方法,收集节点注解与边注解(不实例化)。

    运行时 ``_analyse_node_annotations`` 用 ``getmembers(self, ismethod)``
    收普通方法与 classmethod、不收 staticmethod;类级 ``getmembers(cls, ...)``
    上 staticmethod 取值后与普通函数无异,须按 ``getattr_static`` 的定义形态
    剔除才能对齐口径。``getmembers`` 按名称字母序返回,与运行时同序,后写
    覆盖语义(见 ``_resolve_edges`` 的 name_map)由此自然成立。

    边注解挂在未被 ``@operation_node`` 装饰的方法上时,运行时在该方法的
    ``continue`` 分支静默丢弃边;静态保留方法名产出 warn 诊断。
    """
    entries: list[_NodeEntry] = []
    raw_edges: list[_RawEdge] = []
    non_node_edge_methods: list[str] = []
    members = inspect.getmembers(
        cls, predicate=lambda m: inspect.isfunction(m) or inspect.ismethod(m))
    for name, func in members:
        if isinstance(inspect.getattr_static(cls, name), staticmethod):
            continue
        node: OperationNode | None = getattr(func, 'operation_node_annotation', None)
        edge_descs: list[OperationEdgeDesc] | None = getattr(
            func, 'operation_edge_annotation', None)
        if node is not None:
            entries.append(_NodeEntry(cn=node.cn, method=name, annotation=node))
        if edge_descs is None:
            continue
        if node is None:
            non_node_edge_methods.append(name)
            continue
        for desc in edge_descs:
            # to 恒取边注解所在方法自己的节点(镜像运行时对
            # edge.node_to_name 的构建期填充;该实例字段可能被历史运行
            # 实例污染,静态不读它)
            raw_edges.append(_RawEdge(
                from_name=desc.node_from_name,
                to_cn=node.cn,
                success=desc.success,
                status=desc.status,
                ignore_status_desc=desc.ignore_status,
            ))
    return entries, raw_edges, non_node_edge_methods


def _resolve_edge(raw: _RawEdge,
                  node_name_map: dict[str, _NodeEntry]) -> _EdgeEntry:
    """解析单条边:from 按节点名映射匹配,ignore_status 静态归一。

    ``OperationEdgeDesc.__init__`` 对 ignore_status 是裸赋值,归一发生在
    运行时 ``OperationEdge.__init__``(``False if status is not None else
    ignore_status``);且 ``node_from`` 装饰器的 ignore_status 默认 True,不
    归一会把所有 status 边误标兜底、令 duplicate_fallback_edge 误报。
    """
    return _EdgeEntry(
        from_name=raw.from_name,
        from_cn=raw.from_name if raw.from_name in node_name_map else None,
        to_cn=raw.to_cn,
        success=raw.success,
        status=raw.status,
        ignore_status=False if raw.status is not None else raw.ignore_status_desc,
    )


def _analyse(entries: list[_NodeEntry], edges: list[_EdgeEntry],
             non_node_edge_methods: list[str]) -> _Analysis:
    """起点判定、BFS 排序与全部结构诊断。"""
    grouped: dict[str, list[_NodeEntry]] = {}
    for entry in entries:
        grouped.setdefault(entry.cn, []).append(entry)

    diagnostics: list[dict] = []

    for e in edges:
        if e.from_cn is None:
            diagnostics.append({
                'level': 'error',
                'code': 'missing_node',
                'message': f'找不到节点「{e.from_name}」（指向「{e.to_cn}」的边引用了它）',
            })

    for cn, lst in sorted(grouped.items()):
        if len(lst) > 1:
            methods = ', '.join(x.method for x in lst)
            diagnostics.append({
                'level': 'error',
                'code': 'duplicate_node_name',
                'message': f'存在重复的节点「{cn}」: {methods}',
            })

    start_cn: str | None = None
    start_cns: list[str] = []
    explicit_cns = list(dict.fromkeys(
        entry.cn for entry in entries if entry.annotation.is_start_node))
    if len(explicit_cns) == 1:
        start_cn = explicit_cns[0]
        start_cns = [start_cn]
    elif len(explicit_cns) > 1:
        # 不同名显式多起点才报;同名双显式起点归 duplicate_node_name
        # (运行时判定条件 start_node.cn != node.cn 同样放过同名)
        start_cns = sorted(explicit_cns)
        diagnostics.append({
            'level': 'error',
            'code': 'multiple_start',
            'message': f'存在多个起始节点: {", ".join(start_cns)}',
        })
    elif not entries:
        # 零节点基类(从不单独运行,节点由子类提供)不做起点判定:空图上
        # no_start 是噪音而非编排错误,图论诊断对空图无意义
        start_cns = []
    else:
        in_degree: dict[str, int] = {}
        for e in edges:
            # 断名边没有 from 节点、不构成可达路径,不计入度(否则唯一节点
            # 会被断名边指成有入度,误报 no_start)
            if e.from_cn is not None:
                in_degree[e.to_cn] = in_degree.get(e.to_cn, 0) + 1
        zero_in = sorted(cn for cn in grouped if in_degree.get(cn, 0) == 0)
        if len(zero_in) == 1:
            start_cn = zero_in[0]
            start_cns = zero_in
        elif len(zero_in) > 1:
            start_cns = zero_in
            diagnostics.append({
                'level': 'error',
                'code': 'multiple_start',
                'message': f'存在多个起始节点(自动判定): {", ".join(zero_in)}',
            })
        else:
            diagnostics.append({
                'level': 'error',
                'code': 'no_start',
                'message': '找不到起始节点（无显式起点且无入度0节点）',
            })

    adjacency: dict[str, list[str]] = {}
    for e in edges:
        if e.from_cn is not None:
            adjacency.setdefault(e.from_cn, []).append(e.to_cn)
    visited: set[str] = set(start_cns)
    order: list[str] = list(start_cns)
    queue: deque[str] = deque(start_cns)
    while queue:
        cn = queue.popleft()
        for nxt in adjacency.get(cn, []):
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)
                order.append(nxt)
    unreachable = sorted(cn for cn in grouped if cn not in visited)
    cn_order = order + unreachable

    if not any(d['code'] == 'no_start' for d in diagnostics):
        # no_start 已说明全图不可达,逐节点 warn 是刷屏噪音,由
        # nodes[].reachable 全 false 表达
        for cn in unreachable:
            diagnostics.append({
                'level': 'warn',
                'code': 'unreachable_node',
                'message': f'节点「{cn}」从起点不可达（漏写 node_from 的典型症状）',
            })

    fallback_groups: dict[tuple[str, bool], list[_EdgeEntry]] = {}
    for e in edges:
        if e.from_cn is not None and e.ignore_status:
            # 兜底边冲突按 (from, success 方向) 分组:不同方向的兜底边
            # 运行时先被 success 过滤,互不冲突
            fallback_groups.setdefault((e.from_cn, e.success), []).append(e)
    for (from_cn, success), items in sorted(fallback_groups.items()):
        if len(items) < 2:
            continue
        first_to = items[0].to_cn
        last_to = items[-1].to_cn
        direction = '成功' if success else '失败'
        message = (f'「{from_cn}」的{direction}方向存在 {len(items)} 条兜底边：'
                   f'无 status 返回时第 1 条生效（→{first_to}）；'
                   f'带 status 返回且无匹配时最后 1 条生效（→{last_to}）')
        if first_to == last_to:
            message += '；目标相同无路径丢失'
        diagnostics.append({
            'level': 'warn',
            'code': 'duplicate_fallback_edge',
            'message': message,
        })

    for method in non_node_edge_methods:
        diagnostics.append({
            'level': 'warn',
            'code': 'edge_on_non_node',
            'message': f'方法 {method} 挂有 @node_from 但未被 @operation_node 装饰，边不会生效',
        })

    from_rank = {cn: i for i, cn in enumerate(cn_order)}
    indexed = list(enumerate(edges))

    def _edge_sort_key(item: tuple[int, _EdgeEntry]) -> tuple[bool, int, int]:
        i, e = item
        rank = (from_rank.get(e.from_cn, len(from_rank))
                if e.from_cn is not None else 0)
        return (e.from_cn is None, rank, i)

    ordered_edges = [e for _, e in sorted(indexed, key=_edge_sort_key)]

    return _Analysis(
        start_cn=start_cn,
        start_cns=start_cns,
        cn_order=cn_order,
        grouped=grouped,
        ordered_edges=ordered_edges,
        from_rank=from_rank,
        reachable=visited,
        diagnostics=diagnostics,
    )


def _edge_label(success: bool, status: str | None, ignore_status: bool,
                effective: bool) -> str:
    """边条件标注,与 flow 图例行同款记号。

    兜底边与 status 边互斥(归一语义保证 status 非空时 ignore_status 恒
    False),两种形态不会叠加。断名边(``effective=False``)运行时必炸、无
    生效语义,不描述兜底行为。
    """
    direction = '成功' if success else '失败'
    if effective and ignore_status:
        return f'兜底·{direction}'
    if status is not None:
        return f'{direction}·status={status}'
    return direction


def _render_flow(cls: type, node_count: int, analysis: _Analysis) -> str:
    """文本流转图:按节点分组、边行缩进挂靠,头部摘要 + 图例两行固定。"""
    in_edges: dict[str, list[_EdgeEntry]] = {}
    out_edges: dict[str, list[_EdgeEntry]] = {}
    dangling_by_to: dict[str, list[_EdgeEntry]] = {}
    for e in analysis.ordered_edges:
        if e.from_cn is None:
            dangling_by_to.setdefault(e.to_cn, []).append(e)
        else:
            in_edges.setdefault(e.to_cn, []).append(e)
            out_edges.setdefault(e.from_cn, []).append(e)

    if analysis.start_cn is not None:
        start_display = analysis.start_cn
    elif any(d['code'] == 'multiple_start' for d in analysis.diagnostics):
        start_display = '多个'
    else:
        start_display = '无'
    lines = [
        (f'# {cls.__name__} ({cls.__module__}.{cls.__name__})'
         f' · {node_count}节点 {len(analysis.ordered_edges)}边 · 起点={start_display}'),
        '# 图例: (成功/失败)=按节点返回结果分流 · status=仅该返回状态走此边 · 兜底=该方向其余状态的落点',
    ]
    start_cn_set = set(analysis.start_cns)
    for cn in analysis.cn_order:
        for entry in analysis.grouped[cn]:
            head = f'[起点] {cn}' if cn in start_cn_set else cn
            head += f' (method={entry.method})'
            if cn not in out_edges:
                head += ' [终点]'
            if cn not in analysis.reachable:
                head += ' [不可达]'
            incoming = in_edges.get(cn, [])
            if len(incoming) >= 2:
                sources = sorted({e.from_cn for e in incoming},
                                 key=lambda c: analysis.from_rank[c])
                head += f' ←入: {", ".join(sources)}'
            for e in dangling_by_to.get(cn, []):
                label = _edge_label(e.success, e.status, e.ignore_status,
                                    effective=False)
                head += f' ←✗不存在的来源「{e.from_name}」({label})'
            lines.append(head)
            outs = out_edges.get(cn, [])
            for i, e in enumerate(outs):
                branch = '└─' if i == len(outs) - 1 else '├─'
                label = _edge_label(e.success, e.status, e.ignore_status,
                                    effective=True)
                lines.append(f'  {branch}({label})→ {e.to_cn}')
    return '\n'.join(lines)


def _render_mermaid(analysis: _Analysis) -> str:
    """mermaid flowchart 源码:与文本图同数据源的第二渲染。

    节点 id 按 BFS 序编号(渲染序即执行序);断名边画幽灵来源虚拟节点。
    mermaid 字符串内英文双引号无转义语法,label 与边标注统一替换全角。
    """
    def quote(text: str) -> str:
        return text.replace('"', '＂')

    id_map = {cn: f'n{i}' for i, cn in enumerate(analysis.cn_order, start=1)}
    start_cn_set = set(analysis.start_cns)
    lines = ['flowchart TD']
    for cn in analysis.cn_order:
        if cn in start_cn_set:
            style = ':::start'
        elif cn not in analysis.reachable:
            style = ':::unreachable'
        else:
            style = ''
        lines.append(f'  {id_map[cn]}["{quote(cn)}"]{style}')
    ghost_ids: dict[str, str] = {}
    next_id = len(analysis.cn_order)
    for e in analysis.ordered_edges:
        if e.from_cn is not None:
            continue
        if e.from_name not in ghost_ids:
            next_id += 1
            ghost_ids[e.from_name] = f'n{next_id}'
            lines.append(f'  {ghost_ids[e.from_name]}["✗「{quote(e.from_name)}」"]:::missing')
    for e in analysis.ordered_edges:
        src = (id_map[e.from_cn] if e.from_cn is not None
               else ghost_ids[e.from_name])
        label = _edge_label(e.success, e.status, e.ignore_status,
                            effective=e.from_cn is not None)
        lines.append(f'  {src} -->|"{quote(label)}"| {id_map[e.to_cn]}')
    lines.append('  classDef start fill:#c8e6c9')
    lines.append('  classDef unreachable stroke:#e53935,stroke-dasharray:5 5')
    lines.append('  classDef missing fill:#ffcdd2')
    return '\n'.join(lines)


def extract_operation_flow(cls: type, mermaid: bool = False) -> dict:
    """对 Operation 子类做类级静态提取,返回节点流转全量描述。

    纯反射(不实例化),语义镜像运行时节点网络构建;诊断 error 级
    (missing_node / duplicate_node_name / multiple_start / no_start)与运行
    时 raise 一一对应,出现 error 时 flow 仍尽力渲染 —— 调试价值在
    「运行前看到全貌」,不是报错即止。

    Args:
        cls: Operation 子类(含 Application 子类;app 同样是节点编排
            重灾区,本工具口径是「可读性」不限「可运行性」)。
        mermaid: True 时额外渲染 mermaid flowchart 源码。

    Returns:
        结构见设计契约(op_id/class_name/module/start_node/node_count/
        edge_count/flow/mermaid/nodes/edges/diagnostics/notes)。
    """
    entries, raw_edges, non_node_edge_methods = _scan_class_annotations(cls)
    # 遍历序即 getmembers 字母序,同名条目后者覆盖前者 —— 镜像运行时
    # node_name_map 的构建语义,边解析与运行时命中同一个节点
    node_name_map = {entry.cn: entry for entry in entries}
    edges = [_resolve_edge(raw, node_name_map) for raw in raw_edges]
    analysis = _analyse(entries, edges, non_node_edge_methods)

    nodes_payload = [
        {
            'cn': entry.cn,
            'method': entry.method,
            'is_start_node': entry.annotation.is_start_node,
            'timeout_seconds': entry.annotation.timeout_seconds,
            'node_max_retry_times': entry.annotation.node_max_retry_times,
            'reachable': entry.cn in analysis.reachable,
        }
        for cn in analysis.cn_order
        for entry in analysis.grouped[cn]
    ]
    edges_payload = [
        {
            'from': e.from_cn,
            'to': e.to_cn,
            'success': e.success,
            'status': e.status,
            'ignore_status': e.ignore_status,
        }
        for e in analysis.ordered_edges
    ]
    return {
        'op_id': f'{cls.__module__}.{cls.__name__}',
        'class_name': cls.__name__,
        'module': cls.__module__,
        'start_node': analysis.start_cn,
        'node_count': len(entries),
        'edge_count': len(edges),
        'flow': _render_flow(cls, len(entries), analysis),
        'mermaid': _render_mermaid(analysis) if mermaid else None,
        'nodes': nodes_payload,
        'edges': edges_payload,
        'diagnostics': analysis.diagnostics,
        'notes': list(_NOTES),
    }


def describe_operation_flow(op_id: str, mermaid: bool = False) -> dict:
    """按定位标识解析 operation 并返回其节点流转描述(静态提取)。

    ``op_id`` 契约与 ``describe_operation`` 同构:完整
    ``<module>.<ClassName>``(实时解析,接受任意 Operation 子类含
    Application)或类名短名(扫描缓存精确匹配;App 类被扫描过滤不进缓存,
    短名查不到属预期)。短名多命中返回轻量 ambiguous 形态(只列候选
    op_id,不带参数 schema —— 该场景调用方只需选对目标再看图)。

    Args:
        op_id: 完整 op_id 或类名短名。
        mermaid: True 时额外渲染 mermaid flowchart 源码。

    Returns:
        单命中: 同 ``extract_operation_flow``;
        短名多命中: ``{ambiguous: True, count, candidates[], hint}``。

    Raises:
        ValueError: 短名未找到(附相似类名建议)/ 完整 op_id 形态解析
            失败(格式非法 / 模块无该类 / 非 Operation 子类等)。
    """
    shorts = match_short_name(op_id)
    if shorts is None:
        return extract_operation_flow(resolve_op_class(op_id), mermaid=mermaid)
    if not shorts:
        raise _short_name_not_found_error(op_id)
    if len(shorts) > 1:
        return {
            'ambiguous': True,
            'count': len(shorts),
            'candidates': sorted(i.op_id for i in shorts),
            'hint': '命中多个同名类，用完整 op_id 精确指定',
        }
    return extract_operation_flow(resolve_op_class(shorts[0].op_id),
                                  mermaid=mermaid)
