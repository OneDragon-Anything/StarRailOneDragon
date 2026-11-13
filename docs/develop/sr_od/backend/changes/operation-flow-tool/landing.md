# operation-flow-tool 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/ -m "not slow"` 相关子集）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 核心提取模块 + 测试

**范围**：新建 `src/sr_od/backend/operation_flow.py`（静态提取 / 诊断 / 文本图渲染 / 短名与完整 op_id 解析复用 `operation_registry`）+ `sr-od-test/test/sr_od/backend/test_operation_flow.py`。边界：不含 MCP/HTTP 挂接与正本文档。
**设计依据**：design.md §2.2（提取语义）、§2.4.1-§2.4.4（排序 / flow 格式 / mermaid / 诊断枚举）、§2.5（框架前缀）、§2.7（测试计划）
**文件面**：`src/sr_od/backend/operation_flow.py`（新建）、`sr-od-test/test/sr_od/backend/test_operation_flow.py`（新建）
**依赖**：无
**优先级建议**：9
**完成判据**：
- 提取行为对照 design.md §2.2 六条规则逐条成立（测试覆盖 §2.7 六组用例）；
- `ignore_status` 静态归一与断名边图论口径有专项回归锚点（§2.7 第 1/3 条：status 边不误标兜底；断名边不计入度/不进 BFS/不进 `←入:` 计数/edges[] 垫底）；
- 诊断 code 七枚举各有最小用例断言（含 `duplicate_fallback_edge` 双模 message、同名双显式起点归 `duplicate_node_name` 不报 `multiple_start`、`no_start` 下不逐节点报 unreachable）；
- 全量回归测试：`scan_operations` 全部 op 零 error 级诊断（§2.7 第 5 条，治本制度化锚点）；
- flow 显示对照 §2.4.1/§2.4.2（BFS 序、头部摘要+图例行、`←入:` 仅入边≥2 标注、断名边挂 to 侧 `←✗` 呈现、终点/不可达标注）；mermaid 渲染对照 §2.4.3（引号 label / 引号边标注 / classDef / 断名幽灵节点 / `"` 全角替换）；
- 完成前常规检查（本文首节）
**验收凭据形式**：pytest 测试名

## 3.2 MCP / HTTP 挂接

**范围**：`service_app.py` 工厂 + `app.py` 注册 + `service_routes.py` 端点；重启项目 MCP server 后实调 `describe_operation_flow` 验证（拿一个真实 op 与一个断名/不可达构造对照）。边界：不改 `operation_registry.py` / 公共框架；不含正本文档（归末阶段）。
**设计依据**：design.md §2.3（工具契约）、§2.6（复用与落点）
**文件面**：`src/sr_od/backend/mcp/service_app.py`、`src/sr_od/backend/mcp/app.py`、`src/sr_od/backend/http/service_routes.py`
**依赖**：3.1
**优先级建议**：8
**完成判据**：
- MCP 返回结构字段与 design.md §2.3 逐字段一致；短名/完整 op_id/歧义三种解析形态行为一致；
- HTTP `GET /game/operations/flow?op_id=&mermaid=` 与 MCP 同契约单源；
- 完成前常规检查（本文首节）
**验收凭据形式**：MCP/HTTP 实调返回 JSON 对照（挂接层无新增测试，契约断言已由 3.1 覆盖核心函数）

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：全部落地阶段
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单

- `docs/develop/sr_od/backend/mcp.md`：工具表补 `describe_operation_flow` 行 + 开头工具计数行（34→35）+ 要点 ← 3.2
- `docs/develop/sr_od/backend/http.md`：端点表补 `GET /game/operations/flow` 行 + 「与 MCP 的关系」相应段落（如有）← 3.2
