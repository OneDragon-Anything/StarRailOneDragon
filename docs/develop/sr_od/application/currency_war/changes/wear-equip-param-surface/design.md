# CwActionWearEquipOp（穿装）参数面迁移设计稿

> 迭代：CW 动作 op 迁移流水线 · 设计角色产出（agent 1/4）。
> 对象 = 穿装备动作 op 的参数面改造：执行路径零 game state 依赖 + 参数三分法 + from_dict JSON 通道。
> 冻结宪法（用户裁定）：①动作 op 执行路径零 gs 依赖（可选快路径全部拔除）；②参数面三分法（固定槽位=下标 / 半固定=下标+槽位总数 / 动态坐标=显式 (cx,cy)+语义参数）；③名称字段=语义参数（可选，不参与校验与定位，仅日志）；④坐标新鲜度纪律归调用方（op 纯机械，不做落点前校验）；⑤参数 dataclass 统一补 `from_dict`；⑥gs 要给实体记录坐标（策略层能拿出具体坐标传参的前提）；⑦每个 op 一个迭代，牵涉面一次改净。

## 0. 现状与痛点（探查实据）

- 参数 `kernel/cw_vocab.py::CwActionWearEquipParam`（L499-514）：`item_name/char_name/row/slot/route_tag`，无 `from_dict`。
- op `operations/cw_op/cw_wear_equip_action.py::CwActionWearEquipOp`：构造签名 `(ctx, param, env: PrepExecEnv)`，env 必填。
- 痛点一（MCP 通道）：`src/sr_od/backend/operation_registry.py::_from_dict_type`（L172-177）规定 run_operation JSON 通道只接受「`@dataclass` + 可调用 `from_dict`」的参数注解——词表 param 全族无 `from_dict`（grep 全 CW 域仅 `telemetry/cw_replay_reader.py::from_dict` 一处先例），且 `env: PrepExecEnv` 是无缺省自定义类注解（`_annotation_json_serializable` 判不可传）→ `run_operation('...CwActionWearEquipOp', args=...)` 双双构造不出。
- 痛点二（同名歧义）：op 执行体内 `ex._owned_grid_locate(action.item_name)`（`prep_actions.py` L444-462）按名在 owned 网格现读定位拖拽源——`read_equips` 产出同名多条时（实拍：量产型装甲×2）`next(... if n == item_name)` 恒取首个命中，第二条无法指定。
- 痛点三（执行路径 gs/读屏依赖）：`_equip_slot_drag_point`（`prep_actions.py` L414-442）后排分支每帧调 `obs.cw_back_layout.select_back_layout(ctx, screenshot())`（截图+识别）选布局档；op 体内 L96 `game_state_from_ctx` 为自上报取容器。机械定位半与识别半耦合在执行器里，op 无法脱离 env 独立机械化。

## 1. 新参数面定稿

### 1.1 字段集（`kernel/cw_vocab.py::CwActionWearEquipParam` 整体重写）

三分法归属：

| 类别 | 字段 | 语义 |
|---|---|---|
| ③动态坐标 | `src_cx: int`、`src_cy: int` | 拖拽起点 = owned 装备条目格心（1080p 像素）。调用方从观察产物取（MCP agent = extras.owned_equips 元素 `cx/cy`；kernel 发出点 = `gs.owned_equip_xy`，见 §3）。**取值时机 = 调用方读完立刻用**（冻结原则④，op 不做落点前校验） |
| ②半固定槽位 | `row: str`、`slot: int`、`back_slot_count: int` | 目标排槽位保留画面物理坐标域：`row ∈ 'front'|'back'`；`slot` = 排内画面物理槽位 1 基（前排 1-4 / 后排 1-N）；`back_slot_count` = 后排槽位总数 n（值域 6-9，= `obs.cw_back_layout._LAYOUT_PREFIX` 键域），`row='front'` 时忽略（缺省 6）。op 内按下标+槽位总数静态解析拖点，**不再截图选档**（现行 `_equip_slot_drag_point` 后排分支的 `select_back_layout` 现读拔除；布局档 = 纯静态映射 `n → area 前缀`，`cw_back_layout._layout_prefixes()` 公开读口，L359） |
| 语义参数 | `item_name: str = ''`、`char_name: str = ''` | 可选传入。**机械执行路径零消费**（不定位、不校验）；消费面仅两处：①op 日志与 round detail 打印；②kernel 记账载荷——上报函数 `report_action_wear_equip_param` 以 `item_name` 为 owned 摘件记账键、`char_name` 为 `_locate_unit` 身份核对（`kernel/cw_action_report/wear_equip.py`，duck getattr 读字段，字段名全保留 → 该文件零改动）。生产发出点恒传；缺省 '' 时 op 照常拖拽但记账面按既有拒绝语义 `wear_item_not_owned` 拒单（kernel 既有契约，非本批改动面）。`item_name/char_name` 不加 `action_key_exclude`（不同名件 = 不同动作实例，屏蔽幂等键按行为参数含名称更准）；`route_tag` 保留现状（kw_only + `action_key_exclude`，词表 L144-150 全族统一契约，发出点经 `Emitted.reason='m7_equip_transfer'` 归因，route_tag 缺省 '' 不变） |

from_dict 签名（冻结原则⑤；形态 = `cw_replay_reader.from_dict` 同构：只取已声明字段、缺字段落 dataclass 默认值）：

```python
@classmethod
def from_dict(cls, d: dict) -> 'CwActionWearEquipParam':
    """dict → 动作实例(MCP run_operation JSON 通道;只取已声明字段,
    未知键忽略,缺字段落默认值——形态单一源 = cw_replay_reader.from_dict)。"""
    known = {f.name for f in dataclasses.fields(cls)}
    return cls(**{k: v for k, v in d.items() if k in known})
```

必填项 = `src_cx/src_cy/row/slot`（位置参数域）；`back_slot_count/item_name/char_name/route_tag` 带缺省。run_operation args 示例（进 docstring）：

```json
{"src_cx": 1740, "src_cy": 210, "row": "front", "slot": 2,
 "back_slot_count": 6, "item_name": "量产型装甲", "char_name": "银狼"}
```

### 1.2 守卫断言（op 内，参数语义唯一所有者 = op，flow/action-op.md §1 校验落点契约）

保留并扩展三形（全部 `raise AssertionError` 响亮暴露，禁兜底坐标/禁负下标回环）：

1. `row ∉ {'front','back'}` → 断言（现状保留）；
2. `slot` 越界：`not (1 <= slot <= len(该排拖点表))` → 断言（现状保留，槽位总数改为 op 内自 screen_info 现读）；
3. **新增** `row == 'back' 且 back_slot_count ∉ {6,7,8,9}` → 断言（布局档键域外 = 无 area 档可解析，禁静默按 6 兜底）。

### 1.3 `EquipWearStep`（kernel 计划步）零改动裁定

`kernel/cw_equip_wear_plan.py::EquipWearStep(item_name, char_name, row, slot)` 保持不动：计划面 = （件名→目标槽）语义，**不带坐标**——坐标是执行帧观察快照（`gs.owned_equip_xy`），发出点产 param 时现取（同帧性契约，prep-contract §3）。坐标进计划步会把「网格 reflow → 计划失效」通道扩大成坐标陈旧面，违背新鲜度归调用方原则。

### 1.4 坐标记录例外声明同步

`cw_vocab.py` 模块头两处「坐标参数化机械动作（CwActionWearEquipParam/工具原子类）的 row/slot = 画面物理排槽位」例外声明（L11-13、L141-142）更新：WearEquip 升级为「动态坐标显式传 + row/slot 半固定」形态，例外声明收窄为工具原子类；`prep_actions.py` 模块头 L20-23 同款声明同步。

## 2. 牵涉面清单（逐文件）

> 路径根 = `src/sr_od/application/currency_war/`。grep 全量确认的消费点：`CwActionWearEquipParam` 共 33 处引用，其中代码消费 7 文件、注释引用 3 文件。

### 2.1 `kernel/cw_vocab.py` — 参数定义重写

- 改 `class CwActionWearEquipParam`（L499-514）为 §1.1 新字段集：新增 `src_cx/src_cy/back_slot_count`，`item_name/char_name` 改可选（`''` 缺省），保留 `route_tag`；补 `from_dict` 类方法；docstring 重写（含三分法归属注释 + 索引/坐标字段定义注释：坐标系/取值时机/写入端三要素，AGENTS.md §9 硬约束）。
- `CwAction` union（L951）与 `CW_ACTION_TYPES`（L968）：类名不变，零改动。
- 模块头例外声明两处收窄（§1.4）。

### 2.2 `operations/cw_op/cw_wear_equip_action.py` — op 执行体重写

见 §4 执行语义。签名改 `env: PrepExecEnv | None = None`；机械半全部自持（守卫断言/拖点静态派生/显式起点/park_cursor 自持）；`_owned_grid_locate` 消费删除；docstring 按 §6.1 重写。

### 2.3 `operations/cw_op/cw_action_registry.py` — 零改动

import（L71/L153）与注册行（L177）类名不变；`action_op_for`/`action_op_class_for` 组装签名 `(ctx, action, env)` 兼容 env 缺省化。注册完备测试（`test_action_registry`）机械约束对象不变。

### 2.4 `kernel/cw_equip_wear_plan.py` — 新增发出面 helper

新增模块级函数 `wear_param_steps_of(build, gs) -> tuple[list[CwActionWearEquipParam], int]`（单一源，两发出点 mandate/entry 同吃，禁第二份游标口径）：

```python
def wear_param_steps_of(build: EquipPlanBuild, gs: Any
                        ) -> tuple[list, int]:
    """计划步 → 穿装动作参数列表(发出面单点;坐标消费 = gs.owned_equip_xy
    按名取列表 + 本帧 per-name 游标序贯消费——同名多条(量产型装甲×2)
    任意配对合法,件同名无语义差)。坐标候选缺席 = 该步本帧不产
    (计数返回值承载;实机 = 环内新获得件/观察未覆盖,下帧入口观察后
    自然重派;sim = 后端占位坐标恒可得,见 sim-design 同步节)。
    back_slot_count = int(gs.back_layout.value or 6)(与 _build_equip_wear_plan
    计划面 ``_bk_n or 6`` 同口径,双弃权帧缺省语义沿用非新增)。
    kernel 零 app import(形参 duck:build = EquipPlanBuild,gs = 状态容器)。
    """
```

- 游标逻辑：`cursor: dict[str, int]`；每步取 `cands = xy_map.get(item_name) or []`，`k = cursor.get(name, 0)`；`k >= len(cands)` → 跳过计数；否则产 param（`src_cx/src_cy = cands[k]`，游标 +1）。
- 模块 docstring L6-8 机械原语引用更新：机械半宿主描述改为「op 自持静态派生」，`_owned_grid_locate/_equip_slot_drag_point` 引用删除；补「坐标域单一源 = gs.owned_equip_xy（观察装配点写入），本 helper = 发出面唯一消费口」。
- `EquipWearStep` docstring 补一行：「本步不带坐标；坐标 = 发出点经 `wear_param_steps_of` 从状态容器坐标域现取（同帧快照）」。

### 2.5 `strategies/impl/mandate_v1/mandate.py` — M7 发出点改构

- 改 L1036-1044 的 `_step` 循环：`for _step in _build.steps` 产 param 的内联构造改调 `wear_param_steps_of(_build, state)`（`state: GameState` 在 `run_mandate` 形参 L641，零新增取数）：

```python
params, _xy_pending = wear_param_steps_of(_build, state)
for _p in params:
    out.append(Emitted(_p, True, 'm7_equip_transfer'))
if _xy_pending:
    _count('m7_equip_xy_pending')
if not params and not _build.steps:
    pass  # 空计划 NOOP 现状保留
elif not params:
    _count('equip_plan_xy_all_pending')   # 有计划但坐标全缺席(自愈重派帧)
```

- L1069 `equips.sort(...)` 组内序与 `_EQUIP_ATOM_TYPES`（L95-98）：类名不变零改动。
- L57/L96 import 区：补 `wear_param_steps_of` 来源 import（kernel 依赖方向合规：strategies → kernel）。

### 2.6 `strategies/impl/mandate_v1/entry.py` — 第 7 步同构改

- 改 `_step6_equip_tools`（L1146-1155）：同 §2.5 消费 `wear_param_steps_of(build, gs)`（`gs: GameState` 在形参 L1116）；计数键同款进 `counters`。
- L80/L151 import 区同步。

### 2.7 `kernel/cw_game_state.py` — 新字段 `owned_equip_xy`

`GameState` 装备域（L3166 `equips` 邻位）新增：

```python
owned_equip_xy: Field[dict[str, list[tuple[int, int]]]] = field(default_factory=Field)
# 装备库存坐标域(§3.2.15c):名 → 格心坐标列表(1080p;同名多条 = 列表多元素)。
# 观察域字段:唯一写入方 = 备战入口 heavy 观察装配点(整表覆盖,实读坐标)
# + sim 后端占位同步(环境快照,机械段不消费);零逻辑写入方——环内获得件
# 坐标缺席 = 发出面 wear_param_steps_of 跳过自愈,禁获得链回写坐标(写端
# 同步爆炸面,宁缺勿造同 occupied_equips 家族)。
```

语义档：`None` = 观察域未就绪（同 `equips` None 门，M7 计划构造已按 None 走 fail 通道）；`{}` = 真读到空。**不承诺与 `gs.equips` 名单同序/同长**（对齐键 = 名 + 出现序游标消费，§2.4）——「同序不变式」需要全名单写端（获得链/卖出回收/工具上报/效果改写 ≥10 处）同步维护，牵涉面爆炸且无消费必要（同名件可互换，配对无语义差），弃。

### 2.8 `obs/cw_observe_full.py` — heavy 链产物扩展

改 L178-180：同一次 `read_equips` 产出派生第二键（零额外识别开销）：

```python
_eq_hits = read_equips(frame, _eq_sift, equip_rect=_eq_rect4)
out['owned_equips'] = [n for n, _p, _s in _eq_hits]
out['owned_equip_xy'] = {}
for _n, (_cx, _cy), _s in _eq_hits:
    out['owned_equip_xy'].setdefault(_n, []).append((int(_cx), int(_cy)))
```

资源未就绪分支（L170-175 两 warning）：`owned_equip_xy` 同 `owned_equips` 置 None（同门同语义）。heavy 链返回 dict 的消费面（`cw_screen_prep` 装配点、判读脚本）按新键可选读。

### 2.9 `operations/cw_screen/cw_screen_prep.py` — 装配点平行写

改 L403-408 装备库存观察写端，同环同 sig 平行写坐标域（宁缺勿造守卫同族）：

```python
if _of.get('owned_equips') is not None:
    _gs_obs.observe(_gs_obs.equips, list(_of.get('owned_equips')), sig=_prep_sig)
    if _of.get('owned_equip_xy') is not None:
        _gs_obs.observe(_gs_obs.owned_equip_xy, _of.get('owned_equip_xy'), sig=_prep_sig)
```

### 2.10 `kernel/cw_action_report/wear_equip.py` — 零改动

`report_action_wear_equip_param(gs, param: Any, sig)` 与 `_locate_unit` 均 duck getattr 读 `param.item_name/char_name/row/slot`（L248-250）——字段名全保留，签名不变，零改动。docstring 的 param 描述可顺手补一句「param 携显式坐标（src_cx/src_cy，记账面零消费）」，非必需。

### 2.11 `prep_actions.py` — 机械原语退位与注释收敛

- `_owned_grid_locate`（L444-462）与 `_equip_slot_drag_point`（L414-442）：**保留不删**（唯一剩余消费者 = `cw_tool_use_action.py` L146/L153 的工具原子族，本批不动）；两者 docstring/模块头注释（L410-412）更新：「WearEquip 消费已随坐标显式化退役，现役唯一消费者 = 工具原子族（待迁移）」。
- **新增模块级拖点派生函数**（op 消费；`_equip_slot_drag_point` 的静态半提取，工具原子迁移时可复用）：

```python
def row_drag_points(ctx: SrContext, prefix: str,
                    screen_name: str = SCREEN_NAME) -> list[Point]:
    """prefix-N 全排拖点列(avatar 拖点 = rect 中心 x + y1+21,D-36 校准,
    与 _equip_slot_drag_point 同式;区域缺失 = 该排空列,op 内守卫断言
    越界自然暴露,禁兜底坐标)。"""
```

实现 = `_equip_slot_drag_point` 的 front 分支同式（遍历 `si.area_list` 前缀匹配、`int(area_name[len(pfx):])` 升序、`Point((x1+x2)//2, y1+21)`）。后排档前缀由调用方（op）按 `back_slot_count → _layout_prefixes()` 解析后传入，本函数零识别零截图。

### 2.12 测试仓镜像测试 — 见 §5

### 2.13 文档面 — 见 §6

## 3. gs 坐标记录核查结论

**结论：gs 现在不记 owned 装备坐标；观察端坐标已产出但链上两处丢弃。**

- `gs.equips: Field[list[str]]`（`cw_game_state.py` L3166）= 名单，无坐标。
- 观察端坐标源已存在：`read_equips`（`obs/cw_equipment.py` L437-462）返回 `[(name, (cx, cy), score)]`（默认区域 = 装备区标准格 `(1620,90,1918,710)` 走逐格分类，28 帧真值召回 171/171；非默认 rect 走全域 SIFT）。
- 丢弃点 ①：`cw_observe_full.py` L178-180 `[n for n, _p, _s in read_equips(...)]` 只留名字。
- 丢弃点 ②：`gs.equips` 字段形态 = 名单（装配点 `cw_screen_prep.py` L403-408 只写名单）。
- MCP extras 面已带坐标：`obs/recognizers/battle_prep_recognizer.py` L125 契约 `owned_equips: list[dict]`，元素 `{name, category, cx, cy, inliers}`——**MCP agent 直调路径的坐标源现成，零改动**。

**gs 侧扩展设计**（冻结原则⑥）：新观察域字段 `owned_equip_xy`（§2.7 字段形态）；写入端 = 备战入口 heavy 观察装配点（唯一观察写入方，§2.9 平行写）+ sim 后端占位同步（环境快照，见 §7 未决项）；观察链产物扩展 §2.8。**有意不做**的逻辑写端：环内装备获得链（`gain_equipment`/上报函数族）不回写坐标——实机获得时点无画面读数可写（写即造假坐标），全名单写端同步维护是爆炸面；坐标缺席的治理 = 发出面跳过自愈（§2.4），权威重建归下一入口 heavy 观察。此裁定与 `occupied_equips`（§3.2.15b「零逻辑写入方」）同族。

## 4. op 执行语义

### 4.1 现执行路径 gs/读屏依赖清单（迁移前）

| 位置 | 依赖 | 性质 | 迁移处置 |
|---|---|---|---|
| L79 `ex._owned_grid_locate(item_name)` | 截图 + 模板现读定位源件 | 机械定位读屏 | **拔除** → 显式 `src_cx/src_cy` |
| L77 `ex._equip_slot_drag_point(row, slot)` | 内部后排分支 `select_back_layout(ctx, screenshot())` 截图选档 | 机械定位读屏 | **拔除** → `back_slot_count` 参数 + `_layout_prefixes()` 静态映射 + `row_drag_points` 静态解析 |
| L73 `ex._front_pts/_back_pts` | executor 构造时读一次 screen_info | 静态点位表 | **拔除** → op 内 `row_drag_points` 现读（screen_info 静态解析 = 动作本体目标定位合法面） |
| L78 `cw_sim_ports.mechanical_io_allowed()` | sim port 检查 | 非 gs | 保留（族规约） |
| L96 `game_state_from_ctx(self.ctx)` | 自上报取 gs 容器 | 上报路径（非机械定位） | **保留**（op-layer 自上报契约 = 「点完即写」载体；`gs is None` = 无处记账跳过，与 pick 族 L89-96 同形态。冻结原则①拔除对象 = 「gs 可用时走快定位路径」的机械分支，自上报取容器非此类） |

### 4.2 迁移后执行流（op 纯机械化）

1. 守卫断言三形（§1.2）。
2. 拖点静态解析：`prefix = '前排' if row == 'front' else _layout_prefixes()[back_slot_count]`；`pts = row_drag_points(ctx, prefix)`；`target = pts[slot - 1]`。
3. sim 分支：`mechanical_io_allowed()` 为假 → 机械段静默跳过（现状保留，坐标在 sim 无画面语义）。
4. 实机机械段：`mouse_move((src_cx, src_cy))` 防吞点击 → `PREP_DRAG_SETTLE_WAIT_S` 固定等待（非判效）→ `controller.drag_to(start=(src_cx, src_cy), end=target, hold_time=0.5, duration=1.5)` → 1.5s 固定等待（MCP drag 异步落地）——等待常量与拖拽参数逐字沿用现状（拖拽可靠性参数 = 执行层资产，不随迁移变）。
5. `self.park_cursor(after_wait=0.1)`（`CwOperation` 基类方法自带 sim 零光标静默，剥 `ex._op` 依赖）。
6. 自上报：`gs = game_state_from_ctx(...)`；`report_action_wear_equip_param(gs, action, ChannelSig(...))`——签名零改动；round detail 日志含 `item_name/char_name`（语义参数仅存此消费）。
7. round 结果：`round_success(detail)`。**「owned 网格未定位到 …」round_fail 通道消失**——src 显式坐标后 op 无定位失败形态；`prep_actions._PREP_RECEIPT_BLOCK_CODES` L98-102 中 `('owned 网格未定位到', ...)` 泛化行保留（工具原子族仍产出），注释补声明「WearEquip 侧供给已随坐标显式化退役」。

### 4.3 「体内零 CV-diff 验穿」对账语义安置

现状已合规：op 拖后零读屏零落地判定，「穿没穿归观察写入边对账」（上报函数族 = 逻辑态记账单点；失配告警拦停在观察边界 reconcile）。迁移**无额外移交动作**，仅把该语义写清进新 docstring（「机械执行零判效：发出即记账，拖后零读屏；落地归下一入口 heavy 实读对账，重试 = 决策循环按新观察自然重派」）。任务建议「移交观察边」的实质 = 确认对账语义本来就住观察边、op 侧不再因定位失败产生「受阻上报」形态（§4.2 第 7 点）——发出面残余的「坐标缺席跳过」是决策面分支（§2.4），不进 op。

## 5. 测试设计（sr-od-test，按 §11.4 harness 规范）

> ⚠️ 现场实态（2026-11-17 探查）：测试仓 CW 域测试源文件当前不在 git（`git ls-files` 仅 `obs/test_identity_obs.py` 一条 CW 测试；`operations/cw_op/`、`kernel/` 下仅剩本地 `__pycache__` pyc，源 py 缺失，工作区另有并行批在飞改动）。历史布局参照 = pyc 名单（`test_prep_action_ops` / `test_action_registry` / `test_prep_actions` 等）。实施角色按当时仓内实态落位：源文件在则改，不在则按下述路径新建。

按文件镜像规范（`src/foo/bar.py → sr-od-test/test/foo/test_bar.py`）：

1. `test/sr_od/application/currency_war/kernel/cw_vocab/test_cw_vocab.py`（新建或并入既有）
   - `from_dict` 往返：全字段 dict → from_dict → 逐字段断言；最小 dict（必填 4 项）→ `back_slot_count=6/item_name=''/char_name=''/route_tag=''` 缺省断言；未知键忽略断言。
   - `action_key`：同名不同 `item_name` 产不同键（幂等粒度含语义参数）；`route_tag` 不入键（既有 `test_route_tag_whitelist` 面）。
2. `test/sr_od/application/currency_war/kernel/cw_equip_wear_plan/test_wear_param_steps_of.py`（新建）
   - 游标序贯消费：同名两候选 × 两计划步 → 两 param 各取候选[0]/候选[1]；候选 1 条 × 两步 → 第一 param 产、第二跳过计数 = 1；候选缺席（`owned_equip_xy = None/缺名`）→ 全跳过；`back_slot_count` = `int(back_layout or 6)`（含 None → 6）。
   - 纯函数直测（duck 构造 build/gs），零 harness。
3. `test/sr_od/application/currency_war/operations/cw_op/test_cw_wear_equip_action.py`（新建；harness 剧本）
   - 守卫断言三形：row 非法 / slot 越界 / `back_slot_count ∉ {6..9}`（back 行）→ AssertionError。
   - 实机形态（fixture_controller 剧本）：screen_info 档真档案 → 拖拽调用记录断言 `start == (src_cx, src_cy)`、`end == 前排-N rect 中心 x + y1+21`；自上报记账断言（种子 gs：owned 含件 + deployed 目标单位 → 拖后 `owned` −1 + `unit.equips` +1）。
   - `env=None` 形态：构造 + 执行全链（MCP 直调等价路径）。
   - sim 形态：port 关闭 → 机械零调用记录 + 自上报照走。
   - `with fast_sleep(): op.run()` 包裹（§11.4 跳框架等待）。
4. `test/sr_od/application/currency_war/kernel/cw_action_report/test_wear_equip.py`（源在则改）
   - 新 param 形态回归：显式坐标 param 经 `report_action_wear_equip_param` 记账不变（owned −1 + worn 合成链），锁「字段名保留 → 记账零漂移」。
5. `test/sr_od/application/currency_war/operations/cw_screen/`（装配点，源在则改）
   - heavy 产物含 `owned_equip_xy` → 装配点写断言（含同名两件两坐标）。
6. `test_action_registry`（既有面）：零改动预期——类名与行不变；若镜像缺失随新建。

验收阶梯（skill §3）：L1 `uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`；L2 加 `test_action_registry` 点名；L3 全量 commit 前。

## 6. 文档与 skill

### 6.1 op docstring（MCP 使用说明契约，写进 `cw_wear_equip_action.py`）

要点：起点/终点画面、非终结声明、参数表（三分法归属 + 坐标系/取值时机）、run_operation args 示例、零判效语义、自上报说明。骨架（实施角色按此展开，注释规范：中文、为什么、持久索引）：

```
"""穿装备动作 op(CwActionWearEquipOp)——坐标参数化机械动作(显式起点)。
起点:货币战争-备战画面;终点:装备拖至目标角色排槽穿上,停留原画面。
非终结(terminal=False);机械执行零判效:发出即记账,拖后零读屏,
落地归下一入口 heavy 实读对账,重派 = 决策循环按新观察自然承接。

参数面三分法(词表 cw_vocab.CwActionWearEquipParam 为单一源):
- 动态坐标:src_cx/src_cy = owned 装备条目格心(1080p),从最近一帧
  analyze_screen extras.owned_equips 元素 cx/cy 取(读完立刻用,新鲜度归调用方);
- 半固定槽位:row('front'|'back') + slot(排内画面物理槽位 1 基,
  前排 1-4/后排 1-N) + back_slot_count(后排槽数 6-9,front 忽略);
- 语义参数:item_name/char_name 可选,不参与定位与校验,仅日志;
  经 MCP 调用时建议传——kernel 记账(owned 摘件)以 item_name 为键,
  缺省时拖拽照常但记账面按 wear_item_not_owned 拒单。

MCP run_operation 示例:
  args={"src_cx":1740,"src_cy":210,"row":"front","slot":2,
        "back_slot_count":6,"item_name":"量产型装甲","char_name":"银狼"}

同名多条(如同名装备×2):候选按 extras.owned_equips 出现序,逐件分次调用
(每次消费一个坐标);守卫断言:row 非法/slot 越界/back_slot_count 域外
= AssertionError,禁兜底坐标。
"""
```

### 6.2 skill 文档 `skills/sr-od-currency-war/references/screens/货币战争-备战.md` 条目 8 更新

现文案（L13）标注「穿装暂无可靠 agent 路径，待 op 化」→ 新文案：

> 8. 穿装备：`CwActionWearEquipOp {"src_cx":N,"src_cy":N,"row":"front|back","slot":M,"back_slot_count":6,"item_name":"件名","char_name":"角色名"}`——拖装备栏指定装备到场上角色槽位。`src_cx/src_cy` = extras.owned_equips 里目标件元素的 cx/cy（**刚读过就传，读完立刻用**；同名件多条时逐件分次调用，每次用一个坐标）；`slot` = 目标排槽位 1 基（前排 1-4 / 后排 1-N），`back_slot_count` = 后排槽数（extras deploy_cap−4，front 行可省）；`item_name/char_name` 建议传（记账用）。穿完**重读一次 analyze** 对账（owned 少一件 / 目标角色详情装备栏多一件；穿着即合成时合成产物入角色装备栏）。

（实施角色按现行 skill 写作规范润色；「flow 层有专用 op」括注改为 MCP 工具名直引，玩家 skill 只提 MCP 工具。）

### 6.3 开发侧文档

- `docs/develop/sr_od/application/currency_war/game_state/fields.md`：新增 `#### 3.2.15c 装备库存坐标域 owned_equip_xy`（三段式：语义 = 名→格心坐标列表 dict、同名多条列表多元素、1080p；写入方 = 备战入口 heavy 观察装配点整表覆盖（与 equips 同点同环）+ sim 后端占位同步（环境快照）；零逻辑写入方申报与 §3.2.15b 同族——环内获得件坐标缺席 = 发出面跳过自愈）。
- 开发 skill `skills/sr-od-dev-currency-war/references/flow/action-op.md` L122（备战族表 WearEquip 行）改写：「穿装备单步：显式起点坐标（src_cx/src_cy，调用方从 gs.owned_equip_xy / extras 取）→ 拖至目标 row/slot（back 档按 back_slot_count 静态解析，零截图选档）；op 内守卫断言三形；零定位读屏；自上报（owned −1 + 目标角色 equips +1）；发出面坐标缺席 = 计数跳过下帧重派（wear_param_steps_of）」。
- `prep-contract.md` §1 坐标系节 L9「坐标参数化机械动作（WearEquip/工具原子/OpenBox…）」族描述同步收窄（WearEquip 升级动态坐标形态）。
- `sim-design.md` §6.5 旁路章节若列 op 清单：补「WearEquip 坐标显式化后 sim 后端占位坐标同步义务（机械段不消费，禁实机消费占位）」——落点由实施角色按 sim-design 现行结构定位。

## 7. 风险与未决项

1. **行为变化：实机环内新获得件穿戴延后一帧**。现状 op 执行期按名现读定位，同帧买入的件可同帧穿（M7 发出序回排形态）；迁移后决策帧坐标观察快照无新获得件 → 发出面跳过 → 帧终结 → 下一入口 heavy 观察补坐标后重派。穿着即合成的逻辑账（上报投影活账）不受影响，但环内动作序与遥测分键（新增 `m7_equip_xy_pending`/`equip_plan_xy_all_pending`）判读基线变化——实施后首局需对照判读。
2. **sim 占位坐标同步落点未定**。sim 局观察链缺位，`owned_equip_xy` 若无人写则 sim 穿装链全跳过停摆。设计 = sim 后端 tick 层面 reconcile（名单覆盖差 → 占位坐标 append，占位常量 + 「sim 环境快照、机械段不消费」注释）；具体 tick 挂点（后端主循环 vs 装备入栏 hook）由实施角色按 `cw_sim_backend` 现行结构选位并补 sim-design 申报。**未决**。
3. **测试仓 CW 域测试源缺失**（§5 前言）：疑似并行批在飞；实施角色开工前先 `git -C sr-od-test status` 核实，避免与并行批同文件冲突。
4. **MCP agent 拖拽可靠性待实机验证**。skill 条目 8 实测 agent 手动拖拽 4 连败（误弹合成预览/无效果/坐标失效）；op 化走框架拖拽原语（`controller.drag_to` + hover 预处理 + 固定等待）与手动路径不同，预期成立，但 op 化后 MCP 直调的首次实机验证是硬验收——若同症状复现属执行层拖拽链可靠性问题（修参数不回退设计）。
5. **`back_slot_count` 缺省口径沿用的语义张力**：`int(gs.back_layout.value or 6)` 沿用计划面 `_bk_n or 6` 既有缺省（布局未知双弃权帧 → 6 档基线），与 prep-contract「禁 None→6 翻转弃权」裁定存在既有张力（现状如此，非本批新增）；front-only 回退计划的后排扩展帧可能产 6 档拖点。未决：随布局未知态治理批收敛，本批如实沿用。
6. **`read_equips` 双路径坐标质量差**：screen_info `区域-道具装备` rect 与常量 `(1620,90,1918,710)` 一致时走逐格分类（标定充分），漂移时静默切全域 SIFT（坐标质量略异）——坐标域质量由识别层既有标定承载，本批零改动；装配点不校验 rect 一致性（现状即无）。
7. **拖点校准保真**：`y1+21`（D-36 校准）迁移到 `row_drag_points` 必须与 `_equip_slot_drag_point` 逐字同构（单测锁坐标值），防止迁移引入拖点漂移。
8. **`route_tag` 去留裁定**：保留（词表全族统一形态、`action_key_exclude` 幂等语义、kw_only 向后兼容）——删除反而制造词表内特例。
9. **范围边界**：工具原子族（`cw_tool_use_action.py`）消费同款 `_owned_grid_locate`，本批不动（每 op 一个迭代原则）；其迁移时复用 `row_drag_points` 与坐标域模式。

## 8. 实施顺序建议（给实施角色）

1. `cw_vocab.py` 参数面 + `from_dict`（§2.1）→ `cw_game_state.py` 新字段（§2.7）。
2. `cw_observe_full.py` 产物扩展 + `cw_screen_prep.py` 装配点（§2.8/§2.9）。
3. `cw_equip_wear_plan.py` helper（§2.4）→ `mandate.py`/`entry.py` 发出点（§2.5/§2.6）。
4. `prep_actions.py` `row_drag_points`（§2.11）→ `cw_wear_equip_action.py` op 重写（§2.2/§4.2）。
5. 测试五件套（§5）→ 文档三处（§6.3）→ skill 两处（§6.2/6.3）。
6. MCP server 重启 → `describe_operation_flow` 核对 op 节点图 → 实机单件穿装验证（§7.4 硬验收）。
