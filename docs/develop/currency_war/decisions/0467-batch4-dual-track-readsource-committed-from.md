# ADR-0467: 批 4 commit-2/3——双轨读口换 committed_from 权威派生(C7 零漂移 + C5 显式传参,实测零行为差)

## 状态

accepted(2026-09-03;W653 批 4)

## 背景

`dual_track_phase` 字段族的 v2 主栈消费面按方案丙切分(蓝图 §4.3-R1:禁止「getattr 缺省 False→恒已定型→激进化」的装配边界漏网病理):C7(`cw_recipe.decision_target` 双轨判定直读 GameState 双轨标志)与 C5(`cw_economy._want_level_up` 的 committed 实参同源直读)是本批可原地换源的两点;C1-C6 挂账层读点随买层接管批处置。

## 决策

1. **C7 零漂移换源(commit-2)**:`decision_target` 双轨判定改 `prep_brain.committed_from(session, state)` 权威派生。零漂移依据:decision_v2 生产路径 `transition_framework` 恒 ''(framework_startup 休眠开关关、无写端),换源前后双分支同返回 `target_comp`(W646 攻击面 3 实证)。零漂移锁:`test_cw_w653_c7_zero_drift`(fw≡'' 象限恒等 + 双轨/定型语义保留 + 无意向供给保守 False 变异锁 + 源级不回滑守卫)。
2. **C5 显式传参(commit-3)**:`_want_level_up`/`cw_plan.level_up_gate` 增 `committed: bool | None` 显式参数;None=挂账层旧口径(读双轨标志,`cw_plan.plan` 内部消费面暂留,删除点=买层接管批);dv 腾席链 b 两调用点(fresh/stale)从 `committed_from` 取权威值传入。
3. **C5 差异声明(实测量级=0,W646 预期修正)**:W646 攻击面 3 预期「fresh 帧升级门收紧(激进化病理修复)」的前提是姿态供给消费 `committed`;批 3 预算收权(ADR-0465)后 `get_node_goal` 供给核(`schedule_upgrade`/`refresh_ev_budget` 标量投影)已不消费该参数——目标级由排程核决定。实测:sim 5 seeds 升级时机分布(stash 前后同 seed 对照)逐位一致;单元面无「committed→target_level」差异路径可构造。因此本换源当前为**语义 prophylactic**(消除双轨标志直读的误导面 + 补齐装配边界鲁棒性),行为量级=0;若未来姿态供给恢复 committed 消费,换源面已就位、漏回填病理不会复活。

## Considered Options

- **C5 不动(等买层接管批一起)**:否决——`dual_track_phase` 直读留在活路径(dv 腾席链)上,与 grep 守卫验收「读点=0(豁免层除外)」冲突;且豁免面越大守卫越不可实现(W646 修正⑤)。
- **committed 从 `cw_plan.level_up_gate` 签名删除、改全局读 committed_from**:否决——`level_up_gate` 是 plan/腾席链共用单一源,plan 侧挂账层仍按旧口径,签名删参=挂账层行为批被提前触发。
- **C7 保持 getattr 直读**:否决——getattr 兜底 False=恒按定型=配方伪 comp 静默丢失(W642 识别为静默劣化点)。

## 后果

- 正面:`dual_track_phase` 的 v2 活路径读点归零(剩挂账层 cw_plan/cw_evaluate/cw_comps/cw_economy 旧口径面,豁免挂账);decision_target 换源后与 adapter/prep_director/deploy_bench 同一读端。
- 代价/边界:行为分布本批无可见变化(sim 实证),「收紧」收益是结构性的(防未来回归);零漂移锁与行为锚归档 `.debug/temp/currency_war/w653_batch4/c5_{baseline,after}.json`。
- 验证:L1 1850 绿(除并行批在飞红);ruff 改动文件全绿。
