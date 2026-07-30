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

- **星际和平指南-每日实训**(复用 [guide](guide.md),每日实训 TAB 的子态):
  - 顶部活跃度奖励轨:0 / 100 / 200 / 300 / 400 / 500 档,每档「活跃度」奖励(星琼 / 材料),可领显「领取」、未达显「进行中」、可前往显「前往」;领完用 `training_reward_completed` 模板标记。
  - 下方 4 个每日实训任务(如「累计消耗开拓力」「消灭敌人」「支援角色战斗胜利」「万能合成机」),各带 `进度 X/Y`;右下「刷新时间」每日重置。
  - 左上角标题:首行「星际和平指南」+ 次行「每日实训」(`in_secondary_ui('指南' / '每日实训')` 判定所在页)。
  - fixture:`screens/星际和平指南/每日实训.webp`(每日实训 tab,1 个 120/120 完成 + 1 个可领 + 余进行中)。
- 奖励领取位置:`phone_menu_utils.get_training_reward_claim_btn_pos`(裁 `GUIDE_TRAINING_REWARD_CLAIM_RECT` 匹配 `training_reward_gift`)、领完判定 `is_training_reward_completed`(同区匹配 `training_reward_completed` ≥5 个)。

## 备注 / 待查

- **bot 仅领奖励**:每日实训任务靠日常玩法推进(战斗 / 委托等),bot 领已达标的活跃度 / 奖励(`claim_score` 领活跃度、`claim_reward` 领档位奖励)。
- **指南 TAB 导航**:每日实训在指南 TAB(与生存索引 / 逐光捡金并列)。
- **测试**:`sr-od-test/test/sr_od/application/daily_training/test_daily_training_app.py` —— 奖励提取管线 + 画面态(`in_secondary_ui`)测试;消耗型领奖节点不 mock(需 running 状态)。
