# 落地：升级 op 失败适配与行迹重构

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过（含测试文件）；
- 受影响测试全量一次通过（按阶段点名：challenge_mission / trailblaze_power / cultivation 相关子集）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交逐文件点名 `git add`（禁 `-A`/目录级），提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节；
- 范围红线（本设计 §2「明确不解决」）：不触碰 `ChallengeEchoOfWar`（周本 app）、不做家族循环收敛重构、不给 UpgradeTraceOp 加手动刷本路线——落地时发现触碰需求即停手上报。

### 3.1 块 A：UseTrailblazePower 迁移 + 失败适配

**范围**：迁移件（文件搬移 + 三处 import 消费方 + 等待窗常量抽 `challenge_mission/battle_wait_windows.py` + 测试镜像路径与桩路径）一个提交；失败适配（「失败画面继续」新节点 + 「战斗结果处理」收窄胜利路径 + 超时判负改委托 + 失败/超时出口复用既有 `back_at_last`）一个提交；既有测试判据同步改写（design.md §3 声明的 :112-129 必红改写）；mock 五场景（details/fail-adaptation.md §1.4）。
**设计依据**：details/fail-adaptation.md §1 全节。
**文件面**：`src/sr_od/challenge_mission/use_trailblaze_power.py` → `src/sr_od/application/trailblaze_power/use_trailblaze_power.py`（迁）、`src/sr_od/challenge_mission/battle_wait_windows.py`（新，常量抽取）、`challenge_echo_of_war_core.py`（常量 import 改源）、`trailblaze_power_app.py`、`farm_material.py`（import）、测试仓镜像路径 + 断言改写 + 新增场景。
**依赖**：无。
**优先级建议**：0
**完成判据**：mock 五场景全过；既有胜利链/超时判胜回归通过；判据同步改写后的判负断言锁新行为；ruff。
**验收凭据形式**：pytest 场景名清单 + `challenge_echo_of_war_core` import smoke（常量断链修复确认）。
**既有测试判据同步声明（必红改写，非回归）**：
- 主仓 `challenge_echo_of_war_core.py` 常量 import 改源属**迁移机械修正**，非「触碰周本 app」范围扩展（范围红线豁免：改动限于 import 行，零行为变更）；
- 测试仓 `test_challenge_echo_of_war_core.py:40-42` 常量 import 同步改源（:73-75 窗口值断言不变）；
- `test_use_trailblaze_power_timeout.py:91/:116/:135` 三处 monkeypatch 桩路径字符串 `sr_od.challenge_mission.use_trailblaze_power.…` 随迁移改源；
- `back_at_last` 既有死边 `@node_from('点击挑战后确认', status='退出关卡按钮')`（:340，无产生点）随边表改造顺带清理。

### 3.2 块 B/C：角色线与光锥线手动路线失败适配

**范围**：两文件同构适配——返回分类首位「失败画面」分支（委托共享件 + **分支内联预算检查**：重发/预算耗尽判停/透传三分支）+ 失败重发回链（角色线挂 `farm_in_dungeon`、光锥线挂 `副本刷取分流`）+ 判停回家链复用既有节点；mock 十场景（details/fail-adaptation.md §2.3 五条 + §3 同构五条）。
**设计依据**：details/fail-adaptation.md §2/§3。
**文件面**：`upgrade_character.py`、`upgrade_light_cone.py`、`sr-od-test/test/sr_od/application/cultivation/`（两测试文件）。
**依赖**：3.1（顺序语义：先收口委托链再收口消费方，验收视角——共享件本体早已落地）。
**优先级建议**：6
**完成判据**：mock 十场景全过（含连败至预算耗尽场景）；券路线回归确认通过；两线计场时机维持现状（不统一）；ruff。
**验收凭据形式**：pytest 场景名清单（含预算检查命中断言：失败重发环每轮都过预算检查）。

### 3.3 块 D：UpgradeTraceOp 面板态重构

**范围**：起点/终点契约改面板态↔树态、删固定节点坐标与 `_SKILL_NAMES` 枚举、`target` 改校验锚语义、`auto_farm`→`farm_dungeon` 改名、券耗回填 1、连刷次数接入（`_set_farm_times` 同款）、光锥线补全双形态平移（实做项）、循环内分类失改 fail 交 agent、面板等级收尾读数记账、收尾关面板节点（新建「点击区-关面板空白」area，`_final_status` 出口机制）；mock 七场景（details/trace-rework.md §3）。
**设计依据**：details/trace-rework.md 全节。
**文件面**：`upgrade_trace.py`、`character_traces.yml`（新建「点击区-关面板空白」area + 复用既有「读区-技能分类」/「读区-面板等级」两 area——坐标不符则纠档）、`sr-od-test/test/sr_od/application/cultivation/`（行迹测试文件）。
**依赖**：无（与 3.1/3.2 无代码耦合）。
**优先级建议**：6
**完成判据**：mock 七场景全过；升级循环按钮态判定回归（平移段零行为变更）；ruff。
**验收凭据形式**：pytest 场景名清单。
**既有测试判据同步声明（必红改写，非回归）**：`test_upgrade_trace.py` 锁现版节点图剧本（优先级⓪~⑤、「标题-材料补全弹窗」轮界锚、构造参数 `auto_farm`）——块 D 改契约两端与参数面后**近全文件失配必红**：轮界锚改面板态锚、构造参数改 `farm_dungeon`、状态集合按新出口集改写；另有三处点名——`:173/:205/:269` 的 `level_reads` 计数断言（收尾读数记账新增一次面板等级读取，计数语义变化）、`:207-234` 分类失配重点节点测试（循环③删除后该场景改为「fail 交 agent」语义，测试改写或删除）；落地时按本声明逐条改写，不逐条判断过时性（改动面 = 设计 §1 契约变更总览全表 + 上述点名）。

### 3.4 实机验证（消耗逐次授权）

**范围与顺序**：块 D 零消耗段先行（面板校验失败路径 + 缺料判停路径，阿哈样本材料 0 态可零消耗触发）→ 块 A 花萼场一场（开拓力 30，体力计划授权场景）→ 块 B/C 手动路线各一场（开拓力 10/30）→ 块 D 券刷一场（开拓力 10 + 券 1，E2E 授权；**确认刷取后回面板落点为本次验证项**——取消路径已实测）。
**失败分支主动触发法（授权降配败场走查）**：临时降配队（低练度编队）+ 正常打一场即必败，一次走通「失败画面 → 共享件 → 重发链 → 连败/预算止损 → 收尾」全链——成本上限 = 阈值场数 × 单场开拓力（块 A 5×30=150；块 B/C = `farm_rounds_max` × 10/30）；属正常游戏操作（真实降配，禁注入/mock 画面）。是否执行由负责人逐次授权。
**完成判据**：各块 run 日志可复盘；未授权降配走查时，失败分支实机验证如实挂账（mock 已锁语义，实机遇自然失败时按现场处理协议补验）。
**依赖**：3.1-3.3；MCP server 重启。

### 末阶段：正本更新

**正本更新清单**：
- cultivation 正本区（README.md）：§5 op 清单「UpgradeTraceOp……auto_farm」行改 `farm_dungeon`/面板态契约；新增「升级 op 家族失败适配」语义节（三线失败分支委托共享件/预算内联检查位置/行迹面板态契约与 agent 选节点分工）；
- trailblaze_power 正本区（README.md）:63 文件映射行 `src/sr_od/challenge_mission/use_trailblaze_power.py` 改迁移后路径；新增 UseTrailblazePower 迁入归属与挑战循环要点（等待窗常量已抽 challenge_mission 共享模块的口径）；
- echo_of_war 正本区（挑战机制概览.md）：等待窗常量单一源指针改 `challenge_mission/battle_wait_windows.py`（§3「常量单一源在 use_trailblaze_power」表述随迁移失真）；
- game-coach skill `新手与日常决策.md`：行迹 op 条目改写（面板态契约/参数名 `farm_dungeon`/券耗 1/手动刷边界——花萼侧**不指 `FarmLightConeMaterialOp`**，写「调用方按行迹缺料自行导航，`FarmTraceMaterialOp` 立项前过渡态」）、角色与光锥条目补「战斗失败自动继续（预算内重发）」、`FarmLightConeMaterialOp` 条目补失败适配一句；
- 占位目录收口：`cultivation/changes/manual-fail-form-cultivation/`、`cultivation/changes/trace-upgrade-rework/`、`trailblaze_power/changes/use-trailblaze-power-rehome/` 三占位 README 的「已并入本迭代」指针补 commit 号（设计期指针已改，落地后补最终指向）。
- game-coach skill 改动属**跨仓同步**（skills/ 在主仓但消费方跨项目）：与代码改动分开单独提交，保持可逆；skill 触发验证随末阶段一并做。
**完成判据**：清单清零；正本与实现一致。
