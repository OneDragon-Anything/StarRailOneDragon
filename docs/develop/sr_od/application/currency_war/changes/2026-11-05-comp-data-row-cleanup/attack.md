# comp-data-row-cleanup 对抗审查记录

> 外部 subagent 攻击轮再次通道失联（finished 后报告未送达，一次催收亦未回——与 equip-taboos 轮同症状，通道问题重复出现已非个例）；攻击方向按任务书五向由编排者自完成，全部证据为本轮实际 grep/读码/脚本验证。

## 攻击点清单

### A1【应修→已纳入】flex 消费完备性

- 验证：grep `flex_factions|all_factions` 全域（src + tools 显式路径）——消费点全集 = invest_channels:177（唯一 flex 直读）、all_factions property（launch_admission + flow×2）、建库校验/数据定义；**sim/telemetry/decision_payload 零消费**；tools/ 零命中。设计清单完备 ✅

### A2【验证通过】6 处重叠键档位归属

- 脚本实测：六处重叠键（护盾/减益/击破/护盾/战技点/减益）**全部在档 1**、无一在档 0——删 flex 侧后 invest_channels 走 bonus 降档分支（同分值）、all_factions 集合不变、L2/采购面（只读 bonus）不涉及。恒等成立 ✅

### A3【验证通过】need_star 消费完备性

- grep 全域：消费点全集 = levelup:198（停留门遍历）+ priority 装配/消费（.get(name,1) 数值形态）+ cw_comps 数据/过渡组合生成器；sim/telemetry 零消费；tools/ 零命中 ✅

### A4【验证通过】priority :292「达标成员不缺省」注释语义

- 读 :286-299 全文：注释对照的是「不用 unfinished_star_targets 装配」的方案选择（只收未达标 vs 全量照录），非「值=1 行去留」。删 1 值行后装配仍是全量照录（字段全量 = ≥2 行），「need≥2 成员必须在表」的防线场景不破坏。注释无需改 ✅

### A5【应修→已纳入】测试面三处红旗排查（全安全/仅注释）

- test_cw_comps:267 锁希儿量子 flex `['盛会之星','列车同行']`——该套档 1 = 战技点/治疗，**与 flex 无重叠**，断言恒过（虚警）；
- test_levelup_prob_axis:62-68 用真注册表构帧，_AUX_DONE 语义 = 「辅助 need=1 持有即完成」→ 清理后 = 「辅助不登记（缺省 1★）持有即完成」，**行为恒等**，:63/:66 注释措辞随批更新；
- test_mingyun_grants:10 注释引「双套 need_star=1 旁证」→ 清理后旁证形态 = 双套不登记，注释措辞随批更新。
- 校验误伤排查：测试桩构造 need_star 全部值 ≥2（test_priority/test_deploy_search）；cw_transition_library 桩是 TransitionBond 非 Comp；**删行后 21 套 need_star 仍非空**（脚本实测，derivation_locks:185 断言安全）；过渡组合 need_star 源值 2/3 无 1——两条新校验零误伤 ✅

## 落地后修正（A6 反转——本迭代最重要的一条）

### A6【验证错误→落地撤销】need_star 值=1 行不是死行

- **拦截证据**：窄子集测试 `test_priority.py::test_locked_frame_need_star_full_transcription` 落地后红——`:536` 断言 `stay_target[0] == '藿藿'`（双王局，藿藿 need=1 未持有 = 停留刷牌目标）。
- **错误根源**：本攻击轮 A3/A5 与设计 §2.2 的「levelup:198 遍历形态 need=1 恒不触发」论证**读码错误**——`unfinished_star_targets` 的完成判定是 `_held_max_star < need`，**未持有成员 max=0 < 1 → 入未完成目标集**（「首张即目标」停留语义，levelup docstring :179 明写「辅助 1★ 持有即完成,未持有者入集」——读到了却没算进恒等矩阵）。「与 priority 缺省 get(name,1) 等价」只覆盖一个消费端，遍历读法下「表内有无条目」就是行为。
- **处置**：need_star 全部清理撤销（59 行数据、值域校验、docstring 口径、正本措辞全部回滚），字段 docstring 补防再犯注记（「1★ 行是活数据，勿按缺省等价误判清理」）。
- **教训（同型于 equip-taboos 轮 A1 的验收口径教训）**：自审对抗会犯它要防的错——「已验证恒等」的标签不可信，**活测试断言才是底线**；本轮若直接全量跑（而非窄子集优先）会在更晚暴露。凡「死行/零行为」判定，必须对每个消费点区分**读法形态**（查询缺省 vs 遍历成员资格），遍历形态下与缺省等价的主张一律不成立。

## 结论

五向自审 + 落地后 A6 反转修正：flex∩bonus 清理定稿落地；need_star 清理撤销（活数据）。外部通道失联已如实登记。
