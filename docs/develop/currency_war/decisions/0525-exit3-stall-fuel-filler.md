# ADR-0525:出口③ Φ_stall 过渡件垫件出口(有界成本结构改善授权)

## 状态

已实施(2026-09-05,落地审零阻断;commit = 发射位接线批)。

## 背景

P2 深血域连续三局(15/16/17)实证「深血无转化出口」死握三形态(供给没件/囤金不花/预算门卡死)。17 号稿(§1.1/§7)设计 Φ_stall 过渡件垫件出口:锁线态下不可追支(D=∅)∧ 富金(g>s_reserve)∧ 板深赤字(δ_board>0)帧,买入 1★ 垫件重开搜索集。设计稿对抗三轮(r1 阻断降格出口①/r2 三规格前置/r3 B-1 单点修+聚焦复核零问题)。

## 决策

1. **授权定性**:净成本 ≤1 金(注册表派生界:Δ息∈{0,1},cost≤5、息帽 5)的**有界成本结构改善授权**,零自由参数;严格支配仅 Δ息=0 帧成立。禁回退「无条件授权」旧措辞。
2. **触发谓词**:Φ_stall 四支 = D 支锁线布尔(locked_comp 非 None,禁接 form_progress 成型门)+ A 支合格集空(含成因支与概率对账 fail 向)+ C 支 δ_board>0(level_readable 守卫)+ B 支 g>s_reserve。
3. **资格单一源**:垫件 = 1★ ∧ ∉ buy_members(ADR-0521 对账闭:排除集 ≡ locked_buy_membership)∧ zero_overlap(k_members)∧ refund_full_star_ok。
4. **发射位次**:M6 压库后、EV 前(11 §7.3 垫底级辖域扩展:「未锁线期」→「+ 锁线后 Φ_stall 帧」;与 §5.2(b)2 同消费位两触发源,Z1 确认批落地后 ∨ 合并)。
5. **七分键零静默**:buy/fenced/precheck_unavailable(与 fenced 禁混键)/fuel_not_on_sale/bench_full/below_reserve(发射位)+ held_postbuy(执行侧闭环)。

## 后果

- 行为翻转:Φ_stall 帧从全通道静默 → 垫件买入授权(锁线态首开金支出通道)。
- 依赖:can_deploy_single kernel 单一源('unannotated' 缺因显影);record_fuel_filler_held_postbuy 消费口(5f318567)。
- 边界:空编制位零贡献命题维持 fail-closed(§7.5-①,不阻塞本授权);出口①(升级扩位)独立挂账,不与本出口捆绑。
- 负向锁(四支 fail 向形态)候补强轮补齐(落地审存疑项)。
