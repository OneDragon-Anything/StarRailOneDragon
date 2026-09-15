# 开战(StartBattle)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。

## 1. 动作是什么

点击「按钮-出战」推进节点进入战斗——**转移动作**(备战访问终结·唯一完成态):只把画面从备战转移到战斗,不按游戏规则改写任何局内资源。词表 = `kernel/cw_vocab.py::StartBattle`(无字段 dataclass);执行器 = `prep_actions.py::PrepActionExecutor._start_battle`(发射 → 未落地原样重发长按下 → 仍败计连败停机留证);发射准入核 = `kernel/cw_launch_admission.py::readiness_launch_decision` + `operations/cw_loop.py::readiness_battle_launch`(达标臂)。

## 2. 逻辑态域集

**容器 GameState 全域零写(显式声明「逻辑态 = 空」)**:进战斗后 hp/gold/streak 全部由结算屏真值覆盖接管(`apply_settlement_cover` 结算覆盖写端;败轮金按轮首补发口径)。`kernel/cw_exec_state.py::apply_op_effect` 的显式不建模清单点名 StartBattle:进战斗,hp/gold/streak 由结算屏观察覆盖接管,零推进。

效果账本域(非 GameState 字段):**免战牌子态**的跳过执行落地后次数递减(§3 第 4 条)。

## 3. 确定面转移规则(逐条)

1. **节点转移事实**(非容器域):出战落地 → 外循环置战斗窗口(备战 → 战斗 → 结算 → 回备战轮推进,[../outer_loop.md](../outer_loop.md) §4);备战标识消失 + 无拦截弹窗 = 转移成功的机械判据(`POST_LAUNCH_BLOCKERS` 白名单防「前台无角色」弹窗假成功);
2. **常规发射**(执行器):找钮(「按钮-出战」,免战子态查「按钮-跳过」,正交态查找不锁死单一屏——免战与商店开可叠加)→ mouse_move + click + 失焦守卫(重点一次)→ 未达上限警告弹窗勾选 + 确认(勾「本局不再提示」,对齐 CwScreenDeployNotFull)→ 轮询转移;
3. **未落地重发/停机**:首次失败原样重发(press_time 加长)→ 仍「未落地」计 `launch_dead_streak`,达 `LAUNCH_DEAD_LIMIT` → 停机留证三要素(截图 + flag + stop_running)。发射重发/连败停机 = 流程防线([flow/action_exec.md](../../flow/action_exec.md) §7),不属逻辑态;
4. **免战牌子态**(策略卡「免战牌」激活):出战按钮变「跳过(N/N)」= 本节点直跳战斗(免 2 次战);跳过**执行落地**(备战标识消失验证通过)→ 效果账本次数递减(`kernel/cw_effect_inventory.py::ActiveEffectInventory.consume_use`:remaining_uses −1,归零移除;余量种子 = `EffectSpec.duration_uses`)。递减挂点与登记挂点解耦(登记面缺位的局 consume_use 返 None 零动作,不炸发射回执);「用尽后按钮恢复出战」待实机验(观察工作清单)。

## 4. 随机面

战斗结果与结算载荷 = 随机面归观察(战斗窗自动进行,玩家无操作面)。**「跳过后 hp/streak/收入不动」= 待实机实证的暂定表述(缺口 G9)**:跳过无结算帧、无结算载荷,结算覆盖段对本节点无写入,三字段全部经下一备战观察覆盖(覆盖时三字段必核对)。

## 5. 拒绝语义

- 找不到出战/跳过按钮 = `emitted=False`(「找不到出战按钮」),交上层处置;
- area 缺失 = 确定性失败禁兜底坐标(重发无意义,立即判败上交);
- 出战被拒弹窗(`POST_LAUNCH_BLOCKERS` 在册)= 失败(标识消失为弹窗污染非转移),交「带验证的重部署 → 再出战」链;
- W209j 刹车(ADR-0388):运行中被停 → `StopBrakeShortCircuit` 异常拒绝执行任何动作(停机非动作,不五回执行);
- 容器零写语义下无 applied=False 拒绝形态(`apply_op_effect` else 分支零推进)。

## 6. kernel 符号锚

`kernel/cw_vocab.py::StartBattle`;`prep_actions.py::PrepActionExecutor._start_battle` / `_launch_attempt` / `_launch_dead_escalate`;`kernel/cw_launch_admission.py::readiness_launch_decision`;`operations/cw_loop.py::readiness_battle_launch`;`kernel/cw_effect_inventory.py::ActiveEffectInventory.consume_use` / `EffectSpec.duration_uses`;`kernel/cw_exec_state.py::apply_op_effect`(显式不建模清单);`kernel/cw_game_state.py::apply_settlement_cover`(战后真值接管)。

## 7. 语义验证

StartBattle 不在 `cw_vocab.py::Action` 联合内——节点推进归 sim 引擎日程面,非词表动作转移。「逻辑态 = 空」的容器声明:本动作不改写局内资源,真值由节点边界/结算覆盖承载。无 M1 直锁对象;原 sim 整帧副本载体(simulate)已退役,考古归 git。

## 8. 判例注记(发射期)

**备战期出口(唯一完成态)**(判例 = [screens/README](../../screens/README.md) §4 终结总表):出战落地 = 备战访问终结,交回外循环战斗分支。免战子态下「跳过」同语义点它(推进节点)。发射准入判据(达标臂/锁定重试)= cw_launch_admission 判据族,不属本篇。

## 9. 依据

[../action-logic-state.md](../action-logic-state.md) §5(转场类动作逻辑态 = 空 + 免战牌态);[fields.md](../fields.md) §3.2.19(免战牌激活态与剩余跳过次数)/§4.2 出战行(免战分支与 G9 暂定表述)/§4.2 结算覆盖行;`prep_actions.py::PrepActionExecutor._start_battle` docstring(恢复语义 = 禁 active_window 激活,重发 = 同通道原样重试);[flow/action_exec.md](../../flow/action_exec.md) §7(发射重发/连败停机流程防线)。
