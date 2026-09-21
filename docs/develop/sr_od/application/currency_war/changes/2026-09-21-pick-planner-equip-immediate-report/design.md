# PickPlanner/PickEquip 两相上报清偿 迭代设计（总纲）

## 0. 元信息

- 迭代目标：清偿 `flow/action_ops.md` §4.5 在册欠账最后两行——PickPlanner/PickEquip 的「先只记日志、等确认生效的证据再补写结果」分步上报，按 §1 增补 2（2026-09-21 用户裁定「动作 op 点完就立即上报，按成功把结果写进 game state」）改为点完立即上报完整结果。承接出处 = 上一迭代（event-refresh-unify-supply-pick）T-1 供给行立样的迁移模板 + T-1 验收建议立项（账本 T-5）。
- 状态：草案
- 文档清单：（无详设——单文档方案，本文即完整设计，深度 = 实现者无需再设计）

## 1. 问题与动机

### 1.1 现状症状（代码锚）

1. **骇入策划屏（银狼）两相**：发射相 = `operations/cw_op/cw_overlay_pick_action.py::CwActionPickPlannerOp.run` 确认链发出后仅意图遥测（`kernel/cw_action_report/pick_planner.py` evidence 缺省分支，容器零写）；落地相 = 画面 op `operations/cw_screen/cw_screen_yinlang.py` act 顶部重入裁决出口（OCR「我来当策划」不在 = overlay 已关）消费 `_pending_leg`/`_pick_param` 证据闩，持 `EVIDENCE_OVERLAY_CLOSED` 调落地相（equip 腿入栏+后果链 / upgrade 变换窗三态+档行 / unknown 留证 / weaken 零写）。踩增补 2 禁止清单「等下一轮看画面才补写」+ 裁定正文「禁止做验证」（overlay 已关 = 确认已落地，是判效）。
2. **选择装备屏两相**：发射相 = `CwActionPickEquipOp.run` 点卡后仅意图遥测（`kernel/cw_action_report/pick_equip.py` 同构）；落地相 = `operations/cw_screen/cw_screen_equip_pick.py` act 顶部重入裁决出口（OCR「请选择」不在）消费 `_pending_pick` 证据闩（归一件名入栏+后果链）。
3. **同名常量三处自持**：`EVIDENCE_OVERLAY_CLOSED` 在 pick_planner.py / pick_equip.py 各自定义（原自 pick_invest import，该文件随投资两屏迁移批删除后就地自持）——供给行清偿后成为全仓仅剩的两处两相形态。

### 1.2 根因归层

**约定层**：两屏未随投资两屏/供给行迁移批清偿，非机制缺口——迁移模板（T-1 供给行：单相一口写 + 派发即终结 + 证据闩退役）已在册且经验收。

### 1.3 解决到哪 / 明确不解决

**解决**：①两屏 pick op 单相化（点完确认/点卡立即上报完整效果腿）；②画面 op 证据闩与重入裁决退役、派发即 `round_success` 终结；③两文件 `EVIDENCE_OVERLAY_CLOSED` 常量及全部消费面退役——`action_ops.md` §4.5 欠账段自此**全域清零**。

**明确不解决**：upgrade 变换窗的前置硬校验语义（三态+档行逻辑逐位保持，只换调用时点）；`classify_planner_leg` 银狼锚分类器语义（planner 腿型判定专用，不动）；巨星/伙伴等零写族 pick 屏（它们不是两相欠账——chosen_* 留守重入裁决是 `op-layer.md` §2.2 现行合法形态，迁移归后续批如有裁定）；equip 屏候选域判定判据（`decide_equip_overlay_pick` 不动）。

## 2. 方案

### 2.0 统一契约（两屏共享，照 T-1 供给行模板）

- **pick op 单相化**：机械链（点卡 → 固定等待 → [planner] 确认点击）发出后**立即** `report_action_pick_<snake>_param`（删 `evidence` 参数与本文件 `EVIDENCE_OVERLAY_CLOSED` 常量，一口写完整效果腿）→ `round_success` 终结交回。确认未生效 = 代码 bug，overlay 残留由外循环按当前画面重识别重派（修点击链可靠性，禁验证/重试/防重复补丁——增补 2 禁止清单第 4 条：单相化后「未生效重派 → 效果腿重复应用」的风险按裁定接受，不设防）。
- **画面 op 派发即终结**：act = 决策 → 组装 param/env → 派发 → `round_success` 终结；删重入裁决（`_confirm_pending`/`_pending_leg`/`_pick_param`/`_pick_pending`/`_pending_pick` 全部退役）与对应 OCR 出口门。`CwActionPickPlannerOp` 体内对宿主的 `op._confirm_pending = True` 置位随之删除。
- **时序等价论证（upgrade 腿前置校验）**：原落地相时点 = 确认生效（overlay 关）；新时点 = 确认点击后。两时点之间容器零写入（overlay 动画窗内无观察发生——观察只发生在画面 op 观察 node 与备战入口 heavy 帧），`_apply_upgrade_transform` 前置校验读的 bench/front/back 观察态等值，三态判定与档行语义不变。
- **增补 3 合规自查**：迁移后动作 op 内零新增读屏——planner 的 confirm 定位照现状（`emit_overlay_confirm` 机械确认），equip 点卡定位由 env 传入；归一组装点留在画面 op 决策半（现役位置不动），动作 op 不做观察识别。

### 2.1 逐屏差异

- **选择装备屏（equip，先做——简单腿立复核）**：
  - `CwActionPickEquipOp.run` = 点卡（env.target）→ 固定等 1.2s → 立即上报（单相：`norm_item` 命中 → owned 入栏 + 获得后果链；'' = 未解析翻来源留证）→ `round_success` 终结。本屏点卡即选、无确认步。
  - **归一升级（复用 T-1 已建入口）**：组装点 `normalize_equip_name`（银狼 10 件锚）换 `normalize_registry_equip_name`（注册表 158 名分层归一，T-1 已建）——本屏候选含泛用件（docstring「未锁态语义（仅泛用腿）」在册），10 件锚对泛用件恒 ''；注册表级让泛用注册表件规范名入栏，未命中 fail-closed 不写留证 + 观察覆盖自愈（与供给行同构）。`normalize_equip_name` 本体语义不动（银狼域其他消费面）。
  - 画面 op：删 `_pick_pending`/`_pending_pick`/重入裁决出口门；act = 决策（越界/异常 fallback 第 1 张现状保持）→ 组装 param（idx + 注册表分层归一 norm_item）→ 派发 → `round_success` 终结。本屏零 chosen（选择存证已退役，docstring 在册）。
- **骇入策划屏（planner，后做——复杂腿）**：
  - `CwActionPickPlannerOp.run` = 点卡（env.target，避开「详情」按钮区选中点照旧）→ 固定等 1.2s → 确认点击（`emit_overlay_confirm`，裁决词「我来当策划」照旧）→ 立即 `report_action_pick_planner_param(gs, action, sig, leg_type=env.leg_type, norm_item=env.norm_item)`（单相；leg_type/norm_item 经 env kwargs 形态保持——planner 载荷先例，不迁 param）→ `round_success` 终结。体内 `op._confirm_pending = True` 置位删除。
  - 落地效果腿**逐位保持**：equip 腿（norm_item 命中 → 入栏+后果链；'' 翻来源留证）/ upgrade 变换窗三态+档行（前置硬校验，见 §2.0 时序等价论证）/ unknown 留证 / weaken 零写。
  - 画面 op：删 `_confirm_pending`/`_pending_leg`/`_pick_param`/重入裁决出口门；act = 零参决策 → `classify_planner_leg` 腿型 → 组装 env → 派发 → `round_success` 终结。本屏零 chosen 字段（现状即无）。
  - **归一不升级**：planner 的 `norm_item` 来自 `classify_planner_leg`（腿型判定单源，银狼锚语义 = 本屏判定域），**保持不动**——它不是入栏归一器，是腿型分类器的副产品。

### 2.2 消费点迁移总表

| 符号 | 现消费点 | 迁移 |
|---|---|---|
| `EVIDENCE_OVERLAY_CLOSED`（pick_equip.py 自持） | `cw_screen_equip_pick.py` import+调用；`test_cw_pick_channels_t60.py`（EQUIP_EVIDENCE 面） | 全删；测试改断言「确认点击后容器即持效果」 |
| `EVIDENCE_OVERLAY_CLOSED`（pick_planner.py 自持） | `cw_screen_yinlang.py` import+调用；`test_cw_yinlang_phase32.py`（10+ 处） | 全删；测试改写单相断言 |
| `_pick_pending`/`_pending_pick`（equip_pick） | 本文件读写点 | 删 |
| `_confirm_pending`/`_pending_leg`/`_pick_param`（yinlang） | 本文件读写点 + `cw_overlay_pick_action.py::CwActionPickPlannerOp` 体内置位 | 删（含 pick op 体内置位行） |
| `report_action_pick_equip_param` | equip pick op 调用（发射相）；equip_pick handler 调用（落地相） | 单点化 = equip pick op 确认后一口调用 |
| `report_action_pick_planner_param` | planner pick op 调用（发射相）；yinlang handler 调用（落地相） | 单点化 = planner pick op 确认后一口调用 |
| `normalize_equip_name`（equip pick 组装点） | `cw_screen_equip_pick.py` | 换 `normalize_registry_equip_name`（T-1 已建）；`normalize_equip_name` 本体不动 |

### 2.3 关键取舍（正本化时进动机段）

- **两屏拆两阶段而非合并**：机械链不同（equip 点卡即选 / planner 有确认钮），独立验收粒度清晰；共享文件 `cw_overlay_pick_action.py` 串行批防冲突。
- **equip 归一升级复用注册表分层入口而非保持银狼锚**：本屏候选含泛用件（在册），银狼锚恒 '' = 泛用件永不入栏（现状缺陷）；注册表级与供给行 owned 形态统一；未命中 fail-closed 同构。
- **planner 载荷保持 env kwargs 不迁 param**：leg_type/norm_item 是腿型分类产物非卡选择本体，env 透传先例现役；迁 param 无消费收益。
- **单相重复应用风险不设防**：增补 2 禁止清单第 4 条明文（确认未生效重派 = 代码 bug 域，禁判重保护）；upgrade 变换腿重复应用的后果（多升一次档）同域接受，响亮暴露修根因。

## 3. 验收锚（行为级；验收凭据形式见 landing 各阶段）

1. equip：点卡后（不等下一帧）容器即持 owned（规范名，含泛用件——注册表归一命中时）+ 后果链；画面 op 派发即终结（无重入裁决轮）；`pick_equip.py` 来源 `EVIDENCE_OVERLAY_CLOSED` 及其消费面零残留。
2. planner：确认点击后（不等下一帧）容器即持对应腿效果——equip 腿入栏+后果链 / upgrade 变换（2★→1★）+ 档行 +1 + 级联 / unknown 留证 / weaken 零写；画面 op 派发即终结；`pick_planner.py` 来源 `EVIDENCE_OVERLAY_CLOSED` 及其消费面零残留。
3. 全域两相欠账清零：`action_ops.md` §4.5 欠账段摘除后，全仓 grep `EVIDENCE_OVERLAY_CLOSED` 零命中（豁免 = 无——供给行已清，本批后应全域归零）。
