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
