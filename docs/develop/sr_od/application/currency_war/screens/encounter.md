# 遭遇节点二选一(encounter · 货币战争-遭遇节点)

> 代码 = `operations/cw_screen/cw_screen_encounter.py::CwScreenEncounter`(CwScreenOpBase 子类)。职责:遭遇节点 overlay 一次访问——稳定帧观察(两卡难度/奖励 + 刷新剩余)→ `decide_encounter` 决策 →(按需)分支刷新(访问内重读重选,不终结)→ 点卡选中 + 点「选择」确认机械交回。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_encounter.yml`。

## 1. 分发判定

- 外循环分支 0c:id_mark 锚「货币战争-遭遇节点.标识-遭遇节点」(位置约束 area;全屏 LCS 判据已退役——卡标题 OCR 截断帧会 miss)。分发 = 阶段一身份行,单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。
- 本屏的暗色锁定子态(遭遇锁定)另立 0m 分支(`CwScreenPrepLockedReturn`,见 §7)。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。五相位屏(统一观察架构试点首屏,带刷新链的最复杂代表屏):重入裁决先于装配点分流;两端口在场走五段生命周期、缺省走旧路径;决策入口 = 契约 `decide_encounter(options, gs, session, config, refresh_used)`(双轨:基线核 = `kernel/cw_events.py::decide_encounter`「未成型→低难保生存 / 成型+词缀利→高难拿奖励 / 全克→刷新」;mandate_v1 核 = EV 判据 `strategies/impl/mandate_v1/encounter.py`,语义单一源 = 代码本体;规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1)。重入裁决一件(handle 顶部):确认 pending = 上轮已发确认的选卡快照 `(options, idx)` → 本轮入口锚不在 = overlay 已关(选卡落地)→ 补写 `chosen_encounter` + success;锚在 = 未落地 → 清标志重走(计节点预算)。

## 3. 观察面

入口单次观察(observe 段;决策循环内零读屏)——`_observe_frame`:入口 2s 稳定期(右上「返回备战界面」出现后画面才稳定,时序口径 = [../../../../game/currency_war/research/screen_flow_timing.md](../../../../../game/currency_war/research/screen_flow_timing.md) #23)→ 重截 → 同一稳定帧一次读:

- 选项读取 `obs/cw_node_obs.py::read_encounter_options`:卡标题「遭遇其X」正则 → 难度档(「一」笔画细常漏读,无数字 = 难度 1);奖励带(y 600-695,排「奖励预览」标签)文本按 x 就近归卡;`affixes` 恒空(选项 UI 不显词缀,词缀在未建档的敌方信息覆盖层)——全克刷新判定因此当前恒不触发,执行链就绪待词缀读数通道建立。
- 刷新剩余 `read_encounter_refresh_count`:OCR「剩余次数:N」(矩形带常量,全/半角冒号都认)→ `(剩余次数, 文本中心)`;读缺 = None(失败安全按无刷新)。

观察 payload = `EncounterObservation`(`options`/`refresh_left`/`screen`)。本屏不上报 GameState 容器观察(决策输入 = `game_state_of(match.session)` 视图,overlay 下用上次备战快照语义)。

## 4. 动作面

decide → 分支刷新链 → act,`lifecycle_decision_cycle` 与旧 handle 两路径共享:

```
pick = decide_encounter(options, game_state_of(session), session, config)
  → idx 取 pick.idx(按 pick.idx 选卡,非默认选左)
├─ 分支刷新执行链(不终结;能力源 = 优势布局「分支刷新」,每局 1 次):
│    pick.refresh ∧ 本局未用(ExecState._encounter_refresh_used)
│    ∧ refresh_left 现读 >0(读缺 = 无授权)
│    → _emit_refresh_click(发射即置位防重入 + on_outcome 注册表登记件,§6)
│    → _try_refresh:同帧文本锚(「剩余次数:N」中心)+ 偏移 _REFRESH_BTN_DX(-100)
│      → mouse_move + click → 固定等待 2s(重掷动画覆盖)
│      → 重读选项(读缺 = 空表,保留原候选照常选)
│    → 带 refresh_used=True 重决策 → 按新决策选(「刷没刷成」不判:
│      卡面未变时新观察 = 旧 options,重决策结果天然等价)
└─ act 分派面 _act_execute:置确认 pending(两路径同承共享段头部)
     → 现役确认链 _confirm_default:点卡身选中(「遭遇卡-其一/其二」area center,
       兜底常量 (665,500)/(1288,550))→ 0.8s → 点「选择」确认
       (「按钮-选择」area center,兜底 (1082,898))→ emit_overlay_confirm
       (裁决词「遭遇节点」lcs 0.8;机械交回零判效)
```

交互陷阱:点卡身选中 → 点「选择」确认,**中间勿插空白点击**(会取消选中 → 死循环;防线 = 重入裁决 + 节点预算耗尽 bail);「选择」钮未选中卡时灰置禁用。动作词表:画面 op 直驱;刷新发射载荷 = `EncounterPick`(经 on_outcome 注册表)。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 「选择」确认点击 | 机械交回 | 重入裁决:锚不在 = 补写 chosen + success 交回外循环重分发;锚在 = 重走(计 `node_max_retry_times=10` 预算) |
| 分支刷新 | 不终结 | 留在本画面访问内:重读重选后照常走选卡确认 |
| 入口锚 miss | op FAIL | 交回外循环按当前画面重分发 |

遭遇刷新不终结 = [README.md](README.md) §5.5 刷新语义行;「确认离开 = 画面终结」= [README.md](README.md) §6。

## 6. 状态上报面

- `chosen_encounter` write_logic(出口验真通过分支单次逻辑写入豁免;值 = (难度档, 奖励文本),值取决策所用候选同帧同源;候选未读到/越界 = 盲选 fallback 不写,None 保持「无记录」)。写点 = 重入裁决(标识不在 = 选卡落地)。
- on_outcome 注册表发射型登记件 `encounter_refresh_used`(`EMIT_TRIGGERED_DECLARED` 在册):随刷新点击置位不等验效,`game_state_of(session).write_logic(encounter_refresh_used, +1)`(evidence = `refresh_click`)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.1 / §4「事件选择」;选择落地语义 = fields.md §4(默认不记预期值,后果走观察覆盖)。

## 7. 子态与 overlay

- 暗色锁定子态(遭遇锁定):0m 分支 `operations/cw_screen/cw_screen_prep_locked_return.py::CwScreenPrepLockedReturn` 点右上返回按钮(此态下遭遇锚仍可透出命中,先分流防误派)。
- 「属性详情」面板误触发未建模独立处理:残留归下一帧重入自愈(族注 = [README.md](README.md) §5.5)。

## 8. 守卫与防线

- 刷新单次:发射即置位(`ExecState._encounter_refresh_used`,节点级)防「点偏未生效重入屏反复尝试」;未用/无剩余/已用三态日志可见化。
- 读缺失败安全:refresh_left 读缺 = 无授权;_try_refresh 传入帧读缺 = 空表照常选。
- 验效废除:刷新后无条件重读、确认后零判效;未落地治理 = 重入裁决 + 节点预算耗尽 FAIL bail。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「遭遇节点」;op 内日志 tag = `[cw-encounter]`(options/pick/refreshed/reason、刷新圆钮坐标)。
- 登记件证据 = `refresh_click`;chosen 记录面失败不阻塞(告警行)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_event_screens.py`(迁移结构锁 + 写入流对拍)。
- game 侧知识:画面与交互模型 = [../../../../game/screens/currency_war_encounter.md](../../../../../game/screens/currency_war_encounter.md);分支刷新机制(优势布局授予,每局 1 次)= [../../../../game/currency_war/data/advantage_layouts.md](../../../../../game/currency_war/data/advantage_layouts.md);难度/节点表 = [../../../../game/currency_war/data/competitors.md](../../../../../game/currency_war/data/competitors.md)。
