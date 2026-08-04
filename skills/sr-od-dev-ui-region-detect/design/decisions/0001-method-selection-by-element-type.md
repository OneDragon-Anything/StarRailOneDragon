# 0001. 检测方法按元素类型分流(vision/CV/OCR),非单一法

- **Status**: accepted
- **Date**: 2026-08-04

## Context

检测「画面上一组 UI 元素在哪」时,对所有元素硬套一种法会翻车:

- **稀疏 / 大 / 独特**元素(几个图标按钮、少量大卡槽):用传统 CV 反而多峰乱飘(Canny 边缘配对
  在槽间距小时把相邻槽并成一段)。
- **密集 / 规则网格**(一排很多小槽):用 vision(GLM-4.5V grounding)会漏检 / 错位 ——
  实测某备战栏 9 小槽 vision 只找到 7 个且第 3 个起错位 ~200px(受 32×32 patch 天花板限制)。
- **纯文字**:OCR(`analyze_screen` 的 `ocr_texts`)直接给 1080p 坐标,最省。

## Decision Drivers

- **对症**:不同元素类型有不同的失败模式,单一法覆盖不全。
- **鲁棒**:方法选择应基于可观察的元素特征(稀疏度 / 大小 / 是否等距 / 是否纯文字),而非
  硬编码某画面。
- **工具复用**:优先用框架已有能力(`analyze_screen` OCR、`mcp__4_5v_mcp__analyze_image`
  vision、OpenCV CV)。

## Considered Options

1. **单一 vision**:自由问坐标必幻觉;密集小元素漏检(见 Context)。
2. **单一 CV(投影峰值法)**:密集等距网格强,但大槽 + 复杂立绘内部多峰 → 稀疏大元素数量 /
   位置乱。
3. **按元素类型分流(选中)**:稀疏独特→vision(原生 grounding 格式)、密集规则网格→CV(投影
   峰值法)、带框/底色对比→CV(形状轮廓法,见 [ADR-0003](0003-squares-shape-detection.md))、
   纯文字→OCR。同一画面可混用(稀疏行 vision + 密集行 CV 是常态)。

## Decision

选 3:按可观察的元素特征分流方法。判据写进 `../../SKILL.md`「核心判据:vision vs CV,按元素
类型选」。一句话:**「稀疏独特找 vision,密集网格找 CV,文字找 OCR」**。

## Consequences

- **正向**:对症,覆盖稀疏 / 密集 / 带框 / 文字四类;同一画面混用是常态(不是二选一)。
- **负向**:agent 要先判元素类型再选法(多一步分类);vision 路径必须用模型原生 grounding
  格式(见 `../../SKILL.md` vision 段,否则幻觉)。
- **follow-up**:元素类型判据的阈值(如「≥ ~7 个算密集」「< ~50px 算小目标」)来自有限实测,
  跨项目可微调。

## Links

- `../../SKILL.md`「核心判据」段。
- 实测论据见 [`../detection-methods.md`](../detection-methods.md) 备战屏案例。
- 相关:[ADR-0003](0003-squares-shape-detection.md)(带框元素的 CV 形状法分流)。
