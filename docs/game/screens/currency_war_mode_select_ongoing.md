---
screen_name: 货币战争-模式选择-进行中
appears_in: [currency_war]
last_updated: 2026-11-19
source_image: screens/货币战争-模式选择-进行中/default.webp
---

# 货币战争-模式选择-进行中(挂起对局入口)

服务端存在挂起对局时,大厅点「开始」后落本屏:标准博弈卡带「进行中」分类与当前进度,底部出「结束并结算」「继续进度」双按钮。

## 何时出现 + 状态流转

- **入口**:货币战争-大厅 →「开始「货币战争」」(有挂起对局时)。
- **出口**:点「结束并结算」→ [货币战争-模式选择-结束结算确认](currency_war_giveup_confirm_popup.md);点「继续进度」→ 恢复进对局(自动化永不走此路——挂起局一律放弃,见 CwEntryExit docstring)。

## 识别特征(稳定锚点)

- id_mark 双锚(AND):「进行中」分类(左上,rect 位置绑定)+「结束并结算」按钮(底部右区)。
- 同族碰撞面:模拟宇宙-世界详情页有「结束并结算」同文按钮但无「进行中」分类,双锚凑不齐组合;sim 档的「通关可获得积分」锚 rect (1140,138)-(1420,185) 在本页无文字(fixture 碰撞扫描零命中实证)。
- 页头「货币战争 入画奇航」logo 与大厅锚「标识-玩法名」(text 货币战争) 不撞:锚 rect (50,80)-(170,118) 内落的是「入画奇航」残段,与「货币战争」零公共子序列。

## 可交互元素

- 「结束并结算」:底部右一,白色胶囊按钮。id_mark 兼点击区,点击出结束结算确认弹窗。
- 「继续进度」:底部右二。**自动化永不点击**(续跑语义,见上)——area 只建定位档留「可点控件」事实。
- 「对局记录」「职级奖励」:左下(bot 不操作)。

## 备注

- **screen_info 已建**(`currency_war_mode_select_ongoing`,2026-11-19):id_mark `标识-进行中` + `按钮-结束并结算`,普通区 `按钮-继续进度`;analyze_screen 三帧 is_precise 验证通过。
- 消费方:退出链 route ④b 显式点名(`cw_entry_exit.py` 模块常量 `MODE_ONGOING_SCREEN`)、入口链挂起分支(`cw_entry_start.py::CwEntryStart.MODE_ONGOING_SCREEN`)、返回大世界 op 同构点名分支。屏在 `cw_screen_state.LOBBY_STATE_SCREENS` 白名单内(入口可达非对局屏,对 `get_in_match_screen_name` 不可见)。
- fixture 已归档测试仓 `screens/货币战争-模式选择-进行中/`(default + default_b + default_c 三帧,test_id_mark 真阳性 + 零碰撞)。
