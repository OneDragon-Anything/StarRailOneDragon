# CwActionToolUseOp（工具原子七类）参数面迁移设计稿（r1）

> 迭代：CW 动作 op 迁移流水线 · 设计角色产出（工具 op 批）。
> 上批 = WearEquip 穿装参数面迁移（changes/wear-equip-param-surface/design.md，已落地）。本批 = 工具原子族（`cw_tool_use_action.py`，注册表七行同指一 op）全牵涉面迁移。
> 冻结宪法（用户裁定，穿装批成文）：①动作 op 执行路径零 gs 依赖；②参数面三分法；③名称字段 = 语义参数（可选，不参与校验与定位，仅日志）——**记账面亦零消费**；④坐标新鲜度纪律归调用方；⑤参数 dataclass 统一补 `from_dict`；⑥gs 给实体记录坐标（坐标伴随域）；⑦每个 op 一个迭代，牵涉面一次改净。
> **记账路径总契约（用户裁定，正文 = `skills/sr-od-dev-currency-war/references/flow/action-op.md`「记账路径总契约」条款）全动作 op 迁移继承，不再逐个报批；本批 = 第二个适用者**，逐 op 差异在本文 §0.2 申报。

## 0. 总契约适用与本批逐 op 差异申报

### 0.1 契约继承

记账路径总契约三条（反查时序不变式 / 陈旧窗口禁消费 / 反查唯一性前提与拒单处置）原样适用于工具域，随 op docstring 双落点（§8.1）。语义落点：

- 工具动作 op 上报它实际动过的坐标——**源坐标 = 工具 icon 格心**（七类通用）；equip 模式**目标坐标 = 目标装备 icon 格心**（第二反查键）。kernel 记账层用坐标伴随域 `gs.owned_equip_xy` 反查出具体内容再记账；名称从「记账键」降级为「反查产物」。
- 坐标伴随域字段 = `gs.owned_equip_xy`，与穿装批**同一字段、同一写入方**（观察装配点 `cw_screen_prep.py:416-418` 整表覆盖 + sim 占位同步 `cw_sim_backend.py:5199-5246`）——工具件住 owned 装备网格（`gs.equips`，工具消耗移除记账载体 = `equips` 合并单笔写，`cw_action_report/tool_use.py:12-14`），观察链 `read_equips` 对网格内全部注册条目产出坐标（`cw_observe_full.py:184-189` 双键派生），工具名条目天然在表（假设申报与验收见 §9 条 1）。

### 0.2 本批逐 op 差异（总契约条款「逐 op 差异随各 op 迁移申报」的落点）

| 差异点 | 穿装批形态 | 本批工具域形态 |
|---|---|---|
| 反查键数量 | 单键（src_cx/src_cy） | **双键**：源工具坐标（七类通用）+ equip 模式目标件坐标（冶金炉/特权赋予卡两类的 equip 分支） |
| 反查目标域 | 件名（owned 装备条目） | 同域（工具名与目标件名都是 owned 装备条目；反查函数共用） |
| 反查函数归属 | `wear_equip.py` 模块私有 `_resolve_item_by_xy`（`wear_equip.py:233-245`） | **提升为 kernel 公共口**（第二消费者出现，单源上移；§1.3） |
| 拒单码 | `wear_item_xy_unresolved` | `tool_xy_unresolved`（源键反查不到）+ `tool_target_xy_unresolved`（equip 目标键反查不到） |
| 目标端记账定位 | row/slot 纯槽位反查（`_locate_unit`） | 同构复用：`tool_use.py::_resolve_row_unit`（`tool_use.py:133-144`）已为纯槽位定位，形态保留 |
| 陈旧窗口禁消费载体 | `StrategyState.cw4_wear_pending`（穿戴/重观察交替） | **载体泛化并更名 `cw4_equip_xy_pending`**（§2 核心裁决） |

## 1. 新参数面定稿

### 1.1 参数面三分法：逐工具合法目标域与守卫形态

源端统一：七类全部新增 `tool_cx: int`、`tool_cy: int`（必填位置参数）——工具 icon 格心（1080p），兼源端记账反查键。发出面从坐标伴随域按工具名取（§4.5 helper）；MCP 直调按当帧 `extras.owned_equips` 元素 cx/cy 传。

目标端两类语义（设计问题①的裁决）：

| 工具（词表类） | target_kind | equip 目标域（装备→装备） | char 目标域（拖到角色槽） |
|---|---|---|---|
| 冶金炉 `CwActionFurnaceUseParam` | 双模 | owned 件格心（tgt_cx/tgt_cy，≠源格） | row/slot + back_slot_count |
| 特权赋予卡 `CwActionPrivilegeCardUseParam` | 双模 | 同上（char 分支上报侧维持 fail-closed 零写，`tool_use.py:372-380` 不变） | 同上 |
| 拆装扳手 `CwActionWrenchUseParam` | char 单模 | — | row/slot + back_slot_count |
| 精密拆装扳手 `CwActionPrecisionWrenchUseParam` | char 单模 | — | 同上 |
| 员工投影仪 `CwActionStaffProjectorUseParam` | char 单模 | — | 同上 |
| 完美投影仪 `CwActionPerfectProjectorUseParam` | char 单模 | — | 同上 |
| 好运令牌 `CwActionLuckyTokenUseParam` | char 单模 | — | 同上（判据面现役 fail-closed 永不准入 `cw_equip_env.py:601-603`，参数面保持完备供直调与判据批扩容） |

字段集定稿（`kernel/cw_vocab.py` 七类重写，L558-659 现值）：

- **双模类**（冶金炉/特权赋予卡）：`target_kind: str`（'equip'|'char'，值域封闭）、`tool_cx: int`、`tool_cy: int`（必填位置参数）；`tgt_cx: int = 0`、`tgt_cy: int = 0`（equip 模式目标件格心；**0 = 未传哨兵**，1080p 装备区真实坐标恒非零、sim 占位为负值哨兵（`cw_sim_backend.py:5240`），0 只表达缺省——守卫见 §1.2）、`row: str = ''`、`slot: int = 0`、`back_slot_count: int = 6`（char 模式目标，front 行 back_slot_count 忽略——与 `CwActionWearEquipParam.back_slot_count`（`cw_vocab.py:542`）同口径）；`item_name: str = ''`（equip 模式目标件名；现形态 `cw_vocab.py:571/592` 已带缺省、本就可选——本批改造 = 加 tgt 坐标键后，item_name 定格纯日志语义位：现役 equip 分支在库检查（`tool_use.py:233/390`）退役后其非日志消费归零）；`char_name: str = ''`（char 模式目标角色名，可选语义参数，新增）；`route_tag` 保留（kw_only + `action_key_exclude`，`cw_vocab.py:574-575` 全族契约不变）。
- **char 单模类**（扳手/精密扳手/两投影仪/令牌）：`tool_cx: int`、`tool_cy: int`、`row: str`、`slot: int`（必填位置参数）；`back_slot_count: int = 6`、`char_name: str = ''`（可选语义参数，新增）、`route_tag` 保留。

[索引/坐标定义]（逐字段注释三要素，随类 docstring 落）：`tool_cx/tool_cy` 坐标系 = 1080p 全局像素 owned 工具条目格心，取值时机 = 发出面决策帧坐标伴随域快照；`tgt_cx/tgt_cy` 同域 owned 目标件格心；`row/slot` = 画面物理排槽位（词表通用声明 `cw_vocab.py:11-14`），生成期快照，记账面兼目标定位键（`_resolve_row_unit` 按 row/slot 反查槽现任单位）；`back_slot_count` = 后排槽位画面物理总数 n（值域 6-9 = `obs.cw_back_layout._LAYOUT_PREFIX` 键域）。

`from_dict`（冻结原则⑤）：新增模块级共享实现 `cw_vocab.action_param_from_dict(cls, d)`（形态单一源 = `cw_replay_reader.from_dict` 同构，正文同 `CwActionWearEquipParam.from_dict`（`cw_vocab.py:548-555`）：只取已声明字段、未知键忽略、缺字段落默认值），七类 `from_dict` 类方法各一行委托之。**穿装批 `CwActionWearEquipParam.from_dict` 内联体本批不动**（他批交付物；收敛归后续 sweep，申报行见 §11）。

run_operation args 示例（冶金炉 equip 模式）：

```json
{"target_kind": "equip", "tool_cx": 1660, "tool_cy": 120,
 "tgt_cx": 1740, "tgt_cy": 210, "item_name": "量产型装甲"}
```

### 1.2 守卫断言（op 内，参数语义唯一所有者 = op，flow/action-op.md §1 校验落点契约）

全部 `raise AssertionError` 响亮暴露，禁兜底坐标/禁负下标回环：

1. `target_kind ∉ {'equip','char'}` → 断言（双模类；现状保留，`cw_tool_use_action.py:111-114`）。
2. equip 模式：`tgt_cx == 0 or tgt_cy == 0` → 断言「equip 分支缺目标件坐标」（换掉现状的件名空检 `cw_tool_use_action.py:115-118`）；`(tgt_cx, tgt_cy) == (tool_cx, tool_cy)` → 断言「源与目标同格」（同格自拖非法；sim 占位序号唯一化保证生产路径恒不触发）。
3. char 模式：`row ∉ {'front','back'}` → 断言（现状保留，`cw_tool_use_action.py:122-125/135-138`）；slot 越界 `not (1 <= slot <= len(pts))` → 断言（拖点表现读，`cw_tool_use_action.py:126-131/139-144` 现状守卫**退役**——其表长取自 executor 基线点表 `_back_pts`（只匹配 `后排-1..6` 前缀，`prep_actions.py:312`），后排 7/9 槽的 char 模式工具今日必拒 = 潜在 bug；迁移后按 `back_slot_count` 档位表取长，行为修复申报 §9 条 6）；`row == 'back' 且 back_slot_count ∉ _layout_prefixes()` → 断言（布局档键域外禁静默按 6 兜底，穿装批同款 `cw_wear_equip_action.py:127-131`）。

### 1.3 反查函数提升（第二消费者出现，单源上移）

`_resolve_item_by_xy`（`wear_equip.py:233-245`，穿装批私有件）本批**上移为 `kernel/cw_game_state.py::resolve_item_by_xy` 公共函数**（落点 = `owned_equip_xy` 字段定义旁，`cw_game_state.py:3179` 邻位；字段语义与反查契约同文件承载最紧内聚；kernel 零 app import 契约不受影响）。实现逐字继承，docstring 补双消费方声明（wear_equip / tool_use）。`wear_equip.py` 私有副本删除、调用点（`wear_equip.py:331`）改引公共口——同批一次改净（原则⑦），行为零变化。

### 1.4 词表模块头例外声明收窄

`cw_vocab.py:11-14` 与 `cw_vocab.py:141-145` 两处「坐标参数化机械动作（工具原子类…）row/slot = 画面物理排槽位」例外声明更新：工具原子类升级为「动态坐标显式传（tool_cx/tool_cy 源；equip 模式另带 tgt_cx/tgt_cy）+ row/slot 半固定（char 模式 + back_slot_count）」形态；例外家族收窄为开件三类（OpenBox/OpenTome/OpenBookcard）。`prep_actions.py:20-25` 模块头同款声明同步。

## 2. 交替机制延伸（本批核心裁决）

### 2.1 问题

工具使用 aftermath 含 owned 网格变异：冶金炉消耗工具 ∧ 目标件（equip 模式）或消耗工具 ∧ 全部穿戴件（char 模式，`tool_use.py:250-254/319-324`）、特权卡消耗工具 ∧ 原地变换（`tool_use.py:401-403`）、扳手消耗工具 ∧ 追加穿戴件（`tool_use.py:438-441`）、投影仪消耗工具（`tool_use.py:505-506`）——库存增删引发网格 reflow 移动 owned 条目格位（`cw_tool_use_action.py:154-157` 既有建档注释「合成消耗/reflow,下帧重派」即此）。**穿装批的 `cw4_wear_pending` 交替只看穿装计划**（`mandate_state.py:207-216` 语义注释限定穿戴域；发出点 = mandate M7 `mandate.py:1042-1056` 与 entry 第 7 步 `entry.py:1148-1155` 两处，均只拦穿戴）。工具原子发出后（现役发出点 = entry 第 7 步工具段 `entry.py:1201-1242`，tag `m7_5_tool_consume`），下一帧若有第二次坐标消费（再发一个工具原子，或穿戴步续穿 `entry.py:1157-1159`），消费的是 reflow 前的陈旧伴随域——实机盲拖错格，记账面反查产物跟着错（错账）。参数面迁移后工具原子自己就消费伴随域坐标（源 + equip 目标双键），首发即受契约约束，更不容陈旧。

### 2.2 裁决：标志机制扩展（单标志单域），否决「工具域另立标志」

**裁定：`cw4_wear_pending` 泛化为装备网格伴随域新鲜度标志，更名 `cw4_equip_xy_pending`；穿装与工具原子两类发出都置位，共用同一重观察帧。**

论证（根源两问：根 = 「坐标伴随域 owned_equip_xy 可能陈旧」这一**单一字段**的新鲜度不变式被两类动作的 aftermath 共同威胁；修单标志 = 修根——标志的语义本就该绑在被保护物（伴随域字段）上，而非绑在先到的那个动作族上）：

1. **不变式载体唯一**：被保护物是 `owned_equip_xy` 一个字段；两个标志保护一个字段 = 把一条不变式拆成两份载体，状态空间出现「双置位」组合（两标志都置 → 一帧 Obs 清谁？清一个留一个 = 窗口仍开；清两个 = 与单标志一字不差而多付一个字段）——另立标志是症状级拆分，无任何失效形态被它多覆盖。
2. **成本同形**：单动作收敛形态下（`bridge.py:260-262` 只发 `actions[0]`、余参弃、下帧重算），每帧至多消费一次伴随域；置位帧只产 Obs（无第二次消费）——两方案的重观察帧数逐位相同，扩展不增帧。
3. **同构先例**：部署扫描 `pending_reobserve` 读后清形态（`mandate_state.py:210-211` 引为先例）本就是「域可能陈旧 → 下帧重观察」的域绑定型标志；本裁决 = 同一形态多一个置位端，机制零新增。
4. **fail-safe 方向不变**：标志残留 → 下帧多发一帧无害重观察 → 清位续发（`mandate_state.py:211-213` 既有申报语义照抄，措辞泛化）。

更名理由：`cw4_wear_pending` 字面 = 穿装待重观察，泛化后名不符实；`cw4_equip_xy_pending` 绑定被保护字段名自释义。改动面 = `mandate_state.py:216` 字段 + `mandate.py:1042/1048/1056` 三处 + `entry.py:1148/1153/1161` 三处 + 测试 `test_step6_equip_tools.py:74/80/94/108` 四处，全部本批内（无跨批消费者，grep 全仓 7 处源码引用 + 4 处测试引用已核）。

### 2.3 机制设计（发出点逐处）

- **entry 第 7 步（唯一工具发出点 + 穿装发出点之一，`entry.py:1116-1243`）**：标志检查**上提至步首**。现状漏洞 = flag 检查缩在穿戴门内层（`entry.py:1138-1148`）而工具段在门外（`entry.py:1175`），按「标志置位 ∧ 本帧穿戴门过不过」拆两子形态：**门外子形态**（本帧无穿戴候选，穿戴门整体不进）= 标志无人消费、工具段带陈旧伴随域坐标直发——盲拖 + 错账实锤；**门内子形态**（本帧有穿戴候选）= Obs 占住首位、清标志后落入工具段照构造——陈旧坐标工具原子被 Obs 挡住丢弃 = 白构造/白计数 + 多一帧冗余 Obs 形态（不炸账，纯浪费；该子形态的盲拖链仅被「Obs 排首位」这一列表序事实挡住，非结构保证，序动即实链）。上提后置位帧：清标志 → 产 `Emitted(CwActionObsParam(scope='in_place'), True, 'm7_equip_reobserve')` → **提前 return**（穿戴与工具两段全跳过，置位帧零参数构造 = 「窗口内无第二次消费」的强保证，两子形态一并封死；现状不 early-return 的形态随批收紧，行为申报 §9 条 7）。tag 字符串 `m7_equip_reobserve` 保留不改（遥测分键零 churn；语义注释补「穿装与工具 aftermath 共用」）。
- **entry 工具段置位**：工具原子参数列表非空 → `st.cw4_equip_xy_pending = True`（与穿戴段 `entry.py:1160-1161` 同形）。
- **mandate M7（穿装发出点之一，`mandate.py:1031-1068`）**：仅字段更名，结构零改动——该路径不产工具原子（工具发出点已物理移出 mandate，`mandate.py:1070-1073`），其标志检查在穿戴门内的形态无漏洞（门不进 = 不产穿装参数 = 零坐标消费，不变式不破；标志留置到下一帧 entry 第 7 步上提检查位自然承接 Obs）。
- **覆盖域裁定**：六个可发出工具类全部置位（冶金炉/特权卡/扳手/精密扳手/两投影仪）。好运令牌永不上桌（判据面 fail-closed `cw_equip_env.py:601-603`），无置位面。逐工具细粒度白名单（「该类 aftermath 不 reflow 故免观察」）= 无实机背书的优化，弃——uniform 置位方向 fail-safe（多余帧 = 无害重观察），各类 aftermath 的 reflow 行为差异留实机采证后再裁。
- **获得类动作不在本批扩展**（采晶矿/开箱/补给获得件 = 穿装批 A1 假设辖域，`wear-equip-param-surface/design.md` §1.5 A1 + §7 条 9 回退方案已登记）：若 A1 实测不成立，回退 = 获得类动作帧也置本标志——单标志多一个置位端，机制零新增。本批只把工具 aftermath 纳入（按 op 切纪律）。

### 2.4 计数与遥测申报

- 新增键：`m7_5_tool_xy_pending`（值 = 本帧被跳过的工具原子数，坐标缺席计数，帧粒度按量累加）与 `m7_5_tool_xy_all_pending`（本帧有可用工具原子但参数全缺席的自愈重派帧，+1/帧）——键登记单一源 = `mandate.py` 模块 docstring 计数键清单（实施角色按现行登记位落）。
- 既有键零退役；`m7_5_evaluated`（`entry.py:1183`）口径变化：置位帧提前 return 不再递增（评估计数从「每决策帧一次」变「非重观察帧一次」）——判读基线申报 §9 条 7。
- 发出 tag `m7_5_tool_consume` 保留（`entry.py:1242`）。

## 3. 记账路径重写（`kernel/cw_action_report/tool_use.py`）

### 3.1 现状名称消费清单（设计问题②答案）与改造表

现役上报层消费的名称字段逐处核验（行号为 HEAD 现值）：

| 上报函数 | 现名称消费 | 处置 |
|---|---|---|
| `_furnace_equip_branch`（`tool_use.py:222-262`） | `param.item_name`：在库检查（L233）、采样池键（L241）、移除（L253）、evidence（L257）、后果采证（L258）、reason（L262） | **全改反查产物** `item = resolve_item_by_xy(gs, param.tgt_cx, param.tgt_cy)`：L233 在库检查删除（反查命中即视为在库，同穿装批 `owned.remove` 自然异常防线，见 §3.3）；L241/253/257/258/262 用 `item`；工具端移除 `_remove_one(new_inv, '冶金炉')`（L252）改 `item_tool = resolve_item_by_xy(gs, param.tool_cx, param.tool_cy)` 后严格移除（§3.3） |
| `_furnace_char_branch`（`tool_use.py:265-337`） | 工具端字面 `'冶金炉'`（L320）；穿戴件名自 `unit.equips` 状态推导（L279，合法非参数名） | 工具端改 `resolve_item_by_xy(gs, param.tool_cx, param.tool_cy)` 严格移除；穿戴件名消费维持状态推导不动（宪法③管参数名，不管状态产物名） |
| `report_action_privilege_card_use_param`（`tool_use.py:357-408`） | `param.item_name`：在库检查（L390）、映射键（L398）、变换（L403）、evidence（L405）；工具端字面 `'特权赋予卡'`（L402） | 目标件全改反查产物（在库检查 L390 删除，变换 L403 前置 `inv.index(item)` 自然 ValueError 防静默空变换，§3.3）；工具端改反查严格移除 |
| `_wrench_report`（`tool_use.py:413-449`） | 工具端字面 `tool_name` 形参（L440 consume 移除；evidence L429/444） | 改 `resolve_item_by_xy(gs, param.tool_cx, param.tool_cy)`，按 consume 分支分裂：**consume=True（拆装扳手）**反查不到 = `tool_xy_unresolved` 拒单零写（工具消耗笔是反查产物辖域，总契约处置）；**consume=False（精密扳手）**反查仅作 evidence 归因、**反查不到不拒单**——equips 追加穿戴件与行域清空照写，evidence 注记 `tool_xy_unresolved` 形态（精密扳手无消耗笔可拒，拒单反而造成「物理卸装无账」——行域清空写不落、账实分裂靠 reconcile 兜底，且对照表未刷新前恒拒 = 语义倒退）；`param.row/slot` 槽位定位保留（`_resolve_row_unit` L419） |
| `_projector_report`（`tool_use.py:469-515`） | 工具端字面 `tool_name`（L506 consume 移除）；角色名自 `unit.char_id` 状态推导（L486，合法） | 工具端同扳手改反查严格移除；费用门/获得链不动 |
| `report_action_lucky_token_use_param`（`tool_use.py:534-546`） | 零写留存证据（L543 打印 row/slot） | 不变（永不发出，反查不适用） |

冶金炉与拆装扳手两问的直接回答：**两者的记账都能全改坐标反查产物**——冶金炉的两个消耗对象（工具 + 目标件）各有一个显式坐标反查键；拆装扳手的消耗对象（工具）有源坐标反查键、卸装对象（目标单位）由 row/slot 纯槽位反查（`_resolve_row_unit` 现形态即纯槽位定位，`tool_use.py:133-144`，与穿装批 `_locate_unit` 收缩后同构 `wear_equip.py:248-271`），卸下的穿戴件名自 `unit.equips` 状态推导。七类改造后 `param.item_name` 在 tool_use.py **零残留**（唯 equip 分支 evidence/reason 可选携带 `param.item_name` 日志尾注——不加，保持零消费面干净；日志语义由 op round detail 承载）。

### 3.2 拒单码词表（登记面 = 上报拒绝语义词表 + fields.md 回执契约节，新码先登记再使用）

| 码 | 处置 |
|---|---|
| `tool_xy_unresolved` | **新增**（源工具坐标反查不到：坐标不在表/伴随域 None——拒单辖域 = 工具消耗笔（冶金炉/特权卡/投影仪/扳手 consume=True），拒单零写 + 留存证据，处置 = 交还框架决策循环刷新对照表重派，禁补拖；**精密扳手 consume=False 例外** = 不拒单、evidence 注记本码形态（§3.1 豁免——无消耗笔可拒，拒单 = 物理卸装无账）） |
| `tool_target_xy_unresolved` | **新增**（equip 模式目标件坐标反查不到——冶金炉/特权卡 equip 分支） |
| `furnace_target_missing`（`tool_use.py:240`） | **退役**（名称在库检查删除，反查路径取代） |
| `privilege_target_missing`（`tool_use.py:397`） | **退役**（同上） |
| `tool_target_unit_missing`（`tool_use.py:71/278/427/485`） | **保留升格**：applied=True + 缺陷留存 → **applied=False 拒单**（槽位解析失败 = 陈旧提案；与穿装批 `wear_target_unit_missing` 拒单同形统一 `wear_equip.py:339-342`——同一失效形态两族两处置 = 分裂，统一为拒单；row/slot 越界语义不变） |
| `tool_privilege_worn_unsupported` / `furnace_equips_unobserved` 族 / `projector_cost_gate` / `tool_bridge_zero_write` 零写族 | **保留不变**（bug 面失败安全语义 = gain-chain §2.7 同款既有申报 `tool_use.py:30-32`，非总契约辖域；总契约管「反查不到」，不管「库存未观察/费用门」） |

`LogicOutcome` 出参语义申报：工具域从「恒 applied=True」（`tool_use.py:4-8` 无条件按成功写）**收窄**为「反查/槽位解析失败 = applied=False 拒单零写，其余分支维持 applied=True」——总契约拒单条款的直接落点；op 侧消费 outcome 的形态与穿装批 M-r3-1① 同构（§4.2）。

### 3.3 反查命中后的移除语义分裂（严格移除 vs 容错移除）

- **反查产物**（工具名、equip 目标件名）：**严格移除**（`list.remove` / 前置 `inv.index`）——反查命中但名单缺条目 = 禁消费窗口违反（契约③），以 Python 自然异常响亮暴露（零防御，穿装批同款 `wear_equip.py:365-367` + docstring L314-318）。现役容错 `_remove_one`（`tool_use.py:124-130`，不在 = 零移除返 False）对反查产物退役——容错语义是名称键时代的陈旧提案缓冲，反查键时代陈旧提案在反查处已拒单，命中后缺条目只剩窗口违反一种解释。
- **状态推导名**（冶金炉 char 分支的穿戴件，`tool_use.py:321-322`）：维持 `_remove_one` 容错——非反查产物，总契约不辖；其名单漂移属既有 bug 面（留存证据不停机语义不变），本批不动。**混合语义锁测**见 §7.2（防未来把两族语义搅浑）。

## 4. 牵涉面清单（逐文件；grep 全量已核）

> 路径根 = `src/sr_od/application/currency_war/`。

### 4.1 `kernel/cw_vocab.py` — 七类参数重写 + 共享 from_dict

- 重写七类（L558-659）为 §1.1 字段集；逐类 docstring 补三分法归属 + 索引/坐标定义注释三要素 + 三条契约申报摘要（形态照 `CwActionWearEquipParam` docstring `cw_vocab.py:504-537`）。
- 新增 `action_param_from_dict(cls, d)` 模块函数 + 七类 `from_dict` 委托（§1.1）。
- `CwAction` union（L992-994）、`CW_ACTION_TYPES`（L1010-1011）：类名不变零改动。
- 模块头例外声明两处收窄（§1.4）。

### 4.2 `operations/cw_op/cw_tool_use_action.py` — op 执行体重写

见 §5 执行语义。要点：守卫按 §1.2 重写；机械半自持（显式坐标起点/目标 + `row_drag_points` 静态解析 + `self.park_cursor`，剥 `ex._op`/`ex._ctx`/`ex._owned_grid_locate`/`ex._front_pts/_back_pts` 消费）；签名改 `env: PrepExecEnv | None = None`（穿装批同款 `cw_wear_equip_action.py:93-94`）；两处「owned 网格未定位」round_fail 通道删除（L147-150/153-157）；自上报消费 outcome，`applied=False` 时 detail 追加「记账拒单:<码>(拖拽已发生,账未落)」（穿装批 M-r3-1① 同构 `cw_wear_equip_action.py:156-170`）；docstring 按 §8.2 重写。`_TOOL_NAME_BY_CLASS`（L64-72）保留，职责收窄为 round detail 日志前缀（机械定位职责已随显式坐标消失）。

### 4.3 `operations/cw_op/cw_action_registry.py` — 零改动

import（L42-72/L150）与注册七行（L182-188）类名不变；组装签名兼容 env 缺省化。注册完备测试机械约束对象不变。

### 4.4 `kernel/cw_action_report/tool_use.py` — 记账路径重写（§3）

逐函数改造表 §3.1；拒绝码词表 §3.2；模块 docstring 拒绝语义段重写 + 记账路径总契约引用（「记账 = 坐标反查，反查函数 = kernel `resolve_item_by_xy` 公共口」）。

### 4.5 `kernel/cw_equip_env.py` — 发出面参数构造 helper

新增 `tool_use_params_of(gs, atoms) -> tuple[list[CwAction], int]`（atoms 元组 = `(tool_name, action_kind, target_name)`；action_kind 值域 = 现役两支 `'furnace_single'|'privilege_upgrade'`）：坐标伴随域 `gs.owned_equip_xy.value or {}` None/缺席守卫（同 `wear_param_steps_of` 的 `cw_equip_wear_plan.py:140` 形态）→ 逐原子取工具名坐标 + 目标名坐标（per-name 游标序贯消费，单动作收敛生产形态下游标退化为恒取首候选——先例申报同 `cw_equip_wear_plan.py:128-132`）→ 双坐标齐备才产原子（`CwActionFurnaceUseParam(target_kind='equip', ...)` / `CwActionPrivilegeCardUseParam`，item_name 填日志语义）→ 坐标缺席 = 该原子本帧不产（计数返回值；自愈通道 = 帧稳定截断 → Obs outer_loop 重观察后自然重派，同穿装批）。落点选 `cw_equip_env.py` = 工具判据/准入/通道语义单文件（模块 docstring L33-44 已自认工具执行批宿主），惰性 import cw_vocab（模块内 L563-570 惰性 import 先例同款）。**kernel 零 app import**（gs 形参 duck）。char 模式原子不经本 helper（判据面现役只产 equip 分支，`cw_equip_env.py:559-561`；char 模式构造面 = MCP 直调 + 判据批扩容时的直构）。

### 4.6 `strategies/impl/mandate_v1/entry.py` — 第 7 步改造（§2.3 落点）

- 标志检查上提步首 + 提前 return（L1130-1155 区重排）；字段更名三处（L1148/1153/1161）。
- 工具段（L1175-1243）：原子构造改 helper 调用（现 L1220-1241 的目标选择逻辑 `_rq_set`/`_priv_targets` 保留在 entry——判据语境属决策侧；helper 只管坐标），产参数列表 + `m7_5_tool_xy_pending`/`m7_5_tool_xy_all_pending` 计数 + 置标志；`m7_5_atomic_unmapped` 判定前移到 triples 收集段（L1227-1229 现值语义不变）。
- import 区补 `tool_use_params_of`。

### 4.7 `strategies/impl/mandate_v1/mandate.py` — 仅更名

L1042/1048/1056 字段更名；M7 块结构零改动（§2.3）；`_EQUIP_ATOM_TYPES`（L96-99）与组内序（L1093 `equips.sort`）类名不变零改动。

### 4.8 `strategies/impl/mandate_v1/mandate_state.py` — 载体字段泛化

`cw4_wear_pending` → `cw4_equip_xy_pending`（L216），字段注释块（L207-215）按 §2 裁决重写：语义 = 「owned 装备网格伴随域可能陈旧 → 下一决策帧产 Obs(in_place) 环内重观察后清位」；写入端 = 穿装发出点（mandate M7 / entry 第 7 步）+ 工具原子发出点（entry 第 7 步）；覆盖 aftermath = 穿装合成/reflow + 工具消耗/reflow（获得类 aftermath = A1 假设辖域另案）。

### 4.9 `kernel/cw_game_state.py` — `resolve_item_by_xy` 公共函数

新增于 `owned_equip_xy` 字段（L3179-3195）邻位（§1.3）；字段注释的消费面措辞同步（「发出面坐标源」扩为「穿装与工具原子（源键 + equip 目标键）」）。

### 4.10 `prep_actions.py` — 机械原语退役

- `_owned_grid_locate`（L449-470）随批退役删除：本批后全仓零消费者（工具 op 是现役唯一消费者 `cw_tool_use_action.py:146/153`，本批拔除；穿装批已清空其余消费）。模块头注释（L444-447）与 docstring 同步收口。
- `_PREP_RECEIPT_BLOCK_CODES` 三行退役（L100-105：'owned 网格未定位到工具'/'…目标件'/'…泛化行'）——两供给方（穿装批已退、本批退工具）清零，全仓零 round_fail 供给。
- `executor._front_pts/_back_pts`（L311-312）**保留**：本批后仍有 `cw_move_unit_action.py:67-77` 与 `cw_sell_deployed_action.py:68/81` 两消费者（拖拽交互类不同——角色拖动/卖出与「拖到角色卡」不同族，+21 拖点权威裁定不外溢，`prep_actions.py:164-168` 辖域声明不变）。`row_drag_points` docstring 中「待工具迁移批实机核对后统一按本式」承诺本批兑现：工具 char 模式拖点改走 `row_drag_points`（+21 权威派生式），docstring 该句更新为已统一。

### 4.11 `sim/cw_sim_backend.py` — 零改动（语义自洽结论见 §6）

占位同步函数（L5199-5246）与 advance 挂点（L2439）、序号字段（L1693）全部不动。

### 4.12 `data/cw_equipment_data.py` — 注释同步

L49-50「现役按名定位读仅剩工具原子族 `prep_actions._owned_grid_locate`,待迁移」过期化 → 改「按名定位读已随工具原子族坐标显式化退役；坐标伴随域 = gs.owned_equip_xy（观察装配点写入），发出面坐标源 + 记账面反查键（穿装与工具原子两类）」。

### 4.13 测试仓镜像测试 — 见 §7

### 4.14 文档面 — 见 §8

## 5. op 执行语义

### 5.1 迁移后执行流（op 纯机械化）

1. 守卫断言（§1.2）。
2. 拖点静态解析：equip 模式 `target = Point(int(param.tgt_cx), int(param.tgt_cy))`；char 模式 `prefix = '前排' if row == 'front' else _layout_prefixes()[back_slot_count]`，`pts = row_drag_points(self.ctx, prefix)`，`target = pts[slot - 1]`。
3. sim 分支：`mechanical_io_allowed()` 为假 → 机械段静默跳过（现状保留 `cw_tool_use_action.py:145/168-174`；sim 占位坐标不被机械消费，反查记账照走，§6）。
4. 实机机械段：`start = Point(int(param.tool_cx), int(param.tool_cy))`；`mouse_move(start)` 防吞点击 → `PREP_DRAG_SETTLE_WAIT_S` 固定等待 → `drag_to(start, end, hold_time=0.5, duration=1.5)` → 1.5s 固定等待。**拖拽链统一申报（有意行为变化）**：现状工具链 = mouse_move → 0.2s → drag(hold 0.5, **duration 1.2**)（`cw_tool_use_action.py:163-167`），与穿装批统一后的链（`cw_wear_equip_action.py:145-149`，duration 1.5 + settle 后置）不同参数不同序——同为「库存网格 icon → 目标」拖拽族，统一按穿装批权威链（D-36 校准 + 时序简化申报继承）；风险与验收 §9 条 5。
5. `self.park_cursor(after_wait=0.1)`。
6. 自上报：`gs = game_state_from_ctx(self.ctx)`；`outcome = self._REPORT_BY_CLASS[type(action)](gs, action, ChannelSig(...))`——分派表形态保留（L76-84），签名不变；`gs is None` = 无处记账跳过（outcome=None，detail 不加拒单段）；`outcome.applied=False` 时 detail 追加拒单事实（§4.2）。
7. round 结果：恒 `round_success(detail)`（机械成功语义——拖拽已发生；两处 round_fail 通道消失，`_PREP_RECEIPT_BLOCK_CODES` 三行随之退役 §4.10）。detail 含 `item_name/char_name` 与目标描述（名称唯一机械面消费 = 日志）。

### 5.2 决策侧参数现算契约适用申报

工具发出点（entry 第 7 步）= 单动作决策环辖域（同帧 decide → emit → op 执行 → 上报，`flow/action-op.md` §1 现算契约同款）；helper 坐标快照与上报反查消费同帧同一状态容器——坏参数只能是决策逻辑 bug，自然异常即正确处置。边界载体无新增（战斗链批量发射例外不涉工具）。

## 6. sim 形态自洽结论（设计问题④）

**结论：现有哨兵方案对工具域自洽，零 sim 改动。**[跨批前提申报] 本节全部论证以穿装批终审 F1 返修落地为前提——`_sync_owned_equip_xy_placeholders` None 分支引导初始化 `{}`（占位同步自身 = 环境快照首写端，`cw_sim_backend.py:5224-5226`；主仓 commit `57190272c` 已落地）；该返修未落地前伴随域恒 None → 工具域发出面 helper 恒全跳过（自愈通道兜底不炸），sim 论证整体不生效但无错账面。逐语义核验：

1. **占位坐标可反查**：sim 占位 = `(-1000-k, -1000)` 界外哨兵（`cw_sim_backend.py:5240`），`resolve_item_by_xy` 按精确 (int,int) 匹配，占位命中正常返回名——机械段静默跳过不消费坐标，记账全链通（穿装批已申报语义 §2.13 复用）。
2. **唯一性前提保持**：哨兵序号局内只增不减（L1693/5238-5239），坐标↔条目一一对应在占位路径恒成立；源键 ≠ 目标键由序号唯一化保证（同格双键守卫 §1.2-2 在 sim 生产路径不可触发）。
3. **合成消耗占位件**：冶金炉变异后 owned 净变（消耗 2 追加 1），占位同步按计数差 append（L5235-5241）在下一 advance 步界补新件占位；被消耗名的**陈旧占位残留**（同步只增不删）语义 benign——伴随域以名为键，残留条目反查恒返回该名，不污染他名；发出面按名取坐标，残留只在「该名重新入库」时被复用，此时名单确含该名，`owned.remove` 类严格移除正常落账。
4. **卸装占位件**：扳手/炉 char 分支卸下的穿戴件入 owned（逻辑写）→ 下一 advance 补占位——「获得」方向本就是同步函数的主路径。
5. **陈旧窗口**：sim 局 `Obs(in_place)` 重观察帧对伴随域退化为无害空帧（sim 观察链不产该键，穿装批 m-r3-6② 申报继承）；占位同步挂 advance 步界 = 事实上的伴随域增量刷新点，与交替标志叠加后窗口纪律在 sim 形态同样闭合（置位帧零消费 + advance 补占位）。
6. **直调路径**：MCP 直调传任意坐标 → 反查不到 = `tool_xy_unresolved` 拒单（round detail 感知），与实机同语义（精密扳手 consume=False 例外 = §3.1 注记形态不拒单）。

sim-design.md §6.5 邻域补申报行（§8.4）：工具原子消费本伴随域（源键 + equip 目标键），占位语义不变、零 sim 改动，陈旧占位残留按名键反查恒正确（哨兵唯一化）。

## 7. 测试设计（sr-od-test，按 §11.4 harness 规范；镜像路径，命名无批次号）

### 7.1 `test/sr_od/application/currency_war/kernel/cw_vocab/test_cw_vocab.py`（既有文件扩展）

- 七类 `from_dict`（经共享 `action_param_from_dict`）：全字段 dict 逐字段断言；最小 dict（双模类 3 项 / char 单模类 4 项必填）落全缺省（`tgt_cx=0/back_slot_count=6/item_name=''/char_name=''`）；未知键忽略。
- `action_key`：同坐标不同 `item_name` 产不同键；坐标不同产不同键；`route_tag` 不入键。

### 7.2 `test/sr_od/application/currency_war/kernel/cw_action_report/test_tool_use.py`（新建；本批测试重点）

- **反查命中（冶金炉 equip）**：种子伴随域（工具名 + 目标件名坐标）+ 名单 + rng 注入 → 上报 → 断言 owned 移除工具与目标件、追加采样替换件（同类别池）、evidence 含反查产物名。
- **反查不到**：源坐标不在表 / 伴随域 None → `tool_xy_unresolved` 拒单零写；目标坐标不在表 → `tool_target_xy_unresolved` 拒单零写。
- **名称零消费锁测（宪法③对齐）**：同一 (tool_cx, tool_cy, tgt_cx, tgt_cy) × `item_name` 取不同值（''/'任意名'/'与反查产物不同的名'）→ 记账结果逐位相同。
- **禁消费窗口违反锁测**：伴随域含坐标、名单缺该反查产物 → 断言严格移除抛 ValueError（锁 §3.3 严格语义，防未来静默守卫洗错账）。
- **混合语义锁测**：冶金炉 char 分支——工具端（反查产物）缺席名单 → ValueError；穿戴件端（状态推导名）缺席名单 → `_remove_one` 容错零移除不抛（锁 §3.3 分裂语义的两族边界）。
- **扳手族**：consume=True 移除反查产物 + 追加穿戴件 + 行域清空；consume=False 不移除；源坐标反查不到：拆装扳手 → `tool_xy_unresolved` 拒单零写；**精密扳手 → 不拒单**，equips 追加穿戴件与行域清空照写且 evidence 含 `tool_xy_unresolved` 形态注记（§3.1 豁免语义锁测）。
- **槽位定位**：row/slot 越界/空槽 → `tool_target_unit_missing` **applied=False** 拒单（升格锁测 §3.2）。
- **投影仪**：费用门超门 → 零写分支不变；反查命中 → 移除工具 + `gain_character` 走链。
- **特权卡**：equip 分支反查改造回归（变换同笔）；char 分支 fail-closed 不变；令牌零写不变。
- 既有 rand 采样/后果采证钩子回归：行为不变（仅键源换反查产物）。

### 7.3 `test/sr_od/application/currency_war/operations/cw_op/test_cw_tool_use_action.py`（新建；harness 剧本）

- 守卫断言：target_kind 非法 / equip 缺目标坐标 / 源目标同格 / row 非法 / slot 越界 / back_slot_count 域外 → AssertionError。
- 实机形态（fixture_controller，screen_info 真档案 → 期望值同源派生）：equip 模式拖拽记录 `start == (tool_cx, tool_cy)`、`end == (tgt_cx, tgt_cy)`；char 模式 `end == 前排-N rect 中心 x + y1+21`（+21 权威派生式锁测）。
- **后排 slot > 6 新行为**：`back_slot_count=7/8/9` + 对应档 area → 拖点落对应档（§1.2-3 行为修复锁测）。
- `env=None` 全链；sim 形态（机械零调用 + 自上报照走）；`with fast_sleep(): op.run()`。
- **round detail 拒单码**：种子使上报拒单 → 断言 round_success 且 detail 含「记账拒单:tool_xy_unresolved(拖拽已发生,账未落)」；正常帧 detail 不含拒单段。

### 7.4 `test/sr_od/application/currency_war/kernel/cw_equip_env/test_tool_use_params_of.py`（新建；纯函数直测）

- 双坐标齐备产原子（字段逐位断言）；工具名坐标缺席 / 目标名坐标缺席 → 跳过 + 计数；伴随域 None → 全跳过；游标序贯消费（helper 完备性面）；`gs.back_layout` 不入本 helper（equip 分支无 back_slot_count）。

### 7.5 `test/sr_od/application/currency_war/strategies/impl/mandate_v1/entry/test_step6_equip_tools.py`（既有文件扩展 + 更名同步）

- 字段更名四处（L74/80/94/108）机械同步。
- **工具置位交替**：判据打桩产可用工具原子 + 伴随域种子 → 帧1 产工具原子且置标志；帧2 产 `Obs(in_place)` 且读后清、**零工具参数构造**（提前 return 锁测）。
- **置位帧跳工具段**：置位帧即使判据面有可用工具也不产原子（窗口禁消费锁测）；`m7_5_evaluated` 置位帧不递增（口径变化锁测 §2.4）。
- 工具坐标缺席计数：`m7_5_tool_xy_pending` 按量 + `m7_5_tool_xy_all_pending` 帧。

### 7.6 `test/sr_od/application/currency_war/kernel/cw_action_report/test_wear_equip.py`（既有文件）

- `_resolve_item_by_xy` 上移后 import 面同步（行为零变化，既有反查测试全数照跑）。

### 7.7 `test_action_registry.py`（既有面）

零改动预期（七行类名不变）。

验收阶梯（skill §3）：L1 → L2（`test_action_registry` + `test_tool_use` 点名）→ L3 全量 commit 前。实机验收两序列：①冶金炉 equip 单发（观察 owned 少工具与目标件、多采样替换件，round detail 无拒单）；②「工具使用 → 后续穿装」序列验证交替标志（工具帧 → Obs 帧 → 穿装帧，伴随域刷新后穿装坐标落新格位）+ 工具 char 模式拖点（+21）实机落点核对（`row_drag_points` docstring 承诺的核对义务，§4.10）。

## 8. 文档与 skill

### 8.1 op docstring（MCP 使用说明契约；形态照穿装批 §6.1）

七类共用说明落 `CwActionToolUseOp` 类 docstring：坐标三分法（源 tool_cx/tool_cy 七类通用 + equip 目标 tgt_cx/tgt_cy / char row/slot + back_slot_count）；记账反查双键申报；三条契约摘要（含拒单处置：禁止补拖、交还框架决策循环、直调单件会话）；两类拒单码；守卫断言清单；run_operation args 示例（equip + char 各一）；后排档 back_slot_count 来源提示（extras deploy_cap−4）。

### 8.2 上报模块 docstring

`tool_use.py` 模块头拒绝语义段按 §3.2 词表重写 + 总契约引用（反查函数 = kernel `resolve_item_by_xy`）。

### 8.3 开发侧文档

- `docs/develop/sr_od/application/currency_war/game_state/fields.md`：§3.2.15c（L801-819）消费面①措辞扩展（工具原子源键 + equip 目标键）与新鲜度载体更名（`cw4_equip_xy_pending`，覆盖穿装与工具 aftermath）；回执契约节（L3259-3264 邻域）补工具拒绝码五行变更（§3.2 表）；`owned 网格未定位族`（L3248）闭集行退役。
- `skills/sr-od-dev-currency-war/references/flow/action-op.md`：§5 工具原子七类段（L130-140）整体改写为迁移后形态（显式坐标源/目标、守卫、坐标反查记账、交替载体更名、拒单码）；「记账路径总契约」条款的逐 op 差异附记按 §0.2 表在迭代收尾补入（收尾随正本承载义务）。
- `flow/prep-contract.md`：§1 L9 族描述更新（工具原子升级坐标显式传形态，例外家族收窄开件三类）；§3 L27-28 取值时机表补工具行（tool_cx/tool_cy/tgt_cx/tgt_cy = 发出面决策帧伴随域快照；row/slot/back_slot_count = 生成期快照；载体名更新）；§4 L21 契约 7 补一句（工具上报 = 坐标反查记账同族）；§5 装备臂行补工具臂读法或新增工具臂行（载体 = `CwActionToolUseOp`，坐标伴随域双键消费）；§6 G1 行更新（工具原子已随交替标志 + 伴随域补防线，现役辖域收窄为开件族箱/典籍/书册卡）。
- `docs/develop/sr_od/application/currency_war/sim/sim-design.md` §6.5 邻域（L175）：补 §6 申报句。

### 8.4 玩家 skill

`skills/sr-od-currency-war/references/screens/货币战争-备战.md` 条目 10（L15）改写：坐标形态调用法（源工具 icon cx/cy 从 extras.owned_equips 取，equip 目标件 cx/cy 同源；char 目标 row/slot + back_slot_count）；**单件会话使用**（一次调用一件，用后重读 analyze 对账；连穿/连用交还框架决策循环）；拒单码感知（round detail「记账拒单:tool_xy_unresolved」= 拖拽已发生账未落，禁补拖）。（实施角色按现行写作规范润色；玩家 skill 只提 MCP 工具。）

## 9. 风险与行为变化清单

1. **工具条目在坐标伴随域的观察覆盖（假设申报，验收门）**：工具 icon 的 SIFT 模板在装备注册表内、`read_equips` 对其产出坐标——本设计成立前提，无实机背书（观察链按注册表模板逐格分类，工具件在 `gs.equips` 与网格中，逻辑上应产出；但 v4.7 工具类判据已登记待裁，`cw_equipment_data.py:53-57`）。验收序列 0 = 实机核对 extras.owned_equips 含工具条目坐标；不成立 = 发出面恒跳过（自愈通道兜底不炸），本批停等数据域裁定。
2. **遥测基线变化**：标志更名 + `m7_5_evaluated` 口径收窄 + 新增两计数键 + `m7_5_tool_consume` 帧的参数构造内容变化——首局对照判读申报。
3. **工具域拒单语义收紧**：`tool_target_unit_missing` 从缺陷留存升格拒单、反查产物移除从容错转严格（精密扳手 consume=False 反查不到不拒单 = §3.1 豁免除外）——行为变化面 = 判读台账行形态（applied/reason）与窗口违反暴露方式；bug 面零写族（库存未观察/费用门/特权 char 分支）不变。
4. **直调路径形态边界**：与穿装批同款——直调无对照表刷新手段，第二件连用解不了表陈旧（恒拒单），按单件会话使用；拒单感知 = round detail 拒单码。
5. **拖拽链参数统一风险**：工具拖拽 duration 1.2 → 1.5 + settle 后置（§5.1-4）——无实机背书的参数迁移，实机验收①硬验收；同症状复现属执行层拖拽链可靠性（修参数不回退设计）。
6. **行为修复：char 模式工具后排 slot 7-9 从必拒变可用**（现状守卫表长只匹配基线 6 槽 §1.2-3）；判读基线：后排扩展局工具计划完成率预期上升。
7. **entry 第 7 步置位帧提前 return 的口径变化**：置位帧不进工具评估段（`m7_5_evaluated` 不递增）+ 穿装门不进（现状标志分支也不产穿装）——窗口禁消费的强保证换取评估计数口径变化（§2.3/§2.4）。
8. **交替开销**：每个工具使用 +1 环内重观察帧（与穿装批 A4 同构：末件后仍有一帧冗余 heavy，保留不改——末件免观察优化需要计划尾部判定复杂化，弃）；visit 动作数预算内自收敛。
9. ** mandate M7 门内标志检查的时序窟窿（有意保留，非漏洞）**：标志置位后 mandate 路径若连续多帧无穿戴候选，Obs 延迟到 entry 第 7 步上提检查位才发——窗口内 mandate 路径零坐标消费（不产穿装参数），不变式不破（§2.3 已论证）；若未来 mandate 路径新增坐标消费点，必须同款门内检查。
10. **范围边界**：开件三类（OpenBox/OpenTome/OpenBookcard）的 row/slot 形态、获得类 aftermath 的 A1 假设、`_remove_one` 对状态推导名的容错语义——均非本批辖域（申报行见 §11）。

## 10. 实施顺序建议（给实施角色）

1. `cw_vocab.py` 七类参数 + `action_param_from_dict` + 例外声明收窄（§4.1）→ `cw_game_state.py::resolve_item_by_xy`（§4.9，含 `wear_equip.py` 私有副本退役与调用点改引）。
2. `cw_action_report/tool_use.py` 记账路径重写（§4.4/§3）。
3. `cw_equip_env.py::tool_use_params_of`（§4.5）→ `mandate_state.py` 字段泛化（§4.8）→ `mandate.py` 更名（§4.7）→ `entry.py` 第 7 步改造（§4.6）。
4. `prep_actions.py` 退役三行码表 + `_owned_grid_locate` + `row_drag_points` docstring 收口（§4.10）→ `cw_tool_use_action.py` op 重写（§4.2/§5）→ `cw_equipment_data.py` 注释同步（§4.12）。
5. 测试（§7）→ 文档（§8.3）→ skill 两处（§8.4 + action-op.md 收尾义务）。
6. MCP server 重启 → `describe_operation_flow` 核对 op 节点图（两处 round_fail 通道消失、恒 round_success 形态）→ 实机验收序列（§7 验收段）。

## 11. 申报行（相邻问题，本批不修）

1. `CwActionWearEquipParam.from_dict` 内联体收敛到共享 `action_param_from_dict`（§1.1 遗留）——纯 refactor，归后续 sweep。
2. `cw_move_unit_action.py` / `cw_sell_deployed_action.py` 拖点仍走裸中心派生（`row_area_centers`，非 +21 权威式）——交互族不同（角色拖动/拖出售区），是否统一归交互族实机核对批。
3. 获得类动作（CollectOre/开件/补给）aftermath 是否置交替标志 = 穿装批 A1 假设回退方案的辖域（§2.3 末条），非本批。
4. 好运令牌判据面建模（R9 待办）与写端落位（`tool_use.py:534-546` 零写占位）——既有登记，不本批。
5. v4.7 工具类判据待裁（`cw_equipment_data.py:53-57`）——数据域裁定，影响 §9 条 1 前提。
6. 冶金炉 char 分支状态推导名移除的容错语义（`_remove_one`）与「越白名单件保留」未采证项（`tool_use.py:282-308`）——实机采证批辖域。
