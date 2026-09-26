# deployed 单字段合并(详设·阶段A)

## 问题与约束

- 病灶家族定位:前台/后台是「紧凑下标 ≠ 物理槽位」家族最后一个未治成员——同族先例 = 备战栏(`BenchView` 定长 9,空槽 `kind='empty'` 显式)与商店牌行(`ShopPayload.cards` 定长 5 三态,docstring 明文「紧凑下标≠物理槽位的历史病灶类(同族)在本模型下结构性消失」,记录真事故 = 买牌点击落空槽框)。
- `TrackedBooks`(bench 定长 9 / deployed 定长 10 保洞表)= 该缺口在执行侧的补偿补丁:主域不可槽位直址,执行器另开定长保洞表保「生成期索引 = 执行期索引」(flow/projection_contract.md §4.1 立法),配套动作随动同步腿与商店播种守卫 expected 侧(双响事故修复点,action-logic-state.md §2 溢出条件腿节)。
- 用户裁定(2026-09-25):主域迁移为**单一字段的完整槽位表**(空位显式),TrackedBooks 整体退役(消灭第二账——非改名共存、非仅统一坐标)。
- 硬约束:等价重构——槽位语义等价、行为零变化(触发机制属阶段B+,本阶段不引入)。

## 方案

### 目标模型

```python
@dataclass(frozen=True)
class DeployedView:
    """上阵统一槽位视图(同族 = BenchView / ShopPayload.cards)。
    front_slots[i] = 前排物理槽 i+1(定长 4);back_slots[j] = 后排物理槽 j+1
    (动态容量,随布局扩容,先例 = BenchView.capacity);空槽 = None 显式。"""
    front_slots: list[Unit | None]
    back_slots: list[Unit | None]

deployed: Field[DeployedView]   # 单一字段:一次写 = 一次完整语义变更
```

- **Unit 退役 `slot` 属性**(现役信息位):位置 = 所在子表下标,纯派生;单位跨域流动时位置由动作载荷携带(DeployMove(to_row, to_slot) 现役参数即此)。
- **换排 = 一次写**(同一字段内两子表交换成员)——跨域单语义变更的中间态物种灭绝,无需批量机制。
- **空槽显式**:槽位直址 = (子表, 下标);TrackedBooks 的存在理由(主域给不了槽位直址)消失。
- **开拓者形态随排**:tags 派生按单位所在子表(前排记忆/后排欢愉),语义不变。
- **0-9 换算层退役**:五函数删除(`deployed_slot_no`/`deployed_row_slot`/`deployed_idx_of`/`deployed_rows_to_indexed`/`deployed_indexed_to_rows`,均在 kernel/cw_exec_state.py)——(row, slot) 与存储位置一一对应,零换算。
- **后排动态容量**:容量变化(投资改槽) = 整视图结构性写(先例 = BenchView.capacity 随效果改写);定长 10 装不下**后 7-9 槽**的表示缺陷(现役 tracked 表硬上限;后排容量值域 6-9、扩展格 7-9,cw_exec_state.py:167-171)随之消失。

### TrackedBooks 退役(消费面逐个去向)

| TrackedBooks 消费面 | 去向 |
|---|---|
| 执行器槽位直址(动作随动同步腿:`prep_actions.py::_track_remove_bench/_track_remove_deployed/_track_move_deployed`、buy 链 `mutate_bench_deployed`(cw_buy_card_action.py:161/177)、wear/tool tracked 腿、cw_deploy_move_action/cw_sell_deployed_action 执行器同步分支) | **腿全部删除**——动作写主域(逻辑通道)即同步,第二账无可同步 |
| 商店播种守卫 expected-vs-tracked(双响防御,溢出吸收缺吸收 = 分叉停机实证) | expected 侧**改读主域视图**(gs.deployed/gs.bench 派生)——防御语义保留,载体合一 |
| reconcile 锚定写回(cw_reconcile.py tracked 整表写回腿) | 写回腿删除(观察通道本就写主域) |
| **升星确认候选**(观察跨帧一致性状态) | 候选宿主不动(本就在 cw_reconcile 局旁表);**真变更 = 比较基线**从 tracked 表改为主域派生视图(锚 = (子表, 下标)) |
| `tracked_account_observed` 旗标 / `tracked_unobserved` 判定 | 锚定语义重定义为主域观察锚(观察边界对账唯一发生点不变,两态制不变——prep.md §3/§6) |

### 观察与吸收口径

- **观察写形**:读侧仍分排读屏;落容器 = 一次 observe 写 DeployedView(两排同帧合一)。
- **观察吸收口径**:同子表内**单元级多重集相同、排列不同** = 读数抖动,吸收(键 = (名, 星, 装备集),现役 `_rows_unit_key` 口径延续,cw_game_state.py:2675——名字级键会把装备真值变化误豁免为重排,禁用);换排是我们发起的逻辑写,不进观察吸收。

### 快照兼容

- `schema_version` 升版;旧档迁移函数单次转换(front_row/back_row 两列表 → DeployedView;tracked_books 丢弃——簿记非 Field 本就不入快照流水)。
- `restore_state_snapshot` 兼容面 = 迁移函数一处;接管恢复行为等价。

### 触面清单

| 层 | 触点 |
|---|---|
| 容器(cw_game_state.py) | 字段定义(front_row/back_row → deployed)/种子(seed_opening_state)/快照恢复与归档/`_write_logic_frame` 行域分支(两域 → 单域)/`_resync_board_delta` 单域化/`_absorb_slot_reorder` 键口径/`mutate_bench_deployed_local` 删/`detect_merge_upgrade` 形状/TrackedBooks 类删/`tracked_account_observed` 处置 |
| 写方 | deploy_move、sell_deployed、buy_card(pre_dep 快照)、gain 链(merge 工作表+落写)、wear_equip、工具装备腿、swap_deploy(:93-99,真实行域写方,消费换算函数+Unit.slot,策略侧 live 引用)、**pick_planner(:215-216 直读行域/:236 换算消费/:272-277 升费腿 2★→1★ 写回行域)**、观察链(分排读屏 → 合一写视图) |
| tracked 侧(退役面) | cw_exec_state(换算五函数删;容量常量保留——固定双射动作坐标系仍消费,不删)、prep_actions(_track_* 三腿删)、cw_reconcile(锚定写回腿删、比较基线改主域派生)、cw_vocab(执行侧换算删)、strategies/impl/mandate_v1/(mandate 读口改主域派生)、cw_deploy_move_action/cw_sell_deployed_action(同步分支删)、**cw_action_report/sell_bench.py(:89-102 报告层 tracked 吸收腿)**、**operations/cw_op/cw_prep_sell_bench_action.py(:66 执行腿)**、**operations/cw_screen/cw_screen_shop.py(:532 tracked 读口)**、cw_observation(cw_observation.py:2434 读口改)、cw_screen_prep(:548 读口改)、cw_buy_card_action(:161 mutate 调用与 :177 tracked 读点改;wear tracked 腿在 wear_equip.py:174-182,tool_use 无 tracked 腿) |
| 读方 | sim `_board_truth`、策略层部署决策、`deployed_rows_of`/`front_count_of`/`back_count_of`/`deployed_count_of`/`max_units_of`(派生读口重写或删) |
| 测试 | 断言 front_row/back_row 与 tracked_books 的全部测试 |
| 文档正本 | fields.md §3.2.3/§3.2.4、projection_contract.md §4 与 §3 相关行(双账段/换算段/槽位表立法段)、action-logic-state.md §1.4(随动账行)、screens/prep.md §6(tracked 行)、screens/op-layer.md(对账比较基线)、flow/action_ops.md(动作总册) |

## 关键取舍

- **完整槽位表(取)vs 单位带 row/slot 属性 + 缺席表达空位(弃)**:属性方案查询 = 按属性搜、空位 = 缺席推断;槽位表 = 下标直址、空位显式——与 bench/shop 同族同法,TrackedBooks 三个消费面全部就地消化,用户裁定「game state 存完整列表,前台/后台/备战席/商店都是」。
- **消灭第二账(取,用户裁定)vs 统一坐标保留镜像(弃)vs 改名共存(弃)**:保留 = 两种表示永久并存 + 定长 10 动态后排洞不修;消灭 = 第二账物种灭绝,代价 = 守卫/候选两处消费面迁移(本详设已给去向)。
- **升星候选宿主不动、比较基线改主域派生(取)vs 迁独立簿记组(弃)**:候选本就住在 cw_reconcile 局旁表,迁移是无事生非;真变更只有比较基线(tracked 表 → 主域派生视图)。vs 塞回字段(弃):候选 = 待验证状态,字段 = 当前可信认知,混装破坏两态制语义(prep.md §3)。
