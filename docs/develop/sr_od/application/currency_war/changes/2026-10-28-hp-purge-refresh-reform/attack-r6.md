# hp-purge-refresh-reform 第 6 轮无前提对抗审查报告（终验轮）

- 审查日期：2026-10-28
- 审查者：干净上下文攻击者（无前轮报告接触；attack-r1~r5 未读）
- 对象：design.md + details/hp-purge.md + details/refresh-chain.md + details/shop-buy-reform.md + landing.md（README.md 作索引进度参考；hp-purge-appendix.md 未生成，不在对象内）
- 判据源：全部直调复核（iteration-design.md / strategy-docs 9 篇 / math_proofs.md + proofs/ / 现役代码 / 证据文件 3 份 / 裁定载体 / 测试面 / research / 边界事实 2 处）
- 结论：**发现 14 项**（高 3 / 中 6 / 低 5），集中于「五轮修订后的篇间漂移」与「验收判据可执行性」；未发现归层错误或治本性缺陷（核三主体通过）。

---

## 一、发现清单

### F1【高】残留清零词表与 R-1 保留面直接冲突——3.1 验收判据不可满足
- 位置：`details/hp-purge.md:50`（词表含 `decision_hp`、`blood_xp_full_clicks`）、`:26`（B-6 处置「decision_hp 随 A 组孤儿化删本体」）、`:33`（R-1「行为零变化；hp 不可信帧 fail-closed 语义保留」）、`:55`（「符号级残留清零 + 漏删申报零条 = 本篇完成必要条件」）
- 直调证据：
  - `kernel/cw_economy.py:881` = `blood_xp_gate(decision_hp(gs, session), hp_decision_trusted(gs), …)`——R-1 保留的「经验批支付门」现役唯一存活消费位就是 `decision_hp`；
  - `kernel/cw_economy.py:850` = `hp_trusted >= blood_xp_full_clicks(level) * cost`——「行为零变化」要求保留全量击数算术，`blood_xp_full_clicks` 不可删；
  - `kernel/cw_hp_policy.py:35`（decision_hp 定义）与 `:15-22` 消费同门申报纪律在 hp-purge 文件面内保留。
- 矛盾机制：词表把两符号列为「可清零口径——被删符号清单」，`:51` 的不过扫豁免清单（refresh_ev_budget / p1|p2_blood_floor / p2_handoff_*）未豁免它们。落地批执行只有三条路，全是死路：①删 `decision_hp` 本体 → 违反 R-1 行为零变化且 `cw_economy.py:881` 断链；②改名 → 设计未指定新名（拒因键有指定新名 `xp_batch_payment_defer` 的先例，函数族没有）；③如实漏删申报 → 违反「漏删申报零条」完成必要条件。`:26` 的 B-6「随 A 组孤儿化删本体」沿用清查件 B-6（**R-1 裁决前**写的「随 A 组孤儿化可删」口径），未与 R-1 已裁决保留对账。
- 修正方向：词表移除 `decision_hp`、`blood_xp_full_clicks`（或显式声明「改名 + 新名」）；`hp-purge.md:26` B-6 处置改为「本体保留（唯一消费 = R-1 经验批支付门），`cw_hp_policy.py:15-22` 消费同门纪律段随删面收窄复核」。

### F2【高】shop.py 行段三分契约四处口径互相矛盾（篇间漂移主证）
- 位置：`design.md:46` vs `details/refresh-chain.md:5`、`:21`、`:29` vs `landing.md:43`（3.2 文件面）、`:57`（3.3 文件面）
- 直调证据（真实函数边界）：`_r2_card_reserve` = shop.py:221-231；`_merge_pair_names` = **234-264**；`p92_seat_recoverable` = **267-315**；刷新发射段 = 1962-2080；全文件 2080 行 ✓。
- 三套矛盾口径：
  1. design.md:46：refresh-chain = `:1-233 + :267-315 + :1962-2080`；shop-buy-reform = `:234-266 + :316-1961`（合成腿谓词段归 shop-buy-reform）；
  2. refresh-chain.md:5：本篇 = `:1-315`（**含合成腿谓词段 :234-264**）；`:21` 更明言「实现 = 合成腿谓词按机制全集在该段重写（**refresh-chain 文件面**）」——与总纲 §2.1 文件面互斥契约直接冲突；
  3. landing 3.2 = `shop.py:1-249 + :267 + :1962-2080`、3.3 = `:250-1961`——249/250 分界与 design 的 233/234 不一致；3.3 的 `:250-1961` 还把 p92 函数体 `:268-315` 罩进买面段（3.2 只领了 `:267` 一行符号删除）。
- 后果：landing 是账本唯一源（iteration-design §3.1），照 landing 立任务即得互相重叠/遗漏的文件面；3.2 的合成腿谓词重写（判据组件必需件）在 design.md:46 下无授权段。
- 修正方向：按 refresh-chain 方案把谓词段 `:234-264` 改归 refresh-chain（判据面单一源在其侧），design.md:46 与 landing 3.2/3.3 行段全量同步；或保持 design 划分并改写 refresh-chain.md:5/:21——两说取一，禁四并存。

### F3【高】B 组连带悬空收编面（obs//operations//config/entry_policy/decision_trace/schema:460-465）未获总纲与 landing 文件面授权
- 位置：`details/hp-purge.md:27`（「点名收编进本篇文件面」≥13 处）vs `design.md:47`（hp-purge 独占清单）、`design.md:49`（行级分工）、`landing.md:29`（3.1 文件面）
- 直调证据：design.md:47 独占清单 = cw_discipline_rules / criteria/levelup / cw_economy / cw_intention / cw_comps / cw_performance / cw_registry / cw_hp_policy / cw_game_state / cw_vocab / mandate_state / statefn/predicates / audit/provisional / cw_first_passage——**不含** obs/、operations/、currency_war_config.py、cw_entry_policy.py（已确认存在）、cw_decision_trace.py（已确认存在）、telemetry/schema.py:460-465；landing 3.1 文件面对 telemetry/schema.py 只授 `:488-489`。而 `telemetry/schema.py:460-465`（sess_blood_budget_* 两字段及注释）经直调确认正是 B-14 连带悬空面。
- 后果：3.1 落地批按「文件面互斥契约」纪律无法触碰收编面，B-8/B-17/B-6/B-14 的「注释清零、逐处直调核验」完成判据不可执行。
- 修正方向：design.md §2.1 与 landing 3.1 文件面补授权（目录级 obs/、operations/ 或逐文件行级）。

### F4【中】R-3 的 shop.py carve-out 两锚性质误判，且总纲/详设处置相反
- 位置：`design.md:46`（「:996 为注释性引用（不消费 H 值）…无『两消费位等值锁』义务」）vs `details/hp-purge.md:35`（「shop.py:373/:996 消费行随新 H 输出值语义…3.1 回归测试锁两消费位等值」）
- 直调证据（与两篇说法都不符的真实形态）：
  - shop.py:373 = `shop_unbought_reasons` **docstring 行**（「入参 = kernel.no_target_arms().hub_names 直传」为文档叙述）；全 mandate_v1 无 no_target_arms 活调用（grep 仅 :373 注释 + contracts.py:150/:327 注释）；
  - shop.py:996 = **可执行调用行** `shop_unbought_reasons(gs, k, obligation_members, [], hub_names=frozenset(), …)`——传字面空集，H 变化对其零影响，但绝不是「注释」。
- 后果：实现者无所适从（总纲说无锁义务、详设说必须锁），且「锁两消费位等值」是给两处无 H 流代码定的无对象测试义务。
- 修正方向：按代码实况统一改写：`:373` = 注释随 H 语义更新申报；`:996` = 现役调用但传字面空集、无 H 消费 → 无等值锁义务；删除 hp-purge.md:35 的锁义务句。

### F5【中】R-3 契约守卫面（contracts.py:88-106/:166-171）四句两种结论
- 位置：`details/hp-purge.md:34`（②「契约守卫面…直调核验**不读 H**——**无需改码**」）vs `:35`（「删除/改口径面 = …contracts.py:88-106/:166-171 p2plus 支随新 H」）vs `design.md:49`（3.1 对 contracts.py 只授 `:243-246`，未授 :88-106/:166-171）vs `landing.md:29`（3.1 文件面授 `:88-106/:166-171`）
- 直调证据：contracts.py:88-106 = P86 带维扩展守卫（判 `k_target/k_fallback_*` 字段与 `K_FALLBACK_SOURCE_THREE_ARM` 常量），:166-171 = 同款 band token 判定——均不读 H；「p2plus」带内帧集随 H 变化属行为面非代码面。
- 后果：同一行段「改/不改」与「授权/未授权」篇间两说，落地批无法立判据。
- 修正方向：统一为「不读 H、无需改码，随行为变化申报」；landing 3.1 对该两段改标注为只读核对或移出文件面。

### F6【中】刷新负结果记忆的状态载体四处口径不一（实现者必撞的未决语义选择）
- 位置：`details/shop-buy-reform.md:5`（「载体 = StrategyState，mandate_state.py 新增字段行」）vs 同文件 `:30`（「会话状态载体 = 商店会话状态对象（shop_session）新增字段」）vs `design.md:48`（「shop_session.py 会话字段扩展」）vs `design.md:47`（mandate_state.py = hp-purge **独占**）vs `landing.md:57`（3.3 文件面 = mandate_state.py 新增行 + shop_session.py 访问计数消费）
- 直调证据：`criteria/shop_session.py`（406 行）为**函数模块**（金账锚定/访问判重/gold ledger），无字段载体形态；状态载体实际 = `mandate_state.py` StrategyState（:120-195 各字段）。shop-buy-reform.md 篇内 :5 与 :30 自相矛盾。
- 修正方向：统一为 mandate_state.py StrategyState 新增字段行（与 landing 3.3 及本篇 :5 一致）；design.md:47 mandate_state.py 独占改「行级分工（:123-124/:174 归 3.1，新增字段行归 3.3）」；design.md:48「shop_session.py 会话字段扩展」改为「mandate_state.py 新增字段行 + criteria/shop_session.py 访问计数消费」。

### F7【中】P92 / R 族文档面引用清理清单不完备——残留必然存活过迭代收尾
- 位置：`details/refresh-chain.md:30`（P92 删除面清单）、`:45`（R 族清理清单）、`landing.md:93-112`（正本更新清单）
- 直调证据（全 strategy-docs + proofs + flow + game_state 扫描，下列命中不在任何清理面/清单）：
  1. `proofs/出口生存余量设计批-命题与因果链.md:112`（「### P92(=v3 B1=C2 同构) 无命中期望付费刷新严格劣」整节）与 `:238`（P92 对照行）——清查件 D-24 对该文件只登记 :43/:49/:62（R5 行）；
  2. `r1_commitment_account` 残留三处：`strategy-docs/19_reinforce_channel_and_survival_discount.md:29`、`strategy-docs/20_large_balance_must_spend.md:77`、`proofs/p53-frame-horizon-vgap.md:12/:144`——清查件 D-9/D-10 的行锚均不含这些行，refresh-chain.md:45 R 族清单未列文档面；
  3. `strategy-docs/01_math_framework.md:84`（R0-1/R0-2 结构门叙述行，r0_stop 删除后过期）；
  4. `landing.md:103` 所列 `proofs/…p92…` 单篇文件**不存在**（proofs/ 目录实测无 p92-*.md；P92 正本在 math_proofs.md:113 与出口生存余量批）。
- 放大机制：landing 首节规定阶段扫描范围 = src/ + sr-od-test/，docs/ 归末阶段；末阶段宽词族（hp/血/危机）不含 `P92`/`r1_commitment_account` 词 → 上述文档残留无任何验收网兜住。
- 修正方向：P92 删除面补列出口生存余量批 :112/:238；R 族清理补列 19:29、20:77、p53:12/:144、01:84；landing:103 修正文件名（或删该枚举项并在 math_proofs 行处置中含 P92）。

### F8【中】总纲 §2.0 未随席位腿收窄申报同步（「场上非线内件」残留）
- 位置：`design.md:33`（系统级变化第 2 条仍写「可卖一件腾出位（备战席燃料 ∨ **场上非线内件**）」）vs `details/refresh-chain.md:24`、`:26`（收窄申报：席位腿 = 备战席燃料 only，场上腿在席位维不成立，静默裁掉并申报）vs `landing.md:41`（已是收窄口径）
- 直调证据：裁定 #7 原文（工作清单 W3 行）腾位腿确含「场上非线内件」；收窄申报本身成立（卖场上件释放上阵位不释放备战席位，恢复走关店-腾位-重进链——追查件 §5-2 席位坍缩机制吻合），但总纲「读一遍知全貌」的口径停留在收窄前。
- 修正方向：design.md:33 改为备战席燃料口径，收窄申报指针留在总纲或引 refresh-chain §1。

### F9【中】3.1 残留扫描范围三说并存（全仓 / 本阶段文件面 / docs 归末阶段）
- 位置：`details/hp-purge.md:49`（「3.1 阶段收尾对符号级词表做**全仓扫描**…**全仓安全**」）与 `:51`（「**扫描范围 = 词表全仓**」）vs `landing.md:9`（「扫描范围 = **本阶段文件面（src/ + sr-od-test/）**」）vs hp-purge.md:49 同段自注（「docs/ 残留扫描归末阶段…此前扫必然不清零」）
- 矛盾机制：「全仓」若按字面执行则 3.1 就要扫 docs（与其自注矛盾）；若按 landing 执行则词表符号在本阶段文件面**之外**的 src 残留不进扫描——实测存在此类面：`strategies/impl/cw_strategy.py:446`、`obs/cw_observation.py:2739`、`operations/cw_screen/cw_screen_prep.py:770/:1174` 均有 `decision_hp` 引用（F1 词表符号），不在 3.1 文件面内。
- 修正方向：定为一个口径——「src 全树 + sr-od-test 全树，docs/ 归末阶段」，hp-purge §6 与 landing 首节同步措辞。

### F10【低】核二·无过程叙事违规——对抗轮次发现编号残留
- 位置：`details/refresh-chain.md:21`（「对抗 H-2 修正」）、`:42`（「对抗 B5」）、`:43`（「对抗 B4」）；`details/hp-purge.md:27`（「对抗 A3 收编」）；`design.md:70`（「经对抗审确认」）
- 规范出处：iteration-design.md §5 rule 3（「第几轮攻击类引用随 changes/ 清理全部死亡…『本轮/修订后/已改』类措辞即打回」）；H-2/B4/B5/A3 为前轮对抗报告的发现编号（本轮禁读件），属会话局部标识符。
- 修正方向：改为语义描述——如 :21「（机制全集口径，merge_mechanics §2）」、:42「（实费档与带判据同一目标元组）」、:43（参数流钉死句已自足，删括注）、hp-purge:27 删括注、design.md:70 删「经对抗审确认」。同族轻症：refresh-chain.md:44「原解锁支撤稿」、`:79`「原 W3 形态」为修订史措辞，一并收敛。

### F11【低】hp-purge.md 篇内待决/已决并存（裁决前残留未同步）
- 位置：`details/hp-purge.md:7`（「待决约束：R-1/R-3 处置方案见总纲 §3，**用户裁决前本篇对应小节不动工**」）vs `:36`（「两项已于 2026-10-28 用户裁决通过…**本篇可开工**」）
- 直调证据：design.md §0/§3 与 landing.md:28/:30 均为已裁决口径；:7 为裁决前残句。
- 修正方向：删 :7 或改为「R-1/R-3 已裁决通过（总纲 §3）」。

### F12【低】ρ 口径两处表述不一，且对裁定 #6 字面（「注册表卡价」）的偏离申报位置缺总纲行
- 位置：`details/refresh-chain.md:40`（ρ = 「stay_target_of(state) 的 **CHARACTERS cost**」）vs `:42`（「target[2] **当前实费档**…**非注册表基价直查**」）
- 直调证据：`unfinished_star_targets`（levelup.py:174-203）返回第三元 = `effective_cost` **resolved 实费档**（docstring 自注「银狼系变费后实档」），stay_target_of:206-213 同源——:42 与代码一致，:40 的「CHARACTERS cost」表述失真。裁定 #6 字面为「注册表卡价」，:42 的实费档偏离有工程理由（与带判据同一目标元组、单一源）但总纲 §3 决策表无对应申报行（对照 R-6/R-8/R-9 行的申报先例）。
- 修正方向：:40 改为「target[2] 实费档（effective_cost resolved，与带判据同元组）」；总纲 §3 表补一行口径申报（裁定 #6 落地推导 = 实费档）。

### F13【低】证据文件锚漂移两处（快照继承面）
- 位置与直调证据：
  1. hp 清查件 E-7 锚 `kernel/test_settle.py:551-580`——实测路径 = `sr-od-test/test/sr_od/application/currency_war/operations/cw_op/test_settle.py`（内容吻合：:551 = 「hp 直读测试(decision_hp)」节、:580 断言 decision_hp）；按 hp-purge.md:59 快照「错位如实保留」原则将带病继承；
  2. 裁定载体工作清单「执行纪律」节引用「hp 清查件 §5 词表」——清查件实测止于 §4（无 §5）；幸设计词表（hp-purge §6）自足未引 §5，仅载体内部悬空。
- 修正方向：appendix 快照生成时对 E-7 加路径勘误注；工作清单该句随下批对账修正（非本迭代阻塞项）。

### F14【低】R-6 处置表述混乱：λ 表血带维被错挂到 cw_first_passage，cw_first_passage.py 文件面为空授权
- 位置：`details/hp-purge.md:26`（「例外（R-6）：cw_first_passage.py 本体保留…**其 λ 表血带维参数**随删申报」）vs `design.md:71`（「λ 表血带维随 hp 删除面**孤儿化申报**」）
- 直调证据：①λ 表血带维（hp_band/HP_BAND_NEAR_DEATH）实在 `statefn/lambda_death.py:34-39/:121-146`（清查件 B-12），不在 cw_first_passage.py——「其」字归属错误；②「随删申报」（hp-purge）与「孤儿化申报」（design）处置动词不一致（删 vs 保留申报孤儿）；③cw_first_passage.py 全文件对 3.1 词表符号**零命中**（直调扫描），R-6 又裁定本体保留——该文件在 design.md:47 的独占授权实际无可触碰面（无害但属空授权）。
- 修正方向：hp-purge.md:26 改为「λ 表血带维参数（statefn/lambda_death.py，清查件 B-12）按 design §3 孤儿化申报保留」；cw_first_passage.py 授权面可保留（防御性）但注明「本体保留、无词表触碰面」。

---

## 二、实际攻击过的面清单（直调核验，未列入发现者均通过）

1. **代码锚存在性与行号真值**（60+ 锚逐一直调，全部命中或已申报漂移）：shop.py 2080 行、:221/:234-264/:267-315/:327/:373/:885/:930/:996/:1277-1279/:1543-1616/:1963-1971/:1981-1989/:1994/:1996-2065；refresh.py:22/:32/:97-108/:140/:155/:160/:236/:282-378/:301；levelup.py:174/:193-194/:206-213/:240-277/:288-291/:300-306/:370-377/:376/:385-392/:484-514；cw_discipline_rules.py:82/:154/:212/:235；cw_economy.py:795-882/:1074/:1237/:1275；cw_comps.py:37/:125/:2859/:2862-3102；cw_performance.py:107/:244-269；cw_hp_policy.py:20/:35；cw_game_state.py:2954；cw_intention.py:1067-1094/:1099-1150/:1163-1171/:1166/:1427-1530/:1576；mandate.py:4/:392/:963/:996/:1078-1079；mandate_state.py:123-124/:174/:195；contracts.py:88-106/:100-106/:138-142/:166-171/:243-246/:252/:255/:261-267/:273/:279-291；__init__.py:54-55/:60/:62/:65/:71-73/:76；economy_cycle.py:12/:14/:24/:29-30/:177/:187/:233；telemetry/schema.py:460-465/:488-489/:500；statefn/odds.py:67；cw_investments.py:473/:1216；audit/provisional.py:64；cw_vocab.py:64-69；cw_comps.maybe_pivot 止于 :3102（清查件 :3086 已被设计修正为直调真值，正确）。
2. **语义断言直调**：r0_stop/r1_start 零调用壳 ✓；crisis_refresh_invariant 发射链零消费 ✓；all_in_xp_domain_hit 零产线消费 ✓；is_emergency 唯一消费 = refresh_ev_budget:1275 ✓；level_spend_blocked 唯一消费 = 门④ ✓；neardeath_direction_obs_ src 零发射 ✓；LOCK_PATH 键族测试侧零覆盖 ✓（cw_intention.py:1160 所称守卫测试文件实测不存在，hp-purge.md:35 申报正确）；upgrade_trigger/refresh_warranted 带域互斥（整级预留腿不可达的结构证明）✓；stay_target_of 返回 resolved 实费档 ✓；未锁窗口 unfinished_star_targets 恒空集 ✓；must_spend_r1_budget_fail 在 r2 拒绝域保留 ✓；must_spend_r1_no_buy_blocked 唯一发射点 :2065 ✓；测试仓无任何 r2_card_reserve 断言面（ρ 重定义无既有测试破坏）✓。
3. **证据文件抽核**：hp 清查件 A/B/C/D/E 组条目数（11/19/13/41/10）与锚抽样 ✓；B 组 §1 聚合与 §2.2 明细编号错位——设计已声明快照不重排 ✓；追查件 §0-§7（金账链/17 帧双关/三月七四臂够不着/P92 三帧/A-9 交叉复核）逐项与 design/详设引述一致 ✓；复盘件 A2/死亡形态 ✓；裁定 1-7 转述逐条比对工作清单原文 ✓（裁定 #5 互斥推导、裁定 #6 算式、裁定 #7 删除范围转述准确；裁定 #7 腾位腿收窄已显式申报）。
4. **正本与证明锚**：11_shop_decisions.md:55/:58/:59/:84/:103/:106/:110/:186（批读数 15/15、85/85、中位 105 逐字核对 ✓）；23_shop_screen.md:10/:20；01_math_framework.md:84/:194；10_prep_decisions.md:199；14_p1_consume_arms.md N5 系行；04_survival_budget/12_line_and_intention/02_mandate_layer/00_framework 章锚 ✓；math_proofs.md P21:45/P36:60/P92:113 ✓；proofs/p36-crisis-firepower-floor.md、p37:188、validations/ 目录 ✓；merge_mechanics §2 连锁合成与 §2.5 满栏例外 ✓；正本更新清单所列文件全部存在 ✓。
5. **规范与判据源**：iteration-design.md 三核细则/四硬规则/阶段七件 ✓；strategy-work §1（未证即停用/零调参）§3（无开关）§4（锚点事前写/A/B 挂起）§6（prereg 硬门）✓；sim-testing「先知道边界」末条/「单局复盘素材采集」节/cw_sim_match_drive 脚本 ✓；边界事实两处（2026-10-18 design.md:156 攒金收敛态声明逐字吻合；2026-10-28-supply-decision-wiring 目录存在）✓；landing 阶段小节七件齐 ✓（3.1-3.4 + 末阶段）；引用寿命分层（正文引 changes/ 仅边界事实两处，任务判据源明示许可）✓。
6. **测试面**：E 组 10 条对应文件全部定位 ✓（E-7 路径漂移见 F13）；test_sim_levelup_cycle.py:44 键域清单 ✓；test_seat_recoverable_narrow.py / test_no_target_three_arms.py / test_decision_payload.py:10/:158/:169 / test_line_select.py:358-360 / test_levelup_prob_axis.py:310-317 / test_shop_session_loop.py:658-679 / test_economy.py:321-382/:876-890 ✓。
7. **核三·治本**：归层（语义层 hp 入判据 + 约定层残件未清）成立 ✓；hp 全删 = 治本；刷新链三组件（目标中心条件替抽象枚举）= 治本且有裁定背书；W4 全停语义以支配性互斥论证替代新调参 = 符合零调参纪律；W2 撤解锁支的两难解开路径（预留腿恢复=推翻裁定 #5 vs 饿死环）论证自洽，且 2026-10-18 design.md:156 声明域在其原模型域（现金<线+批）内支撑「攒金收敛态非死锁」✓。未发现症状修法或同族逐件修补升级需求。

## 三、结论

终验轮主轴六项核验结果：①最终漂移——F2/F4/F5/F6/F8/F11（六处篇间/篇内不一致，集中在 shop.py 文件面契约与 R-1/R-3 处置细节）；②逐阶段「凭这份能开工吗」——3.1 被 F1（词表不可清零）与 F3（收编面无授权）阻塞，3.2 被 F2（文件面矛盾）与 F7（清理清单缺漏）阻塞，3.3 被 F6（载体未决）阻塞，3.4/末阶段可执行；③扫描口径与词表——F1/F9（互斥性与完备性各一处实质缺陷）；④文件面契约无主行——F2/F3；⑤测试面锚——F13（一处路径漂移，其余全过）；⑥正本更新清单对账——F7（两文件漏列 + 一处文件名悬空），其余行全部核销。

三高发现（F1/F2/F3）均为「落地批开工即撞」级别：F1 使 3.1 完成判据逻辑不可满足，F2 使账本唯一源与总纲互斥，F3 使 B 组连带验收不可执行。建议修复后无需再开全量新轮——按 iteration-design §6 循环对本清单逐项修复 + 同类泛化排查后，可做一轮定点复查收敛。
