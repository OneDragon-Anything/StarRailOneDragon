# ADR-0590: 部署面让渡决策(T-127 R2)——锁线域装配级键集收窄 + 转型域资格族统一 + P79-3 执行条件发射门 + P79-4 让渡序

## 背景(病灶与归层)

复盘 O2(g_20260907_214130,死因架构面):P2 锁绯英欢愉后,锁线成员
(罗刹/真理医生/银狼LV.999)自 r5 起持续压备战席,板上 8 件无一可换——
M1″ 锁线段各备战帧零发射,carry 绯英停 1★ 被三连小败磨死。归层结论
(T-127 方案 v3.1 §0,经三轮对抗收敛):**根在决策层(部署发射位的换下
资格面)**——主闸 = W209 振荡熔断的弹性阵营保护把「买面铺板不算
off-target」语义(all_factions = factions ∪ flex_factions,ADR-0152)
同源套用到了部署换血域,flex 弹性件(仙舟/量子同频/战技点)在换血域
被当硬保护对象,1★ 候选 victim 全数锁死;次闸 = 守恒门(本局仅拦
1/8)。执行层缺件(可逆下场动作不存在)归 R3,不在本批。

设计 = T-127 方案 v3.1(`.debug/temp/currency_war/t127_deploy_trigger/
方案.md`,三轮无前提对抗零阻断收口),命题权威 = math_proofs **P79**
部署让渡时机命题族(R1 已入册,7fd3b65f)。本 ADR 记 R2(决策层治本)
的落码决策;编排者既裁项:「档关键件」谓词 = 面板口径读法 b(form 机制
单一源 = `cw_comps.form_progress`;面板欠计传导 = 方案 §7 #12 观测项)。

## 决策

1. **装配级键集收窄(方案 §3.1 行 #4,读法 D——四种可实现读法唯此
   成立,禁实施者自选)**:锁线域 `ctx.target_factions` := 核心羁绊集
   (`comp.factions`)∪ 已达成档承载弹性键(flex_factions 中「当前板面
   计数已达任一 tier」的键)。三钉源:收窄只发生在装配层单一源
   (`assemble_swap_plan_inputs` → `locked_redeploy_target_keys`),
   产物同喂五个消费位(offtarget-② `offtarget_sell_allowed` target
   早拒 / `swap_sell_exclusion_reason` 宽口径 target 归因 / 上行
   is_tgt `select_deployments` / `_bench_is_target` /
   `post_sell_offline` 底线),任一消费位各自内联 = 双源 = 五面视图
   分裂,禁;计数源 = `deployed_bond_counts` 注册表口径(与守恒门同
   源,禁面板口径——星间旅人面板 1 vs 注册表真值 2 的欠计类已实证);
   tier 源 = `FACTIONS` tiers 唯一自然源,希儿系特例复用
   `seele_system_formed` 二元。**收窄辖域 = 转型域(落地审 F1 修订)**:
   转型域外——未锁帧与锁线成型帧(fp≥1.00)——键集逐位同旧
   (all_factions 全量,零行为差);初版按 `locked` 全域收窄,使锁线
   成型帧释放件(2★ 纯弹性件)经成型臂绕过 star_guard/P41②/守恒门
   被无守卫卖出,与决策 2 及方案 §2.3「成型臂语义照旧」直接矛盾,已修
   (装配点 fp/board_full 先算后收窄,判据 = `_swap_transition_domain_of`)。

2. **锁线转型域资格族统一(方案 §3.1 行 #5)**:新增辖域谓词单一源
   `_swap_transition_domain` = 转型臂开 ∧ locked ∧ fp<1.00 ∧ 板满。
   域内经收窄释放的 candidate **无论 fenced 与否**统一走转型臂资格族
   (守恒门/star_guard/素材守卫/fw_carry 对称排除/卖后上序底线全
   适用),基座臂提前返回(`offtarget_sell_allowed` 放行即 '')在域内
   **封堵**——否则「弹性键未达成 + 希儿系经贝洛伯格成形」类板面可达
   希儿系泄漏(非 fenced 释放件经基座臂可卖且 arm='base' 只查 up2
   非空,卖之破成形引擎+拆素材对)。域外语义逐位照旧:未锁帧基座臂
   /fp≥1.00 成型臂不动(方案 §2.3);锁线帧 fp 缺读时释放件同弃权
   `fp_unreadable`(ADR-0534 §1「两臂同弃权」的释放件侧延伸)。
   arm 标注钉死(三轮 N5):转型域资格族胜出者恒标 `'transition'`
   (禁落 'base')——`swap_arm_transition_trigger` 分键归因依赖。

3. **守恒门锁线域默认保留(方案 §3.1 行 #7/§3.3)**:已达成过渡档
   (列车同行/持续伤害/护盾/希儿系等 SWAP_GUARD_SYSTEMS 体系档)不被
   换血拆解继续作为 R2 默认形态的资格保护——[31]③「保持手上牌能成的
   其他羁绊板」在册语义落位;「保护对象切终局线档」降级为候裁全量
   形态组成部分,随 `REDEPLOY_TRANSITION_ENABLED` 翻转批另行走
   **ADR-0433 修订申报**(0433 判据锚过渡 form_ok,切对象 = 在册裁定
   修订,禁静默),本批不改守恒门本体。资格门辖域写死(方案 §2.3):
   P41 ② 与 star_guard 属 victim 资格门,不被 f≥2 收益侧豁免。

4. **P79-3 执行条件发射门(新增发射门,mandate M1″ 段)**:锁线转型域
   (arm='transition')计划非空帧,发射前过 `_redeploy_emission_allowed`
   三轴——①压席锁线成员存在(bench ∩ membership 非空,A1 主体);
   ②成员类轴:保守形态(`REDEPLOY_TRANSITION_ENABLED=False`,现役缺省)
   要求压席成员中存在档关键件(`_deploy_advances_form`:部署其使
   form_progress 严格上升,面板口径读法 b);③换下代价轴:卖出态由
   资格面 fail-closed 承载 P41 ②(2★+ 卖出被 star_guard 持有,存活
   victim 恒 1★ = P41 甲.2 全档往返净 0 ⇒ 代价 0 ≤ C_sat ≥ 0),解析
   闭合零自由参数,不另设数值门,V_ms/λ_death 挂账面不新增(P76 §7
   同源在册账)。未过 = 分键 `redeploy_cost_gate_defer`(帧级 defer,
   与逐件资格拒因**分列禁混桶**——资格拒「能不能换」,本键「该不该
   这帧换」)。成型臂/基座臂不辖本门。 defer 键不冒名 m1p_plan_empty。
   档关键件判读源 = 装配 ctx 携带的 `target_comp`(本计划实际消费的
   comp 视图,双轨口径随装配;落地审 F2 对齐,禁发射门另读 state_of
   第二份——双轨帧两源可分歧 = 判据源分裂;ctx 缺读退 state_of 兜底,
   缺读帧保守 defer 方向不变)。

5. **P79-4 让渡序(转型域 victim 序)**:结构档边际贡献升序(度量 =
   `swap_yield_contribution`:「target 视图 ∪ SWAP_GUARD_SYSTEMS」并集
   各体系 achieved 档数下降量,纯结构计数;计数源 = deployed_bond_
   counts,tier 源 = FACTIONS 自然档表,重叠键仙舟取 (3,5,7,10),
   希儿系二元;收窄键集下与 all_factions 全量并集度量**可证等价**——
   剔除键 = 未达成键 achieved 恒 0 离场差分恒 0)→ 星级升序 →
   ctx.deployed 板槽位序首个(显式定义,零新排序键)。资格门与排序键
   正交。**ADR-0534 §5「禁新排序键」在其辖域(锁线转型域)被本决策
   取代**(P79-4 结构计数首键,首件 = 纯过渡件的确定性非 1★ 巧合);
   域外序(1★ 优先 + 扫描序稳定序)逐位照旧。校准值(病灶局 r7 FORM
   帧,注册表直调复算):忘归人 0/艾丝妲 0/三月七 1/希儿 2/缇宝 2/
   饮月 2——首件 = 忘归人。

6. **显式参数与开关生命周期**:让渡总开关 = mandate 模块常量
   `REDEPLOY_TRANSITION_ENABLED`,缺省 False = 保守档件形态(仅档关键
   成员承载让位,非档成员按 [21] 上场窗口语义合法等待);候裁通过后翻
   True = 全量形态(任何压席成员可承载),只翻常量不改结构。合法性 =
   策略开关生命周期门:部署面让渡正当性是用户裁定输入非数学输出
   (P79-5),行为输入(裁决)未就绪 + 开臂判据挂账 = 进度账本 T-127
   候裁行;候裁批落地时守恒门对象切换随行另立 ADR(见决策 3),本常量
   不辖;翻 False 即回滚,无悬置态。

7. **分键闭集扩展(方案 §2.3)**:发射面逐件拒因过滤器
   {engines_guard, star_guard, merge_material_guard, post_sell_offline,
   fp_unreadable} 扩入 **target_keep / buy_membership**(病灶局八件
   拒因 4×target_keep + 2×buy_membership 在旧闭集零显影,「臂武装而
   计划空」无法遥测归因——cw4_counters 档案实测);新增
   `redeploy_cost_gate_defer`(执行条件未过)与
   `redeploy_transition_victim_<名>`(让渡 victim 逐件归因,只随发射
   显影)。`redeploy_undeploy_arm` 键属 R3 下场臂,本批不落。

8. **G1 准入口径顺手修(方案 §2.2/§7 #11 精度组⑥)**:
   `launch_admission_report` 三元①板满由「占用数 ≥ 物理槽位总数
   DEPLOYED_CAPACITY」(level 驱动 cap 全域 <10 ⇒ 结构性不显影)换为
   「占用数 ≥ `state.max_units()`」,与 swap 臂同一裁决先例(禁物理
   门);cap 缺读 = 质量闸兜底同口径。准入观测面其余语义零改;victim
   集与本体的深度同源化(T-121 同族接缝)不在本批。

9. **02 号稿 §7 姊妹出口句(R2 首项,先于落码提交语义)**:sell 机器
   处置行补「M4 姊妹出口·部署腾席卖出」登记句(14 号稿 §9.3 三-3
   ⑧(c) 登记的入册批义务)——落地前出口不得先于 02 修订存在;出口自
   ADR-0530 起在产的事实如实申报为登记滞后。

## Considered Options

- **收窄落点**:a) offtarget 内收窄(读法 A/B)——:895 宽口径仍锁死
  忘归人,零效果;b) 字面「bonds ∩ 名集」(读法 C)——类型不连贯恒空;
  c) 只收窄 :895 不收窄 offtarget(镜像误读,三轮 N4 存档)——病灶局
  outcome 巧合相同但五消费位视图分裂;d) **装配层键集对键集收窄**
  (读法 D,选定——单一源五面同值);e) 消费位逐个改判据——五处第二源,
  否。
- **收窄键集构成**:a) 仅核心羁绊——已达成弹性键(量子同频 tier2)的
  保护面丢失,成形引擎可被拆;b) 核心 ∪ 已达成档承载 flex(选定——
  声明基准 victim=忘归人与保护面=成形量子同频同时成立);c) 全量
  all_factions(现状,病灶本体)。
- **释放件资格路径**:a) 基座臂直接放行(arm='base',只查 up2——希儿
  系泄漏,否);b) 转型域统一资格族 + arm 恒 'transition'(选定);
  c) 仅 fenced 件走资格族——非 fenced 泄漏仍在,否。
- **让渡序首键**:a) 维持 1★ 优先——首件随星级巧合非结构确定性,否;
  b) 结构档边际贡献升序(P79-4,选定);c) 战力/评分键——禁战力建模
  (00 §1),否。
- **执行条件落点**:a) 排序理由(不拦发射——D-2 结论被稀释,否);
  b) 发射门(mandate M1″ 段,选定——「落码归属写死 = 发射门而非仅排序
  理由」);c) kernel select_swap_plan 内——谓词变策略门,hand-built
  ctx 与 sim 意图面被连坐,域语义混淆,否(发射⇔执行接缝不承载政策门)。
- **压席成本数值化(f≤1 带 C_sat 现算)**:a) 落 P_block×V_slot 点值
  ——V_slot 系 P76 【拟】挂账族,零调参纪律禁(否);b) 卖出态解析
  闭合(1★ 代价 0 ≤ C_sat ≥ 0,选定,零自由参数);c) f≤1 带全 defer
  ——病灶局即 f≤1 带,与治病目的矛盾,否。

## 后果

- 正面:病灶局帧 victim = 忘归人(1★ 零损,P41 甲.2)合法释放,锁线
  档关键件(罗刹型)到席→上场延迟收敛至 ≤1 备战帧(P79-1 每帧重评
  既有触发面直接受益);frame-2 起守恒门使候选收敛 = 一换止血;五消费
  位单一源同值;拒因全显影可归因。
- 代价/边界:①锁线转型域发射新增成员类轴,无压席成员/非档成员帧
  由「可发射」转 defer(保守形态设计意图,非回归;满量形态候裁翻
  开);②收窄的上行 blast radius(方案 §7 #9):is_tgt/_bench_is_target/
  post_sell_offline 三面口径随收窄变化,未锁域零差有锁;③档关键件
  判定钉面板口径——数据源修复会使罗刹型判定静默翻转(方案 §7 #12
  观测项,显式接受或回炉候数据源批对账);④sim 的 m1p 发射意图观测键
  (`m1p_intent_record`)不计本发射门 → sim 意图读数会高估生产发射
  (sim 本不建模 swap 执行,行为面无 A/B 判据影响,如实申报);⑤执行
  侧逐件卖出仲裁序(1★ 优先)与发射面让渡序分域并存——资格单一判定
  同函数保证不越资格面,序差属发射⇔执行既定分工(发射=存在性,
  执行=逐件),候选序对齐挂后续批。
- 驳回面申报:`test_base_victim_wins_over_transition_when_first`(转型
  域基座 arm='base' 标注)随决策 2 语义取代更新——ADR-0534 §5 在转型域
  被 P79-4/行 #5 取代,非机械跟绿。

## 锁面

`sr-od-test/test/sr_od/app/currency_war/test_cw_deploy_transition.py`
(新主题文件:双红对 victim=忘归人主断言+希儿形态四条件拒因键断言/
五消费位单一源锁/分键闭集扩展锁/执行条件门 defer 锁/未锁域零外溢锁/
病灶局帧复演锁,docstring 引本 ADR 与 T-127 方案 §3/§6);
`test_cw_swap_transition_arm.py` mandate 发射分键锁随门语义更新
(压席成员供给stub)。

## 修订记录

- **F1 修订(落地审 2026-09-08 05:25:14 报告,采纳路线①)**:装配收窄
  辖域由「locked 全域」钉到锁线转型域(决策 1)——初版使锁线成型帧
  (fp≥1.00∧板满)键集收窄,2★ 纯弹性释放件经成型臂绕过 star_guard/
  P41②/守恒门被无守卫卖出,与本 ADR 决策 2 及方案 §2.3「成型臂语义
  照旧」矛盾。修复后「域外语义照旧」三处声明与行为一致;F1-a(G1 准入
  victim 预估 all_factions 口径与本帧计划体的分叉)随成型帧回全量
  自动消解;转型域内准入口径残差属决策 8 已申报的 T-121 同源化出辖面。
  附随行为锁 = `test_formed_frame_released_flex_member_still_target_
  keep`(藿藿形态)。
- **F2 对齐(同报告备注,随手)**:执行条件发射门档关键件判读源改为
  装配 ctx 携带的 `target_comp`(计划实际消费 comp 视图,双轨口径随
  装配),ctx 缺读退 state_of 兜底(决策 4)。
