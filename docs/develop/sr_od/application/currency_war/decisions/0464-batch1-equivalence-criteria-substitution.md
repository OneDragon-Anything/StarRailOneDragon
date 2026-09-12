# ADR-0464:重构批 1 等价性判据替换——回放对拍退场,单帧锁 + 全量绿 + 零漂移锚重跑接管

> **版本界碑(2026-09-04 ADR 存量 review;对象属 decision_v2 栈或旧策略代,现行权威 = strategy-docs/flow/proofs)**:本 ADR 裁决的对象已亡——decision/ 整包(含 decision_v2 各模块)已随 b94e9cfb 删除,现行唯一策略载体 = mandate_v1(kernel 吸收下沉判据)。本件仅存史料价值(记录设计 why/翻案史);**文内一切「后续应做 X/须换成 Y」类前瞻指令一律视为已亡,勿执行**。

- 日期:2026-08-31
- 状态:accepted(W624 对抗 F1 补洞;实施批 = W620 迁移批 1,报告 = `.debug/temp/currency_war/w620_migration_b1/STATUS.md`)
- 谱系:BLUEPRINT v-final.1 §7 批 1 行的等价性判据修正(迁移执行批,非设计改判;蓝图判据「回放对拍+影子行差异」在其自身批 1 动作下失效,属判据自指缺陷)

## Context(为什么)

BLUEPRINT §7 批 1 行把「回放对拍:分歧仅限批语义改进点;影子行差异全在预期区」列为等价性判据。但同批动作「DirectorV2 升正、`director_v2_prep_enabled` 删」使旧环在 `prep_director._run_loop` 内**物理不可达**(无条件 `return _run_prep_loop_v2`),W606 影子钩子随旧环一并不可达——「旧环当权步的同帧影子对照」失去了当权流,判据自指失效(W624 对抗打穿)。

## Decision(逐条)

1. **判据替换**:批 1 等价性证据改由三件承载——
   a. **单帧等价锁**(test_cw_w620_migration_b1::test_single_frame_equivalence_new_pipeline_vs_old_channel):同一 Snapshot 下,新管线 decide 输出与旧通道(直调现役决策核)op 签名逐位一致。批 1 的 `_select` 复用同一 `decide_prep_action` 与同一 obs 通道,等价性由构造保证,该锁钉住「构造性质未被接线破坏」。
   b. **全量回归绿**:sr-od-test 全量 3541 passed(接线后)/ cw 域 3072 passed(效率追加后)。
   c. **零漂移哈希锚重跑**(批 0 资产):test_cw_w614_sim_fidelity 零漂移锚批 1 后重跑绿(seeds 0..6 行为投影 digest 逐位 = 93ca26cc…;20-seed 全量锚 baseline_digest.md 同源)。锚辖域如实声明:sim 路径不穿过 prep_director 分叉,它检测的是新旧管线**共用的决策组件**(candidates/scoring/arbiter/economy)无漂移;分叉本身的等价由 a/b 承载。
2. **回放对拍移批 2**:批 2 老栈退役(§4.1)删除 `decide_prep_action` 时,须先以已归档局回放喂新管线与老决策核做一次全量对拍并出报告(退役前最后一道对拍);W606 影子机制(纯诊断,registry `director_v2_shadow_compare`)保留至批 3 随旧环退役。
3. **「未动 ≠ 重跑」纪律**:凡以「零漂移锚」为判据的批次,验收必须含本批代码状态下的一次实跑绿,不得引用历史绿。

## Considered Options

- ①离线回放对拍本批补做(否):旧环不可达后,「与旧环决策流对照」须临时复活旧环执行流,基础设施成本与批 2 退役对拍重复;批 1 决策语义零改(等价由构造),收益不成比例。
- ②判据替换 ADR + 零漂移锚重跑(选):证据强度可声明(锚辖域如实),成本一次测试运行。
- ③判据静默降级不记录(否):等价性判据是蓝图级承诺,替换必须显式裁决留痕。

## Consequences

- 批 1 验收证据 = 本 ADR + STATUS「等价性验证」节(单帧锁/全量绿/锚重跑三项齐)。
- 批 2 任务书须继承:退役对拍(Decision 2)+ 锚重跑纪律(Decision 3)。
- W606 影子的生命周期终点更新为「批 3 随旧环整段删」(蓝图 §6 原文不变)。
