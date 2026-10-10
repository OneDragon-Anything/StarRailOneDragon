# 晶矿奖励附着通道 · 设计对抗审查报告(最终稿全量「无前提对抗」)

## ① 结论

**打回**——总纲与三份详设的通道建模、sim 侧、点击兑现侧均已收敛可开工,但 ore-reward-channel §5 事件①(live 位面进入入队)的核心机制前提与代码事实相反:按设计接线规约实现,live 侧位面 2/3 的声明入队与过期清理是**永不触发的死代码**,且设计指定的测试宿主现行形态恰好掩盖该缺陷;须修订 §5 接线规约后重审(其余为 3 项整改、5 项备注,均可局部修)。

## ② 发现清单

### P1【打回】事件①「位面进入」的机制前提与代码事实不符——live 位面 2/3 声明入队与过期清理按文档实现即失效

**问题**:ore-reward-channel §5(及 design.md §2.3 同口径)声称——「判定点 = 节点锚定写(`observe_node_anchor`)**之前**——锚定前 `gs.node.value` 仍是旧 plane,入口 `ore_declared_on_node_observing(gs, incoming_plane, sig)` 比较 incoming vs 锚定前现值即可边沿检测,**锚定后已失前值**」。

**证据**(代码实况,按符号核):

- `observe_node_anchor`(kernel/cw_game_state.py:3501-3545)写的是 **`gs.node_ord`**(经 `advance_node_effective` :3377-3408,只写 node_ord + hist),**不写 `gs.node`**。「锚定写更新 gs.node」这一前提不成立。
- `gs.node` 的 live 观察写点 = `read_game_state`(obs/cw_observation.py:2596/:2603,`gs.observe(gs.node, NodeKey(plane=…))`,phase_round 每帧真读),它经 `observe_full`(obs/cw_observe_full.py:123)执行,调用位置 = `CwScreenPrep._observe` heavy 段 cw_screen_prep.py:240,**早于** observe_node_anchor(:284)与 spheres 写(:384)。
- 因此「锚定写之前」这个插入点读到的 `gs.node.value` **已被 read_game_state 更新为本帧新 plane**:incoming(= 本帧读数)vs 现值恒等,位面变化边沿**永不检出**。

**影响**:live 侧增发货币位面 2(8 金)/位面 3(12 金)声明永不入队、永不附着、永不兑现(位面 1 由事件②兜住);live 位面过渡过期清理(landing 3.4 判据之一)同为死代码。这与总纲「live 与 sim 同一生成函数、同一随机态写径」的目标直接落空一半。

**加重因素**:landing 3.4 指定的接线测试宿主 test_cw_prep_node_row_housekeeping.py,其现行接线锁形态(test_prep_entry_heavy_observation_triggers_writes,:173-218)**monkeypatch 掉 observe_full**——fake observe_full 不写 gs.node,测试面复现不了「read_game_state 先写 node」的真实序。实现者按本文档的错误前提构造测试会得绿,live 失效不可见。

**建议修法**(前值载体换源,次序硬约束保留):

- `_prev_node` 快照对拍(与 `_prev_env` 同族生命周期):在 `observe_full` 调用**之前**读 `gs.node.value` 存快照,heavy 回执后比较 `_st.plane` vs 快照 plane 做位面变化边沿;判定与入队仍须在 spheres 写之前(该次序约束本身成立,保留)。None 前值(环重建首帧)→ 视为边沿触发,与事件②经幂等守卫「该 (env,plane) 无在队条目」互吸(开局首环 None→1 与事件②的 ''→非空双触发,幂等闭合)。
- 过期触发挂在同一位面变化检测点。
- §5 事件①与 design §2.3 的「锚定前现值即前值 / 锚定后已失前值」叙述全文改写;landing 3.4 判据「入队次序」测试加注:fake observe_full 必须真实写 gs.node(或不 fake),否则测试无效。

### Z1【整改】投影审计新增行只写 ore_rewards,漏 ore_declared_pending

**问题**:ore-click-consume §3 只定义「新增 `ore_rewards` 域行」。cw_projection_audit 的域行表现含同族队列域 pending_item_grants(cw_projection_audit.py:210 附近,「入队 / discharge_due_item_grants 到点消费回写,队列 = 卡文推算知识,无观察读端」);新增的 `ore_declared_pending`(逻辑态队列、write_logic 写端三处:入队/消费/过期、无观察读端)应有同族行。缺行 = 审计面域不闭合,实现者要么漏掉要么自行拍板(违写作硬规则 2)。

**建议修法**:§3 补一条——「`ore_declared_pending` 域行:write_logic 写端 = 事件①/②入队 + sim 窗口起点入队 + 挂接入口消费 + 位面过渡过期,队列 = 登记事实,无观察读端(沿 pending_item_grants 行形态)」。

### Z2【整改】正本更新清单漏 flow/projection_contract.md

**问题**:flow/projection_contract.md「状态面板」表逐域列举 GameState 域且已含晶矿域语义(「晶矿域 OreSight.points 载点击坐标」,projection_contract.md:19)。本迭代新增两域 + spheres 写端统一过挂接入口,该表失真;landing「正本更新清单」4 条(fields.md / gain-chain.md / sim-wiring.md / invest_effects.md)未含它(§5 硬规则 4 全量同步复查的漏网项)。

**建议修法**:清单增「flow/projection_contract.md:状态面板表(ore_rewards / ore_declared_pending 两行 + spheres 写端挂接说明)← 3.1/3.4」。

### Z3【整改】kernel→obs 的模块级依赖与私有常量导入未按先例定形

**问题**:ore-reward-channel §4「常量单一源 = 从 cw_identity_obs 导入,禁复制数值」+ landing 3.1 文件面「obs/cw_identity_obs.py(仅 `_SPHERE_PERSIST_POS_TOL` 导入面,不改逻辑)」。代码现状:kernel 桶→obs 的依赖**唯一先例是函数内 lazy import**(kernel/cw_encounter_selection.py:39);模块级 import obs 无先例。且 `_SPHERE_PERSIST_POS_TOL` 是下划线私有名(cw_identity_obs.py:1434),跨包导入私有成员无先例。挂接入口(kernel/cw_ore_channel.py)模块级反依 obs = 既有「obs→kernel」正方向之外新开反向边,后续 obs 演化会拖 kernel。

**建议修法**(设计定死其一):①常量迁驻 kernel(cw_ore_channel 常量面),cw_identity_obs 反向导入(obs→kernel 正方向,`filter_persistent_ores` 消费同一常量,单一源不破,obs 侧 :1465 默认参数同步);②维持从 obs 导入,但明确为函数内 lazy 形态(沿 cw_encounter_selection 先例)且 obs 侧给非下划线导出名。「导入面」一词落成上述明确动作之一。

### B1【备注】sim 声明矿点的 r 值未定义

ore-sim §2 定了色档('金' 占位)与坐标 `(10*(N+1), 10)`,但 OreSight.points 元素是 (color, x, y, r) 四元组(cw_game_state.py:663),r 未拍板(面板矿恒 10,cw_sim_backend.py:558)。r 影响 select_ore_clicks 的「大优先」排序键(cw_prep_actions.py:62)与配对半径语义。建议补一句「r = 10(与面板点同)」。

### B2【备注】ENV_ORE_GRANTS 校验「逐位同值」未声明同长前提

ore-reward-channel §2 校验三条中「同键 ENV_ECONOMY 有非空 gold_per_plane_start → 逐位同值」隐含两元组同长(长度 3 校验只在 ENV_ORE_GRANTS 侧);ENV_ECONOMY 条目长度若 <3,「逐位」语义未定。现唯一条目 (6,8,12)(cw_investments.py:1176)长度 3 不触发,建议补「非空时长度须等于本表值长度」半句,防未来登记踩坑。

### B3【备注】配对贪心的平局打破未定义

§4 步序 3「贪心排序键 = 欧氏标量距离,最近者优先」+「配对歧义时任取一致配对」并存:距离完全相等的两对,排序结果依实现(Python 稳定排序下由候选对枚举序决定,确定但未声明);「任取」措辞可能被实现者读成额外随机。建议注一句「平局依 (旧列序, 新列序) 字典序稳定打破,贪心序确定,无随机」。

### B4【备注】「该位面首个备战档呈现」措辞可读出额外状态

ore-sim §2 的实际语义 = 每个 SCREEN_PREP 呈现帧查 pending(有当前 plane 条目即加声明矿点),「首个」由生成时出队自然保证(呈现帧即挂接入口生成帧,出队后 pending 空)。字面「首个备战档呈现」可能被读成需要额外的「首帧判定」状态。建议改为「备战档呈现帧查 pending(声明出队后自然只在首个备战档出现)」。

### B5【备注】策略禁读 ore_rewards 在 sim 侧无机械护栏(设计已声明取舍,记录在案)

双层防线(随机态域落 logic_rand_fields 不可信侧口径 + 文档契约)与 hp_readable 先例(kernel/cw_hp_policy.py:52)一致,sim 读附着 = oracle 泄漏仅靠纪律与复盘判读兜。可选加固(下批立项评估):sim 装配方给 ore_rewards 加访问计数钩子,局终断言策略零读。本稿不阻塞。

## ③ 依据核验表(设计关键依据 vs 代码实况)

| # | 设计依据(出处) | 代码实况 | 判定 |
|---|---|---|---|
| 1 | 点击时内联掷骰 `reward = roll_ore_reward(roll_rng, int(level))`(design §1 症状 1) | collect_ore.py:138 属实 | ✅ |
| 2 | OreSight 只载存在性(色/坐标/半径) | cw_game_state.py:648-663 属实 | ✅ |
| 3 | 增发货币 = PlazaPortal id 103「第一/二/三位面开始时,获得一个 6/8/12 金币的晶矿」 | cw_invest_data.py:372 逐字属实 | ✅ |
| 4 | sim `_apply_env_plane_gold` observe 直发金、`_begin_node_window` 调用(design §1 症状 3) | cw_sim_backend.py:1480-1494 / :1357 属实 | ✅ |
| 5 | live 侧 `ENV_ECONOMY_PENDING_VERIFICATION['增发货币晶矿自动开启']`(design §1 症状 3) | strategies/impl/mandate_v1/env_economy.py:171-176 属实 | ✅ |
| 6 | write_logic_rand 语义:观察覆盖差异=预期、消费前必须重观察、hp_readable 消费门先例(channel 问题与约束) | cw_game_state.py:3017-3048 / cw_hp_policy.py:52 属实 | ✅ |
| 7 | `_SPHERE_PERSIST_POS_TOL=12`/`_SPHERE_PERSIST_R_TOL=6`、Hough `minDist=35`、`filter_persistent_ores` 为容差 any-match 非坐标稳定器 | cw_identity_obs.py:1434-1435/:1561/:1462-1482 属实;误配几何定量 35−2×12=11≤12 数学正确 | ✅ |
| 8 | ENV_GIFTS ∩ ENV_ECONOMY=∅ 的语义 = 单一环境只落一个估值结构,ENV_ORE_GRANTS 不参与该检查 | cw_investments.py:1349-1352 属实;新表现无三表互斥闸、不触发 | ✅ |
| 9 | `_validate_env_economy` import 即炸先例、INVESTMENT_ENVS 孤儿校验族 | cw_investments.py:1200-1231 属实;增发货币 ∈ INVESTMENT_ENVS(:717) | ✅ |
| 10 | kernel 确定效果直写 write_logic 先例(cw_exec_state 金腿 / cw_effect_inventory 退款腿) | cw_exec_state.py:55-73 / cw_effect_inventory.py:853-864 属实 | ✅ |
| 11 | occupied_equips 键 'front:1' 字符串键先例 | cw_screen_prep.py:375 属实 | ✅ |
| 12 | rng 解析口 `action_sampling_rng`:live 未装配回退现掷、sim 装配方为泛型 lambda tool(键自动生效、本阶段零改动) | cw_action_report/__init__.py:81-94 / cw_sim_backend.py:1628-1629 属实 | ✅ |
| 13 | `_prev_spheres_raw` 先例:op 成员、每备战环重建、环内连续帧 | cw_screen_prep.py:194-203 属实 | ✅ |
| 14 | 现观察序「锚定写在前、spheres 写在后」 | 锚定(:284)在 spheres 写(:384)前属实;**但「锚定前 gs.node 仍是旧 plane / 锚定后失前值」错误**(gs.node 由 read_game_state 经 observe_full :123 更新,早于锚定;锚定写的是 node_ord 不是 node) | ❌ → P1 |
| 15 | active_env 为 gain_invest_env 动作落地链逻辑写、无观察时点 | cw_gain_chain.py:465-483 属实;全库无 active_env observe 写 | ✅ |
| 16 | `_json_safe` dataclass→dict、tuple→list;恢复表按字段名重建复杂域(node/deployed 重建 λ 先例);node 不在开局种子表 | cw_game_state.py:1515-1525/:3878-3885/:1983-2018 属实 | ✅ |
| 17 | 开局种子恒写 level=3 | cw_game_state.py:2003 属实 | ✅ |
| 18 | `reward_ore_points()` 点列 i 从 1 起 (i*10,10)、面板 8 点(金1蓝5灰2) | cw_sim_backend.py:491-493/:543-559 属实;P1 首节点 = reward(kernel/cw_node_schedule.py:28-31)故「第 9 点 (90,10)」例子真实可达 | ✅ |
| 19 | test_cw_collect_ore_rand.py 7 处 monkeypatch(:160/:186/:212/:237/:254/:280/:308) | 逐一核对,7 处行号全中 | ✅ |
| 20 | REWARD_ORE_CONTENT_PLACEHOLDER / ORE_CONTENT_PENDING_U23 现存且删除不破测试 | 定义于 cw_sim_backend.py:496/:503;测试仓无断言(grep 零命中) | ✅ |
| 21 | test_cw_sim_seam.py provider 装卸断言形态实存('collect_ore' 键) | :194-219 属实 | ✅ |
| 22 | sim 第一期辖域 P1+P2、plane>2 raise、位面 3 不可达(12 金由 3.1 单测覆盖) | kernel/cw_node_schedule.py:50-57(P3UnobservedError)/ cw_sim_backend.py:1330 属实 | ✅ |
| 23 | 投影审计现晶矿条目(gold 行「collect_ore 采样直写」、spheres 行「零逻辑写端」) | cw_projection_audit.py:105/:230-232 属实;设计改法与现状对齐 | ✅ |
| 24 | sim 窗口幂等守卫 `_window_begun_ord`(位面过渡点空白与直进节点共用、重放不双发) | cw_sim_backend.py:1336-1344/:864-866 属实 | ✅ |
| 25 | `discharge_due_item_grants` sig=logic_sig('sim:env') 同组同窗先例;logic_sig = logic_action 族 sim 现行构造形态 | cw_sim_backend.py:1364-1365 / sim/cw_sim_base.py:37-40 属实 | ✅ |
| 26 | ENV_ECONOMY['增发货币'].gold_per_plane_start=(6,8,12)(双源同值校验的另一源) | cw_investments.py:1176 属实 | ✅ |
| 27 | select_ore_clicks 现状「颜色与半径仅排序消费,不进载荷」(契约注落点) | cw_prep_actions.py:47-63 属实 | ✅ |
| 28 | write_logic / write_logic_rand sig 族校验 = (logic_action, logic_hook)——live hook(logic_hook)与 sim(logic_action)两形态均合法 | cw_game_state.py:3012/:3049 属实 | ✅ |

## ④ 实现者试读(四阶段能否凭文档开工)

- **3.1 kernel 声明通道与生成内核**:**能开工**。域定义/索引注释/种子/恢复登记/注册表校验/生成函数签名与掷序/挂接入口五步步序/入队幂等与过期,全部到位;微缺口 = B1(声明矿 r 值)、B3(配对平局),一行拍板级,修订时顺手定死即可。
- **3.2 点击兑现**:**能开工**。命中/缺项兜底/level 收窄/reason 优先级/detach 写序/既有出参保留边界完整;测试迁移面具体到行号(核验属实)。
- **3.3 sim 接线**:**能开工**。分道条件、声明矿坐标续接(禁独立起号的撞键论证成立:by_xy 字典键去重,collect_ore.py:95)、占位退役、披露键、确定性论证(泛型 lambda tool 核验属实)齐备;B4 措辞微调即可。
- **3.4 live 挂接**:**不能可靠开工**——事件①接线规约的机制前提错误(P1):照文档实现 = 位面 2/3 声明永不入队的死代码,且指定的测试形态掩盖缺陷;事件②(快照对拍)与 spheres 写端挂接、契约注落点本身可开工。P1 修订(§5 接线规约改快照对拍 + 测试构造约束)后须重审本节。
- **末阶段正本更新**:清单可执行但缺 projection_contract.md(Z2),补齐后闭合。

**治本核(核三)**:§1 归层「语义层」成立——奖励确定时点建模在点击环节而真值时点在矿进入世界、声明矿与随机矿缺统一内容通道,两症状(内联掷骰/固定矿不可表达)与 sim 直发金脱钩同根;§2 修的是内容通道与确定时点本身,非症状补丁;晶矿内容建模此前仅 v0 内联一件,本迭代建统一通道不属「同族第 N 件」复发。归层与根治性通过。

**规范遵循核(核二)**:文档构成四件齐;landing 阶段小节七件齐、固定末阶段在、首节常规检查在;README 仅串文档与进度;正文无过程叙事措辞;依据就地标注密度高且 28 项核验 27 项属实。违例项 = P1(依据标注了与代码相反的事实)、Z1/Z2(实现者无需再设计/全量同步复查两个小缺口)。

**修复后重审范围**:P1(ore-reward-channel §5 事件① + design §2.3 对应句 + landing 3.4 判据注)必修;Z1-Z3 随修订带上;B1-B5 顺手定死。其余部分本稿已收敛,无需重攻。
