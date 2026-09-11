# 0267 - 同轮买卖互斥 + engine_seed 容量门(决策通道振荡 F1 根治)

- 日期:2026-08-24
- 状态:accepted
- 关联:r408;压测自由批 F1(`sim_压测_自由批_2026-08-23.md`;235 次/38 局,单轮最高 8 连);ADR-0260(engine_seed 买道——振荡的一方);ADR-0212/cw_plan r238(卖通道保护集只保成对副本)

## 背景 / 决策驱动

sim 自由批无假设扫描最大怪形态:**同轮买入→卖出同名卡**。bench 满员态下
买通道(engine_seed)与卖通道(_sell_off_target / _sell_for_interest /
_sell_scatter_for_precache / _sell_for_gold)在同一张卡上互踩:

```
段N:  卖杂牌腾位 → engine_seed 见引擎件「未持有」→ 买入(bench 回满)
段N+1: 卖通道判同一张为 off-target/最高退款杂牌 → 卖出
段N+2: engine_seed 又见「未持有」→ 再买 ……
```

机理三缺口:
1. **line_strategy 段间无记忆**——轮内 8 段各次 decide_prep 互不知晓,买过的
   卡名对卖通道不可见;
2. **卖通道保护集只保身份**(线 carry+opportunistic+桥名单 / cw_plan 成对
   副本),不保「本段新买件」——engine_seed 买进的星期日不在任何保护集;
3. **engine_seed「未持有」判据与卖出态构成永动机**——买了即持有→被卖→
   又未持有→再买,`progressed` 恒 True,段预算烧尽。

后果(自由批实证):每对振荡净 0 金、**+4 XP 白拿**(seed4 38 次白拿 152 XP
推到 level 9——等级阶梯部分由幽灵 XP 铺出)、引擎种子归零(169 次 engine_seed
买入当轮全被卖)、boss 轮 8 段预算烧在振荡上零真实补强。决策层是生产代码,
**实机同病**(每对振荡=实机真实买/卖点击)。

复现探针(构造 bench 满+锁线+engine_seed 卡在架,跑 8 段 decide_prep):
修前 7 对振荡(卖停云→买星期日→卖→买……),修后 0。

## 决策

双门 + 一对称臂(r408,`line_strategy.py` + `cw_strategy.py`):

1. **同轮买卖互斥(round-scoped 已买集)**:session 加
   `v2_round_key`/`v2_round_bought`——decide_prep 薄包装内按
   `(plane, round_num)` 换轮重置(**重置在分发之前**,卖通道生成器
   写入时键已当前),段间累积 BuyCard 卡名;四条卖通道
   (`_sell_off_target`/`_sell_for_interest`/`_sell_scatter_for_precache`/
   `_sell_for_gold`)对集内卡名禁卖(`_round_sell_blocked`)。
   **3合1 让位豁免**:同名副本(星级加权,同 _buy_guards 口径)≥3 =
   合成后冗余件,卖出是让位非振荡,放行。
2. **engine_seed 容量门**:`_engine_seed_wants` 判据补「bench 满员(≥9)
   不触发」——「未持有」在满员态先判容量;卖了腾位后的同轮买入由调用方
   st2(卖出后状态)承载,且被门 1 拦住振荡环。
3. **对称臂:同轮已卖不回买**(锁测试发现):卖通道提案即时入
   `v2_round_sold`,engine_seed / copy 标签 / pair 凑对 / line 通道
   对集内卡名禁买——否则「卖通道刚卖→st2(卖出后状态)见未持有→
   同 call 买回」以 1 对/轮的缩幅永动机存活(每轮仍白拿 4 XP、
   引擎种子仍归零;copy 通道的「买副本→卖冗余→再买副本」同病)。
   卖出提案在生成点写入(`_sell_for_interest` 的撤销分支只记
   最终存活提案)。
4. **批内 SellBench 索引降序(r408b 补漏,指挥官验收发现)**:同批
   多条 SellBench 的 bench_idx 都基于**卖出前** bench——执行器
   (sim/实机 op)逐条 pop,先弹低 idx 把后续提案 idx 左移 →
   **卖错名**(seed57 r4:提案卖青雀,弹掉 idx0 刃后实卖本轮已买
   的娜塔莎——按名互斥被索引漂移绕过;n=60 残留 5 局 seed
   25/36/56/57/58 的根因)。修:decide_prep 薄包装内批内
   SellBench 按 idx **降序**重排(先弹高 idx 不影响低 idx,
   提案名=实打名;买/升/刷保持原位)。r410b 再补:**重复槽位
   提案去重**——多条卖通道独立扫同一 bench 可能对同一 idx 各提
   一条(off_target 与 precache 同判一最弱槽),同 idx 二次 pop
   漂移卖掉相邻件(seed36 r3 姬子槽双提案 → 二弹卖掉本轮已买
   的绯英);去重保一条(两通道本就同意图)。
5. **同名跨副本无效换卡守卫(r410,局72 r8 实证,用户目击)**:
   买同名 #2(reason=line,买时合法)→ deploy 侧 sell-offtarget
   卖在场旧 #1(羁绊∩target_factions=∅,卖时也「合法」)→ #2
   顶替——净效果=同角色换卡,白付操作+装备转移。买通道前置守卫
   (`_copy_swap_useless`,挂 `_buy_guards` 可选 session 参):
   镜像 deploy 保留判据,同名在场副本会被保留(∈target_cores
   或 bonds∩target_factions)→ 买副本合法(凑对/3合1);
   所有在场副本会被卖 → 拒买(省 3 金+操作)。

合法动作保持:先卖后买的同轮序(卖杂牌腾位→买方向件)不受限——互斥只禁
「买→卖」方向;跨轮买卖(合理倒手,r383b copy 语义)不在辖内。

## Considered Options

| 选项 | 结论 |
|---|---|
| **A(选定):round-scoped 已买集 + 卖通道过滤** | 拆永动机的最小闭环:振荡必须有「买后卖」一跳,拦住这一跳整个环死;round-scoped 粒度与振荡形态严格对齐(跨轮倒手合法) |
| B:engine_seed 判据改「本局曾买过即记持有」 | 误伤真倒手(买了卖掉再遇到该买回的场景,如转型);且治不了 copy/line 通道的振荡(自由批 54+12 次) |
| C:卖通道保护集扩为「本段新买件」 | 段内序(卖在前买在后)下「本段」集合还没建出来,须近似 round-scoped——即 A |
| D:靠 _buy_guards 容量守卫自然拦截 | 守卫判的是**卖出后**的 st2(买时 bench 已被卖通道腾出位)——恒过,拦不住;这正是 bug 本体 |
| E:engine_seed 加冷却轮 | 时间维补丁,不治「卖通道不认识新买件」的结构缺口;copy/line 通道仍振荡 |

## 后果

- **预期**:同轮买后卖 0 容忍(检查项入 sim 批量);engine_seed 买入存活过
  轮界,种子语义恢复;幽灵 XP 消失(等级阶梯回归真实购买节奏);boss 轮
  段预算可用(振荡局不再劫持)。
- **权衡(如实报)**:卖通道少了一类「刚买进但判 off-target」的回收货源
  ——但该类货源本身就是振荡产物,回收它 = 净 0 金 + 白占段预算,无真实
  价值损失;锁线后方向误判的卡(如买了发现是错件)要等下一轮才能卖,
  一轮 bench 占位是可接受代价。
- 重启/重放丢 session → 已买集空,只失去互斥(回到旧行为),不引入新行为。
- 检查项 `no_same_round_buy_sell` 入 `_BATCH_CHECKS`(0 容忍;仅 v2
  栈账本适用,default 栈 reason='plan' 卖出语义不同,生产侧按
  strategy_id 分栈后选择)。3合1 收集语境的检查侧镜像:同轮有
  reason='copy' 买入的名字,其同名卖出按让位豁免不报(策略侧
  同源豁免);engine_seed/line/bridge_seed 单次买入被当轮卖回仍报。

## 验证

- 复现探针(修前 7 对/修后 0,用完即删);单帧锁
  `test_cw_r408_round_buy_sell_mutex.py`:互斥(买了不卖)/容量门(满员
  不买)/3合1 让位豁免/振荡 XP 不再白拿(多段循环零 buy-sell 对)/换轮
  重置+对称臂(刚卖同名不回买)/批内降序+重复槽位去重(索引不漂移)/
  无效换卡守卫(off-target 在场不买/target 在场凑对合法)/5 残留 seed
  逐局重放零违规(25/36/56/57/58)。
- 验收口径:`simulate_p1_batch(n=60, pool='snapshot', seed_base=0)`
  的 `no_same_round_buy_sell` = 0(指挥官验收发现的残留已归零)。
- sim A/B:归下段(压测官批次对照,hp/engines2 分布以 batch 报告为准)。
