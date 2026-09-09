# ADR-0621: T-171 批序 4 希儿系静态套成型判据 OR 口径（OR 组承接同键档位折法）

- 日期:2026-09-09。批=T-171 批序 4(静态套 form 口径 OR 分裂修复);审查=.debug/temp/currency_war/attacks/t171_static_or/落地审-问题清单.md(方案面+实现面合并对抗)。
- 落地审结论:方案面四问全过(挂腿方向/键级语义边界/形态 B 否决/无漏第三形态);实现面 pair 键集不相交声明核真等全过;阻断 B-1=本批 ADR 缺位且 7 处指针误指 ADR-0620(T-157 投资注册表定谳,与本批零关联)——本文件即 B-1 修复正本。

## 病灶

COMP_LIBRARY 静态套「希儿量子」成型判据为 AND 完全体(form_tiers 量子同频 4 档∧贝洛伯格 2 档全满),与策略文档口径分裂——transition_combos.md:27「希儿在场∧(量子同频≥2∨贝洛伯格≥2),不设完全体门槛」(combo_methodology.md:133「凑到任一=成型」/:143「放大器不需要最大档」)。实测锁线对 form_ok 1/11 vs 对照 81/89,换线/采购/停手判据被系统性压制;验收局量子 3+希儿在板已成型而 fp=0.625 恒 False。

## 决策

1. **判据常量真源归位注册表数据层**:`cw_comps.SEELE_OR_LEGS=(('量子同频',2),('贝洛伯格',2))`、`SEELE_CARRY_CHAR='希儿'`。静态条目在 import 期消费常量,常量若留 cw_intention 会反向 import 成环,故真源落 cw_comps;cw_intention 侧同值常量暂为**双定义恒等态**(过渡),由测试仓恒等锁钉死两侧相等,改指 cw_comps 的一行机械改挂账随 T-35 批(cw_intention 触达批)执行。
2. **静态条目挂 or_legs+required_deployed**,与 ADR-0613 pair 物化路径同构:同一折法 form_progress、同一判据常量,零第二套判定。
3. **OR 组承接同键档位(键级辖域)**:form_progress 中 form_tiers 与 or_legs 同键的档位不计入 AND 账(分子分母同免);档位值保留作结构载体——囤货采购集羁绊展开/_line_hoard/locked_faction_scope/换线距离账读其键值面,清空即残(银狼/佩拉/桑博掉出采购集)。
4. **量 2 vs 量 3 维持候玩家裁决**(transition_combos.md:27 量 2 定义行 vs combo_methodology.md:133/170 量 3「关键补充(用户修正)」):确认后改档动 SEELE_OR_LEGS 一处+恒等锁两侧,另须同步第三表面 `_seele_system_support` 的 ÷2 分母(cw_intention.py:583-587;公式体用字面量不消费常量,恒等锁钉不住——落地审 B-3)。

## Considered(否决面)

- **形态 B 保留 AND 完全体**:否。门与账单(commit 门/armed 配方腿/encounter/_comp_formed)读的就是 form_progress/form_tiers,保留全档=保留病灶。
- **档级承接**(只免 量 2 档、量 4 仍入 AND 账):否。量 4>量 2 部分回到 AND 账=病灶回归;键级辖域闭合且不误捕(pair 伪 comp 剥离 amp_keys 后 or_legs 才非空,cw_intention.py:926-931;分支①/非希儿对 or_legs 恒空)。
- **清空 form_tiers 的 literal 同构**:否。三结构消费位(_line_hoard/locked_faction_scope/line_distance)读键值面,清空即残。
- **降档形态**(form_tiers 写低档):否。键侧 AND 语义装不下析取。

## 已知边界与挂账

- pair 恒不相交依赖数据不变量「BRIDGE_POOL 无 量子同频/贝洛伯格 键」(现由 ADR-0350 封存保证);注册表不变量断言随批补锁(落地审 B-5),防未来桥池数据更新时分支①精确匹配产出纯 AND 伪 comp 静默回归。
- 「bench 在手不算在场」判别性负例随批补(落地审 B-4;批序 1 同款锁的 st_on_bench 帧变量名失实——桑博实际在 deployed)。
- 静态套换线 line_distance/e_rounds 保持原完全体距离账(ADR-0613 已申报既有残差族),正确折算归换入门批,本批未新增畸变。

## 验证

- 病灶帧 fp 0.625→1.0;行为四象限:量 3 贝 1 成/贝 2 量 0 成/量 1 贝 1 不成/量 3 无希儿不成/希儿单卡不成。
- 变异红证:M1 静态腿回退 8 红/M2 承接规则删除 10 红/M3 常量单侧改档 1 红,还原全绿零残留。网格锁断言①(fp≥1.0⟺form_ok)系同函数恒真式,任何变异下不红,变异红证由网格②与其余锁承载(落地审观察,红证申报据此口径)。
- 测试:test_cw_t171_form_or.py +13 锁(26 绿);受影响域 9 文件 265 绿;CW 快速层 3468 绿 0 失败;ruff 净。
- 落地审 13 锁断言值手工重算全部无误;实现与申报方案无落差(B-1 外零阻断)。
