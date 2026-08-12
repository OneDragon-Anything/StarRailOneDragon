# 0109 牌池副本数定案(1/2费=27 / 3/4/5费=9;弃 V4.2 银狼档)

Status: accepted
Date: 2026-08-12

## Context
`cw_shop_odds.POOL_COPIES_PER_CARD`(每种牌副本数 a,驱动 D牌蒙特卡洛 `_refresh_dist`/`expected_refreshes`
+ 未来 #6 牌池 acq)此前是 **placeholder 全 9**(仅 5费 NGA tid=45557485 实锤;其他费用「难实机」未核)。
doc 记两版冲突:V3.7 必修二 27/27/9/9/9 vs V4.2 银狼档 30/25/18/10/9,标「待实机核」。
#6 牌池 acq 被此数据不确定性阻塞(用未核实副本数进策略 = 假信号地基)。

## Decision Drivers
- 3合1 升星机制 → 副本数必为 3 的倍数(9 张合 1 三星;27 张合满 = 可升 4 星)。
- placeholder 9 让 1/2费 D牌蒙特卡洛算错(over-deplete:把 27 当 9 → 期望刷新次数虚高)。

## Considered Options

### A. 27/27/9/9/9(V3.7 必修二;3 的倍数)—— **选定**
1/2费=27(可升 **4 星**:27 = 3 个 3 星 = 9×3)、3/4/5费=9(最高 3 星)。均 3 的倍数,3合1 决定。
5费=9 与 NGA tid=45557485 实锤吻合。用户确认(2026-08-12):「肯定是 3 的倍数,优先信 27/9」+「27 张是因为有 4 星」。

### B. 30/25/18/10/9(V4.2 银狼档)—— **否决**
含 **非 3 倍数**(25/10),与 3合1 升星机制矛盾 → 不可信。来源是搜索摘要(见 memory
`websearch-verify-original-source`:该摘要曾编造「副本数 30/25/18/10/9」,原文只「每种相同」无数字)。
银狼档本身非权威攻略。弃用,doc 删此冲突信息。

### C. 维持 placeholder 9 全待核
否:#6 acq + D牌蒙特卡洛 1/2费 持续算错;数据已有可靠源(V3.7 必修二 + 机制推导),不该再搁置。

## Decision
选 A。`POOL_COPIES_PER_CARD = {1:27, 2:27, 3:9, 4:9, 5:9}`。doc(currency_war.md)定 27/9 为权威,
删 V4.2 冲突信息;「牌库有限(买掉即减)」从「待核」升为「确定机制」(用户确认)。

## Consequences
- D牌蒙特卡洛(`_refresh_dist`/`expected_refreshes`)对 1/2费 现用真实 27(非 placeholder 9)→ 期望刷新次数
  算对(1/2费 池大,deplete 慢,D牌期望更低 = 更易成型,符合低费核心「不赌」设计)。
- **解锁 #6 牌池 acq**:数据齐(a=27/9 + v + REFRESH_PROB),可接 held-card depletion(j)。
  #6 剩余:held-count 接线(session.tracked → select_comp)+ acq 输出尺度校准(1/v 修正会塌缩 acq 范围,
  需重新校准 select_comp 乘子)+ A/B 验证。
- 测试安全:shop_odds 测试直接传 a 参数(测数学性质,非真实值),`expected_refreshes_for_card(cost=3)` 的
  3费=9 未变;296 测试过。
