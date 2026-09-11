# 2026-09-11-unified-state 迭代设计（总纲）

## 0. 元信息
- 迭代目标：ADR-0630 统一 state 收编升级（`docs/develop/currency_war/decisions/0630-unified-state-journal.md`，冲突处以其修订节为准）+ 用户 2026-09-11 裁定：board state 收尾纳入通关迭代能力关键链。任务账本 = `.debug/progress/2026-09-11-cw-clear-run/dag.jsonl`。
- 状态：对抗审中——批次一/二已落地审查，开放点已账本化（T-11/T-12/T-15），收敛后转定稿。
- 文档清单：details/BoardState-数据结构设计.md —— 统一 state 容器数据结构与画面字段规格（详设件，寿命=迭代；正本家 = docs/develop/currency_war/game_state/（总纲+分篇），归拢后自足）。

## 1. 问题与动机
- 现状症状：旧 12 流散乱、写点不全、无渠道签名、无统一 state（退役理由口径，依据 = ADR-0630 背景节；旧 12 流 = 流程侧遥测的十余条独立落盘 JSONL 流，逐流清单见 r5-migration-plan「术语速查」）。
- 根因归层：流程（观察/动作/hook 写入各自落盘、无统一写入口纪律）+ 表示（状态散在多条专用流，无带渠道签名与版本 id 的自足快照记录面）——归层依据 = ADR-0630 决策 1/2/3。
- 解决到哪：统一 state 容器（代码暂名 BoardState）、写入口三渠道封闭集、自足快照 journal、旧流退役与正名排期。
- 明确不解决：玩法策略语义——各效果游戏机制原文、策略判据归 game 子树与 strategy-docs，本迭代只管状态记录面。

## 2. 方案
- 系统级变化：①旧 12 流退役（写面删除与消费迁移排期，单一源 = r5-migration-plan 八波）；②容器收编升级为统一 state（暂名 BoardState，终局正名 GameState——ADR-0630 后果节逐字锚）；③写入口三渠道封闭集（obs=画面 op 观察 / logic_action=动作 op 逻辑计算 / logic_hook=流程 hook 派生逻辑计算，依据 = ADR-0630 决策裁定 5）+ 自足快照 journal（行行自足、零重放，依据 = ADR-0630 决策 3）。
- 详设划分与接口契约：详设一份（details/），承载字段级规格——容器结构（§8）、画面字段清单与写端（§3/§4）、效果族归属（§5）、批次范围枚举（§8.7）；单详设无跨详设接口。**正本定位：正本家 = docs/develop/currency_war/game_state/（总纲+分篇）**——总纲只写设计理念与核心规范，迭代期字段级完整规格暂居本迭代 details/，随批次落地归拢进 game_state/ 分篇（新建分篇承载，拆分粒度归拢时定），归拢后 game_state/ 自足；详见 landing.md「正本更新清单」。
- 迁移排期单一源：`docs/develop/currency_war/game_state/r5-migration-plan.md`（正本区文件，八波排期与波序纪律），本迭代不复制。
