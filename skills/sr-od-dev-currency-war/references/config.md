# 用户配置(config)

> 组件 = `currency_war_config.py`(字段实现与当前值在代码,本篇只记语义与归属)。本篇回答「配置面该有什么、不该有什么」:先给目标用户与归属判据,再给字段语义总表。新增/修改配置字段:先按 §2 判据裁决归属,再对 §3/§4 表落字段。

## 1. 目标用户画像

1. **日常玩家(大多数)**:用 bot 完成日常游戏周期,不较真能否通关最高难度。
2. **成就/奖励刷取**:想拿特定成就奖励(如「8 减益」「300 宝石」类成就),需要 bot 按指定玩法打。

推论:配置面的职责是让用户表达「**我想怎么玩**」,不是「教 bot 怎么玩最优」。策略质量(阵容选择/经济节奏/搜牌时机)是 bot 自己的事,用户不该被迫理解引擎内部才能用起来。日常玩家开箱即用(全默认),成就玩家用转向轴/预设/专用策略表达意图。

## 2. 归属判据(一条红线)

一条数据/参数只问一个问题:「**用户会因个人目的想改它吗?**」

| 类别 | 判据 | 归属 | 例子 |
|---|---|---|---|
| 用户偏好 | 用户因个人目的想改 | **配置**(本篇范围) | 角色/策略/环境的禁用与优先 |
| 游戏客观数据 | 整个游戏版本一致,谁玩都一样 | 注册表/数据 doc | 「净化身心克 DoT」(`pick_common.AFFIX_COUNTERS_FACTIONS`)、刷新概率表 |
| 策略校准参数 | 改它 = 调引擎,用户无对错的个人意见 | 代码常量 | 保血阈值、难度阶梯、利息权重 |
| 开发/实验工具 | 只有开发/验证用 | yml-only 调试字段(不进 GUI) | strategy_seed、max_rounds |

违反即双源或错位。

## 3. 用户转向轴(四类实体 × 三档)

| 实体 | 禁用(hard−) | 优先(soft+) | 必含(hard+) |
|---|---|---|---|
| 角色 | `character_forbid` | `character_priority` | `character_build_around`(any:含任一) |
| 阵营 | `faction_forbid` | `faction_priority` | `faction_build_around`(**all:全部在场**) |
| 投资策略 | `strategy_forbid` | `strategy_priority` | —(投资策略屏的选项评分已覆盖,无需必含档) |
| 投资环境 | `env_forbid` | `env_priority` | —(开局 3 选 1,无需必含档) |
| 运行 | — | — | `strategy_id`(见 §4) |

- 三轴语义:**必含(hard+)> 优先(soft+)> 默认(评估分)> 禁止(hard−)**。
- **阵营轴保留**(成就需要特定阵容,如 8 减益 → `faction_build_around=['减益']`);`faction_build_around` 用 **all() 语义**(多个必含 = 全部在场,多羁绊成就要求),与角色轴 any() 刻意不同。
- **必含轴保留**:成就局常需「一定用某阵容」,「优先」表达不了「一定」。
- 现状:`character_build_around` 消费端 = 策略层选靶(`strategies/impl/flow.py`);`faction_build_around` 当前无消费端(阵容锁定现行机制 = 候选-锁定制 `session_scope.write_line_lock`),字段保留接预设。
- 预设(画像 2 的一键入口):成就预设 = 转向轴打包(如「8 减益」= 减益流派必含 + 相干策略优先),非特殊代码路径——bot 按偏好打、成就自然达成。

## 4. 运行控制与实验字段

| 字段 | 定位 | 语义 |
|---|---|---|
| `strategy_id` | **用户面** | 选策略插件;**当前唯一合法值 = `mandate_v1`**(不配置即此值;策略器注册与换核契约见 [flow/strategy-contract.md](flow/strategy-contract.md);存量 yml 写其他值,配置加载即报错并提示改值) |
| `ev_arm` | 开发/实验(yml-only,不进 GUI) | 投资环境动作发出面的实验分支位(合法值 skeleton_only=发出面旁路 / full=全开),仅 mandate_v1 消费 |
| `strategy_seed` | 开发/实验(同上) | A/B 复现调试;只种子化策略内部随机,游戏侧随机量不在其适用范围内(docs/develop/sr_od/application/currency_war/sim/sim-design.md §7),对用户是虚承诺 |
| `max_rounds` | 开发/实验(同上) | 多轮采样验证;一次 app 运行本就是一整局 |
| `code_hash_gate` | 开发/运维(yml-only,不进 GUI) | 起局前置码哈希结构闸开关:起局前比对 server 已加载码面(进程当前加载的代码文件内容)vs git HEAD,不一致拒起;缺省开 = 安全闸宁拦勿放。**server 进程 PATH 无 git = 起局被拒**(fail-closed——信息缺失/校验失败时宁可拒绝,不带错值运行),git 是起局硬依赖 |
