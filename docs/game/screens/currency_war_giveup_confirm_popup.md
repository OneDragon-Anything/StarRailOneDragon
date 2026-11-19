---
screen_name: 货币战争-模式选择-结束结算确认
appears_in: [currency_war]
last_updated: 2026-11-19
source_image: screens/货币战争-模式选择-结束结算确认/default.webp
---

# 货币战争-模式选择-结束结算确认(放弃挂起局确认弹窗)

模式选择-进行中屏点「结束并结算」后的确认弹窗:提示放弃将直接结算并重置进度,列出当前进度/小队生命值/持有金币/晋升点。

## 何时出现 + 状态流转

- **入口**:[货币战争-模式选择-进行中](currency_war_mode_select_ongoing.md) →「结束并结算」。
- **出口**:点「放弃并结算」→ 货币战争-挑战失败(跳过对局内前半段退出链,直接进结算尾段);点右上角 X 关闭 → 留在挂起态(取消语义,自动化无消费方)。

## 识别特征(稳定锚点)

- id_mark 双锚(AND):「确定结束进程吗」确认文案 +「放弃并结算」按钮。
- 与通用「提示」弹窗族(战斗-退出确认弹窗等)同构但文案/位置独立,fixture 碰撞扫描零命中。

## 可交互元素

- 「放弃并结算」:底部中央,带 X 图标的白色胶囊按钮。id_mark 兼点击区,点击进挑战失败演出。
- 右上角 X 关闭钮:纯图形无文字(no_method 定位区),坐标 (1440,320)-(1484,364) 经裁剪回读校准(2026-11-19)。无生产消费方(取消 = 留在挂起态),area 在档备用。

## 备注

- **screen_info 已建**(`currency_war_giveup_confirm_popup`,建档 2026-11-19 实机走查,关闭钮坐标同年校准):id_mark `标识-确认文案` + `按钮-放弃并结算`,普通区 `按钮-关闭`。
- 消费方:退出链 route ④b 显式点名(`cw_entry_exit.py` 模块常量 `GIVEUP_CONFIRM_SCREEN`)+ `giveup_confirm` 节点点「放弃并结算」;入口链挂起分支与返回大世界 op 的点名集合同含本屏。屏在 `cw_screen_state.LOBBY_STATE_SCREENS` 白名单内。
- fixture 已归档测试仓 `screens/货币战争-模式选择-结束结算确认/default.webp`(test_id_mark 真阳性 + 零碰撞)。
