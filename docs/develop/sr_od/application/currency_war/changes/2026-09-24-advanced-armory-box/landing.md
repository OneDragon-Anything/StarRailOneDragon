# 进阶武装箱策略发放 落地

> 阶段小节 = 账本唯一源;§12 通用工程门 = sr-od-test/README.md「提交」节 +
> 项目 AGENTS.md §7/§10(类型注解/ruff/受影响测试全绿/逐文件 add)。

## 3.1 kernel:登记 + 公共原语 + 箱腿效果体

**范围**:design §2.1(STRATEGY_GRANTS 三条 items_immediate + `_validate_strategy_grants`
空发放集判定并入 items)+ §2.2(`gain_bench_item` 公开原语,`_place_bench_item`
producer 形参化,现调用点行为不变)+ §2.3(PICK_INVEST_EFFECTS 三条箱腿效果体,
`_STRATEGY_BOX_GRANTS` 名单单一源表,惰性 import 破环)+ 计数面同步
(test_cw_invest_strategy.py 计数锁 83→86、cw_investments.py 底册收录判据注释
与计数 docstring 两形态化——「获得…角色名直读」扩「获得…角色名/占席道具直读」)。
**不含**:sim 用例(3.2)、流程侧(零改动认定,无码)、正本文档(末阶段)。
**设计依据**:design.md §2.1/§2.2/§2.3
**文件面**:src/sr_od/application/currency_war/kernel/cw_investments.py、
kernel/cw_gain_chain.py、kernel/cw_gain_effects.py;
sr-od-test/test/sr_od/application/currency_war/test_cw_gain_chain.py、
test_cw_invest_strategy.py
**依赖**:无
**优先级建议**:5
**完成判据**:
- 登记:三卡 `GiftGrant(items_immediate=('进阶武装箱',))` 在册;四通道全空
  条目被拒、箱腿条目通过(注入式校验测试,沿孤儿键先例)
- 计数同步:STRATEGY_GRANTS 计数锁 86、底册注释与分类 docstring 两形态口径
  (83→86 差 = 本批 3 条)
- 词表:`进阶武装箱` ∈ BENCH_ITEM_NAMES(派生自动覆盖,design §2.1 断言)
- 原语:gain_bench_item 落位三态(备战空槽/席满溢出落位/溢出位被占零写留证)
  与 on_env_gained 既有道具通道行为逐项一致(producer 形参化后现役调用点
  回归不变形)
- 效果体:三卡经 `on_strategy_gained`(或 gain_invest_strategy 直调)→
  bench supply_box×1 + 步串 `box_grant:进阶武装箱`;查无效果卡安静不写不变;
  骇客卡现役效果体回归不变形
- 一致性锁:`_STRATEGY_BOX_GRANTS` 与 STRATEGY_GRANTS 三卡 items_immediate
  逐对相等;席满行为锁(bench 满 pick → overflow_card == '进阶武装箱',
  名字经溢出落位真值暴露)
- L1 全量 `-m "not slow"` 全绿(基线 1654 + 本批新增)
- §12 通用工程门
**验收凭据形式**:test_cw_gain_chain.py / test_cw_invest_strategy.py 全绿 +
L1 全量数字;ruff 干净

## 3.2 sim:选卡落箱 E2E

**范围**:design §2.4——test_cw_sim_backend.py 新用例:offer 注入三卡之一
(沿 test_strategy_pick_chain_burst_gold 惯用法)→ pick → bench
`supply_box`×1 + `pending_item_grants` 不受扰(立即发放不经队列)。**不含**:
kernel 改动(全部在 3.1)。
**设计依据**:design.md §2.4
**文件面**:sr-od-test/test/sr_od/application/currency_war/test_cw_sim_backend.py
**依赖**:3.1
**优先级建议**:5
**完成判据**:
- 新用例:pick 战术义眼++(或保守派)→ bench supply_box×1、
  pending_item_grants 保持 [](立即发放不进入定时队列)
- 回归:test_cw_sim_backend.py 既有用例全绿(基线 27 + 本批 1)
- §12 通用工程门
**验收凭据形式**:test_cw_sim_backend.py 全绿

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本 + 关联进度树注记 + 本迭代 README 收口。
**设计依据**:本文件「正本更新清单」节
**文件面**:清单所列正本文档;.debug/progress/ 两迭代目录
**依赖**:3.1、3.2
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致
**验收凭据形式**:文档对照 review

## 正本更新清单

- docs/develop/sr_od/application/currency_war/game_state/gain-chain.md:
  §3 on_strategy_gained 现役枚举更新(骇客单行 → 骇客 + 三箱腿卡;效果体
  消费 gain_bench_item)、§2 原语清单补 gain_bench_item(占席道具公开口)
  ← 阶段 3.1
- docs/game/currency_war/research/invest_effects.md:三卡箱腿形态
  (获得时点占席道具发放,进阶武装箱首例)← 阶段 3.1
- docs/develop/sr_od/application/currency_war/game_state/strategy-env-impacts.md:
  §3 新增三卡四槽条目(形状沿 §2 四槽表,先例 = 大裁员条):官方原文槽 =
  cw_invest_data.py 行位;机制槽内标注未建模腿申报(义眼++/保守派战斗被动腿
  = 策略效果建模批;快请专家·彩好运令牌腿 = 消耗品域、2×【】空括腿 = 数据源
  缺口不猜);state 影响槽 = 箱腿已建模(PICK_INVEST_EFFECTS 效果体 +
  gain_bench_item 链原语,逻辑写);策略层消费槽 = 「候策略侧」(正本惯例);
  三卡均新立行(该文件 §4 目录口径
  STRATEGY_EFFECTS ∪ STRATEGY_ECONOMY 均不含三卡,无并列可补)← 阶段 3.1
- .debug/progress/2026-09-23-invest-effects-calc/checklist.md:三卡行
  (战术义眼++/保守派/快请专家·彩)处理方式列注记「箱腿已建模(2026-09-24
  advanced-armory-box),战斗腿未建模」← 末阶段
- .debug/progress/2026-09-24-advanced-armory-box/README.md:进度收口
  (落地 x/y done、正本更新清零)← 末阶段
