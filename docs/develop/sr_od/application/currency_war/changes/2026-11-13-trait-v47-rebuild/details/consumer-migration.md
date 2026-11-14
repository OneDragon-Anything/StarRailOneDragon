# 消费点迁移（详设）

> 总纲划给本篇：消费点迁移映射、逐文件清单、退役清单、测试面。数据层形态契约见 trait-data-layer.md。

## 问题与约束

- 迁移对象 = `data/cw_factions.py` 的 `FACTIONS` 全部消费（实测 26 文件，`FACTIONS[` / `.tiers` / `.members` / import 三类合计约 60 处引用）；迁移目标 = 总纲 §2.2 数据层契约（`TRAITS`/`trait_by_name`/`tiers` 投影/`members` 字段）。
- 双重变化叠加：①数据来源与字段路径（FACTIONS → Trait）；②羁绊名大换血（旧 32 名 → 新 29 名）——迁移不是等值替换，凡消费「消失羁绊」的逻辑属**规则失效**，需按新机制重写或标注退役，禁机械改名。
- 边界约束：本迭代文件面不含角色注册表条目删改（角色会话批）、不含 COMP_LIBRARY 阵容知识重建（知识层批）、不含策略特判（用户裁定暂缓）——但**必须保证三者被迁移后的 import/测试不炸**（处置见 §4 边界处置）。

## 方案

### 1. 旧羁绊名 → 新羁绊名映射表（迁移的判定依据）

四档分类（依据：config_v4.7 trait_info_list 29 条实测名单 vs 旧 FACTIONS 32 条 + wiki 旧频道 214 实测 32 词条；「疑似改名」档的最终确认 = 迁移阶段对照新旧 desc 原文，疑似不符即回落「消失+新增」处理）：

| 档 | 羁绊 | 消费点处置 |
|---|---|---|
| **沿用**（10） | 持续伤害、击破、能量、群攻、治疗、追击、欢愉、星核猎手、星间旅人、巡海游侠（type 0→2 类别迁移，名字不变） | 字段路径替换，逻辑不变 |
| **疑似改名**（2，迁移时按 desc 原文确认） | 仙舟→仙舟舰队；护盾→守护 | 同「沿用」，但确认 desc 同机制后才落 |
| **消失**（旧 32 − 上 12 = 20） | 贝洛伯格、量子同频、列车同行、战技点、燃血、盛会之星、银河学者、昼之半神、夜之半神、减益、公司、命运卜者、大守护者、魔术师、挚爱之人、领航员、头号玩家、救世主、命运圣杯、师徒（ISOLATED） | 消费其名字的**逻辑段失效**——逐处标注「需重写」或「随宿主退役」（§3 C 类），禁改名为近似新羁绊 |
| **新增**（17） | 云上五骁、千星商会、奇兽花园、小小巨人、少女乐队、幻月游戏、开拓银轨、梦境交织、黄金大饭店、反击、召唤、连击、守护（若非改名）、双龙吟、幻乐之主、机心巧匠、盗火行者、黑市主理人 | 本迭代不主动新增消费逻辑（策略侧暂缓）；仅数据层可查 |

### 2. 逐文件迁移清单（三模式分组）

**A 类·纯字段路径**（tiers/desc 读数，名字沿用或已核对）——替换 `FACTIONS[x].tiers` → `trait_by_name[x].tiers`、`FACTIONS.get(x)` → `trait_by_name.get(x)`：
`cw_comps.py`、`cw_deploy_logic.py`、`cw_env_grants.py`、`cw_faction_callbacks.py`、`cw_gain_chain.py`、`cw_game_state.py`、`cw_observation.py`、`criteria/predicates.py`、`deploy_search.py`、`cw_win_features.py`、`cw_screen_expert_invite.py`、`cw_screen_bookcard.py`、`cw_investments.py`（对拍闸 §5872-5922）。

**B 类·旧羁绊名硬编码在逻辑里**（消失名 → 规则失效）：
- `cw_deploy_logic.py:91-92`（量子同频/贝洛伯格 ≥2 特判）——两羁绊消失，逻辑段随宿主场景标注退役；
- `cw_engine_facts.py:48-49`（同上复写）——同处置；
- `cw_system_cards.py:51-53`（仙舟/持续伤害/列车同行 tier 常量）——仙舟改仙舟舰队、持续伤害沿用、**列车同行消失**（其系统卡逻辑按新机制重写或退役，迁移阶段按宿主系统卡在新版是否存在定）；
- `cw_intention.py:592-593`（燃血成员名单）——燃血消失，标注退役；
- `cw_invest_channels.py:232`（ENGINE_SYNERGY_FACTIONS 引擎阵营表）——引擎阵营=策略数据，本迭代只保证 import 不炸（键更新为沿用名），引擎重组归策略批。

**C 类·死代码删除**（开拓者双形态 + 布洛妮娅选边，用户裁定；前置 = 角色批注册表无此二者）：
`cw_bond_equips.py`（选边分支+开拓者归一）、`cw_board_by_row.py`、`cw_deploy_logic.py`（`__trailblazer__` 键归一段）、`cw_battle_calib.py`、`cw_exec_state.py`（`trailblazer_row_identity/trailblazer_row_unit`）、`cw_game_state.py`（`_row_unit_tags` 相关分支）、`cw_faction_callbacks.py`、`operations/cw_action_report/move_unit.py`（换排归一调用）、`obs/cw_identity_obs.py`、`obs/cw_megastar_obs.py`、`sim/cw_sim_special.py`、`sim/cw_sim_backend.py`（选边引用）、`sim/cw_sim_opening.py`（双形态合并口径）、`sim/power_model/features.py`（排敏感注释段）。
删除原则：函数与调用分支整体删除（非置空）；注册表条目（开拓者·欢愉/记忆/布洛妮娅）的删除归角色批——本阶段删除的代码在角色批前**不可先行**（依赖声明见 landing）。

### 3. 退役清单

- `data/cw_factions.py` 整文件退役（`FactionInfo`/`FACTIONS`/成员派生方法随之消亡；`gen_factions.py` 的旧对拍段同时被新对拍替换）；
- 旧 `MEMBER_EXCEPTIONS`（布洛妮娅隐藏变体等）不迁——新对拍首跑按差异人裁重建；
- `ISOLATED = {"师徒"}` 概念消亡（师徒羁绊已不在 config 名单）。

### 4. 边界处置（保证 import/测试不炸的最小动作）

- **COMP_LIBRARY（`cw_comps.py`，旧赛季阵容定义引用旧羁绊名与 FACTIONS.tiers）**：本迭代只做字段路径替换（`FACTIONS` → `trait_by_name`）+ 模块级声明「条目为旧赛季数据，知识层重跑批处置」；条目内旧羁绊名不更新（查无 tiers 的条目 = 防孤儿校验会报，故迁移阶段将该字典整体挂显式退役标记——具体形态 = 模块头退役声明 + 条目原样保留，消费方为策略层（暂缓批）无运行时触达）；重建归知识层批。
- **旧赛季帖子 fixture（`cw_plaza_posts.py`，对局快照含大量消失角色）**：保留原样（历史语料）；其消费测试若因注册表查无而失败，标 `@pytest.mark.skip` + 理由「v4.7 换赛季，fixture 待新对局重采」（随角色批注册表重建联动，本迭代复核）。

### 5. 测试面

- 测试仓 `FACTIONS` 引用排查（`FACTIONS[` / `cw_factions import`）逐处迁移或随宿主退役；
- 新增测试：数据层 import 守卫（TRAITS/trait_by_name 键集一致、count_mode 枚举合法、members 非空条目占比 sanity）+ 对拍闭环测试（见 trait-data-layer.md §3）；
- 验收基线：L1 全量与迭代前等价（存量旧红 2 个除外，挂账板在案）。

## 关键取舍

- **迁移走「三模式分组」而非逐文件顺序推进**：A 类机械替换可批量，B/C 类是语义操作必须逐处判——分组后 B/C 的工作量显性化（消失羁绊的失效逻辑是本迭代真正的人工成本所在）。
- **COMP_LIBRARY 不在本迭代重建**：阵容知识属知识层（证据三层方法论管辖，等攻略沉淀），本迭代只负责「不炸」；若在本迭代强行重建 = 无攻略语料的凭空编造。
- **旧 fixture 保留而非删除**：历史对局语料是 sim 校准与复盘方法的资产；换赛季只使「注册表查无」而非数据无效——skip 标记保留可回溯性。
