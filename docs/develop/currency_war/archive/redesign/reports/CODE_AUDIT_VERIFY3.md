# 三轮修复核实 + 架构层专项审查(VERIFY3)

> 审计者立场=假设修复有假,逐条到代码落点验证语义;攻不破的写「攻过未破」。
> 审计基线 = 当前工作区 HEAD。注意:CODE_AUDIT_FINAL_R2.md(终审)已对同一批九条修过一轮并抓出 10 条残留(P1 输入面/败局半环等),**当前代码 = 九条修复 + 终审残留修复的叠加态**——本报告按当前态核实,并逐条注明终审残留是否闭合。
> 本报告只写此文件,未改任何代码。行号以审计时工作区为准。

---

## 一、九条修复核实表

| # | 修复声明 | 判定 | 落点与证据 |
|---|---|---|---|
| ① | formed_systems 委托 engines_count(64 板面对拍恒等锁+希儿系三反例) | **真修(含终审 P2 输入面残留已闭)** | `cw3/knowledge/transition_systems.py` L94-113:函数体仅「归一名单 + 透传 `knowledge.cw_engine_facts.engines_count`」,无残余自建判据;members 名单 docstring 明示「只承载买入方向域,成型判据不读本域」。锁:`test_cw3_prep_wiring.py` L516-544(64 随机板面恒等 + 希儿+1贝/希儿+1量/量1贝1 三反例 + 量2正例 + 贝2无希儿负例)、L547-581(输入口径锁:deployed → `board_factions_of` 派生 → engines_count 全链与旧层恒等,含 flows 形态)。生产写点 `strategy_shell.py` L398-405 已改喂 `board_factions_of(_dep_objs)`(终审 P2 抓的 state.board 全集口径已收敛)。**攻过未破**:终审攻破的「同输入恒等但输入源不同」半环,现在两侧喂的是同一个派生函数,锁也升级到全链形态。 |
| ② | PREREG v3 重锁行(二轮数据作废声明) | **真修(且已续 v4)** | `PREREG_cw3_vs_legacy_AB.md` 修订表 L101(v3:口径更新重锁、判明两处系统差、二轮 A/B 数据全部作废、40 seed/侧重跑要求)+ L102(v4:输入口径收口 + 旧侧谓词差如实申报 + 种子件按序 1 提报的统计口径申报)。v4 正是终审 P2 附加项的申报落点,链条完整。 |
| ③ | 生产连败臂 on_round_end 透传 obs.streak + 局级 reset(回归锁走生产链路) | **真修(含终审 P1 败局半环残留已闭)** | 写点三件:`strategy_shell.py` L263(on_match_start 局级 reset 归 0)、L296(on_round_end ← `obs.streak` 透传,与旧层 decision_v2/strategy.py L220 同语义)、`operations/battle_loop.py` L597-602(**败局页 telemetry_only 通道也写 last_streak**:OCR 带符号直采,读不到按连败累积递减——终审 P1 抓的「写点只活在胜轮通道」已补)。生产调用链核实:battle_loop L632 胜页 → `strategy.on_round_end` → `strategies/cw3_strategy.py` L70 适配壳转发 → shell L296,链路真实。锁:`test_crisis_streak_arm_via_production_write_chain`(L663-685,经 on_round_end 生产语义注入,不再手工赋 session)+ 败局页通道锁(L797-852,-1/-2/-5 累积)。 |
| ④ | cap 截断改判 defer_bank + 资金回滚(旧锁按存在性纪律重推) | **真修(含终审 P8② 观测尾巴已闭)** | `strategy_shell.py` L470-479:`cap_cuts_batch` 时 batch_clicks=0、action 改判 `defer_bank`、`batch_reserved=0`(资金预留同步回滚,L478-479);L654-659 遥测 `batch` 字段截断帧置 0(终审 P8② 的「多扣一笔」尾巴)。锁重推:`test_level_cap_guard_stops_clicks` L635-637 断言改为 defer_bank,注释明写「旧锁『允许 buy_batch』钉的是资金不回滚的缺陷语义」——存在性纪律执行到位,非机械跟绿。缺省 `or 10`(实机 lv9 仍可点)与 sim cap=9 两半边均有锁。 |
| ⑤ | P5 数据已出(12 seed 统计:序 6 跳买 670 张,17.8% 为非当前线过渡体系成员) | **数据已出,证据锚点弱** | 数字本体出现在 `strategy_shell.py` L497-498 注释(「12 seed 实测:序 6 跳买 670 张中 17.8% 为非当前线的体系成员」)并被终审报告引用,数值与任务书一致。**但**:①未找到落盘的独立统计报告文件(redesign 目录下无 P5 专档,progress 侧也无 17.8 痕迹),复现该统计的 decisions.jsonl 来源/脚本无持久索引;②终审 P3 曾依据同批数据质疑「种子出口兑现率存疑」(配额计划时点泄漏)——该根因已修(见④同批:配额移执行确认点),但 **17.8% 的供给面数据是修前测的,修后未重测**,「种子出口实际能吃下多少」仍是估计值。按「数据已出、禁拍修法」的门算过关(修法确实走了受控出口+标定参数,未拍阈值);按证据纪律算半分。 |
| ⑥ | 危局判而未动落盘 + crisis_max_sells 入 CalibParams | **真修(含终审 P8① 三态尾巴已闭)** | `strategy_shell.py` L593-620:危局为真即写 `decisions['crisis']`(无条件,含 sells=[]),reason 三态可辨——`no_sellable_fuel_bench_protected` / `seats_freed_by_making_room`(终审 P8① 补的第三态)/ 有卖则带明细。`calibration.py` L52 `crisis_max_sells: int = 2` 入 CalibParams,消费点 L609 `junk_slots[:calib.crisis_max_sells]`。锁:L644-660(判而未动落盘)、L688-722(应急卖+连败臂)。 |
| ⑧ | normalize_char_name 中点变体归一全链 | **真修(含终审 P4 残留已闭)** | `classify.py` L62-80:变体表 `•/・/﹒/． → ·` + **半角 `.` 二级兜底**(终审 P4 抓的缺 ASCII 点已补,真点名「银狼LV.999」不受改写有注释与锁);入口全覆盖核实:decide_prep 主链(L399/410-412)、decide_prep_action 族 B 通道 L780-787(终审 P4 抓的裸 held——归一已上移到锚构造点一次完成)、classify L157/L203、formed_systems L113、line_on_board L508、种子成员判定 L525。锁:L925-929(四变体+真点名)。**攻过未破**:找「归一遗漏消费点」——anchor 构造点归一后,deploy_plan/满席门/换位序消费的均为已归一副本,未见残余裸链。 |
| ⑨ | 持久索引清理 | **半修(点名处已清,模式级残留仍在役)** | 点名的三处:transition_systems 出处已改持久索引(`docs/game/.../transition_combos.md`、`01_strategy_layer.md`——核实为 `docs/develop/currency_war/redesign/` 持久文件,非 .debug);classify L1-16 头注释无 [N],「A/B 二轮归因」引用改为「sim 全批实测」语义描述。**残留**:`[N]` 方括号会话局部编号在 cw3/strategy 子树仍是主流注释风格——`strategy_shell.py` L519 `[41]`、`classify.py` L49 `[35]`、`buy.py`(通篇 [17]/[41]/[34]/[35]/[31])、`levelup.py`、`interest_account.py`、`equipment.py`([42])、`opening.py`、`sell.py`、`streak_money.py`、`resolver.py`、`invest_mutations.py` 等约 30+ 处。这批编号的密码本在 .debug/temp 的迭代文档里,编号本身不指向任何持久文件。属**存量模式违规**而非本批修复回退——本批只承诺清点名三处,但「三轮同缝」的架构反思视角下,这就是「出处链会烂」的现役形态(终审 P7 同判)。 |

**终审(FINAL_R2)其余残留闭合核查**(非本批九条,但影响「修复真实性」总判):P2 输入源(已闭,见①)、P3 配额时点(**已闭**:计数移执行确认点 shop.py L919 / engine_p1 L1159,计划时点仅帧内预占 L548-549)、P5 种子门 liquid 口径(已闭,L519-521)、P6 空 core 线(已闭,L509-513:窗口臂要求 `bool(core)`,空 core 线只能走满编臂)、P9 种子统计申报(已闭,PREREG v4 ③)。终审十条全闭。

**总判:九条中八条真修且锁覆盖到位;⑤数据已出但证据未落独立档案且为修前测;⑨点名处清、模式级残留是存量债。**

---

## 二、字段供给合同盘点(cw3 决策面消费的全部 session/obs 输入)

盘点方法:沿 `Cw3SkeletonStrategy.decide_prep` / `decide_prep_action` / `on_round_end` / `on_match_start` 消费面逐字段回溯写点。「静默缺省」形态 = 消费点有缺省值兜底、生产链无写点或写点可能不触发、缺省语义未在合同面显式声明。

| 字段 | 消费点 | 供给方(写点) | 生产真实写入? | 静默缺省形态 |
|---|---|---|---|---|
| `session.last_streak` | 危局门 L597 | 局级 reset L263;on_round_end←obs.streak L296;battle_loop 败局页 L597-602;obs.streak 供给=结算 OCR | ✅(本轮③修复后胜负两通道齐) | **曾是最典型形态**(三轮 P3:无写点→恒 0;终审 P1:半环不喂→陈旧正值)。现状:obs.streak 读不到时败局页走「递减兜底」**近似语义**,与真值可漂移(声明于注释,未进合同面) |
| `session.cw_paid_refreshes` | R05/R09 门 L331 | reset L260;生产 shop.py L1151;sim engine_p1 L1019 | ✅ | 无(getattr 0 = 语义正确初值) |
| `session.cw_level_cap` | cap 截断 L470 | **sim 专属写点**(engine_p1 L640=9);生产无写点 | ❌ 生产靠 `or 10` 缺省 | **现役静默缺省**:有语义辩护(实机 lv10 真值),但若实机环境效果改等级帽,生产静默用错值,sim/生产不同尺——与 last_streak 同构,只是错值方向未发作 |
| `session.cw3_second_seeds_bought` | 种子配额 L515 | reset L266;执行确认点 shop.py L919 / engine_p1 L1159 | ✅ | 无(终审 P3 修复后计数跟执行走) |
| `session.plane_lengths_seen` | 轮数预估 L425 | prep_director L132-134(位面首帧);sim L719-722 | ✅(首次探测前 None) | 缺省 None → `plane_lengths` 回退**先验表**——有声明(注释+node_schedule docstring),算显式降级非静默 |
| `session.cw3_mutation_ids` / `cw3_frame` / `v3_form_*` | 壳内部+遥测 | 壳自产(每帧重推/覆写) | ✅ | 无 |
| `state.refresh_probs` | 概率真值 L329-330 | **sim 专属**(引擎每阶段重掷注入);生产无写点 | ❌ 生产 None → 基线概率表 | **现役静默缺省(挂账)**:注释 S-7 自认「生产概率条接线后同字段」——决策消费一个降级输入且无哨兵区分「没接」vs「接了但读空」 |
| `state.active_strategies`/`active_env` | 突变集 L284-287 | 实机 handler / sim 注入(双面) | ✅ | 未命中=告警+跳过(可观测) |
| `state.board`(间接) | faction_next_tier 序 2 | OCR 左面板真值(生产)/ `_board_counts_of`(sim) | ✅ | 序 2 谓词消费 board 全集口径,与 formed_systems 的窄口径**双尺并存**(各有语义,但合同面无对照声明) |
| `state.hp/gold/level/xp_progress/shop/bench/deployed` | 全机 | 生产 OCR 采集链 / sim 引擎 | ✅ | hp=None 时各机 fail-closed(危局门 L596 显式判 None) |
| `calib.*`(CalibParams) | 各门阈值 | calib_v1 标定注入 | ✅ | u_by_cost=None → decide_sell fail-closed 持有(显式声明) |
| `obs.bench_chars`/`deployed_chars`(族 B 锚) | decide_prep_action | adapter.snapshot_to_obs | ✅ | obs.state 轻骨架(无板面)为**设计内**形态,注释声明 |

**盘点结论**:12 族输入里 2 个生产无写点、靠静默缺省在役(`cw_level_cap`、`refresh_probs`),1 个近似语义兜底(败局 streak 递减),其余写点齐且多数可观测。三轮抓的缝全部落在这个表的第一列——**合同不存在,所以每条缝都要靠「决策面行为异常→倒查写点」的事后路径发现**,而回归锁又天然长在消费半环(直调策略注入最好写),供给半环无人看守。

---

## 三、架构级防线建议

三轮同缝的根,不是某个字段忘了写,而是**「决策消费的每个输入字段必须有生产写点」这条合同只存在于审计者的脑子里**,代码里既无登记处也无守卫。建议三层,按性价比排序:

1. **输入供给合同表(核心,落点 `cw3/` 一个常量模块,~1-2 天)**:把上表代码化——每个决策消费的 session/obs 字段登记四元组(生产写点符号路径、sim 写点、reset 所有者、缺省语义枚举:`REQUIRED_WRITTEN / DEFAULTED_EXPLICIT(声明理由) / DERIVED_IN_SHELL`)。`DEFAULTED_EXPLICIT` 是关键:允许缺省(如 `or 10`、概率基线)但必须登记,登记处即审查清单——下次审计/加字段时合同表就是唯一入口,不再靠倒查。
2. **守卫测试(半天)**:①合同表完备性锁——遍历 `StrategySession` 声明字段 ∪ 决策面 getattr 消费字段,断言每个都在合同表登记(防新字段裸奔);②写点存在性锁——对 REQUIRED_WRITTEN 字段,断言其登记的生产写点符号真实存在(import 级检查即可,成本极低)。更硬的「读前必写」运行期检测(缺省哨兵 MISSING + 消费侧 assert)留给字段少的现状不划算,先不上。
3. **测试规范条款(零代码,入 sr-od-test README 纪律)**:凡「生产供给」字段的回归锁,**必须至少一条经生产调用链**(battle_loop 级 harness / sim 引擎装配),禁只直调策略注入——P3(三轮)→P1(终审)两轮同缝的直接教训:直调锁绿了两次,生产链断了两次。

成本合计约 2-3 天;对照物是「口径事件→PREREG 重锁→40 seed×2 侧重跑」(v3 行就是这么发生的)与下一轮必然出现的同类审计——防线成本低于一次作废重跑。

---

## 四、结论:A/B 放行判定

**判定:需「轻量合同防线先行」,不建议裸放行;防线落地后即可进 A/B,无需再一轮全量审计。**

理由:

- **本轮九条+终审十条在当前 HEAD 全部核实闭合**,已知缝(成型判据/输入口径/连败供给双半环/cap 资金/配额时点/归一链/危局可观测/PREREG 口径链)没有一条是「表面修」——这是三轮以来修复质量最高的一批,spot-fix 循环本身在收敛(每轮抓的缝越来越窄:从「无写点」到「半环」到「观测尾巴」)。
- **但收敛的机制是「审计者每轮手工重建合同」**,不是结构防线:盘点表显示仍有 2 个生产无写点的静默缺省在役(`cw_level_cap`、`refresh_probs`)、1 个近似语义兜底(败局 streak)。这些今天不发作(sim/生产恰好都按缺省语义对齐),但它们正是 P3/P1 的同族——**只要再加一个决策输入字段,同型缝就会再次从锁缝进来**,而 A/B 出数后才发现口径缝的代价是全量作废重跑(PREREG v3 已演示过一次)。
- 因此最小放行条件 = 第三节第 1+2 条(合同表 + 守卫测试,约 2 天)+ 第 3 条测试规范;第 3 条同时应把败局 streak「递减兜底」与 `refresh_probs` 基线两条挂账显式登记进合同表的 DEFAULTED_EXPLICIT,让哨兵/判读能区分。
- 若选择不立防线直接 A/B:风险不在已修的九条,而在**下一批策略改动引入新输入字段时**——届时口径缝混入效应量的事后成本(重跑+重锁+重审)远高于现在的 2 天防线成本。按「长期最优」判据,防线先行。
