# 获得链(gain-chain.md —— 「获得」过程的链式规范)

> 本文档所属 = game_state 设计目录,总纲见 [README](README.md)(术语与图例:保留词与数字来源标注四形态【注】【推】【拟】【拍】见 [README](README.md) §6 术语表;对账 = 推算状态与下一帧实读逐项比对,对不上即 bug;帧 = 一次拍画面+做决策的时点,帧代次 = 帧的版本标记)。本篇 = **获得链权威版本**:
> 七个链原语(获得投资环境 / 获得角色 / 获得装备 / 获得投资策略 / 获得占席道具 /
> 定时道具到点发放 / 倒计时件到点开盒)的契约(签名/时序)、事件回调枚举、
> 溢出落位规则、随机态参数纪律与失败安全规则。代码 = `kernel/cw_gain_chain.py`
> (路径根 = `src/sr_od/application/currency_war/`)。
>
> 节内引用的代码锚 = 符号名(模块/类/函数/常量),行号不书;本文不引 changes/ 任何
> 内容,自足可读。容器字段语义权威版本 = [fields.md](fields.md),本篇只写「获得」这一
> 动作过程的链式语义。

## 1. 本篇管什么

> 术语注(首次出现):**获得链** = 「获得一件游戏资产」这件事的统一过程语义——
> 注册/落位 → 事件回调 → 升星判断 → 升星产物递归重进获得。此前各效果函数体内
> 手写递归、各自决定升星时机与随机态口径;获得链把过程收敛为统一的原语入口
> (在用七原语见 §2)。

- **管**:一次「获得」内部怎么走——容器写的时序、回调触发点、升星时机、溢出落位、
  随机态如何沿链传播、失败形态怎么处置。
- **不管**:溢出善后(腾位/卖牌归策略溢出面,链只如实记账);效果数据表的内容建模
  (数据表 = 游戏数据映射,见 §3)。

## 2. 原语契约(在用七原语)

七个公开入口(kernel/cw_gain_chain.py;效果内容住 ``cw_gain_effects.py``,
拆分 = 投资两屏迁移批,详见 §8),全部带 `rand: bool` 必带入参(纪律见 §5)
与 `sig: ChannelSig`(链内所有容器写共享链入口 sig,同组遥测;evidence 加
`#place`/`#mergeN`/`#equip` 后缀区分写步)。出参:四个获得原语统一 =
`GainOutcome`(见 §2.6);到点发放/到点开盒原语 = 效果串元组(见 §2.7/§2.9);
占席道具发放原语 = 落位成败布尔(见 §2.8)。

### 2.1 获得投资环境 gain_invest_env

`gain_invest_env(gs, session, env_name, *, rand, sig, rng=None,
producer=GAIN_CHAIN_PRODUCER)`(`rng` = 环境随机支采样注入,透传
`on_env_gained`,缺省回退在该函数体内;与 `gain_invest_strategy` 的
`rng` 形参同构):

0. **无效载荷拒绝(前置)**:归一后名为空/`'?'` = 零写 + 缺陷保留证据
   (`kind = pick_invest_invalid_payload`)——无效输入拒绝,非防重复保护;
1. **注册**:`gs.active_env` 逻辑写(写入方署名 = `producer`,缺省
   `GAIN_CHAIN_PRODUCER`)。选择事实产生在动作执行时(动作 op 机械链
   发出即上报,用户裁定 2026-09-21「执行即按成功处理」;原「点卡前写」
   与「落地补写」两代语义均已停用)。
2. **效果账本登记**:`cw_effect_inventory.py::register_portal_from_env(session,
   env_name)`——best-effort 分支:失败 log + 缺陷保留证据(`kind =
   DEFECT_PORTAL_REGISTER`)、不阻塞;`session=None` = 登记分支跳过(局外/测试形态),
   容器写照常。session 由调用方显式传入,kernel 禁自取上下文。
3. **触发环境效果**:`on_env_gained`(§3)。

直接写语义(零幂等闸):**有效载荷**无条件注册 + 无条件触发效果
(无效载荷拒绝见步 0,输入校验非防重复保护)——投资环境不会第二次
给相同牌(游戏事实),重复上报只可能是代码 bug,按 bug 治理
(action_ops.md §1 增补 2)。

### 2.2 获得角色 gain_character(固定时序)

`gain_character(gs, name, star, *, rand, sig, evidence, producer)`——链式过程的
主原语,固定时序四步:

1. **落位**:以 gs 现帧派生工作池(备战槽表 + 上阵行域派生表 + 溢出表)。
   - 备战有空槽 → `cw_exec_state.py::bench_place` 入槽,写 bench;
   - 备战满 → **溢出落位**(§4);
   - 溢出位已被占 → 零写 + 保留证据(§4);bench 未观察(直构/sim 域)→ 拒落零写(§6)。
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
(栏未观察[直构/sim 域] = 拒落零写,§6)→ `on_equipment_gained` 回调(§3)。装备无升星判断。

**装备获得转换拦截**(自由市场批,登记表 =
`cw_investments.STRATEGY_EQUIP_GAIN_CONVERSIONS`,键 = 卡规范名,值 =
(源装备类别, 目标名)):原语**顶段**守卫(在栏未观察早退之前,直构域持卡
也转换)——持登记卡 ∧ item 属登记源类别 → 装备**不入栏**、**不触发**
`on_equipment_gained` 后果分派,转发 `gain_bench_item` 发放目标(转换 =
确定事件,rand=False 零 rng;目标域判别 `BENCH_ITEM_NAMES` 分道,现役唯一
= 占席道具分支〔简易武装箱〕,装备目标分支留转换族批),出参 = 合成
`GainOutcome(placed=箱落位结果, landing='skipped', detail='converted:<卡名>')`
(调用方零改)。转换辖域 = 一切经本原语的获得事件字面全域(含持卡自身
卡腿的随机简易采样与开箱链所得——「将要获得」无获路枚举,T-102-attack
F1 教训同源;箱→简易→转换→箱单层终止:转发落位路径不再进入本原语);
live 零写观察覆盖(实机转换由游戏自算,双容器观察自然对账);转发写
evidence 前缀 `equip_gain_converted:`(后缀保留原获得事件串留证)。

### 2.4 获得投资策略 gain_invest_strategy

`gain_invest_strategy(gs, session, strategy_name, *, rand, sig, rng=None,
producer=GAIN_CHAIN_PRODUCER)`(策略屏迁移批新增,三段式对齐 §2.1):

0. **无效载荷拒绝(前置)**:归一后名为空/`'?'` = 零写 + 缺陷保留证据
   (`kind = pick_invest_invalid_payload`)——无效输入拒绝,非防重复保护;
1. **注册**:`gs.active_strategies` **按名字去重追加**(归一名已在列表 →
   跳写;持卡列表写入语义 = 数据卫生;跳写后登记/效果分支照常——零幂等
   闸,重复上报 = 代码 bug 面按 bug 治理);
2. **效果账本登记**(best-effort,`session=None` = 跳过):`cw_investments.
   STRATEGY_EFFECTS` 归一名命中 → `effects.register_strategy`(acquired_key =
   节点序位快照)+ burst 桥 `apply_effect_burst_grant` + 板面重写桥
   `apply_board_rewrite`(自画面 op 三桥迁入);失败 log + 缺陷保留证据
   (`kind = DEFECT_STRATEGY_REGISTER`)、不阻塞;
3. **触发策略效果**:`on_strategy_gained`(§3)。

链入口 = 确定性(rand=False);效果体含采样(骇客改件)→ 对其子链翻转
rand=True(§5)。

### 2.5 单级合成 merge_step_once

`merge_step_once(bench, deployed, overflow)`——判**一次** 3 合 1、就地推进三域
工作表,返回升星产物身份 `(char_id, star+1)`;无同名同星 3 只 → None。规则逐条
对齐 `kernel/cw_merge_simulate.py::merge_simulate` 不动点合并段(分组键
`(char_id, star)`、场上载体优先、全备战取最左、溢出件合成腾槽归位优先、装备继承
并入、场上同名同星 ≤1 不变量),对齐由比对测试「同池同输入下,单级 ×N 次 ==
merge_simulate 终态」——禁第二套语义。merge_simulate 是一次到底的不动点推演、无
回调时机;链式版需要「单级合成 + 产物回调」,故独立实现单级函数。

### 2.6 出参 GainOutcome

`GainOutcome`(frozen dataclass,四原语共用):`placed`(容器写主步是否发生)/
`landing`('bench' = 落备战槽 / 'overflow' = 溢出位 / 'skipped' = 未落席)/
`merge_levels`(合成级数)/ `effects`(命中的效果名元组)/ `detail`(拒落因键,
新增 `'invalid_payload'` = 无效载荷拒绝)。
保留证据与测试用,零决策消费。

### 2.7 定时道具到点发放 discharge_due_item_grants

`discharge_due_item_grants(gs, *, plane: int, round_num: int, rand: bool,
sig: ChannelSig) -> tuple[str, ...]`——环境定时道具通道(§3 道具通道定时支)的
到点发放原语:读 `pending_item_grants` 现值,按 (plane, round_num) 分割命中/
保留;命中项逐个 `_place_bench_item` 落位(备战空槽 → 席满溢出落位 → 溢出位被占
零写保留证据,复用即时通道同款道具落位语义);命中非空才一次 write 回写保留队列。
返回效果串 = 每命中项 `item_gift:<名>`(与落位成败解耦,与即时通道同阶)。

- **接入点**:sim `SimBackend._begin_node_window` 内、位面开局环境金
  `_apply_env_plane_gold` 之后——「第 N 位面开始时」类发放落在该位面 1 号节点窗
  打开时点(位面过渡屏被点掉、节点窗真正打开;位面过渡点空白与直进节点共用本
  收尾时点),与 `gold_per_plane_start` 同窗;sig 组名沿 `sim:env`。
- **幂等边界(双保险)**:①生产接入点在 sim 窗口幂等守卫内(`_window_begun_pos`
  对同一节点只放行一次,位面过渡点击重放不双发);②队列本身天然幂等——命中项
  发放即出队,重放调用查无命中、零写零效果。原语自身无幂等闸:生产接入点无重入面,
  未来实机接入点接线时按其重入面另评。
- **rand 语义**:环境发放 = 确定发放,调用方传 `rand=False`(§5;写通道仍统一走
  通道选择入口单口)。
- **零吞错与次序**:落位异常上抛(§6),队列回写收尾——先逐项落位、后回写发放后
  的保留队列,异常时队列不丢账。
- **实机局不接本原语**:队列登记后保持原样,备战真值由观察覆盖
  (fields.md §3.2.24)。

### 2.8 获得占席道具 gain_bench_item

`gain_bench_item(gs, item, *, rand, sig, evidence, producer=GAIN_CHAIN_PRODUCER)`
(占席道具公开发放口,命名沿 gain_character/gain_equipment 系):实现 = 模块
私有落位原语 `_place_bench_item` 加 `producer` 形参后的公开薄包装,落位语义
全部复用——备战空槽落**带名槽件**
`BenchSlot(kind=BENCH_ITEM_KINDS[item], item=item)`(名字→类别映射桥
`cw_investments.BENCH_ITEM_KINDS` 单一源,直查非 .get;映射外道具名
KeyError 响亮;2026-10-24 批起)→ 席满溢出落位(§4,
道具与角色同款)→ 溢出位被占零写 + 保留证据(§6);bench 未观察 = 拒落零写
(§2.2 同款档)。返回落位成败布尔(备战槽或溢出位均算落位)。
`rand=False` = 确定发放(策略箱授予/环境发放同约定,§5)。

消费面:效果域效果体经本口发放占席道具(§3 on_strategy_gained 箱授予分支三卡),
链内其余道具落位调用点(on_env_gained 即时道具通道 / §2.7 到点发放)走
`_place_bench_item` 同一语义核心。公开动机 = 策略发放面补「占席道具」形态:
效果体与链模块双向破环约束下(§8 模块拆分),效果体此前无占席道具发放口——
骇客卡的 bench 分支走 `gain_character`(角色),道具分支无对应入口,公开薄包装即
最小口;`producer` 缺省 = 链缺省署名,既有调用点不传即行为不变。

### 2.9 倒计时件到点开盒 discharge_due_item_opens

`discharge_due_item_opens(gs, *, rand: bool, sig: ChannelSig) -> tuple[str, ...]`
——环境延迟开盒通道(§3 on_env_gained 延迟道具支线)的到点开盒原语,与 §2.7
同区并列:读 `pending_item_opens` 现值(fields.md §3.2.25),生效序位 ≥ 解锁位
(元组字典序,到了及以后都算)的条目为命中并弹除,其余保留;命中非空才一次
write 回写保留队列。返回效果串 = 每命中项 `item_opened:<名>`。

- **零消耗分支**:件 = 棋盘右上战利品区浮动件非占席(实机板件实证 = 与晶矿球
  同区),无席位槽可消耗——开盒 = 队列弹除,零 `_place_bench_item` 调用、零
  bench/overflow/equips 写;开出的奖励若落席由现役观察自然捕捉。
- **开盒零产出写入**:开盒内容卡面 desc 无载,放弃建模(invest_effects.md
  硬裁定:desc 未写明的不主动实机查)——开盒 = 板件从战利品区消失(游戏侧
  事实),模型侧零发放;真值建立后 = 本原语加发放分支,零迁移。
- **接入点**:与 §2.7 同窗相邻——sim 进节点收尾、`discharge_due_item_grants`
  调用之后一行,同一收口继承窗口幂等守卫(窗口重放不双发;队列命中即出队,
  重放查无命中天然幂等同款);sig 组名沿 `sim:env`。
- **rand 语义**:开盒 = 确定事件(非采样),调用方传 `rand=False`(§5);写
  通道走通道选择入口单口;生效序位缺读(effective_node_pos None)→ 零写,
  命中集空 → 零写。
- **实机局不接本原语**(不对称申报,fields.md §3.2.25):实机开盒由游戏自己
  执行,队列条目到点后滞留不弹(纯知识域,现役无消费者);完胜回退分支双端跑
  不受此限——回退是模型知识修正非游戏动作(`check_env_item_open_perfect`,
  settle_confirm 分支挂点)。

### 2.10 策略卡条件发放检查腿 check_strategy_conditional_grants(tick 位)

`check_strategy_conditional_grants(gs) -> None`——策略卡「首次达成世界条件后
发放具名装备」通道(首例规模效应 id 101301,登记表 =
`cw_investments.STRATEGY_CONDITIONAL_GRANTS`,白名单制)的唯一检查本体,与
发放原语同模块内聚。遍历持卡(`active_strategies` 容器直读)∩ 登记表,跳过
已闩(`strategy_conditional_done`);条件 = 角色池(备战 ∪ 上阵 ∪ 溢出,与
gain_character 升星判断同池)内**最大同名单位数** ≥ 阈值 → `gain_equipment`
具名发放(`rand=False`,达标即确定事件)→ 发放成功(placed)才落闩。

- **挂点 = 节点边界 tick 内联腿**(advanced 位闸,唯一调用点 =
  `cw_game_state._tick_strategy_conditional_grants`,函数级惰性 import 反向
  取本函数——本模块模块级依赖 cw_game_state,反向模块级即环):选 tick 位
  的理由 = 获路全集不可枚举(买入双端不经 gain_character、补给走
  grant_bench_unit_cascade、选卡真值归观察覆盖),获得事件侧任何钩子必然漏;
  tick 单钩对容器现值求值,零枚举覆盖买入/补给/选卡/环境赠/开局初始阵容
  全获路。同节点重放 advanced=False 零重复检查(与效果账本 advance_node
  同闸)。
- **计数口径 = 单位数**:升星产物计 1(2星 = 1个角色,「8个一样的角色」
  量词「个」直修饰角色单位);3 合 1 升星使同名计数回落(3→1),闩前回落由
  后续 tick 按现值重估。时延语义 = 达标 tick 即发放(≤ 当前节点窗);「首次」
  = 首个计数达阈的 tick,闩后不再查——卖出/合成回落不回滚已发放。
- **拒落不闩自愈**:`equips` 未观察(None)= fail-closed 零写零闩,池现值
  维持达标时后续 tick 重试;bench 未观察(直构域)= 池不可评估整腿跳过,
  同自愈面;池永久回落阈下则不发放(tick 时点达标才发,边界非缺陷)。
- **写约定**:sig = `_bridge_sig(gs)`(tick 位既有写约定),evidence =
  `strategy_conditional_grant:<卡名>`(gain_equipment 追加 `#equip` 后缀;
  发放与封账同 evidence 同 sig 同组),producer = `strategy_conditional_grant`
  (家族单一标识,cw_env_grants._PRODUCER 同款);封账 = write_logic 直写
  (登记事实非随机态面,env_grants_done 同款)。

### 2.11 策略卡战后发放检查腿 check_strategy_battle_grants(结算位)

`check_strategy_battle_grants(gs, node_kind, sig) -> tuple[tuple[str, str], ...]`
——策略卡「遭遇节点战斗结算后发放占席道具」通道(首例以战养战 id 101501,
登记表 = `cw_investments.STRATEGY_ENCOUNTER_BATTLE_GRANTS`,白名单制)的
唯一检查本体,与发放原语同模块内聚(同域先例 = §2.10 条件腿)。逐持卡
(`active_strategies` 容器直读)∩ 登记表,逐道具 `gain_bench_item` 确定发放
(`rand=False`),返回实际发放的 (卡名, 道具名) 序列(登记表值一致性的
断言面;生产调用零回调面返回值忽略)。本节为策略卡战后触发族的共用节,
同族后继按「登记行直用本通道或各建各表」接入后在此扩员,禁另立平行节。

- **挂点 = sim 结算腿**(现役唯一调用点 = `cw_sim_backend._resolve_battle`,
  既有环境触发腿同段:dot 检查后、败局待办登记前——胜败两态共同路径,
  卡文无「胜利」限定 = 败局存活也发;死亡局在 `_game_over` 提前 return
  处已出局不发放。幂等零新增守卫 = `_settled_key` 节点键,同节点战斗重放
  整段跳过);**live 零写观察覆盖**(箱落备战席有画面真值可读,开箱链来源
  无关,与军火贸易箱腿 live 口径同型;判读面缺口 = live 遥测无该箱归因行,
  与特战资金金腿 live 零写的判读缺口同性质)。
- **无 done 闩(可重复)**:卡文无「首次」限定 = 每次遭遇节点战斗后都发,
  与 §2.10「首次」闩语义通道分立;防重归调用方节点键守卫,本函数零二次
  守卫。
- **写约定**:sig 由调用方传入(sim = `logic_sig('sim:strategy')`,logic
  渠道新组);evidence = `strategy_post_battle#<卡名>`(落席写 `#place`
  后缀),producer = `strategy_battle_grant`(家族单一标识,§2.10 同款);
  落位三态(备战空槽落位/席满溢出落位/溢出位被占零写留证)与 bench 未
  观察拒落(宁缺勿造)全为 `gain_bench_item` 原语内建语义(§2.8),本
  函数零二次判读。

### 2.12 策略卡到级发放检查腿 check_strategy_level_grants(sim advance 位)

`check_strategy_level_grants(gs) -> tuple[str, int] | None`——策略卡
「到达指定等级时提供金币」通道(首例成长基金 id 101701,数据单一源 =
`cw_investments.STRATEGY_ECONOMY` 级数配对字段 `gold_at_level`/
`gold_at_level_target`,registry 驱动非专表,新到级卡登记行即自动覆盖)
的**纯决策本体**:零写零 rng,返回待发放 `(规范卡名, 金额)` 或 None,
两笔写(金 + done 闩)归调用方按所在端通道纪律执行。短路矩阵六序:
①持卡 ∩ 到级条目(`gold_at_level_target>0`)空(未持卡/表外卡同路)
→ None;②已闩(`strategy_conditional_done`)→ None;③level 现值
None → 宁缺勿造;④gold 现值 None → 宁缺勿造**不封账**(本函数零写,
值到位后下次检查自动重查发放);⑤现值级 < 目标级 → None;⑥达标 →
返回 (卡名, 金额)。

- **触发语义 = 状态检查型**:持卡 ∧ 级达标 ∧ 未闩即发,「拿卡时已 ≥
  目标级」同发——等级 = 容器现值非事件流,拿卡时点无从回溯历史跨越
  (§2.10「容器现值求值」同款先例);语义假设经 sim 披露键
  `strategy_level_grant_state_semantics` 申报,实机证伪面 = 拿卡已达标
  局的金变观察。
- **挂点 = sim advance 双点**(`_on_node_advance` 推进点与
  `_on_node_advance_terminal` 局终点,各一段内联接线,挂节点经验入账拍
  之后——跨级事件发生点在 advance 不在节点窗内;局终点发放先于局终
  声明):双点为经验源扩网后前瞻一致,现世界不可达下与单点行为全等,
  裁单点则「局终跨级」一次性缺口永久缺失;**live 零接线**(金面禁直写,
  实机发放由游戏自己执行,金整字段观察覆盖兜底,与特战资金金腿 live
  口径同型;判读缺口 = live 遥测无该 +40 归因行,同性质缺口在册)。
- **双通道分工**:金 = observe 独立笔(evidence
  `strategy:level_gold:<卡名>`,sim 写统一前缀;sim 金写全 observe 现役
  形态,金面禁直写辖效果账本到期接入点,本笔 = 世界合成非 logic 直写),
  闩 = write_logic 直写 done 域(非金 Field 登记事实直写,
  `discharge_due_item_grants` 先形),两笔异通道相邻同步执行(单线程无
  并发观察者);sig 组 = `sim:strategy`(在役组,战后发放腿首落),
  producer = `strategy_level_grant`(家族单一标识,公开常量——写端在
  sim 接线段,跨模块引用署名)。幂等 = 决策函数 done 闩短路 + 调用方
  节点序位守卫双保险(等级 sim 内单调不减,达标态持续为真靠闩封账非靠
  跨越检测)。
- **休眠正确路径(现役边界)**:现役 sim 经验写源(节点经验表 × 选卡
  即时腿 `apply_strategy_pick_xp`)下全程等级上界 96(节点 70 + 即时
  26)< 3→9 级累计门槛 194(`XP_TO_NEXT_LEVEL` 求和),全程封顶 7 级
  → 本腿恒短路矩阵⑤序零写,条件真时行为正确(机制完整非占位);经验
  源扩网(买经验建模/经验常量修订)零改激活,上界 ≥ 194 时休眠边界锁
  先红触发重申报,披露键 `strategy_level_grant_dormant_in_sim` 申报。
  局终同拍多卡双就绪边角:单笔返回契约会漏第二笔,现世界不可达,多卡
  同型批落地时改列表返回或调用方循环并申报。

### 2.13 策略卡胜利结算条件金检查腿 check_strategy_win_gold_grants(结算位)

`check_strategy_win_gold_grants(gs, *, won, hp_delta) -> int`——策略卡
「战斗胜利后，若未损失小队生命值，则每有一个佩佩就会为你提供1金币」通道
(首例招财狗 id 103501,登记表 = `cw_investments.STRATEGY_WIN_GOLD_GRANTS`
白名单:键 = 策略规范名,值 = 每佩佩金数)的唯一检查本体,与 §2.11/§2.12
同族(策略卡战后触发族;本族系 = win 结算条件金形状,扩形状各建各表)。
条件矩阵四序(序即短路序):①持卡 ∩ 登记表空(未持卡/表外卡同路)→ 0;
②`not won` → 0(胜利判据);③`hp_delta != 0` → 0(未损血判据;②③并列
必要——扑满败局形态 `won=False ∧ hp_delta=0` 存在,单条件化会在扑满
败局误发);④佩佩计数 → 返回 n × 表值。

- **计数口径**:合并池(备战槽 ∪ 上阵两排槽 ∪ 溢出位,与升星判断同池
  ——佩佩恒后台仍可因席满落溢出,都是玩家「有」的佩佩)内单位数,
  **不折星**(2★ 佩佩 = 1 个佩佩,「每有一个佩佩」量词直修饰单位);
  bench/deployed 未观察 None → 该域计 0 宁缺勿造(env 触发器同契约);
  溢出位按身份串计,溢出「有件未识别」形态(告警在场 ∧ 身份空串)
  自然计 0(sim 生产不可达,溢出身份由获得链直写恒有串)。
- **纯读零写零 rng、无 done 闩**(周期型,每战斗结算重查):契约同
  §2.12(决策与写面分离),写面(observe 金)归调用方,故无 sig 入参,
  与 check_env_streak_grants 自带写面形态差异显式申报;幂等零新增守卫
  = 调用方 `_settled_key` 节点键。
- **挂点 = sim 结算腿**(现役唯一调用点 = `cw_sim_backend._resolve_battle`,
  策略卡战后触发发放腿(§2.11)之后、败局待办登记之前,胜败两态共同
  路径;死亡局在提前 return 处已出局不发放)。写面 = observe 金独立笔
  (evidence `strategy_win_gold:p<位面>r<轮>`,与 `income:`/`streak:`
  族分列可过滤审计;值 = 当拍收入落账后现值 + n×表值;obs 族 sig 组
  `sim:strategy`——组名沿在役惯例 obs/logic 共用,同名 logic 组 =
  §2.11 发放腿);**live 零写观察覆盖**(金由游戏侧自发入账,下一结算
  屏金真值覆盖收束,与 §2.12 live 口径同型)。
- **触发域 = 全部结算节点**(desc 未写明面的建模 v0:卡面「战斗胜利」
  未限定节点类型,接线不设节点类型守卫——奖励关恒胜白拿即发,扑满
  败局由双判据短路不发);假设经披露键
  `strategy_win_gold_scope_all_settlement_nodes` 随局申报(发金拍
  setdefault),实机持卡局奖励关/扑满关结算屏金收入对照可校准,差额
  暴露归披露键校准面。

### 2.14 策略卡等级装备发放检查腿 check_strategy_level_equip_grants(live 结算位 + sim advance 双点)

`check_strategy_level_equip_grants(gs, sig) -> str | None`——策略卡
「升到9级时，获得【财富宝钻】」通道(首例钻石商人 id 130401,登记表 =
`cw_investments.STRATEGY_LEVEL_GRANTS` 白名单:键 = 策略规范名,值 =
`StrategyLevelGrant(id, level_target, item)`)的唯一检查本体,kernel
直写形态(函数内发放 + 落闩,check_env_streak_grants 同构;与 §2.12
金支「纯决策 + 调用方写」分工相反——装备腿不在金面禁直写辖域,双端
同链零分叉)。条件矩阵六序(序即短路序):①持卡 ∩ 登记表空 → None;
②卡名 ∈ `strategy_conditional_done` → None(一次性封账);③level
现值 None → None 不封账(宁缺勿造,读裸值非 level_of——缺省 1 读口
会把未观察伪装成低级);④equips 现值 None → None 不封账(禁半发放,
闩只在发放同窗登记,后续检查重查);⑤现值等级 < level_target → None;
⑥达标 → `gain_equipment`(rand=False 确定事件 logic 写,evidence
`strategy_level_grant:<卡名>`,producer
`strategy_level_equip_grant`)→ placed=True 落闩(同 evidence 同 sig
相邻原子)并返回装备名;placed=False 零闩返回 None(重试自愈)。

- **双端同链三调用点**:live = 结算覆盖位单点(`cw_screen_battle_wait`
  结算窗,level 资产 None 不调〔与覆盖写端跳过 level 观察同口径〕,
  sig = logic_hook 族 group `battle-wait:strategy-level-grant`,返回
  值刻意忽略);sim = advance 双点(`_on_node_advance` 推进点 +
  `_on_node_advance_terminal` 局终点,均挂节点经验入账拍、先于新节点
  窗/胜局披露,sig = `logic_sig('sim:strategy')`);返回非 None → sim
  侧调宝钻回调 `on_diamond_acquired`(世界数值面三写,live 零回调
  ——deploy_cap/back_layout/diamond_count 联动属观察域识别器)。
- **与金支异名并存**(§2.12 契约零改):「升级类条件卡各建各表各函数」
  在码指令 + 用户裁定(不预建统一条件框架)双锚;共域闩不分叉(同一
  `strategy_conditional_done` Field 纯卡名,卡名即全域能量键)。
- **休眠申报**:现役 sim 经验常量下 9 级不可达(全程封顶 7 级),本腿
  恒短路于第⑤序 = 休眠正确路径(§2.12 同族口径,两披露键两腿共用);
  经验源扩网后零改激活。本表登记第二行时单笔返回契约会漏「局终同拍
  双卡双就绪」第二笔,届点 = 第二行登记批改列表返回或调用方循环。

## 3. 枚举回调(在用四枚举;枚举即收敛,无注册表)

回调 = kernel 内枚举函数,**不设注册机构**(用户裁定:函数体内枚举即收敛,新效果
核实后在函数内加分支)。查无效果 = 安静不写,真值归观察覆盖。

**环境发放五表分域**(哪些发放不经本节枚举):投资环境的「发放」类效果分五表,
`cw_investments.py` 内各管一面——①`ENV_GIFTS`(具名发放通道:角色/占席道具,
经 `on_env_gained` 枚举与 §2.7 定时支,属本节适用范围);②`ENV_ECONOMY`(估值通道:
结构化经济效果参数,策略层 `env_economy` 消费,发放动作不经本链);③
`ENV_ORE_GRANTS`(声明矿通道(首现定义:声明矿 = 按环境声明金额发放的金晶矿):
**sim 世界侧发放**——矿进入世界时的声明内容,在用
= 增发货币〔id 103〕每位面开局 6/8/12 金晶矿)。声明矿的发放形态 = 位面开局
声明入队 → 矿进入世界时附着 → 点击兑现,全程经 `kernel/cw_ore_channel.py`
(电平检查 `check_ore_declared_level` + 挂接入口 `report_spheres_observed`)
而非获得链原语;域定义与队列语义 = fields.md §3.2.8a/§3.2.8b;④
`ENV_STREAK_GRANTS`(**条件达成通道**:结算连胜触发器——发放时点不在「获得」
动作,在战斗结算连胜真值落账后,触发检查单一源 =
`kernel/cw_env_grants.check_env_streak_grants`,在用 = 深井角斗场〔id 104〕
本局首次 5 连胜 → 财富宝钻)。④与前三表的形状分工:`items_immediate` =
选卡当场落席、`items_scheduled` = 登记定时队列到点落席(§2.7)、
`ENV_ORE_GRANTS` = 位面开局声明矿——本表 = **结算时点 × 连胜条件 × 本局
首次一次性**(一次性由 `env_grants_done` 标记承担,域规格 =
fields.md §3.5.5)。发放不经获得链原语与本节枚举回调:装备发放 = equips 尾部
追加 `write_logic_rand` + done 追加两笔相邻直写(宝钻落位不可观察的随机态
写,无落位/升星/回调链诉求);宝钻的世界数值联动(diamond_count/deploy_cap/
back_layout)= sim 侧独立回调 `cw_env_grants.on_diamond_acquired`(observe
三写;live 不调,联动归观察域)。**分域边界**:单一环境只落一个估值结构
(表间互斥校验已随 2026-10-28 治理移除,单一落点归评审把关);
`ENV_ORE_GRANTS` 与两表**不互斥**——增发货币同有估值面
(`ENV_ECONOMY.gold_per_plane_start`,策略层估值消费)与 sim 世界侧(声明矿金额,
点击兑现入账),两表同出卡面原文,金额一致性归评审与 ore 域测试把关
(双源同值校验已随治理移除)。⑤`ENV_DELAYED_ITEM_GRANTS`(**倒计时件通道**:获得刻
纯队列登记零席位写 → sim 进节点收口到点开盒(§2.9)→ settle_confirm 完胜
回退三口全链零采样;域规格 = fields.md §3.2.25)。

- **on_env_gained(gs, session, env_name, *, rand, sig, rng=None)**:查 `cw_investments.py::
  ENV_GIFTS`(投资环境 → 具名发放数据表,即时/随机/定时三通道)。命中后**先按
  advisor 分道,两道互斥**:
  - `advisor=False`(契约类,直接送卡):`chars_immediate` 逐个 `gain_character
    (char, 1★)`(星级未标 = 1★ 先验;确定发放 → rand 原样透传);
  - `advisor=True`(特邀专家,顾问入商店):**不入席**——经解锁写原语
    `cw_gain_chain.py::_unlock_experts` 写权威状态 `gs.unlocked_experts`
    (只增去重幂等 + 成员闭集闸 + rand 透传;「使其在本局游戏中加入商店」
    = 入池可刷,非直接送单位;池派生消费 = `cw_pool.unlocked_expert_copies`
    按名并入 `EXPERT_COPIES_ASSUMED` 副本)。效果串
    `advisor_unlock:<环境名>:<顾问名>`。**条件形态支**(`chars_conditional`
    非空即条件形态,现役唯一 = 特邀专家:银狼「首次获得【银狼LV.999】时,
    顾问入商店」):环境获得时刻对在场单位(备战 ∪ 上阵 ∪ 溢出位)判
    一次「首次获得」——「首次」涵盖环境获得之前已发生的获得,开局种子
    起手与先购得后经蓝海改写等中途获得本环境局在此收口;命中 → 解锁银狼
    入商店,效果串尾 = `银狼`;未命中 → 零写,效果串维持空尾
    (`chars_immediate` 空 join,即「条件形态未触发」的自然读法);bench
    未观察 → fail-closed 不判零写 + 缺陷保留证据(`kind =
    DEFECT_COND_BENCH_UNOBSERVED`;开局种子恒种 bench,种子底座下生产
    不可达,实为直构/测试形态防御)。环境获得后的首次获得由
    `on_character_gained` 转发条件判据承接(见下),两挂点合起来覆盖
    「首次」全语义。
  - **开局替换清席支**(`replaces_opening_supply`,advisor 分道之后、具名支
    之前;首例 = 人才储备 id 144「开局补给替换为3个随机3费角色」):移除
    bench 上全部角色槽(`kind='unit'`;占席道具类槽不在替换面——开局窗
    结构性不存在,防御性保留;部署行/溢出席开局窗恒空不触)后按后续支
    发放。写通道 = `_select_write` 单一收束(清席 = 确定发放语义,rand 原样
    透传,具名支同款):live 选卡窗未锚定 → 落随机态,由首备战帧 bench 整表
    观察覆盖收口;sim 恒未锚定 → 落账即世界真值(纠回 M01 预写的开局 4 张,
    选卡前无消费者,瞬态不可见)。零角色槽(live 空底座)零写,只留效果串
    `env_opening_replace:<removed>`(替换事实恒申报,与发放成败解耦)。
    替换/合成语义假设申报 = `cw_investments.ENV_OPENING_REPLACE_ASSUMPTION_KEYS`
    两键;构建防呆 = `_validate_env_gifts` ⑩(True 须伴随角色支)。
  - **追加随机环境申报行**(`cw_investments.ENV_REROLL_NAMES` 命中,与
    ENV_GIFTS 通道无关、先于其分派):追加随机环境型环境(首例 = 蓝海,
    id 113)选卡后游戏随即再随机获得一个环境,该掷骰 live 端不可观察
    (`active_env` 无观察覆盖通道,选择事实与真值不可分辨)→ 申报留证一行
    (`kind = ENV_REROLL_DECL`,独立小块形态沿 `PICK_INVEST_INVALID_PAYLOAD`
    先例,语义申报非缺陷告警),行为 fail-closed——选卡容器写序列与普通
    环境逐位一致。世界掷骰 = sim 后端追加获得分支二次入链(`cw_sim_backend.
    _on_invest_picked`:原语 `gain_invest_env` 复用、显式双流键 rng
    `M02/env-reroll`/`M02/env-reroll-gift`,卷中环境获得时效果全族照常触发),
    双端各产一行如实记录「选择时点真值未知」;建模知识正本 =
    invest_effects.md 蓝海条。
  - **随机赠卡锁分支**(`cw_investments.ENV_DEPLOY_LOCK_GRANTS` 命中,申报行
    之后、ENV_GIFTS 查表之前;世界发放域登记表白名单,与 ENV_GIFTS 集合
    互斥构建期防呆):获得当刻随机赠卡带上场锁——牌库时点池
    (`cw_pool.grant_char_pool` = 规格域 ∩ 当时牌库,未解锁专家剔除,
    用户裁定 2026-10-28「授予候选 = 当时牌库里存在的角色」)内均匀掷骰
    选名 → `gain_character(rand=True)` 落席
    (星级 = spec.star,`rng` 回退/条件解析与随机角色支同款三层已通)→
    实例发号(`env_grant_uid_seq` 计数器,uid 随落位单位 = 锁匹配键)→
    锁记录 `(名, uid, 解锁序位)` 追加 `env_grant_deploy_locks`(解锁序位 =
    获得刻生效序位沿节点日程表步进 `deploy_lock_nodes` 步,计数起点 =
    获得节点计入锁定段〔设计定读〕;未锚定窗防御基准 (1,1);步进遇 None
    停留最后合法值)→ `perfect_win_accel` 开时追加完胜作用域键
    `deploy_lock_uid#<uid>` 落 `env_grants_done`(键形态登记 =
    fields.md §3.5.5;消费 = `check_env_deploy_lock_perfect` 完胜改写,
    settle_confirm 分支挂点)。效果串两行 `env_gift_random:<名>@<星>star`
    (与随机支同前缀同形,审计归组)+ `env_deploy_lock:<名>#uid<n>@<位>-<轮>`
    (锁登记串)。落位成败与锁记录/done 解耦(placed=False 零写留证,锁
    记录照写);锁随 uid 不随名(掷骰名是猜测,bench 首观察覆盖纠偏,
    守卫拒/放对象不受扰);拦截复用 deploy_move/swap_deploy 既有守卫
    零新建。首例 = 英雄登场(id 133「获得1个2星5费角色,19个节点后才能
    将其上场。战斗完胜后,上场节点额外提前1点。」;建模知识正本 =
    invest_effects.md 英雄登场条)。
  - **延迟道具支线**(`cw_investments.ENV_DELAYED_ITEM_GRANTS` 命中,随机
    赠卡锁分支之后、ENV_GIFTS 查表之前;世界发放域登记表白名单,与 ENV_GIFTS
    集合互斥构建期防呆):获得当刻**纯队列登记零席位写**——件 = 棋盘右上
    战利品区浮动件非占席(实机板件实证 = 与晶矿球同区;禁 `_place_bench_item`
    调用、禁 bench/overflow 任何字段、BENCH_ITEM_NAMES 词表零扩),队列 =
    `pending_item_opens`(fields.md §3.2.25)追加 `(件名, 解锁序位)`(解锁
    序位 = 获得刻生效序位沿节点日程表步进 `open_delay_nodes` 步,计数起点 =
    获得节点计入〔设计裁决点 3〕;未锚定窗防御基准 (1,1);步进遇 None 停留
    最后合法值);`perfect_win_accel` 开时追加 done 条件键 `delayed_open_accel`
    (幂等不重写;消费 = `check_env_item_open_perfect` 完胜回退,
    settle_confirm 分支挂点,解锁位沿序列表前驱回退一步、多次完胜累积)。
    效果串单行 `item_open_scheduled:<名>@<位>-<轮>`;**零 rng**(到手确定
    件名、解锁位确定推算、开盒确定事件——pick_invest_env 随机管线对本表
    零采样分支)。到点开盒 = §2.9 原语(sim 专用,实机不接)。首例 =
    命运礼物(id 134「立刻获得一个【惊喜盒】,倒计时12个节点后礼盒打开,
    战斗完胜后,倒计时额外减少1点。」;建模知识正本 = invest_effects.md
    命运礼物条)。
  - **词缀失效删除分支**(`cw_gain_chain.ENV_AFFIX_DISABLE_ENV` 命中,延迟
    道具支线之后、ENV_GIFTS 查表之前;硬编码分支沿 DOT_CONTRACT_ENV
    枚举即收敛先例,单卡零复用面不入登记表):选敌后破坏(id 146
    「开局时，使一个已生成的敌人词缀失效。」)→ 词缀名单
    (`gs.enemy_affixes`)非空时均匀随机删 1 个、剩余列表整条替换写回,
    经 `_select_write` 择道且 rand=True 双保险声明采样链——live 选卡在
    开局未锚定窗自动落随机态(裁定「词缀要变成随机态」),掷骰 = live
    模型猜测/sim 世界真值,猜测偏差由位面详情补观察闭环转正
    (screens/plane_intel.md 备战委派 + 写门随机态分支;消费门纪律 =
    `logic_rand_fields`)。采样分支具名流键 `action_sampling_rng(
    'env_affix_disable', None)` 分支内自解析(env_merge_grant 双端同槽
    先例,命中判据前置、无命中不取槽);删除写触发词缀域写尾 HP 先验
    回调(`cw_opening_hp.on_enemy_affixes_logic_write`,挂点 =
    `_write_logic_frame` enemy_affixes 分支,logic/logic_rand 两通道
    同经、observe 覆盖零回调,经 `write_prior` 重算先验——fields.md
    §3.1.6);容器空 → 跳过删除,零写 + 申报行(`kind =
    ENV_AFFIX_DISABLE_EMPTY_DECL`,实机已失效而模型未删,偏差全程持续,
    设计披露键 3)。效果串 `env_affix_disable:<词缀名>`。T-14 蓝海追加
    链相容限 sim 端(二次入链 = sim 专属,live 端无二次入链零删除分支
    触发,设计披露键 6);姊妹卡退化失效分支复用本机制(T-291 批套用)。
    设计正本 = 迭代 2026-09-23-invest-effects-calc T-45 设计稿 §2.1/§2.3。
  - **随机支**(`chars_random_immediate`,具名支之后):元素 = `RandomCharSpec
    (cost|faction, star, type_tag)` 随机赠卡规格(家族载体,「随机N费」与
    「随机【阵营】」两族共载体,采样轴二选一构建期互斥校验,费用轴首例 =
    人才引进「开局拥有1个随机4费角色」id 109,阵营轴首例 = 追击概念股
    「获得【追击】角色」id 1001——【X】为流派名非角色名,不入具名检查域);
    发放 = 牌库时点池(`cw_pool.grant_char_pool`:基底 = 规格过滤池
    `random_char_pool` 注册表派生单一源——采样轴内 × char_type 含标签,
    费用轴 = chars_by_cost 全档,阵营轴 = chars_by_faction 默认含流派
    匹配,池非空构建期校验,误登角色名/笔误阵营名 → 域空 import 即炸;
    双形态合并随基底;叠加层 = 未解锁专家剔除〔用户裁定 2026-10-28
    「授予候选 = 当时牌库里存在的角色」:环境注册时点解锁恒空 → 候选
    不含专家;中局通道随容器解锁态〕)内均匀掷骰选名 → `gain_character`
    落席,星级 = spec.star(人才引进 1 = 先验非结构值)。**效果体含采样 →
    子链 rand=True**(§5)——未锚定期(开局窗)本就走 write_logic_rand,
    rand=True 声明采样语义并保锚定后不进失配网(实机猜错 = 首观察静默覆盖,
    `logic_rand_outcome` 收尾,不触发告警停局)。效果串 `env_gift_random:<名>@<星>star`
    (与具名支 `env_gift:` 前缀分离,采样发放可独立过滤审计)。`rng` 缺省回退
    自掷 `random.Random()`(直构/测试形态);正式接线 = 上报函数
    `report_action_pick_invest_env_param` **条件解析**(仅选中环境登记了随机支
    才经 `action_sampling_rng('pick_invest_env', rng)` 解析)——sim 装配 =
    流键 rng 即世界真值,且默认环境局(无随机支)rng 消耗序列逐位不变。
    采样/先验假设申报 = `cw_investments.ENV_RANDOM_CHAR_GRANT_ASSUMPTION_KEYS`
    三键(池内均匀 v0 / 星级 1 先验 / 类型标签过滤口径)。
  - **即时装备支**(`equips_immediate`,落地序 = 随机支之后、即时道具支之前):
    元素 = 具名装备名(EQUIPMENTS 在册;首例 = 红钻贵族 id 131「开局时拥有
    【红钻】和一个【简易武装箱】」,装备入账分支在前 = 卡文序,遥测序与卡文对齐)。
    发放 = `gain_equipment(rand=True)` 入栏(equips 库存,不占席、不进
    BENCH_ITEM_NAMES)——确定具名发放,写通道走随机态(2026-10-17 用户裁定:
    「选卡时点游戏实际发下」对首例环境未经实机判读核实,卡面文本是唯一证据
    ——猜测写 + equips 观察覆盖纠偏,首观察静默覆盖落 `logic_rand_outcome`
    台账,锚定与否都不进失配网;先例 = T-5 财富宝钻/T-29 奖励全分支随机态;
    本支零采样不需 rng)。效果串 `equip_gift:<名>`,与 `env_gift:`/
    `env_star_grant:`/`item_gift:` 前缀分域。登记与构建校验 =
    `_validate_env_gifts` 装备名漂移哨(逐名 ∈ EQUIPMENTS;治理口径
    2026-10-28:防登记笔误类校验〔通道同名互斥/空发放集等〕已移除,
    只留版本漂移哨,错名防线归评审与测试)。
  - **随机装备支**(`equips_random_immediate`,落地序 = 即时道具支之后、定时支
    之前):元素 = 装备类别名(EQUIPMENTS category 词),发放 = 类别池
    (`equips_by_category`,注册表派生单一源)内均匀掷骰选名 →
    `gain_equipment(rand=True)` 入栏(equips 库存,不占席、不进
    BENCH_ITEM_NAMES)。**绑定门**(`ENV_BOSS_GRANTS` 成员资格):成员
    (绑定语义 = 首领节点分支2 按绑定星徽发角色,首例 = 劳务派遣合同
    id 118「获得随机星徽」)效果串 `env_star_grant:<名>` + 发放名落
    `env_grants_done` 条件键 `star_grant#<名>`(placed 守卫下写——equips
    未观察时 `gain_equipment` 零写跳档 → 绑定同样不落,禁「绑定在而装备
    未发」残缺态),消费 = `check_env_boss_grants` 分支2 绑定解析(条件键
    形态登记 = fields.md §3.5.5);非成员(概念股族及后继,首例 = 追击
    概念股 id 1001「初始简易装备」类别池复用本通道)零 done 键、效果串
    前缀 `env_equip_random:<名>`(与具名支 `equip_gift:`/随机角色支
    `env_gift_random:` 分域,审计归组键)。`rng` 回退/条件解析与随机角色
    支同款。
  - **持续伤害契约锚键分支**(条件分支建模 T-28,获得刻纯登记):具名支发完
    椒丘/卡芙卡后,`on_env_gained` 对本卡追加登记 `env_grants_done` 条件键
    `dot_anchor#<位面>-<轮>`(与即时分支同窗相邻 write_logic 直写,同
    evidence 同 sig;**纯登记件非门控**——显式判 node,节点未进窗〔开局
    三选一获取形态〕不写,防 `'dot_anchor#-'` 畸形键;缺锚不影响猜测写/
    计数/证实,消费门 = `check_env_dot_grants` 的 active_env 门)。键形态
    登记单一源 = fields.md §3.5.5;条件分支「猜测写+证实」建模口径 =
    invest_effects.md「条件分支族面口径」节。
  - **道具通道**(`items_immediate` + `items_scheduled`,与 advisor 道无关、
    可叠加):道具 = 占席待开箱,非角色非装备。**即时支**(`items_immediate`):
    落位写入(角色落位同构:备战空槽放**带名槽件**
    `BenchSlot(kind=BENCH_ITEM_KINDS[名], item=名)`——名字→类别映射桥单一源
    (§2.8),双端
    同一获得链——sim 世界写入即容器写;类别由映射编译:武装箱系 →
    supply_box(开箱链)、专家邀请函 → bookcard(开卡链,
    **bookcard 槽件发放首例** = 专家研讨会 id 139,卡文序邀请函先箱后,
    开卡/选卡链现役承接零新通道));席满 = 溢出落位(实机真值:道具与角色
    同款——落溢出席并阻断进入战斗,`overflow_warning=True` + `overflow_card=
    道具名` 两字段直写,见 §4);溢出位被占 = 零写 + 每道具一遥测申报保留证据
    (`kind = DEFECT_OVERFLOW_TAKEN`,与角色分支同款);效果串 `item_gift:<名>`
    (数量 = 元素重复次数)恒登记,开箱链由外循环画面分发承接(武装箱选择画面
    独立建档)。首条 = 火药味(id 101,开局 2 个简易武装箱)。**定时支**
    (`items_scheduled`):登记不落席——(节点键, 道具名)逐项解析入容器队列
    `pending_item_grants`(fields.md §3.2.24;一次 write 回写整表),效果串
    `item_scheduled:<名>@<节点键>`(如 `item_scheduled:特权武装箱@2-1`,
    数量 = 元素重复次数,发放事实登记与即时通道同阶),到点发放 =
    `discharge_due_item_grants`(§2.7)。首例 = 特权阶级(id 102,第二位面
    开始时获得 1 个特权武装箱)。
  - 欢愉契约条件分支**不在本枚举**:正式模型 = 银狼策划选择上报动作落地时点的附加条件授予
    分支(`kernel/cw_action_report/pick_planner.py::_grant_joy_conditional`,
    头号玩家选项触发 + 欢愉契约已登记 → `gain_character`(火花/开拓者·欢愉随机
    其一,1★,rand=True),调用点级 best-effort 例外见 §6;条件分支原文与建模依据 =
    `cw_investments.py::ENV_GIFTS['欢愉契约'].chars_conditional`)。
- **on_character_gained(gs, name, star, *, rand, sig)**:在用枚举 = 转发特邀专家族
  条件形态判据(`cw_gain_chain.py::expert_conditional_trigger`,首个消费者 =
  特邀专家:银狼「首次获得【银狼LV.999】时,顾问入商店」)。判据三条件
  全与:①名直等 `银狼LV.999`(触发映射硬编码分支,单一源指向
  `ENV_GIFTS['特邀专家:银狼'].chars_conditional` 条件散文——该字段 =
  (顾问名, 条件散文)注释性二元组不进判据;按规范名直等,升费 3/4/5 档
  全通吃);②`active_env` 归一 = 本卡(单环境互斥天然挡他环境同形发放,
  如欢愉契约送卡);③银狼 ∉ `unlocked_experts`(「已触发」与「已解锁」
  同一事实,防重发与消费同源、不立第二账本,幂等短路免费兜住升星产物
  递归重进)。命中 → `_unlock_experts` 写解锁 + 效果串
  `expert_unlock:银狼`。同判据**三渠道接线**(环境获得后的事件挂点式
  触发器):购买链(买牌上报回调分支,现役主流)/ 平行桥
  (`grant_bench_unit_cascade` 桥尾)/ 获得链(本收敛点转发)——三渠道
  同判据同写入,行为等价,宿主出参不扩字段(触发写入自身即留证,
  write 行 evidence 标 `expert_trigger`/`#expert_unlock` 族)。获得链
  现役无可达首次**触发**场景(既有可达获得 = boss 节点羁绊分支,被条件②
  × 单环境互斥挡在触发外),本接线 = 收敛点承诺兑现 + 登记表未来扩入
  带目标名池发放分支的防御。开局种子起手与先获后选环境局(首次获得先于
  环境获得)由上 advisor 分道挂点④在场判定收口,两挂点合起来覆盖
  「首次」全语义。**本函数 = 「获得角色触发型」效果未来的唯一收敛点**。
- **on_equipment_gained(gs, item, *, rand, sig)**:查 `cw_effect_inventory.py::
  EQUIP_ACQUIRE_CONSEQUENCES`(装备获得 → 送出单位;该表是游戏数据映射不是效果
  注册表)→ 命中 → `gain_character`(表值星级;确定发放 → rand 原样透传)。
- **on_strategy_gained(gs, strategy_name, *, rand, sig, rng=None)**(策略屏迁移批
  新增):查 ``cw_gain_effects.py::PICK_INVEST_EFFECTS``(策略卡获得效果注册表,
  键 = 注册表规范名;在用全集单一源 = 该表本体与各生成表——骇客单行、
  箱授予分支、援军族、随机装备族、策略延时 offer 族〔键集封闭断言
  守两表面零漂移,枚举此处不逐卡复制〕)→ 命中 → 效果体执行。骇客卡链序 =
  银狼分支 `gain_character` +
  商店池遥测申报行 + 改件 `gain_equipment(rand=True)` 采样入栏(改件后果经
  `on_equipment_gained` 回调)。箱授予分支三卡 = 获得时点占席道具发放:效果体消费
  `gain_bench_item`(§2.8;确定发放 → rand=False,效果串
  `box_grant:<道具名>(placed=<是否落位>)`),发放名单单一源 =
  cw_gain_effects `_STRATEGY_BOX_GRANTS`(卡规范名 → 道具名;与登记面镜像
  `cw_investments.STRATEGY_GRANTS` 三卡 `items_immediate` 逐对相等,
  一致性测试)。三卡的战斗被动效果(能量恢复/伤害减免)非「获得时点」效果,
  不在效果体(获得时点容器写分支适用范围外);快请专家·彩的好运令牌分支(非占席
  道具,消耗品域)与空括号分支(数据源缺口禁猜)同不在。
  **具名角色支首例**(溜佩佩/溜佩佩+/招财狗,佩佩召唤族世界腿;溜佩佩系
  登记面 = 非直读人工转正,招财狗 = 「获得」直读登记):效果体消费
  `gain_character(rand=False)` 具名入席(星级实参 1
  = 占位非先验,佩佩 = cost0 系统召唤单位无星级),落位/回调/升星/席满
  溢出全沿链现役零新增;效果串 `char_grant:<角色名>(placed=<是否落位>,
  merge=<升星级数>)`(前缀与 box_grant/装备/随机角色各族分列可过滤审计),
  发放名单单一源 = cw_gain_effects `_STRATEGY_CHAR_GRANTS`(卡规范名 →
  发放角色;与登记面镜像 `cw_investments.STRATEGY_GRANTS` 三卡
  `chars_immediate` 逐对相等,一致性测试;族后继卡 +1 行复用)。
  **延时 offer 登记腿**(策略卡延时三选一通道,黄金期货首例):注册表
  `cw_investments.STRATEGY_DELAYED_OFFERS`(卡规范名 → id/倒计时/候选品质,
  白名单制)+1 行即自动获得登记腿(效果体由该表派生,键集封闭断言守住
  两表面)。效果体消费 `queue_delayed_invest_offer`(§2 入队原语,登记 =
  确定事件零采样):追加 `(卡名, 倒计时)` 到 `pending_strategy_offers`
  一次 write 回写,效果串 `strategy_offer_scheduled:<品质>@<节拍>`;
  到点呈现归 sim 专用腿(不对称申报,live 队列恒悬置,域规格 =
  fields.md §3.2.26)。未建模申报归
  [strategy-env-impacts.md](strategy-env-impacts.md) §3;未收录卡安静不写。
  **延时发放登记腿**(策略卡延时世界发放通道,人才激励 id 101601 首例,
  与延时 offer 族并列独立域——本族到点产出 = 世界发放写,offer 族 =
  选卡屏事件):注册表 `cw_investments.STRATEGY_DELAYED_GRANTS`(卡规范名
  → id/倒计时/发放物,白名单制;构建校验三漂移哨 = 孤儿键/id 双匹配/
  发放物名 ∈ EQUIPMENTS ∪ BENCH_ITEM_NAMES)+1 行即自动获得登记腿
  (效果体由该表派生)。效果体两步:即时腿 `gain_equipment(rand=False)`
  具名入栏(效果串 `equip_grant:<发放物>(placed=<是否落位>)`;equips
  未观察 = 拒落零写)+ 延时入队腿 `queue_delayed_strategy_grant`(§2
  入队原语,登记 = 确定事件零采样):追加 `(卡名, 倒计时)` 到
  `pending_strategy_grants` 一次 write 回写,效果串
  `strategy_grant_scheduled:<发放物>@<节拍>`;到点发放归 sim 专用腿
  `discharge_due_strategy_grants`(到期即弹除,发放物按注册表行归属
  分道,不对称申报,live 队列恒悬置,域规格 = fields.md §3.2.26b)。
  卡文句式分流:带即时短句的卡(人才激励系)走上述两腿效果体;纯延时
  单句卡(许诺特权/先亏后盈)显式单行登记延时-only 载体(直用两腿工厂
  = 拿卡错发即时腿),效果体仅入队腿。入队条目数 = 注册表 `count`
  字段循环(数量单一源落注册表,先亏后盈 2 = 首例:同拍两条同卡条目
  逐条独立倒计时,到点逐条独立发放/独立席满判定;default 1 与单次
  入队逐位一致)。
  未收录卡安静不写。

## 4. 溢出落位规则(双写入方)

备战席满时新获得件无处落 → 溢出落位(角色与占席道具同款,2026-09-24 实机
真值用户确认——道具同样落溢出席并阻断进入战斗),写 `overflow_warning=True`
+ `overflow_card=身份串`(角色 = char_id,道具 = 道具名;两字段各一行,
同 evidence 同 sig 同组):

- **双写入方声明**:两字段由「观察写入方单一源」扩为**双写入方**——观察完整观察(全量识别)写入方
  (备战溢出观察)+ 获得链逻辑写入方(席满溢出落位直写);第二逻辑写入方先例 = 卖牌
  溢出分支(`kernel/cw_action_report/sell_bench.py`)。与容器字段注释、
  `kernel/cw_projection_audit.py` 对账 basis 行一致,字段语义权威版本 = fields.md
  §3.2.21。
- **身份两分判 kind(带名)**:溢出位身份串的消费方(合成池构建 `_build_pool` /
  卖牌溢出分支入位)按 `cw_investments.BENCH_ITEM_NAMES` 判是否占席道具——
  命中 = 查映射编译 kind 落**带名惰性槽件**
  `BenchSlot(kind=BENCH_ITEM_KINDS[身份串], item=身份串)`(禁造 Unit 假身份进
  合成素材组;kind = `BENCH_ITEM_KINDS` 映射值,武装箱系 = supply_box、
  专家邀请函 = bookcard;2026-10-24 批起带名,入位槽身份与发放写端同源
  不漂),未命中 = 角色。取值清单(词表键集)= 两张 GiftGrant 授予表的
  `items_immediate` ∪ `items_scheduled`(键集一致性归测试与评审把关;
  漏登的运行期后果 = 落席直查 KeyError 响亮可见,2026-10-28 校验治理后
  import 期双向闭合校验已移除);观察专属来源(星徽秘典,tome)不经授予
  通道不入词表(豁免)。
- **星级链记**:星级不入容器字段(overflow_card 只存身份串);链内工作池自记本次
  授予的星级(升星判断用链记真值)——写入即知真值,不依赖观察兜底口径。观察来源
  的溢出卡星级缺读按 1 兜底(现行口径,fields.md §3.2.21)。
- **溢出位被占**(链内连环授予第二次溢出):游戏行为未实证 → 零写 + 缺陷记录表保留证据
  (`kind = DEFECT_OVERFLOW_TAKEN`),禁猜。
- 溢出件被合成消费/腾槽归位 → 溢出位腾空,两字段成对清写(False + '')。
  道具件不入素材组(无升星语义),只参与腾槽归位。

## 5. 随机态参数纪律

六原语与四回调均带 `rand: bool` 必带入参,逐函数入参、递归透传:

- 链入口按自身性质定初值(投资环境/投资策略确认 = 确定性入口,False);
- 递归调用点按**该效果自身性质**传参:效果体含采样 → 对其发起的子链传 `rand=True`;
  不含采样 → 原样透传;
- 采样效果体在用实例:策略通道 = 骇客改件与随机装备族(`on_strategy_gained`
  效果体,rng 经 `gain_invest_strategy` 形参注入;随机装备族池 =
  `equips_by_category` 注册表派生,类别池均匀 v0,分布披露键
  `strategy_random_equip_uniform`);环境通道 = 随机赠卡支(`on_env_gained` 的
  `chars_random_immediate`,rng 经 `gain_invest_env` 形参注入,上报函数条件解析
  ——仅登记了随机支的环境才推 sim 动作采样序号,默认环境局 rng 消耗序列
  逐位不变)。
- 零采样 rand=True 例外(2026-10-17 用户裁定):环境通道即时装备支
  (`equips_immediate`)确定具名、零采样,仍以 rand=True 走随机态通道——
  「选卡时点游戏实际发下」对首例环境未经实机判读核实,卡面文本是唯一证据,
  猜测写 + 观察覆盖纠偏(先例 = T-5 财富宝钻随机态获得);语义 = 通道选择
  声明而非采样,不需 rng。
- 零采样 rand=False 例外(自由市场批):装备获得转换(§2.3)= 确定事件
  (「改为获得」无分布面),转发 `gain_bench_item` 恒 `rand=False` 确定面、
  零 rng 消费——持卡局掷序不变(采样腿照常只消费自身抽样;同 seed 持/
  不持卡两局随机数消耗一致,世界差异仅在写入内容),与上行的分野 =
  转换目标具名确定无猜测写面,无「首观察纠偏」语义可申报。
- 语义:任一写入位置的 rand 值 = 「本次写是否处于随机语义」,不承诺全链一致——采样效果
  只翻转它自己的子链。写通道 = 通道选择入口 `anchor_aware_write`(fields.md §2.6):
  未确认(锚定标志位 `prep_anchored` 未置)一律 `write_logic_rand`——开局预填初值/链落账是
  未验证推算,首观察静默覆盖;确认后按 rand 形参(失配网生效)。通道语义权威版本 =
  fields.md §2.1/§2.5。

## 6. 失败安全四则

1. **链原语零吞错**:容器写分支/回调效果分支异常上抛(真异常该响);调用方(动作上报
   函数)不包整链、零额外吞错。
2. **未锚定期写走随机态,未观察拒落档保留**:容器经开局预填初值播种(fields.md
   §2.6),生产链路阵容/装备域不再有 None——原「未观察 = bug 面」缺陷 kind
   (`gain_chain_bench_unobserved`/`gain_chain_equips_unobserved`)已停用;直构容器
   (sim/测试)的 None 拒落零写与 detail 档保留,零缺陷发射。条件形态在场
   判定挂点(§3 advisor 分道)的 bench 未观察 fail-closed 同属本未观察族:
   不判零写 + 缺陷保留证据(`kind = gain_chain_cond_bench_unobserved`),
   种子底座下生产双端不可达(开局种子恒种 bench),实为直构/测试形态防御。
   链写通道随锚定标志位择道(走通道选择入口)
   (§5,fields.md §2.6)。
3. **查无效果安静不写**(§3):真值归观察覆盖。
4. **席满且溢出位被占 = 零写保留证据**(§4;游戏行为未实证,禁猜)。

best-effort 边界收在**非容器写的观测/登记分支**内(§2.1/§2.4 登记分支;§3
advisor 道现为 `_unlock_experts` 容器写,零吞错不在本边界):失败 log + 缺陷
保留证据、不阻塞。**唯一容器写调用点级例外 = 附加条件授予分支(挂在选项上报上的授予路径)**
(`pick_planner.py::_grant_joy_conditional`,try/except + 缺陷记录行
`joy_conditional_grant_failed` 后照常分支型分派——授予与选项应用是两条独立因果,
授予失败不得拖垮选项应用;链内部零吞错不变)。无效载荷拒绝(§2.1-0/§2.4-0)
同属零写 + 保留证据(输入校验,非防重复保护)。追加随机环境申报行
(`kind = ENV_REROLL_DECL`,§3)同为非告警语义行:追加环境真值 live 不可观察
(`active_env` 无观察覆盖通道),申报留证 + 行为 fail-closed,非缺陷告警——
kind 常量取独立小块位(`PICK_INVEST_INVALID_PAYLOAD` 邻位),非 `DEFECT_`
词表成员,不入缺陷 kind 词表块(免破块内前缀分组)。

## 7. 与旧机制的关系(grant_bench_unit_cascade 过渡期)

`cw_effect_inventory.py::grant_bench_unit_cascade`(落位后**立即**级联合成
`merge_cascade_write`、升星产物不触发回调、备战满拒落零写)仍在用,消费点 =
pick_supply 等旧通道(策略屏效果分支已随投资两屏迁移批改走链原语,消费点撤出)。
它与本链「回调先、升星后」**双时序并存**至各自迁移批;在用消费面无 on-gain 效果
已登记,行为等价。各消费点迁移完成后 grant_bench_unit_cascade 停用。装备获得→送
角色的「全渠道统一后置钩子」`apply_equip_acquire_consequence` 的分派动作已归
`on_equipment_gained` 回调(§3),数据表共用。

## 8. 接入面现状(双支;含模块拆分)

- **投资环境动作落地接入**:`kernel/cw_action_report/pick_invest_env.py::
  report_action_pick_invest_env_param` → `gain_invest_env`(rand=False;
  session 形参显式传入,动作 op 自 ctx 取)。
- **投资策略动作落地接入**(策略屏迁移批新增):`kernel/cw_action_report/
  pick_invest_strategy.py::report_action_pick_invest_strategy_param` →
  `gain_invest_strategy`(无效载荷拒绝/按名字去重追加/登记分支/`on_strategy_
  gained`)。
- **上报时点**(用户裁定 2026-09-21,action_ops.md §1 增补 2):两支均 =
  动作 op 机械链(点选中 → 点确认)发出后**立即**上报——零分步、零证据
  等待;确认未生效 = 代码 bug(点击链可靠性治理)。
- **模块拆分**:链过程语义(原语/合成/枚举回调骨架)住 `kernel/cw_gain_chain.py`;
  效果内容(`PICK_INVEST_EFFECTS` + 骇客采样池 + 效果体)住 `kernel/
  cw_gain_effects.py`(链模块级查表,效果体函数内惰性 import 链原语破环)。
