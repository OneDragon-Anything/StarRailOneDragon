# 0111 sell_refund cost-based(1星=cost / 2星=cost×3−1 / 3星=cost×9−1)

> ⚠️ **手续费模型被 [ADR-0121](0121-sell-refund-fee-cost-dependent.md) 修正**(2026-08-13):「star≥2 一刀切 −1」错 —— 1费各星全额退(live 实测 2★1费=+3);−1 仅 star≥2 且 cost≥2。本 ADR 的 1★=cost 权威结论与「click 详情面板读售价」验证法仍有效;Consequences 中「star 售价矛盾待客观核」已由 0121 解决。

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
- **1星=cost 实机验证通过**(2026-08-12):丹恒·饮月(1星2费)click 头像 → 详情面板显示「+2 出售」= cost。
  → sell_refund(1星, cost) 落地确认。
- **2/3/4 星精确值待真样本**(当前 2星=cost×3−1 用户确认「少1」,3/4星推测同 −1 逻辑)。
- **售价验证法(用户 2026-08-12 给,验通)**:**click 角色头像 → 详情面板显示「+N 出售」**(N=卖出价,
  无损,不用 drag/不真卖)。替原「mouseDown 拖起看出售区」(MCP drag 没法拖起不松手)。
- ⚠️ **star 售价矛盾待客观核(2026-08-12,非武断 star 错)**:丹恒 read_star/simulate 报 2星,click 详情 pi 读
  「+2」(似1星cost)。但 **pi 数金星/读数字都不稳**(17:50 报全1星 / 18:00 报三个2星 / +2 自相矛盾),不凭 pi
  判 star 错。**假设 star 识别对**(用户:read_star 已验证 commit 672aa838;3合1 是全场 deployed+bench+买,simulate
  _merge 只看 bench 有局限 → read_star 实机更准)。售价待客观 OCR 核(click 详情面板数字,非 VLM)。
- 297 测试过(test_sell_refund_cost_based 锁数学 + test_bench_char_cost_unknown 兜底)。
