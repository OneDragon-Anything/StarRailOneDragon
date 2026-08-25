# 0361 P2 段 V_D 修法(DP 窗授权 + 机会成本口径 + 存活收益口径)

- 日期:2026-08-28
- 状态:accepted(直接落地)
- 关联:W152 断点解剖(`.debug/temp/currency_war/cw_dev/deep_read/W152_报告.md`)、
  W153 公式批(P11/P12,`docs/game/currency_war/research/proofs/`)、W150/0359
  (让路批)、0356(出口金底线/回档口径)、W126/0349(V_D 批口径本体)、
  user_playstyle [17](溢余即花簇主条)/[27](掉血 B+P)/[18](hp 计价非触发)

## 背景

W152 判据级解剖:P2 全部 14 个 shop 决策帧的 D(刷新找牌)拒绝,断点串联在
评分层 `vd_refresh_score` 两个判据——

1. **等级窗二分 ×13 帧**:`_resolve_level_goal` 返回 `level_up`(comp 的
   level_plan 在 lv5-7 普遍说升)→ 直接 return None → D 候选恒 −2 金非正分拒。
   这与 DP 姿态**直接冲突**:DP 日程表输出「升级+D6」(升级与刷新是**并行**
   预算,`level_cost+2×rolls` 已算进同一笔 spend),评分层的互斥窗把 D 预算
   整个吞掉——「D 让位给升」从让一拍变成让整个位面(P2 每轮 goal 都说升,
   升级每轮只推进一点)。
2. **批口径 EV 全负 ×1 帧直接判 + 13 帧次级全负**:收益 23-38 金(P1 骨架
   参数 loss=10/battles=5)vs 批口径面值 spend 42-135——金 85-160 溢余带
   死(四局实机,金堆到死无出口)。

实机四局(run15-18)金 85-160 全程零 RefreshShop,带死出局。

## 决策(按 W153 公式;常数全部归 registry 可 A/B 注入)

1. **窗判据(W152 修法①)**:P2 段(plane≥2)的等级窗二分改**消费 DP
   `refresh_budget` 授权**——姿态 refresh_budget>0 → 窗开(升级与 D 并行,
   DP 已给组合预算);=0 → 仍让位;DP 查询异常(None)→ 保守回退 P1 的
   level_plan 门(对局不停)。P1 分支逐位不动。
2. **成本侧(P11)**:P2 段成本项=**决策成本口径**(替换批口径面值 spend):

   ```
   C_dec(g,s) = Δinterest × min(R, vd_p2_recovery_rounds) + ρ·s
   ```

   依据:P11 已证溢余段(g−s≥50)Δinterest=0、息帽已满 → 面值成本高估
   ≥20×;[17] 簇主条「>50 的每一分都没有存的意义,该 D 牌 D 牌」= 用户
   权威直接裁面值口径出局。**预算硬界必须同上**:批口径期望刷金
   s ≤ g − boss_floor——C_dec→0 后 EV 不再是约束,约束移授权层(防
   「C=0 无限刷」)。
3. **收益侧(P12)**:P2 段收益=Δrung×R + Δh3_win × `vd_p2_loss` ×
   hp_to_gold × `battles_left_p2(state)`——loss 用 P2 实测带 15-17 取保守
   中值 16([27] B+P;真值采集点=结算屏 OCR 三项拆解);battles_left 用
   state 推导(`session.plane_node_table` 槽序表数剩余非战斗 token 外槽位,
   表缺失退 registry 缺省 5),非 P1 骨架缺省。**P1 分支逐位不动**。
4. **A/B 通道**:`vd_p2_enabled`(False=回 W153 前行为)。

### 行为变化清单(四局真帧回放,W154 回放断言脚本)

- 6 帧翻正(run16 r1/r2/r4、run17 r1/r2/r4:2费@lv6 j=2 真帧,V_D
  ≈ +38~+42)——DOT队卡芙卡找件通道打开;
- 8 帧仍拒:run15×3 + run16 r5 + run18 r1(预算硬界:批口径刷金 81-135
  > g−10)/ run16 r6/r7/P3r1(核心已 2★,找件目标消失,与修法无关);
- P1 段零漂移(见验证)。

## Considered Options

- **仅修窗判据(不动 EV 口径)**——否决:14 帧 V_D 全负(W152 replay 实算),
  窗开了也被「非正分」拒,单修无效。
- **仅修 EV 口径(不动窗)**——否决:13/14 帧仍被窗二分打空,双保险断点
  必须双解。
- **P2 加金门旁路(金>满息+溢余时窗降权)**——否决:又造一个金门常量,
  与 DP 授权语义重复;DP refresh_budget 是现成的、语义正确的授权单一源。
- **j=2 退回单次边际口径(W152 候选③)**——否决:P12 已证「收益侧换 P2
  参数」覆盖该诉求;P5 检验点①「禁边际口径」边界澄清后无需另立口径。
- **interest_rule 的 D 分支也改回档口径**——不在本批:P5⑤ 金 50/51 拒 D
  的退化输出辖「从 ≥50 跌破 50」的降息档,P2 帧金 80+ 时 spend 由预算硬界
  辖,两界叠加已闭环;interest_rule 买侧/刷新分叉维持 0352 现状。

## 影响

- `scoring.vd_refresh_score`:P2 分叉(窗/成本/收益三处);P1 逐位不动;
- `ev.battles_left_p2` 新推导(消费 `session.plane_node_table`,写入端=
  prep_director r306 首帧,生产路径已存在);
- `registry`:vd_p2_enabled/vd_p2_loss/vd_p2_recovery_rounds/
  vd_p2_liquidity_rho 四常数(可 A/B 注入,hash 锁同步);
- sim 边界声明:现有账本无 P2 段(simulate_p1 只跑 P1),本批 sim 对照以
  「P1 段零漂移」为回归门 + 单帧锁为主验证;P2 段 sim 覆盖=独立大工程
  不在本批。

## 验证

- ruff 通过;
- 新单帧锁 11 条(`test_cw_w154_p2_vd.py`:窗授权×3/正例×3/负例×2/
  battles_left 推导/P1 逐位不动/四局真帧回放判定)+ 受影响 hash 锁同步;
- 四局真帧回放断言脚本(W152 replay_vd 改造,`.debug/temp/currency_war/
  w154_p2d/replay_vd_after.py`):14/14 帧判定符合预测表;
- P1 零漂移 A/B 门:同进程 flag on/off 各 20 局(池指纹同),全指标
  diff={}(逐位一致);
- 全量 pytest:本批文件就绪后 2186P/0F(并行批 W155 在飞 strategy.py 编辑
  造成的 1 个瞬时失败除外,见 W154 报告声明)。
