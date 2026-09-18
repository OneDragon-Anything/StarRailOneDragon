# 黑板退役迁移（详设，阶段 3.2–3.5）

## 问题与约束

- 总纲接口契约 3（坐标契约）、4（写端唯一）约束本篇；阶段 3.1 已完成决策帧名单换源与 M7 读点切换（`details/cap-fix.md`），本篇在其基础上把装备、占用、奖励球依次归位，最终删除 `gs.prep_obs`。
- 约束：识别 reader 本体（SIFT/OCR/模板）不动；本篇只迁移「识别结果的承载与消费」。

## 方案

### 阶段 3.2：装备归位（批 2）

1. **容器立穿戴位置域** `occupied_equips`：Field value = `dict[str, list[str]]`，键 `'front:1'`/`'back:2'` 形态字符串（观察产物 `{(row, 物理槽位): [件名]}` 的序列化安全转换；坐标系依据 cw_prep_actions.py:98-101——row ∈ front|back，slot = 1-based 画面物理槽，与机械动作参数同域）。写端 = **director 装配点**（cw_screen_prep.py:733-738 现役装备观察写端旁，同环同纪律），不改采集层（`observe_full` 的 occupied 采集产物形状不变，仅落点由黑板改容器 observe）。
2. **M7 读源切换**（cw_equip_wear_plan.py:163-182）：`owned` ← 容器 `equips` 读口；`occupied` ← 新域读口。`None` 语义映射：容器 Field 未观察(None) = 识别域未就绪，维持现行 fail 门（:168-175 保守关）方向不变。函数签名不变（入参 session，内部换现读源）。
3. **entry.py 两处 owned 消费同批切换**：帧装备域装配（:793 `owned_equips=getattr(obs, 'owned_equips', None)`）与 **②′ 工具消费发射位的 owned 快照（:674 `_owned_snap = list(getattr(obs, 'owned_equips', None) or [])`）**——后者是工具臂评估输入，改容器 `equips` 读口（语义 = 现读库存全量，与 M7 同源）。
4. **`back_layout_slots` 归位**：M7 后排槽位戳记上界消费（cw_prep_actions.py:101-105）改读容器 `back_layout` Field **原值**——None（未观察）= 双弃权帧（语义等价黑板 None=布局未知），有值 = `int` 槽数；禁用 `back_capacity_of`（其 None→6 缺省会翻转弃权语义）。黑板字段随批 5 删。

### 阶段 3.3：占用改现算（批 3）

1. **席空数读端切换 = 复用既有读口，零新立**：kernel 已有 `bench_free_slots(gs)`（cw_game_state.py:1085-1092，`slot_occupies` 口径 :1079-1082——unit/supply_box/tome 天然占席，宝箱/典籍占席自动计入）与 `bench_is_full`（:1095-1100）。球谓词席自由槽读数（entry.py:141-146 `_sphere_bench_free`）改读 `bench_free_slots`：None（bench 未观察）→ BENCH_CAPACITY 保守（宁多收球不误卖，语义与既有口 None=不确定吻合）。
2. **前后排占用集（`obs.front_occupied`/`back_occupied`）不迁移、本阶段不动**（实施期修正：原稿误判其审计消费为容器侧）：双源对拍（cw_screen_prep.py:829-856，paddle OCR X vs CV 占用扫描）两条腿**均为识别面读数互证**，与容器无关；占用集本身 = 每步现读的识别轻字段（非状态账）。其消费 = 该对拍（合法存续）+ 黑板投影推进（cw_screen_prep.py:1053-1059，随阶段 3.5 投影退役消失）。
3. `free_bench_slots` 黑板字段消费已断（球谓词已切容器派生），随批 5 删;`deploy_vacancy`/`front_size` 同（无决策活消费）。

### 阶段 3.4：奖励球立域（批 4）

1. **容器新域** `spheres`：Field value = `list[dict]`，每项 `{color, x, y, r}`（观察产物 `(color, Point, r)` 同构、像素坐标平铺；球无槽号，坐标必须随识别走——总纲坐标契约）。kernel 立读口还原 `(color, Point, r)` 元组形态，消费面签名不变。
2. **写端**：备战入口观察链上报（两帧持存防抖 `filter_persistent_spheres` 留在观察链内部，cw_screen_prep.py:574-578，防抖状态 op 局部自持）。
3. **读端切换（三处，全量清单）**：球臂探针分支（entry.py:507-509）、**席自由分支发射位（entry.py:492-495，同式 `select_sphere_clicks(obs.spheres, ...)`）**、**席满让路门成效签名（entry.py:170-186 `_sphere_progress_sig`——`getattr(obs, 'spheres')` 球计数与 `getattr(obs, 'bench_chars')` 席计数两分量分别切容器球域读数与 `bench_free_slots` 派生**；此消费若漏切，批 5 删字段后签名经 getattr 缺省静默退化（门成效重置失效无报错），属本迭代要消灭的形态，列为本阶段验收项）。
4. **逻辑态迁移**：`ClickSpheres` 增 kernel 写口分支（`apply_prep_action_logic`，载荷坐标精确摘除，语义 = 现黑板腿 cw_screen_prep.py:974-978 逐位迁移）；黑板球腿删除。正本 `game_state/logic-updates/click-spheres.md` 的「容器 GameState 零写（视觉域推进）」语义翻转（正本更新清单）。
5. **死码块同批换源**：球路径腾席判据块（entry.py:522-566，结构性死码）内的 `obs.spheres`（:524）与 `obs.bench_chars`/`obs.deployed_chars`（:534-539）读点随本阶段换容器读口——批 5 删字段前消除对该块的不可达性依赖（cap-fix.md §方案-5 申报的归属落点）。
6. **对账收益**：球域写入进事件流，「点空 = 球未消」由下一入口观察回补覆盖的既有机制获得 journal 显影。

### 阶段 3.5：gs.prep_obs 退役（批 5）

1. **PrepObservation 全字段去向表**（删除清单以本表为准）：

| 字段 | 去向 |
|---|---|
| `bench_chars` / `deployed_chars` | 阶段 3.1 已切容器（entry 组装 + wanted 臂 + M7 读点）；本阶段删 |
| `owned_equips` / `occupied_equips` / `back_layout_slots` | 阶段 3.2 已切容器；本阶段删 |
| `spheres` | 阶段 3.4 已切容器（含 `_sphere_progress_sig` 与死码块）；本阶段删 |
| `boxes` / `tomes` | **占席与分派归容器 bench kind，写端本阶段细分补齐**（见下 1a）；决策臂改读 bench kind；字段本阶段删 |
| `free_bench_slots` | 阶段 3.3 已切 `bench_free_slots`；本阶段删 |
| `front_occupied` / `back_occupied` | 阶段 3.3 审计侧已切 `deployed_count_of`，投影面随本阶段退役；本阶段删 |
| `deploy_vacancy` / `deploy_divergent` / `deploy_stale` / `front_size` | 无决策活消费（frame 属性现算取代）；本阶段删（双源审计改观察链局部变量） |
| `shop_cards` / `overlay_state` / `overlay_options` | P1/P5 恒空字段（类 docstring 明文，cw_prep_actions.py:51/90-91）；删 |
| `state_gold_trusted` | F2 门（gold 仅 shop 开态可信）改为观察链局部派生位（= shop_open 现算，同现行 772 行式）；代码消费为零（全仓 grep 2026-09-18，攻击复核确认），**但 cw_observation.py:2177-2184 注释将该字段列为推荐读点——随本阶段同步改写该注释**（防僵尸指引）。字段删 |
| `shop_open` / `substate` / `event_overlay` | **保留**，宿主降级（见下 2） |

1a. **boxes/tomes 的容器表达补齐（本阶段前置工作）**：容器 `BenchSlot.kind` 枚举含 `tome`（cw_game_state.py:548）但**现役零写端**——读链把箱/典籍/书册卡统一为 `is_item_slot` 布尔，`bench_view_from_obs` 恒映射 `supply_box`（cw_game_state.py:1446-1451），容器无法区分 OpenBox 与 OpenTome 触发物。补齐 = 观察写端细分：`bench_view_from_obs` 增可选参数 `item_kind_by_slot: dict[int, str]`（缺省空 = 现行行为逐位不变），备战观察链用同帧已现读的 `read_supply_boxes`/`read_tomes` 槽号集（cw_screen_prep.py:579-580）构造该映射（boxes 槽 → `'supply_box'`、tomes 槽 → `'tome'`；书册卡维持现役 reader 归属，随 boxes 映射）。决策臂切换：OpenBox/OpenTome 分派（entry.py:458-461）改读容器 bench 首个 `kind='supply_box'`/`kind='tome'` 槽号——两臂输入等价（槽号 1-based 同坐标系）。**legacy 往返配对同步补齐**：`bench_slots_to_legacy` 的占位件分支现仅认 `supply_box`（cw_game_state.py:1511-1519，`tome` 会落入非 unit 兜底 → None）、`bench_view_of_slots` 恒映射 supply_box（:1663-1668）——细分后必须在两处补 `tome` 配对分支（→ `BenchChar(is_item_slot=True)` 占位件形态，与 supply_box 分支同构），否则批 1 换源后的 legacy 消费面（部署帧 bench 候选、sell_gate 占位恒拒线、`_cidx_of` 槽号→下标映射）会在 tome 槽拿到 None 与现行为产生静默差；补齐后 legacy 消费面零行为差（tome 槽呈现 = 现行 item-slot 占位件同形态）。
2. **宿主降级**：`PrepObservation` 类保留瘦身后的三个控制信号/元信息字段（`shop_open`/`substate`/`event_overlay`），宿主 = 备战环 op 局部对象（不进 gs、不进 session）；bail 判定（cw_screen_prep.py:1486/1650）与观察链内部门参数（:622/:1325/:1383）就地消费。`gs.prep_obs` 槽删除：声明（cw_game_state.py 非 Field 容器字段）+ 全部写点（cw_screen_prep.py 内 `game_state_of(x).prep_obs = obs` 形态各处，:536/:895/:1595/:1758 及 ports 路径 ：532 附近）+ 决策入口读点（bridge.py:**179** `obs = self.gs.prep_obs` 与 ：180-184 None 抛错分支）的 obs 传递面收敛。
3. **动作后写端拓扑（调用位迁移，单一更新点）**：`_project_prep_obs` 函数**整体删除**；kernel 写口 `apply_prep_action_logic`（cw_game_state.py:2293）的调用迁移为备战环执行点的**统一调用**——`_act_execute`（cw_screen_prep.py:1565 执行体）发出动作后即调 `apply_prep_action_logic(gs, action, produced_by=..., sig=...)`，成为动作后逻辑态唯一更新点。**写口词表补齐清单**（现役只有容器腿的四个动作，其容器分支随本阶段进写口）：`OpenTome`/`OpenBookcard`（腾席 = bench 槽 kind → `empty` 化）、`WearEquip`（容器 `equips` 摘件，阶段 3.2 语义迁移）、工具原子族（`equips` −1，目标件消失仍由观察覆盖——`game_state/action-logic-state.md` :283 语义不变）。**`OpenBox` 不进补齐清单**：该动作已 R7 终结化——结束判定先行交回外循环、不经投影口（cw_screen_prep.py:938-939 投影 docstring 明文申报），其容器态由下一次入口 heavy 观察覆盖，无需逻辑态直写。词表外类型的 AssertionError 响亮防线随分派迁入写口内部（现役在 _project_prep_obs 尾部 ：1093-1097）。黑板推进写点（:1594-1595/:1758）删除。
4. **缓存与 light 分支退役**：`_cached_bench`/`_cached_deployed`/`_cached_vacancy`/`_cached_gold_trusted`/`_cached_owned_equips`/`_cached_occupied_equips`/`_cached_back_layout_slots`/`_cached_shop_cards`（shop payload 容器已有）/`_prev_spheres_raw`（防抖移观察链局部）全删；`_observe` 的 light 分支整体退役（「现生产无调用方」申报在册，cw_screen_prep.py:546）。
5. **验收**：符号清零 grep（`gs.prep_obs` / `prep_obs` 写读点 / `PrepObservation` 已删字段 / `_cached_` 系 / 黑板投影腿分支 / `state_gold_trusted` 残留指引注释）+ 全量测试 + **OpenBox/OpenTome 臂分派用例**（bench kind='supply_box'/'tome' 槽号分派正确）+ 实机一局 smoke（决策迹锚与改前同难度局对照，参照 `changes/2026-09-16-strategy-input-unification/landing.md` 的 smoke 申报形态；候实机窗口，不阻代码收口、阻迭代收尾）。

## 关键取舍

1. **宝箱/典籍像素坐标不落盘**——动作参数只需槽号（entry.py:458-461 实证消费形态），槽号→点击坐标是 1080p 固定布局映射（执行器 `_bench_pts` 簇现算）；落盘像素会引入第二份坐标真值。用户裁定 2026-09-18（宝箱/典籍在备战席里，归 bench 表达）。
2. **`PrepObservation` 降级保留而非整类删除**——event_overlay bail、观察链门参数、对账元信息是环内控制信号而非游戏事实，立容器域会让「写端唯二」反而多出观察写端；局部对象不违反「策略器唯读 game state」（策略器不再读它）。
3. **occupied 域立容器 vs M7 挂观察参数直喂**——直喂会让装备域出现「owned 在容器、occupied 走参数」的双轨，且观察产物跨函数透传正是本次退役要消灭的形态；容器域与 equips 平级、同一观察写端上报，契约一致。
4. **奖励球立容器域 vs 留局部**——用户裁定 2026-09-18（奖励球带坐标上报 game state）：球是跨动作存续的盘面事实（点掉才消失），点空回补机制天然需要对账载体；与宝箱/典籍（开掉即消耗、槽位即坐标）分流的判据 = 有无槽号。
5. **boxes/tomes 细分走观察写端参数化 vs 识别层改类型**——识别层给 `is_item_slot` 升类型枚举要动 SIFT 读链本体（本迭代约束禁改）；观察写端已持有同帧 boxes/tomes 槽号集（两个独立 reader 现成），参数化细分零识别改动、缺省参数保旧行为逐位不变。
6. **席空数复用 `bench_free_slots` vs 新立读口**——既有口（cw_game_state.py:1085）`slot_occupies` 口径已含箱/典籍占席且 None=不确定语义与球谓词保守方向吻合；新立同语义读口 = 本迭代主线（灭双源）里再造双源。对立方案放弃。
