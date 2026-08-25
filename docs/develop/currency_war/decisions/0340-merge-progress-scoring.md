# ADR-0340:断买修复评分层最小件(3合1 中间进度显影 + 溢出金断买检查器)

- 日期:2026-08-26
- 状态:accepted(实跑演进,commit 即生效)
- 关联:W93_报告.md(诊断根因)、ADR-0339(W88 core_star)、ADR-0300/0303/0304(r410 守卫与豁免开关)、ADR-0332(评分活性同族)、口述 [13]/[17]/[22]③

## 背景(Context)

第七局(run_20260825_130151)r6-r9 溢出金断买:金 59→90 溢出趴三轮零买,
违反 [17](>50 每一分都该花,三次强调的最高权威)。W93 单帧复放诊断坐实:

- **根因①(评分层,主)**:目标件第 2 份(1★)买入全维度零 delta——`targets`
  集合隶属计数已封顶、`eng_frac` 只辖三过渡体系、`core_star` 只看 star≥2、
  `rung` 按整数档——仲裁层「非正分」拒。r9 实测:买吉尔伽美什/阿格莱雅前后
  `score_state` 完全相等。
- **根因②(生成层)**:r410 守卫(`copy_swap_useless`,ADR-0300)把 deployed
  目标件的第 2 份连候选都不生成(豁免开关 `copy_swap_target_exempt` 默认 OFF,
  ADR-0303/0304 裁决);core 豁免面(t_fac/t_core 命中)不受辖,W93 r9 候选
  能生成即走该面。
- W88/W85 嫌疑排除(A/B 旧树对拍逐位一致);利息地板没拦(拒因全是「非正分」)。

## 决策(Decision)

只做**评分层最小件 + 检查网回灌**;生成层 r410 守卫**不动**(影响面大,
单独批——见 Consequences 设计建议):

1. **评分层份数显影**:新增 score_state 分项 `merge_progress` = 目标集内、
   尚无 star≥2 持有的名字的「第 2 份」份数进度(每名只计一次;第 3 份 merge
   成 2★ 后由 core_star 承接,star≥2 持有则本项对该名让位——两侧不双计);
   域权重 ADR-0295 同式(deployed 副本 ×1.0,纯 bench ×bench_form_weight)。
   常量 `registry.merge_progress_unit`(初值 3.0,= core_star_unit 同量级:
   同一 2★ 目的地的期权;未网格标定)。
2. **检查器回灌**:「P1 溢出金断买」进 `_BATCH_CHECKS`
   (`overflow_gold_zero_buy_streak`):P1 内连续 ≥2 轮金>50 且零 BuyCard
   且零 LevelUp(升级滴漏不算冻结)→ 违规。W93 病灶形态(3 连)必报。

## Considered Options

| 选项 | 评估 |
|---|---|
| A. 评分层份数显影(本 ADR) | 治根因①:第 2 份有期权分即可过「非正分」门;与 core_star(W88)构成 star≥2 门前后两段互补;金流侧风险=买入多花金,由利息地板/息崖平滑(ADR-0332)既有辖域兜底 |
| B. targets 封顶语义重估(0.8 cap 13 目标件过早饱和) | W93 修法方向提及,但改 cap 牵动持有进度全域语义(ADR-0295/0301 标定链),非最小件——留待网格标定批 |
| C. 生成层豁免开关翻转(copy_swap_target_exempt=True) | 掩盖评分层盲区:候选生成了仍评 0 分照样被拒;且翻转影响全目标件生成面(ADR-0303/0304 裁决默认关有据)——单独批评估 |
| D. 守卫条件细化(「同名同星 ≥3 或确实无效」才拒) | 同 C,生成层影响面大;且 core 豁免面已让 r9 形态(core 件)可生成,评分层修后即通 |

## 验证(Verification)

- 单帧锁 8 条(`test_cw_w96_merge_progress.py`):项值 5 + r9 病灶帧
  (deployed 核心 1★ + 店内同名 → 候选生成且正分,delta 含 merge_progress)
  + r7 生成层不变式(r410 守卫行为不变)+ 检查器 4(W93 病灶必报/单轮不报/
  花金断连/P2 不辖)+ 接线锁。
- sim A/B 配对 n=100(池指纹 46066bbe):出口金溢出率/买入频次/断买 streak
  局数/hp_ge_60,配对差 + 95% CI——数字见 deep_read/W96_报告.md(锚点→实测
  →残留格式)。
- 全量 `uv run pytest sr-od-test/`(含 registry hash 锁同步更新)。

## Consequences

- 正:目标件第 2 份买入有了中间进度显影,「金充裕却零买」盲区消除;检查器
  使同类断买形态在 sim 批 checks_violations 涌现。
- 负/风险:merge_progress_unit=3.0 未网格标定(与 core_star 同量级的初值),
  可能过量买副本 → 金流下移;若 sim 出现买入挤占升级/息线,降 unit 重标定。
- **生成层豁免开关重估(只写设计建议,不动 r410 守卫)**:
  1. 现状:守卫拦「deployed 非核心目标件第 2 份」的候选生成;core 豁免面
     (target_comp core_chars/factions 命中)已放行核心件与阵营件。
  2. 评分层本批修复后,r410 拦截件的买入即使生成也会因 merge_progress
     (若∈目标集)评正分——即守卫从「双保险之一」退化为「纯生成层闸」。
  3. 建议:后续单独批把 `copy_swap_useless` 的判据从「target 阵营/core 豁免」
     扩为「∈hoard 目标集即豁免」(与评分层目标集同源,`_target_names`),
     或按 W93 原案「真持有 ≥3 或换卡确实无效才拒」;需配 A/B(生成面变化
     波及 bench 拥挤与 r410 语义锁)与 ADR-0300/0303/0304 的语义链更新。
     本批不动。
