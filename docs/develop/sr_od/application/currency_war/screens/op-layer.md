# 画面 op 层设计(op-layer · 行为规范 + 上报接口 + 形态分型 + 观察解析工具箱)

> 本文 = 画面 op 层唯一设计正本:**§1 行为规范**(每个画面 op 必须表现成什么样,合同)、**§2 上报接口**(观察数据怎么进容器)、**§3 形态分型**(37 画面 op 的形态分类)、**§4 辖域边界**(本层不承载的机制)、**§5 观察解析工具箱**(obs/ 地图)、**§6 流程转点观测锚**(在库机制)。各画面的具体文档 = 同目录各篇(一画面一文档,索引 = [README.md](README.md))。代码锚 = `文件::符号名`(路径根 = `src/sr_od/application/currency_war/`)。
> 术语:**逻辑态** = 动作执行后不经观察、按游戏规则推算并直写容器的预期状态;真值以下一帧观察为准(观察赢)。**obs** = 一个画面一次观察的结果对象(类型化载荷);**report** = 该画面在 kernel 侧的上报函数,把 obs 写进容器。**GameState/记录模型** 字段级正本 = [../game_state/fields.md](../game_state/fields.md)——记录模型管「记什么」,本文管「谁在什么时机喂进去、决策怎么消费、动作怎么落回」;冲突以字段正本为准。

## §1 行为规范

### 1.1 总则:每个画面 op = 两个 node(观察 → 决策动作),直继承 SrOperation

画面 op 不设共享基类:每个画面一个独立类直继承框架 `SrOperation`,类内声明两个 node。

```
画面 op 入口
  ├─ 观察 node(is_start_node):
  │    门(画面身份/节点完成判定;身份门 miss = round_fail 交回外循环重判,
  │        完成门 miss = 画面已离开,round_success 交回)
  │    → 显式读屏(本 op 唯一读屏点)→ 组装 CwScreenXxxObs
  │    → report_screen_xxx_obs(gs, obs) 落容器(match/gs 缺席的局外兜底路径跳过)
  │    → obs 挂实例属性,round_success 进决策动作 node
  └─ 决策动作 node:
       重入裁决(顶部;上轮动作已发 → 锚不在 = 已落地 → 补记录 + success 交回)
       → 决策(从容器零参读;恰一个动作;备战空发射 = CwActionObsParam
         scope='outer_loop' 合法交回——原 HoldFrame 收编,用户裁定 2026-09-20;
         备战域发射决策 = mandate_v1 前置发射位(`bridge._launch_front_check`,
         `decide_prep_screen` 入口消费),armed 帧短路三遍编排直接产
         受限商店访问/出战意图——决策面在策略器,CwScreenPrep 决策段
         消费意图落执行)
       → 动作(经动作 op 机械执行;动作 op 自上报推进逻辑态,零读屏)
       → round_wait 循环推进(node runner 每轮给新帧)
```

- **两 node 职责**:观察 node = 门 + 读屏 + 观察结果上报,无循环、小预算;决策动作 node = 重入裁决 + 决策 + 动作,迭代一律 `round_wait`(不烧 node 重试预算)。act node 保留现役 `node_max_retry_times` 值(仅框架异常路径消费,不新建上限机制)。
- **循环无上限规范(用户裁定)**:框架不负责多轮循环的上限限制——决策动作 node 的循环与外循环轮次推进均不设迭代数上限(无防御帽、无兜底计数,健康循环永不因计数被截断);不收敛/死循环 = **策略实现 bug**,响亮暴露(挂起可观测),修策略根因。失败类出口(异常 fail、外循环 fail 熔断、未知画面兜底)不属于迭代上限。循环兜底不变量 = 1.4 恒可用终结。
- **出口三语义**:决策动作 node 的循环只有三种出口——①**终结动作**(1.4,执行即本访问结束交回外循环);②**重入裁决成功**(动作已落地,补记录后交回);③**异常 fail**(策略异常/执行异常,错误传播交外循环,非防御上限)。备战域另有合法交回通道:策略器返回 `CwActionObsParam(scope='outer_loop')`(本帧无动作,交回外循环重观察;原 HoldFrame 收编,`kernel/cw_vocab.py::CwActionObsParam`)= round_success 交回外循环,不折算战替身;策略发射 `CwActionObsParam(scope='in_place')` 环内重观察见事件 overlay = `CwObsOverlayBail`(动作 op 抛出,决策循环捕获)交回外循环重分发(画面路由归外循环,环内不消化)。
- **重入裁决留在决策动作 node 顶部**:「确认已发 → 下一轮锚不在 = 落地」是动作落地裁决,属循环出口判定,不回观察 node。chosen_* 类落地记录在此刻写(见 §2 动作事实边界)。
- **显式读屏只在观察 node**:决策动作 node 迭代用 node runner 进 node 时给的 `last_screenshot`(`round_wait` 每轮新帧)。除观察 node 外,画面 op 内不调 `screenshot()`。**在册例外(动作通道)**:策略显式发射 `CwActionObsParam(scope='in_place')`(环内重观察)= 经注册表派发 `CwActionObsOp` → 宿主画面 op `reobserve_in_visit`(现役 = `CwScreenPrep`)重跑 heavy 观察链——漏斗直写容器即「重新观察上报」,决策环原地续跑;该通道是唯一的决策循环内读屏点,其余路径仍零读屏(通道细则 = [../flow/action_exec.md](../flow/action_exec.md) §3)。
- **外循环形态不变**:画面识别分发、轮次推进、停机/遥测钩子([../flow/outer_loop.md](../flow/outer_loop.md))不随本规范改动。

### 1.2 动作 op 契约与动作粒度

- **动作 op 形态** = `CwActionXxxOp`(框架 `SrOperation` 子类,构造 = `(ctx, param, env)`):机械执行后直调自己的上报函数(`kernel/cw_action_report/report_action_<snake>_param`),逻辑态由上报函数族独占写入,动作 op 自身不记账。发出即职责完成,落地判定归观察侧;执行异常上抛。**验证不是生命周期段**:动作 op 只管机械执行,禁做任何验证、禁设「验证失败→重试/恢复」编排;动作未生效(观察正确而下一帧对账失配)的处置 = 修动作执行链本身的可靠性(点击链坐标/时序/确认序列),禁止以验证+重试结构兜底。
- **动作粒度**:买一张 = 一个 op、卖一张 = 一个 op、买经验一击 = 一个 op(单击 +4XP;升级 = XP 过门槛表结果,非动作)、刷新 = 一个 op。**满栏例外**:板凳满时点合成槽位,游戏机制自动多买至 3 的倍数张(每张原价)——一击多张 = 一个动作 op,逻辑态直写按实际张数计。复合宏动作(整档替换)已全链退役。

### 1.3 守卫断言与对账边界

- **合法性判定全部内化于策略器**(提议侧约束);执行侧只余**守卫断言**——防 bug 路栏而非控制流分支,非法返回 = 策略器 bug 响亮暴露(禁静默跳过或降级续跑)。现役守卫 = `operations/cw_op/cw_shop_action_ops.py::guard_proposal_vs_expected`(提案对象在期望态存在且未被消费——防策略器算术 bug,恒炸)。守卫零读屏。op 框架既有的重试/等待语义属 execute 执行实现层,不算第二道合法性门。
- **对账唯一发生点 = 观察边界(硬规则)**:对账 = 观察 vs 逻辑的双态比对,唯一合法时点 = **观察数据经 report 进入 game state 的观察边界**(画面 op 观察 node / 动作自上报后的下一观察帧),由 game state 执行比对与仲裁(`kernel/cw_reconcile.py`;锚定机制属 game state 层内部实现);**其余任何状态/op 层不做双态比对,也不做店内原地重建**——动作级「发射即登记 + 下一帧对账」不属于双态比对(归观察侧闭环)。**摄入逻辑住屏文件**:该画面观察进容器的全部逻辑(写点/屏级门/派生/对账特判)住 kernel 屏文件(§2),op 层只组装 obs 并调用 report;依赖读帧的观察审计链(如备战羁绊显示核对)不迁 kernel,留守画面 op 观察 node(§2 辖域边界)。

### 1.4 终结动作集与期望态生命周期

- **终结动作是一等动作**(策略器主动选择,不是循环逃生口);执行即画面 op 结束、交回外循环。**恒可用终结不变量**:每个决策画面的动作空间至少含一个恒可用终结动作(商店 = 关店、备战 = 开战、单选族 = 确认、等待/切换类 = 推进)。**刷新 = 终结的语义自洽**:刷新是唯一引入新事实的动作(新牌面),期望态必须在新事实处重建。终结判定现值 = 注册表 op 类 `terminal`/`terminal_wait` 属性,消费点经 `action_op_class_for` 读取(禁消费点私表);终结集总表 = [README.md](README.md) §6。
- **期望态生命周期**:入口观察(重建,即对账)→ 逐动作逻辑态直写(经动作自上报函数族,零读屏)→ 终结(失效,交回外循环下次重建)。逐动作转移函数腿规格 = [../game_state/logic-updates/](../game_state/logic-updates/README.md)(词表逐动作有逻辑态分支;词表外 = AssertionError 响亮暴露)。
- **字段未观察态**:tracked 账字段取值域含**「未观察」态**——无任何观察锚定,值不可消费;与「已观察下的空」类型可分。进入 = 显式失效事件;退出 = 入口观察对账的屏幕真值写回。策略消费口唯一 = game state。策略默认实现 = 商店开遇未观察 → 返回关店 → 外循环重判落回备战 → 入口观察锚定后再进店;未观察跳过的访问留遥测分键,连续循环 = 锚定失败显式失败出口,禁静默重试。
- **读屏点**:显式读屏只在画面 op 的观察 node;终结交回后外循环重分发,下一次访问的观察 node 即下一次读屏。

### 1.5 形态判据

- 画面 op 按观察/决策/上报三面的有无分型(全形态/节点循环/推进型空决策/驻留状态机/重型屏),判据与 37 屏分类总表 = §3。

## §2 上报接口(kernel/cw_screen_report/)

### 2.1 包形态

- **每画面一文件**:obs 类与该画面上报函数同居(`kernel/cw_screen_report/<画面snake>.py`);与动作侧 `kernel/cw_action_report/<action>.py` 每动作一文件对称。文件名 = 画面 snake;`__init__.py` 不暴露模块(项目惯例),消费方按画面文件名直接 import。
- **命名机械规约**:obs 类 = `CwScreenXxxObs`(商店框 op = `CwOpXxxObs`);上报函数 = `report_screen_<snake>_obs`(obs 类去前缀 `CwScreen` 去后缀 `Obs` 转 snake)。与动作上报函数族同约定:**一个「上报」概念一个形状**,动作/画面观察两族互不混用,都禁按类型聚合的分派转移函数。完备锁测试遍历包内 obs 类,断言 report 函数在场/不在场分侧(推进型不在场)。
- **obs 类**:该画面一次观察的类型化载荷,字段 = 该屏读到的结构化结果 + 稳定帧引用(`screen: Any`,实机识别域载体)。纯数据:只可 import kernel 既有类型 + `cv2.typing.MatLike`。
- **sig 逐位沿原值**:上报函数的 `ChannelSig`(family/actor/evidence)沿用该画面原写点原值(如 actor='CwScreenEncounter');journal 写行语义与迁出前连续。sig 缺省 = 函数体内按原值构造;对 obs 字段缺失的防御口径与原写点一致(读缺 = 跳过写,不加强不减弱)。

### 2.2 辖域边界

- **屏文件 = 该画面观察进容器的全部逻辑的家**:①写点(类型化 obs 载荷 → 容器字段,含屏级幂等门/懒写/恒覆写等写法);②该屏更新逻辑(写点之上的派生/优先级);③该屏对账特判(只在类型化 obs 载荷上运算的观察 vs 逻辑态比对)。**判断线(按角色分流):类型化 obs 载荷的生产半(识别 + 标准化转换,含跨帧读数稳定化、读数有效性门)住观察侧(画面 op 观察 node 或 obs/ 工具箱);落容器半(写点/屏级写门/写点之上的派生/观察 vs 逻辑对账特判)进 kernel 屏文件,恒只在类型化载荷上运算**——识别机制不出观察域,kernel 零像素纪律不破;kernel→obs 直依被分包矩阵禁止,观察侧纯函数以「函数体搬进」kernel 屏文件的方式落地,不是 import。
- **漏斗边界**:`obs/cw_observation.py::read_game_state` 漏斗内部的容器写端 = 既有观察边界,不经 report 接口、不重复承接(备战/买牌的整包观察直写容器,report 相应保持占位或不设摄入面)。
- **动作事实边界(硬规则)**:chosen_*(选择落地记录)与 per-visit 位(如 `encounter_refreshed_in_visit`)留守画面 op——其值在「确认已落地」重入观察后才可信,记账随判定点走(重入裁决点/选择点),不进 report。
- **刷新计数出辖**:节点屏刷新计数(`encounter_refresh_used`/`strategy_refresh_used`)的写端不在画面 op 层(见 §4),`refresh_left` 观察读数只是 obs 字段。

## §3 形态分型(37 画面 op)

画面 op 共 36 个:`operations/cw_screen/` 34 类 + 商店框 2 类(`operations/cw_op/cw_op_open_shop.py::CwOpOpenShop`/`cw_op_close_shop.py::CwOpCloseShop`)。分五型:

| 型 | 判据 | 屏清单 | report |
|---|---|---|---|
| **全形态** | 观察 node + 决策动作 node + report;决策动作 node 承载完整决策循环(重入裁决/分支刷新/确认链) | CwScreenEncounter(专用刷新链保留)、CwScreenSupplyNode、CwScreenInvestStrategy、CwScreenInvestEnv、CwScreenBriefing、CwScreenBossBriefing、CwScreenWaitOneOne、CwScreenDeployNotFull、CwScreenPlaneTransition(链观察)、CwScreenPlaneIntel、CwScreenBoxPick、CwScreenArmoryBox | 12 屏全设;其中 BossBriefing/WaitOneOne/DeployNotFull/PlaneIntel/ArmoryBox 现役零容器摄入面,接口为统一形态占位 |
| **节点循环** | overlay 单选族:两 node,决策动作 node = 零参决策 + 选卡确认链派发(`CwActionPickXxxOp` 经注册表,机械链在动作 op 内,pick-op-unify 批)`round_wait` 循环 | CwScreenMegastar(轻门 + 懒读先例:确认访问不重读候选;选中半迁入动作 op)、CwScreenEquipPick、CwScreenPartner、CwScreenYinLang、CwScreenFortune、CwScreenWishTrial、CwScreenBookcard、CwScreenExpertInvite | 8 屏全设(候选写 `*_opts` 槽) |
| **推进型空决策** | 无选择面无容器域:观察 node = 门判定;决策动作 node = 单步推进 + 重入裁决;**无 report 接口** | CwScreenNextButton、CwScreenPlaneDetail、CwScreenConsumableOverlay、CwScreenEmblemDetailPopup、CwScreenItemDetailPopup、CwScreenInterruptDialog、CwScreenRefreshOddsPopup、CwScreenRoleDetailOverlay、CwScreenShopCardDetail、CwScreenPrepLockedReturn、CwScreenAhaEquipPick(11)+ CwOpOpenShop/CwOpCloseShop(商店框,推进型只读/导航变体) | 无(obs 类只记入口裁决;完备锁断言函数不在场) |
| **驻留状态机**(用户裁定豁免两 node) | 内部 while 处理结算帧、逐轮分类;出口判定(大厅终局锚/完成白名单)与分支链的轮次耦合拆进两 node 会切开 | CwScreenBattleWait(单 node `wait()`;内部结算链 `_write_settlement_observation`/`apply_settlement_cover`/SettlementState 零改动) | report 占位(结算覆盖写端在结算域,非画面观察记账) |
| **重型屏** | 观察 = 既有漏斗 + op 层散落写点收编;决策动作 = 无帽循环/波循环 | CwScreenPrep(观察 node = 环装配 + heavy 观察 + 接管补采 + 纯观察审计留守;决策动作 node = 单动作决策 `while True` 循环,无防御上限;可选域经 report 落容器)、CwScreenBuyCards(观察 node = 入口段 `_shop_entry_read` 含未识别卡停机闸;决策动作 node = 波循环 `run_buy_waves` 内聚状态机,首段复用观察回执不重读) | prep = 可选域(链域/接管域)report;buy_cards = report 占位(容器写端在漏斗) |

退役 1:`CwScreenDeploy`(部署机画面 op)已退役删除——部署 = 备战决策环动作(`CwActionDeployMoveParam` 原子序经 `CwActionDeployMoveOp` 机械执行 + `report_action_deploy_move_param` 自上报逻辑态),部署判定单一源驻 `kernel/cw_deploy_logic.py`,路径速查 = [deploy.md](deploy.md)。合计 12 + 8 + 13 + 1 + 2 = 36。

注(pick-op-unify 批):单选族 13 屏的选卡动作全集收编为 12 个 pick 动作 op(投资两屏共用 `CwActionPickInvestParam` 行,全节点循环/全形态单选屏经注册表派发),op 内 = 选中 → 确认(或点卡即选)→ 自上报(零写);刷新链(遭遇/补给/投资两屏)留守画面 op。

## §4 辖域边界(本层不承载的机制)

- **画面 op 基类/端口/段迹/登记注册表/决策帧假环境分支不存在**:画面 op 层无五段生命周期基类、无观察/动作适配器端口与装配点分流、无生命周期段迹、无 on_outcome 落地登记注册表、无决策帧观察证据注入分支——上述机制整体退役,任何一侧的重新出现即架构回潮。观察/决策两段职责由两 node 直接承载(§1),观察进容器由 report 接口承载(§2)。
- **刷新计数记账不在画面 op 层**:`encounter_refresh_used`/`strategy_refresh_used` 的写端模型与「动作上报 → game state 扣减」改造归动作 op 侧;画面 op 只保留 `refresh_left` 观察读数(obs 字段)与门读容器计数的读端闸(>0 = 已用),不写计数。
- **观察审计链留守**:依赖读帧的观察审计(备战羁绊显示对账、刷新留证)住画面 op 观察 node,消费 obs/ 工具箱识别产物;不迁 kernel、不进 report。
- **策略判据面不在本层**:买/卖/升/刷数学归策略器(策略文档区);画面 op 只做容器零参读 + 动作编排放大。

## §5 观察解析工具箱(obs/)

一屏一解析器;识别机制不出观察域(§2 辖域边界),解析器只回答「读到什么/可不可信」。清单(符号 = `obs/<模块>::符号`):

| 模块 | 管什么 |
|---|---|
| `cw_observation.py` | 备战屏观测主漏斗:`read_game_state` 容器直写 + 轻量回执(观察流/PHASE_FIELD_SPEC 逐字段门) |
| `cw_observe_full.py` | heavy 全面识别组装层(备战入口单次;装备域三路) |
| `cw_identity_obs.py` | 备战屏视觉身份观测(SIFT,非 OCR;bench/deployed 槽位身份) |
| `currency_war_char_id.py` | 角色识别 SIFT 模板匹配(生产用立绘模板库) |
| `currency_war_cv.py` | 备战阶段传统 CV 检测工具 |
| `cw_faction_obs.py` | 羁绊面板显示侧识别 + 与计算侧羁绊计数对账 |
| `cw_back_layout.py` | 后排槽位布局(公式 + CV 实测双通道对账) |
| `cw_equipment.py` | 装备视觉识别(手维护) |
| `cw_node_obs.py` | 节点选项观测(遭遇/补给/巨星/伙伴 → 类型化 Option) |
| `cw_node_reader.py` | 节点行类型识别(纯 CV;`read_node_sequence` 包装接入) |
| `cw_briefing_obs.py` | 简报屏观测(敌人词缀 + 位面首领) |
| `cw_settlement_obs.py` | 结算屏观测(战后小队 HP) |
| `cw_shop_refresh_obs.py` | 商店刷新钮标价/按钮态现场 OCR |
| `cw_arbitration.py` | 观察层读数多源仲裁统一注册面 |
| `cw_resume_lock.py` | 恢复局(locked-resume)检测纯函数 |
| `cw_anchor.py` | 流程转点观测锚机制(ANCHOR_REGISTRY/AnchorSpec/emit_anchor;见 §6) |

**类型化载荷出料**:`kernel/cw_screen_report/` 包 = 各画面 obs 类 + `report_screen_<snake>_obs` 上报函数同居处(§2;每画面一文件,与动作侧 `kernel/cw_action_report/` 对称)——obs/ 解析器产读数,kernel 屏文件承载「读数 → 容器」的落写语义。

## §6 流程转点观测锚(机制在库,接线候批)

- **锚** = 在流程确定性转点上触发的一次结构化观测,三要素 = 确定性触发时点 × 该时点权威事实集 × 落载体登记;是画面/动作上报面族的观测扩员,不是新机制。目的 = 让框架提供更准确的游戏观察数据(事件事实零读屏即确定;事后从散点帧推断是多次实证的缺陷类)。**观测-only 边界**:只做记录面,状态改写/效果施加出栈(payload 预留 effect_ref 槽位恒空,非空 = 红)。
- **触发三型**:landed(动作落地事实,如买牌落地 = 卡名/扣金/合成判定三事实同点唯一可得处)/ emitted(发射即登记,如遭遇·策略刷新计数)/ boundary(流程边界:进节点/进位面/结算)。锚点事件集 = 登记式封闭集(`kernel/cw_anchor.py::ANCHOR_REGISTRY`,现役闭集 8 锚;新锚先登记再接线,集外 = 红);**现役零生产调用点**(惰性纯机制面),动作锚接线随执行器收编批、boundary 触发口候裁决,禁实现批静默选型。
- **锚行封装**:anchor_id/trigger_type/时点键/payload/scope(口径域:global|plane|unit,防跨批口径混用)/evidence_refs(判定事实型必填)/produced_by。载体三面全部复用既有设施:事件行 = ExogenousEvent kind 词表扩展(schema 修订归一个批次,防逐锚散改)、状态锚 = GameState 既有写入 API(source 标注 `anchor:<id>`)、计数 = 效果账本既有挂点。
- **防双源声明**:锚是上报接口面的登记清单面,非平行触发机制;与采集钩子(临时采样)辖域互补禁混同;与停机钩子无交(锚永不触碰 run 状态);帧观察 → 锚 → 遥测落盘是一条管道的三段,锚不产生独立数据域。节点推进权威 = 统一 state 派生规则,锚行禁携带第二份节点序计数。
