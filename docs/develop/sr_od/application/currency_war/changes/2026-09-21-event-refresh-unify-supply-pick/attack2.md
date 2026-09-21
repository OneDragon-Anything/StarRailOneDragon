# 第二轮无前提对抗审（核一）

- 攻击者：核一·无前提攻击（iteration-design.md §7 核一 + §5 写作硬规则卡点）
- 对象：design.md / landing.md **现稿**（README.md 仅上下文；attack.md = 历史工件非权威源）
- 方法：不锚定前轮结论，全部主张自行读正本/代码/归档帧复核；判定只看证据
- 日期：2026-09-21（第二攻击轮）

---

## ① 总判

**需修订（1 项阻塞 + 5 项建议）**。

阻塞项集中在 §2.0B「norm_item 注册表级归一」：把「同 LCS 阈值 0.75 + 唯一命中才返回」从 10 锚名单原样移植到 158 名 EQUIPMENTS 键集，存在**完美 OCR 下也系统性多命中**的结构性歧义（实测 79/158 名落入多命中，含 垃圾袋/生命之花/追击星徽/击破星徽 等基础件与全部 特权/白昼/Max 变体）——设计未对该键集做过任何歧义分析。其余刷新链终结化、闸剩余语义化、消费点迁移总表、验收判据、正本更新清单经逐点对码**全部核过成立**，无前轮同型回归。

## ② 逐条发现

### A1 [阻塞] | design.md §2.0B「norm_item 锚集升级」/ landing 3.1 同段 | 注册表级「LCS 0.75 + 唯一命中」在 EQUIPMENTS 158 名键集上完美 OCR 也系统性多命中，设计未做任何键集歧义分析

- **问题**：设计把 `normalize_equip_name` 的判据（`_similar_equip_hits`：LCS(text,name)/len(name) ≥ 0.75，唯一命中才返回，多命中 = ''）原样扩到注册表键集。该阈值是在 10 个银狼锚名上标定的（`cw_events._EQUIP_NORM_LCS_FLOOR` 注释自证：0.75 = 件名 4 字容错 1 字）。对 158 名键集实算（本审查直调注册表名集复算，判据逐字复刻 `_similar_equip_hits`）：**完美 OCR（text = 精确规范名）下 79/158 名返回多命中 → '' 未解析**。典型：
  - 基础件互撞：「垃圾袋」同时命中 垃圾袋(1.0)/金垃圾袋(1.0)；「生命之花」同时命中 生命之花(1.0)/生命之环(0.75)；「追击星徽」「击破星徽」互撞（LCS=3/4=0.75）；「昼/夜之半神星徽」互撞（0.75）；
  - 全族撞：「碎星斩舰刀·特权」等 **36 个特权名全部**命中自己的进阶基名（基名含于特权名，LCS/len(基名)=1.0）；白昼/极·白昼 6 名 3 重命中；Max/Pro 后缀族（分身墨镜Max/数据拷贝仪Max·Pro/病毒防火墙Max/扑满病毒Max·Pro/星核猎手卡带Max/欢愉卡带Max/管理员手套ProMax）；命运族 极/诅咒 三重命中；穿刺/穿越死棘之枪互撞（1.0）。
- **后果**：这些名字的补给卡即使 OCR 完美读对，norm_item 也恒 ''——①`owned += norm_item` 不写（账面缺件）；②`apply_equip_acquire_consequence` 不发射（送角色腿缺失，bench 少人）；③全靠「观察覆盖自愈」兜底。fail-closed 方向没错，但设计宣称的核心机制（「账面恒标准名」「param 现有字段即 report 全部输入」）在约半数名字空间上**结构性地不工作**，且设计正文对键集歧义零分析（§2.0B 只分析了长文本误挂单向，没分析键集内部互撞）。
- **权威源证据**：`kernel/cw_events.py:916-941`（阈值注释=银狼锚标定语境；唯一命中判据）；`data/cw_equipment_data.py:51-231`（158 名键集）；本审查复算表（79 名多命中清单已留档，可 `uv run python` 复现，判据 = 逐字复刻 `_similar_equip_hits`）。
- **建议修法**（任一，写入 §2.0B 并同步 landing 3.1）：
  1. 注册表级入口加**精确命中快道**（text == 键名 → 直接返回），相似归一只作 OCR 形变救援层；
  2. 照 `classify_planner_leg` 判定序第 1 步先例加 **containment longest-first** 优先（「碎星斩舰刀·特权」containment 命中自身先于基名），多命中只在相似层拒；
  3. 或多命中改「longest-match 取最长命中」+ 仅零命中/并列最长才拒——但须论证取最长在 OCR 缺字方向的安全性。
  无论选哪条，§2.0B 须补一段键集歧义分析（哪些名互撞、判据如何消解），验收锚 1 建议加一条「特权/后缀族名完美 OCR 归一命中」行为锁。

### A2 [建议] | design.md §2.0B/§2.3（owned 名源段） | 「模板键集 = 装备注册表」不严格成立：注册表 158 名、模板库 157 张，「财富」无模板

- **问题**：设计两处宣称 owned 权威写端 `read_equips`「模板键集 = 装备注册表」。实测（equip_plaza 模板文件名 stem vs 注册表名 diff）：157/158，唯「财富」无模板。「财富」若经补给/获得链入 owned，观察侧永远分类不出 → A1 之外的另一条「miss 后观察无法自愈」路径，设计的「观察赢自愈」对该名恒不成立。
- **权威源证据**：`assets/template/currency_war/equip_plaza`（157 文件）；`data/cw_equipment_data.py`（158 名）；装载单一源 `operations/cw_op/cw_op_equip_all.py:139-158`。
- **建议修法**：§2.3 owned 名源段改精确表述（157/158 + 财富缺口申报），或补「财富」模板采集挂账；至少把「模板键集 = 装备注册表」降为「模板键集 ⊆ 注册表，缺 财富」。

### A3 [建议] | design.md §2.0B（fail-closed 自愈句）/ §2.3 | 「错名不入账，下帧模板匹配观察覆盖真值，观察赢自愈」的覆盖时序未论证：miss 与下一个装备观察写端之间存在按名消费面，设计未给覆盖序论证

- **问题**：owned 观察写端唯一 = 备战 heavy 帧（`cw_screen_prep.py:338-350`，`owned_equips` 失读还跳写）。按名消费面：商店线 spare 打分（`strategies/impl/flow.py:675-676`）、comps（`cw_comps.py:1455`）、穿戴计划（`cw_equip_wear_plan.py:175`）、mandate 决策帧（`mandate_v1/entry.py:853`）。设计断言「下帧…覆盖自愈」但没有论证「补给 pick 到下一次备战 heavy 观察之间不存在（或存在但无害）按名消费窗」。补给确认后回到备战帧、备战帧入口先 heavy 观察再开商店/决策的次序**大概率成立**，但这是设计必须就地写出的覆盖序论证（哪帧覆盖、谁先谁后、失读跳写时窗多长），不是读者自明。
- **权威源证据**：上述四消费点 + `cw_screen_prep.py:345`（失读 None 不写保现值）+ `obs/cw_observation.py:2732` 注释（「商店线权重与 flow 打分读 gs.equips」在册申报=已知消费面）。
- **建议修法**：§2.3 补一段覆盖序论证（补给 pick → 备战 heavy observe 先于任何商店/穿戴/mandate 决策消费；失读跳写 = 消费读旧值，危害 = 低配错排序，方向与现役 OCR 原始名不入键同一量级），并如实申报失读窗残余。

### A4 [建议] | design.md §2.0B「一口写序」 | 写序只列 ①owned ②单位腿 ③装备后果腿，未提现状「内容全未知」分支（char/item 双空 = 兜底点卡路径）的去留

- **问题**：现 `report_action_pick_supply_param` 落地相有一个前置分支：char_name 与 norm_item 双空 → bench/equips 双翻来源 + `pick_supply_content_unresolved` 缺陷行（`pick_supply.py:76-88`）。设计的一口写序与 landing 3.1 的「未解析翻来源留证语义保持」都没有点名该分支——实现者可以合理疑问「兜底点卡路径（CARD_BODY，opts 读缺时 param 双空）在新单相里是否保留双翻+缺陷行」。这是设计漏 declared 面，不是行为分歧（保留显然合理）。
- **建议修法**：§2.0B 一口写序补第 0 步「char/item 双空（兜底点卡路径）→ 现行内容全未知分支逐位保持」。

### A5 [建议] | design.md §1.3(3)/landing 3.1 | 死符号清理范围只写「模块头」，`cw_screen_supply_node.py:281-282` 行内同款陈旧注释不在清理面也无 grep 判据覆盖

- **问题**：`_do_action` 内注释「不动 `_LAST_SUPPLY_PICK` 暂存槽(其唯一消费者仍是 cw_loop 合成结算行…)」——该暂存槽现役不存在（全仓仅注释引用），「唯一消费者 cw_loop」为虚构事实。§1.3(3) 与 landing 3.1 都只写「模块头死符号引用清理」，行内注释漏网；3.1 grep 零残留判据（EVIDENCE/_pending_supply/_apply_supply_landing）也不覆盖它。
- **建议修法**：3.1 范围句把「模块头」放宽为「本文件内 set_last_supply_pick/_LAST_SUPPLY_PICK 全部注释引用」，或 grep 判据加这两个符号（豁免 = 无）。

### A6 [建议] | design.md §2.2 表 | sim 侧只安排了 supply 的 left 初值写点，encounter 的 left 在 sim 无写端、无申报——bridge 判据换源后 sim 遭遇决策输入恒 None

- **问题**：§2.2 把 `encounter_refreshed_in_visit` 的 flow.py+bridge.py 消费点改读 `encounter_refresh_left`（None → used=True → 恒拒刷新），但全表无 sim 行为 encounter 安排写端（supply 行有「节点入口先写初始 left=1」）。sim 引擎不建模遭遇刷新执行（`grep sim/ 零 encounter refresh 命中），但 sim 若走 bridge/flow 判据，换源前后 decide_encounter 的 refresh 旗标输出会翻转（旧：位恒 False → 允许建议；新：left 恒 None → 恒拒）——sim A/B 对照口径静默变化，未申报。
- **建议修法**：§2.2 或 §2.3 补一句 sim 遭遇侧申报（二选一：sim 遭遇节点入口同款写 left 初值保持判据输出不变；或申报「sim 无遭遇刷新面，left 恒 None = 判据恒拒，属预期」）。

## ③ 全量同步复查结果表

| 复查面 | 结果 |
|---|---|
| design §1 症状 ↔ §2 方案 ↔ landing 三阶段覆盖 | 1.1(1)→§2.0B/3.1 ✓；1.1(2)→§2.0A/3.3 ✓；1.1(3)→§2.0A 闸/§2.1/3.2+3.3 ✓；§1.3(3) 死符号→3.1（A5 范围偏窄）；反向无孤儿方案项 ✓ |
| 依据就地标注真实性（正本锚） | op-layer §1.1/§1.2/§1.4（两条全域规范原文在册，:52-53）/§2.2/§3 ✓；action_ops §1 增补 2（:11）+ §2.2 固定等待族 + §4.5 欠账三行 + §4.6 三刷新动作行 ✓；action_exec §2.1 ✓；fields §3.4.1「遭遇屏建档无剩余次数区域——现役走代码内矩形先例」原文一致（:736）、§3.4.2/§3.4.3/§3.4.4 ✓；supply.md §2-§9 节名齐 ✓；screens/README §5.5/§6 ✓；screen_flow_timing #19/#23（:85/:89，补给/遭遇刷新 2s 稳定）✓；iteration-design §5/§7 ✓ |
| 依据就地标注真实性（代码锚） | `CwActionPickSupplyOp.run`（0.6s/确认/到账登记/report_node_advance supply_confirm 点击即上报）✓；`_pending_supply`/`_apply_supply_landing` 证据闩 ✓；`_decide_encounter_action` 同访问重读+二次覆盖写+per-visit 位读写（:131-169）✓；`_try_refresh` 点钮+2s+`self.screenshot()` 重读（:171-195）✓；`encounter_refresh_used` 现役零落码写点、恒种子 0（:1776 种子 + 全仓无写端）✓；`supply_refresh_used` live 发射即 +1（supply_node :306-313）✓；`invest_env` 摄入先例（读缺跳写 + names 空整函数早退，:62-68）✓；`CwScreenEncounterObs.refresh_left` 已存在且 report 不消费（encounter.py :39/:57 早退）✓；`read_encounter_refresh_count` 已双出 (count,point) ✓；`_read_refresh_anchor` 现单出 Point、`_REMAIN_RE` 已捕获 N ✓；建档「文本-剩余次数」rect x=1347-1484（yml :61-68）✓；`node_screen_refresh` 域版本 2（game_state :173）✓；flow.py :497-526 / bridge.py :204-227 读源声明与实码一致 ✓；sim :620-634 observe +1 ✓；schema.py :529 陈旧注释在位 ✓；`CwActionPickSupplyParam` 现有 char_name+norm_item、无 raw_item/has_diamond（cw_vocab :726-749）——「param 零扩」属实 ✓；`_PLANNER_EQUIP_ANCHORS` = ITEM_WEAR_GATES 10 键、补给基础件不在列 ✓；LCS 阈值 0.75 = `_EQUIP_NORM_LCS_FLOOR` ✓（但见 A1）；`decide_supply`/两处 `decide_encounter`（cw_events :634/:727、cw_encounter_selection :337）`refresh_used: bool` 形参与「True 则不再建议刷新」消费实码 ✓ |
| §2.2 消费点迁移总表 vs 全仓 grep | 三退役符号 src 侧：supply_used（supply_node 读闸+写点/flow/sim/game_state/audit/schema 注释 6 行齐）✓；encounter_used（encounter 读闸/种子字段/audit）✓；refreshed_in_visit（flow+bridge 旗标源/encounter 读写点/game_state/audit/encounter report docstring 两处——report docstring 随 3.3 改写归「文件面」覆盖）✓；`picked['refreshed']` 值链（组装点+schema 注释）✓；ConfirmSupply（pick op 登记/_overlay_confirm/cw_exec_state）✓；EVIDENCE_OVERLAY_CLOSED 仅 pick_supply 定义+supply_node 导入+t60 SUPPLY_EVIDENCE 面，pick_equip/pick_planner 同名常量豁免申报 ✓；`normalize_equip_name` 消费面（supply_node :341 组装点 + equip_pick 彼辖不动）✓。**无遗漏、无过度**。sr-od-test 侧命中（obs_arch_event_screens/step3/opening_seed/route_clear/t60/yinlang_phase32）归「受影响测试」+ grep 零残留判据强制重写，机械可执行 ✓ |
| 正本更新清单条目 ↔ 致变正本节 | supply.md §2/§3/§4/§5/§6/§8/§9、encounter.md、README §5.5/§6、op-layer §1.1/§1.2/§2.1/§2.2/§3、action_ops §4.5/§4.6/§2.2、action_exec §2.1、fields §3.4.1/§3.4.2——节名全部实存且与致变面对得上（含上轮 F6/F7 清偿项：action_exec §2.1 已挂、README §6 已挂）✓；兜底 grep 行 ✓ |
| 归档帧 | `sr-od-test/screens/货币战争-补给/{default,双排装备}.webp` 文件存在 ✓；帧内容「剩余 0/1」本会话无视觉能力未直读复核——与 supply_node 代码注释引用同一组帧（钮心/文本框几何锚同源），一致性间接支持；如实申报为未直读项 |
| 规范遵循（action_ops §1 三条 + op-layer §1.1/§1.2/§1.4 新两条） | 「点完立即上报完整结果」与 chosen_supply 留守的并立自洽：写点 = 选择点（派发前，supply_node :342-359），先于动作 op 执行——「点完即报」辖效果腿、选择事实边界（op-layer §2.2）辖事实腿，两腿不同物 ✓；「刷新 = 终结」方案（访问内零重读/零二次写/零重决策）与 §1.1 读屏点纪律消解 ✓；「闸 = 剩余语义观察真值」双闸同源 + None 拒绝与 §1.4 :53 文本一致 ✓；活锁方向论证（放行→终结 / 拒绝→重调一次→选卡终结，`decide_*` 的 refresh_used=True 分支实码背书）✓ |

## ④ 试读结论（逐阶段）

- **3.1（补给选卡即时上报）**：**除 A1 外可开工**。report 单相化、ConfirmSupply 退役、pick op 即时上报、死符号清理、grep 判据（含 t60 SUPPLY_EVIDENCE 豁免申报）均可直接落码。A1 未修前，「注册表级相似归一入口」的算法规格是坏的——照字面实现（同 LCS 0.75 唯一命中）会交付一个对半数名字恒 '' 的归一层；worker 无权自选消解策略（design 未给），撞上即停手。
- **3.2（补给刷新闸观察化）**：**可开工**。obs 加字段/双出扩展/容器 left/闸拒绝分支/sim 初值 left=1/picked 键改 refresh_left/schema 注释/:529 顺手清——文件面、判据、豁免口径齐，无「看情况」项。
- **3.3（遭遇刷新链终结化）**：**可开工**。摄入序（options 空整函数早退含 left，invest_env 先例实码同构）、_try_refresh 删重读半、per-visit 位退役、flow+bridge 换源、域版本随批 bump——边界与「不动面」（chosen_encounter/重入裁决）清晰。
- **末阶段（正本更新）**：清单节名全部实存、与致变节对得上；兜底 grep 行可机械执行。A6 建议随批在 fields/op-layer 申报中带一句 sim 遭遇侧口径。

## ⑤ 零发现面声明

以下面本次攻击**零实质发现**（逐点核过、依据真实且支持主张）：§1.1 三条症状的代码锚与定性；§1.2 根因归层（约定层）；「param 零扩」（字段现状即 char_name+norm_item）；消费点迁移总表的完备性与克制（无遗漏无过度）；三退役符号的退役路径与 grep 判据可执行性（含 sr-od-test 强制重写面与豁免口径）；活锁方向安全性论证；kernel 签名不动取舍；chosen_supply 留守与「点完即报」的并立自洽；正本更新清单（上轮 F6/F7 清偿后现稿指向全部真实）；README/landing/design 三者状态与阶段划分一致（「阶段 0/3 done」表述略俭但无歧义）；归档帧文件存在性。
