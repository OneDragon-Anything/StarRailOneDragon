# 核一·无前提攻击报告（第 2 轮）

- 攻击对象：`changes/2026-09-21-pick-planner-equip-immediate-report/` design.md + landing.md 现稿（README 仅上下文；attack.md = 第 1 轮历史工件，只用于核对上轮发现是否真清偿，不锚定其结论）
- 规范出处：docs/develop/harness/iteration-design.md §7 核一 + §5 卡点
- 方法：自行 read/grep 核证据；代码实况以 `src/sr_od/application/currency_war/` 与 `sr-od-test/` 现盘（含未提交工作区改动）为准；正本以 flow/action_ops.md、flow/action_exec.md、screens/op-layer.md、screens/*、game_state/* 现盘为准。

## ① 总判

**需修订后定稿**。发现 7 条：**阻塞 2**（F1 正本清单漏 `flow/action_exec.md`；F2 planner.md 条目节列举错位漏实际表述位）+ 建议 5（F3–F7）。第 1 轮 7 条发现全部真清偿（F1–F6 修订逐点核对成立，F7 升格为 §2.3 协调申报）；本轮新增问题**全部集中在正本更新清单与现状事实句层**，方案本体（单相化契约/换源/退役面/时序等价论证）与权威源逐点吻合，零方案级推翻。3.1/3.2 实现 worker 凭现稿可开工（F4 需一句口径补写）；**末阶段正本更新批凭现稿不可开工**（F1/F2 使「清单清零；正本与实现一致」判据不可达）。

## ② 逐条发现

### F1 [阻塞] 正本更新清单漏 `flow/action_exec.md` §2 pick 族段——「其余屏(策划/补给/装备)= 分步形态欠账…欠账标注见 action_ops.md §4.5」在本批后双重失真，且兜底 grep 两段都抓不到

- **对象位置**：landing.md「正本更新清单」（:42-48，无 action_exec.md 条目）；design.md §1.3「全域清零」主张。
- **问题**：`flow/action_exec.md` :24 现文：「其余屏(策划/补给/装备)= 分步形态欠账(发射相意图遥测零写,落地相 = 画面 op 重入裁决出口持证据调用;迁移归后续批,欠账标注见 action_ops.md §4.5)」。本批落地后该句三重失真：①策划/装备已迁即时上报（补给更是 T-1 后即已失真——本句是承袭的存量过期，本批「全域清零」主张使其必须收口）；②「欠账标注见 action_ops.md §4.5」在欠账段整段摘除后成**悬空引用**；③该句无 `EVIDENCE_OVERLAY_CLOSED` 字面量、也不在 action_ops.md §4.5——兜底 grep 的两段（常量全域 + 「两相/落地相/发射相」在 action_ops §4.5）**均不覆盖此文件**，漏项不可由兜底检出。action_ops.md 自身 (:3) 声明「action_exec.md §2 只留指针与执行面契约表」——该指针段正是 pick 族上报形态的第二个正本落点，清单漏列 = 「正本与实现一致」判据不可达。与第 1 轮 F1（清单漏文件）同类，本批修订后重犯于另一文件。
- **权威源证据**：flow/action_exec.md :24 全文如上；landing.md 清单 :42-48 逐条核对无该文件；action_ops.md :3 反向规格化声明。
- **建议修法**：清单补条目「`flow/action_exec.md`：§2 pick 族段「其余屏(策划/补给/装备)= 分步形态欠账…」句改写为全族即时上报 + 清欠账段引用（补给字样系 T-1 遗留，一并收口）← 3.1/3.2」；或把兜底第二段口径从「在 action_ops §4.5」扩为「在 flow/action_ops.md §4.5 与 flow/action_exec.md §2」。

### F2 [阻塞] planner.md 条目节列举错位：「§1/§4/§5」中 §1 无两相表述可清，实际表述还住在 §2（:12 形态声明）、§6（:55 落地相容器写）与开放设计注（:76）——后两处半数不被兜底覆盖

- **对象位置**：landing.md :45「`screens/planner.md`：§1/§4/§5 全篇两相+重入裁决表述清除（单相化改写）」。
- **问题**：逐节核对 planner.md 现盘：§1（分发判定，:5-8）**零两相/重入表述**（列为清除对象 = 空动作指令）；实际两相/重入裁决表述分布 = §2 :12（「决策动作 node = 顶部重入出口门…`round_wait` 循环推进」——无常量字面量）、§4 :24/:29-38（对照表 + 节点序列，含 `EVIDENCE_OVERLAY_CLOSED`）、§5 :48-49（终结表两行重入出口门行，无常量）、§6 :55（「落地相容器写…evidence=`EVIDENCE_OVERLAY_CLOSED`」）、开放设计注 :76（「落地相写的是分支效果域」）。「§1/§4/§5」按字面执行漏 §2、§6 后半句与 :76；兜底 grep 只能抓到含常量字面量的 :24/:55，**§2 :12 与 :76 的重入裁决/落地相表述永不清除**。这与第 1 轮 F2（条目指向与实际表述位错位，判阻塞）同错误形态第 2 次出现——修法只把文件名改对了，节列举仍与实况不符。「全篇」二字若解读为「整篇」则与「§1/§4/§5」限定自相矛盾，worker 无从裁定口径。
- **权威源证据**：planner.md 现盘 :5-8 / :12 / :24 / :29-38 / :48-49 / :55 / :76（本次逐行核）。
- **建议修法**：条目改为「`screens/planner.md`：全篇单相化改写——§2 形态声明/§4 对照表与节点序列/§5 终结表/§6 状态上报面/开放设计注的两相、重入出口门、落地相表述清除」；或去掉节列举直接写「全篇」，并删去「§1」。

### F3 [建议] op-layer 清单条目不完备（第 1 轮 F3 部分清偿）：漏 §1.1 :33 已迁枚举句、§3 :96 欠账引用句（摘除后悬空）；「节点循环行注」对分型判据失配不充分

- **对象位置**：landing.md :43「`screens/op-layer.md`：§1.2 欠账引用句更新（两相欠账清零）、§3 节点循环行注（yinlang/equip_pick 重入裁决退役改派发即终结）」。
- **问题**：三处。①§1.1 :33 现文「**投资两屏/补给/遭遇**已迁即时上报 + 派发即终结形态…零重入裁决」——枚举句未含策划/装备，不在条目内；②§3 :96 括注「其余屏现状见 action_ops.md §4.5 欠账标注」——§4.5 欠账段整段摘除后为悬空引用，条目未列；③§3 :88「节点循环」型判据 = 「决策动作 node = 零参决策 + 选卡确认链派发…`round_wait` 循环」——两屏迁移后 act = 派发 → `round_success` 终结，**不再满足本型判据**，涉及两屏是否挪型（对照全形态行 CwScreenEncounter「选卡派发即终结」先例）、:88「8 屏全设」计数与 :94「合计…=36」联动改写——「行注」二字覆盖不了这个改动深度，worker 须自行设计分型迁移。第 1 轮 F3 的幻影行已修（行注对象 :88 实存），但枚举句/悬空引用/分型判据三面仍缺。
- **权威源证据**：op-layer.md :33 / :88 / :94 / :96 现文（本次逐行核）；landing :43。
- **建议修法**：条目扩为「§1.1 已迁枚举句（:33）扩含策划/装备；§1.2（:43）与 §3 注（:96）欠账引用句清零；§3 节点循环行（:88）两屏挪型或行注改派发即终结 + 计数句（:88/:94）联动」。若「正本与实现一致」按严格口径判，本条升级为阻塞。

### F4 [建议] §2.3 并行协调申报的事实句「现盘 pick_planner.py 尚无该代码」与工作区实况不符：joy rider 已作为未提交改动在盘（+63 行），且效果分支清单/验收锚 2 均未列 rider

- **对象位置**：design.md :66（取舍 5）；§2.1 :44（落地效果分支逐位保持清单）；§3 验收锚 2；landing.md 3.2 范围。
- **问题**：git 实况：`pick_planner.py` 相对 HEAD 有 **+63/-9 未提交改动**（`_grant_joy_conditional` rider + `rng` 形参 + 落地相内分支类型分派前执行，另 `cw_events.py`/`cw_gain_chain.py`/`cw_overlay_pick_action.py` 同批未提交）——joy-conditional-leg 批已开始落码（第 1 轮 F7 核的「现盘无 joy 符号」已过时）。设计三处未跟上：①事实句「现盘尚无该代码」按现盘为假；②§2.1「落地效果分支逐位保持」清单只列 equip/upgrade/unknown/weaken 四条分支，**未列分支类型分派之前的条件分支 rider**；③验收锚 2 与 landing 3.2 行为测试同样无 rider 面。3.2 worker 在现盘执行「删 evidence 参数、一口写」时必然撞上 `_grant_joy_conditional` 与 `rng` 形参的去留拍板——按「rider 随单相调用点重挂」可**推出**保留，但这是推理不是声明；行为测试若不含 rider 面，「发射时点零授予」类回归（joy 批语义）无人校验。按任务边界 joy 批非攻击对象，如实记录现状：协调申报的方向（重挂单相调用点）成立，缺的是对「已在盘」的事实修正与一句去留口径。
- **权威源证据**：`git diff HEAD --stat` pick_planner.py +63/-9；pick_planner.py 现盘 :94（`_grant_joy_conditional(gs, sig, rng)` 于落地相、分支类型分派前）与 :107-142 定义体；design :44/:66/:71；landing :20/:26。
- **建议修法**：design :66 事实句改「现盘已有该批未提交落码（+63 行）」；§2.1 或 landing 3.2 补一句「分支类型分派前的欢愉条件分支 rider（含 `rng` 形参）随单相化保留在 report 体内、触发时点随调用点前移，行为测试口径与 joy 批对齐」。

### F5 [建议] 「weaken 零写」分支描述与实码不符：weaken 不是独立零写分支，它落 unknown 分支且**有留证**；真正的零写分支是 unrouted 兜底，设计全文未提

- **对象位置**：design.md :13（§1.1「unknown 留证 / weaken 零写」）、:44（§2.1 同款）、:71（验收锚 2 同款）；landing.md :20/:26（「⓪unknown/weaken 留证/零写分支」）。
- **问题**：`pick_planner.py` 现盘分支分派 = equip / upgrade / unknown / 兜底四支：weaken 卡文（含弱化词且装备锚未命中）**落 unknown 支**，走 `_emit_defect(kind='planner_leg_unknown')` 留证（cw_events.py :901-902 docstring 明证「含弱化词且装备锚未命中的卡文落 unknown——静默零记账变响亮申报」）；无任何独立 weaken 分支。真正的「零写不留证」= 未路由分支类型兜底 `unrouted_leg_zero_write`（:104），设计全文未列。「unknown 留证 / weaken 零写」的对仗写法暗示 weaken 分支零留证——失实；landing 的「unknown/weaken 留证/零写」交叉表述含混。行为不受影响（worker 保函数体即保行为），但「逐位保持」的清单本身不逐位。
- **权威源证据**：pick_planner.py :95-104（四支分派现码）；cw_events.py :900-902（分支类型词表注释）。
- **建议修法**：三处 + landing 改为「unknown 留证（含弱化词卡文）/ 未路由分支类型兜底零写」；或按正本 planner.md :55「unknown·weaken 零记账」口径统一为「零记账 + unknown 留证」。

### F6 [建议] `cw_overlay_pick_action.py` 模块头 docstring（:20-24）自述 pick_equip/pick_planner 分步例外——本批后失真；landing 文件面「仅 Op 体」限定把它排除在外，验收锚 3 的 grep 抓不到

- **对象位置**：cw_overlay_pick_action.py :15-24 模块头（「银狼闭环迭代起三线例外:pick_invest / pick_equip / pick_supply = 分步实现(发射相仅意图遥测,落地相在画面 op 重入裁决出口…);pick_planner 发射相 = 意图遥测…效果分支同候证据闩」）；landing :10/:22 文件面「（仅 CwActionPickEquipOp 体）/（仅 CwActionPickPlannerOp 体）」。
- **问题**：本批把 pick_equip/pick_planner 改单相后，该模块头「分步例外」自述失真（且 pick_invest/pick_supply 两名早因前批迁移已失真——T-1 未清此头，属承袭欠账；本批是第三个也是最后一个例外名清偿点，「全域清零」口径下应顺手收口）。「仅 Op 体」的文件面限定使模块头不在改动面；验收锚 3 只 grep 常量名，模块头无常量字面量 → 三重漏网。违项目注释规范（docstring 与实现一致）。
- **权威源证据**：cw_overlay_pick_action.py :15-24 现盘；landing :10/:22。
- **建议修法**：landing 3.1/3.2 文件面各加「模块头两相例外自述句随批清偿（含 pick_invest/pick_supply 遗留名）」，或单列一条注释连带。

### F7 [建议·微] §2.2 表 equip 行测试改写措辞「确认点击后容器即持效果」与 equip 机械链不符（点卡即选无确认步）；另 cw_vocab :733 供给行 `normalize_equip_name` 注释为 T-1 遗留过期，本批可顺手

- **对象位置**：design.md :52（表行 1 迁移列）；cw_vocab.py :733。
- **问题**：①equip 屏「本屏点卡即选、无确认步」是 design §2.1 自己声明的，同文档 :52 却写「测试改断言『**确认点击后**容器即持效果』」——措辞自相矛盾（应「点卡后」），测试重写者可能照抄造出错误断言描述；②cw_vocab :733 `CwActionPickSupplyParam.norm_item` 注释仍写归一器 = `normalize_equip_name`，而供给组装点 T-1 已换 `normalize_registry_equip_name`（cw_screen_supply_node.py :304 现盘）——T-1 遗留过期注释，本批做同族连带（:908）时可顺手，不属义务。
- **权威源证据**：design :39 vs :52；cw_vocab :730-736；cw_screen_supply_node.py :300-304。
- **建议修法**：:52 改「点卡后容器即持效果」；landing 3.1 连带句加「（:733 供给行同款过期注释顺手复核）」。

## ③ 全量同步复查结果表

| 复查面 | 结果 |
|---|---|
| 第 1 轮发现清偿核对 | F1 ✓（锚 3/兜底口径收窄为 src+sr-od-test+docs 正本、豁免 changes/，清单补两文件）；F2 ✓（yinlang.md 幻影条目改 planner.md 实名）；F3 部分（幻影行已修，枚举句/悬空引用/分型判据仍缺 = 本轮 F3）；F4 ✓（「两处自持」）；F5 ✓（cw_vocab :908 连带已入 design/landing）；F6 ✓（修正论据「零枚 → planner_upgrade_source_missing 留证零写、档不 +1 两次」与 `_apply_upgrade_transform` :232-237 实码逐字一致）；F7 ✓（升格 §2.3 协调申报，但事实句过时 = 本轮 F4） |
| design §1 ↔ §2 ↔ landing 三阶段边界 | 覆盖无遗漏无越界（3.1 = equip 全件、3.2 = planner 全件、末阶段 = 正本）；例外 = F1（action_exec 漏列）、F2（planner.md 节错位）、F6（模块头连带未申报）；§1.3「明确不解决」之外无未申报面（joy rider 时点已入 §2.3 申报，F4 仅事实句过时） |
| 引用锚存在性 | `CwActionPickPlannerOp.run`/`CwActionPickEquipOp.run`/`pick_planner.py`/`pick_equip.py`/`cw_screen_yinlang.py`(:204-222/:255-256)/`cw_screen_equip_pick.py`(:125-138/:180)/`classify_planner_branch`(cw_events :994)/`normalize_equip_name`(:930)/`normalize_registry_equip_name`(:951,158 键)/`emit_overlay_confirm`/`CwActionPickEquipParam.norm_item`(cw_vocab :908 注释实存)/`_apply_upgrade_transform`(:172)/`EQUIPMENT_ROSTER` 全部实存且语义相符 ✓；docstring 引证「未锁态语义（仅泛用分支）」cw_screen_equip_pick :156-157 在册 ✓；例外 = F4（joy rider 在盘事实）、F5（weaken 分支描述） |
| 消费点迁移总表 vs 全仓 grep（自行复核） | `EVIDENCE_OVERLAY_CLOSED` src 恰 4 文件（pick_planner :63 定义+:12/:74/:86、pick_equip :40 定义+:9/:48/:55、yinlang :49/:220、equip_pick :44/:137）✓；t60 EQUIP_EVIDENCE 面（import :40 + :127/:218）✓；yinlang_phase32 恰 11 处（import :55 + 10 调用，「10+ 处」✓）；`_pick_pending`/`_pending_pick` equip_pick 本文件（:74/:79/:125-129/:169/:180）✓；`_confirm_pending`/`_pending_leg`/`_pick_param` yinlang 本文件 + planner op 置位 :408 ✓（partner :355/fortune :151/wish_trial/expert_invite/bookcard/deploy_not_full 同名属彼屏，表已限定，无过度）；`normalize_equip_name` 消费面 = equip_pick 组装点（:47/:168）+ cw_events 本体 + cw_vocab 注释两处（:733/:908），本体与银狼域不动 ✓。**src+test 口径无遗漏无过度**；docs 正本缺口归 F1/F2（+ action_ops §1 :22 「现役 pick_invest」例句为承袭过期，量级注记） |
| 判据可满足性 | 验收锚 3 / 兜底 grep 口径（src + sr-od-test + docs 正本；豁免 changes/）修订后**可满足** ✓——正本区现存常量命中 = planner.md :24/:55 与 logic-updates/pick-planner.md :14/:37，均在清单内；例外 = F1（action_exec 表述不在任何 grep 面内） |
| 增补 2/3 与 op-layer §1.2 合规 | 「单相重复应用不设防」与 §1 :25 判重禁令原文兼容（真报两次 = bug 域）✓；修正后 upgrade 重复应用论据与实码一致（count==0 → planner_upgrade_source_missing，:232-237，档不动）✓；增补 3 零新增读屏成立（emit_overlay_confirm 机械确认 + 固定等待零读屏，action_ops §2.3 :59 在册；equip 定位 env 传入）✓ |
| 并行批现状（如实记录，非攻击对象） | 工作区未提交改动 = joy-conditional-leg 批（pick_planner/cw_events/cw_gain_chain/cw_overlay_pick_action + tool-gain-report README/flow README/op-layer.md）；shop-refresh-terminal 目录在飞。op-layer.md 本身已有未提交改动 = 末阶段正本 worker 将在脏文件上操作；3.1↔3.2 串行申报不覆盖与 joy 批的共享文件（cw_overlay_pick_action.py 双批在飞）——协调面已在 §2.3 申报 rider 落点，共享文件的批间串行未申报（注记级） |

## ④ 试读结论（逐阶段）

- **3.1（equip）实现 worker**：**可开工**。单相 report 改法、换源入口（`normalize_registry_equip_name` 现盘 :951，分层语义与 design 引用一致）、删闩删出口门、行为测试三型（命中/未解析/泛用件）、grep 判据均可直接落码；卡点仅 F7① 措辞与 F6（模块头是否顺手，无申报需自拍板）。
- **3.2（planner）实现 worker**：**可开工（附一句口径待补）**。时序等价论证成立（两时点间容器零写入——round_wait 轮 OCR 重入检查非容器写端；report_screen_planner_obs 派发前写完；单线程无并发写端）；唯一实拍板点 = F4：现盘函数体已含 `_grant_joy_conditional`+`rng`（joy 批未提交落码），设计的分支清单与行为测试均未列，worker 需按 §2.3 协调句**推理**出「保留在单相体内」——补一句声明即消。
- **末阶段正本更新批 worker**：**不可开工**。F1（action_exec.md 漏列且兜底双不覆盖）、F2（planner.md 节列举与实况错位，§2/:76 永不清）使「清单清零；正本与实现一致」不可达；F3（op-layer 枚举句/悬空引用/分型判据）按严格口径同判。先修清单再排批。

## ⑤ 零发现面声明

以下面逐项攻击后**零实质发现**（证据见 ③ 表）：方案层单相化契约本体（§2.0 三条）；两屏拆两阶段取舍与共享文件串行依赖；equip 归一升级主张（泛用件在注册表 158 键集、银狼 10 件锚对泛用件恒 ''、fail-closed 同构供给行——cw_events :930-991 现码逐点支持）；upgrade 分支三态+档行逐位保持与时序等价论证；`classify_planner_branch` 不动边界的定性（分支类型分类器副产品非入栏归一器，与代码注释 :893-898 相符）；planner 载荷 env kwargs 不迁 param取舍；零写族 pick 屏不迁移边界（op-layer §2.2 现行合法形态）；src+test 消费点完备性与测试计数；验收锚 3 修订后判据可满足性；增补 2 第 4 条/增补 3 逐条合规；第 1 轮 F1-F6 修订真实落地。
