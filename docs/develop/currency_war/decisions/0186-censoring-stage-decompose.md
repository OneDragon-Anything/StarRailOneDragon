# ADR-0186: 删失感知统计层 v0 落地(redesign 48 号处置:stage 分解 + J0 首份报告)

> ## ⚠️ 更正(2026-08-17 晚,M70 假 win 定位后)
> 本 ADR 原 J0 报告的 plane 数据含 **M70 型 OCR 污染**(read_phase_round 单数字 fallback
> 把难度/等级泄漏当 plane;主开发同日定位并修复读取侧)。值域守卫(plane∈1-3)后重跑:
> - P(reach p2) 21.1%→**16.7%**;P(reach p3) 5.3%→**0%**;P(win) 5.3%→**0%**;
> - **「P(win|reach p3)=100%(活到 p3 即赢)」撤回**——无任何可证实的 p3 到达(原 5.3%
>   正是污染行);「瓶颈在早期存活」结论保留且更强(可证实最深仅 p2);
> - 幸存者虚高 finding(命运圣杯红A)同样撤回(其 p3 到达来自污染行)。
> 治本:`outcomes_to_runs` 值域守卫已固化进模块摄取口(测试覆盖 M70 型/混合型污染)。
> 保留原文如下——错误本身是数据质量审计的证据。

## Status

Accepted(2026-08-17,策略优化会话;IPCW 与删失标注为 v1;难度阶梯观测窗需实机)

## Context

48 号诊断:bot 真局流右删失(基线 82% 未存活)——「每局 outcome 是完整反馈」是全系统
47 轮押注的静默假设。P(win) 混合体里 early 存活型与 late 强度型不可分,maybe_pivot 的
比较量纲错;幸存者条件虚高/死亡线后期潜力被掩埋是偏置方向(高估幸存线、低估死亡线)。

## Decision Drivers

- J0 判据:既有语料 stage 分解重估 vs 现行混合标量,≥3 条实质偏差或带 CI 报告
- 零新局纯重分析(outcomes.jsonl 重建局记录)

## Considered Options

1. **KM 到达曲线 + stage 分解先行(选)**:P(win)=P(r2)×P(r3|r2)×P(win|r3),Wilson CI;
2. 全套 IPCW——需 37 式倾向权重,v1 接;
3. 维持混合标量——删失偏置继续无意识污染线判决。

## Decision

选 1:`cw_censoring.py` v0——stage_decompose(乘积自洽,零分母显式 None)/
kaplan_meier_reach/compare_vs_scalar(J0 两类偏差检出:late_potential_masked =
scalar 0 掩埋 p3 到达;survivor_condition_inflated = scalar 靠低到达率稀疏通关)。

**J0 首份真实报告(19 局/7 线,outcomes.jsonl 重建)**:

- 整体:P(reach p2)=21.1%、P(reach p3)=5.3%、P(win)=5.3%,**P(win|reach p3)=100%** ——
  活到 p3 即赢,全输在 p2 前。**核心事实:当前瓶颈是早期存活,不是后期强度**;
  混合标量把「early 存活问题」记在「线强度」上,正是 48 号预言的量纲错实例;
- 检出 survivor_condition_inflated ×1(命运圣杯红A:scalar 0.25,p(reach p2) 仅 25%);
- 万敌单C(P[r2]=100%,P[r3]=0%)vs 列车同行(P[r2]=14%):early/late 型线首次可分,
  maybe_pivot 的正确比较量纲就位;
- 诚实边界:19 局小样本,CI 宽;结论方向性成立、数值待 telemetry 扩样。

## Consequences

- 48 号机制一第 1 件落地;IPCW(37 池化权重)与 40 号「删失区显式未验证」标注为 v1;
- 难度阶梯观测工具(机制二)需实机窗口,挂 29 队列;
- 对拍锚留档:18 号解析 P(reach) vs 本层经验 KM(不一致=模型函数形式错,喂 40 号);
- 48 号处置完成(v0),提案文件删档;测试 +5。
