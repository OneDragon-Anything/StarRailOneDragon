# W970 · CW 画面分层架构重构设计(流程层 / 观察层按画面 / 决策层按画面拆 / op 原子化)

- 日期:2026-09-02;状态:FINAL(对抗收敛:轮 1 三视角 30 findings + 轮 2 双视角复核 8 条 + 轮 3 收敛复核 3 条实现级修复,全处置;待用户裁决项 1 项见 §8,不阻塞实施)
- 依据:用户口述架构愿景(2026-09-02,逐段)+ DD-010(装备区识别纯化)+ DD-011(操作完成自等动画/稳定门退役)
- 性质:设计文档(先设计后实现);本文只定结构 / 职责 / 接口契约 / 迁移路线,不含行为参数值(值在代码常量,注释带出处)
- **结论一句话:把「按画面分工」立为架构纪律——流程层识别画面并调度,观察/决策接口按画面拆分(备战接口=现 decide_prep_action 收敛,商店接口=现 decide_prep 收敛),op 原子化且完成后自等动画或等判稳标志;BuyShopCards 复合 op 解体,EnsureShop 条件动作退役(其隐藏挂点与决策语义随迁);分四批迁移,批 A 前置「源码锁迁移清单」。**

---

## 0. 接口现状勘误(对抗轮 1 P0 修正,先读)

现状两个决策接口的真实角色(**R2 勘误,初稿曾张冠李戴**):

| 现状接口 | 位置 | 真实角色 | 产出动作族 |
|---|---|---|---|
| `CwStrategy.decide_prep(state, session, config)` | cw_strategy.py:113;**调用点 = shop.py:699(RunBuyPhase 执行中途回调)** | **商店开画面**的 d2 决策(买/升/刷/卖/演进替换) | kernel Action 族:BuyCard / RefreshShop / SellBench / SellDeployed / CompTransaction / LevelUp |
| `CwStrategy.decide_prep_action(obs, session, config)` | decision_v2/strategy.py:730;**调用点 = director 决策循环(备战屏环步)** | **备战画面**的环步决策(含跨画面过渡意图) | PrepAction 族:EnsureShopOpen / EnsureShopClosed / RunBuyPhase / RunDeploy / RunEquip / DeployMove / SellDeployed / SellBench(腾席链 a2) / StartBattle / ClickSpheres / OpenBox / OpenTome / PickBoxCard / DeferSpheres / BailToOuter / LevelUp |

## 1. 背景与动机

用户口述架构愿景(2026-09-02,原话要点):

1. 流程层把控整体流程(进对局、每个操作之后下一个做什么);流程层负责**识别画面**,再调对应观察。
2. 观察只处理当前画面所需的观察。
3. 决策只做当前画面所需的决策——备战画面的决策只会有「打开商店」,不含「商店购买」。
4. 策略接口按画面提供:备战一个、商店开一个。
5. op 原子化:开商店 op 只管开商店,买牌 op 只管买牌。
6. op 规范(DD-011):op 完成后自等动画时间;调用方从稳定画面出发。

现状病灶:

- **复合 op 越权**:`BuyShopCards.buy`(shop.py,~700 行)包办「确保开店→读牌→回调 d2 决策→买/升/刷/卖→收起→买后重估」;「发现商店没开自己先开」是画面职责越权——买牌 op 被调用即蕴含流程层已判定画面为商店开态。
- **决策两接口职责错位**:备战屏环步决策(`decide_prep_action`)产出跨画面过渡意图(EnsureShopOpen/RunBuyPhase),把画面切换塞进决策;商店屏决策(`decide_prep`)被执行层中途回调,依赖倒置。
- **稳定门残留**:gate 与 DD-011 自等动画并存,末批退役依赖本设计的流程层收敛。

## 2. 目标架构

### 2.1 分层职责表

| 层 | 职责 | 纪律(禁区) |
|---|---|---|
| 流程层(`battle_loop` 主循环 + director 编排) | 进对局;**识别画面**(建档判定)→ 按画面调观察 → 按画面调决策 → 按决策调 op → 决定下一步;**读互斥与观察时机由流程层按画面调度** | 不实现具体操作;不做字段级观察;不含业务决策 |
| 观察层(按屏分工,现有模块) | 只观察当前画面所需字段,产出 obs | 不决策、不操作 |
| 决策层(按画面双接口) | 备战接口:备战画面动作(部署/卖上阵/出战/点球/开箱/**打开商店**…);商店接口:商店开画面动作(买/升/刷/卖备战/演进替换) | 备战接口不含商店内动作;商店接口不做画面切换 |
| op 层(原子 op) | 本画面内一个原子动作;完成后自等动画/等判稳标志(DD-011) | 不自查前置画面、不自救、不二次稳定验证 |

### 2.2 画面判定与流转

**判定序(对抗轮 1 修正 + 轮 2 流程复核补,顺序敏感)**:
1. **暗色锁定子态族前置**(轮 2 补):策略锁定/遭遇锁定(#12/#20 实测暗色态备战双锚仍精准命中、收起锚 miss)→ 锁定态分支必须**先于**备战/商店判定(现行 battle_loop 0m 分支序前提,批 C 编排接管不重写此判定链)。
2. **商店开态单锚「按钮-收起」**:命中 → 商店开画面。注意「备战阶段」文本([250,30,520,120])在备战档与开商店档同元素同址,**无画面判别力**,不得作分支判据。
3. **备战双锚**(购买经验+出战):命中 → 备战画面。

自动开店与判定的时序竞争(战斗胜利后商店自动弹出晚于判定)由 director 预收探针现行语义承接,批 D 评估其归宿(收进流程层 or 随 gate 退役改 retry)。**批 C 流程编排接管 = 编排接管,判定链(锚集与优先序)沿用现行 battle_loop 资产不重写。**

```
备战画面(currency_war_battle_prep)
  备战观察(关帧字段:hp 真读/node_type/节点行…) → 备战决策接口
    → [部署/卖上阵/出战/点球/开箱/打开商店(read_only 变体见 §4.4)]
         ↓ 打开商店
OpenShopOp(原子:点「按钮-商店」→ 判稳轮询「按钮-收起」出现)
商店开画面(currency_war_battle_prep_shop_open)
  商店观察(gold/shop/board/refresh 现读 + 融合字段,§4.1.2)→ 商店决策接口
    → [买/升/刷/卖备战/演进替换] × 波(刷新后重判,§4.3.2) → 决策完成
         ↓ 完成
CloseShopOp(原子:点「按钮-收起」→ 自等收起动画 1.0s(#15)) → 回备战画面
```

overlay 画面族(投资策略/投资环境/遭遇锁定/补给锁定/补给箱选卡/巨星/伙伴/秘典)不在本设计双接口范围——沿用既有 handler/bail 交主循环机制;相关动作意图(PickBoxCard 等)归 handler 族。

### 2.3 兼容性事实(已对齐部分)

- 观察层已按屏分工;本设计只把「观察调用时机」收归流程层按画面调度。
- DD-011 常量单一源在 `prep_actions`(SHOP_CLOSE_ANIM_S=1.0 #15;开店判稳轮询间隔 1s 上界 4 轮)。
- 装备区识别已纯化(DD-010),前置画面契约同款纪律。

## 3. 现状对照(As-Is → To-Be)

| 组件 | 现状(勘误后) | 目标 | 批次 |
|---|---|---|---|
| `decide_prep`(商店屏 d2 决策) | RunBuyPhase 中途回调;产出 kernel Action 族 | 收敛为 **`decide_shop_screen`**(商店接口);签名与动作族承接,输入改流程层组装的融合 obs(§4.1.2) | 批 B |
| `decide_prep_action`(备战屏环步决策) | 产出 PrepAction 族(含跨画面过渡意图 EnsureShopOpen/RunBuyPhase) | 收敛为 **`decide_prep_screen`**(备战接口):只输出备战画面动作 + OpenShop;不再输出 RunBuyPhase/EnsureShopOpen | 批 B/C |
| `BuyShopCards.buy` | 复合 op(开/读/决策/执行/收/重估) | 解体:`OpenShopOp` / `BuyCardsOp` / `CloseShopOp`;买后重估与对账挂点随迁(§4.3.4) | 批 A(结构)/批 C(编排) |
| `EnsureShopOpen` | 腾席链 b「开商店取 gold 真值」的决策步 + EnsureShop 条件自查双语义 | **语义拆解**:①读数性开店 → `OpenShop(read_only=True)` 变体(流程层只刷新观察、不调商店决策,读完 CloseShop,§4.4);②画面切换 → `OpenShop` 显式意图;条件自查退役(画面判定承接) | 批 C |
| `EnsureShopClosed` | 关店动作 + **节点类型探针挂点判据**(字符串匹配 `'EnsureShopClosed' in key`,prep_director 旧环/v2 环两处) | 退役:关店由商店决策完成触发 CloseShopOp;**探针挂点随迁至 CloseShopOp 完成后**,挂点判据弃字符串匹配改类型分派 | 批 C |
| `_handle_bench_full`(shop.py 内席满急救) | 备战画面动作藏在买牌 op(点购买经验×10+位置式拖卖);与 director 腾席链双源 | 上移备战接口前置破墙链,与 director 腾席链合流消双源 | 批 C |
| 买牌观测自检网(pixel-diff/SIFT 回读/缺陷台账) | buy 内联 | 归 BuyCardsOp(执行期验证)或观察层(定型帧),迁移清单列名(批 A) | 批 A |
| 环入口 gate + heavy 定型帧 gate(battle_loop/prep_director) | 测量驱动稳定门 | 相位识别 + retry 承接(单点设计,含 1-1 不自动开店特例 #5/#29) | 批 D |
| 节点过渡 preset(run_node/_overlay_confirm) | gate 加速基线预置 | 随上游 gate 退役路径处理 | 批 D |
| `LOCKED_RESUME_ENHANCED`(shop.py,默认关) | 建立在「买牌 op 自开店+开店失败分型接管出战」上 | **删除**(存在前提被本设计取代),ADR 记录 | 批 A |

## 4. 目标接口与 op 契约

### 4.1 决策接口(按画面拆)

#### 4.1.1 接口签名与前身

```
# 备战画面接口(前身 = decide_prep_action;director 环步调用)
decide_prep_screen(obs_prep, session, config) -> list[PrepScreenAction]

# 商店开画面接口(前身 = decide_prep;OpenShopOp 后由流程层调用)
decide_shop_screen(obs_shop, session, config) -> list[ShopScreenAction]
```

#### 4.1.2 决策输入组装契约(对抗轮 1 P0 修正:商店观察是跨帧融合态)

`obs_shop` **不是**商店帧的单帧现读——现役 d2 决策输入为跨帧融合态,字段级来源表(迁移规格,等价于现 shop.py 融合段的搬迁):

| 字段族 | 来源 | 帧 |
|---|---|---|
| gold / shop 牌面 / refresh 可用 | 商店帧现读 | 开商店帧 |
| hp / hp_readable / hp_trusted | 关店帧 HP 读链(新鲜度门+结算真值+r1 重试+fail-closed,现 shop.py 入口段) | **关店帧**(shop 开态 HP 区不可读) |
| node_type | director 关店帧探针(shop 开帧节点行被遮恒 None) | 关店帧 |
| bench / tracked_bench_chars | session tracked 播种(关店帧 SIFT/OCR 累积) | session |
| dual_track_phase / focus_factions | session 位 | — |

`obs_prep` 同理 = 备战帧现读(hp/gold 关态真读/node_type/节点行)+ session 融合。**组装职责归流程层**(观察调用时机归属的自然结果);批 A 对拍口径 = 「融合态快照对拍」(§5)。

#### 4.1.3 动作词表(对抗轮 1 补全)

```
PrepScreenAction ∈ {DeployMove, SellDeployed, SellBench(腾席链 a2), StartBattle,
                    ClickSpheres, OpenBox, OpenTome,
                    PickBoxCard(过渡期,批 C 迁 handler 族),
                    DeferSpheres, BailToOuter,
                    OpenShop, OpenShop(read_only), RunDeploy*, RunEquip*,
                    EnsureShopClosed*(过渡期,批 C 退役)}
ShopScreenAction ∈ {BuyCard, LevelUpShop, RefreshShop, SellBench(商店侧 d2),
                    SellDeployed(谷底回滚), CompTransaction}
```

- `LevelUp` 拆 `LevelUpShop`(商店侧;现单一意图跨态共用,拆后执行器/遥测/对拍可消歧;备战侧暂无独立升级需求,出现时再增)。
- 控制流意图(`DeferSpheres`/`BailToOuter`):框架信号,不走 execute 验证链(现状语义保持),由流程层直接消费。
- `RunDeploy`/`RunEquip` 组合意图:**明确保留**(过渡期复合执行器;其内部原子化另立批次,不在本设计范围——与 RunBuyPhase 解体同思路,单独评估)。
- 卖动作归属(R2 复核勘误):`SellBench` 为**两接口共用**(商店侧 d2 卖通道 + 备战侧腾席链 a2 卖杂件腾席,decision_v2/strategy.py:899)/`SellDeployed`(备战侧与谷底回滚)/`CompTransaction`(演进替换事务,含卖腿)——同轮已买/已卖集登记点随 decide_shop_screen 输入组装迁移(现 shop.py 波循环顶)。
- `PickBoxCard`:过渡期仍由备战决策产出(现 strategy.py:759 规则 1),批 C 随补给箱 overlay 归 handler 族,迁出备战词表。

#### 4.1.4 终止语义

`decide_shop_screen` 终止 = **返回空序列**(单一形式,不设 Done 成员);流程层据空序列触发 CloseShopOp。

### 4.2 op 契约(原子 op 统一规范)

| op | 前置画面 | 动作 | 完成承诺 | 产出画面 |
|---|---|---|---|---|
| `OpenShopOp` | 货币战争-备战 | 点「按钮-商店」(**幂等**:自动开店场景点击落空不判负) | 判稳轮询「**按钮-收起**」出现,1s 间隔 4 轮——判稳标志必须选**目标画面独有锚**(轮 2 流程复核 P0 勘误:「备战阶段」文本两档同元素同址无判别力;「按钮-商店/收起」同址,自动开店竞速下点击可命中反义按钮 → 收起消失 → 轮询超时 → retry,不假成功) | 备战-开商店 |
| `BuyCardsOp` | 备战-开商店 | 执行商店动作序列(§4.3.2 波循环) | 末动作动画等待(升级 1.0s #22 等) | 备战-开商店 |
| `CloseShopOp` | 备战-开商店 | 点「按钮-收起」 | 自等收起动画 1.0s(#15) | 货币战争-备战 |

- **DD-011 验证式例外**(对抗轮 1 补):结果可验证的动作(刷新→两帧一致门 #9、点球→球数验证 H-3、开局补给→结束标志待观察 #5)**不适用固定动画等待**,以验证通过为完成;验证式与固定等待是 DD-011 的两种完成判定,后继防线(retry/对账)不变。此例外条款回写 dd-011。
- **overlay 守卫职责归流程层**:op 内不再自查事件 overlay;mid-run overlay(如 #24 羁绊 overlay 延迟弹出)由「逐动作回流程层确认画面」机制暴露(§4.3.1),动作落空可观测(按钮缺失=未生效)。
- op 内**禁止**:自查前置画面状态、自救性开店/收起、二次稳定验证。

### 4.3 流程编排规格

#### 4.3.1 备战动作执行语义

备战决策返回动作 list = **逐动作回流程层确认画面后执行**(执行器可受托做轻量锚快查,判定权在流程层)。理由:#24 羁绊 overlay 延迟 ~4s 弹出等 mid-run 画面变化必须每步暴露;现行防线(#24 快查锚)保留为实现形态。

#### 4.3.2 商店动作循环(两阶段重判,对抗轮 1 补)

```
波循环(上界 MAX_REFRESH 归流程层):
  商店观察(融合 obs,§4.1.2)→ decide_shop_screen → 动作序列
  → 执行至首个 RefreshShop(含)→【RefreshShop 后 shop 牌面失效(r6 F8)】
  → 重观察 → 重 decide_shop_screen → …直至空序列(完成)
```

- `decide_shop_screen` 契约:**RefreshShop 若出现必为末位动作**(流程层截断兜底);MAX_REFRESH 硬墙归流程层。
- 刷新期望构建(`build_refresh_expect`/`refresh_reconcile_mismatches`,现 shop.py 惰性反向 import)随循环归编排层——「唯一合法评估窗=本波内」的现读时序(pre-shot/免 pre-shot 语义)一并随迁。

#### 4.3.3 动作 → 产物画面映射(流程层据此判定下一步)

| 动作 | 产物画面 |
|---|---|
| DeployMove / SellDeployed / SellBench / ClickSpheres / LevelUpShop / StartBattle(点出战前) | 备战/商店(原地) |
| OpenBox | 补给箱 overlay(handler 族) |
| OpenTome | 秘典 overlay(handler 族) |
| OpenShop | 备战-开商店 |
| StartBattle(点出战) | 战斗(交 battle_loop 战斗分支) |

#### 4.3.4 买后重估与对账挂点随迁(输入契约表)

现 buy 内「买后重估」五项输入随 op 拆分迁移:

| 输入 | 来源 | 去向 |
|---|---|---|
| state(末波融合态) | 商店观察 | BuyCardsOp 产出/流程层持有 |
| hp 三件组(value/readable/trusted) | **OpenShopOp 之前的备战观察**(关帧 HP 读链:新鲜度门+结算真值+r1 重试+fail-closed)→ 归流程层备战观察(商店开态 HP 区不可读,§4.1.2) | 流程层 |
| tracked_bench_chars(空时回退旧 seed) | session | session |
| gold(read_gold_settled 两帧一致门) | **时序锚 = 收起点击后**(入账计数器尾帧防线)→ 由 CloseShopOp 完成后流程层立即执行 | 流程层 |
| total_level 门 | 商店动作账(BuyCardsOp 产出) | 流程层 |

对账挂点同步随迁:spend 关店对拍(`set_unit_gold_close`/`set_unit_exec_facts`,身份键 (plane,round,unit_seq) 契约不变、「每单元必写」约定不变)、w536 买牌期望基座(单元尾计算暂存)。**批 A 迁移清单列名**(§5)。

#### 4.3.5 读数时序契约(对抗轮 1 补:EnsureShop 退役后读互斥的承接)

- 读互斥(HP 关态可读/gold 开态可读,05_observation「读取互斥」条)的执行机制由「EnsureShop 动作显式管理」改为「**流程层按画面调度观察**」:关帧字段读在 OpenShopOp 之前的备战观察;开态字段读在商店观察;观察层对各字段加**前置画面位断言**(画面不符 → 返 None + obs_conflict 留证,不抛错),违例暴露方式与现行 fail-closed 一致。**商店观察冲突的承接 = 流程层重走 §2.2 判定序**(画面已漂移 → 按判定序重新分流,不硬吃冲突帧)。
- node_type 探针:随 CloseShopOp 完成后执行(挂点判据改类型分派);产出链(store_plane_table/node_type_current/upcoming_types)不变。

#### 4.3.6 腾席链 b 读数性开店(对抗轮 1 补)

腾席链 b(bench 满 free=0,需 gold 真值推进判级)→ 备战接口输出 `OpenShop(read_only=True)`:流程层执行 OpenShopOp → 商店观察(拿 gold 真值)→ **不调商店决策**(M-6 门保持:free=0 不进买牌,不触发 _handle_bench_full 位置式卖)→ CloseShopOp → 回备战,链 b 以 trusted gold 继续。r364 进展保证语义(开店成功 = 本轮有进展)由 OpenShopOp 成功承担。

二次失败退路(r366b):链 b 开店重读**仍无 gold 真值**时,现役退路 = stale gold 试算 level_up_gate 直接试升级——该退路**保留**,落备战接口侧 stale-gold 分支,随批 C 迁移(read_only 编排不改变其触发条件)。

## 5. 分批路线与验证口径

| 批 | 内容 | 验证口径 |
|---|---|---|
| A(op 原子化,不动决策) | **前置步:源码锁迁移清单**(shop.py 相关源码锁逐把判定「语义仍有效→随迁新位置重建 / 锁旧结构→按纪律重推改写」;已知锁面:legacy_audit buy 源码锁、telemetry 主 record 站点位置锁、telemetry_collect record_sell_income 接线锁、w536 期望态接线锁、w505 关店对拍静态锁);OpenShopOp/CloseShopOp/BuyCardsOp 抽出(RunBuyPhase 内部改顺序调用);遥测写点随迁(spend_audit/set_unit_gold_close/set_unit_exec_facts,身份键不变);观测自检网归属落定;LOCKED_RESUME_ENHANCED 删除 | 源码锁按迁移清单更新后全绿 + **decisions.jsonl 逐决策对拍 + 全量 CW 测试 + 遥测分布对照**(对抗轮 1 裁决:放弃同运行逐调用严格等价——decide_prep 重度改写 session,同参二次调用必然漂移;备选旁路录制离线重放需 session 可序列化子集,列为可选增强) |
| B(决策接口拆分) | `decide_shop_screen`/`decide_prep_screen` 新接口;调用点迁移(shop.py d2 回调上移、director 环步换名);融合 obs 组装归流程层;LevelUp→LevelUpShop 拆分 | 商店决策对拍(旧 decide_prep vs 新 decide_shop_screen,同融合 obs 出同动作序列)+ 测试绿 |
| C(流程编排接管) | 备战接口输出 OpenShop/OpenShop(read_only);流程层编排(§4.3.2 循环 + §4.3.3 映射);RunBuyPhase 解体;EnsureShop 意图退役(探针挂点/腾席链 b/_handle_bench_full 随迁,§3) | 实机多局对照(买牌数/升级时机/rounds 遥测)+ 回归锁更新 |
| D(gate 末批) | 环入口/heavy 承接设计(**占位:含 1-1 不自动开店特例 #5/#29、自动开店时序竞争的预收探针归宿**)+ preset 处理 + gate 模块删除 | 单点设计另文 |

每批通用:`ruff` + 直接受影响测试 + 全量 CW 测试;commit 前三同步。

## 6. 风险与防线

| 风险 | 防线 |
|---|---|
| 前置画面契约被违反 | 识别不中 → retry;动作落空可观测;对账缺陷台账 |
| 动画时长/判稳标志过期 | retry 上升暴露 → 校准常量 |
| 批 A/B 行为漂移 | 融合态快照对拍 + decisions.jsonl 逐决策对拍(§5 批 A 裁决口径) |
| 兼容期双接口漂移 | 旧接口删除进批 C 完成判据 |
| 自动开店与手动开店合流 | 判稳标志统一(#7/#14)已覆盖 |
| node_type 停更(boss 判定退化) | 探针挂点随迁为批 C 完成判据项(§3) |
| 安灯漏停(gold_close 写点漂移) | 写点随迁进批 A 迁移清单 + exec_fail 分类器离线回归 |

## 7. 明确不做(边界)

- `battle_loop` 结算分支读数/遥测逻辑重组(独立批)。
- sim 适配:**独立批**。事实与约束:sim 引擎以 `decide_prep` 为核心重放入口(engine_p1/cw_replay/checks),且 sim 决策模型为「单次决策出全部动作」,与生产两画面模型不一致——接口签名定稿后,sim 适配方案(组合兼容入口 vs sim 内编排两接口)单独设计;兼容期 `decide_prep` 以组合兼容入口形态保留(内部编排 decide_prep_screen+decide_shop_screen 的等价编排),sim 与旧测试不断链。
- 观察模块内部重构(只改调用时机归属)。
- gate 模块删除(批 D 另文)。
- `RunDeploy`/`RunEquip` 内部原子化(保留为过渡期组合执行器,另立批次评估)。

## 8. 对抗记录

### 轮 3 收敛复核(最终轮)

- **收敛判定:收敛**(设计层面可实施)。一致性抽查(§0/§4.1.3/§4.3.4/§4.3.6/§4.3.5/§2.2 与 §8 互证)无自相矛盾残留;悬置项仅剩「待用户裁决项 1 项」。
- 实现级修复随判落地(2×P1 + 1×P2,不阻塞设计):①EnsureShop 开向轮询 `ok` 未初始化(UnboundLocalError)补初始化;②buy 开店轮询超时改 **fail-closed retry**(原静默继续 = 以「店已开」假设读牌面,竞速误关假成功形态存活;r347 超时语义回归);③常量注释判稳标志残漏跟改。

### 轮 2 复核(架构/代码视角 + 流程视角,2 agent 并行)

- 架构/代码视角(完成):轮 1 P0×3/P1×4 处置**全部有效**(§0 勘误经代码验证方向正确);R2 新引入 4 条已修正——①备战词表漏 SellBench(腾席链 a2,strategy.py:899)→ 两接口共用;②PickBoxCard 过渡期归属标注;③§4.3.4 hp 挂点措辞自相矛盾修正(OpenShopOp 前备战观察);④r366b 二次失败退路归属补录(保留,备战侧 stale-gold 分支)。
- 流程视角(完成):轮 1 九条处置 8 条闭合;新 4 条已全部处置——
  - **[P0] N1 判稳标志无画面判别力**(「备战阶段」文本在备战档与开商店档同元素同址;「按钮-商店/收起」同址,自动开店竞速点击可命中反义按钮 → 假成功):**完成判据改「按钮-收起」**(商店开态独有锚),已同步落地 prep_actions/ shop.py 两处轮询;判稳标志纪律 = **必须选目标画面独有锚**;误关场景(命中收起 → 面板关 → 收起消失)轮询超时 → retry,不假成功。判稳标志纪律与「#7 口述『备战阶段』出现即稳定」的冲突本质 = 口述指「画面稳定」而 bot 需要的是「开店生效判定」——生效判定以独有锚为准(同场留证:本条待玩家确认口述与本修正的口径归属)。
  - **[P2] N2**:§4.3.5 补「商店观察冲突 → 流程层重走判定序」。
  - **[P2] N3**:§2.2 补暗色锁定子态族前置分支序 + 「批 C 不重写判定链」声明正文落点。
  - 其余(①②③④⑤⑥⑧⑨)经 29 条时序 + screen_info 建档 ground truth 验证闭合。

### 轮 1(三视角并行,30 findings,全部处置)

| 视角 | findings | 处置摘要 |
|---|---|---|
| 游戏流程(9 条) | F1 商店接口漏卖(P0)/F2 备战接口漏 ClickSpheres+OpenBox/F3 缺动作→产物画面映射/F4 DD-011 需验证式例外(#9 刷新两帧一致/#16 球数/#5 开局补给)/F5 画面判定优先序(锁定态/概率表/祈愿依赖 battle_loop 分支序)/F6 备战 list 执行语义/#24 竞速/F7 OpenShop 幂等(自动开店竞速)/F8 1-1 特例批 D 占位/F9 EnsureShopClosed 直接删 | F1→§4.1.3 词表;F2→§4.1.3+§2.2 overlay 族边界;F3→§4.3.3 映射表;F4→§4.2 验证式例外(回写 dd-011);F5→§2.2 判定序 + 批 C 不重写判定链声明;F6→§4.3.1 逐动作回流程层;F7→§4.2 OpenShopOp 幂等条款;F8→§5 批 D 占位;F9→§4.1.3(EnsureShopClosed 过渡期)+ §3 批 C 退役 |
| 代码现实(11 条) | F1 obs_shop 融合态(P0)/F2 SellBench(P0,与流程视角互证)/F3 重估五项输入/F4 EnsureShopClosed=探针挂点/F5 源码字符串锁成片/F6 EnsureShopOpen=腾席链 b 读数步/F7 buy 三段隐含步骤(席满急救/overlay 守卫/观测网)/F8 遥测安灯写点/F9 画面判定序/F10 LOCKED_RESUME/F11 刷新期望惰性 import+两阶段循环 | F1→§4.1.2 组装契约;F2→§4.1.3;F3→§4.3.4 输入契约表;F4→§3/§4.3.5 挂点随迁;F5→§5 批 A 锁迁移清单前置+验证口径裁决;F6→§3/§4.3.6 read_only 变体;F7→§3 席满急救上移/§4.2 overlay 守卫归流程层/批 A 观测网清单;F8→§4.3.4+§6 安灯漏停防线;F9→§2.2 判定序;F10→§3 批 A 删除;F11→§4.3.2 循环编排 |
| 架构一致性(10 条) | F1 decide_prep/decide_prep_action 张冠李戴(P0)/F2 商店词表漏卖族(SellBench/SellDeployed/CompTransaction)/F3 备战词表不全+控制流豁免+RunDeploy/RunEquip 归属/F4 OpenShop 语义过载击穿 M-6 门/F5 D 牌两阶段重判环归属/F6 读数时序契约缺位/F7 判稳轮询与 DD-011 原文冲突/F8 终止语义两义+商店会话状态归属/F9 批 A 对拍机制障碍/F10 LevelUp 双态消歧 | F1→§0 勘误表(全文档映射修正);F2/F3→§4.1.3 词表补全;F4→§4.3.6 read_only 变体;F5→§4.3.2;F6→§4.3.5 读数时序契约;F7→**待用户裁决项**(建议:修订 DD-011 增「画面身份确认轮询」豁免——判稳标志是用户口述知识非指纹测量;备选:改固定 success_wait);F8→§4.1.4 空序列单一定义 + §4.3.4 会话归属;F9→§5 批 A 验证口径裁决(方案 b);F10→§4.1.3 LevelUpShop |

**待用户裁决项(1 项)**:F7 架构——判稳轮询与 DD-011「不设第二道稳定验证」字面冲突。建议方案①:修订 DD-011,区分「固定时长自等」与「画面身份确认轮询」(后者按用户口述判稳标志判定**操作是否生效**,非指纹测量);方案②:OpenShopOp 改固定 1.0s 等待+落空 retry 兜底。
