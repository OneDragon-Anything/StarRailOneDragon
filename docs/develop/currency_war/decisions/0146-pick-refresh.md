# ADR-0146: 选卡刷新接入(PickEvent.refresh)——缺口 1 闭环

## Status

Accepted(2026-08-15;按钮坐标 click 实锤待 M21 首触)

## Context

- 用户指出缺口(2026-08-15):游戏规则 = 投资策略 3 选 1 可刷新(界面「刷新次数N」)/投资环境开局可刷 1 次(「剩余次数:N」)/补给可刷 1 次;bot 原永远从首次三张硬选。
- 采集实证(当日):strategy 屏计数文字 (974,854)×3 稳定;env 屏 (776,983);刷新按钮为图标(OCR 无文字),VLM grounding 候选 strategy (1367,832)-(1426,875) / env (649,957)-(699,1007)。
- 前车之鉴(M20 武装箱弹窗):VLM 定位 ≠ 可点,交互坐标必须 click 实锤 —— 但本流程**失败安全**(见 Decision 3),可以先接线后实锤。

## Decision Drivers

1. 刷新免费(次数内)→ 烂手牌换新期望恒正,不刷纯亏。
2. 决策与执行分离:策略层只建议(PickEvent.refresh),handler 按次数真值决定 —— 策略层不碰 UI。
3. 失败安全:坐标无效/点击无变化 → 重读仍得原三张 → 照常选当前最优 = 与现状行为完全一致,不硬阻塞(区别于武装箱弹窗的硬阻塞教训)。

## Considered Options

- A. 建议位 + handler 单次尝试 ✅:decide_event 无状态,重调用即重选;handler 硬编码单次尝试天然防循环。
- B. decide_event 加 refresh_used 参数:要动 decide_invest 抽象接口(8 个策略钩子),为防一个 handler 侧自控的循环不值。
- C. 等坐标实锤后再接:失败安全设计下无必要;M21 首触自然实锤。

## Decision

1. `PickEvent.refresh: bool = False`(纯建议位);decide_event:三张最优 < `EVENT_REFRESH_SCORE_FLOOR`(50,≈评估分中位;白名单 78+/comp-hit 65+ 天然不触发)→ refresh=True,reason 加 "|suggest-refresh"。
2. 两屏建「按钮-刷新」area(纯坐标无 text;VLM 候选,M21 首触实锤后如有偏差即修)。
3. 两 handler 刷新流:pick.refresh 且 OCR 次数 > 0 → 点按钮 → 1.5s → 重读 options;卡名变化 = 刷新成功 → 重 decide(一次性);无变化 = 点空 → 照常选(现状行为)。钩子采集的次数存 `self._refresh_count` 供刷新流读(钩子与刷新流共生,实锤后钩子删、次数读取留)。

## 后续

- M21 首触实锤按钮坐标(成功判据:日志「刷新成功重读」或次数递减);偏差则改 area 坐标。
- 补给屏刷新(decide_supply 已有 refresh 参数)走同模式,待补给屏现场核其按钮。
- 阈值 50 归 tuning(评审建议 5 同批)。
