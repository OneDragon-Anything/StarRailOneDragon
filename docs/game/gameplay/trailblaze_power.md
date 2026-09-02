---
gameplay_name: 开拓力玩法(体力)
app_id: trailblaze_power
last_updated: 2026-09-02
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
  - **饰品提取**(ornamenet_extraction):遗器(可指定预言 / 套装)。**难度绑定存档**(2026-09-02 实机实锤):详情页「难度 Ⅴ」为纯展示文本(点击无反应),实际难度在「获得存档」时于模式内选定并存档记住;bot 用默认存档即沿用其难度。难度 Ⅴ = 推荐队伍等级 80 / 首领敌人 90,低练度账号不可战胜利(2026-09-01/02 两日连败实证)——打不过先在游戏内把存档难度调低,或换强队。
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

**进入链(全部类型一致,2026-08-29 全类型实拍)**:指南-生存索引 → 选分类 → 关卡行「进入」→ **副本挑战面板**(难度侧栏 I-VI + 可能遭遇/可能获取 + 挑战次数滑条 + 挑战按钮,部分类型有特殊机制文案/快速刷取)→「挑战」→ **编队画面**(队伍 tab + 快速编队 + 支援 + 开始挑战)→「开始挑战」→(次数=1 时直进战斗;>1 出 副本连续挑战次数 弹窗)→ 战斗 → 结算(退出关卡/再来一次/重新编队)。

**挑战面板家族差异**(实拍 `screens/<类型>/挑战面板.webp`):花萼金/赤(类型图标+介绍文案)/凝滞虚影(材料属性筛选)/侵蚀隧洞(特殊机制文案+右上「遗器设置」)/历战余响(特殊机制+「本周剩余次数 0/3」横幅=周限 UI 来源;0/3 时挑战仍可进=免体力无奖励)/饰品提取(沉浸器/快捷补充开关+支援列表,见 [screens/饰品提取](../screens/饰品提取.md))。

- **calyx(副本连续挑战次数)** screen_info(`pc_alt=false`,2 area):⚠️ **仅大世界副本入口 F 交互的老路径出现**(2026-08-29 实证:指南直达面板把挑战次数滑条调 >1 再开打也不弹,直接开打);实拍待走一次老入口路径。
- 各类型 fixture:`拟造花萼-赤`(全链4帧)/`拟造花萼-金`/`凝滞虚影`/`侵蚀隧洞`(面板+编队+结算)/`历战余响`(分类页+面板·次数用完态)/`饰品提取`(4帧)。

## 备注 / 待查

- **待实拍画面 + 视觉大模型**:花萼 / 历战 / 饰品战斗画面 + `calyx` 次数输入态实拍归档 + 视觉大模型(消耗体力,待用户配合切画面)。
- **trailblaze_power 计划配置**:`power_config`(plan_times / run_times / mission)—— 用户在 GUI 配计划,bot 按计划跑;配置结构待 `describe_config(trailblaze_power)` 细化。
- **guide 传送**:各玩法入口经「星际和平指南」传送 —— Transport 失败多为地图未探索 / 传送点未解锁(screen-onboarding「Transport 失败排查」)。
- **历战余响** echo_of_war 有独立 app(`application/echo_of_war`)+ `echo_of_war_config`,周限,见 [echo_of_war](echo_of_war.md)。

## 参考来源

- [4399 体力规划指南](https://a.4399.cn/gl/38935068_217170.html)
- [游民星空 双倍花萼规划](https://www.gamersky.com/handbook/202307/1616859.shtml)
- [Gachia 开拓力规划](https://gachia.com/zh/starrail/guides/trailblaze-power-guide)
- [米游社 花藏繁生](https://www.miyoushe.com/sr/wiki/content/5565/detail)
