# op-runtime-debug-log 迭代设计（总纲）

## 0. 元信息

- 迭代目标：op 实测/调试排查的运行链路可观测性——消除日志文件维度的「中间环节」黑盒（画面判定 / 区域识别 / 点击执行 / until 验证 / 画面状态转移），使一次实跑的 debug 日志可读出完整决策链，消除「补日志→重跑」循环
- 状态：定稿
- 文档清单：无详设（单文档方案，§2 即完整设计）

## 1. 问题与动机

- 现状症状：op 卡住 / 行为异常时，**日志文件**只有链路两端——主循环的节点流转行（`节点 X 返回状态 Y`，INFO，operation.py:432）与异常栈（自动存截图）。中间环节在日志文件全黑盒：画面判定结果（`get_match_screen_name` 返回值）、区域识别过程（find 了哪个 area、OCR 读到什么、lcs/conf 多少、命中与否）、点击坐标与执行结果、until 锚验证进度、screen_loader 画面状态转移——均无日志。排查只能「加日志→重跑」，而游戏自动化重跑成本高（出事画面状态难复现，部分随机态不可复现）。
- 现状之另一面（不抹去）：框架在主循环已有 **overlay 遥测通道**——节点流转明细（`_emit_overlay_round_trace`，operation.py:433）、异常与完成事件（`_emit_overlay_timeline`，459/696）、每轮耗时（`_emit_overlay_round_perf`，466）。overlay 是实时浮层事件、不落盘、不可 grep；本迭代补的是它不覆盖的**持久文本日志**通道，两者关系见 §2.5 取舍四。
- 根因归层：流程层——`screen_utils` 识别链路与 `Operation` round 系列作为公共运行链路，其**日志文件通道**从未承担「运行时可观测」职责（overlay 通道已起步但形态不同）；可观测性散落在各 op 开发者自觉打的日志里（质量参差；`src/sr_od/application/cultivation/account/operations/read_warp_status.py` read_status 节点读数后即一条未打）。
- 解决到哪：运行链路 9 个 debug 日志点全覆盖（§2），开发期开 debug 即得「画面→识别→分支→动作→验证→结果」完整决策链；op 层日志纪律随之缩为两条（status 写诊断句 / 关键分支选择落一句）。
- 明确不解决：
  - 不改 INFO 级正常运行日志的内容与量（仅 D2/D3 对现有 INFO 行做尾缀追加，见 §2.1）；
  - 不做日志收集 / 聚合 / 遥测分析（CW 遥测体系另管）；
  - 不做 controller 层 click 失败根因细分（窗口失焦等，另立）；
  - 不做「log 与 overlay 统一运行事件模型」（长期方向，登记见 landing 正本清单）。

## 2. 方案

级别策略：**新增日志点全部 `log.debug`**。日志级别开关已存在：`one_dragon_context.py:269` 在 `init()` 中执行 `log_utils.set_log_level(DEBUG if env_config.is_debug else INFO)`（`log_utils.set_log_level` 同时设置 logger 与全部 handler）——实测期开 debug = 配置 `is_debug=true` 后经 `init()` 生效。唯一待落地核实项：MCP server 启动链路是否必经 `context.init()`（landing 3.3）。

### 2.1 日志点明细（9 点，A–I 组）

**A. 画面判定（`get_match_screen_name` 及其 BFS 子函数）**

- 口径统一定义：「候选 / 试过」= **实际调用过 `is_target_screen` 的画面**——限定列表模式下第 K 个命中时前 K 个算、其余未判定的不算；BFS 模式下 scope 跳过的画面（只展开邻居不判定）不算；BFS 主环之外补漏循环（screen_utils.py:441-446）判定的算，接在判定序末尾。
- 落位机制：`get_match_screen_name_from_last` 内收集判定序与计数（内部变量聚合，经返回值或 out 参数带回父函数）；父函数 `get_match_screen_name` 统一打点。限定列表分支（368-373）不经过子函数，在该分支内就地打点。
- A1（每次判定，结果行）：`画面判定: <名字|None> (判定 N, X.XXs)` —— N=实际判定画面数；耗时覆盖子函数全程（计时起点在父函数入口，子函数返回后打）。
- A2（结果为 None 时追加）：`画面判定: None (试过 [按判定序前 10 个画面名] 全未中)`。
- 附带：`round_by_goto_screen` 内现有 `log.debug(f'当前识别画面 {current_screen_name}')`（operation.py:1473）与 A1 重复，删除。

**B. 区域识别 + 点击（`screen_utils` 识别入口层与底层）**

- B1（`find_area` / `find_area_binary` 入口，结果行）：`find_area <画面.区域>: <命中|未命中>`。
- B1a（`find_area_in_screen` / `find_area_in_screen_binary` 匹配循环处，详情行）：
  - 文本分支：`find_area <画面.区域>: OCR"<原文>" vs "<目标文本>" lcs=<值>/<阈值> → <命中?>`
  - 模板分支：`find_area <画面.区域>: 模板<id> conf=<值>/<阈值> → <命中?>`
  - binary 系（`find_area_in_screen_binary`）格式与 B1a 完全一致（不加 binary 前缀——调用方上下文可区分）。
- B2（`find_and_click_area`，三个点击出口各一条）：`点击 <画面.区域> @ (x,y) pc_alt=<T|F> → <成功|失败>`；识别未命中时 `find_area <画面.区域>: 未命中(不点击)`。
- **接口配套（`find_area_in_screen` 加可选参数 `screen_name: str | None = None`，binary 同构）+ 调用方枚举（grep 实证的完整清单）**：
  - `find_area` / `find_area_binary`（入口）：透传各自的 screen_name；
  - `is_target_screen`（screen_utils.py:479-488，**最高频调用方**——画面判定路径）：透传 `screen_info.screen_name`（475/484 行可得）——不透传则画面判定路径全部退化为裸 area_name，area_name 跨画面不唯一，无法与 A2 名单对号；
  - `tl_as_team_recognizer.py:79/92`、`cw_observation.py:1974/1984`：本迭代不改这两个业务文件（不传，日志退化打 area_name）；后续各自迭代可自行透传。
- **已知技术债（本迭代不还，底账准确记录）**：识别逻辑共**三套并行实现**——`find_area_in_screen`（151-192，纯判定）、`find_and_click_area`（242-302，识别+点击，自带第二份 OCR+模板匹配）、`find_area_in_screen_binary`（95-148，二值化判定，第三份）。日志三处都加；抽公共识别函数的重构不在本迭代（避免日志迭代混入行为重构）。另：`cw_observation.py:1974/1984` 自行二值化后直接调 `find_area_in_screen`（绕过 binary 入口），同构日志覆盖边界以实际调用路径为准。

**C. until 验证（`Operation.round_by_find_and_click_area` 验证循环，operation.py 977-1009 两块）**

- C1：逐锚行**仅覆盖实际验证过的锚**——`until_find_all` 循环遇首个未命中即 break（987-989），break 后的锚未验证、无日志；`until_not_find_all` 相反（首个命中即 break，1004-1006）。行格式：`until 验证: (<画面>, <区域>) <出现|未出现>`。
- 总结论行打在各验证块 return 之前 / 继续点击之前：`until 结论: <全部通过|锚未满足,继续等>`。
- 行序示例（until_find_all 两锚、第一锚未中）：
  ```
  until 验证: (大世界-普通, 右上图标-角色详情) 未出现
  until 结论: 锚未满足,继续等
  ```

**D. 主循环轮次增强（operation.py 432 行现有 INFO 行的尾缀追加，不改级别；消费方核实：节点通知走 round_result 对象（485 send_node_notify）、overlay 走对象字段（433-437），无文本解析该行的消费方——grep「返回状态」实证）**

- D2：行尾追加轮次耗时 `(X.Xs)`（与 `_emit_overlay_round_perf` 同源同口径，见 §2.5 取舍四）。
- D3：RETRY 结果时行尾追加 `retry=<N>/<上限>`，N=**递增后值**（打日志在 469 递增之前，实现取 `node_retry_times + 1`，即「本节点第 N 次重试」）。

**F. goto 路由（`Operation.round_by_goto_screen` 拿到 route 后）**

- F2：`goto 路由: <起点>→<终点> 经 [<画面.区域>, …]`（route.node_list 逐跳）。

**H. 失败自动存图（仅 op 终结处）**

- H1：**仅在 op 以 FAIL 终结处**（operation.py 487-497 块）`save_screenshot(prefix=f'{类名}_fail_{节点名}')`，文件名入日志。节点级 `round_fail` **不存图**——`_get_next_node`（562）按 success/fail 分流出边，fail 是节点间常规转移手段（fail→else 兜底），逐转移存图的量级与「FAIL=出了事」的暗示都不成立；retry 耗尽转 FAIL（474）同样不存（该轮 432 行 INFO + D2/D3 尾缀可查）。量级：一次实测时段 op 终结 FAIL 通常 0-2 次，磁盘可忽略。

**I. 画面状态转移（新增，堵决策链最后缺口）**

- I1：`screen_loader.update_current_screen_name` 内统一打（一处覆盖全部调用位）：`画面状态: <旧>→<新> (来源: <判定|点击乐观|goto跳转|…>)`——实现为该函数加可选 `source: str | None = None` 参数，四个调用位（operation.py:1470 判定、1483 goto 跳转、1497 点击乐观取 goto_list[0]、1524 check_and_update）各自传来源。理由：`current_screen_name` 是下一次 BFS 判定的起点（from_last 403-406），1497 的乐观更新无任何验证却直接改写判定起点——「为什么这次判定从错误画面展开」的答案藏在这类转移里，A1 只报结果不报起点来源。

### 2.2 与现有日志的关系

- `onnx_ocr_matcher` 已有 debug（`OCR结果 %s 耗时 %.2f`）打 OCR 原文，但无 area 上下文（多 area 顺序调用对不上号）——B1a 补上下文后互补，onnx 侧不动。
- `find_area` 系现有唯一 warning（区域未配置）保持；debug 不打在 AREA_NO_CONFIG 路径（warning 已覆盖该事件）。
- op 层自愿 `save_screenshot` 与 H1 不冲突：H1 是框架兜底。
- overlay 通道（round_trace / timeline / round_perf）不动，关系见 §2.5 取舍四。

### 2.3 debug 开启方式（已闭合）

`is_debug` 即日志级别开关：`one_dragon_context.py:269` `init()` 中 `log_utils.set_log_level(DEBUG if env_config.is_debug else INFO)`；`is_debug` 有完整落盘属性（env_config.py:349-362）。实测期开启 = 配置 `is_debug=true` 后经 `init()` 生效。待落地核实项仅一个：MCP server 启动链路是否必经 `context.init()`（若否，在 server 入口补一次 set_log_level，landing 3.3）。

### 2.4 变更面

- `src/one_dragon/base/screen/screen_utils.py`：A（get_match_screen_name / from_last 判定序收集）、B 全组、I 的 update_current_screen_name source 参数（若该函数在 screen_loader 模块则落其所在文件）。
- `src/one_dragon/base/operation/operation.py`：C1/D2/D3/F2/H1/I 的四个调用位传参、删 1473 重复 debug。
- `sr-od-test/`：新增最小烟囱测试（见 landing 判据）。
- 不改任何识别 / 点击 / 路由行为；不改 INFO 存量语义（D2/D3 为尾缀追加，无文本消费者——§2.1 D 已核）。

### 2.5 关键取舍

- **全 debug 级而非 INFO**：正常运行（一条龙数小时）日志量不受影响；级别开关已存在（§2.3），开启成本趋零。备选「retry/fail 轮次升 INFO」被放弃——分级条件逻辑侵入每个日志点。
- **两层日志（B1 结果级 + B1a 详情级）**：入口层有 screen_name 上下文、详情层有匹配过程数据；未命中时同一区域出两条，接受冗余。
- **B1a 量级账与可读性**：画面判定路径逐画面逐 id_mark 出详情行，未中画面首个 id_mark 即断（约 1-2 条/画面）；167 个建档画面下**单次全量判定最坏 100-300 条 B1a**，一个实测时段总量可达万行级。取舍：**接受**——debug 级单行极短，万行约 1MB；可读性靠两段式 grep（先 `画面判定: None` 定位失败轮次 → 按画面名过滤 B1a 明细）。若实测证明不可读，后续迭代再上聚合/失败回放机制（不在本案预建）。
- **log.debug vs 扩展 overlay 事件通道**（互补边界）：overlay = 实时浮层、不落盘、不可 grep、面向运行时观察；log = 持久文件、可 grep、面向事后排查。本迭代全部落 log 通道；D2 的轮次耗时与 `_emit_overlay_round_perf` 同源同口径（同一计时数据两个出口，各自服务事后排查与实时浮层）。「log 与 overlay 统一运行事件模型」为长期方向（landing 正本清单登记技术债指针，本迭代不做）。
- **不抽三套识别公共函数**：日志迭代混重构 = 行为风险与日志收益耦合；技术债三套并列已准确登记（§2.1 B）。
