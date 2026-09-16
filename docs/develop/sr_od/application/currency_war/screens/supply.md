# 补给节点(supply · 货币战争-补给)

> 代码 = `operations/cw_screen/cw_screen_supply_node.py::CwScreenSupplyNode`(CwScreenOpBase 子类)。职责:补给阶段一次访问——动态 N 选 1 装备列观察 → `decide_supply` 一选 →(按需)刷新(节点循环内终结语义)→ 点列卡身 + 确认;**节点完成模型 = observe 门复检 + 节点预算**(committed-but-verifying:验证 overlay 消失才完成)。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_supply.yml`。

## 1. 分发判定

- 外循环分支 0e1:id_mark 锚「货币战争-补给.标识-补给阶段」(位置区分 area,防「补给阶段」与「备战阶段」共享「阶段」误匹配)。分发 = 阶段一身份行,单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。
- 补给是唯一无结算屏节点:op success 后交回外循环重判(无合成结算行)。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。**committed-but-verifying 节点循环**形态:每轮 = observe 门(`_in_node`:标识锚还在?)→ 已离开 = 节点完成 round_success;仍在 = 做一个动作(`_do_action`)→ round_retry 重跑本节点(计 `node_max_retry_times=8` 预算,超 → FAIL bail)。五相位屏:装配点分流;decide+act 内聚于 `_do_action`(两路径共享零转录);本屏无 on_outcome 落地登记件。决策入口 = 契约 `decide_supply(options, gs, session, config, refresh_used)`(委托 `kernel/cw_events.py::decide_supply`;规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E4)。

## 3. 观察面

observe 段 = 节点完成门(`_in_node`)+ 轻观察帧引用(选项读取归 decide 段动作体现役内聚,避免新增读屏);门通过前先弃上轮选定暂存(防陈旧选跨轮/跨节点误写)。选项读取 `obs/cw_node_obs.py::read_supply_options`:

- **列数动态探测**(通常 4 选 1;augment 改写下实测 3-5 不等,禁写死):装备行(y 640-780)定义列,角色行(y 500-600,roster 校验滤噪)按 x 就近配对(x 容差常量);
- 钻识别双通道:主 = SIFT(装备 icon 带扫三钻模板,`cw_equipment` 模板库)、兜底 = 装备名精确匹配三钻集合(非子串,防带钻字误判);
- 每列产出 `(SupplyOption(idx, char, equip, has_diamond), 卡身点击点)`。

观察 payload = `SupplyObservation`(仅帧引用)。本屏不上报 GameState 容器观察(决策输入 = `game_state_of(match.session)` 视图)。

## 4. 动作面

decide+act 内聚 `_do_action`(两路径共享):

```
opts = read_supply_options(ctx, screen);refresh_used = 容器 supply_refresh_used
  计数对照(>0 = 已用;无 match 退实例旗标,测试/离线路径)
pick = decide_supply([o for o,_ in opts], game_state_of(session), ..., refresh_used)
├─ 刷新形态(节点循环内终结语义):pick.refresh ∧ 未用 →
│    文本锚:「文本-剩余次数」建档 rect 外扩 OCR 带 +「剩余次数:N」正则
│    → 实例旗标置位 + 容器计数单点写(write_logic +1,不等验效;
│      本屏无 on_outcome 注册件,无双计面;锚读缺 = 零点击但照常置位——
│      防「建议刷新→锚读缺→零动作」每轮空转烧尽节点预算的活锁)
│    → 锚命中:点锚 + 偏移 _REFRESH_BTN_DX(-100)→ 固定等待 2s
│      (重掷动画覆盖)→ return
│    (round_retry 重进节点 = 入口重建;新装备面由重进后选项现读承载)
└─ 选卡形态:target = opts[pick.idx][1](卡身点击点,y≈550,点卡身不开对话直接选中)
     → 无选项/无 match 兜底 = CARD_BODY 屏中常量(900,550)
     → mouse_move + click → 0.6s → 点「按钮-确认」(round_by_find_and_click_area,
       success_wait 1.5)→ 选定确认时点直写容器 chosen_supply
       (char, equip, has_diamond)→ 到账登记 ConfirmSupply(owned += equip)
```

刷新轮不走选卡分支(选定快照保持 None;兜底点卡轮同样不带快照,决策帧照写但不带选择字段,读端按 None 分型)。动作词表:画面 op 直驱(无 `CW_ACTION_TYPES` 成员)。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| observe 门复检 miss(标识消失) | **节点完成** | 出口验真(纯观察面;chosen_supply 已改确认即写,门处无写动作)→ round_success 交回外循环重判(补给无结算屏) |
| 刷新点击 | 本轮动作即返回 | round_retry 重进节点 = 入口重建(节点内至多刷 1 次由容器 `supply_refresh_used` 计数对照硬限制) |
| 确认未落地 | 节点循环重入 | 下一轮 observe 门仍在 → 重走(计预算,超 `node_max_retry_times=8` → FAIL bail) |

## 6. 状态上报面

- `chosen_supply` write_logic(**确认即写**,选定确认时点单次逻辑写入豁免;值 = (角色, 装备, 有钻石);兜底点卡/刷新轮无选定不写,None 保持「无记录」)。口径申报:supply 确认即写,chosen_tome 维持「出口验真后写」家族口径——差异理由 = supply 的中转暂存宿主随执行层状态类目退役(git 历史可溯),直写是载体消亡后的唯一形态;确认未落地窗内容器短暂持未落地选定,现无决策读者,低危可接受,出口验真保留为观察面。
- 到账登记 `ConfirmSupply`(`kernel/cw_exec_state.py::apply_op_effect` dict 分支,owned += 装备名;equip 未读到 = 不登记)。
- 刷新已用:容器 `supply_refresh_used` 计数在产——**live 写端 = 本 op 刷新分支单点 write_logic +1**(发射即记不等验效;本屏无 on_outcome 注册件,无双计面),sim 引擎经 observe 通道在写,两源同域;读点 = 刷新链容器计数对照(>0 = 已用)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.2 / §4「事件选择」;到账登记 = [../game_state/logic-updates/op-effects.md](../game_state/logic-updates/op-effects.md) §2(ConfirmSupply 行)。

## 7. 子态与 overlay

本屏无子态。建档在册「文本-已选择」「按钮-返回备战界面」area 为画面元素档,本 op 不消费(选中态不判读;返回按钮归外循环/其他链)。

## 8. 守卫与防线

- 刷新单次硬限制:容器 `supply_refresh_used` 计数对照(>0 = 已用),发出点击即 +1(不等验效,防「点偏未生效重入屏反复尝试」);锚读缺零点击 + 照常置位(防「建议刷新→锚读缺→零动作」每轮空转烧尽节点预算的活锁)。
- 出口验真:节点完成 = 标识消失(位置 area,非全屏 LCS);未落地轮重走计预算,预算耗尽 FAIL bail(不无限烧)。
- 兜底点卡 CARD_BODY 仅在无选项/无 match 时使用;有选项而决策越界 = target 保持兜底点(有界重试兜底,非盲选禁令屏)。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「补给节点」;op 内日志 tag = `[cw-supply]`(options/pick/click、锚读缺告警、chosen 记录失败告警)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/` 下 test_cw_runnode_retire.py(旧节点基类退役等价)、test_cw_game_state_consume.py(chosen_supply 接线)、test_cw_obs_arch_event_screens_step3.py(生命周期结构)。
- game 侧知识:画面与机制(动态列数/钻) = [../../../../game/screens/currency_war_supply.md](../../../../../game/screens/currency_war_supply.md);装备价值 = [../../../../game/currency_war/research/equipment_mechanics.md](../../../../../game/currency_war/research/equipment_mechanics.md)。

## 开放设计注

- **补给刷新的终结语义候裁**([README.md](README.md) §8 申报,裁决落本篇):按「刷新 = 唯一引入新事实的动作」原则刷新应为终结 op;现行 as-built = 节点循环内刷新(点刷新 → 固定等待 → round_retry 重进节点 = 入口重建,`_supply_refresh_used` session 态防重入)——行为语义与「终结 → 交回 → 外循环重进 → 入口重建」连续,但终结级别归类(访问终结 vs 节点内动作)未定案,保持候裁不自行收敛。
- 补给刷新次数的源口径(优势布局授予 vs 官方节点表「原生可刷 1 次」)收窄待证,登记 = fields.md §3.4.2;结论出来前禁把「无此刷新」当回归断言。
