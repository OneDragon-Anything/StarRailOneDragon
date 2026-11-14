# 迭代3设计:三升级 op 通用化归并(机械同构收进域内 helper)

## 0. 元信息

- 迭代目标:落地域 README §2.3 既定评估口径「第三份同构复制出现时评估归并」的评估结论——行迹线券刷链(`UpgradeTraceOp.farm_ticket_chain`)落地即第三份同构,本篇是该评估的设计产出,承接 upgrade-align-1 §3(非目标)划给迭代3的「共享 helper 模块 / toast 门控 / 设次数等复制面归并」与其迭代3评估清单各漂移项。
- 状态:草案 v2(吸收对抗审查 r1:1 阻断 + 9 建议,逐条修订)
- 编号约定:H* = §3.2 helper 条目(H5 分两件:H5a 节点骨架 / H5b 探测谓词);S* = §4 迁移步骤;R* = §6.1 风险条目;P2 = 第二优先可选批(§4 S7 的批次属性)
- 范围声明:本迭代只做「机械同构归并 + 域政策修订」,不改任何已定案行为语义。四项统一语义为本设计的前提,不再裁决:①补料优先级 = 通用材料补全 → 快速刷取券 → 手动战斗(出处:三 op 模块 docstring「补料路线与优先级」段,负责人裁定);②toast 正判门控 = 前两次点击/等待后的轮探测「提示-无可刷缺口」,命中即判停收口,漏检由连点/连等封顶兜底(出处:`open_farm_window` 与 `farm_ticket_chain` docstring);③事务式记账 = 幂等判据 + 成功证据 commit + 拦截仅清判据位零回滚(出处:`confirm_ticket_farm`/`_settle_farm_accounting` docstring);④开拓力拦截 = 识别「开拓力补充」弹窗 → 取消 → 原路清场 → POWER_CAPPED,永不触碰「确认」(星琼红线,出处:三线守卫分支注释)。
- 文档清单:本篇单文档(无详设划分——载体选型/helper 清单/迁移计划同属一个方案面,拆详设不减复杂度);landing.md 与 README.md 索引由设计定稿后补。
- trace 依赖:迁移步骤 S6 触碰 `upgrade_trace.py`,该文件以行迹对齐批(迭代2:事务式记账 / 开拓力守卫 / 补料优先级翻转)为先,S6 等行迹批落地后执行;S1–S5 不触碰 trace 文件,与行迹批无冲突面。

### 0.1 负责人裁决记录(r1)

五条开放问题已裁,落点:
1. LC 计场时机:保留不收敛(维持域 README §6 既有裁定);
2. 判停返回词表:本次保留,统一另立 API 批;
3. H10/S7 浮层清场链:纳入本迭代 P2 尾批(放弃判据见 §4 S7);
4. trace 计数器改名:接受(收敛动作;随 S6 前置批完成,测试属性行跟改上限 1 处);
5. 记账日志模板统一:执行(收敛动作)。

两项新涌现问题亦已裁:S6 前置判据显式化(三字段齐 + 幂等判据式记账时机,见 §4 S6 前置);`enter_dungeon` 留后续批(见 §1.1 #10 / §3.3 #14)。

## 1. 问题与动机

### 1.1 现状症状:机械复制面盘点(逐项核实)

| # | 复制面 | 现状 | 依据(符号名) |
|---|---|---|---|
| 1 | 确认框次数设置与读数 | 三线逐字近同,最大复制面;差异仅日志前缀与一处 fail 文案;char/LC 版入口清判据位,trace 版无 | 三 op 各自 `_set_farm_times` / `_read_farm_times` |
| 2 | toast 门控开窗 | char/LC 逐字同构(`open_farm_window` 整节点体);trace 同语义异载体(`farm_ticket_chain` 链入口段,连点计数载体) | `open_farm_window`(char/LC)、`farm_ticket_chain`(trace) |
| 3 | 事务式记账 | char 原生,LC 已对齐(迭代1),两线 `confirm_ticket_farm` 节点体逐字同构 + `_settle_farm_accounting` 同款;trace 待行迹批 | `confirm_ticket_farm` / `_settle_farm_accounting`(char/LC) |
| 4 | 开拓力守卫 | char/LC 各三处:confirm 拦截作废 / `manual_fight` 拦截 / 返回分类取消弹窗;trace 待行迹批 | `confirm_ticket_farm` / `manual_fight` / `back_to_ascend` / `back_after_farm` 内守卫分支 |
| 5 | 无名记名防线 | char 与 LC 的 `_guard_unnamed_manual_farm` + `_read_character_name`(双屏读名)逐字同构(迭代1移植产物);连同入口常规路径的两处内联读名拦截,合计六处(4 处 guard 调用点 + 2 处内联) | `_guard_unnamed_manual_farm` / `_read_character_name`(char/LC)、`check_entry` 常规路径读名段 |
| 6 | 副本态判定与手动入口分支 | char/LC 的 `farm_in_dungeon` 非券路分支(编队双锚判定 + 三态分流 + 点挑战按钮)近字同构,差异 = 副本标题锚表覆盖面(char 双锚:拟造花萼+凝滞虚影;LC 单锚:拟造花萼) | `_in_dungeon_state`(char)、`farm_in_dungeon` / `manual_fight` 双锚判定(char/LC) |
| 7 | 等级读区(核实补充) | char `_read_ascend_level` 与 LC `_read_lc_level` 同 regex(`NN/MM` 取当前值)同构,仅画面/area 名不同;trace `_read_panel_level` 是「等级N」无比例的另一形态,不同构 | `_read_ascend_level` / `_read_lc_level` / `_read_panel_level` |
| 8 | 返回分类浮层清场链(核实补充,P2) | `back_to_ascend`(char)与 `back_after_farm`(LC)的弹窗逐层关闭段(结果框/补充弹窗/选次数框/资源窗口/编队画面/副本画面)近字同构,识别查询顺序一致;路由尾段(FARMED 判 / 预算内联 / 落点分流)是策略,不同构 | `back_to_ascend` / `back_after_farm` |
| 9 | 构造校验(核实补充) | farm 参数 ValueError 检查三线逐字同构 | 三 op `__init__` 参数校验段 |
| 10 | 进入副本节点(核实补充,已裁留后续批) | `enter_dungeon` 节点体(资源窗口点「进入」→ until 挑战锚)char/LC 逐字同构,单调用复制 | `enter_dungeon`(char/LC);去向裁决见 §0.1 |

### 1.2 根因归层

根在**约定层**:域 README §2.3 政策(「同构但不共用」)在两线时代正确,第三份同构落地后机械复制面失去单一源——同一段实现存三份,修 bug/调参须人工同步,漏一处即行为漂移;同时策略差异与机械同构混写在同一文件里,「哪些允许不同」没有判据。修根 = 给机械面立单一源(helper 模块)+ 给政策立新口径(§5 修订案),不是逐文件再抄一遍。

### 1.3 解决到哪 / 明确不解决什么

- 解决:§1.1 表 #1–#7、#9 的归并(§3/§4);#8 已裁纳入 P2(§0.1/§7);域政策修订(§5)。
- 不解决(防范围外溢):策略差异面(§3.3 不收敛清单);判停返回词表统一(调用方契约,已裁保留,§0.1);行迹线行为面(事务式记账/守卫/优先级翻转 = 行迹批范围,S6 只做其落地后的机械接线);识别建档覆盖差异(LC 单锚扩到多副本类型 = 补建档批次的事,本迭代只参数化锚表机制、不动锚表内容);LC 关横幅硬编码坐标(`Point(960,120)`,坐标单一真相源的存量债,归并批不顺带改建档面);#10 `enter_dungeon`(已裁留后续批)、§3.3 #12 LEFTOVER 无名白烧(另立行为批)、§3.3 #13 起始等级读点(保留)——处置见 §3.3。

## 2. 载体选型

### 2.1 候选与结论

候选:a) 纯函数 helper 模块;b) 可复用 mixin;c) 公共基类。**结论 = a**:

- **状态归属**:char/LC 两线账本状态字段名已统一(`_farm_rounds` / `_farm_draws` / `_farm_times_set` / `_farm_window_wait_rounds` / `_capped` / `_stop_status`);trace 现为独立载体(`_final_status` / `_panel_farm_click_rounds` 等,现无 `_farm_draws` / `_farm_window_wait_rounds` / `_capped` / `_stop_status`),待行迹批 + S6 补齐同名(判据见 §4 S6 前置)。字段被测试直接断言/置位(出处:char 测试 `test_confirm_count_on_effective_click` 断言 `op._farm_rounds`/`op._farm_draws`;trace 测试直接置 `op._panel_farm_click_rounds = 2`)。状态必须留在 op 实例上——mixin/基类诱导状态随行为同迁,破坏测试锁面;纯函数首参收 op,状态归属天然清晰。
- **测试缝**:现行测试在 op 类上 monkeypatch 私有方法与识别接口(出处:三测试文件 `_install_script`,桩目标含 `UpgradeCharacterOp._read_farm_times`、`UpgradeLightConeOp._set_farm_times`、`UpgradeTraceOp.save_screenshot` 等)。纯函数 + op 薄委托(§2.3)让缝永远在 op 类上,与现行测试写法零冲突;mixin 会把「缝在哪」变成继承问题。
- **注册面**:op 注册靠 backend 扫描 `sr_od.application` rglob 自动发现(依据:域 README §1);helper 模块不含 Operation 子类,落域根不影响注册。
- **基类否决理由**:三线节点图、入口画面流、状态机载体差异大(char `_stop_status` vs trace `_final_status` + `close_panel` 落账),公共基类必然长成「参数 god + 钩子全家桶」,与「策略差异留 op」判据冲突。

### 2.2 进 helper / 留 op 判据

**进 helper,三条同时满足**:
1. 机械同构:两线以上逐字/近字相同,差异可全部用常量或参数表达;
2. 语义单一:helper 做一件事,内部无**线间**策略分叉(三线合法不同的分支留 op;三线同形的配置分支——如 H8b 所在分流链的 use_fast_ticket 券/手动二选一,三线语义相同——允许进 helper);
3. 缝可保留:一切对识别/回合接口与账本状态的访问都经 op 实例属性(§2.3)。

**留 op**:节点图编排(节点/边/状态出口);按钮分流策略(补料优先级的分支表达,三线合法不同);计场时机(README §6 既有裁定);入口画面流差异;返回词表与状态机载体差异;横幅/面板收尾载体差异。

### 2.3 缝保留规则(测试锁前提,本设计的核心约束)

归并后测试锁面必须不变,规则三条:

1. **op 私有方法保留为委托缝(清单如实,现存即保留)**:char/LC 的 `_set_farm_times` / `_read_farm_times` / `_settle_farm_accounting` / `_read_character_name` / `_guard_unnamed_manual_farm` / `_read_ascend_level`(char)/ `_read_lc_level`(LC)全部保留,签名不变,方法体改为一行委托到 helper 模块函数(例外:线私有入参映射可留在缝方法内,现唯一实例 = LC `_read_lc_level` 的画面/area 选择映射——映射入参即缝参数,无法外移);`_in_dungeon_state` 仅 char 存在(LC 为内联单锚查询,无此方法),无测试桩,保留无妨但计入清单如实声明——monkeypatch 目标不变,既有桩照常生效(含 char/LC 测试里「包装真实现再替换」的写法:`real_set = UpgradeCharacterOp._set_farm_times` 后包计数壳,出处:char 测试 `test_confirm_count_on_effective_click`)。trace 现存缝(`_read_panel_level` / `_read_panel_category` / `_set_farm_times` / `_read_farm_times`)同规则处理;S6 为 trace 新增 `_settle_farm_accounting` 薄缝,与 char/LC 缝面对齐。
2. **helper 经 op 属性访问一切依赖**:helper 函数实现内部,凡访问识别接口(`round_by_find_area` / `round_by_find_and_click_area` / `screenshot` / `save_screenshot`)、回合接口(`round_success` / `round_wait` / `round_retry` / `round_fail`)与账本状态(`_farm_times_set` / `_farm_window_wait_rounds` / `_capped` / `_stop_status` / `_farm_rounds` / `_farm_draws`),一律通过首参 op 的实例属性访问(`op.round_by_find_area(...)`)——类级 monkeypatch 在属性查找上生效,helper 代码在测试里自动走桩。实证锚点:toast 用例把 `save_screenshot` 桩在 op 类上(出处:三测试文件 toast 相关用例),helper 化后 `op.save_screenshot(...)` 仍被拦住。
3. **helper 之间禁止直调**:helper 内部凡调用另一缝语义(读次数/设次数/记账/读名/守卫等),必须经 `op.<缝方法>(...)` 委托,禁止 helper 函数直接互调——直调会绕开类级桩(char 测试 `_read_farm_times` 读数桩 / `_set_farm_times` 计数壳桩 / `_read_character_name` 读名计数桩全数失效,`test_farm_times_plus_compensation` 等用例必红)。调用链形态恒为 缝→helper→(op 缝)→helper,一层委托无递归;缝方法内不做第二段逻辑(线私有入参映射例外同规则 1)。

### 2.4 参数化方式(画面名/area 名/常量如何入参)

- **每线一份 `UpgradeLineSpec`**(frozen dataclass,字段见 §3.1),在各自 op 模块内以模块常量实例化——线私有值(画面名/日志前缀/判停返回词/锚表/消耗常量)的单一源留在 op 模块,helper 只收引用。README §6「三线消耗常量各自独立、勿互相复用」的裁定保留:常量定义不迁移,spec 只作入参搬运。
- **三线同值的共享画面名/area 名**(快速刷取两弹窗、培养资源窗口、挑战副本、开拓力补充弹窗等)上移为 helper 模块常量,op 模块改为引用——消掉三份重复字面量(笔误漂移面)。
- helper 首参恒为 op(Protocol 类型约束,§3.1),次参按需为 spec 或显式参数;不引入 `**kwargs`,构造参数显式(项目硬约束)。

### 2.5 落位

`src/sr_od/application/cultivation/upgrade_common.py`(域根平铺,与 `__init__.py` 同级)。域根不放 Operation 子类与识别器,不触注册扫描;`__init__.py` 不暴露模块(项目惯例),消费方直接 import 模块路径。

## 3. helper 清单

### 3.1 常量、spec 与宿主协议

```python
# 共享画面名常量(三线同值,单一源上移;area 名常量按 helper 需要同法上移)
FAST_FARM_DIALOG_SCREEN = '快速刷取弹窗'
FAST_FARM_RESULT_SCREEN = '快速刷取结果弹窗'
RESOURCE_WINDOW_SCREEN = '培养资源窗口'
CHALLENGE_SCREEN = '挑战副本'
POWER_DIALOG_SCREEN = '开拓力补充弹窗'

@dataclass(frozen=True)
class UpgradeLineSpec:
    log_prefix: str                        # 日志前缀:晋阶 / 光锥晋阶 / 行迹升级
    stop_status: str                       # 材料判停返回词(char MATERIAL_CAPPED / LC LIGHT_CONE_CAPPED)
    ascend_screen: str                     # 养成界面画面名(角色-等级提升 / 光锥-等级提升 / 角色-行迹)
    dungeon_title_areas: tuple[str, ...]   # 挑战副本画面副本类型标题锚表(编队双锚反证用)
    name_read_screens: tuple[str, ...]     # 读名区双屏迭代序(手动路线记名用)
    reentry_hint: str                      # 读名失败指引文案(就地起跑形态)
    trailblaze_per: int                    # 每次刷取消耗开拓力(记账日志用,常量定义留各 op 模块)
    ticket_per: int                        # 每次刷取消耗快速刷取券(记账日志用)
    farm_open_max_attempts: int = 4        # 开窗/面板钮漏检封顶(点击尝试次数,语义见 H5)

class UpgradeFarmHost(Protocol):
    """helper 所需的 op 宿主面(结构化类型,三 op 隐式满足,不继承)。
    声明 helper 访问的全部成员:ctx / screenshot / last_screenshot /
    round_by_find_area / round_by_find_and_click_area / round_success /
    round_wait / round_retry / round_fail / save_screenshot /
    farm_times_per_round / farm_dungeon / use_fast_ticket /
    _farm_rounds / _farm_draws / _farm_times_set / _farm_window_wait_rounds /
    _farm_dialog_wait_rounds / _capped / _stop_status / _char_name /
    及各委托缝私有方法(_set_farm_times / _read_farm_times /
    _settle_farm_accounting / _read_character_name / _guard_unnamed_manual_farm /
    _in_dungeon_state(仅 char))。
    trace 待行迹批+S6 补齐的同名字段(_farm_draws / _farm_window_wait_rounds /
    _capped)按 §4 S6 前置判据纳入。"""
```

### 3.2 helper 签名与语义(逐个,含三线差异参数化)

**H1 构造校验**
```python
def validate_farm_params(farm_times_per_round: int, farm_rounds_max: int) -> None
```
语义 = 三线 `__init__` 现有两条 ValueError(次数须正数或 -1 拉满;预算 ≥1),文案不变。纯函数,三 op `__init__` 直接调用。trace 的 target 非空校验是线私有,留 trace。

**H2 确认框次数设置对**
```python
def read_farm_times(op: UpgradeFarmHost) -> int | None
def set_farm_times(op: UpgradeFarmHost, spec: UpgradeLineSpec, target: int) -> OperationRoundResult
```
语义 = 现读「刷取次数 N」→ target=-1 点「^」拉满 / 正数点「+」补差、达标即成;实际设到值写 `op._farm_times_set`;失败显式 round_fail 交节点预算兜底。三线差异参数化:日志前缀入 spec;**统一收敛一处**——入口清判据位(`op._farm_times_set = 0`,char/LC 形态)对 trace 生效。trace 收敛无行为变化:其调用点前置判据 `_farm_times_set == 0` 才进 set,set 失败路径全部 round_fail(节点预算耗尽终止),不存在 set 失败重入;统一防未来接入点踩残留旧值(依据:LC `_set_farm_times` docstring「设置失败不得残留旧值,否则重入轮拿旧判据跳过设次数直接确认」)。fail 文案「券刷连刷次数未能设到」收敛为统一「刷取次数未能设到」(fail 文案不被测试断言,词面收敛)。

**H3 事务式记账 commit**
```python
def settle_farm_accounting(op: UpgradeFarmHost, spec: UpgradeLineSpec) -> None
```
语义 = 以 `_farm_times_set` 非零为未记账判据:非零则 `_farm_rounds += 1`、`_farm_draws += 设到值`、按 spec 消耗常量记日志、判据位清零(WAIT 重入轮不重复计)。char/LC 现模板已逐字同构,统一入 helper,日志模板参数化 `log_prefix`(文案微调不锁测试;裁决 5 已裁执行,见 §0.1)。trace 接入前提 = §4 S6 前置判据(三字段就位 + 幂等判据式记账时机);`_farm_draws` 字段语义 = 券刷累计次数,与 char/LC 同名同义。

**H4 券确认节点骨架**
```python
def confirm_ticket_farm_step(op: UpgradeFarmHost, spec: UpgradeLineSpec) -> OperationRoundResult
```
语义 = `confirm_ticket_farm` 节点体整段:WAIT 重入幂等分类,**查询顺序与现实现逐条一致(①补充弹窗 probe 先于②结果框 probe**,依据 char/LC `confirm_ticket_farm` 开头两 probe 次序):①补充弹窗在场 → 判据位清零 + `_capped` + `_stop_status='POWER_CAPPED'` + POWER_BLOCKED;②结果框在场 → 经 `op._settle_farm_accounting()`(缝,H3)记账 + RESULT_OPEN;③确认框不在 → 慢询等待;④确认框在 → 未设次数先经 `op._set_farm_times(op.farm_times_per_round)`(缝,H2),再点确认,helper success 后经 `op._settle_farm_accounting()`(缝,H3)记账——缝间调用方向遵守 §2.3 规则 3。char/LC 节点体逐字同构(依据:§1.1 #3),返回词 POWER_BLOCKED 两线一致。op 节点方法保留装饰器与签名,体改一行委托。trace 是否接入由行迹批落地后的链形态与 §4 S6 前置判据决定。

**H5 toast 门控开窗(H5a 节点骨架 / H5b 探测谓词)**
```python
# H5a
def open_farm_window_step(op: UpgradeFarmHost, spec: UpgradeLineSpec) -> OperationRoundResult
# H5b
def no_farm_gap_toast_hit(op: UpgradeFarmHost, toast_screen: str, attempts: int) -> bool
```
`open_farm_window_step`(H5a)= char/LC `open_farm_window` 节点体整段:探测门(`attempts <= 1` 时查「提示-无可刷缺口」,命中 → `_capped` + spec.stop_status + 留证截图 + FARM_WINDOW_FAIL 判停)→ 点击-until 资源窗口 → `is_fail` 或封顶(漏检兜底)→ FARM_WINDOW_FAIL 判停收口。`no_farm_gap_toast_hit`(H5b)= 探测谓词,供 trace 链入口段复用(trace 反应不同:转 CLOSE_PANEL 落账,载体差异留 trace)。两函数关系定死:H5a 探测门内联实现自身查询(不经 H5b 直调);H5b 仅 trace 链入口段消费——H5b 无自有桩面,直调亦不破坏测试锁,显式写明避免实现期二义。
**封顶语义统一(漂移收敛项)**:char/LC 以等待轮计数、`>= 3` 判停,换算 = 4 次点击尝试、前两次轮探测;trace 以点击计数、常量 4 封顶——数值语义逐轮等价(逐轮演算:探测发生在第 1、2 次尝试轮,第 4 次尝试后判停,两线一致)。统一为「尝试计数 ≤1 探测 / 尝试 ≥ spec.farm_open_max_attempts(=4)判停」,计数器统一用 op 属性 `_farm_window_wait_rounds`(char/LC 现名;trace 现名 `_panel_farm_click_rounds`,改名随 §4 S6 前置批完成,裁决 4 已裁,见 §0.1)。

**H6 无名记名防线**
```python
def read_character_name(op: UpgradeFarmHost, spec: UpgradeLineSpec) -> str | None
def guard_unnamed_manual_farm(op: UpgradeFarmHost, spec: UpgradeLineSpec, *, hint: str | None = None) -> OperationRoundResult | None
```
语义 = 双屏迭代读名区 OCR「命途/名字」取「/」后段(屏序入 spec.name_read_screens;area 未建档跳过不报错,保持现行为);guard = 读名写入 `_char_name`,读名失败且「farm_dungeon 且非券路线」授权时 round_fail(消息 = 就地起跑形态 spec.reentry_hint 或入口形态 hint 覆盖)。归并四个调用点:ALREADY_ASCEND 直入 / None 帧探针出口用默认 hint;入口常规路径(详情 TAB / 光锥 TAB)传各自 hint——一条红线一个实现。`_char_name` 属性名三线已统一。

**H7 等级读区(NN/MM 比例形态)**
```python
def read_level_ratio(op: UpgradeFarmHost, screen_name: str, area_name: str) -> int | None
```
语义 = 画面 + area 内 OCR `(\d+)\s*/\s*\d+` 取当前值。char `_read_ascend_level` 委托(单屏单区);LC `_read_lc_level` 委托(area 选择逻辑「TAB 读区-等级 / 界面读区-当前等级」留在 LC 委托方法内——映射是线私有知识)。trace `_read_panel_level` 不同构,留 trace。

**H8 副本态判定与副本刷取分流**
```python
def is_dungeon_state(op: UpgradeFarmHost, spec: UpgradeLineSpec, screen) -> bool
def farm_in_dungeon_step(op: UpgradeFarmHost, spec: UpgradeLineSpec) -> OperationRoundResult
```
`is_dungeon_state` = spec.dungeon_title_areas 任一在场(锚表参数化:char 传双锚,LC 传单锚——锚表内容=建档覆盖面,各线保留现状,扩充归补建档批次);`farm_in_dungeon_step` = `farm_in_dungeon` 节点体整段(券路:点「快速刷取副本」→ 确认框连开有界自旋 `_farm_dialog_wait_rounds >= 4` 留证显式失败;手动路:编队双锚判定「队伍标题在 + 副本标题不在」三态分流 + 点挑战按钮)。手动入口的安全判定(编队钮与挑战按钮 rect/text 重叠、双锚防连环误开战)收敛为单一实现——这是事故教训的防线,单源优先(依据:两线 `farm_in_dungeon`/`manual_fight` docstring 的双锚警示与实测事故记载)。

**H9 开拓力守卫**
```python
def guard_power_blocked(op: UpgradeFarmHost, spec: UpgradeLineSpec, screen, *, on_intercept: Callable[[], None] | None = None) -> OperationRoundResult | None
```
语义 = 「开拓力补充」弹窗在场 → `on_intercept()`(可注入回调,char 传「作废 `_squad_clicked` 旗标」)→ `_capped` + `_stop_status='POWER_CAPPED'` + 日志 → round_success('POWER_BLOCKED');弹窗不在返回 None。星琼红线(永不点「确认」)在单一实现内声明。`manual_fight` 节点头的守卫分支换此 helper;返回分类的补充弹窗取消层属 H10(P2);confirm 内拦截属 H4(需作废账本判据位,语义不同不复用)。trace 待行迹批补守卫后接入——**载体差异(见 upgrade-align-2 §0)**:trace 守卫是链内自持清场形状(置位后留守节点逐轮清场,终态载体 `_final_status`),与 H9 单发拦截形状不同;S6 接入时须扩展 on_intercept/状态载体,或明确 trace 不接入 H9(其守卫已自持,仅归并不接入)。

**H10 返回分类浮层清场(P2,已裁纳入,见 §0.1/§7)**
```python
@dataclass(frozen=True)
class OverlayLayer:
    probe_screen: str; probe_area: str; click_area: str
    until_not: tuple[tuple[str, str], ...]; success_log: str

def close_matching_overlay(op: UpgradeFarmHost, layers: Sequence[OverlayLayer]) -> OperationRoundResult | None
```
语义 = 按层表顺序逐层探测,命中即点关闭控件(until_not 验证)+ round_retry 交回分类重判,全 MISS 返回 None。char/LC 的 `back_to_ascend`/`back_after_farm` 用各自的层表常量(弹窗集两线同),节点保留策略段(FARMED 判 / 失败预算内联 / 落点分流 / 画面级回退);**硬约束:层表顺序必须与现实现逐条一致**,剧本测试的逐查询序才不变。

### 3.3 不收敛项清单(逐项建议)

| # | 漂移项 | 建议 | 依据/理由 |
|---|---|---|---|
| 1 | 按钮分流策略(char:补全按钮在场=缺口合成覆盖,授权补全永不刷取、未授权判停;LC:未授权补全转刷取由 toast 兜底;trace:行迹批翻转) | 保留 | 已定案语义的三线合法表达,是策略不是机械同构;分支留在 `upgrade_loop` |
| 2 | 计场时机(char 离开编队态计场带 `_squad_clicked` 旗标 vs LC 点击时计场) | 保留(已裁) | 域 README §6 明文「刻意保留」;裁决记录见 §0.1/§7 |
| 3 | 材料判停返回词(char MATERIAL_CAPPED / LC LIGHT_CONE_CAPPED) | 保留(已裁) | 调用方(app 编排)契约,统一 = API 破坏;裁决记录见 §0.1/§7 |
| 4 | 横幅收尾载体(char:双横幅标题 + 独立材料返还页分支 + `_close_result_banner`;LC:晋阶横幅+材料返还顺序页,点空白用硬编码 `Point(960,120)`) | 保留 | 浮层语义与顺序不同,强收敛造参数怪;LC 硬编码点属存量债,归并批不顺带改建档面(观察项) |
| 5 | 沿计数统计(`_banner_seen` 双横幅分计 vs `_promo_banner_seen` 单横幅计) | 保留 | 统计口径载体随横幅载体走;字段子集也不同(收尾日志字段集三线不一) |
| 6 | 收尾关面板(trace `close_panel`,`_final_status` 落账 + `_CLOSE_PANEL_MAX_ROUNDS`) | 保留 | 面板退出是 op 出口契约,非横幅瞬态;载体与 char/LC 判停收尾本质不同 |
| 7 | 等待/超时常量(`_ASCEND_SETTLE_SEC` / `_FILL_SETTLE_SEC` / `_LC_FIGHT_POLL_SEC` / `_FARM_POLL_SEC` / `_TRACE_SETTLE_SEC` 等) | 保留 | 实机逐线标定值,收敛无收益 |
| 8 | 入口画面流与重走入口链(char:重选角色;LC:TAB 读名一致校验才接管) | 保留 | 画面流策略差异,防升错防线的实现形态不同 |
| 9 | 确认框次数记忆行为描述(char docstring「游戏记忆上次值」vs LC/trace「不记忆,重开=1」) | 注记不改 | 游戏行为实测口径差异;H2 算法「现读→补差→达标即成」对两种行为都成立,helper 无需感知,docstring 各自保留实测记录 |
| 10 | trace 面板读区(`_read_panel_level`「等级N」/ `_read_panel_category` / `_panel_category_ok`) | 保留 | 读区语义不同构(无比例、文本等值校验),是 trace 起跑闸策略的组成部分 |
| 11 | 开窗封顶数值形态(等价性) | 收敛(非不收敛项) | 已并入 H5,见 §3.2 封顶语义统一 |
| 12 | char LEFTOVER 失败重发子路径无名白烧残留 | 保留(不解决,另立行为批) | 承接迭代1 §3 评估清单;行为缺口非口径漂移(触发窗口窄:中断现场恰为战斗失败画面),不属于机械归并范围 |
| 13 | 起始等级读点(char 于升级循环首轮抵达晋阶界面时读;LC 于入口核对即读) | 保留 | 承接迭代1 §3 评估清单;统计口径读点载体差异,收敛须动行为时序,非机械面 |
| 14 | `enter_dungeon` 节点体(§1.1 #10) | 已裁:留后续批 | 负责人裁决(§0.1):逐字同构但单调用复制质量低,本迭代不扩 H11 |

## 4. 迁移计划

每步 = 一个独立 commit(逐文件点名 add)、独立可回滚;每步完成后跑受影响测试全量一次通过才提交。改任何 Python 代码后须重启项目 MCP server 才对运行时生效(依据:项目 AGENTS.md §6),S1–S7 各步验收前各自重启复验。

**S1 helper 地基 + char 接线**
- 范围:新建 `upgrade_common.py`(常量 + `UpgradeLineSpec` + `UpgradeFarmHost` + H1/H2/H3);`upgrade_character.py` 接线:`__init__` 校验调 H1,`_set_farm_times` / `_read_farm_times` / `_settle_farm_accounting` 改一行委托(签名不变),共享画面名常量改引 helper 模块。LC/trace 不动。
- 测试锁处置:全部原位,**零改动**。判据 = `test_upgrade_character.py` 全绿(缝保留规则的第一次实证:类级桩照常拦住委托缝)。
- 回滚:revert 本 commit(此时 helper 仅 char 消费)。

**S2 LC 机械跟随**
- 范围:`upgrade_light_cone.py` 同款接线(H1/H2/H3)。
- 测试锁处置:全部原位,零改动;`test_upgrade_light_cone.py` 全绿。
- 回滚:revert 本 commit(S1 的 helper 仍被 char 使用,不受影响)。

**S3 记名防线 + 等级读区**
- 范围:H6/H7 入模块;char/LC 的 `_read_character_name` / `_guard_unnamed_manual_farm` / `_read_ascend_level` / `_read_lc_level` 改委托;四个记名调用点(直入/探针/入口常规路径×两线)统一走 H6(hint 参数区分形态)。
- 测试锁处置:全部原位,零改动(缝保留:`_read_character_name` 被两线测试桩住读名计数;guard 行为断言用例原样通过)。
- 回滚:revert 本 commit。

**S4 券确认骨架 + toast 门控开窗**
- 范围:H4/H5 入模块;char/LC 的 `confirm_ticket_farm` / `open_farm_window` 节点保留装饰器与签名、体改一行委托。**硬约束:helper 内识别查询顺序与现实现逐条一致**(probe 先于 click、结果框先于确认框、封顶时机等),这是本步行为等价的验收锚。
- 测试锁处置:全部原位,零改动。判据 = 两线 toast 三用例(命中即停/门控抑制/漏检封顶)+ 券确认幂等/真时序记账用例全绿;`_farm_window_wait_rounds` 计数语义不变。
- 回滚:revert 本 commit。

**S5 副本分流 + 开拓力守卫**
- 范围:H8/H9 入模块,接线分写:char 的 `_in_dungeon_state` 改委托 H8a(`manual_fight` 双锚判定继续经缝调用),`farm_in_dungeon` 体改委托 H8b;LC 无 `_in_dungeon_state` 方法(副本标题查询为内联),内联处替换为 H8a 调用,`farm_in_dungeon` 体改委托 H8b;`manual_fight` 头部守卫两线换 H9(char 传 `on_intercept` 作废旗标回调);LC 构造 spec 时补 `dungeon_title_areas=('标题-拟造花萼',)`。计场时机不动(不收敛项 #2)。
- 测试锁处置:全部原位,零改动。判据 = 手动路线全链 / 双锚防误开战 / 开拓力拦截用例全绿。
- 回滚:revert 本 commit。

**S6 trace 接线(等行迹批落地后执行)**
- 前置(显式判据):行迹对齐批(事务式记账 / 开拓力守卫 / 补料优先级翻转)已落地并对表,且满足——①账本三字段就位:`_farm_draws` / `_farm_window_wait_rounds`(由 `_panel_farm_click_rounds` 改名)/ `_capped`;②记账时机为幂等判据式(成功证据 commit,非确认点击时预记账)。满足则按下方范围接线;若行迹批保留确认点击时记账口径,**S6 降级为只接 H1/H2/H5b**(H3 不接,trace 记账留在 op,H4 不接),其余同。
- 范围:trace `__init__` 校验调 H1;`_set_farm_times` / `_read_farm_times` 改委托 H2(收敛:入口清判据位);新增 `_settle_farm_accounting` 薄缝(与 char/LC 缝面同形,§2.3 规则 1)并接 H3(前置①已含 `_farm_draws` 字段);券刷链入口段 toast 探测换 H5b、封顶常量 `_PANEL_FARM_CLICK_MAX` 收敛进 spec(`farm_open_max_attempts=4`);链内确认段若与 H4 形态一致则接入 H4,否则保留链骨架只换 H2/H3 件(裁决落在本步实施时,以链形态为准)。
- 测试锁处置:计数器改名与其测试属性行(`test_farm_chain_toast_probe_gated_and_click_capped` 直接置 `op._panel_farm_click_rounds` 的一行)随前置批(行迹批)完成;若前置批落地时未跟改该测试行,S6 顺带补上——本迭代对该测试的改动上限 = 恰 1 处属性行。其余全部原位零改动(剧本逐查询序不变的验证同 S4 硬约束)。若行迹批改了链结构导致剧本失配,该部分测试随行迹批的改动面走,不属本步新增改动。
- 回滚:revert 本 commit;不影响 S1–S5。

**S7 返回分类浮层清场(P2,已裁纳入,见 §0.1/§7)**
- 范围:H10 入模块;char `back_to_ascend` / LC `back_after_farm` 的机械清场段(§1.1 #8 所列弹窗层)改层表委托,路由尾段(策略)留 op;识别查询顺序逐条保持。
- 测试锁处置:目标 = 全部原位零改动;若实施中发现任何剧本查询序必须改,本步立即放弃不实施(层序耦合比复制面代价高)——放弃不阻塞迭代收尾。
- 回滚:revert 本 commit。

**依赖链**:S1 → S2 → S3 → S4 → S5 → S6 → S7 顺序执行(后步复用前步的模块与 spec);回滚按逆序,整批放弃时先回消费步再回 S1(模块地基)。

## 5. 域 README §2.3 政策修订案

### 5.1 修订后条文草案(替换 README §2 第 3 条)

> 3. **分域即分治 + 域内共用件**:跨线大域(遗器/光锥/角色养成线)之间零 import、不做预防性抽象、各自持完整实现副本——这一层不变;是否归并的评估时机 = 第三份同构复制出现时(跨件半问)。评估结论按两分法落地:
>    - **策略差异留 op**:分支顺序、路由语义、计场时机、返回词表、收尾载体这类「为什么这么做不同」的实现,留在各线 op,禁用参数化糊弄成假同构;
>    - **机械同构进域内 helper**:两线以上逐字/近字相同、差异可全参数表达、且经 op 实例属性访问可保测试缝的实现段,收进域根共用模块(cultivation 域首例 = `upgrade_common.py`)。helper 三纪律:不持状态(状态归 op 账本属性)、不做线间策略分叉(三线合法不同的分支留 op 节点图;三线同形的配置分支可入 helper)、一切识别/回合/账本访问与缝间调用经 op 属性(测试桩在 op 类上生效)。
>    - **第四形态接入**:新升级类 op 构造自己的 spec 常量(`UpgradeLineSpec` 线私有值)与薄委托私有方法,复用 helper 不复制实现;helper 缺新画面/新语义时扩参数(带向后兼容默认值),不 fork 副本;helper 变更须过全部已接入线测试。

### 5.2 配套修订点

- README §4 末句「三线各自完整实现,不抽共用底层;三条线都落地后再评估是否域内归并」→ 改为「机械同构面已按 §2.3 两分法收进 `upgrade_common.py`;策略差异与识别建档覆盖仍各线自持」。
- README §5 op 清单表状态列与 §6 升级 op 家族失败适配:不因本迭代改语义,仅 S 落地后如需注明 helper 引用则随正本更新批顺带,不改内容。

### 5.3 正本更新清单(供 landing 消费)

- README §2 第 3 条 ← S1–S7 全部落地后按 §5.1 条文替换;
- README §4 末句 ← 同上批按 §5.2 改写;
- cultivation 正本区若另有升级 op 结构描述节,随实现落点核对(landing 阶段核实,本设计不预判存在)。

## 6. 风险与回滚

### 6.1 回归风险面

| # | 风险 | 成因 | 对策 |
|---|---|---|---|
| R1 | 识别查询序漂移 | helper 重排探测顺序 → 剧本测试红、实机轮次行为变化 | S4/S7 硬约束「查询顺序逐条一致」;既有剧本测试全绿 = 验收锚 |
| R2 | 测试缝断裂 | helper 直接引用模块函数或 helper 直调 helper,绕开 op 属性 → 类级 monkeypatch 失效,假绿或 AttributeError | §2.3 缝保留规则三条(属性访问 + 缝直调禁令);S1 首步即实证该规则 |
| R3 | 账本属性名漂移 | 计数器/账本字段被顺手改名 → 测试直接断言/置位的字段失配 | 属性名冻结清单(`_farm_rounds`/`_farm_draws`/`_farm_times_set`/`_farm_window_wait_rounds`/`_farm_dialog_wait_rounds`/`_capped`/`_stop_status`/`_char_name`);唯一改名点 = trace `_panel_farm_click_rounds` → `_farm_window_wait_rounds`(随 §4 S6 前置批完成,该测试属性行跟改上限 1 处) |
| R4 | 共享常量迁移笔误 | 画面名/area 名字面量上移时抄错 → 运行期识别失败 | 常量只迁移一次 + grep 旧字面量归零;ruff + 三线测试兜底 |
| R5 | spec 字段缺省/错填 | 新线接入时 spec 漏字段 → 运行期 None 传播 | spec 为 frozen dataclass 显式字段,漏填构造期即 TypeError;必填字段不设默认值 |
| R6 | 行迹批并行冲突 | S6 与行迹批触碰同一文件 | S6 严格排在行迹批落地后;S1–S5 文件面不含 trace |
| R7 | 行为等价误判 | 「逐字同构」判断有漏(如 char 版多入口清判据位) | §3.2 逐 helper 列明差异与收敛点;每步以既有测试零改动零红为行为等价的机器判据 |

### 6.2 分步回滚方案

- 每步单 commit、逐文件点名 add(并行卫生);任一步回归 → revert 该 commit,不影响未消费该步产出的其他线。
- 依赖逆序回滚:S7→S6→S5→S4→S3→S2→S1;整批放弃时按逆序全回,`upgrade_common.py` 随 S1 回滚消失,三 op 回到迁移前形态。
- S6 回滚不碰 char/LC;S7 可单独放弃(设计内已定义放弃判据)。

## 7. 开放问题处置记录(r1 已裁,逐条对应 §0.1)

1. **LC 手动路线计场时机**(点击时计场 vs char 离开编队态计场):已裁——保留不收敛,维持域 README §6 既有裁定,见 §0.1。
2. **材料判停返回词表**(char `MATERIAL_CAPPED` / LC `LIGHT_CONE_CAPPED` / trace `MATERIAL_CAPPED`):已裁——本次保留,统一另立 API 变更批,见 §0.1。
3. **H10/S7(返回分类浮层清场链)是否纳入本迭代**:已裁——纳入 P2 尾批,按 §4 S7 放弃判据执行,见 §0.1。
4. **trace 计数器改名**(`_panel_farm_click_rounds` → `_farm_window_wait_rounds`):已裁——接受,收敛动作(随 S6 前置批完成),见 §0.1。
5. **记账日志模板统一**(H3 参数化 `log_prefix`,三线日志词面微调):已裁——执行,收敛动作,见 §0.1。

## 8. 总验收判据

- `uv run ruff check` 对全部改动文件零告警;
- 主测试面:`test_upgrade_character.py` / `test_upgrade_light_cone.py` / `test_upgrade_trace.py` 全量一次通过:S1–S5 预期测试零改动零红;S6 预期零改动(计数器改名随前置批,该测试属性行跟改上限 1 处,见 §4 S6 测试锁处置);S7 若实施,剧本查询序不变;
- 消费方测试面:`test_upgrade_character_fail_adaptation.py` 与 `test_upgrade_light_cone_fail_adaptation.py`(直呼 `back_to_ascend` / `back_after_farm`,恰为 S7 目标节点)纳入每步受影响测试全量——S1–S6 不触碰该两节点,其零红为回归锚;S7 实施时以其全绿为查询序不变的消费方判据;
- 行为等价对照:三 op 的识别查询顺序、状态出口集合、账本字段名逐项与迁移前一致(机器判据 = 测试零红;人工判据 = 改后用 `describe_operation_flow` 核对节点图与迁移前一致);
- op 注册面不受影响:三 op op_id 不变,MCP 重启后 `list_operations` 可见性不变;
- 政策修订随正本更新批落 README(§5.3 清单清零)。
