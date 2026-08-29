---
gameplay_name: 邮件
app_id: email
last_updated: 2026-07-29
source: `application/email/` 代码 + phone_menu 邮件子态 area
involves_screens: [菜单]
---

# 邮件(email)

领取系统 / 活动邮件奖励(星琼 / 材料 / 活动发放)。日常收奖励。画面是 **phone_menu 子态**(无独立 screen)。

## 玩法机制

- 邮件:系统补偿 / 活动奖励 / 版本福利等,通过邮件发放。
- 一键全部领取。
- 手机菜单「邮件」入口。

## bot 流程(`application/email`)

`EmailApp` 领奖励流程:
- `open_menu`(开菜单 → 点「邮件」)→ `_click_email`(进邮件)。
- `_claim`(「全部领取」,`邮件-全部领取` area,见 [phone_menu](../screens/phone_menu.md))。
- `back_at_first` / `back_at_last`:首尾返回。

## 画面(独立屏「邮件」,游戏内标题「邮箱」)

2026-08-29 起有独立 screen 档(见 [screens/邮件](../screens/邮件.md));此前挂在 phone_menu 子态。要点:
- 识别锚:左上「邮箱」标题(独有 id_mark);全部领取按钮灰/实两态=可领判据。
- 历史 area `菜单/邮件-全部领取` 仍被 `email_app._claim` 使用,未迁移。
- 游戏机制(规则弹窗原文):收件箱上限 1000 封,超限自动删除无附件或附件已领的邮件;星标邮件不可一键删除(删除已读),可单封删除,过期自动消失。

## 备注 / 待查

- **已建档 fixture(2026-07-29;2026-08-29 整编)**:`screens/邮件/`(邮件列表-有可领 / 邮件列表 / 邮件列表-已领取)+
  `screens/菜单/`(菜单-邮件红点 / 菜单-无邮件红点)。原 `邮件/获得物品.webp` 系通用获得物品弹窗错档,
  已移 `screens/获得物品/邮件领取后.webp`(该弹窗画面待独立建档)。
  测试 `sr-od-test/test/sr_od/application/email/test_email_app.py`(节点级 4 场景:
  有/无红点 `_click_email` + 有/无可领 `_claim`)。
- **bot 仅领取**:`EmailApp` 一键全部领取(不删邮件 / 不处理特定邮件)。
- **邮件红点**:phone_menu 邮件图标 EMAILS template(右侧侧栏 `MENU_ITEMS_AT_RIGHT_PART`,
  center ~1867,272)+ `is_item_with_alert` 检测红点(alert)。
- **与无名勋礼 / 委托 并列**:都是 phone_menu 子态的领奖励 app(邮件 / 委托 / 无名勋礼),
  bot 模式相似(进子态 → 一键领取)。
