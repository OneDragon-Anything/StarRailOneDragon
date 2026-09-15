# 专家邀请函(expert_invite · 货币战争-备战-专家邀请函)

> 代码 = `operations/cw_screen/cw_screen_expert_invite.py::CwScreenExpertInvite`(CwScreenOpBase 子类;默认策略纯函数 = 同文件 `choose_expert_index`)。职责:书册卡开卡后弹出的专家邀请函选卡——读板面阵营 → 默认策略选卡(羁绊同线优先,兜底现金为王)→ 点卡 → 弹窗关 = 选卡落地(重入裁决收案)。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_expert_invitation.yml`。

## 1. 分发判定

- 外循环分支 0k:id_mark 锚「货币战争-备战-专家邀请函.标识-专家邀请函」;命中即接管(同 0i)。分发 = 阶段一身份行,单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。
- 处理链分工:开卡半 = 备战词表 `OpenBookcard`(`kernel/cw_vocab.py` 在册;执行器 = `cw_open_bookcard_action.py::OpenBookcardOp`,发射位 = 备战环入口清场段 `cw_screen_prep.py::CwScreenPrep._clear_prep_cards`,开卡即交回)→ 弹窗由 0k 按画面分发本 op——**本 op 只辖弹窗已开后的选卡**,入口态单一 = 弹窗已开。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。五相位屏,单节点 `choose`(选卡+落地裁决内聚):重入裁决先于装配点分流(选卡 pending = 上轮已发的 `(idx, card_bonds)` 快照;弹窗不在 = 选卡落地 → 补写 chosen_expert + 现金分支到账登记 + success;弹窗在 = 未落地 → 重走计预算);门后读板面+选卡+机械交回链纯移入 `_handle_overlay`(两路径共享零转录);无 on_outcome 落地登记件。选卡判据 = 本文件默认策略纯函数 `choose_expert_index`(非 pick 族九接口;判据见 §4,单测锁行为)。

## 3. 观察面

observe 段 = 弹窗在场门(「标识-专家邀请函」;miss = round_fail 交回外循环重识别自愈)+ 轻观察帧引用;读数归共享动作体:

- 板面阵营 `obs/cw_observation.py::read_board`(弹窗帧左侧羁绊面板透出可读;读数失败 = 空 dict 走现金为王兜底,告警不阻塞);
- 卡羁绊解析 `_resolve_card_bonds`(逐卡 area 约束 OCR):文本精确命中 `data/cw_factions.py::FACTIONS` 键 → 文本含键(OCR 噪声容错)→ 文本 = `data/cw_chars.py::CHARACTERS` 角色名取其首个羁绊(factions 优先,空则 flows)→ 全未命中 = None(策略层走兜底)。

观察 payload = `ExpertObservation`(仅帧引用);本屏不上报 GameState 容器观察。

## 4. 动作面

选卡链 `_handle_overlay`(两路径共享):

```
board = read_board(ctx, screen)(失败 = {} 兜底)
card_bonds = [四张卡逐一解析羁绊]
idx = choose_expert_index(card_bonds, board):
  ① 主力阵营(在场计数最大,并列取名字序首个保证确定性)同线卡优先;
  ② 次选与任一在场阵营(board 计数 >0)同线卡(羁绊面板口径 = factions∪flows
    并计,卡上标签同属一个羁绊命名空间);
  ③ 全无同线 / board 空 / card_bonds 空 → -1(现金为王:选卡无依据时
    经济兜底优于盲选)
area = 「卡-现金为王」(idx<0)∨「卡-1..4」→ area_center 缺失 = round_fail
→ mouse_move + click → 1.2s(选卡 → 弹窗关闭动画窗)
→ 置选卡 pending → round_retry(机械交回零判效;落地归 choose 顶部重入裁决)
```

交互事实(点选语义):点选一个角色卡 → 该角色加入商店(由正常商店逻辑接管);点「现金为王」→ +4 金;弹窗关回备战。动作词表:画面 op 直驱。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 重入裁决弹窗不在(选卡落地) | **画面终结** | 补写 `chosen_expert`(仅卡分支)+ `ConfirmExpertCash` 到账登记(仅现金分支)→ round_success 交回外循环重分发 |
| 重入裁决弹窗在(点击未落地) | 节点循环重入 | 重走选卡(计 `node_max_retry_times=6` 预算,超 → FAIL bail) |
| 入口门弹窗未现 | op FAIL | 交回外循环按下一帧画面重分发(自愈;开卡缺位归备战词表 OpenBookcard 链) |

「确认离开 = 画面终结」= [README.md](README.md) §6。

## 6. 状态上报面

- `chosen_expert` write_logic(重入裁决点写;仅卡分支,值 = 该卡羁绊原文名——chosen_expert 语义 = 受邀专家羁绊;「现金为王」= 无专家受邀,不写)。
- 到账登记 `ConfirmExpertCash`(`kernel/cw_exec_state.py::apply_op_effect` dict 分支,gold +4 固定回金;仅现金分支)。⚠️ 与投资策略卡「现金为王」撞名两实体、效果域不同,按画面域限定匹配禁跨屏按名(fields.md §4)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.5 / §4「事件选择」;到账登记 = [../game_state/logic-updates/op-effects.md](../game_state/logic-updates/op-effects.md) §2(ConfirmExpertCash 行)。

## 7. 子态与 overlay

本屏无子态。书册卡本体(备战席占槽道具,模板 = `assets/template/currency_war/supply/书册卡_未知.png`,识别 = `obs/cw_identity_obs.py::find_bookcards`)属备战画面域,非本屏子态。

## 8. 守卫与防线

- 板面读数失败 → 现金为王兜底(选卡无依据时经济兜底优于盲选;不盲点角色卡)。
- 选卡 area 缺坐标 = round_fail(坐标单一真相源,禁裸坐标兜底)。
- 落地裁决点写(防未落地轮留幻影登记);记录面失败不阻塞收案。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「专家邀请函」;op 内日志 tag = `[cw-bookcard]`(board/卡羁绊/选卡描述)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_event_screens_step3.py`(生命周期段迹锁)、test_cw_game_state_consume.py(chosen_expert 接线锁);`choose_expert_index` 纯函数行为锁同仓。代码注引的接线锁(test_cw_node_screens)已不在册(开放设计注)。
- game 侧知识:画面与书册卡机制 = [../../../../game/screens/currency_war_expert_invitation.md](../../../../../game/screens/currency_war_expert_invitation.md)。
