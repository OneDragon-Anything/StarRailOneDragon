# CwActionOpenTomeOp（开星徽秘典）参数面迁移设计稿（r1）

> 迭代：CW 动作 op 迁移流水线 · 设计角色产出（开星徽秘典 op 批 = 第七棒，开件族第二件）。
> 上批 = 开书册卡 OpenBookcard（changes/open-bookcard-param-surface/design.md，**同族最近先例与同判基准**，已落地 commit 70b2e1f15 + 测试仓 7c177a0d）；第五棒 = SellBench（d3ea8719b）；第四棒 = SellDeployed（68199b48d）；第三棒 = MoveUnit（a09f30e8b）；第二棒 = 工具原子七类（76a94c27c）；首棒 = WearEquip（db4697e40 终稿）。
> **范围裁定（每迭代只切一个 op）**：本批只做 `CwActionOpenTomeOp` 一件——开件族第二件。slot=None 同型已获两处预裁定：工具批预裁定 `open_tome.py:44-45` 在档（流水线账本 `.debug/progress/2026-11-17-cw-mcp-ops-extraction/进度.md:44`）+ bookcard 稿 §9 行 1 同判预告。本稿 = **同判应用 + 轻量化**：与 bookcard 同判的部分标注「同判应用，见 open-bookcard 稿 §N」不再重复论证，本稿价值在差异点（秘典 kind 字段 / 非转移动作零声明 / 非终结交接路径 / sim 无呈现面消费链）。
> 冻结宪法（穿装批成文）：①动作 op 执行路径零 gs 依赖；②参数面三分法；③名称字段 = 语义参数（机械面与记账面均零消费）；④坐标新鲜度纪律归调用方；⑤参数 dataclass 统一补 `from_dict`；⑥gs 给实体记录坐标；⑦每个 op 一个迭代，牵涉面一次改净。
> **记账路径总契约第七适用者**（正文 = `skills/sr-od-dev-currency-war/references/flow/action-op.md` L32「记账路径总契约」条款）：记账键 = 槽位下标，腾位直址写（kind 'tome' → empty）零身份反查——bookcard 同族同判的槽位键域退化形态（§1.2）。
> **行号基准声明**：本稿全部行号基于写稿时 HEAD `57403b744`（全 hash `57403b7449c244bea49fee5de14809cc37e4b8a3`）。任务书下发基准 `70b2e1f15` 与 HEAD 之间仅隔 `57403b744` 一笔，经 `git show --stat` 核验为纯 docs 提交（13 文件全 .md 零 .py），本稿全部 .py 行号对两基准逐位同，引用均已按 HEAD 实读自核。⚠️ **工作区并行批在飞申报**：工作区有未提交改动（`data/affix_effects_data.py`、`currency_war_battle_prep.yml` 等四份画面档、SKILL.md 与四份 skill references——另一装备广场系批的工作现场）。在飞备战档 diff 经 `git diff | Select-String '备战栏'` 核验**零命中**，本稿「备战栏-N 在档」结构事实不受影响；本稿全部引用文件（op/词表/上报层/prep_actions/entry/注册表/画面 op）均不在工作区 M 列表（HEAD 干净已核），实施角色动任何文件前复核该批落库状态，绝不卷入在飞改动行（对齐 bookcard 稿 §0 同款纪律）。

## 0. 本批范围

`operations/cw_op/cw_open_tome_action.py::CwActionOpenTomeOp` + 词表 param `CwActionOpenTomeParam` + 上报层调用面（`kernel/cw_action_report/open_tome.py` None 分支退役 + op 侧 outcome 拒单消费）+ 全部引用（grep 全量已核，§3）。

现状债（迁移动机，逐项对 bookcard 稿 §0 债表同构；行号 = HEAD）：

| 债 | 现值（HEAD） | 迁移形态 |
|---|---|---|
| **slot=None 硬 gs 分支（审计挂号 bug 同型，本批主轴）** | `cw_open_tome_action.py:82-104`：slot=None 时 op 机械路径中途 `game_state_from_ctx` 现算首件 tome 槽（宪法①违例本体）+ 双出口守卫断言（:88-90 gs 缺席 / :96-98 bench 无该 kind 首槽） | None 语义废除、slot 必填化（§1.1，同判应用）——现算收敛发出点 `entry._consumable_open_action` 单点 |
| 词表缺省值死角 | `cw_vocab.py:584` `slot: int \| None = None` | 必填化（§2.1） |
| 上报层 None 分支（工具批预裁定本体，`open_tome.py:44-46`） | `_idx = (int(param.slot) - 1 if param.slot is not None else next(...kind == 'tome'...), None)` ——上报层绕过 op 独立现算的第三副本 | 分支删除，`_idx = int(param.slot) - 1` 直取（§1.2） |
| 机械链窥探 executor 私有面 | `:73` `ex = env.executor`；`:74/:80` 读 `ex._bench_pts` 做守卫上界；`:108` 经 `ex._ctx` 取建档坐标；`:110-111` 经 `ex._ctx.controller` 点击 | op 机械面全自持：守卫上界 op 内现读 `row_area_centers(self.ctx,'备战栏')`，controller/ctx 走 `self.ctx`，零 env 消费（§1.4，同判） |
| 三处同型现算注释与模块常量 | `:35-39` `_TOME_BENCH_KIND = 'tome'` + 「三处语义必须一致，提取公共函数归另批」注释 | None 废除后三处收敛决策层一处，常量与注释随批删除（同判 bookcard 稿 §1.1 论证 4，「提取公共函数」债因对象消失自然闭合） |
| outcome 拒单不可见 | `:123-126` 上报返回值弃收——`tome_slot_missing` 拒单（`open_tome.py:47-49`）对直调方不可见 | `applied=False` → round detail 追加拒单段（家族 M-r3-1① 同形，§1.2） |
| param 缺 `from_dict` | `CwActionOpenTomeParam` 类体内零 classmethod（`cw_vocab.py:577-586`） | 共享 `cw_vocab.action_param_from_dict`（:632-640）一行委托 |
| sim 局白睡 1.8s | `:114-117` `time.sleep(_OVERLAY_ANIM_WAIT_S)` 在 `mechanical_io_allowed()` gate 外无条件执行（点击 :109-111 已 gate、睡眠未 gate） | sleep 移入 gate（bookcard op 现值 :122-131 家族形态），§7 条 3 |
| env 必传（无缺省） | `:56-57` 构造签名 `env: PrepExecEnv` 必传——MCP `run_operation` 直调不可达（backend 扫描面含 `sr_od.application`，op 类已在 `list_operations` 可见，env 形参 required 非 JSON 可构造） | 签名改 `env: PrepExecEnv \| None = None`（家族同款，§1.5） |

**本批比 bookcard 少一件死桩**：`prep_actions.py` 无 `_open_tome` 桩（grep 实锤：bookcard 批已删 `_open_bookcard`，箱/典籍两 op 自 open-actions-mechanical-pure 批起即直连注册表分派，无替身函数），桩删除面不涉本批。

## 1. 本批特有设计题裁决

### 1.1 slot=None 主轴裁决：None 语义废除、slot 必填化（同判应用，见 open-bookcard 稿 §1.1；本节只补本件证据）

**裁决：`CwActionOpenTomeParam.slot` 从 `int | None = None` 改为 `int`（必填无缺省）；op 守卫显式拒 None；上报层 None 现算分支随批删除；None 语义全链退役。** 裁决理由、选项 B 被宪法排除的论证、根层定位全部同判 bookcard 稿 §1.1（论证 1-4 逐条适用），本节不重复，只补本件 grep 证据：

- **生产构造唯一单点** = `strategies/impl/mandate_v1/entry.py:551-558` `_consumable_open_action` 三元组 tome 行（`:554` `('tome', CwActionOpenTomeParam, 'prep_tome')`）——`:558` 恒显式 `Emitted(atom_cls(slot=idx + 1), True, tag)`。grep 全仓 `CwActionOpenTomeParam` 构造仅此一处（其余命中 = 词表定义/union/清单、注册表 import+行、op 引用、上报层 `produced_by` 常量字符串，零第二构造点）。None 只活在四个死角：词表缺省（`cw_vocab.py:584`）、op 现算分支（op :82-104）、上报层 None 分支（`open_tome.py:44-46`）、MCP 直调空 dict——**废除 None = 生产面零改动、纯死角清理**（与 bookcard 同构）。
- **kind 字段值核实（任务点名项）**：秘典在 bench 槽位表的 `BenchSlot.kind` 值 = **`'tome'`**。三源互证：op 模块常量 `cw_open_tome_action.py:39` `_TOME_BENCH_KIND = 'tome'`；发出点 `entry.py:554` kind 键 `'tome'`；上报层判据 `open_tome.py:48` `slots[_idx].kind != 'tome'`。MCP extras 口径同值：`obs/recognizers/battle_prep_recognizer.py:451-454` `bench` extras 字段 doc 明示 slots 元素 `kind: unit/supply_box/tome/bookcard/empty`。**直调传参指引 = 当帧 extras `bench.slots` 中 kind='tome' 槽的下标 + 1**（与发出点同源口径；注意与 OpenBox 的 kind='supply_box' 不同串，第八棒传参指引勿串用本件口径）。

**迁移申报（双调用面覆盖，bookcard 稿 §1.1 表同构）**：

| 调用面 | 现形态 | 迁移后 |
|---|---|---|
| 流程发出面（entry `_consumable_open_action`） | `atom_cls(slot=idx + 1)` 显式传（:558） | **零改动**（已按必填形态传参） |
| MCP 直调面（`run_operation` from_dict 通道） | `{}` → slot=None → op gs 分支双出口 AssertionError；今日实际卡在更早一层（env 必传构造不了 op）——bug 形态不可达，废除 = 修复+打通一体（bookcard 稿同句式） | env 缺省化打通后：`{"slot": 1-9}` = 合法直调；缺 slot 键 = 构造面 TypeError；`{"slot": null}` = op 守卫 AssertionError（文案自教新契约，kind='tome' 口径，§2.2） |
| 单帧测试/离线直构面 | `CwActionOpenTomeParam()` 零参构造合法 | 零参构造 TypeError（§5） |

### 1.2 记账路径核验：腾位直址写 + overlay 登记 star_tome + **零转移声明**（总契约第七适用者，槽位键域退化形态）；上报层非零改造（None 分支退役），零行为变化面见核验表

**记账消费什么（`kernel/cw_action_report/open_tome.py` 逐段现值）**：

| 记账消费 | 现形态 | 名称/载荷来源 |
|---|---|---|
| bench 腾位写 | `slots[_idx] = BenchSlot(kind='empty')` 整表替换单笔（:50-52，evidence `proj_open_item_clear`）；槽越界/空位/类型不符 = `tome_slot_missing` 拒单零写零声明（:47-49） | 记账键 = 槽位下标（`int(param.slot) - 1`）；载荷 = 常量 empty（**零身份反查**——无回金、无装备回收、无 sold 内容，卖出族槽位反查的退化形态，bookcard 同档） |
| 浮层出现事实 | `register_screen_change(gs, 'star_tome', KIND_SCREEN_NAMES['star_tome'], source='s6_click@open_tome')`（:53-65）——点开直弹星徽四选一，登记与动作落地同点（action-op.md L107「开件直登族」①）。kind='star_tome' ∈ 封闭九类（`cw_overlay_register.py:37`），分发档名 = `'货币战争-星徽秘典弹窗'`（:51） | 封闭词表 kind 常量，非名称语义 |
| 转移声明 | **不构造 WorldDecl**（:53-58 注释自述「零画面转移语义」）——`LogicOutcome(applied=True)` 无声明（:66）。**与 bookcard 的结构性差异**：bookcard 构造纯转移 `WorldDecl(next_screen=node_screen_now(gs), trigger='')`（open_bookcard.py:37-38），open_tome 不在转移动作 18 集内（action-op.md L82 终表无 OpenTome 行、L105 明示），非转移动作 `world_decl` 恒 None、无喂入行（action-op.md L77） | —— |
| 早退形态 | bench 视图缺席 = `applied=True, reason='bench_unobserved'` 零写零声明（:38-42；生产不可达——bench 恒有开局种子 9 槽视图，仅测试直构/离线形态可达） | 既有申报保留，本批不动（bookcard 同型分支保留零改动同判，bookcard 稿 §1.2 表 #4） |

**无库存变化核验**：上报函数全文唯一状态容器写端 = `gs.bench`（:51）；零 `gs.equips`/`gs.gold`/零获得链调用 grep 已核——开典籍 = 纯腾位 + 浮层事实，选卡后果归 `PickStarTome` 独立动作（其上报 = `zero_writes.py:152-158` 消费 star_tome 登记 + 零写，选卡侧零装备写端——星徽四选一给羁绊非装备，选卡消费族②同点消费）。

**宪法③核验（空集成立，双面）**：`CwActionOpenTomeParam` 现无名称语义字段（:577-586 仅 slot/route_tag），本批**零新增**；记账面名称消费逐处核验：`write_logic(produced_by='CwActionOpenTomeParam')` 为常量类名字符串（:34），腾位写 empty 无任何名称读取——参数面/记账面双面空集。

**总契约三条在槽位键域的形态**：逐条同判 bookcard 稿 §1.2（①记账 = 上报时点槽位表现读，单动作决策环现算契约辖域；②bench 槽位表恒稳无窗口、tome 无跨帧队列消费面——`_consumable_open_action` 每帧现算现发非 yield plan 持有；③slot ↔ 槽位一一对应，定长槽位表结构性保证）。零新增差异。

**上报层改造裁决：`open_tome.py:44-46` None 现算分支随 §1.1 废除裁决删除**（改 `_idx = int(param.slot) - 1` 直取，migrated bookcard 同款 `open_bookcard.py:68`）；保留它 = 留「上报层绕过 op 独立现算」静默兜底路径，直调驱动构造 slot=None 直接调上报函数会算出与任何点击无关的槽位写账（冻结宪法禁的兜底形态 + 审计 bug 第三副本，bookcard 稿 §1.2 同论证）。删除后「tome kind → 槽号」现算全仓收敛决策层单点。函数 docstring 补 slot 必填申报与现算收敛声明（bookcard 稿 §3.3 同构）。`:48` 的 `kind != 'tome'` 判据**保留**——那是记账拒单判据（目标槽须为 tome kind），非 None 现算，勿误删。

**零行为变化核验表**（上报函数改造的等价性义务，bookcard 稿 §1.2 表同构，差异行加粗）：

| # | 面 | 现值 | 判 |
|---|---|---|---|
| 1 | 唯一消费方 | grep 全仓：`report_action_open_tome_param` 消费 = op 直调单点（`cw_open_tome_action.py:20,123`）；商店序列驱动器/回放驱动器/sim 直调零命中 | 改造无第二消费面断裂 |
| 2 | bench 腾位写形状 | kind 'tome' → empty 整表替换单笔（:50-52） | 零变化 |
| 3 | 拒单形态 | `tome_slot_missing` 拒单零写零声明（:47-49）；reason 词表零变更 | 零变化（消费面新增 = op detail 透出，函数本体不动该分支） |
| 4 | bench_unobserved 早退 | applied=True 零写**零声明**（:38-42） | 零变化（与 bookcard 差异：bookcard 同分支带 `world_decl=_decl(gs)`，tome 无声明载体恒无构造，两件各按自身转移语义成立） |
| 5 | overlay 登记 | star_tome 直登（:53-65） | 零变化（实机外循环分发 `CwScreenBookcard` 选卡 / sim 无呈现面族消费两链不动，§1.6 条 3） |
| 6 | **WorldDecl** | **恒不构造**（:53-58 注释 + :66 无声明返回） | 零变化——op 侧既有零 `declare_world`/零 round data 同步保持（§3.2），**禁随迁移补声明**（补了 = 非转移动作凭空获得转移语义，违 action-op.md L77） |
| 7 | None 分支可达性 | None 输入仅来自「词表缺省/直调空 dict」两形态，均经 op 守卫拦截于上报之前；生产 journal 面自发出点迁策略器起恒显式 slot（None 分支的 `replace(action, slot=slot)` 重建只为显示显式槽号） | 死分支删除零行为差、零历史序列化断链 |

### 1.3 交替机制：开浮层 aftermath 对 `owned_equip_xy` 零交集，`cw4_equip_xy_pending` 零置位端、零机制改动（一句推演）

开典籍腾位写的是 bench 槽位表 kind 位（tome → empty），装备库存网格是独立面板区、备战席占用变化不驱动其布局，且本上报零 `gs.equips` 写端（§1.2 无库存变化核验）→ 零库存增删 → 零网格 reflow → `owned_equip_xy` 坐标恒新鲜。弹窗盖备战的遮挡段（星徽四选一在场期间）：备战环已交回外循环分发选卡，装备网格坐标伴随域无人读；选卡完成回备战后入口 heavy 观察（装备快照唯一写端，prep-contract §2 条 7）重写快照——零陈旧消费窗。**结论：`cw4_equip_xy_pending` 置位端不加开典籍点，本批零标志机制改动**（同判 bookcard 稿 §1.3，本 op 同为其「零贡献成员」——即便 A1 回退批统一收编置位端，本件 aftermath 零 append）。

### 1.4 拖点/点击：守卫上界迁移 op 内现读（`_bench_pts` 剩 OpenBox 一家——**非退役批**）；单击族形态保留零 env 消费（同判应用，见 open-bookcard 稿 §1.4）

- **守卫上界迁移**：`ex._bench_pts`（executor 构造期缓存，`prep_actions.py:362`）→ op 内执行期现读 `row_area_centers(self.ctx, '备战栏')`（静态档，值理论逐位同）。bookcard 单域无 screen_name 域分派问题，tome 同。**`_bench_pts` 非退役申报边界**：本批迁走 tome 后，`PrepActionExecutor._bench_pts` 现役消费者剩一家——`cw_open_box_action.py:77,83`。**属性本体保留，物理退役 = 第八棒（OpenBox 收官批）**，届时与零消费遗留合流清场（§9 申报行 1）。本批注释收口一处：`prep_actions.py:357-361` 「开件两类守卫(OpenBox/OpenTome,各自迁移批退役)——OpenBookcard 已随其参数面迁移批改 op 内现读并废除 slot=None 现算」收窄为「开件一类守卫(OpenBox,其迁移批退役)——OpenBookcard/OpenTome 已随各自参数面迁移批改 op 内现读(OpenTome 并废除 slot=None 现算)」。同块内 `SellDeployed 过渡期仍消费 _front_pts/_back_pts` 陈旧句**不碰**（遗留⑤辖域，归收官批，§9 申报行 1）。
- **点击形态**：本 op 机械本体 = **单击**「备战栏-{slot}」槽位本体中心弹浮层（单击化用户口径 2026-09-25 已确认于现注释，逐字保留）。与拖拽原语 `drag_char_guarded` **不同构**（交互是 click 非 drag）、与 bookcard/OpenBox/CollectOre/LevelUp 同族单击口径——同判应用 bookcard 稿 §1.4：`area_center` 按名直查（`cw_obs_core.py:67-74`，缺档自然异常零防御）与 `row_area_centers` 表长守卫两读并存为有意形态；零新原语、零分域声明（`row_area_centers` docstring 拖点权威分域 :164-170 是拖点派生式辖域，本 op 无拖拽交互不涉）。差异点仅一：坐标源从 `ex._ctx` 换 `self.ctx`（:108 窥探拔除的落地，值同源同档零差）。
- **零 env 消费**（同判 bookcard 稿 §1.5，单域零消费档）：签名改 `env: PrepExecEnv | None = None`，op 体零 env 消费（无域分派/无 ledger/无 executor 依赖）；`PrepExecEnv.executor` 本就 `| None` 可缺省（`prep_actions.py:319`），注册表构造路径恒传完整 env 兼容不动（`cw_action_registry.py:247-256` / `prep_actions.py:468-470`）。

### 1.5 交替载体/新鲜度零涉面

本 op 无坐标伴随域消费（slot 键域动作），`cw4_equip_xy_pending` 的置位端（穿装 mandate M7 + entry 第 7 步）与消费端（Obs in_place 重观察帧）全部不涉——零改动。补此节仅为一句话清边界，防审查者误问。

### 1.6 sim 形态自洽：gate 归位（点击+睡眠同 gate）；**零声明形态保持**；star_tome 消费链零变化

1. 机械 gate：现状点击已 gate（:109-111）、睡眠未 gate（:114-117 无条件）——迁移后 `mouse_move+click+sleep` 全段收进 `mechanical_io_allowed()` gate（bookcard op :122-131 同构）。sim 局开典籍帧从「op 睡 1.8s」双层变「0 睡」单层（§7 条 3）；实机零差异。
2. 期望态推进：上报函数族两执行面同源——op 直调唯一消费面（§1.2 核验表 #1），sim 局经同一 op 路径走同一上报函数。**零声明差异**：op 侧无 `declare_world` 喂入行、round 结果无 data——非转移动作家族口径（action-op.md L77），与 bookcard 的「声明喂入 + data 携带」不同构，两边都正确。
3. overlay 登记 star_tome 的 sim 消费链（零变化申报）：star_tome ∈ sim「无呈现面族」（`cw_sim_backend.py:3229-3241`）——登记后由 sim 后端即时 `consume_screen_change` 消费 + 逐 kind 披露（`star_tome_options_unmodeled`），无模态呈现。该链消费的是登记条目（与动作上报解耦），本批零 sim 改动。
4. 直调路径：MCP `run_operation` 传 `{"slot": N}` → 守卫闭合域内机械（sim 环境 gate 静默）/实机点击 + 上报；非法值 → 守卫 AssertionError 零点击（守卫在 gate 外，两执行面同守）。

## 2. 新参数面定稿

### 2.1 字段集变更（`kernel/cw_vocab.py::CwActionOpenTomeParam`，:577-586 现值）

**零新增、零删除字段**——`slot` + `route_tag` 两字段保留；变更 = `slot` 必填化：

- `slot: int`（去 `| None = None` 缺省，必填第一位）：[索引定义] 注释三要素——坐标系 = 备战栏画面物理槽位 1 基（area 序，坐标参数化机械动作族同系）；取值时机 = 生成期快照（决策半 `_consumable_open_action` 按 gs bench kind='tome' 槽位现算，`entry.py:554-558` 单一现算点；直调 = 当帧 extras bench.slots 同口径）；写入端 = 发出点。None 语义废除申报一句（§1.1 指针）。
- 类 docstring 改写：「slot=None → 第一典籍」句删除（:582），替换为必填申报 + 记账路径总契约第七适用者申报（腾位直址写零反查退化形态 + 宪法③空集 + 零转移声明语义申报）+ 直调传参指引（extras bench.slots kind='tome' 下标+1）。
- `route_tag`（kw_only + `action_key_exclude`）不动。
- 补 `from_dict` classmethod：共享 `cw_vocab.action_param_from_dict`（:632-640）一行委托（bookcard :624-627 家族同款）。最小 dict = `{"slot": 1-9}`；缺 slot 键 = `cls(**…)` 缺参 TypeError（禁在 from_dict 加缺省兜底——共享形态单一源，不为本件开例外）。
- `action_key` 幂等键零变化：`slot` 入键（行为参数，正确）、`route_tag` 不入键（既有 metadata）。词表 `action_key` docstring 失配为本批零触及面（§9 申报行 3）。
- 词表模块头「开件三类」两句（`cw_vocab.py:11-13` 与 `:144-148`）辖域核验：两句述 row/slot **坐标系语义**（画面物理槽位 1 基），三类字段定义仍在且语义不变——句子保留零改动，bookcard 批同判（bookcard 稿 §2.1 末条）；None 缺省残面现在只剩 OpenBox 一类，由 OpenBox 类自身 docstring 与其迁移批申报，不动模块头。

### 2.2 守卫断言（op 内，校验落点契约 = action-op.md L55；同判 bookcard 稿 §2.2 双形，文案换 tome 口径）

1. **None 形**：`action.slot is None` → 断言，文案带契约指引（kind='tome' 版）：`CwActionOpenTomeParam slot 必填(备战栏物理槽 1-9 基 1;直调按当帧 extras bench.slots kind=tome 槽下标+1 传;slot=None 现算语义已随参数面迁移批废除,现算归发出点 entry._consumable_open_action),零点击`。加强理由同判 bookcard 稿 §2.2 条 1（TypeError 不指向参数面，废除语义必须自教）。
2. **越界形**：`not (1 <= int(action.slot) <= len(pts))` → 断言（`pts` = op 内现读 `row_area_centers(self.ctx, '备战栏')`；下界显式闭合禁负下标回环；文案带词表参数语义与合法域 + 画面档定位 `画面档={SCREEN_NAME}`，bookcard op :115-117 同构）；空点表命中同一断言 = 建档漂移哨语义，不设独立分支。守卫在 `mechanical_io_allowed()` gate 外（sim/实机两执行面同守）。

**零 gs 读声明**：机械路径（守卫 + 点名直查 + 点击 + 等待）零 `game_state_from_ctx` 消费——自上报取容器 = 上报路径非机械定位（bookcard 稿 §2.2 同款裁定）；宪法①修复完成（本批实质修复项，修复+声明双真）。

## 3. 牵涉面清单（逐文件；grep 全量已核，行号 = HEAD 57403b744）

> 路径根 = `src/sr_od/application/currency_war/`。

### 3.1 `kernel/cw_vocab.py` — §2.1：slot 必填化 + from_dict + 类 docstring 改写（:577-586）

### 3.2 `operations/cw_op/cw_open_tome_action.py` — op 执行体重写

机械自持：None/越界两形守卫（§2.2）→ `area_center(self.ctx, f'备战栏-{slot}')` 建档直查（零防御口径保留）→ sim gate（点击 + `time.sleep(_OVERLAY_ANIM_WAIT_S)` 同 gate；`_OVERLAY_ANIM_WAIT_S` 函数内局部 import 形态保留不动）→ `self.ctx.controller.mouse_move + click`（防吞点击口径逐字沿用）→ detail 组装 → 自上报：`gs = game_state_from_ctx(self.ctx)`；`gs is None` = 无处记账跳过（零上报零异常，既有行为保留——现状 `:81/:120-121` 的 gs 预取/二次取随 None 分支删除一并坍缩为单次取，bookcard op :140 同形）；`outcome = report_action_open_tome_param(gs, action, ChannelSig(family='logic_action', actor=type(self).__name__, mode='compute'))`；`outcome.applied=False` → detail 追加 `；记账拒单:{outcome.reason}(点击已发生,账未落)`（家族 M-r3-1① 同形，动词「点击」）；`log.info(f'[cw][tome] {detail}')`（bookcard op :153 同形——现状 :118 的先行 log 随 detail 升级并入上报后单行）；`return self.round_success(detail)`——**无 data 参数**（非转移动作零声明，§1.2 核验表 #6；bookcard 的 `data=world_decl` 不搬）。删除面：`replace` import（:13，None 分支专用）、`_TOME_BENCH_KIND` 常量与三处现算注释（:35-39）、`ex` 全部窥探（:73/:74/:80/:108/:110-111）。签名改 `env: PrepExecEnv | None = None`（TYPE_CHECKING import 保留供注解）。`terminal = False`/`terminal_wait = 0.0` 类属性（:52-54）**零改动**——非终结语义保留是本件与 bookcard 的形态差异（§4）。docstring 重写：模块头与类 docstring 按家族参数面迁移形态行文（起终点行沿用 :44 现骨架；「非终结」申报与单击化用户口径注释保留；参数面指引 = slot 直调 extras kind='tome' 口径 + 必填双出口报错申报；直调指引 = run_operation `{"slot": N}`、env=None 缺省备战档；记账总契约第七适用者 + 拒单禁补点口径——拒单 = 腾位账未落，处置 = 交还决策循环重读板面重派，禁补点；零转移声明语义申报一句）。模块头引用规范路径名更新：`flow/action_ops.md` → `flow/action-op.md`（文件改名后旧指针，随重写顺改）。

### 3.3 `kernel/cw_action_report/open_tome.py` — None 分支删除 + docstring 同步（§1.2）

`:44-46` 改 `_idx = int(param.slot) - 1`；函数 docstring 补 slot 必填申报与现算收敛声明（bookcard 稿 §3.3 同构句式）。其余逐位不动（核验表 §1.2）。

### 3.4 `prep_actions.py` — 注释收口一处；点表属性本体零改动

- `_bench_pts` 边界注释收口（:357-361，§1.4 已引新句）；模块头 slot 语义段「开件三类」（:33-36）与回执受阻码注释「开件三动作」（:113-116）零改动（坐标系/历史语义句，bookcard 批同判保留）。
- `_bench_pts/_front_pts/_back_pts` 属性本体、`_drag` 方法、`row_area_centers`/`area_center`/`_OVERLAY_ANIM_WAIT_S` 原语本体零改动；`_front_pts/_back_pts/_drag` 零消费复活遗留**不碰**（退役债务重开 = 遗留⑤，归收官批合流清场，§9 申报行 1）。
- ⚠️ 在飞申报：本文件当前 HEAD 干净（不在工作区 M 列表），实施时复核；绝不卷入并行批改动行。

### 3.5 发出面 `strategies/impl/mandate_v1/entry.py` — 零改动

`:554-558` 已显式传 slot；`:148-153` `_TRUNCATION_POINTS` 含本类（:149）零变化（截断分类 = 类名面，与参数缺省无关）。

### 3.6 `operations/cw_op/cw_action_registry.py` — 零改动

import（:50/:98-100）与注册行（:180）类名不变；组装恒传 env（`action_op_for :256` / `prep_actions._dispatch_action :468-470`）兼容缺省化。

### 3.7 `operations/cw_screen/cw_screen_prep.py` + `cw_screen_bookcard.py` — 零改动（非终结交接路径申报）

**本件与 bookcard 的画面 op 面差异**：bookcard 终结动作走 `_terminal_exit` 专属分支（cw_screen_prep.py:949-954）；OpenTome **非终结**，交接走 director 环通用 overlay-pending 提前返回路径（:883-891 帧代次 none → :892-901 「overlay 已登记 N 项 → 交回外循环分发」wait=0.8）——登记在上报函数内、两执行面同一行代码，`_terminal_exit` 无 tome 分支（grep 实锤：cw_screen_prep.py 全文零 OpenTome 引用），本批零新增分支。星徽四选一画面的接住方 = 外循环阶段一身份分发 `CwScreenBookcard`（:docstring 与词表链引用为指针面，零代码耦合）。

### 3.8 telemetry — 零改动

`telemetry/cw_match_recorder.py:135`（bench 道具槽记录按 kind ∈ supply_box/tome/bookcard 过滤）读 gs 槽位表，与 param 面零耦合；`match_archive.py` 零 tome 序列化面（grep 零命中，对照 bookcard 稿 §3.8 同判）。

### 3.9 测试仓镜像测试 — 见 §5

### 3.10 文档面 — 见 §8

## 4. op 执行语义（迁移后）

1. None 守卫 + 越界守卫（§2.2，gate 外——两执行面同守）。
2. 点击点静态直查：`area_center(self.ctx, f'备战栏-{slot}')`（零截图零识别零 gs；缺失 = 自然异常，零防御既有口径）。
3. sim 分支：`mechanical_io_allowed()` 为假 → 机械段（含固定动画等待）静默跳过（上报函数族照走——sim 期望态推进 = 自上报单点，两执行面同源）。
4. 实机机械段：`mouse_move` 防吞 + `click` → `time.sleep(_OVERLAY_ANIM_WAIT_S)`（1.8s 开典籍动画等待，gate 内，值逐字沿用）。
5. 自上报：腾位 + star_tome 登记（上报函数单点）→ round detail 拒单段消费（无声明喂入行——非转移动作）。
6. round 结果：恒 `round_success('开典籍槽{slot} ✓(发出即记账,落地归观察对账)')`（机械成功语义；零 round_fail 通道，回执受阻码表零变更——detail 文案升级判读申报 §7 条 1）。

**决策侧参数现算契约适用申报**：本 op 发出域 = 备战决策环（entry ① prep 实体面卡片分支 + 第 0 步溢出自救态 2 共用 `_consumable_open_action`，每动作重 decide、同帧承诺成立）。无跨帧队列形态、非战斗链批量发射辖域。**非终结动作语义保留**：terminal=False + terminal_wait=0.0 类属性零改动——开典籍后星徽四选一弹窗由 director 环 overlay-pending 路径交回外循环（:892-901 通用路径，登记驱动非终结口驱动），外循环阶段一身份分发 `CwScreenBookcard` 选卡 `PickStarTome`（选卡消费族②，`zero_writes.py:157` 消费登记）。规划器截断分类面（`_TRUNCATION_POINTS` 含本类，entry.py:149）零变化。

## 5. 测试设计（sr-od-test，按 AGENTS.md §11.4 harness 规范；镜像路径，命名无批次号；对照 bookcard 6 条锁型同构）

> 现场实态：sr-od-test 现存 OpenTome 专属测试零命中（grep 已核，仅 `test_action_registry.py:6` 注释提及漏登记史）；bookcard 测试 = `test_cw_open_bookcard_action.py`（213 行 6 锁）为结构模板。

1. `test/sr_od/application/currency_war/kernel/cw_vocab/test_cw_vocab.py`（既有文件扩展，紧邻 bookcard 组 :325-354）
   - OpenTome `from_dict`：最小 dict `{"slot": 5}` 逐字段断言（`route_tag=''`）；未知键忽略；**缺 slot 键 = TypeError**（必填锁测）；`{"slot": null}` 可构造（None 拦截归 op 守卫的家族口径锁测）。
   - `action_key`：slot 不同产不同键；`route_tag` 不入键。
2. `test/sr_od/application/currency_war/operations/cw_op/test_cw_open_tome_action.py`（新建；harness 剧本，结构照 `test_cw_open_bookcard_action.py` 夹具形态：controller 记录 stub + monkeypatch 防污染 + screen_info 真档案同源派生期望值）
   - **None 守卫锁测（审计 bug 修复锁）**：`slot=None` → AssertionError（文案含「必填」与 kind='tome' 指引关键词）且点击记录零条目。
   - 守卫：slot=0 / 负值 / 越界（≥10）→ AssertionError 零点击（负下标回环防锁）。
   - 实机形态（真档案派生）：点击记录 `== 备战栏-N rect 中心`（裸中心同源锁测）；mouse_move 先于 click（防吞口径顺序锁测）。
   - **round detail 拒单码**：种子使 gs bench 该槽 kind='empty' → round_success 且 detail 含「记账拒单:tome_slot_missing(点击已发生,账未落)」；正常帧（kind='tome'）detail 无拒单段 + 断言 gs bench 该槽变 empty（腾位记账锁测）+ **star_tome 登记在场**（`gs.screen_changes.pending` 含 kind='star_tome' 条目——overlay 登记锁测）+ **round data 无声明锁测**（round 结果 data 为 None——非转移动作零声明形态回归锚，与 bookcard 的 data=WorldDecl 相反向锁，本件差异点）。
   - gs 缺席帧（无 session 种子）→ 机械已发 + 零上报零异常（无处记账跳过形态锁测）。
   - `env=None` 全链跑通；sim 形态（port 关闭 → 点击记录零条目 + 自上报照走 + star_tome 登记照写）；`with fast_sleep(): op.run()`。
3. `test_action_registry.py`（既有面）：零改动预期（terminal=False/terminal_wait=0.0 类属性不变——终结集测试对象不含本类）。
4. `test_prep_actions.py`（既有面）：零改动预期（本批无桩删除、点表属性不动）。

验收阶梯（skill §3）：L1 → L2（点名新增文件 + test_action_registry + test_prep_actions + test_cw_vocab）→ L3 全量 commit 前。实机验收序列 = §11。

## 6. sim 形态自洽结论

**结论：零 sim 改动。**

1. 机械段：gate 归位（§1.6 条 1）——sim 局与实机同跑同一循环/op/策略，上报函数族两执行面同源直调同一函数（op 直调唯一消费面，§1.2 核验表 #1）。
2. 期望态推进：腾位记账 = 槽位表直址写（无伴随域依赖、无反查），sim 形态与实机同核零分叉；**零声明零喂入行**（非转移动作，家族口径）——无端口层分流面可言。
3. overlay 登记：star_tome 直登在上报函数内（两执行面同一行代码）；sim 消费 = 无呈现面族即时消费 + `star_tome_options_unmodeled` 披露（`cw_sim_backend.py:3229-3241`），链路零变化。
4. 直调路径：`{"slot": N}` 在 sim 环境 = 守卫通过 + 机械静默 + 上报照走（round detail 可核）；非法值 AssertionError 两执行面同炸（守卫在 gate 外）。

## 7. 风险与行为变化清单

1. **行为变化：round detail/log 文案升级 + 新增拒单段**（outcome 消费）——journal 判读面从「开典籍槽N」变「开典籍槽N ✓(发出即记账,落地归观察对账)」，拒单帧新增「记账拒单:tome_slot_missing(点击已发生,账未落)」段（现役生产不可达——决策同帧现算下槽态不失配；可达面 = 直调错传/陈旧直构）；遥测分键零新增（reason 词表封闭不动），首局对照判读申报。
2. **行为修复：slot=None 语义废除（审计挂号 bug 同型本体）**——直调缺 slot/传 null 从「op 内 gs 现算双出口 AssertionError」变「构造面 TypeError / op 守卫 AssertionError（零点击零 gs 读，文案指向参数契约）」——fail-fast + 宪法①修复双真；生产发出面零变化（§1.1 迁移申报表）。判读申报：直调报错形态变化，排障时按新报错文案对参数面。
3. **行为变化：sim 局开典籍帧零白睡 1.8s**（sleep 进 gate）——sim 批量局效率改善；实机零差异。
4. **宪法①修复：机械路径 gs 读拔除**——None 形态固有的「现算结果随帧漂移」风险面消除；守卫只判参数合法域。
5. **坐标等价性**：守卫上界（`row_area_centers` 表长）与点击点（`area_center` 同名 area 中心）同源同档零变化；坐标源路径变化（executor 构造期缓存 + `ex._ctx` → op 执行期现读 + `self.ctx`）理论零差，实机落点核对 = 背书义务（§11 验收①）。
6. **死代码退役一件**：上报层 None 分支删除（唯一消费方 = op，核验表背书）。本批无桩删除面（§0 已申报）——比 bookcard 少一件。
7. **交替机制零改动**（§1.3）：开典籍 aftermath 零 `gs.equips` 写端为上报函数现值事实，游戏版本若引入「开典籍直得装备」类机制，该面随版本适配批重新核验，本批不预设。

## 8. 文档与 skill

- `skills/sr-od-dev-currency-war/references/flow/prep-contract.md`（**实施批落地**——本稿点名逐节内容，文档随实施 commit 落保正本与代码现状一致；该文件当前 HEAD 干净已核，实施时复核）：§1 L9 动作字段坐标系段——「箱/典籍过渡期仍经执行器点表守卫(各自迁移批退役)」改「典籍已随其参数面迁移批 op 自持守卫 + slot 必填化（None 废除）；箱过渡期仍经执行器点表守卫（其迁移批=开件族收官批退役）」；§1 L10 画面点位段——「现役消费 = 开件两类守卫 OpenBox/OpenTome」改「现役消费 = OpenBox 一家守卫（其迁移批退役）——OpenBookcard/OpenTome 已随各自参数面迁移批改 op 内现读」；§3 L27 坐标参数化机械动作取值时机段 + L28 OpenBookcard 行句后补 OpenTome 行句（slot = 生成期快照必填，决策半 `_consumable_open_action` 单点现算，None 语义废除——句式照 L28）；§6 G1 活缺口——「现役辖域收窄为开件族箱/典籍」改「收窄为开件族箱（OpenBox）」；G2 不涉申报一句（本 op slot 链走 gs bench kind 扫描与建档 area 直查，零 obs `read_*`/`find_*` 族消费；obs `find_tomes` 残余消费 = 观察分类域，G2 收口归收官批）。
- `skills/sr-od-dev-currency-war/references/flow/action-op.md`（**本批不动**）：HEAD 实读确认 bookcard 批申报的收尾义务（§5 L131 bookcard 行改写、L32 总契约条款批次计数推进）尚未落库——本批同型义务**累积同队列**：§5 L130 OpenTome 行改写（现值行文「`read_tomes` 识别 → 点槽一次开启」为 open-actions-mechanical-pure 批之前的过期描述，改写为参数面迁移后终态：守卫 op 内现读/slot 必填/None 废除/记账拒单 detail/env=None/总契约第七适用者/非终结形态保留/零转移声明）；L32 计数推进（两件槽位键域退化形态一并附记：bookcard 第六 + tome 第七适用者）；§2 L61 备战域动作全集行缺枚举核补（bookcard 稿 §9 行 5 既有申报，同笔顺带）。**三笔归同一收尾批一笔清**（收尾义务批 §11 申报行 4）。
- `skills/sr-od-dev-currency-war/SKILL.md`：零改动（§1.4 参数面规范三分法与本批形态一致；工作区 M 状态的在飞修改不碰）。
- `docs/develop/sr_od/application/currency_war/game_state/fields.md`：零改动（零 gs 字段变更；`tome_slot_missing` 为既有 outcome reason 非回执受阻码，词表零变更）。
- 玩家 skill `skills/sr-od-currency-war/`：零改动（开件族非玩家直调面；`run_operation` 直调 = 开发者/单件会话形态，op docstring 自足——家族五批同款裁定）。
- sim-design.md：零改动（零 sim 行为变更；§6 自洽结论不新增申报行）。

## 9. 申报行（相邻问题，本批不修）

1. **OpenBox 待第八棒 = 开件族收官批**（含 `_bench_pts` 物理退役 + 零消费遗留清场**合流**）：本批迁走 tome 后 `_bench_pts` 现役消费者剩 `cw_open_box_action.py:77,83` 一家——属性本体保留至收官批物理删除；届时合流清场清单（终审已裁定 grep 背书删除安全，流水线遗留⑤）：`_bench_pts/_front_pts/_back_pts` 属性与 `_drag` 方法（现役零 op 消费 grep 实锤，本稿 :363-364/:493 复核）、prep_actions.py 三处过期注释（:332-334 类 docstring 过渡宿主句 / :361 SellDeployed 仍消费句 / :484-497 `_drag` docstring 段）、**OpenBox op 内注释过期面**（`cw_open_box_action.py:38-42`「上报层(kernel/cw_action_report/open_tome.py 等)各有一份同型现算」——本批退役 tome 上报层分支后该句失据，归第八棒随其文件改写）、G2 obs docstring 基声明（prep-contract §6，箱辖域）、词表/prep_actions 模块头「开件三类」辖域句收敛。**OpenBox 与本件的同判差异预告**（防第八棒误搬本稿）：①上报层**零 None 分支需退役**——`report_action_open_box_param`（`zero_writes.py:74-90`）零 param.slot 消费（零写族，本稿 §1.2 核验表无 OpenBox 行的原因）；②登记 kind = `'box_card'`（:86-88）且构造纯转移声明 `WorldDecl(trigger='open_box')`（:89-90）——与 tome 零声明**不同构**，核验表按其上报函数另核；③点击目标 = `武装箱开启位-{slot}` 开启按钮区（`cw_open_box_action.py:111`，非槽本体），直调 extras 指引 = `armory_boxes` 元素 slot 字段（recognizer :458-459），非 bench.slots kind 口径；④kind 字段值 = `'supply_box'`（entry.py:553）。预案判据 = 工具批/bookcard 稿 §9 行 1 同判（None 废除、两形守卫、op 内现读、env 缺省、from_dict、gate 归位照搬；上报/声明/点击面按上述差异另裁）。
2. **bookcard 同判已实施**（commit 70b2e1f15 主仓 + 7c177a0d 测试仓，终审验收通过）——本稿同判引用基准；bookcard 批申报的 action-op.md 收尾义务尚未落库（HEAD 实读），与本批同队列累积（§8）。
3. **词表 `action_key` docstring 与实态失配**（已挂号）：docstring（`cw_vocab.py:1329-1331`）称「现役 = CwActionSellBenchParam.reason 卖出归因 + route_tag 不入键」，实态 `reason`（:228）无 `action_key_exclude` metadata（入键）——流水线总遗留账⑥词表域批量契约批；本批 `action_key` 机制零触及，OpenTome 侧 slot 入键/route_tag 排除均正确无失配。
4. **其余族清点状态**：动作 op 参数面迁移流水线七棒已迁（穿装/工具七类/MoveUnit/SellDeployed/SellBench/OpenBookcard/本批 OpenTome）+ 第八棒 OpenBox 待 = 全流水线收官；pick 族坐标源过渡态收敛（跨迭代挂账板 #8②）非本批；三刷新建议动作/开店编排等注册表外执行体与本批零交集（OpenTome 在注册表内 :180），清点申报防漏。
5. **单击族无失焦守卫家族现状**（bookcard 稿 §9 行 6 同判延续）：开件三类/CollectOre/LevelUp/StartBattle/bookcard 裸 controller 点击，无 `drag_char_guarded` 同构失焦守卫；若未来实证单击输入同病，守卫宿主化归单击族专项，本批零改动。
6. **bench_unobserved 早退形态**（`open_tome.py:38-42`，applied=True + reason 非空 + 零声明）——生产不可达申报保留；直构/离线形态可达且不进拒单 detail；若未来收紧为拒单语义归记账拒单域批，非本批（bookcard 稿 §9 行 7 同型同判）。
7. **星徽四选一 sim 无呈现面族**（`cw_sim_backend.py:3229-3241` 即时消费 + 披露，选项注册表缺位）——选卡决策链的 sim 形态缺口既有申报，归 sim 呈现面批，非本批辖域（本批仅保证登记链零变化）。
8. **`CwScreenBookcard` 类名辖域错位**（bookcard 命名的画面 op 实辖 star_tome 星徽四选一弹窗，专家邀请函归 `CwScreenExpertInvite`）——既有命名，本批零改动；申报防后续读者按类名误判分发关系。

## 10. 实施顺序建议（给实施角色）

1. `cw_vocab.py` param 必填化 + from_dict + docstring（§3.1）。
2. `cw_open_tome_action.py` op 重写（§3.2/§4）。
3. `cw_action_report/open_tome.py` None 分支删除（§3.3）→ `prep_actions.py` 注释收口（§3.4）。
4. 测试（§5）→ 文档（§8；prep-contract 同批落）。
5. MCP server 重启 → `describe_operation_flow` 核对 op 节点图（恒 round_success 单节点形态）→ `list_operations`/`describe_operation` 核对反射参数面（slot required + env 缺省）→ 实机验收序列（§11）。

## 11. 实机验收序列（给实施角色）

1. **点击落点与腾位核对（§7 条 5 义务）**：备战画面开一星徽秘典（决策自然触发或直调）——点击落点 = 秘典槽中心；下一帧实读：星徽四选一弹窗在场（外循环分发 `CwScreenBookcard` 选卡）、bench 该槽腾空、零金变零库存变（腾位直址写旁证）；选卡完成后回备战入口 heavy 观察正常（弹窗盖备战段的交替机制旁证）。
2. **直调单件会话**：run_operation 跑 `CwActionOpenTomeOp`（from_dict 通道，env=None，`{"slot": N}` 按当帧 extras bench.slots kind='tome'）一例，核对 round detail 与落位；**废除形态一例**：缺 slot 键（构造面 TypeError）与 `{"slot": null}`（守卫 AssertionError）各一，核对报错文案指向参数契约。
3. **拒单形态一例**（如可安全构造）：直传与板面不符的 slot（指向空槽）→ 点击已发 + detail 含「记账拒单:tome_slot_missing」段 + 零写账——核对后交还决策循环重派，不补点。
