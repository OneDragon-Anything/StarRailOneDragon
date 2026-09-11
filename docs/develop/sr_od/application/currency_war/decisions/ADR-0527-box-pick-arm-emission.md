# ADR-0527:武装箱选卡臂发射位(OpenBox 假成功判据 + 臂缺位根修)

日期:2026-09-05。状态:已实施(第十八局停场热修;落地审由编排者后续走)。

## 背景(现场)

第十八局(g_20260905_175220)备战 2-2:「简易武装箱 请选择1个」对话框在场
15+ 分钟,备战环空转(OpenBox/ClickSpheres ~80 次,行动流见对局档案),
出战被阻 → stop_run 保场。

## 根因(两层)

1. **OpenBox 假成功判据**:`prep_actions.PrepActionExecutor._open_box` 点
   「开启」后的成功验证 = 轮询「货币战争-备战-武装箱选择」屏
   `标识-请选择`——对话框**已开**时该轮询恒真 → OpenBox 每轮"成功"重开,
   不产生任何消费(重开非幂等动作的幂等误判)。
2. **选卡臂缺位(本 ADR 主根修)**:观测字段 `PrepObservation.
   box_overlay_open`(`cw_screen_prep`)已在库,但决策入口
   `mandate_v1/entry.emit` ① prep 实体面只有 boxes/tomes/spheres/
   event_overlay 四臂,无消费该字段的发射位 → 弹窗后无人发 PickBoxCard。
   下游机械(执行器 `_pick_box_card`、期望态投影 `cw_expected_state`、
   adapter 注册)均早已在库,单缺发射位一行。

## 裁决与修法

- **臂补位**:`entry.emit` ① prep 实体面**首位**补
  `box_overlay_open → PickBoxCard(reason='prep_box_pick')`。
- **选卡优先防重开**(裁定):选卡臂置于 boxes 臂之前——对话框在场帧
  bench 箱读数可能假阳(弹窗覆盖/遮挡不确定),先发选卡消费弹窗,
  禁止 OpenBox 在对话框在场帧再发射(重开空转根因回归锚)。
- OpenBox 假成功判据**本批不改**(其轮询语义在「弹窗未开→等弹出」场景
  仍正确);重开空转由选卡臂优先级封死。若未来出现「OpenBox 在无箱帧
  假成功」新形态,另立判据批(轮询加负向锚:备战栏箱读数消失)。

## 锁(test_cw_box_pick_arm.py,3 条)

1. 箱对话框在场 ⇒ 首发射 = PickBoxCard('prep_box_pick');
2. 对话框在场帧禁再发 OpenBox(重开空转回归锚);
3. 对照:对话框未开 ∧ bench 有箱 ⇒ 照常 OpenBox(既有臂零回退)。

## 边界

- 遭遇面板/投资策略浮层等其他弹窗形态不在本 ADR 辖域(各有 0 系分发/
  达标臂浮层排除承载,ADR 层面见各自审查记录);
- 概率条轮岗语义见 `cw_economy.effective_refresh_prob`(单一源)。
