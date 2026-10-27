# 转型域换人通道统一设计 无前提对抗审查报告(本轮全文,替换既往内容)

> 审查对象:本目录 `design.md`(总纲)/`landing.md`(落地)/`README.md`(索引),现行文本(对抗审中)。
> 审查纪律:干净上下文、无前提、三核并重;数值/口径/引文/码点一律直调复核禁转述,as-built 断言读代码体(docstring 仅线索),行为可达性拿复盘报告真实牌面逐帧推演(含 victim 池在门 2 全谓词+两级序下的可达性与选择结果、OR 承接阵容与档位梯阵容两形态、bench/板侧标签件在装配 A 机制下的卖出可达性)。
> 判据源(全部直调自取):宪法 `strategy-docs/00_framework.md`(第 1 条行亲读)/`01_math_framework.md`;`proofs/math_proofs.md`(P61/P63/P78/P79/P87/P88/P89/P90-94 行)+单篇 p61/p87/p88/出口生存余量篇;注册表(`data/cw_factions.py` 全表、`data/cw_chars.py` :106-181、`kernel/cw_comps.py` 双王圣杯条目+form_progress+SEELE_OR_LEGS、`kernel/cw_merge_simulate.py` same_star_count 定位、`kernel/cw_line_defs.py` 围栏集、`kernel/cw_system_cards.py`);现行换人机器(`kernel/cw_deploy_logic.py` :478-1784 逐段代码体、`kernel/cw_launch_admission.py` 全文、`kernel/cw_intention.py` committed_authority 段)、策略层(`mandate.py` P79-3 段+发出段、`entry.py` 窗口段+第 6 步、`deploy_plan.py` is_tgt、`session_scope.py` line_members_view/direction_comp_of、`statefn/predicates.py` line_members、`criteria/sell_candidates.py` 资格段、`sell_gate.py` 装配 A 段、`mandate_state.py`);正本篇(02/10/11/14/17/18/22/24);流程层(projection_contract §4.3、action_exec/screens 存在性);复盘档案 `.debug/currency_war/deep_review/g_20261026_203023.md`(2-1 帧开店前后双帧逐段);迭代账本(T-115 裁定 dag note 2026-09-07);规范(`docs/develop/harness/iteration-design.md` 全文、`skills/sr-od-currency-war-dev/references/strategy-work.md` 全文)。

## 总判定:**需修订**(阻断 3 + 应修 3 + 存疑 2 + 低 4)

---

## 一、发现清单

### A1【阻断】情形 B(外部凑档件换入)三方矛盾 + §2.6 窗口层 as-built 断言失实

- 码点事实(读代码体,`entry.py:325-345`):`_deploy_window_blocked` 两腿豁免——腿一(`:336-338`)豁免 `direction_comp_of` 的 `line_members`(core∪shared,`statefn/predicates.py:81-92`);腿二(`:340-342`)锁定帧豁免锁定线名单外的一切件。锁定帧下 k = 锁定线(`session_scope.py:387-389`),两腿合起来把**全部件**豁免——**锁定转型域内窗口谓词结构性恒 False,窗口层对本迭代辖域零约束力**。§2.6(design.md:85)「无 entry_signals 登记的替补 = 窗口判定恒关(不可经换人上板)」「外部凑档件(如第 5 格能量件)的可上板性 = 阵容知识登记义务」「未登记期情形 B 不可达」三句在转型域内全部失实:`entry_signals` 缺行→恒关只在**未锁定帧**的终局库成员子域成立(`entry.py:343-345` + `_entry_window_open :281-322`);转型域判别子腿①要求已锁定,情形 B 所在帧类根本不经窗口判定——星期日(`cw_chars.py:155`,能量标签外部件)走腿二 `:340-342` 直接豁免,登记与否无关。
- 三方矛盾:①§2.2 枚举表 B 行(design.md:57)「放行(①②)」+ landing 3.1「枚举表 A/A′/B/C/D/G/E/F 全情形」单帧测试(landing.md:31)要求 B 可达并放行;②§2.7(design.md:91)把 up 侧三消费位(`select_deployments is_tgt`/`_bench_is_target`/`post_sell_offline`)target 视图切**名单口径**——`post_sell_offline` 底线 = up∩名单≠∅(现行同构 `cw_deploy_logic.py:1750-1757`),B 组(外部件进、纯过渡件出)up∩名单=∅ → 底线拒,B 仍不可达;③§2.6 用错误的窗口机制宣告 B 不可达并给「登记后生效」的解锁路径——该路径既不改变腿二豁免、也不改变名单口径底线,不成立。§2.7 自己又写「外部支撑件归 rest 组照旧、经双门换血通道上板」(意图=B 可上板),与同节底线口径直接相抵。
- 修正方向(设计层三选一,全量同步):①外部件换入是意图 → up 侧底线对门 1 通过组放行或改「组内含名单件或外部支撑件」,§2.6 重写为代码体真相(锁定帧窗口惰性,如实申报),landing 3.1 保留 B 正向测试;②外部件换入非意图 → 枚举表删 B 行或改「拒绝(名单口径底线拒)」并申报,landing 改负向稳态测试,§2.6 把真实封堵机制(底线)写明;③维持「登记后可达」 → 必须同时改底线口径并修正 §2.6 机制叙述,否则解锁路径不存在。

### A2【阻断】fenced 关门分支迁移规格不唯一:三种帧类两读法行为不同,申报④不可验证

- 码点事实(`cw_deploy_logic.py:1023-1032`):关门分支——`elif not _trans:` 进入后 `not ENABLED or not _locked → closed;fp 缺读 → fp_unreadable;否则 closed(fp≥1.00∨板不满)`。混轨 `locked` 含配方对锁腿②(装配 `:1479-1480` pair 帧置 True),故 pair 帧板满∧fp<1.0 时 `_trans=True` **跳过**关门分支落资格族(`:1032`)。
- §2.3.1(design.md:73)两句并陈:「关门分支判定迁移:其现行域谓词(混轨 locked)**切换为转型域判别子**」+「**双轨域不关门落资格族**(pair 帧现行『fenced 件可卖』形态保持)」。逐帧类对账:

| 帧类(fenced 件 victim) | 现行 | 读法一:谓词字面切新判别子 | 读法二:按「双轨域不关门」声明 |
|---|---|---|---|
| 转型域(终局锁∧板满∧fp<1.0) | 落资格族(:1032,engines_guard 等) | 进关门分支 → fenced 件全封(违 §2.2 case A「禁字面移植」自警) | 双门/守恒新义裁定(✓ 与 §2.2 一致) |
| pair 帧板满∧fp<1.0 | 落资格族 | 新判别子 False → closed → **申报④声称保持的通路被关死** | 落资格族 ✓ |
| pair 帧板满∧fp≥1.0 | `fenced_arm_closed`(:1031) | closed | 落资格族——**未申报的放宽边**(成型 pair 帧非档承载围栏件由不可卖变可卖) |
| 未锁帧(非 pair 非锁定) | closed(:1027 `not _locked`) | 未定 | 未定 |

  两读法在 pair/未锁两类帧上行为相反,设计文本不能唯一确定迁移后分支形态;`SWAP_TRANSITION_ARM_ENABLED` 退役后 `:1027` 的 `not ENABLED` 检查替代形态未钉;`fenced_arm_closed` 拒因键存废未定(它同时是 mandate 逐件拒因分键闭集成员 `mandate.py:1469-1473` 与 projection §4.3 判读面)。
- 修正方向:按帧类显式钉迁移后真值表(建议:关门分支整体退役、`fenced_arm_closed` 键的存废与其在分键闭集/projection 判读面的归置一并申报),逐帧申报行为差(含 pair 成型帧放宽边与未锁帧归属)。

### A3【阻断】退役迁移面漏功能性消费位:店侧 P88 收窄与双轨域放行门路由

- 码点事实:`SWAP_TRANSITION_ARM_ENABLED`/`_swap_transition_domain_of` 的消费位不止 §2.3.1(design.md:73)点名的五消费位+快照+关门分支——`mandate.py:36-37` import 两符号;`swap_transition_narrow_frame`(`mandate.py:732-777`,P88 店侧 dominance/hub 收窄域谓词,自申报「同一谓词」)在 `:776-777` 直调,消费位 = `shop.py:979` + `mandate.py:1134` 分键;P88 的 D 域含 pair 帧(旧混轨 locked),迁移到新判别子(腿①排除 pair)会使 pair 帧 dominance/hub 收窄解除 = **未申报行为差**,保留旧谓词则与常量退役冲突。§2.3.1 只点了「P88 命题引用(文档)随改写」(§2.9),landing 3.1 文件面(landing.md:27)无 `shop.py`,范围与完成判据均无此项。
- 另:`mandate.py:1495` 发出闸条件 `_m1p.arm == 'transition'`——arm 标注族随转型分支退役换 `bond_gate_*`(§2.3.1),双轨域放行门(§2.5「不动」)靠该路由触发;双轨域 pair 帧计划的 arm 标注值与闸触发条件在新键族下长什么样,设计未申报——「双轨域放行门不动」缺承载文本。
- 修正方向:退役面清单补 `swap_transition_narrow_frame` 归置裁决(域随新判别子并申报 pair 帧收窄解除;或保留独立三腿谓词并申报符号分界)入 landing 3.1 文件面+判据;双轨域放行门的路由条件与计划标注形态补入 §2.5/§2.3.1。

### A4【应修】§2.8 收敛不变式的通道封死枚举漏换人卖出通道;landing 3.3 两条边界锚与设计正文矛盾

- 事实一:段一(design.md:100)「板侧标签命中件的离场通道逐通道封死:来金/演进按 §2.8 排除;自救/晶矿/店换为 bench 侧通道(BENCH_ONLY)不动板面;保护集禁卖」——漏列换人通道:枚举表 A′(design.md:56)明确放行「Saber 换停云」,停云=终局键集标签命中件(`cw_chars.py:121`,仙舟+**能量**),经换人 `CwActionSellDeployedParam` 离场 = 板上标签命中件经卖出动作离场。
- 事实二:landing 3.3 完成判据(design 依据 §2.8)固化两条边界锚(landing.md:58)——「**板上标签命中件不可经卖出通道离场**」被 A′ 放行行为证伪(换人卖出即 SellDeployed);「**bench 侧标签件仍可来金卖出**」与 §2.8 堵回降口二「来金族资格增补排除终局键集标签命中件(**bench 侧含内**——装配 A 身份段 bench/场上两侧一致生效,`sell_gate.py:886-915`+`sell_candidates.py:559-567`)」直接矛盾——bench 标签件恰恰被来金排除,仅自救通道仍可卖(§2.10 自救豁免申报)。
- 结论本体不倒:板上支撑数非降可由门 1 结构保证(①新档/④成型 ⇒ 换入组必含键集命中件 +1 ≥ victim −1;②严格增;③同名在板净 0),但段一的论证形态与两条测试锚须改。
- 修正方向:段一枚举补换人通道,不变式改写为「非换人卖出通道逐通道封死 ∧ 换人通道由门 1 组换收益保证支撑数非降」;landing 3.3 两条锚同步改写(第二条改「bench 标签件仅自救通道可卖」或按裁定后的口径)。

### A5【应修】landing 3.4「0534 退役引用面随本阶段(design §2.3.1)」依据失指,指称需侦探工作才能解码

- 事实:「0534」在 design.md 全文零出现(§2.3.1 = design.md:73 通篇无此词);可解码来源仅一处代码注释——`cw_deploy_logic.py:484-485` 引「docs/develop/sr_od/application/currency_war/decisions/0534-swap-transition-arm.md」(转型分支语义出处件)与 `:1288` 同前缀,而该 decisions 路径在盘上**不存在**(全 docs 树 glob 零命中)= 悬空引用。实现者读 landing 判据与 design 依据无法知道 0534 指什么;「依据就地标注」(iteration-design §5.1)与「全量同步复查:引用锚存在性」(§5.4)双双不满足。
- 修正方向:landing 3.4 把「0534 退役引用面」写成可执行的实名描述(如「cw_deploy_logic.py 转型分支段头注释(:483-489)与 :1288 对退役决策件的引用行清理」),design 依据改指真实存在的锚;若该决策件应存在则先补案或改引 git 历史。

### A6【应修】landing 3.1 组算法测试判据含「超员降级」,设计全文无此语义

- 事实:landing.md:40「组算法测试(两级 victim 序锚帧复验:Saber 换爻光;**超员降级**;无可行组零动作稳态)」——design §2.7(design.md:90-94)无「超员降级」任何定义;转型域判别子腿②=板满(占用 ≥ cap,`cw_deploy_logic.py:1599-1602` 占用数口径),「超员」状态与「降级」行为在设计内无出处。测试判据引用不存在的语义 = 立任务即不可验收(iteration-design §3.1 判据可验证性)。
- 修正方向:design §2.7 补该语义(若指 SIFT 未识别占位件的占用数形态,引 `:1599-1602` 写明),或从判据删除。

### A7【存疑】§2.0「转型域内五层全部消费同一判定函数」与 §2.4/§2.6 显式保留各自折法字面冲突

- §2.0(design.md:24)宣称五层(触发/守恒/素材/放行/窗口,§1:12 同清单)统一单一判定;§2.4(design.md:75-77)素材层零改动(merge_material_guard 自备关切)、§2.6(design.md:83-85)窗口层零改动(entry_signals 自备判定)。实际统一面 = 触发/守恒/资格/放行四层。§1 归层把「多层协作无统一约定」定为公共根,则保留两层独立折法需要在 §2.0 显式声明辖域(素材层关切 = 合成经济价值、窗口层经 A1 核实在转型域惰性——为何不构成同族封堵),否则读者按 §2.0 字面会试图把窗口/素材并入门 1。修正方向:§2.0 改「四层统一 + 素材/窗口两层显式保留(各附理由)」。

### A8【存疑】组贪心宿主 kernel 与宪法第 5 条所有权判据线的张力未正面回答

- 宪法第 5 条(`00_framework.md:15-19`)判据线:「换一套策略实现,会不会要不同的值/序?会 → 策略层」。组贪心的候选序(名单成员先→外部支撑件)、victim 两级序、「首个可行组即停」属决策 policy 形态。关键取舍(design.md:133)以「依赖方向禁反向;单对现行形态升格」选 kernel——kernel 已有 `select_swap_plan`+`select_up` 注入缝先例可缓解,取舍已申报,但未回答判据线问句本身(对比先例:P79-4 让渡序以命题+kernel 注册式落位)。修正方向:取舍段补一句判据线正面回答(换人机器结构序 = P79-4 同族机制定义量,非策略立场;策略定制面 = select_up 注入),或把贪心排序参数化留注入缝。

### 低

- **A9|低|贪心候选序同层并列(星级并列)未钉**:design.md:90「名单成员先(星级降序)→ 外部支撑件(星级降序)」未定义星级并列的层内序。锚帧不受影响(2-1 开店后 bench 名单成员仅 Saber 一名;远坂凛非双王圣杯 core=`cw_comps.py:1022`,属外部支撑件层级,复盘 `:2902-2906` bench 亲读);但 3.5 的 2-2..2-4 逐帧预测表需要确定性序,并列序未钉则推导不唯一。补一个 tie-break(注册表序/bench 扫描序)一句话即可。
- **A10|低|§2.8 落点表述「消费于来金族 FACE_REGULAR」不精确**:`sell_exclusions` 为全部 FACE_REGULAR 场景共用装配(interest/funding/ore_make_room/shop_swap/c1_make_room/levelup_liquidate_prep,`sell_candidates.py:177-196/:559-567`),落点钉死后排除自动覆盖全部常规通道候选池(bench 侧腾位/店换/筹资一并收窄),非仅来金族;§2.11 申报②未逐通道点名。改一句话并申报②补覆盖面清单。
- **A11|低|k_members(终局名单成员)未钉单一源定义**:design.md:28 起多处使用但无定义出处。现行对齐源 = `statefn/predicates.line_members`(core∪shared,`predicates.py:81-92`;01_math_framework §2 目标线 K);`required_deployed` 名归属(希儿系静态套 required=('希儿',))未声明。§2.1 补一行定义+单一源指针。
- **A12|低|victim 序第二键「星级」按现行实现是 1★ 优先桶非全序**:现行键 = `(_contrib, 0 if star≤1 else 1, 槽序)`(`cw_deploy_logic.py:1703-1707`);§2.7(design.md:90)「(档边际贡献, 星级, 槽位)」按全序读会引入实现不存在的序。括注「星级 = 1★ 优先桶(现行 :1705 口径)」。

## 二、核三·治本核验结论

- **§1 归层成立(实证)**:在真实 2-1 帧重放现行机器——板上五件逐件 `target_keep`(吉/远坂凛 = 名单成员;青雀/停云/爻光 = 仙舟标签 ∈ 收窄后 target 视图{命运圣杯,仙舟,战技点},`cw_deploy_logic.py:1004-1022`),必需件分支因双王圣杯无 `required_deployed` 恒关、完成分支因无单件可补满恒关(复盘 C1 主证帧 `:2920` 同结论),计划恒空。「只修触发层不达效」与「多层独立封堵」的归层诊断与帧证据吻合;根在语义层(单件一步成型对多成员多档位不可达)+约定层(层间无统一判定)成立。
- **§2 修根**:以「组换后板态×锁定终局阵容」替换语义单位、门 1/守恒/放行统一折法——修语义根非症状;双轨域原样 = 爆炸半径显式圈定,取舍有据。残留:A7 的「五层统一」申报口径与实际统一面不符;A1/A2/A3 表明统一在情形 B、fence 维、域谓词消费面三处接缝**未收敛完**——恰是需回设计层补钉的面。
- **跨件半问**:§1 自报「同族病第二件,升架构级」(第一件 = 2026-09-18 板满换入分支,docstring `:768-770` 出处行亲读吻合)——本迭代即升级件,非第 3 件症状补丁。

## 三、核二·规范遵循结论(逐条带出处)

- `iteration-design.md`:四节齐 ✓(README/design/landing;无详设 → §0 申报「单文档方案」合规 §2.1);阶段小节七件齐 ✓(3.1-3.5+末阶段逐项核对,含常规检查首节自包含);README 构成 ✓;写作硬规则①依据标注——主体合规,违点 = A5(依据失指)/A6(判据无出处)/A11(定义缺指针);硬规则②无需再设计——违点 = A1(B 形态三处矛盾)/A2(迁移真值表不唯一)/A3(消费位归置未裁决);硬规则③无过程叙事 ✓(三件正文无轮次/修订措辞);硬规则④全量同步复查——违点 = A4/A5/A6(design↔landing 失同步三处)。
- `strategy-work.md`:§1 零调参 ✓(门 1/守恒/白名单全为注册表档位梯与结构计数,`cw_factions.py:67/:93` 档位直调,无新自由参数;【拍】类 = 用户裁定登记,§2.10 合规宪法第 1 条);§2 改前四步 ✓(判读上局 = 复盘立案 C1;玩法文档面引用齐 = research README `:82` 单一源在案;定位两问 = §1 归层;设计先行 = 本稿);§3 开关纪律 ✓(`SWAP_TRANSITION_ARM_ENABLED` 退役 = 存量清理,其注释自申报「删码时同删本常量」;无新增开关,`bond_gate_*` = 遥测键非开关);§6 prereg 完整性硬门 ✓ 形态合规——五线载体逐条亲核:P89 约束段 = `math_proofs.md:110` ✓、02 §8 命题 A = `02_mandate_layer.md:97-99` ✓、11 新基线 = `11_shop_decisions.md:186` ✓、FM-1 = `:185` ✓、T-115 三不状态裁定 = `.debug/progress/2026-09-06-currency-war-redesign/dag.jsonl` 2026-09-07T13:10:18 note ✓(「裁定实质亲验在案」属实);盘点义务声明 ✓。载体核对不豁免 A1-A3 的设计缺陷。

## 四、依据就地标注直调复核(核验通过面;值对标签逐条核对)

- 注册表标签:`cw_chars.py:106-181`——吉尔伽美什:130/Saber:149 = 命运圣杯+能量;开拓者·记忆:168/藿藿:122 含能量;瓦尔特:181/符玄:164 不含;停云:121 = 仙舟+能量;远坂凛:126 = 命运圣杯+战技点;**青雀 = 仙舟+战技点恰在 :112** ✓;爻光:133 = 仙舟+欢愉非圣杯非能量 ✓。档位梯:`cw_factions.py` 命运圣杯 (2,3,4,5) = :67、能量 (3,5,7,10) = :93、战技点 (2,4,6,8) = :94 ✓。双王圣杯(`cw_comps.py:1022-1066`):form_tiers={命运圣杯:3,能量:5} ✓、core_chars 六名 = k_members(**远坂凛不在 core**,§2.2.1「停云/远坂凛类非名单」与注册表一致 ✓)、教义「哪怕下远坂凛都不能拆能量」= :1034 ✓;SEELE_OR_LEGS = :603/SEELE_CARRY_CHAR = :604 ✓;`form_progress` OR 承接+required 腿契约(`:1792-1858`)与门 1④「同一折法」声明 ✓;victim 序度量域收窄键集与全量并集的逐件等价性(docstring `:608-614`,剔除键 = 未达成键,离场单调 ⇒ 差分恒 0)自洽 ✓。
- 锚帧算术(度量域直推):2-1 开店后帧(复盘 `:2877-2920` 亲读:板上 吉/青雀/远坂凛/停云/爻光 5/5;bench 含 Saber 1★+远坂凛第二张 1★)——爻光贡献 = 仙舟 3→2 掉 1 档 = 1;青雀 = 仙舟 −1 + 战技点 2→1 −1 = 2;爻光 < 青雀 → 一级序首 victim = 爻光;换后圣杯 3(二阶新档)∧能量 3(一阶新档)∧支撑数 3→4 严格增。锚①「Saber 换爻光,两级序+贡献度量唯一推导」复核成立(bench 名单候选唯一使组选择唯一)✓;「远坂凛持续受保护(bench 有第二张,same_star_count=2)」经 bench 亲读 + `cw_merge_simulate.py:438`(经 `cw_vocab.py:92` re-export,守卫计数 = 2 拒 `cw_deploy_logic.py:1062-1065`)成立 ✓。
- 码点引用:`:775` 板满门 ✓;`:1666-1668` 板满早退 ✓;`:545-547`/`:991` fp<1.00 键集回全量 ✓;`:582-583` 混轨谓词 ✓;`:999-1003` 量席让位注释 ✓;`:1701` 贡献度量 ✓;`:1750-1755` 单对计划形态 ✓;`:1352-1353` 演进谓词对账义务自声明 ✓;`:496` ENABLED ✓;`cw_intention.py:1606-1630` committed_authority 腿①②、配方锁帧返 True ✓;`cw_launch_admission.py:55-89` target_keep 谓词/`:92-109` 保护集 = core∪shared∪替班/`:215` P61 引用 ✓/`:348` 准入三元只暴露不拦截(§2.7「不新增 admission 闸」依据)✓;`mandate.py:838-895` P79-3 三轴(轴① bench∩membership、轴② Δfp>0 = `_deploy_advances_form`)与 §2.5 描述一致 ✓/`:861` B_t 段 ✓/`:1520-1532` arm 分键与 `cw4_m1p_arm_pending` 写点 ✓/`mandate_state.py:252` ✓;`entry.py:336-342` 豁免两腿存在 ✓(辖域真相见 A1);`sell_candidates.py:385-396` is_field_irrelevant_unit 仅覆盖有档件(有档件 = 贡献件 → 不入无关池,「真实泄露 = 无已达成档的标签件」申报准确)✓;DEPLOY_FENCE = RECIPE{仙舟/持续伤害/列车同行/护盾}∪ENGINE(`cw_line_defs.py:22-28`)→爻光/停云/青雀均围栏件,§2.2「禁字面移植否则 case A fence 件被封」前提 ✓;SWAP_GUARD_SYSTEMS = 三羁绊+希儿系+护盾(`:124-125`+`cw_system_cards.py:102-139`)→§2.3「爻光/青雀守恒体系承载仙舟档」✓。
- 文档引用面:`math_proofs.md` P61 = :83/P78 = :100/P87 = :108(先例引用)/P89 = :110 约束段 ✓;`14_p1_consume_arms.md:602`(P61 族推迟上界)/`:385`(B_t 面)✓;`18_equip_wear_semantics.md:117/:140/:182` P61 = 装备域占位编号(同号异命题陷阱属实)✓;`p87:8` P61 先例引用 ✓;p88/p89/出口生存余量篇在盘且涉 P61/B_t ✓;`cw_launch_admission.py:215`/`mandate.py:861`/`flow.py:138-180`/`telemetry/schema.py:421-422` B_t 面实存 ✓;`proofs/p61-bt-swap-arm-dominance.md` 存在 ✓;`02_mandate_layer.md:12`「部署 0/934」/§7 sell 行 = :90/§8 命题 A = :99 ✓;`11_shop_decisions.md` §4.0 场景表(「场上无关角色」定义)= :128 节内 ✓;`22_prep_screen.md:36-37` 第 6 步+entry_signals 缺行语义 ✓;`24_deploy_segment.md:11`(引「22 §1 第 5 步」漂移属实,实际第 6 步)✓;`10_prep_decisions.md` §1/`17_stall_form_spend_authority` §1.1/`flow/action_exec.md`/`screens/README.md`/`screens/deploy.md:27`/`projection_contract.md:105`(§4.3)全部实存 ✓;`skills/sr-od-currency-war-dev/scripts/cw_sim_match_drive.py` 存在 ✓;复盘档案在案且 §1 seed=20261216 = §2.10 复测 seed 自洽 ✓;`docs/game/currency_war/research/README.md:82` 策略相关文档节 ✓。
- 枚举表其余情形逐帧核:A(Saber 换爻光,①②放行,门 2 逐件过)✓;A′(①放行,停云二级 deprioritize)✓;C(名单成员进,支撑数+2)✓;D(同名升星,3(a) 通道,机制可达)✓;G(希儿系 required 腿+OR 承接,④承接,`_completion_swap_ins` 同折法)✓;E(瓦尔特换符玄四分支全不中)✓;F(卖档位承载件,①档位面+守恒拒)✓;§2.11 申报①覆盖性论证(触发轴同一折法/victim 轴 3(b) 承接+通道 2 更宽)推演通过 ✓;申报③⑤⑥与 §2.7/§2.3 正文一致 ✓。

## 五、结论

- **阻断 3 项(A1/A2/A3)、应修 3 项(A4/A5/A6)、存疑 2 项(A7/A8)、低 4 项(A9-A12)。**
- A1 击穿情形 B 的可实现性与 §2.6 的机制申报(设计自己的枚举表、落地测试、底线口径三处互斥);A2 使申报④在其自引码点的两种合法迁移下均不可满足或引入未申报行为差;A3 是退役面的功能性消费位遗漏(含 shop.py 行为差)。三者均须回设计层裁决并按 iteration-design §5.4 全量同步 design↔landing↔README 后重审;应修 3 项为低成本补钉;存疑/低随批处置。其余攻击面(见第四节)零发现。
