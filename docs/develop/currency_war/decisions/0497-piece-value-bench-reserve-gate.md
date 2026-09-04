# ADR-0497 · 件价值买前 bench 容量预检硬门(reserve 推导落码;ADR-0496 开臂前置件)

> **引用勘误(2026-09-04 ADR 存量 review)**:`.debug/` 归档 → 本目录(decisions/)同名 ADR;`prereg/` → `docs/develop/currency_war/proofs/`(math_proofs 索引)。文内出现处按此对照读取。

## 背景与问题

件价值 Phase 1 标定批(ADR-0496)定谳 w_retention=0.0 的根因是 B 辖域缺位置成本约束:W846 on 臂 G4 满栏帧差 +11pp、B 买入 22.6% 发生在占用=8 的最后空位、合格事件被满栏拒 4,143 次。「买前 bench 容量预检」硬门被评估为对症方向但挂账两项:①消费面逻辑改动超出标定批文件面;②reserve(预留空位数)推导缺位(P29 持位成本 H 未标定)。本 ADR 偿付两项挂账并落码。设计依据链:W852 REPORT(`.debug/temp/currency_war/w852_weight_calibration/REPORT.md` §3)+ W831 v2 §3.3(可加性边界:硬门不进评分,与 Phase 1「E 禁进评分」边界相容)+ W829 支出门 D3(单一实现 `spend_gate.bench_front_full`,禁第二实现)。

## reserve 推导(禁拍死值,状态依赖逐帧可复算)

`piece_value.bench_reserve` = **1 + 线内开对线数**(上限 `piece_value_bench_reserve_cap` 截断):

1. **基线项 1**:P29 卡点保守处理明文「bench 占用 ≥ 容量−1 时 H 取禁囤阈值」——每帧至少保 1 空位给受保护类(线内缺档成员 EV ≥ Δp_tier·R_rest ≈ 1.4×R_rest 金当量;激活钥匙件 P20 2.6-2.9×),而囤牌期权近零(P1:≤2 费再遇 7-15 轮;W846 归因 B 买入 56.7% 为 ≤2 费)。保护与囤牌的价值不对称恒成立 → 基线恒在。
2. **开对项 +1/线**:线内同名 1★ 恰持 1 份的合成线开对数。2★ 合成链深 3 张,但 bench 槽位需求峰值 = 2(第 3 张到达即 merge 完成,满栏合成买合法,W544/ADR-0453,不占新空位);已沉没 1 槽后剩余需求 = 第 2 张的 1 个空位——被囤牌件占掉则整条线停在深度 1(沉没 1 槽 + 1 购),损失大于一枚新囤牌期权 → 每开对线 reserve+1。
3. **上限 cap**:扫描旋钮,缺省 2 = W852 扫描建议带 {1,2} 上沿;reserve ≥ 1 硬不变式(`bench_front_full` 同款守卫)。

边界:无锁线意向时开对数不可判 → 退基线 1(辖域不明不扩张预检)。

## 决策

1. `spend_gate.bench_front_full` 扩参 `reserve: int = 1`(单一实现,缺省值保持 D3 与 P29 定性门行为逐位不变);
2. `piece_value.bench_gate_verdict` 落码:bench 空位 ≤ reserve(占用 ≥ 容量−reserve)时拒新买非合成 BuyCard;豁免面 = merge 候选 ∪ 当轮可部署 ∪ 线内缺档成员(missing_members 单一源);让位序与 D3 同族(boss 窗/ADR-0474 分配器接管帧);拒因进遥测(`sess_pv_bench_block`,session.v3_pv_block 帧级计数透传);
3. arbiter 约束链追加 `pv_bench_reserve` 于 `spend_gate` 之后:双门并存帧 d3_bench 先到先记(首拒即断),本门只记「未达 D3 带但 ≥ 容量−reserve」的不重叠带,零双计;
4. registry:`piece_value_bench_gate_enabled=False`(伞 = piece_value_enabled 合取,默认关第 1 态零漂移)+ `piece_value_bench_reserve_cap=2`(上限扫描旋钮);audit_matrix bench/emergency、bench/mode 格同步;
5. 开臂判据挂账(不执行):硬门落地后按 W836 PREREG 同格重验(a-only 双臂,G4/M1-L 两格),由编排者派;不过则删码留 ADR(第 4 态),禁悬置默认关。

## Considered Options

- **(采纳)reserve 推导硬门 + 链序挂 D3 后**:对症 W846 满栏病灶,不进评分(可加性边界相容),单一谓词实现。
- **(否决)E 软权重进评分**:W852 隔离扫参证明「加项-阈值翻转」机制本身是剂量病灶载体,软权重不解决。
- **(否决)独立第二谓词(bench_free ≤ reserve 自算)**:违反 W829 D3 单一实现纪律,漂移面 +1。
- **(否决)reserve 拍死常量**:违反决策规则数学先行;reserve 依赖开对数(状态),拍死值在多开对帧欠保护、零开对帧过收紧。

## Consequences

- off 零漂移:两旗标默认关,`bench_gate_verdict` 恒 None;`bench_front_full` 缺省参数对既有消费点(D3/P29 定性门)逐位不变。
- 锁组:新锁 `test_cw_w854_bench_gate`(触发/reserve 边界/裁决序去重/让位/遥测/off 零漂移);`test_cw_w829_spend_gate` 锁 0 链序断言按锁的存在性纪律重推(spend_gate 不再是链尾,守卫先到先记语义不变);`test_cw_adr0293_calibration` 字段面/constraints/audit_matrix 回显锁同步。
- 复验挂账:件价值 Phase 1 同格 PREREG 重验(a-only,G4/M1-L),编排者后续派;本批只声明判据。

## 尾注(删码已执行,W927 批)

本 ADR 与 ADR-0496 承载的件价值整机制已按策略开关生命周期第 4 态删码留档执行
(删码 commit 52c84277,本批禁 git commit)。W902 §4 删码范围表逐项清零:scoring.py 买侧
加项块、decision_v2/piece_value.py(硬门+evaluate_piece)、registry 八个
piece_value_* 字段与 constraints/audit_matrix 的 pv_bench_reserve 登记、遥测键
sess_pv_bench_block(schema/recorder/sim 三处)全部删除;锁组 test_cw_piece_value
/test_cw_w854_bench_gate 随码删,adr0293 面册反向操作(删条目)。删码安全性证明
=零漂移:默认 registry 下 sim n=100(seeds 3,000,000..3,000,099,池指纹
6400d5d8edeaf68d+eqg1)与删除前 HEAD 同 seed 逐位一致(证据=
.debug/temp/currency_war/w927_pv_delete/)。终裁依据=W859 §2(delete_code_
keep_adr0497)+W902 §4(buy 子机制活性但零疗效,54% 破息)。
