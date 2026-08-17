---
screen_id: currency_war_wish_trial
screen_name: 货币战争-祈愿试炼
source_image: screens/货币战争-祈愿试炼/祈愿试炼.webp
---

# 货币战争-祈愿试炼

## 何时出现

节点级 quest 选择 overlay(特定节点前,如「再临仪式-二」「遭遇战」;随机出现——命运圣杯等投资策略绑定)。叠在备战上,**挡备战分支**(2026-08-08 实跑:bot 卡此 overlay 68min)。

## 状态流转

- 入口:特定节点前自动弹出(「选择1个祈愿试炼,完成后可获取祈愿奖励」)。
- 出口:点试炼卡身(选中,金框+「确认选择」亮)→ 确认选择 → 关回备战。
- **ESC 不关**(2026-08-08 实测)。

## 识别特征

- id_mark:`标识-祈愿试炼`(920,45-1130,105,lcs 0.5)。标题 top-center。

## 可交互元素

| 元素 | 位置 | 行为 |
|---|---|---|
| 试炼卡 1 body | (660,340)(HandleWishTrial.FIRST_CARD) | 选中第 1 张(MVP;候选卡数随节点变) |
| 按钮-确认选择 | (1448,625 附近) | 确认后关 overlay 回备战 |

## automation 要读信息

- 三张卡名 + objective/reward 文本(y 310-470 带)——策略化选卡(TODO:易完成度/契合 comp;现固定第 1 张)。

## 识别快照

- fixture:`screens/货币战争-祈愿试炼/祈愿试炼.webp`(2026-08-13 采)。
- handler:HandleWishTrial(D-87~89 闭环,2026-08-08 live 验证)。
