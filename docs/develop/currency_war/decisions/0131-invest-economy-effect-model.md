# 0131 投资策略经济效果建模(EconomyEffect;替 REFRESH_DISCOUNT_STRATEGIES 错名单)

## Status

accepted(2026-08-15;用户提出「投资策略/环境效果要直接转经济模型」)

## Context

投资策略效果此前全是**原文描述字符串**,经济模型零消费;唯一消费点 REFRESH_DISCOUNT_STRATEGIES 名单经与米游社 315 全量 doc 对拍 —— **T0 十二条里 8 条描述错**:高效决策非「减半」而是 9999 次免费刷新限时 45 秒;采购专员非「返现」而是每 5/7 次刷新变 5 张同费卡;价值投资·彩非「生息」而是送 2星角色每节点滚雪球;基本保障非「经济」而是战力(带装备角色 +20% 生命 +16% 伤害)。

## Decision Drivers

- 用户(2026-08-15):「部分投资策略/环境可以直接转换成经济模型,例如给多少金币、商店刷新多少次之后变成 1 金币」。
- 效果数值化后刷新期望(蒙特卡洛)、利息档、经验单价才有真值 —— 否则持有强经济策略时策略层系统性错估。

## Considered Options

- 效果字符串运行时解析(正则抽数值)—— 否:脆,注册表建库时一次性结构化更稳。
- 全量 315 条建模 vs T0 + 明确经济类先行 —— 后者(高频/白名单内先建,长尾随 live 持有补)。
- interest_cap_override 多策略并持取 max vs min —— max(游戏取宽值,保守建模与人对齐)。

## Decision

1. cw_investments:EconomyEffect dataclass(instant_gold/gold_per_node/free_refresh_per_node/free_refresh_burst/refresh_surprise_every/gold_per_three_5cost/interest_cap_override/xp_per_refresh/xp_per_node/xp_buy_cost_discount/win_reward_mult);T0 效果原文全修正对齐 doc + 填经济值;补明确经济类策略(本金充裕/开源节流/利息上调/买断制/淘金客/伟大征服/商业间谍);aggregate_economy 聚合(求和字段求和,cap/mult 取 max)。
2. 消费点(cw_decisions):_refresh_cost(免费额度内 0 金,RefreshShop action + 蒙特卡洛期望 + gold 门槛全用真实成本);_refresh_cap 效果驱动替名单;economy_score 利息档上限覆写 + 每节点金计收入 + 连胜倍率;xp_click_cost 买经验折扣。
3. 删 REFRESH_DISCOUNT_STRATEGIES(语义全错);测试改效果断言。

未做(live 持有后补):高效决策 45 秒爆发窗的时机编排(选完立刻狂刷,执行层待办);淘金客 xp_per_refresh 进 MC 期望;gold_per_three_5cost(买 5 费返金)进买入估值;投资环境(ENV)侧经济效果(概念股刷新率加权 _sample_shop 待接)。

验证:测试 5 项新增(88 passed 决策+投资);CW 全套 378 passed。
