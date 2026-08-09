# 13 局内信息模型(策略入参)

> 总见 [README](README.md)。本文:策略拿到的「入参」= **完整的局内信息**,分两半 —— **观测态 `GameState`**(本局画面/状态快照,OCR 填)+ **游戏参考数据**(全量注册表,策略可查)。原则一句话:**信息层只管完整、准确地提供;用不用是策略层的事**。
>
> **why 见** [`decisions.md` D-70](../decisions.md)。本文只讲 what(字段/语义/来源/接线状态)。相关:[05 数据接线](05_data_wiring.md)(`GameState` 怎么被 OCR 填)、[11 策略插件](11_strategy_plugin.md)(`CwStrategy` 钩子收 `state`)、[10 战斗反馈](10_battle_and_enemies.md)(观测日志 `PerformanceTracker`)。

---

## 13.0 目标与非目标

**目标**
- **完整**:策略能拿到一局货币战争里**所有可能有用**的信息(进度/节点/经济/棋盘/商店/投资/装备/资源/生命 + 整局固定事实 + 历史节点日志),**不因「现在没用」就缺字段**。字段先全建出来。
- **单一入口**:所有局内信息收口到 `GameState` 一个容器(每个决策点一份快照);策略不得到处找(`session` 旁路、`ctx` 散落)。
- **诚实(不说谎)**:没读到的字段 = `None`(显式「未观测」),**不用 plausible 默认值说谎**(现在的 `hp` 默认 100、`count` 默认 1,策略分不清「真值」和「没读到」)。「完整提供」的前提是策略能区分真值与缺失。
- **观测态 vs 参考数据 分离**:`GameState` = 本局动态观测(每回合变);游戏参考数据 = 跨局静态知识(羁绊/投资/装备/敌人机制…),两者分开不混。

> **这份清单是活的,不保证一次穷尽**:实际开发/画面建档/实机探索中,只要发现**新的、可能影响决策的局内信息**,就往本文 §13.2 字段表 + 代码 `GameState` 补字段(同样遵循「先建字段、`None` 兜底、接线独立」)。§13.9 的待核实项核实后也可能带出新字段。完整是目标,不是起点。

**非目标**
- **不替策略决定**:信息层不掺决策逻辑(不给 `hp` 自动套阈值、不给 comp 自动打分);那都在策略层(`cw_decisions`/`cw_comps`)。本文只列字段 + 语义 + 来源。
- **不保证全接 OCR**:字段先全建;**接不接 OCR 是单独的画面建档任务**(见 §13.6 wired 表),接一个填一个。没接的 = `None`,不是空猜。
- **不动 hook 签名**:本文只扩 `GameState` 内容 + 修信息归位;`(state, session, config)` 钩子签名不变(那是另一件事)。

---

## 13.1 设计原则(4 条)

1. **完整优先,用不用归策略** —— 只要游戏里能知道、且可能影响决策的信息,都建模进 `GameState`;某字段当前策略没用,也留着(未来用 / 自定义策略用)。例:`streak`(连胜)、`active_strategies`(已持投资策略)。
2. **`None` = 未观测,不说谎** —— OCR 没读到 / 字段未接线 → `None`(或容器空)。**去掉一切 plausible 默认值**(hp=100、count=1、level 兜底估)。策略层自行决定怎么降级(evaluate 对 `None` 安全跳过)。这是与现状最大的行为变化,需同步改策略层 + 测试(§13.8)。
3. **单一入口 + 整局固定事实归位 `state`** —— 开局读一次、整局不变的事实(3 boss、选的难度、选的投资环境、位面修正、敌人词缀)直接放进 `GameState`,框架开局填一次、之后每回合快照带上;**不再 `session`↔`state` 来回 copy**(修「同一信息两个家」)。`StrategySession` 只剩:策略私有 `memory` + `rng` + `target_comp`(策略产出)+ 观测日志(§13.3)。
4. **观测态 vs 参考数据 分离** —— `GameState` 只装本局观测;跨局的「阵营有几 tier、某投资环境啥效果、某装备啥配方」走游戏参考数据注册表(§13.4),策略 import 查询,不进 `GameState`。

---

## 13.2 `GameState` 字段全集

> 三态标注:**✅ 已建模 + OCR 已接**(有真值)/ **🟡 已建模但 OCR 没接**(现读默认/空)/ **❌ 连字段都没有**(本文新增)。接线是画面建档任务(§13.6)。

### A. 进度 / 节点(肉鸽地图)

| 字段 | 类型 | 含义 | 来源(画面) | 接线 |
|---|---|---|---|---|
| `plane` | `int` | 当前位面 1/2/3 | 顶栏 `X-Y` | ✅ `read_phase_round` |
| `node_index` | `int` | 位面内节点号(原 `round_num` 改名,更准) | 顶栏 `X-Y` | ✅ |
| `node_type` | `str \| None` | 当前节点类型:普通战斗/精英/遭遇/补给/巨星/投资/boss/奖励 | 备战顶部节点行(当前图标)/ 框架 dispatch | ❌(战后 `RoundOutcome` 有,**当前**节点无) |
| `node_path` | `list[NodeInfo]` | 本位面节点序列;过去+当前确定,未来节点若画面可见也填 | 备战顶部节点图标行(纯图标无文字) | ❌ 需视觉/CV(§13.9) |
| `enemy_difficulty` | `int \| None` | 当前节点敌人难度数值(随节点递增,可被投资策略压低) | 备战/节点屏 | ❌ |

`NodeInfo = {type: str, status: Literal["past","current","future"]}`。

### B. 整局固定事实(开局读一次,之后每回合带上)

| 字段 | 类型 | 含义 | 来源 | 接线 |
|---|---|---|---|---|
| `selected_difficulty` | `str` | 本局职级(如 `A8-50`;黑铁→…→财富造物主,A8 后带子档 A8-1..A8-50) | 难度确认屏 | ❌(现 `difficulty` 字段在但没接,改名+扩) |
| `match_type` | `str` | 标准博弈 / 超频博弈 | 模式选择屏 | ❌ |
| `plane_bosses` | `list[str]` | 3 位面 boss 名(= 简报屏「3 阵营」,其实是 3 boss) | 简报首领行 | ✅ `read_bosses` |
| `current_boss` | `str \| None` | 当前位面 boss(派生 = `plane_bosses[plane-1]`) | 派生 | ✅(派生) |
| `plane_modifiers` | `list[str]` | 当前位面的特殊修正(如「战个痛快」);每位面都可能有,非第一位面专属 | 简报 | ❌(待核实各 plane 是否都有,§13.9) |
| `enemy_affixes` | `list[str]` | 当前敌人词缀(简报 debuff + 节点词缀) | 简报词缀行 + 节点屏 | 🟡(简报接了 `read_affixes`,节点词缀待) |

### C. 经济

| 字段 | 类型 | 含义 | 来源 | 接线 |
|---|---|---|---|---|
| `gold` | `int \| None` | 当前金币 | 备战底部金币 | ✅ `read_gold` |
| `level` | `int \| None` | 玩家等级(= 可上阵上限,封顶 10) | 备战左侧 | ✅ `read_level`(兜底改 None,§13.8) |
| `level_up_cost` | `int \| None` | 升下一级金价(读真值,不再用表估) | 购买经验按钮 | ❌ |
| `xp_progress` | `tuple[int,int] \| None` | 购买经验进度 `(cur, next)` 如 `(0,4)` | 左侧购买经验 | ❌ |
| `streak` | `int \| None` | 连胜/连败数(正=连胜?) | 结算屏「连胜×N」 | ❌ |
| `shop_refresh_cost` | `int` | 刷新费用(默认 2,可被投资策略减免) | — | ❌(现写死 2) |

> 利息档从 `gold` 派生(`gold//10`,上限 5),不入字段。

### D. 棋盘(前台 / 后台 / 备战栏)

| 字段 | 类型 | 含义 | 来源 | 接线 |
|---|---|---|---|---|
| `deployed` | `list[Unit]` | 已上阵角色(身份/星级/阵营/前 or 后排/身上装备) | 中央棋盘 | 🟡(字段有,**身份没读**:`rebuild_deployed_from_board` 只 faction 无 char_id;见 §13.11) |
| `bench` | `list[Unit]` | 备战栏角色(身份/星级/阵营/身上装备) | 底部备战栏 | 🟡(字段有,身份靠 tracked_bench OCR 名**但 star 恒1 + append-only 不同步**;见 §13.11) |
| `front_max` / `back_max` | `int` | 前/后排槽位上限(4 / 6) | 硬编码 | ✅ |
| `bench_full_flag` | `bool \| None` | 备战栏满 | 「备战席已满」警告 | ✅ `read_bench_full` |
| `board` | `dict[str, FactionState]` | 阵营激活(count + **激活 tier + 下个 tier 阈值**) | 左侧羁绊面板(`X/Y`) | 🟡(count 接了但脆,**tier/阈值没接**) |

`Unit`(现 `BenchChar` 扩)= `slot, char_id, faction, star, position_pref(front/back), equips: list[str]`(**有序**,装备顺序有关,记在角色身上,不另设 assign 字典)。
`FactionState = {count: int, active_tiers: list[int], next_tier: int | None}`。

### E. 商店

| 字段 | 类型 | 含义 | 来源 | 接线 |
|---|---|---|---|---|
| `shop` | `list[ShopCard]` | 5 张牌(阵营/名/费用/星级) | 商店面板 | ✅ `read_shop_cards` |
| `shop_locked` | `bool` | 商店是否锁定 | 商店 | ❌ |

### F. 投资选择(开局 + 局中)

| 字段 | 类型 | 含义 | 来源 | 接线 |
|---|---|---|---|---|
| `active_env` | `str` | 已选投资环境(开局 3 选 1) | 投资环境选择屏 → 写 state | 🟡(现 `session.active_env`,迁 state) |
| `active_strategies` | `list[str]` | **已持有投资策略**(局中选,可多张;影响经济/难度,如「难度修改器」压敌难) | 备战右侧 / 投资策略选择 | ❌(代码 TODO 已点名 `active_strategies`) |
| `megastar_char` | `str \| None` | 巨星绑定的角色 | 巨星节点 | ❌ |
| `partner_char` | `str \| None` | 选择的伙伴 | 选择伙伴节点 | ❌ |

### G. 装备 / 资源

| 字段 | 类型 | 含义 | 来源 | 接线 |
|---|---|---|---|---|
| `inventory` | `Inventory` | `available_equips`(没装上的可用装备)+ `diamonds`(钻) | 备战右侧面板 | ❌ |

`Inventory = {available_equips: list[str], diamonds: int | None}`。
> 装在角色身上的装备 → `Unit.equips`(见 D),不在 `inventory`。总持有 = `inventory.available_equips` + 各 `Unit.equips` 之和。

### H. 生命

| 字段 | 类型 | 含义 | 来源 | 接线 |
|---|---|---|---|---|
| `hp` | `int \| None` | 当前小队生命值 | 备战右上角(**shop 关闭态**才显示) | ✅ `read_hp`(plan-time shop 开态读不到,需关 shop 帧,§13.8) |

---

## 13.3 节点观测日志(`PerformanceTracker` 扩展,§I)

每个**节点**(战斗后)记一条,策略可查任意历史节点做趋势/复盘。

`NodeRecord`(扩现 `RoundOutcome`):
| 字段 | 含义 | 接线 |
|---|---|---|
| `node_index` / `node_type` / `plane` | 哪个节点 | ✅(loop 传) |
| `enemy_difficulty` | 该节点敌人难度 | ❌(随 `state.enemy_difficulty` 接) |
| `hp_before` / `hp_after` | 战前/战后小队 HP | 🟡(`hp_after` 接了 P1.5;`hp_before` 待) |
| `damage` | 该节点总伤害(结算屏「总伤害」) | ❌ |
| `result` | 胜 / 负 | ❌(PvE 无每局胜负,「负」= 灭团 hp→0) |
| `comp_tag` | 当时 target comp | ✅ |

存 `session.performance.history`(已是 source of truth);`on_round_end` 填一条。

---

## 13.4 游戏参考数据(策略可查的注册表,§J)

跨局静态知识,策略 `import` 查询,不进 `GameState`。**单一源 = 代码注册表**(CLAUDE.md「工程化/单一真相源」+ 2026-08-06「游戏数据代码单一源」):游戏数据(name/effect/category/faction/source)一旦在代码注册表全量建模,对应 `data/` doc 即冗余 → **删除**(doc 与代码双源 = 漂移);doc 只在「代码未全量」时作过渡源。

| 数据 | 代码注册表 | 完整度 |
|---|---|---|
| 阵营(羁绊 tiers/效果) | `cw_factions.FACTIONS` | ✅ 31 条 |
| 角色(费用/站位/类型/阵营) | `cw_chars.CHARACTER_ROSTER` | ✅ 74 条 |
| 阵容库 | `cw_comps.COMP_LIBRARY` | ✅(持续填) |
| 投资环境(效果/加成阵营) | `cw_investments.INVESTMENT_ENVS` | ✅ 全量 ~82(D-68 数据银行核对;doc 已删) |
| 投资策略(效果) | `cw_investments.INVESTMENT_STRATEGIES` | 🟡 只收 T0(event_whitelist 用);全量仍在 doc,待收敛 |
| 装备(效果/配方) | `cw_equipment`(+ `cw_synthesis` 合成图谱) | ✅ 全量 153(D-70)+ 合成配方 28(D-77,K7 两两合成);`equipment.md` 留作生成器源(model A,非冗余) |
| 敌人词缀 → 机制 | `cw_comps.AFFIX_MECHANIC_MAP` + `MECHANIC_COUNTERS/SYNERGIES` | 🟡(词缀 OCR 名/池待实机校准) |
| 词缀效果原文 | `affix_effects_data.AFFIX_EFFECTS` | ✅(运行时自动采) |

**缺口(§13.9)**:投资策略/装备代码注册表补全 + 各自 doc 收敛(环境已收敛 D-68);competitors 词缀实机校准。

---

## 13.5 整局固定事实归位(从 `session` 迁入 `state`)

现 `StrategySession` 里的粘性字段 → 迁入 `GameState`(框架开局读、之后每回合快照带):

| 现 `session` 字段 | 迁入 `state` 字段 |
|---|---|
| `briefing_bosses` | `plane_bosses` |
| `briefing_affixes` | `enemy_affixes` |
| `active_env` | `active_env` |
| `plane` / `round_num`(镜像) | 删(`state.plane`/`node_index` 已有) |

迁完后 `StrategySession` 只剩:`target_comp`(策略产出)、`rng`、`performance`(观测日志)、`memory`(策略私有 scratch)。`DefaultCwStrategy.update_target` 里的 `session→state` copy 段删除(信息已在 state)。

---

## 13.6 接线状态表(对接画面建档)

每个 🟡/❌ = 一个待画面建档(`od-dev-screen-onboarding` / `od-dev-ui-region-detect`)的区域。建模先全建(本文),接一个填一个。

| 区域 | 待接字段 | 备注 |
|---|---|---|
| 难度确认屏 | `selected_difficulty` | OCR 职级名 |
| 模式选择屏 | `match_type` | |
| 备战顶部节点行 | `node_type` / `node_path` | **纯图标无文字**,需视觉/CV 建图标模板 |
| 备战/节点屏 | `enemy_difficulty` | 数值 |
| 简报 | `plane_modifiers` | 待核实各 plane |
| 节点屏 | `enemy_affixes`(节点词缀) | 简报已接 |
| 备战左侧购买经验 | `level_up_cost` / `xp_progress` | |
| 备战左侧羁绊面板 | `board`(tier/阈值) | count 已接,扩 |
| 结算屏 | `streak` / `hp_before` / `damage` / `result` | 「连胜×N」「总伤害」 |
| 备战右侧面板 | `inventory`(equips/diamonds) / `active_strategies` | |
| 中央棋盘 / 备战栏 | `deployed`/`bench` 身份 + `Unit.equips` | 现不读身份 |
| 商店 | `shop_locked` | |
| 投资环境/策略选择 | `active_env`(迁)/`active_strategies` 写入 | |

---

## 13.7 难度模型(两阶)

(记进 `docs/game/gameplay/currency_war.md`;字段在 `GameState` §B/A。)

- **`selected_difficulty`(职级)**:黑铁→青铜→翠钢→钴银→冰肽→紫金→投资大师→资本帝王→**财富造物主**(A8,最高)。V4.0 扩到 **A8-1 ~ A8-50**(子档)。**决定起始敌人难度** + 是否带额外敌人词缀。来源:官方玩法说明 + V4.0 扩充说明。
- **`enemy_difficulty`(敌人难度,数值)**:**随节点推进递增**(节点类型不同曲线不同,V3.8 调过:削遭遇敌人攻速攻击、提奖励节点奖励);**可被投资策略压低**(「难度修改器」银 −4、部分金 −3,最低降到 0)。boss 血量 ≈ `base × 1.052^enemy_difficulty`(每 +8 难度 ≈ +50% 血;A8-60+ 血量几十~上百亿)。难度越高 → 敌人属性(攻/速/血)↑ + 额外敌人词缀。
- 两阶都要进 `state`;`state.difficulty`(现)→ 改名 `selected_difficulty` + 新增 `enemy_difficulty`。

---

## 13.8 向后兼容 / 迁移

- **字段保留 + 扩**:现 `GameState` 字段(gold/hp/plane/level/board/shop/bench/deployed/equips/bosses/active_env/enemy_affixes/...)保留;新增 §A-G 缺的;改名 `round_num→node_index`、`difficulty→selected_difficulty`;`equips`(顶层)→ 拆成 `inventory` + `Unit.equips`。
- **去谎言默认(行为变化,需测试)**:`hp` 默认 100 → `None`;`board` count 默认 1 → 缺失不编;`level` 兜底估 → `None`。**策略层(`cw_decisions` evaluate/plan/economy_score...)要对 `None` 安全降级**(跳过该项,不崩、不误判)。同步改测试(现测试可能依赖默认值)。
- **`session` 迁移(§13.5)**:`briefing_*`/`active_env` 进 state;`DefaultCwStrategy.update_target` 的 copy 段删;`battle_loop.__init__` 的 session copy 删。
- **接口不动**:hook 签名 `(state, session, config)` 不变;`plan`/`evaluate` 的冗余 `faction_priority` 参数清理是可选后续(不捆进本文)。

---

## 13.9 待实机核实项

> 建模不阻塞(字段先建,`None` 兜底);核实后填真值。

1. **`plane_modifiers`**:第二/三位面是否也有位面修正(还是只有第一位面)?简报屏各位面分别显示什么?
2. **`node_path`**:备战顶部节点行的**未来节点**是否可见(像肉鸽地图),还是只能「走到一个记一个」?各节点图标代表啥(战斗/精英/boss/补给/遭遇/投资/奖励)—— 需 `od-dev-ui-region-detect` 建图标模板 + 视觉大模型核实(计数/图标语义不可信,要裁切对拍)。
3. **`active_strategies`**:备战右侧是否显示当前持有哪几张投资策略?在哪块?
4. **`inventory`**:右侧面板装备/钻的确切位置 + 读法(图标 or 数字)。
5. **`streak`**:结算屏「连胜×N」的正负语义(连胜 vs 连败怎么区分)。
6. **游戏参考数据注册表**:投资环境已全量(`INVESTMENT_ENVS` ~82,D-68);投资策略(现只 T0)/装备待补全 + doc 收敛;competitors 词缀 OCR 名/池实机校准。

---

## 13.10 实施顺序(建议)

1. **建模**(纯逻辑,不需游戏):扩 `GameState` 字段 + `Unit`/`FactionState`/`Inventory`/`NodeInfo`/`NodeRecord` 类型;去谎言默认(改 `None`);`session` 粘性字段迁 `state`;策略层加 `None` 安全降级 + 测试调绿。
2. **参考数据补全**(纯逻辑):核 `cw_investments`/`cw_equipment` 完整性,缺的补。
3. **接线**(需游戏,画面建档):按 §13.6 表,优先级 = 对决策影响大的先(`enemy_difficulty`/`node_type`/`active_strategies`/`inventory`/`streak` > 其余)。
4. 每接一块,`GameState` 对应字段从 `None` → 真值;策略自然用上(不用改策略代码)。

---

## 13.11 现状代码级 gap(已建模但坏掉的,2026-08-08 审计)

> §13.2 标 🟡「已建模但 OCR 没接」。审计发现 bench/deployed 更严重:**已建模但 bot 跟踪逻辑坏** → 字段有值却是错的 → 比没接更危险(策略拿假信号当真)。决策见 [`decisions.md`](../decisions.md) D-127。

bench/deployed 的实现级 bug(**非** OCR 缺失,是 bot 自跟踪逻辑错):

| 项 | 现状(坏) | 后果 |
|---|---|---|
| bench 星级 | `tracked_bench` 纯名列表,`_tracked_bench_chars` 建 `BenchChar` **不传 star → 恒 1** | `char_quality_score`(`bc.star × 优先`)星级项失效;3 合 1 升星无收益信号 |
| bench 同步 | `tracked_bench` **append-only**:buy 时 append,但 deploy/sell/3 合 1 升星**全不同步** | bench 数量虚高(已 deploy/sell/merge 的角色还在)→ `_bench_faction_counts` / `_concentration_delta` / `BENCH_TARGET_WEIGHT` 全在虚高信号上算 |
| deployed 身份 | `rebuild_deployed_from_board` 从 board 阵营计数重建,**只 faction 无 char_id** | `char_quality` deployed 部分 / `core_chars` 匹配失效 |

**影响**:这三个 bug 让 `evaluate` 的 concentration(用 bench faction)/ `char_quality`(用 bench+deployed 的 char_id+star)在**失真信号**上算。这是 #97(comp spread)调 7 次策略权重没用的隐藏根因之一 —— 不是策略错,是评分地基坏(实例见 I28「策略对但执行坏」)。

**优先补 —— bench 自跟踪(纯逻辑,不依赖 OCR)**:能 bot 自跟踪的不靠屏幕识别。把 `tracked_bench`(纯名列表)升级为带星级的状态机:
- `buy(name)` → append(name, star=1) → merge(同名同星 ≥3 → 合并 star+1,借 `cw_state._merge_bench`)。
- `deploy(identity, row)` → bench 移 deployed(deploy_bench 的 SIFT identity D-102 回报拖了谁,身份保留)。
- `sell` / 每轮用 `board`(OCR 真值)校正总数。

低风险(纯逻辑,可离线单测)、高收益(评分地基修复)。**先于其它接线** —— 地基修复前不调策略权重(避免重蹈 D-120~D-126「在坏地基上调」)。修完用 A8-1(用户已选)实测:concentration 信号是否变准、board 是否真能集中。

**其它 gap 的优先级(接 §13.10,补现实约束)**:
- **#2 观测回路**(结算屏掉血/胜负):「观测驱动」命脉,但依赖结算屏画面建档(§13.9;`on_round_end` 现不被调用)→ 工程 uncertain,先探查画面,不阻塞 #1。
- **#3 节点候选身份**(megastar/partner/supply):需立绘/装备模板库(§13.6),节点出现才验证。
- streak / 对手阵容 / node_path / equips:§13.9 待核,次优。
