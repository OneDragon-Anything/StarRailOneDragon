# MCP tool 实现规范 —— 项目特化落地

> 与 [design-principles.md](design-principles.md) 配对:**design-principles 是「设计原则」**(agent 能力视角,为什么这么设计、tool 该不该有),**本文是「代码怎么写」的落地规范**。
>
> **通用 MCP tool 设计方法论**(tool 命名 / description 契约 / tight input·output schema / annotations / 结构化返回 / actionable error / 读写分离 / token 经济)遵循 **Anthropic 官方 `mcp-server-dev` plugin 的 [`tool-design.md`](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/mcp-server-dev/skills/build-mcp-server/references/tool-design.md)** —— 写 / 改 MCP tool 前先装它(Claude Code 安装见 [setup/ai_coding.md](../../setup/ai_coding.md))。**本文只讲本项目特化的写法与约束**,不重复通用知识。
>
> 适用范围:`src/sr_od/backend/mcp/`(`app.py` / `service_app.py` / `prompts.py`)下所有 `@mcp.tool`。SDK 基线:官方 `mcp` 包内置 `FastMCP`(`from mcp.server.fastmcp import FastMCP`),非第三方 gofastmcp。

## 1. annotations:本项目 tool 怎么分类标

(4 个 hint 的通用定义 / 默认值 / 「是 hint 非安全保证」见官方 mcp-builder。这里只讲本项目分类。)

**双标原则**(对应 design P3,缺一不可):
- docstring 首句点明「观察类 / 操作类」(给人 + 模型读的筛选 prompt);
- `@mcp.tool(annotations=ToolAnnotations(...))` 机器可读(给客户端按副作用筛选 / 自动确认 / 缓存)。

本项目分类:

| 类别 | `readOnlyHint` | `destructiveHint` | 本项目 tool |
|---|:---:|:---:|---|
| 纯观察(只读,不改状态) | `True` | — | `check_game_window` / `capture_game_screen` / `analyze_screen` / `get_run_status` / `list_applications` / `list_operations` / `describe_operation` / `list_mcp_usage_guides` / `get_mcp_usage_guide` / `mys_evaluate_relic_substats` |
| 操作游戏 / 触发运行 / 改配置(改状态非破坏) | 不标(默认非 read_only) | — | `click_game` / `key_tap` / `drag` / `input_text` / `open_game` / `run_one_dragon` / `run_standalone_app` / `run_operation` / `stop_run` / `upsert_screen_area` |
| 不可逆 / 破坏性 | 不标 | `True` | `delete_screen_area`(删 screen_info area) / `close_game`(关游戏) |

**本项目特化**:`open_world_hint` / `idempotent_hint` **默认不标** —— 本项目 tool 都操作**本地游戏运行时**(属「外部世界」交互,`open_world` 保持 MCP 默认语义;`idempotent` 标了也无决策价值,click 幂等无需声明、run 不幂等)。判据:只在「客户端会因此改变确认 / 缓存策略」时才标。

导入:`from mcp.types import ToolAnnotations`(**字段名 camelCase**:`readOnlyHint` / `destructiveHint` / `idempotentHint` / `openWorldHint` / `title`,与 JSON wire 一致;⚠️ snake_case 会被 pydantic 当 extra 忽略、静默失效)。工厂注册的 tool 同理:`mcp.tool(annotations=...)(make_xxx(backend))`。

## 2. Field 参数描述:本项目哪些参数必须加

(通用「用 Pydantic `Field` 加 description / 约束 / `Literal` 枚举」见官方 mcp-builder Phase 2。这里只讲本项目选哪些参数。)

**FastMCP 把函数签名转 JSON schema,但不解析 docstring 的 `Args:` 段成字段 description** —— 参数级说明只能靠 `Annotated[type, Field(description=...)]`。

本项目**必须加 Field description** 的:智能体**不靠参数名 + 类型就懂不了**的 ——
- 布尔开关的隐式语义(`save_image` / `pc_alt` / `block` / `enter` / `use_clipboard`);
- 单位 / 默认特殊的(`press_time`:秒,click 默认 0.1、key 默认 0.0);
- 定位符格式(`op_id` 的 `<module>.<ClassName>`、`screenshot` 的路径 / 图名规则);
- 结构化入参(`args` 的 JSON 可序列化约束)。

**不必加**:纯坐标(`x` / `y`,docstring 已说 1080p 游戏空间)、无歧义标量。

**分工不重复**:Field description 写「参数是什么 / 取值约束」;docstring 写「整体能做什么 / 何时用 / 副作用 / 返回」。同一条信息只留一处。

```python
# 示例(click_game):布尔开关 + 单位特殊的参数加 Field;坐标 x/y 不加
def click_game(
    x: float, y: float,
    press_time: Annotated[float, Field(description="按住时长(秒);click 默认 0.1(游戏识别下限),0=极短按可能无效)")] = 0.1,
    pc_alt: Annotated[bool, Field(description="点击前是否按住 Alt 解锁光标;大世界等 pc_alt=true 画面必需")] = False,
) -> dict: ...
```

## 3. 返回值:形状单一 + 失败走异常通道

(通用结构化返回 / `response_format` / outputSchema 见官方 mcp-builder。这里只讲本项目约束;方法论依据见 design-principles.md P6 / P15。)

- **形状单一(P15)**:一个工具一套返回形状。多字段返回一律 MCP 层 pydantic `*Out` 模型(Field description 进 outputSchema),框架层保持纯 dataclass / 原生类型,`from_backend(**asdict)` 一步转换(样板:`schemas.py` 的 `AnalyzeScreenOut` 族);原子返回(纯路径 / 确认文案)直给 `-> str`,docstring 一行说明返回值语义;**禁 `-> dict`**(生成空 object schema,字段描述无处安放);**禁失败兜底 union**(`T | dict` 使 outputSchema 变包裹形态 `{result: ...}`,模型读到两种形状)。
- **失败走异常通道(P6 三分法)**:backend 校验 / 资源类失败直接透传(如 `BackendNotReadyError`)。sdk 实测(mcp 1.28.1):工具函数抛 Exception → FastMCP 转 `ToolError` → lowlevel 层返回 `CallToolResult(isError=True)` 文本结果,连接不断;HTTP 侧 catch 同一异常返错误响应——同文案对称。**不要 try/except 把失败折进成功结构**:旧模式「返回带 `error` 字段的 dict」已退役——`isError=False` 的失败会骗过按 isError 判成败的客户端。
- **BaseException 防穿透**:停机守卫异常(`StopRunInterrupted`,BaseException 子类)不能裸透传——FastMCP/Starlette 泛型兜底只接 Exception,穿透即 ASGI 层错误 + 连接断。工具层捕获后 `raise RuntimeError(文案) from e` 转普通异常走错误通道(样板:`close_game` / `input_text`;手动端点在 backend 层已有 `stop_guard_exemption` 豁免,此兜底是防御纵深)。
- **与 HTTP 对称(P11)**:同一 backend 方法,MCP 与 HTTP **各自序列化**同构数据(MCP:Out 模型;HTTP:`asdict(dataclass)` / JSON)。别在 MCP 把结构压成多行文本(早期 `check_game_window` 的坑,已修);文本形态仅限「自解释 markdown」类工具(`get_screen_detail`,渲染层 `markdown_render.py`)。

## 4. docstring 三要素

(对应 design P9「docstring 是筛选 prompt」。)每个 tool docstring 至少:

1. **一句话说能做什么 + 首句标「观察类 / 操作类」并带内联定义**——如「观察类(只读,不改任何状态)」/「操作类(会控制游戏)」/「操作类(会改配置文件)」:instructions 是客户端可选注入(server 级定义不保证可见),工具级自带定义不依赖它;
2. **关键约束 / 隐式上下文**(坐标空间、需窗口就绪、单跑道、**操作后需 sleep** 等 —— 把智能体猜不到的显式化);
3. **返回值语义**:原子返回(`-> str`)一行说明返回的是什么;多字段返回的字段语义住 outputSchema(第 3 节),docstring 不抄返回结构。

不啰嗦(context 有限),准确说清即可。参考新 tool(`click_game` / `key_tap` / `drag`)的密度,那是踩坑后校准的基线。

## 5. 命名

(通用「snake_case + 服务前缀 + 动词导向」见官方 mcp-builder。)本项目 tool 按资源分组前缀:game 感知 / 直接动作(`check_game_window` / `click_game` / `capture_game_screen`)、运行(`run_*`)、查询(`list_*` / `describe_*` / `get_run_status`)、screen_info CRUD(`upsert_screen_area` / `delete_screen_area`)。参数名无歧义(`op_id` 不写 `id`,`use_clipboard` 不写 `way`)。

## 6. 借鉴官方 Phase 4 evaluations(本项目缺口,待补)

官方 mcp-builder 把「造 evaluations」作为第 4 阶段:写完 MCP server,造 **10 个只读、复杂、可验证** 的问题,测 LLM 能否用好它(每题:独立 / 只读 / 复杂(多 tool 调用)/ 现实 / 可验证(单一明确答案)/ 稳定)。详见 mcp-builder `reference/evaluation.md`。

本项目 MCP tool 目前只有**单元测试**(mock backend,验证委托与返回结构),**缺这套「LLM 好用度」评估** —— 即「智能体光看 tool 描述 / 参数 / 返回,能否选对工具、传对参数、读懂结果」。后续可针对本项目典型场景(查运行态 / 进游戏 / 分析画面 / screen_info 建模)造问题集,验证描述 / 参数 / 返回是否让 LLM 用得准,反哺本文第 2 / 4 节。

## 7. 改动同步 checklist

改 / 加 MCP tool 后逐条对照:

- [ ] docstring 三要素齐 + 首句「观察 / 操作」标注;
- [ ] `annotations` 按第 1 节分类标了(观察 `readOnlyHint=True` / 破坏 `destructiveHint=True`,**字段名 camelCase**);
- [ ] **读写分离**:单 tool 不混观察 + 操作(通用硬要求);相似操作 tool(`click_game` / `key_tap` / `drag`)描述**互指**何时用另一个(disambiguate);
- [ ] `title` annotation(可选):Anthropic Directory 提交时每个 tool 必须有 title;本项目不提交 Directory,按需作 UI 显示名;
- [ ] 难懂参数加了 `Field description`;
- [ ] 返回形状按第 3 节(多字段 `*Out` / 原子 `-> str`;失败走异常通道,禁兜底 dict / union;BaseException 转 RuntimeError);
- [ ] HTTP 对称能力是否也要补(两个适配器消费者都用 → 放 backend 共享,见 design P11);
- [ ] 测试(`sr-od-test/test/sr_od/backend/`)断言对齐新返回;
- [ ] `ruff check` 改动文件 + 经 daemon 重启 server 验证 tool 注册。

## 相关

- [design-principles.md](design-principles.md) —— 设计原则(本文上游,为什么这么设计)
- [mcp.md](mcp.md) —— 适配器说明与接入（传输 / 配置 / 跨工具约定；工具契约单一源在各 tool docstring，无集中清单）
- [http.md](http.md) —— HTTP 适配器(返回结构对称基准)
- Anthropic 官方 `mcp-server-dev` plugin([tool-design.md](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/mcp-server-dev/skills/build-mcp-server/references/tool-design.md))—— 通用 MCP tool 设计方法论(本文只叠加项目特化;安装见 [setup/ai_coding.md](../../setup/ai_coding.md))
