# 货币战争 · 玩法研究(经我们提炼/核实的知识)

> **本目录 = 我们提炼或核实过的玩法知识**(上游原 sources/ 外部攻略存档已于 2026-08-23 整体删除[eb9c72a1],版本过期致误引;有实质细节的条目已内联回填,补记块标「此为仅存记录」):社区帖统计提炼、机制核实、用户口述(直觉假设与机制证词,ADR-0482)、确认过的打法卡。写作纪律与分层判据见 [docs/game/README.md](../../README.md)「玩法知识分层」节。
> 版本基准:V4.4;版本更新时按证据链重核本目录,再同步代码注册表。

## 权威序(两层,ADR-0482;冲突时以高者为准)

**机制事实层**(游戏怎么运转,只能观测确立):`实机实测/图鉴` > `[口述]`(证词;未实测标「待实测」挂验证账)> `[米游社]` > `[社区]`(bwiki/NGA/攻略,单源或推算标 🟡,未找到标 🔴)

**策略命题层**(什么打法更优,可证明/可实证):`数学证明([math_proofs](../../../develop/sr_od/application/currency_war/proofs/math_proofs.md))+ sim/实机分布实证` > `[口述]`(直觉,假设来源——立命题待证,先例=P4 证伪)> `[米游社]` > `[社区]`

> 旧单层序(口述最高,2026-09-07 废)已由用户裁定废除;历史 `[口述·权威]` 标签=来源出处标记,解释权归本序。

## 玩家理解序(新读者从哪读起;依赖驱动)

> 顺序判据 = 玩法依赖:**机制是纪律的前提**(不懂息档/牌池/乘区,就读不懂纪律为什么这样定),**纪律是过渡的前提**(过渡篇大量按条目号引用 user_playstyle),**过渡与形态证据是终局的前提**。

1. **玩法机制**(游戏怎么运转;自足无前置):
   - [combat.md](combat.md) — 战斗侧:伤害三乘区 / 星级收益 / 扣血结构(为什么装备与星级重要)
   - [economy.md](economy.md) — 经济侧:牌池 / 刷新概率 / 商店槽位行为(买与刷的机制边界)
   - [xp-rules.md](xp-rules.md) — 节点基础经验:节点经验结算(+2/+0/BOSS+12 挂确认)/ 购买经验 4 金=+4XP / 升级门槛表(实机 145 局统计)
   - [board_structure.md](board_structure.md) — 板面格子结构:前台 4/后台 6 恒定,钻石/召唤物才扩后台;等级只定上场人数 cap(推翻旧 level 驱动布局模型)
   - [merge_mechanics.md](merge_mechanics.md) — 升星合成:买牌落点(备战→触发合成改落点)/场上吸收/备战最左/连锁合成(口述·权威;bot 期望态层与拖动对账的合成期望规格)
   - [equipment_mechanics.md](equipment_mechanics.md) — 装备机制与使用策略(证据三级标注,码源+口述):穿着即合成/前后台限定/商店自带装备/唯一件/工具 7 件全量+使用语义(策略决策件挂策略池)/冶金炉回收流水线(经济账框架,P14 生产化)
   - [invest_effects.md](invest_effects.md) — 335 投资策略 + 83 环境效果全量分类(哪类效果可建模)
    - [变宝为废-首次合成垃圾化.md](变宝为废-首次合成垃圾化.md) — 投资环境「变宝为废」机制(游戏明文:每位面首次进阶合成 50% 垃圾袋)与牺牲合成对策(策略命题[口述]待证;决策见 ADR-0498)
   - [screen_flow_timing.md](screen_flow_timing.md) — 对局流程的画面流转时序(生产日志实证)
2. **玩家纪律**(人怎么打;机制之上的打法约束,直觉假设来源——策略命题以 math_proofs 证明与实证为准,ADR-0482):
   - [user_playstyle.md](user_playstyle.md) ★ — 用户口述节奏全集:开局 / 经济息律 / 升级 / 阵容 / 装备纪律(条目现存至 [42],稳定 ID 永不复用;**直觉假设登记簿**——策略命题以 [math_proofs](../../../develop/sr_od/application/currency_war/proofs/math_proofs.md) 证明与 sim/实机分布实证为准,ADR-0482;条目引用须区分已证/待证)
3. **过渡体系与战力证据**(P1 怎么活到成型、什么形态能过;按口述条目号展开,故排在纪律后):
   - [transitions.md](transitions.md) — 过渡叙事:开局分级(锁线资格)/ 成型停手线 / 换血点 / 护航(已抛弃史料)
   - [transition_combos.md](transition_combos.md) ★ — 四种过渡体系逐线定义(引擎池 / 核心池;落码依据)
   - [stage_transitions.md](stage_transitions.md) — P1→P2→P3 阵容演化定量(加法不换件的数据边界)
   - [h3_tier_core_crosstab.md](h3_tier_core_crosstab.md) — 档位 × 核心在场 × 败率交叉(实机语料统计)
4. **终局阵容**(P2/P3 打什么):
   - [final_comps/](final_comps/README.md) ★ — 终局十类分类索引 + 单套 comp 打法单一源
5. **方法论与证明**(怎么读阵容 / 怎么论证策略;工具篇,可穿插读):
   - [combo_methodology.md](combo_methodology.md) — 阵容理解方法论(技能 / 羁绊 / 玩法三层)+ 攻略黑话查证纪律
   - [plaza_methodology.md](plaza_methodology.md) — 玩法方法论 M1-M16(资源入口 / 核心×弹性 / 升星经济学 / 装备优先级…)
   - [math_proofs.md](../../../develop/sr_od/application/currency_war/proofs/math_proofs.md) — 策略命题的数学期望证明集**索引**(命题状态表;单篇证明在 [proofs/](../../../develop/sr_od/application/currency_war/proofs/) 目录,一命题一篇含推导过程与数字表;计算脚本在 `tools/cw/proofs/`)

## 索引(什么问题查哪篇)

| 问题 | 文件 |
|---|---|
| 人怎么打(开局/经济/等级/阵容/装备的直觉假设全景及其证明状态) | [user_playstyle.md](user_playstyle.md) ★直觉假设登记簿(证明状态随 [math_proofs](../../../develop/sr_od/application/currency_war/proofs/math_proofs.md),ADR-0482) |
| 经济机制:牌池/退金/刷新概率/多刷/保血边界/阶段共识 | [economy.md](economy.md) |
| 节点经验:基础经验(+2/+0/BOSS+12 挂确认)/购买经验 4 金=+4XP/升级门槛表 | [xp-rules.md](xp-rules.md) |
| 节点类型:三位面默认序列地面真值 / 普通奖励节点=战斗型(有结算屏,档案定谳) | [plane_schedule_observed.md](plane_schedule_observed.md) |
| 升星合成:买牌落点/场上吸收/备战最左/连锁合成(买一张=可能升两级) | [merge_mechanics.md](merge_mechanics.md) |
| 战斗机制:伤害三乘区/星级收益/血量星/连胜经济/练度 | [combat.md](combat.md) |
| 过渡体系:P1 骨架/过渡成型停手线/换血点/P2 护航(已抛弃史料)/买牌纪律 | [transitions.md](transitions.md) |
| **过渡阵容逐线定义**(引擎池/核心池/直通族结构;落码依据) | [transition_combos.md](transition_combos.md) ★ |
| **终局阵容分类**(final comps 分类索引+逐类累积;CARRY/羁绊双维;**单套 comp 打法知识单一源**) | [final_comps/README.md](final_comps/README.md) ★ |
| 阵容理解方法论(技能/羁绊/玩法三层怎么读) | [combo_methodology.md](combo_methodology.md) |
| 玩法方法论 M1-M16:资源入口/核心×弹性/枢纽分级/骨架拼装/升星经济学/装备优先级/站位… | [plaza_methodology.md](plaza_methodology.md) |
| 策略命题证明(某结论为什么成立/口述直觉的数学保证) | [math_proofs.md](../../../develop/sr_od/application/currency_war/proofs/math_proofs.md) 索引 → [proofs/](../../../develop/sr_od/application/currency_war/proofs/) 单篇 |
| 单套 comp 打法(入场/退场信号/counter/装备叙事) | [final_comps/](final_comps/README.md) 各类文档(2026-08-22 起单一源;原 comps/ 打法卡层已撤销合并) |
| 投资卡效果全量分类与可建模边界(API 裁定) | [invest_effects.md](invest_effects.md) |

## 策略相关文档(改策略前的必读面;单一源在本节)

**策略工作的基线 = research/ 全部文档 + data/ 全部未建模数据文档**(research 按上方「玩家理解序」读:机制是纪律的前提,纪律是过渡的前提,过渡是终局的前提)——策略判断横跨经济/战斗/阵容/终局,漏任何一面都判错;不读全就无法预判改动波及面。

- research/ **唯一排除**:screen_flow_timing(画面流转时序,运行时/运维侧,非策略面)。
- data/(`docs/game/currency_war/data/`,**全部策略相关**):gameplay(官方玩法说明)/ competitors(词缀机制+20 竞争阵营唯一源)/ bosses(boss 克制启示)/ advantage_layouts(跨局 meta 增益)/ plaza_meta(实战 meta)。已建模入代码注册表的数据已删 doc,查值直接看注册表(清单见 data/README)。
- proofs/ 单篇按命题按需读(math_proofs 是命题状态表)。

消费方(sr-od-currency-war-dev skill、判读/验证工作流)引用「改策略前读什么」时指本节,别在别处另列清单。

## 关系图

- **值(数据)的单一源 = 代码注册表**(`src/sr_od/application/currency_war/cw_*.py`);本目录记「凭什么信」。
- **设计消费**:`docs/develop/sr_od/application/currency_war/strategy-docs/` 的 as-built 正文引用本目录结论(只引结论一句话+链接,不复制内容)。
- **上游**:原 ../sources/ 外部原文存档(已删[eb9c72a1],git 历史 `eb9c72a1~1` 可查);仍被引用的条目以各篇「原文细节补记」块为仅存记录,本目录结论的证据等级就地标注。
- **裁定/教训不进本目录**:玩法取舍 → ADR(`docs/develop/sr_od/application/currency_war/decisions/`);分析教训 → 本地 insights。
