# 0623 轮首收入 T1a kernel 单一源函数族(含 net_income 处置申报与败补口径判别执行)

- 日期:2026-09-09
- 状态:accepted
- 关联:ADR-0439(收入口径实机差分)、统一观察架构设计 §7-T1/T2/§7.1(逻辑计算清单表与收入口径申报表)、BoardState 设计 §4.1/§4.2(收入修饰与轮首收入正本)、economy.md §10.1/§11(真值源)、ADR-0620(数据权威序先例)、方案审 F4-①②(统一观察架构设计稿对抗审两前置件)

## 背景

统一观察架构 §7-T1 指认「轮首收入三支」的完整公式(平面感知键 + win_reward_mult + 败补基项)在 kernel 无函数载体:sim 引擎内联式、败补用旧类型表、win_reward_mult 零消费(§1.2 分叉实例 1/2)。本批=T1a(kernel 半部);sim 引擎收入段改调与实机 live 写端指派=T1b(禁碰 sim/engine_p1.py,另行批)。随批须闭合两个前置件:①方案审 F4-①——现役 `net_income(round, streak_pre, lost_node_type)`(决策数学 6 处消费:mandate_v1/shop.py:1016/1364/1987/2148、encounter.py:240、cw_economy `_upgrade_ul_threshold_ok`〔loss_exact 前置,符号名索引〕)与记账口径的差异归属禁不裁决;②方案审 F4-②——败补口径冲突(玩家裁定 2026-09-09「看节点基础奖励」平面感知键 vs ADR-0439 类型表 LOSS_GOLD_BY_NODE {battle:2,encounter:4,boss:4})按判据「补发随轮次变=基础奖励口径;恒 2/4=类型表口径」用已录遥测分桶重放仲裁。

## 决策

1. **kernel 单一源函数族落 `kernel/cw_economy.py`**(与既有收入表同文件,零新桶):`reward_base_gold(plane, round)` 平面感知取键(P1 {1:3,2:4}、其余 5——P2r1=5 为 economy.md §10.1 结构化直读定谳、P3r1=5 无直读样本维持挂账);`loss_compensation_base(plane, round, node_type)` 败补基项(记账口径=玩家裁定平面感知键,待玩家确认);`round_start_income(...)` 四分支派发(supply→reward→败补→常规,与引擎 elif 序同构)+ `RoundStartIncome(branch/base/interest/streak/total)` 分解账 + `LostNodeRef` 取键输入;`win_reward_mult` 参数化施于连胜分量含奖励轮(修复 sim 零消费挂账的 kernel 半部;聚合单一源=aggregate_economy,取最大不叠乘)。分支派发契约:败态跨奖励/补给轮的归宿(吞掉/递延)归调用方,本函数不裁决(§4.2 既有挂账不动)。**辖域排除申报**:每节点固定加金(`gold_per_node`——定期福利/按劳分配/剩余价值)、首领节点金(`gold_per_boss_node` 特战资金族)与战斗表现条件类(剩余价值≤4 等)是轮首收入真实金分量(引擎以 'invest' 键单列入账),**不在本函数族辖域**(签名无槽位)——T1b 接线时以分量扩参 or 调用方聚合单列承载,二选一随 T1b 定;§8.3 清单 free_refresh_burst/xp_per_node/gold_per_boss_node 三字段同此挂 T1b。**supply 支 base 键语义申报**:取平面感知键为 kernel 实现选择(正本 §4.2 只写「基础」未明示键;现标准节点序 supply 不落 r1/r2,与引擎恒 BASE_INCOME 无数值差)——节点序变异使 supply 落 r1/r2 时两域分叉,键语义随 T1b 接线复核定谳。
2. **net_income 处置=F4-① 选项(a)委托改造+传参简化**:base/streak 分量改委托 `reward_base_gold` 的 **P1 规划投影**与 `streak_gold`,消费点数值逐位不变(等价性锁在册);`round_base_income` 降为该投影的薄别名(实现单一源归 reward_base_gold)。**差异归属申报**:决策签名无 plane→P2/P3 的 r1/r2 轮 base 有差(P2r1 真值 5 vs 投影 3);败补参数支只能取类型表做规划下界——两者归属=**决策规划近似,非口径冲突**,落统一观察架构 §7.1 申报表与本函数 docstring;现役 6 消费点全部传 `streak_pre=0, lost_node_type=None`,近似不落值。
3. **F4-② 判别执行=数据不足定谳**(非两口径任何一方胜出):重放脚本 `tools/cw/loss_comp_bucket_replay.py`(只读,判据值独立内联不依赖被审实现),语料=.debug/currency_war/telemetry/matches/*.json 共 146 局(ADR-0439 同源,较其 108 局扩 38 局),方法=逐笔记账差分(动作自带金额字段 BuyCard.card.cost/LevelUp.cost/RefreshShop.cost + exogenous.sell_income 卖金钩子;点球/开箱等未知金流轮整轮剔除;金面效果卡局整局剔除;主子集限结算持金<10 使利息恒 0)。**三项结构性感因**:①判别判据所需的 P1r1/r2 败局阶梯样本语料中不存在(战斗类败局桶 P1r1=0/P1r2=0——低轮位 bot 恒胜,3/4 档读数无从取);②boss 桶 n=1;③标准节点序把「被败节点类型」与「下一节点类型」结构性绑定(battle→encounter→reward),任何大 n 桶的差分窗都混入不同到账项,类型差分与到账项差分不可分(battle 类最佳桶 n=76 与 encounter 类最佳桶 n=88 的下一节点类型不同,非同窗对)。附加观察(不定谳、挂核对项):**次级子集两最佳桶**(battle(1,6)→encounter n=76、encounter(1,7)→reward n=88)差分窗众数层面恒见 **+5 公共项**(主子集 n=21 分布碎不构成「恒」的证据),候选解释=下一战斗/补给节点基础金于轮首入账(与「轮首收入」命名一致),归「到账时序」三点差分实验(§4.2 既有挂账)一并定谳。**记录模型维持玩家裁定口径不变**(零代码口径翻转),挂「待玩家确认」。补采口径(定谳所需):孤立败轮对照局(无点球/无事件浮层/花销可逐笔记账)×{P1r1、P1r2、P1r9 boss 跨位面}≥5 局/桶,采集时同步录结算屏「存量」×下轮关店/开店金三点差分。

## Considered Options

- net_income 处置(b)保留现状仅 docstring 申报——否决:base/streak 分量委托成本为零且消灭「round 单键查表」的第二实现位,(a) 的等价性可锁;纯申报不消双源。
- net_income 处置(a)强形态=签名加 plane 参数全消费点改调用——否决:mandate_v1 消费面(flow.py/mandate.py 邻域)有并行批在飞,签名波及非本批文件面;且 loss_exact 前置的规划语义本就按平滑日程取值,P1 投影与现役值逐位等价,强形态收益为零。(显式战术权衡:规划近似保留,P2r1 真值差 2 金的决策影响随 T1b/玩家确认批一并复查。)
- 判别执行后改判类型表口径(推翻玩家裁定)——否决:类型依赖信号(battle/encounter 桶众数差 ≈2)与到账项差分混杂(感因③),不构成「恒 2/4」的定谳证据;按「口述被证伪需证明」纪律,证明不成立时口述口径维持原位+待确认,非降级改判。
- 判别执行后按玩家裁定关闭挂账(宣称已证)——否决:P1r1/r2 阶梯零样本,blob 无判据所需的读数,宣称即造假。

## 后果

- kernel 收入公式单一源就位:T1b(引擎改调+live 写端指派)只剩接线,无公式第二实现位;win_reward_mult 的 sim 零消费挂账 kernel 半部闭合,引擎半部随 T1b。
- net_income/round_base_income 消费点零行为变化(等价性锁=sr-od-test test_cw_income_single_source,含既有语义锁 test_cw_statefn::test_net_income_schedule 值域)。
- 败补口径冲突从「未仲裁」转「仲裁已执行+数据不足+待玩家确认」:补采到量后按本 ADR §决策3 的方法重放定谳,两口径的胜负判据与采集口径已锁定,防二次仲裁口径漂移。
- +5 公共项观察(限次级子集两最佳桶众数面)并入到账时序三点差分实验的核对清单(若证实=下一节点基础金轮首入账,轮首收入分支面需按「败补+下轮基础金同窗入账」复核 §4.2 行选择优先级表述)。
