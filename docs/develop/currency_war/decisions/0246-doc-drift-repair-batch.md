# ADR-0246 文档漂移修复批(as-built 对齐代码实况)

## Status

accepted(2026-08-24;文档治理)

## Context

三路对拍审查(机械脚本 + 双子代理深读)发现 **38 条系统性漂移**:develop 侧 as-built 正文停在 strategy-v1 时代(redesign rev9,2026-08-21),代码已演进到 strategy-v2 + sim 基建(2026-08-24);game 侧 data 索引停在「注册表未建」旧状态。重灾区是「入口/索引/清单」类内容:

1. **检索口径失效**:05 §6 日志格式只收录 `[cw]/[cw!]` 两前缀,代码另有 33 种 `[cw-<tag>]` 前缀(~270 处)且 `grep "[cw]"` 检索不到 B 族;
2. **导航断链**:strategy/README 模块地图 6 个 v2 模块标「详 06/07」但两篇零覆盖;sim/replay 基建(8+ 模块,已是验证主链)双零覆盖;
3. **语义矛盾**:redesign §5.4 应急滞回退出(DANGER_ROUNDS/HEAL_HYSTERESIS/EMERGENCY_EXIT_HOLD)与代码 `_EMERGENCY_HP` 绝对档简版(r216)是两套;06 GameState 字段表过期(node_index/inventory 已删改,9+ 新字段缺列);
4. **悬空引用**:ADR-0160/0161/0166/0172/0194 提案号被代码与文档引用但文件不存在且无注记;断链 3 处;gate flag 删除代码/文档各引一号(0213/0216);
5. **game 侧过期**:competitors/bosses「注册表未建」声明过期(`affix_effects_data`/`cw_enemy_data` 已建);「正当防卫」doc 120% vs 注册表实采 100% 数值冲突;REFRESH_PROB 缺口行未闭;
6. **值入正文** 15 处(违反 ADR-0210「值只进代码,文档指常量名」)。

## Decision Drivers

- as-built 正文失去「描述系统现在是什么」的可信度 = 判读/导航/检索工作流直接受损
- ADR-0210 文档真值模型已定框架;漂移是执行欠账不是框架问题

## Considered Options

1. **全文重写 strategy/ + redesign**:工作量与风险大(v2 模块设计内容仍以 redesign 为权威,重写 = 双源风险);否
2. **只修断链不动语义**:入口修了、内容仍误导;否
3. **对齐修复 + 注记补桥**(选):清单/口径/字段表按代码实况重写;设计与实现分歧处加「落地现状(Phase A 简版)」注记桥(设计文本按 ADR-0227 两阶段裁定保留为 Phase B 蓝图);悬空提案号在 INDEX 头加映射注记(同 ADR-0100 先例)

## Decision

选 3。修复面(全部落地):

- **05 §6** 重写为两族前缀(A 识别观测层 cw_log / B `[cw-<tag>]` 流程层)+ 可用检索口径(`grep "\[cw"` 通吃);§4 CLI 补 `checks`/`--sim-batch`;`cw_observe.py` docstring 双源收口(指 05 §6)
- **strategy/README** 模块地图:6 个 v2 模块改指 redesign/02/07 实际所在;补 `cw_recipe` 与 sim/回放基建行
- **redesign**:§5.4 加落地现状注记(绝对 HP 档/E8 吸收态/无滞回,常量指 line_strategy);装置清单三处对齐 `cw_phase_machine` 实况;附录 A 重写为「设计常量 ↔ 落地常量」映射表;§6 处置表补 Phase A 产物/cw_recipe/sim 基建行,cw_economy 行改「部分保留复用」
- **06** GameState 字段表重对齐(round_num/equips/BenchChar + 9 缺列字段 + shop_locked 死字段声明);cw_factions 来源改生成器
- **03/04/07/02**:动作表重写(OpenTome 入/RefreshShop 等标注 sim 层)、接线表补 3 行、钩子清单补 decide_prep/decide_planner、star_goals 归 LevelGoal
- **INDEX** 头部加提案号映射注记(0160/0161/0166/0167/0172/0194 → 现存记录落点)
- 断链 3 处修复;`currency_war_config.py` gate 注释 ADR 号 0213→0216(代码侧错引)
- **game 侧**:data/README 与 game/README 注册表状态更新(词缀效果/boss 机制已建模,doc 降为叙事层);正当防卫按实采值修正(100%,标注旧攻略 120% 分歧);REFRESH_PROB 缺口行闭合
- **值入正文 15 处**改常量名引用(01/02/03/05/config/redesign)

## Consequences

- 正面:检索口径、模块导航、字段表、常量索引恢复可信;sim 基建进入正式文档地图
- 悬空提案号保留原引用不改号(改号 = 触碰 14+ 处代码注释,收益低);由 INDEX 注记承担解释
- `# 未验证` 头标(60/119 文件)是**反向漂移**(标记落后于验证状态),但清除须逐文件按画面复审,不属本批文档修复;留在进度树跟进
- r378c_measure_review.md 已被清理但进度树仍引用(本地文件,顺手记录)
