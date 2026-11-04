# 画面 op 层(screens/ · 一画面一文档)

> 本目录 = 画面 op 层设计权威版本:**每个画面 op 一篇**,写「这个画面做什么观察、能发哪些动作 op、哪些动作结束本次访问并返回主循环」。代码根 = `src/sr_od/application/currency_war/operations/cw_screen/`(一画面一文件)+ `obs/`(观察解析工具箱)+ `kernel/cw_screen_report/`(每画面观察上报:obs 类 + report 函数一文件);符号名引用 = `文件::符号名`(行号随代码漂移,不作定位依据)。
> 分工分界:分发判定(两阶段身份分发)的单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2(本目录各篇只写画面特有的排他/穿透形态与身份 id_mark 说明);画面 op 统一规范(两 node 形态/round_wait 循环/终结 op/期望态生命周期/对账边界/report 上报接口)= [op-layer.md](op-layer.md);逐屏形态分类总表(35 屏)= [op-layer.md](op-layer.md) §3;动作执行契约 = [../flow/action_exec.md](../flow/action_exec.md)。
> 术语:见下方「术语表」节;路径缩写约定:本文反引号短路径 `research/X.md`/`data/X.md` 等 = `docs/game/currency_war/` 下对应文件(非 src 树);game 侧文档同理指向本仓 docs/。

## 0. 术语表

- **内置动作**(原"留守臂"):画面 op 内部代码直接执行的固定动作,不经动作注册表派发。
- **零判效**:执行代码只点击、不判断动作是否生效;生效与否以实际观察为准(真值归下一帧观察)。
- **落地复查**(原"重入裁决"):动作发出后,下一轮循环先检查上一动作是否已生效——对应画面标志消失即视为已生效。
- **观察即真值**(原"观察赢"):推算状态与下一帧实际观察不一致时,以实际观察为准。
- **逻辑态**:动作执行后不经观察、按游戏规则推算并直写状态容器(GameState)的预期状态(例:买牌后金币 −40、备战席 +1;下一帧观察不符以实际观察为准)。
- **状态容器**:GameState,游戏状态对象(下同)。
- **对账**:推算状态与下一帧实读逐项比对,对不上 = 有 bug。
- **帧 / 帧代次**:帧 = 一次截屏并做一次决策的时点;帧代次 = 观察帧的版本标记(如"完整帧")。
- **返回主循环**:结束本次画面访问,控制权返回外循环(重新识别画面再分发)。
- **中断恢复的对局**(原"接管局"):程序在对局中异常退出后重启、从局中画面恢复继续跑的对局。
- **动作类型清单**:全库统一登记的动作类型清单(`kernel/cw_vocab.py`,白名单 = `CW_ACTION_TYPES`);"清单外" = 返回的动作类型不在登记范围内。
- **数字来源标注四形态**:涉策略语义的数字带来源标注——【注】游戏定义值(代码注册表直读)/【推】已证推导/【拟】观测估计(须带置信区间)/【拍】用户立场登记值(合法性来自裁定本身)。
- **"零X / X即Y"句式**:正文中的"零字段写操作" = 不写游戏状态;"发出即写" = 发出动作时立即写入;"发出即终结"(原"派发即终结")= 点击发出后即结束本次访问;"零盲发" = 不发出无依据的动作;"零点击终结" = 不点击直接结束本次访问。

## 1. 能力面与策略面(区分原则)

- **能力面** = 画面机制上可做的动作全集:游戏在该画面提供了什么可执行操作,以及我们把每个操作落地为哪个动作 op。七动作族(§4)与状态容器上报函数族(`kernel/cw_action_report/` 的 `report_action_<snake>_param` 等逻辑态直写通道)**全保留**,不随策略收缩删除。
- **策略面** = 默认策略(mandate_v1)在当前策略形态下实际会做的子集。策略面收缩是策略域变更:只改决策入口的提案集,不删执行器/动作类型清单/逻辑态直写。
- **先例**:卖备战(SellBench)与买经验(LevelUp)是商店开画面的**可用**动作(§5.4),但默认策略**不在商店期做**——两者收缩至备战期决策(策略面清单见 strategy-docs 22/23 号篇)。能力矩阵按能力面记;策略归属见 strategy-docs 画面策略篇。
- 记载纪律:每个画面列「游戏可用动作全集」并逐条给 op 映射;某动作当前不被策略使用时在策略归属列注明「策略面收缩至 X 期」,不删行。

## 2. 画面文档模板

每篇画面文档按以下九节组织(大画面各节成章,弹窗/推进族各节可短至一两行):

| # | 节 | 内容 |
|---|---|---|
| 1 | 分发判定 | 外循环怎么认出本画面(id_mark = `画面名.area名`)、与相邻画面的排他/穿透形态;指向 outer_loop §2.2 |
| 2 | 画面形态声明 | 三选一:决策循环形态(问策略器,注明决策入口)/ 空决策形态(纯推进)/ 单选族例外(有选择面零逻辑态账) |
| 3 | 观察面 | 本屏读什么:消费哪些 obs 解析器、什么进 GameState(字段组/写端)、heavy/light;观察上报即对账边界 |
| 4 | 动作面 | **开头放「动作 op 与交回对照表」**(本篇唯一动作清单,逐行 = 动作 op(动作类型清单参数类)/发出方式(二选一:①经动作注册表派发的动作 op;②画面 op 内部代码直接执行的固定动作,下称"内置动作")/上报函数/是否触发返回外循环(终结语义一句话);无动作 op 的画面表内一行「无——单步推进由内置动作完成」)。表后逐动作给执行要点(点击 id_mark、交互时序、动画等待、已知交互陷阱) |
| 5 | 终结与交回 | 逐出口列「条件/级别/交回落点」表,行与 §4 对照表的「触发返回外循环」列一一对应;结束后外循环重判的预期落点 |
| 6 | 状态上报面 | 动作 → 哪个上报函数(`kernel/cw_action_report/<snake>.py::report_action_<snake>_param`;dict 确认族到账 = `kernel/cw_exec_state.py::apply_confirm_effect`),指向 [../game_state/logic-updates/](../game_state/logic-updates/README.md) 对应篇 |
| 7 | 子态与 overlay | 本屏的子态(如备战-开商店、暗色锁定)与本屏会被哪些 overlay 覆盖、命中时结束本次访问还是自处理 |
| 8 | 守卫与防线 | 本屏的停机钩子/失配告警/预算(细则指针 = [../flow/guards.md](../flow/guards.md)) |
| 9 | 遥测与测试面 | journal op 名、branch 分键、缺陷键、测试文件指针、game 侧知识指针 |

纪律:as-built 无状态(事故史/裁定日期不进正文);坐标一律 `画面名.area名`;分发判定不复制外循环表。

## 3. 形态分型(对照 35 屏)

- 画面 op 统一形态 = **两 node 直继承 SrOperation**:观察 node = 门 + 显式读屏 + `CwScreenXxxObs` + `report_screen_<snake>_obs` 落状态容器;决策动作 node = 落地复查 + 决策 + 动作,`round_wait` 循环推进、无防御上限。判据合同 = [op-layer.md](op-layer.md) §1。
- 分型判据:入决策规范 ⇔ **选择面 ∧ 逻辑态账**(商店/备战);空决策形态 ⇔ **无选择面 ∧ 无逻辑态账**——纯推进为流程义务:观察 + 推进处理 + 返回主循环(新 op 单尝试,重试预算归外循环);建档与否非分型维度——本型成员含无画面档的兜底推进(前进按钮)与商店框 2 类(编排壳 op,非画面档成员);单选族例外:有选择面但零逻辑态账(选卡/确认即终结,visit 内无后续决策消费逻辑态)。
- 五型 = 全形态 / 节点循环(overlay 单动作循环)/ 推进型空决策(无 report)/ 驻留状态机豁免(battle_wait,用户裁定)/ 重型屏(漏斗 + 无帽决策循环);逐屏分类与 report 有无总表 = [op-layer.md](op-layer.md) §3。

## 4. 动作类型清单与执行载体

**动作类型清单单一源** = `kernel/cw_vocab.py`(统一登记全部动作类型;白名单 = `CW_ACTION_TYPES`,新增动作必须同步登记,漏登记 = 执行面拒「未知动作类型」,动作从未真正执行)。**注册表单一源** = `operations/cw_op/cw_action_registry.py`(动作类型清单的参数类 → 动作 op 类一张表,`action_op_for`/`action_op_class_for` 全动作唯一注册点;行序 isinstance 首中即返,is-a 链父类行兜底规则见模块头)。

| 动作族 | 动作类型(`kernel/cw_vocab.py`) | 执行载体 | 终结性 |
|---|---|---|---|
| BuyCard(买牌) | `CwActionBuyCardParam` | `operations/cw_op/cw_buy_card_action.py::CwActionBuyCardOp` | 非终结 |
| RefreshShop(刷新) | `CwActionRefreshShopParam` | `cw_refresh_shop_action.py::CwActionRefreshShopOp` | **访问终结**(§6) |
| CloseShop(关商店) | `CwActionCloseShopParam` | `cw_close_shop_action.py::CwActionCloseShopOp`(执行位 = 真机械点击「收起」+ 幂等已关出口 + 清场上报) | **访问终结**(§6) |
| SellBench(卖备战) | `CwActionSellBenchParam` | `cw_prep_sell_bench_action.py::CwActionSellBenchOp`(动作类型清单摊平后商店/备战共用单一注册行;原商店域文件 `cw_sell_bench_action.py` 已停用删除) | 非终结 |
| LevelUp(买经验) | `CwActionLevelUpParam`(单类型;原 LevelUpShop 同字段双类型已随 2026-10-17 迭代 T-4 退役删除) | 注册行 = `cw_prep_level_up_action.py::CwActionLevelUpOp`(备战域);原商店域 `cw_level_up_action.py` 已停用删除 | 非终结 |
| SellDeployed(卖上阵) | `CwActionSellDeployedParam` | `cw_sell_deployed_action.py::CwActionSellDeployedOp`(换人判定单一源 = `kernel/cw_deploy_logic.py::swap_sell_exclusion_reason`,转型域经 `swap_bond_gate_domain` 判别子分派双门资格面) | 非终结 |
| SwapDeploy(上阵↔备战对调) | `CwActionSwapDeployParam` | 未接入调用(动作类型清单+上报函数/sim 消费在用;动作类型清单完备性保留) | 非终结 |
| DeployMove(部署) | `CwActionDeployMoveParam` | `cw_deploy_move_action.py::CwActionDeployMoveOp`(bench→上阵单步拖拽,动作发出点逐帧现算) | 非终结 |
| 领取类(开箱) | `CwActionOpenBoxParam` | `cw_open_box_action.py::CwActionOpenBoxOp` | **访问终结**(§6) |
| 领取类 | `CwActionCollectOreParam`/`CwActionOpenTomeParam` | 同名 `_action.py` op(`cw_open_tome_action.py` 等) | 非终结 |
| 领取类(开书册卡) | `CwActionOpenBookcardParam` | 同名 `_action.py` op(`cw_open_bookcard_action.py`) | **访问终结**(§6) |
| 穿戴/工具 | `CwActionWearEquipParam`/`CwActionFurnaceUseParam`/`CwActionPrivilegeCardUseParam`/`CwActionWrenchUseParam`/`CwActionPrecisionWrenchUseParam`/`CwActionStaffProjectorUseParam`/`CwActionPerfectProjectorUseParam`/`CwActionLuckyTokenUseParam` | `cw_wear_equip_action.py::CwActionWearEquipOp`/`cw_tool_use_action.py::CwActionToolUseOp` | 非终结 |
| 转场 | `CwActionOpenShopParam`/`CwActionStartBattleParam` | `cw_open_shop_action.py::CwActionOpenShopOp`(terminal 承载行,执行抛,正常路径不可达)/`cw_start_battle_action.py::CwActionStartBattleOp`(返回值已登记例外) | 备战环终结/备战访问终结 |

组合壳(RunDeploy/RunEquip/RunTools)已随动作类型清单统一而停用:部署 = 动作发出点逐帧现算 DeployMove 原子序,穿戴 = WearEquip 原子,工具 = 工具原子类经 `CwActionToolUseOp`;部署机画面 op `CwScreenDeploy` 已停用删除——部署无画面 op 载体,路径速查 = [deploy.md](deploy.md)。

**动作坐标系(二分)**:席位域动作(SellBench/SellDeployed/DeployMove)携**状态容器槽位表下标 0 基**(bench 0-8 / deployed 0-9,观察面读口 `bench_view_slots_of`/`deployed_rows_of` 同基直取零换算;DeployMove 落位另携载荷 `(to_row, to_slot)` 直指,执行边零现读);**画面物理槽位 1 基**仅存于坐标参数化机械动作(WearEquip/工具七类/OpenBox/OpenTome/OpenBookcard)的 `row`/`slot` 字段。执行坐标边换算 = `PrepActionExecutor`:备战栏按建档 area 顺序直接取;上阵位在执行器内做"行内槽号→下标"换算,两个视图互转的工具函数 = `cw_exec_state.deployed_indexed_of_view`/`deployed_view_of_indexed`。

## 5. 画面×动作矩阵(能力面)

### 5.1 简报与过场(货币战争-简报 / 货币战争-BOSS简报 / 货币战争-位面过渡 / 货币战争-位面详情 / 位面情报采集 / 等待 1-1 / 前进按钮兜底)

| 游戏可用动作 | 机制依据 | 我们的 op | 访问终结语义 |
|---|---|---|---|
| 简报点「下一步」 | `research/screen_flow_timing.md` 时序 #1(首领出现 +1s 可点) | `operations/cw_screen/cw_screen_briefing.py::CwScreenBriefing`(阶段一身份行「货币战争-简报」);内嵌词缀效果采集段 `_collect_affix_effects`(逐词缀点采 OCR 效果,对注册表 `src/sr_od/application/currency_war/data/affix_effects_data.py` 比对(注册表住 src 树代码;本文头注 `data/X.md` 短路径约定仅适用于 docs/game 侧,不适用于 src 文件),新名/不一致才截图收集;采集写端 best-effort,OCR 采不到即跳过) | 点推进即终结(空决策形态;点采 tooltip 不终结) |
| BOSS 简报点空白 | 同上 #26(「点击空白处继续」出现即可点) | `operations/cw_screen/cw_screen_boss_briefing.py::CwScreenBossBriefing`(阶段一身份行「货币战争-BOSS简报」;位面过渡身份帧含 boss 判别片段时排他接管);点掉后返回主循环重新判定——回备战并自动弹店(`screen_flow_timing.md` #14/#27;接管局例外 = 恢复局商店锁死态只能出战,见 [boss_briefing.md](boss_briefing.md) 开放设计注①) | 点空白即终结 |
| 位面过渡点空白 | 同上 #2 | `operations/cw_screen/cw_screen_plane_transition.py::CwScreenPlaneTransition`(阶段一身份行「货币战争-位面过渡」) | 点空白即终结 |
| 位面详情点 X 关闭 | game 侧画面档 = docs/game/screens/货币战争-位面详情.md(检视浮层;用途见 research/plane_schedule_observed.md「位面详情画面」条) | `operations/cw_screen/cw_screen_plane_detail.py::CwScreenPlaneDetail`(阶段一身份行「货币战争-位面详情」,分发判定单一源 = flow/outer_loop.md §2.2;单篇动作清单 = [plane_detail.md](plane_detail.md) §4) | 点 X 即终结(空决策形态) |
| 采集位面情报(切位面卡/点 boss 节点为采集内部步) | game 侧画面档 = docs/game/screens/货币战争-位面详情.md(宿主屏与上一行同档;用途见 research/plane_schedule_observed.md「位面详情画面」条——中断恢复的对局补采的运行时源) | `operations/cw_screen/cw_screen_plane_intel.py::CwScreenPlaneIntel`(多屏管线形态 6 node,op-layer §3;非外循环分支直管——调用路 = 备战委派插入位置 `cw_screen_prep.py` 观察 node ∧ 手动调起编排 `operations/cw_entry/cw_entry_plane_intel.py::CwEntryPlaneIntel`,单一源 = [plane_intel.md](plane_intel.md)) | 纯观察采集(无游戏推进动作;切卡/点节点带详情条联动转移证据);管线走完上报后由编排点 X 关屏,关屏成功才返回主循环 |
| 无动作(开局补给动画无结束标志,就绪等待) | research/screen_flow_timing.md #5/#29(1-1 是唯一不自动开商店、动画最长的开局节点) | `operations/cw_screen/cw_screen_wait_one_one.py::CwScreenWaitOneOne`(外循环投资环境分支链序第二段,非独立分发分支;轮询 id_mark「货币战争-备战.标识-备战阶段」只判备战面板就绪,超时上界 = `cw_flow_const.py::ONE_ONE_MAX_WAIT_S` 兜底) | 无动作(就绪等待,success 即终结;超时存图保留证据 失败结束本次访问,返回主循环) |
| 点「下一步」(无画面档画面的兜底推进) | 无画面档(能落到本分支 = 该「下一步」不属于任何已建档画面档;入口信号 = 自有 OCR「下一步」同源判定,外循环「下一步」兜底分支,flow/outer_loop.md §2.2) | `operations/cw_screen/cw_screen_next_button.py::CwScreenNextButton`(空决策形态无 report;单篇动作清单 = [next_button.md](next_button.md) §4) | 点「下一步」即终结(复查时 OCR 不命中 = 已离开本画面 success 结束本次访问;推进未落地 失败结束本次访问,返回主循环重新判定) |

### 5.2 投资环境(货币战争-投资环境)

| 游戏可用动作 | 机制依据 | 我们的 op | 访问终结语义 |
|---|---|---|---|
| 三选一选环境卡 | `data/gameplay.md`(投资环境 = 整局增益);开场必经 | `operations/cw_screen/cw_screen_invest_env.py::CwScreenInvestEnv`(阶段一身份行「货币战争-投资环境」);决策 = pick 族 `decide_invest_env`(规格 = strategy-docs/13_pick_family.md) | 确认离开(overlay 消失) |
| 刷新圆钮重掷三卡 | `research/screen_flow_timing.md` #4(刷新动画 ~2s) | 同 op 内整组重掷(`cw_screen_invest_env.py::_decide_and_act`:点→等动画→**本访问即结束本次访问**,round_success 终结,无 pending;外循环重进 = 入口重建重观察重分类);是否建议刷新 = 投资环境刷新三态判据(策略层 `invest_env`,权威版本 = strategy-docs/28_invest_env_screen.md §4;math_proofs P81) | **刷新即本访问终结**(刷新 = 唯一引入新事实的动作);确认离开才画面终结 |

### 5.3 备战画面(货币战争-备战)

主链决策画面。建档 = `assets/game_data/screen_info/currency_war_battle_prep.yml`(备战栏-1..9 / 前排-1..4 / 后排-N / 按钮-商店 / 按钮-出战 / 区域-出售区 / 备战标识-购买经验 等 area)。文档 = [prep.md](prep.md)。

| 游戏可用动作 | 机制依据 | 我们的 op | 策略归属 | 访问终结语义 |
|---|---|---|---|---|
| 上阵(拖备战栏→前排/后排空槽) | 等级=可上阵数(`data/gameplay.md`);站位前台/后台激活角色赋能 | `DeployMove`(部署 = 动作发出点逐帧现算原子序,备战决策环动作;路径速查 = [deploy.md](deploy.md)) | 备战期(22/24 号篇) | 非终结 |
| 换排(上阵单位前排↔后排拖拽) | 同上 | `DeployMove`(to_row 重拖,策略发;错排事实归备战环入口观察对账) | 备战期 | 同上 |
| 卖备战(拖备战栏→区域-出售区) | 卖出退金(`research/economy.md` §3;单一源 `kernel/cw_economy.py::sell_refund`) | `CwActionSellBenchOp`(注册行)+ `prep_actions.py::drag_bench_to_sell` | 备战期:腾位(M4)/凑利息/筹资/换线塌缩(22 号篇) | 非终结 |
| 卖上阵(拖上阵位→出售区) | 同上 | `CwActionSellDeployedOp`(换人判定单一源 = `swap_sell_exclusion_reason`,转型域 = `swap_bond_gate_domain` 判别子分派的双门资格面) | 备战期/部署期换人(24 号篇) | 非终结 |
| 买经验(点「备战标识-购买经验」) | 4 金/击=+4 经验,升级=过门槛表(`research/xp-rules.md` §2;表值 = `kernel/cw_economy.py::XP_TO_NEXT_LEVEL`) | `CwActionLevelUpOp` 备战连点 | 备战期(22 号篇;商店期收缩后的唯一买经验期) | 非终结 |
| 开商店(点「按钮-商店」) | 商店每节点自动刷新 1 次(`data/gameplay.md`) | `OpenShop`;编排 = `cw_screen_prep.py` 商店访问段(文档 = [shop.md](shop.md)) | 备战期(进商店访问的唯一入口动作) | **备战环终结**:执行 = 商店访问编排(open_shop → 商店画面 op 两 node 访问 → 收店),完成后返回主循环重识别 |
| 出战(点「按钮-出战」) | 未在行动值内取胜扣血(`data/gameplay.md`) | `CwActionStartBattleOp`;发出意图 = mandate_v1 决策链最先检查的发出点(判据 = `kernel/cw_launch_admission.py::readiness_launch_decision`);执行 = 统一执行器 `operations/cw_loop.py::launch_battle_unified` | 备战期出口(唯一完成态) | **备战访问终结**:返回主循环战斗分支 |
| 点晶矿(区域-奖励) | 晶矿飞行动画 ≤2s(`research/screen_flow_timing.md` #16) | `CollectOre`(批式:一次全点→固定等待 2s→自上报结束本次访问;席满未点开的晶矿由下一帧观察回补;席满让路门 = `strategies/impl/mandate_v1/entry.py` 席满探针段) | 备战期 | 非终结 |
| 开补给箱(点备战栏箱位) | 开箱即腾位(武装箱 overlay) | `OpenBox`(点「开启」即结束本次访问;选卡弹窗由画面 op `CwScreenBoxPick` 闭环、武装箱获得说明弹窗由 `CwScreenArmoryBox` 点 × 关闭,均非动作) | 备战期(实体面优先,`entry.py::emit` ①) | **访问终结** |
| 开秘密典籍 | 典籍占备战席 1 槽 | `OpenTome`(点槽一次开启;星徽四选一弹窗由外循环阶段一身份分发 `CwScreenBookcard` 接管选卡,非本动作) | 备战期(实体面优先,`entry.py::emit` ①) | 非终结 |
| 查看详情(角色/装备详情浮层) | 游戏辅助功能(`data/gameplay.md`) | 推进型弹窗 `CwScreenRoleDetailOverlay` 等(阶段一身份分发,空决策形态) | 无策略归属(推进为流程义务) | 关闭/点空白即终结 |
| 关闭「中断挑战」弹窗 | ESC 误按/误点左上角弹出的真模态(点遮罩无效,关闭只有 X 一条路;底层 = 备战) | `cw_screen_interrupt_dialog.py::CwScreenInterruptDialog`(阶段一身份分发,空决策形态;语义红线 = 绝不点「放弃并结算」/「暂时离开」,唯一动作 = X;单篇 = [interrupt_dialog.md](interrupt_dialog.md)) | 无策略归属(推进为流程义务) | 点 X 即终结 |
| 锁商店(跨节点保牌) | `research/economy.md` §2.1(整店级锁;官方机制) | **生产链路未建模**(建档已有「按钮-商店锁定」坐标备作将来) | 无 | — |

### 5.4 部署执行(备战画面内,无独立建档画面、无独立画面 op)与商店开画面(货币战争-备战-开商店)

部署不是独立 screen_info 画面:部署 = 备战决策环动作(`CwActionDeployMoveParam` 原子序经 `CwActionDeployMoveOp` 在备战画面上拖拽;部署机画面 op 已停用,路径速查 = [deploy.md](deploy.md));`currency_war_deploy_not_full.yml`(未达上限警告,阶段一身份分发)为部署被拒确认弹窗。商店开画面建档 = `currency_war_battle_prep_shop_open.yml`;文档 = [shop.md](shop.md)。

商店开画面能力面:买牌(`CwActionBuyCardOp`)/刷新(`CwActionRefreshShopOp`,访问终结)/买经验(能力面在役;**执行链已接入调用**——商店域执行环境具备执行器端口,购买经验按钮整批连点通道在产;策略面消费 = 会话内前置升级检查,23 号篇)/卖备战(**执行链已接入调用**——`ShopExecEnv.executor` 端口 + 适配备战执行环境实现,画面档「备战栏-1..9」与「区域-出售区」area 为拖拽两端坐标地基;策略面消费 = 置换账/筹资/C1 恒买腾位,23 号篇;场上角色店内仍禁卖——能力面边界)/关商店(`CwActionCloseShopOp` 执行位真点击,访问终结)/出战(画面「出战」按钮在役——**op 列值 = 前置动作发出点**〔出战就绪帧经 `cw_launch_admission` 前置位发射,非店内 op;受限商店访问帧的溢出段消费入口〕)/牌详情弹窗(阶段一身份分发,点 X 绝不点购买)/刷新概率表(阶段一身份分发;概率条直读进 `refresh_probs` 为观察非动作)/锁商店(未建模)。执行链注记:商店域执行环境(`ShopExecEnv`)具备执行器端口,域内分发适配备战执行环境(拖拽两端/连点按钮读商店画面档);「卖备战/买经验收缩至备战期」的旧先例已废止(§7)。

### 5.5 事件单选族(overlay)

投资策略/补给/遭遇(货币战争-遭遇节点)/盛会之星/选择伙伴/命运卜者(`cw_screen_fortune.py`)/银狼升星(`cw_screen_yinlang.py`)/祈愿试炼/星徽秘典四选一/专家邀请函/武装箱选择(货币战争-备战-武装箱选择,`cw_screen_box_pick.py`)。决策 = pick 族八接口 + `decide_box_card`,规格 = strategy-docs 13 号篇(原选择装备随该屏误判停用删除,2026-09-22)。

**选卡动作执行载体(选卡动作统一迭代起统一;事件屏统一迭代更新)**:12 屏的选卡动作 = 12 个 `CwActionPickXxxOp` 注册行(投资两屏拆类 = `CwActionPickInvestStrategyParam`/`CwActionPickInvestEnvParam` 两行同指一 op),画面 op 决策半只决策与组装机械参数,选中→确认(或点卡即选)机械链 + 自上报在动作 op 内。**上报形态 = 点完立即按成功写入**:这批画面的选卡动作都是「点完立刻把完整结果写进游戏状态,不等下一帧确认」(旧的先记发出、再等落地证据的两步机制已全部删除;用户裁定 = [../flow/action_ops.md](../flow/action_ops.md) §1「用户裁定(点完即写)」)。写入内容:投资两屏的选择事实+效果经获得链 `gain_invest_strategy`/`gain_invest_env` 记;补给在动作发出时一次性写入:获得道具、上场的单位及其效果、获得后果链(`kernel/cw_action_report/pick_supply.py`);遭遇在动作发出时立即写 `chosen_encounter`(`kernel/cw_action_report/pick_encounter.py`);策划按效果类型分支写入:附带条件分支(代码 branch_type='rider')先行,装备写入与升费(费用档提升)写入含 `lv999_cost_tier` 档行(`kernel/cw_action_report/pick_planner.py`)——画面 op 不写游戏状态、点击发出后即结束本次访问,确认未生效由外循环重识别重派。契约权威版本 = [../flow/action_exec.md](../flow/action_exec.md) §2。

| 游戏可用动作 | 机制依据 | 我们的 op | 访问终结语义 |
|---|---|---|---|
| 选卡(N 选 1) | 各事件机制(`data/gameplay.md`/`research/economy.md` §9) | 各画面 op(阶段一身份分发,分支号制已停用) | 确认离开(overlay 消失)= 画面终结 |
| 逐卡/整屏刷新重掷 | 刷新后 ~2s 稳定(时序 #13/#19/#23) | 投资策略逐槽(观察 obs 携带逐卡余量 + `safe_click` 内置动作)/ 遭遇(`cw_screen_encounter.py` 刷新终结分支,状态容器 `encounter_refresh_left` 剩余闸)/ 补给(`cw_screen_supply_node.py`「剩余次数」文本锚定,状态容器 `supply_refresh_left` 剩余闸);建议刷新 = 各屏策略层刷新判据(策略屏 = `invest_strategy` 帧级门+槽级动作集,权威版本 = strategy-docs/29_invest_strategy_screen.md §4;环境屏 = `invest_env` 三态,28_invest_env_screen.md §4;P81) | **刷新 = 终结为全域规范**(权威版本 = [op-layer.md](op-layer.md) §1.4):投资环境整组重掷、投资策略逐卡、遭遇、补给(点钮 + 2s 后 round_success 返回主循环重进 = 入口重建)全链终结语义,闸全域 = 剩余语义观察真值(`*_refresh_left`,禁已用推算);确认离开才画面终结 |
| 开书册卡(点备战席槽位「开启」→ 弹专家邀请函) | 书册卡 = 备战席占槽道具 | `CwActionOpenBookcardOp`(备战决策环终结动作,`terminal=True`;动作发出点 = 策略器 entry ① prep 实体面卡片分支 `strategies/impl/mandate_v1/entry.py`)→ 弹窗由阶段一身份分发 `operations/cw_screen/cw_screen_expert_invite.py::CwScreenExpertInvite` 选卡 | 开卡即备战访问终结;弹窗选卡确认离开 = 弹窗访问终结 |
| 返回备战/返回选择(暗色锁定子态) | 暗色蒙层态判别 id_mark = 右上操作按钮(screen_flow_timing #18) | `operations/cw_screen/cw_screen_prep_locked_return.py::CwScreenPrepLockedReturn`(阶段一身份分发;策略锁定/遭遇锁定两档参数化) | 点返回即终结 |
| 关「属性详情」面板 | 点卡身上部误触发 | 未建模独立处理(点卡 = 机械单发);面板残留由下一帧重新识别自愈(重分发重走链/详情 overlay 族分支) | 面板关闭即随重新访问收敛 |
| 盛会之星「请选择强化角色」伴随文案 | 该 area 与「按钮-确认选择」rect 重叠,系伴随文案非步骤 | 未建模独立处理(确认 = 纯机械单发);确认未落地残留归巨星节点循环复查自愈 | 确认推进即画面终结 |
| 阿哈装备点首件(四选一固定单发) | 投资策略「阿哈大悦」装备选择 overlay(无独立画面档,id_mark = 货币战争-备战.标识-简易装备;不选卡死备战) | `cw_screen_aha_equip_pick.py::CwScreenAhaEquipPick`(空决策形态 + 固定单发不问策略器;单篇 = [aha_equip_pick.md](aha_equip_pick.md)) | 点首件自动关 overlay 即终结 |
| 关闭获得类介绍 modal(聘用书/消耗品/武装箱说明) | 获得道具后自动弹出的介绍 modal(聘用书分支 / 消耗品浮层分支;武装箱说明叠 3 选 1 屏或备战) | `cw_screen_item_detail_popup.py::CwScreenItemDetailPopup`(道具详情弹窗·聘用书分支:OCR「聘用书」∧ 祈愿排他)/ `cw_screen_consumable_overlay.py::CwScreenConsumableOverlay`(阶段三双 OCR 特殊分发,无独立画面档)/ `cw_screen_armory_box.py::CwScreenArmoryBox`(阶段一身份分发)三空决策屏 | 点 ×/X 关闭即终结 |

### 5.6 战斗窗与结算、回大厅收尾

战斗自动进行(auto-battler),玩家无操作面:`operations/cw_screen/cw_screen_battle_wait.py::CwScreenBattleWait` 三段式(等结算→结算处理→结束本次访问);结算点「继续挑战」出现后 ~1.5s 结算数据才稳定(时序 #6),点继续 = 战斗窗终结回备战(自动开商店,唯 1-1 例外 #29)。对局结束回到大厅画面时,由主循环的"大厅收尾"分支直接处理(运行收尾、奖励分配、存档写入都在那里),对局主循环到此结束。

## 6. 回外循环(终结)语义总表

外层循环(`operations/cw_loop.py::CwLoop.loop`)是唯一循环;画面访问在以下动作/分支处结束、控制权返回主循环(终结判定现值 = 注册表 op 类 `terminal`/`terminal_wait` 属性,消费点经 `action_op_class_for` 读取;恒可用终结不变量 = 每个决策画面的动作空间至少含一个恒可用终结动作):

| 终结动作/条件 | 终结级别 | 语义 |
|---|---|---|
| 商店 RefreshShop | **访问终结** | 刷新是唯一引入新事实的动作(新牌面),执行即本访问结束返回主循环;重进 = 重走画面分发(命中备战的开商店态)+ 入口观察重建期望态。无 visit 级硬墙(无限刷新环 = 策略 bug,框架不兜底);现实出口 = 未观察跳过熔断(`shop.md` §5) |
| 商店 CloseShop | **访问终结** | 恒可用终结 op(全函数「无动作可做」的表达);执行位 = 动作 op `CwActionCloseShopOp` 真机械点击(幂等已关出口),返回主循环 |
| 商店全 unknown 失读窗 | **入口观察停机** | 牌面含 unknown 槽(读链终判)→ 入口观察处 `stop_running` 框架截图保留证据,决策/购买不见残缺牌面;决策侧仅 CloseShop 收工为纵深第二线(`shop.md` §5,guards.md §3) |
| 备战 StartBattle | **访问终结(唯一完成态)** | 出战 → 外循环置战斗窗口(备战→战斗→结算→回备战轮推进,`outer_loop.md` §4) |
| 备战 OpenShop | 备战环终结 | 交商店访问编排(显式开店)或回外循环重识别(读数开店) |
| 备战 OpenBox | **访问终结** | 点「开启」即返回主循环重新观察;武装箱选择画面由外循环按画面分发独立画面 op 选卡([box_pick.md](box_pick.md)),选卡动作不经备战决策循环 |
| 备战 OpenBookcard | **访问终结** | 开卡 = 专家邀请函弹窗在场 = 新事实,返回主循环按该画面分发选卡(`terminal_wait=1.8`;动作发出点 = 策略器 entry ① prep 实体面卡片分支) |
| 备战 overlay 检出 | 环中止 | 弹层/事件在场 → 返回主循环分支 handler |
| 备战无动作(None) | 合法结束本次访问 | None = 本帧无动作,返回主循环重新观察(商店域无此通道,该通道已由 CloseShop 终结取代) |
| 单选族确认离开 | 画面终结 | overlay 消失即节点完成(补给节点无结算屏);投资两屏/补给/遭遇/策划/装备 = **发出确认链(或点卡即选)即 round_success 结束本次访问**(即时上报形态,确认未生效由外循环重识别重派) |
| 推进型画面(简报/过渡/详情/弹窗) | 画面终结 | 点推进/关闭即终结(空决策形态) |
| 中断恢复的对局锁定态 | 例外约束 | 进过战斗后异常重启的对局,商店交互被游戏禁用(只能出战;`research/economy.md` §2.1 恢复态限制),外循环锁定态直通出战(`operations/cw_loop.py::locked_resume_sync_and_battle`) |

## 7. 先例与边界

- **先例(2026-09-14 收缩先例已废止)**:卖备战/买经验是商店开画面**可用且在产**的动作(执行链已接入调用,§5.4)——店内可卖备战席(候选池仅备战席)与店内购买经验(整批连点)为现行策略面动作(置换账/筹资/会话内升级,策略归属 = [../strategy-docs/23_shop_screen.md](../strategy-docs/23_shop_screen.md));备战期接收面 = [../strategy-docs/22_prep_screen.md](../strategy-docs/22_prep_screen.md)(节点内关店/重开不刷新牌面、牌面持久,节点切换才自动刷新,`research/economy.md` §2.1)。
- **商店锁**:游戏机制存在(整店级),建档已有按钮坐标,生产链路未建模——能力面登记为「存在但未接入调用」。
- **SwapDeploy**:动作类型清单/状态容器逻辑态直写/sim 消费在用,生产执行器未接入调用——能力面按动作类型清单完备性保留。
- **刷新不换牌面的场景**:节点内关店→重开不刷新(牌面持久);跨节点自动刷新全店(不继承)。判「是否刷新」以节点推进事件为识别标志(`research/economy.md` §2.1)。

## 8. 文档索引(34 篇)

主链:[prep.md](prep.md)(备战)/ [shop.md](shop.md)(商店开画面)/ [battle_wait.md](battle_wait.md)(战斗等待·结算)。
单选族:[invest_strategy.md](invest_strategy.md) / [invest_env.md](invest_env.md) / [encounter.md](encounter.md) / [supply.md](supply.md) / [megastar.md](megastar.md) / [partner.md](partner.md) / [fortune.md](fortune.md) / [planner.md](planner.md) / [wish_trial.md](wish_trial.md) / [bookcard.md](bookcard.md) / [expert_invite.md](expert_invite.md) / [box_pick.md](box_pick.md)。(原 [equip_pick.md](equip_pick.md) 随选择装备屏误判停用删除,2026-09-22。)
简报与过场:[briefing.md](briefing.md) / [boss_briefing.md](boss_briefing.md) / [plane_transition.md](plane_transition.md) / [plane_detail.md](plane_detail.md) / [plane_intel.md](plane_intel.md) / [wait_one_one.md](wait_one_one.md) / [next_button.md](next_button.md)。
弹窗与部署:[armory_box.md](armory_box.md) / [consumable_overlay.md](consumable_overlay.md) / [aha_equip_pick.md](aha_equip_pick.md) / [emblem_detail_popup.md](emblem_detail_popup.md) / [item_detail_popup.md](item_detail_popup.md) / [role_detail_overlay.md](role_detail_overlay.md) / [shop_card_detail.md](shop_card_detail.md) / [refresh_odds_popup.md](refresh_odds_popup.md) / [prep_locked_return.md](prep_locked_return.md) / [interrupt_dialog.md](interrupt_dialog.md) / [deploy.md](deploy.md) / [deploy_not_full.md](deploy_not_full.md)。

开放设计注:补给刷新的终结语义(原待裁决项)已定案落 [supply.md](supply.md);boss 简报去向已裁([boss_briefing.md](boss_briefing.md),README 已按 as-built 修正);各族其余申报面(换人卖出接缝/建档缺口/测试断档等)见各篇文末。
