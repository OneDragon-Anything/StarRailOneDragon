# 投资策略三选一(invest_strategy · 货币战争-投资策略)

> 代码 = `operations/cw_screen/cw_screen_invest_strategy.py::CwScreenInvestStrategy`(CwScreenOpBase 子类)。职责:投资策略 overlay 一次访问——入口稳定帧观察 → `decide_invest` 决策 →(按需)逐卡刷新终结动作 → 点最优卡 + 确认机械交回。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/currency_war_invest_strategy.yml`。

## 1. 分发判定

- 外循环分支 0e:**双信号 + 复探**(判据单一源 = `cw_loop.py::_invest_overlay_dispatch`)——首探 = id_mark 锚「货币战争-投资策略.标识-请选择投资策略」∨ OCR 全短语「请选择投资策略」(lcs 0.8);首探 miss 且备战双锚命中(浮层穿透形态)→ 短窗后新截图复探一次,命中即派发。复探产出的新截图回写分发帧(未命中时后续分支吃更新帧)。OCR 腿为 outer_loop §2.1「优先 area 化」的显式豁免(浮层淡入期 id_mark 单探测不稳定,`outer_loop.md` §2.2 0e 行)。
- 序位:先于备战双锚(overlay 叠备战时「购买经验」透出命中);判定不复制序位表,单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3;不入决策规范,op 形态照常)。本屏为统一观察架构五相位屏:`CwScreenOpBase` 子类,handle 顶部**重入裁决先于装配点分流**(确认/刷新两 pending 裁决两路径共用),两端口完整在场走五段生命周期、缺省走旧路径(并存纪律 = [../flow/统一观察架构-画面op基类设计.md](../flow/统一观察架构-画面op基类设计.md))。决策入口 = 契约 `strategies/impl/cw_strategy.py::CwStrategy.decide_invest('strategy', ...)`(规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) §1;判据本体 = `kernel/cw_events.py::decide_event`)。重入裁决两件(handle 顶部):
- 确认裁决:上轮已发确认 → 本轮入口锚不在 = overlay 已关(选卡落地)→ 补 append 持卡 + success 交回;锚仍在 = 确认未落地 → 清标志重走(计节点预算)。
- 刷新裁决:上轮已发刷新 → 锚在 = 预期(逐卡重掷后 overlay 仍在)→ 穿透正常观察链重分类重决策;锚不在 = overlay 意外离开(刷新从不关 overlay)→ success 交回外循环重分派。

## 3. 观察面

入口单次观察(observe 段;决策循环内零读屏)——`_observe_frame` 序:

1. 入口锚复探窗(ADR-0529 语义):首帧探测「标识-请选择投资策略」,miss → 可中断睡眠 0.8s × 4 次复探;超窗仍 miss = `entry_ok=False` → observe 段 round_retry 有界自愈(节点预算内,不炸 op);
2. visit 起点单点复位:实例首帧(锚验通过后)清 `exec_state_of(session)._invest_refresh_used_slots`(同 visit 重入不清,跨 visit 新实例必清;防重入与计数现读双保险不同源);
3. 1s 稳定等待后重截(标题出现后三卡才渲染稳定,时序口径 = [../../../../game/currency_war/research/screen_flow_timing.md](../../../../game/currency_war/research/screen_flow_timing.md) #11);
4. 候选读取 `_read_options`:全图 OCR,按卡名行 y 带(465-505)+ 文本长 2-8 字 + 排除表过滤出 3 张卡名,按 center-x 左→右排序;首帧全图 OCR 存底随 payload。

观察 payload = `InvestStrategyObservation`(`entry_ok`/`options`/`first_ocr_map`/`screen`)。**本屏不上报 GameState 容器观察**(无 `read_game_state` 消费;决策输入 = 容器视图 `board_state_of(session)`,overlay 下 board 不可读由视图侧承载)。

## 4. 动作面

decide+act 内聚 `_decide_and_act`(两路径共享):

```
names = opts 卡名;pick = decide_invest('strategy', names, board_state_of(session), ...)
  (无 match 局外防御 = 裸空容器 decide_event,且显式跳过刷新链)
├─ 逐卡刷新 = 终结动作(pick.refresh_slots 非空 ∧ opts 非空):
│    逐槽计数现读 read_invest_refresh_counts(ctx, screen, 'strategy')
│    + pair_refresh_counts_to_slots(x 就近配对到槽,超半槽距 = 读缺)
│    → 三闸逐步守卫:闸1 计数现读 >0(权威闸,读缺 = 无授权失败安全);
│      闸2 槽未发射过(_invest_refresh_used_slots 防重入);
│      闸3 唯一 L1 槽守卫(_guard_classify 现算:恰一个非血∧非禁槽 → 该槽不可刷)
│    → 点「刷新次数N」文本锚 + 固定偏移 _REFRESH_BTN_DX(-88,safe_click)
│    → _emit_refresh_click(发射即置位 + on_outcome 注册表登记件,见 §6)
│    → 动画窗固定等待 1.5s(机械时序)→ 刷新 pending + round_retry = 本访问终结交回
│      (访问内零比对:刷后不重读不比对不重决策;新事实归重入访问)
├─ 点卡:卡名行 Y(「区域-卡名行」center,兜底常量)+ 该卡 center-x → safe_click → 0.7s
└─ 确认:「按钮-确认」center(兜底常量)→ 置确认 pending → emit_overlay_confirm
     (机械交回,验效废除 = [../flow/screen_op.md](../flow/screen_op.md) §2;
      落地判定归 §2 确认裁决)
```

交互陷阱:选中点击 = **卡名行**(y≈474);点描述区/卡底不选中(选中失败 → 确认灰置,重入裁决 + 节点预算兜底)。动作词表:本屏为画面 op 直驱(不经动作 op 注册表,无 `CW_ACTION_TYPES` 成员);刷新发射载荷 = `StrategyRefreshClick`(slot = 画面槽位下标左→右 0-2,与 `PickEvent.refresh_slots` 同坐标系)。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 逐卡刷新点击(点一槽即交) | 访问终结 | round_retry → 节点重跑 → 刷新裁决(锚在 = 穿透重观察重决策) |
| 确认点击 | 机械交回 | 重入确认裁决:锚不在 = append 持卡 + success 交回外循环重分发;锚在 = 重走(计预算) |
| 入口锚复探超窗 | 有界重试 | round_retry 消耗 `node_max_retry_times=10` 预算,超限 op FAIL 交外循环 |

单选族「确认离开 = 画面终结」语义 = [README.md](README.md) §6;本屏刷新同商店刷新的「唯一引入新事实动作」终结原则([../flow/screen_op.md](../flow/screen_op.md) §4),落点 = 重入访问重建观察。

## 6. 状态上报面

- **持卡登记**(`_append_confirmed_strategy`,确认裁决出口):`session.active_strategies` 去重追加 + GameState `active_strategies` write_logic(局级累计);效果账本挂点 best-effort:`STRATEGY_EFFECTS` 命中 → `effects.register_strategy`(acquired_t = 节点序快照)+ burst 桥 `apply_effect_burst_grant` + 板面重写桥 `apply_board_rewrite`(出售面逻辑写/替换面零写留证)。
- **刷新计数登记件**:on_outcome 注册表发射型 `strategy_refresh_used`(`EMIT_TRIGGERED_DECLARED` 在册,`cw_screen_op_base.py`),触发点 = `_emit_refresh_click` 共用分派面;写端 = `board_state_of(session).write_logic(strategy_refresh_used, ...)` 逐卡 dict,键 = `kernel/cw_investments.py::normalize_invest_name` 归一,随点击置位不等验效。
- 字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.4 / §4「投资选择」;效果账挂点 = [../game_state/logic-updates/op-effects.md](../game_state/logic-updates/op-effects.md) §8(事件线选择非逻辑态通道)。

## 7. 子态与 overlay

- 本屏无子态;无独立 overlay 覆盖面(浮层自身即分发对象)。
- 点卡身上部误触发的「属性详情」面板未建模独立处理:面板残留归下一帧重入自愈(重分发重走链/详情 overlay 族分支,族注 = [README.md](README.md) §5.5)。

## 8. 守卫与防线

- 入口复探窗(ADR-0529 语义):过渡帧单探测误 fail 防线;超窗 round_retry 不炸 op(节点预算兜底)。
- 刷新偏移错(文本锚漂移)→ 刷新未命中:重读 = 原卡名集、重决策结果天然等价(能力退化非事故);计数现读权威闸防超刷。
- 验效废除:访问内刷后零比对、确认后零判效;未落地治理 = 重入裁决 + 节点预算耗尽 FAIL bail(预算 = `node_max_retry_times=10`)。
- 未注册卡名告警(注册表数据缺口可见化,不阻塞)。
- 守卫总册域(停机钩子/安灯/预算)不设本屏专属防线,细则 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「投资策略」(dispatch 包装统一落 `[cw-op]` 主日志行);op 内日志 tag = `[cw-strat]`(options/chose/reason、槽位刷新终结交回)。
- 登记件证据 = `refresh_click@slot{i}`;缺陷面 = 无(零效果留证通道仅投资环境屏)。
- 测试锁:实机行为锁 + 写入流对拍 = `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_phase_screens.py`。
- game 侧知识:画面建档与交互 = [../../../../game/screens/currency_war_invest_strategy.md](../../../../game/screens/currency_war_invest_strategy.md);刷新判据数学 = [../proofs/p81-invest-refresh-dominance.md](../proofs/p81-invest-refresh-dominance.md);决策规格 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md)。
