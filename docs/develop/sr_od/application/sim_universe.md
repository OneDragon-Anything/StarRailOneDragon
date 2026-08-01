---
app_id: sim_universe
last_updated: 2026-08-01
source: application/sim_universe/ 代码(@operation_node 节点链)
---

# 模拟宇宙 应用编排(sim_universe)

重 app(多 op 编排),常驻 Roguelike 玩法自动化。玩法机制见 [gameplay/sim_uni](../../../game/gameplay/sim_uni.md),画面见 [screen 模拟宇宙](../../../game/screens/模拟宇宙.md)。

## 顶层编排:SimUniApp(`sim_uni_app.py`)

**入口循环**(完成后回到「检查运行次数」跑下一个宇宙,直到次数满 / 异常超限):

```
检查运行次数 → 识别初始画面 → 传送 → 选择宇宙 → 选择难度 → 开始挑战
            → 选择命途 → 自动宇宙 → [异常退出] → 领取每周奖励 → 完成后返回
```

节点链(状态分支):
- **检查运行次数**(is_start):`init_for_sim_uni`;精英日/周次数满 → `STATUS_ALL_FINISHED`;异常 ≥10 → `STATUS_EXCEPTION`。
- **识别初始画面**:`get_sim_uni_initial_screen_state`;若已 `SIM_TYPE_NORMAL`(在入口)+ all_finished → `STATUS_TO_WEEKLY_REWARD`。
- **传送**:`GuideTransport`(指南·旷宇纷争·差分宇宙·前往模拟宇宙)。
- **选择宇宙**(`ChooseSimUniNum`):`STATUS_RESTART`(重新开始)→ 选难度;`STATUS_CONTINUE`(继续)→ 开始挑战。
- **选择难度**(`ChooseSimUniDiff`)→ 开始挑战。
- **开始挑战**(`SimUniStart`):`STATUS_RESTART` → 选命途;`STATUS_CONTINUE` → 自动宇宙。
- **选择命途**(`SimUniChoosePath`)→ 自动宇宙。
- **自动宇宙**(`SimUniRunWorld`):跑层;`success=False` → 自动宇宙发生异常。
- **自动宇宙发生异常**:debug 原地 fail;否则 → 异常退出。
- **异常退出**(`SimUniExit`)→ (边)回检查运行次数。
- **领取每周奖励**(`SimUniClaimWeeklyReward`)← `STATUS_TO_WEEKLY_REWARD`。
- **完成后返回**(`BackToNormalWorldPlus`)← `STATUS_EXCEPTION` / 领取每周奖励(含 fail)。

## 宇宙级:SimUniRunWorld(`auto_run/sim_uni_run_world.py`,完成整个宇宙)

**挑战楼层**(`SimUniRunLevel`)循环:
- `STATUS_BOSS_CLEARED`(首领通关)→ 结束(`STATUS_SUCCESS` 通关)。
- `success=False` → 异常处理(debug `round_fail` / 否则 `SimUniExit`)。
- 战斗失败(`SimUniEnterFight.STATUS_BATTLE_FAIL`)→ 战斗失败结算 → 战斗失败结算确认 → 点击空白处继续。

带 `max_reward_to_get`(沉浸奖励次数上限)+ `get_reward_callback`;连续两次同队伍后 `skip_check_members=True` 跳过组队检测。

## 楼层级:SimUniRunLevel(`auto_run/sim_uni_run_level.py`,单楼层)

```
等待加载 → 识别组队成员 → 切换1号位 → 识别楼层类型 → 匹配路线 → 按类型运行路线指令v1
                                                                       ↓ (失败/无路线)
                                                                  按类型运行路线指令v2
                                                                       ↓ (ENTRY_NOT_FOUND)
                                                                  重置(最多1次)→ 回识别楼层类型
```

- **等待加载**(`SimUniWaitLevelStart`)。
- **识别组队成员**(`CheckTeamMembersInWorld`,可 skip)→ **切换1号位**(`SwitchMember`)。
- **识别楼层类型**:`get_level_type`;失败 `round_retry`。
- **匹配路线**:仅 **3-8 宇宙 COMBAT 楼层**,小地图 `match_best_sim_uni_route`,**两次一致**才认定(牺牲时间换稳定)。
- **按类型运行路线指令v1** → `_get_route_op`;BOSS 通关 → `STATUS_BOSS_CLEARED`。
- **v2**:`v1` 失败(`MoveDirectly.STATUS_NO_POS`)/ 无路线 / 匹配路线失败 → v2 兜底。
- **重置**:`ENTRY_NOT_FOUND` → `ResetSimUniLevel`(最多 1 次)→ 回识别楼层类型;超限 `STATUS_NO_RESET`。

**楼层类型**(`SimUniLevelTypeEnum`):`COMBAT`(战斗)/`EVENT`(事件)/`TRANSACTION`(交易)/`ENCOUNTER`(遭遇)/`RESPITE`(休整)/`ELITE`(精英)/`BOSS`(首领)/`ANY`(差分4.0 位面)。

## 路线 op 分工(`_get_route_op`,按楼层类型选 op)

| 楼层类型 | v1(预录路线) | v2(算法兜底) |
|---|---|---|
| COMBAT 战斗 | `SimUniRunCombatRoute`(需 route,3-8 宇宙) | `SimUniRunCombatRouteV2` |
| EVENT / TRANSACTION / ENCOUNTER | — | `SimUniRunEventRouteV2` |
| RESPITE 休整 | — | `SimUniRunRespiteRouteV2` |
| ELITE / BOSS 精英/首领 | — | `SimUniRunEliteRouteV2`(带奖励回调) |

## move v1 vs v2

- **v1**(`move_v1/`,`SimUniRunCombatRoute` + `MoveToNextLevel` + `sim_uni_move_to_enemy_by_mm`/`_detect`):靠**预录路线**(`sim_uni_route_data`,小地图匹配),仅 3-8 宇宙战斗楼层;精度高但依赖路线数据。
- **v2**(`move_v2/`,`SimUniRunCombatRouteV2`/`Elite`/`Event`/`Respite` + `sim_uni_run_route_base_v2`):**算法兜底**,覆盖所有楼层类型;v1 失败或无路线时启用。
- **流程**:COMBAT 楼层先试 v1(有路线且 `algo≠2`)→ 失败 / 无路线 → v2;其他楼层直接 v2。

## 子 op 目录(`operations/`)

- **entry/**:`choose_sim_uni_num`(选世界)、`choose_sim_uni_diff`(选难度)、`sim_uni_start`(开始挑战)、`sim_uni_claim_weekly_reward`(领每周奖励)。
- **bless/**:`sim_uni_choose_bless`(选祝福)、`sim_uni_drop_bless`(弃祝福)、`sim_uni_upgrade_bless`(强化祝福)、`sim_uni_choose_path`(选命途)。
- **curio/**:`sim_uni_choose_curio`(选奇物)、`sim_uni_drop_curio`(弃奇物)。
- **event/**:`sim_uni_event`(事件)、`sim_uni_reward`(事件奖励)。
- **battle/**:`sim_uni_fight_elite`(打精英)。
- **move_v1/**:`move_to_next_level`、`sim_uni_move_to_enemy_by_mm`/`_detect`、`sim_uni_run_combat_route_v1`、`move_directly_in_sim_uni`、`sim_uni_route_op`。
- **move_v2/**:`sim_uni_run_combat_route_v2`、`sim_uni_run_elite_route_v2`、`sim_uni_run_event_route_v2`、`sim_uni_run_respite_route_v2`、`sim_uni_run_route_base_v2`、`sim_uni_move_to_next_level_v3`。
- **auto_run/**:`sim_uni_run_world`、`sim_uni_run_level`、`reset_sim_uni_level`、`sim_uni_wait_level_start`。
- **根**:`sim_uni_exit`(退出结算)、`sim_uni_enter_fight`(进战斗)、`sim_uni_event`、`sim_uni_move_utils`。

## 配置 / 数据

- `sim_uni_config.py` / `sim_uni_challenge_config.py`:挑战配置(周宇宙 / 难度 / 命途 / 精英日·周次数)。
- `sim_uni_route_data.py` + `sim_uni_route.py`:预录路线数据 + 路线模型(v1 用)。
- `sim_uni_data.py`:世界(`SimUniWorldEnum`)/ 命途(`SimUniPath`)/ 楼层类型(`SimUniLevelTypeEnum`)枚举。
- `sim_uni_run_record.py`:运行记录(精英日 / 周次数)。
- `sim_uni_screen_state.py`:画面状态判定(`get_sim_uni_screen_state` / `get_level_type` / `get_sim_uni_initial_screen_state`)。

## 待查

- v1 预录路线数据覆盖范围(3-8 宇宙战斗楼层)是否随版本更新需补。
- 差分宇宙 4.0(`ANY` 楼层 / 选择站点 / 选择奇迹 / 欢愉假面)目前仅在 `BackToNormalWorldPlus` 有退出处理,`SimUniRunLevel` 的 `ANY` 分支未在 `_get_route_op` 覆盖(返回 None → fail)—— 是否需补待评估。
- 战斗失败路径:`SimUniRunWorld` 处理「战斗失败-终止/确认/点击空白」,与 `sim_uni.yml` 的战斗失败 area 对应;`BackToNormalWorldPlus` 也有战斗失败兜底,两者职责边界待确认。
