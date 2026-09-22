# 商店刷新真终结与访问循环规范化 落地

## 3.1 店开防抖删除
**范围**:`_shop_entry_read` 删 3×0.8s 有界重读循环(单次读,读缺交决策前置门);同文件注释面防抖引用同步(模块级函数 docstring/类注/observe node 注/run_buy_waves docstring/段头注释两处)。不含其它改动。
**设计依据**:design.md §1-4/§2-6;details/shop-visit-loop.md §2.5 末行。
**文件面**:`src/sr_od/application/currency_war/operations/cw_screen/cw_screen_buy_cards.py`
**依赖**:无
**优先级建议**:2(先落,后续阶段同文件动刀)
**完成判据**:
- 入口观察路径恰一次读(grep 无重读循环/无 0.8 sleep);行为 = 读缺交决策前置门响亮失败;
- 通用工程门(= 修改面 ruff check + 直接受影响测试;项目 AGENTS.md 提交纪律)。
**验收凭据形式**:grep + CW 商店面测试(test_cw_shop_*)。

## 3.2 刷新次数 Field 化
**范围**:GameState 新建 `free_refresh_left` Field(剩余语义,§1.4 家族);漏斗新增消费端锚定(复用现役 `read_shop_refresh_button` 调用产物 `obs/cw_observation.py:2700`,双态口径:免费态锚次数/付费域锚 0/判不出跳写;失配走 Field 既有安灯,零手写台账);刷新上报 free 腿改 `write_logic` Field 扣减(未观察保守按付费);两发放桥(`grant_effect_node_refresh_balance`/`apply_effect_burst_grant`)改道 Field(None 基 = 0 起算);效果账本 `free_refresh_balance`/`grant_free_refreshes` 退役、`record_refresh` 只留 paid/total;**刷新上报随机态腿**(算法自 `cw_sim_shop.deal_shop:69` 迁 kernel 新模块 `cw_shop_deal.py` → `gs.write_logic_rand` 写 5 槽 payload 随机态,observe 覆盖差异落 `logic_rand_outcome` 台账不进安灯;干旱/供给族仅消费 observation 源);读端改造(`cw_sim_shop.py:64-66` 刷新价格改读 Field、`deal_shop` 改调 kernel 采样器);刷新回执 extra(`refresh_board_changed` 位)删除;`_reconcile_refresh_pending`/`_record_free_refresh_proc`/`_shop_entry_names`/proc flag 退役;`refresh_board_changed_of` 消费面清理(grep 定夺是否随清理批退役)。**边界调整(保每 commit 恒绿)**:`cw_refresh_shop_action.py` 中依赖被退役 `free_refresh_balance` 的 T-13 票块(含其按钮真值读与 `refresh_free_truth` 接线)强制本阶段前置清除——清除后 free 判定即走 Field;3.3 再完成其余零读屏项(刷前两口径/刷后落账/ledger 字段)。
**设计依据**:details/shop-visit-loop.md §2.3/§2.9。
**文件面**:`kernel/cw_game_state.py`(Field + 两桥)、`obs/cw_observation.py`(漏斗,仅新增消费端)、`kernel/cw_action_report/refresh_shop.py`、`kernel/cw_effect_inventory.py`、`kernel/cw_shop_deal.py`(新,算法自 sim 迁入)、`sim/cw_sim_shop.py`(deal_shop 改调 + 刷价读 Field)、`cw_refresh_shop_action.py`(T-13 票块前置清除,边界调整段)、`cw_screen_buy_cards.py`(段顶对账件退役)、`kernel/cw_action_report/__init__.py`(docstring 同步,screen-review 登记义务)、`kernel/cw_projection_audit.py`(完备锁审计行)、直接受影响测试
**依赖**:无(与 3.1 同文件不同域,排序在后避免在飞冲突)
**优先级建议**:3
**完成判据**:
- 单测:双态锚定三支(免费态锚次数/付费域锚 0/判不出跳写)+ observe 覆盖 logic 失配走既有安灯 + 扣减/两桥发放写端 produced_by/evidence 断言(None 基 = 0 起算)+ 未观察保守按付费 + 随机态采样(确定性种子断言 + `write_logic_rand` 落 `logic_rand_outcome` 台账、不进失配安灯三分流);
- sim 刷新价格读 Field;效果账本零 free 余额残留(grep);
- 通用工程门。
**验收凭据形式**:新增单测 + ruff。

## 3.3 刷新动作 op 零读屏化
**范围**:details/shop-visit-loop.md §2.4 全项(删刷前两口径读/刷新钮真值读+两票/刷后牌名落账;`free=None` Field 值判定;`REFRESH_CLICK_SETTLE_WAIT_S` 常量保留);`ShopVisitLedger` 字段删除:对账件三字段 + 真值两字段 + `refresh_post_names`;**模块头与 report docstring 的「终结跳写 payload 不写」旧申报更新为 write_logic_rand 收窄申报(N1 supersession)**;`telemetry/schema.py:773` 沿用已废硬墙口径的注释顺带清理。
**设计依据**:details/shop-visit-loop.md §2.4;用户裁定「动作 op 机械执行、默认成功、不做验证」。
**文件面**:`cw_refresh_shop_action.py`、`cw_shop_action_ops.py`、`kernel/cw_action_report/refresh_shop.py`(supersession docstring)、`telemetry/schema.py`(硬墙口径注释顺带清理)、直接受影响测试
**依赖**:3.2(对账链已迁容器,删 ledger 落账不丢证据)
**优先级建议**:4
**完成判据**:
- 刷新 op 文件零 screenshot/read 调用(grep 断言);
- 效果账本三计数触发语义不变(既有投影锁绿);
- 通用工程门。
**验收凭据形式**:grep + test_cw_shop_projection_logic 等。

## 3.4 商店画面 op 两 node 规范化 + 节点行归位 + 受限消费迁策略侧 + 节点行观察归位
**范围**:details/shop-visit-loop.md §2.1/§2.2/§2.5/§2.6/§2.7/§2.8/§2.10:`run_buy_waves` 解体(段首簿记迁观察 node/act node round_wait 单动作循环,全动作统一路径零拦截零闸)、**CloseShop 执行位真点击化**(`CwActionCloseShopOp` 收编点击/幂等出口/上报清场;`CwOpCloseShop` 编排壳 + `close_shop` 核心函数退役)、**节点行观察归位**(探针函数族 `probe_node_type`/`store_plane_table`/`_capture_unrecognized_node_icons` 迁备战 heavy 观察链节点行消费位 `_write_prep_node_chain` 同点,商店域零探针)、**发射帧受限消费迁策略侧**(cw_loop 仲裁段与 spend_gate 通路退役;mandate_v1 StrategyState 派生标记 + `decide_shop_action` 自限,政策谓词留守 kernel;`OpenShop.restricted_spend` 字段与 `_act_execute_default` 截流退役)、**买牌上报获取回调腿**(`on_buy` 新挂点;`apply_action_outcome` BUY bump 删除)、买牌兜底坐标 `_Pt(0, 288)` 清除、三调用点改造(仲裁段退役 → 两路 + 单跑)、段尾观测块/买前裁片/ledger 死字段/替身缝删除、帧代次每访问 full。
**设计依据**:details/shop-visit-loop.md §2.1/§2.2/§2.5/§2.6/§2.8/§2.10。
**文件面**:`cw_screen_buy_cards.py`、`cw_screen_prep.py`、`cw_loop.py`、`cw_buy_card_action.py`、`cw_close_shop_action.py`、`cw_op_close_shop.py`(退役)、`kernel/cw_screen_report/close_shop.py`(孤儿 obs 随壳退役)、`kernel/cw_prep_expect.py`、`kernel/cw_launch_arbitrage.py`(消费面调整)、`kernel/cw_vocab.py`(restricted_spend 字段退役)、`strategies/impl/mandate_v1`(受限会话自限)、`strategies/impl/flow.py`(自限落点)、`kernel/cw_action_report/buy_card.py`(on_buy 挂点)、`kernel/cw_action_report/close_shop.py`(清场申报)、`kernel/cw_effect_inventory.py`(on_buy sink)、`kernel/cw_open_shop_action.py`(截流退役)、`kernel/cw_projection_audit.py`(basis 现值化)、decision_frame_hooks(挂点文案现值化)、`obs/cw_shop_refresh_obs.py`(refresh_board_changed_of 退役)、`obs/cw_observation.py`(`new_bench_slots` 退役)、`screens/op-layer.md` §3 分型表(完备锁被迫同步,提前落盘已裁定)、直接受影响测试
**依赖**:3.1、3.3
**优先级建议**:5
**完成判据**:
- CwScreenBuyCards = 规范两 node 形态(观察 node 每访问恰一次读;决策动作 node 零读屏 round_wait;终结读注册表;决策循环无 CloseShop 特例分支);段机器零残留(grep `did_refresh`/`refresh_wave_is_refresh_only`/`run_buy_waves`/`CwOpCloseShop` 在 **src/ + sr-od-test/** 零命中;正本文档引用归末阶段清零);
- CloseShop 执行位:点收起 + 幂等已关出口 + `report_action_close_shop_param` 清场,零转移验证;「终结不入 decisions 行」契约保持;
- **节点行归位**:`probe_node_type` 在 cw_screen_buy_cards.py 零残留;备战入口 heavy 观察触发槽序表/台账写(单测:轮位对齐门/环境宽限窗守卫随迁语义不变;识别复用 observe_full 现役调用,零新增读屏);
- **买牌回调**:on_buy 在获取计算完后触发(满栏合成按 k 计数);CounterKey.BUY 不再经 flow 层落地门(grep 零残留),sim 路径同源计数(单测);
- **受限消费迁策略侧**:仲裁段/spend_gate 零残留(grep);mandate_v1 自限单测(armed ∧ 超息线 → 提案过谓词检,拒 = CloseShop 收访问消费终止;金回线 → CloseShop → StartBattle 正常发射;段旗每武装段至多一次);
- 买牌兜底坐标清除(点位缺失/槽号越界显式 round_fail,与 level_btn/refresh_btn 同款);
- **出参交接面**:op 暴露 `ledger` 属性;visit_open_shop 失败判定 = `is_success`,计数读 `op.ledger.total_*`(既有测试随改);
- 删除面清单(详设 §2.5)全项 grep 零残留(同上限定面);
- 通用工程门。
**验收凭据形式**:grep + 测试清单(test_cw_budget_disclosure / shop_unobserved_gate / shop_projection_logic / unified_action_4 / action_emit_book / overflow_gate / round_fresh_buys_host / shop_action_face_contraction / shop_close_clear / buy_cards_defense_funnel / screen_report_ports + 节点行归位新单测)。

## 3.5 类名正名
**范围**:`CwScreenShop` → `CwScreenShop`、`cw_screen_buy_cards.py` → `cw_screen_shop.py`、op_name → 「货币战争-商店」;kernel 观察面随画面名机械规约同步:`kernel/cw_screen_report/buy_cards.py` → `shop.py`、`CwScreenShopObs` → `CwScreenShopObs`、`report_screen_shop_obs` → `report_screen_shop_obs`(op-layer §2.1 命名机械规约);语义重命名(refactor 工具)+ 全项目消费锚同步(测试/文档符号锚)。
**设计依据**:design.md §2-2;op-layer.md §2.1 命名规约;用户裁定正名。
**文件面**:重命名涉及面(src 引用点、sr-od-test 引用点)
**依赖**:3.4
**优先级建议**:4
**完成判据**:`CwScreenShop`/`cw_screen_buy_cards`/`CwScreenShopObs`/`report_screen_shop_obs` 在 **src/ + sr-od-test/** 零残留(正本文档引用归末阶段);全量引用点更新;通用工程门。
**验收凭据形式**:grep 零残留 + CW 快速集绿。

## 3.6 全量验收
**范围**:CW 快速集全量;提交面复核(申报面 = 入库面)。
**文件面**:无新改动(修复面 = 上列文件)
**依赖**:3.5
**优先级建议**:5
**完成判据**:`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"` 全绿;修改面 ruff 全绿。
**验收凭据形式**:测试输出 + git show --stat 复核。
**验收追记(编排方裁定)**:提交面 22 对集合外文件分层裁定——Tier1(14 对,范围/判据明文、文件面行粒度缺口)、Tier2(5 对,退役连带/完备锁强制)追认;Tier3 两对(`cw_action_report/__init__.py` docstring = screen-review 登记义务、`screens/op-layer.md` §3 = 完备锁被迫同步)经 3.2/3.4 阶段验收分别裁定合规,一并追认;各阶段「文件面」行已补正为实际入库面。3.6 判定 PASS(全量 958 passed;34 触碰文件 ruff 全绿;13 词残留终扫双仓零命中)。完整报告 = `.debug/temp/acceptance-3.6-report.md`。

## 末阶段:正本更新
**范围**:按「正本更新清单」逐条更新正本;顺带清理两项(3.5 验收建议):`kernel/cw_anchor.py` 注释「现役登记件还在 cw_op_buy_cards」指向已退役符号(改指现役 `cw_buy_card_action.py`)、`cw_screen_prep.py` 「买牌访问…」日志文案与正名后「商店」域用语统一。
**设计依据**:本文件「正本更新清单」节。
**文件面**:清单所列正本文档。
**依赖**:3.1–3.6
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致。
**验收凭据形式**:文档对照 review。

## 正本更新清单
- `screens/shop.md`:§1(发射帧仲裁受限访问条目 → 受限消费迁策略侧申报)、§2(形态声明:round_wait 单动作循环;刷新 = 访问终结)、§3(观察面:单次读零防抖/刷新次数观察锚定/每访问 full)、§4(动作面表与伪代码重写:round_wait 循环,CloseShop 经注册表执行,spend_gate 行删除)、§5(终结表:刷新行 = 访问终结真交回;删段间判定/仅刷新段/spend_gate 闸拒行;收尾观测段删除——节点行观察归备战观察域)、§6(删 refresh_counters/prev_node_spent 旧口径)、§8(免费刷新 proc 留证行退役 → Field 锚定失配安灯)、§9(遥测面)← 3.1–3.4
- `screens/prep.md`:观察面(节点行写点接线申报:迁 heavy 链节点行消费位 `_write_prep_node_chain` 同点,识别复用现役调用)← 3.4
- `screens/op-layer.md`:§3 分型表(CwScreenBuyCards 行改写新形态并正名 CwScreenShop;`CwOpCloseShop` 行退役,推进型名单/计数同步)、§1.4/§4(商店域接入刷新次数 Field 模式申报:`free_refresh_left` 剩余语义;None = 未观察保守按付费,次数是记账面非决策闸)← 3.2/3.4/3.5
- `screens/README.md`:§3(五型描述波循环措辞)、§4 动作词表(RefreshShop 终结性/CloseShop 编排壳两行)、§5.4(商店能力面:买经验/卖备战加「未接线」注记;CwOpCloseShop 引用清理)、§6 终结总表(RefreshShop 行:段终结 → 访问终结;CloseShop 行执行位改动作 op)← 3.4/3.5
- `flow/action_exec.md`:§2 执行契约表商店编排行、§4 BuyCard 行(on_buy 回调/BUY bump 迁移)、§4 RefreshShop 行(零读屏/free = Field 锚定/真终结/终结跳写 payload 半边收窄 = write_logic_rand 随机态)、§4.7(CwOpCloseShop 行/run_buy_waves 行随退役清理)← 3.2/3.3/3.4
- `flow/action_ops.md`:§1 增补 3(动作 op 零观察识别规范,用户裁定直接写入,即时生效非末阶段)、§4.1 BuyCard 行 + RefreshShop 行(§1 增补 3 欠账清除:裁片/三读删除,free = Field 观察锚定)、§4.3 OpenShop 行(restricted_spend 受限形态退役)、§4.7(CwOpCloseShop 行/run_buy_waves 行随退役清理)← 3.2/3.3/3.4
- `strategy-docs/`(mandate_v1 受限会话自限申报:发射帧政策消费从 flow 闸改决策入口,篇目随实现定位)← 3.4
- `flow/README.md`:§1 总图(商店编排/波循环措辞)、§2.2(decide_shop_action 输入列修正:终态零参口,决策读容器单例)← 3.4
- `flow/guards.md`:§3 入口段描述核对(防抖措辞如有残留)、§7(免费刷新 proc 行随 proc 通道退役)← 3.1/3.2
- `flow/projection_contract.md`:§3.5 店开帧披露调用点措辞核对、§3.6(两执行面同源在商店 payload 的落地申报:刷新随机态经 write_logic_rand)← 3.2/3.4
