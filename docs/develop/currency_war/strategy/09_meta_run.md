# 09 meta-run 层:优势布局 + 攻略推荐(分,round 2 新发掘)

> 总见 [README](README.md)。review r2 发掘的 **跨局/信号源层**(round 1 纯"单局内"视角漏掉的)。
> **2026-08-03 修订(用户实战经验)**:**删"凹开局重开"** —— 策略够好就该能"理智"克服任何开局,重开不必要(原 R2-2 移除)。meta-run 只留**优势布局激活**(跨局 meta)+ **攻略推荐**(版本无关信号源)。

## R2-1 优势布局 / 等价钻钞(跨局 meta 增益)— high

**事实**(gameplay.md 原文):每场对局结束获得「**等价钻钞**」,用于激活「**优势布局**」,为**后续对局**提供额外机制 / 战斗增幅。
**影响**:没激活优势布局的 run 战力先天吃亏;全激活后 A8 通关门槛显著降低。这是**跨局 meta 进度**,直接提升局内战力。

**⚠️ 默认不碰(2026-08-03 用户:防打乱玩家继承)**:优势布局/钻钞是**玩家的持久化跨局继承**(玩家自己攒的 buff)。bot 默认**不动**(配置 `manage_meta_run=false`)——保留玩家设置,不做破坏性操作。**仅当用户显式开 `manage_meta_run=true`** 才:
- **pre-run 阶段(-1)**:run 前检查已激活的优势布局 + 激活最优的一组(OCR 面板 + 点击激活;决策:`decide_advantage_layout(owned_drills, target_a8) → 布局组合`,优先战力增幅类)。
- **钻钞 farming 循环**:用**超频博弈**(R2-5,快速模式)刷钻 → 喂优势布局 → 再打标准 A8(阶段 6+ 元循环,同样受 `manage_meta_run` 门控)。

**原则**:一切**持久化/跨局状态**(花钻钞、改优势布局、改玩家存档类)默认 opt-in(不碰);局内状态(买/deploy/升/D 牌)才默认自动。防 bot 破坏玩家在游戏里的长期投入。

**数据**:优势布局图鉴(../../../game/currency_war/data/advantage_layouts.md bwiki 版,米游社待校准)+ 钻钞数(OCR)。**需游戏**(且需 `manage_meta_run=true`)。
**阶段**:06 加「阶段 -1:优势布局 preconditioning」(pre-run,需游戏 + manage_meta_run 开)。

## R2-3 游戏自带"攻略"推荐(版本无关 ground truth)— high

**事实**(gameplay.md 原文):「打开『攻略』,将根据当前场上及备战席中的角色推荐攻略。应用攻略后,将在商店及备战席中**高亮提示推荐使用的角色**,对应的**推荐装备**也将在对局内提示。」
**影响**:这是**游戏官方实时给的 comp 推荐**,跨版本有效(game 自己随版本更新),正好**补 COMP_LIBRARY 版本过期风险**(R2-12)。比静态 COMP_LIBRARY 更"灵活 + 版本适应"。
**方案**:
- `read_game_guide(ctx) → recommended_comp`(OCR 攻略画面读推荐 comp + 高亮角色 + 推荐装备)。
- select_comp 把 `game_recommended_comp` 作为**先验 / fallback**:COMP_LIBRARY 为先验、攻略为运行时校准;**COMP_LIBRARY 版本过期(version 不匹配)时攻略接管**(R2-12 staleness 的运行时解)。
- 也可用攻略高亮角色作为 character_priority 的动态补充(游戏推荐的角色优先拿)。
**数据**:攻略画面 OCR。**需游戏**。
**阶段**:05 加 `read_game_guide` 字段 + 03 select_comp 用攻略先验(阶段 4-5 接线后)。

## R2-5 超频博弈 vs 标准博弈(med)

**事实**(gameplay.md):超频 = 快速模式(时间更短),晋升点 / 钻钞略少。
**方案**:
- **标准 A8 高胜率(主目标)**:plan 全程针对标准博弈 A8。
- **超频 farming(辅)**:超频刷钻喂优势布局(R2-1)+ replay harness(阶段 5.5)用超频采样更快收敛。
- README 目标段区分「标准 A8 高胜率(主)+ 超频 farming(辅)」。

## 与现有架构的关系
- 09 是 **meta 层(跨局 / 信号源)**,在战略层(A2 阵容)之上/之前:
  - pre-run:优势布局激活(R2-1)。
  - 局内:攻略推荐(R2-3)作为 select_comp 的信号源 + staleness fallback。
- 不推翻三层架构,是在其上加一层「meta-run」(优势布局)。

## 数据需求(游戏边界)
- 优势布局图鉴 + 钻钞数 + 攻略画面:**需游戏**。
- decide_advantage_layout 逻辑(选最优组合):**非游戏**(纯逻辑 + mock 测)。

## 测试(纯逻辑)
- decide_advantage_layout:优先战力增幅布局(势力削弱/投资经验/钻石闪耀等,详 ../../../game/currency_war/data/advantage_layouts.md)。
- select_comp 攻略先验:game_recommended_comp 给定时优先它(version 过期时)。

## 阶段(06 加)
- **阶段 -1**:优势布局 preconditioning(pre-run,需游戏)。
- **阶段 6+**:钻钞 farming 元循环(超频刷钻 → 喂优势布局 → 标准 A8)。
- 攻略推荐接入:阶段 4-5(read_game_guide OCR + select_comp 用)。
