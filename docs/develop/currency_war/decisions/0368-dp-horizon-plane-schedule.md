# 0368 — DP 视界位面槽序重排(位面日程自适应)

- 日期: 2026-08-29
- 状态: accepted (采纳)
- 关联: ADR-0366(位面轮数单一源,W167;本批=其 C 组「DP 视界该动但工程大记档下批」的落地)、ADR-0362(sim P2 段)、ADR-0361(battles_left_p2)、ADR-0234/0235(plane_node_table 写入端)、ADR-0347(v2 栈 DP 接线)、ADR-0313(t 轴口径)

## 背景与问题

W167/ADR-0366 分类清单 C 组(6 处):cw_horizon DP 把全程当 27 槽(3×9)
均匀切片,但真实轮数 P1=9/P2=7/P3 未知。判读(W169 报告 §1)量化实际伤害:

- **位面内 node 下标无错**:生产查询 t=(p-1)·9+r−1,P2 的 r1..r7 → t=9..15,
  位面内下标(t−9=r−1)与正确排布相同 → difficulty_scale 在 P2 已占槽上没错;
- **错在尾部与端点**:① boss 奖金槽 (t+1)%9==0 → P2 真实 boss(t=15)无
  +2 金,幻影 t=17 领奖——P2 末轮收入模型偏瘦 2 金;② 幻影尾:t=16/17 两轮
  不存在,值函数按其存在规划 → P2 段 DP 剩余轮数虚高 2、未来收入/掉血虚增
  (V_D 窗 refresh_budget / 升级授权偏松);③ P3 槽序右移 2(真实 16 起);
- **离线对拍实证**:状态网格(gold 0-110 step5 × level 4-9 × hp 20-100 step10,
  1242 态/轮)旧解 vs (9,7,9) 解的动作翻转率 P2 r1-r7 = 14.3%/22.9%/20.6%/
  28.8%/25.4%/27.4%/26.8%,值差 |Δv| 至 ~12.4(≈1.2 档存活奖励);sim 真实
  消费面:P2 段 DP 姿态 tag 1242/1640(75.7%)查询翻新(逐轮 r1 460 → r7 12)。

**写入端断链(判读新发现,顺带修)**:生产 prep_director 的 write-once 守卫
(`not plane_node_table`)使 P1 的 9 槽表整局滞留——session 按整局建、位面
过渡不重建,生产 P2 的 7 槽真值表**永不落盘**:nodes_of_plane / battles_left_p2
/ 本批 DP 日程在生产 P2 全部读陈旧 P1 表恒 9(表「在」但是错的,连表缺回退
告警都不发)。W167 A 组修复在生产 P2 同样不生效(sim 生效仅因 sim 直接写表)。

## 决策

1. **位面日程自适应(schedule-aware horizon),单一源 `cw_horizon.schedule_of(session)`**:
   真值 = `session.plane_lengths_seen`(本局已揭晓位面轮数序列),未揭晓位面
   回退 `NODES_PER_PLANE=9` 先验(P3 进表即自适应);脏表守卫每位面长度夹
   [1,9](W154 语义)。`solve(ledger, pl)` 全链参数化(难度曲线按日程偏移归属
   位面 / boss 奖金落日程位面末槽 / 总程=日程求和);查询映射统一
   `HorizonSolution.slot_of(plane, round)`(horizon 内单一源,消 `(p-1)·9+r−1`
   散写);解缓存 memo 键=(台账指纹, 日程)。
2. **P1 逐位不变是结构保证**:P1 期 seen 至多 [9] → 日程 (9,9,9) ≡ 旧常量
   → memo 同键命中同一解对象;默认日程下 difficulty_scale / node_income /
   slot_of 与旧式公式逐位一致(单帧锁全 t 域对拍)。
3. **写入端修复**:`prep_director.store_plane_table`(可单测纯函数)按
   `plane_node_table_plane` 锚定**每位面首帧重写**槽序表并 append
   plane_lengths_seen(位面内恒定语义不变);sim P2 进场写表同步记 seen。
4. **消费端分栈裁决**:
   - v2 栈(生产决策主干):`ev.dp_posture` 透传 session → 真值日程(仲裁层
     授权门 / W154 V_D 窗 refresh_budget 自动跟上);
   - v1 栈纯函数消费端(`get_node_goal` ← cw_economy/cw_evaluate/cw_plan)
     与 cw_telemetry 影子查询:**保持先验日程**(无 session 透传面,牵动宽;
     默认日程 ≡ 旧行为逐位零漂移)——遗留记档,P3 真值批或 v1 退役批再裁;
   - `cw_state.effective_hp_threshold`(first-passage hp 地板,W167 B8/C6):
     同为纯 state 函数无 session,保持先验——同上遗留。

## Considered Options

- **27 槽表全局重排为单一 (9,7,P3) 日程(不分栈)**:拒——P1 期的值函数依赖
  全部未来槽,改未来日程必然动 P1 值(P1 零漂移门破);且 P3 真值未知期无
  全局真值可言。自适应日程(P1 期=先验 ≡ 旧解)是「P1 结构零漂移」与
  「P2 真值」同时成立的唯一解。
- **查询侧槽位重映射(不动 solve)**:拒——幻影尾在解的值函数里,重映射
  查询槽读到的仍是带幻影尾的值;假修。
- **schedule 真值读 plane_node_table(现有表)**:拒——表只辖当前位面,
  P3 期不知 P2=7(跨位面真值丢失);plane_lengths_seen 序列保跨位面记忆,
  且与写入端(每位面首帧)同点维护,单一源。
- **v1 栈 session 透传(get_node_goal/effective_hp_threshold 加参)**:缓——
  调用链(cw_evaluate/cw_plan/cw_comps/default_strategy)全部纯 state 透传
  面宽;v1 栈已被 v2 仲裁层为主干取代,收益小;记档遗留。
- **_horizon_node_goal 加 session 参数**:拒——grep 无调用方可传
  (零写入=死参数,防线字段纪律);v2 消费走 ev.dp_posture 直查。

## 验证

- 新单帧锁 12(`test_cw_w169_dp_schedule.py`):schedule_of 真值/回退/脏表
  封顶;默认日程 ≡ 旧式公式全 t 域对拍(offsets/ends/difficulty_scale/
  node_income);修正日程 boss 落 t=15/P3 前移 t=16;slot_of 等价性与越界
  防御;memo 同键同对象(P1 结构零漂移)与日程分键;dp_posture 透传
  session+真值日程解(P2 r7 帧翻转存在性);store_plane_table 每位面首帧
  重写+seen append+同位面不覆写。
- P1 零漂移门:sim planes=1 fallback 池 seeds 0-19 逐 seed 全指标
  (final_hp/hp_trail/refreshes/level/dir_round)改前 vs 改后 diff={}。
- sim A/B(同进程 flag 对照,snapshot 池同指纹 a36b110642220a11,
  seeds 0-99,planes=2):P2 姿态 tag 翻新 1242/1640(75.7%,r1 460→r7 12,
  +D6 750→642/+D2 181→244/存息 199→234=去幻影尾后更收敛);行为 headline
  波动带内(refreshes 221=221/hp0 86→85/avg_rounds 3.24→3.23/
  avg_final_hp 0.03→0.28)——姿态层修正传导到行为层被下游门/金约束
  吸收,方向=去松。
- ruff 5 改动文件全过;全量 pytest 见 W169 报告(ci_smoke 1F 为并行在飞
  域既有红,stash 本批文件复跑仍红=干净归因)。

## 影响

- cw_horizon(日程参数化+slot_of+schedule_of+memo 键)、cw_strategy
  (session 新字段 plane_node_table_plane/plane_lengths_seen)、prep_director
  (store_plane_table 每位面首帧重写)、cw_sim(P2 进场记 seen)、
  decision_v2/ev(dp_posture 透传 session+slot_of)。
- 生产 P2 修复面(与 ADR-0366 A 组叠加):DP 姿态/V_D 窗 refresh_budget/
  升级 DP 授权臂读真值日程;nodes_of_plane/battles_left_p2 生产 P2 从
  陈旧 P1 表修复为 7 槽真值。
- 遗留:v1 栈 get_node_goal/遥测影子/hp 地板先验日程(P3 真值批再裁);
  P3 首局实读表后 schedule 自适应生效。
- strategy as-built(01_posture.md §1 位面日程行)同步。
