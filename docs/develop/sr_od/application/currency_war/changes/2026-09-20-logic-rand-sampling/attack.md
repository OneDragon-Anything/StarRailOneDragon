# logic-rand-sampling 设计对抗报告

> 攻击者独立审查（核一·无前提 / 核二·规范遵循 / 核三·治本核验 + 定稿试读），对照 `docs/develop/harness/iteration-design.md` §5/§7。全部代码/文档锚均经 grep/read/git 实证。

## 结论：**需修订（存在 blocker）**

blocker × 4，major × 3，minor × 4。根因归层（语义层）成立、修法是根（采样语义 + 上报函数单一源 + 显式范式化），核三通过；败在定稿试读：sim 接线与批式载荷两个面上「实现者无需再设计」不成立，且掉落形态与在册游戏知识存在未调和冲突。

---

## Blocker（未解决不得定稿）

### B1 | design.md §0 裁决2 / §2.3 / §2.4 | 掉落第四形态「箱」与在册游戏知识冲突未调和，采样面整体缺箱分支
- **问题**：设计按口述三选一（金/装备/角色）建模。但在册依据记载点晶矿可掉**箱**且落席占槽：
  - `docs/develop/sr_od/application/currency_war/game_state/fields.md` §4.2 ClickSpheres（L799-800）：「游戏事实=采晶矿即开启、内容即时入账、**角色/箱落席占 1 槽**、席满点不动」；
  - `strategies/impl/mandate_v1/entry.py` L267-270：CwActionCollectOreParam「末批判——本批为序列内最后一批（**可能掉箱后截断**）」——策略器在册语义明确认为点矿会掉箱；
  - `docs/game/currency_war/research/final_comps/final_wandi_burn.md` L129：「晶矿(金币/角色/装备/**稀有物**)」——研究档第四类。
  设计全文无「箱/稀有物」字样：采样器支撑集、三分支写表、五域标记集、席满守卫（箱也耗席）均无箱分支。若箱形态真实，落地后该动作对箱掉落零表达、席满守卫口径错。
- **依据**：事实核对义务（本审规程）；规范 §5 规则1「设计信任二手转述而与游戏真值不符」所防事故的原型。
- **建议修法**：不重开口述裁定，但设计必须增「在册冲突调和」段——либо补一条用户裁定明确三选一覆盖/否决在册箱记载，либо按在册知识补箱分支；同时正本清单补 fields.md §4.2 ClickSpheres 与 entry.py 末批判依据链的同步项。二者取一前不得定稿。

### B2 | design.md §2.3 / §2.4 | 多点载荷的采样语义未定义（一动作 = 多次采样？）
- **问题**：现行发射位是**批式多点**载荷——`entry.py` L527-544 `CwActionCollectOreParam(points=select_ore_clicks(_sf_targets, SPHERE_CLICK_BATCH_MAX_K))`，`collect_ore.py` L40 `_drop` 为集合，一次动作可点开多颗晶矿。而 §2.3 `roll_ore_reward` 只定义单次采样、§2.4 写表按**单一抽中类型**组织（三分支互斥）、标记集按单 reward 建。多点时：每点独立采样？写序逐点分组还是整动作一组？多点中一部分是角色时席满守卫按累计耗席计还是单空位？全部无答案。
- **依据**：规范 §5 规则2（定稿门槛）+ §7 核一定稿试读；代码锚 `select_ore_clicks`/`SPHERE_CLICK_BATCH_MAX_K` 实证（`entry.py` L527、`cw_prep_actions.py`）。
- **建议修法**：§2.4 显式定义逐点循环语义（每点一次 roll、每点独立三分支与标记、group_id 组织方式、多点耗席守卫口径），或显式裁定本批载荷恒单点并给出依据。

### B3 | design.md §2.5 | sim 接线未定义到可实施：「现有 rng 传递惯例」在 apply_player_action 不存在，CollectOre 委托分支也不存在
- **问题**：§2.5 称「`apply_player_action` 的 CollectOre 委托分支传 `stream_rng(...)`（形参随引擎现有 rng 传递惯例对接）」。实证：
  - `sim/cw_sim_actions.py::apply_player_action`（L95-137）**无 rng 形参**，分派表**无 CollectOre 分支**——`CwActionCollectOreParam` 现落入 `unsupported_action_type`；
  - 仓内唯一 rng 传递先例 = 引擎 `_apply_furnace`（`cw_sim_engine.py` L411-426）在 apply_player_action **之外**旁路直调带 rng 的腿函数，并非「apply_player_action 的惯例」。
  实现者必须自行设计：rng 形参加在 apply_player_action（新 kwarg？）还是引擎像 furnace 一样旁路直调上报函数？谁负责 uses 计数？均未定义。
- **依据**：规范 §5 规则2；任务书定稿试读攻面（sim 接线形参对接）。
- **建议修法**：§2.5 落到签名级：明确新增分派行 + rng 到达路径（推荐 furnace 先例——引擎侧旁路直调 `report_action_collect_ore_param(..., rng=stream_rng(...))`，apply_player_action 主表不动，或明确 kwarg 方案），并写明调用点。

### B4 | design.md §0 裁决7 / §2.5 | 流键 `M1x/ore` 无局内坐标：违反流键硬约束，同局多次点矿采样完全相同
- **问题**：`sim/cw_sim_streams.py` 模块头硬约束「流键 = 模块号 + **局内坐标**（如 M05/p1/r3）」，`stream_rng(seed,key)` 每次调用重派生 `random.Random(f'{seed}#{key}')`。固定键 `M1x/ore` 意味着同局内**每一次**点矿动作拿到同一 rng 种子 → 采样序列逐位相同（多 prep 期、同 prep 多批全中招）。裁决 8「采样即世界真值」在第二次及以后点矿时直接失效（世界被错误建模为重复奖励）。同族先例 `M10/炉/{uses}` 带使用序正是为此。
- **依据**：`cw_sim_streams.py` L7-11 硬约束 + L18 实现；`cw_sim_engine.py` L421 先例。裁决 7 给了流键名，但未豁免局内坐标约束——设计层必须把坐标方案定出来。
- **建议修法**：流键定义为 `M1x/ore/{uses}`（使用序，谁计数随 B3 接线一并定）；若坚持无坐标键，需给出「每局至多一次点矿」的依据。

---

## Major（修订后可定稿）

### M1 | design.md §2.2 #1 / §2.4 步3c+ | merge 步回调的调用侧写入契约不精确：一级合并可同时变更 bench 与行域，「每级落一行」无法表达
- **问题**：`_merge_bench` 是全场域（bench∪deployed）：一级合并可以是「carrier 在 deployed 升星 + bench 侧两份置 None」——bench 与 front_row/back_row **同级同时变更**。§2.4 步 3c+ 写「每级合并落一行」单行无法同时表达两域；on_step 触发时调用侧写哪些域（仅变更域？每级全写？）、值语义（整表）、以及每次行写自动触发 board 增量重算产生的中间态 board 行是否预期（逐步写会让 board 派生行按每级各出一行），均未裁定。实现者需自行设计写行方案 → 违反「无需再设计」。
- **依据**：规范 §5 规则2；`cw_merge_simulate.py` L225-287（全场域、载体场上优先）、`cw_game_state.py` L2971-2973（每次行写触发 `_resync_board_delta`）。
- **建议修法**：写明「每级合并后、每个**受该级影响**的域各落一行（整表值，evidence `proj_ore_merge#N`）；board 派生行随行写自动逐级产生，属预期流水」。

### M2 | design.md §2.4 步2/步3b | 未观察域（值 None）上的「值不变标记」与「现值+采样件」未定义
- **问题**：equips 未观察（`Field` 值 None，装备域未读是常态，见 fields.md §3.2.15）时：步 3b「现值 + [采样件]」= None + 件？步 2 对 gold/equips 等域写「值不变 = None」的标记行是否合法（observe 侧 None 是硬拒绝，write_logic 族对 None 的边界未在设计申报）？bench/front_row 同理（行域 None 时标记行怎么写、board 无基座跳过）。
- **依据**：规范 §5 规则2；`cw_game_state.py` L2676-2678（observe 拒 None）、L2800-2802（board 无基座跳过）。
- **建议修法**：§2.4 增边界行：目标域值 None 时的处理（建议：None 域跳写不标记——随机态标记对「本就未知」的域无信息增益，`logic_rand_fields` 语义也不变）。

### M3 | landing.md「正本更新清单」 | 清单遗漏 fields.md §4.2 ClickSpheres 与 action-logic-state.md §3.6——两处正文的「点晶矿记录层面」描述将被本迭代正面推翻
- **问题**：fields.md §4.2 ClickSpheres 现文「记录层面=采晶矿 op **不改席占位**，全部等后续观察覆盖（金币/装备即时入账同样等识别）」、action-logic-state.md §3.6 同口径——本迭代后点晶矿**改写** bench/gold/equips（采样+标记），该两节整体失真。清单只列了 fields.md §2.1/§2.3/§2.5 与 action-logic-state.md §1.1/§1.2，未含 §4.2/§3.6 → 「清单清零」后正本仍与实现矛盾。
- **依据**：iteration-design.md §3.2（正本清单 = 收尾判据）；规范 §5 规则4（全量同步复查）。
- **建议修法**：清单补两行：fields.md §4.2 ClickSpheres、action-logic-state.md §3.6 ClickSpheres ← 3.2。

---

## Minor（定稿可带）

1. | design.md §0 | 总纲缺「状态/文档清单」元信息行（iteration-design §2.1 要求 §0 含状态位草案→对抗审中→定稿；现仅 README 有进度）。建议 §0 补状态行。
2. | landing.md 3.3 清单末行 | 「归入在册晶矿/奖励相关篇**或新建**」= 酌情表述（规范 §5 规则2 卡点：定稿禁「酌情」）。建议定死归哪篇（研究档现有晶矿相关记载散在 screen_flow_timing.md/economy.md，建议明确落点）。
3. | landing.md 3.1 | 判据/清单未含 `_write_logic_frame` docstring（L2963-2965「board 恒走 write_logic(logic)，**不随行域随机态扩散**」）与 `_resync_board_delta` docstring 的同步修订——与改动#2 正面矛盾，漏改即留代码注释与行为打架。文件面已覆盖，判据补一句即可。
4. | design.md §0.1 | 假设档披露键未给「在册落点」（B 类候实机数据惯例有落点先例，如 `cw_sim_actions.py` L92 `NODE_XP_PENDING_U17`）；建议写明键落哪份研究档/披露表。

---

## 通过面（零发现声明）

- **核一锚点核对**：`_merge_bench`、`_write_logic_frame`、`_resync_board_delta`、`any_logic_rand`（新建，基座确无）、`write_logic_rand`、`logic_rand_fields`、`REFRESH_PROB`、`chars_by_cost`、`stream_rng`、`apply_player_action`、`effective_deal_probs`、`cw_equipment_data` category=简易（8 件）、`snapshot_copy`、`bench_place`、`OreSight`、`_executed_gold_delta` ClickSpheres 支（prep_actions.py L519/542）、`logic-updates/collect-ore.md`、fields.md §2.1-§2.5、fields.md §4.2、action-logic-state.md §1.1/§1.2、game_state/README.md §3.1、`test_cw_shop_projection_logic`（sr-od-test 实存）、基座 commit `d24585b7d`（git log 实存）——全部存在，无死锚。
- **基座行为核对**：observe() 等值覆盖零行、logic_rand 差异落 `logic_rand_outcome` 不进三分流（cw_game_state.py L2681-2689）与设计 §2.1 一致；`_MISMATCH_SUPPRESS_PREFIXES` 实存。
- **核二结构**：landing 三阶段七件齐、固定末阶段+正本清单在位、README 合模板、无过程叙事措辞。
- **核三治本**：归层语义层成立（两态制无随机落点，症状描述与代码实证一致）；§2 修根（采样语义+污染传递+上报函数单一源）；「逐动作迁移后续批」是范式化声明而非同族逐件症状补丁，架构级处理得当。
- **标记集自洽**（单 reward 前提下）：三分支对五域+board 的覆盖经逐格走查自洽（角色分支行域由步 3c+/步 4 补全）；拒分支先于 spheres 摘除、全分支一致。

---

## 复审轮（修订 commit bc22d297b 后）

### 复审结论：**收敛（可定稿）**

上轮 blocker×4 / major×3 / minor×4 全部实质解决（非文字绕过），逐条核验如下；修订引入的新发现均为 minor（3 条），不阻定稿。

### ① 上轮发现逐条核销

| 编号 | 核验 | 依据 |
|---|---|---|
| B1 | ✅ 已解决。§0 裁决2 增「在册冲突调和」段：三处记载差异逐一盘点（screen_flow_timing #16 三形态实证一致 / fields §4.2 箱 / wandi 稀有物），v0 有意取三选一并降级为「临时建模口径」（非核实事实），容错论证成立——错形态时被标记域（含「值不变」标记域）与真值观察差异均出 `logic_rand_outcome` 行且观察采新纠偏（cw_game_state.py L2681-2689 机制实证支持），席满让路门+观察回补承担代价引在册裁定；校准回路（常量面 + `logic_rand_outcome` 数据源）+ 新建 `research/sphere_rewards.md` 记录冲突与证据分级，知识归位合规。 | design §0 裁决2 / §2.3；landing 清单末行 |
| B2 | ✅ 已解决。§2.4「多点载荷语义」定义到可实施：逐点顺序推演、每点独立守卫/roll/写行、evidence 点序 `#ore<k>`、席满累计判（含前点角色耗位）该点跳过留 spheres、后续点继续判；引在册裁定佐证。 | design §2.4 |
| B3 | ✅ 已解决（余一处误名，见新 minor R1）。§2.5 重写为炉先例旁路直调：引擎前置分派拦截、`eng.ore_uses`（`furnace_uses` 同型实证存在）、拒分支不耗序（与 `_apply_furnace` L418-425 先判后计次序一致）、apply_player_action 主表不动（实证其确无 CollectOre 分支，主表零改动正确）。 | design §2.5；cw_sim_engine.py L407-426 |
| B4 | ✅ 已解决。流键 `M1x/ore/{uses}`，uses = 局内点矿动作单调序 1 基引擎计数，满足流键硬约束（模块号+局内坐标），与 `M10/炉/{uses}` 同型；批内同一 rng 实例顺序推进、跨批坐标隔离，语义完备。 | design §0 裁决7 / §2.3 / §2.5 |
| M1 | ✅ 已解决。§2.2 #1 + §2.4 步 3c+ 明定「每级合并后每个受该级影响的域各落一行（整表值），双域变更两行同号」，board 逐级派生行申报为预期流水；landing 3.1 判据含双域两行行为锁。 | design §2.2/§2.4；landing 3.1 |
| M2 | ✅ 已解决。§2.4「None 域边界」：None 跳写不标记、抽中域 None 跳采样写、bench 未观察整批拒 `'bench_unobserved'`；board 无基座跳过引既有门（L2800-2802 实证）。 | design §2.4 |
| M3 | ✅ 已解决。正本清单补 fields.md §4.2 ClickSpheres 与 action-logic-state.md §3.6 两行，改写口径明示。 | landing 正本清单 |
| minor×4 | ✅ 全部解决：§0 元信息（目标/状态/文档清单）补齐（design L3）；game doc 落点定死新建 `research/sphere_rewards.md`；landing 3.1 判据补 `_write_logic_frame`/`_resync_board_delta` docstring 同步；披露键落点 = `ORE_ASSUMPTION_KEYS`（§0.1 末行 + landing 3.2 判据键名一致性锁）。 | design L3/§0.1；landing 3.1/3.2/清单 |

### ② 修订引入的新主张攻击

- **逐点推演 × spheres 按点摘除**：自洽。「载荷无交集整批拒」保留现行为（全批零交集才拒），部分交集中不匹配点自然零摘除，与逐点摘除不冲突；开成点即时摘（logic 确定面）、席满点留 spheres 与在册回补裁定一致。动作级混合批出参口径见 R2（minor）。
- **双域合并行 × board 逐级行流水**：自洽。行域写触发 `_resync_board_delta`、bench 写不触发（L2971-2973 仅 front_row/back_row），逐级 board 派生行已申报预期；evidence `proj_ore_merge#<级>#ore<k>` 与 landing 判据词表一致。
- **sim 旁路直调 sig**：语义选择无缺口但草图误名，见 R1（minor）。
- **`eng.ore_uses` 字段**：`_Eng` 新字段、`furnace_uses` 同型先例实证（cw_sim_engine.py L425），可实施。

### ③ 全量同步复查（design ↔ landing ↔ README）

- landing 3.2 文件面已由 `cw_sim_actions.py` 改为 `cw_sim_engine.py`，与 §2.5 一致 ✓；3.2 判据（多点锁/席满即止锁/双域行/None 边界/sim 接线锁/拒分支先于任何写）与 design §2.4/§2.5 逐条对得上 ✓；README 进度（对抗审中/0/3）仍准确 ✓；上轮核过的全部锚无回归，修订新增锚（`SPHERE_CLICK_BATCH_MAX_K`、`_apply_furnace`、`furnace_uses`、screen_flow_timing #16、`ORE_ASSUMPTION_KEYS`）全部实存 ✓。

### 复审新发现（均 minor，定稿可带）

1. **R1** | design §2.5 代码草图 | sig 占位 `actor='SimEngineP1'` 与代码实况不符：logic_action 族的 sim 规范 actor = `SIM_ENGINE_ACTOR = 'SimEngineV2'`（`cw_sim_base.py` L22 / `logic_sig()` L40-42，`apply_player_action` L111 即用它）；`'SimEngineP1'` 是注册的 **obs 族**外部事件写点 actor（`cw_game_state.py` L410），不是本分派应引用的名字。语义无选择缺口（canonical = `logic_sig(group_id=...)` 与 L111 同型），但照抄草图会造出带错误 actor 的手写 ChannelSig。建议定稿时把占位改为「`logic_sig(group_id=f'act:sim@{node_tag}')`，与 apply_player_action 同型」并删误名。
2. **R2** | design §2.4 多点载荷语义 | 混合批的动作级 `LogicOutcome` 出参未列：部分点开成、部分点席满跳过时 applied/reason 词表（全部点跳过时 applied=False？部分开成 True 带何 reason？）未定义。消费面（prep_actions 分发/发射位 H-3 进度判据以 spheres 变化为准）风险低，建议补一行出参口径。
3. **R3** | design §2.4 末段「没开的点留在载荷」 | 措辞误向：不摘除 = 该坐标留在 **spheres 字段值**里（前文「留在 spheres」正确，此处「留在载荷」指向动作参数，易误导实现者去改载荷）。建议改字。

**定稿判定**：R1-R3 均为实现者可零设计成本自行纠正、或一行改字的级别，不构成「无需再设计」违规；上轮全部 blocker/major 实质关闭 → **收敛，可定稿**。
