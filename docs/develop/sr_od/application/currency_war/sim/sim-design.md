# 货币战争 sim 游戏后端设计（sim/ · 体系总纲）

> 性质：**设计权威版本（as-built）**——写 sim 现在就是这么设计的：结构、语义、接口契约、数据流、边界；与代码现状同步维护，架构变化才改本文。数值一律不落本文（单一源在代码常量/注册表，正文只写常量名）。
> 结构分工（本目录三篇）：本文 = 体系总纲；[sim-wiring.md](sim-wiring.md) = 容器 GameState ↔ sim 后端逐域接线底账（域粒度，接线变更改对应行）；[sim-power-model.md](sim-power-model.md) = 战斗结算机制化（战力模型）需求定义件（未实施，落地时按其重建结算层）。
> 读者 = 无会话历史的工程师/智能体。术语首次出现给定义。代码定位一律用符号锚 `文件::符号名`，路径根 = `src/sr_od/application/currency_war/`。
> 前身申报：sim 曾是「自驱动引擎」（reset/step 步进协议、策略注入式喂帧、引擎私有工作帧）；该形态已整体停用，考古走 git 历史。本文只写现值。

## 0. 术语

| 术语 | 定义 |
|---|---|
| **live** | 实机运行的 bot（operations 逐动作执行 + 遥测落盘） |
| **sim** | 单局模拟器形态的**游戏后端**：给定局级输入，按游戏规则推演一局的容器状态演化；对流程的动作与画面请求产出应答 |
| **驱动反转** | 架构裁决：真流程（外层循环 + 画面 op + 动作 op + 策略器）当驱动者，sim 退居「游戏后端」——后端不自驱动、不内嵌循环、不自当策略消费者 |
| **SimBackend** | 世界后端本体（`sim/cw_sim_backend.py::SimBackend`）：组合持有容器 + 后端私有运行时，一实例一局 |
| **容器** | `kernel/cw_game_state.py` 的 `GameState`：局内已知事实的唯一状态类型，live 与 sim 同一类型、同一份；写入走带渠道签名的写入口（渠道族封闭集 obs/logic_action/logic_hook），frozen 帧替换 |
| **上报函数族** | `kernel/cw_action_report/report_action_<snake>_param`（动作）与 `kernel/cw_screen_report/report_screen_<snake>_obs`（观察）两族具名函数：字段转移/观察落地的唯一写入口，拒绝语义在函数内 |
| **画面状态机** | SimBackend 内的呈现机：状态 = （screen_info 档名，子态载荷），答「当前在哪屏、什么可见、点击把世界带到哪」 |
| **流键** | 随机子流的键 = 模块号 + 局内坐标（如 `M05/deal/p1/r3` 发牌）；全部随机量按流键派生独立子流（§7） |
| **金路径** | sim 对局会呈现的 screen_info 档名集合（观察生成器注册表键全集，§6.4）；非金路径屏不出注册表 |
| **披露面** | 后端申报「未建模/占位口径」的键值表（`disclosures`），随局结果 unmodeled 输出；判读者据此挡外推 |
| **sim-only 差异** | sim 存在而 live 无对应物（或行为不同）的语义面，判读时须显式声明不可外推（§8.2） |

## 1. 职责与架构

### 1.1 sim 的职责

sim 是**游戏本体的单局模拟器**（「游戏后端」），不是策略评估器：按游戏规则转移状态、按机制概率产生随机量，对动作产出状态回应。策略效果的批量评估、A/B 对照、统计工具都**不在 sim 本体内**——它们是 sim 之上的外层，现不存在（§8.3 边界）。

驱动反转是本架构的根本裁决：真流程当驱动者。同一套流程代码（外层循环、画面 op、动作 op）与同一套策略器，装上后端就在 sim 世界跑，卸了就在实机跑——两形态的分叉面收敛在端口模块与操作基类覆写（§6.5）。

### 1.2 一实例一局与局级输入

`SimBackend` 一实例服务一局；构造即 reset。局级输入 = `seed: int` + `sim/cw_sim_run_config.py::RunConfig`（开局参数正典字段清单唯一汇总面：职级/难度档/环境在场等），由装配方给定——后端内不猜开局条件分布。对局类型非「标准博弈」 = 构造期显式拒绝，不猜差异。

### 1.3 与 live 的同一性

- **同一容器**：局状态 = 容器 `GameState` 单例（`kernel/cw_game_state.game_state_of(session)`），live 与 sim 同一类型、同一渠道架构。后端的世界真值写 obs 渠道，动作效果经动作 op 走 logic_action 渠道；sim 侧证据前缀 = `sim:` 族（`sim/cw_sim_base.py::sim_evidence`）。
- **同一规则核**：后端不复制任何游戏规则——数据注册表（`data/` 各表）、经济与规则核（`kernel/cw_economy.py`、`cw_shop_deal.py`、`cw_gain_chain.py` 等）、决策核（strategies/ 全族）live 与 sim 共用。规则件语义缺口 = 补 kernel（生产双端受益），禁 sim 第二份实现。
- **同一写通道**：见 §6.1 写通道三条各一。

## 2. 世界后端结构

### 2.1 组成

`SimBackend`（`sim/cw_sim_backend.py::SimBackend`）为 dataclass，**组合**持有 `gs: GameState`（禁子类——子类制造第二容器形状，Field 通道与裸属性两套状态纪律混于一体，决策输入形状随运行模式漂移）。三块内容：

1. **画面状态机**（私有态）：当前屏档名 + 子态、模态结束本次访问目标、节点窗口让路恢复位（§3）。
2. **采样簿记**（实机不可观察）：offer 全程去重集（`excluded_invest`/`excluded_env`）、overlay 队列（`sim/cw_sim_overlay.py::OverlayQueue`）、触发水位标志（`planner_fired`/`megastar_fired_tier`/`planner_seen_star`）、随机流键坐标簿记、待授予候选下标。
3. **局结果面**：`hp_trail`、`disclosures`（披露面）、`done`、幂等守卫键；`result()` 出 `sim/cw_sim_backend.py::SimRunResult`（纯结果无评判，消费方 = 运行器断言）。

### 2.2 世界规则件

世界规则的承载位置（语义单一源全在 kernel/data，sim 侧只有编排与采样注入）：

| 规则件 | 承载 |
|---|---|
| 轮首收入（常规/补给·奖励节点/败局补偿 三分支） | kernel `cw_economy.round_start_income`；后端包装 = `cw_sim_backend.apply_round_start_income` |
| 连胜转移 | `cw_sim_backend.streak_signed_after`（容器带符号连胜单账） |
| 节点经验 | `cw_sim_backend.apply_node_xp` + `NODE_XP_BY_TYPE` 表（依据 docs/game/currency_war/research/xp-rules.md） |
| 商店发牌 | kernel `cw_shop_deal.sample_shop_deal`（单一源）；后端 `deal_shop` 只做节点切换自动全刷的世界写 |
| 概率档与轮岗 | `cw_sim_backend.effective_deal_probs` + kernel `cw_battle_calib.roll_rotation_per_stage` |
| offer 采样 | `cw_sim_backend.sample_strategy_offer` / `sample_env_offer`（投资策略/环境三选一的定期投放,代码称 offer:每局固定轮次各一次;「联席决策」是投资环境之一,会在 2-6 节点追加一次投放;键形 = `offer_slots`）。品质改写型环境（时代×3/头彩/尾彩/银·金·彩）命中取卡按 `ENV_POOL_REWRITE` 按槽直取目标品质池抽样（判据 = `rewrite_slot_qualities_for_pick` 槽位向量形,2026-10-19 用户裁定批自单品质形泛化:全改写型/settled 定谳部分型 = 三槽同向量,银·金·彩 = 卡面三槽品质按位〔用户裁定卡面即真值〕;目标池吃光回退全池）。逐卡刷新呈现与世界分支 = 固定日程槽基准每卡 1 次 + `extra_pick_refreshes` 环境增量,刷新动作经上报声明 `refresh_invest_strategy`/`refresh_invest_env` 触发重掷(槽位品质承诺跨刷新保持;联席额外槽不呈现刷新——desc 未写明,保守缺位;非改写环境的刷新重掷品质 = 默认分布掷点,desc 无刷新品质语义,建模选择申报,实机对账纠偏面) |
| 战斗结算 | `sim/cw_sim_battle.py::settle_battle`（随机输出面，§8.2）+ `apply_hp_outcome`（0hp 保底/局终判定） |
| 敌人侧 | `sim/cw_sim_enemy.py`（难度基线/boss 名单 resolve） |
| 开局种子 | `sim/cw_sim_opening.py::apply_opening` |
| 节点选项生成 | `cw_sim_backend` 节点事件件（`encounter_options`/`supply_options`/`box_options`/`reward_ore_points`） |
| 词缀采样 | `SimBackend._sample_affixes`（流键 `reset/affixes`；`RunConfig.enemy_affixes` 降级为定向测试 override） |
| 特殊角色判据 | `sim/cw_sim_special.py`（planner 升星判据 `planner_overlay_due` 等） |

### 2.3 动作写入零私有语义

后端**没有私有动作转移语义**。玩家动作的世界效果由流程侧动作 op 组装并直调上报函数族承担（与实机完全同构：实机 op 怎么组装 `executed`，sim 路径同一段 op 代码同法组装）。动作随机采样分支（炉/骇客改件/晶矿/刷新等带随机的上报函数）经 `kernel/cw_action_report` 包的 `set_action_rng_provider` 拿流键 rng，注入点 = 装配函数 `sim/cw_sim_backend.py::install_backend`（键形 `action/<tool>/<序号>`，序号 = 本装配内调用序）；实机缺省 None = 未播种口径零变化。

### 2.4 确定性

后端自有采样全部由 seed 派生（`sim/cw_sim_streams.py::stream_rng` 流键，键形沿用模块号坐标系）。同 seed 同 RunConfig 的两次 reset→局终运行，容器逐位一致（确定性测试 = 测试仓首局验收测试）。

## 3. 画面状态机

### 3.1 状态与档名

状态 = （screen_info 档名，子态载荷）。档名权威 = `assets/game_data/screen_info` 各建档；代码层档名常量 = `cw_sim_backend` 的 `SCREEN_*` 常量群（备战/开商店/简报/投资环境/投资策略/补给/遭遇节点/BOSS简报/位面过渡/武装箱/专家邀请函/盛会之星/银狼升星/结算/大厅）。**子态不设独立档名**：晶矿子态（`PREP_SUB_ORE`）与开局补给等待变体（`PREP_SUB_WAIT_ONE_ONE`）= 备战档载荷，由该档名生成器内部分派观察产物（§6.4）。

### 3.2 转移源两类

1. **动作后果声明**（kernel `cw_world_decl.WorldDecl`，契约权威版本 = §6.3）：转移动作 op 经端口 `cw_sim_ports.declare_world` 喂入 `SimBackend.advance`，按 `decl.trigger` 分派世界过程/画面呈现、完成后按 `decl.next_screen` 等值对账。18 转移动作全量声明驱动：settle_confirm/supply_confirm（经 kernel `report_node_advance`）→ 节点推进；start_battle/pick_encounter → 战斗结算 → 结算页；开箱动作落地 → 武装箱画面 + 候选生成；pick 族 → 模态结束本次访问/选卡世界过程；纯转移类（开书册卡/关店/零写选卡族）→ 按 `next_screen` 推进画面。同一终结动作重复上报不二次推进 = kernel 观察态门（重复上报零推进）+ 后端逐 handler 幂等守卫。
2. **点击源**（不经声明通道的推进型点击，经端口 `click_answer` 感知）：简报下一步、BOSS 简报点空白、位面过渡点空白、补给刷新、开店。这些点击的转移语义权威源 = `docs/develop/sr_od/application/currency_war/screens/` 各篇的终结动作与返回表。

**商店牌面观察链**（点击源「开店」的观察写回语义）：牌面 = 节点级持久事实，发牌时定（节点窗口序列的商店自动全刷；实机不可观察，后端私有记录 `SimBackend._shop_record`）。开店呈现时把记录写回 `gs.shop`（模拟读屏，对偶实机「每次进店 live 漏斗重读屏写 payload」——sim 无识别面，以发牌期记录承载同一观察语义）；关店动作上报 `leave_screen` 清空 `gs.shop` 呈现不清记录；节点切换新发牌自然覆盖记录（整店锁跳过发牌 = 牌面跨节点保留，同语义）。记录跟随 = 全部驱动入口（`screen_identity`/`observe`/`visible`/`click_answer`/`advance`）懒同步在屏 payload 非空即跟随——覆盖发牌/刷新/买卡一切写点（写点与下次开店之间必经驱动入口：策略帧循环先观察后决策）。写回仅离屏态生效（在屏态保持现值零写）。

### 3.3 节点窗口序列

节点推进（终结动作触发）后的窗口序列（`SimBackend._begin_node_window`，权威序 = 旧引擎实测收尾检查序 overlay → offer → 下一节点）：

```
写 gs.node（NodeKey）+ 节点序位观察 id_mark 确认（kernel observe_node_anchor，键 =
(位面, 轮) 序位元组）
→ 轮首收入（kernel round_start_income 三分支；败局补偿支消费容器 pending_loss；
  扑满帧例外 = 收入递延至结算分支 `_resolve_battle`，基数快照仍轮初口径——
  统一公式「战败时无连胜成分」需胜负，窗口开时未知）
→ 位面开局环境金（kernel cw_investments.INVESTMENT_ENVS 结构化通道）
→ 商店自动全刷（整店锁跳过；kernel sample_shop_deal 采样）
→ overlay 队列检查（非空 → 让路呈现压住节点屏，选定后复走 offer 检查——让路不吞 offer 槽）
→ offer 日程检查（投资策略/环境定期投放——每局固定轮次各一次,「联席决策」环境在 2-6 节点追加;命中 → 呈现投资策略选卡屏）。策略延时 offer 到期检查挂日程检查之前（优先序 = 固定日程/联席槽 > 延时 offer 队列:槽在场或本窗已呈现一次 → 到点条目悬置顺延下一窗,披露键 `strategy_delayed_offer_deferred`;到点呈现定品质三选一走同一投资策略屏,刷新授权逐卡按登记 refresh_count 呈现〔0 = 不可刷 = 空授权〕,呈现即消费队列弹除,rng 流键 `M11/offer-extra/...` 与固定日程分域,呈现留证键 `strategy_delayed_offer_fired`;队列域与 live 不对称申报 = fields.md §3.2.26）。拿卡拍立即腿（登记 delay_nodes=0,白银投资首例）不辖窗首检查——挂选卡落地尾段（`_on_invest_picked` 内、模态返回之前）:弹除本拍拿卡同拍登记的 delay-0 条目并立即呈现第二选卡（经同一 report 通道重入落地,每拍至多一次）,rng 流键 `M11/offer-extra/pick/...` 分键,呈现留证键 `strategy_immediate_offer_fired`。
→ 按节点类型呈现对应屏（battle/reward → 备战档，reward = 晶矿子态；
  supply → 补给屏；encounter → 遭遇屏；boss → BOSS 简报）
```

窗口前段（收入/环境金/发牌）对同一节点只执行一次（幂等守卫键 = 节点序位 `(位面, 轮)` 元组，`SimBackend._window_begun_pos`）——位面过渡点空白等点击源可能重放收尾。窗口入口 `_enter_node_window(pos: NodePos)` 按序位键取类型（`node_sequence_of(pos[0], 场字段现值)[pos[1]-1]`）与 id_mark 确认；节点经验在节点推进时入账（被离开节点的类型）；连胜转移在战斗结算后。位面过渡 = 全继承无重置（容器直接续跑下一位面序列，`kernel/cw_node_schedule.py::node_sequence_of` 地面真值表覆盖位面 1+2+3，位面 3 = 2026-10-15 用户裁定入码；位面 3 末节点之后再推进 = 胜利终局——后继原语无后继，披露键 `DISCLOSURE_RUN_COMPLETE`）。

**策略卡羁绊条件两拍发放腿**（策略卡「激活8个羁绊并完成一场战斗后，进入节点时获得5个随机星徽」通道，不要小看我们的羁绊 id 200901 首例）：两拍分挂两处——**武装拍**在结算腿 `_resolve_battle` 策略战后腿段尾（`check_strategy_bond_battle_grants`：持卡 ∧ 战斗完成 ∧ 激活羁绊数 ≥ 表载阈值 → 容器武装标记 `strategy_bond_battle_armed` 置 True，零 rng 零采样；胜败两态共同路径，死亡局提前 return 不武装），**交付拍**在本窗多腿邻位收口段（`discharge_strategy_bond_battle_grants`：武装在场 → 星徽池采样 ×5 逐件放回入栏 → 武装消费 False；不按 kind 分叉任意窗开都查——武装事实已由结算拍锚定；挂 node_char 腿后、商店全刷前，交付物先于本窗商店发牌落位）。desc「进入节点时获得」= 发放时点在窗开非结算拍，两拍间无板面写窗（状态等值）；幂等 = 既有 `_settled_key`（武装拍）/窗口幂等守卫（交付拍）两面零新增；rng = 独立子流键 `M13/{位面}/{轮}/strategy-bond`（策略战后发放族子键式沿 ins/boss-grant 先例）；可重复无 done 闩（每场合格战斗恰获其下一窗 1 次交付）；live 零写观察覆盖（武装标记无 live 观察通道，装备入栏 = equips 观察覆盖；判读缺口 = 遥测无归因行，同族性质）。契约正本 = [gain-chain.md](../game_state/gain-chain.md) §2.16、场字段 = [fields.md](../game_state/fields.md) §3.2.26d。

**策略卡羁绊档位条件发放腿**（策略卡「<门槛羁绊>羁绊激活时，战斗中首次激活3/7/10个不同的非独立羁绊后，获得【具名装备】」通道，梦境大舞台 id 252301 首例）：**触发-发放单拍制**，单挂结算腿 `_resolve_battle` 策略战后腿段尾（羁绊条件两拍腿之后、败局待办登记前，胜败两态共同路径，死亡局提前 return 不发放）——`check_strategy_bond_tier_grants`：持卡 ∩ 登记表（`cw_investments.STRATEGY_BOND_TIER_GRANTS`）→ gate（门槛羁绊计数 ≥ 自身 tiers[0]，状态检查型，关闭期零写零闩）→ 激活非独立羁绊全集数（FACTIONS 逐族 category 过滤 + `_faction_count` 双源 max）→ 逐档首达闩（`strategy_bond_tier_fired`，'<卡名>#<档位>' 复合键）达标即 `gain_equipment(rand=False)` 具名直发。与上一腿两拍制时点语义异构（本卡「战斗中…后获得」发放时点 = 结算拍本拍，无节点窗载体句）故不共表各建各表；幂等 = 既有 `_settled_key` 零新增；**零 rng 零披露键**（具名确定发放无采样路径）；live 零写观察覆盖（星徽入栏有画面真值；判读缺口 = 遥测无归因行，羁绊条件发放族同性质）。契约正本 = [gain-chain.md](../game_state/gain-chain.md) §2.17、场字段 = [fields.md](../game_state/fields.md) §3.2.26f。

**策略卡首领战结束回血腿**(策略卡「首领战斗结束时回复50点小队生命值」通道,奋斗协议 id 301801 首例):单挂结算腿 `_resolve_battle` 策略战后腿段尾(羁绊档位腿之后、败局待办登记前,胜败两态共同路径,死亡局提前 return 不回血;挂点在结算环行与损血差分之后——+50 不污染本场环行差分与损血档位判据)——`check_strategy_boss_end_heal`(Σ 持卡 `boss_end_heal_hp`,纯读零写;kind=='boss' 门在调用方):持卡 ∧ boss ∧ heal>0 → observe hp 独立笔 + `_hp_trail_append` 成对(容器不变式②写流↔轨迹同构保持);**直加不 clip**(正部 HP 加法家族形:选卡即时腿/极·阿瓦隆获得回血同判——hp_max 字段缺位零上限消费,live 真实小队生命上限未采证经披露键 `strategy_boss_heal_hp_cap_unverified` 随局申报,证伪 → 常量改值零迁移);hp 未观察(None)= 无基座零写零追加(禁造假基座);sig = obs 族 `'sim:strategy'` 组(策略胜利金腿同组);幂等 = 既有 `_settled_key` 零新增;live 零写观察覆盖(回血后血量条真值入容器);次节点完胜结构性漏判 = `check_env_deploy_lock_perfect` 既有偏严条款辖内新事件源(方向单一偏严),披露键 `strategy_boss_heal_perfect_win_bias` 随局申报,live 结算屏显示相位(heal 前/后)未采证经披露键 `strategy_boss_heal_display_phase_unverified` 判读申报。契约正本 = [gain-chain.md](../game_state/gain-chain.md) §2.19。

**策略卡赠礼条件双腿**(策略卡「激活4【巡海游侠】时…获得…2星【黄泉】（携【星间旅人星徽】）/进入下一个奖励节点时，获得【波提欧】」通道，迷之旅人 id 253601 首例）：单挂节点窗收口段——`check_strategy_gift_grants(node_kind=kind)`，挂装备计数 XP 腿后、商店全刷前（腿1 = 羁绊人数条件任意窗评估：`deployed_bond_counts` 上阵计数 ≥ 4 发 2★黄泉 + 携徽 `gain_equipment(rand=True)` 入栏；腿2 = 节点类型条件：kind=='reward' 窗发 1★波提欧，发放物先于本窗商店发牌落席；选卡节点本窗不重查 = 「下一个」语义的结构性实现）。双登记表 = `cw_investments.STRATEGY_FACTION_COUNT_GRANTS`/`STRATEGY_REWARD_NODE_GRANTS` 白名单；封账 = `strategy_grants_done` 逐腿 '<卡名>#<腿键>' 复合键（placed 才闩，拒落自愈），幂等 = 窗口幂等守卫 + done 闩双层零新增；前置腿写端对账：直发取卡腿经获得链效果体可写板面，现序下其产出计入本窗羁绊计数（进窗快照口径，证伪路径 = 实机直发改板面同窗计数观察）；**零 rng 采样零披露键**（徽腿 rand=True 系随机态认知通道非采样）；live 零写观察覆盖（角色落席/装备入栏有画面真值）。契约正本 = [gain-chain.md](../game_state/gain-chain.md) §2.18、场字段 = [fields.md](../game_state/fields.md) §3.2.26g。

**局终声明消费分支**：kernel 终局出口为事件式（`report_node_advance` 遇 `sequence_next` 无后继 → 零写入零效果 tick，返回 `applied=True, reason='match_end'` + `WorldDecl(next_screen='')`）；`advance()` 对 `trigger='node_advance' ∧ next_screen=''` 走局终分支 = XP 入账（被离开节点的类型）+ `DISCLOSURE_RUN_COMPLETE` 胜局披露（键值 `survived_p3_boss`；hp 归零败局走结算死亡分支不经此分支 = 胜负判别单一源在披露集）+ game over 收尾，对账随后走 `done ∧ decl=''` 合格分支。kernel 声明权威、sim 对账分工不变；同 run 多条 `match_end` = 同一终局事件重复发出，`advance()` done 早退吸收。历史口径注：位面 3 入码前本分支披露 `DISCLOSURE_P3_UNOBSERVED`（键值 `enter_p3_game_over_u19`，p3_unobserved），该键已随位面 3 真值入码退役不再发射，常量保留作历史遥测语料判读身份。

**节点序列权威与场字段分发**：序列真值的单一源 = `cw_node_schedule`（默认地面真值表 + 环境修饰层）。改节点序列的投资环境（统一注册表 `ENV_NODE_REWRITE_RULES`：插入型「人身意外险」boss 前插补给 / 替换型「战争边疆」位面 3 战斗→遭遇）经 `resolve_plane_node_seqs` 在环境注册时一次性解出，由获得链尾段写进 GameState 场字段 `node_seq_by_plane`（逻辑态；字段契约与回退语义见 [fields.md](../game_state/fields.md) §3.2.1）。运行时 sim 与 kernel 同源读该字段：局终判定/进窗/窗口收尾/offer 门/节点屏呈现各消费点传场字段现值（None = 未注册回退默认表）；节点身份一律 `(位面, 轮)` 序位键直用，kind 查询经 `node_sequence_of` 直查（缺键 = 损坏半态/越界位面，异常契约统一 `PlaneSeqMissingError`）。**停用注**：sim 侧编号反解薄委托 `_ordinal_to_node`/`_node_ordinal` 已随全局节点编号表示停用删除（删壳即消解，无独立第二实现）。任一侧漏读字段 = 修饰局位面 1 轮 9 推进时 `next_screen` 声明与呈现屏确定性漂移（`DECL_SCREEN_DRIFT` 保留证据）。

### 3.4 初始序列（reset）

词缀采样入 RunConfig → 开局种子（`apply_opening`，obs 真值覆盖种子底座）→ boss 名单采样写容器（`gs.plane_bosses`）→ 整店锁/宝钻计数按现役口径写初值 → hp 轨迹首点 → 呈现简报屏（词缀 + boss 载荷已写容器）。此后：简报下一步 → （环境在场）投资环境选卡 → wait_one_one 等待变体 → 位面 1 轮 1 对应屏。进入/退出条件的权威源 = `docs/develop/sr_od/application/currency_war/screens/` 各篇。

### 3.5 until 与可见性语义

点击分支带 until 时按实机同形返回 `round_wait`（「点了≠成了」），下一轮 until 问询 = 状态机可见性（`visible`）——上报已同步转移画面，故下一轮即为转移后真值（与实机「以实际观察为准」同形，语义不降级）。可见性裁据：模态屏呈现态压住底层屏（模态族内 `_MODAL_SCREENS` 互斥）；sim 不建模的浮层，其「在场锚」area 恒不可见（`_UNPRESENTED_OVERLAY_ANCHORS` 锚门控语义）。

### 3.6 未注册屏显式报错

状态机呈现未注册屏时 `observe` = `LookupError` 具名显式报错（防静默失真——sim 不会走到的屏出现观察请求 = 接线 bug 或适用范围外屏，显式报错而非产空产物）。

## 4. overlay 触发登记层

### 4.1 机制

判据 → 容器登记 → 呈现，三段均与实机同源：

- **判据**：kernel 值回调（`kernel/cw_faction_callbacks.py`，挂 `GameState._write_logic_frame` deployed 写尾）按阵营资格集/星级事件在**逻辑写时**判定，命中即登记——sim 与实机同一份判据代码，观察写零回调（观察通道不触发）。
- **登记**：`kernel/cw_overlay_register.py` 三口（`register_screen_change` / `consume_screen_change` / `clear_screen_changes`）+ 九类登记目录（封闭集,新增类型必须登记）+ 屏档名映射（`KIND_SCREEN_NAMES`）；登记簿 = `gs.screen_changes.pending`（ScreenChanges sidecar，含逐档簿记 `wish_tiers_fired` / `planner_tiers_fired` / `fortune_battles`，生命周期 = 局）。
- **呈现**：`SimBackend._present_pending_overlay`——数据源 = 容器登记 pending；呈现位三处 = `screen_identity` 问询时点懒呈现（动作上报内登记的条目在宿主结束后的首次身份问询压上模态，等价实机「动作落地即弹」）、`advance` 纯转移尾、节点窗起点（fortune 呈现门判目标底层）。

### 4.2 目录

- **开箱 / 专家邀请函 / 星徽四选一**：动作触发——`open_box` / `open_bookcard` / `open_tome` 上报内直登（kind = `box_card` / `expert_invite` / `star_tome`，成功分支才登）；开箱的候选生成走 `report_screen_box_pick_obs` 同名通道。
- **巨星（盛会之星）**：判据 = deployed 逻辑写尾的资格集上穿（**逐次上穿即弹,无簿记去重**——ScreenChanges 侧栏簿记仅 wish/planner/fortune 三族;阈值语义源 = `data/cw_factions.py` tiers），一局可多次。
- **planner（银狼升星）**：判据 = deployed 逻辑写尾的银狼星级回调（每费用档一次，簿记 = `planner_tiers_fired`）。
- **命运卜者（占卜屋强化）**：判据 = 占卜屋 settle_confirm 上报登记；**呈现门** = 底层备战才收尾（下一节点非备战时条目存活等待）。
- **列车同行 / 祈愿试炼 / 阿哈装备**：判据/选卡上报登记；**sim 无呈现面族**（画面 op 无 sim 观察路径，呈现即卡 observe 重试）→ 懒呈现位消费 + 逐 kind 披露（披露键 = `cw_sim_overlay.OVERLAY_PARAM_PENDING:{kind}`）；partner 候选可自资格集算，待 sim 观察路径接线后再呈现。这是**数据缺口不是架构豁免**：补观察路径后逐个落呈现，架构面（登记/呈现/返回）零改动。

## 5. 容器字段判据

### 5.1 判据

实机对局中存在且可观察/影响玩法的世界事实 → `GameState` Field（双端受益）；实机不可观察的生成器采样簿记 → SimBackend 私有。**禁第三形态**（GameState 子类）。字段级规格权威版本 = `game_state/fields.md`。

### 5.2 历史多账收敛（现值单账）

引擎私有工作帧已不存在，三处历史多账的现役承载：

| 事实 | 承载 |
|---|---|
| 位面/轮次 | `gs.node`（NodeKey 单账；进节点/推进时写，与实机画面 op id_mark 确认 `kernel observe_node_anchor` 同口） |
| 选项载荷（投资环境/策略/补给/遭遇/箱/晶矿面板） | 容器各 opts/面板槽，经生成器 + `cw_screen_report` 同名上报函数送达（与实机观察同一条写通道），后端不私持副本 |
| 无符号连胜 | 容器带符号连胜派生读 `max(signed, 0)`，不设第二账 |

### 5.3 判据新增容器 Field

- `pending_loss`：败态待补偿登记（`kernel/cw_economy.py::LostNodeRef`）。写端 = 战斗结算失败分支；消费 = 轮首收入败局补偿支（口径见 kernel `cw_economy`），非 supply/reward 节点消费、败态跨轮保留至下一战斗轮。
- `shop_locked`：整店锁。v1 恒 `False`（动作类型清单无锁通道，首版恒解锁 + 披露，字段先行占位；实机写端待锁图标观察补档）。
- `diamond_count`：宝钻计数（UI 可见局内货币）。sim 写端 = 补给带钻选项落地写入（`_on_supply_picked` 按 `DIAMOND_EQUIP_NAMES` 名单从 `chosen_supply` 现值派生）；**现役失配申报**：sim 占位池的钻标挂基础件名、不命中名单 → 宝钻发放分支接线在位但不发放，激活归占位分布真实化批裁定；实机写端待补档。

## 6. 双端消费契约

### 6.1 写通道三条各一

| 通道 | 承载 | sim 写端 |
|---|---|---|
| 观察（obs 渠道） | 画面观察落地 | 生成器产物经 `kernel/cw_screen_report/report_screen_<snake>_obs` 落容器（与实机观察同一条写通道）；后端世界事实另有直接 obs 写点（`sim_evidence` 证据族，逐域清单见 sim-wiring.md） |
| 动作（logic_action 渠道） | 动作的字段转移 | 流程侧动作 op 组装后直调自己的上报函数（`report_action_<snake>_param`）——sim 与实机同一段 op 代码 |
| 节点推进 | 终结动作上报 | kernel `report_node_advance`（trigger 封闭集 {settle_confirm, supply_confirm}），sim 与实机同源 |

### 6.2 端口模块（接口契约唯一载体）

`sim/cw_sim_ports.py`——模块级装配槽 + 端口函数；缺省 `None` = 纯实机、零行为变化。端口六口（薄协议，签名不随屏数增长）：

- `screen_identity()`：后端画面状态机答当前 screen_info 档名。
- `observe(screen_name)`：生成器直出该屏 `CwScreenXxxObs` 形状产物；消费方必须经同名上报函数落容器。
- `sim_or_live_observation(screen_name, live_read)`：读屏点改道 helper（装了后端 → `observe`，否则原读链）；逐屏显式读屏点一行机械接线，是观察路径唯一的 op 触点。
- `sim_or_live_identity(screen_names, live_read)`：画面身份读点改道 helper（外循环阶段一身份分发；档名 ∈ 调用方清单才返回）。
- `click_answer(...)` / `visible(...)`：sim 点击应答（后端先按点击处理状态机转移，再出实机同形 round 结果，机械镜 = `cw_sim_ports.mirror_click_answer`）与 until/门可见性问询。
- `declare_world(decl)`：动作后果声明喂入——转移动作 op 自上报出口直调；未装配 = no-op（实机零行为变化），装配后 = 后端 `advance(decl)`，`decl is None` 本层直返（契约权威版本 = §6.3）。

装配纪律：`install_sim_backend` 进程内单装配（重复安装 raise）、`uninstall_sim_backend` 幂等、测试 teardown 必卸（模块槽是进程全局，残留跨测试泄漏）。`mechanical_io_allowed()` = 机械 IO 分支（直连 controller 点击/拖拽）可达性检查口。

### 6.3 动作后果声明（WorldDecl）

「转移动作」= 落地后世界画面/进程前进的动作（全集 18）。动作后果的出口通道 = **动作后果声明**（`kernel/cw_world_decl.py`）：转移动作的「动作落地 → 世界后果」由上报函数自产的数据承载。schema 两维：`next_screen` = 动作后确定的下一画面 screen_info 档名（`''` = 无画面，局终等未建模终态）；`trigger` = 推进分派类别（`''` = 纯画面转移，后端零专属过程）。载体 = `kernel/cw_game_state.py::LogicOutcome.world_decl`（构造义务：上报函数 `applied=True` 出口必构造；`applied=False` = None）。

不引发画面转移的世界变化（板面组成/升星等）不走独立事件通道——由容器值回调（`kernel/cw_faction_callbacks.py`）在 deployed 逻辑写尾内联判定（§4.1 判据段），零模块级钩子槽。

声明契约四条：

1. **trigger 封闭集**：单一源 = `sim/cw_sim_backend.py::ADVANCE_TRIGGER_KINDS`（advance 分派表键集），过程类含：`node_advance`（节点推进）/ `battle_resolve`（战斗结算）/ `battle_skip`（免战跳过,免战牌建模批）/ `open_box` / `pick_box_card` / `pick_megastar` / `pick_planner` / `pick_supply` / `pick_invest_env` / `pick_invest_strategy` / `pick_encounter` / `spy_shop_refresh` / `refresh_invest_env` / `refresh_invest_strategy`。准入判据 = 写端归属：上报函数/获得链已写的后果（腾位/离屏/动作直接后果）不进 trigger；只有后端专属的过程（经济结算/队列出队/候选采样/排除集簿记——实机里「游戏自己算」的部分）才进；写端全在上报侧的动作（开书册卡/关店/五类零写选卡）= `''` 纯转移。值零新词，沿用动作名。
2. **`node_advance` 的 `next_screen` 推导**：权威源 = kernel 后继原语 `sequence_next`（`kernel/cw_node_schedule.py`，带场字段现值参）+ `effective_node_pos`（`kernel/cw_game_state.py`，推进落账后的生效序位）。规则序：`sequence_next` 无后继（超出建模域）→ 局终声明事件式 `''`（`reason='match_end'`，零写入零效果 tick）→ 位面切换轮优先（`货币战争-位面过渡`）→ 新节点窗稳态屏（`window_stable_screen_now` 族：battle/reward→开商店档、supply→补给、encounter→遭遇节点、boss→BOSS 简报、1-1→备战档）。禁读容器 `gs.node` 作推导口——它是观察镜像，不随推进变。
3. **喂入契约**：转移动作 op 在自上报出口紧跟一行 `cw_sim_ports.declare_world(outcome.world_decl)`（一次动作多支上报 = 每支上报出口各自紧跟一行；round 结果 `data` 携带最后一份声明）；非转移动作 `world_decl` 恒 None，无喂入行。端口未装配 = no-op（实机零行为变化）；`decl is None` 端口层直返。
4. **消费与对账**（`SimBackend.advance(decl)`）：按 `decl.trigger` 分派世界过程/画面呈现（18 转移动作全量在表；`''` = 纯画面转移，按 `next_screen` 推进）；完成后按 `decl.next_screen` 等值对账——断言对象 = 状态机**底层稳态画面**（让路恢复位消费完、overlay 弹完后的落点屏）；建模内失配豁免三类（overlay 登记已登记 pending / offer 呈现 / 节点窗让路）断言延后至稳态补验；`next_screen=''` 预测局终，断言载体 = `done` 为真 ∧ 呈现大厅屏（局终无下一画面，不走字面等值）。断言不等且不在豁免集 = `disclosures` 缺陷保留证据不停机（声明与状态机漂移的早期警报）。`trigger` 集外值 = ValueError 显式报错（构造点漂移 = 接线 bug，禁静默）。
5. **免战跳过过程**（`battle_skip`；免战牌建模批）：声明来源 = 出战上报跳过子态分支（`kernel/cw_action_report/start_battle.py`，`next_screen` = 跳过后下一节点窗稳态屏推导 `_skip_next_screen`——规则族 = `window_stable_screen_now` 对后继序位求值;后继 None = 局终事件式空串）。世界消费 = `SimBackend._skip_battle`：零战斗面（不掷点/不掉血/无结算收入落账/无连胜转移/无环境·策略战后发放/无难度记录/无结算环帧行/无败局待办），被跳节点经验照常入账 + 镜像 `_on_node_advance` 记账段（策略卡到级金/装备腿——跳过拍 = 跨级事件拍），世界直进下一节点窗（新窗全部腿经窗口幂等守卫自动继承）；重入幂等守卫 = `_settled_key`（skip 后同节点 battle_resolve 空转零双账），后到 `node_advance` 声明经序位守卫空转。uses 递减零写（单一写端 = 上报腿）。建模假设披露键：`cw_skip_scope_battle_only_assumption`（跳过辖域 = 仅普通战斗）、`cw_skip_settlement_semantics_pending`（结算语义族待实机比对）。

### 6.4 观察生成器

`sim/cw_sim_obs_gen.py`——注册表：screen_info 档名 → `fn(backend) -> CwScreenXxxObs`。生成器从世界真值（容器 + 状态机运行时）填结构体，零截图零识别；**写通道铁律**：产物必须经 `kernel/cw_screen_report/` 同名上报函数落容器（观察口径/归一化/缺省语义单一源在 report 消费端，生成器只产数据）。金路径 13 档名（备战含晶矿子态与 wait_one_one 变体、商店、battle_wait、补给、投资环境、投资策略、简报、boss 简报、位面过渡、遭遇、开箱、巨星、planner）；非金路径屏不出注册表（§3.6 显式报错）。`PrepObservation` 控制信号（shop_open/substate/event_overlay）由生成器随观察产出。

### 6.5 流程侧接缝

- `operations/cw_operation_base.py::CwOperation`：CW operations 树唯一父类（框架 `SrOperation` 子类）。sim 装配后改写四条路径：`screenshot()`（哨兵帧，不触 controller，框架每轮自动截图无感运转）、`round_by_find_and_click_area()`（端口 click_answer + until 轮询在本层 `visible` 收尾、不重进后端——重进 = 重复触发转移）、`round_by_find_area()`（端口 visible 应答）、`park_cursor()`（静默跳过）。其余 round_by_* / screen_utils 助手一律 `super()` 透传；实机路径全部 `super()` 原样零变化。
- **直连 controller 旁路**（机械 IO 分支）：逐点加 `mechanical_io_allowed()` port 检查（sim → 机械分支静默成功，世界反应由紧随的自上报承接）；漏改路径由运行器 controller 桩兜底。
- **运行器与桩**（测试仓 `sr-od-test/test/harness/sim_backend_runner.py`）：真 screen_loader（生成器查档案点位）+ controller 桩（全接口触碰即 AssertionError，报「sim 模式触碰真实 IO」+ 调用栈）+ `sim_backend_fixture` 装配纪律包装（teardown 必卸）+ `fast_sleep` 等待旁路。sim 分支的等待参数透传丢弃（sim 世界瞬时呈现）。

### 6.6 装配点

`sim/cw_sim_backend.install_backend(backend)`：端口槽装配 + kernel 事实事件 sink 订阅（转移后果不经订阅，走声明喂入 = §6.2 `declare_world`）+ 动作随机采样 rng 提供槽注入（§2.3）；`uninstall_backend()` 幂等复位三槽。装配点 = sim 运行器（测试仓 harness）；生产实跑入口当前不存在（§8.3）。

## 7. 随机性纪律

- **流键子流**：单局 = 一个 `seed: int`；全部随机量按 `random.Random(f'{seed}#{stream_key}')` 派生子流，键形 = 模块号 + 局内坐标（世界件沿用 `Mxx/...` 坐标系，动作分支流键 = `action/<tool>/<序号>`）。禁模块间共享 rng 实例；禁策略器读 sim 流（策略自带随机时用独立流键）。
- 动机：单 rng 实例按消耗序耦合时，任何模块加/删一次采样就扰动全流；流键化后各模块随机序独立，模块规格可独立演化。
- **概率源三通道**（随机量的唯一合法来源）：①游戏内可读真值表（如 `data/cw_shop_odds.py` 的 `REFRESH_PROB`）；②已收案的机制口径（依据 docs/game/currency_war/research/ 对应篇）；③已裁定的定案值（裁定记录见对应代码行注释）。禁以 replay/语料统计分布充当机制概率。
- **可复现承诺** = `(seed, RunConfig, 注册表指纹)`。

## 8. 保真度分层与 sim-only 边界

### 8.1 保真度分层（判读外推纪律）

| 层 | 内容 | 判读口径 |
|---|---|---|
| 真代码层 | 注册表/概率表/策略本体/上报函数族 | 可直接信 |
| 机制层 | 按游戏规则建模的转移（收入/经验/发牌/获得链/状态机） | 信机制文档（docs/game/currency_war/research/） |
| 校准层 | 不可复刻面（战斗随机输出面等，随局披露） | 结论带免责，战力相关判读禁出 |
| sim-only 差异面 | §8.2 申报清单 + `disclosures` 披露面 | 禁外推 |

### 8.2 sim-only 与未建模申报（维护义务：新增面在此登记，披露键随局输出）

| 面 | 现役口径 | 判读限制 |
|---|---|---|
| 战斗结算 | 随机输出面：胜负 = 均匀伯努利（`cw_sim_battle.SIM_WIN_PROB`），败局扣血 = 区间均匀采样（`SIM_HP_LOSS_MIN`/`SIM_HP_LOSS_MAX`，以实测单次败局总扣血样本域为基准）；**普通奖励关恒胜白拿**（奖励关不需要战力 = kernel `cw_reward_node.py` 裁定权威行,后端结算分支改写 won/hp_delta,输出面 `SIM_REWARD_FREE_WIN_FACE`,M13 随机流先采后改写保持消耗恒定）；扑满关不掉血豁免（掷点保留 = 奖励有无 + 连胜账胜+1/败清零） | 战力相关判读禁出；奖励关恒胜面=结构规则非随机档（扣血采样值只对真战斗类节点有效）；机制化重建需求件 = sim-power-model.md |
| 扣血分量 | 基础伤害/进度伤害置 None 占位，随局披露不可分 | 分项判读禁出，候实机结算帧采集 |
| 击杀触发掉落 | 爆晶矿族（银 20%/金 30%/彩 45%）逐击杀触发源未建模（双端皆盲；持有局零掉落，资产面低估申报；正本 = game 侧 invest_effects.md §6 爆晶矿族行） | 持卡局晶矿掉落相关结论禁出 |
| 板面重写族 | 按面分述（正本 = `cw_effect_inventory.apply_board_rewrite` sim 语义申报段）：人力重组/大裁员出售面 = 双端同链已通（桥经获得链在 sim 局真实执行，存量锁钉死）；人力重组发牌面（2★三档随机）= 后端发牌腿已接（`cw_sim_backend.apply_strategy_pick_sell_all_deal`，判据集 = 具发牌腿语义值 `'sell_all_deal'` 派生——语义值细分防素出售卡误入，挂 `_on_invest_picked` 选卡落地拍、呈现闩防重放，授予出口 `grant_bucket_names` 派生桶，流键 `M24/sell-all-deal`）；大裁员 = 素出售无发牌面（卡文无发牌句，不入发牌判据集，sim 局零假发牌），刷腿 burst=6 经获得链登记拍发放（同链），×2 卖价修饰 = 全族缺口低估申报（退款按基础公式记，×2 施径待实采）；全员晋升替换面 = 维持 sim 零建模（全场升 1 费随机替换，穿戴装备归属未采证；其拆装扳手×2 装备腿经获得链 sim 同链生效，不属本申报面） | 替换面持卡局板面战力相关结论禁出（系统性低估）；发牌面抽名分布 = 授予出口 v0 双键假设（≥9 不约束/按名均匀），禁按实机分布外推；大裁员退款 = 基础公式低估（真实双倍价金以 live 观察为准），×2 口径闭合前禁出金面精确结论 |
| 位面 3 | 默认序列已入真值表（2026-10-15 用户裁定，单局节点条全列 + 前缀结算实证；3-4 格结算标注冲突按裁决取节点条读法），推进超位面 3 = 胜利终局（披露键 `DISCLOSURE_RUN_COMPLETE`） | 序列证据等级低于位面 1/2，后续实机位面 3 局逐格复核（plane_schedule_observed.md「位面 3 观测现状」） |
| offer 触发 | 罕见离群触发点（观测 ~1-2%，触发源未归因）不建模（披露键 `OFFER_OUTLIER_DISCLOSURE`） | 作披露面 |
| 词缀采样 | 张数/分布占位（注册表键集均匀无放回，披露键 `DISCLOSURE_AFFIX_SAMPLE`） | 词缀构成敏感结论禁出 |
| overlay 余族 | partner/expert/fate/aha/hack 评估器缺位不入队（`OVERLAY_PARAM_PENDING`） | 这些 overlay 的决策域 sim 不可测 |
| 环境经济 | 位面开局金通道已结构化生效，其余通道挂披露（`DISCLOSURE_ENV_CHANNELS`） | 其余经济通道结论禁出 |
| 装备/工具发放 | 发放空表/特权投影仪/炉拖角色模式未建模（`UNMODELED_GRANTS` 族披露键） | 装备获取轨迹 sim 不可判 |
| 合成事件覆盖面 | 角色 3 星合成事件源 = buy/gain 两生产域已覆盖（买牌上报合并连锁/获得链补给选卡·策略直发·环境发放——星星相印金腿两域可达）；**变体合成**（白衣伙伴/双龙会互用升星变体，cw_invest_data 变体行）与**投影仪复制源合成**（工具使用动作 sim 无执行面,复制不可达）不建模（边界申报本行,无独立披露键） | 变体/复制源合成的金腿与合成计数相关结论禁出（系统性低估）；live 侧实机真值不受影响 |
| 策略卡合成触发发放覆盖面 | 「合成2星2费角色时获得砂金」（砂里淘金，`STRATEGY_MERGE_GRANTS` + `check_strategy_merge_grants`）事件源 = 同一 merge facts 采集（buy/gain 四发火点与 `check_env_merge_grants` 同点并排，buy/gain 两域可达）；**变体合成**与**投影仪复制源合成**不可达边界同上行 | 同上行：变体/复制源合成的发放相关结论禁出（系统性低估）；live 侧实机真值不受影响（live 零写沿发牌族正本） |
| 策略卡晶矿开启触发发放覆盖面 | 「开启晶矿时，有50%概率获得一个低一档的晶矿」（黄晶矿工，`STRATEGY_ORE_OPEN_EFFECTS` + `check_strategy_ore_open_effects`）触发腿 = 双端同段采集上报尾部同口已建模（流键 rng = sim 世界真值/live 预测写观察覆盖自愈）；**「极低概率获得棱彩晶矿」腿零建模**（desc 无数值，API 裁定不实机查，披露键 `strategy_ore_tier_down_prism_prob_unknown` 常驻）——持有局棱彩晶矿获取量系统性低估；低一档链序（棱彩→金→蓝→灰）系推断非档案（披露键 `strategy_ore_tier_chain_inferred` 常驻，链序错 = 单档少发非错发世界写） | 持卡局棱彩晶矿获取量与低一档档位分布相关结论禁出（系统性低估）；正本 = game 侧 invest_effects.md §2 黄晶矿工行 + §6 未决知识两行 |
| sim-only 简化档 | 开局补给等待变体、晶矿面板内容占位、开箱候选占位、补给带钻槽位口径等逐键披露 | 逐键披露挡外推 |

### 8.3 不建模边界（架构边界，非缺陷）

- 批量运行 / A/B / 统计工具：不在 sim 本体内，现不存在；恢复载体 = 以后端为世界的批跑件，另批立项。
- 入口链 / 退出链：sim 从对局内起点（简报屏）开始，局终呈现大厅屏即收尾；大世界导航不在适用范围内。
- 战斗与收入校准补齐、噪声注入（对账失能补偿）、性能：不在现役适用范围。
- 战斗等待动画窗：实机时间维，sim 结算瞬时完成（呈现结算页承载流程消费链）。

## 9. 记录与回放

- **记录** = 容器统一 state 流水（`kernel/cw_state_journal.py`，live/sim 同构）；sim 不自建第二账本、无批量落盘面。
- **决策回放**（`sim/cw_replay.py`）：对历史局的容器真值帧重放商店决策，秒级看到策略改动影响了哪些决策——策略改动的先导验证通道。回放驱动器逐动作直调上报函数族推进期望态，与生产同一条转移语义。

## 10. 守恒不变量

- **牌池守恒**：剩余牌库 = 固定牌库 − 手上持有副本总数（held 由 bench/deployed 星级派生，Σ 3^(star−1)；合成不销毁，2★ 计 3 张/3★ 计 9 张）。开局手牌是派生池的首个写端，先于任何商店发牌。
- **容器不变式**：金币不出现无规则依据的负值；hp 轨迹与结算记录一致；经验等级符合规则表；局终无未消费的败态补偿登记（`pending_loss` 局终必空）。由测试仓首局验收测试校验。
- 维护义务：新增机制不变量在此登记，由对应模块的行为测试承载。
