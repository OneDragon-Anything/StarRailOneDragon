# CwActionOpenBookcardOp（开书册卡）参数面迁移设计稿（r1）

> 迭代：CW 动作 op 迁移流水线 · 设计角色产出（开书册卡 op 批 = 第六棒，开件族第一件）。
> 上批 = 卖备战席 SellBench（changes/sell-bench-param-surface/design.md，已落地 commit d3ea8719b）；第四棒 = SellDeployed（commit 68199b48d）；第三棒 = MoveUnit（commit a09f30e8b）；第二棒 = 工具原子七类（commit 76a94c27c）；首棒 = WearEquip（commit db4697e40 终稿）。
> **范围裁定（用户指令，每迭代只切一个 op）**：本批只做 `CwActionOpenBookcardOp` 一件——开件族第一件，**审计挂号的 slot=None 硬 gs 分支 bug（op 机械路径消费 game state + 双出口 AssertionError，挂号链 = MoveUnit 稿 §9 行 2 → SellDeployed 稿 §9 行 3 → SellBench 稿 §9 行 1 → 流水线账本 `进度.md:41` 第六棒条）随本批处理**，是本批核心价值。OpenBox/OpenTome 撤出本批、待后续独立迭代（§9 申报行 1）。
> 冻结宪法（用户裁定，穿装批成文）：①动作 op 执行路径零 gs 依赖；②参数面三分法；③名称字段 = 语义参数（可选，不参与校验与定位，仅日志）——记账面亦零消费；④坐标新鲜度纪律归调用方；⑤参数 dataclass 统一补 `from_dict`；⑥gs 给实体记录坐标（坐标伴随域）；⑦每个 op 一个迭代，牵涉面一次改净。
> **记账路径总契约（正文 = `skills/sr-od-dev-currency-war/references/flow/action-op.md` L32「记账路径总契约」条款；行号 = b87bf023d 基准——前稿引 L30 系 T-6 改动该文件前的旧行距）第六适用者**；本 op 对象住槽位表不住坐标伴随域，且记账载荷退化——腾位直址写（kind bookcard → empty），无身份反查需求（无回金/无装备回收/无 sold 内容），比卖出族槽位反查更简一档（§1.2）。
> **行号基准声明**：本稿全部行号基于 HEAD `b87bf023d`。任务书下发基准 `d3ea8719b` 已漂一格——漂移提交 b87bf023d（T-6 出战域原子化正本更新）经 `git show --stat` 核验为纯 docs/skill 提交（12 文件零 .py），本稿全部 .py 行号对两基准逐位同，引用均已按 HEAD 实读自核。⚠️ **工作区并行批在飞申报**：工作区有未提交改动（`data/affix_effects_data.py`、备战/商店/投资画面档 yml、SKILL.md 与三份 skill references 等——另一装备广场系批的工作现场）。在飞备战档 diff 经 `git diff | Select-String '备战栏'` 核验**不触备战栏-N area 族**，本稿「备战栏-N 在档」结构事实不受影响；实施角色动任何文件前必须复核该批落库状态，本稿引用以 HEAD 为准，绝不卷入在飞改动行（对齐 SellBench 稿 §0 同款纪律）。

## 0. 本批范围

`operations/cw_op/cw_open_bookcard_action.py::CwActionOpenBookcardOp` + 词表 param `CwActionOpenBookcardParam` + 上报层调用面（outcome 消费形态 + None 分支退役，§1.2）+ 全部引用（grep 全量已核，§3）。

现状债（迁移动机）：

| 债 | 现值（HEAD） | 迁移形态 |
|---|---|---|
| **slot=None 硬 gs 分支（审计挂号 bug，本批主轴）** | `cw_open_bookcard_action.py:85-107`：slot=None 时 op 机械路径中途 `game_state_from_ctx` 现算首件 bookcard 槽（宪法①「执行路径零 gs 依赖」违例本体）+ 双出口守卫断言（gs 缺席 / bench 无该 kind 首槽 → AssertionError） | None 语义废除、slot 必填化（§1.1）：词表字段去缺省 + op 守卫显式拒 None + 上报层 None 分支随批退役——「哪个槽有书册卡」的现算收敛回决策层唯一合法 gs 消费面（现值已合规，零改动） |
| 机械链窥探 executor 私有面 | `:77` `ex = env.executor` 后 `:78/:84` 读 `ex._bench_pts` 私有点表做守卫上界、`:113/:115-116` 经 `ex._ctx` 取 controller——与 SellBench 批已退役的 getattr 容缺同族（本件非 getattr 形态，直接必崩商店域形态但本件单域无此形态，债 = 私有面窥探本身） | op 机械面全自持：守卫上界 op 内现读 `row_area_centers(ctx,'备战栏')`，controller 走 `self.ctx`，零 env 消费（§1.4） |
| outcome 拒单不可见 | `:134-138` `outcome` 仅取 `world_decl`，`applied=False`（`bookcard_slot_missing` 拒单零写）对直调方不可见 | 家族 M-r3-1① 同形：`applied=False` → round detail 追加拒单段（§1.2） |
| param 缺 `from_dict` | `CwActionOpenBookcardParam` 无 `from_dict` classmethod（`cw_vocab.py:590-606` 类体内零 classmethod） | 共享 `cw_vocab.action_param_from_dict`（:610-618）一行委托 |
| sim 局白睡 1.8s | `:120-123` `time.sleep(_OVERLAY_ANIM_WAIT_S)` 在 `mechanical_io_allowed()` gate 外无条件执行（点击已 gate、睡眠未 gate） | sleep 移入 gate（SellBench op 现值 :120-127 家族形态），§7 条 3 行为变化申报 |
| env 必传（无缺省） | `:59-60` 构造签名 `env: PrepExecEnv` 必传——MCP `run_operation` 直调不可达（backend 扫描面 `operation_registry.py:41-44` 含 `sr_od.application`，本 op 类已在 `list_operations` 可见，env 形参 required 非 JSON 可构造 = 卡在构造面） | 签名改 `env: PrepExecEnv | None = None`（家族同款：形参保留 = 注册表构造签名兼容 + MCP 直调缺省安全，§1.5） |
| 死桩替身 | `prep_actions.py:485-494` `_open_bookcard` 薄委托——docstring 自述保留理由 = 单帧测试 `test_prep_action_ops.py::test_open_bookcard_executor_mechanical` 直调面；**该测试已不存在**（sr-od-test 全仓 grep `_open_bookcard`/`open_bookcard`/`test_prep_action_ops` 零命中），src 生产面零调用（grep 已核） | 随批删除（bookcard 专属桩，牵涉面一次改净；SellBench 批删 `_sell_bench` 桩同款先例） |

## 1. 本批特有设计题裁决

### 1.1 slot=None 主轴裁决：None 语义废除、slot 必填化（选项 B「现读定位」被冻结宪法排除，非裁量题）

**裁决：`CwActionOpenBookcardParam.slot` 从 `int | None = None` 改为 `int`（必填无缺省）；op 守卫显式拒 None；上报层 None 现算分支随批删除；None 语义全链退役。**

**根在哪一层（根源两问）**：根在**约定层**——None 是「op 帮调用方去 gs 里找答案」的参数缺省语义，它把「参数缺失」翻译成「op 做一次决策层本职的现算」。修根 = 把现算归还决策层（唯一合法 gs 消费面），参数面只收显式值、缺失即显式报错——正是冻结宪法①明文「gs 可选快路径全部拔除；参数缺失 = 参数校验显式报错（禁静默兜底）」的执行，不是症状补丁。

**论证链**：

1. **生产发出面已合规，None 零生产流量**：唯一生产构造点 = `strategies/impl/mandate_v1/entry.py:538-559` `_consumable_open_action`（entry ① prep 实体面卡片分支 + 第 0 步溢出自救态 2 两个调用域共用）——`:555-558` 决策层从 gs bench 槽位表按 kind 现算 `idx` 并显式传 `Emitted(atom_cls(slot=idx + 1), True, tag)`。grep 全量核验：`CwActionOpenBookcardParam` 构造仅此一处。None 只活在四个死角：词表缺省值（`cw_vocab.py:603`）、op 现算分支（op :85-107）、上报层 None 分支（`open_bookcard.py:65-67`）、MCP 直调空 dict 形态。**废除 None = 生产面零改动、纯死角清理**——迁移成本与风险最小的根治形态。
2. **bug 形态定位（审计挂号内容兑现）**：MCP 直调（`run_operation` from_dict 最小 dict `{}`）→ slot 落缺省 None → op 进 gs 分支 → 直调场景 `game_state_from_ctx` 缺席返回 None → AssertionError「gs 缺席」（op :91-94）；即使 gs 在场而 bench 无 bookcard kind 槽 → 第二 AssertionError（:100-103）。双出口都是「参数缺失的报错点脱节」：报错发生在 op 内部现算出口，错误信息不指向参数契约，且机械路径已消费 gs（宪法①违例先于报错发生）。必填化后同一形态 = 构造面 TypeError（缺 slot 键，from_dict `cls(**…)` 自然缺参异常）或 op 守卫 AssertionError（显式传 null，文案直指参数契约）——报错点前移至参数面，fail-fast。
3. **选项 B（转「现读定位占槽物」合法形态）被宪法排除**：SellBench 的「op 内现读」先例 = `row_area_centers` 现读 screen_info **静态档**（点位表，建档常量）——那是合法现读源。而「哪个槽位当前被书册卡占据」不是静态档信息，它只存在于两处：gs 逻辑态（观察装配点写入的 bench kind 槽位表）或画面观察态（find_bookcards 识别）。动作 op 两处都不许读：读 gs = 宪法①违例（正是本批要拔除的对象，转一圈回到原地）；读屏 = action-op.md「零新增读屏」明文禁。**结论：选项 B 不存在合法实现形态**，「现读」与「占槽物定位」两个词组合不出第三条路——这不是两案择优，是一案成立一案被规范排除。
4. **三处同型现算收敛为一处，附带债务闭合**：现值三处各自维护「bench 首个 bookcard kind 槽 → 槽号」同型现算（决策层 `entry.py:555-558` / op `:95-104` / 上报层 `open_bookcard.py:65-67`），op 文件头 :37-42 注释自述「三处语义必须一致，提取公共函数归另批」——本批废除 None 后三处收敛为决策层一处，op 文件头注释与 `_BOOKCARD_BENCH_KIND` 常量（:42，模块私有无外部消费，grep 已核）随批删除，「提取公共函数」债因对象消失自然闭合（无需另批）。

**迁移申报（双调用面覆盖）**：

| 调用面 | 现形态 | 迁移后 |
|---|---|---|
| 流程发出面（entry `_consumable_open_action`，生产唯一构造点） | `atom_cls(slot=idx + 1)` 显式传（:558） | **零改动**——已按必填形态传参，废除 None 对它零行为差（这是裁决 1 的直接落地证据） |
| MCP 直调面（agent 经 `run_operation`，from_dict 通道） | `{}` → slot=None → op gs 分支 → 双出口 AssertionError（审计挂号 bug 形态）；本形态今日还卡在更早一层：`env` 必传非 JSON 可构造，`run_operation` 构造不了 op（§0 债表末行）——**bug 形态今日实际不可达，废除是「修复+打通」一体** | env 缺省化打通构造面后：`{"slot": 1-9}` = 合法直调；缺 slot 键 = 构造面 TypeError（缺参自然异常）；`{"slot": null}` = op 守卫 AssertionError（文案申报废除语义与传参指引，§2.2）；传参指引 = 当帧 extras `bench.slots` 中 kind='bookcard' 槽的下标 + 1（决策同源口径，§3.2 docstring 契约） |
| 单帧测试/离线直构面 | `CwActionOpenBookcardParam()` 零参构造合法（落 None） | 零参构造 TypeError（缺必填位）——测试与离线面同步显式化（§5） |

### 1.2 记账路径核验：腾位直址写 + overlay 登记 + 纯转移声明（总契约第六适用者，槽位键域退化形态）；上报层**非零改造**（None 分支退役），零行为变化面见核验表

**记账消费什么（宪法③核验前置的事实面，`kernel/cw_action_report/open_bookcard.py` 逐段现值）**：

| 记账消费 | 现形态 | 名称/载荷来源 |
|---|---|---|
| bench 腾位写 | `param.slot` → 槽位表直址，`slots[_idx] = BenchSlot(kind='empty')` 整表替换单笔（:64-73）；槽不存在/越界/类型不符 = `bookcard_slot_missing` 拒单零写零声明（:68-70） | 记账键 = 槽位下标（`int(param.slot) - 1`）；载荷 = 常量 empty（**零身份反查**——无回金、无装备回收、无 sold 内容，卖出族槽位反查的退化形态） |
| 浮层出现事实 | `register_screen_change(gs, 'expert_invite', KIND_SCREEN_NAMES['expert_invite'])`（:74-82）——点开直弹专家邀请函五选一，登记与动作落地同点（action-op.md L107「开件直登族」） | 封闭词表 kind 常量，非名称语义 |
| 转移声明 | `WorldDecl(next_screen=node_screen_now(gs), trigger='')` 纯转移（:37-38，转移表 #6 行） | 节点序现算（kernel 派生） |
| 早退形态 | bench 视图缺席 = `applied=True, reason='bench_unobserved'` 零写但带声明（:57-63；docstring 自述生产不可达——bench 恒有开局种子 9 槽视图，仅测试直构/离线形态可达） | 既有申报保留，本批不动（§9 申报行 8） |

**无库存变化核验**：上报函数全文唯一状态容器写端 = `gs.bench`（:72）；零 `gs.equips`/`gs.gold`/零获得链调用 grep 已核——开卡 = 纯腾位 + 浮层事实，选卡后果（专家人选入板）归 `PickExpertInvite` 独立动作的记账，不在本 op 辖域。

**宪法③核验**：`CwActionOpenBookcardParam` 现无名称语义字段（无 item_name/char_name 形态，:590-606 仅 slot/route_tag），本批**零新增**——宪法③对本 op = 空集成立。记账面名称消费逐处核验：`write_logic(produced_by='CwActionOpenBookcardParam')` 为常量类名字符串（:54），非参数名称字段；腾位写 empty 无任何名称读取——空集结论双面（参数面/记账面）成立。

**总契约三条在槽位键域的形态**：①反查时序——记账 = 上报时点槽位表现读，单动作决策环现算契约辖域（entry 每动作重 decide，同帧同容器），无坐标伴随域刷新时序面；②陈旧窗口——bench 槽位表恒稳（腾位置 empty 不移位，词表坐标系声明同族口径），无窗口；bookcard 无跨帧队列消费面（`_consumable_open_action` 每帧现算现发，非 yield plan 持有形态）；③唯一性——slot ↔ 槽位一一对应（定长槽位表结构性保证，无表形态）。

**上报层改造裁决：非「零改造」，改一处死代码 + docstring，零行为变化面按下表核验。** `open_bookcard.py:65-67` None 现算分支随 §1.1 废除裁决删除（`_idx = int(param.slot) - 1` 直取）——保留它 = 留一条「上报层绕过 op 独立现算」的静默兜底路径：直调驱动若构造 slot=None 直接调上报函数，会算出与任何点击都无关的槽位写账（恰是冻结宪法禁的兜底形态，也是审计 bug 的第三副本）。删除后「bookcard kind → 槽号」现算全仓收敛决策层单点（§1.1 论证 4）。

**零行为变化核验表**（上报函数改造的等价性义务）：

| # | 面 | 现值 | 判 |
|---|---|---|---|
| 1 | 唯一消费方 | grep 全仓：`report_action_open_bookcard_param` 消费 = op 直调单点（`cw_open_bookcard_action.py:22,134`）；商店序列驱动器/回放驱动器/sim 直调零命中（bookcard 备战域动作，两驱动器辖域 = 商店序列） | 改造无第二消费面断裂 |
| 2 | bench 腾位写形状 | kind 'bookcard' → empty 整表替换单笔（:71-73） | 零变化 |
| 3 | 拒单形态 | `bookcard_slot_missing` 拒单零写零声明（:68-70）；reason 词表零变更 | 零变化（消费面新增 = op detail 透出，函数本体不动该分支） |
| 4 | bench_unobserved 早退 | applied=True + 声明（:57-63） | 零变化（applied=True 不进拒单 detail——家族形态按 applied 分流） |
| 5 | overlay 登记 | expert_invite 直登（:74-82） | 零变化（sim 懒呈现位/实机外循环分发两消费链不动） |
| 6 | WorldDecl | 纯转移 trigger=''（:37-38）+ op 侧 `declare_world` 喂入与 `data=world_decl` round data（op :130-140）——journal 记账面既有行为 | 零变化（逐位保留） |
| 7 | None 分支可达性 | None 输入仅来自「词表缺省/直调空 dict」两形态，均经 op 守卫拦截于上报之前；生产 journal 面自 2026-09-19 发出点迁策略器起恒显式 slot（词表 :598-601 既有申报） | 死分支删除零行为差、零历史序列化断链 |

### 1.3 交替机制：开浮层 aftermath 对 `owned_equip_xy` 零交集，`cw4_equip_xy_pending` 零置位端、零机制改动

**推演（MoveUnit 稿 §1.3 格式）**：开卡腾位写的是 bench 槽位表 kind 位（bookcard → empty），装备库存网格是独立面板区、备战席占用变化不驱动其布局，且本上报零 `gs.equips` 写端（§1.2 无库存变化核验）→ 零库存增删 → 零网格 reflow → `owned_equip_xy` 坐标恒新鲜。**结论：`cw4_equip_xy_pending` 置位端不加开卡点；本批零标志机制改动**（现役置位端 = 穿装发出点 mandate M7 + entry 第 7 步、工具原子发出点 entry 第 7 步，不变）。附带辨析：SellDeployed 稿 §9 行 2 的 A1 收编面把 OpenBookcard 列入「获得类」清单——按本批上报函数核验，开卡自身 aftermath 零 append（获得发生在后续选卡动作 PickExpertInvite），即便 A1 回退批统一收编置位端，本 op 也是零贡献成员，两批申报不冲突。

### 1.4 拖点分域与点击形态：守卫上界迁移 op 内现读（`_bench_pts` 剩两消费，非退役批）；点击目标 = 单击族建档直查，与拖拽原语**不同构**

**守卫上界（`_bench_pts` 消费侧迁移）**：现状 `ex._bench_pts` = 执行器构造期缓存（`prep_actions.py:361`，构造时 `row_area_centers(ctx,'备战栏')` 读一次），本 op 消费 = 表长做 slot 守卫上界（op :78/:84）。迁移 = SellBench 稿 §1.3 预裁的同式：op 内执行期现读 `row_area_centers(self.ctx, '备战栏')`（缺省备战画面档）——executor 构造期缓存 → op 执行期现读同一静态档，值理论逐位同。bookcard 单域备战画面，无 SellBench 的 screen_name 域分派问题（SellBench 稿 §1.3 既有明示）。**`_bench_pts` 非退役申报边界**：本批迁走 bookcard 后，`PrepActionExecutor._bench_pts` 现役消费者剩两个——`cw_open_box_action.py:77,83` 与 `cw_open_tome_action.py:74,80`（开件守卫同族）——**保留属性本体，物理退役 = 开件族最后一件迁移批**（届时与 `_front_pts/_back_pts/_drag` 零消费复活遗留合流清场，§9 申报行 1/2）。本批注释收口一处：`prep_actions.py:357-360` 「开件三类守卫(其迁移批退役)」收窄为「开件两类守卫(OpenBox/OpenTome,各自迁移批退役)——OpenBookcard 已随其参数面迁移批改 op 内现读」。

**点击目标形态（任务题 4 对照裁决）**：本 op 机械本体 = **单击**「备战栏-{slot}」槽位本体中心弹浮层——与 SellBench/MoveUnit 的拖拽原语（`drag_char_guarded`：失焦守卫 + `DragCwChar.drag_char` 中心拖 hold0）**不同构**：交互机制是 click 不是 drag，拖拽原语的整族构成（拖前 settle/drag_to/落点 park）无对象可套。本件现役单击链 = `mouse_move(center)` 防吞点击 + `click(center)`（op :113-116，与 OpenBox :111-114 / OpenTome :108-111 / CollectOre :78-79 / LevelUp :109-111 同族口径）——**保留现役单击族形态，零新原语、零 drag_char_guarded 消费**。坐标值核验：`area_center(ctx, f'备战栏-{slot}')` 直查同名 area 中心（`cw_obs_core.py:67-74`），与 `row_area_centers` 裸中心派生式同值同源（同 rect.center）；**不并入 pts[slot-1] 直取**——点表下标在 area 族有缺档时会静默错位（`row_area_centers` 跳过非连续编号后按序压缩，`prep_actions.py:177-184`），`area_center` 按名直查缺档自然异常（零防御既有口径），点名单槽场景按名直查比按位取表更防建档漂移误点——两读并存（守卫读表长、点击读单名）为有意形态非冗余，申报在此。`row_area_centers` docstring 的拖点权威分域申报（角色拖动族/装备 icon→角色卡族，:164-170）是**拖点派生式**辖域，本 op 无拖拽交互不涉——零新增分域声明。

### 1.5 env 缺省化与零 env 消费（家族单域标准形态）：executor/ledger/screen_name 三无

裁决：签名改 `env: PrepExecEnv | None = None`，op 体**零 env 消费**（MoveUnit/SellDeployed/穿装/工具家族形态，非 SellBench 双域元数据形态）——bookcard 单域备战动作：无域坐标权威画面分派需求（单档，`row_area_centers`/`area_center` 缺省备战档即全量正确）、无访问账（无 ledger 概念）、无 executor 点表/`_ctx` 依赖（§1.4 已自持化）。env=None 缺省 = MCP 直调合法形态；`PrepExecEnv.executor` 本就 `| None` 可缺省（`prep_actions.py:319`），注册表构造路径（`_dispatch_action :467-469` / `action_op_for :256`）恒传完整 env 兼容不动。对照 SellBench 的「两处元数据保留」偏离：bookcard 无双域事实即无偏离——家族两形态各按域事实自然分流，本件归零消费档。

### 1.6 sim 形态自洽：gate 归位（点击+睡眠同 gate），两执行面同源单点

1. 机械 gate：现状点击已 gate（:114）、睡眠未 gate（:120-123 无条件）——迁移后 `mouse_move+click+sleep` 全段收进 `mechanical_io_allowed()` gate（SellBench op :120-127 同构）。sim 局开卡帧从「op 睡 1.8s + 终结口 wait 1.8s」双层变「终结口 wait 1.8s」单层（行为变化申报 §7 条 3）；实机双层保留零差异。
2. 期望态推进：上报函数族两执行面同源——op 直调是唯一消费面（§1.2 核验表 #1），sim 局经同一 op 路径走同一上报函数；`declare_world` 未装配 no-op / 装配后 advance（`cw_sim_ports.py:242-252`），拒绝出口 `world_decl=None` 喂入被端口层直返吞掉（:250）——喂入行恒写、语义由端口层分流，家族既有形态保留。
3. overlay 登记 expert_invite → sim 懒呈现位消费链零变化（登记在上报函数内，两执行面同一行代码，action-op.md L107 既有）。
4. 直调路径：MCP `run_operation` 传 `{"slot": N}` → 守卫闭合域内机械（sim 环境 gate 静默）/实机点击 + 上报；传非法值 → 守卫 AssertionError 零点击（模拟与实机同守——守卫在 gate 外，家族形态）。

## 2. 新参数面定稿

### 2.1 字段集变更（`kernel/cw_vocab.py::CwActionOpenBookcardParam`，:590-606 现值）

**零新增、零删除字段**——`slot` + `route_tag` 两字段保留；变更 = `slot` 必填化：

- `slot: int`（去 `| None = None` 缺省，必填第一位）：[索引定义] 注释三要素——坐标系 = 备战栏画面物理槽位 1 基（area 序，坐标参数化机械动作族同系）；取值时机 = 生成期快照（决策半 `_consumable_open_action` 按 gs bench kind='bookcard' 槽位现算，`entry.py:555-558` 单一现算点；直调 = 当帧 extras bench.slots 同口径）；写入端 = 发出点。None 语义废除申报一句（§1.1 指针）。
- 类 docstring 更新：「slot=None → 第一张书册卡」句删除（:601），替换为必填申报 + 记账路径总契约第六适用者申报（腾位直址写零反查退化形态 + 宪法③空集）+ 直调传参指引（extras bench.slots kind='bookcard' 下标+1）。
- `route_tag`（kw_only + `action_key_exclude`）不动。
- 补 `from_dict` classmethod：共享 `cw_vocab.action_param_from_dict`（:610-618）一行委托（MoveUnit/SellDeployed/SellBench 家族同款）。最小 dict = `{"slot": 1-9}`；缺 slot 键 = `cls(**…)` 缺参 TypeError（构造面显式报错，禁在 from_dict 加缺省兜底——共享形态单一源，不为本件开例外）。
- `action_key` 幂等键零变化：`slot` 入键（行为参数，正确——同槽位同动作），`route_tag` 不入键（既有 metadata）。词表 `action_key` docstring 失配为本批零触及面（§9 申报行 3）。
- 词表模块头 :12 「(开件三类 OpenBox/OpenTome/OpenBookcard):row/slot 字段按定义 = …」句辖域核验：三类字段定义仍在（箱/典籍未迁），仅 bookcard 必填化——句子保留、bookcard 类 docstring 内单独申报差异。

### 2.2 守卫断言（op 内，校验落点契约 = action-op.md L55；全部 `raise AssertionError` 响亮暴露，禁兜底坐标/禁负下标回环）

两形守卫（对比 SellBench 单形——多 None 形，因本件 None 有废止申报义务）：

1. **None 形（新增）**：`action.slot is None` → 断言，文案带契约指引：`CwActionOpenBookcardParam slot 必填(备战栏物理槽 1-9 基 1;直调按当帧 extras bench.slots kind=bookcard 槽下标+1 传;slot=None 现算语义已随参数面迁移批废除,现算归发出点 entry._consumable_open_action)`。**有意较 SellBench 的 `int(bench_idx)` 自然 TypeError 形态加强**：None 废除是审计挂号 bug 的修法本体，拒绝信息必须自教新契约（TypeError 只会说 NoneType 不可整型化，不指向参数面）；「缺席守卫断言」= action-op.md L22 限定域申报明文形态（缺席与越界同款守卫）。
2. **越界形（改源保留）**：`not (1 <= int(action.slot) <= len(pts))` → 断言（`pts` = op 内现读 `row_area_centers(self.ctx, '备战栏')`；下界显式闭合禁负下标回环；文案带词表参数语义与合法域 + 画面档定位，SellBench op :117-119 同构）；空点表（len=0）命中同一断言 = 建档漂移哨语义（SellBench 稿 §1.2 论证 4 同判），不设独立分支。守卫在 `mechanical_io_allowed()` gate 外（sim/实机两执行面同守）。

**零 gs 读声明**：机械路径（守卫 + 点名直查 + 点击 + 等待）零 `game_state_from_ctx` 消费——自上报取容器 = 上报路径非机械定位（SellDeployed 稿 §4 既有同款裁定）；宪法①修复完成（本批实质修复项，对照 SellDeployed 稿 §7 条 6「形态修复非声明」判据，本件是修复+声明双真）。

## 3. 牵涉面清单（逐文件；grep 全量已核，行号 = HEAD b87bf023d）

> 路径根 = `src/sr_od/application/currency_war/`。

### 3.1 `kernel/cw_vocab.py` — §2.1：slot 必填化 + from_dict + 类 docstring 三节改写

### 3.2 `operations/cw_op/cw_open_bookcard_action.py` — op 执行体重写

机械自持：None/越界两形守卫（§2.2）→ `area_center(self.ctx, f'备战栏-{slot}')` 建档直查（零防御口径保留：缺失 = 点击消费点自然异常）→ sim gate（点击 + `time.sleep(_OVERLAY_ANIM_WAIT_S)` 同 gate；`_OVERLAY_ANIM_WAIT_S` 函数内局部 import 形态保留不动）→ `self.ctx.controller.mouse_move + click`（防吞点击口径逐字沿用）→ log（detail 携带）→ 自上报：`gs = game_state_from_ctx(self.ctx)`；`gs is None` = 无处记账跳过（outcome=None，detail 不加拒单段，`declare_world` 与 round data 同跳——gs 缺席即无声明载体，既有行为保留）；`outcome = report_action_open_bookcard_param(gs, action, ChannelSig(family='logic_action', actor=type(self).__name__, mode='compute'))`；`world_decl = outcome.world_decl` + `cw_sim_ports.declare_world(world_decl)` + `round_success(detail, data=world_decl)` 逐位保留；`outcome.applied=False` → detail 追加 `；记账拒单:{reason}(点击已发生,账未落)`（家族 M-r3-1① 同形，动词按交互形态换「点击」）。删除面：`replace` import（:15，None 分支专用）、`_BOOKCARD_BENCH_KIND` 常量与三处现算注释（:37-42）、`ex` 全部窥探。签名改 `env: PrepExecEnv | None = None`（TYPE_CHECKING import 保留供注解）。docstring 重写：模块头与类 docstring 按家族参数面迁移形态行文（起终点行沿用 :47 现骨架；终结动作/terminal_wait=1.8 类属性与等价注释 :52-57 零改动；参数面指引 = slot 直调 extras 口径 + 必填双出口报错申报；直调指引 = run_operation `{"slot": N}`、env=None 缺省备战档；记账总契约第六适用者 + 拒单禁补点口径——拒单 = 腾位账未落，处置 = 交还决策循环重读板面重派，禁补点）。

### 3.3 `kernel/cw_action_report/open_bookcard.py` — None 分支删除 + docstring 同步（§1.2）

`:65-67` 改 `_idx = int(param.slot) - 1`；函数 docstring 补 slot 必填申报与三处现算收敛声明。其余逐位不动（核验表 §1.2）。

### 3.4 `prep_actions.py` — 死桩删除 + 注释收口两处；点表属性本体零改动

- `_open_bookcard` 方法删除（:485-494；零消费 grep 背书，保留理由所引测试已不存在——§0 债表末行）。
- 模块头桩注记句更新（:42-43）：「八桩零调用已删,``_open_bookcard`` 因单帧测试直调面保留」→「九桩零调用已删(_open_bookcard 随其参数面迁移批删除——其保留理由所引单帧测试已不存在,全仓零消费)」。
- `_bench_pts` 边界注释收口（:357-360）：「开件三类守卫(其迁移批退役)」→「开件两类守卫(OpenBox/OpenTome,各自迁移批退役)——OpenBookcard 已随其参数面迁移批改 op 内现读并废除 slot=None 现算」。
- `_bench_pts/_front_pts/_back_pts` 属性本体、`row_area_centers`/`area_center`/`_OVERLAY_ANIM_WAIT_S` 原语本体零改动；`_front_pts/_back_pts/_drag` 零消费复活遗留**不碰**（退役债务重开已挂号归 SellDeployed 收尾小 commit，进度.md:40 ⑤，§9 申报行 2）。
- ⚠️ 在飞申报：本文件当前 HEAD 干净（不在工作区 M 列表），实施时复核；绝不卷入并行批改动行。

### 3.5 发出面 `strategies/impl/mandate_v1/entry.py` — 零改动（§1.1 迁移申报：`:555-558` 已显式传 slot；`_TRUNCATION_POINTS :148-153` 含本类零变化）

### 3.6 `operations/cw_op/cw_action_registry.py` — 零改动

import（:89-91/:47）与注册行（:181）类名不变；组装恒传 env（`action_op_for :256` / `_dispatch_action`）兼容缺省化。注册完备测试机械约束对象不变。

### 3.7 `operations/cw_screen/cw_screen_prep.py` + `cw_screen_expert_invite.py` — 零改动

终结口 OpenBookcardOp 分支（:949-954，`wait=op_cls.terminal_wait` 消费类属性）与入口 docstring（:743-745）零变化；expert_invite 画面 op 对 bookcard 词表链的引用 = docstring 指针面（:5/:11/:119/:138），零代码耦合。

### 3.8 `telemetry/match_archive.py` — 零改动

OpenBookcard 零序列化面（grep 零命中——无字段枚举注释、无解析函数，对照 SellDeployed 稿 §3.8 的存在面）。

### 3.9 测试仓镜像测试 — 见 §5

### 3.10 文档面 — 见 §8

## 4. op 执行语义（迁移后）

1. None 守卫 + 越界守卫（§2.2，gate 外——两执行面同守）。
2. 点击点静态直查：`area_center(self.ctx, f'备战栏-{slot}')`（零截图零识别零 gs；缺失 = 自然异常，零防御既有口径）。
3. sim 分支：`mechanical_io_allowed()` 为假 → 机械段（含固定动画等待）静默跳过（上报函数族照走——sim 期望态推进 = 自上报单点，两执行面同源）。
4. 实机机械段：`mouse_move` 防吞 + `click` → `time.sleep(_OVERLAY_ANIM_WAIT_S)`（1.8s 开卡动画等待，gate 内，值逐字沿用）。
5. 自上报：腾位 + expert_invite 登记 + 纯转移声明（上报函数单点）→ `declare_world` 喂入 → round data 携声明（journal 记账面，既有行为逐位保留）。
6. round 结果：恒 `round_success(f'开书册卡槽{slot} ✓(发出即记账,落地归观察对账)', data=world_decl)`（机械成功语义；零 round_fail 通道，回执受阻码表零变更——detail 文案升级判读申报 §7 条 1）。

**决策侧参数现算契约适用申报**：本 op 发出域 = 备战决策环（entry ① 卡片分支 + 第 0 步自救态 2 共用 `_consumable_open_action`，每动作重 decide、同帧承诺成立——slot 现算与执行同帧同容器）。无跨帧队列形态（非 yield plan 持有动作）、非战斗链批量发射辖域（发射集 = MoveUnit）。**终结动作语义保留**：terminal=True + terminal_wait=1.8 类属性零改动，弹专家邀请函 = 新事实交回主循环分发 `CwScreenExpertInvite` 选卡（外循环链零变化）。

## 5. 测试设计（sr-od-test，按 AGENTS.md §11.4 harness 规范；镜像路径，命名无批次号）

> 现场实态：CW 域测试源文件部分仅在 `__pycache__`（SellDeployed/SellBench 稿 §5 同款申报）——实施角色按仓内实态落位。sr-od-test 现存 OpenBookcard 相关测试零命中（grep 已核），全部按下述路径新建/扩展。

1. `test/sr_od/application/currency_war/kernel/cw_vocab/test_cw_vocab.py`（既有文件扩展）
   - OpenBookcard `from_dict`：最小 dict `{"slot": 5}` 逐字段断言（`route_tag=''`）；未知键忽略；**缺 slot 键 = TypeError**（必填锁测——废除 None 的构造面出口）；`{"slot": null}` 可构造（None 拦截归 op 守卫——构造面不做类型校验的家族口径锁测）。
   - `action_key`：slot 不同产不同键；`route_tag` 不入键。
2. `test/sr_od/application/currency_war/operations/cw_op/test_cw_open_bookcard_action.py`（新建；harness 剧本，结构照 `test_cw_prep_sell_bench_action.py` 夹具形态：controller 记录 stub + monkeypatch 防污染 + screen_info 真档案同源派生期望值）
   - **None 守卫锁测（审计 bug 修复锁）**：`slot=None` → AssertionError（文案含「必填」与废除申报关键词）且点击记录零条目（迁移前该形态走 gs 现算分支，迁移后响亮拒绝——本批核心行为变化的回归锚）。
   - 守卫：slot=0 / 负值 / 越界（≥10）→ AssertionError 零点击（负下标回环防锁）。
   - 实机形态（真档案派生）：点击记录 `== 备战栏-N rect 中心`（裸中心同源锁测，`_expected_center` 同式）；mouse_move 先于 click（防吞口径顺序锁测）。
   - **round detail 拒单码**：种子使 gs bench 该槽 kind='empty'（决策陈旧帧模拟，机械面不读 gs、点击已发）→ round_success 且 detail 含「记账拒单:bookcard_slot_missing(点击已发生,账未落)」；正常帧（kind='bookcard'）detail 无拒单段 + 断言 gs bench 该槽变 empty（腾位记账锁测）+ expert_invite 登记在场（overlay 登记锁测）+ round data 携 WorldDecl（next_screen='货币战争-备战'，trigger=''——转移声明锁测）。
   - gs 缺席帧（无 session 种子）→ 机械已发 + 零上报零声明零异常（无处记账跳过形态锁测）。
   - `env=None` 全链跑通；sim 形态（port 关闭 → 点击记录零条目 + 自上报照走）；`with fast_sleep(): op.run()`。
3. `test_prep_actions.py`（既有面）：`_open_bookcard` 桩删除后零引用锁测无需新增（全仓零消费 grep 即背书）；既有面零改动预期。
4. `test_action_registry.py`（既有面）：零改动预期（terminal=True/terminal_wait=1.8 类属性不变）。

验收阶梯（skill §3）：L1 → L2（点名新增文件 + test_action_registry + test_prep_actions）→ L3 全量 commit 前。**实机验收序列 = §11**。

## 6. sim 形态自洽结论

**结论：零 sim 改动。**

1. 机械段：gate 归位（§1.6）——sim 局与实机同跑同一循环/op/策略，上报函数族两执行面同源直调同一函数（op 直调唯一消费面，§1.2 核验表 #1；无驱动器第二消费面需对齐）。
2. 期望态推进：腾位记账 = 槽位表直址写（无伴随域依赖、无反查），sim 形态与实机同核零分叉；`world_decl` 喂入行恒写、端口层分流（未装配 no-op / 装配 advance），拒绝出口 None 被端口层吞掉——家族既有形态零改动。
3. overlay 登记：expert_invite 直登在上报函数内（两执行面同一行代码），sim 懒呈现位/外循环分发消费链零变化。
4. 直调路径：`{"slot": N}` 在 sim 环境 = 守卫通过 + 机械静默 + 上报照走（round detail 可核）；非法值 AssertionError 两执行面同炸（守卫在 gate 外）。

## 7. 风险与行为变化清单

1. **行为变化：round detail 文案升级 + 新增拒单段**（outcome 消费）——journal 判读面从「开书册卡槽N」变「开书册卡槽N ✓(发出即记账,落地归观察对账)」，拒单帧新增「记账拒单:bookcard_slot_missing(点击已发生,账未落)」段（现役生产不可达——决策同帧现算下槽态不失配；可达面 = 直调错传/陈旧直构）；遥测分键零新增（reason 词表封闭不动），首局对照判读申报。
2. **行为修复：slot=None 语义废除（审计挂号 bug 本体）**——直调缺 slot/传 null 从「op 内 gs 现算双出口 AssertionError（报错点脱节 + 机械路径已读 gs）」变「构造面 TypeError / op 守卫 AssertionError（零点击零 gs 读，文案指向参数契约）」——fail-fast + 宪法①修复双真；生产发出面零变化（§1.1 迁移申报表）。判读申报：直调报错形态变化，排障时按新报错文案对参数面。
3. **行为变化：sim 局开卡帧零白睡 1.8s**（sleep 进 gate）——sim 批量局效率改善（开卡 = 每书册卡一帧，频率低于卖出族，收益同方向）；实机零差异。
4. **宪法①修复：机械路径 gs 读拔除**——None 形态固有的「现算结果随帧漂移」风险面消除；守卫只判参数合法域，不再间接触碰观察态。
5. **坐标等价性**：守卫上界（`row_area_centers` 表长）与点击点（`area_center` 同名 area 中心）同源同档零变化；坐标源路径变化（executor 构造期缓存 → op 执行期现读）理论零差，实机落点核对 = 背书义务（§11 验收①）。
6. **死代码退役两件**：`_open_bookcard` 桩删除（零消费 grep 背书；若后续考古发现隐匿消费面，该消费面本就该走注册表分派——桩的存在本身是旧接缝）；上报层 None 分支删除（唯一消费方 = op，核验表背书）。
7. **交替机制零改动**（§1.3）：开卡 aftermath 零 `gs.equips` 写端为上报函数现值事实，游戏版本若引入「开卡直得装备」类机制，该面随版本适配批重新核验，本批不预设。

## 8. 文档与 skill

- `skills/sr-od-dev-currency-war/references/flow/prep-contract.md`（**实施批落地**——本稿点名逐节内容，文档随实施 commit 落保正本与代码现状一致；该文件当前 HEAD 干净已核，实施时复核）：§1 L9 动作字段坐标系段——开件三类句拆写：OpenBookcard 标注「已随其参数面迁移批 op 自持守卫 + slot 必填化（None 废除）」，箱/典籍标注「过渡期仍经执行器点表（各自迁移批退役）」；§3 L27 坐标参数化机械动作取值时机段——补 OpenBookcard 行句（slot = 生成期快照必填，决策半 `_consumable_open_action` 单点现算，None 语义废除）；§6 G1 活缺口——辖域收窄句更新（「现役辖域收窄为开件族箱/典籍」——bookcard 已随批补防线：必填参数 + 决策单点现算，脱离 G1 辖域）；G2 不涉（bookcard slot 链不走 obs `read_*` 族 slot_idx 面——决策层走 gs bench kind 扫描）。
- `skills/sr-od-dev-currency-war/references/flow/action-op.md`（**收尾义务，本批不动**——b87bf023d 刚落库该文件，实施/收尾角色执行）：§5 备战族 OpenBookcard 行（L131）改写——现值行文「`find_bookcards` 识别 → 点槽中心」是 open-actions-mechanical-pure 批之前的过期描述（现役 op 零读屏，状态容器槽位直点形态），改写为参数面迁移后终态（守卫 op 内现读/slot 必填/None 废除/记账拒单 detail/env=None/总契约第六适用者/终结形态保留）；§1 记账路径总契约条款批次计数推进（「已迁五批」→「已迁六批」+ 本 op 逐 op 差异附记：槽位键域零反查退化形态 + None 语义废除 + 三处现算收敛决策层）；§2 备战域动作全集行（L61）——`OpenBookcard(slot)` 签名不变零改动，但该行缺枚举 OpenBookcard（连同 WearEquip/工具七类），文档清单缺口归收尾批顺带核补（§9 申报行 5）。
- `skills/sr-od-dev-currency-war/SKILL.md`：零改动（§1.4 参数面规范三分法与本批形态一致；工作区 M 状态的在飞修改不碰）。
- `docs/develop/sr_od/application/currency_war/game_state/fields.md`：零改动（零 gs 字段变更；`bookcard_slot_missing` 为既有 outcome reason 非回执受阻码，词表零变更）。
- 玩家 skill `skills/sr-od-currency-war/`：零改动（开件族非玩家直调面；`run_operation` 直调 = 开发者/单件会话形态，op docstring 自足——MoveUnit/SellDeployed/SellBench 批同款裁定）。
- sim-design.md：零改动（零 sim 行为变更；§6 自洽结论不新增申报行）。

## 9. 申报行（相邻问题，本批不修）

1. **开件族另两件（OpenBox/OpenTome）待后续迭代**（用户裁定：每迭代只切一个 op）：两件与本件同构（None 语义 + `_bench_pts` 守卫 + area_center 单击 + env 必传 + 缺 from_dict + sim 白睡），**None 废除预期同判预裁定**（选项 B 同被宪法排除；同款两形守卫 + 上报层 None 分支退役——OpenTome 上报层同型分支在 `open_tome.py:44-45` 实证在档）；其余牵涉面 = 各自上报函数核验（OpenBox = zero_writes 上报落点形态另核）、`_bench_pts` 最后消费者判定与物理删除、G2 obs docstring 基声明（prep-contract §6，箱/典籍辖域）随收官批收口。
2. **bookcard 修复与开件族退役路径联动**：本批迁走 bookcard 后 `_bench_pts` 剩 OpenBox/OpenTome 两消费（§1.4 边界申报）——物理退役 = 最后一件迁移批，届时与 `_front_pts/_back_pts/_drag` 零消费复活遗留（T 系列重整批归还态，现役零 op 消费 grep 实锤；退役债务重开挂号 = 进度.md:40 ⑤，归 SellDeployed 义务收尾小 commit）合流清场；`cw_screen_prep.py:181,212-213` 观察侧同名 `_bench_pts` = 同名异物（观察域私有惰性缓存），收官批删 executor 属性时以 SellBench 稿 §9 行 9 + 本行辨析为防误伤依据。
3. **词表 `action_key` docstring 与实态失配**（已挂号）：docstring（`cw_vocab.py:1305-1310`）称「现役 = CwActionSellBenchParam.reason 卖出归因不入键」，实态 `CwActionSellBenchParam.reason`（:228）无 `action_key_exclude` metadata（入键）——SellBench 稿 §9 行 4 同勘误延续，挂号面 = 流水线总遗留账⑥（进度.md:40）词表域批量契约批；本批 `action_key` 机制零触及，OpenBookcard 侧 slot 入键/route_tag 排除均正确无失配。
4. **Pick* 族清点状态**——既有登记（跨迭代挂账板「动作 op 规范违例清偿」#8②：pick 族坐标源过渡态收敛目标 = 状态容器坐标伴随域；MoveUnit/SellDeployed/SellBench 稿 §9 各行延续），非本批。
5. **action-op.md §2 L61 备战域动作全集行缺枚举**（OpenBookcard/WearEquip/工具七类不在行内）——文档清单缺口，归收尾义务批随 §5 行改写顺带核补（§8 已点名）。
6. **单击族无失焦守卫家族现状**——开件三类/CollectOre/LevelUp/StartBattle/bookcard 裸 controller 点击，无 `drag_char_guarded` 同构失焦守卫（该守卫实证辖域 = 拖拽输入静默丢，单击无实证）；若未来实证单击输入同病，守卫宿主化归单击族专项，本批零改动。
7. **bench_unobserved 早退形态**（applied=True + reason 非空 + 声明，`open_bookcard.py:57-63`）——生产不可达申报保留；直构/离线形态可达且不进拒单 detail；若未来收紧为拒单语义归记账拒单域批（OpenTome 同型），非本批。
8. **三刷新建议动作/开店编排等注册表外执行体**与本批零交集（bookcard 在注册表内），清点申报防漏。

## 10. 实施顺序建议（给实施角色）

1. `cw_vocab.py` param 必填化 + from_dict + docstring（§3.1）。
2. `cw_open_bookcard_action.py` op 重写（§3.2/§4）。
3. `cw_action_report/open_bookcard.py` None 分支删除（§3.3）→ `prep_actions.py` 桩删除 + 注释收口（§3.4）。
4. 测试（§5）→ 文档（§8；prep-contract 同批落）。
5. MCP server 重启 → `describe_operation_flow` 核对 op 节点图（恒 round_success 单节点形态）→ `list_operations`/`describe_operation` 核对反射参数面（slot required + env 缺省）→ 实机验收序列（§11）。

## 11. 实机验收序列（给实施角色）

1. **点击落点与腾位核对（§7 条 5 义务）**：备战画面开一书册卡（决策自然触发或直调）——点击落点 = 书册卡槽中心；下一帧实读：专家邀请函弹窗在场（外循环分发 `CwScreenExpertInvite`）、bench 该槽腾空、零金变零库存变（腾位直址写旁证）。
2. **直调单件会话**：run_operation 跑 `CwActionOpenBookcardOp`（from_dict 通道，env=None，`{"slot": N}` 按当帧 extras）一例，核对 round detail 与落位；**废除形态一例**：缺 slot 键（构造面 TypeError）与 `{"slot": null}`（守卫 AssertionError）各一，核对报错文案指向参数契约。
3. **拒单形态一例**（如可安全构造）：直传与板面不符的 slot（指向空槽）→ 点击已发 + detail 含「记账拒单:bookcard_slot_missing」段 + 零写账——核对后交还决策循环重派，不补点。
