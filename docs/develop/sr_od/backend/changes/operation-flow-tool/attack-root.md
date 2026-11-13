# operation-flow-tool 设计对抗报告（无前提 / 规范遵循 / 治本）

- 攻击对象：本目录 design.md（193 行）、landing.md、README.md。
- 判罚依据：docs/develop/harness/iteration-design.md（§2/§5/§7/附录）；项目 AGENTS.md「文档规范」「测试规范」「Operation 最佳实践」；正本 docs/develop/sr_od/backend/mcp.md、http.md。
- 代码证据均按当前工作区实读核对（one_dragon/base/operation/operation.py、operation_edge.py、operation_node.py；sr_od/backend/operation_registry.py、mcp/app.py、mcp/service_app.py、http/service_routes.py；sr_od/challenge_mission/use_trailblaze_power.py；sr_od/application/echo_of_war/challenge_ehco_of_war.py；sr_od/application/currency_war/operations/cw_op/cw_buy_card_action.py；sr_od/operations/sr_operation.py、operations/move/move_directly.py；sr-od-test/test/sr_od/backend/）。
- 编号 B1…B12；处置取值：打回修订 / 接受风险 / 文字修正。

## B1 断名边（missing_node）的表示三处互相矛盾，flow 挂靠位置无规范可依

- 定位：design.md §2.2 规则 3（L53）、§2.3 返回结构注释（L84 `'to': str|None, # to=None = 断名边（missing_node）`）、§2.4.2 示例（L112 `├─(失败)→ ✗节点不存在「阵亡传送恢复」`）。
- 攻击内容：同一诊断在三处给出三种互斥表示。①规则 3 定义 missing_node = `from_name` 匹配不到节点——悬空端是 **from**；②edges[] 结构却把可空端标在 `to` 上，而按规则 2「to = 边注解所在方法自己的节点」，to 结构上恒可解析，`to=None` 在 missing_node 场景不可能出现；③§2.4.2 示例把断名边画成节点「传送」的**出边**（箭头指向不存在的目标），但按提取语义该边注解挂在 transport 方法上、方向是 阵亡传送恢复→传送（入边），且 flow 格式「按节点分组、边行缩进挂靠」以 from 节点为分组锚——from 节点不存在时这条边**没有任何可挂靠的分组**，示例给的答案（挂在 to 节点下、方向反转）与规则 2/3 均矛盾。实现者无法凭本文落笔：断名边在 `edges[]` 里 from/to 各填什么、在 `flow` 里挂在哪、箭头朝哪，三个问题都没有自洽答案。
- 依据：design.md §2.2 规则 2/3、§2.3、§2.4.2；对照 operation.py L255-L261（运行时对 from/to 双端校验，desc 的 to 由 L252 强制填充为本方法节点）；iteration-design.md §5 硬规则 2（实现者无需再设计）。
- 建议处置：**打回修订**。统一裁定：missing_node 边的 `from` 填原始未匹配字符串（`to` 恒为方法自身节点名）；flow 渲染位置明确（建议挂在 to 节点块内、以 `←✗` 入边形态表达并注明缺失源），示例同步重画。

## B2 边属性归一归错了类：「直接读 desc 不重算」按字面实现会对健康 op 误标兜底、误报 duplicate_fallback_edge

- 定位：design.md §2.2 规则 4（L54）、§2.4.4 表 duplicate_fallback_edge 行与末段「语义依据」（L159）。
- 攻击内容：规则 4 声称「`OperationEdgeDesc.__init__` 已归一：`status is not None` 时 `ignore_status` 恒 False，不重算」。事实相反：`OperationEdgeDesc.__init__` 对 `ignore_status` 是裸赋值（operation_edge.py L61），归一发生在**运行时构建 `OperationEdge` 时**（operation_edge.py L36 `self.ignore_status: bool = False if status is not None else ignore_status`）。`node_from` 装饰器的 `ignore_status` 默认值是 True（operation_edge.py L68），即**每条带 status 的边在 desc 层的原始值都是 True**。按规则 4 字面执行（读 desc 原值、不重算）：①所有 status 边的 `edges[].ignore_status` 错为 True，flow/mermaid 按 §2.4.2/§2.4.3 规则全部多出「·兜底」标记；②duplicate_fallback_edge「同 (from, success 方向) 下 ignore_status=True 的边 >1 条」会对完全健康的 op 误报——以本设计自己的旗舰示例 UseTrailblazePower 为证：`back_at_last` 的 `@node_from('点击挑战后确认', status='开拓力弹框-取消')` 与 `@node_from('点击挑战后确认', status='退出关卡按钮')`（use_trailblaze_power.py L339-L340）两条 status 边 desc 原值均 ignore_status=True，成功方向即刻凑满 2 条 → 假警告。而设计 §2.4.2 自己的示例把 status 边渲染成不带兜底（正确口径），与规则 4 直接打架。同族引文错误：§2.4.4 末段把「一个节点应该最多只有一条边忽略返回状态」注为 `OperationEdgeDesc` docstring（operation_edge.py L39-L41），实际该句在 **OperationEdge** 的 `ignore_status` 字段 docstring 里。
- 依据：operation_edge.py L36/L61/L64-L93（node_from 默认 ignore_status=True、desc 裸存）；operation.py L263-L269（运行时以 desc 字段构造 OperationEdge，归一在 OperationEdge.__init__）；use_trailblaze_power.py L338-L341；iteration-design.md §7 核一（结论只看证据）。
- 建议处置：**打回修订**。规则 4 改为：静态侧复算归一（镜像 operation_edge.py L36 的 `status is not None → ignore_status=False`），并更正归一出处与 L39-L41 引文归属。

## B3 治本缺口：「静态诊断把运行时校验提前」与按需工具机制不匹配，更小的治本路径（扫描根全量诊断回归测试）未纳入也未在取舍中讨论

- 定位：design.md §1.3 解决项 2（L25）、§2.7 测试计划、§3 关键取舍。
- 攻击内容：§1.1 症状二是「编排错误全部推迟到运行期才发现：写错一个 from_name 要等到跑起来才炸」；§1.3 宣称解决方案是「静态诊断把运行时校验提前」。但交付物是一个**按需调用的只读 MCP 工具**——没有人调用它，校验就没有被提前任何一步；机制上并不成立「提前」，只成立「可以提前」。更小且制度化的治本路径被绕开：对 `scan_operations` 全量结果逐类跑静态提取、断言零 error 诊断的回归测试（核心函数已建、约十行，CI 每次提交自动把关，恰好兑现「校验前移」并能顺带清点存量坏边）。该路径既未进 §2.7，也未在 §3 关键取舍中作为被放弃的备选出现——按 AGENTS.local.md §1 根源两问「症状修法必须显式声明战术权衡」，当前是对症状二的未声明症状修法。§2.7 第 3 组只拿 MoveDirectly 单类过解析层，理由「属 registry 既有覆盖面」混淆了解析覆盖与诊断覆盖两回事。
- 依据：design.md §1.1/§1.3/§2.7/§3；operation.py L258（运行期 raise 的唯一防线现状）；iteration-design.md §7 核三（说不清治本 = 打回）；sr-od-test 既有全量回归惯例（AGENTS.md「测试规范」§10.1：新功能测试锁设计约定）。
- 建议处置：**打回修订**（二选一）：① §2.7 增第 5 组「扫描根全量 op 零 error 诊断」回归测试（warn 白名单机制随之定）；或 ② 明确改口为「提供按需查看能力，不做制度化前移」并在 §3 关键取舍补该取舍的理由与后续排期。
- 附：跨件半问核验——静态反射读取 op 元数据已有架构级归宿（operation_registry 单源），本设计复用其解析而非另起炉灶，不构成同族第二件症状补丁，此判据不适用。

## B4 §2.4.2 示例以真实 op 之名呈现虚构数据，计数、方法名、边、入边来源均与代码不符

- 定位：design.md §1.1（L13「12 节点 24 边」）、§2.4.2 示例块（L108-L118）。
- 攻击内容：实读 use_trailblaze_power.py：`@operation_node` 14 处、`@node_from` 20 处——「12 节点 24 边」两个数字都错。示例中 `method=confirm_click`、`method=choose_times` 方法不存在（真实为 `confirm_after_click_challenge`、`_before_click_challenge`）；「传送→(成功·status=开拓力弹框-取消)→点击挑战后确认」这条边不存在（真实该 status 边是 点击挑战后确认→完成后退出，L339）；「点击挑战后确认 ←入: 传送, 点击挑战, 战斗结果处理」错误——真实入边只有 点击挑战（L143）；「(成功)→ 选择配队」不存在（真实仅 success=False·status=无对话框 一条，L167）；「(兜底·成功)」的记号顺序与 §2.4.2 自己规定的标注序（success → ·status → ·兜底）不一致。另外 §1.1「challenge_ehco_of_war.py 近 30 边」实数为 23（grep 计数），「近 30」失准。该示例是 §2.7 第 1 组「断言 flow 文本关键行」与 landing 3.1 判据「对照 §2.4.1/§2.4.2」的直观参照，虚实混杂会直接误导 fixture 编写。
- 依据：use_trailblaze_power.py L72-L345 逐条计数；challenge_ehco_of_war.py @node_from 23 处；iteration-design.md §5 硬规则 1（依据就地标注须为真）。
- 建议处置：**文字修正**。示例标注「格式示意、非真实 op 数据」，或以真实类重新生成；计数更正为 14 节点 20 边 / 23 边。

## B5 「实例化即炸」表述与代码不符：断名校验在 execute 路径触发，构造不炸

- 定位：design.md §3 关键取舍第一条（L190「能覆盖『实例化即炸』的断名错误（实例化路径在 `_init_network` 就 raise）」）；§1.1「在 op 实例化运行时才校验」。
- 攻击内容：`_init_network`（operation.py L274）由 `_init_before_execute`（L197）调用，后者在 `execute()`（L399）里执行；`Operation.__init__`（L90-L162）不触碰节点网络。带断名边的 op 可以正常构造，首次 raise 在运行时。§3 用「实例化即炸」论证静态扫描优于「实例化后读成品图」，论据失真（真实障碍是 `SrOperation.__init__` 构造 `OpenAndEnterGame(ctx)` 的副作用依赖与需要可用 ctx——这一条本身成立，决策无需失真论据支撑）。
- 依据：operation.py L90-L162（__init__ 无网络构建）/L197/L274/L399；sr_operation.py L24。
- 建议处置：**文字修正**。改为「execute 前的 `_init_before_execute` 才构建网络并 raise」；§1.1「实例化运行时」改为「运行时」。

## B6 报错文案要求与「复用不重写」两头落空

- 定位：design.md §2.3（L65「App 类不在扫描根内，短名查不到属预期，报错文案提示用完整 op_id」）与 §2.6（L172「复用 …`_short_name_not_found_error`（不重写解析）」）。
- 攻击内容：`_short_name_not_found_error` 的现成文案是「未找到类名 … ；完整清单用 list_operations 查」（operation_registry.py L558-L563），并不含「用完整 op_id（App 类不在扫描根）」的提示。§2.3 的文案要求与 §2.6 的原样复用不可同时满足，实现者须自行二选一（包一层附加提示 = 某种重写；原样复用 = 违 §2.3）。
- 依据：operation_registry.py L558-L563；iteration-design.md §5 硬规则 2。
- 建议处置：**文字修正**。明确：flow 工具层捕获后追加一句 App 类引导（允许，不改 registry 函数本体），或删除 §2.3 的文案主张。

## B7 阶段 3.2 验收凭据「+ pytest」无着落：挂接层零自动测试的决定未声明

- 定位：landing.md 3.2（L27-L36）；design.md §2.7。
- 攻击内容：3.2 完成判据含「短名/完整 op_id/歧义三种解析形态行为一致」，凭据形式写「MCP 实调返回 JSON 对照 + pytest」，但该阶段文件面没有任何测试文件，§2.7 四组用例也全部落在核心模块（operation_flow.py）——「pytest」指代不明，判据不可验证。同时既有挂接层测试是子集式断言（test_mcp_app.py L63-73 `<=`、L301 `<=`），新增工具/端点不会让任何现有测试变红：新 MCP 工具与 HTTP 端点将带着零自动测试上线，而 test_mcp_app.py 对 describe_operation 等同族工具有委托测试先例（L351-L380）。「不为薄挂接层写测试」是可辩护的取舍，但须在 §2.7/§3 显式声明，而不是留一个悬空的「pytest」。
- 依据：landing.md 3.2；design.md §2.7；test_mcp_app.py L59-73/L297-301/L351-L380；AGENTS.md「测试规范」§10.5-3（修改代码后同步更新测试）；iteration-design.md §7 核一（判据可验证）。
- 建议处置：**文字修正**。凭据改为「MCP 实调 JSON 对照 + 3.1 测试回归」，或在 3.2 文件面/§2.7 补挂接层最小测试（注册存在 + readOnlyHint + 一条委托路径）。

## B8 自造术语首现未定义、MCP 写作惯例出处未指针

- 定位：design.md §1.3（L25「断名边」「兜底边」首现）、§2.3（L95「tool docstring 按 MCP 惯例写全」）。
- 攻击内容：「断名边」首现于 §1.3，全文无显式定义（定义实质散落在 §2.3 注释与 §2.4.4 missing_node 行，且互相矛盾，见 B1）；「兜底边」首现于 §1.3，语义定义在 §2.4.2 图例与 §2.4.4。按 AGENTS.md「文档规范」：首次出现的项目术语给定义 + 例子。「MCP 惯例」有单一源文档 docs/develop/sr_od/backend/mcp-implementation.md（mcp/app.py 模块头 L16-L17 指定），设计未引出处。
- 依据：AGENTS.md「文档规范」（禁自造黑话、首现给定义）；mcp/app.py L16-L17；design.md §1.3/§2.3。
- 建议处置：**文字修正**。§1.3 首现处各给一句定义；§2.3 补 mcp-implementation.md 指针。

## B9 正本更新清单粒度欠细：两处正本必改点不在清单行字面覆盖内

- 定位：landing.md「正本更新清单」（L50-L51）；正本 mcp.md L7、http.md L47。
- 攻击内容：mcp.md 工具节首行「34 个 `@mcp.tool`」是硬计数，加工具后须同步改 35，该行不在「工具表 + 要点」的字面范围；http.md「与 MCP 的关系」节整段枚举自定义 op 端点与 MCP 工具的对应关系（`/game/operations` ↔ `list_operations` 等），新端点 `/game/operations/flow` ↔ `describe_operation_flow` 应补入该段，亦不在「端点表」字面范围。末阶段判据是「清单清零」，粒度漏项会让清零后正本仍与实现不一致。
- 依据：mcp.md L7/L9-L47；http.md L47；iteration-design.md §3.2。
- 建议处置：**文字修正**。清单两行细化为「mcp.md：工具表 + 工具计数行 + 要点」「http.md：端点表 + 与 MCP 的关系段」。

## B10 状态滞后：对抗已在进行，README 进度区与 design §0 仍是前置态

- 定位：README.md 进度区（L10-L13「迭代设计:草案 / 设计对抗:未开始」）；design.md §0（L6「状态：草案」）。
- 攻击内容：本报告落盘即「设计对抗」已实际发生，README 仍标「未开始」且无报告链接；按生命周期（iteration-design.md §6：草案 → 对抗审中 → 定稿，状态由总纲 §0 表达），对抗批期间 §0 应为「对抗审中」、README 进度区应更新并链接报告。另注意：iteration-design.md 附录 D 模板报告名为 attack.md，本报告按派工指令落 attack-root.md，README 收录时须用实际文件名，避免再挂死链。
- 依据：iteration-design.md §4/§6/附录 D；README.md 现状。
- 建议处置：**文字修正**（本报告落盘后随即更新两处状态与链接）。

## B11 mermaid 边标签未纳入「永不炸语法」保障

- 定位：design.md §2.4.3（L130-L132「label 引号包裹节点 cn——中文、空格、括号等永不炸语法」与「边标注 …放 `-->|…|`」）。
- 攻击内容：引号保障只覆盖节点 label；边标签 `-->|成功·status=<值>·兜底|` 中 `<值>` 是业务自由字符串（status 常量遍布全仓，无字符集约束），含 `|`、`"` 等字符即破坏 mermaid 语法。设计目标句「永不炸语法」对边标签不成立。
- 依据：design.md §2.4.3；mermaid flowchart 语法（边标签同样支持 `-->|"…"|` 引号形态）。
- 建议处置：**接受风险**（或一行文字修正：边标签同样引号包裹）。

## B12 游戏无关的核心提取落在 sr_od 侧，归属张力与 SR→ZZZ 同步义务未声明

- 定位：design.md §1.3「不改 one_dragon 公共框架」、§2.6（L173「只依赖 inspect + one_dragon…数据类」）。
- 攻击内容：按设计自述，operation_flow.py 核心只读 one_dragon 注解数据类、零 SR 依赖——这是游戏无关能力，而仓库架构划分是 one_dragon=公共框架（游戏无关）、sr_od=星铁业务（AGENTS.md §1.1）。设计的取舍声明只覆盖「不动既有框架代码」（公共包改动需跨项目同步），没有覆盖「新增的游戏无关代码为何不进公共包」这一归属决策，也未提 SR→ZZZ 同步件义务（本机协作约定：共享模式改动写同步文件）。ZZZ 侧将来要么重复实现、要么二次搬迁。
- 依据：design.md §1.3/§2.6；AGENTS.md §1.1（one_dragon=游戏无关公共框架）；AGENTS.local.md §2.2（SR→ZZZ 同步）。
- 建议处置：**接受风险**（补声明：§3 关键取舍加一段「核心为游戏无关、暂留 SR 侧的理由 + 落地时写 SR→ZZZ 同步件」；若裁定进公共包则改 §2.1 落点）。

## 已核验通过面（零发现项）

- 结构规范：四类文档齐（README/design/landing，无详设合法——§0 已声明单文档）；阶段小节七件齐（3.1/3.2/末阶段逐项核对）；首节「完成前常规检查」自包含且引用的项目 AGENTS.md 章节真实存在。
- 写作硬规则 3（无过程叙事）：三份文档无「本轮/修订后/已改/变更史」类措辞。
- 双层文档流铁律反向检查：grep 全 docs 树，无 changes/ 之外的长期存活物引用 operation-flow-tool/operation_flow/describe_operation_flow；design 引用的正本（mcp.md/http.md）与测试路径均真实存在且方向合法（changes/ → 正本）。
- 引用锚与行号：design 引用的框架行号逐条核对为真——operation.py L220-L272/L255-L315/L258/L244/L311/L315/L324-L350/L359/L571-L572、operation_edge.py L39-L41（内容为真，归属见 B2）、service_routes.py L119-L139、sr_operation.py L24、cw_buy_card_action.py L65、operation_registry.py 717 行、`resolve_op_class`/`match_short_name`/`_short_name_not_found_error`/`_SCAN_ROOTS` 排除 Application 均属实。
- 挂接模式与正本契约一致：工厂模式（make_describe_operation 闭包 + 工具层 except 返 `{error}`、观察类不设 success 键）与 mcp.md/http.md 描述及 service_app.py/service_routes.py/app.py 现状吻合；`ToolAnnotations(readOnlyHint=True, title=…)` 注册先例存在（app.py L546-L551）；HTTP「业务失败 200 + {error}」惯例一致；landing 3.2 的「重启 MCP server 后实调」符合项目 AGENTS.md §6。
- 静态提取的镜像论证总体成立：getmembers 类级 vs 实例级口径（isfunction/ismethod/staticmethod 剔除）、MRO 重写节点消失、起点判定 L306-L315 镜像（含入度表在注入前构建）、遍历序与兜底边「后遍历者覆盖」语义（L571-L572）、`node_to_name` 不读的污染规避、`need_check_game_win` 不做静态推断的理由（cw_buy_card_action.py L65 实证）均与代码对得上。
- 边界对照：§1 声称面与 §2 覆盖面逐项对齐（HTTP 镜像/诊断枚举七枚=landing「七枚举」/docstring 要求/mermaid 已由 §1.3 不解决项反向声明）；无未声明的偷渡面。
- 测试计划合规：镜像路径、fake 类零副作用、不连真游戏、MoveDirectly 真实类存在（move_directly.py L30）。

## 总体结论

**需修订**。必修：B1（断名边表示三处矛盾）、B2（边属性归一归错类，误标兜底+误报诊断）、B3（「校验提前」名不副实，全量诊断回归测试或显式改口二选一）。B4-B10 为文字修正（建议随必修一并处理，均为低成本）；B11/B12 接受风险（B12 建议补一段声明）。修订完成后按 iteration-design.md §5 硬规则 4 做 design↔landing↔README 全量同步复查，再进入定稿试读。
