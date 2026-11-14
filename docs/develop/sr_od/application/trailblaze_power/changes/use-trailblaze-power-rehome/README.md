# UseTrailblazePower 迁移开拓力 app + 失败形态适配（外溢迭代·占位）

## 承接出处
- 源迭代：`docs/develop/sr_od/application/echo_of_war/changes/weekly-challenge-core/`（details/fail-form-adaptation.md；用户裁定 2026-11-14：开拓力 app 的接入不在源迭代范围）
- 攻击依据：源迭代对抗报告 attack.md 第一轮（三处失败消费点在新失败画面无限重试卡死；归属裁定）与第二轮 P1-4（判据同步声明，见下）

## 落地判据同步声明
- **既有测试随行为变更需同步修订**：`sr-od-test/test/sr_od/challenge_mission/test_use_trailblaze_power_timeout.py:112-129` 锁的是「超时收尾见战斗失败 → 点战斗画面·退出关卡按钮」旧行为——本迭代把它改为「委托共享失败继续件 → 关副本退出」后该断言必红，落地时同步改写（不是回归）。
- 其余体力挑战既有测试以「失败分支不回归、胜利路径不回归」为界。

## 范围（一句话）
`UseTrailblazePower` 由 `src/sr_od/challenge_mission/` 迁至 `src/sr_od/application/trailblaze_power/`（负责人裁定：花萼的 op 归开拓力 app；两处 import 消费方 trailblaze_power_app.py:15、farm_material.py:40 与测试镜像同步）+ 三处失败消费点接入共享失败继续件 `ResumeFromBattleFail`（源迭代 fail-form-adaptation.md 定义）。

## 设计草案（对抗审前草稿，立项时转正）
- 失败重发回链定死「选择次数」节点（use_trailblaze_power.py:85-98）——滑条节点重算 `plan_times - finish_times` 本轮次数，记账自洽；「回点击挑战则滑条不重放、下轮用画面残留值」的方案废弃。
- 超限（连败 5 次）→ 点「挑战副本·按钮-关闭副本」退出（落大世界，与既有收尾 BackToNormalWorldPlus 幂等衔接）。
- 超时收尾判负分支 → 委托 `ResumeFromBattleFail` → 退出（超时语境不重试）。
- 记账不变：失败不计 `finish_times`；`on_battle_success` 回调不因失败触发。
- mock 三场景：主链失败→重发成功；主链连败→关副本退出；超时判负→失败继续→退出。

## 状态

已并入迭代 `cultivation/changes/upgrade-ops-adaptation/`（块 A，details/fail-adaptation.md §1——迁移件与失败适配同批，占位草案（回链定滑条/连败关副本/超时判负委托/记账不变）已吸收进节点卡）。本占位不再单独立项。
