# 货币战争 流程控制设计（flow/ · 唯一现行家）

> 本目录是货币战争（CW）**流程控制的唯一现行设计家**，由流程层代码反向规格化而成（本批为纯文档，零代码改动）。原 `strategy-docs/09_architecture.md`（契约/插件/管理器/注册壳/三臂）已删除，其内容全部收编入本 README §2。
> 职责分界（用户裁定）：**策略文档（`../strategy-docs/`）只管"每个画面结合哪些数学证明、怎么产出决策"；流程控制单独立文档（本目录）**——画面识别与路由、访问相位推进、动作发射契约、守卫与停机。
> 读者 = 无会话历史的工程师/智能体。术语首次出现给定义。引用格式 = `文件:行号`（路径根 = `src/sr_od/application/currency_war/`）。
> **⚠️ 波批形态 = 待迁移态（单处声明，不逐篇重复）**：本目录各篇描述的商店决策「波批形态」（一次观察算整波动作、截断器、波级契约）已被 [ADR-0517](../decisions/0517-single-action-screen-op.md)（画面 op 单动作循环，proposed）裁定为目标架构的**替换对象**——目标态规格见 [screen_op.md](screen_op.md)，实现未动，各篇 as-built 描述加「待 ADR-0517 迁移」标注处即迁移面。

## 1. 四层结构总图

```
┌─ 外层循环（cw_loop.py）────────────────────────────────────────┐
│ 画面识别 → 分支路由（overlay 0x 系 → 备战 1 → 战斗窗 → 大厅 3c）│
│ 轮次推进（备战环 → 出战 → 战斗等待 → 结算 → 回备战）            │
│ 停机/遥测钩子（守卫、runs summary、分配器、对局存档）           │
├─ 画面指挥（cw_screen_prep.py = 备战单轮五段）─────────────────┤
│ ①观察(heavy/light) ②对账 ③决策调接口 ④期望态计算 ⑤执行+结束判定 │
│ 商店编排（_open_shop_phase：开店→波循环→关店→finalize→节点探针）│
├─ 策略步进（mandate_v1：bridge.py 决策入口 + entry.py 三遍编排）┤
│ 备战决策 live 链 = bridge.decide_prep_screen → decide_from_turn   │
│   → entry.emit（①prep实体面→②证明→③升档器→④骨架M1-M7→⑤EV→       │
│   ⑥无动作⇒StartBattle，自有动作词表）；flow.py 旧备战骨架         │
│   （相位机/腾席链）= 死码待收敛（prep_visit.md §2.1）；            │
│   pick 族 9 钩子与生命周期钩子仍由 flow.py 中间 ABC 承载          │
├─ 动作执行（kernel/cw_prep_actions.py 词表 + prep_actions.py 执行器│
│ + cw_op_buy_cards.py 商店波 + cw_op_deploy.py 部署）───────────┤
│ 三态发射契约（NOOP/失败/成功可区分）、重试/恢复原语、观测复查   │
└────────────────────────────────────────────────────────────────┘
```

分层判据：**外层循环管"现在是哪个画面、交给谁"；画面指挥管"一次访问内观察→决策→执行的编排"；策略步进管"给一帧观察出什么动作序列"（骨架 + 委托 mandate_v1 判据）；动作执行管"一个动作怎么落地、怎么验证"**。策略判据（买/卖/升/刷的数学）一律不在本目录，见 `../strategy-docs/11_shop_decisions.md` 等篇。

## 2. 策略↔流程契约（吸收原 strategy-docs/09_architecture.md）

> 原 09 篇已删除，其四身份分离与 17 接口内容收编于本节。判据语义的归属篇同步改指 strategy-docs 新编号。

### 2.1 四身份分离

| 身份 | 载体 | 职责 | 禁止 |
|---|---|---|---|
| **契约** | `strategies/impl/cw_strategy.py` 的 `CwStrategy` ABC（17 钩子，全 abstract） | 定义策略器与流程侧之间的全部接口（§2.2） | ABC 自身零内置逻辑（纯接口；`cw_strategy.py:59-72`） |
| **管理器** | `strategies/impl/cw_strategy_manager.py`（StrategyManager） | 按 config.strategy_id 实例化/选择策略；值域 = {decision_v2, mandate_v1} | 不承载判据；不知策略内部结构 |
| **实现** | `strategies/impl/mandate_v1/`（单一核）+ `strategies/impl/decision_v2/`（A/B 冻结基线）+ `strategies/impl/flow.py`（`CwFlowStrategy` 中间辅助 ABC：生命周期/意向/pick 族/备战骨架，`_abstract=True` 不注册，`flow.py:121-135`） | 决策本体 | 禁自实现生命周期机制（幂等键/连败恢复/屏蔽/stall 门——归流程侧）；禁绕契约自造接口 |
| **注册壳** | `strategies/mandate_v1_strategy.py`（MandateV1Live） | 把实现包注册进策略扫描器 | 壳内零判据逻辑 |

### 2.2 17 接口（钩子全景；`cw_strategy.py:85-205` + `flow.py`）

**生命周期 4**（实现 = `flow.py`）：

| 钩子 | 调用时机（流程侧） | 语义 |
|---|---|---|
| `create_session(config)` | 每局开始一次 | 返回空白 StrategySession（rng 由 run loop 按 config.strategy_seed 覆写；`flow.py:237-239`） |
| `on_match_start(state, session, config)` | 外循环 iter1 新局首截图后（`cw_loop.py:661-679`） | 意向/演进/报警/轮键跨局清零（`flow.py:139-201`） |
| `on_round_end(state, session, config, obs)` | 每场战斗结算观测后 | performance 记录 + streak/HP 真值喂入 + 谷底回滚判（`flow.py:203-235`；HP 仅过 `gated_hp` 新鲜度门进 session，`cw_strategy.py:263-287`） |
| `on_match_end(session, config, outcome)` | 回大厅收口（`cw_loop.py:1433-1434`） | no-op（P1；`flow.py:241-243`） |

**战略 1**：`update_target(state, session, config)`——意向状态机驱动 + P1 配方对物化，写 `session.target_comp`。调用点 = 每个备战回合 `decide_shop_screen` 之前（备战单轮观察段，`cw_screen_prep.py:1271`；商店波首波，`cw_op_buy_cards.py:509`；买后重估，`cw_screen_prep.py:2066`）。决策语义 = `../strategy-docs/12_line_and_intention.md`。

**序列决策 3**：

| 钩子 | 输入（黑板） | 返回 | 三态语义 |
|---|---|---|---|
| `decide_prep_screen(session, config)` | `session.prep_obs_frame`（备战观察帧；写者 = CwScreenPrep 观察段/破墙派生帧，`cw_screen_prep.py:641-648`） | `list[PrepAction]`，执行序 = 列表序 | 空序列合法 = 本帧无动作（交回外循环重观察；`cw_screen_prep.py:1291-1295`）；**观察帧缺失即抛错**（禁静默按空观察决策） |
| `decide_shop_screen(session, config)` | `session.shop_state_frame`（商店融合观察态；写者 = 商店波循环顶融合段，`cw_op_buy_cards.py:569`） | `list[Action]`（词表 = BuyCard/LevelUpShop/RefreshShop/SellBench/SellDeployed/CompTransaction） | **空序列 = 决策完成触发关店**（`cw_screen_prep.py:_open_shop_phase` 波循环 + `cw_op_buy_cards.py:1069` 收工） |
| `decide_prep_action(obs, session, config)` | 旧单动作签名 | deprecated 兼容薄委托：写黑板 → 委托序列核（基类 `flow.py:491-499` 直传完整 list；live 覆写 `mandate_v1/bridge.py:110-122` 解包首元素、空批→DeferSpheres；调用方迁移完随 P5 删除） |

**序列语义（冻结条款，反向自 `cw_strategy.py:134-161` 与 `cw_screen_prep.py:1296-1398`）**【待 ADR-0517 迁移：本小节序列契约（整波返回/帧稳定域/截断/空批终止）是波批形态的流程侧表述，目标态由终结 op 与单动作循环取代，见 [screen_op.md](screen_op.md) §3；迁移前以本节 as-built 为准】：
- **帧稳定域**：序列内第 i+1 个动作不得依赖第 i 个动作执行后的新观察；发射时逐动作判"执行后画面状态能否静态推出"，推不出即截断。流程侧保守口径 = 每动作落地后 heavy 重观察再续发（`cw_screen_prep.py:1297-1301`）；OpenShop/StartBattle 作序列终点。
- **fail-stop**：任一动作未落地 → 丢弃余下动作 → 恢复原语（关已知弹层，`prep_actions.try_recovery`）→ 交回外循环 heavy 重观察重调接口（`cw_screen_prep.py:1382-1393`）。参数非法（F3 拒绝）与执行失败同型。
- **逐动作验证保留**：期望态对账/执行验证照跑，不依赖重决策（`cw_screen_prep.py:1376-1378`）。
- **控制流走词表内特殊动作**（DeferSpheres 族；defer 计数归框架，`cw_screen_prep.py:1307-1312`）；策略器禁用空批表达控制流。
- **生命周期机制归流程侧**：幂等键 `action_key`、连败→恢复→屏蔽、stall 门、强制出战。

**pick 族 9**（选项决策；动作编排归画面 op，不进序列契约辖内；`flow.py:298-487`）：
`decide_invest`（E1/E2 投资三选一）、`decide_supply`（E4 补给）、`decide_encounter`（E3 遭遇）、`decide_megastar`（E7 巨星）、`decide_partner`（E6 伙伴/领航员）、`decide_planner`（银狼策划）、`decide_star_tome`（星徽典籍四选一）、`decide_wish_trial`（圣杯试炼二选一）、`decide_box_card`（武装箱选卡）。返回 PickEvent 系载体。决策规格 = `../strategy-docs/13_pick_family.md`。

共 4+1+3+9 = 17。新事件面优先归并进既有 pick 钩子或走契约改版，禁旁路自造接口。

### 2.3 装配与依赖矩阵（吸收原 09 §4）

- **依赖方向**：实现包 → 知识层/数学层/执行层单向；分包依赖矩阵禁 decision→obs 直依（obs 读口经 app 桶装配点 `install_obs_ports()` 注入）；决策本体 = 纯函数（bridge.decide_from_turn），装配链由注册桥壳覆写注入（app 桶）。
- **装配点**：obs→Snapshot 装配半部在 app 桶（decision_assembly）；黑板单一写端纪律保持；`_RESET_PHASE_ROUND_CACHE` 注入槽（缺省关）+ `discard_stale_match_container`（异常路径残留容器弃置，ADR-0419——session 全量重建 by construction）。
- **gated_hp**（结算 HP 新鲜度门，r68/r69 单源 helper）：结算真值仅在可信窗口内覆盖现读——观测质量门，非决策输入（`../strategy-docs/04_survival_budget.md` §7 表 #6）。
- **sim 消费面注记**：sim 仅消费 update_target + decide_shop_screen——sim A/B 的证明面 = 商店波经济决策；prep 屏编排域在 sim 无实体真值源，其正确性防线 = 契约锁 + 适配器零漂移门 + 实机，不在 sim A/B 辖内。

### 2.4 三臂 A/B 与换核时序（吸收原 09 §5）

- **三臂结构**（判前锁 v6 口径）：单被测体两因子 strategy_id∈{decision_v2, mandate_v1} × ev_arm∈{skeleton_only, full}；三臂 = ①mandate_v1/skeleton_only ②mandate_v1/full ③decision_v2 基线。预指定主对照 = ②−①（EV 增量，命题 B）；次对照 ①−③（命题 A 非劣参照，仅描述性）。命题 A/B 判据骨架 = `../strategy-docs/02_mandate_layer.md` §8。
- **归因域限定**：sim 引擎唯一决策入口 = decide_shop_screen ⇒ 归因域 = shop 决策面（prep 面 sim 不可达），结论不得外推为全决策面处理效应。
- **判读硬前置**（判前锁 v6 检查单）：任一行未落地 ⇒ 正式 A/B 被 raise 拦死（排程层防零刷新事故复发）；强制披露清单（fail-closed 关闭面的拒因计数——U_X/T_SEARCH_A 豁免 ⇒ EV 买/压库/凑息卖/换线塌缩五面两臂恒等关闭，headline 必须随附该降级分量）。
- **遥测分栈**：DecisionTrace 按 (strategy_id, ev_arm) 二元组分栈；mandate 标记维度区分骨架/EV 动作。
- **换核机制** = config 切 strategy_id（最小面），不改流程侧分发；单一核 = mandate_v1（cw4 分层包），decision_v2 为声明的 A/B 基线臂（A/B 过线 = 整体删除旧决策包的触发门，dd-001 时序裁决）。

### 2.5 无状态策略与 session

策略实例不持有可变每局状态（`cw_strategy.py:60-72`）；跨步状态走 `StrategySession`（框架每局新建、局终销毁）。异常路径残留容器由 `discard_stale_match_container` 在"确凿新局"信号点丢弃（`cw_strategy.py:232-260`）。obs 读口注入槽 `_RESET_PHASE_ROUND_CACHE` 缺省关（`cw_strategy.py:223-229`）。

## 3. 各篇导读

| 篇 | 一句话 |
|---|---|
| [outer_loop.md](outer_loop.md) | 外层循环：画面识别分支序、路由、轮次推进、停机/遥测钩子 |
| [screen_op.md](screen_op.md) | **画面 op 统一规范（ADR-0517 目标态，as-designed 未落码）**：单动作决策循环、动作基类 execute+project、终结 op 集、期望态生命周期、复合动作类、观测通道归属、开放问题裁决建议 |
| [prep_visit.md](prep_visit.md) | 备战访问：单轮五段、备战决策 live 链（mandate_v1）与死码旧骨架标注、腾席链（死码）、完成判定与交还外循环 |
| [shop_visit.md](shop_visit.md) | 商店访问：波循环、读序、执行至首个刷新、离店条件与收尾 |
| [action_exec.md](action_exec.md) | 复合动作执行：词表、发射契约三态、重试/恢复语义、观测复查 |
| [guards.md](guards.md) | 守卫总册：G3 环级无进展守卫、停滞/未知/失活防线、降级链、fail-closed 行为 |

## 4. 守卫总览（细则 = guards.md）

| 守卫 | 触发 | 动作 | 载体 |
|---|---|---|---|
| 环级无进展守卫（G3） | 连续 3 个备战环"同签名动作批 ∧ 状态零推进" | 截图+flag 存证 → stop_running | `cw_loop.py:1077-1126` |
| 停滞 watchdog | 同屏 OCR 指纹连续 6 次采样相同（非战斗态） | 哨兵 flag+日志，**不停机** | `cw_loop.py:434-495` |
| 未知画面兜底 | 连续 15 轮全分支不命中（指数退避封顶 10s） | 停机保画面待建档 | `cw_loop.py:1518-1560` |
| 策略失活早停 | 连续 2 个完整轮无策略心跳决策行 | 停局重启加载策略 | `cw_loop.py:1142-1179` |
| 执行失败安灯 | 购买单元"计划花费>0 金差≈0"（分类器三态） | 停机留现场 flag | `cw_screen_prep.py:1642-1712` |
| 商店未识别卡停机 | 防抖重读 2 帧后仍有未识别槽 | 停机保画面待建档 | `cw_op_buy_cards.py:1072-1135` |
| 误分发/恢复链限额 | 位面过渡连败 3 / 前台无角色重部署 2 / director 连败 5 | round_fail 交兜底链 | `cw_loop.py:200-208,927-976,1306-1315` |

## 5. 宪法四条对流程层的适用口径

流程层反向规格化同样过宪法四条（`../strategy-docs/00_framework.md` §1）。流程层的主辖域是编排与守卫，本无策略判据；但反向平移中发现下列**现状违例**（详见各篇 ⚠️ 标记）：

1. **位面字面门**：`flow.py:275`（`state.plane == 1` 辖域）、`flow.py:542`（`round_num >= 9` boss 先验）——修正方向：段索引/节点数一律由节点日程（`cw_plane_table.schedule_of`）派生查表，位面只作查表键。
2. **hp 越权消费**：谷底回滚 `VALLEY_ROLLBACK_LOSS=15`（`flow.py:118,224-234`）——hp 掉量作质量信号触发回滚动作，不在 hp 授权对账表（`../strategy-docs/04_survival_budget.md` §7）；**已裁定退役（2026-09-04 用户裁定：未经数学证明即退役；04 §7 #7）**，代码删除随迁移后批次。
3. **无标数字**：`VALLEY_ROLLBACK_LOSS=15` 无三形态标注；随第 2 项退役一并消失。
