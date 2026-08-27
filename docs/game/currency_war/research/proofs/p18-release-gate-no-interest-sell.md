# P18:门辖帧无涨金动机卖候选(release 消费门的集合过滤不变式)

> 状态:**已证(集合过滤不变式;辖域=候选生成器输出集,非帧内金账)**
> 对象:W348 落地的 release 门——`decision_v2/candidates.py` 的
> `_release_sell_gate` + `decision_v2/posture_release.py` 的 `spend_gate_active`。
> 依据:`candidates.py:366-389`(门)/`:392-427`(`_sell_tag` 唯一调用点)/
> `:463-481`(生成器卖段唯一生成点);`posture_release.py:225-237`(判据单一源);
> ADR-0296(候选生成器架构)/W362 审查报告批② §6(命题立项挂账与边界约束)。
> 提出:W362 审查挂账;证明=本批(纯文档批,代码路径穷举,无实验数据)。

## 命题

设 F 为一决策帧,满足:**门辖帧** ≜ `registry.release_spend_gate_enabled = True`
∧ `spend_gate_active(session, registry) = True`。设 Sell(G(F)) 为候选生成器
`generate_candidates(state, session, registry)` 在帧 F 输出的候选中,动作为
`SellBench` 的子集;`tag(c)` 为候选的动机档。则:

**Sell(G(F)) ∩ {tag ∈ {off_target, for_gold}} = ∅**

即:门辖帧内,候选生成器不产生**以凑息/换金为目的**的卖出动作候选。

**边界(不得过度声明,照 W362 审查原话)**:本命题**不**等价于「帧内金不涨」
——①门辖外的 free_bench 腾席卖照常生成且返金;②演进替换事务卖
(`CompTransaction.sell`)与谷底回滚卖在演进引擎与 strategy 发射点,不经候选
生成器(结构上不受辖);③帧内金还会因买/升/刷**支出下降**而相对变化。
命题只辖「生成器输出集中的凑息向卖档」,金账不在辖域。

## 证明(代码路径穷举)

### ① 卖动作在生成器内的生成点唯一

`generate_candidates` 的动作类逐一核对(`candidates.py:430-497`):买
(shop 循环→`BuyCard`)、升(`LevelUp`)、刷(`RefreshShop`)、部署
(`_deploy_candidates`→`DeployMove`)、合成(`_synthesize_candidates`→
`Synthesize`)——均非卖。`SellBench` 的**唯一**生成点是 bench 循环
(`:463-481`),每件经 `_sell_tag`;`tag is None` 即不生成候选。

### ② 全部卖档无一例外过门

`_sell_tag`(`:392-427`)按 `registry.sell_tag_priority` 只裁三个档:
`off_target`(非目标非应急)/`for_gold`(应急非目标)/`free_bench`(bench 满
腾位);守卫链(`_sell_blocked`/`round_sell_blocked`/`sole_engine_sell_blocked`)
不过者提前返回 None(连候选都不存在,更不在命题辖域)。**返回值恒为
`_release_sell_gate(tag, …)`**(`:427`)——不存在绕过门的 return 路径。

### ③ 门是纯过滤,只辖涨金向两档

`_release_sell_gate`(`:366-389`):

```
tag ∉ {off_target, for_gold}  → 原样返回(透传)
tag ∈ {off_target, for_gold} ∧ spend_gate_active(…)  → 返回 None
```

门不产生、不改写候选(纯过滤);门辖帧内,两涨金向档的 `tag` 为 None
→ 由 ①,该档候选不进入输出集。∎

### ④ 判据单一源无第二判定源

`spend_gate_active`(`posture_release.py:225-237`)=
`registry.release_spend_gate_enabled ∧ session.v3_release is not None`。
`v3_release` 由 `evaluate_release` 每轮入口写入(与义务预算/latch 同源),
消费面(scoring 息 EV 中性/本门)经此读 release 态,不在各自层重算 FLIP
——「门辖帧」的定义本身单源,命题前提无歧义。

### ⑤ 反例检验(构造失败记录)

对「门辖帧内存在涨金向卖候选」穷举构造路径:

| 构造路径 | 结果 |
|---|---|
| bench 循环产 off_target/for_gold 候选 | ②③ 拦截(tag=None) |
| free_bench 卖「其实也返金」 | ③ 透传,但动机=腾 slot 非「以凑息为目的」,属显式豁免面(锁 B `test_release_gate_spares_free_bench_sell` 互证)——非反例 |
| 演进事务卖/谷底回滚卖凑息 | 不经生成器(演进引擎/strategy 发射点),辖域外——非反例 |
| 开关关帧(|门 no-op)| 不满足前提(非门辖帧),命题空洞真——非反例 |

四路构造全部失败,反例不存在。∎

## 边界与已知残留(防静默偏差)

1. **for_gold 防御性对齐**:for_gold 要求 hp≤emergency_hp,与 FLIP 辖区现
   不相交(FLIP 显式让位同带)——本门对该档当前**无可辖对象**,是防辖区
   调整后静默对冲的对齐件(`candidates.py:379-380` 注释)。命题对它成立
   是空洞分支,非经验内容。
2. **C2 残留不辖**:V_D 的 C_dec 息损项(`scoring.py:809-813`)是**评分面**
   对冲,不在本命题辖域(本命题辖生成器输出集)——W362 挂账 C2 另案审计。
3. **开关前置**:命题全部内容以 `release_spend_gate_enabled=True` 为前提;
   默认 False 时恒空洞真(A/B 基线臂零漂移)。

## 检验点

1. **单帧实例**:锁 B(门辖帧断言 sell tag 集 ⊆ {free_bench})是命题在
   单帧上的实例;门辖帧内出现 off_target/for_gold 卖候选即违命题(可机检)。
2. **辖集完备性(结构检验)**:向 `sell_tag_priority` 新增涨金向 tag 时,
   必须同步进 `_release_sell_gate` 的辖集字面量,否则违命题——可机检:
   「辖集 ⊇ sell_tag_priority 中涨金向档集」静态断言。
3. **豁免面锚**:门辖帧 ∧ bench 满时 free_bench 卖仍生成且返金——命题
   边界(非凑息动机豁免)的持续实证;若该锚消失(连 free_bench 也被抑制)
   说明门被改写过宽,回炉。
4. **边界字面检验**:任何把本命题表述为「帧内金不涨」的文档/判据即违
   本命题边界声明(金还会因 free_bench 卖返金与买支出下降而变化)。

## 关联

- P11(泄息义务的存在性前提:溢余段持有边际=0)、P17(FLIP 姿态 A/B 判据);
- ADR-0296(候选生成器架构)、W348 断链修复批(`61d16733`)、W362 审查批②
  (`.debug/temp/currency_war/w362_six_review_batch2/REVIEW.md`,挂账来源与
  「防过度声明」边界原话);
- 姊妹篇 P19(同为 W362 挂账命题化:计数语义)。
