# 消费点迁移（详设）

> 总纲划给本篇：消费点迁移的方法与判定规则、旧羁绊名映射表、边界处置、测试面。数据层形态契约见 trait-data-layer.md。

## 问题与约束

- 迁移对象 = `data/cw_factions.py` 的 `FACTIONS` 全部消费。**清单方法论（第一轮对抗 A5-A8 定案）：静态手抄清单必然漂移（首版漏 3 文件/错 2 路径/错 1 实体）——迁移面以 grep 实测为单一源**：
  - 引用面命令：`Get-ChildItem src/sr_od/application/currency_war -Recurse -Include *.py | Select-String 'FACTIONS|cw_factions'`（2026-11-13 实测 = **55 文件 / 355 处**，含注释与 docstring 字面；消费面以「非注释行 + import」复核）；
  - 死代码面命令：`Select-String 'is_trailblazer|trailblazer_|SIDE_PICK_DUAL_BONDS|side_pick_bond'`；
  - 每阶段开工时重跑命令生成当日清单，按本篇 §2 分组判据归类处置；设计不预写逐文件清单（漂移源）。
- 双重变化叠加：①数据来源与字段路径（FACTIONS → Trait）；②羁绊名大换血（旧 32 名 → 新 29 名）——迁移不是等值替换，凡消费「消失羁绊」的逻辑属**规则失效**，需按新机制重写或标注退役，禁机械改名。
- 边界约束：本迭代文件面不含角色注册表条目删改（角色批）、不含 COMP_LIBRARY 阵容知识重建（知识层批）、不含策略特判（用户裁定暂缓）——但**必须保证 import/测试不炸**（处置见 §4）。
- 跨迭代查表契约（第一轮对抗 A15 立项；形态用户裁定 2026-11-14 = **派生形态**）：members 翻译依赖「plaza id → 角色规范名」查表；**契约要求 = 消费方（本迭代生成器）运行期从角色注册表现场派生映射（`{c.source: c.name for c in CHARACTERS}`，只读注册表、不落数据文件）——注册表 v4.7 多档建模后每条目自带 source（阿哈三档 151112/151122/151132 各自成条），映射与注册表本体信息量相同，角色批专门交付索引符号属数据复制，故不要求其暴露符号**；覆盖范围 = config role_list 全部条目 id（含升格高费档等对拍例外档——实测帖内阿哈 5/7 费档 id 出场 21/81 帖，聚合 role_ids 并集必含，派生映射天然覆盖，生成器保留覆盖对拍守卫，第二轮复攻 B1）；**禁本批补建脱离注册表的平行索引（手工表/独立数据源/硬编码名单）**。

## 方案

### 1. 旧羁绊名 → 新羁绊名映射表（迁移判定依据）

四档分类（依据：config_v4.7 trait_info_list 29 条实测名单 vs 旧 `FACTIONS` 32 条逐名比对；「疑似改名」档最终确认 = 对照新旧 desc 原文，不符即回落「消失+新增」处置）：

| 档 | 羁绊 | 消费点处置 |
|---|---|---|
| **沿用**（10） | 持续伤害、击破、能量、群攻、治疗、追击、欢愉、星核猎手、星间旅人、巡海游侠（type 0→2 类别迁移，名字不变） | 字段路径替换，逻辑不变 |
| **疑似改名**（2，迁移时按 desc 原文确认） | 仙舟→仙舟舰队；护盾→守护 | 同「沿用」，但确认 desc 同机制后才落 |
| **消失**（20，实测真集，第一轮对抗 A4 修正：含狼狩、去师徒——师徒非 FACTIONS 条目，仅 gen_factions 排除常量，归 §3 退役清单） | 贝洛伯格、**狼狩**、盛会之星、列车同行、命运圣杯、昼之半神、夜之半神、银河学者、公司、量子同频、减益、燃血、战技点、挚爱之人、魔术师、大守护者、命运卜者、救世主、头号玩家、领航员 | 消费其名字的**逻辑段失效**——逐处标注「需重写」或「随宿主退役」（§2 C 类判据），禁改名为近似新羁绊 |
| **新增**（17） | 云上五骁、千星商会、奇兽花园、小小巨人、少女乐队、幻月游戏、开拓银轨、梦境交织、黄金大饭店、反击、召唤、连击、双龙吟、幻乐之主、机心巧匠、盗火行者、黑市主理人 | 本迭代不主动新增消费逻辑（策略侧暂缓）；仅数据层可查 |

### 2. 三模式分组判据（每阶段以当日 grep 清单按此归类）

- **A 类·纯字段路径**：消费 `tiers`/`desc`/成员信息且所用羁绊 ∈ 沿用/疑似改名档——替换 `FACTIONS[x]` → `trait_by_name[x]`（`tiers` 投影与 `members` 字段契约见 trait-data-layer.md）。疑似改名档先做 desc 对照确认再落。代表样例（非清单）：`telemetry/cw_win_features.py`、`kernel/cw_gain_chain.py`（activation 判据）、`strategies/impl/mandate_v1/shop.py`、`telemetry/cw_win_model.py`、`obs/cw_faction_obs.py`（`raw in FACTIONS` 名标准化门——键集换血后需按 B 类语义申报新名单门）。
- **B 类·失效逻辑/语义面**：消费消失档羁绊名的逻辑段——逐处标注「需重写」或「随宿主退役」；边界处置见 §4。代表样例：`cw_deploy_logic.py` 量子同频/贝洛伯格特判段、`cw_system_cards.py` 列车同行常量、`cw_gain_chain.py` 策略卡发放判据（**category 语义重定义**，见 §2.1）、`cw_invest_channels.py` 引擎阵营表（见 §4）。
- **C 类·死代码删除**：`trailblazer_*` / `SIDE_PICK_DUAL_BONDS` / `side_pick_bond` 全部符号与调用分支（用户裁定：新版消失即删；前置 = 角色批注册表无开拓者/布洛妮娅）。实测面含（第一轮对抗 A6 修正后）：`data/cw_chars.py`（符号定义）、`kernel/cw_bond_equips.py`、`cw_board_by_row.py`、`cw_deploy_logic.py`、`cw_battle_calib.py`、`cw_exec_state.py`、`cw_game_state.py`、`cw_faction_callbacks.py`、`kernel/cw_action_report/move_unit.py`（路径 A6 修正）、`obs/cw_observation.py`（:1705 归一真代码）、`obs/cw_identity_obs.py`、`obs/cw_megastar_obs.py`、`strategies/impl/mandate_v1/deploy_search.py`（:184-199 选边真代码，该文件 A/C 双处置申报）、`sim/cw_sim_special.py`、`sim/cw_sim_backend.py`、`sim/cw_sim_opening.py`、`sim/power_model/features.py`。以阶段开工日 grep 输出为准（新命中按同类处置）。

#### 2.1 cw_gain_chain 策略卡发放判据的语义重定义（第一轮对抗 A3）

`cw_gain_chain.py:2741-2743`：`activated = {f for f, info in FACTIONS.items() if info.category != 'independent' and ...}`（策略卡羁绊档发放的「非独立羁绊激活全集」）。迁移语义：旧 `category='independent'` 的业务含义 = 「非常规组队羁绊」；新版对应的官方结构 = **`trait_type`**——新判据写法 = `trait.trait_type in (0, 1)`（阵营 + 流派 = 常规组队羁绊），排除 type 2 独立羁绊。**语义重定义声明**：旧排除集 = 7 个单卡专属羁绊，新排除集 = 6 个 type 2 特殊羁绊，集合内容不同但「排除非常规组队羁绊」的业务判据一致；差集（旧有今无 1 个、今有旧无 0 个的重叠核对在迁移阶段以两侧名单对照表落档）。**巡海游侠点名（第二轮复攻 B5）**：沿用 10 档唯一换 type 的羁绊（旧 type 0→新 type 2），判据重定义后其发放资格从旧口径翻转为排除——差集落档时对此例显式核对，作为策略暂缓批恢复时的行为变化输入。处置归 B 类（语义操作，非机械替换）。

### 3. 退役清单（收尾阶段执行）

- `data/cw_factions.py` 整文件退役（`FactionInfo`/`FACTIONS`/成员派生方法消亡）；**时机 = A/B/C 类迁移全部完成后**（防 import 断中间态，第一轮对抗 A10 重划）；
- 旧 `MEMBER_EXCEPTIONS` 不迁——新对拍首跑按差异人裁重建；
- `ISOLATED = {"师徒"}`（gen_factions 排除常量）随师徒概念消亡删除；
- 注释/docstring 中消失羁绊名字面：随宿主文件迁移顺手订正（如 cw_intention.py:592 注释举例含燃血——第一轮对抗 A9 降级为注释订正，非逻辑段）。

### 4. 边界处置（保证 import/测试不炸的最小动作）

- **COMP_LIBRARY（`cw_comps.py`，旧赛季阵容定义）**：字段路径替换（FACTIONS → trait_by_name）+ 模块级退役声明（条目为旧赛季数据，知识层批处置）；条目内旧羁绊名不更新，消费方为策略层（暂缓批）无运行时触达。
- **旧赛季帖子 fixture（`cw_plaza_posts.py`）**：保留原样（历史语料）；其消费测试因注册表查无失败时标 `@pytest.mark.skip` + 理由「v4.7 换赛季，fixture 待新对局重采」（与角色批联动，本迭代复核）。
- **策略偏好默认值（`currency_war_config.py` DEFAULT_*，第一轮对抗 A16）**：`DEFAULT_FACTION_PRIORITY` 含 5 个消失名 + 改名前名「仙舟」——GUI/YAML 可改的策略偏好（meta 层），随策略批校准；本迭代豁免声明进 3.5 判据范围定义。
- **引擎阵营表（`cw_invest_channels.py:89` ENGINE_SYNERGY_FACTIONS，第一轮对抗 A8）**：手编策略表，消失名在 value（键为增益名）——本迭代加退役标注（注释声明待策略批重组），**不更新内容**；3.5 判据豁免。
- **挂账板引用**：`.debug/progress/CW跨迭代挂账.md` §一.0（装备贡献表 L2 / 存量旧红 2 个 / 开拓者选边删除三条款）——开拓者条款批归属以本设计 landing 为准回写（设计定稿时同步）。

### 5. 测试面

- 测试仓 `FACTIONS` 引用排查（同 §2 分组判据归类）逐处迁移或随宿主退役；
- 新增测试：数据层 import 守卫（TRAITS/trait_by_name 键集一致、count_mode 枚举合法、members sanity）+ 对拍闭环测试（trait-data-layer.md §3）；
- 验收基线：L1 全量与迭代前等价（存量旧红 2 个除外，挂账板在案）；
- 判据的 grep 范围定义（供 landing 引用）：「消失名清零」= B 类清单文件内消费代码清零；**豁免** = 手编策略表退役标注段（§4）、`currency_war_config` DEFAULT_*、注册表/装备/fixture 历史数据面、注释内引文。

## 关键取舍

- **迁移走「实测命令 + 分组判据」而非静态逐文件清单**：首版手抄清单被第一轮对抗证伪（漏 3 文件/错 2 路径/错 1 实体，A5-A8 同根因）——55 文件 355 处的动态清单静态枚举必漂移；判据化后每阶段以当日 grep 归类，落地验收用「grep 清零」动态判据兜底。
- **COMP_LIBRARY 不在本迭代重建**：阵容知识属知识层（证据三层方法论管辖，等攻略沉淀），本迭代只负责「不炸」；强行重建 = 无攻略语料的凭空编造。
- **旧 fixture 保留而非删除**：历史对局语料是 sim 校准与复盘方法的资产；换赛季只使「注册表查无」而非数据无效——skip 标记保留可回溯性。
- **cw_gain_chain 判据用 trait_type 重写而非保留 category 字段**：category 在新数据层无官方对应物（trait_type 即官方分类）；为保住一个消费点而在数据层加非官方字段 = 违反数据层纯官方原则——判据语义（排除非常规组队羁绊）由 trait_type 表达，重定义声明见 §2.1。
