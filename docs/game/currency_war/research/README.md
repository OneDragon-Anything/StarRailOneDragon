# 货币战争 · 玩法研究(经我们提炼/核实的知识)

> **本目录 = 我们提炼或核实过的玩法知识**(区别于 [../sources/](../sources/) 的外部原文存档):社区帖统计提炼、机制核实、**用户口述(最高权威)**、确认过的打法卡。写作纪律与分层判据见 [docs/game/README.md](../../README.md)「玩法知识分层」节。
> 版本基准:V4.4;版本更新时按证据链重核本目录,再同步代码注册表。

## 权威序(冲突时以高者为准)

`[口述]` 用户 A8 实战口述 > `[图鉴]` 游戏内图鉴 / 实机实测 > `[米游社]` > `[社区]` bwiki/NGA/攻略(单源或推算标 🟡,未找到标 🔴)

## 索引(什么问题查哪篇)

| 问题 | 文件 |
|---|---|
| 人怎么打(开局/经济/等级/阵容/装备的基准节奏) | [user_playstyle.md](user_playstyle.md) ★策略校准第一入口 |
| 经济机制:牌池/退金/刷新概率/多刷/保血边界/阶段共识 | [economy.md](economy.md) |
| 战斗机制:伤害三乘区/星级收益/血量星/连胜经济/练度 | [combat.md](combat.md) |
| 过渡体系:P1 骨架/过渡成型停手线/换血点/P2 护航/买牌纪律 | [transitions.md](transitions.md) |
| **过渡阵容逐线定义**(引擎池/核心池/直通族结构;落码依据) | [transition_combos.md](transition_combos.md) ★ |
| **终局阵容分类**(final comps 分类索引+逐类累积;CARRY/羁绊双维;**单套 comp 打法知识单一源**) | [final_comps/README.md](final_comps/README.md) ★ |
| **阵容战力基线**(形态×位面能否过的证据表;bot 敢用白名单) | [power_baseline.md](power_baseline.md) ★ |
| 阵容理解方法论(技能/羁绊/玩法三层怎么读) | [combo_methodology.md](combo_methodology.md) |
| 玩法方法论 M1-M16:资源入口/核心×弹性/枢纽分级/骨架拼装/升星经济学/装备优先级/站位… | [plaza_methodology.md](plaza_methodology.md) |
| 单套 comp 打法(入场/退场信号/counter/装备叙事) | [final_comps/](final_comps/README.md) 各类文档(2026-08-22 起单一源;原 comps/ 打法卡层已撤销合并) |
| 投资卡效果全量分类与可建模边界(API 裁定) | [invest_effects.md](invest_effects.md) |

## 关系图

- **值(数据)的单一源 = 代码注册表**(`src/sr_od/application/currency_war/cw_*.py`);本目录记「凭什么信」。
- **设计消费**:`docs/develop/currency_war/strategy/` 的 as-built 正文引用本目录结论(只引结论一句话+链接,不复制内容)。
- **上游**:[../sources/](../sources/) 外部原文存档(版本冻结);本目录的每条结论指回源。
- **裁定/教训不进本目录**:玩法取舍 → ADR(`docs/develop/currency_war/decisions/`);分析教训 → 本地 insights。
