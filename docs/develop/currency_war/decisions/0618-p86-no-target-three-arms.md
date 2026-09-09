# ADR-0618: P86 无目标期三臂判据落码——FALLBACK_COMP_NAME 四面退役与乙臂枢纽期权接线(T-177)

## 背景

无目标期帧(P2+ 商店决策帧 ∧ `target_comp=None` ∧ 意向供给在场 ∧ 未降格终局)的
囤货方向此前由单线硬编码常量 `FALLBACK_COMP_NAME='绯英欢愉'` 赋值,不经任何判据;
绯英自身 G=0.0000——「候选机器判全线不可行后,囤货方向落在被同一门判死的线上」
(P35 复盘 §6-5 实证),经 k_members 向买面辖域/卖免面/刷新账合格集三下游供血,
全部无判据管辖。命题与证明闭合于 `proofs/p86-no-target-period-fund-allocation.md`
(正本,方案审 13 项+对销复核 12/12)与 `proofs/p86-proof-batch.md`(证明批 v2,
必答六件终裁+九锁增量条款),全站贯通复核 11/11 放行落码批规范消费。

## 决策

1. **四面退役**(正本 §4.2 逐位):①`hoard_target_set` unlocked 终支换三臂判据,
   常量删除留墓碑注;②`cw_economy._schedule_target_core` 移除兜底锚,维持缺省
   3 费并申报(峰值级锚只进概率校准分量,方向语义中性;处死计划批 1 语义提前
   兑现,archive 漂移登记随注);③`_p1_transition_eligible` 绯英恒 no-op 支删除
   (删前死分支断言测试化:P1 信号路径未资格信号被配方锁段过滤,删除行为零差);
   ④`DirectionView.fallback_comp` 投影字段整体删除(单一写端、grep 无读端)。
2. **三臂判据**(kernel 单一源 `no_target_arms`):甲臂=候选机器强锁门逐字
   (同一谓词 `line_completion_feasibility`/同一常量 `revoke_miss_tolerance_eps`/
   同一 plane 条件+机器自身选择序;promote_candidates 禁入调用链);乙臂=资格核
   `cov≥2 ∧ 非单卡注册身份`(输入面恰五元,AST 静态锁)+非合并素材第五前件
   (`same_star_count` 全场域)+四谓词核,发射位物理先于 M2 承载同帧仲裁三层序
   (支配序[授权面收窄至 C_x={l_d} 单线件]→机器原生序→注册表声明序;覆盖数
   降序显式否决);丙臂=两臂皆空缺省守息(合法空集带 `k_fallback_source` 证据
   经契约放行;辖买卡买面与卖面资格,不辖升级/刷新既有授权——prep M3 与
   R1 no_chaseable fail-closed 照旧)。
3. **k_members 三下游换源**(正本 §4.6):M2 义务/卖免 zero_overlap/刷新账合格集
   整体吃判据臂输出;判死帧错向囤积结构性消失,必花域烧费路径(RefreshShop
   yielded)在无目标帧族随合格集空 fail-closed 关闭。
4. **契约面**(最小触碰,编排者追认):`ContractCtx` 增 `k_fallback_band`/
   `k_fallback_source`;`_k_projection_domain_full` 带维度非对称期待(p1 带空=
   违例,p2plus 合法空须三臂来源证据);`_s_reserve_line_formed` 合法空扩展
   (落地审追认:无它则裁决②「必花域维持」落不了地——两臂皆空溢余帧的
   支配性买被 S 预留前提误冻;F-9 加固=band+source 双核与 k_projection 同构,
   供给缺帧旧违例边界维持)。
5. **乙臂登记**:`LAUNCH_CAUSE_BY_ARM` +`hub_option_buy: hold`(A4 硬闸地基),
   15 键穷举锁随批重推;拒因键 `hub_option` 先于 ④(P2+ 帧 ④ 经 committed 门
   构造性关闭,枢纽臂为交集卡活通道;P1 键序零变化)。

## Considered Options(最值钱项)

- **F-1 竞争域二选一(落地审中项,裁选项 a)**:让位判定以「方向件在售」为域
  会令更早声明的不可负担件持续挤掉枢纽发射机会;修正=让位判定前对方向件加
  本帧可发射快判(金/席),合取不过者不获挤占权——对齐证明批 §4.4「序只在
  各自合取都过但资源只承其一的竞争帧介入」。否决「如实申报在售即域」:
  该口径与附带条款①直接冲突,属判据本体让步。
- **乙臂经 k_members→M2 通道获取**:否决——M2 无息纪律/星级/素材门,五前件
  合取语义不可承载,破证明批 §3.2 发射合取。
- **候选序沿用店面遍历序**:否决(变异实证)——与「发射序与实现遍历顺序解耦」
  冲突,改为声明序排序(与资格核枚举同源)。
- **覆盖数降序仲裁键**:否决(证明批 §4.4 显式否决;集合包含单调性≠基数单调性),
  自然分歧帧测试化钉死。
- **v1「覆盖集⊇甲臂候选集」形态**:否决(定理 B3 空洞引理——病灶帧恒真)。

## 后果

- 判死方向囤货通道结构性关闭(错向囤积与必花域烧费在同帧族消失);枢纽期权
  获取通道开启(获取=备战席持有,行权归部署域既有管辖,零新增行权授权)。
- 新判读键族:`shop_no_target_arm_a_adopted`/`_dead_defer`/`_corner_defer`/
  `shop_no_target_hold_default`/`hub_option_*`/`must_spend_r1_yielded_no_target`
  (F-6 联合分键);`shop_k_fallback_p2plus` 语义重建为「回退采用(甲臂方向集)」,
  跨批对账须按新构成解读。
- 已知缺口如实申报:甲臂缓锁豁免角漏授(保守向,机器锁后 M2 自纠,
  corner_defer 分键显影);乙臂家族内集中覆盖(爻光型)期权集中度由开火计数
  与出口转化判读守;`cw4_hub_acquired_names` 载体已挂,deployed_from_hub/
  activation_from_hub 读端归部署域下批(F-3 半)——**攻击 r1 后状态更新见
  「攻击 r1 闭环」节:三面读端已接线**。
- 甲臂候选集帧内至多三次求值(k_empty_window_fallback/no_target_arms/flow 日志位)
  为已知效率面,归机械批(F-8)。

## 攻击 r1 闭环(备战策略攻击 634ec79b,发现1【高】三面同批收口)

乙臂「获取 = 免费期权持有」的持有语义原只活在买因标签:覆盖数 ≥2 注册表
派生枢纽集包含静态持有集(`sell_hold_exclusion_names`)之外成员(瓦尔特/
刻律德菈,cw_line_facts 移出记录实证)——hold 类登记名字腿恒拒(病灶信号键
被常态发射污染)且卖面无保护(fresh_buys 只保同轮,下帧凑息/腾席/筹资可当
1★ 燃料卖掉),期权价值被己方判据销毁。三面收口(禁只补一面):

1. 面①登记资格域:`_hold_qualification_ok` 名字腿 = 静态持有集 ∪
   乙臂获取名集(发射位先登记后 emit,当笔在场);launch_cause_mismatch
   病灶信号语义不再被乙臂常态稀释(名集之外名仍拒,负锁在案)。
2. 面②装配 A 身份段:`identity_exclusions` 并集获取名集——保护面只辖
   实际获取件(取获取时点记录,不随帧资格集波动扩张)。
3. 面③部署域行权显影:cw_op_deploy 鸭子读同一载体(属性契约,同
   `cw4_fuel_filler_stall_buys` 先例),围栏放行上场的获取名按笔计
   `deployed_from_hub`;正本 §4.3-1「围栏放行核查前置」自此有代码面兑现。

载体 = `cw4_hub_acquired_names`(发射位单一写点);策略侧读口
`sell_gate.hub_acquired_names_of` 单一源,部署域鸭子读同一属性禁改名。
锁:三面收口锁 1(登记零污染+簿落账+下帧 L1 过期后身份段保护——
**变异夹具须推进帧轮再验**,同轮 L1 硬面会遮蔽面②缺失)+静态接线锁 1+
负锁 1(名集之外名不获资格域);变异 M-A(持有腿摘除)/M-B(身份段并集
摘除)各自红、还原绿。随批:中1 mandate `_redeploy_emission_allowed` ③轴
docstring 按 ADR-0614 §决策5 重推(三审 C-1 挂账兑现);中低1
`_seele_system_support` docstring 并入 T-59 副本形态挂账(ADR-0613 确认项);
低2 detect_signals ②注释「⑤兜底」陈旧语义更新;发现5 乙臂星级腿改消费
`refund_full_star_ok` 单一源(对本面等价,防半边退金表静默分叉)。

## 验证

- 新锁 30(九锁对表+四面退役+契约六例+F-1/F-5 补锁),变异 3 发全红(MUTANT-1
  覆盖边界 2→3/MUTANT-2 层1 支摘除/F-1 竞争域回退)还原绿;重推 5 文件全部
  语义重推非机械跟绿;CW L1 全量 3437 passed/0 failed;ruff 8 文件绿。
- sim A/B 同 seed 段 [4000,4099] 同池配对(460e6031e2f4ae06+eqg1,planes=2):
  案发帧(P35 同型)错向囤积 2→0、带内烧费 5→0、枢纽发射 1(开火性>0 门达成)、
  headline 全在种子噪声带;manifest=`.debug/temp/t177_ab/AB_MANIFEST.md`
  (易失档,持久结论以本节与本 ADR §验证为准)。
