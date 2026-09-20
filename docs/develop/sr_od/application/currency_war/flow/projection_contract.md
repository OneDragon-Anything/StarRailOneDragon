# 备战逻辑态面交互契约（projection_contract）

> **定位**：备战阶段的「逻辑态面」= 策略侧维护的局面状态面板与观察帧字段（`cw_state.GameState` 面板 / 观察帧）向执行臂暴露的读写面。本篇是该逻辑态面与执行侧（部署臂 / 换血臂 / 卖出臂 / 装备臂）之间的接口契约：消费方读什么字段、写入端承诺什么不变式、取值时序（生成期快照 vs 执行期现读）、坐标系声明，以及现状代码对照「索引/槽位字段必须带定义注释」条款（AGENTS.md 注释规范）的缺口登记。
> **判层**：归 `flow/`——本篇是决策↔执行的数据流与接口契约，属流程控制现行家 as-built 辖域（`README.md` §1 分层判据中「画面指挥/动作执行」两层的交界）；策略判据（卖谁/换谁的数学）不在本篇，见 `../strategy-docs/`。
> **读者**：无会话历史的工程师/智能体。代码锚 = `文件::符号名`（路径根 = `src/sr_od/application/currency_war/`）。术语首现给定义。

## 术语

- **逻辑态面**：把「画面实况 + bot 跟踪」整理成策略可消费的状态数据的各层数据结构的总称；其中动作执行后不经观察、按游戏规则推算并直写容器的预期状态即**逻辑态**（真值以下一帧观察为准(观察赢)）。不是游戏画面上的视觉投影（拖拽预览、浮窗等视觉现象归画面建档域，见 `od-dev-screen-onboarding`）。
- **动作坐标系(统一词表)**：席位域动作(`CwActionSellBenchParam.bench_idx`/`CwActionSellDeployedParam.deployed_idx`/`CwActionDeployMoveParam.bench_idx`)携**容器槽位表下标**(0 基;词表单一源 = `kernel/cw_vocab.py`,坐标系裁定见各类 docstring)——原「策略/执行同名双模块双坐标系(族 A/族 B)」随词表摊平退役,同类不再双模块同名。DeployMove 的落位 = `(to_row, to_slot)` 载荷直指(`to_slot` = 排内 1 基画面槽号,表下标 = `deployed_idx_of(to_row, to_slot)`;落位决策权归策略层,执行边零现读)。坐标参数化机械动作(`CwActionWearEquipParam`/工具原子/`CwActionOpenBoxParam`/`CwActionOpenTomeParam`/`CwActionOpenBookcardParam`)的 `row`/`slot` = 画面物理排槽位 1 基(拖点直取 area,不经换算)。
- **生成期快照 / 执行期现读**：生成期 = 决策帧装配时点（入口 heavy 观察到动作发射之间）；执行期 = 执行器真正读屏/拖拽时点。「生成期=执行期」表示索引跨该间隙恒稳，两时点读同一槽得到同一格。
- **tracked 账**：tracked 主账槽位簿记 `GameState.tracked_books`（`kernel/cw_game_state.py::TrackedBooks`，bench/deployed 两面非 Field 簿记组），由卖出/部署 handler 在动作落地时同步增删。
- ~~**黑板**：`session.prep_obs_frame`~~（**已退役**，迭代 2026-09-18-prep-obs-retirement 阶段 3.5）：备战观察帧宿主与 `gs.prep_obs` 槽已删,策略器唯读容器契约归位;`PrepObservation` 瘦身为备战环 op 局部控制信号载体(shop_open/substate/event_overlay,不进 gs、不进 session、不再是策略器输入),语义见 `../screens/prep.md` §2。

## 1. 逻辑态面的数据面分层

| 层 | 载体 | 角色 | 关键契约 |
|---|---|---|---|
| 状态面板 | `kernel/cw_game_state.py::GameState` | 决策域局面模型（OCR 填充 + bot 跟踪）= **策略器唯一输入** | `bench` = `BenchView`（slots+capacity,元素 `BenchSlot` 五分类 kind ∈ unit/supply_box/tome/bookcard/empty）、`front_row`/`back_row` = Unit 行（= 上阵面,排内 1 基 `slot` 信息位;阵营不入 Unit,注册表派生）；tracked 主账 = `tracked_books`（bench 定长 9 保洞 / deployed 定长 10 下标恒稳）；晶矿域 OreSight.points 载点击坐标 |
| 观察载体 | `kernel/cw_prep_actions.py::PrepObservation` | 备战环 **op 局部控制信号**(shop_open/substate/event_overlay),不进策略器 | 宿主 = 备战环 op 局部对象;不再承载名单/装备/占用/晶矿(全容器域) |

执行侧载体（消费方读写的落地对象）：

- `kernel/cw_game_state.py::GameState` 容器簿记：tracked 主账 = `tracked_books`
  （`TrackedBooks`，bench/deployed 两面槽位簿记；形状契约 = `bench` =
  `list[BenchSlot | None]` 定长 9（元素 = 容器同款 BenchSlot 五分类,kind 随形
  保留;None = 洞,卖出/上阵/合成消耗置 None 不移位,ADR-0316 保洞）、
  `deployed` = `list[Unit | None]` 定长 10（表下标 = deployed_idx 恒稳,排归属
  由下标派生 0-3 前/4-9 后,换算单一源 = `cw_exec_state.deployed_row_slot`/
  `deployed_idx_of`,ADR-0392）。执行层不再设
  独立状态载体（执行层状态类目已退役，git 历史可溯）；失败记忆/期望态容器随类目
  退役删除。
- 期望态路径寻址：期望态条目表已随期望账机制退役（`ExpectedEntry` 不存在），
  身份寻址对账消亡；字段路径字符串现仅作上报函数族（`kernel/cw_action_report/`）与
  `kernel/cw_exec_state.py::apply_confirm_effect` 推进清单及遥测面载体
  （§2.4）。
- 帧级透传槽：`StrategyState.cw4_m1p_arm_pending`（换血臂发射⇔执行归因透传，§4.3）。

## 2. 坐标系声明

### 2.1 两个容器（权威槽位 = 下标）

- **bench（备战栏）**：观察面 = `gs.bench`（`BenchView`,slots 定长 = capacity,列表下标 0-8 = 物理槽位 1-9 减一;空槽 = `kind='empty'`,非 None 洞）；tracked 面 = `tracked_books.bench`（定长 9 保洞,卖出/上阵置 None 不移位 → 下标跨动作组恒稳）。容量判据 = 派生单一源 `kernel/cw_game_state.py::bench_free_slots`/`bench_is_full`，**禁止 `len(slots)` 数占用**。
- **deployed（上阵）**：观察面 = `gs.front_row`/`gs.back_row`（Unit 行,元素 `Unit.slot` = 排内 1 基物理槽号）；tracked 面 = `tracked_books.deployed`（定长 10 下标表,下标 0-3 = 前排槽 1-4、4-9 = 后排槽 1-6；后排实际格数随布局档 6/7/8 变，扩展格属画面布局域不进本表示，见 `cw_back_layout.py`）。下标→排内槽号换算 = `deployed_slot_no`，反向 = `deployed_idx_of`。

`Unit.slot` 为排内 1 基信息位（观察期快照），落槽写端（`bench_place`/上报函数落位腿）负责让信息位与落位下标一致；权威槽位恒为下标。阵营不入 Unit——由 char_id 查角色注册表派生。

### 2.2 动作字段坐标系(统一词表,零换算)

词表摊平后单一坐标系(原双族对照表随双模块词表退役,考古走 git):席位域动作直携容器槽位表下标(0 基,§2.1 权威),执行坐标边(容器下标 → screen_info 槽位中心)换算单点 = `PrepActionExecutor`(bench 侧备战栏-N area 序直取;deployed 侧 `kernel/cw_exec_state.py::deployed_row_slot`);坐标参数化机械动作的物理排槽位 1 基字段拖点直取(§术语)。跨域阅读锚 = 各动作类 docstring(`kernel/cw_vocab.py`)。

### 2.3 画面点位（下标 → 像素）

- 点位单一源 = screen_info「货币战争-备战」的 `备战栏-N` / `前排-N` / `后排-N` area，经 `prep_actions.py::row_area_centers` 按 N 升序读出中心点。
- 执行器（`PrepActionExecutor.__init__`）构造时读一次三排点位表；物理槽号 → 点位 = `pts[slot - 1]`；容器下标直取（如 `prep_actions.py::drag_bench_to_sell` 的 `bench_idx`）= `pts[bench_idx]`。screen_info 是静态建档，点位表构造一次全程有效；槽位**内容**才是动态面。
- 后排点位按 cap 差公式选档（`cw_back_layout.py::select_back_layout` 单一入口），`row_area_centers` 读全部已建档区自动跟上。

### 2.4 期望态路径命名空间（已退役）

期望态条目表与身份寻址对账已随期望账机制退役（对账唯一发生点 = 观察边界）。
历史 path 形态与基的判读知识保留如下——字段路径字符串现仍作上报函数族/
`apply_confirm_effect` 推进清单与遥测面载体，判读者按 path 直读槽号时仍须分域：

| path 形态 | 括号内语义 | 基 |
|---|---|---|
| `tracked_bench_chars[N]` | 备战栏物理槽号 | **1-based** |
| `tracked_deployed[N]` | deployed 槽位表下标 | **0-based** |
| `deployed.{row}.{slot}` | 排 + 排内槽号 | slot **1-based** |

⚠️ 同一命名空间内 `tracked_bench_chars[N]` 与 `tracked_deployed[N]` 基不同（1-based vs 0-based）——读写两侧同约定，零行为分叉；判读侧按 path 直读槽号时必须先分域（缺口登记 G3，已消解——身份寻址对账随条目表退役）。

## 3. 写入端不变式（逻辑态面对消费方的承诺）

1. **槽位表形状**：tracked 主账 bench/deployed 为定长槽位表（元素 `BenchSlot | None` / `Unit | None`）；删除语义 = 置 None 不移位（保洞）。由此「生成期索引 = 执行期索引」在单轮内成立，同轮多笔卖出/部署不可能引起索引漂移（的立法目的）。观察面 `gs.bench`/`front_row`/`back_row` 无洞语义——空槽 = `kind='empty'`、行 = Unit 列表。
2. **信息位归一**：bench 落槽写端（`kernel/cw_exec_state.py::bench_place`）与上报函数落位腿让 `Unit.slot` 与落位下标一致；跨排移动的开拓者形态归一（char_id 随排切换）核 = `cw_exec_state.trailblazer_row_identity`（deploy_move/swap 两上报函数同源调用）。排路由不在写端——发射期由策略层 `deploy_row_pref`（comp 站位覆盖 > 注册表 position_pref 派生 > back 兜底）定。
3. **快照隔离**：`kernel/cw_exec_state.py::snapshot_copy` 浅拷贝 + equips 固化 tuple 使拷贝与 `session.tracked_*` 断开对象别名——session 侧就地写端（shop 星级/装备拼接、deploy 装备覆盖）不穿透拷贝，反向亦然。`snapshot_copy` 现役消费方 = `kernel/cw_action_report/buy_card.py::report_action_buy_card_param`（买牌买前快照 scratch 拷贝链——快照与升星腿内聚单点），拷贝隔离由机制保证、不靠消费纪律，不随已退役的视图层消失。
4. **tracked 账随动**：卖出 handler 销账（`prep_actions.py::_track_remove_bench` 按下标置 None；`_track_remove_deployed` 经 `deployed_idx_of` 换算置 None）；上阵落槽 = `_track_move_deployed` 载荷 `(to_row, to_slot)` 直写下标（与执行拖点/容器写侧同源,交换语义镜像——被占位单位回源槽）。落地事实的权威判定 = 观察边界对账（观察赢），tracked 账为其输入/输出簿记(原部署 op 收尾 SIFT 纠漂/装备快照回路随部署机画面 op 退役删除;对账权威 = 备战入口 heavy 观察,星级抖动门驻 `kernel/cw_reconcile.py`)。
5. **披露面承诺**：预算遥测披露面 = `v3_reserve_cap`/`v3_reserve_overflow`/`v3_release_budget`/`v3_release_spent` 四字段 + `v3_disclosure_key` 键戳，唯一写点 = `economy_cycle.disclose_budget`，两调用点 = 备战决策入口（`bridge.py::decide_prep_screen`，前置发射位判定之后的原装配缝位，非 armed 短路帧才到达）与店开帧覆写（`economy_cycle.py::disclose_budget_at_shop_frame`）；披露面是遥测列非决策输入，禁决策消费，守卫锁 = test_cw_budget_disclosure（armed 短路帧不披露单帧锁 = test_armed_shortcircuit_frame_writes_no_disclosure）。
6. **期望态两执行面同源**：原子动作的期望态推进唯一入口 = 上报函数族 `kernel/cw_action_report/report_action_<snake>_param`（动作 op 组装后直调自己的上报函数 = 实机 op 自上报；sim/回放引擎入口 = 一行委托分支串，`cw_sim_actions.apply_player_action`；驱动器 `decide_shop_screen` 两覆写逐动作直调）——两执行面同走同一函数族,单点即同源（动作 op 重组批④,design.md §2）。
7. **装备 owned 搬运链**：装备 owned 名单写端 = `cw_op_equip_all.py::CwOpEquipAll`（`read_equips` 多列读 → `session.last_owned_equips`）；穿戴落地销账 = `cw_op_equip_all.py::register_equip_worn`（owned −1 件 + `tracked_deployed[idx]` equips +1，deployed 下标换算公式在其 docstring 声明）。

## 4. 时序：生成期快照 vs 执行期现读

### 4.1 备战线数据流时间线

```
备战节点入口 heavy 观察(obs.cw_observe_full::observe_full，唯一读屏点)
  → 容器 game state 直写(CwScreenPrep 观察装配点:bench/deployed/equips/
     occupied_equips/spheres/node_chain/...渠道①;PrepObservation 局部
     载控制信号)
  → bridge.decide_prep_screen：方向代次消费（帧代次标注读后即清）
  → 前置发射位 _launch_front_check（armed 帧短路 return；短路帧不披露）
  → 预算遥测披露 economy_cycle.disclose_budget（落点 = 前置发射位判定之后，非 armed 帧才到达）
  → 决策（decide_prep_frame → entry.emit 三遍编排；决策输入 = 容器 game state 直读，零黑板；动作产出 = 恰一个动作（CwAction））
  → 帧稳定截断（entry.py::truncate_frame_stable；单动作循环逐帧恰取一个动作，空发射 = CwActionObsParam scope='outer_loop' 交回外循环重观察——原 HoldFrame 收编，用户裁定 2026-09-20）
  → 执行（PrepActionExecutor 分派 → CwActionXxxOp(SrOperation) 节点直调）
  → op 自上报（report_action_<snake>_param）+ tracked 随动（执行器 _track_*）
    （动作后逻辑态唯一更新点 = 上报函数族单点）
    → 下一动作或终结 op
```

### 4.2 动作参数的时序语义

- **携 `expect` 代际校验的动作**（卖出/换位类;原「族 A」语义）：`bench_idx`/`deployed_idx` 取值时机 = 生成期=执行期（槽位表恒稳）；提案代际校验字段 `expect`（期望名）由发射点写入，应用时名不符 → `stale_proposal` 拒绝。expect 写入端逐字段声明见各动作类 docstring（`kernel/cw_vocab.py`）。
- **坐标参数化机械动作**（穿戴/工具/开件类;原「族 B」语义）：`slot`/`row` 取值时机 = 生成期快照（决策帧观察），**无 expect 代际校验字段**。防线依赖两个前提：①单动作循环生成即执行，决策-执行间隙内画面由逐动作逻辑态直写推定（`../screens/prep.md` §2）；②执行拖拽**机械单发**（`DragCwChar.drag_char`，零判效零重试——拖后像素验已拆除），发出即记账，落地事实由下一入口观察对账暴露（失配留证）。若未来此类动作进入跨帧队列，该前提失效，需先补代际防线（缺口登记 G4）。
- **消费方不得把坐标参数化动作的字段当执行期索引复用**：执行器把槽号转点位后即拖拽（机械发出）；换血臂（§4.3）的 victim 选择在执行面用 SIFT 现读重判，不信任发射帧的槽位内容。

### 4.3 发射⇔执行透传通道（换血臂）

- **归因透传**：`StrategyState.cw4_m1p_arm_pending`——写端 = mandate 发射位（帧级无条件复位 None,m1p 臂武装时置臂名）；原消费点 = 部署机卖出臂(读后即清),**已随部署机画面 op 退役删除——现役零读端,归因分键悬空**,接线归 SellDeployed 动作路径侧重组批。该槽只承载归因分键（键族 `sell_offtarget_arm_*`），不承载行为参数。
- **判定单一源**：换血计划装配单一源 = `kernel/cw_deploy_logic.py::assemble_swap_plan_inputs` + `select_swap_plan`（发射侧同函数同参,禁第二份口径）。执行面现读(SIFT 覆写)随部署机退役;逐件可卖判定单一源 = `swap_sell_exclusion_reason`(现役消费面 = mandate 发射侧)。
- **装备穿戴的执行期时序**（L0/L1 实证批素材）：穿戴落点判定 = avatar 下方 mini icon 区 CV-diff（`_below_icon_diff`，阈值常量在 `cw_op_equip_all.py`），drag 前稳帧确认 + 落空补救链坐标现读重定位；owned 授予快照每次穿戴 op 执行只记一遍（`_snap_logged`，循环重读不重复记）；跨轮 owned 演化靠穿戴销账与复读覆盖——消费 `session.last_owned_equips` 的一方不得假设其逐帧重读。

### 4.4 观察时序边界

备战观察 = 入口 heavy 单次读屏直写容器;`PrepObservation` 局部载体只载控制信号(shop_open/substate/event_overlay),不承载状态面(名单/装备/占用/晶矿全容器域,阶段 3.5 起黑板退役)。执行侧对同一画面的**再读**与决策帧之间无一致性承诺——需要强一致的判定（如 deploy 的占用检测）一律执行期现读（CV `slot_occupied`），不从观察载体取。动作-观察间隙内的局面推进 = op 自上报函数（`report_action_<snake>_param`）逻辑态直写(「在观察态到来之前供决策使用」是逻辑态的全部职能),真值以下一帧观察为准。

## 5. 消费方读什么（逐臂）

| 臂 | 载体 | 读的逻辑态面字段 | 读法 |
|---|---|---|---|
| 部署臂 | 备战环动作路径:mandate 发射位 → `CwActionDeployMoveOp`(`cw_deploy_move_action.py`) | 逻辑态面(容器):bench 槽位表/期望态;物理真值 = 下一帧备战入口 heavy 观察(占用 CV/身份 SIFT/`deploy_cap` 防抖,由漏斗写端承接) | 逐动作机械拖拽 + 自上报 `report_action_deploy_move_param`(零像素判效);计划单一源 = 策略层 `mandate_v1/deploy_plan.py::deploy_plan_moves`(选人 `select_deployments_reasoned` + 排路由 `deploy_row_pref` + 槽位 `deploy_slot_plans`);kernel `cw_deploy_logic.py::residual_fill_plan` = 残余补位 |
| 换血臂（M1″/m1p） | 发射面 `mandate.py` m1p 段;执行面 = `CwActionSellDeployedOp`(`cw_sell_deployed_action.py`)+ 后续 DeployMove 补部署(原部署机卖出臂执行面已随其退役) | 发射面 = 决策帧槽位表(MandateFrame/GameState 域);逐件拒因 = `swap_sell_exclusion_reason`(现役消费面 = 发射侧) | §4.3;1:1 替换上限 = `bench_target_count`;卖出后残余补部署走 `residual_fill_plan` |
| 卖出臂（SellBench，双域统一） | `operations/cw_op/cw_prep_sell_bench_action.py::CwActionSellBenchOp`（词表摊平后商店/备战共用单一注册行；原商店域文件 `cw_sell_bench_action.py` 已退役删除） | `CwActionSellBenchParam.bench_idx`（槽位表下标 0-8）+ `expect` 期望名 | `drag_bench_to_sell` 直收 0-based，机械单发发出即记账；op 自上报 `report_action_sell_bench_param`（容器逻辑态单点：expect 非空失配 = `stale_proposal` 拒零写 + 置 empty + 回金 + 装备回收）+ 执行器 `_track_remove_bench` 销 tracked 账；零判效，落地事实归下一入口观察对账 |
| 装备臂 | `operations/cw_op/cw_op_equip_all.py::CwOpEquipAll` | owned 多列网格（`read_equips`）、`session.last_owned_equips`、`read_row_equipped` 已穿表（slot 1-based）、avatar CV-diff | §3.7 搬运链；穿戴候选过滤工具类；P0-2 只往空槽 drag（`_empty_slots`，防覆盖已穿） |

## 6. 现状边界与缺口登记（对照注释规范逐文件点名）

> 判据 = AGENTS.md 注释规范「索引/槽位字段必须带定义注释」：凡带索引/槽位/序号语义的整型字段，注释须声明**坐标系**（哪个容器的下标/画面物理槽位及基）与**取值时机**（生成期快照/执行期现读/恒稳）；期望校验类防线字段另须注明**写入端**。以下为**现状缺口登记（只登记，不改代码）**——它们是本契约的现行边界，消费方与后续修复批以本节为准。

| # | 文件::符号 | 缺口 | 影响 |
|---|---|---|---|
| G1 | ~~`kernel/cw_game_state.py::BenchChar.slot`~~（**已消解**） | 缺口宿主 `BenchChar` 已随容器化退役：`Unit.slot` 现役带 `[索引定义]` 注释（行内 1 基画面槽号 + 观察期快照时机），tracked 形状与下标坐标系声明住 `TrackedBooks` docstring 与动作类 docstring；旧 `slot=0`「未落槽」哨兵随 `_card_to_bench` 换形口删除 | 跨模块读者依据 = 代码注释与本文 §2.1 |
| G3 | ~~`kernel/cw_exec_state.py::apply_op_effect`（path 构造；动作 op 重组批④后本口瘦身改名 `apply_confirm_effect`）与 `ExpectedEntry` docstring~~（**已消解**） | 期望态路径命名空间同一括号形态两种基（`tracked_bench_chars[N]` = 1-based、`tracked_deployed[N]` = 0-based、`deployed.{row}.{slot}` = 1-based）；缺口对象 `ExpectedEntry` 已随期望态条目表退役,身份寻址对账消亡 | path 字符串仍作上报函数族/`apply_confirm_effect` 推进清单/遥测面载体,判读者按 path 直读槽号须分域的提醒保留于 §2.4 |
| G4 | `kernel/cw_prep_actions.py::SellBench.slot` / `SellDeployed.row+slot` / `DeployMove.bench_idx+to_row+to_slot`（坐标参数化族全部槽位字段） | 坐标系有声明（模块头+类 docstring：物理槽位/载荷直指），**取值时机零声明**；「无 expect 代际校验、依赖单动作循环生成即执行短间隙」的结构边界未写在动作定义处（只散在 prep_visit/action_exec 的循环语义） | 坐标参数化动作一旦进入跨帧队列即无代际防线；登记为契约边界，接线跨帧队列前必须先补 expect 类防线或取值时机声明 |
| G5 | `obs/cw_identity_obs.py::find_supply_boxes` / `find_tomes` / `read_supply_boxes` / `read_tomes` | 返回值 `slot_idx` 的基（1-based，来自 `_ctx_slots` 的 `range(1, count+1)`）只在实现里，函数级 docstring 未声明；对照同文件 `bench_item_slots` 的「注释规范硬门」写法属漏网 | 消费方 `OpenBox.slot`/`OpenTome.slot` 的 validate（1-9）与匹配（`b[0]==action.slot`）全依赖此基；声明缺失=新读取方易按 0-based 惯例错拿 |
| G6 | `kernel/cw_deploy_logic.py::residual_fill_plan`(部署机锚已随其退役收敛 kernel 单一源) | 返回三元组声明了 `slot_idx` 基（排行点位表 0-based 下标），但 `bench_idx` 的基与入参 `bench_pos`/`bench_cid` 的键域（bench 槽位表下标 0-8）只在调用方局部变量注释里有，函数自身 docstring 未声明 | 该函数标注「可离线直测」，离线构造入参时键域无函数级依据 |
| G7 | ~~`strategies/impl/mandate_v1/turn_state.py` + `assembly.py`~~（**已结案**） | TurnState 层已随 turnstate-retirement 物理删除；hoard/hoard_readable 随 DirectionView 消亡 | 现行决策通路 = §4.1 时间线 |
| G8 | ~~`strategies/impl/mandate_v1/contracts.py`~~（**已结案**：Snapshot 契约族经用户裁定随 turnstate-retirement T-6 退役整删，零生产消费实证在案；权威表灭失挂账随之销项） | 权威表指向 w583_stage2_contracts/SCHEMA_DRAFT.md，原始件已灭失（2026-09-12 清理）——载体删除后不再存在迁入问题 | 契约族残留引用 = 零（src/测试仓 grep 实证）；历史裁决原文归 git 历史 |

已核对合规（抽样，供后续审计对照，不再逐一列出）：族 A 全部 `[索引定义]` 字段（`SellBench.bench_idx`/`DeployMove.bench_idx`/`DeployMove.to_row+to_slot`/`SellDeployed.deployed_idx`/`SwapDeploy.deployed_idx+bench_idx`/`FillSpec.idx`/`PickEvent.option_idx+refresh_slots`）、`GameState.bench`(BenchView)`/front_row/back_row` 容器注释、`BenchSlot.kind` 五分类与 `Unit.slot` 索引定义、`cw_identity_obs.py::bench_item_slots`、`prep_actions.py::drag_bench_to_sell`、`cw_op_equip_all.py::register_equip_worn`、`cw_state.py::xp_apply_clicks`。（`cw_exec_state.py::_invest_refresh_used_slots` 抽样条目已随该字段退役移除。）

## 7. 接口注（被挡下游的消费面依据）

- **装备穿着主病灶策略语义再评估（opening 窗口与非 key_equips 释放条件）与装备释放条件批的策略语义评估**，其执行侧事实依据 = 本契约 §3.7（装备 owned 搬运链与穿戴销账）+ §4.3 末段（穿戴的执行期时序：稳帧/CV-diff 验穿/补救链/owned 授予快照每次执行只记一遍）+ §5 装备臂行。两任务判读执行侧「穿上/没穿上」证据时，以 `register_equip_worn` 销账链与 `equip_zero_wear` 哨兵的契约语义为准，不以画面单帧直觉为准。
- 两任务涉及卖出/释放条件评估时，其动作面坐标系 = §2.2 双族对照（族 A `bench_idx`/`deployed_idx` + expect 代际校验；族 B 物理槽位无 expect）；评估「卖没卖对人」必须先分族再读数。
- 本契约的验证阶梯状态：L0（读面基线）/L1（单件验穿）已过（报告 = `.debug/temp/currency_war/_archive_20260908/projection_ladder/阶梯执行报告_L0_L1.md`）；L2（已穿非空样本）/L3（落空补救链量化）需实机窗采样，**不在本批**，其结论落地前，涉及「批量穿戴不覆盖已穿」「落空率数字」的策略假设按未证对待（口径）。
