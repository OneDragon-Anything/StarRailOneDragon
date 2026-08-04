# sr-od-dev-write-operation — 设计概览

> 本文件是 **what**(skill 长什么样 / 范围 / 边界 / 构成)。**why**(为什么按粒度拆、为什么 op 粒度规范随 op 走)见 `decisions/0001-split-by-granularity.md`。

## 定位(是什么)

OneDragon 框架上「写 / 改 / 调试**单个 Operation**」的完整方法论 skill。mechanics(节点图 / round 结果 / `round_by_*` 选型 / op 内工具 / 单 op 测试机制)+ **op 粒度开发规范**(看动等验 / 识别方式选型 / 建档前置 / TDD+fixture / 调试读日志 / 密集日志 / 多样本核实 / 预料外画面调研 / 重复手动建op / bug#1 在 op 内形态)织在一起。给 coding agent 看,框架通用(不绑具体玩法)。

## 为什么单独成一个 skill(边界)

按**粒度**把"玩法自动化开发"拆成三层,每层一个自洽完整的 skill(理由见 ADR-0001):

- **op 粒度**(单 Operation)→ 本 skill(`sr-od-dev-write-operation`)。高频:写 / 改 / 修 op。
- **app 粒度**(整个 SrApplication 产品化:factory / config / GUI / run-record / app 级编排)→ `sr-od-dev-application`(待建)。
- **玩法粒度**(从零做新玩法的全程 pipeline)→ `od-dev-gameplay-automation`(已存在,瘦身为纯 pipeline)。

判单项归哪层,问:这是「单个 Operation 的写 / 改 / 修」,还是「整个 app 的搭 / 配 / 编排」,还是「从零做新玩法的全程」?

## 范围 IN(op 作者完整参考)

**mechanics**

- Operation 结构:`__init__`(ctx / op_name / node_max_retry_times / timeout_seconds / op_callback / need_check_game_win)、`handle_init` 生命周期
- 节点图:`@operation_node`(is_start_node / node_max_retry_times / screenshot_before_round / mute / save_status)、`@node_from`(from_name / status / success / ignore_status)、按 round 结果 + status 路由、自环陷阱、`previous_node` / `current_node`
- round 结果语义:`round_success` / `round_wait` / `round_retry` / `round_fail` 各自对节点图的影响(WAIT 重跑当前节点;RETRY 累计重试、超 max 转 FAIL;SUCCESS/FAIL 沿边找下一节点)+ status / data / wait / wait_round_time
- `round_by_*` 选型:`round_by_ocr` / `round_by_ocr_and_click` / `round_by_ocr_and_click_by_priority` / `round_by_find_area` / `round_by_find_and_click_area` / `round_by_goto_screen` / `round_by_click_area` + success_wait / retry_wait / lcs_percent / until_find_all / color_range / crop_first
- op 内工具:`screenshot()` / `last_screenshot`、`ctx.controller`(click / mouse_move / btn_tap / active_window)、`ctx.ocr`(get_ocr_result_list)、`save_screenshot()`
- 单 op 测试机制:`run_operation` 单跑、`add_mock_screenshot` 喂序列 fixture、刻画测试 vs TDD

**op 粒度规范(织入主线,非另开节)**

- 看 → 动 → 等 → 验 循环
- 每屏定识别方式(文字 → OCR / 固定 UI → screen_info / 动态稀有 → vision)+ OCR 关键词选画面独有(中文 LCS 误匹配坑)
- 建档前置:op 碰到的屏须先建档 → 引用 `od-dev-screen-onboarding`
- TDD + fixture 覆盖(每状态 1-2 张典型 fixture)
- 调试纪律:bot 卡住先读日志 → 不够就补日志 + 存图 → 结合玩法知识形成假设再验证
- 密集日志 + debug 截图(信息密度论:一次实跑暴露尽量多问题)
- 多样本核实 OCR / 读取器,不凭单点 / 单图下结论
- 预料外画面 → 调研"代码哪个动作交互进来" + 建档 + 改 click 避开误触元素
- 重复手动操作 2+ 次 → 建成 op
- bug#1 在 op 内形态(每 round `before_screenshot` 移鼠标 → 吞紧接 click;mouse_move + click 缓解;pre_delay / active_window 间隙)+ 框架陷阱(MCP click 异步需 sleep / ONNX 走 gpu_executor / 配置改了需重启 server 生效 / 录屏走 MCP 后端 / server 日志 UTF-8)

## 范围 OUT(指针,不重复)

- 从零做新玩法全程 → `od-dev-gameplay-automation`
- app 产品化(factory / config / GUI / run-record / app 级编排)→ `sr-od-dev-application`(待建;app 节点复用本 skill 的节点图机制,不重复讲)
- 建一张屏的机制(analyze → vision → doc → screen_info area → 存模板)→ `od-dev-screen-onboarding`
- 检测 / 验证 UI 区域坐标(槽位网格 / 图标阵列)→ `sr-od-dev-ui-region-detect`
- 通用 bug 定位 / 修复流程 → `superpowers:systematic-debugming` / `sr-od-dev-deciding-a-fix`(本 skill 只提供 op 领域知识,通用流程走它们)

## 构成(文件结构)

- `SKILL.md`:compact 核心 —— op 作者主线流程(写一个 op 的步骤)+ 选型判据 + 框架地基级接口名(`@operation_node` / `@node_from` / `round_by_*` / `controller` / `ocr` ...)。指令式(祈使句 + 判据),frontmatter description 只写触发。
- `references/`(progressive disclosure,情境细节 just-in-time,SKILL.md 引用):
  - `round-by-helpers.md`:`round_by_*` 家族逐个语义 + 何时用哪个 + 关键参数
  - `node-graph.md`:节点图机制 / 路由规则 / 自环陷阱 / `previous_node`
  - `testing.md`:单 op 测试机制 + TDD / fixture 策略
  - `framework-pitfalls.md`:bug#1 在 op 内形态 + 其他框架陷阱
- `design/`:本目录(overview + ADR)。

## 分阶段(phasing)

- **MVP(本步)**:建成 `sr-od-dev-write-operation`(SKILL.md + references + design),作 op 粒度规范的**新单一源**;在 `od-dev-gameplay-automation` 里把迁出的那几节(调试纪律 / 预料外画面 / 日志密度 / 重复手动建op / 证据纪律)替换为一行指针,避免双源。
- **Follow-up**:`od-dev-gameplay-automation` 全案瘦身(阶段 5/6 收窄成"策略 + 引用");建 `sr-od-dev-application`。

## 类型(RED / GREEN)

方法论覆盖型(整合 OneDragon op 开发已成型的实践 + 框架 API 成系统流程)→ RED 可省,**GREEN 必做**(方法见 `od-dev-writing-skills` 的 `references/skill-testing.md`:clean 工作空间 utility test + 可交互子 agent 做"给现有 app 写个新 op"任务 + 我扮用户只答所问 + 观察 gap + 修 + 循环)。

**状态:draft(GREEN-pending,2026-08-04)** —— 结构合规(od-dev-writing-skills 4 硬规范自检过),GREEN utility test 待跑。跑过 → 改 `validated`。
