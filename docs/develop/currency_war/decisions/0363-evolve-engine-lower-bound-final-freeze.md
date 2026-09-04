# 0363 — evolve 换档的引擎下界守卫与末轮演进冻结(S1 型修法)

- 日期: 2026-08-28
- 状态: accepted (采纳)
- 关联: ADR-0360(evolve 换血保护四件,本批补其「在场」盲区)、ADR-0359(final_fence 末轮围栏,语义对齐)、ADR-0357(P1 配方锁)

## 背景与问题

W159 六臂逐局归因(同池 bab146c68c5df11a seeds 0-99):S1 型
「成型后引擎丢失」(engines 曾 ≥2,终局 <2)从 4 局(W150/W154)翻倍到
10-11 局(W155),全部 37/37 S1 局通道唯一 = `evolve_tx → to_bench`:

1. W155 件2(同名去重)治好 W143 rejected 死循环后,末轮(r8-9)单体系
   加深事务**首次真正应用**;
2. `_is_new_line` 按提案单体系划档,把**另一个已达标引擎体系**的在场件
   整批划 old_line 下场进 bench(W159 §2:seed63 列车同行加深把 DOT 全家
   下场;seed46/74 DOT2 演进把希儿本体下场);
3. ADR-0360 件3 保留序只保「不卖」不保「在场」(下场 22 件终局 77% 仍在
   bench)——末轮无剩余轮回场窗,良性轮换退化为**永久丢失**。

这是保护没罩住的盲区,不是件2 的副作用(基线 4 局同型早在 W150 就存在,
件2 揭开了被 reject 循环意外挡住的旧有换档行为)。strict_mal 存量 0.31
的 1/3(S1 型)由此构成(W158 §4)。

## 决策(两件独立,A/B 通道独立)

1. **引擎下界守卫**(`registry.evolve_engine_guard_enabled`,默认开;
   `cw_evolution.execute_replacement` 生成侧):事务净效果使过渡引擎数
   (`cw_sim._engines_count` 口径,W158 strict 度量同源)从 ≥2 跌破 2 时,
   **被拆引擎体系的 deployed 贡献件获得新线同级留场资格**(不划 old_line
   下场;留场件挤占 room → 新上场数收紧)——语义「换血可以,拆引擎不行」。
   触发面精确到 ≥2→<2:engines<2 局(成型问题非丢失问题)与 ≥2→≥2 的
   良性换血均不辖。护的是**在场引擎贡献**([31] top4 是胜率保证),
   不是库存(库存保护 = ADR-0360 件3,两者互补)。
2. **末轮演进冻结**(`registry.evolve_final_freeze_enabled`,默认开;
   `cw_evolution.evolution_step._try`):位面末窗(剩 ≤1 轮,
   round_num ≥ NODES_PER_PLANE-1,即 r8-9)演进换档(undeploy/sell
   非空的拆板事务)冻结不发射——纯加深(deploy-only)与填位照旧。
   与 ADR-0359 final_fence(买侧末轮围栏)语义对齐:末轮换档天然无
   回场窗(W159 §1:丢失 90% 落 r8-9),「加深收益 < 引擎丢失风险」
   在该窗口系统性为真。

## Considered Options

- **修保留序让引擎件「留场」而非「留 bench」**(扩展 ADR-0360 件3):
  拒——保留序作用于 old_line 的**去向排序**(bench vs 卖),改它到
  「不下场」要动 old_line 划档本身,等价于本决策件1,且保留序语义会被
  拉扯成两个职责;直接在划档处给「新线同级资格」语义更干净。
- **末轮提案整体冻结(含加深)**:拒——加深(deploy-only)不拆任何
  体系,末轮仍可能补齐目标体系件([21] 窗口语义),冻加深是过紧。
- **提案降分(penalty 式)处理 2→<2 事务**:拒——降分让位在同轮最优
  竞争里生效,但末轮常常没有竞争提案(唯一机会 = 唯一被选项),降分
  对无竞争单选项无效;该场景是硬下界语义(引擎数),不是优先级语义。
- **只做件1 不做件2**:件1 挡住「引擎体系被整批划走」,但 r8-9 的
  拆板事务即使不跌破 2 也可能拆掉填充/半档板面终局定型;件2 是窗口
  语义(无回场窗不做不可逆动作),与件1 正交——实测两者叠加主指标
  降得更稳(见验证)。

## 验证

- 新单帧锁 6(见 `sr-od-test/test/sr_od/app/currency_war/
  test_cw_evolution.py` §6):守卫帧留场/关臂复现 S1 通道/单引擎局
  不辖(开关联事务逐位同)/定向性(散件照旧下场)/末轮冻结×拆板与
  纯加深两态/关臂解冻;既有 14 锁全绿。
- sim A/B(同树同池 snapshot,seeds 0-99,ctrl=两件关 / w160=两件开):
  数字与池指纹见 W160 报告(`.debug/temp/currency_war/cw_dev/deep_read/
  W160_S1_报告.md`;工作树含 W157 在飞改动,池指纹 v8 与 bab146c6
  跨日不可比,两臂同树内对照为准)。

## 影响

- cw_evolution(守卫 helper `_engine_systems_formed`/
  `_lost_engine_systems`/`_contributes_engine_system` + execute_replacement
  划档重组)、decision_v2/registry(两开关)、decision_v2/strategy
  (registry 注入)。
- strategy/02_comp.md §10 与 README 演进行同步语义指针。
