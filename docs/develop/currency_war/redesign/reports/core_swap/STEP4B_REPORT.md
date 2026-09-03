# CW 换核 步4b 商店线 criteria 接线批 交付报告(mandate_v1.decide_shop_screen)

> 规格单一源:`design/IMPL_DESIGN.md` §6.4-R(§4.2 发射面/§4.2.1 旁路集/
> R189-5 修复池落点表)+ `design/CONTRACT_SERIES_DECISION.md` **v2 已冻结**
> (§3.1 商店线域截断表+§3.3 fail-closed;词表=cw_state.Action 族)+ `core_swap/
> SIM_CONSUMPTION_MAP.md`(sim 消费=engine_p1:937 decide_shop_screen;rng 中立/
> registry/零漂移门先于 A/B)+ `core_swap/FIXPOOL_EMITTER_DIGEST.md` §3(商店面
> 经济项验收判据)。cw4 步2/步3+4 已落件本批只消费不改数值语义;STEP34_REPORT
> 裁量 #1(商店线=冻结基线透传)由本批接线兑现拆除。

## 1. 规格条款对照表(逐件 → 条款出处)

| # | 实现 | 文件 | 条款出处 |
|---|---|---|---|
| 1 | 商店波决策本体 `decide_shop_wave`:方向(K=session.target_comp/stop_flag/干旱计数)→ 预算投影(cap_resolved 现读→g*=10×cap_resolved 参数化[R70-1]、S 预留=b_target 单一源、逐动作金/席位静态投影)→ 骨架 pass(M4 腾席→M2 线成员买入→dominance_buy→M3 升级整批→M6 溢余)→ EV pass(臂①旁路集=§4.2.1)→ 截断/排序 | `decision/cw4/shop.py`(新) | §4.2 发射面规格(entry 三遍编排商店侧投影);§3.1 执行序;§3.4 |
| 2 | 商店线截断发射器 `truncate_shop_frame_stable`:BuyCard/LevelUpShop=可续;拖拽族(SellBench/SellDeployed/DeployMove/SwapDeploy)=条件续(槽位下标恒稳,ADR-0316/0392);RefreshShop/CompTransaction=截断点;**合成触发**=买入使同名同星持有(bench∪deployed 保守全域)达 3 ⇒ 该买牌后截断+`shop_merge_trigger_truncate` 计数;PickEvent(pick 返回载体,§3.1 词表源对账声明辖外)与词表外类型 ⇒ §3.3 fail-closed 截断+`emitter_unknown_action_truncated`(步3+4 已登记键,复用零新键) | 同上 | 契约 v2 §3.1 逐类+§3.3;SIM_CONSUMPTION_MAP Q2(break-redecide 同语义) |
| 3 | bridge 接线:`MandateV1Strategy.decide_shop_screen` 覆写为 cw4 商店波(黑板=session.shop_state_frame 唯一输入;缺帧抛错);**update_target=透传声明**(规格未给 cw4 战略层新形态——证明层线选择在 prep 三遍内、sim 消费的战略层钩子沿用 decision_v2 意向状态机;继承即透传禁自创,R189-1 ④-2② 基线零改动同款);pick 族/生命周期钩子缺省透传 | `decision/cw4/bridge.py` | 契约 §1/§5;SIM_CONSUMPTION_MAP Q1(sim 消费=update_target+decide_shop_screen 两钩子);任务书第 3 项 |
| 4 | sim 可驱动性:零局内 rng 消费(test_rng_neutral 直测 getstate 恒等);registry 属性继承自带(Q3 坑位①);ev_arm=config 字段读取(非法值回落 full,R1-1) | shop.py/bridge.py | SIM_CONSUMPTION_MAP ③-1/③-5 |
| 5 | A/B 门组(`sim/ab_core_swap.py` 重写):`baseline_self_pairing_gate`(decision_v2 自配对 n≥20 ledger 逐位相等——透传拆除后基线臂零污染证明)+ `arm_diff_probe`(小 n 双臂相异存在性证明+ledger 可读性锚);旧 `zero_drift_gate`(两臂逐位相等)随透传拆除**不适用新核**,删除并在 docstring 声明 | `sim/ab_core_swap.py` | SIM_CONSUMPTION_MAP ③-2/③-3;任务书验收④⑤;runner.py 让路(并行未提交改动,harness 维持本模块零侵入) |
| 6 | 遥测键登记:design_telemetry 键节加 9 键(shop_ev_u_unavailable/shop_ev_shop_domain/shop_ev_no_candidate/shop_ev_all_vetoed/shop_r1_ev_unavailable/shop_wave_idle_gold/shop_hard_node_gate_open/shop_drought_reset_on_buy/shop_merge_trigger_truncate)+索引行同步(22→31 节) | `design/design_telemetry.md`(仅加键行) | 契约 v2 §3.3(键名归遥测登记纪律,契约禁成第二登记源) |
| 7 | 测试 32+2 用例(新 32 快速+2 慢桶;旧 TestZeroDriftGate 锁重推为基线自配对,锁的存在性纪律) | `sr-od-test/.../test_cw4_shop_line.py`(新)+`test_cw4_mandate_v1.py`(改 1 类) | 任务书验收①-⑥ |

## 2. 修复池商店面经济项核销(R189-5 落点表商店面项,验收判据=FIXPOOL §3)

| 项 | 本批落点 | 核销 |
|---|---|---|
| D-FM1 sink+濒死孤注 | 支配买通道(金>g* ∧ stop_flag ⇒ 全额可退 1★ 买入;test_d_fm1_sink_channel_open)+M6 溢余存在性(fail-closed None 期不买+计数);濒死孤注=升档器血线解锁包(None 期结构位,步3+4 已落) | ✅ 结构+测试;F2 主指标待步6 正式 A/B |
| D-D 硬节点补强门 | `hard_node_reinforce_gate` 商店波消费(节点∈{encounter,boss} ∧ 金≥守息线 ⇒ `shop_hard_node_gate_open` 计数;正反例测试) | ✅ 观察级接线+测试;Δp_prep 数值加权挂标定批(FIXPOOL 原判保持) |
| D-P2idle 带金闲置 | 决策迹分键三件:`shop_ev_no_candidate`(无候选)/`shop_ev_all_vetoed`(全拒)/`shop_ev_u_unavailable`(缺输入)+`shop_wave_idle_gold`(gold≥10 零动作波);三测试 | ✅ 先决(候选生成日志)+可辨分键;A/B 指标集收录归步6 呈报(不擅自立) |
| D-F9 二引擎节奏 | 干旱计数面共骨架(D-A45 事件语义)+criteria/buy 档窗口(T_SEARCH 注入形态) | ✅ 骨架共享;trio3 OPEN 挂对账(保持) |
| D-A45 干旱重置 | 商店侧半边:买入目标件 ⇒ `line_state.drought=0`+`shop_drought_reset_on_buy` 计数(正反例测试:未买目标件不重置);prep 侧半边=步3+4 proof.update_line_state | ✅ test_d_a45_drought_reset_on_target_buy / test_d_f9_drought_no_reset_without_target_buy |
| D-BUYNOTE 整买纪律 | M3 内嵌 `spend_unified`(整批够升级才放行;金不足不发射 test_levelup_face_batch_discipline 前半) | ✅ 复用步3+4 判据,本批消费位接线 |
| D-F1 选卡折现 | 非商店面(pick 接口辖外) | ⏸ 同 STEP34 呈报(pick 面收编批) |

## 3. 验收数字(全实测)

- **①criteria 七面商店形态单测**:TestCriteriaShopFaces 11 用例 ✅——买面(M2 义务买入+金门/dominance sink+非 1★ 拒)/卖面(M4 腾席先卖后买/funding 支撑两臂)/升级面(整买纪律正反+lv9_stop)/刷新面(None fail-closed+分键)/压库面(m6_overflow_strand)/装备面(辖域申报=输出全在商店词表)/证明面(stop_flag 门 dominance)。
- **②词表+截断契约锁**:TestShopTruncationContract 9 用例 ✅——词表 9 类覆盖断言(8 类辖内+PickEvent 词表外);BuyCard/LevelUpShop 可续;拖拽族条件续;RefreshShop/CompTransaction 截断点(尾部丢弃);合成触发截断(bench 2 副本/含 deployed 保守域两例+计数);§3.3 PickEvent 与 rogue 类型 fail-closed+计数;黑板缺帧抛错。
- **③修复池商店面检查点核销表**:见上节(7 项落点;1 项 OPEN 保持)。
- **④双臂可跑且行为相异实证**:`arm_diff_probe(n=6, seed_base=0, pool='snapshot')` → **{n:6, diff_pairs:6, ok:True}**(seed 0-5 全部 ledger 相异);ledger 可读性锚(seed 0):基线臂 9 轮行(动作 SellBench 2/BuyCard 11/CompTransaction 12/LevelUp 42/RefreshShop 6)vs 新核 9 轮行(BuyCard 4=M2 线成员买入)——新核 None 期行为面=M2 义务买+少量支配买(设计内 fail-closed 形态:刷新/凑息/事务面零发射)。**非正式 A/B**(正式=步6,判前锁 v6 前置)。
- **⑤基线臂零漂移复跑**:`baseline_self_pairing_gate(n=20, seed_base=0, pool='snapshot')` → **{n:20, mismatches:[], ok:True}**(decision_v2 自配对 20/20 seed ledger 逐位相等)——透传拆除后本批零污染基线臂。零漂移门不适用新核(非适配器;两臂 diff=设计内形态,由 ④ 承载)。
- **⑥CW 域快速层全绿**:`uv run pytest sr-od-test/test/sr_od/app/currency_war -m "not slow and not legacy_baseline"` → **2344 passed / 0 failed / 2 skipped / 1 xpassed**(166s;xpassed=test_cw_decisions.py::test_xp_helpers_clicks_and_cost,r17 已知缺口 xfail 非 strict,与本批无关亲验;与 STEP34 基数 2327 的差=本批 +32 快速用例+并行批(tests 计数随并行在飞改动波动),零失败为本批判据)。
- **ruff**:改动 5 文件全过(autofix 后 0 error)。
- **慢桶**:test_cw4_shop_line.py::TestSimGates 2 用例 + test_cw4_mandate_v1.py::TestZeroDriftGate(重推锁)全过(33.69s 合跑);slow_marks.txt 同步(旧条目改名+新增 2 条)。
- **锁更新(锁的存在性纪律)**:旧 `TestZeroDriftGate::test_shop_line_zero_drift_n20` 钉「两臂透传逐位相等」语义——步4b 拆透随后该锁钉死已废弃语义(构造性必红),重推为基线自配对锁(同判据族:同 seed 同池 ledger 逐位相等,对象改 decision_v2×2),锁注释注明重推依据;slow_marks 条目同步。

## 4. 解释性裁量清单(拿不准的规格点,呈报候裁)

1. **合成触发截断的保守域=bench∪deployed 全场同名同星计数**:契约 §3.1「满栏买入可触发自动合成」只给现象未给判定式;本批取「本次买入使同名同星持有(bench+deployed)达 3 ⇒ 截断」(3合1 机制,ShopCard.merge_preview docstring「买第 3 张即 3合1」)。保守处:①deployed 副本并入计数(合成载体可在场域,是否参与合成触发未见机制文档定谳);②不依赖 merge_preview(sim 恒 0)。偏保守方向=多截断少发射,fail-stop 兜底。待裁:精确触发域(是否含 deployed/是否读 merge_preview)。
2. **M2 商店波买入档选择=同名最廉档**:规格只定义 M2 义务(线成员必处置),未给商店波「同名多档(1★/2★)」选择式;本批取最廉(1★ 优先,star 不设门——义务买入序 1/2 不走 EV 否决,§3.4 豁免条款)。待裁:是否需要星级偏好(2★ 直购省席)。
3. **dominance 商店波消费面=star==1 ∧ refund_full_star_ok(注册表直读)**:P24 零参数;实测 sell_refund(1,cost)==cost 对全部 1★ 成立(手续费仅 star≥2 域)⇒ 支配买=全部 1★ 非线内件。若 P24 原文「档内」另有约束(如 cost 档),T_SEARCH 档窗口在 None 期不可用——当前形态=无档约束的保守超集,待标定批收紧。
4. **D-D 硬节点门=纯观察级接线**:FIXPOOL §3-D-D 要求「生成定向补强意图」;None 期 V̄/r1 EV 未标定,补强的行为面(付费刷新/定向买)无判据载体——本批只接门消费+计数,行为面挂标定批(与 STEP34 D-D 处理同款,呈报确认非降级)。
5. **M6 注入形态档窗口={1,2,3} 结构占位**:T_SEARCH_A 非 None 期给 `frozenset({1,2,3})`(与 criteria/buy.ev_buy_candidates 步3+4 同款占位),档窗口数值随标定批定谳——两处同源复制(非单一源),收紧时两处同改;待裁:是否提升为 provisional 槽位值。
6. **干旱重置的商店侧半边在 sim 是 prep 空转态**:sim 不驱动 prep(D-A45 prep 侧 LineState 在 sim 恒缺省)⇒ 商店侧重置作用于 prep 帧创建的状态机;sim 内该路径计数仍记录(事件可观测),状态机半边 prep 域(实机生效)。申报边界非缺陷。
7. **ev_arm 生产 extra pickup**:STEP34 裁量 #8(半边未接)维持——cw4_counters 在 session 侧累积,ledger 行 extra 追加随让路裁决批。

## 5. 检查点时间线

- 批内:规格通读(IMPL_DESIGN §4.2/§6.4-R + 契约 v2 + SIM_CONSUMPTION_MAP + FIXPOOL + STEP1/2/34 报告 + engine_p1 消费面 L990-1330 亲读)→ shop.py 落码 → bridge 接线+透传声明 → ab_core_swap 门组重写 → 冒烟(手工帧:4 BuyCard+计数可读)→ 双门首跑(自配对 20/20 绿;diff 6/6)→ 测试 34 用例(5 红均测试前提错位:dominance 全 1★ 可退/arm1 构造/词表集合断言/u 分键进路/dominance 吞 EV 候选——逐个重推锁语义,零生产代码返工)→ 全绿 → ruff → design_telemetry 9 键登记 → CW 域快速层(后台)。
- 快速层终态:2344 passed / 0 failed / 2 skipped / 1 xpassed(r17 已知缺口 xfail,与本批无关;两轮复跑零失败)。

## 6. 约束自检

- 让路规则:runner.py/decision_assembly/prep_brain/cw_screen_prep/cw_strategy/decision_v2 系全部只读零编辑;本批编辑的既有文件(bridge.py/ab_core_swap.py/test_cw4_mandate_v1.py/slow_marks.txt/design_telemetry.md)批前均无并行未提交改动(git status 亲验:bridge.py 与 ab_core_swap.py 系本线步3+4 产物未提交,属本任务线自有件)。
- redesign 文档仅加键行(design_telemetry 键节 9 新键+索引行;其余零触碰);契约 v2 正文零触碰。
- cw4 步2/步3+4 已落件数值语义零变更(本批新增 shop.py+bridge 覆写,既有 criteria/statefn/proof/mandate 只读消费)。
- 不 git commit;不跑正式 A/B(步6 判读批,判前锁 v6 硬前置)。∎
