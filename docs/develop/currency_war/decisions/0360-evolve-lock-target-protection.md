# 0360 — evolve 换血事务的锁定目标件保护

- 日期: 2026-08-26
- 状态: accepted (采纳)
- 关联: ADR-0226(deploy 围栏桥派生)、ADR-0317(生成侧守卫)、ADR-0339(种子窗保留序)、ADR-0357(P1 配方锁)、ADR-0359(买侧通道锁定约束)

## 背景与问题

W147 归因(w143_formation ledger n=100,池 bab146c68c5df11a):evolve 换血
风暴对目标件的挤出是**恶性被动挤出非主动卖**——目标件离场 60 笔中
59 笔被动(dep→bench 挤出 50 + 事务溢出卖出 10),主动卖仅 1 笔;机制:

1. 锁定后仍有 **216 轮次** applied evolve 事务目标在锁定体系外(仙舟3
   占 138)——off-lock 提案的 `execute_replacement` target_factions 不含
   锁定 faction → 锁定目标件被 old_line 整档解除逻辑划下场;
2. strict 自毁 35 局挤出后 **59% 不回场且终局全部不在场**;
3. rejected 死循环 34 局(`duplicate_on_board` 同因重提零清障——留场
   新线同名 + bench 副本进部署名单;且被拒事务仍被发射,下一轮原样重提);
4. skip_fence 绕自动部署围栏场均 5.1 轮,挤出无纠偏路径。

## 决策(四件,全部优先级/围栏式,禁一刀切禁换——成局 22% 良性中性轮换)

1. **提案层目标约束**(`registry.evolve_lock_constraint_enabled` /
   `evolve_off_lock_penalty=3.0`;`cw_evolution._best_option` 选择序降分):
   锁定帧(`cw_intention.locked_faction_scope` 非 None——p1_pair 体系键
   ∪ locked_comp 主副档键,`locked_buy_scope` 的阵营口径版本)下,off-lock
   提案在选择序减 penalty;`evaluate_upgrade` 三条件裁决不辖(降级非
   禁换,全部机会均 off-lock 时照选最优)。
2. **保留序保护**(`execute_replacement` retained 排序,ADR-0339 种子窗
   同型):old_line 溢出卖出时,锁定目标件(`locked_buy_scope` 采购集)/
   引擎件(全羁绊 ∩ TRANSITION_TRAITS,[31] top4 恒方向件)与种子窗口件
   同级最优先——先吃非保护件。
3. **deploy 围栏锁定键放行**(`select_deployments` 新参
   `locked_factions`,ADR-0226 同型扩位):锁定帧体系键按**全羁绊**匹配
   (键常为流派——燃血/欢愉,围栏基准键是主阵营)并入围栏放行集;
   cw_sim 与 deploy_bench op 双侧接线;未传锁定帧时围栏行为逐位同旧版。
4. **提案去重/退避**(`duplicate_on_board` 根治,ADR-0317 生成侧守卫):
   ①bench 新线候选与**留场新线 deployed** 同名剔除(W65 只折叠了 bench
   内部同名);②`_try` 中 simulate 拒绝的事务不再发射(旧版拒了仍返回
   tx → 每轮原样重提)并登记签名退避 2 轮(`EvolutionState.reject_backoff`)。

## Considered Options

| 方案 | 裁决 | 理由 |
|---|---|---|
| 卖出守卫(拦截目标件卖出) | ✗ | W147:主动卖目标件全部失败局仅 1 笔——空集问题 |
| 锁定帧禁换(off-lock 提案一票否决) | ✗ | 成局 22% 良性中性轮换 + 7 笔良性挤出;禁换伤良性(W147 定调) |
| _is_new_line 直接豁免锁定件(不进 old_line) | ✗(保守) | 改整档替换语义面过大;保留序(溢出先吃非保护件)同型且可分步 |
| 围栏键用主阵营口径(同 DEPLOY_FENCE 基准) | ✗ | 锁定体系键多为流派(燃血/欢愉),主阵营口径永不通配 |
| 被拒不发射即止(不加退避) | 部分否 | 同因跨轮重提仍耗决策段;退避窗 2 轮有界(W143 s26 三轮重提实证) |

## 后果

- 锁:`test_cw_w155_evolve_lock_guard.py` 6 条(降级/保留序/围栏/去重/
  被拒不发射+退避/scope 派生)+ W35 载体桩同步;A/B 见
  `.debug/temp/currency_war/w155_evolve_lock/`。
- 代价:off-lock 良性换档延后(降分让位);被拒事务不再进账本 rejected
  行(`explicit_action_rejects` 预期下降——可观测性转移进
  `[cw][ev][reject-backoff]` log 行);退避窗内该提案不重试(≤2 轮有界)。
- 边界:skip_fence 轮(显式事务 applied 轮)围栏仍跳过——围栏兜底作用于
  非显式轮的回场路径;件 1 可 A/B 关闭,件 2/3/4 无条件(行为修复本体)。
