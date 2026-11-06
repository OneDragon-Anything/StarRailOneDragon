# hp-purge-refresh-reform 第 7 轮定点复查报告

- 复查人：干净上下文定点复查者（只带主轴清单与判据源，未读 attack-r1~r6；检索意外命中禁读件内容未引用、未跟进）
- 复查日期：2026-10-28
- 复查性质：第 6 轮结论「按清单修复 + 同类泛化排查后做一轮定点复查即可收敛」的执行轮——主轴 = ①第六轮修复面验证（修订到位性 + 新漂移）；②两类失误（并发编辑回退 / 过程叙事）的全篇同类排查
- 结论：**11 条发现（高 0 / 中 4 / 低 7）**。四条主轴核心全部验证通过（R-3 终选口径四处同口径、测试锚六文件精确、词表互斥完备、扫描口径一致、两类泛化排查仅剩 1 处过程叙事残留），发现集中在**行级文件面五处同步缺口**与**措辞/覆盖精度**，无行为方案级问题、无裁定违反。

## 一、发现清单

### F1【中】shop.py 行段三分五处不一致（文件面互斥契约分裂）

- 位置：总纲 `design.md:46`（权威口径）vs `details/refresh-chain.md:5`（边界）与 `:21`（合成腿重写落点）vs `details/shop-buy-reform.md:5`（边界）vs `landing.md:43`（3.2 文件面）与 `landing.md:57`（3.3 文件面）。
- 口径对照（总纲 §2.1 = `:1-233` 头部与 ρ 别名 / `:234-266` _merge_pair_names → shop-buy-reform / `:267-315` p92_seat_recoverable 删除段 → refresh-chain / `:316-1961` 买面 → shop-buy-reform / `:1962-2080` 刷新发射收工 → refresh-chain；直调核实：shop.py 实测 2080 行，`_r2_card_reserve`:221、`_merge_pair_names`:234-264、`p92_seat_recoverable`:267-315、买面 `:316` 起、发射段 :1962-2080——总纲口径与函数边界逐位吻合）：
  - refresh-chain.md:5 声称本篇管「`shop.py` …（:1-315，含 ρ 别名、合成腿谓词段 :234-264、p92_seat_recoverable 删除段 :267-315）」——把总纲划给 shop-buy-reform 的 :234-266 整段并入本篇；:21 进一步写「实现 = 合成腿谓词按机制全集在该段重写（refresh-chain 文件面）」，与总纲行段归属正面冲突；
  - shop-buy-reform.md:5 声称买面段「≈L250-1961」——缺总纲划入的 :234-249（谓词段前半），又含总纲划给 refresh-chain 的 :267-315；
  - landing.md:43（3.2）写 `shop.py:1-249`（头部与 ρ 别名）+ `shop.py:267`（单行符号删除）——:249 无函数边界意义（:250 落在 `_merge_pair_names` 函数体内），p92 段只认领 :267 单行、:268-315 函数体落入 3.3 的 :250-1961；
  - landing.md:57（3.3）写 `shop.py:250-1961`——与总纲的 `:234-266` + `:316-1961` 两段口径均不合。
- 后果：总纲 §2.1 明言「各详设不得触碰对方文件面」；照 landing 立阶段任务会把错误文件面写进账本，落地批按任一详设边界动工即跨面误触（最实际的一条：refresh-chain 按 :1-315 重写 `_merge_pair_names` = 侵入 shop-buy-reform 行段）。
- 修正方向：四处统一为总纲 §2.1 口径——refresh-chain 边界改「:1-233 + :267-315 + :1962-2080」，合成腿谓词重写落点二选一并五处同步（a：重写归 shop-buy-reform 段内执行、refresh-chain 只消费；b：总纲 §2.1 把 :234-266 改判 refresh-chain，shop-buy-reform 只消费）；landing 3.2 改「:1-233 + :267-315 + :1962-2080」、3.3 改「:234-266 + :316-1961」；shop-buy-reform 边界同改。规范出处 = iteration-design §5 硬规则 4（修订后 design↔landing↔README 全量反查）。

### F2【中】hp-purge §3「两消费位等值锁」与总纲 carve-out 契约正面冲突（R-3 修复面内残留漂移）

- 位置：`details/hp-purge.md:33` vs `design.md:46`。
- hp-purge.md:33 称「`shop.py:373/:996` 消费行随新 H 输出值语义（…仅此两行归本篇 + 3.1 回归测试锁两消费位等值）」；总纲 §2.1 同两行的直调结论 = 「三行均无 H 值流（直调核验），处置 = 随删/注释申报，无『两消费位等值锁』义务」。本人独立直调复核：`:373` = docstring 内 `kernel.no_target_arms().hub_names` 文字引用（无值流）；`:996` = `shop_unbought_reasons(gs, k, obligation_members, [], hub_names=frozenset(), …)` 字面空集实参（无 H 值流）——总纲结论属实，hp-purge:33 的「消费行随新 H 输出值语义」不成立，且其加派的「3.1 回归测试锁两消费位等值」义务与总纲明文的「无义务」相抵（同篇 hp-purge:5 也自认「唯 carve-out 三行」）。
- 后果：实现者按 hp-purge 会写一个无语义的等值锁测试（锁两行无值流行为）或与总纲冲突；属并发编辑回退类残留（总纲拿到了直调修正、详设同段未跟上）。
- 修正方向：hp-purge §3 删除面补全句改为总纲口径（随删/注释申报，无「两消费位等值锁」义务），删「消费行随新 H 输出值语义」与「3.1 回归测试锁两消费位等值」两处短语。

### F3【中】landing 3.1 收编了申报「本批零触碰」的 cw_first_passage.py，且引用总纲不存在的收编

- 位置：`landing.md:29`（3.1 文件面「`cw_first_passage.py`（B 组触碰面，总纲 §2.1 收编）」）vs `details/hp-purge.md:24`（R-6 例外：「`cw_first_passage.py` 本体保留…本批零触碰、不在词表」）vs `design.md:47`（hp-purge 独占清单未列该文件）。
- 直调：总纲 §2.1 hp-purge 独占清单（design.md:47）确实无 cw_first_passage.py；hp-purge §2 的 R-6 例外明写零触碰。landing 的「总纲 §2.1 收编」指向不存在的事实，且与零触碰申报相反。
- 修正方向：从 landing 3.1 文件面删去 `cw_first_passage.py` 条目（若落地确需触碰，则总纲 §2.1、hp-purge §2 两处同步改口径后保留）。

### F4【中】R-1/A-10 执行面缺 entry.py:844-846（快照单一源含它、设计文件面三处无授权）

- 位置：`details/hp-purge.md:19`（A-10 行锚仅 `criteria/levelup.py:385-392` + `cw_economy.py:792-882`）、`design.md:47`（hp-purge 独占清单与 B 组连带注释面均无 mandate_v1/entry.py）、`landing.md:29`（3.1 文件面同缺）vs 清查件 `.debug/temp/2026-10-28_hp逻辑清查.md` §3 R-1 行（A-10 面明列「+ entry.py:844-846 血本位凑金步」）。
- 直调：entry.py:844-846 = `_step3_level_up` docstring 血本位段（「…血闸过即发射…」）——R-1 删「血闸」hp 家族命名后该段措辞需同步；裁定载体执行纪律的宽词族亦含「血闸」。快照（hp-purge §7 执行单一源）含该段而设计文件面三处无授权 → 落地批撞无主文件或违规触碰。
- 修正方向：hp-purge §1 A-10 行锚补 `entry.py:844-846`（注释行），总纲 §2.1 hp-purge 文件面（B 组连带注释面同款点名）与 landing 3.1 文件面收编 mandate_v1/entry.py 该段。

### F5【低】refresh-chain §2 段标题「原解锁支撤稿」过程叙事残留（主轴 2b 唯一命中）

- 位置：`details/refresh-chain.md:44`（「资金序声明（升级推迟期；原解锁支撤稿）」）。
- 规范出处：iteration-design §5 硬规则 3——「不写…上稿改了什么」「『本轮/修订后/已改』类措辞即打回」；「撤稿」= 修订史措辞（段内正文「不设解锁支 + 饿死环推导」已自足，括注可删）。同族轻症：refresh-chain:44 / design.md:36 的「原 W2 动机…已消灭」为动机对照（W2 = 裁定载体持久条目号，合法指针），可留；refresh-chain:80「撤解锁支」为现选语义（关键取舍），合法。
- 修正方向：括注改纯语义（如「升级推迟期不设解锁支」）。

### F6【低】README refresh-chain 摘要为旧口径（与总纲 §0 文档清单不同口径）

- 位置：`README.md:7`（「刷新链三组件改革（金线公式/目标可买/死码清理/解锁支）」）vs `design.md:13`（「（金线公式/目标可买条件/判据族死码清理/危机不变式删除/资金序声明）」）。
- 「解锁支」作改革项列出与终态「不设解锁支（资金序声明）」相悖，且缺危机不变式删除。并发编辑回退类残留。
- 修正方向：README:7 与总纲 §0 同口径。

### F7【低】词表覆盖缺口两处（主轴 1d）

- ① `levelup_blood_gate_defer`：改名声明在（hp-purge §6 → `xp_batch_payment_defer`），但该符号不在 §6 清零词表，且无任何词表条目能子串命中它（现役 `criteria/levelup.py:314/:387` 两处直调确认）——改名漏改时残留扫描清零判据兜不住。修正：清零词表补该符号。
- ② `blood_xp_mode`：R-1 保留面符号（`cw_investments.py:1216` carve-out「改类条目」、levelup.py:389 现役消费），未列入「不过扫符号」声明清单——无误捕风险（无清零条目能命中），但保留面申报不完整。修正：不过扫清单补 `blood_xp_mode`。

### F8【低】refresh-chain §3 引用清理锚 `01_math_framework.md:84` 失真

- 位置：`details/refresh-chain.md:51`。
- 直调：01 号稿 P36/crisis 行实为 `:88`（支配性例外：危机帧刷新通道不变式 P36-a）与 `:119`（危机火力 P36-a/a′）；`:84` 为 R0 停止行（无危机内容，属 R 族清理面）。landing 正本更新清单写「P36…行删」与实际行位对应，唯 refresh-chain §3 的 ：84 指错，且真正的 P36 引用行（:88/:119）未列。
- 修正方向：`:84` 移归 R 族清理条目（或删），P36 引用清理改指 `01_math_framework.md:88/:119`。

### F9【低】hp-purge §2 R-6 段「λ 表血带维…随删孤儿化申报」表述失真（有误删歧义）

- 位置：`details/hp-purge.md:24`（「λ 表血带维参数实在 `lambda_death.py`（B-12）→ 随删孤儿化申报」）与 `design.md:72`（R-6 行「λ 表血带维随 hp 删除面孤儿化申报」）。
- 直调：血带维零变化——`hp_band`（lambda_death.py:121-130）由同文件 `make_key`（:142）现役消费（λ 表键维），`HP_BAND_NEAR_DEATH`（:36-37）由 predicates.py 濒死带谓词（:144/:176，R-7 保留面）消费，模块 docstring（:13）已申报「λ 表本体保留为 P51 标定工件」——既无删面也无新增孤儿。清查件 §3 R-6 的推荐 = 「保留为概率侧标定工件，但解除与决策面的全部接线」。「随删」二字可被读作删行（删血带维 = λ 键结构变更，恰是保留推荐反对的动作）。
- 修正方向：改「保留（概率侧标定工件，本批零触碰，与 cw_first_passage 同款；不新增孤儿——make_key/predicates 现役消费链不变）」。

### F10【低】末阶段宽词盘点口径三处表述不一，其一引用不存在的清查件 §5

- 位置：`details/hp-purge.md:52`（宽词族 = hp/血/危机/crisis）vs `landing.md:9`（各详设验收词并集 ∪ P92/R 族/危机词族）vs 裁定载体 `.debug/temp/2026-10-28_CW修复工作清单.md:27`（「危机带/血预算/血闸/…以 hp 清查件 §5 词表为准」）。
- 直调：清查件章节只有 §1-§4（聚合清单/分类明细/待裁决项/完整性自检），**无 §5**——载体引用的宽词单一源悬空。三处均为末阶段辅助盘点（非清零门槛，hp-purge §6 与 landing 同此定位），但落地批需要唯一口径。
- 修正方向：landing 与 hp-purge 统一为一个公式（建议 =「清查件 A/B/D 组锚符号 ∪ 各详设验收词并集 ∪ hp/血/危机/crisis 宽词族」，豁免清单随申报出具）；载体 §5 引用随快照义务在附录中勘误注记。

### F11【低】裁定载体未登记 R-1/R-3 裁决结果（溯源断链，不阻断落地）

- 位置：`.debug/temp/2026-10-28_CW修复工作清单.md:117-125`（裁决队列仍为「W1 动工前须闭合/R-1/R-3 待裁决」原貌）。
- 载体自述「本清单此后为裁定与挂账台账」；R-1/R-3 已裁决事实现仅存于设计四处（design §0:10/§3、hp-purge §3、landing:28/:30，四处彼此一致）。清查件 §3 R-3 的两难原文（「删（+命题重锚排期）或暂留」）与终选「删血项、机制保留」的中间路径（实核后工程定夺）之间缺一环可溯源的用户裁决记录。
- 修正方向：载体裁决队列补两行闭合记录（或在 R-1/R-3 行内标注「已闭合 2026-10-28，见迭代 design §3」）。

## 二、实际复查过的面清单（直调核验通过面）

1. **主轴 1a：R-3 终选口径四处同口径 ✓**——hp-purge §1 表 A-11 行（:20「已裁决（R-3，删血项、机制保留）：H = 剩余节点数…细目见 §3」）/ hp-purge §3（:32 处置细目①-④）/ 总纲 design.md §3（:68 终选口径 + 行为变化）/ landing.md 3.1 范围与完成判据（:27/:33「A-11 删血项、机制保留，细目 = hp-purge §3 处置细目①-④」）与「验证与保全」表（:21「R-3 已裁删血项、机制保留…可行性与回退带不再随血低收紧」）——四处同一口径，行为变化申报三处一致。支撑锚全部直调属实：H 现式 `min(plane_left, ceil(hp/vd_p2_loss))`（cw_intention.py:1070/:1093）；`k_empty_window_fallback` 三生产消费位（shop.py:885 / entry.py:480 / decision_payload.py:101）；契约守卫面不读 H（contracts.py:88-106）与 `K_FALLBACK_SOURCE_THREE_ARM` 守卫（:100-106/:166-171）、P1 空窗职责（:138-142）；neardeath 死键仅注册行（cw_intention.py:1166，src 全仓唯一命中）；LOCK_PATH 键族测试侧零覆盖属实（测试仓无守卫测试文件）。唯 F2 为该修复面内残留漂移。
2. **主轴 1b：测试面锚 ✓**——六文件：`test_no_target_three_arms.py`（存在，实锁 P86 三分支与回退带：docstring 收编对照 + `test_k_empty_window_fallback_bands`:128）、`test_decision_payload.py`（:10/:158/:169 三处 `k_empty_window_fallback` 锚逐行精确）、`test_line_select.py`（:358-360 直调断言精确）、`test_seat_recoverable_narrow.py`（存在，实锁 `shop.p92_seat_recoverable` 收窄判定，改造指向正确）、`test_sim_levelup_cycle.py`（:44 = `_REFRESH_REJECT_KEYS` 键域清单，含 p92/must_spend 两键，精确）；`test_cw_interest_floor.py`——测试仓不存在（全仓零引用），且设计五文件**零点名**（上一轮死锚已正确摘除；shop.py:227 docstring 的同款死引用落在 3.2 ρ 重写段 :221-231 内随改消失）。归属全部正确（前三者归 3.1/R-3 面，后两者归 3.2/P92 面）。
3. **主轴 1c：shop.py 行段与 carve-out ✓（除 F1 的五处口径分裂外）**——全文件 2080 行；`:221` `_r2_card_reserve` 别名、`:234` `_merge_pair_names`、`:267-315` `p92_seat_recoverable`、`:316` 买面起、`:885` 序 1 名单回退、`:930` missing 名集、`:996` 字面空集调用、M6 `:1543-1616`、免费分支 `:1963-1971`、GATE_GOLD_SHORT 支 `:1988-1989`、P92 装配 `:1996-2054`、计数键 `:2062-2063`/`:2064-2065`（`must_spend_r1_budget_fail`:2067 在 r2 拒绝域保留，与设计一致）——设计行锚逐位命中；carve-out 三行 ：373（docstring 引用行）/:327（refresh_ev_budget 注释行）/:996（字面空集调用行）内容与总纲描述一致且确无 H 值流。
4. **主轴 1d：词表 ✓（除 F7 两缺口）**——清零词表 21 符号全部在 src 现役命中（k_alert:k700/form_floor:k268/:271/k_linear:k702/k_hp_calibration_grid:k699/:704/blood_margin_low_hp:k166/:706/:707 等逐个确认）；与不过扫 5 族（decision_hp/blood_xp_full_clicks/refresh_ev_budget/p1|p2_blood_floor/p2_handoff_*）无交集、无子串误捕；`levelup_blood_gate_defer→xp_batch_payment_defer` 改名声明在；3.1 全仓符号扫描口径（hp-purge §6）与 landing 常规检查（:9）一致。
5. **主轴 2a：并发编辑回退类 grep ✓（除 F1/F2/F3/F4/F6 已列）**——「整条退役」（现存 3 处均为放弃理由陈述：design:68/hp-purge:32/:62 关键取舍，合法）、「场上非线内件」（现存 2 处均为收窄申报与访问间隙处理：refresh-chain:24/:26；总纲 §2.0:33 与 landing:41 已是收窄口径——「可卖一件备战席燃料腾出位」）、「三布尔」（零残留，design:52 = 两布尔合取）、「解锁支放行」（现存为不设解锁支的 rationale，合法；README:7 摘要旧口径 = F6）、「G3 补全」「3.3 回归锁」「test_cw_lock_path_obs_keys」（五文件零残留）。
6. **主轴 2b：过程叙事类 grep ✓（除 F5）**——「对抗审 X-」「攻击 X」「attack-r」「已裁决前不动工」「曾两度反复」五文件零残留（hp-purge:5/:34 均为已裁决口径；hp-purge:62 备选放弃为合法关键取舍）；硬规则 3 卡点词（本轮/修订后/已改/第一版/回定/上稿/撤回）补扫仅命中 F5 一处；「对抗审中」为生命周期状态值（合法）。
7. **判据源直调**——iteration-design §5 硬规则 3/4 原文；裁定载体（7 条用户裁定、W2/W3/W4/W5/W10/W11 条目、裁决队列、执行顺序）；hp 清查件（§3 R-1/R-2~R-9 两难原文、A-11 行、B-4/B-9/B-11/B-12 行）；追查件与复盘件（三件均存在）；strategy-docs：11:58（[40]② 定性）/11:110（§3.1 P92）/11:186（批读数行，stay_gate 85/85、死时金≥50 15/15、终金中位 105 逐字吻合）、01:88/:119（P36 行，见 F8）/01:194（all_channel_exists 钩子行）、23:10（刷新放行条件行）、10:199（p44 历史注记）、20:77（r1_commitment_account）、19:29（r1_commitment_account）、14 N5 行（:162 起）、12 §1.4/§2、04 §6 第 1 项（L_c 口径差核对 = 「§6-1」锚实）、22/26/17/21/README/strategy-telemetry 存在、flow/ 与 game_state/ 四件在应用区根存在；proofs：math_proofs P21:45/P36:60/P40:64/P54:76/P86:106/P92:113 行全在、p36 单篇存在、出口生存:112/:238（P92 节）、p37:188（P36 同族）、p53-frame-horizon-vgap:12/:144（r1_commitment_account 残留）；边界事实两处：`changes/2026-10-18-levelup-band-gate/design.md:156`（攒金收敛声明域，逐字吻合）与 `changes/2026-10-28-supply-decision-wiring` 迭代存在；代码锚：refresh.py（:22/:97-108/:140/:160/:236/:282-378/:301）、contracts.py（:88-106/:100-106/:135-145/:166-171/:243-246/:252/:255/:261-267/:273/:279-282/:283-287/:288-291）、criteria/__init__.py（:54-55/:60/:62/:65/:71-73/:76）、levelup.py（:174/:193-194/:370-377 资格门④+`levelup_crisis_defer`:376/:385-392 门⑥血闸+`levelup_blood_gate_defer`:387/:484-514）、mandate.py（:4/:392/:963/:996/:1078-1079）、cw_discipline_rules.py（:82-128/:154-209/:212-260）、cw_economy.py（:792-882/:1074-1088/:1237-1287）、cw_comps.py（:37/:125/:2852-2859/:2862 起）、cw_performance.py（:107/:244-269）、cw_hp_policy.py:20、cw_game_state.py:2954、cw_investments.py（:473 高效决策 9999/:1216 blood_xp_mode）、economy_cycle.py（:12/:14/:24/:29-30/:177/:187/:233）、telemetry/schema.py（:460-465/:488-489/:500）、statefn/odds.py:67、mandate_state.py（:123-124 血预算拒付字段/:174 handoff hp 投影——landing 3.1/3.3 行级分工锚精确）、cw_registry（vd_p1_loss_intercept:314/vd_p1_loss_slope_rung:317/vd_p2_loss:357）、lambda_death.py（:13/:36-37/:121-130/:142）、cw_shop_odds.py（expected_refreshes/reencounter_window_frames/acquirability_factor 在）、research/merge_mechanics.md §2（连锁合成机制全集 = 合成腿口径依据，吻合）、research/economy.md 存在；criteria/shop_session.py 存在（landing 3.3 裸名可解析）；cw_decision_trace.py 存在（总纲 §2.1 B 组连带面点名成立）；sr-od-test E-7 漂移注记属实（operations/cw_op/test_settle.py 在、kernel/ 下无 test_settle）。

## 三、收敛判读

- 高严重度：0（连续第二轮）。中严重度 4 条全部为**行级文件面/契约同步缺口**（F1-F4），修正均为机械同步动作，无行为方案返工；低 7 条为措辞/覆盖/台账精度。
- 主轴结论：第 6 轮「定点复查即可收敛」的判断成立——修复面主体（R-3 四处口径、测试锚、词表、扫描口径、旧口径残留清零）全部到位；未收敛项集中在 design↔details↔landing 的行级全量反查未做完（F1-F4 即硬规则 4 的同类实证），建议本轮修复 F1-F5 后即可定稿（F6-F11 可随批顺带）。
