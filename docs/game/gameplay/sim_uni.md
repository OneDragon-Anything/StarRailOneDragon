---
gameplay_name: 模拟宇宙
app_id: sim_universe
last_updated: 2026-08-01
source: WebSearch 攻略(2025)+ screen_info `sim_uni`(30 area)+ `application/sim_universe/` 代码 + 2026-08-01 实拍修正(8 命途 / 子态 / 交易商店)
involves_screens: [模拟宇宙, 战斗画面]
---

# 模拟宇宙(sim_universe)

常驻 Roguelike 玩法。选命途 → 逐层推进位面(蜂巢地图)→ 战斗 / 事件 / 商店 / 休息地块 → 击败首领通关。祝福 + 奇物 + 随机事件强化队伍。**`pc_alt=true`**(大世界类 3D 探索,锁光标)。

## 玩法机制(攻略)

- **核心**:Roguelike —— 选 1 命途(8 选 1:**存护 / 记忆 / 虚无 / 丰饶 / 巡猎 / 毁灭 / 欢愉 / 繁育**,实拍命途选择画面确认)→ 收集该命途 + 跨命途「祝福」(1-3 星,3 星 = 命途回响 / 回响构音,如巡猎「四相断我」)+「奇物」+ 随机事件,组合强化队伍。
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

- **旷宇纷争入口(2026-07-29 采)**:指南 旷宇纷争 tab(差分宇宙选择 + 晋升等级 / 周期积分 / 前往参与)实拍归档 `screens/星际和平指南/旷宇纷争.webp`。
- **sim_uni 内部子态已建档(2026-08-01)**:画面 doc [screens/模拟宇宙](../screens/模拟宇宙.md) 收录 **20 子态**(入口流程①~⑪ + 获得弹窗 / 选择奇物 / 事件 / 沉浸奖励 / 休整 / 精英 / 战斗 + 交易 / 战斗失败),实拍归档 `screens/模拟宇宙/*.webp`(含交易商店对话+选项);**仅战斗失败仍为代码 + screen_info 推断**(bot 自动战斗强、不输,难触发)。跑层随机子态(祝福/奇物/事件/休整/精英)用「钩子法」抓(画面判定函数加临时截图钩子);**交易**经临时 transaction/event 优先级跑层触发(v2 算法路线默认 combat 第一会绕开事件/交易地块),事后回滚 priority。
- **重 app 编排已补(2026-08-01)**:develop doc [develop/sr_od/application/sim_universe](../../develop/sr_od/application/sim_universe.md) 写 SimUniApp / RunWorld / RunLevel 节点链 + 路线 op 分工 + move v1/v2 差异(v1 靠预录路线仅 3-8 宇宙战斗,v2 算法兜底覆盖全类型)。
- **差分宇宙已建档(2026-08-01)**:画面 doc [screens/差分宇宙](../screens/差分宇宙.md) 收录 6 子态(入口 / 大世界 / 选祝福 / 选奇物 / 选方程 / 获得方程);bot 仅覆盖饰品提取,Roguelike 演算未实现(画面 screen_info 未建模)。

## 参考来源

- [官方:差分宇宙千面英雄玩法说明](https://sr.mihoyo.com/news/154448?nav=home)
- [官方:差分宇宙玩法说明](https://sr.mihoyo.com/news/124155)
- [B站WIKI:模拟宇宙](https://wiki.biligame.com/sr/%E6%A8%A1%E6%8B%9F%E5%AE%87%E5%AE%99)
- [TapTap:不可知域玩法说明](https://www.taptap.cn/moment/597474868950207916)
