# 运行链路可观测性(debug 日志与 overlay 边界)

> op 运行链路的日志观测体系 as-built。变更来源:op-runtime-debug-log 迭代;日志点语义细节与取舍的决策依据见该迭代 design(历史考古用,正本自足)。

## 1. 定位

op 一轮执行的决策链 = 截图 → 画面判定 → 识别 → 分支 → 动作(点击) → until 验证 → round 结果流转。框架在两个通道暴露这条链:

- **日志文件通道**(本文主体):持久、可 grep、面向事后排查。debug 级全覆盖运行链路中间环节;INFO 级只保留节点流转与 op 终态。
- **overlay 遥测通道**:实时浮层事件(`_emit_overlay_round_trace` / `timeline` / `round_perf`),不落盘、不可 grep、面向运行时观察。两通道互补,同源数据(如轮次耗时)允许双出口。

## 2. debug 开启方式

`is_debug` 即日志级别开关:`SrContext.init()`(`one_dragon_context.py`)执行 `log_utils.set_log_level(DEBUG if is_debug else INFO)`,同时设置 logger 与全部 handler。MCP server 链路经 `backend.start() → SrContext.init()` 必经此设置。

操作:GUI 调试设置或直接改 `config/env.yml` 的 `is_debug: true`,重启 MCP server 生效。实测/排查期开启,正常挂机运行关闭(万行级日志仅 debug 期产生)。

## 3. 日志点清单(全部 debug 级,除注明)

| 组 | 位置 | 格式 | 用途 |
|---|---|---|---|
| A1 | `screen_utils.get_match_screen_name` | `画面判定: <名|None> (判定 N, X.XXs)` | 判定结果+实际判定数+耗时;候选口径=实际调用过 is_target_screen 的画面(scope 跳过、提前命中未判不计) |
| A2 | 同上(None 时) | `画面判定: None (试过 [判定序前 10] 全未中)` | 判定失败的直接证据 |
| B1 | `find_area(_binary)` 入口 | `find_area <画面.区域>: <命中|未命中>` | 结果行 |
| B1a | `find_area_in_screen(_binary)` 匹配循环 | 文本:`find_area <画面.区域>: OCR"<原文>" vs "<目标>" lcs=<值>/<阈值> → <命中?>`;模板:`… 模板<id> conf=<值|->/<阈值> → <命中?>`(未命中被阈值过滤时 conf 打 `-`) | 匹配详情;binary 路径格式同 |
| B2 | `find_and_click_area` 三出口 | `点击 <画面.区域> @ (x,y) pc_alt=<T|F> → <成功|失败>`;未命中:`find_area <画面.区域>: 未命中(不点击)` | 「找了没点」vs「点了没效」分流 |
| C1 | `round_by_find_and_click_area` until 循环 | 逐锚:`until 验证: (<画面>, <区域>) <出现|未出现>`;总结论:`until 结论: <全部通过|锚未满足,继续等>` | 逐锚行仅覆盖实际验证过的锚(break 即止) |
| D2 | 主循环节点流转 INFO 行尾缀 | `(X.Xs)` | 轮次耗时,与 round_perf 同源 |
| D3 | 同上(RETRY 时) | `retry=<N>/<上限>`,N=递增后值 | 节点预算余量 |
| F2 | `round_by_goto_screen` | `goto 路由: <起点>→<终点> 经 [<画面.区域>…]` | 路由边排查 |
| H1 | op 终结 FAIL 处 | `save_screenshot(prefix='<类名>_fail_<节点名>')` + 文件名入日志 | 仅 op 终结;节点级 fail 是常规转移不存图 |
| I1 | `screen_loader.update_current_screen_name` | `画面状态: <旧>→<新> (来源: <判定|goto跳转|点击乐观>)` | source 非 None 且旧≠新才打;判定起点来源可追 |

接口:`find_area_in_screen(_binary)` 与 `update_current_screen_name` 各加可选参数(`screen_name` / `source`),None 时兼容既有调用方(日志退化)。

## 4. 排查阅读姿势

两段式 grep:先 `画面判定: None` / `retry=` 定位失败轮次 → 按画面名过滤 B1a 明细看「OCR 读到什么、差多少」。量级账:画面判定路径逐画面逐 id_mark 出详情行(未中画面首锚即断,约 1-2 条/画面),全量建档画面下单次判定最坏百余条、实测时段可达万行——属 debug 期预期量。

## 5. 技术债(登记未实施)

- 识别逻辑三套并行实现(`find_area_in_screen` / `find_and_click_area` / `find_area_in_screen_binary`)的合并重构。
- log 与 overlay 统一运行事件模型(当前同源数据双出口是受控冗余)。
