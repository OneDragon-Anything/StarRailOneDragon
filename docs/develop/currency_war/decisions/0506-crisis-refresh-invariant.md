# ADR-0506: 危机帧刷新通道不变式(P36-a)

## 状态
accepted(已落地**无条件生效**——用户升格裁决覆盖先前开臂裁决:
`crisis_refresh_invariant_enabled` 开关整删,不变式恒接线,不留注入面。
依据=P36-a 单篇结构证明(B>0⟹n≥1,零参数,P23.1/P23.4 背书),prereg
A/B 仅作确认(off 16.21%→on 0.71%≈0/M0 翻正 45 帧/G1 行动率 +5.2pp
过,w951 REPORT §3)。实机确认门挂账不变:match 5+ 帧级核对 M1 哑火帧
占比→0(crisis 帧 release_budget>0 且无 RefreshShop);连续 ≥2 局执行
缺位型哑火 → 回退评审)

## 背景
- 命题 P-新1-a(w945 DESIGN):通道不变式 **B>0 ⟹ n≥1**(预算>0 的危机帧
  必须存在 ≥1 次刷新执行通道)——结构已证零参数:P23.1 统一门不含预算帽,
  帽/门阻断正 EV 通道等价强制攥金,P23.4 死亡域金终端价值≡0 ⇒ 阻断严格劣。
- 现状实证(w946 标定):实机 crisis 帧 RefreshShop p50=0/哑火帧(budget>0
  ∧ 实花=0)12/30,持金中位 130;p_hit 宽口径 ≥0.94(两源)——刷新通道
  有效率高,哑火是纯执行缺位。
- 机制定位(w951 REPORT §1,重放实证):病灶不在预算门,在 **ADR-0468 息档
  截断门的车道分类**——危机刷新按 essential=False 裁,arbiter 预截断门
  `tier_truncated_spend(gold, 刷价, essential=False)=min(刷价, gold%10)`
  在 gold%10<刷价时先拒(g105→残 1 拒;g130→残 0 拒,预算 12 原封未动),
  `authorize_release_refresh` 从未被触达。截断门前提(息档 0.1/轮值得保护)
  在危机带被 ADR-0503/W907 证伪(P23.4 金终端价值≈0)——门在自己的辖域
  外作废了通道不变式。

## 决策
危机帧(指令 reason='crisis')在预算>0 且仍可负担一刷时,**本帧首刷按
essential 车道过息档截断门**(两处截断门同址分类,判据单一址=
`posture_release.crisis_invariant_lane`):预算门/boss_floor/g≥0 三门照辖;
首刷兑现后(`v2_round_refreshes>0`)恢复常态截断——不变式只保 n≥1,
豁免面不外溢。开关 `crisis_refresh_invariant_enabled` 默认关
(crisis 族,与 `crisis_release_enabled` 同族子臂:不变式辖 crisis 指令,
父臂关则子臂无从触发)。

## Considered Options
1. **首刷 essential 车道(采纳)**:豁免面最小(单帧单笔),与 prereg
   主判据「哑火帧率→0」一一对应,off→on 差异可归因。
2. 危机帧全域豁免截断门:语义上同样有 P23.4 背书,但行为变化面大于命题
   所保(n≥1 之后的行为无 A/B 判据),归因混杂,弃。
3. 只改 `authorize_release_refresh` 内门:实证不够——预门先拒时授权门
   根本不被调用(p2r6 幀重放证据),修了等于没修。
4. 改预算式(把截断残差计入预算):预算语义(ADR-0503 min(溢余,帽))与
   截断语义(ADR-0468 息档)是两个维度,混改破坏单一源,弃。

## 后果
- 验证=test_cw_w951_p36a_invariant 7 锁(不变式单帧锁/关臂零漂移锚/
  车道谓词边界/W944 血预算门协同核对/字段面;开臂重推后关臂锚改 OFF
  显式注入承载)+w917/w645 邻锁全绿+replay 哑火帧翻正(2/2);L1 快速集。
- A/B 已判(prereg w951 §6 回填):主判据哑火帧率 off 16.21%→on 0.71%≈0
  过、G1 行动率 +5.2pp 过;据此翻默认(第 3 态)。
- **实机确认门挂账**:match 5+ 帧级核对 M1 哑火帧占比→0(基线 12/30≈40%;
  危机帧=sess_release_reason='crisis' ∧ sess_release_budget>0);连续 ≥2 局
  出现执行缺位型哑火(非预算耗尽/非无通道节点)→ 开臂回退评审。
