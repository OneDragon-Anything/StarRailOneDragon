# operation 流转打印工具（describe_operation_flow）迭代设计（总纲）

## 0. 元信息

- 迭代目标：用户需求「增加一个基础 MCP 工具，打印一个 operation 的流转，防止代码写得乱、看不清 node 之间的流转」（2026-11-13 会话直接需求）
- 状态：草案
- 文档清单：（单文档方案，无详设——本文即完整设计）

## 1. 问题与动机

### 1.1 现状症状

- Operation 的节点编排靠 `@operation_node`（挂 `OperationNode` 到函数属性 `operation_node_annotation`）+ `@node_from`（挂 `OperationEdgeDesc` 列表到函数属性 `operation_edge_annotation`）分散声明（`src/one_dragon/base/operation/operation_node.py` / `operation_edge.py`）。节点一多（如 `use_trailblaze_power.py` 12 节点 24 边、`challenge_ehco_of_war.py` 近 30 边），流转关系只能脑内拼图。
- 编排错误全部推迟到**运行期**才发现：`_analyse_node_annotations` 在 op 实例化运行时才校验「找不到节点 / 多个起始节点 / 找不到起始节点」并 raise（`operation.py` L255-L315）——写错一个 `from_name` 要等到跑起来才炸。
- 远程 MCP 使用者（LLM agent）只有 `list_operations` / `describe_operation`（参数 schema），**看不到节点结构**——op 的过程语义（怎么流转、失败走哪、收尾在哪）对它完全不可见。

### 1.2 根因归层

**表示层**：节点流转信息客观存在于装饰器注解中，但没有任何可读的静态表示形式；错误校验只有运行时一条路径。不是流程层（注解机制本身健康）、不是语义层（边语义明确）。

### 1.3 解决到哪；明确不解决

- 解决：
  1. 新 MCP 工具 `describe_operation_flow(op_id)`：静态（纯反射、不实例化）提取任意 Operation 子类的节点图，返回文本流转图 + 结构化 nodes/edges + 静态诊断；
  2. 静态诊断把运行时校验提前（断名边 / 多起点 / 零起点 / 重复节点名），并补运行时不查的结构问题（不可达节点、同方向多条兜底边、边挂在非节点方法上）;
  3. HTTP 镜像端点（与 MCP 同契约单源）。
- 明确不解决：
  - 不改 `one_dragon` 公共框架（不动 Operation / 装饰器 / 运行时校验逻辑——公共包改动需跨项目同步，本需求在 SR 侧只读注解即可满足）；
  - 不做运行时流转 tracing（运行路径已有 `send_node_notify` / 日志 / `get_run_status`，不重复）；
  - 不做 mermaid/图形渲染输出（文本分组图 + 结构化数据已覆盖 LLM 与人读；需要时后续扩展）；
  - 不推断 `need_check_game_win`（静态无法可靠判定——子类 super 调用传字面量的场景会误判，见 §2.5）。

## 2. 方案（单文档完整设计）

### 2.1 系统级变化

| 位置 | 变化 |
|---|---|
| `src/sr_od/backend/operation_flow.py` | 新模块：静态提取 + 诊断 + 文本图渲染（核心逻辑单源） |
| `src/sr_od/backend/mcp/service_app.py` | 新增 `make_describe_operation_flow` 工厂 |
| `src/sr_od/backend/mcp/app.py` | 注册 tool（`readOnlyHint=True`） |
| `src/sr_od/backend/http/service_routes.py` | 新增 `GET /game/operations/flow?op_id=`（薄适配，调同一核心函数） |
| `docs/develop/sr_od/backend/mcp.md` / `http.md` | 正本工具表补行（收尾阶段） |
| `sr-od-test/test/sr_od/backend/test_operation_flow.py` | 测试（镜像规范） |

### 2.2 核心提取：类级静态扫描（语义镜像运行时）

**依据**：`Operation._analyse_node_annotations`（`operation.py` L220-L272）遍历 `inspect.getmembers(self, predicate=inspect.ismethod)` 读函数属性；注解挂在**函数对象**上（装饰器 `setattr(func, ...)`），类级遍历同样读得到（MRO 继承、子类重写覆盖行为与运行时一致：重写未再装饰 → 节点消失）。类级遍历的谓词定死为：`inspect.getmembers(cls, predicate=lambda m: inspect.isfunction(m) or inspect.ismethod(m))`——类上取值普通方法为函数（isfunction）、classmethod 为绑定方法（ismethod），两者运行时实例遍历（ismethod）都收；staticmethod 依 `inspect.getattr_static(cls, name)` 返回 `staticmethod` 对象剔除（运行时实例遍历不收 staticmethod，镜像其口径）。

提取规则（逐条镜像运行时语义）：

1. **节点**：函数带 `operation_node_annotation` → 节点，`cn` 取注解的 `cn`（业务代码内可能用中文或英文 name，不做假设）；同一方法可同时带边注解。
2. **边**：函数带 `operation_edge_annotation`（`OperationEdgeDesc` 列表）→ 每条 desc 一条边；**to 节点 = 该边注解所在方法自己的节点**（运行时 `edge.node_to_name` 也是这么填充的，L252——静态不读 `node_to_name` 字段，它可能被历史运行实例污染，且静态语义就是「挂在谁身上谁就是 to」）。
3. **from 节点**：按 `desc.node_from_name` 字符串匹配节点 `cn`；匹配不到 = 诊断 `missing_node`（运行时 L258 同样 raise）。
4. **边属性**：直接读 desc 构造后的字段（`success` / `status` / `ignore_status`——`OperationEdgeDesc.__init__` 已归一：`status is not None` 时 `ignore_status` 恒 False，不重算）。
5. **起点判定**（镜像 L306-L315）：显式 `is_start_node=True` 优先；无显式起点时按**业务边入度 0** 自动判定（入度不含框架前缀注入——运行时入度表在注入前构建）；多起点 → 诊断 `multiple_start`；零起点 → 诊断 `no_start`。
6. **重复节点名**：不同方法同 `cn` → 诊断 `duplicate_node_name`（运行时 `_add_node` L359 raise，静态提前发现）。
7. **遍历序**：`getmembers` 按名称字母序 + 方法内装饰器自下而上追加序——与运行时 edge_list 构建序一致，用于 §2.4 兜底边诊断判定「哪条生效」。

### 2.3 工具契约

```
describe_operation_flow(op_id: str) -> dict
```

- `op_id` 契约与 `describe_operation` 完全同构：完整 `<module>.<ClassName>`（`resolve_op_class` 实时解析，**接受任意 Operation 子类，含 Application**——app 类同样是节点编排重灾区，如 `currency_war_app`；运行类工具 `_is_runnable_op` 排除 Application 是「可运行性」口径，本工具是「可读性」口径，不排斥）或类名短名（扫描缓存精确匹配，多命中返 `{ambiguous: True, matches[]}` 候选 op_id 列表——App 类不在扫描根内，短名查不到属预期，报错文案提示用完整 op_id）。
- 解析失败（未找到 / 非 Operation 子类）→ MCP 层 except 返回 `{error}`，与 `describe_operation` 同模式；不引入 `success` 键（观察类工具既有惯例）。

返回结构：

```python
{
  'op_id': str, 'class_name': str, 'module': str,
  'start_node': str | None,        # multiple_start/no_start 时 None
  'node_count': int, 'edge_count': int,
  'flow': str,                     # 文本流转图（§2.4 格式，主形态）
  'nodes': [                       # 按字母序（与运行时遍历序一致）
    {'cn': str, 'method': str,           # 方法名，定位源码用
     'is_start_node': bool, 'timeout_seconds': float|None,
     'node_max_retry_times': int, 'reachable': bool},
  ],
  'edges': [                       # 遍历序（§2.2 第 7 条）
    {'from': str, 'to': str|None,        # to=None = 断名边（missing_node）
     'success': bool, 'status': str|None, 'ignore_status': bool},
  ],
  'diagnostics': [
    {'level': 'error'|'warn', 'code': str, 'message': str},  # code 枚举见 §2.4
  ],
  'notes': [str, ...],             # 固定说明（终点语义 / 框架前缀省略等）
}
```

- `diagnostics` 出现 error 时 `flow` 仍尽力渲染（断名边画成 `→ ✗节点不存在`）——调试价值在「运行前看到全貌」，不是报错即止。
- tool docstring 按 MCP 惯例写全（观察类 / 纯反射不实例化 / 为什么不实例化：`SrOperation.__init__` 构造 `OpenAndEnterGame` 等副作用依赖）。

### 2.4 文本流转图格式与诊断项

`flow` 主格式（按节点分组、节点字母序，边行缩进挂靠）：

```
# UseTrailblazePower (sr_od.challenge_mission.use_trailblaze_power.UseTrailblazePower)
[起点] 传送 (method=transport)
  ├─(成功·status=开拓力弹框-取消)→ 点击挑战后确认
  ├─(失败)→ ✗节点不存在「阵亡传送恢复」
  └─(兜底·成功)→ 选择次数
选择次数 (method=choose_times) [终点]
  （无出边：返回成功即整个 op 成功）
```

- 边标注规则：`success` → `(成功)` / `(失败)`；`status` 非空追加 `·status=<值>`；`ignore_status=True` 追加 `·兜底`（语义：该 success 方向任意 status 匹配不到时的落点）。
- 节点标注：起点 `[起点]`；无出边 `[终点]`；不可达节点追加 `[不可达]`。
- 环（A→B→A）在分组图里天然表达为两条边行，不特殊处理；可达性判定用 BFS（含环、含断名边跳过）。

诊断项（`code` 稳定枚举，level 语义：error = 运行时必炸或图不成立；warn = 结构可疑但不致命）：

| code | level | 判定 | 运行时行为对照 |
|---|---|---|---|
| `missing_node` | error | 边的 `from_name` 匹配不到任何节点 | 运行时 raise `找不到节点`（L258） |
| `duplicate_node_name` | error | 不同方法产出同 `cn` 节点 | 运行时 `_add_node` raise（L359） |
| `multiple_start` | error | 显式多起点，或自动判定多个入度 0 节点 | 运行时 raise（L244/L311） |
| `no_start` | error | 无显式起点且无入度 0 节点 | 运行时 raise（L315） |
| `unreachable_node` | warn | 从起点 BFS 不可达（含起点为 None 时全图不可达） | 运行时静默——节点永不执行，改漏 `node_from` 的典型症状 |
| `duplicate_fallback_edge` | warn | 同 `(from, success 方向)` 下 `ignore_status=True` 的边 >1 条 | 运行时静默——`_get_next_node` 后遍历者覆盖先遍历者（L571-L572），先写的兜底路径静默丢失；message 按 §2.2 第 7 条遍历序指出生效的那条 |
| `edge_on_non_node` | warn | 边注解挂在未被 `@operation_node` 装饰的方法上 | 运行时静默——`_analyse_node_annotations` 对无节点注解的方法 `continue`，边被丢弃（L236-L238） |

**兜底边诊断的语义依据**：`_get_next_node`（L550-L588）先按 `edge.success` 过滤（兜底边也不例外），再记 `ignore_status` 兜底、`status` 精确匹配短路——故「多条兜底」必须按 success 方向分组判定，不同方向的兜底边不冲突；`OperationEdgeDesc` docstring 明言「一个节点应该最多只有一条边忽略返回状态」（operation_edge.py L39-L41）。

不做「成功无路可走」类启发式诊断：运行时 status 值是动态字符串，静态无法穷举覆盖性，误报率高（收尾节点本来就是无路即结束）；宁缺毋滥。

### 2.5 框架前缀节点的处理

运行时 `_add_check_game_node`（L324-L350）在 `need_check_game_win=True` 时于起点前注入「检测游戏窗口→打开并进入游戏」。决策：

- **默认不画进图**，`notes` 固定一句：「框架是否在起点前注入『检测游戏窗口→打开并进入游戏』前缀取决于实例构造参数 `need_check_game_win`（默认 True），本图未画出」。
- 不做静态推断、不加开关参数：`need_check_game_win` 是实例参数，子类 super 调用传字面量时（如 `cw_buy_card_action.py` L65 传 `False`）签名反射必误判；框架前缀对「看清业务流转」零增益，画进去只添噪音。

### 2.6 复用与落点

- 解析复用 `operation_registry.resolve_op_class` / `match_short_name` / `_short_name_not_found_error`（不重写解析；ambiguous 形态列候选 op_id，无需 matches 全 schema）。
- 新模块 `operation_flow.py` 只依赖 `inspect` + `one_dragon.base.operation.operation_node/operation_edge` 的数据类（只读，不 import Operation 运行时逻辑）——`operation_registry.py` 已 717 行，不再塞入。
- MCP 工厂与注册：`service_app.py` `make_describe_operation_flow(backend)`（签名对齐既有工厂，虽不实际用 backend.ctx——与 `describe_operation` 的 ctx 占位同理）+ `app.py` `mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, title="查看 operation 节点流转"))`。
- HTTP：`GET /game/operations/flow?op_id=`，`asyncio.to_thread` 包核心函数，业务失败 `200 + {error}`——与 `handle_game_operations_describe` 同模式（service_routes.py L119-L139）。

### 2.7 测试计划

`sr-od-test/test/sr_od/backend/test_operation_flow.py`（镜像 `test_operation_registry.py` 位置）：

1. **正常图提取**：测试模块内定义 fake op 类（真装饰器 `@operation_node`/`@node_from`，多节点多分支含 status/兜底边），断言 nodes/edges/start_node/flow 文本关键行。
2. **诊断各 code 一条**：每个 code 构造最小 fake 类断言（missing_node / duplicate_node_name / multiple_start / no_start / unreachable_node / duplicate_fallback_edge + 生效边指认 / edge_on_non_node）。
3. **解析层**：完整 op_id 传测试内 fake 类（`resolve_op_class` 实时 importlib 解析可行）；短名路径不在扫描根，不测（属 registry 既有覆盖面）。
4. **Application 类可达**：fake Application 子类完整 op_id 也能提取（契约 §2.3）。

测试纪律遵循 sr-od-test/README：fake 类全在测试文件内、零副作用（不实例化 op，只做类级反射）、不连真游戏。

## 3. 关键取舍

- **静态扫描 vs 实例化后读 `_node_edges_map`**：实例化最省事（直接拿运行时成品图），但 `SrOperation.__init__` 构造 `OpenAndEnterGame(ctx)` 等副作用依赖（sr_operation.py L24），`operation_registry` 全模块哲学就是纯反射不实例化——静态扫描沿用该哲学，且能覆盖「实例化即炸」的断名错误（实例化路径在 `_init_network` 就 raise，工具反而没法用）。
- **文本分组图 vs mermaid**：mermaid 可渲染但节点多时源码同样乱、且 LLM 消费无优势；分组文本信息密度最高、无歧义。结构化 `edges[]` 已提供程序化消费通道，后续要 mermaid 是纯增量。
- **不诊断「成功无路」启发式**：见 §2.4 末段——静态证据不足，误报伤信任。
- **App 类不进短名解析**：App 不在扫描根（`_SCAN_ROOTS` 排除 Application 是既有口径），短名自然查不到；完整 op_id 实时解析覆盖该场景，错误文案引导即可。
