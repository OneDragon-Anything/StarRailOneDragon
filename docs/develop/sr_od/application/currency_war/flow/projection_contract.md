# 备战逻辑态面交互契约（projection_contract）

> **定位**：备战阶段的「逻辑态面」= 策略侧维护的局面状态面板与决策视图字段（`cw_state.GameState` 面板 / 观察帧 / `TurnState` 视图）向执行臂暴露的读写面。本篇是该逻辑态面与执行侧（部署臂 / 换血臂 / 卖出臂 / 装备臂）之间的接口契约：消费方读什么字段、写入端承诺什么不变式、取值时序（生成期快照 vs 执行期现读）、坐标系声明，以及现状代码对照「索引/槽位字段必须带定义注释」条款（AGENTS.md 注释规范）的缺口登记。
> **判层**：归 `flow/`——本篇是决策↔执行的数据流与接口契约，属流程控制现行家 as-built 辖域（`README.md` §1 分层判据中「画面指挥/动作执行」两层的交界）；策略判据（卖谁/换谁的数学）不在本篇，见 `../strategy-docs/`。
> **读者**：无会话历史的工程师/智能体。代码锚 = `文件::符号名`（路径根 = `src/sr_od/application/currency_war/`）。术语首现给定义。

## 术语

- **逻辑态面**：把「画面实况 + bot 跟踪」整理成策略可消费的状态数据的各层数据结构的总称；其中动作执行后不经观察、按游戏规则推算并直写容器的预期状态即**逻辑态**（真值以下一帧观察为准(观察赢)）。不是游戏画面上的视觉投影（拖拽预览、浮窗等视觉现象归画面建档域，见 `od-dev-screen-onboarding`）。
- **族 A / 族 B（动作坐标系两族）**：同名动作类在两个模块里坐标系不同基——族 A = `kernel/cw_game_state.py` 的策略动作（状态坐标系，容器下标）；族 B = `kernel/cw_prep_actions.py` 的执行动作（画面坐标系，物理槽位）。权威对照表单一源 = `cw_state.py` Action 节约定块（§2 引用，不复制）。
- **生成期快照 / 执行期现读**：生成期 = 决策帧装配时点（入口 heavy 观察到动作发射之间）；执行期 = 执行器真正读屏/拖拽时点。「生成期=执行期」表示索引跨该间隙恒稳，两时点读同一槽得到同一格。
- **tracked 账**：执行侧随动跟踪账 `ExecState.tracked_bench_chars / tracked_deployed`（`kernel/cw_exec_state.py::ExecState`），由卖出/部署 handler 在动作落地时同步增删。
- **黑板**：`session.prep_obs_frame`（备战观察帧，写者白名单 = 入口观察段/循环逻辑态直写步；读者 = 决策入口），语义见 `../screens/prep.md` §2。

## 1. 逻辑态面的四层数据面

| 层 | 载体 | 角色 | 关键契约 |
|---|---|---|---|
| 状态面板 | `kernel/cw_game_state.py::GameState` | 决策域局面模型（OCR 填充 + bot 跟踪） | `bench` 定长 9 槽表、`deployed` 定长 10 槽表；卖出/下场置 None 不移位 |
| 观察帧 | `kernel/cw_prep_actions.py::PrepObservation` | 备战决策单一输入（黑板内容物） | heavy 字段（`state`/`bench_chars`/`deployed_chars`/`deploy_vacancy`）入口单次刷新，light 步沿用可能 stale；轻字段（球/箱/占用/开态）每步现读 |
| 快照视图 | `strategies/impl/mandate_v1/contracts.py::Snapshot` | frozen 观察视图（装配半部 `decision_assembly.snapshot_from_obs` 产出） | 容器下标 = 槽位语义（bench 下标 0-8、deployed 下标 0-3 前排/4-9 后排，声明在其类 docstring「空值表示总约定」）；deepcopy 隔离 |
| 决策视图 | `strategies/impl/mandate_v1/turn_state.py::TurnState` | 每备战节点入口幂等装配（`assembly.py::assemble` 单一写端） | DirectionView（方向）/BudgetView（预算）；派生值不落 session，唯一豁免 = 遥测披露面四字段+键戳 |

执行侧载体（消费方读写的落地对象）：

- `kernel/cw_exec_state.py::ExecState`：局容器级执行状态。`tracked_bench_chars`/`tracked_deployed` 双账（形状契约 =  槽位表、pad 后含 None；tracked_bench_chars 恒 pad 态由 reconcile 写回端经 `bench_from_compact` 重建保证，消费端下标即布局）、`deploy_fail_counts` 失败记忆、`expected_state` 期望态容器等。
- 期望态路径寻址：`kernel/cw_exec_state.py(原 cw_expected_state.py,已删)::ExpectedEntry.path`，身份寻址字符串（§2.4）。
- 帧级透传槽：`MandateState.cw4_m1p_arm_pending`（换血臂发射⇔执行归因透传，§4.3）。

## 2. 坐标系声明

### 2.1 两个容器（权威槽位 = 下标）

- **bench（备战栏）**：定长 `BENCH_CAPACITY=9` 槽表（`cw_state.py::BENCH_CAPACITY`）。列表下标 0-8 = 物理槽位 1-9 减一；`BenchChar.slot` 保留 1-based 屏幕槽号，**信息位**。卖出/上阵置 None 不移位 → 索引跨动作组恒稳。容量判据 = `kernel/cw_exec_state.py::bench_occupied`，**禁止 `len(bench)`**；迭代一律 `cw_state.py::iter_occupied`。
- **deployed（上阵）**：定长 `DEPLOYED_CAPACITY=10` 槽表。下标 0-3 = 前排槽 1-4、4-9 = 后排槽 1-6（后排实际格数随布局档 6/7/8 变，扩展格属画面布局域不进本表示，见 `cw_back_layout.py`）。容量判据 = `deployed_occupied`；迭代 = `iter_occupied_deployed`；下标→排内槽号换算 = `deployed_slot_no`。

`BenchChar.position_pref` / `BenchChar.slot` 在两容器中均为信息位，落槽写端（`bench_place` / `deployed_place`）负责归一信息位与下标一致；权威槽位恒为下标。

### 2.2 动作字段双族对照（单一源引用）

权威对照表与换算公式 = `cw_state.py` Action 节约定块「双族对照表」（代码注释，本篇不复制全文）。摘要：

| 同名类 | 族 A（`cw_state`，状态坐标系） | 族 B（`cw_prep_actions`，画面坐标系） |
|---|---|---|
| `SellBench` | `bench_idx` = 槽位表下标 0-8 | `slot` = 物理槽位 1-9 |
| `DeployMove` | `bench_idx` = 槽位表下标 0-8 | `from_slot`/`to_slot` = 物理槽位 |
| `SellDeployed` | `deployed_idx` = 槽位表下标 0-9 | `row`+`slot` = 物理排+槽位 |

换算：bench 域 族 A = 族 B − 1；deployed 域 族 A 下标 = front: slot−1 ∣ back: 4+slot−1。跨族阅读时以类头「≠ 另一族」标注为准。

### 2.3 画面点位（下标 → 像素）

- 点位单一源 = screen_info「货币战争-备战」的 `备战栏-N` / `前排-N` / `后排-N` area，经 `prep_actions.py::row_area_centers` 按 N 升序读出中心点。
- 执行器（`PrepActionExecutor.__init__`）构造时读一次三排点位表；族 B 物理槽号 → 点位 = `pts[slot - 1]`；0-based 助手（如 `prep_actions.py::drag_bench_to_sell` 的 `bench_idx`）= `pts[bench_idx]`。screen_info 是静态建档，点位表构造一次全程有效；槽位**内容**才是动态面。
- 后排点位按 cap 差公式选档（`cw_back_layout.py::select_back_layout` 单一入口），`row_area_centers` 读全部已建档区自动跟上。

### 2.4 期望态路径命名空间（`cw_expected_state.py`）

期望态条目按 `path` 字符串身份寻址，对账清账按同串匹配；tracked 族比对按**身份**（名字包含）豁免位移（`cw_expected_state.py::_values_match`）。现役 path 形态与基：

| path 形态 | 括号内语义 | 基 | 写点 |
|---|---|---|---|
| `tracked_bench_chars[N]` | 备战栏物理槽号 | **1-based** | `apply_op_effect` SellBench 分支 |
| `tracked_bench_chars[名@N星]` | 买入落点/合成链（名字键） | — | 精确建模区 dict 形态 |
| `tracked_deployed[N]` | deployed 槽位表下标 | **0-based** | `apply_op_effect` SellDeployed / `register_equip_worn` |
| `deployed.{row}.{slot}` | 排 + 排内槽号 | slot **1-based** | `apply_op_effect` DeployMove |
| `owned[名]` / `gold` / `xp_ledger` 等 | 字段族 | — | 各分支 |

⚠️ 同一命名空间内 `tracked_bench_chars[N]` 与 `tracked_deployed[N]` 基不同（1-based vs 0-based）——现状读写两侧同约定，零行为分叉；判读侧按 path 直读槽号时必须先分域（缺口登记 G3）。

## 3. 写入端不变式（逻辑态面对消费方的承诺）

1. **槽位表形状**：bench/deployed 为定长槽位表，元素 `BenchChar | None`；删除语义 = 置 None 不移位。由此「生成期索引 = 执行期索引」在单轮内成立，同轮多笔卖出/部署不可能引起索引漂移（的立法目的）。
2. **信息位归一**：任何把 `BenchChar` 放进槽位表的写端（`bench_place`/`deployed_place`/部署装配 `assemble_bench_list`）必须让 `slot`/`position_pref` 与落位下标一致；跨排移动经 `_apply_row_to_char` 归一。
3. **快照隔离**：TurnState 元素经 `cw_state.py::snapshot_copy` 浅拷贝 + equips 固化 tuple，与 `session.tracked_*` 断开对象别名——session 侧就地写端（shop 星级/装备拼接、deploy 装备覆盖）不穿透视图，反向亦然；Snapshot 为 frozen + deepcopy。快照不在帧间存活由拷贝机制保证，不靠消费纪律。
4. **tracked 账随动**：卖出 handler 销账（`prep_actions.py::_track_remove_bench` 按 `bc.slot` 过滤；`_track_remove_deployed` 按 换算置 None）；上阵落槽走 `deployed_place` 单一源（`_track_move_deployed`）；部署 op 收尾 SIFT 真值纠漂（`cw_screen_deploy.py::_reconcile_tracking`，观测回路）+ 装备快照回写（`_snapshot_equips_into_tracking` 写 `tracked_deployed[].equips`）。tracked 账与期望态逻辑态账的双账对拍 = 逻辑态建模错的在环检测器（`screen_op.md` §2.3(ii)）。
5. **幂等装配**：TurnState 同输入重入返回等值（`assembly.py::assemble`）；视图派生值不落 session；唯一豁免 = 遥测披露面（`v3_reserve_cap`/`v3_reserve_overflow`/`v3_release_budget`/`v3_release_spent` + `v3_disclosure_key` 键戳，禁决策消费，守卫锁 = test_cw_budget_disclosure）。
6. **期望态两执行面同源**：原子动作的期望态推进唯一入口 = `kernel/cw_exec_state.py::apply_op_effect`（`PrepActionExecutor.execute` 与 decision 面绑定回放共同底层，登记挂执行器入口一次覆盖）。
7. **装备 owned 搬运链**：装备 owned 名单写端 = `cw_op_equip_all.py::CwOpEquipAll`（`read_equips` 多列读 → `session.last_owned_equips`）；穿戴落地销账 = `cw_op_equip_all.py::register_equip_worn`（owned −1 件 + `tracked_deployed[idx]` equips +1，deployed 下标换算公式在其 docstring 声明）。

## 4. 时序：生成期快照 vs 执行期现读

### 4.1 备战线数据流时间线

```
备战节点入口 heavy 观察(obs.cw_observe_full::observe_full，唯一读屏点)
  → 写黑板 session.prep_obs_frame（写者白名单）
  → assemble（TurnState 幂等装配）
  → 决策（entry.emit 三遍编排；动作产出 = 恰一个动作（CwAction | None））
  → 帧稳定截断（entry.py::truncate_frame_stable；单动作循环逐帧恰取一个动作，None = 本帧无动作交回重观察）
  → 执行（PrepActionExecutor / 组合 op）
  → 期望态登记 + tracked 随动 → 逐动作逻辑态直写（纯计算零读屏）→ 下一动作或终结 op
```

### 4.2 动作参数的时序语义

- **族 A 动作**（sim/策略域）：`bench_idx`/`deployed_idx` 取值时机 = 生成期=执行期（槽位表恒稳）；提案代际校验字段 `expect`（期望名）由发射点写入，应用时名不符 → `stale_proposal` 拒绝。expect 写入端逐字段声明见各动作类 docstring（如 `cw_state.py::SellBench`）。
- **族 B 动作**（执行域）：`slot`/`from_slot`/`to_slot` 取值时机 = 生成期快照（决策帧观察），**无 expect 代际校验字段**。防线依赖两个前提：①单动作循环生成即执行，决策-执行间隙内画面由逐动作逻辑态直写推定（`../screens/prep.md` §2）；②执行拖拽**机械单发**（`DragCwChar.drag_char`，零判效零重试——拖后像素验已拆除），发出即记账，落地事实由下一入口观察对账暴露（失配留证）。若未来族 B 动作进入跨帧队列，该前提失效，需先补代际防线（缺口登记 G4）。
- **消费方不得把族 B 动作参数当执行期索引复用**：执行器把槽号转点位后即拖拽（机械发出）；换血臂（§4.3）的 victim 选择在执行面用 SIFT 现读重判，不信任发射帧的槽位内容。

### 4.3 发射⇔执行透传通道（换血臂）

- **归因透传**：`MandateState.cw4_m1p_arm_pending`——写端 = mandate 发射位（发射 `RunDeploy` 时置臂名）；消费点 = `cw_screen_deploy.py::CwScreenDeploy.deploy` 卖出臂**读后即清**（一次消费）；发射位每帧入口**无条件复位** None（防「本帧无 m1p、执行未及消费」的跨帧残留误归因）。该槽只承载归因分键（键族 `sell_offtarget_arm_*`），不承载行为参数。
- **臂态位**：`ExecState.cw4_swap_arm_on`——执行面换阵卖出义务臂开合状态（`CwScreenDeploy.deploy` 逐环重评写入），供判读开合抖动。
- **判定单一源 + 两域差**：换血计划装配单一源 = `kernel/cw_deploy_logic.py::assemble_swap_plan_inputs` + `select_swap_plan`（发射⇔执行同函数同参，禁第二份口径）。已知域差（by design，非分叉）：发射面喂入决策帧槽位表（`mandate.py` m1p 段，`frame.bench`/`frame.deployed`）；执行面喂入 `session.last_state` 滞后帧 + **SIFT 现读覆写** `evolution_swap_armed`（`cw_screen_deploy.py` deploy-swap 段，域 = 本帧 SIFT 读）。发射⇔执行间隙内 bench 变化由执行面现读吸收；逐件可卖判定单一源 = `swap_sell_exclusion_reason`。
- **装备穿戴的执行期时序**（L0/L1 实证批素材）：穿戴落点判定 = avatar 下方 mini icon 区 CV-diff（`_below_icon_diff`，阈值常量在 `cw_op_equip_all.py`），drag 前稳帧确认 + 落空补救链坐标现读重定位；owned 授予快照每次穿戴 op 执行只记一遍（`_snap_logged`，循环重读不重复记）；跨轮 owned 演化靠穿戴销账与复读覆盖——消费 `session.last_owned_equips` 的一方不得假设其逐帧重读。

### 4.4 观察分层的时序边界

`PrepObservation` heavy 字段在 light 步沿用上次值（stale 窗口 = 无动作步，单线程内安全）；`state.gold` 仅商店开态可信（F2 门）；`boxes`/`spheres`/`front_occupied` 等轻字段每步现读。执行侧对同一画面的**再读**与决策帧之间无一致性承诺——需要强一致的判定（如 deploy 的占用检测）一律执行期现读（CV `slot_occupied`），不从决策帧取。

## 5. 消费方读什么（逐臂）

| 臂 | 载体 | 读的逻辑态面字段 | 读法 |
|---|---|---|---|
| 部署臂 | `operations/cw_screen/cw_screen_deploy.py::CwScreenDeploy` | bench/前/后排占用（CV `slot_occupied` 现读）、身份（SIFT `read_bench_chars`/`read_deployed_chars`）、`deploy_cap`（防抖真读）、board（`session.last_state.board`） | 全执行期现读；计划判定单一源 = kernel `select_deployments_reasoned`；`assemble_bench_list` 构造 BenchChar（`slot=_bi+1`，占槽物品显式 `is_item_slot=True`） |
| 换血臂（M1″/m1p） | 发射面 `mandate.py` m1p 段 + 执行面 `CwScreenDeploy.deploy` deploy-swap 卖出臂 | 发射面 = 决策帧槽位表（Snapshot/GameState 域）；执行面 = last_state 滞后帧 + SIFT 现读；逐件拒因 = `swap_sell_exclusion_reason` 现读域喂入 | §4.3；1:1 替换上限 = `bench_target_count`；卖出后残余补部署走 `residual_fill_plan`（点位下标域） |
| 卖出臂（prep 域） | `prep_actions.py::_sell_bench` | 族 B `SellBench.slot`（物理槽号） | `drag_bench_to_sell(op, ctx, slot−1)`（基转换在调用点）；成功后 `_track_remove_bench` 销 tracked 账 + `apply_op_effect` 登记期望态 |
| 卖出臂（shop 域） | `operations/cw_op/cw_sell_bench_action.py::SellBenchOp` | 族 A `SellBench.bench_idx`（槽位表下标）+ `expect` 期望名 | `drag_bench_to_sell` 直收 0-based，机械单发发出即记账（tracked 双账无条件推进：置 None 不紧缩）+ `register_round_sold`；expect 代际校验归转移函数（`apply_shop_action_logic` 对非空 expect 做 `stale_proposal` 拒，applied=False 零容器写）；零判效，落地事实归下一入口观察对账 |
| 装备臂 | `operations/cw_op/cw_op_equip_all.py::CwOpEquipAll` | owned 多列网格（`read_equips`）、`session.last_owned_equips`、`read_row_equipped` 已穿表（slot 1-based）、avatar CV-diff | §3.7 搬运链；穿戴候选过滤工具类；P0-2 只往空槽 drag（`_empty_slots`，防覆盖已穿） |

## 6. 现状边界与缺口登记（对照注释规范逐文件点名）

> 判据 = AGENTS.md 注释规范「索引/槽位字段必须带定义注释」：凡带索引/槽位/序号语义的整型字段，注释须声明**坐标系**（哪个容器的下标/画面物理槽位及基）与**取值时机**（生成期快照/执行期现读/恒稳）；期望校验类防线字段另须注明**写入端**。以下为**现状缺口登记（只登记，不改代码）**——它们是本契约的现行边界，消费方与后续修复批以本节为准。

| # | 文件::符号 | 缺口 | 影响 |
|---|---|---|---|
| G1 | `kernel/cw_game_state.py::BenchChar.slot` | 逻辑态面最核心槽位字段**自身零定义注释**：坐标系/取值时机/双容器语义（bench 域 = 1-based 物理槽号权威输入；deployed 域 = 排内槽号信息位、派生自下标）只散在 GameState 容器注释与 Action 对照表；`_card_to_bench`(现役 kernel/cw_vocab.py 与 cw_merge_simulate.py)构造的 `slot=0`「未落槽」哨兵值也无处声明 | 跨模块读者只能靠猜；slot=0 哨兵与 1-based 值域混存于同一字段无声明 |
| G3 | `kernel/cw_exec_state.py(原 cw_expected_state.py,已删)::apply_op_effect`（path 构造）与 `ExpectedEntry` docstring | 期望态路径命名空间同一括号形态两种基：`tracked_bench_chars[N]` = 1-based 物理槽号、`tracked_deployed[N]` = 0-based 槽位表下标、`deployed.{row}.{slot}` = 1-based；`ExpectedEntry` docstring 只写「槽位路径」未分基 | 现状零行为分叉（清账同串匹配 + 身份匹配豁免位移）；判读/离线工具按 path 直读槽号会错位 |
| G4 | `kernel/cw_prep_actions.py::SellBench.slot` / `SellDeployed.row+slot` / `DeployMove.from_slot/to_slot`（族 B 全部槽位字段） | 坐标系有声明（模块头+类 docstring：物理槽位），**取值时机零声明**；「族 B 无 expect 代际校验、依赖单动作循环生成即执行短间隙」的结构边界未写在动作定义处（只散在 prep_visit/action_exec 的循环语义） | 族 B 动作一旦进入跨帧队列即无代际防线；登记为契约边界，接线跨帧队列前必须先补 expect 类防线或取值时机声明 |
| G5 | `obs/cw_identity_obs.py::find_supply_boxes` / `find_tomes` / `read_supply_boxes` / `read_tomes` | 返回值 `slot_idx` 的基（1-based，来自 `_ctx_slots` 的 `range(1, count+1)`）只在实现里，函数级 docstring 未声明；对照同文件 `bench_item_slots` 的「注释规范硬门」写法属漏网 | 消费方 `OpenBox.slot`/`OpenTome.slot` 的 validate（1-9）与匹配（`b[0]==action.slot`）全依赖此基；声明缺失=新读取方易按 0-based 惯例错拿 |
| G6 | `operations/cw_screen/cw_screen_deploy.py::residual_fill_plan` | 返回三元组声明了 `slot_idx` 基（排行点位表 0-based 下标），但 `bench_idx` 的基与入参 `bench_pos`/`bench_cid` 的键域（bench 槽位表下标 0-8）只在调用方局部变量注释里有，函数自身 docstring 未声明 | 该函数标注「可离线直测」，离线构造入参时键域无函数级依据 |
| G7 | `strategies/impl/mandate_v1/turn_state.py` + `assembly.py`（现状事实，非注释缺口） | `DirectionView.bench_view`/`deployed_view`（R2 读口）与 `hoard`/`hoard_readable` 现状**零生产消费点**：每装配帧照常写入（snapshot_copy 成本照付），src 全仓读点仅测试（`hoard_consumer_domain` 仅测试消费）；`entry.emit` 的 `turn` 形参同样声明未消费，决策输入实际走 `obs` + `state_of(session)` 直读。字段 docstring 对此是诚实的（「决策板面输入仍走 snap 新鲜读」），但「决策判据一律消费 TurnState 幂等装配」的纪律表述与现状通路不一致，易被误读为决策已走 TurnState | 下游按 docstring 推断数据流会得出错误依赖图；读口接线或退役归后续批裁决，本契约只申报现状 |
| G8 | `strategies/impl/mandate_v1/contracts.py`（权威指针存续风险） | Snapshot 逐字段权威表指向 w583_stage2_contracts/SCHEMA_DRAFT.md——gitignored 工作副本，**该原始件已灭失（2026-09-12 清理），存续风险已应验**；同型先例 = 已灭失重锚的 `CONTRACT_SERIES_DECISION.md`（处置 = `action_exec.md` §1 权威链重锚申报） | 权威表已灭失；建议后续批把权威表迁入 docs 或 contracts.py docstring（迁移挂账仍开放） |

已核对合规（抽样，供后续审计对照，不再逐一列出）：族 A 全部 `[索引定义]` 字段（`SellBench.bench_idx`/`DeployMove.bench_idx`/`SellDeployed.deployed_idx`/`SwapDeploy.deployed_idx+bench_idx`/`FillSpec.idx`/`PickEvent.option_idx+refresh_slots`）、`GameState.bench/deployed` 容器注释、`BenchChar.is_item_slot`、`ShopCard.merge_preview`、`cw_identity_obs.py::bench_item_slots`、`prep_actions.py::drag_bench_to_sell`、`cw_op_equip_all.py::register_equip_worn`、`cw_exec_state.py::_invest_refresh_used_slots`、`cw_state.py::xp_apply_clicks`。

## 7. 接口注（被挡下游的消费面依据）

- **装备穿着主病灶策略语义再评估（opening 窗口与非 key_equips 释放条件）与装备释放条件批的策略语义评估**，其执行侧事实依据 = 本契约 §3.7（装备 owned 搬运链与穿戴销账）+ §4.3 末段（穿戴的执行期时序：稳帧/CV-diff 验穿/补救链/owned 授予快照每次执行只记一遍）+ §5 装备臂行。两任务判读执行侧「穿上/没穿上」证据时，以 `register_equip_worn` 销账链与 `equip_zero_wear` 哨兵的契约语义为准，不以画面单帧直觉为准。
- 两任务涉及卖出/释放条件评估时，其动作面坐标系 = §2.2 双族对照（族 A `bench_idx`/`deployed_idx` + expect 代际校验；族 B 物理槽位无 expect）；评估「卖没卖对人」必须先分族再读数。
- 本契约的验证阶梯状态：L0（读面基线）/L1（单件验穿）已过（报告 = `.debug/temp/currency_war/_archive_20260908/projection_ladder/阶梯执行报告_L0_L1.md`）；L2（已穿非空样本）/L3（落空补救链量化）需实机窗采样，**不在本批**，其结论落地前，涉及「批量穿戴不覆盖已穿」「落空率数字」的策略假设按未证对待（口径）。
