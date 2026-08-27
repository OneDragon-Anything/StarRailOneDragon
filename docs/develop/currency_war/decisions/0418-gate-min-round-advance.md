# ADR-0418 handoff_gate_min_round 前移 8→6:承接门家族授权窗加宽兑换落地(W288)

- 日期:2026-09-05
- 状态:accepted
- 谱系:ADR-0400(承接门原设计,末窗=8)、ADR-0411(四通道无条件
  转正)、ADR-0413(game_cap 非绑定裁定,把 per_round/gate_min_round
  列为「加量」两个有效旋钮、另立批);任务 W275(A/B 裁决批)+
  W288(本批,前置核验+条件落批)
- 产物:`.debug/temp/currency_war/w275_knob_ab/`(REPORT.md 四臂 AB)
  + `.debug/temp/currency_war/w288_gate_landing/`(本批双段核验:
  w288_verify.py 可重跑 + w288_replay_diff.json + w288_buy_quality.json)

## Context(为什么)

W275 四臂配对 sim AB(n=200,v11 冻结池 `7af8197782d42c05` 同 seed,
base 臂与 ADR-0413 表逐位一致=配对基线有效)裁决:`handoff_gate_min_round`
前移成立但留了**硬前置**——该常量被承接门家族共享(filters 成型停手
承接维/arbiter 缺口项 EV 账/candidates 副本放行/M-A 定向刷新窗,
外加 handoff hp 投影加项的触发条件),前移同时提前这些面的点火时机;
不核漂移与买质量不得落。W288 即走完该前置后执行三选一兑换。

A/B 主证据(W275 REPORT §2,gr6 臂 vs base):

| 指标 | base | gr6 |
|---|---|---|
| dir 授权次数(arbiter 通道) | 274 | 339 |
| core2≥1 进场率 | 12.17% | **18.85%** |
| core2≥1 配对翻转(+/−) | — | **22:9**(31 局 71% 正向,二项单侧 p≈0.025) |
| star≥2 率 | 0.5% | 1.5%(3:1 翻) |
| 进场金均值差(CI95) | — | −1.50 [−4.28, +1.87] 无信号 |
| 末 HP / hp0 / P2 进场率 | — | 全无信号 |

剂量-响应单调(gr7 15:7 → gr6 22:9)支持「前移是有信息量的旋钮」。

## Decision

**`handoff_gate_min_round` 8→6(合资格窗 {r8,r9}→{r6..r9});落批前
置双核验全过,当场兑换:**

### 前置① 历史局回放定性漂移(W288 A 段,cw_replay 同帧集双臂重放)

93 个历史局、全部 (plane,round) 去重帧,`DecisionV2Strategy(registry=
replace(DEFAULT, handoff_gate_min_round=6))` vs 默认注册表逐帧对拍:
分歧仅出现在 P1 r7 一帧(类别=买不同卡);P1 r1-r5/r8/r9、P2、P3
**零漂移**——行为变化严格限于新点火窗,无结构外溢。

### 前置② 提前点火买入质量(W288 B 段,sim n=200 配对复现+W288 注入)

P1 r6/r7 早期买入的身份构成(classify_buy 单一源):

| 指标 | base | gr6 |
|---|---|---|
| r6/r7 买入总笔数 | 363 | 753 |
| off(线外散件)占比 | 6.06% | **3.59%(反升:更好)** |
| engine+pair+bridge_seed 占比 | 93.94% | 96.41% |
| core2≥1 / 进场金均值 | 12.17% / 24.68 | **18.85% / 23.18**(与 W275 gr6 臂逐位一致=同注入法互证) |

结论:**提前开窗没有买到更差的东西**——新窗内买的是引擎/凑对/桥件,
散件率反而下降;代价为早期多花金 ~3.3 金/局,与进场金差无信号一致。
两前置均过 ⇒ 兑换「调常量」映射(W275 §4 第三映射:「方向对、量级
待实机定标」),落地形态=registry 单常量改值,**与被测臂注入逐位一致**
(测试手段与落地形态分离,sim-testing §5——零新增未测行为)。

### Considered Options

| 选项 | 裁决 | 理由 |
|---|---|---|
| 前移 8→6 仅改常量(本批) | **是** | 双前置过;AB 方向正且免费;HP 面不受扰动(P1 存活主线不动) |
| 同步解耦 boss +2 触发条件再落 | 否(挂账 Consequences) | 解耦改行为代码 ⇒ 与已测臂不一致,AB 证据作废须重跑;先按被测形态落地 |
| 不合入等实机对照局 | 否 | 回放+质量核已覆盖 W275 自立的两条硬前置;悬置=禁 |
| 加量改 directed_refresh_per_round | 另立批候选 | W275 已裁不合入(显著金代价 −4.04 零产出);联合双开不做 |

## Consequences

- registry 改一处值+注释带证据链指向本 ADR;受影响锁同步:
  test_cw_w227_handoff_gate(非末窗边界 r7→r5;原「r7 停手」零漂移
  锁在 min_round 前移后构造不出「floor 过∧门不辖」帧,改锁「窗内 ∧
  承接达标(gap=0)仍停手」)、test_cw_w252_directed_refresh、
  test_cw_w242_star_directed 同边界重排、test_cw_adr0293_calibration
  hash 锁更新(8233f282…)。
- **已知耦合 wart(挂账)**:`handoff_boss_reward_bonus`(+2,r8 奖励胜)
  的触发条件历史绑定 `round_num == handoff_gate_min_round`,前移后在
  r6 触发;r8 视角标定的投影公式(hp−34 Q3 口径)在 r6/r7 少算后续
  节点期望伤害 ⇒ 早期投影偏乐观。该畸变端到端存在于测量臂内(属被测
  行为的一部分,净效应已被 AB 覆盖为正),**解耦需新增独立轮次常量+
  改 handoff.boss_projected_hp 并重跑配对 AB**,待下一批碰承接门的
  批顺路做。handoff.py 两处 docstring 的「r8-r9 末窗」措辞随此挂账
  一并修(strategy as-built 数值不入正文纪律,单一源在 registry 注释)。
- 定向刷新 cap 语义注记:窗容量变为 {r6..r9}×per_round2=8 > game_cap6,
  cap 自本变更起重新可能 bind(实测 gr6 授权 339 次 vs 窗容量理论上限
  的差距属后续大批/实机定标面,不改变本批结论)。
- 实机验收锚点(事前写,供下一轮实机批核对):① P1 r6/r7 出现定向
  刷新/破息投资行为(旧代码为零);② core2≥1 进场局占比上升方向;
  ③ 金账无恶化信号(进场金中位数不动)。sim 边界继承 W275 §5(star≥2
  为低频事件只证方向;装备/词条未建模)。
