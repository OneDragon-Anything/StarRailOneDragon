# 货币战争(currency_war)游戏数据

> 玩法概览(机制 / 流程 / 决策点)见 [docs/game/gameplay/currency_war.md](../gameplay/currency_war.md)。
> **本目录 = 游戏玩法数据**(玩家视角事实:机制 / 数据,游戏版本改才变,**与自动化代码无关**)。
> 自动化实现设计(bot 流程 / 策略 / 决策 why)见 [docs/develop/currency_war/](../../develop/currency_war/)。
> 依据 `od-dev-gameplay-automation` ADR-0008:docs/game/ 只放游戏玩法,自动化归 docs/develop/。判据:「游戏改了它变 → 本目录;代码改了它变 → docs/develop/」。

## `data/` —— 游戏数据(⚠️ 2026-08-18 大收敛:注册表全量建模的 doc 已删,数据单一源铁律)

**已删(代码注册表即单一源,版本更新改注册表+测试,doc 不再维护)**:
- ~~characters.md + characters/ 74 文件~~ → `cw_chars.CHARACTERS`(72)
- ~~traits.json + traits/ 34 文件 + factions.md~~ → `cw_factions.FACTIONS`(32)
- ~~equipment.md~~ → `cw_equipment.EQUIPMENTS`(158)
- ~~invest_cards.md~~ → `cw_invest_data`(plaza API 生成器直灌注册表,ADR-0150)
- ~~comp_library.md~~ → `cw_comps.COMP_LIBRARY`(20 套,含 V4.4 评级)

**保留(未全量建模:注册表承载结构化数据,本文承载叙事/启示层)**:
- [README](data/README.md) —— 索引 + 数据源 / 抓取通道 / 剩余缺口
- [gameplay.md](data/gameplay.md) —— 官方玩法说明(content/6564 全文)+ 机制速查(**有限行动值(AV)限时** 等)
- [competitors.md](data/competitors.md) —— ~50 敌人词缀机制分类/克制叙事(**词缀效果原文已入注册表 `affix_effects_data`,HandleBriefing 运行时采集;机制克/利映射在 `cw_comps.MECHANIC_COUNTERS`**)+ 竞争对手阵营(未建模,唯一源)
- [advantage_layouts.md](data/advantage_layouts.md) —— 优势布局(跨局 meta;注册表未建,唯一源)
- [bosses.md](data/bosses.md) —— boss 克制(**机制 tag 已入注册表 `cw_enemy_data.BOSS_MECHANICS`(20)+ `matchup`;本文=逐 boss 技能叙事/克制启示层**)

## `research/` —— 玩法研究(我们提炼/核实的知识,活文档)

索引与权威序见 [research/README](research/README.md):**user_playstyle(用户口述,策略校准最高权威)** / economy(经济机制核实)/ **combat(战斗机制:三乘区/星级/血量星/连胜)** / **transitions(过渡体系:P1 骨架/护航/买牌纪律)** / plaza_methodology(M1-M16 玩法方法论)/ **final_comps(终局阵容十类深读,单套 comp 打法知识单一源)** / invest_effects(投资效果全量分类)。与 `sources/`(外部原文存档,按版本冻结)相对——research 是经我们核实、随版本原地更新的知识;写作纪律(证据分级/无实现进度/值单一源在注册表)见 [docs/game/README.md](../README.md)。

## `sources/` —— 外部原文存档(`阵容_` 阵容攻略 / `公共_` 公共知识;按版本冻结)

保真纪律与命名规约见 [sources/README](sources/README.md):只带来源元数据头,原文不改,我们的批注不进存档;提炼后的现行结论以 [research/](research/README.md) 为准。

- [阵容_README](sources/V4.4_阵容_README.md) —— 跨阵容 pattern(评级总览 / 开局过渡分级 / 通用角色 / 通用装备 / 成型节奏共性,V4.4)
- 逐套:17 套(V3.7×5 / V3.8×5 / V4.0×1 / V4.2×1 / V4.4×5)见各文件(V 前缀即版本)
- [公共_视频目录](sources/公共_视频目录.md) —— UP「甘泽成谣雨成诗」45 个币战视频按版本编目 + 转录状态
- [公共_核心机制](sources/V3.7_公共_核心机制.md) / [公共_经济运营](sources/V3.7_公共_经济运营.md) / [公共_前期过渡](sources/V3.7_公共_前期过渡.md)(V3.7 必修一/二/三)/ [公共_难度攻略](sources/V4.0-4.4_公共_难度攻略.md)(A830-A850 难度环境 + 中期过渡三套护航,V4.0/V4.2/V4.4)

## 画面事实
画面(screen doc,游戏提供的 UI)算游戏玩法,仍在 [docs/game/screens/](../screens/)(`currency_war_*.md`)。

## 版本维护
货币战争赛季制,数据随版本变。更新流程:① 投资/环境:重跑 `tools/cw/gen_plaza_invest.py`(plaza API,内建 diff 报告,直灌注册表)→ 按 diff 修 overlay 孤儿键;② 角色:重跑 `tools/cw/gen_plaza_chars.py`;③ 其余:重抓米游社图鉴 → **同步代码注册表**(`cw_chars.CHARACTERS` / `cw_factions.FACTIONS` / `cw_equipment.EQUIPMENTS` 等,注册表是唯一数据源)→ 回归测试。data/ 仅 bosses/competitors 等未建模 doc 需手工同步。
数据源优先级:plaza 官方 API / 游戏内(权威)>>> 米游社百科 >>> bwiki / NGA / 攻略(参考)。标 🟢 官方原文 / 🟡 攻略一致 / 🔴 未找到。
