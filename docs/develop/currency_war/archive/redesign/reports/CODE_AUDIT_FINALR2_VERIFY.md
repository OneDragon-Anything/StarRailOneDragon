# 终审 R2 修复批(9 条)对抗式核实报告(VERIFY-FINALR2)

> 审计者立场=假设修复有假,逐条 grep+读码核实落点语义、逐条跑声称的回归锁、抽 2 条做「修复不存在」反向实验;攻不破的角度才写「核实过」。
> 核实基线 = 当前工作区(含并行在飞改动,git status 有多文件 M 态)。本报告只写此文件,未改任何代码。行号以审计时工作区为准。
> 已知前序核实:同目录 `CODE_AUDIT_VERIFY3.md`(另一轮验证)已覆盖九条+终审残留;本报告为独立复核,结论以其为准不抄,分歧处显式标注(见 §三.3)。

---

## 一、九条核实表(落点 / 锁 / 反向验证)

| # | 修复声明 | 落点核实(语义读码) | 回归锁(亲跑) | 判定 |
|---|---|---|---|---|
| 1 | **P1 败局页连败供给**:battle_loop `_record_round_outcome` telemetry_only 分支,killed 门后写 `session.last_streak`(OCR 带符号直采/未读按连败累积递减) | **存在且语义正确**。`operations/battle_loop.py` L586-592 = killed 门(只落显式败局行,防位面过渡页伪行);L593-602 = 修复本体,且在 killed 门**之后**(误入同形屏不写,语义正确):`_obs.streak` 非零直采(L598-599),读到 0 时按连败语义递减——负值继续 −1、非负转入 −1(L600-602),与「带符号 连胜+/连败−」口径一致。胜页链路经 on_round_end(shell L296)不变 | `test_loss_page_streak_via_battle_loop_harness`(test_cw3_prep_wiring.py L795-852):battle_loop 级 harness(绑真 `_record_round_outcome`,只桩 OCR/recorder),断言 -1→-2 累积、OCR 带符号 -5 直采。**亲跑绿**(该文件 38/38 passed) | ✅ 真修 |
| 2 | **P2 输入统一**:镜像 board 喂入改 `cw_battle_calib.board_factions_of`;对拍锁全链恒等;PREREG v4 行 | 调用点 `strategy_shell.py` L398-405:`_dep_objs` 逐员过 `normalize_char_name` 后喂 `board_factions_of(_dep_objs)`——与旧层兜底门(`decision_v2/phase.py` L109)同一派生函数,state.board 全集口径不再喂镜像;注释如实申报旧侧谓词差(三件套/豁免/轮门)。`cw_battle_calib.py` L324 导出 `board_factions_of` 别名。PREREG v4 行在 `.debug/temp/currency_war/redesign/PREREG_cw3_vs_legacy_AB.md` L102(输入口径双层同尺限定+旧侧谓词差申报+种子统计口径申报) | `test_formed_chain_input_unified_with_legacy_board_source`(L547-581):deployed 名单→board_factions_of→engines_count 全链,与旧层 32 随机板面恒等 + flows-only(卡芙卡)输入分歧可见性断言。**亲跑绿**。⚠️ 锁覆盖缺口见 §三.1 | ✅ 真修(锁为函数级,见保留项) |
| 3 | **P3 种子配额执行点入账**:shop.py BuyCard 落地分支 + sim 应用分支才扣;计划拒/改判自然返还;两连调锁 | 三处核实:①计划时点**不再写 session**——`strategy_shell.py` L515 只读计数,L548-549 帧内预占 seed_budget(局部变量),全仓 grep `cw3_second_seeds_bought` 写点仅 3 个(reset×2 + 执行点×2);②`operations/prep/shop.py` L916-921:BuyCard 落地后按 `'second_system_seed' in action.reason` 入账,注释「计划被拒/改判不消耗配额」(返还=计划时不扣的隐式形态,语义达成);③`sim/engine_p1.py` L1156-1161:同判据入账。reason 判据与发射段 L669 前缀严格对齐 | `test_seed_quota_committed_only_on_execution`(L855-874):两连调(计划→重判)后配额仍 0、重判仍出种子、手工 +1 后不再计划。**亲跑绿** | ✅ 真修 |
| 4a | **归一全链**(族 B 锚/线计数/种子判定 + 半角点二级兜底,真点名「银狼LV.999」不受改写) | ①族 B 通道:归一上移到锚构造点 `strategy_shell.py` L780-787(`_anchor_state_from_obs` 对 bench/deployed 全员 `normalize_char_name`,注释「消费点不再各自打补丁」);②线计数 L507-508 `normalize_char_name(d.char_id) in line_roster`;③种子判定 L525 `seed_name = normalize_char_name(card.name)`;④主链 held L409-412、classify L157/L203 均归一;⑤`classify.py` L63 变体表(•/・/﹒/．)+ L67 半角 `.` 二级兜底,L78 真点名守卫(`out in CHARACTERS` 命中即原样返回——「银狼LV.999」注册表真名不受改写,逻辑核实成立) | `test_normalize_full_channel_variant_names`(L916 起):四变体等价 + `normalize_char_name('银狼LV.999')=='银狼LV.999'` + 形变名族 B 锚换位链。**亲跑绿** | ✅ 真修 |
| 4b | **种子金门 liquid 口径** | `strategy_shell.py` L519-521:门分量改 `liquid_left = gold_liquid - batch_reserved`,L529 判 `liquid_left >= s_floor + card.cost`;逐笔买入同步扣 liquid_left(L547),卖退金同步回补(L586/L614)。与 decide_levelup 的 `gold_liquid`(L388/L455)同尺;裸金 `gold_left` 仍留给买入金门(L543),各归其位 | `test_seed_gold_gate_liquid_basis`(L877-888):裸金 0+活期垫件,liquid(2) < 息线(50) → 关门。**亲跑绿**。注:锁只覆盖「liquid 不足关门」半边,「liquid 足开」半边由锁 2(gold=4000)间接承载 | ✅ 真修 |
| 4c | **空 core 线满编臂** | `strategy_shell.py` L509-513:窗口臂加 `bool(core)` 前置(列车/DOT core=() 时「窗口全覆盖」不再 vacuously true),空 core 线只能走满编臂 `line_on_board >= max_units`;注释如实记录该裁决语义 | `test_seed_exit_empty_core_line_requires_full_board`(L891-913):列车2 线,板未满→不触发;线成员满编→触发。**亲跑绿** | ✅ 真修 |
| 5a | **持久索引清理** | 点名三处已清:`strategy_shell.py` L461 旧「审计 P4」注释、L388「A/B 二轮归因」、docstring「p41+[31]」、`classify.py` L95-96「A/B 二轮归因」——全仓 grep 无残留。⚠️ 新修复注释引入了「终审 P1/P5」引用(battle_loop L593、strategy_shell L496),指向 `.debug/temp` 审计文件,见 §三.4 | 无专锁(注释卫生无行为锁,不适用) | ✅ 落实(带 §三.4 残留注) |
| 5b | **L5 依赖声明对齐** | `strategy_shell.py` L5 改为「包布局守卫 LEGAL_EDGES 只准消费 data/kernel/knowledge」——与 `test_cw_package_layout.py` L54 `LEGAL_EDGES` 实际矩阵一致(该守卫测试在 cw_quick 内,**亲跑绿**) | 同左 | ✅ 真修 |
| 5c | **crisis reason 三态** | `strategy_shell.py` L599/L615-620:三态 = 有卖带明细 / `no_sellable_fuel_bench_protected`(席满无可卖)/ `seats_freed_by_making_room`(腾席链已腾出位);`decisions['crisis']` 无条件落盘(L640-646) | `test_crisis_gate_judged_but_no_sell_observable`(L644-660)锁第二态;`seats_freed` 第三态**无专锁**(grep 测试无引用)——落码正确,锁缺 | ✅ 真修(锁缺一态,见 §三.2) |
| 5d | **cap 帧 batch 遥测记 0** | `strategy_shell.py` L652-659:cap 截断帧 `decisions['levelup']['batch']` 置 0、reason=`cap_cut_batch_defer_bank`、action 改判 defer_bank;资金预留同步回滚 L478-479 | 截断改判半边有锁(`test_level_cap_guard_stops_clicks` L635-637 断言 defer_bank,**亲跑绿**);`batch: 0` 字段值**无专锁** | ✅ 真修(字段值锁缺,见 §三.2) |
| 5e | **种子统计口径并入 v4 申报** | PREREG v4 行③:种子按序 1 提报、reason 前缀/seed 旗标可辨、按 order 聚合的分布统计自本版起含注入——申报文本与落码(`decisions['buys']` L672-674 带 seed 旗标)一致 | 文档申报,无行为锁(不适用) | ✅ 落实 |

## 二、反向验证(抽 2 条,均「构造修复不存在的输入」确认锁会红)

1. **P1(剥除修复实验,运行时完成、零文件改动)**:`inspect.getsource` 取 `_record_round_outcome` 真源,剥除 L593-602 修复块(剥后源码确认无 `_obs.streak` 写入、无递减兜底),exec 编译为替身方法,套用锁的同一 harness(OCR 桩返 streak=0、killed=False,连败场景)→ `last_streak` 保持 0,锁断言 `== -1` **失败(锁红)**。结论:该锁真实钉住修复本体,不是自证恒真的桩锁。
2. **P3(旧缺陷形态注入实验)**:包一层 `decide_prep` wrapper,在计划时点把种子数写回 `session.cw3_second_seeds_bought`(等价旧代码「计划时点无条件入账」),复刻锁的板面(gold=4000、满编+缇宝)两连调 → 断言 1(计划后计数==0)实测计数=1 **红**;断言 2(重判仍出种子)实测种子计划=0 **红**。结论:锁的断言对「入账时点」敏感,计划时点回归必被抓。

## 三、不一致项 / 保留项(攻破的角度)

1. **P2 对拍锁是「函数级」而非「调用点级」——声称的「全链恒等」锁存在一处覆盖缝**:`test_formed_chain_input_unified_with_legacy_board_source` 验的是「board_factions_of 派生 → formed_systems 与 engines_count 恒等」,但**没有任何断言钉住 `strategy_shell.py` L402 这个调用点**。反向推演:若调用点回退喂 `state.board` 全集口径,`test_form_telemetry_mirror_written` 的正例(仙舟3+列车2,两口径同 2 体系)与负例(乱破,无羁绊,两口径同 0)在两种口径下**同样通过**——即输入口径回归(恰是终审 P2 抓的那条缝)无测试会红,目前只靠读码钉住。落码本身核实正确;判「修真、锁窄」。
2. **两个观测尾巴落码无锁**:`seats_freed_by_making_room`(第三态 reason)与 cap 截断帧 `batch: 0` 字段值均无任何测试引用/断言;各有锁覆盖的只是邻接半边(crisis 第二态、defer_bank 改判)。回归时这两处可静默丢失。
3. **与前序 VERIFY3 报告的一致性**:结论方向一致(九条全闭、终审残留全闭);但 VERIFY3 未指出上两条锁覆盖缝。本报告按对抗立场补记,二者不矛盾。
4. **持久索引的模式级残留(新引入)**:本批修复自己的注释引用了「终审 P1/P5」等审计批号(battle_loop L593、strategy_shell L496 等),审计文件本体在 gitignored 的 `.debug/temp` 下。与仓内既有的「Wxxx 审计 Px」注释惯例同族(项目现状普遍如此),判存量模式而非本批回退;但按终审 P7 自己的标准,新写注释继续引入这类引用 = 该模式仍在自增殖。
5. **P1 递减兜底是近似语义**(OCR 读不到 streak 时按连败累积递减,可能漂离真值)——注释已如实声明,非失实;仅提示哨兵/判读消费时知悉。

## 四、L1 快速集复跑(亲跑,`uv run pytest @sr-od-test/cw_quick.txt`,421s)

**3311 passed / 3 failed / 4 skipped / 1 xpassed**。3 红与在册存量对照:

| 失败用例 | 在册归属 |
|---|---|
| `test_cw_star_form.py::test_calibration_anchor_r1_in_band` | ✅ 在册(流水 2026-09-01 02:38:「star_form 统计带 1 红=语料与旧带错配的存量项」) |
| `test_cw_w614_sim_fidelity.py::TestZeroDriftAnchor::test_default_path_behavior_digest_unchanged` | ✅ 在册(流水 01:20/01:57:w614=旧树行为摘要锁,登记随批 1b 消亡) |
| `test_cw_equip_grant_calib.py::test_p1_grant_volume_matches_real_profile` | ⚠️ **未能确证在册**:单独复跑仍红(可复现);流水账只写「3 红存量名单」未点名该条(早期在册的 realization_chain 现已不红)。工作区存在大量并行在飞改动,可能=在飞批或装备λ标定待办相关——**建议编排者做一次归属核查**,不能默认计入在册 |

## 五、总判

**九条全部真修落码,声称的回归锁全部真实存在且当前绿;两条反向实验证明关键锁(P1/P3)对修复本体敏感非摆设。** 保留项均为「锁窄于修」而非「修假」:P2 调用点口径、两个观测尾巴字段、`seats_freed` 第三态无锁;另有一红(equip_grant_calib)归属待核查。不构成 A/B 放行的反向证据,与 VERIFY3 的「合同防线先行」建议不相冲突。
