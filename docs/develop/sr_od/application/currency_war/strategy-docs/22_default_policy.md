# 22 默认策略总述(mandate_v1 · 按画面)

> 定位:默认策略实现 mandate_v1 的**按画面行为正本**——每个时期策略会执行什么动作、按什么判据、动作落在哪个画面。本篇按用户裁定(2026-09-14,策略收缩)的目标形态书写:商店期动作面收窄为买牌/刷新/关商店,卖备战与买经验收缩至备战期决策。
> 前置阅读:[00_framework.md](00_framework.md)(哲学与约束)、[01_math_framework.md](01_math_framework.md)(数学框架)、[02_mandate_layer.md](02_mandate_layer.md)(骨架义务 M1-M7 与三层权限模型)、[04_survival_budget.md](04_survival_budget.md)(血预算)。
> 职责分界与对偶篇:**能力面**(画面机制上可做的动作全集、动作 op 映射、终结语义)= [../flow/screens-actions-capability.md](../flow/screens-actions-capability.md)(下称「能力矩阵篇」);**流程编排**(循环怎么转、访问相位、守卫)= `../flow/`。本篇只管策略面:每个画面**会**做什么。
> 判据书写纪律:形式判据只写**判据名与档名指针**,数值单一源在代码(常量名形态,禁裸值);命题 P(N) 经 `../proofs/math_proofs.md` 索引跳单篇,有验证档的注明 `proofs/validations/` 档名。术语:**骨架义务** = 不做会输的动作;**EV** = 做了更赚的优化动作(定义 = 02 §2);**备战期/商店期** = 备战画面访问段/商店开画面访问段;**部署期** = 备战画面内部署执行段(无独立建档画面,能力矩阵篇 §3.4)。

## 1. 总体形态

- 单一策略核 = mandate_v1(注册面封闭集,`strategies/impl/cw_strategy_manager.py`);策略器 = 全函数 f(期望态)→动作,永不返回 None;备战域逐帧取首项(单动作选择序),商店域恰返回一个动作。决策入口:备战 = `strategies/impl/mandate_v1/bridge.py::decide_prep_screen` → `entry.py::emit`;商店 = `strategies/impl/mandate_v1/shop.py::decide_shop_action`。
- 三层权限模型(02 §2):证明层(线选择,`mandate_v1/proof.py`)→ 骨架层(义务 M1-M7,`mandate_v1/mandate.py`)→ EV 层(优化判据,`mandate_v1/criteria/`);「不做会输」的是骨架,「做了更赚」的是 EV,「做给谁看」的是证明。
- 策略收缩(本篇目标形态,用户裁定 2026-09-14):**商店期 = 买牌/刷新/关商店**;卖备战(腾位/凑息/筹资)与买经验**只在备战期决策**。能力面不变——七动作族、商店动作 op 表与转移函数全保留(能力矩阵篇 §2);收缩只改决策提案集。判例载明见能力矩阵篇 §5 与本篇 §7。
- 决策依据的机制事实全部引用 game 侧正本(经济/经验/时序 = `docs/game/currency_war/research/economy.md`、`xp-rules.md`、`screen_flow_timing.md`;官方机制 = `data/gameplay.md`),本篇不复制数值。

## 2. 备战期(货币战争-备战)

### 2.1 思路/算法概述

备战期决策入口编排序(`entry.py::emit`,单动作循环逐帧取首项):① 备战实体面(武装箱/典籍/奖励球)→ ①′ wanted 闭环 → ② 证明 pass(线状态机/换线登记)→ ②′ 工具消费 → ③ 升档器求值位 → ④ 骨架 pass(M1-M7)→ ⑤ EV pass → ⑥ 无动作 ⇒ 出战。各面:

- **攒息规划**:守息线 g* = 饱和线(常量单一源 = `kernel/cw_economy.py::saturation_line`,息律投资局 cap 解析后同式);溢余处置 = 骨架义务 M6(金超 g* 且无整批目标时转压库卡,判据 = 02 §3 M6 行 + 11 §1 金约束门);可变现息线下界与凑息账 = P56([proofs/p56-realizable-interest-floor.md](../proofs/p56-realizable-interest-floor.md))。
- **等级节奏**:骨架义务 M3 升级日程,双臂形态(02 §3):存在性 arm1(人口位谓词,判据 = `criteria/levelup.py::pop_slot`)+ 调度门 arm2(结构守息门,判据 = `criteria/levelup.py::arm2_schedule`);支出过升级预算闸(`criteria/levelup.py::levelup_budget_gate`;命题 P71/P72,[proofs/p71-levelup-channel-budget-gate.md](../proofs/p71-levelup-channel-budget-gate.md)、[proofs/p72-full-band-budget-gate.md](../proofs/p72-full-band-budget-gate.md));整批可负担 = P48 整买纪律(`criteria/levelup.py::spend_unified`);等级帽资格闸单一源 = `kernel/cw_registry.py::level_max`;血本位支付能力检查 = `kernel/cw_economy.py::blood_xp_gate`([40]②,11 §2);血预算停追级线 = `criteria/levelup.py::level_spend_blocked`(04 §4,P21 兑现视界)。
- **凑息卖出**:金贴息线缺口时卖备战换金,档序 = P49 压缩卖回序(判据 = `criteria/sell.py::sell_for_interest`;[proofs/p49-pool-compression-ev.md](../proofs/p49-pool-compression-ev.md));卖出资格统一受装配 A 辖(`sell_gate.py::sell_exclusions`;命题族 P78,`../proofs/math_proofs.md` P78 行)+ 空板止损守卫(`sell_gate.py::empty_board_sell_blocked`)。
- **腾位运营**:备战席满挡义务买入 → M4 腾席卖最弱 1★ 垫件(判据 = `mandate.py::fuel_sell_candidates`;义务边界 = 02 §3 M4 行);席满破墙单轮(警告模态在场时破墙动作优先)归流程层(`../flow/prep_visit.md` §4)。
- **上阵/换排**:骨架义务 M1(线成员部署)与 M5(开局板面),部署计划发射门纪律 = 10 §1;列车配方底线门及其锁线豁免(判据 = `kernel/cw_deploy_logic.py::recipe_floor_holds`,10 §1 r288 行);部署期细则见本篇 §4。
- **装备与工具**:M7 骨架地板 + EV 穿戴判据(判据单一源 = `kernel/cw_equip_env.py` 求值,语义 = [18_equip_wear_semantics.md](18_equip_wear_semantics.md));工具 7 件消耗判据单一源 = `kernel/cw_equip_env.py::evaluate_tool_actions`(10 §2.1)。
- **姿态与升档器**:默认姿态 = 发展优先(00 §1);升档器(血线硬地板解锁包 + λ 顾问只升不降)= 00 §4,求值位在 ③。

### 2.2 备战期会执行的动作清单

| 动作 | 词表载体 | 触发判据(指针) |
|---|---|---|
| 上阵/换排(拖备战栏→前排/后排) | `DeployMove` / 组合 `RunDeploy` | M1/M5 + 10 §1 发射门纪律;残余补部署 P24([proofs/p24-residual-fill-dominance.md](../proofs/p24-residual-fill-dominance.md)) |
| 卖备战(腾位/凑息/筹资/换线塌缩) | `SellBench` | M4(`mandate.py::fuel_sell_candidates`)/ P49+P56(`criteria/sell.py::sell_for_interest`)/ 筹资(`criteria/sell.py::funding_support_sell`)/ 塌缩([12_line_and_intention.md](12_line_and_intention.md));资格面 = `sell_gate.py::sell_exclusions`(P78) |
| 买经验(连点「购买经验」至升一级) | `LevelUp` | M3 双臂 + 预算闸 + 整买纪律 + 等级帽 + 血本位/血预算线(§2.1 等级节奏行全链) |
| 开商店(显式/读数两形态) | `OpenShop` | 骨架/EV 需要店面时;读数开商店 = 腾席链取金真值等(`kernel/cw_prep_actions.py::OpenShop`) |
| 开补给箱/开典籍/点奖励球 | `OpenBox`/`OpenTome`/`ClickSpheres`(+`PickBoxCard`) | 实体面优先(`entry.py::emit` ①;箱选卡判据 = 13 号篇;席满让路门 = entry 席满探针段) |
| 穿装备/消耗工具 | `RunEquip`/`RunTools` | M7 + 18 号篇 + `cw_equip_env` 求值 |
| 出战 | `StartBattle` | 达标臂(`kernel/cw_launch_admission.py::readiness_launch_decision`:配方完备 + 板面承重质量,§5);序列终点 = 备战环正常出口 |

备战期不做的:闭店态无商店域动作;卖上阵件仅经部署面换血通道(§4),无独立备战卖出上阵的义务出口。

## 3. 商店期(货币战争-备战-开商店)

### 3.1 思路/算法概述

- **候选买入评估**:对店面每张牌先判类再过金约束门——件级买入判定序(六序)与 M2 义务通道语义 = [11_shop_decisions.md](11_shop_decisions.md) §1(序 1/序 2 = 骨架义务 M2,不走息律门;序 3-5 = EV 买面,判据 = `criteria/buy.py::ev_buy_candidates`/`ev_buy_veto`);合成完成买入 M2b 与核心卡支配支(C1)= 11 §1/§2 在案通道;拒因分类单一源 = `shop.py::shop_unbought_reasons`(含 P92 可实现性桶)。
- **刷新门**:路径总账形式二(判据本体 = `criteria/refresh.py::r1_commitment_account`,账项装配 = `shop.py::_r1_ledger_terms`;命题 = P40 刷新 EV 三层门 [proofs/p40-refresh-ev.md](../proofs/p40-refresh-ev.md) + 验证档 [proofs/validations/P40_VALIDATION.md](../proofs/validations/P40_VALIDATION.md),息损递推 = P47 [proofs/p47-interest-account.md](../proofs/p47-interest-account.md));期内续刷受 R2 息线熔断(`criteria/refresh.py::r2_budget` + `r2_card_reserve`;P54 [proofs/p54-r2-interest-floor.md](../proofs/p54-r2-interest-floor.md));刷前过存在性门 P92(判据 = `criteria/refresh.py::all_channel_buy_exists`,`../proofs/math_proofs.md` P92 行:全买入通道可实现集为空的帧拦刷);危机帧不变式 P36-a(`criteria/refresh.py::crisis_refresh_invariant`)先于存在性门。
- **收工判定**:「无动作可做」= 主动提案 `CloseShop`(恒可用终结,全函数契约);牌面含未识别槽(失读窗)→ 花钱动作全禁、仅关店收工(能力矩阵篇 §3.5/§4);visit 级刷新硬墙(`operations/cw_screen/cw_screen_buy_cards.py::MAX_REFRESH`)超墙后终结集降级仅关店。
- **满席腾位(收缩后目标形态)**:商店期**不卖备战**——席满而需腾位时 = 提案 `CloseShop` 离店 → 外循环交备战 → 备战期 M4 腾席卖出(§2.1)→ 重开商店(`OpenShop`)继续买。牌面持久依据:节点内关店/重开不刷新商店,跨节点才自动刷新全店(`docs/game/currency_war/research/economy.md` §2.1)——腾位往返不损失已刷牌面。
- **商店期不做**(能力面可用、策略面收缩,判例 = 能力矩阵篇 §5):卖备战(`SellBenchOp`)、买经验(`LevelUpOp`)——两者收缩至备战期(§2.2);上阵/卖上阵本就非商店画面动作面。

### 3.2 商店期会执行的动作清单

| 动作 | 词表/op 载体 | 触发判据(指针) |
|---|---|---|
| 买牌 | `BuyCard` → `operations/cw_op/cw_shop_actions.py::BuyCardOp` | 六序判类 + M2 义务 + M2b/C1 支配支 + EV 买面(§3.1 候选买入评估行) |
| 刷新 | `RefreshShop` → `cw_shop_actions.py::RefreshShopOp`(**段终结**) | 刷新门路径总账 + R2 熔断 + P92 存在性门 + P36-a(§3.1 刷新门行) |
| 关商店 | `CloseShop` → `cw_shop_actions.py::CloseShopOp`(**访问终结**) | 收工判定(§3.1);席满腾位链第一步 |

## 4. 部署期(备战画面内部署执行段)

- **选人围栏**:部署候选受围栏辖——引擎/配方体系件围栏 `DEPLOY_FENCE`(单一源 = `kernel/cw_launch_admission.py::DEPLOY_FENCE`,RECIPE ∪ ENGINE)与发射资格(`cw_launch_admission.py::offtarget_sell_allowed`);部署机按角色前后台属性拖入对应排空槽,后排布局选档单一入口 = `obs/cw_back_layout.py::select_back_layout`(能力矩阵篇 §3.4)。
- **换血卖出**:off-target 上阵件挡 target 上场时先卖腾位,victim 资格单一判定 = `kernel/cw_deploy_logic.py::swap_sell_exclusion_reason`(义务集 ∪ 新鲜度排除 ∪ 资格族);部署面换血是 M4 之外的姊妹卖出出口(语义 = 02 §7 sell 行)。
- **补齐语义**:残余补部署 P24(空槽上任意围栏认可件零支出严格优先,`math_proofs.md` P24 行);发射门纪律 = 计划空是合法稳态,发射方与执行方同源谓词判空不发射(10 §1)。
- 会执行的动作:选人上阵(`RunDeploy` 组合路径 = 部署机)、换排、换血卖出(部署机内 `SellDeployed`);未达上限确认弹窗由流程层推进(非策略决策)。

## 5. 战斗与结算期

- **出战标准**:达标臂发射核 = `kernel/cw_launch_admission.py::readiness_launch_decision`(配方完备 fp 门槛 + 板面承重质量维 `launch_board_quality_report`;推迟帧观测位与上界 = 同模块);发射帧受限消费仲裁(溢出段一次受限商店访问,预算闸拒因 = 花后金位跌破息线)归流程层(`../flow/outer_loop.md` §3 达标臂行)。
- **战斗**:自动进行,bot 无决策动作(等待+探针 = `operations/cw_screen/cw_screen_battle_wait.py`,能力矩阵篇 §3.7)。
- **结算读数**:结算屏三项(收入明细/连胜/利息)数值单一源 = `kernel/cw_economy.py` 注册表(机制与凭据 = `docs/game/currency_war/research/economy.md` §10/§11);hp 真值链 = 结算读点经新鲜度门(`strategies/impl/cw_strategy.py::gated_hp`)覆盖现读;掉血结构 = P15(授权对账表 = [04_survival_budget.md](04_survival_budget.md) §7,hp 消费唯一登记处)。
- **连败/血线响应**:非独立战斗期决策——全部折算进备战/商店判据(血预算停追级线 §2.1、危机刷新不变式 P36-a、升档器血线硬地板 00 §4);败局收入补发口径 = economy.md §11(玩家裁定),不进策略判据本体。

## 6. 事件面(overlay,pick 族)

九接口决策(投资策略/投资环境/补给/遭遇/盛会之星/伙伴/装备/命运卜者/骇入策划等)+ 武装箱四选一 + 星徽秘典 + 专家邀请函:判据规格 = [13_pick_family.md](13_pick_family.md)(逐接口,不复制);刷新建议判据 = `kernel/cw_events.py::decide_event`(P81 [proofs/p81-invest-refresh-dominance.md](../proofs/p81-invest-refresh-dominance.md);环境屏不启用刷新 = 逐槽计数现读 >0 才点,载体 = `PickEvent.refresh`/`refresh_slots`)。事件面动作(选卡/刷新/返回)与终结语义 = 能力矩阵篇 §3.2/§3.6;事件选择不占备战/商店期动作面(overlay 交回外循环分支 handler)。

## 7. 能力 vs 策略(与能力矩阵篇同一原则)

- 能力面 = 画面机制上可做的动作全集(七动作族与转移函数全保留);策略面 = 默认策略实际会做的子集。定义与记载纪律 = 能力矩阵篇 §1,两篇互为对偶:本篇读「会做什么」,能力矩阵篇读「能做什么、哪个 op 执行、何时终结」。
- **在案判例**:卖备战/买经验是商店开画面可用动作,但默认策略不在商店期做(收缩至备战期,用户裁定 2026-09-14)——能力矩阵按能力面保留两行,本篇按策略面记商店期动作清单(§3.2)不含它们。
- 收缩只发生在商店期:备战期/部署期动作集与能力面同集(对照 §2.2/§4 与能力矩阵篇 §3.3/§3.4)。

## 8. 判据指针总表(数值单一源在代码)

| 判据 | 符号锚(单一源) | 档名指针 |
|---|---|---|
| 守息线 g*(饱和线) | `kernel/cw_economy.py::saturation_line` | 02 §3 M6 / 11 §1 金约束门 |
| EV 买面候选与否决 | `criteria/buy.py::ev_buy_candidates` / `ev_buy_veto` | 11 §1 六序 |
| 拒因分类 | `shop.py::shop_unbought_reasons` | 11 §1(T-115 拒因键序) |
| 刷新门(路径总账) | `criteria/refresh.py::r1_commitment_account` | P40 + P47(`proofs/p40-refresh-ev.md`、`p47-interest-account.md`、`validations/P40_VALIDATION.md`) |
| R2 息线熔断 | `criteria/refresh.py::r2_budget` / `r2_card_reserve` | P54(`proofs/p54-r2-interest-floor.md`) |
| 刷新存在性门 | `criteria/refresh.py::all_channel_buy_exists` | `../proofs/math_proofs.md` P92 行 |
| 危机刷新不变式 | `criteria/refresh.py::crisis_refresh_invariant` | `../proofs/math_proofs.md` P36-a |
| 升级存在性 arm1 / 调度门 arm2 | `criteria/levelup.py::pop_slot` / `arm2_schedule` | P39(`proofs/p39-levelup-ev.md`)/ 02 §3 M3 |
| 升级预算闸 | `criteria/levelup.py::levelup_budget_gate` | P71/P72(`proofs/p71-levelup-channel-budget-gate.md`、`p72-full-band-budget-gate.md`) |
| 整批可负担(整买纪律) | `criteria/levelup.py::spend_unified` | P48(`proofs/p48-batch-xp-banking-ev.md`) |
| 等级帽资格闸 | `kernel/cw_registry.py::level_max` | 11 §2 |
| 血本位安全带 / 停追级线 | `kernel/cw_economy.py::blood_xp_gate` / `criteria/levelup.py::level_spend_blocked` | [40]②(11 §2)/ P21 + 04 §4 |
| M4 腾席卖出候选 | `mandate.py::fuel_sell_candidates` | 02 §3 M4 |
| 凑息卖出档序 | `criteria/sell.py::sell_for_interest` | P49 + P56(`proofs/p49-pool-compression-ev.md`、`p56-realizable-interest-floor.md`) |
| 筹资卖出 | `criteria/sell.py::funding_support_sell` | P78(`../proofs/math_proofs.md` P78 行) |
| 卖出资格统一装配 | `sell_gate.py::sell_exclusions` + `empty_board_sell_blocked` | P78 + 11 §4.1 |
| 换血卖出资格 | `kernel/cw_deploy_logic.py::swap_sell_exclusion_reason` | 02 §7 sell 行(姊妹出口) |
| 部署围栏 / 配方底线门 | `kernel/cw_launch_admission.py::DEPLOY_FENCE` / `kernel/cw_deploy_logic.py::recipe_floor_holds` | 10 §1(r288 行) |
| 残余补部署 | P24 判据(发射面) | `proofs/p24-residual-fill-dominance.md` |
| 出战达标门 | `kernel/cw_launch_admission.py::readiness_launch_decision` | `../flow/outer_loop.md` §3 达标臂行 |
| 事件刷新建议 | `kernel/cw_events.py::decide_event` | 13 号篇 + P81(`proofs/p81-invest-refresh-dominance.md`) |
| 机制数值注册表 | `kernel/cw_economy.py`(XP_PER_BUY/XP_TO_NEXT_LEVEL/REFRESH_COST_BASE/sell_refund)、`data/cw_shop_odds.py`(REFRESH_PROB/POOL_COPIES_PER_CARD/expected_refreshes_for_card) | `docs/game/currency_war/research/xp-rules.md` §2、`economy.md` §2/§3(凭什么信) |
