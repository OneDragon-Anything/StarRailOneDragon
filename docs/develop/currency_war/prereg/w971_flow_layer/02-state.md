# 02 · 局状态收编 / 黑板模式 / 字段生命周期

> W971 分篇。总纲见 [DESIGN.md](DESIGN.md)。

## 1. 局状态 = 收编现役 StrategySession(用户拍板)

- **不新立状态对象**:StrategySession 字段已全、消费面广(遥测/对账/sim),收编避免双源迁移风险。
- 收编内容:
  1. **消灭 ctx 信箱**:简报三件(词缀/难度/boss 序)改由观察 op 直接写 session,删除 ctx 散字段(cw_briefing_*)与「取走拷贝」段;
  2. **字段更新者白名单**:session 每个字段族声明合法更新者(op/handler 名),新增写入点 = 违反架构;
  3. **遥测/对账统一读路径**:消费 session 的口径单一源。
- 边界:session 既有字段语义不动(只收编写路径,不改字段)。
- **match 生命周期前置**(对抗轮 1 代码现实 P1 补):现役 session 在 run 首帧 handle_init 才建立——BriefingOp 直写 session 要求 **match 建立前移**(进对局即建 session,先于首帧识别);P2 实施时同步迁移,否则 BriefingOp 无写目标。
- **reconcile 双输入显式化**(对抗轮 1 代码现实 P1 补):现役 reconcile_briefing_vs_plane_intel 依赖「ctx 槽(简报侧)+ session 槽(实采侧)」双轨比对;单槽黑板化后若两输入合并会对账变自比——保留两个**来源标记不同的** session 字段(briefing_bosses vs intel_bosses)供对账,「消灭 ctx 信箱」消灭的是搬运通道,不是对账的双输入语义。
- **阶段顺序修正**(对抗轮 1 P0 采纳):ctx 信箱的**删除**不随 P2(写路径收编批)——BriefingOp 在 P3 才存在,P2 删 copy 段 = 词缀/boss 链静默断流(中性退化对拍测不出)。修正:P2 期 BriefingOp 与旧 ctx 拷贝段**双写过渡**,P3 BriefingOp 稳定后删 ctx 段。

## 2. 黑板模式:决策统一读 session(用户拍板)

- **决策接口统一读 session,取消「每画面组装 obs 子集」**:
  - `decide_prep_screen(session, config)` / `decide_shop_screen(session, config)`。
  - 观察 op 读画面 → 写 session;决策读 session 出动作;遥测/对账读 session——**session 是唯一数据总线**,无搬运、无双源。
- **为什么可行(与现役同向)**:现役 `decide_prep(state, session, config)` 已是「本轮快照 + 跨轮状态」双输入,且 state 字段自带可信位(`hp_readable/hp_trusted/gold_readable`,ADR-0491 None 化、hp 新鲜度门 last_hp_t)——黑板模式下决策统一读 session,**新鲜度位原样复用**,决策侧按位保守(现状行为不变)。
- **代价与对策**:
  - 决策输入依赖隐式化 → 总纲 §4「字段 × 写者 × 读者」清单 + 决策实现 docstring 声明消费字段族;
  - 「本轮观察 vs 历史遗留」区分 → 可信位/新鲜度门(现役机制);
  - 单线程 op 顺序执行,无并发读写问题。
- **W970 接口签名变更注记**:W970 §4.1 签名与 §4.1.2「融合 obs 组装契约」由本节取代(§4.1.2 字段来源表语义转化为「观察 op 写 session 的字段清单」,仍是迁移规格)。

## 3. session 字段生命周期(黑板模式的失效管理)

session 字段按生命周期三分类,**离开产生它的画面时,画面态字段必须清理**(否则决策读到幽灵数据,如关店后残留上一波商店牌面):

| 类 | 语义 | 例 | 清理时机 |
|---|---|---|---|
| **持久知识** | 跨画面、跨轮有效 | briefing 词缀/boss 序、**refresh_probs**(等级函数,不清理,用户口述确认)、节点台账、tracked 角色 | 局终/显式覆写 |
| **画面态** | 只属于某画面的观察结果 | 商店牌 shop_cards、刷新花费——**商店关闭时清理** | 离开画面(op 完成承诺内清理) |
| **新鲜快照** | 每轮观察覆写,带可信位 | hp/gold/board/streak(readable/trusted/None 化) | 每轮观察覆写,不删只覆盖 |

- 清理者白名单:每个画面态字段的「清理 op」与「写入 op」同进白名单,禁止第三方清。
- 现役对照:快照链「每帧新建 GameState」天然无残留;黑板化后清理从「隐式(帧新建)」变「显式(完成承诺内清理)」——CloseShopOp 承诺 = 收起点击 + 1.0s 自等 + **商店族字段清理**,三者一体。

### 3.1 白名单宿主与豁免类目(对抗轮 1 代码现实 P1 修正)

- **宿主修正**:session 宿主实为 `cw_strategy_session.py`(StrategySession ~90 字段)+ `cw_state.py`(GameState)两处——白名单全量清点以两文件为准(可脚本化生成初稿,人工复核写者指派),总纲 §4 表只列「写路径收编」主字段族。
- **决策层字段族豁免类目**(新增):决策函数私有的状态字段(v3_* 族/prep_phase/defer_count/v2_round_bought 等 ~30 个,`cw_strategy_session.py:167-293`)——**写者 = 决策接口函数本身**,判据 = 「决策私有状态 vs 观察事实」二分:观察事实字段(画面读到的)归观察 op 写;决策私有字段归决策函数写;禁止跨类混写同一字段。无此豁免,黑板化会把现存决策写路径全部判违例。
- 已知遗漏族(对抗轮 1 点名,白名单补行):deploy_cap、streak、plane/round、owned 装备(equips/last_owned_equips)、bench_full_flag、active_env/megastar_char/partner_char/active_strategies(各 overlay op 写入)、_supply_refresh_used/_encounter_refresh_used(§2.13/§2.14 的「每局 1 次」状态)、投资环境台账写者、商店波 tracked 写者、备战 enemy_difficulty 通道、cw_plane_* 第二信箱族、cw_selected_difficulty——P2 实施时全量入表。

## 4. 字段 × 写者 × 读者白名单

见总纲 §4 表(本篇与总纲 §4 同源,总纲为准;此处不重复)。纪律:新增写入点 = 违反白名单;ctx 信箱字段随 BriefingOp 落地删除。

### 4.1 全量清点表(P2 落地批,脚本化清点 + 人工复核写者指派)

宿主 = `kernel/cw_strategy_session.py`(StrategySession dataclass 85 字段,清点于 P2 批)+ 少量决策私有动态属性(归 §3.1 豁免类目,见 4.2)。`cw_state.py`(GameState)为逐帧新建的快照容器,字段写者 = 观察层组装点,不逐字段列。生命周期分类 = §3 三分类(持久/画面态/新鲜快照);「环级」= Director 环入口清零的子类。

| 字段 | 生命周期 | 写者(白名单) | 主读者 |
|---|---|---|---|
| target_comp / target_drought / stash_comp / commit_signals / commit_flip_pending / focus_factions / transition_framework / dual_track_phase | 持久(轮内刷新) | 决策战略层(update_target / cw_transition) | 买/上/卖判据 / 遥测 |
| briefing_affixes | 持久 | BriefingOp 内联直写(仅空时写;ctx 信箱字段已随 P5 物理删除) | decide_encounter(mechanics_fit)/ 遥测 |
| selected_difficulty / enemy_difficulty | 持久 | 入口 establish_new_match(职级,经 ctx.cw_selected_difficulty 活通道)/ BriefingOp 直写(难度) | 难度账 / read_game_state |
| briefing_bosses | 持久 | BriefingOp 直写 / CollectPlaneIntel(实采覆写)/ prep_director 补采 | boss_fit / reconcile_briefing_vs_plane_intel(对账双输入之简报侧,**与实采侧不合并**) |
| active_env | 持久 | 投资/环境 overlay handler | 投资环境台账 |
| active_strategies | 持久 | 投资策略/环境 overlay handler | cw_intention / 决策(active_strategies 注入) |
| effect_inventory | 持久 | 升级挂点(prep_actions._level_up) | 效果清单读端 |
| chosen_megastar / chosen_partner | 持久 | 巨星/伙伴 handler | 遥测 / comp 匹配复盘 |
| megastar_candidate_clicked | handler 内 | RunMegastarNode | handler 幂等 |
| _supply_refresh_used / _encounter_refresh_used | 持久(每局 1 次门) | 补给/遭遇 handler | 同 handler |
| last_node_type / node_type_current / upcoming_types / nodeseq_probe_anchor / plane_node_table / plane_node_table_plane / plane_lengths_seen | 持久(位面切换覆写) | 节点探针(prep_director._probe_node_type,CloseShop 后挂点)/ 备战观察 | boss 判定 / 节点分发 / 遥测 |
| tracked_bench / tracked_bench_chars / tracked_deployed | 新鲜快照+累积 | 备战观察(cw_reconcile.reconcile_tracking)/ 动作登记(mutate_bench_deployed / 买牌 OCR) | 部署 / 卖守卫(sell_guard)/ 评分 |
| last_owned_equips | 新鲜快照 | EquipAll | _pseudo_state / 遥测 |
| last_hp / last_hp_t / last_hp_real / last_hp_real_node / hp_suspect | 新鲜快照(新鲜度门) | 结算观测(on_round_end)/ 备战观察(reconcile_hp,gated_hp 单一门) | 两画面决策 hp 链 |
| last_streak | 新鲜快照 | on_round_end(结算屏) | economy C 杠杆 |
| last_level_obs | 新鲜快照 | 备战观察 | 等级单调守卫 |
| last_state | 新鲜快照 | 备战观察(director._observe)/ 商店观察(buy_cards 波顶) | overlay handler 近似 / session 锚 |
| last_candidate_scores(+round) | 新鲜快照 | 决策核(_decide_shop_plan) | 遥测判读 |
| deploy_fail_counts | 持久(对账刷新) | 执行器(拖拽失败记忆) | 腾席链 a |
| launch_dead_streak | 持久 | prep_actions 出战发射 | 停机钩子(cw_launch_dead) |
| star_regression_count / star_pending_regression | 持久 | 识别防抖钩子 | 停机钩子(star 回退) |
| bail_reason_counts | 局级 | bail 交回 | ping-pong 诊断 |
| free_bench_gold_wait | 环级 | 决策(腾席链 b)/ director 环入口清零 | 链 b 等待门 |
| pending_deploys | 环级 | 旧部署意图组装 | DeployBench |
| defer_count / prep_phase / prep_phase_retry | 环级(环入口清零) | 决策函数(黑板豁免类目)+ director | 环步状态机 |
| pending_buy_expect | 单元(消费即清) | shop.py 买牌单元收尾 | PrepDirector 对账 |
| xp_expect_ledger | 持久 | PrepDirector(XpLedger) | 经验对账 |
| v3_spend_auth / v3_posture_receipt / v3_posture_unfulfilled | 帧级 | 决策预算核(attach)/ 仲裁收口(reconcile) | 预算-回执对账门 |
| **prep_obs_frame**(P2 新增) | 新鲜快照(每次备战观察覆写) | 备战观察装配点(prep_director._observe)/ 破警告派生帧 / 兼容期 decide_prep_action 薄委托 | decide_prep_screen(黑板唯一输入) |
| **shop_state_frame**(P2 新增) | 画面态(进店波顶覆写;CloseShopOp 完成承诺清理随 P3 接管) | 商店观察融合段(buy_cards.run_buy_waves 波顶)/ 兼容期 decide_prep 薄委托 / sim(独立批) | decide_shop_screen(黑板唯一输入) |
| rng / performance | 局终 | 框架(run loop 种子)/ on_round_end | 复现 / 观测反馈 |

### 4.2 决策私有豁免类目清点(P2 落地)

### 4.3 期望态与 session 统一(2026-09-02 用户定稿;P4/P3b 遵照)

**问题**:操作 op 会触发识别面之外的游戏自动变化(典型:商店购买触发 3合1 升星——合成改变前台/后台角色星级与位置,而商店开态只识别备战席占位,星级不可见)。

**机制**:操作 op 执行后,**按逻辑规则更新 session 对应字段并标记为期望态(expected)**;下次实际画面识别到该字段时,覆盖期望态为实机态(actual),**覆盖时做对账**(expected ≠ actual = 未建模游戏行为/识别缺陷/合成落点模型错——当场留证)。

**原子 op × session 影响 × 期望态清单**(全 op;「期望态字段」= 操作后按逻辑推进、待实读覆盖的字段):

| 原子 op | 直接影响 | 期望态字段 |
|---|---|---|
| BuyCard(买牌) | gold −费;bench +1(角色×星级=卡星级) | bench;**合成链**(同名同星凑3 → 升星:连锁/落点/满栏自动多买,merge_mechanics §2/§2.5);2星直出 → 金账对账暴露 |
| DeployMove(上阵/换位) | bench 源 −1;deployed 目标 +1;**拖到场上同名同星 = 合成**(星级升,装备继承) | bench/deployed/星级/已穿装备随人 |
| SellDeployed(卖上阵) | deployed −1;装备返还 owned(全额);gold +售价;board 计数 −1 | deployed/owned/gold/board |
| SellBench(卖备战) | bench −1;gold +售价(bench 件无装备) | bench/gold |
| LevelUpShop(购买经验) | gold −cost;xp +XP_PER_BUY;xp 满 → level+1(cap 可能 +1) | gold/level/xp/cap |
| RefreshShop | gold −2;shop_cards 全换(旧牌失效) | gold/shop_cards |
| ClickSpheres(奖励球) | 球消失;奖励内容未知(装备/金) | owned 或 gold 标「+奖励(待实读)」 |
| OpenBox / 补给/武装箱选卡 | 箱 −1;装备区 +1(选中装备) | owned |
| OpenTome / 秘典选卡 | 秘典 −1;+星徽/装备 | owned(星徽含阵营语义 → 分配守卫联动) |
| 列车同行星徽穿着 | 目标角色 +列车同行羁绊(add-if-absent;**同阵营装备不上**,dd-015 定谳) | board/角色羁绊标签 |
| 投资策略选卡 | 效果按 invest_effects 分类:金/XP 流→台账;机制突变→mutations;日程类(期货/联席)→日程账本 | 台账/日程账本 |
| 投资环境选卡 | 全局环境(概率/经济) | 环境登记 |
| 遭遇确认 | 进入遭遇战斗 | (战斗段由战斗等待 op 接管) |
| CloseShopOp | 商店族字段清理 | shop_cards 等(§3) |

- **期望态链跨 op 轮次(用户定稿,非 op 内批式)**:画面 op = 观察(本画面识别面)→ 调决策接口(session)→ 输出原子 op 序列 → 交回。操作(如商店购买触发 3合1)引起的 session 变化若发生在**当前画面识别面之外**(商店态看不到 bench 角色星级/身份),session 按逻辑推进并标记 expected——**后续任意轮 op 的决策都读这个期望态推进值**,直到回到能识别该字段的画面(备战识别覆盖 bench/deployed/星级/装备)才覆盖为 actual 并对账。例:商店连续多轮(刷新→再决策)之间无备战识别,合成后的 bench/星级全靠期望态链维持。
- **对账三用途**:①合成落点模型校验;②未建模游戏行为发现;③识别缺陷暴露。
- **建模范围裁剪(用户定稿)**:精确期望态只建「跨轮窗口内决策依赖的字段」——唯一刚需 = **商店多轮窗口**(合成链+金账+bench/deployed/装备区:刷新→再买连续多轮无备战识别,决策要算合成/腾席必须精确)。**单轮即回的 overlay(投资策略/补给选卡等)不做精确期望态**:选完立刻回备战,实读自然覆盖;策略效果走**台账记账**(延期兑现:金按节点到账/XP 到点),台账记「该到账什么」、实读取「实际多少」——天然对账,不逐卡硬编码 session 影响。
- **实现挂账**:期望态标记与覆盖的对账 infra(标 expected 的字段结构/实读覆盖点/diff 留证)随 P4 建机制,ops 逐个接。

写者 = 决策接口函数本身(``DecisionV2Strategy`` 族:decide_prep/decide_shop_screen/on_round_end/update_target 及其内核 arbiter/discipline/evolution/intention)。dataclass 正式字段:v2_state / locked_line / bridge_id / v2_ever_full_interest / v2_prev_hp / v2_round_key / v2_round_bought / v2_round_sold / v2_seed_bought / v3_intention / v3_evolution / v3_hoard / v3_core_names / v3_mode / v3_alarm / v3_pending_rollback / v3_prev_hp / v3_last_intention_event / v3_intention_key / v3_blood_budget_rejects / v3_blood_budget_refresh_rejects / v3_terminal_release / v3_terminal_release_plane / v3_handoff / v3_handoff_plane。另有决策函数经 setattr 写的**动态私有属性**(v2_remedy_used / v2_steady_lv_used / v3_formed_stop / v3_steady_lv_abandoned / v3_remedy_abandoned / v3_handoff_gap / v3_handoff_hp_proj / v3_release / v3_release_round / v3_release_spent / v3_phase / v3_form_ok / v3_form_score / v3_dp_posture / v3_reserve_cap / v3_reserve_overflow / v3_release_budget / v3_release_reason / v3_piggy_reward / v3_alloc_frame)——同归本豁免类目(写者=决策函数),不升正式字段(升格归遥测 schema 批)。观察事实字段与决策私有字段的二分判据见 §3.1;禁跨类混写同一字段。