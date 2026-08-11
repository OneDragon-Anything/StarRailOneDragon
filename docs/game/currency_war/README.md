# 货币战争(currency_war)游戏数据

> 玩法概览(机制 / 流程 / 决策点)见 [docs/game/gameplay/currency_war.md](../gameplay/currency_war.md)。
> **本目录 = 游戏玩法数据**(玩家视角事实:机制 / 数据,游戏版本改才变,**与自动化代码无关**)。
> 自动化实现设计(bot 流程 / 策略 / 决策 why)见 [docs/develop/currency_war/](../../develop/currency_war/)。
> 依据 `od-dev-gameplay-automation` ADR-0008:docs/game/ 只放游戏玩法,自动化归 docs/develop/。判据:「游戏改了它变 → 本目录;代码改了它变 → docs/develop/」。

## `data/` —— 游戏数据(策略地基,米游社百科 V4.4 原文 🟢)
- [README](data/README.md) —— 索引 + 数据源 / 抓取通道 / 剩余缺口
- [gameplay.md](data/gameplay.md) —— 官方玩法说明(content/6564 全文)+ 机制速查(**有限行动值(AV)限时** 等)
- [factions.md](data/factions.md) —— 31 羁绊逐层效果原文
- [characters.md](data/characters.md) —— 74 角色(费用 / 站位 / 类型 / 阵营 / 流派)
- [competitors.md](data/competitors.md) —— ~50 敌人词缀全集 V4.4(按机制分类)
- [equipment.md](data/equipment.md) —— ~130 装备(简易 / 进阶 / 特权 / 星徽 / 白昼 / Fate / 工具)
- [investment_strategies.md](data/investment_strategies.md) —— 216 投资策略
- 投资环境(~82,概念股 / 邀请 / 契约 / 时代 / 经济 / 规则 / 专家)—— **代码单一源** `src/sr_od/application/currency_war/cw_investments.py::INVESTMENT_ENVS`(代码已全量建模,doc 不存)
- [comp_library.md](data/comp_library.md) —— 起步阵容 roster 8+ 套 + V4.4 评级 + S 级运营要点
- [economy_research.md](data/economy_research.md) —— 牌池 / 买卖退金 / 刷新概率 / boss HP 缩放(实据;刷新概率权威值在代码 `cw_shop_odds.REFRESH_PROB`)
- [advantage_layouts.md](data/advantage_layouts.md) —— 优势布局(跨局 meta,bwiki pending 米游社)
- [bosses.md](data/bosses.md) —— boss 克制

## 画面事实
画面(screen doc,游戏提供的 UI)算游戏玩法,仍在 [docs/game/screens/](../screens/)(`currency_war_*.md`)。

## 版本维护
货币战争赛季制,数据随版本变。更新流程:重抓米游社图鉴(`data/` 各文件)→ 同步代码注册表(`cw_chars.CHARACTERS` / `cw_factions.FACTIONS` / `cw_equipment.EQUIPMENTS` 等)→ 回归测试。
数据源优先级:米游社百科 / 游戏内(权威)>>> bwiki / NGA / 攻略(参考)。标 🟢 米游社原文 / 🟡 攻略一致 / 🔴 未找到。
