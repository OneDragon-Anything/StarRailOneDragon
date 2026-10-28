# 动作后果声明化（总纲）

## 0. 元信息
- 迭代目标：用户裁定（2026-09-24 会话）——动作上报改为**返回后果声明**，实机与 sim 共用该声明驱动「交回外循环判断」与「sim 世界推进」；转移事件机制退役。范围第一批 = **正常流程全部转移动作**（出战/战斗结算/节点推进/开箱/选卡族/开书册卡/关店）；overlay 触发面不在本迭代。
- 状态：定稿（对抗收敛 + 试读过；attack.md 历轮台账全闭环）
- 文档清单：details/world-decl.md —— 后果声明 schema、18 转移动作对照表、backend 推进分派、单动作单轨迁移与退役面

## 1. 问题与动机

- **现状症状**：「动作落地 → 世界后果」的知识三处并行——①动作注册表 `terminal` 属性（交回与否，`screens/README.md` §6 回外循环(终结)语义总表）；②转移事件封闭集（`kernel/cw_event_hooks.py::TRANSITION_EVENT_KINDS` 18 成员，kind = 动作落地名）；③SimBackend 分派表（`on_transition_event` 按 kind 逐个分派到画面推进/世界过程）。新增一个转移动作要同步三处，漏一处 = 广播点漂移（封闭集 ValueError 响亮兜底）或状态机不推进。
- **表达缺口**：`terminal` 是静态属性，表达不了「动作后世界动态决定画面」——部署/买牌后板面变化可能触发盛会之星弹窗（实机靠画面 op 循环内 B 面扫描兜底交回，动作层无感知）；overlay 目录每次扩充（武装箱说明弹窗、partner 等）都要先动事件封闭集再动 backend 分派表。
- **根因归层**：语义层——「动作的后果」没有单一源。后果知识应住在**动作自己的上报函数**里（它持有容器、知道动作干了什么），消费方各取所需；现在它散落在注册表、封闭集、backend 分派表三处。
- **解决到哪**：转移类后果（可能前往的画面 + 触发的世界过程）声明化：上报函数算并返回声明 → 动作 op 经端口喂 sim backend → 画面 op 派发点按声明判断交回。转移事件半部（18 kind + 装饰器 + sink + `on_transition_event`）退役。
- **明确不解决**：
  1. overlay 触发层——事实事件 `board_changed`/`star_up`（`cw_event_hooks.FACT_EVENT_KINDS`）与 backend 巨星/planner 评估器原样保留，overlay 批再声明化（届时评估器 kernel 化后并入声明）；
  2. 点击源（简报下一步/位面过渡/开店/补给刷新）——不经上报函数，仍走 `click_answer` 端口（backend 感知面 = `sim/cw_sim_backend.py::_handle_click_source` 逐 case 现役登记）；
  3. `terminal` 访问终结属性——**保留**。交回与转移是正交两义：refresh 族「访问终结但画面档不变」（现役 terminal 登记 = `operations/cw_op/cw_refresh_shop_action.py`；终结总表 = `screens/README.md` §6），声明只承载转移，交回判断仍需终结属性；
  4. 动画等待值（`terminal_wait`）与机械分支 port 检查——不动。

## 2. 方案

### 2.1 系统级变化

动作上报函数（kernel，实机 sim 同一函数）在写完容器后**构造后果声明** `WorldDecl`，随 `LogicOutcome.world_decl` 字段返回。消费点：

```
动作 op：机械执行 → 自上报 → 声明经端口喂 backend（sim 驱动；实机 no-op）+ 随 round 返回结果 data 带回
画面 op：本迭代零改动——交回判断仍由 terminal 单独承载（terminal ⇒ 交回）
backend：advance(decl) → 按 trigger 分派推进（世界过程/画面呈现）→ 按 next_screen 等值对账画面档
```

**交回与转移正交**（本迭代定案）：交回语义由 `terminal` 单独承载，声明不参与交回判断。依据（持久锚）：① refresh 族 `terminal=True` 但无画面转移（`operations/cw_op/cw_refresh_shop_action.py` 现役 terminal 登记 + `screens/README.md` §6 终结总表「访问终结但画面档不变」行）；② 局终罕见态——P2 末确认 `terminal=True` 必须交回但无下一画面（声明空串），「terminal ∧ 声明非空」式会在此卡死留守。声明在实机是**数据面**（journal 预期画面 vs 实读画面 diff 对账料，禁作判效断言）；判断切换（`terminal ∨ 声明含 overlay 档`）留给 overlay 批——非终结动作（部署/买牌）触发弹窗需交回的场景，届时 data 通道已就位。

| 声明维度 | 实机消费 | sim 消费 |
|---|---|---|
| `next_screen`（确定的下一画面） | 弱：journal 预期记账，供画面漂移 diff | **强**：推进后等值对账（不等 = 缺陷留证） |
| `trigger`（推进分派类别） | 不消费（可日志） | **强**：分派世界过程/画面呈现 |

声明首先是 **sim 的驱动协议**（backend 感知「动作落地了」的时机信号 + 推进分派依据），其次顺带给实机当记账料——实机画面真值归下一帧识别（「观察赢」，flow/README 卷首术语注），禁作判效断言（A3 拆除的轮询判效禁变相回归）。

### 2.2 跨详设接口契约（单一权威 = details/world-decl.md）

1. **声明 schema**：`WorldDecl(next_screen: str, trigger: str)`；`next_screen` = 动作后确定的下一画面 screen_info 档名（空串 = 无画面——局终等未建模终态；`node_advance` 的推导权威源 = **kernel 节点日程真值表**（本迭代自 `sim/cw_sim_plane_schedule.py` 迁入 kernel 新模块，R1 修法 (a)）+ `effective_node_ord`——容器 `gs.node` 为观察镜像不随推进变，禁作推导读口）；`trigger` ∈ 收敛推进类别集（9 类 + 空，权威集 = 详设 §3 分派表；**值零新词，沿用现役动作名**）。18 转移 kind 归并为 9 个推进类别 + 纯转移——**准入判据 = 写端归属**：上报函数/获得链已写的后果（腾席/离屏/动作直接后果）不进 trigger；只有 backend 专属的活才进（sim 经济结算、队列出队、候选采样、排除集簿记——实机里「游戏自己算」的部分），其余动作 `trigger=''` 纯画面转移。**注意**：`trigger` 是声明数据里的分类标签，随 `LogicOutcome.world_decl` 显式传递，与已退役的事件机制（sink/订阅/广播）无关。
2. **返回载体**：`LogicOutcome` 新增字段 `world_decl: WorldDecl | None = None`；构造声明是上报函数 `applied=True` 出口的义务，`applied=False`（拒绝/未发出）= `None`（对齐现行「applied=False 零广播」）。**签名改形申报**：`report_node_advance` 现役返回 `bool`，本迭代改返回 `LogicOutcome`（applied = 推进落账位），两个 bool 消费点随 3.2 改造（详设 §1）。
3. **喂入契约**：动作 op 自上报后一行 `cw_sim_ports.declare_world(outcome.world_decl)`——端口未装 = no-op（实机零开销零行为变化），装了 = `SimBackend.advance(decl)`。
4. **派发点契约**：本迭代画面 op 派发点**零改动**（交回判断 = `terminal`，现状不变）；动作 op 的 round 返回结果以 `data` 字段承载 `WorldDecl | None`（框架 `OperationRoundResult.data: Any` 现役通用载荷位，零框架改动）——通道就位，判断切换（overlay 批）届时启用。
5. **backend 推进契约**：`advance(decl)` 按 `trigger` 分派推进（`node_advance → _on_node_advance`；`battle_resolve → _resolve_battle` 等 9 case），`trigger=''` = 纯转移（按 `next_screen` 推进画面，零专属过程）——现行 `on_transition_event` 各 case 的内部逻辑平移不变；推进完成后实际画面与 `next_screen` **等值对账**（对账对象 = 底层稳态画面，建模内让路/overlay 呈现豁免集与局终断言载体见详设 §3）；`trigger` 集外值 = `ValueError` 响亮（与现行封闭集同等防线）。
6. **退役面**：`TRANSITION_EVENT_KINDS`/`TransitionEvent`/`set_transition_event_sink`/`emit_transition_event`/`transition_event_on_applied`/`SimBackend.on_transition_event` 删除；事实事件半部（`FACT_EVENT_KINDS`/`emit_fact_event`/`on_fact_event`）原样保留。
7. **迁移策略**：单动作单轨——每个动作落声明的同时摘其事件广播（装饰器或 emit 点），backend 双入口并存期间同一动作只有一条驱动路径，无双驱动窗口；全部 18 动作迁完 → 3.4 退役批整体删除。

### 2.3 详设划分

单详设 details/world-decl.md 承载：schema 定义、18 转移动作声明对照表（初值 + 权威源盘点规则）、`advance` 分派表、喂入与派发点契约的落点文件、退役清单、测试与验收面。实现某阶段只读总纲 + 该详设即可动手。
