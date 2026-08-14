# ADR-0123 备战编排从固定序列改为观察驱动决策环(PrepDirector)

- 日期:2026-08-14
- 状态:已接受(P1 已实现 2026-08-14:prep_director.py + prep_actions.py + decide_prep_action 钩子 + DefaultCwStrategy 具现 + 挂载切换;live 验证待做)
- 设计详文:[strategy/15_prep_director.md](../strategy/15_prep_director.md)

## 背景

BattlePrepCycle 是固定流水线(收球→买牌→部署→装备→出战),腾席决策被硬编码在买牌 op 内
(`_handle_bench_full` 位置式卖 bench-1..3)。2026-08-14 实跑暴露:奖励球 + 备战席满时,
收球 op 中断、腾席在下一节点,球要拖一整轮才收;且腾席不认身份可能卖核心、不考虑 deploy 空位/升级扩容。

用户定调:策略应该是**根据当前画面输出下一步做什么**(例:有奖励未领+备战满 → 拖前后台/卖无关角色/
都有用则留球),做一步 → 再识别 → 再决定。

## 决策(v7 定稿,三轮 review 后;本节为唯一现行版,历史修订见下方附注)

新增 **PrepDirector(内环 SrOperation,替换主循环中的 BattlePrepCycle 挂载点;外环主循环不动)**:
观察(PrepObservation,组合现成 reader 轻/重分层)→ 单步决策(`CwStrategy.decide_prep_action`,
**abstract ABC 钩子**,默认实现住 DefaultCwStrategy(11 号 ABC+Default),复用 _should_deploy/
_weakest_bench_idx/plan)→ 执行(原子动作映射原语带验证;组合动作 RunBuyPhase/RunDeploy/RunEquip
仅商店/部署/装备域 P1-P3 过渡)。环出口 = StartBattle(无球无箱无正提升无可上无可穿);

防死循环三层:同动作连败 2 次先试恢复原语(分型,禁裸 ESC)→ 无效 BailToOuter(外环重入重建 Director
时 stall/屏蔽/defer 计数全清零;ping-pong 由主循环 **MAX_ITER=2000** 对局预算兜底 —— round_wait
不消耗 node 重试预算,operation.py:453-461,勿引 node_max_retry_times)→ 恢复试尽仍零进展
(stall≥5/步数>60)才强制出战;StartBattle 屏蔽豁免;连续 bail≥3 同因计数宿主 = StrategySession
(该计数**不在**清零清单内,局终才销毁)。

P1 动作集 = ClickSpheres/OpenBox/PickBoxCard/SellBench/SellDeployed/DeployMove(仅腾席链)/
StartBattle/LevelUp/EnsureShopOpen/Closed + 控制流(DeferSpheres 不计 stall 计步数/BailToOuter)
+ **RunDeploy(DeployBench 整体,v7 修三轮 H-2:保留 D-10 换血/同角色去重 5.1.7/前排保证 5.1.6/
cap 门 5.1.8 四项板上行为,零部署回归;原子 DeployMove 只用于腾席链,避免每次部署触发 SIFT 重观察)**;
四项行为 P2/P3 随部署域原子化上移为策略规则后退役。

腾席优先级:deploy 空位上人 > 升级扩容 > 卖最弱(身份感知,_weakest_bench_idx 待加 3合1 件保护)> 全有用则 DeferSpheres(defer_count 环入口清零)。

**v4 分离(用户定调:「这块应该只是框架,要和具体策略分离开来,可以有多种策略实现」)**:环 = 框架(八条不变式 F1-F8:单步契约/观察真实/动作合法域/验证防护/出口兜底/无状态策略/可换策略/可回放),「下一步做什么」全部判断 = 策略(CwStrategy 子类,可多实现热插拔,对齐 11 号插件机制);decide_prep_action 为 **abstract ABC 钩子**(v3 的「基类给默认实现」违反 11 号 ABC+Default 分层,修正:参考实现住 DefaultCwStrategy);§5 规则降级为 Default 参考实现非框架。

**v3 补全**:① **工具域**(UseProjector 复制核心=3合1 神器/UseWrench 卸装回收/UseSmelter 赌重roll,决策函数待写,P4)—— 现 EquipOnly 过滤跳过工具从不使用;② **事件域**(投资策略/环境、盛会之星、伙伴、祈愿、遭遇、补给 overlay 选择)P5 收编进环(决策函数现成 decide_*,祈愿缺),主循环瘦身为纯路由;③ **两层环架构**:外环(主循环)路由 + 内环(PrepDirector)步级决策,P1-4 遇 overlay BailToOuter(零回归),P5 统一 obs。

## 迁移

**P1 内环替换**(新域原子:奖励/席位/战斗;商店/装备组合过渡,子 op 一行不动,收球-腾席闭环当轮完成;默认策略加门防 _handle_bench_full 位置式卖残留)→ **P2 买牌原子化**(拆 plan 单步,淘汰 shop.py 两阶段 hack + _handle_bench_full,删 shop.py 内 update_target 调用)→ **P3 部署/装备原子化**(BattlePrepCycle 退役,对账进环入口)→ **P4 工具域**(UseProjector 等 6 主动工具 + 决策函数)→ **P5 事件域收编**(前置:祈愿 3.9/圣杯 3.10/补给/投资×2 重建档;巨星/伙伴/遭遇先收编;P5 出口补 GoToSupplyScreen/GoPickStrategy;主循环瘦身为纯路由)。
每 Phase 独立 live 验(M=3),不并行。

## 后果

- 正:备战内所有行为成为可决策点(观察驱动贯彻到步级);收球/腾席/买牌互不阻塞;
  RefreshShop 后计划过期问题被「逐步重观察」自然解决(P2);
- 负:每步观察有成本 → 轻/重分层控制;环需要防死循环预算;迁移期两套编排并存(P3 前可切回);
- 不变:三层架构(战略/战术/数据)、plan()/evaluate() 内核、现有子 op 内部逻辑、主循环挂载方式。
