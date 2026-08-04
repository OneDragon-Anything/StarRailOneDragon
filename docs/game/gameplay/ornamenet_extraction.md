---
gameplay_name: 饰品提取
app_id: ornamenet_extraction
last_updated: 2026-07-29
source: WebSearch 攻略 + screen_info `ornamenet_extraction`(15 area)+ `application/div_uni/operations/ornamenet_extraction` 代码
involves_screens: [饰品提取, 队伍, 战斗画面]
---

# 饰品提取(ornamenet_extraction)

获取**位面饰品**(内圈遗器:位面球 + 连结绳)的核心玩法。选套装存档 + 编队 + 挑战,消耗 40 开拓力 / 1 沉浸器。是 [开拓力玩法](trailblaze_power.md) 的子玩法。`pc_alt=false`。

## 玩法机制(攻略)

- **位面饰品**:遗器内圈两件套(位面球 + 连结绳),与外圈四件套(隧洞遗器)组合。
- **消耗**:40 开拓力 / 次,或 1 沉浸器 / 深度沉浸器(免战斗提取)。
- **奖励**:65 级(均衡 6)最大,单次最多 3 个五星位面饰品。
- **入口**:星际和平指南 → 生存索引 → 饰品提取。
- **套装存档**:可选套装(存档预设,4 个存档槽)—— 按需刷指定套装。
- **位面分裂活动**:双倍奖励。

## bot 流程(`application/div_uni/operations/ornamenet_extraction`)

`ChallengeOrnamentExtraction`:
- `choose_oe_file`(选套装存档 / 档案 1-4)→ `choose_oe_support`(选支援角色)→ 挑战(战斗)。
- 由 `trailblaze_power` app 按计划调度(execute_plan)。

## 画面(`ornamenet_extraction` screen_info,15 area,pc_alt=false)

- **标题**:左上角标题-饰品提取 / 左上角标题-存档管理。
- **存档选择**(套装预设):按钮-切换存档入口 / 确认 / 存档使用中;**档案-1/2/3/4**(4 个套装存档槽)。
- **编队**:按钮-预设编队、区域-预设编队名称。
- **支援**:按钮-支援、**支援角色替换图标**(⚠️ pc_rect 占位待填,见下)、支援入队踢 4 号位角色。
- **挑战**:按钮-开始挑战。

## 备注 / 待查

- **`支援角色替换图标` pc_rect 待填**:`ornamenet_extraction.yml` 该 area `pc_rect=[0,0,0,0]` 占位(坐标待建档细化时实拍填),area 有用途(支援角色替换提示)、不删。与 `challenge_mission` 同名 area 同问题。
- **待实拍画面 + 视觉大模型**:饰品提取各态(存档选择 / 编队 / 支援 / 挑战)实拍归档 + 视觉大模型(套装图标 / 存档槽 / 编队位)—— 消耗体力,待用户配合。
- **4 存档 = 套装预设**:档案 1-4 是 4 个套装预设(玩家预先配,bot 选存档刷指定套装)。
- **预言套装**:攻略未明确「预言」(可能记忆偏差);饰品提取可选套装存档,具体套装名待实拍存档确认。
- **沉浸器 / 深度沉浸器**:免战斗提取,bot 是否覆盖(优先用沉浸器)待确认。

## 参考来源

- [2.0 位面饰品刷取与角色适配](https://cg.163.com/static/content/65d83e08240edbd57375e16e)
- [游民星空 遗器及位面饰品系统](https://www.gamersky.com/handbook/202307/1616859.shtml)
