# 升级 op 失败适配与行迹重构（迭代设计·总纲）

## 0. 状态

设计稿 v1（对抗审前）。流程：本设计 → 无前提对抗 → 修订收敛 → 负责人批准 → 按 landing.md 落地。

## 1. 背景与动机

weekly-challenge-core 迭代（`docs/develop/sr_od/application/echo_of_war/changes/weekly-challenge-core/`）为周本挑战建立了共享失败继续件 `ResumeFromBattleFail`（challenge_mission 包）并接入周本核心；实机验证了「大世界-战斗失败」新形态（无结算按钮、点空白回挑战画面）。家族其余成员的战斗循环仍在旧形态假设下运行——负责人指令：**其他的升级 op 也做类似的适配**（先设计、再对抗）。

现状风险盘点（依据 = 各实现文件行号，2026-11-14 代码现状）：

| 成员 | 战斗循环位置 | 失败画面现状行为 | 风险 |
|---|---|---|---|
| `UseTrailblazePower`（体力计划一条龙 + FarmLightConeMaterialOp 委托链） | use_trailblaze_power.py 全节点图 | `_after_battle_result`（:290-307）失败后找「战斗画面·退出关卡/再来一次按钮」——新形态两者皆无 → retry 预算耗尽 FAIL，失败画面残留 | 卡死级（一条龙挂） |
| `UpgradeCharacterOp` 手动路线（角色晋阶，farm_dungeon + 非 use_fast_ticket） | manual_fight（upgrade_character.py:726-760）+ 返回分类 back_to_ascend（:766+） | 失败画面 = 非编队态 → BATTLE_DONE → 返回分类无该画面分支 → 过渡帧慢询 → 节点 300s 超时 FAIL；败场开拓力已扣、料未刷到、失败画面残留 | 死胡同级（op FAIL + 现场残留） |
| `UpgradeLightConeOp` 手动路线（光锥晋阶，同上形态） | 手动挑战战斗（upgrade_light_cone.py:661-690）+ 刷取返回分类 back_after_farm（:696+） | 同构同风险 | 同上 |
| `UpgradeTraceOp`（行迹升级） | 无战斗循环（券刷走游戏内快速刷取；手动刷本划出 op 边界归 agent 层） | 不受失败形态影响；但 op 本体仍是「树态固定坐标点节点」旧契约（upgrade_trace.py:5-9 逐角色一致性未验），与负责人裁定的面板态契约不符 | 重构欠账（非失败形态） |

## 2. 范围

### 做什么（四个工作块）

- **块 A：UseTrailblazePower 失败形态适配 + 迁移开拓力 app**——三处失败消费点接入 `ResumeFromBattleFail`；op 由 `challenge_mission/` 迁至 `application/trailblaze_power/`（负责人既定裁定：花萼的 op 归开拓力 app）。详见 details/fail-adaptation.md §1。
- **块 B：角色线手动路线失败适配**——`UpgradeCharacterOp` 返回分类增加失败画面分支：委托共享件回挑战画面后按预算重发。详见 details/fail-adaptation.md §2。
- **块 C：光锥线手动路线失败适配**——`UpgradeLightConeOp` 同构适配。详见 details/fail-adaptation.md §3。
- **块 D：UpgradeTraceOp 面板态重构**——起点/终点改面板态↔树态契约、删除固定节点坐标、参数面对齐光锥/角色线、券耗常量按实测回填、连刷次数接入、实值记账。详见 details/trace-rework.md。

### 明确不解决（边界外，各有去处）

- **`ChallengeEchoOfWar`（周本 app）的失败适配与超时防线**——非升级 op；其占位 `echo_of_war/changes/echo-of-war-fail-adaptation/`（含对抗审前草案）保留，与 `battle-loop-unification`（app 切核心收敛）动机重叠，归周本域后续一并处理。
- **battle-loop-unification（家族循环收敛为共享件）**——强制触发条件（版本再变迫使家族逐件适配）未满足；本次是共享件消费推广，不是循环重构，收敛面经本次缩小（家族手写循环 −1：UseTrailblazePower 失败分支改委托后，其循环骨架仍在）。
- **UpgradeTraceOp 的手动刷本 op 化**——维持负责人裁定：手动刷（花萼直进/周本）划出 op 边界，agent 层编排（行迹侧周本手动刷已由 `ChallengeEchoOfWarByName` 承接；花萼侧走 `FarmLightConeMaterialOp`，其委托链的卡死风险由块 A 收口）。
- **角色/光锥线 farm_dungeon 券路线（use_fast_ticket=True）**——游戏内快速刷取直领奖，无战斗画面，零适配。

## 3. 方案概览

- **共享件复用**：全部失败分支消费 `ResumeFromBattleFail`（challenge_mission 包，weekly-challenge-core 3.1 落地，含两态分流/连等封顶/转态验锚，本迭代零改动零新增消费接口）。家族先例 = 周本核心 ⑪ 失败画面继续节点（weekly-core.md 节点卡）。
- **重发/判停策略按循环语义各定**：UseTrailblazePower 失败重发回链定死「选择次数」节点（滑条重算本轮次数，记账自洽——占位草案既定）；连败达阈值（家族口径 5）→ 关副本退出交既有收尾。角色/光锥线失败计场（开拓力已扣）→ 按既有 `farm_rounds_max` 预算重发（预算天然封顶，不另设连败阈值——每轮失败消耗已获 farm_dungeon 授权，重发边际成本即一场开拓力；预算耗尽判停即自然报告）。
- **迁移机械件**：UseTrailblazePower 迁移 = 文件搬移 + 两处 import 消费方（trailblaze_power_app.py:15、farm_material.py:40）+ 测试镜像路径同步；类名/签名/行为除失败分支外零变更。
- **判据同步声明**：`sr-od-test/test/sr_od/challenge_mission/test_use_trailblaze_power_timeout.py:112-129` 锁「超时收尾见战斗失败 → 点战斗画面·退出关卡按钮」旧行为，块 A 改为「委托共享件 → 关副本退出」后该断言必红——落地时同步改写（不是回归）。

## 4. 外溢面

- 周本 app 适配与循环统一：占位不变（`echo_of_war/changes/echo-of-war-fail-adaptation/`、`echo_of_war/changes/battle-loop-unification/`）。
- 光锥/角色手动刷失败后的回家链落点：块 B/C 落地前需一次可逆实机走查（失败画面 → 共享件回挑战画面的落点识别依据：挑战画面 = 资源窗口「进入」的落点形态，画面档已建）——失败触发为自然条件态（低练度打高难副本），实机验证批纳入 landing。

## 5. 验收口径

每块 mock 场景全过 + ruff；块 A 另含既有超时测试的判据同步改写；实机验证按 landing 分阶段，消耗类 E2E 逐次授权。
