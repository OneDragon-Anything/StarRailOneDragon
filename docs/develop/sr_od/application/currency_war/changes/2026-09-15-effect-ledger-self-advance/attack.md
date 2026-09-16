# 设计对抗报告:效果账本自推进迁移

> 攻击规范:`docs/develop/harness/iteration-design.md` §7(三核)/§5(写作硬规则三条)。
> 所有行号为 2026-09-15 攻击时工作树实测;被攻击文本 = 同目录 design.md / landing.md / README.md。

## 结论

**打回**:两处致命——①金结算参数源未定且自然实现(照抄现块读 `bs.node` 镜像)在 0q 位面过渡/弹窗腿推进场景读到**上一节点**的 (plane, round, kind),产出错窗金结算 logic 写入;②`effective=None` 时"管线段无条件调用"落 `advance_node(None)` 无条件推进,设计的"账本内置去重为闸门"主张对 None 结构性不成立,且现码 `cw_loop.py:1895-1899` 的显式禁令被静默废除——按现稿实施会产出错误金面与余期行为。

## 发现清单

### F1 金结算参数源未定,自然实现读陈旧节点镜像 → 0q/弹窗腿场景错窗金结算(致命)

- 位置:design.md §2 方案 1.d;landing.md 3.1 判据②
- 问题:design 1.d 只指定"以提供方聚合参数调 `settle_node_boundary_gold`",**plane / round_num / node_type / streak 四个实参的来源通篇未定**。设计在闸门条件里唯一写的节点读口是 `self.node.value`(即观察镜像),实现者自然照抄现块(`cw_loop.py:1949-1959`:plane/round/kind 全取自 `_nd_tick = _bs_tick.node.value`)。但四腿(备战腿/弹窗腿/0q 腿)只写 `node_ord`/`node_hist_ord`,**不写 `bs.node`(NodeKey)镜像**(`cw_game_state.py:3137/3176/3254`);镜像由漏斗在前序行刷新(`cw_observation.py:2508-2528`,且弹窗帧的进度读数是缓存 c = 上一节点)。于是:
  - **0q 位面过渡**(实路径:boss 备战帧已按新时点结算 boss 收入 → boss 战 → 结算写 settlement → `_note_branch_screen('货币战争-位面过渡')` 进 0q 腿,`cw_loop.py:1507-1508/1837-1838`):推进到 (p+1,1) 时 `node.value` 仍是 (p,9,'boss'),闸门五条件**全过**(settlement=killed True、streak 在场、kind='boss' 可知、提供方已注册)→ 以 `reward_base_gold(p,9)+boss 分支` **把 boss 节点收入再结一遍**,且真节点 (p+1,1) 的收入因账本去重已消耗永不再结。每个获胜离位面都触发一次错误金面 logic 写入。
  - **0n 商店面板块自动弹形态**(弹窗腿,`cw_game_state.py:3036-3040`):0n 不在类型直定映射(`SCREEN_NODE_TYPE_DIRECT` 无 0n,`:218-222`),推进到 N+1 时 `node.value` 仍为 N 的缓存键 → 同型错窗。
  - 根子上,设计对 advance 键落实了 R5 规则六"键源切派生层"(用 `effective_node_ord`),但**结算参数没有切**——(plane, round) 应由 `effective` 经 `_node_key_for_ord` 反解(`cw_game_state.py:3183-3189`)而非读镜像,design 未写。
- 依据:`cw_game_state.py:3036-3049`(腿只写 node_ord)、`cw_game_state.py:3219`(仅类型派生写 bs.node)、`cw_observation.py:2508-2528`(镜像=帧进度读/缓存)、`cw_loop.py:1894/1949-1959`(现块参数全取镜像)、`cw_economy.py:515-531`(node_type/plane/round 直接进收入分支)、`node-derivation.md` §3.3 规则六"键源切派生层"。

### F2 effective=None 无条件推进:设计的闸门主张对 None 不成立,现码显式禁令被静默废除(致命)

- 位置:design.md §2 方案 1.a("账本内置去重……为闸门,管线段无条件调用")
- 问题:`advance_node` 的去重守卫是 `node_ordinal is not None and node_ordinal == self._last_tick_node`(`cw_effect_inventory.py:346-348`)——**None 直接绕过去重**并无条件递减全部 N_NODES 条目、返回 advanced=True(`:349-360`,None 也绕过"登记当节点不推进"守卫)。生产上 `observe_screen_context` 在节点派生前就会被调用:开局链分支写点(简报/投资环境/等待1-1,`cw_loop.py:1537-1567`,不带 phase_round、节点未派生)与漏斗开局帧。设计规定"无条件调用"并以去重为唯一闸门 → 这些帧每次都无条件推进。现码对 此有**逐字禁令**:`cw_loop.py:1895-1899 "advance_node(None) 守卫……禁把「未观察」当「真进节点」无条件推进虚耗余期/虚累余额"`,该守卫随 tick 块删除而被设计静默废除,行为变化申报未提。当日注册表侥幸无害(在册词缀三条无 N_NODES 型、账本空时 advanced=True 的下游动作皆 no-op),但"接下来 N 个节点"类卡词是注册表的支持形态,任何此类条目在节点派生前登记即错误扣减余期、节点 1 双发刷新余额。landing 3.1 判据④只测"同帧同序幂等",未测 None 帧,该缺陷可带绿入库。
- 依据:`cw_effect_inventory.py:323-360`(None 旁路去重与登记守卫)、`cw_loop.py:1893-1901`(现码 None 禁令)、`cw_loop.py:1029-1032`(`_note_branch_screen` 无 phase_round 观察)、`cw_observation.py:2682-2685`(漏斗随分派观察)。

### F3 依据失实两处:行号锚陈旧 + 章节指向不存在(重要)

- 位置:design.md §2 方案 1.a 依据;§0/§1 依据
- 问题:
  1. design 1.a 标注"`cw_effect_inventory.py` §240-254(同节点去重与「登记当节点不推进」守卫在 inventory 内)"——**实址 240-254 是登记端代码**(`_register`/`register_strategy`);去重守卫实址 `:346-348`,守卫全文在 `advance_node :323-360`。该陈旧锚系从 `effect-domain.md:203`(正本自身行号快照已漂移)转抄,未对真实文件核对——正是硬规则 1 卡点防的事故。
  2. design §1 依据"「目标态在 _swap 派生管线内」"标注出处为 `effect-domain.md` §节点推进触发的效果推进段——**该章节在 effect-domain.md 不存在**(全文 grep 无 `_swap` 派生管线目标态表述);此目标态实际住 `node-derivation.md` §3.3 规则六(v3.8-中-1,`node-derivation.md:302-313`)。§0"承接 effect-domain.md(§节点推进族)记载的目标态"同误:effect-domain §节点推进族(`:281` 起)是逐效果规格组,非迁移目标态。
- 依据:`cw_effect_inventory.py:238-254 vs 323-360`、`effect-domain.md:199-227`(§7.3 全文)、`node-derivation.md:302-313`(规则六原文)。

### F4 引用的目标态含"迁移三面",设计只做两面,"计数器退役"未做也未申报不解决(重要)

- 位置:design.md §1 根因归层/§2 方案;对照 §1 明确不解决
- 问题:设计自己引用的目标态(node-derivation.md 规则六 v3.8-中-1;strategy-env-impacts.md:97 同文)明确迁移三面 = **①驱动时点 ②键源切派生层 ③计数器退役**,并指认现态病灶含"双权威窗(派生 hist 守卫单调 vs tick 键镜像现读)"。设计做了①②,却把 `_last_tick_node` **升格为管线段的主闸门**("账本内置去重为闸门"),计数器不退役——双权威窗换形存续(派生 hist 去重键 vs 账本内部计数器,两套去重可分叉:未来"权威降位重锚"落码时 hist 回退而计数器不回退,效果推进自此永久拒动)。"明确不解决"清单未列计数器退役 = 既不治本也不申报缓征,违反核三"说不清治本 = 打回"的申报义务。
- 依据:`node-derivation.md:305-311`(迁移三面原文)、`strategy-env-impacts.md:97`(同文)、design.md §2 方案 1.a。

### F5 「kind 可知」未定义,且该闸是现码没有的新增闸,"保守闸语义与现值一致"申报不实(重要)

- 位置:design.md §2 方案 1.d
- 问题:①"kind 可知"无定义:NodeKey.kind 有继承机制(漏斗 kind 未读帧继承现值合成新键,`cw_observation.py:2515-2527`),'' 与继承值算不算"可知"未定,实现者须自行拍板(硬规则 2 违例)。②现码金结算闸门只有 `_nd_tick is not None ∧ settlement ∧ killed=True ∧ streak`(`cw_loop.py:1942-1945`),**没有 kind 闸**——未定型节点现在照常结算(round_start_income 的 else 分支按 combat 落袋,`cw_economy.py:528-531`)。设计新增 kind 闸后,kind 不可知节点从"按 combat 结算"变"跳过"——这不是保守 no-op,是**收入语义变化**,与 design 1.d"保守闸语义与现值一致"的申报直接矛盾,行为变化申报节也未列。
- 依据:`cw_loop.py:1940-1960`(现闸无 kind 条件)、`cw_economy.py:515-531`(分支派发与 else→combat)、`cw_observation.py:2509-2514`(kind 继承机制)。

### F6 生产注册点二义,恢复链窗口未定义 → 恢复局可能全程静默跳过金结算(重要)

- 位置:design.md §2 方案 2;landing.md 3.2 文件面
- 问题:design 说"生产注册 = ctx 级一次性注册",landing 3.2 说"生产注册点(ctx 级一次性注册,**开局链初始化处**)"——两说是两个不同的挂点。若注册真挂开局链初始化:恢复接管局不走过开局链(恢复检测在 loop 内,`cw_loop.py:1036-1054`),提供方全程缺位;design 规定"未注册 = 金结算跳过"且无告警 → 恢复局整局节点边界金静默不结。现码无提供方(loop 直调 aggregate_economy,`cw_loop.py:1933-1948`),恢复局照常结算——这是一条未申报的行为回归面。若注册挂 ctx/app 级则无此窗口,但设计没有排除开局链读法。
- 依据:design.md §2 方案 2 vs landing.md 3.2 文件面(两处表述)、`cw_loop.py:1933-1948`(现码无提供方依赖)、design.md §2 方案 2"未注册或返回 None = 金结算跳过"。

### F7 3.1→3.2 双驱动共存窗口未分析:弹窗腿形态下双发金结算(重要)

- 位置:landing.md 3.1/3.2(阶段划分与依赖);design.md 行为变化申报
- 问题:3.1 接入管线段后、3.2 删 tick 块前,生产同时存在两个驱动。稳态下侥幸安全(loop tick 读镜像恒比管线慢一拍,同序撞账本去重),但**弹窗腿先推进形态破防**:结算后 0n 自动弹先被采到(漏斗)→ 管线推进 N 并结算 N;下一备战 pass 的 loop tick 读镜像缓存 c = N-1 → `advance(N-1)` 与 `_last_tick_node=N` 不等 → **再推进一次**(双扣余期+双发刷新余额),且闸门全过 → 以 N-1 的键**把 N-1 的收入再结一遍**。landing 无"3.1 落地后不得跑实机局直至 3.2"类守卫,design 行为变化申报亦无此窗口分析;两阶段按账本结构可间隔任意时长交付。
- 依据:`cw_loop.py:1894`(tick 键源=镜像)、`cw_game_state.py:3171-3172`(弹窗帧进度读=缓存 c=上一节点)、`cw_effect_inventory.py:346-348`(异序即再推进)、landing.md 3.1(范围明确"不删 cw_loop 块")。

### F8 landing 3.3 哨兵交接申报失实:金结算成功日志随块消失未申报(重要)

- 位置:landing.md 3.3 完成判据
- 问题:3.3 申报"本迁移后账本推进不产生新日志节奏变化(到期留证 warning 行保留)"。但 tick 块里还有**金结算成功 log.info**(`cw_loop.py:1961-1966`,"[cw-loop] 节点边界金结算 logic 写入(branch=… total=…)"),随块删除;design 管线段规格(1.b 只保留到期 warning、1.d 无任何日志)不重建该行——日志节奏**有**变化,哨兵交接核对建立在不实前提上。现块 best-effort 外壳的 `log.warning('[cw-loop] 效果账本 tick 失败…')`(`:1968-1969`)同理消失,design 1.f 只写了新段的 except 路径。
- 依据:`cw_loop.py:1961-1969`、design.md §2 方案 1.b/1.d/1.f。

### F9 landing 3.1 验收判据盲区:致命场景零覆盖,可全绿放行 F1/F2/F5(重要)

- 位置:landing.md 3.1 完成判据①-⑤
- 问题:五条判据覆盖了备战帧推进、金结算基本形、提供方缺位、同序幂等、killed=False——但① **0q/弹窗腿推进时结算参数正确性**(F1 的错窗场景)无判据;② **effective=None 帧行为**(F2)无判据;③ **kind 未定型/继承值行为**(F5)无判据。按此验收,两处致命缺陷可测试全绿入库。另判据②措辞"金面 write_logic 增量 = 收入三支+财富"未锚 `NodeBoundarySettlement.written/branch` 等现成验收载体(`cw_effect_inventory.py:1067-1077`)。
- 依据:landing.md 3.1 判据清单、design.md §2 方案 1(无对应边界条款)。

### F10 "设计 §8.4「备战帧观察后调用」"为悬空引用(次要)

- 位置:design.md §2 行为变化申报第一条
- 问题:"即设计 §8.4「备战帧观察后调用」的本意"——全仓无此文:changes/2026-09-06-c1-direct-core-entry/design.md 的 §8.4 是 v3 修订总表,fields.md §8.4 是 payload 域;该用法块只存在于已删的旧设计件(cw_loop.py:1886 注释同引"设计 §5.1/§8.4",同悬空)。引用不可解析 = 依据无法核对(硬规则 1);主张本身另有 effect-domain §7.3/cw_loop 注释旁证,故降为次要。
- 依据:grep 全 game_state+changes 无「备战帧观察后调用」章节;`node-derivation.md:8`(原遥测设计件已删记载)。

### F11 outer_loop.md 正本更新清单措辞会误伤合并步(次要)

- 位置:landing.md 正本更新清单第 3 条
- 问题:"§3 备战表面默认分支进入序中「效果账本节点 tick」步删除(步骤随删重排)"——实文该步是**合并步**:"GameState 心跳观察者采样 + 效果账本节点 tick"(`outer_loop.md:91`)。按字面整步删除会把心跳采样(观察断流诊断的哨兵载体)一并抹掉;清单应写"步内效果账本 tick 半句删除、心跳采样保留"。
- 依据:`outer_loop.md:86-99`(§3 进入序全文)。

### F12 frame 证据串与 streak 归一未钉(次要)

- 位置:design.md §2 方案 1.c/1.d
- 问题:①1.c 写 `grant_effect_node_refresh_balance(self, frame=…)`——省略号未定值;现值为 `f'p{plane}-r{round}'`(`cw_loop.py:1918/1959`),且 0q/弹窗腿场景 frame 取哪个键(镜像还是派生序)与 F1 同源,未定。②现码 streak 入结算前做 `int(max(0, _streak))` 归一(`cw_loop.py:1954`;streak 字段带符号,`cw_game_state.py:2504`),设计未申报该归一是保留还是改传原值。
- 依据:`cw_loop.py:1918/1954/1959`、`cw_game_state.py:2504`。

## 附:攻击指派六方向的独立推演结论

1. **同节点多次观察(弹窗插播/关店重开)**:同序重复观察被账本去重挡住(非问题);0n 重入被 prev 守卫拒绝(`cw_game_state.py:3036-3037`,备战系 prev ∉ 守卫族)。真正的洞不在重复触发,在 None 帧与异序帧(→F2/F7)。
2. **恢复局**:弹窗腿禁用(`cw_game_state.py:3164-3166`)、新容器 settlement/streak 为 None → 首节点金结算跳过,与 loop 现值一致,无多记少记(非问题);但提供方若挂开局链则恢复局全程不结算(→F6)。
3. **与同管线其他写入的时序**:效果段在类型派生后、方法返回前,先于本节点任何动作 op,"先推进后选卡"保持;金结算 logic 写随后受观察覆盖辖,失配显影机制不变(非问题)。settle 读的金基座 = 本帧镜像刷新前的现值,与现块时点等价。
4. **提供方未注册窗口**:开局链初始化前无 session 即无容器即无观察,窗口良性;恢复链窗口见 F6(是问题)。
5. **node_type 分支派发**:`round_start_income` 对未知/空 kind 落 **else→combat 分支照发收入**(`cw_economy.py:528-531`),所以"跳过"不是保守 no-op 而是语义变化;且现码本无 kind 闸(→F5,是问题)。
6. **`project_effect_capacity` 消费面**:全仓 grep(kernel 定义、docstring 引用、cw_loop 调用之外无生产消费)证实消费面仅 loop,landing 3.2 的 grep 零残留判据可达(非问题)。

## 已核对无误的依据清单

| 设计标注 | 核对结果 |
|---|---|
| `cw_game_state.py:2973-3059`(observe_screen_context 管线与四腿) | ✓ 实址吻合:上下文对 3020-3026、顶栏层 3028-3029、四腿 3032-3049、类型派生 3053-3059;"管线段序"契约与实构一致 |
| `cw_game_state.py:816-831`(_STATE_JOURNAL_SINK 注册模式先例) | ✓ 模块级单槽 + set 注入口,先例成立 |
| `cw_game_state.py:2748`(best-effort 不毒化写入链) | ✓ 原文在;注:先例落 `log.debug`,design 1.f 规定 `log.warning`——自定选择非失实,但"同纪律"表述下级别差异未申报 |
| `cw_game_state.py:3095`(effective_node_ord 读口) | ✓ 3095-3106,max 派生计算非存储,None 安全 |
| `cw_effect_inventory.py:1055-1110`(节点边界窗 + 金未读自跳契约) | ✓ 两窗结构 1054-1064;金未读整拍跳过恰在 1107-1110;`settle_node_boundary_gold` 签名 1080-1085 |
| `cw_loop.py` 备战分支效果段"约 70 行" | ✓ 实址 1885-1969(85 行含注释;纯代码约 60 行,"约"可接受);五动作逐行核对一致:advance 1901(含 None 守卫 1895-1899)、到期留证 warning 1902-1905、刷新发放 1915-1919、金结算保守闸 1940-1960、容量重锚 1967(不限 advanced);另有金结算成功 log.info 1961-1966 设计未迁移(→F8) |
| `cw_loop.py` 效果段"全仓唯一生产调用点" | ✓ grep 全 src:advance_node/grant/settle/project 生产调用仅 cw_loop;其余为 kernel 定义与 doc 引用 |
| `node-derivation.md` §①(四规则组、与 advance_node 同坐标系) | ✓ :62-78,"节点身份 = (plane-1)*9+round_num(与效果账本 advance_node 同坐标系)" |
| `node-derivation.md` §3.3 定义基准(R5) | ✓ :161-180,"节点推进 = 进入该节点的备战画面(商店开);补给特例;投资策略卡计数起点 = 拿卡后第一次进备战" |
| `cw_effect_inventory.py:240-254`(去重与登记守卫) | ✗ →F3(实址 346-348 / 323-360) |
| `effect-domain.md` §节点推进触发的效果推进段 | ✗ →F3(目标态实住 node-derivation.md §3.3 规则六 :302-313) |
| `strategy-env-impacts.md` 效果桥条目(现态挂点/目标态) | ✓ :97 与正本更新清单第 2 条描述一致(该条目含"迁移三面"字样,佐证 F4) |
| `outer_loop.md` §3「效果账本节点 tick」步 | ✓ 存在,但为合并步(→F11) |
| `game_state/README.md` 条件同步项 | ✓ 合理:现有索引行无效果推进挂点直述,:37 派生序描述迁移后仍真,条件项可不清零也可同步 |
| landing 3.1 测试文件路径 | ✓ `sr-od-test/test/sr_od/application/currency_war/test_cw_game_state.py` 存在 |
| 提供方返回形状 tuple[float, int, int\|None] | ✓ 与现块消费的 aggregate_economy 三字段一致(`cw_investments.py:741-780`;win_reward_mult 取 max、cap 取宽语义现值) |
| `board_state_of` 失用 import 备注 | ✓ 达标臂自有 import 在 `cw_loop.py:1992`,备注准确 |
| 规范遵循(核二) | 四节齐、landing 阶段七件齐、无过程叙事措辞、README 模板合规;违例集中在硬规则 1(F3/F10)与硬规则 2(F1/F2/F5/F6/F12 的未定语义) |
| 治本(核三) | §1 归层(流程层、编排住错层)成立——R5 规则六目标态与漏斗/loop 双写点实证;§2 对①②治本、③未收口(→F4);外溢面自成迭代符合 iteration-design.md §1.1,非逐件修违例 |
