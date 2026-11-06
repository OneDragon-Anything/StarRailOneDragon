# hp-purge-refresh-reform 设计对抗审查报告（R-2 轮·无前提）

> 审查人 = 干净上下文攻击者；对象 = design.md + details/ 三详设 + landing.md + README.md（修订后现稿）。
> 判据源全部直调复核（iteration-design §7 三核 + strategy-work §6）：strategy-docs 宪法篇/math_proofs、
> 现役代码锚逐 file:line 直调、hp 清查件/追查件/复盘件/裁定清单独立抽核、测试面直调、
> 边界迭代（2026-10-28-supply-decision-wiring）与 sim-testing 引用直调。
> 结论：**4 高 / 9 中 / 8 低**，未收敛；核心方案（hp 判据族物理删除 + 刷新链三组件 + 买面三修复）经直调成立，
> 集中缺陷在**文件面契约、R-3 删除面完备性、测试面锚**三处——照现稿开工会在 R-3 链上撞运行时错误或验收死锁。

**工具副作用披露**：审查过程中一次未限定目录的全文检索意外返回了禁读件 attack-r1.md 的 4 行命中（未主动阅读）。
本报告全部发现均基于本人对代码/文档/证据文件的独立直调证据（每条附行号），未引用该文件内容。

---

## 一、发现清单

### 高（H）

**H1｜R-3「K 空窗回退」链删除面不完备：三个生产消费位漏列，词表与「只删 p2plus 带」自相矛盾；契约层守卫漏一处 → 照稿开工必然运行时错误或验收死锁**
- 位置：details/hp-purge.md:33（R-3 删除面补全清单）、:48（§6 词表含 `k_empty_window_fallback`）；design.md:46（hp-purge 独占文件面）；landing.md:29（3.1 文件面）。
- 代码真值（直调）：`k_empty_window_fallback`（kernel/cw_intention.py:1576-1603）的现役生产消费位有三处——`shop.py:885`（商店序 1 名单 K 空窗回退，活调用）、`entry.py:480`（准备域）、`decision_payload.py:101`（payload 派生链）——均不在 hp-purge 删除面、不在其文件面、不在 landing 3.1 文件面。仅删 p2plus 带（:1602-1603）→ 符号保留 → §6 词表「k_empty_window_fallback 符号级清零」不可达；整函数删除 → 三处消费位 AttributeError + P1 空窗死锁环回归（contracts.py:138-142 明文该函数 p1_gap 带防「K 空→零买入→板面零变化→永不锁」环）+ R-3 行为申报（design.md:67 只申报「P2 未锁定窗口囤货方向」）严重不完整。
- 同链漏项：`K_FALLBACK_SOURCE_THREE_ARM` 在 contracts.py:100-106（`_s_reserve_line_formed`）与 :166-171（`_k_projection_domain_full`）两处守卫消费，hp-purge.md:33 只列 :166-171——删常量后前者 ImportError 被 ensure_contract 吞（contracts.py:361-364 fail-closed）→ EV 买候选/M6/dominance 在 K 空窗帧**静默全弃权**（行为退化，非崩溃，更隐蔽）。
- 修正方向：R-3 删除面补全三消费位 + p2plus 带替换语义（shop 序 1 名单/entry 部署围栏/payload 回退各返回什么）+ `_s_reserve_line_formed` p2plus 支；词表按「整函数删」或「p2plus 支删」二选一重新对齐；行为申报补 K 空窗帧买面/部署围栏语义。

**H2｜hp-purge 删除面实际触碰文件超出其文件面授权（清查件 B 组/契约行/连带面无主）**
- 位置：design.md:46（独占清单 8 文件）、:44（互斥契约）、design.md:30（「清单单一源 = hp 清查件…落地批照单执行」）；landing.md:29（3.1 文件面）。
- 清查件直调（.debug/temp/2026-10-28_hp逻辑清查.md）B 组锚需触碰：`kernel/cw_game_state.py:4707-4746`（B-16 scalar_projection_state）、`kernel/cw_vocab.py:64-69`（B-17 re-export）、`mandate_state.py:123-124/:174`（B-14/B-15 计数器与孤儿字段）、`statefn/predicates.py:125-185`（B-11 待 R-7）、`audit/provisional.py:64`（B-18）、`cw_first_passage.py`（B-9 待 R-6）——全部不在 hp-purge/3.1 文件面。「照单执行」⊈「文件面授权」，两契约互相矛盾。
- 清查件 A-5 明细（:74）自带「契约登记 criteria/contracts.py:243-246、criteria/__init__.py:54-55 随删」——hp-purge.md:17（A-4/A-5 表行）转述时丢弃；两文件在 3.2 面（landing.md:43）但 3.2 验收词（refresh-chain.md:25/:45）不含 `level_spend_blocked` → 该符号在 contracts.py/__init__.py/mandate.py:963/:996 的残留**永无阶段合法删除与扫描覆盖**，hp-purge §6「level_spend_blocked 清零」验收必然落空。
- 同型：A-7 连带面 `cw_comps.py:37`（effective_hp_threshold import）、`:125` 注释、`:2852-2859`（PIVOT_SURVIVAL_COOLDOWN_ROUNDS 常量与保命豁免注释）不在 A-7 锚（:2862-3086）内且词表无覆盖。
- 修正方向：总纲 §2.1 文件面契约按「删除面全量盘点」重写（B 组触碰文件收编 + contracts.py/__init__.py 行级 carve-out + level_spend_blocked 词入 3.1 扫描口径），或把 A-5 契约行/B 组触碰面显式划入 3.1 文件面。

**H3｜shop.py 行段互斥契约与买面六序实际分布矛盾：≈L1600 边界把 M6/垫件/序 5/序 6/C1 切进 refresh-chain 面，W4/W5 落点跨面不可达**
- 位置：design.md:47（shop-buy-reform 独占「买面段（六序/M6/星级语义，≈L200-1600）」）vs design.md:48（refresh-chain「会话/凑金段（≈L1600-2080）」）；landing.md:43（3.2 文件面）。
- 代码真值（直调，shop.py 全文恰 2080 行）：M6 压牌库段 = shop.py:1543-1616（裁定载体 W4 锚与追查件 §5-3 锚一致）、垫件支 :1618-1659、序 5 EV 买面 :1750-1797、序 6/C1 核心卡支 :1799-1859——六序买面实际延伸至 ≈L1859，刷新发射段起点 = :1962。「六序/M6 归 shop-buy-reform」的语义管辖与「≈L1600-2080 归 refresh-chain」的行段授权冲突：W4 的实现落点（M6 触发谓词追加窗口否决项，shop-buy-reform.md:23）按 3.3 文件面不可达。
- 同族：design.md:52「若 W4 需改 fuel_sell_candidates 行为，改动归 shop-buy-reform」——该本体在 mandate.py:392（直调），不在 shop-buy-reform 文件面（shop.py 买面段+shop_session.py+levelup.py 消费接线）。
- 修正方向：行段边界以语义分界重划（买面 ≈L200-1961 / 发射+收工 ≈L1962-2080，或按函数清单而非行段），fuel_sell_candidates 本体文件（mandate.py）显式入 shop-buy-reform 文件面或声明「只消费不改本体为硬边界」。

**H4｜测试面锚错位与漏列：test_no_target_three_arms.py 归属错误；P92 实际测试面未列；R-3 测试面零登记**
- 位置：details/refresh-chain.md:25（P92 删除面「测试 test_no_target_three_arms.py P92 断言面」）；details/hp-purge.md:32-33（R-3 处置，无测试清理）。
- 直调：test_no_target_three_arms.py 锁的是 **P86 三分支判据**（docstring :15-20「cw_intention.no_target_arms/k_empty_window_fallback」、test_k_empty_window_fallback_bands :128、乙臂收编 hub_option 不得复现断言 :191-227）——它是 **R-3 删除对象**的测试，与 P92 无关。P92 的实际测试面 = test_seat_recoverable_narrow.py:192（`p92_no_buy_refresh_blocked` 断言）+ test_sim_levelup_cycle.py:44（键域清单）——refresh-chain 未列。R-3 测试清理（test_no_target_three_arms.py 全文件、test_decision_payload.py:10/:158/:169、test_line_select.py:358-360 的 k_empty_window_fallback 直调断言）在 hp-purge 零登记。
- 连带：`p92_seat_recoverable`（shop.py:267）在 P92 门删除后仅剩目标可买席位腿复用——符号名携带 p92 词根，验收词 `P92` 扫描将命中保留符号；该函数去留/改名未声明（refresh-chain.md:24「复用同参装配」未指明是调它还是按其形态另写）。
- 修正方向：refresh-chain §1 测试锚改为 test_seat_recoverable_narrow/test_sim_levelup_cycle；hp-purge §3 补 R-3 测试清理清单（含守卫测试 test_cw_lock_path_obs_keys，见 M7）；声明 p92_seat_recoverable 改名或保留豁免。

### 中（M）

**M1｜R-5（挂空死码 A-6/A-7/A-8）处置三处口径不一致**
- 清查件 §3 R-5（:240）明文两难未决「请用户定范围」；design.md:68 括号注「R-4/R-6/R-7 有建议方案」漏 R-5 的处置路径；hp-purge.md:18-19（A-6/A-7/A-8 表行）已写死「删」。裁定未落，详设先行拍板，总纲与详设不同步。修正：R-5 补进总纲 §3 已裁决表（若用户已口裁）或回退详设表行为「随 R-5 裁决」。

**M2｜landing 正本更新清单与清查件 D 组对账不全 + telemetry/schema.py 归阶段矛盾**
- landing.md:95-110 清单漏：`strategy-docs/20_large_balance_must_spend.md`（清查件 D-10 有收尾行）、proofs 行漏 `p21`（D-19 降级义务——hp-purge.md:42 有「P21 等删除或重锚」，landing 清单 proofs 行只有 p36/p37/p71/p72/p85/p86/p92/p28/p24）、无 `proofs/validations/` 面（D-25 随母命题处置）。
- landing.md:110「telemetry/schema.py 义务来源枚举 `'crisis'` 清 ← 3.1」但 3.1 文件面（landing.md:29）无此文件；该文件物理改动在 3.2 面（landing.md:43 注释残留三处）。修正：清单补三行 + 归 3.2。

**M3｜refresh-chain §2 缺验收词；:65 锚符号错位**
- landing.md:48 判据引用「refresh-chain 详设 §1/§3 各段验收词」——§2（金线闸/R 族清理，refresh-chain.md:28-38）无验收词，R 族（`r0_stop|r1_start|r1_commitment_account`）与 GATE_GOLD_SHORT 支删除无扫描词支撑；裁定载体 W10 的验收词（grep 三符号，工作清单 :104）未被继承。且 :65 直调 = `('refresh', 'r1_commitment_account')` 注册行（criteria/__init__.py:65），非 r0_stop/r1_start 的行——refresh-chain.md:38 合并转述丢了 r1_commitment_account 符号名，实现者按文执行会错位。修正：§2 补验收词（含 r1_commitment_account）并点名符号。

**M4｜landing 正本更新清单 math_proofs.md 路径错误**
- landing.md:100 写 `strategy-docs/math_proofs.md`；该文件实际在 `docs/develop/sr_od/application/currency_war/proofs/math_proofs.md`（glob 直调；strategy-docs/ 下无此文件）。末阶段按清单找不到文件。

**M5｜refresh-chain 对 shop-buy-reform 的节号引用错**
- refresh-chain.md:50「负结果记忆本体归 shop-buy-reform 详设 §4」与 :64（§5 伪码注释「# shop-buy-reform §4」）——直调 shop-buy-reform.md：负结果记忆在 **§3**（:27），§4 是「明确不做」（:34）。修订漂移（硬规则 4）。

**M6｜A-9 删除锚终点失真；get_node_goal 全参支收窄形态未声明**
- hp-purge.md:27 锚「:1237-1275 refresh_ev_budget 归零」——函数实际 :1237-1287（直调），词表 `refresh_ev_budget` 清零要求整函数删除时锚不覆盖 :1276-1287；消费位 `cw_economy.py:995`（get_node_goal 全参支内，现役死路）与 economy_cycle.py:187（channel_capacity，披露面链）删除后 get_node_goal 形参支收窄形态（清查件 B-16「改」）无执行规则。
- 附注：A-9「零行为差（消费端=遥测披露面）」声称经独立复核**成立**（obligation 唯一消费者 = disclose_budget→v3_release_budget 披露字段 economy_cycle.py:295，docstring :243-255 明文禁决策消费；get_node_goal 全参支现役无调用——budget.py:106 部分传参走 :1000 先验 fallback）。本条只报锚与执行规则，不动摇处置结论。

**M7｜R-3 删除面未声明 G 门观测键族与守卫测试处置**
- cw_intention.py:1163-1171 `LOCK_PATH_OBS_KEY_PREFIXES` 含 `p2_supply_gate_cull`/`neardeath_direction_obs_`（G 门/H 观测键；:1160 注释守卫测试 = test_cw_lock_path_obs_keys）。G 门删除后这些键零发射成死键、守卫测试红——hp-purge.md:32 处置②未提。修正：处置②补观测键族与守卫测试的随删/保留声明。

**M8｜hp-purge §2 B 组执行规则只覆盖「删/不动」两态，「改」类条目无执行语义**
- hp-purge.md:25 规则原文只定义两态；清查件 B 组含「改」类：B-6（decision_hp 随 A 组孤儿化可删/可信位保留）、B-16（见 M6）、B-19（blood_xp_mode 随 R-1 联动核）——三者既非 R-4~R-9 裁决项也无执行规则。修正：B 组执行规则补「改」类处置映射。

### 低（L）

**L1｜过程叙事残留（硬规则 3 违例，多处）**
- design.md:35「对抗审 G2 实证」；refresh-chain.md:21「对抗审 M7 修正」、:35「对抗审 M9 修正」、:37「对抗审 G2 撤稿…攻击推导见 attack.md G2」、:42「对抗审 L13」、:73「攻击 G2 选项 b」；hp-purge.md:27「对抗审 G4 归属更正」、:33「对抗审 G3」、:45 标题「对抗审 M10 时点修正」、:52 标题「对抗审 L-low」、:59「第一版推荐，已放弃（对抗审后确认）」；shop-buy-reform.md:11 标题「对抗审 G1 语义链修订」、:16「G1 核心修正」。iteration-design §5 卡点「『本轮/修订后/已改』类措辞即打回」；G2/M7/G4 等编号随对抗报告清理死亡（引用寿命违例）。论证内容保留、过程表述转纯语义。

**L2｜总纲 §2.1 文件面契约清单不完整；三文件跨详设双触碰无行段划分**
- landing 各阶段文件面中的 mandate.py、contracts.py、criteria/__init__.py、economy_cycle.py、telemetry/schema.py、cw_investments.py 均不在 design.md:44-49 契约三行清单内；contracts.py（hp-purge :150/:327/:166-171 vs refresh-chain :252/:255/:273/:283）与 economy_cycle.py（3.1 动 :29-30/:187、3.2 动 :24/:233）、telemetry/schema.py（:500 归 3.2、'crisis' 归 3.1）为双触碰文件，契约未给行段/条目划分。

**L3｜「清单单一源」表述漂移；appendix 未进文档清单**
- design.md:30「清单单一源 = hp 清查件，本迭代不复制清单」vs hp-purge.md:54「快照抄录至 details/hp-purge-appendix.md，作为落地批执行单一源；.debug 原件仅作溯源」——总纲 §2.0 未同步快照义务；appendix 落地后为 details/ 第 4 份文件，README.md 与 design.md 文档清单均未预留行。

**L4｜「满栏例外」表述歧义 + 目标可买新拒因键未定义**
- refresh-chain.md:17「已持同名同星 1★ 恰 2 张（买第 3 张直接合成，满栏例外）」未说明例外方向（机制事实 = 满栏不阻断、买入即自动合成净释放 1 席——shop.py:324-325 引 merge §2.5/p76 可证）；此处无依据就地标注（硬规则 1）。refresh_warranted 返回 (bool, 拒因键)——目标可买 False 的新拒因键未定义，观测面判读归因缺口。

**L5｜landing 3.4 删除性判据为必然真（弱验收）**
- landing.md:75「不再出现危机带拦升级 17 帧/金滞留形态」——机制删除后结构性不可能重现，判据无鉴别力；建议改为「同 seed 轨迹差异点逐帧对账（锚 = 追查件 §1.2/§1.4）+ 四指标读数」，把「形态消失」降级为机理说明。

**L6｜must_spend_r1_no_buy_blocked 计数键处置未声明**
- shop.py:2064-2065（P92 拒绝域内联级计数）随 P92 门结构消失，refresh-chain 验收词不含该键，去留未声明（对照 must_spend_r1_budget_fail :2067 在 r2 拒绝域，保留）。

**L7｜r2_card_reserve 重定义的契约行/BYPASS 行描述同步未列**
- contracts.py:279-282（「P54-r2-interest-floor §②」描述）、criteria/__init__.py:71-73 描述文本随 ρ 语义改需更新；refresh-chain.md:35 只列了 shop.py:221 别名与 P54 命题行，未列这两处（文件在 3.2 面可改，缺义务声明）。

**L8｜行号/节号小漂移汇总**
- refresh-chain.md:7「P92 通道枚举（shop.py:1975-2049）」——装配+调用实际至 :2054、计数键 :2062-2063（3.2 段覆盖无害）；refresh-chain.md:38/hp-purge.md:33「cw_intention.py:1555-1603」——`k_empty_window_fallback` def 实际 :1576（起点落在 hoard_target_set 内部注释）；hp-purge.md:19「cw_performance.py:244-268」——函数实至 :269；hp-purge.md:42「D 组 41 条（hp 清查件 §2.4）」——§2.4 仅 30 条（D-1~D-30），41 = §2.4 + §2.5（DG-1~DG-11，11 条 game 侧），节号应写 §2.4+§2.5；landing.md:93 同引 §2.4。

---

## 二、零发现面（实际攻击过且核实无误）

1. **裁定转述忠实**：裁定 #1-#7（修复工作清单「用户裁定」节）与 design.md §0/§2.0/§3 逐条对——hp 出策略/删除纪律/危机不变式+P36-a/整级预留腿死因（互斥不可达）/金线算式（移项一致）/P92 删除+目标可买三腿，均忠实；裁定 #7 席位腿收缩为 bench-only 有据（23_shop_screen.md:13「满席腾位=关店走备战 M4」+ economy.md §2.1 牌面持久依据，就地标注 ✓）。
2. **数值证据链全部直调吻合**：15/15、85/85、终金中位 105（11_shop_decisions.md:186）；17/17 帧 levelup_crisis_defer（复盘件 :3815）；bench 9/9、m6_bench_full=8、p92_no_buy_refresh_blocked=3、三月七 r2 帧、20 槽 4 板（追查件 §1.2/§1.4/§1.5/§4/§5）；9999 次免费刷（cw_investments.py:473 + shop.py:1963-1971 直调）；death@P2r5 金 142（复盘件 :10/:3815）。
3. **代码锚逐点直调**（吻合项）：refresh.py:22/:97-108/:140/:160/:236/:282-378；shop.py:221/:234/:267/:327（refresh_ev_budget 注释 ✓ 属 A-9 连带）/:373（no_target_arms docstring）/:885/:930/:996/:1963-1971/:1981-1989/:1994/:2037；cw_discipline_rules.py:82-128/:154-209/:212-260；levelup.py:174/:206/:370-377/:385-392/:484-514（门序 7→6 与 11:55 七道一致）；cw_economy.py:792-882/:995/:1074-1088/:1237；cw_intention.py:1067-1150/:1180-1181/:1427-1603；cw_comps.py:2862-3086（信号 3 :2918-2995）；cw_performance.py:244-269；cw_game_state.py:2954；contracts.py:150/:166-171/:243/:252/:255/:273/:283；criteria/__init__.py:54/:60/:62/:65/:76；mandate.py:4/:392/:1078-1079；economy_cycle.py:24/:29-30/:187/:233/:295；statefn/odds.py:67；telemetry/schema.py:488-489/:500；cw_synthesis.py:185；shop_session.py:109；crisis_invariant_lane/crisis_overflow/authorize_release_refresh 零定义仅三处注释 ✓。
4. **A-9 零行为差独立复核成立**（见 M6 附注）——设计对追查件 §7 的转述准确。
5. **正本/证明锚**：11:58/:110/:186、01_math_framework.md:194、12_line_and_intention.md §1.4(:49)/§2(:68)、23_shop_screen.md:10（r1_commitment_account/all_channel_buy_exists/crisis 死引用集中行，清理面覆盖）、math_proofs P21:45/P36:60/P86:106/P92:113、proofs/p36-crisis-firepower-floor.md 存在、p37:188、04_survival_budget §7（[40]② 已裁定行 :66 域）、00_framework §3（hp 授权两件）、10_prep_decisions.md:199（p44 移除注记）。
6. **边界事实**：2026-10-28-supply-decision-wiring 五件套存在 ✓；changes/2026-10-18-levelup-band-gate/design.md:156「攒息期双滞=预期健康态」声明域 ✓；sim-testing「先知道边界」末条 A/B 挂起 +「单局复盘素材采集」cw_sim_match_drive ✓；2026-10-12 期望式裁定（refresh.py:51 docstring + shop-buy-reform §4 引用）✓。
7. **测试面**：test_no_target_three_arms.py/test_levelup_prob_axis.py（E-1 锚 :316/:435/:508-515 ✓）/test_shop_session_loop.py（E-3 锚 :665 ✓）存在且锁语义与清查件一致。
8. **治本核（核三）成立**：根因归层（语义层 hp 立为输入 + 约定层残件未清）与代码实况相符（refresh 判据链本身无 hp 入参，hp 经门④拦升级间接锁刷——追查件 §2 互锁机理直调吻合）；方案 = 物理删除 + 三组件定型，修根非症状；无开关、无悬置、prereg 硬门已建表（landing「验证与保全」节，四指标+FM-1+读数行+锁线行为，语义更新申报明确）。

## 三、三核结论

- **核一（无前提）**：不通过。H1-H4 + M6——凭现稿开工：R-3 批会在 K 空窗回退链撞运行时错误或验收死锁；3.1 批按清查件照单执行必越文件面；3.3 批 W4 落点不可达；测试随删清单锚错文件。landing 阶段七件齐、依赖序合理、验收凭据形式明确——问题集中在设计层的文件面/删除面契约，不在阶段拆分。
- **核二（规范遵循）**：L1（硬规则 3 过程叙事）、M2-M5/L2-L3/L8（硬规则 4 修订后全量同步未做透：正本清单对账、交叉节号、路径、单一源表述）；硬规则 1 依据标注总体良好（仅 L4 一处缺标注）；阶段小节七件齐 ✓；引用寿命分层 ✓（.debug 依赖已有快照义务补救）。
- **核三（治本）**：通过（见零发现面 8）。

**处置建议**：H1-H4 返设计层修订（文件面契约重划 + R-3 删除面补全 + 测试面清单重锚）后，M/L 随修订一并全量同步；修订后按惯例再起无前提对抗轮。
