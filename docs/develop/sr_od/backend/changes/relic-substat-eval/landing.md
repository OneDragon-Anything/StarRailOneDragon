# relic-substat-eval 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过；
- 本阶段直接受影响测试全量一次通过(`uv run pytest sr-od-test/ -m "not slow"` 相关子集)；
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交；
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号与任务 id;提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 纯计算模块与 fixture 测试
**范围**：新建 `src/sr_od/backend/mcp/relic_eval_tools.py`——`evaluate(roster_data, criteria)` 纯函数 + 归一表/口径包表常量；同批交付 fixture 测试。拉一次真实名册核对词条 name_cn 全集，据其定稿归一表（口径包表按 design §2.4 定稿判据核对，不挂名册）。边界——不含 MCP 注册、不含知识库文件改动。
**设计依据**：design.md §2.2（接口与字段）、§2.3（计算规则 1-10）、§2.4（常量表）、§2.5（模块路径与取舍）
**文件面**：`src/sr_od/backend/mcp/relic_eval_tools.py`、`sr-od-test/test/sr_od/backend/mcp/test_relic_eval_tools.py`（含 fixture 数据）
**依赖**：前置数据条件 = mys 会话有效（过期则先 `mys_login`，验证页人工环节可能需要用户在场）；无其他代码依赖
**优先级建议**：5
**完成判据**：
- evaluate 按 design §2.3 全部 10 条规则输出（归一/warnings 机制/数值解析/遍历域/命中/主词条核对含头手排除/阈值求和口径/最弱件/verdict 模板含空数据分支/跳过缺名/结构防御）；
- 归一表经真实名册词条名全集核对定稿；fixture 数据 = 自造样例 + 真实名册字段形态（注释只标数据来源，核对过程不入注释）；
- 每条 fixture 场景锁定其设计约定的字段表现（对照 design §2.2/§2.3），不做无场景语义的逐字段遍历断言；
- 完成前常规检查（本文首节）。
**验收凭据形式**：测试名与断言场景清单 + 真实名册词条名全集对照记录（fixture 注释标来源）

## 3.2 MCP 工具注册
**范围**：`mys_tools.py` 注册 `mys_evaluate_relic_substats`（描述文本与 Returns 段逐字取 design §2.2；入参 schema 按字段表——`roster_data: list[object]`；`roster_data` 缺省时走 controller 自拉并透传非 success 信封）。边界——不重启 server（3.4 做）。
**设计依据**：design.md §2.2（工具描述/入参/出参/信封状态语义）、§2.5（适配层）
**文件面**：`src/sr_od/backend/mcp/mys_tools.py`
**依赖**：3.1
**优先级建议**：5
**完成判据**：
- 工具注册成功：名称/描述（含 Returns 段）/入参字段与类型对照 design §2.2 逐项一致（`roster_data` 数组类型为 A1 修复重点）；
- 四态信封语义按 §2.2 Returns 段可达：success / session_expired、verification_required（自拉透传）/ error（criteria 空、重名、roster_data 结构非法、拉取业务失败）；
- `roster_data` 缺省路径与传入路径都可达（代码审查）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：注册代码 diff 对照 design §2.2 文本

## 3.3 角色档口径行补齐
**范围**：为 design §2.5 验收名单的 12 个角色，在 `skills/sr-od-game-coach/references/characters/<角色>.md` 的「副词条」节各补一行机器可读口径「有效口径: <口径包名或枚举>」（依据各档现有「副词条」措辞改写，不改写原措辞行）。边界——只动这 12 个文件、只加这一行；其余角色的铺开归 game-coach 维护流程，不在本迭代。
**设计依据**：design.md §2.5（验收名单与跨层依赖）、§2.4（口径包表——写行时用到的包名必须已在该表）
**文件面**：`skills/sr-od-game-coach/references/characters/{卡芙卡,海瑟音,黑天鹅,丹恒•腾荒,黄泉,千冶•刃,缇宝,灵砂,Archer,远坂凛,花火,阮•梅}.md`
**依赖**：3.1（口径包表定稿后才知道可用包名）
**优先级建议**：5
**完成判据**：
- 12 个角色档各含一行「有效口径」，其词项都能被归一表展开（用 3.1 的表自查）；
- 完成前常规检查（本文首节）。
**验收凭据形式**：12 文件 diff（逐文件一行新增）

## 3.4 server 重启与实机冒烟
**范围**：经 sr_od_daemon 重启主 MCP server；用 design §2.5 验收名单 12 人的真实口径跑一轮实机评估；抽检 2 个角色的数字与人工按明细手数对照。边界——不做词条诊断结论（那是使用方的事）。
**设计依据**：design.md §2.1（数据流）、§2.3（规则）、§2.5（验收名单）
**文件面**：无代码面（操作 + 抽检记录留 `.debug/temp/`）
**依赖**：3.1、3.2、3.3
**优先级建议**：6
**完成判据**：
- server 重启后工具可调（首调 Session not found 重试即愈属预期）；
- design §2.5 名单中实有角色全部评估成功；缺员/形态分歧落入 `not_found` 属预期，在留档记录中说明（参照 investment.md 知更鸟缺员先例）；
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
- `docs/develop/sr_od/backend/mys.md`：工具清单/协议节补 `mys_evaluate_relic_substats`（含四态信封语义）← 3.2/3.4
- `docs/develop/sr_od/backend/mcp.md`：工具表加行（签名/返回语义/tool 总数）← 3.2
- `docs/develop/sr_od/backend/mcp-implementation.md`：§1 分类表纯观察工具名单加行 ← 3.2
- `skills/sr-od-game-coach/references/investment.md`：「有效词条计数工具的设计决定」节更新为已实现（工具名/入参/出处指向 mys.md），并登记速记归一表（口径包名清单）的出处 ← 3.4
