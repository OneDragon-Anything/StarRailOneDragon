# 0280 carry 腾位门:bench 满时降保护集卖最弱件买 carry(批⑯ F3/F4)

- 状态: accepted
- 日期: 2026-08-24
- 来源: sim 压测批⑯ F3/F4(最大杠杆节);修复队列 [31] carry 响应门的规格改写

## 背景

批⑯ F3(观测臂 300 局):56 局(18.7%)出现「carry 在店+金足+未持有
+策略零买入」(148 事件,均 r7.0);分解出 **137/148 事件 bench=9 满,
其中 109 事件 bench 内零可卖件**——槽位归因:保护集 7.45/槽、
faction-close 1.52/槽、真可卖仅 0.51/事件。根因是 `_protect_set`
(双桥池 fixed∪core 全名单+锁线 opportunistic+carry,20+ 名字)把
bench 变成只进不出的仓库;唯一稀缺=bench 槽(口述[22] 囤牌纪律)。

批⑯ F4(强制买干预臂):「金够必买」单点收益≈0——300 局仅 10 事件
真注入,配对差 mean +0.037 / stdev 0.635,**统计零效应**;且 miss 的
93% 撞容量墙(买门会守卫拒买)——**强制买不是杠杆,腾位才是**。
r8-r9 的 miss(53%)买不买已无差异(终局段买入不改变 P1 结算曲线)。

## 决策

1. **carry 腾位门**(`line_strategy._carry_bench_gate`,r416):carry
   在店+金足(gold−cost≥调用方地板,不破息档)+bench 满(≥9)+
   零 off-target 可卖 → **降保护集卖最弱件再买**(reason=
   `carry_gate`);挂在 economy/boss_breaker/war 三买通道尾;
2. **「最弱件」判据**=保护集内 off-line 价值最低,与 r410
   `_copy_swap_useless` 的保留判据同源镜像——弱序:非保护件 >
   非当前线件 > 非桥件 > 副本冗余;**3合1 保护不动**:完整合成份
   (星级加权 copies==3)不腾(卖一份=拆合成材料),超上限冗余
   (copies>3,`_buy_guards` 已判纯浪费的第 4 份)优先腾;
   `_round_sell_blocked` 的 ≥3 让位豁免机制保留不覆写;
3. **收益域限定**:门只在 P1 r≤`_CARRY_GATE_MAX_ROUND`(=7)生效
   ——r8-r9 的 miss 无差异(批⑯ F4);r9 boss 轮不触发腾位
   (boss 轮禁令 [32] 同族,r≤7 一并覆盖);
4. **卖出件不回买**:腾位卖出的件入 `session.v2_round_sold`
   (r408 对称臂同源,挂同一集合);
5. **检查项**(批⑯设计表,入 `cw_sim_checks`):
   `carry_gate_bench_deadlock`(死锁指纹,P1 r≤7+锁线+carry 在店
   +金足+bench9+零买零卖;进 `_BATCH_CHECKS` 批量内嵌,修复后应
   归 0,金足口径含小额息档残差声明)、`protect_set_bench_share`
   (锁线局 r6+ 保护件占 bench ≥7/9 披露级,跨局聚合,供保护集
   收窄裁决,violations 恒 0)。

## Considered Options

- **A. carry 必买门(「金够必买」)**:拒绝——批⑯ F4 实证统计零效应
  (93% miss 撞容量墙,能注入的边缘事件对终局 HP 无可测影响);
- **B. 收窄 `_protect_set` 本体**:拒绝(本批)——保护集是双桥池
  全名单派生的结构性口径,全局收窄影响所有卖通道;先用门内局部
  降级(只在本门判弱序),`protect_set_bench_share` 披露积累证据
  后再裁全局收窄;
- **C. carry 腾位门(选定)**——对准 F3 根因(卖通道窒息)而非
  买门,收益锚在 r8 以前的 miss(F4);
- **D. 同轮卖出件可回买**:拒绝——r408 对称臂同源,回买=缩幅
  振荡(白拿 XP)。

## 影响

- `strategies/line_strategy.py`:常量 `_CARRY_GATE_MAX_ROUND`;
  新方法 `_carry_bench_gate`;economy/boss_breaker/war 三处挂接;
- `cw_sim_checks.py`:`check_carry_gate_bench_deadlock`
  (进 `_BATCH_CHECKS`)+ `check_protect_set_bench_share`(显式调用);
- 测试:`test_cw_r416_carry_bench_gate.py`(5 锁:腾位买成/直接
  通道不走降级/3合1 不腾/r8+ 不触发/同轮不回买+检查项双向锁);
- sim 预期:miss 率(死锁指纹)从 18.7% 显著下降;hp 类指标改善
  须过 n=300 段间噪声带(hp_ge_60 ±0.020,批⑯ F2)才可采信——
  P1-only sim 看不到 P2 成型连续性收益(批⑯ 盲区声明)。
