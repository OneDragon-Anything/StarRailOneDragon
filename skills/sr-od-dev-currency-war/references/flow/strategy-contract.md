# 策略器契约(strategy-contract)

> 路径根 = `src/sr_od/application/currency_war/`;代码定位一律用 `文件::符号名`。
> 职责分界:策略文档只管「每个画面结合哪些数学证明、怎么产出决策」(`docs/develop/sr_od/application/currency_war/strategy-docs/`);流程控制单独立文档(本篇)——画面识别与路由、访问相位推进、动作发出契约、守卫与停机。

**策略器 = 决定「此刻做什么动作」的大脑。**画面 op 的策略器处理段(四段规范第 4 段,见 [screen-op.md](screen-op.md))按当前画面调用它对应的决策接口:策略器自己从状态容器读观察事实,返回恰一个动作,画面 op 把动作交给动作 op 执行。策略器不碰屏幕、不管流程编排、不执行动作、不持有跨局状态;决策所需的中间变量一律收拢在自己的实现包私有状态里(§4),不放状态容器。

## 1. 一次决策怎么发生

画面 op 策略器 node 循环,每帧:

1. 按当前画面调对应决策接口(备战 = `decide_prep_screen`,商店 = `decide_shop_action`,选卡屏 = pick 族对应接口,全清单见 §3);
2. 策略器读状态容器——**接口输入零参数**:观察事实全在状态容器里,不传帧数据;
3. 返回**恰一个动作**(CwAction),**无 None**——本帧无动作 = 发 `Obs(scope='outer_loop')`(空动作并入词表,承载「结束本次访问返回主循环重判」语义);
4. 画面 op 把动作交动作 op 机械执行(零读屏);
5. 终结动作结束本次访问返回主循环;非终结动作 round_wait 进下一帧。

策略器异常/非法返回由消费端(画面 op 的决策循环)守卫拒绝:异常 → 本轮 fail 交外循环 retry 链;非 CwAction 返回 → 具名 fail 保留证据。

## 2. 类结构:四个类各干什么

| 类(身份) | 干什么 | 禁什么 |
|---|---|---|
| `CwStrategy`(`strategies/impl/cw_strategy.py`,接口定义) | 定义全部决策入口的抽象签名(零参决策入口 14,§3.2);构造注入 + 自动决策记录 | ABC 自身零内置逻辑(纯接口,_create_state 钩子除外);零策略专属语义 |
| `StrategyManager`(`strategies/impl/cw_strategy_manager.py`,选策略) | 按实例化/配置选择策略;注册面封闭集 = {mandate_v1} | 不承载判据;不知策略内部结构 |
| mandate_v1(`strategies/impl/mandate_v1/`,决策本体) | 现役唯一实现;`flow.py::CwFlowStrategy` 为中间辅助 ABC,承载每局创建/pick 族/商店单动作接口的缺省实现(`_abstract=True` 不注册) | 禁自实现生命周期机制(幂等键/连败恢复/屏蔽/stall 门——归流程侧);禁绕契约自造接口 |
| `MandateV1Live`(`strategies/mandate_v1_strategy.py`,注册壳) | 把实现包注册进策略扫描器 | 壳内零判据逻辑 |

## 3. 接口清单

### 3.1 构造注入(唯一的每局全新创建入口)

每局开始由引导漏斗 `cls(gs, config)` 全新构造策略器实例,实例不跨局(match 对象弃置 = 实例连带回收;异常路径残留 match 的弃置守卫 = `discard_stale_match_container`)。四项注入:

- `self.gs` = 当局状态容器单例只读引用(决策输入的单一来源);
- `self.config` = 对局配置按参注入;
- `self.state` = 策略器私有状态实例(经 `_create_state` 钩子每局新建,缺省 None,子类覆写定制——见 §4);
- `self.rng` = 决策随机源(`config.strategy_seed` None → 固定种子 0,禁静默翻转为熵种子——可复现纪律)。

`create_session`/`create_state` 工厂已停用。**决策记录自动包裹**:`__init_subclass__` 给全部决策入口自动包 wrapper(决策序号/决策标签/`decision_payload` 载荷钩子)——遥测捕获缝结构上不可漏,不靠实现自觉。

### 3.2 分画面决策口 14(抽象;零参)

各入口按帧的新旧标记(帧代次)自行触发终局意向重估,不设独立钩子。

| 接口 | 输入 | 返回 | 语义 |
|---|---|---|---|
| `decide_prep_screen` | 状态容器 game state 直读 | **恰一个动作**(CwAction),无 None;重观察 = CwActionObsParam 两口径(in_place 环内重观察 / outer_loop 结束本次访问) | 备战决策 |
| `decide_shop_action` | 状态容器直读 | **恰一个动作**,「无动作可做」= `CloseShop` 恒可用终结 | 决策本体 = `mandate_v1/shop.py`;状态容器 shop payload 离屏 = 观察层失约抛错 |
| pick 族 12:`decide_invest_env` / `decide_invest_strategy` / `decide_supply` / `decide_encounter` / `decide_megastar` / `decide_partner` / `decide_planner` / `decide_star_tome` / `decide_wish_trial` / `decide_box_card` / `decide_fortune` / `decide_expert_invite` | 状态容器槽零参读(候选自各 `*_opts` 槽/payload 槽;离屏 None = 观察层失约抛错) | 恰一个动作:选卡 `CwActionPickXxxParam` ∨ 刷新建议动作,互斥单发 | 选项决策;动作编排归画面 op。决策规格 = strategy-docs/13_pick_family.md |

### 3.3 内部辅助成员(实现层,不属接口)

- `decide_shop_screen`(flow 层缺省驱动器 + bridge 覆写)——**给回放与测试用的旧式驱动器**:逐帧调 `decide_shop_action` + 逐动作直调上报函数推进期望态,终结动作截停;生产执行侧不走(单动作循环),sim 亦不走。
- `_refresh_direction` / `_refresh_direction_views`(flow 层私有)——**省算机制**(方向节拍 = 每游戏轮只做一次的昂贵计算段):用两个标记槽记录最近一次备战/商店观察是新是旧(`gs.frame_class_prep`/`gs.frame_class_shop` ∈ full/view/none),决策入口据此每游戏轮只做一次贵段;标记读完即清,只有观察装配点和决策环能写。
- `write_shop_mirrors`(遥测镜像写者)。

**生命周期机制归流程侧**:幂等键 `action_key`、stall 门、强制出战——策略器不管自己的重试/幂等/卡死防护,由流程层承载。新事件面优先归并进既有 pick 接口或走契约改版,禁旁路自造接口。

## 4. 状态放哪(三层)

先说三层各装什么:

- **GameState 状态容器** = **局内事实的唯一载体**:观察到的对局事实(血量/金币/牌面/板凳/等级/连胜/节点类型/词缀/池状态/已持投资策略等)全在这里,含 Field 域与非 Field 簿记(设计权威版本 = `docs/develop/sr_od/application/currency_war/game_state/README.md` + 代码字段定义注释)。策略器的全部输入从这里读;执行层不再设旁表状态载体。
- **策略器状态 StrategyState** = **策略器自己的中间变量**:意向状态机、限制器计数、推导缓存——实现包私有类(mandate_v1 的 MandateState),实例属性 `self.state` 承载(经 `_create_state` 钩子每局全新创建);setter 同步挂接 `gs.strategy_state`——单一状态对象两处引用,禁第二状态对象。
- **StrategySession**(`kernel/cw_strategy_session.py`)= 一局总载体:装观察数据 + 框架设施(性能观测反馈跟踪器);策略器状态与 rng 已迁策略器实例属性,session 不再中转。

**变量收拢规则**:策略器决策所需的中间变量(意向状态机/计数器/推导状态/临时标记),一律收拢在自己实现包的私有状态(StrategyState)里——禁写进 GameState 状态容器(那是局内观察事实的载体,决策中间量不是事实),禁散落模块级全局。

再讲三条规则:

1. **策略器状态是黑盒**:状态对象归策略器实例私有,框架经 `gs.strategy_state` 挂接解析到同一对象、只搬运不读写其内部——kernel 判据层消费经**访问函数**(`strategy_state_of(gs)`,None-safe,状态缺席不新建,类型收窄);任何新遥测字段必须从访问函数出发,禁直读猜字段;禁 impl 侧 `state_of` 从执行层调用。
2. **恢复局 = 策略器状态空着重来**:server 重启后接管残局,session 观察数据由入口观察全量重建;策略器状态**不可重建、不尝试重建**——以空状态冷启动,凭当帧观察重新驱动。丢失语义:意向状态机从未锁定态重驱动(可能锁到与重启前不同的线,决策仍自洽);纯限制器计数归零 = 「未发生过」;同轮已卖集丢失 = 守卫失效窗口与先卖后买回的资产缩水循环风险(下个入口重估自愈);遥测分键局终快照只含恢复后增量。
3. **换策略只允许发生在局边界**:切 `strategy_id` 替换时,旧实例整体弃置、新实现全新构造——状态类型是实现包私有,跨实现的状态迁移**不定义**(实例不跨局使其天然成立)。

补充:

- **坐标伴随域**:凡观察域识别的「可选/可交互实体」(选项卡/备战栏/装备栏/晶矿/浮层按钮),状态容器除语义事实 Field 外,同源记录**坐标伴随字段**(命名 `<实体>_xy` 或条目内 cx/cy)。写端 = 观察上报单点整表覆盖(随帧刷新),**禁逻辑写端**——动作后回填坐标无画面读数;坐标缺席 = 策略产参跳过自愈、下帧观察重派,禁回填猜值。用途 = 动作原语参数面③类(动态坐标显式传参,SKILL.md §1.4)的数据源:策略层产动作参数时从伴随域取坐标,动作 op 零内部识别——与动作域「坐标按下标取自状态容器」规范同族,由 pick 族推广到全部视觉定位实体。逐字段登记随实现落在 cw_game_state 字段注释(先例 = owned_equip_xy)。
- 异常路径残留状态容器由 `discard_stale_match_container` 在「确凿新局」信号点丢弃。

**第三方兼容**:注册面封闭集 = {mandate_v1};构造注入 + 零参入口契约对存量第三方策略**不兼容 = 显式破坏申报**(契约形状权威版本 = `strategies/impl/cw_strategy.py` 的 `CwStrategy` 基类 docstring)。

## 5. 装配与依赖

- **依赖方向**:实现包 → 知识层/数学层/执行层单向;分包依赖矩阵禁 decision→obs 直接依赖(obs 读口经 app 层装配点 `install_obs_ports()` 注入);决策本体 = 纯函数。
- **决策 hp 读口与可信位**:统一读口 = `kernel/cw_hp_policy.py::decision_hp`(gs.hp 直读);可信位另经 `hp_decision_trusted_of`(`gs.hp.source ∈ {observation, carried}`,prior/logic fail-closed——信息缺失时宁可判不可信,不猜值);hp 不入其余任何策略判据,新增 hp 决策消费点必经读口或登记豁免。
- **sim 消费面**:sim = 游戏后端(驱动反转——真流程当驱动者,状态副本在后端):四层全图装上后端即在 sim 状态副本跑一局,**全决策面 sim 可达**;批量运行与 A/B 不在 sim 本体内(边界 = sim/sim-design.md §8.3);校准缺口的判读限制 = sim-design §8.2 申报清单。
- **换核与 A/B**:注册面封闭集 = {mandate_v1};换核机制 = config 切 `strategy_id`(最小面),不改流程侧分发。归因限制:sim-design §8.2 申报面上的读数不得作策略效应证据,真代码层/机制层读数可外推(保真度分层承载)。
