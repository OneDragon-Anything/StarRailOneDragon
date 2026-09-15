# 备战画面(prep · 货币战争-备战)

> 代码 = `operations/cw_screen/cw_screen_prep.py::CwScreenPrep`(编排)+ `strategies/impl/mandate_v1/bridge.py`(决策入口)+ `prep_actions.py::PrepActionExecutor`(备战执行器)+ `operations/cw_screen/cw_screen_deploy.py`(部署机)。职责:一次备战画面访问的完整编排——入口观察→对账→单动作决策循环(执行→逻辑态直写),直到终结动作交回外循环。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 外循环分支 1:**双锚同帧命中**——「货币战争-备战.备战标识-购买经验」∧「货币战争-备战.按钮-出战」(`operations/cw_loop.py::CwLoop.loop` 备战分支)。overlay 半开帧下单锚可从底层透出命中,双锚同帧是防误派判据。
- 位置 = 阶段二默认分支(浮层帧由阶段一各画面身份先行接管——历史「先查备战会误派」事故见 [../flow/outer_loop.md](../flow/outer_loop.md) §2.2)。
- 本画面的浮层子态另立分支:「备战-开商店」= 0n(转交商店访问,[shop.md](shop.md));暗色锁定族 = 0m(`CwScreenPrepLockedReturn`)。

## 2. 画面形态声明

**决策循环形态**。决策入口 = 契约 `strategies/impl/cw_strategy.py::CwStrategy.decide_prep_screen`(黑板 = `session.prep_obs_frame`,缺失即抛错,禁静默按空观察决策);实现链 = `strategies/impl/mandate_v1/bridge.py::decide_prep_screen` → `bridge.py::decide_from_turn`(纯函数)→ `entry.py::emit`。

`entry.emit` 编排序(与代码体一致):①prep 实体面(boxes→OpenBox / tomes→OpenTome / spheres→席满让路门:席自由(free>0)照常 ClickSpheres,席满(free==0)按 `entry.SPHERE_DEFER_PROBE_K` 单探针后让路 fall-through 落后续步骤序)→ ②证明 pass(信号臂/K/stop_flag/线级状态机/换线)→ ③升档器求值位 → ④骨架 pass(M1-M7,`mandate.py`)→ ⑤EV pass(criteria,臂①旁路)→ ⑥无动作 ⇒ StartBattle(备战环正常出口)。动作词表 = emit/adapter 自有映射(`adapter.py::_OP_SPECS`),输出 `list[PrepAction]`——单动作循环取**首项**消费(逐帧取首项 = 单动作选择序)。

## 3. 观察面

入口单次 heavy;唯一决策读屏点 = 入口对账(统一规范 = [op-layer.md](op-layer.md) §1.3):

- **环入口序列**:`_clear_entry_overlays`(残留模态一键关,清场注册表 `ENTRY_OVERLAY_CLOSE`)→ `_clear_prep_cards`(书册卡开卡即交回:0k 分发选卡,弹窗帧禁 heavy 读)→ `_try_collapse_open_shop`(开商店态收起探针;店开着则走 0n/商店访问路径)→ `_observe(heavy=True)` → 帧代次标注 `session.prep_frame_class='full'` → `obs.event_overlay` 非空即交回外循环重分发(不计数)→ 接管局补采 `_takeover_collect_if_needed`(`session.briefing_bosses` 空 ∧ 节点条可读 → 位面详情情报采集,2 次失败放弃)。
- **heavy 观察消费 obs 解析工具箱**:SIFT 身份(bench/deployed)+ GameState 全量(读漏斗 `obs/cw_observation.py::read_game_state` 容器直写,观察渠道含 carry/prior/leave_screen/relay)+ cap 读取 + 装备域三路(`obs/cw_observe_full.py::observe_full` 组装单一源:owned 件名池全量/occupied 已穿明细/后排布局选档);光标 parking 先行(防 OCR/SIFT 污染)。观察 payload = `kernel/cw_prep_actions.py::PrepObservation`,写黑板 `session.prep_obs_frame`(写者白名单 = 入口观察段/循环逻辑态直写步;读者 = decide_prep_screen)。
- **对账边界**:本屏观察写入 = ①观察态上报进 GameState 的观察边界,对账在此发生——上一访问逐动作暂存的期望态记账(`exec_state_of(session).cw_prep_pending_accts`)在本帧定型时统一 `_v2_post_frame_accounting` 消费后清空;容器侧比对与仲裁 = `kernel/cw_reconcile.py`(锚定/槽号健康不变量/bench 写回)。
- 可信门:gold 仅 shop 开态可信(`obs.state_gold_trusted = obs.shop_open`,关态读空);hp 决策消费统一经 `kernel/cw_hp_policy.py::decision_hp` 门(`cw_strategy.py::gated_hp` = 策略实现层既有调用点的薄委托)。
- light 形态(轻字段每步现读)为兼容形态,生产无调用方。

## 4. 动作面

单动作决策循环(`for _vi in range(VISIT_ACTION_CAP)`,循环内零读屏):

```
action = strategy.decide_prep_screen(session, config) 取首项(空批合法 → 交回外循环重观察)
→ F3 validate(参数非法 = 拒绝执行 + 交回留证;执行前输入契约检查,非动作后判效)
→ 期望态记账构造(SellBench/DeployMove → drag_expect;SellDeployed → equip_expect;
   DeployMove/SellDeployed → deployed 计数前后拍)
→ 执行 _act_execute(机械执行,无成败回执,发出即职责完成;
   落地登记注册表在发射点统一触发——单一发射口,发射即触发)
→ acct 暂存 exec_state.cw_prep_pending_accts(对账归下一入口时点)
→ 终结判定读注册表 action_op_class_for(action).terminal(终结 → _terminal_exit 交回)
→ 逻辑态直写 _project_prep_obs(纯计算零读屏)→ 黑板推进,下一动作决策读逻辑态
   (直写帧代次 = 'none':同 visit 内续动作不重复触发方向刷新)
```

- **动作全集**(备战域):OpenBox/OpenTome/ClickSpheres/DeployMove/SellBench/SellDeployed/WearEquip/LevelUp/OpenShop/StartBattle(组合壳 RunDeploy/RunEquip/RunTools 已随统一词表退役,批2b R2:部署 = DeployMove 原子序发射位逐帧现算,穿戴 = WearEquip 原子,工具 = 工具原子类经 ToolUseOp)。词表单一源 = `kernel/cw_vocab.py::CW_ACTION_TYPES`;注册表 = `operations/cw_op/cw_action_registry.py`(SellBench/LevelUp 注册行 = 备战域 op)。
- **逻辑态直写覆盖(R9 全覆盖)**:词表逐动作有逻辑态分支(规则全集正本 = [../game_state/action-logic-state.md](../game_state/action-logic-state.md) + [../game_state/logic-updates/](../game_state/logic-updates/README.md));「未建模 → 返回 None 保守回退」分支已删除,词表外类型 = AssertionError 响亮暴露(注册表同款纪律)。
- 段序号置位:访问入口 `strategy_state.cw4_segment_serial += 1`(访问 = 腾席拒绝结论的输入不变性段;上一访问/上一域残留的续段 token/结论闩按序号不等自动失效)。
- 执行要点(交互陷阱):拖拽类 = 统一拖拽原语机械单发(确认 settle → hold 短拖 → 光标 parking,零判效零重试);ClickSpheres 批式一次全点 → 等 2s → 统一验证;LevelUp 备战连点至升一级(单击价现读,缺读兜底 `kernel/cw_economy.py::XP_CLICK_COST_FALLBACK`)。细则 = [../flow/action_exec.md](../flow/action_exec.md)。

## 5. 终结与交回

- **StartBattle = 唯一完成态**:发射即终结交回外循环,外循环置战斗窗口(`_battle_ts` 置位 + `_battle_wait_active`,下轮战斗等待分支接管;`outer_loop.md` §4)。
- **OpenShop = 备战环终结**:显式开店(read_only=False)交商店访问编排;read_only 读数开店后交回重识别。
- 空批 / overlay 交回 / 访问动作数达上限(VISIT_ACTION_CAP;防御:决策循环不收敛 = 逻辑态或策略 bug,交回外循环由 stall 防线接管,不静默续跑)均合法交回;每轮外循环重识别保证稳定性。
- 环让位重入契约:本 op 返回后外循环必经 return → 下轮 loop 顶全分支重判,不在同一迭代内直接回备战分支。

## 6. 状态上报面

- 动作 → 转移函数腿:逐动作规格见 [../game_state/logic-updates/](../game_state/logic-updates/README.md)(备战域 = `kernel/cw_game_state.py::apply_prep_action_logic`;效果账 = `kernel/cw_exec_state.py::apply_op_effect`)。
- 执行侧 tracked 账随动(执行簿记,与对账无关,无策略读口);期望态记账(acct 族)在下一入口 heavy 帧消费对账,失配 = 纠偏/缺陷台账,零决策不重执行。

## 7. 子态与 overlay

- 子态「备战-开商店」:外循环 0n 分支转交商店访问(文档 = [shop.md](shop.md));环入口 `_try_collapse_open_shop` 收起探针兜底漏帧。
- 暗色锁定子态(策略锁定/遭遇锁定):0m 分支 `CwScreenPrepLockedReturn` 点右上返回按钮(此态下备战双锚仍精准命中,不先分流会被当正常备战操作读暗牌)。
- overlay 覆盖:全部 0 系 overlay 在外循环先行分流;观察段 `obs.event_overlay` 非空 = 交回重分发(双保险)。

## 8. 守卫与防线

- 执行失败安灯:购买单元收尾分类器(`_spend_unit_close` + `_exec_fail_hook_check`,分类器 = `run_state.py::exec_fail_should_stop`),每局最多停一次(guards.md §4)。

## 9. 遥测与锁面

- journal op 名 = 「备战」(dispatch 包装统一落 `[cw-op]` 主日志行);0n 分键 branch_shop_open_hit / branch_shop_open_visit_ok / branch_shop_open_visit_fail;发射域分键 deploy_emit_* / deploy_exec_*。
- 测试锁:黑板帧代次写点集契约锁、生命周期段迹锁等,锁面 = `sr-od-test/test/sr_od/application/currency_war/`(test_cw_blackboard.py 等)。
- game 侧知识:过渡体系/战斗机制 = [../../../../game/currency_war/research/README.md](../../../../game/currency_war/research/README.md);画面建档 = `assets/game_data/screen_info/currency_war_battle_prep.yml`。
