# 旧账卫生与运维收编 设计对抗审报告（attack.md）

> 对抗批输入：design.md / landing.md / README.md / details/ 六份（九份全文通读后施攻）。
> 判据源：iteration-design.md（三核细则与写作硬规则）、账本 dag.jsonl（dag.py card T-13/T-14/T-16..T-27 + T-33/T-28/T-4/T-5/T-7 与旧账 T-280/T-308 卡）、AGENTS.md / AGENTS.local.md 纪律节、r5-migration-plan.md §2、仓库工作树与 HEAD 直调。
> 所有发现均按「册+节+严重级+发作场景+证据」给出；零转述，锚点全部亲跑核验。

## 一、发现清单（按严重级）

### F1【高·阻断】T-17 阶段整体设计在过时世界态上：三层方案已由旧账 T-308 入库，九份文档零提及

- **位置**：design.md §0/§1（T-17 列为 14 项之一）、§2 IC-2；landing.md §3.4；details/execution-seam-projection.md §T-17 全节。
- **事实**：execution-seam §T-17 的全部方案内容——S2 主修（`reconcile_tracking` 写回经 `bench_from_compact` 重建槽位表+槽号健康门+拒绝留证）、S1 结构防御（4 点 `pad_bench(deepcopy(tracked))` 下标直拷）、S3 epoch 通道（`bench_layout_epoch` 字段+递增+播种期快照+单动作循环检差三步）、顺路面三件（guard docstring/defect verdict 根因句、读路径写副作用关闭注释、ExecState 双账注解修正）——**已由旧账 T-308 落码批于 2026-09-11 12:42 提交入库（bd27989d4，主仓 7 文件 +203/−33，测试仓 3 文件新锁 15，落地审 accept）**。旧账 T-308 卡状态 = done（附注入库记录 12:45:44）；其方案正本正是本迭代引用的同一份「T-280-交付报告.md §③ v2 修订版」。
- **文档失真点（逐条亲验）**：
  1. 症状现在时（「持续制造者 = reconcile_tracking 写回紧凑列表」）——HEAD 的写回已经健康门+槽位表重建（`git show HEAD:.../cw_reconcile.py` 含 S2 全套）；2 例 WARNING 是 T-308 修复前的实证。
  2. 行锚点全部为 T-308 入库前旧位：S1 四点「cw_op_buy_cards.py:783/:349、cw_shop_action_ops.py:239/:488」现居 :797/:354/:223-275/:527；「禁改 cw_screen_prep.py:548/702」现居 :497/:627（T-321 批又移过一次，详设定稿时点已漂）。
  3. 「同构先例 = cw_reconcile.py:236-237 deployed 侧」——该两行现指向的恰是 **bench 侧 S2 主修注释本身**（deployed 侧先例在 :273-278）。
  4. 改动面声明「cw_reconcile.py / cw_state.py / cw_op_buy_cards.py / cw_shop_action_ops.py」——S3 字段实居 cw_exec_state.py（不在面内），而 cw_state.py 恰是 T-308 交付时**明文收窄为零触碰**的文件（T-308 卡与 commit message 均申报「方案申报面实际收窄 = helpers 零改」）。面在两个方向上都不对。
  5. 迭代目录九份文件对 T-308 / bd27989d4 **零提及**（Select-String 实测空）。
- **T-17 真实残余**（文档均未声明）：①「连续批跑 0 例降级 WARNING」正式取证（T-308 只做了新锁 107 passed 与「基线当前树已全绿」口径处置）；②T-308 落地审 P3 残余：健康门拒绝分支 sorted 混型防御面+返回值 docstring（候小批）；③实机回归项（候实机窗）；④重放/锁凭据与账本 criteria 对账。即 T-17 从「优先级 4 的落码批」实为「验证+小残余收尾批」。
- **发作场景**：编排者照 landing §3.4（优先级 4，全迭代技术面最高排位）派 T-17 → worker 按详设「按方案正本三层落码」重做已入库改动 → 与 HEAD/留树 hunks 冲突，或产出零 diff 白批；IC-2 让 T-16 继续等一个已存在的 pad 态契约，空转一轮。
- **证据**：`dag.py --file 旧账/dag.jsonl card T-280 / T-308`；`git log -1 bd27989d4`；`git show HEAD:.../cw_reconcile.py`；`git status`（cw_op_buy_cards.py / cw_shop_action_ops.py 干净）；工作树 diff（cw_reconcile.py 仅剩他批 is_merge_effect_window 18 行）。

### F2【高·阻断】「T-17 必须先于 W6/W7/W8 开工落库」：两条依据腿失真，且与 sim state 门相抵（字面不可满足）

- **位置**：design.md §2「跨迭代互斥」；landing.md §3.4 依赖行。
- **攻点一（依据失真）**：design.md 给该硬时序标注「依据 = T-280-交付报告.md §③ 冲突时序段」。该段原文（temp 报告 L87）只含「①排当前在飞批 commit 入库之后（…禁半-tree 叠批）」，通篇无 W6/W7/W8 字样——「先于 W6/W7/W8」是设计者外推，却挂在引用名下（写作硬规则 1：依据须真的支撑主张）。且该段的「在飞批」= T-308 落码批本身，其入库条件**早已满足**（12:42 入库）。
- **攻点二（前提失真）**：时序论证的核心前提「T-17 改动面含 kernel/cw_state.py（W8 切割对象）」——见 F1 第 4 条，被引用方案的实际交付已把 cw_state.py 收窄为零触碰；真实残余只涉 cw_reconcile.py 单文件小修（W6 的 applied-gate 确实复用 cw_reconcile.py，残余时序有意义但面极小）。
- **攻点三（与 state 门相抵）**：T-17 完成判据「修复后连续批跑 0 例降级 WARNING」是 sim 批。AGENTS.local state 门（「实机对局与 sim 批在 state 链（T-1..T-7、T-9..T-12、T-15）全部 done 前禁止开跑」）下，第一次合法批跑发生在 T-5(W6)/T-6(W7)/T-7(W8) done **之后**——而硬时序要求 T-17 落库先于 W6 开工。若门按字面辖一切 sim 批，该时序永不可满足；若门的辖域只限策略找问题批，设计必须显式说清，否则实现者无法裁决。live-verification-and-rulings.md §问题与约束引用该门时只引了「禁开实机」半句，对 sim 半句与本迭代 sim 域四批（3.4-3.7）的关系零消解；landing §3.4 的挂账豁免也只写了「实机回归项候实机窗」，未覆盖同样被门挡的批跑项——同批之内两套豁免口径不一致。
- **与 r5 §2 并行约束的相容性结论（任务书指定核验项）**：时序窗本身**与 r5 相容**——W6=T-5 进入门=W5 绿+T-4 键载体绿（卡面与 r5 §2 逐字一致），T-4 门=C1-C8 候用户裁决（T-1 wait 在案）→ 窗真实存在；W5 已于旧账闭环（检查点成果摘要），不构成第三方文件域冲突源；r5「同一时刻最多两波在飞」辖 unified-state 波间，不禁止外部卫生批插窗。**不相容的不是 r5 约束，而是该硬时序自己的依据与 state 门**。
- **发作场景**：编排者信此条在窗内强推 T-17 → 撞 state 门（批跑非法）或被迫豁免判据；或 W6 开工前一等再等一个实际上已无落码面的批，白占用关键链窗口。
- **要求**：改写为「T-17 残余（验证取证+P3 小修）先于 W6 开工」并显式裁决 sim 门辖域；删除已被 T-308 推翻的 cw_state.py 前提。

### F3【高】账本 deps 与设计排布脱节：全部阶段间关系零建边，「ready 首行派单」口径下必然违约

- **位置**：design.md §0（「按账本 deps 与文件面互斥真实排布」「依赖与复查时机显式写进阶段小节」）；landing.md 头注（「阶段间依赖 = 账本共同前置 T-33 之外的真实排布」）；账本 14 张卡前置一律仅 T-33。
- **事实**（dag.py card 逐卡核验）：landing/总纲声明的阶段间关系在账本**一条边都没有**。其中按 od-dev-progress-tracking §5 分判（「它的完成能不能由本账本一条 done 满足？能→deps」）必须建边的：
  1. **IC-2 单源依赖**：T-16 完成需 T-17 的 pad 态契约与 guard 形状 → T-16 应 dep T-17（卡面「被依赖:无」）；
  2. **IC-1 单源依赖**：T-20 方案/落码以 T-18 定谳资格面为判定基准单源 → T-20 应 dep T-18（卡面「被依赖:无」）；
  3. **账本内任务等待**：T-24 候 T-30 done、T-25 候 T-29/T-30 终态——三者皆本账本任务，属 deps 而非 cond/散文（卡面均未建边）。
  其余纯文件面互斥排序（T-21/T-22→T-23、T-24 先行等）可辩为「排序偏好不是依赖」，但 design.md §0 自称「按账本 deps …真实排布」，而账本 deps 对排序的实际贡献为零，声明与事实不符。
- **发作场景**：自主推进派单口径 = 「空出的槽照 dag.py ready 首行取下一个」。T-33 done 后 ready 会把 T-16/T-20/T-24/T-25 与其前置并行放出：T-16 在无 IC-2 契约复核下开工、T-20 抢跑继承占位件误列（strategy-qualification §关键取舍自己写的返工场景）、T-24/T-25 与 T-29/T-30 在飞面相撞。单源契约只活在 landing 散文里，机器图的防偏离承诺落空。
- **要求**：`dag.py dep` 补上述边（或编排者把「landing 排布优先于 ready 序」立为显式派单规程并记档）。

### F4【中】design.md §1 文件面冲突清单漏 2 处真实冲突——本迭代要解的问题 3 自身没做全

- **位置**：design.md §1 症状 3（冲突清单）；对照 landing §3.7/§3.8/§3.10 文件面。
- **事实**：§1 清单列了 shop.py、执行缝两文件、runner.py、engine_p1.py、doc 旧树五处，漏了：
  1. **mandate_v1/mandate.py**：T-16（landing §3.10 文件面明列「mandate.py（m3_levelup_batch 段）」）× T-18（§3.8 文件面明列「mandate.py（fuel_sell_candidates 及其调用点）」，实测 mandate.py:248）——两批都声明动它，landing 无任何串行化（§3.10 只排了 3.4 与 cond，§3.8 只排了 3.2 与实机窗）；
  2. **operations/cw_screen/cw_screen_prep.py**：T-16（执行缝入账模块子集）× T-23（§3.7 back_size 消费位）——同样未排布。
- **发作场景**：3.8 与 3.10（或 3.7 与 3.10）并行在飞——GC-1 只保「开工前一眼」，保不住两批同窗互相制造对方开工后的新 hunks；mandate.py 段落相邻（资格面与 m3 发射段同文件）时 git 层冲突直接炸。
- **缓解与定级**：停手令+编排者在飞互斥可兜底，故定中；但「文件面互斥排布」是 design.md §1 承诺的三样交付之一，交付物名不副实。

### F5【中】T-25 的 skill 本体归属仓声明错误：junction 实测指向本仓，公共仓无此 skill，「两仓两笔 commit」凭据不可满足

- **位置**：details/docs-hygiene.md §T-25「引用面同步」第 2 条与「关键取舍」第 3 条；landing §3.3 文件面（「公共仓 OneDragon-Skills 的 skill 文件（独立 commit）」）与验收凭据形式（「两仓 commit hash」）。
- **事实**（直调实测）：`.dsh/skills/sr-od-currency-war-dev` junction 目标 = `D:\code\workspace\StarRailOneDragon\skills\sr-od-currency-war-dev`（**本仓**路径）；`git ls-files skills/sr-od-currency-war-dev` 有 tracked 文件（SKILL.md 等）；公共仓 OneDragon-Skills 的 skills/ 目录只有 od-dev-* 十五件，**无 sr-od-currency-war-dev**。即 skill 本体在本仓、单源在本仓，与 AGENTS.md「SR 专属 skill（sr-od- 前缀）进本仓 skills/」一致。docs-hygiene「skill 本体在公共仓 OneDragon-Skills…路径引用修改发生在公共仓…与主仓分两笔」为事实错误。
- **发作场景**：worker 按 §3.3 文件面去公共仓找/改 skill → 找不到则停手回路由一轮；更坏：在公共仓新建同名 skill「补齐」→ 单源被 fork 成两份，恰制造本批要清的同类病。验收侧按「两仓 hash」对账永远对不上。
- **附注**：skill 在本仓被 git 跟踪，T-25 的「旧路径全仓 0 引用 grep 锁」用 git grep 天然覆盖 skill 文件（无 gitignore 盲区），该判据本身不受影响；须改的只是归属仓声明、文件面与「单仓单笔 commit + 单仓 hash」凭据口径。

### F6【中】T-13 消费接线段的数据源前提失真：效果文本注册表被当成授予计数载体，与 unified-state 效果线的接口零声明

- **位置**：details/free-refresh-onboarding.md §方案 3、§边界与验收文件面；landing §3.11。
- **事实**：详设称「授予效果字段现居 data/cw_invest_data.py（免费刷新相关字段在册）」。实测该文件在册的是 **PlazaAugment 效果文本**（固定理财/大裁员/加油站等条目，`effect='获得N次免费刷新'` 字符串），不是可消费的计数载体；src 全域无商店侧免费刷新余额/授予计数字段（grep 实测：免费刷新仅现于 data 文本与投资屏 PickEvent.refresh_slots 通道）。把效果字符串变成可对账的授予计数，属 unified-state 效果线（账本 T-9..T-12 效果批，尤其 T-11「条件判定型免费刷新效果结构化wire」）。本迭代域边界声明只说了「禁动域结构」，未声明 T-13 消费段与效果线任务的接口：计数谁产、字段居哪、效果线未落时消费段接什么。
- **发作场景**：T-13 实机窗先开（其 cond 与 T-11 无序），worker 按详设找「cw_invest_data 的授予计数字段」落空 → 停手回路由一轮；或自行在执行面造第二计数源 → 与效果线 wire 双源，恰是本批要防的病。
- **要求**：总纲补一条跨迭代接口契约（T-13 计数消费 × 效果线计数生产），或在详设内把「余额真值 = 屏读 + 授予计数」的计数源改为显式候裁项。

### F7【中】T-17 方案正本与 T-23 单源事实落在 .debug/temp/ 临时区（不入 git、易失）

- **位置**：design.md §2 IC-2/跨迭代互斥等六处引「T-280-交付报告.md」；landing §3.7 依赖引「T-322-实施-交付报告.md」；details/execution-seam §T-17「方案正本」；details/sim-baseline §T-23。
- **事实**：两文件均在 `.debug/temp/currency_war/`（实测存在；旧账 reports/ 无 T-280-交付报告，仅 reviews/ 有方案对抗审）。.debug/temp 按 AGENTS.local 是临时区（不入 git、按纪律清扫）。commit message 引 temp 报告是项目既有 practice，但把 temp 文件当作**迭代设计的方法正本**（T-17 重新交付的唯一方案依据）与**单源事实**（T-322 闸门二/三语义）承载面，寿命错配。
- **发作场景**：temp 清扫后 T-17/T-23 的落码依据只剩详设二手转述；对抗审要求「直调原文」时原文已灭。
- **要求**：设计批把两报告正本复制进迭代目录（或账本 reports/）后引用。

### F8【中】账本与设计已发生「各自演化」：T-24 扩围 note（23:59:17）未回写 landing §3.2

- **位置**：design.md §0（「设计改 → 小节改 → 账本 note/criteria 跟改，禁两处各自演化」）；账本 T-24 附注 vs landing §3.2 范围。
- **事实**：T-24 卡 2026-09-11T23:59:17 附注把清理面扩围——「正本到 .debug 悬空引用清单（文件已灭失，math_proofs/projection_contract/flow 多处）见 reports/T-30-r1.md 第 4 节，本批清理时一并覆盖」。landing §3.2 范围/判据仍是纯 ADR 悬空引用口径，未含扩围面。设计批（T-33，23:50:58 建）产出在前、账本扩围在后，回写义务未被履行——正是总纲自己禁止的双源漂移，且发生在设计定稿流程内。
- **发作场景**：worker 照 §3.2 干活漏掉扩围面 → reviewer 按 note 指针对账 → 打回一轮；或两口径各清一半，grep 锁口径失真。
- **要求**：landing §3.2 范围补扩围面（或由编排者裁决扩围改立新任务，两处之一必须动）。

### F9【中】design.md §1 声称「各任务自身的根因归层在其详设逐个给出」——六份详设零显式归层

- **位置**：design.md §1 根因归层行；details/ 六份全文。
- **事实**：六份详设无一处按「表示/约定/流程/语义」给任务级归层标注（关键字实测零命中；个别可从症状推断，如 T-17≈表示层双源、T-18≈资格语义面，「可推断」≠「已给出」）。核三的逐任务卡点「归层结论成立吗」因此无挂点；总纲声明与交付不符（写作硬规则 1 同族：写了没做的事）。
- **要求**：详设各任务节补一行显式归层，或总纲收回该句改为「归层由对抗审逐任务补判」。

### F10【低】landing 在飞面声明为会失效的现状快照，且已失真

- **位置**：landing §3.4 依赖（「四文件全部有在飞 hunks」）、§3.5 依赖（「engine_p1.py 在飞 hunks」）。
- **事实**：实测 git status——四文件中 cw_op_buy_cards.py / cw_shop_action_ops.py 干净（S1 已随 T-308 入库），仅 cw_reconcile.py / cw_state.py 有在飞 hunks（且属 T-64/T-183 退役批等他批，非 T-17 面）；engine_p1.py 干净（T-321 已入库）。GC-1 机制可自纠，但设计文档写当下树态违反无状态纪律，且这类声明会持续过期。
- **要求**：在飞面判断收归 GC-1 开工前核对（landing 只写「按 GC-1 核对」，不预写快照结论）。

### F11【低】GC-3 的「测试分层单一源」指针差一跳

- **位置**：design.md §2 GC-3；skills/sr-od-currency-war-dev/references/strategy-work.md §4。
- **事实**：GC-3 称「测试分层单一源 = strategy-work「验证」」；strategy-work §4 明文「测试分层命令…= **SKILL.md** 单一源地图「测试分层」行」——命令原文的单一源在 SKILL.md，GC-3 指到的是间接源。命令本身实测无差（GC-3 的 L1 命令与 T-321/T-298 入库笔亲跑命令逐字一致，`legacy_baseline` 标记真实在用）。
- **要求**：指针改指 SKILL.md 单一源地图行，或写「strategy-work「验证」→ 其内指针」。

### F12【低】末阶段（正本更新）无账本卡承载，README 计数口径不含它

- **位置**：landing「末阶段：正本更新」；README 进度行「阶段 0/14 done…末阶段=正本更新」；账本 T-33 卡（设计定稿任务，非正本更新任务）。
- **事实**：14 阶段↔14 卡追认映射闭合，但末阶段不在映射内、账本无对应任务。按「照 dag.py ready 派单」口径，正本更新批无卡可派，收尾义务仅由 landing 文本承载——iteration-design §3.1 的机制意图是让收尾成为「流程终点，不是记得就做」。可辩「DAG 是长出来的」（§6），故定低；建议 T-33 验收时顺手立末阶段卡（criteria 已可写：清单清零+正本一致）。

### F13【低】T-24 计数快照内嵌账本 criteria；docs-hygiene 命中面路径写法不一

- **位置**：账本 T-24 criteria「(20处/11文件)」；details/docs-hygiene.md §T-24 命中面。
- **事实**：实测 `git grep -E 'ADR-0648|…|0653-m2b'` = 25 处/12 文件（较记账时点 +5/+1，另一在飞清理批会继续移动该数）。landing §3.2 用「约 20 处/11-12 文件…以开工时 grep 重跑为准」已免疫；账本 criteria 的括号计数是会过期的第二抄本（机械判据「0 命中」本身不受影响）。另 docs-hygiene 命中面写「mandate_v1/criteria/contracts.py、criteria/equipment.py、criteria/__init__.py」——后两者缺 mandate_v1/ 前缀，实际同目录，读者需自行补全。

## 二、攻过未破角度清单（证据在案，均未破）

1. **覆盖面与计数**：T-13/T-14/T-16..T-27 = 14 项与 landing §3.1..3.14 一一对应；T-15 排除正确（观察架构域）；T-19 无详设走总纲内联设计合法（iteration-design §2.1 单文档方案）。
2. **criteria/cond/优先级逐字段对账**：14 张卡 criteria 原文、cond 复查时机、优先级数字与 landing 各阶段小节逐条一致（含 T-14 七条、T-23 四条全量核对）。
3. **T-28 deps 声明**：T-13/T-14 确在 T-28 deps 面（卡面实证），free-refresh「下游」句准确。
4. **代码与文档锚点大面实测命中**：shop.py:2728-2729 seat_recoverable 申报、refresh.py:196-199 代理偏宽申报（逐字）；cw_economy.py BASE_INCOME:383/REWARD_BASE_GOLD_BY_ROUND/streak_gold:48/利息封顶；cw_equipment_data.py:53 宝钻官方效果原文逐字命中；mandate.py:248 fuel_sell_candidates；cw_state.py:153 is_item_slot；economy.md §10/§11 与 §11「待玩家确认」⚠️ 段；board_structure.md §备战栏（L47）/§上限 9 格（L25）；ADR-0623 决策 3；T-162 入库笔 1c65941a 真实存在且语义相符。
5. **T-19 死引用前提亲证**：`merge_round_rows` 在 src 零定义（grep 实测），ledger_hooks.py:10 仅注释提及，review_skeleton.py:47 导入必 ImportError；修法两分支（改现居路径/最小语义等价实现）覆盖两种现实，判据「亲跑复现通过」可机械验收。
6. **T-25 迁移树碰撞排查**：目标址 docs/develop/sr_od/application/currency_war/ 现存仅 changes/，与旧树 7 子目录+2 文件零名称冲突；git mv 保历史、旧路径 0 引用 grep 锁方向可行（skill 文件在本仓被 git 跟踪，git grep 无盲区——归属仓声明本身的错误见 F5）。
7. **r5 §2 波次并行约束相容性**（任务书指定项）：见 F2 结论——窗真实、约束不冲突，败点在依据与 state 门。
8. **IC-5 / GC-2 / GC-4 与 AGENTS.md 一致性**：ADR 用户命令制、逐文件点名 add、禁改 ADR 历史原文，均与 AGENTS.md/AGENTS.local 条文对齐。
9. **阶段小节七件齐**：15 个小节（含末阶段）七件俱全；README 结构合模板；无过程叙事措辞（「经方案对抗审修订版」属来源标注非过程叙事）。
10. **治本核验（核三）**：各批修法对根——T-17 单一源化三层（根治播种双源）、T-18 补生产资格面（此前只修假环境侧=症状侧）、T-20 代理收窄至单源、T-21 对权威源校准、T-22 容忍语义定谳、T-23 追平容器真值；本迭代自身即批次化缺口的架构级收编，无「逐件修第 3 件」违例。唯归层标注缺失见 F9。
11. **T-24 口径与在飞实践兼容**：T-298（cffb85488）已入库的悬空清理实践（结论在则语义化/纯指针删）与 IC-5 口径一致；「开工时 grep 重跑为准」条款免疫命中面漂移（实测 25 处/12 文件）。
12. **域边界声明自洽**：unified-state/unified-observation 只点状修复+停手令、IC-6 屏幕读面边界与 AGENTS.md screen_info 纪律、obs/ 只动值计算的 T-23 声明，互相无矛盾。

## 三、结论与阻断摘要

- **发现计数**：13 项——高 3（F1/F2/F3）、中 6（F4-F9）、低 4（F10-F13）。
- **阻断摘要**：F1（T-17 三层方案已由旧账 T-308 于 bd27989d4 入库，迭代文档零提及，阶段范围须按「验证+P3 残余+实机候窗」重写）；F2（「T-17 先于 W6/W7/W8」引用不支撑主张、cw_state.py 前提已被交付推翻、与 sim state 门字面相抵，须显式裁决并改写）；F3（账本 deps 零建边，单源契约只活在散文里，ready 首行派单必违约）。三项均在 design.md §2/landing §3.4/账本映射的定稿关键路径上，按 iteration-design §6「未决 = 停在对抗审中」，攻击未收敛，不定稿。
- 其余 10 项为定稿前应顺手修的偏差（F4-F9 建议随 F1-F3 一并处理；F10-F13 低 cost，其中 F5 须在 3.3 开工前修正，防 worker 误改公共仓 fork 单源）。
- 攻击面留痕：三核均已过——核一（无前提：锚点/前提/依据逐条直调，F1/F2/F5/F6/F10 即战果）；核二（规范遵循：iteration-design 硬规则三条+od-dev-progress-tracking §5+AGENTS.md 纪律，F3/F8/F9/F11/F13 即战果）；核三（治本：各批修法对根成立，归层标注缺口见 F9）。

## 四、裁决记档（设计批 T-33 修订轮，2026-09-12）

> 13 项发现逐条裁决：**全部成立，无「不成立」记档**。修订已按任务书落盘至 design.md / landing.md / README.md / details/ 六份（attack.md 历史发现未改动，仅追加本节）；关键事实由修订批独立复核（bd27989d4 入库笔、T-280 报告 §③ 原文零 W6/W7/W8 字样、junction 目标本仓、cw_invest_data 效果文本、grep 25 处/12 文件均亲验一致）。逐条处置位置：

| 发现 | 裁决 | 修订位置 |
|---|---|---|
| F1 | 成立 | details/execution-seam-projection.md §T-17 按 T-308 后世界态全节重写（症状改历史记档、锚点/先例/改动面校正、残余四件清单、禁重做已入库面）；landing §3.4 重写为残余收尾批（criteria 括注 T-308 兑现状态）；design.md §0 状态/正本落盘声明、§1 症状 3 校正、§2 IC-2 按契约已入库改写；README 文档节补 T-308/bd27989d4 引用 |
| F2 | 成立 | design.md §2 跨迭代互斥改写「T-17 残余修复先于 W6」+ 废止旧主张（引用不支撑 + cw_state.py 前提被推翻）+ **编排者裁决原文照录** + r5 §2 相容性结论；landing §3.4 依赖行同步；live-verification §问题与约束补 sim 半句与 3.4 取证段挂门 |
| F3 | 成立 | design.md 新增 §3 账本依赖边清单（8 条边 + 分判依据）；landing 各阶段「依赖」字段逐条标注「边见 design.md §3」一一对应；落账 = 账本动作申报 §3.1（编排者执行） |
| F4 | 成立 | design.md §1 症状 3 补 mandate.py（T-16 m3_levelup_batch 段 × T-18 fuel_sell_candidates 段）与 cw_screen_prep.py（T-16 修点子集 × T-23 back_size 消费位）两处；landing §3.8/§3.10 依赖行互加 mandate.py 互斥；strategy-qualification §T-18 约束同步 |
| F5 | 成立 | docs-hygiene §T-25 引用面第 2 条归属仓改本仓 skills/sr-od-currency-war-dev（junction 单源，公共仓无此 skill）；关键取舍改「单仓单笔」；landing §3.3 范围/文件面/验收凭据改单仓单笔 commit + 单仓 hash |
| F6 | 成立 | design.md §2 新增 IC-7（T-13 计数消费 × 效果线计数生产，计数载体归 unified-state 效果线 T-11 wire）；free-refresh 方案 3/文件面/关键取舍按「效果文本 ≠ 计数载体」校正；landing §3.11 范围/依赖同步 |
| F7 | 成立 | 两报告正本已复制进 details/sources/（附溯源 README，定稿批当场落盘消易失窗口）；design.md §0 正本落盘声明统一指落盘正本；landing §3.7 依赖与 sim-baseline §T-23 改引落盘正本；正本更新清单增末阶段核对条 |
| F8 | 成立 | landing §3.2 范围补扩围面（正本到 .debug 悬空引用清单，清单 = reports/T-30-r1.md 第 4 节）；docs-hygiene §T-24 增「扩围面」条同口径 |
| F9 | 成立 | 六份详设 13 个任务节全部补「根因归层」行（T-16/T-17 见 execution-seam，T-18/T-20 见 strategy-qualification，T-21/T-22/T-23 见 sim-baseline，T-13 见 free-refresh，T-24/T-25 见 docs-hygiene，T-14/T-26/T-27 见 live-verification）；T-19 归层补进 design.md §2 内联设计；design.md §1 归层行改为指认显式挂点 |
| F10 | 成立 | landing §3.4/§3.5/§3.7 在飞面快照声明收归「GC-1 在飞面开工前核对（不预写快照）」；§3.2 同步措辞 |
| F11 | 成立 | design.md §2 GC-3 测试分层单一源指针改指 sr-od-currency-war-dev SKILL.md「单一源地图·测试分层」行（strategy-work「验证」降为其下游指针） |
| F12 | 成立 | 末阶段卡账本动作申报 = design.md §3 第 2 条（dag.py add 命令草案，deps = 全部落地阶段）；landing 末阶段小节补「账本承载」声明 |
| F13 | 成立 | 账本动作申报 = design.md §3 第 3 条（T-24 计数勘正 note：定稿时点实测 25 处/12 文件）；docs-hygiene §T-24 命中面路径前缀补全（mandate_v1/criteria/{contracts,equipment,__init__}.py）与计数快照标注 |
