# 遭遇节点二选一(encounter · 货币战争-遭遇节点)

> 代码 = `operations/cw_screen/cw_screen_encounter.py::CwScreenEncounter`(两 node 直继承 `SrOperation`)。职责:遭遇节点 overlay 一次访问——入口帧一次观察(两卡难度/奖励 + 刷新剩余次数)→ `decide_encounter` 决策 → 分支刷新(终结)或选卡确认链派发(派发即终结)→ 交回外循环。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_encounter.yml`。

## 1. 分发判定

- 阶段一身份分发(id_mark 锚「货币战争-遭遇节点.标识-遭遇节点」,位置约束 area;全屏 LCS 判据已退役——卡标题 OCR 截断帧会 miss)。单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。
- 本屏的暗色锁定子态(遭遇锁定)另立锁定子态画面(`CwScreenPrepLockedReturn`,见 §7)。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 画面身份门(「标识-遭遇节点」,miss = round_fail 交回外循环重判)→ **门命中即用 node runner 帧一次读**(候选 + 剩余次数,同帧同源;原「入口 2s 稳定期」已删,用户裁定 2026-09-21,时序口径 supersession 见 [../../../../game/currency_war/research/screen_flow_timing.md](../../../../../game/currency_war/research/screen_flow_timing.md) #23;候选读缺的失败安全 = §4 空候选零点击终结)→ `report_screen_encounter_obs` 落容器 `encounter` 域 + `encounter_refresh_left`(摄入序照先例:options 空整函数早退不写含 left;match/gs 缺席的局外兜底路径跳过 report)→ obs 与刷新文本锚点挂实例属性。决策动作 node = 零参决策(候选自容器 `encounter` 槽;基线核 = `kernel/cw_events.py::decide_encounter`,mandate_v1 现役核 = `bridge.py` 覆写 → `kernel/cw_encounter_selection.py` E-2 判据单一源,历史 EV 核搁置让位保留禁删;规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1)→ **三出口均终结访问**(派发即终结,重入裁决已退役;合同 = [op-layer.md](op-layer.md) §1.1 出口①,投资两屏/补给同形态):①刷新 = 点钮一次 + 2s → round_success 终结;②选卡 = 派发确认链(机械链 + chosen 即时上报在动作 op 内)→ round_success 终结;③空候选 = 零点击终结交回重读。确认未生效 = 代码 bug,overlay 残留由外循环按当前画面重识别重派(修法 = 点击链可靠性)。

## 3. 观察面

入口单次观察(观察 node;决策循环不再读屏)——门命中即读,无稳定期等待:

- 选项读取 `obs/cw_node_obs.py::read_encounter_options`:卡标题「遭遇其X」正则 → 难度档(「一」笔画细常漏读,无数字 = 难度 1);奖励带(y 600-695,排「奖励预览」标签)文本按 x 就近归卡;`affixes` 恒空(选项卡面 UI 不显词缀,词缀住「货币战争-敌人信息浮层」覆盖层——已建档,chips OCR 实测可读,读数通道就绪,接线消费待后续批),全克刷新判定因此当前恒不触发。
- 刷新剩余 `read_encounter_refresh_count`:OCR「剩余次数:N」(矩形带常量,全/半角冒号都认)→ `(剩余次数, 文本中心)`;读缺 = None(= 未观察,闸拒绝)。

观察 payload = `CwScreenEncounterObs`(`options`/`refresh_left`/`screen`,住 `kernel/cw_screen_report/encounter.py`);report = `report_screen_encounter_obs`:候选写容器 `encounter` 域(EncounterPayload;空候选整函数早退不写含 left)+ **`refresh_left` 摄入 `encounter_refresh_left`**(剩余语义观察写端,读缺跳写、逐访问覆盖;None = 未观察 = 拒绝刷新)。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionPickEncounterOp`(`CwActionPickEncounterParam`) | 注册表工厂 `action_op_for`(env 只携宿主 `op`;卡位由动作 op 内读建档 area(缺失 = 显式 round_fail 交回重读,禁兜底坐标),确认钮 = `round_by_find_and_click_area` 全族统一) | **发射即写** `report_action_pick_encounter_param`(`kernel/cw_action_report/pick_encounter.py`:确认点击后立即写 `chosen_encounter`,值组装 = 容器 `encounter` payload 槽 `options[param.idx]`,离屏/越界 = 缺陷留证不写 fail-closed) | **是(派发即终结)**:发出后 round_success 终结交回外循环;落地判定归观察侧(overlay 残留由外循环重识别重派) |
| 分支刷新(无注册表动作 op;`CwActionRefreshNodeOptionsParam` 仅策略建议载体) | 画面 op 留守臂(容器 `encounter_refresh_left` 闸 + 锚点对照闸 → 放行:同帧「剩余次数:N」文本中心锚定偏移 `_REFRESH_BTN_DX`(-100)`mouse_move`+`click` + 2s 固定等待) | 无自上报(刷新 = 终结交回,新选项由外循环重进后的入口观察现读承载,**访问内零重读零二次覆盖写零重决策**) | **是(终结)**:round_success 终结交回;闸拒绝(剩余 ≤0 或 None 或锚点缺)→ 零点击,重调一次决策按原评分选卡落②;重调仍建议刷新(闸数据不一致)→ 零点击终结交回 |
| (空候选,非动作) | — | — | **是**:零点击 round_success 终结交回重读(候选读缺禁盲选派发确认——选卡确认不可逆消耗本节点) |

交互陷阱:点卡身选中 → 点「选择」确认,**中间勿插空白点击**(会取消选中 → 死循环);「选择」钮未选中卡时灰置禁用。确认链整体(点卡 + 确认 + 发射即写)经动作工厂(`cw_pick_encounter_action.py::CwActionPickEncounterOp`);刷新发射零记账(剩余次数 = 观察真值,无计数记账)。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 选卡确认链派发 | **派发即终结** | round_success 交回外循环重分发;确认未生效 = overlay 残留由外循环重识别重派 |
| 分支刷新点钮 | **终结** | 点钮 + 2s → round_success 交回;外循环重进 = 入口重建重观察 |
| 空候选/闸数据不一致 | **零点击终结** | round_success 交回重读(禁盲选、防空转) |
| 入口锚 miss | op FAIL | 交回外循环按当前画面重分发 |

三出口均终结访问,`round_wait` 循环面对刷新建议不存在(活锁方向安全,design §2.0A 同构论证);`node_max_retry_times=10` 现役值仅框架异常路径消费。「确认离开 = 画面终结」= [README.md](README.md) §6。

## 6. 状态上报面

- 候选观察:`report_screen_encounter_obs` 写容器 `encounter` 域(空候选不写)+ `encounter_refresh_left`(剩余语义观察写端)。
- `chosen_encounter`:写端 = **动作侧发射即写**(`kernel/cw_action_report/pick_encounter.py`,用户裁定 2026-09-21 遭遇例外改判,先例 = 投资域 chosen 迁获得链;值 = (难度档, 奖励文本),盲选/越界不写防假值固化;发射即写语义 = 意图记录,确认未生效窗内暂态假值由重派覆盖自愈);**兑现后清(单次消费,见下)**。
- `encounter_reward_claimed`(顶层字段,`tuple[int, str] | None`):遭遇奖励兑现记录 = 最近一次伤害达标兑现的所选值,单槽逐遭遇覆盖。写端 = 结算兑现回调 `kernel/cw_encounter_selection.py::claim_encounter_reward`(挂点 = `CwOpSettleConfirm` 确认点击后、推进上报前):判遭遇 = 双证(node 镜像 token 'encounter' ∧ ring 尾行 node_type=='遭遇';原「结算行 note」载体不可实现,attack3 R1 定谳)∧ 达标 = `progress_delta > 0` 单判(遭遇奖励 = 伤害进度达标制非清场制,机制依据 = [../../../../game/currency_war/research/combat.md](../../../../../game/currency_war/research/combat.md) §3);兑现即清 `chosen_encounter`(单次消费:镜像残留/驻留重入/结算覆盖陈旧三面收口,天然幂等)。**数值不直写防双源**:金币真值 = `settle_truth` 结算读数、随机4费 = bench 观察(观察赢);兑现记录 = 语义账面(现役消费面 = 审计投影唯一,策略器收益对账读端挂账)。假阴性申报:双证存在同源面,镜像缺失遭遇局 fail-closed 漏兑现(方向安全)。
- 刷新计数:`encounter_refresh_used` 已用计数与 `encounter_refreshed_in_visit` per-visit 位已退役(剩余语义化,迭代 2026-09-21-event-refresh-unify-supply-pick),闸 = `encounter_refresh_left` 剩余语义观察真值(kernel 闸与画面对照闸同读该字段)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.1 / §4「事件选择」;选择落地语义 = fields.md §4。

## 7. 子态与 overlay

- 暗色锁定子态(遭遇锁定):`operations/cw_screen/cw_screen_prep_locked_return.py::CwScreenPrepLockedReturn` 点右上返回按钮(此态下遭遇锚仍可透出命中,先分流防误派)。
- 「属性详情」面板误触发未建模独立处理:残留归下一帧重入自愈(族注 = [README.md](README.md) §5.5)。
- 「敌方信息」浮层(查看详情):已建档「货币战争-敌人信息浮层」,阶段一身份分发独立处理。

## 8. 守卫与防线

- 空候选防线:候选读缺 = 零点击终结交回重读,禁盲选派发(选卡确认不可逆消耗本节点)。
- 刷新单次:闸 = `encounter_refresh_left` 剩余语义观察真值(≤0 或 None = 拒绝);拒绝 → 重调一次决策按原评分选(单轮内有界);重调仍建议刷新(闸数据不一致)→ 零点击终结交回。点偏/无布局时交回后重进重读,失败安全。
- 兑现回调防误兑现:双证判遭遇 + 达标单判 + 兑现后清 chosen(单次消费);局外/session 缺 = 跳过;异常不阻塞结算(best-effort)。
- 读缺失败安全:refresh_left 读缺 = None = 闸拒绝;候选读缺 = 零点击交回。
- 验效废除:确认后零判效;刷新「刷没刷成」不判(点偏 = 重进重读);落地判定归观察侧。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「遭遇节点」;op 内日志 tag = `[cw-encounter]`(options/pick/refresh、刷新圆钮坐标、零点击终结归因)。
- 兑现回调归因串可见化:`[cw-settle-confirm]` 行(claimed/未触发归因)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_event_screens.py`(门/观察接线+left 摄入/派发即终结/空候选零点击/刷新终结恰一次/闸拒绝/闸不一致零点击/兑现回调七臂)+ `test_cw_screen_report_ports.py`(摄入序:空候选整函数早退含 left)+ `test_cw_game_state_consume.py`(chosen 记录面:report 直调真选/离屏/越界)。
- game 侧知识:画面与交互模型 = [../../../../game/screens/currency_war_encounter.md](../../../../../game/screens/currency_war_encounter.md);分支刷新机制(优势布局授予,每局 1 次)= [../../../../game/currency_war/data/advantage_layouts.md](../../../../../game/currency_war/data/advantage_layouts.md);难度/节点表 = [../../../../game/currency_war/data/competitors.md](../../../../../game/currency_war/data/competitors.md);遭遇奖励达标制 = [../../../../game/currency_war/research/combat.md](../../../../../game/currency_war/research/combat.md) §3;时序口径(含 #23 supersession)= [../../../../game/currency_war/research/screen_flow_timing.md](../../../../../game/currency_war/research/screen_flow_timing.md)。
