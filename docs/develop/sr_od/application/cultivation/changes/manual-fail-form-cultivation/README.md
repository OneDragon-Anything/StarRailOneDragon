# 光锥/角色手动路径失败形态适配（外溢迭代·占位）

## 承接出处
- 源迭代：`docs/develop/sr_od/application/echo_of_war/changes/weekly-challenge-core/`（design.md §1「明确不解决」+ details/fail-form-adaptation.md 关键取舍）
- 裁定：光锥/角色手动路径的失败分支不并入源迭代（养线已验证 op，回家链各异，改动面与验证面自成闭环）

## 范围（一句话）
`UpgradeLightConeOp` 与 `UpgradeCharacterOp` 手动刷取路径的失败消费点接入共享失败继续件 `ResumeFromBattleFail`（challenge_mission 包，源迭代 3.1 落地后可用），并核定各自失败后的回家链（光锥/角色各自的资源窗口/详情页落点未实测，落地前先补实测）。

## 状态

已并入迭代 `cultivation/changes/upgrade-ops-adaptation/`（块 B/C，details/fail-adaptation.md §2/§3——设计期核实：角色线手动路线战斗循环在 manual_fight/back_to_ascend，光锥线在 手动挑战战斗/back_after_farm，两线失败画面均无分支）。本占位不再单独立项。

落地落点：主仓 `eeda21c42`（两线失败分支 + 内联预算检查 + 重发回链）、测试仓 `55174271`（mock 十场景）。
