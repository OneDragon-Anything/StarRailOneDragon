# 补给节点(supply · 货币战争-补给)

> 代码 = `operations/cw_screen/cw_screen_supply_node.py::CwScreenSupplyNode`(两 node 直继承 `SrOperation`)。职责:补给阶段一次访问——动态 N 选 1 装备列观察 → `decide_supply` 一选 →(按需)刷新(终结动作交回)→ 点列卡身 + 确认;**节点完成模型 = 标识门复检**(门 miss = overlay 消失/进入下一节点 = 节点完成交回)。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_supply.yml`。

## 1. 分发判定

- 阶段一身份分发(号制已退役,不引 0x):id_mark 锚「货币战争-补给.标识-补给阶段」(位置区分 area,防「补给阶段」与「备战阶段」共享「阶段」误匹配)。单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。
- 补给是唯一无结算屏节点:op success 后交回外循环重判(无合成结算行)。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。**committed-but-verifying 节点循环**形态,两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 节点完成门(`_in_node`:标识锚还在;已离开 = 节点完成 round_success 交回外循环)→ 选项一次读 → `report_screen_supply_node_obs` 落容器 `supply` → obs + 点卡定位点挂实例属性。决策动作 node = 顶部节点完成复检(每轮新帧)→ 零参决策 `match.strategy.decide_supply()`(候选自容器 `supply` 槽;缺省实现委托 `kernel/cw_events.py::decide_supply`,规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E4)→ 单动作(刷新终结交回 ∨ 选卡确认链经 `CwActionPickSupplyOp` 派发,机械链+自上报在动作 op 内,pick-op-unify 批)→ `round_wait` 循环推进(无防御上限;`node_max_retry_times=8` 现役值仅框架异常路径消费)。确认落地面 = 节点完成门证据闩应用一次(`_apply_supply_landing` → `report_action_pick_supply_param` 落地相:单位腿 + 装备后果腿);`chosen_supply` 确认即写与刷新计数内联写留守决策体(见 §6)。

## 3. 观察面

观察 node = 节点完成门(`_in_node`)+ 选项一次读(每访问恰一次,决策轮复用实例载体不重读)。选项读取 `obs/cw_node_obs.py::read_supply_options`:

- **列数动态探测**(通常 4 选 1;augment 改写下实测 3-5 不等,禁写死):装备行(y 640-780)定义列,角色行(y 500-600,roster 校验滤噪)按 x 就近配对(x 容差常量);
- 钻识别双通道:主 = SIFT(装备 icon 带扫三钻模板,`cw_equipment` 模板库)、兜底 = 装备名精确匹配三钻集合(非子串,防带钻字误判);
- 每列产出 `(SupplyOption(idx, char, equip, has_diamond), 卡身点击点)`。

观察 payload = `CwScreenSupplyNodeObs`(`in_node`/`options`/`screen`,住 `kernel/cw_screen_report/supply_node.py`);report = `report_screen_supply_node_obs` 摄入候选写容器 `supply` 域(空 = 读缺不写,闸在 report 内;match/gs 缺席的局外兜底路径跳过 report)。决策零参读容器槽。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionPickSupplyOp`(`CwActionPickSupplyParam`) | 注册表工厂 `action_op_for`(决策半组装 `OverlayPickExecEnv`:卡身定位点/选定快照/选中下标) | 分步自上报 `report_action_pick_supply_param`:发射相(意图遥测,容器零写)+ 到账登记 `ConfirmSupply`(动作 op 确认收尾);落地相由本 op 节点完成门证据闩(`_apply_supply_landing`)持 `EVIDENCE_OVERLAY_CLOSED` 调用 | 否(非终结):发出后 `round_wait` 循环推进;落地由节点完成门复检判——标识不在 = 落地相应用 + success 交回外循环(见 §5) |
| 刷新重掷(无注册表动作 op;`CwActionRefreshSupplyParam` 仅策略建议载体) | 画面 op 留守臂(`_do_action` 刷新分支:「文本-剩余次数」建档 rect 外扩 OCR 带锚定偏移 `mouse_move`+`click`) | 无自上报(发射即容器 `supply_refresh_used` 计数 +1,内联写留守决策体;锚读缺 = 零点击照常 +1) | **是(访问终结)**:点击 + 2s 动画窗后 `round_success` 即交回,外循环重进 = 入口重建;锚读缺例外 = `round_wait` 留守,下轮按非刷新重选;节点内至多刷 1 次 = 容器计数对照硬限制 |

决策动作 node 单动作体 `_do_action`(零参:候选与点击点自观察轮实例载体消费):

```
opts = 观察轮实例载体(_sup_opts);refresh_used = 容器 supply_refresh_used
  计数对照(>0 = 已用;无 match 退实例旗标,测试/离线路径)
pick = match.strategy.decide_supply()(零参;候选读容器 supply 槽)
├─ 刷新形态(终结动作,ADR-0517):pick.refresh ∧ 未用 →
│    文本锚:「文本-剩余次数」建档 rect 外扩 OCR 带 +「剩余次数:N」正则
│    → 实例旗标置位 + 容器计数单点写(write_logic +1,不等验效;
│      内联写留守决策体;锚读缺 = 零点击但照常置位——
│      防「建议刷新→锚读缺→零动作」每轮空转烧尽节点预算的活锁)
│    → 锚命中:点锚 + 偏移 _REFRESH_BTN_DX(-100)→ 固定等待 2s
│      (重掷动画覆盖)→ return
│    (点钮即终结交回 = 外循环重进入口重建;新装备面由重进后选项现读承载)
└─ 选卡形态:target = opts[pick.idx][1](卡身点击点,y≈550,点卡身不开对话直接选中)
     → 无选项/无 match 兜底 = CARD_BODY 屏中常量(900,550)
     → mouse_move + click → 0.6s → 点「按钮-确认」(round_by_find_and_click_area,
       success_wait 1.5)→ 选卡分支确认即写容器 chosen_supply
       (char, equip, has_diamond;点击链发射前单点直写)→ 到账登记
       ConfirmSupply(owned += equip,动作 op 机械半)
```

刷新轮不走选卡分支(选定快照保持 None;兜底点卡轮同样不带快照,决策帧照写但不带选择字段,读端按 None 分型)。选卡+确认+自上报整体经动作工厂(`cw_overlay_pick_action.py::CwActionPickSupplyOp`;自上报 `report_action_pick_supply_param` = 发射相意图遥测,落地相归节点完成门证据闩;派发 param 携真实选中 idx,到账登记 ConfirmSupply 在彼)。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 门 miss(标识消失;observe 首门 / act 每轮复检) | **节点完成** | 出口验真(纯观察面);act 门先落地相证据闩应用一次(`_apply_supply_landing`)→ round_success 交回外循环重判(补给无结算屏;`chosen_supply` 确认即写不在门) |
| 刷新点击 | **终结动作** | round_success 交回外循环重进 = 入口重建(节点内至多刷 1 次由容器 `supply_refresh_used` 计数对照硬限制) |
| 确认未落地 | 节点循环重入 | 下一轮决策动作 node 门复检仍在 → 重走(`round_wait` 循环推进,不烧节点重试预算,无防御上限) |

## 6. 状态上报面

- `chosen_supply` write_logic(**确认即写**,选卡分支单点直写、点击链发射前;值 = (角色, 装备, 有钻石);兜底点卡/刷新轮无选定不写,None 保持「无记录」)。口径申报:supply 确认即写,chosen_tome 维持「出口验真后写」家族口径——差异理由 = supply 的中转暂存宿主随执行层状态类目退役(git 历史可溯),直写是载体消亡后的唯一形态;确认未落地窗内容器短暂持未落地选定,现无决策读者,低危可接受,出口验真保留为观察面。
- 候选观察:`report_screen_supply_node_obs` 摄入候选写容器 `supply` 域(空 = 读缺不写)。
- 到账登记 `ConfirmSupply`(`kernel/cw_exec_state.py::apply_confirm_effect` dict 分支,owned += 装备名;equip 未读到 = 不登记)。
- 刷新已用:容器 `supply_refresh_used` 计数在产——**live 写端 = 决策体刷新分支单点 write_logic +1**(发射即记不等验效;内联写留守决策体),sim 引擎经 observe 通道在写,两源同域;读点 = 刷新链容器计数对照(>0 = 已用)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.2 / §4「事件选择」;到账登记 = [../game_state/logic-updates/op-effects.md](../game_state/logic-updates/op-effects.md) §2(ConfirmSupply 行)。

## 7. 子态与 overlay

本屏无子态。建档在册「文本-已选择」「按钮-返回备战界面」area 为画面元素档,本 op 不消费(选中态不判读;返回按钮归外循环/其他链)。

## 8. 守卫与防线

- 刷新单次硬限制:容器 `supply_refresh_used` 计数对照(>0 = 已用),发出点击即 +1(不等验效,防「点偏未生效重入屏反复尝试」);锚读缺零点击 + 照常置位(防「建议刷新→锚读缺→零动作」每轮空转烧尽节点预算的活锁)。
- 出口验真:节点完成 = 标识消失(位置 area,非全屏 LCS);未落地轮重走 = `round_wait` 循环推进(无防御上限,不收敛 = 策略 bug 响亮暴露)。
- 兜底点卡 CARD_BODY 仅在无选项/无 match 时使用;有选项而决策越界 = target 保持兜底点(有界重试兜底,非盲选禁令屏)。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「补给节点」;op 内日志 tag = `[cw-supply]`(options/pick/click、锚读缺告警、chosen 记录失败告警)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/` 下 test_cw_obs_arch_event_screens_step3.py(supply 两 node 行为锁:chosen 确认即写/刷新计数写端)、test_cw_runnode_retire.py(旧节点基类退役等价)、test_cw_game_state_consume.py(chosen_supply 接线)。
- game 侧知识:画面与机制(动态列数/钻) = [../../../../game/screens/currency_war_supply.md](../../../../../game/screens/currency_war_supply.md);装备价值 = [../../../../game/currency_war/research/equipment_mechanics.md](../../../../../game/currency_war/research/equipment_mechanics.md)。

## 开放设计注

- 刷新 = 终结动作(ADR-0517,代码已落):建议刷新 ∧ 未用 → 点钮一次 → round_success 交回外循环重进 = 入口重建,新装备面由重进后的入口观察现读承载;节点内至多刷 1 次的硬限制 = 容器 `supply_refresh_used` 计数对照。
- 补给刷新次数的源口径(优势布局授予 vs 官方节点表「原生可刷 1 次」)收窄待证,登记 = fields.md §3.4.2;结论出来前禁把「无此刷新」当回归断言。
