# 0294. 红项修复合卷:engine_seed 年龄豁免 + phantom_equip sim 过滤 + 工作树收编

- 日期: 2026-08-24
- 状态: accepted

## 背景与动机

ADR-0289 §5 裁决出两个真发现(n=300 基线红项):`engine_seed_not_resold`
127/300(策略 bug:种子被卖通道当回合素材卖回,归零+白烧预算)与
`phantom_equip_no_wear` 174/300(sim 建模缺陷:supply 占位名以真装备
身份进穿着)。本卷三件小修复合并清偿,另收编遗留工作树。

## 决策

### 件1:engine_seed 年龄豁免(策略 bug,红项 127/300)

- 根因:r408(ADR-0267)同轮买卖互斥只辖 round-scoped 集;跨轮后
  保护集(双桥池∪锁线名单)**不含 engine_seed 近期买入**,四条卖通道
  (off_target/for_gold/for_interest/precache)照卖 ≤2 轮前买的种子。
- 修法:`session.v2_seed_bought`(char_id → ((plane, round), 同轮份数))
  由 decide_prep 从存活提案登记 reason=engine_seed 的购入轮;新增
  `_seed_age_blocked`:买入 ≤2 轮且同轮份数 <2 → 全部卖通道不进可卖集。
- 豁免边(与检查项 `check_engine_seed_not_resold` 镜像):同轮同名买入
  ≥2 = 3合1 素材收集语境(冗余让位合法)不拦;位面不符/无记录/旧
  session 缺字段保守不拦。
- carry 腾位门交互:腾位卖出同走豁免;但 bench 真满(≥9,本门前置)
  且唯一可卖=种子时**兜底放行**——不腾则 carry 死锁,豁免让位给 carry。
  门③的「直接卖通道可解」判据同加种子过滤(防错位空手返回)。
- 锁:买入 r=N → r=N+1/N+2 卖不选、r=N+3 可卖(测试
  `test_cw_adr0289_red_repair.py`,n=30 批内违规 0)。

### 件2:phantom_equip sim 采样过滤(sim 建模缺陷,红项 174/300)

- 根因:cw_sim supply 采样池 = `_EQUIP_VALUE` 键 + `'未知装备'`,带钻
  时 `append('钻石')` 进 `st.equips`(owned 池);`equip_allocation`
  无注册表过滤 → 占位名/语义标签以真装备身份进穿着。
- 修法:采样池对齐 `EQUIPMENT_ROSTER`(单一源)——'未知装备' 与
  价值表注册表外旧名不进池;带钻是词缀元数据,不再以 '钻石' 占位
  实体进池,改披露计数 `SimResult.phantom_supply_picks`(批报告聚合
  `phantom_supply_picks`)。锁:n=30 owned 池/equipped 全在注册表内,
  `phantom_equip_no_wear` 违规 0(修前 174/300)。

### 件3:工作树收编 + 批级入口接线欠账

- 收编遗留 138 行(`cw_sim_checks.py`:批㉚ `check_hp_ge60_frame_lock`
  + 注册行;ADR-0291 decision_v2 两检查 + 注册行)——归属核实后随本卷
  chore commit。**在飞的标定批文件(decision_v2/registry.py、
  scoring.py)不收编**。
- ADR-0289 接线欠账清偿:`run_batch_level_checks` 并入
  `simulate_p1_batch` 末尾(批级披露/哨兵/条件型检查随批自动跑,
  吃全批账本+report+pool_map)。

## 验证(n=30,snapshot 池,单进程)

- `engine_seed_not_resold` 127/300 → **0**;`phantom_equip_no_wear`
  174/300 → **0**;smoke 待裁豁免表相应两项移除,回归 0 容忍。
- 批级入口接线后新增批级键全绿/披露;`decision_v2_candidate_coverage`
  结构层探针红(sell/synthesize 候选未实现——decision_v2 生成器实现
  在飞)→ smoke 豁免表收录,实现合流后移除。
- hp_ge_60 0.133 / avg_final_hp 32.73(n=30,池指纹同快照;与
  ADR-0292 新锚 0.127/33.98 的差在 n=30 分辨率底内,不可作方向判读)。

## Considered Options(最值钱栏)

- **只修 sell4gold/off_target(ADR 字面两通道)**:拒绝——检查项辖
  **全部** SellBench,for_interest/precache 不加豁免则红项只降不清零;
- **carry 门硬禁种子**:拒绝——bench 真满且唯一可卖=种子时 carry
  死锁(门空手返回,carry 永远买不进),兜底放行是死锁豁免非漏洞;
- **件2 在 equip_allocation 层加注册表过滤**:拒绝——生产侧批⑲ F2
  路径已被过滤,病只在 sim 采样层;在分配层再加=双源防御掩盖采样
  缺陷;
- **'钻石' 保留进池但分配时排除**:拒绝——带钻在游戏里是词缀不是
  装备实体,进池本身就是伪实体;披露计数保留其 sim 痕迹。

## 后果

- 红项两真发现闭环:检查项回归 0 容忍(smoke 豁免表收缩到 3 项:
  dead_system_second_pivot/degrade_recover_mutex/decision_v2_
  candidate_coverage);
- session 新字段 `v2_seed_bought`(旧 session 反序列化保守空);
- 旧锁 `test_round_set_resets_per_round`(r408 批)断言「r5 立即跨轮
  卖回合法」——本裁决推翻该语义,测试改为窗口断言;
- 遗留:numbering——decision_v2 在飞标定批代码注释亦引用「ADR-0294」,
  其 ADR 落盘时需顺延编号(本卷占用 0294)。
