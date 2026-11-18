# CwActionOpenBoxOp（开简易武装箱）参数面迁移设计稿（r1）

> 迭代：CW 动作 op 迁移流水线 · 设计角色产出（开武装箱 op 批 = 第八棒，**开件族收官件，全流水线末件**）。
> 上批 = 开星徽秘典 OpenTome（changes/open-tome-param-surface/design.md，**同族最近先例与同判基准**，已落地 commit 9f8d48bad）；第六棒 = 开书册卡 OpenBookcard（changes/open-bookcard-param-surface/design.md，commit 70b2e1f15 + 测试仓 7c177a0d）；第五棒 = SellBench（d3ea8719b）；第四棒 = SellDeployed（68199b48d）；第三棒 = MoveUnit（a09f30e8b）；第二棒 = 工具原子七类（76a94c27c）；首棒 = WearEquip（db4697e40 终稿）。
> **范围裁定（每迭代只切一个 op）**：本批只做 `CwActionOpenBoxOp` 一件——开件族第三件即收官件。slot=None 同型已获两处预裁定（工具批预裁 + bookcard 稿 §9 行 1 同判预告）+ tome 稿 §9 行 1 五项差异预告（本稿逐项应答，见 §1.1/§1.2/§1.4/§2.1/§9 行 2）。本稿 = **同判应用 + 差异辨析**：与 bookcard/tome 同判的部分标注「同判应用，见 open-tome 稿 §N」不再重复论证；本稿价值在五项差异——①零写占位形态的总契约适用申报（与 tome「腾位直址写」根本不同构）；②上报内 `box_card` 登记 + 有声明 `_decl_bottom(gs,'open_box')`（与 tome 零声明相反）；③点击目标 = 武装箱开启位按钮区（非槽本体）；④kind='supply_box'（kind 串不同）；⑤退役债务合流（`_bench_pts` 物理退役 + 遗留⑤清场归实施批）。
> 冻结宪法（穿装批成文）：①动作 op 执行路径零 gs 依赖；②参数面三分法；③名称字段 = 语义参数（机械面与记账面均零消费）；④坐标新鲜度纪律归调用方；⑤参数 dataclass 统一补 `from_dict`；⑥gs 给实体记录坐标；⑦每个 op 一个迭代，牵涉面一次改净。
> **记账路径总契约第八适用者**（正文 = `skills/sr-od-dev-currency-war/references/flow/action-op.md` L32「记账路径总契约」条款）——**独立申报，前七适用者表述不适用本件**：本件上报 = **零写占位形态**（`kernel/cw_action_report/zero_writes.py:74-90`——状态容器零写 + `box_card` 登记 + 转移声明，腾位归下一入口 heavy 实读覆盖），与 tome/bookcard 的「腾位直址写零身份反查」退化形态**不同构**（那两件是槽位键域零反查；本件是**零键域零写**——上报函数零 param 字段消费、零状态容器写端，总契约三条在此域整族退化，见 §1.2）。
> **行号基准声明**：本稿全部行号基于写稿时 HEAD `9f8d48bad`（全 hash `9f8d48bad34b4267be069d6cb142015fa83fbdcf`）。任务书下发基准与写稿 HEAD 同值（第七棒 tome 批落地 commit 即当前 HEAD），零漂移；全部行号按 HEAD 实读自核。⚠️ **工作区并行批在飞申报**：工作区有未提交改动（`data/affix_effects_data.py`、`currency_war_battle_prep.yml` 等四份画面档、SKILL.md 与四份 skill references——装备广场系批工作现场）。两道核验已做：①在飞备战档 diff 经 `git diff | Select-String '武装箱开启位|备战栏'` **零命中**，本稿「武装箱开启位-N 在档」结构事实不受影响；②src/currency_war 在飞 .py 仅 `data/affix_effects_data.py`（数据表），本稿全部引用文件（op/词表/上报层/prep_actions/entry/注册表/画面 op/obs/telemetry）均 HEAD 干净。实施角色动任何文件前复核在飞批落库状态，绝不卷入在飞改动行（对齐 bookcard/tome 稿 §0 同款纪律）。

## 0. 本批范围

`operations/cw_op/cw_open_box_action.py::CwActionOpenBoxOp` + 词表 param `CwActionOpenBoxParam` + 上报层调用面（`kernel/cw_action_report/zero_writes.py::report_action_open_box_param`——**代码零改动，仅 docstring 补申报**，§1.2）+ 发出面/注册表/画面 op/telemetry 全部引用（grep 全量已核，§3）+ **开件族收官合流**：`PrepActionExecutor._bench_pts` 物理退役 + 遗留⑤死代码清场（§3.4，实施批义务）。

现状债（迁移动机，逐项对 tome 稿 §0 债表同构；行号 = HEAD `9f8d48bad`）：

| 债 | 现值（HEAD） | 迁移形态 |
|---|---|---|
| **slot=None 硬 gs 分支（审计挂号 bug 同型第三例=末例，本批主轴）** | `cw_open_box_action.py:84-105`：slot=None 时 op 机械路径中途 `game_state_from_ctx` 现算首件 supply_box 槽（宪法①违例本体）+ 双出口守卫断言（:90-93 gs 缺席 / :98-101 bench 无该 kind 首槽） | None 语义废除、slot 必填化（§1.1，同判应用）——现算收敛发出点 `entry._consumable_open_action` 单点 |
| 词表缺省值死角 | `cw_vocab.py:572` `slot: int \| None = None`（类 docstring :571「slot=None → 第一箱」） | 必填化 + docstring 改写（§2.1） |
| 上报层 None 分支 | **零**——`report_action_open_box_param`（`zero_writes.py:74-90`）零 param 字段消费（param 仅透传签名，函数体零读；零腾位写、零现算）——tome 稿 §9 行 1 差异预告①兑现实核 | 上报层**代码零改动**（家族八批首例），仅 docstring 补申报一句（§1.2 裁决） |
| 机械链窥探 executor 私有面 | `:75-76` `env = self.env; ex = env.executor`；`:77/:83` 读 `ex._bench_pts` 做守卫上界；`:111` 经 `ex._ctx` 取建档坐标；`:113-114` 经 `ex._ctx.controller` 点击 | op 机械面全自持：守卫上界 op 内现读 `row_area_centers(self.ctx,'备战栏')`，controller/ctx 走 `self.ctx`，零 env 消费（§1.4，同判） |
| op 内过期注释与常量 | `:38-43` `_BOX_BENCH_KIND = 'supply_box'` 常量 + 「决策层与上报层(kernel/cw_action_report/open_tome.py 等)各有一份同型现算,三处语义必须一致,提取公共函数归另批」注释——tome 上报层 None 分支已退役，**该句已失据**（tome 稿 §9 行 1 预告的 OpenBox op 内注释过期面） | None 废除后三处收敛决策层一处，常量与注释随批删除（同判 bookcard 稿 §1.1 论证 4） |
| 旧规范路径指针 | `:3/:78` `flow/action_ops.md`（action-op.md 改名前旧名） | op 重写顺改 `flow/action-op.md`（tome 批同款）；`op-layer.md` 指针保留（全仓既有面，非本批辖域） |
| sim 局白睡 1.8s | `:112-120` 点击已 gate（:112-114）、`time.sleep(_OVERLAY_ANIM_WAIT_S)` 未 gate（:117-120 无条件执行） | sleep 移入 gate（tome op 现值 :130-139 家族形态），§7 条 3 |
| env 必传（无缺省） | `:64-65` 构造签名 `env: PrepExecEnv` 必传——MCP `run_operation` 直调不可达（env 形参 required 非 JSON 可构造） | 签名改 `env: PrepExecEnv \| None = None`（家族同款，§1.5） |
| param 缺 `from_dict` | `CwActionOpenBoxParam` 类体内零 classmethod（`cw_vocab.py:569-574`） | 共享 `cw_vocab.action_param_from_dict`（:659-667）一行委托 |

**本批比 tome 少一件债、多两件合流**：少 = 上报层 None 分支退役（zero_writes 零写族无此分支）；多 = ①`_bench_pts` 物理退役（本批迁走 OpenBox 后执行器点表现役消费清零，§1.4）；②遗留⑤清场（`_front_pts/_back_pts/_drag` 零消费死代码 + 三处过期注释——第五棒终审裁定 grep 背书删除安全，归本批合流，§3.4）。**这两件是实施批义务**：本稿只做裁决与清单 + 实施批验收自核清单（§5 末），源码零改动（红线）。

## 1. 本批特有设计题裁决

### 1.1 slot=None 主轴裁决：None 语义废除、slot 必填化（同判应用，见 open-tome 稿 §1.1；本节只补本件证据）

**裁决：`CwActionOpenBoxParam.slot` 从 `int | None = None` 改为 `int`（必填无缺省）；op 守卫显式拒 None；None 语义全链退役。** 裁决理由、选项 B 被宪法排除的论证、根层定位全部同判 bookcard 稿 §1.1（论证 1-4 逐条适用；上报层 None 分支一项不适用——本件上报层无该分支，见 §0 债表），本节不重复，只补本件 grep 证据：

- **生产构造唯一单点** = `strategies/impl/mandate_v1/entry.py:551-558` `_consumable_open_action` 三元组 supply_box 行（`:553` `('supply_box', CwActionOpenBoxParam, 'prep_box')`）——`:558` 恒显式 `Emitted(atom_cls(slot=idx + 1), True, tag)`。grep 全仓 `CwActionOpenBoxParam` 构造仅此一处（其余命中 = 词表定义、`_TRUNCATION_POINTS :149`、注册表 import+行 :92-93/:179、op 引用、上报函数签名类型面——零第二构造点）。None 只活在四个死角：词表缺省（`cw_vocab.py:572`）、op 现算分支（op :84-105）、MCP 直调空 dict、单帧测试零参构造——**废除 None = 生产面零改动、纯死角清理**（bookcard/tome 同构；与两件差一项：无上报层死角）。
- **kind 字段值核实（差异预告④）**：武装箱在 bench 槽位表的 `BenchSlot.kind` 值 = **`'supply_box'`**。三源互证：op 模块常量 `cw_open_box_action.py:43` `_BOX_BENCH_KIND = 'supply_box'`；发出点 `entry.py:553` kind 键 `'supply_box'`；recognizer extras doc `battle_prep_recognizer.py:452`（slots 元素 kind 枚举 `unit/supply_box/tome/bookcard/empty`）。与 tome `'tome'`、bookcard `'bookcard'` 均不同串——三件开件 kind 互斥，直调传参指引各用各的串，勿串用（tome 稿 §1.1 已反告本棒，本稿对称反告后续读者）。**直调传参双口径（等价申报，§2.2/§3.2 契约化）**：①发出点同源口径 = 当帧 extras `bench.slots` 中 kind='supply_box' 槽的下标 + 1（与 bookcard/tome 同构）；②观察直供口径 = 当帧 extras `armory_boxes` 元素的 `slot` 字段**直接传（无需 +1）**——`read_armory_boxes`→`find_armory_boxes`→`_ctx_slots`（`obs/cw_identity_obs.py:522-529`）`range(1, count + 1)` 实证 slot_idx = 备战栏物理槽位 1 基，与口径①同一物理槽位号语义等价。①②任选其一（tome 稿 §9 行 1 差异预告③的「直调 extras 指引 = armory_boxes 元素 slot 字段」与本稿口径②同源）。

**迁移申报（双调用面覆盖，bookcard 稿 §1.1 表同构）**：

| 调用面 | 现形态 | 迁移后 |
|---|---|---|
| 流程发出面（entry `_consumable_open_action`） | `atom_cls(slot=idx + 1)` 显式传（:558） | **零改动**（已按必填形态传参） |
| MCP 直调面（`run_operation` from_dict 通道） | `{}` → slot=None → op gs 分支双出口 AssertionError；今日实际卡在更早一层（env 必传构造不了 op）——bug 形态不可达，废除 = 修复+打通一体（bookcard 稿同句式） | env 缺省化打通后：`{"slot": 1-9}` = 合法直调；缺 slot 键 = 构造面 TypeError；`{"slot": null}` = op 守卫 AssertionError（文案自教新契约，kind='supply_box' 双口径，§2.2） |
| 单帧测试/离线直构面 | `CwActionOpenBoxParam()` 零参构造合法 | 零参构造 TypeError（§5） |

### 1.2 记账路径核验：零写占位形态 + box_card 登记 + 有声明 `_decl_bottom`（总契约第八适用者独立申报）；上报层零代码改造；零行为变化面见核验表

**核心辨析（差异预告①②合题）：零写占位形态与总契约「点完即写」如何自洽。**

总契约「点完即写」（action-op.md L20）的时间语义 = **点完立即上报、零两相零补写**——OpenBox 现值满足（op :131-136 点击后立即上报，无确认无探画面）；写语义由**该动作的上报函数单点**定义（L68「每动作恰一个具名函数 = 该动作的字段写操作语义单点」+「零写族策略声明在包 `__init__`」）。OpenBox 的字段写操作语义 = **状态容器零写**（`zero_writes.py:74-90` 全文零 `gs.bench`/`gs.equips`/`gs.gold` 写端）+ `box_card` 登记（:86-88）+ 转移声明构造（:89-90）。即：上报在时点维度「点完即写」完整成立，在载荷维度写的是「登记 + 声明」而非逻辑态直写。

「腾位归下一入口 heavy 实读」的语义与自洽条件：开箱即腾席（武装箱占席道具使用后消失），但腾席事实**不在动作时点写 bench 槽位表**，而由下一次备战入口 heavy 观察的实读全量覆盖——权威真值链 = 观察（prep-contract §2 条 4 同源）。这不是「点完不写等下一轮补写」的被禁形态（L37「等下一轮看画面才补写」禁的是**延迟决策记账**；本件登记+声明即时落账，悬空的只有 bench 腾位位，且悬空段零消费面）。**零写安全的结构前提 = R7 终结化**（op `terminal = True`，:57-58）：上报后 op 立即经终结口交回主循环（`cw_screen_prep.py:940-948`），武装箱选择模态压住备战画面期间，决策环不再消费 bench 槽位表——「腾位悬空段零消费窗口」。对比 tome/bookcard 必须腾位直址写的根源：两件是环内续跑动作（OpenTome 非终结 / OpenBookcard 终结但上报后同 visit 决策面仍可能消费槽位表），不写腾位 = 同帧决策重复派发开件或把空槽当占用；OpenBox 终结转移使直址写**可省**——零写 + 实读覆盖是更彻底的「逻辑态不做将被立刻覆盖的写」形态（直址写腾位后下一 heavy 实读照样整表重建，逻辑态写只在悬空段被消费时才有价值）。**Heavy 实读补写时序申报（两执行面）**：

- **实机链**：OpenBox 上报（零写+登记+声明）→ 终结口交回主循环（wait=`terminal_wait` 1.8s，`cw_screen_prep.py:947-948`）→ 主循环重识别（box_card 登记分发档名 `'货币战争-备战-武装箱选择'`，`cw_overlay_register.py:52`）→ 分发 `CwScreenBoxPick` 选卡（`cw_loop.py:898-902`）→ PickBoxCard 选卡（零写族，`zero_writes.py:174-181` 消费 box_card 登记）→ 回主循环 → 备战入口 heavy 观察（bench 整表重建 + 装备快照唯一写端重写——腾位与装备入库同帧落账）。悬空段 = 选卡期间，bench 槽位表无决策消费面。
- **sim 链**：`declare_world(decl trigger='open_box')` → backend advance 分派 `_on_open_box`（`cw_sim_backend.py:2399-2400`）→ 候选呈现（:3078-3089）→ 决策环 `decide_box_card` → PickBoxCard → `_on_box_picked`（:2401-2402 → :3091-3109，`gain_equipment` 获得链入栏）→ 步界 `_sync_owned_equip_xy_placeholders`（:2439 → :5199-5246）。sim 侧 bench 域真值由后端状态副本按箱消失推演（零悬空消费问题同构）。

**宪法③核验（空集成立，双面）**：`CwActionOpenBoxParam` 现无名称语义字段（:569-574 仅 slot/route_tag），本批**零新增**；记账面名称消费逐处核验：`_report_zero_write` 的 `param` 形参仅签名透传（`zero_writes.py:62-70` 函数体零读 param）、`produced_by` 类零——本件上报连 `write_logic` 调用都无（零写族无记账写端），「produced_by 常量类名字符串」面在 tome/bookcard 存在、本件**整面不存在**——宪法③对本件 = 比前两件更强一档的空集（参数面零名称字段 + 记账面零 param 消费）。

**总契约三条在零写形态的退化**（对照 bookcard 稿 §1.2 三条逐条）：①反查时序——本件**无反查**（零键域：零坐标键零槽位键，上报函数零 param 消费），整条退化成立；②陈旧窗口——直址写形态靠「槽位表恒稳」维持窗口判定，本件靠「悬空段零消费」（终结转移结构性保证，§1.2 前段）消除窗口——比直址写更强；③唯一性——`box_card` 登记与 PickBoxCard 消费一一对应（register-consume 契约，`cw_overlay_register.py` 封闭九类 + 选卡消费族②），声明 `trigger='open_box'` 与 backend 分派一一对应（`ADVANCE_TRIGGER_KINDS` 封闭集，`cw_sim_backend.py:1605-1606`）。零新增差异。

**上报层改造裁决：代码零改动（家族八批首例）。** `zero_writes.py:74-90` 无 None 分支（零 param 消费）、无腾位写、无拒单出口（`_report_zero_write` 恒 `applied=True`，`zero_writes.py:69`——「applied=True = 动作受理，非拒绝」）——无任何退役面。tome 稿 §9 行 1 差异预告①「上报层零 None 分支需退役」实核兑现。**唯一改造 = 函数 docstring 补申报一段**（slot 必填口径 + 总契约第八适用者零写形态标注 + param 零消费申报），最小 diff，不改任何可执行行为。函数体内既有「§1.7」旧章节引用与 :46-48 声明改底层屏注释**保留不动**（语义自述句，非本批辖域）。

**零行为变化核验表**（上报函数零代码改造的等价性义务，tome 稿 §1.2 表同构，差异行加粗）：

| # | 面 | 现值 | 判 |
|---|---|---|---|
| 1 | 唯一消费方 | grep 全仓：`report_action_open_box_param` 消费 = op 直调单点（`cw_open_box_action.py:22-24,131`）；商店序列驱动器/回放驱动器/sim 直调零命中 | 改造无第二消费面断裂 |
| 2 | **状态容器写** | **零写**（:74-90 全文零 gs 写端；腾位归下一入口 heavy 实读） | 零变化——**本件无「腾位写形状」行可核（bookcard/tome 表 #2 对应面在此域不存在）** |
| 3 | **拒单形态** | **无拒单出口**（`_report_zero_write` 恒 applied=True；零写族无 slot 校验——目标槽错传在零写形态下不可检出，真值归 heavy 实读对账） | 零变化——op 侧**无拒单 detail 段消费**（与 bookcard/tome 的 `*_slot_missing` 拒单段结构性差异，§3.2/§4 明示） |
| 4 | overlay 登记 | box_card 直登（:86-88，source='s6_click@open_box'） | 零变化（实机外循环分发 CwScreenBoxPick / sim 模态呈现两消费链不动，§1.6 条 3） |
| 5 | **WorldDecl** | **有声明**：`_decl_bottom(gs, 'open_box')`（:89-90；next_screen = `node_screen_now(gs)` **底层屏**，:51-54）——差异预告②兑现：与 tome 恒零声明**不同构**（tome 无喂入行无 data；本件 op 侧既有 `declare_world` 喂入 + `data=world_decl`，op :127-137），与 bookcard 纯转移同构但 **next_screen 语义不同档**（bookcard = `node_screen_now` 亦底层屏——两件同值；bookcard trigger='' / 本件 trigger='open_box' 挂 backend 开箱采样分派，:2399-2400） | 零变化（逐位保留） |
| 6 | kind='supply_box' 口径 | 上报面零 kind 消费（kind 只活在决策半现算与登记 kind='box_card'——两串不同域：bench 槽位 kind='supply_box' / overlay 登记 kind='box_card'，勿混） | 零变化（申报防串用） |

### 1.3 交替机制：开箱 aftermath 对 `owned_equip_xy` 零交集，`cw4_equip_xy_pending` 零置位端、零机制改动（推演表照 MoveUnit 稿 §3 格式；A1 收编申报照 SellDeployed 稿 §9 行 2 句式）

**推演（OpenBox aftermath 对坐标伴随域的影响面，逐域核验）**：

| 领域 | OpenBox aftermath 动到的域 | 判 |
|---|---|---|
| bench 腾位 | 零写族——`gs.bench` 零写端（§1.2），腾位归下一入口 heavy 实读整表重建 | 装备库存网格是独立面板区，备战席占用变化不驱动其布局；heavy 实读时 `owned_equip_xy` 全量重建（装备快照唯一写端，prep-contract §2 条 7）——伴随域恒新鲜 |
| 装备入库（获得方向） | **不在本动作 aftermath**——获得发生在 `PickBoxCard` 落地时点：实机 = 选卡后回备战 heavy 观察（零写族，`zero_writes.py:174-181` 选卡上报亦零写）；sim = `_on_box_picked` 的 `gain_equipment` 获得链（:3099-3102）+ 步界占位同步 `_sync_owned_equip_xy_placeholders`（:5199-5246） | **装备网格增长方向**：实机侧无增量问题（heavy 全量重建）；sim 侧 = 占位坐标按计数差 append、存量条目格位不动（:5235-5241 逐差额 append 占位序号恒新）——sim 结构性满足 A1（「获得件插入只占空格、已登记条目格位不动」）。本件与「获得类」的关系比单击两件更直接：武装箱链 = 装备获得通道，但获得时点在选卡动作，不在开箱动作——OpenBox 与 PickBoxCard 两上报**双双零 `gs.equips` 写端**，整链无一处置位端需要加 |
| 模态遮挡段 | 武装箱选择画面在场期间备战被压 | 装备网格坐标伴随域无人读（决策环已交回选卡画面）；选卡完成回备战 heavy 观察重写快照——零陈旧消费窗 |

**结论：OpenBox aftermath 不触发 `owned_equip_xy` 失效——交替标志 `cw4_equip_xy_pending` 本批零置位端、零机制改动**（现役置位端 = 穿装发出点 + 工具原子发出点，不变）。**A1 收编申报**（SellDeployed 稿 §9 行 2 收编面清单内 OpenBox 在列）：A1 成立 → 本件零置位端成立（ aftermath 零 append）；A1 不成立 → 回退批统一收编置位端时，OpenBox 点位同为**零贡献成员**（获得发生在 PickBoxCard，即便收编也加在获得动作帧而非开箱帧——而 PickBoxCard 上报同样零写，实机侧获得真值归 heavy 实读，收编点在实机形态下无可置位对象）。bookcard/tome 稿已各自申报零贡献成员（两件获得类 = PickExpertInvite/PickStarTome 选卡时点），本件对称成立且更直接——武装箱开箱链是全开件族中唯一「获得物 = 装备」的链，链上两动作零写、获得落账归 heavy 实读/sim 步界同步，与 A1 假设的辖域零交叉。

### 1.4 拖点/点击：守卫上界迁移 op 内现读（`_bench_pts` 物理退役随本批实施落）；点击目标 = 武装箱开启位按钮区（**不住 `_bench_pts`**——独立 area 族辨析）；单击族形态零 env 消费（同判应用，见 open-tome 稿 §1.4）

- **守卫上界迁移（同判应用）**：`ex._bench_pts`（executor 构造期缓存，`prep_actions.py:363`）→ op 内执行期现读 `row_area_centers(self.ctx, '备战栏')`（静态档，值理论逐位同）。bookcard/tome 稿 §1.4 同式已两度实施，第三例照搬。
- **点击目标辨析（差异预告③，本稿独立裁决——关系 `_bench_pts` 退役准确性）**：本 op 点击点 = `area_center(ctx, f'武装箱开启位-{slot}')`（op :111）——**「武装箱开启位-N」是独立 area 族**（`assets/game_data/screen_info/currency_war_battle_prep.yml:1126-1252`，武装箱开启位-1..9 九档全在档、与备战栏-N 同档共存），**不是「备战栏-N」族成员，不住 `_bench_pts`**（`_bench_pts = row_area_centers(ctx,'备战栏')` = 槽位本体族点位表）。OpenBox 对 `_bench_pts` 的消费 = **仅表长**（:77/:83 守卫上界），非坐标源——点击坐标恒走「武装箱开启位-N」直查。辨析结论：**`_bench_pts` 退役裁决与点击目标零耦合**——迁移后守卫上界改 op 内现读备战栏点表（同判），点击点 `area_center(self.ctx, f'武装箱开启位-{slot}')` 直查**逐字保留**（坐标语义、值、档零变化）。与 bookcard/tome 的差异 = 交互目标：两件点「备战栏-{slot}」槽位本体中心弹浮层，本件点「武装箱开启位-{slot}」**开启按钮区**开箱——area 族不同名是游戏交互结构的如实镜像（箱体占槽、开启钮独立布局），不是建档冗余。守卫上界用备战栏点表（槽位域 1-9）与「武装箱开启位-N」九档一一对应（同槽位号同基）——`_ctx_slots` 1 基实证（§1.1 口径②）+ 画面档九档 grep 实证双背书。
- **两读并存申报（同判）**：守卫读 `row_area_centers` 表长、点击读 `area_center` 单名直查——按名直查缺档自然异常比按位取表更防建档漂移误点（bookcard 稿 §1.4 同款论证），两读并存为有意形态非冗余。`row_area_centers` docstring 拖点权威分域（prep_actions.py:164-170）是拖点派生式辖域，本 op 无拖拽交互不涉——零新增分域声明。
- **零 env 消费**（同判 bookcard 稿 §1.5 / tome 稿 §1.4 条 3，单域零消费档）：签名改 `env: PrepExecEnv | None = None`，op 体零 env 消费（无域分派/无 ledger/无 executor 依赖）；`PrepExecEnv.executor` 本就 `| None` 可缺省（`prep_actions.py:319`），注册表构造路径恒传完整 env 兼容不动（`prep_actions.py:469-471` / `cw_action_registry.py` 组装面）。
- **`_bench_pts` 物理退役申报边界（本批 = 收官批，与 bookcard/tome 的「非退役批」申报相反向收口）**：本批迁走 OpenBox 后，`PrepActionExecutor._bench_pts` 现役 op 消费清零（grep 实锤：src 全仓消费 = `cw_open_box_action.py:77,83` 一家 + `cw_screen_prep.py:181,212-213` **同名异物**——观察域私有惰性缓存， bookcard 稿 §9 行 2 已辨析防误伤，本批退役 executor 属性时以此防误删观察侧）。实施批删除属性本体（§3.4），与遗留⑤合流清场（§9 行 2）。

### 1.5 交替载体/新鲜度零涉面

本 op 无坐标伴随域消费（slot 键域动作），`cw4_equip_xy_pending` 的置位端（穿装 mandate M7 + entry 第 7 步）与消费端（Obs in_place 重观察帧）全部不涉——零改动。补此节仅为一句话清边界，防审查者误问（bookcard/tome 稿同节同判）。

### 1.6 sim 形态自洽：gate 归位（点击+睡眠同 gate）；**有声明形态保持**；box_card 消费链零变化（同判应用，见 open-tome 稿 §1.6；差异点独立辨析）

1. 机械 gate：现状点击已 gate（:112-114）、睡眠未 gate（:117-120 无条件）——迁移后 `mouse_move+click+sleep` 全段收进 `mechanical_io_allowed()` gate（tome op 现值 :130-139 同构）。sim 局开箱帧从「op 睡 1.8s + 终结口 wait 1.8s」双层变「终结口 wait 1.8s」单层（§7 条 3）；实机双层保留零差异。
2. 期望态推进：上报函数族两执行面同源——op 直调唯一消费面（§1.2 核验表 #1），sim 局经同一 op 路径走同一上报函数。**有声明差异**（vs tome 零声明）：op 侧 `declare_world` 喂入行 + round 结果 `data=world_decl` **逐位保留**（op :127-137 现值已具备，与 bookcard 同构）——backend advance 按 `trigger='open_box'` 分派 `_on_open_box`（:2399-2400），`_reconcile_next_screen(decl)` 按底层屏声明对账——武装箱选择画面的实际呈现走 `_present_modal(SCREEN_BOX)`（:3086，模态层），声明 next_screen = 底层屏（备战档）与模态呈现并行不冲突（zero_writes.py:46-48 既有申报「声明改底层屏——武装箱选择画面的出现事实改由登记承载」）。
3. overlay 登记 box_card 的 sim 消费链（零变化申报）：`_on_open_box` 候选写入 = `report_screen_box_pick_obs`（:3087-3089，写 `box_card_names`/`box_card_names_xy` 候选）；PickBoxCard 落地 `_on_box_picked`（:2401-2402）走 `gain_equipment` 获得链（:3099-3102）+ `_dismiss_modal`。登记/消费在上报函数内与 sim 后端分派两处（两执行面同一行代码或同一分派键），本批零 sim 改动。**sim `armory_boxes` 读数口径**（任务点名核实面）：sim 局 op 上报走 `declare_world`（候选呈现由 backend 承载），op 不消费 extras `armory_boxes`；实机直调双口径（§1.1）与 sim 链零交集——sim 自洽零分叉。
4. 直调路径：MCP `run_operation` 传 `{"slot": N}` → 守卫闭合域内机械（sim 环境 gate 静默）/实机点击 + 上报；非法值 → 守卫 AssertionError 零点击（守卫在 gate 外，两执行面同守）。

## 2. 新参数面定稿

### 2.1 字段集变更（`kernel/cw_vocab.py::CwActionOpenBoxParam`，:569-574 现值）

**零新增、零删除字段**——`slot` + `route_tag` 两字段保留；变更 = `slot` 必填化（同判应用，见 open-tome 稿 §2.1；docstring 改写按 tome 类 :578-604 终态模板换 box 口径）：

- `slot: int`（去 `| None = None` 缺省，必填第一位）：[索引定义] 注释三要素——坐标系 = 备战栏画面物理槽位 1 基（area 序，坐标参数化机械动作族同系）；取值时机 = 生成期快照（决策半 `_consumable_open_action` 按 gs bench kind='supply_box' 槽位现算，`entry.py:553-558` 单一现算点；直调 = 双口径任一，§1.1）；写入端 = 发出点。None 语义废除申报一句（§1.1 指针）。
- 类 docstring 改写：「slot=None → 第一箱」句删除（:571），替换为必填申报 + 记账路径总契约**第八适用者**申报（零写占位形态：状态容器零写 + box_card 登记 + `_decl_bottom(gs,'open_box')` 转移声明，腾位归下一入口 heavy 实读——与前两件腾位直址写不同构）+ 宪法③空集 + 直调传参双口径指引（bench.slots kind='supply_box' 下标+1 / armory_boxes 元素 slot 直传）。
- `route_tag`（kw_only + `action_key_exclude`）不动。
- 补 `from_dict` classmethod：共享 `cw_vocab.action_param_from_dict`（:659-667）一行委托（tome :609-613 家族同款）。最小 dict = `{"slot": 1-9}`；缺 slot 键 = `cls(**…)` 缺参 TypeError（禁在 from_dict 加缺省兜底——共享形态单一源，不为本件开例外）。
- `action_key` 幂等键零变化：`slot` 入键（行为参数，正确）、`route_tag` 不入键（既有 metadata）。词表 `action_key` docstring 失配为本批零触及面（§9 行 3）。
- 词表模块头「开件三类」两句（`cw_vocab.py:11-13` 与 `:144-148`）辖域核验：两句述 row/slot **坐标系语义**（画面物理槽位 1 基），三类字段定义仍在且语义不变——句子保留零改动（bookcard/tome 批同判）；None 缺省残面本批后清零（全流水线无 `slot | None` 形态残存——词表侧终态申报随本批实现，模块头句子本身不述缺省语义无需改）。

### 2.2 守卫断言（op 内，校验落点契约 = action-op.md L55；同判 bookcard/tome 稿 §2.2 双形，文案换 supply_box 双口径）

1. **None 形**：`action.slot is None` → 断言，文案带契约指引（kind='supply_box' 双口径版）：`CwActionOpenBoxParam slot 必填(备战栏物理槽 1-9 基 1;直调按当帧 extras bench.slots kind=supply_box 槽下标+1 或 extras.armory_boxes 元素 slot 字段直传;slot=None 现算语义已随参数面迁移批废除,现算归发出点 entry._consumable_open_action),零点击`。加强理由同判 bookcard 稿 §2.2 条 1（TypeError 不指向参数面，废除语义必须自教）。
2. **越界形**：`not (1 <= int(action.slot) <= len(pts))` → 断言（`pts` = op 内现读 `row_area_centers(self.ctx, '备战栏')`；下界显式闭合禁负下标回环；文案带词表参数语义与合法域 + 画面档定位 `画面档={SCREEN_NAME}`，tome op :118-125 同构）；空点表命中同一断言 = 建档漂移哨语义，不设独立分支。守卫在 `mechanical_io_allowed()` gate 外（sim/实机两执行面同守）。守卫上界取备战栏点表（槽位域），点击点走「武装箱开启位-{slot}」直查——两 area 族同槽位号同基（§1.4 辨析），越界判定域与点击目标域对齐无漂移。

**零 gs 读声明**：机械路径（守卫 + 点名直查 + 点击 + 等待）零 `game_state_from_ctx` 消费——自上报取容器 = 上报路径非机械定位（bookcard 稿 §2.2 同款裁定）；宪法①修复完成（本批实质修复项，修复+声明双真）。现状 op 的 gs 预取/二次取双段（:84 None 分支取 + :127-129 上报段补取）随 None 分支删除**坍缩为上报段单次取**（tome op :145 同形）。

## 3. 牵涉面清单（逐文件；grep 全量已核，行号 = HEAD `9f8d48bad`）

> 路径根 = `src/sr_od/application/currency_war/`。

### 3.1 `kernel/cw_vocab.py` — §2.1：slot 必填化 + from_dict + 类 docstring 改写（:569-574）

### 3.2 `operations/cw_op/cw_open_box_action.py` — op 执行体重写

机械自持：None/越界两形守卫（§2.2）→ `area_center(self.ctx, f'武装箱开启位-{slot}')` 建档直查（**点击目标族名逐字保留**，零防御口径保留）→ sim gate（点击 + `time.sleep(_OVERLAY_ANIM_WAIT_S)` 同 gate；`_OVERLAY_ANIM_WAIT_S` 函数内局部 import 形态保留不动）→ `self.ctx.controller.mouse_move + click`（防吞点击口径逐字沿用）→ detail 组装 → 自上报：`gs = game_state_from_ctx(self.ctx)`；`gs is None` = 无处记账跳过（零上报零异常，`world_decl=None`、data=None——gs 缺席即无声明载体，既有行为保留）；`outcome = report_action_open_box_param(gs, action, ChannelSig(family='logic_action', actor=type(self).__name__, mode='compute'))`；`world_decl = outcome.world_decl` + `cw_sim_ports.declare_world(world_decl)` + `return self.round_success(detail, data=world_decl)` **逐位保留**（:127-137 现值形态，bookcard 同构）。**无拒单 detail 段**（零写族恒 applied=True，§1.2 核验表 #3——bookcard/tome 的 `outcome.applied` 分支不搬）。删除面：`replace` import（:16，None 分支专用）、`_BOX_BENCH_KIND` 常量与三处现算注释（:38-43）、`ex` 全部窥探（:75-76/:77/:83/:111/:113-114）、gs 预取段（:84-107 坍缩）。签名改 `env: PrepExecEnv | None = None`（TYPE_CHECKING import 保留供注解）。`terminal = True`/`terminal_wait = 1.8` 类属性（:57-62）**零改动**——终结形态保留是本件与 tome 的形态差异（tome 非终结）。docstring 重写：模块头与类 docstring 按家族参数面迁移形态行文（起终点行沿用 :47-48 现骨架；终结动作申报与「武装箱选择画面由外循环分发 CwScreenBoxPick 选卡」保留；参数面指引 = slot 双口径直调 + 必填双出口报错申报；直调指引 = run_operation `{"slot": N}`、env=None 缺省备战档；记账总契约**第八适用者零写占位形态**申报（零状态容器写 + box_card 登记 + `_decl_bottom` 声明 + 腾位归下一入口 heavy 实读——与 tome 第七适用者腾位直址写不同构）+ **零拒单出口**申报（零写族无 slot 校验，真值归 heavy 实读对账——直调错传 slot 的后果 = 点错槽开启失败，外循环按实读重派，非静默错账）；转移声明语义申报（`declare_world` 喂入 + data 携声明，trigger='open_box'）。模块头引用规范路径名顺改：`flow/action_ops.md` → `flow/action-op.md`（tome 批同款）；`op-layer.md` 指针保留（全仓既有面）。

### 3.3 `kernel/cw_action_report/zero_writes.py` — **代码零改动**；docstring 补申报一段（§1.2 裁决）

`report_action_open_box_param` docstring 追加：slot 必填申报 + 总契约第八适用者零写形态标注 + param 零消费申报（`param` 形参签名透传零读取——零写族形态自教）。函数体逐位不动（核验表 §1.2）。文件其余函数零触及。

### 3.4 `prep_actions.py` — **开件族收官合流清场（实施批义务清单）**；`row_area_centers`/`area_center`/`_OVERLAY_ANIM_WAIT_S` 原语本体零改动

本批随 OpenBox 迁移落的开件族收官退役（第五棒终审已裁定 grep 背书删除安全；**全部为实施批动作，本稿只裁决与清单**）：

| # | 退役件 | 现值定位（HEAD） | grep 背书（本稿已核） |
|---|---|---|---|
| 1 | `_bench_pts` 属性（本批迁走 OpenBox 后零 op 消费） | `:363`（构造期赋值）+ `:357-362` 注释段 | src 消费 = `cw_open_box_action.py:77,83` 一家（本批随 op 重写拔除）+ `cw_screen_prep.py:181,212-213` **同名异物防误伤**（观察域私有惰性缓存，bookcard 稿 §9 行 2 辨析，不动） |
| 2 | `_front_pts` 属性（遗留⑤） | `:364` | 零消费（仅构造期赋值 + 两处过期注释提及） |
| 3 | `_back_pts` 属性（遗留⑤） | `:365` | 零消费（同上） |
| 4 | `_drag` 方法（遗留⑤） | `:494-522` | `\._drag\(` 全仓零命中（SellDeployed 已随第四棒迁移改消费模块级 `drag_char_guarded`） |
| 5 | 类 docstring 过渡宿主句（三处过期注释之一） | `:330-334`「``_drag`` 方法与 ``_front_pts/_back_pts`` 点表 = 席位域待迁移动作(SellDeployed 等)的过渡宿主…」 | SellDeployed 已迁，句过期——随 #2-4 删除改写 |
| 6 | 点表段 SellDeployed 仍消费句（三处过期注释之二） | `:361-362`「SellDeployed 过渡期仍消费 _front_pts/_back_pts(其迁移批退役)」 | 同上过期——随注释段收口删除 |
| 7 | `_drag` docstring 段（三处过期注释之三） | `:494-498`（随 #4 方法本体删除） | 同上 |

收口口径：构造段注释（:357-362）改写为退役终态申报一句（如「点表属性已随开件族收官批物理退役——全部消费 op 已随各自参数面迁移批改 op 内现读 `row_area_centers`/`row_drag_points`」），或整段删除由属性消失自明（实施角色按最小 diff 裁决，两形皆合规）。类 docstring 的「角色拖拽统一拖拽原语 = 模块级 drag_char_guarded」句**保留**（`drag_char_guarded` 仍是现役原语，宿主 = 模块级函数，MoveUnit/SellDeployed/SellBench op 自持消费）。模块头与 `execute`/`_dispatch_action` 内的 `flow/action_ops.md` 旧指针（:18/:368/:403/:409/:458）**不顺改**（全仓改名面，非本批辖域防扩散——tome 批同样只顺改自身文件）。

⚠️ 在飞申报：本文件当前 HEAD 干净（不在工作区 M 列表，已核），实施时复核；绝不卷入并行批改动行。

### 3.5 发出面 `strategies/impl/mandate_v1/entry.py` — 零改动

`:551-558` 三元组 supply_box 行 + `atom_cls(slot=idx + 1)` 已显式传 slot；`:148-149` `_TRUNCATION_POINTS` 含本类零变化（截断分类 = 类名面，与参数缺省无关）。

### 3.6 `operations/cw_op/cw_action_registry.py` — 零改动

import（:92-93）与注册行（:179）类名不变；组装恒传 env（`prep_actions.py:469-471`）兼容缺省化。

### 3.7 `operations/cw_screen/cw_screen_prep.py` + `operations/cw_loop.py` + `operations/cw_screen/cw_screen_box_pick.py` — 零改动（终结口分支与分发链申报）；注释收口一处

- 终结口 OpenBox 分支（`cw_screen_prep.py:940-948`）零改动——`terminal=True`/`terminal_wait=1.8` 类属性不变，`wait=op_cls.terminal_wait` 消费不变。分支注释 :944「与 ``_open_box`` 动画等待 ``_OVERLAY_ANIM_WAIT_S`` 等价」**指针失据**（`_open_box` 替身函数已不存在，grep 实锤唯一提及 = 本注释）——随批收口为「与 `prep_actions._OVERLAY_ANIM_WAIT_S` 逐字等价」表述（本件 op 相关第四处过期注释，tome 稿 §9 行 1 未列、本稿实核补列）。
- 主循环双画面分发（`cw_loop.py:892-902`）：「货币战争-武装箱弹窗」（获得说明弹窗 `CwScreenArmoryBox`，获得链时点出现）与「货币战争-备战-武装箱选择」（四选一选卡 `CwScreenBoxPick`，box_card 登记分发）是**两个不同画面 op**——本 op 点开启直弹后者（zero_writes docstring 既有申报），前者与本批零交集。申报防后续读者按「武装箱」族名误判分发关系。
- `cw_screen_box_pick.py` 选卡链零改动（box_card 登记消费 = PickBoxCard，动作面零变化）。

### 3.8 `obs/cw_identity_obs.py` + `obs/recognizers/battle_prep_recognizer.py` — 零代码改动；G2 收口义务（docstring 基声明，实施批落）

- OpenBox 迁移后 op slot 链走 gs bench kind='supply_box' 扫描与「武装箱开启位-N」建档直查，**零 obs `read_*`/`find_*` 族消费**（同 bookcard/tome 终态）——G2 的 op 消费面消失；残余消费 = 观察分类域（`cw_identity_obs.py:854` 备战席槽位分类 / `:1424` 低分渲染兜底）与 recognizer extras（`battle_prep_recognizer.py:407-408`）。
- **G2 收口 = docstring 补 slot_idx 基声明**（实施批最小 diff）：`find_armory_boxes`（:1312-1313）与 `read_armory_boxes`（:1336-1337）docstring 补「`slot_idx` = 备战栏物理槽位 1 基（`_ctx_slots` `range(1, count+1)` 产，缺失档跳过不压缩——与 `row_area_centers` 的按序压缩不同构）」+ center 几何语义（槽 rect 几何中心）。顺带勘误申报：recognizer extras doc :458「cx/cy=开启按钮中心」与实现（:1332 槽 rect 中心）存在表述漂移——不影响本批（op 点击点恒建档直查，零 extras 坐标消费），勘误一句随 G2 收口落（实施角色裁决保留或改写）。

### 3.9 `telemetry/cw_match_recorder.py` + `match_archive.py` — 零改动

bench 道具槽记录按 kind ∈ supply_box/tome/bookcard 过滤（`cw_match_recorder.py:133-135`）读 gs 槽位表，与 param 面零耦合；`match_archive.py` 零 OpenBox 序列化面（grep 零命中，bookcard/tome 稿 §3.8 同判）。

### 3.10 测试仓镜像测试 — 见 §5

### 3.11 文档面 — 见 §8

## 4. op 执行语义（迁移后）

1. None 守卫 + 越界守卫（§2.2，gate 外——两执行面同守）。
2. 点击点静态直查：`area_center(self.ctx, f'武装箱开启位-{slot}')`（开启按钮区，零截图零识别零 gs；缺失 = 自然异常，零防御既有口径）。
3. sim 分支：`mechanical_io_allowed()` 为假 → 机械段（含固定动画等待）静默跳过（上报函数族照走——sim 期望态推进 = 自上报单点，两执行面同源）。
4. 实机机械段：`mouse_move` 防吞 + `click` → `time.sleep(_OVERLAY_ANIM_WAIT_S)`（1.8s 开箱动画等待，gate 内，值逐字沿用）。
5. 自上报：box_card 登记 + `_decl_bottom(gs,'open_box')` 声明（上报函数单点，零状态容器写）→ `declare_world` 喂入 → round data 携声明（journal 记账面，既有行为逐位保留）。
6. round 结果：恒 `round_success('开箱槽{slot} ✓(发出即上报:零写族+登记+声明,落地归下一入口heavy实读)', data=world_decl)`（机械成功语义；零 round_fail 通道零拒单段——detail 文案升级判读申报 §7 条 1）。

**决策侧参数现算契约适用申报**：本 op 发出域 = 备战决策环（entry ① prep 实体面卡片分支 + 第 0 步溢出自救态 2 共用 `_consumable_open_action`，每动作重 decide、同帧承诺成立）。无跨帧队列形态、非战斗链批量发射辖域。**终结动作语义保留**：terminal=True + terminal_wait=1.8 类属性零改动——点完开启即返回主循环（`_terminal_exit` 分支 :940-948），武装箱选择画面由外循环按 box_card 登记分发 `CwScreenBoxPick` 选卡 `PickBoxCard`（选卡消费族②，`zero_writes.py:179` 消费登记）。规划器截断分类面（`_TRUNCATION_POINTS` 含本类，entry.py:149）零变化。**「无箱/指定槽无箱 = 不发出」语义归属申报**：该条件住发出面决策半（`_consumable_open_action` 按 kind 扫描，无 kind 槽 = 返回 None 不构造动作），不在 op——op 只对显式 slot 机械执行，slot 语义正确性归决策现算 + 越界守卫，零写形态下「错槽开空」由外循环按实读重派（§3.2 docstring 口径）。

## 5. 测试设计（sr-od-test，按 AGENTS.md §11.4 harness 规范；镜像路径，命名无批次号；**对照 tome 7 锁型裁剪**——裁拒单段锁、换零写锁）

> 现场实态：sr-od-test 现存 OpenBox 专属测试零命中（grep `CwActionOpenBox|cw_open_box` 零命中）；`_bench_pts/_front_pts/_back_pts/executor._drag` 测试直调零命中（test_prep_actions.py 的 `recorded_drags` = 测试自建 controller stub 属性，非 executor 成员）——`test_prep_actions.py` 既有面零改动预期，四件退役后由 L2 阶梯跑通背书。

1. `test/sr_od/application/currency_war/kernel/cw_vocab/test_cw_vocab.py`（既有文件扩展，紧邻 tome/bookcard 组）
   - OpenBox `from_dict`：最小 dict `{"slot": 5}` 逐字段断言（`route_tag=''`）；未知键忽略；**缺 slot 键 = TypeError**（必填锁测）；`{"slot": null}` 可构造（None 拦截归 op 守卫的家族口径锁测）。
   - `action_key`：slot 不同产不同键；`route_tag` 不入键。
2. `test/sr_od/application/currency_war/operations/cw_op/test_cw_open_box_action.py`（新建；harness 剧本，结构照 `test_cw_open_tome_action.py` 夹具形态：controller 记录 stub + monkeypatch 防污染 + screen_info 真档案同源派生期望值）
   - **None 守卫锁测（审计 bug 修复锁，第三例收官）**：`slot=None` → AssertionError（文案含「必填」与 kind='supply_box' 双口径指引关键词）且点击记录零条目。
   - 守卫：slot=0 / 负值 / 越界（≥10）→ AssertionError 零点击（负下标回环防锁）。
   - 实机形态（真档案派生）：点击记录 `== 武装箱开启位-N rect 中心`（**期望值派生源 = 武装箱开启位 area，非备战栏-N**——本件与 tome/bookcard 同源锁测的派生域差异）；mouse_move 先于 click（防吞口径顺序锁测）。
   - **零写锁测（本件特色锁，替代 tome 拒单段锁测）**：正常帧 → round_success 且 **gs bench 槽位表零变化**（零写族锁测——与 tome/bookcard 的「腾位写断言」反向锁，本件差异点锚一）+ **box_card 登记在场**（`gs.screen_changes.pending` 含 kind='box_card' 条目——overlay 登记锁测）+ **round data 携 WorldDecl**（`next_screen = node_screen_now` 推导值=备战档、`trigger='open_box'`——有声明形态锁测；与 tome 零声明反向、与 bookcard 同构但 trigger 值不同——差异点锚二）+ detail 无拒单段（恒 applied=True 锁测）。
   - gs 缺席帧（无 session 种子）→ 机械已发 + 零上报零异常（data=None，无处记账跳过形态锁测）。
   - `env=None` 全链跑通；sim 形态（port 关闭 → 点击记录零条目 + 自上报照走 + 登记与声明照写）；`with fast_sleep(): op.run()`。
3. `test_action_registry.py`（既有面）：零改动预期（terminal=True/terminal_wait=1.8 类属性不变——终结集测试对象含本类现值已是，零变化）。
4. `test_prep_actions.py`（既有面）：零改动预期（四件退役零测试直调，grep 已核）。

### 5.1 实施批验收自核清单（grep 零残留断言组；实施 commit 前逐条跑，全绿才交验收）

**src 面**：

1. `grep -rn "_bench_pts" src/sr_od/application/currency_war/prep_actions.py` → **零命中**（属性退役；`cw_screen_prep.py` 命中属同名异物观察域，不在本断言域）。
2. `grep -rn "_front_pts|_back_pts" src/sr_od/application/currency_war/prep_actions.py` → **零命中**（遗留⑤）。
3. `grep -rn "\._drag\(" src/sr_od/application/currency_war/` → **零命中**（遗留⑤；`drag_char_guarded`/`DragCwChar.drag_char` 不受影响——搜带点调用形态防误伤）。
4. `grep -n "ex\.|env\.executor|_BOX_BENCH_KIND|from dataclasses import replace" src/.../operations/cw_op/cw_open_box_action.py` → **零命中**（窥探拔除 + 常量删除 + None 分支专用 import 删除）。
5. `grep -cn "game_state_from_ctx" src/.../operations/cw_op/cw_open_box_action.py` → **恰 1**（上报段单次取，机械路径零消费——宪法①修复锚）。
6. `grep -rn "_open_box" src/sr_od/application/currency_war/` → **零命中**（含 `cw_screen_prep.py:944` 过期指针收口后）。
7. `grep -rn "'supply_box', CwActionOpenBoxParam" src/sr_od/application/currency_war/strategies/` → **恰 1**（`entry.py:553` 三元组行——发出面唯一构造点恒在；`:558` 经 `atom_cls(slot=…)` 变量调用，类名字面不出现，防 grep 误判零命中）。
8. `grep -n "slot is None" src/.../operations/cw_op/cw_open_box_action.py` → **恰 1**（None 守卫本体；词表字段已无 None 缺省）。

**测试面**：

9. None 直构形态锁测在场：测试文件含 `CwActionOpenBoxParam(slot=None)` 构造行且断言 AssertionError + 点击记录零条目（grep 文件名 + 关键词核）。
10. 全量 `uv run pytest sr-od-test/ -m "not slow"` 一次通过（L3）。

**文档面**：

11. `grep -n "_bench_pts" skills/sr-od-dev-currency-war/references/flow/prep-contract.md` → 残留命中仅「已随开件族收官批物理退役」类历史申报句（§8 同步后核语义，不再有「现役消费」句）。

## 6. sim 形态自洽结论

**结论：零 sim 改动。**

1. 机械段：gate 归位（§1.6 条 1）——sim 局与实机同跑同一循环/op/策略，上报函数族两执行面同源直调同一函数（op 直调唯一消费面，§1.2 核验表 #1）。
2. 期望态推进：零写占位形态在 sim 与实机同核零分叉——上报零状态容器写，声明 `trigger='open_box'` 喂入 → backend `_on_open_box` 分派（候选呈现），真值由后端状态副本/下一 heavy 实读承载（两执行面同一声明同一分派键）；武装箱选择画面的呈现 = `_present_modal(SCREEN_BOX)` 模态层，与声明 next_screen=底层屏并行不冲突（zero_writes.py:46-48 既有申报）。
3. overlay 登记：box_card 直登在上报函数内（两执行面同一行代码）；sim 消费 = 候选写入（`report_screen_box_pick_obs`）+ PickBoxCard 落地 `gain_equipment` 获得链 + 步界 `_sync_owned_equip_xy_placeholders` 占位同步（§1.3 推演）——链路零变化。sim 武装箱候选固定集 `box_options()`（占位建模）为 sim-design 既有申报面，非本批辖域。
4. 直调路径：`{"slot": N}` 在 sim 环境 = 守卫通过 + 机械静默 + 上报照走（round data 可核声明）；非法值 AssertionError 两执行面同炸（守卫在 gate 外）。

## 7. 风险与行为变化清单

1. **行为变化：round detail/log 文案升级**（detail 组装升级；**data 面、上报函数面零变化**——本件现值已具备 data=world_decl，无 tome 的「补声明」类变化）——journal 判读面从「开箱槽{slot} → 点开启已发(交回外循环…)」变「开箱槽{slot} ✓(发出即上报:零写族+登记+声明,落地归下一入口heavy实读)」；**无拒单段**（零写族无拒单出口——与 bookcard/tome 的「新增拒单段」行为变化在本件不存在）；遥测分键零新增，首局对照判读申报。
2. **行为修复：slot=None 语义废除（审计挂号 bug 同型第三例=末例收官）**——直调缺 slot/传 null 从「op 内 gs 现算双出口 AssertionError」变「构造面 TypeError / op 守卫 AssertionError（零点击零 gs 读，文案指向参数契约）」——fail-fast + 宪法①修复双真；生产发出面零变化（§1.1 迁移申报表）。判读申报：直调报错形态变化，排障时按新报错文案对参数面。
3. **行为变化：sim 局开箱帧零白睡 1.8s**（sleep 进 gate）——sim 批量局效率改善；实机零差异。
4. **宪法①修复：机械路径 gs 读拔除**——None 形态固有的「现算结果随帧漂移」风险面消除；守卫只判参数合法域。
5. **坐标等价性**：守卫上界（`row_area_centers` 表长）与点击点（`area_center` 同名 area 中心）同源同档零变化；坐标源路径变化（executor 构造期缓存 + `ex._ctx` → op 执行期现读 + `self.ctx`）理论零差，实机落点核对 = 背书义务（§11 验收①——**核对目标 = 武装箱开启位-N 按钮区落点**，与两件先例的槽中心核对不同位）。
6. **死代码退役四件 + op 内三件**：`_bench_pts/_front_pts/_back_pts/_drag`（开件族收官合流，遗留⑤清偿——grep 背书 §3.4）+ op 内 None 分支/`_BOX_BENCH_KIND` 常量/`replace` import。**上报层零退役**（零写族无 None 分支——核验表背书）。
7. **交替机制零改动**（§1.3）：开箱 aftermath 零 `gs.equips` 写端 + 获得时点在选卡动作 = 上报函数现值事实；A1 若不成立，回退批收编点在获得动作帧而 OpenBox 仍零贡献（§1.3 A1 收编申报）。
8. **`_bench_pts` 物理退役的结构风险（本批独有，前七批无）**：删除 executor 属性触 `PrepActionExecutor.__init__`（全动作共宿主）——防误伤锚 = `cw_screen_prep.py:181,212-213` 同名异物（观察域惰性缓存，**不动**）；防回归锚 = L2 阶梯全量（备战域动作全注册表回归）。退役后若考古发现隐匿消费面，该消费面本就该走 op 内现读——属性存在本身是旧接缝（bookcard 稿 §7 条 6 同句式）。

## 8. 文档与 skill

- `skills/sr-od-dev-currency-war/references/flow/prep-contract.md`（**实施批落地**——本稿点名逐节内容，文档随实施 commit 落保正本与代码现状一致；该文件当前 HEAD 干净已核，实施时复核）：§1 L9 动作字段坐标系段——「箱过渡期仍经执行器点表守卫(其迁移批=开件族收官批退役)」句退役，改「开箱已随其参数面迁移批 op 自持守卫 + slot 必填化（None 废除）——开件三类全部完成参数面迁移」；§1 L10 画面点位段——「现役消费 = OpenBox 一家守卫,其迁移批 = 开件族收官批退役」改「`_bench_pts` 已随开件族收官批物理退役——备战栏点表现役消费归各 op 内 `row_area_centers` 现读（MoveUnit/SellDeployed/SellBench/OpenBookcard/OpenTome/OpenBox 全量）」；§3 L27 坐标参数化机械动作取值时机段后补 OpenBox 行句（slot = 生成期快照必填，决策半 `_consumable_open_action` 单点现算，None 语义废除——句式照 L28/L29；直调双口径申报）；§6 G1 活缺口——「现役辖域收窄为开件族箱（OpenBox）」改闭合申报「开件族箱 OpenBox 已随收官批补防线（必填参数 + 决策单点现算），坐标参数化族缺口全量闭合——G1 辖域清空」；§6 G2——收口义务点名（obs 两函数 docstring 基声明 + recognizer 表述勘误，§3.8）。
- `skills/sr-od-dev-currency-war/references/flow/action-op.md`（**本批不动**）：HEAD 实读确认 bookcard/tome 批申报的收尾义务（§5 L131/L130 行改写、L32 批次计数推进、L61 枚举核补）尚未落库——本批同型义务**累积同队列**：§5 L129 OpenBox 行改写（现值行文「`read_armory_boxes` 识别 → 点「开启」→ 固定动画等待…无箱/指定槽无箱 = 不发出」多处过期——零读屏形态/发出面语义误置 op 行/缺 slot 必填/守卫/零写族/终结形态，改写为参数面迁移后终态）；**L90 转移终表 #5 next_screen 列过期（本稿新发现）**：现值列「货币战争-备战-武装箱选择」，代码现值 = `_decl_bottom(gs,'open_box')` → `node_screen_now(gs)` 底层屏（zero_writes.py:46-48「声明改底层屏」申报后文档未跟上；画面出现事实归 box_card 登记承载）——收尾批改「底层屏（node_screen_now 推导；选择画面出现事实 = 登记 kind box_card）」；L32 计数推进（「已迁两批」段补第八适用者：零写占位形态——零状态容器写 + 登记 + 声明，腾位归下一入口 heavy 实读，零键域零反查整族退化）。**四笔归同一收尾批一笔清**（收尾义务批）。
- `skills/sr-od-dev-currency-war/SKILL.md`：零改动（§1.4 参数面规范三分法与本批形态一致；工作区 M 状态的在飞修改不碰）。
- `docs/develop/sr_od/application/currency_war/game_state/fields.md`：零改动（零 gs 字段变更——零写族零新词；`box_card` 登记为既有封闭九类成员）。
- 玩家 skill `skills/sr-od-currency-war/`：零改动（开件族非玩家直调面；`run_operation` 直调 = 开发者/单件会话形态，op docstring 自足——家族七批同款裁定）。
- sim-design.md：零改动（零 sim 行为变更；§6 自洽结论不新增申报行）。

## 9. 申报行（相邻问题，本批不修；任务书点名必列项在行 1/2/3/4/5）

1. **开件族收官声明**：本批 = 开件族第三件即末件——本批后 `PrepActionExecutor._bench_pts` 物理退役随实施批落（§3.4 #1），**动作 op 参数面迁移流水线八棒全收官**（穿装/工具七类/MoveUnit/SellDeployed/SellBench/OpenBookcard/OpenTome/OpenBox）。词表侧 `int | None` slot 缺省残面清零，prep-contract G1 坐标参数化族辖域闭合（§8 同步内容）。流水线级遗留账⑥（词表 `action_key` docstring 失配）与收尾义务批（action-op.md 四笔）为流水线收官后仅存文档面队列。
2. **退役债务⑤合流清场清单**（第五棒终审裁定归开件族收官批）：`_front_pts/_back_pts/_drag` 零消费死代码 + 三处过期注释 + 本稿实核补列第四处（`cw_screen_prep.py:944` `_open_box` 失据指针）——逐件定位与 grep 背书见 §3.4 表，实施批验收自核见 §5.1 断言组 1-3/6。防误伤双锚：`cw_screen_prep.py:181,212-213` 同名异物观察域缓存不动；`row_area_centers`/`row_drag_points`/`drag_char_guarded` 模块级原语本体零改动（现役全 op 消费面）。
3. **词表 `action_key` docstring 与实态失配**（已挂号，流水线总遗留账⑥）：docstring（`cw_vocab.py:1329-1331` 附近）称「reason 卖出归因不入键」，实态 `reason` 无 `action_key_exclude` metadata（入键）——归词表域批量契约批；本批 `action_key` 机制零触及，OpenBox 侧 slot 入键/route_tag 排除均正确无失配。
4. **Pick* 族与其余注册表 op 清点状态**：动作 op 参数面迁移流水线八棒已迁（清单见行 1）——注册表内备战域动作全量完成参数面迁移；pick 族 12 行坐标源过渡态收敛（跨迭代挂账板 #8②）非本批；三刷新建议动作/开店编排/结算确认等注册表外执行体与本批零交集（OpenBox 在注册表内 :179），清点申报防漏。
5. **开件族 G2 收口**：G2（obs `find_armory_boxes`/`read_armory_boxes`/`find_tomes` 的 `slot_idx` 基 docstring 声明缺失）收口归本批实施批落——义务面 = 两函数 docstring 补基声明 + recognizer 表述勘误申报（§3.8）；OpenBox 迁移后 op 面零 obs `read_*`/`find_*` 消费，G2 残余辖域 = 观察分类域与 recognizer extras（新读取方防错拿依据）。 tome 侧 `find_tomes` 同款义务若 tome 批未落，随本批 G2 收口一并补齐（实施角色 grep `find_tomes` docstring 现值裁决）。
6. **action-op.md 转移终表 #5 next_screen 列过期**（本稿新发现，归收尾批四笔队列）：声明改底层屏（zero_writes.py:46-48）后 L90 列值未跟上——判读警示：收尾批落地前，按 L90 旧值核 open_box 声明会误判漂移；权威 = 代码现值 `_decl_bottom`。
7. **单击族无失焦守卫家族现状**（bookcard 稿 §9 行 6 同判延续）：开件三类/CollectOre/LevelUp/StartBattle 裸 controller 点击，无 `drag_char_guarded` 同构失焦守卫；若未来实证单击输入同病，守卫宿主化归单击族专项，本批零改动。
8. **`CwScreenArmoryBox` 与 `CwScreenBoxPick` 双画面族**（§3.7）：「武装箱弹窗」（获得说明弹窗）与「武装箱选择」（四选一选卡）两个画面 op 同族名异档——本批零改动；申报防后续读者按族名误判 OpenBox 分发关系。

## 10. 实施顺序建议（给实施角色）

1. `cw_vocab.py` param 必填化 + from_dict + docstring（§3.1）。
2. `cw_open_box_action.py` op 重写（§3.2/§4）。
3. `zero_writes.py` docstring 补申报（§3.3）→ `prep_actions.py` 四件退役 + 注释收口（§3.4）→ `cw_screen_prep.py:944` 注释收口（§3.7）。
4. obs G2 docstring 收口（§3.8）→ 测试（§5）→ 文档（§8；prep-contract 同批落）。
5. §5.1 自核清单逐条跑 → MCP server 重启 → `describe_operation_flow` 核对 op 节点图（恒 round_success 单节点形态）→ `list_operations`/`describe_operation` 核对反射参数面（slot required + env 缺省）→ 实机验收序列（§11）。

## 11. 实机验收序列（给实施角色）

1. **点击落点与零写核对（§7 条 5 义务）**：备战画面开一简易武装箱（决策自然触发或直调）——点击落点 = **武装箱开启位-N 开启按钮区**（非备战栏槽中心，与 bookcard/tome 验收核对位不同）；下一帧实读：武装箱选择四选一画面在场（外循环分发 `CwScreenBoxPick`）、bench 该槽箱消失（heavy 实读覆盖旁证）；选卡后回备战 heavy 观察装备快照含新件（获得链旁证）。
2. **直调单件会话**：run_operation 跑 `CwActionOpenBoxOp`（from_dict 通道，env=None）双口径各一例——`{"slot": N}` 按 extras `bench.slots` kind='supply_box' 下标+1 与按 extras `armory_boxes` 元素 slot 直传各一，核对 round detail/data 与落位；**废除形态一例**：缺 slot 键（构造面 TypeError）与 `{"slot": null}`（守卫 AssertionError）各一，核对报错文案指向参数契约。
3. **零写账核对**：round data 核对（`next_screen`=备战档、`trigger='open_box'`）+ 选卡回备战 heavy 前 gs bench 槽位表零变化（零写族旁证——悬空段零消费窗口期核对）；gs 缺席直构帧（如可安全构造）机械已发零上报零异常。
