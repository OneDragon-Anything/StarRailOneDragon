---
name: sr-od-treasures-lightward
description: 要打、自动化、开发或理解逐光捡金系列玩法（忘却之庭·混沌回忆、虚构叙事、末日幻影、异相仲裁）时用——进副本、看环境增益、查推荐阵容、选编队进战斗、领奖励的操作路由与玩法分型知识，references/gameplay.md 装玩法机制全量建档。凡是「打这期混沌回忆/虚构叙事/末日幻影」「逐光捡金怎么自动挑战」「异相仲裁怎么进」，或开发逐光捡金相关功能（新类型适配/修挑战 bug/补画面建档）、要了解该系列玩法机制，都先用本 skill，即使没明说。基础配队与养成决策归 sr-od-game-coach；单条 op 的实现与调试归 od-dev-write-operation；运行失败排查归 od-dev-debug-automation。
---

# 逐光捡金玩法路由（sr-od-treasures-lightward）

逐光捡金（Treasures Lightward）是常驻高难挑战合集，入口链：大世界 → 手机菜单 → 星际和平指南 → 逐光捡金 tab → 分类页（左侧四类）。玩法总机制与入口链细节见本 skill [references/gameplay.md](references/gameplay.md)；各画面建档见 docs/game/screens/ 下同名 doc。

## 总 checklist（没做完这 5 步不算完成一次逐光捡金任务）

1. ☐ **判类型**：确认目标是四类之一——忘却之庭·混沌回忆 / 虚构叙事 / 末日幻影 / 异相仲裁（对应代码枚举 TLMode：FORGOTTEN_HALL / PURE_FICTION / APOCALYPTIC_SHADOW / ANOMALY_ARBITRATION）。异相仲裁未探明，直接告知用户不能自动打。必做。
2. ☐ **收集输入**：① 环境增益（按类型块的读法读当期实值）；② 敌人弱点与等级（编队屏「建议属性」等）；③ 账号练度（按 `sr-od-account-inspection` 拉米游社数据）。判据：三样各有明确值或标「不可得」，不许缺省编造。必做。
3. ☐ **定阵容**：按 `sr-od-game-coach` 的配队决策工作流选体系与成员，交叉游戏内「通关阵容」推荐。判据：每队给出成员 + 一句核心逻辑。必做。
4. ☐ **导航并挑战**：按类型块的「操作路径」跑 op（经 MCP `run_operation`，op_id 格式 `sr_od.operations.<模块>.<类名>`）。判据：op 返回挑战成功状态。必做。
5. ☐ **奖励确认**：挑战流程内的奖励弹窗由战斗 op 自动处理；期次累计奖励按类型块的「奖励」节核对入口。判据：奖励领取情况有明确结论。必做。

## 公共路由（所有类型通用）

- **进副本**：`GotoTreasuresLightward`（`sr_od.operations.goto_treasures_lightward.GotoTreasuresLightward`，参数 mode = 枚举值字符串）。任意画面出发；已在入口链画面（选关/编队屏等）自动接续，新期开场介绍页与期次更新弹窗自动处理。终点：忘却之庭 = 选关（混沌回忆视图）；虚构叙事 / 末日幻影 = 各自选关。
- **游戏基础信息**（角色/光锥/遗器静态数据）：按 `sr-od-game-coach` 的 MCP 常量查询（`character_lookup` / `cone_lookup` / `relic_lookup`），零 IO 不需登录。
- **账号养成状态**：按 `sr-od-account-inspection`（mys MCP 四工具拉米游社数据）。
- **配队工作流（必做，禁止凭可见列表随手凑）**：① 每节点读敌人弱点（编队屏「建议属性」/首领信息屏）；② 打开编队屏「通关阵容」弹窗看全服推荐阵容——按节点行展示 4 人推荐 + 配套增益图标，识别用脸库（analyze_screen 或截图脚本匹配头像）；③ 点「一键上阵」套用当前选中行的推荐（未持有位保留现有成员并留空，需手动补；确认弹窗会显示各节点持有数）；④ 按弹窗行尾增益图标给每行装配对应增益（推荐阵容与增益是配套设计）；⑤ 知识库未覆盖时用 web 搜索补：关键词模板「星穹铁道 4.X 末日幻影/虚构叙事 攻略 配队推荐」，可靠源 = 知乎攻略专栏（如冻梨游研社，含 boss 机制拆解 + 按 buff 分类的阵容）、taptap V4.X 攻略、官方公告；攻略阵容 ∩ 账号持有（弹窗「显示我的持有情况」开关）取交集。
- **攻略搜索**：优先 `sr-od-game-coach` 路由表（玩法档/体系档/阵容档）；知识库未命中再用 web 搜索补，向用户转述时声明「未实证」。
- **游戏内推荐阵容**：各类型编队屏的「通关阵容」入口（分布见各类型块）。
- **增益读取（MCP 直读）**：增益弹窗画面已建档的，用 MCP `analyze_screen` 识别对应画面，返回的 extras 字段直接给出结构化增益（槽位/名称/装配态/描述）。**增益选择一律按卡片位置（1 基 = 从 1 开始数），不按名称**——名称随期轮换，锚名称会跨期失效。
- **挑战策略（所有类型）**：直接挑战**最高已解锁难度/关卡**，不逐难度重打——最高 3 星难度跨期记录，新一期自动解锁该难度及全部前置；3 星通关最高解锁难度 = 视同通关全部前置并补发前置奖励（战斗 op 自动处理弹窗）。常规满星后星启开启（3 支不同队伍挑战 3 关）。
- **期次时效**：增益内容、关卡名、敌人配置随期轮换（约 42 天一期），需当期实读，不使用历史值。

## 忘却之庭 · 混沌回忆（FORGOTTEN_HALL）

### 玩法概貌

传统回合制挑战，相对普通：每关 2 波连续战斗（上下半各 1 支 4 人队，共 8 人），波间无结算直接衔接；星数按剩余行动轮计（满星 36）。每关有独立环境增益（记忆紊流，仅当前关生效），是三类中唯一「单层 buff」的玩法。机制细节见 references/gameplay.md「玩法机制」节。

### 操作路径（agent 从零到通关）

1. `GotoTreasuresLightward(mode='forgotten_hall')` → 选关（记忆紊流更新弹窗自动关闭）。
2. 选关界面点目标关卡水晶 → 编队屏（画面 doc：忘却之庭-编队）。
3. 读输入：编队屏每半场「建议属性」（= 该半场敌人弱点表）+ 敌人等级 +「词条-记忆紊流」看本关增益。
4. 跑挑战 ops（见「编队与战斗 op」）。
5. 战斗收尾自动回选关；换下一关回到步骤 2。多关循环编排无现成 op，由调用方控制。

### 攻略与推荐阵容

- `sr-od-game-coach` 路由到混沌回忆玩法档与体系档。
- 编队屏「按钮-通关阵容」→ 弹窗双 tab：推荐 = 全服统计（新期显示「数据统计中」）；好友 = 好友满星记录（各节点 4 人 + 星数 + 一键上阵按钮，套用效果未实测）。

### 编队与战斗 op

- `TlFillTeamsOp`（`sr_od.operations.tl_fill_team.TlFillTeamsOp`，参数 team_names = 8 个角色中文名按波序拼接，每 4 人切一波）：清空编队 + 按波填人。⚠️ 仅适用忘却之庭编队屏，其余类型布局不同不可套用。
- 编队屏点「混沌回忆」按钮发起挑战（ops 均不点它）——op 内用 `round_by_find_and_click_area` 点「FH_START_CHALLENGE」area，MCP 手动操作用 `analyze_screen` 命中后 `click_game` 按钮中心。
- `TlStartChallengeOp`（`sr_od.operations.tl_start_challenge.TlStartChallengeOp`，参数 wave_teams = [[波1四人],[波2四人]]）：前进 → 秘技 → 开战 → 两波自动循环 → 挑战成功收尾。

### 奖励

- 首次 3 星通关最高解锁关弹「快速通关」（视同通关全部前置，奖励列表 + 确认）→「获得物品」页——由 `TlStartChallengeOp` 自动处理。
- 期次累计奖励：选关界面「按钮-星芒礼包」→ 馈赠弹窗（印记馈赠 / 回忆馈赠两 tab）。自动领取 op 未建模，需 MCP 手动点击（坐标以画面 doc 为准）。

## 虚构叙事（PURE_FICTION）

### 玩法概貌

多波群怪速刷，按击杀数计分。增益双层：编队屏左栏「战意效果」全局单选（对全部关卡生效）+ 每行行首加号打开「荒腔走板」弹窗三选一（每关独立）。

### 操作路径

1. `GotoTreasuresLightward(mode='pure_fiction')` → 选关（新期开场介绍页自动点「开启故事」）。
2. 选关点目标关卡纸鹤 → 编队屏（画面 doc：虚构叙事-编队）。
3. 读输入：左栏「战意效果」列表 + 每行「荒腔走板」——点行加号开弹窗后，用 MCP `analyze_screen` 识别「虚构叙事-荒腔走板」，extras 返回 node_no/boss_name/buffs（含 slot/name/equipped/desc）。
4. 跑挑战 op（见「编队与战斗 op」）。

### 攻略与推荐阵容

- `sr-od-game-coach` 路由到虚构叙事玩法档（群怪/速击体系优先）。
- 编队屏「按钮-通关阵容」辅助查看。

### 编队与战斗 op

- 组合 op（把子 op 串成完整挑战的入口 op）`TlPureFictionChallengeOp`（`sr_od.operations.tl_pf_challenge.TlPureFictionChallengeOp`）：参数 team_names（8 人按行序）、buff_slot（战意效果序号，1 基）、buff_slots（每行荒腔走板序号列表，1 基）。前置 = 已在虚构叙事编队屏（组合 op 不做选关→编队屏跳转，操作路径步骤 2 由调用方完成）。
- 内部子 op 也可单独跑：`TlPfTeamFillOp` / `TlPfBuffEquipOp`（buff_slot + buff_slots）/ `TlPfBattleOp`。

### 奖励

- 3 星首通最高难度弹「快速通关」补发前置奖励——由 `TlPfBattleOp` 自动处理。
- 期次累计奖励领取入口未建模（挂账）。

## 末日幻影（APOCALYPTIC_SHADOW）

### 玩法概貌

少怪打机制击破首领 boss：每行（节点）一支 4 人队，共 2 节点；增益 = 每行行尾圆圈按钮打开「终焉公理」弹窗三选一。行内「坚防守备」类按钮是敌方特性查看器（点击只弹说明，不改装配），不是 buff 选项。

### 操作路径

1. `GotoTreasuresLightward(mode='apocalyptic_shadow')` → 选关（新期开场介绍页自动点「前往挑战」；画面 doc：末日幻影-选关）。
2. 选关默认选中最高可玩难度——进编队屏前重新点目标难度标签。
3. 读输入：「末日幻影-首领信息」画面看 boss 弱点与机制；行尾圆圈开「终焉公理」弹窗后，用 MCP `analyze_screen` 识别「末日幻影-终焉公理」，extras 返回 node_no/boss_name/buffs（含 slot/name/equipped/desc）。
4. 跑挑战 op（见「编队与战斗 op」）。

### 攻略与推荐阵容

- `sr-od-game-coach` 路由到末日幻影玩法档（击破/爆发体系优先），boss 机制核对画面 doc：末日幻影-首领信息。
- 编队屏通关阵容入口未建档；攻略缺口用 web 搜索补。

### 编队与战斗 op

- 组合 op `TlApocalypticShadowChallengeOp`（`sr_od.operations.tl_as_challenge.TlApocalypticShadowChallengeOp`）：参数 team_names（8 人按行序）、buff_slots（每行终焉公理序号，1 基，默认 (1,1)）。入口节点自行处理「选关屏→编队屏」跳转（已在编队屏 / 挑战进行中也直接接续）。
- 队伍须避开带警告标记的角色（如当期试用）——可落位但「前往挑战」校验不过、点击无反应。
- 内部子 op 也可单独跑：`TlAsTeamFillOp` / `TlAsAxiomEquipOp`（buff_slots）/ `TlAsBattleOp`。

### 末日幻影补充（星启交互模型与通关阵容）

- 「通关阵容」按钮位置随布局漂移：双节点(01-03)在编队屏右上 y≈147；星启(04)在同区域 y≈65——点击前以 OCR 实读「通关阵容」文本位置为准。
- 星启编队屏交互模型（2026-11-06 实机）：点行内槽位剪影（x≈1494）= 展开选人列表 + 选中该行；行尾「+」（x≈1826）= 打开该行终焉公理增益弹窗；右上垃圾桶 = 清空全部三行（连增益一起清）；**退出编队屏直接关闭丢弃修改，从节点结算页「退出」回编队屏则保留**；改队后再挑战会弹「战绩重置」确认。
- 通关阵容弹窗已建档（screen `末日幻影-通关阵容`：推荐/好友 tab、三节点行、一键上阵、换一批；fixture 测试仓 `末日幻影-通关阵容/推荐阵容.webp`）；推荐头像用脸库脚本识别（fixture 帧实测全部命中）。

### 奖励

- 快速通关补发——由 `TlAsBattleOp` 自动处理。
- 星启模式（难度04，三节点）：挑战 ops 未适配（显式防御）；槽位识别在星启布局下按新标定常量工作（`tl_team_obs` 星启分支），填充/装配/战斗链的 op 适配仍在挂账；期次累计奖励领取入口未建模。

## 异相仲裁（ANOMALY_ARBITRATION）

未探明：无画面建档、无玩法 doc、无挑战 op。`GotoTreasuresLightward` 对它的分支点击入口按钮后显式失败挂账。要打它：先按 `od-dev-screen-onboarding` 建档 → 按 `od-dev-gameplay-automation` 从零做 op——在此之前如实告知用户不能自动打。

## 现状边界

- app 整体（选关循环 / 星数检测 / 满星自动下一关）未迁移新框架：单次挑战的各 op 可用，多关编排由调用方控制。
- 忘却之庭星启模式（第 12 关 3 节点）未适配。
- 所有增益按位置选择不按名称；所有点击坐标以 screen_info / 画面 doc 为准，不在代码里硬编码。
