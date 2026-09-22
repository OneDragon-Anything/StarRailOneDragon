# 投资策略三选一(invest_strategy · 货币战争-投资策略)

> 代码 = `operations/cw_screen/cw_screen_invest_strategy.py::CwScreenInvestStrategy`(两 node 直继承 `SrOperation`)。职责:投资策略 overlay 一次访问——入口稳定帧观察 → `decide_invest` 决策 →(按需)逐卡刷新终结动作 → 选卡确认链经 `CwActionPickInvestOp` 派发。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_invest_strategy.yml`。

## 1. 分发判定

- 外循环分发(阶段一身份行):id_mark 锚「货币战争-投资策略.标识-请选择投资策略」命中即派发。历史双信号+复探(N5)与 OCR 全短语腿已退役(screen_flow_timing #30 裁定:横幅中间态不处理,帧落阶段二守卫等待)。
- 分发 = 阶段一身份行(标题锚);判定不复制分发表,单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。

## 2. 画面形态声明

**横幅中间态**(2026-09-15 决策帧实证 + 用户裁定,过渡记录 = [../../../../game/currency_war/research/screen_flow_timing.md](../../../../../game/currency_war/research/screen_flow_timing.md) #30):入口展开为两段——备战画面先完整可见,选卡页展开过程中存在「备战完整可见 + 中部横幅『请选择投资策略』(y≈510,选卡未渲染)」的中间态。横幅态**零可交互元素,裁定不派发不处理**(等展开完成;横幅态标题不在 id_mark 位 [855,78,1065,118],锚判定天然 miss,现行分发判据与该裁定一致)。

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3;不入决策规范,op 形态照常)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口锚复探窗(有界自愈)→ **一次读全**(候选 + 逐卡刷新剩余,零稳定帧等待——用户裁定 2026-09-21)→ `report_screen_invest_strategy_obs` 落容器 `invest_strategy_opts` + `strategy_refresh_left` 槽 → obs 挂实例属性。决策动作 node = 零参决策 `strategies/impl/cw_strategy.py::CwStrategy.decide_invest_strategy`(候选自容器槽;**空候选/无有效输出 = round_fail 显式失败,零盲发**;判据本体 = `kernel/cw_events.py::decide_event`,规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1)→ 逐卡刷新终结交回 ∨ 选卡确认链经 `CwActionPickInvestOp` 派发(词表 = `CwActionPickInvestStrategyParam`;**动作 op 点完确认立即上报完整结果**——选择事实经获得链 `gain_invest_strategy` 记:无效载荷拒绝/active_strategies 按名字去重追加/效果账本登记腿/`on_strategy_gained` 效果分派,正本 = [../game_state/gain-chain.md](../game_state/gain-chain.md))→ **round_success 终结交回外循环**(选完即交回,用户裁定 2026-09-21;确认未生效 = 代码 bug,overlay 残留由外循环重识别重派,修法 = 点击链可靠性)。刷新 = 终结动作,无 pending 裁决:点钮后本访问即 round_success 终结交回,外循环重进 = 入口重建重观察重决策。

## 3. 观察面

入口单次观察(观察 node;决策环零识别)——`_observe_frame` 序:

1. 入口锚复探窗(语义):首帧探测「标识-请选择投资策略」,miss → 可中断睡眠 0.8s × 4 次复探;超窗仍 miss = `entry_ok=False` → 观察 node round_retry 有界自愈(观察 node `node_max_retry_times=10` 预算内,不炸 op);
2. **一次读全**(零稳定帧等待,用户裁定 2026-09-21):同一帧读卡名(`_read_options`:全图 OCR,按卡名行 y 带 465-505 + 文本长 2-8 字 + 排除表过滤,按 center-x 左→右排序)+ 逐卡刷新剩余计数(`read_invest_refresh_counts`,x 就近配对到槽,读缺 = None);首帧全图 OCR 存底随 payload。

(旧 1s 稳定帧已删,读缺自愈 = 复探窗 + 外循环重派;空候选 → 决策动作 node round_fail 显式失败,见 §2/§5。)

观察 payload = `CwScreenInvestStrategyObs`(`entry_ok`/`options`/`refresh_slots`/`first_ocr_map`/`screen`,住 `kernel/cw_screen_report/invest_strategy.py`);report = `report_screen_invest_strategy_obs` 候选写容器 `invest_strategy_opts` 槽 + 逐卡剩余合并写 `strategy_refresh_left`(观察写端,键 = 规范卡名,读缺键跳写;names 空 = OCR 未读得不写;match/gs 缺席的局外兜底路径跳过)。决策零参读容器槽,刷新闸直接消费 obs 携带余量。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionPickInvestOp`(`CwActionPickInvestStrategyParam`,投资两屏拆类后两行同指一 op) | 注册表工厂 `action_op_for`(决策半组装 `OverlayPickExecEnv`:定位点/确认钮/裁决词) | **即时上报**(动作 op 内,机械链发出后立即):`report_action_pick_invest_strategy_param` → `gain_invest_strategy` 整链(无效载荷拒绝/持卡面按名字去重追加/登记腿/效果分派;reason=`gain_chain_applied`)——零分步零证据等待 | **是(访问终结)**:派发后 `round_success` 终结交回;确认未生效 = 代码 bug(外循环重识别重派,修法 = 点击链可靠性) |
| 逐卡刷新(无注册表动作 op;`CwActionRefreshInvestCardsParam` 仅策略建议载体) | 画面 op 留守臂(`_decide_and_act` 逐卡刷新终结分支:obs 携带余量闸 + 文本锚定偏移 `safe_click`) | 无自上报(刷新计数 = 剩余语义,写端 = 观察 report 摄入;访问内零比对,刷后不重读) | **是(访问终结)**:点击 + 1.5s 动画窗后 `round_success` 即交回;外循环重进 = 入口重建 |

决策动作 node 单决策体 `_decide_and_act`(零参,输入 = 观察轮 obs 载体):

```
names = opts 卡名;空候选 → round_fail 显式失败(零盲发)
match 判空:无 match 局外 = 零决策零点击 round_success 终结交回
  (遭遇屏同款;生产对局分发恒有 match,该出口仅独立跑可达)
act = match.strategy.decide_invest_strategy()(零参,候选读容器 invest_strategy_opts 槽)
├─ 逐卡刷新 = 终结动作(act.refresh_slots 非空):
│    闸1 obs.refresh_slots 槽余量 >0(权威闸,读缺 = 无授权失败安全);
│    闸2 容器 strategy_refresh_left 剩余口径对照(≤0 = 尽;键缺失由闸1裁决;
│      观察写端每访问覆盖,与闸1同帧同值);
│    闸3 唯一 L1 槽守卫(_guard_classify 现算:恰一个非血∧非禁槽 → 该槽不可刷)
│    三闸全败(建议帧但无槽可执行)→ 同访问重调一次落选卡:
│      策略侧同帧去重(scratch 键 = (kind, 候选元组):建议帧首调发建议、
│      紧随重调落选卡,零选卡漂移;依据 = strategies/impl/flow.py::
│      _decide_invest docstring、strategy-docs/13_pick_family.md §1 invest
│      行「重决策仍经本入口」;重调发生在任何刷新执行之前、零新事实,
│      不触 op-layer.md §1.4「禁重调决策」的刷新链禁令——在册形态非违例)
│        重调返回选卡 → 落「选卡确认链」分支;
│        重调仍返回刷新(策略器未实现去重 = bug 面)→ act=None
│          → 汇入「决策无有效选卡输出」round_fail 显式失败(单次重调,
│            零二次重调零循环,对照 encounter.md §4 同款申报口径)
│    → 点「货币战争-投资策略.区域-刷新次数行」OCR 命中文本中心
│      + 固定偏移 _REFRESH_BTN_DX(-88,safe_click)
│    → 动画窗固定等待 1.5s(机械时序)→ round_success = 本访问终结交回
│      (访问内零比对:刷后不重读不比对不重决策;新事实归重进访问重建)
├─ 决策无有效选卡输出 → round_fail 显式失败(零盲点)
└─ 选卡确认链:派发 CwActionPickInvestOp
     (机械链在动作 op 内,点完确认立即上报完整结果;派发 param 携真实选中
      idx + 归一名,定位点 = 「货币战争-投资策略.区域-卡名行」center
      (缺失兜底常量 CARD_CLICK_Y)+ 该卡 center-x,确认钮 =
      「货币战争-投资策略.按钮-确认」建档查找点击(动作 op 内,全族统一),
      裁决词「投资策略」)
     → round_success = 本访问终结交回外循环
```

交互陷阱:选中点击 = **卡名行**(y≈474);点描述区/卡底不选中(选中失败 → 确认灰置;确认未生效 = 点击链 bug 面修因,不设重试)。选卡+确认链经动作工厂(`CwActionPickInvestOp`)派发,刷新圆钮点击留守画面 op(safe_click);刷新槽位坐标 = 观察段配对产物(slot = 画面槽位下标左→右 0-2,与 `RefreshInvestCards.slots` 同坐标系)。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 逐卡刷新点击(点一槽即交) | **访问终结** | round_success 交回外循环重进 = 入口重建,重进后重观察重决策 |
| 选卡确认链派发 | **访问终结** | round_success 交回外循环重分发(结果已即时上报写入;确认未生效 = 代码 bug,overlay 残留由外循环重识别重派,修法 = 点击链可靠性) |
| 局外无 match(仅独立跑可达) | **访问终结** | round_success 交回(零决策零点击;画面 op 不产决策,flow/README §1 铁律) |
| 三闸全败重调仍返回刷新 | 显式失败 | round_fail(「决策无有效输出」同出口;策略器同帧去重未实现的 bug 面响亮暴露,零二次重调) |
| 空候选/决策无有效输出 | 显式失败 | round_fail 交外循环(零盲发,bug 面响亮暴露) |
| 入口锚复探超窗 | 有界重试 | 观察 node round_retry 消耗其 `node_max_retry_times=10` 预算,超限 op FAIL 交外循环 |

单选族「确认离开 = 画面终结」语义 = [README.md](README.md) §6;本屏刷新同商店刷新的「唯一引入新事实动作」终结原则([op-layer.md](op-layer.md) §1.4),落点 = 重入访问重建观察。

## 6. 状态上报面

- **持卡登记**(获得链 `gain_invest_strategy`,动作 op 即时上报):GameState `active_strategies` 按名字去重追加(裁定:持卡列表恒无重复名)+ 效果账本登记腿 best-effort(`STRATEGY_EFFECTS` 命中 → `effects.register_strategy`(acquired_t = 节点序快照)+ burst 桥 `apply_effect_burst_grant` + 板面重写桥 `apply_board_rewrite`;失败 log + 缺陷留证 `gain_chain_strategy_register_failed`,不阻塞)+ `on_strategy_gained` 效果分派(骇客专家:银狼 = 狼腿经 `gain_character` 入席 + 商店池申报行 + 改件 `gain_equipment` 采样链)。画面 op 零选择写点(三桥已自画面 op 迁链)。
- **刷新剩余次数**:`strategy_refresh_left` 观察写端(观察 report 摄入「刷新次数N」读数,读缺键跳写、已观察键覆盖;值 = 剩余,≤0 = 尽);画面 op 零计数写点,闸 1 = obs 携带余量、闸 2 = 容器对照。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.4 / §4「投资选择」;效果账挂点 = [../game_state/logic-updates/op-effects.md](../game_state/logic-updates/op-effects.md) §8(事件线选择非逻辑态通道)。

## 7. 子态与 overlay

- 本屏无子态;无独立 overlay 覆盖面(浮层自身即分发对象)。
- 点卡身上部误触发的「属性详情」面板未建模独立处理:面板残留归下一帧重入自愈(重分发重走链/详情 overlay 族分支,族注 = [README.md](README.md) §5.5)。

## 8. 守卫与防线

- 入口复探窗(语义):过渡帧单探测误 fail 防线;超窗 round_retry 不炸 op(节点预算兜底)。
- 刷新偏移错(文本锚漂移)→ 刷新未命中:重读 = 原卡名集、重决策结果天然等价(能力退化非事故);obs 余量权威闸防超刷。
- 验效废除:访问内刷后零比对、确认后零判效;确认未生效 = 代码 bug(点击链治理),overlay 残留由外循环重识别重派(数据面零回滚零判重,action_ops.md §1 增补 2)。
- 空候选/决策无有效输出 = round_fail 显式失败(零盲发,fallback 路径已废)。
- 同帧去重契约(三闸全败重调):重调仍返回刷新 = 策略器未实现去重的 bug 面 →「决策无有效选卡输出」round_fail 显式失败;去重单一源 = 策略器(flow.py::_decide_invest scratch 键),画面 op 只重调一次、重调仍刷新即弃,零循环。
- 未注册卡名告警(注册表数据缺口可见化,不阻塞)。
- 守卫总册域(停机钩子/安灯/预算)不设本屏专属防线,细则 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「投资策略」(dispatch 包装统一落 `[cw-op]` 主日志行);op 内日志 tag = `[cw-strat]`(options/chose/reason、槽位刷新终结交回);获得链侧 tag = `[cw-gain]`(效果账本登记/板面重写桥/策略落地分步)。
- 缺陷面:登记腿失败 = `gain_chain_strategy_register_failed`;无效载荷 = `pick_invest_invalid_payload`(零盲发配套)。
- 测试锁:两 node 行为锁 + 写入流对拍 = `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_phase_screens.py`(派发即终结+派发时点写入对拍/空候选零盲发/局外零决策交回/观察复探窗与 report 含 left 摄入/刷新终结交回);即时上报与去重链锁 = `test_cw_yinlang_phase32.py`(即时上报/无效载荷/去重/骇客链);获得链锁 = `test_cw_gain_chain.py`(gain_invest_strategy/gain_invest_env 链腿);动作 op 类型分派 = `test_cw_unified_action_4.py`。
- game 侧知识:画面建档与交互 = [../../../../game/screens/currency_war_invest_strategy.md](../../../../../game/screens/currency_war_invest_strategy.md);刷新判据数学 = [../proofs/p81-invest-refresh-dominance.md](../proofs/p81-invest-refresh-dominance.md);决策规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md)。
