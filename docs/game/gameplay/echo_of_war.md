---
gameplay_name: 历战余响(周本)
app_id: echo_of_war
last_updated: 2026-07-29
source: WebSearch 攻略 + `application/echo_of_war/` 代码
involves_screens: [星际和平指南, 战斗画面]
---

# 历战余响(echo_of_war)

周常副本(周本),角色行迹高级材料的核心来源。每周 3 次(周一刷新),每次消耗 30 开拓力;3 次后可免体力进入(刷成就 / 支援)。是 [开拓力玩法](trailblaze_power.md) 的子玩法(周限)。

## 玩法机制(攻略)

- **周本**:每周挑战 **3 次**(周一刷新),每次 **30 开拓力**。
- **解锁**:开拓等级 26 + 雅利洛-VI 主线。
- **难度**:最高 VI(随均衡等级解锁,均衡 6 全解锁);随均衡等级掉落提升。
- **3 次后**:可免体力进入(刷成就 / 组队支援,无奖励)。
- **奖励**:行迹高级材料(核心)+ 遗器 + 光锥 + 流光余晖。
- 建议:留到周日打最高难度(性价比高)。
- 入口:指南 → 生存索引 → 历战余响传送。

## bot 流程(`application/echo_of_war`)

`EchoOfWarApp`(历战余响):
- `check_task`(检查周任务:本周是否还有次数)→ `check_power`(`GuideCheckPower` 体力检查)→ `_use_power`(消耗体力)→ `challenge_echo_of_war`(战斗)。
- `GuideMission`(指南 mission,传送去历战余响点)。
- `on_battle_success(run_times, use_power)`(战斗成功回调,更新次数 / 体力)。
- `plan.mission_id`(计划指定哪个历战 boss)。

## 与开拓力玩法关系

历战余响是 [trailblaze_power](trailblaze_power.md) 的**周限子玩法**(与花萼 / 饰品 / 模拟宇宙并列):
- 花萼 / 饰品:无周限,按体力。
- **历战余响:周限 3 次 + 体力**(双重限制)。
- 模拟宇宙:独立 Roguelike。

## 画面

- **指南传送**(guide,生存索引 → 历战余响点)。
- **战斗**(`battle`)。
- **领奖励**(战斗后)。
- 无独立 `echo_of_war` screen_info —— 复用 guide + battle + 通用奖励画面。

## 备注 / 待查

- **待实拍画面 + vision**:历战历战 boss 战斗 + 奖励画面实拍归档 + vision(周本 boss / 难度选择 / 奖励图标)—— 周限 3 次,待用户配合切画面。
- **周限判断**:`check_task` 检测本周次数(run_record),bot 按周限跑。
- **体力检查**:`GuideCheckPower`(指南层检查体力,不足跳过 / 提示)。
- **难度选择**:历战难度 I-VI,bot 按配置跑哪个难度,待确认。
- **3 次后免体力**:bot 是否覆盖(刷成就 / 支援),待确认 —— 通常 bot 只跑奖励次数(3 次)。

## 参考来源

- [百度百科 历战余响](https://baike.baidu.com/item/%E5%8E%86%E6%88%98%E4%BD%99%E5%93%8D/63857979)
- [TapTap 全角色行迹材料攻略](https://www.taptap.cn/moment/797240343924837460)
- [B站 历战余响各级掉落统计](https://www.bilibili.com/read/cv24534160)
- [灰机Wiki 均衡等级收益速查](https://starrail.huijiwiki.com/wiki/%E5%9D%87%E8%A1%A1%E7%AD%89%E7%BA%A7/%E6%94%B6%E7%9B%8A%E9%80%9F%E6%9F%A5%E8%A1%A8)
