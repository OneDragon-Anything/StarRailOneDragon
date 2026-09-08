# ADR-0617: 满栏合成买双账同构(T-182 守卫误炸事故——tracked 满栏丢件漏记合成,写端单一源治本)

- 状态:已实施(代码+测试+flow as-built 三处回填;落地审需修项闭环)
- 日期:2026-09-09
- 关联:ADR-0517(§守卫两属(ii) 双账断言)、ADR-0518(**§对抗修复批补登「满栏分支生产不可达」声明被本事故证伪,见 §4 更正**)、ADR-0523(守卫两级分型)、ADR-0520(播种层退役先例)、merge_mechanics.md §2.5(满栏例外机制权威档);落地审=`.debug/temp/currency_war/attacks/t182_dual_ledger/落地审.md`

## 背景

运行局 2026-09-09 05:52(run_20260909_053235,plane 1 round 9)商店访问内连续两次炸出 `guard_expected_vs_tracked` AssertionError(stage='project',cw_shop_action_ops.py:272):

- crash#1(05:52:01):expected=[阿格莱雅,丹恒·饮月,花火,艾丝妲,绯英,阮·梅,绯英,花火,希儿] vs tracked=[椒丘,丹恒·饮月,…];
- crash#2(05:52:25):expected=[椒丘,三月七,花火,艾丝妲,绯英,阮·梅,绯英,花火,希儿] vs tracked=[椒丘,丹恒·饮月,…]。

两帧 bench 均满栏 9/9 且含同名同星副本对(绯英×2/花火×2,T-59 开放问题实测现身:同名同星可同场为合法态),访问内动作序列同为「满栏 m2_merge_completion 合成买 → 下一动作买新卡落腾出槽」。

## 根因(定谳:expected 正确 / tracked 漏记)

满栏(9/9)下的合成完成买(reason=`m2_merge_completion`,own=2 = bench 素材@槽 + 场上同名同星载体)走 merge_mechanics §2.5 满栏例外:游戏真实行为 = **接受买入并自动合成**——bench 素材被消费(槽位腾出,9→8)、场上载体升星(「场上同名卡升星优先」落点规则)。两侧建模自此分叉:

- **投影侧(`simulate`)正确**:bench_place 失败 → merge_buy_completes 判通过 → 临时挂尾 k 张 → `_merge_bench` 全场域合成(素材消费/载体升星)→ 截回定长 9;
- **tracked 侧(`mutate_bench_deployed`)漏记**:bench_place 满栏**丢件** → 只见 2 份不合成 → 槽位不动(9/9 维持)。

守卫的满栏豁免(`apply_action_outcome` 的 `_skip_guard`,按投影侧占用数 ≥ BENCH_CAPACITY 判)在合成买当帧成立、守卫跳过;**同 visit 下一动作**(阿格莱雅/三月七)落在投影侧已腾出的槽,投影侧占用 8 < 9 逃出豁免,守卫对拍两本已分叉的账 → 炸出。project 消息标注「投影建模 bug?」为误导归因——真实分叉源在 tracked 侧。

**证据链(金链逐动作;口径精确化按落地审 F-3)**:①买入落地 = 屏读金前后对照(05:51:59 offer 帧 61 → 05:52:05 offer 帧 59;05:52:19 帧 51 → 05:52:28 帧 48),每动作 k=1 购买款逐扣零残差,且满栏非合成买必拒(merge_mechanics §2.5 常态)反推被接受的买必为合成完成买;②投影侧一致性 = journal 回执行 gold=60/bench_used=8(crash#1)与 gold=49/bench_used=8(crash#2)——**注意 journal 的 gold/bench_used 是投影字段(op_journal 取 post_frame),非游戏回读**,「与游戏实扣对齐」成立于上述屏读金交叉对账(落地审已独立复算);③tracked 漏记 = crash#1 tracked 签名与买前逐字原样(椒丘@槽1 仍在/无腾槽/无阿格莱雅)vs expected 签名 = 合成后+新卡落腾出槽;④复发机制 = 商店入口播种取自 tracked 账(cw_op_buy_cards.py 播种单一源行)而非屏幕,分叉随陈旧账带入后续 visit 直至备战屏 SIFT 对账纠漂,故 05:52:05–05:52:24 间可重建同型分叉再炸;⑤崩溃截图 CwLoop_1788904320984/1788904345785 为框架缓存陈旧帧(内容早于保存时刻 ≥2 次刷新),不入证据链。

## 决策

1. **满栏合成买分支单一源化**:自 `simulate` 抽出 `_apply_full_bench_merge_buy(bench, deployed, card, shop)`(cw_state.py)——前置 = bench_place 失败语境 ∧ `merge_buy_completes` 通过(不满足 = 满栏拒买,ADR-0283 兜底语义不变,返回 None);应用 = k=`merge_buy_k` 张临时挂尾 → `_merge_bench` → 截回定长 9。simulate 与 `mutate_bench_deployed` 共用,gold 扣减/店侧 k 张下架仍归投影侧(tracked 域不管金/店)。
2. **tracked mutate 带 shop 视图**:`mutate_bench_deployed` 增可选参 `shop`(缺省 None = 旧丢件行为零漂移,无店面语境的既有调用方不受扰);生产 BuyCard 路径(BuyCardOp.execute)传 `env.state.shop`(与 simulate 同一动作前店面视图)。牌名未识别(name 空)不触发合成分支(无法判合成对象,保守维持丢件)。守卫逻辑/豁免判定零改动。
3. **ADR-0518「满栏分支生产不可达」声明证伪更正**:ADR-0518 §对抗修复批补登(及 flow/shop_visit.md 同源行)曾断言「EV 买面席位门后,满栏 §2.5 分支与双账满栏豁免在商店生产路径不可达=防御纵深」——本事故实证 m2_merge_completion 提案在满栏帧照常发射并触发 §2.5 合成分支,该不可达声明**失效**。防御纵深表述作废;席位门仍拦「无合成空间的满栏 EV 买」,但其后的 m2 合成完成买是 §2.5 分支的常态生产入口。
4. **守卫满栏豁免面收窄申报**:豁免原依据「两模型满栏语境不同构」随本批治本消失;收窄后豁免面 = **非合成满栏买被游戏拒绝而像素差漏检的 fail-open 残余窗**(两账同 no-op,对拍仍过;残余风险 = 机制知识缺口——§2.5 连升低置信项/落点低置信项——下「模型判不合成而游戏合成」帧,守卫于下一动作帧仍可捕获)。
5. **T-59 副本面兼容声明**:合成仍只按同名同星 ≥3 分组,≤2 副本同场合法态(merge_mechanics §3 推论)不受影响;事故帧 bench 即含绯英×2/花火×2,重放锁携副本对全程同构走过合成买。T-59 开放问题本身不因本批关闭。

## 后果

- 满栏合成买后两账同构(素材消费/槽位腾出/载体升星同步入 tracked),同 visit 后续动作的守卫对拍恢复「同一本账」语义,误炸根因移除;
- tracked 账自此正确镜像游戏的满栏合成事实,后续对账/重播种/卖出链消费到的是真值;
- 商店入口播种仍取自 tracked 账(既有架构,本批不改),其正确性现在由 mutate 的同构性承载;
- flow as-built 三处「两模型不同构」表述回填(action_exec.md §4/guards.md §8 降级表/shop_visit.md §2 流程图)+ shop_visit.md ADR-0518 补登行证伪标注。

## 验证

- 新锁 6(test_cw_full_bench_merge_mutate.py):事故帧重放×2(载荷=守卫 Traceback 原文+journal 金链,修复后守卫静默零告警)、变异自检(旧形态世界守卫必炸=场景有牙 + 生产≠旧形态=修复回退即红)、k=2 自动多买双账同构、非合成满栏买拒收零漂移、shop=None 兼容面;
- 外部变异:禁用合成分支 → 4 failed/2 passed(红集=两重放+变异自检+k2;绿面=两零漂移锁,符合设计),复原 6 passed;
- 受影响点名(test_cw4_shop_line/test_cw_state/test_cw_buy_outcome_gate/test_trailblazer_form)62 passed;CW 全量快速集(-m "not slow")3395 passed / 0 failed;ruff 改动文件全绿;
- 落地审:干净上下文对抗 review 全技术门放行(根因定谳确认/实现落差零/变异红集逐项吻合/归层合规/禁碰面零触碰),需修仅文档三同步(本 ADR+回填+定谳精确化吸收),报告 = `.debug/temp/currency_war/attacks/t182_dual_ledger/落地审.md`。

## 转呈(非本批辖域,交接锚点)

提案侧字段语义疑点:crash#2 journal 行 `reason=m2_merge_completion ∧ card.merge_preview=0` 并存(crash#1 同 reason 而 preview=2)——两字段异源(merge_preview = 屏幕 §2.7 合成预览星标读取,已知闪烁;m2_merge_completion = 决策器 own-count 自算理由),并存非同义冲突,但「决策器判合成而屏幕无预览」帧在满栏语境无独立旁证。信任缺口归 mandate_v1 提案侧批查(本批禁碰面已守);锚点 = op_journal.jsonl ts=2026-09-09T05:52:00 与 05:52:25 两行。
