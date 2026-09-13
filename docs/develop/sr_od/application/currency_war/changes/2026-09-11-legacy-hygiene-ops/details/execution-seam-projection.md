# 执行缝账务与投影播种（详设：T-16 / T-17）

## 问题与约束
本篇辖两批，共享「执行缝（决策发射与执行入账之间）」与「投影播种/guard」文件面，互斥关系按总纲 IC-2 排布；域边界按总纲 §2（kernel/cw_state.py 为 W8 切割对象，本篇只做点状修复）。

### T-17 simulate 落洞 churn 重排治本（旧账 T-280；三层方案已由旧账 T-308 落码批入库，本任务 = 残余收尾）
- **状态（T-308 后世界态）**：下列三层方案与顺路面三件已由旧账 T-308 落码批于 2026-09-11 12:42 入库——主仓 bd27989d4（7 文件 +203/−33：cw_reconcile.py / cw_exec_state.py / cw_op_buy_cards.py / cw_shop_action_ops.py / decisions/0646-bench-layout-single-source.md / decisions/INDEX.md / flow/projection_contract.md），测试仓 377b61889ae0（3 文件新锁 15），落地审 = 旧账 reviews/T-308-落地审.md accept。本批（账本 T-17）= 验证与残余收尾，**禁重做已入库面**（照旧方案重落会产出零 diff 白批或与 HEAD/留树 hunks 冲突）。
- **症状（历史记档，T-308 修复前实证）**：批量跑曾出现 2 例降级 WARNING（降级不炸）——bench 布局真相双源：`tracked_bench_chars` 的列表下标布局（mutate/simulate 动作面消费）与 `BenchChar.slot` 字段（投影播种与 guard 构造消费）脱节，持续制造者 = `reconcile_tracking` 写回紧凑列表（依据 = T-280-交付报告.md §①，两例日志实证；报告落盘正本 = details/sources/）。**该写回现已带槽号健康门 + 槽位表重建（HEAD 即是，见下 S2）**——症状时态止于 T-308 前实证。
- **方案正本（已由 T-308 逐条照落，下述为入库内容记档）**：T-280-交付报告.md §③（经方案对抗审修订版；落盘正本 details/sources/）——三层同纲：
  - **S2（主修，已入库）**：`reconcile_tracking` 写回前把 SIFT 读经 `bench_from_compact` 转槽位表（画面槽号→下标，定长 9）再写 `tracked_bench_chars`；写回前置槽号健康门（占用槽号唯一 ∧ 全在 1..BENCH_CAPACITY，违者拒绝写回 + defects 台账留证）。同构先例 = 同函数 deployed 侧写回——定稿时点锚：S2 主修注释现居 cw_reconcile.py:236-245 一带，deployed 侧先例（`deployed_from_compact` 转槽位表）现居 :273-278；**行号为快照，开工以符号名/注释标记（T-308）重定位为准，禁死信行号**。
  - **S1（结构防御，已入库）**：tracked 输入域消费点改「下标直拷」，恰 4 点——定稿时点锚：投影播种 cw_op_buy_cards.py:797、买牌期望态基座 cw_op_buy_cards.py:354、guard tracked 构造 cw_shop_action_ops.py:223-275 区、卖出侧 tracked 归一 cw_shop_action_ops.py:527——`pad_bench(deepcopy(tracked))` 替代 `bench_from_compact`。**cw_screen_prep.py 两点禁改**（输入是 SIFT 现读 obs.bench_chars，非 tracked；其槽号优先放置是正确适配）——原 :548/:702 经 T-321 批移位后现居 :497/:627，原样在树。「S2 后行为逐位等价」主张限定到这 4 点。
  - **S3（epoch 通道，已入库）**：exec_state（cw_exec_state.py，不在旧申报面四文件之列）加 `bench_layout_epoch: int`，reconcile drifted 写回点递增，投影帧播种透传，商店单动作循环每动作消费前检差，命中则三步：截断 in-flight plan 序列 → 按 tracked 重播种（复用 `_reseed_bench_layout` 含槽号健康门）→ 重入决策。当前架构下 S2+S1 后 epoch 恒不变，纯未来防御通道。
- **改动面（T-308 实际交付，校正经纬）**：头面 = 上列 7 文件；**cw_state.py 零触碰**（方案申报面实际收窄 = helpers 零改，健康门写回点前置——T-308 卡与 commit message 均申报）；cw_screen_prep.py 禁改遵守；math_proofs 零触碰。旧申报面「cw_reconcile.py / cw_state.py / cw_op_buy_cards.py / cw_shop_action_ops.py」在两个方向上失真，以本条为准。
- **残余（本批辖面 = 账本 T-17 criteria 未兑现子项）**：
  1. **P3 残余小修**：cw_reconcile.py 健康门拒绝分支 sorted 混型防御面 + 返回值 docstring（T-308 落地审问题 2 记档候小批）；
  2. **「连续批跑 0 例降级 WARNING（前值 2 例实证）」正式取证**：sim 批，**挂 sim 门后执行**（总纲 §2 编排者裁决原文照录），不构成 W6 前置；
  3. **同型 visit 实机回归 0 例**：候实机窗；
  4. **凭据对账记档**：T-308 已交付凭据（两例重放锁逐字节 EQ / 新锁 15 / 107 passed / 变异红证）与账本 T-17 criteria 逐条对账，随残余批交付报告登记。
- **约束（T-308 后）**：残余修复（1）**先于 unified-state W6 开工**（W6 applied-gate 复用 cw_reconcile.py，禁在其上叠批；cw_state.py 前提已随 T-308 交付废止）；批跑取证段（2）挂 sim 门，不阻塞 W6；本批零策略语义、零新数值判据；math_proofs 零增行（证明载体 = 结构单一源 + 变异锁有牙性，命题语义写交付报告）；旧时序条款「排当前在飞批 commit 入库之后」已由 T-308 入库兑现，残余开工按总纲 GC-1 逐文件对账（不预写在飞快照）。

### T-16 备战帧金动作漏账修复（旧账 T-306）
- **根因归层**：约定层——执行缝账务包络的辖域约定只辖商店单元，备战帧金动作被排除在包络外（修法 = 辖域约定补全，非新机制）。
- **症状**：备战帧 m3 经验批（mandate.py m3_levelup_batch）商店单元收口后发 5 次直接 `LevelUp(-20金)`，不经 journal 回执/outcome 计数/spend_executed——执行缝三套账只辖商店单元，备战帧金动作全部漏账（依据 = 旧账 T-306 卡，T-234 复跑定谳真红）。发射侧实为单次 `Emitted(LevelUp())`，5 击是执行/决策侧按 clicks 展开。
- **修法方向**：备战帧金动作接入与商店单元同构的账务包络——journal 回执 + outcome 计数 + spend_executed 入账。修法定谳前义务（旧账 T-234 落地审验收三条转告，落码前逐条执行）：
  1. 补跑一轮 HEAD 对照组落档（定谳类交付对照组证据同权留档）；
  2. **钉死展开位**：先亲读执行/决策侧 clicks 展开代码，把「单次 Emitted 展开为 5 击」的确切位置写成结论（落交付报告），修点据此选择；另立备战帧金账锁——现锁只抓负形态，禁只认此锁转绿；
  3. 守卫锁出处回填为持久指针（代码注释/交付报告；按总纲 GC-4，ADR 候用户命令）。
- **约束**：mandate 面在飞改动入库后才可落码（cond 复查 = 盘点 git status 与主线索引）；排 T-17 残余修复之后（IC-2：pad 态契约与 guard 形状**本体已由 T-308 入库（bd27989d4）**，开工前复核已入库契约——锚 = + flow/projection_contract.md，以残余修复落库后形状为修点定谳基准；该小修与 T-16 文件面不相交，串行为保守排布）；与 T-18 共 mandate.py 互斥（m3_levelup_batch 段 × fuel_sell_candidates 段，总纲 §1 症状 3，编排者控制在飞互斥）；修复走双审（方案段 + 落码批，落地审必验）。

## 方案（实施序）
1. **T-17 残余先行**：P3 小修落码（cw_reconcile.py 健康门拒绝分支）→ 批跑取证段候 sim 门（挂门执行，不阻塞 W6）→ 实机回归候实机窗 → T-308 凭据与账本 criteria 对账记档随残余批交付。
2. **T-16 随后**：T-17 残余修复落库 + mandate 面入库后开工；按修法定谳义务 1-3 产出结论 → 方案段（含修点选择依据）→ 落码（备战帧金动作入账三套账接通）→ 执行缝账务包络测试锁 → CW 子集绿。

## 关键取舍
- **churn 批「事件接投影链」单独落地被否**：诊断证明分叉主因在播种双源（写回制造），只做 S3 不做 S2 时脱节每局再生（T-280 报告 §③ 被否替代案③，实证机制直接否决）；守卫侧提前对拍、simulate/mutate 合并单引擎两案同段被否。
- **残余批禁重做已入库面**：三层已入库（bd27989d4），照旧详设「按方案正本三层落码」重做会产出零 diff 白批或与 HEAD/留树 hunks 冲突（attack.md F1 发作场景）——开工先对账 HEAD 与 T-308 交付面，残余面以本详设「残余」清单为准。
- **T-16 修点不预设**：发射侧/展开侧/入账侧三处都可能是修点，以「钉死展开位」结论为准择一，禁凭症状直觉直接在发射侧堵（旧账 T-306 P2 义务的动机 = 防修在展开下游导致账面 1 笔/画面 5 击的二次失真）。
