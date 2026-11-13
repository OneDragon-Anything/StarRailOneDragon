# operation-flow-tool 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/ -m "not slow"` 相关子集）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 核心提取模块 + 测试

**范围**：新建 `src/sr_od/backend/operation_flow.py`（静态提取 / 诊断 / 文本图渲染 / 短名与完整 op_id 解析复用 `operation_registry`）+ `sr-od-test/test/sr_od/backend/test_operation_flow.py`。边界：不含 MCP/HTTP 挂接与正本文档。
**设计依据**：design.md §2.2（提取语义）、§2.4（flow 格式与诊断枚举）、§2.5（框架前缀）、§2.7（测试计划）
**文件面**：`src/sr_od/backend/operation_flow.py`（新建）、`sr-od-test/test/sr_od/backend/test_operation_flow.py`（新建）
**依赖**：无
**优先级建议**：9
**完成判据**：
- 提取行为对照 design.md §2.2 七条规则逐条成立（测试覆盖 §2.7 四组用例）；
- 诊断 code 七枚举各有最小用例断言（含 `duplicate_fallback_edge` 的生效边指认）；
- 完成前常规检查（本文首节）
**验收凭据形式**：pytest 测试名

## 3.2 MCP / HTTP 挂接 + 正本文档

**范围**：`service_app.py` 工厂 + `app.py` 注册 + `service_routes.py` 端点；重启项目 MCP server 后实调 `describe_operation_flow` 验证（拿一个真实 op 如 `UseTrailblazePower` 与一个断名/不可达构造对照）。边界：不改 `operation_registry.py` / 公共框架。
**设计依据**：design.md §2.3（工具契约）、§2.6（复用与落点）
**文件面**：`src/sr_od/backend/mcp/service_app.py`、`src/sr_od/backend/mcp/app.py`、`src/sr_od/backend/http/service_routes.py`
**依赖**：3.1
**优先级建议**：8
**完成判据**：
- MCP 返回结构字段与 design.md §2.3 逐字段一致；短名/完整 op_id/歧义三种解析形态行为一致；
- HTTP `GET /game/operations/flow?op_id=` 与 MCP 同契约单源；
- 完成前常规检查（本文首节）
**验收凭据形式**：MCP 实调返回 JSON 对照 + pytest

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：全部落地阶段
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单

- `docs/develop/sr_od/backend/mcp.md`：工具表 + 要点 ← 3.2
- `docs/develop/sr_od/backend/http.md`：端点表 ← 3.2
