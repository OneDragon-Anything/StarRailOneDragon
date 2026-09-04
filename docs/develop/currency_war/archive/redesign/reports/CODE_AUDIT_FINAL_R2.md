# 终审(R2):ROUND3 九条修复 + P5 第二体系种子件受控出口·对抗式审计

> 审计者立场=假设代码有错,逐条设法证明;攻不破的角度单列「攻过未破」。
> 审计对象:①formed_systems 委托 engines_count(64 板面对拍锁/希儿系三反例);②PREREG v3 重锁行;③生产连败臂(on_round_end 透传 obs.streak+局级 reset);④cap 截断改判 defer_bank+资金回滚;⑤P5 数据(禁拍修法);⑥危局判而未动落盘+crisis_max_sells 入 CalibParams;⑧角色名归一全链;⑨持久索引清理;以及 P5 种子件受控出口(strategy_shell 买入预判段)。
> 知识基准:knowledge/cw_engine_facts.py(engines_count 权威)、decision_v2/phase.py(旧层兜底门)、kernel/cw_battle_calib.py(口径函数对)、PREREG_cw3_vs_legacy_AB.md v3、operations/battle_loop.py(on_round_end 生产调用链)。
> 本报告只写此文件,未改任何代码。行号以审计时工作区为准。

---

## 一、问题清单(按严重排序)

### P1(严重)生产连败臂仍是死输入:败局结算页走 telemetry_only,跳过 on_round_end——修复③只接了「写点存在」,没接「败局不写」
- 文件/位置:`operations/battle_loop.py` L469-488(L482-483「telemetry_only=True:**仅遥测零策略面**——只写一行 outcomes(source='loss_page'),跳过 on_round_end」)、L649-659(败局主通道 = 分支 1f → `_record_loss_page` → telemetry_only);写点本体 `cw3/strategy_shell.py` L286-292(`session.last_streak = obs.streak`)。
- 机制:on_round_end 只有分支 3(胜结算屏「挑战成功」)会以非 telemetry-only 调用(battle_loop L622-624);败局页的**主通道是 1f 模板门,L652-656 明证「1f 命中即点按钮翻页返回」**——恰恰是连败累积的那些轮,`session.last_streak` 不更新。带符号语义(连胜 +/连败 −,RoundOutcome.streak)意味着生产侧 last_streak 只可能收到**胜轮的正值或 0**;连败 3 局的典型危局帧读到的还是**上一次胜轮的陈旧正值**(比恒 0 更糟:方向还是反的)。`strategy_shell.py` L582 `<= -2` 恒 False——修复③宣称的「生产连败臂写入点」在主路径上依旧不通,仅 1f 模板偶然 miss 落到 3b 的偶发帧会写。
- 发作场景:hp 41-60 且连败 ≥2 的危局帧(S1 哨兵的另一半口径),生产危局门不开——与三轮审计 P3 描述的生产退化形态**同形**,只是缺口从「无写点」挪到了「写点只活在胜轮通道」。sim 侧掩盖(engine_p1 L1634 结算段直接补写 last_streak,不分胜负)。
- 回归锁 `test_crisis_streak_arm_via_production_write_chain`(test_cw3_prep_wiring.py L623-645)直接调 `strat.on_round_end(streak=-2)`——锁的是策略侧消费半环,生产调用链的「败局不喂」半环仍无锁覆盖;锁绿 ≠ 生产链通(与上一轮 P3 的锁缺陷同构,修了实现没修锁的覆盖面)。
- 判定:治本修法在 `_record_loss_page`/1f 路径把「连败供给」单独透传(哪怕零策略面的其余部分保持 telemetry-only),并补「败局轮 last_streak 更新」的生产链锁(经 battle_loop 级 harness,非直调策略)。

### P2(严重)委托只统一了函数、没统一输入:state.board(羁绊全集+装备羁绊)vs 旧层 `_board_factions_of`(factions+flows)——「同一读数源」是假命题,P2 修复只完成一半
- 文件/位置:`strategy_shell.py` L391-395(注释「阵营计数供给 = state.board(与旧层同一读数源)」+ `formed_systems(state.board, deployed_names)`)vs `decision_v2/phase.py` L108-112(旧层 `engines_count(_board_factions_of(deployed), dep_names)`);口径函数对 `kernel/cw_battle_calib.py` L302-319(`_board_factions_of` = factions+flows)vs `kernel/cw_state.py` L913-938(`_recount_board` = **factions+flows+independent+星徽/卡带装备羁绊**,经 `cw_bond_equips.unit_bond_tags`)。
- 机制:sim 侧 `engine_p1.py` L458/L1433 给 cw3 的 `st.board = _board_counts_of(st.deployed)`(= `_recount_board`,全集口径);旧层兜底门喂的是 `_board_factions_of`(窄口径)。同一 deployed 名单,只要场上有独立羁绊角色或装备羁绊贡献命中四体系阵营名(星徽/卡带按 `unit_bond_tags` 计入),两侧喂给**同一个** engines_count 的 board 字典就可以不同 → 体系数可不同。64 板面对拍锁(test_cw3_prep_wiring.py L513-541)把**同一个 board dict** 喂两侧断言恒等——它锁的是函数级委托,不锁输入口径;输入分歧恰好从锁的构造里被排除。生产侧更宽:state.board = OCR 左面板真值(全集口径,cw_state.py L10-16 自述),旧层依旧 deployed 派生。
- 附加:PREREG v3 行声明「M3/M4 的 form 口径自此 = engines_count 阵营计数口径」与「同尺可比」仍过强——旧侧 `v3_form_ok` 的实际写入点 = `decision_v2/strategy.py` L339 `form_ok(state, session, registry)`:锁定线走三件套、未锁定走 `fallback_engines_count`(**engines_count + hp_charge_stack 2★ 豁免** + `phase_fallback_min_round` 轮门,phase.py L92-117)。旧臂 M3/M4 口径并非裸 engines_count,新旧效应量仍混入谓词差(豁免/轮门/三件套)。
- 发作场景:含装备羁绊/独立羁绊的板面,镜像体系数虚高一档 → form_ok 提前为真(S0→S1 判读、M3/M4 读数)且与旧层兜底门不同值——P2 声称消灭的「同板面两侧不同体系数」在输入面残留。
- 判定:治本修法 = formed_systems 的 board 输入改为与旧层同函数派生(`_board_factions_of(deployed)`,或把「喂 engines_count 的 board 口径」钉成单一源函数双侧共用);同步把对拍锁升级为「deployed 名单 → 双侧全链(board 派生 + engines_count)恒等」,并在 PREREG 补申报旧侧谓词差。

### P3(高)种子件配额在「计划时点」入账:逐动作重决策环下,一次未执行的计划就烧光全局唯一配额
- 文件/位置:`strategy_shell.py` L501-534(买入预判循环内 `seeds_used += 1` 后 L534 无条件 `session.cw3_second_seeds_bought = seeds_used`)。
- 机制:壳的执行语义是「执行环逐动作重决策」(本文件 L641-643 自述;docstring L19「刷新发生的帧只发刷新……买入由下一决策环重判」同族)。一次 decide_prep 发出 `[SellBench, ..., BuyCard(种子), ...]` 后,执行器每应用一个动作就重跑 decide_prep;种子卡此时**仍在店里**,但配额已被上一次**计划**写进 session → seed_budget=0 → 种子从后续计划中消失。净效果:局级唯一一颗种子被「一个可能永远不执行的意图」烧掉(卖出/升级动作插入、执行层 expect 守卫拒买、刷新重排,任何一条都触发重判)。对照同文件内 `cw_paid_refreshes` 的纪律(L309-311 自述「写点 = 刷新**执行**段」)——种子计数故意选了计划时点,违背同模块自己声明的「计数跟执行走」先例。
- 发作场景:seed 帧恰有腾席卖出(种子买入正是需要腾席的场景之一,buy_intents 非空才触发 p41 卖)→ 卖动作必先于买动作执行 → 重判必发生 → 种子必被配额泄漏吞掉。**种子出口在其最需要生效的场景下大概率失效**;12 seed 统计(序 6 中 17.8% 非线体系成员)宣称的供给修复兑现率存疑。
- 回归锁缺口:test_cw3_prep_wiring.py L736-747(配额锁)单次 decide_prep 断言,无「计划→重判→计划」两连调形态;配额计数时点无锁钉死。
- 判定:治本修法 = 计数移到执行确认点(与 cw_paid_refreshes 同构),或计划入账前比对「上帧已发射未结算」的种子意图去重;补两连调回归锁。

### P4(中高)「归一全链」不成立:生产族 B 通道(decide_prep_action)零归一,种子/满编判定裸名比对,中点变体表缺半角点
- 文件/位置:`strategy_shell.py` L823-825(L823 `held = held_name_set([u.char_id ...])` **裸 char_id**)、L829(opening 用裸 held 选臂)、L836(deploy_plan(anchor, roster) — roster 是注册表规范名,anchor 板面是 OCR 裸名)、L496-497(`line_on_board`:裸 `d.char_id in line_roster`)、L510-511(种子成员判定:裸 `card.name in TRANSITION_MEMBER_UNION` / `card.name not in line_roster`);变体表 `classify.py` L63(`{'•','・','﹒','．'}`,**缺 ASCII '.'**)。
- 机制:归一只覆盖了 decide_prep 主链(L393-404 显式归一)+ classify/formed_systems 内部归一。但:
  1. **decide_prep_action 是生产实机走的族 B 通道**(L761 docstring 自述部署/换位/满席门全在此),held/opening/`classify_unit_class` 的 held 入参全裸——OCR 名带一个中点形变,opening 选不出臂/选错臂 → roster 空/错 → 部署规划、M-6 满席腾席门(fuels 判定 L879-884 的 held 同裸)整链失准。修复⑧宣称「分类/成型/held 三处口径一致」,第三处(held)在生产通道上是断的。
  2. `line_on_board` 裸比对:满编臂(种子出口前置①的右支)对形变线成员计 0 → 满编误判不成立 → 出口该开不开(fail-closed 方向,但语义错)。
  3. 种子成员判定裸名:形变名的真体系成员卡进不了出口(漏供,方向保守但与 classify 内部已归一的序 6 判定**同卡不同链**——同一张「丹恒•饮月」卡在 classify 里是序 1 线成员、在 seed 判定里是陌生名)。
  4. 变体表:OCR 对「·」的经典误识形态含半角 `.`(与「.」句点形近),表里只有全角`．`;一条 `.` 之差整链照错——归一防线在它自己声称防的那个误识族上留缝。
- 发作场景:生产实机「丹恒.饮月」(半角点)帧:decide_prep 链归一救回 → 但 decide_prep_action 通道同帧裸判 → 部署通道与主链对同一板面输出矛盾计划(主链要部署、族 B 满席门判不出燃料)。
- 判定:治本修法 = 生产侧 char_id 入口统一归一(obs→state 写入点或 anchor 构造点,而非每个消费点补丁),变体表补 `.`;补「形变名全通道」回归锁。

### P5(中)种子出口「金足」用裸金,S 是活期口径——[41] 资产形态口径在自己门口被违反
- 文件/位置:`strategy_shell.py` L500(`s_floor = line_s ... else floor_gold`)、L504(`gold_left = state.gold - batch_reserved`)、L512(`gold_left >= s_floor + card.cost`);S 的定义域 = `levelup.py` L131-140 + L15-17(「金位按裸金+活期卡退金计,gold_liquid 已含活期退金」,[41] 资产形态口径)。
- 机制:decide_levelup 判「gold_liquid < s_line」用的是 liquid(裸金+bench 1★ 全额退金);种子门比较的是 `state.gold`(裸金)减预留。bench 有活期资产时 liquid > 裸金 → 同一「金足」前置在升级机和种子门用两把尺:升级机判「钱已囤到 S、可随时花」的帧,种子门可能因裸金不足拒绝——出口系统性欠 firing,且与任务书声明的「gold_left ≥ (S 或息线)+ 种子件价」的 S 口径([41] 资产形态)不一致。floor_gold=cap×10 纯息线,裸金比息线尚可自洽;S 半边不自洽。
- 判定:改 `gold_left` 的种子门分量为 liquid 口径(或声明 S 在此降格为裸金近似的边界注)。

### P6(中)前置①「主线搜索窗口全覆盖」对空 core 线恒真:列车/DOT 线的种子出口实际只剩金门+配额
- 文件/位置:`strategy_shell.py` L414(`lw = line_windows(state, core)`)、L498-499(`main_covered = (len(lw.search) == 0 or ...)`);`windows.py` L58-90(窗口只为 core 成员生成;`transition_systems.py` L58-73:train2/dot2 `core=()`)。
- 机制:线 = 列车2/DOT2 时 core 为空 → lw.search 恒空 → `main_covered` 恒 True,「线的方向已无当下可做的事」的前提从未被检验(列车线完全可以还有未上场成员/未凑 2★ 的加法可做)。种子出口在这两条线上从第一帧起就由「金 ≥ floor+价」单门把守,仅配额 1/局兜底——与裁决语义(「主线无当下可做才准分心」)不符。回归锁 _seed_state 只造仙舟线(三人组 core),空 core 半边零覆盖。
- 判定:空 core 线的「覆盖」应改判据(如「线成员上场数 ≥ max_units」单臂,或明示空 core 线豁免前置①的裁决依据)。

### P7(低)持久索引清理(修复⑨)不彻底 + 布局守卫文档漂移
- 位置:`strategy_shell.py` L461(「审计 P4」——.debug/temp 审计报告的会话局部标识)、L388(「A/B 二轮归因」指向 .debug/temp 易失文件)、docstring L17(「p41+[31]」);`classify.py` L95-96(「A/B 二轮归因」同源);`strategy_shell.py` L5(「cw3 包依赖矩阵只准消费 data/kernel」)与 `test_cw_package_layout.py` L73(LEGAL_EDGES 实际 = `{'data','kernel','knowledge'}`)矛盾——守卫是好的,入口文档还钉着旧矩阵,下一个按文档改依赖的人会被误导。
- 判定:出处改持久索引(cw_engine_facts 符号名 / PREREG v3 行 / ADR 号),L5 文档同步矩阵。

### P8(低)危局落盘的两个观测尾巴
- 位置:`strategy_shell.py` L584-600、L620-626。
- ①`crisis=True 且 bench_vacancy>0`(p41 腾席已腾出位)时 decisions['crisis'] 照写但 `reason=''`——判读无法区分「腾席后无需应急卖」与其它;修复⑥宣称的「无可卖标注 reason」只覆盖 `vacancy<=0` 分支。
- ②cap 截断后 `decisions['levelup']['batch']` 仍显示 `lu.batch_gold`(L636)而实际预留已回滚为 0——遥测消费方按该字段推金流会多扣一笔(与 P4 修复要消灭的「预算虚紧」在遥测面同形)。
- 判定:reason 补 `seats_freed_by_making_room` 类标注;截断帧 batch 字段置 0 或加 `reserved:0`。

### P9(低)种子改判序 1 污染买入分类统计
- 位置:`strategy_shell.py` L513(`dataclasses.replace(cc, order=1, ...)`)、L649-651(decisions['buys'] 记 `order: cand.order` = 1)。
- 机制:遥测里序 1 计数被种子注入抬高;'seed' 旗标与 reason 前缀可辨,但消费方(cw_batch_stats 类聚合)若按 order 聚合不知旗标 → 序 1/序 6 分布统计失真,未来跑「序 6 中非线体系成员占比」验证(上轮 P5 的验证建议)时,基线已被种子出口改变而无痕。属可接受设计(裁决要求按序 1 提报),但**统计口径变更未在任何判读文档申报**。

---

## 二、攻过未破清单

1. **formed_systems 委托本体无残余自建判据**:函数体仅归一+透传 engines_count(transition_systems.py L94-113),members 名单只承载买入方向域,docstring 明示分工不互冒充;64 随机板面恒等锁 + 希儿系三反例(希儿+1贝/希儿+1量/量1贝1)+「贝2 无希儿」负例全数反锁。函数级委托攻不破(输入面分歧见 P2,属另一层)。
2. **危局卖与 p41 腾席同槽双卖**:`crisis` 分支要求 `bench_vacancy <= 0`,而 p41 每卖一席 vacancy +1——p41 卖了 ≥1 席则危局卖整支不进,两卖集合天然互斥;候选池虽同源(bench_slots 快照),进入条件保证不重叠。攻破未遂。
3. **配额 reset 所有者与 0 值陷阱**:on_match_start 局级 reset(strategy_shell L262)+ `max(0, quota-used)` 无负数泄漏;`getattr(...,0) or 0` 对 0/-2 语义正确(-2 真值通过)。锁 L736-747 钉住。reset 时机本身攻不破(计数时点缺陷是 P3,另一层)。
4. **cap 判定边界**:`state.level >= level_cap` 边界、缺省 `or 10`(实机 lv9 付费有效)、sim 每局装配覆写(engine_p1 L638)、`cw_level_cap` 已升 StrategySession 正式字段(缺省 None)——判定半边自洽;`decide_levelup` 的 `cap` 形参是息帽(loss_exact 用)非等级帽,无混名实义。
5. **依赖方向结构合规**:cw3→knowledge 消费边已在 LEGAL_EDGES 明文放行(test_cw_package_layout.py L68-73,含禁第二把尺的修法注),守卫扫函数级 import 不留盲区;transition_systems 内 lazy import 是防环姿态(classify 实际不反向 import,无环)。结构无违规(文档漂移见 P7)。
6. **crisis_max_sells 入 CalibParams**:L594 消费 `calib.crisis_max_sells`,缺省 2 带定义注释,标定批可触达——上轮 P6 附属项已闭合。
7. **危局卖资金/席位的环语义**:危局退金入 gold_left 后本帧刷新门可用、买入不回补——与「腾出的席与金由下一决策环重判消费」的环语义自洽(继承上轮裁决),本帧买入按保守预算判,无透支路径。

---

## 三、回归锁覆盖缺口汇总

- **P1 生产链半环**:`test_crisis_streak_arm_via_production_write_chain` 只锁策略侧消费;「败局轮(1f 通道)last_streak 必须更新」无任何 battle_loop 级锁——本轮 P1 正是从这条缝里活着进来的。
- **P2 输入口径**:对拍锁同输入恒等;「deployed → board 派生 → engines_count 全链」与旧层恒等的锁缺失;含装备羁绊/独立羁绊的板面形态零覆盖。
- **P3 配额时点**:无「计划→重判→再计划」两连调锁;配额入账时点(计划 vs 执行)无锁钉死。
- **P4 归一链**:decide_prep_action 通道、line_on_board、种子成员判定的形变名形态零覆盖;变体表对半角 `.` 的钉子缺失。
- **P6 空 core 线**:种子出口前置①在 train2/dot2 线上的行为零覆盖。

## 四、修复优先级建议(不改代码,供裁决)

1. **P1**:败局页路径单独透传连败供给(最小侵入:`_record_loss_page` 补 `session.last_streak` 更新或等效通道),补生产链锁;先于任何 A/B 出数——S1 哨兵的连败臂在生产不可信。
2. **P2**:镜像 board 输入收敛到与旧层同源函数;PREREG 补 v4 行(输入口径差 + 旧侧谓词差申报),按 §5.2 口径事件办理。
3. **P3**:种子计数移执行确认点;补两连调锁。
4. **P4**:生产 char_id 入口统一归一 + 变体表补 `.`;补形变名全通道锁。
5. **P5-P9**:种子门 liquid 口径、空 core 线覆盖判据、注释持久索引与 L5 矩阵文档同步、crisis reason/levelup.batch 观测尾巴、种子统计口径申报。
