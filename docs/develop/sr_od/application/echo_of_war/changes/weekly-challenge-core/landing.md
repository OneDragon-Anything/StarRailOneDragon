# 周本挑战核心与行迹刷取接入 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）
- `uv run ruff check` 对本阶段改动文件全部通过（含测试文件）；
- 本阶段直接受影响测试全量一次通过（按阶段点名目录：echo_of_war / challenge_mission 相关子集），例：`$env:PYTHONPATH="src"; uv run pytest sr-od-test/test/sr_od/application/echo_of_war -q -p no:cacheprovider`；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 说清改了什么；提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。
- 范围红线（用户裁定）：本迭代不接入周本 app（ChallengeEchoOfWar）与开拓力 app（UseTrailblazePower）——它们的失败适配/迁移归各自外溢迭代占位目录，落地时发现触碰需求即停手上报，禁自行扩面。

### 3.1 周本挑战循环核心 op + 共享失败继续件
**范围**：新建 `ChallengeEchoOfWarCore`（echo_of_war 包，节点图/docstring 两段式/取值校验/timeout 声明）+ 新建共享失败继续件 `ResumeFromBattleFail`（challenge_mission 包）；sr-od-test mock 场景表全量（weekly-core.md 十三场景，含 ⑫ 三分支直呼式单测）。边界：不动 ChallengeEchoOfWar、不接行迹、不动 use_trailblaze_power。
**设计依据**：details/weekly-core.md 全节；details/fail-form-adaptation.md「方案：共享失败继续件」节
**文件面**：`src/sr_od/application/echo_of_war/challenge_echo_of_war_core.py`（新建）、`src/sr_od/challenge_mission/resume_from_battle_fail.py`（新建）、`sr-od-test/test/sr_od/application/echo_of_war/` 与 `sr-od-test/test/sr_od/challenge_mission/`（新建测试）
**依赖**：无
**优先级建议**：0
**完成判据**：
- mock 场景全过，status 落点与 weekly-core.md status 表逐一对照（含 ⑫ 直呼三场景：超时胜利未达计划报「超时胜利已退出」非假成功、判负转 ⑪ 链、二次超时转「战斗超时无结算」）；
- 构造签名与 MCP 契约一致（ctx 逐字/纯 JSON 参数/无回调）；support 'none' 归一防线生效（场景 13）；
- <完成前常规检查（本文首节）>
**验收凭据形式**：pytest 场景名清单 + 节点流转断言

### 3.2 周本按名挑战包装 op（行迹侧接入）
**范围**：新建 `ChallengeEchoOfWarByName`（mission 解析 + support 'none'→None 翻译 + 周本计划配队解析（0=沿用当前编队并日志显性化）+ 回大世界→传送→核心→统一收尾，成功终态 status 恒「已返回大世界」、fail 原样透传；次数耗尽分支清 left_times）；mock 场景：中文名解析、ID 解析、多命中 ValueError、零命中 ValueError（带可选值清单）、计划配队解析（team_num=3 传核心 / team_num=0 跳过切队且日志报口径）、'none' 翻译、全链委托（核心八类 status 全名单逐一分支断言，全名单见 weekly-core.md status 出口表）。
**设计依据**：details/trace-integration.md「周本按名挑战包装」节；details/weekly-core.md status 出口表（全名单）
**文件面**：`src/sr_od/application/echo_of_war/`（新包装文件）、`sr-od-test/test/sr_od/application/echo_of_war/`
**依赖**：3.1
**优先级建议**：6
**完成判据**：
- mock 场景过：八类 status 全名单逐一分支断言 + 未知 status 透传 fail + 解析两异常面 + 配队解析与翻译；
- docstring 两段式 + MCP 契约（ctx/纯 JSON 参数）+ op_name 照 app 先例；
- <完成前常规检查（本文首节）>
**验收凭据形式**：pytest 场景名清单

### 3.3 MCP 验收三连 + 实机验证（行迹侧）
**范围**：重启项目 MCP server 后 `list_operations` 找得到新 op → `describe_operation` 核对 schema 与 docstring → 实机 `run_operation`。
**设计依据**：weekly-core.md status 表、trace-integration.md 包装节点链
**文件面**：无代码改动（验证批）
**依赖**：3.1、3.2
**优先级建议**：8
**完成判据**：
- `describe_operation` 核对两 op：参数 schema 与设计一致；核心各节点 `timeout_seconds`（⑨/⑫-a=25 分钟、⑩/⑫-b/共享件=3 分钟、共享件兜底口径）与 `node_max_retry_times`（节点级 5/10）声明值逐一核对；
- 实机零消耗链：**从行迹面板态起跑**（观察项：BackToNormalWorldPlus 从面板态回家的未实测段）→ 传送 → 次数耗尽弹窗取消 → 终态「已返回大世界」且日志带「本周次数耗尽」流转，开拓力零扣（自然恢复除外），left_times 已清零，全程日志可复盘；
- 实机全胜链（`已完成计划次数` 路径）：等周本次数恢复后随行迹手动刷实测，通过即销此项（届时若跨迭代由负责人裁定顺延）；
- <完成前常规检查（本文首节）>
**验收凭据形式**：run_operation 日志（status 流转 + 开拓力读数对照）

### 末阶段：正本更新
**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：清单所列正本文档
**依赖**：全部落地阶段
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单
- `docs/develop/sr_od/application/echo_of_war/` 正本区（新建挑战机制概览：核心/包装/app 三 op 职责与起点终点）← 3.1、3.2
- `skills/sr-od-game-coach/references/basics/新手与日常决策.md`「已建成的养成 op」节（增补 ChallengeEchoOfWarByName 用法与授权口径，含计划配队=0 的风险显性化）与行迹缺料推荐链口径 ← 3.2
