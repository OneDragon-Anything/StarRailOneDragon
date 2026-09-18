# 画面 op 层(screens/ · 一画面一文档)

> 本目录 = 画面 op 层设计正本:**每个画面 op 一篇**,写「这个画面做什么观察、能发哪些动作 op、哪些动作终结交回外循环」。代码根 = `src/sr_od/application/currency_war/operations/cw_screen/`(一画面一文件)+ `obs/`(观察解析工具箱)+ `kernel/cw_screen_report/`(每画面观察上报:obs 类 + report 函数一文件);符号锚 = `文件::符号名`(行号随代码漂移,不作定位依据)。
> 分工分界:分发判定(两阶段身份分发)的单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2(本目录各篇只写画面特有的排他/穿透形态与身份锚说明);画面 op 统一规范(两 node 形态/round_wait 循环/终结 op/期望态生命周期/对账边界/report 上报接口)= [op-layer.md](op-layer.md);逐屏形态分类总表(37 屏)= [op-layer.md](op-layer.md) §3;动作执行契约 = [../flow/action_exec.md](../flow/action_exec.md)。
> 术语:逻辑态 = 动作执行后不经观察、按游戏规则推算并直写容器的预期状态;真值以下一帧观察为准(观察赢)。
> 路径缩写约定:本文反引号短路径 `research/X.md`/`data/X.md` 等 = `docs/game/currency_war/` 下对应文件(非 src 树);game 侧文档同理指向本仓 docs/。


## 1. 能力面与策略面(区分原则)

- **能力面** = 画面机制上可做的动作全集:游戏在该画面提供了什么可执行操作,以及我们把每个操作落地为哪个动作 op。七动作族(§4)与容器上报函数族(`kernel/cw_action_report/` 的 `report_action_<snake>_param` 等逻辑态直写通道)**全保留**,不随策略收缩删除。
- **策略面** = 默认策略(mandate_v1)在当前策略形态下实际会做的子集。策略面收缩是策略域变更:只改决策入口的提案集,不删执行器/词表/逻辑态直写。
- **判例**:卖备战(SellBench)与买经验(LevelUp)是商店开画面的**可用**动作(§5.4),但默认策略**不在商店期做**——两者收缩至备战期决策(策略面清单见 strategy-docs 22/23 号篇)。能力矩阵按能力面记;策略归属见 strategy-docs 画面策略篇。
- 记载纪律:每个画面列「游戏可用动作全集」并逐条给 op 映射;某动作当前不被策略使用时在策略归属列注明「策略面收缩至 X 期」,不删行。

## 2. 画面文档模板

每篇画面文档按以下九节组织(大画面各节成章,弹窗/推进族各节可短至一两行):

| # | 节 | 内容 |
|---|---|---|
| 1 | 分发判定 | 外循环怎么认出本画面(锚 = `画面名.area名`)、与相邻画面的排他/穿透形态;指向 outer_loop §2.2 |
| 2 | 画面形态声明 | 三选一:决策循环形态(问策略器,注明决策入口)/ 空决策形态(纯推进)/ 单选族例外(有选择面零逻辑态账) |
| 3 | 观察面 | 本屏读什么:消费哪些 obs 解析器、什么进 GameState(字段组/写端)、heavy/light;观察上报即对账边界 |
| 4 | 动作面 | 可用动作 op 全集 + 词表成员 + 每个动作的执行要点(点击锚、交互时序、动画等待、已知交互陷阱) |
| 5 | 终结与交回 | 哪些动作终结本访问交回外循环(terminal/terminal_wait 现值,经注册表读);交回后外循环重判的预期落点 |
| 6 | 状态上报面 | 动作 → 哪个上报函数(`kernel/cw_action_report/<snake>.py::report_action_<snake>_param`;dict 确认族到账 = `kernel/cw_exec_state.py::apply_confirm_effect`),指向 [../game_state/logic-updates/](../game_state/logic-updates/README.md) 对应篇 |
| 7 | 子态与 overlay | 本屏的子态(如备战-开商店、暗色锁定)与本屏会被哪些 overlay 覆盖、命中时交回还是自处理 |
| 8 | 守卫与防线 | 本屏的停机钩子/安灯/预算(细则指针 = [../flow/guards.md](../flow/guards.md)) |
| 9 | 遥测与锁面 | journal op 名、branch 分键、缺陷键、测试锁文件指针、game 侧知识指针 |

纪律:as-built 无状态(事故史/裁定日期不进正文);坐标一律 `画面名.area名`;分发判定不复制外循环表。

## 3. 形态分型(对照 37 屏)

- 画面 op 统一形态 = **两 node 直继承 SrOperation**:观察 node = 门 + 显式读屏 + `CwScreenXxxObs` + `report_screen_<snake>_obs` 落容器;决策动作 node = 重入裁决 + 决策 + 动作,`round_wait` 循环推进、无防御上限。判据合同 = [op-layer.md](op-layer.md) §1。
- 分型判据:入决策规范 ⇔ **选择面 ∧ 逻辑态账**(商店/备战);空决策形态 ⇔ 已建档分发画面且两者皆缺——纯推进为流程义务:观察 + 推进处理 + 交回外循环(新 op 单尝试,重试预算归外循环);单选族例外:有选择面但零逻辑态账(选卡/确认即终结,visit 内无后续决策消费逻辑态)。
- 五型 = 全形态 / 节点循环(overlay 单动作循环)/ 推进型空决策(无 report)/ 驻留状态机豁免(battle_wait,用户裁定)/ 重型屏(漏斗+波循环);逐屏分类与 report 有无总表 = [op-layer.md](op-layer.md) §3。

## 4. 动作词表与执行载体

**词表单一源** = `kernel/cw_vocab.py`(统一动作词表;白名单 = `CW_ACTION_TYPES`,新增动作必须同步登记,漏登记 = 执行面拒「未知动作类型」,动作从未真正执行)。**注册表单一源** = `operations/cw_op/cw_action_registry.py`(词表类 → 动作 op 类一张表,`action_op_for`/`action_op_class_for` 全动作唯一注册点;行序 isinstance 首中即返,is-a 链父类行兜底规则见模块头)。

| 动作族 | 词表(`kernel/cw_vocab.py`) | 执行载体 | 终结性 |
|---|---|---|---|
| BuyCard(买牌) | `CwActionBuyCardParam` | `operations/cw_op/cw_buy_card_action.py::CwActionBuyCardOp` | 非终结 |
| RefreshShop(刷新) | `CwActionRefreshShopParam` | `cw_refresh_shop_action.py::CwActionRefreshShopOp` | **段终结**(§6) |
| CloseShop(关商店) | `CwActionCloseShopParam` | `cw_close_shop_action.py::CwActionCloseShopOp`(关店点击由编排壳 `cw_op_close_shop.py::CwOpCloseShop` 承担) | **访问终结**(§6) |
| SellBench(卖备战) | `CwActionSellBenchParam` | `cw_prep_sell_bench_action.py::CwActionSellBenchOp`(词表摊平后商店/备战共用单一注册行;原商店域文件 `cw_sell_bench_action.py` 已退役删除) | 非终结 |
| LevelUp(买经验) | `CwActionLevelUpParam`(`CwActionLevelUpShopParam` 同字段双类型,显式独立行同备战 op,单击) | 注册行 = `cw_prep_level_up_action.py::CwActionLevelUpOp`;原商店域 `cw_level_up_action.py` 已退役删除 | 非终结 |
| SellDeployed(卖上阵) | `CwActionSellDeployedParam` | `cw_sell_deployed_action.py::CwActionSellDeployedOp` + 部署面换血(`cw_screen_deploy.py::_sell_offtarget_deployed`) | 非终结 |
| SwapDeploy(上阵↔备战对调) | `CwActionSwapDeployParam` | 未接线(词表+上报函数/sim 消费在役;词表完备性保留) | 非终结 |
| DeployMove(部署) | `CwActionDeployMoveParam` | `cw_deploy_move_action.py::CwActionDeployMoveOp`(bench→上阵单步拖拽,发射位逐帧现算) | 非终结 |
| 领取类(开箱) | `CwActionOpenBoxParam` | `cw_open_box_action.py::CwActionOpenBoxOp` | **访问终结**(§6) |
| 领取类 | `CwActionClickSpheresParam`/`CwActionOpenTomeParam`/`CwActionOpenBookcardParam` | 同名 `_action.py` op(`cw_open_tome_action.py` 等) | 非终结 |
| 穿戴/工具 | `CwActionWearEquipParam`/`CwActionFurnaceUseParam`/`CwActionPrivilegeCardUseParam`/`CwActionWrenchUseParam`/`CwActionPrecisionWrenchUseParam`/`CwActionStaffProjectorUseParam`/`CwActionPerfectProjectorUseParam`/`CwActionLuckyTokenUseParam` | `cw_wear_equip_action.py::CwActionWearEquipOp`/`cw_tool_use_action.py::CwActionToolUseOp` | 非终结 |
| 转场 | `CwActionOpenShopParam`/`CwActionStartBattleParam` | `cw_open_shop_action.py::CwActionOpenShopOp`(terminal 承载行,执行抛,正常路径不可达)/`cw_start_battle_action.py::CwActionStartBattleOp`(返回值在册例外) | 备战环终结/备战访问终结 |

组合壳(RunDeploy/RunEquip/RunTools)已随统一词表退役(批2b R2):部署 = 发射位逐帧现算 DeployMove 原子序,穿戴 = WearEquip 原子,工具 = 工具原子类经 `CwActionToolUseOp`;`CwScreenDeploy` 唯一生产直调 = 外循环 0j 恢复链(见 [deploy.md](deploy.md))。

**动作坐标系(二分)**:席位域动作(SellBench/SellDeployed/DeployMove)携**容器槽位表下标 0 基**(bench 0-8 / deployed 0-9,读口 `bench_slots_of`/`deployed_slots_of` 同基直取零换算);**画面物理槽位 1 基**仅存于坐标参数化机械动作(WearEquip/工具七类/OpenBox/OpenTome/OpenBookcard)的 `row`/`slot` 字段。执行坐标边换算单点 = `kernel/cw_exec_state.py::deployed_row_slot`(下标→物理排槽)/ `deployed_idx_of`(物理→下标)。

## 5. 画面×动作矩阵(能力面)

### 5.1 简报与过场(货币战争-简报 / 货币战争-BOSS简报 / 货币战争-位面过渡)

| 游戏可用动作 | 机制依据 | 我们的 op | 访问终结语义 |
|---|---|---|---|
| 简报点「下一步」 | `research/screen_flow_timing.md` 时序 #1(首领出现 +1s 可点) | `operations/cw_screen/cw_screen_briefing.py::CwScreenBriefing`(外循环 0r 分支);内嵌词缀效果采集段 `_collect_affix_effects`(逐词缀点采 OCR 效果,对注册表 `data/affix_effects_data.py` 比对,新名/不一致才截图收集;采集写端 best-effort,OCR 采不到即跳过) | 点推进即终结(空决策形态;点采 tooltip 不终结) |
| BOSS 简报点空白 | 同上 #26(「点击空白处继续」出现即可点) | `operations/cw_screen/cw_screen_boss_briefing.py::CwScreenBossBriefing`(0p 分支);点掉后交回外循环重判——boss 战自动开打,商店不开(模块头 as-built 实证;game 侧口述时序 #14「自动开店」已废,见 [boss_briefing.md](boss_briefing.md) 开放设计注) | 点空白即终结 |
| 位面过渡点空白 | 同上 #2 | `operations/cw_screen/cw_screen_plane_transition.py::CwScreenPlaneTransition`(0q 分支) | 点空白即终结 |

### 5.2 投资环境(货币战争-投资环境)

| 游戏可用动作 | 机制依据 | 我们的 op | 访问终结语义 |
|---|---|---|---|
| 三选一选环境卡 | `data/gameplay.md`(投资环境 = 整局增益);开场必经 | `operations/cw_screen/cw_screen_invest_env.py::CwScreenInvestEnv`(0s 分支);决策 = pick 族 `decide_invest`(规格 = strategy-docs 13 号篇) | 确认离开(overlay 消失) |
| 刷新圆钮重掷三卡 | `research/screen_flow_timing.md` #4(刷新动画 ~2s) | 同 op 内整组重掷(`cw_screen_invest_env.py::_decide_and_act`:点→等动画→**本访问即交回**,pending+round_retry 重入后重观察重决策);是否建议刷新 = `PickEvent.refresh` 判据(`kernel/cw_events.py::decide_event`,math_proofs P81) | **刷新即本访问终结**(刷新 = 唯一引入新事实的动作);确认离开才画面终结 |

### 5.3 备战画面(货币战争-备战)

主链决策画面。建档 = `assets/game_data/screen_info/currency_war_battle_prep.yml`(备战栏-1..9 / 前排-1..4 / 后排-N / 按钮-商店 / 按钮-出战 / 区域-出售区 / 备战标识-购买经验 等 area)。文档 = [prep.md](prep.md)。

| 游戏可用动作 | 机制依据 | 我们的 op | 策略归属 | 访问终结语义 |
|---|---|---|---|---|
| 上阵(拖备战栏→前排/后排空槽) | 等级=可上阵数(`data/gameplay.md`);站位前台/后台激活角色赋能 | `DeployMove`(部署 = 发射位逐帧现算原子序;`CwScreenDeploy` 直调 = 0j 恢复链,见 [deploy.md](deploy.md)) | 备战期(22/24 号篇) | 非终结 |
| 换排(上阵单位前排↔后排拖拽) | 同上 | 部署机内拖拽(`_deploy_deterministic` 含错排归位 `_fix_misplaced_rows`) | 备战期 | 同上 |
| 卖备战(拖备战栏→区域-出售区) | 卖出退金(`research/economy.md` §3;单一源 `kernel/cw_economy.py::sell_refund`) | `CwActionSellBenchOp`(注册行)+ `prep_actions.py::drag_bench_to_sell` | 备战期:腾位(M4)/凑息/筹资/换线塌缩(22 号篇) | 非终结 |
| 卖上阵(拖上阵位→出售区) | 同上 | `CwActionSellDeployedOp` + 部署面换血(`cw_screen_deploy.py::_sell_offtarget_deployed`) | 备战期/部署期换血(24 号篇) | 非终结 |
| 买经验(点「备战标识-购买经验」) | 4 金/击=+4 经验,升级=过门槛表(`research/xp-rules.md` §2;表值 = `kernel/cw_economy.py::XP_TO_NEXT_LEVEL`) | `CwActionLevelUpOp` 备战连点 | 备战期(22 号篇;商店期收缩后的唯一买经验期) | 非终结 |
| 开商店(点「按钮-商店」) | 商店每节点自动刷新 1 次(`data/gameplay.md`) | `OpenShop`(read_only 两形态);编排 = `cw_screen_prep.py` 商店访问段(文档 = [shop.md](shop.md)) | 备战期(进商店访问的唯一入口动作) | **备战环终结**:开店/读数开店后交商店访问编排或回外循环重识别 |
| 出战(点「按钮-出战」) | 未在行动值内取胜扣血(`data/gameplay.md`) | `CwActionStartBattleOp`;发射意图 = mandate_v1 前置发射位(判据 = `kernel/cw_launch_admission.py::readiness_launch_decision`);执行 = 统一执行器 `operations/cw_loop.py::launch_battle_unified` | 备战期出口(唯一完成态) | **备战访问终结**:交回外循环战斗分支 |
| 点奖励球(区域-奖励) | 奖励球飞行动画 ≤2s(`research/screen_flow_timing.md` #16) | `ClickSpheres`(批式:一次全点→等 2s→统一验证;席满让路门 = `strategies/impl/mandate_v1/entry.py` 席满探针段) | 备战期 | 非终结 |
| 开补给箱(点备战栏箱位) | 开箱即腾席(武装箱 overlay) | `OpenBox`(点「开启」即交回;选卡弹窗由画面 op `CwScreenBoxPick` 闭环,非动作) | 备战期(实体面优先,`entry.py::emit` ①) | **访问终结** |
| 开秘密典籍 | 典籍占备战席 1 槽 | `OpenTome`(选卡弹窗由画面 op `CwScreenBoxPick` 闭环,非动作) | 备战期(实体面优先,`entry.py::emit` ①) | 非终结 |
| 查看详情(角色/装备详情浮层) | 游戏辅助功能(`data/gameplay.md`) | 推进弹窗族 `CwScreenRoleDetailOverlay` 等(1b/1d/1g 分支,空决策形态) | 无策略归属(推进为流程义务) | 关闭/点空白即终结 |
| 锁商店(跨节点保牌) | `research/economy.md` §2.1(整店级锁;官方机制) | **生产链路未建模**(建档已有「按钮-商店锁定」坐标备作将来) | 无 | — |

### 5.4 部署执行段(备战画面内,无独立建档画面)与商店开画面(货币战争-备战-开商店)

部署不是独立 screen_info 画面:部署机 `CwScreenDeploy` 以拖拽在备战画面上执行(`SCREEN_NAME = '货币战争-备战'`);`currency_war_deploy_not_full.yml`(未达上限警告,0d 分支)为部署被拒确认弹窗。商店开画面建档 = `currency_war_battle_prep_shop_open.yml`;文档 = [shop.md](shop.md)。

商店开画面能力面:买牌(`CwActionBuyCardOp`)/刷新(`CwActionRefreshShopOp`,段终结)/买经验(能力面可用、策略面收缩)/卖备战(同前)/关商店(`CwActionCloseShopOp` + CwOpCloseShop,访问终结)/牌详情弹窗(0t,点 X 绝不点购买)/刷新概率表(0e2,概率条直读进 `refresh_probs` 为观察非动作)/锁商店(未建模)。策略面 = 商店期默认动作面仅 买/刷/关(判例 §7;23 号篇)。

### 5.5 事件单选族(overlay)

投资策略/补给/遭遇(货币战争-遭遇节点)/盛会之星/选择伙伴/选择装备/命运卜者(`cw_screen_fortune.py`)/骇入策划(`cw_screen_planner.py`)/祈愿试炼/星徽秘典四选一/专家邀请函/武装箱弹窗。决策 = pick 族九接口 + `decide_box_card`,规格 = strategy-docs 13 号篇。

| 游戏可用动作 | 机制依据 | 我们的 op | 访问终结语义 |
|---|---|---|---|
| 选卡(N 选 1) | 各事件机制(`data/gameplay.md`/`research/economy.md` §9) | 各画面 op(分支序 0c/0e/0e1/0a 族/0h/0i/0k/0f) | 确认离开(overlay 消失)= 画面终结 |
| 逐卡/整屏刷新重掷 | 刷新后 ~2s 稳定(时序 #13/#19/#23) | 投资策略逐槽(`cw_screen_invest_strategy.py::_emit_refresh_click`)/ 遭遇(`cw_screen_encounter.py::_try_refresh`)/ 补给(`cw_screen_supply_node.py`「剩余次数」文本锚定);建议刷新 = `PickEvent.refresh`(`kernel/cw_events.py::decide_event`,P81;策略屏逐槽 = `PickEvent.refresh_slots`) | 投资策略逐卡刷新 = **本访问终结**(点一槽刷新圆钮即 pending+round_retry 交回,次轮重入重观察重决策)——与投资环境整组重掷同款;遭遇/补给刷新不终结(留在本画面访问内重读重选);确认离开才画面终结 |
| 开书册卡(点备战席槽位「开启」→ 弹专家邀请函) | 书册卡 = 备战席占槽道具 | `cw_screen_expert_invite.py::open_card`(0k 处理链首节点;找书册卡/点开启/过渡帧等待,纯导航零决策) | 弹窗开成即链内转选卡(不终结外层访问) |
| 返回备战/返回选择(暗色锁定子态) | 暗色蒙层态判别锚 = 右上操作按钮(screen_flow_timing #18) | `operations/cw_screen/cw_screen_prep_locked_return.py::CwScreenPrepLockedReturn`(0m;策略锁定/遭遇锁定两档参数化) | 点返回即终结 |
| 关「属性详情」面板 | 点卡身上部误触发 | 未建模独立处理(点卡 = 机械单发);面板残留归下一帧重入自愈(重分发重走链/详情 overlay 族分支) | 面板关闭即随重入收敛 |
| 盛会之星「请选择强化角色」伴随文案 | 该 area 与「按钮-确认选择」rect 重叠,系伴随文案非步骤 | 未建模独立处理(确认 = 纯机械单发);确认未落地残留归巨星节点循环重入自愈 | 确认推进即画面终结 |

### 5.6 战斗窗与结算、回大厅收口

战斗自动进行(auto-battler),玩家无操作面:`operations/cw_screen/cw_screen_battle_wait.py::CwScreenBattleWait` 三段式(等结算→结算处理→交回);结算点「继续挑战」出现后 ~1.5s 结算数据才稳定(时序 #6),点继续 = 战斗窗终结回备战(自动开商店,唯 1-1 例外 #29)。对局结束回大厅(货币战争-大厅,3c 分支)= 外循环直管收口(run 收口/分配器/存档装配写端),对局循环终止。

## 6. 回外循环(终结)语义总表

外层循环(`operations/cw_loop.py::CwLoop.loop`)是唯一循环;画面访问在以下动作/分支处结束、控制权交回外循环(终结判定现值 = 注册表 op 类 `terminal`/`terminal_wait` 属性,消费点经 `action_op_class_for` 读取;恒可用终结不变量 = 每个决策画面的动作空间至少含一个恒可用终结动作):

| 终结动作/条件 | 终结级别 | 语义 |
|---|---|---|
| 商店 RefreshShop | **段终结** | 刷新是唯一引入新事实的动作(新牌面),执行即本段 break;下一段入口观察重建期望态。visit 级刷新硬墙 = `cw_screen_buy_cards.py::MAX_REFRESH`(超墙终结集降级仅关店,`shop.md` §3) |
| 商店 CloseShop | **访问终结** | 恒可用终结 op(全函数「无动作可做」的表达);关店点击由编排壳 CwOpCloseShop 执行,节点探针收尾后交回外循环 |
| 商店全 unknown 失读窗 | **入口观察停机** | 牌面含 unknown 槽(读链终判)→ 入口观察处 `stop_running` 框架截图留证,决策/购买不见残缺牌面;决策侧仅 CloseShop 收工为纵深第二线(`shop.md` §5,guards.md §3) |
| 备战 StartBattle | **访问终结(唯一完成态)** | 出战 → 外循环置战斗窗口(备战→战斗→结算→回备战轮推进,`outer_loop.md` §4) |
| 备战 OpenShop | 备战环终结 | 交商店访问编排(显式开店)或回外循环重识别(读数开店) |
| 备战 OpenBox | **访问终结** | 点「开启」即交回外循环重观察;武装箱选择画面由外循环按画面分发独立画面 op 选卡([box_pick.md](box_pick.md)),选卡动作不经备战决策循环 |
| 备战 overlay 检出 | 环中止 | 弹层/事件在场 → 交回外循环分支 handler |
| 备战无动作(None) | 合法交回 | None = 本帧无动作,交回外循环重观察(商店域无此通道,该通道已由 CloseShop 终结取代) |
| 单选族确认离开 | 画面终结 | overlay 消失即节点完成(补给节点无结算屏) |
| 推进型画面(简报/过渡/详情/弹窗族) | 画面终结 | 点推进/关闭即终结(空决策形态) |
| 恢复局锁定态 | 例外约束 | 进过战斗后异常重启的恢复局,商店交互被游戏禁用(只能出战;`research/economy.md` §2.1 恢复态限制),外循环锁定态直通出战(`operations/cw_loop.py::locked_resume_sync_and_battle`) |

## 7. 判例与边界

- **判例**:卖备战/买经验是商店开画面**可用**动作(机制路径已验证),但默认策略**不在商店期做**——策略面收缩至备战期(商店期 = 买牌/刷新/关商店;席满腾位形态 = 关店时交还外循环,由备战 op 在自己的决策周期自行判断与卖出;节点内关店/重开不刷新牌面、牌面持久,节点切换才自动刷新,`research/economy.md` §2.1)。策略归属 = [../strategy-docs/23_shop_screen.md](../strategy-docs/23_shop_screen.md)(商店期动作面)与 [../strategy-docs/22_prep_screen.md](../strategy-docs/22_prep_screen.md)(备战期接收面)。
- **商店锁**:游戏机制存在(整店级),建档已有按钮坐标,生产链路未建模——能力面登记为「存在但未接线」。
- **SwapDeploy**:词表/容器逻辑态直写/sim 消费在役,生产执行器未接线——能力面按词表完备性保留。
- **刷新不换牌面的场景**:节点内关店→重开不刷新(牌面持久);跨节点自动刷新全店(不继承)。判「是否刷新」以节点推进事件为锚(`research/economy.md` §2.1)。

## 8. 文档索引(35 篇)

主链:[prep.md](prep.md)(备战)/ [shop.md](shop.md)(商店开画面)/ [battle_wait.md](battle_wait.md)(战斗等待·结算)。
单选族:[invest_strategy.md](invest_strategy.md) / [invest_env.md](invest_env.md) / [encounter.md](encounter.md) / [supply.md](supply.md) / [megastar.md](megastar.md) / [partner.md](partner.md) / [equip_pick.md](equip_pick.md) / [fortune.md](fortune.md) / [planner.md](planner.md) / [wish_trial.md](wish_trial.md) / [bookcard.md](bookcard.md) / [expert_invite.md](expert_invite.md) / [box_pick.md](box_pick.md)。
简报与过场:[briefing.md](briefing.md) / [boss_briefing.md](boss_briefing.md) / [plane_transition.md](plane_transition.md) / [plane_detail.md](plane_detail.md) / [plane_intel.md](plane_intel.md) / [wait_one_one.md](wait_one_one.md) / [next_button.md](next_button.md)。
弹窗与部署:[armory_box.md](armory_box.md) / [consumable_overlay.md](consumable_overlay.md) / [aha_equip_pick.md](aha_equip_pick.md) / [emblem_detail_popup.md](emblem_detail_popup.md) / [item_detail_popup.md](item_detail_popup.md) / [role_detail_overlay.md](role_detail_overlay.md) / [shop_card_detail.md](shop_card_detail.md) / [refresh_odds_popup.md](refresh_odds_popup.md) / [prep_locked_return.md](prep_locked_return.md) / [interrupt_dialog.md](interrupt_dialog.md) / [deploy.md](deploy.md) / [deploy_not_full.md](deploy_not_full.md)。

开放设计注:补给刷新的终结语义候裁已落 [supply.md](supply.md);boss 简报去向已裁([boss_briefing.md](boss_briefing.md),README 已按 as-built 修正);各族其余申报面(m1p 接缝/建档缺口/测试锁断档等)见各篇文末。
