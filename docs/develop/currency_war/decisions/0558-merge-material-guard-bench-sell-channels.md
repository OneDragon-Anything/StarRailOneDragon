# ADR-0558: 合成素材拒入守卫(G-S1)——bench 卖出通道资格补「场上同名同星计数」维,与部署侧 merge_material_guard 同键单一源

- 状态:已实施(落地审两阻断修复后定稿:ADR 补立/锚修正 + F-1/F-2/F-3 三非阻断处置随批)
- 关联:`cw_state.same_star_count`(计数单一源)、`cw_deploy_logic.swap_sell_exclusion_reason`(部署侧同键拒因闭集,ADR-0534)、merge_mechanics.md §1/§2(合成机制口径)、P41(燃料类支配性论证,素材升格中间类)、P56(活期投影第五消费面,F-2)、P60(换手收敛性质,守卫只扩排除集)、ADR-0534 §3(单一源纪律)

## 1. 背景与问题(两案同根缺口)

两实机局同根:合成素材的价值(距 2★ 差一张的确定性升星进度期权)不在 bench 卖出资格谓词的判据维里——

- g_20260906_081836 P2r1(resume):bench 卡芙卡 1★ + 板上卡芙卡 1★ 并存(2/3 进度),凑息通道按 (star, slot) 序 2g 卖断——唯一 2★ 升级路径被卖出侧自己拆掉;
- g_20260906_095111 P2r1(hp7 濒死帧):bench 藿藿 1★ + 板上藿藿 1★(P1r3 首买+P1r8 囤腿),SellBench bench_idx=1 +1g。

根因:同名同星计数在买侧被多处判据消费、在 deployed 卖出侧有 `merge_material_guard` 守卫,但 bench 侧全部卖出通道(M4 燃料/凑息卖/支付变现/换线塌缩)资格谓词不读该量——素材与普通垫件在判据层不可区分。P41② 文字辖域未被违反,是分类判据把素材错分进燃料类(素材边际贡献 = 确定性进度,≠0,类资格不满足)。

## 2. Considered Options

- **A(采纳)G-S1 核心守卫**:新增合成素材子谓词 `cw_state.merge_material_reject_reason`,判 `c_excl = same_star_count(name, 1, bench∪deployed) − 1 ≥ 1` 拒入资格集,拒因键与部署侧同名同键;五发射位各自调用子谓词,**各通道原有资格谓词一律不动**(禁把整段资格谓词共享进 line_switch——那会给换线塌缩凭空加过滤)。零新参数、fail-closed、与 P41「中间类标定前持有」章程同构。
- **B(否决)整段资格谓词上提共享**:给 line_switch 强加零重叠/后台效果/排除集三维 = 改变现行换线塌缩行为,无数学重推背书。
- **C(否决,二期)G-S2 翻转比较式直接落码**:翻转条件 `V_slot + V_gold需求 > V_merge_progress` 的 W_2★(2★ 战力边际定价)**无在册标定来源**(P30① 的 V(1★→2★) 通道未标定)——比较式无载,按 fail-closed 原则本期守卫恒拦。**PREREG 申报(锁5 口径)**:W_2★ 标定落地前,G-S2 必须走 fail-closed 不卖分支,禁无 CI 值静默进闸门(P41 五门先例同构)。

c_excl 判据的数学边界:同名同星满 3 即自动升星且不变量「场上同名同星 ≤1」(merge_mechanics §1/§2)⇒ c_excl≥2 稳态不可达,守卫生效域恒为 c_excl=1(2/3 进度,缺 m≡1)。

## 3. 已实施架构

- 守卫单一源:`cw_state.merge_material_reject_reason`(消费 `same_star_count`,禁消费方手搓同式;docstring 承载判据/辖域/出处)。
- 五发射位:M4 燃料(`mandate.fuel_sell_candidates`,shop.py 三个 M4 消费位+mandate 腾席环随其覆盖)、凑息卖 `sell_for_interest`、支付变现 `funding_support_sell`、换线塌缩 `line_switch_sell`(criteria/sell.py 三函数体内)。
- 拒因分键:`merge_material_guard_blocked` 同键计数(counters 可选参数;生产接线=凑息 shop.py 一处+M4 mandate 腾席环/shop 三处+支付 entry 两处/shop 一处,F-3 补全后全发射位显影)。
- 锁(测试仓 `test_cw_merge_material_guard.py`,16+ 条):单帧锁×4通道+换线帧+对照零漂移 / 单一源 grep 锁(定义点唯一+四发射位各自引用+策略层禁手搓) / P60 收敛性质保持锁(拔守卫对照=移除即红) / 两案发帧回放锁(k_members 经 `k_empty_window_fallback` P2+ 带单一源派生,禁空集假设) / P56 活期投影面锁(F-2)。

## 4. 边界申报

- **配对一致性(R2-5,accepted loss)**:守卫只护 bench 侧;deployed 侧 swap 路径存在不经过 merge_material_guard 的出口(`offtarget_sell_allowed` 放行早退先于守卫)——deployed 副本经该出口被卖则 c_excl 归 0、bench 守卫下帧放行,素材保护实际强度 = 两侧保护窗交集、退化形态 = 延迟一帧。deployed 侧同辖收口归 cw_launch_admission 决策下沉面另批,本批不提前同辖。
- **第五消费面(F-2)**:`fuel_sell_candidates` 同时是 P56 `s_reserve = g* − Σ活期退金投影` 的活期资格单一源——守卫使其收缩:素材在场帧 liquid_refund↓ → s_reserve↑ → 买面判据变保守。方向正确(投影口径 = 可执行卖出集,守卫后更真),已补单帧锁显式钉方向。
- **滞留显影欠账**:`merge_material_stale`(素材滞留纯计数,G-B1 第四级)未落;G1-only 期素材只滞留不增值是预期形态,拦截事件观测走 `merge_material_guard_blocked` 分键。
- **分期声明**:G1-only 期验收 = ①卖断素材事件计数=0 ②滞留可读且不恶化 win ③win 率不劣;**「2★ 合成完成数↑」不作本期判据**(归 G-B1 二期)。G-B1 四级申报(定向刷新扩窗[P1 unlocked]/P2 增值设计件[另立]/比较式视界截断/滞留显影)随本 ADR 在案,未立项。

## 5. 风险与后果

- 素材在场帧凑息缺口覆盖能力下降(素材不再可卖)——分期 A 预期形态,滞留代价由 G-B1 增值侧承接;sim A/B(守卫开/关 n≥200 同 seed 配对)归验收批。
- 锁语义连带:既有档案帧锁若以素材为凑息对象须按「锁语义重推」改载体不改意图(先例:test_cw_must_spend_zone 十九局 r6 帧,bench 单位改非素材垫件,docstring 记录重推理由)。
