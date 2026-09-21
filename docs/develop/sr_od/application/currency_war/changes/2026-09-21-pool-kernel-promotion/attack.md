# 2026-09-21-pool-kernel-promotion 设计对抗审查报告(核一·无前提攻击)

- 攻击对象:`design.md`(单文档方案,草案态,2026-09-21 版)
- 审查标准:`docs/develop/harness/iteration-design.md` §5 写作硬规则、§7 核一
- 审查方式:全库 grep 对账 + 源码逐点核验,无预设焦点
- 路径约定:证据路径省略前缀——src 侧 = `src/sr_od/application/currency_war/`,测试侧 = `sr-od-test/test/sr_od/application/currency_war/`

---

## 发现清单

### F1 [major] | design.md §1.1(3)/§2.2/§2.3/§2.6 | M21「全库零消费」主张不成立:测试仓消费两符号且断言的正是本批宣告矛盾的旧口径,波及文件未申报

- **发现**:设计称 `silver_wolf_effective_cost`/`SILVER_WOLF_COST_BY_STAR`「全库零消费」,所引证据只有引擎 import 面(src 侧核验属实:src 全库唯一 `cw_sim_special` 消费方 = `sim/cw_sim_engine.py:159-162`,只 import `SILVER_WOLF_ID`+`planner_overlay_due`)。但测试仓 `test_cw_sim_equips.py` import 了两个待退役符号(:50/:53),且 `test_silver_wolf_cost_by_star_and_front_gate`(:148-155)逐条断言旧口径 `{1:3,2:4,3:5}` 与「星级×上场态」语义——正是设计 §1.1 宣告与 2026-09-18 定谳矛盾、要退役的口径。直接删除符号 → 该测试文件 import 崩、整个模块收集失败。§2.6 文件面只写「sr-od-test/ 对应测试(含 sim 池现役测试文件迁移/改面)」——`test_cw_sim_equips.py` 不是 sim 池测试文件,不在申报面;§2.3 的「M21 退役锁(两符号不可 import)」与该文件现存断言直接冲突,两断言不能同时成立,设计未写明旧测试怎么处置。
- **证据**:`test_cw_sim_equips.py:49-55`(import 两符号)、`:148-155`(断言旧口径);对照 `sim/cw_sim_engine.py:159-162`;设计 §1.1「全库零消费(grep 证实:引擎只消费…)」、§2.6 文件面行。
- **修正方向**:①「零消费」主张限定为 src 侧或改为「src 零消费 + 测试仓 `test_cw_sim_equips.py` 消费」;②§2.6 文件面补 `test_cw_sim_equips.py`;③§2.3 写明该测试处置:断言旧口径的锁随口径退役(按测试纪律「先判断再改」,该测试锁的是已被定谳推翻的表现,应删或改写为 effective_cost 语义锁),并让「M21 退役锁」与之并存不矛盾。

### F2 [major] | design.md §2.4(取舍表 held 键行) | 「证伪由观察对账暴露再升」对 held 按名归并不成立:暴露通道无名,且最常见的双档共存形状不触发任何在册检测

- **发现**:该申报照搬银狼升星记账批的形态,但那边的「观察对账」有明确机制(档行 + 商店费用徽章读档对账,见 starup-accounting design.md §2.0:61、§2.3),适用于**档字段语义**。搬到**池 held 按名归并**后,双档共存(如备战 2★ 档3 + 上阵变换 1★ 档4 同时在场)的暴露链逐环核验全部落空:
  1. 容器审计面 `lv999_cost_tier` = `AUDIT_PROCESS_ONLY`(`kernel/cw_projection_audit.py:303-306`,明写无观察读端)——审计对账看不见双档;
  2. 备战/上阵观察不读费用徽章,`resolve_cost_star` 全库只在商店读牌用(`obs/cw_observation.py:1809/:2002`)——held 归桶输入无档信息;
  3. 守恒炸错不触发:双档形状 held = 3+1 = 4 ≤ 9,无负值(`sim/cw_sim_pool.py:82-86`);
  4. 升费腿「多枚留证行」只盖「触发时刻两枚 2★」形状(`kernel/cw_action_report/pick_planner.py:182-195`),不盖「2★ 留备战 + 1★ 已上场」;上阵变费腿无歧义检查(`deploy_move.py:107-110`,(银狼,3★,<5) 即变换);
  5. 唯一间接通道 = 商店徽章读数与 `effective_cost` 基准失配告警(`cw_observation.py:2003-2010`),但它只在「升费后商店仍出旧档银狼」时才响——而定谳本身说「升费后商店只出新费用档」(记录处 exclusive-loop design.md §2.0:60),最可能的证伪形状恰恰不产生商店信号。
  结论:常见证伪形状下 held 归桶错乱**静默**,采样空间按错桶算、无任何在册机制报警。「由观察对账暴露」作为风险申报形态无支撑。
- **证据**:如上逐条;申报原文 = design.md §2.4「held 键」行;被引形态出处 = starup-accounting design.md:116、:248。
- **修正方向**:二选一改申报形态——①指名暴露通道并写明覆盖边界(商店徽章告警只盖「商店出旧档」形状;sim↔实机发牌对拍盖分布级差异),说明「再升」由什么触发;②如实申报「held 桶错乱不自发暴露」,并给兜底检测(如升费腿落档行时对账「容器内银狼星级分布 vs 单档假设」的披露行,或 sim 对拍锁显式盖双档形状)。禁保留无机制支撑的「由观察对账暴露」原句。

### F3 [minor] | design.md §2.0 | import 方向笔误:「kernel→sim import 合法方向」写成了被禁止的方向

- **发现**:§2.0 写「sim 反向复用(kernel→sim import 合法方向)」。kernel→sim 恰是 §1.1(:19-20)宣告被包布局矩阵禁止的方向;合法方向是 sim→kernel。只读 §2.0 的实现者会把禁令读成许可。
- **证据**:design.md:74(§2.0)对照 :19-20(§1.1);代码侧同判:`kernel/cw_battle_calib.py:17-19`(「留 sim 桶成 decision→sim / kernel→sim 违规边…本模块(kernel 桶)零 sim 依赖」)、`kernel/cw_overlay_registry.py:21`。
- **修正方向**:改为「sim→kernel import 合法方向」。

### F4 [minor] | design.md §1.2/§1.1 | 两处依据指针失效或无出处:「§剩余池论证」节不存在;「包布局矩阵」无可定位单一源

- **发现**:①:41 引「(银狼升星记账批 §剩余池论证)」——starup-accounting design.md 无此节(节名为 §0-§2.8,逐节核过);该论证实际内容在该批 §1.2 基线事实(:51-54「3/4/5 费副本数相等 → 档移不改变池量,只变桶归属」)。②:19-20 以「包布局矩阵禁 kernel→sim 依赖」为依据但未给矩阵出处;全库检索「包布局矩阵」仅存在于本设计与两个代码头注(`cw_battle_calib.py:18`、`cw_overlay_registry.py:21`),无定义矩阵的文档。主张本身经核验为真(kernel/ 全域零 `currency_war.sim` import),但依据写法让读者无处对账。
- **证据**:starup-accounting design.md 节标题清单(:1-:254 heading);grep「包布局矩阵」全库 5 处命中(本设计 2 + 代码头注 2 + 本行);kernel/ 无 sim import(grep 证实)。
- **修正方向**:①指针改指「银狼升星记账批 §1.2 基线事实」;②「包布局矩阵」给出定义处,或改写为可核验表述(「kernel 现役零 import sim,kernel 只许依 data 等(先例:`cw_battle_calib.py` 头注)」)。

### F5 [minor] | design.md §1.4(不解决表)/§2.1 | extra_experts 现役零调用方未申报,「透传原样」缺事实依据

- **发现**:src 侧 `deal_shop` 唯一调用方(`sim/cw_sim_engine.py:528`)**不传** extra_experts;该参数全链(`cw_sim_shop.py:71` → `cw_sim_pool.py:101/:33`)现役只有测试在传(`test_cw_sim_pool.py:63`)。设计 §1.4 裁了「维持现披露,参数透传原样」,但没写「现役零调用方」——读者无从判断保留的是在用参数还是投机参数。处理口径已定,缺的是事实申报。
- **证据**:`sim/cw_sim_engine.py:528`(deal_shop 调用不带 extra_experts);grep `extra_experts` src 侧 12 处全部在定义链与 `cw_sim_shop.py:87` 内部透传;测试侧仅 `test_cw_sim_pool.py:63-64`。
- **修正方向**:§1.4 或 §2.1 补一句现役清点(零调用方;消费方 = 测试回归 + 将来效果批具名追加),让「保留」取舍有据。

### F6 [minor] | design.md §2.2 | cw_sim_special 头注改写范围只覆盖「升费口径行」,同 bullet 内「池面天然只出 3 费档/无需额外过滤器」句随本批失效未处置

- **发现**:M21 bullet(`sim/cw_sim_special.py:6-11`)含两个旧口径:星级×上场态(:9)与「池面天然只出 3 费档——无需额外过滤器,注册表现状即口径」(:9-11)。本批后池过滤器改为 `effective_cost` 单点——第二句的**理由**退役(sim 行为不变是因 sim 不写档,不是「无需过滤器」)。设计只写「升费口径行改指容器档字段」,按字面执行会留下一段与新过滤器矛盾的头注。
- **证据**:`sim/cw_sim_special.py:6-11`;design.md §2.2 头注行;本批 §2.1 过滤条件改造。
- **修正方向**:头注改写范围写全(两处都改/删,或逐句声明保留理由)。

### F7 [minor] | design.md §2.3/§2.6 | 「迁移等价对拍」对照基准未定义 + 测试迁移动作不具名,试读卡点

- **发现**:§2.0 定「不留 re-export shim」+「逐字迁入」,§2.3 要求「迁移前后同值(同输入容器)」——旧模块同批删除后,「迁移前后」对比怎么构造设计未写(双实现并存一轮?git 历史逐字 diff?还是「现役测试断言原样保留通过 = 对拍」?)。三种构造产出的验收工件不同,属留给实现者拍板的语义选择。同族:测试迁移动作只有「迁移/改面」一笔——可核事实 = `test_cw_sim_pool.py` 一个文件 7 条测试,其中 3 条(:54/:69/:89)直依赖池四函数 import 需改写、文件名含 `cw_sim_pool` 是否随 kernel 语义改名未定。
- **证据**:design.md:74-75(§2.0)、:106-113(§2.3)、:128-130(§2.6);`test_cw_sim_pool.py:28-40`(import 面)、:54/:69/:89(三条池直测)。
- **修正方向**:写明对拍构造(最省形态:现役断言面逐字保留、仅改 import 来源,通过即等价;要更强就声明 git 历史逐字核);测试动作写具名清单(改 import 的测试号、文件名处置)。

### F8 [minor] | design.md §2.1 | 模块头注「随迁」会把 changes/ 引用种进新建 kernel 模块,与「代码禁引 changes/」铁律冲突,处置未定

- **发现**:现役 `sim/cw_sim_pool.py` 头注(:1-4)把 `changes/2026-09-15-sim-redesign/design.md` 称为「设计正本」并按节引用——本就是代码引 changes/ 的形态(存量问题)。§2.1 定「模块头注……随迁」,逐字迁移 = 在**新建的** kernel 永久层模块里重新种下这个引用,违反 AGENTS.md「代码与正本文档禁引 changes/ 内容(长期引用)」。设计未写随迁时该指针怎么处置。
- **证据**:`sim/cw_sim_pool.py:1-4`;design.md:81-82(§2.1);AGENTS.md §9 双层文档流铁律。
- **修正方向**:§2.1 补一句:头注随迁时 changes/ 指针改指正本或改纯语义描述,M06/U10/U11 语义保留。

---

## 核验通过面(逐项核过、无发现)

1. **全库唯一消费方(src 侧)成立**:`cw_sim_pool` 唯一 import = `sim/cw_sim_shop.py:43`;四函数中仅 `drawable_names` 被外部消费(:87),`fixed_pool`/`held_copies`/`remaining_pool` 在 src 无外部消费(仅模块内互调 :77-78)。测试侧爆炸半径 = `test_cw_sim_pool.py` 1 文件 7 测(3 条直测池函数),量级与「迁移/改面」一笔相称(具名缺失见 F7)。
2. **M21 零消费(src 侧)成立**:`cw_sim_special` 全 src 唯一消费方 = `cw_sim_engine.py:159-162` + :463(注释),只触留守符号;`SILVER_WOLF_ID`/`planner_overlay_due`/`trailblazer_form_of` 留守后模块自洽。测试侧不成立(见 F1)。
3. **档透传形态成立**:sim 全域零 `lv999_cost_tier` 写点(grep 证实;仅有的两个写端在实机链 `kernel/cw_action_report/pick_planner.py:211`、`deploy_move.py:131`);`effective_cost` 未观察归约 3(`kernel/cw_economy.py:175-177`)→「sim 档恒 None 行为与现状一致」成立。现役无 sim↔实机共用 gs 的接管/resume 路径(sim 引擎自建 gs),「半新半旧」无发生面;将来任一方写档、池经单一读口自动跟上,形态自洽。
4. **import 无环**:cw_pool 拟 import 集 = {data.cw_chars, data.cw_shop_odds, kernel.cw_game_state, kernel.cw_economy};cw_economy 自身链(cw_chars/cw_game_state/cw_investments/cw_plane_table/cw_registry)今日已无环且零 sim 依赖;cw_pool 为新叶,不引入回边;sim→kernel 方向合法(`cw_sim_shop.py` 现役已 import 三个 kernel 模块)。方向笔误见 F3(笔误非结构问题)。
5. **M21 退役对引擎消费零波及**:`cw_sim_engine.py:159-162`(import)与 :473(`planner_overlay_due(SILVER_WOLF_ID, …)` 触发判据)均只触留守符号,删两死符号不波及。
6. **档感知单点(模块内)成立**:`remaining_pool` 按名计、桶在 `drawable_names` 查询时现分;`POOL_COPIES_PER_CARD` 的其他在役消费面 = 估值概率族(`statefn/odds.py`、`vopt.py`、`kernel/cw_line_switch.py:86-90`)已挂账(starup §2.6:229 排除行,注册表起始费语义)、「不解决」表已列;`cw_sim_opening.py:91` 只判 copies>0,档无关。在役代码无「需要档感知而不走 drawable_names」的池路径;效果批消费链(`cw_effect_inventory.py:727/:736`)现为观察收口零采样,将来按 starup §2.7:239-240 前置契约走本模块,契约与 §2.1 改造一致。
7. **依据标注逐条核**(除 F1/F4 外均实):`POOL_COPIES_PER_CARD` {1:27,2:27,3:9,4:9,5:9} = `data/cw_shop_odds.py:33` 逐值吻合;同名即同档记录处 = exclusive-loop design.md §2.0:60 逐字吻合(「容器内费用档不同时存在…同名即同档;口述·权威 2026-09-18」);`effective_cost` docstring 辖域声明 = `cw_economy.py:159`(「随机授予采样空间」);M21 旧口径矛盾定性 = starup §1.2:65-68 逐点吻合;「M22 辖」与「池升格批前置契约」上游声明 = starup §2.6:230、§2.7:239-240,本设计 §2.1 与契约一致;design.md 全部行号锚(cw_sim_pool :33/:54/:90/:100/:109/:82-86、cw_sim_shop :43、cw_sim_special :39/:45-58、cw_sim_engine :159-162/:473)逐一核实无误。
8. **landing.md**:尚未起草(README 申明「定稿后拆阶段」),本报告不攻;对抗收敛后 landing 阶段须按本报告修订后的设计派生并对照。

---

## 总结论

**需修订后收敛。**

计数:major 2(F1 测试仓消费未申报 / F2 证伪可检测性申报无支撑),minor 6(F3 方向笔误 / F4 依据指针 / F5 extra_experts 事实申报 / F6 头注改写范围 / F7 对拍基准与测试动作具名 / F8 changes/ 引用随迁)。

主体方案(搬家非重写、档感知单点、M21 src 侧退役、透传形态、import 布局、上游契约兑现)经逐项核验成立;两处 major 都是「主张与证据面不齐」而非方案结构错误,修订后本设计可到定稿门槛。
