# 逐画面逐动作显示规范（详设）

## 问题与约束

消费 pipeline.md §6 渲染中间表示（唯一数据面；meta 键名闭集在彼处，本文只定义显示形态与中文措辞）。用户裁定（2026-10-16）：局头单独成章逐行排；其余分析章节全部不输出；凡定义的画面 op 有 journal 行即成章；每画面章内「0 观察 → 动作节×N → 策略评价」。裁定偏差申报见 design §1.5（无收尾章、counters 不渲染）。

## 方案

### §1 报告骨架

```markdown
# 货币战争复盘 <game_id>
## 局头
## 开局
### 开局 画面-BOSS简报
### 开局 画面-投资环境
## 节点 1-1 奖励
### 节点 1-1 奖励 画面-备战
#### 0 观察
#### 1 买牌 藿藿(1金)
…
#### 策略评价
### 节点 1-1 奖励 画面-商店
### 节点 1-1 奖励 画面-战斗
## 节点 1-2 …
## 未归节（有则）
## 未归行（有则）
## 复盘者附加
```

### §2 局头（meta 逐行 `- 键: 值`；键名闭集 = pipeline §6 Report.meta）

显示形态：runs 显 run_id 顿号列表；终局行合成一句（`final_type 位面 P-R hp 金 时长`）；stats 零坏行显「无」，非零显 `坏行 N/非对象 N/字节修复 N`。

### §3 画面注册表（actor 全名 → 画面 id / 决策面 / 0 观察键集）

- 快照章（由 current_screen 值开章）：

| current_screen 值 | 章名 | 决策面 | 0 观察键集（键 → 显示） |
|---|---|---|---|
| 货币战争-备战 | 画面-备战 | ✓ | 金 gold/血 hp/等级 level/经验 xp(`已攒/所需`)/升级价 level_up_cost/连胜 streak；前排·后排 deployed（§4.3 单位格式）；备战席 bench（槽位表，§4.3）；后台格数 back_layout；羁绊计数 board（`名×计数`顿号串）；装备库存 equips/穿戴 occupied_equips；晶矿 spheres（`N 座(颜色×n,…)`；points 为点击载荷不渲染）；溢出 overflow_warning/overflow_card；持卡 active_strategies/环境 active_env |
| 货币战争-备战-开商店 | 画面-商店 | ✓ | 金 gold/免费刷新余量 free_refresh_left/刷新价 shop_refresh_cost/等级 level；牌面表（见下）；概率 refresh_probs（`档→概率`顿号串） |
| 货币战争-战斗等待 | 画面-战斗 | ✗ | 战前：deployed/enemy_difficulty/enemy_affixes；**结算不入 0 观察**——settlement 写入行走 pipeline §5「章内变化」块（键集：hp_after/streak_after/killed→胜负/progress_delta/gold/level/xp；来源锚 = `cw_screen_battle_wait.py:125,449-461,550-565`）。settlement 写入行兼作本章开章证据（sim 无 current_screen 形态，pipeline §4 修订） |
| （sim 侧真未注册 id） | 原样 id | ✗ | 空（兜底形态，pipeline §4；注册表扩容后原样本 货币战争-BOSS简报/补给/遭遇节点 已成注册键，兜底只承接未来未知画面） |
| 货币战争-BOSS简报 | 画面-BOSS简报 | ✗ | plane_bosses、enemy_affixes、selected_difficulty（sim 广播值） |
| 货币战争-简报 | 画面-BOSS简报 | ✗ | 同 BOSS简报（sim 广播值） |
| 货币战争-补给 | 画面-补给 | ✓ | supply.options、supply_refresh_left、gold（sim 广播值） |
| 货币战争-遭遇节点 | 画面-遭遇 | ✓ | encounter.options、encounter_refresh_left（sim 广播值） |
| 货币战争-投资环境 | 画面-投资环境 | ✓ | invest_env_opts、env_refresh_left、gold（sim 广播值） |
| 货币战争-投资策略 | 画面-投资策略 | ✓ | invest_strategy_opts、strategy_refresh_left（sim 广播值） |
| 货币战争-位面过渡 | 画面-位面转场 | ✗ | node_seq_by_plane、enemy_affixes（sim 广播值） |
| 货币战争-备战-武装箱选择 | 画面-箱子 | ✓ | box_card_names（sim 广播值） |
| 货币战争-备战-专家邀请函 | 画面-专家邀请 | ✓ | expert_invite（sim 广播值） |
| 货币战争-盛会之星 | 画面-巨星 | ✓ | megastar_opts（sim 广播值） |
| 货币战争-银狼升星 | 画面-银狼策划 | ✓ | planner_opts（sim 广播值） |

- 注册纪律：同 title 必须同规格（decision/键集）——相邻合并沿用先开章规格，异规格会同义静默错判；本表以代码为准（渲染器 `SCREEN_REGISTRY` 为最终事实）。

- 弹层章（由 actor 映射开章；回执 screen/sig.screen 不参与切分，pipeline §4）：

| actor | 章名 | 决策面 | 0 观察键集 |
|---|---|---|---|
| CwScreenInvestEnv | 画面-投资环境 | ✓ | invest_env_opts、env_refresh_left、gold |
| CwScreenInvestStrategy | 画面-投资策略 | ✓ | invest_strategy_opts、strategy_refresh_left |
| CwScreenSupplyNode | 画面-补给 | ✓ | supply.options、supply_refresh_left |
| CwScreenEncounter | 画面-遭遇 | ✓ | encounter.options、encounter_refresh_left |
| CwScreenBriefing / CwScreenBossBriefing | 画面-BOSS简报 | ✗ | plane_bosses、enemy_affixes、selected_difficulty |
| CwScreenPlaneTransition / CwScreenPlaneDetail / CwScreenPlaneIntel | 画面-位面转场 | ✗ | node_seq_by_plane、enemy_affixes（plane_modifiers 为登记在案恒缺键，不列） |
| CwScreenMegastar / CwScreenPartner / CwScreenExpertInvite / CwScreenFortune / CwScreenWishTrial / CwScreenBookcard / CwScreenBoxPick / CwScreenArmoryBox / CwScreenAhaEquipPick | 画面-巨星/伙伴/专家邀请/命运卜者/祈愿试炼/书卡/箱子/军械库/顿悟装备 | ✓ | megastar_opts/partner_opts/expert_invite/fortune_opts/wish_trial_opts/box_card_names/box_card_names/equips/equips |
| CwScreenYinLang | 画面-银狼策划 | ✓ | planner_opts（两卡候选） |
| CwOpSettleConfirm / CwLoop（对局收口） | 画面-对局收口 | ✗ | ——（终局事实在局头，design §1.5） |

- 交互辅助 op（`CwScreenItemDetailPopup/CwScreenRefreshOddsPopup/CwScreenRoleDetailOverlay/CwScreenShopCardDetailPopup/CwScreenEmblemDetailPopup/CwScreenInterruptDialog/CwScreenConsumableOverlay/CwScreenNextButton/CwScreenWaitOneOne/CwScreenPrepLockedReturn/CwScreenDeployNotFull/CwScreenPrep/CwScreenShop` 等）：CwScreenPrep/CwScreenShop 即快照章两行（备战/商店），不另注册；其余辅助 op 与其余 `operations/cw_screen/` 已定义 op（目录实测 33 个 op 类）按裁定②同规：**有 journal 行即按其 actor 注册显示，无行不出现**；未注册进缺口注记。
- 商品牌面表：`| 槽 | 牌名 | 阵营 | 费用 | 星级 |`；槽 = ShopSlot 数组下标+1，三态：content 显卡值/empty 显「空」/unknown 显「识别失败」（`cw_game_state.py:731-744`）。

### §4 动作节显示规范

- 标题：`#### <序号> <动作名> <摘要>`；动作名 = §4.1 映射；摘要组装优先级 = action 载荷（如 `藿藿(1金)`）> detail > 无摘要。
- 动作行 `- 动作:`：`applied/reason/detail` 透传；`applied=false` 或 `reason` 非空 → 行首 **⚠**；action 载荷 = 人读摘要（`牌名(阵营,费用金,槽N) · char_id · reason`，T-5）；其余 extra 逐键列出。
- 状态变化表：`| 字段 | 前 → 后 | 说明 |`（挂动作节 = 锚后区间；无锚前缀写入行 = 章「章内变化」块，同表结构）；字段列 = §4.2 映射，未命中显原始 field 名；`logic_hook` 行说明列加「(效果钩子)」。
- 无状态变化的动作只渲染动作行。

#### §4.1 动作词中文映射（回执动词开放集：已见词 + 现役发射点枚举 + 未命中原样显示）

短动词（live 实测）：BuyCard→买牌 / SellBench→卖备战 / SellDeployed→卖上阵 / DeployMove→换位 / RunDeploy→部署 / WearEquip→穿装备 / ClickSpheres→点晶矿 / CwOpOpenShop→开店 / CwOpCloseShop→收店 / StartBattle→出战。
参数型别名（sim 实测 + 现役发射点 `cw_close_shop_action.py:49` 等）：CwActionBuyCardParam→买牌 / CwActionSellBenchParam→卖备战 / CwActionDeployMoveParam→换位 / CwActionWearEquipParam→穿装备 / CwActionLevelUpParam→升级 / CwActionLevelUpShopParam→店内升级 / CwActionStartBattleParam→出战 / CwActionCollectOreParam→采晶矿 / CwActionCloseShopOp→收店。
代码词表补录（旧流实测有、新账未再现，保留映射）：LevelUp→升级 / LevelUpShop→店内升级 / RefreshShop→刷新商店 / OpenBox→开箱。

#### §4.2 状态字段中文映射（journal field → 名；来源 = `cw_game_state.py:2209-2636` Field 注释）

gold→金 / hp→血 / level→等级 / xp→经验 / streak→连胜 / level_up_cost→升级价 / deploy_cap→部署上限 / bench→备战席 / deployed→上阵 / front_row→前排 / back_row→后排 / back_layout→后台格数 / board→羁绊计数 / equips→装备库存 / occupied_equips→穿戴 / shop→商店牌面 / spheres→晶矿 / active_env→投资环境 / active_strategies→持卡 / planner_opts→策划候选 / chosen_*→已选(各选项) / settlement→结算 / node→节点 / current_screen→画面 / overflow_warning→溢出警告 / overflow_card→溢出卡。

#### §4.3 复杂载荷单元格格式（JSON 形状 → 显示，确定性规则；差分单元格与观察行共用 `_value_brief`）

- 通用兜底：list → 顿号串逐元素；dict → `k:v` 逗号串；tuple → 逗号串；None/缺 → 不渲染该行。
- **已知键走具名摘要（T-5 起，差分单元格与观察行同规，禁截断 raw JSON）**：bench → `爻光1★、三月七1★(空×6)`；deployed → `前排 希儿1★;后排 藿藿1★`；front_row/back_row → 单位顿号串；board → `名×n` 顿号串；spheres → `2 座(灰×2)`（points 不渲染）；shop → `椒丘1金、翡翠1金(空×2)(识别失败×n)`；ore_rewards → `40,10=装备 轮滑鞋;50,10=角色 翡翠;70,10=金+3`；node_path(含 baseline) → `P1: —→奖励→战斗→…`（token 中文）；node → `P1-R3 战斗`；settlement → `胜 血 84 进度 +2 …`；match_final → `stopped hp 84 金 31`；xp → `已攒/所需`；标量列表键（equips/active_strategies/plane_bosses/enemy_affixes/各 *_opts）→ 顿号串；occupied_equips → `单位:装备,装备`；node_seq_by_plane → `P1: 奖励→…;P2: …`；round_fresh_buys → `phase[1,1]: 翡翠、三月七`；pending_loss → `P1-R4 (battle)`；supply/encounter → `0: 角色+装备(带钻);…`（options 摘要）；回执 action 载荷 → `牌名(阵营,费用金,槽N) · char_id · reason`（动作行）。
- 通用兜底规则用于未注册键；新遥测键应先进 §4.3 摘要注册再进词表。
- **0 观察的表格型键不走摘要**（entry_tables 路径，规格不变）：bench → 槽位横排表 `| 1 | … | 9 |`（表头 = 槽号，数据行 = 内容 `名★级`/「空」/「未识别」，三态同 ShopSlot `cw_game_state.py:740`；用户裁定 2 行×9 列横排）；supply/encounter options → `| 列 | 内容 |` 表（encounter 行 = `难度N=奖励文本`，supply 行 = `角色+装备组(带钻标)`）；shop → 五槽牌面表（§3）。摘要路径只服务差分单元格与观察行。

### §5 特殊情况

1. **仲裁行**（row='obs_event'，识别回读与账面不一致的裁决记录）：挂所在画面章尾注 `- 仲裁 <field>: <old> → <new>（<verdict>）`。
2. 观察道更新（sig.family='obs' 写入行，非章首快照）：章尾注 `- 观察: <字段中文>=<人读摘要>`；**空值/空串不渲染**；`prev_screen`/`current_screen` 路由键跳过；同章同 (field, 格式化值) 去重（T-5）。
2a. **渲染同值行**（差分单元格前=后）：不进变化表，章尾注 `- 同值写入 ×N 略(前=后,零信息)`（T-5）。
2b. **开局段无画面归属行**：渲染为开局组尾「### 开局初始化与基线观察」小节（开局初始化写入 / 开局基线观察 / 未注册缺口保留显影），不粘进画面章（T-5；规则 = pipeline §3 修订）。
3. 续局（--run/多段）：局头「运行段」如实列出。
4. 未归行：文末 `## 未归行` 清单（pipeline §6 annex_unattached）；空则省略。未归节组：标题 `## 未归节`，组内画面章同规。
5. 空动作画面章：只渲染 0 观察 + 章内变化块（若有）+ 策略评价（若决策面）。
6. **策略评价**：固定 `#### 策略评价` 空节，决策面画面章必有；渲染器不预填任何评价内容。
7. 动作标题摘要的 action 载荷缺位时：由状态变化表交叉定位标的物（BuyCard 回执实测含完整 action 载荷——牌名/费用/槽位，缺位形态可接受；结论，对抗审已裁决）。
8. **复盘者附加**：文末固定 `## 复盘者附加` 空节（渲染器只给标题，不预填任何子结构）；协议四产出（候选修复项/回灌判据读数/位面三问/完整性审计）等复盘者义务产物填入该节（用户裁定 2026-10-16 落点 = A）。

## 关键取舍

- **0 观察只显有值行 vs 全键占位**：只显有值。快照是累计子集（pipeline 问题与约束），占位行会把「未观察」与「真值为空」混为一谈（event_overlay 双义禁令先例，`cw_game_state.py:2453`）。
- **不做跨行回查**（如 BuyCard 回执缺 action 时回查店面前 payload）：回执自带字段 + 状态变化表已可定位标的物；跨行回查引入次序猜测，违背行行自足消费纪律（journal.md §5）。
- **cw4_counters 不渲染**（裁定③字面：策略行为键，retirement.md §3）；match_final 非计数键进局头终局行。
- **不设收尾章**（裁定①枚举无收尾）；对局收口画面按裁定②口径自然成章（非决策面）。
