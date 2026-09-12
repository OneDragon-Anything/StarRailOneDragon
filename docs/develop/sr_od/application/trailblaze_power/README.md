# 开拓力（Trailblaze Power）App 设计文档

## 定位与目标

`TrailblazePowerApp`（app_id `trailblaze_power`）按用户配置的**体力计划列表**依次自动挑战各类副本，直到计划完成或资源（开拓力 / 沉浸器）用尽。它是对「体力类副本」的统一调度壳：**计划管理、资源预估、按副本类型分派**都在 app 层，具体挑战逻辑在各类型自己的 Operation 里。

- 计划列表与历史由 `TrailblazePowerConfig`（`config/xx/trailblaze_power.yml`）持久化，GUI 入口为主界面「体力计划」页（`sr_od/gui/interface/one_dragon/sr_power_plan_interface.py`）。
- 一个计划条目 = 一个副本 + 该副本的战斗配置 + 计划次数 / 已运行次数。

## 架构概述

app 是节点图（复用 Operation 机制），主链：

```
检查当前需要挑战的关卡（is_start_node）
  → 打开指南检查体力            （读当前开拓力 power 与沉浸器数量 qty）
  → 执行开拓力计划              （核心调度节点，见下）
  → 完成后返回                  （BackToNormalWorldPlus 回大世界收口）
```

`执行开拓力计划` 的调度语义：

1. 先 `check_plan_run_times()`：所有计划都跑满时，把已运行次数整体减去计划次数（回绕，供循环执行）。
2. `get_next_plan()` 从上次尝试的计划之后找第一个未完成的计划；找不到则结束。
3. 资源预估：`可跑次数 = 开拓力 // 该副本单次体力`；**模拟宇宙 / 饰品提取两类额外加沉浸器数量**（这两类消耗沉浸器）。预估为 0 则跳过该计划找下一个。
4. 本次运行次数 = min(可跑次数, 计划次数 − 已运行次数)，为 0 视为计划完成。
5. 按副本分类（`GuideMission.cate.cn`）分派给三种执行载体（见下表），执行中通过回调扣减 `power` / `qty` 并 `add_run_times` 记账。

### 副本类型索引

| 类型（cate.cn） | 执行载体 | 资源 | 类型文档 |
|---|---|---|---|
| 饰品提取 | `ChallengeOrnamentExtraction` | 沉浸器优先，不足扣开拓力 | [missions/ornament_extraction.md](missions/ornament_extraction.md) |
| 模拟宇宙 | `SimUniApp`（指定世界号） | 沉浸器优先，不足扣开拓力 | 见 `docs/develop/sr_od/application/sim_universe.md` |
| 其余标准副本（拟造花萼 / 凝滞虚影 / 侵蚀隧洞 / 历战余响等） | `UseTrailblazePower` | 开拓力 | 待补 |

类型分派的关键差异：标准副本用计划里的 `team_num`（游戏主界面预备编队 1~9）；饰品提取不用预备编队，改用 `file_num` + `team_name`（它有自己的存档与预设编队体系，详见类型文档）。

## 计划条目字段语义（TrailblazePowerPlanItem）

| 字段 | 语义 |
|---|---|
| `mission_id` | 星际和平指南副本唯一 id；加载时按它反查 `GuideMission`，查不到的旧数据被过滤丢弃 |
| `team_num` | 标准副本使用的预备编队号；0 = 游戏内当前配队。饰品提取不使用此字段 |
| `file_num` | 饰品提取存档号；0 = 游戏内当前存档。仅饰品提取使用 |
| `team_name` | 饰品提取预设编队名；空串 = 默认配队（不切队）。仅饰品提取使用 |
| `support` | 支援角色 id；`'none'` / None = 不带支援 |
| `plan_times` / `run_times` | 计划次数 / 已运行次数；跑满后由回绕机制复位 |
| `diff` | 难度；0 = 自动。**饰品提取当前未实现难度选择**（op 内相关节点停用），恒传 0 |

配置文件另有 `history_teams`（按 mission_id 记住上次的战斗配置，新增计划时回填）与 `loop`（GUI「循环执行」开关，循环语义由上面的回绕机制支撑）。

## 文件映射

| 文件 | 职责 |
|---|---|
| `src/sr_od/application/trailblaze_power/trailblaze_power_app.py` | app 节点图 + 类型分派 + 资源记账 |
| `src/sr_od/application/trailblaze_power/trailblaze_power_config.py` | 计划列表持久化 / 下一个计划选择 / 次数回绕 |
| `src/sr_od/application/trailblaze_power/trailblaze_power_run_record.py` | 按日运行记录 |
| `src/sr_od/application/trailblaze_power/trailblaze_power_app_factory.py` | 约定式自动注册 |
| `src/sr_od/gui/interface/one_dragon/sr_power_plan_interface.py` | 体力计划 GUI（计划卡片增删改 / 排序 / 循环开关） |
| `src/sr_od/application/div_uni/operations/ornamenet_extraction.py` | 饰品提取执行链（见类型文档） |
| `src/sr_od/challenge_mission/use_trailblaze_power.py` | 标准副本执行链 |

## 迭代设计

增量迭代设计放 `changes/` 子目录（每次迭代一个子目录：迭代开始写设计 → 对抗审查 → 实现后更新正本）。架构级选型决策按用户命令记录于 `decisions/`（ADR）。当前两者暂无内容。
