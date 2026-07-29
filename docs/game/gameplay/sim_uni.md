---
gameplay_name: 模拟宇宙
app_id: sim_universe
last_updated: 2026-07-29
source: WebSearch 攻略(2025)+ screen_info `sim_uni`(30 area)+ `application/sim_universe/` 代码
involves_screens: [模拟宇宙, 战斗画面]
---

# 模拟宇宙(sim_universe)

常驻 Roguelike 玩法。选命途 → 逐层推进位面(蜂巢地图)→ 战斗 / 事件 / 商店 / 休息地块 → 击败首领通关。祝福 + 奇物 + 随机事件强化队伍。**`pc_alt=true`**(大世界类 3D 探索,锁光标)。

## 玩法机制(攻略)

- **核心**:Roguelike —— 祝福(命途:毁灭 / 存护 / 巡猎 / 智识 / 同谐 / 虚无 / 丰饶)+ 奇物 + 随机事件,组合强化队伍。
- **流程**:选世界 / 命途 → 位面探索(蜂巢格子,向右 / 右上 / 右下移动)→ 战斗 / 事件 / 商店 / 休息地块 → 击败首领 → 通关结算。
- **扩展**:差分宇宙(千面英雄,星阶模式 / 数值映射)、不可知域(分形档案第四位面,挑战失败不影响结算)。
- **奖励**:位面饰品(遗器)、模拟宇宙积分、技能点、星琼(累计解锁命途祝福 5/12/18/22/24/26 个各 ×80)。
- 每周奖励(一键领取)。

## bot 流程(`application/sim_universe/`,重 app 多 op 编排)

- **entry**:`choose_sim_uni_num`(选世界 / 难度)+ `sim_uni_start`(启动)。
- **auto_run**:`sim_uni_run_level`(跑层)→ `reset_sim_uni_level` / `sim_uni_wait_level_start`(层初始化)→ `move_to_next_level`(move_v1)→ `sim_uni_run_combat_route_v1`/`v2`(战斗路线)。
- **move_v1 / v2**:`move_to_next_level` + `sim_uni_move_to_enemy_by_mm`(小地图找敌)+ `sim_uni_run_combat_route`(战斗)。v1 / v2 两套战斗路线算法。
- **结算**:菜单-结束并结算 / 终止战斗并结算 / 沉浸奖励 / 每周奖励-一键领取。

## 画面(`sim_uni` screen_info,30 area,pc_alt=true)

- **入口态**:宇宙入口-进行中-1/2、当前宇宙名称-1/2、入口-启动模拟宇宙 / 继续 / 下载初始角色 / 低等级确认。
- **探索态**:楼层类型、怪物上方等级、大世界返回按钮、左上角标题。
- **事件**:事件标题、点击空白处继续。
- **结算**:菜单-结束并结算、终止战斗并结算、退出对话框-确认、沉浸奖励、每周奖励-一键领取 / 红点。
- **战斗失败**:战斗失败(标题)、战斗失败-终止战斗并结算 / 确认、点击空白处关闭。
- **差分宇宙**:差分宇宙-暂离。

## 备注 / 待查

- **待实拍画面 + vision**:sim_uni 各子态(入口 / 探索 / 事件 / 结算 / 战斗失败)实拍归档(`screens/模拟宇宙/*.webp`)+ vision 看图(蜂巢地图 / 祝福选择 / 奇物 / 事件 UI 等图标布局)—— 进 sim_uni 消耗体力,待用户配合切画面。
- **重 app 编排**:sim_universe 的 auto_run + move v1/v2 详细节点链(@operation_node)待读代码补 develop doc(`docs/develop/sr_od/application/sim_universe.md`)。
- **move v1 vs v2**:两套战斗路线算法差异待确认。
- **扩展玩法覆盖**:差分宇宙(`div_uni` app?)/ 不可知域,bot 覆盖范围待确认(div_uni application 已存在)。

## 参考来源

- [官方:差分宇宙千面英雄玩法说明](https://sr.mihoyo.com/news/154448?nav=home)
- [官方:差分宇宙玩法说明](https://sr.mihoyo.com/news/124155)
- [B站WIKI:模拟宇宙](https://wiki.biligame.com/sr/%E6%A8%A1%E6%8B%9F%E5%AE%87%E5%AE%99)
- [TapTap:不可知域玩法说明](https://www.taptap.cn/moment/597474868950207916)
