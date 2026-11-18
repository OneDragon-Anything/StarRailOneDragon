# 策略↔流程契约与状态分离(strategy-contract)

> 路径根 = `src/sr_od/application/currency_war/`;代码定位一律用 `文件::符号名`。
> 职责分界(用户裁定):**策略文档只管「每个画面结合哪些数学证明、怎么产出决策」(`docs/develop/sr_od/application/currency_war/strategy-docs/`);流程控制单独立文档(本篇)**——画面识别与路由、访问相位推进、动作发出契约、守卫与停机。

## 1. 四身份分离

| 身份 | 载体 | 职责 | 禁止 |
|---|---|---|---|
| **契约** | `strategies/impl/cw_strategy.py` 的 `CwStrategy` ABC(抽象 16 + 非 abstract 工厂 1) | 定义各画面 op 调用策略器的全部决策入口与唯一的每局新建入口 | ABC 自身零内置逻辑(纯接口,create_state 工厂除外);零策略专属语义 |
| **管理器** | `strategies/impl/cw_strategy_manager.py`(StrategyManager) | 按实例化/选择策略;注册面封闭集 = {mandate_v1} | 不承载判据;不知策略内部结构 |
| **实现** | `strategies/impl/mandate_v1/`(单一核)+ `strategies/impl/flow.py`(`CwFlowStrategy` 中间辅助 ABC:唯一的每局新建入口/pick 族/商店单动作接口与驱动器缺省,`_abstract=True` 不注册) | 决策本体 | 禁自实现生命周期机制(幂等键/连败恢复/屏蔽/stall 门——归流程侧);禁绕契约自造接口 |
| **注册壳** | `strategies/mandate_v1_strategy.py`(MandateV1Live) | 把实现包注册进策略扫描器 | 壳内零判据逻辑 |

## 2. 契约接口全景(形状;17 = 每局全新创建口 2 + 分画面决策入口 15)

**每局全新创建口 2**(实现 = `flow.py`):

| 接口 | 调用时机(流程侧) | 语义 |
|---|---|---|
| `create_session(config)` [abstract] | 每局开始一次(establish_new_match/防御路径/回放三处同源) | 返回空白 StrategySession + 策略器状态工厂接入调用 + live 初值——**唯一的每局新建入口** |
| `create_state(config)` [非 abstract 工厂] | 仅由 create_session 接入调用 | 每局新建策略器状态对象(黑盒契约;缺省 None = 第三方插件兼容条款——新增 abstract 钩子会破坏存量第三方策略;config 可忽略、可为 None) |

**分画面决策入口 15**(抽象;终局意向重估由各入口经帧代次标注内化触发):

| 接口 | 输入 | 返回 | 语义 |
|---|---|---|---|
| decide_prep_screen(session, config) | 状态容器 game state 直读 | **恰一个动作**(CwAction),None 停用;重观察动作 = CwActionObsParam 两口径 | 本帧无动作是合法通道;策略器异常/非法形状由消费端守卫拒绝(决策循环 try/except:异常→本轮 fail 交外循环 retry 链;非 CwAction 返回→具名 fail 保留证据) |
| `decide_shop_action(session, config)` | **终态零参口**:决策输入 = 状态容器单例 `game_state_of(session)` | **恰一个动作**,「无动作可做」= `CloseShop` 恒可用终结 | 决策本体 = `mandate_v1/shop.py`;状态容器 shop payload 离屏 = 观察层失约抛错 |
| `decide_invest_env`/`decide_invest_strategy`/`decide_supply`/`decide_encounter`/`decide_megastar`/`decide_partner`/`decide_planner`/`decide_star_tome`/`decide_wish_trial`/`decide_box_card`/`decide_fortune`/`decide_expert_invite`(pick 族 12) | 状态容器槽零参读(候选自各 `*_opts` 槽/payload 槽;离屏 None = 观察层失约抛错) | 恰一个动作:选卡 `CwActionPickXxxParam` ∨ 刷新建议动作,互斥单发 | 选项决策;动作编排归画面 op。决策规格 = strategy-docs/13_pick_family.md |

**非契约成员(实现层)**:

- `decide_shop_screen`(flow 层缺省驱动器 + bridge 覆写)——**序列兼容驱动器**:逐帧调 `decide_shop_action` + 逐动作直调上报函数推进期望态,终结动作截停;回放/既有序列测试消费;生产执行侧不走(单动作循环),sim 亦不走。
- `_refresh_direction`/`_refresh_direction_views`(flow 层私有)——**方向节拍内化**(方向节拍 = 每游戏轮只做一次的贵段):用两个标记槽记录最近一次备战/商店观察是新是旧(`gs.frame_class_prep`/`gs.frame_class_shop` ∈ full/view/none),决策入口据此每游戏轮只做一次贵段;标记读完即清,只有观察装配点和决策环能写。
- `write_shop_mirrors`(遥测镜像写者)。

**生命周期机制归流程侧**:幂等键 `action_key`、stall 门、强制出战。新事件面优先归并进既有 pick 接口或走契约改版,禁旁路自造接口。

## 3. 装配与依赖

- **依赖方向**:实现包 → 知识层/数学层/执行层单向;分包依赖矩阵禁 decision→obs 直依(obs 读口经 app 层装配点 `install_obs_ports()` 注入);决策本体 = 纯函数。
- **决策 hp 读口与可信位**:统一读口 = `kernel/cw_hp_policy.py::decision_hp`(gs.hp 直读);可信位另经 `hp_decision_trusted_of`(`gs.hp.source ∈ {observation, carried}`,prior/logic fail-closed——信息缺失时宁可判不可信,不猜值);hp 不入其余任何策略判据,新增 hp 决策消费点必经读口或登记豁免。
- **sim 消费面**:sim = 游戏后端(驱动反转——真流程当驱动者,状态副本在后端):四层全图装上后端即在 sim 状态副本跑一局,**全决策面 sim 可达**;批量运行与 A/B 不在 sim 本体内(边界 = sim/sim-design.md §8.3);校准缺口的判读限制 = sim-design §8.2 申报清单。
- **换核与 A/B**:注册面封闭集 = {mandate_v1};换核机制 = config 切 `strategy_id`(最小面),不改流程侧分发。归因域限定:结论外推限制由保真度分层承载——sim-design §8.2 申报面上的读数不得作策略效应证据,真代码层/机制层读数可外推。

## 4. 状态分离契约(session / 策略器状态 / GameState)

> 来源裁定(用户):session 的本义 = 只承载「从游戏画面观察到的数据」(框架采集与更新的职责);策略需要的中间状态、临时变量、推导状态都是**策略器的内容**——策略器一局内存活、自己持有;执行层状态归画面 op/执行层(现行已并入 GameState 状态容器)。

**现行结构**:

- **StrategySession**(`kernel/cw_strategy_session.py`)= 一局跨步状态载体,只含:观察数据(框架从游戏画面采集/推导的对局事实:血量/金币/牌面/板凳/等级/连胜/节点类型/词缀/池状态/已持投资策略等)+ 框架设施(rng 种子契约基准/performance 观测反馈跟踪器)+ `strategy_state` 黑盒引用。
- **策略器状态** = 实现包私有 `StrategyState`(mandate_v1 的 MandateState),经 `CwStrategy.create_state` 工厂每局全新创建、挂 `session.strategy_state` 黑盒引用,框架只搬运引用,不读不写其内部——所有权归策略器,生命周期管理(每局新建、局终随 session 销毁)归框架。执行层需要读写策略器状态时,一律经 kernel `strategy_state_of`(None-safe,状态缺席不新建)——禁 impl 侧 `state_of` 从执行层调用。
- **GameState 状态容器** = 局内事实独占承载(设计权威版本 = `docs/develop/sr_od/application/currency_war/game_state/README.md` + fields.md)——含 Field 域与非 Field 簿记;执行层状态类目已停用(局内事实不再设旁表状态载体)。
- **坐标伴随域(用户裁定:gs 给实体记录坐标)**:凡观察域识别的「可选/可交互实体」(选项卡/备战栏/装备栏/晶矿/浮层按钮),状态容器除语义事实 Field 外,同源记录**坐标伴随字段**(命名 `<实体>_xy` 或条目内 cx/cy)。写端 = 观察上报单点整表覆盖(随帧刷新),**禁逻辑写端**——动作后回填坐标无画面读数,坐标缺席语义 = 策略产参跳过自愈、下帧观察重派,禁回填猜值。用途 = 动作原语参数面③类(动态坐标显式传参,SKILL.md §1.4)的数据源:策略层产动作参数时从伴随域取坐标,动作 op 零内部识别——与动作域「坐标按下标取自状态容器」既有裁定同族,由 pick 族推广到全部视觉定位实体。逐字段登记随实现落 fields.md(先例 = owned_equip_xy)。
- 异常路径残留状态容器由 `discard_stale_match_container` 在「确凿新局」信号点丢弃。

**三裁决**:

1. **载体形态 = 黑盒状态对象挂 session,所有权归策略器**:框架只搬运引用不识内部结构;kernel 判据层对策略状态的消费经**访问函数**(取 `session.strategy_state` 后类型收窄);**遥测可见性完全依赖访问函数抽读链——任何新遥测字段必须从访问函数出发,禁直读 session 猜字段**。
2. **恢复局语义 = 策略器状态保守冷启动**:恢复局(server 重启后接管残局)下,session 观察数据由入口观察全量重建,策略器状态**不可重建、不尝试重建**——以空状态冷启动,凭当帧观察数据重新驱动意向状态机。丢失语义:意向状态机从未锁定态重驱动(可能锁到与重启前不同的线,决策仍自洽);纯限制器计数归零 = 「未发生过」;同轮已卖集丢失 = 守卫失效窗口与先卖后买回的缩幅循环风险(下个入口重估自愈);遥测分键局终快照只含恢复后增量。
3. **热替换面 = 局边界丢弃冷启**:换策略实现(切 strategy_id)只允许发生在**局边界**;替换时旧状态对象整体丢弃、新实现的状态对象由其工厂每局全新创建——状态类型是各实现包私有,跨实现的状态迁移**不定义**。

**第三方插件兼容条款**:`create_state` 定义为 ABC 非 abstract 钩子,基类缺省实现返回 None——存量第三方策略零破坏(「零破坏」= 缺省 None 不会让策略构造与 create_session 报错);不承诺框架行为面读点容忍 None——未覆写且无工厂注册时状态恒 None,进入行为面读点 = AttributeError 显式报错(mis-assembly 信号,优于静默产 None 假数据)。
