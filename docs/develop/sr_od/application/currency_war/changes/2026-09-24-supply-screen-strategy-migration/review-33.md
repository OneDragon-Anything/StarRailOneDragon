# review-33 文档批对抗审查(aae6ee303 / c472e852d / ab808e7a9)

- 审查对象:①`aae6ee303` 新建 30 号稿;②`c472e852d` 八处指针更新;③`ab808e7a9` 迭代工件 16 件入册。
- 规格单一源:本目录 design.md §2.7(文档面)+ §2.2-§2.6(判据语义);landing.md 阶段 3.3(范围/判据/grep 词表)。
- 方法:三笔逐 hunk 亲读;30 号稿全文对照 design §2.2-§2.5 与实码 `strategies/impl/mandate_v1/supply.py`、`strategies/impl/flow.py`、`operations/cw_screen/cw_screen_supply_node.py` 逐条对;landing 3.3 验收词表复跑;git 史实证核查。
- 结论:**0 高 / 1 中 / 5 低**。判据语义、裁定登记、指针改后形态、验收词表全部达标;中位项(F1)为画面文档死符号指针残留,建议随本批收口补一刀;低位项不阻断。

## 发现清单

### F1 [中] `docs/game/screens/currency_war_supply.md:55` — `RunSupplyNode` 死符号指针残留,与同文件 :57 自相矛盾
- 内容::57(本批改写)申报「旧 `RunSupplyNode` 执行器已退役,现役 = `CwScreenSupplyNode`」;:55(识别快照节,不在 design §2.7 点名锚清单内)仍写「`RunSupplyNode.CARD_BODY=(900,550)` 硬编码兜底」。`RunSupplyNode` 全仓(src/docs/skills)代码零命中,该兜底常量现址 = `operations/cw_screen/cw_screen_supply_node.py:83`(`CwScreenSupplyNode.CARD_BODY = Point(900, 550)`,数值同为 (900,550))。正本画面文档内一处说符号已死、一处仍引该符号。
- 判据:landing 3.3 验收「全仓 grep 旧指针零残留(白名单 = changes/ 历史工件 + 在册存活指称)」——`RunSupplyNode` 两者皆非。
- 修正方向::55 改指 `CwScreenSupplyNode.CARD_BODY`(`cw_screen_supply_node.py:83`)或去符号化写「兜底点 (900,550)」。

### F2 [低] `strategy-docs/30_supply_screen.md:79` — 正本引跨迭代里程碑锚「sim-redesign 迭代 M18」,指向 changes/ 工件内容
- 内容:§6「①决策腿接线(在册交接:sim-redesign 迭代 M18)」——M18 的定义住 `changes/2026-09-15-sim-redesign/design.md`(changes/ 工件,寿命 = 迭代、不定期删减);正本引之违「代码与正本文档禁引 changes/ 内容(长期引用),正本必须自足」。同类先例已在 `changes/2026-09-22-screen-review/supply_node.md:54` 登记为全仓清理候选,本稿属新增一例。句子语义本体(决策腿接线 = sim 可见前置)自足,锚死后不失义,故降为低。
- 修正方向:去里程碑号,改纯语义(「在册交接:sim-redesign 迭代的决策腿接线」)。

### F3 [低] `strategy-docs/16_evaluation_tables_reassessment.md:74` — 已删代码称「现址」,用词自相矛盾
- 内容:「该内联形态现址 = cw_events.py:616-647,已随 2026-09-24 补给屏策略层迁移删除」——代码已物理删除则无「现址」;同格「`EQUIP_GENERIC_VALUE` 表本体现址 = `cw_equip_value.py:42-80`」(活符号)用法正确,对比之下错位更显。
- 修正方向:「现址」→「原址」(或「删除前实址」)。

### F4 [低] `design.md:100` 与 `landing.md:29/:38` — 对共享文件旧态的记载失准(「18-27」「env/29 两批先后漏改」)
- 内容:design §2.7 称导航句旧态为「18-27」且「env/29 两批先后漏改」;landing 3.3 验收词写「18-27→18-30」。git 实证:投资策略批 3.3(`9cce56962`)已把该句 18-27→18-29,本批落批前像 = 18-29(`c472e852d` diff 可证)——「29 批漏改」不实,「18-27→18-30」与实际前像不符。终态「18-30」正确,「18-27 零残留」验收平凡通过;落批执行面遵守了跨批协调纪律(重读当前态),失准仅在 design/landing 文本记载层。
- 修正方向:changes/ 工件寿命 = 迭代,可随收尾批勘误(改为「env 批漏改、29 批已收口至 18-29,本批 18-29→18-30」);不阻断。

### F5 [低] 本目录 `README.md:11-12` — 入册时的进度快照与同批可观察历史矛盾
- 内容:入册 commit(`ab808e7a9`,14:03:07)仍记「落地:未开始」「正本更新:未开始」,而 3.1/3.2(`f07ba95ca`/`b90b12746`)与 3.3 文档面(`c472e852d`,14:03:00)在其之前/同分钟已落地;同批入库的 30 号稿与指针更新即 3.3 交付物。快照停在落码前的旧态。
- 修正方向:进度树按实态刷新(3.1-3.3 已落地待记、3.4 实机判读与末阶段未开始);若为刻意时点快照,注明快照时刻。

### F6 [低] `strategy-docs/30_supply_screen.md:9` — 类比从句缠绕,易误读为「本画面含【拍】值登记」
- 内容:「(同 28 号稿立场分形态,数字三形态扩展【拍】的裁定来源)」——按 01 §6 章程,【拍】值须落策略层立场分表;本批判据为结构序、零【拍】数值、无立场分表。读者按句索表会扑空;从句本身也难断句。
- 修正方向:改「合法性法理同 01 §6【拍】形态(裁定即证据);本篇判据为结构序,无【拍】数值登记面」或等效直白句。

## 攻击面清单(核毕无发现)

1. **30 号稿 vs design §2.2-§2.5 判据语义逐条**:三级字典序与多钻「带钻候选集内细分」、空帧 idx=0 no-options、`get_comp` 空串/失败两口径、`demoted_endgame` 防御位、名单 = core∪shared 不含 transition、char 读缺不进候选仍参与装备轴、tier 3/2/1/0 语义与需求计数、两账三参、排序链(tier→通用值→输入序)、凑星判据 `same_star_count==2` 布尔零梯度与 deployed 展平/bench 槽序申报、`gs.board` 非数据源、3★ 不入判据、刷新三级全空(读法 A 只看档位)+ 次数闸内嵌 fail-closed、闸拒绝帧产出语义(组合不存在/仅锚点缺触发面)、P1 配方锁帧形态、输出契约与词表映射、席满溢出席 + 记账失真申报——全部保真,无缺项。
2. **30 号稿 vs 实码 as-built**:常量指称全部实存(`cw_node_obs.DIAMOND_EQUIP_NAMES`:216;`cw_equip_value.pick_equipment`:192((tier, base) 字典序、并列输入序先);`equip_tier`:163(计数语义逐位吻合);`cw_merge_simulate.same_star_count`:424;`gs.supply_refresh_left`(None=未观察,cw_game_state:2147);`Comp` 四字段 cw_comps:102/:108/:111/:112)。多钻 pool 口径(:120)、闸拒绝落第 3 级路径(刷新分支要求角色级空转,:126)、`_two_accounts` 与 `flow.decide_box_card`(:759-779)逐位同形——文档写的就是代码做的。
3. **裁定登记四项**:每项收裁定原文;读法 A 确认记录在(裁定④,含 2026-09-24 确认与两读行为相反申报);出处齐(节头「用户 2026-09-24」+ ④内联日期)。
4. **八处指针改后形态**:25 号稿三处(头注清单/§1 差异要点/§2 表行)+ 新增拆分头注(照 28/29 先例);13 号稿 §1 行(照 decide_invest_env 行先例)与 §2 E4 行;README §2 增 30 行 + 导航句 18-30;08 号稿 E4「现有语义」格整体替换(旧描述以退役声明保留,同 E1 行先例);16 号稿 :74 整体改写(结构映射四条/死引用替锚/支配定性对齐,无旧表述残留为现行语义);三份画面文档各锚(screens/supply.md 委托指针+双闸语义、currency_war_supply.md :19/:37/:39/:57、货币战争-补给.md :32/:39)——逐处与 design §2.7 对上。
5. **as-built 纪律(30 号稿)**:无进度标记、无「本批」、无过程叙事;🔴 = 01 §6 在册待标定分级、【拍】= 章程扩展形态,均非自造黑话(唯 F6 从句缠绕);不复制 13 号稿判据(头注反向指针 + 「本篇不复制」);常量只写名(tier 档位数 = 结构语义非调参值)。
6. **landing 3.3 词表复跑**:25 号稿「补给」恰 1 行(头注);13/08/16 补给表述 = 指针行/销账形态;README「18-27」零残留;三画面文档 `decide_supply` 全指策略层(:3/:39 为白名单存活指称 = flow/ABC 方法名);src `decide_supply` 命中全白名单(flow 入口/ABC/调用点)、`SupplyPick`/`supply_reroll_decision` src+测试+skills 零命中;`flow.py:598` 的 `refresh_used` 属 `decide_encounter`(kernel 委托现存形参,非残留)。
7. **夹带与豁免**:三笔文件集 = 1/8/16,恰等申报面,无集外文件;commit 3 目录级 add 满足豁免(整目录本批新建,16 件全为新文件,无既有文件被卷入)。
8. **引用寿命**:30 号稿零引本批 design/landing(F2 的 M18 为唯一 changes/ 类引用,已立 F2);被删符号在正本与代码零墓碑(除 F1)。

## 范围外观察(不计发现)

- `screens/README.md:113`「pick 族八接口」计数与 `flow/README.md:81`「pick 族 12」不一致(存量文本,非本批编辑面);30 号稿以 §5.2/§5.5 为能力面指针,建议该计数随后续批收口。
