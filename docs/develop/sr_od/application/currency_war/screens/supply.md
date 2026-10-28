# 补给节点(supply · 货币战争-补给)

> 代码 = `operations/cw_screen/cw_screen_supply_node.py::CwScreenSupplyNode`(两 node 直继承 `SrOperation`)。职责:补给阶段一次访问——动态 N 选 1 装备列观察(含刷新剩余次数)→ `decide_supply` 一选(决策输入与门槛 = 观察产物 obs 载体 `self._obs.options`,两态同构;空候选 = 零点击终结交回,禁盲选)→ 刷新(终结动作返回主循环)或选卡确认链发出(点击发出后即结束本次访问)→ 返回主循环;**节点完成模型 = 标识门复检**(门 miss = overlay 消失/进入下一节点 = 节点完成并结束本次访问)。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_supply.yml`。

## 1. 分发判定

- 阶段一身份分发(旧外循环分支编号已停用):id_mark 识别标志「货币战争-补给.标识-补给阶段」(位置区分 area,防「补给阶段」与「备战阶段」共享「阶段」误匹配)。单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。
- 补给是唯一无结算屏节点:op success 后返回主循环重新判定(无合成结算行)。

## 2. 画面形态声明

**单选族例外**(有选择面但零逻辑态账——逻辑态 = 动作执行后不经观察、按游戏规则推算并直写容器的预期状态,例:买牌后金币 −40、备战席 +1;下一帧观察与推算不符时以实际观察为准,下同;本屏选择不产生逻辑态账,判据 = [README.md](README.md) §3)。**发出即终结形态**(投资两屏/遭遇同族:确认点击发出后即结束本次访问、返回主循环;合同 = [op-layer.md](op-layer.md) §1.1),两 node 直继承 `SrOperation`:观察 node = 节点完成门(`_in_node`:标识识别标志还在;已离开 = 节点完成 round_success 返回主循环)→ 选项一次读 + 刷新剩余读数 → `report_screen_supply_node_obs` 落容器(容器 = GameState,游戏状态对象,下同)`supply` + `supply_refresh_left` → obs + 点卡定位点/刷新定位点挂实例属性。决策动作 node = 顶部节点完成复检(每轮新帧,分发身份安全网)→ 零参决策 `match.strategy.decide_supply()`(决策输入与门槛 = **obs 载体 `self._obs.options` 非空**(两态同构:实机 = 读链同帧产物,sim = 观察改道生成器产物吃容器现值组装——禁挂实例执行载体,纪律正本 = [op-layer.md](op-layer.md) §1.1 实例载体纪律);空候选 = 零点击 round_success 终结交回(外循环重进重建入口重读),**禁盲选派发**——选卡确认不可逆消耗本节点,合同 = [op-layer.md](op-layer.md) §1.1 出口③;无 match 局外不设早退支,画面 op 不支持局外单独调用;**判据单一源 = 策略层 `strategies/impl/mandate_v1/supply.py::decide`**(三级字典序 + 刷新判据,语义正本 = [../strategy-docs/30_supply_screen.md](../strategy-docs/30_supply_screen.md);flow 零参口包装动作类型清单),pick 族接口规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E4 行;E 系编号 = 事件面编号,目录见该篇)→ 单动作(空候选零点击终结 ∨ 刷新结束本次访问 ∨ 守卫①②后选卡确认链经 `CwActionPickSupplyOp` 派发即 round_success 终结,机械链 + **即时单相上报** + 动作回执簿记在动作 op 内)。确认未生效 = 代码 bug,overlay 残留由外循环按当前画面重识别重派(无落地复查环节、无旧机制补写面)。

## 3. 观察面

观察 node = 节点完成门(`_in_node`)+ 选项一次读(每访问恰一次,决策轮复用 obs 载体不重读)。读屏点改道两态(`cw_sim_ports.sim_or_live_observation`):装 sim 后端 → 生成器产物 `cw_sim_obs_gen.gen_supply` 吃容器 `supply` 现值组装(经同名 report 落容器,不回填执行载体);否则执行实机读链(选项 + 刷新锚同帧一次读)。实机读链选项读取 `obs/cw_node_obs.py::read_supply_options`(归并纯函数 `_group_supply_columns` 可离线单测):

- **列数动态探测**(通常 4 选 1;augment 改写下实测 3-5 不等,禁写死):**以角色名坐标定列骨架**(y 500-600 行内识别角色名,roster 校验滤噪;x 序 = 列骨架,列 = 选项 = 角色 + 随选装备组,选中一并获得、非穿戴语义);装备行(y 640-780)按 x 聚簇后按簇心 x 归入最近的角色名列参考点(容差常量;簇心 = 装备名 OCR 文本中心);孤儿簇(该列角色名失读)自成列 char='' 不并入邻列,无装备参考点时成 char-only 列(equip=''——人才储备类变体天然承接);
- 钻识别双通道:主 = SIFT(装备 icon 带扫三钻模板 → 命中点按最近簇心归列,`cw_equipment` 模板库)、兜底 = 装备名精确匹配三钻集合(遍历全列件名,非子串,防带钻字误判);
- 每列产出 `(SupplyOption(idx, char, equip, extra_equips, has_diamond), 卡身点击点)`(equip = 列内画面 y 序首件,extra_equips = 其余件,OCR 原文未归一)。

**执行载体与决策载体分立**:实机读链同步填充实例执行载体 `_card_points`(逐列 `(选项, 点击点)`)/`_refresh_point`(刷新文本锚点)——只被机械执行消费,**禁承载决策输入、禁作决策门槛**(决策输入与门槛一律读 obs 载体 `options`;纪律正本 = [op-layer.md](op-layer.md) §1.1 实例载体纪律;sim 观察改道不回填执行载体,门槛挂错载体 = sim 策略器结构性不可达,补给曾因此盲点兜底无声消耗节点,已根修)。

刷新剩余读数 `_read_refresh_anchor`:「文本-剩余次数」建档 rect 外扩 OCR 带 +「剩余次数:N」正则 → `(count, Point)` 双出(同帧同源,count 供闸与快照、point 供刷新分支文本定位);读缺 = None。

观察 payload = `CwScreenSupplyNodeObs`(`in_node`/`options`/`refresh_left`/`screen`,位于 `kernel/cw_screen_report/supply_node.py`);report = `report_screen_supply_node_obs` 摄入候选写容器 `supply` 域(空 = 读缺不写,闸在 report 内)+ **`refresh_left` 摄入 `supply_refresh_left`**(剩余语义观察写端,读缺跳写、逐访问覆盖)。节点推进的观察核实写端 = 本观察 node(补给屏节点条 → kernel `observe_node_anchor`)。决策零参读容器槽。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「返回主循环」= 本访问结束、控制权返回主循环 `cw_loop.py::CwLoop.loop` 重新识别画面并重判):

| 动作 op(动作类型清单参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionPickSupplyOp`(`CwActionPickSupplyParam`) | 注册表工厂 `action_op_for`(决策半组装 `OverlayPickExecEnv`:卡身定位点(实机 = 执行载体 `_card_points[pick.idx]`;sim = None,机械执行分支端口检查跳过)/归一件名/附加件归一名组/角色名/选中下标——内容载荷自 obs 载体 `options[pick.idx]` 构造) | **即时单相自上报** `report_action_pick_supply_param`(确认点击后一口写角色单位部分 `grant_bench_unit_cascade` + 装备部分 0..n 件 owned 规范名 + 获得后果链 `apply_equip_acquire_consequence`,主件 → 附加件画面 y 序;内容全未知 = 查来源保留证据禁猜,零装备名读数列 = 装备域零写保留证据不发缺陷,名未解析件逐件查来源保留证据)+ 节点推进 `report_node_advance(supply_confirm)`(确认点击落地即上报,重复上报被 kernel 观察态门挡)+ **动作回执 `_note_receipt` 两出口全簿记**(确认点击已发 = reason=''/实机确认定位缺失 = `定位缺失(按钮-确认)`/sim 受理恒 reason='',detail = idx + 内容摘要;receipts 域第 5 处产回执执行链,契约单一源 = [../game_state/fields.md](../game_state/fields.md) 回执契约节) | **是(发出即终结)**:点击发出后即结束本次访问,round_success 终结返回主循环;确认未生效由外循环重识别重派 |
| 刷新重掷(无注册表动作 op;`CwActionRefreshSupplyParam` 仅策略建议载体) | 画面 op 内置动作(内置动作 = 画面 op 内部代码直接执行的固定动作,不经动作注册表派发;对照闸全式 = 容器 `supply_refresh_left` 读数 ≥1 ∧ 锚点分量(实机 = 刷新文本锚 `_refresh_point` 在位,锚缺并入拒绝面防机械点击 None;sim = 无锚点分量恒过)。两态执行:实机 = 文本锚定点 + `mouse_move`+`click`(`_REFRESH_BTN_DX` 固定偏移) + 2s 固定等待;sim = 「文本-剩余次数」area 端口点击(基类 sim 改道 `click_answer` → 后端 `_supply_refresh`:剩余闸内嵌再验 + left−1 + 选项重掷落容器)) | 无自上报(刷新 = 结束本次访问,新装备面由外循环重进后的入口观察现读承载;不接动作回执——刷新 = 画面 op 执行的终结动作,非动作 op) | **是(终结)**:点钮 + 2s 动画窗后 round_success 结束本次访问(sim area 点击后同为终结交回);判据侧次数闸内嵌 decide(仅剩余 ≥1 才可能返刷新建议);建议刷但对照闸拒绝 → 重调一次(纯函数同输入同输出仍建议刷)→ 两态防线:实机 `round_fail` 交回(计入外循环重派上限)/ sim 零点击终结交回 |

决策动作 node 单动作体 `_do_action`(零参:决策输入与门槛 = obs 载体 `self._obs.options`):

```
options = self._obs.options(观察产物,两态同构);_left = 容器 supply_refresh_left(观察轮 report 摄入)
options 空 → 零点击 round_success 终结交回(外循环重进重建入口重读;禁盲选派发)
pick = match.strategy.decide_supply()(零参;候选读容器 supply 槽)
├─ 建议刷但对照闸拒绝(left 读缺/≤0,或实机锚点缺失;sim 无锚点分量不拒)
│    → 重调一次(纯函数同输入同输出仍建议刷)→ 两态防线:
│      实机 round_fail 交回(计入外循环 OP_FAIL_REDISPATCH_LIMIT)/ sim 零点击 round_success 终结交回
├─ 刷新形态(终结动作,闸放行):实机 =「剩余次数」文本锚点 + 偏移 _REFRESH_BTN_DX(-100)点圆钮一次
│    → 固定等待 2s(重掷动画覆盖)→ round_success 结束本次访问
│    (点钮即结束本次访问 = 外循环重进入口重建;新装备面由重进后选项现读承载)
│    sim =「文本-剩余次数」area 端口点击(基类 sim 改道 → 后端 _supply_refresh)→ 同为终结交回
└─ 选卡形态:守卫① pick 非 CwActionPickSupplyParam(词表外/None)→ 具名 round_fail 零盲发
     (消息含策略器原值 repr 留证);守卫② pick.idx 越界 → AssertionError 禁钳位(拦在派发前)
     → chosen_supply 确认即写(点击链发出前单点直写,数据源 = obs 载体 options[pick.idx]:
       (角色, 装备名列表) 2 元组,OCR 原文 y 序,不带钻字段;空候选/刷新轮不写 = 真选守卫)
     → 内容载荷构造(归一件名 = normalize_registry_equip_name 现算,多/零命中 = '' 禁猜)
     → 机械执行两态:实机 target = _card_points[pick.idx][1](卡身点击点,点卡身不开对话直接选中)
       / sim target = None(动作 op 机械执行分支端口检查跳过,世界反应由上报声明链驱动)
     → mouse_move + click → 0.6s → 点「按钮-确认」(round_by_find_and_click_area,
       success_wait 1.5)→ 动作 op 即时单相上报完整结果 + supply_confirm 推进 + 动作回执簿记
```

选定快照 `picked`(角色/首件装备/附加装备 `extra_equips`/钻 + `refresh_left` 容器现值快照)= 选定事实现场载荷,在用消费面 = 零(遥测接线待后续实施;在读渲染方 = `tools/cw/replay_to_md.py` `_supply_entry`);空候选轮/刷新轮不带快照。选卡+确认+即时上报整体经动作工厂(`cw_pick_supply_action.py::CwActionPickSupplyOp`;归一件名 = 注册表级分层归一 `normalize_registry_equip_name` 现算:精确快道 → containment longest-first → 相似救援唯一命中,多/零命中 = '' 禁猜逐件翻来源保留证据)。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 门 miss(标识消失;observe 首门 / act 每轮复检) | **节点完成** | 纯观察出口验真 → round_success 返回主循环重新判定(补给无结算屏) |
| 空候选(obs 载体 `options` 空) | **零点击终结** | round_success 终结交回,外循环重进重建入口重读(禁盲选——选卡确认不可逆消耗本节点) |
| 刷新点击 | **终结动作** | round_success 返回主循环重进 = 入口重建(闸 = 容器 `supply_refresh_left` 剩余语义真值 ∧ 锚点分量两态) |
| 选卡确认链发出 | **发出即终结** | round_success 返回主循环;确认未生效由外循环重识别重派 |
| 对照闸拒绝(建议刷 ∧ 重调仍建议刷;left 读缺/≤0 或实机锚缺) | **两态防线** | 实机 round_fail 交回(计入外循环 `OP_FAIL_REDISPATCH_LIMIT` 重派上限)/ sim 零点击 round_success 终结交回(重进重读即恢复) |

## 6. 状态上报面

- `chosen_supply` write_logic(**确认即写**,选卡分支单点直写、点击链发出前,数据源 = obs 载体 `options[pick.idx]` 与执行载体同帧同源、两态一致;值 = (角色, 装备名列表) 2 元组,OCR 原文 y 序,不带钻字段——有没有钻石由消费侧按 `DIAMOND_EQUIP_NAMES` 名单自列表派生;空候选轮/刷新轮无选定不写,None 保持「无记录」)。口径申报:supply 确认即写,chosen_tome 维持「出口验真后写」家族口径——差异理由 = supply 的中转暂存宿主随执行层状态类目停用(git 历史可溯),直写是载体消亡后的唯一形态;确认未落地窗内容器短暂持未落地选定,现无决策读者,低危可接受,出口验真保留为观察面。
- 动作回执:`note_action_receipt`(receipts 域,`CwActionPickSupplyOp` 两出口全簿记——每执行恰一条回执行:确认点击已发 = reason=''/实机确认定位缺失 = `定位缺失(按钮-确认)`/sim 点击经端口受理恒按已发出簿记 reason='';detail = idx + 内容摘要;screen = `货币战争-补给`)。**第 5 处产回执执行链**(前四处 = prep 统一口/close_shop/open_shop/shop 落地门),契约单一源 = [../game_state/fields.md](../game_state/fields.md) 回执契约节。
- 候选观察:`report_screen_supply_node_obs` 摄入候选写容器 `supply` 域(空 = 读缺不写)+ `supply_refresh_left` 摄入(读缺跳写)。
- **效果逻辑态单相上报**(`kernel/cw_action_report/pick_supply.py::report_action_pick_supply_param`,即时单相):装备部分 = owned += 0..n 件归一规范名(集合 = 首件 + `extra_norm_items`,主件 → 附加件画面 y 序;无装备名读数列时 = 装备域零写 + 保留证据(日志行 + reason `no_equip_column` 载体)、不发缺陷)+ 角色单位部分(角色入席 + 合成级联)+ 获得后果链(命中后果表送角色 → bench + 级联);内容全未知 = 受影响域值不变查来源 + 缺陷保留证据(禁猜);名未解析件 = 逐件值不变查来源 + 缺陷保留证据(fail-closed,错名不入账由观察覆盖自愈,已解析件照常入账)。
- 节点推进:`report_node_advance(trigger='supply_confirm')`(确认点击落地即上报;kernel 观察态门 = 唯一推进落账门)。
- 刷新剩余:容器 `supply_refresh_left`(观察写端 + sim 写端:补给节点入口先写初始 left=1、刷新 left−1 ≥0 截断);旧 `supply_refresh_used` 已用计数已停用(剩余语义化)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.2 / §4「事件选择」;到账登记 ConfirmSupply 行已停用(即时单相上报取代)。

## 7. 子态与 overlay

本屏无子态。建档已登记「文本-已选择」「按钮-返回备战界面」area 为画面元素档,本 op 不消费(选中态不判读;返回按钮归外循环/其他链)。

## 8. 守卫与防线

- 刷新单次:双闸 = 判据侧次数闸内嵌 decide(`gs.supply_refresh_left` ≥1 才可能返建议,None fail-closed)+ op 侧对照闸(全式 = 容器剩余语义观察真值 ≥1 ∧ 锚点分量——实机 = 刷新文本锚 `_refresh_point` 在位(锚缺并入拒绝面防机械点击 None),sim = 无锚点分量恒过;两态分流判别式 = `cw_sim_ports.mechanical_io_allowed()`);建议刷但对照闸拒绝 → 重调一次(纯函数同输入同输出仍建议刷)→ 两态防线:实机 `round_fail` 交回(计入外循环 `OP_FAIL_REDISPATCH_LIMIT` 重派上限,防「锚持续读缺 ∧ 建议刷恒成立」每轮空转,防线先例 = 遭遇屏)/ sim 零点击 round_success 终结交回(拒绝仅剩 left 读缺形态,重进重读即恢复)。
- 出口验真:节点完成 = 标识消失(位置 area,非全屏 LCS);发出即终结形态下循环面已消(空候选终结/刷新终结/选卡终结/对照闸拒绝防线/节点完成五出口)。
- 空候选禁盲选:决策输入与门槛 = obs 载体 `options`,空 = 零点击 round_success 终结交回重读(选卡确认不可逆消耗本节点);**`CARD_BODY` 屏中常量盲点兜底已删除**(兜底派发与禁盲选纪律冲突);无 match 局外不设早退支(画面 op 不支持局外单独调用,缺上下文沿正常链路失败即预期)。
- 守卫断言(对齐遭遇屏双守卫,登记正本 = [op-layer.md](op-layer.md) §1.3):①决策返回非 `CwActionPickSupplyParam`(词表外/None)→ 具名 round_fail 零盲发,消息含策略器原值 repr 留证;②`pick.idx` 越界 → AssertionError 守卫断言禁钳位(越界放行会确认错卡不可逆,必须拦在派发前)。两守卫均在派发前、零点击。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与测试面

- journal op 名 =「货币战争-补给节点」;op 内日志 tag = `[cw-supply]`(options/pick/click、空候选零点击 info、对照闸拒绝两态(实机 round_fail 告警/sim 零点击 info)、chosen 记录失败告警)。
- 测试:`sr-od-test/test/sr_od/application/currency_war/` 下 test_obs_arch_event_screens.py(supply 两 node 行为测试:chosen 确认即写/刷新闸 left 语义(剩余 1 点钮恰一次终结/0 与 None 零点击重调链有界——stub 闸面断言,实机拒绝防线 = round_fail 专属测试)/act 流转形态)、test_cw_screen_supply_node.py(空候选零点击终结、守卫①词表外 round_fail、守卫②idx 越界 AssertionError、对照闸拒绝两态防线(实机 round_fail 计入重派上限形态/sim 零点击终结零派发)、刷新两态(实机锚点+dx 机械点击/sim area 点击触发后端 `_supply_refresh`)、sim 两态 pick 流(decide_supply 被调/内容载荷分支入账/chosen_supply 写行/节点推进))、test_overlay_ops.py(`CwActionPickSupplyOp` 动作回执两出口簿记:实机确认定位缺失 = `定位缺失(按钮-确认)`/sim 受理恒 reason='')、test_cw_game_state_consume.py(chosen_supply 接线)、sim 补给刷新段测试(初始 left=1 与 left−1 截断)、strategies/impl/mandate_v1/test_supply.py(策略单帧测试 + flow 接线)。
- game 侧知识:画面与机制(动态列数/钻) = [../../../../game/screens/currency_war_supply.md](../../../../../game/screens/currency_war_supply.md);装备价值 = [../../../../game/currency_war/research/equipment_mechanics.md](../../../../../game/currency_war/research/equipment_mechanics.md)。

## 开放设计注

- 刷新 = 终结动作(全域规范 = [op-layer.md](op-layer.md) §1.4):建议刷新 ∧ 闸放行 → 点钮一次 → round_success 返回主循环重进 = 入口重建,新装备面由重进后的入口观察现读承载。
- 补给刷新次数的源口径(优势布局授予 vs 官方节点表「原生可刷 1 次」)收窄待证,登记 = fields.md §3.4.2;剩余语义读数直接消费游戏屏显真值,不依赖该先验;结论出来前禁把「无此刷新」当回归断言。
