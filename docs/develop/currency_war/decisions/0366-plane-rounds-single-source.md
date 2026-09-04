# 0366 — 位面轮数单一源 nodes_of_plane(口径断层修复:决策面 per-plane 真值)

- 日期: 2026-08-29
- 状态: accepted (采纳)
- 关联: ADR-0362(P2_ROUNDS=7 证据与 sim P2 段)、ADR-0363(末轮冻结,辖域修正)、ADR-0359(final_fence,轮门修正)、ADR-0361(battles_left_p2 推导)、ADR-0234/0235(plane_node_table 写入端)

## 背景与问题

`cw_horizon.NODES_PER_PLANE=9` 是全局先验,但实机 P2=7 轮(W157 16 局
语料:boss@r7、r1-r7 全在;economy.md §10.2 开局帧 7 槽)。所有
「本位面轮数」语义的消费者在 P2 全部错位(W165 巡检 #3,总模型级横切缺陷):

- 冻结窗(ADR-0363 件2):P2 r≥8 永不触发 → **空集**(W160 报告
  「per-plane 辖 P2/P3 位面末」表述不实——对齐在 P1-only 生效的错误基线上);
- final_fence(ADR-0359)/plane_last_battle:P2 boss@r7 判非位面末,永不辖;
- `_hard_node` remaining≤3:P2 窗推迟两轮(r7 才开,真实 r4);
- plane_remaining_nodes(冻结超限对照):P2 虚高 2 轮。

P3 轮数未知(零语料)——任何写死方案都会在 P3 复发同一断层。

## 决策

1. **单一源 `cw_horizon.nodes_of_plane(session)`**:真值 =
   `len(session.plane_node_table)`(r306 开局帧实读槽序表,prep_director
   每位面首帧写、位面内恒定)——P1=9、P2=7、**P3 首局进表即自适应**;
   表缺(裸 session/None/sim P1 段/开局首帧前)→ 回退
   `NODES_PER_PLANE=9` 先验 + 一次性 `[cw!][horizon]` 告警(回退事件
   即 P3 真值未知期的记档通道)。duck-typed 读 session,horizon 纯函数
   章程不破。
2. **P1 逐位不变是结构保证**:生产 P1 表恒 9 槽;sim P1 段不写表
   (ADR-0362 只在 P2 进场写)→ 两路取值 ≡ 旧常量。
3. **消费面分类裁决(44 处 grep 全量,W167 报告 §1)**:
   - 【本位面轮数,本批改 7 处】evolution 冻结窗 / `_hard_node` /
     `plane_last_battle` / `_streak_floor` remaining / scoring
     final_fence 轮门 / `plane_remaining_nodes`(签名加可选 session,
     裸调用回退 P1 先验)/ `battles_left_p2` 切片(表长=真值;超长
     脏表守卫保留:以 NODES_PER_PLANE 为最大先验封顶,W154 语义)。
   - 【全局 elapsed/全局 27 槽,不改 8 处】cw_comps early/COMMIT_ROUND/
     信号2 remaining、cw_evaluate `_elapsed_rounds`、
     `total_remaining_nodes`/`cross_plane_remaining_nodes`(ADR-0347
     显式全局口径)、血报警 t 轴、hp 地板 t——`(p-1)*9+r` 的 elapsed
     在 P1/P2 内本就正确(P1=9 已知);P3 内的偏差随 P3 轮数真值一批修。
   - 【DP 视界,该动但工程大,记档下批】cw_horizon difficulty_scale
     divmod 9 切片 / boss 奖金 `(t+1)%9==0`(P2 实际 t=15 处 boss,
     DP 收入模型漏 2 金)/ t 映射消费端(dp_posture/_horizon_node_goal)/
     hp 地板日程。修法=把 27 槽表重排为 9+7+P3 实际日程(位面偏移表
     进 horizon 常量层),牵动 solve 布局与全部 DP 锚——独立批。

## Considered Options

- **P2_ROUNDS=7 常量注入消费点**:拒——第二源;P3 复发同一断层,
  且消费点仍需 plane-aware 分支(每处写 `9 if plane==1 else 7`),
  散写=双源漂移。
- **消费点直接读 `len(session.plane_node_table)`**:拒——表缺回退
  与告警逻辑会在 7 处复制;单一源函数一处封装。
- **DP 视界同批修**:分步裁决——动 solve 结构(27 槽重排)风险大,
  本批先修决策面(冻结/fence/boss/remaining),DP 视界与本报告同判
  记档下批(本批 ADR 显式列遗留)。
- **表缺静默回退(不告警)**:拒——P3 真值未知期,回退事件是唯一
  的「P3 在用先验 9」观测面;静默=断层复发不可见。

## 验证

- 新单帧锁 9(`test_cw_w167_plane_rounds.py`):单一源表长(P2=7/
  P3 自适应 8/表缺回退)/P2 r6 冻结生效(旧空集)/P1 r7-r8 逐位不变/
  plane_last_battle P2 boss@r7 判正/_hard_node P2 窗提前两轮/final_fence
  轮门 P2 末轮/plane_remaining_nodes P2 真值+旧签名兼容/battles_left
  切片与脏表守卫。
- P1 零漂移门:sim planes=1 fallback 池 n=20 seeds 0-19 逐 seed 全指标
  (final_hp/hp_trail/refreshes/dir_round/level/n_ledger)diff={}。
- sim A/B(同池 snapshot planes=2 n=100 seeds 0-99):P2 段冻结窗从
  空集→生效(r6/r7 冻结事件出现);P1 侧 freeze 分布仍 r8/r9 不变;
  P2 headline 波动带内。数字见 W167 报告 §5。
- ruff 7 改动文件全过;全量 pytest 见报告 §5。

## 影响

- cw_horizon(nodes_of_plane 单一源)、cw_evolution(冻结窗)、
  decision_v2/discipline(3 处)、decision_v2/scoring(fence 轮门)、
  cw_intention(plane_remaining_nodes 签名+update_intention 透传)、
  decision_v2/strategy(调用点透传)、decision_v2/ev(battles_left 切片)。
- 遗留(下批):DP 视界 9 切片重排(difficulty_scale/boss 奖金/t 映射/
  hp 地板日程);P3 首局实读表后 nodes_of_plane 自适应生效。
- strategy as-built(02_comp.md §10 冻结窗语义行)同步。
