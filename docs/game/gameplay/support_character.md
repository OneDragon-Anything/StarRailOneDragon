---
gameplay_name: 支援角色(漫游签证)
app_id: support_character
last_updated: 2026-07-29
source: `application/support_character/` 代码(op_name「支援角色奖励」)+ phone_menu 省略号/漫游签证 area
involves_screens: [菜单]
---

# 支援角色 / 漫游签证(support_character)

漫游签证系统:借好友角色(支援)+ 每天收信用点奖励。bot 收支援奖励(op_name「支援角色奖励」)。画面在 **phone_menu 省略号子菜单**(无独立 screen)。

## 玩法机制

- **漫游签证**:借好友角色作支援(每天),收取支援奖励(信用点)。
- 入口:手机菜单 → 省略号(更多)→ 漫游签证。
- 有奖励时(STATUS_WITH_ALERT 红点)→ 点角色领;无奖励(STATUS_NO_ALERT)→ 跳过。

## bot 流程(`application/support_character`)

`SupportCharacterApp`(支援角色奖励):
- `open_menu`(开菜单)→ `_click_ellipsis`(点省略号 `phone_menu_utils.get_phone_menu_ellipsis_pos`)。
- `_click_profile`(点「漫游签证」`get_phone_menu_ellipsis_item_pos`)。
- 有红点(`STATUS_WITH_ALERT`)→ `_click_character`(点角色领奖励)。
- 无红点(`STATUS_NO_ALERT`)→ `back_at_last`(返回,无奖励可领)。

## 画面(phone_menu 省略号子菜单)

无独立 screen —— 漫游签证 UI 在 phone_menu 省略号(更多)展开的子菜单:
- 省略号入口(`ui_ellipsis` template,`phone_menu_utils.get_phone_menu_ellipsis_pos`)。
- 漫游签证项(`get_phone_menu_ellipsis_item_pos('漫游签证')`,OCR 匹配项名)。
- 角色卡片 / 红点(alert 检测 `ui_alert` template)。
- **漫游签证面板**(进入后):角色展示 tab —— 个人资料(昵称 / UID / 开拓等级 / 生日)+ **支援角色**栏(3 个借出角色,如飞霄 / 遐蝶 / 黄泉,等级 80)+ 战绩 / 收集展示 tab + 漫游动态。bot 的 `_click_character` 点 `Point(1862,358)` 领支援奖励。
- **fixture**:`screens/漫游签证/角色展示.webp`(角色展示 tab,支援角色 飞霄 / 遐蝶 / 黄泉,无红点态)。

## 备注 / 待查

- **已采(2026-07-29)**:漫游签证面板(角色展示 tab)实拍归档(见上 fixture);**红点可领态**(`STATUS_WITH_ALERT`)待有奖励时实拍。
- **bot 仅领奖励**:`SupportCharacterApp` 收支援奖励(不借角色本身,借角色在编队时 `team` 画面支援态处理)。
- **漫游签证 vs 编队支援**:本 app 收漫游签证奖励(信用点);编队时借好友角色(SUPPORT_BTN in [team](../screens/team.md))是另一回事。
- **红点检测**:`ui_alert` template 检测省略号/漫游签证红点(有奖励),`STATUS_WITH_ALERT`/`NO_ALERT` 分支。
