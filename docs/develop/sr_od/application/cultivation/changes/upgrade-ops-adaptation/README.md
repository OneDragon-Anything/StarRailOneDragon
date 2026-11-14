# 升级 op 失败适配与行迹重构（迭代目录）

## 状态

**设计稿 v1，对抗审进行中**——收敛后交负责人批准，批准前不开工。

## 一句话

升级 op 家族的战斗循环全部接入共享失败继续件 `ResumeFromBattleFail`（weekly-challenge-core 3.1 落地）收口失败形态卡死风险；`UpgradeTraceOp` 按负责人裁定重构为面板态契约（agent 选节点）。

## 块

- 块 A：`UseTrailblazePower` 失败适配 + 迁移开拓力 app → details/fail-adaptation.md §1（占位 `trailblaze_power/changes/use-trailblaze-power-rehome/` 转正）
- 块 B：角色线手动路线失败适配 → details/fail-adaptation.md §2（占位 `cultivation/changes/manual-fail-form-cultivation/` 转正）
- 块 C：光锥线手动路线失败适配 → details/fail-adaptation.md §3（同上占位）
- 块 D：`UpgradeTraceOp` 面板态重构 → details/trace-rework.md（占位 `cultivation/changes/trace-upgrade-rework/` 转正）

## 文件

- design.md——总纲（背景/范围/方案概览/明确不解决/外溢面）
- details/fail-adaptation.md——块 A/B/C 节点卡级详设
- details/trace-rework.md——块 D 节点卡级详设
- landing.md——落地四阶段 + 完成判据 + 正本更新清单
- attack.md——对抗记录（对抗轮次后补）
