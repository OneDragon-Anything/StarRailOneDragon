# 0106 策略 review 修复批次2(W_BOSS死重 / character_priority三重 / star钩子漏bench)

Status: accepted
Date: 2026-08-12

## Context
review 缺口批次2(次优快赢 + #5 最小减死重)。#5 动态权重(comp_score 死重治本)+ #6 牌池 acq(大改)下批。

## Decision
- **W_BOSS 0.10→0(暂)**:boss_fit 恒 0.5(countered_by_bosses 俗称未对齐 task#73 → 死重),权重让 W_PROG(0.45→0.55)。boss 机制建模接通后回退 0.10。部分减死重(comp_score 动态权重治本 = 下批 ADR-0107)。
- **character_priority 去 CHAR_PRIORITY_BONUS\*2**(买候选 flat):`char_quality_score` 已计 priority×star,原三重(char_quality + 买*2 + 豁免门)过度偏置用户偏好。豁免门留(不阻 priority 买)。
- **star 钩子查 session.tracked_bench_chars**(原查 state.bench 恒空,因 read_game_state 不读 bench 身份 → 漏 bench 2星如赛飞儿)。

## Consequences
- comp_score boss 死重减(W_BOSS=0);equip/mech/env 死重仍在(动态权重治本下批 ADR-0107)。
- priority 角色买意愿降(只 char_quality 一处计,非三重);豁免门留(不阻塞)。
- star 钩子采 bench 2星(赛飞儿类不再漏 → read_star 2星样本采集闭环)。
- 296 测试过。
- **下批**:#5 动态权重(comp_score *_fit 返 None + 归一)+ #6 牌池 acq(识别 deployed/bench 身份 + 牌池剩余模型 → acq 扣牌池消耗,用户点出的根因)。
