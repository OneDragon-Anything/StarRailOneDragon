# 视界族与 9 制几何层清扫(详设)

## 问题与约束

**指派依据(用户已裁,非本篇新立)**:T-8 裁决点 7(「具名常量 9 制几何层」= `NODES_PER_PLANE=9` + `schedule_of` [1,9] 夹取 + (9,9,9) 先验 + `node_t_of`;方法论勘误 = 扫描须含具名常量族)+ 裁决点 9(「剩余节点数属策略侧职责,框架不提供;策略需要自行从场字段序列计算」「函数退役与策略侧自算迁移随废弃编号迭代清扫面」)。

**总纲接口契约引用**:design.md §2.0——节点身份 = `NodePos` 键;有效节点序列唯一真值 = `gs.node_seq_by_plane`(T-8 场字段,None 回退默认表);本篇只辖**数量语义**的长度真值源迁移,不辖身份表示。

**约束**:
1. 策略决策口径语义不变——剩余节点数含当前节点、`gold_next_nodes` 按「剩余−1」截断、boss 通道「含当前节点口径偏高」既有申报保留;只换长度真值源与消除夹取/P3 虚拟轮(行为变化见 §8);
2. kernel 禁 import strategies 桶边界不动;
3. 框架不向策略新供视界量(裁决点 9 字面)——序列模块只留键原语(`sequence_next` 族),禁加「剩余节点数」类公共视界函数;
4. P3 = 建模域外 = 运行终局(bot 进 P3 即走结束链),视界封顶 modeled planes(场字段键集 = P1+P2);现役 P3 虚拟 9 轮先验移除;
5. 零新长度常量(horizon 层既有纪律沿袭,R3-2/「TOTAL_NODES=27 病灶」)。

## 方案

### 1. 真值源与读取面

长度真值 = `gs.node_seq_by_plane.value`(场字段);None(未注册,开局 P1 前段)回退默认表。读取口 = `cw_node_schedule.node_sequence_of(plane, seqs)`(现役 API,零新增);位面遍历域 = 序列表键集(现役 {1,2})。**不新建任何视界公共函数**——本篇所有迁移都是消费方就地或策略门面内部实现。

### 2. cw_plane_table 退役清单(9 制几何层整体退役)

- **退役**:`node_t_of`、`schedule_of`、`r_remaining`、`r_global`、`r_remaining_in_plane`、`plane_offsets`、`plane_end_slots`、`NODES_PER_PLANE`、`TOTAL_NODES`、`DEFAULT_PLANE_LENGTHS`、`PLANE_FALLBACK_PRIORS`(11 符号;消费迁移见 §3-§6,消费清零依据 = 本篇 §3-§6 逐条)。
- **保留**:`nodes_of_plane`(实况读、不夹;P2=7 语义依据 = cw_discipline_rules.py:68「P2 boss@r7 判正,旧按 9 计永不触发」,docstring = cw_plane_table.py:129-139;消费 = cw_discipline_rules:79、cw_line_switch:208、cw_economy:1408、cw_intention:366,零改动——唯 :366 None 回退分支与 :96-100 import 随退役迁移,见 §5)、`clicks_to_level`/`level_cost`/`peak_refresh_level`/`HP_LOSS_MU`/`p_win_p2`(标定/胜率族,非几何)。
- `nodes_of_plane` 回退常量再基:表缺回退从 `NODES_PER_PLANE=9` 改 `len(node_sequence_of(1, 场字段现值 or None))`(修饰 10 / 默认 9;session 非 GameState 时按 None);一次性告警保留;消费点注释随回退语义同步(cw_economy.py:914「缺表回退先验 9」句)。
- 模块头「现役口径」段随退役改写(几何层退役声明 + 保留面清单)。

### 3. 策略门面重基(mandate_v1/statefn/horizon.py;签名不变)

- `r_remaining(session, plane, round)`/`r_global`/`r_remaining_in_plane` 内部改场字段求和:`remaining = Σ_{p>plane} len(seq[p]) + (len(seq[plane]) − round + 1)`(含当前节点,与现行 `r_remaining_in_plane = plane_length − (node_in_plane − 1)` 半部逐值同式;planes = 序列表键集;None 回退默认表)——语义逐字保留(含当前节点、到局终)。
- 门面 `__all__` 去 `schedule_of`(随退役);`delta_interest_flow`/`delta_w_increment`/`r_trunc` 不动(证明常数族 λ₃ 窗,非几何)。
- 模块 docstring 单一源声明改「场字段(`gs.node_seq_by_plane`)」;裸 session/None 的 duck-typed 读出门面内部自备(`_probe_books` 同款模式)。

### 4. 策略侧直连 import 改道(消费零逻辑改动)

- `proof.py:49`、`budget.py:48`、`criteria/levelup.py:339-341`:`r_remaining` 改从 `statefn/horizon` import(签名同)。
- `strategy_economy.py:56-60`:`node_t_of`/`plane_end_slots`/`schedule_of` 三 import 随退役删除(通道 4 改写见 §6);:64 门面 import 零改。
- `shop.py`(:1342/:1799/:2394/:2564)经门面调用,零改动。
- `statefn/odds.py:23-25`(`peak_refresh_level` 标定表)零改动。

### 5. kernel 消费就地迁移(禁新公共视界口;就地 ≤3 行,注释互锚 + 指裁决点 9)

| 消费点 | 现状 | 迁移 |
|---|---|---|
| cw_economy.py:1121(溢金视界 `rounds`) | `r_remaining(session, …)` | 场字段求和就地 |
| cw_intention.py:952(超窗出口 `r_rem`) | 同上 | 同上(与 cw_economy 注释互锚) |
| cw_economy.py:213-225(hp_safe 阈 `nodes_left` 闭式) | `(plane-1)*NODES_PER_PLANE + …`/`TOTAL_NODES` | 场字段求和(修掉闭式与夹取;行为变化见 §8.6) |
| cw_intention.py:371-376(`total_remaining_nodes`) | 恒按 9/位面计(29 号稿 :26 已登记禁消费缺陷) | 场字段求和修正(:407 遭遇窗门唯一消费保留) |
| cw_intention.py:96-100(模块级 import)+ :366(`plane_remaining_nodes` None 回退分支) | import `NODES_PER_PLANE`/`TOTAL_NODES`/`r_remaining`;:366 `else NODES_PER_PLANE` | import 随退役清理;:366 None 分支改 `len(node_sequence_of(1, None))`(默认表 P1 长,与 nodes_of_plane 再基同款) |
| cw_comps.py:1655-1656(早期判)/:2300-2302(commit)/:2546-2551(信号 2 ceiling) | elapsed/remaining 闭式 ×3 | 模块内私有 elapsed/remaining 场字段求和 helper(同文件三调用点合一,非公共视界口;elapsed = Σ_{p<plane} len + round,含当前节点口径与现式同) |
| cw_registry.py:478、operations/cw_screen/cw_screen_prep.py:1146 | 注释涉退役符号 | 注释随改 |
| strategies/impl/mandate_v1/criteria/refresh.py:71 | docstring 坐标系句引「kernel/cw_plane_table.r_remaining」 | 改指策略门面(注释级) |

### 6. strategy_economy 通道 4(boss 计数)场字段 kind 化

剩余 boss 数 = 场字段序列自当前节点(含)起 `'boss'` 计数——kind 直查替代「位面末槽 × 每位面恰一 boss」几何假设(修饰局 boss 位移与未来序列变异天然正确)。**默认局数值变,非逐值不变**:现役 `plane_end_slots(schedule_of(gs))` 对 P3 先验 9 使 P3 虚拟末槽恒计入(P1 段 3 个、P2 起 2 个),kind 化封顶 modeled planes 后 P1 段 2、P2 起 1——P3 虚拟 boss 移除,方向与 §8.2 同(不可达节点不计),行为申报见 §8.3。通道 2/3/5/6 的 `remaining`(:241,经门面 `r_global`)零改;:209-228 docstring 与模块 docstring(:23-31,`PLANE_FALLBACK_PRIORS` 先验回退句)随改。

### 7. audit/标定面

- `audit/derived.py:72-74`:R_全局 长度真值源注改场字段;`cw_plane_table.schedule_of`/`PLANE_FALLBACK_PRIORS` 符号引用随退役更新。
- `audit/calibration.py:68`:`E2_DOMAIN_R_REMAIN_MAX` 27 → **18**(场字段 modeled 总长最大值 = 修饰 P1+P2 = 10+8;依据注释);:47 网格域注释「T=r_remaining∈{1..27}」随改(上界同源)。

### 8. 行为变化申报(策略规划输入的真值修正,T-8 裁决点 9 认定的缺陷修复面;变化项逐项列,不变项逐项给依据)

1. **修饰局视界「少 1」夹取偏差消除**(schedule_of 把实读 P1=10 夹回 9 的方向性偏保守——裁决点 9 点名的故障);
2. **P3 虚拟 9 轮移除**:视界封顶 modeled planes(P1+P2 = 16/18;现役 schedule_of 先验 9/7/9 = 25、TOTAL_NODES 闭式 = 27,两套口径本就互异)——与 bot 生命周期一致(进 P3 即结束链),P2 末段不再计入不可达轮;
3. **boss 计数默认局亦变**:P3 虚拟末槽移除 → P1 段 3→2、P2 起 2→1(gold_per_boss_node 通道现金分随之;方向 = 不可达节点不计,与 §8.2 同源);
4. **hp_safe 阈 nodes_left 封顶变化**(cw_economy:213-225 迁移):27 制闭式 → 场字段 modeled 总长,默认局 P2 r1 即 18→7(P1 段同式不变)——hp 安全阈不再计入不可达的第三位面虚构余量;
5. 裸 session/None 回退先验 9 → 默认表长度(默认局数值不变,修饰局 10/8);
6. 标定域 27→18 收紧(校准网格定义面,非运行行为);
7. **默认局不变面**:门面 `r_remaining`/`r_global` 对默认表逐值同现役 schedule_of 口径(含当前节点语义保留);`total_remaining_nodes` 修正后默认局 P1/P2 段与门面同值(P3 段不再虚构);cw_comps 早期/commit 判据默认局逐值不变(elapsed 口径与现式同,§5)。

## 关键取舍

1. **策略门面保留签名重基 vs 六消费文件全部就地自算**:门面是策略侧自有件,由它自算正合裁决点 9(kernel = 框架不提供;策略模块自算),消费面 churn 最小。弃:全部就地——六文件重复同段求和,漂移面更大。
2. **kernel 两判据点就地 ≤3 行 vs 新公共 helper**:裁决点 9 字面禁止新公共视界口(口子一开,策略回引 = 违裁决);两处就地 + 注释互锚,重复面 6 行可控。弃:helper。
3. **cw_comps 模块内私有 helper vs 三处就地**:同文件三调用点合一是普通去重,不属公共视界口。弃:三处就地(同文件三副本)。
4. **schedule_of 整体退役 vs 去夹保留**:消费清零后无主;[1,9] 夹取与场字段真值结构性相抵。弃:去夹保留——留无消费几何函数 = 第二真相源回潮 invite。
5. **total_remaining_nodes 修正 vs 退役**:唯一消费(cw_intention:407)在役;已登记缺陷顺手修正。弃:退役。
6. **标定域 27→18 vs 留 27**:视界上界 18 下,27 含永不进入的死区间;18 = 新真值上界。弃:留 27。
