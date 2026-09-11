# ADR-0230 遥测采集缺口接线(session→state 统一回写)

## Status

accepted(2026-08-22;r358d;承接 ADR-0229 缺口清单,用户指令「缺代码的先补」)

## Context

观察面审计(ADR-0229)发现 9 个 GameState 字段恒空。逐一核查根因后分三档:①session 有数据但 read_game_state 只回写了 active_strategies 一项(default_strategy.update_target 的注入只覆盖 default 策略,LineStrategy 局全空);②handler 选择后未落 session(巨星/伙伴);③根本无 reader(位面修正/锁店)。streak 核查为**误报**——L905 一直接好,局46 恒 0 是结算真值。

## Decision Drivers

- 注入点应在 state 组装层(read_game_state),与策略无关——update_target 注入只覆盖一个策略是结构性错位
- 复盘维度(环境/词缀/巨星/伙伴)与决策维度(mechanics_fit/boss_fit/env 亲和)同源,一处接线两处受益

## Considered Options

1. 在 LineStrategy.update_target 复制 default 的注入段:第二处副本,策略族再扩还要抄。
2. **read_game_state 尾部统一回写**(选):session(持久宿主)→ state 每次组装时拷贝,幂等(非空才覆);default_strategy 原注入保留不冲突。
3. 顺手补 plane_modifiers/shop_locked 的 reader:超出「接线」范围(观察基建=新 reader+area 建档),留工作项。

## Decision

选 2。改动:cw_observation.read_game_state 尾部 +5 字段回写(active_env/plane_bosses/enemy_affixes/chosen_megastar→megastar_char/chosen_partner→partner_char);run_megastar_node/handle_select_partner 选择时写 session.chosen_*;StrategySession 声明两字段。skill telemetry-reading 缺口清单同步(仍缺 reader 的 2 项标注)。验证:observation 35 passed + 全量 959 passed(1 已知 flaky 单跑过)。
