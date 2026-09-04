# ADR-0124 买牌 tempo 例外:未成型 commit 放行板直接增强散牌

> ⚠️ **语义被 [ADR-0127](0127-strategy-review-h1-h4.md) H2 收敛**(2026-08-15):阵营计数只用 board(deployed 真值;旧含 bench = 买进单张反向维持例外开启,spread 吸引子);删 cost≥3 无阵营分支(OCR 失败 cost 默认 3 会自动放行);补 fp 守卫(成型即关)。本文旧语义描述不再是实现,以 0127 + 代码为准。

- 日期:2026-08-15
- 状态:已接受(实现于 cw_decisions._best_improving_action)

## 背景

live 7 局 A8 telemetry(M1-M7 + alloc 分析)实锤:commitment prefilter(T#97)与 saving gate 叠加后位面 1 每轮仅买 ~1 单位、攒金 7→62,板饿死(每场 -10~-36 HP,1-9 boss 进场仅 13 HP)。COMMIT_ROUND=2 轮数兜底使第 2 轮起(买 1 张 target 后)即 commit → 严格拒散牌;shop 没刷 target 时空过攒金。成绩轨迹:攒金版 价值41(M1/M2)vs 升级版 25(M5)vs 14(M7)—— XP 与单位投入失衡持续加深。

## 决策驱动

1. 板饿死代价(每场掉 HP,HP 不可再生)> spread 代价(散卡仍可 deploy 保战力)
2. 人类打法:前期买强散卡保 tempo,成型后纯堆 target —— bot commit 过早/过死
3. 「一切评分 comp 相关」不等于「非 target 不买」:板上 ≥2 同阵营散卡就是在深化成型羁绊

## 考虑过的选项

- A. 提高 COMMIT_ROUND(2→4):治标,commit 后仍会饿死;且削弱 anti-oscillation
- B. 删 prefilter:回归「买一切」spread(plane1-9 实采 7 阵营零成型的老病)
- C. tempo 例外(选定):未成型(form_progress<COMMIT_FRAC)时放行「板直接增强」散牌(板上 ≥2 同阵营计数 或 cost≥3 强卡,且板不满员);成型后保持严格(原 T#97 语义不变)
- D. 强制最低买牌量:硬性轮指标,与 eval 框架冲突,放弃

## 决策

选 C,同时落两处:① prefilter 的 tempo 例外(未成型 commit + 板增强散牌放行);② saving gate 同例外(板直接增强 ≠ 泄金)。成型后(form_progress≥0.4)行为与旧版完全一致 —— 已成型 comp 不受影响,无回归风险。

## 后果

- 正:位面 1 板密度上升(预期每轮 2-4 买),HP 曲线平缓;comp 未成型期战力有保底
- 负:散卡占 bench/板位,可能推迟成型(接受 —— 成型前的生存优先);tracked by telemetry
- 验证:live 对局板价值/HP 曲线 vs M5-M7 基线;test_cw_decisions 回归全绿(114 passed)
