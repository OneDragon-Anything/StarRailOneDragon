# 22 备战画面策略面(prep screen)

> 画面 = 货币战争-备战(建档 `assets/game_data/screen_info/currency_war_battle_prep.yml`);**能力面**(游戏可用动作全集/op 映射/终结语义)= [../screens/README.md](../screens/README.md) §5.3。本篇 = 该画面的**策略面**:策略思路概述 + 会执行的动作清单(按用户裁定 2026-09-14 策略收缩后的目标形态)+ 形式判据指针。
> 判据本体的唯一现行家 = 既有编号篇,**引用不重复**:部署/装备/腾席判据 = [10_prep_decisions.md](10_prep_decisions.md);骨架义务 M1-M7 = [02_mandate_layer.md](02_mandate_layer.md);血预算 = [04_survival_budget.md](04_survival_budget.md);装备穿戴语义 = [18_equip_wear_semantics.md](18_equip_wear_semantics.md);换线 = [12_line_and_intention.md](12_line_and_intention.md)。数值单一源在代码(常量名形态)。流程编排 = `../flow/prep_visit.md`。

## 1. 策略思路/算法概述

决策入口 = `strategies/impl/mandate_v1/bridge.py::decide_prep_screen` → `entry.py::emit` 三遍编排,单动作循环逐帧恰取一个动作(接口返回 `CwAction | None`,`None` = 本帧无动作交回外循环重观察):① 备战实体面(武装箱/典籍/奖励球)→ ①′ wanted 闭环 → ② 证明 pass(线状态机/换线登记)→ ②′ 工具消费 → ③ 升档器求值位 → ④ 骨架 pass(M1-M7)→ ⑤ EV pass → ⑥ 无动作 ⇒ 出战(备战环唯一完成态)。各面:

- **攒息规划**:守息线 g* = 饱和线(常量单一源 = `kernel/cw_economy.py::saturation_line`);溢余处置 = 骨架义务 M6;可变现息线下界 = P56(`../proofs/p56-realizable-interest-floor.md`)。
- **等级节奏**:骨架义务 M3 双臂(存在性 arm1 + 调度门 arm2),支出过升级预算闸(P71/P72)、整批可负担(P48 整买纪律)、等级帽资格闸(`kernel/cw_registry.py::level_max`)、血本位支付检查(`kernel/cw_economy.py::blood_xp_gate`)与血预算停追级线(04 §4)。
- **凑息卖出**(商店期收缩后的备战期承接口):金贴息线缺口时卖备战换金,档序 = P49(`../proofs/p49-pool-compression-ev.md`);资格统一受装配 A 辖(`sell_gate.py::sell_exclusions`,P78)+ 空板止损守卫(`sell_gate.py::empty_board_sell_blocked`)。
- **腾位运营**:备战席满挡义务买入 → M4 腾席卖最弱 1★ 垫件(`mandate.py::fuel_sell_candidates`);席满破墙单轮归流程层(`../flow/prep_visit.md` §4)。商店期席满腾位链的「备战卖」一步落在本画面(见 [23_shop_screen.md](23_shop_screen.md))。
- **上阵/换排**:骨架义务 M1(线成员部署)/M5(开局板面),发射门纪律 = 10 §1;部署执行段细则 = [24_deploy_segment.md](24_deploy_segment.md)。
- **装备与工具**:M7 骨架地板 + EV 穿戴(18 号篇);工具消耗判据单一源 = `kernel/cw_equip_env.py::evaluate_tool_actions`。
- **姿态与升档器**:发展优先默认(00 号篇 §1);升档器(血线硬地板 + λ 顾问只升不降)= 00 号篇 §4。

## 2. 会执行的动作清单(收缩后目标形态)

| 动作 | 词表载体 | 触发判据(指针) |
|---|---|---|
| 上阵/换排(拖备战栏→前排/后排) | `DeployMove`(原子序,发射位逐帧现算) | M1/M5 + 10 §1 发射门纪律;残余补部署 P24(`../proofs/p24-residual-fill-dominance.md`) |
| 卖备战(腾位/凑息/筹资/换线塌缩) | `SellBench` | M4(`mandate.py::fuel_sell_candidates`)/ P49+P56(`criteria/sell.py::sell_for_interest`)/ 筹资(`criteria/sell.py::funding_support_sell`)/ 塌缩(12 号篇);资格面 = `sell_gate.py::sell_exclusions`(P78) |
| 买经验(连点「购买经验」至升一级;商店期收缩后的唯一买经验期) | `LevelUp` | M3 双臂 + 预算闸 + 整买纪律 + 等级帽 + 血本位/血预算线(§1 等级节奏行全链) |
| 开商店(显式/读数两形态) | `OpenShop` | 骨架/EV 需要店面时;读数开商店 = 腾席链取金真值等(词表载体 = `kernel/cw_vocab.py::OpenShop`) |
| 开补给箱/开典籍/点奖励球 | `OpenBox`/`OpenTome`/`ClickSpheres` | 实体面优先(`entry.py::emit` ①;箱选卡判据 = 13 号篇;席满让路门 = entry 席满探针段) |
| 穿装备/消耗工具 | `WearEquip`/工具原子类(经 `ToolUseOp`) | M7 + 18 号篇 + `cw_equip_env` 求值 |
| 出战 | `StartBattle` | 达标臂(`kernel/cw_launch_admission.py::readiness_launch_decision`);备战环正常出口(唯一完成态,详见 [26_battle_settlement.md](26_battle_settlement.md)) |

备战期不做的:闭店态无商店域动作;卖上阵件仅经部署面换血通道([24_deploy_segment.md](24_deploy_segment.md)),无独立备战卖出上阵的义务出口。

## 3. 能力 vs 策略

备战期动作集与能力面同集(策略收缩只发生在商店期,对照 [../screens/README.md](../screens/README.md) §5.3 与 [23_shop_screen.md](23_shop_screen.md) §3);原则定义 = [../screens/README.md](../screens/README.md) §1。
