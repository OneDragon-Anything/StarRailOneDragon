# overlay 触发登记 落地

## 3.1 容器合并(DeployedView 完整槽位表)
**范围**:front_row/back_row → `deployed: Field[DeployedView]`(front_slots 定长 4 + back_slots 动态,空槽显式);Unit.slot 属性退役;快照 schema 升版 + 迁移函数;观察链合一写;全部行域写方/读方改新视图(不再调用换算函数)。**不含 TrackedBooks 退役(= 3.2)与换算五函数删除(= 3.2,tracked 消费端在 3.1 窗口期仍用)**。
**设计依据**:details/deployed-merge.md「目标模型」「观察与吸收口径」「快照兼容」「触面清单」
**文件面**:kernel/cw_game_state.py、全部行域写方/读方、观察链、测试仓相应断言(清单见详设触面表,不含 tracked 退役面)
**依赖**:无
**优先级建议**:9
**完成判据**:
- 槽位语义等价:front_slots/back_slots 与原 front_row/back_row 逐槽对拍(占用/空位/成员)一致——测试仓全量绿(行域断言改写后)
- 换排/替换/空槽上场各为单次 deployed 写(写序断言)
- 快照:旧档恢复经迁移函数行为等价(restore 测试)
- §12 通用工程门
**验收凭据形式**:测试全量绿 + sim 局结果对拍 + 写序断言

## 3.2 TrackedBooks 退役
**范围**:tracked 主账(bench/deployed 两面)与全部随动同步腿删除;商店播种守卫 expected 侧改读主域派生;升星确认候选宿主不动、比较基线改主域派生视图;tracked_account_observed 锚定语义重定义;换算五函数删除(`deployed_slot_no`/`deployed_row_slot`/`deployed_idx_of`/`deployed_rows_to_indexed`/`deployed_indexed_to_rows`,kernel/cw_exec_state.py)。
**设计依据**:details/deployed-merge.md「TrackedBooks 退役」表 + 「触面清单」tracked 侧行
**文件面**:kernel/cw_game_state.py(类删)、kernel/cw_exec_state.py(五函数删)、prep_actions.py、cw_reconcile.py、cw_vocab.py、strategies/impl/mandate_v1/(mandate 读口)、operations/cw_op/(deploy_move/sell_deployed/buy_card 同步分支)、obs/cw_observation.py、operations/cw_screen/cw_screen_prep.py、相应测试
**依赖**:3.1
**优先级建议**:8
**完成判据**:
- 双响防御语义保留:商店播种守卫 expected-vs-主域 分叉停机路径测试在册且绿
- 升星确认(两帧一致)行为等价:对账测试绿(候选宿主不动——本就在 cw_reconcile 局旁表;真变更 = 比较基线从 tracked 表改为主域派生视图)
- 全仓 `tracked_books`/`_track_`/`mutate_bench_deployed` 引用归零;换算层五函数归零(`deployed_slot_no`/`deployed_row_slot`/`deployed_idx_of`/`deployed_rows_to_indexed`/`deployed_indexed_to_rows`,均在 kernel/cw_exec_state.py)
- §12 通用工程门
**验收凭据形式**:测试(守卫/对账)+ grep 归零清单

## 3.3 值域回调级联 + 登记
**范围**:派生维护按名分解 → 四回调挂点(on_units_changed/on_equips_changed = 事件通知;on_qualification_changed = 判据;on_star_changed = S3);资格集派生存值(盯三阵营)+ 羁绊计数字段分立口径;簿记(祈愿/planner 已触发档集合、占卜屋计数);register/consume/clear 接口与容器存处;S4 占卜屋 settle 腿直登;S5 阿哈选卡直登;S6 三个 open_* 上报直登。
**设计依据**:details/faction-trigger.md(级联表/资格集语义/判据归位/星徽链路)+ details/register-consume.md(接口/存处/其余触发类)
**文件面**:kernel/(新回调模块 + cw_game_state.py 派生维护)、kernel/cw_action_report/(判据落点各上报)、新登记模块
**依赖**:3.1(单字段写形)
**优先级建议**:8
**完成判据**:
- 判据逐条行为测试:伙伴(成员增减/星徽穿卸/经典合成集合不变不弹/合成继承获资格弹/换排非开拓者阵容不弹)、巨星(跨档上穿即弹含降档回升/重选两形态/写后达首档门槛)、祈愿跨档(首达一次)、planner(合成落场上/2★ 上场/每费用档一次/备战不触发/无→3 按弹)、占卜屋(计数 2 倍数/延迟到备战)、阿哈、open_* 直登——测试逐条对应
- 获得链递归中间层判据语义完整(merge step 单写含产物与移除)
- §12 通用工程门
**验收凭据形式**:测试(判据逐条)

## 3.4 消费面(实机 + sim)
**范围**:宿主 op(备战/商店)动作后查 pending 交回;外循环两段式判定提速(pending 逐屏先试 → miss 回退全扫描,机制 = get_match_screen_name 不承传入序);识别对账行(pending vs 实扫不一致 → note_obs_event);pick 上报 consume(八个有上报的 pick;aha = sim advance + 实机兜底清空);sim 呈现读 pending + 逐 kind 呈现门(fortune 仅备战底层);S6 声明 next_screen 语义回归底层屏(open_box trigger 保留)。
**设计依据**:details/register-consume.md(消费节)+ details/faction-trigger.md(级联)
**文件面**:operations/cw_loop.py、operations/cw_screen/(宿主 op 与 pick op)、sim/(backend/overlay)、kernel/cw_action_report/(open_* 与 pick 上报)、sim advance 声明消费两 case
**依赖**:3.3
**优先级建议**:7
**完成判据**:
- 宿主交回:pending 非空 → round_success(测试:备战/商店两宿主)
- 排序提速:pending 画面首中(get_match_screen_name 候选序,测试);未命中全扫描兜底不变
- sim 对拍:同局脚本结果与迁移前一致(除 sim 修正清单七项的显式行为差异:planner 扫描范围[备→场]、planner 簿记[一次性→每费用档]、megastar 簿记[水位→逐次上穿,降档再升也弹]、fate → wish_trial、expert → expert_invite、hack → planner 正名、fortune 补 kind)
- §12 通用工程门
**验收凭据形式**:测试 + sim 对拍

## 3.5 退役清扫
**范围**:事实事件三件套(FactEvent/FACT_EVENT_KINDS/set_fact_event_sink)与 **6 处 emit 调用**(deploy_move:143、buy_card:184/186、wear_equip:187、sell_bench:121、sell_deployed:78)删除;sim `_evaluate_megastar`/`_evaluate_planner`/`_board_truth`/`_refresh_board`/`OverlayQueue`/megastar_fired_tier/planner_fired/planner_seen_star 退役;sim 三建模错误修正收尾(fate → wish_trial 正名,fortune 补 kind);OpenTome 双击改单击(实机核后执行——bug 在册:cw_open_tome_action.py 双击序列第二击落已弹弹窗)。
**设计依据**:details/register-consume.md(迁移退役清单)+ details/trigger-inventory.md §1.9
**文件面**:kernel/cw_event_hooks.py、kernel/cw_action_report/(六 emit 点)、sim/ 三件、operations/cw_op/cw_open_tome_action.py
**依赖**:3.4
**优先级建议**:5
**完成判据**:
- 全仓 FactEvent/emit_fact_event/set_fact_event_sink 引用归零;sim 私有评估器符号归零
- OpenTome 单击后选卡链路测试绿(实机核凭据 = 实机局 journal)
- §12 通用工程门
**验收凭据形式**:grep 归零 + 测试 + 实机 journal

## 末阶段:正本更新
**范围**:按「正本更新清单」逐条更新
**设计依据**:本文件「正本更新清单」节
**文件面**:清单所列正本文档
**依赖**:全部落地阶段
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致
**验收凭据形式**:文档对照 review

## 正本更新清单
- fields.md:§3.2.3/§3.2.4 合卷 + deployed 字段节 + tracked_books 簿记行删 ← 3.1/3.2
- projection_contract.md:§4(槽位表立法段/双账段/换算段)与 §3 相关行 ← 3.1/3.2
- action-logic-state.md:§1.4 随动账行删 + §3 各动作行域口径 ← 3.1/3.2/3.3
- screens/prep.md:§6 tracked 行 ← 3.2
- screens/op-layer.md:对账相关节(升星确认比较基线) ← 3.2
- sim-design.md:§4 overlay 触发层(值域回调+登记)/§6.3 事件钩子节删 ← 3.3/3.4/3.5
- sim-wiring.md:§六(装配节) ← 3.5
- architecture.md:模块表(新回调/登记模块行、事件钩子行删) ← 3.3/3.5
- flow/action_ops.md:动作总册(声明列 + 登记/判据关系) ← 3.3/3.4
- flow/outer_loop.md:§2.2 分发排序提速节 ← 3.4
- screens/op-layer.md:§1.2 ← 3.4
- screens/megastar.md / planner.md:触发语义勘误(每费用档等) ← 3.3
- game/gameplay/currency_war.md 银狼段:触发次数口径 ← 3.3
