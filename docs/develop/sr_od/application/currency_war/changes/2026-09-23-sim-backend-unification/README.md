# 2026-09-23-sim-backend-unification

> sim 统一：sim 重构为游戏后端（SimBackend），真流程在其上跑通一局。投资效果逻辑计算迭代（进度树 `2026-09-23-invest-effects-calc`）登记的前置。

## 文档

- 设计总纲：[design.md](design.md)
- 详设：[details/sim-backend.md](details/sim-backend.md) —— 世界模拟 / 画面状态机 / overlay 触发层 / 字段收敛 / 旧引擎退役
- 详设：[details/flow-seam.md](details/flow-seam.md) —— 端口模块 / CwOperation 覆写面 / 生成器 / 运行器与桩 / 测试迁移
- 落地：[landing.md](landing.md)

## 进度

- 迭代设计：定稿
- 设计对抗：收敛 · 报告=[attack.md](attack.md)（16 发现已修复；定稿复核通过；T-6/T-8/T-9/T-10 各轮验收新问题已全部立项消化或归例行注释卫生清单）
- 落地：10/10 done（T-1 接缝基建 / T-2 SimBackend 核心 / T-3 金路径生成器 / T-4 首局验收(MVP 四条尺全绿) / T-5 正本更新 / T-6 时序扫尾 / T-7 多种子完备性 / T-8 正本 token 扫尾 / T-9 src 注释层扫尾 / T-10 注释卫生收口；明细见 landing.md 与 reports/）
- 正本更新：清零
