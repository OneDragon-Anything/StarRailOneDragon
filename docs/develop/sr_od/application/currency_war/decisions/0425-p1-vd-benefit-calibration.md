# ADR-0425:P1 段 V_D 收益侧骨架值治理(战斗数槽序表推导 + 条件掉血遥测拟合)

> **禁引注**:P15 旧回归系数 11.32−0.37·rung 已作废禁引;现行值以 P15v2_REPROOF 主表(848dc1aa)为准。

## Status

accepted(2026-08-27)

## Context

外部审计(§四-1 最高性价比项)实锤:`scoring.vd_refresh_score` 的 P1 收益侧战斗项用骨架值
`expected_battle_loss=10.0`(自标「未标定」)× `battles_left_est=5.0`(自标「未标定」),
而 W154/ADR-0361 的 P12 修法只治理了 P2 侧(`vd_p2_loss=16` + 战斗数从 state 槽序表推导)——
P1 的战斗数本可用同一手法推导却没推。数学先行硬门下,两个骨架值都不是合法的决策阈值背书。

## 决策

P1 收益侧两因子替换为推导值+标定值(常量单一源进 registry,来源标注遵守参数来源总账纪律):

1. **战斗数 = 推导(机制确定性)**:`ev.battles_left_plane`(P1/P2 同法统一,原
   `battles_left_p2` 改名留别名)从 `session.plane_node_table` 逐轮数剩余战斗槽;
   表缺退 `battles_left_est` 骨架缺省。确定性命题=math_proofs P15 检验点①。
2. **掉血 = 遥测拟合(条件败局伤害)**:新函数 `scoring.p1_battle_loss_est`,
   `loss(r) = vd_p1_loss_intercept + vd_p1_loss_slope_rung × r`,r 钳制 0-3。
   **语义必须是条件败局伤害**——收益式该因子与 Δwin_rate 相乘,取全样本无条件均值
   (对抗复核系数 −11.6+2.68·rung)会与胜率双计(P15 口径命题),故复用同一 W324
   语料的败侧行拟合:`vd_p1_loss_intercept=11.32` / `vd_p1_loss_slope_rung=-0.37`
   (battle n=278/73 局聚类稳健,斜率 SE 1.25;产物 `fit_results.json` 的
   `two_state_model.battle`,W324 归档目录)。来源标注=遥测拟合。
3. **消费点**:`vd_refresh_score` P1 分支、`engine_jump_gold`(掉血取成型后档——避免的
   掉血发生在完成之后)、`formation_gold_account`(透传 session,买侧 form_gold 同式
   同源跟随)。`score_state` 层3 power 的骨架视界**不在本批辖域**(独立治理项,保持)。

## 效果(P1 授权带变化方向与量级,P15 §③)

- core 2★ 完成的收益战斗项:r2 +0.53 / r5 −3.31 / r8 −7.14(相对骨架 9.05);
- pair 缺件通道 jump(0) @r5:6.93→4.55;
- 方向:**前中段小幅放宽,末窗显著收紧**——骨架 5 在末窗系统性高估剩余战斗
  (真值 3→1),凭空放大找件收益;与「末窗泄息找件」治理方向同向。
- 附带 P2 form_gold 漂移(同式同源跟随):战斗数从缺省 5 变逐轮推导、掉血 10→拟合值,
  量级同上表;P2 的 V_D(D 通道)分支不受影响。

## Considered Options

- **A(采纳)推导+条件拟合**:两个骨架值一次清账,口径命题先行排除错语义;
- B 复用无条件均值 −11.6+2.68·rung:被 P15 口径命题否决(双计胜率,方向性低估);
- C 只推战斗数、掉血维持 10:半治理(11.32−0.37·r 与 10 在 rung0-1 差 <4%,
  但 rung≥2 差 6-10%,且「未标定」标注无法摘除);
- D 层3 power 视界一并治理:波及全体候选排序基线,与本批 V_D 收益侧辖域不同,另立。

## Consequences

- 行为变化面:P1 D 通道(core/pair)+ 全位面买侧 form_gold;sim 基线需重捕后才可跨批对比
  (现行基线声明「基于现行模型」的场合注意 ADR-0424 粗模型验证门耦合);
- 验证:新锁 `test_cw_w336_p1_vd_benefit_calibration.py`(5 锁,入 cw_quick)+
  W126/W131/W154/W170 本地复算同步;L1 全集与基线持平;
- 挂账:层3 `score_state` power 视界(rounds_left_est/battles_left_est)治理另立;
  拟合的 rung 域上限 3(rung≥3 钳制,语料 rung3 薄样本 n=9)。
