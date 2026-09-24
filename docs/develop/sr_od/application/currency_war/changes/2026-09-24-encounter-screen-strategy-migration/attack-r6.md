# 遭遇迁移设计 对抗审查报告(第六轮)

> 攻击对象 = 本目录 design.md / landing.md / README.md 三件(全读)。隔离声明:不读此前轮次报告,全部发现由本轮独立直调得出;每条发现附本轮直调证据(文件:行/直调值)。
> 判据源直调:00_framework.md §1(宪法五/六原文)、01_math_framework.md §6(【拍】章程原文)、04_survival_budget.md §7 裁定表第 9 行、screens/op-layer.md §1.4、proofs/p64-encounter-dstat-static-map-uncalibratable.md(辖域原文)、math_proofs.md 索引 P15/P26/P85 行、P9_VALIDATION.md(存在性)、iteration-design.md、strategy-work.md、项目 AGENTS.md;现役代码逐符号直调(cw_encounter_selection / cw_events / cw_survey19_hooks / cw_difficulty_account / cw_economy / cw_vocab / cw_node_schedule / cw_obs_core / flow / bridge / mandate_v1/encounter.py / audit/provisional.py / cw_strategy / cw_screen_encounter / cw_pick_encounter_action / cw_action_report/pick_encounter / cw_loop / cw_node_obs / cw_game_state / sim/cw_sim_backend / data/cw_equipment_data / tools/cw/gen_equip_registry);测试仓显式 grep(sr-od-test 被 gitignore,常规 grep 不覆盖,已单独直调);全仓消费面 grep 验证;先例批(invest-env/supply)design §1 承接声明。

## 发现清单

### R6-F1 [严重度:高] 边缘白名单/奖励偏好序的合法性载体三处口径互相矛盾,「判据正本已落码结构、本批零新立」断言与现役实址形态不符
- 位置:design §2.2 设计原则段 vs 同节决策序 4「形态申报」vs README「待用户过目/裁定点」
- 发现:同一结构(边缘态可及档)给出两套互斥合法性链——①设计原则段:「判据结构本身(边缘态可及档白名单 {其一, 其二}、钻>装备>金币>末档偏好序)按 **【拍】立场登记形态**入册…过目未过 → 该两项不生效,遭遇选档回落最低档 fail 向」;②决策序 4:「01 §6【拍】字面辖域(加法立场值)不覆盖闸门数字,**本白名单不走【拍】登记**——合法性链 = 原判据正本已落码结构(本批零新立)+ 对抗审查确认载体 + 用户追认候记」;③README:「【拍】立场登记两项:边缘态白名单、奖励偏好序——过目记录 = 落地验收凭据」。①③同口径,②与之矛盾;且两种链的失败语义不同(①过目未过 = 两项不生效回落最低档;②追认候记 = 无失败分支)。直调 01_math_framework.md:168,【拍】原文辖域 = 「登记即立场、分差即偏好强度的加法立场值」,凡「数值大小参与方向/闸门判断」的量归【推】/【拟】纪律——design 自认章程缺口成立,但缺口的补法(按【拍】精神登记 vs 声明不走【拍】)两段各说各话。另外「原判据正本已落码结构(本批零新立)」与实址不符:现役 `cw_encounter_selection.py:417-418` 为数值 cap 闸(`cap = 2 if kappa == '边缘' else 6` + `if t > cap: continue`),不是「离散档位白名单,非数值阈值比较」;同一行代码的另一半(cap=6)在 §2.2 又被承认「实现保留原核 cap=6 = 档位值域上界」保留数值形态——同一结构的两半被分裂成两种合法性类别。最后,【拍】合法性要件 1(01 §6:165「登记表在册:每个【拍】值落策略层立场分表(表只收非零行,每行带裁定理由)」)的载体落点(立场分表)在 design/landing 均无安排——设计只安排了要件 2 的过目载体(定稿呈报)。
- 修正方向:统一为一套链并三件同步——推荐:两项均按「已落码结构沿用 + 定稿呈报用户追认」申报(放弃【拍】登记路径),或均按【拍】登记并补立场分表落点;同步把「白名单非数值阈值比较」改写为「现役 cap 数值闸的语义等价表述(档位值域 1..6 下 t>2 排除 ≡ t∈{1,2})」;明确追认失败分支的回落行为(若采追认链)。

### R6-F2 [严重度:高] 「kernel 真值表下两窗口口径逐位等价」断言为假——P2 首遭遇帧的战斗类窗口会纳入上一位面遭遇行
- 位置:design §2.2 窗口申报段 / §2.10 窗口候选取舍
- 发现:design 断言「kernel 表下两窗口口径逐位等价(每位面至多一次遭遇,遭遇决策帧自身行尚不存在)」并以此为主要依据维持候选 A。直调 `cw_node_schedule.py:28-36`(P1 = 9 节点,encounter@r7;P2 = 7 节点,encounter@r5)+ `cw_encounter_selection.py:106/124-133/162-164`(SettlementRing 跨位面累积、深度 10、补给零行、`last_normal_battles` 按 node_type 过滤):P2 r5 遭遇决策帧时,环内已入 P1 全部结算行(含 r7 遭遇行;P2 r1-r4 后环内 8+3=11 行,旋转淘汰 P1 r1 后仍含 P1 r7 遭遇行)。候选 B(战斗类窗口 = 普战+遭遇)在该帧 = [P1-r7-遭遇, P2-r4-普战],候选 A(普战窗口)= [P2-r2, P2-r4]——**不等价**。括号理由「遭遇决策帧自身行尚不存在」只排除了本位面遭遇行,漏了上一位面遭遇行(P1 遭遇行在 P2 决策帧仍在环内)。P1 首遭遇帧(r7)确等价(此前无遭遇行),等价断言只对 P1 成立。
- 修正方向:改写 §2.2/§2.10 论证为「P1 位面内两口径等价;P2 首遭遇帧不等价(上一位面遭遇行入窗,窗口新鲜度更高);维持候选 A 的独立依据 = 无行为面确证的语义变更不做 + P2 序列两源分歧未定谳」;31 号稿数学挂账的窗口变体触发器评估时纳入跨位面遭遇行入窗面(方向核查:遭遇败局入窗使 κ_S 降档 = 反应提前,宪法三合法方向,与 design 既有变体论证自洽)。

### R6-F3 [严重度:中] landing 3.2 完成判据②「全仓词边界 grep 零命中 EncounterPick」按字面不可执行——changes/ 历史文档与本迭代文档裸名恒在
- 位置:landing.md 3.2 完成判据②
- 发现:直调全仓 grep `EncounterPick`(docs 面命中 56 处):裸类名大量存在于 `changes/2026-09-14-unified-action-factory/design.md:255`、`changes/2026-09-16-strategy-terminal-contract/`(design/attack 多处)、`changes/2026-09-16-strategy-input-unification/`、`changes/2026-09-18-action-op-reorg/design.md:72`,以及本迭代 design.md/landing.md 自身——3.2 时点正本更新(3.3)未执行、changes/ 按规范不定期清理且不属于本批收口面,「全仓零命中」按字面在 3.2 时点必红。判据意图显然是代码面(src + sr-od-test),但字面不可满足 = worker 卡验收或自行放宽口径(机械跟绿通道)。
- 修正方向:判据②限定为「src/ 与 sr-od-test/ 代码面词边界 grep 零命中」(EV 核保留分支沿用既有括注语义),或逐文件点名。

### R6-F4 [严重度:中] design §2.5 同节先说「op 层零行为改动(仅注释收口)」后说「防线随批落(op 层一处行为改动)」——旧口径段未随定稿收口
- 位置:design §2.5 第二段 vs 第三段
- 发现:第二段:「op 侧重调路径…重调同输入同输出(纯函数)→ 仍返 Suggestion → **零点击终结交回,op 层零行为改动(仅注释收口,§2.8)**」;第三段:「**处置 = 防线随批落(op 层一处行为改动)**:…重调仍返 Suggestion ∧ 刷新锚读缺 → `round_fail` 交回…**其余 op 层零行为改动**」。landing 3.2 已采纳防线版(「替换现『零点击 round_success 交回』」),但 §2.5 第二段完整陈述了与最终设计相反的行为语义且未改写——同一节内两段对同一重调出口给出互斥结论,违反 iteration-design 写作硬规则 4(修订后全量同步复查)。
- 修正方向:第二段「零点击终结交回,op 层零行为改动」句改写为指向第三段防线(「仍返 Suggestion → 落防线,见下」),删去「op 层零行为改动」表述。

### R6-F5 [严重度:中] `REWARD_TIER_LAST`(第五个模块级公开符号)未入迁移清单/删除清单/零残留 grep 集
- 位置:design §2.7 cw_encounter_selection 删除/迁出面;landing 3.1 范围②、3.2 完成判据①
- 发现:直调 `cw_encounter_selection.py:253` `REWARD_TIER_LAST = _REWARD_TIER_UNMAPPED`——模块级公开别名(无下划线前缀),全仓 grep 仅此一处定义、零外部消费。design §2.7 迁出清单只写「`reward_tier` 与四档常量」(即 `_REWARD_TIER_DIAMOND/_EQUIP/_GOLD/_UNMAPPED`,:247-250),landing 3.1 同措辞,3.2 零残留 grep 集(14 符号)亦无此符号。落地时 ruff 对模块级变量不报错,该符号将无申报地滞留 kernel 或随 `_REWARD_TIER_UNMAPPED` 迁移而断链(NameError)。
- 修正方向:§2.7 与 landing 3.1 补 `REWARD_TIER_LAST`(随迁或直接删除——零消费,推荐删除);3.2 判据①旧址零残留集补该符号。

### R6-F6 [严重度:中] kernel 保留面两个符号的孤儿态未申报:`game_start_reset` 现态全仓零调用、`selection_state_of` 判据迁出后零消费
- 位置:design §2.1 kernel 保留面清单
- 发现:直调全仓(src + 测试仓)grep——`game_start_reset`(cw_encounter_selection.py:206)**零调用方**,其 docstring「RunLoop handle_init 或首结算时调」与实现不符(环/经验表生命周期实际由 `cw_game_state.py:2132/2135` 字段 `default_factory` 与 `record_settlement_row` residual 臂承担);`selection_state_of`(:201)唯一消费 = 被迁的 `decide_encounter`(:389),迁移后零消费。design 把两者列进「结算观测持久化基建」保留面却未申报孤儿态;同稿 §2.7 对 `cw_difficulty_account` 明确做了「孤儿态登记,物理删除归后续清理批」的申报——同类情形处置不对称,「保留面」叙述对 `game_start_reset` 含虚构的被调契约。
- 修正方向:§2.1 或 §2.7 补两条孤儿申报(存量零调用 + 迁出后零消费),各给处置:保留须写明理由(如「E-3 标定批/未来写端预留」),否则归后续清理批;`game_start_reset` docstring 的被调声明一并收口。

### R6-F7 [严重度:低] §2.6 消费面「全列(直调核实)」漏列 EV 核 `encounter.py` 的 `EncounterPick` 顶层运行时依赖
- 位置:design §2.6 消费面清单
- 发现:直调 `mandate_v1/encounter.py:79-82`(顶层运行时 import)+ :264/:268/:280/:306/:308/:387(六处签名注解/构造)+ :67(docstring 字样)——`EncounterPick` 的真实消费方。§2.6 清单六项(cw_encounter_selection/bridge/动作链/test_cw_unified_action_4/cw_events/cw_vocab)不含 encounter.py;该依赖在 §2.7/§2.10 与 landing 3.2 有完整覆盖,施工不会漏,但「消费面全列」的声明失实,单读 §2.6 的实现者会得到不完备消费面图像。
- 修正方向:§2.6 清单补 encounter.py 一项并标注「处置随裁定点 1,见 §2.7」。

### R6-F8 [严重度:低] §2.7 注释收口清单自称「已知点全列」但漏 `cw_survey19_hooks` 模块 docstring 的 P9 遭遇叙述
- 位置:design §2.7 注释指针收口清单
- 发现:直调 `cw_survey19_hooks.py:1-11`——模块 docstring 首行「二轮扫描落地件:P9 遭遇接难度账本 + P1 狼狩穿戴纪律」及第 7 行「P9:难度增减的场合依赖…进遭遇档位选择」描述的函数(`encounter_tier_score`)在本批删除,叙述随之失效;该文件在 landing 3.2 文件面内,但 §2.7 收口清单(「已知点全列」)未列此 docstring,仅靠「末阶段全仓复扫兜底」。
- 修正方向:收口清单补 `cw_survey19_hooks` 模块 docstring(P9 句随 `encounter_tier_score` 删除收口)。

### R6-F9 [严重度:低] 决策序编号步骤缺「窗口不足帧」刷新臂的显式步骤,行为需从因词枚举反推
- 位置:design §2.2 决策序 1-7
- 发现:步骤 1 只定「<2 行 → 窗口不足(独立态…)」,步骤 3 刷新阀只挂 κ「不足」,步骤 5 只挂「足量/边缘态…排除」——窗口不足帧的完整行为(可刷 → `refresh-valve:window-insufficient`;不可刷 → `dark-fallback:window-insufficient`)在编号步骤中无落点,仅由因词封闭枚举段与步骤 7 的「reason 带窗口/κ 诊断」间接承载;现役核为显式分支(`cw_encounter_selection.py:390-397`,窗口检查先于 κ 计算短路)。信息齐备、拼合唯一,不阻塞施工,但决策序自称「与现役核同构,门序收窄」,编号清单少了现役核的第一短路臂。
- 修正方向:决策序补一步显式写窗口不足帧两臂(或并进步骤 3 并改写其主语为「窗口不足/κ不足」)。

### R6-F10 [严重度:低] 对 economy.md §10.2 证据状态的转述失真(「其中一帧标注待复核」)
- 位置:design §2.2 窗口申报段
- 发现:直调 `economy.md:133`——P2 行证据格 =「2-1 开局帧读全(1 帧;待多局复核)」,即**整行**仅 1 帧开局读数、整行待多局复核;design 写「双遭遇(r3/r5,其中一帧标注待复核)」易读成两遭遇帧之一待复核。另两源分歧不止遭遇位:economy 表 P2 r3=encounter/r4=reward vs kernel 表 P2 r3=supply/r4=battle(`cw_node_schedule.py:34-36`),错位是结构性的。「两源冲突未定谳」的结论不受影响。
- 修正方向:如实转述为「该行仅 1 帧开局读数、整行待多局复核,且与 kernel 表在 r3-r5 多位错位」。

### R6-F11 [严重度:低] 31 号稿「判据语义 = 本设计 §2.2–§2.5」与正本 as-built 数值纪律的转写义务无提示
- 位置:design §2.9
- 发现:AGENTS.md §9「设计正文 as-built 无状态:数值/权重/阈值只写常量名(单一源在代码)」;§2.2–§2.5 含「白名单{其一,其二}」「cap=6」「窗口 2 行」「阈值 0.5」等数值表述。31 号稿若按「= §2.2–§2.5」照抄入正本即违 as-built 纪律,需转写为结构语义 + 常量名;design 未提示该转写义务。
- 修正方向:§2.9 补一句「31 号稿判据节按 as-built 纪律转写:结构语义 + 常量名,数值单一源 = `encounter_pick.py`」。

## 零发现面申报

以下面本轮实际攻击且无发现(证据均为直调):

- **数值/口径直调复算(全对)**:六标定槽字面全 None(cw_encounter_selection.py:47-64);cap=2/6、窗口 `last_normal_battles(2)`、`_FILL_EDGE_THRESHOLD=0.5`(:285)、四档序数 0..3(:247-253)、`SETTLEMENT_RING_DEPTH=10`(:106);`ENCOUNTER_TIER_COUNT=4` 与占位文本 `金+20(占位,…)` 不含「金币」字面(sim/cw_sim_backend.py:488-491/535-539,与 §2.12 申报逐位一致,sim `refresh_left=None`:1378);`DIAMOND_EQUIP_NAMES={'红钻','蓝钻','财富宝钻'}`(cw_node_obs.py:216);`_CN_NUM` 六档 + 漏读「一」→1(:29-30/56);P15v2 boss 26.79 vs 普战 10.45(math_proofs.md 索引 P15 行);P26 双挂账(Δp_prep/L_node,索引 P26 行);P85 分键 D_N={遭遇,boss}(索引 P85 行)——与 §2.12 验收线保全申报相符。
- **引文核(逐字)**:04 号稿裁定表第 9 行(:111,授权辖域/「判据正本」指针/2026-09-12 确认)与 §0/§1/§2.9 引用一致;op-layer.md §1.4 剩余语义(:93/:116,None=未观察、读缺跳写);P64 辖域原文(静态 dict 形态,DELTA_T 引申申报的边界 design 已如实标注「非 P64 原文结论」,引申论证经自由项逐项核对成立);01 §6【拍】章程原文(见 F1 的辖域引用本身准确);25 号稿头注 9 项含退役删除注记(:3)+ 拆分先例注记(:4-6)+ §2 表行「装备」残留(:19);13 号稿 :21「双轨」过期描述实址;08 号稿 E3 行三格(:18);strategy-docs/README 导航句「18-30」(:56);combat.md §3 达标制(:38-39);敌人信息浮层入口②形态与「难度分随卡变」(浮层文档 :9/:45);cw_node_schedule P1/P2 表与「两位面均单遭遇」;先例批承接声明(invest-env design §1:18、supply design §1:14/26)。
- **消费面/删除面声明直调**:`encounter_tier_score` 唯一消费 = cw_events `_score`(:129/:145,src+测试仓);`apply_calibration`/`reset_calibration` 全仓零外部引用;`EVENT_PICK_TYPES`/`EventPick` 零外部消费、模块级运行时构造实址(cw_events.py:538-543);EV 核 `decide_encounter_ev` src+测试仓双零消费、「测试仓 EV 核纯函数锁」确认不存在;`flow.py:656/793/807` 现役消费行号逐一命中;`test_cw_unified_action_4.py:28/:259/:278` 命中;`test_cw_obs_arch_event_screens.py:417-420` import 的确为保留面符号(claim_encounter_reward/record_settlement_row);`DifficultyAccount`/`marginal_value` 生产消费面与 §2.7 孤儿申报相符(marginal_value 唯一消费 = encounter_tier_score,DifficultyAccount 零生产调用);`last_normal_battles`/`record_settlement_row` 消费面(唯一生产写端 = cw_screen_battle_wait.py:305/330);bridge 顶层运行时 import EncounterPick(:33-35,TYPE_CHECKING 块在 :53);flow `_require_slot_options` 守卫与 `refresh_used` 预计算实址(:599-602);cw_vocab :715/:906、cw_economy :414、cw_difficulty_account :59、provisional :22-23、supply.py :12 指针句全实址;动作链鸭子消费实址(cw_pick_encounter_action.py:54/67、pick_encounter.py:47-58);`cw_loop.op_fail_redispatch_tick`(:462-482,ok→整窗归零)与 §2.5「零点击 round_success 不计数且清零」定谳一致,防线 round_fail 计入上限的有界收敛论证成立;cw_strategy 依赖矩阵句(:253-255)与接口注(:178-180)实址;cw_game_state 容器字段(settlement_ring:2132/encounter_log:2135/encounter_refresh_left:2161/enemy_difficulty:2126);data/cw_equipment_data.py「生成、勿手改」头注(:3)与三钻无标志字段(:53/64/65)、EQUIPMENT_ROSTER(:233)——§1 症状 4「不迁 data 文件」论证成立;cw_obs_core 为 kernel 手维护读数域文件,宿主选择成立;sim 遭遇决策链(op act 调 strategy.decide_encounter,observe 走 sim 端口)与 §2.12 sim 盲区申报链一致。
- **行为锁实址**:重调零点击行为锁(:395-404,断言「终结交回」+ 零点击)与 §2.5/landing 3.2 改写对象一致;`claim_encounter_reward` 分支锁(:407 起)为保留面零改动,正确。
- **三件互查与试读**:landing 3.1/3.2/3.3 阶段范围、文件面、依赖序与 design §2.1–§2.9 逐项对照一致(§2.7 收口清单在 landing 3.2 无缺项,除 F8 所述);3.1 阶段结束态自洽(新核未接、import 全闭合、行为零变化的暂态合法);3.2 原子切换结束态 import 闭合(F401 实测清收申报覆盖 cw_events 专属 import 与 bridge 悬空 import);README 进度/待裁定点与 design §0/§2.10 一致(但见 F1 的口径矛盾);§2.12 行为变化申报 5 条与验收锚 7 条互洽;无过程叙事违例;依据就地标注密度合格。
- **治本核验(核三)**:§1 归层成立——三核并存、判据本体驻 kernel、kernel→obs 反向依赖均为直调实锤,归「分层语义 + 表示」两层准确;§2 修的是根——迁移兑现宪法五/六本体面、暗装门收窄重划 fail-closed 粒度(表示层根)、检测集归位 kernel 读数域消反向依赖、三核收敛立单一源,均非症状补丁;逐画面迁移节奏为 00_framework §1.6 明文规定,本批不构成「逐件修不升架构」违例。
