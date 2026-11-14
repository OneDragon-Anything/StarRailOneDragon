# 光锥/角色手动路径失败形态适配（外溢迭代·占位）

## 承接出处
- 源迭代：`docs/develop/sr_od/application/echo_of_war/changes/weekly-challenge-core/`（design.md §1「明确不解决」+ details/fail-form-adaptation.md 关键取舍）
- 裁定：光锥/角色手动路径的失败分支不并入源迭代（养线已验证 op，回家链各异，改动面与验证面自成闭环）

## 范围（一句话）
`UpgradeLightConeOp` 与 `UpgradeCharacterOp` 手动刷取路径的失败消费点接入共享失败继续件 `ResumeFromBattleFail`（challenge_mission 包，源迭代 3.1 落地后可用），并核定各自失败后的回家链（光锥/角色各自的资源窗口/详情页落点未实测，落地前先补实测）。

## 状态
未立项（占位）。现状风险：两 op 失败后找不存在的按钮无限重试，靠 op 级重试/看门狗兜底。
