# relic-substat-eval 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过(`uv run pytest sr-od-test/ -m "not slow"` 相关子集)；
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交；
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号与任务 id;提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 纯计算模块与常量定稿
**范围**：新建 `src/sr_od/backend/mys/relic_substat_eval.py`——`evaluate(roster_data, criteria)` 纯函数 + 别名表 + 口径包表两张常量；拉一次真实名册核对词条 name_cn 全集并据此定稿两张常量表。边界——不含 MCP 注册、不含 controller 改动、不含知识库文件改动。
**设计依据**：design.md §2.2（接口与字段）、§2.3（计算规则）、§2.4（常量表初稿）、§2.5（代码结构）
**文件面**：`src/sr_od/backend/mys/relic_substat_eval.py`
**依赖**：无
**优先级建议**：5
**完成判据**：
- evaluate 按 design §2.3 全部 8 条规则输出（别名归一/口径包展开/命中计数/主词条核对/阈值对照/最弱件/verdict 模板/跳过与缺名）；
- 两张常量表经真实名册词条名全集核对后定稿（核对记录随提交留档于测试 fixture 注释）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：测试名（3.2 的 fixture 测试）+ 真实名册词条名清单对照记录

## 3.2 fixture 测试
**范围**：sr-od-test 新增纯函数测试；边界——不含 MCP 层测试（工具注册属胶水，行为由 3.4 冒烟覆盖）。
**设计依据**：design.md §2.2（出参 schema）、§2.3（计算规则）
**文件面**：`sr-od-test/test/sr_od/backend/mys/test_relic_substat_eval.py`（含 fixture 数据）
**依赖**：3.1
**优先级建议**：5
**完成判据**：
- fixture 场景覆盖：别名归一命中、口径包展开、穿错主词条、阈值达标与差线、浪费分布与最弱件、verdict 模板串、criteria 角色名不存在 → not_found、criteria 空表 → results 空；
- 断言计数与输出结构对照 design §2.2 表逐字段；
- 完成前常规检查（本文首节）。
**验收凭据形式**：测试名与断言数（pytest 输出对照 design §2.2 字段清单）

## 3.3 MCP 工具注册
**范围**：`mys_tools.py` 注册 `mys_evaluate_relic_substats`（描述文本逐字取 design §2.2；入参 schema 按字段表；roster_data 缺省时走 controller 自拉 `mys_get_roster_detail`）；边界——不重启 server（3.4 做）。
**设计依据**：design.md §2.2（工具描述/入参/出参）、§2.5（适配层）
**文件面**：`src/sr_od/backend/mcp/mys_tools.py`
**依赖**：3.1
**优先级建议**：5
**完成判据**：
- 工具按 design §2.2 注册成功（名称/描述/入参字段一致）；
- `roster_data` 缺省路径与传入路径都可达（代码审查）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：注册代码 diff 对照 design §2.2 文本

## 3.4 server 重启与实机冒烟
**范围**：经 sr_od_daemon 重启主 MCP server；用星启候选队 12 人的真实口径跑一轮实机评估；抽检 2 个角色的数字与人工手数对照。边界——不做词条诊断结论（那是使用方的事）。
**设计依据**：design.md §2.1（数据流）、§2.3（规则）
**文件面**：无代码面（操作 + 抽检记录留 `.debug/temp/`）
**依赖**：3.2、3.3
**优先级建议**：6
**完成判据**：
- server 重启后工具可调（首调 Session not found 重试即愈属预期）；
- 实机 12 人评估输出完整（results 12 条 + not_found 空）；
- 抽检 2 角色的命中数与人工按明细手数一致；
- 完成前常规检查（本文首节，仅涉提交时适用）。
**验收凭据形式**：实机输出 JSON 留档 + 抽检数字对照表

## 末阶段：正本更新
**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：3.1~3.4 全部。
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致。
**验收凭据形式**：文档对照 review。

## 正本更新清单
- `docs/develop/sr_od/backend/mys.md`：工具清单/协议节补 `mys_evaluate_relic_substats` ← 3.3/3.4
- `docs/develop/sr_od/backend/mcp.md` / `mcp-implementation.md`：若含工具清单/描述汇总则同步 ← 3.3（实现时确认是否涉及）
- `skills/sr-od-game-coach/references/investment.md`：「有效词条计数工具的设计决定」节更新为已实现（工具名/入参/出处指向 mys.md）← 3.4
- 角色档 12 人的「有效口径」行（候选队使用面）：本迭代 3.4 冒烟即需 → 由 3.4 顺带补齐并注明其余角色归 game-coach 维护流程铺开
