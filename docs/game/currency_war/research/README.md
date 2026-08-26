# 货币战争 · 玩法研究(经我们提炼/核实的知识)

> **本目录 = 我们提炼或核实过的玩法知识**(上游原 sources/ 外部攻略存档已于 2026-08-23 整体删除[eb9c72a1],版本过期致误引;有实质细节的条目已内联回填,补记块标「此为仅存记录」):社区帖统计提炼、机制核实、**用户口述(最高权威)**、确认过的打法卡。写作纪律与分层判据见 [docs/game/README.md](../../README.md)「玩法知识分层」节。
> 版本基准:V4.4;版本更新时按证据链重核本目录,再同步代码注册表。

## 权威序(冲突时以高者为准)

`[口述]` 用户 A8 实战口述 > `[图鉴]` 游戏内图鉴 / 实机实测 > `[米游社]` > `[社区]` bwiki/NGA/攻略(单源或推算标 🟡,未找到标 🔴)

## 玩家理解序(新读者从哪读起;依赖驱动)

> 顺序判据 = 玩法依赖:**机制是纪律的前提**(不懂息档/牌池/乘区,就读不懂纪律为什么这样定),**纪律是过渡的前提**(过渡篇大量按条目号引用 user_playstyle),**过渡与形态证据是终局的前提**。

1. **玩法机制**(游戏怎么运转;自足无前置):
   - [combat.md](combat.md) — 战斗侧:伤害三乘区 / 星级收益 / 扣血结构(为什么装备与星级重要)
   - [economy.md](economy.md) — 经济侧:牌池 / 刷新概率 / 商店槽位行为(买与刷的机制边界)
   - [board_structure.md](board_structure.md) — 板面格子结构:前台 4/后台 6 恒定,钻石/召唤物才扩后台;等级只定上场人数 cap(推翻旧 level 驱动布局模型)
   - [equipment_mechanics.md](equipment_mechanics.md) — 装备机制与使用策略:穿着即合成/前后台限定/冶金炉(单件刷+拖角色=刷+拆)/扳手/无用装备回收流水线/期望课题(口述权威)
   - [invest_effects.md](invest_effects.md) — 335 投资策略 + 83 环境效果全量分类(哪类效果可建模)
   - [screen_flow_timing.md](screen_flow_timing.md) — 对局流程的画面流转时序(生产日志实证)
2. **玩家纪律**(人怎么打;机制之上的打法约束,口述最高权威):
   - [user_playstyle.md](user_playstyle.md) ★ — 用户口述节奏全集:开局 / 经济息律 / 升级 / 阵容 / 装备纪律(条目 [1]-[33],策略校准第一入口)
3. **过渡体系与战力证据**(P1 怎么活到成型、什么形态能过;按口述条目号展开,故排在纪律后):
   - [transitions.md](transitions.md) — 过渡叙事:开局分级(锁线资格)/ 成型停手线 / 换血点 / 护航(已抛弃史料)
   - [transition_combos.md](transition_combos.md) ★ — 四种过渡体系逐线定义(引擎池 / 核心池;落码依据)
   - [power_baseline.md](power_baseline.md) ★ — 形态 × 位面能否过的证据表(bot 敢用白名单)
   - [stage_transitions.md](stage_transitions.md) — P1→P2→P3 阵容演化定量(加法不换件的数据边界)
   - [h3_tier_core_crosstab.md](h3_tier_core_crosstab.md) — 档位 × 核心在场 × 败率交叉(实机语料统计)
4. **终局阵容**(P2/P3 打什么):
   - [final_comps/](final_comps/README.md) ★ — 终局十类分类索引 + 单套 comp 打法单一源
5. **方法论与证明**(怎么读阵容 / 怎么论证策略;工具篇,可穿插读):
   - [combo_methodology.md](combo_methodology.md) — 阵容理解方法论(技能 / 羁绊 / 玩法三层)+ 攻略黑话查证纪律
   - [plaza_methodology.md](plaza_methodology.md) — 玩法方法论 M1-M16(资源入口 / 核心×弹性 / 升星经济学 / 装备优先级…)
   - [math_proofs.md](math_proofs.md) — 策略命题的数学期望证明集**索引**(命题状态表;单篇证明在 [proofs/](proofs/) 目录,一命题一篇含推导过程与数字表;计算脚本在 `tools/cw/proofs/`)

## 索引(什么问题查哪篇)

| 问题 | 文件 |
|---|---|
| 人怎么打(开局/经济/等级/阵容/装备的基准节奏) | [user_playstyle.md](user_playstyle.md) ★策略校准第一入口 |
| 经济机制:牌池/退金/刷新概率/多刷/保血边界/阶段共识 | [economy.md](economy.md) |
| 战斗机制:伤害三乘区/星级收益/血量星/连胜经济/练度 | [combat.md](combat.md) |
| 过渡体系:P1 骨架/过渡成型停手线/换血点/P2 护航(已抛弃史料)/买牌纪律 | [transitions.md](transitions.md) |
| **过渡阵容逐线定义**(引擎池/核心池/直通族结构;落码依据) | [transition_combos.md](transition_combos.md) ★ |
| **终局阵容分类**(final comps 分类索引+逐类累积;CARRY/羁绊双维;**单套 comp 打法知识单一源**) | [final_comps/README.md](final_comps/README.md) ★ |
| **阵容战力基线**(形态×位面能否过的证据表;bot 敢用白名单) | [power_baseline.md](power_baseline.md) ★ |
| 阵容理解方法论(技能/羁绊/玩法三层怎么读) | [combo_methodology.md](combo_methodology.md) |
| 玩法方法论 M1-M16:资源入口/核心×弹性/枢纽分级/骨架拼装/升星经济学/装备优先级/站位… | [plaza_methodology.md](plaza_methodology.md) |
| 策略命题证明(某结论为什么成立/口述直觉的数学保证) | [math_proofs.md](math_proofs.md) 索引 → [proofs/](proofs/) 单篇 |
| 单套 comp 打法(入场/退场信号/counter/装备叙事) | [final_comps/](final_comps/README.md) 各类文档(2026-08-22 起单一源;原 comps/ 打法卡层已撤销合并) |
| 投资卡效果全量分类与可建模边界(API 裁定) | [invest_effects.md](invest_effects.md) |

## 策略相关文档(改策略前的必读面;单一源在本节)

**策略工作的基线 = research/ 全部文档 + data/ 全部未建模数据文档**(research 按上方「玩家理解序」读:机制是纪律的前提,纪律是过渡的前提,过渡是终局的前提)——策略判断横跨经济/战斗/阵容/终局,漏任何一面都判错;不读全就无法预判改动波及面。

- research/ **唯一排除**:screen_flow_timing(画面流转时序,运行时/运维侧,非策略面)。
- data/(`docs/game/currency_war/data/`,**全部策略相关**):gameplay(官方玩法说明)/ competitors(词缀机制+20 竞争阵营唯一源)/ bosses(boss 克制启示)/ advantage_layouts(跨局 meta 增益)/ plaza_meta(实战 meta)。已建模入代码注册表的数据已删 doc,查值直接看注册表(清单见 data/README)。
- research/ **核心三篇**(★):user_playstyle(口述权威,全文精读)/ transition_combos(过渡配方落码依据)/ power_baseline(形态白名单)。
- proofs/ 单篇按命题按需读(math_proofs 是命题状态表)。
- 日常增量的按任务补读组合见下方「任务路由」表(路由表是**增量跟踪**用,不是基线的替代)。

消费方(sr-od-currency-war-dev skill、判读/验证工作流)引用「改策略前读什么」时指本节,别在别处另列清单。

## 任务路由(做什么任务,先读什么组合)

> 防单篇自闭:不同任务的关键知识散在不同的篇——只读一篇≈读局部。判读类另有前置三问(sr-od-currency-war-dev skill 判读节),本表是其文档来源。

| 任务 | 先读组合 |
|---|---|
| 判读一局(局后复盘) | user_playstyle [28][18][27] + power_baseline(形态白名单) + transitions §1(锁线资格) |
| 改买入/意向/锁定逻辑 | user_playstyle 全文 + transition_combos(配方定义) + transitions(开局分级) + economy(息律) |
| 改评分/经济类权重 | user_playstyle + economy |
| 掉血归因/战斗机制理解 | user_playstyle [27] + combat |
| 改换阵/部署/装备分配 | user_playstyle [21][24][29] + combo_methodology + **board_structure(格子结构,布局选档前提)** |
| 终局阵容设计 | final_comps/ + plaza_methodology |
| 阶段转型(P1→P2→P3) | transitions §换血点 + user_playstyle [26] + plaza_methodology(阶段阵容) |

> 条目号(如 [28])指 user_playstyle.md 的口述条目编号——最高权威来源,判读判据优先锚定它。

## 关键互链(读 A 篇时该跳去的 B 篇)

- user_playstyle [20](过渡是配方)→ 配方逐线定义在 transition_combos;资格判据(什么条件配走哪条线)在 transitions §1
- user_playstyle [28](50 金通关 P1)→ 达标形态见 power_baseline P1 榜
- user_playstyle [31](羁绊降级梯队)→ 凑数位定性(哪些羁绊是经济挂件零输出)在 transition_combos
- transitions §1 开局分级 → 直通线资格枚举=锁线判据权威源(代码消费点 cw_intention,ADR-0338)
- power_baseline 位面骨架 → P1→P3 形态演进的用户口径在 user_playstyle [26]

## 关系图

- **值(数据)的单一源 = 代码注册表**(`src/sr_od/application/currency_war/cw_*.py`);本目录记「凭什么信」。
- **设计消费**:`docs/develop/currency_war/strategy/` 的 as-built 正文引用本目录结论(只引结论一句话+链接,不复制内容)。
- **上游**:原 ../sources/ 外部原文存档(已删[eb9c72a1],git 历史 `eb9c72a1~1` 可查);仍被引用的条目以各篇「原文细节补记」块为仅存记录,本目录结论的证据等级就地标注。
- **裁定/教训不进本目录**:玩法取舍 → ADR(`docs/develop/currency_war/decisions/`);分析教训 → 本地 insights。
