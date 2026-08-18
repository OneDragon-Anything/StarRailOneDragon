# ADR-0209: 阵容选择架构重构——双轨过渡 + 信号定型(用户六轮指导定稿)

## Status

Accepted(2026-08-18 r37-r47 用户指导定稿;接线批待做)

## Context

七连败(A8)的共同根因:select_comp 从最终 comp 选线 → P1 买「半成型最终线」
(form 0.25-0.5)打不过玩家的「成型过渡包」→ P1 后段战力崩 → boss 稳定损
20-36 → P2 残血开局即溃。bot 的玩法模型缺了「过渡」这整层。

## Decision Drivers(用户指导链,r37-r47)

1. **P1 过渡阵容与最终 comp 很少重叠**(plaza 784 篇实证:重叠双峰,38% 一条线
   /22% 完全换阵;纯过渡牌 艾丝妲31%→2% 等)
2. **主流过渡 = 仙舟系(32%)+ 列车系(29%)两种**;DOT 在 V4.4 退化为 2DOT
   挂件(28%),无纯 DOT 过渡阵容
3. **过渡期可买最终 comp 牌存 bench(不上场)**——囤牌是正确投资,不是错误
4. **定型信号从开局积累**:词缀→P1 投资策略→P1 投资环境→商店供给→补给/遭遇/
   奖励节点产出(「当前局的整体观察」);最晚 P2-3 投资选择定型,之后经济量
   不足以转型
5. **P1 大部分用过渡阵容 5 人口过**(Early 上场 79%=5 人)——本质尽快 50 金
   吃满息;等级在定型时才拉(我们 P1 冲 lv6-7 花光金 = 方向反)
6. **comp 二分法**(数据):可一条线(命运圣杯61%/群攻/量子54%/仙舟 ≥50%,
   低费核心)vs 需过渡包(战技点11%/追击29%,高费核心);希儿线是条件式一条线
   (Early 拿到希儿才成立)
7. **COMP_LIBRARY 不重定**(攻略手工建档,plaza 对账全覆盖;「能量线」=双王
   圣杯形态)——但**数据字段以官方 API 聚合为准**(by_carry 29 簇:key_equips/
   form_tiers 分支比/core_chars 频次/3星率),guides 作机制注释
8. **flex 全收有风险**:列车 7 个 flex 是跨攻略聚合,单局应按信号收敛到 1-2 个

## Considered Options

1. **双轨架构(选)**:场上打过渡双框架包(仙舟/列车),bench 按信号领先线囤
   最终牌;信号达标或 P2-3 deadline 定型(卖过渡→最终上场→装备星级全投)
2. 只修 select_comp 权重:不动层,半成型问题仍在
3. 全部换阵过渡:丢掉低费线一条线的机会(38% 的真实玩法)

## Decision

选 1。已落地模型层(cw_transition.py):
- `TRANSITION_PACK` 双框架(仙舟包:藿藿/饮月/爻光/卡芙卡/椒丘;列车包:
  三月七/姬子/花火/瓦尔特;通用插件:千冶·刃)
- `CommitSignals` 信号管线(7 信号源加权累积;词缀1.5/策略2.0/环境1.0/供给0.5/
  补给0.8/遭遇0.6/奖励0.4;ready=领先线≥3.0)
- `COMMIT_DEADLINE_T=12`(P2-3 强制定型)、`EARLY_POP_CAP=5`(P1 五人口攒息)

### 接线批(待做,统一实施后全量测试)

1. **信号喂入**:update_target 各信号到达时调 CommitSignals.add
   (词缀=mechanics_fit 分/投资策略=affinity 表/节点产出 handler 挂点)
2. **双轨买牌**:plan prefilter 双轨期允许买「信号领先线」的牌进 bench;
   场上维持过渡包(EARLY_POP_CAP)
3. **定型切换**:ready or past_deadline → target 切最终线 + 卖过渡牌
   (复用 r32 集中卖散,keep 集按过渡包档位)
4. **flex 收敛**:flex_factions 按信号倾向收敛 1-2 个(护盾流/减益流)
5. **P1 经济**:双轨期 spend_mode 以 interest 为主(DP interest 姿态已支持),
   定型后才 rush_level(与 r16 切流咬合)
6. **字段换血(API 口径)**:key_equips←carry_equips 频次/form_tiers 分支比←
   traits 分布/core_chars←units 频次(星期日 217/274 核)/star_goals←3星率

## Consequences

- 策略从「一条线打到底」升级为玩家真实玩法「过渡→定型」两段式;
- p1_direct 分流:低费线(core 均费≤3)可 P1 早 commit,高费线完整双轨;
- 全部接线完成前不分步全量测试(用户口径:调整完再统一测);
- 实跑验证指标:P1 boss 损血(现 20-36)/P2 进场 hp+gold/胜率。
