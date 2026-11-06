# hp-purge-refresh-reform 对抗审查报告（第 3 轮）

- 审查人 = 干净上下文攻击者，未读前两轮报告（attack-r1/attack-r2.md 禁读已遵守，检索未命中其内容）。
- 审查对象 = design.md + details/hp-purge.md + details/refresh-chain.md + details/shop-buy-reform.md + landing.md（修订后现稿）。
- 判据源 = 全部直调复核，无二手转述：iteration-design.md；strategy-docs 九篇关键锚；math_proofs.md 六个被引命题行；mandate_v1/kernel 现役代码（约 60 个 file:line 锚逐一核对存在性与语义）；三件会话产物（hp 逻辑清查 / P2 金滞留追查 / g_20261028_011013 复盘）；用户裁定载体七条；测试仓实际文件与行号；外部边界声明两处（2026-10-18-levelup-band-gate design.md:156、2026-10-28-supply-decision-wiring 目录）。

## 结论

**13 条发现：高 2 / 中 5 / 低 6。** 主体方案（hp 判据族删除、刷新链三组件、买面三修复、W2 撤稿的资金序推导）经代码与证据对账成立、治本成立；发现集中在两类：**R-3 终选口径的修订后全量同步失败**（同一处未同步在 hp-purge 内部与 landing 双双残留）与**行级文件面/词表/测试锚的精度缺口**。

---

## 发现清单

### 高

**F-1【高·全量同步失败/R-3 口径自相矛盾】R-3 终选口径「删血项、机制保留」未同步到 hp-purge §1 表与 landing，且 landing 携幽灵引用**
- 位置：`details/hp-purge.md:22`（§1 表 A-11 行）vs `details/hp-purge.md:33`（§3 R-3）；`landing.md:27`、`landing.md:33`。
- 实况：hp-purge.md §1 表 A-11 处置仍写「**已裁决（R-3，整条退役）：视界机制全删**」，同篇 §3 R-3 已定为「**删血项、机制保留**——机制本体（`k_empty_window_fallback` 及其消费链）保留」（总纲 design.md §3 同口径）。而 design.md §3 对 R-5 的表述明立「**hp-purge §1 表行为准**」的权威序——按表执行会把机制本体整条删掉，与终选裁决相反。landing.md 3.1 范围与完成判据两处仍写「A-11 视界**整条退役**含 **G3 补全位点**」：「整条退役」为被否决口径；「G3」在 hp-purge.md 全篇不存在（细目编号是 ①②③④），为旧修订编号残留。
- 修正方向：hp-purge.md §1 A-11 行处置改写为「删血项、机制保留（细目见 §3）」；landing.md 3.1 两处改写为终选口径并删「G3 补全位点」字样。规范出处 = iteration-design.md §5 硬规则 4（design↔landing 全量反查）——该规则自述「失同步在同一迭代两次实证，二次复发即流程级」，本轮为第三处实例。

**F-2【高·锚失真】设计引用的守卫测试 `test_cw_lock_path_obs_keys` 不存在；neardeath 观测键为零发射死键，R-3 的条件式申报不可执行**
- 位置：`details/hp-purge.md:34`（「守卫测试 `test_cw_lock_path_obs_keys` **保留**」）；`landing.md:29`（3.1 文件面点名 `test_cw_lock_path_obs_keys.py`）；`details/hp-purge.md:34`（「`neardeath_direction_obs_` 键若发射条件含血项 → 随删申报」）。
- 实况：sr-od-test 全仓 grep `lock_path_obs|LOCK_PATH_OBS` 及 `p2_handoff_|promote_candidate_|weakplane_exempt_eval|intention_locked_frame_` 全部零命中——该守卫测试不存在，LOCK_PATH 观测键族在测试侧零覆盖（`kernel/cw_intention.py:1159-1160` 注释声称的守卫测试同样不存在，属代码注释与测试实况漂移，设计把漂移注释当了真）。另：`neardeath_direction_obs_` 前缀在 src 全域仅 `cw_intention.py:1166` 注册行一处，**无任何发射点**——R-3 的「若发射条件含血项→随删申报」的对象是死键，实现者无法按字面执行（找不到发射条件），且删该前缀会牵动（不存在的）守卫测试与 cw_intention.py:1157-1160 注释块，两处均未入删除面。
- 修正方向：hp-purge §3 R-3 测试面一句改为「该守卫测试不存在（注释声称与实况漂移），G 门保留后的观测键处置 = 实测发射面盘点后申报」；landing 3.1 文件面删去该测试名；`neardeath_direction_obs_` 处置改为确定性指令（如「零发射点，随观测键盘点一并裁决删留，连带 cw_intention.py:1157-1171 注释块」）。

### 中

**F-3【中·文件面契约冲突】`p92_seat_recoverable`（shop.py:267）与 A-9 注释（shop.py:327）的删除义务落在对方独占行段，无 carve-out、无归属阶段**
- 位置：`details/refresh-chain.md:27`（P92 整门删除声明「`p92_seat_recoverable`（`shop.py:267`）符号删除」）；`details/hp-purge.md:28`（A-9 连带面点名 `shop.py:327`）；`design.md:46`（carve-out 只有 `:373/:996` 两行）；`landing.md:43`（3.2 文件面 = `:1-249`+`:1962-2080`）、`landing.md:29`（3.1 文件面无 shop.py:327）。
- 实况：shop.py:267（`p92_seat_recoverable` 定义）与 :327（`_frame_search_windows` docstring 中的 `refresh_ev_budget` 注释，实测存在）都位于 shop-buy-reform 独占段 `:250-1961` 内。refresh-chain/hp-purge 各自声明删除，但总纲 carve-out 未划这两行、landing 两阶段文件面都不覆盖——「各详设不得触碰对方文件面」契约被删除面穿越，且残留扫描（验收词 `p92_seat_recoverable`、词表 `refresh_ev_budget`）按「本阶段文件面」执行时扫不到这两行。
- 修正方向：design.md §2.1 carve-out 扩为四行（`:267` 归 3.2、`:327` 归 3.1，或明确该两行随对应删除动作跨段执行并同步进 landing 两阶段文件面）。

**F-4【中·行号漂移】A-7 删除区间截断：cw_comps.py maybe_pivot 现行止于 :3102，设计区间 :2862-3086 少 16 行，且多个真连带符号不在任何删除面**
- 位置：`details/hp-purge.md:18`（A-7 锚 `cw_comps.py:2862-3086`）。
- 实况：清查件基线 = a42f1e2c；该文件其后经 aff29a0e0/f31c18ed9 两次术语 rename，行号已漂移。现行 `maybe_pivot` 跨 :2862-3102（:3087-3102 = 信号 2 支 + `return None`）——按声明区间删除会留下悬挂代码（实现者可自救，但设计锚失真，且 appendix 快照将继承同一错误）。连带面缺项：`pivot_overlap`（cw_comps.py:523/:539，唯一消费方即 maybe_pivot，删后孤儿化）不在删除面；`cw_performance.py:107`、`cw_hp_policy.py:20` 的 maybe_pivot 注释引用未入连带面；cw_economy.py:213 `effective_hp_threshold` 本体与 cw_vocab.py:69 re-export 的删除义务只在清查件 B-8/B-17 行（appendix 可补），hp-purge.md §1 表自身不带。
- 修正方向：A-7 锚更新为 `:2862-3102`（按现行树重测），连带面补 pivot_overlap 与两处注释引用；appendix 快照生成时按现行树全量重测行号（清查件基线早于两次 rename，A-8 的 :244-269 已是现行值而 A-7 不是，属混合年份锚）。

**F-5【中·验收口径】hp-purge §6 残留扫描词表不完备：删除面内十余个符号无词可扫**
- 位置：`details/hp-purge.md:49`（词表 10 项）。
- 实况：词表覆盖 A 组主删符号，但同属本篇删除面的以下符号不在词表：`blood_xp_full_clicks`（A-10 改名族）、`levelup_blood_gate_defer`（门⑥拒因键——R-1 删「血闸」家族命名后，若键改名，旧键在 telemetry 文档/判读面的残留无词表兜底；若不改名，与「删 hp 家族命名」的处置词冲突且设计未写明改不改）、`k_alert`/`k_hp_calibration_grid`/`blood_margin_low_hp`/`boss_tax_p75_by_plane`（清查件 B-5/B-6）、`handoff_boss_e_damage` 族（B-4）、`HP_SAFE_THRESHOLD`/`DIFFICULTY_HP_TABLE`/`effective_hp_threshold`（B-8/B-17）、`HP_QUALITY_ALARM`/`HP_DISTRESS_FRAC`（B-10）、`p1_blood_floor`/`p2_blood_floor`（B-11）、`v3_handoff_hp_proj`（B-15）、`P_HIT_Q_CONV`（B-18）。「符号级残留清零」作为完成必要条件时，口径不足以验收 B 组。
- 修正方向：§6 词表扩为「A 组词表 + B 组被删符号清单（随 appendix 快照生成时逐行收集）」，并对 R-1 改名族显式声明「计数键 `levelup_blood_gate_defer` 改名与否」——该语义选择现在无答案（见 F-10）。

**F-6【中·行级分工漏项】共享文件行级分工与实况有多处缺口（修订漂移类）**
- 位置与实况（全部直调核实）：
  - `mandate.py:4`：模块 docstring 引 `crisis_refresh_invariant`，不在 3.2 行级分工（design.md:49 只划 :1078-1079）——危机验收词扫描按阶段文件面执行时会漏；
  - `economy_cycle.py:12/:14/:177`：`refresh_ev_budget` 注释/调用点 docstring 三处，不在 3.1 分工（只划 :29-30/:187）；
  - `contracts.py:261-267`：`refresh_warranted` 契约行 scope 描述「三段式刷新判据主式（查表零计算…）」在目标可买并入后过期，未列入任何阶段同步点（3.2 只划 :252/:255/:273/:283）；
  - `statefn/odds.py:67`：在 landing 3.1 文件面有、design.md §2.1 共享分工无——总纲契约与 landing 文件面失同步（反向例）。
- 修正方向：design.md §2.1 共享分工补齐上述行；contracts.py:261-267 明确归 3.2（描述随目标可买语义同步）。

**F-7【中·依据锚错文件/错域】两处依据就地标注指向错误位置**
- 位置：`details/refresh-chain.md:17`；`details/shop-buy-reform.md:14`。
- 实况：①合成腿依据「merge §2.5/p76，shop.py:324-325」——该文本（「满栏不阻断…p76『深追不受席满阻断』」）实测在 **refresh.py:324**（all_channel_buy_exists docstring），shop.py:324-325 是搜索窗锚注释；且该 docstring 所属函数正是被删对象，依据文本会随删除消失，需迁入新实现处。②「目标件的合成链消费义务由 cw_synthesis.py:185『只合目标件』反向保证」——cw_synthesis.py:185 是**装备**合成隶属度阈值注释（`SYNTHESIS_MEMBERSHIP_THRESHOLD`），与角色星级合成链（3 合 1）不同域，不构成角色副本「非让渡死库存」的保证；角色侧依据应指向 merge 机器本体（如 `_merge_pair_names` 口径 / cw_merge_simulate）或删去该引。
- 修正方向：两处锚改指正确文件；refresh-chain 补一句「P92 删除后 merge §2.5/p76 依据文本迁入目标可买实现注释」。

### 低

**F-8【低·无过程叙事】攻击报告编号与对抗过程措辞残留**
- 位置：`details/refresh-chain.md:39`（「逐轮推演见 attack-r1.md G2，已归档」）、`:75`（「（攻击 G2 选项 b）」）；`details/hp-purge.md:33`（「按对抗 H1 工程实况定为」）；`design.md:68`（「经对抗实核不可行」）。
- 说明：饿死环推演正文已自足（design §2.0 第 3 条 + refresh-chain §2 末条），对 attack-r1.md 的指针可删；「对抗 H1」「攻击 G2」为审查过程编号，规范 = iteration-design.md §5 硬规则 3。修正方向：删指针与编号，保留纯语义表述。

**F-9【低·引用寿命】追查件/复盘件/工作清单无快照义务**
- 位置：`design.md:5-8`、`details/refresh-chain.md:73-74`、`details/shop-buy-reform.md:41`。
- 实况：清查件已有 appendix 快照义务（hp-purge §7），但追查件（refresh-chain/shop-buy 的关键依据载体：缺陷 #2/#3 归因、r2 帧实证、§1.4 P92 误拦三帧）与复盘件同为 .debug 会话产物且无摘录义务——依据就地标注的出处寿命不齐。修正方向：landing 3.1 快照义务扩一项，或在详设内把被引用的关键结论（缺陷归因段）就地摘录。

**F-10【低·无需再设计】R-4/R-7 处置口径不可执行；`levelup_blood_gate_defer` 改名与否未定**
- 位置：`design.md:69`（「随 3.1 落地批按 hp 清查件建议逐条处置」）。
- 实况：清查件 R-7 明言「留（标注）或删**请用户裁**」（无建议）、R-4 除倾向外「归属（观测层 or 独立保留）**请用户确认**」仍开放——「按建议处置」对这两条无输入。另 R-1 落地时门⑥拒因键是否随「删血闸命名」改名，设计未回答（见 F-5）。修正方向：design §3 对 R-4 归属、R-7 删留、门⑥键名三处给出确定答案或显式列为裁决项。

**F-11【低·裁定转述差】裁定 #7 席位腿收窄（去「场上非线内件」）等价性有据，但死态余量公式与裁定原文不一致且未申报**
- 位置：`details/refresh-chain.md:23`、`:28`；裁定原文 = `.debug/temp/2026-10-28_CW修复工作清单.md:52`。
- 实况：设计把「可卖一件腾出位〔备战席燃料 ∨ 场上非线内件〕」收窄为 bench-only + 访问间隙关店腾位链——依据成立（23_shop_screen.md:13 满席腾位收缩形态 + 节点内牌面持久），收窄本身合法。但「已知余量」死态公式（席满+零燃料+不可合成）比裁定原文余量公式（另含「场上无非线内件」条件）面更宽，行为变化申报未声明该差。修正方向：refresh-chain §1 余量句补齐条件并在行为变化申报中写明与裁定字面的这一处收窄及等价机制。

**F-12【低·前置裁决未声明闭合】W5「need_star 达标后同名副本语义」在清单中标注待裁决，设计以机械推导定案但无闭合声明**
- 位置：`details/shop-buy-reform.md:15`（缺口=0 → 显式停买）；`.debug/temp/2026-10-28_CW修复工作清单.md:68`（「前置裁决…待裁决后设计」）。
- 说明：推导本身成立（达标成员对同名 1★ 副本零星级推进，unfinished_star_targets 以持有最高星 < need 判定，levelup.py:199-202 实测）；缺的是把「该前置已按机械事实闭合、无需用户裁定」写明。修正方向：shop-buy-reform §1 补一句依据声明。

**F-13【低·锚区间重叠】hp-purge §1 A-11 的 H 区间写法含入 G 门**
- 位置：`details/hp-purge.md:22`（「`cw_intention.py:1067-1150`（H）+ `:1099-1150`（G 门）」）。
- 实况：`p2_supply_horizon` 实际 :1067-1094（清查件口径一致），:1067-1150 与 G 门区间重叠，切区间时会含 `line_completion_feasibility` 函数头。修正方向：H 锚改 :1067-1094。

---

## 已核实无发现的面（证据要点）

- **行号锚主面**：shop.py（总 2080 行 ✓；三分段 :1-249/:250-1961/:1962-2080 语义内容逐段核对 ✓；:221/:234/:267/:327/:373/:885/:930/:996/:1543-1616(M6 ✓)/:1859/:1963-1971/:1981-1989/:1994/:1996-2054/:2062-2065 全部命中）；refresh.py（:22/:32/:97-108 锁定后分支 ✓/:140/:160/:236/:282-378 全文读毕，docstring 与设计描述一致）；levelup.py（:174/:206-213 stay_target_of ✓/:370-377 门④ ✓/:385-392 门⑥ ✓/:484-514 ✓，门序 7→6 推导成立）；contracts.py（:88-106/:100-106/:138-142/:166-171/:243-246/:252/:255/:273/:279-282/:283 全部精确）；criteria/__init__.py（:54-55/:60/:62/:65/:71-73/:76 全部精确）；cw_discipline_rules.py（:82-128/:154-209/:212-260 精确）；cw_economy.py（:792-882 血闸族精确、:1074-1088/:1237-1287 精确）；cw_intention.py（:1067-1094/:1099-1150/:1163-1171/:1180-1181/:1427-1530/:1576 精确）；cw_performance.py（:244-269 A-8 精确，docstring 自申报待办层挂空与设计一致）；cw_game_state.py:2954 ✓；economy_cycle.py（:24/:233/:29-30/:187 ✓）；telemetry/schema.py（:488-489/:500 精确）；statefn/odds.py:67 ✓；cw_investments.py:473（高效决策 9999）✓；k_empty_window_fallback 三处生产消费位（shop.py:885/entry.py:480/decision_payload.py:101）精确 ✓。
- **R-1 转述**：「血余额 ≥ 批 + hp 不可信帧 fail-closed」与 cw_economy.py:817-882 实况逐位一致；依据锚 11_shop_decisions.md:58 存在且语义相符；entry.py 无 blood_xp 直引（改名面不外溢，核过）。
- **R-3 转述**：三消费位 + P1 空窗防环职责（contracts.py:138-142）+ K_FALLBACK_SOURCE_THREE_ARM 守卫链（contracts.py:166-171）实况相符；撤销/换线消费位停用证据（cw_intention.py:1180-1181）相符；行为变化申报方向（可行性/回退带不再随血低收紧）与 G→H 链实况一致。
- **裁定七条转述**：#5/#6 与代码实况（shop.py:1987-1989、r2_card_reserve 旧口径漏 2★ 追 3★）一致；#6 新算式与裁定字面逐项一致；#2 追认与现行三分派一致；W2 撤稿的资金序推导自洽（资金线推迟态 = 攒金收敛，等级帽封顶后结构性收敛，非死锁），外部声明锚 changes/2026-10-18-levelup-band-gate/design.md:156 实证存在且语义相符。
- **证据文件**：hp 清查件 A 组 11 条/B 组 19 条/C 组 13 条/D 组 41 条（D-1~D-30 + DG-1~DG-11）/E 组 10 条计数与设计声称全部吻合；追查件 §1.2/§1.4/§4/§7 与设计引用逐项对上（17/17 拦截、bench 9/9、m6_bench_full=8、p92_no_buy_refresh_blocked=3、A-9 零行为差复核）；11_shop_decisions.md:186 三个批读数（15/15、85/85、中位 105）逐字核实。
- **文档锚**：11_shop_decisions.md:58/:110/:186、01_math_framework.md:194（all_channel_exists 钩子行）、23_shop_screen.md:10（R1 漂移行 + P36-a + P92 三合一，正本更新清单覆盖 :10/:20）、14_p1_consume_arms.md（N5/§5.2 区段存在）、10_prep_decisions.md:199、p37-late-xp-conversion-cost.md:188 全部命中；math_proofs.md P21(:45)/P36(:60)/P40(:64)/P54(:76)/P86(:106)/P92(:113) 六行存在；proofs/p36-crisis-firepower-floor.md 整文件存在（删面真实）；正本更新清单与清查件 D 组对账结构成立（landing 已声明「完整单一源 = 清查件 D 组，不一致以快照为准」，抽对 20+ 行无出入，12_line_and_intention §2 H 语义行为设计自加义务、合理）。
- **测试面存在性**：test_no_target_three_arms.py（实锁 P86 三分支与回退带，设计声称属实）、test_seat_recoverable_narrow.py（实锁 shop.p92_seat_recoverable）、test_sim_levelup_cycle.py:44（p92 计数键域清单，精确）、test_decision_payload.py:10/:158/:169（精确）、test_line_select.py:358-360（精确）全部存在；清查件 E 组引用的 9 个测试文件全部存在。
- **结构规范**：总纲 §0-§2 齐全、三详设三部分齐全、landing 五阶段七件齐、README 结构合规、附录前瞻声明（hp-purge-appendix.md 3.1 开工前生成）合规、明确不解决清单与边界依据（iteration-design §1.1 + supply-decision-wiring 目录实证存在）合规。
- **治本**：归层结论（语义层 hp 立为输入 + 约定层残件未清）与证据相符；三条线均修根（删判据族而非加开关、三组件对齐裁定模型、免费分支纳入判据而非限次补丁）；无逐件补丁模式复发。
