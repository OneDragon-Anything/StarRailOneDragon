# 等待 1-1 备战(wait_one_one · 开局补给动画等待)

> 代码 = `operations/cw_screen/cw_screen_wait_one_one.py::CwScreenWaitOneOne`(两 node 直继承 `SrOperation`)。职责:投资环境确认后进 1-1 的开局补给动画等待——动画长且无结束标志,轮询「备战阶段」锚判「备战面板就绪」;固定上界仅作超时兜底。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

非独立分支:外循环投资环境分支 **链序第二段**(`CwScreenInvestEnv` → 本 op,用户裁定的特殊等待;两 op 两对 journal 行,首段轮次结果只记日志不分流,返回尾段结果——链序代码锚 = `cw_loop.py::CwLoop.loop` 投资环境分支段)。主判据锚 = 「货币战争-备战.标识-备战阶段」:该文本备战/开商店两档同址无画面判别力,此处只判「备战面板就绪」非画面分支,用途正当(代码注);**不据它做画面分发**(分发仍归外循环全分支)。

## 2. 画面形态声明

**空决策纯等待形态**。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1;本屏 = 其在册就绪等待变体,观察 node 轮询为已登记形态非偏离):观察 node = 轮询主体——锚命中 → obs 装载 + 占位 report → success 进决策动作 node;超时 → 存图留证 + round_fail 交回;未就绪未超时 → `round_wait(ONE_ONE_POLL_INTERVAL_S)` 轮询(wait 语义不耗框架 retry 预算,轮询由固定超时兜底)。决策动作 node = 零动作 success 交回(纯等待型无推进动作)。`_monotonic` = 可测时钟模块级单点(测试换假时钟验超时)。

## 3. 观察面

轮询单锚判定(观察 node 两早退:锚命中 / 超时);超时基 = `_first_seen_ts`(首见非就绪帧时钟起点)。obs = `CwScreenWaitOneOneObs`(`on_screen`/`screen`,住 `kernel/cw_screen_report/wait_one_one.py`;锚命中轮装载,轮询轮与超时轮不装载——锚判定外零读屏);report = `report_screen_wait_one_one_obs` 占位调用(本屏现役零容器写点,接口为统一形态占位;match/gs 缺席跳过)。零容器写端。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| 无动作 op——纯等待零推进(无任何点击;锚轮询留守 op 内) | 画面 op 留守臂(观察 node `observe` 轮询 `round_wait`;决策动作 node `act` 零动作 success 交回) | `report_screen_wait_one_one_obs` 占位调用(锚命中轮;现役零容器写点,统一形态占位) | 是(锚「货币战争-备战.标识-备战阶段」命中 → act round_success 交回;超时 ≥ `ONE_ONE_MAX_WAIT_S` → 存图留证 + round_fail 交回) |

零动作(纯等待;轮询间隔 = `ONE_ONE_POLL_INTERVAL_S`,上界 = `ONE_ONE_MAX_WAIT_S`,常量单一源 = `operations/cw_screen/cw_flow_const.py`)。

## 5. 终结与交回

- 锚命中 → `round_success('1-1 备战就绪')` 交回(外循环下轮全分支重判进备战分支)。
- 超时 ≥ `ONE_ONE_MAX_WAIT_S` → 存图(`wait_one_one_timeout`)留证 + `round_fail` 交循环(锚一直不现 = 异常,不静默续等)。

## 6. 状态上报面

零写端。

## 7. 子态与 overlay

无子态。开局补给动画无结束标志 = 本 op 存在根因(screen_flow_timing #5/#29:1-1 是唯一不自动开商店、动画最长的开局节点)。

## 8. 守卫与防线

固定超时兜底 = 唯一防线(上界常量待实机校准只改常量);轮询不吃框架 retry 预算。

## 9. 遥测与锁面

- journal op 名 = 「等待1-1」;日志前缀 `[cw-flow-wait11]`。
- 测试锁:两 node 行为锁 + 假时钟超时锁(锚命中 round_wait 轮询/超时留证 fail)= `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_closing_screens.py`。
- game 侧知识:[../../../../game/currency_war/research/screen_flow_timing.md](../../../../../game/currency_war/research/screen_flow_timing.md) #5/#29。
