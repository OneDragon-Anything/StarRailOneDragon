# 备战交互链迁移（特殊流程段消费首批）迭代设计（总纲）

## 0. 元信息

- **迭代目标**：挂账板《CW跨迭代挂账.md》§二.7② 余面（备战默认分支三段交互链）落地——消费上批（2026-11-18-launch-atom-restructure）定型的画面 op 四段规范与特殊流程段位置。
- **用户裁定（2026-11-18）**：①五个设计点按默认案执行（锁定态跟对局走不进状态容器逻辑域／探针在特殊流程段试探零状态写／补给分流机械随迁／战斗窗置位留主循环回调／多轮停点留主循环）；②测试靠已有画面建档支撑 harness，实机验收不阻批——实现中发现 harness 覆盖不了的实机形态，最后记入货币战争待办。
- **状态**：定稿（2026-11-18，两轮三核收敛，报告与处置 = [attack.md](attack.md)）
- **单文档方案**：本文即完整设计（深度要求与详设相同）。

## 1. 问题与动机

### 1.1 现状症状

主循环（`operations/cw_loop.py::CwLoop`）住着四处**操作画面的代码**与配套状态：

1. **返回投资策略点击**（:1342-1346，备战分支内）：OCR「返回投资策略选择」（lcs_percent=0.9，防线理由见 :1338-1341 注释——与「请选择投资策略」共享子串 0.75 在默认阈值之上，误匹配会吞投资策略屏致死循环）→ 点击 → 计数报警（`_cw_back_btn_count`）→ 交回。语义 = 上游投资策略屏处理失败的 symptom 补救；
2. **恢复局锁定探针**（:1357-1388）：候选判定（`resume_candidate(新match, 位面, 轮次)`，轮次经 `read_phase_round` 读）→ **候选过判即接管失效写**（:1370，先于探针点击，非锁定候选帧同样写）→ 点「按钮-商店」试探 → 验收「按钮-收起」出现与否（`probe_resolve`）→ 非锁定收店走常规 / 锁定确认置三标志（:1384-1386，`locked_resume=True ∧ locked_sync_done=False` 同帧配对写）；
3. **锁定直出战**（:1389-1401）：`locked_resume_sync_and_battle`（上批已迁 `prep_actions.py`）→ 成功 = 锁解除 + 置战斗窗（:1395-1396）+ 交回 / 未执行 = retry 保锁；
4. **补给分流**（:1421-1437）：`read_node_sequence` current=supply ∧ `chosen_supply` 未确认 → 点「按钮-返回补给阶段」进补给屏 / 已确认 → 走常规备战。

配套状态住 loop 实例：`_is_new_match/_cw_resume_candidate/_cw_locked_resume/_cw_locked_round`（handle_init :441-449 每次 execute 重判/重置）+ `_cw_locked_sync_done`（handle_init **不**初始化，由 `prep_actions.py:630` getattr 容缺承载）+ `_cw_back_btn_count`（:451）。

**周边关联点**（本批波及但不迁移）：

- **战斗帧恢复检测**（:1222-1240，iter1 ∧ 新局 ∧ battle_or_transit 分支）：最小读位面轮次 → 残局标记 → **接管失效写第二确认点**（:1237）。留主循环。
- **max_rounds 停点**（:1406-1410）：位于三段链**之后**、补给分流之前。
- **接管失效写方法**（`_invalidate_tracked_on_takeover` :530-562）：两确认点共用的写体（GameState `tracked_account_observed` 写 False，actor='CwLoop'，evidence='takeover_invalidation'）。

### 1.2 根因归层

- **流程层**：特殊流程段宿主缺位——三段链是画面级子态识别与处置（答案固定的流程反射），规范位置已在上一批定型（画面 op 四段：识别 → 上报 → 特殊画面流程处理 → 策略器处理），本批消费。

### 1.3 解决到哪 / 明确不解决

**解决**：三段链迁入 `CwScreenPrep` 特殊流程位置，锁定状态机宿主随迁（写入节奏不变），主循环备战分支坍缩为「识别（双识别标志）→ 兜底清 → 停点 → 派发」。

**明确不解决**：

- 横幅中间态守卫（OCR「请选择投资策略」→ wait）：识别侧守卫，留主循环；
- max_rounds 停点：运行管理，留主循环（次序新语义申报见 §2.2-4）；
- `_fallback_clear_pending`（兜底清）与 `_on_prep_round` 回调（战斗窗置位）：循环本职，留主循环；
- **战斗帧恢复检测块**（:1222-1240）与其失效写确认点（:1237）：留主循环（失效写方法因此保留，见 §2.3）；
- **浮层闸门 / 屏态复验两道防线退役论证**：上批移交本批裁——显式维持（消费面 = 出战发出链，随迁宿主不变），退役论证移交挂账板新条目（§二.7⑤）；
- 挂账板 §二.7④（局终收尾等）：维持现状，本批不触碰；
- 挂账板 §二.7①（道具详情弹窗）：已裁暂维持，本批不触碰。

## 2. 方案

### 2.1 目标形态

```
主循环备战分支(坍缩后):
  横幅守卫 → prep_anchors_hit 双识别标志识别 → _fallback_clear_pending
  → max_rounds 停点 → 派发 CwScreenPrep(on_result 回调不变)

CwScreenPrep 观察 node:
  段1 子态识别(最顶部,先于 match 缺席门/清场/收店探针/heavy/补采/审计):
     0. Match.locked_resume=True = 锁定确认态(含重派发重入帧) → 直达段3b
     a. OCR「返回投资策略选择」在场(lcs 0.9 同款) = 返回按钮子态
     b. Match.resume_probe_pending=True = 探针子态:
        候选过判 → 立即接管失效写(段2 上报) → 点「按钮-商店」试探 → 判定
     c. read_node_sequence current=supply ∧ chosen_supply 未确认 = 补给分流子态
     优先序 0 > a > b > c(现状同序);非常规子态跳过全部既有前置段
     (清场/收店探针/heavy/补采委派/审计,零接触 cw4_segment_serial)
     查全否 → match 缺席门 → 清场 → 收店探针 → heavy → …(现行全量,零变化)
  段2 上报 = 子态流程事实写(Match 字段 + 接管失效写),非 obs 上报:
     b 查候选过判: 失效写(actor='CwScreenPrep')+探针;
     探针裁决后: resume_probe_pending 无条件撤回(现状 :1376 同语义,防同 run 重探针);
     锁定确认: locked_resume=True ∧ locked_round ∧ locked_sync_done=False 同帧配对写
  探针与收店 = 识别手段(观察 node 识别性点击,读屏例外新类);
  非锁定收店后续跑常规路径(按序跑齐全部既有前置段,等价今天 fresh visit)

CwScreenPrep 决策动作 node:
  段3 特殊流程处置(位于 cw4_segment_serial 置位行之前):
     a. 点「返回投资策略选择」→ 交回(下轮身份分发进投资策略屏)
     b. 锁定 → locked_resume_sync_and_battle(prep_actions) → 成功=锁解除+交回
        / 未执行=retry 保锁(round_retry,预算 3 耗尽→访问 fail→外环 fail-streak)
     c. 点「按钮-返回补给阶段」→ 交回(下轮身份分发进补给屏)
     a/c 点击成败均交回(不落段4、不落 retry): 下轮重识别自然重试(现状同语义)
  段4 策略器处理: 常规路径现状不变
```

### 2.2 子态识别与处置的重分层（本设计的关键裁定）

**判定（识别）前置到段 1 最顶部、处置（动作）在段 3**，依据 = 行为保真：今天这三类帧**从不进入 CwScreenPrep 访问**（主循环在派发前就处置完毕），即「heavy 观察、清场、收店探针、补采委派、审计、serial 置位」从未在这三类帧上跑过。迁移后若按规范字面先跑这些前置段再特殊流程，产生两处行为漂移：

1. **锁定帧**：heavy 观察会把板面真值写入状态容器 → 恢复局同步步的部署计划从「空计划零部署」（现状，`prep_actions.py::locked_resume_sync_and_battle` docstring 隐藏前提声明：恢复局 session 新鲜板面未观察 ⇒ deploy-swap 卖出通道整体跳过）漂移为「真部署」——未经验证的行为变化；
2. **返回按钮帧/补给未确认帧**：多出对账（reconcile：观察段把屏幕真值写回状态容器）写面与 serial 置位（无害但非现状）。

裁定：

- **非常规子态 → 段 1 只做子态识别与上报，跳过全部既有前置段；常规帧走现行全量路径零变化**。四查落点 = 观察 node 最顶部（先于清场/收店探针）——子态帧今天对这两段零接触，放在其后 = 新增接触面；返回按钮 OCR 的 overlay 干扰形态与今天同场（主循环跑 OCR 时 overlay 同样在场），lcs 0.9 防线照搬即保真。
- **第 0 查（锁定确认态）是硬前提**：锁定帧在任何轮次都先于派发被拦截（现状 :1389 先于 :1468）——迁移后锁定帧重入 op 的通路 = 段3b retry 耗尽 → 访问 fail → 重派发新访问，此时 `resume_probe_pending` 已清、a/c 查不命中，无第 0 查则 heavy 观察在锁定帧上执行（即漂移①）。优先序 0 > a > b > c：现状实证仅「锁定先于补给」（:1389 先于 :1421，「恢复局例外：恢复局商店锁死只能出战」）；0 提前于 a/b 依赖子态不共存假设（锁定帧上 b 必不命中——候选已清；a 的 symptom 形态与商店锁死实践中不共存），按假设申报。
- **探针 = 锁定子态的识别手段**（商店可开性探测），不是策略动作；其判定结论（锁定/非锁定）经段 2 上报。**失效写时点保持「候选过判即写」**（现状 :1370 先于探针点击，非锁定候选帧同样写）——不挂锁定确认，非锁定接管帧的失效保护不收窄。
- **非锁定探针帧收店后继续常规路径**：按序跑齐全部既有前置段（清场→收店探针→heavy→补采→审计），等价今天「收店后同帧落常规派发 → fresh visit 全序列」；收店 `success_wait=1.0` 沿现状值。
- **max_rounds 停点次序变化 = 新语义申报**：现状停点在三段链之后（达标帧先处置返回按钮/探针/锁定出战再停，:1342→:1406）；坍缩后停点先于派发，**停点模式下三类子态不再处置**（候选挂起、锁定不确认、返回按钮不点，直接停屏）。裁定接受：停点语义 =「停备战屏不跑备战单轮」，三段链属备战交互；stop 模式属人工验证场景。**跨 run 后果随记**：停点命中候选帧后同进程再跑（人工验证的标准「停→看→再跑」），`was_new=False` → `resume_probe_pending=False` → 探针链对该局永久失活（锁定接管则锁永不确定）——与现状 rerun 语义逐点一致（既有形态保留），危害与承载见 §2.3 残余面申报。正本 loop.md §3 同步申报。

### 2.3 锁定状态机宿主迁移

宿主 = `CurrencyWarMatch`（`strategies/impl/cw_strategy.py:365`，运行时挂 `ctx.cw_match`，生命周期 = 每局创建/局终置 None）。additive 字段（带定义注释：取值时机/写入端/消费边界）：

| 字段 | 迁自 | 语义与写入节奏 |
|---|---|---|
| `is_new_match: bool` | loop `_is_new_match` | **handle_init 逐 execute 重判写入**（`was_new = ctx.cw_match is None`，兜底建局先建后写）——非创建时点定值；续跑/手动多轮语义与现状逐点一致 |
| `resume_probe_pending: bool` | `_cw_resume_candidate` | handle_init 写 `= was_new`（新局 True 待探针裁决）；撤回点两处随迁：候选判定否（现 :1368）/ 探针裁决后（现 :1376） |
| `locked_resume: bool` | `_cw_locked_resume` | handle_init 重置 False；锁定确认置 True |
| `locked_round: int` | `_cw_locked_round` | handle_init 重置 0；锁定确认写轮次（遥测对照） |
| `locked_sync_done: bool = True` | （loop 不初始化，prep_actions getattr 容缺） | **不进 handle_init 重置**（与现状一致）；锁定确认置 False、prep_actions 发出后置 True；初值 True 依赖配对不变量：段3b 仅经 `locked_resume=True` 可达，而该置位与 `locked_sync_done=False` 同帧配对写 |

- **写入节奏裁定**：全部字段**写入节奏维持现状 per-run 重判/重置**（handle_init 内写 Match，兜底建局先 `establish_new_match` 再写）——「宿主容量整局、写入节奏 per-run」，续跑与手动多轮行为与现状逐点等价（跨 run 锁定帧跌回常规链的现状形态一并保留）。
- **读取点改指**：三处 run 级消费（:459 SettlementState、:461 兜底建局门、:1222 恢复检测门）改读 Match 字段——handle_init 先于三处执行，值语义逐点等价；候选判定输入（现 :1367 `resume_candidate(self._is_new_match,…)`）改读 Match 字段。
- **消费边界**：以上字段仅 `operations/` 树与 `prep_actions.py`（发出核证据位）读写；**策略器禁读**——强制 = 结构性不持有（策略器构造签名无 Match 引用，mandate_v1 全目录零引用实证）+ `CwStrategy` 契约 docstring 登记禁读字段清单。流程事实不进 GameState（真值域混入流程事实会脏「观察态/逻辑态」边界——观察态 = 屏幕真值锚定标记，逻辑态 = 策略器推理用写入通道），也不进 kernel StrategySession（瘦身终态，八处 session 份停用，流程事实不入 kernel）。
- **接管失效写双确认点分流**：备战帧确认点迁画面 op 段2（同款 `write_logic` 调用，actor 改指 `CwScreenPrep`，evidence='takeover_invalidation' 不变）；**战斗帧确认点（:1237）留主循环，`_invalidate_tracked_on_takeover` 方法保留**（docstring 写点登记同步改写）。`kernel/cw_game_state.py:2825` 字段注释的写入端登记随 3.2 更新。
- **返回按钮计数**：`_cw_back_btn_count` 迁 `cw4_counters` 分键 `back_to_strategy_symptom`（遥测单一载体）。申报：寿命 per-run → per-match（计数起点每局归零，日志「第N次」语义随之）、进局终 `MatchFinal.cw4_counters` 快照（遥测面新增，改善方向）、写点需 `strategy_state` 缺席 None 守卫（先例 = `prep_actions.py` 发出链既有守卫）。写点 = 画面 op 段3a 处置处（随 3.2 迁）。
- **Match 缺席防御**：run 语境下 handle_init 兜底建局后 Match 恒在场；画面 op 段1 读 Match 局外/桩缺席时，第 0 查与 b 查按否处理（较现状严格——现状候选初值可为 True，但该形态仅存于桩场景，接受并申报）。证据位写侧（prep_actions 置 True）在 Match 缺席时结构性不可达：段3b 仅经第 0 查门（`locked_resume=True`）可达，该置位蕴含 Match 在场。
- **跨 run 残余面（既有形态保留，非本批引入）**：per-run 重置节奏下，锁定帧跨 run 重入无第 0 查保护（第 0 查辖界 = 同 run）——落常规链 heavy 观察后策略器发商店动作、锁定帧点击落空、空转至系统哨兵（`kernel/cw_resume_lock.py` 头注记录的原始故障形态以降级形式复发）。危害面 = 手动逐轮验证场景的接管局；现状同形态已存在（重置语义保留 = 「行为零变化」承诺的一部分）。处置：显式接受 + 挂账板立目（§二.7⑥），后续单独裁。

### 2.4 主循环残留面

横幅守卫、`prep_anchors_hit` 识别、`_fallback_clear_pending`、max_rounds 停点、`_on_prep_round` 回调、派发与环让位重入契约、战斗帧恢复检测块（:1222-1240）及其失效写点——全部保留。锁定直出战的战斗窗置位（现 :1395-1396）删去：`_on_prep_round` 回调对一切 success 交回统一置位（既有语义，宽限等待 + 白名单兜底机制不变）。

### 2.5 sim 面

三子态 sim 均**恒不可达**，sim 零行为变化：

| 子态 | 机理 |
|---|---|
| 探针/锁定直出战 | sim 驱动器预建 Match 后才构造 CwLoop（`sr-od-test/test/harness/sim_backend_runner.py` 与 `skills/sr-od-dev-currency-war/scripts/cw_sim_match_drive.py` 同形）→ handle_init `was-None` 判 False → `resume_probe_pending=False`（b 查触发条件即不满足）→ 探针不触发 |
| 补给分流 | sim 对 supply 节点**原子呈现**备战底层+补给模态（`_present_node_screen` → `_present_modal` 立即翻屏），未确认期身份恒补给屏 → 主循环阶段一直接分发 CwScreenSupplyNode，「备战帧 ∧ current=supply ∧ 未确认」形态不可达；后端亦无「按钮-返回补给阶段」点击源 |
| 返回投资策略 | 上游策略屏处理失败 symptom，sim 决策链不产生该形态（sim 包与后端 grep 零命中） |

### 2.6 交互时序（迁移后）与 wait 值对照

```
备战帧(常规): 派发 → 段1 三查全否 → 前置段全量(现状) → 段4 策略器决策
锁定重入帧:   派发 → 段1 第0查命中 → 跳全部前置段 → 段3b 出战 → 交回/未执行
返回按钮帧:   派发 → 段1a → 跳前置段 → 段3a 点击 → 交回 → 下轮投资策略屏
恢复候选帧:   派发 → 段1b → 候选过判失效写(段2) → 点商店试探 →
              非锁定: 收店 → 按序跑齐前置段 → 段4 /
              锁定: 段2 配对写 → 段3b 同步步+出战 → 交回(回调置战斗窗)
补给未确认帧: 派发 → 段1c → 跳前置段 → 段3c 点击 → 交回 → 下轮补给屏
```

wait 值与防线参数**沿现状值随迁**（来源 = 被迁代码行原值）：返回按钮 OCR lcs_percent=0.9（防线理由注释随迁，见 §1.1-1）+ 点击 success_wait=2 + 交回 round_wait(2)（:1342/:1346）；探针点击 success_wait=1.2（:1372）；非锁定收店 success_wait=1.0（:1380）；锁定出战交回 round_wait(3)（:1398）；未执行 retry round_retry(2)（:1401，预算 3 → 访问 fail → 外环 fail-streak 备战键限 5）；补给点击 success_wait=2 + 交回 round_wait(2)（:1435/:1437）。失败链幅度对照申报：现状 = loop 节点 retry 预算 400（cw_loop.py:1177 显式覆写）≈ 400 次原地重试后 CwLoop fail；新形态 = 每访问 3 次 × 外环重派发 5 次 = 至多 15 次出战尝试后 CwLoop fail（锁定帧场景两次派发之间无 ok，streak 不归零）——均有界，界收窄约一个量级。

### 2.7 关键取舍

1. **子态识别前置 heavy 之前，不按四段规范字面**：规范段 1-2 = 观察 node 全量，但三类子态帧今天从不被任何前置段接触（保真要求见 §2.2）；子态识别本身 = 识别工作（段 1 语义内），处置动作仍在段 3。对正本的扩展修订申报：①段 1 允许识别性点击（探针/收店 = 读屏例外新类）；②段 2 语义扩展 = 子态流程事实写（Match 字段 + 失效写），非 obs 上报——正本更新清单覆盖两条。
2. **锁定态宿主 = CurrencyWarMatch 散字段**：寿命同构（宿主容量整局/局终消亡）；GameState 是真值域、kernel StrategySession 处于瘦身终态（流程事实不入 kernel），两者均不取；不加 PrepFlowState 组合对象（Match 已是对局域事实载体，五字段同域聚集，再加一层间接无收益）。op 实例每访问新建，跨访问存活不成立。
3. **三子态不拆独立 op、不按「每类一 node」拆分**：三子态宿主都是备战画面（派发依据 = 双识别标志同帧命中，备战无独立 id_mark 身份——op 内不重复身份门），同帧互斥（OCR/探针/节点条判定互不共现）；引用正本 screen-op.md「备战（CwScreenPrep）特殊」豁免行，三类处置共享决策动作 node 顶部特殊流程分流位。
4. **三段迁移一次切换，禁分批**：op 吸收与主循环坍缩若分两批，中间态双探针互双发（主循环探针先跑清候选，画面 op 再探会二次点商店）——迁移原子性 = 正确性约束，非排期偏好。
5. **战斗窗置位依赖既有回调，不在特殊流程内重复**：`_on_prep_round` 对一切 success 统一置位（宽限 + 白名单兜底既有），特殊流程内重复置位 = 第二写点。
6. **停点模式不处置三段链 = 新语义**（§2.2 末条裁定），非保真项，正本同步申报。

### 2.8 测试面（新建清单；画面建档支撑 harness，实机项最后记账）

按 sr-od-test src 镜像拆分目录形态新建（harness = `sr-od-test/test/harness/fixture_controller.py`，`with fast_sleep()`；画面帧与 area 可见性由建档现值驱动）：

- **`test/sr_od/application/currency_war/operations/cw_screen/cw_screen_prep/test_prep_special_flow.py`**（新建；测试目录现仅存 `__pycache__` 缓存，测试文件全量新建）六剧本：
  1. 常规帧：四查全否 → 前置段全量照旧（现行为零变化）；
  2. 返回按钮帧：识别 → 跳前置段 → 点击返回（lcs 断言）→ 交回；
  3. 探针非锁定：候选帧点商店 → 收起出现 → 失效写已发生 → 收店 → `resume_probe_pending` 撤回断言 → 按序跑齐前置段 → 策略器路径；
  4. 探针锁定：候选帧点商店 → 收起不出现 → 失效写 + 配对写字段断言（`locked_resume=True ∧ locked_sync_done=False`）→ 候选撤回断言 → 同步步 → 出战发出 → 交回；
  5. 补给未确认：识别 → 跳前置段 → 点返回补给阶段 → 交回；补给已确认 → 常规路径；
  6. **锁定重派发帧**：段3b retry 耗尽 → 访问 fail → 重派发新访问经第 0 查直达段3b，断言零前置段接触（防 heavy 在锁定帧执行）。
- **既有回归同步**：`test_prep_actions.py` 四路径回归的 resume 证据位剧本改指 Match 宿主字段（现状断言写 op 属性，桩对象动态 setattr 掩盖宿主失配——同步后消除）；主循环侧备战分支**无既有测试**（测试仓 CW 域 2026-11-16 清场后为零），3.1/3.2 的护栏 = 六剧本按阶段先行提交（3.2 提交首批，3.3 补齐）。
- **harness 前提**：首步验证 fixture 帧资产（备战/开商店画面帧图）现值可用——「零新建档」指 screen_info 档；帧图不可用则在剧本内构造（零真实副作用）。
- 建档支撑声明：探针两形态（收起出现/不出现）由 harness 帧状态脚本化（`set_phases` 帧序列切换 + 建档帧资产，含备战「已锁定/未锁定」帧），`货币战争-备战`/`货币战争-备战-开商店` 档现值直接可用。
