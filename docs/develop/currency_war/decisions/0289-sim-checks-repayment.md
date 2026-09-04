# 0289. 检查项清偿批:29 批压测 123 条设计落地 cw_sim_checks

- 日期: 2026-08-24
- 状态: accepted(清偿性质大卷)

## 背景与动机

29 批 sim 压测(测试官常设角色)累计产出 **123 条「检查项设计」**(各报告
「检查项设计」节,只设计不实现),其中 29 条已随各批裁决进
`cw_sim_checks.py`。其余 **94 条积压**——用户点名批评「问题较大的应该留下
回归」:压测发现的问题若不固化成检查项/单帧锁,同类病下次仍靠 sim 批量
重跑暴露。本批(检查项清偿批)把积压设计按三分类清偿:**可直接实现 /
条件披露型(前置依赖未满足)/ 归档(语义已被后续修复取代或设计非检查项)**。

## 决策

### 1. 分类处置(94 条 → 48 实现 + 46 归档)

**实现 48 条**(全部带 docstring 记判据出处=哪批哪发现):

- **逐局违规锁(12,进 _BATCH_CHECKS)**:gold_nonneg(批⑮F6)/
  bench_capacity(批⑰F6)/deployed_schema_filter(批⑧F3)/
  engine_seed_not_resold(自由批)/buys_at_full_bench(自由批+ADR-0283)/
  oscillation_xp_cap(自由批观测)/levelup_flat4_lock(批⑳F3 裁决)/
  phantom_equip_no_wear(批⑲F2)/carry_on_shelf_responded(成型批)/
  no_future_carry_sold(成型批)/dead_system_second_pivot(成型批)/
  degrade_recover_mutex(批⑯F5,条件违规——[31] 降级未实现期以 pivot
  摇摆指纹辖);
- **批级聚合/披露/哨兵(25,经 run_batch_level_checks 聚合入口)**:
  成型批 3(late_deploy_full/no_streak_buy_freeze/hoard_gold_no_engine/
  second_engine_deadline=4)+批⑫ 4+批⑭ mc_faction_calib+批⑰
  carry_gate_outcome_tracking+批⑱ 2+批⑲ 2+批⑳ hp_readable+批㉓
  briefing_pipeline_liveness+批㉔ deploy_cap_reader_noise+批㉗ 4+批④
  shop_cost_conformance/rare_metric_min_n+批⑥ recipe_refresh_ev_guard+
  批⑬ encounter_rung_sample_budget+自由批 boss_round_real_actions;
- **语料级(3,吃 outcomes/summary,调用方显式调)**:attach_run_detector/
  hp_monotonic_sentinel(批⑬)/plane_reached_consistency(批⑧F4);
- **锚登记/工具(8)**:S300 第二参照段(批⑭)/低可见通道 registry 含
  commit 归因注记(批⑳/㉑)/段间噪声带(批⑯)/adr0266_ab_guard(批⑤)。

**接线分工**:逐局锁自动随 simulate_p1_batch 跑;批级入口
`run_batch_level_checks` 已就绪,**cw_sim.py 侧接线(worker X 在飞,
冲突隔离)合流后并入**;条件披露型统一「依赖在则判,不在则披露跳过+
注释标依赖」。

**归档 46 条**(死因清单,报告名+条目+死因;节选大类):
- 批⑤ `mid_interest_floor_reachable`——ADR-0266 裁决后 `_MID_INTEREST_
  FLOOR` 已删,检查项死;
- 批⑲ `levelup_click_cost_truth`(逐级真值表版)——批⑳ 裁决 flat 4,
  原设计作废(改实现为 flat4 账本锁);
- 批⑮ `anchor_reregister_d891233d`——快照重生成+新锚已在 ADR-0279/0284
  落地,登记动作完成态;
- sim 演进清单类(成型批 S3/批⑦ sim_bench_excludes_deployed/批⑧
  sim_deploy_fill_after_O/批⑲-㉓ 建模升级族)——非检查项,是校准层
  升级任务(归 sim 演进清单,ADR-0219 域);
- 生产侧接线类(批⑨ OCR 修复/批⑫ 遥测字段/批⑬ runs 标签写入端/
  批⑮ default 栈 config seam 等)——落点是 cw_telemetry/battle_loop/
  cw_plan,不在 checks 模块域;
- 策略实现类(批⑯ carry 门修复本体/批㉒ 槽消费修复本体/批㉘ 部署时序
  修复本体等)——修复已随各 ADR 落地,本批只补其验收检查;
- 数据采集项(批④ sell_refund/批㉒ merge_ret_copies_truth/批⑮
  fallback 遥测等)——采集任务非断言,归采集清单。

### 2. n=300 验证(新条目应全绿或披露)

n=300 s0-299 pool=snapshot(指纹 d891233d28be3493)全检查网
(输出:`.debug/temp/currency_war/cw_dev/sim_repay_n300_final.json`,
不入 git):**逐局锁 27 键中 22 绿**;**新发现红条目 5 项进「待裁」
清单**(见下);批级 26 键全披露型(0 违规,依赖未接线项显式「跳过
不判」);既有检查(delta_pool_bucket_min_n 7 / sim_endgold_calib 1)
红与树内 worker W 在飞改动相符,非本批引入。

### 3. 新发现待裁清单(n=300 红条目,如实报不裁决;裁决见 §5)

| 检查项 | 红/300 | 初判 |
|---|---|---|
| `phantom_equip_no_wear` | 174 | sim supply 装备占位名进穿着(钻石126/翁瓦克25/超级电池23/未知装备19/能量饮料18)——批⑲ F2 判读的 sim 侧同族:supply 占位名未被装备分配层排除(真发现候选) |
| `engine_seed_not_resold` | 127 | sell4gold 通道把 ≤2 轮前 engine_seed 买入当素材卖(种子归零;自由批 0 容忍判读的跨轮残留形态,真发现候选) |
| `dead_system_second_pivot` | 158 | **判据过严候选**:口径修正后仍与等级供给门混杂(低级只见 1 费,目标件 2-3 费结构性零出现)——待裁决收紧口径(如只辖高等级段)或降披露 |
| `carry_on_shelf_responded` | 7(2.3%) | 设计报警线 30%/目标 <10%——达标内残留,指纹保留不裁 |
| `degrade_recover_mutex` | 3 | pivot 摇摆指纹(seed 57/89/189);[31] 降级落地后按 relapse 语义升级判读 |
| `shop_cost_conformance` | 2 | lv4 2费/3费零供给——疑 XP 重放等级混杂(行末 level≠抽牌时点 level,批⑭ 实证 26% 行偏差),非池截断回归 |

### 4. 中途判据修正(证据驱动,非调绿)

`dead_system_second_pivot` 首版按「阵营全卡在店数<tier」实现,n=300
实测 253/300 红(列车同行全池仅 1-2 名成员,「供给<2」是常态)——与
设计时观测(13/60)量级矛盾,判为**首版口径错**,修正为「线目标件
(carry∪core∪opportunistic)在店连续 3 轮零出现」。修正后 158/300,
仍高——混杂分析进待裁清单(见上),不在本批二次改判据。

## 5. 红项裁决表(§3 待裁 → 清偿批收口裁决;证据=代码定位+n300 数据)

| 检查项 | 红/300 | 裁决 | 证据与动作 |
|---|---|---|---|
| `phantom_equip_no_wear` | 174 | **真发现(sim 侧建模缺陷,非生产 bug)** | `cw_sim.py` L1184 supply 采样池 = `_EQUIP_VALUE` 键+`'未知装备'`,L1194 带钻时 `append('钻石')` 进 `st.equips`(owned 池),`equip_allocation` 无注册表过滤 → 占位名/语义标签以真装备身份进穿着。生产侧批⑲ F2 路径(SIFT 占位)已被过滤,病只在 sim 校准层。动作:修 sim supply 采样对齐 `EQUIPMENT_ROSTER`、`'钻石'` 改元数据通道不进 owned 池;修复落地前保持红(smoke 豁免) |
| `engine_seed_not_resold` | 127 | **真发现(策略 bug,待修)** | `_sell_for_gold`(line_strategy L990)卖「保护集外最弱件」——保护集=双桥池∪opportunistic∪carry,**不含 engine_seed 近期买入**;唯一年龄护栏 `_round_sell_blocked`(r408)只辖同轮。设计 0 容忍(种子 ≥2 轮不回卖)从未落进 sell 通道(设计时现状 169 次即卖的残留形态)。动作:session 记 seed 购入轮,sell 通道(sell4gold/off_target/for_interest)加 ≤2 轮种子年龄豁免 |
| `dead_system_second_pivot` | 158 | **检查器误判(判据与等级供给门混杂)** | 口径一次修正(253→158)后仍红过半——低等级段只见 1 费、目标件 2-3 费结构性零出现被计为「死守死线」。动作:修检查器——仅辖「当轮供给可见目标费位」的轮段(level 已达目标费位解锁);本批不再二次改判据(§4 纪律),归下一批 |
| `carry_on_shelf_responded` | 7(2.3%) | **达标内残留** | 设计报警线 30%、目标 <10%——2.3% 在目标内。不动,指纹保留继续观测 |
| `degrade_recover_mutex` | 3 | **依赖未满足(判读语义待升级)** | [31] 凑档降级(ADR-0288)已落地,检查仍停在「降级未实现期 pivot 摇摆指纹」。按既定升级路径改 relapse 语义(降级买入后再 pivot 同线=relapse);3 局(seed 57/89/189)待升级后复核 |
| `shop_cost_conformance` | 2 | **检查器误判/依赖未满足(XP 重放等级混杂)** | 账本行 level 是轮末值≠抽牌时点(批⑭ 实证 26% 行偏差),lv4 的 2/3 费零供给疑为时点错位非池截断回归。动作:依赖账本补 wave 时点 level 字段后对齐重判;无字段前按披露处理 |

裁决后续:真发现 2 项(phantom/种子回卖)进修复待办(落点分别是 cw_sim supply 采样层与 line_strategy sell 通道);检查器误判 2 项进检查网修订待办;达标内 1 项与依赖未满足 1 项保持现状。修复/修订落地后从 smoke 豁免表(`test_cw_sim_cli_smoke._PENDING_ADJUDICATION`)移除,回归 0 容忍。

## Considered Options(最值钱栏)

- **全量 94 条都实现**:拒绝——归档类(死门/已完成态/他域任务)实现
  出来 = 恒绿死码,污染检查网信噪比;
- **只实现 0 容忍类、放弃披露型**:拒绝——设计表大量「先建观测」条目
  正是防「headline 一致掩盖低层移动」的低可见通道(批⑳/㉑ 教训),
  条件披露型(依赖在则判,不在则披露跳过)兼顾两侧;
- **cw_sim.py 一并接线批级入口**:拒绝——worker X 在飞(批㉘ 段已落
  1249 行未提交),碰 cw_sim = 冲突面;聚合入口先行,接线随合流;
- **红条目就地降级换全绿**:拒绝(纪律「不许为了绿改判据」)——红
  条目单列待裁清单,证据与混杂分析如实呈报。

## 后果

- 检查网从 15 逐局键扩到 27,批级披露 26 键;新条目 docstring 全部
  记判据出处(哪批哪发现),n=300 基线归档(.debug,不入 git);
- 5 项红条目已裁决(§5):2 项真发现(phantom=sim 采样层缺陷/种子回卖=sell 通道无年龄豁免)、2 项检查器误判、1 项达标内、1 项依赖未满足;
- cw_sim 接线欠账:run_batch_level_checks 并入 simulate_p1_batch
  (worker X 合流后);
- 锁测试:`test_cw_sim_checks_repay.py` 24 条双向(构造违规必报/
  好样本必过)。
