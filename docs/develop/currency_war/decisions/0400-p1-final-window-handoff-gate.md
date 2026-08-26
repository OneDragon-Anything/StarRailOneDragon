# 0400 P1 末窗承接门(设计件 08 Phase 1 落地:formed_stop 承接维 + EV 承接缺口项)

- 日期:2026-09-02
- 状态:accepted
- 前置:ADR-0399(Phase 0 观测层+档位标定)、W226 扩样复验(`.debug/temp/currency_war/w226_handoff_sim/`)
- 设计件:`docs/develop/currency_war/strategy/08_p2_handoff.md` §4.2 Phase 1 / §4.1 判据 3

## Context(为什么)

W220 双局实证(run 28 带血不足型 / run 26 板面质量不足型)→ ADR-0399 落了
承接快照观测层,但**零行为**:P1 末窗(r8-r9 boss 窗)的花钱决策仍未把
「带进 P2 的资产够不够活」计入期望——formed_stop 是纯 P1 语义「能不能过
P1」,EV 账没有承接项。W226 扩样确认门控维度(总档位 tier)全指标单调
+ β/γ 敏感性端点一致 → Phase 1 解禁。

## Decision(做了什么)

**判据单一源** `decision_v2.handoff.handoff_gate_gap(state, session, registry)`
——纯函数:辖域 = plane==1 ∧ r≥`handoff_gate_min_round`(=8,末窗)∧ 开关
开;返回投影承接档位(handoff_snapshot 在当前轮决策入口现算,近端投影)
距 `handoff_gate_tier_target`(=1)的缺口数。**只辖末窗是 P1 非末窗零漂移
门的结构前提**。观测:session.v3_handoff_gap(sim 账本轮行 `handoff_gap`)。

两个挂载点(设计件 §4.2,均为既有接口零新层):

- **挂载点 a(formed_stop 承接维,filters)**:`formed_stop_active` 在
  form_ok 通过后,末窗承接缺口>0 → **不停手继续投资**(丢弃停手判定;
  [18]「位面末最后一战是损失最小的 ALL IN 时机」的承接扩展——低血/全
  1★ 板带差资产进 P2,存金无意义,换板面战力)。缺口在 form_ok 之前算
  (观测字段无论成型与否都写)。
- **挂载点 b(EV 承接缺口项,arbiter.interest_rule)**:末窗买侧破息
  EV 账的 V 加 `handoff_ev_gap_bonus`(=5.0)×缺口——末窗破息投资
  授权阈值放宽;auth trace 带 `handoff_gap`。**只辖买侧**:刷新的平面
  R 上界口径(ADR-0352)与升级平台账(levelup_ev_basis)不动,不双计。

registry 四字段(`handoff_gate_enabled`/`handoff_gate_min_round`/
`handoff_gate_tier_target`/`handoff_ev_gap_bonus`),A/B 注入;
默认值论证见 Consequences。

## Considered Options

| 选项 | 裁决 | 理由 |
|---|---|---|
| 缺口判据放 formed_stop/arbiter 各写一份 | 否 | 谓词族单一源(ADR-0343 教训);两挂载点同判据才不漂移 |
| 缺口=承接快照(session.v3_handoff)现值 | 否 | 快照只在 P2 首帧采样;P1 末窗无值——需投影(现算 handoff_snapshot) |
| 投影用「位面末预测」(模拟剩余轮资产) | 否,近端投影 | 末窗距出口 ≤2 轮,板面/血量漂移有限;预测器违反设计件 §4.2「不预测」裁决(核心哲学 1) |
| EV 缺口项辖全部动作(D/升级) | 否,只辖买侧 | D 是同轮搜寻消耗([17] 平台语义,P5⑤ 退化输出逐位保留);升级有独立平台账——双门双计是 ADR-0347 明令禁止形态 |
| 缺口目标 = hp_tier/board_tier 分维 | 否,总档位 | ADR-0399 标定:总档位(短板语义)单调且端点稳健;分维多门=切点耦合 |
| 承接门改锁线/换线 | 否 | [23] 锁定不 pivot;Phase 1 不动意向状态机(设计件 §4.3) |

## Consequences

- **默认 flag=OFF(关=回 W226 前行为;A/B 裁决,ADR-0305 先例:三窗
  无一致正方向 → 默认关通道保留)**。A/B 数字(n=300 池 3be1d31006541ba2
  seed 0-299 同池同 seed 配对,planes=2 invest on,
  `.debug/temp/currency_war/w227_handoff_gate/w227_ab.json`):
  - **行为面(门生效证据)**:r8 均买 1.02(on) vs 0.67(off);门扣住
    轮 1499(on 臂 ledger handoff_gap>0 的轮);进场档位分布 on
    259/21 vs W226 基线 256/20(tier0/1,基本不动);
  - **P1 零漂移门 ✓**:非末窗(round<8)逐 seed 逐位 diff,drift_seeds=[]
    (判据 3 后半过);
  - **outcome 面(判据 3 主指标)**:p2_hp0_rate 0.9393(on) vs
    0.9348(off) 微升;avg_p2_rounds 3.71 vs 3.77 微降;p2_win_rate
    0.1784 vs 0.1877;p2_entered 0.9333 vs 0.9200。**方向不通过
    (如实报败)**——hp0 率未降/存活轮未升,差异在噪声带内但无一
    为正方向;门扣住子群逐 seed 配对(n=260)同样平(hp0 246 vs 245/
    存活轮 3.70 vs 3.72/末 hp 0.9 vs 1.0)。
  - **裁决归因(与 W226 已声明 sim 边界一致)**:承接门的主投资方向
    是星级深度(core2)与末窗板面补强,而 sim 胜率模型(ADR-0377
    win_p = p0+β·form−γ·drift,form=engines+level)对 core2 **无因果
    通道**(W226 §⑥ 已定位并声明)→ sim 无法仲裁该修法的收益方向,
    「不劣」不构成默认开的依据(禁「不劣」措辞纪律)。通道保留,
    **复验挂账:ADR-0377 form 加星级分量后重跑 simulate_handoff_ab**;
    真值面的最终裁决归后续实机语料(承接档位分层判读)。
- formed_stop 语义变更(仅 flag 开时):P1 末窗成型但承接未达标轮不再
  停手——`overflow_gold_zero_buy_streak` 豁免面同步收窄(承接轮有买
  不进 streak;无买且 gap>0 的轮 formed_stop=False 会进 streak——判读
  注意该差异是预期行为,门生效的证据)。
- w119 comp 派生辖轮锁改用 gate-off 注册表隔离(语义正交:该锁辖
  typical_form_round 派生,承接维由 test_cw_w227_handoff_gate 辖);
  test_cw_w227 行为臂全部显式 replace 开闸(默认关后不依赖默认值)。
- Phase 2(P2 早期姿态偏置)/Phase 3(hp<10 保命路径收编)仍挂账
  设计件 §5 分期表;Phase 2 前置 = 本批默认裁决(观测/授权通道已就绪,
  开闸条件=复验翻正)。

## 验证

- 新单帧锁 `test_cw_w227_handoff_gate`(窗口辖域/承接维 run28 型构造局/
  EV 缺口项放行+拒对照+auth trace/sim 账本字段+A/B 非末窗零漂移 n=4);
- registry hash 锁同步(test_cw_adr0293_calibration);
- A/B 批:`simulate_handoff_ab` n=300 seed 0-299 池 3be1d31006541ba2
  planes=2 invest on(223s;判据 3 判读见 Consequences——零漂移过/
  行为面过/outcome 面不过 → 默认关);
- run 28/31 型构造局(验收 3):test_formed_stop_handoff_dim_run28_type
  ——末窗成型低血帧门臂不停手(买保留=继续投资证据行),关臂照旧拦;
- L1 + 全量 pytest 0 failed(commit 前)。
