# 转型域换人通道统一设计 无前提对抗审查报告

> 审查对象：本目录 `design.md` / `landing.md` / `README.md`（状态：对抗审中）。
> 审查纪律：干净上下文、无前提、三核并重（无前提 / 规范遵循 / 治本核验）；数值/口径/引文/码点一律直调复核，as-built 断言读代码体（docstring 仅线索），行为可达性拿复盘报告真实牌面逐帧推演。
> 判据源（直调自取）：`docs/develop/harness/iteration-design.md`、`skills/sr-od-currency-war-dev/references/strategy-work.md`、strategy-docs/00/01 宪法、`proofs/math_proofs.md`（P61/P78/P79/P87/P88/P89 行）与 proofs 单篇、注册表（`data/cw_factions.py`/`data/cw_chars.py`/`kernel/cw_comps.py`/`kernel/cw_merge_simulate.py`）、现行换人机器（`kernel/cw_deploy_logic.py` 全 1784 行、`kernel/cw_launch_admission.py`、`kernel/cw_intention.py`、`kernel/cw_merge_simulate.py`）、策略层（`strategies/impl/mandate_v1/mandate.py`/`entry.py`/`deploy_plan.py`/`criteria/sell_candidates.py`/`sell_gate.py`）、复盘报告 `.debug/currency_war/deep_review/g_20261026_203023.md`、flow/screens 正本、02/11/14/17/18/22/24 号篇。

## 总判定：**需修订**（2 阻断 + 6 应修 + 4 低；阻断不排除不得定稿）

---

## 一、发现清单

### A1【阻断】victim 序首键度量域未钉死——锚①「Saber 换青雀·槽位序唯一推导」在 P79-4 注册度量下被证伪

- 位置：`design.md:90`（§2.7 锚帧复验）、`design.md:111`（§2.10 锚①）；`kernel/cw_deploy_logic.py:1695-1708`（现行排序处）、`:1701-1702`（首键 = `swap_yield_contribution(ctx.target_factions, …)`）；`proofs/math_proofs.md:101`（P79-4 注册度量域 =「`target_comp.all_factions` ∪ SWAP_GUARD_SYSTEMS 并集各档 achieved 档数下降量」）。
- 推演（复盘报告 `g_20261026_203023.md:2605/2618` 真实牌面：板上 吉/青雀/远坂凛/停云/爻光，羁绊计数 圣杯×2、能量×2、战技点×2、仙舟×3、欢愉×1）：
  - 现行 victim 序首键 = 档边际贡献（P79-4 让渡序，码点 `:1701`）。按 P79-4 注册度量域（all_factions ∪ guard）：移除**青雀**（仙舟+战技点，`cw_chars.py:112`）掉两档——仙舟 3→2（`cw_factions.py:53` tiers (3,5,7,10)，achieved 1→0）+ 战技点 2→1（`cw_factions.py:94` tiers (2,4,6,8)，achieved 1→0）= 贡献 2；移除**爻光**（仙舟+欢愉，`cw_chars.py:133`）只掉仙舟一档 = 贡献 1。升序排序下**爻光先于青雀**，贪心配对将发出 **Saber 换爻光**，锚①「Saber 换青雀（…槽位序推导唯一）」不成立。
  - 锚①只有在首键度量域 = 终局键集 {命运圣杯, 能量}（此时青雀/爻光贡献同为 0，槽位序才唯一推出青雀：deployed 扫描序青雀 scan=1 先于爻光 scan=4）或「终局键集 ∪ guard」（两者同为 1，同上）时成立。
- 根因：§2.3.1 退役键集收窄五消费位，但 victim 序度量消费的 `ctx.target_factions` **不在五消费位清单**（`locked_redeploy_target_keys` docstring 列的五位 = offtarget-② / swap_sell_exclusion_reason 宽口径归因 / is_tgt / _bench_is_target / post_sell_offline，`cw_deploy_logic.py:540-543`）；退役后该度量喂什么口径，设计全文未钉。按「现行机器 victim 序」的字面继承（= P79-4 注册式）锚①必挂；§2.10 锚②预测表同染此歧义。实现者的四种合理读法中两种保锚、三种挂锚（终局键集 / 键集∪guard 保锚；all_factions∪guard / 收窄键集残留 / all_factions 全量挂锚），无文本裁决。
- 修正方向：§2.7 显式钉死 victim 序首键的度量域（建议 = 终局键集档位梯，零过渡体系项），并按 §2.9 对 B_t 的同款纪律声明与 P79-4 注册度量域的关系（迁移改写或语义边界申报，禁双源漂移）；若维持 P79-4 口径则锚①改为 Saber 换爻光并重推唯一性。

### A2【阻断】行为差申报④「pair 帧 fenced off-target 件路径保持现行」与其自引码点 `:1025-1032` 相互矛盾——按设计自身的退役指令无法兑现该申报

- 位置：`design.md:119`（§2.11 申报④，自引 `cw_deploy_logic.py:1025-1032` 为「pair 帧基准」）；`cw_deploy_logic.py:1025-1031`、`:979`、`:586-601`；`landing.md:25/34`（3.1 范围与完成判据引用申报④）。
- 事实（读代码体）：`:1025-1031` 是**关门分支**——locked 帧不满足旧域谓词（`_trans=False`）时 fenced 件返 `fenced_arm_closed`。pair 帧当前 fenced off-target 件**可卖**的真正通路是 `_trans=True`（旧域 `locked` 含配方对锁腿②，`cw_deploy_logic.py:582-583` + `SwapPlanContext.locked` 字段注 `:1104-1109`）时**绕过 `:1025` 落入 `:1032` 资格族承接**。设计退役 `_swap_transition_domain`、新判别子显式排除 p1_pair（§2.0）后，pair 帧新域=False → `:1025` 分支命中 → 常量退役后恒 `fenced_arm_closed` → pair 帧 fenced off-target victim 池静默清空，**申报④声称保持的「fenced 件资格族可卖的现行形态」恰好被该分支关死**。
- 后果：双轨域配方完成件分支（§1「明确不解决、原样保留」）的 victim 池收窄（fenced off-target 件不可再为完成品腾位），与申报④直接冲突；3.1 完成判据「pair 帧 fenced off-target 路径保持现行（申报④）」无设计内可实现判据——实现者按退役指令机械迁移 = 违反申报④，按「保持现行」补特例 = 违反 §2.0 单一源纪律（各层自备第二套域谓词），两头都无文本授权。
- 修正方向：显式钉死 pair 帧 fenced victim 判定谓词的归宿（例如：让位白名单同样适用 pair 帧并申报该行为差；或声明 fenced-victim 通路保留旧混轨 `locked` 域腿作为**具名第二谓词**并写明两谓词的各自适用范围），同步 `landing.md:25/34` 判据。

### A3【应修】`evolution_swap_arm_trigger` 的域腿对账义务未入设计——代码自声明「域定义变更时本谓词须随对账，禁静默分叉」

- 位置：`design.md:73`（§2.3.1 退役面清单不含该消费位）；`cw_deploy_logic.py:1319-1363`（`:1358` 内联 `locked ∧ fp<1.00 ∧ board_full` 三腿；`:1352-1353` 对账自声明）。
- 事实：演进降级换人分支触发谓词内联自己的域腿（未消费 `_swap_transition_domain_of`），并在 docstring 明文要求「域定义变更时本谓词须随对账」。本迭代正是域定义变更（判别子换腿①单轨），但 §2.3.1 的消费位迁移清单与 landing 3.1 范围均未提它：实现者保留其消费混轨 `locked` 字段 = 行为原样（合规但设计未申报该归置）；改接新判别子 = pair 帧演进武装消失（未申报的行为差）。两条路无文本裁决。
- 修正方向：§2.3.1 增一句显式归置（建议：`evolution_swap_arm_trigger` 域腿维持消费 `ctx.locked` 混轨 = 双轨域原样申报，并注明与新判别子无共享单一源是**已申报的两谓词分界**）。

### A4【应修】门 2 保留面含 `fenced_arm_closed`，与转型域「纯过渡件含 fence 件可卖」的 C1 解锁点矛盾

- 位置：`design.md:40`（§2.2 门 2：「资格族（…/ `fenced_arm_closed` / …等拒因面保留」）；`design.md:45/55`（一级 victim = 纯过渡件 / 情形 A 放行）；`cw_launch_admission.py:44`（DEPLOY_FENCE = RECIPE ∪ ENGINE）；`cw_chars.py:112/133`（青雀/爻光均含仙舟 = fence 成员）。
- 矛盾：锚帧一级 victim（青雀/爻光）都是 fence 件——现行机器里 fence 件在转型域可卖恰恰是**绕过** fenced 分支落资格族（`:1032` 承接注释），`fenced_arm_closed` 在旧转型域内本就不可达（仅板不满/fp 缺读边沿帧触发）。设计的双门转型域里纯过渡件 victim 走白名单一级放行，`fenced_arm_closed` 若按「保留面」字面移植回转型域，A 情形（Saber 换青雀）被该拒因直接封死，C1 解锁点失效。保留面清单与枚举表 A 两处文本不可同时成立，取舍未写。
- 修正方向：§2.2 门 2 明确 `fenced_arm_closed` 在转型域**无角色**（仅双轨域/域外帧保留），或把该拒因从转型域保留面移除并注明 fence 维由白名单取代。

### A5【应修】landing 3.1 文件面缺 `mandate.py`——「arm 分键新键族写入断言」的写点在该文件

- 位置：`landing.md:27`（3.1 文件面 = cw_deploy_logic.py / cw_launch_admission.py / deploy_plan.py）；`design.md:73`（§2.3.1「arm 标注分键归宿…换新键族（bond_gate_* 四键 + victim 序来源键）；`cw4_m1p_arm_pending` 归因透传载体保留」）；`strategies/impl/mandate_v1/mandate.py:1522`（`_count('swap_arm_transition_trigger')` 分键写点）、`:1532`（`cw4_m1p_arm_pending` 写点）、`mandate_state.py:252`（载体字段）。
- 事实：arm 分键的遥测写点全在 `emit_swap_redeploy`（mandate.py）。3.1 范围含新键族落地与写入断言，文件面却不含 mandate.py（它归 3.2）——worker 依 3.1 文件面开工完不成 3.1 判据，越面改又违反文件面纪律。阶段粒度规范（iteration-design §3.1：判据依赖另一阶段未完成部分 = 划分不当）同判。
- 修正方向：mandate.py（emit_swap_redeploy 分键段）入 3.1 文件面；或把分键新键族整体移入 3.2 范围并在 3.1 范围声明边界。

### A6【应修】§2.8 全局不变式与溢出告警自救豁免冲突：「标签命中件不可经卖出通道离场（板侧与 bench 侧一致）」不成立

- 位置：`design.md:97-99`（§2.8 堵回降口二 + 全局单调论证）；`strategies/impl/mandate_v1/sell_gate.py:886-915`（装配 A 身份段构成）；`strategies/impl/mandate_v1/entry.py:611-617`（第 0 步自救态序「资格仲裁族全通道豁免、线内件按价值序末位让位」）；`proofs/math_proofs.md:100`（P78 行自救扩展面豁免 = P78-1/P78-4/P78-7 全通道豁免）。
- 事实：新排除落装配 A 身份段后覆盖全部 FACE_REGULAR 通道 ✓，但自救通道**整族豁免装配 A**——溢出告警帧 bench 侧标签件仍可卖，「bench 侧一致生效」与「标签命中件不可经卖出通道离场」两条全称表述均被自救通道证伪。若反过来把新排除纳入自救豁免族，则保命通道对标签件的容量收窄 = 一处未申报的行为差（自救是止损通道，收窄须显式裁定）。单调论证本身可救（自救不卖板侧件 → 「板上支撑数非降」仍真，收敛论证只需「板侧非降 + 换人触发严格增」两段式），但设计未做这层切分，前提表述与豁免机制直接相抵。
- 修正方向：§2.8 二选一并写明——①新排除入自救豁免族（申报自救容量收窄为接受的行为差），或②不入豁免族（把不变式改述为「板侧支撑数非降 + 换人触发结构量严格增」，撤回 bench 侧全称表述并注明自救豁免边界）；P78 行改写内容（§2.9 已列）随本裁定同步。

### A7【应修】正本更新清单缺 `strategy-docs/11_shop_decisions.md`（§4.0 卖出候选评估器）

- 位置：`landing.md:94-108`（正本更新清单无 11 号稿行）；`design.md:98`（§2.8 自认「引文单一源：无关角色定义 = 11 号稿 §4.0 场景表」）；`strategy-docs/11_shop_decisions.md:116-129`（§4.0「卖出候选评估器（全部卖出场景的单一入口）」场景表，资格列 = 常规面描述）。
- 事实：3.3 改装配 A 身份段构成 → 全部 FACE_REGULAR 场景（升级凑金/节末凑息/来金 session_funding 等）的资格语义随之变化，§4.0 场景表是这些场景资格面的正本描述。迭代收尾义务（AGENTS「双层文档流」：代码实现后更新正本）对该文件缺行，清单清零 ≠ 正本与实现一致。
- 修正方向：正本更新清单增 `strategy-docs/11_shop_decisions.md：§4.0 场景表资格列（装配 A 身份段新构件） ← 3.3`。

### A8【应修】门 1③「同名升星横换」的必要条件未钉死；victim 全序中名单让位对（3(a)/3(b)）的位置未定

- 位置：`design.md:38`（门 1③ 正文只写「换入件星级 > 被换件星级」）；`design.md:59`（D 情形按同名口径举例）；`design.md:90`（§2.7 两级序只排一级/二级）；`design.md:47`（§2.2.1 通道 3 名单成员让位）。
- 两处语义选择无答案（iteration-design 硬规则 2「实现者无需再设计」直接违例）：
  1. **③ 是否要求同名**：不要求 → 任意星级升横换（如 2★ 纯过渡件换 1★ 纯过渡件，零终局结构收益）都过门 1，触发面显著超出「转型收益」语义；要求 → 正文与括号判据需写明同名条件。枚举表 D 的行名暗示同名，正文未钉。
  2. **名单让位对在 victim 全序中的位置**：两级序只定义一级/二级；3(a)/3(b) 的名单 victim 排何处（二级之后？与候选配对时专项尝试？）未钉。「首个可行组即停」的结果依赖该全序——D 情形（板上有更早槽位的纯过渡件且该配对过门 1 却被同名去重拦下）的最终选择随序变化。
- 修正方向：门 1③ 写明「同名」是否必要条件（建议：必要，与 3(a) 让位通道对齐）；§2.7 补一行 victim 全序（建议：一级 → 二级 → 名单让位对，同层内现行三键）。

### A9【低】§2.6 窗口辖域的 as-built 表述与代码体不符（无依据标注）

- 位置：`design.md:85`（「外部凑档件无 `entry_signals` 登记 = 不受窗口辖（辖域定义 = 知识卡 entry_signals…）」）；`strategies/impl/mandate_v1/entry.py:281-345`。
- 事实（读代码体）：窗口拦截真源 = `_deploy_window_blocked`（`:325-345`）——辖域是「纯终局件谓词」（终局库成员），**缺行 = fail 恒假**（`:283`「缺行 fail 恒假」），即解锁帧的终局库成员缺 entry_signals 行 = 受辖恒关，恰与设计表述相反；锁定帧外部件不受辖的真实机制是 `:340-342` 锁定线外豁免（非「无登记」）、方向线成员豁免是 `:336-338` 过渡/方向配方成员腿。新判别子域恒为锁定帧 → 结论侥幸成立，但表述的机制错误且无依据标注（as-built 断言读代码体，此处未读）。
- 修正方向：§2.6 改述为「锁定帧：名单成员经 `:336-338` 豁免、非名单件经 `:340-342` 锁定线外豁免，两腿均不受辖；解锁帧终局库成员缺行 = 恒关照旧」，并补码点依据。

### A10【低】关键取舍「OR 承接阵容成型 ①②③全不中」全称断言过宽

- 位置：`design.md:130`（取舍「门 1 纳入成品腿 vs 独立保留完成品分支」）；`design.md:60`（G 情形）；`cw_comps.py:603`（SEELE_OR_LEGS）、`:825-831`（希儿 comp：required=希儿、or_legs 全承接）。
- 事实：希儿本人入板 = 名单成员，victim 非支撑件时门 1②（支撑数严格增）**同样命中**；放大器入板跨贝 2/量 2 档时①也命中。「①②③全不中」只在「换出件同为支撑件」的形态下成立。④的必要性结论不受影响（该形态确实存在），但取舍依据的全称表述失真，正本化时会把错误论证带进动机段。
- 修正方向：改述为「存在 ①②③ 全不中的完成形态（换出件同为支撑件时的希儿入板），故仍需 ④ 承接」。

### A11【低】landing 3.1「deploy_plan.py（up 侧三消费位）」定位失真

- 位置：`landing.md:27`；`strategies/impl/mandate_v1/deploy_plan.py:186`（is_tgt 在此 ✓）；`cw_deploy_logic.py:1712`（`_bench_is_target`）、`:1750-1757`（`post_sell_offline` 底线）——三处中两处在 cw_deploy_logic.py 的 `select_swap_plan` 体内。
- 事实：文件面覆盖未漏（cw_deploy_logic.py 也在清单），但括号注把三消费位全归 deploy_plan.py = 码点标注错误。
- 修正方向：括号注改为「deploy_plan.py:186（is_tgt）；cw_deploy_logic.py select_swap_plan 体内（_bench_is_target / post_sell_offline）」。

### A12【低】3.1 与 3.2 完成判据重复计同一组算法测试面

- 位置：`landing.md:38`（3.1「组算法测试（两级 victim 序锚帧复验…超员降级；无可行组零动作稳态）」）与 `landing.md:51`（3.2「组算法单帧测试（含超员降级、无可行组零动作稳态）」）。
- 事实：同一测试面在两个阶段的验收凭据中双计，两阶段各自声明对同一判据负责，验收时归属不明（且 3.2 依赖 3.1，判据复述不产生增量验证）。
- 修正方向：组算法测试面归属 3.1（判据宿主），3.2 判据改为引用 3.1 已验面 + 只增发射/放行接线专项。

---

## 二、实际攻击过的面清单

**核一（无前提）**
1. §1 问题陈述与 §2 边界完整性：C1 立案原文（复盘 `:3634`）、同病第一件补丁出处（`required_swap_arm_pending` docstring `:769-770` = 2026-09-18 sim 实证）、02 号稿 §1「部署 0/934」（`:12`）——三处引用直调属实；「明确不解决」清单与 §2 各节改动面对账（买入面 C2 / sim 结算 / 经济升级本体均被正确排除；§2.7 组算法与执行形态落在「§2.0–§2.8」范围指针内）。
2. 依据就地标注逐条直调：`committed_authority` 腿①②（`cw_intention.py:1606-1630`，配方锁帧返 True 属实）；板满门 `:775`/`:1666-1668`；fp<1.00 语义 `:545-547`/`:991`；`swap_sell_exclusion_reason` 义务集/新鲜度/资格族闭集（`:933-938`，拒因面与 §2.2 列举一致）；`SWAP_GUARD_SYSTEMS` = 四体系+护盾（`:124-125`+`:502-505`，GUARD_SYSTEM_TIERS 三羁绊+希儿系）；victim 序三键（`:1695-1708`）；`select_swap_plan` 单对形态（`:1750-1755`）；`_swap_victim_yields_for_swap_in` 量席让位（`:871-894` + `:997-1004` 注）；P79-3 三轴（`mandate.py:838-895`：轴① bench∩membership、轴② `_deploy_advances_form`=Δfp>0，与 §2.5 描述一致）；`offtarget_sell_allowed`（`cw_launch_admission.py:55-89`）；`is_field_irrelevant_unit` = 仅覆盖有档件（`sell_candidates.py:385-390`）、装配 A 消费面 `:559-564`、`sell_gate.identity_exclusions :886`；来金族 FACE_REGULAR/POOL_BENCH_ONLY（`:177-196`）；演进分支 star_guard 让位（`:1045-1061`）；`cw_merge_simulate` 合成 3 合 1 全场域/场上同名同星 ≤1（场载体不被消耗 → 板数不减）。注册表标签逐条核对 `cw_chars.py:106-181`（吉尔伽美什/Saber=圣杯+能量；开拓者·记忆/藿藿含能量；瓦尔特/符玄不含；停云=仙舟+能量；远坂凛=圣杯+战技点；**青雀=仙舟+战技点恰在 ：112**；爻光=仙舟+欢愉非圣杯非能量）与 `cw_factions.py` 档位表（圣杯 2/3/4/5 `:67`、能量 3/5/7/10 `:93`、战技点 2/4/6/8 `:94`、护盾 2/4 `:96`、仙舟 3/5/7/10 `:53`）；双王圣杯（`cw_comps.py:1022-1066`：core_chars=k_members、form_tiers={圣杯3,能量5}、flex=[列车/战技点/治疗/盛会]、shared=core 子集、教义「哪怕下远坂凛都不能拆能量」`:1034`）；SEELE_OR_LEGS `:603`、form_progress 承接契约 `:1792-1856`。
3. 试读（实现者视角逐阶段）：3.1–3.5 + 末阶段逐节过「凭这份能否开工」——产出 A1/A2/A4/A5/A8（详见发现清单）。
4. landing↔design 一致性：设计依据节号全部存在；文件面路径全部真实存在（含 `skills/sr-od-currency-war-dev/scripts/cw_sim_match_drive.py --seed` `:118-119`）；prereg 实体清单五线载体逐条核对（math_proofs P89 行 `:110` 约束段、02 §8 命题 A `:97-99`、11 升级基线 `:186`、FM-1 `:185`、T-115 裁定在案）；P61 清理引用面逐一核对（math_proofs P61 行 `:83`、P87 行 `:108`、P78 行 `:100`、p63 `:7/:52`、p87 单篇 `:8`、p88 `:98`、p89 `:60`、出口生存余量 `:17/:62`、14 号篇 `:602`（P61）/:385（B_t）、18 号篇 `:117/:140/:182`（装备域占位编号=同号异命题属实）、`cw_launch_admission.py:215`、`mandate.py:861` 邻域 B_t、`flow.py:136-147`、telemetry `schema.py:419-421`）；24 号稿「22 §1 第 5 步」漂移属实（`24_deploy_segment.md:11` vs `22_prep_screen.md:34/36`）；projection_contract §4.3（`:105`）与 `cw4_m1p_arm_pending` 载体（`mandate_state.py:252`）在案。
5. 设计内多处置文本两两对账：判别子三合取 ↔ §2.3.1 退役面 ↔ landing 3.1 范围（产出 A2/A3/A5）；门 2 保留面 ↔ 枚举表 A/§2.3 守恒切分（产出 A4）；§2.2.1 白名单 ↔ §2.7 两级序（产出 A8）；§2.8 不变式 ↔ P78 自救豁免（产出 A6）；§2.11 申报①–⑥ 与关键取舍逐条核（申报①触发轴/victim 轴覆盖性推演通过；申报④产出 A2）。
6. 行为可达性逐帧推演（真实牌面）：2-1 开店前帧（entry 十段序：第 5 步开店先于第 6 步部署调整，`entry.py:9-14/:1022`——bench 阿格莱雅（能量标签=外部支撑件）换青雀在该帧不可达，锚时序成立）；2-1 开店后帧（锚①主帧：换入序 Saber 先、门 2 逐件核——青雀非 fresh/1★/非素材对/非义务集，远坂凛受 `same_star_count=2` 保护与 §2.4 核验一致、停云二级、吉为名单不可让——门 1①② 数值复核圣杯 3=二阶/能量 3=一阶）；现行机器 C1 死因逐步复演（四 victim 全被 engines_guard/target_keep 封死，§1 根因叙事机械成立）；OR 承接阵容形态与档位梯形态分别推演（G/E/F/D 情形逐一核；E 瓦尔特换符玄全不中属实、F 守恒拒属实、D 经 name_dup 拦截后让位可达性成立但依赖 A8 未钉全序）；bench 侧/板侧标签件在装配 A 机制下的卖出可达性（产出 A6）。

**核二（规范遵循）**
- iteration-design.md：四节齐（§0/§1/§2 ✓，单文档方案合规）；landing 七件齐逐阶段核 ✓（常规检查首节自包含 + prereg 硬门 ✓）；README 构成 ✓；写作硬规则：依据标注（A1 锚帧复验、A9 窗口辖域两处未标注/错标）、无需再设计（A1/A2/A8 三处「看情况」级缺口）、无过程叙事（三件正文未发现违例）；修订后全量同步复查视角的引用锚/路径/清单核对见核一第 4 条（A7/A11 为该步产出）。
- strategy-work.md：§1 零调参（门 1/守恒/白名单判据全为注册表与结构计数，无新自由参数 ✓；§2.10 行为锚点验收 = 宪法第 1 条合规 ✓）；§2 改前四步（判读上局=复盘立案 ✓、读全玩法文档=research README `:82` 单一源在案、定位两问=§1 归层 ✓、设计先行 ✓）；§3 开关纪律（无新增开关；`SWAP_TRANSITION_ARM_ENABLED` 退役 = 存量清理 ✓）；§6 对抗循环与 prereg 完整性硬门（landing 首节+实体清单 ✓，盘点义务声明 ✓）；§5 单帧测试纪律（landing「断言写语义」「禁机械跟绿」✓）。

**核三（治本核验）**
- §1 归层成立性：以现行代码逐帧复演 C1（触发谓词真 → victim 全封死），确认封堵点分布在守恒层（engines_guard 仙舟档）与资格层（阵营视图 target_keep）两处且判据对象/折法不一——「语义层+约定层」归层结论**成立**。
- §2 修根判定：双门+白名单把多层独立判据收敛到单一判定原则，属约定层根修；跨件半问有显式回答（第二件 → 架构级统一，双轨域保留有爆炸半径取舍申报）——治本方向成立；但 A1/A2/A4 表明统一在 victim 序度量域、pair 帧域谓词、fence 维三个接缝处**未收敛完**，恰是本报告要求补钉的面。
- 同族逐件修检查：非——本迭代自身即跨件半问的升级产物；双轨域不动已显式申报理由。

## 三、结论

- **阻断 2 项（A1/A2）、应修 6 项（A3–A8）、低 4 项（A9–A12）、存疑 0 项。**
- A1 直接击穿验收锚①（设计自己的行为判据在其自引的 victim 序语义下不唯一且被证伪）；A2 使「双轨域零行为差」申报在自引码点下不可满足。两阻断不修复不得定稿；应修项均为低成本补钉（各一句话/一行清单级），修复后按 iteration-design §5.4 全量同步复查一遍 design↔landing↔README。
