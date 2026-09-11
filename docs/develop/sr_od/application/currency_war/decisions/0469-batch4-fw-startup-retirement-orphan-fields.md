# ADR-0469: 批 4 commit-4——framework_startup_v2 开关退役(生产链全断,删码)+ v1-only session 孤儿字段断尾 + 悬置开关验证排期落账

> **版本界碑(2026-09-04 ADR 存量 review;统一迁移批史,与 b94e9cfb 互证)**:本 ADR 裁决的对象已亡——decision/ 整包(含 decision_v2 各模块)已随 b94e9cfb(dd-038)删除,现行唯一策略载体 = mandate_v1(kernel 吸收下沉判据)。本件仅存史料价值(记录设计 why/翻案史);**文内一切「后续应做 X/须换成 Y」类前瞻指令一律视为已亡,勿执行**。

## 状态

accepted(2026-09-03;W653 批 4)

## 背景

`framework_startup_v2_enabled` 是 transition_framework 在 dv 路径的唯一潜在写入者,默认关、无任何置 True 点(全仓 grep=0),生产路径该字段恒空(W455 实测 107/107 出口帧全空 + W646 §0.1 三重实证)。开关生命周期门(W642 任务二)第 4 态裁决:退役删码;备选「转正开臂判据」因无带窗口判据被否。同批清偿 default 栈退役(ADR-0466)后失去写端的 v1-only session 字段。

## 决策

1. **开关 #1 退役(删码清单 = W646 修正③四件,执行有一处偏差如实声明)**:
   - 删 `registry.framework_startup_v2_enabled` 字段块与注释;
   - 删 `DecisionV2Strategy.decide_prep` 过渡框架启动重接线分支块;
   - 删 `cw_transition.pick_framework_startup` / `in_early_phase`(调用点唯一=dv 分支;`_framework_counts`/`pick_framework` 保留,见偏差声明);
   - 删 `cw_sim_checks.check_transition_framework_liveness` 及其注册项(留=无数据面的死检查器);
   - 测试:`test_cw_fw_startup.py` 整文件删(armed 执法/开关 True 臂/零漂移锁随退役);`test_cw_adr0293_calibration.py` 注册表字段表去该行。
   - **偏差声明**:W646 预期 `pick_framework`/`FRAMEWORK_FACTIONS` 同批归零——实证不成立:`FRAMEWORK_FACTIONS` 有活消费面(`cw_transition.transition_score`←`cw_plan` 买侧评分挂账层、`deploy_bench` 围栏),且 `pick_framework`/`_framework_counts` 是 10 个测试文件钉住的纯函数族(零 session/registry 耦合)。本批**保留**(合法复活种子,非「留函数删字段」的半删态——与已删 registry 字段耦合的是 startup 变体,其本体已删);production 写端已全断,生产路径 transition_framework 恒 ''。
2. **孤儿字段断尾(W639 §2.1)**:
   - `StrategySession.pivot_cooldown_until` 删除(唯一写端=default update_target,已随本体退役);消费面:`cw_telemetry.sess_pivot_cooldown` 字段与写行、`shop.py` 回显删除(旧语料 extra.get 缺省 None,schema 兼容);`maybe_pivot` 顶部冷却守卫保留(挂账层,getattr 兜底惰性化),`test_cw_pivot_invariant` 自建桩不受影响。
   - `StrategySession.drought_excluded` 删除(同上唯一写端);`cw_line_switch` L332 的 getattr 兜底读保留(空集=零漂移,记小件)。
3. **悬置开关验证排期落账(禁「维持现状」,全部落 registry 字段注释)**:
   - #2 `line_switch_survival_gate_enabled`:补独立开臂判据(与 two-state 同锚 A/B;判据=濒死带时长/换线拦截率不劣 ∧ 转进死线局归零);可验时点=批 5 sim A/B;
   - #3 `rounds_two_state_enabled` / #4 `c1_directed_spend_enabled` / #5 `recipe_fence_enabled`:补 deadline=批 5 sim A/B 批(#5 第一个跑——形态达标率当期头号缺项);
   - #6 `form_break_sell_blocked_enabled` / #7 `below_floor_spend_gate_enabled`:挂账至实机回归战役(蓝图 §8,前置=批 5 说服包),判读量入武装序判读清单。

## Considered Options

- **#1 转正开臂判据保留休眠**:否决(W642 任务二)——复活条件无带窗口判据=非法悬置;生产链全断,保留=假活性。
- **FRAMEWORK_FACTIONS/pick_framework 一并删**:否决(本批)——活消费面实证(W646 清单漏项)+ 10 文件测试面;留待配方模型退役批(买层接管后 transition_score 面归零时)一并裁决。
- **drought_excluded 连 cw_line_switch 读点同删**:部分否决(承 W639 §2.1)——该读点在 v2 活跃模块,删读点需语义级确认驱逐覆盖;getattr 兜底零漂移,记小件。

## 后果

- 正面:registry 悬置开关 -1;无写端字段族清零;7 悬置开关全部有明确验证批次或实机排期(无「维持现状」态)。
- 代价/边界:框架复活需重新立项(信号累积器+预注册 A/B,ADR-0442 复活条件段);旧遥测语料 sess_pivot_cooldown 列退役(判读脚本列宽变化记档)。
- 验证:ruff 改动文件绿;L1 全量绿;grep `framework_startup_v2_enabled|pick_framework_startup|check_transition_framework_liveness` 生产引用=0。
