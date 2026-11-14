# 挑战战斗循环统一（外溢迭代·占位）

## 承接出处
- 源迭代：`docs/develop/sr_od/application/echo_of_war/changes/weekly-challenge-core/`（design.md §1「明确不解决」Phase 2 条目）

## 范围（一句话）
统一挑战机制家族的战斗循环实现——家族成员：`ChallengeEchoOfWar`/`ChallengeEchoOfWarCore`（周本）、`UseTrailblazePower`（花萼形制）、光锥/角色手动路径各自的手写循环；「等待战斗结果→结果处理（退出关卡/再来一次/失败继续）」段同构，收敛为共享件。**含 ChallengeEchoOfWar 切换到核心**（weekly-challenge-core 源迭代「明确不解决」首条指向此处）。

## 强制触发条件（负责人裁定口径）
挑战机制相关画面/流程下次随版本再变、家族成员需要再次逐一跟进适配时，**必须立项本迭代**做一次收敛，禁止再逐件打补丁（同族第 N 次逐件修 = 违反跨件半问）。

## 状态
未立项（占位）。风险声明：weekly-challenge-core 落地后家族仍有 3 份战斗循环实现（UseTrailblazePower / ChallengeEchoOfWar / 核心），收敛面已通过共享失败继续件缩小。
⚠️ 同文件占位：`echo-of-war-fail-adaptation/`（失败适配+超时防线，改动同文件 `challenge_ehco_of_war.py`）——本占位立项（app 切核心）会把失败适配大部分范围吸收进核心，两占位禁各自独立落地，立项时先裁定收口顺序。
