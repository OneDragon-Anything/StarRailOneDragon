# ADR-0471: sim 满级升级拒付对齐与破息例外谱收编

## 1. 背景与问题

两个 sim 检查/执行层的噪声源,经核查均为建模/记账层问题,非策略行为缺陷:

**① 满级升级拒付空转**:sim 批复跑中 `level_cap_rejects` 达 25.45 次/局(n=60,seed 630000–630059,1527 次),全部零金效果。根源两问定位:**根在建模约定层**——同一环境内两把等级尺:决策层单一源 `registry.level_max=10`(实机真值,lv9 是正常付费升级档)与 sim 执行层 `cw_sim.LEVEL_CAP=9`(声明性建模分歧,放开需池重锚,另行挂账)。决策层「等级未满」前置(`decision_v2/candidates.py: generate_candidates` 的 `state.level < registry.level_max`)本就存在且单一源正确;churn 机制 = lv9 帧:决策层 9<10 放行并完成 EV 授权 → 执行层 9≥9 拒付 → 下一决策段再提案。病根是「两把尺未对齐」,不是决策层缺陷。

**② 破息无例外记账**:段级破息检查器(`cw_sim_checks.seg_check_break_interest_exception`)例外谱过期——诊断窗 n=60 的 18 起事件 **18/18 全部**由升级授权通道花费(24–32 金/轮追级经验,`spend.levelup`,单一源 `ev.levelup_ev_basis`,ADR-0347/0354)或刷新授权通道花费(4–6 金,`refresh_ev_budget` 预算式,ADR-0409)引发,无一是纯买件破息——是「有例外但没标注」的误标,不是真破息。过期原因:旧谱的奖励/补给节点限定口径([16]②)未随「息律节点无关」定调收编;升级/刷新如今是任意节点合法的授权通道。真无例外破息(纯买件、无店全想要/连胜保)仍存在,必须继续红。

## 2. 决策

**① 接线单一址对齐,不造第二把尺**:新增 `cw_sim.sim_decision_registry()` = `dataclasses.replace(DEFAULT_REGISTRY, level_max=LEVEL_CAP)`——sim 侧决策层注册表是 DEFAULT_REGISTRY 的**环境视图**(值单一源自 LEVEL_CAP),在 `simulate_p1` 默认策略构造与 `simulate_p1_ab` 两臂消费。拒付层保留(执行层防线双保险);`DEFAULT_REGISTRY` 不动(实机 lv10 语义原样,实机行为零改动)。

**② 例外谱收编 + 花费分解**:例外谱补两类授权通道——④ `levelup_spend`(spend.levelup>0,任意节点)⑤ `refresh_spend`(spend.refresh>0);真无例外破息仍红,红事件新增 `spend_breakdown{levelup,refresh,buys}` 字段,归因不需人工分账。只动诊断谱系,决策/执行层零触碰。

同批配套:刷帽检查两口径定项(定向车道局帽=硬锁,归因走 session 计数器差值,零 arbiter 改动;普通车道轮帽=披露型)。

## 3. 被否决的替代方案

- **决策层造第二把尺**(决策层/sim 各持一值):两把尺的分歧正是病灶本身;再造「sim 版 level_max 常量」是把分歧写进第三个维护点,版本更新时三处漂移无守卫。环境视图接线 = 值只有 LEVEL_CAP 一个源。
- **删执行层拒付层**:拒付是执行层最后的防线(授权与执行解耦的双保险),删防线换噪声消除是错误交换。
- **刷帽普通车道口径作硬锁**:每决策段授权刷数(`min(REFRESH_ROLL_CAP=6, 溢余/刷价)`)是**逐段**重读预算的口径,轮级累计自然可越帽——账本轮行无法重构段界,「单决策帧越帽」与自然多段行为在账本上同构,硬锁在自然批 2/20 局即红(实证不可行),降为披露;「决策层轮级授权被逐段架空」的口径漂移实锤归策略域批裁决。

## 4. Consequences

- 决策/执行层零触碰,实机行为零改动(DEFAULT_REGISTRY 与实机链路均未动)。
- **非轨迹中性(如实声明)**:隔离归因 12/20 局轨迹位移——lv9 帧不再把槽位耗在必然被拒的升级链上,改走其他授权动作;结果面 n=60 方向略负(hp0 率 0.75→0.817、final_hp 均值 6.75→5.38)但幅度在二项噪声带内(SE≈5.6pp),无金损失差异(被拒升级本就不扣金)。w614 零漂移锚已按既定流程重锚(cdec4400),分布面影响并入下一批 sim A/B 判读。
- 破息读数噪声消除:残留红 = 真无例外破息候选,A/B 守卫「不升」判读更干净。
- 普通车道轮帽的「逐段重读预算」口径漂移只披露不修,修复属行为变更,挂账策略域批。

## 5. 验证

锁组 `sr-od-test/test/sr_od/app/currency_war/test_cw_w652_p4_fixes.py`(13 锁):`sim_registry_aligns_exec_cap`(视图 level_max==LEVEL_CAP ∧ DEFAULT_REGISTRY.level_max==10 不漂移)/ `levelup_candidate_absent_at_sim_cap_frame`(满级帧升级发起=0 穿透锁)/ `levelup_candidate_still_valid_below_live_cap`(实机语义下 lv9 帧仍生成候选,sim 分歧不倒灌)/ 破息三锁(追级通道不红 / 刷新通道不红 / 真无例外仍红且 spend_breakdown 逐字段)/ 刷帽四锁。锁红证据:对 HEAD 版(git show 提取独立加载)重放新断言 7/7 锁红成立。前后数字(n=60 同 seed):level_cap_rejects 25.45→0;seg_break_interest_exception 事件 18 起→0。L3 全量绿(唯一红为并行批归属既有红)。
