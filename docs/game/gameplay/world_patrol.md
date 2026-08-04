---
gameplay_name: 锄大地(world_patrol)
app_id: world_patrol
last_updated: 2026-07-29
source: `application/world_patrol/` 代码(APP_NAME「锄大地」)+ 路线数据;WebSearch「锄地路线」攻略
involves_screens: [大世界, 战斗画面]
---

# 锄大地(world_patrol)

沿预设路线在大世界跑图打怪(俗称「锄地」),刷星琼 / 材料 / 成就。**无开拓力消耗**(区别于花萼 / 历战),但耗时长(跑图)。bot 有完整路线数据 + 白名单。

## 玩法机制(攻略)

- **锄大地**:大世界沿路线跑,打所有遇敌(刷星琼 / 材料 / 破坏物)。
- **无体力**:纯跑图 + 战斗,free 收益(星琼 + 材料)。
- **耗时**:路线长,跑全程久(需后台跑)。
- **路线**:玩家社区维护的锄地路线(传送 → 移动 → 战斗节点),追求最优路径刷怪。
- bot 用预设路线数据(`world_patrol_route_data`)自动跑。

## bot 流程(`application/world_patrol`)

`WorldPatrolApp`(op_name「锄大地」):
- `load_route_list`(加载路线,按 `whitelist` 白名单 + `finished` 已完成过滤)→ `WorldPatrolRunRoute`(跑路线)。
- 每条路线:`transport`(传送)→ `move`(移动,按路线节点 press_time)→ `world_patrol_enter_fight`(遇敌战斗)→ 循环到路线完。
- `route_list` + `current_route_idx`(路线索引);`current_route_start_time`(计时)。
- `back_to_normal_world`(回大世界)+ `cancel_trace`(取消任务追踪,避免干扰路线)。
- `init_for_world_patrol`(锄地专属初始化)。

## 路线数据

- `world_patrol_route_data`:预设路线(传送 / 移动 / 战斗节点序列)。
- `world_patrol_whitelist_config`:路线白名单(用户选要跑的路线集合)。
- `world_patrol_route` / `world_patrol_route_utils`:路线结构 + 工具。
- `world_patrol_route_draw_utils`:路线绘制(可视化 / 调试)。

## 画面

- **大世界跑图**(`normal_world`,`pc_alt=true` 锁光标,click 需 pc_alt)。
- **战斗**(`battle`)。
- `world_patrol_screen_state`:锄地专属画面状态(路线中识别)。

## 备注 / 待查

- **待实拍画面 + 视觉大模型**:锄地跑图(路线节点 / 遇敌)+ 战斗实拍归档 + 视觉大模型 —— 耗时长,待用户配合 / 后台跑时截图。
- **路线数据格式**:`world_patrol_route_data` 的路线结构(传送点 / move press_time / 战斗触发)待细化 doc。
- **白名单**:用户在 GUI 选路线(whitelist),bot 跑选中路线集合;`world_patrol_whitelist_config` 结构待 `describe_config`。
- **搜索术语**:world_patrol 俗称「锄大地」(非「巡星之路」),攻略搜「锄大地 / 锄地路线」。
- **耗时 + 后台**:锄地路线长,bot 跑全程耗时,通常后台 / 托管跑。

## 参考来源

- [游民星空 锄地路线攻略](https://www.gamersky.com/handbook/202307/1616859.shtml)
- [Epic 开始游玩前 13 诀窍](https://store.epicgames.com/news/13-tips-you-need-to-know-before-starting-honkai-star-rail?lang=zh-Hant)
