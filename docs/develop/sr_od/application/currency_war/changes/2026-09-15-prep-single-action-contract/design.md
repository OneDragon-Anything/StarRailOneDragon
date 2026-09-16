# 备战契约接口收口为单动作(总纲)

## 0. 元信息

- 迭代目标:备战决策契约接口 `CwStrategy.decide_prep_screen` 收口为「恰返回一个动作 / None」,对齐画面 op 契约规范「每个画面 op 一个接口、只产出一个动作」(用户 2026-09-15 策略基座规范核查;商店 `decide_shop_action` 已是单动作形状,备战是唯一遗留)。
- 状态:定稿(熔断收口:残余发现全部修复或登记归属将来批,用户裁定收口)
- 文档清单:无详设(单文档;§2 即完整设计)

## 1. 问题与动机

- 现状症状:契约接口签名返回 `list[CwAction]`(`strategies/impl/cw_strategy.py`);生产消费端(`operations/cw_screen/cw_screen_prep.py` 两处决策循环,~L2029 主循环与 ~L2234 `lifecycle_decision_cycle`)每帧只取 `actions[0]`,列表尾部动作逐帧丢弃;空序列 = 「本帧无动作」交回外循环。接口形状(波批序列契约,2026-09-03 冻结)与消费语义(单动作循环,设计正本 = `screens/op-layer.md` §1.1)不符——形状是单动作循环迁移(2026-09-06 落码)未收完的遗留。
- 根因归层:**表示层**(接口形状)。波批时代的「一次决策产整波」表示残留;消费语义已迁移,表示未跟上。
- 基类 docstring 现行文本已是 as-built 口径(单动作消费/已退役语义标注);landing 3.1 ① 的 docstring 改写 = 新契约语义落位,非口径修复的重复处理。
- 解决到哪:契约面形状收口 + 消费端形状校验改写 + mandate_v1 边界适配。
- 明确不解决(防外溢):
  - 「只接收 game state」的字面化——输入经 session 黑板(容器 BoardState/obs_frame)是有意设计,决策的历史依赖性(意向状态机/defer 计数)需要跨步状态载体,规范核查已认定精神符合,不动;
  - 决策核内部发射组织(`entry.emit` 三遍编排、帧稳定分类、`_merge_ev_before_frame_end` 合并)——它们是首项选择序的活机制(取舍见 §3 备选 B);
  - 商店 `decide_shop_screen` 驱动器(sim 引擎/回放/序列锁消费整序列,合法多动作面)与 pick 族(单选返回,已合规);
  - 决策核内灭失契约工作副本引用族(`entry.py` ≥8 处「契约 v2 §3.2/§3.3/契约 §2」、`mandate.py` L1299「契约截断点」等)——既有债,归决策核行为变更大批顺带收敛,本批核内零改动边界不含(缓解在位:`entry.py` 模块头已就地自证契约工作副本灭失并重锚 `flow/action_exec.md` §1);
  - `changes/`/归档稿死指针族的**面外存量**(同族指针散布于注册表/适配器/criteria/账本/谓词等 ≥10 文件:如 `cw_action_registry.py`、`mandate_v1/adapter.py`、`criteria/contracts.py`、`criteria/levelup.py`、`criteria/sell.py`、`mandate_state.py`、`economy_cycle.py`、`sell_gate.py`、`statefn/predicates.py`)——既有债,本批只清四文件面内实态 5+4 处;面外存量归将来的全仓注释卫生批顺带,不在本批扩面;
  - 正本路径笔误族面外存量(`flow/action-logic-state.md` 误写全仓 7 处,面内 3 处本批清,面外 4 处 = `kernel/cw_game_state.py`×3 + `kernel/cw_vocab.py` L801)与已删 `decision_v2` 包死引用族面外存量(`telemetry/schema.py` L469、`cw_equip_wear_plan.py` L256、`cw_registry.py` L1317、`cw_screen_planner.py` L197)——同归全仓注释卫生批顺带;
  - `mandate_v1/shop.py` L758 同措辞句(「波批优先级 逐帧取首项」,flow.py 收敛句的语源本体,语义仍真)不在本批文件面,归商店线判据批顺带。

## 2. 方案

### 2.1 接口语义

签名变更(`strategies/impl/cw_strategy.py::CwStrategy`):

```python
@abstractmethod
def decide_prep_screen(self, session: StrategySession,
                       config: CurrencyWarConfig) -> CwAction | None:
```

- 返回**恰一个动作**(`CwAction` 实例)= 本帧要执行的那个动作;执行序概念随单动作循环消亡。
- 返回 `None` = 本帧无动作可发,交回外循环重观察(连续 None 的 stall 兜底归外循环防线,语义与现行空序列分支逐一等价;现行分支 = `cw_screen_prep.py` 空批 `round_success` 交回)。
- 契约成员数不变(每局冷建 2 + 分画面决策入口 11,abstract 12 + 工厂 1 = 13;单一源 = `flow/README.md` §2.2)——只改备战入口的返回类型。
- 「观察帧缺失即抛错」「生命周期机制归流程侧」两条现行契约纪律原文保留,不变。
- 基类 docstring 定稿关键句(照抄语义,防旧口径关键词回潮;现行 as-built 文本中的形状遗留注/已退役语义注随本批删除):「备战画面黑板决策接口(单动作契约,返回 ``CwAction | None``)。输入 = ``session.prep_obs_frame``(备战观察结果由观察层写入)。返回**恰一个动作** = 本帧要执行的那个;``None`` = 本帧无动作可发,交回外循环重观察(连续 None 的 stall 兜底归外循环防线);禁用 None 表达控制流——画面转移一律走终结动作(开箱/开店/出战等)。「观察帧缺失即抛错」——黑板模式下决策读到 None 帧 = 观察层失约。生命周期机制(幂等键 ``action_key``/执行失败记忆/stall 门/强制出战)归框架流程侧,策略器不自实现。」
- 基类模块头 as-built 失真句随批收敛(L4-5「唯一内置具现 = ``DecisionV2Strategy``(注册桥在 ``strategies/decision_v2_strategy.py``)」——类与注册桥文件均已删):→「唯一注册核 = mandate_v1(注册壳 = ``strategies/mandate_v1_strategy.py``)」(注册面封闭集依据 = `flow/README.md` §2.1)。

`None` 通道的三点依据(为什么保留 None 而不是改成分域同构的「无动作 = StartBattle」):

1. **备战域「本帧无动作」是已声明的合法通道**:op-layer §1.1 分域表述——「None/空批通道不表达控制流(备战域空批 = 『本帧无动作』合法交回,与商店域『空批已由 CloseShop 终结取代』分域表述)」。本迭代把空批形状换成 None,语义零变化(该正本句的措辞随本迭代在 landing 3.3 收口为 None 口径)。
2. **mandate_v1 常态路径不产空;防御边产的空与新 None 通道消费端逐义等价**:决策核 emit ⑥ 空则补 StartBattle(`entry.py`「⑥ 无动作 ⇒ 出战」段),常态无空。可达空返回边 = `truncate_frame_stable` 的防御边——条件续复检在首位 `SellBench`/`DeployMove` 引用失效槽位时截断为空(该复检为真实缺陷类 R196 症5 而设,属活防线);unknown 分类首位边不可达(决策核可发射的 17 类全被四分类覆盖;备战词表全集 18 类含 OpenBookcard 系画面 op 侧发射、不经决策核——entry.py 头注「18 类」系既有计数漂移,本批不动)。该空边现行走空批 `round_success` 交回,改后走同义 None 分支,行为零变化;同时 None 作为契约面为第三方策略保留「既不出战也不动作」的等待表达自由(B4 条款,基类 `create_state` 缺省 None 同源)。若把无动作折叠进出战,等待态被强制变成出战态 = 契约层面收窄表达力。
3. **StartBattle 是受判据辖制的决策动作**(出战标准 = `strategy-docs/26_battle_settlement.md`),不是「无动作」的缺省替身;op-layer §1.4 的「备战恒可用终结 = 开战」说的是动作空间恒含可发射的出战,不等于「无动作必须表达为出战」。

### 2.2 消费端改写(两处同构)

`cw_screen_prep.py` 两处决策循环(主循环 + `lifecycle_decision_cycle`),每处把现行段(decide 调用 → F3 形状校验 → 空批分支 → 取首项)改为:

```python
try:
    result = match.strategy.decide_prep_screen(session, config)
except Exception as e:  # noqa: BLE001  策略异常 = 本轮 fail(外循环 retry 链兜)
    log.warning(f'[cw!][director] decide_prep_screen 异常: {e}')
    return self.round_fail(status=f'策略决策异常: {e}')
if result is not None and not isinstance(result, CwAction):
    log.warning(f'[cw!][director] 策略输出非 CwAction|None: '
                f'{type(result).__name__}')
    return self.round_fail(status='策略输出非 CwAction|None(F3)')
if result is None:
    # None = 本帧无动作可发,交回外循环重观察;
    # 连续 None 的 stall 兜底归外循环防线。
    return self.round_success('本帧无动作,交回外循环重观察', wait=1.0)
action = result
```

- **决策调用的 try/except 异常包装与 warning 行原样保留**(策略异常 → 具名 round_fail 交外循环 retry 链;现行实态 = 主循环与 lifecycle 两处同构),仅 F3 分支的 status/warning 文案随新形状改写。
- 形状校验保持**守卫断言语义**(非法返回 = 策略器 bug 响亮暴露,禁静默跳过;依据 = op-layer §1.3 守卫断言与对账边界)。
- 死口径注释/文案同批收敛(逐处点名,实现者不再自行判断改不改):
  - 两处循环的「空批合法(契约 §4…)」注释——「契约 §4」指向已灭失的契约工作副本,改写为 None 语义注释;
  - 两处循环 F3 参数校验注释的「契约 §2:参数非法交回留证…」(与 §4 同一灭失副本)→ 删死引用、保留语义自足表述(「参数非法交回留证;执行前输入契约检查,非动作后判效」——不重锚新指针:action_exec §2 无此语义,活正本 = `screens/prep.md` §4);
  - `lifecycle_decision_cycle` docstring 整句定稿——首行死指针「(架构设计 §5.1 后三段逐动作迭代)」(§5.1 指向已灭失工作副本)随批删除;终结出口枚举定稿:「终结出口语义 = 无动作(None)/参数非法/出战(发出即终结)/开店切换/访问上限」(删「空批」→ None 口径;删「控制流」——控制流类动作已整体退役出词表;删「逻辑态未建模」——保守回退分支已随 R9 删除,孪生死口径);
  - 主循环决策段头注释块(在 §2.2 码块替换段之外,L2004-2014 区域)整块定稿——删「三遍编排序保持(决策核输出逐帧取首项 = 单动作选择序,输出等价系条件命题——帧级锁按锁纪律重推)」(消费端不再取首项,整句过期)与「逻辑态未建模的动作同判保守回退」(R9 已删分支),定稿文本:「③④⑤ 单动作决策循环(ADR-0517 迁移批;前身份 = 序列消费 + 每动作落地后 heavy 重观察的保守口径)。新形态:入口 heavy 一次建期望态 → 逐动作『决策(黑板=逻辑态)→ F3 校验 → 期望态计算 → 执行 → 逻辑态直写』循环,循环内零读屏。已知画面出口(OpenShop/StartBattle/OpenBox)= 终结 op,执行即本访问结束交回外循环(下次入口重观察)。B1 拆除(用户裁定 2026-09-10):验证段+恢复原语分支退役——动作机械执行(端口无成败回执),无进展治理归外循环 stall 防线(F2),落地判定归观察侧 reconcile。」;
  - 两处循环的循环外预声明 `actions: list = []`(L2016/L2220 区域)随改写定名 `result` 成死变量,删除(ruff F841 在项目 select 内,通用工程门必红);
  - **收尾机械扫尾(防枚举漏孪生,结构性判据)**:四文件全文 grep 关键词族(`契约 §`/`契约 v`/`序列契约`/`序列发射`/`空批`/`取首项`/`drain`/`unified-action-factory`/`design.md`/`DESIGN.md`/`统一设计稿`/`action-logic-state`),命中逐处三分处置——已收敛(本批点名处)/保留申报(写明理由,如「决策核内发射组织语义,非流程侧契约」)/新发现(补收敛);禁未处置命中。枚举清单可能不全,本扫尾是完备性的机械兜底;
  - `changes/` 引用注释实态 5 处(L664「unified-action-factory 批2b」、L984「unified-action-factory…§2.6」、L2103-2106 与 L2325-2326「design.md unified-action-factory §2.4」、L2537 裸「design.md §2.6」)——「代码禁引 changes/」铁律的既有债,随本批注释收敛**全部清理**(同族同批清,不留保留申报口子):删 changes/ 指针、保留语义表述(「终结集与等待时长改读注册表 op 类 `terminal`/`terminal_wait` 类属性,消费点经注册表读类属性,禁消费点私表」等已自足);正本路径笔误同族实态 3 处(L985/L1000/L1187;首处语句起于 L984 注释行)顺带修正(「flow/action-logic-state.md」→「game_state/action-logic-state.md」);扫尾关键词族因此补 `action-logic-state`;扫尾关键词族因此补 `design.md`(裸 design.md 指针无其他词可兜);
  - `bridge.py` 死引用(逐处处置见 §2.3)。
- 其余段零变化(枚举):**决策调用异常包装段**、F3 参数校验 `validate`、期望态记账、执行、终结判定、逻辑态直写、段序号置位。
- 第三方兼容(B4):实现旧 list 形状的策略(无论 list 空否)在新形状校验处 fail(谓词 = 非 None 且非 CwAction)——注册面封闭集 = {mandate_v1}(依据 = `flow/README.md` §2.1 管理器行),无第三方在册;响亮暴露正是契约改版的预期防线,不做静默兼容垫片。

### 2.3 mandate_v1 边界适配

`strategies/impl/mandate_v1/bridge.py::MandateV1Strategy.decide_prep_screen`(当前唯一具现;flow 中间 ABC 保持 abstract 不实现):

- 决策核调用不变(`decide_from_turn(obs, turn, session, config, registry=...)` 仍返回 list),边界取首项:

```python
actions = decide_from_turn(obs, turn, session, config, registry=self.registry)
return actions[0] if actions else None
```

- 决策核(`entry.emit` / `decide_from_turn` / 帧稳定分类 / 三遍合并)零改动。理由:
  1. 三遍编排的相对序决定首项(EV 卖面整体插到首个截断点/终点之前,`_merge_ev_before_frame_end`;R197 症1 修复语义)——核内 list 是**首项选择序的活来源**,不是死形状;
  2. 帧稳定分类/截断在 mandate_v1 包内 4 处真实调用(bridge.py 截断发射 1 处、entry.py 内部 2 处、mandate.py M7 发射序回排 1 处),另有 mandate.py 注释提及 3 处(独立申报注释 2 处:L1299 凑息卖接线位、L1753 M1″ 生产发射臂段;调用点就地说明 1 处:L1951-1957 M7 回排段)——耦合实证在包内成面,不是孤立点;
  3. 行为零变化要求最小证明面:bridge 边界「取首项」与消费端原「取首项」同源同位,行为逐位等价。
- `bridge.py::decide_prep_screen` docstring 同步改写,死引用逐一收敛(处置与消费端「契约 §4」同款:灭失副本引用改语义表述或改指现行正本节):
  1. 首句「(契约 v1/v2 接口;序列决策契约正本 = flow/action_exec.md §1)」——契约工作副本已灭失,且 action_exec §1 实为词表与注册表节,双重死引用;
  2. 「经帧稳定截断(契约 §3.2 逐类判 + §3.3 fail-closed)」——§3.2/§3.3 为灭失契约工作副本节号;同句前半「输出 = ``list[CwAction]``(执行序=列表序)」一并整句改写——docstring 核心段以下方定稿关键句**整段替换**,不逐点拼补(与 §2.1 基类 docstring 同款待遇);
  3. 「入口内务 = 结算惰性 drain + 备战帧代次消费」——结算惰性 drain 已删除(实码只调帧代次消费,`flow.py::_consume_prep_direction_frame` docstring 自证);
  4. 类级三处:`DESCRIPTION`「序列契约 v2 帧稳定截断发射」→「单动作循环发射(帧稳定截断为决策核内发射组织,非流程侧契约)」;裸「§4.1」两处(模块 docstring 首段 L3、类 docstring 第二段 L81「pick 族缺省实现(基线本体零改动,§4.1)」)→ 均删括注/改语义表述(指涉的方案节已灭失;「config 切 strategy_id 即换核」「pick 族缺省实现(基线零改动)」已足表意);
  5. 同族残留三处(未改行,逃过 diff 域判据,显式点名):模块 docstring L14「契约 §5 职责分界」(同族灭失契约工作副本引用)→ 改语义表述(如「生产路径职责分界:画面 op 只写黑板 + 调一个决策入口」);模块 docstring L9 引已删除的 `decision_v2/adapter.py` 作分拆先例(整包已删,先例指针死)→ 改语义表述或删;类 docstring 首句「三遍化决策序(证明→骨架→EV)+ 序列发射」→「…+ 单动作循环发射」。
- `flow.py::decide_shop_action` docstring 顺带收敛两处(docstring-only 零行为;同 docstring 孪生):L695-696「选择序 = 既有波批优先级 逐帧取首项」→「选择序 = 决策本体候选扫描序,逐帧恰取一个动作」(商店决策本体 = mandate_v1/shop.py 顺序候选扫描,无 entry.emit 式发射组织;现行句「波批优先级」语源属实,仅换单动作口径,不虚构发射组织语义);L699「入口内务 = 结算惰性 drain + 帧代次消费」→「入口内务 = 帧代次消费(:meth:`_consume_shop_direction_frame`;方向刷新在决策读视图之前完成,ADR-0583 内化锚)」。另:flow.py L202-203「方法体逐字平移自 ``decision_v2/strategy.py``」(整包已删)→ 改语义表述(「平移自已退役的 decision_v2 决策包,行为锚见各方法 docstring 与 sim 契约锁」)。
- `flow.py` 面③出辖观察件注释块的已归档设计稿指针四处顺带收敛(L105「p2_blood_band_unified_design/DESIGN.md §2.3-5(a)」、L112「统一设计稿 §4-8」、L133「统一设计稿 §5-F4」、L139 裸「§4-8」;指向 .debug 归档 gitignore 稿 = 死指针):判据语义已自足于代码,删指针或改语义表述。
- `flow.py` 两处删除声明墓碑(L422-423「原前置的结算惰性 drain 已删除」、L430「结算槽 drain 已删除」)系删除声明墓碑(扫尾词族会命中),**保留申报**——语义为现行事实的出处说明,非死口径,不改。
- `decide_prep_screen` 新 docstring 关键句定稿(核心段整段替换,不逐点拼补;防旧口径关键词回潮):「备战画面黑板决策(单动作契约接口,返回 ``CwAction | None``)。输入 = ``session.prep_obs_frame``(缺失即抛错)。输出 = 决策核发射序列的**首个动作**;空序列(含截断截空)→ ``None`` = 本帧无动作。帧稳定截断为决策核内发射组织,非流程侧契约。入口内务 = 备战帧代次消费(方向刷新先于三遍编排)。」

### 2.4 sim / 回放影响:零

- sim 引擎唯一决策入口 = 商店决策面,prep 面在 sim 无实体真值源(依据 = `flow/README.md` §2.3「sim 消费面注记」);
- `cw_replay --diff` 只重放商店决策面(依据 = op-layer §4 次门表述),本批改动对 replay 逐位无感;
- `tools/cw/replay_to_md.py` = 离线记录渲染工具(按 decisions 记录流渲染备战/商店/补给三类 op 段),不调用备战契约接口,零影响。
- **可观测性声明**(对齐 strategy-work §4 A/B 申报纪律):本批改动层 = 契约形状 + 流程消费端,sim 结构性不可见,不可作 A/B 判据;验证 = 契约锁 + 实机(§2.6)。

### 2.5 测试与锁

- 在册锁盘点:测试仓 `decide_prep_screen` 消费面仅 `test_cw_p2_blood_band.py` 的 abstract 桩子类(`*a, **kw` 签名,形状免疫);全仓 grep 无断言 list 形状/空批文案的锁。在册锁零更新义务。
- **新增契约形状锁**(测试仓新增用例,锁 docstring 出处 = `flow/README.md` §2.2——3.3 正本更新后的备战接口行;指针纪律见 landing §3.2/§3.3):
  - mandate_v1 具现:有动作帧 → 返回恰一个 `CwAction` 实例(且 = `decide_from_turn` 输出首项);
  - 空发射态构造(决策核返回空 list 的桩/直调路径)→ 返回 None;
  - 非 None 非 CwAction 的非法返回 → 消费端 F3 fail(消费端守卫锁,可用桩策略)。
- L1 快速集全绿(命令 = `uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`。注:CW skill「测试分层」行路径 `…/sr_od/app/…` 系笔误、其 `legacy_baseline` 标记已死(全仓零命中,`-m` 与 `not slow` 恒等),两处均已在 skill 反馈队列在册候裁,以本行内联命令为准)。

### 2.6 验证(行为零变化声明)

- 本批 = 纯形状收口:决策核零改动、bridge 取首项与消费端原取首项同源、空序列→None 逐义映射。行为等价不依赖 sim 分布证据(§2.4 已声明 sim 不可见),依赖**代码等价论证 + 契约锁**。
- **预期判读面文案变化申报**(非行为变更):空批分支 `round_success` detail 两处「空批(本帧无动作),交回外循环重观察」→「本帧无动作,交回外循环重观察」;F3 形状拒绝 warning/status「策略输出非 list[CwAction](F3)」→「策略输出非 CwAction|None(F3)」。已核无工具/测试/哨兵依赖旧文案(测试仓与 tools/ 零命中;哨兵实态 = `.dsh/skills/sr-od-currency-war-dev/scripts/` 4 件,亦零命中),journal 判读遇新文案形态不记异常。
- 实机烟雾一局(流程回归哨兵,非策略验收;分工依据 = strategy-work §4 实机/sim 分工)。判读锚点开跑前写死:
  1. 备战节点无新增 stall 兜底触发/执行失败安灯/未知画面兜底;
  2. 备战发射相关分键分布与改前基线同型,无新增异常分键(上款申报的文案变化除外)。键族写死 = `cw4_counters` 真实计数键族:`emitter_*`(截断/丢弃)、`deploy_emit_*`/`deploy_exec_*`、`t1_interest_prep_emit`、`wanted_leg_*`、`m1p_*`、`sphere_defer_*` 等,以基线局 journal 实际出现键为准(`prep_box`/`prep_tome`/`prep_spheres` 系 Emitted.reason 路由标签,非计数键,勿 grep)。基线来源 = 遥测账本查询(`telemetry/journal_query`)改动前最近数局实机局;比对口径 = 分键集合与量级同型,不要求逐键相等;
  3. StartBattle 出战流转正常(备战环 → 战斗等待)。
- 改 Python 代码后项目 MCP server 必须重启才生效(AGENTS.md「MCP」节;实机烟雾前执行,局中禁改纪律不适用——本批无实机局在跑时才动码)。

## 3. 关键取舍

- **备选 A(采纳):契约面收口,决策核内保留 list。** 核内 list 承担首项排序职责(§2.3 理由 1/2),强行单动作化核 = 零行为收益的结构重构 + 证明面扩大;契约形状是用户规范的直接对象,收它即治根(表示层)。
- **备选 B(弃):决策核一并改单动作**(`decide_from_turn` 返回单动作,拆发射组织机器)。弃因:需重推 EV-骨架拓扑合并语义(R197 症1 修复)与帧稳定分类/截断的包内 4 处调用点(§2.3 理由 2),证明面大、无行为差;核内简化应挂将来的行为变更大批顺带,不单独立项。
- **备选 C(弃):形状不动,只改文档口径。** 弃因:规范主诉求 = 接口只产出一个动作;形状遗留会持续误导新策略实现者(按 list 语义实现,尾部动作静默失效 = 隐性 bug 温床);表示层根因留在源头违背治本原则。
- **备选 D(弃):备战也对齐商店「全函数」,无动作 = StartBattle,不设 None。** 弃因:与已声明的备战域分域表述冲突(op-layer §1.1 备战空批合法交回),且收窄第三方策略的等待表达自由(§2.1 依据 2/3);收益仅剩与商店形状对称,而对称本身不是规范条款。
