# operation-flow-tool 实现者走查（对抗审查）

- 被审对象：design.md（总纲）、landing.md（阶段拆分）
- 审查视角：假自己是拿到这份设计的实现者，逐阶段验证「凭这份能开工吗」
- 方法：设计的技术断言逐条对照真实代码核实（行号均已实地验证），语义空洞按「实现者必须做选择而设计未回答」判
- 结论速览：攻击点 7 条（A1-A7），必修 3 条（A1/A2/A3），文字修正 4 条（A4-A7）；总体结论**需修订**

## A1 duplicate_fallback_edge 的「生效边指认」规则与运行时行为不符

**定位**：design.md §2.4.4 诊断表 `duplicate_fallback_edge` 行、§2.2 第 7 条

**攻击内容**：设计断言「运行时静默——`_get_next_node` 后遍历者覆盖先遍历者（L571-L572），先写的兜底路径静默丢失；message 按 §2.2 第 7 条遍历序指出生效的那条」。这条指认规则只覆盖了运行时的一半分支：

1. 兜底边 `status` 恒为 `None`（`OperationEdge.__init__` 归一：`status is not None` 时 `ignore_status` 恒 False，operation_edge.py L36）。当当前轮返回 `status=None`（`round_success()` / `round_fail()` 不带 status，业务主路径）时，`_get_next_node` 走 L574-L576：`edge.status is None and current_round_result.status is None → next_node_id = ...; break`——**遍历序第一条** status=None 边直接 break 生效，多条兜底边时是首条生效，与「后遍历者覆盖先遍历者」正好相反。
2. 只有当 `current_round_result.status ≠ None` 且无精确匹配时，才走 L571-L572（`final_next_node_id` 无条件覆盖）+ L585-L586——此时**最后一条**兜底边生效。
3. 「生效的那条边」由运行时动态 status 决定，静态 message 无法单一指认；设计把它定死为单一规则，对无 status 返回的主路径会给出反向指认，误导使用者。
4. 判定「同 (from, success 方向) 下 `ignore_status=True` 的边 >1 条」未豁免 to 相同的冗余形态：from/to 都相同的多条兜底边没有路径丢失事实（殊途同归），message「先写的兜底路径静默丢失」对该形态失真。

**依据**：operation.py L550-L588（重点 L568 success 过滤、L571-L572 final 覆盖、L574-L576 status=None break、L583-L586 next 优先于 final）；operation_edge.py L36（兜底边 status 恒 None）、L39-L41（「一个节点应该最多只有一条边忽略返回状态」——设计引用行号正确）。

**建议处置**：**需修订**。message 不再指认单一「生效边」，改为列出同组全部兜底边的遍历序并说明两分支语义（当前轮 status=None → 首条 break 生效；status≠None 且无精确匹配 → 末条覆盖生效）；或最简弱化为「存在 N 条兜底边（按遍历序列出），运行时按当前轮返回 status 决定实际走哪条」。可选：to 相同的冗余形态豁免或降级措辞。

## A2 断名边（missing_node）在「尽力渲染」下的三处图论语义未定义

**定位**：design.md §2.4.1（BFS 序与入度 0 起点）、§2.3（edges[] 排序注释）、§2.4.2（`←入:` 标注）

**攻击内容**：设计只回答了断名边的一处语义（「可达性判定用 BFS（断名边跳过）」，§2.4.2），其余三处悬空，且运行时无先例可镜像（运行时断名边在 operation.py L258 直接 raise，L294-L304 的入度表构建在 raise 之后——运行时根本不存在「带断名边的图」），静态必须自行定死而设计未定：

1. **入度 0 起点判定**（§2.4.1「无显式则全部入度 0 节点」）：断名边的 to 是真实节点，这条幽灵入边计不计入度？计入则可能掩盖真实的入度 0 节点——例：A→B 正常、C(断名)→A，若计入则 A 非起点，无显式起点时 no_start 误报 + 全图不可达，诊断形态大变。
2. **edges[] 排序**（§2.3「from 节点 BFS 序 × 节点内构建序」）：断名边没有 from 节点，不属任何节点的分组，序列中无处安放。
3. **`←入:` 入边计数**（§2.4.2「入边 ≥2 的节点列出全部来源」）：断名边算不算该节点的入边、来源名（幽灵 from_name）怎么呈现，未定。

三种口径产生不同的 `start_node`/`nodes[].reachable`/排序输出，实现者只能瞎选。

**依据**：operation.py L255-L261（断名 raise 先于图构建）、L294-L304（入度表仅统计已解析边）；design.md §2.2 第 5 条只排除了「框架前缀注入」未提断名边。

**建议处置**：**需修订**。定死一处一致口径并写入 §2.4.1/§2.3/§2.4.2。建议：断名边不计入度、不进 `←入:` 计数（幽灵入边不参与图论判定，只作诊断行呈现）；edges[] 中断名边独立尾区按构建序列出（或按 to 节点 BFS 序挂靠），与「可达性跳过」口径对齐。

## A3 重复节点名（duplicate_node_name）场景三处语义未定义或与运行时有偏差

**定位**：design.md §2.2 第 3/5/6 条、§2.4.4 诊断表

**攻击内容**：诊断本身可实现（不同方法同 `cn` 可检出），但该 error 场景下设计承诺「尽力渲染」而渲染语义未定义，且一处与「语义镜像运行时」的自承诺（§2.2 标题）相悖：

1. **multiple_start 判定**：运行时 L243 条件是 `if start_node is not None and start_node.cn != node.cn: raise`——**同名**双显式起点不触发多起点 raise，最终在 `_add_node`（L358-L359）以「存在重复的节点」炸；自动判定分支 L310 同构造。静态若按「显式 `is_start_node=True` 节点数 >1」判 multiple_start，会在同名场景多报一条运行时不会报的诊断。
2. **边解析的节点匹配**：运行时 L240 `node_name_map[node.cn] = node` 是 dict 覆盖赋值——同名节点按 getmembers 字母序**后者覆盖前者**，L256 边解析用覆盖后的节点。静态 §2.2 第 3 条只说「按 `desc.node_from_name` 字符串匹配节点 `cn`」，未定同名时匹配哪个方法（`nodes[].method` 与边的对应会漂移）。
3. **nodes[]/flow 呈现**：两个同名节点（method 不同）怎么列未定义；BFS 序/入度计算按 cn 分组时同名节点是合并还是分立也未写。

**依据**：operation.py L233-L245（L240 dict 覆盖、L243 同名条件）、L310（自动判定同名条件）、L352-L360（`_add_node` 重复名 raise，设计引用 L359 正确）。

**建议处置**：**需修订**（轻——诊断已报 error 不漏，但渲染规则要定死）。§2.2 补三条：同名多显式起点不报 multiple_start（镜像 L243/L310，只报 duplicate_node_name）；边匹配镜像 L240 的字母序后写覆盖；nodes[] 同名节点并列以 method 区分、入度按 cn 合并计。

## A4 背景数据断言失真：节点/边计数与真实代码不符

**定位**：design.md §1.1、§2.4.2 示例头部行

**攻击内容**：§1.1 称 `use_trailblaze_power.py`「12 节点 24 边」，实测 **15 节点 20 边**（`@operation_node` 15 处：L73/86/138/144/168/174/186/192/218/222/247/290/310/329/342；`@node_from` 20 处：L72/85/137/143/167/173/185/191/217/218/219/246/289/309/327/328/338/339/340/341）。§1.1 称 `challenge_ehco_of_war.py`「近 30 边」，实测 **23 边**。§2.4.2 示例头部「UseTrailblazePower · 12节点 24边」同错；示例还把「status=开拓力弹框-取消」边画成「传送→点击挑战后确认」，真实拓扑是「点击挑战后确认→完成后退出」（use_trailblaze_power.py L339）——示意可接受，但既然用真实 op 与真实节点名，编造拓扑会误导读者对照源码。

**依据**：src/sr_od/challenge_mission/use_trailblaze_power.py（上述行号）；src/sr_od/application/echo_of_war/challenge_ehco_of_war.py（23 处 @node_from，L61-L237）。

**建议处置**：文字修正。计数改为实测值或改成泛指（「十余节点二十余边」）；示例拓扑要么改为真实子图，要么明示「拓扑为格式示意，非该 op 真实流转」。

## A5 mermaid「永不炸语法」断言过强：`"` 与 `|` 未处理

**定位**：design.md §2.4.3

**攻击内容**：「label 引号包裹节点 cn——中文、空格、括号等永不炸语法」——列举的字符确实安全，但引号包裹的 label 内再出现 `"`（`n["a"b"]` 非法）、边标注 `-->|…|` 内出现 `|`（定界符被截断）会破坏语法。cn 与 status 都是业务代码字面量，概率低，但工具是通用诊断入口，「永不」不成立。

**依据**：mermaid flowchart 语法（引号字符串不提供 `"` 转义机制；`|` 是边标签定界符）；设计 §2.4.3 原文断言「永不炸」。

**建议处置**：文字修正。写明对 label/边标注中的 `"` 与 `|` 做替换（如替换为全角 `＂`/`｜`）或声明「业务字面量域内不含这两个字符」的假设与失效条件。

## A6 解析层测试的断言面未定义，按字面实现会违反测试纪律

**定位**：design.md §2.7 第 3 条

**攻击内容**：「完整 op_id 传扫描根内真实类（如 `sr_od.operations.move.move_directly.MoveDirectly`）」只定了输入没定断言面。若实现者顺手续锁 MoveDirectly 的节点清单/计数，节点随正常迭代增删即测试红——违反 sr-od-test/README「写测试」节第 3 条（「断言结果的结构与文案……不断言会随正常调整变动的统计数值」，与 AGENTS.md §10.5-2 同源）。应明确该组测试锁「解析链路行为」：解析成功、返回结构字段成立（`op_id`/`class_name` 回填、`start_node` 非空、`node_count > 0`、无 error 级诊断），不锁具体节点内容。

**依据**：sr-od-test/README.md L111；design.md §2.7 第 3 条原文无断言面表述。

**建议处置**：文字修正。§2.7 补一句断言口径（锁结构成立，不锁真实类节点清单）。

## A7 「App 类不在扫描根内」与 registry 代码相反：归因写反

**定位**：design.md §2.3（「App 类不在扫描根内，短名查不到属预期」）、§3 取舍末条（「App 不在扫描根（`_SCAN_ROOTS` 排除 Application 是既有口径）」）

**攻击内容**：`_SCAN_ROOTS`（operation_registry.py L41-L44）**包含** `'sr_od.application'`——App 类恰在扫描根内被遍历（如 `src/sr_od/application/currency_war/currency_war_app.py`）。短名查不到的真实机制是 `_is_runnable_op` 三重过滤中的 `issubclass(cls, Application) → return False`（L76-L77）把扫描到的 App 类剔除。行为结论碰巧都对（短名查不到；完整 op_id 走 `resolve_op_class` L533 只判 `issubclass(cls, Operation)` 不排 Application，App 可用），但机制归因与代码相反，会建立错误心智模型——例如误以为往 `sr_od/application` 新增 App 类不会被扫描触碰、或以为 `_SCAN_ROOTS` 维护者需为 App 做排除。

**依据**：operation_registry.py L41-L44（`_SCAN_ROOTS` 含 `sr_od.application`）、L57-L80（`_is_runnable_op`，L76-L77 Application 剔除）、L495-L535（`resolve_op_class` 不排 Application）；src/sr_od/application/currency_war/currency_war_app.py 存在于扫描根包内。

**建议处置**：文字修正（随本轮修订一并改）。归因改写为「App 类在扫描根 `sr_od.application` 内被扫到，由 `_is_runnable_op` 的 Application 过滤剔除，故短名缓存无 App；完整 op_id 经 `resolve_op_class` 不做 Application 排除，App 类可达」。

---

## 总体结论

**需修订**（必须修：A1、A2、A3；A4-A7 为文字修正，应随修订一并改正，不单独阻塞）。

三条必修的共同性质：都出现在「诊断出 error 后仍尽力渲染」的承诺区（design §2.3 末条）——A1 是生效边指认与运行时行为不符（会输出误导性诊断 message），A2/A3 是渲染路径上的语义空洞（实现者必须做选择而设计未回答，不同选择产出不同的 start_node/reachable/排序/诊断组合）。修订方式都是补写定死口径，不动方案骨架。

以下维度逐项核对**无实质发现**（正面确认，避免误伤）：

- **§2.2 谓词与运行时镜像的主体正确**：类级 `isfunction or ismethod` 谓词 + `getattr_static` 剔除 staticmethod 的三态分析与 Python 3.11 语义一致（类访问 staticmethod 返回底层函数、`getattr_static` 返回包装对象）；绑定方法经属性代理读函数注解与类级直读同源；装饰器叠加序「自下而上追加」与 `node_from` 实现（operation_edge.py L75-L93 逐层 append）一致；`node_to_name` 污染防御（不读该字段）正确对应 operation.py L252 的运行时变异；子类重写覆盖语义与 getmembers MRO 取值一致。
- **运行时无业务侧动态节点注入**：`_add_node` / `_node_edges_map` 全仓仅 operation.py 内部使用（L291/L336/L339/L345-L346），业务代码零调用；`_init_network` docstring L279「从子类实现添加节点和边」是陈旧残留，当前实现唯一来源是注解——静态提取的镜像面完整，框架前缀注入（§2.5）是仅有的例外且设计已处理（不画进图 + notes 说明）。
- **§2.5/§2.6 断言全部命中**：`need_check_game_win` 默认 True（operation.py L97）；`cw_buy_card_action.py` L65 传 False、`sr_operation.py` L24 构造 `OpenAndEnterGame(ctx)`、`handle_game_operations_describe` 位于 service_routes.py L119-L139、`operation_registry.py` 恰 717 行、`make_describe_operation` 的 ctx 占位模式、`mcp.tool(annotations=...)` 注册模式——逐条与代码吻合。
- **测试计划无结构性坑**：fake 类纯反射不实例化（`Operation.__init__` 不执行，test_operation_registry.py L36-L76 已有同模式先例）；fake 类不入扫描根、不走 `resolve_op_class`（规避 `__module__` 守卫与 pytest 无包导入路径问题）——设计的规避决策与 sr-od-test 基础设施（conftest 无强制依赖、外连阻断、落盘重定向）兼容。
- **landing.md 与 design 一致**：三个阶段的设计依据节均真实存在且判据可验证（诊断七枚举 = §2.4.4 表 7 行、§2.2 七条规则 = 实际 7 条）；文件面真实（`test_operation_registry.py` 同目录镜像成立，`mcp.md`/`http.md` 正本存在）；阶段依赖顺序合理，3.2 含「重启 MCP server 后实调」符合 AGENTS.md §6 的代码生效约束。
