# ADR-0521: P2 锁线购买口径切换(locked_comp 单一源)

- 状态:已实施(代码+测试;ADR 为行为语义变更补档)
- 日期:2026-09-05
- 关联:01 §3.1(M2 骨架义务)、ADR-0357(P1 配方锁帧 locked_comp 恒空)、复盘 g_20260905_035710(七轮 0 买实证)、策略审查 0520/0545(P0-1 定性=实现断裂非设计缺口)

## 背景

第四局实机(g_20260905_035710)P2 段:p2r1 锁「列车同行」成立后,r1-r7 连锁内阵营成员(丹恒·饮月/开拓者·欢愉)被拒 non_line,七轮 0 买、金 14→86 滞留,hp 45→3。

## 根因

买入 membership 判定消费 `shop.py → line_members(target_comp)`(comp core∪shared,列车同行仅 4 人),而锁定采购集正典是 `cw_intention.locked_buy_scope`(含阵营∪流派全集成员)——双源断裂:锁线状态建立后购买侧未切换口径,M2 骨架义务(锁线成员照买)被违反。

## 决策

1. `cw_intention.locked_buy_membership(ist)`(kernel 层单一源,依赖方向 kernel←strategies):locked_comp 非空 ⇒ 返回 locked_buy_scope;P1 配方锁帧(locked_comp 恒空)/空窗/weak ⇒ None。
2. `shop.decide_shop_action` ①方向段:K 空窗回退后消费该函数,非空则 k_members 切换为锁定采购集——下游拒因遥测/M2/M4/dominance/EV/R1 账全链参数化自动同源。
3. 消费点裁决:proof.py(成型/干旱口径)与 entry.py(部署域)不切换,语义依据申报;entry.py 部署面是否同切归跨件半问 sibling。

## 后果

- P1 无锁态行为零变化(回归锁钉死);P2 锁线帧锁内成员进买入义务集,拒因从 non_line 变 missing_*。
- 已知边界:锁线断供期(锁定采购集也无供给)仍无救援通道——归「落后即消费」架构件(触发输入限非 hp 量,00 §3 硬闸门约束),非本 ADR 辖域。

## 验证

ruff 净;六锁(事故帧直译/拒因遥测/单一源对拍/P1 无锁回归/边界)全绿;CW 快速集 2181 passed / 1 skipped(ZeroDriftAnchor 指纹守卫按设计)。

## 修订(2026-09-05,合并审计 F1-F4,d87ae866)

决策 2 的「下游全链参数化自动同源」表述被合并对抗审计推翻并修正:M4 腾席(fuel_sell_candidates)/funding/凑息卖(卖免面)与 R1/R2 刷新账维持 core∪shared 口径,不随锁定采购集翻转——否则锁内 hoard 全集免卖塞满 bench + M2 积极买入 ⇒ 腾席候选空集,「金滞留不买」停滞换拍复发。现口径三面拆分:买面=buy_members(锁定采购集,消费 M2 义务/M2b/拒因遥测/EV 排除);卖免面=k_members(core∪shared);刷新账=P40 A4 目标阵容件。transition_pair 成员维持 ADR-0367 二级囤货定位不升骨架义务。收敛性挂账:锁线 hoard 集换手循环(buy_members≫bench 9 时 M4 每帧卖 1 买 1)的收敛性可证未证,立项候选(结构级命题或 sim 定谳)。

## 修订(2026-09-06,P60 结构级定谳回写)

收敛性挂账由 `proofs/p60-locked-hoard-churn-convergence.md` **证伪定谳**(结构级,帧级构造已充分,sim 定谳不再需要):大 hoard 锁线族(|B|>C,注册表 5 comp)出口 missing=∅ 结构性不可达,且燃料集与买入集相交(Fuel排除集=k ⊊ B)使 Φ 无单调保证——永恒卖 1 买 1 换手(净金≈0 + drought 被买动作重置 = 伪装进展)。治本(本批落地)= **三卖出通道(M4 燃料/凑息卖/支付支撑卖)统一排除 buy_members**(`exclude_names` 注入,与 EV 排除集同款)——Fuel∩B=∅ ⟹ Φ 单调、循环 ≤|B∖k| 次收敛;|B|>C 行为变为诚实停摆(m2_retry_exhausted/bench_full_buy_abandon 计数 + `shop_hoard_over_capacity` 帧级告警)。伪装进展观测面:`shop_churn_pair_buy`(买回近期卖出成员)计数 + drought 重置按来源分键(`shop_drought_reset_on_buy`/`shop_drought_reset_on_churn_buy`)。义务分级候选(M2 义务序收窄 B)仍归设计层待 ADR。
