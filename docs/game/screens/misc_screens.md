---
gameplay_name: 其他画面总览(common / catapult / fast_recover_dialog)
last_updated: 2026-07-29
source: screen_info `common` / `catapult` / `fast_recover_dialog`
---

# 其他画面总览

未归入主流程的 3 个小画面:通用对话框、弹珠机活动、快速恢复对话框。

## common(通用画面)

`pc_alt=false`,2 area。**通用对话框 / 弹窗兜底画面**(各处确认弹窗)。
- 左上角标题(标题区)。
- 对话框-确认(通用确认按钮)。
- 用途:各处确认弹窗(无固定文字特征,靠结构 —— 见 screen-onboarding「兜底画面」)。

## catapult(弹珠机)

`pc_alt=false`,5 area。**弹珠机 / 弹射玩法**(活动)。
- 移动交互-单行(交互提示)。
- 离开按钮、弹射(操作)、DIALOG_CONFIRM、退出对话框-确认。
- 用途:弹珠机活动(弹射操作),可能是版本活动玩法。

## fast_recover_dialog(快速恢复对话框)

`pc_alt=false`,5 area。**快速恢复开拓力**(用奇巧零食等消耗品补体力)。
- 快速恢复标题、确认、取消。
- 暂无可用消耗品(无零食提示)。
- 奇巧零食(消耗品选项)。
- 用途:体力不足时,用奇巧零食快速恢复开拓力(关联 [trailblaze_power](../gameplay/trailblaze_power.md) 体力 + [trick_snack](../gameplay/misc_apps.md) 零食)。

## 备注 / 待查

- **common 兜底**:通用对话框无固定特征,靠结构(标题+确认)识别 —— 各处确认弹窗复用。
- **catapult 弹珠机**:活动玩法,bot 是否覆盖待确认(可能是版本限时活动)。
- **fast_recover 与零食**:快速恢复用奇巧零食(奇巧零食由 [trick_snack](../gameplay/misc_apps.md) app 购买 / 合成),体力不足时补。
- **待实拍 + vision**:3 画面实拍归档(通用对话框 / 弹珠机 / 快速恢复弹窗)。
