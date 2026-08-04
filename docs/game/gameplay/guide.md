---
gameplay_name: 星际和平指南(guide,导航中枢)
app_id: guide
last_updated: 2026-07-29
source: screen_info `guide`(20 area)+ `interastral_peace_guide/` op 代码
involves_screens: [星际和平指南]
---

# 星际和平指南(guide)

导航中枢,不是独立玩法 —— 是**各体力玩法的传送入口**(花萼 / 饰品 / 历战 / 侵蚀隧洞 / 凝滞虚影 / 模拟宇宙 / 忘却之庭 经指南传送)。`pc_alt=false`。手机菜单「指南」进入。

## 结构(screen_info `guide`,20 area)

- **6 个 TAB**:TAB-行动摘要、TAB-每日实训、TAB-生存索引(体力玩法入口)、TAB-旷宇纷争、TAB-逐光捡金(忘却之庭入口)、TAB-开拓历程。
- **分类列表**(左侧):各 TAB 下的分类(如生存索引下:花萼/饰品/历战…)。
- **副本列表**:分类下的副本 / mission(传送点)。
- **生存索引信息**:生存索引-体力 / 沉浸器数量(+ 完整体力 / 完整沉浸器数量)。
- **等待加载(传送后)**:等待加载-拟造花萼(金/赤)、饰品提取、凝滞虚影、侵蚀隧洞、历战余响、模拟宇宙、培养目标 —— 传送后各玩法的加载确认画面。

## bot 流程(`interastral_peace_guide/`)

- `OpenGuide`(开指南:菜单点「指南」`phone_menu_const.INTERASTRAL_GUIDE`)。
- `GuideChooseTab`(选 TAB,如「生存索引」)。
- `GuideChooseCategory`(选分类,如花萼)。
- `GuideChooseMission`(选副本 / 传送点 mission)。
- `GuideTransport`(传送:确认传送 → 等待加载-XX → 落目标大世界)。
- `GuideCheckPower`(体力检查:`GuidePowerResult`,不足跳过 / 提示)。

## 数据模型(`guide_def.py`)

- `GuideTab`:指南 TAB(行动摘要 / 生存索引 / 逐光捡金…)。
- `GuideCategory`:分类(tab + 中文名 + unique_id)。
- `GuideMission`:副本(cate + mission_name + region_name + display_name + power 体力 + 传送点 tp)。
- `guide_data.py`:mission 注册表(`get_mission_by_unique_id`)。

## 传送入口(各玩法)

体力玩法经指南传送:
| 玩法 | 等待加载 area | 去向 |
|---|---|---|
| 拟造花萼(金/赤) | 等待加载-拟造花萼(金)/(赤) | 大世界花萼点 → 战斗 |
| 饰品提取 | 等待加载-饰品提取 | 饰品提取画面 |
| 凝滞虚影 | 等待加载-凝滞虚影 | (角色晋升材料) |
| 侵蚀隧洞 | 等待加载-侵蚀隧洞 | (外圈遗器) |
| 历战余响 | 等待加载-历战余响 | 周本 boss |
| 模拟宇宙 | 等待加载-模拟宇宙 | 模拟宇宙入口 |

## 备注 / 待查

- **导航中枢,非玩法**:指南本身无奖励,是各玩法传送入口 —— bot 各体力 app(trailblaze_power / echo_of_war)经指南传送。
- **传送失败 = 地图未探索**:`GuideTransport` 打开地图选不中目标点 → 多为该地图未探索 / 传送点未解锁(screen-onboarding「Transport 失败排查」)。
- **体力检查**:`GuideCheckPower`(指南层检查体力 / 沉浸器,不足跳过)。
- **待实拍画面 + 视觉大模型**:指南各 TAB(生存索引 / 逐光捡金)+ 分类 / 副本列表 + 等待加载态实拍归档 + 视觉大模型(TAB 图标 / 副本图标 / 体力显示)。
- **6 TAB 覆盖**:行动摘要 / 每日实训 / 生存索引 / 旷宇纷争 / 逐光捡金 / 开拓历程 —— bot 主要用生存索引(体力)+ 逐光捡金(忘却之庭),其他 TAB 用途待确认。
