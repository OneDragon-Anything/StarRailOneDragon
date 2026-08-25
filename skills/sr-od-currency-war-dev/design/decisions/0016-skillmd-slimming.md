# ADR-0016:SKILL.md 瘦身(细则下沉 references,正文只留判据层)

- **Status**: accepted
- **日期**: 2026-08-25

## Context

SKILL.md 涨到 38.6KB/166 行(超长行堆积),每次触发 skill 全量注入智能体上下文,约 1.5-2 万 token——用户直接要求优化。诊断三类病灶:

1. **细则滞留正文**:sim A/B 验收纪律(10 条)、压测官角色、模拟灵活使用与双批挖掘、哨兵脚本组与武装口径、首局锚点模板、goal/schedule 元纪律(15 条)、数据治理五步等 ~20KB 低频细则全在 SKILL.md;而 references/ 已有对口文件(verification/runtime-ops/telemetry-reading)却没接住——progressive disclosure(正文 compact、细节 just-in-time)名存实亡。
2. **双源重复**:「哨兵重武三步」SKILL.md 与 runtime-ops.md 各写一遍;「复盘全面」与 telemetry-reading 核心原则重叠;「文档同步不欠账」在元纪律与文档同步节出现两次。
3. **叙事压指令**(ADR-0015 的同型残余):「(2026-08-XX 用户定调)」日期标记与「(实证见 design/decisions/)」泛指针在正文出现 20+ 次——ADR-0015 决策 1 引入的「实证见 design/decisions/」句式被逐条复制后自身成了噪声;日期数字对干净读者无信息量(有效信号是「用户定调」这个权威等级词)。

外部约束(不可破坏):docs/ 三处引用本 skill 的「判读」节名、telemetry-reading、verification.md;AGENTS.local 引用「实机运维」节——**全部节名保留**,只移内容。

## Considered Options

1. **只删不迁**——否决:细则本身是多次事故反推的有效判据,删除=丢知识;且 ADR-0015 已证明「抽象化」不解决体量(判据仍在正文)。
2. **拆成多个独立 skill**——否决:CW 手册的单一入口定位(ADR-0002 工作流轴)依赖一个 skill 承载全部场景路由;拆分后触发路由复杂化、跨 skill 指针爆炸。
3. **progressive disclosure 落实(选定)**:SKILL.md 只留「每轮开发循环要锚定的判据」(checklist/单一源地图/三问/梯度/核心运维判据/一行式元纪律),细则整段下沉 references/(既有四文件 + 新建 autonomous-loop.md);正文对应位置留一行式指针。

## Decision

1. **分层判据**:内容「每轮循环都要对照」→ SKILL.md;「特定场景才需要」(判读数据侧/sim 验收/监控武装/自主推进编排细节)→ references/。防坑清单例外:高频陷阱判据留在正文(每条已是判据行,论据已抽象)。
2. **迁移分配**:
   - `references/autonomous-loop.md`(**新建**):goal 轮纪律/schedule 提醒纪律/**schedule 提醒网七角色表与派单模板硬规范**(自实机运维节归位迁入)/指挥官-worker 分工/对抗审查两形态/数学期望标尺/哨兵报警消费协议(原元纪律 15 条中 5 条整条迁入,其余 10 条压缩为正文一行式);
   - `references/telemetry-reading.md`:数据源注释>采样凑证、数据治理五步、阵容三维、反例论据(原判读节);
   - `references/verification.md`:sim 已知边界(详版)、sim A/B 与多批并行验收纪律(10 条)、压测测试官、模拟灵活使用与双批挖掘(原验证工作台节);
   - `references/runtime-ops.md`:实机通道(mcp_call.ps1)、哨兵脚本组表+武装命令口径+试用期纪律、重启接管段遥测降权、布局交互实锤、首局锚点模板、常置 flag 处置(原实机运维节)。
3. **双源清理**:迁入时与 references 既有内容合并去重(重武三步只留 runtime-ops 一处;「复盘全面」并入 telemetry-reading 核心原则节);正文对应处只留一行指针,不再复述。
4. **叙事标记收敛**(对 ADR-0015 决策 1/3 的细化修正):「(实证见 design/decisions/)」泛指针从逐条标注改为节级一次(导读句);具体 ADR 编号(ADR-0010/0219/0233/0239 等)继续逐条保留——可校验、grep 得到;「(2026-08-XX 用户定调)」保留「(用户定调 …)」权威等级、删日期数字(时序锚归 ADR/进度树);当期态值(如池指纹锚)不进正文。
5. **新增内容的准入门槛**(防再膨胀):往 SKILL.md 加内容前先问「这是每轮循环都要锚定的判据,还是特定场景细则?」——后者进 references;references 同主题既有节优先合并,不开平行节。**对偶面(防减过头,2026-08-25 用户追问补)**:从正文/references 减内容前过「消费频率 × 断链代价」两问——高频执行判据(每轮收账都过的清单类)**留在当场**(skill 间引用不自动加载,断链=漏步,比 token 贵);低频结构性内容(一次性建置时消费)才指针化。与公共 skill 重复≠该减:按 ADR-0003 模式「关键判据自包含重述(名字+一行),完整定义归公共」已是稳态,重述层低漂移,不算病态双源。

## Consequences

- SKILL.md 38.6KB → 18.9KB(判据层,2026-08-25 W117 审查实测 18865 字节;初稿「约 13KB」为预估数,实测偏高——判据层保留下限由对偶面两问守住,进一步压缩交给后续按准入门槛演化),触发注入成本降约一半;细则按需读取(just-in-time),总知识量不减。
- 正文与 references 形成「判据行 → 展开细则」两级结构;漂移风险从「双源重复」变为「指针失联」——防线上,每次改 references 节名需同步正文指针(节名进正文且外部文档在引用的那几个:判读/验证工作台/实机运维等,改名成本高,天然稳定)。
- 元纪律 15 条 → 正文路由行 + autonomous-loop.md 全量:自主推进会话须多读一个文件才能拿到编排细节(可接受:元纪律消费场景集中在 goal/schedule 轮,正是 just-in-time 时机;与 ADR-0011「入 skill」决策不冲突——references 在 skill 内,路由行是消费锚)。
- ADR-0015 的「实证见 design/decisions/」句式不再逐条使用;该 ADR 的批号抽象化判据本身仍有效。

## 迁移对照(后续维护者用)

| 原 SKILL.md 位置 | 去向 |
|---|---|
| 判读节:数据源注释/数据治理/阵容三维/反例论据/复盘全面 | telemetry-reading.md「判读纪律」扩充 + 新节「数据侧纪律」「反例论据」 |
| 验证工作台:sim 已知边界详版 | verification.md「sim 已知边界」节 |
| 验证工作台:sim A/B 验收纪律/压测官/灵活使用/双批挖掘 | verification.md 同名三节 |
| 实机运维:mcp_call.ps1/哨兵表/武装口径/试用期/遥测降权/布局实锤/首局锚点/常置 flag | runtime-ops.md「实机通道」新节 + 「监控栈」扩充 + 新节「判读与建档的运维侧纪律」(**2026-08-25 后续:mcp_call 实机通道节已删**——前提过期:项目级 `.dsh/mcp.servers.yml` 已原生挂载 sr_od/sr_od_daemon,该节自述的「演进路径:挂进 DSH MCP 配置获得原生工具」已发生,脚本通道成前朝遗物且无活消费点,脚本与 session 文件一并删除;过期内容删除是维护动作,不另立 ADR) |
| goal/schedule 自我校准 15 条 | 初版瘦身留「正文 10 条一行式」;复检(用户指出同 schedule 表一样的准入问题)后二次收缩——7 条 autonomous-loop.md 已覆盖,「做事按 skill 来/素材泵」2 条补迁入,「保持架构」并入 checklist 步骤 4 判据,正文只留路由行(goal/schedule 消息到达 → 读 autonomous-loop.md;goal 轮第一动作回指 checklist)。与 ADR-0011 的关系:0011 反对的是校准点放 skill 之外(AGENTS.local/schedule 注入,goal 轮智能体读不到);收缩到 skill 目录内 references + 正文路由行保留消费锚,「入 skill + 离工作现场近」的决策意图不变 |
| 实机运维节「schedule 体系」子节(七角色表/间隔/派单模板硬规范) | autonomous-loop.md「schedule 提醒网」节——**归属修正**:七角色中仅「值守兜底」涉实机,其余六角色全是自主推进编排关切,初版瘦身保位在实机运维下是结构瑕疵;归位后正文 goal/schedule 节与 AGENTS.local 两处指针同步(同批完成) |
| 交付验收「L1/L3 命令见上节」(原为悬空引用,命令实际在下节) | 顺手修正为「见 §验证工作台」 |
