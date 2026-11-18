# CwActionWearEquipOp（穿装）参数面迁移设计稿（r2 修订版）

> 迭代：CW 动作 op 迁移流水线 · 设计角色产出（agent 1/4）。
> r2 = 按对抗审查（1 blocker + 4 major + 8 minor + 行为变化漏报）修订：B1 采方案 A（穿戴/重观察交替）、M2 拖点派生裁定、M3 sim 写端转本批必做、M4 宪法③例外申报（§9 独立节）、minor 全清。
> 冻结宪法（用户裁定）：①动作 op 执行路径零 gs 依赖（可选快路径全部拔除）；②参数面三分法（固定槽位=下标 / 半固定=下标+槽位总数 / 动态坐标=显式 (cx,cy)+语义参数）；③名称字段=语义参数（可选，不参与校验与定位，仅日志）——**本稿 §9 对宪法③提例外申报，待用户裁决**；④坐标新鲜度纪律归调用方（op 纯机械，不做落点前校验）；⑤参数 dataclass 统一补 `from_dict`；⑥gs 要给实体记录坐标（策略层能拿出具体坐标传参的前提）；⑦每个 op 一个迭代，牵涉面一次改净。

## 0. 现状与痛点（探查实据）

- 参数 `kernel/cw_vocab.py::CwActionWearEquipParam`（L499-514）：`item_name/char_name/row/slot/route_tag`，无 `from_dict`。
- op `operations/cw_op/cw_wear_equip_action.py::CwActionWearEquipOp`：构造签名 `(ctx, param, env: PrepExecEnv)`，env 必填。
- 痛点一（MCP 通道）：`src/sr_od/backend/operation_registry.py::_from_dict_type`（L172-177）规定 run_operation JSON 通道只接受「`@dataclass` + 可调用 `from_dict`」的参数注解——词表 param 全族无 `from_dict`（grep 全 CW 域仅 `telemetry/cw_replay_reader.py::from_dict` 一处先例），且 `env: PrepExecEnv` 是无缺省自定义类注解（`_annotation_json_serializable` 判不可传）→ `run_operation('...CwActionWearEquipOp', args=...)` 双双构造不出。
- 痛点二（同名歧义）：op 执行体内 `ex._owned_grid_locate(action.item_name)`（`prep_actions.py` L444-462）按名在 owned 网格现读定位拖拽源——`read_equips` 产出同名多条时（实拍：量产型装甲×2）`next(... if n == item_name)` 恒取首个命中，第二条无法指定。
- 痛点三（执行路径 gs/读屏依赖）：`_equip_slot_drag_point`（`prep_actions.py` L414-442）后排分支每帧调 `obs.cw_back_layout.select_back_layout(ctx, screenshot())`（截图+识别）选布局档。机械定位半与识别半耦合在执行器里，op 无法脱离 env 独立机械化。
- 痛点四（M2 审查核实的现状两族矛盾）：穿戴目标点 = `前排-N/后排-N` area rect **中心 x + y1+21**（D-36 实机校准背书，现役跑通）；工具 char 模式拖目标 = 同族 area 的 `row_area_centers` rect **裸中心**（`cw_tool_use_action.py` L160-161 消费 `ex._front_pts/_back_pts`；「源码挖掘，待实机核对」，无实机背书）——同一拖拽交互两派生式并存，无裁定记录。

## 1. 新参数面定稿

### 1.1 字段集（`kernel/cw_vocab.py::CwActionWearEquipParam` 整体重写）

三分法归属：

| 类别 | 字段 | 语义 |
|---|---|---|
| ③动态坐标 | `src_cx: int`、`src_cy: int` | 拖拽起点 = owned 装备条目格心（1080p 像素）。调用方从观察产物取（MCP agent = extras.owned_equips 元素 `cx/cy`；kernel 发出点 = `gs.owned_equip_xy`，见 §3）。**取值时机 = 发出面决策帧的坐标域快照；同访问内上一穿戴帧后经环内重观察刷新（§1.5 方案 A）**。op 不做落点前校验（宪法④） |
| ②半固定槽位 | `row: str`、`slot: int`、`back_slot_count: int` | 目标排槽位保留画面物理坐标域：`row ∈ 'front'|'back'`；`slot` = 排内画面物理槽位 1 基（前排 1-4 / 后排 1-N）；`back_slot_count` = 后排槽位总数 n（值域 6-9，= `obs.cw_back_layout._LAYOUT_PREFIX` 键域），`row='front'` 时忽略（缺省 6）。op 内按下标+槽位总数静态解析拖点，**不再截图选档**（布局档 = 纯静态映射 `n → area 前缀`，`cw_back_layout._layout_prefixes()` 公开读口，L359） |
| 语义参数 | `item_name: str = ''`、`char_name: str = ''` | 可选传入。**op 机械执行路径零消费**（不定位、不校验、零分支）；消费面仅两处：①op 日志与 round detail 打印；②kernel 记账载荷——上报函数 `report_action_wear_equip_param` 以 `item_name` 为 owned 摘件记账键、`char_name` 为 `_locate_unit` 身份核对输入。**kernel 记账契约对名称的事实消费构成宪法③例外，独立申报见 §9（待用户裁决）**。两字段缺省语义不同：`item_name=''` → 记账面 `wear_item_not_owned` 拒单（'' 不在 owned）；`char_name=''` → `_locate_unit` 接受（= 穿给该槽现任单位，front-only 回退步既有语义，L257 `not char_name or u.char_id == char_name`），不拒单。生产发出点恒传两字段。`item_name/char_name` 不加 `action_key_exclude`（不同名件 = 不同动作实例，屏蔽幂等键按行为参数含名称更准）；`route_tag` 保留现状（kw_only + `action_key_exclude`，词表 L144-150 全族统一契约，发出点经 `Emitted.reason='m7_equip_transfer'` 归因，route_tag 缺省 '' 不变） |

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
2. `slot` 越界：`not (1 <= slot <= len(该排拖点表))` → 断言（现状保留，槽位总数改为 op 内按档位拖点表现读——注意此处与现状行为有差：现状 `ex._back_pts = row_area_centers(ctx, '后排')` 前缀只匹配基线 `后排-1..6`，后排 7/8/9 槽的计划步今日必被拒（潜在 bug）；迁移后按 `back_slot_count` 档位表取长，slot 7-9 开始可用，行为变化申报见 §7.5）；
3. **新增** `row == 'back' 且 back_slot_count ∉ {6,7,8,9}` → 断言（布局档键域外 = 无 area 档可解析，禁静默按 6 兜底）。

### 1.3 `EquipWearStep`（kernel 计划步）零改动裁定

`kernel/cw_equip_wear_plan.py::EquipWearStep(item_name, char_name, row, slot)` 保持不动：计划面 = （件名→目标槽）语义，**不带坐标**。坐标的时序语义由 §1.5 重观察交替承载——计划步的执行序语义不变（逐帧单件收敛），坐标新鲜度不再依赖「计划步即执行帧」假设（该假设在「同访问多步穿戴 + 穿着即合成 reflow」下不成立，r1 论证错误已修正）。

### 1.4 坐标记录例外声明同步

`cw_vocab.py` 模块头两处「坐标参数化机械动作（CwActionWearEquipParam/工具原子类）的 row/slot = 画面物理排槽位」例外声明（L11-13、L141-142）更新：WearEquip 升级为「动态坐标显式传 + row/slot 半固定」形态，例外声明收窄为工具原子类；`prep_actions.py` 模块头 L20-23 同款声明同步。

### 1.5 坐标新鲜度机制（B1 修复，方案 A：穿戴/重观察交替）

**问题（审查 B1）**：穿戴是「逐帧单件收敛」常态（entry.py `_step6_equip_tools` 注释），多步计划 = 同一访问内连续多帧逐件拖；穿着即合成/网格 reflow aftermath（`prep_actions.py` L67-71、`mandate.py` L1052-1053、`cw_tool_use_action.py` L157 三处建档注释）会移动 owned 网格条目。若第 2 步穿戴仍用入口帧的 `owned_equip_xy` 快照 = 从陈旧坐标盲拖（拖错件 → 账实分裂且实物穿错 / 拖空格静默无效）。现状正确性恰由 op 内按名现读承载（每步重新定位，reflow 天然免疫）——拔除现读后必须补等价的新鲜度机制。

**裁定：方案 A（环内重观察交替）**。同访问内凡发出一帧 `CwActionWearEquipParam`，下一决策帧发 `CwActionObsParam(scope='in_place')` 环内重观察（heavy 观察链重跑 → `owned_equip_xy` 实读整表覆盖 → 坐标刷新），之后才续产下一穿戴步。同构先例 = 部署扫描「拖动与重观察交替」（`entry.py` L726-748：`plan.pending_reobserve` 置位 → 下帧 `Emitted(CwActionObsParam(scope='in_place'), True, 'yield_plan_reobserve')` + 读后清）。

机制设计：

- **载体**：`mandate_state.StrategyState` 新字段 `cw4_wear_pending: bool = False`（发出点写、消费点读后清——与部署扫描读后清同构；session 级生命周期，局间自然清）。fail-safe 方向安全：穿戴 op 异常致标志残留 → 下帧多发一帧 Obs(in_place)（无害重观察）→ 清标志续穿。
- **发出面逻辑**（`wear_param_steps_of` 与 M7/第 7 步的编排，详见 §2.4/§2.5）：
  - `cw4_wear_pending` 在位 → 本帧产 `Obs(in_place)`（清标志），不发穿戴（bridge 单动作发射语义下，本帧即重观察帧）；
  - 标志不在位 → 正常产首穿戴步（坐标 = 现行坐标域快照）+ 置标志。
- **时序展开**（同访问多步穿戴）：帧1 穿 step1（入口快照坐标）→ 帧2 Obs(in_place)（重观察刷新坐标域）→ 帧3 穿 step2'（刷新后坐标）→ … → 计划空帧 NOOP / Obs(outer_loop) 终结访问。环内开销 = 每件穿戴 +1 重观察帧（部署扫描既有同款开销，能力现成）。
- **跳过自愈通道（保留，与方案 A 正交）**：环内新获得件（采晶矿/买牌获得装备）在坐标域无条目 → 发出面跳过该步（计数）→ 该帧无穿戴动作，由既有的「帧稳定截断 → Obs(outer_loop)」通道终结访问重观察后重派。方案 A 管已观察件的 reflow 陈旧；跳过通道管从未观察到的件——两者覆盖不同失效形态，都保留。
- **对「零逻辑写端」申报的影响**：无。方案 A 不给 `owned_equip_xy` 开任何上报侧写端（对比方案 B = 上报 applied 时置 None 失效标记，需修订「零逻辑写端」宪法条款并交用户确认——**不推荐**，理由：①开写端即宪法修订点；②失效→空帧→outer_loop 重观察比 in_place 多一帧；③无先例背书。方案 B 仅作并列申报存档，若用户裁 B 再改设计）。

## 2. 牵涉面清单（逐文件）

> 路径根 = `src/sr_od/application/currency_war/`。grep 全量确认的消费点：`CwActionWearEquipParam` 全部引用 9 文件（审查复核无漏）。

### 2.1 `kernel/cw_vocab.py` — 参数定义重写

- 改 `class CwActionWearEquipParam`（L499-514）为 §1.1 新字段集：新增 `src_cx/src_cy/back_slot_count`，`item_name/char_name` 改可选（`''` 缺省），保留 `route_tag`；补 `from_dict` 类方法；docstring 重写（含三分法归属注释 + 索引/坐标字段定义注释：坐标系/取值时机/写入端三要素；取值时机按 §1.1 表述）。
- `CwAction` union（L951）与 `CW_ACTION_TYPES`（L968）：类名不变，零改动。
- 模块头例外声明两处收窄（§1.4）。

### 2.2 `operations/cw_op/cw_wear_equip_action.py` — op 执行体重写

见 §4 执行语义。签名改 `env: PrepExecEnv | None = None`；机械半全部自持（守卫断言/拖点静态派生/显式起点/park_cursor 自持）；`_owned_grid_locate` 消费删除；docstring 按 §6.1 重写。

### 2.3 `operations/cw_op/cw_action_registry.py` — 零改动

import（L71/L153）与注册行（L177）类名不变；`action_op_for`/`action_op_class_for` 组装签名 `(ctx, action, env)` 兼容 env 缺省化。注册完备测试（`test_action_registry`）机械约束对象不变。

### 2.4 `kernel/cw_equip_wear_plan.py` — 新增发出面 helper

新增模块级函数 `wear_param_steps_of(build, gs) -> tuple[list[CwActionWearEquipParam], int]`（单一源，两发出点 mandate/entry 同吃，禁第二份游标口径）。

**职责裁定**：helper 只管 param 列表（坐标域消费单点）；重观察标志编排（§1.5 的 Obs 构造与标志写读）留在发出点 mandate/entry——标志与 Obs 是策略编排语义，不沉进 kernel helper，helper 保持纯坐标消费函数（kernel 零 app import 契约不受影响）。最终形态：

```python
def wear_param_steps_of(build: EquipPlanBuild, gs: Any
                        ) -> tuple[list[CwActionWearEquipParam], int]:
    """计划步 → 穿装动作参数列表(发出面坐标域消费单点) + 坐标缺席步数。

    坐标消费 = gs.owned_equip_xy 按名取列表 + per-name 游标序贯消费。
    游标为 helper 完备性/MCP 对齐产物:**生产单动作收敛形态下
    (bridge.py decide_prep_screen 只发 actions[0]、余参弃、下帧重算)
    每帧至多产一个 param,游标退化为恒取首候选**;同名多条(量产型
    装甲×2)逐件分帧消费,件同名无语义差,任意配对合法。
    坐标候选缺席 = 该步本帧不产(计数返回值承载;实机 = 环内新获得件/
    观察未覆盖,经帧稳定截断 → Obs outer_loop → 入口 heavy 重观察后
    自然重派;sim = 后端占位同步恒可得,见 §3/§7.2)。
    back_slot_count = int(gs.back_layout.value or 6)(与计划面
    ``_bk_n or 6`` 同口径,双弃权帧缺省沿用非新增)。
    kernel 零 app import(形参 duck:build = EquipPlanBuild,gs = 状态容器)。
    """
    # 实现要点(伪码):
    xy_map = gs.owned_equip_xy.value or {}   # None 守卫(m1):未就绪 → 全跳过
    cursor: dict[str, int] = {}
    params: list = []
    skipped = 0
    for step in build.steps:
        cands = xy_map.get(step.item_name) or []
        k = cursor.get(step.item_name, 0)
        if k >= len(cands):
            skipped += 1
            continue
        cx, cy = cands[k]
        cursor[step.item_name] = k + 1
        params.append(CwActionWearEquipParam(
            src_cx=int(cx), src_cy=int(cy),
            row=step.row, slot=step.slot,
            back_slot_count=int(gs.back_layout.value or 6),
            item_name=step.item_name, char_name=step.char_name))
    return params, skipped
```

- 模块 docstring L6-8 机械原语引用更新：机械半宿主描述改为「op 自持静态派生」，`_owned_grid_locate` 引用删除、`_equip_slot_drag_point` 引用改为「已随本批退役」（§2.11）；补「坐标域单一源 = gs.owned_equip_xy（观察装配点写入），本函数 = 发出面唯一消费口」。
- `EquipWearStep` docstring 补一行：「本步不带坐标；坐标 = 发出点经 `wear_param_steps_of` 从状态容器坐标域取（入口观察快照，穿戴帧间经环内重观察刷新，§1.5）」。

### 2.5 `strategies/impl/mandate_v1/mandate.py` — M7 发出点改构

改 L1030-1044 段（**含重观察交替编排 + 既有计数保全（M1）**）：

```python
        _build = _build_equip_wear_plan(session, registry)
        if _build.fail_reason:
            _count('equip_plan_resource_missing')          # 现状保留
        elif _st.cw4_wear_pending:
            # B1 方案 A:上帧已发穿戴 → 本帧环内重观察(owned_equip_xy
            # 实读刷新)后再续穿;读后清(先例 = entry.py 部署扫描
            # pending_reobserve 形态 L726-728)。本帧计划构造结果丢弃,
            # 不产穿戴。
            _st.cw4_wear_pending = False
            out.append(Emitted(CwActionObsParam(scope='in_place'),
                               True, 'm7_equip_reobserve'))
        else:
            params, _xy_pending = wear_param_steps_of(_build, state)
            for _p in params:
                out.append(Emitted(_p, True, 'm7_equip_transfer'))
            if params:
                _st.cw4_wear_pending = True
            if not _build.steps:
                # 空计划 NOOP 现状保留(M1:既有计数逐字保全,两发出点同构)
                _count('equip_plan_empty_noop')
            if _xy_pending:
                # 计数口径(m3):值 = 本帧被跳过的计划步数(帧粒度事件,
                # 非布尔发生过),键族申报进 cw4_counters 键登记单一源注释。
                _count_xy_pending(_xy_pending)   # 键 = m7_equip_xy_pending
            if _build.steps and not params:
                _count('equip_plan_xy_all_pending')   # 坐标全缺席(自愈重派帧)
```

（`_st = state_of(session)`；`_count_xy_pending` = 带步数的计数写入——实施角色按 `cw4_counters` 现行写法落位。`CwActionObsParam` import 补进 L47-59 区。）

- L1069 `equips.sort(...)` 组内序与 `_EQUIP_ATOM_TYPES`（L95-98）：类名不变零改动（Obs 不入装备原子截断分类，其帧稳定分类按现状面——`CwActionObsParam` 已在 `entry.py` `_CONTINUABLE`/分支拦截域，零新增）。
- L57/L96 import 区：补 `wear_param_steps_of`（kernel）与 `CwActionObsParam`（若未在 import 区）。

### 2.6 `strategies/impl/mandate_v1/entry.py` — 第 7 步同构改

- 改 `_step6_equip_tools`（L1146-1155）：同 §2.5 编排（标志读后清 → Obs(in_place)；否则 helper + 计数），`_st = state_of(session)`，既有 `equip_plan_empty_noop`/`equip_plan_resource_missing` 计数逐字保留（M1：两发出点计数语义不得分叉）。
- L80/L151 import 区同步。

### 2.7 `strategies/impl/mandate_v1/mandate_state.py` — 新载体字段

`StrategyState` 增 `cw4_wear_pending: bool = False`（§1.5 载体；读后清语义、fail-safe 方向、局间生命周期申报进字段注释）。位置与字段注释风格 = 既有 `cw4_counters` 邻域。

### 2.8 `kernel/cw_game_state.py` — 新字段 `owned_equip_xy`

`GameState` 装备域（L3166 `equips` 邻位）新增：

```python
owned_equip_xy: Field[dict[str, list[tuple[int, int]]]] = field(default_factory=Field)
# 装备库存坐标域(§3.2.15c):名 → 格心坐标列表(1080p;同名多条 = 列表多元素)。
# 观察域字段:唯一写入方 = 备战入口 heavy 观察装配点(整表覆盖,实读坐标)
# + sim 后端占位同步(环境快照,机械段不消费);零逻辑写入方——环内获得件
# 坐标缺席 = 发出面跳过自愈,禁获得链回写坐标(写端同步爆炸面,宁缺勿造
# 同 occupied_equips 家族)。
# ⚠️ 与 occupied_equips(审计面,决策零消费)的语义差:本字段 = 决策消费面
# (发出面坐标源),陈旧有行为后果(拖错格)——新鲜度由策略侧穿戴/重观察
# 交替(§1.5)承载,非字段自身保证;消费方禁跨重观察帧复用快照坐标。
```

语义档：`None` = 观察域未就绪（同 `equips` None 门，M7 计划构造已按 None 走 fail 通道）；`{}` = 真读到空。**不承诺与 `gs.equips` 名单同序/同长**（对齐键 = 名 + 出现序游标消费）——「同序不变式」需要全名单写端（获得链/卖出回收/工具上报/效果改写 ≥10 处）同步维护，牵涉面爆炸且无消费必要（同名件可互换，配对无语义差），弃。

### 2.9 `obs/cw_observe_full.py` — heavy 链产物扩展

改 L178-180：同一次 `read_equips` 产出派生第二键（零额外识别开销）：

```python
_eq_hits = read_equips(frame, _eq_sift, equip_rect=_eq_rect4)
out['owned_equips'] = [n for n, _p, _s in _eq_hits]
out['owned_equip_xy'] = {}
for _n, (_cx, _cy), _s in _eq_hits:
    out['owned_equip_xy'].setdefault(_n, []).append((int(_cx), int(_cy)))
```

资源未就绪分支（L170-175 两 warning）：`owned_equip_xy` **不置键**（同现状形态——消费面 `.get()` 得 None，m8 措辞对齐）。

### 2.10 `operations/cw_screen/cw_screen_prep.py` — 装配点平行写

改 L403-408 装备库存观察写端，同环同 sig 平行写坐标域（宁缺勿造守卫同族）：

```python
if _of.get('owned_equips') is not None:
    _gs_obs.observe(_gs_obs.equips, list(_of.get('owned_equips')), sig=_prep_sig)
    if _of.get('owned_equip_xy') is not None:
        _gs_obs.observe(_gs_obs.owned_equip_xy, _of.get('owned_equip_xy'), sig=_prep_sig)
```

### 2.11 `prep_actions.py` — 机械原语退役与拖点权威裁定（M2 修订）

- **`_equip_slot_drag_point`（L414-442）随批退役删除**：本批后全仓零消费者（审查核实：工具 char 模式目标 = `ex._front_pts/_back_pts` 裸中心派生，非本函数；穿戴 op 是唯一消费者且本批拔除）。保留 = 制度化一个与工具族矛盾的拖点派生式（docstring 错误延续），删除 = 根治。退役申报写进 commit message。
- **`_owned_grid_locate`（L444-462）保留**：现役唯一剩余消费者 = `cw_tool_use_action.py` L146/L153（工具 equip 模式源/目标件定位），待工具迁移批处置；其 docstring/模块头注释（L410-412）更新：「WearEquip 消费已随坐标显式化退役，现役唯一消费者 = 工具原子族（待迁移）」。
- **新增模块级拖点派生函数**（op 消费）：

```python
def row_drag_points(ctx: SrContext, prefix: str,
                    screen_name: str = SCREEN_NAME) -> list[Point]:
    """prefix-N 全排 avatar 拖点列(rect 中心 x + y1+21)。

    [拖点派生权威裁定(本批申报)]:+21(D-36 校准)= 穿戴域实机校准背书
    的权威派生式;工具 char 模式现役裸中心派生(cw_tool_use_action
    L160-161 经 row_area_centers)= 无实机背书的历史形态,待工具迁移批
    实机核对后统一按本式(同一「拖到角色卡」交互应同一拖点)。后排档
    前缀由调用方按 back_slot_count → cw_back_layout._layout_prefixes()
    静态解析后传入,本函数零识别零截图。区域缺失 = 该排空列,op 内
    守卫断言越界自然暴露,禁兜底坐标。
    """
```

实现 = 原 `_equip_slot_drag_point` front 分支同式（遍历 `si.area_list` 前缀匹配、`int(area_name[len(pfx):])` 升序、`Point((x1+x2)//2, y1+21)`），单测锁坐标值（§5）。

### 2.12 `sim/cw_sim_backend.py` — 占位坐标同步（M3：转本批必做）

参数面变更落本批，sim 停摆也落本批——占位同步**纳入本批必做**，不留未决：

- 落点 = sim 后端 tick 层（实施角色按 `cw_sim_backend` 主循环现行结构选位，建议挂在对局 tick 后/动作派发前的固定点位），逻辑 = 名单覆盖差 reconcile helper（kernel 侧 `cw_equip_wear_plan` 邻位新增 `sync_owned_equip_xy_placeholder(gs)` 或 sim 内联，实施角色裁量）：

```python
# 语义:名单(gs.equips)有而坐标域(owned_equip_xy)无的名 → append 占位坐标。
# 占位常量 = 装备区 rect 中心附近固定值(如 (1769, 400));sim 环境快照,
# 机械段静默不消费,禁实机消费占位(实机恒观察写真值)。
# 同名已有坐标条目时零动作(不重复 append);观察域 None(未就绪)→ 跳过
# (等观察/名单就绪)。evidence/申报语义 = sim-design §6.5 环境快照族。
```

- `docs/develop/sr_od/application/currency_war/sim/sim-design.md` §6.5 邻域补申报行：「owned_equip_xy = 环境快照字段，sim 后端占位同步（名单覆盖差 append），机械段不消费」。

### 2.13 `data/cw_equipment_data.py` — 注释同步（m6）

L49 注释「与执行边定位读（`prep_actions._owned_grid_locate`，全库模板按名定位）」过期化（WearEquip 退役后该函数仅剩工具族消费）→ 改为语义化表述：「坐标伴随面 = gs.owned_equip_xy（观察装配点写入）；按名定位读现役仅剩工具原子族（`prep_actions._owned_grid_locate`，待迁移）」。

### 2.14 测试仓镜像测试 — 见 §5

### 2.15 文档面 — 见 §6

## 3. gs 坐标记录核查结论

**结论：gs 现在不记 owned 装备坐标；观察端坐标已产出但链上两处丢弃。**

- `gs.equips: Field[list[str]]`（`cw_game_state.py` L3166）= 名单，无坐标。
- 观察端坐标源已存在：`read_equips`（`obs/cw_equipment.py` L437-462）返回 `[(name, (cx, cy), score)]`（默认区域 = 装备区标准格 `(1620,90,1918,710)` 走逐格分类，28 帧真值召回 171/171；非默认 rect 走全域 SIFT）。
- 丢弃点 ①：`cw_observe_full.py` L178-180 `[n for n, _p, _s in read_equips(...)]` 只留名字。
- 丢弃点 ②：`gs.equips` 字段形态 = 名单（装配点 `cw_screen_prep.py` L403-408 只写名单）。
- MCP extras 面已带坐标：`obs/recognizers/battle_prep_recognizer.py` L125 契约 `owned_equips: list[dict]`，元素 `{name, category, cx, cy, inliers}`——**MCP agent 直调路径的坐标源现成，零改动**。

**gs 侧扩展设计**（冻结原则⑥）：新观察域字段 `owned_equip_xy`（§2.8 字段形态）；写入端 = 备战入口 heavy 观察装配点（唯一观察写入方，§2.10 平行写）+ sim 后端占位同步（环境快照，§2.12 本批必做）。**有意不做**的逻辑写端：环内装备获得链（`gain_equipment`/上报函数族）不回写坐标——实机获得时点无画面读数可写（写即造假坐标），全名单写端同步维护是爆炸面；坐标缺席/陈旧的治理 = 策略侧双通道（§1.5：跳过自愈 + 穿戴/重观察交替），权威重建归观察写端。此裁定与 `occupied_equips`（§3.2.15b「零逻辑写入方」）同族，但须注意两字段语义差（§2.8 字段注释已申报）：`occupied_equips` = 决策零消费审计面，`owned_equip_xy` = 决策消费面——陈旧有行为后果，故 §1.5 机制是本字段可用性的必要组成，非可选优化。

## 4. op 执行语义

### 4.1 现执行路径 gs/读屏依赖清单（迁移前）

| 位置 | 依赖 | 性质 | 迁移处置 |
|---|---|---|---|
| L79 `ex._owned_grid_locate(item_name)` | 截图 + 模板现读定位源件 | 机械定位读屏 | **拔除** → 显式 `src_cx/src_cy`（新鲜度由 §1.5 策略侧交替机制补位——现状现读的 reflow 免疫能力由重观察帧等价承接，非裸拔） |
| L77 `ex._equip_slot_drag_point(row, slot)` | 内部后排分支 `select_back_layout(ctx, screenshot())` 截图选档 | 机械定位读屏 | **拔除** → `back_slot_count` 参数 + `_layout_prefixes()` 静态映射 + `row_drag_points` 静态解析（§2.11） |
| L73 `ex._front_pts/_back_pts` | executor 构造时读一次 screen_info | 静态点位表 | **仅拔除 wear op 的消费**；executor 两属性保留（工具 op `cw_tool_use_action.py` L126/L139/L160 仍消费，保留至工具迁移批，m7 措辞） |
| L78 `cw_sim_ports.mechanical_io_allowed()` | sim port 检查 | 非 gs | 保留（族规约） |
| L96 `game_state_from_ctx(self.ctx)` | 自上报取 gs 容器 | 上报路径（非机械定位） | **保留**（op-layer 自上报契约 = 「点完即写」载体；`gs is None` = 无处记账跳过，与 pick 族 L89-96 同形态。冻结原则①拔除对象 = 「gs 可用时走快定位路径」的机械分支，自上报取容器非此类） |

### 4.2 迁移后执行流（op 纯机械化）

1. 守卫断言三形（§1.2）。
2. 拖点静态解析：`prefix = '前排' if row == 'front' else _layout_prefixes()[back_slot_count]`；`pts = row_drag_points(ctx, prefix)`；`target = pts[slot - 1]`。
3. sim 分支：`mechanical_io_allowed()` 为假 → 机械段静默跳过（现状保留，坐标在 sim 无画面语义——sim 恒占位坐标亦不被消费）。
4. 实机机械段：`mouse_move((src_cx, src_cy))` 防吞点击 → `PREP_DRAG_SETTLE_WAIT_S` 固定等待（非判效）→ `controller.drag_to(start=(src_cx, src_cy), end=target, hold_time=0.5, duration=1.5)` → 1.5s 固定等待（MCP drag 异步落地）——等待常量与拖拽参数逐字沿用现状（拖拽可靠性参数 = 执行层资产，不随迁移变）。
5. `self.park_cursor(after_wait=0.1)`（`CwOperation` 基类方法自带 sim 零光标静默，剥 `ex._op` 依赖）。
6. 自上报：`gs = game_state_from_ctx(...)`；`report_action_wear_equip_param(gs, action, ChannelSig(...))`——签名零改动；round detail 日志含 `item_name/char_name`（语义参数仅存此机械面消费）。
7. round 结果：`round_success(detail)`。**「owned 网格未定位到 …」round_fail 通道消失**——src 显式坐标后 op 无定位失败形态；`prep_actions._PREP_RECEIPT_BLOCK_CODES` L98-102 中 `('owned 网格未定位到', ...)` 泛化行保留（工具原子族仍产出），注释补声明「WearEquip 侧供给已随坐标显式化退役」。

### 4.3 「体内零 CV-diff 验穿」对账语义安置

现状已合规：op 拖后零读屏零落地判定，「穿没穿归观察写入边对账」（上报函数族 = 逻辑态记账单点；失配告警拦停在观察边界 reconcile）。迁移**无额外移交动作**，仅把该语义写清进新 docstring（「机械执行零判效：发出即记账，拖后零读屏；落地归下一入口 heavy 实读对账，重试 = 决策循环按新观察自然重派」）。「移交观察边」的实质 = 确认对账语义本来就住观察边、op 侧不再因定位失败产生「受阻上报」形态（§4.2 第 7 点）——发出面残余的「坐标缺席跳过」是决策面分支（§1.5），不进 op。方案 A 的重观察帧同时是既有「观察帧对账」点位（部署扫描先例注释 L713「观察帧对账：自上报推演 vs 实读板面」）——穿戴域获得同款对账点位，为穿着即合成的逻辑账提供环内纠偏窗。

## 5. 测试设计（sr-od-test，按 §11.4 harness 规范）

> ⚠️ 现场实态（2026-11-17 探查）：测试仓 CW 域测试源文件当前不在 git（`git ls-files` 仅 `obs/test_identity_obs.py` 一条 CW 测试；`operations/cw_op/`、`kernel/` 下仅剩本地 `__pycache__` pyc，源 py 缺失，工作区另有并行批在飞改动）。历史布局参照 = pyc 名单（`test_prep_action_ops` / `test_action_registry` / `test_prep_actions` 等）。实施角色按当时仓内实态落位：源文件在则改，不在则按下述路径新建。

按文件镜像规范（`src/foo/bar.py → sr-od-test/test/foo/test_bar.py`）：

1. `test/sr_od/application/currency_war/kernel/cw_vocab/test_cw_vocab.py`（新建或并入既有）
   - `from_dict` 往返：全字段 dict → from_dict → 逐字段断言；最小 dict（必填 4 项）→ `back_slot_count=6/item_name=''/char_name=''/route_tag=''` 缺省断言；未知键忽略断言。
   - `action_key`：同名不同 `item_name` 产不同键（幂等粒度含语义参数）；`route_tag` 不入键（既有 route_tag 白名单校验面——CW 域测试源缺失态下新建时一并补，m4）。
2. `test/sr_od/application/currency_war/kernel/cw_equip_wear_plan/test_wear_param_steps_of.py`（新建；纯函数直测，零 harness）
   - 游标序贯消费：同名两候选 × 两计划步 → 两 param 各取候选[0]/候选[1]（helper 完备性面；生产单动作收敛下恒取首候选，m2）。
   - **None 守卫**：`gs.owned_equip_xy.value = None` → 全跳过、`skipped = len(steps)`（m1）。
   - 候选 1 条 × 两步 → 第一 param 产、第二跳过计数 = 1；候选缺名分支 → 跳过。
   - `back_slot_count` = `int(back_layout or 6)`（含 None → 6、值域 6-9 直通）。
3. `test/sr_od/application/currency_war/operations/cw_op/test_cw_wear_equip_action.py`（新建；harness 剧本）
   - 守卫断言三形：row 非法 / slot 越界 / `back_slot_count ∉ {6..9}`（back 行）→ AssertionError。
   - 实机形态（fixture_controller 剧本，screen_info 真档案 → 期望值从同源 yml 派生）：拖拽调用记录断言 `start == (src_cx, src_cy)`、`end == 前排-N rect 中心 x + y1+21`；自上报记账断言（种子 gs：owned 含件 + deployed 目标单位 → 拖后 `owned` −1 + `unit.equips` +1）。
   - **后排 slot > 6 新行为**：`back_slot_count=7/8/9` + 对应档 area → 拖点落 `后排7槽-N` 族（行为修复锁测，§7.5）。
   - `env=None` 形态：构造 + 执行全链（MCP 直调等价路径）。
   - sim 形态：port 关闭 → 机械零调用记录 + 自上报照走。
   - `with fast_sleep(): op.run()` 包裹（§11.4 跳框架等待）。
4. `test/sr_od/application/currency_war/kernel/cw_action_report/test_wear_equip.py`（源在则改）
   - 新 param 形态回归：显式坐标 param 经 `report_action_wear_equip_param` 记账不变（owned −1 + worn 合成链），锁「字段名保留 → 记账零漂移」。
   - `char_name=''` 分支：row/slot 有效 + 空 char_name → 记账照写（穿给槽现任单位语义，M4 补测）。
5. `test/sr_od/application/currency_war/operations/cw_screen/`（装配点，源在则改）
   - heavy 产物含 `owned_equip_xy` → 装配点写断言（含同名两件两坐标）。
   - **未就绪分支**：装备域资源缺失 → heavy 产物无 `owned_equip_xy` 键、装配点零写（保现值）（审查缺测项补）。
6. 发出面编排（mandate/entry，源在则改）
   - 标志交替：置位帧 → 产 `Obs(in_place)` 且清标志；未置位帧 → 产 WearEquip 且置标志（§1.5 时序锁测）。
   - M1 保全：空计划帧 → `equip_plan_empty_noop` 计数仍发生。
7. `test_action_registry`（既有面）：零改动预期——类名与行不变；若镜像缺失随新建。

验收阶梯（skill §3）：L1 `uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`；L2 加 `test_action_registry` 点名；L3 全量 commit 前。

## 6. 文档与 skill

### 6.1 op docstring（MCP 使用说明契约，写进 `cw_wear_equip_action.py`；M4 修订：两字段分述、零自相矛盾）

```
"""穿装备动作 op(CwActionWearEquipOp)——坐标参数化机械动作(显式起点)。
起点:货币战争-备战画面;终点:装备拖至目标角色排槽穿上,停留原画面。
非终结(terminal=False);机械执行零判效:发出即记账,拖后零读屏,
落地归下一入口 heavy 实读对账,重派 = 决策循环按新观察自然承接。

参数面三分法(词表 cw_vocab.CwActionWearEquipParam 为单一源):
- 动态坐标:src_cx/src_cy = owned 装备条目格心(1080p),从最近一帧
  analyze_screen extras.owned_equips 元素 cx/cy 取(读完立刻用,新鲜度
  归调用方;同访问连穿多件时框架侧每件穿后重观察刷新,读数以最近一帧
  extras 为准);
- 半固定槽位:row('front'|'back') + slot(排内画面物理槽位 1 基,
  前排 1-4/后排 1-N) + back_slot_count(后排槽数 6-9,front 行可省);
- 语义参数(仅机械面日志;kernel 记账载荷,见下两行分述):
  - item_name:建议传——记账摘件键;缺省 '' 时拖拽照常,但记账面按
    wear_item_not_owned 拒单(账不落,下帧对账暴露);
  - char_name:可省——目标定位按 row/slot;传时记账面做身份核对
    (不符 = wear_target_unit_missing 拒单);'' = 穿给该槽现任单位
    (front-only 回退语义,不拒单)。

MCP run_operation 示例:
  args={"src_cx":1740,"src_cy":210,"row":"front","slot":2,
        "back_slot_count":6,"item_name":"量产型装甲","char_name":"银狼"}

同名多条(如同名装备×2):候选按 extras.owned_equips 出现序,逐件分次调用
(每次消费一个坐标;连穿时逐件调用间读最新 extras);守卫断言:row 非法/
slot 越界/back_slot_count 域外 = AssertionError,禁兜底坐标。
"""
```

### 6.2 skill 文档 `skills/sr-od-currency-war/references/screens/货币战争-备战.md` 条目 8 更新

现文案（L13）标注「穿装暂无可靠 agent 路径，待 op 化」→ 新文案：

> 8. 穿装备：`CwActionWearEquipOp {"src_cx":N,"src_cy":N,"row":"front|back","slot":M,"back_slot_count":6,"item_name":"件名","char_name":"角色名"}`——拖装备栏指定装备到场上角色槽位。`src_cx/src_cy` = extras.owned_equips 里目标件元素的 cx/cy（**读最新一帧 extras 就传**；同名件多条时逐件分次调用，每次用一个坐标，连穿多件时每件穿完重读一次 extras 再取下一个坐标）；`slot` = 目标排槽位 1 基（前排 1-4 / 后排 1-N），`back_slot_count` = 后排槽数（extras deploy_cap−4，front 行可省）；`item_name` 建议传（记账摘件用，缺省时拖拽照常但账不落）；`char_name` 可省（省 = 穿给该槽现任角色）。穿完**重读一次 analyze** 对账（owned 少一件 / 目标角色详情装备栏多一件；穿着即合成时合成产物入角色装备栏）。

（实施角色按现行 skill 写作规范润色；玩家 skill 只提 MCP 工具。）

### 6.3 开发侧文档

- `docs/develop/sr_od/application/currency_war/game_state/fields.md`：新增 `#### 3.2.15c 装备库存坐标域 owned_equip_xy`（三段式：语义 = 名→格心坐标列表 dict、同名多条列表多元素、1080p、决策消费面（与 occupied_equips 审计面的语义差）；写入方 = 备战入口 heavy 观察装配点整表覆盖（与 equips 同点同环）+ sim 后端占位同步（环境快照）；零逻辑写入方申报——坐标缺席/陈旧治理 = 策略侧双通道（§1.5））。
- 开发 skill `skills/sr-od-dev-currency-war/references/flow/action-op.md` L122（备战族表 WearEquip 行）改写：「穿装备单步：显式起点坐标（src_cx/src_cy，调用方从 gs.owned_equip_xy / extras 取）→ 拖至目标 row/slot（back 档按 back_slot_count 静态解析，零截图选档）；op 内守卫断言三形；零定位读屏；自上报（owned −1 + 目标角色 equips +1）；发出面 = 穿戴/重观察交替（cw4_wear_pending 标志，先例 = 部署扫描 pending_reobserve）+ 坐标缺席跳过自愈（wear_param_steps_of）」。
- `flow/prep-contract.md` 两处：§1 坐标系节 L9「坐标参数化机械动作（WearEquip/工具原子/OpenBox…）」族描述收窄（WearEquip 升级动态坐标形态）；**L27-28 §3 取值时机节**（m5）：坐标参数化动作取值时机申报表补 WearEquip 行——「src_cx/src_cy = 入口观察快照，同访问内穿戴帧间经环内重观察（Obs in_place）刷新；row/slot/back_slot_count = 生成期快照（无 expect 代际校验前提同族）」；§6 活缺口 G1 行补注：WearEquip 已随坐标域 + 重观察交替补防线，G1 现役辖域收窄为工具原子/开件族。
- `docs/develop/sr_od/application/currency_war/sim/sim-design.md` §6.5 邻域：补「owned_equip_xy = 环境快照字段，sim 后端占位同步（名单覆盖差 append），机械段不消费，禁实机消费占位」（§2.12）。
- `kernel/cw_action_report/wear_equip.py` 模块 docstring 可顺手补一句「param 携显式坐标（src_cx/src_cy，记账面零消费）」，非必需。

## 7. 风险与行为变化清单

1. **行为变化：实机环内新获得件穿戴延后一帧**（现状 op 执行期按名现读可同帧穿新获得件；迁移后坐标域无该件条目 → 发出面跳过 → 帧终结重观察后重派）。逻辑账（上报投影活账）不受影响；遥测分键基线变化（新增 `m7_equip_xy_pending`/`equip_plan_xy_all_pending`/`m7_equip_reobserve`），首局需对照判读。
2. **行为变化：每件穿戴 +1 环内重观察帧**（方案 A 交替；先例 = 部署扫描同款开销）。单访问耗时上界上浮（重观察帧耗时 ≈ heavy 链），visit 动作数预算内自收敛；效率剖析按「一局时间花在哪」口径关注备战访问时长变化。
3. **sim 穿装链保活（M3，本批必做）**：占位坐标同步（§2.12）随批落，不合入即 sim 穿装全跳过停摆——实施顺序 §8 第 4.5 步与 sim 改动同批 commit，缺一不合。
4. **MCP agent 拖拽可靠性待实机验证**：skill 条目 8 实测 agent 手动拖拽 4 连败（误弹合成预览/无效果/坐标失效）；op 化走框架拖拽原语（`controller.drag_to` + hover 预处理 + 固定等待）与手动路径不同，预期成立，但 op 化后 MCP 直调的首次实机验证是硬验收——若同症状复现属执行层拖拽链可靠性问题（修参数不回退设计）。
5. **行为变化（潜在 bug 修复）：后排 slot 7-9 从必拒变可用**。现状 op 守卫槽位总数 = `row_area_centers(ctx, '后排')` 表长（前缀只匹配基线 `后排-1..6`，实测建档），后排 7/8/9 槽计划步（计划面 `_bk_n or 6` 可产）今日必被 AssertionError 拒掉；迁移后守卫按 `back_slot_count` 档位拖点表长，slot 7-9 开始可用。判读基线：后排扩展局（宝钻/召唤物扩展）的穿戴计划完成率预期上升；此为隐藏行为修复，供对照。
6. **`back_slot_count` 缺省口径沿用的语义张力**：`int(gs.back_layout.value or 6)` 沿用计划面 `_bk_n or 6` 既有缺省（布局未知双弃权帧 → 6 档基线），与 prep-contract「禁 None→6 翻转弃权」裁定存在既有张力（现状如此，非本批新增）；front-only 回退计划的后排扩展帧可能产 6 档拖点。未决：随布局未知态治理批收敛，本批如实沿用。
7. **`read_equips` 双路径坐标质量差**：screen_info `区域-道具装备` rect 与常量 `(1620,90,1918,710)` 一致时走逐格分类（标定充分），漂移时静默切全域 SIFT（坐标质量略异）——坐标域质量由识别层既有标定承载，本批零改动。
8. **拖点校准保真**：`y1+21`（D-36 校准）迁移到 `row_drag_points` 必须与原 `_equip_slot_drag_point` 逐字同构（单测锁坐标值），防迁移引入拖点漂移。**拖点权威裁定（M2）**：+21 校准式为该 area 拖点权威派生；工具 char 模式裸中心派生 = 无实机背书历史形态，工具迁移批实机核对后统一（§2.11 申报）。
9. **`route_tag` 去留裁定**：保留（词表全族统一形态、`action_key_exclude` 幂等语义、kw_only 向后兼容）。
10. **范围边界**：工具原子族（`cw_tool_use_action.py`）消费 `_owned_grid_locate` 与 `ex._front_pts/_back_pts`，本批不动（每 op 一个迭代原则）；其迁移时复用 `row_drag_points`（+21 权威式）与坐标域模式。

## 8. 实施顺序建议（给实施角色）

1. `cw_vocab.py` 参数面 + `from_dict`（§2.1）→ `cw_game_state.py` 新字段（§2.8）。
2. `cw_observe_full.py` 产物扩展 + `cw_screen_prep.py` 装配点（§2.9/§2.10）。
3. `cw_equip_wear_plan.py` helper（§2.4）→ `mandate_state.py` 载体字段（§2.7）→ `mandate.py`/`entry.py` 发出点编排（§2.5/§2.6）。
4. `prep_actions.py` `row_drag_points` + `_equip_slot_drag_point` 退役（§2.11）→ `cw_wear_equip_action.py` op 重写（§2.2/§4.2）→ **sim 占位同步（§2.12，与本批同 commit，缺一不合）** → `cw_equipment_data.py` 注释同步（§2.13）。
5. 测试七件套（§5）→ 文档四处（§6.3）→ skill 两处（§6.2/6.3）。
6. MCP server 重启 → `describe_operation_flow` 核对 op 节点图 → 实机单件穿装验证（§7.4 硬验收）+ 后排扩展局 slot 7-9 验证（§7.5）。

## 9. 宪法③例外申报（独立节，转呈用户裁决，r2 新增）

**申报事项**：穿装动作的名称字段（`item_name`/`char_name`）在 kernel 记账层的事实消费，构成宪法③「名称字段……不参与任何校验与定位，仅用于决定 op 日志打印内容」的例外。

**事实陈述**（代码实据）：
- `kernel/cw_action_report/wear_equip.py::report_action_wear_equip_param` L330：以 `param.item_name` 做 owned 在库校验（`wear_item_not_owned` 拒单零写）；
- 同文件 `_locate_unit` L257：以 `param.char_name` 做目标身份核对（不符 = `wear_target_unit_missing` 拒单零写；**空 char_name 接受** = 穿给槽现任单位）。

**例外理由**：
1. 宪法③的立法意图 = 名称不参与 **op 机械执行面**（定位拖拽目标）的校验与定位——迁移后 op 内对两字段零消费（不定位、不校验、零分支），机械面完全合规；
2. kernel 上报函数族 = 「点完即写」的逻辑态记账单点（op-layer 契约），`item_name` 是记账载荷（owned 摘哪件、合成用什么件——没有名称记账无法进行），其拒绝语义（`wear_item_not_owned` 等）是对账面防线，属 kernel 既有契约，非 op 机械路径的校验；
3. 替代方案（记账改按坐标摘件）不成立：逻辑态 `gs.equips` 是名字列表，坐标不进逻辑账；按「坐标→名」反查 = 把观察面坐标当记账键，观察覆盖后坐标漂移即错账。

**申报诉求**：裁定宪法③对 WearEquip 的 kernel 记账消费是否豁免（本设计按「豁免」拟制——机械面合规 + 记账面例外申报存档；若用户裁定不豁免，备选 = 上报函数族改名语义字段如 `item_ref`/`target_ref` 以示与机械定位名称的区别，属后续迭代）。
