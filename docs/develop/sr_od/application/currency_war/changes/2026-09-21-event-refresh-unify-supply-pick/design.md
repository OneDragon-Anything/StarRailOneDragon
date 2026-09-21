# 事件屏刷新链统一 + 补给选卡即时上报 迭代设计（总纲）

## 0. 元信息

- 迭代目标：把三条用户裁定落到遭遇/补给两屏——
  1. **动作 op 点完立即上报完整结果**（规范正本 = `flow/action_ops.md` §1 增补 2；本迭代清偿 supply 欠账行）；
  2. **刷新类动作一律终结交回外循环重观察**（刷新改变选项，选项 = 决策输入，必须经入口观察重建，禁访问内自读新选项续决策；补给已按 ADR-0517 落地，本迭代把遭遇拉齐）；
  3. **刷新闸一律消费「剩余次数」屏显观察真值**（禁已用推算；字段先例 = `game_state/fields.md` §3.4.3/§3.4.4 的 `env_refresh_left`/`strategy_refresh_left`）。

  裁定 2/3 已入正本规范，单一源 = `screens/op-layer.md` §1.4「刷新 = 终结」「刷新闸 = 剩余语义观察真值」两条；遭遇链与两已用字段在正本中标注为在档欠账，本迭代即其清偿批。
- 状态：草案
- 文档清单：（无详设——单文档方案，本文即完整设计，深度 = 实现者无需再设计）

## 1. 问题与动机

### 1.1 现状症状（代码锚）

1. **补给 pick 两相上报**：发射相 = `operations/cw_op/cw_overlay_pick_action.py::CwActionPickSupplyOp.run` 确认点击后仅意图遥测（`kernel/cw_action_report/pick_supply.py` evidence 缺省分支，容器零写）；落地相 = 画面 op `_pending_supply` 证据闩（`operations/cw_screen/cw_screen_supply_node.py::_apply_supply_landing` 持 `EVIDENCE_OVERLAY_CLOSED` 在节点完成门 miss 时补写单位腿+装备后果腿）。踩 `action_ops.md` §1 禁止清单两条：「等下一轮看画面才补写」+「验证是否成功」（overlay 已关 = 确认已落地，是判效）。在册欠账 = `action_ops.md` §4.5 supply 行。
2. **遭遇刷新链访问内重读重决策**：`operations/cw_screen/cw_screen_encounter.py::_decide_encounter_action` 建议刷新 → `_try_refresh` 点钮 + 2s + **同访问 `self.screenshot()` 重读选项** + `report_screen_encounter_obs` 二次覆盖写 + 重调 `decide_encounter` + `encounter_refreshed_in_visit` per-visit 位防循环。违反「刷新 = 终结」全域规范（`screens/op-layer.md` §1.4，新选项未走入口观察重建）；决策体内截图不在读屏点在册例外（`screens/op-layer.md` §1.1 仅两类）。
3. **遭遇/补给刷新闸 = 已用计数**：`encounter_refresh_used`（fields.md §3.4.1 写端申报 = on_outcome 发射型钩子）+ `supply_refresh_used`（live 发射即 +1）。违反「刷新闸 = 剩余语义观察真值」全域规范（`screens/op-layer.md` §1.4）；且补给计数闸内嵌「每节点至多刷 1 次」先验，与实测矛盾——归档帧 `sr-od-test/screens/货币战争-补给/`（`default.webp` 剩余 0 / `双排装备.webp` 剩余 1，同为备战 1-5 补给节点）证明次数为逐局授予的变量，授予 >1 次即漏刷。两字段源口径均收窄待证（fields.md §3.4.1/§3.4.2）——剩余语义读数直接消费游戏屏显真值，不依赖该先验。

### 1.2 根因归层

**约定层**：事件屏各链历史演化，未随 2026-09-21 两条裁定（动作上报增补 2、刷新计数剩余语义化）统一收口。非表示/流程层——容器字段、report 摄入、终结动作机制均已承载目标形态（投资两屏即证），无需动架构。

### 1.3 解决到哪 / 明确不解决

**解决**：①补给 pick 即时上报（清 supply 欠账行）；②遭遇 + 补给刷新链终结化、闸剩余语义化（`*_refresh_left` 新字段，`*_refresh_used` 与 `encounter_refreshed_in_visit` 退役）；③`cw_screen_supply_node.py` 模块头残留符号清理（`cw_telemetry.set_last_supply_pick`/`_LAST_SUPPLY_PICK` 引用——两符号现役不存在，全仓零写端，随 ① 顺手清）。

**明确不解决（外溢候选登记）**：PickPlanner/PickEquip 两相欠账（同根同修法，本迭代 supply 行立模板后另批复制，禁并入本迭代——迭代边界判据见 `docs/develop/harness/iteration-design.md` §1.1）；投资两屏（已合规，作参照系不动）；刷新建议判据本身（`kernel/cw_events.py::decide_encounter/decide_supply` 的 P81 判据与 `refresh_used: bool` 参数签名不动，只换上游闸数据源）。

## 2. 方案

### 2.0 统一契约（跨阶段共享接口）

**A. 刷新链统一形态（遭遇/补给；投资两屏现状即此形态）**

- **刷新 = 终结动作**：建议刷新 ∧ 闸放行 → `mouse_move`+`click` 圆钮（文本锚定位，坐标源不变）→ 固定等待 2s（`docs/game/currency_war/research/screen_flow_timing.md` #19/#23 重掷动画窗）→ `round_success` 终结交回外循环 → 重进 = 入口重建（新选项由入口观察现读）。**访问内零重读、零二次覆盖写、零重决策、零新增读屏点**。
- **闸 = 剩余语义同源双闸**：新容器顶层字段 `supply_refresh_left` / `encounter_refresh_left`（`int | None`；**None = 未观察**），写端 = 各屏观察 report 摄入「剩余次数：N」稳定帧读数（读缺跳写、逐访问覆盖；机械先例 = `kernel/cw_screen_report/invest_env.py` 的 `env_refresh_left` 摄入）。kernel 闸（`strategies/impl/flow.py` 刷新闸输入源；mandate 侧 = `bridge.py` 同源段）与 handler 对照闸同读该字段：**剩余 ≤0 或 None = 拒绝**；拒绝 → 重调一次决策按原评分选（单轮内有界）。
- **活锁方向安全性**（替代原 per-visit 位/烧旗标防线的论证）：建议刷新 → 放行 → 终结（访问结束，无循环面）；建议刷新 → 拒绝 → 本轮内重调一次 → 选卡派发 → 派发即终结。两分支都终结访问或落选卡，`round_wait` 循环面对刷新建议不再存在，重复建议无跨轮载体。
- **kernel 签名不动**：`decide_encounter/decide_supply(..., refresh_used: bool)` 形参保持，上游改传 `used = not (left is not None and left > 0)`。

**B. 补给 pick 即时上报形态（照投资两屏先例，`op-layer.md` §1.1 出口①「派发即终结」）**

- `CwActionPickSupplyOp.run` = 点卡 → 0.6s → 点确认 → **立即** `report_action_pick_supply_param`（单相，一口写完整结果）→ `report_node_advance(gs, trigger='supply_confirm')`（现状保持，点击即上报）→ `round_success` 终结交回。确认未生效 = 代码 bug，overlay 残留由外循环按当前画面重识别重派，修法 = 点击链可靠性（禁验证/重试补丁）。
- **report 函数单相化**：`kernel/cw_action_report/pick_supply.py` 删 `evidence` 参数与 `EVIDENCE_OVERLAY_CLOSED` 常量；一口写序 = ①`chosen_supply` 三元组 ②`owned += 装备原始名` ③单位腿 `grant_bench_unit_cascade`（char_name 命中时）④装备后果腿 `apply_equip_acquire_consequence`（norm_item 命中时）；内容全未知/装备名未解析 → 现行翻来源留证语义逐位保持。
- **ConfirmSupply 到账边退役**：`operations/cw_screen/_overlay_confirm.py::register_confirm_arrival` 的 ConfirmSupply 分支与 `kernel/cw_exec_state.py::apply_confirm_effect` 对应行删除（ConfirmBox/ConfirmTome/ConfirmExpertCash 不动）；pick op 内到账登记调用删除。owned 名源 = **OCR 原始名**（时序逐位保持现行到账语义——与 Box/Tome 及装备域按名查找同名源，不用归一名防失配）；后果腿 = `norm_item` 归一名（不变）。
- **画面 op**：删 `_pending_supply`/`_apply_supply_landing`/证据闩 import；act 选卡分支 = 派发即 `round_success` 终结（零重入裁决）；节点完成门保留于 observe 首门（分发身份安全网：已离开 = 节点完成 success 交回）。

### 2.1 逐屏差异

- **补给**：建档「文本-剩余次数」已在（`assets/game_data/screen_info/currency_war_supply.yml` rect (1347,969)-(1484,997)，归档帧对账吻合）；`_read_refresh_anchor` 已解析 N——扩为返回 (count, point) 双出（同帧同源，零新增截图）；观察 node 读数进 obs（`CwScreenSupplyNodeObs` 加 `refresh_left` 字段）→ report 摄入。刷新分支删实例旗标 `_refresh_used` 与容器计数写点；锚读缺（count=None）→ 容器 None → 闸拒绝（覆盖原「零点击照常烧旗标」防线，烧旗标机制退役）。
- **遭遇**：「剩余次数」读数走既有代码内矩形通道 `obs/cw_node_obs.py::read_encounter_refresh_count`（fields.md §3.4.1 在册先例「遭遇屏建档无剩余次数区域」，不新建档）；`CwScreenEncounterObs.refresh_left` 字段已存在（现状 report 不消费）——report 补摄入；`_try_refresh` 删重读半（保留点钮+等待）；`_decide_encounter_action` 删分支重决策/二次覆盖写/per-visit 位读写；选卡分支的重入裁决与 `chosen_encounter` 写端**不动**（动作事实边界现行合法形态，`op-layer.md` §2.2，不在本迭代辖内）。

### 2.2 消费点迁移总表

| 符号 | 现消费点 | 迁移 |
|---|---|---|
| `supply_refresh_used` | `cw_screen_supply_node.py`（读闸 + 写点） | 删（闸改 left；写点随终结形态消失） |
| | `strategies/impl/flow.py` 刷新闸源（现读 used 计数） | 改读 `supply_refresh_left` |
| | `sim/cw_sim_engine.py` 补给刷新段（observe 写 +1） | 改 observe 写 `supply_refresh_left`-1（≥0 截断） |
| | `kernel/cw_game_state.py`（开局种子 + 字段定义） | 字段删；新增 `supply_refresh_left`（无种子 = None 未观察）；`node_screen_refresh` 域版本 2→3 |
| | `kernel/cw_projection_audit.py` 审计行 | 行改 left |
| | `telemetry/schema.py` refreshed 值源注释 | 值源改 left 读点 |
| `encounter_refresh_used` | `cw_screen_encounter.py`（读闸） | 删 |
| | `kernel/cw_game_state.py`（种子 + 字段） | 删 |
| | `kernel/cw_projection_audit.py` 审计行 | 删行（left 新增行） |
| `encounter_refreshed_in_visit` | `strategies/impl/flow.py` + `strategies/impl/mandate_v1/bridge.py`（刷新旗标源） | 改读 `encounter_refresh_left`（used = not(left>0)） |
| | `cw_screen_encounter.py`（读写点） | 删 |
| | `kernel/cw_game_state.py`（字段 + node_screen_refresh 域版本注释） | 删（随域版本 bump） |

### 2.3 关键取舍（正本化时进动机段）

- **剩余字段 = 独立顶层字段，不入 payload**：对齐投资两屏先例（`env_refresh_left`/`strategy_refresh_left` 均顶层）；payload 形状不动 → `encounter`/`supply` payload 域版本不 bump，只有 `node_screen_refresh` 域因字段增删 bump。
- **读缺(None) = 拒绝刷新，不做分支内现读兜底**：入口观察是唯一摄入点，分支内现读 = 保留第二读屏点（违读屏点纪律方向）；读缺低频低危（浪费一次刷新机会），活锁方向安全。
- **一口写进 report 函数，不保留 ConfirmSupply 到账边**：上报函数 = 该动作容器写语义单点（`cw_action_report` 包 docstring 族规约）；两写点合并消双源。
- **kernel 判据函数签名不动**（`refresh_used` 形参名保持）：`cw_events` 判据为 sim/生产共用面，签名稳定优先；语义换源收敛在上游闸一处。

## 3. 验收锚（行为级；验收凭据形式见 landing 各阶段）

1. 补给选卡：确认点击后（不等下一帧）容器即持完整结果——`chosen_supply` 三元组 + owned 含装备原始名 + bench 含角色（合成级联后）；全链无落地相补写面（`_pending_supply`/`EVIDENCE_OVERLAY_CLOSED` 零残留）。
2. 补给刷新：剩余 1 → 建议刷新 → 点钮恰一次 → 访问终结交回；剩余 0 或 None → 零点击不终结，按原评分选卡。
3. 遭遇刷新：点钮恰一次 → 访问终结交回（无同访问重读、无二次覆盖写、无重决策）；剩余 0 或 None → 按原评分选卡。
4. 全链零已用计数残留：`supply_refresh_used`/`encounter_refresh_used`/`encounter_refreshed_in_visit` 三符号全仓 grep 零命中（telemetry 历史数据只读注释除外）。
