# ADR-0410: formed_stop 目标件白名单 + boss 轮升级禁令删除([32] 口径定调)

- 状态: 已采纳(2026-08-27,W255)
- 关联: ADR-0343(成型停手初建)/ADR-0400(P1 末窗承接门)/ADR-0347(EV 总账升级授权)/ADR-0354(levelup 检查器判据重定义)/W123 §5.2(static_ev 保守计违规的旧校准)
- 设计件: `docs/develop/currency_war/strategy/10_formed_stop_boss_mech.md`(裁决表单一源)

## Context

用户 2026-08-27 定调两个口径:

1. **[13] 成型停手的正确语义**:成型停的是「过渡件」;**目标阵容件照买
   照囤**——[21] final 件买而不上、[22] 有用先囤正是成型后阶段的正常
   行为。现实现(`filters.filter_candidates` 尾段「formed_stop ∧
   BuyCard → ok=False」)把目标件/final 囤件一并饿死 = 语义过宽。
2. **[32] 消费有效性/腾席优先级全程通用、节点无关**(病例注已消解节点
   特殊化):但决策栈长出了一族 boss 轮特殊机制,需全量盘点逐条裁决。

## Decision

### ① formed_stop 目标件白名单

`formed_stop_active` 五项判定不变。动作级后置步改为分域拦:BuyCard 候选
仅当买入名 ∈ 白名单外才拒;白名单 = `candidates._target_names`
(hoard 目标采购集 ∪ 体系卡引擎件,[31] 三级梯队的目标层),封装在
`filters._formed_stop_buy_allowed`。链日志白名单放行行带
`formed_stop_exempt=True`;`session.v3_formed_stop` 与检查器豁免语义
(`overflow_gold_zero_buy_streak`)不变。

### ② boss 族裁决表(c 类唯一=升级禁令)

设计件 §2 全表(a/b/c 三类);落码结论:

- **c 删**:arbiter `_check_constraint('boss_levelup_ban')` 的「boss 窗
  → 一律拒」分支删除,升级裁决全走 EV 总账(`ev.levelup_ev_basis`,
  [12]/[33] 单一裁决点)。约束名保留(审计矩阵与检查器名字空间稳定)。
  同步删 remediation 两处补偿臂的「非 boss 轮才发」守卫
  (`steady_state_levelup_group`/`_compensate_slot`)。
- **b 保留有据**:boss_floor 地板族(位面末本金边际)、boss_breaker
  war 覆盖态(依据 [19] 连胜三态谱,非 [32])、default 栈 pivot 冻结
  (换线纪律 [23],两局撕囤实证)、plane_last_battle ALL IN([18] 原文
  位面末时机)、观测层 boss 轮次门(r80 防张冠李戴)。逐条依据见设计件。
- 无 a 类泛化件:[32] 是纪律文本不是代码机制,方向是去特殊化非复制。

### ③ 检查网同步

`check_levelup_interest_engine_gate` 合法授权面 {pop_slot, dp} 扩为
**{pop_slot, dp, static_ev}**:禁令删除后 static_ev 臂成为末窗升级的主
授权臂;n=20 冒测新判据涌现 static_ev 违规 8 例(seed 0/5/9/11/12),
与「该臂帧量级 0-1」的 W123 校准前提矛盾——保留计违规=系统性误报合法面。
无 auth 键的退化检测面(授权观测缺失必报)不动。

## Considered Options

① formed_stop:
- **选(b):白名单放行目标件**——直引 [13]/[21]/[22] 口述权威;
  `[31]` 三级梯队天然给出「目标 vs 过渡」的分域判据,单一源零新增表。
- (a)整个停手门降级为评分偏置:丢掉 ADR-0343 的显式回归资产与检查器
  豁免契约,改动画量大且 sim 校准负担重。
- (c)保持全拦:违反口述最高权威,继续饿死 final 囤件(W227 承接门
  就是为此在末窗打洞的先例——本决策把洞按语义补全,不再依赖缺口维)。

② boss_levelup_ban:
- **选(c)删除禁令臂,EV 总账接管**:[32] 定调为全程通用;病例注明确
  「真病是升完没有能上场的强单位」,人口位臂①(可负担性入口门+cap 满∧
  bench 有目标件)恰是该病的账面化;boss_floor 继续兜本金边际,ALL IN
  窗不稀释(评分恒用原表)。
- (a)泛化「boss 前禁升级」到全部战斗节点:与 [33] 人口位当轮兑现冲突,
  且 DP 授权已辖时机选择——多一道门只会双重计罚(ADR-0347 收编前的病)。
- (b)保留但白名单 pop_slot 帧: dual gate([12] 门收编时已裁过一次),
  禁令臂保留即维持节点特殊化语义,违背定调。

③ static_ev 检查面:并入合法面(数据驱动:8/20 局涌现 vs 校准前提 0-1)
vs 保留可疑(宁可误报):误报会永久污染冒测红绿信号,失去变异检测价值。

## Consequences

- 成型后 P1 店内出现 hoard 目标件时会照买照囤(主观测面=sim 批成型轮
  内带买局的局数上升);过渡件拒绝面不变,息纪律由既有 interest_rule/
  gold_floor 单一裁决(白名单只管候选在场,不豁免金约束)。
- P1 r9/P2r7 等 boss 轮升级从恒拒变为过账放行(boss_floor 地板内);
  补偿链在 boss 轮优先升级而非换位。exit 金下行风险由 EV 总账与
  interest_rule 同一决算承担,A/B 若需要以「出口金分布」复核。
- default 栈(direct 流)`cw_plan` 的腾席链 boss 升级禁(ADR-0274)本批
  不动(非决策主路,v2 四层为准);后续若 default 栈复活再对齐。

## Verification

- 单帧锁:`sr-od-test/test/sr_od/app/currency_war/test_cw_w255_formed_target_boss_nodemech.py`
  ——通过/拒两类各一(目标件 vs 名单外件)+ boss 帧 LevelUp 经 EV 接受 +
  可负担性拒因走总账文案。
- 回归:W107/W131/W52 三文件旧锁随语义演进修订(docstring 记过期原因);
  L1 全绿;L3 commit 前一次。
- sim 对照(冻结池 4e8f3d9637008258,n=120 seed 0-119,前后对照):
  主观测面=成型停手轮含目标件买入的局面数变化 + boss 轮 LevelUp 从 0→>0;
  见 `.debug/temp/currency_war/w255_sim_report.md`(本仓 .debug 不入 git,
  数字摘录于交付报告)。
