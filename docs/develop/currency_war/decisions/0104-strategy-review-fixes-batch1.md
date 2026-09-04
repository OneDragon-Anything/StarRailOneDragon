# 0104 策略 review 修复批次 1(反甲白厄死comp / 蒙特卡洛concentration / 卖路径护target)

Status: accepted
Date: 2026-08-12

## Context
两子 agent 全面 review 策略实现(战术 cw_decisions + 战略 cw_comps/performance;报告见 `.debug/temp/currency_war/cw_dev/策略review_缺口.md`),出 6 阻塞 + 多次优。本批次修前 3 个易修快赢(#1-3);#4-6(select_comp acq 主导 / comp_score 动态权重 / 牌池 acq)下批次。

## Decision Drivers
- commitment(承诺 target)须贯穿全链路(买/部署/卖),非只买部署。
- 估值口径一致(蒙特卡洛 D 牌 vs 真实买)。
- 数据正确(factions ⊆ FACTIONS,防命途/职业误当阵营)。

## Considered Options

### #1 反甲白厄 factions=["毁灭"] 死 comp(cw_comps:310)
- 根因:"毁灭"是命途(destruction,DPS_PATHS)非阵营,白厄真无阵营(`cw_chars:104` factions="",独立羁绊"救世主")→ form_progress 恒 0,死 comp 污染候选池。
- **A(选)**:factions/form_tiers 改空(白厄无阵营;反甲流靠单核 + 以牙还牙甲×3,不靠阵营成型)+ 防回归测试(factions/form_tiers ⊆ FACTIONS)。
- B:移出 COMP_LIBRARY(破 4 处测试引用,工作量大)。
- C:守卫(form_progress 0 不进 select)—— 不修数据根因。
选 A:白厄真无阵营,最小改 + 防回归。

### #2 蒙特卡洛 _best_buy_deploy_eval 漏 _concentration_delta(cw_decisions:524)
- 根因:D 牌估值(蒙特卡洛)与真实买(`_best_improving_action`)口径不一致 —— 真实买加 `_concentration_delta`,蒙特卡洛不加 → 集中度维度(±4~8)在 D 牌估值缺席 → 低估刷新价值 → 该 D 不 D。
- **A(选)**:补 `_concentration_delta`(口径统一)。
- B:忽略(D 牌估值仍偏)。
选 A:1 行口径统一。

### #3 卖路径不护 target 核心(cw_decisions:370/587/634/789)
- 根因:`_bench_sell_value` 只护 character_priority + close_factions,不护 target_comp → 刚买的 target 核心(非 priority/非 close)被当"最弱"卖凑息 → 一边承诺 target 一边卖 target 核心(plan 内同回合可能发生)。
- **A(选)**:`_bench_sell_value`/`_weakest_bench_idx`/`_maybe_sell_for_interest` 加 target_comp 参数,target 核心(core_chars / 全羁绊 `_card_hits_target` 命中)+100 保护分(同 priority 量级)+ plan 2 调用处(L587/L634)传 target_comp。
- B:仅扩 priority(用户须手列所有 target 核心,不可持续)。
选 A:commitment 贯穿卖路径。

## Decision
- #1 反甲白厄 factions=[]/form_tiers={};+ `test_comp_factions_in_FACTIONS` 防回归。
- #2 `_best_buy_deploy_eval` 补 `_concentration_delta`。
- #3 卖路径 3 函数加 target_comp + target 核心 +100;plan L587/L634 传 target_comp。
- `test_select_comp_optionality_top_n` 修正:旧断言"select top3 raw comp_score 降序"假设错(select 按乘法总分排序,raw 不保证),反甲白厄 factions 修正后暴露。
- 296 测试过。

## Consequences
- 反甲白厄不再死 comp(form_progress 0 但靠 core+equip;select 候选 progress 低,board/formation 中性 1.0)。
- 蒙特卡洛 D 牌估值准(含集中度)→ 该 D 时 D。
- target 核心不被卖凑息(commitment 贯穿卖路径)。
- 下批次:#4 select_comp acq 主导(P1 弱根因)/ #5 comp_score 动态权重(死重)/ #6 牌池 acq(识别 deployed/bench)。
