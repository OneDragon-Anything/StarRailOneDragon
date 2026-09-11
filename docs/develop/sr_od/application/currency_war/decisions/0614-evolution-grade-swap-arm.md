# 0614 — 演进降级换血臂(star_guard 武装让位;T-168 演进层换血提案接线·最小等效通道)

- 日期: 2026-09-09
- 状态: accepted (采纳;方案面 = 跨件半问裁决 + 盘点三立确认,任务书直授实施+落地审)
- 关联: ADR-0382(分级降级换血——本批为其语义在换血机器的参数化落位)、ADR-0386(W209 振荡熔断——非武装域语义不动)、ADR-0530/0534/0590(M1″ 换血机器/资格族统一/让渡序——本臂为该机器的新资格族,同臂扩展先例 = 0534 转型臂)、ADR-0590 决策 8(star_guard 让位口径的既有申报先例)、P41(甲.2 往返账——卖出代价轴重推见 §决策5)、P61(转型臂 B_t 弱支配——本臂 2★ victim 落在其声明域外,辖域注见 §决策5)
- 批: T-168(进度账本 .debug/progress/2026-09-06-currency-war-redesign/dag.jsonl)

## 背景与问题

T-168 立案证据(模拟批 20260908_2115/211743,池 0e091d4d):演进层统一入口
`evolution_step`(cw_evolution.py:1310,含 ADR-0371 补完/ADR-0382 分级降级
换血)全仓零调用 = 死代码;换血事务族执行端三处齐备但零发射;P2 锁线后
板满帧「bench 有锁线 core、板上全过渡件」形态无换血通道,④终局阵容完成率
4%、bench_full_buy_abandon 4717 次/100 局、must_spend 泄金全走刷新。

T-169(5c6620da)接通 M1″ 执行面后,基线批(20260909_055352,s1600,池
460e6031)swap 已活跃(952 评估帧 / 354 执行),但 star_guard 拒 189 帧仍
是结构缺口:板面线外件普遍 2★ 化后,1★ 限卖使「卖线外件上 core」在病灶
帧不可达。演进层 ADR-0382 恰为此形态而设(分级保护下的弱件让位,弱序 =
星级→费用),其语义宿主却悬于死代码。

## 决策

**演进降级换血臂**——ADR-0382 分级语义接入换血机器的参数化面,零新发射位、
零新执行通道、零第二可行性门:

1. **准入三元**(`evolution_swap_arm_trigger`,纯函数,kernel 单一源):
   锁线(`locked_buy_membership` 非空)∧ 转型域(fp 缺读臂关、fp≥1.00 臂关)
   ∧ 板满(占用数 ≥ max_units)∧ bench 占用件名 ∈ 采购集。装配级缺省计算
   (`assemble_swap_plan_inputs` 产物 `SwapPlanContext.evolution_swap_armed`,
   发射面/sim 同函数同值);执行侧 `cw_op_deploy` 卖出臂在 SIFT 现读 bench
   域后经同一函数重算覆写(装配源分轨既定面,发射⇔执行同值)。
2. **star_guard 武装让位**(`swap_sell_exclusion_reason`):武装帧对可读
   星级 >1 的 victim 放行进入结构守卫评估——target/engines/merge/fresh/
   membership 守卫全保留;星级不可读恒拒(不可判星级 = 不可判 ADR-0382
   弱序,fail 向)。非武装帧逐位同旧。
3. **触发位划界(防同点双发射)**:臂不新增发射位——M1″ 既有发射位
   (mandate.py:1335 起,`not any(RunDeploy)` 守卫 + 单次评估)与 sim 引擎
   M1″ 块照旧单点发射;本臂只改资格判定,同帧至多一次发射由构造保证。
   计划胜出者仍走 P79-4 让渡序(结构档边际贡献升序→星级→板槽位序):
   1★ 弱件恒先于 2★,臂只在「无 1★ 可卖件」帧扩容 victim 集。
4. **上 core 半边**:复用既有部署链——发射 = RunDeploy(m1_swap_redeploy)
   → CwOpDeploy 卖出臂逐件卖 + 部署 core(core_tgt 桶先序);sim = 引擎
   M1″ 执行转录 + 轮末部署块残余补上(T-169 同构)。bench 翻正 → S1 清键
   走 RunDeploy 落地路径(i) deploy_launch,开店闩自愈,M2 重开买入。
5. **卖出代价轴重推**(P79-3 ③ 轴前提更新,注 = mandate `_redeploy_
   emission_allowed` docstring 既有文本随本 ADR 由后续批修订):旧闭合
   论证「存活 victim 恒 1★ = 往返净 0」在武装帧失效——2★ 卖出 = P41
   往返净损 > 0;正当性 = 病灶态机会账:板满 ∧ 席满 ∧ 线未成的卡死态下,
   1 个 bench 槽的期权价值(买入线内件→完成度推进)与「core 上板」的
   直接完成度收益,支配 2★ 线外件的持有价值(该件不卖也上不了场、卖则
   腾槽激活整条买入链;机会成本量级锚 = T-168 立案证据批的
   bench_full_buy_abandon 4717 次/100 局)。A/B 验收 = §验证。
   **P61 辖域注(F4)**:math_proofs P61(转型臂 B_t 弱支配)声明域 =
   守卫合格 1★ fenced victim(边界第 1 条「1★ 限卖残差」);本臂武装帧
   2★ victim 换血落在该声明域之外——金不减腿在 2★ 卖出失效(P41 往返
   净损 > 0),收敛性改由 B_t 严格增腿独立承载(胜出者必过
   post_sell_offline 底线 ⇒ B_t 净 +1,无死循环保持);证明批回填
   math_proofs P61 边界行(挂账 = 编排者证明批排期)。

### Considered Options

- **整体接线 evolution_step**(修向原文第一形态):拒——其常规提案
  (propose_upgrades 换档/ADR-0371 补完)与 mandate_v1 部署/授权机器构成
  第二决策面(跨件半问管辖的冲突形态),且 kernel CompTransaction 在生产
  无执行通道,需新建执行面,波及面最大;死代码激活的收益被并行决策面
  风险压倒。
- **独立提案函数+新发射位**(prep 环 M1″ 后补位):拒——同点双发射风险
  正是任务书划界令所辖;且 victim 资格若不复用机器即第二可行性门,复用
  机器则与 M1″ 逐位重复、零缺口增益。
- **准入三元只作观测面不拦截**(launch_admission 先例形态):拒——本臂
  让位的是 1★ 限卖这一既有资格语义,触发面必须硬门(fail-closed 各腿
  齐备才武装);观测面形态会让 2★ 让位在未锁/成型帧泄漏。
- **持久门**(照搬 ADR-0382 的 4 轮持续门):拒——该门辖补完事务激活宽度
  (缺口持续追踪),本臂触发面已被准入三元 + P79-3 ② 档关键件轴
  (REDEPLOY_TRANSITION_ENABLED 保守缺省,form-advancing 才发射)收窄到
  完成度推进帧;叠加持久门会让臂在 s5 型「轮轮卡死」形态前 4 轮空转,
  与验收目标(④/abandon 改善)反向。

## 验证

- 新锁 6(`sr-od-test/test/sr_od/app/currency_war/test_cw_evolution_swap_arm.py`,
  T-21 wait 行联动准入常驻锁):主锁(全 2★ 板面武装帧 → 爻光 2★ 让位、
  上序三月七、arm='transition';未武装对照 star_guard ×4 计划空)/执行侧
  同函数放行/准入三元逐腿矩阵(7 腿 fail-closed)/装配级计算与腿移除/
  其余守卫武装帧全保留(buy_membership/fresh_buy/engines_guard/
  merge_material_guard/星级不可读)/run_mandate 发射端到端。
- 变异打红:摘除 star_guard 武装旁路 → 主锁/执行侧/守卫保留/端到端
  4 锁红(触发器矩阵 2 锁不受牵连 = 选择性正确),恢复后全绿。
- 邻锁更新(`test_cw_deploy_transition.py::test_lesion_frame_replay_
  fires_victim_yuanguiren`,按锁的存在性纪律重推非机械跟绿):病灶帧
  = 武装帧,艾丝妲 2★ 不再 star_guard 一票拒,进入结构守卫(其卖出不
  掉已达成档 → 放行、让渡序居后);计划胜出者/victim/up/arm 逐位不变
  (胜出分键 redeploy_transition_victim_忘归人==1 持有),star_guard
  显影消失 = 臂激活伴生面;非武装域 1★ 限卖由
  test_cw_swap_transition_arm::test_star_guard_blocks_2star_victim 原锁
  继续持有(该锁手装 ctx 缺省非武装,逐位同旧)。
- swap 族邻锁 76 全绿(test_cw_swap_plan/swap_transition_arm/
  deploy_transition/recipe_floor_lock_exempt/evolution_swap_arm);
  CW 域 L1 快速集(`-m "not slow and not legacy_baseline"`)全绿;ruff
  改动文件全绿。
- sim A/B(planes=2,池 snapshot 460e6031+eqg1,manifest 申报代码态):
  **同 seed 配对对**(seeds 1600-1699,n=100,改前 20260909_055352000 /
  改后 20260909_060741000):④终局阵容完成率 22→30(+8pp;逐 seed
  翻转 = 8 翻正 [1603/1614/1619/1639/1667/1673/1683/1698] × 0 翻退)、
  m1p 执行 354→386(Δ+32)、star_guard 拒 189→1(臂激活机制指纹)、
  通关率 24→23(战斗结算校准面 + 种子噪声,按 2026-09-09 在册裁定
  不作 A/B 判据)。**不相交 seed 对**(基线 s1600 / 处理 s1700,n=100
  各,任务书验收设计):④ 22→28(+6pp)、star_guard 189→3、执行
  354→375。
  **bench_full_buy_abandon 面(落地审 F1 修订口径;如实申报未达标)**:
  读径 = decisions.jsonl 逐帧 `obs.cw4_counters['bench_full_buy_abandon']`,
  **帧正值求和口径**(Σ over 帧 counter>0,落地审口径,本批复现精确
  命中)按 `v3_intention.phase=='locked'` 分轴——配对对 全量
  6206→6154(锁线帧 3423→3371,未锁帧 2783=2783 逐位相同,停滞帧集
  978=978 [锁线 475/未锁 503 均不变]);逐局末值 703→680;不相交处理
  批 s1700 全量 6062。结论:未改善(全量 −0.8% 量级);量纲论证 = 该
  计数是臂的**上游状态量**(板满被阻买入压力的帧级敞口)非输出量,
  臂输出 = 换血转化 + 完成度——锁线敞口 −52 与「每次转化消费一被阻
  买」一致,未锁帧零扰动(2783/978 双逐位相同 = 臂辖域外无触碰的
  额外指纹);④ 为主判据。**口径勘误(F1)**:本 ADR 初稿的
  「885→886/889」系局内计数器分段复位形态下取局最大值求和的方法学
  错误(该口径不可复现,弃用);初稿括注「P1 未锁帧主导 ≈3 倍于 P2」
  系事件差分口径(差分事件 未锁 1096 > 锁线 347)与帧正值口径
  (锁线 3423 > 未锁 2783)方向相反所致的混标——两口径测的是不同对象
  (事件增量 vs 停滞敞口),本 ADR 统一采用帧正值口径并如实改写。

## 影响

- kernel/cw_deploy_logic(`evolution_swap_arm_trigger` + `SwapPlanContext.
  evolution_swap_armed` + `assemble_swap_plan_inputs` 计算 + `swap_sell_
  exclusion_reason` 武装让位)、operations/cw_op/cw_op_deploy(执行侧
  SIFT 域重算覆写)。
- 语义宿主声明:cw_evolution(ADR-0382 分级机器)零改动;演进层换血
  能力经本臂在换血机器的参数化面生效,evolution_step 死代码本体由
  后续批按其辖域另行处置(本批不接线,防第二决策面)。
- 观测面变化(如实申报):武装帧 2★ victim 的 star_guard 拒因显影消失
  (病灶帧形态);臂激活本身无独立计数键(发射/执行沿用 m1p_fired/
  m1p 记录与既有拒因分键),臂激活帧的反事实识别 = 未武装对照批的
  star_guard 计数差。

## 落地审闭环(2026-09-09,报告 = .debug/temp/currency_war/attacks/t168_evolution_wiring/落地审.md)

需修 2 项收口:F1 = abandon 数字改帧正值求和口径(实施方复现审方读径
精确命中:6206→6154/锁线 3423→3371/未锁 2783=2783/帧集 978=978/逐局
末值 703→680;初稿 885 系局最大值口径方法学错误弃用,初稿「未锁 ≈3 倍」
系事件差分口径混标,两口径并注于 §验证);F2 = as-built 双指针行
(flow/action_exec.md 第三例外 + strategy-docs/14 落码回记二)。
建议 4 项随批:F3 = 代码注释账本行引用全量改 ADR-0614 持久索引
(cw_deploy_logic ×6 + cw_op_deploy ×1 + 测试仓 ×3);F4 = P61 辖域注
入 ADR(关联行 + §决策5);F5 = 测试头注变异红数 3→4;F6 = trigger
docstring 与转型域谓词偏差申报(可达性拓扑安全依据成文)。
