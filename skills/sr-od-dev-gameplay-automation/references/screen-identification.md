# 画面建档深度细则(阶段 3)

> 本文件是 SKILL.md 阶段 3 的 situational 深度细则。画面建档是自动化核心环节时按需读。
> 配合协作 skill `sr-od-dev-screen-onboarding`(analyze→vision→doc→缺口→建模→归档)与 `sr-od-dev-ui-region-detect`(坐标检测)。

## 识别优先级(判定"当前在哪个画面")

1. **文字 → OCR**(`analyze_screen` 的 `ocr_texts`,1080p 直出坐标)。OCR 关键词**选画面独有的**,别用会出现在多个画面的子串。
2. **固定 UI 元素 → screen_info**(写 `assets/game_data/screen_info/<screen>.yml`,pc_rect 坐标)。坐标怎么来见 `sr-od-dev-ui-region-detect`(稀疏独特找 vision、密集网格投影找 CV、文字找 OCR;vision 必须用原生 grounding 格式)。
3. **状态/选中/计数 → vision 兜底**,但 vision 的状态推理不可信,只信客观描述;坐标对错用数值对拍 ground truth(别用 vision 当裁判)。

## 中文关键词 LCS 误匹配(判据 + 修法)

框架 `round_by_ocr` 默认 `lcs_percent=0.5`(LCS 最长公共子序列 / 目标长度 ≥ 阈值)。**中文关键词若与别的画面文字共享 2+ 字子串,就会在 0.5 误匹配** —— 不是"子串包含",是"子序列比例"。

- **症状**:loop 卡在某屏 round_wait 循环、handler 不触发(日志无子 op 执行)、或派发到错误 handler。
- **判据**:卡死 + OCR 明明有关键词但 handler 不跑 → 查 `round_by_ocr` 关键词是否与同屏/邻屏文字共享 2+ 字。
- **修(两档)**:
  1. **快速止血**:该 `round_by_ocr` / `round_by_ocr_and_click` 传 `lcs_percent=0.7~0.9`(真匹配 1.0 不受影响,假匹配 0.5 被杀);或用更长/更独有关键词(如全标题)。
  2. **根因解(推荐)**:**用固定位置识别** —— 关键词只在它**固定的画面位置**识别(screen_info 建 area 圈定该位置,不全文扫),从源头避免与画面其他位置的同类文字冲突。全屏 `round_by_ocr`(loose 全文匹配)天生易冲突;固定位置 screen_info area 检测(bound 到位置)才稳。
- **别只改一个就收工** —— 同 loop 里所有中文关键词都可能踩,逐个审共享子串;长期把派发检测迁到 screen_info area(固定位置)。LCS 误匹配本质 = 全屏匹配撞同类元素;固定位置是根治。

## 建档只写 docs + screen_info,别改原内容

`pc_rect` 占位是**待填**不是坏数据 —— 画面/玩法建档只写 docs/game 的 doc + 新增 area,不动 screen_info 已有内容(详见 `sr-od-dev-screen-onboarding`)。

## 每个状态都建档 + 存 fixture(防回归地基)

早期接触玩法**很多画面没见过** —— 每碰到一个新状态就:① 截代表图存 fixture(项目 test 目录 / `.debug/`);② screen_info 建该画面 area;③ 写针对该 fixture 的测试。

**别凭 1-2 张图写整个流程** —— 一个流程通常有多种状态(不同子界面/事件选项/阶段切换/结算页…),只见过一两种就下结论/写代码,必然漏状态、回归不断。不认识的画面别猜,先 `analyze_screen` + vision 看清(vision 取坐标必须用原生 grounding 格式,方法见 `sr-od-dev-ui-region-detect`)。
