# CwActionSellDeployedOp（卖场上单位）参数面迁移设计稿（r1）

> 迭代：CW 动作 op 迁移流水线 · 设计角色产出（卖场上单位 op 批 = 第四棒）。
> 上批 = 统一拖动 MoveUnit（changes/move-unit-param-surface/design.md，已落地 commit a09f30e8b）；上上批 = 工具原子七类（changes/tool-use-param-surface/design.md，commit 76a94c27c）；首棒 = WearEquip 穿装（changes/wear-equip-param-surface/design.md，commit db4697e40 终稿）。
> **范围裁定（用户指令，每迭代只切一个 op）**：本批只做 `CwActionSellDeployedOp` 一件；SellBench 撤出本批、待后续独立迭代（§9 申报行 1）。
> 冻结宪法（用户裁定，穿装批成文）：①动作 op 执行路径零 gs 依赖；②参数面三分法；③名称字段 = 语义参数（可选，不参与校验与定位，仅日志）——记账面亦零消费；④坐标新鲜度纪律归调用方；⑤参数 dataclass 统一补 `from_dict`；⑥gs 给实体记录坐标（坐标伴随域）；⑦每个 op 一个迭代，牵涉面一次改净。
> **记账路径总契约（正文 = `skills/sr-od-dev-currency-war/references/flow/action-op.md`「记账路径总契约」条款）第四适用者**；本 op 对象住槽位表不住坐标伴随域——记账键 = 槽位下标、记账载荷 = 槽位反查产物/状态推导名（「槽位反查」无表形态，MoveUnit 为第一例，本批 = 第二例，§1.2）。

## 0. 本批范围

`operations/cw_op/cw_sell_deployed_action.py::CwActionSellDeployedOp` + 词表 param `CwActionSellDeployedParam` + 上报层调用面（outcome 消费形态）+ 全部引用（grep 全量已核，§3）。

现状债（迁移动机）：

| 债 | 现值 | 迁移形态 |
|---|---|---|
| 机械半消费执行器点表 + gs 读 | `ex._front_pts/_back_pts`（构造期缓存）+ `ex._drag` + **执行路径中途读 gs**（`cw_sell_deployed_action.py:66-69`：`back_capacity_of(_gs)` 现读算 cap——冻结宪法①违例，同域唯一残留） | 机械半自持：op 内 `row_area_centers` 现读点位表 + 模块级 `drag_char_guarded` 原语 + `sell_point` 单一源；cap 守卫改 `back_slot_count` 参数静态闭合 |
| 扩格后排槽必拒（潜在 bug） | `ex._back_pts = row_area_centers(ctx, '后排')` 前缀只匹配基线 `后排-1..6`，扩格局（宝钻 7/8/9）后排槽直卖今日机械段必拒——与穿装批 §1.2-2、工具批 §1.2-3、MoveUnit 批 §0 已修形态同款（上报侧直读动态视图不截断、机械侧点表截断 = 两面不一致） | 新参 `back_slot_count`（布局档静态解析），后排 7-9 可用 |
| outcome 丢弃 | `report_action_sell_deployed_param` 返回值不消费（`cw_sell_deployed_action.py:92-97`），`deployed_idx_out_of_range`/`stale_proposal` 拒单对直调方不可见 | MoveUnit/穿装/工具批 M-r3-1① 同形：`applied=False` → round detail 追加拒单段 |
| param 缺 `from_dict` | MCP `run_operation` JSON 通道无法构造 | 共享 `action_param_from_dict` 一行委托 |
| dead 形参实参 | op 上报调用带 `session=` 实参（`cw_sell_deployed_action.py:96-97`），上报函数体零消费（`sell_deployed.py` 全文无 session 读取；现役消费 session 的上报函数仅 start_battle/pick_invest 两族） | 摘除实参（零行为差；上报函数签名 `session: object = None` 形参不动——族内兼容位） |

## 1. 本批特有设计题裁决

### 1.1 交替机制延伸题（本棒主轴，MoveUnit 批 §1.3 明言 deferred 到本批）：卖出 aftermath = 纯增长方向 = A1 假设辖域，本批零交替机制改动

**推演（SellDeployed aftermath 对坐标伴随域 `gs.owned_equip_xy` 的影响面，逐域核验）**：

| aftermath 产物 | 载体（上报写端现值） | 与 `owned_equip_xy` 的关系 |
|---|---|---|
| 卸装件回库存 | `gs.equips` 追加（`sell_deployed.py:81-83` `+ list(sold.equips)`；SellBench 同族 `sell_bench.py:109-111`） | **获得方向库存增长 = 穿装批 A1 假设辖域**（wear design §1.5 A1：「获得件插入只占空格、已登记条目格位不动——逐格分类器 28 固定格结构支持，但无实机背书」）。A1 成立 → 存量条目格位不动、存量坐标恒新鲜，新回装件坐标缺席（`wear_param_steps_of`/`tool_use_params_of` 缺席跳过 + 帧稳定截断 → Obs outer_loop 重观察重派的自愈通道覆盖）；A1 不成立 → 存量条目位移、后续穿戴/工具帧盲拖错格 + 反查错账（错账由观察对账暴露 + 失配告警拦停，非静默） |
| 场上摘槽 | `gs.deployed` 置 None 不移位（`sell_deployed.py:65-75`） | 零交集：装备库存网格是独立面板区，部署行变化不驱动装备网格布局（MoveUnit 批 §1.3 同款结论） |
| 回金 | `gs.gold`（`sell_deployed.py:76-80`） | 零交集 |
| 记账面自身 | 槽位反查（§1.2） | 零消费坐标伴随域——卖出上报本身**不是**陈旧窗口消费者；风险面仅在同 visit 后续穿戴/工具帧的坐标消费 |

**sim 形态零失效面（旁证）**：sim 占位 = `(-1000-k, -1000)` 界外哨兵按占位序号唯一化、只增不删（工具批 §6 条 1-2 既有申报；`test_sync_owned_equip_xy_placeholders.py` 锁测面）——卖出 aftermath 的回装件在下一 advance 步界按名单计数差 append 占位（占位同步的主路径就是获得方向），存量占位坐标恒不变；按名反查恒正确。sim 局本批零改动。

**裁决：`cw4_equip_xy_pending` 置位端**不**加卖出点；本批零标志机制改动（现役置位端 = 穿装发出点 mandate M7 + entry 第 7 步、工具原子发出点 entry 第 7 步，不变）。**

论证（按工具批口径，根源两问：根 = 「坐标伴随域 owned_equip_xy 可能陈旧」这一**单一字段**的新鲜度不变式；置位端判据 = aftermath 是否威胁该不变式，威胁判定现役依赖 A1 假设——不是「哪个 op 在迁移」）：

1. **单字段单标志无争议面**：卖出 aftermath 若要置位，置的就是 `cw4_equip_xy_pending` 这一个标志——工具批 §2.2 已裁定双标志保护单字段无解（「双置位」组合：清一个留一个 = 窗口仍开；清两个 = 与单标志一字不差而多付一个字段）。本批零新增载体、零机制改动，同判无新题。
2. **卖出 aftermath 与获得类动作同族，同族必须同判据**：卖场上/卖备战席的卸装回收 = 装备**纯增长**回库存（卖出全程零 owned 消耗——grep 已核 `sell_deployed.py`/`sell_bench.py`/`cw_env_grants.py:1151` 均为 append 形态），与采晶矿/开件/补给的获得件属同一失效方向。工具批 §2.3 末条明文 defer：「获得类动作不在本批扩展……回退 = 获得类动作帧也置本标志——单标志多一个置位端，机制零新增」。卖出族若本批单独收编而获得族不收编，等于把同一条不变式的置位端按「哪个 op 在迁移」切分——恰是工具批 §2.2 否决的「标志绑动作族」思维的换向复发（判据分裂）。
3. **置位端完整性**：SellBench 装备回收 aftermath 与 SellDeployed 同形同载体，SellBench 在批外（MoveUnit 批 §9 申报行 1 用户裁定独立迭代）——本批只收编 SellDeployed 置位端 = 单字段的部分置位端，保护面残缺且不可推理（「卖场上置位、卖备战席不置位」）。置位端要收就是一族一起收。
4. **统一裁决点 = A1 实机验证批**（穿装批 §1.5 A1 申报的验收序列「采晶矿→穿装」，wear design §8.6）：A1 成立 → 全族（获得类 + 两卖出）零置位端成立；A1 不成立 → 回退方案一次收编全族置位端（CollectOre/OpenBox/OpenTome/OpenBookcard/PickSupply + SellDeployed/SellBench 装备回收），单标志多置位端、机制零新增。本批在 §9 申报行 2 登记卖出族的 A1 回退归属，不预设结论。
5. **成本与 fail-safe 方向核对**：不加以外，最坏失效 = A1 不成立时卖出后同 visit 下一穿戴帧盲拖错格——治理结构现役已全（新件缺席跳过自愈 / 陈旧坐标反查命中错名 → 记账面错账由观察对账暴露失配告警拦停 / 反查不到拒单），且 A1 回退是成文的一次性收编路径，非无底洞敞口。反之在本批无条件置位 = 每次卖出 +1 环内重观察帧（卖出是高频动作：换星直卖/腾席/凑利息），无实机背书的失效模式撑不起该常态成本——「逐类 aftermath 细粒度白名单免观察」方向工具批已弃（无背书优化），本批对称地「逐类细粒度收编置位」同罪弃。

### 1.2 卸装件名的记账语义：状态推导（`sold.equips` 载体），非参数名；宪法③对本 op = 空集成立

**上报层名称消费逐处核验**（`kernel/cw_action_report/sell_deployed.py` 现值，行号为 HEAD）：

| 记账消费 | 现形态 | 名称来源 |
|---|---|---|
| 槽位写（摘槽置 None） | `deployed_idx` → 动态视图 `(front+back)[idx]` 直址（:53-57），越界/空槽 = `deployed_idx_out_of_range` 拒单零写 | 记账键 = 槽位下标（状态容器槽位表下标，非名称非坐标） |
| 卖出单位身份/星级/退款 | `_sold.char_id`（:59-64 stale_proposal 对照）/ `sold.star` + `bench_char_cost`（:76-77） | **槽位反查产物**（按 idx 反查槽现任单位） |
| 装备回收 | `sold.equips` 追加回 `gs.equips`（:81-83） | **状态推导名**（反查产物单位的载体字段——单位对象本身就是它携带装备的权威） |
| 归因 | `param.reason` → outcome.reason（:87）；`param.income` 零消费（记录非指令，同 SellBench 词表申报） | 参数归因字段（非名称语义） |

**裁决：卸装件名 = 状态推导，零改造。** 辖域辨析：宪法③管「参数名」——op 参数里的名称字段在 op 机械面与 kernel 记账面均零消费；状态推导名（`sold.equips`）是记账载荷的正当来源，**不在宪法③辖域**（工具批先例原文：「穿戴件名消费维持状态推导不动（宪法③管参数名，不管状态产物名）」tool design §3.1）。工具批扳手先例的另一半「状态推导名容错」（`_remove_one`）本 op 无对应物：卖出对回装件只有 append 没有 remove，容错/严格语义分裂在卖出域不存在。`CwActionSellDeployedParam` 现无名称语义字段（无 item_name/char_name 形态），**零新增**——MoveUnit 批 §1.4 同形裁定（槽位键族不加名称参数；MCP 直调定位全凭下标，round detail 语义由槽号承载），宪法③对本 op = 空集成立。

**总契约适用申报（第四适用者）**：契约三条在槽位键域的形态 = ①反查时序——记账 = 上报时点状态容器槽位表现读，与决策同帧同容器（单动作决策环现算契约辖域），无坐标伴随域刷新时序面；②陈旧窗口——槽位表恒稳（卖出置 None 不移位，`cw_vocab.py:386-388` 既有申报），无窗口；跨帧队列消费面（yield plan 卖步骤逐帧消化）由发出点按名现读重推导 fail-closed 承接（`entry.py:693-697` 现值）；③唯一性——deployed_idx ↔ 槽位一一对应（槽位表结构性保证，槽位表本身就是名称↔位置对照表，无表形态）。`report_action_sell_deployed_param` **零改造**。

### 1.3 卖出目标定位：`deployed_idx` 保留 + `back_slot_count` 新参（不换 row/slot 二元组）

**裁决：参数定位键保留 `deployed_idx`（deployed 视图统一槽位表下标），新增 `back_slot_count: int = 6`；`row/slot` 只是 op 内执行坐标边的内联换算产物，不升格为参数。**

论证：

1. **三分法归属**：卖出目标 = deployed 排槽位 = ②半固定形态「传下标 + 槽位总数」——下标 = `deployed_idx`（发出面从状态容器视图直取，零换算），槽位总数 = `back_slot_count`（后排布局档 6-9）。`deployed_idx` 本身就是单坐标系（前排 0-3 / 后排 4+ 排内 1 基固定双射，`prep-contract.md` §1 既有声明、词表模块头 `cw_vocab.py:144`「执行坐标边 deployed 下标→(排,排内槽号)固定双射内联算术」既有申报）——内联换算属执行坐标边，不是参数面缺陷。
2. **换 row/slot = 三面 churn 零行为收益**：发出面三构造点全持视图下标（§3.5/§3.6），换二元组 = 每点加一次下标→二元组换算；记账面 `report_action_sell_deployed_param` 按下标直址写（§1.2 核验），换二元组 = 上报层加反向换算；遥测面 `match_archive._sell_deployed_target_names`（:762-801）按序列化字段 `deployed_idx` 解析卖出目标身份，换二元组 = 序列化形状断裂 + 历史帧判读断层。MoveUnit 批先例同构：现成坐标系保留、只补布局档参数（MoveUnit 四元组原样保留 + `back_slot_count`）。
3. **宪法①修复路径**：现 op 执行路径中途读 gs（`back_capacity_of(_gs)`，:66-69）正是为补布局档信息——`back_slot_count` 参数化后该读数拔除，cap 守卫改静态闭合（§2.2），机械路径归零 gs 依赖（自上报取容器 = 上报路径非机械定位，穿装批 §4.1 既有同款裁定）。

**发出面填参（三构造点全 keyword 传参，插字段行为安全；grep 已核全仓仅三处构造）**：

- `deploy_diff.py:100`（换星直卖）：函数已持 `_back_slot_count = back_capacity_of(gs)` 快照（:58-64，MoveUnit 批铺设）→ 补 `back_slot_count=_back_slot_count`。
- `entry.py:699`（yield plan 卖步骤）：函数持 `gs` → 补 `back_slot_count=back_capacity_of(gs)`（函数级 import，`entry.py:335-337` 既有局部 import 风格）。
- `entry.py:857`（`_emit_sell_candidate` deployed 支，第 0/2/7 步共用）：函数持 `gs` → 同式。

缺省 6 兜底帧 = 布局未观察帧（守卫响亮拒绝扩格槽号 = fail-closed 正确方向，MoveUnit 批 §6 条 2 同款判读基线）。`expect` 三构造点现恒缺省 ''（不校验形态）——保留现状，填参完整性归既有代际防线批核（§9 申报行 5）。

### 1.4 拖点权威分域：源 = 角色拖动族裸中心（分域申报既在，本批纯消费侧迁移）；目标 = `sell_point` 出售区单一源（归属核对通过）

- **源端（角色卡槽位）**：`row_area_centers` 裸中心 = 角色拖动族（MoveUnit/SellDeployed/SellBench 阵型操作）权威派生式——`prep_actions.py:143-149` 分域申报已在（MoveUnit 批落地时已把 SellDeployed 列入该族），+21（`row_drag_points`，装备 icon→角色卡族）不外溢（工具批 §11 申报行 2 预告「角色拖动/拖出售区交互族不同」、MoveUnit 批 §1.1 裁决「SellDeployed/SellBench 半随各自迭代裁定（预期同判）」——本批兑现该预期，判 = 同 MoveUnit：整卡可拖、卡中心拖 + hold0 实测背书，落点目标是槽位格不是卡内热区，两族派生式互不外溢）。**声明面零新增**（分域申报两侧 docstring 已成文，本批只换消费路径：executor 构造期缓存 → op 执行期现读同一静态档，坐标值理论逐位同）。
- **目标端（出售区）**：`sell_point`（`prep_actions.py:199-213`）= screen_info「区域-出售区」area 中心单一源，游戏机制 = 拖到左下区域即出售、无按钮；备战画面档自带该 area（`currency_war_battle_prep.yml:761`）。**归属核对结论**：出售区点位不住两族排点位表（非 `前排-N/后排-N/备战栏-N`、非装备族 +21 表），是独立区域 area——卖出交互族（拖角色到出售区）的落点权威 = 该 area 中心，源端才是族分域问题。现 op 已消费 `sell_point`（:87），迁移零坐标变化；`sell_point` 的 area 缺失 RuntimeError 上抛形态保留（共享原语，`drag_bench_to_sell` 同消费——「建档漂移哨」语义非参数违法域，与 op 内 AssertionError 守卫分工既有；两类异常形态不统一，越批界，§9 申报行 6）。
- **拖拽原语**：op 直调 `drag_char_guarded(self, self.ctx, src, dst)`（失焦守卫 + sim 静默 + `DragCwChar.drag_char` 中心拖 hold0）——**不复用** `drag_bench_to_sell`（bench 专属 wrapper：内置备战栏点表 + bench_idx 守卫，形态不同域），与 `drag_bench_to_sell` 的组构成分（`row_area_centers` + `sell_point` + `drag_char_guarded`）同源复用。`drag_bench_to_sell` 本体零改动，其去留归 SellBench 批（§9 申报行 1）。

### 1.5 过渡宿主退役裁决：`_drag` + `_front_pts/_back_pts` 随批退役（SellDeployed = 最后消费者）；`_bench_pts` 保留

grep 全量已核（src + 测试仓）：`ex._front_pts/_back_pts` 现役唯一消费者 = `cw_sell_deployed_action.py:68/81`；`ex._drag` 现役唯一消费者 = `cw_sell_deployed_action.py:87`。本批拔除后三者全仓零消费者：

- **删除** `PrepActionExecutor._drag`（`prep_actions.py:482-510`）与 `self._front_pts/_back_pts` 两属性（:340-341）——MoveUnit 批 §6 条 7「保留至 SellDeployed 迁移批——其迁移批退役时同步清」的本批兑现，退役申报写进 commit message。
- **保留** `self._bench_pts`（:339）：现役消费者 = 开件三类守卫（`cw_open_box_action.py:76-84`/`cw_open_tome_action.py:73-80`/`cw_open_bookcard_action.py:77-84`）+ SellBench getattr 容缺守卫（`cw_prep_sell_bench_action.py:72-80`，双域形态）——各自迁移批退役（§9 申报行 1/3）。
- **注释面同步清单**：执行器类 docstring 过渡宿主声明（:311-313）、`__init__` 三属性注释（:336-338）、装备/工具域段尾「_drag 方法过渡期保留」句（:473-480）、`drag_char_guarded` docstring「SellDeployed 过渡期仍经 executor._drag，其迁移批并入本宿主」句（:225-228 → 更新为三消费者已并入）、模块头「SellBench/SellDeployed 过渡期仍经执行器点表」（:21-23 → 收窄为仅 SellBench）。

**行为等价对照（`ex._drag` → `drag_char_guarded`，逐项）**：sim 分支（`sim_backend_installed()` 静默返回）✓ 同；失焦守卫（后台化先激活 + 0.3s）✓ 同；`DragCwChar.drag_char`（mouse_move settle 0.2s → drag_to duration 1.0 hold0 → 0.5s → park_cursor 0.3s）✓ 同。唯一差 = drag_char 的 `op` 实参从宿主 CwScreenPrep 变为 SellDeployed op 自身（仅 `op.ctx` 解引用面，MoveUnit 批同款）。**行为逐位等价，非新拖拽参数迁移**（与工具批 duration 1.2→1.5 的「有意行为变化」不同类）。

## 2. 新参数面定稿

### 2.1 字段集变更（`kernel/cw_vocab.py::CwActionSellDeployedParam`，L376-395 现值）

- 新增 `back_slot_count: int = 6`（`deployed_idx` 后；[索引定义] 三要素注释：坐标系 = 后排槽位画面物理总数 n，值域 6-9 = `obs.cw_back_layout._LAYOUT_PREFIX` 键域；取值时机 = 生成期快照（发出点 `back_capacity_of(gs)` 现读）；`deployed_idx < 4`（前排域）时忽略）。
- 保留 `deployed_idx`（坐标系与取值时机注释已有，补跨帧队列消费面申报：yield plan 卖步骤 = 跨帧消化形态，发出点按名现读重推导 fail-closed——§1.2 契约②）；保留 `income`（记录非指令）/`reason`（归因记录）/`expect`（遥测观测字段 + 校验保留，[防线写入端] 申报：现役生产发出点恒缺省 ''）/`route_tag`（kw_only + `action_key_exclude` 全族契约不变）。
- 补 `from_dict`（共享形态一行委托 = `cw_vocab.action_param_from_dict`，MoveUnit 同款 `cw_vocab.py:457-461`）；旧帧/旧序列化数据缺 `back_slot_count` 键 → 落缺省 6，历史 `deployed_idx ≤ 9`（后排槽 1-6）值域全兼容。
- docstring 补记账路径总契约适用申报（第四适用者 + 槽位反查无表形态 + 宪法③空集）与 §1.1 交替裁决申报（卖出 aftermath = A1 辖域零置位端）。
- `action_key` 幂等键自动含 `back_slot_count`（行为参数入键正确——同槽位不同布局档 = 不同拖拽落点，禁共享屏蔽粒度；MoveUnit 批 §2.1 同款）。

### 2.2 守卫断言（op 内，校验落点契约；全部 `raise AssertionError` 响亮暴露，禁兜底坐标/禁负下标回环）

1. **新增** `deployed_idx >= DEPLOYED_FRONT_CAPACITY` ∧ `back_slot_count ∉ _layout_prefixes()` → 断言（布局档键域外禁静默按 6 兜底；前排域不查——MoveUnit「域不涉则忽略」同式）。
2. **改静态闭合** `not (0 <= deployed_idx < DEPLOYED_FRONT_CAPACITY + back_slot_count)` → 断言（现状 cap 上界取自 gs 现读，迁移后 = 参数静态；下界显式闭合禁负下标回环——现状 `0 <=` 已有，保留并声明）。
3. **现状保留** 槽号越界 `not (1 <= slot_no <= len(该排点位表))` → 断言（表源改 op 内现读：front = `row_area_centers(ctx,'前排')`、back = `row_area_centers(ctx, _layout_prefixes()[back_slot_count])`——扩格 7-9 槽从必拒变可用，行为修复申报 §7 条 2）。

内联换算保留：`row = 'front' if deployed_idx < 4 else 'back'`；`slot_no = deployed_idx+1`（front）/ `deployed_idx-3`（back）——固定双射内联算术（prep-contract §1 既有申报形态），不抽公共函数（两行算术，全仓三消费面各两行、抽函数 = 无收益耦合面；match_archive 遥测侧换算同判不动）。

### 2.3 记账路径核验：SellDeployed 已合规（槽位反查产物形态），零上报函数改造

§1.2 逐消费面核验结论：记账键 = 槽位下标、记账载荷 = 反查产物/状态推导名——总契约精神在本域既有形态 = 槽位反查（无表形态第二例）。`report_action_sell_deployed_param` 零改造；**op 侧行为变化（本批唯一上报调用面变化）**= outcome 消费（M-r3-1① 同形）：`applied=False` 时 round detail 追加「记账拒单:<reason>(拖拽已发生,账未落)」。本 op 拒单形态现役 = `deployed_idx_out_of_range:{idx}` / `stale_proposal:{expect}!={char_id}`——**零新增拒单码、零退役、零词表变更**（fields.md 回执契约节零改动）。

## 3. 牵涉面清单（逐文件；grep 全量已核）

> 路径根 = `src/sr_od/application/currency_war/`。

### 3.1 `kernel/cw_vocab.py` — §2.1 字段集

### 3.2 `operations/cw_op/cw_sell_deployed_action.py` — op 执行体重写

机械半自持：守卫三形（§2.2）→ 内联换算 + 点位静态解析（`row_area_centers`，back 按档前缀）→ `sell_point` 出售区落点 → sim 分支 `mechanical_io_allowed()` 显式 gate（MoveUnit 同款 :124-133 形态）→ 实机 `drag_char_guarded` + 1.0s 固定等待（用户口述口径「卖出动画 1s」逐字沿用 :88，与 SellBench op 同口径）→ 自上报（outcome 消费，detail 拒单段；摘 `session=` dead 实参）。签名改 `env: PrepExecEnv | None = None`（穿装/工具/MoveUnit 批同款，零 env 消费，形参保留 = 注册表构造签名兼容；MCP 直调自此可达）。docstring 重写（槽位键参数面 + 总契约第四适用者申报 + 三契约槽位域形态 + 拒单禁补拖口径 + deployed_idx 映射指引 + 词表参数面指引）。

### 3.3 `operations/cw_op/cw_action_registry.py` — 零改动

import 与注册行（:143-144/:173）类名不变；组装签名兼容 env 缺省化。注册完备测试机械约束对象不变。

### 3.4 `prep_actions.py` — 过渡宿主退役 + 注释收口（§1.5 清单）

`_drag` 方法与 `_front_pts/_back_pts` 两属性删除；`_bench_pts` 保留；五处注释面同步。`row_area_centers`/`row_drag_points`/`sell_point`/`drag_char_guarded`/`drag_bench_to_sell` 五个原语本体零改动（`drag_char_guarded` 仅 docstring 一句更新）。

### 3.5 `strategies/impl/mandate_v1/deploy_diff.py` — 发出面填参一处（§1.3）

### 3.6 `strategies/impl/mandate_v1/entry.py` — 发出面填参两处（§1.3）

### 3.7 `kernel/cw_action_report/sell_deployed.py` — 零改动（§2.3）

### 3.8 `telemetry/match_archive.py` — 序列化字段枚举注释一行同步

:768「序列化字段 deployed_idx/income/reason/expect，无 row/slot」→ 补 `back_slot_count`（序列化面新增字段的事实申报；解析函数 `_sell_deployed_target_names` 只读 `deployed_idx`，零行为变化）。

### 3.9 测试仓镜像测试 — 见 §5

### 3.10 文档面 — 见 §8

## 4. op 执行语义（迁移后）

1. 守卫断言三形（§2.2）。
2. 内联换算 + 点位静态解析：`row_area_centers(ctx, 前缀)`（零截图零识别零 gs；back 前缀 = `_layout_prefixes()[back_slot_count]`）。
3. sim 分支：`mechanical_io_allowed()` 为假 → 机械段静默跳过（上报函数族照走——sim 期望态推进 = 自上报单点，两执行面同源）。
4. 实机机械段：`drag_char_guarded(self, self.ctx, src, sell_point(self.ctx))`（失焦守卫 → 中心拖 + hold0）→ `time.sleep(1.0)` 固定等待（卖出动画口径逐字沿用）。
5. 自上报：`gs = game_state_from_ctx(self.ctx)`；`outcome = report_action_sell_deployed_param(gs, action, ChannelSig(family='logic_action', actor=type(self).__name__, mode='compute'))`；`gs is None` = 无处记账跳过（outcome=None，detail 不加拒单段）；`outcome.applied=False` → detail 追加拒单段（§2.3）。
6. round 结果：恒 `round_success(detail)`（机械成功语义——拖拽已发出；零 round_fail 通道，回执受阻码表零变更）。

**决策侧参数现算契约适用申报**：本 op 发出域 = 备战决策环（每动作重 decide，同帧承诺成立）。**跨帧队列形态申报**：yield plan 卖步骤 = 计划游标跨帧消化（prep-contract §3 G1 的槽位键族豁免形态——`deployed_idx` 取值时机 = 生成期=执行期恒稳，非坐标伴随域快照；跨帧陈旧由发出点按名现读重推导 + `step.issued` 执行失败出口承接，`entry.py:684-697` 现值）。战斗链批量发射边界载体不涉本 op（发射集 = MoveUnit）。

## 5. 测试设计（sr-od-test，按 §11.4 harness 规范；镜像路径，命名无批次号）

> 现场实态申报：CW 域测试源文件多数仅在 `__pycache__`（wear design §5 同款）——实施角色按当时仓内实态落位：源文件在则改，不在则按下述路径新建。

1. `test/sr_od/application/currency_war/kernel/cw_vocab/test_cw_vocab.py`
   - SellDeployed `from_dict`：全字段 dict 逐字段断言；最小 dict（`deployed_idx` 必填）落全缺省（`back_slot_count=6/income=None/reason=''/expect=''/route_tag=''`）；未知键忽略。
   - `action_key`：`back_slot_count` 不同产不同键；`route_tag` 不入键（`reason` 入键 = SellDeployed 现状非 action_key_exclude 字段，零变化不锁测）。
2. `test/sr_od/application/currency_war/operations/cw_op/test_cw_sell_deployed_action.py`（新建；harness 剧本）
   - 守卫：deployed_idx 负值 / 越界（≥ 4+back_slot_count）/ 后排槽 + back_slot_count 域外 → AssertionError 且零拖拽；前排槽 + back_slot_count 域外不拦（忽略域锁测）。
   - 实机形态（screen_info 真档案 → 期望值同源派生）：front 槽拖拽记录 `start == 前排-N rect 中心`（裸中心锁测）、`end == 区域-出售区 rect 中心`（sell_point 同源锁测）；back 槽按档位表（含 `back_slot_count=7` → `后排7槽-N` 档，行为修复锁测——形态照 `test_cw_move_unit_action.py` 既有锁测）。
   - **round detail 拒单码**：种子使上报拒单（状态容器 deployed 视图该槽空槽，机械面不读 gs 拖拽已发出）→ round_success 且 detail 含「记账拒单:deployed_idx_out_of_range:…(拖拽已发生,账未落)」；`expect` 填名不符种子 → detail 含 stale_proposal 段；正常记账帧 detail 不含拒单段。
   - `env=None` 全链；sim 形态（port 关闭 → 机械零调用 + 自上报照走）；`with fast_sleep(): op.run()`。
3. `test/sr_od/application/currency_war/strategies/impl/mandate_v1/deploy_diff/test_deploy_diff.py`（既有文件扩展）
   - 换星直卖 `back_slot_count` 填参锁测：种子 `back_layout=8` → 卖出动作 `back_slot_count == 8`；None → 6。
4. `test_action_registry.py`（既有面）：零改动预期。

验收阶梯（skill §3）：L1 → L2（点名新增文件 + test_action_registry）→ L3 全量 commit 前。**实机验收序列 = §11**。

## 6. sim 形态自洽结论

**结论：零 sim 改动。**

1. 机械段：op 显式 `mechanical_io_allowed()` gate（现状 = `ex._drag` 内部 `sim_backend_installed()` 静默，迁移后语义逐位等价，§1.5 对照表）；sim 局与实机同跑同一循环/op/策略，上报函数族两执行面同源直调同一函数（bridge.py:353-354 商店序列驱动器 / flow.py:897-898 回放驱动器直调零改动）。
2. 期望态推进：卖出记账 = 槽位反查（`deployed` 动态视图直址 + `sold.equips` 状态推导），不依赖任何伴随域快照——sim 形态与实机同核零分叉。
3. 装备网格伴随域：卖出 aftermath 的回装件由 sim 占位同步在 advance 步界按计数差 append 哨兵占位（获得方向 = 同步主路径），存量占位坐标恒不变、按名反查恒正确（§1.1 sim 零失效面）；`cw4_equip_xy_pending` 交替标志零置位端变更，sim 的重观察帧退化语义不变（工具批 §6 条 5 既有申报）。
4. `back_slot_count`：sim 局 `back_layout` 伴随域 = 环境快照族字段（宝钻扩展经 sim 效果链写），发出点 `back_capacity_of(gs)` 与 op 守卫同一读口同一档（MoveUnit 批 §1.5 sim 形态同构）；布局未观察帧缺省 6 = fail-closed 拒扩格槽号。
5. 直调路径：MCP `run_operation`（from_dict 通道）传非法 `deployed_idx`/`expect` → 机械拖拽仍发出、上报拒单零写，round detail 带拒单码（§5 条 2）——直调方按 detail 感知，**禁补拖**（处置 = 重读 extras 按新板面重派）。

## 7. 风险与行为变化清单

1. **行为变化：round detail 新增拒单段**（outcome 消费）——journal 判读面新增「记账拒单:…」段（现役触发 = 陈旧提案拒单帧：deployed_idx_out_of_range/stale_proposal）；遥测分键零新增（reason 词表封闭不动），首局对照判读申报。
2. **行为修复：扩格局后排 slot 7-9 直卖从机械段必拒变可用**（现状点表只匹配基线 6 槽，上报侧直读动态视图两面不一致）；判读基线：扩格局（宝钻 7/8/9）换星直卖/腾席直卖完成率预期上升。发出点填参随批落地（§3.5/§3.6），缺省 6 兜底帧 = 布局未观察帧（守卫响亮拒绝扩格槽号 = fail-closed 正确方向）。
3. **`action_key` 幂等键扩域**：键含 back_slot_count——既有键形态历史数据不可比，判读基线申报（MoveUnit 批 §6 条 3 同款）。
4. **拖点坐标等价性**：`row_area_centers` 裸中心 + `sell_point` 零变化（同源同一静态档）；坐标源路径变化（executor 构造期缓存 → op 执行期现读）理论零差，实机落点核对 = 背书义务（§1.4/§11 验收①②）。
5. **`_drag`/`_front_pts/_back_pts` 退役**：行为逐位等价原语并入（§1.5 对照表），风险面 = 等价性自证依赖对照表——实机验收①即覆盖（卖出落点 + 生效核对）。
6. **宪法①修复：机械路径 gs 读拔除**（`back_capacity_of` 中途读 → 参数静态闭合）——零 gs 依赖后 cap 守卫不再随观察态漂移，扩格槽号在「布局已观察但参数未填」帧响亮拒绝（fail-closed），判读时 round 异常栈直接指向参数缺失。
7. **dead `session=` 实参摘除**：零行为差（上报函数体零消费已核 §0）；上报函数签名不动。
8. **交替机制零改动（§1.1 裁决的风险敞口登记）**：A1 不成立时卖出后同 visit 穿戴帧盲拖错格 + 反查错账——既有治理结构兜底（跳过自愈/反查拒单/观察对账失配告警），A1 验证批为统一收编点（§9 申报行 2）。

## 8. 文档与 skill

- `skills/sr-od-dev-currency-war/references/flow/prep-contract.md`（**实施批落地**——本稿点名逐节内容，文档随实施 commit 落保正本与代码现状一致；当前无并行批在飞改动已核）：§1 L9 动作字段坐标系族描述更新（SellDeployed 补 back_slot_count 与 op 自持点位解析，「SellBench/SellDeployed 过渡期仍经执行器点表」收窄为仅 SellBench）；§3 取值时机表补 SellDeployed 行（deployed_idx = 生成期=执行期槽位表恒稳 + 跨帧队列消费面申报；back_slot_count = 生成期快照 `back_capacity_of(gs)`，前排域忽略）；§5 卖出臂行同步（机械半自持/outcome 拒单 detail/拖点裸中心+sell_point）；§5 换人臂行修复过期引用「后续 DeployMove 补部署」（DeployMove 已退役，统一拖动承载）。
- `skills/sr-od-dev-currency-war/references/flow/action-op.md`（**收尾义务，本批不动**——该文件有并行批措辞规范化清扫在飞未落库，禁混提交）：§5 备战族 SellDeployed 行改写（机械半自持/back_slot_count/守卫三形/拒单 detail/拖点裸中心+sell_point/过渡宿主退役）；§1 记账路径总契约条款批次计数推进（「已迁三批」→「已迁四批」，依赖 MoveUnit 收尾补行先落）+ 本 op 逐 op 差异附记（槽位反查无表形态第二例 + 交替延伸裁决：卖出 aftermath = A1 辖域零置位端）。并行批落库后由实施/收尾角色执行。
- `docs/develop/sr_od/application/currency_war/game_state/fields.md`：零改动（零 gs 字段变更、零拒单码变更）。
- 玩家 skill `skills/sr-od-currency-war/`：零改动（卖出族非玩家直调面；MoveUnit 批同款裁定——from_dict 通道为开发者/单件会话形态，op docstring 自足）。
- sim-design.md：零改动（零 sim 行为变更；§6 自洽结论不新增申报行——MoveUnit 批同判）。

## 9. 申报行（相邻问题，本批不修）

1. **SellBench 待后续独立迭代**（用户裁定：每迭代只切一个 op）：牵涉面 = 双域 env 形态保留裁定（PrepExecEnv/ShopExecEnv 双端口 + getattr 容缺守卫 vs `drag_bench_to_sell` 内置点表守卫的双守卫形态）、`drag_bench_to_sell` wrapper 去留、outcome 消费（`bench_idx_out_of_range`/`stale_proposal`）、from_dict、`_bench_pts` 最后消费者判定、A1 回退归属（§9 行 2 同族）。
2. **获得类动作 + 卖出族 aftermath 的交替标志回退归属 = A1 实机验证批统一裁决**（§1.1 裁决落点）：收编面 = CollectOre/OpenBox/OpenTome/OpenBookcard/PickSupply 获得件 + SellDeployed/SellBench 装备回收，单标志多置位端机制零新增；验收入口 = 穿装批 §8.6「采晶矿→穿装」序列，扩展「卖出→穿装」序列同批验证。
3. 开件三类（OpenBox/OpenTome/OpenBookcard）仍消费 `executor._bench_pts` 做守卫 + bookcard slot=None 硬 gs 分支已知项——开件族迁移批随批退役 `_bench_pts`（MoveUnit 批 §9 行 2 既有登记延续）。
4. Pick* 族契约状态——既有登记，非本批。
5. SellDeployed 三发出点 `expect` 恒缺省 ''（不校验形态）——与 MoveUnit 批 §9 条 4 同形，提案代际防线填参完整性归该批核；本批保留现状零填参。
6. `sell_point` RuntimeError（area 缺失建档漂移哨）与 op 守卫 AssertionError 两类异常形态并存——共享原语跨域（SellBench/商店域同消费），统一归 SellBench 批或异常形态专项，本批不动。
7. match_archive `_sell_deployed_target_names` 与 op 内联换算各持一份 deployed_idx→(排,槽号) 双射算术（三消费面各两行）——抽公共函数收益为负（§2.2 裁决），若未来换算面增多再议。

## 10. 实施顺序建议（给实施角色）

1. `cw_vocab.py` param 扩字段 + from_dict + docstring（§3.1）。
2. `prep_actions.py` 过渡宿主退役 + 注释收口（§3.4）。
3. `cw_sell_deployed_action.py` op 重写（§3.2/§4）。
4. 发出面填参三处（§3.5/§3.6）→ `match_archive.py` 注释一行（§3.8）。
5. 测试（§5）→ 文档（§8；prep-contract 同批落）。
6. MCP server 重启 → `describe_operation_flow` 核对 op 节点图（恒 round_success 单节点形态）→ 实机验收序列（§11）。

## 11. 实机验收序列（给实施角色）

1. **拖拽落点核对（§1.4 义务）**：①前排槽直卖一例（起 = 前排-N 中心、终 = 出售区中心；下一帧实读：板上少人 + 库存多卸装件 + 回金）；②扩格局（宝钻 7/8/9）后排槽直卖一例（行为修复核对，§7 条 2）。
2. **「卖出→穿装」序列旁证（§1.1 A1 辖域）**：卖一场上带装件 → 下一帧若发穿戴步，观察回装件走「坐标缺席跳过 → Obs outer_loop → 重派」通道不炸账；同 visit 存量件穿戴落位正常（A1 成立旁证，不钉结论）。
3. **直调单件会话**：run_operation 跑 SellDeployed 一例（from_dict 通道，env=None），核对 round detail 与落位；拒单形态一例（非法 expect 或空槽 idx）核对「记账拒单:…」段。
