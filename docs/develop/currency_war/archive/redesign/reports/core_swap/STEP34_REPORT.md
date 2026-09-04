# CW 换核迁移序 步3+步4 合并批 交付报告(mandate_v1 新核本体落码)

> 规格单一源:`design/IMPL_DESIGN.md` §6.4-R(R189-6 步3[R191 修注:statefn
> 输入缝挂 mandate_v1 内部,不加生产接线步]+步4[R189-4 结构签名/R189-5 修复池
> 落点表/④-3 四函数位]);`design/CONTRACT_SERIES_DECISION.md` **v2 已冻结**
> (2026-09-03 用户批准;§3.2 备战线域 17 类逐类表+§3.3 fail-closed);
> `core_swap/FIXPOOL_EMITTER_DIGEST.md`(14+1 项)、`BATCH0_RESLICE_INPUT.md`、
> `SIM_CONSUMPTION_MAP.md`(A/B 约束)。cw4 步2 件(statefn 8+audit 3)本批
> 只消费;禁改数值语义——本批对 cw4 既有件仅动了 `audit/provisional.py`
> 的**槽位登记表**(加 2 槽,见解释性裁量 #3),数值语义零变更。

## 1. 规格条款对照表(逐件 → 条款出处)

| # | 实现 | 文件 | 条款出处 |
|---|---|---|---|
| 1 | proof 四函数位:should_switch(复用 `cw_line_switch.should_switch_e` 比较器,参数=provisional 槽位解析序→`dataclasses.replace` 解析实参 registry 视图调用,比较器签名不加重载/文件本体零改动;θ/D_min/δ 任一 None ⇒ 不评估+`theta_unavailable` 分键)+证据门 P38(序数形态,阈值【拟】未立禁自造数值门)+stop_buy(R4-F8 函数位;R10-5 纯分类谓词,评估对象恒为该帧生效 K,逐备战期重评)+signal_arm(§2.7.1 S0──信号──▶S3;R11-3 两臂同开) | `decision/cw4/proof.py`(新) | §6.4-R R189-1 ④-3;R192 修注;R24-2;R9-2/R11-1/R10-5;§2.7.1 |
| 2 | 线级状态机(共根组 3):`LineState`(dwell/drought/evicted 回锁禁止窗)——D-A45 干旱计数「手上目标件存量 ≥1 ⇒ 重置」+D-P4 切线滞回(撤线窗口内同线回锁阻断) | 同上(`update_line_state`/`register_eviction`) | R189-5 D-A45/D-P4 行;FIXPOOL §3 |
| 3 | mandate 执行器:M5→dominance_buy→M2(→M4 重试环)→M1→M3→M1′→M6→M7 单帧闭环;四硬约束检查点 ①-④(唯一合法拦截集,封闭);M2→M4 重试 ≤B=9、M4 0 发射立即放弃;dominance/M6 席位失败单帧单评不入环(R12-2/R21-4);fuel_sell(P41 零参数,mandate 邻位,bench_effect_qualified 豁免);动作标记 mandate=True(R14-4) | `decision/cw4/mandate.py`(新) | §3.1/§3.2/§3.3;R8-8/R11-5;R12-2/R21-4/R32-3;§2.2 fuel_sell 行 |
| 4 | entry 三遍编排(证明 pass→升档器求值位→骨架 pass→EV pass)+`emit`(R189-4 结构签名形态;Emitted 载体带 mandate/funding_support 标记)+升档器求值位(R27-1②;None 期=结构位+影子计数,R29-1/R36-2 两态真表述)+StartBattle 序列终点 | `decision/cw4/entry.py`(新) | §3.1 执行序;R189-4;§2.0-3 |
| 5 | 发射器帧稳定截断 `truncate_frame_stable`:契约 v2 §3.2 备战线域 17 类逐类判(机器可读分类表)+§3.3 fail-closed(词表外/无分类 ⇒ 截断+`emitter_unknown_action_truncated` 计数披露;ClickSpheres 掉箱不可静态预测 ⇒ 保守截断;4 退役类兼容面保守判=截断点;BailToOuter 终点) | 同上 | 契约 v2 §3.2/§3.3;R195 症2(权威=v2 定稿正文) |
| 6 | criteria 七面:buy(ev_buy_candidates/ev_buy_veto 发射面一体+p2_lock_buy 占位)/sell(line_switch_sell/sell_for_interest/funding_support_sell 支付支撑通道)/levelup(arm2_schedule 门+spend_unified[P48 整买纪律=D-BUYNOTE 收编]+batch_form/lv9_stop/pop_slot[D-lv7])/refresh(r0_stop/r1_start/r2_budget/crisis_refresh_invariant+hard_node_reinforce_gate[D-D])/stockpile(stockpile_buy)/equipment(wear_release[D-B 三态]/affix_allocation[D-F46]/keep_policy/endgame_context[D-P3]);**BYPASS_TABLE=§4.2.1 臂①旁路集函数级枚举表单一源**(22 行,类别合法值含 R7-1 第四类「发射面」) | `decision/cw4/criteria/`(新,7 文件) | §2.1-2.6 落码映射;§4.2.1(R5-4/R7-1/R9-1/R10-3/R11-3/R38-5 完备性口径);R189-5 |
| 7 | bridge:CwStrategy 子类 `MandateV1Strategy`(STRATEGY_ID='mandate_v1')实现契约接口;**步3 内部装配缝**:decide_prep_screen 内部消费 `prep_brain.assemble`(读同一黑板 prep_obs_frame,④-5 单一源;幂等/单一写端/快照纪律保持;不加生产接线步);观察帧缺失抛错。**依赖矩阵合规分拆**:obs→Snapshot 装配半部在 app 桶(decision_assembly),decision 桶禁依(adapter 分拆先例)——决策本体=bridge.decide_from_turn 纯函数(decision 桶),装配链由注册桥壳 MandateV1Live 覆写 `_assemble_turn` 注入(app 桶) | `decision/cw4/bridge.py`(新)+`strategies/mandate_v1_strategy.py`(新) | §6.4-R 步3 R191 修注;R189-0;契约 §1/§5;test_cw_package_layout LEGAL_EDGES |
| 8 | 注册桥(照抄 DecisionV2Live 模式,__module__ 守卫壳子类) | `strategies/mandate_v1_strategy.py`(新) | R189-2 免做④ |
| 9 | config strategy_id 值域扩 {'decision_v2','mandate_v1'}(构造期校验+save 持久化)+ev_arm 开发字段({'skeleton_only','full'},R1-1) | `currency_war_config.py` | §4.1;R189-2 改造① |
| 10 | manager 校验文案(合法值=decision_v2/mandate_v1) | `decision/cw_strategy_manager.py` | 同上 |
| 11 | ev_arm 遥测:DecisionTrace.ev_arm 字段(schema 末尾追加可选)+recorder extra pickup+ledger_hooks 判栈改 **(strategy_id, ev_arm) 二元组**(mandate_v1 分栈 `mandate[skeleton_only/full]`;ADR-0245 新栈不盲跑 coldstart) | `telemetry/schema.py`/`recorder.py`/`sim/ledger_hooks.py` | R1-1;§4.1;任务书第 5 项 |
| 12 | 遥测键登记(design_telemetry 键节仅加键行):新登 7 键——ev_arm/switchline_event/emitter_unknown_action_truncated/m2_retry_exhausted/dominance_bench_wait/m6_overflow_strand/signal_arm_direct(theta_unavailable/switchline_skipped/switchline_exit_blocked/advisor 族已在册零重登);索引行同步 | `design/design_telemetry.md` | 契约 v2 §3.3(键名归遥测登记纪律,契约禁成第二登记源) |
| 13 | A/B 接线:双臂工厂 `make_core_swap_arms`(两臂同 `sim_decision_registry()` 派生,新核 registry 属性带上)+零漂移门 `zero_drift_gate`(同 seed 同池 SimResult.ledger 逐位相等) | `sim/ab_core_swap.py`(新) | SIM_CONSUMPTION_MAP ③/Q3(rng 中立/环境恒等/零漂移门先于 A/B);任务书第 7 项 |
| 14 | 测试(验收①-⑥ 全项) | `sr-od-test/test/sr_od/app/currency_war/test_cw4_mandate_v1.py`(38 用例;零漂移门入慢桶) | §6.4-R 步4 验收行 |

## 2. 修复池 14+1 项逐项落点与检查点核销(R189-5 表)

| 项 | 落点(本批实现) | 核销状态 |
|---|---|---|
| D-B 装备穿着释放 | `criteria/equipment.wear_release` 三态门(简易件即穿/里程碑收窄释放/强敌节点释放);M7 消费 | ✅ 三态各一测(TestFixpoolCheckpoints.test_d_b_wear_release_three_states);**P7 对账先决呈报**:key 装备需求 sim 零激活两读未定谳(口径合法恒空 vs 死代码)——本批按「分层规则穿」实现,深度定谳挂步6 前接线批(OPEN 保持) |
| D-D 硬节点补强门 | `criteria/refresh.hard_node_reinforce_gate`(节点类型语境输入,P26/P40 接线形态) | ✅ 门函数+类别入 BYPASS_TABLE;数值加权(Δp_prep)挂标定 |
| D-F1 选卡生存折现 | pick 接口辖外(契约 §0)——登记接口占位 | ⏸ 呈报:选卡 eval 折现待 pick 面收编批(与 D-FM2 同批候选) |
| D-C44 部署输入契约 | `mandate.MandateFrame`=黑板全量现读,每帧重建(bench_free/deploy_vacancy 现读派生) | ✅ test_d_c44_fresh_read_frame |
| D-A45 干旱计数事件 | `proof.update_line_state`(存量 ≥1 ⇒ drought 重置 0) | ✅ test_d_a45_drought_reset_on_holding |
| D-F46 词缀装备分配 | `criteria/equipment.affix_allocation`(weakness ⇒ 主输出优先凑满 3 件) | ✅ 函数落位;OPEN=sim 定谳保持(单局候选);carry 识别以已穿件数代理(呈报 #4) |
| D-dup 场上 dup 估值 | `mandate._deployable` 消费 `vopt.dup_power_qualified`(步2 已落) | ✅ test_d_dup_not_deployable |
| D-FM1 金→战力出口 | M6 义务存在性(g*>饱和线∧无 S 目标)+dominance_buy 资格门(参数化 g*,R70-1)+OpenShop 意图载体;濒死孤注=升档器血线解锁包(None 期结构位) | ✅ 结构落位;F2 主指标待 A/B(步6) |
| D-FM4 成型位面语义 | `proof.stop_buy`(位面分档由 K/update_target 承载)+`criteria/levelup.pop_slot` | ✅ 谓词形态锁(test_f4_metric_with_indicator_set);**F4 度量**:成型判定=stop_buy 谓词非 form_ok 单门,随指标集呈报(度量重采随步6) |
| D-FM2 P1 末窗承接 | `criteria/equipment.endgame_context`(r_remaining≤3 语境输入) | ✅ 语境谓词落位;OPEN=量级以实机为准(保持) |
| D-P2idle 带金闲置 | entry 发射面组织+决策迹 reason 字段(逐发射显式理由;无候选 vs 全拒由 reason 键可辨) | ✅ 先决(候选生成日志)=Emitted.reason 载体;判读消费随步6 |
| D-P3 收尾终局投资 | `criteria/equipment.endgame_context`+levelup/equipment 消费位 | ✅ 语境输入;OPEN=实机 boss 掉血对拍定谳(保持) |
| D-P4 切线滞回 | `proof.LineState.evicted` 回锁禁止窗+θ/D_min 比较器滞回 | ✅ 结构+测试(test ④);F3 主指标待 A/B |
| D-F9 二引擎节奏 | 干旱计数面(D-A45 同骨架)+criteria/buy 档窗口 | ✅ 骨架共享;trio3 OPEN 挂对账(保持) |
| D-lv7(OPEN) | `criteria/levelup.pop_slot`(满编+富金+候补 → 升 cap 意图;不触发显式理由进决策迹) | ✅ test_d_lv7_pop_slot_explicit_reasons(四理由分支);[33] 覆盖核查=判据合法不触发路径有显式理由 |
| D-BUYNOTE 整买纪律 | `criteria/levelup.spend_unified`(XP 仅整批够升级放行)内嵌 M3 | ✅ test_d_buynote_spend_unified |
| (附)三个新增对拍计数提议 | placed_after_buy/带金零动作轮/干旱重置计数 | ⏸ 随步6 指标集呈报裁定(FIXPOOL §5 附注,账本未登记——不擅自立) |

## 3. 验收数字(全实测)

- **①四硬约束检查点各一例**:TestHardConstraints 4 用例 ✅(①金/整批合计、②bench_full/board_full/同名同星、③S 预留边界、④线内件禁卖)。
- **②臂①旁路集函数级枚举对拍**:TestBypassEnumeration ✅——ast 扫 criteria/* 全部公开函数位(12 函数)逐一命中 BYPASS_TABLE(22 行);类别合法值 8 类;谓词/状态函数/判据/结构不变式恒不旁路;支配族(dominance/fuel)在 mandate 邻位臂①不旁路。
- **③截断契约锁**:TestTruncateFrameStable ✅——17 具体类逐类判型断言(continue 2/conditional 5/terminal 1/truncation 9[含 ClickSpheres 保守截断+4 退役类]);PREP_ACTION_TYPES 词表穷尽无 unknown;截断点/终点必在末位;§3.3 词表外动作(Rogue 类)截断+计数=1。
- **④fail-closed None 槽位**:TestFailClosedNoneSlots ✅——θ/D_min/δ 任一 None ⇒ theta_unavailable 分键(禁复用 switchline_skipped/exit_blocked,三因可辨断言);臂① ⇒ switchline_skipped;u/V_ms None ⇒ switchline_exit_blocked(K 冻结);T_SEARCH_A None ⇒ M6 不买+m6_overflow_strand;line_switch_sell None 期不卖;ev_buy u None 空候选。
- **⑤修复池检查点核销表**:见上节(14+1 全行有落点;4 项 OPEN 保持原判未擅动)。
- **⑥商店线零漂移门**:`zero_drift_gate(n=20, seed_base=0, pool='snapshot')` → **{n:20, mismatches:[], ok:True}**(SimResult.ledger 20/20 seed 逐位相等;单条 13.93s,入慢桶)。新核未接商店线=证明零污染成立;prep 等价门不适用新核(非适配器,契约 v1 §1 口径)。**新核冒烟**:探针语料 6 形态帧(常态/bench 满/富金/球/箱/空)× 双臂 ev_am 跑 `decide_prep_screen` 无异常,输出全部 PrepAction 且截断判符合 v2(截断点/终点恒末位);黑板 None 帧抛错。
- **⑦快速层**:CW 域 `pytest sr-od-test/test/sr_od/app/currency_war -m "not slow and not legacy_baseline"` → **2327 passed / 0 failed**(2 skipped 系既有 skip;含本批 38 快速用例);ruff 改动文件全过(autofix 后 0 error)。
- **锁更新(锁的存在性纪律,锁红≠改动错)**:两枚钉旧注册面的锁按 §6.4-R 值域扩重推——`test_cw_strategy_planner.py::test_builtin_registry_is_decision_v2_only` 与 `test_cw_gradient_switch.py::test_strategies_discoverable` 改钉封闭集 ['decision_v2','mandate_v1'](锁注释注明重推依据);`test_cw_package_layout` 依赖矩阵锁驱动桥分拆重构(见上表 #7),矩阵本体零改动。
- **A/B 双臂可跑实证**:`make_core_swap_arms()` 返回 (DecisionV2Strategy, MandateV1Strategy),两臂同 sim_decision_registry() 派生、新核 registry 属性在;零漂移门绿=双臂同底座可跑。**本批未跑正式 A/B**(步6 判读批)。

## 4. 解释性裁量清单(拿不准的规格点,先呈报后落;参考步2 的 5 项先例)

1. **mandate_v1 商店线=冻结基线透传**(最重裁量):本批 MandateV1Strategy 继承
   DecisionV2Strategy,decide_shop_screen/update_target/pick 族=基线原样透传
   (基线本体零改动,§4.1 不违)。依据:①SIM_CONSUMPTION_MAP Q1(sim A/B
   证明面=商店波;decide_prep_screen 在 sim 零调用)——商店线不透传则 sim
   双臂无可比经济行为;②criteria 七面的商店线接线(EV 候选/付费刷新/压库
   发射面挂进 decide_shop_screen)规格未给接线批定位,任务书第 7 项只要求
   「双臂可跑+零漂移门绿」;③零漂移门(验收⑥)以透传实证零污染。**待裁**:
   商店线接线批的排期(建议步6 判读批前的独立接线批,否则臂② 的
   criteria EV 面在 sim 无行为载体)。
2. **P16 滞回 δ 槽位补建**:R23-5「θ/D_min/δ 同槽登记」,步2 只建了
   THETA/D_MIN(DELTA_PRIOR 系窗口平移量,R34-4 撞名不同义)——本批在
   provisional.py 补 `DELTA_HYST` 槽(缺位会使 should_switch 解析序两读)。
   同批补 `P_LAMBDA_QUANTILE`(R28-1 p【拟】,升档器求值位载体)。两处均
   缺口闭合、非数值语义变更;呈报确认。
3. **M2 买入意图的 prep 帧载体=OpenShop(read_only=False)**:PrepAction 词表
   无买牌动作(买牌=商店线 Action 族),线成员买入/dominance/M6 的买意图在
   prep 帧以开商店意图承载(截断点,序列收口,商店线执行实际购买)。与
   执行序 §3.1 一致(骨架发射意图,商店循环落地)。
4. **D-F46 carry 识别以「已穿件数」代理**:主输出位标记(comp 知识 carry
   字段)未在 COMP_LIBRARY 落位,本批用已穿件数排序代理凑满通道;精确
   carry 识别随 comp 知识批。
5. **M5 开局板辖域=round_num≤1 ∧ 板空**:「开局」帧定义规格未给轮次边界,
   取位面内第 1 轮(M5 数学状态=无数学按 comp 知识执行,载体=RunDeploy
   现读重建)。
6. **signal_arm 可判定载体=session.active_strategies ∩ {'黑塔纪元'}**:直通线
   信号谱其余成员(圣杯契约/万敌数量/昼神速度流)的 obs 层观测面未落
   (PrepObservation 无对应实体字段),本批只接①类策略驱动信号并计数
   `signal_arm_direct`;K 直通锁线沿用 update_target 的投资策略偏置通道。
   信号谱补全挂 obs 层批。
7. **runner.py 让路**:git status 见并行未提交改动(步1/步2 批),A/B harness
   落新模块 `sim/ab_core_swap.py`(零侵入);runner 正式合流入口待裁。
   同因未动的并行修改文件:decision_assembly.py/prep_brain.py/
   cw_screen_prep.py/cw_strategy.py(本批全部只读消费)。
8. **ev_arm 生产 extra pickup 半边**:DecisionTrace/ledger_hooks 判栈已落;
   cw_screen_prep(冻结面)把 ev_arm 写进决策行 extra 的生产接线因让路未做
   ——mandate_v1 的 cw4_counters 已在 session 侧累积,接线为 cw_screen_prep
   一行 extra 追加,随让路裁决批补。

## 5. 检查点时间线

- 2026-09-07 批内:规格通读(IMPL_DESIGN §1/§2/§3/§4.2/§6.4-R + 契约 v2 +
  FIXPOOL/SIM_CONSUMPTION/BATCH0 + STEP1/2 报告)→ proof.py 落码 →
  criteria/ 七面+BYPASS_TABLE → mandate.py → entry.py(截断发射器)→
  bridge.py+注册桥+config/manager → ev_arm schema/recorder/ledger_hooks →
  design_telemetry 键登记(仅加键行)→ sim/ab_core_swap.py → 测试 38 用例
  全绿(零漂移门 n=20 mismatch=0,13.93s 入慢桶)→ ruff 全过 →
  CW 域快速层(后台,结果见下)。
- 快速层结果(终态):`uv run pytest sr-od-test/test/sr_od/app/currency_war -m
  "not slow and not legacy_baseline"` → **2327 passed / 0 failed / 2 skipped**
  (136.7s);首跑曾 3 红(两枚注册面旧锁+依赖矩阵)均按锁语义重推消解
  (见 §3 锁更新条);零漂移门慢桶复跑 1 passed(12.7s)。

## 6. 约束自检

- 让路规则:目标文件中并行未提交改动者(runner/decision_assembly/
  prep_brain/cw_screen_prep/cw_strategy/decision_v2 系)全部只读,零编辑;
  本批编辑的既有文件(currency_war_config/cw_strategy_manager/schema/
  recorder/ledger_hooks/design_telemetry/provisional[加槽])批前均无未提交改动。
- redesign 文档仅加键行(design_telemetry 键节 7 新键+索引行;其余零触碰)。
- cw4 步2 件数值语义零变更(唯 provisional.py 加 2 槽位登记,呈报 #2)。
- 契约 v2 正文零触碰;截断判实现按 v2 §3.2 备战线域表逐类落。
- 本批不跑正式 A/B;不 git commit。∎
