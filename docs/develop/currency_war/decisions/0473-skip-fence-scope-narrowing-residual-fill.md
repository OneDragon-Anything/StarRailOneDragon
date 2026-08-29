# ADR-0473: skip_fence 互斥辖域收窄——轮级禁运改「通道级+显式保留集」残余补部署(F1 病理修复)+ 检查器扩窗 r2-r9

## 状态

accepted(2026-09-06;围栏互斥辖域收窄实施批)

## 背景

F1 病理:skip_fence 机制(裁决1「显式>围栏,同轮互斥」)的实现把互斥做成了**整轮粒度禁运**——`_explicit_deploy_seen`(本轮有 applied 显式动作)时轮末部署块整体跳过 `select_deployments`。演进事务密集轮(FORM 期换阵/合星风暴)每轮必有 applied CompTransaction ⟹ 连续多轮禁运 ⟹ 换阵撤回/3合1 吞副本造成的板面空槽连续过夜(样本 seed 640247 r5-r7 deployed 缩退 6→3→2、hp 67→63→51),欠载打仗掉血;检查器双盲(轮窗 r2-r4 与 F1 发生位置 r4-r8 系统性错开 + skip 轮 `deploy_lag_units` 恒 0 无数据)使该形态无人报警,四波狩猎合并复现率 1→1→1→3 上行。逐帧账本还原证实:触发谓词零 hp 依赖(与 ADR-0470 濒死止损族无关)、每个 skip 轮都有真 applied 显式动作(非数据错)、无 skip 轮部署回填全部健康(替补逻辑无病,病灶只在 skip 轮辖域)——根 = 互斥**辖域**(粒度)语义过宽,该收窄非补丁。

## 决策

1. **残余补部署(W716 F1 修复设计 §三;命题 P24)**:skip 轮轮末(全部显式动作应用后)对「`select_deployments` up 集 ∖ 显式保留集」执行 bench→空槽补部署:
   - **显式保留集**(消解互斥的本意 = 防同一部署通道双写):① 3合1 素材副本(同名同星全场计数 ≥2,与 cw_plan 卖保护/checks「第二张同名留 bench 合法囤积」同口径);② final 买而不上件(session 持有名单 `v3_hoard.char_targets` 仅 locked/forced 模式——[21] 窗口语义「羁绊组齐才替换上场」辖 final 件;P1 过渡模式(p1_pair/p1_transition/weak/fallback)的囤货集是买侧方向,不构成部署保留,否则修复面被囤货全集吞掉);
   - **零支出零破息约束**:动作面仅 bench→空槽 pop-append,不买/卖/刷/swap——金账恒等式各项不受影响(C=I=0,P24 支配定理:任何 Δp≥0 受益在该域非负,u>0 时严格正);
   - 账本:`skip_fence` 行保留(配对锁 `check_skip_fence_pairing` 语义不破),reason 有补部署时扩展 `explicit_action_v2+residual_fill`;sim 指标新增 `residual_deployed`/`residual_held`;
   - **辖域声明**:skip_fence 互斥只存在于 sim(生产侧无写入点)——本修是 sim 执行层保真度修复:修后 sim 的 P1 板深/血分布才代表生产行为(生产 DeployBench op 每轮独立跑,无此禁运)。
2. **检查器扩窗(`check_deploy_fills_cap`)**:轮窗 r2-r4 → r2-r9(原窗是旧时代的先验,与 F1 发生位置系统性错开,W714 三例全窗外);判据本身零改(增长豁免/可上货口径/连续 2 轮门照旧)。skip 轮 `deploy_lag_units` 补齐(补部署后重放围栏、输入剔除保留集——保留件是「刻意不上」非 lag),消除「skip 轮恒 0」的第二失明面。
3. **命题落档**:`docs/game/currency_war/research/proofs/p24-residual-fill-dominance.md`(P24 支配定理 + P21/P23 辖域不触碰声明)。

## Considered Options

- **维持整轮禁运(裁决1 原义最保守读法)**:否决——互斥防的是通道双写,轮级禁运把保护面扩大到「与显式动作毫无槽位冲突的补部署」,辖域漂移即病理本体。
- **hp 条件豁免(濒死才补部署)**:否决——触发谓词本无 hp,引入 hp 是造第二个仲裁者;且 P24 下补部署在濒死域同样严格不劣(零支出),无豁免理由。
- **保留集取 `v3_hoard.char_targets` 全模态**:否决——P1 过渡模式囤货集是四体系/体系对成员全集,与围栏 up 集几乎重合,取全会使补部署退化回禁运(修复自吞);[21] 的「买而不上」语义只辖 final 件(locked/forced)。
- **3合1 素材副本放行一张(fill_mode 本会上)**:否决——「第二张同名留 bench 是合法囤积」是 checks/卖保护两侧的既定语义,部署侧保留与消费面口径一致;部署一张虽不破坏全场域合并,但策略语义是攒合成不是凑板面。

## 后果

- 正面:F1 形态(跳轮欠载缩退)根治;skip 轮部署可见性补齐(双失明面全消);sim 分布去偏。
- 代价/边界:skip 轮板面多 u 件上阵(粗模型两位数金当量级单例收益,批级期望亚金/局——修复主收益是保真不是期望增益);`check_deploy_fills_cap` 扩窗后历史批次的违规口径变化(跨批对照须同窗)。
- 验证:回归锁 4 条(`sr-od-test/test/sr_od/app/currency_war/test_cw_f1_residual_fill.py`,新锁先红后绿:补部署/保留集/支配形状锁在 no-op 变异下红,扩窗锁在旧窗下红);5 立案种子逐帧重放归零;新鲜 100 种子(640400-640499)F1 复现率 3/100→0 + 出口锚对照不劣;L1/L3。
