# 画面-动作能力矩阵(screens-actions-capability)

> 定位:货币战争主链每一画面/状态的「游戏可用动作全集 + 我们的动作 op 映射 + 回外循环(终结)语义」正本。本篇记**能力面**(画面机制上可做的动作全集);**策略面**(默认策略实际会做的子集)= strategy-docs 画面策略篇 22-27(逐画面一文档,索引 = [../strategy-docs/README.md](../strategy-docs/README.md))。
> 机制事实依据 = `docs/game/currency_war/data/gameplay.md`(官方玩法)、`research/xp-rules.md`、`research/screen_flow_timing.md`、`research/economy.md` 与 `assets/game_data/screen_info/` 画面建档;op 映射依据 = 代码现状。符号锚 = `文件::符号名`(行号不写,随代码漂移);路径根 = `src/sr_od/application/currency_war/`。
> 读者 = 无会话历史的工程师/智能体。职责分界:「循环怎么转、路由怎么走」= [outer_loop.md](outer_loop.md)、[README.md](README.md);「一次访问内观察→决策→执行的编排」= [prep_visit.md](prep_visit.md)、[screen_op.md](screen_op.md)、[shop_visit.md](shop_visit.md);「每个画面策略会做什么、按什么判据」= strategy-docs 画面策略篇(22-27)与本目录各判据篇。

## 1. 能力面与策略面(区分原则,用户裁定 2026-09-14)

- **能力面** = 画面机制上可做的动作全集:游戏在该画面提供了什么可执行操作,以及我们把每个操作落地为哪个动作 op。七动作族(§2)与容器转移函数(`kernel/cw_game_state.py::apply_shop_action_logic` 等投影通道)**全保留**,不随策略收缩删除。
- **策略面** = 默认策略(mandate_v1)在当前策略形态下实际会做的子集。策略面收缩是策略域变更:只改决策入口的提案集,不删执行器/词表/投影。
- **判例(在案裁定)**:卖备战(SellBench)与买经验(LevelUp)是商店开画面的**可用**动作(§3.5),但默认策略**不在商店期做**——两者收缩至备战期决策(策略面清单见 22/23 号篇)。能力矩阵按能力面记;策略归属见 strategy-docs 画面策略篇(22-27)。
- 本篇记载纪律:每个画面列「游戏可用动作全集」并逐条给 op 映射;某动作当前不被策略使用时在策略归属列注明「策略面收缩至 X 期」,不删行。

## 2. 动作词表:七动作族与执行载体

七动作族 = 商店/备战两域共用的动作词汇核,词表载体 = `kernel/cw_vocab.py`(策略动作 `Action` 族)与 `kernel/cw_prep_actions.py`(备战域 `PrepAction` 族)。动作 op 执行载体两套:

| 动作族 | 词表载体 | 商店域 op(执行器) | 备战域执行载体 | 终结性 |
|---|---|---|---|---|
| BuyCard(买牌) | `kernel/cw_vocab.py::BuyCard` | `operations/cw_op/cw_shop_actions.py::BuyCardOp` | —(备战域无买牌;牌只在商店买) | 非终结 |
| RefreshShop(刷新) | `kernel/cw_vocab.py::RefreshShop` | `cw_shop_actions.py::RefreshShopOp`(`terminal=True`) | — | **段终结**(§4) |
| CloseShop(关商店) | `kernel/cw_vocab.py::CloseShop` | `cw_shop_actions.py::CloseShopOp`(`terminal=True`;关店点击由编排壳 `operations/cw_op/cw_op_close_shop.py::CwOpCloseShop` 承担) | — | **访问终结**(§4) |
| SellBench(卖备战) | `kernel/cw_vocab.py::SellBench`(族 A 下标)/ `kernel/cw_prep_actions.py::SellBench`(族 B 物理槽位 1-9) | `cw_shop_actions.py::SellBenchOp`(商店域,机制上可用;策略面收缩后商店期不提案,见 §5 判例) | `prep_actions.py::PrepActionExecutor` → `prep_actions.py::drag_bench_to_sell`(拖备战栏→出售区) | 非终结 |
| LevelUp(买经验) | `kernel/cw_vocab.py::LevelUp`(`LevelUpShop` is-a `LevelUp`,同 op 单击)/ `kernel/cw_prep_actions.py::LevelUp`(备战域,连点至升一级) | `cw_shop_actions.py::LevelUpOp`(单击「购买经验」=+4 经验,非整级;机制依据 `research/xp-rules.md` §2) | `PrepActionExecutor` 备战连点循环(单击价现读,缺读兜底 `kernel/cw_economy.py::XP_CLICK_COST_FALLBACK`) | 非终结 |
| SellDeployed(卖上阵) | `kernel/cw_vocab.py::SellDeployed` | —(未入商店 op 表 `cw_shop_actions.py::_OP_TABLE`) | `PrepActionExecutor`(拖上阵位→出售区)/ `operations/cw_screen/cw_screen_deploy.py::_sell_offtarget_deployed`(部署面换血卖出) | 非终结 |
| SwapDeploy(上阵↔备战对调) | `kernel/cw_vocab.py::SwapDeploy` | — | —(词表+容器投影/sim 消费;生产执行器未接线,词表完备性保留) | 非终结 |

补充词条(非七动作族但属动作空间):`CompTransaction`(整档替换事务,`cw_shop_actions.py::CompTransactionOp`,终结邻接 fallback)、`DeployMove`(备战栏→上阵拖拽,`kernel/cw_prep_actions.py::DeployMove` + 部署机)、控制流/组合动作(`ClickSpheres`/`OpenBox`/`OpenTome`/`PickBoxCard`/`RunDeploy`/`RunEquip`/`RunTools`/`OpenShop`/`StartBattle`,全集白名单 = `kernel/cw_prep_actions.py::PREP_ACTION_TYPES`)。

**双族坐标系**(跨域阅读必读,单一源 = `kernel/cw_vocab.py` Action 节约定块):族 A(`cw_vocab`)= 状态容器槽位表下标(bench 0-8 / deployed 0-9);族 B(`cw_prep_actions`)= 画面物理槽位(bench 1-9 / deployed row+slot)。换算:bench 域族 B = 族 A + 1;deployed 域 front idx=slot−1、back idx=4+slot−1。

## 3. 画面×动作矩阵(主链)

### 3.1 简报与过场(货币战争-简报 / 货币战争-BOSS简报 / 货币战争-位面过渡)

| 游戏可用动作 | 机制依据 | 我们的 op | 访问终结语义 |
|---|---|---|---|
| 简报点「下一步」 | `research/screen_flow_timing.md` 口述时序 #1(首领出现 +1s 可点) | `operations/cw_screen/cw_screen_briefing.py::CwScreenBriefing`(外循环 0r 分支) | 点推进即终结(空决策形态,`screen_op.md` §8.3) |
| BOSS 简报点空白 | 同上 #26(「点击空白处继续」出现即可点) | `operations/cw_screen/cw_screen_boss_briefing.py::CwScreenBossBriefing`(0p 分支);关闭后自动开店(screen_flow_timing #14 触发源清单) | 点空白即终结 |
| 位面过渡点空白 | 同上 #2 | `operations/cw_screen/cw_screen_plane_transition.py::CwScreenPlaneTransition`(0q 分支) | 点空白即终结 |

### 3.2 投资环境(货币战争-投资环境)

| 游戏可用动作 | 机制依据 | 我们的 op | 访问终结语义 |
|---|---|---|---|
| 三选一选环境卡 | `data/gameplay.md`(投资环境 = 整局增益);开场必经 | `operations/cw_screen/cw_screen_invest_env.py::CwScreenInvestEnv`(0s 分支);决策 = pick 族 `decide_invest`(契约面 `strategies/impl/cw_strategy.py::CwStrategy`,规格 = strategy-docs 13 号篇) | 确认离开(overlay 消失) |
| 刷新圆钮重掷三卡 | `research/screen_flow_timing.md` #4(刷新动画 ~2s) | 同 op 内整组重掷(`cw_screen_invest_env.py::_decide_and_act`:文本锚定刷新钮→点→等动画→重读);是否建议刷新 = `PickEvent.refresh` 判据(`kernel/cw_events.py::decide_event`,math_proofs P81) | 刷新不终结(留在本画面重选);确认离开才终结 |

### 3.3 备战画面(货币战争-备战)

主链决策画面。建档 = `assets/game_data/screen_info/currency_war_battle_prep.yml`(备战栏-1..9 / 前排-1..4 / 后排-N / 按钮-商店 / 按钮-出战 / 区域-出售区 / 备战标识-购买经验 等 area)。决策入口 = `strategies/impl/mandate_v1/bridge.py::decide_prep_screen` → `entry.py::emit`(三遍编排);执行器 = `prep_actions.py::PrepActionExecutor` + 部署机/开关店 op;编排 = `operations/cw_screen/cw_screen_prep.py::CwScreenPrep`(1 分支)。

| 游戏可用动作 | 机制依据 | 我们的 op | 策略归属 | 访问终结语义 |
|---|---|---|---|---|
| 上阵(拖备战栏→前排/后排空槽) | 等级=可上阵数(`data/gameplay.md`);站位前台/后台激活角色赋能 | `DeployMove`(族 B)+ 部署机 `operations/cw_screen/cw_screen_deploy.py::CwScreenDeploy.deploy`(组合路径 = `RunDeploy`) | 备战期(22/24 号篇) | 非终结;部署属未建模投影面 → 执行后保守回退交回外循环重观察(prep_visit.md §1) |
| 换排(上阵单位前排↔后排拖拽) | 同上(放对激活赋能) | 部署机内拖拽(`_deploy_deterministic` 含错排归位 `_fix_misplaced_rows`) | 备战期 | 同上 |
| 卖备战(拖备战栏→区域-出售区) | 卖出退金规则(`research/economy.md` §3,单一源 `kernel/cw_economy.py::sell_refund`) | `PrepActionExecutor` → `prep_actions.py::drag_bench_to_sell`;词表 `kernel/cw_prep_actions.py::SellBench` | 备战期:腾位(M4)/凑息(P49 ⑤)/筹资/换线塌缩(22 号篇) | 非终结 |
| 卖上阵(拖上阵位→出售区) | 同上 | 词表 `kernel/cw_vocab.py::SellDeployed`;备战执行器 + 部署面换血(`cw_screen_deploy.py::_sell_offtarget_deployed`) | 备战期/部署期换血(24 号篇) | 非终结 |
| 买经验(点「备战标识-购买经验」) | 4 金/击=+4 经验,升级=过门槛表(`research/xp-rules.md` §2;表值 = `kernel/cw_economy.py::XP_TO_NEXT_LEVEL`) | `PrepActionExecutor` 备战连点循环;词表 `kernel/cw_prep_actions.py::LevelUp` | 备战期(22 号篇;商店期收缩后的唯一买经验期) | 非终结 |
| 开商店(点「按钮-商店」) | 商店每节点自动刷新 1 次(`data/gameplay.md`);备战帧金币可见可读(`kernel/cw_prep_actions.py::OpenShop` 注) | 词表 `kernel/cw_prep_actions.py::OpenShop`(read_only 两形态);编排 = `cw_screen_prep.py` 商店访问段 | 备战期(进商店访问的唯一入口动作) | **备战环终结**:开店/读数开店后交商店访问编排或回外循环重识别(prep_visit.md §1/§3) |
| 出战(点「按钮-出战」) | 未在行动值内取胜扣血(`data/gameplay.md`) | 词表 `kernel/cw_prep_actions.py::StartBattle`;发射核 = `kernel/cw_launch_admission.py::readiness_launch_decision` + `operations/cw_loop.py::readiness_battle_launch`(达标臂) | 备战期出口(唯一完成态) | **备战访问终结**:交回外循环战斗分支(prep_visit.md §3) |
| 点奖励球(区域-奖励) | 奖励球飞行动画 ≤2s(`research/screen_flow_timing.md` #16) | `PrepActionExecutor._click_spheres`(批式:一次全点→等 2s→统一验证);词表 `ClickSpheres` | 备战期(席满让路门 = `strategies/impl/mandate_v1/entry.py` 席满探针段) | 非终结 |
| 开补给箱(点备战栏箱位)/开秘密典籍 | 开箱即腾席(武装箱 overlay);典籍占备战席 1 槽 | 词表 `OpenBox`/`OpenTome` + `PickBoxCard`(四选一) | 备战期(实体面优先,`entry.py::emit` ①) | 非终结(选卡弹窗由 ①臂闭环) |
| 查看详情(角色/装备详情浮层) | 攻略/详情为游戏辅助功能(`data/gameplay.md`) | 推进弹窗族:`operations/cw_screen/cw_screen_role_detail_overlay.py::CwScreenRoleDetailOverlay` 等(1b/1d/1g 分支,空决策形态) | 无策略归属(推进为流程义务) | 关闭/点空白即终结 |
| 锁商店(跨节点保牌) | `research/economy.md` §2.1(整店级锁;官方机制) | **生产链路未建模**(无识别无动作;建档已有「按钮-商店锁定」坐标备作将来) | 无 | — |

### 3.4 部署执行段(备战画面内,无独立建档画面)

部署不是一个独立 screen_info 画面:部署机 `CwScreenDeploy` 的 `SCREEN_NAME = '货币战争-备战'`,以拖拽在备战画面上执行(op 名「货币战争-部署角色」),另有 `currency_war_deploy_not_full.yml`(货币战争-未达上限警告,0d 分支 `CwScreenDeployNotFull`)为部署被游戏拒时的确认弹窗。

| 游戏可用动作 | 机制依据 | 我们的 op | 访问终结语义 |
|---|---|---|---|
| 上阵(CV 占用检测 → 逐角色按前后台属性拖入空槽) | 后排格数 = 6+(部署上限−等级)(ADR-0385 口径;布局选档单一入口 `obs/cw_back_layout.py::select_back_layout`) | `cw_screen_deploy.py::CwScreenDeploy.deploy`(`_deploy_deterministic`) | 部署完成后交回调用方(备战环/前台无角色恢复链 0j),非独立画面访问 |
| 换血卖出(off-target 上阵件挡 target 上场时先卖) | 换血 victim 资格单一源 = `kernel/cw_deploy_logic.py::swap_sell_exclusion_reason`;围栏 = `kernel/cw_launch_admission.py::DEPLOY_FENCE` ∋ 与否经 `offtarget_sell_allowed` | `cw_screen_deploy.py::_sell_offtarget_deployed` | 同上 |
| 未达上限确认(点确认完成部署) | 上阵数低于等级上限时游戏弹确认 | `operations/cw_screen/cw_screen_deploy_not_full.py::CwScreenDeployNotFull` | 点确认即终结(弹窗消失) |

### 3.5 商店开画面(货币战争-备战-开商店)

建档 = `assets/game_data/screen_info/currency_war_battle_prep_shop_open.yml`(商店牌-1..5 / 按钮-刷新 / 备战标识-购买经验 / 按钮-收起 等 area)。决策入口 = `strategies/impl/mandate_v1/shop.py::decide_shop_action`(全函数:f(期望态)→恰一个动作);单动作循环 = `operations/cw_screen/cw_screen_buy_cards.py::run_buy_waves`;op 分发 = `cw_shop_actions.py::shop_action_op_for`。进入路径三载体:显式开店(OpenShop)/外循环 0n 转交(店已开)/发射帧仲裁受限访问(`operations/cw_loop.py` 发射帧仲裁段;载体表 = flow/session.md)。

| 游戏可用动作 | 机制依据 | 我们的 op | 策略归属 | 访问终结语义 |
|---|---|---|---|---|
| 买牌(点商店牌-N) | 买后槽位留空不紧缩;满栏仍可买触发合成的牌(一击多张,`research/merge_mechanics.md`);牌费 = 费用徽章直读 | `cw_shop_actions.py::BuyCardOp`(槽号定位 = payload 定长槽阵列→「商店牌-N」坐标;买前裁片留证) | 商店期主力动作(23 号篇) | 非终结 |
| 刷新(点「按钮-刷新」) | 手动刷新 2 金/次恒定(`research/economy.md` §2;常量 `kernel/cw_economy.py::REFRESH_COST_BASE`);刷新后整店 5 槽全换(同 §2.1) | `cw_shop_actions.py::RefreshShopOp`(刷前现读→点刷新→牌行两帧指纹一致门) | 商店期(刷新门判据 = 23 号篇) | **段终结**(§4) |
| 买经验(点「备战标识-购买经验」) | 同 §3.3 买经验行 | `cw_shop_actions.py::LevelUpOp`(单击;`LevelUpShop` 意图) | **能力面可用、策略面收缩**:默认策略不在商店期买经验,移备战期决策(§5 判例;23 号篇) | 非终结 |
| 卖备战(拖备战栏→出售区;店开态备战席条仍可见) | 同 §3.3 卖备战 | `cw_shop_actions.py::SellBenchOp`(`drag_bench_to_sell` 复用) | **能力面可用、策略面收缩**:席满腾位/凑息卖收缩至备战期(§5 判例;腾位链 = 关店→备战卖→重开,牌面持久,23 号篇) | 非终结 |
| 关商店(点「按钮-收起」) | 收起 ~1s 过场回备战(`research/screen_flow_timing.md` #15) | `cw_shop_actions.py::CloseShopOp`(no-op)+ 编排壳 `operations/cw_op/cw_op_close_shop.py::CwOpCloseShop` 承担点击 | 商店期收工动作(恒可用终结) | **访问终结**(§4) |
| 查看牌详情(商店牌详情弹窗) | — | `operations/cw_screen/cw_screen_shop_card_detail.py::CwScreenShopCardDetailPopup`(0t 分支;点 X 验消失,**绝不点购买**) | 无(推进为流程义务) | 关闭即终结 |
| 查看刷新概率表(弹窗/概率条) | 概率表 OCR 双源一致(`research/economy.md` §2;单一源 `data/cw_shop_odds.py::REFRESH_PROB`) | 弹窗:`operations/cw_screen/cw_screen_refresh_odds_popup.py::CwScreenRefreshOddsPopup`(0e2);概率条直读进 `refresh_probs`(观察,非动作) | 无 | 关闭即终结 |
| 锁商店 | 同 §3.3 | 未建模(同 §3.3 行) | 无 | — |

### 3.6 事件单选族(overlay)

投资策略(货币战争-投资策略)/补给(货币战争-补给)/遭遇(货币战争-遭遇节点)/盛会之星(货币战争-盛会之星)/选择伙伴/选择装备(cw_equip_pick)/命运卜者(cw_fortune_picker)/骇入策划(cw_hacker_planner)/祈愿试炼/星徽秘典四选一/专家邀请函/武装箱弹窗(货币战争-武装箱弹窗)。决策 = pick 族九接口 + `decide_box_card`,规格 = strategy-docs 13 号篇。

| 游戏可用动作 | 机制依据 | 我们的 op | 访问终结语义 |
|---|---|---|---|
| 选卡(N 选 1) | 投资策略整局增益+难度加成(`data/gameplay.md`/`research/economy.md` §9) | 各画面 op(`operations/cw_screen/cw_screen_invest_strategy.py` 等;分支序 0c/0e/0e1/0a 族/0h/0i/0k/0f) | 确认离开(overlay 消失)= 画面终结 |
| 逐卡/整屏刷新重掷 | 投资策略逐卡刷新、遭遇/补给屏刷新(时序 #13/#19/#23:刷新后 ~2s 稳定) | 投资策略逐槽(`cw_screen_invest_strategy.py::_emit_refresh_click`)/ 遭遇(`cw_screen_encounter.py::_try_refresh`)/ 补给(「剩余次数」文本锚定点刷新,`cw_screen_supply_node.py`);建议刷新 = `PickEvent.refresh`(`kernel/cw_events.py::decide_event`,P81;策略屏逐槽 = `PickEvent.refresh_slots`) | 刷新不终结(留在本画面);确认离开才终结 |
| 返回备战/返回选择(暗色锁定子态) | 暗色蒙层态判别锚 = 右上操作按钮(screen_flow_timing #18) | `operations/cw_screen/cw_screen_prep_locked_return.py::CwScreenPrepLockedReturn`(0m;策略锁定/遭遇锁定两档参数化) | 点返回即终结 |

### 3.7 战斗窗与结算(货币战争-战斗 / 货币战争-战斗结算 / 货币战争-结算 / 货币战争-结算-战报)

| 游戏可用动作 | 机制依据 | 我们的 op | 访问终结语义 |
|---|---|---|---|
| (战斗自动进行,玩家无操作面) | auto-battler(`data/gameplay.md`) | `operations/cw_screen/cw_screen_battle_wait.py::CwScreenBattleWait` 三段式:等结算→结算处理→交回 | 结算读点后交回外循环(备战双锚宽判定命中即 success) |
| 结算点「继续挑战」 | 「继续挑战」出现后 ~1.5s 结算数据才稳定(screen_flow_timing #6,用户复核裁定) | 同上结算段(读点前等待 1.5s + 重截) | 点继续 = 战斗窗终结,回备战(自动开商店,唯 1-1 例外,#29) |

### 3.8 回大厅收口(货币战争-大厅)

| 游戏可用动作 | 机制依据 | 我们的 op | 访问终结语义 |
|---|---|---|---|
| 对局结束留在结算/大厅 | 胜利结算/职级评价(`data/gameplay.md`) | 外循环 3c 分支直管收口(runs summary/分配器/存档写端;不迁移) | 对局循环终止(`round_success('对局结束,回大厅')`) |

## 4. 回外循环(终结)语义总表

外层循环(`operations/cw_loop.py::CwLoop.loop`)是唯一循环;画面访问在以下动作/分支处结束、控制权交回外循环(`flow/screen_op.md` §3 终结 op 集;恒可用终结不变量 = 决策 6):

| 终结动作/条件 | 终结级别 | 语义 |
|---|---|---|
| 商店 RefreshShop | **段终结** | 刷新是唯一引入新事实的动作(新牌面),执行即本段 break;下一段入口观察重建期望态。visit 级刷新硬墙 = `cw_screen_buy_cards.py::MAX_REFRESH`(超墙终结集降级仅关店,`shop_visit.md` §3) |
| 商店 CloseShop | **访问终结** | 恒可用终结 op(全函数「无动作可做」的表达);关店点击由编排壳 CwOpCloseShop 执行,节点探针收尾后交回外循环 |
| 商店 CompTransaction | 终结邻接 fallback | 执行后本画面访问结束交回外循环重观察(合成建模 fallback 语义,禁半档中间态) |
| 商店全 unknown 失读窗 | 收工终结 | 牌面含 unknown 槽 → 花钱动作禁发射,仅 CloseShop 收工;未识别卡停机钩子留证(`shop_visit.md` §3) |
| 备战 StartBattle | **访问终结(唯一完成态)** | 出战落地 → 外循环置战斗窗口(备战→战斗→结算→回备战轮推进,`outer_loop.md` §4) |
| 备战 OpenShop | 备战环终结 | 交商店访问编排(显式开店)或回外循环重识别(读数开店) |
| 备战 BailToOuter / overlay 检出 | 环中止 | 弹层/事件在场 → 交回外循环分支 handler(如盛会之星/事件 overlay) |
| 备战空批(无动作) | 合法交回 | 空序列合法 = 本帧无动作,交回外循环重观察(商店域无此通道,已被 CloseShop 终结取代) |
| 备战未建模投影面动作 | 保守回退终结 | DeployMove/SellDeployed/LevelUp/RunDeploy/RunEquip 等投影未建模面执行后本访问终结交回外循环重观察(重观察语境禁猜,`prep_visit.md` §1) |
| 单选族确认离开 | 画面终结 | overlay 消失即节点完成(补给节点无结算屏,合成 outcome 行,0e1) |
| 推进型画面(简报/过渡/详情/弹窗族) | 画面终结 | 点推进/关闭即终结(空决策形态) |
| 恢复局锁定态 | 例外约束 | 进过战斗后异常重启的恢复局,商店交互被游戏禁用(只能出战;`research/economy.md` §2.1 恢复态限制),外循环锁定态直通出战(`operations/cw_loop.py::locked_resume_sync_and_battle`) |

## 5. 判例载明与边界

- **判例(用户裁定 2026-09-14)**:卖备战/买经验是商店开画面**可用**动作(SellBenchOp/LevelUpOp 在商店 op 表在役,机制路径已验证),但默认策略**不在商店期做**——策略面收缩至备战期(商店期 = 买牌/刷新/关商店;席满腾位链 = 关商店→备战期卖→重开商店,节点内关店/重开不刷新牌面、牌面持久,节点切换才自动刷新,`research/economy.md` §2.1)。能力矩阵按能力面记:七动作族、商店 op 表、容器转移函数全保留;策略归属 = [23_shop_screen.md](../strategy-docs/23_shop_screen.md)(商店期动作面)与 [22_prep_screen.md](../strategy-docs/22_prep_screen.md)(备战期接收面)。
- **商店锁**:游戏机制存在(整店级,`research/economy.md` §2.1),建档已有按钮坐标,生产链路未建模(无识别/无动作)——能力面登记为「存在但未接线」。
- **SwapDeploy**:词表/容器投影/sim 消费在役,生产执行器未接线(备战域部署换位经部署机拖拽承载)——能力面按词表完备性保留。
- **刷新不换牌面的场景**:节点内关店→重开不刷新(牌面持久);跨节点自动刷新全店(不继承)。判「是否刷新」以节点推进事件为锚(`research/economy.md` §2.1)。
