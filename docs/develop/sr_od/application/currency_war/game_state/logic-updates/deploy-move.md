# 部署(DeployMove)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。数值只写常量名,单一源在代码。

## 1. 动作是什么

把备战席某槽位的角色拖到上阵(前排/后排)指定槽落位——腾位链与部署义务的原子步。动作类型(`kernel/cw_vocab.py` 清单中的类)= `CwActionDeployMoveParam`(状态容器(GameState)(GameState,游戏状态对象,下同)动作域,`cw_vocab.py::Action` 联合已登记;字段 `bench_idx` = bench 槽位表下标 0-8、`to_row` ∈ front/back、`to_slot` = 排内 1 基画面槽号(表下标 = 排内槽号内联换算(to_row, to_slot))、`faction` = 上阵后 board 阵营计数所需,执行面不消费)。op 载体 = `operations/cw_op/cw_deploy_move_action.py::CwActionDeployMoveOp`(非终结;体迁自执行器,原薄委托 `prep_actions.py::PrepActionExecutor._deploy_move` 已随死代码清偿移除,执行 = op 直执行 + 自上报)。**动作发出形态(原子通路)** = 决策核逐帧发出 DeployMove 序,备战环逐帧执行决策输出的恰一个动作(None = 本帧无动作,返回主循环重新观察);组合壳(RunDeploy)已停用。**动作发出点的计划构造单一源** = `strategies/impl/mandate_v1/deploy_plan.py::deploy_plan_moves`(选人 `select_deployments_reasoned` + 排路由 `deploy_row_pref` + 槽位 `deploy_slot_plans`;mandate 动作发出点与 cw_loop 出战链 `battle_chain_deploy_params` 共用,禁第二套计划装配);执行落位零现读——落位意图全部在载荷 `(to_row, to_slot)`,执行边与字段写操作侧按载荷直落。

## 2. 逻辑态域集

字段写操作入入口 = 上报函数 `kernel/cw_action_report/deploy_move.py::report_action_deploy_move_param`,写域 = bench / front_row / back_row / board(board 派生随行写挂钩;gold/xp/level 不触,申报面 = 函数 docstring):

| 域 | 写 / 跳写(跳写 = 留空不写、等观察覆盖) | 说明 |
|---|---|---|
| bench | 写 | 源槽摘除(槽 kind → `empty` 不移位),**原生 `BenchView.slots` 直操**(不经任何换形往返,kind 五分类保形;evidence `proj_deploy_src_clear`) |
| front_row / back_row | 写 | 载荷 `(to_row, to_slot)` 经换算单一源 内联换算 定表下标落位后,`deployed_indexed_to_rows` 展开整行 `write_logic`(evidence `proj_deploy_front` / `proj_deploy_back`) |
| board | 派生随写 | **派生量**:front_row/back_row 有行写入时挂钩 `GameState._resync_board_delta` 自动增量重算(evidence `proj_board_resync`),禁止在本分支手写 board |
| 上阵计数 | 派生 | 零独立字段,`deployed_count_of` 读口现算 |

**装备随人走**(对象整体迁移):身份/星级/装备随落位对象迁入目标行。

**上阵变换窗**(仅落位分支对命中):`kernel/cw_action_report/deploy_move.py` 常量 `_TRANSFORM_CHAR_ID`/`_TRANSFORM_STAR`/`_TRANSFORMED_STAR` = 银狼LV.999 3★ 拖上场 → 落场写**下一费用档 1★**(身份保持,非 3★ 原样);变换后的合成连锁走 `cw_effect_inventory.merge_cascade_write`(evidence `proj_deploy_lv999_merge`),转移细则 = §3 第 3 条。

配套账随动作同步:

- 席位单账:本上报直写主域——deployed 视图整值替换(载荷 `(to_row, to_slot)` 经排内槽号内联换算定子表下标),bench 侧源槽置 `empty`;交换语义镜像——目标槽有人 = 被占位单位回源 bench 槽。无平行第二账。

## 3. 确定面转移规则(逐条)

1. **状态容器分支守卫**(先试落位后写账):`to_row` 非法(∉ front/back)= 参数非法零写;源槽空/非 unit/越界 = 陈旧提案零写;载荷槽越出定长表或换算回读与载荷 (排, 槽) 不符(跨排,如 front 5 号落在表后段)= 载荷非法零写——静默零写等观察覆盖;
2. **目标落位** = 载荷 `(to_row, to_slot)` 直指(换算 = 排内槽号 ↔ 子表下标内联算术,与执行拖点同源无分叉):目标槽空 = 放置;有人 = 交换——被占位单位整体回填源 bench 槽(与 `report_action_swap_deploy_param` 换位契约同语义,装备随对象,);禁占位拒绝、禁静默换槽(不另寻空位);
3. **上阵变换窗(银狼LV.999 3★ 落位分支对)**:拖拽载荷唯一指定源 = 恰此一枚(无歧义,免多枚三态判定)→ 落场单位写**下一费用档 1★**(常量单一源 = 上报函数;角色固有升星升费:备战栏不升费、拖上场才触发,机制锚 = `docs/game/gameplay/currency_war.md`「银狼LV.999 升星升费」条;身份保持,槽位随拖拽落点、观察为真值);其余单位恒等搬运零行为差。变换后的合成连锁 = `cw_effect_inventory.merge_cascade_write`(evidence `proj_deploy_lv999_merge`):正常路 = 常规引擎逐级合并、受影响域各落一行(确定面 `write_logic`);涉 LV.999 跨档合并(merge 身份键 = (char_id, star) 无费用维度,跨档禁猜)尚未定案 → 自动降级 = bench/front_row/back_row 值不变、来源标记翻转(恒随机态标记 `write_logic_rand`,evidence 后缀 `#lv999_hold`,观察覆盖差异属预期、由观察收尾)+ 保留证据的记录行 `LV999_MERGE_UNDECIDED_KIND`,定案后恢复推演;
4. **开拓者形态归一挂字段写操作入入口**:开拓者按目标排换形态(char_id 随排切换,board 计数不再错账)= 上报函数内 `cw_exec_state.trailblazer_row_unit`(归一核单一源 = `trailblazer_row_identity`,与 swap 上报同源——换排 = 命途切换,deploy/swap 两上报统一归一入口);tracked 侧同核(上报函数 DeployMove 分支);
5. **同名同星已在场拒**(恒成立约束「场上同名同星 ≤1」,`research/merge_mechanics.md` §3):守卫 = 上报函数内 `board_unique_key` 同名唯一性判定(与 sim 同源)——同名唯一键命中即整体不迁移;
6. **board 派生增量口径**:board 现值为 None(板未读过)跳过等观察首读;否则对本次行写做单位多重集差(键 = `_rows_unit_key`)——新增单位逐个加其羁绊标签(`_row_unit_tags` → `kernel/cw_bond_equips.py::unit_bond_tags`,星徽/卡带贡献在内)、移除单位逐个减、减至 0 摘键;观察基座的装备羁绊真值保留(禁全量重算抹基座);未知身份(注册表外/OCR 误读)零贡献,禁 faction 兜底(Unit 不存阵营防注册表双源);
7. **机械执行**(零判效——发出后不读屏验证是否生效,发出即记账):源拖点 = `bench_idx` 备战栏 area 序直取(状态容器下标 = area 序,零换算)→ 落点 = 载荷槽对应排 area 序 `to_slot - 1`(落位意图全部在载荷,执行边零现读零决定)→ `_drag`(DragCwChar 中心拖 + 失焦守卫)→ 固定等待 2s 徽章动画(`research/screen_flow_timing.md` #10)→ `上报直写主域`;
8. **执行器拒绝通道**:载荷槽越出画面槽位数（含 to_slot < 1 的负下标回环形态——`action_ops.md` §1 坐标裁定「禁负下标直取列表」）= 调用方 bug，op 内守卫断言 `AssertionError` 响亮报错（terminal-fail-status 批：原 round_fail「陈旧载荷观察重派」吸收形态废弃）。

## 4. 随机面

画面时序面(非逻辑态):徽章动画 ~2s / overlay 延迟弹出(`research/screen_flow_timing.md` #10/#24)。逻辑随机态唯一面 = 上阵变换窗的涉 LV.999 级联降级(§3 第 3 条):跨档合并尚未定案 → bench/front_row/back_row 值不变、来源标记翻转(随机态标记,观察覆盖差异属预期、不触发失配告警)+ 保留证据的记录行;定案后恢复 merge 推演确定面。

## 5. 拒绝语义

- 状态容器分支三守卫(§3 第 1 条)= 静默零写,等观察覆盖;
- 同名同星已在场 = 游戏拒(§3 第 5 条,tracked 口守卫);
- 执行器载荷槽越出画面槽位数（含 to_slot < 1）= 调用方 bug，op 内守卫断言 `AssertionError` 响亮报错（terminal-fail-status 批）；目标槽拖拽未落地 = 零变化,下一入口完整观察实读对账把差异暴露出来——机械零判效(发出后不读屏验证是否生效):拖拽静默不生效属执行环境噪声,账实失配 → 失配告警停机 → 按真 bug 修,重试 = 决策循环按新观察自然重派;
- validate 静态参数拒(`bench_idx` 越界 / to_row 非法)= 发出前输入契约拒绝。

## 6. kernel 符号锚

`kernel/cw_action_report/deploy_move.py::report_action_deploy_move_param`(bench 侧原生 `BenchView.slots` 直操;变换窗常量 `_TRANSFORM_CHAR_ID`/`_TRANSFORM_STAR`/`_TRANSFORMED_STAR`)/ `GameState._resync_board_delta`(board 派生挂钩单一源)/ `_row_unit_tags`;`kernel/cw_effect_inventory.py::merge_cascade_write`(降级感知合成级联单一消费体)/ `lv999_cascade_blocked`(涉 LV.999 跨档禁猜降级判据);`kernel/cw_action_report/deploy_move.py`(同名守卫 + 载荷落位 + 开拓者形态归一内聚上报);`kernel/cw_exec_state.py` 工作表桥(`deployed_indexed_of_view`/`deployed_view_of_indexed`) / `deployed_indexed_to_rows` / `trailblazer_row_unit`;`strategies/impl/mandate_v1/deploy_plan.py::deploy_plan_moves`(动作发出点计划单一源);`kernel/cw_bond_equips.py::unit_bond_tags`(羁绊标签单一源);`prep_actions.py::PrepActionExecutor.上报直写主域`;`operations/cw_op/cw_deploy_move_action.py::CwActionDeployMoveOp`。

## 7. 语义验证(状态容器口径)

DeployMove 转移语义单一源 = 上报函数(`report_action_deploy_move_param`:三守卫/源槽摘除/载荷 `(to_row, to_slot)` 直落两行 + board 派生挂钩随写;原聚合写入入口与 sim 整帧副本单步应用器已随动作 op 重组与帧通道停用删除,考古归 git)。board 增量口径的状态容器派生路径 = 未知身份零贡献。派生漂移由下一备战帧观察覆盖收敛:`_absorb_board_derived` 命中(evidence 前缀 `proj_board_resync` 适用范围)落 `board_derived_adopt` 记录行采新,不触发失配告警;「上阵单位集合」不变量由 front_row/back_row 失配/纯重排吸收面独立把守。

## 8. 先例注记(动作发出阶段)

备战期;部署属逻辑态已建模面,执行后不强制保守回退,结束本次访问(逻辑态全覆盖后帧内逻辑态推进承接;overlay 检出仍环中止交外环 handler)。腾位链(卖前腾位)与部署义务(上阵数未满)共用本动作;发出准入判据(armed 判定,mandate_v1 前置动作发出点消费 kernel `readiness_launch_decision`)归动作发出点的判据面,不在本篇。

## 9. 依据

[../action-logic-state.md](../action-logic-state.md) §3/§3A/§1.5(席位单账直写语义);`kernel/cw_action_report/deploy_move.py` docstring(写域/守卫与上阵变换窗申报面);`kernel/cw_effect_inventory.py::merge_cascade_write` docstring(降级语义与行域载体);`GameState._resync_board_delta` 方法注(增量口径依据);`kernel/cw_exec_state.py` /槽位语义注;`strategies/impl/mandate_v1/deploy_plan.py` 模块头(计划单一源口径);`research/merge_mechanics.md` §3(同名唯一恒成立);`research/screen_flow_timing.md` #10/#24。
