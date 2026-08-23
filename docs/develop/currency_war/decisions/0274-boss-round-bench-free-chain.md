# 0274 - 腾席链三改:boss 轮禁升级 + 卖件优先 + 真缺人口/息引擎前置(口述[32])

- 日期:2026-08-24
- 状态:accepted
- 关联:口述 [32](user_playstyle,局72 r9 实证);批⑧ F2 局72;ADR-0266(息引擎门);r364/r366b(局47 死循环修)
- 落点:`default_strategy.py` `_free_bench_step`(腾席链)

## 背景 / 决策驱动

局72 r9(boss 轮)腾席链 b 连升 5→6→7,进 boss 剩 4 金。口述[32](2026-08-23 用户权威):
大部分攻略 5-6 人口就能过位面1——r9 花光金币升级是纯浪费(升级的 cap 收益下轮才兑现,
boss 当轮不上场);腾席需求优先用卖件解决;升级腾席只在「杂件卖无可卖且人口确实不够」
(攻略基准 cap-deployed≥1 就不该升)时考虑;boss 轮一律禁升级。

## 决策

腾席链次序从 `a deploy → b 升级 → c 卖最弱 → d 留置` 改为:

```
a  deploy 空位(零成本最优,不变)
a2 卖杂件(新增:off-target  bench 件,最低价值先卖)
b  升级(三前置,见下)
c  卖最弱(不变)
d  留置(不变)
```

1. **boss 轮禁升级**:`_is_boss_round`(node_type=='boss' 权威 + round≥9 先验,supply
   例外——判定源同 update_target `_boss_window` 前两支)→ 跳过整段链 b(含 gold 真值
   等待:不升就不必开店),落 a2/c 卖件。位面切换首战(plane≥2 r1)不辖——那是 pivot
   冻结窗语义,非「位面末节点」。
2. **卖件优先于升级**(a2):判据 `_card_supports_target` False(off-target;与 deploy 的
   sell-offtarget 腾位同源)+ `_bench_sell_value` 最低价值 + 3合1 重复件保护(同
   `_weakest_bench_idx`)。target=None(reactive 早段)跳过(无 off-target 语义,防全卖)。
3. **升级三前置**(b):
   - 真缺人口:`_cap_shortfall` = 想上场件(`_should_deploy` 同链 a 判据)超出
     「cap − deployed」的富余数 ≥1(现有空位可吸纳的先扣)——缺口 0 时升级无当轮可兑现
     的人口收益,不升,也不为升级空等 gold 真值;
   - 息引擎门:`_levelup_engine_ok`(ADR-0266 同款:lv<5 豁免;曾达满息 latch ∨ 升级
     总成本花完后金仍 ≥50)——boss-breaker/catchup 之外**第三条升级通道**的漏网收口;
   - 原有 level_up_gate + r364/r366b gold 真值等待/stale 试算逻辑保留不变。

配套:`_pseudo_state` 补拷 `node_type`(权威源 session.node_type_current,备战节点行);
`decide_prep_action` 拆实现体 + **后置 latch 采样**(ADR-0266 同款语义:决策读「此前」
是否曾达满息,决策后置位;default 栈此前无采样端)。

## Considered Options

| 选项 | 结论 |
|---|---|
| **A(选定):三前置 + a2 卖杂件插入** | 口述[32] 三条各落一判据;复用既有单一源(off-target/价值排序/引擎门),零新常量 |
| B:只加 boss 轮禁升 | 局72 形态只在 boss 轮堵住;非 boss 轮「杂件可卖却升级」同病漏网 |
| C:boss 轮连卖件也禁(纯留置) | 口述明说「腾席优先用卖件解决」——卖件在 boss 轮合法且正确 |
| D:cap-deployed 字面 ≥1 才升 | 与口述「cap-deployed≥1 就不该升」矛盾(任务规格的「cap-deployed≥1」按「缺口≥1」
| | 落地:空位吸纳后仍有想上场件;锁3「缺口 0 → 不升」双向钉死) |

## 后果

- 局72 形态(boss 轮连升级耗光金)根除;非 boss 轮的「杂件在席却升级」「板未满却升级」
  两类漏网同收。
- 行为收紧面:bench 全杂件且 target=None 的早段局,链 b 不再被杂件触发(升级本就该由
  主流程 gate 管,腾席链只管腾席)——旧锁 `test_prep_director` 4 条链 b 可达性 fixture
  补「板满+应上场件」 precondition(锁的语义是 gold 真值机制,非可达性本身)。
- 息引擎门收紧 default 栈腾席链升级节奏(lv≥5 未立引擎时)——与 ADR-0266 对 boss-breaker
  的影响面同族,sim/实机分布对照归当期验证。

## 验证

- 锁:`test_cw_r412_bench_free_gates.py` 5 条——boss 轮(node_type 权威 + r9 先验)拒升 /
  bench 满杂件可卖→卖不升 / 缺口 0→不升(连 gold 等待都不进)/ 杂件卖尽+真缺人口+引擎立
  →允许 / 引擎未立(lv5 花完<50)→拒升落卖件。
- 前置自检:非 boss 轮同 fixture LevelUp 正常出(禁令只杀 boss 轮,不误伤常规升级)。
