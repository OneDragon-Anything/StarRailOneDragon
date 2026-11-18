# 备战逻辑态面契约(prep-contract)

> 备战阶段的「逻辑态面」= 状态容器面板与观察帧字段向执行臂暴露的读写面。本篇 = 该面与执行侧(部署臂/换人臂/卖出臂/装备臂)之间的接口契约:消费方读什么字段、写入端承诺什么不变式、取值时序、坐标系声明。路径根 = `src/sr_od/application/currency_war/`;代码定位一律用 `文件::符号名`。

## 1. 坐标系

- **bench(备战栏)**:`gs.bench`(BenchView,slots 定长 = capacity,列表下标 0-8 = 物理槽位 1-9 减一;空槽 = `kind='empty'`)。容量判据 = 派生单一源 `bench_free_slots`/`bench_is_full`,**禁止 `len(slots)` 数占用**。
- **deployed(上阵)**:`gs.deployed`(DeployedView 统一槽位视图,`front_slots[i]` = 前排物理槽 i+1(定长 4)/ `back_slots[j]` = 后排物理槽 j+1(**动态容量 6-9**,上限 = `DEPLOYED_BACK_CAPACITY_MAX`;扩展格进视图);位置 = 子表下标纯派生,下标 0-3 = 前排槽 1-4、4-9 = 后排槽 1-6)。权威槽位恒为子表下标(`Unit` 不存槽位信息位,阵营不入 Unit——由 char_id 查角色注册表派生)。
- **动作字段坐标系(统一动作类型清单,零换算)**:席位域动作(SellBench.bench_idx/SellDeployed.deployed_idx)直携状态容器槽位表下标(0 基);MoveUnit = 统一拖动四元组 `(src_domain, src_slot, dst_domain, dst_slot)`(bench 0 基 / front/back 排内 1 基画面槽号)+ `back_slot_count`(后排槽位画面物理总数 6-9,生成期快照,发出点 `back_capacity_of(gs)` 现读——MoveUnit 参数面迁移批新增;src/dst 域均非 back 时忽略);SellDeployed = `deployed_idx`(deployed 视图统一槽位表下标,前排 0-3 / 后排 4+ 排内 1 基)+ `back_slot_count`(同 MoveUnit 口径,SellDeployed 参数面迁移批新增;deployed_idx < 4 前排域忽略;row/slot 只是 op 内执行坐标边的内联换算产物,不升格为参数);坐标参数化机械动作(开件三类 OpenBox/OpenTome/OpenBookcard)的 row/slot = 画面物理排槽位 1 基(拖点直取 area,不经换算);穿装 WearEquip 与工具原子七类已升级「动态坐标显式传 + row/slot 半固定」形态(src = 1080p owned 格心显式坐标——WearEquip.src_cx/src_cy / 工具 tool_cx/tool_cy,equip 模式另带 tgt_cx/tgt_cy 目标;槽位拖点经 `prep_actions.row_drag_points` 静态解析,零读屏)。**拖点权威分域(角色拖动族 = 裸中心)**:MoveUnit/SellDeployed 拖点 = `prep_actions.row_area_centers` 裸中心(整卡可拖、卡中心拖 + hold0 实测背书;装备 icon→角色卡族 = `row_drag_points` +21,D-36 校准——两族交互机制不同,派生式分域互不外溢,申报见两函数 docstring)。执行坐标边:MoveUnit/SellDeployed = op 自持(各自参数面迁移批,op 内经模块级原语现读点位表);其余席位域动作(SellBench)过渡期仍经 `PrepActionExecutor` 点表(其迁移批自持化)。
- **画面点位**:点位单一源 = screen_info「货币战争-备战」的 `备战栏-N`/`前排-N`/`后排-N` area,经 `prep_actions.py::row_area_centers` 按 N 升序读出中心点;执行器构造时读一次备战栏点位表(开件三类守卫与 SellBench 守卫过渡期消费),场上排点位 = 各 op 内经 `row_area_centers` 现读;后排点位按 cap 差公式选档(`cw_back_layout.py::select_back_layout` 单一入口)。
- 遥测/推进清单 path 形态判读分域:`bench.slots[N]` = 0 基;`deployed.{row}.{slot}` = slot 1 基。

## 2. 写入端不变式(逻辑态面对消费方的承诺)

1. **槽位表形状**:`gs.bench` 与 `gs.deployed` 为唯一定长槽位表;动作落地整值替换、无洞语义,「生成期索引 = 执行期索引」在单轮内成立。
2. **排路由不在写端**:写端不做排归属的二次决策——跨排移动按载荷落点直写,排路由在发出期由策略层 `deploy_row_pref`(comp 站位覆盖 > 注册表 position_pref 派生 > back 兜底)定。
3. **快照隔离**:`kernel/cw_exec_state.py::snapshot_copy` 浅拷贝 + equips 固化 tuple 断开对象别名。
4. **席位单账直写**:卖出/部署/换位 handler 直写主域字段,交换语义镜像——被占位单位回源槽。落地事实的权威判定 = 观察边界对账(以实际观察为准,权威 = 备战入口 heavy 观察,星级抖动门驻 `kernel/cw_reconcile.py`)。
5. **披露面承诺**:预算遥测披露面四字段 + 键戳,唯一写点 = `economy_cycle.disclose_budget`,两调用点 = 备战决策入口与店开帧覆写;披露面是遥测列非决策输入,禁决策消费。
6. **期望态两执行面同源**:原子动作的期望态推进唯一入口 = 上报函数族(实机 op 自上报 = sim 侧同构同一段代码直调同一上报函数,回放驱动器同族)——两执行面同走同一函数族,单点即同源。商店 payload 的落地:刷新上报的牌面随机采样经 kernel 发牌采样器采样(与 sim 同一发牌代码),走 `write_logic_rand` 随机态专用通道写入;实机上采样只是猜测——下一帧实际观察若与采样不一致,属预期内差异,落 `logic_rand_outcome` 台账、不进失配告警。
7. **装备 owned 搬运链**:装备 owned 快照写端 = 备战入口观察装配点;穿戴写入 = `report_action_wear_equip_param`(owned −1 + 目标角色 equips +1,上报函数单点);工具上报 = 坐标反查记账同族(消耗移除与效果分支 `gs.equips` 合并单笔写,反查不到 = 拒单零写,记账路径总契约第二适用者)。

## 3. 时序:生成期快照 vs 执行期现读

- 生成期 = 决策帧装配时点(入口 heavy 观察到动作发出之间);执行期 = 执行器真正读屏/拖拽时点。
- **携 `expect` 代际校验的动作**(卖出/换位类):`bench_idx`/`deployed_idx` 取值时机 = 生成期=执行期(槽位表恒稳);提案代际校验字段 `expect`(期望名)由发出点写入,应用时名不符 → `stale_proposal` 拒绝。
- **坐标参数化机械动作**(穿戴/工具/开件类):`slot`/`row` 取值时机 = 生成期快照,**无 expect 代际校验字段**。防线依赖两个前提:①单动作循环生成即执行,决策-执行间隙内画面由逐动作逻辑态直写推定;②执行拖拽机械单发,发出即记账。若此类动作进入跨帧队列,该前提失效,需先补代际防线(活缺口 G1)。
- **WearEquip(坐标显式传形态)**:`src_cx`/`src_cy` 取值时机 = 发出面决策帧的坐标伴随域(`gs.owned_equip_xy`)快照,同访问内上一穿戴帧后经环内重观察刷新(装备网格伴随域新鲜度交替,载体 = `StrategyState.cw4_equip_xy_pending`,穿装与工具 aftermath 共置位共用重观察帧);`row`/`slot`/`back_slot_count` = 生成期快照。
- **工具原子七类(坐标显式传形态)**:`tool_cx`/`tool_cy`(源)与 `tgt_cx`/`tgt_cy`(equip 模式目标)取值时机 = 发出面决策帧的坐标伴随域快照(发出点 = entry 第 7 步,经 `cw_equip_env.tool_use_params_of` 取数;同一交替载体 `cw4_equip_xy_pending`,置位帧零参数构造);`row`/`slot`/`back_slot_count` = 生成期快照。
- **消费方不得把坐标参数化动作的字段当执行期索引复用**。
- **MoveUnit(槽位键 + back_slot_count 形态,参数面迁移批)**:`src_slot`/`dst_slot` 取值时机 = 生成期=执行期(槽位表恒稳——移位置 None/empty 不移位,上款卖出/换位类同域);`back_slot_count` = 生成期快照(发出点 `back_capacity_of(gs)` 现读,None 退 6 基线;op 侧按布局档静态解析后排拖点,扩格 7-9 槽随此可达);`expect` 代际校验照上款(换位类防线,战斗链批量发射边界载体的陈旧化治理依赖 report 静态域拒绝,action-op.md §1 边界载体登记)。
- **SellDeployed(槽位键 + back_slot_count 形态,参数面迁移批)**:`deployed_idx` 取值时机 = 生成期=执行期恒稳(槽位表恒稳——卖出置 None 不移位,上款同域);yield plan 卖步骤 = 跨帧队列消化形态,陈旧由发出点按名现读重推导 + `step.issued` 执行失败出口承接(fail-closed——槽位键族豁免 G1 跨帧禁入形态,键恒稳使跨帧消化合法);`back_slot_count` = 生成期快照(发出点 `back_capacity_of(gs)` 现读;deployed_idx < 4 前排域忽略);`expect` 代际校验照上款(现役生产发出点恒缺省 '')。

## 4. 备战线数据流时间线

```
备战节点入口 heavy 观察(唯一读屏点)
  → 状态容器 game state 直写(观察装配点)
  → bridge.decide_prep_screen:方向版本标记消费(读后即清)
  → 决策链最先检查的发出点 _launch_front_check(出战就绪帧短路 return;短路帧不披露)
  → 预算遥测披露 economy_cycle.disclose_budget
  → 决策(decide_prep_frame → entry.emit 三遍编排;决策输入 = 状态容器直读;
     动作产出 = 恰一个动作)
  → 帧稳定截断(单动作循环逐帧恰取一个动作,本帧无动作 = Obs outer_loop
     返回主循环重观察)
  → 执行(PrepActionExecutor 分派 → CwActionXxxOp 节点直调)
  → op 自上报(动作后逻辑态唯一更新点 = 上报函数族单点)
    → 下一动作或终结 op
```

## 5. 消费方读什么(逐臂)

| 臂 | 载体 | 读法 |
|---|---|---|
| 部署臂 | 备战环动作路径:统一部署搜索定型目标板(`deploy_search.search_deploy_target`)→ 差分执行器产动作序(`deploy_diff.deploy_diff_target_actions`)→ `CwActionMoveUnitOp` | 逐动作机械拖拽 + 自上报(零像素判效);计划执行期(前置步驱板)= 拖动与重观察交替(`pending_reobserve`,连续 2 次无进展 = 级联卡死出口);MoveUnit 已随参数面迁移批 op 自持(back_slot_count 发出面填参 = `back_capacity_of(gs)`,拖点 = 裸中心权威分域);kernel `cw_deploy_logic.py::residual_fill_plan` = 残余补位 |
| 换人臂 | 发出面 `mandate.py::emit_swap_redeploy`;执行面 = `CwActionSellDeployedOp` 卖出 + 统一拖动补部署(`CwActionMoveUnitOp`;DeployMove 已退役,统一拖动承载) | 发出面 = 决策帧槽位表;计划单一源 = `assemble_swap_plan_inputs`+`select_swap_plan`(发出侧同函数同参,禁第二份口径);发出⇔执行归因透传 = `StrategyState.cw4_m1p_arm_pending`(帧级无条件复位);发射面分键 = `cw4_counters`(键登记单一源 = emit_swap_redeploy 写点注释) |
| 卖出臂 | SellDeployed:发出面三构造点(`deploy_diff` 换星直卖 / entry yield plan 卖步骤 / entry `_emit_sell_candidate` deployed 支)→ `CwActionSellDeployedOp`;SellBench:`CwActionSellBenchOp` | SellDeployed = 机械半自持(deployed_idx + back_slot_count 布局档静态解析排槽拖点,`row_area_centers` 裸中心 → `sell_point` 出售区单一源,拖拽原语 `drag_char_guarded`;扩格 7-9 槽随档可达)+ 自上报(槽位反查记账,deployed_idx 越界/空槽 = `deployed_idx_out_of_range`、expect 失配 = `stale_proposal` 拒单零写,拒单经 round detail 拒单段透出,禁补拖);SellBench = `bench_idx`(槽位表下标 0-8)+ `expect` 期望名;`drag_bench_to_sell` 直收 0 基,机械单发发出即记账;自上报(expect 非空失配 = stale_proposal 拒零写 + 置 empty + 回金 + 装备回收) |
| 装备臂 | 发出点 = mandate M7 装备段(判据单一源 = `kernel/cw_equip_wear_plan._build_equip_wear_plan`;参数列表单一源 = `wear_param_steps_of`,发出面坐标伴随域消费单点)→ `CwActionWearEquipOp` | owned 装备域(`gs.equips` 快照,观察装配点直写)+ 坐标伴随域 `gs.owned_equip_xy`;机械半形态 = 显式起点(src_cx/src_cy)→ 槽位拖点静态解析(row/slot + back_slot_count → `row_drag_points`,零截图)→ 固定等待 settle → 单次拖拽(零判效)→ 自上报(坐标伴随域反查件名记账,反查不到 = `wear_item_xy_unresolved` 拒单零写);新鲜度 = 装备网格伴随域交替标志 `cw4_equip_xy_pending`(置位帧产 `Obs(in_place)`)+ 坐标缺席跳过自愈双通道 |
| 工具臂 | 发出点 = entry 第 7 步工具段(判据/准入单一源 = `kernel/cw_equip_env.evaluate_tool_actions`/`admitted_tool_actions`;参数列表单一源 = `tool_use_params_of` 坐标伴随域消费口)→ `CwActionToolUseOp`(七类共 op) | owned 装备域 + 坐标伴随域双键(tool_cx/tool_cy 源;equip 模式另带 tgt_cx/tgt_cy 目标,双坐标齐备才产原子,缺席跳过 + 计数自愈);机械半形态 = 显式起点 → equip 显式目标坐标 / char 槽位拖点静态解析(row/slot + back_slot_count → `row_drag_points`,零截图)→ 固定等待 settle → 单次拖拽(零判效)→ 自上报(记账 = 坐标反查,反查不到 = `tool_xy_unresolved`/`tool_target_xy_unresolved` 拒单零写,精密扳手 consume=False 豁免注记;`tool_target_unit_missing` 升格拒单);新鲜度 = 同一交替标志 `cw4_equip_xy_pending`(entry 第 7 步步首检查 + 提前 return,置位帧零参数构造) |

## 6. 活缺口登记(对照「索引/槽位字段必须带定义注释」条款;只登记,不改代码)

| # | 文件::符号 | 缺口 | 影响 |
|---|---|---|---|
| G1 | `kernel/cw_prep_actions.py` 坐标参数化族槽位字段 | 坐标系有声明,**取值时机零声明**;「无 expect 代际校验、依赖单动作循环生成即执行短间隙」的结构边界未写在动作定义处 | 坐标参数化动作一旦进入跨帧队列即无代际防线;接入跨帧队列前必须先补 expect 类防线或取值时机声明(WearEquip 与工具原子均已随坐标伴随域 + 装备网格伴随域交替标志补防线,现役辖域收窄为开件族箱/典籍/书册卡) |
| G2 | `obs/cw_identity_obs.py::find_armory_boxes`/`find_tomes`/`read_armory_boxes`/`read_tomes` | 返回值 `slot_idx` 的基(1 基)只在实现里,函数级 docstring 未声明 | 消费方 `OpenBox.slot`/`OpenTome.slot` 的 validate 与匹配全依赖此基;声明缺失 = 新读取方易按 0 基惯例错拿 |
| G3 | `kernel/cw_deploy_logic.py::residual_fill_plan` | `bench_idx` 的基与入参键域只在调用方局部变量注释里有,函数自身 docstring 未声明 | 离线构造入参时键域无函数级依据 |
