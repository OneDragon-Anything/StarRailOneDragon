# ADR-0566 — 发射帧受限消费仲裁(金出口族出口 B 溢出段):armed 短路帧保留消费权,先消费后发射

- **Status**: accepted
- **Date**: 2026-09-07
- **关联**: ADR-0557(发射短路语义与反假阴性哨兵——本批改造其哨兵断言)、ADR-0560(P71-b 升级量闸——仲裁段内升级消费继续过该闸)、P70(proofs/p70-launch-frame-overflow-spend-dominance.md,已证——本批数学授权)
- **设计稿**: `.debug/temp/currency_war/gold_exit_family/DESIGN.md` v1.1(§2.2 段一判式/§3.2 出口 B/§3.2 载体 I-2 位次/§5 辖域/§6 A/B 预注册/§8 批 1);攻击复核 = 同目录 `attack.md`/`attack_v11.md`(N-1 观测载体裁决见 §6)
- **批 0 基线**: `.debug/temp/currency_war/gold_exit_family/batch0_baseline/BASELINE.md`(池 `14f29f3bc2307492+eqg1`,seeds 0-299,planes=1,短路态基线)

## 1. 背景与问题

ADR-0557 落地后,生产达标臂(armed = 线成型 fp≥1.0,单键恒真无解除条件)在每轮备战入口直接发射,整段短路备战动作链——发射帧成为「有动作决策点」意义上的零决策帧,金出口族四元组的全部出口在该帧族结构性不可达(`in_must_spend_zone` 辖域 = 有动作决策点帧,对短路轮失明)。批 0 基线实证(n=300):发射短路轮 869/2700(32.2%),发射帧 idle_gold 中位 113(P90 188),终局残金中位 131.5(IQR 118-190),291/300 局 boss 轮零动作,末轮 2★ 中位 2——成型后金囤 96-196 花不出、合成素材滞留,即金出口族设计稿 §1.1 症状①。

数学授权已备:发射帧是「窗内剩余备战决策数 = 0」的构造性强形态,P70 已证——溢出段息损恒零 ⇒ 任一 ΔV≥0 的合法即时消费弱支配留存;辖域 = 溢出量预算 g − g* 内的 Δ息=0 帧,花穿息线部分出辖(p70 边界 1)。带内段(g ≤ g*)挂 L1' 独立命题,fail-closed 证不出不花。

## 2. 决策(裁决)

**短路骨架保留;「确将发射」路径独占插入仲裁段:先受限消费、消费机会用尽(或无合格消费)后照常发射。** 判定语义单一源 = `kernel/cw_launch_arbitrage.py` + `kernel/cw_economy.in_launch_spend_zone`;执行皮肤留两面各自循环体(与 ADR-0557「发射核留 operations 不动」同判据)。

### 2.1 触发面 T(armed 判据零改动)

armed(`readiness_launch_decision` 单一源输出,零改动)∧ 节点 ∈ 战斗类 ∧ `in_launch_spend_zone(gold, session)`(新增谓词,与必花域共享 `saturation_line(cap_resolved_of_session)` 链,禁内联第二份;买断制 cap=0 出辖恒 False)。**与必花域同 g* 不同域,禁并键**(DESIGN §5;两域互斥 = 调用点约定非结构保证,M-1 降级口径)。

### 2.2 资格面 Q 与预算

消费对象 = shop 出口族既有评估栈(策略器 `decide_shop_action` 单动作核)按**既有选择序与资格门**产出的动作(M2 缺件/m2_stockpile/M2b 合并完成、M3 升级过 P71-b 量闸、R1 刷新过 r1/r2 门、M6/dominance 压库按各自门)——仲裁只提供「这帧有多少零息死仓金可花」,**不新造第二套评估语义**(DESIGN 红线 1),**不重排评估序**(红线 5)。窗内预算 = g − g*(溢出量):单动作预算闸 `launch_arbitration_gate(action, gold, session)` = 花后金位 ≥ g*;**闸拒 = 消费终止非跳过续试**(跳过高位动作改试低位 = 重排既有评估序)。卖出/部署事务族零成本动作不辖(闸辖「花」不辖「换手」)。

### 2.3 位次契约(v1.1 I-2 钉死;两道闸对齐)

生产插入位 = cw_loop 备战分支内,只挂达标臂位次:**armed 判定通过 → 浮层在场闸通过(`readiness_overlay_hold` 路径)→ `_prep_anchors_hit` 预检通过 → 仲裁段 → `readiness_battle_launch`**。预检(备战双锚单一源,零新参数)只作仲裁段的门;发射核零改动,其内部屏态复验保留作**纵深防线**——仲裁若未恢复备战屏态 ⇒ 走既有 stale 分支弃射,该帧记 `launch_arbitrage_abandoned_launch` defect 分键(可辨识残量,从「非发射帧 digest 零变化」锚辖域显式豁免,禁静默)。仲裁访问失败路径(未识别卡停机钩子等)abort 旗置位:不关店、不发射,保画面交停机接管(禁摧毁停机钩子现场)。收益耗尽臂发射位(:1723 一带)与恢复局面发射位零改动。

sim 同构接线:发射建模块立模后同位次接入;两道生产闸的 sim 结构等价物 = 恒真(结构盲区如实申报,sim 无浮层、无切屏竞态)。防分叉三层:①判定语义单一源(本 ADR §2.1/§2.2 全部 kernel 函数 + 分键名常量族);②位次契约单一源(本节);③对账锚各守拓扑(§6)。

### 2.4 带内段 fail-closed

g ≤ g* 的发射帧:不开店、决策段仍零执行,计 `launch_arbitrage_inband_closed` 分键(与「溢出帧零消费」`launch_arbitrage_zero_consume` 分键可辨——前者是授权缺位,后者是机会缺位)。

### 2.5 sim 侧形态

溢出段发射帧的决策段循环以 `LAUNCH_ARBITRAGE_SEGMENT_CAP = 5` 段帽运行(结构常量,与生产 run_buy_waves `MAX_REFRESH+1` 访问段帽同构;kernel 桶禁 import operations,以常量+派生注释对齐);段内逐动作过预算闸,拒则整段收工。带内段帧 range=0。发射帧的部署代理块照常执行(生产 RunDeploy+StartBattle 同构,零改动)。

### 2.6 无开关

P70 已证 = 直接落码无开关(DESIGN §8 批 1;strategy-work §3 第 1 档)。回滚靠 git revert。

## 3. 哨兵断言改造(随批重推,非机械跟绿)

`check_sim_launch_short_circuit` 从「金不花」升级为「**自由决策段零执行 ∧ 仲裁段外零消费**」(锁语义重推记录 = 测试文件 docstring):

- `short_circuited is True` 仍必查(短路辖的是自由决策链,仲裁段不是自由链);
- `launch['arbitrage']` 披露必查(新增;缺披露 = 接线被拆 = 批 0 假阴性形态回归,红);
- 带内帧:动作空 ∧ spend 全零(fail-closed 锚);
- 溢出帧:动作/花费允许,预算不变量 `gold_after ≥ g_star` 必查(破线红——合并多买等投影外成本由此响亮暴露)。

红证在案:临时禁用仲裁接线 ⇒ 4 个行为/哨兵锁全红(披露缺位形态);还原后全绿。

## 4. Considered Options

| 方案 | 裁决 | 理由 |
|---|---|---|
| 保留短路(现状) | ✗ | 三面 p<0.0001 成对恶化在案(sink_baseline);金出口族 A/B 已被 ADR-0557 修正过一次假阴性,不能再造「看得见打不决策」的帧 |
| 回退短路 | ✗ | 重开 ADR-0557 所治的结构性假阴性根;恢复的是无权衡设计的旧语义 |
| 自由决策段照跑(不设预算闸) | ✗ | 带内段无授权(L1' fail-closed);花穿息线出 P70 辖域(边界 1);且放任既有评估栈以常态视界计账,违背「仲裁只供溢出预算」的辖域声明 |
| 白名单消费类(M2/M2b/M3 才放行) | ✗ | 在评估栈输出上按动作类过滤 = 跳过高位臂改取低位臂 = 重排既有评估序(违红线 5),且另造第二套资格面 |
| **既有评估栈全序复用 + 预算闸 + 位次契约(本批)** | ✓ | 评估语义一份(红线 1);P70 辖域精确(Δ息=0);两面判定单一源;发射链零改动 |
| 逐事件遥测补生产侧粒度 | ✗ | N-1 三选一裁决 = 如实降格(§6);生产 `record_defect` 逐事件链成本与判读收益不匹配 |

## 5. 后果与边界

- **发射帧行为变更本体**:溢出帧 idle_gold 左移、终局金向 g* 带回落、成型后零动作轮趋零、合成通道(合并完成买)在战斗轮恢复——A/B 验收读数见 §7;带内帧/非发射帧零行为变化(锚辖域)。
- **池基线再断裂**(DESIGN §12-5):批 1 起金流行为变更,跨批直接对比禁用;批 0 读数按「短路态基线」标注,批 1 = 新基线首批。
- **闸投影成本与执行侧真实成本的模型差**:合并多买等投影外成本可能使花后金位跌破 g*——后验检测分键 `launch_arbitrage_cross_line`(生产/sim 同名),正常恒 0;>0 = 残量显影(哨兵同判红,禁静默)。
- **带内发射帧观测投影变化**:launch 行新增 `arbitrage` 披露位 + `launch_arbitrage_inband_closed` 分键 = 观测面新增,行为面零变化(带内帧动作空、零花、零 rng 消耗)。
- **必花域观测面扩展**:发射帧仲裁段成为决策点后,`must_spend_zone_frames` 等观测键在溢出发射帧开始计数(语义正确的决策点扩展;跨批对拍必花域类指标须声明口径变化)。
- **评估栈计数器粒度**:仲裁帧上 `merge_material_stale` 等每帧计数键会随仲裁段执行而增加——指标 4 的判读以轮差分方向为准,粒度申报同 ADR-0517 迁移先例。
- **禁改面维持**:armed 判据、14 号稿 §9.6 防停机初衷(守卫/C1 计数/闩面)、其他出口(出口 A/C/D)零落码——本批只落批 1。

## 6. 观测载体申报(N-1 三选一裁决:如实降格)

attack_v11 N-1:生产侧 `cw4_counters` 只有局终快照,无逐轮粒度——「闸命中帧仲裁零消费」的同轮互斥读数在现有生产遥测载体下不可测。**裁决 = 不做逐事件遥测,如实降格**:

- **sim 侧逐帧强断言**(哨兵,§3):轮差分(`obs.cw4_counters` 逐轮增量)+ `launch.arbitrage` 帧级披露,互斥与预算不变量逐帧可测;
- **生产侧总量弱对账**:`launch_arbitrage_*` 计数族随局终快照链入档,批报告报总量(`readiness_overlay_hold` 总增量 vs `launch_arbitrage_*` 总增量),互斥的回归检测由 sim 侧承担;
- 生产侧新增 defect 分键 `launch_arbitrage_abandoned_launch`(仲裁消费后弃射)走既有 `record_defect` 链,不新增遥测管道。

## 7. A/B 验收预注册线誊写(DESIGN §6.2 批 1 辖域;commit 后、跑批前誊入,禁看完数据挪线)

| # | 指标 | 批 0 读数 | 方向线 |
|---|---|---|---|
| 1 | 发射帧 idle_gold(中位/P75) | 113 / 134 | 显著下降(配对符号检验) |
| 2 | 终局残金中位 | 131.5 | 向 g*(50)带回落;分位全表报 |
| 3 | 短路轮零动作占比 | 32.2% 构造性零动作 | 溢出帧消费占比可辨(`launch_arbitrage_zero_consume` 可归因) |
| 4 | merge_material_stale_ge2 | 1,830 | 下降(合成通道恢复) |
| 10a | 息基代理 × 形态达标 | 0.667 / 97.0% | 成对不劣(配对 +/−/0 + 符号检验);达标占比方向改善 |

判读纪律:1-4/10a 为 sim 兑现面(批 1 辖域);10b(hp/胜率)挂实机 A/B 批(DESIGN §8 批 7,候排)。零漂移锚:零发射帧局(未达标局)的账本轨迹与批 0 逐位一致(强对照,兼作并行在飞改动 sim 中立性的对账探针)。

## 8. 实施落点

| 面 | 改动 |
|---|---|
| `kernel/cw_economy.py` | +`in_launch_spend_zone`(共享 g* 单一源) |
| `kernel/cw_launch_arbitrage.py`(新) | 预算闸/成本投影/分键名常量族/段帽常量 |
| `operations/cw_loop.py` | `_launch_frame_arbitration`(预检/区判/开店/受限访问/关店/abort)+ armed 分支位次接线 + 弃射 defect 分键 |
| `operations/cw_op/cw_op_buy_cards.py` | `run_buy_waves` + 可选 `spend_gate` 参(缺省 None 零漂移;拒 = 本动作不执行 + 访问收工) |
| `sim/engine_p1.py` | 仲裁段区判 + 段帽 + 逐动作闸 + `launch.arbitrage` 披露 |
| `sim/checks/launch.py` | 哨兵断言升级(§3) |
| `sr-od-test/` | `test_cw_launch_arbitrage.py`(判定核/单一源/位次契约/生产行为全分支)+ `test_cw_sim_launch_sink.py` 锁 3/4/5 重推 + 红证 |
| as-built | `flow/outer_loop.md` §3(仲裁位次)、`sim/sim-design.md` §4.3(债-1/残-2 复查时机) |
