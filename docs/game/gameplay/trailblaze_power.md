---
gameplay_name: 开拓力玩法(体力)
app_id: trailblaze_power
last_updated: 2026-07-29
source: WebSearch 花萼攻略 + screen_info `calyx` + `application/trailblaze_power` 代码
involves_screens: [星际和平指南, 战斗画面, 副本连续挑战次数, 模拟宇宙, 饰品提取]
---

# 开拓力玩法(trailblaze_power)

消耗开拓力(体力)刷材料的玩法总称。`TrailblazePowerApp` 按用户计划(power_config)调度子玩法:**花萼**(经验 / 晋升材料)/ **历战余响**(周本)/ **饰品提取**(遗器)/ **模拟宇宙**(Roguelike)。

## 玩法机制(攻略)

- **开拓力**(体力):随时间恢复 + 后备开拓力(额外储存)。消耗刷材料,勿溢出。
- **子玩法**:
  - **拟造花萼(金)**:角色经验书 / 光锥经验 / 信用点 / 行迹材料。
  - **拟造花萼(赤)**:角色晋升 / 突破 / 命途材料。
  - **历战余响**(echo_of_war):周本(每周限次,行迹材料)。
  - **饰品提取**(ornamenet_extraction):遗器(可指定预言 / 套装)。
  - **模拟宇宙**(sim_universe):Roguelike(见 [sim_uni](sim_uni.md))。
- **入口**:右上方指南 → 生存索引 → 传送对应玩法点(花萼/历战/饰品点)。
- **双倍活动**:花藏繁生(双倍花萼奖励)。
- **体力规划优先级**:角色突破材料 > 光锥 / 行迹 > 信用点 / 经验书 > 均衡 5 后集中刷遗器。

## bot 流程(`application/trailblaze_power`)

`TrailblazePowerApp` 调度:
- `check_task`(检查计划)→ `open_guide`(开指南)→ `execute_plan`(按计划跑)。
- `power_config.check_plan_run_times`(计划次数 / 体力核算)。
- 按 `mission`(每个 mission 有 `power` 体力消耗)→ `can_run_times = power // mission.power` → 跑(`sim_uni` / `ornamenet_extraction` / guide mission 战斗)。
- 战斗后领奖励,更新 `run_times`,直到达 `plan_times` 或体力耗尽。

## 子玩法 app

- **模拟宇宙** `sim_universe`(见 [sim_uni](sim_uni.md))。
- **饰品提取** `ornamenet_extraction`(div_uni app,见 [ornamenet_extraction](../screens/ornamenet_extraction.md) screen)。
- **花萼 / 历战**:via guide(指南传送 + 大世界战斗 + `calyx` 次数输入)。

## 画面

- **calyx(副本连续挑战次数)** screen_info(`pc_alt=false`,2 area):文本-挑战次数-饰品提取 / 其他 —— 连续挑战 N 次的次数输入画面(花萼 / 饰品等连续挑战)。
- 各子玩法画面:花萼(大世界传送点 + 战斗)、历战(战斗)、饰品提取(`ornamenet_extraction` screen)、模拟宇宙(`sim_uni`)。

## 备注 / 待查

- **待实拍画面 + vision**:花萼 / 历战 / 饰品战斗画面 + `calyx` 次数输入态实拍归档 + vision(消耗体力,待用户配合切画面)。
- **trailblaze_power 计划配置**:`power_config`(plan_times / run_times / mission)—— 用户在 GUI 配计划,bot 按计划跑;配置结构待 `describe_config(trailblaze_power)` 细化。
- **guide 传送**:各玩法入口经「星际和平指南」传送 —— Transport 失败多为地图未探索 / 传送点未解锁(screen-onboarding「Transport 失败排查」)。
- **历战余响** echo_of_war 有独立 app(`application/echo_of_war`)+ `echo_of_war_config`,周限,待补 doc。

## 参考来源

- [4399 体力规划指南](https://a.4399.cn/gl/38935068_217170.html)
- [游民星空 双倍花萼规划](https://www.gamersky.com/handbook/202307/1616859.shtml)
- [Gachia 开拓力规划](https://gachia.com/zh/starrail/guides/trailblaze-power-guide)
- [米游社 花藏繁生](https://www.miyoushe.com/sr/wiki/content/5565/detail)
