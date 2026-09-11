# ADR-0625: 恒买腾席支(T-115)——裁定族三买臂席满转化 + 判红检测器落码

- 状态:已实施(commit 候编排者统一门;落地审由编排者另派)
- 关联:ADR-0580(T-115 规则③恒买/规则④转线裁定正本)、ADR-0569(C1 通道本体与本批签名收窄修订注)、ADR-0585(sell_gate 统一装配;腾席支 = m4_fuel 新消费位非新通道)、ADR-0611(卖出 reason/convert_reason 契约)、math_proofs P76 甲(1★ 全额退精确 0)/P78-1(同 visit 禁卖)/P78-5′(筹资豁免立项面)、ADR-0267(诚实停摆语义先例)、`sr-od-currency-war-dev` strategy-work(开关禁令/锁纪律)、方案正本 = `.debug/temp/currency_war/恒买腾席-方案v2.md`(收口复审零新症入册)与 v1 对抗审报告(阻断 A1/A2 与九点波及)

## 1. 背景与问题

席满帧上,恒买/裁定族买臂在席位门前静默弃买,与用户裁定(规则③恒买)冲突且零显影:①未锁线恒买腿 shop 席门 `break` 无键可达(真静默);②锁线支配支被帧级前件 `core_single_card_buy_eligible(locked_buy, bench_free)` 的 `bench_free>0` 维在循环外整体拦死(循环内席门为死防御);③④转线腿席门 `break` 无键可达。病灶帧 s8r8 金 95(必花域)希儿在售被拒 `core_candidate_rejected`,同帧 `stockpile_bench_full` 证席满,整轮 8 刷零买零卖。次根 = 遥测层:拒因注释 declared「核心件在售帧被拒判红」,sim/checks 全目录零消费(未落码)。

## 2. Considered Options

- **①(采纳)三腿接腾席支 + 帧门席位维下放(A1 实码级三步)**:资格门收窄为锁线态单判,席满帧入循环在帧内席门走腾席;三腿(未锁线恒买/锁线支配支/④转线)共享单 helper,复用 `fuel_sell_candidates` + `sell_exclusions(channel='m4_fuel')` 既有单一源(不扩 P78 通道闭集,m4_fuel 新消费位)。备选「helper 提到帧门前」否决:腾席会在星级/息档门可能不放行的帧先卖燃料,循环终局弃买时重演「先卖再报」不可逆净损,且须为 helper 复制判据预检;「锁线腿降档不接」否决:留半边病灶。
- **②(否决)仅落检测器不修行为**:静默违持续,检测器红即常红——判红器是回归资产,不是行为修复本身。
- **③(否决)维持现状**:直接违反 ADR-0580 规则③裁定。
- **A4 恒买金约束语义(候裁4,默认案申报)**:金不足时按「卖前金读」——金不足不卖筹(ADR-0580「硬闸只继承席/金」字面现值);双桶分键(`*_unaffordable_fundable`/`*_unaffordable_strict`)保住判读面,两桶均显影不动作;「可筹金读」扩展案属恒买帧燃料筹资,须按 P78-5′ 通道对价段显式立项另批,本批禁夹带。
- **检测器严格红域(A2 降维)**:红 = 写端位出口键完备性破坏(seen 帧零出口键),victim 席面重推整段作废——rows 载体无 MandateState 会话态(伪造空 session 令窗口段排除全空,P78-1 边界帧必假红)且无帧级 bench。

## 3. 已实施架构

- **帧门收窄(A1)**:`mandate.core_single_card_buy_eligible(locked_buy) -> bool`(`return locked_buy`);生产消费点唯一 = shop.py C1 锁线腿 elif 门;契约键 `('mandate', 'core_single_card_buy_eligible')` 核验 `ContractCtx.locked_buy_members` 与函数签名零耦合。
- **门序重排(零漂移)**:买射出 = 全门合取可交换 ⇒ 席空帧决策逐位不变。锁线腿 星级(`refund_full_star_ok`)→息档(`t5_p1_false`)→金(`check_affordable`)→席(腾席);恒买腿 金→席(星级/息档不继承,裁定「恒买」无条件);④腿 星级→金→席。
- **腾席 helper(三腿共享)**:victim 探测帧内惰性缓存(`_core_victim`,唯一 `exclude_names=` 落点,`_mm_dedup` 同集防 merge_material 事件双计);发射与 M2 缺员/m2_stockpile 两腾席位逐字段一致(`SellBench(income=_shop_sell_refund(victim), expect=victim, reason='' 仅孤儿证明标记, convert_reason='fuel_victim_protect_demoted' T3 命中时)`),卖 1 张即止,下一决策迭代原臂原判据买入。腾席增量金成本 ≡ 0(P76 甲:1★ 全档退款往返净 0),增量息损 ≡ 0(息函数单调)。
- **诚实停摆(权限模型)**:无合法 victim(义务基座/③④持有件/合成素材/带效果件/本 visit 窗口件全排除)不卖义务件凑恒买——骨架义务 M2 族 > 裁定族买;计 `*_no_fuel` 观察桶。
- **尾键收窄**:`core_numeric_fail_closed` 改 for-else——循环无 break 自然走完(星级/息档/金闸弃帧)才落;席满停摆帧(break)不落,消除「no_fuel 与 numeric_fail_closed 共火」;金闸弃帧经双桶键显影后同走完路径照落(机制面申报)。
- **卫生键(候裁1 移位案)**:②(b) dead_gold 外门三条件合取(gold/席/reward)显式拆分,`dead_gold_press_bench_full_gate` 落外门 bench_free≤0 支(结构性可达;原拟内门落点不可达 = 死键,B2)。dominance/m6 死键(`dominance_bench_wait`/`m6_bench_full`)活键化 = 候裁随批项,本批未裁未动。
- **判红检测器(A2)**:`sim/checks/ledger.check_core_ruling_seat_violation` 注册进 `_BATCH_CHECKS`;判红载体 = 轮级 `obs.cw4_counters` 增量快照(engine_p1 行装配在役);红则 = **计数式轮级回退** `Σseen > Σ出口键`(收口复审残注①钉死;多候补帧逐帧出口 ≥1 ⇒ 恒不假红);出口键闭集 = §5.6 三族 16 键(shop.py 发射位镜像,值漂移由双向锁暴露);观察桶(`*_no_fuel`/双 unaffordable)非红,批级披露 `core_ruling_seat_bucket_disclosure`(seen 开火性 × 出口键分布)进 `run_batch_level_checks`。轮级并集口径对同轮混合帧有稀释,逐帧精确配对候零行为加列 contingency(未落,申报);锁线腿/④腿逐帧严格红域候 ADR-0569 判据式与裁定辖域关系裁定(候裁2)。
- **种子过渡窗(候裁5,申报回退)**:victim 种子显影键依赖「种子件单一源(实施时直调)」——直调结论 = 生产决策位无可直调单一源(种子身份 = 引擎件 ∧ 购买时未持有,第二合取需购买史语境,`is_engine_piece` 单独作判据系语义漂移的第二源);按收口复审残注③申报回退候裁,过渡窗处于**无显影**状态(非静默,本 ADR 即申报载体);处置**已裁**(编排者 2026-09-10 裁决)= 采(b)维持待 T-126 种子排除统一落地,不改(a)实施序。
- **零开关**:结构可证直接落码无条件生效(strategy-work §3 档 1),回滚靠 git revert。零新自由参数(全部判据 = 既有单一源谓词复用或合取重排)。

## 4. 边界申报

- **m4_fuel 高频新消费位**:恒买腿每核心在售帧触发腾席探测,T-126 种子排除落地前的过渡窗内种子件被卖频率结构性上升(§4.5 加重面申报;显影键空缺见上)。
- **凑息回拉并存**:金不足帧 C1 腿双桶显影后,同帧凑息回拉臂(t1_interest,既有行为)可对同一燃料做筹资卖出——两臂判据辖域独立,不互斥不混桶。
- **锁线腿双桶近不可达**:息门先于金门(星→息→金),金不足帧 `loss_exact>0` 恒被息门截先(实测 gold=2/c=3 L=1),锁线腿 unaffordable 双桶键近不可达;帧出口完备性由尾键承载(收口复审残扫同判)。
- **dominance/②(b)/m6 燃料买维持持有**(§3.4 弱支配):席满腾席 = 卖一张燃料买一张燃料,换手净金 0、席位占用不变、代价 2 动作帧 ⇒ 收益 0 成本 ≥0。hub/泄金档 = 其他辖域不越权。
- **T-192 划界**:④腿接腾席不触 segments.py ④例外臂检测器锁;本批 sim/checks 改动仅为 ledger.py/runner.py 增量,未重组既有检查。
- **drought**:腾席卖不复位 drought(经 `_note_sell` 仅记换手对);核心买复位走既有 `shop_drought_reset_on_buy` 单一源。

## 5. 验证

- **新锁族(§10 ①-⑨)**:`sr-od-test/test/sr_od/app/currency_war/test_cw_core_seat_vacate.py`(腾席发射三腿/转化闭环/诚实停摆/P78-1 窗口边界/门序零漂移/for-else 边界/检测器自测五件/批级披露/出口键完备性扫描/双桶含 t5 截先申报锁)。
- **旧锁重推**:`test_bench_full_frame_gate_blocks` 判锁层订正(帧门席维下放后拦截面在帧内席门)+ 断言集新增 `core_locked_no_fuel == 1`,四条旧断言全保持;`test_interest_break_frame_not_fired`/`test_star2_direct_sale_not_fired` 席空走完帧尾键行为不变;`TestEmissionFace` 扩一位(9→10,实测口径;B8「现有 10」系未实测误记);`TestConsumptionSiteManifest` shop.py 5→6(helper 单 `exclude_names=` 落点登记)。
- **守卫移除验证(先红后绿)**:①检测器判红短路 ⇒ 检测器自测 2 红,还原绿;②帧门席维回插(`and bench_free > 0`)⇒ `test_bench_full_frame_gate_blocks` + 锁线腾席发射锁 2 红,还原绿。
- 文档三同步:本 ADR + ADR-0569 修订注 + 11_shop_decisions §C1/④ as-built 语义行 + INDEX。