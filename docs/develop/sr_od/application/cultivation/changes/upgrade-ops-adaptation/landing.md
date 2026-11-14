# 落地：升级 op 失败适配与行迹重构

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过（含测试文件）；
- 受影响测试全量一次通过（按阶段点名：challenge_mission / trailblaze_power / cultivation 相关子集）；
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交；
- 提交逐文件点名 `git add`（禁 `-A`/目录级），提交后 `git show --stat` 复核入库面 = 申报面；
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节；
- 范围红线（本设计 §2「明确不解决」）：不触碰 `ChallengeEchoOfWar`（周本 app）、不做家族循环收敛重构、不给 UpgradeTraceOp 加手动刷本路线——落地时发现触碰需求即停手上报。

### 3.1 块 A：UseTrailblazePower 迁移 + 失败适配

**范围**：迁移件（文件搬移 + 两处 import + 测试镜像路径）一个提交；失败适配（「失败画面继续」新节点 + 「战斗结果处理」收窄胜利路径 + 超时判负改委托 + 连败关副本出口）一个提交；既有测试判据同步改写（design.md §3 声明的 :112-129 必红改写）；mock 五场景（details/fail-adaptation.md §1.4）。
**设计依据**：details/fail-adaptation.md §1 全节。
**文件面**：`src/sr_od/challenge_mission/use_trailblaze_power.py` → `src/sr_od/application/trailblaze_power/use_trailblaze_power.py`（迁）、`trailblaze_power_app.py`、`farm_material.py`（import）、测试仓镜像路径 + 断言改写 + 新增场景。
**依赖**：无。
**完成判据**：mock 五场景全过；既有胜利链/超时判胜回归通过；判据同步改写后的判负断言锁新行为；ruff。

### 3.2 块 B/C：角色线与光锥线手动路线失败适配

**范围**：两文件同构适配——返回分类首位「失败画面」分支（委托共享件）+ 失败重发回链（角色线挂 `farm_in_dungeon`、光锥线挂 `副本刷取分流`）；mock 八场景（details/fail-adaptation.md §2.3/§3）。
**设计依据**：details/fail-adaptation.md §2/§3。
**文件面**：`upgrade_character.py`、`upgrade_light_cone.py`、`sr-od-test/test/sr_od/application/cultivation/`（两测试文件）。
**依赖**：3.1（共享件已可用——实际早已落地，此处依赖为顺序语义：先收口委托链再收口消费方，验收视角）。
**完成判据**：mock 八场景全过；券路线回归确认通过；两线计场时机维持现状（不统一）；ruff。

### 3.3 块 D：UpgradeTraceOp 面板态重构

**范围**：起点/终点契约改面板态↔树态、删固定节点坐标与 `_SKILL_NAMES` 枚举、`target` 改校验锚语义、`auto_farm`→`farm_dungeon` 改名、券耗回填 1、连刷次数接入（`_set_farm_times` 同款）、实值记账、收尾关面板节点；mock 七场景（details/trace-rework.md §3）。落地前置建档：面板「读区-技能分类」与「等级读数」两 area（od-dev-screen-onboarding，探索帧已够）。
**设计依据**：details/trace-rework.md 全节。
**文件面**：`upgrade_trace.py`、`角色-行迹` 画面档两 area、`sr-od-test/test/sr_od/application/cultivation/`（行迹测试文件）。
**依赖**：无（与 3.1/3.2 无代码耦合）。
**完成判据**：mock 七场景全过；现版券刷链回归（链路平移不重写）；ruff。

### 3.4 实机验证（消耗逐次授权）

**范围与顺序**：块 D 零消耗段先行（面板校验失败路径 + 缺料判停路径，阿哈样本材料 0 态可零消耗触发）→ 块 A 花萼场一场（开拓力 30，体力计划授权场景；失败分支触发为自然条件态——低练度才败，mock 已锁语义，实机遇自然失败时按现场处理协议补验）→ 块 B/C 手动路线各一场（开拓力 10/30）→ 块 D 券刷一场（开拓力 10 + 券 1，E2E 授权）。
**完成判据**：各块 run 日志可复盘；失败分支未自然触发时如实挂账（不硬造败场）。
**依赖**：3.1-3.3；MCP server 重启。

### 末阶段：正本更新

**正本更新清单**：
- cultivation 正本区：升级 op 家族概览（三线契约/失败适配语义/行迹面板态契约与 agent 选节点分工）；
- trailblaze_power 正本区：UseTrailblazePower 迁入后的归属与挑战循环要点；
- game-coach skill `新手与日常决策.md`：行迹 op 条目改写（面板态契约/参数名/券耗 1/手动刷边界）、角色与光锥条目补「战斗失败自动继续（预算内重发）」、`FarmLightConeMaterialOp` 条目补失败适配一句；
- 占位目录收口：`cultivation/changes/manual-fail-form-cultivation/`、`cultivation/changes/trace-upgrade-rework/`、`trailblaze_power/changes/use-trailblaze-power-rehome/` 三占位 README 改「已并入本迭代」指针。
**完成判据**：清单清零；正本与实现一致。
