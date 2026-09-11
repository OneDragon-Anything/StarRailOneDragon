# 0132 投资卡效果原文采集(invest_cards.jsonl;ground truth 回流)

## Status

accepted(2026-08-15;用户问「有没有代码在采集投资策略和投资环境的效果」—— 答案是只采名字不采效果,补)

## Context

名字层已有(handle_invest_strategy/env OCR 三卡名 → 选中的写 session.active_strategies/active_env → decisions.jsonl state 快照),但**效果层零采集**:_read_options 的 OCR 刻意按 y 带过滤掉描述文本;无运行时数值对账。ADR-0131 对拍米游社 315 全量 doc 发现 T0 十二条里 8 条效果描述错 —— 长期没发现的根因就是没有 ground truth 回流。且 INVESTMENT_STRATEGIES 注册表只收 T0(~19/315),遇到的绝大多数策略无效果数据也无告警。

## Considered Options

- 采集方式:①停机钩子(方案 D)—— 否:每局稳定遇到 2-6 张卡,无需停机;②**复用同一帧 OCR 顺带分桶**(零额外 OCR 成本,采集不拖慢备战)→ 采用;③单独再跑一次全图 OCR —— 否:双倍耗时。
- 落点:decisions.jsonl(回合决策迹)vs 独立 invest_cards.jsonl —— 独立(事件粒度不同;每卡一行便于离线对拍)。
- 生命周期:**常驻 telemetry**(与 decisions.jsonl 同级,enabled 默认开)非临时采集钩子 —— 315 长尾靠每局遇到渐进补全 + 版本变更感知,是长期数据回流基础设施。

## Decision

1. cw_telemetry:`bucket_card_texts(anchors, items, y_min, y_max)` 纯函数(文本归 x 最近锚点卡,描述带过滤,桶内 y 升序)+ `record_invest_cards(kind, cards)` 模块级(invest_cards.jsonl,每卡一行 {ts,run_id,kind,idx,name,x,effect_text,chosen})。
2. handle_invest_strategy:_read_options stash 全图 OCR map(同帧复用);选卡后按描述带 y 505-835 分桶采集(kind=strategy);未注册名 [cw-strat] 告警(镜像 env 侧 is_known_env)。
3. handle_invest_env:同款(描述带 y 410-900,kind=env;环境注册表虽全量仍采 —— 对拍校验 + 版本变更感知)。

## 后续(数据回流闭环,离线)

- 离线对拍脚本:invest_cards.jsonl vs INVESTMENT_STRATEGIES 注册表 → 出差异清单(错效果/未注册)→ 补注册表(ADR-0131 长尾渐进)。
- 运行时数值对账(定期福利 +2金/节点、加油站免费刷 gold 不降)—— 待 M17+ 遥测量够后做效果验证。

验证:测试 3 项新增(test_cw_telemetry 12 passed);M17 起生效。
