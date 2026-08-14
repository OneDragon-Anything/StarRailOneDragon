# ADR-0123 备战编排从固定序列改为观察驱动决策环(PrepDirector)

- 日期:2026-08-14
- 状态:已接受(设计定稿,实现 P1 待做)
- 设计详文:[strategy/15_prep_director.md](../strategy/15_prep_director.md)

## 背景

BattlePrepCycle 是固定流水线(收球→买牌→部署→装备→出战),腾席决策被硬编码在买牌 op 内
(`_handle_bench_full` 位置式卖 bench-1..3)。2026-08-14 实跑暴露:奖励球 + 备战席满时,
收球 op 中断、腾席在下一节点,球要拖一整轮才收;且腾席不认身份可能卖核心、不考虑 deploy 空位/升级扩容。

用户定调:策略应该是**根据当前画面输出下一步做什么**(例:有奖励未领+备战满 → 拖前后台/卖无关角色/
都有用则留球),做一步 → 再识别 → 再决定。

## 决策(v3 决策点全景,2026-08-14 用户两轮 review)

新增 PrepDirector(SrOperation):观察(PrepObservation,组合现成 reader 轻/重分层)→ 单步决策(动作全集**原子化**:ClickSphere/ClickSpheres(k=free 带内验早停)/OpenBox/PickBoxCard/BuyCard/LevelUp/RefreshShop/**SellBench(身份感知)**/DeployMove/WearEquip/StartBattle;组合动作仅商店/装备域过渡用)
(`CwStrategy.decide_prep_action` 新方法,基类默认规则版,复用 _should_deploy/_weakest_bench_idx/plan)→
执行(宏动作映射现有 op,P1 一行不改)→ 再观察。环出口 = StartBattle(无球无箱无正提升无可上无可穿);
防死循环 = 动作级 fail 屏蔽 + 环级 stall 预算强制出战。

腾席优先级:deploy 空位上人 > 升级扩容 > 卖最弱(身份感知)> 全有用则 DeferSpheres。

**v3 补全**:① **工具域**(UseProjector 复制核心=3合1 神器/UseWrench 卸装回收/UseSmelter 赌重roll,决策函数待写,P4)—— 现 EquipOnly 过滤跳过工具从不使用;② **事件域**(投资策略/环境、盛会之星、伙伴、祈愿、遭遇、补给 overlay 选择)P5 收编进环(决策函数现成 decide_*,祈愿缺),主循环瘦身为纯路由;③ **两层环架构**:外环(主循环)路由 + 内环(PrepDirector)步级决策,P1-4 遇 overlay BailToOuter(零回归),P5 统一 obs。

## 迁移

P1 外环替换(子 op 不动,收球-腾席闭环当轮完成)→ P2 买牌内部化(拆 plan 单步,淘汰 shop.py
两阶段 hack + _handle_bench_full)→ P3 部署/装备内部化(BattlePrepCycle 退役)。
每 Phase 独立 live 验(M=3)。

## 后果

- 正:备战内所有行为成为可决策点(观察驱动贯彻到步级);收球/腾席/买牌互不阻塞;
  RefreshShop 后计划过期问题被「逐步重观察」自然解决(P2);
- 负:每步观察有成本 → 轻/重分层控制;环需要防死循环预算;迁移期两套编排并存(P3 前可切回);
- 不变:三层架构(战略/战术/数据)、plan()/evaluate() 内核、现有子 op 内部逻辑、主循环挂载方式。
