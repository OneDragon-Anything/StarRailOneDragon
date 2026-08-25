# 0367 — ①资格锁定局的过渡对保护副方向

- 日期: 2026-08-29
- 状态: accepted (采纳)
- 关联: ADR-0357(P1 配方锁,①通道保留 comp 的设计源头)、ADR-0359(买侧锁定目标约束,scope 单一实现)、ADR-0360(evolve 保护四件,消费 locked_faction_scope)、ADR-0363(引擎下界守卫,保护基准扩辖对象)、W164(判读与 R1/R2 裁决原文,`.debug/temp/currency_war/cw_dev/deep_read/W164_报告.md`)

## 背景与问题

W164 判读(同池 62159448f0d72ad3 与 W163 精确同池):inject on 口径
strict_mal 0.20 vs off 0.05 的差值 15 局全部来自①资格通道——注入策略/
环境信号 r1 即锁终局 comp,其采购集(`locked_buy_scope` 的 comp 分量)把
囤货方向从过渡引擎引开(engines2_by_r6 0.27→0.15 同根同向),evolve 按
comp 线换档拆过渡体系(S2 挤出 19/20 mal 局)。这是 W145 主灶(P1 锁定
产物错为终局 comp)在①通道的残留:W145 按 [23] 刻意保留①通道锁 comp
(直通线合法例外),但其 P1 段的过渡验收形态冲突([20]/[13])当时未处理。

W164 已排除另两个假设:约束不弱(mal 买主体 61% 是 comp 采购集线内件,
约束按定义不辖;off-scope 泄漏 6 笔全落设计内豁免面)与时序不晚(comp
锁 r1 即立)——真问题是锁的**产物语义**,不是锁的时点或约束强度。

## 决策(R1+R2 裁决落地;flag `P1_LOCK_TRANSITION_PAIR`,默认开)

①资格锁定局(P1 锁终局 comp)的 P1 段,过渡对=**受保护副方向**:
comp 采购集仍为主方向([23] 直通权不变,核心件优先级与 hoard 目标件集
逐位不动),过渡对享二级囤货/成型优先:

1. **意向层**:`IntentionState.transition_pair` 新字段(非空 ⟺ P1 ∧
   locked ∧ P1_RECIPE_LOCK 开);派生口径与 `p1_pair` 同源复用
   (`_derive_p1_pair`,四体系支持度 top-2,随资产重派生=[20]
   「变体按来牌选」);撤销(两出口)/逐出/出 P1 清空。不复用 `p1_pair`
   字段:该字段契约(ADR-0357)是配方锁局的**锁定产物**,复用会污染其
   目标语义/hoard mode/遥测标签。
2. **买侧 scope ∪**:`locked_buy_scope` ∪ 对成员集(对件免 demote/
   免 final_fence,[22]④ 有用先囤——便宜囤对件不与 comp 主方向抢预算:
   对件不进 hoard 目标件集,经 engine_seed/pair/bond_fallback 通道二级
   买入,comp 主序对副序);`locked_faction_scope` ∪ 对体系键(希儿系
   展开=量子同频+贝洛伯格,同 `_pair_members` 口径)。
3. **guard 基准扩辖(R2)**:`_locked_protected_names`(evolve 溢出
   卖出保留序)/`_off_lock_opt`(off-lock 提案判据)消费上述两 scope
   → 对件自动受「换血可以拆引擎不行」保护(W160/ADR-0363 守卫的基准
   面);现状①锁局过渡体系件中非三羁绊成员(希儿系)裸奔。evolve 侧
   零代码改动(∪ 同式经既有接口)。
4. **成型验收**:`form_ok` locked 路径在①锁局(comp 三件套之外)再要求
   `fallback_engines_count ≥ phase_fallback_min_engines`——[13]/[20]
   P1 验收形态仍是体系对,comp 三件套即停手会饿死过渡引擎
   (engines2_by_r6 下移的组成面);formed_stop 同谓词族自动跟随。
   配方锁局(走兜底门)/P2+/未锁局不辖。

## Considered Options

- **复用 `p1_pair` 字段装①锁局副方向**:拒——污染 ADR-0357 锁定产物
  契约(非空=配方锁局锁定帧,hoard mode/遥测标签/约束基准语义全变),
  双语义字段=判读断档源;派生口径复用、字段独立,两全。
- **对件进 hoard 目标件集(与 comp 件同权竞争)**:拒——违反主方向优先
  硬边界([23] 底线):对件与 comp 件同轮顶分竞争预算会拖慢主方向;
  二级通道(engine_seed 见即买/pair 凑对)已有独立预算语义([22]④)。
- **备选读法(直通局以 comp 进度为 P1 验收,弃过渡对)**:编排者裁决
  **不采纳**但记档——与 [13]「过渡成型≈过 P1」直接冲突(comp 三件套
  是终局形态不是 P1 形态);全部行为挂 flag 可一键回退至此读法
  (`P1_LOCK_TRANSITION_PAIR=False`)。
- **flag 放 decision_v2 registry**:拒——三个落点中 guard 消费方
  (cw_evolution)不读 registry,registry flag 无法辖 guard 基准;模块
  flag 单点辖全部(消费面经字段空集自动回退),仿 `P1_RECIPE_LOCK`
  先例。

## 验证

- 新单帧锁 14(`test_cw_w166_lock_transition_pair.py`:派生与 scope ∪/
  重派生生命周期/撤销清空/三级对照免辖(comp√对√其他×)/末轮免 fence/
  hoard 主方向逐位不变/方向门放行/guard 保护集扩辖+对照/form_ok 体系对
  判据+三域回归/配方锁局零漂移/未锁回归/A-B 通道回退);
- invest-off 零漂移门:同进程 flag on/off n=20 全局逐位同(无注入→零①
  锁局→字段恒空,0/20 不一致);
- sim A/B(inject on,同进程同池同 seed 配对 seeds 0-99,planes=2;
  两臂池指纹一致,并行批在飞改池致快照指纹漂移[8f4f5674≠W163 锚
  62159448],A 臂逐指标精确复现 W163/W164 headline 0.20/0.15/36,
  批内配对有效):strict_mal **0.20→0.13**(20→13 局;残差拆解=①锁局
  never-2-engine 成型局 8[供给/决策门域,W143 §7.2/7.3 已记档归下一批]
  + finE≥2 被判挤出的良性轮换 3 + 配方锁局基线 2[两臂同有])/
  engines2_by_r6 **0.15→0.19**(回升向 off 口径 0.27)/strict_benign
  0.28→0.35/良性轮换 0.84→0.89 局(围栏未压死)/出口金 36.4→36.0、
  hp 20.3→22.1(观测,不恶化);
- **comp 进度硬边界**([23] 底线):①锁局 comp 核心件获取轮次两臂配对
  (21 局:18 平/B 晚 1/B 早 2,均值差 −0.43 即 B 略早),锁定态翻转
  0 局——副方向不拖慢主方向,flag 默认 True 维持;
- 全量 pytest 2247P/1F:该 1F=`test_ci_smoke_snapshot_batch` 的
  `overflow_gold_zero_buy_streak`(seed20,配方锁局)——**干净隔离
  归因并行批**:stash 本批全部未提交 src 编辑后 HEAD 仍红(其提交
  871a8da1 信息中对「W166 在飞」的归因与本隔离实证相反,记档)。

## 后果

- ①锁局 P1 的账本 decisions 行新增 `transition_pair` 键
  (`serialize_intention` 字段全量序列化自动携带),判读可读副方向态。
- 残差主成分(①锁局 never-2-engine 成型局)不在本批辖域:保护副方向
  治「有引擎被拆」,治不了「引擎凑不齐」——后者归 W143 §7.2/7.3 的
  供给/找牌预算批。
- 边界记档:本批实跑期间并行批(ADR-0366)提交卷走了本批
  `decision_v2/discipline.py` 的编辑(混入其 commit,内容无损);sim
  快照池指纹随其在飞池编辑漂移,跨批数字对照须核指纹。
