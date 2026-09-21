# 备战画面(prep · 货币战争-备战)

> 代码 = `operations/cw_screen/cw_screen_prep.py::CwScreenPrep`(编排)+ `strategies/impl/mandate_v1/bridge.py`(决策入口)+ `prep_actions.py::PrepActionExecutor`(备战执行器;部署 = DeployMove 动作,路径速查 = [deploy.md](deploy.md))。职责:一次备战画面访问的完整编排——入口观察→对账→单动作决策循环(执行→逻辑态直写),直到终结动作交回外循环。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 外循环分支 1:**双锚同帧命中**——「货币战争-备战.备战标识-购买经验」∧「货币战争-备战.按钮-出战」(`operations/cw_loop.py::CwLoop.loop` 备战分支)。overlay 半开帧下单锚可从底层透出命中,双锚同帧是防误派判据。
- 位置 = 阶段二默认分支(浮层帧由阶段一各画面身份先行接管——历史「先查备战会误派」事故见 [../flow/outer_loop.md](../flow/outer_loop.md) §2.2)。
- 本画面的浮层子态另立分支:「备战-开商店」= 开商店态三锚(在册号 0n;转交商店访问,[shop.md](shop.md));暗色锁定族 = `CwScreenPrepLockedReturn`(阶段一身份分发)。

## 2. 画面形态声明

**决策循环形态**。决策入口 = 契约 `strategies/impl/cw_strategy.py::CwStrategy.decide_prep_screen`(决策输入 = **容器 game state 直读**,零黑板——备战黑板帧已随迭代 2026-09-18-prep-obs-retirement 阶段 3.5 退役);实现链 = `strategies/impl/mandate_v1/bridge.py::decide_prep_screen`:方向代次消费 → **前置发射位 `bridge.py::_launch_front_check`**(发射决策宿主;armed 帧短路三遍编排,直接产受限商店访问意图或 `StartBattle` 终点意图)→ 预算遥测披露(`economy_cycle.disclose_budget`,非 armed 短路帧才到达)→ `bridge.py::decide_prep_frame`(三遍编排,内调 `entry.py::emit` + 帧稳定截断)。

`entry.emit` 编排序(与代码体一致):①prep 实体面(容器 bench kind 分派:bookcard→OpenBookcard / supply_box→OpenBox / tome→OpenTome,书册卡臂 = 用户裁定 2026-09-19 开卡时机归策略器,终结动作;晶矿容器域→席满让路门:席自由(free>0)照常 CollectOre,席满(free==0)按 `entry.ORE_DEFER_PROBE_K` 单探针后让路 fall-through 落后续步骤序)→ ①′ wanted 闭环消费臂(名单输入 = 容器读口派生)→ ②证明 pass(信号臂/K/stop_flag/线级状态机/换线)→ ②′ 工具消费发射位 → ③升档器求值位 → ④骨架 pass(M1-M7,`mandate.py`,板满可行性门前置)→ ⑤EV pass(criteria,臂①旁路)→ ⑥无动作 ⇒ StartBattle(备战环正常出口;armed 帧的 StartBattle 与受限访问意图由前置发射位短路本序直接产,见上方决策链)。动作词表 = emit/adapter 自有映射(`adapter.py::_OP_SPECS`),输出恰一个动作(`CwAction`;空发射 = CwActionObsParam scope='outer_loop' 交回外循环重观察——原 HoldFrame 收编,用户裁定 2026-09-20)。

## 3. 观察面

入口单次 heavy;唯一决策读屏点 = 入口对账(统一规范 = [op-layer.md](op-layer.md) §1.3):

- **环入口序列**:`_clear_entry_overlays`(残留模态一键关,清场注册表 `ENTRY_OVERLAY_CLOSE`)→ `_try_collapse_open_shop`(开商店态收起探针;店开着则走 0n/商店访问路径)→ `_observe(heavy=True)` → 帧代次标注 `gs.frame_class_prep='full'` → `obs.event_overlay` 非空即交回外循环重分发(不计数)→ 接管补采委派 `_delegate_plane_intel_if_needed`(触发谓词 = 容器无位面真值 `not gs.plane_bosses.value`;「节点条可读」守卫 = 半开帧不委派、等下轮免费重判;编排单一源 = `CwEntryPlaneIntel`([plane_intel.md](plane_intel.md)),委派结果透传——成功 = round_success 交回外循环重识别,失败 = round_fail 走外循环既有失败链,无自带计数/放弃分支)。书册卡不在入口代清(用户裁定 2026-09-19 开卡时机归策略器):识别 kind('bookcard')由观察读链识别期定 kind(``_bench_item_kind_by_slot``)进容器 bench,开卡动作由策略器 entry ① 卡片臂发射(终结动作,交回语义不变)。(幻影墓碑:「试用角色揭示卡」= 备战栏动画帧误判,2026-09-19 定谳撤销,墓碑 = `cw_identity_obs` 模块内注,禁再建模。)
- **heavy 观察消费 obs 解析工具箱**:SIFT 身份(bench/deployed)+ GameState 全量(读漏斗 `obs/cw_observation.py::read_game_state` 容器直写,观察渠道含 carry/prior/leave_screen/relay)+ cap 读取 + 装备域三路(`obs/cw_observe_full.py::observe_full` 组装单一源:owned 件名池全量/occupied 已穿明细/后排布局选档);光标 parking 先行(防 OCR/SIFT 污染)。观察产物 = **容器 game state 直写**(CwScreenPrep 观察装配点,渠道①:bench 含箱/典籍 kind 细分/deployed/equips/occupied_equips/spheres 载荷坐标/node_chain);`PrepObservation` 局部对象仅载控制信号(shop_open/substate/event_overlay),不进 gs、不进 session、不再是策略器输入(黑板已退役,迭代 2026-09-18-prep-obs-retirement 阶段 3.5)。
- **对账边界**:本屏观察写入 = ①观察态上报进 GameState 的观察边界,对账唯一发生点在此——动作落地判定 = 容器逻辑态直写 + 本帧观察覆盖(观察赢),观察侧失配记缺陷台账;容器侧比对与仲裁 = `kernel/cw_reconcile.py`(锚定/槽号健康不变量/bench 写回);本帧定型时另跑纯观察审计族 `_v2_post_frame_accounting`(羁绊显示,零决策)。
- 可信门:gold 仅 shop 开态可信(F2 门 = shop_open 现算派生,黑板 state_gold_trusted 位已退役);hp 决策消费统一经 `kernel/cw_hp_policy.py::decision_hp` 门(`cw_strategy.py::gated_hp` = 策略实现层既有调用点的薄委托)。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionDeployMoveOp`(`CwActionDeployMoveParam`) | 注册表工厂(执行器 `_dispatch_action`:`action_op_class_for` + `PrepExecEnv` 组装) | 自上报 `report_action_deploy_move_param` | 否(非终结):发出后决策环原地续跑,下一动作读容器逻辑态 |
| `CwActionSellBenchOp`(`CwActionSellBenchParam`,备战域注册行) | 注册表工厂(同上) | 自上报 `report_action_sell_bench_param` | 否(非终结)同上 |
| `CwActionSellDeployedOp`(`CwActionSellDeployedParam`) | 注册表工厂(同上) | 自上报 `report_action_sell_deployed_param` | 否(非终结)同上 |
| `CwActionLevelUpOp`(`CwActionLevelUpParam`) | 注册表工厂(同上) | 自上报 `report_action_level_up_param` | 否(非终结)同上 |
| `CwActionCollectOreOp`(`CwActionCollectOreParam`) | 注册表工厂(同上) | 自上报 `report_action_collect_ore_param` | 否(非终结)同上 |
| `CwActionOpenTomeOp`(`CwActionOpenTomeParam`) | 注册表工厂(同上) | 自上报 `report_action_open_tome_param` | 否(非终结)同上 |
| `CwActionWearEquipOp`(`CwActionWearEquipParam`) | 注册表工厂(同上) | 自上报 `report_action_wear_equip_param` | 否(非终结)同上 |
| `CwActionToolUseOp`(工具原子七类 `CwActionFurnaceUseParam`/`CwActionPrivilegeCardUseParam`/`CwActionWrenchUseParam`/`CwActionPrecisionWrenchUseParam`/`CwActionStaffProjectorUseParam`/`CwActionPerfectProjectorUseParam`/`CwActionLuckyTokenUseParam`) | 注册表工厂(同上) | 自上报 `report_action_<snake>_param` 七类各一 | 否(非终结)同上 |
| `CwActionObsOp`(`CwActionObsParam`,scope='in_place') | 注册表工厂;执行半 = 宿主 `reobserve_in_visit()` heavy 观察链重跑 | 自上报 `report_action_obs_param` | 否(非终结):帧代次标 full 后决策环原地续跑(访问/段序号不重启);重观察见事件 overlay = `CwObsOverlayBail` 交回重分发 |
| `CwActionObsOp`(`CwActionObsParam`,scope='outer_loop') | 决策环 F3 之前拦截(不进 validate/执行器/动作记录) | 无自上报(拦截型空发射) | **是(交回重观察)**:round_success 交回外循环重观察 |
| `CwActionStartBattleOp`(`CwActionStartBattleParam`) | 画面 op 执行位(`_act_execute_default` 分流 → `cw_loop.py::launch_battle_unified(face='armed')`:屏态复验→浮层检查→部署原子序→出战点击链) | 自上报 `report_action_start_battle_param`(免战跳过子态随上报携带) | **是(访问终结)**:点击序列完成即 `_terminal_exit` round_success 交回外循环战斗分支(terminal_wait=3) |
| `CwActionOpenShopOp`(`CwActionOpenShopParam`;op 本体 = terminal 承载行,正常路径不可达) | 画面 op 执行位(`_act_execute_default` 分流:普通 = `_open_shop_phase` 流程层商店编排(open_shop + `visit_open_shop`);restricted_spend = `_launch_frame_arbitration` 仲裁单元) | 无自上报(容器逻辑态推进 = 商店域各动作 op 自上报单点) | **是(访问终结)**:完整商店访问(开→买波→收店)或仲裁完成后 `_terminal_exit` round_success 交回外循环重识别(terminal_wait=1.0);仅买波失败路径店开态交回 |
| `CwActionOpenBoxOp`(`CwActionOpenBoxParam`,终结化) | 注册表工厂(执行器 `_dispatch_action`) | 自上报 `report_action_open_box_param`(零写族) | **是(访问终结)**:武装箱选择画面出现 = 新事实 → `_terminal_exit` round_success 交回外循环按该画面分发(terminal_wait=1.8) |
| `CwActionOpenBookcardOp`(`CwActionOpenBookcardParam`,终结) | 注册表工厂(执行器 `_dispatch_action`) | 自上报 `report_action_open_bookcard_param` | **是(访问终结)**:专家邀请函弹窗在场 = 新事实 → `_terminal_exit` round_success 交回外循环重分发(专家邀请函身份臂,terminal_wait=1.8) |
| 无注册表动作 op——环入口清场臂(`_clear_entry_overlays`,观察 node 序列) | 画面 op 留守臂(注册表 `ENTRY_OVERLAY_CLOSE` 逐屏锚探,命中点该屏关闭 area) | 无自上报(纯清场,零容器写) | 否(非终结):清完继续观察 node 序列 |
| 无注册表动作 op——开商店收起探针(`_try_collapse_open_shop`,观察 node 序列) | 画面 op 留守臂(点「货币战争-备战-开商店.按钮-收起」) | 无自上报 | 否(非终结):收起后继续 heavy 观察 |

单动作决策循环(`while True`,循环内零读屏——在册例外 = CwActionObs 环内重观察,见下方通道行;无防御上限——不收敛 = 策略 bug 响亮暴露,不加兜底帽):

```
action = strategy.decide_prep_screen(容器 game state 直读;
           空发射 = CwActionObsParam(scope='outer_loop') → 交回外循环重观察)
→ F3 validate(参数非法 = 拒绝执行 + 交回留证;执行前输入契约检查,非动作后判效)
→ 执行 _act_execute_default(机械执行,无成败回执,发出即职责完成;
   动作事实走各动作 op 自上报,画面 op 侧无登记面)
→ 终结判定读注册表 action_op_class_for(action).terminal(终结 → _terminal_exit 交回)
→ op 自上报 report_action_<snake>_param(动作后逻辑态唯一更新点 = 上报函数单点,
   纯计算零读屏;下一动作决策读容器逻辑态)
   (直写帧代次 = 'none':同 visit 内续动作不重复触发方向刷新;
    CwActionObs(in_place) = 'full':访问内重观察 = 新观察写点,方向重估触发同入口帧)
```

- **重观察通道(CwActionObs,scope 选口径)**:`scope='in_place'` → 注册表派发 `CwActionObsOp` → 宿主 `reobserve_in_visit()` heavy 观察链重跑(漏斗直写容器 = 重新观察上报),帧代次标 full 后**决策环原地续跑**(不交回外循环,访问/段序号不重启);重观察见事件 overlay = `CwObsOverlayBail` 抛出、决策循环捕获交回外循环重分发。`scope='outer_loop'` → 决策环 F3 之前拦截交回外循环重观察(不进执行器/动作记录;原 HoldFrame 空发射帧收编,用户裁定 2026-09-20)。通道细则单一源 = [../flow/action_exec.md](../flow/action_exec.md) §3。

- **动作全集**(备战域):OpenBox/OpenTome/OpenBookcard/CollectOre/DeployMove/SellBench/SellDeployed/WearEquip/LevelUp/OpenShop/StartBattle/Obs(环内重观察,零点击零拖拽;通道细则 = 上方「环内重观察通道」行)(组合壳 RunDeploy/RunEquip/RunTools 已随统一词表退役:部署 = DeployMove 原子序发射位逐帧现算,穿戴 = WearEquip 原子,工具 = 工具原子类经 `CwActionToolUseOp`)。词表单一源 = `kernel/cw_vocab.py::CW_ACTION_TYPES`;注册表 = `operations/cw_op/cw_action_registry.py`(SellBench/LevelUp 注册行 = 备战域 op)。
- **逻辑态直写覆盖**(上报函数族申报):有容器写语义动作 = SellBench/SellDeployed/DeployMove/LevelUp/CollectOre/OpenTome/OpenBookcard(各一上报函数,op 自上报单点);零写族 = OpenBox(终结化)/WearEquip/工具原子七类/事件线 pick 族集中在 `zero_writes.py`(消费真值归观察,截断点独占发射帧零窗口)。规则全集正本 = [../game_state/action-logic-state.md](../game_state/action-logic-state.md) + [../game_state/logic-updates/](../game_state/logic-updates/README.md)。
- 段序号置位:访问入口 `strategy_state.cw4_segment_serial += 1`(访问 = 腾席拒绝结论的输入不变性段;上一访问/上一域残留的续段 token/结论闩按序号不等自动失效)。
- 执行要点(交互陷阱):拖拽类 = 统一拖拽原语机械单发(确认 settle → hold 短拖 → 光标 parking,零判效零重试);CollectOre 批式一次全点 → 等 2s → 统一验证;LevelUp 逐帧单击至升满一级(发射面 cost = `xp_click_cost` 现算装载,失读回退 `kernel/cw_economy.py::XP_CLICK_COST_FALLBACK`)。细则 = [../flow/action_exec.md](../flow/action_exec.md)。

## 5. 终结与交回

- **StartBattle = 唯一完成态**:发射即终结交回外循环,外循环置战斗窗口(`_battle_ts` 置位 + `_battle_wait_active`,下轮战斗等待分支接管;`outer_loop.md` §4)。
- **OpenShop = 备战环终结**:执行 = 流程层商店访问编排(`_open_shop_phase` → open_shop 幂等开店 → `visit_open_shop`);受限访问(`restricted_spend`)在 `_act_execute_default` 截流走仲裁单元。访问完成后经终结出口交回外循环(文档 = [shop.md](shop.md))。
- **OpenBookcard = 终结**(2026-09-19 卡片臂策略器化):开卡即引入新事实(专家邀请函弹窗在场),交回外循环重观察;原备战环入口清场代发通道撤销,发射位 = 策略器 entry ① 卡片臂。
- **OpenBox = 终结**(终结化):开箱即引入新事实(武装箱选择画面出现),交回外循环按该画面分发选卡 op;等待时长 = 注册表 `CwActionOpenBoxOp.terminal_wait`。
- HoldFrame 通道(已收编 = CwActionObsParam scope='outer_loop',本帧无动作合法交回重观察)/ overlay 交回 / 终结动作;CwActionObs(in_place) 执行见事件 overlay = `CwObsOverlayBail` 交回重分发(画面路由归外循环);决策循环无防御上限(不收敛 = 逻辑态或策略 bug,响亮暴露,交回外循环由 stall 防线接管,不静默续跑)。
- 环让位重入契约:本 op 返回后外循环必经 return → 下轮 loop 顶全分支重判,不在同一迭代内直接回备战分支。

## 6. 状态上报面

- 动作 → 上报函数:逐动作规格见 [../game_state/logic-updates/](../game_state/logic-updates/README.md)(备战域 = `kernel/cw_action_report/<snake>.py::report_action_<snake>_param`;dict 确认族到账 = `kernel/cw_exec_state.py::apply_confirm_effect`)。
- tracked 主账随动(容器簿记 `GameState.tracked_books`,与对账无关,无策略读口);动作落地判定归观察边界对账(两态制:逻辑态直写 + 观察覆盖,失配 = 纠偏/缺陷台账,零决策不重执行);期望态暂存记账机制已随执行层状态类目退役(git 历史可溯)。

## 7. 子态与 overlay

- 子态「备战-开商店」:外循环 0n 分支转交商店访问(文档 = [shop.md](shop.md));环入口 `_try_collapse_open_shop` 收起探针兜底漏帧。
- 暗色锁定子态(策略锁定/遭遇锁定):`CwScreenPrepLockedReturn` 点右上返回按钮(此态下备战双锚仍精准命中,不先分流会被当正常备战操作读暗牌)。
- overlay 覆盖:全部 0 系 overlay 在外循环先行分流;观察段 `obs.event_overlay` 非空 = 交回重分发(双保险)。

## 8. 守卫与防线

- 安灯面已退役(原执行失败安灯,2026-09-16 裁定:动作 op 机械执行后无成败判定输入,未建档实证的故障形态不作兜底理由;细则 = [../flow/guards.md](../flow/guards.md))。
- 停机钩子 = [临时段·特殊投资策略商店停机钩子](`_spec_invest_shop_stop_hook`,挂点 = `visit_open_shop` 首部;用户 2026-09-10 指令临时捕获,采够删整段)——非备战环守卫,商店访问编排域。

## 9. 遥测与锁面

- journal op 名 = 「备战」(dispatch 包装统一落 `[cw-op]` 主日志行);0n 分键 branch_shop_open_hit / branch_shop_open_visit_ok / branch_shop_open_visit_fail;发射域分键 deploy_emit_* / deploy_exec_*;板满拒因 = cw4_counters `deploy_cap_full`(帧级去重,迭代阶段 3.1)。
- 测试锁:生命周期段迹锁、词表覆盖锁(写口两集)、部署 cap 板满门三锁等,锁面 = `sr-od-test/test/sr_od/application/currency_war/`(test_cw_deploy_cap_gate.py / test_cw_unified_action_2a.py 等;原黑板帧代次写点集契约锁随黑板退役删除)。
- game 侧知识:过渡体系/战斗机制 = [../../../../game/currency_war/research/README.md](../../../../../game/currency_war/research/README.md);画面建档 = `assets/game_data/screen_info/currency_war_battle_prep.yml`。
