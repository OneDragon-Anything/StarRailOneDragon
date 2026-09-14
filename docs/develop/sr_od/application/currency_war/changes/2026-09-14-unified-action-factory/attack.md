# 统一动作工厂迭代设计 对抗审查报告

> 审查对象 = 本目录 design.md(总纲,单文档方案)/ landing.md(四批+末阶段)/ README.md。
> 方法 = 三核(无前提/规范遵循/治本)并重,设计主张逐项对权威源与代码核真;
> 代码行号以本次审查时点工作区为准。本报告只读评审,不改任何文件(本报告除外)。

---

## 一、核一·无前提攻击(设计主张与代码真值逐项核)

### F1【design.md §2.6 合并清单 SellBench 行】合并类字段并集漏 `convert_reason`,字段顺序与现役不符
- **攻击内容**:设计给出统一类签名 `SellBench(bench_idx, expect='', income=None, reason='')`,并称「族A 三字段 + 族B reason」。按此签名实现会把现役族A 的 `convert_reason` 字段(结构化豁免分键,发射位在填、检查器在读)从类上删掉;同时设计给出的字段顺序(expect 在 income 前)与现役定义顺序(bench_idx, income, expect, reason, convert_reason)不一致——任何按位置传参的构造点会静默错位。另外「族A 三字段」计数不实:族A 现役是 1 必填 + 4 缺省字段;且 reason 并非「族B 吸收进来的」——族A 本来就有 reason(卖出通道记录字段),双族各自都有该字段。
- **证据**:`kernel/cw_vocab.py:341-396`(SellBench 字段 = bench_idx/income/expect/reason/convert_reason;convert_reason = ADR-0611 转化类豁免分键,发射位 T-165 两通道在填,`SELL_BENCH_CONVERT_REASONS` :425-430 检查器消费);`kernel/cw_prep_actions.py:85-99`(族B SellBench = slot + reason,reason 带 action_key_exclude)。
- **建议修法**:合并清单改为「统一类 = 现役族A 类原样(字段与顺序逐字保留)+ 族B 构造点改产该类」,不新写签名;若确要重排字段顺序,先全仓扫位置传参点并逐点申报。

### F2【design.md §2.6 合并清单 LevelUp 行】漏 `auth_basis`;prep 发射面 `cost` 必填字段的填充源未定义
- **攻击内容**:统一类写作 `LevelUp(cost)`,漏掉族A 现役的 `auth_basis` 授权记录字段(记录非指令,但被 sim 账本序列化为 `auth` 键、被检查器 levelup_interest_engine_gate 消费)。照设计签名实现会拆掉该记录链。另一侧:族B `LevelUp()` 现役无字段,发射面(mandate.py:1481)构造 `LevelUp()`;合并后 cost 是必填字段,备战发射点从哪取值(观测 level_up_cost?kernel `xp_click_cost` 现算?失读时回退 `XP_CLICK_COST_FALLBACK`?)设计未写——实现者必须自行设计。
- **证据**:`kernel/cw_vocab.py:434-443`(LevelUp = cost + auth_basis,auth_basis 消费面注释在案);`sim/engine_p1.py:2299-2314`(auth 键转录);`strategies/impl/mandate_v1/mandate.py:1481`(`Emitted(LevelUp(), True, ...)`)。
- **建议修法**:合并行改为「统一类 = 现役族A LevelUp 原样」,并补一段「备战发射点 cost 取值口径 = kernel 单一源逐帧现算,失读回退常量」,写死取值函数名。

### F3【design.md §2.6 合并清单 DeployMove 行】统一类签名 ≠ 族A 现役签名,faction/to_row 去向未申报,与「sim 消费面零改动」自相矛盾
- **攻击内容**:设计统一类 = `DeployMove(from_bench_idx, to_deployed_idx)`;族A 现役 = `DeployMove(bench_idx, to_row, faction)`(to_row = 'front'/'back' 语义排,faction 供 board 重算)。这不是「归一到族A」,是重新设计族A:faction 字段被静默删除(simulate 的 board 重算要从哪拿阵营?从 bench 槽位对象现取?未写),to_row 改由下标推导,字段名整体改。若按设计改签名,`cw_vocab.simulate`、mutate/投影面、序列化形状都要动——直接推翻 §2.6「规范系 = 族A ⇒ sim 决策/投影/引擎面零改动」的主张(该主张对 SellBench/LevelUp/SellDeployed 三行成立,唯独 DeployMove 行自相矛盾)。且设计未披露一个关键事实:DeployMove 现役**全仓零构造点**(族A 族B 都无人构造,腾席部署实际走 RunDeploy 组合壳)——为一个死类改签名,成本/风险描述失真。
- **证据**:`kernel/cw_vocab.py:466-478`(族A DeployMove = bench_idx/to_row/faction);`kernel/cw_prep_actions.py:135-140`(族B = from_slot/to_row/to_slot);全仓 grep `DeployMove(` 仅命中类定义行(cw_prep_actions.py:136),零构造;`kernel/cw_vocab.py:933` simulate(DeployMove) 消费 to_row/faction。
- **建议修法**:DeployMove 行改为「统一类 = 现役族A 原样,族B 物理槽位参数由执行边换算吸收」;或若坚持改签名,把 faction/to_row 的推导口径、simulate/mutate/投影面波及清单、sim 行为锁的适用性逐项写进 §2.6。

### F4【landing.md §3.2 文件面】批2 文件面 ≠ §2.6 改动面,至少漏四个必改文件
- **攻击内容**:批2 词表归一必然波及以下文件,均不在批2 文件面清单内:
  1. `kernel/cw_prep_expect.py`——`compute_drag_expect`(:70-106)直接读 `action.slot`/`action.from_slot`/`action.to_row`/`action.to_slot` 与 PrepObservation 的物理槽位对账;合并后动作字段变 bench_idx(0-8),不改它则拖拽期望态全部静默错位(下标差 1,缺陷台账假红/漏报)。
  2. `kernel/cw_exec_state.py`——`apply_op_effect`(:301-353)import 族B SellBench/SellDeployed/PickBoxCard 并读 `action.slot`/`action.row`(物理→下标换算 :343-344);词表退役 + 字段改名后此函数必改。
  3. `kernel/cw_game_state.py`——`apply_prep_action_logic`(:2076)是备战容器投影写口(cw_screen_prep.py:905 显式引用「kernel 写口 apply_prep_action_logic 单一源」),消费备战动作字段;必改。
  4. `operations/cw_loop.py`——发射核直接构造并执行 `StartBattle()`(:413、:1971 两处,经 PrepActionExecutor);词表搬家后 import 面翻转。此外 app 桶 decision_assembly 按 mandate_v1/adapter.py 模块头申报「import prep_actions 词汇」,也属词表消费点。
  另有一个未决策略题:族B 类从 cw_prep_actions 迁走后,旧 import 路径是「全翻」还是「留转发 shim」(cw_vocab 头部 T-7 W8 有现成 shim 先例)——两种做法文件面完全不同,设计未选。
- **证据**:`kernel/cw_prep_expect.py:70-106`;`kernel/cw_exec_state.py:301-353`(import 块 :319-323 指 cw_prep_actions);`kernel/cw_game_state.py:2076`;`operations/cw_loop.py:413/:1971`;`strategies/impl/mandate_v1/adapter.py:5-8`。
- **建议修法**:批2 文件面至少补上述四文件(+ decision_assembly 视扫描结果);import 翻转策略(shim 过渡 vs 一次翻清)在 §2.6 写死一种。

### F5【design.md §1/§2.2/§2.3/§2.4、landing.md §3.1】代码锚点一组失真,多数指向 T-201 拆分前布局
- **攻击内容**:设计多处「依据就地标注」的行号锚按现在的代码核不到:
  - `cw_action_base.py:37`(terminal 属性)——该文件总共 35 行,terminal 在 :27;`:72`(SellBenchOp.execute)——文件里根本没有 SellBenchOp,T-201 后在 `cw_sell_bench_action.py`。设计与「T-201 拆分后形态」的立项前提自相矛盾。
  - `cw_shop_actions.py:398`(LevelUpShop is-a LevelUp 注册注)——文件仅 56 行,注在 :41。
  - `cw_screen_prep.py:1368`((detail, emitted) 消费面)——该行在 `_reconcile_merge_preview` 文档串里;实际消费面 = `:2056-2061`(`_last_mech_detail` 读 `executor.last_detail`)。
  - `cw_screen_buy_cards.py:1143`(shop_action_op_for 消费点)——实际 :1148。
  - `cw_state.simulate`——`kernel/cw_state.py` 模块已不存在(simulate 现住 `cw_vocab.py:933`);§2.6 依据②整段引用失效模块路径。
  - 「17 类动作两条链」——两条分派链实际辖 16 类(DeployMove 等 16 个,见 prep_actions.py:1006-1053);词表全集 18 类(PREP_ACTION_TYPES,cw_prep_actions.py:204-210);且 OpenShop 根本不经执行器(cw_screen_prep.py:2037 流程层截流,prep_actions.py:810-812 注释明示)。三个数字与一个结构事实都不对。
  相比之下 prep_actions.py 自身的锚(:660/:715/:720-744/:745-746/:995/:1030/:1272/:1278/:633)全部核实无误——失真集中在 cw_op/cw_screen 侧,像是按 T-201 拆分前的旧布局写的。
- **证据**:见各条括注;`operations/cw_op/cw_action_base.py`(全文 35 行);`operations/cw_op/cw_shop_actions.py`(全文 56 行);`operations/cw_screen/cw_screen_prep.py:2037`。
- **建议修法**:逐条重锚到现文件现行号;「17 类」改为与 PREP_ACTION_TYPES 一致的口径,并注明 OpenShop 走流程层编排不经执行器这一结构事实(它直接决定批3 的注册表形态,见 F8)。

### F6【design.md §2.6 LevelUp 粒度衔接】两步走的前提在活跃路径上不存在;商店先例不可平移;「两形态择一」= 未定稿
- **攻击内容**(本条同时是核二硬规则2 违例,双记):
  1. **前提无据**:设计的条件分支建立在「发射面幂等键(action_key)拦截逐帧重发」上。核实现役活跃备战环(cw_screen_prep 决策循环 :1667-1785)**不存在任何按 action_key 的重发拦截**——action_key 的消费点只有校验日志(:1704-1706)、记账键(:1726)、执行日志(:2057/:2061);「连败→恢复→屏蔽」整套机制已随内环拆除退役(cw_screen_prep.py:1567-1570 明文)。拦截机制不存在,则条件分支永远走步骤①,fallback ②是死条款。
  2. **商店先例不可平移**:商店侧「多击序列由决策循环逐帧重组」成立的前提是商店投影对 LevelUpShop **已建模**(bridge.py:233-241,逐动作 `apply_shop_action_logic` 推进,击数恒 1)。备战侧 LevelUp 在投影面**未建模**(`_project_prep_obs` 未建模面清单明列 LevelUp,cw_screen_prep.py:912-915)→ 每发一击即投影未建模 → visit 终结 → 外循环 heavy 重观察。逐帧单击的真实代价 = **每单击一次全套 heavy 重观察**(识别链整跑一遍),与商店先例结构不同。若要避免,就得给备战投影补 LevelUp 的 xp/cap 推进建模——这是设计从未提及的新语义工作。
  3. **下游消费面未分析**:执行器内连点环现辖授权逻辑(血闸 blood_xp_gate、金地板逐击查金、击数推导 clicks_to_next_level/blood_xp_full_clicks,prep_actions.py:1394-1527);改逐帧单击后这套授权归属(随发射面上移到 mandate?留守执行器单击前检?)未写。发射面侧还有一整组假设「一次 LevelUp 发射 = 升完一级」的机制:M2 stall 非变集 {LevelUp}(mandate.py:133-135)、授权形态 'level' 的 posture_unfulfilled 对账(mandate.py:837-860/:929)、m1p 同帧 LevelUp 抑制(:1504)、RunTools/LevelUp 同帧执行序回排(entry/mandate)——逐帧化后语义全要重推,设计零覆盖。
- **证据**:cw_screen_prep.py:1567-1570/:912-915/:1667-1785;mandate.py:133-135/:837-860/:905-929/:1481/:1504;bridge.py:233-241;prep_actions.py:1394-1527。
- **建议修法**:先把事实写对(无拦截机制;备战投影未建模),再在 §2.6 **定死一个形态**:要么「①逐帧单击 + 批2 同批给备战投影补 LevelUp xp/cap 推进 + 授权归属逐项点名」,要么「②执行器有界连点保留为动作内部步骤(screen_op.md §2.3 先例,零行为)」。禁保留「若…则…择一」句式。

### F7【design.md §2.6 遥测/journal schema、landing.md §3.2 判据】跨批容缺口径不覆盖「改名 + 值域漂移」
- **攻击内容**:设计的兼容口径 =「字段带默认值、类型消费全向后兼容、判读工具容缺读取」——这套口径是为**加字段**(SellBench.reason 先例)设计的,管不住**改名**:prep 域 journal/receipt 行的 SellBench 载荷从 `slot`(物理 1-9)变 `bench_idx`(下标 0-8)。判读侧跨批混读同一 `__type__='SellBench'` 时,同语义字段分裂成两个键且**数值基准还差 1**(旧档 slot=3 = 新档 bench_idx=2)。「容缺读取」只解决新读端读旧档缺键不炸,解决不了跨批对读的语义对齐——单局复盘/跨局对照若横跨本迭代前后档,卖出槽位口径会静默错位。设计只字未提值域漂移与跨批判读的申报口径(对比:schema.py 对 2026-09-13 状态收敛批的旧档有显式「旧档案兼容窗(读侧,申报)」段,可循此例)。
- **证据**:`telemetry/schema.py:256-283`(serialize_action 载荷键 = dataclass 字段名 + __type__);`telemetry/op_journal.py:173`;`telemetry/schema.py:246-250`(旧档兼容窗先例);`kernel/cw_vocab.py:318-327`(双族值域:族B 1-9 / 族A 0-8)。
- **建议修法**:§2.6 补一段「跨批判读口径」:列出改名键清单(slot→bench_idx 等)、值域换算式(旧值−1)、判读工具读侧的双键兼容窗落点(telemetry/query.py + tools/cw),并申报「本迭代前后档 SellBench/SellDeployed/DeployMove 行不可直比,须按换算式归一后比较」。

### F8【design.md §2.4/§2.5 OpenShop】OpenShopOp 的 execute 体与 read_only 两形态无定义;流程层编排与工厂的关系未定
- **攻击内容**:专项质疑面证实:OpenShop 现役不经执行器分派(cw_screen_prep.py:2037 截流 → `_open_shop_phase` 流程层编排 :2405-2450,read_only=True 走 CwOpOpenShop→heavy 观察→CwOpCloseShop→回备战,read_only=False 走商店单动作循环)。设计 §2.4 给 OpenShopOp 置 terminal=True,但:(a) 它的 execute 体是什么?流程编排是画面 op 的流程职责,塞进动作 op 违反设计自己的「执行包络/流程编排留守」划分;留空则注册表里是个不可执行的死行。(b) 注册表按词表类一行,OpenShop 一个类带 read_only 两个形态——一行怎么表达两形态语义?(c) 现行结束判定 StartBattle 与 OpenShop 的等待时长不同(wait=3 vs wait=1.0,cw_screen_prep.py:1760-1767),只把类型集合换成 terminal 布尔属性,时长差异由谁承载未写。
- **证据**:cw_screen_prep.py:2037/:2405-2450/:1760-1767;prep_actions.py:810-812。
- **建议修法**:§2.4 显式写:OpenShopOp 注册为「terminal 承载行」,execute = 显式抛错或固定 detail + emitted=False(流程层截流在前,该行本就不可达,与 ControlFlowOp 同款防静默纪律);terminal 属性之外补「终结等待时长随 op 类属性」或保留消费点按类型查表的现状并锁等价。

### F9【design.md §2.2/§2.4 StartBattle】「恒 True 零判效」基类契约与 StartBattle 出战链 as-built 直接冲突,无例外条款
- **攻击内容**:批1 把「恒 True 零判效」docstring 契约上收基类(§2.2);批3 要求 StartBattleOp.execute = `_start_battle` 逐字迁移。但 `_start_battle/_launch_attempt`(prep_actions.py:1563-1701)含:落地判效轮询(6×0.5s 查备战标识消失)、失败原样重发(长按下加固)、连败停机留证(stop_running + flag,`_launch_dead_escalate`)、免战子态 fallback(按钮-跳过)、未达上限警告处理。逐字保留 = 该 op 违反基类契约且内部含在册判效面(prep_actions.py:639-641 明示这是批4 挂账的 A6 出战链判效面,候消费端同退役);遵守基类契约 = 砍掉重发/停机/免战防线 = 行为变化,与「全程零行为」矛盾。设计对这对矛盾零字处理——批3 实现者撞上必停手。
- **证据**:prep_actions.py:1563-1701/:639-641/:90-100;design.md §2.1/§2.2/§2.4。
- **建议修法**:§2.4 给 StartBattleOp(及经 executor 的出战链)显式例外条款:基类契约的在册例外,判效/重发/停机面 as-built 保留,退役批挂账(统一观察架构 A6 批4)指向写明;或者把「重发+停机」明确定为「发射位内部步骤」纳入动作语义,两者选一写死。

### F10【design.md §2.6 换算归属、landing.md §3.2 判据】「调用点换算全数消灭 / slot-1 型换算零残留」按字面不可达成
- **攻击内容**:容器下标规范系只统一了**动作词表**;底层 `BenchChar.slot` 仍是物理 1-9,被 tracked 账(exec_state)、部署机 CwScreenDeploy、装备穿戴计划、PrepObservation SIFT 观察全链共享。发射面要产 bench_idx,要么在发射点做 `bc.slot - 1`(这就是一条 slot-1 换算,与判据冲突),要么观察面给容器下标平行表示(新表示,设计未提)。执行边的 tracked 同步、screen_info 槽位中心取坐标也仍需下标→物理换算。「换算全数消灭」真实含义是「换算从散点调用收拢到观察/执行两个边界」,不是消失;landing 批2 判据「调用点 slot - 1 型换算零残留」按字面执行会逼实现者删掉必须存在的换算。
- **证据**:`kernel/cw_prep_actions.py:258-263`(BenchChar.slot 1-based);prep_actions.py:1278/:1289/:1298-1299/:1345-1371(tracked/坐标消费);mandate_v1 发射点 9 处 `SellBench(slot=bc.slot)`(mandate.py:888/:1148/:1251,entry.py:551/:821/:832/:1138/:1192/:1204)。
- **建议修法**:§2.6 与批2 判据改为「发射/决策面产容器下标;物理换算仅存于观察写入边与执行坐标边,且各只允许一处(函数化)」;验收改查「换算函数唯一 + 散点换算零残留」。

### F11【design.md §2.6 词表模块归一】SELL_BENCH_REASONS / SELL_BENCH_ORPHAN_REASONS 常量新居未定;牵动 sim/checks(「sim 只加锁不改实现」边界)
- **攻击内容**:两个值域闭集现住 cw_prep_actions(词表模块);sim 侧检查器(sim/checks/suspects.py:106、ledger.py:550/:994)import 之。归一后若常量随词表迁入 cw_vocab,sim/checks 的 import 断裂 = sim 侧被改(与「sim 侧只加锁不改实现」及批2 文件面无 sim/checks 冲突);若留守 cw_prep_actions(已「退役词表职责」的模块),归一后的单一词表主张留尾巴。设计对这两个常量只写了「值域不变」,没写住哪。
- **证据**:`kernel/cw_prep_actions.py:102-125`;`sim/checks/suspects.py:106`;`sim/checks/ledger.py:550/:994`。
- **建议修法**:§2.6 写死常量归宿(建议随词表迁 cw_vocab,并把 sim/checks 三个 import 点列入批2 文件面显式申报「仅 import 路径翻转,零语义」;或明确 shim 过渡)。

### F12【design.md §2.6 合并类基类承载】统一类的基类/route_tag/action_key_exclude metadata 归属未定义
- **攻击内容**:族B 动作带 PrepAction 基类(kw_only route_tag 字段,bridge.py:279-280 发射位回写;action_key_exclude metadata 排除归因)。统一类住 cw_vocab 后:它还是不是 PrepAction 子类?route_tag 字段还带不带?族B SellBench.reason 的 action_key_exclude metadata 合并后保不保留(族A 的 reason 现在没有该 metadata——若按族A 定义合入,prep 发射的 `SellBench(reason='line_switch_collapse')` 会分裂幂等/记账键,与 §2.6「归因字段不入幂等键」口径冲突)?统一词表的家族树(PrepAction 基座覆盖全动作?Action 联合类型怎么表达?)设计只字未提。
- **证据**:`kernel/cw_prep_actions.py:27-42`(route_tag + metadata);bridge.py:273-281;`kernel/cw_vocab.py:373`(族A reason 无 metadata);`kernel/cw_prep_actions.py:216-234`(action_key 消费 metadata)。
- **建议修法**:§2.6 增「统一词表家族树」小节:基类、route_tag 承载、metadata 逐字段裁定(建议统一类 = PrepAction 后代,reason/convert_reason/auth_basis/route_tag 全部保留 action_key_exclude),并附 action_key 输出前后对照锁。

### 核一·已核实成立的主张(明写,避免「全盘否定」误读)
- **批1→批2 依赖(专项质疑面⑦)成立**:统一 SellBench/LevelUp = 现役族A 类本身(除 F1/F2 的字段申报问题,类身份不变),批1 商店六行(BuyCard/LevelUp/RefreshShop/SellBench/CloseShop/CompTransaction,cw_shop_actions.py:39-46)在批2 后键稳定;SellDeployed/DeployMove 不在批1 表,无冲突。
- **sim 零构造族B 类(专项质疑面⑤)证实**:sim 构造点全为族A(engine_p1.py:880 `SellDeployed(deployed_idx=...)` 等,import 源 = cw_vocab);sim/checks 仅 import 常量(F11 的住留问题)。规范系取族A ⇒ sim 行为零变化的**方向**成立(DeployMove 行按 F3 修正后完全成立)。
- **坐标换算恒等式写对了**:「族B = 族A + 1(bench 域);deployed front idx=slot−1、back idx=4+slot−1」与 cw_vocab.py:326-327 双族对照表逐字一致。
- **退役成员清单全**:EnsureShopOpen/EnsureShopClosed/RunBuyPhase 三者与词表对照无遗漏;BailToOuter(词表已退役)也以 ControlFlowOp 在册覆盖。
- **prep_actions.py 自身的行号锚全部核实无误**(:633/:660/:715/:720-744/:745-746/:995/:1030/:1272/:1278/:1394)。
- **部署面调用点担忧(专项质疑面②的前半)解除**:换血/场内换排(CwScreenDeploy)全链不构造词表类,全仓 grep 零命中,deploy 是原始拖拽——SellDeployed 统一为 deployed_idx 不产生部署面迁移面;真正的消费面在执行器/期望态/投影三处(已并入 F4 文件面清单)。

---

## 二、核二·规范遵循攻击(对照 iteration-design.md §3/§5/§7)

### F13【design.md §2.6 LevelUp 粒度衔接】硬规则2「实现者无需再设计」直接违例
- **攻击内容**:「两形态择一并测试锁,禁第三形态」= 把形态选择推迟到实现期观察后拍板,规范原文「看情况/待定/酌情 = 未定稿」逐字命中。**批2 凭 §2.6 现状不能开工**:LevelUp 一项上,实现者要自行决定 cost 填充源(F2)、血闸/金地板/击数推导归属、投影是否补建模、发射面 stall/授权机制重推(F6)。
- **证据**:iteration-design.md §5 规则2;F2/F6 全部证据。
- **建议修法**:见 F6。

### F14【design.md §2.4+§2.6 批2/批3 语义选择面汇总】「凭这份能开工」试读不通过的其余各点
- **攻击内容**:假扮批2/批3 实现者逐段试读,以下语义选择在设计与权威源里都没有答案:
  1. 统一词表家族树与 metadata(F12);
  2. SELL_BENCH_* 常量新居(F11);
  3. import 翻转策略:shim 还是全翻(F4);
  4. OpenShopOp execute 体与两形态表达(F8);
  5. terminal 化后 StartBattle/OpenShop 等待时长(3s/1s)差异的承载(F8);
  6. StartBattle 基类契约例外(F9);
  7. 落地批2 判据「动作序列对照不变」与 LevelUp 逐帧单击(改变发射序列)的关系——判据无豁免条款,照字面批2 必然验收失败或逼实现者放弃 §2.6 的粒度衔接;landing 需显式写「LevelUp 发射序列按 §2.6 定案形态豁免序列不变判据,以专门锁替代」。
- **证据**:landing.md §3.2 完成判据第 3 条 vs design.md §2.6。
- **建议修法**:逐条补写进 design.md 对应节;landing 判据补 LevelUp 豁免口径。

### F15【design.md 全文】硬规则1「依据就地标注」失真面(F5 锚点组之外的两处主张)
- **攻击内容**:除 F5 的行号锚失真外:「17 类动作两条链」的计数主张(F5)、「发射面幂等键拦截逐帧重发」的前提主张(F6)、「族A 三字段」的字段计数(F1)、「换算全数消灭」(F10)均为无依据标注或与代码真值不符的主张——按卡点细则,未标注/失标注 = 弱点自带坐标,全部命中。
- **证据**:见 F1/F5/F6/F10。
- **建议修法**:随各条修法一并落文。

### F16【landing.md 末阶段 vs 正本更新清单】末阶段依赖漏批4,清单自相矛盾
- **攻击内容**:末阶段「依赖:批1-批3 全部」,但正本更新清明确有一行「统一观察架构 §6.1/§6.2 回填 ← 批4」。按此依赖,末阶段可在批4 前启动,该行永远无法清零,「清单清零 = 收尾完成」的判据结构性不可满足。
- **证据**:landing.md 末阶段节与「正本更新清单」节。
- **建议修法**:末阶段依赖改「批1-批4 全部」。

### F17【README.md 进度】进度阶段数与 landing 不符
- **攻击内容**:README 写「落地:阶段 0/3 done」;landing 实为批1-批4 + 末阶段共 5 个阶段小节。README 是唯一进度源,与阶段唯一源不一致。
- **证据**:README.md:12;landing.md 全文结构。
- **建议修法**:改为「阶段 0/5」(或与 landing 阶段计数口径统一)。

### F18【landing.md 各阶段小节】七件齐核对结果
- **攻击内容**:逐阶段核对七件(范围/设计依据/文件面/依赖/优先级建议/完成判据/验收凭据形式):批1-批4 与末阶段**七件齐**,设计依据指向真实存在的节,固定末阶段在册——该项**通过**。缺陷只有 F4(文件面覆盖不足)与 F16(依赖错)两处,已在核一/本核另条记。
- **证据**:landing.md §3.1-§3.4 + 末阶段,对照 iteration-design.md §3.1。
- **建议修法**:无(除 F4/F16)。

### F19【design.md 全文】硬规则3「无过程叙事」核对结果
- **攻击内容**:全文无「第几轮/已改/本轮」类措辞;卷首用户裁定与承接出处属裁定指针,合规——该项**通过,零发现**。
- **证据**:design.md 全文对照 iteration-design.md §5 规则3 卡点。
- **建议修法**:无。

---

## 三、核三·治本核验(根源两问)

### 结论:方向治本成立;两处表述需要按代码真值收敛后,治本论证才完整

1. **归层成立**:§1 根因归层 = 约定层,判据充分——同名四类差异仅在坐标系约定(双族对照表,cw_vocab.py:315-332),sim 已单边消费族A(构造点实证),两域执行端口分叉非领域必需。修法 = 单一词表 + 单一坐标系 + 执行边换算,修的是约定/表示本身,不是再加一层包装;与统一观察架构 §6.1 词表纪律(「先改契约再落码」「禁适配器私有动作类型」)方向一致,AST 锁正是该纪律「验收挂 AST 扫描」申报(§6.1)的机械化兑现——一致性成立。
2. **批序论证成立**:先归一(批2,独立语义批 + 全仓扫描 + sim seed 锁)后收编(批3/批4,形态批),归因不混淆;批1 注册表先行、批2 键稳定(F12 已核实)。代价申报诚实:批2/批3 会先后两次动 executor 同一批方法(批2 改字段消费、批3 迁体),设计未点出这层「同文件两批税」,但不构成批序否决。
3. **两处折扣**(已在核一立案,治本口径下复述):
   - DeployMove 行不是归一而是重新设计族A(F3)——治本叙事里混入了一段未论证的表示重设计,且与「sim 零改动」冲突;
   - 「调用点换算全数消灭」强于实际(F10)——换算是收拢改归属,不是消灭;治本主张的表述强于方案本体,会被实现者按字面执行出错。
4. **同族问题第二次出现检查**:本迭代不属逐件修症状——「统一动作工厂」就是把「商店工厂/备战分派」两形的根(执行端口无统一契约)一次收口;词表归一同样是把「双族坐标系」这个约定层根一次拔掉。跨件半问通过。

---

## 四、专项质疑面逐条结论(汇总)

| 质疑面 | 结论 |
|---|---|
| §2.6 合并清单与代码真值 | **不通过**:SellBench 漏 convert_reason+顺序不符(F1);LevelUp 漏 auth_basis+cost 填充源未定(F2);DeployMove 签名 ≠ 族A 且 faction 去向未申报(F3);SellDeployed 行成立;换算恒等式写对(核一·已核实节) |
| landing 文件面覆盖 §2.6 改动面 | **不通过**:漏 cw_prep_expect/cw_exec_state/cw_game_state/cw_loop(+import 策略未定)(F4) |
| 判据可验证性 | **不通过**:「动作序列对照不变」与 LevelUp 粒度变更冲突无豁免(F14-7);「slot-1 零残留」按字面不可达成(F10);其余判据(扫描报告/AST 等价比对/sim seed 锁)可验证 |
| LevelUp 两步走 | **不通过**:前提(幂等拦截)在活跃路径不存在、商店先例因投影边界不可平移、择一 = 未定稿、血闸/金地板/stall 授权消费面零覆盖(F6/F13) |
| SellDeployed 统一后部署面调用点迁移 | **担忧解除**:部署面零构造词表类;消费面在执行器/期望态/投影,批2 文件面修正 F4 后可覆盖 |
| OpenShop read_only 两形态 / StartBattle fallback / DeferSpheres 控制流 | DeferSpheres **通过**(设计与现行 dispatch 软拒逐字对齐);OpenShop **不通过**(execute 体/两形态/等待时长未定,F8);StartBattle **不通过**(基类契约矛盾无例外条款,F9) |
| 遥测/journal 改名跨批判读 | **不通过**:容缺口径只管加字段不管改名+值域漂移,跨批混读同 __type__ 异值域(F7) |
| sim「零改动」主张 | **方向证实**:sim 零构造族B、统一类=族A ⇒ 引擎/投影行为零变化成立;DeployMove 行按 F3 修正后主张完全成立(现行写法自相矛盾) |
| 批1/批2 注册表键依赖 | **成立**(核一·已核实节) |

---

## 五、三核结论

- **核一·无前提:不通过**。合并清单四行里三行与代码真值不符(F1/F2/F3);批2 文件面漏至少四个必改文件(F4);一处关键主张(LevelUp 幂等拦截前提)在活跃代码中不存在(F6);一组依据锚点指向已不存在的布局(F5)。设计的主干结构(工厂/注册表/批序/规范系)与代码事实对得上,但「实现者照着核真」所必需的细节层失真密度已超过可施工线。
- **核二·规范遵循:不通过**。硬规则2 被 LevelUp「两形择一」直接命中(F13),另有七处语义选择无答案(F14 清单);硬规则1 失真面见 F15;硬规则3 与 landing 七件齐**通过**(F18/F19 零发现);流程面两处小错(末阶段依赖漏批4 F16、README 阶段数 F17)。
- **核三·治本:通过(附修正条件)**。归层正确、方案修约定层之根而非包装、批序论证成立、与统一观察架构 §6.1 词表纪律一致;但 DeployMove 行的表示重设计与「换算全数消灭」表述须按 F3/F10 收敛,否则治本叙事与方案本体不一致。

## 六、定稿门槛判断(距「实现者无需再设计」还差哪些)

定稿门槛 = 攻击收敛 + 试读过;现状 = 草案,维持。收敛前必须补齐(按批归位):

1. **合并清单按代码真值重写**(§2.6):四行统一类一律「现役族A 类原样吸收」,字段全集/顺序/metadata 逐字列明(SellBench.convert_reason、LevelUp.auth_basis、DeployMove 的 faction/to_row 裁定);统一词表家族树(基类、route_tag、action_key_exclude)写死(F1/F2/F3/F12)。
2. **LevelUp 粒度定案**(§2.6):删「择一」句式,定死形态;若取逐帧单击,须同批定义备战投影 LevelUp 建模、cost 填充源、血闸/金地板/击数推导归属、发射面 stall/授权机制(M2 非变集/posture 对账/同帧抑制)的逐项处置(F6/F13)。
3. **StartBattle/OpenShop 两行显式裁定**(§2.4):基类契约例外条款(判效/重发/停机 as-built 保留与退役挂账指向)、OpenShopOp execute 体与两形态表达、terminal 等待时长承载(F8/F9)。
4. **批2 文件面扩围 + import 策略**(landing §3.2):补 cw_prep_expect/cw_exec_state/cw_game_state/cw_loop(+decision_assembly 视扫描);shim vs 全翻二选一;SELL_BENCH_* 常量新居(F4/F11)。
5. **判据修正**(landing §3.2):「动作序列不变」加 LevelUp 豁免口径;「换算零残留」改为「换算函数唯一 + 散点零残留」(F10/F14-7)。
6. **跨批判读口径**(§2.6):改名键清单 + 值域换算式 + 判读工具兼容窗落点(F7)。
7. **锚点勘误**(§1/§2):cw_action_base/cw_shop_actions/cw_screen_prep/cw_screen_buy_cards/cw_state.simulate 全部重锚;「17 类/两条链」改为词表 18 类 + 链辖 16 类 + OpenShop 流程层截流的事实口径(F5)。
8. **流程面**:末阶段依赖补批4;README 阶段数对齐(F16/F17)。

上述 1-7 全部落文并复过一轮试读(逐阶段问「凭这份能否开工」),才够到定稿门槛。
