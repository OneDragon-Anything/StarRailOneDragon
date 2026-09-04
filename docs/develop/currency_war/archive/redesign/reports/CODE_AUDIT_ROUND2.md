# 代码审计报告·第二轮:部署/换位通道 + 接缝修复批(S-1~S-13)+ 刷新收敛(对抗式)

- 审计立场:对抗式(假设有错、设法证明;攻不破的才进「攻过未破」)。
- 审计对象:`cw3/strategy/deploy.py`、`cw3/strategy_shell.py`(族 A CompTransaction + 族 B `decide_prep_action`)、接缝修复批 1c64d5f0 声明的 S-1~S-13、刷新收敛口径(ADR-0513)。
- 方法:全量读源码 + 生产/执行/供给三侧写点-消费点 grep 对账 + 对照原始规格(CODE_AUDIT_SEAMS.md 逐条)与判前锁(PREREG v1、ADR-0513)。
- 本报告只此一个文件,未改任何代码。

---

## 一、问题清单(按严重级降序)

### 【高-1】族 B 部署/换位通道在生产侧是死码——`obs.state` 读的是空骨架,bench/deployed 恒空

- 位置:`cw3/strategy_shell.py:640-667`(`state = obs.state` 后 `iter_occupied(state.bench)` / `iter_occupied_deployed(state.deployed)`);供给侧 `decision/decision_v2/adapter.py:94-114`(`_anchor_state` 只填 plane/round/level/gold/hp,**不填 bench/deployed/board**,`GameState()` 默认空 list,cw_state.py:219/227)+ `prep_brain.py:211`(`_select` 用 `snapshot_to_obs` 重建 obs)。
- 发作场景:生产备战环唯一路径 = `prep_director._run_prep_loop_v2` → `DecideAdapter.decide` → `prep_brain._select` → `strategy.decide_prep_action(snapshot_to_obs(...))`。该 obs 的 `state` 是锚骨架,**bench/deployed 恒空**;cw3 步 4 的 `held` 恒空 → `decide_opening` 无臂 → roster 空 → `deploy_plan` waiting/outs 全空 → plan 恒空 → **部署/换位通道在生产的每一步都被跳过,无声**。对照:decision_v2 同一 obs 通道读的是 `obs.bench_chars`/`obs.deployed_chars`(decision_v2/strategy.py:1017-1018),不是 `obs.state.bench`——cw3 族 B 读错了供给字段。真实部署回落到相位机 `RunDeploy`(旧框架 naive 拖放),**换位护栏/卖最弱/线内优先语义在生产完全不存在**。
- 判定:修复令①宣称「一台机器、两个动作面」双面接通;实际族 B 面只在 sim 侧(若 sim 有调用方)或测试桩(手搓全量 state)下活,生产恒死。这正对本次审计主指控「只修了表象」——告警/接线都写了,数据供给源头接错。
- 严重级:**高**(核心交付在生产不可达,且断得无声——没有任何 log/缺陷计数标记「plan 为空」)。

### 【高-2】族 A CompTransaction 在生产 shop 执行器被静默丢弃——遥测虚高 + docstring 虚假声明

- 位置:发射侧 `cw3/strategy_shell.py:525-545`;执行侧 `operations/prep/shop.py:848-1139`(动作分支仅 BuyCard/LevelUp/RefreshShop/SellBench,**无 CompTransaction 分支**;L838 注释「DeployMove/SellBench 仍跳过」也未提 CompTransaction)。全 operations/ 树 grep 证实零 CompTransaction 消费点。
- 发作场景:生产买牌波内,cw3 `decide_prep` 发出的 move/swap CompTransaction 逐动作循环不命中任何 isinstance 分支 → **静默 no-op**,无日志、无 `_plan_truncated` 标记、无缺陷计数。但 `record_decision(actions)`(shop.py:836)已把 moves/swaps 连同 `decisions['deploy']` 计数落遥测 → 判读/对拍看到「本轮部署 1 moves 1 swaps」,实际游戏面什么都没发生——与 S-6 修复要治的「decisions['buys'] 遥测虚高」**同型病灶在同期新代码里重现**。同时 `strategy_shell.py:525-527` 注释宣称「生产 shop 前缀执行器同形状」,与事实不符(docstring 级虚假契约声明)。
-连带效应:sim 侧 CompTransaction 真执行卖+上(engine_p1.py:1234-1304),生产侧不执行 → swap 的卖退金/池守恒/板面变化在两侧经济轨迹系统性分叉,sim A/B 结论对生产行为的外推在部署面上失真。
- 严重级:**高**(遥测可信度 + 双侧分叉 + 契约声明失实三杀)。

### 【高-3】deploy.py 换位牺牲位的「骨架护栏」失效——`classify_unit_class` 传空 held,结构可达骨架被当燃料卖

- 位置:`cw3/strategy/deploy.py:88`(`classify_unit_class(d.char_id, frozenset(), line_roster)`);判据本体 `cw3/knowledge/classify.py:142`(`structural_overlap(unit_name, held) >= 1 → CLASS_SKELETON`)。
- 发作场景:骨架三来源中线名单/插件库/5 费档不依赖 held,唯独「结构可达」(该单位参与的某 comp 与持有重叠 ≥1 → 邻接线替换有条件,不卖)完全依赖 held。deploy.py 传 `frozenset()` → 结构可达判据恒不触发。场景:板上 1★ 3 费件 X(非当前线、<5 费、非插件),bench 持有 X 同 comp 的另一件 → 正判 = skeleton(保护),实判 = fuel → **满位换位把 X 卖掉,拆散在建结构**。同文件内对照:壳的腾席卖循环(strategy_shell.py:470)传的是真 `held`——同一批、同一护栏语义、两处实现一个带 held 一个不带,自证 deploy.py 是笔误而非设计。
- 发作面:sim(族 A swap 真执行卖)+ 生产(若高-1 修复后族 B 走同一规划器)双面;当前生产因高-1/高-2 未触达,但 sim A/B 正在用这个坏护栏出数。
- 严重级:**高**(护栏声明「骨架/插件/2★+ 护栏」三分之一是空的;不可逆销毁资产)。

### 【中高-4】`waiting_unit_exists` 没跳出空位依赖的镜像 case:板满 + 无可牺牲时,升级臂一恒关——而升级恰是创造 vacancy 的动作

- 位置:`cw3/strategy/deploy.py:126-131` + `strategy_shell.py:413`(`waiting_unit = waiting_unit_exists(plan, line_roster)`)。
- 发作场景:板上满编(2★/线内成员,guard 全拦),bench 躺着线的第 4 张核心(差一级人口才能上)。此时 plan 为空(无 vacancy、outs 被 2★+ 护栏拦)→ waiting_unit=False → p39 臂一(`waiting_unit` 是其关键输入,levelup.py)不开 → **不为上场而升级的路径仍死**。docstring 声称「③ 去空位依赖:空位与换位两通道都算兑现路径」——只解了「有空位/有燃料」两态,漏了「升级本身就是兑现路径的前提」这第三态,而这恰是归因报告「升级臂一 waiting_unit 恒 False」要治的原始病灶的主体场景。修复覆盖性指控正面命中:修了谓词的输入面,没修谓词语义。
- 严重级:**中高**(p39 升级臂在最常见的满编追核心场景继续饿死;levelup 只剩 p48 攒金臂)。

### 【中高-5】族 B 相位机缺 v2 同族三守卫 + 「失败靠全量重判自愈」声明在部署失败场景不成立

- 位置:`cw3/strategy_shell.py:669-681`(相位机);对照件 `decision_v2/strategy.py:985-1025`。
- 攻击点三条:
  1. **无 M-6 门**:phase 0 满席(free_bench_slots==0)时 cw3 直接 `RunBuyPhase`——v2 的 M-6 门(decision_v2/strategy.py:994-1005)正是为防「满席进买牌 → shop.py `_handle_bench_full` 位置式卖」的 P1 残留风险而加;cw3 无此门,已封事故形态回归。
  2. **无 r23 空板出战守卫**:部署连续失败后 cw3 照发 `StartBattle`(54 局 5 次空板出战、单节点掉 24-29 血的实证形态,v2:1013-1024 有守卫,cw3 无)。「执行失败由验证链拒绝后同相位重判」的注释与代码不符:相位在**出动作时**已前移(669-681 先 ++ 再 return),RunDeploy 执行失败并不会回相位;唯一补偿是步 4 通道每步全量重判——而步 4 因高-1 恒死。两层防线同时缺席 → 部署失败时 cw3 带缺员(乃至 0 员)出战。上批遗留声明「靠全量重判自愈」**不在任何锁/判前文件里**,只是注释自证。
  3. **无 r93 deploy_fail_counts 记忆**:同一拖拽失败候选每步重发(DeployMove 失败记忆是 v2 侧 session 字段,cw3 不消费),烧步数预算到 Director stall 门才兜住。
- 严重级:**中高**(生产事故复发风险;守卫都在同仓同族现役代码里,属接线遗漏而非未知需求)。

### 【中-6】S-11 的「修复」只是一条自我豁免注释,其断言与原指控场景相抵且无出处

- 位置:`cw3/strategy/windows.py:102-110,120`。
- 原指控(S-11):`v_gap = k×(V̄+卡价)` 线性外推在 k≥2 时重复计档、门偏松,点名场景含「单成员持有 1 张再缺 2 张(k=2)」;要求至少声明线性化假设边界。本批修复 = 加注释,注释却写「换算式仅对**单成员 k 口径**经标定批校准」——单成员 k=2 **就是**被点名的重复计档场景,注释等于宣称该场景已校准,而全仓找不到 k=2 档位的标定出处(calibration.py 只有 u/H/V̄ 三常量;v_gap 是装配侧现算的纯公式)。多成员禁 R1 是修复前就有的旧门,非本批成果。净效果:行为零变化 + 一条**与审计指控相抵、无出处索引**的注释,后人读注释会误以为 k=2 已校准。
- 严重级:**中**(门方向偏松 = 过刷,真实代价;且注释制造虚假安全感)。

### 【中-7】免费刷额度每波重复授予——决策侧不按已用递减,与执行侧分叉

- 位置:帧装配 `strategy_shell.py:326`(`'free_refresh_per_node': resolve_free_refresh(state, mutations)`,纯由持卡聚合,无已用量状态);执行侧 sim `engine_p1.py:803,1004-1006`(`_free_used` 按节点递增,额度内 cost=0)。
- 发作场景:「每节点免费刷 N 次」注入局,一个备战期展开为多波(刷新收敛后多刷逐帧展开正是本批设计)。**每一波**重算帧都重新拿到全额 N 次额度 → R2 预算门 `n_max = free + ⌊…⌋` 与 R1 总账 `paid_ref = e_ref - free` 每波都按「还没用过」算;执行侧只有第一波真免费,后续波实付全价。净偏差 = 每波多批一刷的预算 + R1 总账系统性低估息损输入(spend_plan 偏小 → L 偏小 → 门偏松)。生产侧同构(游戏额度耗尽后实扣金,决策每波仍以为有免费)。
- 严重级:**中**(限免费刷注入局;方向偏松 = 过刷;决策/执行账目不一致恰是 ADR-0513 自己立的验收门要防的形态)。

### 【中-8】腾席卖循环未按「卖最弱」排序——与同批 deploy.py 换位序及所引证明口径自相矛盾

- 位置:`strategy_shell.py:464-487`(按 `bench_slots` 槽位序遍历,逐个跑 `decide_sell`,达标即卖)。
- 场景:需腾 2 席、槽 0 是 4 费燃料、槽 5 是 1 费燃料 → 先卖 4 费(退金多但毁的是更贵资产;V_opt 判据逐个独立,先过门的先死)。deploy.py 的 outs 明确 `(cost, star, idx)` 升序 = 卖最弱([32] 序),同一批两处卖件通道序不一致;module docstring 引「[32] 先卖杂件」作为本循环的依据,代码没兑现序。
- 严重级:**中**(资产销毁序次优;与声明口径不符;非崩溃)。

### 【中-9】PREREG v1 冻结面已被修复批改动,修订表无重锁记录——第二轮 A/B 若按 v1 开跑即违反自家锁纪律

- 位置:`PREREG_cw3_vs_legacy_AB.md` §5.1(「双侧策略代码冻结……禁改」)+ 修订表(仅 v1);事实:修复批改了 `cw3/strategy_shell.py`、`cw3/strategy/refresh.py`、`cw3/knowledge/invest_mutations.py`(全部冻结面)及共享 kernel 消费面,ADR-0513 记录「A/B 第一轮 40 seed 已出数并归因失败」。
- 分析:按 §5.1/§5.2,实现缺陷修复后应「本锁作废 → 修完重新锁 → 两侧同新环境全量重跑」,修订表应升 v2。当前 v1 仍是唯一判据源。风险形态:第二轮直接引用「PREREG v1」而代码已非锁时代码 → 判据与被测体版本错位;或有人以「指标没变」为由跳过重锁仪式 → 锁的「防看完数据挪线」效力被稀释(第一轮失败归因已经看过数据)。
- 严重级:**中**(流程/判据有效性;非代码 bug,但按本项目判前锁纪律属违例形态)。

### 【低中-10】`row_slot_of_deployed_idx` 越界兜底落在「卖」动作上 = 兜底即误卖

- 位置:`cw3/strategy/deploy.py:134-142`(越界 → `('back', 1)`);消费点 `strategy_shell.py:665-667`(直接 `SellDeployed(row=row, slot=slot)`)。
- 场景:deployed_idx 异常(-1/≥10,污染态)时,普通查询兜底错坐标顶多 no-op;这里兜底后**无条件发 SellDeployed(back,1)**——后排 1 号槽可能站着线内成员/2★ 核心。卖是不可逆动作,兜底方向应 fail-closed(不发动作)而非拍坐标。当前被高-1 挡住(通道死),高-1 修复瞬间暴露。
- 严重级:**低中**(dormant,但修复高-1 时必须同批修)。

### 【低-11】族 A 空位计算用去重集合——板上同名重复件致 vacancy 虚高,事务被引擎拒

- 位置:`cw3/strategy/deploy.py:71-73`(`on_board` 是 char_id 集合,`deployed_n = len(on_board)`)。
- 场景:板上两个同名 1★(合法状态)→ deployed_n 少计 1 → vacancy 虚高 1 → 发出超出容量的 move → 引擎 `deploy_cap_exceeded` 原子拒(engine_p1 `explicit_action_rejects` 计数污染)+ 拒绝事务还连带占用该决策段。同文件规范明示容量判据 = 占用数(`deployed_occupied`,cw_state.py:418「禁止 len」精神),此处用集合基数是同型错误。
- 严重级:**低**(sim 侧被校验层拦住,代价是拒单噪声;无崩坏)。

### 【低-12】注释规范批量违例:会话局部标识符与非持久出处进新代码

- 位置与证据:
  - `deploy.py:1-16`:「修复令①」「redesign 归因报告 §五」「[9]/[31]/[32]/[41]」——方括号编号与会话任务令均属注释规范明令禁止的「只在当次会话有意义的编号」;「归因报告」无持久路径。
  - `strategy_shell.py:459/514/547`:「S-6 对齐」「修复令②」——S-N 的权威源是 `CODE_AUDIT_SEAMS.md`,该文件在 `.debug/temp/`(gitignored、临时目录),**不是持久索引**;ADR-0513 同病(「依据审计 = .debug/temp/.../CODE_AUDIT_SEAMS.md」,该指针必然腐朽)。
  - `deploy.py:95,115-116`:`wi` 计数器全程自增后 `_ = wi` 显式丢弃——死变量 + 消噪声入码。
- 严重级:**低**(不发作;按项目规范「新增即违规」计)。

### 【低-13】族 B `max_units` 取陈旧帧

- 位置:`strategy_shell.py:651-653`(`frame = session.cw3_frame` 上一次 `decide_prep`/`update_target` 留下的帧,`mu = frame.get('max_units') or state.level or 1`)。
- 场景:director 环内步级决策发生在 shop 波之间,`cw3_frame` 是上波快照;若期间升级落地(level 变了),mu 仍旧值 → plan 的 vacancy 口径错一拍。有 `or state.level` 兜底但仅在帧缺失时生效,帧存在但陈旧时不兜。当前被高-1 挡住,同批修。
- 严重级:**低**。

---

## 二、S-1~S-13 逐条修复覆盖性裁决

| 项 | 裁决 | 依据 |
|---|---|---|
| S-1 付费刷生产写点 | **真修** | shop.py:1115-1139 写点存在;`refresh_counts_paid`(shop.py:301-312)免费须前后金均读到且相等、缺读按付费,正证判据与 sim(engine_p1:1004-1014 `_cost_r>0` 才计)同源;硬墙跳过不进判定。攻过的残余:点击落空(金未动)会按「免费」漏计一次——方向是多计免费=门晚开,与声明的倾斜理由自洽,不立案。 |
| S-2 node_type 三源链 | **真修** | `_node_has_combat`(shell:579-592)链 = node_type_current → last_node_type → state.node_type;词表双语并列覆盖两侧供给实测形态(sim 英文 reward/supply;生产左移源 = Hu 模板英文词、兜底 OCR 经 `_NODE_TYPE_KEYWORDS` 映射英文;'普通战斗'/'首领'/'boss' → 战斗方向正确)。读不到保守按战斗。攻过未破(见 §三-2)。 |
| S-3 归一防线 | **真修** | `ids_for_names`(invest_mutations.py:624-648)先 `normalize_invest_name` 再查,miss 告警+跳过,可观测。 |
| S-4 xp_instant/xp_flows 消费 | **部分修·挂账已声明** | 帧键已披露(shell:330-331)、sim 侧 oneshot 入账接通(engine_p1:787-793)、防双计语义清晰;但 `decide_levelup` 仍无 XP 流入参数(grep 证 levelup.py 零消费),决策质量缺口仍在。ADR-0513 已把「decide_levelup XP 流入消费」列入挂账——按「挂账须可见」标准算合格,按「审计指控被真修」标准算未闭环。 |
| S-5 免费额度进帧 | **修了但引入新洞** | R1/R2 折算正确(refresh.py:111-118,129-170);但每波重授(本报告 中-7)——门内公式对、跨波账目错,恰是「公式对」≠「对得上执行」的缝面同型病。 |
| S-6 腾席对齐 | **真修(带残留)** | sell_target = min(买入意图数, bench_cap)(shell:462-464),虚高形态消除;残留 = 卖序未排(中-8)。 |
| S-7 概率直传 | **真修** | shell:310-311 缺省读 `state.refresh_probs` 实读直传;无观测退基线。 |
| S-8 字段正式化+reset owner | **真修** | 四字段升正式声明(cw_strategy_session.py:319-337,含坐标系/写点/reset 双 owner 注);生产 reset = on_match_start(shell:252,battle_loop:779 确认调用)、sim reset = engine_p1:634。攻过未破。 |
| S-9 死快照 | **真修** | 逐帧覆写(shell:307-308),开局快照语义已废,字段注释同步改写。 |
| S-10 p2 臂透传 | **真修** | engine_p2.py:117-148 签名含 strategy_id 并透传 simulate_p1;计数归零语义补注。 |
| S-11 v_gap 线性外推 | **未真修(注释豁免)** | 见 中-6:行为零变化 + 相抵断言。 |
| S-12 卫生三件 | **真修** | `_classify_leftover` 死参 has_econ 已删(invest_mutations.py:479);占位-删除舞蹈已改为按名登记(L324 注);壳内 import 已是公开名 `bench_char_cost`(shell:126)。 |
| S-13 同段多刷定价 | **口径性消除+挂账一致** | 每帧 ≤1 刷后壳侧「同段多刷」不复存在;engine_p1:998-1000 与登记表 tag 同步保留 gap 声明,消费面一致。 |

---

## 三、攻过未破清单(攻过、证据在手、未破)

1. **刷新收敛账目(核心口径)**:发射序 卖→升级→买入→部署→刷新 在两侧落码一致(shell:502-576;engine 逐动作按 list 序消费);生产波循环(shop.py:657 `for _ in range(MAX_REFRESH+1)`)每波重读+重 `decide_prep`,每波 ≤1 刷、付费计数先写后读 → 下一波 `resolve_refresh_cost(paid)` 拿到新计数,'120'/R05 门口径随实际推进;`prefix` 截断逻辑对 cw3 恒全量执行(刷新恒末位,`refresh_idx+1 == len(actions)`,`_plan_truncated` 不触发)——323 笔买入丢失的结构(刷新截断尾部)确已消除。`n_planned` 全额入账与逐帧发射 1 刷的对账键齐备;R1「承诺账」跨帧退化为逐帧重评是 ADR-0513 明示取舍(「逐帧重判自然展开」),不判为 bug。
2. **S-2 词表完备性程序化核对**:生产 node_type_current 两条供给链(左移 `_prev[0]` = 上帧 upcoming 的 Hu 模板词 battle/supply/encounter/reward;兜底 current OCR 经 `_NODE_TYPE_KEYWORDS` 映射英文)+ `last_node_type` 中文词——非战斗形态(reward/supply/奖励/补给)全部入排除集,'首领'/'boss'/'普通战斗'/'遭遇'/'巨星' 均正确落战斗方向(保守侧)。未找到「非战斗节点被当战斗」的现存词形。
3. **S-8 跨局复用**:engine_p1:634 局装配点统一清零 + on_match_start(shell:252,battle_loop:779 局首实调)双 owner,「跨局 session 复用滚账」原指控闭合。
4. **row_slot_of_deployed_idx 主映射**:deployed 下标 0-3=前排 1-4、4-9=后排 1-6(cw_state.py:212-218 权威定义)与族 B 物理槽位语义(cw_prep_actions.py:12「前排 1-4/后排 1-N」)逐段一致;bench 域「族 B 物理槽位 = 族 A 下标 + 1」与 DeployMove.from_slot 用法一致。仅越界兜底方向有罪(低-10),主映射无罪。
5. **族 A swap 的金账**:发射序 4 的 swap 在买入(序 3)之后,但 swap 的卖退金未计入同帧任何后续门(刷新金 = gold_left 已扣完买入)——退金只落到下一帧 state.gold,下一帧全量重判,无透支面。
6. **付费刷计数与免费 proc 留证共存**:shop.py 免费正证分支(前后金相等)与计数分支判据同一(`refresh_counts_paid`),不会「留证为免费、计数为付费」双头;硬墙跳过在分支之前 continue,不进判定。
7. **S-3 回归面**:`INVEST_BY_NAME` 与登记表同源派生(import 期一次推导,invest_mutations.py:620-621),归一函数单一源在 cw_investments——cw3 未复刻第二份归一逻辑。
8. **executed 面对 cw3 动作的既有防线仍闭合**:满栏拒买守卫、decide_prep 异常留证-上抛(shop.py:726-741)、MAX_REFRESH 硬墙、买牌 x 去重——cw3 动作不逃逸执行层防线(CompTransaction 的静默丢弃是「无分支」而非「防线豁免」,已单列高-2)。
9. **DirectorV2 环生命周期对 cw3 相位机的承载**:prep_phase 环入口清零(director_v2.py:110;旧环 prep_director.py:1098 同)、步数预算/stall 门/ping-pong 停机均策略无关,cw3 相位机的「发射即前移」在环级兜底范围内(除中-5 列的三个缺口外,无新增死循环形态)。

---

## 四、总评

本批在**接缝面**(S-1/S-2/S-3/S-7/S-8/S-9/S-10/S-12)修复质量高:写点-消费点两侧都接通、fail 方向有论证、挂账显式。但**主交付(部署/换位通道)恰恰重演了接缝审计自己命名的病灶形态**——「登记/供给面宣称完备,消费/接线面断链且断得无声」:族 B 读空骨架(高-1)、族 A 被执行器静默丢弃(高-2)、骨架护栏空转(高-3),三者叠加 = 修复令①在生产为 0 交付、在 sim 为带坏护栏的交付,且正在给 A/B 出数。建议下一批以「每个新动作族必须有 grep 可证的生产执行分支 + 一次生产路径的 plan-非空断言测试」为验收门,并先于一切 sim 结论处理高-1/高-2/高-3;S-11 的注释豁免应回炉为「k≥2 拆分求和或声明未校准禁 R1」。
