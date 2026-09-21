# 事件屏刷新链统一 + 补给选卡即时上报(含遭遇链扩围)

## 文档
- 设计总纲:[design.md](design.md)(§2.4 = 遭遇链扩围,2026-09-21 用户裁定)
- 落地:[landing.md](landing.md)
- 对抗审:[attack.md](attack.md)/[attack2.md](attack2.md)(原三块两轮)/[attack3.md](attack3.md)(扩围两段:X1-X9 + R1-R6)

## 进度
- 迭代设计:定稿(X1-X9 + R1-R6 处置收敛;R2 的 X5/X9 项在第一轮修订闭合)
- 设计对抗:收敛 · 报告=[attack.md](attack.md)/[attack2.md](attack2.md)/[attack3.md](attack3.md)
- 落地:全部 done——T-1(补给选卡即时上报,`123827e00`)/T-2(补给刷新闸观察化,`24752ab11`)/T-3(遭遇刷新链终结化与闸观察化,`50d9933e8` + 测试仓 `0c1dbf9f`)/T-7(遭遇链扩围:稳定期删除 + 选卡派发即终结 + chosen 迁动作侧 + 结算奖励兑现回调;设计批 `f0cdd13b5` + 实现批 + r2 修复 `ef1bb393d` + 测试仓 `deb9c8bc`/`8d51fb13`;r1 打回→r2 accept,明细见 reports/T-7-r1.md + reviews/T-7-r1.md §7)
- 正本更新:done(T-4,`147cc3c6b`;encounter.md/supply.md 全文重写 + README/op-layer/action_ops/action_exec/flow README/fields 同步 + 兜底死注释清;验收 = reviews/T-4-r1.md accept)

## 外溢挂账(后续批)
- T-5:PickPlanner/PickEquip 两相上报清偿(wait;外溢另批)
- T-6:「财富」装备模板采集补缺(wait;data-collection 批)
- R5:策略器收益对账读端(encounter_reward_claimed 消费读端,外溢候选)
- op-layer §3 标题「37」vs 正文「36」数字漂移(review 在册发现,归后续批)
- 实机待验:遭遇分支刷新点击行为、未激活布局 UI 形态(game 侧 currency_war_encounter.md 在册)
