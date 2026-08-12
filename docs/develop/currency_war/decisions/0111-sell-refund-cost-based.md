# 0111 sell_refund cost-based(1星=cost / 2星=cost×3−1 / 3星=cost×9−1)

Status: accepted
Date: 2026-08-12

## Context
用户(2026-08-12)提醒「卖出获得的金币没记录,这个挺重要」—— 经济决策(凑息 / 升等级 / 死局卖牌续命)
依赖卖出退金,但旧 `SELL_VALUE={1:1,2:3,3:5}` 是**按 star 的纯占位**(连 1星都没按 cost:1星固定 1,
2-5费卡卖出全错;2/3星固定 3/5 也错)。`simulate` 的 SellBench + `_maybe_sell_for_interest`(凑息)
都用它 → 经济计算失真。

## Decision Drivers
- 卖出退金是经济决策核心(凑息跨 10 倍数 / 升等级凑金 / 死局卖牌),值必须对。
- 1星=cost 多源确认(BWIKI「按其费用获得回收金币」+ 4399 + 用户)→ 至少这条确定,该落地。

## Considered Options

### A. sell_refund(star, cost) = cost × 合成倍数 − 手续费 —— **选定**
- 1星 = cost(🟢 权威;无合成 → 无手续费 → 买卖净 0 = 免费牌池操纵)。
- 2星 = cost×3 − 1、3星 = cost×9 − 1、4星 = cost×27 − 1(合成成本扣 1 手续费)。
- 2星 `−1`:**用户印象「2星少1金币」** + 修 economy_research §2 内部矛盾(L83「2星=cost×3 即免费」
  vs L93「2星以上不免费」→ 改 cost×3−1 = 亏 1 金 = 「不免费」,自洽)。
- 3/4星 `−1`:推测同「合成手续费」逻辑(🟡 待 hook 实机核)。

### B. 纯合成倍数(2星=cost×3,无手续费)
否 —— 和「2星以上不免费」(economy_research §2 自相矛盾)+ 用户「少1」冲突。

### C. 维持 star 固定占位
否 —— 连 1星都没按 cost,经济计算持续失真。

## Decision
选 A。`_SELL_MULT={1:1,2:3,3:9,4:27}`(合成倍数 = 该星卡基础副本数,3合1);`sell_refund` 对 `star≥2`
再 `−1` 手续费。`_bench_char_cost(bc)` 从 char_id 查 CHARACTERS.cost(未知 → 3 兜底);`simulate` SellBench
+ `_maybe_sell_for_interest` 用新签名。economy_research §2/§6/缺口表 同步更新(break-even 推论修正:
1星免费 / 2星以上亏 1)。

## Consequences
- 经济决策按真实退金算(高费卡卖出回更多;2星以上亏 1 手续费 → 凑息/卖牌成本更准)。
- **2/3/4 星精确值待 hook 实机核**(当前 2星=少1 用户确认,3/4星推测)。
- **hook 验证法(用户 2026-08-12 给)**:**拖起来(mouseDown 角色头像,不松手/不到出售区)→ 出售区
  就显示该角色卖出价格** → 无损采集(不真卖就能读值,OCR 出售区显示 → 拖回原位)。采到 2/3星卡时
  校准 sell_refund 的 −1 推测。当前局无 2/3星卡 → hook 被动等。
- 297 测试过(test_sell_refund_cost_based 锁数学 + test_bench_char_cost_unknown 兜底)。
