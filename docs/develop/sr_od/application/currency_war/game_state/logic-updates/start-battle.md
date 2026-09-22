# 开战(StartBattle)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。

## 1. 动作是什么

点击「按钮-出战」推进节点进入战斗——**转移动作**(备战访问终结·唯一完成态):只把画面从备战转移到战斗,不按游戏规则改写任何局内资源。词表 = `kernel/cw_vocab.py::CwActionStartBattleParam`(无字段 dataclass);执行 = 三路径(备战环/统一执行器/恢复局)经同一注册表分派到达 `operations/cw_op/cw_start_battle_action.py::CwActionStartBattleOp`(点击+弹窗确认,零判效零重发);**发射统一执行器** = `operations/cw_loop.py::launch_battle_unified`(屏态复验→浮层安全检查→部署原子序→出战点击链;face = armed/resume 两调用面);发射准入判据 = mandate_v1 前置发射位消费 kernel `readiness_launch_decision`(策略层宿主)。战斗窗置位 = 外循环既有口径(驻留闩),置位通道 = 备战访问 op 的交回(`cw_loop.py::CwLoop.loop` 备战分支 `_on_prep_round` 回调):出战意图在 op 内经统一执行器落执行后,op 以终结出口 success 交回,外循环见 success 交回即置 `_battle_ts` + `_battle_wait_active`;非出战出口的 success 交回误置位由 CwScreenBattleWait 宽限等待与备战白名单锚兜底分流。

## 2. 逻辑态域集

**容器 GameState 全域零写(显式声明「逻辑态 = 空」)**:进战斗后 hp/gold/streak 全部由结算屏真值覆盖接管(`apply_settlement_cover` 结算覆盖写端;败轮金按轮首补发口径)。上报函数 `report_action_start_battle_param` 的申报:进战斗,hp/gold/streak 由结算屏观察覆盖接管,零推进。

效果账本域(非 GameState 字段):**免战牌子态**的跳过在上报动作时次数递减(§3 第 1 条)。

## 3. 确定面转移规则(逐条)

1. **上报动作**(非容器域):op 完成步(点击出战/跳过 + 弹窗确认后)直调自己的上报函数 `report_action_start_battle_param`;免战牌子态(`skip_substate=True`)在上报函数内执行效果账本 consume_use(上报时递减,未登记零动作);战斗窗口置位归外循环(出战点击落地由游戏承载,op 零判效)。
2. **常规发射**(执行器):找钮(「按钮-出战」;免战子态查「按钮-跳过」;备战 + 开商店两屏正交态查找——免战与商店开可叠加,叠加帧识别为开商店屏)→ mouse_move + click(基本单击)→ 固定等待 1.0s(`POST_CLICK_WAIT_S`,弹窗渲染窗,不轮询)→ 单帧截图弹窗收口(「货币战争-未达上限警告」= 勾「勾选-本局不再提示」+ 点「按钮-确认」,对齐 CwScreenDeployNotFull;「货币战争-提示-前台无角色」= 点「按钮-确认」;都没有 = 完成——出战点击后的真弹窗全清单已排查仅此两类)→ 上报动作事实交回。旧发射家族(6×0.5s 转移轮询/备战标识消失验证/POST_LAUNCH_BLOCKERS 拦截弹窗守卫/重发长按下/失焦守卫/launch_dead 连败停机)已整删:op 不判效,交回后画面状态由外循环下一帧重判;
3. **零重试零判效**:点击未落地/被拒不重发不计数——交回外循环重判,下一周期策略自然重提案;点击丢失的停顿监测归哨兵(框架不裁策略卡死)。
4. **免战牌子态**(策略卡「免战牌」激活):出战按钮变「跳过(N/N)」= 本节点直跳战斗(免 2 次战);跳过点击并完成上报 → 效果账本次数递减(上报时递减,§3 第 1 条)(`kernel/cw_effect_inventory.py::ActiveEffectInventory.consume_use`:remaining_uses −1,归零移除;余量种子 = `EffectSpec.duration_uses`)。递减挂点与登记挂点解耦(登记面缺位的局 consume_use 返 None 零动作,不炸发射回执);「用尽后按钮恢复出战」待实机验(观察工作清单)。

## 4. 随机面

战斗结果与结算载荷 = 随机面归观察(战斗窗自动进行,玩家无操作面)。**「跳过后 hp/streak/收入不动」= 待实机实证的暂定表述(缺口 G9)**:跳过无结算帧、无结算载荷,结算覆盖段对本节点无写入,三字段全部经下一备战观察覆盖(覆盖时三字段必核对)。

## 5. 拒绝语义

- 找不到出战/跳过按钮 = `emitted=False`(detail =「未执行:找不到按钮」,交上层处置;
- area 缺失 = 确定性失败禁兜底坐标(detail =「area 缺失:<area 名>」,按序列未完成上报「未执行」交回);
- 出战被拒弹窗(未达上限警告/前台无角色)= op 内点确认后完成交回;重部署归策略部署义务(下一备战帧自然提案),框架零恢复链。
- W209j 刹车:运行中被停 → `StopBrakeShortCircuit` 异常拒绝执行任何动作(停机非动作,不五回执行);
- 容器零写语义下无 applied=False 拒绝形态(上报函数恒零容器写,`applied=True` 受理)。

## 6. kernel 符号锚

`kernel/cw_vocab.py::CwActionStartBattleParam`;`operations/cw_op/cw_start_battle_action.py::CwActionStartBattleOp`(点击+弹窗确认零判效);`kernel/cw_action_report/start_battle.py::report_action_start_battle_param`(免战递减内聚);

## 7. 语义验证

StartBattle 不在 `cw_vocab.py::Action` 联合内——节点推进归 sim 引擎日程面,非词表动作转移。「逻辑态 = 空」的容器声明:本动作不改写局内资源,真值由节点边界/结算覆盖承载。无 M1 直锁对象;原 sim 整帧副本载体(simulate)已退役,考古归 git。

## 8. 判例注记(发射期)

**备战期出口(唯一完成态)**(判例 = [screens/README](../../screens/README.md) §4 终结总表):出战落地 = 备战访问终结,交回外循环战斗分支。免战子态下「跳过」同语义点它(推进节点)。发射准入判据(armed 判定,mandate_v1 前置发射位消费)= kernel `cw_launch_admission` 判据族(`readiness_launch_decision`),不属本篇。

## 9. 依据

[../action-logic-state.md](../action-logic-state.md) §5(转场类动作逻辑态 = 空 + 免战牌态);[fields.md](../fields.md) §3.2.19(免战牌激活态与剩余跳过次数)/§4.2 出战行(免战分支与 G9 暂定表述)/§4.2 结算覆盖行;`operations/cw_op/cw_start_battle_action.py` 模块头(执行序与旧发射家族整删申报;替身缝 = `prep_actions.py::PrepActionExecutor._start_battle` 薄委托);[flow/action_exec.md](../../flow/action_exec.md) §7(发射重发/连败停机流程防线)。

## 10. 同族:OpenShop(开店)

转场族另一注册行,逻辑态同为**空**;逐动作逻辑态已拆专篇 = [open-shop.md](open-shop.md)(terminal 承载行;容器零写;流程层消费 = `cw_screen_prep._open_shop_phase`)。
