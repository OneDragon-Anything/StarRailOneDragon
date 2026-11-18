# CwActionWearEquipOp（穿装）参数面迁移设计稿（r3 修订版）

> 迭代：CW 动作 op 迁移流水线 · 设计角色产出（agent 1/4）。
> r2 = 对抗审查修订（B1 重观察交替 / M2 拖点裁定 / M3 sim 必做 / M4 宪法③例外申报 / m1-m8 全清）。
> r3 = 按**用户架构裁定**重写记账域：r2 §9 豁免申报路线作废，记账路径改为「op 上报坐标 → kernel 坐标伴随域反查内容 → 名字降级为反查产物；名称校验删除」。存活节（§1.5 方案 A 机制、M1 遥测保全、M2 拖点退役/裁定、M3 sim 同步必做、m1-m8、§7.5 行为修复申报）复审已核销，原样继承。
> 冻结宪法（用户裁定）：①动作 op 执行路径零 gs 依赖；②参数面三分法；③名称字段=语义参数（可选，不参与校验与定位，仅日志）——**r3 起记账面亦零消费，宪法③原样成立无例外（§9 对齐申报）**；④坐标新鲜度纪律归调用方；⑤参数 dataclass 统一补 `from_dict`；⑥gs 给实体记录坐标（坐标伴随域）；⑦每个 op 一个迭代，牵涉面一次改净。

## 0. 用户架构裁定（记账路径总契约，r3 新增总纲）

> 「动作 op 上报坐标，game state 里根据坐标找到具体的内容，自然就知道是什么了，动作 op 依然保持机械执行。」——用户裁定原文

落地含义（**动作注册表全集（`cw_action_registry.py` 全行）迁移的记账路径总契约**，本稿成文为一般性契约，后续 op 迁移继承不再逐个报批；wear-equip = 第一个适用者）：

1. op 上报它实际动过的坐标（`src_cx/src_cy`），kernel 记账层用观察产出的坐标伴随域对照表（`owned_equip_xy`，名字↔坐标）**反查**出具体内容再记账——名字从「记账键」降级为「反查产物」。
2. 名称校验移除：`wear_item_not_owned`（owned 名单校验）与 `_locate_unit` 的 char_name 身份核对整个删掉，换「反查不到 → 拒单零写 → 跳过自愈通道」。目标单位身份改由槽位反查（gs 知道该槽现任是谁；槽空 = 拒单）。
3. 宪法③原条文原样成立、无例外：名称字段在 op 机械面与 kernel 记账面均零消费，op 参数里的名字只剩日志语义（§9 对齐申报）。
4. 反查前提与窗口纪律 = 三条一句话级申报（§1.5 契约段 + op docstring 双落点）：
   - **反查时序不变式**：上报反查消费拖前快照；重观察刷新必须晚于上报；
   - **陈旧窗口禁消费**：记账后 → 重观察前的坐标伴随域陈旧条目窗口禁消费——由 `cw4_wear_pending` 交替保证（§1.5）；
   - **反查唯一性前提**：同一快照内坐标↔条目一一对应（单格单件）；MCP 直调陈旧坐标反查不到 = 拒单（round detail 带拒单码），**拒单后禁止补拖、连穿无对照表刷新手段则按单件会话使用**（§1.5 契约 3 + MCP 直调形态边界）。

## 1. 新参数面定稿

### 1.1 字段集（`kernel/cw_vocab.py::CwActionWearEquipParam` 整体重写）

三分法归属：

| 类别 | 字段 | 语义 |
|---|---|---|
| ③动态坐标 | `src_cx: int`、`src_cy: int` | 拖拽起点 = owned 装备条目格心（1080p 像素），**兼记账反查键**（kernel 上报层用它从坐标伴随域反查装备名，§0 总契约）。调用方从观察产物取（MCP agent = extras.owned_equips 元素 `cx/cy`；kernel 发出点 = `gs.owned_equip_xy`）。**取值时机 = 发出面决策帧的坐标伴随域快照；同访问内上一穿戴帧后经环内重观察刷新（§1.5）**。op 不做落点前校验（宪法④） |
| ②半固定槽位 | `row: str`、`slot: int`、`back_slot_count: int` | 目标排槽位保留画面物理坐标域：`row ∈ 'front'|'back'`；`slot` = 排内画面物理槽位 1 基（前排 1-4 / 后排 1-N），**兼记账目标定位键**（`_locate_unit` 按 row/slot 反查槽现任单位）；`back_slot_count` = 后排槽位总数 n（值域 6-9，= `obs.cw_back_layout._LAYOUT_PREFIX` 键域），`row='front'` 时忽略（缺省 6）。op 内按下标+槽位总数静态解析拖点，不再截图选档（布局档 = 纯静态映射 `n → area 前缀`，`cw_back_layout._layout_prefixes()` 公开读口） |
| 语义参数 | `item_name: str = ''`、`char_name: str = ''` | 可选传入。**机械执行面与 kernel 记账面均零消费**（r3：记账改坐标反查，名称校验与身份核对删除）——名称字段唯一消费 = op 日志与 round detail 打印，纯日志语义，宪法③原样成立无例外（§9 对齐申报）。缺省 '' 行为完全一致（记账不读名称）。生产发出点恒传（日志归因可读性）。`item_name/char_name` 不加 `action_key_exclude`（不同名件 = 不同动作实例，屏蔽幂等键按行为参数含名称更准——名称进键不影响零消费裁定，键是屏蔽计数面非消费面）；`route_tag` 保留现状（kw_only + `action_key_exclude`，词表 L144-150 全族统一契约） |

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

`kernel/cw_equip_wear_plan.py::EquipWearStep(item_name, char_name, row, slot)` 保持不动：计划面 = （件名→目标槽）语义，不带坐标。坐标的时序语义由 §1.5 重观察交替承载——计划步的执行序语义不变（逐帧单件收敛），坐标新鲜度不再依赖「计划步即执行帧」假设。

### 1.4 坐标记录例外声明同步

`cw_vocab.py` 模块头两处「坐标参数化机械动作（CwActionWearEquipParam/工具原子类）的 row/slot = 画面物理排槽位」例外声明（L11-13、L141-142）更新：WearEquip 升级为「动态坐标显式传 + row/slot 半固定」形态，例外声明收窄为工具原子类；`prep_actions.py` 模块头 L20-23 同款声明同步。

### 1.5 坐标伴随域新鲜度机制（B1 方案 A：穿戴/重观察交替；r3 补三条契约申报 + A1 假设申报）

**问题**：穿戴是「逐帧单件收敛」常态（entry.py `_step6_equip_tools` 注释），多步计划 = 同一访问内连续多帧逐件拖；穿着即合成/网格 reflow aftermath（`prep_actions.py` L67-71、`mandate.py` L1052-1053、`cw_tool_use_action.py` L157 三处建档注释）会移动 owned 网格条目。若第 2 步穿戴仍用入口帧的 `owned_equip_xy` 快照 = 从陈旧坐标盲拖（拖错件 → 账实分裂且实物穿错 / 拖空格静默无效）。现状正确性恰由 op 内按名现读承载——拔除现读后必须补等价的新鲜度机制。

**裁定：方案 A（环内重观察交替）**。同访问内凡发出一帧 `CwActionWearEquipParam`，下一决策帧发 `CwActionObsParam(scope='in_place')` 环内重观察（heavy 观察链重跑 → `owned_equip_xy` 实读整表覆盖 → 坐标伴随域刷新），之后才续产下一穿戴步。同构先例 = 部署扫描「拖动与重观察交替」（`entry.py` L726-748：`plan.pending_reobserve` 置位 → 下帧 `Emitted(CwActionObsParam(scope='in_place'), True, 'yield_plan_reobserve')` + 读后清）。

机制设计：

- **载体**：`mandate_state.StrategyState` 新字段 `cw4_wear_pending: bool = False`（发出点写、消费点读后清——与部署扫描读后清同构；session 级生命周期，局间自然清）。fail-safe 方向安全：穿戴 op 异常致标志残留 → 下帧多发一帧 Obs(in_place)（无害重观察）→ 清标志续穿。
- **发出面逻辑**（§2.5/§2.6 编排）：标志在位 → 本帧产 `Obs(in_place)`（清标志）；标志不在位 → 产首穿戴步（坐标 = 现行坐标伴随域快照）+ 置标志。
- **时序展开**（同访问多步穿戴）：帧1 穿 step1（入口快照坐标）→ 帧2 Obs(in_place)（重观察刷新）→ 帧3 穿 step2'（刷新后坐标）→ … → 计划空帧 NOOP / Obs(outer_loop) 终结访问。环内开销 = 每件穿戴 +1 重观察帧（部署扫描既有同款开销，能力现成；末件穿戴后仍发一帧重观察 = 每访问一次冗余 heavy，成本申报见 §7.2，不改）。
- **跳过自愈通道（保留，与方案 A 正交）**：环内新获得件（采晶矿/买牌获得装备）在坐标伴随域无条目 → 发出面跳过该步（计数）→ 该帧无穿戴动作，由既有的「帧稳定截断 → Obs(outer_loop)」通道终结访问重观察后重派。方案 A 管已观察件的 reflow 陈旧；跳过通道管从未观察到的件——两者覆盖不同失效形态，都保留。
- **对「禁逻辑写端」申报的影响**：无。方案 A 不给 `owned_equip_xy` 开任何策略/动作侧写端（r2 方案 B = 上报置 None 失效标记的备选已随 r3 架构裁定作废——新记账路径下反查拒单 + 跳过自愈天然覆盖失效形态，无需失效写端）。

**契约段（三条一句话级申报，双落点 = 本节 + op docstring §6.1；r4 修订含拒单处置指引改写）**：

1. **反查时序不变式**：上报反查消费**拖前快照**（op 执行拖拽所用的坐标伴随域快照 = 上报反查所读的同一份）；重观察刷新必须**晚于**上报（先记账后刷新——反读到的是「拖拽当时语义上的那件」）。
2. **陈旧窗口禁消费**：记账（上报）完成 → 重观察刷新之间，坐标伴随域存在陈旧条目窗口；该窗口内的条目**禁被任何发出/记账消费**——由 `cw4_wear_pending` 交替保证（标志帧只产 Obs 不产穿戴，窗口内无第二次消费）。新架构下该纪律加重：窗口内陈旧条目若被反查消费即错账（拖的是 reflow 前的格、账记的是反查产物），非仅拖错格。
3. **反查唯一性前提与拒单处置**：同一快照内坐标↔条目一一对应——**观察路径由逐格分类器保证**（28 固定格单格单件产出）、**sim 占位路径由唯一化方案保证**（§2.13 基值+序号偏移，同值即冲突）。反查不到（坐标不在表/伴随域未就绪）= `wear_item_xy_unresolved` 拒单零写；**拒单发生在拖拽之后，拒单后禁止补拖**（拖拽已发生，再拖 = 二次拖拽事故）——处置 = 刷新对照表后重试（刷新手段 = 重跑备战观察链，框架路径即交还决策循环经观察链自然重派；直调方无刷新手段，见下方形态边界）；**连穿场景每件之间需要一次对照表刷新，无刷新手段的调用方（MCP 直调，见 §6.1）按单件会话使用**。形态归类补充：反查**命中**但名单缺条目 = 禁消费窗口违反（契约 2），以异常响亮暴露（零防御纪律，`owned.remove` ValueError），非拒单路径。

**MCP 直调路径的形态边界（M-r3-1 申报）**：直调方无对照表刷新手段——`CwActionObsOp` 直调 = 宿主能力缺失 AssertionError（`cw_action_registry.py` L192-195 注册行注释明示），`analyze_screen` 为只读工具不写 gs。因此直调路径：①第二件连穿的「重读 extras 取新坐标」**解不了表陈旧**（坐标新、表旧 → 反查恒不中拒单，且永远拒单）；②唯一安全用法 = 单件会话（一坐标一调用一观察对账，连穿交还框架决策循环——框架路径有交替机制保证表刷新）；③拒单感知 = round detail 拒单事实（§2.2/§4.2 步骤 6，直调方按 detail 拒单码停手，禁止按旧坐标重试 = 盲拖错格 + 错账）。

**A1 假设申报（入口观察后、首穿前的环内动作用隔）**：交替机制只覆盖「穿戴帧之后」的 reflow；入口观察后、首穿前若有改变 owned 网格的环内动作（采晶矿获得件最常见），首穿仍用入口快照坐标。**申报假设：获得件插入只占空格、已登记条目格位不动**（逐格分类器 28 固定格结构支持——新件落空格、旧件格位不变——但**无实机背书**）。验收实机验证（§8.6「采晶矿→穿装」序列）；实测不成立的回退方案 = 获得类动作（CollectOre 等）发出帧后也置 `cw4_wear_pending`（交替机制扩展到获得类 aftermath，机制零新增）。

## 2. 牵涉面清单（逐文件）

> 路径根 = `src/sr_od/application/currency_war/`。grep 全量确认的消费点：`CwActionWearEquipParam` 全部引用 9 文件。

### 2.1 `kernel/cw_vocab.py` — 参数定义重写

- 改 `class CwActionWearEquipParam`（L499-514）为 §1.1 新字段集：新增 `src_cx/src_cy/back_slot_count`，`item_name/char_name` 改可选（`''` 缺省），保留 `route_tag`；补 `from_dict` 类方法；docstring 重写（三分法归属 + 索引/坐标字段定义注释三要素 + §0 三条契约申报摘要）。
- `CwAction` union（L951）与 `CW_ACTION_TYPES`（L968）：类名不变，零改动。
- 模块头例外声明两处收窄（§1.4）。

### 2.2 `operations/cw_op/cw_wear_equip_action.py` — op 执行体重写

见 §4 执行语义。签名改 `env: PrepExecEnv | None = None`；机械半全部自持（守卫断言/拖点静态派生/显式起点/park_cursor 自持）；`_owned_grid_locate` 消费删除；docstring 按 §6.1 重写（含三条契约申报）。

**op 侧唯一新增改动（M-r3-1 修法①）：round detail 携带记账拒单码**——现状 op 丢弃 `report_action_wear_equip_param` 返回的 `LogicOutcome`（L96-101），r3 后上报函数可拒单（`wear_item_xy_unresolved`，拖拽已发生账未落），round detail 恒「已发」会让直调方无从感知拒单。改法：op 消费 outcome，`applied=False` 时 detail 追加拒单事实（机械 `round_success` 语义不变——拖拽确实已发生；不分支重试、不读屏验证，仅如实上报动作事实，零判效/零重试纪律不受触及；`gs is None` 无 outcome 时 detail 不变）：

```python
        outcome = report_action_wear_equip_param(gs, action, ChannelSig(...))
        detail = f'穿戴 → ({action.row}-{action.slot}) 已发(发出即记账,落地归观察对账)'
        if outcome is not None and not outcome.applied:
            detail += f'；记账拒单:{outcome.reason}(拖拽已发生,账未落)'
        log.info(f'[cw][wear] {detail}')
        return self.round_success(detail)
```

除此外机械半与 r2 形态一致（上报函数签名不变，`param: Any` duck）。

### 2.3 `operations/cw_op/cw_action_registry.py` — 零改动

import（L71/L153）与注册行（L177）类名不变；组装签名兼容 env 缺省化。注册完备测试机械约束对象不变。

### 2.4 `kernel/cw_equip_wear_plan.py` — 新增发出面 helper

新增模块级函数 `wear_param_steps_of(build, gs) -> tuple[list[CwActionWearEquipParam], int]`（单一源，两发出点 mandate/entry 同吃，禁第二份游标口径）。

**职责裁定**：helper 只管 param 列表（坐标伴随域消费单点）；重观察标志编排（§1.5 的 Obs 构造与标志写读）留在发出点 mandate/entry——标志与 Obs 是策略编排语义，不沉进 kernel helper，helper 保持纯坐标消费函数（kernel 零 app import 契约不受影响）。最终形态：

```python
def wear_param_steps_of(build: EquipPlanBuild, gs: Any
                        ) -> tuple[list[CwActionWearEquipParam], int]:
    """计划步 → 穿装动作参数列表(发出面坐标伴随域消费单点) + 坐标缺席步数。

    坐标消费 = gs.owned_equip_xy 按名取列表 + per-name 游标序贯消费。
    游标为 helper 完备性/MCP 对齐产物:**生产单动作收敛形态下
    (bridge.py decide_prep_screen 只发 actions[0]、余参弃、下帧重算)
    每帧至多产一个 param,游标退化为恒取首候选**;同名多条(量产型
    装甲×2)逐件分帧消费,件同名无语义差,任意配对合法。
    坐标候选缺席 = 该步本帧不产(计数返回值承载;实机 = 环内新获得件/
    观察未覆盖,经帧稳定截断 → Obs outer_loop → 入口 heavy 重观察后
    自然重派;sim = 后端占位同步恒可得,见 §2.13/§7.3)。
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

**与记账面反查的两道防线关系（r3 申报；r4 精确化）**：发出面预检（本 helper 坐标缺席跳过）与记账面反查拒单（`wear_item_xy_unresolved`，§2.11）= 同一失效形态的两道防线——发出面用同一坐标伴随域预检，同帧下反查必命中。**kernel 生产路径预检漏网不可达**（emit 与 report 同宿主迭代内同步执行、零中间写端，复审已核）——第二道防线的实际生效面 = **MCP 直调路径**（直调坐标脱离发出面预检，由反查拒单 + round detail 拒单码承接，§6.1），勿据本段误判 kernel 存在竞态面。

- 模块 docstring L6-8 机械原语引用更新：机械半宿主描述改为「op 自持静态派生」，`_owned_grid_locate` 引用删除、`_equip_slot_drag_point` 引用改为「已随本批退役」（§2.11）；补「坐标伴随域单一源 = gs.owned_equip_xy（观察装配点写入），本函数 = 发出面唯一消费口」。
- `EquipWearStep` docstring 补一行：「本步不带坐标；坐标 = 发出点经 `wear_param_steps_of` 从状态容器坐标伴随域取（入口观察快照，穿戴帧间经环内重观察刷新，§1.5）」。

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
            # 不产穿戴——§1.5 契约 2(陈旧窗口禁消费)的执行点。
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

- L1069 `equips.sort(...)` 组内序与 `_EQUIP_ATOM_TYPES`（L95-98）：类名不变零改动。
- L57/L96 import 区：补 `wear_param_steps_of`（kernel）与 `CwActionObsParam`（若未在 import 区）。

### 2.6 `strategies/impl/mandate_v1/entry.py` — 第 7 步同构改

- 改 `_step6_equip_tools`（L1146-1155）：同 §2.5 编排（标志读后清 → Obs(in_place)；否则 helper + 计数），`_st = state_of(session)`，既有 `equip_plan_empty_noop`/`equip_plan_resource_missing` 计数逐字保留（M1：两发出点计数语义不得分叉）。
- L80/L151 import 区同步。

### 2.7 `strategies/impl/mandate_v1/mandate_state.py` — 新载体字段

`StrategyState` 增 `cw4_wear_pending: bool = False`（§1.5 载体；读后清语义、fail-safe 方向、局间生命周期申报进字段注释）。位置与字段注释风格 = 既有 `cw4_counters` 邻域。

### 2.8 `kernel/cw_game_state.py` — 新字段 `owned_equip_xy`（坐标伴随域）

`GameState` 装备域（L3166 `equips` 邻位）新增（定名与写端条款 = 并行批规范 strategy-contract §4 / screen-op §2「坐标伴随域」，§6.3 引）：

```python
owned_equip_xy: Field[dict[str, list[tuple[int, int]]]] = field(default_factory=Field)
# 装备库存坐标伴随域(§3.2.15c):名 → 格心坐标列表(1080p;同名多条 = 列表多元素)。
# 观察域字段:唯一观察写入方 = 备战入口 heavy 观察装配点(整表覆盖,实读坐标)
# + sim 后端占位同步(环境快照通道,机械段不消费;先例 = sim 环境条件发放
# 对 diamond_count/back_layout 的 sim 侧写通道);禁策略/动作逻辑写端——
# 环内获得件坐标缺席 = 发出面跳过自愈,禁回填猜值(规范 screen-op §2 同款)。
# ⚠️ 与 occupied_equips(审计面,决策零消费)的语义差:本字段 = 决策消费面
# (发出面坐标源 + 记账面反查键,r3)——陈旧有行为后果(拖错格/错账),
# 新鲜度由策略侧穿戴/重观察交替(§1.5 三条契约)承载;消费方禁跨重观察帧
# 复用快照坐标。
```

语义档：`None` = 观察域未就绪（同 `equips` None 门，M7 计划构造已按 None 走 fail 通道；反查面同样按 None → 反查不到拒单）；`{}` = 真读到空。**不承诺与 `gs.equips` 名单同序/同长**（对齐键 = 名 + 出现序游标消费）——「同序不变式」需要全名单写端（获得链/卖出回收/工具上报/效果改写 ≥10 处）同步维护，牵涉面爆炸且无消费必要（同名件可互换，配对无语义差），弃。

### 2.9 `obs/cw_observe_full.py` — heavy 链产物扩展

改 L178-180：同一次 `read_equips` 产出派生第二键（零额外识别开销）：

```python
_eq_hits = read_equips(frame, _eq_sift, equip_rect=_eq_rect4)
out['owned_equips'] = [n for n, _p, _s in _eq_hits]
out['owned_equip_xy'] = {}
for _n, (_cx, _cy), _s in _eq_hits:
    out['owned_equip_xy'].setdefault(_n, []).append((int(_cx), int(_cy)))
```

资源未就绪分支（L170-175 两 warning）：`owned_equip_xy` **不置键**（同现状形态——消费面 `.get()` 得 None，m8 措辞）。

### 2.10 `operations/cw_screen/cw_screen_prep.py` — 装配点平行写

改 L403-408 装备库存观察写端，同环同 sig 平行写坐标伴随域（宁缺勿造守卫同族）：

```python
if _of.get('owned_equips') is not None:
    _gs_obs.observe(_gs_obs.equips, list(_of.get('owned_equips')), sig=_prep_sig)
    if _of.get('owned_equip_xy') is not None:
        _gs_obs.observe(_gs_obs.owned_equip_xy, _of.get('owned_equip_xy'), sig=_prep_sig)
```

### 2.11 `kernel/cw_action_report/wear_equip.py` — 记账路径重写（r3 核心域；r2「零改动」裁定作废）

按 §0 用户架构裁定重写：记账 = 坐标反查，名称校验删除。

**新增反查函数**（同文件模块级，记账域单点）：

```python
def _resolve_item_by_xy(gs: GameState, src_cx: int, src_cy: int) -> str | None:
    """坐标伴随域反查装备名((cx,cy) → 名;记账路径总契约 §0 适用)。

    唯一性前提 = 同一快照内坐标↔名一一对应(单格单件,逐格分类器保证);
    反查不到(坐标不在表/伴随域未就绪 None) = None → 调用侧拒单零写
    (wear_item_xy_unresolved)→ 跳过自愈通道(下帧观察重派)。
    条目量级 ≤28 格线性遍历,无性能面。"""
    xy_map = gs.owned_equip_xy.value or {}
    for name, cands in xy_map.items():
        if (int(src_cx), int(src_cy)) in [(int(a), int(b)) for a, b in cands]:
            return name
    return None
```

**`report_action_wear_equip_param` 改造**（L306-382）：

1. **删除** L329-332 owned 名单校验（`wear_item_not_owned` 退役）→ 换坐标反查：

```python
    item = _resolve_item_by_xy(gs, param.src_cx, param.src_cy)
    if item is None:
        return _reject('wear_item_xy_unresolved',
                       'owned_equip_xy 含 (src_cx, src_cy) 条目',
                       f'xy=({param.src_cx},{param.src_cy})')
```

2. **`_locate_unit` 收缩**（L228-277）：删 char_name 形参消费（L257 身份核对整删）；删名匹配回退分支（L264-277 bench 扫描 + deployed 名匹配——char_name 字段没了、row/slot 生产恒传，分支零生产消费，随批退役）；保留纯槽位定位（row/slot → (域,下标,单位)），越界/空槽拒单保留（`wear_target_unit_missing` 语义**收窄**：删「在位者与 char_name 不符」条件，字段没了；front-only 回退步拖空槽 = 槽空拒单语义不变，与游戏侧静默拒同形，对账面暴露）。
3. **合成/刃锻/摘件/证据全改反查产物消费**：L341-344 `_wear_synthesis(list(unit.equips) + [item], ...)`、L352-353 刃锻支输入、L362-364 `owned.remove(item)` + evidence 字符串 `owned[{item}] -1`——一律用反查产物 `item`，`param.item_name` 在本文件零残留。
4. **反查后名单一致性**：反查产物名直走既有 `owned.remove`（不加名单校验）——反查表与名单同环同源产出（§2.9 同一次 read_equips 派生），反查命中逻辑上必在名单；理论不一致态（名单已摘而伴随域未刷新）= 取值直接使用、Python 自然异常（`list.remove` ValueError）= bug 响亮暴露（零防御纪律同族，禁校验出口）。

**拒绝码词表申报**（登记面 = 上报拒绝语义词表，`cw_action_report` 包 docstring 词表 + fields.md 回执契约节，实施角色按现行登记位落）：

| 码 | 处置 |
|---|---|
| `wear_item_not_owned` | **退役**（名称校验删除，§0 裁定 2） |
| `wear_target_unit_missing` | **保留收窄**（越界/空槽拒单保留；「在位者与 char_name 不符」条件随 char_name 核对删除） |
| `wear_item_xy_unresolved` | **新增**（坐标伴随域反查不到；登记后使用——新码先登记再使用纪律） |

**模块 docstring 更新**：拒绝语义段（L41-48）按上表重写；补记账路径总契约引用（「记账 = 坐标反查（§0 用户裁定；契约正文 = changes/wear-equip-param-surface/design.md §0——迭代收尾正本化时随正本区承载）」）。

### 2.12 `prep_actions.py` — 机械原语退役与拖点权威裁定（M2 修订）

- **`_equip_slot_drag_point`（L414-442）随批退役删除**：本批后全仓零消费者（工具 char 模式目标 = `ex._front_pts/_back_pts` 裸中心派生，非本函数；穿戴 op 是唯一消费者且本批拔除）。保留 = 制度化一个与工具族矛盾的拖点派生式，删除 = 根治。退役申报写进 commit message。
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

### 2.13 `sim/cw_sim_backend.py` — 占位坐标同步（M3：本批必做；A2 语义消歧）

参数面变更落本批，sim 停摆也落本批——占位同步**纳入本批必做**。复审注：新记账路径下 sim 占位坐标进表 = 反查可命中 = 记账全链通，比 r2 形态更干净。

- **写通道消歧（A2 + m-r3-2）**：sim 写端 = **环境快照通道，写通道 = `gs.observe`**（先例同款——sim 环境快照写也是 observe 形态，`cw_sim_backend.py` L2808-2809「三写 observe 通道 sig 由回调内构」即 `diamond_count`/`back_layout` 环境快照写）；**禁 `write_logic`**（会把伴随域写成逻辑态，破坏 observe-vs-logic 失配告警语义）。
- **落点** = sim 后端 tick 层（实施角色按 `cw_sim_backend` 主循环现行结构选位），逻辑 = 名单覆盖差 reconcile（**按计数差 append，非按名存在性跳过**——同名 2 件只 append 1 条会让第二条反查/记账消费缺位）：

```python
# 语义:名单(gs.equips)中每名的条目数 − 坐标伴随域该名条目数 = 差额,
# 差额 > 0 → 逐差额 append 占位坐标(同名 2 件 1 坐标场景 = 差 1 补 1,
# 非存在性跳过)。
# [占位唯一化(M-r3-2):占位亦须满足坐标↔条目一一对应——反查按坐标
#  首中语义,同值占位会反查错名污染 sim 逻辑账。形态 = 基值 + 全局
#  占位序号偏移:(1769, 400 + 13*k),k = sim 后端维护的占位递增序号
#  (伴随域 sim 局只增不减,序号恒新,无重排冲突面)。
#  占位 = sim 环境快照,机械段静默不消费(反查可命中,记账正常),
#  禁实机消费占位(实机恒观察写真值)。
#  伴随域 None(未就绪) → 跳过(等观察/名单就绪)。
#  写通道 = gs.observe(见上,禁 write_logic)。]
# 申报语义 = sim-design §6.5 环境快照族。
```

- **sim 形态下 Obs(in_place) 帧的影响申报（m-r3-6②，r2 收割遗留补齐）**：sim 局交替机制的重观察帧行为 = 若 sim 局观察链不产 `owned_equip_xy`（无真机识别产出），伴随域恒占位态——重观察帧退化为无害空帧（占位表不被刷新也不被破坏，反查恒命中占位，交替机制语义自洽）；若 sim 侧行为产实读键（宿主观察链的 sim 侧形态归 sim-design 辖域），亦为合法整表覆盖刷新。两分支均不破坏 §1.5 契约，无需 sim 侧特判。
- `docs/develop/sr_od/application/currency_war/sim/sim-design.md` §6.5 邻域补申报行：「owned_equip_xy = 环境快照字段，写通道 = gs.observe，sim 后端按名单计数差 append 占位（占位按基值+序号唯一化，先例 diamond_count 环境快照写），机械段静默不消费，禁实机消费占位」。

### 2.14 `data/cw_equipment_data.py` — 注释同步（m6）

L49 注释「与执行边定位读（`prep_actions._owned_grid_locate`，全库模板按名定位）」过期化 → 改为语义化表述：「坐标伴随域 = gs.owned_equip_xy（观察装配点写入）；按名定位读现役仅剩工具原子族（`prep_actions._owned_grid_locate`，待迁移）」。

### 2.15 测试仓镜像测试 — 见 §5

### 2.16 文档面 — 见 §6

## 3. gs 坐标伴随域核查结论

**结论：gs 现在不记 owned 装备坐标；观察端坐标已产出但链上两处丢弃。**

- `gs.equips: Field[list[str]]`（`cw_game_state.py` L3166）= 名单，无坐标。
- 观察端坐标源已存在：`read_equips`（`obs/cw_equipment.py` L437-462）返回 `[(name, (cx, cy), score)]`（默认区域 = 装备区标准格 `(1620,90,1918,710)` 走逐格分类，28 帧真值召回 171/171；非默认 rect 走全域 SIFT）。
- 丢弃点 ①：`cw_observe_full.py` L178-180 `[n for n, _p, _s in read_equips(...)]` 只留名字。
- 丢弃点 ②：`gs.equips` 字段形态 = 名单（装配点 `cw_screen_prep.py` L403-408 只写名单）。
- MCP extras 面已带坐标：`obs/recognizers/battle_prep_recognizer.py` L125 契约 `owned_equips: list[dict]`，元素 `{name, category, cx, cy, inliers}`——**MCP agent 直调路径的坐标源现成，零改动**。

**gs 侧扩展设计**（冻结原则⑥ = 坐标伴随域规范，strategy-contract §4 / screen-op §2）：新观察域字段 `owned_equip_xy`（§2.8）；写入端 = 备战入口 heavy 观察装配点（唯一观察写入方，§2.10）+ sim 后端占位同步（环境快照通道，§2.13）。**有意不做**的策略/动作逻辑写端：环内装备获得链（`gain_equipment`/上报函数族）不回写坐标——实机获得时点无画面读数可写（写即造假坐标，规范「禁回填猜值」），全名单写端同步维护是爆炸面；坐标缺席/陈旧的治理 = 策略侧双通道（§1.5：跳过自愈 + 穿戴/重观察交替）+ 记账面反查拒单兜底（§2.11），权威重建归观察写端。与 `occupied_equips`（§3.2.15b）的同族点 = 零策略/动作逻辑写端；语义差（决策消费面 vs 审计面）已在 §2.8 字段注释申报——陈旧有行为后果，§1.5 机制是本字段可用性的必要组成。

## 4. op 执行语义

### 4.1 现执行路径 gs/读屏依赖清单（迁移前）

| 位置 | 依赖 | 性质 | 迁移处置 |
|---|---|---|---|
| L79 `ex._owned_grid_locate(item_name)` | 截图 + 模板现读定位源件 | 机械定位读屏 | **拔除** → 显式 `src_cx/src_cy`（新鲜度由 §1.5 策略侧交替机制补位；坐标反查记账键兼用同一值） |
| L77 `ex._equip_slot_drag_point(row, slot)` | 内部后排分支 `select_back_layout(ctx, screenshot())` 截图选档 | 机械定位读屏 | **拔除** → `back_slot_count` 参数 + `_layout_prefixes()` 静态映射 + `row_drag_points` 静态解析（§2.12） |
| L73 `ex._front_pts/_back_pts` | executor 构造时读一次 screen_info | 静态点位表 | **仅拔除 wear op 的消费**；executor 两属性保留（工具 op `cw_tool_use_action.py` L126/L139/L160 仍消费，保留至工具迁移批，m7） |
| L78 `cw_sim_ports.mechanical_io_allowed()` | sim port 检查 | 非 gs | 保留（族规约） |
| L96 `game_state_from_ctx(self.ctx)` | 自上报取 gs 容器 | 上报路径（非机械定位） | **保留**（op-layer 自上报契约 = 「点完即写」载体；`gs is None` = 无处记账跳过，与 pick 族 L89-96 同形态。冻结原则①拔除对象 = 「gs 可用时走快定位路径」的机械分支，自上报取容器非此类） |

### 4.2 迁移后执行流（op 纯机械化）

1. 守卫断言三形（§1.2）。
2. 拖点静态解析：`prefix = '前排' if row == 'front' else _layout_prefixes()[back_slot_count]`；`pts = row_drag_points(ctx, prefix)`；`target = pts[slot - 1]`。
3. sim 分支：`mechanical_io_allowed()` 为假 → 机械段静默跳过（现状保留；sim 占位坐标不被机械消费，反查记账照走）。
4. 实机机械段：`mouse_move((src_cx, src_cy))` 防吞点击 → `PREP_DRAG_SETTLE_WAIT_S` 固定等待（非判效）→ `controller.drag_to(start=(src_cx, src_cy), end=target, hold_time=0.5, duration=1.5)` → 1.5s 固定等待（MCP drag 异步落地）——等待常量与拖拽参数逐字沿用现状。
5. `self.park_cursor(after_wait=0.1)`（`CwOperation` 基类方法自带 sim 零光标静默，剥 `ex._op` 依赖）。
6. 自上报：`gs = game_state_from_ctx(...)`；`outcome = report_action_wear_equip_param(gs, action, ChannelSig(...))`——签名不变；kernel 侧坐标反查记账（§2.11，op 零感知）；**outcome.applied=False 时 round detail 追加拒单事实**（「记账拒单:<码>(拖拽已发生,账未落)」——M-r3-1 修法①，直调方经 round 结果感知拒单；机械成功语义不变）；round detail 日志含 `item_name/char_name`（名称唯一机械面消费 = 日志）。
7. round 结果：`round_success(detail)`。**「owned 网格未定位到 …」round_fail 通道消失**；`prep_actions._PREP_RECEIPT_BLOCK_CODES` L98-102 泛化行保留（工具原子族仍产出），注释补声明「WearEquip 侧供给已随坐标显式化退役」。

### 4.3 「体内零 CV-diff 验穿」对账语义安置

现状已合规：op 拖后零读屏零落地判定，对账归观察边界 reconcile。迁移无额外移交动作，语义写清进新 docstring。方案 A 的重观察帧同时是既有「观察帧对账」点位（部署扫描先例注释 L713）——穿戴域获得同款对账点位；r3 记账路径下反查产物与实物的最终真值对账仍归下一入口 heavy 观察（反查错 = 错账，观察覆盖纠偏 + 失配告警拦停，与既有对账语义同族）。

## 5. 测试设计（sr-od-test，按 §11.4 harness 规范）

> ⚠️ 现场实态：测试仓 CW 域测试源文件当前不在 git（仅剩本地 `__pycache__` pyc，工作区另有并行批在飞改动）。实施角色按当时仓内实态落位：源文件在则改，不在则按下述路径新建。

按文件镜像规范（`src/foo/bar.py → sr-od-test/test/foo/test_bar.py`）：

1. `test/sr_od/application/currency_war/kernel/cw_vocab/test_cw_vocab.py`（新建或并入既有）
   - `from_dict` 往返：全字段 dict → 逐字段断言；最小 dict（必填 4 项）→ `back_slot_count=6/item_name=''/char_name=''/route_tag=''` 缺省断言；未知键忽略断言。
   - `action_key`：同名不同 `item_name` 产不同键；`route_tag` 不入键（route_tag 白名单校验面新建时一并补，m4）。
2. `test/sr_od/application/currency_war/kernel/cw_equip_wear_plan/test_wear_param_steps_of.py`（新建；纯函数直测）
   - 游标序贯消费（helper 完备性面；生产单动作收敛下恒取首候选，m2）。
   - **None 守卫**：`gs.owned_equip_xy.value = None` → 全跳过（m1）。
   - 候选 1 条 × 两步 → 首产次跳；候选缺名分支 → 跳过。
   - `back_slot_count` = `int(back_layout or 6)`（含 None → 6）。
3. `test/sr_od/application/currency_war/operations/cw_op/test_cw_wear_equip_action.py`（新建；harness 剧本）
   - 守卫断言三形 → AssertionError。
   - 实机形态（fixture_controller，screen_info 真档案 → 期望值从同源 yml 派生）：拖拽调用记录断言 `start == (src_cx, src_cy)`、`end == 前排-N rect 中心 x + y1+21`。
   - **后排 slot > 6 新行为**：`back_slot_count=7/8/9` + 对应档 area → 拖点落 `后排7槽-N` 族（§7.5 行为修复锁测）。
   - `env=None` 形态全链；sim 形态（port 关闭 → 机械零调用 + 自上报照走）；`with fast_sleep(): op.run()`。
   - **round detail 拒单码（M-r3-1①）**：种子使上报拒单（坐标不在伴随域）→ 断言 round_success 且 detail 含「记账拒单:wear_item_xy_unresolved（拖拽已发生,账未落）」；正常记账帧 detail 不含拒单段（锁 §2.2 detail 组装形态）。
4. `test/sr_od/application/currency_war/kernel/cw_action_report/test_wear_equip.py`（r3 重写重点）
   - **反查命中**：种子坐标伴随域（名+坐标）+ 名单 + deployed 单位 → 上报 → 记账消费反查产物断言（owned −1 + `unit.equips` 合成链 + evidence 含反查名）。
   - **反查不到**：坐标不在表 / 表 None → `wear_item_xy_unresolved` 拒单零写断言。
   - **名称零消费锁测（r3 核心新测）**：同一 (src_cx, src_cy, row, slot) × `item_name`/`char_name` 取不同值（''/'任意名'/'与反查产物不同的名'）→ 记账结果逐位相同（锁「名称在记账面零消费」，宪法③对齐）。
   - **禁消费窗口违反锁测（m-r3-5）**：种子坐标伴随域含坐标、名单**缺**该反查产物名 → 断言 `owned.remove` 抛 ValueError（锁零防御纪律——防未来有人加静默守卫把错账洗成静默）。
   - **槽位定位收窄**：slot 越界 / 空槽 → `wear_target_unit_missing` 拒单；`char_name` 任意值不再影响定位（身份核对删除回归）。
   - 既有合成链回归：穿着即合成 / 融合召唤 / 刃锻支照走（输入改反查产物后行为不变）。
5. `test/sr_od/application/currency_war/operations/cw_screen/`（装配点，源在则改）
   - heavy 产物含 `owned_equip_xy` → 装配点写断言（含同名两件两坐标）。
   - **未就绪分支**：资源缺失 → heavy 产物无键、装配点零写（保现值）。
6. 发出面编排（mandate/entry，源在则改）
   - 标志交替：置位帧 → 产 `Obs(in_place)` 且清标志；未置位帧 → 产 WearEquip 且置标志（§1.5 时序锁测）。
   - M1 保全：空计划帧 → `equip_plan_empty_noop` 计数仍发生。
7. `test_action_registry`（既有面）：零改动预期；镜像缺失随新建。

验收阶梯（skill §3）：L1 → L2（`test_action_registry` 点名）→ L3 全量 commit 前。

## 6. 文档与 skill

### 6.1 op docstring（MCP 使用说明契约；r3 补三条契约申报落点）

```
"""穿装备动作 op(CwActionWearEquipOp)——坐标参数化机械动作(显式起点,
坐标兼记账反查键)。起点:货币战争-备战画面;终点:装备拖至目标角色
排槽穿上,停留原画面。非终结(terminal=False);机械执行零判效:发出即
记账,拖后零读屏,落地归下一入口 heavy 实读对账,重派 = 决策循环按新
观察自然承接。

参数面三分法(词表 cw_vocab.CwActionWearEquipParam 为单一源):
- 动态坐标:src_cx/src_cy = owned 装备条目格心(1080p),从最近一帧
  analyze_screen extras.owned_equips 元素 cx/cy 取(读完立刻用;连穿
  多件时框架侧每件穿后重观察刷新,读数以最近一帧 extras 为准);
  记账 = 按此坐标反查(用户裁定「动作 op 上报坐标,game state 根据坐标
  找到内容」)——反查不到 = 记账拒单(wear_item_xy_unresolved),账不落
  (处置见下方契约 3:禁止补拖,交还框架决策循环);
- 半固定槽位:row('front'|'back') + slot(排内画面物理槽位 1 基,
  前排 1-4/后排 1-N,记账目标定位键 = 该槽现任单位) + back_slot_count
  (后排槽数 6-9,front 行可省);
- 语义参数(纯日志,机械面与记账面均零消费,可省):item_name/char_name
  仅进日志与 round detail,传不传不影响执行与记账。

[记账反查契约(三条,迁移设计稿 §1.5 成文)]
1. 反查时序不变式:上报反查消费拖前快照;重观察刷新必须晚于上报;
2. 记账后→重观察前的坐标伴随域陈旧条目窗口禁消费(框架侧由穿戴/
   重观察交替保证);
3. 反查唯一性前提:同一快照内坐标↔装备一一对应(观察路径 = 单格单件
   逐格分类保证);反查不到 = 记账拒单(wear_item_xy_unresolved,拖拽
   已发生、账未落;round detail 会带拒单码)。**拒单后禁止补拖**(拖拽
   已发生,再拖 = 二次拖拽)——处置 = 交还框架决策循环(由框架观察链
   刷新对照表后自然重派),勿自行换坐标重试(重读 extras 取新坐标解不了
   对照表陈旧,恒拒单);用旧坐标重试 = 盲拖错格+错账。反查命中但名单
   缺条目 = 禁消费窗口违反,以异常响亮暴露,非拒单路径。
   直调方无对照表刷新手段(观察工具只读不写状态)→ **连穿场景每件之间
   需要一次对照表刷新,无刷新手段则按单件会话使用**(一坐标一调用一
   观察对账,连穿交还框架)。

MCP run_operation 示例:
  args={"src_cx":1740,"src_cy":210,"row":"front","slot":2,
        "back_slot_count":6,"item_name":"量产型装甲","char_name":"银狼"}

守卫断言:row 非法/slot 越界/back_slot_count 域外 = AssertionError,
禁兜底坐标。同名多条:候选按 extras.owned_equips 出现序,每次调用消费
一个坐标;直调方按单件会话使用(连穿交还框架决策循环,见上方契约 3)。
"""
```

### 6.2 skill 文档 `skills/sr-od-currency-war/references/screens/货币战争-备战.md` 条目 8 更新

> 8. 穿装备：`CwActionWearEquipOp {"src_cx":N,"src_cy":N,"row":"front|back","slot":M,"back_slot_count":6,"item_name":"件名","char_name":"角色名"}`——拖装备栏指定装备到场上角色槽位。`src_cx/src_cy` = extras.owned_equips 里目标件元素的 cx/cy（**读最新一帧 extras 就传**——记账按坐标反查，陈旧坐标会记账拒单）；`slot` = 目标排槽位 1 基（前排 1-4 / 后排 1-N），`back_slot_count` = 后排槽数（extras deploy_cap−4，front 行可省）；`item_name`/`char_name` 可省（纯日志）。**按单件会话使用**：一次调用穿一件，穿完重读一次 analyze 对账（owned 少一件 / 目标角色详情装备栏多一件；穿着即合成时合成产物入角色装备栏）；要连穿多件就每件走一轮「读 extras → 调用 → 重读对账」，下一件的坐标必须来自穿完并**经框架重观察刷新后**的读数——round detail 出现「记账拒单:wear_item_xy_unresolved」= 拖拽已发生但账未落，**禁止补拖**（再拖 = 二次拖拽），交还框架决策循环重派即可。

（实施角色按现行 skill 写作规范润色；玩家 skill 只提 MCP 工具。）

### 6.3 开发侧文档

- `docs/develop/sr_od/application/currency_war/game_state/fields.md`：新增 `#### 3.2.15c 装备库存坐标伴随域 owned_equip_xy`（语义 = 名→格心坐标列表 dict、同名多条列表多元素、1080p、决策消费面（发出面坐标源 + **记账面反查键** r3）与 occupied_equips 审计面的语义差；写入方 = 备战入口 heavy 观察装配点整表覆盖 + sim 环境快照通道按名单计数差 append 占位（先例 diamond_count）；禁策略/动作逻辑写端申报；**记账反查键用途申报** = §0 总契约首例）；同文件回执契约节补拒绝码三行变更（§2.11 词表表）。
- 开发 skill `skills/sr-od-dev-currency-war/references/flow/action-op.md`：L122 WearEquip 行改写（显式起点/静态拖点/守卫三形/自上报坐标反查记账/交替+跳过双通道）；新增**记账路径总契约条款（用户裁定，自足成文，m-r3-3：不引 changes/ 路径，长期存活物铁律）**，草文：

> **记账路径总契约（用户裁定）**：动作 op 上报它实际动过的坐标，kernel 记账层用观察产出的坐标伴随域对照表反查出具体内容再记账——名称从「记账键」降级为「反查产物」；名称字段在 op 机械面与 kernel 记账面均零消费（宪法③原样成立）。三条契约：①反查时序不变式——上报反查消费拖前快照，重观察刷新必须晚于上报；②记账后→重观察前的坐标伴随域陈旧条目窗口禁消费（框架侧由动作/重观察交替保证）；③反查唯一性前提 = 同一快照内坐标↔条目一一对应（观察路径逐格分类保证，sim 占位路径唯一化保证）；反查不到 = 拒单零写（拒单发生在拖拽后，禁止补拖，处置 = 交还框架决策循环刷新对照表重派）；反查命中但名单缺条目 = 禁消费窗口违反，以异常响亮暴露（零防御），非拒单路径。全动作 op 迁移继承本契约，不再逐个报批；首例 = WearEquip。逐 op 差异（如坐标伴随域字段名/反查目标域）随各 op 迁移设计稿在迭代内申报，收尾随正本条款承载。
- `flow/prep-contract.md` 三处：§1 坐标系节 L9 族描述收窄（WearEquip 升级动态坐标形态）；**L27-28 §3 取值时机节**：坐标参数化动作取值时机申报表补 WearEquip 行（src_cx/src_cy = 入口观察快照 + 环内重观察刷新；row/slot/back_slot_count = 生成期快照）；§6 活缺口 G1 行补注（WearEquip 已随坐标伴随域 + 重观察交替补防线，G1 现役辖域收窄为工具原子/开件族）。
- `flow/strategy-contract.md` §4 / `flow/screen-op.md` §2（坐标伴随域规范条款，并行批 44297f855）：无需改动（该规范已引 owned_equip_xy 为先例）；本设计稿全文术语已对齐「坐标伴随域」定名（A3）。
- `docs/develop/sr_od/application/currency_war/sim/sim-design.md` §6.5 邻域：补环境快照通道申报（§2.13）。
- `kernel/cw_action_report/wear_equip.py` 模块 docstring：拒绝语义段重写 + 总契约引用（§2.11）。

## 7. 风险与行为变化清单

1. **行为变化：实机环内新获得件穿戴延后一帧**（现状按名现读可同帧穿；迁移后坐标伴随域无该件条目 → 发出面跳过 → 帧终结重观察后重派）。遥测分键基线变化（新增 `m7_equip_xy_pending`/`equip_plan_xy_all_pending`/`m7_equip_reobserve` + **round detail 拒单文案**（「记账拒单:…」段，M-r3-1 修法①——journal 判读面新增段，§5.3 锁测），首局对照判读。
2. **行为变化：每件穿戴 +1 环内重观察帧**（方案 A 交替）。末件穿戴后仍发一帧重观察 = 每访问一次冗余 heavy（A4：保留不改，成本申报即此——换取时序不变式 1 的无条件成立，不做「末件免观察」优化，避免计划尾部判定复杂化）；visit 动作数预算内自收敛。
3. **sim 穿装链保活（M3，本批必做）**：占位坐标同步随批落（复审注：新记账路径下占位进表 = 反查命中 = 记账全链通）；实施顺序 §8 强制同 commit，缺一不合。
4. **MCP agent 拖拽可靠性待实机验证**：op 化走框架拖拽原语与手动路径不同（skill 条目 8 手动 4 连败），首次实机验证是硬验收；同症状复现属执行层拖拽链可靠性问题（修参数不回退设计）。
5. **行为变化（潜在 bug 修复）：后排 slot 7-9 从必拒变可用**（现状守卫表长只匹配基线 6 槽；迁移后按档位表）。判读基线：后排扩展局穿戴计划完成率预期上升。
6. **`back_slot_count` 缺省口径沿用的语义张力**：`int(gs.back_layout.value or 6)` 沿用计划面既有缺省（布局未知双弃权帧张力为现状，非本批新增）；随布局未知态治理批收敛。
7. **`read_equips` 双路径坐标质量差**：rect 与常量一致走逐格分类（标定充分），漂移切全域 SIFT——识别层既有标定承载，本批零改动。
8. **拖点校准保真**：`y1+21` 迁移逐字同构（单测锁坐标值）。拖点权威裁定（M2）：+21 校准式为权威派生；工具 char 模式裸中心 = 无实机背书历史形态，工具迁移批统一（§2.12 申报）。
9. **A1 假设的实机风险**：「获得件插入只占空格、已登记条目格位不动」无实机背书（§1.5 申报）——若实测不成立（插入引发已登记条目位移），回退方案 = 获得类动作帧后也置 `cw4_wear_pending`（§8.6 验收触发裁定）。
10. **反查错账的暴露面（r3 新增）**：记账 = 坐标反查后，若坐标伴随域与实物错位（陈旧窗口被消费/唯一性被破坏），账记反查产物、实物移动的是坐标指向的格——账实分裂由下一入口 heavy 观察对账暴露（失配告警拦停），修法落根因层（§1.5 三条契约的违反点排查）。三条契约成文（§1.5/§6.1）= 预防线；「禁以偶发结案」纪律下每个未生效/失配照常查根因。
11. **`route_tag` 去留裁定**：保留（词表全族统一形态）。
12. **范围边界**：工具原子族（`cw_tool_use_action.py`）消费 `_owned_grid_locate` 与 `ex._front_pts/_back_pts`，本批不动；其迁移时复用 `row_drag_points` 与坐标伴随域模式，记账路径按 §0 总契约改造（其上报函数消费 item_name 定位目标件——同族改造面，随该批）。

## 8. 实施顺序建议（给实施角色）

1. `cw_vocab.py` 参数面 + `from_dict`（§2.1）→ `cw_game_state.py` 坐标伴随域字段（§2.8）。
2. `cw_observe_full.py` 产物扩展 + `cw_screen_prep.py` 装配点（§2.9/§2.10）。
3. `cw_action_report/wear_equip.py` 记账路径重写（§2.11：反查函数/校验删除/_locate_unit 收缩/拒绝码词表）。
4. `cw_equip_wear_plan.py` helper（§2.4）→ `mandate_state.py` 载体字段（§2.7）→ `mandate.py`/`entry.py` 发出点编排（§2.5/§2.6）。
5. `prep_actions.py` `row_drag_points` + `_equip_slot_drag_point` 退役（§2.12）→ `cw_wear_equip_action.py` op 重写（§2.2/§4.2）→ **sim 占位同步（§2.13，与本批同 commit，缺一不合）** → `cw_equipment_data.py` 注释同步（§2.14）。
6. 测试七件套（§5）→ 文档（§6.3）→ skill 两处（§6.2/6.3）。
7. MCP server 重启 → `describe_operation_flow` 核对 op 节点图 → **实机验收两序列**：①单件穿装（§7.4 硬验收）；②「采晶矿 → 穿装」序列（A1 假设验证：观察获得件是否只占空格、已登记条目格位不动；不成立 → 触发 §1.5 回退方案裁定）+ 后排扩展局 slot 7-9 验证（§7.5）。

## 9. 记账路径对齐申报（r3 改写；原「宪法③例外申报」作废）

**申报事项**：本设计稿记账路径已按用户架构裁定重写并**对齐**宪法③——宪法③原条文原样成立、无例外，无需豁免。

**对齐陈述**：

- **裁定落地形态**：op 上报它实际动过的坐标（`src_cx/src_cy`），kernel 记账层用观察产出的坐标伴随域对照表（`owned_equip_xy`）反查出具体内容再记账；名称校验（`wear_item_not_owned`）与 char_name 身份核对（`_locate_unit` L257）整个删除，换「反查不到 → 拒单零写（`wear_item_xy_unresolved`）→ 跳过自愈通道」；目标单位身份改由槽位反查（row/slot → 槽现任单位，槽空 = 拒单）。
- **宪法③逐面核验**：名称字段（`item_name`/`char_name`）在 **op 机械面**零消费（不定位、不校验、零分支，仅日志）——原条文「不参与校验与定位、仅日志」成立；在 **kernel 记账面**亦零消费（r3 重写后 `param.item_name`/`param.char_name` 于 `cw_action_report/wear_equip.py` 零残留，记账键 = 坐标、记账载荷 = 反查产物）——r2 曾申报的「记账面事实消费例外」随重写消除，无例外需要申报。
- **总契约成文**：本裁定 = 动作注册表全集迁移的记账路径总契约（动作 op 上报坐标 → kernel 坐标伴随域反查 → 名称降级为反查产物/日志语义），已按产出要求成文于 §0 与 §6.3（action-op.md 补条款，自足成文不引 changes/ 路径），后续 op 迁移直接继承、不再逐个报批；wear-equip = 第一个适用者。
- **迭代收尾义务**：本节与 §0 总契约在迭代收尾（代码落地后）随正本区承载（action-op.md 正本条款 = §6.3 已列；本 changes/ 文档寿命 = 迭代，正本自足后本稿可删）。
