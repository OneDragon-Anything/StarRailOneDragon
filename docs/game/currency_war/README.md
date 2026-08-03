# 货币战争(currency_war)深度文档

> 玩法概览见 [docs/game/gameplay/currency_war.md](../gameplay/currency_war.md)。本目录是货币战争自动化的
> **数据 + 策略设计**深度文档(从 `.debug/temp/currency_war/` 迁入 docs/,版本化 + 代码注释可稳定引用)。
> 开发日志(process_log / insights / decisions / strategy_research / articles / review 报告)仍在 `.debug/temp/currency_war/`(不入 git,本地工作区)。

## 目录

### `data/` —— 游戏数据(策略地基,米游社百科 V4.4 原文 🟢)
- [README](data/README.md) —— 索引 + 数据源/抓取通道/剩余缺口
- [gameplay.md](data/gameplay.md) —— 官方玩法说明(content/6564 全文)+ 机制速查
- [factions.md](data/factions.md) —— 31 羁绊逐层效果原文
- [characters.md](data/characters.md) —— 74 角色(费用/站位/类型/阵营/流派)
- [competitors.md](data/competitors.md) —— ~50 敌人词缀全集 V4.4(按机制分类)
- [equipment.md](data/equipment.md) —— ~130 装备(简易/进阶/特权/星徽/白昼/Fate/工具)
- [investment_strategies.md](data/investment_strategies.md) —— 216 投资策略
- [investment_envs.md](data/investment_envs.md) —— 74 投资环境(概念股/邀请/契约…)
- [comp_library.md](data/comp_library.md) —— 起步阵容 roster 8+ 套 + V4.4 评级 + S 级运营要点
- [economy_research.md](data/economy_research.md) —— 牌池/买卖退金/刷新概率/boss HP 缩放(实据)
- [advantage_layouts.md](data/advantage_layouts.md) —— 优势布局(跨局 meta,bwiki pending 米游社)

### `strategy/` —— 策略完整方案(设计先行,代码按它实现)
- [README](strategy/README.md) —— 总(一句话方案 + 三层架构 + 用户配置口 + 实施阶段)
- [01_architecture.md](strategy/01_architecture.md) —— 三层架构 + 数据流
- [02_eval_search.md](strategy/02_eval_search.md) —— A3 阶段键控 eval + A1 蒙特卡洛 D 牌 + A4 牌池
- [03_comp_planning.md](strategy/03_comp_planning.md) —— A2 阵容规划(comp_score/转型/巨星/经济统一论)
- [04_state_reconciliation.md](strategy/04_state_reconciliation.md) —— A6 多层数据校准方法论
- [05_data_wiring.md](strategy/05_data_wiring.md) —— GameState 字段表 + 每回合 op 序列
- [06_phases.md](strategy/06_phases.md) —— 逐阶段实施 + replay harness
- [07_equipment.md](strategy/07_equipment.md) —— 装备模型 + equip_fit(comp 相关)
- [08_node_decisions.md](strategy/08_node_decisions.md) —— 遭遇/巨星/补给出钻节点决策
- [09_meta_run.md](strategy/09_meta_run.md) —— 跨局 meta-run(优势布局默认不碰)
- [10_battle_and_enemies.md](strategy/10_battle_and_enemies.md) —— 观测反馈 PerformanceTracker + 敌人机制双向

## 代码引用

代码注释引用本目录稳定路径,例如:
- `cw_chars.py` → `docs/game/currency_war/data/characters.md`(角色规范名单一真相源)
- `cw_comps.py` → `docs/game/currency_war/strategy/03_comp_planning.md`(阵容规划设计)
- `cw_shop_odds.py` → `docs/game/currency_war/data/economy_research.md`(D牌池参数)

## 版本维护

货币战争赛季制,数据随版本变。更新流程:重抓米游社图鉴(`data/` 各文件)→ 同步代码注册表
(`cw_chars.CHARACTERS` / `cw_factions.FACTIONS` / `cw_equipment.EQUIPMENTS` 等)→ 回归测试。
数据源优先级:米游社百科/游戏内(权威)>>> bwiki/NGA/攻略(参考)。标 🟢 米游社原文 / 🟡 攻略一致 / 🔴 未找到。
