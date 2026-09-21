# 获得链(gain-chain)迭代设计(总纲)

## 0. 元信息

- 迭代目标:制定动作 op 上报后 game state 的**链式处理规范**——「获得投资环境 / 获得角色 / 获得装备」三个链原语 + 事件回调枚举 + 升星时序 + 随机态参数纪律;并以**投资环境落地相**为首个接入面。
- 用户裁定(2026-09-21,逐条):①画面 op 只管观察选项与机械派发,「选择」发生在策略器发出动作 op、动作落地处理之后——`active_env` 点卡前写退役;②回调**不设注册表**,在回调函数体内枚举即可(收敛);③随机态 = 每个函数一个入参、递归透传,**中途触发的效果可能是随机的、可以翻转该值**(不是入口定死);④查无效果 = 安静不写;⑤「未观察」应属 bug(接管局进来在备战,观察可补全),暂按零写+留证处理,**文档留标记后续梳理**;⑥迁移面 = 本次只接投资环境。
- 状态:定稿(攻击收敛:r1 9 条处置完毕;r2 新增 R1/R2 两条机械修正已落,攻击者预授权收敛;试读过)
- 文档清单:无详设(单文档方案,本篇即完整设计)

## 1. 问题与动机

现状症状(锚 = `文件::符号`,路径根 = `src/sr_od/application/currency_war/`):

1. **选择事实的写点错位**:`operations/cw_screen/cw_screen_invest_env.py::CwScreenInvestEnv._decide_and_act` 在点卡前写 `gs.active_env`(ADR-0598 时代语义)。画面 op 的职责 = 观察选项 + 决策 + 机械派发;选择事实应产生在动作落地处理时(裁定①)。确认未落地重走时,点卡前写留下「已选环境」中间假账。
2. **没有统一的获得过程语义**:落地相效果 = 按卡名散表 `kernel/cw_action_report/pick_invest.py::PICK_INVEST_EFFECTS`(现役 2 张)+ 独立后置钩子 `kernel/cw_effect_inventory.py::apply_equip_acquire_consequence`(装备获得→送角色,「全渠道统一后置钩子」,其 docstring 自述入栏不在辖);效果函数体内手写递归,无统一时序。
3. **升星时机错、产物断链**:`cw_effect_inventory.py::grant_bench_unit_cascade` 落位后**立即**级联合成(`merge_cascade_write`,锚 :1489-1492),升星产物不再触发任何回调;备战席满 = 拒落零写(`detail='bench_full'`,锚 :1483-1484),不建模溢出席——而容器已有溢出字段(`kernel/cw_game_state.py` `overflow_warning`/`overflow_card`,§3.2.20 实机建档)、卖牌溢出腿(`kernel/cw_action_report/sell_bench.py`:溢出腿,腾出槽当帧记溢出卡入位)与 sim 渠道(`sim/cw_sim_nodes.py`「席满不丢,溢出悬挂由容器」)在册。
4. **随机态无链级规则**:`rand` 形参逐调用点各自决定(锚 `grant_bench_unit_cascade`/`apply_equip_acquire_consequence` 的 rand 形参),采样进入链后下游写通道无约束。

根因归层:**语义层**——「获得」这件事(注册 → 回调 → 升星 → 递归)没有统一的过程语义;散点是它的症状(约定层表现)。

解决到哪:三链原语 + 回调枚举 + 升星时序(回调先、升星后、产物重进)+ 溢出落位 + 随机态参数纪律 + 投资环境落地相接入。

明确不解决(防外溢):`pick_supply`/装备后果桥等旧消费点迁移(后续批,过渡期双时序并存见 §2.5);环境/策略效果全量核实建模(推广批;查无效果安静不写);策略屏(`source='strategy'`)落地相改造(本批不动);sim 引擎接线(链原语纯函数可复用,另批);接管局观察补全与「未观察」根治(另批——裁定⑤,本批只留证 + 标记)。

## 2. 方案(完整设计)

### 2.1 链原语(kernel 新模块 `kernel/cw_gain_chain.py`)

三个公开入口(均带 `rand: bool` 必带入参,纪律见 §2.4)与一个结果载体:

**`gain_invest_env(gs, session, env_name, *, rand, sig, producer='CwGainChain') -> GainOutcome`**

1. 注册:`gs.write_logic(gs.active_env, env_name, produced_by=producer, sig=sig)`(写点自画面 op 迁入;ADR-0598 退役,行为变化申报 §2.6-1)。写行署名 = **新写端新名**(`producer` 形参缺省即 `CwGainChain`,落地相接入显式传同值)——写点迁移属申报过的行为变化,不沿用旧名伪装连续;`sig` = 链入口必传入参(落地相 = 重入裁决出口现役 sig);
2. 效果账本登记:`cw_effect_inventory.register_portal_from_env(session, env_name)`(调用点自画面 op 迁入;**本腿自包 best-effort**——登记/遥测面失败 log + 缺陷台账、不阻塞;容器写腿零吞错,异常粒度全表见 §2.7);
3. 触发环境效果:`on_env_gained(...)`(§2.3)。

**`gain_character(gs, name, star, *, rand, sig, evidence, producer) -> GainOutcome`** — 固定时序:

1. **落位**:工作副本 = `gs.bench` 槽表 + 上阵行域派生表(容器原生形状,基座同现行 `grant_bench_unit_cascade` 的 `bench_place` + `deployed_rows_to_indexed`,锚 cw_effect_inventory.py:1475-1488)。
   - 备战有空槽 → `bench_place` 入槽;
   - **备战满 → 溢出落位**(裁定⑥配套):写 `overflow_warning=True` + `overflow_card=name`(两字段各一行,同 evidence 同 sig 同组)。**写端声明**:两字段由「观察写端单一源」扩为**双写端**(观察 heavy 写端 + 获得链逻辑写端)——第二逻辑写端先例 = 卖牌溢出腿已直写 overflow_card(`kernel/cw_action_report/sell_bench.py` 溢出腿:腾出槽当帧记溢出卡入位);正本面同步 = landing 正本清单(fields.md §3.2.20、容器字段注释、projection_audit basis)。星级不入容器字段(字段只有身份串,锚 cw_game_state.py:2002-2008),链内工作池自记本次授予的星级——链写入即知真值,不依赖观察兜底口径;
   - 溢出位已被占(链内连环授予第二次溢出):游戏行为未实证 → 零写 + 缺陷台账留证(`record_defect`,不停机),禁猜;
   - `gs.bench` 未观察(None)= bug 面(裁定⑤):零写 + 缺陷台账留证,不停机;**【待梳理标记】**根治归观察补全批,标记落正本 gain-chain 篇「已知缺口」节 + 代码注释。
2. **触发「获得角色」回调**:`on_character_gained(...)`(§2.3)——回调内可递归调任意链原语,递归子链的 rand 按效果自身性质传(§2.4)。
3. **回调返回后,3 合 1 升星判断**(顺序 = 用户裁定「先触发回调…回来后再触发 3 合 1 升星判断」——回调可能补齐第三只):
   - 合成池 = 备战槽 ∪ 上阵 ∪ 溢出(链内溢出单位含链记星级;观察来源的溢出卡星级缺读按 1 兜底,现行口径锚 cw_game_state.py:2004-2006);
   - 恰有同名同星 3 只 → 消耗三只、载体升星;载体选择/落点/装备继承规则逐条对齐 `kernel/cw_merge_simulate.py::merge_simulate` 不动点合并段(:206-279:含场上载体优先、全备战取最左、溢出件合成腾槽归位优先、装备继承并入、分组键 (char_id, star));
   - **升星产物 = 获得一只高一星角色 → 递归走 `gain_character`**(回调 → 升星判断 → …,裁定「升星也会触发获得角色的回调,类似之前的再继续」);无三连同名同星 → 终止。递归深度有界(星级上限)。
   - 与 merge_simulate 的关系:merge_simulate 是一次到底的不动点推演、无回调时机;链式版需要「**单级合成 + 产物回调**」——实现 = cw_gain_chain 内新增单级合并函数,规则逐条对齐 merge_simulate(禁第二套语义),并以**对拍测试**锁「同池同输入下,单级×N 次 == merge_simulate 终态」。
4. 每次容器写按 rand 走 `gs.write_logic` / `gs.write_logic_rand`(通道语义锚 cw_effect_inventory.py:1461-1464)。

**`gain_equipment(gs, item, *, rand, sig, evidence, producer) -> GainOutcome`**

1. 入栏:`gs.equips` 追加(栏未观察 = 同 bug 留证规则);
2. `on_equipment_gained(...)` 回调(§2.3)。装备无升星判断。

**`GainOutcome`**(frozen dataclass,三原语共用):`placed: bool` / `landing: str`('bench'|'overflow'|'skipped')/ `merge_levels: int` / `effects: tuple[str, ...]`(命中的效果名)/ `detail: str`——留证与测试用、零决策消费(沿 `BenchGrantResult` 先例,cw_effect_inventory.py:1442-1448)。

### 2.2 递归不变量

- 回调先于升星;升星产物重进获得角色;无三连同名同星即终止。
- 链内所有容器写共享链入口传入的 `sig`(同组遥测),evidence 加后缀区分(沿 merge on_step 编号先例 `#mergeN`,cw_effect_inventory.py:1421)。
- 链不负责腾位/卖牌(溢出善后归策略溢出面,锚 `strategies/impl/mandate_v1/mandate.py` 溢出告警门);链只如实记账。

### 2.3 回调(kernel 内枚举函数;无注册表——裁定②)

- **`on_env_gained(gs, session, env_name, *, rand, sig)`** 枚举:
  1. `ENV_GIFTS[env_name]` 命中(数据表 = `kernel/cw_investments.py`:1547-1634;值全部 = cw_invest_data 效果原文直读,import 即校验:孤儿键/角色名漂移/空发放集,锚 :1610-1634)。**先按 advisor 分道,两道互斥**——advisor 条目(特邀专家:停云/加拉赫/桑博)同样携带 `chars_immediate`,该字段在 advisor 行仅作顾问身份输入,禁再入席:
     - `advisor=False`(契约类:翡翠/砂金/欢愉契约 等,直接送卡语义,锚 cw_investments.py:229「False=直接送卡(契约,白得资产)」):`chars_immediate` 逐个 → `gain_character(char, 1★, rand=rand)`(星级未标 = 1★ 同句式先例,先验错 = 响停修因非随机,锚 pick_invest.py:98-100 现行同款注释);
     - `advisor=True`(特邀专家,顾问入商店语义,锚 cw_investments.py:227-229):**不入席**——容器无商店池字段,`chars_immediate` 身份只进遥测申报一行(先例 = pick_invest.py:133-137 hacker shop_pool decl);
  2. 条件腿标记面:欢愉契约 provisional 翻来源闩现役通道原样保留(临时测量仪表,撤场条件已在册,锚 pick_invest.py:106-109)。
- **`on_character_gained(gs, name, star, *, rand, sig)`**:初始枚举 = 空集(暂无已核实的「获得角色时」触发型效果;查无效果安静不写)。**本函数 = 该类效果未来的唯一收敛点**。
- **`on_equipment_gained(gs, item, *, rand, sig)`**:消费 `EQUIP_ACQUIRE_CONSEQUENCES` 数据表(装备获得→送出单位,锚 cw_effect_inventory.py:1525-1533)→ 命中 → `gain_character(送出单位, rand=rand)`。该表是游戏数据映射不是效果注册表,保留;分派动作住本回调。

查无效果 = 安静不写,真值归观察覆盖(裁定④)。

### 2.4 随机态参数纪律(裁定③:每函数入参、递归透传、中途可翻转)

- 三原语与三回调均带 `rand: bool` 必带入参;链入口按自身性质定初值(投资环境确认 = 确定性,False);
- 递归调用点按**该效果自身性质**传参:效果体含采样(roll/随机发放)→ 对其发起的子链传 `rand=True`;不含采样 → 原样透传;
- 语义:任一写点的 rand 值 = 「本次写是否处于随机语义」,不承诺全链一致——采样效果只翻转它自己的子链。

### 2.5 接入面改造(本批唯一接线面 = 投资环境落地相)

- `kernel/cw_action_report/pick_invest.py::report_action_pick_invest_param` 落地相 `source='portal'` 支:改调 `gain_invest_env(gs, session, canon)`(替代现役「跳过第一步 + PICK_INVEST_EFFECTS 分派」)。`report_action_pick_invest_param` 增加 `session: object | None = None` 关键字参数(portal 支消费;kernel 禁自取上下文,由调用方显式传入——调用点 = 画面 op 重入裁决出口,持 `ctx.cw_match.session`;**None = 账本登记腿跳过**[局外/测试形态],容器写照常);`strategy` 支与发射相不消费。
- `PICK_INVEST_EFFECTS` 收窄:删「欢愉契约」行(portal 卡经策略屏不可达,行 = 死键);provisional 通道随枚举迁 `on_env_gained`;「骇客专家:银狼」行保留(策略屏专用)。
- `operations/cw_screen/cw_screen_invest_env.py::CwScreenInvestEnv._decide_and_act` 尾段:**删除** active_env write_logic 块与 register_portal_from_env 块(选择事实归落地链);其余(零参决策/刷新臂/变异窗/确认 pending/派发)不动。
- 策略屏(`source='strategy'`)落地相**本批不动**(active_strategies append + PICK_INVEST_EFFECTS 现行);「获得投资策略」原语随策略屏迁移批另立。
- 过渡期申报:`grant_bench_unit_cascade`(落位即合成、无回调)仍被 pick_supply/装备后果桥消费,与本链「回调先、升星后」双时序并存至各自迁移批;效果面无重叠(pick_supply 无 on-gain 效果在册),行为等价。

### 2.6 行为变化申报(对抗审重点攻击面)

1. **active_env 写时点**:点卡前 → 落地相(裁定①,ADR-0598 退役)。改善:确认未落地重走不再留中间假账;失败的访问不再产生「已选环境」。风险面:落地相不触发(= 选择未发生)则不写——该形态本就应无账。
2. **ENV_GIFTS 全量即时发放接入**:ENV_GIFTS 收录环境(契约类 chars_immediate 8+ 条,如 翡翠/砂金/欢愉契约;特邀专家走 advisor 申报分道)此前仅欢愉契约有容器写腿,现全部经链生效——**行为扩张**;数据依据 = 实证注册表 + 构建校验(cw_investments.py:1610-1634);表外环境安静不写。
3. **席满行为**:拒落零写 → 溢出落笔(overflow_warning/card)——对齐游戏侧行为(game 侧 screens/currency_war_prep.md 告警/溢出节实机建档;sim 渠道 cw_sim_nodes.py 同口径)。
4. **升星产物触发回调**(新增;先前产物无回调)。
5. **bench 未观察**:静默拒落 → 零写 + 缺陷台账留证(裁定⑤,bug 面)。
6. **溢出字段双写端**:overflow_warning/overflow_card 由「观察写端单一源」扩为观察 + 获得链逻辑双写端(第二逻辑写端先例 = 卖牌溢出腿);fields.md §3.2.20、容器字段注释、`kernel/cw_projection_audit.py` 对账 basis 行随正本批同步(landing 正本清单已列)。
7. **动作事实边界合同修订**:`screens/op-layer.md` §2.2「chosen_* 留守画面 op、不进 report」条款在**投资环境域收窄**——active_env 选择事实经动作落地链记(裁定①);其余 chosen_*(巨星/伙伴等)维持原条款。op-layer.md 已入 landing 正本清单。

### 2.7 边界与失败安全汇总

- 未观察(bench/equips)= bug 面:零写 + `record_defect` 留证,不停机;【待梳理标记:根治归观察补全批】
- 席满且溢出位被占:零写 + 留证(游戏行为未实证,禁猜);
- 回调查无效果:安静不写;
- 异常粒度:①链原语**零吞错**——容器写腿/回调效果腿异常上抛(真异常该响);②best-effort 边界收在**非容器写的观测/登记腿内**(账本登记腿、advisor/条件腿遥测申报行:失败 log + 缺陷台账、不阻塞——语义自画面 op 现行登记面 try/except 迁入;原「pick_invest.py:186 best-effort」锚作废,该处无异常处理);③落地相调用方零额外吞错(report 函数不包整链)。

### 2.8 测试面

- 单级合成 × N 与 merge_simulate 终态对拍(同池同输入);溢出落位/归位/溢出位被占留证;
- 递归调用序桩测(落位 → 回调 → 升星 → 产物递归的顺序断言;回调补齐第三只后再合成的时序锁);
- rand 翻转传播(采样效果子链 rand=True、其余透传);
- 未观察留证;落地相 portal 接线(active_env 写时点迁移锁:点卡前无写、落地相有写);
- 欢愉契约迁移等价(现役 `test_cw_yinlang_phase32` 落地链改写);ENV_GIFTS advisor/非 advisor 分道。
