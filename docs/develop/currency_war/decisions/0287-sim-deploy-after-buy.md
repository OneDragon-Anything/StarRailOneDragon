# ADR-0287: sim 部署时序对齐生产序(买后部署)+ HP 上界钳制

- 状态:accepted
- 日期:2026-08-24
- 批次来源:批㉘ F1-F6(压测报告 `sim_压测_批㉘_2026-08-24.md`,已裁决)
- 关联:r422;ADR-0271(deploy pop 语义)/ADR-0276(sim 接线先例)/ADR-0279(rung 结算键)/ADR-0284(槽消费)/ADR-0286(前批 sim 语义修)

## 背景与问题

批㉘ 审计回合内编排序域:生产备战单轮(battle_prep.py)实锤序 =
⓪收球→①买牌(含升级/刷新)→**②部署**→③装备→④出战;而 sim 的部署块
在**轮首**(收入入账/商店抽取/买/升级之前)。后果(n=300 观测):

- F1:890/2698 轮(33.0%)「当轮可上未上」(1124 件次,双峰 r1/r3/r9);
- F2:结算键滞后——rung(`_settle_rung`)与 depth(`_deployable_depth`)
  读滞后一档的 deployed;**boss 轮 53.6% 结算键滞后**(BOSS_WIN_P_BY_
  ENGINES 读低一档成型度);
- F4:encounter/boss 的 depth 桶键同滞后(桶级失真比 rung ±1 档更粗);
- F5:LevelUp 当轮 cap 不生效(293 滞后轮含升级;cap+1 空位滞留一轮,
  「升级→上阵」即时战力链断一轮,批⑦「升 7 级 EV≈0」的语义地基被
  时序吃掉一截);
- F6(潜伏):HP 结算 `max(0, …)` 无上界——当期无害(语料 max 88 /
  sim max 92 均未触界),但批㉗ reward 胖尾修复(+20~39 回血)落地后
  hp 可破 100,hp_ge_60 换方向虚高。

配对干预臂(只 patch 结算键读「买后部署」反事实)已量化:
avg_final_hp 29.39→31.78(**+2.39hp 下界口径**,se 0.554,超 n=300
非配对分辨率底 ±1.93),hp_ge_60 +3.3pp——且是 sim hp 低估裂口的
又一已量化分量,与批㉗ 胖尾修复正交可叠加。

## 决策

1. **部署块整体移位**(cw_sim `simulate_p1`):从轮首移到**决策段循环
   之后、轮末升级 while 之后、结算之前**——生产序 ⓪→①→②→④ 对齐。
   结算键(rung/depth)随动读买后板(战斗读买后真值,不再滞后);
   LevelUp 当轮腾出的 cap 在部署时 `st.max_units()` 立即生效(F5 链通)。
   目标集(_tf/_tc/_fw)改在部署点从 session **买后现读**(生产语义:
   买牌段 update_target 已刷新,锁线轮目标已更新)。
2. **deploy_lag_units 披露**(批㉘ 检查项 ledger_deploy_lag_disclosure):
   部署后重放围栏(`select_deployments` 同参),残留可上件数入账本
   sim 节 + batch 汇总——买后部署语义下应恒 0;>0 = 部署时序回归
   (重构再犯轮首序)/围栏漏上,由 check_deploy_after_buy_semantics
   常态扫出(观测臂 33.0% 的口径固化为检查)。
3. **HP 上界钳制**(F6,检查项 hp_upper_bound_truth):游戏机制真值
   **未见文档证据**(语料 max 88 / sim max 92 均未触界,非 cap=100
   证明)——暂按 `HP_UPPER_BOUND=100` 钳制(cw_sim 常量,检查模块
   同步镜像),防批㉗ 胖尾修复落地后 hp 破百;实机满血样本核真后
   更新常量(检查项锁 hp>100 恒 0)。

## Considered Options

- **只 patch 结算键读反事实**(批㉘ 干预臂口径):拒绝——那是下界
  测量不是修复;策略决策读的 deployed/bench 仍滞后,块移位才是
  生产序语义本身。
- **部署块移位但目标集仍轮首读**:拒绝——生产部署时 target 已被
  本轮 update_target 刷新(尤其锁线轮);轮首快照是批㉘ 盲区标注的
  「近似,偏差方向未定」,移位后无理由保留。
- **HP 上界按语料 max 88 钳**:拒绝——88 是未触界观测非机制真值,
  按观测值钳会截掉合法的 89-100 区间;cap 100 是保守哨兵,真值
  待实机满血样本(核真须用结算屏/备战关店帧,shop 开态 HP 显示位
  被遮是已知观测陷阱)。

## 验证(n=300 / seed_base=90000 / pool='snapshot' d891233d28be3493,配对 seed)

| 臂 | avg_final_hp | hp_ge_60 | losses_le_2 | engines2_by_r6 | deploy_lag |
|---|---|---|---|---|---|
| 基线 HEAD 8a9324a6 | 27.073 | 0.0367 | 0.057 | 0.220 | —(旧序) |
| 本 ADR(部署移位) | 31.337 | 0.0700 | 0.140 | 0.347 | 0 |

+4.26hp / +3.3pp / losses_le_2 +8pp——**超批㉘ 下界 +2.39 预期**
(下界只含结算键通道;块移位让后续轮决策看到更满的板,全效应 ≥
下界,盲区标注兑现)。checks:deploy_after_buy_semantics /
ledger_deploy_lag_disclosure / hp_upper_bound_truth 全 0;既有违规
集(carry_gate 1 局 / delta_pool 桶饥饿 / endgold 比值)与基线逐项
一致,无新增。
