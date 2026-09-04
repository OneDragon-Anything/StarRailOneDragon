# 商店访问（shop_visit）

> 反向规格化来源 = `operations/cw_screen/cw_screen_prep.py:_open_shop_phase`（流程层商店编排）+ `operations/cw_op/cw_op_buy_cards.py:run_buy_waves`（买牌波循环）+ `finalize_buy_phase`（单元收尾）。职责：商店打开态的一次访问编排——波循环驱动 `decide_shop_screen`、执行至首个刷新、离店收尾。路径根 = `src/sr_od/application/currency_war/`。
> **决策判据（买什么/卖什么/刷不刷/升不升）一律不在本篇**——本篇只管"波怎么循环、槽位按什么顺序评估、何时离店"；判据见 `../strategy-docs/11_shop_decisions.md`。

## 1. 入口与形态（`cw_screen_prep.py:1716-1770` `_open_shop_phase`）

OpenShop 动作两形态（`kernel/cw_prep_actions.py:108-117`）：

| 形态 | 编排 |
|---|---|
| `read_only=True`（读数性开店） | CwOpOpenShop（幂等：已开不点）→ heavy 观察（gold 开态真值进 session）→ **不调商店决策**（M-6 门保持：free=0 不进买牌）→ CwOpCloseShop → 节点探针 → 回备战。progressed = 开店成功（r364 进展保证语义） |
| `read_only=False`（显式开店） | 开店前 hp 三件组取**开店前的备战观察**（商店开态 HP 区不可读，读互斥）→ `run_buy_waves`（§2）→ CwOpCloseShop → `finalize_buy_phase`（§4）→ 节点探针 |

购买单元记账：开店前 `_spend_unit_open`（时点+gold 观测+F2 诚实标注），收尾 `_spend_unit_close`（boundary=closed/failed/aborted → spend_ledger.jsonl；`cw_screen_prep.py:1573-1630`）。波循环失败路径不开收（店留着交上层重新识别）。

## 2. 波循环（`cw_op_buy_cards.py:415-1239` `run_buy_waves`）

```
for _ in range(MAX_REFRESH + 1):          # MAX_REFRESH=4 硬墙（cw_op_buy_cards.py:365）
  ├─ 波顶 settle：非连击续刷波 sleep 0.3s（board 面板动画防 OCR 误读）+ park_cursor
  ├─ 读序（槽位评估顺序）：
  │    read_game_state(phase=PHASE_PREP_SHOP_OPEN) 全量现读（gold/hp/lv/plane/round/shop 五槽）
  │    → _apply_hp（shop 关闭帧 hp 三件组值+位同写覆盖）
  │    → 首波 update_target（执行边界压缩：替代原开店后专用读）
  │    → node_type 拷 Director shop 关态真值（shop 开帧节点行被遮恒 None）
  │    → dual_track_phase/committed_from 拷入（R1 唯一读端）
  │    → gold==0 救援（读 0 时重读 4 帧取首个 >0；结果留证 obs_conflict）
  │    → gold_open = 首波快照（对拍基线，任何动作执行前）
  │    → bench 播种：tracked_bench_chars 优先（带 star+merge），空退 tracked_bench（旧路径）
  │    → session.last_state = state；黑板写 session.shop_state_frame（写者白名单 = 本段）
  │    → 期望态覆盖点 shop_wave_top 清账（gold 族可信读清账；tracked 族透传不确认）
  ├─ 决策：actions = strategy.decide_shop_screen(session, config)
  │    异常 → decisions 落 Error 占位行 + 完整栈 log 后上抛（留证后抛，r95）
  ├─ 遥测：state/shop/plan 日志行（带 node/next 节点上下文）+ record_shop_snapshot('offer') + record_decision（session 态快照全量 extra）
  ├─ 执行至首个 RefreshShop（含）：
  │    refresh_idx = 首个刷新下标；prefix = actions[:refresh_idx+1]（无刷新 = 全部）
  │    prefix 后仍有动作 → plan_truncated=True（"计划≠尝试"可见化，ADR-0456）
  │    逐动作（action_exec.md §4）：
  │      BuyCard：x 去重 → 点牌位 → sleep 0.4 → 账（total_buy/spend_executed/tracked/买前裁片
  │              留证）→ 满栏自动多买补差（k 公式单一源 cw_state.merge_buy_k）
  │      LevelUp：点购买经验 → sleep 1.0（动画对齐）→ 账
  │      RefreshShop：total_refresh≥MAX_REFRESH → 跳过+refresh_skipped='max_cap'（硬墙）
  │              刷前期望构建（仅刷新波复用波顶现读；其余波点击前 pre-shot 现读金+牌名集——
  │              state.shop 是 plan 期读数，波内买卡不摘已买牌，不可作刷前读）
  │              → 点刷新 → 牌行两帧指纹一致门（≤2s，超时回退 0.5s 静置）
  │              → 刷后重读：record_shop_snapshot('refresh') + refresh_effective 三值判定
  │              （False=全同 → 缺陷台账留证；True ∧ 金未扣 → 免费刷新 proc flag 留证不停机）
  │              + 刷新期望对账（金腿失读不评；牌腿 1-4 张不判错——槽位解锁未建模）
  │      SellBench：卖前对拍守卫 sell_guard_ok（生成期快照 vs 执行期 tracked 现槽名；
  │              不符 = stale_proposal 整笔跳过）→ 拖拽卖出 → tracking 同步（置 None 不紧缩）
  │              + register_round_sold（同轮不回买）+ 卖出入账实收观测（gold 前后差落盘）
  ├─ 波间判定：did_refresh=False → break（本轮无刷新 → 买完收工）
```

`MAX_REFRESH=4`【注·框架常量】是防死循环硬墙（plan 的 _refresh_cap 是单次 plan 软上限，每轮 plan 重置）；刷新是否值得刷是策略判据（P40 三层门，见 `../strategy-docs/11_shop_decisions.md` §刷新）。

## 3. 离店条件

| 条件 | 语义 |
|---|---|
| **空序列** | decide_shop_screen 返回 [] = 决策完成（契约终止语义）→ 本波 prefix 为空、did_refresh=False → break → 关店。唯一常规离店条件 |
| 刷新硬墙 | MAX_REFRESH 耗尽 → 本轮当未刷新收工 |
| 未识别卡停机 | 收工前检查：商店仍有未识别槽（SIFT miss）→ 判据化自愈重读 2 帧（`_wait_shop_row_stable` 两帧指纹一致 + ≥1.0s 最短观察窗）→ 仍 miss → 停机保画面待建档（用户裁决 2026-08-24：未识别不能降级带病跑；`cw_op_buy_cards.py:1072-1135`） |
| 波循环异常 | 上抛 → 编排层单元 aborted 关账，店不收（交上层重新识别） |

## 4. 单元收尾 finalize_buy_phase（`cw_screen_prep.py:1996-2134`）

1. **买后重估**（r251）：total_buy/level/refresh 非零 → 用最新 bench 重跑一次 update_target（买桥件当轮认领，紧随 deploy 有方向；幂等）。无升级单元走增量态构造 `build_post_buy_incremental_state`（gold 真读 + tracked 重播替代整帧 OCR；fail-closed 两维：金失读/tracked 空 → 回退全量 read_game_state）。
2. **买牌期望暂存**：纯买入单元（无卖出/未识别牌）→ `compute_buy_expect` 暂存 `session.pending_buy_expect`，主环 heavy 定型帧消费对账。
3. **gold 差值双源对拍**：expected = 开店首读金 − 全程执行花金 + 全程卖入（`expected_gold_after_actions`；基线必须取首读快照，末波重读已净含花销）；|差|>2 → obs_conflict 留证（容忍 ±2 = 收入/连胜金不可观项）。关店实读金无条件暂存进单元行（gold_close，三态判定 unknown 面收窄）。
4. **执行事实暂存**：plan_truncated / refresh_* → set_unit_exec_facts（安灯分类器消费）。
5. 返回单元摘要（plan 买N张 升N次 刷N次 卖N张 + gold/lv/plane）。

## 5. 节点探针（`cw_screen_prep.py:1831-1933`）

关店后（店确定关的可靠时点）读节点行序列：日志 + 未识别图标采集钩子（版本前哨）+ 槽序表按位面首帧写入（`store_plane_table`，位面变更重写 + plane_lengths_seen 追加）+ current 节点左移推断（上帧 upcoming[0] 优先，锚定轮次防同轮多 probe 超前；OCR 直读兜底）+ upcoming 存下轮。**实时识别是权威**（应对 invest-env 改节点），槽序表只作离线统计源与左移兜底参照。

## 6. ⚠️ 现状违宪待改标记

本篇辖内无位面字面门与 hp 越权消费；数字均为框架常量（MAX_REFRESH、±2 对拍容差、settle 时长）不进策略决策门。登记一项流程债：`_shop_row_rects` 的字面量兜底 `Rect(300,228,1560,326)`（`cw_op_buy_cards.py:85`）——area 缺失才回退，1080p 项目既有前提，非判据违例。
