# ADR-0470: P1 血预算停付防线的终止分支(止损转支出,terminal_release)

> **半亡注**:terminal_release 决策位活(discipline.terminal_release_bit);文中 allocator 相关半句对象已死(decision_v2/allocator.py)。

## 1. 背景与问题

W643 定钉(W643_repro REPORT §1-§3):主窗 16.5% 局以「P1 出口 hp≤10 ∧ 出口金>50」结束,停手窗均值 2 轮、金净上行,主形态=破息持有下的低效消费。机制链:血预算停付族(停升级 ADR-0448 / 搜索型刷新停付+末窗支出降格 ADR-0451)在「死亡已不可避免」的域内仍锁死消费——而该域内金留到死=零价值(金随死亡清零、息无从谈起),防线应让位给「死前能兑现战力」的当轮转化支出。

## 2. 决策

discipline 层新增终止分支谓词 `terminal_release(state, session, registry)`,判据链:开关 → `state.plane == 1` 硬门(首批 P1 only)→ 位面内触发闩 → 非位面末 ALL IN 窗 → `hp_decision_trusted` fail-closed → `S0 ≤ terminal_survival_eps`。其中:

- **S0 = Π_{i∈K} p_i**(守钱世界存活概率上界),K = {剩余场 i : L_i ≥ hp}(单发穿透链,一败即死必须全胜);L_i/p_i 全走既有标定单一源(battle L=vd_p1_loss_*、encounter/boss L=streak_floor_loss_damage、p=streak_floor_win_rate 注入表);rung 取 deployed 域 0-2 钳制(与连胜地板同源);K=∅ → S0=1(空链恒真不触发)。S0 忽略非穿透场累计失血 → 是真存活概率的**上界**,用上界做触发 fail-safe。
- **ε 默认 0.03**:EV 对比式反解 ε* = ΔS·V_live/(g+ΔG),最悲观角(ΔS=0.02、V_live=300、g+ΔG=212)≈0.0283;诚实带 [0.03,0.10]。重标定挂账:p_i 表为 sim 档证据、Δp(piece) 与 ε*(g) 随金自适应未标定,实机真值 n≥30 后全带重推。
- **三门接线**:①`blood_budget_refresh_blocked` 在 ALL IN 豁免后加终止豁免,且须过**当轮转化双门**(bench 空槽 ∧(deploy 空位 ∨ 存在 1★ 板面垫底件)——真约束是 deploy 槽非 bench 槽;板满帧战力兑现延到次战之后,不进释放辖域);②`p1_directed_downgrade_active` 加终止短路(降格的隐含前提「血预算还值得保」在死亡域被金零值引理压没);③**停升级门不豁免**——P21 数学:濒死升级 EV=−C−I 严格为负,与金是否零价值无关。
- **适用边界(防错误引用)**:P21 全负结论辖 p≤0.30 ∧ Δp≤0.28 ∧ V_live=300;网格外存在翻正点(p_post≳0.32、注入表 rung2=0.315 已在邻域)。不解除停升级的理由是频率与代价判断,不是「P21 已证全域为负」。
- **位面内触发闩**:本位面首次触发后恒释放(session 载体,位面切换由 plane 键控失效)——对冲释放后买件升 rung 使 S0 回升越 ε 的邻域抖动;金零值引理单调性(hp 只降不升)保证不存在「触发后又该守钱」的反悔世界。
- **记账与检查器分工(R4)**:谓词闩位经 `terminal_release_bit` 单一址写入 sim 账本行 `terminal_release` 位与实机遥测 `sess_terminal_release`;检查器**禁同式复算 S0**(守卫与被测同源时,S0 实现缺陷在同批误放帧同样豁免,段级守卫对最危险失败模式失明)——`seg_check_p1_blood_budget_refresh` 改吃账本位(带内刷新 ∧ 位假=违规),新增 `seg_terminal_release_ledger`(终止位帧刷新拒付与账本位矛盾且双门按行内快照可开=账本错位违规;双门复算只用槽位真值,与禁令不冲突)。S0 公式正确性由测试仓闭式对拍单帧锁在 L1 层承载。
- **首批不放**:卖件腾槽路径(装备/合成素材损失 sim 不可见)、P2 扩辖(P2 帧 S0 极小,无硬门会形成不消费 P2 参数的第二判定源)——均留独立批。预算层(`refresh_ev_budget`/`schedule_upgrade`)一字不动。

## 3. 数学依据(金零值引理 + EV 对比式)

若 S0=0,守钱世界一切资产价值=0,任何使 S1>0 的支出严格占优——终止分支在极限情形是定理。量化:守钱价值 = S0·(V_live+g+ΔG),转支出价值 = (S0+ΔS)·V_live,释放占优 ⟺ S0 ≤ ΔS·V_live/(g+ΔG)。ΔG≈+40(停手窗均值 2 轮 ×(位面收入 15+息 5),漏此项会高估守钱——停手窗金净上行实证)。

## 4. 被否决的替代方案

- **只放刷新**:降格压掉的定向战力买是「低效消费」的另一构成,只放刷新留半个病灶;
- **三门全放(含升级)**:P21 数学禁止,且新追级泵污染 A/B 主判;
- **改预算层**(预算字段在死亡域归零):破 W635-F1 契约边界——预算层是「怎么花」的 EV 核,拒付层是「许不许花」的纪律面,终止分支全部落在拒付层;
- **检查器同式复算 S0 做豁免**:守卫与被测同源 → 公式缺陷双盲(R4 废止理由)。

## 5. 验证

新锁组 `sr-od-test/test/sr_od/app/currency_war/test_cw_p1_terminal_release.py`(S0 闭式对拍 K 空/单场/两场/双节点链;终止帧三断言一体;非终止帧零漂移;不可信帧 fail-closed;双门四象限;滞回闩+P2 硬门;一致性检查器两构造反例;账本位单源)。既有锁改判:`test_cw_blood_budget_stop`(终止帧仍拒升级对照用例)、`test_cw_blood_budget_wave2`(辖域声明「血预算带=非终止帧」+终止帧反例+检查器位豁免用例)、`test_cw_hp_trust_defense`(不可信帧不触发终止分支)、`test_cw_adr0293_calibration`(registry 字段面登记 terminal_release_enabled/terminal_survival_eps)。A/B 判据(PROTOCOL 冻结件,归编排者):主判=停手形态占比降 ≥1/3;守卫 G4 终止位翻转/局 ≤1、G5 终止位占比分布带;`seg_break_interest_exception` 守卫改「非终止帧破息例外计数不升」(FM-9,PROTOCOL 冻结前落笔)。
