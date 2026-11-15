# 末日幻影 app 骨架 迭代设计（总纲）

## 0. 元信息

- 迭代目标：把逐光捡金·末日幻影做成可独立运行的 Application（`run_standalone_app` 可跑），选人策略用随机占位，流程优先（用户裁定 2026-11-16 凌晨：选人暂时乱选，先串流程；不进一条龙；设计与实现全程子agent无前提评审；03:45 停工）
- 状态：草案（对抗审中 → 定稿）
- 文档清单：无详设（单文档方案，本文件即完整设计）

## 1. 需求与用户裁定

### 1.1 用户裁定（2026-11-16 凌晨，口头指令存档）

1. 按 `od-dev-write-application` 把末日幻影做成 app；选人策略**暂时随机**，先把流程串起来。
2. 时间富余则同构串虚构叙事、忘却之庭（本迭代不含，外溢面）。
3. **不进一条龙**（`DEFAULT_GROUP = False`）；不做 GUI；不做通知配置。
4. 当晚用户睡觉，全程不询问，靠子agent无前提评审把关。

### 1.2 范围

- 做：末日幻影单次挑战的完整链路 app 化——导航 → 进编队屏探测规模 → 随机选人 → 装配增益 → 挑战战斗 → 领取期次奖励 → 回大世界。
- 不做（明确排除，防外溢）：异相仲裁；难度选择（打当前默认选中难度）；选关多关循环；星数检测与满星判定；已通关跳过检测；选人策略优化（随机占位，留策略接缝）；GUI；一条龙接入；忘却之庭/虚构叙事（外溢面，自成新迭代）。

## 2. 现状与复用盘点

末日幻影单次挑战的 op 层已实机打通（依据：`sr-od-treasures-lightward` skill 现状边界节 + 各 op 文件 docstring 的实机标注），app 层缺失（`list_applications` 无本玩法条目）。复用清单：

| 环节 | 复用件 | 位置 | 状态 |
|---|---|---|---|
| 导航到选关 | `GotoTreasuresLightward` | `src/sr_od/application/treasures_lightward/operations/goto_treasures_lightward.py` | 实机验证（末日幻影收尾=选关双锚） |
| 编队选人 | `TlAsTeamFillOp` | `operations/apocalyptic_shadow/team_fill.py` | 实机验证（星启/双节点双路径） |
| 增益装配 | `TlAsAxiomEquipOp` | `operations/apocalyptic_shadow/buff_equip.py` | 实机验证 |
| 挑战组合 | `TlApocalypticShadowChallengeOp` | `operations/apocalyptic_shadow/challenge.py` | 实机验证（含选关→编队多态入口/更换编队弹窗/快速通关弹窗） |
| 领取期次奖励 | `TlRewardClaimOp` | `operations/apocalyptic_shadow/reward_claim.py` | 实机验证（两 tab 一键全领） |
| 返回大世界 | `BackToNormalWorldPlus` | `src/sr_od/operations/back_to_normal_world_plus.py` | 项目通用收尾（开拓力 app 同款） |

新增代码只有 app 编排层（五件套 + 编排节点 + 随机策略函数），零新画面交互。

## 3. 流程设计（四段式骨架）

起点 = 主界面（app 由框架自动进游戏，`SrApplication` 默认 `need_check_game_win=True`）；终点 = 大世界。

```
① 导航段
  [任意画面] --GotoTreasuresLightward(APOCALYPTIC_SHADOW)--> 末日幻影-选关
② 玩法段
  [末日幻影-选关] --[点 按钮-前往挑战 | 按钮-重新挑战]--> 末日幻影-编队
  [末日幻影-编队] --[read_team_nodes 读节点行数]--> 规模=2行(01-03)或3行(星启04)
  [编队屏] --随机选人(纯逻辑,不流转)--> team_names(8/12人) + buff_slots(全1)
  [编队屏] --TlApocalypticShadowChallengeOp--> 末日幻影-选关(挑战完成)
③ 领奖段
  [末日幻影-选关] --TlRewardClaimOp--> 末日幻影-选关(两 tab 领取完成)
④ 返回段
  [末日幻影-选关] --BackToNormalWorldPlus--> 大世界
```

- ② 的「探测规模」是 app 编排节点（非独立 op）：需要**在构造挑战 op 之前**知道 8 人还是 12 人（`TlAsTeamFillOp` 构造校验 8/12，`team_fill.py` L96-97），而编队屏行数只有进了编队屏才能实读。进入编队屏的点击复用选关屏已建档 area（`按钮-前往挑战`/`按钮-重新挑战`，challenge.py 入口节点 L141-150 实证过两态），点击后以编队屏双锚（`标题-末日幻影行`+`标题-编队行`）验证到达；行数判定复用 `read_team_nodes`（`obs/tl_team_obs.py`，team_fill 同款调用方式）。探测节点完成后挑战组合 op 的入口节点检测到已在编队屏直接接续（challenge.py L121-125），无重复导航。
- 领奖段归属裁定：挑战成功会新增可领奖励，故领奖放**挑战之后**一次完成（挑战前不领，旧奖励由本次一并覆盖；祭礼奖励不领取不会过期，依据：`docs/game/screens/末日幻影-祭礼奖励.md` 奖励行三态为「可领/已领/未达成」，无时效态）。
- 随机选人节点是纯逻辑（无画面操作）：从角色池随机抽取，行序拼接（行1=节点一）。增益固定选每行第 1 张（占位策略，`buff_slots=(1,)*行数`，1 基序号——增益名称随期轮换，按位置选择是既有口径，依据 challenge.py L103-104 docstring）。

## 4. 新增代码结构

包：`src/sr_od/application/apocalyptic_shadow/`（内置应用，绝对导入，跟随 trailblaze_power 五件套命名）

| 文件 | 内容 |
|---|---|
| `__init__.py` | 空 |
| `apocalyptic_shadow_const.py` | `APP_ID='apocalyptic_shadow'` / `APP_NAME='末日幻影'` / `DEFAULT_GROUP=False` / `NEED_NOTIFY=False` |
| `apocalyptic_shadow_config.py` | `YamlConfig` 子类：`claim_rewards: bool = True`；`character_pool: list[str]` 默认 = 内置快照池；模块常量 `DEFAULT_CHARACTER_POOL`（2026-11-16 米游社 `mys_get_characters` 65 人名单 ∩ `CHARACTER_LIST` 校验 = 64 人，「开拓者」因常量表按命途拆名被排除） |
| `strategy.py` | `pick_random_teams(pool, team_count) -> list[str]`：`random.sample` 无放回抽取 `team_count*4` 个；纯函数零副作用（未来换真策略的接缝） |
| `apocalyptic_shadow_run_record.py` | `AppRunRecord` 子类：`check_and_update_status()` 恒重置（每次都跑，独立工具语义，同 trailblaze_power_run_record L16-17 口径） |
| `apocalyptic_shadow_app_factory.py` | `ApplicationFactory` 子类：`create_application` / `create_config` / `create_run_record` 三件全实现；app 构造时显式传入 run_record 与 config（不挂 Context 接线，依据 skill §4.4「通常 factory 就够」） |
| `apocalyptic_shadow_app.py` | `SrApplication` 子类，节点图见 §3；启动时校验角色池（池内名字必须 ∈ `CHARACTER_LIST` 的 cn 名，不合法的名字剔除并打日志；池不足以凑 `team_count*4` 人 → 显式失败） |

app 运行时配置实例与 factory 共用同一 ApplicationConfig 文件（`config/<实例>/one_dragon/apocalyptic_shadow.yml`）。MCP 配置工具的路由表是**显式注册制**（`src/sr_od/backend/config_router.py` 的 ROUTES，app 配置不会因 factory 实现了 create_config 而自动出现——实测 `describe_config` 报「不支持的 app_id」），本迭代在该表补 `apocalyptic_shadow` 条目（field-only 形态，同「每月合成」）：可写字段 `claim_rewards`；`character_pool` 为列表字段，`set_config` 写不了（工具值类型仅 str/int/bool），保持 `get_config` 可读、改池走 yaml 编辑。连带修复共享层 bug：`set_config` 的 handler 对布尔字段做字符串矫正（实测 MCP 客户端会把 JSON 布尔序列化成 `'false'` 字符串落盘，Python 侧为真值、开关语义反转；`config_app.py`），月度兑换/合成两条 bool 路由同享此修复。

## 5. 失败处理语义（编排设计约定）

| 失败点 | 语义 | 理由 |
|---|---|---|
| ① 导航失败 | **中止**，app 失败 | 后续步骤无从谈起 |
| ② 探测规模失败 | **中止** | 无法定选人数量；选关/编队屏画面异常需要人看 |
| ② 挑战失败 | **中止**，运行记录不标完成 | 挑战是本 app 的核心产出；失败重跑语义 = 重新挑战 |
| ③ 领奖失败 | **继续**，节点状态记警告，app 仍成功收尾 | 主产出（挑战）已完成；祭礼奖励无时效（§3 依据），下次运行补领 |
| ④ 返回失败 | **中止**，app 失败 | 返回段是四段之一；失败意味着停在大世界以外画面，如实报失败 |

## 6. run_record 设计

- 重置周期：**恒重置**（`check_and_update_status` 直接 `reset_record`）——本 app 是独立工具（不在一条龙），没有「本周期已跑就跳过」的需求，每次调用都是明确意图；成功/失败状态照常落盘留历史（`AppRunRecord` 默认能力）。
- 业务字段：无（挑战结果、领取数量不落业务字段；结算信息在日志与游戏内可见。字段留给策略迭代时再加）。

## 7. config 设计

| 字段 | 类型 | 默认 | 语义 |
|---|---|---|---|
| `claim_rewards` | bool | `True` | 是否执行③领奖段；`False` 时跳过该节点 |
| `character_pool` | list[str] | 内置 64 人快照 | 随机选人的候选池；空列表 = 回落默认快照池 |

- 运行态字段无。MCP 配置工具验收（describe/get/set 一轮）进端到端验收判据。

## 8. 随机选人策略（占位）

- `pick_random_teams(pool, team_count)`：无放回随机抽 `team_count*4` 个名字；不做任何强度/属性/弱点考量（用户裁定：乱选）。
- 已知边界（如实声明）：随机队可能战败或低分——末日幻影战斗以「剩余行动值」计分，行动值耗尽 = 低分结算不视为失败流程（challenge.py L44 实证口径），流程不受影响；随机队含当期试用角色的风险由池来源消除（池 = 账号持有名单快照，试用角色不在 `mys_get_characters` 名单内）。
- 名字对齐防线：池构建时 ∩ `CHARACTER_LIST`（app 启动校验，§4）；`TlAsTeamFillOp` 构造处还有第二道同名校验（team_fill.py L108-109）。

## 9. 验收判据

1. `uv run ruff check` 通过（仅本迭代新增/修改文件）。
2. 重启 MCP server 后 `list_applications` 出现 `apocalyptic_shadow`（`in_standalone_list` 或注册列表可见）。
3. `run_standalone_app(app_id='apocalyptic_shadow')` 实机端到端：从当前画面出发 → 选关 → 编队 → 随机编队 → 挑战战斗 → 结算回选关 → 领奖 → 大世界收尾；运行记录成功。
4. MCP 配置工具：`describe_config` 能看到两个字段且语义清晰；`get_config`/`set_config` 改 `claim_rewards` 读回一致。
5. 子agent无前提实现评审意见收敛（阻塞项修完，建议项裁定留档）。

## 10. 待实机核对清单（核销表）

| # | 待核对项 | 核对时机 |
|---|---|---|
| 1 | 选关屏默认选中难度 = 最高可玩（本设计不主动选难度） | 端到端运行观察 |
| 2 | 探测节点两分支：未通关=「前往挑战」大按钮 / 已通关=「重新挑战」 | 端到端运行观察 |
| 3 | 星启（04）默认选中时 3 行探测 → 12 人链路 | 若当晚默认选中为 04 则顺带核销，否则挂账下期 |
| 4 | 池内名字与编队屏列表卡识别名一致（64 人快照） | 端到端运行（填充失败即暴露） |
| 5 | 已通关难度重新挑战的「更换编队确认」弹窗在 app 链路中被组合 op 正常处理 | 端到端运行观察 |

## 11. 关键取舍

- **探测规模做 app 节点而非独立 op**：它只为「构造挑战 op 前定人数」服务，单独暴露给 MCP 意义弱；复用 `read_team_nodes` 与已建档 area，逻辑 ~30 行。将来虚构叙事/忘却之庭 app 化不需要它（固定 8 人），不值得为此抽公共 op。
- **领奖放挑战后单次**：见 §3 归属裁定；挑战前领奖是纯冗余运行时。
- **角色池 = 快照常量 + config 可覆盖**：今晚无 GUI 无米游社运行时依赖的最小闭环；缺点 = 名单随账号变动会过期，过期表现为填充失败「列表到底未找到」（可定位、可修）。根治（编队屏实机扫描建池）留策略迭代。
- **难度不选择**：挑战组合 op 明确不选难度（challenge.py L19-21），默认选中即最高可玩（skill 口径），与「先串流程」目标一致；难度配置项留外溢迭代。
