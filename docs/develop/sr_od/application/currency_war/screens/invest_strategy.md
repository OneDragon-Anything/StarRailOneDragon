# 投资策略三选一(invest_strategy · 货币战争-投资策略)

> 代码 = `operations/cw_screen/cw_screen_invest_strategy.py::CwScreenInvestStrategy`(两 node 直继承 `SrOperation`)。职责:投资策略 overlay 一次访问——入口稳定帧观察 → `decide_invest` 决策 →(按需)逐卡刷新终结动作 → 选卡确认链经 `CwActionPickInvestOp` 派发。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_invest_strategy.yml`。

## 1. 分发判定

- 外循环分发(阶段一身份行):id_mark 锚「货币战争-投资策略.标识-请选择投资策略」命中即派发。历史双信号+复探(N5)与 OCR 全短语腿已退役(screen_flow_timing #30 裁定:横幅中间态不处理,帧落阶段二守卫等待)。
- 分发 = 阶段一身份行(标题锚);判定不复制分发表,单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。

## 2. 画面形态声明

**横幅中间态**(2026-09-15 决策帧实证 + 用户裁定,过渡记录 = [../../../../game/currency_war/research/screen_flow_timing.md](../../../../../game/currency_war/research/screen_flow_timing.md) #30):入口展开为两段——备战画面先完整可见,选卡页展开过程中存在「备战完整可见 + 中部横幅『请选择投资策略』(y≈510,选卡未渲染)」的中间态。横幅态**零可交互元素,裁定不派发不处理**(等展开完成;横幅态标题不在 id_mark 位 [855,78,1065,118],锚判定天然 miss,现行分发判据与该裁定一致)。

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3;不入决策规范,op 形态照常)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口锚复探窗(ADR-0529 有界自愈)→ 1s 稳定帧 → 候选一次读 → `report_screen_invest_strategy_obs` 落容器 `invest_strategy_opts` 槽 → obs 挂实例属性。决策动作 node = 顶部重入裁决两件 → 零参决策 `strategies/impl/cw_strategy.py::CwStrategy.decide_invest_strategy()`(候选自容器槽;判据本体 = `kernel/cw_events.py::decide_event`,规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1)→ 逐卡刷新终结交回 ∨ 选卡确认链经 `CwActionPickInvestOp` 派发(投资两屏共用 op,机械链+自上报在动作 op 内,pick-op-unify 批)→ `round_wait` 循环推进(无防御上限;`node_max_retry_times=10` 现役值仅框架异常路径消费)。重入裁决两件(决策动作 node 顶部):
- 确认裁决:上轮已发确认 → 本轮入口锚不在 = overlay 已关(选卡落地)→ 补 append 持卡 + success 交回;锚仍在 = 确认未落地 → 清标志重走。
- 刷新 = 终结动作,无 pending 裁决:点钮后本访问即 round_success 终结交回,外循环重进 = 入口重建重观察重决策。

## 3. 观察面

入口单次观察(观察 node;决策循环用 node runner 新帧)——`_observe_frame` 序:

1. 入口锚复探窗(ADR-0529 语义):首帧探测「标识-请选择投资策略」,miss → 可中断睡眠 0.8s × 4 次复探;超窗仍 miss = `entry_ok=False` → 观察 node round_retry 有界自愈(观察 node `node_max_retry_times=10` 预算内,不炸 op);
2. 1s 稳定等待后重截(标题出现后三卡才渲染稳定,时序口径 = [../../../../game/currency_war/research/screen_flow_timing.md](../../../../../game/currency_war/research/screen_flow_timing.md) #11);
3. 候选读取 `_read_options`:全图 OCR,按卡名行 y 带(465-505)+ 文本长 2-8 字 + 排除表过滤出 3 张卡名,按 center-x 左→右排序;首帧全图 OCR 存底随 payload。

(旧 visit 起点槽位集复位步已随防重入宿主退役删除——容器逐卡计数局内累计无 visit 级复位,闸 2 改容器计数对照,见 §4。)

观察 payload = `CwScreenInvestStrategyObs`(`entry_ok`/`options`/`first_ocr_map`/`screen`,住 `kernel/cw_screen_report/invest_strategy.py`);report = `report_screen_invest_strategy_obs` 候选写容器 `invest_strategy_opts` 槽(names 空 = OCR 未读得不写,闸在 report 内;match/gs 缺席的局外兜底路径跳过)。决策零参读容器槽。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionPickInvestOp`(`CwActionPickInvestParam`,投资两屏共用注册行) | 注册表工厂 `action_op_for`(决策半组装 `OverlayPickExecEnv`:定位点/确认钮/裁决词) | 自上报 `report_action_pick_invest_param` 发射相(意图遥测,容器零写);落地相由本 op 重入裁决出口(`_append_confirmed_strategy`)持 `EVIDENCE_OVERLAY_CLOSED` 调用 | 否(非终结):发出后 `round_wait` 循环推进;落地由重入裁决判——锚不在 = append 持卡 + success 交回外循环(见 §5) |
| 逐卡刷新(无注册表动作 op;`CwActionRefreshInvestCardsParam` 仅策略建议载体) | 画面 op 留守臂(`_decide_and_act` 逐卡刷新终结分支:槽位「刷新次数N」文本锚定偏移 `safe_click`) | 无自上报(刷新计数写端出辖动作侧,画面 op 零记账;访问内零比对,刷后不重读) | **是(访问终结)**:点击 + 1.5s 动画窗后 `round_success` 即交回;外循环重进 = 入口重建 |

决策动作 node 单决策体 `_decide_and_act`(零参:候选/帧/首帧 OCR 存底自观察轮 obs 载体):

```
names = opts 卡名;act = match.strategy.decide_invest_strategy()
  (零参,候选读容器 invest_strategy_opts 槽;
   无 match 局外防御 = 裸空容器 decide_event,且显式跳过刷新链)
├─ 逐卡刷新 = 终结动作(act.refresh_slots 非空 ∧ opts 非空):
│    逐槽计数现读 read_invest_refresh_counts(ctx, screen, 'strategy')
│    + pair_refresh_counts_to_slots(x 就近配对到槽,超半槽距 = 读缺)
│    → 三闸逐步守卫:闸1 计数现读 >0(权威闸,读缺 = 无授权失败安全);
│      闸2 容器逐卡计数未用过(strategy_refresh_used 对照,>0 = 已用;
│        局内累计,无 visit 级复位——闸1 现读 + 计数双闸,每访问恰一次决策);
│      闸3 唯一 L1 槽守卫(_guard_classify 现算:恰一个非血∧非禁槽 → 该槽不可刷)
│    → 点「刷新次数N」文本锚 + 固定偏移 _REFRESH_BTN_DX(-88,safe_click)
│    → 动画窗固定等待 1.5s(机械时序)→ round_success = 本访问终结交回
│      (访问内零比对:刷后不重读不比对不重决策;新事实归重进访问重建)
├─ 选卡确认链:置确认 pending(待裁决选卡名)→ 派发 CwActionPickInvestOp
│    (投资两屏共用;机械链在动作 op 内,op 内自上报
│     report_action_pick_invest_param 零写;派发 param 携真实选中 idx,
│     定位点 = 「区域-卡名行」center[兜底常量] + 该卡 center-x,
│     确认钮 = 「按钮-确认」center[兜底常量],裁决词「投资策略」)
│    (机械交回,验效废除 = [op-layer.md](op-layer.md) §1.2;
│     落地判定归 §2 确认裁决)
```

交互陷阱:选中点击 = **卡名行**(y≈474);点描述区/卡底不选中(选中失败 → 确认灰置,重入裁决兜底)。选卡+确认链经动作工厂(`CwActionPickInvestOp`)派发,刷新圆钮点击留守画面 op(safe_click);刷新槽位坐标 = `pair_refresh_counts_to_slots` 现读配对(slot = 画面槽位下标左→右 0-2,与 `RefreshInvestCards.slots` 同坐标系)。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 逐卡刷新点击(点一槽即交) | **访问终结** | round_success 交回外循环重进 = 入口重建,重进后重观察重决策 |
| 确认点击 | 机械交回 | 重入确认裁决:锚不在 = append 持卡 + success 交回外循环重分发;锚在 = 重走(`round_wait` 循环推进,无防御上限) |
| 入口锚复探超窗 | 有界重试 | 观察 node round_retry 消耗其 `node_max_retry_times=10` 预算,超限 op FAIL 交外循环 |

单选族「确认离开 = 画面终结」语义 = [README.md](README.md) §6;本屏刷新同商店刷新的「唯一引入新事实动作」终结原则([op-layer.md](op-layer.md) §1.4),落点 = 重入访问重建观察。

## 6. 状态上报面

- **持卡登记**(`_append_confirmed_strategy`,确认裁决出口):`session.active_strategies` 去重追加 + GameState `active_strategies` write_logic(局级累计);效果账本挂点 best-effort:`STRATEGY_EFFECTS` 命中 → `effects.register_strategy`(acquired_t = 节点序快照)+ burst 桥 `apply_effect_burst_grant` + 板面重写桥 `apply_board_rewrite`(出售面逻辑写/替换面零写留证)。
- **刷新计数读端闸**:`strategy_refresh_used` 计数写端随画面 op 基类退役([op-layer.md](op-layer.md) §4 刷新计数出辖),刷新发射零自上报(零写族 `report_action_refresh_invest_cards_param` 现无调用方);闸 2 保留容器逐卡计数读端(键 = `kernel/cw_investments.py::normalize_invest_name` 归一,>0 = 已用),防重入主承重 = 闸 1 屏上余量现读(读缺 = 无授权失败安全)。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.4 / §4「投资选择」;效果账挂点 = [../game_state/logic-updates/op-effects.md](../game_state/logic-updates/op-effects.md) §8(事件线选择非逻辑态通道)。

## 7. 子态与 overlay

- 本屏无子态;无独立 overlay 覆盖面(浮层自身即分发对象)。
- 点卡身上部误触发的「属性详情」面板未建模独立处理:面板残留归下一帧重入自愈(重分发重走链/详情 overlay 族分支,族注 = [README.md](README.md) §5.5)。

## 8. 守卫与防线

- 入口复探窗(ADR-0529 语义):过渡帧单探测误 fail 防线;超窗 round_retry 不炸 op(节点预算兜底)。
- 刷新偏移错(文本锚漂移)→ 刷新未命中:重读 = 原卡名集、重决策结果天然等价(能力退化非事故);计数现读权威闸防超刷。
- 验效废除:访问内刷后零比对、确认后零判效;未落地治理 = 重入裁决(`round_wait` 循环推进,无防御上限)。
- 未注册卡名告警(注册表数据缺口可见化,不阻塞)。
- 守卫总册域(停机钩子/安灯/预算)不设本屏专属防线,细则 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「投资策略」(dispatch 包装统一落 `[cw-op]` 主日志行);op 内日志 tag = `[cw-strat]`(options/chose/reason、槽位刷新终结交回)。
- 缺陷面 = 无(零效果留证通道仅投资环境屏)。
- 测试锁:两 node 行为锁 + 写入流对拍 = `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_phase_screens.py`(重入裁决×门组合/刷新终结交回/闸 2 容器计数读源/观察复探窗与 report)。
- game 侧知识:画面建档与交互 = [../../../../game/screens/currency_war_invest_strategy.md](../../../../../game/screens/currency_war_invest_strategy.md);刷新判据数学 = [../proofs/p81-invest-refresh-dominance.md](../proofs/p81-invest-refresh-dominance.md);决策规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md)。
