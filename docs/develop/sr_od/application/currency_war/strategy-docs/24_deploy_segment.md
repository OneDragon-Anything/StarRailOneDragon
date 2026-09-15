# 24 部署执行段策略面(deploy segment)

> 定位 = **备战画面内部署执行段**(无独立 screen_info 建档画面):部署机以拖拽在货币战争-备战上执行(op 名「货币战争-部署角色」),未达上限确认弹窗(货币战争-未达上限警告)由流程层推进;**能力面** = [../screens/README.md](../screens/README.md) §5.4。本篇 = 该段的**策略面**:思路概述 + 动作清单 + 形式判据指针。
> 判据本体引用不重复:部署与站位判据 = [10_prep_decisions.md](10_prep_decisions.md) §1;换血卖出的骨架侧语义 = [02_mandate_layer.md](02_mandate_layer.md) §7(sell 行,M4 姊妹出口)。数值单一源在代码。

## 1. 策略思路/算法概述

- **选人围栏**:部署候选受围栏辖——引擎/配方体系件围栏 `DEPLOY_FENCE`(单一源 = `kernel/cw_launch_admission.py::DEPLOY_FENCE`,RECIPE ∪ ENGINE)与发射资格(`cw_launch_admission.py::offtarget_sell_allowed`);部署机按角色前后台属性拖入对应排空槽,后排布局选档单一入口 = `obs/cw_back_layout.py::select_back_layout`。
- **换血卖出**:off-target 上阵件挡 target 上场时先卖腾位,victim 资格单一判定 = `kernel/cw_deploy_logic.py::swap_sell_exclusion_reason`(义务集 ∪ 新鲜度排除 ∪ 资格族);部署面换血是 M4 之外的姊妹卖出出口(02 §7)。
- **补齐语义**:残余补部署 P24(空槽上任意围栏认可件零支出严格优先,`../proofs/p24-residual-fill-dominance.md`);发射门纪律 = 计划空是合法稳态,发射方与执行方同源谓词判空不发射(10 §1)。

## 2. 会执行的动作清单

| 动作 | 词表/op 载体 | 触发判据(指针) |
|---|---|---|
| 选人上阵 | `RunDeploy`(组合路径 = 部署机 `operations/cw_screen/cw_screen_deploy.py::CwScreenDeploy.deploy`) | M1/M5 + 围栏 + 10 §1 |
| 换排 | 部署机内拖拽(含错排归位 `_fix_misplaced_rows`) | 同上(放对激活角色赋能) |
| 换血卖出 | 部署机内 `SellDeployed`(`_sell_offtarget_deployed`) | victim 资格 = `swap_sell_exclusion_reason`(义务集∪新鲜度排除∪资格族) |

## 3. 能力 vs 策略

部署执行段动作集与能力面同集(能力矩阵篇 §3.4);策略收缩不涉及本段(收缩只发生在商店期,见 [23_shop_screen.md](23_shop_screen.md) §3)。
