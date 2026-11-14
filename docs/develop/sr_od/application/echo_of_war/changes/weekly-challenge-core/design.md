# 周本挑战核心与行迹刷取接入 迭代设计（总纲）

## 0. 元信息
- 迭代目标：行迹升级重构建取侧——周本挑战循环抽核心 op 并接入行迹、配队沿用计划配置、花萼与体力计划共用、战斗失败新形态适配（用户裁定 2026-11-14：本次只做核心 op 且只在行迹接入，核心放周本 app 包，周本 app 切换后续处理）
- 状态：定稿（四轮对抗收敛，报告见 attack.md；落地待用户批准开工）
- 文档清单：
  - details/weekly-core.md —— 周本挑战循环核心 op（节点卡/status/MCP 契约/mock 场景表）
  - details/trace-integration.md —— 行迹侧接入：周本按名包装（配队解析）+ 花萼共用口径
  - details/fail-form-adaptation.md —— 共享失败继续件 `ResumeFromBattleFail`（两 app 侧接入外溢占位目录）

## 1. 问题与动机
- 现状症状：
  1. 行迹升级的周本手动刷能力缺失，agent 层无法一条 `run_operation` 完成周本刷取；其花萼券刷四态推进已实现（`upgrade_trace.py:296-320`），但连刷次数参数为占位（`:85-87`）、券耗常量未按实测回填（`:56-58` 写 3，实测口径花萼赤 10+券 1/次）；
  2. 周本挑战机制 `ChallengeEchoOfWar` 与运行时对象参数捆绑（`mission: GuideMission`，类 docstring 自声明「非 MCP 传参单元」），agent/MCP 层不可用；
  3. 版本更新后战斗失败画面为新形态：无「退出关卡/再来一次」按钮，只有「点击空白区域继续」回挑战画面（实测记录：本迭代探索目录 screen-flow.md「战斗失败流程」节，测试仓外探索存证）；`use_trailblaze_power._after_battle_result`（use_trailblaze_power.py:297-307）、`_wait_battle_result_timeout` 判负分支（:273-275 → :286-287）与 `ChallengeEchoOfWar._after_battle_result`（challenge_ehco_of_war.py:188-193）三处失败消费点都找不存在的按钮 → 无限重试卡死；且 `ChallengeEchoOfWar` 战斗等待无节点超时防线（round_wait 无限继续）；
  4. 周本次数耗尽（0/3）可零开拓力挑战但无奖励（负责人口径 2026-11-14）——语义为「不打」，现有 app 已按取消退出处理（challenge_ehco_of_war.py:106-114）。
- 根因归层（表示/约定/流程/语义）：**流程层**为主——挑战循环＋战斗结果处理没有公共件（失败形态修法会长出三份以上同构实现即为证据），周本挑战能力被周本 app 独占；**语义层**为次——游戏失败画面形态变更后识别/处理未跟进。两根同源于「挑战机制家族无公共件」，本迭代以核心 op＋共享失败继续件收敛（收敛面收窄声明见 fail-form-adaptation.md 关键取舍）。
- 解决到哪：核心 op 新增、共享失败继续件新增（本迭代仅核心消费）、行迹侧按名包装接入（含配队从周本计划解析）。
- 明确不解决：
  - ChallengeEchoOfWar 切换到核心（后续迭代，本迭代两套并存为已知临时重复；收敛承载见外溢迭代 `changes/battle-loop-unification/`）；
  - 周本 app 与开拓力 app 的接入（用户裁定 2026-11-14）：`ChallengeEchoOfWar` 失败适配+战斗超时防线 → 外溢迭代 `changes/echo-of-war-fail-adaptation/`；`UseTrailblazePower` 迁移开拓力 app + 失败适配 → 外溢迭代 `docs/develop/sr_od/application/trailblaze_power/changes/use-trailblaze-power-rehome/`（占位均已立，设计草案随迁）；
  - 光锥/角色手动路径失败适配 → 外溢迭代 `docs/develop/sr_od/application/cultivation/changes/manual-fail-form-cultivation/`（占位已立）；
  - 战斗循环与 UseTrailblazePower 的深度统一 → 外溢迭代 `changes/battle-loop-unification/`（占位已立）；**强制触发条件：挑战机制相关画面/流程下次随版本再变时必须立项**（防「后续再说」烂尾）；
  - 行迹升级 op 本体的节点选择重构与券耗常量回填 → 外溢迭代 `docs/develop/sr_od/application/cultivation/changes/trace-upgrade-rework/`（占位已立）；
  - agent 手动刷路径的 run_record 记账：核心/包装不写 `echo_of_war_run_record`（left_times 清零除外，见 trace-integration.md）、不写开拓力消耗流水——手动路径的消耗由日志承载、由调用方向用户汇报；一条龙编排路径的记账不受影响（app 路径照旧）；
  - 一条龙编排本身；行迹花萼券刷的连刷参数接入与券耗常量回填（归 trace-upgrade-rework 外溢迭代）。

## 2. 方案
- 系统级变化：
  1. 新增 `ChallengeEchoOfWarCore`（echo_of_war 包）：起点 = 挑战副本-历战余响·挑战态，入口由调用方负责；纯参数 `team_num`/`plan_times`/`support`；战斗失败新形态处理内置（经共享失败继续件）；中文 status 出口（details/weekly-core.md）；
  2. 新增共享失败继续件 `ResumeFromBattleFail`（challenge_mission 包）：失败画面点空白 → until 挑战画面锚回归；核心⑩与两处失败适配共用（details/fail-form-adaptation.md）；
  3. 新增周本按名挑战包装 op（echo_of_war 包）：mission 中文名/ID → 查周本计划配队（含 'none'→None 翻译）→ 回大世界 → 传送 → 核心 → 收尾回大世界；MCP 可 `run_operation`（details/trace-integration.md）；
  4. 行迹侧手动刷链路口径：周本 = 包装 op；花萼 = 沿用 `FarmLightConeMaterialOp`（材料反查直达 + 委托 `UseTrailblazePower(skip_transport=true)`，已存在实机验证——探索记录与 game-coach「已建成的养成 op」节有实跑记录），零新建；`UseTrailblazePower` 的失败适配与迁移开拓力 app 为外溢迭代（不在本迭代）。
- 配队解析分层契约（跨详设接口，唯一必须在总纲定死的深度内容）：
  - **核心与共享挑战机制只收纯参数**（`team_num`/`support`），不读任何计划配置；`support` 约定为 None = 不用支援（核心委托前把 'none' 归一为 None，见 weekly-core.md ⑤）；
  - **带 mission 语义的层负责查计划出配队并做 'none'→None 翻译**：周本包装查 `EchoOfWarConfig.plan_list`（echo_of_war_config.py:29-59，周本全量补齐保证按 mission_id 必可查）；花萼编排层查体力计划（trailblaze_power_config.py 的 plan_list 项 team_num/support——执行期配队即计划项字段；`get_history_by_uid`（:223）是新建计划项取历史默认的后备，非执行期解析）；
  - `team_num=0` = 沿用游戏内当前编队（choose_team.py:30「传 0 直接视为成功(跳过选择)」；trailblaze_power_config.py:14「0代表游戏内当前配队」）；包装层在计划项 team_num=0 时于日志显式报「计划配队=0，将沿用当前编队」（授权显性化）；
  - `FarmLightConeMaterialOp` 维持 `team_num` 参数现状（默认 0 = 当前编队，花萼难度低接受；配队解析归其编排调用方，本迭代不引入计划解析）。
- 详设划分与跨详设接口契约：weekly-core.md 定义核心构造签名与 status 集合（全名单亦列于 trace-integration.md 包装节点 3，防跨详设拼凑），是 trace-integration.md（包装委托核心）与 fail-form-adaptation.md（共享件与退出语义对齐）的共同契约；共享失败继续件 `ResumeFromBattleFail` 定义于 fail-form-adaptation.md，weekly-core.md ⑩ 与 landing 3.2/3.3 以其为准；包装 op 是行迹侧唯一新增入口。
