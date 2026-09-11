# ADR-0564 — 配方底线门「锁定线语境豁免」:门判定收敛 kernel 单一函数 + 五处消费点全量接线

- **Status**: accepted
- **Date**: 2026-09-07
- **关联**: ADR-0261(r288 门本体与档值单源)、ADR-0360(件3 deploy 围栏锁定键放行,同型缺省兼容先例)、ADR-0534(转型臂——本批复活其列车线通道)、dd-037(部署发射⇔执行单一源契约)
- **设计稿**: `.debug/temp/currency_war/fix_recipe_floor/方案-v3.md`(终稿,含再攻 B2/B3 全部修订;本 ADR 为其判据与决策载体)

## 1. 背景与问题

实机形态:「锁定列车线 + deployed 恒 7/8 + bench 列车 core(姬子·启行)恒不上板 + 每帧空批兜底」。机制链:

1. **门本体**(ADR-0261 裁决选项3):`select_deployments` 的 r288 配方底线门——列车 ≥2 档 ∧ 仙舟 <3 → 列车件让位留 bench(仙舟基础线优先,局 23/24 实锤的既定配方纪律);
2. 门辖**全体桶**(终选循环逐件判定)→ 发射侧 `has_deployable` 判 False → mandate 三发射位(M5/M1/M1′)不提案 RunDeploy → 决策序落 StartBattle 兜底;
3. 执行侧从未运行 → **执行侧计数零痕迹**(I5 根)——发射短路形态下 op 侧遥测结构性无帧。

与 ADR-0261 的关系:门本体与档值(列车 2/仙舟 3,注册表锚 cw_factions tiers 首档)**不动**;本批 = **辖域收窄**——锁定线语境 ∧ 本帧无有效仙舟供给的帧门让位。

## 2. 决策(裁决)

豁免条件 = **(1) ∧ (2)**,判定收敛 kernel 单一纯函数 `recipe_floor_holds(main_faction, train_now, xz_now, lock_exempt_armed, supply_exists)`:

- **条件(1) 锁定线语境**(单源 = `cw_intention.locked_line_recipe_floor_conflict`):`ist.locked_comp` 非空 ∧ `get_comp` 可解析 ∧ `comp.form_tiers['列车同行'] > RECIPE_FLOOR_TRAIN_CAP`(门封顶档)。只读 locked_comp,**禁 scope 成员判**(见 §5-I3);失效安全不依赖清空路径枚举——locked_comp 逐帧重读,任一清空路径(驱逐/撤销换 weak/撤销换 unlocked/降格终局,赋空点五处)或套名解析失败都自动关豁免。
- **条件(2) 本帧无有效仙舟供给**(单源 = `xianzhou_supply_exists` 四条件谓词):全羁绊含仙舟 ∧ 非 item_slot ∧ 非同名在场 ∧ 主阵营≠列车同行。死供给三类排除防 I2 死锁换形复发。
- **五处消费点全改走单一判定,禁分支副本**:
  | CP | 消费点 | 接线 |
  |---|---|---|
  | CP1 | kernel `select_deployments` | 新参 `recipe_floor_lock_exempt`,门改走 `recipe_floor_holds`,供给惰性(armed 才现算) |
  | CP2 | op 主拖拽循环 | `r288_hold_now` 适配器(动态 `_deployed_fac` 增量真值保留) |
  | CP2′ | **op 输入装配段计划构造**(B2/N1 第五消费点) | `_sel_dep(...)` 直传同帧武装布尔——漏武装 = 计划层仍 held 列车件(order 不含)→ 豁免执行侧静默失效,恰回「零痕迹」形态 |
  | CP3 | op P24 fill 过滤 | `filter_fill_plan_by_floor` 纯函数(与主循环同消费适配器,kernel 留 bench 件不得绕回上板) |
  | CP4 | swap | `SwapPlanContext.recipe_floor_lock_exempt` 显式下传,`select_swap_plan` 卖后假想上序穿参 |
- **API 家族全量穿参**:`select_deployments_reasoned`/`has_deployable`/`has_deployable_reasoned`(新增,发射侧遥测载体)/`can_deploy_single` 各带同名新参。
- **新参缺省 False = 逐位同旧**(ADR-0360 件3 同型硬保证):豁免分支永不触达、供给谓词不被执行(计算面同旧)。生产接线全量生效,**不是策略开关**(无默认关悬置;生产链无「接线可拆」开关)。
- **遥测双写**(I5,全部走 `cw4_counters`,零新增管道):
  - 发射侧(mandate._deployable,reasoned 化):`deploy_emit_held_<reason>`(帧级去重三键之一,并集语义)/`deploy_emit_floor_ctx_open`(分母)/`deploy_emit_floor_exempt_open`(armed 帧无豁免对照补跑,拒因消失 = 开火,G1 读数);
  - 执行侧(op):`deploy_exec_held_<reason>`(每 execute 一次)/`deploy_exec_r288_skip_ctx_open|closed`(主循环门命中与 P24 剔除按帧武装布尔分桶,M4 漂移显影键);
  - **漂移键成因**:武装布尔只读 `ist.locked_comp`(意向状态机单源),**不读 bench**——「发射帧开、执行帧关」的唯一成因 = 意向状态机自身翻转(决策⇔执行间隙清空/换线),归因锚指向意向事件流,不指向 bench 供给变化。
- **sim 接线**(I4):4 调用点显式穿参;`_rf` 计算独立 try/except(fail-closed False)且显式后置于 `_lf` 赋值之后——禁与 `_lf` 同块/同 import 组(裸 except best-effort 的既有兜底不得被新增量故障面连坐清空)。sim 行为缺省逐位同旧;接线 = ADR-0261 选项3 可见性的延续。

## 3. 对既有决策的显式推翻

**被推翻**:op 主循环门注释「锁线路径的线内件上板也要守配方底线(锁线路径无守门=审查②盲区)」的**辖域**(cw_op_deploy 原 L1109-1110;该次审查把 r288 门刻意扩辖到锁定线)。推翻理由:

1. **前提不成立于空槽通道**:r288 的伤害机制是「驱逐」(板满下列车 3 档吃板挤掉仙舟件);豁免放行的部署只发生在 vacancy>0 帧(三发射位均有 vacancy 门),空槽上板不驱逐任何件。理背书 = P24 残余补部署支配定理「空 cap 槽上任意合法单位 ΔEV≥0」——本门对空槽填人的拦截本来就是该定理的人为例外,豁免把例外收窄回「有真供给竞争」的帧。
2. **门的保留目标换承保人**:仙舟基础线保护在锁定线语境下由条件(2) 供给保留条款继续承保——bench 有真供给时门照拦、供给先上;锁定线并不放弃仙舟(列车线自己的 core 含仙舟双籍件,丹恒·饮月 = 仙舟主阵营+列车同行,注册表事实)。
3. **原决策针对的通道闸门未拆**:驱逐通道闸门(victim 侧 W209 熔断、成型臂 fp≥1.00∧板满、转型臂逐件守卫、守恒门)原样;残余暴露 = 未成型引擎仙舟件 1★ 换血让位(围栏在案,进 G5 监测)。

## 4. Considered Options

| 方案 | 裁决 | 理由 |
|---|---|---|
| A 仅改发射侧(has_deployable 放行) | ✗ | 执行侧两道门副本仍在:「静默不发射」变「发射了执行不了」,更差 |
| B 无条件全豁免 | ✗ | 失去仙舟基础线保护,r288 裸奔 |
| C 豁免判据键在 locked_faction_scope 成员 | ✗ | P1 配方锁(桥对)帧 locked_comp='' 但 scope 非空 → 门在过渡期误开 = 重开 r288 暴露面 |
| **D 锁定线语境 + 有效供给条款 + 单一判定函数 + 五消费点接线** | ✓ | 本批 |
| E P1 框架帧同豁免 | ✗ 暂缓 | 见 §7 占位裁决 |

## 5. 后果与边界

- **I3**(禁 scope 判):helper 只读 locked_comp,结构上不可触达 p1_pair;桥池列车目标档=2 = 门封顶,过渡纪律全额生效(回归锚 = 测试 1③ 桥对帧变体)。
- **转型臂列车线复活**(收益 + 监测义务):锁定列车线帧上卖后假想态的列车 core 不再被 recipe_floor 持有 → 拒因 `post_sell_held` 不再恒现 → ADR-0534 转型臂对列车线恢复「卖 1 上 1」能力;进 G5 监测(`swap_arm_transition_trigger` 轮差分)。
- **残余暴露**:未成型引擎仙舟件 1★ 换血让位通道(守恒门/star_guard/素材守卫围栏在案,经济有界)。
- **M4 漂移键**:见 §2 遥测节成因注(意向状态机自身,非 bench)。
- **sim 可观测性**:①kernel 门判定 + 发射侧谓词 = sim 可见(接线后);②op 执行侧门改造与执行侧遥测 = sim 结构性不可见(实机 only,G6);③发射侧键经 cw4_counters 轮差分入 sim 账本,执行侧键仅 op 局终快照链;④swap 执行侧卖出 = sim 结构性不建模(m1p 只记发射意图),涉 swap 离场的判据一律实机 only。基线侧「发射短路帧」为结构性无帧,禁把基线盲区读数当零值证据。

## 6. 判据节(A/B 预注册;先 commit 后跑批,载体 = 本节)

**性质申报**:结构性修复(支配性论证支撑,§3),A/B = 落地后确认性对拍与实现验证,不构成采纳裁决。基线协议:改前 HEAD 跑 `cw_sim batch --n 60 --pool snapshot`,seed_base=0,记批头池指纹(协议锚 = ADR-0261 修订1;历史指纹 942d3f79c09e2eb5 仅供协议对照);改后同参数同池同种子;digest/轨迹级两侧钉 `PYTHONHASHSEED=0`;影响面必跑 `cw_replay --diff` 看行为漂移首发点。

预注册判据(六组):

- **G1 生效门**:锁定线帧集 `deploy_emit_held_recipe_floor` ≈ 0;`deploy_emit_floor_exempt_open` > 0(开火验证:新机制触发 0 次 = 输入死,先查接线再谈效果)。
- **G2 收益向**:锁定线成型率(locked train comp fp≥1.00 帧占比)≥ 基线且方向向上;`post_sell_held` 分键显著下降(转型臂通道复活)。
- **G3 不劣门**:avg_final_hp / hp_ge_60 / battle_losses_le_2 同池同种子噪声带内不劣(单侧劣化超带 = 回炉查因,禁带病上实机)。
- **G4 r288 复发门·部署通道**:锁定列车冲突语境轮的「轮间 roster diff 仙舟全羁绊件离场事件数」≤ 基线 + 噪声。派生口径(账本已可计算形态,零账本字段新增)= 相邻两轮账本行 `state.deployed/bench` 逐件 char_id 集合做差,差集中消失名 ∈ 仙舟全羁绊件(CHARACTERS 查表 factions+flows 含仙舟);语境筛选 = 该行 `v3_intention.locked_comp` 可解析 ∧ `form_tiers['列车同行'] > RECIPE_FLOOR_TRAIN_CAP`。通道合并计(离场即计的门语义;SellBench 行有名可作通道分键)。批统计工具侧扩展 = G4 派生指标落 `skills/sr-od-currency-war-dev/scripts/cw_batch_stats.py`(现仅消费 cw4_counters 聚合),**该工具行不在本批代码文件面,候 A/B 批落**。(候补批留痕:G4 工具已随候补批——shop.py 预检接线批,进度账本 T-86——落地,派生口径 = 本节预注册原文,通道分键读账本转录顶层 name;判据运行仍候 A/B 批。)
- **G5 r288 复发门·换血通道**:①锁定线帧 `swap_arm_transition_trigger` 批增量 > 0(转型臂复活确认;轮级 join 口径:行 `v3_intention.locked_comp` 解析为列车冲突 comp ∧ 该行 obs.cw4_counters 含该键增量——键为局级聚合,无帧级锁定属性,按轮级 join 判读);②`engines_guard` 拒因在案(守恒门 =「拆成型引擎」形态被拦的守恒证据)。原「仙舟件经 swap 1★ 离场计数」判据删除(sim 不建模执行侧 swap 卖出,恒真不可测),移 G6 判据 3′。
- **G6 执行面(sim 结构性不可见,实机验证)**:`deploy_zero_place_breaker` 缺陷计数不升;部署 round_fail 帧不增;`deploy_exec_r288_skip_ctx_open/closed` 可归因;**3′** 锁定线帧仙舟全羁绊件经 swap 卖出离场事件 ≤ 基线 + 噪声(实机对局档案派生;实机辅助锚 = `deploy_swap_no_victim` 显影键;**基线样本源候实机批指认**——阈值结构已预注册,基线源指认是执行细节,不阻塞判据线先 commit)。

## 7. 挂账与占位裁决(含期限条目)

- **P1 配方锁帧不豁免(占位裁决,登记 + 期限)**:本设计下 P1 框架帧(P1 配方锁/桥对)`locked_comp` 恒空(ADR-0357)→ 条件(1) 恒 False → 天然不豁免,零代码。框架列车目标 4 vs 封顶 2 的同型冲突在 P1 亦存在,过渡纪律最值钱期不豁免是合理缺省——但此为**占位裁决非终局**,登记重裁期限:**实机连续 3 局再现 P1 同形卡点(框架锁线帧列车 core 恒拦致部署真空),或下一策略迭代收口评审时,以先到者为准必须重裁**(升格需先解 p1_pair 语境的目标档来源,非本批参数可表达);禁无限期悬置。
- **数据依赖声明**(豁免条件(2) 谓词完备性):依赖注册表现状「**仙舟羁绊件主阵营恒=仙舟**」(cw_chars 9/9)。当前该事实与门交互自洽:仙舟 ∈ RECIPE_FACTIONS ⊂ DEPLOY_FENCE → 主阵营仙舟件恒不被散牌围栏拦;board 仙舟档≥1 ⟺ 供给件成对 → 不被 rest_capacity 拦。**未来入表「flows 含仙舟 ∧ 主阵营 ∉ RECIPE_FACTIONS」的件**:锁定列车线帧 board_recipe=4<RECIPE_BASE(recipe_starved 恒真),vacancy≤2 帧该件被围栏/rest_capacity 拦住上不了场、却仍被判有效供给 → 豁免闭合 → 列车 core 恒拦 = 死供给第四类换形复发。处置:不预扩谓词(为不存在角色扩防是过度设计);**入表复核义务 = 凡新增仙舟羁绊件,核对其主阵营取值**(条件④实现注释点名围栏/成对门交互)。
- **常量挂账关联**:`RECIPE_FLOOR_TRAIN_CAP`/`RECIPE_FLOOR_XZ_BASE` 派生自 `TRANSITION_TRAITS` 副本,该副本带迁移挂账(cw_deploy_logic 头部注释;权威副本 = knowledge/cw_engine_facts.TRANSITION_TRAITS,按 legacy cleanup 计划随文件删除)——新常量属既有消费方向的模块级化(cw_intention 本就 import TRANSITION_TRAITS,非新增消费方文件),**副本迁移执行时本常量须随迁,禁留断链**。
- **G4 派生工具**:已随候补批(shop.py 预检接线批,T-86)落地——`cw_batch_stats.py` G4 派生指标,口径 = §6 G4 预注册原文;A/B 判据运行仍候实机批。**G6 判据 3′ 基线源指认**:候 A/B 实机批指认,不在本批代码面。
- **shop.py 两处 `can_deploy_single` 预检接线义务(v3 §1.6.5)候补批**:已由候补批(T-86)接线——出口③/T5 两调用位按本条形态补 `recipe_floor_lock_exempt` keyword(try/fail-closed 同 mandate `_deployable` 形态),接线锁与红证在测试仓 `test_cw_exit3_fuel_filler`/`test_cw_t5_unlocked_transition`。本条其余留痕(未接线理由)保留作裁决记录。

## 8. 引用勘误(随批修)

「deploy 围栏锁定键放行」是 ADR-0360 **决策件 3**(件 4 = 提案去重/退避)。本批修正三处误引:`cw_deploy_logic.py` select_deployments docstring、围栏放行 inline 注释、`engine_p1.py` 围栏装配注释——均「件4」→「件3」;新 ADR 与新注释一律用正确编号。
