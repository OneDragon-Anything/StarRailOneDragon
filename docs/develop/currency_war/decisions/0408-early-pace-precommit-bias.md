# ADR-0408 假设 A:r3/r4 投资节奏前置(early_pace 评分偏置)

- 日期:2026-09-04
- 状态:accepted(默认关;A/B outcome 裁决见验证节)
- 谱系:W248 报告 §四假设 A 定稿;前置 W251 之前已解除的 ADR-0407
  (v11 encounter rung 键,rung 维因果链可验——本批机理核的前提)
- 任务:W251

## Context(为什么)

W248(n=150 sim,池 73c64c8b)找因结论:P1 掉血由**败场计数驱动**
(战斗类节点 delta<0 场次,Pearson r=−0.635,唯一强相关);高损耗
局与低损耗局的分化在 r3-r4 已发生(r3 hp 73.5 vs 81.4),r7 遭遇战
拉大差距、boss 补刀。当前策略按息纪律延后投资,r3/r4 常带浅板上阵。

假设 A(W248 定稿):r3-r4 的投资决策若能前移(更早把金转化为战力),
可降低 r7/boss 高损耗轮的败场数。修法落点当时悬而未决(评分偏置 vs
levelup 提前);ADR-0407 落地后,r7/boss 的伤害结算带真实 rung 条件性,
「投资→战力→减伤」因果链在 sim 内首次完整可测——本批同时是修复后的
首次机理核测量。

## Decision

**授权点 = 层3 评分(scoring.score_candidate)注入偏置通道**,非 levelup
提前、非地板改动:

1. **判据**:P1 ∧ r∈[`early_pace_min_round`, `early_pace_max_round`]
   (缺省 3-4,W248 干预口径「r3-r4 备战期放宽破息授权一档;r5 supply
   自然回补」)∧ 战力买标签(= `crisis_buy_tags` 同集复用,不另造
   标签集)∧ 非 emergency([18] 纪律态优先)时,val ≤
   `early_pace_val_max`(0.5,双计防线同 forming_bias_val_max)的买候选
   加 `early_pace_bias`(5.0,forming_bias 同阶)。
2. **防双计**(W232/W238 三件套):本项只把非正分买顶进约束链;息账
   单一源仍是 interest_rule 的 EV 授权(V 随分数进入 = 授权阈值放宽是
   本修法本体语义,不是第二份授权值);registry 无 early_pace 专有 EV
   常量字段(单帧锁钉死五字段白名单);正分候选不叠加(bd['early_pace']
   记触发依据,行为面核可用)。boss 窗(war 覆盖态同理)不辖——与
   forming_bias 的纪律态先行序一致;forming_bias 自身窗口 r≥5 与本项
   r3-r4 无重叠。
3. **flag:`early_pace_enabled=False` 默认关**(A/B 裁决先例
   ADR-0305/0400/0402/0403/0405),关=现行为逐位零漂移(sim 整局
   ledger 恒等 + 改前基线逐 seed digest 对拍双门)。

### Considered Options(取舍)

| 选项 | 裁决 | 理由 |
|---|---|---|
| r3/r4 地板临时下移(interest_floor 局部降档) | 否 | 地板是政策态常数(HOARD 全轮域语义),局部降档=全局金底线失真;且绕过 EV 账=授权不走账(违 [17]/[28] 期望值框架) |
| levelup 授权提前(平台账窗放宽) | 否 | 升级总账(levelup_ev_basis)口径自洽,P1 多击早前 W194 泛化曾致 never2 回归(辖域敏感);假设 A 的靶点是「买战力件太晚」,升级不是主拦截位 |
| 直改 interest_rule 的 C 折中系数(r3-r4 局部调 recovery_rounds) | 否 | 动已标定常量(ADR-0352)的辖域局部化=双源漂移;评分偏置不动既有常量 |
| 层3 偏置通道(本批方案) | 是 | crisis/goldrich/forming 三个先例的同族第 4 件;只显影「到不了约束链」的候选,EV/地板/copies_cap/bench 容量全照辖;A/B 臂可独立回滚 |

## 验证(裁决依据)

- 结构锁:`sr-od-test/test/sr_od/app/currency_war/test_cw_w251_early_pace.py`
  (5 锁:主通道+防叠边界/窗口辖域+纪律态不越权/约束链照辖+数值单一源/
  默认值锁/sim flag 关整局恒等)。
- 零漂移门:B 臂(flag 关)三窗逐局 ledger digest 与 HEAD(ae555946)
  改前基线逐位一致(`baseline_ledger_digest.json` vs
  `armB_ledger_digest.json`;注:工作区内的首份基线因后台采集与代码
  编辑竞态被污染,真基线以 HEAD worktree 重采版为准)。
- A/B:同池(v11 指纹随报告记录)同 seed 配对、同进程双臂,三窗纪律
  (main 251000/n300 + anchor 异族窗 0-99/n100 + 相邻异族窗
  901000-901099/n100);数字单一源=`ab_report.json`(+ 本 ADR 下方
  结果补记)。
- 机理核(v11 解锁后的首测):A 臂 vs 基线的 r7(encounter)/r9(boss)
  EΔ 对比——投资前移若成立,rung 分布上移应表现为 EΔ 绝对值下降;
  若 EΔ 不动而出口 hp 变,则变化走的是伤害模型外的通道(如实归因)。
- outcome:P2 承接 hp_tier 迁移/p2_hp0/存活轮/胜率;星级 form 通道
  (ADR-0401)叠加效应观察(entry_tier/hp_tier 分布位移)。

### A/B 结果补记(W251 裁决)

n=300(main,seed 251000-251299)+ anchor 异族窗(0-99,n=100)+
相邻异族窗(901000-901099,n=100);同池同 seed 同进程配对。**数据
边界**:批跑途中主仓池快照被实机局终自动再生管线覆写(run37 语料
入池,v10 撕裂态致 resolve raise)——A/B 双臂在覆写前同进程完成,
内部自洽,但指纹 **10163d3b938c684b 是一次性进程内产物,不可复现
重放**;零漂移门为此改用冻结 JSON 池(a6bbbdede3f8b604)两仓对拍
补偿(见验证节),主指标结论按「同批内配对差」判读,跨日绝对值
不引。

| 窗 | 配对出口hp差(A−B) | hp升/降 seed | 配对败场差 | p2_hp0(A/B) |
|---|---|---|---|---|
| main n=300 | −0.41 | 2/7 | −0.003 | 0.8322/0.8223 |
| anchor n=100 | −0.26 | 1/1 | +0.04 | 0.9167/0.9167 |
| high n=100 | +0.22 | 1/1 | −0.01 | 0.8947/0.8958 |

- **outcome 裁决:无一致正方向,默认关维持**(三窗配对差符号
  不一致,幅度全在噪声带;exit_hp_mean 基线本身 ~2,p2_hp0 ~0.83
  的饱和分布下有效分辨力低——如实声明:当前 P1 段出口分布已深度
  饱和,hp 类指标的臂间可辨性受限)。
- **机理核(v11 rung 键解锁后首测)**:r7 encounter EΔ A/B=
  −8.447 vs −8.440(main)/boss −26.181 vs −26.177——**EΔ 两臂
  几乎不动**。解读:r3/r4 早买的确改变了投资时序(r3/r4 买笔
  303→326,+7.6% 触发证据成立),但 r7/boss 结算的 rung 条件性
  没有响应——偏置只顶「到不了约束链」的候选,**没有改变 r3-r6
  板面成型度(rung)的路径**;W248 假设 A 的「投资前移→run g 上
  移→高损耗轮减伤」链条在此剂量(bias=5.0,单轮带宽)下不成立。
  与 ADR-0305 goldrich 偏置否决的旧结论同构:成型加速可见,hp 不跟。
- 行为面:main r3/r4 战力买笔数 303(B)→326(A)。

## 默认关论证

沿用 ADR-0400 起五连先例的行为面/outcome 面分离裁决原则:**结构成立
(触发证据)不足以裁默认开**;hp0/存活轮分布须有一致正方向(三窗
符号一致),部分方向或噪声带内即维持默认关、通道保留。禁「归零/不劣」
措辞;裁决数字只引 ab_report.json 与本 ADR 补记,不引会话转述。

## Effects

- registry 五字段(enabled/min/max/bias/val_max),scoring 一段偏置块,
  zero schema/接口变更;消费点仅层3,遥测/checks 无新契约(bd 键是
  判读面非锁面)。
- 后续网:A/B 正方向 → 默认开裁决 + W248 §四预期方向核对(E[r3/r4]
  −2~−3、出口 p25 +8~12 的兑现度如实报);负方向 → 记录失败机理后
  关闭通道回滚注册表副本即可。
