# 0384 — 补偿器卖件组批量下界过滤(136 型聚合窗补偿通道闭合)

- 日期: 2026-09-01
- 状态: accepted (采纳)
- 关联: ADR-0380(卖侧下界执行点补全——本批补其边界声明不实处)、ADR-0373(卖侧唯一体系引擎守卫语义单一源)、W203(①A:边界表「补偿器=逐笔渐进态」与代码不符的巡检实证)、W197/W201/W202(own_gap 锚链)
- 批: W205(件②)

## 背景与问题

W197/ADR-0380 边界表声明「carry_gate ④ / 两补偿器 | sell_priority_key
(逐笔渐进态) | ADR-0373 既有」。W203 巡检亲读证伪:`_compensate_gold/
_compensate_bench` 的卖件候选列表对批前 `state` **一次性构造**,
`sell_priority_key` 内的 `sole_engine_sell_blocked` 对 state 单次
评估,组内取前 k 笔发射——**无逐笔重评、无前序扣减**;补偿组在
`_run_remediation_pass` 只过三资源约束重验,不走卖侧下界复检。
因此 136 型同批聚合窗(组内两笔**异名** TT 件各见 count=tier+1、
逐笔合法,合计跌破 tier)在补偿通道结构上存在。同名双副本被
`star_weighted_copies≥2` 挡,故可命中形态=同体系两个不同成员。

实证面:W197/W201 两轮 n=300 own_gap 名单恒 [136,269] 无新增 →
该窗未显现命中(与 136 当年 1/300 稀有度一致;300 样本不足以
下「不存在」结论)。但边界声明不实必须更正(记档豁免或修法,
二选一)。

## 决策

**修法(结构性闭合,弃记档豁免)**:`remediation._sell_floor_filter`
——两补偿器的卖件候选列表排序后、发射前,按
`discipline.sole_engine_sell_floor_plan`(W197 批量口径单一源:前序
「可卖」件从计数扣减,blocked 件不卖不扣)对 **working**(执行前
真值,同轮前序采纳卖出已计入)过滤:

- 过滤后凑不足(金:got<shortfall / 槽:len<need)→ 整组放弃
  (既有事务性语义不变,无部分卖出);
- `_compensate_bench` 的种子死锁豁免名单(seed_cands)同样过滤:
  下界不变量(ADR-0373 引擎体系不清空)> 买死锁——死锁由后续轮/
  其他通道消化,卖唯一 TT 种子换 carry 正是 ADR-0373 所禁;
- flag 复用 `registry.sell_floor_exec_guard_enabled`(关=逐位回
  W197 后行为,A/B 通道与 ADR-0380 一致)。

ADR-0380 边界表「carry_gate ④/两补偿器」行同步勘误(渐进态由
本批补全;carry_gate ④ 单笔发射本就无聚合窗,不受辖)。

## Considered Options

- **记档豁免(W203 给的备选)**:可行但次优——判据单一源现成
  (`sole_engine_sell_floor_plan`)、改动=每补偿器一行过滤、
  锁可构造;结构性闭合优于在 ADR 里养一个「已知豁免面」。
- **补偿组重验层(_resource_blocked)加卖侧纪律复检**:拒——
  重验层只查三资源约束是 ADR-0326 契约,加纪律查询拉扯层职责;
  过滤放构造层(候选生成的同层)语义更准。
- **候选生成时对 working 重算全部键**:拒——working 占用守卫
  已有,全键重算=重复语义;只补下界维(聚合缺口唯一缺失维)。
- **零修法只更正边界声明**:拒——结构窗实证存在(136 型可构造
  性),300 样本未命中≠不可命中;修法成本一行,豁免记账成本
  永久。

## 验证

- 新单帧锁 4(`test_cw_w205_comp_floor.py`):①金补偿主锁
  (列车在手 3=tier+1,缺口需两笔回金 → 第二笔被逐笔扣减挡、
  整组放弃);②缺口一笔即够时不过度辖(只卖最弱一件,体系
  3→2=tier 合法);③flag off 逐位回旧行为(两笔均卖);④bench
  腾位主锁(缺 2 槽双 TT 件 → 第二笔被挡整组放弃;off 臂两笔
  均卖)。
- sim A/B n=300(同池 861fc9f6 重放,seeds 0-299,A 臂=flag off
  精确复现现锚 never2 7/mal 20):主指标=never2/mal 不回升、
  benign→mal=0、192 不恶化、出口金/hp 带内;数字见 W205 报告。
- ADR-0380 边界表勘误 + strategy/03_tactics.md 执行点段同步。

## 影响

- decision_v2/remediation(`_sell_floor_filter` + 两补偿器各一行
  消费)、ADR-0380(边界表勘误)、strategy/03_tactics.md(执行点
  补全段补补偿器一句);registry 无新 flag(复用)。
