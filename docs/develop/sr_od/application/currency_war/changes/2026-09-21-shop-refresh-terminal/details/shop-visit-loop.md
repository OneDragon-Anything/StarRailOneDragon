# 商店访问新形态(详设)

## 问题与约束

- 边界:动 `operations/cw_screen/cw_screen_buy_cards.py`、`operations/cw_op/cw_refresh_shop_action.py`、`operations/cw_op/cw_shop_action_ops.py`、`operations/cw_screen/cw_screen_prep.py`(`visit_open_shop`/`_open_shop_phase`/`_act_execute_default`)、`operations/cw_loop.py`(仲裁段退役)、`kernel/cw_game_state.py`(free_refresh_left Field/两发放桥)、`kernel/cw_action_report/refresh_shop.py`(free 腿 + 随机态腿)、`kernel/cw_effect_inventory.py`(字段退役)、`kernel/cw_launch_arbitrage.py`(消费面调整)、`kernel/cw_vocab.py`(restricted_spend 退役)、`kernel/cw_prep_expect.py`(crop 退役)、`strategies/impl/mandate_v1`(受限会话自限)、`obs/cw_observation.py`(`new_bench_slots` 退役;节点行写点宿主 = `cw_screen_prep._write_prep_node_chain` 消费侧,漏斗侧识别零新增)、`kernel/cw_shop_deal.py`(新,采样器)。不碰:策略判据数学、`probe_node_type` 识别与写点实现(宿主迁移)、`guard_proposal_vs_expected` 守卫、`decision_frame_hooks.save_decision_frame` 接口、节点推进上报族。路径根 = `src/sr_od/application/currency_war/`。
- 总纲划给本篇的接口契约:免费刷新次数 Field(§2.3)、构造签名与调用点交接面 + 发射帧受限消费迁策略侧(§2.2/§2.10)、CloseShop 执行位归属(§2.1)、上报回调腿(§2.9)、节点行归位(§2.8)。路径根 = `src/sr_od/application/currency_war/`。

## 方案

### 2.1 访问形态逐拍

**观察 node(is_start_node;每访问恰一次)**:

1. `cw_match` 缺席(独立单跑)→ 兜底建核(`discard_stale_match_container` + `establish_new_match`,现 `run_buy_waves` 顶部逻辑原样迁入)。
2. `time.sleep(0.3)` + `park_cursor`(现值不变)→ `_shop_entry_read`(**读 + 未识别卡停机闸两段,单次读零防抖**;停机闸判据/处置不变,guards.md §3)。
3. `CwScreenShopObs` 镜像挂实例属性 (不变)。
4. 段首簿记迁入本 node(visit 边界 = op 边界,现 `run_buy_waves` 段顶逻辑等价搬运):`cw4_segment_serial += 1`(T-82 visit 输入不变性段);帧代次 `frame_class_shop = 'full'`(§2.6);预算披露覆写 `disclose_budget_at_shop_frame`;入口观察漏斗自带**刷新次数观察锚定**(§2.3 观察写端,漏斗 shop-open 段内,op 零额外调用);state 行日志(gold/hp/lv/plane/round/node/board/target/fp/bench,现段顶行原样);`save_decision_frame(op, 'shop_entry', 帧)`(每访问一帧)。
5. round_success 进决策动作 node。

**决策动作 node(round_wait 循环;每轮;全动作统一路径,零特例拦截,零闸)**:

1. `decide_shop_action()`(终态零参口,容器零参读;异常留证后上抛,现口径不变)。受限消费政策 = 策略侧自限(§2.10):决策入口读 StrategyState 自身限制发射值域,flow 零闸零拦截。
2. CloseShop 且 `tracked_unobserved` → `_note_shop_skip_unobserved` 留痕/连续跳过熔断不变(熔断 = round_fail 交兜底链);留痕后**照常走统一执行路径**(未观察跳过 = 零消费动作,仅执行关店离店,备战环 heavy 观察锚定后再进店)。
3. 守卫 `guard_proposal_vs_expected(action, 容器)` 不变(炸出 = 策略器 bug)。
4. 注册表类级解析 + `ShopExecEnv` 组装 + execute——**含 CloseShop**(执行位 = 真点击,见下)。
5. 逐动作簿记:`apply_action_outcome`、`accrue_release_spent`、`cw4_frame_action_record` 续段 token(T-82)不变;`note_shop_action_receipt` 对 CloseShop **跳过**(「终结不入 decisions 行」契约不变);CloseShop 的执行事实回执由动作 op 自身承担(现编排壳 `_note_receipt` 语义迁入 execute)。
6. 终结判定读注册表 `action_op_class_for(action).terminal`:False → round_wait(帧不消费,零读屏);True(RefreshShop/CloseShop)→ round_success(**访问终结,交回外循环**;零额外动作——节点行观察已归备战观察域,§2.8,商店域零探针)。
7. 访问动作日志行(`plan=…`,现段尾行语义)随轮累积,交回前 log;round_success 回执 detail = 执行账汇总串(现口径)。

**CloseShop 执行位(动作 op 真机械执行;「拦截 + no-op + 编排壳代点」旧形拆除)**:

- `CwActionCloseShopOp` 执行体 = ①帧上找「按钮-收起」:miss = 店已关(幂等,无动作可发)→ exec 回执 applied=false + `report_action_close_shop_param`(leave_screen 清场,已关残留同样清)+ round_success;②命中 → 点击 + 固定等待 `SHOP_CLOSE_ANIM_S` + exec 回执 applied=true + `report_action_close_shop_param` + round_success。零转移验证(收起消失与否归下一帧观察;点击未生效 = 外循环 0n 重分发自然重派,重派即重试)。
- `CwOpCloseShop` 编排壳**退役删除**:其存在理由(波机时代动作 op 不执行、壳代点)随执行位收编消亡,留壳 = 第二个摆设壳;幂等两出口语义逐位迁入执行体。分型表/完备锁面随正本更新调整。

### 2.2 生产调用点改造

> 注:本篇 `CwScreenShop` = 正名前名。用户裁定正名:类 → `CwScreenShop`、文件 → `cw_screen_shop.py`、op_name → 「货币战争-商店」;落地阶段 3.5 以语义重命名执行,测试/文档锚随批同步。

| 调用点 | 现状 | 改后 |
|---|---|---|
| `cw_screen_prep.py::visit_open_shop`(0n 转交与显式开店同口) | `run_buy_waves(self, match)` → `close_shop(self)` → `probe_node_type(self)` | 显式开店路径先 `open_shop(self)`(幂等,不变)→ 构造 `CwScreenBuyCards(self.ctx)` 并 run → 读取回执记访问账;关店已收编进 op,节点行观察归备战观察域(§2.8);`_open_shop_phase` 收编为唯一开店路径,restricted_spend 截流分支随 §2.10 退役 |
| `cw_loop.py` 发射帧仲裁段(≈:515-590) | spend_gate 闭包 + 带闸波循环 + 无条件关店 + 发射 | **整段退役**(§2.10:受限消费迁策略侧自限)——商店访问只剩普通路径,发射走备战分支正常决策 |
| `run_operation` 单跑 | 类自持两 node | 不变(兜底建核已迁观察 node) |

- `run_buy_waves` 函数删除;`pre_entry` 替身缝删除。
- **出参交接契约**(替代现役 `(rr, ledger)` 元组):op 实例暴露 `ledger` 属性(`ShopVisitLedger`,run 完成后有效);调用方失败判定 = `run()` 结果 `is_success`(False = 未识别卡停机/未观察熔断的 round_fail,abort 语义与现役 `_rr is not None` 同型);executed 计数消费源 = `op.ledger.total_buy/total_xp_buy/total_refresh`(备战编排回执/zero-consume 分键改此处读)。
- `cw_screen_buy_cards` 模块属性替身缝(`read_gold_opt`/`read_shop_cards` 的 noqa re-export)删除:消费方 = 刷新 op 读屏(随 §2.4 亡);测试桩改 `cw_observation.read_game_state`(先例 = test_cw_game_state 的漏斗桩)。

### 2.3 免费刷新次数:GameState Field(观察锚定 + 动作扣减 + 发放登记同格)

**载体裁定(用户裁定)**:次数载体升格为 GameState **Field** `gs.free_refresh_left`(int,剩余语义,命名随 op-layer §1.4 `*_refresh_left` 家族;None = 未观察)——**不落效果账本 int**。§1.4/§4 为投资两屏/遭遇定的 Field 模式,商店域**接入**(非例外),正本更新落申报行。

**三写端(同一格)**:

- **观察锚定(新增消费端)**:入口观察漏斗 shop-open 段**复用现役** `read_shop_refresh_button` 调用产物(`obs/cw_observation.py:2700`,现消费 `_btn.price` 写 `gs.shop_refresh_cost`),新增 `gs.observe(gs.free_refresh_left, 值, sig=_sig_read)`,零新增读屏。双态口径:free=True → 锚 `free_remaining`;free=False(付费域可读,含耗尽/灰态,游戏规则 ⇒ 免费余量恒 0)→ 锚 0;free=None(整帧判不出)→ 跳写(宁缺勿造)。**失配对账 = Field 机制白送**:observe 覆盖 logic 失配走既有 `cw_mismatch_policy` 安灯,零手写台账。
- **动作上报扣减(逻辑态,用户裁定)**:`report_action_refresh_shop_param` 内 `gs.write_logic(gs.free_refresh_left, max(0, left−1), produced_by='CwActionRefreshShopParam', evidence='proj_refresh_free_left')`;free 判定 = `gs.free_refresh_left.value > 0`。**None = 未观察 → 保守按 paid 计数**(口径申报:次数是记账面非决策闸,商店刷新允许性归策略面;落 op-layer 正本行)。paid_refresh_count/total_refresh_count 留效果账本累计(非画面可观察剩余,不迁)。
- **发放登记(两桥改道 Field)**:`grant_effect_node_refresh_balance`(节点推进发放:加油站/搜打撤 =1、双手狸 =2、本金充裕条件族;挂点 = cw_loop 节点 tick)与 `apply_effect_burst_grant`(选卡 burst:免费午餐/及时雨/固定理财即时段)由 `grant_free_refreshes(n)` 改 `gs.write_logic(gs.free_refresh_left, left+n, produced_by=<效果源>, evidence='effect_node@plane/round' / 'effect_burst@frame')`。**None 基 = 0 起算**(开局底座 0 = 机制真值「开局无免费次数」,与现役效果账本初始一致):发放即首次落值,不存在 None+n。

**效果账本字段退役**:`ActiveEffectInventory.free_refresh_balance`(cw_effect_inventory.py:233)删除;`record_refresh` 的 free 扣减腿移除(:441-452,只留 paid/total 累计);`grant_free_refreshes`(:456-462)退役。**读端改造**:sim 刷新价格 `cw_sim_shop.py:64-66` 改读 Field(sim 发放/扣减经同两桥与上报函数,容器即模拟 gs);刷新计数组**注释面同步**(`cw_projection_audit.py:161` 与 `cw_game_state.py:2041`,均为注释块非代码行);`cw_refresh_shop_action.py:125` T-13 票随 §2.4 删除。

- **对账 = 下一入口观察**:刷新为访问终结,一次访问至多一次刷新 → 点击时 Field = 本访问入口刚锚定值,free 判定可靠;下一入口 observe 重新锚定,漂移自愈(观察赢,机制白送)。T-13 动作侧 UI 真值读与两张留证票退役,判定职能由 Field 既有失配安灯承接。
- **盲区口径**:双态锚定下「归零侧不可达」不成立(付费域可读即 0 的观察);残留 = 整帧判不出轮跳写(瞬态,下轮成功读补锚),如实申报。
- **金/牌面快照对账(probe)退役**:`shop_refresh_probe` 不引入;现役 `_reconcile_refresh_pending`/`_record_free_refresh_proc`/`cw_free_refresh_proc.flag`(ADR-0456 临时通道,flag 自述「确认后删」)随段机器退役——免费刷新的事实可见性 = Field 锚定失配安灯 + 效果账本计数,不再需要金/牌面快照比对。
- **刷新回执 extra(`refresh_board_changed` 位)删除**:其唯一消费 = 安灯 free_refresh_proc 豁免判定输入,随 proc 通道退役。`refresh_board_changed_of` 不迁 kernel:两消费面(段顶对账点/回执 extra)均退役,函数留 obs 工具箱(生产零消费,是否随清理批退役 = 落地阶段 grep 定夺)。

### 2.4 刷新动作 op 零读屏化

删除(`cw_refresh_shop_action.py`):①刷前现读两口径分支(`ledger.refresh_first_action` 消费面);②`cw_shop_refresh_obs.read_shop_refresh_button` 真值读与 `ledger.refresh_free_truth/free_remaining_truth` 落账;③两张真值↔账本留证票(`free_truth_logic_divergence`/`free_balance_ui_mismatch`);④刷后牌名落账读(`read_shop_cards`);⑤对账件 ledger 三件(`refresh_pre_gold/pre_names/pending_reconcile`)落账。

保留:点击、`REFRESH_CLICK_SETTLE_WAIT_S=1.0` 固定等待(等待不是判效,action_ops.md §2.2)、刷价记账(`shop_refresh_cost.value` 读口 + `REFRESH_COST_BASE` 回退)、自上报(free=None → **Field 值判定**,值 = 入口观察锚定的 `free_refresh_left`(§2.3);None 未观察 → 保守按 paid;T-13 UI 真值通道退役,判定职能收口观察边界)。效果账本只留 paid/total 累计(free 余额腿迁 Field,§2.3)。

### 2.5 删除面清单(文件::符号 → 处置;消费点核查结论就地标注)

| 符号 | 处置 | 消费点核查 |
|---|---|---|
| `cw_screen_buy_cards.py::run_buy_waves` | 删除(职能迁观察 node/决策动作 node;全动作统一路径) | 调用点三处(§2.2)全改;文档引用随正本更新清理 |
| `cw_op_close_shop.py::CwOpCloseShop` + `close_shop` 核心函数 + `_note_receipt`/`_clear_shop_payload` | 退役删除(执行位收编,§2.1 CloseShop 执行位;幂等两出口语义逐位迁入 `CwActionCloseShopOp` 执行体;`report_action_close_shop_param` 为容器清场上报) | 生产调用方 = visit_open_shop/仲裁段(随 §2.2 改造消失);分型表(推进型 37 屏名单)/完备锁面随正本更新调整 |
| `cw_screen_buy_cards.py` 节点行探针函数族:`probe_node_type`/`store_plane_table`/`_capture_unrecognized_node_icons`/`_NODE_ICON_SHOT_TS` | 迁出商店域 → 备战 heavy 观察链节点行消费位(§2.8,用户裁定:节点行是备战画面观察内容) | 消费面 = 槽序表/台账/结算回路(不变);识别器 = obs/cw_node_reader(不动) |
| `cw_buy_card_action.py` 兜底坐标 `_Pt(0, 288)`(槽号越界/点位缺失时静默点击) | 删除(用户裁定:废弃兜底,采用 screen_info)——点位缺失/槽号越界 = 显式 round_fail(信息带 area 名,与 level_btn/refresh_btn 同款纪律) | 违反坐标单一真相源与「禁兜底坐标静默点击」同文件声明;commit 面随 3.4 |
| `cw_loop.py` 发射帧仲裁段特殊路径 + `run_buy_waves` 的 `spend_gate` 形参 + `cw_screen_prep._act_execute_default` restricted_spend 截流分支 + `CwActionOpenShopParam.restricted_spend` 字段 | 退役(受限消费迁策略侧自限,§2.10) | 消费面 = 发射帧受限会话(改策略 StrategyState 派生标记 + decide 自限);kernel `launch_arbitration_gate` 谓词留守单一源,消费方改策略决策入口 |
| `kernel/cw_effect_inventory.py`:`free_refresh_balance` 字段(:233)+ `grant_free_refreshes`(:456)+ `record_refresh` free 扣减腿(:441-452) | 退役/改造(次数升格 Field `gs.free_refresh_left`,三写端同格,§2.3) | 写端 = 两发放桥 + 刷新上报(全改道 Field);读端 = `cw_sim_shop.py:64-66` / `refresh_shop.py:55`(改读 Field);`cw_projection_audit.py:161` 计数组行同步 |
| `kernel/cw_screen_report/close_shop.py`(`CwOpCloseShopObs` 孤儿 obs 类) | 随壳退役删除;完备锁面(sr-od-test `test_cw_screen_report_ports.py` 的 close_shop 文件行与 `CwOpCloseShopObs` 在册行)同步更新 | 完备锁对该侧断言 report 不在场,行删除即锁面更新(grep 实证:test_cw_screen_report_ports.py :53/:58/:69) |
| 决策循环 CloseShop 拦截特例(`run_buy_waves` intercept 分支) | 删除(全动作统一路径,CloseShop 经注册表真执行) | 随 run_buy_waves 解体消亡;「终结不入 decisions 行」契约保留(循环内跳过该回执调用) |
| 同文件 `refresh_wave_is_refresh_only`/`_reconcile_refresh_pending`/`_shop_entry_names`/`_record_free_refresh_proc` | 删除(免费腿判定由次数锚定 + 失配对账取代,§2.3) | 段机器内部消费,随壳亡;proc flag 为人工判读临时通道(自述确认后删) |
| 同文件段尾观测块:`bench_buy_slots_settle_retry`/`bench_buy_occupancy_ok`/`bench_buy_count_ok`/`bench_buy_identity_missing`/`_buy_baseline`/pixel-diff 调用块/`match.bench_slot_map` 写点 | 删除(用户裁定 ⑤:画面 op 结尾不自做对账;逻辑态上报 + 下一入口观察对账承接) | `match.bench_slot_map` 全仓仅此写点、零读端(grep 实证);`new_bench_slots`(obs/cw_observation.py)唯一消费 = 本块 → 函数随删 |
| `cw_buy_card_action.py` 买前裁片块(`_card_crop`) | 删除(动作 op 零读屏;证据职能归下一入口观察对账) | 消费 = `BuyPurchase.crop` 遥测(test_cw_action_emit_book 断言 crop 非空)→ 字段删除 + 该测试改 |
| `kernel/cw_prep_expect.py::BuyPurchase.crop` | 字段删除(`count`/`k` 保留 = 上报 executed 单一源) | 全仓消费仅遥测面(grep 实证) |
| `cw_refresh_shop_action.py` 读屏三处 + 两票 | 删除(§2.4) | defects 两分键随删;`read_gold_opt`/`read_shop_cards` 替身缝随之(§2.2) |
| `ShopVisitLedger` 字段:`refresh_first_action`/`did_refresh`/`refresh_attempted`/`plan_truncated`/`total_sell_income`/`total_sell_skip`/`refresh_pre_gold`/`refresh_pre_names`/`refresh_pending_reconcile`/`refresh_post_names`/`refresh_free_truth`/`refresh_free_remaining_truth` | 删除 | `refresh_attempted` 仅写无读;`plan_truncated`/`total_sell_income`/`total_sell_skip` 零写零读;其余段机器内部(grep 实证,落地阶段复核) |
| `ShopVisitLedger` 保留:`total_buy`/`total_xp_buy`/`total_refresh`/`total_sell`/`spend_executed`/`bought_names`/`buy_purchases` | 保留(执行账/回执 detail/上报 executed 单一源) | — |
| `_shop_entry_read` 防抖循环 | 删除(用户裁定 ②) | 测试零引用(grep 实证) |
| `cw_screen_buy_cards` 模块属性替身缝 re-export | 删除 | 见 §2.2 末条 |

### 2.6 帧代次与披露

- `frame_class_shop`:**每访问入口 = 'full'**(方向贵段限频 = 既有键守卫「每 game-round 恰一次」,flow/README §2.2)。语义升级申报:刷新后新访问重估方向视图(现役「续段 none 不重估」随段机器退役);限频由键守卫承载,行为面无失控风险。
- `disclose_budget_at_shop_frame`:每访问入口一次(现每段一次;刷新访问即新披露,频率与现役段级等价,projection_contract.md §3.5 两调用点声明不变)。
- `save_decision_frame('shop_entry')`:每访问一帧(现每段一帧同点覆盖,文件覆盖语义不变)。

### 2.7 风险与处置

- 刷新动画 > 1s 时,新访问入口读可能撞动画帧 → 未识别卡停机闸响亮(不恢复防抖,用户裁定 ②)。处置 = 动作层可靠性:有实证再调 `REFRESH_CLICK_SETTLE_WAIT_S` 常量;禁验证/重试结构。
- 刷新真交回后,每刷一次 = 一次完整 0n 重分发。读屏净变化 = 刷前两口径读/真值读/刷后读三处删除 vs 重分发锚判定读,总量不增(现役每段本就要入口全量现读)。
- sim:驱动器 `decide_shop_screen` 消费面不变;次数 Field 同格(sim 发放/扣减经同两桥与上报函数,读端 `cw_sim_shop.py` 改读 Field,§2.3);sim A/B 证明面(商店波经济决策)不在本迭代辖内。

### 2.8 节点行观察归位备战观察域(用户裁定)

- **归属语义**:节点行 = 备战画面的观察内容。商店访问终结 → 交回外循环 → 外循环重识别 → 备战分支 → 备战观察自然发生,节点行在那时读——与商店访问/关店动作零耦合。现役挂在商店访问尾(`cw_screen_buy_cards.py::probe_node_type`,由 `visit_open_shop` 关店后调用)属历史接线错位,本迭代归位。
- **迁移面**:`probe_node_type` 的识别(`read_node_sequence`,obs/cw_node_reader)**零新增**——`cw_observe_full.py:148` 现役已调并把 slots 回传;写点半(`store_plane_table` 槽序表按位面首帧写含 `plane_lengths_seen`、台账按位合并 `ledger_update_plane` 'prep_row' 源含轮位对齐门 current idx == round_num−1、未识别图标采集钩子 300s 防抖)迁**备战 heavy 观察链节点行消费位**(`cw_screen_prep._observe`/`_write_prep_node_chain` 同帧同点合并落位);守卫语义不变(轮位对齐门/环境宽限窗/防抖随迁)。
- **触发面变化(如实申报)**:现役 = 仅商店访问尾触发(非商店轮不触发);归位后 = 每次备战入口 heavy 观察触发(识别复用现役调用,零新增读屏)。覆盖 ≥ 现役(两次商店访问之间必有一次备战入口 heavy 观察);读器自带非 clean 备战帧空转守卫(返回空即 skip)。成本增量 ≈ 0(读已存在,新增的只是写点接线)。
- **消费面不变**:槽序表(`plane_node_table`/`plane_lengths_seen`)、节点台账(结算观测回路/备战查表)、遥测分键。
- **商店域零探针**:`cw_screen_buy_cards.py` 内探针函数族整体迁出,商店访问交回零额外动作。

### 2.9 上报回调腿(买牌获取回调 + 刷新随机态;用户裁定)

- **买牌:回调在「获取角色计算完」后触发**。`report_action_buy_card_param` 在简单腿(落位)+ 合成连锁 + 升星腿全部计算完成后,触发购买回调 `gs.effects.on_buy(card, star, k)`(新挂点,形态镜像既有 `on_level_up`):bump `CounterKey.BUY`(返利族「每购 3 张 5 费」门槛面)+ 购买族效果分派预留位。时点语义 = 回调可见购买后的席面/升星事实;满栏合成一击多买按实际张数 k 计 k 次。flow 层 `apply_action_outcome` 的 BUY bump(现役唯一触发点,best-effort)**删除**——计数归上报单点,live/sim 同源(sim 经同一函数自动获得计数,消除计数分叉)。
- **刷新:先算商店牌随机态,再触发相关计数**。`report_action_refresh_shop_param` 在 `record_refresh` 计数后:①经发牌机器采样**商店牌随机态**(算法本体自 `sim/cw_sim_shop.py::deal_shop`(:69)迁入 kernel 新模块 `kernel/cw_shop_deal.py`,数据源 = `data/cw_shop_odds.py` 概率注册表;sim `deal_shop` 改调同一函数)→ `gs.write_logic_rand(gs.shop, 采样 payload, evidence='refresh_random_sample')`(**随机态专用通道**;`write_logic` 通道在 EXEMPT_REGISTRY 空登记下,observe 覆盖差异必进失配安灯停机——采样与实读几乎恒不等,照稿实现 = 每刷必停)。write_logic_rand 语义与本腿逐句同义(「实机上采样是猜测,sim 里采样即世界真值——同一上报函数两副面孔」):observe 覆盖差异 = 预期内,只落 `logic_rand_outcome` 台账行,不进失配安灯三分流。②相关计数触发:`CounterKey.REFRESH/REFRESH_TOTAL/REFRESH_PAID` 维持 `record_refresh` 既有触发;商店内容条件计数(干旱/供给 streak 族)消费口径见下。
- **与 logic_rand 消费门的关系**:logic_rand 契约 = 策略器消费前必须重观察。干旱/供给 streak 族(`cw_intention._update_pair_drought`)消费口径 = **仅 observation 源**(logic_rand 源该拍跳过,宁缺勿造)。恢复拍锚:刷新为访问终结,交回后 shop 域随离屏清 None(干旱族遇空 shop 冻结不误计);**下一次商店访问入口观察**以真值覆盖(`logic_rand_outcome` 留证),干旱族即恢复消费——与消费门同向,无豁免申报。
- **supersession 申报**:现役「终结跳写(2026-09-18 用户裁决):金与刷后牌面不写」的 **payload 半边随本裁定收窄**——payload 改 write_logic_rand 随机态(观察赢),金仍不写;刷新 op 模块头与 report docstring 的旧申报随 3.3 清理面更新。
- **两执行面同源**:随机态采样住上报函数后,sim 与实机走同一发牌代码(sim 的牌 = 采样即真值,实机的牌 = 采样被下一观察覆盖)——期望态两执行面同源原则(projection_contract §3.6)在商店 payload 上的落地。

### 2.10 发射帧受限消费迁策略侧(用户裁定:策略的事情不进流程框架)

- **现状**:发射帧仲裁 = cw_loop 特殊段(spend_gate 闭包 + `run_buy_waves(spend_gate=…)` + 无条件关店 + 发射,≈:515-590)——**花金政策闸住在 flow 层**,属决策面逻辑错位(flow/README 分层判据:决策归策略器)。
- **改后**:仲裁段与 spend_gate 通路**退役**;商店访问只剩普通路径。受限会话 = 策略侧自限:mandate_v1 前置发射位判定(armed ∧ 金超息线)时,`decide_shop_action` 读 StrategyState 派生标记,提案后经谓词检(**谓词单一源 = `kernel/cw_launch_arbitrage.py::launch_arbitration_gate`**,与 flow 闸同源):拒 → 本访问收工(决策改发 CloseShop,消费终止语义逐位平移,非改试次优——评估序不变);受阻回执语义(`blocked:spend_gate` exec_events 行)随拒拍落策略侧,遥测分键同迁 `strategy_state`。金回线内 → CloseShop → StartBattle 正常发射。
- **段旗留守**:`cw4_launch_spend_visited`(每武装段至多一次受限访问;失武装复位语义不变)**留守不拆**——闸不保证一次访问把金压到线内(零消费访问在册,KEY_ZERO_CONSUME 口径),拆旗 = 开店/关店循环;「每帧现算」限定于受限标记本身的派生方式,不及段旗。
- **连带退役**:`run_buy_waves` 的 `spend_gate` 形参、`CwScreenShop` 构造 `spend_gate` 参数、`cw_loop` 仲裁段特殊路径、`cw_screen_prep._act_execute_default` 的 restricted_spend 截流分支、`CwActionOpenShopParam.restricted_spend` 字段(OpenShop 归一单一形态)。受限会话进出店 = 普通 OpenShop/0n 路径,策略在决策内自限。
- **策略侧细则**(mandate_v1 变更,随 3.4 同批落地保证行为连续):标记派生与自限值域、受限会话遥测分键迁 `strategy_state`(现 flow 闸闭包计数);判据数学零改动(谓词同源)。
- **辖域申报(第三轮验收观察)**:自限辖域 = armed ∧ 金超息线的**全部** `decide_shop_action` 帧,含 armed 质量推迟帧上的普通商店决策(现役 spend_gate 只辖仲裁段,这类帧旧态不受闸)——属本节受限会话定义(armed ∧ 金超息线)的设计内辖域,无质量豁免;边界帧(金恰落息线)随标记 `≥` 放宽与旧闸带内拒域对齐(零分歧迁移)。

## 关键取舍

- **段机器保留、仅改申报**(放弃):用户裁定违规;伪终结继续绕过外循环,补偿复杂度继续增长。
- **对账件宿主 = StrategyState**(放弃):对账属观察域职责,容器观察面单一源;与用户裁定 ⑤ 同一原则。
- **保留段尾像素 diff 观测**(放弃):用户裁定 ⑤;pixel-diff 不分方向、误报源多(其自身注释已自证卖出/合并槽变化计入),逻辑态上报 + 下一观察对账已覆盖。
- **刷新 op 保留 UI 真值通道**(放弃):动作 op 零读屏是裁定主文;账本余额回退口径 = 上报函数既有语义,真值↔账本分歧的显影交观察边界 reconcile,不在动作层自证。
