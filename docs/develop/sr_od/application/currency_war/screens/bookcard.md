# 星徽秘典四选一(bookcard · 货币战争-星徽秘典弹窗)

> 代码 = `operations/cw_screen/cw_screen_bookcard.py::CwScreenBookcard`(两 node 直继承 `SrOperation`)。职责:星徽秘典四选一弹窗一次访问——OCR「XX星徽」卡名 → `decide_star_tome` 选卡 → 点卡即选(弹窗自关,无确认钮);选卡落地由重入裁决承载并补写 chosen_tome + 到账登记。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_star_tome_popup.yml`。

## 1. 分发判定

- 阶段一身份分发(号制已退役):id_mark 锚「货币战争-星徽秘典弹窗.标识-星徽秘典」(lcs 0.9);命中即接管,不放行备战分支。单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口门(「标识-星徽秘典」,miss = round_fail 交回外循环重判)→ 卡阵营名一次读(经 FACTIONS 注册表两段转换标准化门)→ `report_screen_bookcard_obs` 落容器 `star_tome_opts` / `star_tome_opts_xy`(同门双写)→ obs 挂实例属性。决策动作 node = 顶部重入裁决(选卡 pending = 上轮已发选卡的星徽名;弹窗不在 = 选卡落地 → 此刻才写 chosen_tome + 到账登记 + success;弹窗在 = 点击未落地 → 重走重选,不留幻影登记)→ 零参决策 `match.strategy.decide_star_tome()`(候选自容器槽;打分:target 阵营命中 / board 已有阵营 / 配方框架阵营命中,权重 = `strategies/impl/pick_bias.py::PICK_BIAS` tome_* 常量,规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1 E17)。决策出口守卫:决策无有效输出(候选空/返回 None/词表外)= 具名 round_fail 零盲发(op-layer §1.1 出口③,消息含原值);无 match 局外不设早退支(用户裁决 2026-09-22 全族删门);pick idx 越界 = 守卫断言 AssertionError(op-layer §1.3,禁钳位);各臂与守卫均在派发前、零点击;选卡派发 = 策略产实例直发(无重建无钳位,流程侧零值域改写)。选卡链经 `CwActionPickStarTomeOp` 派发(点卡即选机械链+自上报在动作 op 内;选卡坐标 = 动作 op 自容器 `star_tome_opts_xy` 按 idx 取)→ `round_wait` 循环推进(无防御上限;`node_max_retry_times=5` 现役值仅框架异常路径消费)。

## 3. 观察面

观察 node = 入口门(「标识-星徽秘典」)+ 卡阵营名一次读(每访问恰一次,决策轮复用实例载体);卡名读取 `_read_card_factions`:全屏 OCR,取「XX星徽」后缀文本(长度 > 2)→ [(阵营名, x 中心)] 左→右排序。**观察标准化门**(op-layer.md §1.1 观察标准化门;转换成功性边界登记):候选名经 FACTIONS 注册表两段转换——①形变归一(去「星徽」后缀 + 空白剥离,读链既有)后精确命中 `data/cw_factions.py::FACTIONS`;②不中再 LCS 相似(`one_dragon.utils.str_utils::find_best_match_by_lcs`,阈值常量住代码);任一候选两段皆不中 = 观察失败 round_fail 早退、`star_tome_opts` / `star_tome_opts_xy` 双域零写零上报交回外循环重读(禁带病上报);星徽四选一为选项互斥屏,多候选命中同一注册名 = 同判转换失败;容器值域自此 = FACTIONS 标准注册名(标准化后决策消费标准名,动作上报只携 idx)。坐标解点:候选点 = (OCR x 中心,x 近邻「星徽卡-N」建档中心 y;x 近邻锚自决策半迁观察侧,防 area 序与画面序错位),观察期一次解出;任一「星徽卡-N」area 缺失 = 观察失败 round_fail 早退、双域零写(op-layer.md §1.1 :35,坐标单一真相源 = 观察上报)。观察 payload = `CwScreenBookcardObs`(`on_screen`/`options`/`option_points`/`screen`,住 `kernel/cw_screen_report/bookcard.py`);report = `report_screen_bookcard_obs` 候选与候选点一并写 `star_tome_opts` / `star_tome_opts_xy`(同门同写,op-layer.md §1.1 :35;空候选不写,闸在 report 内,双域一体;match/gs 缺席的局外兜底路径跳过)。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionPickStarTomeOp`(`CwActionPickStarTomeParam`) | 注册表工厂 `action_op_for` 直发策略产 `CwActionPickStarTomeParam` 实例(`OverlayPickExecEnv`:策略产值 idx;坐标由动作 op 自容器取[op-layer §1.1 :35];三守卫派发前置) | 自上报 `report_action_pick_star_tome_param`(零写族,容器零写) | 否(非终结):发出后 `round_wait` 循环推进;落地由重入裁决判——「货币战争-星徽秘典弹窗.标识-星徽秘典」不在 = `_settle_picked_tome`(ConfirmTome 到账登记 + `chosen_tome` 写)+ success 交回外循环(见 §5) |

决策动作 node 决策+机械交回链(整体经动作工厂 `cw_pick_star_tome_action.py::CwActionPickStarTomeOp` 派发;机械链+自上报零写在动作 op 内,派发 param = 策略产实例直发):

```
cards = 观察轮实例载体(标准化注册名)→ 零参决策 decide_star_tome()(候选读容器 star_tome_opts 槽)
  (无 match 局外不设早退支——单跑缺上下文沿正常链路失败即预期,
   用户裁决 2026-09-22 全族删门;cards 空 / 返回词表外 = 守卫 fail
   零盲发;idx 越界 = 守卫断言)
坐标 = 容器 star_tome_opts_xy[pick.idx](动作 op 内取;缺席 = 守卫断言,op-layer §1.1 :35)
  → 置选卡 pending → 派发
  (动作 op 内:自容器取点 safe_click(防吞点击)→ 1.0s
   → 自上报 report_action_pick_star_tome_param)
  (机械交回零判效;弹窗关没关由下一轮重入裁决)
```

交互陷阱:点卡即选、弹窗自关(无确认步骤);决策无有效输出 = 守卫 fail 交回外循环重访问重读,无 fallback 轮(哨兵通道已退役);选卡名恒 = 策略产值候选名;选卡坐标 = 动作 op 自容器 `star_tome_opts_xy` 按 idx 取(op-layer.md §1.1 :35)。与备战词表 `OpenTome`(开秘密典籍道具)分属两域——本屏是弹窗选卡画面,OpenTome 是备战开道具动作。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 重入裁决弹窗不在(选卡落地) | **画面终结** | `_settle_picked_tome`(到账登记 + chosen_tome 写)→ round_success(wait = `CW_OVERLAY_SETTLE_S`)交回外循环重分发 |
| 重入裁决弹窗在(点击未落地) | 节点循环重入 | 重走重选(`round_wait` 循环推进,不烧节点重试预算,无防御上限) |
| 无 match(局外) | 不设早退支(op-layer §1.1;用户裁决 2026-09-22 全族删门) | 未支持用法:单跑缺上下文沿正常链路自然失败,局内不达此态 |
| 决策无有效输出(候选空/返回词表外)/ pick idx 越界 | 守卫 fail(op FAIL) | round_fail(含原值)交回外循环 / 框架异常路径(round_retry + 留证截图,计 node_max_retry_times=5 预算)耗尽 fail;连续 fail 由外环重派网兜底(flow/README §4) |
| 入口锚 miss | op FAIL | 交回外循环重分发 |
| 星徽卡-N 建档缺失(观察侧解点) | 观察失败(op FAIL) | 观察失败 round_fail 早退、`star_tome_opts` / `star_tome_opts_xy` 双域零写,交回外循环重分发;act 段零几何,无决策半建档出口 |

「确认离开 = 画面终结」= [README.md](README.md) §6(本屏确认 = 点卡本身)。

## 6. 状态上报面

- 候选观察:`report_screen_bookcard_obs` 候选与候选点一并写 `star_tome_opts` / `star_tome_opts_xy`(同门同写,op-layer.md §1.1 :35;空候选不写,双域一体)。
- `chosen_tome` write_logic(重入裁决点写;值 = 选中卡阵营名,标准化注册名)。
- 到账登记 `ConfirmTome`(`kernel/cw_exec_state.py::apply_confirm_effect` dict 分支,owned += 「X星徽」;OCR 卡名已去后缀作阵营名,登记时回拼全名,已是全名则原样)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.5 / §4「事件选择」;到账登记 = [../game_state/logic-updates/op-effects.md](../game_state/logic-updates/op-effects.md) §2(ConfirmTome 行)。

## 7. 子态与 overlay

本屏无子态。建档在册「按钮-关闭」(×)area 为画面元素档,本 op 不消费(选卡即关,无独立关闭路径)。

## 8. 守卫与防线

- ①决策输入守卫:无 match 局外不设早退支(op-layer.md §1.1;用户裁决 2026-09-22 全族删门)——原「cards 空 / 无 match = idx 0 fallback」的无 match 半边退役申报;候选空 = 具名 round_fail 零盲发(op-layer §1.1 出口③)——原句候选空半边退役申报。
- ②返回契约与值域守卫:None/词表外 = 具名 round_fail(消息含原值)、idx 越界 = 守卫断言 AssertionError(op-layer.md §1.3,禁钳位)——原「静默钳 0」退役申报。
- ③坐标域:选卡坐标 = 容器 `star_tome_opts_xy`(与候选名域 `star_tome_opts` 同序等长)——观察上报与名字域同门一并入容器(op-layer.md §1.1 :35,坐标单一真相源 = 观察上报),动作 op 按 idx 自容器取点,缺席/越界 = 守卫断言零点击,禁回退 `env.target`/screen_info 现取(禁第二坐标源);坐标失读语义与名字域同格(已有正式值失读 = carried,从未读过 = None);确认钮等静态控件锚 = screen_info area 现取,不入坐标域。
- ④观察标准化门:阵营名经 FACTIONS 注册表两段转换,任一候选转换失败/多候选命中同一注册名 = 观察失败 round_fail 早退、双域零写(转换成功性边界登记见 §3)。
- 「星徽卡-N」area 缺失 = 观察失败:解点随观察上报迁移,观察侧 `area_center` 返 None = 观察失败 round_fail 早退、双域零写交回外循环(与转换失败同格,同门同进退);「禁裸坐标兜底」语义随出口迁观察侧不变。
- x 近邻锚(观察侧解点)= 候选 OCR x 选 x 近邻「星徽卡-N」area 取 y(防 area 序与画面序错位;近邻锚半自决策半迁观察侧)。
- 落地裁决点写(防未落地轮留幻影登记);选卡名恒 = 策略产值候选名(哨兵通道退役),`_settle_picked_tome` 保留空名守卫防幻影登记。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「星徽秘典」;op 内日志 tag = `[cw-flow-bookcard]`(候选/选中/idx)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(bookcard 臂:观察双域上报锁/观察失败三态零写锁[标准化失败·同名同判·建档缺失]/守卫四锁——①a 无 match 局外不设早退支(自然失败)、①b 候选空 fail、②返回契约 fail、③越界断言)、test_cw_unified_action_4.py(StarTome 容器取点锁:容器值点击/缺席·越界断言零点击)、test_cw_screen_report_ports.py(report 同门双写/等长守卫/空桩双域门)、test_cw_game_state_consume.py(chosen_tome 接线锁)。代码注引的典籍通道锁(test_cw_fake_channels_outerloop)已不在册(开放设计注)。
- game 侧知识:画面与机制(星徽 = 阵营徽记装备) = [../../../../game/screens/currency_war_star_tome_popup.md](../../../../../game/screens/currency_war_star_tome_popup.md)。
