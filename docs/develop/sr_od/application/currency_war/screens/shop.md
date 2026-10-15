# 商店开画面(shop · 货币战争-备战-开商店)

> 代码 = `operations/cw_screen/cw_screen_shop.py::CwScreenShop`(两 node 画面 op:观察 node + 决策动作 node)+ `operations/cw_screen/cw_screen_prep.py::visit_open_shop`(生产调用编排单一源)。职责:商店打开态的一次访问——入口观察(唯一读屏点)→ 单动作 round_wait 决策循环(执行 → 逻辑态直写;逻辑态 = 动作执行后不经观察、按游戏规则推算并直写容器的预期状态,例:买牌后金币 −40、备战席 +1;下一帧观察与推算不符时以实际观察为准,下同)→ 终结动作返回主循环(结束本次访问 = 本访问结束、控制权返回主循环重新识别画面;下同)。路径根 = `src/sr_od/application/currency_war/`。
> **决策判据(买什么/卖什么/刷不刷/升不升)一律不在本篇**——本篇只管「循环怎么转、期望态怎么推进、何时离店」;判据见 [../../strategy-docs/11_shop_decisions.md](../strategy-docs/11_shop_decisions.md)。

## 1. 分发判定

- 外循环「商店开画面」分支(店已开态):开商店画面档**三 id_mark** 同帧——「备战标识-购买经验」∧「按钮-收起」∧「标识-备战阶段」(`_shop_open_anchors_hit`;与干净备战的「按钮-出战」天然互斥)。分发 = 阶段一身份行(三 id_mark;历史穿透命中曾把部署/出战点击打在浮层上,§2.2)。
- 显式开店:备战访问内 `OpenShop` 动作 → `visit_open_shop`(本篇 §2 编排单一源,与「商店开画面」分支转交同口构造 `CwScreenShop`)。OpenShop 为单一形态,无受限变体。
- 受限消费(策略侧自限,零流程闸——受限是策略自己遵守的纪律,框架不加流程强制):策略器每帧现算一个标记,表示本帧处于「决战前的受限花钱阶段」(出战就绪 ∧ 金币已达利息线;派生标记 = `mandate_v1/bridge.py::launch_restricted_session_active`,每帧现算、不跨帧记忆)。处于该阶段时,决策链最先检查的发出点(`mandate_v1/bridge.py::_launch_front_check`)产出的商店访问意图 = 普通开店/普通访问路径。该阶段商店只做一次受限购买:`decide_shop_action` 给出唯一提案,经 kernel 校验谓词 `kernel/cw_launch_arbitrage.py::launch_arbitration_gate` 检查,拒绝则改发 CloseShop 关店、结束本次访问(直接放弃,不换第二方案);每个出战就绪段最多触发一次(阶段标志位 `cw4_launch_spend_visited`,离开出战就绪状态后复位)。
- 建档 = `assets/game_data/screen_info/currency_war_battle_prep_shop_open.yml`(商店牌-1..5 / 按钮-刷新 / 备战标识-购买经验 / 按钮-收起 等 area)。

## 2. 画面形态声明

**决策循环形态(两 node 画面 op;决策动作 node = round_wait 单动作循环)**。生产两路(外循环「商店开画面」分支转交与显式开店同口 `visit_open_shop`、`run_operation` 单跑)构造 `CwScreenShop` 并节点函数直驱(观察 node 恰一次 → 决策动作 node 循环至终结;不经框架 execute 循环——决策循环轮间零截图)。决策入口 = 契约 `decide_shop_action`(`strategies/impl/mandate_v1/shop.py`;**全函数** = 对任何输入都给出恰一个动作:f(期望态) → 恰一个动作,「无动作可做」= CloseShop 恒可用终结;观察帧缺失即抛错;终态零参口)。全动作统一路径零特例拦截零闸(§4);终结动作(RefreshShop/CloseShop)= 本访问结束返回主循环——外循环「商店开画面」分支重分发 → 新访问入口观察重建牌面 → 策略逐帧再决策,「刷后买不买/刷不刷」由策略在下一访问自然表达。刷新无次数上限——用户裁定:无限刷新环 = 策略实现 bug,框架不兜底(暴露面 = 外部停滞哨兵);决策循环无防御性轮数上限——用户裁定:不收敛 = 策略实现 bug,响亮暴露。回放经 `decide_shop_screen` 驱动器消费(非契约成员,同经 `decide_shop_action` 单动作核);sim 经真流程消费同一单动作接口(驱动反转,无独立引擎直调面)。

出参交接契约:失败判定 = 轮结果 `is_success`(False = 未识别卡停机/未观察熔断的 round_fail);执行账 = `op.ledger`(`ShopVisitLedger`,run 完成后有效,`total_buy`/`total_xp_buy`/`total_refresh` 为上报 executed 计数单一源)。

## 3. 观察面

**入口观察 = 唯一决策读屏点 = 对账边界**(对账 = 把动作后按游戏规则推算的状态与下一帧实际观察比对核实,不符时以实际观察为准;下同。`CwScreenShop.observe`,每访问恰一次;单次读零防抖——读缺交决策前置门 `decide_shop_action` 响亮失败,禁重读等待):

```
点击点位/升级钮/刷新钮 screen_info 定位核实(缺失 = 建档漂移显式 round_fail,禁兜底坐标静默点击)
→ read_game_state(phase=PHASE_PREP_SHOP_OPEN) 全量现读,漏斗容器(容器 = GameState,游戏状态对象,下同)直写(obs 族渠道签名;
   产出 GameStateReadReceipt 回执)
→ 未识别卡停机闸(读链终判仍含 unknown 槽 → stop_running 保留证据 + round_fail)
→ 免费刷新次数观察登记(漏斗 shop-open 段自带,复用刷新钮三态在用读,零新增读屏:
   免费态登记实读次数 / 付费域登记 0(游戏规则 ⇒ 免费余量恒 0)/ 整帧判不出跳写;
   失配对账 = Field 机制白送,见 §8)
→ 帧代次 frame_class_shop = 'full'(帧代次 = 一帧观察的完整度标记,'full' =
   完整帧;每进店一次就把观察帧标为「完整帧」;刷新后重进按全新入口重估策略
   方向,开销大的方向计算每游戏轮只算一次,由既有缓存标记保证)
→ 节点类型 = 店开上下文查现行链直定(`chain_node_type`;链缺位/位越界/未辨 =
   kind None 诚实缺位,零内建回落;
   本段无台账回填写端——logic 通道覆盖会吞观察对账,滞后拷贝禁令)
→ 店开帧预算披露覆写(gold 真值入链,overflow/budget 三预算字段;每访问一次)
```

观察写入 = ①观察态上报进 GameState 的观察边界;段内不比对、不重建(统一规范 = [op-layer.md](op-layer.md) §1.3;关键信息未观察由字段态值前置拦截,见 §5 全 unknown 窗)。画面 obs 类 = `CwScreenShopObs`(`kernel/cw_screen_report/shop.py`,report 保持占位):观察 node 产入口回执同面镜像挂实例属性(供决策侧/测试消费),无容器摄入面——容器写端在观察漏斗 `read_game_state`。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「返回主循环」= 本访问结束、控制权返回主循环 `cw_loop.py::CwLoop.loop` 重新识别画面并重判):

| 动作 op(动作类型清单参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| `CwActionBuyCardOp`(`CwActionBuyCardParam`) | 注册表工厂(`action_op_class_for` + `ShopExecEnv` 组装) | 自上报 `report_action_buy_card_param` 单点(简单落位/合成连锁/升星分支内聚;获取计算完后触发 `gs.effects.on_buy` 购买回调,bump CounterKey.BUY) | 否(非终结):发出后落地门/回执行,决策循环续跑;执行未落地 = applied=false 回执行,期望态两侧都不动 |
| `CwActionLevelUpOp`(`CwActionLevelUpShopParam`;备战域注册行同 op) | 注册表工厂(同上) | 自上报 `report_action_level_up_param` | 否(非终结):发出后决策循环续跑(clicks 序列 = 动作内部步骤,逐帧重组) |
| `CwActionSellBenchOp`(`CwActionSellBenchParam`;注册行已更替备战域 op) | 注册表工厂(同上) | 自上报 `report_action_sell_bench_param` | 否(非终结):拖拽机械单发,发出即记账 |
| `CwActionRefreshShopOp`(`CwActionRefreshShopParam`,**访问终结** terminal=True) | 注册表工厂(同上) | 自上报 `report_action_refresh_shop_param` 单口(计数触发 + `free_refresh_left` Field 免费次数分支扣减 + `write_logic_rand` 随机态采样) | **是(访问终结)**:执行后本访问即结束返回主循环重进;零读屏零验证(免费判定 = Field 值,非决策闸) |
| `CwActionCloseShopOp`(`CwActionCloseShopParam`;执行位 = 真机械点击) | 注册表工厂(同上,全动作统一路径) | 自上报 `report_action_close_shop_param`(店族 payload 清场 leave_screen;幂等已关/点击已发两出口同调) | **是(访问终结)**:恒可用终结;「终结不入 decisions 行」契约(执行事实回执由动作 op 自身承担) |

```
while True(round_wait 单动作循环;循环内零读屏,帧不消费):
  action = strategy.decide_shop_action()   # 恰一个动作,全函数(终态零参口)
  │    异常 → 保留证据后上抛
  ├─ CloseShop 且 tracked 未观察 → 跳过留痕/连续跳过熔断(留痕后照常执行:
  │    未观察跳过 = 零消费动作,仅执行关店离店,备战环 heavy 观察核实后再进店)
  ├─ 守卫断言 guard_proposal_vs_expected(提案对象在期望态存在且未被消费,
  │    炸出 = 策略器算术 bug;防 bug 护栏,非控制流分支)
  ├─ 动作 op execute(注册表派发;全动作统一路径,零特例拦截零闸;机械发出,零成败判定):
  │    BuyCard:槽号定位(payload 定长槽阵列,数组下标+1 = 物理槽;身份同一性优先,
  │            退化 (name,star))→ 点牌位 → 动画窗 → 发出即记账
  │            (total_buy/spend_executed/bought_names)→ 满栏自动多买补差(k 单一源)
  │    LevelUp:点购买经验单击 → 动画等待(clicks 序列 = 动作内部步骤,决策循环逐帧重组)
  │    RefreshShop(访问终结):点刷新 → 固定等待(`REFRESH_CLICK_SETTLE_WAIT_S`)
  │            → 发出即记账(刷价 = 容器刷价现值,失读回基价常量)→ 自上报
  │            (计数 + Field 免费次数分支扣减 + write_logic_rand 随机态)
  │    SellBench(能力面;注册行已更替备战域):拖拽机械单发 → 发出即记账
  │    CloseShop(访问终结):执行位找「按钮-收起」→ miss = 店已关(幂等出口)；
  │            命中 = 点击 + 固定等待 → 清场上报;零转移验证
  ├─ 落地门 apply_action_outcome(调用环单一源):execute 无返回(发出即职责完成,零判效——判效 = 执行侧判定动作是否生效,零判效 = 不判定、落地事实归下一帧观察;下同);
  │    门保留为结构防线——未落地 ⇒ 两侧都不动;期望态推进 = op 自上报单点
  ├─ op 自上报(容器规则通道,纯计算零读屏)直写容器
  终结判定读注册表 action_op_class_for(action).terminal:
    非终结 = round_wait;终结(RefreshShop/CloseShop)= round_success 返回主循环
    (访问动作日志行结束本次访问前 log;回执 detail = 执行账汇总串)
```

逐动作规格 = [../game_state/logic-updates/](../game_state/logic-updates/README.md)(buy-card / refresh-shop / close-shop / level-up 各篇)。

## 5. 终结与交回

| 条件 | 语义 |
|---|---|
| **RefreshShop 访问终结** | 刷新是唯一引入新事实的动作(新牌面),执行即本访问结束返回主循环——重进 = 全新访问入口观察重建期望态(真结束本次访问,零额外动作;节点行观察归备战观察域,商店域零探针) |
| **CloseShop 访问终结** | 策略器主动选关店(全函数「无动作可做」的表达)= 恒可用终结;执行位真点击收起,返回主循环。唯一常规离店条件 |
| 未观察跳过熔断 | tracked 未观察 → 策略恒可用终结 CloseShop = 零动作跳过(缺陷台账留痕);连续 `SHOP_UNOBSERVED_SKIP_LIMIT` 次 = round_fail 交兜底链 |
| 全 unknown 窗 | 牌面含 unknown 槽(整帧 OCR/SIFT 失读窗)→ **入口观察即停**(见下行;决策入口前置门仅返回 CloseShop 为纵深第二线) |
| 刷新无硬墙 | 刷新无次数上限(用户裁定:无限刷新环 = 策略实现 bug,框架不兜底);每刷一次 = 一次完整「商店开画面」分支重分发与全新访问 |
| 未识别卡停机 | 入口观察回执落地即判:读链终判(内部易误判重观察后)仍含 unknown 槽(empty=确证空位不计)→ `stop_running(save_screenshot=True)` 框架截图保留证据 + round_fail——决策/购买不见残缺牌面(未识别不能降级带病跑;细则 = [../flow/guards.md](../flow/guards.md) §3) |
| 循环异常 | 上抛 → 编排层单元 aborted 关账,店不收(交上层重新识别) |

`visit_open_shop` = 商店画面 op 驱动的**编排单一源**(构造 `CwScreenShop` 节点函数直驱),显式开店与「商店开画面」分支转交两路径共用;失败路径不收店(店留着交上层重新识别)。访问回执 detail = 固定完成事实串(执行账计数;该行不计入停滞看门狗认可的实质推进信号——零动作空转与真买牌在日志行形态上不可分,推进可见化归 state/round 变化、复合动作成功、采晶矿成功等信号)。

## 6. 状态上报面

- 动作 → 上报函数:op 自上报 `kernel/cw_action_report/<snake>.py::report_action_<snake>_param` 单点(买牌 = `report_action_buy_card_param`,快照与合成升星分支内聚,升星判据单一源 = `kernel/cw_game_state.py::detect_merge_upgrade`;购买计数回调 `gs.effects.on_buy` = 买牌上报函数内获取计算完时点单点,live/sim 同源);逐动作规格 = [../game_state/logic-updates/](../game_state/logic-updates/README.md)。
- 免费刷新剩余次数位于容器字段 `gs.free_refresh_left`(Field,剩余语义):观察登记(§3)/刷新上报扣减/发放登记三写端同格;付费/全量刷新计数留效果账本累计。

## 7. 子态与 overlay

- 商店卡牌详情弹窗:阶段一身份分发(`CwScreenShopCardDetailPopup`,点 X 验消失,**绝不点购买**——买不买归商店域)。
- 商店刷新概率表弹窗:阶段一身份分发(点 × 关);概率条直读进 `refresh_probs` = 观察非动作。
- 暗色衬底弹窗遮蔽底层全部识别标志时,外循环阶段一身份分发的弹窗分支先行分流,之后才可能落到本画面分支。

## 8. 守卫与防线

- 未识别卡停机(§5,入口观察即停;用户裁定:未识别不能降级带病跑,识别不到就是 bug)。
- 刷新无硬墙(用户裁定:无限刷新环 = 策略实现 bug,框架不兜底;外循环无进展治理归 stall 防线);shop_visit_idle_gold 计数键(visit 语义)。
- EV 买面席位门(满栏帧不提案,拒因分键 shop_ev_bench_wait;满栏合成买面 m2_merge_completion 提案不在该门适用范围内)。
- 免费刷新次数失配告警:观察登记值与动作扣减/发放登记的 logic 值失配 → 走 Field 既有失配告警(`kernel/cw_mismatch_policy.py`,§6 观察对账告警同机制)——免费刷新的事实可见性 = 该告警 + 效果账本计数,零手写对账台账。

## 9. 遥测与测试面

- journal op 名 = 「商店访问」(「商店开画面」分支转交与显式开店同口);计数键 shop_visit_idle_gold / branch_shop_open_*;投放分键 plan_visit_action_cap / shop_ev_bench_wait。
- 刷新遥测:执行账 `total_refresh`(paid/total 两计数留效果账本累计);telemetry schema 存量读兼容字段 `plan_truncated`/`refresh_attempted`/`refresh_board_changed`(`telemetry/schema.py`,现无生产写入端,读存量行兼容)。
- 受限会话自限遥测:受阻分键 `launch_arbitrage_gate_blocked` 落策略器状态 `cw4_counters`(拒绝发生时的写点 = `decide_shop_action` 内自限);受限会话阶段标志位 `cw4_launch_spend_visited`。
- 测试:商店投影逻辑测试(test_shop_projection_logic)、受限购买校验门(launch_arbitration_gate)交叉核对、P56 买面测试等,测试面 = `sr-od-test/test/sr_od/application/currency_war/`。
- game 侧知识:经济机制(刷新/利息/锁商店) = [../../../../game/currency_war/research/economy.md](../../../../../game/currency_war/research/economy.md);合成机制 = [../../../../game/currency_war/research/merge_mechanics.md](../../../../../game/currency_war/research/merge_mechanics.md)。
