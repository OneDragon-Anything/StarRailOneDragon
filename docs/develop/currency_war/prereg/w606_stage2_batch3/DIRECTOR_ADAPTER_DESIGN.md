# DIRECTOR_ADAPTER_DESIGN · default_strategy 适配器 + DirectorV2 开关 + 对拍硬门协议(W606 阶段2批③·第一段设计)

> 设计依据:W561 REPORT §三.1/§三.9/§四阶段2(唯一素材源)、W571 任务书阶段2批③定义、W598 对抗审计 REPORT §六修补清单、W588 DESIGN 批③挂账、ADR-0458 批③挂账、W599 加固后契约(contracts.py)与批②循环(director_v2.py)。
> 本段零 src 改动;第二段落码严格按本文,偏差须先改本文再动码。

---

## 0. 义务勾稽(W598 §六)

| W598 项 | 本批落点 |
|---|---|
| 1 frozen 容器/深拷贝/derive_snapshot | W599 已落,本批**只消费不削弱**;破警告路径改用 `derive_snapshot`(见 §5.3) |
| 2 映射义务清单 4 字段 + 双坐标系注释 | 适配器 §3.2 逐字段注入(含 `_pseudo_state` 漏拷 active_strategies 裂缝修复);DeployMove 参数取 `BenchChar.slot`(1-based)非容器下标,锁钉死 |
| 3 逆真值 fixture + 实机对拍硬门 | §7 对拍协议双门,写死不可被 sim 全绿替代 |
| 4 schema_version 执行点 / 语义改判纪律 | 执行点批②已落(DirectorV2 环顶 `require_schema_version`,本批不新增执行点);语义改判=version 必动纪律沿用 W599 契约注释 |

---

## 1. 总体形态

```
prep_director.py(现役 SrOperation,最小侵入)
  └─ 环入口分叉点(gate → bench-full 破警告 → update_target 之后、旧 while 之前)
       ├─ 开关关(默认)→ 旧 while 逐位不动(零行为漂移)
       └─ 开关开 → 构造 DirectorV2 端口组(全部复用现役件)→ run(session)
            → LoopOutcome → SrOperation 轮次语义映射(§6)→ round_*
```

**新增文件仅一个**:`decision_v2/adapter.py`。内容三件:
1. `snapshot_to_obs(snapshot, session) -> PrepObservation`(§3.1);
2. `decision_state(snapshot, session) -> GameState`(§3.2,含 4 义务字段注入与裂缝修复);
3. `make_decide_ports(strategy, config, director) -> _DirectorPorts` + `PrepAction↔AtomOp 映射`(§4)。

**default_strategy.py 预期零改**:适配是包外层(构造 obs-like 调现役 `decide_prep_action`),W598 攻击1 指出的 `_pseudo_state` 漏拷裂缝在适配器的 `decision_state` 构造中修复——现役伪态函数冻结不动(它还被 shop.py 等既有消费面引用,动它超出本批文件面纪律)。

---

## 2. 开关(默认关 + 开臂判据挂账)

### 2.1 载体与读取

- 字段:`DecisionV2Registry.director_v2_prep_enabled: bool = False`(registry 追加一字段,frozen dataclass 缺省值不破坏既有注入点)。
- 读取:`prep_director` 分叉点经 helper `director_v2_enabled(strategy)`:strategy 带 `.registry` 属性(DecisionV2Strategy)读其字段;否则读 `DEFAULT_REGISTRY`(=False)。**无配置文件新键、无 session 字段**——registry 是既有 A/B 合法载体(两套注册表各跑一臂),与 vd_p2_enabled 等同型。
- 默认关的合法性(策略开关生命周期门):唯一合法理由=**行为输入未就绪**——实机对拍数据(§7 门1)尚未采集,新环决策流在实机边界态上的等价性未证。开臂判据挂账见 §7.4。禁在判据满足前以「先开着试试」翻默认。

### 2.2 分叉点最小侵入(prep_director.py)

在 `while True:`(旧环主体)前插一段,伪码:

```python
if director_v2_enabled(match.strategy):
    return _run_prep_loop_v2(self, match, session, config)   # adapter 模块提供
# 旧 while 逐位不动
```

`_run_prep_loop_v2` 内:构造端口(§5)→ `DirectorV2(ports).run(session)` → 出口映射(§6)。共享前置(gate 稳定帧、bench-full 破警告、`free_bench_gold_wait` 清零、gated_hp 门、`update_target`)全在分叉点**之前**,新旧环共用零重写。分叉点之后的旧环主体一行不改。

---

## 3. Snapshot → 决策输入映射(适配器正向)

### 3.1 `snapshot_to_obs(snapshot, session) -> PrepObservation`

供现役 `decide_prep_action(obs, session, config)` 消费。逐字段:

| Snapshot 字段 | PrepObservation 字段 | 映射规则与边界 |
|---|---|---|
| bench | bench_chars | 剔 None;**元素 BenchChar 原样**(slot 1-based 保持,策略 DeployMove(from_slot=bc.slot) 直消费) |
| deployed | deployed_chars | 同上(0-3 前排/4-9 后排容器下标) |
| board | (obs 无对应) | 现役步级不消费;不映射(损耗声明:步级无 board 消费点,W598 对拍表已证) |
| gold + gold_trusted | state.gold + state_gold_trusted | 进 `decision_state` 构造的 GameState(§3.2);F2 语义保持:`gold_trusted=True` 才采用 gold |
| plane/round_num/node_type/level/level_up_cost | state.* | 同上 |
| hp + hp_readable | state.hp | 经 `cw_strategy.gated_hp` 门(session 锚重建,与现役 `_pseudo_state` 同款) |
| spheres | spheres | `RewardSphere(color,x,y,radius)` → `(color, Point(x,y), radius)` 元组列表 |
| boxes / tomes | boxes / tomes | `(None, Point(x,y))`——快照无槽号字段;现役策略只发 `OpenBox()/OpenTome()`(slot=None=第一箱/典籍),无槽号消费点,映射简化合法并锁注释 |
| free_bench_slots | free_bench_slots | **None → 9(BENCH_CAPACITY)**:保守方向裁决=「宁多收球(点击失败可自愈、defer 门兜住)不误卖(SellBench 不可逆)」;None→0 会误触发腾席链卖最弱,被否。此改判式是门2 fixture 的钉死对象 |
| deploy_vacancy | deploy_vacancy | None → 0(保守:不假装有空位;腾席链 a 跳过,b/c 正常) |
| front_occupied/back_occupied/front_size/back_size | 同名 | 原样(frozenset→set 拷贝) |
| shop_open / box_overlay_open / event_overlay | 同名 | 原样;event_overlay 非 None 在 DirectorV2 环顶已 bail,到不了 decide |
| spheres/boxes/tomes 空元组 | 空 list | 「观测事实非失读」语义保持 |
| classification.confident | — | 框架门已在环顶拦截;obs 构造假定 confident=True(断言,违者抛错) |

### 3.2 `decision_state(snapshot, session) -> GameState`(4 义务字段注入 + 裂缝修复)

构造策略内部链(`cw_recipe.decision_target` / `cw_plan.level_up_gate` / `cw_comps`)消费的 GameState。基座 = snapshot_to_obs 所得 state 的超集:

| GameState 字段 | 来源(单一源) | 备注 |
|---|---|---|
| bench/deployed/board | snapshot.bench/deployed(剔 None)/构造 board 计数 | deployed 下标=紧缩列表(与 cw_state 同构) |
| gold/plane/round_num/level/level_up_cost/node_type/hp | snapshot + session 锚 | node_type:快照值 or `session.node_type_current` or last_state(现役三级同序);hp 过 gated_hp |
| **dual_track_phase** | `session.dual_track_phase` | 义务①;现役伪态已拷,适配器同款 |
| **active_strategies** | `list(session.active_strategies)` | 义务②;**裂缝修复**:现役 `_pseudo_state` 漏拷此字段 → 链 a/c 的 `decision_target` 走 `cw_intention._direct_line_qualified`(cw_intention.py:332)与 `cw_economy.level_up_gate(strategies=)`(cw_economy.py:196/204)时持有策略判据静默失效为空。适配器显式注入,行为锁钉死(非空 session → decision_state.active_strategies 非空) |
| **equips** | `list(session.last_owned_equips)` | 义务③;cw_comps acquirability 消费 |
| **refresh_probs** | `session.last_state.refresh_probs`(heavy 观察帧携带,None=未读) | 义务④;消费点 cw_plan.py:414(D 牌采样)/discipline.py:522。陈旧性声明:该字段随 heavy 帧刷新,与现役 obs.state 同窗口,新鲜度契约=快照不承载 stale(W599 裁决),适配器不加第二源 |

> 修复声明:此注入使**新环步级路径**的持有策略判据比现役伪态路径更正确(现役链 a/c 恒空是活 bug)。对拍门(§7 门1)若出现「新环走了持有策略分支、旧环没走」的分歧,归因为此修复的**预期行为差**,记入 §7.3 已知合法差异清单,不算适配器缺陷。

---

## 4. PrepAction → AtomOp 映射(适配器反向 + 执行回放)

### 4.1 映射表(16 动作全集)

| PrepAction | op_key | domain | 语义注 |
|---|---|---|---|
| DeferSpheres | — | — | **不产 op**:`Decision(control=Defer(reason='球留置'))` |
| BailToOuter | — | — | `Decision(control=Bail(reason))` |
| PickBoxCard | `pick_box_card` | interact | 执行器默认选卡 |
| OpenBox | `open_box` | interact | |
| OpenTome | `open_tome` | interact | |
| ClickSpheres(k) | `click_spheres:{k}` | interact | k 入 key(不同上限=不同动作) |
| SellBench(slot) | `sell_bench:{slot}` | bench | slot=物理槽位 1-9(族 B 坐标系,prep_actions.py §13.1) |
| SellDeployed(row,slot) | `sell_deployed:{row}:{slot}` | bench | |
| DeployMove(from_slot,to_row,to_slot) | `deploy:{from_slot}:{to_row}:{to_slot}` | bench | from_slot=**BenchChar.slot 1-based**;to_slot=物理槽位(同族 B);双基并存即 contracts 注释防 off-by-one 的消费点 |
| LevelUp | `level_up` | shop | |
| EnsureShopOpen | `ensure_shop_open` | shop | |
| EnsureShopClosed | `ensure_shop_closed` | shop | |
| StartBattle | `start_battle` | battle | 屏蔽豁免对账见 §4.2 |
| RunBuyPhase | `run_buy_phase` | shop | CompositeOp(E1 两档制:保留组合形态,期望态单元上报归阶段3) |
| RunDeploy | `run_deploy` | deploy | |
| RunEquip | `run_equip` | equip | |

- `domain` 取值与 DirectorV2 同域批校验对接;适配器每步只发**单 op**(现役 decide_prep_action 单动作),批语义天然满足。
- **op_key 绑定回放**:AtomOp 契约无参数字段(批①骨架,不扩)。适配器在 decide 时登记 `op_key → PrepAction` 绑定(实例内 dict,每步覆盖);`execute` 端口按 `op.op_key` 查绑定取 PrepAction → `self._executor.execute(action)`(复用现役执行器与 F3 验证链,零重写),返回 `(progressed, detail)`。查无绑定 = 框架缺陷路径(record_defect + progressed=False)。

### 4.2 StartBattle 屏蔽豁免对账(ADR-0458 批③挂账闭环)

现役环豁免 StartBattle 不进屏蔽(被拒可无限重提案至 MAX_STEPS 强战)。DirectorV2 无动作类型豁免(规则中立),blocked 命中一律拒绝+stall。**等价性论证**:start_battle 连败 2 次 → 恢复原语 → 仍败且无关弹层 → 屏蔽 → 后续重提案走「拒绝+stall」→ STALL_LIMIT(5) 且恢复已试尽 → `_stall_gate` → F5 强制出战(BATTLE_FORCED)。即两环终局同为强制出战,差异仅在中间重试次数(现役 MAX_STEPS=60 次重提案 vs 新环 ~ stall 预算次)。
- 残差声明(不削 DirectorV2 防线):新环在「StartBattle 反复失败」场景重试次数显著少于旧环 → 更快强制出战。强制出战本身 = 现役既有语义(_force_battle),非新行为。
- 对拍门判据:门1 影子流不含该差异(影子只比 decide 输出);若实机门1 期间出现 start_battle 分歧按 §7.3 归因。
- 落码时锁:本论证注释写入 adapter.py 映射表项 + STATUS 挂账勾销。

---

## 5. DirectorV2 端口组(全部复用现役件)

| 端口 | 实现 | 备注 |
|---|---|---|
| decide | 闭包:snapshot → decision_state + snapshot_to_obs → `strategy.decide_prep_action(obs, session, config)`(r412 latch 采样随原函数继承)→ §4 映射 → Decision | session 原样透传(W571 定义) |
| observe(heavy) | `director._observe(heavy)` → obs → `snapshot_from_obs(obs, session, classification)` → Snapshot | snapshot_from_obs = snapshot_to_obs 的逆映射纯函数,None 语义逐字段按契约(读不到=None 禁兜底;free_bench_slots 失读=None,不做 §3.1 的 9 兜底——那是 decide 侧消费映射,方向不同勿混);classification:备战主画面 → `SubstateClassification('prep_shop', confident=True)`;子态注册表收拢批(1a)产物若已落,消费其分类结果 |
| execute | §4.1 绑定回放 → `director._executor.execute(action)` | 现役 F3 验证/失败三路径原样 |
| recover | 旧环恢复原语(已知弹层关闭 helper;落码时对齐旧环实现体,返回「是否关过已知弹层」bool) | W588 挂账项 |
| force_battle | `director._force_battle(reason)` 包装,成功→True | |
| is_stopped | `run_context.last_run_result is not None`(W209j 精确判据,现读不缓存) | |
| stop_with_evidence | 现役停机留证路径(sentinel 截图+flag+stop_running;与旧环 ping-pong 停机同款) | |
| record_defect | cw_telemetry 缺陷通道(best-effort,吞异常不炸环) | |

`snapshot_from_obs` 与 `synthesize_snapshot`(cw_sim.py:3502)的关系:sim 合成器从 GameState 合成(恒真位),`snapshot_from_obs` 从实机 obs 合成(None 语义全量)——两者共享字段映射语义但**不合并实现**(真值契约不同);对拍门1 使两者在同一映射式上受检(§7)。

---

## 6. LoopOutcome → SrOperation 轮次语义映射(W561 §三.9)

| LoopOutcomeKind | 现役对应 | 映射 |
|---|---|---|
| BATTLE | `round_success('出战(环出口)', wait=3)`(prep_director:2050) | 同 |
| BATTLE_FORCED | `round_success(f'强制出战({why})', wait=3)` / 执行失败 `round_fail`(2381-2392) | 同;reason 入 status |
| BAIL | `round_success('BailToOuter(reason)', wait=1)`(2379;bail 计数已在引擎 `_bail` 内完成) | 同 |
| PINGPONG_STOP | `round_fail(f'同因 bail ×n(reason) 停机待建档')`(2377;留证由 stop_with_evidence 端口已完成) | 同 |
| BRAKE_STOPPED | `round_fail('已停止[hook]')`(1923) | 同 |
| EVIDENCE_STOP | 留证停机 + `round_fail(status=reason)`(现役分类不 confident 无独立路径,语义=§13.2 路径停机) | 新增出口,落 fail 语义 |
| FAIL | `round_fail(status=f'策略决策异常: …')`(1932/2012 同型) | 同;reason 入 status |

落码时逐条与所引现役行号对拍(行号以落码时工作区为准,语义锁进测试)。

---

## 7. 对拍硬门协议(W598 攻击4 修法,写死)

**总则:新环开臂(默认翻 True)必须双门全绿;sim 合成器恒真位使 sim 全绿在结构上测不到边界态(W598 九恒真位表),故 sim 结果不构成开臂依据,只能构成否决依据(发现分歧即拦)。**

### 7.1 门1:实机同 obs 同策略影子对拍

- 形态:`DecisionV2Registry.director_v2_shadow_compare: bool = False`(第二字段,与开臂开关独立;影子模式**恒由旧环当权执行**,新环零落地动作——安全性优先)。
- 采样点:旧环每步 `decide_prep_action(obs, session, config)` 调用后(含破警告路径),同帧构造 Snapshot(`snapshot_from_obs`)→ 适配器 decide → 反向映射回 PrepAction → 与旧环动作**逐位对照**(类型 + 全参数)。
- 记录:逐步追加 `.debug/temp/currency_war/w606_stage2_batch3/compare_<runid>.jsonl`(步号/旧动作/新动作/分歧标记/快照指纹);分歧行同步 telemetry exec_event(`event='v2_shadow_divergence'`)。
- 硬门判据:**n≥100 决策步(≥2 实机局)且逐位分歧 = 0**。出现分歧:逐条归因 → 适配器缺陷(修码重跑)或 §7.3 已知合法差异(归档说明)。
- 边界声明(诚实范围):门1 只证「同输入同输出」(决策函数等价),不证控制流等价(新环自身 observe 节奏/生命周期行为)——后者由批②时机锁 + 门2 + 禁区纪律覆盖;此范围限制写入开臂 ADR。

### 7.2 门2:逆真值 fixture(9 恒真位反事实,离线直喂 decide)

每恒真位一个 fixture 构造(直接构造 Snapshot,不经 sim),喂 `adapter.decide`,断言保守臂(不崩 + 显式预期动作):

| # | 恒真位 | 反事实构造 | 预期 decide 行为(钉死) |
|---|---|---|---|
| 1 | confident 恒 True | `confident=False` | 引擎侧拦截(批②已锁);fixture 断言适配器被调前框架已拦(适配器断言 confident 抛错) |
| 2 | gold_trusted 恒 True | False + shop_open=False | 链 b 不走 EnsureShopOpen→LevelUp 真值臂;落 stale 试算或链 c,不误升级 |
| 3 | free_bench_slots 恒 int | None | §3.1 映射 → 收球臂(不卖件);零 SellBench 断言 |
| 4 | board 恒可读 | None | 步级无消费,decide 正常出动作(回归锁:不崩不空转) |
| 5 | spheres 恒空 | 非空(含假球位) | shop_open=True 时先 EnsureShopClosed(live 重叠误检防线继承) |
| 6 | event_overlay 恒 None | 非 None('盛会之星') | decide 不可达(引擎环顶 bail);适配器直调时断言透传 Bail |
| 7 | shop_open 恒 True | False + gold 场景 | F2:state_gold_trusted=False,gold 不进决策 state |
| 8 | hp 恒真值 | None + hp_readable=False | gated_hp 走 session 锚陈值,不 0/100 兜底 |
| 9 | box_overlay_open 恒 False | True | 恒 PickBoxCard(规则 1 首位) |

fixture 落 `sr-od-test`(测试仓),构造器复用 W599 逆真值表达性锁的构造手法。

### 7.3 已知合法差异清单(门1 归因白名单,初始三项,扩条须编排者批)

1. active_strategies 注入修复:新环 decision_target 可能走持有策略亲和分支而旧环(伪态漏拷)不走(§3.2);
2. 影子采样点在旧环 decide 后:同帧两次 decide 之间无游戏状态变化(纯函数),但旧环 decide 自身有副作用(session.prep_phase 前移、r412 latch)——影子侧**只读比较**,副作用以旧环为准,比对在副作用后取快照会造成 phase 型伪分歧 → 采样序 = 旧 decide → 记录旧动作 → 构造快照 → 影子 decide(影子 side-effect 经深拷贝 session 隔离);
3. StartBattle 强战收敛次数差(§4.2,仅引擎层,门1 不可见)。

### 7.4 开臂判据(挂账,满足才翻默认)

1. 门1:n≥100 步逐位分歧=0(分歧全归因闭合);
2. 门2:9 fixture 全绿;
3. 交付门:sr-od-test 全量绿 + ruff(改动文件)绿;
4. 翻转动作:单独 commit(default=True)+ ADR(含门1 数据指针与 §7.1 范围声明)。

---

## 8. 测试计划(第二段落码清单,sr-od-test)

| 锁文件 | 锁内容 |
|---|---|
| test_cw_w606_adapter_snapshot_map.py | §3.1/§3.2 逐字段映射;4 义务字段注入(**active_strategies 非空 → decision_state 非空**裂缝修复行为锁);free_bench_slots None→9 与 deploy_vacancy None→0 保守裁决锁;slot 双基(off-by-one)锁 |
| test_cw_w606_adapter_atomop_map.py | 16 动作映射全集锁(op_key/domain);Defer/Bail 控制流不产 op;op_key 绑定回放锁(execute 收到正确 PrepAction);查无绑定缺陷路径 |
| test_cw_w606_loop_outcome_map.py | 7 出口 → round 语义锁(§6 表) |
| test_cw_w606_adversarial_fixtures.py | 门2 九 fixture(表格式即断言) |
| test_cw_w606_shadow_compare.py | 影子比对纯函数部分:同 obs 流旧/新 decide 一致性离线锁;session 深拷贝隔离锁;jsonl 记录格式锁 |
| test_cw_w606_switch.py | 默认 False 锁;registry 注入 True → 分叉走新环(端口桩);False → 旧环逐位(现有旧环锁全绿即零漂移证) |

回归:直接受影响面 + `uv run pytest sr-od-test/` 全量(commit 前口径)。

---

## 9. 文件面与禁碰

- 动:`decision_v2/adapter.py`(新)、`decision_v2/registry.py`(+2 字段)、`prep_director.py`(分叉点+端口包装,最小侵入)、测试仓新增 6 锁。
- 预期零改:`default_strategy.py`(适配包外层;若落码发现必须改,先回报编排者裁决)。
- 禁碰:cw_identity_obs(W595)/operations/prep/shop.py(W592)/telemetry 面(W603 在飞,只调 record 接口不改文件)/cw_sim_checks(W605 在飞)。
- sim 侧:cw_sim.py 不动(对拍协议 sim 侧执行 = 用既有 synthesize_snapshot 喂适配器的离线脚本/测试,不改 sim 本体)。

## 10. 风险与盲区

- 旧环 `_observe` 返回 obs 与 Snapshot 的映射在识别边界态(heavy 沿用帧)的 None 语义可能反推不出(如 free_bench_slots 实机恒 int 现读,无 None 源)——门2 fixture 直接构造 Snapshot,不依赖 obs 源,盲区可控;
- 恢复原语实现体未逐行读(旧环 2545 行内),落码时对齐并补挂账;
- 影子对拍引入的每步开销 = 一次纯函数 decide + 一次序列化,毫秒级,无识别新调用;若实测超预算,采样率降档(每 N 步 1 采)须改协议并记录。
