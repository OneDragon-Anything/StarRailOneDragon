# ADR-0237 腾席链死循环修复(gold 真值等待上限 + 全保护强制卖)

## Status

accepted(2026-08-22;r364;局47 卡 50 分钟判读驱动)

## Context

局47 P1r6(HP 88/gold 19/lv6/板 5 满/bench 9 满):12:18-13:10 死循环「备战席已满警告 → M-6 门 → 腾席链 b 要求 state_gold_trusted → EnsureShopOpen(执行 ✓)→ 警告仍在 → 重入 M-6」40 次,零出战。根因:**链 b 的前提(state_gold_trusted)在环内不可达**——EnsureShopOpen 成功不保证下一轮决策时 obs 快照已刷新该标志,无进展环。链 c(_weakest_bench_idx 全保护返 None)是潜在第二死锁形态。

## Considered Options

1. EnsureShopOpen 执行层同步返回 fresh state:改执行层接口,面大。
2. **进展保证:等待计数 + 双兜底**(选):gold 真值等待计数(环入口清零);>1 次仍无真值 → 放弃等待直落链 c;链 c 全保护且等待超限 → 强制卖 bench 首个非在场件(保护是优化不是死锁理由)。
3. 满席直接出战(不破满也合法):改动更小但绕过腾席语义,且买牌阶段被跳过后经济断;留作链 c 兜底也失败时的下一道。

## Decision

选 2。session.free_bench_gold_wait 计数;链 b 第 2 次无真值落链 c(日志标注);链 c 全保护 + 超限强制卖非在场件。r290 锁测试随结构演进更新断言(语义不变:直读仅兜底)。

## Consequences

- 死循环环从「无限」变「≤2 次 + 一次卖」;卖散件损失 << 卡 50 分钟(HP 88 完全能打)。
- 局47 部分成果有效:r361 部署修复 ✓(r4 激活档 2,局46 整局 0),四连胜开局(82→88)。
