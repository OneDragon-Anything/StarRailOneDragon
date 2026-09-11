# dd-035 P2 锁线可行性三维护栏 + 撤销出口③(供给不可行降级)

## 背景

R5 型死法族:锁线目标件**供给空缺**——P2 已锁线的核心缺件在店持续缺席,而撤销出口①(断供证据)的合法开窗门槛 N_req(由容忍概率 ε 从再遇窗口期望闭式推导,`core_miss_n_required`)按其推导式在 P2 视界内需要 21-42 轮不可得,而 P2 全位面只剩 7 节点——「既无法完成、又永远无法合法放弃的线」死守到底。修复批 REPORT = `.debug/temp/currency_war/line_feasibility_weighting/REPORT.md`(含 A/B 三轮收敛数字与逐帧证据)。

前置链:dd-033 落了 P2 目标移交(「锁线前先验证可达性」的移交面)与出口可逆;dd-034 落了 `PAIR_SUPPLY_CONFIRM_ROUNDS`(「出现观测 vs 缺席证据」的离散化换算)。本批把同一可达性验证补全到信号锁线与已锁线撤销两个面。

## 决策

### 单一源:可行性度量 G 与视界 H(kernel/cw_intention,零新自由参数)

- `p2_supply_horizon(state, session, registry)` → **H = min(位面剩余节点, ⌈hp / registry.vd_p2_loss⌉)**——「剩余轮 × 血预算」合取面:还能承受几次 P2 败战,就还剩几轮「等得到供给」的有效窗口。两输入均为既有单一源(位面剩余节点=ADR-0366 本位面真值;`vd_p2_loss`=P12/P21 已采的 P2 单战期望掉血,与 `p2_crisis_band` 同源)。
- `line_completion_feasibility(...)` → **G = ∏_缺件(1−(1−q_m)^H)**,q_m = `_core_miss_q`(cw_shop_odds refresh_prob × DISTINCT_CARDS_PER_COST 注册表派生,与 `encounter_window_rounds`/`core_miss_n_required` 同一静态近似)。缺件已在店/到手 → 该件因子 F=1(affordability 归花钱层,意向层不双计);某缺件该等级不出 → G=0。缺件独立近似构造性**高估** G,判据只用它做「不可行」侧的保守开闸,高估方向安全。
- 判据阈值 = 既有 `registry.revoke_miss_tolerance_eps`(ε);断供观测证据轮数 = 既有 `PAIR_SUPPLY_CONFIRM_ROUNDS`(dd-034 同一「出现 vs 缺席」离散化推导的线级同构)。

### 三个消费位(均在 update_intention,辖 plane==2;P1 配方锁/P3 强锁-降格语义零触碰)

1. **P2 移交强锁候选门**:handoff 候选补 G > ε;全不可行 → 保持 unlocked(⑤兜底,dd-033 原语义的「降级目标」面)。
2. **P2 信号缓锁门**:①②类信号线意向核心不在店 ∧ G ≤ ε ⇒ 本轮不锁(与 W607 H1 环境判据同款缓锁;核心在店的信号不辖——P25「核心出现即买」价值优先)。
3. **撤销出口③ 供给不可行降级**:已锁线 P2 ∧ 窗开 ∧ 核心不在店 ∧ G_locked ≤ ε ∧ 线内在店断供 ≥ `PAIR_SUPPLY_CONFIRM_ROUNDS`(观测证据,`LineTrack.member_drought`)∧ ∃替代线(G_alt > ε ∧ 替代线意向核心在店/在手=已验证可达)⇒ 降级 unlocked,证据快照落 `revoke_evidence{kind:'supply_infeasible', g_locked/g_alt/member_drought/...}`(serialize_intention 自动携带);次轮由 dd-033 handoff_lock 重锁可行线。**可逆设计**:不写 evicted(un-evict 同款语义);撤销当轮不接移交重锁(「一回合最多一次转移」纪律,`_p2_handoff` 补 not revoked 守卫)。

### P25 关系(边界)

可行性差 ≠ 不锁线:G ≤ ε 不没收已锁线、不拦核心在店的锁;出口③必须三证据合取才开火;全线不可行时**不折腾**(维持现任方向,任何换线都是 ε 级噪声);线内件买入义务(M2)零触碰。出口①(断供证据)与出口③的关系:①是「缺得足够久」的观测证据通道,③是「先验上永远等不到」的可行性通道——③开火不以①的 N_req 累积为前提,这正是本批要修的死法族。

### 附带:shop_unbought_reasons 拒因投影修复(decision/cw4/shop.py)

旧版只投影金不投影席/回金——M2 波内先买占掉末席后,同波后续线内件被席闸跳过会误标 `no_path`(应为 `missing_bench_full`);SellBench/SellDeployed/DeployMove 的席与回金现同步投影。并补**双栈语境声明**:sim 面的 `missing_no_path` 是 cw4 义务语义拒因分类器被套在 decision_v2 决策栈动作上的假异常标签(sim 决策走 decision_v2 栈不调 cw4 决策核),判读须先查 decision_v2 侧拒因(评分/copies_cap/预算投影),不能按 cw4 义务语义直接定谳异常。

## Considered Options

- **纯先验撤线(G ≤ ε 即可撤)**:A/B 第 1 轮实证误杀活线(s3 局——列车同行成员持续在售,纯先验判据却撤线换死线),avg_final_hp −1.23——**弃**;加断供观测证据合取——采纳。
- **断供无替代验证(只加断供≥2 轮)**:第 2 轮仍误杀 s3(引擎线可有 2 轮店隙),且替代线自己 G 也低时换过去是拿血量赌先验——**弃**;替代线须「已验证可达」(G_alt > ε ∧ 替代核心在店/在手,[23] 贯穿件语义)——采纳。第 3 轮终态:27/30 局逐位恒等,唯一分歧行局结局由发牌随机主导。
- **全线不可行也不折腾(不加出口③,维持现状)**:否证——R5 死法族的病灶正是「死守一条既无法完成、出口①门槛在视界内又永远无法合法放弃的线」;出口③的三证据合取+替代线可达门槛已把误杀面压到实证为零,撤销可逆+不写 evicted 再兜一层。采纳出口③形态。

## 后果与遗留

- 验收(摘要,详见 REPORT.md):新锁 13 条亲跑绿(`sr-od-test/test/sr_od/app/currency_war/test_cw_line_feasibility.py`);CW 快速集 2549 passed 唯一红 = w614 sim 保真 digest(行为变更预期)。sim 配对(n=30/臂,同池指纹 399e93da60da23d0,同 seed 0-29):分布中性(avg_final_hp −1.30、p2_hp0 13/30 vs 12/30、换线 1/30),差异全落单一分歧行局,在二项噪声带内**无定谳力**——不宣称改善,机制开火行为由单帧锁承载。
- 挂账:**sim n≥100 复核 + 实机多局验收**;回滚 = git revert 单操作。
- **R5 主死因判断修正**(给下一批):三轮 A/B 证据指向——「供给空缺死守」死亡在 sim 面不是锁线机制单独可解:换线候选的 G 同样低(0.05-0.18,换谁都完成不了)。真正的杠杆在 spend 侧转化(P48/P51 危机带让渡)与线价值模型(P25 卡点=Δλ_death 标定)。下一批落点移到 spend 侧转化与 P25 数值标定,锁线面维持本批护栏形态。
- 口径:本批 A/B 两臂均在池指纹 399e93da 上跑,与 dd-033/dd-034 批报告数字池不同,不可直比。
