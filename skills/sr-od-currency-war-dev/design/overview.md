# sr-od-currency-war-dev · 设计总览

## 定位

货币战争(Currency War)自动化的**开发·维护·自主推进操作手册**,项目内 dev skill(跟仓库走,不独立发布)。回答三件事:知识在哪(单一源地图)、按什么纪律改(设计先行+三份文档前置)、用什么验证与运维(反馈梯度+实机运维)。

## 边界

- **不管**:新玩法从零搭建(od-dev-gameplay-automation)、通用任务账本方法(od-dev-progress-tracking)、停机钩子生命周期(od-dev-stop-hooks)、画面建档(od-dev-screen-onboarding)、写单个 op(od-dev-write-operation)——CW 场景下按 SKILL.md 入口序路由到它们,本 skill 不复述其内容。
- **不管**:游戏机制知识本身(在哪查由单一源地图指路)、策略的具体行为语义(strategy/01-07 是源)。
- 面向**已存在的 CW app**;若 CW 被推倒重写,本 skill 随之修订。

## 构成

- `SKILL.md`:导读 + 入口分诊表(任务→门,路由到各域 references 主线)+ 单一源地图(全部指针的集中地)+ 文档同步三同步(见 ADR-0024;细则按节下沉 references)。
- `references/sim-testing.md`:模拟测试专属说明(边界+找问题三步主线(统计→筛坏指标→挑局复盘);A/B 归 strategy-work「验证」;批组织在 autonomous-loop的分诊与固化;见 ADR-0023)。
- `references/telemetry-reading.md`:实机局数据判读方法论(判读流程与先取尺子门、查询工具、观察面全量清单、视图覆盖矩阵、采集缺口;见 ADR-0023)。
- `references/runtime-ops.md`:实机运维细则(启动与重启、早停判据、局间交接序、残局画面清单、监控栈与哨兵脚本组)。
- `references/data-collection.md`:数据采集全景(生成器族、图鉴实采、运行时钩子、建模增量层、钩子统一使用与产物路径)。
- `references/compo-knowledge.md`:阵容知识工程(证据三层、三笔账、提炼/修订/版本重跑流程)。
- `references/strategy-work.md`:策略工作统一说明(策略是什么与骨架、改前、开关落地、验证、单帧锁)。
- `references/autonomous-loop.md`:CW 编排资产(定时任务提醒网角色与提示词模板/实机监控自执行模板/策略审查/哨兵报警消费;定时任务消费与编排者-worker 等通用机制单一源=od-dev-agent-autonomous-mode,设计见 ADR-0022)。
- `design/`:本文件 + 决策存档。

## 与其它约定层的分工

- 全局/项目 AGENTS:always-on 通用纪律(工作流级);本 skill 只管 CW 特定操作,通用部分不复述。
- `docs/`:知识与设计本体;本 skill 是「怎么消费/维护它们」的操作规程。
- `.debug/progress/` 当前活跃迭代目录的入口 `进度.md`:运行状态;本 skill 的操作对象(读写),不是知识源(多迭代三层结构,规范=od-dev-progress-tracking §2.5)。
