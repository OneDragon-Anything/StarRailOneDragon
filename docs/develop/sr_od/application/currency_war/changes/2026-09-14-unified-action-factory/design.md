# 统一动作工厂(unified-action-factory)迭代设计(总纲)

> 承接出处:2026-09-11-cw-clear-run 迭代收官讨论中的用户裁定(2026-09-14)——
> ①立项单一动作工厂;②空决策推进型 op 不入工厂;③**词表归一入本迭代**
> (用户裁定「双族共存 → 要治本」:不做共存过渡,同名动作合并为单一
> 词表、单一坐标系)。
> 对抗审后用户裁定(2026-09-14,R1-R6,与上文同批生效):
> R1 退役=删(退役动作类直接删除,旧日志数据可弃);
> R2 组合不入框架词表(RunDeploy/RunEquip/RunTools 是策略实现,删除,
> 改决策核逐个发原子动作;删除时机=原子通路就位后,归一词表批内);
> R3 CompTransaction 删(整档替换宏动作=策略内容,词表/kernel 建模/
> sim 消费/op 全链删除);
> R4 ClickSpheres 改形(动作携带球坐标列表,执行器纯机械逐个点;
> 词表边界声明:框架词表=原子动作+坐标参数化机械动作,其余=策略实现);
> R5 刷新=终结(投资环境刷新圆钮已落码,commit 05b027af6;作为「刷新
> 终结」结构语义先例写入本设计);
> R6 LevelUp 粒度定案(单动作意图;发射形态与逻辑态建模缺口给唯一
> 方案)。
> R7 武装箱四选一独立成画面 op(PickBoxCard 出备战词表;OpenBox 开箱后
> 本访问交回,外循环按武装箱选择画面分发到新画面 op;形态按
> screen_op.md §8.3 判据 = 单选族例外、选卡即终结)。
> R8 工具不设通用动作:每个消耗品作用对象语义不同(冶金炉→拖到角色,
> 含角色模式;拆装扳手→拆装备),按消耗品各立原子动作;RunTools 删除后
> 的原子通路按此多类落,与 R2 组合拆除条款合并执行。裁决1(2026-09-14)
> 定案命名:FurnaceUse/PrivilegeCardUse/WrenchUse/PrecisionWrenchUse/
> 投影仪按型号两类/LuckyTokenUse(清单见 §2.6 工具条款)。
> 裁决2(2026-09-14):批2 拆 2a(原子通路)/2b(归一删除)两账本节点
> (landing §3.2a/§3.2b)。
> R9 「逻辑态未建模→交回外循环保守回退」从目标架构废除——治本 = 每个
> 动作 op 立刻补逻辑态计算;正本 `flow/action-logic-state.md`(动作op ×
> 逻辑态计算枚举)已起草在案,本设计引用为地基与批2/批3 实现规格
> 来源,勿重复枚举;该文档备战域现状行(§3.3 备战 LevelUp 连点旧形态
> 申报「逻辑态显式不推进」)与本篇 LevelUp 定案④相反,随批2a 落码
> 同步转录(landing §3.2a);保守回退仅在该文档标注的知识缺口处临时
> 存在且须带补档计划。
> 裁决3 比对收口纪律升格通用原则:所有比对(验证/判效/一致性检查)只
> 收口在 game_state 写入观察态的对账点,动作 op 内零比对;WearEquip 零
> 比对出生,旧 CV-diff 验穿批2 同批删;现役动作 op 内留证比对面列待迁
> 清单随批3/批4 迁观察侧(§2.4)。
> 术语正名(用户裁定 2026-09-14):**逻辑态** = 动作执行后不经观察、
> 按游戏规则推算预期状态并直写容器的状态(旧称「投影」为误用造词,
> 本篇统一用逻辑态;代码标识符本批不改,登记见 §2.6)。
> 本迭代 = 统一观察架构(`flow/统一观察架构-画面op基类设计.md`)动作端口
> 契约(§6)在实机侧的收口批;前置形态 = 同期 T-197/T-198/T-201 的画面 op
> 正名与动作文件拆分。

## 0. 元信息

- 迭代目标:全部动作 op 公用一个工厂——实机动作执行端口从「商店一套类
  注册表工厂 + 备战一套执行器方法分派」收敛为「一个通用基类 + 一张全动作
  注册表」;词表归一为单一坐标系 + 词表边界收敛(原子动作入词表,
  策略实现出词表)。
- 状态:草案(对抗审修订版,R1-R6 已落文,待复核收敛后定稿)
- 文档清单:无详设(单文档方案,本篇即完整设计)

## 1. 问题与动机

- **现状症状**(代码事实,2026-09-14 工作区核真,T-207 死词清理批在飞删除
  五个退役类后的现状):
  1. 实机动作执行端口两套形态:商店域 = 动作 op 类 + 注册表工厂
     (`operations/cw_op/cw_shop_actions.py::_OP_TABLE` :39-46 +
     `shop_action_op_for` :49-56,isinstance 分派);备战域 = 单执行器
     方法 if/elif 链(`prep_actions.py::_execute_dispatch` :990 与
     `_dispatch_direct` :1023)。备战词表全集 13 类
     (`kernel/cw_prep_actions.py::PREP_ACTION_TYPES` :174),执行器两链
     辖 12 类(组合/出战链 4 + 直执行链 8);OpenShop 不经执行器——
     画面 op 流程层截流(`cw_screen_prep.py::_act_execute_default`
     :2013-2034 → `_open_shop_phase` :2381)。
  2. 同名动作两执行体:`SellBench` 在两域各一套——商店 `SellBenchOp.
     execute`(`cw_sell_bench_action.py`,拖拽 + tracked 同步
     `mutate_bench_deployed` + 商店账本)vs 备战 `_sell_bench`
     (`prep_actions.py:1261`,同一拖拽原语 `drag_bench_to_sell` +
     `_track_remove_bench` + sleep)。机械半已单一源,tracked 账维护/
     时序/记账各一套,且备战侧调用点做坐标系换算(`action.slot - 1`,
     :1267)。
  3. 终结语义两形:商店 = op 类 `terminal` 属性
     (`cw_action_base.py:27`);备战 = 消费点按类型集合判
     (`cw_screen_prep.py` 决策循环结束判定段 :1747-1754,StartBattle
     wait=3 / OpenShop wait=1.0;生命周期孪生环 :1959-1963 同构)——
     同一框架概念两处表达。
  4. 词表边界失守:备战词表混入策略实现——组合壳 `RunDeploy`/`RunEquip`
     /`RunTools`(一次发射封装整段流程,计划与授权在执行器内闭环,
     `cw_prep_actions.py:156-167`);批式挑选载荷 `ClickSpheres.max_k`
     (大球优先与预算截断在执行器 `_click_spheres` :1046-1063);商店
     词表混入整档替换宏 `CompTransaction`(`cw_vocab.py:611`,全仓零
     生产构造,仅词表内 :1239 内部重组构造);选卡决策以备战动作承载:
   `PickBoxCard`(`cw_prep_actions.py:68`,发射点 `entry.py:457`
   'prep_box_pick' 臂,执行器内嵌默认选卡)的访问面实为独立建档画面
   「货币战争-备战-武装箱选择」——策略实现长进了备战词表且错挂画面
   归属(用户裁定 R7 正位)。
  5. 同名动作双坐标系:族A(`kernel/cw_vocab.py`,容器槽位表下标,0 起)
     与族B(`kernel/cw_prep_actions.py`,画面物理槽位,1 起),对照表
     与换算式见 `cw_vocab.py:315-332`;换算散在调用点(实锤
     `prep_actions.py:1267` `action.slot - 1`)。
- **根因归层:约定层**。统一观察架构 §6.2 已宣言目标形态(「映射表声明式
  (意图类型 → 点击链函数),散在 op/handler 内的过程代码逐步收拢」),§6.6
  动作清单表在设计层已是全动作一张映射表;代码未跟上是因为两域各自生长,
  不是领域必需的差异。词表边界失守同理:组合壳/宏动作是策略实现长进了
  框架词表,不是框架必需的词表成员。判据 = 用户裁定的框架/策略两层区分
  (2026-09-14):框架上每画面同形(决策核 → 意图 → 动作 op 执行),
  执行端口没有理由分商店/备战两套;词表没有理由收策略实现。
- **解决到哪**:批1 通用基类 + 单一注册表(零行为);批2 词表归一 +
  原子通路 + 组合壳/宏动作删除(语义批,申报面见 §2.6);批3 备战执行器
  收编(零行为);批4 事件线 pick 收编 + 词表纪律注册完备锁(零行为);
  末阶段正本更新。
- **明确不解决**(防外溢):
  1. 空决策推进型 op(简报/弹窗族/位面过渡)——用户裁定不入(无意图词表,
     空决策形态合同另立,screen_op.md §8.3);
  2. sim 侧动作应用主体——已单一(`CwActionSink` 协议 + 引擎 apply,
     §6.3);族A 合并面 sim 零改动(§2.6);CompTransaction 的 sim 消费
     删除是 R3 申报面,非本条豁免;
  3. 出战链判效面的退役——判效/重发/停机 as-built 保留,退役挂账统一
     观察架构 A6(§2.4);
  4. 整档替换(CompTransaction 语义)的策略侧重表达——框架面删除归批2,
     策略以原子序列重表达归策略侧另批;
  5. 各域执行包络(守卫断言/账本/回执登记)的语义——留守原位,只随
     分发形态换挂点。

## 2. 方案

### 2.1 目标形态与词表边界

```
各画面决策核 → 意图(词表对象)
    → action_op_for(intent)          # 全动作唯一注册点(单一工厂)
    → ActionOp.execute(env)          # 通用基类;发出即职责完成(T-223;
                                     # 在册例外 = StartBattleOp,§2.4)
    → terminal? → 该画面终结处理
```

- **词表边界声明**(用户裁定 2026-09-14 R4):框架词表 = 原子动作 +
  坐标参数化机械动作(单步点击/单步拖拽/逐坐标点击列);组合编排、
  授权循环、批内挑选逻辑 = 策略实现,不入词表。词表成员资格按此判据
  逐类审查(批2 执行),注册完备锁(§2.5)自此机械可查。
- **比对收口纪律**(用户裁决3,通用原则):所有比对(验证/判效/
  一致性检查)只收口在 game_state 写入观察态的对账点,动作 op 内零
  比对。新建动作 op 零比对出生;现役动作 op 内留证比对面列待迁清单
  (§2.4),过渡期保留但标注违规待迁,随批3/批4 迁观察侧。

### 2.2 通用基类(批1,零行为)

- `cw_action_base.py` 内 `ShopActionOp` 升格为 `ActionOp`;商店六 op 改继承
  `ActionOp`(类体零改动)。
- 新增 env 协议(`typing.Protocol`,同文件):

  ```python
  class ActionExecEnv(Protocol):
      op: SrOperation
      match: object
      config: object
  ```

  基类签名 `execute(self, env: ActionExecEnv) -> bool`;域 env
  (`ShopExecEnv`,`cw_shop_action_ops.py:125`,批2 增 `PrepExecEnv`)
  结构化满足协议。子类覆写可窄化为本域 env 类型(运行时不检查参数类型,
  项目既有风格)。依据:商店域现役 `ShopExecEnv` 四公共字段
  (op/match/config)+ 域私有字段(坐标/账本/state),备战域执行器自持
  字段(`prep_actions.py:628-651`,last_detail :633 / last_launch_ok
  :637 / last_gold_delta :643)同构可映射。
- `terminal` 属性(:27)原样上收基类;「恒 True 零判效」docstring 契约
  (:32-35)上收基类时**预置例外条款占位**:在册例外 = StartBattleOp
  (§2.4 批3 落款),基类契约文本注明例外登记口,批1 本身零行为。

### 2.3 单一注册表(批1,零行为)

- 新文件 `operations/cw_op/cw_action_registry.py`:`_REGISTRY`(dict:词表
  类 → op 类)+ `action_op_for(action) -> ActionOp`。词表外类型
  AssertionError 响亮暴露(沿用 ADR-0517 决策 9 语义,报错文案改中性)。
- **注册行顺序敏感**:is-a 链的父类行必须在子类可独立匹配处之前兜底
  (现役先例:`LevelUpShop` is-a `LevelUp` 同 op,`cw_shop_actions.py:41`
  注)。注册表按「族 → 基类兜底行 → 具体类行」分区注释。
- `shop_action_op_for` 改薄委托 `action_op_for`(消费面
  `cw_screen_buy_cards.py:1148` 零改动,测试替身缝保留);商店六行
  (BuyCard/LevelUp/RefreshShop/SellBench/CloseShop/CompTransaction,
  `cw_shop_actions.py:39-46`)首批在册。CompTransaction 行的删除归批2
  (R3),批1 行键先行稳定。
- 备战域与事件线 pick 类型本批**不入表**(批2 归一后,批3/批4 收编),
  注册表头注明收编计划,防「表已单一」误读。

### 2.4 备战执行器收编(批3,零行为)

- **执行包络留守 runner**:`PrepActionExecutor.execute`
  (`prep_actions.py:697`)的 W209j 停机刹车(:710-714)、执行点金差
  显影(:715-741)、回执/journal 登记(`_note_action_receipt` :843 /
  `_note_action_journal` :875)、`validate` 参数校验(:655)全部留守
  ——它们是访问级账务与防线,不是动作级机械执行。
- **分派改查注册表**:每动作立 op 类,`execute` 体 = 现 executor 同名方法
  逐字迁移;executor 原方法改薄委托(保持测试 monkeypatch 面),行为零
  变化。`_execute_dispatch`(:990)/`_dispatch_direct`(:1023)两条
  isinstance 链删除,入口改 `action_op_for(action).execute(env)`。
  批2 已把 LevelUp 体单击化、ClickSpheres 体机械化(§2.6),批3 只迁形
  不改语义。
- **env**:新立 `PrepExecEnv`(dataclass:op/match/config + executor 引用
  + 宿主环面)。组合壳已随批2 删除(R2),原「组合壳构造参数经 env
  传递」通道不存在;穿戴/工具的槽位参数在动作对象自身(坐标参数化字段)。
- **detail/emitted 旁路**:prep 域 `(detail, emitted)` 语义不进基类返回值
  (基类契约见例外条款);op 类写 `env.detail`/`env.emitted` 旁路字段,
  runner 包络读之——与现行 `executor.last_detail` 旁路(:633)同构,
  消费面(`cw_screen_prep.py::_act_execute_default` :2035-2037 写点、
  `_act_execute` :1998 fire_outcome_hooks 读点)语义不变。
- **终结判定对齐**:备战环结束判定(决策循环 :1747-1754 与生命周期孪生环
  :1959-1963 两处)由 `isinstance(action, (StartBattle, OpenShop, OpenBox))`(R7 并入 OpenBox)改读
  `op.terminal`;**终结等待时长 = op 类属性 `terminal_wait`**
  (ClassVar;`StartBattleOp.terminal_wait=3`、`OpenShopOp.terminal_wait=1.0`,
  与现行 wait 值逐一等价)——时长属动作转移语义,随 op 类承载,消费点
  经注册表读类属性,禁消费点私表。
- **OpenShopOp 显式裁定**(注册行 = terminal 承载行):
  - `execute` 体 = 抛 `AssertionError`(防静默复活)。OpenShop 的流程编排
    是画面 op 流程职责(`_act_execute_default` 截流 :2013-2034 →
    `_open_shop_phase` :2381-2426),按本设计「流程编排留守」划分不进
    动作 op;注册行在正常路径不可达,可达即分派漏斗被绕过,响亮暴露。
  - read_only 两形态 = 动作字段 `OpenShop.read_only`
    (`cw_prep_actions.py:147`)承载,消费在流程层编排(:2415 分支),
    与注册表无关——注册表一行,不表达形态分叉。
- **StartBattleOp 显式裁定**(基类契约在册例外):
  - `_start_battle`/`_launch_attempt`(:1520-1659)as-built 保留:落地
    判效轮询、失败原样重发(长按下加固)、连败停机留证
    (`_launch_dead_escalate` :1667)、免战子态 fallback、未达上限警告
    处理,批3 体迁零行为。
  - 例外条款落基类契约登记口:`StartBattleOp.execute` 返回值 = 发射位
    **内部事实**(非恒 True;找不到按钮/未落地 = False),消费面 =
    cw_loop 发射链 `last_launch_ok` 旁路(`cw_loop.py:385-420`,读点
    :419)与执行态写点(`prep_actions.py:742-752`)。
  - 退役挂账:判效/重发/停机面随统一观察架构 A6(消费端退役时同退;
    在册挂账标注 `prep_actions.py:634-637`、`cw_loop.py:386`)。本迭代
    不动该面,批3 diff 内零语义改动。
- **退役成员无注册行**(用户裁定 R1:退役=删):`EnsureShopOpen`/
  `EnsureShopClosed`/`RunBuyPhase`/`BailToOuter`/`DeferSpheres` 已由
  T-207 删除(全仓零引用核真),不设墓碑行、不设 `ControlFlowOp` 承载行;
  词表退役语义自此 = 直接删除类,旧 journal 数据可弃。
- **比对收口迁移清单**(裁决3③;过渡期保留但代码标注「违规待迁」,
  随批3/批4 迁观察侧;迁移时零决策留证语义由观察侧缺陷台账
  `defects.record_defect` 承接):
  1. 投资环境刷新零效果留证——刷新计数前后比对(`cw_screen_invest_env.py`
     :316-333,defect 键 refresh_no_effect);
  2. RefreshShopOp 刷新牌面三值比对——刷前/刷后牌名集
     (`cw_refresh_shop_action.py` :141-143,refresh_board_changed);
  3. RefreshShopOp 刷新期望对账——期望金/卡数 vs 实读
     (`cw_refresh_shop_action.py` :144-171,defect 键
     refresh_expect_mismatch);
  - 具名三面归批4 统一迁移(shop 域 op 注册表收编后处置、投资环境面随
    overlay 批);批3 辖 prep 域现役零留证比对面(CV-diff 已批2 删、工具
    对拍随原子化由观察承接);迁移批任务书第一步全仓扫描动作 op 内
    比对面补全清单,漏面不合格。

### 2.5 事件线 pick 收编 + 词表纪律锁(批4,零行为)

- `kernel/cw_events.py` pick 词表(EncounterPick :612/SupplyPick :725/
  MegastarPick :789/PartnerPick :817/PlannerPick :838)注册 op 类,
  execute = 现役 overlay 确认链(点卡选中 → 确认,`_overlay_confirm.
  confirm_and_verify`);各 overlay 画面 op 的 act 段改经工厂。
- 词表纪律注册完备锁(测试;**运行时锁,禁源码扫描**——源码扫描测试
  一律禁止,不在测试里读取/扫描源码做断言,AGENTS.md §10.3):锁面
  遍历词表元组单一源——统一词表 `CW_ACTION_TYPES`(基类随迁时自
  `PREP_ACTION_TYPES` :174 更名迁移,白名单元组先例形态保留)与
  `cw_events` pick 族运行时元组(批4 新增常量,先例同上);逐类断言
  注册表解析可命中该类(is-a 兜底语义同注册表,经注册表类级查询,
  不构造业务动作实例、不读源码),未注册 = 锁红。**退役 = 删类**
  (R1):元组中不存在即天然不可复活,无退役行、无墓碑。此即词表纪律
  (统一观察架构 §6.1「新动作入词表 = 先改契约再落码」)的机械化兑现;
  该节原「AST 扫描」验收申报按源码扫描测试禁令改形为运行时锁,正本
  回填时同步申报(landing 正本更新清单)。

### 2.6 词表归一(批2,语义批;用户裁定 2026-09-14 ③ + R1-R4/R6)

- **病根**:同一游戏动作在两个词表模块各有一个类、两套坐标——族A
  (`kernel/cw_vocab.py`,容器槽位表下标,0 起)与族B
  (`kernel/cw_prep_actions.py`,画面物理槽位,1 起)。同名者四:
  SellBench/SellDeployed/DeployMove/LevelUp;换算 `族B = 族A + 1`
  (bench 域;deployed front idx=slot−1、back idx=4+slot−1)散在调用点
  (实锤 `prep_actions.py:1267`)。依据:双族对照表
  `cw_vocab.py:315-332`;`screens-actions-capability.md` §2 双族坐标系节。
- **规范系裁定 = 容器槽位表下标(族A 口径)**。依据:①状态容器
  (GameState)是唯一状态真相,观察漏斗已把物理槽位读数写入容器槽位表;
  ②sim 已单边消费族A(构造点实证 `sim/engine_p1.py:880`
  `SellDeployed(deployed_idx=...)`,import 源 = cw_vocab)⇒ 族A 合并面
  sim 消费零改动;③物理坐标只在执行边需要,换算是纯函数
  (screens-actions-capability §2)。
- **合并清单(四对;统一类一律 = 现役族A 类原样,字段/顺序/metadata
  逐字保留,族B 类删除,族B 构造点改产族A 类)**:

  | 统一类(住 `cw_vocab`) | 裁定 | 吸收的族B 类 |
  |---|---|---|
  | `SellBench` | 族A 类原样:`bench_idx`(:367)/`income`(:371)/`expect`(:372)/`reason`(:373)/`convert_reason`(:383),字段与顺序逐字保留;`convert_reason` = ADR-0611 转化类豁免分键,值域单一源 `SELL_BENCH_CONVERT_REASONS`(:425) | `cw_prep_actions.SellBench(slot, reason)`(:74-88)删除;构造点 9 处改产(`mandate.py:888/:1148/:1251`、`entry.py:541/:808/:819/:1125/:1179/:1191`),参数 `bench_idx` = 容器槽位表下标(换算口径见「换算归属」) |
  | `LevelUp` | 族A 类原样:`cost`(:435,必填)+ `auth_basis`(:436,授权记录非指令;sim 账本 `auth` 键转录 `engine_p1.py:2299-2315`,检查器 levelup_interest_engine_gate 消费) | `cw_prep_actions.LevelUp`(:133,无字段)删除;发射点 `mandate.py:1481` 改产族A 类,cost/auth_basis 填充口径见「LevelUp 粒度定案」 |
  | `SellDeployed` | 族A 类原样:`deployed_idx`(:574,槽位表下标 0-9)/`income`(:578)/`reason`(:579)/`expect`(:580);物理 row/slot 由执行边换算 | `cw_prep_actions.SellDeployed(row, slot)`(:118-121)删除;**全仓零构造点**(grep 核真,无迁移面);换血卖出由 R2 原子通路首产 |
  | `DeployMove` | 族A 类原样:`bench_idx`(:473)/`to_row`(:477,语义排字段保留,不按下标推导)/`faction`(:478,上阵后 board 阵营计数所需,发射位从容器槽位表角色对象现取;`simulate` 的 DeployMove 分支(:938-939)消费此字段) | `cw_prep_actions.DeployMove(from_slot, to_row, to_slot)`(:125-129)删除;**全仓零构造点死类**(腾席部署实际走 RunDeploy 组合壳——本行如实披露),R2 原子通路就位后由发射面首产 |

  同名类删除后,「cw_prep_actions 的 SellBench 与 cw_state(=cw_vocab
  别名,`flow.py:748`/`bridge.py:177`)的 SellBench 同名异类禁混引」
  防线(`cw_game_state.py:2112-2113`)随单一词表消亡。
- **统一词表家族树**:基类 `PrepAction`(`cw_prep_actions.py:28`,
  `route_tag` kw_only + `action_key_exclude` metadata :41-42)随词表迁
  `cw_vocab` 并更名 **`CwAction`**(统一词表后「Prep」前缀与辖域不符;
  更名的 import 翻转与词表迁移同批完成,无额外面);原族A 十类
  (Action 联合 :648-649 全体)统一收编为 `CwAction` 后代(route_tag
  kw_only 缺省 '' 向后兼容族A 既有构造与 sim 构造面);`Action` 联合类型
  保留(sim 侧判别用代数和),运行时 isinstance 检查统一用基类。
  metadata 逐字段裁定:`reason`/`convert_reason`/`auth_basis`/`route_tag`
  全部保留 `action_key_exclude`(归因/记录/路由不入幂等键);`action_key`
  函数(`cw_prep_actions.py:186-204`)随迁。批2 附 action_key 输出前后
  对照锁(逐类键面锁定,改名与字段合并不得漂移键粒度)。route_tag 承载
  保留:`bridge.py:273-280` 发射臂回写面不变。
- **组合壳删除与原子通路**(用户裁定 R2;「画面 op 内过程」备选不采用,
  三件全取原子发射——三者均为策略门控且与备战经济排序敏感,画面 op
  自驱动会丢发射序语义):
  - `RunDeploy`/`RunEquip`/`RunTools`(`cw_prep_actions.py:156-167`)删除
    (已死 `RunBuyPhase` 随 T-207 先删)。执行器组合分支
    (`_execute_dispatch` :1001-1014、`_run_equip` :1740、
    `_run_composite` :1789)随批3 收编面删除。
  - **原子发射通路形态(唯一方案)**:
    1. **部署**:决策核逐帧按 kernel `select_deployments`
       (`cw_deploy_logic.py:439`;带拒因形态 `select_deployments_reasoned`
       :649)现算部署计划,逐 move 产 `DeployMove`;板满换阵卖人按
       `select_swap_plan`(:1650)计划逐人产 `SellDeployed`/`SellBench`。
       计划单一源已在 kernel(`cw_screen_deploy.py:1243` 「发射×执行
       单一源」在册),组合壳删除后发射位直接消费同一函数,无第二源。
    2. **穿装备**:新原子类 **`WearEquip`**(装备库槽位 + 目标角色
       物理槽位,坐标参数化机械动作);计划构造 = 现役
       `_build_equip_wear_plan`(`prep_actions.py:210`)自执行器模块迁
       kernel,决策侧逐帧现算;CV-diff 验穿批2 同批删(裁决3:WearEquip
       零比对出生),穿没穿由观察写入边对账承接;逻辑态 = `obs.owned_equips`
       摘件(与 OpenBox/OpenTome 同形,`_project_prep_obs` :921-926 先例)。
    3. **工具**(用户裁定 R8 + 裁决1:每消耗品一个原子类,命名定案;
       通用 UseTool 作废):RunTools 删除后的原子通路按消耗品多类落,
       各类自带作用对象参数声明(索引/槽位字段按 AGENTS §8 定义注释
       规范:坐标系 + 取值时机,逐类写明;作用对象语义源 = 官方道具文
       `cw_equipment_data.py:190-196` + 效果申报表
       `cw_affix_effects.py:246-290`):
       - **`FurnaceUse`**(冶金炉;双模式):拖装备 = 原地变异同类型随机
         (target = 装备库 owned 件);拖角色 = 全拆 + 变随机(target =
         角色槽位);产出不可预知 → 观察收口(现役负写端留证纪律保留)。
       - **`PrivilegeCardUse`**(特权赋予卡;双腿):库存腿 target = 被变换
         的进阶成品件(装备库 owned);拖角色腿 target = 角色槽位(从
         已穿进阶装备选一件原位特权化,落码位 `cw_affix_effects:1157`
         在册)。
       - **`WrenchUse`**(拆装扳手):target = 角色槽位(取下该角色全部
         穿戴,装备归属面回区)。
       - **`PrecisionWrenchUse`**(精密拆装扳手):target = 角色槽位(同上;
         无限次用;重复获得改 +1 金 = 贡献算术,获得回执窗现役在册保留)。
       - 投影仪按型号两类(**`StaffProjectorUse`**(员工)/
         **`PerfectProjectorUse`**(完美)):target = 角色
         槽位(在备战席创造该角色 1 星复制);费用门参数逐类声明
         (员工 = 3 费及以下,完美 = 无门;门表单一源
         `cw_affix_effects.py:442-446`)。
       - **`LuckyTokenUse`**(幸运令牌):作用对象判据面现役 fail-closed
         永不进准入(`cw_op_tools.py:16` 在册)——类随族立档 + 注册行,
         发射位挂账判据面建模批(枚举文档标注知识缺口 + 补档计划,
         R9 纪律);禁无判据发射。
       - 准入现状:现役 admitted 两件 = 冶金炉/特权赋予卡
         (`cw_op_tools.py:252-254`),其余类立档候判据面;G1 准入判定
         留守发射位(`entry.py:692` 形态);消耗确认对拍与效果写端
         (`apply_tool_execution_write` 载体)留守观察/效果库存写端原位。
    4. **执行序守卫归属 = 决策核发射序**(唯一答案):备战环逐帧取决策
       输出首项执行(`cw_screen_prep.py:1683`),发射序即执行序;先卖后上
       由 kernel 计划序表达,同帧多件排序由发射位表达(现役
       `mandate.py:1687-1692` 回排块随组合壳删除退役,由发射序自然承担,
       不新增执行器层守卫)。
    5. **cw_loop 直构造面同步改**:出战链(`cw_loop.py:390-420`,RunDeploy
       :402/:411 + StartBattle :413)改「按 `select_deployments` 现算逐
       move 发 `DeployMove` + 发 StartBattle」;恒指纹窗白名单
       `EXHAUSTION_WINDOW_ACTIONS`(:229,现 = {OpenShop, RunDeploy})
       重推 = {OpenShop}(RunDeploy 删除;DeployMove 是进展性动作,
       出现在恒指纹窗 = 真实进展,不入窗;重推判据落批2 交付记录)。
  - **删除时机 = 原子通路就位后,归一词表批内**(批2 拆 2a/2b 两账本
    节点,见 landing §3.2a/§3.2b:2a 通路先立、2b 归一删除)。
- **CompTransaction 删除**(用户裁定 R3):整档替换宏动作 = 策略内容,
  原子词表已覆盖其全部子步(SellBench/SellDeployed/DeployMove/BuyCard),
  框架面全链删除;整档替换语义由策略侧以原子序列重表达(策略侧另批,
  §1 明确不解决)。删除面清单:
  - 词表:类与 `FillSpec`(仅 `CompTransaction.fill` 消费,`cw_vocab.py`
    :537/:611;`fill` 字段 :636)、`Action` 联合成员(:648)、
    `_resolve_comp_transaction`(:668)、`_apply_comp_transaction`(:871)、
    `simulate` 分支与装备守恒元组成员(:953-954/:1126-1136)、
    `mutate_bench_deployed` 分支(:1232-1259);
  - kernel 提案建模:`apply_shop_action_logic` CompTransaction 分支
    (`cw_game_state.py:1893-1899` 起);
  - sim 消费:`engine_p1.py`(import :86;消费 :2405/:2435/:2466)、
    `sim/checks/ledger.py`(:956/:1629 及关联判据)、`sim/pool.py:136`
    注释面;旧 sim 数据可弃(R1 同规);
  - op 全链:`cw_comp_transaction_action.py` 删档(现役即词表完备性落位,
    类头 :22 自我申报;全仓零生产构造,grep 核真)、注册表行
    (`cw_shop_actions.py:12/:27/:45`)、商店循环终结邻接 fallback 收缩为
    RefreshShop(`cw_screen_buy_cards.py:1098-1108/:1193-1201`)、
    策略截停集收缩(`flow.py:744/:799`、`bridge.py:170/:231`、
    `shop.py:260`)。
- **ClickSpheres 改形**(用户裁定 R4):保留动作类,改坐标参数化——
  载荷 = 有序球坐标列表(观察侧供球:`PrepObservation.spheres`
  `cw_prep_actions.py:230`,形态 [(color, Point, r)]);执行器纯机械
  逐个点(现 `_click_spheres` 读屏与排序半 :1059-1063 删除);大球优先
  /上界挑选逻辑迁决策侧 kernel 单一源(纯选择函数:输入 obs.spheres +
  席位约束,输出有序点击列表);发射位(`entry.py:492/:506`)调用之。
  逻辑态随改形收紧:现保守清空(`_project_prep_obs` :933-934)改按载荷
  精确摘球。旧 max_k 载荷退役,旧 journal 行可弃(R1 同规)。
- **武装箱四选一独立成画面 op**(用户裁定 R7):
  - **PickBoxCard 删除**(词表 13 → 12):发射点 `entry.py:457`
    ('prep_box_pick' 臂)删除;执行链 `validate`(:690-692)/分派
    (:1031)/`_pick_box_card`(:1174)/`_default_box_card`(:1213)删除;
    `adapter.py:106` AtomOp 映射行、`cw_exec_state.py:308/:342`
    apply_op_effect 分支删除。
  - **选卡执行面迁移 = OCR 读名与调用编排自执行器迁新画面 op**
    (决策函数原位,不搬家):现役执行器内嵌默认选卡(`_default_box_card`
    :1213-1250,v7 M-3 申报「P1 住执行器,P5 上移策略」)中待迁面只有
    执行器半——OCR 读卡名 + 「OCR 卡名 → `decide_box_card` →
    `cw_equip_value.pick_equipment` 序数分档」的调用编排
    (screen_op.md §7 表在案),落位文件 = 新画面 op
    `operations/cw_screen/cw_screen_box_pick.py`;决策函数现役已各就
    其位、原位消费:`decide_box_card` 策略侧(`flow.py:656`/
    `cw_strategy.py:204`)、打分单一源 `pick_equipment` kernel 侧
    (`cw_equip_value.py:191`);机械点选半同归新画面 op。
  - **新画面 op 独立立文件**:建档画面「货币战争-备战-武装箱选择」
    (执行器 `BOX_SCREEN` 常量 `prep_actions.py:615` 即此画面名)立独立
    新文件 op——勿与 `cw_screen_armory_box.py` 混(该 op = 道具获得说明
    弹窗点×关,screen_op.md §7 表明示两物);visit 形态 = 观察四卡 →
    `decide_box_card`(kernel)→ 点卡 → 确认 → 交回外循环。
  - **形态裁定(唯一答案)**:适用 screen_op.md §8.3 判据总表——选择面
    (四卡选一)∧ 零逻辑态账(screen_op.md §8.3 判据原文「投影账」=
    正名前旧称;选卡不写容器/期望账;装备入包归观察域
    `owned_equips` 下一帧现读)⇒ **单选族例外**(不入决策规范;入 op
    规范 = 已建档分发画面),visit = 选卡即终结(同事件单选族一步形态,
    同 `cw_screen_equip_pick` 模式);**不入动作工厂注册表**(非动作词表
    成员,外循环按画面分发)。
  - **OpenBox 终结化**:开箱后本访问交回(新增事实 = 武装箱选择画面
    出现,与刷新终结结构语义 R5 同构);`_project_prep_obs` OpenBox
    分支(:921-926)随终结化作废删除;交回等待值来源写死(批2a)=
    现役 `_open_box` 动画等待 `_OVERLAY_ANIM_WAIT_S`
    (`prep_actions.py:73`);批3 `OpenBoxOp` 置 `terminal=True`
    (terminal_wait 与批2a 落地值等价,批3 锁)。
  - **批次归位**:全部落批2a(新 op 与分发先立、PickBoxCard 链后删,节点
    内行为连贯);批3 收编清单联动(PickBoxCard 不立 op 类);批4 锁面
    词表数联动(本裁定单项:备战词表 13 → 12;批4 锁面以批2 完成后的
    统一词表 `CW_ACTION_TYPES` 实际元组为准,不另记账目数)。
- **逻辑态计算全覆盖**(用户裁定 R9,废除「未建模 → 保守回退」):
  「逻辑态未建模 → 交回外循环保守回退」自目标架构废除(现役形态 =
  `_project_prep_obs` 未建模返回 None → visit 终结交回外循环,
  :910-913/:953);治本口径 = **每个动作 op 立刻补逻辑态计算**。
  逻辑态计算枚举正本 = `flow/action-logic-state.md`(动作 op × 逻辑态
  计算枚举,已起草在案;其备战域现状行与本篇定案④相反,随批2a 落码同步转录
   (义务落 landing §3.2a))——本设计引用之为地基与批2/批3 实现规格
  来源,不重复枚举。现役未建模面清单(:910-913:DeployMove/
  SellDeployed/LevelUp/RunDeploy/RunEquip)去向:RunDeploy/RunEquip
  随组合壳删除消亡;DeployMove/SellDeployed 按枚举文档补齐;LevelUp
  由本节定案转录枚举文档。「保守回退」仅在该文档标注的知识缺口处临时
  存在且须带补档计划(缺口 + 补档批指针);无标注缺口的动作禁无逻辑态
  发射。机制归属:`apply_prep_action_logic`(kernel 写口 :2085)扩为
  逐动作逻辑态计算单一源口,域集随枚举文档逐动作扩(标识符改名见
  正名登记项)。
- **LevelUp 粒度定案**(用户裁定 R6;取代旧「两步走择一」——该条件的
  前提不成立,按代码真值重述:①活跃备战环(`cw_screen_prep.py` 决策
  循环 :1655-1772)**无按 action_key 的重发拦截**,action_key 消费点仅
  校验日志(:1691/:1693)与记账键(:1713-1715);②备战逻辑态未建模
  LevelUp(`_project_prep_obs` 未建模面 :910-913 明列),逐帧单击若无
  逻辑态建模则每击触发 heavy 重观察):
  - **定案 = 逐帧单击发射 + 批2 同批补备战逻辑态 LevelUp 建模**(唯一
    形态,禁再开第二形态):
    1. 统一类语义 = 单击「购买经验」一次,+`XP_PER_BUY` 经验
       (ADR-0517 决策 3/ADR-0129 既定粒度;商店域同形先例
       `cw_level_up_action.py:19-21` 「每帧恰发一击,多击序列由决策循环
       逐帧重组」);
    2. 发射形态 = 决策核逐帧至多一击,升 N 击 = N 帧;每帧发射前置 =
       kernel `clicks_to_next_level`(`cw_economy.py:693`)现算击数 > 0;
    3. **cost 填充口径(唯一)** = kernel 单一源逐帧现算
       `xp_click_cost(board_state_of(session))`(`cw_economy.py:656`),
       失读回退 `XP_CLICK_COST_FALLBACK`(:57);**auth_basis 填充口径
       (唯一)** = 发射臂放行名分键,现役 arm1/arm0/pop/must_spend 形态
       保留(`mandate.py:1473-1482`);
    4. 逻辑态建模缺口唯一方案 = `apply_prep_action_logic` 域集
       `PREP_PROJECTION_DOMAINS`(`cw_game_state.py:2082`,现封闭
       ('gold','bench'))扩 ('xp','level'):LevelUp 分支 = gold −cost +
       xp/level 跨门槛推进(推进公式单一源 = kernel `xp_apply_clicks`
       (`cw_economy.py:64`,XP_PER_BUY :55 / XP_TO_NEXT_LEVEL :56));
       **deploy_cap 不写**——容量真值由观察写端防抖读承接
       (deploy_cap = level + 宝钻,`cw_game_state.py:2323`;逻辑态写入后
       `max_units` 的 cap<level 兜底规则 `cw_vocab.py:253-261` 自然保守
       承接升级增量,防抖真值下一入口观察刷新);逻辑态失真由下一入口
       heavy reconcile 对账纠偏(既有纪律,`fields.md` §2.3 观察赢);
        LevelUp 行同步转录 `flow/action-logic-state.md` 枚举正本;
        批间中间态(批2a 时族B `LevelUp` 尚无 cost/auth_basis 字段,
        批2b 类合并翻转才有):金腿暂由执行缝金差承担
        (`_executed_gold_delta`,执行包络留守面)、逻辑态分支只落
        xp/level 推进不写 gold;批2b 翻转切 `action.cost` 直写
        (gold −cost 同步生效)——拆分见 landing §3.2a/§3.2b;
    5. 授权归属逐项(执行器授权面全删,`_level_up` :1383-1516 单击化 =
       找钮→点→固定等待,零授权零计数):血闸入口整级授权与逐击 hp
       地板 → 发射面(entry posture 血闸让位在册 :972-981 + 决策核逐帧
       hp 现值判定);金地板逐击查金 → 决策核发射门(spend_unified /
       levelup_budget_gate 既有 :1012/:1029);击数推导 → kernel(发射
       判据,见第 2 条);
    6. 发射面既有机制逐项裁定:M2 停摆非变集 {LevelUp}
       (`mandate.py:135`)成员资格不变(单击只动 xp/level/gold);
       posture_unfulfilled 'level' 对账(`entry.py:823-831` 挂点、
       `_reconcile_posture_authorization` :867,spend_mode='level' :914)
       口径改「本帧授权存在(击数>0)∧ 本帧未发射 ⇒ unfulfilled」
       (:1041-1047 置位面不变);m1p 同帧 LevelUp 抑制
       (`mandate.py:1504-1505`)语义不变;RunTools/LevelUp 同帧执行序
       回排随 RunTools 删除消亡(R2),RunEquip 回排块保留至装备原子
       通路就位(同批内先后步)。
- **刷新=终结结构语义**(用户裁定 R5;与 LevelUp 逐帧单击定案同构——
  「唯一引入新事实的动作交回外循环重观察」):先例两处在册——商店
  `RefreshShopOp`(`terminal=True`,`cw_refresh_shop_action.py:28-34`)
  与投资环境刷新圆钮(已落码 T-206,commit 05b027af6,
  `cw_screen_invest_env.py` 模块头 :7-13 与终结交回 :270-341,
  pending+round_retry 交回重入);策略屏/遭遇/补给刷新是否同款 = 逐画面
  审查中,本设计按「刷新终结为结构语义」表述,不为未审画面预设结论。
- **换算归属**(修正口径):发射/决策面一律产容器下标——发射面从容器
  槽位表读口(bench/deployed 槽位表,0 基序)直接取下标构造动作,不经
  `BenchChar.slot` 反推;物理槽位号(`BenchChar.slot` 信息位,1-9)仅存
  两边界,各只允许**一处**换算函数:①观察写入边(物理读数 → 容器槽位
  表,现役 observe/reconcile 写链);②执行坐标边(容器下标 → screen_info
  槽位中心,executor 单点;tracked 同步的物理↔下标换算随迁收拢,
  现役散点形态见 `prep_actions.py:1355-1356`/`cw_exec_state.py:331-332`)。
  依据:发射点反推(如 `bc.slot - 1`)本身就是换算散点,与其收在发射面
  不如让发射面吃容器下标;容器读口已是 0 基序,零转换成本。
- **值域闭集常量新居**:`SELL_BENCH_REASONS`/`SELL_BENCH_ORPHAN_REASONS`
  (`cw_prep_actions.py:98/:112`)随词表迁 `cw_vocab`(与
  `SELL_BENCH_CONVERT_REASONS` :425 同居);sim/checks 三 import 位
  (`sim/checks/suspects.py:106-110`、`sim/checks/ledger.py:550-554/
  :994-998`)列入批2 文件面,仅 import 行翻转,零语义。
- **实施前置(批2 第一步,任务书纪律 = 全仓符号扫描)**:四同名类 +
  `PREP_ACTION_TYPES` 全类 + `CompTransaction`/`FillSpec` + 组合壳三件 +
  `ClickSpheres` 的定义/构造/消费点扫描(含 telemetry `serialize_action`
  `schema.py:256-283` 与 journal 判读工具、`tools/cw` 判读脚本),扫描
  结果附任务书,漏点不合格。
- **遥测/journal 跨批判读口径**(改名 + 值域漂移双申报):
  - 改名键清单:prep 域 journal/receipt 行(行形态
    `op_journal.py:171-173`)`SellBench` 载荷 `slot`(1-9)→
    `bench_idx`(0-8);族B `SellDeployed`/`DeployMove` 现役零构造
    (无新增行面;历史档案若有个别行,归读侧旧档兼容原则容缺处理);
    商店域行键面不变。字段名 `reason`/`auth_basis`/
    `convert_reason` 全保留,`ACTION_REASON_SOURCE_KEYS`
    (`schema.py:290-292`)不变。
  - 值域换算式:旧 `slot` 值 − 1 = 新 `bench_idx` 值。
  - 兼容窗落点(读侧,申报;循 `schema.py:246-250` 旧档案兼容窗先例):
    `telemetry/query.py`、`telemetry/journal_query.py` 与 `tools/cw`
    判读脚本对 `__type__='SellBench'` 行双键兼容读
    (`bench_idx` 缺席回退 `slot`−1)。
  - 申报:**本迭代前后档 SellBench 行不可直比**,须按换算式归一后比较;
    跨批单局复盘/对照由上述读侧兼容窗吸收,禁判读侧裸读裸比。
- **sim 侧边界(分段申报,取代笼统「sim 零改动」)**:①族A 合并 = sim
  零改动(统一类 = 族A 类本身,引擎/逻辑态行为零变化);②CompTransaction
  删 = sim 消费面显式删除(R3 申报面,上列文件入批2 文件面);③
  SELL_BENCH_* 常量 = import 翻转零语义。锁 = 固定 seed 对局(动作流
  不含 CompTransaction)的动作序列与结果逐项不变。
- **逻辑态代码标识符正名登记(本批不改,待裁)**:概念已正名逻辑态
  (卷首裁定行),含旧词根的标识符本批保持原名、零代码改动:
  `_project_prep_obs`(`cw_screen_prep.py:887`)、
  `PREP_PROJECTION_DOMAINS`(`cw_game_state.py:2082`)、
  `flow/projection_contract.md`(正本文件名)。建议后续标识符正名批统一
  改名(方向:`_advance_logic_state`/`LOGIC_STATE_DOMAINS`/
  `flow/logic_state_contract.md`),随本迭代正本回填一并申报用户裁决。

### 2.7 关键取舍

- **单一表 vs 每域一表共享工厂机制**:选单一表。每域一表保留了两形分派,
  等于不收口;单一表让「词表类型必有注册行」可由注册完备锁机械约束
  (§2.5),词表纪律从文档约定变机械约束。
- **op 类包装 executor 方法(薄委托保留)vs 方法体物理搬迁**:
  选「体迁 + 薄委托」。纯包装不消灭两形(方法还在 executor);物理搬迁
  删方法则破坏测试 monkeypatch 面。薄委托兼得:分派单一、行为零变、
  替身缝保留。
- **detail/emitted 进基类返回值 vs env 旁路**:选旁路。改基类返回契约
  `(bool, str, bool)` 会波及商店域六 op 与全部消费点,违背零行为;
  旁路与现行 `last_detail` 同构(§2.4)。
- **退役=删 vs 墓碑/登记行防复活**:选删(用户裁定 R1)。墓碑行的防复活
  价值由注册完备锁承担——类不在词表元组即不可被构造,锁面天然覆盖;
  旧日志数据可弃,不为死数据保留代码形状。
- **组合壳删除 vs 保留组合类只换包装**:选删(用户裁定 R2)。组合壳留在
  词表的代价 = 框架词表混入策略实现(计划与授权在执行器闭环,决策核
  失明),每新组合都要动框架;原子通路让决策序=执行序、授权归发射面、
  计划归 kernel 单一源,是单动作架构的彻底形态。代价(发射面重写 +
  穿装备/工具多类新原子类)由批2 同批承担。
- **LevelUp 逐帧单击+逻辑态建模 vs 执行器有界连点(动作内部步骤)**:
  选前者(R6)。后者把「一次发射 = 升完一级」留在执行器,与统一类单击
  语义(ADR-0517 决策 3)冲突——cost 字段失义,且授权滞留执行层与发射面
  门(spend_unified/血闸 posture)构成双源;前者的代价(逻辑态建模 + 发射面
  授权重排)一次性、有 kernel 公式单一源可用(`xp_apply_clicks`)。先例
  = 商店域单击形态(`cw_level_up_action.py:19-21`)与刷新终结结构语义
  (R5)同构:新事实/新进展交回决策循环重组。
- **词表归一入本迭代 vs 共存过渡**:用户裁定治本(2026-09-14)。共存过渡
  的代价 = 双词表双真相源期间,每次新动作都要双族登记、每次消费都要
  换算,换算税随共存期线性增长;归一的不可逆风险(换算错 = 卖错人)由
  批2 独立语义批 + 全仓符号扫描 + sim seed 回归锁承住,不与形态批混淆
  归因。
