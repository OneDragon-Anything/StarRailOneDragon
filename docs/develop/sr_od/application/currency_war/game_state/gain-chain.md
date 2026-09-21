# 获得链(gain-chain.md —— 「获得」过程的链式规范)

> 本文档所属 = game_state 设计目录,总纲见 [README](README.md)。本篇 = **获得链正本**:
> 「获得投资环境 / 获得角色 / 获得装备」三个链原语的契约(签名/时序)、事件回调枚举、
> 溢出落位规则、随机态参数纪律与失败安全规则。代码 = `kernel/cw_gain_chain.py`
> (路径根 = `src/sr_od/application/currency_war/`)。
>
> 节内引用的代码锚 = 符号名(模块/类/函数/常量),行号不书;本文不引 changes/ 任何
> 内容,自足可读。容器字段语义正本 = [fields.md](fields.md),本篇只写「获得」这一
> 动作过程的链式语义。

## 1. 本篇管什么

> 术语注(首次出现):**获得链** = 「获得一件游戏资产」这件事的统一过程语义——
> 注册/落位 → 事件回调 → 升星判断 → 升星产物递归重进获得。此前各效果函数体内
> 手写递归、各自决定升星时机与随机态口径;获得链把过程收敛为三个原语入口。

- **管**:一次「获得」内部怎么走——容器写的时序、回调触发点、升星时机、溢出落位、
  随机态如何沿链传播、失败形态怎么处置。
- **不管**:溢出善后(腾位/卖牌归策略溢出面,链只如实记账);效果数据表的内容建模
  (数据表 = 游戏数据映射,见 §3)。

## 2. 原语契约(现役四原语)

四个公开入口(kernel/cw_gain_chain.py;效果内容住 ``cw_gain_effects.py``,
拆分 = 投资两屏迁移批,详见 §8),全部带 `rand: bool` 必带入参(纪律见 §5)
与 `sig: ChannelSig`(链内所有容器写共享链入口 sig,同组遥测;evidence 加
`#place`/`#mergeN`/`#equip` 后缀区分写步)。出参统一 = `GainOutcome`(见 §2.6)。

### 2.1 获得投资环境 gain_invest_env

`gain_invest_env(gs, session, env_name, *, rand, sig, producer=GAIN_CHAIN_PRODUCER)`:

1. **注册**:`gs.active_env` 逻辑写(写端署名 = `producer`,缺省
   `GAIN_CHAIN_PRODUCER`)。选择事实产生在动作执行时(动作 op 机械链
   发出即上报,用户裁定 2026-09-21「执行即按成功处理」;原「点卡前写」
   与「落地相写」两代语义均已退役)。
2. **效果账本登记**:`cw_effect_inventory.py::register_portal_from_env(session,
   env_name)`——best-effort 腿:失败 log + 缺陷留证(`kind =
   DEFECT_PORTAL_REGISTER`)、不阻塞;`session=None` = 登记腿跳过(局外/测试形态),
   容器写照常。session 由调用方显式传入,kernel 禁自取上下文。
3. **触发环境效果**:`on_env_gained`(§3)。

直接写语义(零幂等闸):无条件注册 + 无条件触发效果——投资环境不会
第二次给相同牌(游戏事实),重复上报只可能是代码 bug,按 bug 治理
(action_ops.md §1 增补 2)。

### 2.2 获得角色 gain_character(固定时序)

`gain_character(gs, name, star, *, rand, sig, evidence, producer)`——链式过程的
主原语,固定时序四步:

1. **落位**:以 gs 现帧派生工作池(备战槽表 + 上阵行域派生表 + 溢出表)。
   - 备战有空槽 → `cw_exec_state.py::bench_place` 入槽,写 bench;
   - 备战满 → **溢出落位**(§4);
   - 溢出位已被占 / bench 未观察 → 零写 + 留证(§6)。
2. **触发「获得角色」回调** `on_character_gained`(§3)——回调可递归调任意链原语。
3. **回调返回后,单级 3 合 1 升星判断**(合成池 = 备战 ∪ 上阵 ∪ 溢出):恰有同名
   同星 3 只 → 消耗三只、载体升星(单级合成规则见 §2.5)。**回调先于升星**的理由 =
   回调可能补齐第三只;回调子链写过的域,升星判断前重建工作池再判。
4. **升星产物 = 获得一只高一星角色 → 递归重进本原语**(回调 → 升星判断 → …;无三连
   同名同星即终止,递归深度由星级/件数自然收敛)。产物已在载体位,递归帧不再落位
   (只走回调与后续升星判断)。

链不负责腾位/卖牌;席满溢出的善后归策略溢出面。

### 2.3 获得装备 gain_equipment

`gain_equipment(gs, item, *, rand, sig, evidence, producer)`:`gs.equips` 追加入栏
(栏未观察 = 同 bug 留证规则,§6)→ `on_equipment_gained` 回调(§3)。装备无升星判断。

### 2.4 获得投资策略 gain_invest_strategy

`gain_invest_strategy(gs, session, strategy_name, *, rand, sig, rng=None,
producer=GAIN_CHAIN_PRODUCER)`(策略屏迁移批新增,三段式对齐 §2.1):

0. **无效载荷拒绝(前置)**:归一后名为空/`'?'` = 零写 + 缺陷留证
   (`kind = pick_invest_invalid_payload`)——无效输入拒绝,非防重复保护;
1. **注册**:`gs.active_strategies` **按名字去重追加**(归一名已在列表 →
   跳写;持卡列表写入语义 = 数据卫生;跳写后登记/效果腿照常——零幂等
   闸,重复上报 = 代码 bug 面按 bug 治理);
2. **效果账本登记**(best-effort,`session=None` = 跳过):`cw_investments.
   STRATEGY_EFFECTS` 归一名命中 → `effects.register_strategy`(acquired_t =
   节点序快照)+ burst 桥 `apply_effect_burst_grant` + 板面重写桥
   `apply_board_rewrite`(自画面 op 三桥迁入);失败 log + 缺陷留证
   (`kind = DEFECT_STRATEGY_REGISTER`)、不阻塞;
3. **触发策略效果**:`on_strategy_gained`(§3)。

链入口 = 确定性(rand=False);效果体含采样(骇客改件)→ 对其子链翻转
rand=True(§5)。

### 2.5 单级合成 merge_step_once

`merge_step_once(bench, deployed, overflow)`——判**一次** 3 合 1、就地推进三域
工作表,返回升星产物身份 `(char_id, star+1)`;无同名同星 3 只 → None。规则逐条
对齐 `kernel/cw_merge_simulate.py::merge_simulate` 不动点合并段(分组键
`(char_id, star)`、场上载体优先、全备战取最左、溢出件合成腾槽归位优先、装备继承
并入、场上同名同星 ≤1 不变量),对齐由对拍测试锁「同池同输入下,单级 ×N 次 ==
merge_simulate 终态」——禁第二套语义。merge_simulate 是一次到底的不动点推演、无
回调时机;链式版需要「单级合成 + 产物回调」,故独立实现单级函数。

### 2.6 出参 GainOutcome

`GainOutcome`(frozen dataclass,四原语共用):`placed`(容器写主步是否发生)/
`landing`('bench' = 落备战槽 / 'overflow' = 溢出位 / 'skipped' = 未落席)/
`merge_levels`(合成级数)/ `effects`(命中的效果名元组)/ `detail`(拒落因键,
新增 `'invalid_payload'` = 无效载荷拒绝)。
留证与测试用,零决策消费。

## 3. 枚举回调(现役四枚举;枚举即收敛,无注册表)

回调 = kernel 内枚举函数,**不设注册机构**(用户裁定:函数体内枚举即收敛,新效果
核实后在函数内加分支)。查无效果 = 安静不写,真值归观察覆盖。

- **on_env_gained(gs, session, env_name, *, rand, sig)**:查 `cw_investments.py::
  ENV_GIFTS`(投资环境 → 即时发放数据表)。命中后**先按 advisor 分道,两道互斥**:
  - `advisor=False`(契约类,直接送卡):`chars_immediate` 逐个 `gain_character
    (char, 1★)`(星级未标 = 1★ 先验;确定发放 → rand 原样透传);
  - `advisor=True`(特邀专家,顾问入商店):**不入席**——容器无商店池字段,身份
    只进遥测申报一行(`kind = DEFECT_ADVISOR_DECL`);`chars_immediate` 在 advisor
    行仅作顾问身份输入。
  - 欢愉契约条件腿(头号玩家触发,标记面):bench/equips 值不变
    `write_logic_rand` 翻来源 + 留证行(`kind = JOY_PROVISIONAL_KIND`)——有界
    显式测量仪表,定谳后必须撤(残留 = 临时闩未撤的显式信号)。
- **on_character_gained(gs, name, star, *, rand, sig)**:现役枚举 = **空集**(暂无
  已核实的「获得角色时」触发型效果)。**本函数 = 该类效果未来的唯一收敛点**。
- **on_equipment_gained(gs, item, *, rand, sig)**:查 `cw_effect_inventory.py::
  EQUIP_ACQUIRE_CONSEQUENCES`(装备获得 → 送出单位;该表是游戏数据映射不是效果
  注册表)→ 命中 → `gain_character`(表值星级;确定发放 → rand 原样透传)。
- **on_strategy_gained(gs, strategy_name, *, rand, sig, rng=None)**(策略屏迁移批
  新增):查 ``cw_gain_effects.py::PICK_INVEST_EFFECTS``(策略卡获得效果注册表,
  键 = 注册表规范名;现役单行「骇客专家:银狼」)→ 命中 → 效果体执行(链序 =
  狼腿 `gain_character` + 商店池遥测申报行 + 改件 `gain_equipment(rand=True)`
  采样入栏,改件后果经 `on_equipment_gained` 回调);未收录卡安静不写。

## 4. 溢出落位规则(双写端)

备战席满时新获得角色无处落 → 溢出落位,写 `overflow_warning=True` +
`overflow_card=name`(两字段各一行,同 evidence 同 sig 同组):

- **双写端声明**:两字段由「观察写端单一源」扩为**双写端**——观察 heavy 写端
  (备战溢出观察)+ 获得链逻辑写端(席满溢出落位直写);第二逻辑写端先例 = 卖牌
  溢出腿(`kernel/cw_action_report/sell_bench.py`)。与容器字段注释、
  `kernel/cw_projection_audit.py` 对账 basis 行一致,字段语义正本 = fields.md
  §3.2.21。
- **星级链记**:星级不入容器字段(overflow_card 只存身份串);链内工作池自记本次
  授予的星级(升星判断用链记真值)——写入即知真值,不依赖观察兜底口径。观察来源
  的溢出卡星级缺读按 1 兜底(现行口径,fields.md §3.2.21)。
- **溢出位被占**(链内连环授予第二次溢出):游戏行为未实证 → 零写 + 缺陷台账留证
  (`kind = DEFECT_OVERFLOW_TAKEN`),禁猜。
- 溢出件被合成消费/腾槽归位 → 溢出位腾空,两字段成对清写(False + '')。

## 5. 随机态参数纪律

四原语与四回调均带 `rand: bool` 必带入参,逐函数入参、递归透传:

- 链入口按自身性质定初值(投资环境/投资策略确认 = 确定性入口,False);
- 递归调用点按**该效果自身性质**传参:效果体含采样 → 对其发起的子链传 `rand=True`;
  不含采样 → 原样透传;
- 语义:任一写点的 rand 值 = 「本次写是否处于随机语义」,不承诺全链一致——采样效果
  只翻转它自己的子链。写通道:rand=True 走 `write_logic_rand`、False 走
  `write_logic`(通道语义正本 = fields.md §2.1/§2.5)。

## 6. 失败安全四则

1. **链原语零吞错**:容器写腿/回调效果腿异常上抛(真异常该响);调用方(动作上报
   函数)不包整链、零额外吞错。
2. **未观察 = bug 面,零写留证**:bench/equips 未观察(None)时零写 + 缺陷台账留证
   (`kind = DEFECT_BENCH_UNOBSERVED` / `DEFECT_EQUIPS_UNOBSERVED`),不停机。
   【待梳理标记:接管局进来在备战,观察可补全;根治归观察补全批】
3. **查无效果安静不写**(§3):真值归观察覆盖。
4. **席满且溢出位被占 = 零写留证**(§4;游戏行为未实证,禁猜)。

best-effort 边界只收在**非容器写的观测/登记腿**内(§2.1/§2.4 登记腿、§3 advisor 申报
行/条件腿标记面):失败 log + 缺陷留证、不阻塞。无效载荷拒绝(§2.4-0)同属
零写 + 留证(输入校验,非防重复保护)。

## 7. 与旧机制的关系(grant_bench_unit_cascade 过渡期)

`cw_effect_inventory.py::grant_bench_unit_cascade`(落位后**立即**级联合成
`merge_cascade_write`、升星产物不触发回调、备战满拒落零写)仍在役,消费点 =
pick_supply 等旧通道(策略屏效果腿已随投资两屏迁移批改走链原语,消费点撤出)。
它与本链「回调先、升星后」**双时序并存**至各自迁移批;现役消费面无 on-gain 效果
在册,行为等价。各消费点迁移完成后 grant_bench_unit_cascade 退役。装备获得→送
角色的「全渠道统一后置钩子」`apply_equip_acquire_consequence` 的分派动作已归
`on_equipment_gained` 回调(§3),数据表共用。

## 8. 接入面现状(双支;含模块拆分)

- **投资环境落地相**:`kernel/cw_action_report/pick_invest_env.py::
  report_action_pick_invest_env_param` → `gain_invest_env`(rand=False;
  session 形参显式传入,动作 op 自 ctx 取)。
- **投资策略落地相**(策略屏迁移批新增):`kernel/cw_action_report/
  pick_invest_strategy.py::report_action_pick_invest_strategy_param` →
  `gain_invest_strategy`(无效载荷拒绝/按名字去重追加/登记腿/`on_strategy_
  gained`)。
- **上报时点**(用户裁定 2026-09-21,action_ops.md §1 增补 2):两支均 =
  动作 op 机械链(点选中 → 点确认)发出后**立即**上报——零分步、零证据
  等待;确认未生效 = 代码 bug(点击链可靠性治理)。
- **模块拆分**:链过程语义(原语/合成/枚举回调骨架)住 `kernel/cw_gain_chain.py`;
  效果内容(`PICK_INVEST_EFFECTS` + 骇客采样池 + 效果体)住 `kernel/
  cw_gain_effects.py`(链模块级查表,效果体函数内惰性 import 链原语破环;
  拆分详设 = changes/2026-09-21-invest-landing-chain/details/
  gain-chain-file-split.md)。
