# 废弃全局节点编号(node_ordinal)迭代设计(总纲)

> 状态:草案(设计成稿,待对抗审;定稿后才可派落地批)。
> 立项出处:2026-09-23-invest-effects-calc 迭代 T-8(人身意外险)设计对抗中的用户裁定(2026-10-12):「废弃这个编号,单独立项」。

## 0. 元信息

- 迭代目标:废弃节点全局编号(`node_ordinal`,闭式公式 `(位面-1)*9 + 轮`)作为独立表示,节点位置/进度/数数语义全部改由 `(位面, 轮)` + 有效节点序列(场字段)承载。
- 状态:草案(设计成稿,待对抗审)。
- 文档清单:**单文档方案**——本文档 §2 即完整设计(无 `details/` 划分:这是单一表示的原子切换,各消费域改法同构,分篇只会制造跨篇对表面);落地 = [landing.md](landing.md);索引 = [README.md](README.md)。

## 1. 问题与动机

### 1.1 现状症状

1. **编号定义与序列脱钩**。全局编号的实现是一条闭式公式 `(位面-1)*9 + 轮`(cw_game_state.py:332-335),内嵌「第 1 位面恒 9 个节点」的默认环境假设。位面节点序列随投资环境变异后(人身意外险:P1=10/P2=8),公式与真实序列分叉:正解(公式)与反解(按序列累加,cw_node_schedule.py:60-74)不一致,「二元可逆」前提破(node-derivation.md §3.3),同一数字跨局含义不同(旧局 10 = 2-1,修饰局 10 = 1-10)。
2. **公式拷贝散落,单一源名存实亡**。全仓 `*9`/`//9`/`%9` 扫描(T-8 轮 5 外部审查)命中 14 处:kernel 正反解两套(cw_game_state.py:332/3350 + cw_node_schedule.py:60)、sim 独立双实现(`_ordinal_to_node`/`_node_ordinal`,cw_sim_backend.py:1298/1346)、obs 与 operations 内联三处(cw_observation.py:2273、cw_screen_battle_wait.py:379/670、cw_screen_supply_node.py:172)、商店查链反解一处(cw_game_state.py:3267)、acquired_t 快照两处(cw_effect_inventory.py:692、cw_affix_effects.py:450)、telemetry 死 helper 一处(journal_query.py:218)。每引入一个改序列的环境,都要全量扫描甄别哪些拷贝会错——invest-effects-calc/T-8 为此把改动面扩到 12 文件。
3. **表示分叉的守卫成本**。以编号为一方的消费点(锚定水位比较、效果账本去重与数数、推进水位、类型直定倒退免疫)与以 (位面,轮) 为另一方的消费点(同式岛:结算单调门、败局闩、hp 帧龄门锚)并存,两套表示的对齐义务散落在各处注释与测试里,序列一变即需逐处重审。
4. **遥测语料跨局不可比**。journal 落盘的 ord 依存局口径(旧局 9 制/新局修饰制),跨局比序错位,只能靠纪律约定(跨语料对账按 (位面,轮) 键)兜底,无结构保证。

### 1.2 根因归层

**表示层**。「节点在序列中的位置」这一维信息,被实现为「与序列脱钩的闭式公式」——公式内嵌了默认环境的序列长度假设。序列成为可变量(投资环境改节点)后,公式从「序列的一维投影」退化为「与序列并行的第二真相源」,由此派生全部拷贝与分叉症状。编号概念本身(把序列拉直成数轴,使「接下来 N 个节点」「推进 +1」「同节点去重」成为标量算术)有真实价值;垃圾的是**投影方式**(闭式公式)而非投影需求——但公式退役后编号即「序列下标」,与其维护一套永远追着序列走的间接层,不如直接以 (位面,轮) + 序列表为唯一表示、数数语义走显式序列运算(本设计 §2.0 裁决)。

### 1.3 解决到哪 / 明确不解决

**解决**:全局编号作为独立表示退役;其全部消费语义(效果账本的登记时点/到期/去重与「接下来 N 个节点」数数、推进水位与观察锚定、类型直定与倒退免疫、sim 节点窗定位、遥测落盘与查询)改由 (位面,轮) + 有效节点序列表达;全仓公式拷贝清零,表示唯一。

**明确不解决**:

- 策略侧选卡估值/打分不变(另一范围);
- (位面,轮) 的读数链本身(OCR 两位数/值域守卫)不在本迭代(invest-effects-calc/T-8 已修);
- 节点序列场字段(`node_seq_by_plane`)机制为既定前提沿用(T-8 落地),本迭代不重设计;
- 位面序列真值采集(含 P3 补采)另案;
- 历史遥测语料的旧口径 ord 不迁移(按 run 隔离,对账用 (位面,轮) 键——T-8 裁决点 4 已裁定,随编号废弃自然终局)。

### 1.4 前置与关联

- 前置:invest-effects-calc/T-8(人身意外险)落地——场字段与序列修饰层是本迭代的表示基础(本设计以 T-8 终态为基线,见 §2.0;T-8 未落地前本迭代不实施)。
- 关联:invest-effects-calc/T-8 裁决点 5(kernel/sim 双份反解合并)随本迭代整体消解,本卡按「双份+同参」过渡;裁决点 6 的坐标消费面扩面修复为过渡态正确性义务,不因本迭代豁免。
- 关联申报:同迭代设计件 T-19(劳伍派遣合同,设计成稿未落地)内引用 `node_pos_of`/`node_ordinal_of` 的「T-8 落地随迁」行,随本迭代整体失效——其触发器坐标改按 (位面,轮) 键表达,由 T-19 自身落地批消化(登记义务,不进本迭代文件面)。

## 2. 方案

### 2.0 表示裁决与基线声明

**裁决(§1.2 归层的落地形态):节点身份唯一表示 = `(位面, 轮)` 序位元组;全局编号整族退役。**

- 序位 `NodePos = tuple[int, int]`(1 基),单一源住 `cw_node_schedule`(序列真值同域)。
- **字典序 = 序列全序**:位面优先、位面内轮次次序的元组字典序,与「有效节点序列按位面拼接展平」的前缀和序逐值一致(位面主序拼接下前缀和严格单调,数学恒等,不依赖任何具体序列值)。推论:**全部比较/去重/水位语义(锚定四分支、推进去重、倒退免疫、单调门、败局闩、登记当节点守卫)改元组直接比较,零序列依赖、零参数穿线**——这正是编号表示的守卫成本(每个持序值的生产/消费点都必须正确穿 `seqs`,T-8 裁决点 6 的 14 处扫描实证)被整体拆除的机制基础。
- **数数语义显式化**:「推进 +1」= `sequence_next(pos, seqs)`(§2.1,全仓唯一后继实现,位面切换在此发生);「接下来 N 个节点」= 效果账本既有自然数倒计时(`remaining_nodes` 递减,本就是相对计数,无需坐标算术,§2.4);规划量(剩余节点数/剩余 boss 数)= 策略侧既有 `schedule_of` 求和族,不动(§2.7)。
- **T-8 终态基线**:本设计以 T-8 落地后形态为起点——`node_seq_by_plane` 场字段在役(写点唯一 = `gain_invest_env` 尾段)、`node_sequence_of(plane, seqs=None)`/`node_round_cap(plane, seqs=None)`/`resolve_plane_node_seqs(env)` 在役、`node_pos_of(ordinal, seqs=None)` 与 kernel `node_ordinal_of(plane, round, seqs=None)` 带环境参在役。本迭代 **删除** T-8 的正反解换算面(`node_pos_of`、`node_ordinal_of`、kernel/sim 双份反解),**保留** 序列直查面(`node_sequence_of`/`node_round_cap`/`resolve_plane_node_seqs`——kind 查询与读数 cap 是序列的合法直查消费,不是编号投影)。T-8 的「正反解互逆锁」测试随反解删除而退役(无编号可互逆)。
- **P3 不变**:P3 无观测 → 序列表无 P3 → 后继在 P2 末返回 None(§2.1),局终语义不变;`P3UnobservedError` 仍拦一切对未知位面的序列直查。

### 2.1 序列模块键原语(kernel/cw_node_schedule.py)

```python
#: 节点序位(位面, 轮次),二元素整数元组,1 基。节点身份唯一表示:
#: 字典序 = 有效节点序列按位面拼接展平的全序(位面主序下前缀和单调恒等)。
NodePos: TypeAlias = tuple[int, int]

def sequence_next(pos: NodePos,
                  seqs: dict[int, tuple[str, ...]] | None = None,
                  ) -> NodePos | None:
```

- `sequence_next` = 「推进 +1」的唯一实现:位面内 `r < len(seq)` → `(p, r+1)`;位面末 → 下一位面首 `(p+1, 1)`;下一位面无序列表(现役 = P3)→ **None = 超出建模域,调用方按局终处理**;`r > len(seq)`(损坏坐标)→ `ValueError` 响亮,禁静默跨位面。`seqs` 缺省 = 默认表(与 `node_sequence_of` 同参约定)。
- **退役**:`node_pos_of`(反解;唯一消费方 kernel `_node_advance_next_screen` 随 §2.2 改键后无输入)。T-8 为其加的 `seqs` 参数随删除消失。
- 保留不动:`PLANE_NODE_TABLES`/`P1_NODE_SEQUENCE`/`P2_NODE_SEQUENCE`/`NODE_KINDS`/`P3UnobservedError`/`validate_sequences`/`ENV_NODE_SUPPLY_BEFORE_BOSS`/`resolve_plane_node_seqs`/`node_sequence_of`/`node_round_cap`(T-8 面)。模块头「现役口径」段随键原语改写(真值表 + 键原语,不再出现「节点线性序」表述)。

### 2.2 kernel 节点域(字段与推进原语;cw_game_state.py)

**字段(两态生命周期与写点准入全部保留,只换值载体)**:

- `node_ord: Field[int]` → **`node_pos: Field[tuple[int, int]]`**(:2585;索引定义注释同步改写:值 = NodePos,两态语义 = 锚定态 observation `observe_node_anchor` 直写 / 推进态 logic `report_node_advance` 经原语写入,生效读口 = `effective_node_pos`)。
- `node_hist_ord: int | None` → **`node_hist_pos: tuple[int, int] | None`**(:2622;run 内单调水位 + 去重键 `(run_id, 生效序位)` 的 run 内载体,语义不变)。
- `DEFAULT_GS_SCHEMA['derivation']` 4 → **5**(:257,域版本 bump 先例 = 版本 4 两态生命周期切换批);行级 `GAME_STATE_SCHEMA_VERSION` 不动(恢复面无旧档迁移函数需求,旧档 `node_ord` 键被恢复面忽略,§2.8)。
- `cw_projection_audit.PROJECTION_AUDIT['node_ord']` 行改键 `'node_pos'`,basis 改两态键表述(:401;完备性锁双向,旧键不删即 `audit_stale_keys` 红)。

**原语(签名换载体,处置规则逐分支保持)**:

- `effective_node_ord` → **`effective_node_pos(gs) -> NodePos | None`**(:3310):= max(node_pos 现值, node_hist_pos),**max 换元组字典序**(None 安全不变)。
- `advance_node_effective(gs, candidate: NodePos, *, actor, sig, source)`(:3446):去重守卫 `candidate <= effective` **元组比较**(同序幂等);写 `node_pos`(source 由调用方定,logic/observation 两路不变);`node_hist_pos` 单调水位(元组比较);效果推进尾段同临界区不变。
- `report_node_advance(gs, *, trigger, sig=None)`(:3480):观察态门双条件不变(`node_pos.value is not None ∧ source == 'observation'`);candidate 从 `effective + 1` 改 **`sequence_next(effective, gs.node_seq_by_plane.value)`**;返回出口:
  - **`sequence_next` 非 None**:照旧落账,`applied=True, reason=f'node_pos→{p}-{r}'`(原 `node_ord→{n}` 串退役),`world_decl` 照旧推导(§2.2 末);
  - **`sequence_next` = None(P2 末终局确认)**:**局终声明事件式**——零写入(无后继序位可写)、零效果 tick(无节点进入;现行在此多 tick 一次越界序 `total+1`,属越界幽灵节点的一次虚假发放递减,见 §2.12 披露 1),返回 `applied=True, reason='match_end'` + `WorldDecl(next_screen='', trigger='node_advance')`。`applied=True` 语义 = 终结动作确实落地(对齐「applied= 动作落地」契约;对账消费面 = §2.6)。
- `observe_node_anchor(gs, pos: NodePos, *, trigger_screen, actor, sig=None)`(:3570):四分支处置语义逐字保留,比较全换元组——`v is None` → first_anchor;`pos > v` → advance 补推;`pos == v` → reanchor;`pos < v` → stale_dropped 倒退免疫留证。跨位面形态 `(1,10) < (2,1)` 由字典序自然严格(T-8 修饰局下同式成立,不需任何序列查询)。
- **删除**:`node_ordinal_of`(:332-335 正解公式)、`_node_key_for_ord`(:3350-3356 反解)、`_obs_node_ordinal` 改 **`_obs_node_pos(gs)`**(镜像已是 NodeKey,直接返回 `(cur.plane, cur.round_num)`,:3325)。

**next_screen 推导(`_node_advance_next_screen`,:3423)**:输入即键——`pos = effective_node_pos(gs)`;`pos[1] > len(node_sequence_of(pos[0], seqs))` = 防御性 `''`(不可达:终局已在 `report_node_advance` 拦截,防御保留与现行同位);`pos[0] > 1 ∧ pos[1] == 1` → 位面过渡;否则 `_NODE_KIND_NEXT_SCREENS[node_sequence_of(...)[pos[1]-1]]`。`total` 求和与 `node_pos_of` 反解两段退役。

### 2.3 类型派生与商店查链(kernel/cw_game_state.py)

- **商店查链**(:3264-3274):`_shop_panel_type_target` 改返回 `NodePos | None`(max 换元组字典序,:3345);链查询 `chain_node_type(self, _shop_plane, _shop_round)` 的内联 `//9 %9` 反解(:3267-3268)退役,改 `chain_node_type(self, target[0], target[1])`——目标本来就是键,反解整段消失。
- **直定写入**(`_write_derived_node_type`,:3617):形参 `target_ord: int` → **`target_pos: NodePos`**;`NodeKey` 构造改直建 `NodeKey(plane=target_pos[0], round_num=target_pos[1], kind=kind)`(`_node_key_for_ord` 删除的承接点);**倒退免疫** `node_ordinal_of(cur...) > target_ord`(:3641)→ `(cur.plane, cur.round_num) > target_pos` 元组比较,语义逐值等价。BOSS 简报直定宿主(kernel/cw_screen_report/boss_briefing.py:50-55)目标从 `gs.node_hist_ord` 改 `gs.node_hist_pos`,`target_pos=int(hist)` 改直传元组。
- 直定冲突/倒退 obs_event 载荷里的 `target_ord`/`node_ord` 键改 `target_pos`/`node_pos`(值 = `f'{p}-{r}'` 串或 [p, r],留证面口径随载体)。

### 2.4 效果账本(kernel/cw_effect_inventory.py + cw_affix_effects.py)

账本保持「零 import 包内模块」纪律(类型注解就地写 `tuple[int, int]`,注释指 `cw_node_schedule.NodePos`):

- `ActiveEffect.acquired_t: int | None` → **`acquired_key: tuple[int, int] | None`**(:189,注释改「登记时点节点序位快照 (位面,轮)」)。
- `ActiveEffectInventory._last_tick_node` → **`_last_tick_key`**(:222,去重键 = 序位相等)。
- `advance_node(node_ordinal)` → **`advance_node(node_key: tuple[int, int] | None)`**(:335):同节点去重 `node_key == self._last_tick_key`;「登记当节点不推进」守卫 `e.acquired_key >= node_key` **元组比较**(:365-367——语义与现行 `>=` 序数比较逐值等价,字典序=全序);`remaining_nodes` 自然数倒计时**零改动**(「接下来 N 个节点」自 T-8 修饰制起差值即真实节点数,倒计时本就不依赖坐标算术)。
- 快照两处内联 9 制退役:`_portal_acquired_t` → **`_portal_acquired_key`** 返回 `(nd.plane, nd.round_num)`(:684-693);`register_affixes_from_names` 同款内联(:448-450)同改。kernel 侧调用方 `_tick_effect_boundary_impl`(:3380-3384)传 `effective_node_pos(gs)`;frame 串 `f'p{(effective-1)//9+1}-r{(effective-1)%9+1}'`(:3383)改 `f'p{pos[0]}-r{pos[1]}'`(frame 只进 evidence/余额账,随键直拼)。

### 2.5 观察锚定写端与画面 op(operations/cw_screen/)

- `CwScreenPrep` 备战锚定(cw_screen_prep.py:292-299):`node_ordinal_of(int(_st.plane), int(_st.round_num))` → `(int(_st.plane), int(_st.round_num))` 直传;import 面 `node_ordinal_of` 移除。
- `CwScreenSupplyNode._read_node_bar`(cw_screen_supply_node.py:144-173):返回值从内联 `(plane-1)*9+rnd`(:172)改 **`NodePos` 元组**;OCR 正则与值域守卫维持 T-8 终态(`node_round_cap`,不在本迭代);调用点锚定(:214-218)传元组。
- 位面过渡 opening 判定(cw_screen_plane_transition.py:64、kernel/cw_screen_report/plane_transition.py:59):`gs.node_hist_ord is None` → `gs.node_hist_pos is None`(机械改名)。
- 注释面:cw_op_settle_confirm.py:11/:133、cw_pick_supply_action.py、cw_encounter_selection.py:238 的 `node_ord` 表述随载体改 `node_pos`(行为零改动)。

### 2.6 sim 节点窗与局终声明消费(sim/cw_sim_backend.py)

- 簿记换键:`_entered_ord: int = 0` → **`_entered_pos: NodePos | None = None`**(守卫 `eff is None or (_entered_pos is not None and eff <= _entered_pos)`,元组比较);`_window_begun_ord` → **`_window_begun_pos`**(:765/:768,窗口幂等守卫键换序位,防双发语义不变);`_pending_reconcile` 元素首槽随键(:777/:1046/:1083)。
- **退役**:`_ordinal_to_node`(:1298-1307)与 `_node_ordinal`(:1346-1354)双实现整体删除(T-8 裁决点 5 的「双份+同参」过渡态至此消解)。
- `_enter_node_window(pos: NodePos)`(:1316):`kind = node_sequence_of(pos[0], gs.node_seq_by_plane.value)[pos[1]-1]`;镜像写 `NodeKey(plane=pos[0], round_num=pos[1], kind=kind)`;锚定 `observe_node_anchor(self.gs, pos, ...)`(:1328);位面过渡臂 `pos[0] > 1 ∧ pos[1] == 1` 不变。
- `_on_node_advance`(:1089):去重守卫换键;`eff > sum(len(...))` 局终分支**退役**(键表示下不存在越界序位,见 §2.2 终局事件式);正常路径 = XP 入账(prev.kind)→ `_entered_pos = eff` → `_enter_node_window(eff)`。
- **`advance()` 增局终腿**(:988):`decl.trigger == 'node_advance' ∧ decl.next_screen == ''` → `_on_node_advance_terminal()`——XP 入账(prev.kind,与现行局终前入账同序 :1095-1098)+ `DISCLOSURE_P3_UNOBSERVED` 披露(键值 `enter_p3_game_over_u19` 保留)+ `_game_over()`;此后 `_reconcile_next_screen` 走 `done=True ∧ decl=''` 合格臂(:1067-1075),漂移面零新增。kernel 声明权威、sim 对账的既有分工不变:非终局推进仍走 `_on_node_advance` 状态重导出。
- `_node_window_target_base`/`_present_offer_or_node_screen`/`_present_node_screen`/offer 门(:1437-1441/:1451-1453/:1478):全部已按 `(plane, r)` 直查,仅随 `node_sequence_of` 的 T-8 `seqs` 参在位,零结构改动。

### 2.7 同式岛与规划量收口(operations + obs + kernel 规划面)

- **结算单调门**(cw_screen_battle_wait.py:379-381):T-8 已改元组比较 = 本迭代目标形态,**零改动申报**(依据:T-8 §2.5 绑定面;字典序即目标全序)。
- **败局闩次级证据**(:654-678):`_t = (nd.plane-1)*9 + nd.round_num`(:670)与 `SETTLE_DEFEAT_LATCH_MIN_T = 14`(:245)→ `_pos = (nd.plane, nd.round_num)` 与 **`SETTLE_DEFEAT_LATCH_MIN_POS: ClassVar[tuple[int, int]] = (2, 5)`**;门 `_pos >= SETTLE_DEFEAT_LATCH_MIN_POS`。**逐值等价证明**:`(p-1)*9+r >= 14 ⟺ (p,r) >= (2,5)`(字典序=序数序,含修饰局 (1,10)=10<14 不置闩形态,T-8 §3 零改动申报的验证依据沿袭)。
- **killed hp 对比兜底邻接门**(:455-476):`node_t_of(session, plane, round)` 时基与 `_now_t - _prev_t == 1`(:465-471)→ 序位后继判定 `_prev_pos is not None ∧ is_sequence_successor(_prev_pos, cur_pos)`;`SettlementState.last_outcome_t: int | None`(:217)→ **`last_outcome_pos: tuple[int, int] | None`**。后继判定就地纯函数 `(p1,r1)→(p1,r1+1) | (p1+1,1)`(相邻性是键的局部性质,无需序列表——较 `node_t_of` 时基还免除了 schedule_of 长度误差面)。
- **`cw_plane_table.node_t_of` 重定域**(cw_plane_table.py:106-125):本迭代迁出其唯一身份面消费点(killed 邻接门)后,在册消费仅剩策略规划量(strategy_economy.py:257-261 剩余 boss 数)。函数保留,契约注释改「规划数量语义(策略侧估算用);节点身份消费禁入(身份 = NodePos,表示唯一)」。
- **hp 帧龄门锚死局部**(obs/cw_observation.py:2268-2273):`_node_t` 赋值后全函数零读(消费端「帧龄门」已随终态契约 §A 退役,注释自述与 grep 双证)——整段删除,零行为。

### 2.8 遥测·快照·载体

- **快照**(`full_state_snapshot`,:2749):`values` 自动携带 `node_pos`(Field 迭代;`_json_safe` 元组→list,:1538);顶层 `'node_hist_ord'` 键 → `'node_hist_pos'`(:2789);effects 行 `'acquired_t'` 键 → `'acquired_key'`(值 [p, r],:2769)。
- **恢复**(`restore_state_snapshot`,:3872):复杂值重建表增 `node_pos` 条目(list → `tuple[int, int]`,先例 = node/deployed 按字段名重建);旧档 `node_ord` 键与旧 `node_hist_ord` 顶层键被忽略(历史语料不迁移裁定,恢复 = 离线判读面,零迁移函数)。
- **锚行槽退役**(kernel/cw_anchor.py):`AnchorEvent.node_seq`(:110)与 `to_row` `'node_seq'` 键(:127)、`emit_anchor` 的 `node_seq` 形参(:301/:364)与幂等键槽(:313)整体删除——锚行时点键已含 `plane/round`,`node_seq` 是编号投影的遥测镜像;`emit_anchor` 现无生产调用方(全仓 grep 零命中,登记表在册即权威),零行为面。
- **死 helper 删除**(telemetry/journal_query.py:218-224 `node_ordinal_of(row)`):T-8 已核全仓零调用方;`node_key_of`/`round_state_snapshots` 均 (位面,轮) 键,查询面合规不动。
- **defects 维度**(telemetry/defects.py:40 `'node_seq'`):缺陷维度词表成员,与编号表示无关,**零改动申报**(此处 node_seq 指「节点序列」感知维度,非序位快照)。

### 2.9 影响面与零改动申报

**改(文件面,14 文件)**:

| 文件 | 面 | 节 |
|---|---|---|
| kernel/cw_node_schedule.py | NodePos + `sequence_next`;删 `node_pos_of`;模块头口径 | §2.1 |
| kernel/cw_game_state.py | 字段两件套/schema bump/原语换键/商店查链/直定/frame/next_screen/终局事件式/快照恢复/模块头 | §2.2/2.3/2.8 |
| kernel/cw_projection_audit.py | 审计表键 | §2.2 |
| kernel/cw_effect_inventory.py | acquired_key/_last_tick_key/advance_node/frame 消费 | §2.4 |
| kernel/cw_affix_effects.py | 快照内联退役 | §2.4 |
| kernel/cw_screen_report/boss_briefing.py | hist 直定目标 | §2.3 |
| kernel/cw_screen_report/plane_transition.py | opening 判定改名 | §2.5 |
| sim/cw_sim_backend.py | 簿记键/双反解删除/进窗/局终腿 | §2.6 |
| operations/cw_screen/cw_screen_prep.py | 锚定传元组 | §2.5 |
| operations/cw_screen/cw_screen_supply_node.py | 节点条返回元组 | §2.5 |
| operations/cw_screen/cw_screen_plane_transition.py | opening 判定改名 | §2.5 |
| operations/cw_screen/cw_screen_battle_wait.py | 败局闩键门/邻接门/last_outcome_pos | §2.7 |
| operations/cw_op/cw_op_settle_confirm.py + cw_pick_supply_action.py + kernel/cw_encounter_selection.py | 注释口径 | §2.5 |
| kernel/cw_anchor.py + telemetry/journal_query.py + obs/cw_observation.py | 锚行槽/死 helper/死局部 | §2.8/2.7 |

**零改动(带依据)**:

- `node_seq_by_plane` 场字段四件套与 `resolve_plane_node_seqs`/`ENV_NODE_SUPPLY_BEFORE_BOSS`(T-8 面,既定前提);
- 读数链(`read_phase_round`/`parse_settlement_round`/`_NODE_BAR_RE` 正则与 `node_round_cap` 值域):T-8 终态,序位直读无编号;
- 结算单调门(已是元组比较,§2.7);
- 观察漏斗对 `gs.node` 镜像的写端(镜像本就是 NodeKey)与 `top_bar_raw` 观察层;
- 外循环路由、画面 op 分发、补给/遭遇/商店行为链(键化不触画面语义);
- 策略层全部(估值/打分/规划量;`cw_plane_table` 规划函数族只动 `node_t_of` 契约注释);
- 默认环境与修饰环境全部行为(字典序=全序恒等 + 逐值等价证明见各节;行为差仅 §2.12 披露 1/3 两处申报面);
- `SETTLE_DEFEAT_LATCH` 主证据链(进度符号)、`defects` 维度词表、`node_key_of`/`round_state_snapshots` 查询面。

### 2.10 关键取舍

1. **键直表示 vs 序下标制**(保留单一标量,定义为「有效序列展平下标」,全量经序模块换算):弃。下标制与闭式公式同构——每个持序值的生产/消费点都必须正确穿 `seqs`,漏穿即跨系分叉;而比较/去重/水位语义本可零序列依赖(字典序恒等)。T-8 裁决点 6 的 14 处扫描已实证该耦合的守卫成本;编号退役后仍保留下标 = 把症状换了个名字留下。
2. **兼容双表示并存渐迁**(node_ord 与 node_pos 并存):弃。双表示并存期 = 分叉守卫成本最高期,且违背「表示唯一」目标;R7 触发模型换代先例 = 原子切换、一次提交完成、无并存窗口(node-derivation.md §3.3-6)。
3. **终局仍写虚拟越界键**(如 `(2, len+1)`)保持「推进必写值」不变量:弃。越界键 = 序列外幽灵坐标,kind 查询/序列长度对它无定义,全链需特判「虚拟终局键」= 新表示内嵌特例;事件式终局(`sequence_next` = None → 声明 `''`)语义干净,且 sim 消费面本就以 `next_screen=''` 为局终预测载体(对账 :1067-1078)。
4. **NodePos 用 dataclass 而非 tuple**:弃。字典序比较是本设计的机制基础(§2.0),tuple 原生支持且 JSON 直转;dataclass 需自定义全序与序列化,零收益。
5. **规划量(`node_t_of`/`r_global` 族)一并键化**:弃。它们是数量/距离语义(「还剩多少节点」),不是节点身份;策略侧明确不解决(§1.3)。仅迁出 `node_t_of` 的身份面消费点并重定域其契约(§2.7)。
6. **AnchorEvent.node_seq 槽保留为休眠**:弃。休眠槽 = 未来编号生产者的合法入口邀请,与「表示唯一」相悖;删除成本为零(无调用方,§2.8)。

### 2.11 测试锁面设想(锁设计约定,细则归实现批 landing)

1. **后继纯函数锁**:`sequence_next` 默认表——(1,1)→(1,2)…(1,9)→(2,1)、(2,7)→None;修饰表(T-8 表)——(1,9)→(1,10)→(2,1)、(2,8)→None;(1,11) 类越界 → ValueError;P3 直查 → `P3UnobservedError`。
2. **推进原语锁**:正常推进写 `node_pos`(logic)+ hist 水位 + 效果尾段同临界区;去重(同序位幂等);观察态门(双条件,门挡留证零推进);跨位面推进 (1,9)→(2,1)(默认)与 (1,10)→(2,1)(修饰)。
3. **终局锁**:P2 末 boss 结算确认 → `applied=True, reason='match_end'`、`node_pos`/`node_hist_pos`/效果账本零写入零 tick、decl `next_screen=''`;sim 收 decl'' → XP 入账 + `p3_unobserved` 披露 + game_over、对账合格臂零漂移。
4. **锚定四分支锁**:first_anchor/advance/reanchor/stale_dropped 键版逐分支;跨位面字典序严格性((1,10) < (2,1),修饰表)。
5. **类型直定锁**:目标键直建 NodeKey;倒退免疫(镜像键 > 目标键丢弃留证);商店查链键 = 目标序位本身(无反解)。
6. **账本锁**:登记当节点不推进(`acquired_key >= node_key`,含镜像领先形态);同序位去重;倒计时行为与现役逐值同。
7. **同式岛锁**:败局闩键门与旧 t 门逐值对拍((1,10)/(2,1)/(2,5) 边界);killed 邻接门(同位面相邻/跨位面 (1,9)→(2,1)/(1,10)→(2,1) 后继成立、跨两节点不成立)。
8. **快照往返锁**:`node_pos`/`node_hist_pos`/`acquired_key` 快照↔恢复逐值;旧档 `node_ord` 键忽略不炸。
9. **默认局回归**:默认环境 sim 全链一次,窗口幂等/收入/局终轮次与现役基线逐值同(修饰局回归 = T-8 既有测试面)。

### 2.12 披露申报

1. **终局虚假 tick 移除(行为差,遥测面)**:现行终局确认会把水位推到越界序 `total+1` 并对效果账本多 tick 一次(advance_node_effective 内联于推进,越界序位无节点语义);键化后终局零写入零 tick。影响 = 尾局存活效果的 `remaining_nodes` 少递减一次、到期移除日志少一行——对局已终,账本随 run 销毁,零世界语义;sim 对账面不变(现役 sim 局终臂同在 tick 之后)。
2. **reason 串与留证载荷口径**:`node_ord→N` 串、`target_ord`/`node_ord` 留证键改 `node_pos→p-r`/`target_pos`/`node_pos`——判读脚本若硬编码旧串需随批知晓(在册判读面 grep 核对归实现批);journal 行形状变化按 run 隔离,跨语料对账按 (位面,轮) 键(§1.3 既定)。
3. **killed 邻接门免除 schedule_of 误差面**:现役时基 `node_t_of` 依赖 `schedule_of` 已揭晓长度(P3 先验 9),修饰局插入节点若晚于表揭晓时点存在时基偏差窗;键后继判定无此依赖。方向 = 更准,非回归;`last_outcome_pos` 为段内状态(非 Field),跨段残留语义与 `last_outcome_t` 相同。
4. **`emit_anchor` 形参收敛**:锚行 `node_seq` 槽退役后,未来接线方按七字段封装的文档口径(node-derivation.md §3.5 历史节/正本批更新)同步;登记表在册锚 `node_enter` 的宿主描述不变。
5. **T-8 互逆锁退役**:T-8 落地批交付的「正反解互逆锁」测试随 `node_pos_of` 删除退役(无编号可互逆);其「场字段↔live 台账对照」披露通道(序列真值证伪面)与键化正交,保留。
