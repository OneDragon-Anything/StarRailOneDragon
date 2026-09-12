# 2026-09-11-unified-state 落地

> **判据源声明**：完成判据单一源 = 本文件阶段小节（iteration-design.md §3.1：阶段小节 = 账本唯一源，
> 立任务照小节 add，criteria 预注册指向本节）；设计改 → 小节改 → 账本 criteria 跟改，禁止两处各自演化。
> **追认事实**：账本先于本文件存在（`.debug/progress/2026-09-11-cw-clear-run/dag.jsonl`，编排者过渡
> 安排），期间账本侧发生的增挂（T-2/T-3/T-9/T-10/T-11/T-12/T-15 增挂 dep=T-31 对抗定稿门；T-5 挂
> 账本目录 w6-切换波次调研草案）以本文件追认；对抗定稿后两处对账以本文件为准，criteria 残余漂移项
> 由编排者按修订批申报落账（T-6 范围收窄/T-7 候裁门/T-12 判据节号/T-5 行号锚等）。

### 3.1 阶段1：W4 键收编链（T-1+T-2+T-3+T-4）
**范围**：四捆绑任务构成 T-4 的前置链，序①→④：①决策行 schema C1-C8 用户裁决定谳（T-1，wait 门=用户裁决；设计底稿=details/recovered/T-320-决策行文件schema设计.md，候裁状态）；②cw4 效果域内容语义设计件（T-2，候裁 8 二选一：成文或显式降级「键值原样入效果域」——两案均辖，禁以候裁 8 未决跳过本件）；③cw4 逐 key 审计只读三分清单（T-3：游戏效果键→效果域/策略行为键→决策行/无消费键删，判定面四查）；④键收编落码+cw4_counters 流删清底（T-4，按三分清单分键落码：效果域写点经 inventory 方法域 D1 锚/策略键入决策行字段/无消费键删）。
**先行段申报**：W4 审计段与键收编落码段已在 2026-09-06 迭代先行执行一遍（凭据=旧账 reviews/W4-审计-r3-复核.md accept + W4-键收编-落地审.md accept；封闭锁=sr-od-test test_cw4_key_closure.py）——先行段裁量=策略键暂由 `MandateState.cw4_counters` 容器承载零迁移、效果域 0 键定谳、流载体 `cw4_counters.jsonl` 写端/装配面已删（聚合现归宿=局终域行载荷 `MatchFinal.cw4_counters`）。本阶段④的净工作 = schema 定谳（①）后把键从过渡载体迁入三分清单定谳归宿，禁按先行段已兜住的容器形态宣布完成（详见「已执行波次对账」W4 行）。
**边界**：游戏机制效果原文考证归 game 子树（设计件只定键的归宿域，不复写机制语义）。
**设计依据**：r5-migration-plan §2 W4 行、§7 候裁 8；详设 §7（效果面完备性判据）。
**文件面**：strategies/kernel 分键写点、operations/cw_loop.py、telemetry/match_archive.py、telemetry/cli.py（r5-migration-plan §6 P4）。
**依赖**：T-1 用户裁决门（账本 cond）；审计段（T-3）可先行。
**优先级建议**：10（账本 2026-09-11 上调后现值，T-1..T-4 同值）
**完成判据**：账本 T-1/T-2/T-3/T-4 criteria 预注册（dag.jsonl）。
**验收凭据形式**：账本各任务 criteria 所列凭据（键全集封闭性锁+落地审+实机窗口，r5-migration-plan §2 W4）。

### 3.2 阶段2：W6 决策面切统一容器（T-5）
**范围**：生产决策面签名与字段读切换统一容器、sim 内部模型切换、投影 cw_bs_view 退役；交付次序按账本 T-5 criteria 预注册 5 波=kernel 标量评估簇/经济血线门/方向层演化部署事件/strategies 全簇+装配/sim 引擎+退役（次序单一源=账本目录 w6-切换波次调研草案）；边界=不含旧 GameState 本体删除（归阶段4）。
**设计依据**：r5-migration-plan §2 W6 行；详设 §8.7（迁移批次二消费切换落位面）。
**文件面**（r5-migration-plan §6 P6 全列）：kernel 决策簇、strategies/impl（mandate_v1）、sim（engine_p1/engine_p2/cw_replay/runner）、decision_assembly/cw_game_ports、kernel/cw_bs_view.py 删除、kernel/cw_evolution.py（applied-gate 族改 receipts+reconcile）、cw_expected_state.py（两态制残余清理）、Δ池再生管线（语料源切 journal）、last_state 三写点（operations/cw_screen/cw_screen_prep.py 与 operations/cw_op/cw_op_buy_cards.py 的 `session.last_state` 赋值点——符号锚，行号随树漂移）。
**依赖**：阶段1；W5 已绿（r5-migration-plan §2 W6 进入门；执行凭据=「已执行波次对账」节 W5 行）。
**优先级建议**：10（账本现值）
**完成判据**：账本 T-5 criteria 预注册（dag.jsonl）。
**验收凭据形式**：零引用锁（src+测试仓旧 GameState=0）+决策行为锁族+回放语料逐位等价（r5-migration-plan §2 W6）。

### 3.3 阶段3：W7 剩余旧流写面删除（T-6）
**范围**：board_state_archive 写点下线+逐能力归宿核对（bs_prov 注记/挂起摘要/局终速查 match_final——W2 载体已在产）+recorder/cw_telemetry_exit 残余 no-op 桩退场（record_exogenous/recover_dangling，候裁定谳后整段退）+保留流（defect_ledger/op_journal）按候裁 4 定谳执行+归档只读声明。
**边界**：删除波 1 已兑现面不在本阶段——收编 9 流全部生产写入端、battle_done 旧写、retirement.md 影子框架重构与 ADR 同步均已先行完成（凭据=ADR-0641+commit 3d4461438；其后果节明载 W7 文档义务「后续 W7 到达时余量为零」）；旧流数据文件不删不写（归档只读）。
**设计依据**：r5-migration-plan §2 W7 行；ADR-0641（删除波 1 先行段=本阶段的已完成部分，判据单一源）。
**文件面**：operations/cw_loop.py（archive_snapshot 写点）、telemetry/recorder.py（残余桩）、kernel/cw_telemetry_exit.py（record_exogenous 桩）——P7 已兑现面（recorder 旧流方法/cw_screen_battle_wait 旧写/retirement.md/sim/ledger_hooks 兜底）移出。
**依赖**：阶段1-2；候裁 2（invest 效果原文断供回流）与候裁 4（defect_ledger/op_journal 案 A/B）定谳（r5-migration-plan §7 把候裁 2/4 列编排者裁决清单 P2/P7 槽——账本 T-6 cond「用户定谳」措辞与其不一，路由对齐随修订批落账）。
**优先级建议**：9（账本现值）
**完成判据**：账本 T-6 criteria 预注册（dag.jsonl；criteria 内已兑现项「retirement 影子框架重构+ADR同步」的收窄修订=账本动作，随修订批申报落账）。
**验收凭据形式**：旧流文件名全仓零写点 grep 锁+全量测试绿+实机 ≥2 完整局（r5-migration-plan §2 W7）。

### 3.4 阶段4：W8 本体删除+BoardState 正名 GameState（T-7）
**范围**：cw_state.py 切割删除（旧 GameState 数据类+专属方法；共享词汇类型居所按候裁 9）+正名 BoardState→GameState（先删后名两段，模块文件名候裁 7）；边界=居所与文件名只执行既有裁定候选，不重裁。
**设计依据**：r5-migration-plan §2 W8 行+§3（改名时机）；详设头部命名对应注。
**文件面**：kernel/cw_state.py（切割）、kernel/cw_board_state.py（正名）、全仓 import 面+测试仓、D1 锁常量、game_state 目录命名注（r5-migration-plan §6 P8）。
**依赖**：阶段3；**候裁 7（正名后模块文件名）与候裁 9（cw_state 残余词汇居所）定谳为前置硬门（r5-migration-plan §7 P8 前置裁决，现均未定谳）——未定谳不开工**（worker 撞未决设计=停手上报，禁自行拍板）。
**优先级建议**：9（账本现值）
**完成判据**：账本 T-7 criteria 预注册（dag.jsonl；候裁 7/9 等待条件挂 cond=账本动作，随修订批申报落账）。
**验收凭据形式**：旧本体全仓零引用锁+全量测试绿+正名后 1 完整局（r5-migration-plan §2 W8）。

### 3.5 阶段5：效果账本结算挂点接线（T-9）
**范围**：效果账本 effect_inventory 结算挂点（on_battle_end）接线；边界=五在产挂点（选卡登记/节点 tick/计数 bump/跳过递减/升级标记）不重做。
**设计依据**：详设 §5（§5.1 在场效果激活账本·挂点清单）。
**文件面**：kernel/cw_effect_inventory.py、kernel/cw_board_state.py、battle 结算链挂点（cw_screen_battle_wait/cw_loop）。
**依赖**：效果账本载体在产（已落地批次，详设 §5.1）。
**优先级建议**：9（账本现值）
**完成判据**：账本 T-9 criteria 预注册（dag.jsonl）。
**验收凭据形式**：账本 criteria 所列凭据（挂点行为锁）。

### 3.6 阶段6：board_rewrite 板面重写落码（T-10）
**范围**：EffectSpec.board_rewrite 面（全员晋升/人力重组/卖全场族）落码执行；边界=随机替换面的非确定性后果仍走观察覆盖收口（详设 §5.3 归属判据）。
**设计依据**：详设 §5（§5.3 板面重写族各行）。
**文件面**：kernel/cw_effect_inventory.py、kernel/cw_board_state.py、备战执行链应用点。
**依赖**：效果账本载体在产（详设 §5.1）。
**优先级建议**：9（账本现值）
**完成判据**：账本 T-10 criteria 预注册（dag.jsonl）。
**验收凭据形式**：账本 criteria 所列凭据（确定性面行为锁）。

### 3.7 阶段7：条件型免费刷新结构化（T-11）
**范围**：条件型免费发放结构化入计数域；边界=非条件族（per_node/NODE_ENTER/burst 已在册）不重做。
**设计依据**：详设 §3.3.6（商店免费刷新余额）。
**文件面**：kernel/cw_board_state.py（计数域）、kernel/cw_effect_inventory.py、刷新执行免费闸消费面。
**依赖**：免费刷新结构化字段族在册（详设 §3.3.5）。
**优先级建议**：9（账本现值）
**完成判据**：账本 T-11 criteria 预注册（dag.jsonl）。
**验收凭据形式**：账本 criteria 所列凭据（计数行为锁）。

### 3.8 阶段8：词缀 affix 建模（T-12）
**范围**：affix_effects_data 词缀（成长的烦恼/变宝为废等）结构化建模、ActiveEffect.source='affix' 启用；边界=玩法机制原文归 game 子树，不复制进 state。
**设计依据**：详设 §3.4.4/§5.3（§5.2 词缀缺口登记辖）。
**文件面**：affix_effects_data.py（注册表）、kernel/cw_effect_inventory.py、kernel/cw_board_state.py。
**依赖**：无（ActiveEffect.source='affix' 预留在册，详设 §5.2）。
**优先级建议**：9（账本现值）
**完成判据**：账本 T-12 criteria 预注册（dag.jsonl；criteria 内「设计 §5.3扫描范围」判据指针勘正为「设计 §7扫描范围」=账本动作，随修订批申报落账）。
**验收凭据形式**：账本 criteria 所列凭据（改写面归属锁）。

### 3.9 阶段9：备战席星级观察采证（T-15）
**范围**：备战席星级/装备图标观察面采证（负探针复核）与采证定谳。
**边界**：采证定谳后按账本 T-15 criteria 二分支执行——**有源→识别线接入+bs.bench 星级消费收口（详设 §3.2.18 窟窿二）随本任务延伸落地；无源→窟窿正式关闭申报（冻结残余清单登记）**。接线与消费收口不外派「后续批」：两分支已由 T-15 criteria 预注册进本任务辖。
**设计依据**：详设 §3.2.18（星级与装备子字段·备战席装备图标负探针）。
**文件面**：obs/ 识别面（battle_prep_recognizer/cw_identity_obs）、kernel/cw_board_state.py（有源分支的星级消费收口）、画面建档 assets/game_data/screen_info（如需补档）。
**依赖**：无（观察线在役：read_star/cw_identity_obs）。
**优先级建议**：8（账本现值）
**完成判据**：账本 T-15 criteria 预注册（dag.jsonl）。
**验收凭据形式**：账本 criteria 所列凭据（采证记档+探针复核记录；有源分支另加识别线行为锁）。

## 已执行波次对账（本账本外的先行执行面）
> r5 八波中 W1/W2/W3/W5、W4 先行段与删除波 1 已在本账本（T-1..T-33）之外先行执行（2026-09-06
> 迭代与删除波 1 独立批次）；本节=其在本文档的唯一对账载体，各阶段依赖行的「已绿」以此节凭据为准。
- **W1 journal 常开化+观察接线收尾**：ADR-0634（直迁裁定、journal 无条件常开）；代码锚=telemetry/match_archive.py v12 注「无条件常开(R5 W1/ADR-0634)」；落地审=旧账 reviews/W1波-落地审.md。
- **W2 局终域+收编准备**：ADR-0630 修订节三条（局终域域键/写口辖域勘误/监听触发语义勘误）；入库笔=commit 8294d0bdb；落地审=旧账 reviews/W2-局终域-落地审.md accept + W2-返工-delta审.md 闭环。
- **W3 判读/哨兵/运行时切新账+删旧读面**：哨兵三脚本切 journal（skills/sr-od-currency-war-dev/scripts/ cw_sentinel v5.2「活跃局判定切 journal」/cw_runs_gap/cw_early_stop）；telemetry/cli.py 头注「--source 双读面拆除」；落地审=旧账 reviews/W3波-落地审.md。
- **W4 先行段（审计+键收编落码）**：旧账 reviews/W4-审计-r3-复核.md accept（键全集底稿 336 键+9 开放族）+ W4-键收编-落地审.md accept（流删+容器承载裁量+封闭锁 test_cw4_key_closure.py）；净余量与禁完成口径见 §3.1 先行段申报。
- **W5 透传域建模收编**：入库笔=commit 8087ae3c9（落地审零阻断放行）；代码锚=kernel/cw_bs_view.py 域清单「容器值收编」；测试锁=sr-od-test test_cw_w5_passthrough_adoption.py；落地审=旧账 reviews/W5-实施-落地审.md。
- **删除波 1（W7 先行段）**：ADR-0641+commit 3d4461438（38 文件 −2144/+397；落地审=旧账 reviews/删除波1-落地审.md accept，本地不入 git，凭据链见 ADR-0641 关联节）；retirement.md 影子框架重构随批兑现、battle_done 旧写随批删除。

## 末阶段：正本更新
**范围**：按「正本更新清单」逐条更新正本
**设计依据**：本文件「正本更新清单」节
**文件面**：game_state/（README 总纲+分篇，含新建 fields.md）、清单所列代码 docstring 与正本区文档
**依赖**：全部阶段
**优先级建议**：0
**完成判据**：清单清零；正本与实现一致
**验收凭据形式**：文档对照 review

## 正本更新清单
> 终态：正本家 = docs/develop/currency_war/game_state/（总纲+分篇）；本迭代全部设计语义最终归宿于此，详设件是过程载体。
- game_state/fields.md（**新建分篇**，承载字段级规格——来源=详设 §3 画面字段清单/§4 决策 op 写入面/§5 效果族归属；拆分粒度=归拢时定，可按画面或域拆多篇）← 阶段5-8
- game_state/README.md §3.3 域清单字段面收全 ← 阶段5-8
- game_state/README.md §1/§5 过渡注清除（详设归拢后）← 末阶段
- 代码 docstring 引 changes/ 详设的收口（改指正本 game_state/——入口=总纲，字段级面指分篇）← 末阶段。收口清单（grep 锚=`changes/2026-09-11-unified-state` 与裸名 `BoardState-数据结构设计`，共 5 代码文件）：
  - kernel/cw_board_state.py:5（changes/ 路径引用）+ :827（跨迭代引 changes/2026-09-06-redesign/w5-透传域建模方案.md——归宿=正本或 ADR，随批定）；
  - kernel/cw_bs_view.py:2-5（头注两处；本文件随阶段2 删除，删除即收口）；
  - obs/cw_shop_refresh_obs.py:4-5；
  - sim/engine_p1.py:1575 与 obs/cw_observation.py:2394（裸名引用「BoardState-数据结构设计.md」，同辖收口）。

  （勘正：kernel/cw_anchor 无 changes/ 引用，不在清单——原清单误列项随对抗修订批除去。）
- 正本区三处引 changes/ 详设的长期引用清除（铁律=AGENTS.md「代码与正本文档禁引 changes/ 内容」；改指 game_state/ 正本入口，与上条同批收口）← 末阶段：
  - docs/develop/currency_war/README.md:28；
  - docs/develop/currency_war/game_state/README.md:12/:102；
  - docs/develop/currency_war/design/统一观察架构-画面op基类设计.md:4。
- game_state/README.md §5 件 B(节点链观察-设计v1)指针已 re-anchor 至 details/recovered/ 落位件(2026-09-12 指针回填批完成;.debug/temp 原件仍留未删)← 末阶段核对即可

## 排除声明
- T-8 属统一观察架构迭代，不在本迭代面；
- T-13/T-14/T-16..T-28 非本迭代面（归属各自所属迭代的账本辖）；
- 详设 §5.2 缺口登记面本迭代只建模两项：本金充裕族条件免费刷新（阶段7/T-11）与词缀（阶段8/T-12）；其余缺口（容量改写〔节省工位〕、发牌族全量逐卡登记、hp_max 三来源、时点型延迟金载体、长线利好刷价、公司严选/搜打撤/高效决策等）**本迭代不建模，继续观察覆盖兜底**——登记=归属（详设 §7 冻结判据辖），不构成排期承诺，后续建模批立项候编排者。**容量改写硬前置申报**：首批容量条目（节省工位）的建模批必须同批补观察构造器容量感知（详设 §8.7 批次三补单⑧ project_effect_capacity 自设前置——缺它投影恒 no-op，「按 9 槽摆 3 槽席」危害对节省工位局不设防），禁拆两批。
