# hp-purge-refresh-reform 无前提对抗审查报告（attack）

- 审查日期：2026-10-28。审查者 = 干净上下文攻击者，判据源全部直调复核（代码读体、正本读行、证据文件读节、测试仓直查），未采信任何二手转述。
- 结论：**非零发现，17 条（高 4 / 中 7 / 低 6）**。设计主体（裁定转述、代码主锚、数学行锚、边界迭代、落地结构）经直调大量命中为真，但存在 4 个会阻塞/带偏落地批的实质缺陷，详见下表。末节附「实际攻击过的面清单」与「核验为真的面清单」。

## 发现清单

严重度定义：高 = 按现稿落地必然产出错误实现/契约破坏/无法验收；中 = 语义未定或依据失真，实现者须停手回设计或自作主张二选一；低 = 锚点/口径瑕疵，不阻塞但须修。

### 高

**G1｜W5「买 1★ 即推进」在机器上中途断链，且制造已裁让渡的死库存形态**
- 位置：`details/shop-buy-reform.md:14`（「含已持 2★ 追 3★ 成员买 1★ 副本——3★ = 9 张 1★ 等价，买 1★ 即推进」）、`:16`（「M2b 合成完成买（宽集）与 P92 ④腿（已删）不受影响」）；代码锚 `shop.py:1277-1279`（m2_stockpile 门 `_cnt(m,1)==1 ∧ _cnt(m,2)==0`）、`shop.py:1315-1333`（M2b 触发 = `_merge_pair_names` = 全局面同名**恰 2 张 ∧ 均 1★**，`shop.py:234-247` docstring 明注「1★×2 与 ≥2★ 同名并存」买三张通道机器未实现、11_shop_decisions.md §2 同口径显式设计边界）。
- 攻击推导：2★ 已持有成员追 3★，W5 放开前两张 1★ 副本买入后，局面 = 1★×2 ∧ 2★ 并存——此时第 3 张 1★ **无任何买臂**：M2b 形态不匹配（恰 2 张全 1★）、m2_stockpile 被 `cnt2≠0` 关闭、M6 排除线内成员（追查件 dseq97 实证 `m6_line_member_excluded`）。合成连锁（merge §2.5/14 号稿 §3.7：买第 3 张 1★ → 第 2 只 2★ → 连锁 3★）因第 3 张买不出而永不触发。结果 = 9 张等价推进在第 3 张卡死，且该形态正是 14_p1_consume_arms.md §3.7 裁定让渡的「cnt1≥2 ∧ 有 2★」死库存形态（该裁定的退出依赖 = 位面 1 目标未立；P2 已立 3★ 目标，让渡理由不适用，机器断链适用）。设计对第 3 张 1★ 由谁买、合成通道是否随 W5 扩（推翻 11 §2 显式边界需申报）零着墨。
- 修正方向：三选一并申报——①W5 同批扩 M2b/新增买臂覆盖「1★×2 ∧ ≥2★ 并存」形态（连带 `_merge_pair_names` 收扩与 P92 ④腿注释同步，推翻显式边界须作为行为变化申报）；②W5 收窄为「未持有任何成件的成员副本照买」，2★ 追 3★ 另立项；③申报「买 1★ 推进仅到 1★×2 即停」的真实语义并给退出路径。landing 3.3 的「2★ 追 3★ 场景单帧」测试须改锁完整推进链而非单帧可买。

**G2｜解锁支 × 整级预留腿删除的联合效果未分析：凑金在途帧刷新无预留，存在升级饿死环形态**
- 位置：`details/refresh-chain.md:34`（整级预留腿删除，死因 = 升级触发态与刷新放行态互斥）、`:35`（解锁支：升级判定 ∈ {defer/gold_short} → 放行刷）；被删保护的原意图 = `shop.py:1981-1989`（「刷新不烧升级凑金，防压牌库换卡↔升级凑不齐活锁」）。
- 攻击推导：腿删除的互斥论证（gold_short 只在 stay_gate 帧出现、stay_gate 帧 refresh ①支必拒）被解锁支**本人打破**——解锁支恰在 stay_gate ∧ defer/gold_short 帧放行刷新，而此时刷新预留已无升级批分量（腿已删）。gold_short 判据是 `gold + liquid − 批 ≥ line`，gold 完全可以同时 ≥ `g* + ρ + 刷价`——刷新照发、凑金被烧。逐轮推演：节点收入 → gold 越过 `g*+ρ+刷价` → 解锁支放行刷/买目标卡 → 金回落到线下 → stay_gate 仍 defer（批 40-84 金永攒不到线+批）→ 循环。原代码同帧是「双门同闭、金单调积累到线+批后升级发射」（追查件缺陷 #1 的旧形态），解锁支将其改造成「刷新烧金、升级永久 defer」的新形态。裁定 #5 的用户理由只覆盖②③支帧（「判断了停留就没有预留的必要」），①支+解锁支帧不在其文义内。
- 修正方向：设计须显式回答解锁支帧的资金序——（a）gold_short/凑金在途帧刷新让位（解锁支只覆盖 defer 无凑金帧）；（b）解锁支帧保留升级批预留（腿删除范围收窄到②③支）；（c）维持现稿并申报「升级可被搜索性支出无限期推迟」为可接受行为 + 给判读键。三选一须进详设并同步 landing 3.2 判据。

**G3｜R-3/A-11 删除面漏项 + 文件面契约破约：contracts.py 与 shop.py 消费位无主，扫描词表防不住**
- 位置：`details/hp-purge.md:21`（A-11 锚 = cw_intention.py:1067-1150/:1427-1530 + shop.py:373）、`:30`（R-3 处置②删 p2_supply_horizon/line_completion_feasibility/G 门残件）；总纲 `design.md:44-47` 文件面互斥契约（hp-purge 独占 = kernel 8 文件，**无 contracts.py/shop.py**）；landing `3.1` 文件面（:29，无 contracts.py/shop.py）、`3.2` 文件面（:43 含 contracts.py 但范围无 R-3 条目）。
- 直调核验的漏项面：
  1. `criteria/contracts.py:150`、`:327`（契约文本引用 hoard_target_set/三分支回退单一源）+ `:166-171`（`_k_projection_domain_full` 守卫 `k_fallback_source == K_FALLBACK_SOURCE_THREE_ARM`）——三分支判据（no_target_arms）退役后该守卫与文本全 stale，且 p2plus 带合法空集证据链（three_arm 证据）失去载体；
  2. `shop.py:373/:996`（乙分支 hub_names 消费在**买面段** shop-buy-reform 文件面内，hp-purge 的 A-11 无权触碰；shop.py 不在 3.1 文件面）；
  3. `cw_intention.py:1555-1603`（hoard_target_set p2plus 带 + `k_empty_window_fallback`——正本 12_line_and_intention.md §2 登记的 K 空窗回退单一源，现役消费 entry.py:480/shop.py:885/decision_payload.py:101）：A-11 锚区间（:1427-1530）不含此段，而「窗口内囤货退回候选 top3 缺件口径」的自然落点恰在此——改后语义（p2plus 带回退集来源、空集合法性）设计未回答；
  4. hp-purge §6 残留扫描词表（:44）不含 `no_target_arms|hoard_target_set|arm_a|k_fallback|K_FALLBACK_SOURCE` 词族——以上任何残件漏删扫描均放行。
- 修正方向：R-3 处置面补全上述四处锚并裁决文件面归属（contracts.py 归 3.1 或 3.2 范围补 R-3 行；shop.py:373/:996 归 3.1 契约例外或移交 3.3）；k_empty_window_fallback p2plus 带改后语义写进 R-3 处置；§6 词表补齐 R-3 词族。

**G4｜A-9（应急带归零链）归属三处互相矛盾，实现者无法确定执行批**
- 位置：`details/hp-purge.md:25`（B 组段把「cw_economy.py 应急带归零链（is_emergency → refresh_ev_budget）」列为**本篇范围**，且标注「照 hp 清查件 **B 组表**逐条执行」——清查件中它是 **A 组条目 A-9**（§1/§2.1），B 组表无此行，组别引用错误）；landing `3.1` 范围（:27「hp 清查件 A 组（**除 A-9 已定死腿归 3.2**）」）；landing `3.2` 范围与文件面（:41/:43，**无 A-9、无 cw_economy.py**）；总纲 `design.md:46`（cw_economy.py 归 hp-purge 独占）。
- 连带：A-9 删除面跨 `kernel/cw_economy.py:1074-1088/:1237-1275`（归 3.1 面 ✓）+ `economy_cycle.py:187/:29`、`statefn/odds.py:67`、`shop.py:327` 的注释/消费面（**不在任何详设文件面**）；hp-purge §6 词表不含 `is_emergency|emergency_hp|refresh_ev_budget`——跨面注释残留扫描防不住。
- 修正方向：三处统一（建议：A-9 归 3.1/hp-purge，landing 3.1 范围改回「A 组全量」，hp-purge §2 修正组别引用为 A-9；跨文件注释面点名进处置清单并补词表；或按现 landing 归 3.2 则总纲契约与 3.2 文件面同步补 cw_economy.py——但后者与 §2.1 互斥契约冲突，代价更大）。

### 中

**M5｜R-3 处置在同篇内自相矛盾——「关键取舍」未随二次裁定同步（写作硬规则 4 违例）**
- 位置：`details/hp-purge.md:30`（§3 推荐 = 视界**整条退役**，处置②含 G 门残件删除）vs `:49`（关键取舍「R-3 备选 = 视界整条删除（G 门也删）：**放弃**……只删 hp 项 = 最小治本面」）。
- 攻击：备选文本 = 二次裁定**之前**的旧推荐口径；总纲 §3 R-3 行与 hp-purge §3 已同步为「整条退役」，唯取舍段残留旧案。实现者读两段得相反指令（G 门删还是留）；且按 iteration-design 硬规则 4，修订后应 design↔details 全量反查，此为漏网实证。
- 修正方向：重写 `:49` 备选段——新备选应为「只删 hp 项（H 改剩余节点数、G 门保留）」，放弃理由换为二次裁定依据（锁定后不设换线、旧消费位停用、窗口极短）。

**M6｜新 ρ（停留目标卡价）在 P2 未锁定窗口无取值定义，「ρ 无需兜底」论断只对锁定支成立**
- 位置：`details/refresh-chain.md:33`（「停留目标为空的帧判据本就拒绝（no_star_target），ρ 无需兜底」）。
- 直调反证：`criteria/levelup.py:193-194`（unfinished_star_targets 未锁帧**恒返回空**）→ stay_target_of=None；而 `criteria/refresh.py:79-96` 未锁窗口分支在候选缺件命中时**返回 True 放行**（键 `unlocked_no_qualified_gap` 仅拒帧出现），`shop.py:1987-1995` 的 r2_budget 照达。未锁放行帧 ρ 取值 = ？（取 0 则未锁窗口丢卡价预留——行为变化未申报；取其他则来源未指）。裁定 #6 原文语境是锁定停留刷，设计把它移植到 `r2_card_reserve` 单一源（同时服务未锁窗口）时未处理该分支。
- 修正方向：ρ 定义补未锁帧语义（建议：未锁帧 ρ = 候选缺件集最低费卡价——与合格集旧口径同构；或申报未锁帧 ρ=0 的行为差），并补对应单帧测试进 refresh-chain §5 清单。

**M7｜「席可腾」第三腿（场上非线内件）与真值源域不符——裁定 #7 的析取支被静默收窄**
- 位置：`details/refresh-chain.md:18`（「fuel_sell_candidates 资格面非空（可卖一件腾出位——备战席燃料 ∨ 场上非线内件）」）、`:24`（已知余量把「场上无非线内件」列入几乎不可构造死态）；真值源 `mandate.py:392-407`（fuel_sell_candidates 输入域 = **bench 占席条目**，不含场上）；能力面边界 = 11_shop_decisions.md §4.0（店内禁卖场上，能力面边界）。
- 攻击：店内卖出场上件机械不可达，第三腿在发射帧恒 False——「席满 + 零 bench 燃料 + 场上有非线内件」帧按设计余量论证**不该**是死态（可经备战侧卖场上/换人腾位），按实现真值源**就是**死态。余量声明与实现口径不匹配，裁定原文腿被静默删减且无行为变化申报。
- 修正方向：详设如实申报——店内帧第三腿只有 bench 燃料腿，「场上非线内件」腿须明确为「关店后备战侧腾位可达」（与解拦复核机制衔接）或从条件中删除并申报与裁定 #7 的口径差。

**M8｜E 组毯式处置覆盖清查件逐条处置；R-4/R-6/R-7 未决裁决未进总纲决策点**
- 位置：`details/hp-purge.md:40`（「E 组 10 条测试锁：随删/重写」）vs hp 清查件 §2.6 E-9（**保留不动**——sim 0hp 保底机制锁，属 C-6 保留面）、E-2/E-6/E-8（挂 R-7/R-4 裁决）；`details/hp-purge.md:25`（B 组毯式「零消费孤儿直接删」）vs 清查件 B-9（cw_first_passage 全模块，「待裁决 R-6 附带……倾向保留为概率侧标定工件」）、B-11（待裁决 R-7）；总纲 `design.md:61-66`（§3 决策点仅登记 R-1/R-3）。
- 攻击：按毯式规则执行会误删 E-9（保留机制的测试）并把 B-9 顺势删掉（与清查件倾向保留方向相反）；按清查件执行则在 B-9/B-11/E-2/E-6 撞「待裁决」标记——而总纲无此三项决策点，实现者只能停手（硬规则 2 停手令必然触发）或自行拍板。裁定 #3 执行纪律（挂空/孤儿一律删）可覆盖 A-7/A-8（R-5），但 R-4（cw_opening_hp 属世界事实面、倾向保留）/R-6/R-7 的对象不是「挂空死码」，毯式纪律盖不住。
- 修正方向：hp-purge §2/§5 改为逐条引用清查件处置（或显式排除 E-9 与 R-4/R-6/R-7 对象并声明「维持现状、裁决另批」）；总纲 §3 或元信息登记三项未决裁决的指针与默认态。

**M9｜P92/门④删除面的登记残件与测试面缺位；landing 3.2 引用不存在的「§1 验收词」**
- 位置与直调证据：
  1. `criteria/contracts.py:283+`（`('refresh', 'all_channel_buy_exists')` 契约登记行）不在 refresh-chain §1 P92 删除清单（:23 列了函数/装配段/计数键/命题行/钩子行/正本段，漏契约行——违删除纪律「连根删」）；
  2. `test_no_target_three_arms.py`（锁 P86 三分支/甲分支 G 门逐字语义，R-3 改造必涉）不在 hp 清查件 E 组、任何详设或 landing 测试面；
  3. `details/refresh-chain.md:23`（§1）无验收词，landing `3.2` 完成判据（:48）却写「P92/危机不变式/R 族删除面残留扫描清零（refresh-chain 详设 **§1/§3 验收词**）」——§1/§2 均无词表，判据按文不可执行（W10 词族 `r1_commitment_account|r0_stop|r1_start`、P92 词族均需补写）；
  4. 同类：A-5 门④删除的契约登记面（清查件 A-5 明注 `criteria/contracts.py:243-246`、`criteria/__init__.py:54-55` 随删）不在 hp-purge 锚表与 3.1 文件面（contracts.py/__init__.py 归 3.2 面、范围无 A 组条目）。
- 修正方向：refresh-chain §1 补契约行/验收词/测试面三项；hp-purge A-4/A-5 行补契约登记锚并裁决其文件面归属（建议 3.1 契约例外，或明注归 3.2 范围增补行）。

**M10｜残留扫描的时点矛盾与词表不可满足：阶段判据与末阶段分工冲突、调查词族当验收词必产大量保留面命中**
- 位置：`details/hp-purge.md:44`（扫描范围 = src/ + sr-od-test/ + **docs/ develop 侧**；「残留申报清零 = 本篇完成必要条件」）vs landing `3.1` 范围（:27「D 组正本章删归末阶段」）与 landing 首节（:9「本阶段删除面对应验收词表残留扫描清零」）——3.1/3.2 完成时 docs/ 侧 D 组残留在，按篇级词表扫 docs/ 必不清零。
- 词表问题：hp-purge §6 词表 = hp 清查件 §5 **调查词族**（hp/血/crisis/blood/掉血/floor/濒死/保底 等宽词）∪ 8 符号——宽词与 C 组保留面（13 条不动：hp 读数链、hp_floor_triggered、hp_pay 遥测、P15）、λ 血带维（B-12 保留）、血本位 B-19（保留）、金 floor 词样结构性冲突，字面清零不可达；「残留申报清零」若指「申报后豁免」，豁免协议（谁批、登记在哪）未定义。
- 修正方向：分层——3.1/3.2 阶段判据 = 本阶段代码/测试面词表清零（符号级）；docs/ 侧扫描移到末阶段判据；§6 定义「保留面豁免清单」协议（逐命中登记豁免依据：清查件条目号），或把验收词表改为精确符号族 + 保留面白名单。

**M11｜正本更新清单不完整：清查件 D 组约 20 篇 develop 侧正本受影响，清单仅 12 行**
- 位置：landing `正本更新清单`（:93-103）vs hp 清查件 §2.4 D-1~D-30 与 §2.4 proofs 表（D-18~D-25）。
- 直调核验的缺行面（本迭代改动直接使其过期/须重写，清单无行）：`00_framework.md` §3 硬闸门授权面与 §4（清查件 D-1 明言「修裁定时本节须重写授权面」）；`22_prep_screen.md` §1 第 4 步「血预算线/资金线门类拒发同落零动作」（D-12）；`26_battle_settlement.md`（D-14）；`17_stall_form_spend_authority.md`/`19_reinforce_channel_and_survival_discount.md`/`21_opening_window_and_tool_consume.md`（D-8/D-9/D-11）；`strategy-docs/README.md`（D-16）；`flow/README.md`/`flow/action_ops.md`（D-27/D-28，随 B-7/decision_hp 与 R-1 联动）；`game_state/fields.md` 等（D-29）；`proofs/p28`（A-9 数学基座降级）与 `p24` 过期行（D-20/D-24）；`01_math_framework.md` §3.4 R2 门 ρ 口径行与 §5 状态函数表刷新判据行（清单 01 行只列命题行删除，未含 §3.4「ρ[合格集最低费卡价]」现行形态行——ρ 重定义后必 stale）；`04_survival_budget.md` §6-1（vd_p1/vd_p2 口径差核对项随 R-8 联动）不止 §7 一行。末阶段判据 = 清单清零，照单执行必漏。
- 修正方向：正本更新清单按清查件 §2.4 全量对表补行（每行标注处置：删/重写/核对不动），或清单行改写为「hp 清查件 §2.4 逐条 + 以下增补行」，把清查件 §2.4 收编为末阶段执行清单的合法引用源。

### 低

**L12｜追查件节锚错位（两处）**：`design.md:21`「追查件 §1.1 r2 帧」与 `details/refresh-chain.md:69`「追查件 §1.1（误拦案例）」——直调核验：三月七四臂够不着实况在追查件 **§1.2**（dseq97 逐臂拆解），P92 误拦三帧在 **§1.4**（dseq110/114/122）；§1.1 是 P2r1 帧表（无三月七、无 P92 拦刷）。依据锚节号须改为 §1.2/§1.4。

**L13｜危机不变式「旧层残件」锚不存在于现役代码**：`details/refresh-chain.md:40` 列删除对象 `crisis_invariant_lane`/`crisis_overflow`/消费门 `authorize_release_refresh`——全仓直调仅 `economy_cycle.py:24/:233`、`telemetry/schema.py:500` 三处**注释停用史引用**，符号零定义（清查件 A-9/追查件 §7.1 同口径「已停用零调用」）。删除面实为空；反而这三处注释残留不在 §3 验收词内（词表无 `authorize_release_refresh`），按删除纪律应入清单一并清。修正：§3 改写为「符号已不存在，清三处注释残留 + 验收词补 authorize_release_refresh」。

**L14｜R-8 未登记进总纲**：`details/hp-purge.md:39/:44` 以「game 侧随 R-8 裁决」为界——R-8 定义仅在清单裁决队列 R-4~R-9 行（`.debug/temp/2026-10-28_CW修复工作清单.md:123`）与清查件 §3，总纲 §0/§3 无指针。未决前默认态（只删 develop 侧）已定、不阻塞，但裁决载体应进总纲元信息或 §3 待决表。

**L15｜解锁支的取数通道未定**：`details/refresh-chain.md:35` 要求 refresh_warranted ①支消费 upgrade_gate_verdict 的 defer/gold_short 结论——未指明通道：判据内重调 = `levelup_*_defer` 拒因计数键双计（该门在升级意图出口已逐帧评估，23 号稿 §1「同帧一次评估」）；传参 = 判据单一源签名变更（`refresh_warranted(state, session)` 契约面、criteria/__init__.py 注册行随改）。实现者须自择，属「无需再设计」缺口（轻）。修正：详设指明复用同帧门判定结果（shop.py 已算 `_up_verdict`，作为实参传入或判据改为消费缓存值）并申报计数键处理。

**L16｜shop.py 文件面分段缺口**：总纲 `design.md:45-47`——买面段 ≈L200-1600 与刷新发射段 ≈L1950-2080 之间 **L1600-1950 未归属**（直调：dominance/C1 段至 :1958、M6 段 :1543-1616 跨 1600 边界）。本迭代无既知工作落在该带，但契约口径与代码实况不齐，后续修订易踩。修正：边界改为「买面段 = L200-1960（刷新提案段前）」或按符号域（六序/M6/C1/dominance 函数体）划界。

**L17｜清单单一源与扫描词表寄存 .debug/temp**：`design.md:30`/`details/hp-purge.md:25`（「清单单一源 = hp 清查件，本迭代不复制清单」）+ §6 词表引用清查件 §5——三份依据件（清查件/追查件/裁定清单）均在 gitignore 的临时区，寿命无承诺；落地批中途文件被清 = 照单执行与验收扫描失据。修正：迭代收编（复制进本迭代目录 details/ 或 `evidence/`，注明源头），或至少在 README 登记副本路径与快照 commit。

## 实际攻击过的面清单

1. **核一·无前提**：三详设逐阶段试读（3.1 按 hp-purge 照单开工 / 3.2 按 refresh-chain §5 终态伪码开工 / 3.3 按 shop-buy-reform 开工）；总纲 §1 改动面 ↔ 详设/landing 文件面覆盖比对（A-9/A-11/契约登记面/shop.py 分段）；跨详设接口契约（席可腾真值源域、停留目标单一源、刷新布尔语义、免费腿分工）逐条对代码核；landing 阶段七件齐与判据可执行性（验收词存在性、扫描时点、对照判读锚）。
2. **核二·规范遵循**：写作硬规则四条逐条（依据就地标注——全部 file:line 锚直调；无需再设计——试读撞点；无过程叙事——未发现违例；修订同步——M5 实证违例）；阶段小节七件（landing 五阶段 + 末阶段逐项核对，齐）；引用寿命分层（L17；design 引 .debug 件按任务判据源框架许可，但「单一源不复制」的寿命风险入档）。
3. **核三·治本**：§1 归层（语义层 hp-as-input + 约定层残件堆积）与方案对位核验——hp 判据族物理删除 = 修根 ✓、刷新链三组件 = 结构收敛 ✓、买面三修复 = 配合缺陷结构修复 ✓、W6/W7 挂账如实声明 ✓；同族第二次逐件修检查——本迭代为双线并治非逐件补丁 ✓（G2 的解锁支属「兜底加固」自认定位，但其交互未分析归核一）；未发现「第 3 件症状补丁」形态。
4. **数值/口径/引文/码点直调**：refresh.py 全文（r0_stop:22/r1_start:140/crisis_refresh_invariant:160/r2_card_reserve:236/all_channel_buy_exists:282-378/refresh_warranted 三支/`unlocked_no_qualified_gap`:96）；shop.py 关键段（免费腿 1963-1971/预留+腿 1981-1989/r2+P92+发射 1990-2063/_merge_pair_names:234/p92_seat_recoverable:267/missing:930/M2b+stockpile 1272-1333/hub_names 373/996/_r2_card_reserve:221）；levelup.py（unfinished_star_targets:174 未锁空支:193/stay_target_of:206/门序:300-306/门④:370-377/门⑥:385-392/level_spend_blocked:484-514）；cw_discipline_rules.py（:82-128/:154-209/:212-260）；cw_economy.py（blood gate :792-882/is_emergency :1074/refresh_ev_budget :1237-1275）；cw_intention.py（p2_supply_horizon:1067/line_completion_feasibility:1099/arm_a_*:1427/no_target_arms:1508/hoard_target_set:1530/k_empty_window_fallback:1576/停用申报:1180）；contracts.py（:150/:166-171/:243-246/:252/:255/:273/:283）；criteria/__init__.py（:54-55/:60/:62/:65/:76）；mandate.py（fuel_sell_candidates:392 域/序位声明:1078）；cw_comps.py:2862/cw_performance.py:244-268/cw_game_state.py:2954/cw_investments.py:473；math_proofs.md 行（P21:45/P36:60/P40:64/P54:76/P86:106/P92:113）；正本行（11:55/:58/:59/:110/:186、01:194、12:49-51/:68、23:10、04:66/:98-114、10:199、14:162、p37:188、flow/session.md:41-43）；skill 引用（sim-testing §一/「先知道边界」末条/「单局复盘素材采集」/cw_sim_match_drive、strategy-work §3/§4/§6、SKILL.md「测试分层」行）；测试面（test_levelup_prob_axis.py:310/:420/:499、test_shop_session_loop.py:658/:747、test_no_target_three_arms.py、test_seat_recoverable_narrow.py、全仓无 r2_card_reserve/test_cw_interest_floor 直引）；证据文件（清查件全篇、追查件全篇、修复工作清单全篇）；边界迭代（2026-10-28-supply-decision-wiring 五件套存在、范围相符）；research/economy.md §5-§7 hp 打法段。

## 核验为真（零发现）的面

- 总纲 §0 核心裁定 ①-⑤ 与清单裁定 1-7 的映射忠实；R-1 处置与 [40]② 定性（11:58）、宪法口径一致；R-3 事实链（12 §1.4 用户立场、撤销出口停用 cw_intention:1180、现役消费面）除 G3 漏项外主体成立。
- hp-purge A 组表锚与清查件 §2.1 逐条一致（A-1/A-2 合行、A-3~A-11 全命中）；B 组/C 组边界引用与清查件组表基本对齐（除 G4/M8 所列）；C 组「hp_floor_triggered 保留」锚 :2954 命中。
- refresh-chain：三分派与 refresh_warranted 现状描述准确；目标可买三腿中两腿（空位/合成）与机制吻合（merge §2.5 满栏例外）；P92 整门删除清单的函数/装配段/计数键/命题行/钩子行/正本段六类锚全部直调命中；R 族死码清理锚（:22/:140/contracts:252/:255/__init__:60/:62/:65/:301）全命中；金线闸算式与裁定 #6 文义一致、`no_star_target` 拒帧前提对锁定支成立。
- shop-buy-reform：need_star 口径与 unfinished_star_targets 语义一致；「达标成员显式停买」与 need_star「追到底」语义自洽（达标=完成的读法成立）；W11 负结果记忆与 2026-10-12 不用期望裁定不冲突的论证成立；免费腿 9999 证据（cw_investments:473 + shop.py:1963-1971）直调属实。
- landing：阶段七件齐、依赖序合理（3.2←3.1、3.3←3.2、3.4←全）、对照判据锚（追查件 §1 逐帧表、11:186 基线行、g_20261028_011013 存档）真实存在；A/B 挂起声明与 sim-testing 现状一致；prereg 硬门清单与 strategy-work §6 对齐。
- 边界事实：supply-decision-wiring 独立迭代真实存在且范围（补给接线）与「不并入」声明相符；W6/W7/W9 挂账与清单一致。
- 无过程叙事违例；README/四节结构合规。
