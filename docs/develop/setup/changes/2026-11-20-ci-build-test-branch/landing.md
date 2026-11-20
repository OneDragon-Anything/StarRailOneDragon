# CI 集成测试分支（Build Test Branch）落地

## 影响面申报（线级一份，设计定稿时冻结）

### 代码文档面

- tools/ci/build_test_branch.py（新增）
- .github/workflows/build-test-branch.yml（新增）
- .github/workflows/test-check.yml（触发扩展 / workflow_run / checkout / 失败 issue 通知）
- docs/develop/setup/repositories.md（新增，分支与 CI 机制正本）
- AGENTS.md（§1.1 目录结构 tools/ 行补「ci」，末阶段）

### 共享资产面

- 无（不碰 uv.lock、screen_info、skills、公共框架包）

### 共享资源面

- 无（纯 CI 与脚本文件：不需实机、不重启 MCP server、不触发任何外发动作；schedule/workflow_run 触发因默认分支前置处于休眠，design §2.3-1）

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动的 `.py` 文件全部通过；
- 受影响测试：本迭代无 `src/` 改动、无测试改动（取舍见 design §2.4），pytest 项不适用；
- 测试仓同步：无测试仓改动，不适用；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号；提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 build-test-branch 移植

**范围**：新增 `tools/ci/build_test_branch.py`（照搬 ZZZ 同名脚本 + BASE_BRANCH 基线参数化：design §2.2-1 全量清单——git 实参 5 处 + 文案/docstring）与 `.github/workflows/build-test-branch.yml`（照搬 + env `BASE_BRANCH: feat/mcp-backend-sync2` + concurrency + owner 门控 + permissions）。边界——不动 test-check.yml（归 3.2）；不手工预置标签（脚本 ensure_labels 首跑自建）；不改 ZZZ 仓任何文件。
**设计依据**：design.md §2.1 前两行、§2.2-1、§2.3-1/2/5
**文件面**：tools/ci/build_test_branch.py、.github/workflows/build-test-branch.yml
**依赖**：无
**优先级建议**：8
**完成判据**：
- `uv run python -m py_compile tools/ci/build_test_branch.py` 通过；`uv run ruff check tools/ci/build_test_branch.py` 通过；
- 脚本与 ZZZ 源件逐段对照：除基线参数化（design §2.2-1 清单）外无语义差异（squash/冲突检测/署名/标签/Summary/push --force 全保留）；
- **基线收口（grep 双形态口径）**：`grep -n "origin/main" tools/ci/build_test_branch.py` 零命中（拦连写实参）；`grep -n '"main"'` 命中仅 1 处且为 `os.environ.get("BASE_BRANCH", "main")` 默认值行（拦 `"origin", "main"` 分离实参与文案裸字符串）；build-test-branch.yml 头注释无裸 main 基线表述（原 ZZZ 注释的 origin/main 措辞随基线改）；
- workflow 终态含：schedule `0 20 * * *` + workflow_dispatch(prs 输入) + concurrency（`group: ${{ github.workflow }}`、cancel-in-progress: false）+ owner 门控 + permissions 三写 + env INCLUDE_LABEL/CONFLICT_LABEL（照搬）与 BASE_BRANCH（SR 新增）+ ubuntu 步骤齐全；
- YAML 语法解析通过（python yaml.safe_load 或等价工具）；
- 休眠边界如实：不试图实跑验证 schedule/dispatch（默认分支前置未满足，design §2.3-1）；CI 实跑核对项写入 `.debug/temp/TODO.md`（前置满足后首跑，两步验收口径 = design §2.3-1）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：命令退出码 / grep 记录 / 文件对照记录

## 3.2 test-check 闭环接线

**范围**：test-check.yml 四处改动——①push 触发扩展（`branches: [main, feat/mcp-backend-sync2]`）+ concurrency（`group: test-check-${{ github.event.workflow_run.head_sha || github.ref }}`、cancel-in-progress: true）；②`on.workflow_run`（workflows: ["Build Test Branch"], types: [completed]）+ job if 新增 workflow_run 成功过滤；③主仓 checkout 显式 `ref: ${{ github.event.workflow_run.head_sha || github.ref }}`；④测试仓 checkout workflow_run 分支（ref 取 `env.BASE_BRANCH`，取不到 fallback main，沿用 continue-on-error + 后续 fallback 模式）+ env 块声明 BASE_BRANCH。边界——不动现有 pull_request 触发行为与测试执行步骤；不新增探针（已存在）。
**设计依据**：design.md §2.2-2/3、§2.3-1/3/4
**文件面**：.github/workflows/test-check.yml
**依赖**：3.1（workflow_run 引用 workflow 名）
**优先级建议**：7
**完成判据**：
- push 触发含 main 与活线两分支；concurrency 存在且 cancel-in-progress: true、group 表达式为 `test-check-${{ github.event.workflow_run.head_sha || github.ref }}`（design §2.2-3——不用裸 github.ref，防与 push main 同组互挤）；
- `on` 块含 workflow_run 且 workflows 名与 3.1 的 workflow `name:` 完全一致；job if 对 workflow_run 事件过滤 `conclusion == 'success'` 且对原有事件行为不变；
- 主仓 checkout 含 `ref: ${{ github.event.workflow_run.head_sha || github.ref }}` 表达式（design §2.2-3 平台事实依据）；
- 测试仓 checkout 三事件各自取 ref 正确：pull_request → `github.head_ref`（现状不变）；push → `main`（现状不变）；workflow_run → `env.BASE_BRANCH`，失败 fallback `main`；
- env 块含 `BASE_BRANCH: feat/mcp-backend-sync2`（与 3.1 workflow 同名同值）；
- YAML 语法解析通过；
- 完成前常规检查（本文首节；本阶段无 .py 改动，ruff 项不适用）。
**验收凭据形式**：YAML 对照 / 解析退出码

## 3.3 失败 issue 通知

**范围**：test-check.yml 失败出口升级与成功收尾——失败步骤以 `if: failure() &&`（workflow_run 条件）限定集成分支事件（design §2.2-2 对称口径），gh 创建或评论带 `test-branch-red` 标签的 issue（附运行链接与分支头 sha），标签首跑自建；成功收尾步骤以 `if: success() &&`（workflow_run 条件）显式声明，仅 workflow_run 触发时关闭该标签全部 open issue；permissions 新增 `issues: write`、步骤 env 提供 GH_TOKEN。边界——不动失败 notice 文案本体（保留日志层）；不接外部 webhook（design §2.4 取舍）。
**设计依据**：design.md §2.2-2、§2.3-1（唤醒两步验收）
**文件面**：.github/workflows/test-check.yml
**依赖**：3.2（挂在同一触发结构上）
**优先级建议**：7
**完成判据**：
- test-check.yml permissions 含 `issues: write`（现状仅 contents: read——缺它 gh issue create 403、红灯通知静默失效，design §2.3-5）；失败/成功步骤 env 含 `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}`；
- 失败步骤 `if` 含 `failure() &&` workflow_run 条件（对 push/pull_request 失败不开 issue，design §2.2-2）；含 gh 命令：查开 issue（`gh search issues --label test-branch-red --state open`）→ 存在则评论、不存在则创建（`gh issue create --label`），内容含运行链接；
- 成功收尾步骤 `if` 显式含 `success() &&` workflow_run 触发条件（不依赖隐式规则；对 push/pull_request 事件不执行）；含关闭该标签 open issue 的 gh 命令；
- 标签 `test-branch-red` 无需手工预置（步骤内 `gh label create --force` 或等价幂等自建）；
- YAML 语法解析通过；
- 完成前常规检查（本文首节；无 .py 改动，ruff 项不适用）。
**验收凭据形式**：YAML 对照 / 解析退出码

## 末阶段：正本更新

**范围**：按「正本更新清单」逐条更新正本。边界——不追改 `docs/**/changes/` 历史过程件。
**设计依据**：本文件「正本更新清单」节；AGENTS.md §13
**文件面**：AGENTS.md、docs/develop/setup/repositories.md
**依赖**：3.1、3.2、3.3
**优先级建议**：0
**完成判据**：清单清零；AGENTS.md §1.1 目录树 tools/ 行含 ci（改 AI 入口文件按 od-dev-writing-agent-instructions skill 处理）；repositories.md 含分支模型、CI workflow 清单、test 分支机制（标签语义、BASE_BRANCH 双处同步义务、休眠前置与唤醒两步验收清单）
**验收凭据形式**：文档对照 review

## 正本更新清单

- docs/develop/setup/repositories.md：新建（分支模型 / CI workflow 清单 / test 分支机制与唤醒验收） ← 3.1/3.2/3.3
- AGENTS.md §1.1 目录结构 tools/ 行（补「ci」） ← 3.1
