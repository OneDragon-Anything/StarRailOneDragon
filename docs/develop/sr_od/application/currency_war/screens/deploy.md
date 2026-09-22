# 部署(deploy · 已退役画面 op;部署 = 备战决策环动作)

> **退役申报**:部署机画面 op `CwScreenDeploy`(原 `operations/cw_screen/cw_screen_deploy.py`,单 node 拖拽批处理)已退役删除——组合壳 RunDeploy 随统一词表退役后,部署的生产路径 = **备战决策环动作**:发射核(`strategies/impl/mandate_v1/mandate.py` R2 原子部署发射位)逐帧现算发 `CwActionDeployMoveParam` 原子序 → 决策动作 node 经 `prep_actions.py::PrepActionExecutor._deploy_move` 执行拖拽 → 动作自上报 `kernel/cw_action_report/deploy_move.py::report_action_deploy_move_param` 计算部署逻辑态 → 决策循环以逻辑态续算(无防御上限;不收敛 = 策略实现 bug)。本篇不再描述画面 op,仅作路径指针与历史交互模型的单一索引。
>
> 「前台无角色」场景 = 确认步(`cw_loop.py::_frontless_confirm_step`,点掉提示弹窗,零恢复动作)+ 备战环自然重部署(重观察发现 bench 有人 → mandate 发部署序);原 0j 恢复链(直调部署机重拖)已退役。

## 1. 现役路径速查

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判。本篇无独立画面 op,对照表记部署动作在备战决策环内的真实落点):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| 无画面 op——部署 = 备战决策环动作 `CwActionDeployMoveOp`(`CwActionDeployMoveParam`,注册表在册行) | 备战决策环执行器 `prep_actions.py::PrepActionExecutor._deploy_move`(薄委托经注册表类级解析组装;发射核 = `strategies/impl/mandate_v1/mandate.py` R2 原子部署发射位逐帧发序) | 自上报 `report_action_deploy_move_param`(`kernel/cw_action_report/deploy_move.py`;bench→deployed 槽位平移 + board 维护) | 否(非终结,`terminal=False`):部署序在备战决策环内消化,机械执行零判效,落地归下一帧观察对账、拖拽静默未生效由决策循环按新观察自然重派;本访问不因部署终结,交回由备战画面 op(`CwScreenPrep`)自身出口承载 |

部署拖点坐标全部来自备战建档(`货币战争-备战.备战栏-N` → `货币战争-备战.前排-N`/`货币战争-备战.后排-N` 中心,`DragCwChar.drag_char` 中心拖 + hold0)。

| 环节 | 单一源 |
|---|---|
| 部署选人/围栏/排序/底线门 | `kernel/cw_deploy_logic.py`(`select_deployments_reasoned`/`recipe_floor_holds`/`select_swap_plan`/`residual_fill_plan`) |
| 动作词表 | `kernel/cw_vocab.py::CwActionDeployMoveParam`(槽位表下标 0 基) |
| 拖拽执行 | `operations/cw_op/cw_deploy_move_action.py::CwActionDeployMoveOp`(原语 = `operations/dev/drag_cw_char.py::DragCwChar.drag_char`,中心拖 + hold0) |
| 部署逻辑态 | `kernel/cw_action_report/deploy_move.py::report_action_deploy_move_param`(bench→deployed 槽位平移 + board 维护) |
| 落地对账 | 备战环下一帧入口观察(观察赢;星级抖动门/两态仲裁驻 `kernel/cw_reconcile.py`) |
| 后排布局选档 | `obs/cw_back_layout.py::select_back_layout`(cap 差公式;未知态写类冻结) |
| deployed 计数双源仲裁 | `obs/cw_observation.py::arbitrate_deployed_count`(取低值 fail-closed) |
| 换血卖出(m1p 臂) | 发射面 mandate + `kernel/cw_deploy_logic.py::swap_sell_exclusion_reason`(判定单一源);卖出动作 = `CwActionSellDeployedParam`(`cw_sell_deployed_action.py`) |

## 2. 历史交互模型索引(供考古)

拖拽机制验证(中心拖 + hold0)、遮蔽哨发射前拦截、排位纠错、off-target 卖出腾位、deployed 双源仲裁留证、P24 残余补部署支配定理——判定单一源已全部收编 `kernel/cw_deploy_logic.py`(函数级对应关系见其模块头与各函数 docstring);执行编排与状态机的历史形态 = 本文件 git 历史(`operations/cw_screen/cw_screen_deploy.py`)。

## 3. 建档与坐标

部署在备战画面上以拖拽执行(非独立建档画面):槽位坐标全部来自备战建档(`assets/game_data/screen_info/currency_war_battle_prep.yml`:备战栏-1..9 / 前排-1..4 / 后排-N / 区域-出售区),现役消费方 = `CwActionDeployMoveOp`(拖点)与 `prep_actions.py::sell_point`(卖出落点)。
