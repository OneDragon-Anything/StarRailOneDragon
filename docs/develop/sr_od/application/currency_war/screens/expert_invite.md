# 专家邀请函(expert_invite · 货币战争-备战-专家邀请函)

> 代码 = `operations/cw_screen/cw_screen_expert_invite.py::CwScreenExpertInvite`(两 node 直继承 `SrOperation`)。职责:书册卡开卡后弹出的专家邀请函选卡——读板面阵营 → 默认策略选卡(羁绊同线优先,兜底现金为王)→ 点卡 → 弹窗关 = 选卡落地(重入裁决收案)。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_expert_invitation.yml`。

## 1. 分发判定

- 阶段一身份分发(号制已退役):id_mark 锚「货币战争-备战-专家邀请函.标识-专家邀请函」;命中即接管。单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。
- 处理链分工:开卡半 = 备战词表 `OpenBookcard`(`kernel/cw_vocab.py::CwActionOpenBookcardParam` 在册;执行器 = `cw_open_bookcard_action.py::CwActionOpenBookcardOp`,终结动作 `terminal=True`;发射位 = 策略器 entry ① prep 实体面卡片臂 `strategies/impl/mandate_v1/entry.py`,开卡时机归策略实现管,备战观察不再入口代清;开卡即交回)→ 弹窗由阶段一身份分发本 op——**本 op 只辖弹窗已开后的选卡**,入口态单一 = 弹窗已开。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 弹窗在场门(「标识-专家邀请函」,miss = round_fail 交回外循环重识别自愈)→ 弹窗载体一次读(板面 + 卡羁绊 + 选卡坐标解算)→ `report_screen_expert_invite_obs` 落容器 `expert_invite` 槽 → obs 挂实例属性。决策动作 node = 顶部重入裁决(选卡 pending = 上轮已发的 `(idx, card_bonds)` 快照;弹窗不在 = 选卡落地 → 补写 chosen_expert + 现金分支到账登记 + success;弹窗在 = 未落地 → 重走)→ 零参决策 `match.strategy.decide_expert_invite()`(候选自容器槽;判据单一源 = kernel `cw_events.py::choose_expert_index`,羁绊同线优先兜底现金为王,判据见 §4)。屏内无兜底:决策返回 None/词表外 = 具名 round_fail 零盲发交外循环(op-layer.md §1.1 出口③,消息含原值);idx 域外(词表值域 0..3 ∨ -1)= 守卫断言 AssertionError(op-layer.md §1.3,禁静默并入现金分支);策略异常自然传播(含离屏失约 ValueError);两守卫均在派发前、零点击;选卡派发 = 策略产 `CwActionPickExpertInviteParam` 直发,流程侧零值域改写;无 match 局外不设早退支(用户裁决 2026-09-22 全族删门)。选卡链经 `CwActionPickExpertInviteOp` 派发(直发策略产实例;点卡即选机械链+自上报在动作 op 内,pick-op-unify 批)→ `round_wait` 循环推进(无防御上限;`node_max_retry_times=6` 现役值仅框架异常路径消费)。

## 3. 观察面

观察 node = 弹窗在场门(「标识-专家邀请函」;miss = round_fail 交回外循环重识别自愈)+ 弹窗载体一次读(每访问恰一次,决策轮复用实例载体):

- 板面阵营 `obs/cw_observation.py::read_board`(弹窗帧左侧羁绊面板透出可读;读数失败 = 空 dict 走现金为王兜底,告警不阻塞);
- 卡羁绊解析 `_resolve_card_bonds`(逐卡 area 约束 OCR):文本精确命中 `data/cw_factions.py::FACTIONS` 键 → 文本含键(OCR 噪声容错)→ 文本 = `data/cw_chars.py::CHARACTERS` 角色名取其首个羁绊(factions 优先,空则 flows)→ 全未命中 = None(策略层走兜底);
- 选卡坐标解算(坐标随观察上报,[op-layer.md](op-layer.md) §1.1 :35):四卡区中心(`CARD_AREAS` 逐区 `area_center`)+「卡-现金为王」区中心,观察期一次解算,值形状 = 1080p 平铺元组,随 payload 同门一并上报;坐标单一真相源 = 观察上报,决策半零现算(动作 op 自容器按下标取,见 §4)。

观察 payload = `CwScreenExpertInviteObs`(`on_screen`/`card_bonds`/`board`/`card_points`/`cash_point`/`screen`,住 `kernel/cw_screen_report/expert_invite.py`);report = `report_screen_expert_invite_obs` 载体写容器 `expert_invite` 槽(`ExpertInvitePayload` card_bonds/board/card_points/cash_point 四字段同门一并写,恒写;match/gs 缺席的局外兜底路径跳过)。

**转换成功性边界(:34 欠账登记)**:本屏名字域转换失败现役语义 = 照报不早退——单卡解析全不中 → 该卡 None 照报(`_resolve_card_bonds` 三级解析全未命中)、板面读数失败 → `{}` 照报(`read_board` 异常吞为空),两态进容器照常决策(kernel 判据无依据 → -1 现金为王);与 [op-layer.md](op-layer.md) §1.1 观察标准化门「转换失败 = 观察失败 round_fail 零写零上报」不一致面在册为欠账形态。坐标域随同门:任一卡区建档缺失 → `card_points` 整域 None 照报(禁部分列表——错位 idx 坐标系);report 组装处等长守卫 `len(card_points) == len(card_bonds)`(定长 4,卡 i ↔ card_points[i] 同序)。收敛方向 = 转换失败 round_fail 零写零上报或维持屏契约边界,名字与坐标同门一次落净(:34 欠账清偿批裁决),清偿前零行为改动。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionPickExpertInviteOp`(`CwActionPickExpertInviteParam`,idx=-1 = 现金为王语义) | 注册表工厂 `action_op_for`(派发实例 = 策略产 `CwActionPickExpertInviteParam`,两守卫后直发;无 match 局外不设早退支——用户裁决 2026-09-22 全族删门,无派发;`OverlayPickExecEnv` = idx-only,零 target——坐标由动作 op 自容器 `expert_invite.card_points[idx]` ∨ `cash_point`(idx=-1)取,[op-layer.md](op-layer.md) §1.1 :35,缺席/越界 = 守卫断言) | 自上报 `report_action_pick_expert_invite_param`(零写族,容器零写) | 否(非终结):发出后 `round_wait` 循环推进;落地由重入裁决判——「货币战争-备战-专家邀请函.标识-专家邀请函」不在 = 补写 `chosen_expert`(仅卡分支)/ `ConfirmExpertCash` 到账登记(仅现金分支)+ success 交回外循环(见 §5) |

决策动作 node 选卡链(整体经动作工厂 `cw_pick_expert_invite_action.py::CwActionPickExpertInviteOp` 派发,pick-op-unify 批;机械链+自上报零写在动作 op 内;派发 = 直发策略产 `CwActionPickExpertInviteParam` 实例,含 -1 现金为王语义):

```
board/card_bonds = 观察轮 obs 载体
pick = decide_expert_invite()(零参;候选读容器 expert_invite 槽;
  判据本体 = kernel choose_expert_index;屏内无兜底)
  ① 主力阵营(在场计数最大,并列取名字序首个保证确定性)同线卡优先;
  ② 次选与任一在场阵营(board 计数 >0)同线卡(羁绊面板口径 = factions∪flows
    并计,卡上标签同属一个羁绊命名空间);
  ③ 全无同线 / board 空 / card_bonds 空 → -1(现金为王:选卡无依据时
    经济兜底优于盲选)
+ 守卫①(pick 非 CwActionPickExpertInviteParam → round_fail 含原值零盲发)
+ 守卫②(pick.idx 域外 0..3 ∨ -1 → AssertionError)→ idx = pick.idx
坐标 = 容器 expert_invite.card_points[idx] ∨ cash_point(idx=-1;
  动作 op 内取,缺席/越界 = 守卫断言,op-layer.md §1.1 :35)
→ 置选卡 pending → 直发策略产实例派发
  (动作 op 内:容器取点 → mouse_move + click → 1.2s[选卡 → 弹窗关闭动画窗]
   → 自上报 report_action_pick_expert_invite_param)
  (机械交回零判效;落地归决策动作 node 顶部重入裁决)
```

交互事实(点选语义):点选一个角色卡 → 该角色加入商店(由正常商店逻辑接管);点「现金为王」→ +4 金;弹窗关回备战。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 重入裁决弹窗不在(选卡落地) | **画面终结** | 补写 `chosen_expert`(仅卡分支)+ `ConfirmExpertCash` 到账登记(仅现金分支)→ round_success 交回外循环重分发 |
| 重入裁决弹窗在(点击未落地) | 节点循环重入 | 重走选卡(`round_wait` 循环推进,不烧节点重试预算,无防御上限) |
| 入口门弹窗未现 | op FAIL | 交回外循环按下一帧画面重分发(自愈;开卡缺位归备战词表 OpenBookcard 链) |
| 决策无有效输出(返回词表外/None)/ idx 域外 / 策略异常 | 守卫 fail(op FAIL / 异常上抛) | round_fail(含原值)交回外循环 / 框架异常路径(留证截图 + `node_max_retry_times=6` 预算耗尽)fail;连续 fail 由外环 fail 重派网兜底([flow/README.md](../flow/README.md) §4) |
| 无 match(局外) | 不设早退支(op-layer §1.1;用户裁决 2026-09-22 全族删门) | 未支持用法:单跑缺上下文沿正常链路自然失败,局内不达此态 |

「确认离开 = 画面终结」= [README.md](README.md) §6。

## 6. 状态上报面

- 弹窗载体观察:`report_screen_expert_invite_obs` 载体写容器 `expert_invite` 槽(`ExpertInvitePayload` card_bonds/board/card_points/cash_point 四字段同门一并写)。
- `chosen_expert` write_logic(重入裁决点写;仅卡分支,值 = 该卡羁绊原文名——chosen_expert 语义 = 受邀专家羁绊;「现金为王」= 无专家受邀,不写)。
- 到账登记 `ConfirmExpertCash`(`kernel/cw_exec_state.py::apply_confirm_effect` dict 分支,gold +4 固定回金;仅现金分支)。⚠️ 与投资策略卡「现金为王」撞名两实体、效果域不同,按画面域限定匹配禁跨屏按名(fields.md §4)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.5 / §4「事件选择」;到账登记 = [../game_state/logic-updates/op-effects.md](../game_state/logic-updates/op-effects.md) §2(ConfirmExpertCash 行)。

## 7. 子态与 overlay

本屏无子态。书册卡本体(备战席占槽道具,模板 = `assets/template/currency_war/supply/书册卡_未知.png`,识别 = `obs/cw_identity_obs.py::find_bookcards`)属备战画面域,非本屏子态。

## 8. 守卫与防线

- 板面读数失败 → 现金为王兜底(kernel 判据侧合法缺省 = `choose_expert_index` board 空返 -1,观察域语义,非流程侧决策兜底;决策出口处置见守卫两条)(观察读数转换失败态 = None/{} 照报,现役为 [op-layer.md](op-layer.md) §1.1 观察标准化门(:34)欠账形态;收敛方向 = 转换失败 round_fail 零写零上报或屏契约登记转换成功性边界——本屏现按后者登记,见 §3 转换成功性边界)。
- 决策返回契约守卫:decide_expert_invite 返回 None/词表外 = 具名 round_fail 零盲发、策略异常自然传播(原「决策链异常降级同直调」退役申报)。
- 值域守卫:pick idx 域外 = 守卫断言 AssertionError,域 = 0..3 ∨ -1(原「idx<0 静默并入现金分支」退役申报)。
- 选卡坐标缺席/越界 = 动作 op 容器取点守卫断言 AssertionError(坐标单一真相源 = 观察上报,[op-layer.md](op-layer.md) §1.1 :35,动作 op 按下标自容器 `expert_invite` 取,禁现算回退;原「决策半 area 缺坐标 round_fail」随坐标收敛迁出)。
- 落地裁决点写(防未落地轮留幻影登记);记录面失败不阻塞收案。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「专家邀请函」;op 内日志 tag = `[cw-bookcard]`(board/卡羁绊/选卡描述)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(节点循环族两 node 形态锁:观察上报容器含坐标域/入口门 miss fail)、test_cw_unified_action_2c.py(决策出口守卫锁组 `test_expert_invite_decision_*`:返回契约/值域/异常传播/正路两态/局外无早退支自然失败 + report 双写同门等长守卫锁)、test_cw_unified_action_4.py(expert 容器双源取点与缺席/越界守卫二态锁)、test_cw_game_state_consume.py(chosen_expert 接线锁);`choose_expert_index` 纯函数行为锁同仓。代码注引的接线锁(test_cw_node_screens)已不在册(开放设计注)。
- game 侧知识:画面与书册卡机制 = [../../../../game/screens/currency_war_expert_invitation.md](../../../../../game/screens/currency_war_expert_invitation.md)。
