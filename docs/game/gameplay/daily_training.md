---
gameplay_name: 每日实训
app_id: daily_training
last_updated: 2026-07-29
source: `application/daily_training/` 代码(op_name「每日实训」)+ guide 每日实训 TAB
involves_screens: [星际和平指南]
---

# 每日实训(daily_training)

每日任务系统,完成日常活动(战斗 / 玩法)积累实训积分,领奖励。日常必做。入口:**星际和平指南 → 每日实训 TAB**(见 [guide](guide.md))。

## 玩法机制

- **每日实训**:每日任务(完成各活动积累积分),积分达标领奖励(星琼 / 材料)。
- 每日刷新。
- 入口:指南「每日实训」TAB。

## bot 流程(`application/daily_training`)

`DailyTrainingApp`(每日实训):
- `open_menu` → `click_guide`(开指南)→ `guide_choose_tab`(选「每日实训」TAB,`guide_data.best_match_tab_by_name`)。
- `claim_score`(领积分)→ `claim_reward`(领奖励,`phone_menu_utils` training_reward)。
- `in_secondary_ui('指南'/'每日实训')`(验证在指南每日实训页)。

## 画面

- **guide 每日实训 TAB**(`guide` screen,TAB-每日实训,见 [guide](guide.md))。
- 训练奖励领取(`phone_menu_utils.is_training_reward_completed` / `get_training_reward_claim_btn_pos`)。
- 无独立 screen —— 复用 guide。

## 备注 / 待查

- **待实拍 + vision**:每日实训 TAB + 积分 + 奖励领取态实拍归档。
- **bot 仅领奖励**:每日实训任务靠日常玩法推进(战斗 / 委托等),bot 领已达标的积分 / 奖励。
- **指南 TAB 导航**:每日实训在指南 TAB(与生存索引 / 逐光捡金并列)。
