# ADR-0308: sim 回退层节点胜率换 W31 实测节点×轮次阶梯

- 状态:accepted
- 日期:2026-08-24
- 背靠:sim 校准层(Δ池不可达时的回退结算);supersedes
  ADR-0277 件2(boss 胜率=f(成型度) rung 门)与 ADR-0306 件2
  (rung≥3 = rung2 桶外推)的**胜负面部分**——幅度层(损益分布)
  与 Δ池主路径不变。

## 背景与动机

W31(路线 A 原型,`cw_dev/deep_read/W31_报告.md`)在 P1 replay
语料(n=192,plane=1 & killed 非空 & board_before 非空)上实测:
**胜负几乎被 node_type × round 决定**——奖励轮 1.0 / 普通战斗
0.29(r3 0.30 / r4 0.29)/ 遭遇 0.04 / boss 0.05;完成度控制在
轮次后无增量信号。报告 §6.3 明确指出:该阶梯可替换 sim 校准层
拍脑袋的节点胜率——比完成度映射本身更快变现。

被替换的拍脑袋值(`cw_sim.py` 回退层):

| 节点 | 旧胜负面 | 性质 |
|---|---|---|
| battle | 方向二元门控(方向已立→胜,WIN_DELTAS) | 胜率从未按节点实测 |
| encounter | 结构性恒败(p=0) | 无胜分支 |
| boss | rung 表 (0, 0, 0.25) + rung≥3 = rung2 桶外推(≈0.667) | 跨节点(battle→boss)外推,ADR-0306 已自认边界 |
| reward/supply | 恒胜(+2) | 与实测 1.0 一致,不变 |

## 决策

1. 回退层胜负面统一走单一取值口 ``node_win_p(node, round)``:
   ``NODE_WIN_P_LADDER``(逐轮实测组合)优先,缺组合退
   ``NODE_WIN_P_BY_TYPE``(类型边际)。常量带来源注(n=192,
   W31_报告)。
2. 损益幅度层全保留(battle:WIN_DELTAS/LOSS_BASE/LOSS_PER_ROUND;
   encounter:boss 档×1.15;boss:BOSS_BY_DIR_ROUND)——W31 语料
   只有 killed 二值,无胜幅度分层。
3. ``_SAMPLER_VERSION`` 5→6(结算语义变更,池内容不变,指纹变);
   快照 META 指纹与 ANCHOR_REGISTRY_N300 重记。
4. 检查网随动:
   - ``check_boss_win_calibration``:恒败判定加 n≥100 地板
     (阶梯 boss 胜率 ~0.05,小批 0 胜是抽样噪声:0.95^25≈28%,
     原「存在即判」在 smoke 级恒假红);删「胜率随深度单调」判据
     (旧判据把已废弃的「胜率=f(成型度)」设计当真值锁);
   - ``check_boss_win_p_cache_freshness`` 整体删除(被检机制
     boss_win_p/``_BOSS_WIN_P_EXTRAPOLATED`` 缓存已不存在)。

## Considered Options

- **A(采纳):阶梯边际替换全部回退胜负面**——语料直证,单一
  取值口,边界显式(病局镜像、无条件性)。
- B:只换 encounter/battle、boss 保留 rung 门——boss 恰是外推
  证据最弱的一档(rung≥3 的 0.667 来自 battle rung2 桶 n=6 跨
  节点外推),保留 = 保留最拍的数字,否决。
- C:阶梯为基率 × rung 调制(保成型价值链)——语料无 rung 条件
  分布支撑,调制系数只能再造一层拍脑袋,否决;rung→hp 耦合在
  Δ池主路径(battle rung 桶采样)仍在,回退层耦合损失可接受。
- D:等新策略语料再换——W31 数字是当下唯一实测,旧 rung 门
  继续给 sim 假 hp 天花板,否决。

## 后果

- 正面:回退层胜负面全部有语料出处;fallback 与 Δ池两态的
  胜率口径同源(同一 replay 语料)。
- 负面/边界:**阶梯来自旧策略(line_strategy)病局语料——六局
  同型败的镜像**(W30/W31 收账判读):①它是「旧策略在各种板面
  下的边际胜率」,不含成型度条件性;②新策略(decision_v2)语料
  攒够后**应重标本表**(届时遥测 board_before 补记角色名+星级,
  条件性才可标定)。注记在常量注释。
- hp 类锚指标下移属预期(hp_ge_60 0.137→0.09,avg_final_hp
  35.68→32.08);策略侧锚零漂移(engines2/recipe5/refreshes
  逐位持平)= 只有结算校准变了,决策行为面没动。
- ``formation_hp_coupling_sentinel`` 仍绿(快照主路径 battle
  rung 桶耦合仍在,25 局 diff +5.33)。
- 快照指纹仅随版本重算(池内容不变);全量生成器重跑**推迟**到
  W39(历史语料回填)合流后,避免语料增量与本版本变更耦合在
  一次指纹变更里。

## 回归验证

- 新增/更新锁:node_win_p 阶梯数字锁 + 废弃机制残留检查
  (adr0306 测试文件);boss 阶梯胜率扁平锁 + 批量胜局涌现
  (150 局,ADR-0308 口径)(r413);恒败判定 n 地板双向锁(r413);
  boss_settle 单一取值口 source 锁(battle_rung 测试);
  _SAMPLER_VERSION==6 两处(adr0292/r409);cache_freshness 六锁
  删除(b37)。
- n=300 seeds 0-299 snapshot 重记锚(上文数字);smoke 25 局
  非豁免检查全绿。
- ⚠️ 全量回归受 W35 载体批在飞改动的**既有断裂**阻塞
  (decision_v2/candidates `_star_weighted_copies` 改名未同步
  cw_sim_checks 调用点)——与本批无关,时序见 W37 报告。
