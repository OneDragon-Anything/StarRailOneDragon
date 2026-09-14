# 状态收敛与画面 op 规范化 落地

> 状态:草案(设计总纲定稿后本文件才可立账本任务;阶段划分候盘点报告细化)。
> 通用工程门 = od-dev-progress-tracking §12(含 `ruff check` 仅改动文件、测试纪律;各阶段完成判据统一引用,不逐条复述)。

## 3.1 阶段一·sim 引擎内部模型切容器
**范围**:engine_p1/engine_p2/runner 内部状态切容器 GameState,真值直写(obs 族);`synthesize_from_game_state`/`feed_sim_truth`/`_feed_board_state` 双抄写并单退役;`simulate(CwSimFrame)` 与 `apply_shop_action_logic` 收敛为单一转移函数(4 调用点逐腿平移 + RefreshShop/LevelUp 内联保留面消解 + DeployMove 围栏块 :2519-2552 并入或申报对齐)。内部批次序(盘点 §5):先引擎读面切容器(纯读换源零删除)→ 再引擎写面+工作帧切换(最重)。不含:生产观察链(3.2)、遥测序列化面(3.3)、策略签名勘误(3.2 收口)。
**设计依据**:design.md §2 系统级变化 1/2、渠道签名契约;details/sim-state-switch.md §1-§4
**文件面**:sim/engine_p1.py、sim/engine_p2.py、sim/runner.py、sim/cw_replay.py、kernel/cw_vocab.py、kernel/cw_game_state.py
**依赖**:设计定稿
**优先级建议**:8
**完成判据**:
- sim 全量锁 + 零漂移锚绿(test_cw_sim_fidelity 指纹不变为收紧目标,漂移须申报语义依据);
- 引擎内 CwSimFrame 构造/字段访问零残留(grep 锁);
- 防回漂三锁(test_cw_sim_shop_single_source)按单源新形态重推:spy 锁改指单一转移函数、桩行为锁语义保持、grep 锁特征式更新(simulate 内联特征随退役改指新函数面);
- §12 通用工程门。
**验收凭据形式**:grep 锁 + sim fidelity 指纹 + 全量测试。

## 3.2 阶段一·生产观察链直写 + BuyCardsOutcome 退役 + 签名收口
**范围**:read_game_state 产出直 observe 进容器(8 调用点,详见 sim-state-switch.md §5);BuyCardsOutcome 删除(消费方四件迁移,安灯钩子数据源改 receipts+容器派生,对拍窗一期);cw_game_ports 端口注解切容器;策略签名收口(2 处签名勘误/4 处注释勘误/5 真双型收敛——state_equips_multiset 例外申报/encounter.py 本地帧视图删除/seed_age_blocked 死码删除)。
**设计依据**:design.md §2 系统级变化 1;details/sim-state-switch.md §5-§6
**文件面**:obs/cw_observation.py、obs/cw_observe_full.py、operations/cw_op/cw_op_buy_cards.py、operations/cw_screen/cw_screen_prep.py、cw_game_ports.py、telemetry/query.py、kernel/cw_shop_action_ops 相关、strategies/impl/mandate_v1/(签名面)、kernel/cw_discipline_rules.py
**依赖**:3.1(转移函数已单源)
**优先级建议**:8
**完成判据**:
- 生产链 CwSimFrame 零残留(grep 锁,src 全树);
- 安灯钩子行为保持:计划花费>0 金差≈0 → 仍停机(对拍既有哨兵语义);
- 买光商店实机单跑 CwScreenBuyCards 不再崩(重启 server 后)——本判据与 3.5 批1 联合验收,本阶段允许 shop 域仍走旧紧缩读链的过渡态(容器 shop 域写入口径不变)。
**验收凭据形式**:grep 锁 + 安灯钩子对拍 + 实机买光店单跑。

## 3.3 阶段一·遥测序列化面切换
**范围**:telemetry/schema.serialize_state、op_journal 帧参数、cw_decision_trace state 快照切容器序列化;旧帧序列化残留删除。
**设计依据**:design.md §2 系统级变化 1;details/sim-state-switch.md §4;内容底账 = .debug/temp/cwsimframe_migration_inventory.md §C4(迭代内工件引用)
**文件面**:telemetry/schema.py、telemetry/op_journal.py、kernel/cw_decision_trace.py、telemetry/cw_replay_reader.py
**依赖**:3.1、3.2
**优先级建议**:6
**完成判据**:序列化消费面(判读 CLI/复盘工具)走查一次过;旧帧活引用(构造/字段访问/签名)src 零残留(本体与残余共享词汇留 W8,见 design 契约 1)。
**验收凭据形式**:grep 锁 + 判读 CLI 走查。

## 3.4 阶段一·设计件同步
**范围**:sim-design.md/sim-wiring.md 更新为引擎直写容器 as-built;cw_game_state.py 容器 docstring「同步通道」声明更新。
**设计依据**:design.md §0/§2
**文件面**:docs/develop/sr_od/application/currency_war/sim/、kernel/cw_game_state.py(仅注释)
**依赖**:3.1-3.3
**优先级建议**:5
**完成判据**:文档与实现一致(逐字段接线表重对账)。
**验收凭据形式**:文档对照 review。

## 3.5 阶段二·批1 商店域三态定长根闭环
**范围**:ShopSlot 三态词表;read_shop_cards 定长 5 槽产出(锚门/亮度判据/SIFT miss→unknown+缺陷台账);容器 ShopPayload.cards 定长写入;投影口 BuyCard 移除改空位置换;两个硬必改点(收工停机钩子 `any(not c.name)` 改 kind 判据;cw_observe_full.py:129 子态判定改锚判);全 unknown 窗行为(花钱禁发射+CloseShop+停机留证,shop-slot-model §5.1);定长不变量锁;锁面处置按 sim-state-switch §3 表(M1 重推为容器单函数行为锁)。
**设计依据**:design.md §2 详设 details/shop-slot-model.md
**文件面**:kernel/cw_vocab.py、obs/cw_observation.py、kernel/cw_game_state.py、operations/cw_op/cw_op_buy_cards.py、operations/cw_op/cw_shop_action_ops.py、obs/cw_observe_full.py、strategies/impl/mandate_v1/shop.py(投影口相关面)
**依赖**:3.2(生产链直写)
**优先级建议**:9
**完成判据**:
- 买光商店实机单跑 CwScreenBuyCards 正常 CloseShop 收工(goal 总判据);
- 定长不变量锁绿;两个硬必改点行为锁绿(空位不触发未识别卡钩子);
- 失读形态锁绿(全 unknown 窗 → CloseShop+停机留证,shop-slot-model §5.1);
- 受影响测试全量一次过(精简纪律:只新增定长不变量/三态判据/单源锁)。
**验收凭据形式**:实机单跑 + 锁 + 全量测试。

## 3.6 阶段二·批2 策略消费面过滤
**范围**:mandate_v1/shop.py 13 处消费点适配定长数组(criteria/buy.py slot_idx 坐标系、refresh_effective 空位过滤等,以审计 D 项清单为底)+ ShopCard.slot 字段兼容期退役(shop-slot-model §1,消费点禁读 slot)。
**设计依据**:details/shop-slot-model.md 消费点清单
**文件面**:strategies/impl/mandate_v1/(shop.py、criteria/buy.py、criteria/refresh.py 等)
**依赖**:3.5(词表冻结)
**优先级建议**:7
**完成判据**:策略行为锁族全绿;决策行为无静默漂移(候选集对照)。
**验收凭据形式**:决策行为锁 + 全量测试。

## 3.7 阶段二·批4 bench/deployed/备战
**范围**:bench 槽级「占用未识别」None 态申报化;deployed 容器层(front_row/back_row)定长化;备战域 SIFT 透传三态化;统一观察架构 §2.2 透传豁免条款 = **延后撤销**(编排者裁定:以 deployed 槽级置信度遥测连续两版本稳定为前提门,详设 shop-slot-model §7.2 登记;非删除)。
**设计依据**:design.md §2 系统级变化 3;audit A 项四域差距表
**文件面**:kernel/cw_game_state.py、obs/cw_identity_obs.py、obs/(备战观察面)、design 正本(统一观察架构)
**依赖**:3.5
**优先级建议**:5
**完成判据**:四域达标度复扫 = 全对齐;豁免条款删除。
**验收凭据形式**:四域复扫 + 文档对照。

## 3.8 阶段三·判效拆除 4 族
**范围**:按 design.md §2 阶段三方案拆 BuyCardOp 灰度差判效/SellBench 像素验重试/RefreshShopOp 判效半边/CwScreenDeploy 像素判效族;合法面 5 个不拆。
**设计依据**:design.md §2 阶段三(单文档)
**文件面**:operations/cw_op/cw_shop_action_ops.py、operations/currency_war/prep_actions.py、operations/cw_op/cw_op_deploy.py
**依赖**:3.5(①族的 reconcile 承接前提)
**优先级建议**:6
**完成判据**:4 族判效代码删除;合法面 5 个原样;实机 ≥1 局落地-观察链路走查正常。
**验收凭据形式**:grep 锁 + 实机局走查。

## 3.9 阶段一收口·坐标兜底族删除(P4,用户明令)
**范围**:删除 10 处坐标兜底常量与消费点兜底支,area 缺失改大声失败(AREA_NO_CONFIG 一族既有语义):cw_op_buy_cards.py:386-387(LEVEL_UP/REFRESH_FALLBACK,消费 :805-806)、prep_actions.py:618-620(BATTLE/CONFIRM/CHECKBOX_FALLBACK,消费 :1623-1652)与 :144 硬编码兜底 helper、cw_faction_obs.py:45(:210)、cw_identity_obs.py:1412(:1595)、cw_op_equip_all.py:389(:424)、cw_screen_partner.py:84(:254)。不含:COST_SOURCE_ROSTER_FALLBACK(信源分级)/XP_CLICK_COST_FALLBACK(数值缺省)/PLANE_FALLBACK_PRIORS(机制先验)/K_FALLBACK_SOURCE_THREE_ARM(臂名)——语义不同,保留。
**设计依据**:design.md §1 解决到哪;.debug/temp/shop_slot_problems.md P4;「坐标单一真相源」规范(AGENTS.md)
**文件面**:上列 6 文件
**依赖**:无(与各批正交;触碰 cw_op_buy_cards.py/prep_actions.py 与 3.2/3.8 同文件域,merge 时序由编排者对账)
**优先级建议**:6
**完成判据**:FALLBACK 坐标常量全仓零残留(grep 锁,含消费点);area 缺失路径行为 = 显式失败非静默兜底;受影响测试一次过。
**验收凭据形式**:grep 锁 + 全量测试。

## 末阶段:正本更新
**范围**:按「正本更新清单」逐条更新正本。
**设计依据**:本文件「正本更新清单」节。
**文件面**:清单所列正本文档。
**依赖**:全部落地阶段。
**优先级建议**:0。
**完成判据**:清单清零;正本与实现一致。
**验收凭据形式**:文档对照 review。

## 正本更新清单

- sim/sim-design.md §1.3/§2(架构图与动作契约:引擎直写容器、转移单源) ← 3.1/3.4
- sim/sim-wiring.md(接线底账重对账:字段映射换容器域) ← 3.1/3.4
- design/统一观察架构-画面op基类设计.md §2.2(透传豁免条款延后撤销登记,前提门见 §7.2) ← 3.7
- design/统一观察架构-画面op基类设计.md(观察产物类型:直写容器 as-built) ← 3.2
- game_state/fields.md(ShopPayload 定长契约/ShopSlot 词表,如该表涉商店域) ← 3.5
- flow/shop_visit.md / flow/action_exec.md(判效拆除后的执行面描述) ← 3.8
