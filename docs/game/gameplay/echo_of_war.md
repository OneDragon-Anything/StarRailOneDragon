---
gameplay_name: 历战余响(周本)
app_id: echo_of_war
last_updated: 2026-07-30
source: WebSearch 攻略 + `application/echo_of_war/` 代码 + `guide` / `challenge_mission` screen_info + check_power fixture + 2026-07-30 实拍(选关/战败)
involves_screens: [星际和平指南, 挑战副本, 战斗画面, 大世界-战斗失败]
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

`EchoOfWarApp` 三节点链(`check_task` → `check_power` → `_use_power`):
- **`check_task`**(起始节点,**纯配置逻辑,不读截图**):读 `echo_of_war_config.next_plan_item`
  + `echo_of_war_run_record.left_times` → `STATUS_WITH_PLAN`(有计划 + 周限次数>0)/
  `STATUS_NO_PLAN`(无计划 或 周限用完)。首行还会调 `ctx.power_config.check_plan_run_times()`
  重置开拓力计划次数。
- **`check_power`**(委托 `GuideCheckPower`):打开指南 → 选生存索引 tab → OCR
  `生存索引-完整体力`(开拓力)/ `生存索引-完整沉浸器数量`(沉浸器),回填 `self.power`。
- **`_use_power`**(委托 `ChallengeEchoOfWar`):`GuideTransport` 传送去历战 boss 点 →
  点挑战 → 配队 / 选支援 → 战斗 → 再来一次 / 退出;`on_battle_success` 回调更新
  `plan.run_times` + `run_record.left_times` + 扣体力。
- `plan.mission_id`(`echo_of_war_config.plan_list`,指定哪个历战 boss);`plan_times` 计划次数。

## 与开拓力玩法关系

历战余响是 [trailblaze_power](trailblaze_power.md) 的**周限子玩法**(与花萼 / 饰品 / 模拟宇宙并列):
- 花萼 / 饰品:无周限,按体力。
- **历战余响:周限 3 次 + 体力**(双重限制)。
- 模拟宇宙:独立 Roguelike。

## 画面

无独立 `echo_of_war` screen_info —— 复用共享画面:
- **星际和平指南-生存索引**(`guide`):`check_power` 在此读开拓力 / 沉浸器(`生存索引-完整体力` /
  `生存索引-完整沉浸器数量` area)。fixture 已归档 `screens/星际和平指南/生存索引.webp`。
- **挑战副本**(`challenge_mission`,共享):挑战按钮 / 开拓力弹框 / 开始挑战按钮 / 阵亡弹框 /
  提示弹框(均已建模,见 `challenge_mission.yml`)。
- **战斗 / 领奖励**:通用 `battle`(挑战成功结算) + 通用奖励画面。
- **战斗失败结算**:⚠️ 归属 **「大世界-战斗失败」** screen(非「战斗画面」,2026-07-30 实测)。
  `is_battle_fail` 查该 screen 的「标题-战斗失败」area(已修,见 [battle.md](../screens/battle.md))。
  fixture:`screens/历战余响/选关-铁骸的锈冢.webp`(选关) + `screens/大世界-战斗失败/战斗失败-历战余响.webp`(战败)。
- **指南传送**:生存索引 → 历战余响点(`GuideTransport`,`等待加载-历战余响` area)。

## 备注 / 待查

- **`check_task` 是纯配置逻辑**:不读截图,节点测试用 mock config 覆盖三分支
  (有计划 / 无计划 / 周限用完);`check_power` 测 `GuideCheckPower.get_power_and_qty`
  OCR 提取(见 `sr-od-test/.../echo_of_war/test_echo_of_war_app.py`)。
- **已实拍(2026-07-30)**:历战余响选关(铁骸的锈冢 难度VI,`screens/历战余响/`)+ 战败结算(「大世界-战斗失败」screen,`screens/大世界-战斗失败/战斗失败-历战余响.webp`)。战败 screen 归属已确认 —— 与拟造花萼/凝滞虚影/侵蚀隧洞**一致**(副本战败统一进「大世界-战斗失败」)。
- **待补实拍**:历战 boss 战斗过程态 / 挑战成功结算 / 奖励领取(需正常打赢一场)。
- **周限判断**:`check_task` 读 `run_record.left_times`(本周剩余次数),bot 按周限跑。
- **体力检查**:`GuideCheckPower`(指南生存索引层 OCR 开拓力,不足则后续 `_use_power` 跳过)。
- **难度选择**:历战难度 I-VI,bot 按配置跑哪个难度,待确认。
- **3 次后免体力**:bot 是否覆盖(刷成就 / 支援),待确认 —— 通常 bot 只跑奖励次数(3 次)。

## 参考来源

- [百度百科 历战余响](https://baike.baidu.com/item/%E5%8E%86%E6%88%98%E4%BD%99%E5%93%8D/63857979)
- [TapTap 全角色行迹材料攻略](https://www.taptap.cn/moment/797240343924837460)
- [B站 历战余响各级掉落统计](https://www.bilibili.com/read/cv24534160)
- [灰机Wiki 均衡等级收益速查](https://starrail.huijiwiki.com/wiki/%E5%9D%87%E8%A1%A1%E7%AD%89%E7%BA%A7/%E6%94%B6%E7%9B%8A%E9%80%9F%E6%9F%A5%E8%A1%A8)
