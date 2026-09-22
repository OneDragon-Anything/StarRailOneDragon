# 卖上阵(SellDeployed)逐动作逻辑态

> 归属:[logic-updates/](README.md) 逐动作分篇;总则见 [../action-logic-state.md](../action-logic-state.md)。符号锚路径根 = `src/sr_od/application/currency_war/`。数值只写常量名。

## 1. 动作是什么

把已上阵(前排/后排)的某个单位拖到出售区卖出,回收退款并腾出上阵位。v2 动作族成员:词表 + 容器逻辑态直写 + sim 消费在役,商店期默认发射面不含本动作(生产策略面归备战域)。执行载体 = `operations/cw_op/cw_sell_deployed_action.py::CwActionSellDeployedOp`(注册表行);换血卖出(m1p 臂)= mandate 发射位逐件产 `CwActionSellDeployedParam` 原子,同一执行载体,卖谁判据单一源 = `kernel/cw_deploy_logic.py::swap_sell_exclusion_reason`。词表 = `kernel/cw_vocab.py::CwActionSellDeployedParam`(`deployed_idx` = deployed 槽位表下标 0-9,0-3 前/4-9 后)。

## 2. 逻辑态域集

**容器写口(双域统一单点)** = 上报函数 `kernel/cw_action_report/sell_deployed.py::report_action_sell_deployed_param`(原商店腿/备战腿的历史两份随动作 op 重组合一):

| 域 | 写 / 跳写 | 说明 |
|---|---|---|
| front_row / back_row | 写 | deployed 槽表中间形态置空(不移位)→ 整表 `write_logic`(平移契约,`deployed_slots_to_rows` 换算) |
| board | 派生随写 | **派生量**:front_row/back_row 行写端挂钩 `GameState._resync_board_delta` 自动增量重算(观察基座 + 行变更差),本腿禁手写 board(见 §3 第 4 条) |
| gold | 写 | `gold += 退款`;None 跳写 |
| equips | 写 | 被卖单位装备全量追加进 owned 库存(`sold.equips` 非空才写;原执行账 owned 恢复腿随函数内聚单点化) |
| bench / shop / xp | 跳写 | 不触 |

**效果账面(申报:执行缝无金腿/无独立 owned 腿)**:回金与 owned 恢复的唯一写点 = 上报函数(原 `apply_op_effect` 金腿已随「统一观察对账迭代 2026-09-16 归因批」退役——执行缝 + 投影双腿各记一次 +refund,实读倒挂 −2 实证;原执行账 owned 恢复腿(执行账单一写者、无投影对应物)随 op 自上报收编进本函数单点)。

## 3. 确定面转移规则(逐条)

1. deployed 该槽位清空(置 None **不移位**;`deployed_idx` 跨动作组恒稳);
2. `gold += 退款`——退款公式与手续费口径与卖备战**同一条**(单一源 = `kernel/cw_economy.py::sell_refund` + `bench_char_cost`;`_SELL_MULT` 倍数 + star≥2 且 cost≥2 手续费 −1,cost=1 豁免);
3. 装备全量回装备区(同卖备战第 3 条:口述·权威 + C6 守恒建模 + 缺口 G5 帧级证据未采);
4. board **派生随写**:front_row/back_row 整表写触发行写端挂钩 `GameState._resync_board_delta` 自动增量重算(观察基座含面板真值的装备羁绊贡献,本次行写只施加单位多重集差——新增加其羁绊标签、移除减、减至 0 摘键;禁独立手写 board);上阵计数随 deployed 摘槽派生递减(无独立字段写);
5. 执行侧 tracked 同步:`PrepActionExecutor._track_remove_deployed`(物理 (row, slot) → `deployed_idx_of` 换算,置 None,且校验 `position_pref` 与排一致防错位)。

## 4. 随机面

无。卖价修饰(`sell_price_mult`,大裁员/降本增效)口径待实证 = 缺口 G4,闭合前不写修饰腿。

## 5. 拒绝语义

- 槽位越界 / 槽空:`applied=False, reason='deployed_idx_out_of_range:<idx>'`(上报函数守卫零写);
- **期望失配 stale_proposal**:expect 非空且与槽内 `char_id` 不符 = `applied=False`(expect 经 降级为遥测观测字段,名不符仍是跨代际提案的拒绝信号);
- 执行器零判效:拖拽发出即职责完成,落地归观察 reconcile。

## 6. kernel 符号锚

`kernel/cw_action_report/sell_deployed.py::report_action_sell_deployed_param`(双域统一单点)/ `GameState._resync_board_delta`(board 派生挂钩单一源)/ `_row_unit_tags`;`kernel/cw_economy.py::sell_refund` / `bench_char_cost`;`kernel/cw_exec_state.py::deployed_row_slot` / `deployed_idx_of`;`prep_actions.py::PrepActionExecutor._sell_deployed` / `_track_remove_deployed`;`operations/cw_op/cw_sell_deployed_action.py::CwActionSellDeployedOp`(换血卖出 = m1p 发射臂逐件产原子,资格单一源 = `kernel/cw_deploy_logic.py::swap_sell_exclusion_reason`)。

## 7. 语义验证(M1 直锁)

卖上阵动作转移语义单一源 = 上报函数(`report_action_sell_deployed_param`:空槽/越界拒 + expect 失配拒零推进 + 摘槽 + `sell_refund` 回金 + 装备回收 + front/back rows 整表平移(board 派生挂钩随写),双域统一单点)。原 `kernel/cw_vocab.py::simulate` SellDeployed 分支(整帧副本第二载体)已随零生产消费退役,考古归 git。商店域投影语义由直锁 M1(`test_cw_shop_projection_logic`)钉住,v2 族金样直锁 = `test_cw_transfer_golden`(初态本地构造)。C6 装备守恒核对的活机制 = 观察边界 reconcile(原 sim 侧 `EquipsLedger` 快照比对对账入口随 simulate 退役)。

## 8. 判例注记(发射期)

生产策略面归**备战期**(部署期换血/腾位卖,策略判据 = strategy-docs/24 号篇):商店域 v2 动作族能力面保留(上报函数 `report_action_sell_deployed_param` 在役),生产策略面归备战期(注册表单行在册,备战域 op);商店期默认发射面 = 买/刷/关(判例 = [screens/README](../../screens/README.md) §5)。

## 9. 依据

`research/economy.md` §3;`research/equipment_mechanics.md` §1 与「装备转移机制」节(卖角色 = 装备回区主力通道);`kernel/cw_action_report/sell_deployed.py::report_action_sell_deployed_param` docstring(v2 族语义正本);[fields.md](../fields.md) §3.2.3/§3.2.4(前后台角色)/§4.2 SellBench 行(「卖场上角色 → 前台/后台 −该牌」)。
