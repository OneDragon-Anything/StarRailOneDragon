# ADR-0256: SellBench.income 生产补采(sim↔生产账本卖出回金对齐,r381)

- **Status**: accepted(部分落地——字段+2/9 创建点;补标余 7 处挂 sim 账本批)
- **Date**: 2026-08-23

## Context

sim 账本的卖出回金按 cost 1:1 计(cw_sim 侧合成键),生产的真值口径是
`sell_refund(star, cost)`(2★×3+手续费)——两侧本就不同源,导致判读
「卖牌回金」时 sim 与生产账本无法对拍(交接清单⑤)。补采思路:在动作
创建时把**预期回金**记进 SellBench 动作本身(记录字段,非指令参数;
None=未标,兼容旧调用),消费端(sim 账本/遥测判读)按 sell_refund 口径
对齐。注意仓内有两个 SellBench 类(cw_state 决策动作 vs prep_actions
执行类),本字段落在 **cw_state 类**(决策侧创建点即生产真值源)。

## Considered Options

1. **动作携带 income 字段(创建时标注)**——创建点即策略已知 refund 的
   地方,标注零额外读屏;未标(None)显式可辨。
2. 执行侧回填(执行完按实际回金写账本)——需要执行结果观察,链路长且
   执行侧 SellBench 是另一个类,两侧 schema 对齐成本高。
3. 只改 sim 侧统一按 sell_refund 算——不动生产,但 sim 与生产「实际
   收到多少金」仍无生产侧真值,对拍依旧缺一头。

## Decision

选 1:`cw_state.SellBench` 增 `income: int | None = None`(sell_refund
口径,创建时预期回金;None=未标)。

## Consequences

- **已落地(以代码为准,commit message 有虚报)**:字段定义(cw_state,
  随 17eb1901 批落地)+ 标注 2 处(line_strategy `_sell_off_target`
  (L980,`_refund_of` helper)/`_sell_for_interest`(L1023,refund 直带);
  commit 9bb56950)。
- **缺口 7 处未标注**(9bb56950 message 声称「四个生产创建点全部标注+
  default 两处 _sell_income_of」——`_sell_income_of` 全仓不存在,
  default_strategy diff 仅注释变更;**以代码为准**):cw_plan L523/L620/
  L1165、default_strategy L782/L789(腾席链 c)、line_strategy L915(swap)/
  L933(sell4gold)。消费端须按 None=未标处理,勿当回金 0。
- 教训:字段与标注分落两个 commit 且 message 虚报覆盖面——跨 commit
  的 feature 落地以代码 grep 为准,不信单一 message(本 ADR 由补写时
  对拍发现并如实记录)。
