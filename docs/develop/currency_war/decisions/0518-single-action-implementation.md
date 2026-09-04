# ADR-0518: 画面 op 单动作循环实施批(ADR-0517 迁移落码)

> 状态:**accepted**(实施批 2026-09-06)。本文是 [ADR-0517](0517-single-action-screen-op.md)(画面 op 单动作循环架构)的实施 ADR:记录迁移面、处置表落点、测试重锚与哨兵基线。规格与裁定依据一律以 ADR-0517 为单一源,本文不重复推导,只记「落成什么样」。路径根 = `src/sr_od/application/currency_war/`。

## 背景

ADR-0517 accepted 前,商店决策为波批形态(`decide_shop_wave` 一次性算整波 + 执行侧截断器),备战为「每动作落地后 heavy 重观察」保守口径。本批(2026-09-06)按 ADR-0517 十条裁定将两域落码为单动作循环;补给面按同款语义申报;死码簇(旧备战骨架)同批清除。

## 迁移面(as-built,全部对工作树代码直调复核)

### 商店域

- **决策核**:`strategies/impl/mandate_v1/shop.py:355 decide_shop_action(state, session, config) -> Action`——全函数(决策 5),「无动作可做」= 返回 `CloseShop` 恒可用终结(决策 4/6,取代旧「空序列 = 决策完成」通道);选择序 = 既有波批优先级逐帧取首项(ADR-0517 §映射,序不变):M4 腾席 → M2 线成员(含 M2b 合并完成)→ dominance → M3 升级(单击)→ M6 溢余 → EV 买面 → R1 付费刷新(终结)→ 凑息卖 → 支付支撑卖 → CloseShop。契约核验(`contracts.ensure_contract`)挂在单动作决策入口,取值口径 = 动作后真值(§8.1 落点,见下)。
- **策略接口**:`strategies/impl/flow.py:478 CwFlowStrategy.decide_shop_action`(ABC 钩子,委托 mandate_v1/shop);黑板 = `session.shop_state_frame`,写者 = 入口观察段 / 单动作投影步 / sim 引擎。
- **序列兼容驱动器**:`mandate_v1/bridge.py:124 decide_shop_screen` 保留给 sim 引擎 / 回放 / 既有序列锁——驱动 = 逐帧调 `decide_shop_action` + `cw_state.simulate` 纯投影推进期望态,终结动作截停序列、CloseShop 收尾不入序列(输出形态与旧截断器对齐)。与旧波批的输出等价系条件命题(ADR-0517 §映射·P52 条)。
- **截断器退役**:`shop.py:134` 载退役声明——旧 `_SHOP_CONTINUE/_SHOP_CONDITIONAL/_SHOP_TRUNCATION` 三分类与 `truncate_shop_frame_stable` 随波批形态退役,截断点语义被终结 op 吸收;名-槽一致性复检降级为执行侧守卫断言。
- **动作基类与动作 op 集**:新模块 `operations/cw_op/cw_shop_action_ops.py`——`ShopActionOp` 基类两方法 `execute(env)`(机械执行)+ `project(state)`(决策 10;实现 = `cw_state.simulate` 单一源,合成连锁/满栏例外 §2.5 自动多买/金账全在其内,禁第二实现);`terminal` 类标记终结动作。词表 → op 表(`_OP_TABLE`):BuyCard / LevelUp(单击,clicks 序列 = 动作内部步骤,由决策循环逐帧重组)/ RefreshShop(终结)/ SellBench / CloseShop(终结,关店点击由编排壳 CwOpCloseShop 承担,动作 op 内 no-op)/ CompTransaction(终结,见处置表)。
- **执行侧单动作循环**:`operations/cw_op/cw_op_buy_cards.py:411 run_buy_waves`(函数名保留,前身份 = 买牌波循环)——段循环 `for _ in range(MAX_REFRESH + 1)`:每段入口观察(段顶 read_game_state 全量现读 → hp 覆盖 → 首段 update_target → node_type/dual 拷入 → gold==0 救援 → gold_open 首段快照 → tracked 播种 → 黑板写 `shop_state_frame`,即对账)→ 内层 `while True` 决策循环(零读屏):`decide_shop_action` → 守卫断言 → 动作 op `execute` → 非终结且落地则 `project` 推进黑板。CloseShop 终结 = 本访问收工;RefreshShop 终结 = 本段结束、外层段循环下一次迭代即「外循环重进」的物理载体(入口观察重建,读屏次数与波批持平,ADR-0517 §读屏成本)。
- **刷新硬墙 visit 级重定位**:候选 (a) 落定——`ledger.total_refresh`(ShopVisitLedger,旧闭包计数器具名化)≥ `MAX_REFRESH=4` ⇒ 终结集降级为仅关店(`cw_op_buy_cards.py:646`,硬墙跳过 = 计划了但未尝试,`plan_truncated=True` + `refresh_skipped='max_cap'` 可见化不停,`w577` 局 22 误停根因)。
- **decisions 遥测行**:段尾累计行(段粒度 = 旧波行同框架;actions = 本段执行累计,CloseShop 终结不入行——与旧「空序列 = 完成」的行形态对齐;单动作下不存在「截断丢弃尾」,`plan_truncated` 仅由刷新硬墙置位)。
- **对抗修复批补登(2026-09-06,实施对抗轮 1-2)**:①EV 买面席位门(`shop.py` EV pass 补 check_seats 与 dominance 同款;拒因分键 `shop_ev_bench_wait`)——满栏非合并买入在 simulate 走 bench_full 整动作 no-op 分支,无门则同帧重复提案不收敛;席位门后买面全 gated(M4 腾席/M2 break/M2b continue/dominance/M6/EV 各有门),**满栏 §2.5 执行侧机制与双账满栏豁免在商店生产路径不可达,保留为防御纵深**;②执行侧防御帧帽 `SHOP_SEGMENT_ACTION_CAP=16`(与备战 VISIT_ACTION_CAP 同款;超帽 RuntimeError + `plan_visit_action_cap` 分键,禁静默);③计数键改名 `shop_wave_idle_gold`→`shop_visit_idle_gold`(visit 语义;跨结构不可直接对拍,旧键全仓零消费);④prep SellBench 投影补 state 侧金账(`sell_refund` 与 simulate 同式;此前半投影致同访问后续帧读偏低金=过量卖出风险);⑤OpenBox/OpenTome 投影按 action.slot 摘;⑥guard_proposal_vs_expected 补 BuyCard 名断言。

### 备战域

- **入口单次 heavy + 逐动作投影**:`operations/cw_screen/cw_screen_prep.py:1261 run`(备战单轮)——①入口 heavy 观察一次(`_observe(heavy=True)`,期望态重建的唯一读屏点,即对账)→ ③④⑤ 单动作决策循环 `for _vi in range(VISIT_ACTION_CAP)`(=16,防决策循环不收敛,达上限交回外循环由 stall 防线接管):`decide_prep_screen` 取输出**首项**(单动作选择序,三遍编排序保持)→ F3 校验 → 期望态计算(drag/equip/dep 记账)→ 执行 → 投影。旧「每个执行过的游戏动作后 heavy 重观察」契约已灭(`_observe` docstring 载)。
- **投影已建模面**(`_project_prep_obs`,纯计算零读屏):OpenBox/OpenTome(开一件腾席)、ClickSpheres(残球保守清空)、SellBench(槽位摘除 + free+1)。
- **未建模面保守回退**:投影返回 None(DeployMove/SellDeployed/LevelUp/RunDeploy/RunEquip)⇒ 本访问终结交回外循环重观察——重观察语境禁猜,与商店线 CompTransaction 终结邻接 fallback 同款纪律。**遗留验证阶梯见文末**。
- **对账暂存入口消费**:`session.cw_prep_pending_accts`(逐动作 acct 字典暂存;下一入口 heavy 时点统一 `_v2_post_frame_accounting` 消费后清空,`cw_screen_prep.py:1303-1305/:1443-1446`)——对账时机从「波内多处」收拢为「入口单点」,投影建模分叉在下一入口暴露。
- **终结 op**:OpenShop(切商店画面)、StartBattle(出战)、DeferSpheres/BailToOuter(控制流交回)、投影未建模回退——执行即本访问结束交回外循环。

### 补给面(申报性适配,无结构改动)

`operations/cw_screen/cw_screen_supply_node.py:17-23` 载 ADR-0517 §8.4 适配申报:本节点已按单动作架构语义运转——每轮 handle = 入口重观察(`_in_node` 验证 + `read_supply_options` 现读)→ 单动作决策(`decide_supply` 一选)→ 执行;**刷新 = 终结 op**(点击后本动作即返回,`round_retry` 重进节点 = 入口重建);节点内至多刷 1 次由 `_supply_refresh_used` session 实态承载(carried 融合,跨外环重建存活,与商店 visit 级硬墙对称)。docstring 旧「无刷新按钮」陈旧残句已删(现载「刷新按钮实存(REFRESH_BTN 图标式)」)。

### 死码清理

`strategies/impl/flow.py` 模块头(:15-22)载:旧备战骨架 10 方法删除——`_decide_prep_action_impl` / `_main_flow_step`(prep_phase 相位机)/ `_free_bench_step`(腾席链)/ `_deploy_up_candidates` / `_bench_junk_idx` / `_pseudo_state` / `_fresh_state` 及私有 helper(`_is_boss_round` / `_cap_shortfall` / `_levelup_engine_ok`);传递性死码 `kernel/cw_deploy_seat` 整模块删除(`_should_deploy` 族;文件已不存在,存活载体 = `cw_state.board_unique_key` / `cw_deploy_logic`);session 暂存字段 `prep_phase` / `prep_phase_retry` / `free_bench_gold_wait` 同批清除(`cw_strategy_session.py:140` 载注)。

## 处置表摘要(ADR-0517 各候选的落点)

| 处置项 | ADR-0517 候选 | 落点 |
|---|---|---|
| 守卫两属 (i) proposal-vs-expected | 迁移保留 | `cw_shop_action_ops.guard_proposal_vs_expected`(SellBench 槽位占用与 expect 名一致;炸出 = 策略器 bug) |
| 守卫两属 (ii) expected-vs-tracked 双账 | 建议保留 | `guard_expected_vs_tracked`(投影链 vs tracked 账对拍;**满栏买入豁免**——tracked 的 bench_place 满栏丢件 vs simulate 走 §2.5 k 张分支,两模型不同构,对账重挂点 = 下一入口观察) |
| 执行侧观测通道三件(卖回金实收/刷新有效性/免费刷新证据) | (a) / (b) | **(a) 落定**:保留为动作 op `execute` 实现层遥测(RefreshShopOp 内),与决策读屏解耦;物理读屏量与波批持平 |
| 刷新硬墙 | (a) 外循环计数 / (b) 预算并入期望态 | **(a) 落定**:执行侧 visit 级 `ledger.total_refresh` 计数,超墙终结集降级仅关店 |
| sim-only refresh_used 计数接 live | 实施批先裁 | 未接(live 定价维持 `state.shop_refresh_cost or 基价`,免费刷新仍为事后观测留证)——按 ADR-0517 §3.1 第 2 条的「不接则无此字段可融合」分支 |
| CompTransaction | 复合动作类 + 终结邻接 fallback | `CompTransactionOp`(terminal=True,执行即访问结束交回重观察);商店单动作决策核现行不提案 CompTransaction(提案面在备战域),op 为词表完备性落位 |
| 非满栏合成槽位买一击张数 | research 知识缺口 | **保守假设一击一张**(`cw_shop_action_ops` 模块头申报;与 simulate 常规买入分支一致),规则模型误差由入口对账兜底;实机冻结解除后补档验证 |

## 开放问题五条落点(ADR-0517 §开放问题 / screen_op.md §8)

1. **8.1 contract ctx 逐动作取值语义**:已按 flow 侧裁决建议落——动作后真值(= 期望态当前值,契约核验挂单动作决策入口、与决策同源,`shop.py:355` docstring 载声明;跨结构计数对比须声明口径切换)。
2. **8.2 prep_phase 相位机归属**:死码已清——相位机随 `_main_flow_step` 删除,session 三字段(`prep_phase`/`prep_phase_retry`/`free_bench_gold_wait`)同批清除。
3. **8.3 无决策画面的规范边界**:处置表已交付——按「选择面 ∧ 投影账」判据对 §7 盘点表逐行定案(screen_op.md §7/§8.3:商店/备战/补给入规范,单选族例外、无决策画面外循环直管)。
4. **8.4 补给刷新终结语义**:已按建议落——刷新 = 终结 op 申报 + `_supply_refresh_used` session 实态硬墙(见上「补给面」)。
5. **8.5 安灯输入面重锚**:**输入面未变申报**——decisions 行保持段尾累计行形态(段粒度 = 旧波行同框架,安灯分类器消费的「本轮 shop plan 行」载体未消失),`plan_truncated` 豁免通道保留且语义收窄为「刷新硬墙跳过」(单动作下不存在截断丢弃尾);逐动作事件流重锚未做,留后续按需(现输入面可支撑三态判定,无失效面)。

## 测试重锚清单(sr-od-test/,锁语义随结构重推,非机械跟绿)

| 测试文件 | 重锚面 |
|---|---|
| `test_cw4_shop_line.py` | 终结 op 契约锁(前身 = 截断契约锁)、词表外类型响亮暴露、proposal-vs-expected 守卫、R197 同槽防线(发射侧丢弃通道退役) |
| `test_cw_telemetry.py` | decide_shop_screen 波调用 → decide_shop_action 顺序锁(拷贝行在单动作循环之后) |
| `test_cw_telemetry_collect.py` | record 站点自 run_buy_waves 波循环迁入单动作循环 |
| `test_cw_p56_t1.py` | 回拉遥测计数粒度「每波一次」→「每决策帧一次」 |
| `test_cw_strategy_iter_7f.py` | 首帧 M2b 席闸行为(单动作逐帧重判) |
| `test_cw_deploy_ops.py` | 期望态时点(execute 前)/对账点(acct 暂存 session);腾席链门 + 空板出战守卫测试组随死码删除 |
| `test_cw_data_registry.py` / `test_cw_obs_chain.py` / `test_cw_strategy_chain_smoke.py` / `test_cw_w953_planner_strategy_wiring.py` / `test_cw_w971_blackboard.py` | 旧死码核具现(`_decide_prep_action_impl` 桥)退役,测试改走 live 链 |
| `test_cw_target_matching.py` | cw_deploy_seat 删除,判据载体迁移 |
| `test_scenario_gen.py` | 同名禁双不变量载体 = `cw_state.board_unique_key`;双轨期 carry 判定存活载体重锚 |
| `test_cw_sim_suite.py` | bench_full_flag 点亮面随 sim 重锚批重探(w614 同批) |

## w614 digest 新哨兵基线

`test_cw_w614_sim_fidelity.py` 零漂移锚重锚(注释 :115-120 载):波批→单动作的条件等价前提(波批投影无残差)不成立——逐帧重判使帧内后段动作可见前段动作的真值更新(实证:M2b 合并买在凑息卖腾席后的下一帧补发;凑息卖逐帧重估缺口),行为位移属 ADR-0517 §与现行架构的映射预告的真语义差(「帧级锁不预期保持绿」),非 unintended drift。

**新锚值 = `996a1f579845c20fff92661332534910a54b838868ee6f29a50b0632f7fd0459`**(seeds 0..5,pool='snapshot';前锚 f3d80127…),继续做 unintended drift 哨兵。

## 遗留:备战未建模投影面的实机验证阶梯

备战投影未建模面(DeployMove/SellDeployed/LevelUp/RunDeploy/RunEquip)现行走保守回退(终结重观察)——功能正确但读屏量与旧 per-action heavy 持平。**实机解冻后的验证阶梯**(逐面推进,过一档建一档投影):

1. 每面收集保守回退触发频次(段内单动作访问占比)——高频面优先建模;
2. 建模面须有确定性规则源(deployed 物理落位规则 / XP 表推进),禁猜;
3. 建模后面挂 `guard_expected_vs_tracked` 同款双账断言(投影 bug 在环检测)入验证阶梯;
4. 同款纪律适用于商店线「非满栏合成槽位买一击张数」知识缺口(补档 `merge_mechanics.md` 后验证,未过则该买面升格终结 op)。

## 关联

ADR-0517(规格单一源);`flow/screen_op.md`(目标态规格)、`flow/shop_visit.md` / `flow/prep_visit.md`(as-built 正文);`strategy-docs/02_mandate_layer.md` §7/§9、`strategy-docs/11_shop_decisions.md`(装配形态 as-built)。
