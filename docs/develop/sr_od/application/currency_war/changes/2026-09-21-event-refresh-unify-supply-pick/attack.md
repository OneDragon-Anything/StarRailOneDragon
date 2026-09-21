# 对抗审报告 · 核一·无前提攻击（规范出处 = docs/develop/harness/iteration-design.md §7 核一 + §5 写作硬规则卡点）

> 攻击对象 = 本目录 design.md（总纲）+ landing.md（落地拆分）；README.md 仅作上下文。纯文档对抗审：代码核对 = 读码核符号存在性与语义；归档帧经视觉复核（视觉子代理直读 webp）。零预设焦点，结论只看证据。

## ① 总判

**需修订**（不可按现稿直接定稿开工）。发现总数 **16**，其中**阻塞级 4**（F1–F4）、建议级 12。四条阻塞的共同形态：3.1（补给选卡即时上报）的方案在**数据载体与规范边界**两层都欠定——report 单相化「一口写」所需的关键输入不在任何声明的载体内（F2），chosen_supply 写入 report 违反 op-layer §2.2 动作事实边界硬规则且正本更新清单未列该条款修订（F3），telemetry `refreshed` 布尔语义随两符号退役断链（F4），且 landing 3.1 的 grep 完成判据按字面永不可满足（F1）。修完 F1–F4 后方案主体（刷新链终结化 + 闸剩余语义化，3.2/3.3）证据链扎实、可定稿。

## ② 逐条发现

### F1 [阻塞] | landing.md 3.1 完成判据 | 「EVIDENCE_OVERLAY_CLOSED / ConfirmSupply 全仓 grep 零残留」按字面永不可满足

- **对象位置**：landing.md 3.1 完成判据第 2 行；design.md §3 验收锚 1（「`_pending_supply`/`EVIDENCE_OVERLAY_CLOSED` 零残留」——「全链」措辞含糊，landing 把它放大成「全仓」）。
- **问题**：`EVIDENCE_OVERLAY_CLOSED` 是**每动作文件各自定义的同名常量**，不属 supply 专有。全仓 grep 实况（本次复核）：`kernel/cw_action_report/pick_equip.py:40`、`pick_planner.py:55` 各自定义；`operations/cw_screen/cw_screen_equip_pick.py:44,137`、`cw_screen_yinlang.py:49,220` 导入消费；测试 `test_cw_yinlang_phase32.py`（10+ 处）、`test_cw_pick_channels_t60.py:39`（pick_equip 侧 `EQUIP_EVIDENCE`）在用。这些全部是 §1.3 明确不解决的 PickPlanner/PickEquip 两相欠账辖内合法残留。判据照字面执行 = 3.1 永远无法验收（worker 撞上即停手令）。
- **权威源证据**：见上 grep 实况；design.md §1.3「明确不解决：PickPlanner/PickEquip 两相欠账」自证这些面必须保留。
- **建议修法**：判据限定符号来源——「`kernel/cw_action_report/pick_supply.py` 内的 `EVIDENCE_OVERLAY_CLOSED` 与其在 supply 链的导入点（`cw_screen_supply_node.py`、`test_cw_pick_channels_t60.py` 的 `SUPPLY_EVIDENCE`）零残留；pick_equip/pick_planner 各自同名常量不在辖内」。`ConfirmSupply` 可保留全仓口径（删两处分支 + pick op 登记调用 + 受影响测试后确实可归零），但应显式声明豁免面 = 历史遥测只读注释。

### F2 [阻塞] | design.md §2.0B / §3 验收锚 1 | report 单相化「一口写」的 ①② 两腿数据载体未定义——param 不携带 OCR 原始装备名与 has_diamond

- **对象位置**：design.md §2.0B「一口写序 = ①`chosen_supply` 三元组 ②`owned += 装备原始名` …」；§3 验收锚 1「`chosen_supply` 三元组 + owned 含装备原始名」。
- **问题**：report 函数唯一声明的输入 = `CwActionPickSupplyParam`，其字段只有 `idx / reason / char_name / norm_item / route_tag`（`kernel/cw_vocab.py:727-749`），且 docstring 明言「OCR 原始名不静默改写**由 handler 持有**」。腿①需要的三元组含 `has_diamond` 与原始装备名，腿②需要 OCR 原始装备名——三者在 param、obs 声明的传递面里都不存在。design 全文未声明 param 扩字段（如 `raw_item`/`has_diamond`）或改经 env 传递；「OCR 原始名…由 handler 持有」的现行架构约定如何随之改也未写。实现者必须自行发明载体与字段语义 = 违 §5「实现者无需再设计」。
- **权威源证据**：`cw_vocab.py:727-749`（字段清单 + 原始名归 handler 声明）；`cw_screen_supply_node.py:333-341`（原始名/has_diamond 现居 handler 局部 `_opt`）；`cw_overlay_pick_action.py:229-235`（现行到账登记的原始名来自 `env.picked['equip']`，非 param）。
- **建议修法**：§2.0B 显式声明载体——最小修法 = `CwActionPickSupplyParam` 增 `raw_item: str = ''`（OCR 原始装备名）与 `has_diamond: bool = False`（均 `action_key_exclude` 先例），handler 组装 param 时随 `char_name/norm_item` 同点现算；同步声明 param docstring「原始名归 handler 持有」句随之改写。

### F3 [阻塞] | design.md §2.0B | `chosen_supply` 写入 report 函数违反 op-layer §2.2 动作事实边界硬规则，正本更新清单未列该条款修订

- **对象位置**：design.md §2.0B（leg ①）；landing.md 正本更新清单 op-layer.md 条目、supply.md 条目、fields.md 条目。
- **问题**：op-layer §2.2 硬规则原文「chosen_*（选择落地记录）与 per-visit 位…**留守画面 op**——记账随判定点走…**不进 report**」（投资域经**获得链**是唯一在册豁免，supply 不在其中）；fields.md §3.4 前言（:685）与 `screens/supply.md` §6（:67）同款。design 把 chosen_supply 写点从 handler 选择点迁进 `kernel/cw_action_report/pick_supply.py`，与三条正本现行文本直接冲突；而 landing 的 op-layer 条目只列「§2.2（**刷新计数出辖节**改剩余语义全域）」、supply.md 条目 §6 只写「supply_refresh_used 行退役」、fields.md 条目只写 §3.4.1/§3.4.2——**没有任何一条覆盖动作事实边界条款与 chosen_supply 写端口径的修订**。末阶段按清单执行后正本与实现必然失同步。
- **权威源证据**：op-layer.md §2.2（:76）；fields.md :685-687；supply.md :67（「chosen_supply 确认即写…留守决策体」）；landing.md 正本更新清单 :59-62。
- **建议修法**：二选一并写明——①正本清单补条目：op-layer §2.2 动作事实边界增 supply 收窄条款（选择事实经动作上报函数在选择点写，同投资域先例精神）、supply.md §6 / fields.md §3.4.1 前言同步改写；②或 chosen_supply 维持 handler 选择点写（现状已是确认即写），report 一口写序去掉 leg ①。取①则 design §2.3 关键取舍补一条理由。

### F4 [阻塞] | design.md §2.1/§2.2 + landing 3.2 | picked['refreshed'] / 遥测 synthetic_supply 的 `refreshed` 布尔随两符号退役失去值定义，消费点迁移总表漏项

- **对象位置**：design.md §2.1（「删实例旗标 `_refresh_used` 与容器计数写点」）、§2.2 表（`supply_refresh_used` 行只列 6 个消费点）；landing 3.2。
- **问题**：`_do_action` 真选分支的选定快照 `picked['refreshed'] = _refresh_used`（`cw_screen_supply_node.py:336`）是遥测链的**值生产者**：`telemetry/schema.py:645-646` 明载「refreshed=该次确认前是否已刷新重掷（**值源 = 容器 node_screen_refresh.supply_refresh_used 计数 >0 读点**，CwScreenSupplyNode 选定快照随行）」。3.2 同时删掉实例旗标（生产者）与容器计数（值源），而剩余语义 `supply_refresh_left` **无法等价导出**该布尔（无「本局初始授予数」基线，left=1 既可能是未刷也可能是授予 2 已刷 1）。landing 3.2 只写「telemetry/schema.py（仅注释）」——注释改了，值生产链断了。设计未定义 refreshed 的新语义（弃字段？改语义为 left 快照？保留实例旗标仅作遥测源？）= 语义选择未定稿。
- **权威源证据**：`cw_screen_supply_node.py:331-336`；`telemetry/schema.py:642-651`；design.md §2.2 表。
- **建议修法**：§2.2 表补一行「`picked['refreshed']`（遥测选定快照字段）」并定语义——最简 = 改为携带 `supply_refresh_left` 现值快照（读端按 `left` 分型），schema.py 相应改字段语义注释而非仅「值源改 left 读点」；或显式声明 refreshed 字段退役（历史数据只读保留，新数据恒缺省）。

### F5 [建议] | design.md §1.3 | 「P81 判据」误标——P81 仅辖投资策略屏逐卡刷新，decide_encounter/decide_supply 的刷新判据另有出处

- **问题**：design §1.3 称「`kernel/cw_events.py::decide_encounter/decide_supply` 的 **P81 判据**…不动」。权威源明示 P81 = 投资策略屏逐卡刷新弱占优（`proofs/math_proofs.md` P91 行；`strategy-docs/08_events.md` E4 行明文「重刷期权挂 P40 变体②…**非 P81 辖域——P81 限投资策略屏逐卡刷新**」）。decide_supply 的刷新判据是「无钻刷新找钻」（`cw_events.py:744-746`），decide_encounter 是全分支克制判定（`cw_events.py:657`），均与 P81 无关。无行为后果但属「依据标注」错挂，会误导后续读者以为两判据有数学证明护体。
- **建议修法**：改为「decide_encounter/decide_supply 的现行刷新建议判据（`cw_events.py` 各自分支）与 `refresh_used: bool` 参数签名不动」。

### F6 [建议] | landing.md 正本更新清单 | 「action_exec.md §2.2（固定等待族补给刷新 2s 登记）」节不存在——固定等待族在 action_ops.md §2.2

- **问题**：`flow/action_exec.md` 正文止于 §6，无 §2.2（其 §2.1「终结动作上报节点推进」存在且含补给确认行 ✓）；「固定等待族」正本 = `flow/action_ops.md` §2.2（现列刷新 1s=商店等，无补给刷新 2s 条目）。清单条目把登记目标挂错文件/节名，末阶段「清单清零」对照会落空。
- **建议修法**：改为「action_ops.md §2.2 固定等待族补补给/遭遇刷新 2s 登记（时序 #19/#23）」；action_exec.md 只保留 §2.1 补给确认行复核。

### F7 [建议] | landing.md 正本更新清单 | 漏 screens/README.md §6（终结语义总表）与 supply.md §6 chosen_supply 面

- **问题**：screens/README §6「单选族确认离开」行（:138）现文「补给节点无结算屏；**投资两屏** = 派发确认链即 round_success 终结交回」——本迭代后补给选卡分支同样变派发即终结（design §2.0B 画面op），该行必改，清单未列 §6。supply.md §6 的 chosen_supply 行（:67）同因 F3 需改而清单括号未含。
- **建议修法**：screens/README 条目补「§6 单选族确认离开行（补给改派发即终结）」；supply.md §6 括号补 chosen_supply 写端（随 F3 裁定）。

### F8 [建议] | design.md §1.1(3) | 对 fields.md §3.4.1 的写端申报引用不准确，且未申报「encounter_refresh_used 现役零写端」事实

- **问题**：design 称「`encounter_refresh_used`（**fields.md §3.4.1 写端申报 = on_outcome 发射型钩子**）」。fields.md §3.4.1 实文（:707-710）是「写端 = 动作 op 侧辖域…计数写端**接回后** = 单点 write_logic +1」；「on_outcome 发射型钩子」字样实际住在 `cw_game_state.py:2052` 注释与 `cw_projection_audit.py:169` 审计行。更实质的：全仓 grep 证实该字段**无任何落码写点**（仅开局种子 `_seed(...,0)` 与读闸），写端是纯申报态——与 strategy_refresh_used 退役时发现的「申报与零写端矛盾」同族。设计引用时未申报这一现状，§2.2 表也未出现写点行（正确），但 §1.1 的引用方式会让读者以为存在活钩子。
- **建议修法**：引用改为「申报写端 = on_outcome 发射型钩子（`cw_game_state.py` 字段注释/审计行在册；fields.md §3.4.1 申报为动作侧辖域；**现役零落码写点，恒种子 0**，实际防循环面 = per-visit 位」——顺带让「退役」的必要性论证更准。

### F9 [建议] | design.md §1.1(3) | 归档帧证据主张略超帧所证——「授予 >1 次即漏刷」是推论不是帧证

- **问题**：经视觉子代理直读复核，两帧内容与设计描述相符（`default.webp` 剩余次数 0、`双排装备.webp` 剩余次数 1，顶部节点条**均**「备战阶段 1-5」）——「次数为逐局授予的变量」有帧证。但帧只覆盖 0 与 1 两态，「存在授予 >1 次的局」无实证；「授予 >1 次即漏刷」是已用计数闸的逻辑推论。设计把两者并列为帧「证明」。
- **建议修法**：措辞拆开：「帧证 = 同节点跨局剩余 0/1 并存（逐局变量）；推论 = 授予 >1 次时已用计数闸漏刷（>1 授予的局待实证，不影响剩余语义修法成立——裁定 3 已独立成立）」。

### F10 [建议] | landing.md 首节 | 「§12 通用工程门」悬空标签——同族缺陷第五犯（内容已内联，唯 §12 指针无目标）

- **问题**：iteration-design.md 正文止于 §7（+附录），「§12」在全规范树无对应节；同族裁定史 = chain-observation attack F11、strategy-input-unification attack2 B2-10、takeover A9（均裁定须换可解析形态）。本篇首节已内联定义（「ruff 改动文件 + 直接受影响测试全绿」），可解析性优于前犯，但「§12」前缀仍不可解析，且定义未标源（先例形态 = 「源 = 项目 AGENTS.md『测试规范』『提交流程与协作边界』节」）。
- **建议修法**：删「§12」前缀，判据行改「通用工程门（本文首节定义）」，首节定义补源标注。

### F11 [建议] | design.md §1.3③ | 残留符号清理范围漏 telemetry/schema.py:529 的 `set_last_supply_pick` 陈旧引用

- **问题**：design §1.3③ 称两符号「现役不存在，全仓零写端」——经 grep 属实（无定义点），但陈旧引用不止 `cw_screen_supply_node.py` 模块头：`telemetry/schema.py:529` 注释「形状与 telemetry.state 暂存槽/set_last_supply_pick 一致」同引死符号。清理范围声明只含模块头，该处会继续留尸。
- **建议修法**：③清理面补「（另 telemetry/schema.py:529 注释同款引用顺手清）」或显式声明不辖。

### F12 [建议] | design.md §2.2 / landing 3.2 | sim 侧 `supply_refresh_left` 写模型欠定——「observe 写 left-1」无初始授予写

- **问题**：新字段「无种子 = None 未观察」；sim 引擎补给段现只写 used+1（`cw_sim_engine.py:623-634`）。迁移后「observe 写 left-1（≥0 截断）」在 left=None 时无定义（None-1），sim 需在补给节点入口先产初始 left（授予模型），设计未写。
- **建议修法**：§2.2 sim 行补「补给节点入口 observe 写初始 left（= 授予数，sim 世界真值；建议 1，与现 `used<1` 闸等价）」。

### F13 [建议] | design.md §2.0A | 「投资两屏现状即此形态」与在册例外②的细微出入

- **问题**：统一契约 A 写「访问内**零重读**」，而 op-layer §1.1 在册例外② = 投资环境刷新终结臂的刷后帧**留证重读**（零决策零判效，进缺陷台账）——投资环境现役并非绝对零重读。遭遇/补给按 A 落地不含留证读是合法的（例外②是「允许」非「必须」），但「现状即此形态」的等号不严格。
- **建议修法**：措辞改「投资两屏现状即此形态（投资环境另持例外②终结臂留证读，零决策零判效，不在本迭代复制）」。

### F14 [建议] | design.md §2.1（遭遇） | report 摄入 refresh_left 的「读缺跳写」与 options 早退闸的交互未写明

- **问题**：`report_screen_encounter_obs` 现结构 = options 空 → 整体 return（`encounter.py:57`）；invest_env 先例同款（names 空先 return，`invest_env.py:62-66`）。补摄入 refresh_left 后，「options 读缺但 refresh_left 读得」时 left 是否写未声明（按先例结构 = 不写）。
- **建议修法**：照先例声明「options 空早退整函数不写（含 left）」即可，一句话堵住实现分叉。

### F15 [建议] | design.md §1.1(1) | 禁止清单引用措辞——「验证是否成功」非 §1 清单原文条目

- **问题**：design 称踩 §1 禁止清单两条「『等下一轮看画面才补写』+『验证是否成功』」。action_ops §1 禁止清单四条中无「验证是否成功」字样（它在裁定正文与 §1.2/op-layer「验证不是生命周期段」）。「等下一轮看画面才补写」逐字在册 ✓。语义成立、引用不精确。
- **建议修法**：改「踩 §1 禁止清单『等下一轮看画面才补写』条 + §1 裁定正文『禁止做验证』（op-layer §1.1/§1.2 同款）」。

### F16 [建议] | landing.md 3.2/3.3 判据 | 「supply_refresh_used 全仓 grep 零命中」未显式带豁免口径（3.3 带了）

- **问题**：3.3 判据写「（验收锚 4 收口）」而验收锚 4 原文带「telemetry 历史数据只读注释除外」；3.2 判据自写了豁免；但 schema.py:646 只读注释豁免后，受影响测试（`test_cw_game_state_opening_seed.py:57,106-107` 等）改名/删行属正常翻新，grep 判据若含 sr-od-test 需与测试翻新同批成立——判据未声明 grep 范围（src + sr-od-test）。
- **建议修法**：3.2/3.3 判据统一声明「grep 范围 = src + sr-od-test；src 豁免 = telemetry 历史数据只读注释」。

## ③ 全量同步复查结果表

| 复查面 | 结果 |
|---|---|
| design 引用的正本节真实性 | op-layer §1.1/§1.2/§1.4/§2.1/§2.2/§3 ✓；action_ops §1/§2.2/§4.5/§4.6 ✓；fields §3.4.1–§3.4.4 ✓；supply.md/encounter.md §2–§9 ✓；screens/README §5.5/§6 ✓；**action_exec §2.2 ✗（F6）**；iteration-design §1.1/§5/§7 ✓ |
| 代码锚存在性 | cw_screen_supply_node（`_pending_supply`/`_apply_supply_landing`/`_read_refresh_anchor`/`_refresh_used`/`_do_action`）✓；cw_screen_encounter（`_decide_encounter_action`/`_try_refresh` 同访问重读+二次覆盖写+per-visit 位）✓ 与设计描述逐点吻合；pick_supply.py 两相+`EVIDENCE_OVERLAY_CLOSED` ✓；cw_overlay_pick_action PickSupply（0.6s/确认/到账登记/report_node_advance 现状点击即上报）✓；cw_screen_report/{supply_node,encounter,invest_env}.py ✓（supply obs 无 refresh_left=待加 ✓、encounter obs refresh_left 已存在且 report 不消费 ✓、invest_env 摄入先例 ✓）；cw_game_state（种子 :1776-1777、字段 :2052-2053/:2195、node_screen_refresh=2 :172）✓；cw_projection_audit :167/:170/:273 ✓；flow.py :497-526 / bridge.py :205-236（读源声明与实码一致）✓；sim :620-634 ✓；schema.py :646 ✓；cw_events decide_encounter/decide_supply 签名 `refresh_used: bool` ✓；cw_vocab CwActionPickSupplyParam 字段 **✗ 载体缺口（F2）** |
| §2.2 消费点迁移总表 vs 全仓 grep | 三退役符号（supply_refresh_used/encounter_refresh_used/encounter_refreshed_in_visit）src 侧消费点逐一比对：表覆盖全部（supply_node 读闸+写点/flow/sim/game_state 种子字段/audit/schema 注释；encounter 读闸/种子字段/audit；flow+bridge 旗标源/encounter 读写点/域版本注释）**无遗漏**；**漏 `picked['refreshed']` 值链（F4）**；sr-od-test 侧（step3/t60/opening_seed/obs_arch/route_clear）归「受影响测试」覆盖 ✓ |
| 判据同步（design §3 ↔ landing 各阶段） | 锚 1↔3.1 ✓（判据可执行性受 F1 拖累）；锚 2↔3.2 ✓；锚 3↔3.3 ✓；锚 4 拆 3.2/3.3 ✓（豁免口径 F16） |
| landing 文件面真实路径 | 全部实存（含 test_cw_supply_advance_wiring.py / test_cw_game_state_consume.py / test_cw_obs_arch_event_screens_step3.py）✓ |
| 正本更新清单条目 ↔ 实际致变正本节 | supply.md/encounter.md/README §5.5/action_ops §4.5/§4.6/fields ✓；**action_exec §2.2 错挂（F6）、screens/README §6 漏（F7）、op-layer §2.2 动作事实边界漏（F3）** |
| design↔README 状态 | design §0「草案」/ README「迭代设计:草案、设计对抗:未开始」一致 ✓ |

## ④ 试读结论（逐阶段）

- **3.1（补给选卡即时上报）**：**不可开工**。三处需实现者自行设计：①report 一口写的 legs ①② 输入载体（F2——param 无原始名/has_diamond，加什么字段、谁组装、`cw_vocab` docstring「原始名归 handler」约定如何改，全部空白）；②chosen_supply 进 report 与 op-layer §2.2 硬规则的关系未裁（F3）；③验收判据 grep 面不可满足（F1）。机械半（删证据闩/删 ConfirmSupply 边/派发即终结）语义完整可做。
- **3.2（补给刷新闸观察化）**：**基本可开工，两处欠定**。主体（obs 加字段/双出/闸换源/拒绝重调/烧旗标退役/域版本 2→3）语义选择在设计内全部有答案；欠定 = refreshed 遥测语义（F4，实为 3.1/3.2 交界——picked 快照在选卡分支组装但旗标在 3.2 删）与 sim 初始授予（F12）。
- **3.3（遭遇刷新链终结化）**：**可开工**。终结化路径、left 摄入、per-visit 位退役、flow/bridge 换源、「不动面」（重入裁决/chosen_encounter）边界清晰，拒绝分支经 `refresh_used` 形参重调的机制现成（`_decide_encounter_action` 防御分支先例在码）。仅 F14 一句话级补充。

## ⑤ 零发现面声明（查过无问题的面，防重复攻击）

1. **现状症状描述（§1.1）与代码逐点吻合**：supply 两相上报、encounter 访问内 `self.screenshot()` 重读+二次覆盖写+重决策+per-visit 位、supply 已按 ADR-0517 终结化——全部与实码一致。
2. **两条全域规范的存在性与文本**（op-layer §1.4「刷新 = 终结」「刷新闸 = 剩余语义观察真值」、action_ops §1 增补 2）引用属实，且均已在正本在册（含「迁移归本迭代」的欠账标注互指一致）。
3. **归档帧内容**：经视觉直读证实 default.webp=剩余 0、双排装备.webp=剩余 1、同「备战阶段 1-5」（帧本身无可攻击处；仅 F9 的推论措辞）。
4. **建档 rect**：`currency_war_supply.yml`「文本-剩余次数」pc_rect = (1347,969)-(1484,997) 与设计引用逐位一致。
5. **§2.2 表对三退役符号的 src 消费点完备性**（除 F4 值链外零遗漏）；`EVIDENCE_OVERLAY_CLOSED`/`ConfirmSupply` 的 supply 链消费点枚举完备（pick_supply 定义、supply_node 导入、pick op 到账登记、exec_state/_overlay_confirm 分支、t60 测试）。
6. **活锁方向安全性论证（§2.0A）**：放行→终结 / 拒绝→重调选卡两分支均终结访问或落选卡，与「循环无上限规范 + 恒可用终结不变量」（op-layer §1.1/§1.4）自洽；拒绝重调的防再建议机制经 `refresh_used` 形参天然成立（实码先例 `cw_events.decide_supply` rule 3）。
7. **kernel 签名不动取舍**：decide_encounter/decide_supply 的 `refresh_used` 形参与消费实码核实；bridge 侧走 `cw_encounter_selection.decide_encounter`（同形参）——「只换上游闸数据源」可行。
8. **域版本取舍**：node_screen_refresh 现 2、bump 3 合规；encounter/supply payload 域形状不动、不 bump 的论证与 fields §2.2/§3.7 一致。
9. **landing 阶段依赖**：3.2 依赖 3.1（同文件防冲突）、3.3 依赖 3.2（共享 game_state/audit/域版本）挂对，无环、无跨阶段拆同一符号迁移（supply_refresh_left 全链在 3.2、encounter 链在 3.3）。
10. **边界完整性（攻击项 1）**：§1.3「明确不解决」四项（PickPlanner/PickEquip、投资两屏、判据本身、迭代边界判据引用）与 §2/landing 实际触碰面一致，未见 §1.3 之外的漏 declared 面——F3/F4 属「解决面内的欠定」而非越界。
11. **文档形式面**：三文档构成齐、阶段七件齐、无过程叙事/进度标记混入正文、README 只放索引与进度、无行号锚（全部符号级/节级引用）。

（报告完；F1–F4 为定稿前必改项，其余建议级可随修订顺手收敛。）
