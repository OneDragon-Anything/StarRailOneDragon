# W607 · 词缀消费面设计件(B4 收敛:环境词缀判据 + 库藏生锈消费 + opening hold 收窄;零改动第一段)

> 类名已随 2026-09-03 命名迁移更替,对照 NAMING.md(本文为带日期预登记设计记录,类名保持当时事实,未改)。

> 任务:统一设计「词缀/环境信息消费面」——①词条→策略钩子的信息流 ②三病灶修法(锁线环境判据/生锈穿戴加权/hold 收窄)及相互关系 ③效果判据(过程量) ④测试计划 ⑤与 W606 批③(适配器/开关)的时序。
> 纪律:本批**零改动**(未碰 src/ 与 sr-od-test/);产物仅本文件(增量写)。
> 结论合格线:词条语义全部引 docs 调研(文件:行);修法标定进 decision_v2 registry,不拍死值。
> 文件面:禁碰在飞面(W606:default_strategy/decision_v2/prep_director;W603 刚落:telemetry/observe/strategy)——本设计的落点标注均以此为约束。

---

## 0. 同根诊断:三个病灶是同一消费面缺口的三个投影

W586 复盘 B4 已定性:「词缀是简报三读数里唯一零消费的读数」(w586_formal_review/REPORT.md B4 节)。把三个病灶并排看,缺口形状一致——**敌方/环境信息进了 state,但不进决策**:

| 病灶 | 信息(已在 state) | 该进的决策 | 现状 |
|---|---|---|---|
| ① 局22 锁「万敌单C」但当局无万敌环境(W570r §2.3;W586 B4 勘误候选:简报行含 忍无可忍,词缀清单两源不一致待复核——不影响「判据缺位」这一结构性结论) | `state.enemy_affixes`(cw_state.py:199) | **选线/锁线资格** | `_direct_line_qualified`(cw_intention.py:320-335)只查投资策略/环境两张亲和表,词缀零参与 |
| ② owned 滞留装备喂敌(competitors.md:45:每件未穿 → 敌伤 +3%/己伤 −4%,上限 10 件) | 词缀表中「库藏生锈」语义(affix_effects_data 注册表) | **囤积/保留权重 + 穿戴执行优先级** | 策略不读该词条;穿戴优先级无「生锈在场→优先清库存」分支 |
| ③ r1-r2 装备 hold 在有战斗轮时白板挨打(W593 §2.2 闸门①) | `state.node_type`(cw_state.py:138)+ 节点序列台账(cw_state.py:1626 `ledger_node_type`) | **opening hold 辖域** | hold 判据只看 `round_num <= 2`(equip_all.py:381),不看该轮是否战斗节点 |

**统一判断**:三个修法共享同一条信息管道(敌词缀/节点类型 → 决策钩子),应按「一条管道、三个消费钩子」设计,而不是三件独立补丁——这正是根源两问的「跨件半问」结论(W586 B1 与 B4 同局叠加已经示范过:词条惩罚与行为病灶同局互喂)。

---

## 1. 词条→策略钩子的信息流设计(读哪/何时读/进哪个决策)

### 1.1 现有读数面(不新建读取,只补消费)

词缀的**读取链已完备**且经 W586 G1 验证(HarandleBriefing 运行时采集 + LCS 清洗 + 歧义 None 留证):

- 写入端:`ctx.cw_briefing_affixes` → `session.briefing_affixes`(battle_loop.py:210-213 / takeover_collect_plane_intel.py:146-147,仅空时写)→ `state.enemy_affixes`(default_strategy.py:203-206 注入;cw_observation.py:1830-1831 同步)。
- 现有唯一消费:`mechanics_fit`(cw_comps.py:1150-1168,经 `AFFIX_MECHANIC_MAP` 归一为机制 tag,comp_score 评分项)与遭遇选项打分(cw_events.py:87 `decide_event` 的机制克制惩罚,ADR-0203)——**全是「comp 评分/选项评分」面,没有「资格/权重/辖域」面**。这就是消费面缺口的准确定位:词缀只被当作软信号(分数),从未被当作硬判据(资格门)或执行权重。

### 1.2 管道设计:每决策帧一次的派生环境快照(O(1) 预计算)

**新增一个派生量,不新建读取**:`EnvAffixContext`(纯函数,输入 `state.enemy_affixes` + `state.node_type`,输出两个派生集):

1. `mech_set: set[str]` — 词缀 → `AFFIX_MECHANIC_MAP` 机制 tag 集(已有同构实现: ScoreContext.mechanics,cw_comps.py:1272-1273,未知词缀原样透传);
2. `rust_count: int` — 库藏生锈在场的 owned 未穿计件面(数量语义见 §3.2;游戏上限 10 件,competitors.md:45)。

计算时机:每帧决策入口(update_target / 步级 decision)各算一次,帧内全钩子共享——决策热路径总成本 = 词缀数 × 查表,O(词缀数) 且每帧只算一遍;各钩子消费 O(1) 集合判定。符合热路径约束。

**「当前/将遇」语义**:判据消费 `state.enemy_affixes`(当前位面词缀);W586 B4 的简报归属滞后修复(W576 移交④)落地前,该字段在位面切换窗口可能滞后一位面——判据必须带「词缀可信位」守卫(字段空/未更新时判据返 None=信息缺失,走动态权重剔除语义,ADR-0107 同款),**不猜**。

### 1.3 三个消费钩子(信息流向总表)

| 钩子 | 读 | 进哪个决策 | 修法节 |
|---|---|---|---|
| H1 锁线环境判据 | `mech_set` | 选线/锁线资格(`update_intention` 链) | §3.1 |
| H2 生锈穿戴加权 | `rust_count`(词条在场布尔) | ①囤积/卖出保留权重(decision_v2 sell/hold 评分) ②穿戴执行优先级(equip_all) | §3.2 |
| H3 hold 收窄 | `node_type`(经 `ledger_node_type` 查表) | opening hold 辖域(equip_all) | §3.3 |

H2 与 H3 同属「装备持有价值」消费面(§3.4 关系);H1 独立于装备面,但与 H2/H3 共用 §1.2 的派生快照。

---

## 2. 词条语义底账(全部引 docs 调研,零猜测)

| 词条/环境语义 | 出处 | 对设计的作用 |
|---|---|---|
| 库藏生锈:备战席每 1 件未穿装备 → 敌方造成伤害 +3%、受到伤害 −4%,最多计 10 件;克攒装备不穿的囤积打法,利即时合成穿戴满装备 comp | docs/game/currency_war/data/competitors.md:45(2026-08-28 游戏内实采 `affix_effects_data`,证据级=游戏内 OCR 实采) | H2 的数量语义与方向(惩罚随件数线性、上限 10) |
| 忍无可忍:敌受 7 次攻击后提前 100%(敌方多动类) | competitors.md:68 | 万敌强环境集成员;W586 B4 勘误候选的争议词条 |
| 万敌启用环境(强)= 敌方多动/反伤类词条:正当防卫、忍无可忍、应激反应、一鼓作气、灼热轰炸(成型后)、反伤类;**环境不满足时该线选线降权不选**;「这不是对『早上累积型』例外的取消——例外只在已选该线且环境成立时才生效」 | docs/game/currency_war/research/final_comps/accumulator_family.md:98,103-104(万敌篇词条矩阵,证据高) | H1 的强环境集单一源;「降权不选」语义 = H1 挂资格门而非砍部署例外 |
| 「启用环境成立:当前/将遇敌方词缀 ∈ 该成员的强环境集」(累积型部署豁免的形式化前提②) | accumulator_family.md:118-143(§4.2 设计**未实现**,归后续策略批) | H1 的判据形式已有成文形式化,本设计引用而非另造 |
| 全局累积型角色「越早越好……但这类阵容需特定环境(万敌需敌方多动类词条)才强,**无环境不选**」 | docs/game/currency_war/research/user_playstyle.md:108-111([21] 例外,2026-08-26 用户定谒原文) | H1 的口述权威源(最高证据级) |
| 词条矩阵是开局前置决策:正吃(反震/万敌吃敌方多动类)与硬 counter——**读词条决定开哪条线** | docs/game/currency_war/research/final_comps/README.md:165-167(D3) | 「词缀→选线」是玩法共识层,非本项目发明 |
| 词条×骨架互动:忍无可忍/应激反应/同步行动/一鼓作气 大幅增强前期 2DOT(怪频动→DOT 多触发) | docs/game/currency_war/research/transitions.md:20 | H1 的可扩展面(过渡线环境判据二期);本批不辖 |
| 开局词缀规避:词缀与 comp 是双向选择,bot 不重开,已见词缀作 comp 评分输入 | docs/game/currency_war/research/plaza_methodology.md:103-105(M15) | 辖域声明:bot 不重开,H1 只辖「局中选线」,不辖重开 |
| W586 B4:enemy_affixes 字段已知恒空、briefing 存证行有人写无人读 | w586_formal_review/REPORT.md B4 | 词缀可信位守卫的必要性(§1.2);注:W603 后 default_strategy 已接 briefing→state 注入(default_strategy.py:203-206),「恒空」指 state 字段在旧局的历史观测,接线现状以代码为准 |

**边界声明**:各 final_comps 单篇的 counter 词条(如 银狼怕 正当防卫/能量逃逸/时间刺客,final_yinlang_joy.md:76)属「硬 counter 避线」语义,与 H1 的「强环境要线」是同一判据的双向(正吃/反吃);本批 H1 先辖**累积型线的正吃面**(accumulator_family §3 表),反吃面(避线降权)已有 mechanics_fit 软信号覆盖,是否升硬门挂二期,不摊大本批。

---

## 3. 三修法

### 3.1 H1 锁线环境判据(病灶①)

**判据**(派生,不手写线名——沿用 ADR-0338「派生优于快照」纪律):

```
_line_env_qualified(state, comp) -> bool | None:
  acc = comp.global_accumulators 中类型为 'hp_charge_stack' 的成员   # 字段已落地,accumulator_family.md §4.1
  若 comp 无累积型成员 → None(判据不辖,资格面不变)
  若 state.enemy_affixes 为空(可信位缺失)→ None(§1.2 守卫,动态剔除,不拦)
  否则 → mech_set ∩ 该成员强环境机制集 ≠ ∅
    强环境机制集 = 词缀名清单经 AFFIX_MECHANIC_MAP 归一的机制 tag 集,
    词条名单单一源 = accumulator_family.md:98 表(进代码注册表同层,
    与 MECHANIC_SYNERGIES 并列新增 STRONG_ENV_MECHS 映射,允许部分成员
    环境非词缀型如 银狼升费链——该成员不进本映射,判据自然不辖)
```

**挂闸点**:消费点 = 锁线资格链,两处:

1. `_p1_gate_blocks`(cw_intention.py:373-385)的资格源扩展:非过渡线且 `_line_env_qualified() is False` → P1 拦(现状只查两张亲和表);
2. **P2/P3 直通锁线点**(病灶①的实际发生地——局22 是 P2 r1 经③核心卡锁万敌单C,由 `_direct_line_qualified` 之外的核心卡路径进线,[23] 合法):累积型线在环境缺失时的锁线由「可锁」改「锁线降权/缓锁」——具体实现为 `update_intention`(cw_intention.py:780 起,registry 注入点已存在)对目标候选加环境降权项。**不砍③锁线路径本身**(accumulator_family.md:104:例外只在已选且环境成立时生效,反向同理——环境不成立只是不**主动选**,不是没收已锁线;已锁线的处置=缓锁重评,归换线既有通道判,不新增通道)。

**标定进 registry**(decision_v2/registry,不拍死值):`line_env_gate_enabled`(开关)、`line_env_lock_penalty`(环境缺失时锁线降权量级)、`line_env_lock_min_round`(缓锁前最小观察轮,防 r1 词缀窗口误判)。开关生命周期:行为输入(enemy_affixes 注入链)已就绪,但 W586 B4 的简报归属滞后未修前可信位有缺口——**开臂判据挂账**:简报归属修复落地 + sim A/B 双臂过,才默认开;在此之前默认关并在 registry 注释写明挂账,符合「策略开关的生命周期」门(非悬置:开臂条件具体可判)。

### 3.2 H2 库藏生锈消费(病灶②)

**数量语义**(competitors.md:45):惩罚 = 每件 owned 未穿装备 → 敌 +3% 伤/−4% 受伤,计件上限 10。策略侧不需要复刻游戏精确数值,只需要**方向正确的边际惩罚**——每多滞留一件,清库存的期望收益单调上升。

**两个消费点**:

1. **囤积/保留权重(decision_v2)**:词条在场时,owned 未穿装备(含穿在 bench 角色身上但未上场?否——语义是备战席物品栏未穿戴,即 owned 区滞留件,W593 §一已定谳)的保留价值扣减一项,量级随滞留件数线性、按游戏上限截断。落点 = sell_priority / hold value 评分(decision_v2/scoring.py 的持有域权重 + remediation 卖出优先序),进 registry:`rust_hoard_penalty_per_equip`(每件扣减量级,标定候选)、`rust_hoard_penalty_cap`(截断,标注=游戏机制上限 10,这是**引文档实采值**非拍脑袋)。
2. **穿戴执行优先级(equip_all)**:词条在场 → 非工具可穿件全部进入穿戴池并置于 hold 判据之前(即 §3.3 的 hold 对「生锈在场」豁免)。落点 = equip_all 的 `_transition_hold_active` 判据输入追加一项;equip_all 不在 W606 文件面内,可独立排期。

**注意不做过头**:库藏生锈只惩罚「滞留」,不惩罚「为合成链预留的材料件」——穿戴即合成的路径(equipment_mechanics.md §1,穿着即合成)不受影响,因为合成件穿上后即退出 owned 计件。装备分配器本身的质量(W586 B1 的分配一致性)是另一件,不并入本设计。

### 3.3 H3 opening hold 收窄(病灶③)

**现状**:hold 判据 `round_num <= 2`(equip_all.py:378-384,r388/ADR-0257)。by-design 前提 = r1-r2 是奖励轮无战斗——局22 r2 StartBattle 实证前提只对 r1 成立(W593 §2.2 闸门①)。

**修法**:hold 辖域从「r≤2」收窄为「r≤2 **且当前节点非战斗类**」。节点类型真值 = `state.node_type`(顶部标签 OCR,cw_state.py:138)+ 节点序列台账回查 `ledger_node_type(session, plane, round)`(cw_state.py:1626,位面详情采集/备战节点行双写端,已存在)——查表 O(1)。战斗类节点集(battle/boss/encounter/精英)进 registry:`opening_hold_battle_nodes`(节点类型名单,与节点 reader 词汇表同源,非新造)。台账缺失(None)时**维持现状 hold**(保守侧:不因观察缺失而改变既有行为,宁缺勿错同款)。

**标定进 registry**:`opening_hold_battle_gate_enabled`(开关)。此修与 §3.2.2 强耦合(见 §3.4),建议同批落地同批 A/B。

### 3.4 三修法的相互关系

- **H2② 与 H3 是同一判据的两面**:hold 收窄定义「什么时候必须穿」,生锈豁免定义「有词条时更必须穿」。合并为一个谓词:`_wear_now_required(state) = (非 opening hold) or (rust 在场) or (key_equips 命中既有规则)`——一个函数一处测试,避免两个布尔在 equip_all 里散装与门。
- **H1 独立于装备面**,但三者共享 §1.2 派生快照与「可信位守卫→None 动态剔除」范式——这是本设计件真正的「统一」:不是三个补丁,是一条信息管道 + 一个守卫范式 + 三个消费钩子。
- **互不阻塞**:H1 可独立先行(见 §6 时序),H2/H3 成对落地。

---

## 4. 效果判据(过程量;禁 HP 主门,P17 立法口径)

| 钩子 | 过程量 | 目标方向 | 观测面 |
|---|---|---|---|
| H1 | 累积型线锁线帧中「环境缺失」帧数 | =0(判据生效后) | 遥测 target/intention 帧 + 判据命中 reasons(新增 reasons 字段,判读可归因) |
| H1 | 选线分布:万敌线出现局中 `enemy_affixes ∈ 强环境集` 命中率 | 100%(含「词缀可信位缺失→判 None 不锁」的显式豁免行) | 同上 + outcomes.enemy_affixes 快照(cw_telemetry.py:319 已有) |
| H2 | 带词条局 anomalies「滞留≥3 件跨 2 轮」行数(W593 ④已立的实机锚点) | =0 | anomalies 视图(已有通道) |
| H2 | 平均 owned 滞留件数(带词条局 vs 无词条局 对照) | 带词条局显著更低 |EquipAll owned 快照(cw session.last_owned_equips 已有,equip_all.py:456) |
| H3 | 有战斗节点的 r2 局中 worn>0 帧占比 | 从 0(局22 形态)升到>0 | decisions 帧 deployed 装备计数(W586 装备维差分口径) |
| H3 | hold 触发帧的 node_type 分布 | 仅「奖励/无战斗」类 | equip_all log 的 hold 行追加 node_type 字段(一行 log 改动,非热路径) |

---

## 5. 测试计划

**L1 单测(纯函数,零实机依赖)**:

1. H1 判据四态:无累积成员→None / 词缀空→None(可信位守卫) / 环境命中→True / 环境缺失→False;OCR 形变词缀经 AFFIX_MECHANIC_MAP 归一路径各一例。
2. H2 权重三态:词条不在场零扰动 / 在场线性扣减 / 上限截断;与合成链预留件不冲突(材料件不扣)一例。
3. H3 判据四态:战斗节点不 hold / 非战斗节点 hold / 台账 None 维持现状 hold / key_equips 命中照穿(既有规则不被收窄误伤)。
4. 谓词组合 `_wear_now_required` 真值表全覆盖(防两布尔散装与门的漏支)。
5. registry 新字段缺省值路径:开关全关 = 与现状逐位同行为(回归守卫,仿 W606 DirectorV2 分支先例)。

**L2 sim A/B(挂 sim-testing §3 武器库)**:

- H2+H3 合并一臂(rust 消费+hold 收窄 vs 现状),n≥100 双窗,出口=穿戴率@r2、key_equips 命中(p1_key_hit 方向)、滞留件数、合成触发次数(W593 ④的 sim 出口清单直接沿用)。
- H1 单独一臂,出口=选线分布(万敌线仅在强环境局出现)+ 环境缺失局锁线帧数。
- sim 侧注意:词缀注入需在 sim 场景生成器带 enemy_affixes 维度(现 sim 可能无词缀场景——实现批第一动作先核实,若无则 H1 的 sim 臂需先补场景注入,属 sim 基建小件)。

**L3 实机判读锚点**:§4 表逐行进局后判读 checklist;首局必带「H1 reasons 字段非空」锚点(仿 W586 问1「血线内停手证据>0」的锚点纪律)。

---

## 6. 与 W606 批③(适配器/开关)的时序关系

**现状约束**:W606 在飞面 = default_strategy / decision_v2 / prep_director(prep_director.py:1909 的 DirectorV2 开关分支,默认关);批③ = 适配器/开关收口。本设计三个钩子的落点与之相交情况:

| 钩子 | 落点文件 | 与 W606 文件面相交 |
|---|---|---|
| H1 | cw_intention.py + decision_v2/registry(新字段) | registry 相交(批③动 registry/adapter);cw_intention 本身不相交 |
| H2① | decision_v2/scoring + remediation + registry | **相交**(decision_v2 是 W606 主战场) |
| H2② + H3 | operations/prep/equip_all.py | 不相交 |

**建议时序**:

1. **H1 先行(批③合并前或并行均可)**:cw_intention 单文件 + registry 新增字段段(追加型,与批③的 registry 改动不同字段无冲突;若批③正在大改 registry 结构,则等批③合并后追加,合并冲突成本最低)。前置依赖=W586 B4 简报归属滞后修复(词缀可信位),该项在 W576 移交清单④,若未落地则 H1 以默认关进码、开臂判据挂账(§3.1)。
2. **H2① 等批③合并后**:decision_v2 评分/卖出面是批③主战场,在其上叠权重项必然踩在飞 diff——排队后落,避免双臂并行改同一评分管道。
3. **H2②+H3(equip_all 侧)随时可落**:不在任何在飞文件面,且是三修法中证据最实、行为面最小的(W593 ①②③同款「防复发」级),可与 H1 同批先行。

一句话:**能先行的(H1+H2②/H3)不与批③抢文件,必须排队的(H2①)排批③后**——时序由文件面冲突决定,不由重要性决定。

---

## 7. 盲区与移交

1. **局22 词缀清单两源不一致未定谳**(W586 B4:简报行含 忍无可忍 vs W570r 所引源无):本设计不依赖该定谳(判据缺位是结构性的,清单真假都拦不住「无判据」);定谳归 W576 移交④修复批。
2. **强环境集的机制 tag 映射缺口**:accumulator_family.md:98 的词缀名单是**名字级**,AFFIX_MECHANIC_MAP 是**名字→机制 tag**映射——「反伤类」等类目词到具体词缀名的展开需实现批对照 affix_effects_data 注册表逐个核实,缺映射的词缀按「不命中」处理(宁缺勿错,不猜)。
3. **sim 词缀场景维度有无未核实**(§5 L2 已标注为实现批第一动作)。
4. 本批零改动,三钩子均未实现;实现批的任务书应引用本文件 §3(修法)+ §5(测试)+ §6(时序),数值全部走 registry 标定通道。

---

## 8. 第二波增补 · H2① 消费面几何核查与数学裁决(W606 合并后)

§3.2.1 原预设「囤积/保留权重落 decision_v2 评分/卖出面」。第二波开工核查**否决该落点**:

1. decision_v2 卖出面全部通道(`sell_priority_key` 族)操作对象是 `BenchChar`,装备无卖出动作面;`score_state` 加装备项=对候选排序的常数项(买/卖/上角色动作均不改 `state.equips`)=死项。
2. 获取面(补给 `decide_supply`/巨星策划 `decide_planner`)数学无翻转点:每件滞留金当量 = 0.03 × expected_battle_loss(10) × battles_left_est(5) × hp_to_gold(0.5) = **0.75**(保守=只建模敌伤面,−4% 减伤面无损耗模型映射=不猜),封顶 10 件=7.5;补给面 key_fit 边际 10 > 7.5 恒先、非 key 件间同额平移序不变;策划面装备类扣后上界 13.5 < 升费 40/弱化 55。

**裁决 = 行为分支不合入**(验证纪律兑换三选一之「确认无效→不合入」);账面单一源落 registry 数据层(`rust_hoard_damage_share`/`rust_hoard_penalty_cap`,无行为分支),证明锁 = `test_cw_w607_h2o_verdict.py`(**锁红即重评触发器**:装备价值表上调/key_fit 下调/滞留份额双向建模/W612 装备处置或 inventory 动作面,任一变动即按公式重算重裁)。滞留治理的真消费点 = 执行层 H2②(穿上即退出计件,第一波已落),获取面重复计罚无增量。完整推导与局24 判读清单见 ADR-0461 增补节。

---

## 附:引用文件清单(本批全部只读)

- docs/game/currency_war/data/competitors.md(词缀语义单一源层)
- docs/game/currency_war/research/final_comps/accumulator_family.md、README.md、final_yinlang_joy.md
- docs/game/currency_war/research/user_playstyle.md、transitions.md、plaza_methodology.md
- docs/game/currency_war/research/equipment_mechanics.md(经 W593 转引)
- .debug/temp/currency_war/w586_formal_review/REPORT.md、w593_equip_wear/DESIGN.md、w570r_planar1_diagnosis/findings.md
- src 侧锚点:cw_intention.py / cw_comps.py / cw_events.py / cw_state.py / cw_telemetry.py / operations/prep/equip_all.py / operations/battle_loop.py / strategies/default_strategy.py / prep_director.py(均为实读定位,未修改)
