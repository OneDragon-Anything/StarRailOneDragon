# 补给节点(supply · 货币战争-补给)

> 代码 = `operations/cw_screen/cw_screen_supply_node.py::CwScreenSupplyNode`(两 node 直继承 `SrOperation`)。职责:补给阶段一次访问——动态 N 选 1 装备列观察(含刷新剩余次数)→ `decide_supply` 一选 → 刷新(终结动作交回)或选卡确认链派发(派发即终结)→ 交回外循环;**节点完成模型 = 标识门复检**(门 miss = overlay 消失/进入下一节点 = 节点完成交回)。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_supply.yml`。

## 1. 分发判定

- 阶段一身份分发(号制已退役,不引 0x):id_mark 锚「货币战争-补给.标识-补给阶段」(位置区分 area,防「补给阶段」与「备战阶段」共享「阶段」误匹配)。单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。
- 补给是唯一无结算屏节点:op success 后交回外循环重判(无合成结算行)。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。**派发即终结形态**(投资两屏/遭遇同族,合同 = [op-layer.md](op-layer.md) §1.1),两 node 直继承 `SrOperation`:观察 node = 节点完成门(`_in_node`:标识锚还在;已离开 = 节点完成 round_success 交回外循环)→ 选项一次读 + 刷新剩余读数 → `report_screen_supply_node_obs` 落容器 `supply` + `supply_refresh_left` → obs + 点卡定位点/刷新锚点挂实例属性。决策动作 node = 顶部节点完成复检(每轮新帧,分发身份安全网)→ 零参决策 `match.strategy.decide_supply()`(候选自容器 `supply` 槽;缺省实现委托 `kernel/cw_events.py::decide_supply`,规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E4)→ 单动作(刷新终结交回 ∨ 选卡确认链经 `CwActionPickSupplyOp` 派发即 round_success 终结,机械链 + **即时单相上报**在动作 op 内)。确认未生效 = 代码 bug,overlay 残留由外循环按当前画面重识别重派(零重入裁决、零落地相补写面)。

## 3. 观察面

观察 node = 节点完成门(`_in_node`)+ 选项一次读(每访问恰一次,决策轮复用实例载体不重读)。选项读取 `obs/cw_node_obs.py::read_supply_options`:

- **列数动态探测**(通常 4 选 1;augment 改写下实测 3-5 不等,禁写死):装备行(y 640-780)定义列,角色行(y 500-600,roster 校验滤噪)按 x 就近配对(x 容差常量);
- 钻识别双通道:主 = SIFT(装备 icon 带扫三钻模板,`cw_equipment` 模板库)、兜底 = 装备名精确匹配三钻集合(非子串,防带钻字误判);
- 每列产出 `(SupplyOption(idx, char, equip, has_diamond), 卡身点击点)`。

刷新剩余读数 `_read_refresh_anchor`:「文本-剩余次数」建档 rect 外扩 OCR 带 +「剩余次数:N」正则 → `(count, Point)` 双出(同帧同源,count 供闸与快照、point 供刷新臂文本锚定);读缺 = None。

观察 payload = `CwScreenSupplyNodeObs`(`in_node`/`options`/`refresh_left`/`screen`,住 `kernel/cw_screen_report/supply_node.py`);report = `report_screen_supply_node_obs` 摄入候选写容器 `supply` 域(空 = 读缺不写,闸在 report 内)+ **`refresh_left` 摄入 `supply_refresh_left`**(剩余语义观察写端,读缺跳写、逐访问覆盖)。节点推进锚定写端 = 本观察 node(补给屏节点条 → kernel `observe_node_anchor`)。决策零参读容器槽。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionPickSupplyOp`(`CwActionPickSupplyParam`) | 注册表工厂 `action_op_for`(决策半组装 `OverlayPickExecEnv`:卡身定位点/归一件名/角色名/选中下标) | **即时单相自上报** `report_action_pick_supply_param`(确认点击后一口写 owned 规范名 + 单位腿 `grant_bench_unit_cascade` + 装备后果腿 `apply_equip_acquire_consequence`;内容全未知/名未解析 = 翻来源留证禁猜)+ 节点推进 `report_node_advance(supply_confirm)`(确认点击落地即上报,重复上报被 kernel 观察态门挡) | **是(派发即终结)**:发出后 round_success 终结交回外循环;确认未生效由外循环重识别重派 |
| 刷新重掷(无注册表动作 op;`CwActionRefreshSupplyParam` 仅策略建议载体) | 画面 op 留守臂(容器 `supply_refresh_left` 剩余闸 + 锚点对照闸放行:「文本-剩余次数」锚定偏移 `mouse_move`+`click`) | 无自上报(刷新 = 终结交回,新装备面由外循环重进后的入口观察现读承载) | **是(终结)**:点钮 + 2s 动画窗后 round_success 交回;闸拒绝(剩余 ≤0 或 None 或锚点缺)→ 零点击,重调一次决策按原评分选;重调仍建议刷新(闸数据不一致)→ 零点击终结交回 |

决策动作 node 单动作体 `_do_action`(零参:候选与点击点自观察轮实例载体消费):

```
opts = 观察轮实例载体;_left = 容器 supply_refresh_left(观察轮 report 摄入)
pick = match.strategy.decide_supply()(零参;候选读容器 supply 槽)
├─ 闸拒绝(pick.refresh ∧ (left ≤0 ∨ None ∨ 锚点缺))→ 重调一次按原评分选;
│    重调仍建议刷新 = 闸数据不一致 → 零点击终结交回(外循环重进重试观察)
├─ 刷新形态(终结动作):pick.refresh ∧ 闸放行 →
│    文本锚点 + 偏移 _REFRESH_BTN_DX(-100)点圆钮一次 → 固定等待 2s
│    (重掷动画覆盖)→ 动作已发,round_success 终结交回
│    (点钮即终结交回 = 外循环重进入口重建;新装备面由重进后选项现读承载)
└─ 选卡形态:target = opts[pick.idx][1](卡身点击点,y≈550,点卡身不开对话直接选中;
     无选项/无 match 兜底 = CARD_BODY 屏中常量(900,550))
     → chosen_supply 确认即写(点击链发射前单点直写:(char, equip, has_diamond);
       兜底点卡/刷新轮不写 = 真选守卫)
     → mouse_move + click → 0.6s → 点「按钮-确认」(round_by_find_and_click_area,
       success_wait 1.5)→ 动作 op 即时单相上报完整结果 + supply_confirm 推进
```

选定快照 `picked`(角色/装备/钻 + `refresh_left` 容器现值快照)= 选定事实现场载荷,现役消费面 = 零(遥测接线候批);刷新轮/兜底点卡轮不带快照。选卡+确认+即时上报整体经动作工厂(`cw_overlay_pick_action.py::CwActionPickSupplyOp`;归一件名 = 注册表级分层归一 `normalize_registry_equip_name` 现算:精确快道 → containment longest-first → 相似救援唯一命中,多/零命中 = '' 禁猜翻来源留证)。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 门 miss(标识消失;observe 首门 / act 每轮复检) | **节点完成** | 纯观察出口验真 → round_success 交回外循环重判(补给无结算屏) |
| 刷新点击 | **终结动作** | round_success 交回外循环重进 = 入口重建(闸 = 容器 `supply_refresh_left` 剩余语义真值) |
| 选卡确认链派发 | **派发即终结** | round_success 交回外循环;确认未生效由外循环重识别重派 |
| 闸数据不一致(重调仍建议刷新) | 零点击终结 | round_success 交回外循环重进重试观察(防每轮空转烧尽节点预算) |

## 6. 状态上报面

- `chosen_supply` write_logic(**确认即写**,选卡分支单点直写、点击链发射前;值 = (角色, 装备, 有钻石);兜底点卡/刷新轮无选定不写,None 保持「无记录」)。口径申报:supply 确认即写,chosen_tome 维持「出口验真后写」家族口径——差异理由 = supply 的中转暂存宿主随执行层状态类目退役(git 历史可溯),直写是载体消亡后的唯一形态;确认未落地窗内容器短暂持未落地选定,现无决策读者,低危可接受,出口验真保留为观察面。
- 候选观察:`report_screen_supply_node_obs` 摄入候选写容器 `supply` 域(空 = 读缺不写)+ `supply_refresh_left` 摄入(读缺跳写)。
- **效果逻辑态单相上报**(`kernel/cw_action_report/pick_supply.py::report_action_pick_supply_param`,即时单相):owned += 规范名(归一件名)+ 单位腿(角色入席 + 合成级联)+ 装备后果腿(命中后果表送角色 → bench + 级联);内容全未知/名未解析 = 受影响域值不变翻来源 + 缺陷留证(fail-closed,错名不入账由观察覆盖自愈)。
- 节点推进:`report_node_advance(trigger='supply_confirm')`(确认点击落地即上报;kernel 观察态门 = 唯一推进落账门)。
- 刷新剩余:容器 `supply_refresh_left`(观察写端 + sim 写端:补给节点入口先写初始 left=1、刷新 left−1 ≥0 截断);旧 `supply_refresh_used` 已用计数已退役(剩余语义化)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.2 / §4「事件选择」;到账登记 ConfirmSupply 行已退役(即时单相上报取代)。

## 7. 子态与 overlay

本屏无子态。建档在册「文本-已选择」「按钮-返回备战界面」area 为画面元素档,本 op 不消费(选中态不判读;返回按钮归外循环/其他链)。

## 8. 守卫与防线

- 刷新单次:闸 = 容器 `supply_refresh_left` 剩余语义观察真值(≤0 或 None = 拒绝;读缺 = 少刷一次机会非卡死面,活锁方向安全);拒绝 → 重调一次落选卡;重调仍建议刷新 → 零点击终结交回(防「建议刷新→锚读缺→零动作」每轮空转烧尽节点预算)。
- 出口验真:节点完成 = 标识消失(位置 area,非全屏 LCS);派发即终结形态下循环面已消(刷新终结/选卡终结/节点完成三出口)。
- 兜底点卡 CARD_BODY 仅在无选项/无 match 时使用;有选项而决策越界 = target 保持兜底点(有界重试兜底,非盲选禁令屏)。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「补给节点」;op 内日志 tag = `[cw-supply]`(options/pick/click、闸拒绝告警、闸不一致零点击告警、chosen 记录失败告警)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/` 下 test_cw_obs_arch_event_screens_step3.py(supply 两 node 行为锁:chosen 确认即写/刷新终结)、test_cw_runnode_retire.py(旧节点基类退役等价)、test_cw_game_state_consume.py(chosen_supply 接线)、刷新闸行为锁(剩余 1 点钮恰一次终结/0 与 None 零点击按原评分选)、sim 补给刷新段测试(初始 left=1 与 left−1 截断)。
- game 侧知识:画面与机制(动态列数/钻) = [../../../../game/screens/currency_war_supply.md](../../../../../game/screens/currency_war_supply.md);装备价值 = [../../../../game/currency_war/research/equipment_mechanics.md](../../../../../game/currency_war/research/equipment_mechanics.md)。

## 开放设计注

- 刷新 = 终结动作(全域规范 = [op-layer.md](op-layer.md) §1.4):建议刷新 ∧ 闸放行 → 点钮一次 → round_success 交回外循环重进 = 入口重建,新装备面由重进后的入口观察现读承载。
- 补给刷新次数的源口径(优势布局授予 vs 官方节点表「原生可刷 1 次」)收窄待证,登记 = fields.md §3.4.2;剩余语义读数直接消费游戏屏显真值,不依赖该先验;结论出来前禁把「无此刷新」当回归断言。
