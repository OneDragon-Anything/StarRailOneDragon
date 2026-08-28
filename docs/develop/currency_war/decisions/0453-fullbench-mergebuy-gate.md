# 0453 满栏合成买:ADR-0283 硬守卫升级为「触发合成则允许」(W544)

- 状态: accepted
- 日期: 2026-08-29
- 来源: 用户权威裁决(2026-08-29):「备战满时,触发合成的购买应该被支持,否则被迫卖有用角色」;机制规格唯一源 = `docs/game/currency_war/research/merge_mechanics.md` §2.5(2026-08-28 口述·权威)

## 背景

ADR-0283 时代确立「bench 满 = 硬模态拒买」,决策层满栏购买判据此后只留
一个豁免:ADR-0325(S3)的 k=1 特例——同名同 1★ 已有 2 份、买第 3 份
(`will_merge_on_buy`)。merge_mechanics §2.5 口述补全了满栏例外的一般
机制后,旧判据过窄:

- **k>1 自动多买不可达**:已有 1 份、店内刷 2 张时,游戏一次点击自动
  买 2 张完成合成(k = min(店内张数, 3−已有数 mod 3));旧门按「本次
  只买 1 张、凑不满 3」拒——该拒直接把决策层推向腾位卖(补偿器
  `_compensate_bench`/腾位通道卖掉有用角色),正是裁决禁止的后果;
- **金账口径缺 k 维**:满栏合成买无价格优惠(全款 k×单价),旧
  `_cost_of` 只按 1×单价校验金地板/息账,补偿缺口也会凑少。

## 决策

满栏购买判据从「一律拒 + k=1 特例豁免」升级为一般式(判据单一源 =
`cw_state.merge_buy_completes`/`merge_buy_k`,新增于 `cw_state`):

- **允许条件** = 同名同星计数(备战栏+场上,`_merge_bench` 全场域分组
  键)+ 本次购买 ≥ 3(本次点击完成恰好一次合成);
- **k** = min(店内张数, 3 − 已有数 mod 3)(§2.5 绝不多买上限);
- **金** = k × 单价全款校验(`arbiter._cost_of` k-aware;补偿器
  `remediation._compensate_gold` 缺口同式);
- **不满足合成条件仍拒**(ADR-0283 守卫语义保留为兜底);
- **carry_gate 同步**:腾位门前先判合成可达——核心在店且本次购买完成
  合成 → 不卖任何件直接买;
- **执行层确认**(shop.py):一次点击 = 游戏自动多买 k 张,执行仍单击;
  执行账改记 1×单价 + (k−1)× 多买补差,与 gold 差值对拍(±2 容差)
  对齐;k 公式自 shop.py 内联计算收敛到 cw_state 单一源(W536 的
  `compute_buy_expect` 消费 `BuyPurchase.count`,增量端不动)。

### Considered Options

- **A. 维持旧门(k=1 特例)**:拒绝——用户权威裁决点名「被迫卖有用角色」
  不可接受;k>1 场景结构性不可达 = 满栏时定向件买入完成率受损;
- **B. 只改决策门,金账不动**:拒绝——k×单价全款是 §2.5 机制事实,
  1× 校验会让金地板/息账/补偿缺口系统性算少(破地板买);
- **C. registry 开关灰度**:拒绝——行为输入已就绪(机制口述权威 +
  用户裁决),无「待标定/待验证」挂账理由;按策略开关生命周期,
  直接落码,零漂移由「只改满栏分支」的结构保证;
- **D. 判据收敛到 cw_state 一般式(选定)**——k 公式此前已有三处
  语义(shop.py 内联/W536 增量端/决策门),收敛一处防漂移;
  `will_merge_on_buy` 保留为生成侧 merge 标记(k=1 特例语义)。

## 影响

- `cw_state.py`:`same_star_count`/`merge_buy_k`/`merge_buy_completes`
  单一源;`simulate` BuyCard 满栏分支支持 k 张多买(金 k×、店 k 张
  下架、`_merge_bench` 合成落点、临时尾槽截回);
- `decision_v2/arbiter.py`:bench_capacity 门豁免判据升级;
  `_cost_of(cand, working)` k-aware(gold_floor/interest_rule 消费);
- `decision_v2/discipline.py`:carry_gate 合成可达不腾位;
- `decision_v2/remediation.py`:金补偿缺口按 k×单价;
- `operations/prep/shop.py`:k 公式消费单一源 + 执行账补差;
- 测试:`sr-od-test/test/sr_od/app/currency_war/test_cw_w544_fullbench_mergebuy.py`
  (k 公式/门/金账/执行/carry_gate 五面);
- **未辖面(挂账)**:sim 执行层(cw_sim.py)的 ADR-0283 守卫本批冻结
  (并行批在飞面),sim 内满栏 BuyCard 仍不执行——sim↔生产在满栏合成
  买帧存在已知执行层滞后,升级 cw_sim 执行守卫的批次须与本 ADR 对齐
  (届时 `bench_full_skipped_buys` 披露键语义同步收窄为「非合成拒买」)。
