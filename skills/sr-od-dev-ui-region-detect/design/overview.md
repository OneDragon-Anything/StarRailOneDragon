# sr-od-dev-ui-region-detect · 设计概览(what)

## 为什么做

自动化一个游戏玩法,绕不开「画面上一组 UI 元素在哪」:槽位网格、图标按钮、卡牌阵列。
两种常见翻车:

1. **直接问 vision「坐标多少」** → 自由问坐标必幻觉(全图偏几百 px),因为没用模型原生
   grounding 格式。
2. **对所有元素硬套一种法** → 稀疏元素用 CV 多峰乱飘、密集网格用 vision 漏检。

本 skill 把「按元素类型选 vision/CV/OCR + 密集网格的 CV 投影峰值法 + 带框元素的形状轮廓法
+ 数值验证」固化成方法论,避免每次重新踩坑。

## 定位与边界

- **定位**:`sr-od-dev-screen-onboarding` 的**补充**。onboarding 管画面**建档**全流程
  (analyze → vision 理解 → 写 doc → 建模入 screen_info);本 skill 只管**「检测 / 验证坐标」
  的方法选型与纪律**(vision vs CV vs OCR 判据 + 密集网格投影峰值法 + 带框元素形状轮廓法 +
  数值验证)。
- **建模入 screen_info**(`upsert_screen_area` 等)仍走 onboarding skill,本 skill 不重复。
- **不记任何具体游戏坐标 / 键位 / 机制**(那归 doc);SKILL.md 正文只写方法 / 判据
  (见 `sr-od-dev-skill-guide` 硬规范 4)。具体项目案例 / 实测数据只在本 `design/` 内作决策论据。
- **自包含**:GLM-4.5V grounding 格式细节内联 SKILL.md(不外引个人 `.claude/` 文件 —— skill 入库
  共享,`.claude/` 不在库)。

## 构成

- `SKILL.md` —— 智能体指令:核心判据(vision/CV/OCR 按元素类型选)+ vision 原生 grounding
  格式 + CV 投影峰值法 + CV 形状轮廓法 + 数值验证纪律。
- `detect_grid.py` —— 密集规则网格槽位检测的可复用 CV 实现(逐列标准差 + 峰值 NMS),
  `detect_grid_row(img, y1, y2, x1, x2, slot_w) -> list[int]`。
- `design/` —— 本目录:设计 + 决策存档(给维护者,不进 agent 上下文)。

## 何时根本不需要运行时检测

screen_info 已有 `pc_rect`(建档时圈好)→ 自动化**直接用坐标**,不运行时检测。本 skill 的检测
方法主要用于:**建档阶段定位坐标**、**验证已圈坐标是否随版本漂移**、**定位 screen_info 未覆盖
的动态元素**(如刷新的商店内容)。别为了「全自动」在运行时重检测已有 screen_info 的元素
(多此一举且更脆)。

## 决策一览(各条 why 见 `decisions/` 对应 ADR)

| 决策 | 摘要 | ADR |
|------|------|-----|
| 方法按元素类型分流 | 稀疏独特→vision、密集网格→CV、文字→OCR,非单一法 | [0001](decisions/0001-method-selection-by-element-type.md) |
| 验证用数值对拍 | ground truth 数值差为准,不用 vision 当裁判 | [0002](decisions/0002-numeric-verification-not-vision-judge.md) |
| 矩形阵列用 squares | 几何判矩形(免疫颜色变化),非颜色阈值/背景互补 | [0003](decisions/0003-squares-shape-detection.md) |
| vision 颜色不可信精确值 | 定性描述可用,精确阈值/RGB 由 CV 采样定 | [0004](decisions/0004-vision-color-unreliable.md) |

CV 投影法的**信号 / 参数选择**(标准差 vs 框色、平滑核、阈值)属调参级实现论据,不配 ADR,
见 [`detection-methods.md`](detection-methods.md)。
