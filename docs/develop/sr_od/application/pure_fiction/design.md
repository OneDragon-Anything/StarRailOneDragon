# 虚构叙事独立应用（as-built 设计正文）

> 本文是 `pure_fiction` 应用的正本设计（as-built），与代码现状一致。过程见 `changes/`。

## 1. 定位与边界

- 逐光捡金·虚构叙事的一键挑战独立应用：`run_standalone_app(app_id='pure_fiction')`，主界面起、大世界收，单次运行挑战**关卡01**一次（最高已解锁关卡的选关 area 仅建模 01）。
- 不进一条龙、无 GUI、无通知；选人随机占位（接缝 = 共享 `treasures_lightward/random_team.py`）。
- 明确不做：关卡选择、领奖段（期次奖励领取 op 未建模，挂账）、星数检测、忘却之庭 app（未启动）。

## 2. 结构

包 `src/sr_od/application/pure_fiction/` 六件套，形态与末日幻影 app 一致（const/config/run_record/factory/app；config 仅 `character_pool`，config_router 不设条目——无 settable 字段）。复用件：`GotoTreasuresLightward(PURE_FICTION)`、`TlPureFictionChallengeOp`（fill/equip/battle）、`BackToNormalWorldPlus`。

## 3. 节点图（四段式）

```
① 前往虚构叙事(start) = GotoTreasuresLightward(PURE_FICTION)（新期开场页由其收尾节点处理）
② 进编队屏            = 选关点「纸鹤-关卡01」→ 虚构叙事-编队双锚 until；已在编队屏短路
   随机选人           = ∩CHARACTER_LIST → random_team.pick_random_teams(8)
   执行挑战           = TlPureFictionChallengeOp(team_names, buff_slot=1, buff_slots=[1,1])，带换人重选(预算 初选+2)
③ 领奖段 无（挂账）
④ 返回大世界          = BackToNormalWorldPlus
```

## 4. 失败处理语义

同末日幻影 app（AS 正本 §4）：导航/进编队屏失败中止；「列表到底未找到 X」剔除重选（PF 填充失败文案与 AS 同款）；其余挑战失败中止；返回失败中止。

## 5. 已知边界

- 组合 op 不做选关→编队屏导航（前置校验制）——「进编队屏」由本 app 节点承担（与 AS 同款战术权衡：分支语义与 ops 侧同步维护义务；根治 = 抽「进入逐光捡金编队屏」族 op）。
- 随机队战斗完成度：PF 为群怪击杀计分，随机队可完成战斗但分数低（周期制自然收束）；实测口径见 changes 迭代核销表。
- 中断恢复：同 AS（游戏重启恢复到挑战中画面时，先 BackToNormalWorldPlus 收回大世界）。
