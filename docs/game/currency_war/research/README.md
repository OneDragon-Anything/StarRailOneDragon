# 货币战争 · 玩法研究(经我们提炼/核实的知识)

> **本目录 = 我们提炼或核实过的玩法知识**(上游原 sources/ 外部攻略存档已于 2026-08-23 整体删除[eb9c72a1],版本过期致误引;有实质细节的条目已内联回填,补记块标「此为仅存记录」):社区帖统计提炼、机制核实、用户口述(直觉假设与机制证词)、确认过的打法卡。写作纪律与分层判据见 [docs/game/README.md](../../README.md)「玩法知识分层」节。
> 版本基准:V4.4;版本更新时按证据链重核本目录,再同步代码注册表。

## 证据优先级排序(权威序;两层;冲突时以高者为准)

**机制事实层**(游戏怎么运转,只能观测确立):`实机实测/图鉴` > `[口述]`(证词;未实测标「待实测」并登记待验证待办)> `[米游社]` > `[社区]`(bwiki/NGA/攻略,单源或推算标 🟡,未找到标 🔴)

**策略命题层**(什么打法更优,可证明/可实证):`数学证明([math_proofs](../../../develop/sr_od/application/currency_war/proofs/math_proofs.md))+ sim/实机分布实证` > `[口述]`(直觉,假设来源——立命题待证,先例=math_proofs 第 4 号命题证伪)> `[米游社]` > `[社区]`

> 旧单层序(口述最高,2026-09-07 废)已由用户裁定废除;历史 `[口述·权威]` 标签=来源出处标记,解释权归本序。

## 术语表(本目录通用词的白话定义)

> 各篇正文沿用下列统一叫法;旧黑话在原文首次出现处以括注给出对照。代码标识符(变量/常量/文件路径)与游戏内官方名词不受影响。

| 术语 | 白话定义 |
|---|---|
| 压牌库 | 通过买入(通常是可全额退回的低星牌)减少剩余牌库、提高后续刷新刷出目标牌的概率——全局供给策略,不是本位战力投资 |
| 过渡桥阵容 | 位面 1→2 承上启下的中间过渡阵容:保底稳血、攒经济,随后一步换到终局阵容 |
| 成型停买线 | 阵容成型到标准(羁绊/星级/人口达标)即停止买入该类件的判据线 |
| 开局直奔终局阵容 | 开局即锁定并直奔某终局阵容的打法(信号驱动,不经通用过渡体系);社区语境的「直通线/直通族」 |
| 全程留用角色 | 从位面 1 一路留用到终局的角色(如千冶·刃/三月七/花火/星期日) |
| 多线通用角色 | 能进入多条终局路线的通用角色(枢纽型,如瓦尔特/符玄) |
| 凑羁绊填充角色 | 为凑出羁绊档位而临时填充的角色(旧称「挂件」),成型后可替换卖出 |
| 临时凑数角色 | 空窗期/未成型期用现有牌临时凑数、散件垫底的填充位(旧称「垫层/凑数位」) |
| 星徽穿戴者 | 星徽(转职徽章)挂在谁身上的角色;星徽给穿戴者授予/加计一个羁绊 |
| 旧采集时期 | 动作日志 journal 上线之前的数据采集时期(缺动作行,统计口径受限) |
| 刷新商店(抽牌) | 花金币刷新商店找牌的动作;社区也叫 D 牌(猛 D/大 D=大量刷新) |
| 单一源 / 正本 | 该信息只在一处正式维护、他处只引用不复制(单一源);被引用为权威版本的正文(正本) |
| 对账 | bot 推算的期望状态 vs 画面实读逐项比对核验(「拖拽后状态核对器」即做此事的模块) |
| 权威序 / 证据优先级排序 | 冲突时听谁的:实机实测 > 口述 > 米游社 > 社区(机制层);证明/实证 > 口述 > 攻略(策略层),见上节 |

## 玩家理解序(新读者从哪读起;依赖驱动)

> 顺序判据 = 玩法依赖:**机制是纪律的前提**(不懂利息档/牌池/乘区,就读不懂纪律为什么这样定),**纪律是过渡的前提**(过渡篇大量按条目号引用 user_playstyle),**过渡与形态证据是终局的前提**。

1. **玩法机制**(游戏怎么运转;自足无前置):
   - [combat.md](combat.md) — 战斗侧:伤害三乘区 / 星级收益 / 扣血结构(为什么装备与星级重要)
   - [economy.md](economy.md) — 经济侧:牌池 / 刷新概率 / 商店槽位行为(买与刷的机制边界)
   - [xp-rules.md](xp-rules.md) — 节点基础经验:节点经验结算(+2/+0/BOSS+12 待确认)/ 购买经验 4 金=+4XP / 升级门槛表(实机 145 局统计)
   - [board_structure.md](board_structure.md) — 板面格子结构:前台 4/后台 6 恒定,钻石/召唤物才扩后台;等级只定上场人数 cap(推翻旧 level 驱动布局模型)
   - [merge_mechanics.md](merge_mechanics.md) — 升星合成:买牌落点(备战→触发合成改落点)/场上吸收/备战最左/连锁合成(口述·权威;bot 期望态层与拖拽后状态核对器的合成期望规格)
   - [equipment_mechanics.md](equipment_mechanics.md) — 装备机制与使用策略(证据分级标注,码源+口述):穿着即合成/前后台限定/商店自带装备/唯一件/工具 7 件全量+使用语义(策略决策件挂策略池)/冶金炉回收流水线(经济账框架,math_proofs 第 14 号命题生产化)
   - [invest_effects.md](invest_effects.md) — 335 投资策略 + 83 环境效果全量分类(哪类效果可建模)
    - [变宝为废-首次合成垃圾化.md](变宝为废-首次合成垃圾化.md) — 投资环境「变宝为废」机制(游戏明文:每位面首次进阶合成 50% 垃圾袋)与牺牲合成对策(策略命题[口述]待证;决策)
   - [screen_flow_timing.md](screen_flow_timing.md) — 对局流程的画面流转时序(生产日志实证)
2. **玩家纪律**(人怎么打;机制之上的打法约束,直觉假设来源——策略命题以 math_proofs 证明与实证为准):
   - [user_playstyle.md](user_playstyle.md) ★ — 用户口述节奏全集:开局 / 经济利息律 / 升级 / 阵容 / 装备纪律(条目现存至 [42],稳定 ID 永不复用;**直觉假设登记簿**——策略命题以 [math_proofs](../../../develop/sr_od/application/currency_war/proofs/math_proofs.md) 证明与 sim/实机分布实证为准;条目引用须区分已证/待证)
3. **过渡体系与战力证据**(位面 1 怎么活到成型、什么形态能过;按口述条目号展开,故排在纪律后):
   - [transitions.md](transitions.md) — 过渡叙事:开局分级(终局阵容锁定资格)/ 成型停买线 / 换血点 / 保底过渡阵容(已抛弃史料)
   - [transition_combos.md](transition_combos.md) ★ — 四种过渡体系逐路线定义(引擎池 / 核心池;落码依据)
   - [stage_transitions.md](stage_transitions.md) — 位面 1→2→3 阵容演化定量(加法不换件的数据边界)
   - [h3_tier_core_crosstab.md](h3_tier_core_crosstab.md) — 档位 × 核心在场 × 败率交叉(实机语料统计)
4. **终局阵容**(位面 2/3 打什么):
   - [final_comps/](final_comps/README.md) ★ — 终局十类分类索引 + 单套阵容打法单一源
5. **方法论与证明**(怎么读阵容 / 怎么论证策略;工具篇,可穿插读):
   - [combo_methodology.md](combo_methodology.md) — 阵容理解方法论(技能 / 羁绊 / 玩法三层)+ 攻略黑话查证纪律
   - [plaza_methodology.md](plaza_methodology.md) — 玩法方法论 M1-M16(资源入口 / 核心×弹性 / 升星经济学 / 装备优先级…)
   - [math_proofs.md](../../../develop/sr_od/application/currency_war/proofs/math_proofs.md) — 策略命题的数学期望证明集**索引**(命题状态表;单篇证明在 [proofs/](../../../develop/sr_od/application/currency_war/proofs/) 目录,一命题一篇含推导过程与数字表;计算脚本在 `tools/cw/proofs/`)

## 索引(什么问题查哪篇)

| 问题 | 文件 |
|---|---|
| 人怎么打(开局/经济/等级/阵容/装备的直觉假设全景及其证明状态) | [user_playstyle.md](user_playstyle.md) ★直觉假设登记簿(证明状态随 [math_proofs](../../../develop/sr_od/application/currency_war/proofs/math_proofs.md)) |
| 经济机制:牌池/退金/刷新概率/多刷/保血边界/阶段共识 | [economy.md](economy.md) |
| 节点经验:基础经验(+2/+0/BOSS+12 待确认)/购买经验 4 金=+4XP/升级门槛表 | [xp-rules.md](xp-rules.md) |
| 节点类型:三位面默认序列地面真值 / 普通奖励节点=战斗型(有结算屏,档案已定案) | [plane_schedule_observed.md](plane_schedule_observed.md) |
| 升星合成:买牌落点/场上吸收/备战最左/连锁合成(买一张=可能升两级) | [merge_mechanics.md](merge_mechanics.md) |
| 战斗机制:伤害三乘区/星级收益/血量星/连胜经济/练度 | [combat.md](combat.md) |
| 过渡体系:位面 1 骨架/成型停买线/换血点/位面 2 保底过渡阵容(已抛弃史料)/买牌纪律 | [transitions.md](transitions.md) |
| **过渡阵容逐路线定义**(引擎池/核心池/开局直奔终局阵容的结构;落码依据) | [transition_combos.md](transition_combos.md) ★ |
| **终局阵容分类**(final comps 分类索引+逐类累积;核心角色/羁绊双维;**单套阵容打法知识单一源**) | [final_comps/README.md](final_comps/README.md) ★ |
| 阵容理解方法论(技能/羁绊/玩法三层怎么读) | [combo_methodology.md](combo_methodology.md) |
| 玩法方法论 M1-M16:资源入口/核心×弹性/多线通用角色分级/骨架拼装/升星经济学/装备优先级/站位… | [plaza_methodology.md](plaza_methodology.md) |
| 策略命题证明(某结论为什么成立/口述直觉的数学保证) | [math_proofs.md](../../../develop/sr_od/application/currency_war/proofs/math_proofs.md) 索引 → [proofs/](../../../develop/sr_od/application/currency_war/proofs/) 单篇 |
| 单套阵容打法(入场/退场信号/counter/装备叙事) | [final_comps/](final_comps/README.md) 各类文档(2026-08-22 起单一源;原 comps/ 打法卡层已撤销合并) |
| 投资卡效果全量分类与可建模边界(API 裁定) | [invest_effects.md](invest_effects.md) |

## 策略相关文档(改策略前的必读面;单一源在本节)

**策略工作的基线 = research/ 全部文档 + data/ 全部未建模数据文档**(research 按上方「玩家理解序」读:机制是纪律的前提,纪律是过渡的前提,过渡是终局的前提)——策略判断横跨经济/战斗/阵容/终局,漏任何一面都判错;不读全就无法预判改动波及面。

- research/ **唯一排除**:screen_flow_timing(画面流转时序,运行时/运维侧,非策略面)。
- data/(`docs/game/currency_war/data/`,**全部策略相关**):gameplay(官方玩法说明)/ competitors(词缀机制+20 竞争阵营唯一源)/ bosses(boss 克制启示)/ advantage_layouts(跨局 meta 增益)/ plaza_meta(实战 meta)。已建模入代码注册表的数据已删 doc,查值直接看注册表(清单见 data/README)。
- proofs/ 单篇按命题按需读(math_proofs 是命题状态表)。

消费方(sr-od-currency-war-dev skill、判读/验证工作流)引用「改策略前读什么」时指本节,别在别处另列清单。

## 关系图

- **值(数据)的单一源 = 代码注册表**(`src/sr_od/application/currency_war/data/cw_*.py`);本目录记「凭什么信」。
- **设计消费**:`docs/develop/sr_od/application/currency_war/strategy-docs/` 的 as-built 正文引用本目录结论(只引结论一句话+链接,不复制内容)。
- **上游**:原 ../sources/ 外部原文存档(已删[eb9c72a1],git 历史 `eb9c72a1~1` 可查);仍被引用的条目以各篇「原文细节补记」块为仅存记录,本目录结论的证据等级就地标注。
- **裁定/教训不进本目录**:玩法取舍 → 设计文档动机段与代码注释(ADR 档案体系已按用户令退役);分析教训 → 本地 insights。
