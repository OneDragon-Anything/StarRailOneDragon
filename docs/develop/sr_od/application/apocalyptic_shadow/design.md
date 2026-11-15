# 末日幻影独立应用（as-built 设计正文）

> 本文是 `apocalyptic_shadow` 应用的正本设计（as-built）：写系统现在的结构与语义，与代码现状一致。
> 过程与迭代史见 `changes/`（迭代内工件，寿命 = 迭代）；数值单一源在代码，本文只写常量名。

## 1. 定位与边界

- 逐光捡金·末日幻影的一键挑战独立应用：`run_standalone_app(app_id='apocalyptic_shadow')` 触发，主界面起、大世界收，单次运行挑战**当前默认选中难度**（=最高可玩，含星启）一次。
- 不进一条龙（`DEFAULT_GROUP = False`）、无 GUI、无通知配置；选人策略为随机占位（用户裁定 2026-11-16），真策略接缝在共享模块 `treasures_lightward/random_team.py`。
- 明确不做：难度选择、多关循环、星数/满星检测、已通关跳过、异相仲裁。

## 2. 结构

包 `src/sr_od/application/apocalyptic_shadow/`（内置应用，约定式自动发现 `*_factory.py` + `*_const.py`）：

| 文件 | 职责 |
|---|---|
| `apocalyptic_shadow_const.py` | `APP_ID='apocalyptic_shadow'` / `APP_NAME='末日幻影'` / `DEFAULT_GROUP=False` / `NEED_NOTIFY=False` |
| `apocalyptic_shadow_config.py` | `ApplicationConfig` 子类，落 `config/<实例>/<组>/apocalyptic_shadow.yml`；字段 `claim_rewards: bool = True`、`character_pool: list[str]`（空回落共享默认池；剔除不合法名后不足 = 显式失败） |
| `apocalyptic_shadow_run_record.py` | `AppRunRecord` 恒重置口径（独立工具无周期跳过语义；成功/失败照常落盘） |
| `apocalyptic_shadow_app_factory.py` | factory 三件全实现（application/config/run_record），app 构造显式传 run_record，不挂 Context 接线 |
| `apocalyptic_shadow_app.py` | 节点图（§3） |

复用件（不修改）：`GotoTreasuresLightward`、`TlApocalypticShadowChallengeOp`（及其子 op fill/equip/battle/battle_exit）、`TlRewardClaimOp`、`BackToNormalWorldPlus`，均在 `sr_od/application/treasures_lightward/` 与 `sr_od/operations/`。共享随机选人：`sr_od/application/treasures_lightward/random_team.py`（默认池快照 ∩ CHARACTER_LIST 校验说明见其 docstring）。

MCP 配置路由：`src/sr_od/backend/config_router.py` 显式条目 `apocalyptic_shadow`（field-only），可写字段 `claim_rewards`；`set_config` 布尔字符串矫正见 `config_app.py`（共享修复）。

## 3. 节点图（四段式）

```
① 前往末日幻影(start)  = GotoTreasuresLightward(APOCALYPTIC_SHADOW)
② 进编队屏探测规模      = 选关屏状态机(见 §3.1) → read_team_nodes 实读行数(2=01-03 / 3=星启04)
   随机选人             = ∩CHARACTER_LIST 过滤 → random_team.pick_random_teams(行数×4) → buff_slots=全1
   执行挑战            = TlApocalypticShadowChallengeOp(team_names, buff_slots)，带换人重选(§4)
③ 领取期次奖励         = TlRewardClaimOp(claim_rewards=False 时跳过；失败不阻塞收尾)
④ 返回大世界           = BackToNormalWorldPlus
```

### 3.1 探测节点状态机（选关屏 → 编队屏）

分支序（每轮按截图重新分流，语义与 challenge.py 入口节点同源）：
1. 首领简报横幅可见 → 显式失败（编队满员态已用旧队发起挑战，与本 app 换队目标冲突）；
2. 编队屏双锚（`标题-末日幻影行`+`标题-编队行`）→ 读行数（`read_team_nodes` 读空重试=遮挡容错；行数∉{2,3} 显式失败）；
3. 「更换编队确认」弹窗 → 点确认重试；
4. 「前往挑战」/「重新挑战」/「更换编队」按钮 → 点击重试（until 编队屏双锚）。

## 4. 失败处理语义

| 失败点 | 语义 |
|---|---|
| ① 导航失败 | 中止 |
| ② 探测规模失败 | 中止 |
| ② 挑战失败（「列表到底未找到 X」） | 剔除 X 重选重试，预算 = 初选+2（`random_team.extract_missing_name`/`re_pick`；填充 op 先清空再填可安全重入） |
| ② 挑战失败（其余） | 中止，运行记录不标完成 |
| ③ 领奖失败 | 继续（`round_success('领奖失败,继续收尾')` 状态串+日志；祭礼奖励无时效，下次运行补领） |
| ④ 返回失败 | 中止 |

## 5. 已知边界与挂账（2026-11-16 实机口径）

- **随机队 vs 星启战力现实**：默认选中=星启 04（实测），随机占位队在机制门 boss（召唤物免疫门）上可能无法在有效时间内完成战斗——这是「选人策略暂时乱选」的直接代价，构成下批引入真实选人/难度策略的实证触发（skill od-dev-write-application §6 引入判据）。
- **狩猎版三月七不可扫**：编队屏角色列表整列表遍历从未出卡（脸库有模板、裁片可识别），根因待查；换人重选韧性兜底。
- **列表尾部卡盲区**：网格建档 rect 曾止于第四行，尾部卡不可扫——已修（`treasures_light_team.yml` `区域-角色网格` 下界 960；实测依据：末页第五行标签 y=884-909、底部排序控件 y=974-1001）。
- **节点战斗「发起战斗」点画面中心**（`battle.py` 节点战斗循环）：boss 偏离画面中心时点击落在己方角色上，开战无效（2026-11-16 实机复现，人工点攻击键立即开战）——挂账：开战点击应锚定攻击按钮 area（坐标单一真相源建档），下批修。
- 中断恢复：游戏重启后恢复到进行中的挑战节点画面，「进入游戏」op 不识别该画面会判失败——先经 `BackToNormalWorldPlus` 收回大世界再跑 app。
