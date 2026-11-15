# 2026-11-16-pf-app-skeleton 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 仅对本阶段改动文件全部通过；
- 共享选人单测全量一次通过（`uv run pytest sr-od-test/test/sr_od/application/apocalyptic_shadow/test_strategy.py -q`）；
- 提交：逐文件点名 `git add`，提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 app 六件套实现

**范围**：新建 `src/sr_od/application/pure_fiction/` 六文件；共享选人逻辑上移 `treasures_lightward/random_team.py`（AS 改用，strategy.py 删除）。
**设计依据**：design.md §1.3、§2
**文件面**：`src/sr_od/application/pure_fiction/**`（新建）、`src/sr_od/application/treasures_lightward/random_team.py`（新建）、`src/sr_od/application/apocalyptic_shadow/*`（改用共享）、`sr-od-test/test/sr_od/application/apocalyptic_shadow/test_strategy.py`（随迁扩条目）
**依赖**：无
**优先级建议**：8
**完成判据**：节点图对齐 §2.1；lint + 导入冒烟通过；共享单测全绿；常规检查。
**验收凭据形式**：diff 对照 + 单测输出。

## 3.2 注册与实机端到端

**范围**：重启 MCP server；`run_standalone_app(app_id='pure_fiction')` 端到端。
**设计依据**：design.md §2.1、§3、§4
**文件面**：无代码改动（问题定位按 od-dev-write-application §10 分层）
**依赖**：3.1
**优先级建议**：9
**完成判据**：端到端四段走通（大世界收）；§4 核销表逐条记录；常规检查（无代码改动跳过 lint/测试子项）。
**验收凭据形式**：MCP 工具输出（run 终态）。

## 3.3 提交与正本更新

**范围**：分批提交（代码 / 文档）；正本 `docs/develop/sr_od/application/pure_fiction/design.md`（as-built，无状态口径）。
**设计依据**：AGENTS.md 文档规范；landing 首节
**文件面**：本迭代全部文件 + 正本
**依赖**：3.2
**优先级建议**：6
**完成判据**：`git show --stat` 入库面 = 申报面；正本与实现一致、不引 changes/。
**验收凭据形式**：git show --stat + 文档对照。

## 正本更新清单

- `docs/develop/sr_od/application/pure_fiction/design.md`（新建正本）：app 结构、节点图、失败语义、config、复用 op 清单 ← 3.1/3.2/3.3
