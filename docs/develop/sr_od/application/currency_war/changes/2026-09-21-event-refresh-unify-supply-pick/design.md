# 事件屏刷新链统一 + 补给选卡即时上报 迭代设计（总纲）

## 0. 元信息

- 迭代目标：把三条用户裁定落到遭遇/补给两屏——
  1. **动作 op 点完立即上报完整结果**（规范正本 = `flow/action_ops.md` §1 增补 2；本迭代清偿 supply 欠账行）；
  2. **刷新类动作一律终结交回外循环重观察**（刷新改变选项，选项 = 决策输入，必须经入口观察重建，禁访问内自读新选项续决策；补给已按 ADR-0517 落地，本迭代把遭遇拉齐）；
  3. **刷新闸一律消费「剩余次数」屏显观察真值**（禁已用推算；字段先例 = `game_state/fields.md` §3.4.3/§3.4.4 的 `env_refresh_left`/`strategy_refresh_left`）。

  裁定 2/3 已入正本规范，单一源 = `screens/op-layer.md` §1.4「刷新 = 终结」「刷新闸 = 剩余语义观察真值」两条；遭遇链与两已用字段在正本中标注为在档欠账，本迭代即其清偿批。
- 状态：定稿（原三块经 attack.md/attack2.md 两轮收敛；扩围 §2.4 经 attack3.md 三核审处置后定稿，9 条全采纳，处置 = design/landing 同步修订）
- 文档清单：（无详设——单文档方案，本文即完整设计，深度 = 实现者无需再设计）

## 1. 问题与动机

### 1.1 现状症状（代码锚）

1. **补给 pick 两相上报**：发射相 = `operations/cw_op/cw_overlay_pick_action.py::CwActionPickSupplyOp.run` 确认点击后仅意图遥测（`kernel/cw_action_report/pick_supply.py` evidence 缺省分支，容器零写）；落地相 = 画面 op `_pending_supply` 证据闩（`operations/cw_screen/cw_screen_supply_node.py::_apply_supply_landing` 持 `EVIDENCE_OVERLAY_CLOSED` 在节点完成门 miss 时补写单位腿+装备后果腿）。踩 `action_ops.md` §1 禁止清单「等下一轮看画面才补写」条 + §1 裁定正文「禁止做验证」（overlay 已关 = 确认已落地，是判效；`screens/op-layer.md` §1.2「验证不是生命周期段」同款）。在册欠账 = `action_ops.md` §4.5 supply 行。
2. **遭遇刷新链访问内重读重决策**：`operations/cw_screen/cw_screen_encounter.py::_decide_encounter_action` 建议刷新 → `_try_refresh` 点钮 + 2s + **同访问 `self.screenshot()` 重读选项** + `report_screen_encounter_obs` 二次覆盖写 + 重调 `decide_encounter` + `encounter_refreshed_in_visit` per-visit 位防循环。违反「刷新 = 终结」全域规范（`screens/op-layer.md` §1.4，新选项未走入口观察重建）；决策体内截图不在读屏点在册例外（`screens/op-layer.md` §1.1 仅两类）。
3. **遭遇/补给刷新闸 = 已用计数**：`encounter_refresh_used`（申报写端 = on_outcome 发射型钩子，`cw_game_state.py` 字段注释/`cw_projection_audit.py` 审计行在册；**现役零落码写点，恒开局种子 0**，实际防循环面 = per-visit 位）+ `supply_refresh_used`（live 发射即 +1）。违反「刷新闸 = 剩余语义观察真值」全域规范（`screens/op-layer.md` §1.4）；且补给计数闸内嵌「每节点至多刷 1 次」先验。帧证 = 归档帧 `sr-od-test/screens/货币战争-补给/`（`default.webp` 剩余 0 / `双排装备.webp` 剩余 1，均为备战 1-5 补给节点）——同节点跨局剩余 0/1 并存，次数为逐局授予的变量；推论（非帧证）= 若存在授予 >1 次的局，已用计数闸漏刷（>1 授予待实证，不影响剩余语义修法成立——裁定 3 独立成立）。两字段源口径均收窄待证（fields.md §3.4.1/§3.4.2）——剩余语义读数直接消费游戏屏显真值，不依赖该先验。

### 1.2 根因归层

**约定层**：事件屏各链历史演化，未随 2026-09-21 两条裁定（动作上报增补 2、刷新计数剩余语义化）统一收口。非表示/流程层——容器字段、report 摄入、终结动作机制均已承载目标形态（投资两屏即证），无需动架构。

### 1.3 解决到哪 / 明确不解决

**解决**：①补给 pick 即时上报（清 supply 欠账行）；②遭遇 + 补给刷新链终结化、闸剩余语义化（`*_refresh_left` 新字段，`*_refresh_used` 与 `encounter_refreshed_in_visit` 退役）；③残留符号清理——`cw_screen_supply_node.py` 模块头死符号引用（`cw_telemetry.set_last_supply_pick`/`_LAST_SUPPLY_PICK`，现役不存在、全仓零写端）+ `telemetry/schema.py`「暂存槽/set_last_supply_pick 一致」同款陈旧注释（:529 附近），随 ①② 同文件顺手清。

**明确不解决（外溢候选登记）**：PickPlanner/PickEquip 两相欠账（同根同修法，本迭代 supply 行立模板后另批复制，禁并入本迭代——迭代边界判据见 `docs/develop/harness/iteration-design.md` §1.1；其各自文件的 `EVIDENCE_OVERLAY_CLOSED` 同名常量属彼辖，非本批清理面）；投资两屏（已合规，作参照系不动）；刷新建议判据本身（`kernel/cw_events.py::decide_encounter/decide_supply` 的现行刷新建议分支与 `refresh_used: bool` 参数签名不动，只换上游闸数据源）。

## 2. 方案

### 2.0 统一契约（跨阶段共享接口）

**A. 刷新链统一形态（遭遇/补给；投资两屏现状即此形态——投资环境另持在册例外②终结臂留证读，零决策零判效，不在本迭代复制）**

- **刷新 = 终结动作**：建议刷新 ∧ 闸放行 → `mouse_move`+`click` 圆钮（文本锚定位，坐标源不变）→ 固定等待 2s（`docs/game/currency_war/research/screen_flow_timing.md` #19/#23 重掷动画窗）→ `round_success` 终结交回外循环 → 重进 = 入口重建（新选项由入口观察现读）。**访问内零重读、零二次覆盖写、零重决策、零新增读屏点**。
- **闸 = 剩余语义同源双闸**：新容器顶层字段 `supply_refresh_left` / `encounter_refresh_left`（`int | None`；**None = 未观察**），写端 = 各屏观察 report 摄入「剩余次数：N」稳定帧读数（读缺跳写、逐访问覆盖；机械先例 = `kernel/cw_screen_report/invest_env.py` 的 `env_refresh_left` 摄入）。kernel 闸（`strategies/impl/flow.py` 刷新闸输入源；mandate 侧 = `bridge.py` 同源段）与 handler 对照闸同读该字段：**剩余 ≤0 或 None = 拒绝**；拒绝 → 重调一次决策按原评分选（单轮内有界）。
- **活锁方向安全性**（替代原 per-visit 位/烧旗标防线的论证）：建议刷新 → 放行 → 终结（访问结束，无循环面）；建议刷新 → 拒绝 → 本轮内重调一次 → 选卡派发 → 派发即终结。两分支都终结访问或落选卡，`round_wait` 循环面对刷新建议不再存在，重复建议无跨轮载体。
- **kernel 签名不动**：`decide_encounter/decide_supply(..., refresh_used: bool)` 形参保持，上游改传 `used = not (left is not None and left > 0)`。

**B. 补给 pick 即时上报形态（照投资两屏先例，`op-layer.md` §1.1 出口①「派发即终结」）**

- `CwActionPickSupplyOp.run` = 点卡 → 0.6s → 点确认 → **立即** `report_action_pick_supply_param`（单相，一口写效果逻辑态）→ `report_node_advance(gs, trigger='supply_confirm')`（现状保持，点击即上报）→ `round_success` 终结交回。确认未生效 = 代码 bug，overlay 残留由外循环按当前画面重识别重派，修法 = 点击链可靠性（禁验证/重试补丁）。
- **账面恒标准名，param 零扩字段**（用户裁定 2026-09-21：OCR 易错，账面名一律规范形态）：owned 权威写端 `read_equips` 本产规范名（模板逐格分类，`obs/cw_equipment.py`；模板键集 157 张 **⊆** 注册表 158 名——「财富」无模板，该名观察永不覆盖 = 自愈缺口，申报 + 模板采集挂账 data-collection 批，非本迭代），现行到账追加原始 OCR 名是账面异类形态——本批退出。**norm_item 锚集升级 + 分层归一**：`normalize_equip_name` 现锚 = 银狼专属 10 件穿戴门键（`cw_events._PLANNER_EQUIP_ANCHORS`），补给基础件不在其列 → 恒未解析；supply 侧改用**装备注册表级分层归一**（`kernel/cw_events.py` 新入口；planner 银狼锚归一语义不动，两入口分立），层级定死：
  1. **精确快道**：text 与注册表键名全等 → 直返。理由 = 纯「LCS 0.75 + 唯一命中」直移 158 名键集，完美 OCR 下实测 79/158 名多命中拒识（垃圾袋/金垃圾袋、生命之花/生命之环 0.75、追击/击破星徽互撞、昼/夜之半神星徽互撞、36 个特权名全撞进阶基名、白昼/极·白昼、Max/Pro 后缀族、命运族、穿刺/穿越死棘之枪）——相似判据不得为首层；
  2. **containment longest-first**：注册表名 contained in text 取最长唯一（`classify_planner_leg` 判定序第 1 步先例；「·特权」类装饰噪声由本层消解）；并列最长 → 落相似层；
  3. **相似救援**：LCS ≥ 0.75 唯一命中 → 返回；多命中/零命中 → ''（禁猜，fail-closed）。
  行为锁 = 特权/后缀族/互撞族完美 OCR 命中 + 形变救援 + 多命中拒识（landing 3.1）。残余申报：OCR 把一件误读成另一件规范名（生命之花→生命之环类）归一层原理不可辨，入账暂态错名由观察覆盖自愈（覆盖序论证 = §2.3）。
  handler 组装点换用分层归一，param 现有字段（`char_name` roster 校验产物 + `norm_item` 分层归一）即 report 全部输入——**不扩 raw_item/has_diamond**。
- **report 函数单相化**：`kernel/cw_action_report/pick_supply.py` 删 `evidence` 参数与 `EVIDENCE_OVERLAY_CLOSED` 常量（**仅本文件的同名常量**；pick_equip/pick_planner 各自同名常量属彼辖不动）；一口写序 = ⓪`char_name` 与 `norm_item` 双空（兜底点卡路径）→ 现行「内容全未知」分支逐位保持（bench/equips 值不变翻来源 + `pick_supply_content_unresolved` 缺陷行）→ ①`owned += norm_item`（**规范名**；'' = 未解析不写 + 翻来源留证缺陷行——fail-closed：错名不入账，观察覆盖自愈，覆盖序论证见 §2.3）②单位腿 `grant_bench_unit_cascade`（`char_name` 命中时）③装备后果腿 `apply_equip_acquire_consequence`（`norm_item` 命中时）；单位腿 char_name 未命中 → 现行翻来源留证语义保持。
- **chosen_supply 不进 report**：留守画面 op 选卡分支确认即写（现状写点、时机均已合规——`screens/op-layer.md` §2.2 动作事实边界硬规则零改动）。
- **ConfirmSupply 到账边退役**：`operations/cw_screen/_overlay_confirm.py::register_confirm_arrival` 的 ConfirmSupply 分支与 `kernel/cw_exec_state.py::apply_confirm_effect` 对应行删除（ConfirmBox/ConfirmTome/ConfirmExpertCash 不动）；pick op 内到账登记调用删除。
- **画面 op**：删 `_pending_supply`/`_apply_supply_landing`/证据闩 import；act 选卡分支 = 派发即 `round_success` 终结（零重入裁决）；节点完成门保留于 observe 首门（分发身份安全网：已离开 = 节点完成 success 交回）。

### 2.1 逐屏差异

- **补给**：建档「文本-剩余次数」已在（`assets/game_data/screen_info/currency_war_supply.yml` rect (1347,969)-(1484,997)，归档帧对账吻合）；`_read_refresh_anchor` 已解析 N——扩为返回 (count, point) 双出（同帧同源，零新增截图）；观察 node 读数进 obs（`CwScreenSupplyNodeObs` 加 `refresh_left` 字段）→ report 摄入。刷新分支删实例旗标 `_refresh_used` 与容器计数写点；锚读缺（count=None）→ 容器 None → 闸拒绝（覆盖原「零点击照常烧旗标」防线，烧旗标机制退役）。选定快照 `picked` dict：3.1 删 ConfirmSupply 消费后保留组装（选定事实现场载荷，现役零消费面，遥测接线候批），3.2 起 `picked['refreshed']` 布尔键改 `picked['refresh_left']`（值 = 容器 left 现值，可 None——布尔随计数闸消亡，left 快照供读端按剩余分型；无「本局初始授予数」基线，布尔不可由 left 等价导出，故改携带而非推导）。
- **遭遇**：「剩余次数」读数走既有代码内矩形通道 `obs/cw_node_obs.py::read_encounter_refresh_count`（fields.md §3.4.1 在册先例「遭遇屏建档无剩余次数区域」，不新建档）；`CwScreenEncounterObs.refresh_left` 字段已存在（现状 report 不消费）——report 补摄入，**摄入序照先例：options 空整函数早退不写（含 left）**（`invest_env.py` names 空先 return 同构）；`_try_refresh` 删重读半（保留点钮+等待）；`_decide_encounter_action` 删分支重决策/二次覆盖写/per-visit 位读写；选卡分支的重入裁决与 `chosen_encounter` 写端原列「不动」，**扩围（2026-09-21 用户裁定）后归 §2.4 辖内：重入裁决删除、chosen 写端迁动作侧即时上报，见 §2.4 第二/三块**。

### 2.2 消费点迁移总表

| 符号 | 现消费点 | 迁移 |
|---|---|---|
| `supply_refresh_used` | `cw_screen_supply_node.py`（读闸 + 写点） | 删（闸改 left；写点随终结形态消失） |
| | `strategies/impl/flow.py` 刷新闸源（现读 used 计数） | 改读 `supply_refresh_left` |
| | `sim/cw_sim_engine.py` 补给刷新段（observe 写 +1） | 改 observe 写 left：**补给节点入口先写初始 left = 1**（sim 世界授予真值，与现 `used<1` 闸等价），刷新时 left−1（≥0 截断） |
| | `kernel/cw_game_state.py`（开局种子 + 字段定义） | 字段删；新增 `supply_refresh_left`（无种子 = None 未观察）；`node_screen_refresh` 域版本 2→3 |
| | `kernel/cw_projection_audit.py` 审计行 | 行改 left |
| | `telemetry/schema.py` refreshed 值源注释 | 语义改写：选定快照 `refreshed` 布尔键退役（历史行只读），新行携 `refresh_left` 快照（见 §2.1 补给） |
| `picked['refreshed']`（选定快照布尔，值源 = used 计数读点） | `cw_screen_supply_node.py` 选卡分支组装；`telemetry/schema.py` supply_pick 字段注释 | 3.1 保留组装（消费面声明为零）；3.2 键改 `refresh_left` = 容器 left 现值快照（布尔不可由 left 等价导出，故改携带） |
| `encounter_refresh_used` | `cw_screen_encounter.py`（读闸） | 删 |
| | `kernel/cw_game_state.py`（种子 + 字段） | 删 |
| | `kernel/cw_projection_audit.py` 审计行 | 删行（left 新增行） |
| `encounter_refreshed_in_visit` | `strategies/impl/flow.py` + `strategies/impl/mandate_v1/bridge.py`（刷新旗标源） | 改读 `encounter_refresh_left`（used = not(left>0)） |
| | `cw_screen_encounter.py`（读写点） | 删 |
| | `kernel/cw_game_state.py`（字段 + node_screen_refresh 域版本注释） | 删（随域版本 bump） |
| `_confirm_pending`（确认已发快照） | `cw_screen_encounter.py`（置位 + 重入裁决读点） | 删（重入裁决退役，§2.4 第二块） |
| `_record_chosen` | `cw_screen_encounter.py`（重入裁决出口写 chosen） | 删（写端迁动作 report，§2.4 第三块） |
| `chosen_encounter`（写端） | 画面 op 重入裁决点（留守形态） | 迁 `kernel/cw_action_report/pick_encounter.py::report_action_pick_encounter_param`（发射即写；值组装 = `gs.encounter` payload 槽；兑现后清，§2.4 第三/四块） |
| `gs.encounter` payload 槽 | 消费点 = 决策入口（decide_encounter） | 新增消费点 = 动作 report 值组装（同源读，§2.4 第三块） |
| `encounter_reward_claimed`（新字段） | — | 新增：写端 = 结算兑现回调（§2.4 第四块）；审计行新增（cw_projection_audit）；遥测 schema 接线候批申报；兑现后清 `chosen_encounter`（单次消费） |
| `screen_flow_timing.md` #23 口径注 | encounter 观察注释引用 | 改写（supersession 标记，§2.4 第一块；文档判据 = landing 3.3） |

### 2.3 关键取舍（正本化时进动机段）- **剩余字段 = 独立顶层字段，不入 payload**：对齐投资两屏先例（`env_refresh_left`/`strategy_refresh_left` 均顶层）；payload 形状不动 → `encounter`/`supply` payload 域版本不 bump，只有 `node_screen_refresh` 域因字段增删 bump。
- **读缺(None) = 拒绝刷新，不做分支内现读兜底**：入口观察是唯一摄入点，分支内现读 = 保留第二读屏点（违读屏点纪律方向）；读缺低频低危（浪费一次刷新机会），活锁方向安全。
- **chosen_supply 留守画面 op，不进 report**：`op-layer.md` §2.2 动作事实边界硬规则零改动；现状「确认即写」时机已合规（写点 = 选择点，点击链发射前），本迭代只清效果腿的两相形态，不迁选择事实写点。对比项：投资域 chosen 迁获得链是显式收窄条款（用户裁定），supply 无同款裁定则不扩豁免。
- **效果腿进 report 函数，ConfirmSupply 到账边退役**：上报函数 = 该动作效果逻辑态写语义单点（`cw_action_report` 包 docstring 族规约）；两写点合并消双源。owned 名源 = **注册表规范名**（norm_item）——owned 权威写端 `read_equips` 观察摄取本产规范名（模板逐格分类），原始 OCR 名到账是账面异类形态，本批消双形态。
- **kernel 判据函数签名不动**（`refresh_used` 形参名保持）：`cw_events` 判据为 sim/生产共用面，签名稳定优先；语义换源收敛在上游闸一处。
- **param 零扩字段**：char_name（roster 校验产物）+ norm_item（分层归一）即 report 全部输入；has_diamond 不入 param（chosen_supply 留守 handler 后无 report 腿消费）、raw_item 不设（账面恒标准名，原始名退出——对抗审 F2 载体缺口随 owned 名源改规范名消解）。
- **覆盖序论证（owned 写后按名消费窗）**：owned 观察写端唯一 = 备战 heavy 帧（`cw_screen_prep.py` observe，失读 None 跳写保现值）。补给确认 → 节点推进 → 交回外循环 → 备战帧：备战 op **观察 node 先于决策动作 node**（两 node 结构序），商店 spare 打分（`flow.py`）/comps/穿戴计划/mandate 帧全部消费于决策侧 → 按名消费恒发生在重观察之后的新真值上。失读跳写窗 = 消费读旧值（暂态规范名或缺件），危害 = 排序/计划次优，与现行原始名入账同量级——残余如实申报，不设额外防线（治理归 reconcile/缺陷台账）。
- **sim 遭遇侧申报**：sim 引擎唯一决策入口 = 商店决策面（sim/ 全目录零遭遇刷新执行面），`decide_encounter` 判据不在 sim 路径 → `encounter_refresh_left` 无 sim 写端 = 预期非缺口；flow/bridge 判据换源仅 live 生效，sim 无行为差异。

### 2.4 遭遇扩围（2026-09-21 用户裁定；landing 3.3 后三块；经 attack3 对抗审处置修订）

- **入口稳定期删除**：观察 node 门命中即用 node runner 帧一次读。原 2s 稳定期（`research/screen_flow_timing.md` #23「右上『返回备战界面』出现后 2s 才稳定」）随用户裁定退役——用户为最高权威（先例 = combat.md §3 遭遇高危节点条），口径注同步改写。**空候选分支新行为（attack3 X2）**：候选读缺（`options` 空）≠ 失败安全——现状空候选会以 `idx=0` 盲选左卡并派发确认（不可逆消耗本节点选择）；删除稳定期后读缺概率上升，该盲选路径**一并退役**：`options` 空 = 零点击 `round_success` 终结交回外循环重进重读（与刷新闸数据不一致分支同构，`cw_screen_encounter.py` 现役先例）；剩余读缺 = None = 闸拒绝（不变）。
- **选卡派发即终结**：`CwActionPickEncounterOp` 派发后画面 op `round_success` 终结（投资两屏/补给 3.1 同形态），删重入裁决（`_confirm_pending`/锚在重走/`_record_chosen`）。活锁方向安全论证与 §2.0A 同构：决策必产恰一个动作（选卡派发 = 终结 / 刷新 = 终结 / 空候选 = 零点击交回），`round_wait` 循环对各分支均无跨轮载体。确认未生效 = 代码 bug，overlay 残留由外循环按当前画面重识别重派（修法 = 点击链可靠性）。
- **chosen_encounter 迁动作侧即时上报**：`report_action_pick_encounter_param` 从零写族升格容器写，**模块归宿 = 迁具名新模块 `kernel/cw_action_report/pick_encounter.py`**（attack3 X6 处置修正：attack3 建议名 `encounter.py` 与包规约「文件名 = 动作 snake」冲突，落地取 snake 对齐形态；照 pick_supply 升格先例，zero_writes 零写族语义不容容器写函数留守），zero_writes 删该函数并更新迁出注记，landing 文件面同步。值组装 = `gs.encounter` payload 槽 `options[param.idx]`（策略决策同源，param 零扩字段）；payload 离屏/idx 越界 = 缺陷留证不写（None 保持「无记录」，防盲选固化假值——现 `_record_chosen` 守卫口径平移）。**暂态假值窗申报（attack3 X8）**：chosen 迁后语义 = 「发射即写的意图记录」，确认未生效窗内为暂态假值，由外循环重派覆盖自愈；奖励兑现回调对该窗的消费防线见第四块（兑现后清 chosen）。op-layer §2.2 动作事实边界硬规则对应腿修订：遭遇例外改判（用户裁定显式迁移，先例 = 投资域 chosen 迁获得链的显式收窄条款）；巨星/伙伴等其余 chosen_* 维持不动。
- **结算奖励兑现回调**：机制依据 = `research/combat.md` §3「遭遇奖励 = 伤害进度达标制，非清场制」——进度打够最低线即拿奖励，定谳采集点 = 结算屏三项（现役 `progress_delta` 已入 `RoundOutcome` 与容器结算域）。挂点 = `CwOpSettleConfirm` 确认点击后调 kernel 回调（`kernel/cw_encounter_selection.py::claim_encounter_reward`，遭遇×结算对账域）。回调 = 纯容器读零读屏。
  - **判据（attack3 X4/X7 处置后）**：节点判遭遇 = 双证——`node_kind_of(gs) == '遭遇'`（读 `gs.node` 镜像 = 最近备战帧观察的节点类型）**∧** 容器结算行 `note == 'battle_done:遭遇'`（本局结算覆盖写端的行注记，防跨节点类型陈旧）；达标 = **单判** `gs.settlement` 域 `progress_delta > 0`（killed 不入判据：结算链 killed 多为 progress 符号派生值、hp 对比兜底腿在遭遇局「伤害进度达标制」下语义未证，attack3 X7）；`progress_delta is None` = 删失不兑现；`chosen_encounter` 为 None（未写/已消费）= 不兑现。**兑现后清 `chosen_encounter`（单次消费语义）**——一并收口三条误兑现面（attack3 X4）：镜像残留（兑现后 chosen 空，后续非遭遇局恒拒）、驻留重入轮（第二轮 chosen 已空，天然幂等，零闩）、结算覆盖 best-effort 失败的陈旧窗（上一场兑现已清 chosen；**残余申报**：本场结算覆盖失败 ∧ 上一场同为遭遇 ∧ 本场 chosen 已写时仍可能误记一条兑现记录——低频观测异常组合，后果 = 语义账面脏行非资金操作，如实申报不设额外防线）。
  - **载体与接线（attack3 X3）**：新顶层字段 `encounter_reward_claimed: tuple[int, str] | None`（值 = (难度档, 奖励文本)，单槽逐遭遇覆盖）；写通道 = `gs.write_logic`，`ChannelSig(family='logic_action', actor='CwOpSettleConfirm', mode='compute')`（写端 = 回调宿主 op）；`kernel/cw_projection_audit.py` 新增审计行；遥测 schema 接线**候批申报**（现役消费面 = 容器读端（策略器收益对账）+ 审计投影，journal 行随结算确认 op 现有链路）；生命周期 = 局内逐遭遇覆盖，无开局种子（None = 本局未兑现过），局终随容器销毁；sim 零写端申报（sim 无遭遇结算回调面，与 `encounter_refresh_left` 同申报）。
  - **时序论证（attack3 X4(a) 重写）**：`report_node_advance` 只推进 `gs.node_ord` 序号，不写 `gs.node` 镜像——回调在推进前或后调对 `node_kind_of` 读值无差别；「确认点击后、推进上报前调回调」保留的理由 = 语义顺序（先记账后推进）与防御下一备战帧观察早到覆写镜像；本局结算数据就绪性由宿主 `CwScreenBattleWait` ②段保证（读点先于确认 op 派发，attack3 已核无异议）。
  - **数值不直写**（防双源）：金币真值 = `apply_settlement_cover` 的 `settle_truth`（结算读数）、随机4费角色 = bench heavy 观察（观察赢）；兑现记录 = 语义账面，消费面 = 策略器收益对账/单局复盘。无 chosen（盲选 fallback/残留行）→ 不兑现。

## 3. 验收锚（行为级；验收凭据形式见 landing 各阶段）

1. 补给选卡：确认点击后（不等下一帧）容器即持效果逻辑态——owned 含装备规范名（norm_item 命中时）+ bench 含角色（合成级联后）；`chosen_supply` 三元组在派发前已由画面 op 写（现状时机不变）；注册表级分层归一行为锁：特权/后缀族/互撞族（垃圾袋/金垃圾袋、生命之花/生命之环、追击/击破星徽）完美 OCR 恒命中、OCR 形变救援命中、多命中拒识返回 ''；supply 链无落地相补写面（`kernel/cw_action_report/pick_supply.py` 的 `EVIDENCE_OVERLAY_CLOSED` 及其在 supply 链的导入点零残留；pick_equip/pick_planner 同名常量不在辖内）。
2. 补给刷新：剩余 1 → 建议刷新 → 点钮恰一次 → 访问终结交回；剩余 0 或 None → 零点击不终结，按原评分选卡。
3. 遭遇刷新：点钮恰一次 → 访问终结交回（无同访问重读、无二次覆盖写、无重决策）；剩余 0 或 None → 按原评分选卡。入口门命中即读（无 2s 稳定期）；**候选读缺（options 空）= 零点击 round_success 终结交回（禁盲选派发确认）**。选卡：派发即 `round_success` 终结（零重入裁决轮）；确认点击后（不等下一帧）容器即持 `chosen_encounter` = payload 槽所选 (难度, 奖励文本)；payload 离屏/idx 越界 = 缺陷留证不写。奖励兑现：遭遇结算确认 ∧（node 镜像='遭遇' ∧ 结算行 note='battle_done:遭遇'）∧ `progress_delta>0` → 容器即持 `encounter_reward_claimed` = 所选 (难度, 奖励文本)，**且 `chosen_encounter` 随即被清（单次消费）**；未达标/删失/无 chosen → 不写不清。
4. 全链零已用计数残留：`supply_refresh_used`/`encounter_refresh_used`/`encounter_refreshed_in_visit` 三符号零命中（grep 范围 = src + sr-od-test；豁免 = telemetry 历史数据只读注释）。
