# 商店访问（shop_visit）

> 反向规格化来源 = `operations/cw_screen/cw_screen_prep.py:_open_shop_phase`（流程层商店编排）+ `operations/cw_screen/cw_screen_buy_cards.py:run_buy_waves`（商店单动作循环）+ `finalize_buy_phase`（单元收尾）。职责：商店打开态的一次访问编排——单动作决策循环驱动 `decide_shop_action`、终结 op 离店、收尾。路径根 = `src/sr_od/application/currency_war/`。
> **决策判据（买什么/卖什么/刷不刷/升不升）一律不在本篇**——本篇只管"循环怎么转、期望态怎么推进、何时离店"；判据见 `../strategy-docs/11_shop_decisions.md`。架构 = 单动作循环（已落码,单动作实现批 2026-09-06）。

## 1. 入口与形态（`cw_screen_prep.py:1791` `_open_shop_phase`）

OpenShop 动作两形态（`kernel/cw_prep_actions.py:108-117`）：

| 形态 | 编排 |
|---|---|
| `read_only=True`（读数性开店） | CwOpOpenShop（幂等：已开不点）→ heavy 观察（gold 开态真值进 session）→ **不调商店决策**（M-6 门保持：free=0 不进买牌）→ CwOpCloseShop → 节点探针 → 回备战。progressed = 开店成功（r364 进展保证语义） |
| `read_only=False`（显式开店） | 开店前 hp 三件组取**开店前的备战观察**（商店开态 HP 区不可读，读互斥）→ `visit_open_shop`（§2） |

第三入口形态：**0n 外循环转交（店已开）**——外循环 0n 分支命中后直接调 `CwScreenPrep.visit_open_shop()`（hp 缺省 `(None, False, False)` 不覆盖，fail-closed）：不调 open_shop（店已开由三 id_mark 锚确认，连点都不发），入口观察现读已开的店 → 策略器决策 → CloseShop 终结。路由层不硬编码收起（收不收归策略器，CloseShop = 商店画面 op 的一等终结动作）。

`visit_open_shop` = 商店访问尾段（run_buy_waves → CwOpCloseShop → finalize_buy_phase → 节点探针）的**编排单一源**，显式开店与 0n 转交两路径共用。失败路径不开收（店留着交上层重新识别）。

购买单元记账：开店前 `_spend_unit_open`（时点+gold 观测+F2 诚实标注），收尾 `_spend_unit_close`（boundary=closed/failed/aborted → spend_ledger.jsonl；`cw_screen_prep.py:1679` 起）。循环失败路径不开收（店留着交上层重新识别）。

## 2. 单动作循环（`cw_op_buy_cards.py:411 run_buy_waves`）

一次画面访问 = 轮「入口观察 + 逐动作决策循环」（决策 1）。外层段循环 `for _ in range(MAX_REFRESH + 1)`：每段 = 一次入口观察 + 一个内层决策循环；**截断器 `truncate_shop_frame_stable` 已退役**（截断点语义被终结 op 吸收，`shop.py:134` 载退役声明）。

```
for _ in range(MAX_REFRESH + 1):          # 段循环(刷新终结 = 下一段开始)
  ├─ 段顶 settle：非连击续刷段 sleep 0.3s（board 面板动画防 OCR 误读）+ park_cursor
  ├─ 入口观察(段顶,唯一决策读屏点 = 对账):
  │    read_game_state(phase=PHASE_PREP_SHOP_OPEN) 全量现读,漏斗容器直写
  │    (obs 族渠道签名;产出 = GameStateReadReceipt 回执,journal 行基准)
  │    → 店开入口防抖(shop 域未入容器时有界重读 3×0.8s;仍缺 = 交决策前置门)
  │    → 首段帧代次标注 full（方向视图由 decide_shop_action 入口消费刷新,续段 none 保持首段值）
  │    → node_type 台账回填（键 = 本帧 plane/round；查不到保持 None fail-open;
  │      回填 = write_logic 台账权威值覆盖,下一备战帧真读观察赢）
  │    → gold==0 救援（读 0 时重读 4 帧取首个 >0；结果留证 obs_conflict,
  │      救回值经观察渠道覆盖写 bs.gold）
  │    → 店开帧预算披露覆写（gold 真值入链,overflow/budget 三预算字段）
  │    → 播种期对账 guard_expected_vs_tracked(stage='seed';先对账分叉归因
  │      「播种/入口账」,投影后分叉才归「投影模型」)
  └─ 决策循环 while True（零读屏,决策 1/8;循环顶布局代次检差 reseed +
       防御帧帽 SHOP_SEGMENT_ACTION_CAP=16,超帽 RuntimeError 响亮暴露）:
       action = strategy.decide_shop_action(session, config)   # 恰返回一个动作,全函数
       │    异常 → decisions 落 Error 占位行 + 完整栈 log 后上抛（留证后抛,r95）
       ├─ CloseShop 终结 → break（关店点击由编排壳 CwOpCloseShop 承担）
       ├─ RefreshShop ∧ ledger.total_refresh ≥ MAX_REFRESH → 硬墙跳过:
       │    plan_truncated=True + refresh_skipped='max_cap'（可见化不停）→ break
       │    （终结 break 落地后每段恰至多一次刷新;硬墙封顶的是跨段刷新提案——
       │      终结→重进→再刷新,防外循环无进展;did_refresh 段级复位）
       ├─ spend_gate（发射帧仲裁,缺省 None）: 拒 = 本动作不执行 + 本访问收工
       ├─ 守卫断言（cw_shop_action_ops,决策 9——防 bug 路栏,炸出 = 策略器 bug）:
       │    guard_proposal_vs_expected（提案对象在期望态存在且未被消费）
       ├─ 动作 op execute（cw_shop_action_ops._OP_TABLE 词表分发;机械发出,
       │    执行回执 note_shop_action_receipt 逐动作一行,零成败判定）:
       │    BuyCard：槽号定位（payload 定长槽阵列,数组下标+1 = 物理槽;身份同一性
       │            优先,退化 (name,star)）→ 买前裁片纯留证 → 点牌位 → sleep 0.4
       │            → 账（total_buy/spend_executed/bought_names）→ 满栏自动多买
       │            补差（k 单一源 = merge_buy_k）
       │    LevelUp：点购买经验单击 → sleep 1.0（动画对齐）→ 账（clicks 序列 = 动作内部
       │            步骤,由决策循环逐帧重组——外部买面在单击之间不可插花）
       │    RefreshShop（终结）：刷前现读两口径（仅刷新段复用段顶整帧读;其余段点击前
       │            一帧现读金+牌名集）→ 刷前刷新钮真值读（三态+免费剩余次数）→
       │            点刷新 → 牌行两帧指纹一致门（≤2s,超时回退静置）→ 发出即记账
       │            （刷价 = 基价常量）;牌名集三值对比仅作安灯豁免判定输入 + 遥测
       │            （refresh_board_changed）;免费刷新 proc 留证（牌面已变∧金未扣
       │            → flag 不停机）+ 刷新期望对账（零决策）
       │    SellBench：拖拽机械单发（零判效零重试）→ 发出即记账（total_sell/
       │            total_sell_income 计划值）→ tracking 同步（置 None 不紧缩）
       │            + register_round_sold（同轮不回买）
       ├─ 落地门 apply_action_outcome（调用环单一源,cw_op_buy_cards）: execute
       │    恒 True（发出即职责完成,零判效）;门保留为结构防线——未落地 ⇒ 两侧
       │    都不动:不投影/不守卫/不入已买集/不计数;落地且非终结才进投影
       ├─ 投影（容器规则通道直写,纯计算零读屏）: apply_shop_action_logic 投影口
            简单腿 + apply_shop_merge_leg 合成升星腿（买前快照三件组基点）直写
            容器 → guard_expected_vs_tracked 双账断言（满栏买入 skip——满栏合成
              买面 tracked 与投影同走 _apply_full_bench_merge_buy 单一源,双账
              同构,不再丢件漏记）
  段尾：decisions 行（段尾累计行:actions = 本段执行累计,CloseShop 终结不入行;
          单动作下无截断丢弃尾,plan_truncated 仅由刷新硬墙/闸拒置位;粒度申报:
          刷新 = 终结 op 后本段即 break ⇒ 每刷独立成行）
       └─ 终结 op 退出（决策 4/7）: execute 后 _aop.terminal 为真 → break——
       │    刷新引入的新牌面 = 新事实,由下一段入口观察重建期望态;终结不投影
       │    （期望态按规格作废）,旧牌面不再回流策略器（消灭 RefreshShop 连发
       │    至硬墙 / 旧牌面 BuyCard 提案错买两个分支）。
  段间判定：did_refresh=False → break（本段无刷新/硬墙 → 收工）
```

`MAX_REFRESH=4`【注·框架常量】是**visit 级刷新硬墙**（候选 (a) 落定）：终结→重进→再刷新的循环形态下,防策略器反复选刷新造成外循环无进展——超墙后终结集降级为仅关店。刷新是否值得刷是策略判据（P40 三层门,见 `../strategy-docs/11_shop_decisions.md` §刷新）。

**对抗修复批登记（补登节）**：①决策循环有防御帧帽 `SHOP_SEGMENT_ACTION_CAP=16`（内层 while 顶计数,超帽 RuntimeError + `plan_visit_action_cap` 分键,禁静默——与备战 VISIT_ACTION_CAP 同款防线）；②EV 买面席位门（满栏帧不提案,拒因分键 `shop_ev_bench_wait`;~~席位门后满栏 §2.5 分支与双账满栏豁免在商店生产路径不可达=防御纵深~~ **该不可达声明已被 2026-09-09 05:52 运行局证伪**——m2_merge_completion 提案在满栏帧照常发射并触发满栏 §2.5 合成分支）；③计数键 `shop_visit_idle_gold`（旧 `shop_wave_idle_gold` 改名,visit 语义,跨结构不可直接对拍）。

**与波批的输出等价是条件命题**（前提 = 波批投影无残差;投影残差史 bug 类）——帧级锁按「锁的存在性纪律」重推语义,禁机械跟绿（w614 哨兵锚已重锚）。

## 3. 离店条件

| 条件 | 语义 |
|---|---|
| **CloseShop 终结** | 策略器主动选关店终结 op（全函数「无动作可做」的表达,决策 4/5;取代旧「空序列 = 决策完成」通道）→ 本段收工。唯一常规离店条件 |
| 全 unknown 窗 | 牌面含 unknown 槽（整帧 OCR/SIFT 失读窗）→ 决策入口前置门仅返回 CloseShop（花钱动作 BuyCard/RefreshShop/LevelUp 一律禁发射,不猜;真买空 [empty×5] 不受影响）→ 收工段未识别卡停机钩子随即承接留证 |
| 刷新硬墙 | visit 级 `total_refresh` ≥ MAX_REFRESH → 终结集降级仅关店（本轮当未刷新收工） |
| 未识别卡停机 | 收工前检查：牌面仍有 unknown 槽（kind=='unknown' 判据;empty=确证空位不计）→ 判据化自愈重读 2 帧（`_wait_shop_row_stable` 两帧指纹一致 + ≥1.0s 最短观察窗）→ 仍 miss → 停机保画面待建档（用户裁决 2026-08-24：未识别不能降级带病跑；`cw_op_buy_cards.py` 收工段停机钩子） |
| 循环异常 | 上抛 → 编排层单元 aborted 关账，店不收（交上层重新识别） |

## 4. 单元收尾 finalize_buy_phase（`cw_screen_prep.py:2071`）

1. **买后重估暂存**（r251;内化形态）：total_buy/level/refresh 非零 → 用最新 bench 构造 `_post` **暂存为黑板派生帧标 view**（`prep_obs_frame` 缺席则跳过,0n 直入商店窄窗）,由下一决策入口(pick/备战)消费刷新——买桥件当轮认领,紧随消费面有方向;幂等(键守卫段同轮短路)。无升级单元走增量态构造 `build_post_buy_incremental_state`（gold 真读 + tracked 重播替代整帧 OCR；fail-closed 两维：金失读/tracked 空 → 回退全量 read_game_state）。
2. **买牌期望暂存**：纯买入单元（无卖出/未识别牌）→ `compute_buy_expect` 暂存 `session.pending_buy_expect`，主环 heavy 定型帧消费对账。
3. **gold 差值双源对拍**：expected = 开店首读金 − 全程执行花金 + 全程卖入（`expected_gold_after_actions`；基线必须取首读快照，末波重读已净含花销）；|差|>2 → obs_conflict 留证（容忍 ±2 = 收入/连胜金不可观项）。关店实读金无条件暂存进单元行（gold_close，三态判定 unknown 面收窄）。
4. **执行事实暂存**：plan_truncated / refresh_* → set_unit_exec_facts（安灯分类器消费）。
5. 返回单元摘要（plan 买N张 升N次 刷N次 卖N张 + gold/lv/plane）。

## 5. 节点探针（`cw_screen_prep.py` `_open_shop_phase` 收尾段）

关店后（店确定关的可靠时点）读节点行序列：日志 + 未识别图标采集钩子（版本前哨）+ 槽序表按位面首帧写入（`store_plane_table`，位面变更重写 + plane_lengths_seen 追加）+ current 节点左移推断（上帧 upcoming[0] 优先，锚定轮次防同轮多 probe 超前；OCR 直读兜底）+ upcoming 存下轮。**实时识别是权威**（应对 invest-env 改节点），槽序表只作离线统计源与左移兜底参照。

## 6. ⚠️ 现状违宪待改标记

本篇辖内无位面字面门与 hp 越权消费；数字均为框架常量（MAX_REFRESH、±2 对拍容差、settle 时长）不进策略决策门。登记一项流程债：`_shop_row_rects` 的字面量兜底 `Rect(300,228,1560,326)`（`cw_op_buy_cards.py:81`）——area 缺失才回退，1080p 项目既有前提，非判据违例。
