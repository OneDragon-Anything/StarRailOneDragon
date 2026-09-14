# 货币战争 流程控制设计（flow/ · 唯一现行家）

> 本目录是货币战争（CW）**流程控制的唯一现行设计家**，由流程层代码反向规格化而成（本批为纯文档，零代码改动）。原 `strategy-docs/09_architecture.md`（契约/插件/管理器/注册壳/三臂）已删除，其内容全部收编入本 README §2。
> 职责分界（用户裁定）：**策略文档（`../strategy-docs/`）只管"每个画面结合哪些数学证明、怎么产出决策"；流程控制单独立文档（本目录）**——画面识别与路由、访问相位推进、动作发射契约、守卫与停机。
> 读者 = 无会话历史的工程师/智能体。术语首次出现给定义。代码定位一律用符号锚 `文件::符号名`（loop 内语义段用 `文件::CwLoop.loop(段名)` 形态）——行号随代码增长漂移，不作定位依据；路径根 = `src/sr_od/application/currency_war/`。
> **单动作循环架构 = 已迁移（设计定案并实施,2026-09-06 落码）**：商店决策波批形态（一次观察算整波动作、截断器、波级契约）已被单动作循环（入口观察→逐动作决策循环→终结 op）替换;备战 per-action heavy 重读契约已灭（入口单次 + 逐动作投影 + 未建模面保守回退）;旧备战骨架死码（flow.py 10 方法 + kernel/cw_deploy_seat + prep_phase 族 session 字段）已物理删除。目标态规格 = [screen_op.md](screen_op.md)（as-designed 与 as-built 对齐维护）;各篇 as-built 描述即为现行实现。波批时代的 §2.2 序列契约保留为历史注（见该节）。

## 1. 四层结构总图

```
┌─ 外层循环（cw_loop.py）────────────────────────────────────────┐
│ 画面识别 → 分支路由（overlay 0x 系 → 备战 1 → 战斗窗 → 大厅 3c）│
│ 轮次推进（备战环 → 出战 → 战斗等待 → 结算 → 回备战）            │
│ 停机/遥测钩子（守卫、runs summary、分配器、对局存档）           │
├─ 画面指挥（cw_screen_prep.py = 备战单轮：入口 heavy 观察+对账+单动作决策循环）─────────────────┤
│ ①入口观察(heavy) ②对账(暂存记账入口消费) ③-⑤单动作循环:决策取 │
 │ 首项→期望态计算→执行→投影(零读屏);终结 op 交回外循环            │
│ 商店编排（_open_shop_phase：开店→单动作循环→关店→finalize→节点探针）│
├─ 策略步进（mandate_v1：bridge.py 决策入口 + entry.py 三遍编排）┤
│ 备战决策 live 链 = bridge.decide_prep_screen → decide_from_turn   │
│   → entry.emit（①prep实体面→②证明→③升档器→④骨架M1-M7→⑤EV→       │
│   ⑥无动作⇒StartBattle，自有动作词表,单动作循环逐帧取首项）;商店决策│
│   = decide_shop_action 单动作接口;flow.py 旧备战骨架 │
│   （相位机/腾席链等 10 方法+session 字段）已删（prep_visit.md §2.1）│
│   pick 族 9 接口与冷建/结算收编仍由 flow.py 中间 ABC 承载│
├─ 动作执行（kernel/cw_prep_actions.py 词表 + prep_actions.py 执行器│
│ + cw_screen_buy_cards.py 循环壳 + cw_shop_actions.py 商店动作工厂  │
 │ (cw_<action>_action.py 一 op 一文件;守卫 cw_shop_action_ops.py)  │
 │ (execute 单方法) + cw_op_deploy.py 部署）────────────────────┤
│ 三态发射契约（NOOP/失败/成功可区分）、动作机械发出+until 转移   │
│ 验证+执行侧守卫面、恢复原语、观测复查                          │
└────────────────────────────────────────────────────────────────┘
```

分层判据：**外层循环管"现在是哪个画面、交给谁"；画面指挥管"一次访问内观察→决策→执行的编排"；策略步进管"给一帧期望态提什么动作"（骨架 + 委托 mandate_v1 判据,单动作选择序）；动作执行管"一个动作怎么落地、怎么验证"**。策略判据（买/卖/升/刷的数学）一律不在本目录，见 `../strategy-docs/11_shop_decisions.md` 等篇。

## 2. 策略↔流程契约(吸收原 strategy-docs/09_architecture.md;意向层重塑拆分)

> 原 09 篇已删除,其四身份分离与接口内容收编于本节。判据语义的归属篇同步改指 strategy-docs 新编号。**契约形状**:ABC = 「每局冷建 2 + 分画面决策入口 11」抽象 12 + 非 abstract 工厂 create_state 1 = 保留总成员 13(独特方法面 20);方向重估节拍/生命周期事件等策略内部构造不在契约面。

### 2.1 四身份分离

| 身份 | 载体 | 职责 | 禁止 |
|---|---|---|---|
| **契约** | `strategies/impl/cw_strategy.py` 的 `CwStrategy` ABC(抽象 12 + 非 abstract 工厂 1;接口面见 §2.2) | 定义各画面 op 调用策略器的全部决策入口与唯一冷建口(§2.2) | ABC 自身零内置逻辑(纯接口,create_state 工厂除外);零策略专属语义(update_target/意向 target 机器/生命周期事件钩子已出契约面) |
| **管理器** | `strategies/impl/cw_strategy_manager.py`(StrategyManager) | 按实例化/选择策略;注册面封闭集 = {mandate_v1}(decision_v2 已随 commit b94e9cfb 删除) | 不承载判据;不知策略内部结构 |
| **实现** | `strategies/impl/mandate_v1/`(单一核)+ `strategies/impl/flow.py`(`CwFlowStrategy` 中间辅助 ABC:唯一冷建口/方向节拍内化刷新/pick 族/商店单动作接口与驱动器缺省,`_abstract=True` 不注册;旧备战骨架已删;结算策略半惰性 drain 三方法已删(T-64 退役批)) | 决策本体 | 禁自实现生命周期机制(幂等键/连败恢复/屏蔽/stall 门——归流程侧);禁绕契约自造接口 |
| **注册壳** | `strategies/mandate_v1_strategy.py`(MandateV1Live) | 把实现包注册进策略扫描器 | 壳内零判据逻辑 |

### 2.2 契约接口全景(形状;`cw_strategy.py` + `flow.py`)

**每局冷建 2**(实现 = `flow.py`):

| 接口 | 调用时机(流程侧) | 语义 |
|---|---|---|
| `create_session(config)` [abstract] | 每局开始一次(establish_new_match 进对局前移点/防御路径/回放三处同源) | 返回空白 StrategySession + 策略器状态工厂接线 + live 初值 v3_phase='FORM'——**唯一冷建口**(原 on_match_start 冷建与初值双写点收编) |
| `create_state(config)` [非 abstract 工厂] | 仅由 create_session 接线调用 | 每局冷建策略器状态对象(黑盒契约;缺省 None = 第三方 B4 条款) |

**分画面决策入口 11**(抽象;方向重估由各入口经黑板帧代次标注内化触发):

| 接口 | 输入(黑板) | 返回 | 语义 |
|---|---|---|---|
| `decide_prep_screen(session, config)` | `session.prep_obs_frame`(备战观察帧;写者 = CwScreenPrep 入口观察段/破墙派生帧/循环投影步) | `list[PrepAction]`,单动作循环取**首项**消费(逐帧取首项 = 单动作选择序) | 空序列合法 = 本帧无动作(交回外循环重观察);**观察帧缺失即抛错**(禁静默按空观察决策) |
| `decide_shop_action(session, config)` [本批升格入 ABC] | `session.shop_state_frame`(期望态;写者 = 入口观察段/单动作投影步/sim 引擎) | **恰一个动作**,「无动作可做」= `CloseShop` 恒可用终结;生产执行侧单动作循环逐帧调用(`run_buy_waves`),契约核验挂本入口 | 决策本体 = `mandate_v1/shop.py`;观察帧缺失即抛错 |
| `decide_invest/supply/encounter/megastar/partner/planner/star_tome/wish_trial/box_card`(pick 族 9) | overlay 观察实参 + session | PickEvent 系载体/索引 | 选项决策;动作编排归画面 op,不进序列契约辖内。决策规格 = `../strategy-docs/13_pick_family.md` |

**非契约成员(实现层,不在 ABC 面)**:

- `decide_shop_screen`(flow 层缺省驱动器 + bridge 覆写)——**序列兼容驱动器**:逐帧调 `decide_shop_action` + 容器投影直写推进期望态(`apply_shop_action_logic` 简单腿 + `apply_shop_merge_leg` 合成升星腿,买前快照三件组基点;T-163 起零 `cw_state.simulate` 前瞻消费),终结动作截停、CloseShop 收尾不入序列。sim 引擎/回放/既有序列锁消费;生产执行侧不走(单动作循环)。mandate 覆写保留特有记账(已买件/段序号/续段 token)。
- `_refresh_direction`/`_refresh_direction_views`(flow 层私有)——**方向节拍内化**:键守卫贵段(`update_intention` 状态机 + 候选评分遥测)每 game-round 恰一次 + 便宜派生视图段;触发信号 = 黑板帧代次标注(`session.prep_frame_class`/`shop_frame_class` ∈ full/view/none,写者 = 流程观察段具名写点,读者 = 决策入口,读后即清;驱动器不写帧类槽)。
- ~~`_drain_pending_round_outcomes`(flow 层私有)~~——**已删(T-64 退役批)**:结算策略半惰性加工(掉血三臂/node_type 回落/谷底回滚登记)经方案批复核为零行为死链(登记臂前置零写端/三臂零决策消费端),04_survival_budget §7 #7/#8 裁决落地删除;`session.pending_round_outcomes` 槽保留为观察半累积面。
- `write_shop_mirrors`(遥测镜像写者)。

注(生命周期):旧 `on_match_start/on_match_end` 删除(职责归 create_session 唯一冷建口/局终收口);旧 `on_round_end` 拆两半——观察半(performance.record/last_streak/last_hp 过置信门/last_hp_t)= battle_wait 结算点**即时直写**(`cw_screen_battle_wait._write_settlement_observation` 单一写点),策略半原经 `session.pending_round_outcomes` 待加工槽惰性 drain——**该消费半已随 T-64 退役批删除,槽保留为只写不读的观察累积面**。旧 `decide_prep_action` 薄委托已删(P5 挂账兑现)。

**序列语义(历史注——波批时代的冻结条款,反向自旧 `cw_strategy.py` 与旧 `cw_screen_prep.py` 序列消费段)**【迁移后本节为**历史契约**:整波返回/帧稳定截断/空批终止语义已由终结 op 与单动作循环取代([screen_op.md](screen_op.md) §3),本节保留作旧序列锁与历史 ADR 的解读钥匙——现行 fail-stop/控制流/生命周期机制条款仍有效】:
- **帧稳定域**(历史):序列内第 i+1 个动作不得依赖第 i 个动作执行后的新观察;发射时逐动作判"执行后画面状态能否静态推出",推不出即截断——截断器已退役,截断点语义由终结 op 吸收;流程侧保守口径(每动作落地后 heavy 重观察)已由「入口单次 heavy + 逐动作投影」取代。OpenShop/StartBattle 现为终结 op。
- **fail-stop**(现行有效):任一动作未落地 → 恢复原语(关已知弹层,`prep_actions.try_recovery`)→ 交回外循环 heavy 重观察重调接口。参数非法(F3 拒绝)与执行失败同型。
- **逐动作验证保留**(现行有效):期望态对账/执行验证照跑,不依赖重决策(对账时点 = 下一入口,经 `cw_prep_pending_accts` 暂存)。
- **控制流走词表内特殊动作**(现行有效;DeferSpheres 族;defer 计数归框架);策略器禁用空批表达控制流(商店侧空批通道已由 CloseShop 终结取代)。
- **生命周期机制归流程侧**(现行有效):幂等键 `action_key`、连败→恢复→屏蔽、stall 门、强制出战。

共 冷建 2 + 决策入口 11(抽象 12 + 工厂 1 = 13)。新事件面优先归并进既有 pick 接口或走契约改版,禁旁路自造接口。

### 2.3 装配与依赖矩阵（吸收原 09 §4）

- **依赖方向**：实现包 → 知识层/数学层/执行层单向；分包依赖矩阵禁 decision→obs 直依（obs 读口经 app 桶装配点 `install_obs_ports()` 注入）；决策本体 = 纯函数（bridge.decide_from_turn），装配链由注册桥壳覆写注入（app 桶）。
- **装配点**：obs→Snapshot 装配半部在 app 桶（decision_assembly）；黑板单一写端纪律保持；`_RESET_PHASE_ROUND_CACHE` 注入槽（缺省关）+ `discard_stale_match_container`（异常路径残留容器弃置——session 全量重建 by construction）。
- **gated_hp**（结算 HP 新鲜度门，r68/r69 单源 helper）：结算真值仅在可信窗口内覆盖现读——观测质量门，非决策输入（`../strategy-docs/04_survival_budget.md` §7 表 #6）。
- **sim 消费面注记**:sim 消费 decide_shop_screen 驱动器(方向重估经驱动器内单动作入口消费 full 帧触发)——sim A/B 的证明面 = 商店波经济决策;prep 屏编排域在 sim 无实体真值源,其正确性防线 = 契约锁 + 适配器零漂移门 + 实机,不在 sim A/B 辖内。

### 2.4 三臂 A/B 与换核时序（吸收原 09 §5）

- **三臂结构**（判前锁 v6 口径）：单被测体两因子 strategy_id∈{decision_v2, mandate_v1} × ev_arm∈{skeleton_only, full}；三臂 = ①mandate_v1/skeleton_only ②mandate_v1/full ③decision_v2 基线。预指定主对照 = ②−①（EV 增量，命题 B）；次对照 ①−③（命题 A 非劣参照，仅描述性）。命题 A/B 判据骨架 = `../strategy-docs/02_mandate_layer.md` §8。
- **归因域限定**：sim 引擎唯一决策入口 = decide_shop_screen ⇒ 归因域 = shop 决策面（prep 面 sim 不可达），结论不得外推为全决策面处理效应。
- **判读硬前置**（判前锁 v6 检查单）：任一行未落地 ⇒ 正式 A/B 被 raise 拦死（排程层防零刷新事故复发）；强制披露清单（fail-closed 关闭面的拒因计数——U_X/T_SEARCH_A 豁免 ⇒ EV 买/压库/凑息卖/换线塌缩五面两臂恒等关闭，headline 必须随附该降级分量）。
- **遥测分栈**：DecisionTrace 按 (strategy_id, ev_arm) 二元组分栈；mandate 标记维度区分骨架/EV 动作。
- **换核机制** = config 切 strategy_id（最小面），不改流程侧分发；单一核 = mandate_v1（cw4 分层包），decision_v2 为声明的 A/B 基线臂（A/B 过线 = 整体删除旧决策包的触发门；该触发门已随旧决策包删除终结）。

### 2.5 无状态策略与 session / 策略器状态

策略实例不持有可变每局状态;状态三类分离(设计单一源 = `flow/session.md` as-designed):**观察数据**走 `StrategySession`(框架每局新建、局终销毁,只承载读屏采集);**策略器状态** = 实现包私有 `MandateState`,经 `CwStrategy.create_state` 工厂(非 abstract,基类缺省 None)每局冷建、挂 `session.strategy_state` 黑盒引用,框架只搬运引用,消费经访问函数(`strategy_state_of`/impl 侧 `state_of`);**执行层状态** = `ExecState`,宿主 = `CurrencyWarMatch.exec_state`,无 ctx 面经 `exec_state_of(session)` 旁表访问口。异常路径残留容器由 `discard_stale_match_container` 在"确凿新局"信号点丢弃(`cw_strategy.py`)。obs 读口注入槽 `_RESET_PHASE_ROUND_CACHE` 缺省关(`cw_strategy.py`)。

## 3. 各篇导读

| 篇 | 一句话 |
|---|---|
| [outer_loop.md](outer_loop.md) | 外层循环：画面识别分支序、路由、轮次推进、停机/遥测钩子 |
| [screen_op.md](screen_op.md) | **画面 op 统一规范（规格,已落码）**：单动作决策循环、动作基类 execute 单方法（期望态推进 = 容器规则通道:投影口 + 合成升星腿,T-163）、终结 op 集、期望态生命周期、复合动作类、观测通道归属、开放问题落点 |
| [prep_visit.md](prep_visit.md) | 备战访问：单轮形态（入口 heavy + 单动作决策循环 + 投影/保守回退）、备战决策 live 链（mandate_v1）、旧骨架删除注、完成判定与交还外循环 |
| [shop_visit.md](shop_visit.md) | 商店访问：单动作循环（入口观察→逐动作→终结 op）、visit 级刷新硬墙、离店条件与收尾 |
| [action_exec.md](action_exec.md) | 复合动作执行：词表、发射契约三态、动作机械发出+until 转移验证、执行侧守卫面、恢复语义、观测复查 |
| [projection_contract.md](projection_contract.md) | 备战投影面交互契约：cw_state 面板/TurnState 投影 ↔ 执行臂的字段消费、双族坐标系、快照 vs 现读时序、注释规范缺口登记 |
| [guards.md](guards.md) | 守卫总册：G3 环级无进展守卫、停滞/未知/失活防线、降级链、fail-closed 行为 |

## 4. 守卫总览（细则 = guards.md）

| 守卫 | 触发 | 动作 | 载体 |
|---|---|---|---|
| 环级无进展守卫（G3） | 连续 3 个备战环"同签名动作批 ∧ 状态零推进" | 截图+flag 存证 → stop_running | `cw_loop.py::CwLoop.loop` 备战分支 G3 计数段 |
| 停滞 watchdog | 同屏 OCR 指纹连续 6 次采样相同（非战斗态） | 哨兵 flag+日志，**不停机** | `cw_loop.py::CwLoop._stall_watch_tick` |
| 未知画面兜底 | 连续 15 轮全分支不命中（指数退避封顶 10s） | 停机保画面待建档 | `cw_loop.py::CwLoop._handle_unknown_fallback` |
| 策略失活早停 | 连续 2 个完整轮无策略心跳决策行 | 停局重启加载策略 | `cw_loop.py::CwLoop.loop` 策略失活早停检查段 |
| 执行失败安灯 | 购买单元"计划花费>0 金差≈0"（分类器三态） | 停机留现场 flag | `cw_screen_prep.py::CwScreenPrep._exec_fail_hook_check` |
| 商店未识别卡停机 | 收工段牌面仍有 unknown 槽（kind 判据）；判据化自愈重读 2 帧自愈面 | 停机保画面待建档 | `cw_screen_buy_cards.py::run_buy_waves` 未识别卡停机钩子段 |
| 误分发/恢复链限额 | 位面过渡连败 3 / 前台无角色重部署 2 / director 连败 5 | round_fail 交兜底链 | `cw_loop.py::CwLoop` 限额类常量（FRONTLESS_REDEPLOY_LIMIT/PLANE_MISDISPATCH_LIMIT）与 loop 内 director streak 判定 |

## 5. 宪法四条对流程层的适用口径

流程层反向规格化同样过宪法四条（`../strategy-docs/00_framework.md` §1）。流程层的主辖域是编排与守卫，本无策略判据；但反向平移中发现下列**现状违例**（详见各篇 ⚠️ 标记）：

1. **位面字面门**：`flow.py`（`state.plane == 1` 辖域,方向刷新派生视图段）——修正方向：段索引/节点数一律由节点日程（`cw_plane_table.schedule_of`）派生查表，位面只作查表键。（另一处 `round_num >= 9` boss 先验随单动作循环迁移批死码清理消失——载体 `_is_boss_round` 已删。）
2. **hp 越权消费**：谷底回滚 `VALLEY_ROLLBACK_LOSS=15`（`flow.py` 结算策略半 drain 段）——hp 掉量作质量信号触发回滚动作，不在 hp 授权对账表（`../strategy-docs/04_survival_budget.md` §7）；**已裁定退役（2026-09-04 用户裁定：未经数学证明即退役；04 §7 #7）**，代码删除已随 T-64 退役批执行，本项销案。
3. **无标数字**：`VALLEY_ROLLBACK_LOSS=15` 无三形态标注；随第 2 项退役一并消失（已执行）。

## 6. 入口链（enter/start）与弹窗守卫族

> 反向规格化来源 = `currency_war_app.py` + `operations/cw_entry/`（app/enter/start 三层）。对局内循环见 outer_loop.md，本节管「大世界 → 大厅 → 备战」入口链。守卫族决策依据 = 「守卫引入」→「注册表化+领取目标修正」两次演进（细节归 git 历史）。

### 6.1 链路结构

```
CurrencyWarApp（app 三节点）
  _enter_lobby：弹窗守卫 → 暂停面板恢复预检 → 大厅锚/对局屏判定（已在则跳过）→ CwEntryEnter
  _start_match：恢复预检 → 对局屏判定 → CwEntryStart
  _run_loop：CwLoop（对局内，见 outer_loop.md）
CwEntryEnter.wait_lobby（node_max_retry_times=30；`cw_entry_enter.py::CwEntryEnter.wait_lobby`）：弹窗守卫 → 大厅锚 → 前往参与 → 点空白关弹窗 → 公告轮播 → F 交互进大厅
CwEntryStart.click_start（node_max_retry_times 装饰器缺省 3；`operation_node.py::operation_node`）→ advance_to_prep（node_max_retry_times=60；`cw_entry_start.py::CwEntryStart.advance_to_prep`）：备战锚 → 弹窗守卫 → 大厅残留逃逸 →
  前进按钮分支序（难度确认/模式选择/简报/继续进度/投资环境/投资策略/教程叠层/积分奖励页）→ 兜底 retry
```

### 6.2 弹窗守卫族（注册表 `ENTRY_POPUP_GUARDS` + 统一入口 `try_handle_entry_popups`，`cw_entry_start.py`）

四挂点各一行调用 `try_handle_entry_popups(op, screen)`；识别→动作→具名 retry 的参数住在注册表数据行（`EntryPopupGuardSpec`），元组顺序 = 挂点执行序（supply 在 detail 族前，领取优先；序位机械防线 = 测试仓守卫序位锁，元组重排即红）：

| 注册表项 | 识别（AND 全锚同帧） | 动作 | 返回 |
|---|---|---|---|
| `_TRAIN_SUPPLY_GUARD` | 单锚 `标识-列车补给`@0.75 | 点 `文本-领取提示`（领取语义，无 X 钮；S2 实证领取点， rect 以「区域-中央徽章危险区」留档仅供测试负向断言，生产永不点击） | `round_retry('列车补给领取中', wait=3)` |
| `_JADE_DETAIL_GUARD` | 双锚：`标识-星琼标题`@0.5 + `标识-稀有货币`@0.75 | 点 `按钮-关闭X` | `round_retry('星琼详情弹窗关闭中', wait=1.5)` |
| `_STAR_BADGE_GUARD` | 双锚：`标识-流派星徽`@0.9 + `标识-套组标题`@0.9 | 点 `按钮-关闭` | `round_retry('星徽详情弹窗关闭中', wait=1.5)` |

- `try_handle_train_supply_popup` 薄包装仅保留给 CW 之外的真实消费方 `back_to_normal_world_plus`（只管 supply 语义不变）；jade/badge 无 CW 外消费方不设包装。
- **挂点序位**：守卫列位于各节点一切既有分支之前（模态弹窗盖场时背景锚点全部失明，守卫不接则兜底空烧节点预算）；`advance_to_prep` 内先于一切状态分支，且守卫轮不烧 `_advance_steps` 推进预算。
- **返回语义**：守卫一律 `round_retry`（计入 `node_max_retry_times`），禁 `round_wait`（框架对 WAIT 不计 retry 且归零计数 → 无界空转）；守卫×领取交替循环每圈耗 2 次预算，任一节点预算内具名 FAIL。
- **对局屏白名单口径**：`cw_screen_state.LOBBY_STATE_SCREENS` 显式排除入口链可达的非对局屏（大厅/攻略系/列车补给弹窗/星琼详情/星徽详情/积分奖励等）；带 `货币战争-` 前缀的新建档屏默认进对局屏集，入口链可达的弹窗/奖励页漏排除 = 误判「已在对局中」跳过 enter（锁测试钉死）。
