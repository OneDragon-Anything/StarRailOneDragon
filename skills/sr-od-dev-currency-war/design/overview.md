# sr-od-dev-currency-war · 设计总览

## 定位

货币战争(Currency War)自动化的**开发·维护·自主推进操作手册**,项目内 dev skill(跟仓库走,不独立发布)。回答三件事:代码架构与铁律是什么(SKILL.md §1)、任务从分诊表哪一行进入(§2 入口分诊)、知识在哪与行为变更怎么同步文档(§3 单一源地图+§4)。

## 边界

- **不管**:新玩法从零搭建(od-dev-write-application)、迭代流程与迭代内进度(od-dev-run-iteration)、停机钩子生命周期(od-dev-stop-hooks)、画面建档(od-dev-screen-onboarding)、写单个 op(od-dev-write-operation)——CW 场景下按 SKILL.md 入口序路由到它们,本 skill 不复述其内容。
- **不管**:游戏机制知识本身(在哪查由单一源地图指路)、策略的具体行为语义(strategy/01-07 是源)。
- 面向**已存在的 CW app**;若 CW 被推倒重写,本 skill 随之修订。

## 构成

- `SKILL.md`:导读 + 入口分诊表(任务→对应域,路由到各域 references 主线)+ 单一源地图(全部指针的集中地)+ 文档同步(细则按节下沉 references)。
- `references/sim-testing.md`:模拟测试专属说明(边界+找问题三步主线(统计→筛坏指标→挑局复盘);A/B 归 strategy-work「验证」)。
- `references/telemetry-reading.md`:实机局数据判读方法论(判读流程与先定标准步骤、查询工具、观察面全量清单、视图覆盖矩阵、采集缺口)。
- `references/runtime-ops.md`:实机运维细则(启动与重启、早停判据、局间交接序、残局画面清单、监控栈与哨兵脚本组)。
- `references/data-collection.md`:数据采集全景(生成器族、图鉴实采、运行时钩子、建模增量层、钩子统一使用与产物路径)。
- `references/version-update.md`:版本更新 CW 域适配方法(场景判型扩充/换赛季重做、按域依赖顺序的 checklist 与验收判据、换赛季特有面、已知坑;总流程挂 sr-od-dev-version-update-adaptation 路由表)。
- `references/compo-knowledge.md`:阵容知识工程(证据三层、三笔账、提炼/修订/版本重跑流程)。
- `references/strategy-work.md`:策略工作统一说明(策略是什么与方法主线、改前、开关落地、验证、单帧测试)。
- `references/autonomous-loop.md`:CW 实机探索期编排细则+领域叠加件(实机探索 agent 协议/窗口所有权串行/问题处置循环/传话纪律/核心面清单与共享资产枚举的 CW 映射;策略迭代期最小定义=时期切换种子;通用框架单一源=od-dev-agent-autonomous-mode 的需求线流水线)。
- `design/`:本文件;ADR(why)仅经用户命令创建(默认无)。

## 与其它约定层的分工

- 全局/项目 AGENTS:always-on 通用纪律(工作流级);本 skill 只管 CW 特定操作,通用部分不复述。
- `docs/`:知识与设计本体;本 skill 是「怎么消费/维护它们」的操作规程。
- `.debug/progress/` 根下的存量迭代目录:历史运行状态,只读封存;新迭代的进度住 `.temp/changes/` 迭代目录(tasks.md,规范见 od-dev-run-iteration)。

## 动机记录

- **§1.4 参数规范(用户裁定)**:动作原语最初按 kernel 会话语义设计参数(名称定位/槽位缺省走 game state 现算),暴露三类缺口——名称在重复实体下定位歧义(实拍:装备栏同名多条)、个别分支 game state 缺席即断言崩溃、参数 dataclass 缺 `from_dict` 导致 MCP JSON 通道构造不出(实机局 agent 无法调用穿装 op)。裁定:执行路径零 game state 依赖、参数三分法(固定槽位/半固定/动态坐标)、名称降级语义参数、坐标新鲜度归调用方、迁移按 op 切四角色子代理流水线(设计→review→实施→review)。刻意不采纳:op 落点前校验(违反动作 op 纯机械契约,新鲜度归调用方纪律)、按名称定位(重复实体歧义不可解)。
- **自主推进形态重写为实机探索期(用户裁定)**:旧形态(定时任务提醒+实机监控角色+哨兵报警消费接入+模拟常开+局终自动派复盘)服务 server 自动跑局时代,随阶段切换整体废弃;新形态 = 编排者派实机探索 agent 按游玩 skill 亲自玩、遇问题停止操作并汇报,走诊断→设计→对抗评审(每轮全新子 agent)→实现→终审→实机验证循环,编排者全程只调度与传话不做技术判断。刻意不采纳:在旧文档上保留定时任务模板待将来恢复使用(用户裁定需要时重写,不留尾巴)。
