# 0128 用户人玩节奏落地批次 1(连胜不对称/1费集星免费/boss前花完/comp停留D)

## Status

accepted(2026-08-15;批次 1 —— 用户节奏 §7 + 攻略全量复查 11 项中的 4 项小修 + comp 停留语义)

## Context

用户 2026-08-15 上线口述完整人玩节奏(economy_research §7,权威),并要求全量重审攻略调研找策略缺口。攻略↔代码全量对照产出 11 项真补充(子代理复查,落 `cw_dev/策略复查_20260815.md` 待归档)。本 ADR 落地其中与「位面 2 进场 HP 低 + fp 冻结」瓶颈最直接、且改动面小的 4 项 + comp 停留语义;其余(装备角色级分配/品质难度/插件包/站位 comp 驱动等)排后续批次。

## Decision Drivers

- 用户节奏:「核心在几级概率大就停在那级刷」「boss 关前把钱花完」「1费买卖净 0」。
- 攻略明确条款:核心机制:27(无连败补偿)、经济运营:18(boss 前花完)、前期过渡:29(1费集 2星免费战力)、阵容_列车同行:53(停 7 级 D 3星姬子)。

## Considered Options

- 连胜对称计分保留(TFT 惯例)vs 只计连胜 —— 货币战争无连败补偿(攻略实锤),对称 = 虚构收入 → 只计连胜。
- boss 前花完:node_plan 按轮次猜 boss vs node_type=='boss' 实测标签 —— boss 轮次可变(1-7/1-8/1-9),标签是运行时真值且 boss 检测已实机核实 → 用标签。
- comp 停留:node 地板(固定推 8)vs comp level_plan 显式 roll 压过地板 —— 用户「不无脑停也不无脑推级」,核心概率级停留是 comp 知识 → comp 显式意图优先。

## Decision

1. **连胜不对称**(复查 #5):economy_score streak 只计正方向(连败 0 分)。
2. **1费集星例外**(复查 #11):副本买入门「场上同名散牌不集」加 cost==1 豁免(1星买卖净 0,集 2★ = 免费战力,ADR-0121)。
3. **boss 前花完**(复查 #4):node_type=='boss' → _should_save_for_interest 早退 False + _refresh_cap ≥4。
4. **comp 停留 D 语义**:comp 对当前级显式 roll/stable → _want_level_up 返 False(不买经验,钱花 D 牌)+ _refresh_cap ≥4;列车 level_plan 7 级改 roll 3星姬子·启行(旧 7=level_up 冲 8,违背停留人玩节奏)。

未落批次 1 的复查项(#1/2/3/6/7/9/10 + #8 其余 comp 数据)见 cw_dev 进度,Round-8+ 处理。

验证:CW 全套 378 passed(连胜断言按新语义更新;bench-full 测试改 seeded rng 去偶发)。

