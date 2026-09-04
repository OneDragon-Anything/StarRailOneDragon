# A/B 失败归因:新层(cw3)为什么几乎不出手

> 批次:`AB_cw3_n40_s0`(新,cw3)vs `AB_legacy_v2_n40_s0`(旧,decision_v2),同 seed 0-39、同池指纹 `6400d5d8edeaf68d+eqg1`。
> 方法:sim-testing「找问题」三步(全量账本统计 → 逐帧深读 → 门控热点定位),叠加**进程内重放探针**(seeds 0-9,运行时包装 `Cw3SkeletonStrategy.decide_prep` 捕获 `session.cw3_frame['decisions']` + 对 `cw3.strategy_shell.decide_buy` 全量埋点;未改任何仓库代码)。重放复现了批次 headline(金囤 200+ / 终级 6 / hp 归零),证据可信。
> 数据边界:sim 未建模装备效果与 P2 专属;`decisions.jsonl` 的 `actions[]` 只含首个决策帧,后续重入帧的决策只在 `session.cw3_frame`,故探针重放是必要手段。

---

## 一、现象的量化拆解(全量 40 局统计)

| 面 | 新侧 | 旧侧 |
|---|---|---|
| 动作构成(全批) | BuyCard 598 / RefreshShop 253 / LevelUp 42 / **SellBench 3 / 部署换位 0** | BuyCard 1071 / LevelUp 1448 / RefreshShop 764 / **CompTransaction 934 / SellBench 287** |
| 零动作轮占比 | 162/461 轮(35%);P2 段几乎全空转(2,1)-(2,7)零动作 20/10/8/10/10/3/4 局 | 25/554 轮 |
| 终级中位 | **6**(r5 到 6 后冻结) | 持续点经验(LevelUp 为逐击形态) |
| 金轨迹(中位) | r5=72 → r9=217 → P2 末 231-381 持续滞留 | 正常流转 |
| 板面 | 终局部署中位 6 人=当前 cap,但**开局四人组整局不变(s0 逐人核对),核心从不上板**,form 恒 0 | CompTransaction 逐轮换档 |

## 二、拒因 Top 分布(探针,10 seed / 277 决策帧 / 1374 笔逐卡判定)

| 判定结果 | reason | 次数 | 落点 |
|---|---|---|---|
| 拒 | `order2_two_resource_conjunction_fail` | **144(唯一拒因)** | `cw3/strategy/buy.py` L135-138(序 2 两资源合取:`board_vacancy≥1 ∧ bench_vacancy≥1`) |
| 批 | `ruling_17_overflow_free_spend` | 565 | buy.py L96(>息线随时花) |
| 批 | `same_band_small_spend` / `hold_domain_pass_exempt_or_instant` | 56 / 9 | buy.py L113-116 |
| **批准但未发射** | (刷新早退推迟) | **323 笔** | `strategy_shell.py` L507-532(刷新发生则本帧止)× 引擎逐动作消费 |

**关键读数:金约束门几乎没拒过人。** p46 否决域、[41] 囤 S 门、满息金锁合计 0 次拒——「金位<S 恒 defer」「证据门 fail-closed」这些候选嫌疑全部排除。买入门不是瓶颈。

### 逐机器门控热点(逐帧深读 seed 0-2)

1. **`board_vacancy` 全程 = 0**(277 帧无一例外)。序 2 场况插件(买了即上的战力件)被合取门整类拒死。
2. **升级机 defer_bank 冻结在 L6**:`decisions['levelup'] = {action:'defer_bank', reason:'arm2_fail_a=True_b=False_c=…'}` 逐轮复现。
   - 臂一(阵容驱动)`waiting_unit` 要求 `board_vacancy≥1 ∧ bench 有线件`(`strategy_shell.py` L403-406)——board 无空位 → **臂一整局不开**;
   - 臂二 b=False:3 费搜索窗 L6→L7 ΔV_band < U_L+p47 息损(`levelup.py` L148-161;p39 锚「3费2星 L6→L7 ΔV=28.4 vs U=40 纯移位负」)——**按证明口径该 defer**;
   - p48 目标线 S≈120-140(`defer_bank` 的 s_line 实测值)→ 金位低于 S 时连溢余自由花都被收窄。
3. **刷新机预算型多刷 + 每帧早退**:`refresh.why='R1_started_budget_capped'`,n 实测 5→38(占预算口径),p_hit=0.0885。sim 引擎逐动作消费、遇 RefreshShop 立即重决策、段上限 8(`engine_p1.py` L916-933 `for _seg in range(8)`)→ 每刷一次吃掉一段,部分轮 8 段全被刷新耗尽,**当轮已批准的买入一笔都发不出去**(seed0 r6 实录:n=12,11,10,…,5 逐帧递减,金每次只 -2;323 笔批准买入被这样推迟)。
4. **零动作轮的成因**:店 Face 大量卡被知识层分类为序 6(纯冗余,`cc.order==6` 直接跳过,连 `decide_buy` 都不进)+ 序 2 被合取门拒 → 整帧空集。金囤到 200+ 也买不了:能买的序 1(线件)店里没有,能买的序 2 被空位门拒。

## 三、根因链

```
主根(架构未实现):cw3 薄壳没有部署/换位机器
  证据:decide_prep_action 恒 BailToOuter('cw3_skeleton_no_machine')(strategy_shell.py L563);
        update_target 不设 target(L341-342);
        全批 40 局部署/换位动作 = 0(旧层同批 934 次 CompTransaction + 287 次 SellBench)
    ↓
board_vacancy 恒 0 → 三处联锁饿死:
  ① 序 2 场况插件整类拒(buy.py L135)→ 战力件买不上板
  ② arm1 waiting_unit 恒 False(levelup 消费点 shell L403-406)→ 升级只剩 arm2
  ③ 买入的线件只能压 bench,由引擎自动补位上板、无换位 → 开局 junk 板整局不变
    ↓
arm2 b=False(p39 证明:L6→7 3 费窗纯移位负,口径该如此)→ 终级冻结 6
p48 S≈120-140 囤金 + 店面序 6 化 → 金滞留 200+,花费率 0.112、空转 0.382
次生(实现层):刷新机 R1 预算型多刷(n≤38)× 引擎逐动作重决策(段上限 8)
  → 104/277 帧刷新早退,323 笔已批准买入被推迟/当轮丢失 → 空转进一步放大
    ↓
板面战力不涨 → 掉血不受控 → final_hp 全 0(旧侧 0-37)
```

## 四、「实现 bug vs 供给不足」二分结论

**属「供给不足」(口径该如此,但上游供给断供)**:
- `order2_two_resource_conjunction_fail`:设计原文即两资源合取([35]/[31]③),门本身没错——错在没有机器去创造 board 空位;
- p39 臂二 defer / p48 囤 S / [41][17] 金门:全部按证明口径正确运转(实测几乎没拒过),是「正确地什么都不做」;
- 序 6 分类(店面大量判冗余):分类器按注册表工作,但既无换线也无部署,分类前提(活跃线)名存实亡。

**属「实现缺失/bug」**:
1. **部署/换位机器整块缺失**(决定性缺口):A/B 里旧层每局 ~23 次换档 + 7 次卖,新层 0 次。薄壳阶段已知,但它是本批全部哨兵越线的第一因。
2. **刷新早退 × 段上限联锁**:薄壳按「刷新发生则本帧止、下一决策环重判」设计(shell L507-532),引擎逐动作消费+段上限 8(engine_p1 L916-933)使「重判」成本变成每次一段——预算型多刷(n 最大 38)必然把买入挤出当轮。两侧语义各自成立、组合后互相破坏,属实现层需收敛的接口口径。
3. **成型指标恒 0 是结构性必然**:`update_target` 不设 target → form 机器无输入 → `form_ok`/`末轮成型度` 恒 0,该指标在换档机器落地前无判读价值。

## 五、候选修复清单(按治本序)

1. **给 cw3 接入部署/换位通道**(CompTransaction / DeployMove,或最小版:线件买入后与板上非线 1★ 换位)。证据:全批 0 换位;277 帧 board_vacancy 恒 0;arm1/序 2 双饿死均以它为根。落地后序 2 门、arm1 会自然打开,无需改门本身。
2. **收敛「刷新早退」与引擎段预算的口径**:预算型多刷一次帧内完成,或重入重判深度与买入让路规则显式化。证据:seed0 r6 n=12→5 逐帧递减、323 笔批准买入被推迟、部分轮 8 段全耗于刷新。
3. **`waiting_unit` 谓词去「board_vacancy≥1」依赖**(换位可行 ≠ 当前有空位)。证据:shell L403-406,arm1 全批 0 次开启。
4. **复核 L6→L7 冻结是否符合过渡阵容意图**:p39 锚下 3 费窗升级恒负 EV,若过渡路线需要 L7 战力,该口径需重新证明或给阵容驱动臂补通道。证据:全批终级中位 6,r5 后 LevelUp 0 次。
5. (低优先)**换线/评分机器(E1/E2)落地前,form 类指标标注「无判读价值」**,防后续批次继续拿恒 0 指标当哨兵。

## 六、与旧侧同 seed 对照(确认「该做没做」而非「环境没给机会」)

同池同 seed 下旧层逐轮动作量:BuyCard r1-r9 每轮全批 45-177 笔、CompTransaction r1-r7 每轮 61-191 笔、LevelUp r5-r9 每轮 90-302 次——**环境供给(店面/金/节点)足以支撑高频操作**;新层在同环境 r7-r9 每轮仅 20-56 笔、r10 起归零。差异全部落在决策层,非环境断供。
