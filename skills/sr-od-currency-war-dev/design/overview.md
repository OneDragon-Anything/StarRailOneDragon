# sr-od-currency-war-dev · 设计总览

## 定位

货币战争(Currency War)自动化的**开发·维护·自主推进操作手册**,项目内 dev skill(跟仓库走,不独立发布)。回答三件事:知识在哪(单一源地图)、按什么纪律改(设计先行+三份文档前置)、用什么验证与运维(反馈梯度+实机运维)。

## 边界

- **不管**:新玩法从零搭建(od-dev-gameplay-automation)、通用任务树方法(od-dev-progress-tracking)、停机钩子生命周期(od-dev-stop-hooks)、画面建档(od-dev-screen-onboarding)、写单个 op(od-dev-write-operation)——CW 场景下按 SKILL.md 入口序路由到它们,本 skill 不复述其内容。
- **不管**:游戏机制知识本身(在哪查由单一源地图指路)、策略的具体行为语义(strategy/01-07 是源)。
- 面向**已存在的 CW app**;若 CW 被推倒重写,本 skill 随之修订。

## 构成

- `SKILL.md`:入口分诊表(任务→主节/门)+ 必做 checklist(8 步开发循环)+ 单一源地图 + 判读/验证/运维/文档同步/防坑的**判据层**(每轮要锚定的核心;细则按节下沉 references,见 ADR-0016/0017)。
- `references/verification.md`:验证工作台细则(sim A/B 与多批验收纪律、压测官、灵活使用与双批挖掘、诚实性分层、分诊与回灌、变异探针、单帧锁模板、实机判读)。
- `references/telemetry-reading.md`:遥测判读方法论(观察面全量清单、视图覆盖矩阵、采集缺口、数据侧纪律)。
- `references/runtime-ops.md`:实机运维细则(交接序、残局画面清单、监控栈与哨兵脚本组、判读与建档的运维侧纪律、运行坑)。
- `references/data-collection.md`:数据采集全景(生成器族、图鉴实采、运行时钩子、建模增量层、钩子统一使用与产物路径)。
- `references/compo-knowledge.md`:阵容知识工程(证据三层、三笔账、提炼/修订/版本重跑流程)。
- `references/strategy-work.md`:策略工作统一说明(思路/核心骨架/改前必做/策略特有验证纪律/疑问三滤网)。
- `references/autonomous-loop.md`:CW 编排资产(schedule 提醒网四角色与提示词模板/派单规范指针/哨兵报警消费;goal/schedule 消费与编排者-worker 等通用机制单一源=od-dev-agent-autonomous-mode,见 ADR-0018/0020/0021)。
- `design/`:本文件 + 决策存档。

## 与其它约定层的分工

- 全局/项目 AGENTS:always-on 通用纪律(工作流级);本 skill 只管 CW 特定操作,通用部分不复述(但**自包含重述**改策略纪律的关键判据——见 ADR-0003)。
- `docs/`:知识与设计本体;本 skill 是「怎么消费/维护它们」的操作规程。
- `.debug/progress/` 当前活跃迭代目录的入口 `进度.md`:运行状态;本 skill 的操作对象(读写),不是知识源(多迭代三层结构,规范=od-dev-progress-tracking §2.5)。
