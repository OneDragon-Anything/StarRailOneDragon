# 仓库结构：分支与 CI

本仓的分支模型、GitHub Actions 工作流清单、集成分支（test）机制的单一事实源。测试仓（sr-od-test）的独立维护见 AGENTS.md §1。

## 1. 分支模型

| 分支 | 角色 |
|---|---|
| main | 默认分支。GitHub 平台规则：**定时（schedule）、手动（workflow_dispatch）、工作流联动（workflow_run）三类触发只运行默认分支上的文件**——带这三类触发的 workflow 改动，进入默认分支后才生效 |
| 活开发线 | 日常集成与直推分支（名称随时代更换，现阶段为 `feat/mcp-backend-sync2`）；test-check 对它开了 push 触发，直推即跑全量测试 |
| test | 集成验证分支，由 Build Test Branch workflow 每日自动重建（强制推送），**禁止手工提交** |

## 2. CI 工作流清单

| workflow | 触发 | 职责 |
|---|---|---|
| test-check | PR / push（main 与活线）/ workflow_run 联动 | 全量测试；import 探针；集成分支红灯 issue（§3） |
| build-release | tag 推送 / 手动 | 构建安装器、启动器与环境依赖包并发布 |
| build-test-branch | 每日定时 / 手动（prs 列表） | 重建 test 集成分支（§3） |
| locale-po | push / 手动 | 多语言编译（ubuntu + pip 直装，无 uv——其 PYTHONPATH 前缀是导入功能依赖，保留） |
| auto-close-issue | 每日定时 | 自动关闭带「无法复现」标签的沉寂 issue |

## 3. 集成分支（test）机制

**一次完整过程**：每日定时（北京时间凌晨，平台延迟可达数小时）或手动触发 Build Test Branch → 从 `BASE_BRANCH` 指定的基线分支重建 test 分支 → 带 `test-branch` 标签的 open PR 按 PR 号升序逐个 squash 合入 → 与基线或先前 PR 冲突的跳过并打 `test-conflict` 标签（Step Summary 出冲突文件/行号/相关 PR 报告）→ 推送成功后联动 test-check 在 test 分支头跑全量测试 → 测试失败开/评论带 `test-branch-red` 标签的 issue，转绿自动关闭（自管理指示灯；push/PR 事件的测试失败不进 issue——有关联人）。

**PR 标签语义**：

| 标签 | 含义 | 谁打 |
|---|---|---|
| test-branch | 该 PR 参与集成分支验证 | 维护者 |
| test-conflict | 该 PR 与基线或先前 PR 冲突被跳过，需 rebase | workflow 自动 |
| test-branch-red | 集成分支测试失败（issue 标签，转绿自动关） | workflow 自动 |

**BASE_BRANCH 双处同步义务**：集成分支基线在两个 workflow 里各有一份 env（build-test-branch.yml 与 test-check.yml 的 `BASE_BRANCH`，GitHub 的 env 不跨 workflow 共享）——活线换代时**两处必须同步改**，漏改一侧会按 main 口径静默运行（无平台告警）。

**唤醒验收两步走**（定时/联动触发休眠后恢复、或新接手验证时）：

1. 首跑只验「机制跑通」：test 分支被重建、test-check 被联动触发、红灯 issue 路径可达——这三件成立即机制正常，**与测试红绿无关**；
2. 基线修红单独走：test-check 长期未运行后首跑大概率红，把红修完之前，集成分支不当作合入防线使用。

**边界**：workflow_run 联动时测试仓（sr-od-test）取 `BASE_BRANCH` 同名分支（缺失回退 main）——open PR 各自新增的测试不在集成验证内；PR 基点与基线分支错位过远（未 rebase 的存量 PR）会被冲突墙跳过，防线的实际作用始于 PR 群对齐之后。
