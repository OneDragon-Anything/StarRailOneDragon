# CwActionMoveUnitOp（统一拖动）参数面迁移设计稿（r1）

> 迭代：CW 动作 op 迁移流水线 · 设计角色产出（统一拖动 op 批 = 第三棒）。
> 上批 = 工具原子七类参数面迁移（changes/tool-use-param-surface/design.md，已落地 commit 76a94c27c）；上上批 = WearEquip 穿装（changes/wear-equip-param-surface/design.md，commit db4697e40 终稿）。
> **范围裁定（用户指令，每迭代只切一个 op）**：本批只做 `CwActionMoveUnitOp` 一件；SellDeployed/SellBench 撤出本批、待后续独立迭代（§9 申报行 1）。
> 冻结宪法（用户裁定，穿装批成文）：①动作 op 执行路径零 gs 依赖；②参数面三分法；③名称字段 = 语义参数（可选，不参与校验与定位，仅日志）——记账面亦零消费；④坐标新鲜度纪律归调用方；⑤参数 dataclass 统一补 `from_dict`；⑥gs 给实体记录坐标（坐标伴随域）；⑦每个 op 一个迭代，牵涉面一次改净。
> **记账路径总契约（正文 = `skills/sr-od-dev-currency-war/references/flow/action-op.md`「记账路径总契约」条款）第三适用者**；本批逐 op 差异在 §1.4 申报：本 op 对象住槽位表不住坐标伴随域，记账键 = 槽位下标、记账载荷 = 槽位反查产物/状态推导名（「槽位反查」= 总契约精神在本域的既有形态）。

## 0. 本批范围

`operations/cw_op/cw_move_unit_action.py::CwActionMoveUnitOp` + 词表 param `CwActionMoveUnitParam` + 上报层调用面（outcome 消费形态）+ 全部引用。

现状债（迁移动机）：

| 债 | 现值 | 迁移形态 |
|---|---|---|
| 机械半消费执行器点表 | `env.executor._bench_pts/_front_pts/_back_pts`（构造期缓存）+ `ex._drag` | 机械半自持：op 内 `row_area_centers` 现读点位表 + 模块级 `drag_char_guarded` 原语 |
| 后排扩格槽必拒（潜在 bug） | `ex._back_pts` = `row_area_centers(ctx, '后排')` 前缀只匹配基线 `后排-1..6`，扩格局（宝钻 7/8/9）后排槽拖动今日必拒——与穿装批 §1.2-2、工具批 §1.2-3 已修形态同款 | 新参 `back_slot_count`（布局档静态解析），后排 7-9 可用 |
| outcome 丢弃 | `report_action_move_unit_param` 返回值不消费，陈旧提案拒单对直调方不可见 | 穿装/工具批 M-r3-1① 同形：`applied=False` → round detail 追加拒单段 |
| param 缺 `from_dict` | MCP `run_operation` JSON 通道无法构造 | 共享 `action_param_from_dict` 一行委托 |

## 1. 本批特有设计题裁决

### 1.1 裸中心拖点债（工具批 §11 申报行 2 的本批兑现）：保留裸中心，拖点权威分域成文

**裁决：MoveUnit 拖点保留 `row_area_centers` 裸中心（角色拖动族权威派生式），+21 校准（`row_drag_points`）不外溢到本族；两族分域在两侧 docstring 对偶成文。**

论证（根源两问：根 = 「拖点派生式的权威」绑定的是**交互族**而非先到的迁移批；修分域 = 修根，统一才是把一族实测校准抹掉的症状修法）：

1. **交互机制不同族，各有机背书**：角色拖动 = 整卡可拖、卡中心拖 + hold0 按下即移（`operations/actions/drag_cw_char.py` 模块头实测背书：中心 drag 飞霄 bench→bench → 上阵 ✓，且明确推翻旧「avatar 偏移 + 长按」假设）；装备 icon→角色卡 = 落点必须命中卡内头像区（+21 = D-36 校准，穿装批以被替换稳帧轮询标定）。两族落点目标不同（槽位格 vs 卡内热区），「同一交互同一拖点」原则在族内成立、跨族不成立。
2. **prep-contract §1 既有声明同向**：备战栏/前排/后排三排「画面点位」单一源 = `row_area_centers` 中心点——本 op 迁移沿用同一单一源，坐标值逐位零变化（迁移等价性最强形态）。
3. **工具批的统一是族内统一**：工具 char 模式 = 装备 icon→角色卡交互，与穿装同族，故统一 +21 成立；其 §11 申报行 2 已预告「角色拖动/拖出售区交互族不同，是否统一归交互族实机核对批」——本批 = 该批的 MoveUnit 半，裁决 = 分域；统一方向被否（把已背书落点改成无背书参数 = 风险方向反了）。SellDeployed/SellBench 半随各自迭代裁定（预期同判，见 §9 申报行 1）。

落地：

- `row_area_centers` docstring 补申报（拖点权威分域的角色拖动族半边），`row_drag_points` docstring 补辖域声明（装备 icon→角色卡族半边）——两处对偶闭合工具批申报行 2 的 MoveUnit 半；
- `prep_actions.py` 新模块级机械原语 `drag_char_guarded(op, ctx, src, dst)`（失焦守卫 + sim 分支 + 统一拖拽原语 `DragCwChar.drag_char`，§3.2）；
- **实机核对义务**：验收序列（§7）加「拖拽落点核对」——bench→front 空槽与占槽、bench→bench、下场形各一，以下一帧实读板面为准核对落位。迁移后坐标源路径变化（executor 构造期缓存 → op 执行期自解析同一静态档），坐标值理论逐位同，落点核对 = 等价性的实机背书。

### 1.2 换位规则不一致（单局实机样本）：不钉结论、零守卫新增、applied = 机械事实

**现象申报（单局样本，待复核）**：备战→前排占用槽拖拽换位未生效（2★↔1★ 槽交换形态）；同局备战→后排占用槽交换成功。单局样本不钉「前排占用槽换位被游戏拒绝」结论——不可排除拖拽链噪声、星级/银狼变换窗交互等替代解释。

**裁决**：

1. **上报语义不改**：applied = 机械事实——拖拽已发出 + 按推演矩阵写入（目标槽有人 = 交换交互）。注册表 MoveUnit 行既有申报「拖拽语义 = 游戏规则：目标槽空 = 放置、有人 = 交换交互，执行层不判断占位、不拒、禁静默换槽」原样成立；不可假定换位恒成功 = 不在动作层做任何「先判断目标槽占用再决定发不发」的分支。
2. **守卫零新增**：前置拒绝占槽换位 = 流程侧决策闸门（分层违例：动作该不该发归策略侧），且会误杀后排合法换位（后排样本实机成功过——两种结果都真实存在，前置拒绝单向误杀）。op 内守卫断言域（域非法/槽越界/负下标/back_slot_count 键域外）照 §2.2，不扩。
3. **失败治理归既有三道结构**（换位被游戏拒绝形态下系统表现）：①计划执行期拖动与重观察交替（`StrategyState.pending_reobserve`）+ 观察帧对账——自上报推演的交换 vs 实读板面不符即暴露；②级联卡死出口（连续 2 次重观察无进展 = 计划失败，`entry._emit_yield_plan` 既有）；③决策循环按新观察自然重派（差分执行器 diff 幂等重产，第 6 步常规部署同构）。系统不炸，该位不收敛 → 卡死出口交还。
4. **待复核义务**：验收序列（§7）加「占槽换位两形」核对（前排占槽/后排占槽各一）；复现 ≥2 局 → 根因归 game 知识批（推演矩阵分支化 or 交互替代路径修正，落 `docs/game/currency_war/research/` + 上报推演矩阵），禁动作层补丁（「禁以偶发结案」纪律：失配告警拦停的每个未生效查到根因修根因层）。

### 1.3 交替机制交互题：MoveUnit aftermath 不触碰 `owned_equip_xy` 失效面——零交替机制改动

**推演（MoveUnit aftermath 对坐标伴随域的影响面，逐域核验）**：

| aftermath 产物 | 载体 | 与 `owned_equip_xy` 的关系 |
|---|---|---|
| 角色换位/上场/下场/席内挪位 | `gs.bench` + `gs.deployed`（上报推演矩阵整值替换写） | 零交集：装备库存网格坐标伴随域的键 = **owned 库存条目名**（`gs.equips` 名单的坐标像），MoveUnit 零 `gs.equips` 写端 |
| 穿戴件随角色移动 | 穿戴件住 `unit.equips`（角色载体），不入 owned 池 | 零交集：owned 网格坐标面只描库存格（装备区格心，y 值域 90-710），穿戴件在角色身上不在库存格 |
| 备战席占用变化 | `gs.bench` 槽位表 | 零交集：备战席住角色/占位道具，装备库存网格是独立面板区，两者画面区域不相交、布局互不驱动 |
| 场上部署行变化（穿装目标端 row/slot 定位面） | `gs.deployed` 槽位表 | **坐标面零影响**：穿装目标端拖点 = `row/slot` → screen_info 排 area 静态解析（`row_drag_points`，槽位格坐标不随内容移动）；MoveUnit 改变的是「哪个人在哪个槽」（占用映射），不是槽位格坐标——受影响面 = 穿装计划的目标端**占用反查**（row/slot → 槽现任单位），那是提案代际域（计划逐帧重建 + 单动作收敛 + Obs 交替既有治理），不是坐标伴随域 |
| 装备网格 reflow | 仅由库存内容增删驱动（获得/消耗/回收） | MoveUnit 零库存增删 → 网格条目格位不变 → `owned_equip_xy` 坐标恒新鲜 |

**结论：MoveUnit aftermath 不触发 `owned_equip_xy` 失效——交替标志 `cw4_equip_xy_pending` 本批零置位端、零机制改动**（现役置位端 = 穿装发出点 + 工具原子发出点，不变）。直觉「不受影响」经逐域推演成立；唯一需要辨析的「部署行变化 → 穿装目标端」属占用反查的代际域，非坐标伴随域，且已有逐帧重算 + Obs 交替治理覆盖。卖出族（装备回收 → 库存增长 → 网格 reflow 风险）才有交替延伸题——随 SellDeployed/SellBench 各自迭代裁决（§9 申报行 1），本批不预设。

### 1.4 记账路径核验：MoveUnit 已合规（槽位反查产物形态），零上报函数改造

**逐消费面核验**（`kernel/cw_action_report/move_unit.py` 现值）：

| 记账消费 | 现形态 | 名称来源 |
|---|---|---|
| bench/deployed 两域槽位写 | 推演矩阵按源/目标槽现值推演（放置/交换/下场/挪位全分支，整值替换单笔写） | 槽位反查产物（`bench_slots[idx].unit` / `deployed[idx]`），全状态推导 |
| 银狼变换窗 | `effective_cost(gs, …)` 现读 + `merge_cascade_write` 级联 | 状态推导 |
| board 羁绊计数 | 行写端挂钩增量重算（禁手写） | 派生量 |
| 上场锁/唯一性守卫 | `deploy_lock_block_reason` / `board_unique_key` 按 unit 键 | 槽位反查产物键 |

**结论**：记账键 = 槽位下标、记账载荷 = 反查产物——**总契约精神（名称降级为反查产物）在本域的既有形态 = 槽位反查**。总契约的「坐标伴随域反查」路径辖域 = 住坐标伴随域（`gs.owned_equip_xy`）的装备网格条目（名称↔坐标需对照表反查，因网格 reflow 会移动条目）；本 op 对象住槽位表（置 None/empty 不移位坐标系，槽位跨动作组恒稳），**槽位表本身就是名称↔位置对照表**，按下标反查槽现任内容 = 同一精神的无表形态。`report_action_move_unit_param` **零改造**。

**宪法③核验**：`CwActionMoveUnitParam` 无名称语义字段（无 item_name/char_name 形态）——宪法③对本 op = 空集成立。`expect` = 提案代际防线字段（发出点写入、上报层 stale_proposal 拒单消费；prep-contract §3 既有申报），性质 = 防线非语义名，**保留**：战斗链批量发射边界载体（action-op.md §1 边界载体登记：`launch_prepared_battle` 一次产整批 MoveUnit 参数、逐个 execute 间状态容器被自上报改写）的陈旧化治理明确依赖「report 静态域拒绝」，expect（名不符拒单）是该治理的组成，删除 = 无等价物替换的防线削弱。

**op 侧行为变化（本批唯一上报调用面变化）**：op 自上报消费 outcome（穿装/工具批 M-r3-1① 同形）——`applied=False` 时 round detail 追加「记账拒单:<reason>(拖拽已发生,账未落)」，直调方经 round 结果感知拒单；机械 round_success 语义不变（拖拽确实已发生）。本 op 拒单形态现役 = 陈旧提案类（`move_slot_invalid`/`src_empty`/`stale_proposal`/`dst_unknown_unit`/`duplicate_on_board`/上场锁），零新增拒单码、零词表变更。

### 1.5 from/to 语义与 back_slot_count；sim 形态自洽

- **from/to 语义零变化**：四元组 `(src_domain, src_slot, dst_domain, dst_slot)`，域 ∈ {'front','back','bench'}；bench 槽 0-8 基 0 / front 槽 1-4 / back 槽 1-N 动态基 1（词表既有声明）。四象限 = bench/front/back 各作源与目标（9 组合，推演矩阵全覆盖）。
- **新增 `back_slot_count: int = 6`**（缺省 6）：后排拖点按布局档静态解析（`_layout_prefixes()[n]` 前缀 → `row_area_centers` 现读该档区表）——扩格局后排 7-9 槽拖动从必拒变可用（行为修复，§6 条 2）。守卫：src/dst 任一为 back ∧ `back_slot_count ∉ _layout_prefixes()` → AssertionError（键域外禁静默按 6 兜底，穿装/工具批同款）。
- **发出点填参**：`deploy_diff.py` 三处 MoveUnit 构造（place_missing/fix_misrow/disembark）+ `entry.py` 自救上场一处——`back_slot_count=back_capacity_of(gs)`（构造点均持 gs；`back_capacity_of` = 后排格数读口单一源，None 退 6 基线，与穿装批 `int(gs.back_layout.value or 6)` 同式且已封装，禁内联第二份）。构造点全部 keyword 传参（grep 已核），插字段行为安全。
- **sim 形态自洽（部署行伴随域形态）**：sim 局与实机同跑同一循环/op/策略——机械段 `cw_sim_ports.mechanical_io_allowed()` 为假静默跳过（穿装/工具同款 gate），上报函数族两执行面同源直调同一批函数。sim 局的 `back_layout` 伴随域 = 环境快照族字段：基线未写（None）→ 发出点读口退 6；宝钻/召唤扩展经 sim 效果链环境快照写（`on_diamond_acquired` 回调三写，live 同拍零写语义既有申报）→ 发出点与 op 两端同一读口同一档。「部署行伴随域形态」= back_layout 语义档（None = 未观察 6 基线 / 写实值 = 扩展档）；模拟态落位推演（`deploy_diff` 轻量模拟态按 `CwActionMoveUnitParam` 坐标系推进）与上报推演矩阵同核，自洽零 sim 改动。
- **直调形态**：param 补 `from_dict`（共享 `cw_vocab.action_param_from_dict` 一行委托）；`back_slot_count` 可省（缺省 6；直调后排槽按当帧 extras deploy_cap−4 传，与工具批口径同）。

## 2. 新参数面定稿

### 2.1 字段集变更（`kernel/cw_vocab.py::CwActionMoveUnitParam`）

- 新增 `back_slot_count: int = 6`（`dst_slot` 后；[索引定义] 三要素注释：坐标系 = 后排槽位画面物理总数 n（值域 6-9 = `obs.cw_back_layout._LAYOUT_PREFIX` 键域）；取值时机 = 生成期快照（发出点 `back_capacity_of(gs)` 现读）；src/dst 域均非 back 时忽略）。
- 补 `from_dict`（共享形态一行委托）。
- docstring 补记账路径总契约适用申报（§1.4 槽位反查形态 + expect 防线申报）。
- `action_key` 幂等键自动含 back_slot_count（行为参数入键正确——同槽位不同布局档 = 不同拖拽落点，禁共享屏蔽粒度）。

### 2.2 守卫断言（op 内，校验落点契约）

全部 `raise AssertionError` 响亮暴露，禁兜底坐标/禁负下标回环（下界显式闭合）：

1. domain 非法（`∉ {'front','back','bench'}`，src/dst 各一）→ 断言（现状保留）；
2. slot 越界按域解析表长闭合：bench `0 <= slot < len(备战栏点位表)`、front `1 <= slot <= len(前排点位表)`、back `1 <= slot <= len(档位后排点位表)`（现状保留，表源改 op 内现读）；
3. **新增** src/dst 任一为 back ∧ `back_slot_count ∉ _layout_prefixes()` → 断言。

## 3. 牵涉面清单（逐文件；grep 全量已核）

> 路径根 = `src/sr_od/application/currency_war/`。

### 3.1 `kernel/cw_vocab.py` — §2.1 字段集

### 3.2 `prep_actions.py` — 机械原语宿主与拖点分域成文

- **新增模块级 `drag_char_guarded(op, ctx, src, dst)`**：角色拖拽机械原语 = sim 分支（`sim_backend_installed()` 真 → 静默返回）+ 失焦守卫（窗口后台化拖拽输入静默丢，先激活）+ 统一拖拽原语 `DragCwChar.drag_char`。
- **失焦守卫单一宿主收敛**：`drag_bench_to_sell` 内联失焦守卫段删除、改调 `drag_char_guarded`（原散落 `executor._drag` 与 `drag_bench_to_sell` 两份内联副本 → 单源）。行为差申报：sim 分支从「函数首行早退（零点表读）」变「守卫先走、拖拽段静默」——点表读为静态档读取零副作用，守卫在 sim 亦可触发 = 防线统一（合法 bench_idx 0-8 对 9 区恒不触发）。`drag_bench_to_sell` 的点表守卫保留（原语自守卫 = MCP 直调原语面兜底，`cw_sell_bench_by_slot` 消费不变）。
- **`row_area_centers` docstring 补角色拖动族权威派生式申报**、**`row_drag_points` docstring 补装备 icon→角色卡族辖域声明**（§1.1 两处对偶）。
- **执行器过渡形态保留**：`PrepActionExecutor._drag` 方法与 `_front_pts/_back_pts` 点表**不退役**——本批后仍有 SellDeployed 一组消费者（其迁移批退役）；`_bench_pts` 保留（开件三类 + SellBench 过渡期消费）。`_drag` docstring 与执行器注释标注过渡宿主身份。

### 3.3 `operations/cw_op/cw_move_unit_action.py` — op 执行体重写

机械半自持：守卫三形（§2.2）→ 点位静态解析（`row_area_centers` 三域，back 按档前缀）→ sim 分支 `mechanical_io_allowed()` → 实机 `drag_char_guarded` + 2s 固定等待（羁绊徽章动画窗口径逐字沿用）→ 自上报（outcome 消费，detail 拒单段 §1.4）。签名改 `env: PrepExecEnv | None = None`（穿装/工具批同款，零 env 消费，形参保留 = 注册表构造签名兼容）。docstring 重写（含单局样本现象申报 §1.2 摘要 + 落点核对义务提示 + 词表参数面指引）。

### 3.4 `strategies/impl/mandate_v1/deploy_diff.py` — 发出面填参

`deploy_diff_actions` 内三处 MoveUnit 构造补 `back_slot_count=back_capacity_of(gs)`（函数持 gs；import 补 kernel `back_capacity_of`）。轻量模拟态推进零变化；换星直卖的 SellDeployed 构造不动（其迭代批辖域）。

### 3.5 `strategies/impl/mandate_v1/entry.py` — 发出面填参一处

`_emit_deploy_moves_scoped`（自救上场 MoveUnit，持 `state`）补 `back_slot_count=back_capacity_of(state)`。yield-plan/m1p 的 SellDeployed 发出点不动。

### 3.6 `operations/cw_op/cw_action_registry.py` — 零改动

import 与注册行类名不变；组装签名兼容 env 缺省化。注册完备测试机械约束对象不变。

### 3.7 `kernel/cw_action_report/move_unit.py` — 零改动

§1.4 核验结论：槽位反查产物形态已合规，零改造。

### 3.8 测试仓镜像测试 — 见 §5

### 3.9 文档面 — 见 §8

## 4. op 执行语义（迁移后）

1. 守卫断言（§2.2）。
2. 点位静态解析：`row_area_centers(ctx, 前缀)`（零截图零识别；back 前缀 = `_layout_prefixes()[back_slot_count]`）。
3. sim 分支：`mechanical_io_allowed()` 为假 → 机械段静默跳过（上报函数族照走——sim 期望态推进 = 自上报单点，两执行面同源）。
4. 实机机械段：`drag_char_guarded`（失焦守卫 → 中心拖 + hold0）→ 2s 固定等待。
5. 自上报：`game_state_from_ctx` → `report_action_move_unit_param`；`gs is None` = 无处记账跳过；`outcome.applied=False` → detail 追加拒单段（§1.4）。
6. round 结果：恒 `round_success(detail)`（机械成功语义——拖拽已发出；零 round_fail 通道，回执受阻码表零变更）。

**决策侧参数现算契约适用申报**：本 op 发出域 = 备战决策环（每动作重 decide，同帧承诺成立）+ **战斗链批量发射边界载体**（`launch_prepared_battle` 一次产整批 MoveUnit 逐个 execute——action-op.md §1 既有登记，陈旧化治理 = report 静态域拒绝 + 观察 reconcile，expect 防线是组成，§1.4）。

## 5. 测试设计（sr-od-test，按 §11.4 harness 规范；镜像路径，命名无批次号）

1. `test/sr_od/application/currency_war/kernel/cw_vocab/test_cw_vocab.py`（既有文件扩展）
   - MoveUnit `from_dict`：全字段 dict 逐字段断言；最小 dict（4 必填项）落全缺省（`back_slot_count=6/reason=''/expect=''`）；未知键忽略。
   - `action_key`：back_slot_count 不同产不同键；`route_tag` 不入键。
2. `test/sr_od/application/currency_war/operations/cw_op/test_cw_move_unit_action.py`（新建；harness 剧本）
   - 守卫：domain 非法（src/dst 各一）/ slot 越界三域 / 负 slot / back_slot_count 域外 → AssertionError 且零拖拽。
   - 实机形态（screen_info 真档案 → 期望值同源派生）：bench→front 拖拽记录 `start == 备战栏-N rect 中心`、`end == 前排-M rect 中心`（裸中心锁测，§1.1）；back 槽按档位表（含 `back_slot_count=7` → `后排7槽-N` 档，行为修复锁测）。
   - **round detail 拒单码**：种子使上报拒单（src 槽空）→ round_success 且 detail 含「记账拒单:src_empty…(拖拽已发生,账未落)」；正常记账帧不含拒单段。
   - `env=None` 全链；sim 形态（port 关闭 → 机械零调用 + 自上报照走）；`with fast_sleep(): op.run()`。
3. `test/sr_od/application/currency_war/strategies/impl/mandate_v1/deploy_diff/test_deploy_diff.py`（新建；纯函数直测）
   - `back_slot_count` 填参锁测：种子 `back_layout=8` → 产出的 MoveUnit 参数 `back_slot_count == 8`；None → 6。
4. `test_action_registry.py`（既有面）：零改动预期。

验收阶梯（skill §3）：L1 → L2（点名新增文件 + test_action_registry）→ L3 全量 commit 前。**实机验收序列 = §7**。

## 6. 风险与行为变化清单

1. **行为变化：round detail 新增拒单段**（outcome 消费）——journal 判读面新增「记账拒单:…」段（现役触发 = 陈旧提案拒单帧：src_empty/stale_proposal/槽越界零写/上场锁/唯一性键）；遥测分键零新增（reason 词表封闭不动），首局对照判读申报。
2. **行为修复：后排 slot 7-9 从必拒变可用**（现状点表只匹配基线 6 槽）；判读基线：扩格局（宝钻 7/8/9）后排部署完成率预期上升。发出点填参随批落地（§3.4/§3.5），缺省 6 兜底帧 = 布局未观察帧（守卫响亮拒绝扩格槽号 = fail-closed 正确方向）。
3. **`action_key` 幂等键扩域**：键含 back_slot_count——同槽位不同布局档 = 不同键（屏蔽计数粒度更准，方向正确）；既有键形态历史数据不可比，判读基线申报。
4. **拖点坐标等价性**：`row_area_centers` 裸中心零变化（同源同一静态档）；坐标源路径变化（构造期缓存 → 执行期现读）理论零差，实机落点核对 = 背书义务（§1.1/§7）。
5. **`drag_bench_to_sell` sim 分支行为差**：守卫先于静默（§3.2）——合法域内零可感差异，非法 bench_idx 在 sim 亦炸（防线统一方向）。
6. **换位规则待复核**（§1.2）：单局样本不钉结论；复现 ≥2 局走 game 知识批，动作层零补丁。
7. **执行器属性过渡保留**：`_drag`/`_front_pts/_back_pts` 保留至 SellDeployed 迁移批——过渡宿主身份已注释标注，其迁移批退役时同步清。

## 7. 实机验收序列（给实施角色）

1. **拖拽落点核对（§1.1 义务）**：①bench→front 空槽上场；②bench→bench 席内挪位；③bench→front 占槽交换（前排形态 = §1.2 待复核项，成功/失败均如实记录）；④bench→back 占槽交换一例（后排形态，样本局成功过——回归确认）；⑤场上→bench 下场形（经交换形态核对）。每例以下一帧实读板面核对落位。
2. **扩格局核对（§6 条 2）**：宝钻/召唤局（back_layout 7-9）后排拖动一例，核对档位拖点落位。
3. **直调单件会话**：run_operation 跑 MoveUnit 一例（from_dict 通道），核对 round detail 与落位。

## 8. 文档与 skill

- `skills/sr-od-dev-currency-war/references/flow/prep-contract.md`（本批更新，文件当前无并行批在飞改动）：§1 动作字段坐标系族描述更新（MoveUnit 补 back_slot_count 与 op 自持点位解析、拖点权威分域申报）；§3 取值时机表补 MoveUnit 行（back_slot_count = 生成期快照，发出点 `back_capacity_of(gs)`；src/dst 槽位 = 生成期=执行期不变）；§5 部署臂行同步。
- `skills/sr-od-dev-currency-war/references/flow/action-op.md`（**收尾义务，本批不动**——该文件有并行批措辞规范化清扫在飞未落库，禁混提交）：§5 备战族 MoveUnit 行改写（机械半自持/back_slot_count/拒单 detail/拖点裸中心权威分域）；§1 记账路径总契约条款「已迁两批」→「已迁三批」+ 本 op 逐 op 差异附记（§1.4 槽位反查形态）。并行批落库后由实施/收尾角色执行。
- 玩家 skill：零改动（玩家面拖角色用 `DragCwChar` op（`operations/actions/`，MCP 直调面签名不变）；CwActionMoveUnitOp 非玩家直调面）。
- `docs/develop/sr_od/application/currency_war/game_state/fields.md`：零改动（零 gs 字段变更、零拒单码变更）。

## 9. 申报行（相邻问题，本批不修）

1. **SellDeployed/SellBench 待后续独立迭代**（用户裁定：每迭代只切一个 op）：两者各自牵涉面 = 机械半自持（executor `_drag`/`_front_pts/_back_pts` 随 SellDeployed 迁移退役；SellBench 双域 env 形态保留裁定）、`back_slot_count` 新参、卖出 aftermath 的交替标志延伸题（装备回收 → owned 网格增长方向 reflow，§1.3 同族推演在其域重做）、裸中心拖点分域申报（预期同 §1.1 判）、outcome 消费、from_dict。本批已为其铺路：`drag_char_guarded` 原语（卖出族拖拽并入宿主面）、词表共享 `from_dict` 形态先例。
2. 开件三类（OpenBox/OpenTome/OpenBookcard）仍消费 `executor._bench_pts` 做守卫——开件族迁移批（含 bookcard slot=None 硬 gs 分支已知项）随批退役。
3. Pick* 族契约状态——既有登记，非本批。
4. 战斗链批量发射（`launch_prepared_battle`）的 MoveUnit 批内 expect 全缺省形态（构造点未填 expect）——边界载体既有登记的治理已覆盖（report 静态域拒绝），expect 填参完整性归发射准入批核。
5. `entry._emit_deploy_moves_scoped` 自救上场的 MoveUnit 不发 Obs 交替（告警帧救援语义，零计划游标）——落位对账归下一入口 heavy 观察，既有形态不动。
