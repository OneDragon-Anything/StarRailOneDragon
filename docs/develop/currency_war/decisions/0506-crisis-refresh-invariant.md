# ADR-0506: 危机帧刷新通道不变式(P36-a)

## 状态
accepted(开关 `crisis_refresh_invariant_enabled` 生命周期第 1 态默认关;
开臂判据挂 prereg A/B)

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
  车道谓词边界/W944 血预算门协同核对/字段面)+w917/w645 邻锁全绿+
  replay 哑火帧翻正(2/2);L1 快速集。
- 挂账=A/B(prereg w951)主判据哑火帧率 on≈0、次要实花面/hp 不劣化;
  过→翻默认,不过→删码留本 ADR(开关生命周期,禁悬置)。
- sim 侧注意:sim 引擎危机帧刷新本就 p50=3(w946),sim A/B 若 off 基线
  哑火率≈0 则 sim 不构成证据域,判据改挂实机(prereg §4 预案)。
