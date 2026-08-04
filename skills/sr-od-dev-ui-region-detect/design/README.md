# sr-od-dev-ui-region-detect · 设计文档索引

本 skill 的设计存档(**给后续维护者,不进智能体执行上下文**)。使用信息(方法选型 / 步骤 /
判据)全在 `../SKILL.md`,智能体不需要读本目录;这里只记「为什么这么定」+ 方法参数依据。

- [`overview.md`](overview.md) —— 定位 / 边界 / 构成 / 复用产物(what)。
- [`detection-methods.md`](detection-methods.md) —— CV 投影峰值法的信号 / 参数选择依据 + 踩坑
  (调参级实现论据,不配 ADR;步骤见 `../SKILL.md`,这里只记「为什么这些参数」)。
- `decisions/` —— 架构级决策(ADR,arc42 §9 = why):
  - [INDEX](decisions/INDEX.md)
  - [0001 检测方法按元素类型分流(vision/CV/OCR),非单一法](decisions/0001-method-selection-by-element-type.md)
  - [0002 验证用数值对拍 ground truth,不用 vision 当裁判](decisions/0002-numeric-verification-not-vision-judge.md)
  - [0003 矩形/卡牌阵列用 squares 几何检测(免疫颜色变化)](decisions/0003-squares-shape-detection.md)
  - [0004 vision 颜色不可信精确值,定性可用 + CV 采样定准值](decisions/0004-vision-color-unreliable.md)

> 迁移自旧版单文件 `design.md`(混合 design+decision);按 `sr-od-dev-skill-guide` 硬规范 1 拆分。
