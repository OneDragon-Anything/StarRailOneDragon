# 画面建档索引

StarRailOneDragon 各 screen 画面建档 doc 索引。代表截图归档测试仓 `sr-od-test/screens/<screen>/`。建档方法论见 skill `od-dev-screen-onboarding`(客观识别 → 主观理解 → 建档 → 缺口分析 → 主动建模 → 归档)。

## 通用画面

| screen | doc | 说明 |
|---|---|---|
| 大世界 | [normal_world.md](normal_world.md) | 3D 探索大世界,`pc_alt=true`(锁光标) |
| 手机菜单 | [phone_menu.md](phone_menu.md) | 手机主菜单 |
| 大地图 | [large_map.md](large_map.md) | 2D 大地图导航 / 传送 |
| 背包 | [bag.md](bag.md) | 背包各 tab(消耗品/光锥/遗器/材料…) |
| 队伍 | [team.md](team.md) | 队伍编成 |
| 角色 | [character.md](character.md) | 角色养成 |
| 任务 | [mission.md](mission.md) | 任务 / 委托 |
| 战斗 | [battle.md](battle.md) | 回合制战斗(过程态 + 结果结算) |
| 对话 | [对话.md](对话.md) | 剧情对话 |
| 商店 | [store.md](store.md) | 商店购买 |
| 合成 | [synthesize.md](synthesize.md) | 合成 / 转化 |
| 进入游戏 | [enter_game.md](enter_game.md) | 登录 / 进入游戏流程 |
| 杂项画面 | [misc_screens.md](misc_screens.md) | 杂项 / 兜底画面 |
| 辅助 | [misc_auxiliary.md](misc_auxiliary.md) | 辅助功能画面 |

## 玩法画面

| screen | doc | 说明 |
|---|---|---|
| 模拟宇宙 | [模拟宇宙.md](模拟宇宙.md) | `sim_uni`,**20 子态**(入口流程①~⑪ / 获得弹窗 / 选择奇物 / 事件 / 沉浸奖励 / 休整 / 精英 / 战斗 / 交易·战斗失败推断),18 实拍 + 2 推断 |
| 差分宇宙 | [差分宇宙.md](差分宇宙.md) | `div_uni`·千面英雄,**6 子态**(入口 / 探索 / 选祝福 / 选奇物 / 选方程 / 获得方程),Roguelike bot 未覆盖(screen_info 未建模) |
| 货币战争 | [currency_war_lobby.md](currency_war_lobby.md) | `currency_war`,auto-chess 肉鸽,建档进行中(2026-08)。子屏 doc:大厅·模式选择·难度确认·简报·投资环境·备战·商店·[遭遇节点](currency_war_encounter.md)·战斗·补给·投资策略·[未达上限警告](currency_war_deploy_warning.md)·[结算](currency_war_settlement.md)·[挑战失败](currency_war_challenge_failed.md)·[选择伙伴](currency_war_choose_partner.md)·[盛会之星](currency_war_megastar.md)(羁绊触发的选巨星 overlay);**攻略面板**([列表](currency_war_guide_list.md)·[详情](currency_war_guide_detail.md)·[图例](currency_war_guide_legend.md)·[攻略码输入](currency_war_guide_code_input.md)·[保存阵容](currency_war_guide_save_modal.md)·[装备追踪](currency_war_guide_equip_track.md)·[阵容编辑](currency_war_guide_editor.md),2026-08-15 建档);备战子态屏:[角色详情](currency_war_char_detail.md)(点角色)+ 开商店(无独立 doc);独立装备详情(备战右侧装备,待建档) |

> 玩法机制 doc 见 [gameplay/](../gameplay/);app 编排 develop doc 见 [develop/sr_od/application/](../../develop/sr_od/application/)。
