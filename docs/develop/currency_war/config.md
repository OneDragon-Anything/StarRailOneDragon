# 货币战争 用户配置设计(配置语义单一源)

> 本文回答「配置面该有什么、不该有什么」。决策依据(用户画像定调 + 单一职责原则)见
> [ADR-0203](decisions/0203-config-user-preference-single-duty.md);字段实现 = `currency_war_config.py`
> (行为与当前值在代码,本文只记语义与归属)。

## 1. 目标用户画像(用户定调,ADR-0203)

1. **日常玩家(大多数)**:用 bot 完成日常游戏周期,不较真能否通关最高难度。
2. **成就/奖励刷取**:想拿特定成就奖励(如「8 减益」「300 宝石」类成就),需要 bot 按指定玩法打。

**推论**:配置面的职责是让用户表达「**我想怎么玩**」,不是「教 bot 怎么玩最优」。策略质量(阵容
选择/经济节奏/搜牌时机)是 bot 自己的事,用户不该被迫理解引擎内部才能用起来。日常玩家开箱即用
(全默认),成就玩家用转向轴/预设/专用策略表达意图。

## 2. 归属判据(一条红线)

一条数据/参数只问一个问题:「**用户会因个人目的想改它吗?**」

| 类别 | 判据 | 归属 | 例子 |
|---|---|---|---|
| 用户偏好 | 用户因个人目的想改 | **配置**(本文范围) | 角色/策略/环境的禁用与优先 |
| 游戏客观数据 | 整个游戏版本一致,谁玩都一样 | 注册表/数据 doc | 「净化身心克 DoT」(MECHANIC_COUNTERS)、刷新概率表 |
| 策略校准参数 | 改它=调引擎,用户无对错的个人意见 | 代码常量 | 保血阈值、难度阶梯、利息权重 |
| 开发/实验工具 | 只有开发/验证用 | yml-only 调试字段(不进 GUI) | strategy_seed、max_rounds |

违反即双源或错位(反面案例:原 `dot_punish_envs` 把游戏客观数据放进了配置,与注册表双源且
注释把词缀标成「投资环境」,ADR-0203 删)。

## 3. 目标配置面

### 3.1 用户面(按画像收敛;四类实体 × 三档)

| 实体 | 禁用(hard−) | 优先(soft+) | 必含(hard+) |
|---|---|---|---|
| 角色 | `character_forbid` | `character_priority` | `character_build_around`(any:含任一) |
| 阵营 | `faction_forbid` | `faction_priority` | `faction_build_around`(**all:全部在场**) |
| 投资策略 | `strategy_forbid` | `strategy_priority` | —(选卡分数已足) |
| 投资环境 | `env_forbid` | `env_priority` | —(开局 3 选 1) |
| 运行 | — | — | `strategy_id`(见 §4) |

> 原 `event_whitelist`(恒最高 boost)已删(ADR-0204):「指定具体分值」是引擎调参非用户偏好,
> priority/forbid 已覆盖用户语义(想要/不要);打分环里的「恒最高」第三态无真实画像需求。

- 三轴语义:**必含(hard+)> 优先(soft+)> 默认(评估分)> 禁止(hard−)**。
- **阵营轴保留**(成就需要特定阵容,如 8减益 → `faction_build_around=['减益']`);
  `faction_build_around` 用 **all() 语义**(多个必含 = 全部在场,多羁绊成就要求),与角色轴 any() 刻意不同。
- **必含轴保留**:成就局常需「一定用某阵容」,「优先」表达不了「一定」。
- 消费端落点:comp 侧 `_passes_steering` 硬过滤 + `_priority_boost` 软加分
  (select_comp);选卡侧 `decide_event` 打分环加 priority `STEERING_PRIORITY_BONUS` /
  forbid `STEERING_FORBID_PENALTY`(常量在 cw_events;策略走策略轴、
  env 注册表命中走环境轴;子串匹配 OCR 容错;全被禁 → 分数落刷新阈值下自然建议刷新兜底)。
- 预设(§3.2)打包这些轴,不自建平行评分。

### 3.2 预设(画像 2 的一键入口,后续做)

成就预设 = 转向轴打包(如「8 减益」= 减益流派必含 + 相干策略优先),非特殊代码路径 —— bot 按
偏好打、成就自然达成。

## 4. 运行控制与实验:只留 strategy_id(定稿;ADR-0204)

配置面的运行控制收敛结论(用户裁定):**用户面只留 `strategy_id`**——「选哪个脑」是真实用户选择:默认策略够日常;**画像 2 的成就玩法未来=选专用策略插件**(如「8 减益成就策略」),这是比逐字段转向更高一层的入口,策略插件体系(11 号)对用户的唯一暴露点。

| 字段 | 定位 | 语义 |
|---|---|---|
| `strategy_id` | **用户面** | 选策略插件(`default` = 不配置即内置打法;现行生产 v2 = `decision_v2`;旧 `line_v2` 已删,ADR-0336) |
| `strategy_seed` | 开发/实验(yml-only,不进 GUI) | A/B 复现调试;只种子化策略内部随机(游戏侧种子化不到,对用户是虚承诺,07 §4) |
| `max_rounds` | 开发/实验(同上) | 多轮采样验证;一次 app 运行本就是一整局 |

> 已出清字段(`economy_mode`/`event_whitelist` 删、`hp_safe_threshold`/`difficulty_hp_override` 迁代码常量 `cw_state.HP_SAFE_THRESHOLD`/`DIFFICULTY_HP_TABLE`、gate_* 4 个 yml-only flag 删)的**why 与过程 → [ADR-0204](decisions/0204-config-prune-batch2.md) / [ADR-0216](decisions/0216-gate-old-path-removal.md)**;阵营轴保留与必含轴确认的用户裁定 → ADR-0203。

## 5. 待用户定的事项

无待定项;后续配置演进(GUI setting card / 预设)按 §3 目标态实施。历史裁定(阵营轴保留/必含轴/§4 出清)已收进 ADR-0203/0204,变更过程不再在此记流水。
