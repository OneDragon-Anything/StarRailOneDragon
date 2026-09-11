# ADR-0448: 血预算停手·停升级线(P2 停升级 + P1 停追级)进决策层(W523)

## 背景

W516(sim 定谳,n=200 基线+配对)与 ⑳+1 实机局判读共同定谳:P2 死亡的主导
机理是血预算算术——濒死段「追级泵」仍在为未来人口花金(⑳+1:血线 16/1 时
升 6/12 次),金换到了人口、人没活到人口生效。根在语义层:花钱义务由息线
单一驱动,血量只进报警(discipline 三臂)不进花钱/停花判据。设计唯一源 =
`docs/develop/currency_war/strategy/12_blood_budget_semantics.md`
(§3.1/§2.3-P1-b);本 ADR 记 P21 同族两条停手语义的实现裁决(P1-a/P1-c/
停刷新数值不在本批,留后续波次)。

## 决策

**P2 停升级线**(设计 §3.1):P2 备战帧 hp ≤ `ceil(d×registry.vd_p2_loss)`
= 21(d=1,L_c=20.05)时拒绝购买经验;**P1 停追级线**(设计 §2.3-P1-b,
完备性条款):P1 备战帧 hp ≤ `ceil(d×L_c(rung2))` = 11(L_c=vd_p1_loss_*
拟合 10.58)时拒绝升级。唯一豁免 = `plane_last_battle` ALL IN 清零窗
([18] 位面末最后一战是损失最小的花光时机,停手让位)。

数学依据 = P21(math_proofs 证明集):存活到账判据 h > d·L_c 在 h ≤ d·L_c
域内恒假 → 升级收益恒 0、EV = −C − I 严格为负,且敏感网格
(p,Δp,d,c) ∈ [0.10,0.30]×[0.05,0.28]×{0,1,2}×{4,6,8} 全负域——
**结论与 β 标定无关**,故不需要 A/B 开臂即落码(设计 §4.2 先行清单)。

### 实现形态:授权通道前置拒付过滤(与 level_cap_rejects 同型)

- **不是第五种覆盖态**:discipline 覆盖序(emergency > blood_alarm >
  boss_breaker > mode)不动;与息线门是**独立谓词取 AND**(血线胜)——
  emergency 态内停手同样生效(应急梯度给「怎么花」,停手给「不许为未来
  花」,作用在不同切面)。
- **接线三面**(LevelUp 授权通道全覆盖,堵旁路):
  1. arbiter 约束链新约束 `'blood_budget_stop'`(registry.constraints,
     审计表 slot 行三格登记)——候选通道单一收口,与 `boss_levelup_ban`
     的升级总账门并设(先血线后 EV 账,拒付原因分列可判读);
  2. remediation 稳态多击组(`steady_state_levelup_group`,W194/ADR-0378)
     ——「为未来人口买经验」的追级形态,线内整组拒发;
  3. remediation deploy_cap 补偿臂①(`_compensate_slot`)——该臂升级的
     受益部署解的是**下轮**(本臂注释原文「升级解的是下轮」),属 ≥1 战
     后兑现的未来收益,线内跳过①落②换位(SwapDeploy 不花金,不在辖域)。
- **披露**:拒付计数 `session.v3_blood_budget_rejects`(arbiter 逐候选击、
  稳态组/S4 臂逐事件),sim 逐轮差分进账本
  `sim.blood_budget_levelup_rejects` + 批聚合披露——语义对齐执行层
  `level_cap_rejects` 的披露模式(计数>0=语义生效面,不作达标线)。
- **常量单一源**:registry 三字段(`blood_budget_stop_enabled` 默认 True
  =P21 定谳恒接线,False=A/B 对照臂/回退锚,非悬置开关——与
  `vd_p2_enabled` 同型;`blood_budget_stop_d`=1;`p1_levelup_stop_rung`=2),
  线值由 vd_* 标定常量推导(discipline.p1/p2_levelup_stop_hp),不另立数值。
  cw_sim_checks 段级检查用镜像常量(纯函数纪律,先例
  `_LEVELUP_AUTH_WHITELIST`),漂移由测试仓双向锁辖。

## Considered Options

1. **覆盖态实现(第五态)** — 拒:与 discipline 覆盖序语义冲突(停手是
   拒付不是授权收窄),且设计 §5.3 明文裁决排除。
2. **只在 candidates 层过滤** — 拒:稳态多击组/补偿臂①两条授权旁路可绕过
   停手门(⑳+1 病灶帧的升级恰多由补偿臂发出),不封旁路=语义漏门。
3. **执行层拦截(仿 level_cap_rejects 在 cw_sim 拒付)** — 拒:执行层拦截
   只保金不保行为语义,决策层仍发无效动作(违背「授权通道前置拒付」的
   设计裁决);执行层同型只取其**披露模式**,不取其拦截层。
4. **补偿臂①照发(视为当轮转化豁免)** — 拒:该臂受益部署在下轮,不满足
   「当轮转化」豁免判据(收益在本战兑现);豁免扩到它会重新打开血线内
   追级通道。
5. **A/B 通过后落码(默认关)** — 拒:P21 全负域是数学证明不是 sim 假设,
   β 标定前结论稳健(设计 §4.2);悬置默认关违反开关生命周期(已判决未
   执行的悬案)。sim A/B 作行为面佐证而非开臂门(诚实预期:救活不显著,
   本语义省钱不救活)。

## 采纳裁决与验证

- **配对 A/B**(n=100/臂,池 6400d5d8edeaf68d+eqg1,同 seed,
  PYTHONHASHSEED=0,`ab_zero_drift.py`):p2_hp0 率 0.81→0.81(不劣,差
  0.0000);死时携带金 114.43→119.94(+5.51,略升——与设计预测「死时金
  略升」一致);P2 升级击数 125→89(拒付 880 次);诚实预期兑现=救活
  不显著,sim 数字不作成败判(设计 §7),主证据=结构断言+实机配对局。
- **零漂移门**:未触线局(on/off 双臂全程未进停手辖域帧)账本逐 seed
  diff = {}(0 局漂移);触线局 96/100(停手线在 P2 段高频辖域,符合
  设计「必然改变触线帧行为」的预期)。
- **段级检查**(cw_sim_checks `_SEGMENT_CHECKS` 两条新项):
  `seg_p2_blood_budget_levelup` / `seg_p1_blood_budget_levelup`,违规
  判据=备战帧 hp(上一行结算 hp 口径)≤停线 ∧ 非 ALL IN 帧 ∧ 有
  LevelUp;A/B on 臂违规 0。
- **回放锁**:⑳+1 局(run_20260828_191254)帧回放——血≤停手线备战帧
  新策略 LevelUp=0(旧栈同帧升 6/12 次);单帧锁测试
  `test_cw_blood_budget_stop.py`(停线数值/辖域/ALL IN 反例/接线三面/
  镜像双向锁)。
- **已知标定核对项(挂账,设计 §5.4-1)**:L_c 口径——registry.vd_p2_loss
  (20.05,P12 收益侧)与 W375 双源重标定后的 `p2_cond_loss_table`
  normal=12.77(条件败面)为同 estimand 的新标定;本线按设计定稿取
  vd_p2_loss,标定真值到位后按推导链重推(输入更新、推导链不变)。

## 状态

accepted(2026-08-29,W523)
