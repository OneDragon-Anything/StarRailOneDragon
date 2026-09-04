# ADR-0516: V̄ 链退役 + 刷新/升级决策改路径总账比较(形式二)

## 背景

刷新决策推导批(2026-09-04,验收采纳)完成机制清单 M1-M13 与两形式对比后,用户裁定:

- **禁胜率建模**——V̄_net 链(修订单 R1 后 = Δp[plane]×单战价值×r)的全部因子端(分位面胜率边际、伤害金折算)都是统计拟合量,不属游戏定义量,整链退役;
- **刷新决策 = 路径总账比较(形式二)**——复用 P39 升级 EV + P40 刷新门 + P56 息线,判据输入全为游戏定义量(REFRESH_PROB 池参数 / XP 表 / 息律 / 连胜表),禁统计、禁胜率;
- **等级锚方向保留**(每费单峰等级锚,REFRESH_PROB 表值直证)+ 三修正(见下)。

## 决策

1. **V̄ 链退役**:`statefn/vbar.py` 改退役墓碑模块(v_bar_net/window_vbar/per_battle_value/streak_floor_gold 整链删除;streak_floor_gold grep 定夺无其他消费端);注册表 `win_rate_dp_by_plane` / `vbar_hp_value_transitional` 退役(墓碑注;STREAK_GOLD_TABLE 表值不动,连胜金真源仍在 cw_economy)。
2. **R1 刷新启动门 = 形式二的可负担性**:`c_eff·E(D|L*) + Σ卡费 + L(g, spend, R_剩余, Ī) ≤ 可用预算 = g − g*`(g* = 10×cap_resolved)。E = expected_refreshes_for_card 按缺件集与选定等级 L*(k=3 完成档为代码消费位;k=3/9/1 三档在文档判据面声明);L* = 形式二的等级选择输出(留级账 T_stay vs 升一级账 T_up 取小,升级账含 U_L = clicks×单价及其息损)。判据本体 = criteria/refresh.r1_commitment_account,装配 = shop.py(`_r1_ledger_terms`)。装配口径(对抗审查修复批申报):Σ卡费 = 每成员 (k−j)×cost(完成路径真实卡费,与 E 同档);R1 金基准 = 买后投影金(发射位在波尾,与 R2 同基准)。P40 R2 息线熔断保留原语义(R2 可追过滤随 L* 重估)。V_GAP 槽位比较项退役(provisional 槽位保留登记,消费端清零)。
3. **P57 搜索窗重锚塌缩带**:窗口判据从 V̄ 门式(p ≥ c_eff/V̄,双读法)改为 `refresh_prob(L,c) ≥ ω×refresh_prob(峰值级(c),c)`(ω = registry.omega_collapse_ratio,与 ADR-0475 refresh_ev_budget 归零腿同源)——读法①/②分歧问题随 V̄ 退役消解;calib e2_24.7 对拍锚同批作废。
4. **schedule_upgrade ② 臂补 U_L 阈值检验**(三修正①):升级 iff `c_eff·(E(D|L) − E(D|L+1)) + ΔV_pop > U_L + C_int`。ΔV_pop 按 P39 式 = w·1[板满 ∧ bench 有 2★ 等待件]（**勘误注**：该指示函数中「2★ 等待件」系本 ADR 撰写期的收窄形态，现行裁定谓词 = **阵营相关单位、不限星级**——2026-09-01 玩家裁定，权威声明 = strategy-docs 01 §2「玩家裁定三条」/02 §3 M3；star≥2 收窄形态已判废。ΔV_pop 的翻转语义不变，谓词读法以现行裁定为准）(w 待标定禁计值 ⇒ 指示=1 视为翻转项、指示=0 时纯概率账须独自过阈);C_int = P47 L(g, U_L, R, Ī)。裸「峰值级>当前级」直觉缺此检验会在小移位带过度升级。**单核代表降级申报(对抗审查修复批)**:规格的 E 为缺件集 ΣE_i,实现取单目标核心代表(缺件集装配在 strategies 侧,kernel 判据禁 import strategies)——多成员同受升级受益帧检验偏严(保守向),成员在 L+1 概率回落帧单核可能高估净受益(边界注)。**cap 三源归一(对抗审查修复批)**:本检验的 loss_exact cap 参数与 ② 前置息线共用 `cap_resolved_of_session`(session resolved 链;`registry.interest_cap×10` 不再辖本前置——裸缺省 cap 5 在息律投资 cap=10 局低估 C_int)。
5. **实现下沉**:loss_exact / net_income(→ kernel/cw_economy)与 r_global/r_remaining(→ kernel/cw_plane_table)实现下沉、statefn 模块 import 重定向——kernel 判据消费这些量须保持「kernel 禁 import strategies」桶依赖矩阵;消费方调用零改(与 schedule_upgrade 下沉同款先例)。

## 三修正(推导批直觉对错清单的反例承载)

1. **升级费 U_L 阈值**:反例 = 希儿 lv7 概率侧省刷费 28 < 升级金 40,纯概率账亏 12,靠人口位 ΔV_pop 翻转——由决策 4 承载。
2. **路径总账 vs 贪心**:反例 = 缺花火+希儿时,留 lv6 双买账 123 < 买花火升 7 再买账 135——贪心序(先买在售件)不总优,由 R1 门的 T_stay/T_up 两侧枚举承载。**近似口径注**:双卡数字属可推区间 127-145 的代表读数(账式含 Σ卡费/息损随帧浮动的分量)——「贪心序多付」的方向结论不依赖具体读数;逐位复现口径 = **j=0 双卡纯刷费项** stay 侧 2×(23.7+38.1)=123.63(完整 T_stay 另含 Σ卡费 15 与息损 L ⇒ ≥138.6;up 侧随花火 j 假设浮动,j=0 起 135 量级)——两数字均为同口径刷费项读数,非完整总账逐位值。
3. **息线双侧**:停级买牌也压金破息——刷新与买牌两侧都过 L/g* 账(R1 可用预算 = g − g*;买面 = P56 可变现口径),由比较式结构承载。

## 行为影响

R1 门从「V_GAP 槽位 None ⇒ fail-closed 零刷新」变为「预算比较恒求值」:金在息线及以下恒不刷;大溢余 + 可追缺件帧开刷(帧级锁 = test_cw_vgap_frame_horizon / test_cw_zero_refresh_fix)。E(D|L) 取**完成账语义**(用户裁定 2026-09-04:等级服务整套目标阵容缺件集的补齐——任一成员该级不可追 ⇒ E=∞ ⇒ T(L) 不可行,等级比较指向整套可补齐的层级;混合峰级合格集的开门率收缩为设计内保守)。搜索窗由 V̄ 门式改塌缩带锚后,ω 窗较旧 V̄ 门**放宽**(V̄_net 门把窗口压在「刷新价值高于门槛」的窄带,塌缩带只按 ω×峰值概率比例截尾——低概率长尾多收进窗,方向性影响申报,量级归 sim 对拍)。schedule_upgrade ② 臂收紧(小移位带不再排程);测试重锚:w633 排程锁改 4 费大移位带帧(2 费小移位带帧被正确收紧)、statefn 窗口表改 ω 锚全表、p57/vgap/zero_refresh/r2_floor 按新判据重写(锁语义 = 新判据,非机械跟绿)。实机不跑(用户冻结:重设计落码前零实机;本批 = 落码批)。

## 备选

- 保留 V̄ 链挂标定接口——被否:用户裁定禁胜率建模,标定无从附着(ADR-0515 同构)。
- R1 门比较项换 sim 标定值——被否:违背「判据输入全为游戏定义量」的裁定,且 A/B 无裁决权。
- 搜索窗保留 V̄ 门式等标定——被否:窗口语义随比较项退役失去载体,塌缩带锚零新自由参数且已有 ADR-0475 先例。

## 关联

推导批裁决(流水 2026-09-04,验收采纳);P53 修订单 R2 + math_proofs P53 行退役标注(证明侧);P39/P40/P47/P55/P56(接缝);ADR-0515(前批因子清退);实现 = statefn/vbar(墓碑)/odds、criteria/refresh+contracts、shop.py、cw_registry/cw_economy/cw_plane_table、statefn/interest+income+horizon(重定向)、audit/provisional。
