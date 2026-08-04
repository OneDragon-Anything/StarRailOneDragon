---
name: sr-od-dev-write-operation
description: 当要在一条龙(OneDragon)框架上**新建、修改或调试单个 Operation** 时用 —— 写一个 op(用 `@operation_node` 声明节点、用 `round_by_*` 做画面判定与点击、处理一个画面或一类动作、返回 round 结果),或改/修已有 op 的逻辑与 bug。Use when writing, modifying, or debugging a single Operation on the OneDragon framework — declare nodes via `@operation_node`, detect/click screens via `round_by_*`, handle one screen/action, return round results; includes fixing an op's logic/bugs. 不触发:从零做新玩法(od-dev-gameplay-automation)、搭/改 app 骨架与配置(sr-od-dev-application)。
---

# 写 / 改 / 调试单个 Operation(OneDragon)

OneDragon 的 Operation 是**节点图状态机**:一个 op = 若干 `@operation_node` 节点 + `@node_from` 边。框架每轮截图 → 跑当前节点 → 按其返回的 round 结果沿边找下一节点。**写 op = 把"一类画面 / 一个动作"拆成节点,每节点读屏 → 判定 → 动作 → 返回 round 结果。**

> 全程守「**看(screenshot/OCR)→ 动(click/key)→ 等(sleep)→ 验(再读屏)**」。别凭猜硬写 —— 凭猜只覆盖一种情况、漏另一种,必回归。

## 写一个 op 的主线(按序)

1. **先找兄弟 op 抄骨架,别从零**。在 `src/sr_od/` 找一个职责相近的已有 op(同类画面 / 同类动作),照它的 `__init__` / `handle_init` / 节点结构写。比从零省一个数量级,也符合项目"先复用现有 Operation"硬约束。
2. **要碰的屏先建档,再写逻辑**。op 依赖的每个画面必须先有 screen_info area / 模板 —— 没建档的屏不写逻辑(坐标 / 关键词会全靠猜)。建档走 `od-dev-screen-onboarding`;坐标检测 / 验证走 `sr-od-dev-ui-region-detect`。
3. **拆节点**:一节点 = 一类画面 / 一个动作。激进拆小 op —— 某方法 if-elif ≥ 3 个不同画面/动作,或单 op 超 ~80 行 → 拆成独立 op(便于 `run_operation` 单跑定位失败步)。
4. **每节点**:读屏 → 判定 → 动作 → **返回 round 结果**(语义见下)。
5. **单 op 实测**:`run_operation '<op_id>'` 单跑通过,再接入主流程。测试机制见 `references/testing.md`。

## round 结果驱动节点图(核心心智)

每节点返回 `round_success` / `round_wait` / `round_retry` / `round_fail`(+ `status` / `data` / `wait`):

| 返回 | 框架行为 |
|---|---|
| `round_success(status)` | 沿 success 边找下一节点;无下一节点 → op 成功结束 |
| `round_fail(status)` | 沿 fail 边找下一节点;无下一节点 → op 失败结束 |
| `round_wait` | **重跑当前节点**(等画面变化 / 等动画) |
| `round_retry` | 累计重试当前节点;超 `node_max_retry_times` → 转 FAIL |

`status` 字符串给 `@node_from(status=...)` 精确路由(多出口节点按状态分流)。完整路由规则 / 自环陷阱 / `previous_node` / `handle_init` 见 `references/node-graph.md`。

## 画面判定与点击:`round_by_*` 选型

| 场景 | 用 |
|---|---|
| OCR 找文字并点击 | `round_by_ocr_and_click` |
| OCR 只判定不点 | `round_by_ocr` |
| 多目标按优先级点一个 | `round_by_ocr_and_click_by_priority` |
| screen_info area 找图/字并点 | `round_by_find_and_click_area` |
| 固定区域只判定 | `round_by_find_area` |
| 直接点固定坐标区域 | `round_by_click_area`(不判定) |
| 导航到某画面 | `round_by_goto_screen`(按 screen_info route) |

> ⚠️ **OCR 关键词必须画面独有**。框架 `round_by_ocr*` 默认 `lcs_percent=0.5`(子序列匹配),关键词与同屏/邻屏文字**共享 2+ 字子串即误匹配** → 该节点不触发或走到错误画面。止血:传 `lcs_percent=0.7~0.9` 或用更长独有关键词;根治:用**固定位置识别**(screen_info area 圈定关键词所在位置,不全文扫)。逐 helper 全参数 + LCS 机制见 `references/round-by-helpers.md`。

## op 内工具

- 截图:`self.screenshot()` 截并存 `self.last_screenshot`;`save_screenshot()` 落盘调试。
- 点击 / 按键:`self.ctx.controller` 的 `click(pos)` / `mouse_move(pos)` / `btn_tap(key)` / `active_window()`。
- OCR:`self.ctx.ocr.get_ocr_result_list(image, rect=...)`(区域 OCR,与全屏 OCR 行为可能不一致,分开验)。
- 调子 op:节点里 `sub.execute()` → `self.round_by_op_result(op_result)` 转 round 结果。

## 必守不变量(反复发作的坑)

1. **bug#1:每轮 `before_screenshot` 把鼠标移到角落 → 紧接的 `click` 被游戏判拖拽落空**。症状:op 同坐标点不中、手动 `click_game` 一发即中。缓解:关键 click 前 `mouse_move(target)` 再 `click(target)`(鼠标已到位 = 零移动 = 不被判拖拽);click 之间别再截图。详 + 其他坑见 `references/framework-pitfalls.md`。
2. **MCP click/key 异步**:立即返回但 ~1s 才落地;操作后 `sleep` 再验,否则截到点击前画面。
3. **调试先读日志,不够就补日志**:bot 卡住 / op 失败 → 先读 `.debug/sr_od_mcp/` 下日志(实际 OCR / 走到哪个节点 / 决策状态),别盲点坐标。日志解释不了 → 在决策点补日志(OCR 摘要 + 点击坐标 + 分支结果)+ `save_screenshot()` 存图。
4. **预料外画面别只 ESC**:先调研"上一步代码点了什么 → 落到哪个 UI 元素 → 游戏对该元素的交互",建档后改 click 避开误触元素(不只加 ESC handler)。
5. **多样本核实**:验证 OCR / 读取器跨多样本看统计分布,别凭一张图 / 单次推断下结论。

## 边界(这些去别的 skill)

- 从零做新玩法全程 → `od-dev-gameplay-automation`
- app 产品化(factory / config / GUI / run-record / app 编排)→ `sr-od-dev-application`
- 建一张屏的机制 → `od-dev-screen-onboarding`
- 通用 bug 定位 / 修复流程 → `superpowers:systematic-debugging` / `sr-od-dev-deciding-a-fix`

## 写完自检

- [ ] 碰到的屏都建了档(screen_info area / 模板),不是凭猜坐标/关键词?
- [ ] op 拆得够小(单一职责),能 `run_operation` 单跑定位?
- [ ] OCR 关键词画面独有(查了 LCS 共享子串)?
- [ ] 关键 click 加了 bug#1 缓解(`mouse_move` + `click`)?
- [ ] 决策点有日志 + 存图,卡了能复盘?
- [ ] 单 op `run_operation` 实测通过再接入?
