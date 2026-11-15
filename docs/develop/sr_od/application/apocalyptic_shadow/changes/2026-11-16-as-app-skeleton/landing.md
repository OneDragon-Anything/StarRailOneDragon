# 2026-11-16-as-app-skeleton 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 仅对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/ -m "not slow"` 相关子集；本迭代无存量测试受影响，新增测试见阶段判据）；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 app 五件套与编排实现

**范围**：新建 `src/sr_od/application/apocalyptic_shadow/` 全部七个文件（见 design.md §4 表）；不动 treasures_lightward 包内任何 op。
**设计依据**：design.md §3（流程）、§4（结构）、§5（失败语义）、§6（run_record）、§7（config）、§8（策略）
**文件面**：`src/sr_od/application/apocalyptic_shadow/**`（新建）
**依赖**：无
**优先级建议**：8
**完成判据**：
- 节点图与 design.md §3 一致：有且只有一个 `is_start_node`；每个节点都有 `@node_from` 串接；失败语义逐节点对齐 §5；
- `uv run python -c "import sr_od.application.apocalyptic_shadow.apocalyptic_shadow_app"` 无导入错误；
- 完成前常规检查（本文件首节；测试子集 = `uv run pytest sr-od-test/ -m "not slow" -k "apocalyptic or treasure"` 全绿，无相关存量测试则输出为空亦算通过）。
**验收凭据形式**：代码 diff 对照 design.md §3/§5；导入冒烟输出。

## 3.2 注册确认与实机端到端

**范围**：重启项目 MCP server（改了 Python 代码必须做）；`list_applications` 不含本 app 属预期（`DEFAULT_GROUP=False` 只列默认组，注册验证走 `run_context.is_app_registered` / factory 扫描结果）；`run_standalone_app(app_id='apocalyptic_shadow')` 实机跑一遍；MCP 配置工具读写验收（config_router 已补 `apocalyptic_shadow` 条目）。
**设计依据**：design.md §3（四段）、§4（config 路由显式注册制）、§9（验收判据 2/3/4）、§10（核销表）
**文件面**：无代码改动（发现问题时按 od-dev-write-application §10 分层定位，改动回到 3.1 文件面 + `src/sr_od/backend/config_router.py` / `src/sr_od/backend/mcp/config_app.py` 两处共享层）
**依赖**：3.1
**优先级建议**：9
**完成判据**：
- `list_applications` 含 `apocalyptic_shadow`；
- 端到端四段走通（主界面起、大世界收），运行记录成功；
- §10 核销表逐条记录核对结论（核对不了的下期挂账，如实标注）；
- `describe_config` / `get_config` / `set_config(claim_rewards)` 各一轮成功；
- 完成前常规检查（本文件首节；无代码改动则跳过 lint/测试子项）。
**验收凭据形式**：MCP 工具输出（应用列表、run 终态、配置读写回显）。

## 3.3 子agent无前提实现评审与修订

**范围**：以自包含任务书派子agent对抗评审实现（核一无前提 / 核二规范遵循 / 核三治本，攻击面见 iteration-design.md §7）；阻塞项必须修，建议项逐条裁定。
**设计依据**：iteration-design.md §7；design.md 全文
**文件面**：`src/sr_od/application/apocalyptic_shadow/**`、`sr-od-test/**`（评审发现的补测）、本迭代目录文档
**依赖**：3.2
**优先级建议**：7
**完成判据**：
- 评审报告落 `attack.md`（与本文件同目录）；阻塞项修完且复验；建议项逐条有裁定（采纳/留档）；
- 修订涉及行为时回归 3.2 相应判据；
- 完成前常规检查（本文件首节）。
**验收凭据形式**：attack.md 报告 + 修订 diff。

## 3.4 分阶段提交

**范围**：3.1 完成后提交一次（app 代码 + 设计文档），3.3 收敛后提交一次（评审修订 + 测试）。逐文件点名 add。
**设计依据**：AGENTS.md「提交流程与协作边界」；本文件首节
**文件面**：本迭代声明过的全部文件
**依赖**：3.1（首次提交）、3.3（末次提交）
**优先级建议**：5
**完成判据**：`git show --stat` 入库面 = 申报面；工作区无本迭代遗留未提交文件（`git status` 核对）。
**验收凭据形式**：git show --stat 输出。

## 末阶段：正本更新

**范围**：按「正本更新清单」把本迭代结果沉淀为正本文档（as-built 设计正文，无状态口径）。
**设计依据**：AGENTS.md「文档规范·双层文档流」
**文件面**：`docs/develop/sr_od/application/apocalyptic_shadow/design.md`（正本，新建）
**依赖**：3.3
**优先级建议**：6
**完成判据**：正本只写结构/语义/接口契约/数据流/边界/动机与约束，与代码现状一致；正本不引用 changes/ 内容。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `docs/develop/sr_od/application/apocalyptic_shadow/design.md`（新建正本）：app 结构、节点图、失败语义、config、复用 op 清单 ← 3.1/3.2/3.3 全部阶段
