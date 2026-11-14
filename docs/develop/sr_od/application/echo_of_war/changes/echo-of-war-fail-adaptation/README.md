# 周本 app 失败形态适配与战斗超时防线（外溢迭代·占位）

## 承接出处
- 源迭代：`docs/develop/sr_od/application/echo_of_war/changes/weekly-challenge-core/`（details/fail-form-adaptation.md；用户裁定 2026-11-14：周本 app 的接入不在源迭代范围）
- 攻击依据：源迭代第一轮对抗报告（attack.md）——ChallengeEchoOfWar 失败后找不存在的按钮无限重试（challenge_ehco_of_war.py:188-193）、战斗等待无节点超时防线（round_wait 无限继续 = 一条龙挂死，:159-178）

## 范围（一句话）
`ChallengeEchoOfWar`（周本 app）接入共享失败继续件 `ResumeFromBattleFail`（源迭代 fail-form-adaptation.md 定义）+ 补战斗等待节点超时防线（25 分钟家族口径 + 超时收尾节点，语义照 use_trailblaze_power.py:246-278）。

## 设计草案（对抗审前草稿，立项时转正）
- `_after_battle_result`（challenge_ehco_of_war.py:188-193）：`BATTLE_FAIL` 计数后 → 委托 `ResumeFromBattleFail` → 回挑战画面 → `battle_fail_times >= 5` 或 `battle_success_times >= plan_times` → 点「挑战副本-历战余响·按钮-关闭副本」→ 既有 `back_at_last`（:238-241）；否则 → 回「点击挑战」节点（:68）重新发起（周本发起链无滑条，无回链歧义）。
- `等待战斗结果`（:159-178）显式 `timeout_seconds`（25 分钟家族口径）+ 超时沿边转超时收尾节点（观察至结算：胜→补记→点退出关卡；败→委托共享失败继续件→超限关副本退出；二次超时→fail，经 STATUS_TIMEOUT 出边转终态节点落自定义文案）。
- 对外签名与计划记账不动。

## 状态
未立项（占位）。现状风险：一条龙周本计划遇战斗失败即卡死（找不存在按钮无限重试）、战斗永不结算即整条龙挂死。
