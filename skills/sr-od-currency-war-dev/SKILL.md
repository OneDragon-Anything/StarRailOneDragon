---
name: sr-od-currency-war-dev
description: 当在 StarRailOneDragon 仓库开发/维护/自主推进货币战争(Currency War,app_id `currency_war`)自动化时用——改策略代码、判读遥测与对局数据、跑实机局、修运行 bug、迭代算法、维护 CW 文档/ADR 都算,即使没明说。凡是碰 `src/sr_od/application/currency_war/`、`docs/*/currency_war/`、cw_sim 模拟、CW 遥测判读的工作都用本 skill。新玩法从零搭建走 od-dev-gameplay-automation,通用任务账本/钩子/画面建档走对应 od-dev-* skill,本 skill 只管已存在的货币战争。
---

# 货币战争开发·维护·自主推进

> 读者 = 无会话历史的干净智能体。本 skill 是 CW 的操作手册:知识在哪、按什么纪律改、用什么验证、实机怎么运维。**入口先分诊**(按当次任务定位主场与该走的门);**每个域自带自己的必做 checklist**(策略改动在 strategy-work、sim 改动在 sim-testing)——开发循环轮没做完所属域的 checklist 不算完成。正文只留每轮要锚定的判据;细则按节下沉 `references/`(按需读),决策依据在 `design/decisions/`。

## 入口分诊(按当次任务定位;「门」=该任务的硬判据)

| 当次任务 | 主节(门) | 细则 |
|---|---|---|
| 改策略 / 迭代算法 | strategy-work「策略改动 checklist」(判读→文档门→设计→验证阶梯→三同步) | strategy-work |
| 出策略方案 / 策略分歧裁决 / 疑问该问谁 | strategy-work「疑问/分歧的裁决」(三滤网) | strategy-work |
| 判读一局 / 跨局对照 | telemetry-reading「判读流程」(步骤0=先取尺子:当期目标行判据+strategy-work §2) | telemetry-reading |
| 起局 / 停局 / 监控 / 残局清理 | runtime-ops「启动与重启+局间交接序」 | runtime-ops |
| sim 批量 / A/B / 压测 / 改 sim 基建 | sim-testing「sim 改动 checklist」(池指纹/回放对拍/变异探针) | sim-testing |
| 阵容知识提炼 / 修订 / 版本重跑 | compo-knowledge(证据三层;先读再动) | compo-knowledge |
| 数据采集 / 版本重采 / 新字段建模 | §单一源地图·数据行(权威序;生成器分层) | data-collection |
| 自主推进(定时任务提醒 / worker 汇报与交付验收 / 哨兵报警响应 / 对抗) | 事件驱动模式 = od-dev-agent-autonomous-mode(公共 skill);CW 叠加细则 → autonomous-loop.md,各域交付按所属域 checklist 验收 | autonomous-loop |
| ADR / as-built 维护 | §文档同步(三同步) | — |
| 未命中任何行(任务不属上表) | 大概率非 CW 专属:按任务性质走对应公共 skill(写 op→od-dev-write-operation / 画面建档→od-dev-screen-onboarding / 排查运行失败→od-dev-debug-automation);确属 CW 但表中无行 → 先查下方单一源地图,仍定位不了 → 给分诊表补行 | — |

开发循环轮从所属域的 checklist 进(分诊表路由);分诊同时服务窄任务与新会话入口。会话开工的通用步(读进度账本/确认窗口/查钩子)与 commit 前的通用验证(ruff/全量测试)属项目级规范,在项目 AGENTS.md 类指令文件/公共 skill(od-dev-stop-hooks 等)承载,本 skill 不复述。

## 单一源地图(知识在哪,别造第二源)

| 要什么 | 去哪 |
|---|---|
| **策略工作统一说明**(思路/核心骨架/改前必做/验证与单帧锁/疑问三滤网) | [references/strategy-work.md](references/strategy-work.md);改策略前的必读文档面(全目录+阅读顺序)→ `docs/game/currency_war/research/README.md`「策略相关文档」节 |
| **模拟测试说明**(sim 能信什么/武器库/压测官/分诊与回灌) | [references/sim-testing.md](references/sim-testing.md) |
| **测试分层**(L1 快速集 `uv run pytest @sr-od-test/cw_quick.txt` ~3min/L2=L1+受影响域点名/L3 全量 `uv run pytest sr-od-test/` ~5min 仅 commit 前;禁跳到实机试错,实机运行期=做便宜层的窗口) | 各域 checklist 消费;策略验证阶梯单一源 = strategy-work §4 |
| **实机局数据判读**(判读流程/查询工具/观察面全量/已知缺口) | [references/telemetry-reading.md](references/telemetry-reading.md) |
| **实机运维细则**(单跑道 MCP 一次一 run;**改代码必须重启 server 才生效且重启杀对局 → 攒批局中不改**;重启/早停/残局清理/监控栈与哨兵) | [references/runtime-ops.md](references/runtime-ops.md) |
| **自主推进模式运转框架**(开启仪式/编排者-worker/审查分层/提醒网) | `od-dev-agent-autonomous-mode`(公共 skill);CW 叠加细则 = [references/autonomous-loop.md](references/autonomous-loop.md);进度结构见 od-dev-progress-tracking §2.5 |
| 人怎么玩(口述权威,改策略必读) | `docs/game/currency_war/research/user_playstyle.md` 全文 |
| 系统设计 as-built(为什么有 v2/架构/决策链/模块地图/边界)+ 设计 why | `docs/develop/currency_war/strategy/README.md`(分篇入口)+ `decisions/`(ADR;redesign.md 已砍除归档,ADR-0365) |
| 决策 why(一决策一文件) | `docs/develop/currency_war/decisions/`(INDEX + ADR-NNNN) |
| 单套 comp 打法知识 | `docs/game/currency_war/research/final_comps/`(唯一源) |
| 阵容知识怎么提炼/修订/版本重跑 | [references/compo-knowledge.md](references/compo-knowledge.md)(证据三层+三笔账) |
| 过渡阵容(引擎池/核心池/渐进路径) | `research/transition_combos.md` + `combo_methodology.md` + `transitions.md` |
| 游戏数据值(角色/羁绊/装备/概率) | 代码注册表 `cw_chars`/`cw_factions`/`cw_equipment`/`cw_shop_odds` 等——**值只在代码,data doc 只记「凭什么信」** |
| 数据怎么采集/版本更新重采/采集钩子盘点 | [references/data-collection.md](references/data-collection.md) |
| 外部攻略原文(版本冻结) | `docs/game/currency_war/sources/`(只带元数据头,原文不改) |
| 运行状态/焦点/待办 | `.debug/progress/` 根下的当前活跃迭代目录(未封存)入口 `进度.md`——多迭代三层结构(迭代目录→app→三池),规范=od-dev-progress-tracking §2.5。**卫生纪律**:只放活状态(焦点/待办/判读结论),轮次叙事/过期记录切归档文件留指针;单文件超 ~800 行即触发归档整理 |

分层判据:**游戏改了它变 → game 侧;代码改了它变 → develop 侧;进度/踩坑 → 本地进度账本,一律不进共享文档。**

## 文档同步(行为变更三同步)

策略行为/权重/算法语义/config·screen_info·GameState 字段/实跑根因任一变更 → commit 前:
1. 加 ADR(`docs/develop/currency_war/decisions/00NN-<slug>.md`,arc42 格式;INDEX 追加;**Considered Options 栏最值钱**);
2. strategy as-built 正文更新语义(值只进代码,文档写语义+指常量名);
3. 代码注释引 ADR-NN。

游戏知识变更(机制/阵容结论)进 `game/currency_war/research/` 对应篇(带证据分级),不进 develop;**攒 ADR = 漂移**(实跑演进当场记,攒了再补的成本远高于顺手写一条)。
