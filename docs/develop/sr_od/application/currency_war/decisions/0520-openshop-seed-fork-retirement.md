# ADR-0520: OpenShop 播种层双源分叉治本(tracked_bench 旧账退役)

- 状态:已实施(代码+测试+守卫文案)
- 日期:2026-09-05
- 关联:ADR-0517(§守卫两属断言)、ADR-0518(单动作实施)、flow/action_exec.md §2(发射×执行契约);诊断报告 `.debug/temp/currency_war/20260905_openshop_fork_diag/report.md`

## 背景

第二局实机(run_20260905_020939)02:13:08 与 02:26:39 两次炸出 OpenShop 前置守卫「期望态 vs tracked 双账分离」:expected 累积陈旧名 [('藿藿',1),('丹恒·饮月',1),('忘归人',1)] 而 tracked 按屏幕真值为空/仅新购。诊断批帧级法证否决了守卫自我诊断的「project/mutate 投影分叉」——真根因为**第三类:播种层双源分叉**。

## 根因

商店入口播种(cw_op_buy_cards.py 原 :543-546)在主账 `tracked_bench_chars` 为空时回退读旧名列表 `tracked_bench`(唯一写点 BuyCardOp.execute append,全链路零清理点)。买牌-部署循环中,牌被部署上场后旧账不修剪,下次 OpenShop 播种时回退分支把整串陈旧名复活进期望态;守卫对拍的主账却是屏幕真值——播种源与守卫源两账分离,首帧(LevelUp 投影,bench 恒等)必炸。自愈机制(守卫 fail 交外循环 → 下一入口 heavy 读屏重建)使局未卡死,但每帧附带损害=该帧 LevelUp 金实扣未落遥测。

## 决策

1. **退役 `tracked_bench` 旧账**:删除回退播种分支、`_tracked_bench_chars` helper、session 字段声明(留墓碑注);单动作架构下回退失去存在前提——首轮场景应由入口 heavy 读屏重建(决策 8),不读历史账。
2. **播种期对账接线**:单动作循环入口新增 `guard_expected_vs_tracked(stage='seed')`——首动作前先对账,分叉归「播种/入口账」;投影后对账(stage='project')保持原语义。两类消息分离,消除本案误报方向。对抗审计修正(2026-09-05):seed 档可达类别实为「tracked 主账空而屏幕 bench 非空」=跟踪账丢件/识别幻影检测器(tracked 非空时对账按构造恒等);独立 run_operation 防御路径下(临时 session tracked 恒空)seed 守卫必先炸,失败形态从「首动作后」变「零动作」,已申报为已知行为差异。
3. **测试三锁**(测试仓):墓碑扫描锁(点号锚定 `.tracked_bench` 属性访问,带变异自检防恒绿)、事故帧 seed-rebuild 语义锁(真空主账播种为空+两点静默+投影无陈旧名)、两属消息分离锁。

## 后果

- 买牌-部署循环不再累积陈旧期望账;OpenShop 前置守卫恢复「对拍同一本账」的语义。
- 附带损害(帧内金实扣未落遥测)随分叉消失而消失。
- 历史文档中「project/mutate 分叉」的旧表述按本 ADR 重新归因;新守卫消息两分叉措辞分离。

## 验证

ruff 净;新增锁直跑绿;CW 快速集 2150 passed / 0 failed / 1 xpassed(编排者亲跑复核)。
