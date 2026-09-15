# 等待 1-1 备战(wait_one_one · 开局补给动画等待)

> 代码 = `operations/cw_screen/cw_screen_wait_one_one.py::CwScreenWaitOneOne`。职责:投资环境确认后进 1-1 的开局补给动画等待——动画长且无结束标志,轮询「备战阶段」锚判「备战面板就绪」;固定上界仅作超时兜底。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

非独立分支:外循环 0s **链序第二段**(`CwScreenInvestEnv` → 本 op,用户裁定的特殊等待;两 op 两对 journal 行,首段轮次结果只记日志不分流,返回尾段结果——`cw_loop.py::CwLoop.loop` 0s 分支)。主判据锚 = 「货币战争-备战.标识-备战阶段」:该文本备战/开商店两档同址无画面判别力,此处只判「备战面板就绪」非画面分支,用途正当(代码注);**不据它做画面分发**(分发仍归外循环全分支)。

## 2. 画面形态声明

**空决策纯等待形态**:decide/act 段零动作如实申报;decision cycle = `round_wait(ONE_ONE_POLL_INTERVAL_S)` 轮询等下一帧(wait 语义不耗框架 retry 预算,轮询由固定超时兜底)。装配点分流同族(两端口在场 → 五段;缺省 → 生产直连旧路径);`_monotonic` = 可测时钟模块级单点(测试换假时钟验超时)。

## 3. 观察面

轮询单锚判定(`lifecycle_observe` 两早退:锚命中 / 超时);超时基 = `_first_seen_ts`(首见非就绪帧时钟起点)。零写端。

## 4. 动作面

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
- 测试锁:五段路径 + 假时钟超时锁 = `sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_closing_screens.py`(代码注另引 `test_cw_flow_ops.py`,现状不在测试仓,同 [plane_transition.md](plane_transition.md) 开放设计注)。
- game 侧知识:[../../../../game/currency_war/research/screen_flow_timing.md](../../../../../game/currency_war/research/screen_flow_timing.md) #5/#29。
