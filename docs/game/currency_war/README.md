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
- (economy_research.md 更早已迁 docs/develop/currency_war/strategy/ —— 用户口述策略校准非固化游戏数据)

**保留(注册表未建模的唯一源)**:
- [README](data/README.md) —— 索引 + 数据源 / 抓取通道 / 剩余缺口
- [gameplay.md](data/gameplay.md) —— 官方玩法说明(content/6564 全文)+ 机制速查(**有限行动值(AV)限时** 等)
- [competitors.md](data/competitors.md) —— ~50 敌人词缀全集 V4.4(按机制分类;⚠️ 代码注册表未建,唯一源)
- [advantage_layouts.md](data/advantage_layouts.md) —— 优势布局(跨局 meta)
- [bosses.md](data/bosses.md) —— boss 克制(⚠️ 代码注册表未建,唯一源)

## `guides/` —— 攻略目录(`阵容_` 阵容推荐 / `公共_` 公共知识)

### `阵容_*.md` —— 阵容攻略(玩家视角,游戏知识)
每套阵容怎么 work / 成型节奏 / 过渡 / 装备(为什么)/ 弱点。米游社 V4.4 合集(76807134)+ 各 comp 攻略 + B 站 UP「甘泽成谣雨成诗」视频转录核实。
- [阵容_README](guides/V4.4_阵容_README.md) —— 跨 comp pattern(评级总览 / 开局过渡分级 / 通用角色 / 通用装备 / 成型节奏共性)
- 逐套:[阵容_列车同行](guides/V4.4_阵容_列车同行.md) / [阵容_命运圣杯红A](guides/V4.4_阵容_命运圣杯红A.md) / [阵容_绯英欢愉](guides/V4.2_阵容_绯英欢愉.md) / [阵容_希儿量子](guides/V4.4_阵容_希儿量子.md) / [阵容_黄泉减益](guides/V4.4_阵容_黄泉减益.md) / [阵容_龙丹战技点](guides/V3.8_阵容_龙丹战技点.md) / [阵容_双王圣杯](guides/V4.4_阵容_双王圣杯.md) ……全 17 套(另含 V3.8 [阵容_大黑塔](guides/V3.8_阵容_大黑塔.md)、V4.0 [阵容_火花星间旅人](guides/V4.0_阵容_火花星间旅人.md))见阵容_README
- 结构化字段(factions/core/form_tiers/level_plan)权威源 = `src/sr_od/application/currency_war/cw_comps.py::COMP_LIBRARY`;本目录是叙事/why(互补非双源)。

### `公共_*.md` —— 公共知识(跨阵容:机制 / 经济 / 过渡;B 站 UP 转录核实,标版本)
- [公共_视频目录](guides/公共_视频目录.md) —— UP「甘泽成谣雨成诗」45 个币战视频按版本(V3.7→V4.4)编目 + 类型 + 转录状态
- [公共_核心机制](guides/V3.7_公共_核心机制.md) —— ★伤害公式三乘区 / 血量加星 / 难度→血量 +5.2%/级 / 投资策略难度(V3.7)
- [公共_经济运营](guides/V3.7_公共_经济运营.md) —— 连胜>>利息 / 牌池副本 27·9 / 卡牌池操纵 / 低费=不赌(V3.7)
- [公共_前期过渡](guides/V3.7_公共_前期过渡.md) —— 桑博+艾斯达 2DOT 过渡公式 / 怪物词条×DOT 互动(V3.7)
- [公共_难度攻略](guides/V4.0-4.4_公共_难度攻略.md) —— A830/A840/A850 难度环境 + 中期过渡三套护航(选择>>努力,V4.0/V4.2/V4.4)

## 画面事实
画面(screen doc,游戏提供的 UI)算游戏玩法,仍在 [docs/game/screens/](../screens/)(`currency_war_*.md`)。

## 版本维护
货币战争赛季制,数据随版本变。更新流程:① 投资/环境:重跑 `tools/cw/gen_plaza_invest.py`(plaza API,内建 diff 报告,直灌注册表)→ 按 diff 修 overlay 孤儿键;② 角色:重跑 `tools/cw/gen_plaza_chars.py`;③ 其余:重抓米游社图鉴 → **同步代码注册表**(`cw_chars.CHARACTERS` / `cw_factions.FACTIONS` / `cw_equipment.EQUIPMENTS` 等,注册表是唯一数据源)→ 回归测试。data/ 仅 bosses/competitors 等未建模 doc 需手工同步。
数据源优先级:plaza 官方 API / 游戏内(权威)>>> 米游社百科 >>> bwiki / NGA / 攻略(参考)。标 🟢 官方原文 / 🟡 攻略一致 / 🔴 未找到。
