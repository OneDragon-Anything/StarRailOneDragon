# 商店访问（shop_visit）

> 反向规格化来源 = `operations/cw_screen/cw_screen_prep.py:_open_shop_phase`（流程层商店编排）+ `operations/cw_op/cw_op_buy_cards.py:run_buy_waves`（商店单动作循环）+ `finalize_buy_phase`（单元收尾）。职责：商店打开态的一次访问编排——单动作决策循环驱动 `decide_shop_action`、终结 op 离店、收尾。路径根 = `src/sr_od/application/currency_war/`。
> **决策判据（买什么/卖什么/刷不刷/升不升）一律不在本篇**——本篇只管"循环怎么转、期望态怎么推进、何时离店"；判据见 `../strategy-docs/11_shop_decisions.md`。架构 = ADR-0517 单动作循环（已落码,实施 ADR-0518）。

## 1. 入口与形态（`cw_screen_prep.py:1791` `_open_shop_phase`）

OpenShop 动作两形态（`kernel/cw_prep_actions.py:108-117`）：

| 形态 | 编排 |
|---|---|
| `read_only=True`（读数性开店） | CwOpOpenShop（幂等：已开不点）→ heavy 观察（gold 开态真值进 session）→ **不调商店决策**（M-6 门保持：free=0 不进买牌）→ CwOpCloseShop → 节点探针 → 回备战。progressed = 开店成功（r364 进展保证语义） |
| `read_only=False`（显式开店） | 开店前 hp 三件组取**开店前的备战观察**（商店开态 HP 区不可读，读互斥）→ `run_buy_waves`（§2）→ CwOpCloseShop → `finalize_buy_phase`（§4）→ 节点探针 |

购买单元记账：开店前 `_spend_unit_open`（时点+gold 观测+F2 诚实标注），收尾 `_spend_unit_close`（boundary=closed/failed/aborted → spend_ledger.jsonl；`cw_screen_prep.py:1679` 起）。循环失败路径不开收（店留着交上层重新识别）。

## 2. 单动作循环（`cw_op_buy_cards.py:411 run_buy_waves`；ADR-0517/0518）

一次画面访问 = 轮「入口观察 + 逐动作决策循环」（ADR-0517 决策 1）。外层段循环 `for _ in range(MAX_REFRESH + 1)`：每段 = 一次入口观察 + 一个内层决策循环；**截断器 `truncate_shop_frame_stable` 已退役**（截断点语义被终结 op 吸收，`shop.py:134` 载退役声明）。

```
for _ in range(MAX_REFRESH + 1):          # 段循环(刷新终结 = 下一段开始)
  ├─ 段顶 settle：非连击续刷段 sleep 0.3s（board 面板动画防 OCR 误读）+ park_cursor
  ├─ 入口观察(段顶,唯一决策读屏点 = 对账):
  │    read_game_state(phase=PHASE_PREP_SHOP_OPEN) 全量现读（gold/hp/lv/plane/round/shop 五槽）
  │    → _apply_hp（shop 关闭帧 hp 三件组值+位同写覆盖）
  │    → 首段 update_target（执行边界压缩：替代原开店后专用读）
  │    → node_type 拷 Director shop 关态真值（shop 开帧节点行被遮恒 None）
  │    → dual_track_phase/committed_from 拷入（R1 唯一读端）
  │    → gold==0 救援（读 0 时重读 4 帧取首个 >0；结果留证 obs_conflict）
  │    → gold_open = 首段快照（对拍基线，任何动作执行前）
  │    → bench 播种：tracked_bench_chars 优先（带 star+merge），空退 tracked_bench（旧路径）
  │    → session.last_state = state；黑板写 session.shop_state_frame（写者白名单 = 本段/投影步）
  │    → 期望态覆盖点 shop_wave_top 清账（gold 族可信读清账；tracked 族透传不确认）
  │    → recorder.record_shop_snapshot('offer') + state/plan 日志行（带 node/next 节点上下文）
  └─ 决策循环 while True（零读屏,ADR-0517 决策 1/8）:
       action = strategy.decide_shop_action(session, config)   # 恰返回一个动作,全函数
       │    异常 → decisions 落 Error 占位行 + 完整栈 log 后上抛（留证后抛,r95）
       ├─ CloseShop 终结 → break（关店点击由编排壳 CwOpCloseShop 承担）
       ├─ RefreshShop ∧ ledger.total_refresh ≥ MAX_REFRESH → 硬墙跳过:
       │    plan_truncated=True + refresh_skipped='max_cap'（可见化不停）→ break
       ├─ 守卫断言（cw_shop_action_ops,决策 9——防 bug 路栏,炸出 = 策略器 bug）:
       │    guard_proposal_vs_expected（提案对象在期望态存在且未被消费）
       ├─ 动作 op execute（cw_shop_action_ops._OP_TABLE 词表分发）:
       │    BuyCard：点牌位 → sleep 0.4 → 账（total_buy/spend_executed/tracked/买前裁片
       │            留证）→ 满栏自动多买补差（k 公式单一源 cw_state.merge_buy_k）
       │    LevelUp：点购买经验单击 → sleep 1.0（动画对齐）→ 账（clicks 序列 = 动作内部
       │            步骤,由决策循环逐帧重组——外部买面在单击之间不可插花）
       │    RefreshShop（终结）：刷前现读两口径（仅刷新段复用段顶整帧读;其余段点击前
       │            一帧现读金+牌名集）→ 点刷新 → 牌行两帧指纹一致门（≤2.5s,超时回退
       │            静置）→ 刷后重读三通道（执行实现层遥测,候选 a）: record_shop_snapshot
       │            ('refresh') + refresh_effective 三值判定（False=全同 → 缺陷台账留证;
       │            True ∧ 金未扣 → 免费刷新 proc flag 留证不停机）+ 刷新期望对账
       │            （金腿失读不评；牌腿 1-4 张不判错——槽位解锁未建模）
       │    SellBench：拖前 gold 基数 → 拖拽卖出（拖 3 次源槽未变 = 失败,不投影——
       │            两侧都不动保持双账一致）→ tracking 同步（置 None 不紧缩）
       │            + register_round_sold（同轮不回买）+ 卖出入账实收观测（前后 gold 差落盘）
       └─ 投影（决策 10:动作 op project = cw_state.simulate 单一源,纯计算零读屏）:
            非终结且落地 → 黑板推进 session.shop_state_frame = project(态)
            → guard_expected_vs_tracked 双账断言（满栏买入豁免——tracked 的 bench_place
              满栏丢件 vs simulate §2.5 k 张分支不同构,对账重挂点 = 下一入口观察）
  段尾：state.equips 拷贝（必须在决策之后——cw_comps 装备动态权重读 state.equips）
        + decisions 行（段尾累计行:actions = 本段执行累计,CloseShop 终结不入行,
          与旧「空序列=完成」的行形态对齐;单动作下无截断丢弃尾,plan_truncated
          仅由刷新硬墙置位）
  段间判定：did_refresh=False → break（本段无刷新/硬墙 → 收工）
```

`MAX_REFRESH=4`【注·框架常量】是**visit 级刷新硬墙**（ADR-0517 §3.1 候选 (a) 落定）：终结→重进→再刷新的循环形态下,防策略器反复选刷新造成外循环无进展——超墙后终结集降级为仅关店。刷新是否值得刷是策略判据（P40 三层门,见 `../strategy-docs/11_shop_decisions.md` §刷新）。

**对抗修复批登记（ADR-0518 补登节）**：①决策循环有防御帧帽 `SHOP_SEGMENT_ACTION_CAP=16`（内层 while 顶计数,超帽 RuntimeError + `plan_visit_action_cap` 分键,禁静默——与备战 VISIT_ACTION_CAP 同款防线）；②EV 买面席位门（满栏帧不提案,拒因分键 `shop_ev_bench_wait`;席位门后满栏 §2.5 分支与双账满栏豁免在商店生产路径不可达=防御纵深）；③计数键 `shop_visit_idle_gold`（旧 `shop_wave_idle_gold` 改名,visit 语义,跨结构不可直接对拍）。

**与波批的输出等价是条件命题**（前提 = 波批投影无残差;投影残差史见 ADR-0517 §消灭的 bug 类）——帧级锁按「锁的存在性纪律」重推语义,禁机械跟绿（w614 哨兵锚已重锚,ADR-0518）。

## 3. 离店条件

| 条件 | 语义 |
|---|---|
| **CloseShop 终结** | 策略器主动选关店终结 op（全函数「无动作可做」的表达,ADR-0517 决策 4/5;取代旧「空序列 = 决策完成」通道）→ 本段收工。唯一常规离店条件 |
| 刷新硬墙 | visit 级 `total_refresh` ≥ MAX_REFRESH → 终结集降级仅关店（本轮当未刷新收工） |
| 未识别卡停机 | 收工前检查：商店仍有未识别槽（SIFT miss）→ 判据化自愈重读 2 帧（`_wait_shop_row_stable` 两帧指纹一致 + ≥1.0s 最短观察窗）→ 仍 miss → 停机保画面待建档（用户裁决 2026-08-24：未识别不能降级带病跑；`cw_op_buy_cards.py` 收工段停机钩子） |
| 循环异常 | 上抛 → 编排层单元 aborted 关账，店不收（交上层重新识别） |

## 4. 单元收尾 finalize_buy_phase（`cw_screen_prep.py:2071`）

1. **买后重估**（r251）：total_buy/level/refresh 非零 → 用最新 bench 重跑一次 update_target（买桥件当轮认领，紧随 deploy 有方向；幂等）。无升级单元走增量态构造 `build_post_buy_incremental_state`（gold 真读 + tracked 重播替代整帧 OCR；fail-closed 两维：金失读/tracked 空 → 回退全量 read_game_state）。
2. **买牌期望暂存**：纯买入单元（无卖出/未识别牌）→ `compute_buy_expect` 暂存 `session.pending_buy_expect`，主环 heavy 定型帧消费对账。
3. **gold 差值双源对拍**：expected = 开店首读金 − 全程执行花金 + 全程卖入（`expected_gold_after_actions`；基线必须取首读快照，末波重读已净含花销）；|差|>2 → obs_conflict 留证（容忍 ±2 = 收入/连胜金不可观项）。关店实读金无条件暂存进单元行（gold_close，三态判定 unknown 面收窄）。
4. **执行事实暂存**：plan_truncated / refresh_* → set_unit_exec_facts（安灯分类器消费）。
5. 返回单元摘要（plan 买N张 升N次 刷N次 卖N张 + gold/lv/plane）。

## 5. 节点探针（`cw_screen_prep.py` `_open_shop_phase` 收尾段）

关店后（店确定关的可靠时点）读节点行序列：日志 + 未识别图标采集钩子（版本前哨）+ 槽序表按位面首帧写入（`store_plane_table`，位面变更重写 + plane_lengths_seen 追加）+ current 节点左移推断（上帧 upcoming[0] 优先，锚定轮次防同轮多 probe 超前；OCR 直读兜底）+ upcoming 存下轮。**实时识别是权威**（应对 invest-env 改节点），槽序表只作离线统计源与左移兜底参照。

## 6. ⚠️ 现状违宪待改标记

本篇辖内无位面字面门与 hp 越权消费；数字均为框架常量（MAX_REFRESH、±2 对拍容差、settle 时长）不进策略决策门。登记一项流程债：`_shop_row_rects` 的字面量兜底 `Rect(300,228,1560,326)`（`cw_op_buy_cards.py:81`）——area 缺失才回退，1080p 项目既有前提，非判据违例。
