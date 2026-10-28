# 废弃全局节点编号(node_ordinal)迭代设计(总纲)

> 状态:定稿;进度见 README。
> 立项出处:2026-09-23-invest-effects-calc 迭代 T-8(人身意外险)设计对抗中的用户裁定(2026-10-12):「废弃这个编号,单独立项」。

## 0. 元信息

- 迭代目标:废弃节点全局编号(`node_ordinal`,闭式公式 `(位面-1)*9 + 轮`)作为独立表示,节点位置/进度/数数语义全部改由 `(位面, 轮)` + 有效节点序列(场字段)承载。
- 状态:定稿。
- 文档清单:design.md §2 即完整设计(无第二详设划分:键表示切换是单一原子语义,消费域改法同构);视界族清扫自成 [details/horizon-cleanup.md](details/horizon-cleanup.md)(T-8 裁决点 9 指派的迁移面,独立成篇);落地 = [landing.md](landing.md);索引 = [README.md](README.md)。

## 1. 问题与动机

### 1.1 现状症状

1. **编号表示与序列并存为第二真相源(T-8 后现状;立项时的闭式公式形态见 T-8 设计底册)**。T-8 落地后 kernel 主实现已改为「按局修饰变长制」序列累加(`node_ordinal_of`,cw_game_state.py:339-358,docstring 明文与 `node_pos_of` 同表互逆),「正解公式 vs 反解累加」的脱钩在主实现已消亡;**仍存活的根** = 编号作为独立表示与 (位面,轮) 并存 + 公式拷贝散落:败局闩内联闭式(cw_screen_battle_wait.py:667 区)、journal 死 helper(journal_query.py:218-224)、历史 docstring/注,以及以编号为键的整族消费(推进水位/锚定/账本/直定/sim 簿记,§2.9 改清单)。序列再变(新修饰环境/P3 补采)时,这族拷贝与并存表示即是下一个 T-8 式 12 文件扩面点。
2. **公式/几何拷贝散落,单一源名存实亡**。全仓 `*9`/`//9`/`%9` 扫描命中 14 处(底册承 T-8 设计,裁决点 6 扩面):kernel 正反解两套(cw_game_state.py:332/3350 + cw_node_schedule.py:60)、sim 独立双实现(`_ordinal_to_node`/`_node_ordinal`,cw_sim_backend.py:1298/1346)、obs 与 operations 内联四锚三文件(cw_observation.py:2273、cw_screen_battle_wait.py:379/670、cw_screen_supply_node.py:172)、商店查链反解一处(cw_game_state.py:3267)、acquired_t 快照两处(cw_effect_inventory.py:692、cw_affix_effects.py:450)、frame 拼接一处(cw_game_state.py:3383)、telemetry 死 helper 一处(journal_query.py:218)。每引入一个改序列的环境,都要全量扫描甄别哪些拷贝会错——invest-effects-calc/T-8 为此把改动面扩到 12 文件;T-8 裁决点 7 另立方法论勘误:扫描须含具名常量族(`NODES_PER_PLANE`/`schedule_of` 夹取族,本迭代 §2.7/details 承接)。(本条 = 立项时底册,历史锚;T-8 落地后主实现面已消解,残余见症状 1 与 §2.9。)
3. **表示分叉的守卫成本**。以编号为一方的消费点(锚定水位比较、效果账本去重与数数、推进水位、类型直定倒退免疫)与以 (位面,轮) 为另一方的消费点(同式岛:结算单调门、败局闩、hp 帧龄门锚)并存,两套表示的对齐义务散落在各处注释与测试里,序列一变即需逐处重审。
4. **遥测语料跨局不可比**。journal 落盘的 ord 依存局口径(旧局 9 制/新局修饰制),跨局比序错位,只能靠纪律约定(跨语料对账按 (位面,轮) 键)兜底,无结构保证。

### 1.2 根因归层

**表示层**。「节点在序列中的位置」这一维信息,以「与序列并行/脱钩的编号投影」存在——立项时为内嵌默认环境假设的闭式公式,T-8 后主实现虽已改为同表互逆的变长累加,但编号仍是与 (位面,轮) 并行的**第二表示**,且其拷贝散落在消费层(症状 1/2)。序列成为可变量(投资环境改节点)后,任何与序列并行的位置表示都要靠全量扫描维持对齐,由此派生全部拷贝与分叉症状。编号概念本身(把序列拉直成数轴,使「接下来 N 个节点」「推进 +1」「同节点去重」成为标量算术)有真实价值;垃圾的是**投影方式**(独立表示)而非投影需求——与其维护一套永远追着序列走的间接层,不如直接以 (位面,轮) + 序列表为唯一表示、数数语义走显式序列运算(本设计 §2.0 裁决)。

### 1.3 解决到哪 / 明确不解决

**解决**:全局编号作为独立表示退役;其全部消费语义(效果账本的登记时点/到期/去重与「接下来 N 个节点」数数、推进水位与观察锚定、类型直定与倒退免疫、sim 节点窗定位、遥测落盘与查询)改由 (位面,轮) + 有效节点序列表达;T-8 裁决点 9 指派的视界族/9 制几何层清扫(函数退役 + 策略消费方自算迁移)在本迭代承接(§2.7 + [details/horizon-cleanup.md](details/horizon-cleanup.md));全仓公式拷贝与具名常量几何层清零,表示唯一。

**明确不解决**:

- 策略侧选卡估值/打分不变(StanceRow/打分器另一范围)——唯 T-8 裁决点 9 指派的视界长度真值源迁移除外(其行为变化 = 真值修正,见 details §8);
- (位面,轮) 的读数链本身(OCR 两位数/值域守卫)不在本迭代(invest-effects-calc/T-8 已修);
- 节点序列场字段(`node_seq_by_plane`)机制为既定前提沿用(T-8 落地),本迭代不重设计;
- 位面序列真值采集(含 P3 补采)另案;
- 历史遥测语料的旧口径 ord 不迁移(按 run 隔离,对账用 (位面,轮) 键——T-8 裁决点 4 已裁定,随编号废弃自然终局)。

### 1.4 前置与关联

- 前置:invest-effects-calc/T-8(人身意外险)——**已落地(2026-10-12),前置闸满足**;场字段与序列修饰层在役(实码核验:`node_seq_by_plane` 场字段/`resolve_plane_node_seqs`/`node_round_cap`/`_validate_env_node_seq` 全部在册)。落地态与本设计基线的三处对齐申报见 §2.0。
- 关联:invest-effects-calc/T-8 裁决点 5(kernel/sim 双份反解合并)——T-8 落地态已把双份实现收成薄委托(sim 壳直调 kernel 带参函数),本迭代删壳即消解;裁决点 6 的坐标消费面扩面修复已随 T-8 落地,本迭代表示切换不回退之。
- 关联(T-8 定稿新增):**裁决点 7 前半**——killed-hp 兜底门删除(HP 对比兜底块 + `_st.last_outcome_t` 随删,胜负判定必须在结算画面识别;勘误后口径:`node_t_of` 不随删、保留至本迭代 3.5 退役)属 T-8 落地面,**门本体本迭代零接触**(§2.7);**裁决点 9**——视界族/9 制几何层的函数退役与策略侧自算迁移**指派本迭代**(§2.7 + details/horizon-cleanup.md 承接)。
- 关联申报:同迭代设计件 T-19(劳伍派遣合同,设计成稿未落地)内引用 `node_pos_of`/`node_ordinal_of` 的「T-8 落地随迁」行,随本迭代整体失效——其触发器坐标改按 (位面,轮) 键表达,由 T-19 自身落地批消化(登记义务,不进本迭代文件面)。

## 2. 方案

> **行号基准**:本节 file:line = T-8 落地后工作树(2026-10-12);后续在飞批使行号漂移时按符号名定位,锚语义不变。

### 2.0 表示裁决与基线声明

**裁决(§1.2 归层的落地形态):节点身份唯一表示 = `(位面, 轮)` 序位元组;全局编号整族退役。**

- 序位 `NodePos = tuple[int, int]`(1 基),单一源住 `cw_node_schedule`(序列真值同域)。
- **标识对外口径(用户裁定 2026-10-12:统一使用「位面-轮」式标识)**:节点标识 = `2-1` 形态的「位面-轮」标签,不再有独立于它的全局编号;元组 `(2, 1)` 只是标签的容器内表示,journal 数值列(plane/round_num)是列不是标签、维持不变。本迭代新铸的字符串口径(reason 串/留证载荷值/frame 串)统一按「位面-轮」形态落字(§2.2/§2.4)。
- **字典序 = 序列全序**:位面优先、位面内轮次次序的元组字典序,与「有效节点序列按位面拼接展平」的前缀和序逐值一致(位面主序拼接下前缀和严格单调,数学恒等,不依赖任何具体序列值)。推论:**全部比较/去重/水位语义(锚定四分支、推进去重、倒退免疫、单调门、败局闩、登记当节点守卫)改元组直接比较,零序列依赖、零参数穿线**——这正是编号表示的守卫成本(每个持序值的生产/消费点都必须正确穿 `seqs`,T-8 裁决点 6 的 14 处扫描实证)被整体拆除的机制基础。
- **数数语义显式化**:「推进 +1」= `sequence_next(pos, seqs)`(§2.1,全仓唯一后继实现,位面切换在此发生);「接下来 N 个节点」= 效果账本既有自然数倒计时(`remaining_nodes` 递减,本就是相对计数,无需坐标算术,§2.4);规划量(剩余节点数/剩余 boss 数)= 策略侧既有 `schedule_of` 求和族,不动(§2.7)。
- **T-8 终态基线(已落地,2026-10-12 树核验)**:`node_seq_by_plane` 场字段在役(写点唯一 = `gain_invest_env` 尾段 cw_gain_chain.py:489-495;独立 gs_schema 域版本 1,cw_game_state.py:248)、`node_sequence_of(plane, seqs=None)`/`node_round_cap(plane, seqs=None)`/`resolve_plane_node_seqs(env)`/`ENV_NODE_SUPPLY_BEFORE_BOSS` 在役、`node_pos_of(ordinal, seqs=None)` 与 kernel `node_ordinal_of(plane, round, seqs=None)` 带环境参在役;**killed-hp 兜底门已删**(裁决点 7 前半:`last_outcome_t` 随删,`node_t_of` **保留**——T-8 落地批未执行其改清单的删除项,现役唯一消费 = strategy_economy.py:57/:260,退役归本迭代 3.5)。本迭代 **删除** T-8 的正反解换算面(`node_pos_of`、`node_ordinal_of`、sim 薄委托壳),**保留** 序列直查面(`node_sequence_of`/`node_round_cap`/`resolve_plane_node_seqs`——kind 查询与读数 cap 是序列的合法直查消费,不是编号投影)。T-8 的「正反解互逆测试」随反解删除而退役(无编号可互逆)。
- **落地态对齐申报(三处)**:①`node_t_of` 存活(T-8 改清单「死函数删除」未执行——实现批留函,现役消费面 = strategy_economy 估值通道;本迭代 3.5 退役时一并迁移该消费,见 details §6);②sim 双反解已是**薄委托**(`_ordinal_to_node` 内部直调 `node_pos_of(ordinal, seqs)`、`_node_ordinal` 直调 `node_ordinal_of(…, seqs)`——裁决点 5 的「双份+同参」落地为壳形态),3.2 删壳即可;③`node_seq_by_plane` 为独立 gs_schema 域(版本 1),不占 derivation 域——本迭代 bump 仍只动 derivation(4→5)。
- **P3 不变**:P3 无观测 → 序列表无 P3 → 后继在位面无序列表(含 P2 末)时返回 None(§2.1),局终语义不变;`P3UnobservedError` 仍拦一切对未知位面的序列直查(`node_sequence_of` 直查路径;`sequence_next` 对未知位面按 None 返回,见 §2.1 契约)。

### 2.1 序列模块键原语(kernel/cw_node_schedule.py)

```python
#: 节点序位(位面, 轮次),二元素整数元组,1 基。节点身份唯一表示:
#: 字典序 = 有效节点序列按位面拼接展平的全序(位面主序下前缀和单调恒等)。
NodePos: TypeAlias = tuple[int, int]

def sequence_next(pos: NodePos,
                  seqs: dict[int, tuple[str, ...]] | None = None,
                  ) -> NodePos | None:
```

- `sequence_next` = 「推进 +1」的唯一实现,四态契约:**①** 位面内 `r < len(seq)` → `(p, r+1)`;**②** 位面末 → 下一位面首 `(p+1, 1)`;**③** 下一位面无序列表,**或 pos 自身位面不在序列表**(live 真局进 P3 的锚定形态,read_phase_round 位面 3 放行 + 锚定无位面白名单)→ **None = 超出建模域,调用方按局终处理**(对齐现役 `eff > total` 优雅局终臂的 '' 语义,cw_game_state.py:3437-3439);**④** `r > len(seq)`(modeled 位面内的损坏坐标)→ `ValueError` 响亮,禁静默跨位面。`seqs` 缺省 = 默认表(与 `node_sequence_of` 同参约定)。
- **退役**:`node_pos_of`(反解;消费方 = §2.2-§2.6 各节所列点——next_screen/商店查链/直定/frame/sim 薄委托,随各节退役后零残留)。T-8 为其加的 `seqs` 参数随删除消失。
- 保留不动:`PLANE_NODE_TABLES`/`P1_NODE_SEQUENCE`/`P2_NODE_SEQUENCE`/`NODE_KINDS`/`P3UnobservedError`/`validate_sequences`/`ENV_NODE_SUPPLY_BEFORE_BOSS`/`resolve_plane_node_seqs`/`node_sequence_of`/`node_round_cap`(T-8 面)。模块头「现役口径」段随键原语改写(真值表 + 键原语,不再出现「节点线性序」表述)。

### 2.2 kernel 节点域(字段与推进原语;cw_game_state.py)

**字段(两态生命周期与写点准入全部保留,只换值载体)**:

- `node_ord: Field[int]` → **`node_pos: Field[tuple[int, int]]`**(:2630;索引定义注释同步改写:值 = NodePos,两态语义 = 锚定态 observation `observe_node_anchor` 直写 / 推进态 logic `report_node_advance` 经原语写入,生效读口 = `effective_node_pos`)。
- `node_hist_ord: int | None` → **`node_hist_pos: tuple[int, int] | None`**(:2667;run 内单调水位 + 去重键 `(run_id, 生效序位)` 的 run 内载体,语义不变)。
- `DEFAULT_GS_SCHEMA['derivation']` 4 → **5**(:264,域版本 bump 先例 = 版本 4 两态生命周期切换批);行级 `GAME_STATE_SCHEMA_VERSION` 不动(恢复面无旧档迁移函数需求,旧档 `node_ord` 键被恢复面忽略,§2.8);`node_seq_by_plane` 是 T-8 落地的独立域(版本 1,:248),不在本 bump 面。
- `cw_projection_audit.PROJECTION_AUDIT['node_ord']` 行改键 `'node_pos'`,basis 改两态键表述(:408;完备性测试双向,旧键不删即 `audit_stale_keys` 红)。

**原语(签名换载体,处置规则逐分支保持)**:

- `effective_node_ord` → **`effective_node_pos(gs) -> NodePos | None`**(:3360):= max(node_pos 现值, node_hist_pos),**max 换元组字典序**(None 安全不变)。
- `advance_node_effective(gs, candidate: NodePos, *, actor, sig, source)`(:3515):去重守卫 `candidate <= effective` **元组比较**(同序幂等);写 `node_pos`(source 由调用方定,logic/observation 两路不变);`node_hist_pos` 单调水位(元组比较);效果推进尾段同临界区不变。
- `report_node_advance(gs, *, trigger, sig=None)`(:3549):观察态门双条件不变(`node_pos.value is not None ∧ source == 'observation'`);candidate 从 `effective + 1` 改 **`sequence_next(effective, gs.node_seq_by_plane.value)`**;返回出口:
  - **`sequence_next` 非 None**:照旧落账,`applied=True, reason=f'node_pos→{p}-{r}'`(原 `node_ord→{n}` 串退役),`world_decl` 照旧推导(§2.2 末);
  - **`sequence_next` = None(P2 末终局确认,或 live P3 锚定后的上报)**:**局终声明事件式**——零写入(无后继序位可写)、零效果 tick(无节点进入;现行在此多 tick 一次越界序 `total+1`,属越界幽灵节点的一次虚假发放递减,见 §2.12 披露 1),返回 `applied=True, reason='match_end'` + `WorldDecl(next_screen='', trigger='node_advance')`。**applied 语义扩展申报**:在库契约 = 「applied = 实际推进落账位」(kernel docstring,`report_node_advance` 内)+「applied=True 出口必构造声明;applied=False = None」(flow/action_ops.md §1)——终局出口把「落账位」语义单点扩展为「终结动作落地事实」(落地但无后继可写),kernel docstring 随 3.2 修订,action_ops.md §1 义务句补终局出口语义(正本更新清单);现消费面仅日志(cw_op_settle_confirm.py:148)与声明构造,无判效断言消费。
- `observe_node_anchor(gs, pos: NodePos, *, trigger_screen, actor, sig=None)`(:3639;现签名第二参为 `ordinal: int`,seqs 处理在调用方正解侧——本迭代换 pos 载体后调用方 seqs 义务随之消失):四分支前置**位面在表守卫**(新增,显式化 T-8 前由 `node_ordinal_of` 抛错承担的隐式白名单):`pos[0]` ∉ 序列表键集(场字段键集,缺省默认表)→ 不写任何水位 + obs_event arbitrate 留证(读数 = OCR 位面误读形态,如 1↔3),返回 `out_of_domain_dropped`——防越域键写入毒化水位并伪造终局(现役 prep 侧 suppress 零写入/supply 侧响亮抛错,语义等价保留)。守卫后四分支处置逐字保留,比较全换元组——`v is None` → first_anchor;`pos > v` → advance 补推;`pos == v` → reanchor;`pos < v` → stale_dropped 倒退免疫留证。跨位面形态 `(1,10) < (2,1)` 由字典序自然严格(T-8 修饰局下同式成立,不需任何序列查询)。
- **删除**:`node_ordinal_of`(:339,T-8 落地态带 seqs 参的正解)、`_node_key_for_ord`(:3405 反解)、`_obs_node_ordinal` 改 **`_obs_node_pos(gs)`**(镜像已是 NodeKey,直接返回 `(cur.plane, cur.round_num)`,:3375)。

**next_screen 推导(`_node_advance_next_screen`,:3488)**:输入即键——`pos = effective_node_pos(gs)`;**防御分支与现行同位优雅**:`pos is None → ''`(现行分支保留);`pos[0]` 无序列表 → `''`(对齐现行 `eff > total` 优雅局终;**禁直查 `node_sequence_of` 抛错**——先判位面在表性再取长);`pos[1] > len(seq)` → `''`(modeled 位面内损坏坐标防御);`pos[0] > 1 ∧ pos[1] == 1` → 位面过渡;否则 `_NODE_KIND_NEXT_SCREENS[seq[pos[1]-1]]`。`total` 求和与 `node_pos_of` 反解两段退役。

### 2.3 类型派生与商店查链(kernel/cw_game_state.py)

- **商店查链**(observe_screen_context 商店分支,:3318):`_shop_panel_type_target` 改返回 `NodePos | None`(max 换元组字典序,:3400);链查询目标解码——T-8 落地态已把内联公式改为 `node_pos_of(_shop_target, seqs)(:3318)`,本迭代目标态 = 目标即键,**连 `node_pos_of` 解码也退役**,改 `chain_node_type(self, target[0], target[1])` 直查。
- **直定写入**(`_write_derived_node_type`,:3686):形参 `target_ord: int` → **`target_pos: NodePos`**;`NodeKey` 构造改直建 `NodeKey(plane=target_pos[0], round_num=target_pos[1], kind=kind)`(`_node_key_for_ord` 删除的承接点);**倒退免疫** `node_ordinal_of(cur…, seqs) > target_ord`(:3715,T-8 落地态带 seqs)→ `(cur.plane, cur.round_num) > target_pos` 元组比较,语义逐值等价。BOSS 简报直定宿主(kernel/cw_screen_report/boss_briefing.py:50-55)目标从 `gs.node_hist_ord` 改 `gs.node_hist_pos`,直传元组。
- 直定冲突/倒退 obs_event 载荷里的 `target_ord`/`node_ord` 键改 `target_pos`/`node_pos`(值 = `f'{p}-{r}'` 串或 [p, r],留证面口径随载体)。

### 2.4 效果账本(kernel/cw_effect_inventory.py + cw_affix_effects.py)

账本保持「零 import 包内模块」纪律(类型注解就地写 `tuple[int, int]`,注释指 `cw_node_schedule.NodePos`):

- `ActiveEffect.acquired_t: int | None` → **`acquired_key: tuple[int, int] | None`**(:189,T-8 已改「修饰制坐标系」措辞,本迭代再改键表示)。
- `ActiveEffectInventory._last_tick_node` → **`_last_tick_key`**(:225,去重键 = 序位相等)。
- `advance_node(node_ordinal)` → **`advance_node(node_key: tuple[int, int] | None)`**(:338):同节点去重 `node_key == self._last_tick_key`(:362-364);「登记当节点不推进」守卫 `e.acquired_key >= node_key` **元组比较**(:369-371——语义与现行 `>=` 序数比较逐值等价,字典序=全序);`remaining_nodes` 自然数倒计时**零改动**(「接下来 N 个节点」自 T-8 修饰制起差值即真实节点数,倒计时本就不依赖坐标算术)。
- 快照两处内联退役:`_portal_acquired_t` → **`_portal_acquired_key`** 返回 `(nd.plane, nd.round_num)`(:688 起;T-8 落地态内部已改调 `node_ordinal_of(…, seqs)`,本迭代连正解调用一起退役);`register_affixes_from_names` 同款(:454-456)同改;`_register`/`register_strategy`/`register_affix`/`register_portal` 的 `acquired_t` 形参名随载体(:253/:264/:268/:283);`tick_node` 兼容口形参随改(:378)。**kernel 消费方随批**:cw_gain_chain.py:43(import)/:623(调用)/:581 区(注释)——portal 获得链直连消费点,与生产方同批评审(atomic 面闭合);同文件 `_node_frame`(:569-573,链内 frame 串 `p{plane}-r{round}`)一并统一为「位面-轮」形态 f'{p}-{r}'(与 frame 口径同批,消除同 run 双形态并立——披露 2)。kernel 侧调用方 `_tick_effect_boundary_impl`(:3435)传 `effective_node_pos(gs)`;frame 串改 `f'{pos[0]}-{pos[1]}'`(「位面-轮」统一标识,用户裁定 2026-10-12;frame 只进 evidence/余额账,随键直拼)。

### 2.5 观察锚定写端与画面 op(operations/cw_screen/)

- `CwScreenPrep` 备战锚定(cw_screen_prep.py:300-303):`node_ordinal_of(int(_st.plane), int(_st.round_num), seqs=…)`(T-8 落地态)→ `(int(_st.plane), int(_st.round_num))` 直传;import 面 `node_ordinal_of` 移除。
- `CwScreenSupplyNode._read_node_bar`(cw_screen_supply_node.py:149-186):返回值 T-8 落地态 = `node_ordinal_of(plane, rnd, seqs)(:183)`,本迭代改 **`NodePos` 元组直返**(正解调用随之退役);OCR 正则与值域守卫维持 T-8 终态(`node_round_cap`,不在本迭代);调用点锚定(:227)传元组。
- 位面过渡 opening 判定(cw_screen_plane_transition.py:64、kernel/cw_screen_report/plane_transition.py:59):`gs.node_hist_ord is None` → `gs.node_hist_pos is None`(机械改名)。
- 注释面:cw_op_settle_confirm.py:11/:133、cw_encounter_selection.py:238 的 `node_ord` 表述随载体改 `node_pos`(行为零改动)。

### 2.6 sim 节点窗与局终声明消费(sim/cw_sim_backend.py)

- 簿记换键:`_entered_ord: int = 0` → **`_entered_pos: NodePos | None = None`**(守卫 `eff is None or (_entered_pos is not None and eff <= _entered_pos)`,元组比较);`_window_begun_ord` → **`_window_begun_pos`**(:767/:770,窗口幂等守卫键换序位,防双发语义不变);`_pending_reconcile` 元素首槽随键(:1048/:1085)。
- **退役**:`_ordinal_to_node`(:1303)与 `_node_ordinal`(:1347)——T-8 落地态已是**薄委托**(内部直调 kernel `node_pos_of`/`node_ordinal_of` 带 seqs),本迭代删壳即消解(裁决点 5 终局)。
- `_enter_node_window(pos: NodePos)`(:1319):`kind = node_sequence_of(pos[0], gs.node_seq_by_plane.value)[pos[1]-1]`;镜像写 `NodeKey(plane=pos[0], round_num=pos[1], kind=kind)`;锚定 `observe_node_anchor(self.gs, pos, ...)`;位面过渡臂 `pos[0] > 1 ∧ pos[1] == 1` 不变。
- `_on_node_advance`(:1092):去重守卫换键(:1095);`eff > sum(len(...))` 局终分支**退役**(键表示下不存在越界序位,见 §2.2 终局事件式);正常路径 = XP 入账(prev.kind)→ `_entered_pos = eff` → `_enter_node_window(eff)`。
- **`advance()` 增局终分支**(:990 分派臂):`decl.trigger == 'node_advance' ∧ decl.next_screen == ''` → `_on_node_advance_terminal()`——XP 入账(prev.kind,与现行局终前入账同序)+ `DISCLOSURE_P3_UNOBSERVED` 披露(键值 `enter_p3_game_over_u19` 保留)+ `_game_over()`;此后 `_reconcile_next_screen` 走 `done=True ∧ decl=''` 合格臂,漂移面零新增。kernel 声明权威、sim 对账的既有分工不变:非终局推进仍走 `_on_node_advance` 状态重导出。
- `_node_window_target_base`/`_present_offer_or_node_screen`/`_present_node_screen`/offer 门(:1436-1440/:1450-1452/:1477):全部已按 `(plane, r)` 直查,仅随 `node_sequence_of` 的 T-8 `seqs` 参在位,零结构改动。

### 2.7 同式岛收口与视界族清扫(operations + obs + kernel 规划面)

- **结算单调门**(cw_screen_battle_wait.py 结算读半,_scr 单调臂):T-8 已改元组比较 = 本迭代目标形态,**零改动申报**(依据:T-8 §2.5 绑定面;字典序即目标全序)。
- **败局闩次级证据**(cw_screen_battle_wait.py:651-675;T-8 不辖此门):`_t = (nd.plane-1)*9 + nd.round_num`(:665 区)与 `SETTLE_DEFEAT_LATCH_MIN_T = 14`(:242)→ `_pos = (nd.plane, nd.round_num)` 与 **`SETTLE_DEFEAT_LATCH_MIN_POS: ClassVar[tuple[int, int]] = (2, 5)`**;门 `_pos >= SETTLE_DEFEAT_LATCH_MIN_POS`。**逐值等价证明**:`(p-1)*9+r >= 14 ⟺ (p,r) >= (2,5)`(字典序=序数序,含修饰局 (1,10)=10<14 不置闩形态)。
- **killed-hp 兜底门 / `last_outcome_t`:零接触申报**——T-8 落地批已删(裁决点 7 前半;实码核验:结算 killed 判定仅剩 progress 符号/killed 文本两路,battle_wait :463-473),不在本迭代文件面;`node_t_of` **T-8 保留未删**(§2.0 对齐申报①),其退役归 3.5。3.3 以「门与 `last_outcome_t` 符号不存在」断言作核对。
- **视界族/9 制几何层清扫(T-8 裁决点 9 指派本迭代)**:`node_t_of` 的策略侧消费(strategy_economy.py:57/:260 boss 通道,T-8 落地后在役)、`schedule_of`/`r_remaining`/`r_global` 族与 `NODES_PER_PLANE`/`TOTAL_NODES` 具名常量闭式的函数退役与消费方场字段自算迁移,方案全量在 [details/horizon-cleanup.md](details/horizon-cleanup.md);总纲级要点 = 退役 11 符号(几何层整体)、策略门面(horizon.py)签名不变重基、kernel 判据点就地 ≤3 行迁移、禁新公共视界口(裁决点 9 字面)。
- **hp 帧龄门锚死局部**(`_node_t`,obs/cw_observation.py):**T-8 落地已顺带删除**(当前树 grep 零命中——漏斗 round_caps 改造时清理),本迭代零接触申报。

### 2.8 遥测·快照·载体

- **快照**(`full_state_snapshot`,:2794):`values` 自动携带 `node_pos`(Field 迭代;`_json_safe` 元组→list);顶层 `'node_hist_ord'` 键 → `'node_hist_pos'`(:2834);effects 行 `'acquired_t'` 键 → `'acquired_key'`(值 [p, r],effects 序列化区)。
- **恢复**(`restore_state_snapshot`,:3946):复杂值重建表增 `node_pos` 条目(list → `tuple[int, int]`,先例 = node/deployed 按字段名重建;T-8 已有 `node_seq_by_plane` 重建先例 :4048);旧档 `node_ord` 键与旧 `node_hist_ord` 顶层键被忽略(历史语料不迁移裁定,恢复 = 离线判读面,零迁移函数)。
- **锚行槽退役**(kernel/cw_anchor.py):`AnchorEvent.node_seq`(:110)与 `to_row` `'node_seq'` 键(:127)、`emit_anchor` 的 `node_seq` 形参(:301)与幂等键槽(:313)整体删除——锚行时点键已含 `plane/round`,`node_seq` 是编号投影的遥测镜像;`emit_anchor` 现无生产调用方(全仓 grep 零命中,登记表在册即权威),零行为面。
- **死 helper 删除**(telemetry/journal_query.py:218-224 `node_ordinal_of(row)`):T-8 已核全仓零调用方;`node_key_of`/`round_state_snapshots` 均 (位面,轮) 键,查询面合规不动。
- **defects 维度**(telemetry/defects.py `'node_seq'`):缺陷维度词表成员,与编号表示无关,**零改动申报**(此处 node_seq 指「节点序列」感知维度,非序位快照)。

### 2.9 影响面与零改动申报

**改(按行分组;同组符号/注释改动一次提交;22 行表共 31 文件)**:

| 文件 | 面 | 节 |
|---|---|---|
| kernel/cw_node_schedule.py | NodePos + `sequence_next`;删 `node_pos_of`;模块头口径 | §2.1 |
| kernel/cw_game_state.py | 字段两件套/schema bump/原语换键/商店查链/直定/frame/next_screen/终局事件式/快照恢复/模块头 | §2.2/2.3/2.8 |
| kernel/cw_projection_audit.py | 审计表键 | §2.2 |
| kernel/cw_effect_inventory.py | acquired_key/_last_tick_key/advance_node/frame 消费/register 族形参 | §2.4 |
| kernel/cw_affix_effects.py | 快照内联退役 | §2.4 |
| kernel/cw_gain_chain.py | `_portal_acquired_key` import/调用/注释 | §2.4 |
| kernel/cw_screen_report/boss_briefing.py | hist 直定目标 | §2.3 |
| kernel/cw_screen_report/plane_transition.py | opening 判定改名 | §2.5 |
| sim/cw_sim_backend.py | 簿记键/双反解删除/进窗/局终分支 | §2.6 |
| operations/cw_screen/cw_screen_prep.py | 锚定传元组 | §2.5 |
| operations/cw_screen/cw_screen_supply_node.py | 节点条返回元组 | §2.5 |
| operations/cw_screen/cw_screen_plane_transition.py | opening 判定改名 | §2.5 |
| operations/cw_screen/cw_screen_battle_wait.py | 败局闩键门 | §2.7 |
| operations/cw_op/cw_op_settle_confirm.py + kernel/cw_encounter_selection.py | 注释口径 | §2.5 |
| kernel/cw_anchor.py + telemetry/journal_query.py + kernel/cw_reconcile.py | 锚行槽/死 helper/死形参(`reconcile_hp` 的 `node_t` 兼容形参 :456,守卫删除后零消费) | §2.8 |
| kernel/cw_plane_table.py | 几何层 11 符号退役 + nodes_of_plane 回退再基 + 模块头 | §2.7/details §2 |
| strategies/impl/mandate_v1/statefn/horizon.py | 门面场字段重基(签名不变) | §2.7/details §3 |
| strategies/impl/mandate_v1/proof.py + statefn/budget.py + criteria/levelup.py | r_remaining import 改道门面 | §2.7/details §4 |
| strategies/impl/mandate_v1/strategy_economy.py | boss 通道 kind 化 + 退役 import 清理 + docstring | §2.7/details §6 |
| strategies/impl/mandate_v1/audit/derived.py + audit/calibration.py | 真值源注 + 标定域再基 | §2.7/details §7 |
| strategies/impl/mandate_v1/criteria/refresh.py | docstring 坐标系句改指策略门面(注释级) | §2.7/details §5 |
| kernel/cw_economy.py + cw_intention.py + cw_comps.py + cw_registry.py | 判据点就地迁移/闭式修正/注释 | §2.7/details §5 |

**零改动(带依据)**:

- `node_seq_by_plane` 场字段四件套与 `resolve_plane_node_seqs`/`ENV_NODE_SUPPLY_BEFORE_BOSS`(T-8 面,既定前提);
- 读数链(`read_phase_round`/`parse_settlement_round`/`_NODE_BAR_RE` 正则与 `node_round_cap` 值域):T-8 终态,序位直读无编号;
- 结算单调门、killed-hp 兜底门(后者 T-8 已删,本迭代零接触——§2.7);
- 观察漏斗对 `gs.node` 镜像的写端(镜像本就是 NodeKey)与 `top_bar_raw` 观察层;
- 外循环路由、画面 op 分发、补给/遭遇/商店行为链(键化不触画面语义);
- 策略层选卡估值/打分(StanceRow/打分器)与 `shop.py`/`statefn/odds.py`(门面调用/标定表,签名不变零改)、`nodes_of_plane` 消费族(`cw_discipline_rules`/`cw_line_switch`/`cw_intention:365-368` 位面内对照量——唯 :366 None 回退分支消费 `NODES_PER_PLANE`,随 details §5 迁移;其余零改动);
- 默认环境与修饰环境全部行为(字典序=全序恒等 + 逐值等价证明见各节;行为差申报面 = §2.12 披露 1/2/3);
- `SETTLE_DEFEAT_LATCH` 主证据链(进度符号)、`defects` 维度词表、`node_key_of`/`round_state_snapshots` 查询面。

### 2.10 关键取舍

1. **键直表示 vs 序下标制**(保留单一标量,定义为「有效序列展平下标」,全量经序模块换算):弃。下标制与闭式公式同构——每个持序值的生产/消费点都必须正确穿 `seqs`,漏穿即跨系分叉;而比较/去重/水位语义本可零序列依赖(字典序恒等)。T-8 裁决点 6 的 14 处扫描已实证该耦合的守卫成本;编号退役后仍保留下标 = 把症状换了个名字留下。
2. **兼容双表示并存渐迁**(node_ord 与 node_pos 并存):弃。双表示并存期 = 分叉守卫成本最高期,且违背「表示唯一」目标;R7 触发模型换代先例 = 原子切换、一次提交完成、无并存窗口(node-derivation.md §3.3-6)。
3. **终局仍写虚拟越界键**(如 `(2, len+1)`)保持「推进必写值」不变量:弃。越界键 = 序列外幽灵坐标,kind 查询/序列长度对它无定义,全链需特判「虚拟终局键」= 新表示内嵌特例;事件式终局(`sequence_next` = None → 声明 `''`)语义干净,且 sim 消费面本就以 `next_screen=''` 为局终预测载体(对账 :1067-1078)。
4. **NodePos 用 dataclass 而非 tuple**:弃。字典序比较是本设计的机制基础(§2.0),tuple 原生支持且 JSON 直转;dataclass 需自定义全序与序列化,零收益。
5. **规划量(`node_t_of`/`r_global` 族)一并键化**:数量/距离语义(「还剩多少节点」)不是节点身份,不参与键化——但 T-8 裁决点 9(晚于本迭代立项)把该族的**函数退役与策略自算迁移指派给本迭代**,故清扫面入 §2.7/details 承接;身份表示(键)与数量语义(计数)的分界维持。
6. **AnchorEvent.node_seq 槽保留为休眠**:弃。休眠槽 = 未来编号生产者的合法入口邀请,与「表示唯一」相悖;删除成本为零(无调用方,§2.8)。

### 2.11 测试面设想(钉住设计约定,细则归实现批 landing)

1. **后继纯函数测试**:`sequence_next` 默认表——(1,1)→(1,2)…(1,9)→(2,1)、(2,7)→None;修饰表(T-8 表)——(1,9)→(1,10)→(2,1)、(2,8)→None;pos 位面不在序列表((3,1))→None;(1,11) 类越界 → ValueError。
2. **推进原语测试**:正常推进写 `node_pos`(logic)+ hist 水位 + 效果尾段同临界区;去重(同序位幂等);观察态门(双条件,门挡留证零推进);跨位面推进 (1,9)→(2,1)(默认)与 (1,10)→(2,1)(修饰)。
3. **终局测试**:P2 末 boss 结算确认 → `applied=True, reason='match_end'`、`node_pos`/`node_hist_pos`/效果账本零写入零 tick、decl `next_screen=''`;sim 收 decl'' → XP 入账 + `p3_unobserved` 披露 + game_over、对账合格臂零漂移。
4. **锚定四分支测试**:first_anchor/advance/reanchor/stale_dropped 键版逐分支;跨位面字典序严格性((1,10) < (2,1),修饰表);**位面在表守卫测试**——(3,x) 误读形态不写水位、留证丢弃、返回 `out_of_domain_dropped`(与现役 prep suppress/supply 抛错语义等价对照)。
5. **类型直定测试**:目标键直建 NodeKey;倒退免疫(镜像键 > 目标键丢弃留证);商店查链键 = 目标序位本身(无反解)。
6. **账本测试**:登记当节点不推进(`acquired_key >= node_key`,含镜像领先形态);同序位去重;倒计时行为与现役逐值同。
7. **败局闩测试**:键门与旧 t 门逐值对拍((1,10)/(2,1)/(2,4)/(2,5) 边界,含修饰局形态)。
8. **快照/恢复测试**(三句分明,对齐恢复面 values-only 语义):①`node_pos` 快照→恢复逐值(list→tuple 重建表条目在位);②`node_hist_pos`/`acquired_key` 钉住**快照行形状**(顶层键 `node_hist_pos`、effects 行 `acquired_key` 值形 [p, r])+ 恢复面忽略申报(零迁移,恢复不消费此二者);③旧档 `node_ord`/`node_hist_ord` 键恢复零炸。
9. **默认局回归**:默认环境 sim 全链一次,窗口幂等/收入/局终轮次与现役基线逐值同(修饰局回归 = T-8 既有测试面)。
10. **视界族测试**(details §3/§6/§8):门面 `r_remaining` 场字段求和(默认表 = 现役 schedule_of 逐值;修饰表 = 修夹取后真值;None 回退);strategy_economy boss 计数对拍 = **变化申报面**(默认局 P1 段 3→2、P2 起 2→1,P3 虚拟末槽移除——details §8.3;非逐值不变);hp_safe 阈 nodes_left 对拍 = 变化申报面(details §8.4,默认局 P2 r1 18→7);`total_remaining_nodes` 修正后与门面同值。

### 2.12 披露申报

1. **终局虚假 tick 移除 + 终局后重复上报语义(行为差)**:现行终局确认会把水位推到越界序 `total+1` 并对效果账本多 tick 一次(advance_node_effective 内联于推进,越界序位无节点语义);键化后终局零写入零 tick。影响 = 尾局存活效果的 `remaining_nodes` 少递减一次、到期移除日志少一行——对局已终,账本随 run 销毁,零世界语义;sim 对账面不变(现役 sim 局终臂同在 tick 之后)。**幂等性形态变化**:现役终局推进写 logic 态,同屏重试上报被观察态门挡;键化终局零写入,`node_pos` 保持锚定态 → 终局后重试上报恒过门并重复发射 `match_end`(applied=True;零状态破坏,sim `advance()` done 早退吸收)——判读口径 = 同 run 多条 match_end 视为同一终局事件(键 = run_id),落地批不设终局闩(新增状态 vs 重复行噪声,取后者)。
2. **reason 串与留证载荷口径**:`node_ord→N` 串、`target_ord`/`node_ord` 留证键改 `node_pos→2-1`(「位面-轮」统一标识,用户裁定 2026-10-12)、`target_pos`/`node_pos`;效果 frame 串统一为 `1-3` 形态,生产点两处随批同改——`_tick_effect_boundary_impl`(cw_game_state.py:3435 起,frame 拼接在其体 内)与 cw_gain_chain `_node_frame`(:569-573,burst 桥/板面重写桥 evidence 链)——改造后同 run 无 `p1-r3` 旧形态残留;判读脚本若硬编码旧串需随批知晓(在册判读面 grep 核对归实现批);journal 行形状变化按 run 隔离,跨语料对账按 (位面,轮) 键(§1.3 既定)。
3. **视界族行为变化(策略规划输入真值修正,T-8 裁决点 9 认定的缺陷修复面)**:修饰局视界「少 1」夹取偏差消除、P3 虚拟 9 轮移除(视界封顶 modeled planes,与 bot 进 P3 即结束链的生命周期一致)、boss 计数几何假设改 field 实 kind(**默认局亦变**:P1 段 3→2、P2 起 2→1)、hp_safe 阈 nodes_left 封顶变化(默认局 P2 r1 18→7)、标定域 27→18 收紧——变化项与默认局不变面逐项申报 = details/horizon-cleanup.md §8。
4. **`emit_anchor` 形参收敛**:锚行 `node_seq` 槽退役后,未来接线方按七字段封装的文档口径(node-derivation.md §3.5 历史节/正本批更新)同步;登记表在册锚 `node_enter` 的宿主描述不变。
5. **T-8 互逆测试退役与 killed 门零接触**:T-8 落地批交付的「正反解互逆测试」随 `node_pos_of` 删除退役(无编号可互逆);killed-hp 兜底门/killed 邻接门行为面归 T-8(裁决点 7 前半),本迭代无涉——其「场字段↔live 台账对照」披露通道(序列真值证伪面)与键化正交,保留。
6. **遥测身份字样豁免**:披露键值 `enter_p3_game_over_u19`(DISCLOSURE_P3_UNOBSERVED)含历史越界序编号字样,作为遥测身份保留(改键值 = journal 对账断流;语料连续性优先)——编号清零目标辖代码表示,不辖既有遥测身份串。
