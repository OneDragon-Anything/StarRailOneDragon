# ADR-0328:r408 同轮互斥时序缺口修复(登记点=动作采纳处 + 执行域对齐)

- 状态:accepted(W67 批)
- 日期:2026-08-25
- 决策:见下「决策」节;正文落点 = `decision_v2/arbiter.py`(
  `_register_accepted`/主循环采纳处/补偿趟采纳处) +
  `decision_v2/discipline.py`(`register_round_bought`/carry_gate
  腾位买登记) + `decision_v2/strategy.py`(decide_prep ⑤ 执行域
  对齐 `exec_state`/演进与谷底回滚卖件登记 `_register_early_sells`)。
  W66 合流总验「最高价值异常」修复批。

## 背景(现象与根因)

W66 合流总验(n=400,pool 指纹 6c0c8397f3f38a58):v2
`no_same_round_buy_sell` 同 seed 14→25、**96/400(24%)**——同轮
「BUY X(店新副本)+ SELL X(段首旧副本)」振荡,白拿 XP +
引擎种子归零(oscillation_xp_cap 20/400 全为其子集)。该检查是
ADR-0267/r408 **0 容忍**锁;与 W52 remediation 非主因(交集
7/96 < 随机期望 9.6)。

**探针钉死(seeds 0/6/14)后发现两类机制**:
1. **决策级时序缺口**(W66 报告 §5-1 结论):r408 守卫
   (`same_round_mutex`/`round_sell_blocked`/`_sell_blocked`)查
   `session.v2_round_bought`,该集合只在 **decide_prep 尾部**
   (arbitrate 之后)统一登记——同趟 arbitrate 内先采纳 BUY X,
   后续 SELL X 候选裁决时守卫读**上一段已买集**,双双过。
2. **执行域错位**(本批探针新发现,seeds 0/6/14 实证的**主来源**):
   arbitrate 的 `working` 从 decide_prep **入口原始态**初始化,而
   真实执行序里**演进事务 CompTransaction(decide_prep ②步)先于
   arbitrate 落地**——COMP 的 deploy/undeploy/sell 改变 bench 槽位
   布局后,SellBench(idx, intended=原始槽内容)执行时槽位已指向
   他人(常是刚采纳买入的同名卡)→ **实卖错件** → 账本如实转录
   「BUY X → SELL X」→ no_same 违规(名义违规,机制是执行错位)。
   W66 报告把 seeds 0/6/14 全部归为决策级,本批 arbitrate log
   逐行核对:修复决策级后 0/6/14 仍违规,且 arbitrate 内**无同名
   BUY+SELL 共现**——违规全部来自执行错位。

**根在哪一层**:流程层——「守卫的观测域(动作采纳的同一事务域)」
  与「登记/校验的时点(延迟到趟尾)」不一致;以及「决策域(working
  从入口态)与执行域(前置动作后)」不一致。前者让已采纳买不可见,
  后者让 SellBench 槽位语义漂移。

## 决策

1. **登记点前移到动作采纳处**(决策级):arbiter 主循环采纳
   BuyCard 即 `register_round_bought`(v2_round_bought,轮键自校验),
   采纳 SellBench 即 `register_round_sold`;补偿趟受益买重发、
   carry_gate 腾位买同样采纳即登记;engine_seed 购入轮登记
   (ADR-0289 §5)随采纳处一并完成(`_register_accepted`)。
   decide_prep 尾部不再兜底回写(单一登记点)。
2. **执行域对齐**(执行错位):decide_prep ⑤ 把前置已采纳动作
   (演进 CompTransaction/谷底回滚/演进卖件)simulate 成 `exec_state`
   传给 arbitrate 作 state 参数——arbitrate 的 working 从执行域
   初始化,index_drift/same_round_mutex/floor/资金评估基于「真实
   执行序」;候选生成/过滤/评分仍用原始态(候选 idx 语义=原始槽)。
   演进/谷底回滚的卖出件(CompTransaction.sell/SellDeployed)在
   arbitrate 前登记同轮已卖集(`_register_early_sells`)。
3. **不变量**(r408 语义在趟内完整):同一趟内买过的名字不可卖、
   卖过的名字不可买,且 SellBench 执行时槽位内容与提案一致
   (执行域校验消除卖错件)。

## Considered Options

- **仅决策级修法(采纳 BuyCard 时登记 v2_round_bought;W66 建议
  方向①)**:不能消除执行错位(0/6/14 探针实证,arbitrate 层已无
  同名共现仍违规)——否决,作为本批组成部分保留。
- **卖候选以 working 已买集过滤(W66 建议方向②)**:卖候选生成在
  arbitrate 前(无 working),且执行错位与已买集无关(是槽位内容
  漂移)——不解决本批发现的机制,否决。
- **执行器 SellBench.expect 校验(ADR-0317 既有设计)**:能防卖错件,
  但需改 sim/生产执行器(文件面外),且不解决决策级时序——留作
  执行器侧既有防线(expect 字段),本批决策域对齐使其成为冗余兜底。
- **exec_state 前置 simulate(采纳)**:把决策域对齐执行域,一处
  修两类机制(决策级时序 + 执行错位),符合「动作采纳的同一事务域」
  教义;代价=arbitrate 的 floor/资金基于前置后状态(语义修正:前置
  卖回金计入,消除「COMP 卖 + 补偿再卖」双重变现)。

## 影响面

- 行为变化清单:
  - 同趟 BUY X 采纳后 SELL X 候选被拒(决策级,r408 时序)——**意图内**。
  - 同趟先卖后买同名被拒(r408 对称臂同趟成立)——**意图内**。
  - SellBench 执行时槽位内容漂移被 index_drift 拒(不再卖错件,
    消除账本假象违规)——**意图内**。
  - arbitrate 的 floor/资金/占用基于前置动作后状态(演进回金计入,
    消除双重变现)——**意图内**(语义修正,sim headline 有波动,
    如实报)。
  - 演进卖件后同轮 arbitrate 不再买同名(已卖禁买)——**意图内**。
- 测试:新增 `test_cw_adr0328_same_round_mutex_timing.py`(六锁:
  同趟 BUY→SELL 拒 / 先卖后买拒 / 去登记变异涌现违规 / carry_gate
  登记 / 候选管线端到端 / W66 探针 seed 重放归零);W35 补偿整链
  锁构造适配(exec_state 语义:压库件选演进不消费的件)。
