# W971 · CW 流程层重构设计(总纲)

- 日期:2026-09-02;状态:**FINAL(收敛,可实施)**——对抗轮 1(三视角 41 findings + 时序终检 5 项)全部处置;复核轮 1 修订验证通过;复核轮 2 F-1~F-4 清毕,收敛确认。待实机项已挂账(自动战斗检测/暗态帧补采/投资环境仅开局/接管局简报/位面页序)
- 实施进度:P2(决策接口+黑板)完成——`decide_prep_screen`/`decide_shop_screen` 落地(§2 黑板;观察写 session:prep_obs_frame/shop_state_frame,写者白名单落 02-state §4.1;ctx 信箱双写过渡未删,对抗轮 1 P0 口径);match 建立前移(§2.1,establish_new_match);LevelUpShop 拆分;决策层豁免清点(02-state §4.2)——dd-014;**P3 完成(P3a 建 cw_flow 包 + P3b 接线,dd-017)**——开局编排接线(0a0b 位面简报/位面过渡内联/开局投资环境段三段退役,接管局首帧分流 §2.1)、七 overlay op 分发接管(干扰弹窗分支保留)、ctx 信箱退役(BriefingOp 内联直写 session)、纯分发器接管备战/商店常态编排(W970 批 C 全项,见该文实施进度);P4 完成(战斗等待 op + 期望态 infra);**P5 进行中**——ctx 信箱字段(`cw_briefing_affixes`/`cw_briefing_bosses`/`cw_enemy_difficulty`)物理删除(读写点已随 P3b/P4 全量退役);gate 模块清点完成:多处活消费(prep_director/run_node/prep 两 op/cw_observation/_overlay_confirm),**保留不删**,剩余消费面清尾随批 D 另文
- 依据:用户口述架构愿景(2026-09-02,逐段,§2 各节)+ W970(画面分层架构,FINAL+amended)——本篇是 W970 续篇:W970 治「商店链与决策接口」,本篇治「流程层编排与局状态」
- 结构:总-分。本篇 = 总纲(背景/决策索引/总图/迁移/风险/边界);分篇按画面域:
  - [01-opening.md](01-opening.md) — 简报 op / 开局序列 / 位面切换(§2.2/2.3/2.3.1)
  - [02-state.md](02-state.md) — 局状态收编 / 黑板模式 / 字段生命周期 / 白名单(§2.1/2.7/2.7.1/§4)
  - [03-prep.md](03-prep.md) — 备战循环 / 干净备战 op / 20 项识别清单 / 原子 op(§2.6/2.6.1)
  - [04-shop.md](04-shop.md) — 商店开画面 / 投资策略 / 再选调研 / 暗态备选(§2.8/2.12)
  - [05-battle.md](05-battle.md) — 战斗等待 op / 自动战斗检测 / 点空白加速 / 整局退出(§2.10/2.11/2.17)
  - [06-overlays.md](06-overlays.md) — 补给 / 遭遇 / BOSS 简报 / 剩余 overlay 族(§2.13/2.14/2.15/2.16)

## 1. 背景与动机(用户口述 + 现状病灶)

口述要点:①入口前固定时长;②简报画面做**第一次数据观察(单独 op)**,数据进**统一内存状态**(贯穿整局,多 op 更新,遥测/对账消费);③简报后到 1-1 是**固定流程,每画面独立 op**;④1-1 前整段拉出主循环;⑤循环内**去掉稳定门**,识别到什么画面就进对应 op;⑥决策统一读 session(黑板);⑦op 原子化,完成承诺两形态(DD-011 amended)。

现状病灶(亲读实证):
- **局状态不正式**:事实载体 StrategySession,但简报数据绕「ctx 信箱」(入口存 ctx → battle_loop 取走拷贝),无更新者白名单;
- **简报观察三个写入点**(入口/0a0b/位面详情兜底);
- **开局流程一半 op 化一半内联**(位面过渡/开局补给/位面简报内联;投资环境等已有 handler);
- **结算链内联**(分支 1f/2/3 读点+点击,自动开店判稳用标志位跨分支传递)。

## 2. 已确认决策索引(详情见分篇)

| 决策 | 分篇 | 一句话 |
|---|---|---|
| 局状态收编 StrategySession | 02-state | 不新立对象;消灭 ctx 信箱;写者白名单;遥测/对账统一读路径 |
| 黑板模式(决策统一读 session) | 02-state | `decide_prep_screen(session, config)`;取消 obs 组装;可信位复用 |
| 字段生命周期三分类 | 02-state | 持久知识 / 画面态(离开画面清理) / 新鲜快照 |
| BriefingOp 简报观察收敛 | 01-opening | 三个写入点收敛为单 op(观察→写 session→点下一步) |
| 开局序列独立于 loop | 01-opening | BriefingOp→位面过渡→投资环境→WaitOneOneOp(~10s)→1-1 |
| 位面 2/3 切换 | 01-opening | 同款 op 复用,编排挂结算后;无投资环境 |
| 备战循环 + 稳定门退役 | 03-prep | 识别到什么进什么 op;防护=逐动作确认+触发计算式等待 |
| 干净备战 op(20 项识别) | 03-prep | 观察写 session → decide_prep_screen → 逐动作原子 op |
| 流程信号意图退役 | 03-prep | DeferSpheres/BailToOuter 删(交回是默认行为;空序列合法;stall 归状态对账) |
| 商店画面收缩 | 04-shop | 动作集只剩 BuyCard/RefreshShop;整理类全移备战;CompTransaction 废弃 |
| 投资策略流程 | 04-shop | 路 2 结算屏读数采纳(暗态备选保留);原子 op 3 个;完成承诺 = 商店开 ∪ 再选 overlay 双候选+上界兜底 |
| 再选效果调研 | 04-shop | 417 条全查命中 8 张;A 立即再选=循环天然处理;B 延迟再选=日程账本 |
| 遭遇 overlay | 06-overlays | 决策读难度预览(词缀是全局);确认后回备战+商店自动开 |
| 补给 overlay | 06-overlays | 与投资策略同构;决策域=宝钻+契合;决策归策略接口原则 |
| 战斗等待 op | 05-battle | 三段式;完成判据白名单;点空白加速;采集段随迁 |
| 自动战斗检测 | 05-battle | 项目共用;特征=「我方行动中」;待实机采集 |
| overlay 完成承诺两口径 | 06-overlays | 节点后四类=等商店开画面;备战触发七类=固定 1.0s 回干净备战 |
| 整局退出 | 05-battle | ExitCurrencyWarMatch 复用,固定时长 |

## 3. 目标架构总图

```
进对局(StartCurrencyWarMatch)
  │
  ├─ 开局编排(独立于主循环,01-opening):
  │    BriefingOp(观察→写session→点下一步)
  │      → PlaneTransitionOp(点空白)
  │      → InvestEnvOp(3选1,含刷新)
  │      → WaitOneOneOp(~10s,1-1 不自动开店特例)
  │      → 1-1 备战就绪
  │
  ├─ 顶层循环(纯分发器;判定序:沿用现役优先序框架+W971 扩锚,暗色锁定态→商店开锚→备战双锚→…):
  │    识别画面 → 分发:
  │    ├ 备战 → 干净备战op:观察20项写session → decide_prep_screen(session)
  │    │         → 逐动作原子op(部署/卖/点球/开箱/典籍/OpenShop[read_only]/出战)
  │    ├ 商店开 → 商店op:读牌面 → decide_shop_screen(session)
  │    │         → BuyCard/RefreshShop 波循环 → 空序列 → CloseShopOp(含字段清理)
  │    ├ overlay → 对应 overlay op(06-overlays:投资策略/补给/遭遇/巨星/列车同行/
  │    │            武装箱/祈愿/策划/命运/秘典)
  │    ├ 战斗/结算 → 战斗等待op(05-battle:等结算→读数→点继续→白名单判据)
  │    (过渡帧点空白内嵌战斗等待 op,不设独立分发分支——对抗轮 1 修正误点风险)
  │
  └─ 整局退出(05-battle):ExitCurrencyWarMatch 复用,固定时长
```

## 4. 局状态字段 × 更新者白名单(详见 02-state.md)

生命周期三分类:持久知识 / 画面态 / 新鲜快照。主字段族写路径:

| 字段族 | 写者(白名单) | 清理 | 主读者 |
|---|---|---|---|
| briefing_affixes / briefing_bosses / enemy_difficulty | **BriefingOp**(位面详情兜底=其重试形态) | 局终 | decide_encounter / 难度账 / 遥测 |
| gold | 备战观察 / 商店观察 / 战斗等待op(结算屏) | 每轮覆写 | 全部决策 / 遥测 / 台账 |
| hp(+readable/trusted/last_hp_t) | 备战观察(关帧)/ 战斗等待op(结算屏) | 每轮覆写+新鲜度门 | 两画面决策 |
| level / xp / level_up_cost | 备战观察 | 每轮覆写 | 升级决策 / 台账 |
| board(羁绊计数) | 备战观察(徽标;暗态不读) | 每轮覆写 | decide_prep_screen / DeployMove 触发计算 |
| bench / deployed / tracked_bench_chars | 备战观察(SIFT)/ 动作登记 | 每轮覆写+累积 | decide_shop_screen(sell_guard) / 部署 |
| shop_cards / 刷新花费 | 商店观察 | **CloseShopOp 完成承诺清理** | decide_shop_screen |
| refresh_probs | 商店观察 | 不清理(等级函数) | decide_shop_screen / 经济账 |
| node_type / 节点台账 | 节点探针(CloseShopOp 后,类型分派)/ 备战观察 | 位面切换覆写 | 节点分发 / boss 判定 / 难度账 |
| 投资日程账本(新增) | 投资策略op(选卡登记) | 局终 | 流程层日程调度 |
| 难度账/marginal_value 输入 | decide_encounter / 战果记录 | 局终 | decide_encounter |

纪律:新增写入点 = 违反白名单;ctx 信箱字段(cw_briefing_*)随 BriefingOp 落地删除。

## 5. 迁移路线

**W970 批次映射**:批 A→P1、批 B→P2、批 C→P3(编排切换+随迁全项)、批 D→P5;对抗轮 1 修正批次断层。
| 阶段 | 内容(吸收 W970 批次) | 验证口径 |
|---|---|---|
| P1 商店链原子化(=W970批A) | OpenShopOp/BuyCardsOp/CloseShopOp 拆分(源码锁迁移清单前置);遥测写点随迁;LOCKED_RESUME 删 | 锁按清单更新后绿 + decisions.jsonl 逐决策对拍 + 全量测试 |
| P2 决策接口+黑板(=W970批B+黑板) | decide_prep_screen/decide_shop_screen(session 签名);观察写路径收编(ctx 信箱双写过渡,P3 删——对抗轮 1 批次修正);LevelUpShop 拆分 | 新旧入口决策对拍 + 白名单落地检查 |
| P3 开局序列+overlay族+**编排切换**(=W970批C 全项) | BriefingOp/PlaneTransitionOp/WaitOneOneOp 新建;七 overlay op 统一模式;开局编排接线(主循环瘦身:0a0b/分支6/投资环境段退役);**纯分发器接管备战/商店常态编排(W970 批 C 全项:RunBuyPhase 解体、腾席链 b read_only、探针挂点、_handle_bench_full 合流)**;干扰弹窗分支保留 | 实机单局:开局序列走查 + overlay 各触发一次 + 常态编排对照 |
| P4 战斗段+结算链 | 战斗等待op(结算读点随迁,遥测红线);点空白加速随迁;自动战斗检测(待采集);节点探针挂点随迁 | 实机多局:遥测连续性对照(decisions.jsonl/match_archive)+ rounds 遥测 |
| P5 收尾 | PREP_SETTLE_S 退役;标志位退役;EnsureShop 意图删除;gate 模块删除(清单清零) | 全量测试 + 实机对照 |

每阶段:`ruff` + 受影响测试 + 全量 CW 测试;commit 前三同步(ADR/AS-BUILT/注释)。

## 6. 风险与防线

| 风险 | 防线 |
|---|---|
| 结算链迁移打断遥测(decisions.jsonl/match_archive) | P4 红线:读点随迁清单 + 实机遥测连续性对照 |
| 暗态/画面态识别错数据进 session | 字段可信位 + ADR-0417「暗态不裁不覆」(身份/徽标暗态不读) |
| 黑板模式脏读(陈旧字段) | 生命周期三分类 + CloseShopOp 式清理者白名单 |
| 链式选择(8 张再选卡)漏处理 | 顶层循环重识别天然分发;日程账本管延迟再选 |
| 白名单外写入回流 | code review 按 §4 表;违例 = obs_conflict 留证 |
| 判稳标志选错(共用元素) | 独有锚纪律(DD-011 amended)+ 判据白名单集中定义 |

## 7. 边界

- battle_loop 结算分支**遥测读点重组细节**归 P4 实施设计(本篇只定归属与红线)。
- sim 适配独立批(**已完成**:引擎决策环 engine_p1/回放 harness cw_replay/检查器 checks.decision_v2 全部切黑板接口 `decide_shop_screen`(帧写者 = sim 引擎,写者白名单见 02-state §4.1);升级意图经商店屏词表 LevelUpShop(is-a LevelUp,执行链零改动);期望态离线口径 = session.expected_state 显式空 dict + ShopCard.cost_source 缺省 'roster'(不依赖实机识别);旧 decide_prep 薄委托仅存迁移期兼容,离线主路径不再依赖)。
- 观察模块内部重构不做(只改调用时机与写路径归属)。
- RunDeploy/RunEquip 内部原子化另立批次。
- gate 模块删除(W970 批 D/本篇 P5)另文。

## 8. 对抗与修订记录

### 对抗轮 1(2026-09-02,三视角 41 条:4 P0 / 19 P1 / 18 P2,全部处置)
- P0×4:战斗等待白名单补位面简报锚(后经用户裁决移除,见下) / 接管局入口规格(01-opening §2.1) / 团灭终局分叉第三出口(05-battle) / ctx 信箱删除批次修正(P2 双写过渡 P3 删)
- P1 集中:迁移路线断层(P3 纳入 W970 批 C 全项+映射表) / 完成承诺收敛(到达判定 vs 面板就位分离) / 场景①判稳锚统一「按钮-收起」(dd-011 勘误) / 白名单宿主+决策层豁免类目 / W970 §4.1.3 词表 amendment / match 建立前移 / reconcile 双输入 / stall 规格最小集 / LevelUpShop 行 / M39 长按与 #25 读点时序 / 刷新次数随卡变 / 干扰弹窗族保留 / 词缀效果采集职责随迁
- 时序终检:24/29 闭合;5 项修订(循环分发式/接管中间态/等待上界兜底/#23 时序/暗色锁定态归属)

- 对抗轮 1:三视角并行(架构一致性/代码现实/玩法流程覆盖)= 41 findings + 时序终检 5 项,全部处置(见下)。
