# 0306 - Δ池扩容批:解锁 hp 类杠杆的总闸(口径裁决+胜率外推+桶覆盖披露+换锚)

- **Status**: accepted(2026-08-25;0305 件2/件3 登记的扩容前置兑现——
  本批不改策略代码,改的是 sim 校准层的可信地基)
- **Context**:0305 战役级发现——池 battle rung2 桶胜率 44.4%(Δ口径,
  n=9)且 rung≥3 无桶,0301/0305 的评分杠杆(eng_frac 追级、goldrich_
  buy_bias)全被这个校准层天花板封死。本批四件:语料增量盘点、快照
  重生成+降级路径胜率外推、胜判定口径裁决、n=300 新锚+战役标尺。
- **Decision**(四件):
  1. **件1 语料增量盘点 = 零增量**:outcomes.jsonl 现 191 行 vs 池
     META 覆盖 191 行(29 runs,QUARANTINED 排除后)——**扩容原料
     为零**,上次快照(066c4185)已含全部可信语料。按 rung 分桶:
     battle r0 n=40 / r1 n=31 / r2 n=9 / **r3-r4 零样本**;tier7+
     全节点 17 行(H3 件1 口径)不变。结论:**语料不足如实报**
     (rung≥3 桶贫困,本批不虚构样本),扩容的唯一途径=实机继续
     跑局攒 outcomes——这正对应「实机常跑=素材泵」的既有定调。
  2. **件2 重生成+降级路径胜率外推**:生成器全量重跑(增量=0 自动
     进池);`_SAMPLER_VERSION` 4→5。battle rung≥3 桶贫困(n<10)
     的降级路径(邻桶下探已有)中,**boss 胜分支掷胜的胜率**由
     ADR-0277 拍脑袋的 0.25(沿用 e2 值)改为**「rung2 桶实测」
     外推**:新 `cw_sim.boss_win_p()` 单一取值口,rung≥3 读快照
     META `battle_rung['2']['win_killed']`(实测 **0.667**,
     killed 口径 6 行 4 胜;META 缺字段退 `BOSS_WIN_P_FALLBACK`
     =0.25 防静默归零);rung0/1/2 仍用批③ H3 实测矩阵不动。
     **证据标注**:外推边界 = ①rung2 实测 n(killed 已知)小样本
     ②battle→boss 跨节点外推——两边界写入 docstring 与本 ADR,
     实机 boss rung≥3 胜局样本积累后应改为直接拟合(登记在
     delta_pool_bucket_coverage 的贫困披露)。
  3. **件3 胜判定口径裁决 = killed 权威**:`outcomes.killed`(结算
     屏 extras)为唯一权威口径,Δ(相邻轮 hp 差分)是派生量。
     **0305「同 9 行 3 行异号」按生成器配对口径复核为伪影**:
     复审计(`adr0306_pool_audit.py`,结论入本 ADR)在 rung 分桶
     下 killed 已知行异号实证 **0/61**(r0 0/31、r1 0/24、r2 0/6);
     0305 的「44.4% vs 77.8%」系 **tier×core 分桶(H3 矩阵)与
     rung 分桶(池)的错位对照**——两组 9 行不是同一组行。另
     killed=None 行(19/80)只入 Δ 分布不入胜率分母,分母披露
     (killed_known/killed_unknown)进 META。生成器统一用权威
     口径出逐桶 `win_killed`(win_delta 对照保留)。
  4. **件4 桶覆盖披露检查**:`check_delta_pool_bucket_coverage`
     进 cw_sim_checks + simulate_p1_batch 内嵌——判据=各桶 n≥10
     或快照 META `bucket_poverty` 显式披露(battle rung 域 0-4
     缺桶同样辖);snapshot 池带 META 披露,auto 池无披露载体
     贫困即违规,fallback 空池不辖(先例语义)。本批贫困披露:
     battle r2(n=9)/r3(缺)/r4(缺)+ boss 三桶 + encounter 三桶
     + reward 两桶,共 11 条。
- **Considered Options**:
  1. **维持 0.25 不动等 boss 实测**:否决——rung≥3 boss 胜局样本
     本批零新增,而 0.25 拍脑袋值已被 rung2 实测(0.667,killed
     口径)证明系统性低估成型局胜率;杠杆解锁(0305 登记的
     goldrich/追级复验)被它封死,先解锁校准层才谈策略复验。
  2. **把 Δ 口径逐桶 win_delta(44.4%)当外推源**:否决——件3
     裁决 killed 是权威口径;Δ 口径含 killed=None 行的差分噪声
     (reward+2 混入)且与结算屏真值可异号(虽本语料实证 0,
     机制上不保证),外推取权威侧。
  3. **虚构 rung3 桶(插值/合成)**:否决——语料不足就报不足,
     生成器只写真值;下探链+外推胜率已是显式降级路径。
- **验证**(新池 886f8a39c87c8c6b,v5 指纹;单进程串行,CPU 配额
  纪律遵守;报告 `.debug/temp/currency_war/cw_dev/adr0306_*`):
  - 复审计:80 battle 配对样本逐行 killed vs Δ 对照(异号 0,
    伪影结论成立);rung3+ 零行实证;
  - 定向锁:`test_cw_adr0306_delta_pool_expansion.py` 8 条(META
    胜率字段/行数账/贫困披露/boss_win_p 外推与兜底/coverage 检查
    单元+快照自洽+批内嵌/单一源口)+ 旧锁语义化更新 3 处(sampler
    v5 ×2、boss_win_p 单一源)——定向 5 文件 54 passed;ruff 通过;
  - n=300 新锚(seed 0-299,默认臂):hp_ge_60 **0.137**(旧
    0.127)/avg_final_hp **35.68**(旧 33.98)/battle_losses_le_2
    **0.167**(旧 0.127)——上移方向符合预期(池变真实),已登记
    `ANCHOR_REGISTRY_N300`,旧锚(066c4185)标注失效原因=池校准
    修正非策略变化;checks 内嵌全绿新增项
    (delta_pool_bucket_coverage 0 违规),既有红(equip_value_
    strategy_key_coverage=在飞 worker 域、dead_system=判据过严
    候选)与本批无关维持;
  - v1/v2 双臂三窗战役标尺(30×3×2=180 局,同池同进程):
    gap(v1−v2,负=v2 更高)= **−3.00/−1.23/−0.83**(anchor/fam_a/
    fam_b;gap_sd 30.4/24.4/29.9,n=30 分辨率底 ±9.7~10.9hp——
    **三窗全在噪声带内,方向不叙**,本批立法的 ab_verdict_claim
    纪律适用于自身);hp_ge_60 v2 0.167/0.033/0.067 vs v1 0.133/
    0.067/0.067(±3.3pp 底内)——新池下两臂维持批㊱「统计平局带」
    口径,不构成领先叙述(初稿「v2 三窗全领先」系符号误录+
    越底叙述,收账审查拦截,第 10 次批间互证)。
- **Consequences**:
  - 正:0305 登记的评分域杠杆(goldrich_buy_bias 通道、追级权重)
    解锁可复验;胜判定单口径消歧(killed);桶贫困显式披露进
    检查网(未来语料增长自动收敛贫困);锚随池指纹迁移可追溯;
    0305「3/9 异号」伪影纠正(防后续误引用);
  - 负/风险:①rung≥3 胜率外推的小样本边界(battle→boss 跨节点
    + n=6)——rung2 桶 killed 样本攒厚或 boss 实测出现后需复验;
    ②battle r2 桶 n=9 仍贫困(<10),扩容依赖实机攒局(实机侧
    killed=None 行继续占 19/80,upgrade 侧 killed 采集覆盖为
    前置);③全量 pytest 已在 CPU 空窗补跑清偿(1896 passed;
    暴露 0305 两处漏更锁——registry hash(goldrich 三参)与锚
    对照值锁,均已语义化更新,详 0306 收账条)。
