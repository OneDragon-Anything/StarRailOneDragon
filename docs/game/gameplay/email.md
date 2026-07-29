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

## 画面(phone_menu 邮件子态)

无独立 screen —— 邮件 UI 在 phone_menu 弹窗态:
- `邮件-全部领取`(text "全部领取",一键领取所有邮件附件)。
- 邮件列表 / 附件展示(OCR 动态,无固定 area)。

## 备注 / 待查

- **已建档 fixture(2026-07-29)**:`screens/邮件/`(邮件列表-有可领 / 邮件列表-无可领 /
  获得物品弹窗)+ `screens/菜单/`(菜单-邮件红点 / 菜单-无邮件红点)。
  测试 `sr-od-test/test/sr_od/application/email/test_email_app.py`(节点级 4 场景:
  有/无红点 `_click_email` + 有/无可领 `_claim`)。
- **bot 仅领取**:`EmailApp` 一键全部领取(不删邮件 / 不处理特定邮件)。
- **邮件红点**:phone_menu 邮件图标 EMAILS template(右侧侧栏 `MENU_ITEMS_AT_RIGHT_PART`,
  center ~1867,272)+ `is_item_with_alert` 检测红点(alert)。
- **与无名勋礼 / 委托 并列**:都是 phone_menu 子态的领奖励 app(邮件 / 委托 / 无名勋礼),
  bot 模式相似(进子态 → 一键领取)。
