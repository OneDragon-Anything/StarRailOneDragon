# 0353 form_ok 兜底门结构判据(兜底局相位切换看阵容完成度)

- 日期:2026-08-26
- 状态:accepted(直接落地)
- 关联:0346(相位影子/兜底门引入)、0347(切授权+轮数下限)、W127 global_accumulators 标注、
  transition_combos.md(四体系两两组合=过渡成型)、user_playstyle(判读原则 2026-08-26
  「任何位面看阵容完成度」)

## 背景

意向**未锁定**的兜底局,form_ok(相位切换谓词 FORM→HOARD/SPEND)走
`form_score ≥ phase_form_score_gate(0.5) ∧ r≥5` 的连续量降级门。两证该门过松:

- **W118 sim(A 臂 §5)**:兜底局首真直方图 r2=10/r3=4——单过渡体系 score 恰 0.5 过门,
  ②a(ADR-0347)加 r≥5 压灭早期,但门本体未动;
- **实机 run15(run_20260825_225052)**:意向未锁(locked_line 恒空),r4 起
  form_score=0.65(仙舟3 **单体系** + 配方档小数 rung_frac 撑分,deployed 5 人 8 阵营
  各 1 档的全散板)→ r6 过轮数下限即转真,HOARD→SPEND 金 49→92 而 r6-r9 板面几乎不动
  ——「凑够羁绊档过门」而非「板面朝一条线收敛」。

用户判读原则(2026-08-26):**任何位面看阵容完成度**——兜底门语义应为「板面真正朝某条线
收敛」,不是「分数可达」。

## 决策

1. **兜底门改结构判据**:`form_ok(未锁) := r ≥ phase_fallback_min_round ∧
   fallback_engines_count(state) ≥ phase_fallback_min_engines(=2)`。有效体系数 =
   `_engines_count`(四过渡体系单一源,仙舟3/列车2/DOT2/希儿系,**deployed 口径**)
   + hp_charge_stack 型全局累积角色豁免(上场 2★ 计 1)。判据基准 = transition_combos
   定稿「四体系两两组合=过渡成型,单体系点火≠成型」(三选二 140/328 帖)。
2. **万敌豁免消费 W127 字段**:豁免集 = `cw_comps.hp_charge_stack_chars()`(COMP_LIBRARY
   `global_accumulators` 派生,当前={万敌}:受击充能+生命上限永久提高=场上事件驱动的
   全局叠层,上场即真实累积战力);门槛 star≥2 与 form_ok 族「核心 2★」同向保守。
   `cost_escalation` 型(银狼)不豁免——累积由购买驱动,字段 docstring 明示不适用
   部署类例外。
3. **删 `phase_form_score_gate`**;`form_score` 降级**纯遥测观测**(sim 账本/生产
   decisions.jsonl 字段保留,不进任何判据——后续若再标定有数据可依)。
4. **三件套路径(意向锁定局)语义零改动**;default 栈冻结零改动。

## Considered Options

- **① 分数∧主线集中度**(最高体系占分率)——否决:需新造指标无文档锚,仍是代理量,
  散板可被边缘值绕过。
- **③ 分数门槛抬到三件套典型分**——否决:仍被 recipe_tier 小数游戏化(run15 0.65 已
  >0.5),与②相比是间接代理;②直接表达「板面收敛到 ≥2 真实伤害体系」。
- 万敌豁免不设星级门槛——否决:1★ 单卡叠层虽真但板面薄,保守与谓词族「核心 2★」
  同向;豁免过宽会重开弱板转真窗。

## 后果

- 兜底局单体系+配方档板(run15 型)form_ok 回 False → 相位 FORM → 地板 form_floor(20)
  → 金不再滞留攒息而转向板面强化;HOARD/SPEND 轮占比下降(弱板误转真减少)。
- formed_stop 在未锁局的触发面同步收严(与门咬合方向一致);w107 存在性锁改「首个
  **咬合**局」扫描(首个触发局可为仅标志局)。
- `phase_fallback_min_round` 保留(合取):两体系早凑齐时 r5 前人口/星级仍薄,保守留
  FORM(地板 20 允许买,不亏)。
- 验证:单帧锁(run15 r4/r6 反例帧→FORM、两体系帧→True、万敌豁免帧)+ sim seeds
  0-99 同池 A/B(见 W132 报告)。
