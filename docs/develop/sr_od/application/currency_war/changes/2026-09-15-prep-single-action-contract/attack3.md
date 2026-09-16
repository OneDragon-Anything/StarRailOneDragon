# attack3 —— 无前提对抗审查报告(第三批)

> 审查对象:本目录 README.md / design.md / landing.md;`src/sr_od/application/currency_war/strategies/impl/cw_strategy.py::decide_prep_screen` docstring(工作区未提交修改);`docs/develop/sr_od/application/currency_war/strategy-docs/README.md`「策略↔流程契约」行(工作区未提交修改)。
> 纪律:数值/口径/引文/码点全部直调复核(代码体、正本文档、测试仓、skill references);未读同目录 attack.md / attack2.md(3.3 闭域 grep 机械扫过 changes/ 全树时其行文出现在命中列表中,未作为本报告任何发现的依据)。
> 结论:**高危 0,中危 6,低危 7**(F13 为范围外既有缺陷,随录)。对象 2(docstring as-built 十句)与对象 3(策略↔流程契约行)**零发现**。

## 发现清单

### F1(中)3.1 验收 grep 关键词与设计自身的替代文本冲突,验收凭据按字面不可执行

- 位置:`landing.md` L14(关键词集 `取首项 / 空批 / 契约 § / list[CwAction] / 结算惰性 drain`,作用于本批三文件 diff 行,要求零命中)vs `design.md` §2.2 码块注释、§2.3、landing 清单 #6。
- 直调事实:
  - design.md §2.2 拟改码块(L58)注释为「`# None = 本帧无动作可发(原空批分支逐义替换)→ …`」——**新增 diff 行自带「空批」**,完成判据同时要求「消费端代码形状与 §2.2 码块一致」与「diff 行『空批』零命中」,两条互斥,实现者必违其一;
  - §2.3 要求 bridge docstring 按「边界取首项」语义改写,而新 docstring 表述该机制的自然措辞(设计的自用语言)就是「取首项」——`取首项` 零命中要求同样存在碰撞风险,设计未给新 docstring 的定稿文本;
  - landing 清单 #6 对 op-layer L21 的替换文本只改备战域半句,商店域半句「空批已由 CloseShop 终结取代」的「空批」措辞是否随改未定稿(`…` 省略)——该行在清单内,改后若保留「空批」则 3.3 闭域检查(清单外零命中)对其仍命中,实现者需自行扩权改写。
- 修正方向:①§2.2 码块注释改为不含「空批」的定稿文本(如「None = 本帧无动作可发,交回外循环重观察」);②给 bridge 新 docstring 关键句定稿文本,或把 3.1 关键词改为「作用于行为语义面」的更窄集;③清单 #6 写明商店域半句的定稿措辞(建议「与商店域(该通道已由 CloseShop 终结取代)」)。

### F2(中)3.3 闭域检查漏挂 3 处必命中点 + 1 处语义无关误命中未豁免,「清单外零命中」按字面不可满足

- 位置:`landing.md` L36(完成判据)与「正本更新清单」L43-53。
- 直调事实(本报告按清单同款关键词 `首项|空批|list[PrepAction]` 全树重跑,排除 changes/ 与 flow/README §2.2 历史注节后的清单外命中):
  - `game_state/action-logic-state.md` L163:「备战环逐帧取决策输出**首项**执行」——活正本句,清单未挂;
  - `game_state/logic-updates/prep-executor-actions.md` L13:「备战环逐帧取决策输出**首项**执行」——同型,未挂;
  - `strategy-docs/02_mandate_layer.md` L82:「逐帧取最优**首项**」——同型,未挂(该行更深的问题见 F3);
  - `proofs/validations/P51_V3_REBUILD.md` L391:「R31-2 **首项**=1」——语义无关(拟合器标签规则,非动作选序),闭域检查必命中但正确处置是豁免而非改写;豁免清单只有「历史注节与 changes/」两例外。
- 影响:三个真实漏挂 = 实现者在 3.3 阶段临场决定改法(违背「实现者无需再设计」);一个误命中 = 机械判据按字面必然红,验收凭据失去裁决力。
- 修正方向:清单补 3 条目(改法 = 「取首项」句统一为单动作/None 口径);3.3 完成判据补 `proofs/` 目录豁免(或点名该行豁免 + 理由「非动作选序语义」)。

### F3(中)正本间矛盾遗留:02_mandate_layer.md「策略器 = 全函数…永不返回 None」与本迭代备战 None 通道直接冲突,且机械网对此盲

- 位置:`strategy-docs/02_mandate_layer.md` L82(「**策略器 = 全函数**(f(期望态) → 动作,**永不返回 None**;『无动作可做』的表达 = 直接选终结 op)」)vs `design.md` §2.1(备战入口返回 `CwAction | None`)、`landing.md` 清单(无该文件条目)。
- 直调事实:该句是 as-designed 现行态的规范级主张,无分域限定;本迭代落码后备战契约合法返回 None,正本间直接矛盾。3.3 闭域关键词(首项/空批/list[PrepAction])对「永不返回 None」全部不命中——即使清单补挂了该行的「首项」半句(F2),None 半句仍会以「同句已改」的错觉漏网。姊妹句 `screens/op-layer.md` L21 改写后「策略器全函数」统领表述保留,靠同句分域从句调和,而 02 无从句。
- 修正方向:清单为 02_mandate_layer.md L82 增设条目,把「全函数」改写为分域表述(商店 = 全函数恒可用 CloseShop;备战 = 恰一动作/None,None = 本帧无动作合法交回);op-layer §1.1 的统领句同步评估是否加分域限定语。

### F4(中)实机烟雾判读锚点 2 依据失真:`cw4_counters` 不存在 `prep_*` 键族

- 位置:`design.md` §2.6 锚点 2(L116:「备战发射分键分布(`cw4_counters` 的 `prep_*`/`emitter_*` 键)」)。
- 直调事实(全仓计数键枚举):`emitter_*` 键族存在(entry.py:`emitter_post_truncation_dropped`/`emitter_unknown_action_truncated`/`emitter_conditional_truncated`);**`prep_*` 计数键零存在**——`prep_box`/`prep_tome`/`prep_spheres` 是 `Emitted.reason`(路由标签,非计数键),`prep_clean`/`prep_row` 是相位/账本来源标注。备战发射相关计数键的真实家族是异构前缀:`deploy_emit_*`/`deploy_exec_*`(部署)、`t1_interest_prep_emit`/`wanted_leg_*`/`m1p_fired`/`sphere_defer_*` 等。
- 影响:判读者按稿 grep `prep_*` 得空集,锚点 2 要么不可执行、要么被临场收窄成只剩 `emitter_*`,基线比对口径失真。
- 修正方向:锚点 2 点名真实键族清单(或改为「备战域发射相关分键全集,清单 = emitter_* + deploy_emit_*/deploy_exec_* + t1_interest_prep_emit + wanted_leg_* + m1p_* + sphere_defer_*,以 3.1 改动前的 journal 基线实际出现键为准」)。

### F5(中)「mandate_v1 现状恒不返回空」过强:条件续复检首位置空返回边未排除

- 位置:`design.md` §2.1 依据 2(L40)。
- 直调事实:`entry.truncate_frame_stable` 的条件续分支对首位 `SellBench`/`DeployMove` 做 `bench_slots` 名-槽复检,复检失败即 `_cut()` 返回**空 list**(entry.py L309-320;bridge 恒供给 `bench_slots`,L288-290)。该复检正是为真实缺陷类而设(R196 症5),属活的防御边——设计只论证了「unknown 首位边不可达」,未覆盖此边,「现状恒不返回空 / None 不是现役行为路径」作为绝对命题不成立。
- 影响界定:行为零变化结论**不受影响**——该边今日产空 list 走空批 `round_success` 交回,改后产 None 走同义 `round_success` 交回,逐义等价(design §2.1 已声明该映射);失真的是依据命题的完备性,以及「None 在 mandate_v1 仅是契约合法性保留」的表述强度。
- 修正方向:依据 2 补第三条结构边界(条件续复检首位失败边可产空,映射后语义不变),或把主张弱化为「正常路径不产空;防御边产的空与新 None 通道消费端逐义等价」。

### F6(中)死口径收敛清单漏同环「契约 §2」死引用,收敛半途而废

- 位置:`design.md` §2.2 死口径清单(L66-70)vs `cw_screen_prep.py` L2044-2045(主循环)与 L2249-2250(lifecycle)。
- 直调事实:两处循环 F3 校验注释「`# F3 校验(契约 §2:参数非法交回留证;…)`」——「契约 §2」与被点名的「契约 §4」同源(灭失契约工作副本),设计逐处点名了 §4 注释、lifecycle docstring、L2007-2008 头注块(连码块外的注释都点到了),却漏了同一循环体内紧邻的 §2 注释。3.1 验收 grep `契约 §` 只作用于 diff 行,该行不在替换段 → 批后必残留,与「死口径注释同批收敛」的自身意图不一致,收敛后同一对循环内 §4 已清而 §2 仍在。
- 修正方向:§2.2 死口径清单补「两处循环 F3 校验注释的『契约 §2』(灭失副本引用)→ 改语义表述或改指 action_exec.md §2/§3」。

### F7(低)「prep 域词表 17 类全被四分类覆盖」口径不精确,且与 entry.py 头注「18 类」互相打架

- 位置:`design.md` §2.1 依据 2 / §2.3 理由 2;`entry.py` L15(自称「18 类逐类表」)、L200-217;`kernel/cw_vocab.py` L834-843。
- 直调事实:CW_ACTION_TYPES 备战域子集 = 18 类(含 OpenBookcard);entry 四分类元组实覆盖 11+1+1+4 = **17** 类(OpenBookcard 无分类,判 unknown)。设计结论(unknown 首位边经决策核不可达)成立——OpenBookcard 由画面 op 侧 `_clear_prep_cards` 发射、不经决策核——但「prep 域词表 17 类」按字面为假(词表 18、覆盖 17),且同模块 entry.py 头注写「18 类」,复核者直调即卡壳。
- 修正方向:改为「决策核可发射的 17 类全被四分类覆盖(OpenBookcard 系画面 op 侧发射,不经决策核/截断器)」;entry.py 头注「18 类」属既有漂移,可随本批顺带勘误或另挂。

### F8(低)bridge.py 内同族死引用未点名:「序列契约 v2」(STRATEGY_DESCRIPTION)与裸「§4.1」

- 位置:`bridge.py` L92(`DESCRIPTION: …序列契约 v2 帧稳定截断发射`)、L3(`§4.1 新 strategy_id 双被测体`);`design.md` §2.3 只点名 docstring 三处。
- 直调事实:两者同属灭失契约工作副本引用族;3.1 关键词 `契约 §` 对「契约 v2」(无 §)与裸「§4.1」均不命中 → 批后 bridge.py 呈 docstring 已收敛、类描述仍指序列契约 v2 的半收敛态。(entry.py 内大量「契约 v2 §3.2」引用因「决策核零改动」边界明确留存,属设计裁量的既知代价,不列发现;bridge 在本批三文件内,标准应一致。)
- 修正方向:§2.3 清单补第 4 处:STRATEGY_DESCRIPTION 改「帧稳定截断发射(决策核内发射组织,非流程侧契约)」口径;L3 裸「§4.1」改语义表述。

### F9(低)flow.py::decide_shop_action docstring 残留同款死引用「结算惰性 drain」,且在两道机械网之外永不收敛

- 位置:`strategies/impl/flow.py` L699(「入口内务 = 结算惰性 drain + 帧代次消费」)vs `flow.py` L423-430(`_consume_prep_direction_frame` docstring 自证 drain 已删除)。
- 直调事实:与 design §2.3 点名收敛的 bridge 第 3 处死引用逐字同款;flow 中间 ABC 被本批排除(合理,行为零变化),但该死引用因此逃过 3.1(三文件 diff 行)与 3.3(docs 树)两道网,无任何后续批次兜底。设计引 flow.py 该文件另一 docstring 作证据,说明作者到过现场。
- 修正方向:landing 3.1 范围附一句「flow.py::decide_shop_action docstring 死引用『结算惰性 drain』顺带收敛(docstring-only,零行为)」,或显式申报留待商店线批次。

### F10(低)B4 兼容句「返回非空 list 的策略…fail」不精确:空 list 同样 fail

- 位置:`design.md` §2.2 末条(L72)。
- 直调事实:新校验谓词 `result is not None and not isinstance(result, CwAction)` 对 `[]` 同样拒绝(旧契约下 `[]` 走空批成功分支)。注册面封闭集 = {mandate_v1}(flow/README §2.1 直调吻合),无实际第三方,仅表述失真;括注「(非 None 非 CwAction)」已含正确谓词。
- 修正方向:改为「实现旧 list 形状的策略(无论空否)在新形状校验处 fail」。

### F11(低)3.3 PrepAction 裸名人工复核只指 projection_contract §4.1,漏 action_exec.md L9「备战域 PrepAction 全集」

- 位置:`landing.md` L36;`flow/action_exec.md` L9。
- 直调事实:「PrepAction 类已亡」是清单 #3 自认的前提(unified-action-factory 批基类更名 CwAction),L9 的「备战域 PrepAction 全集」是活正本里的裸死类名(非执行器名),按设计自身判据应改「备战域动作全集」;裸名人工复核指令却只指向 projection_contract §4.1 一处。
- 修正方向:清单补一条(action_exec.md §1 L9 裸名改写)或把人工复核指令从「人工核 §4.1」扩为「排除 PrepActionExecutor 等合法名后逐处核」。

### F12(低)「序列终点」波批措辞残留于活正本与核注释,清单与闭域关键词均不可见

- 位置:`strategy-docs/22_prep_screen.md` L28(「序列终点 = 备战环正常出口」);`entry.py` L442(核内,本批不改动,随录)。
- 直调事实:与「执行序概念随单动作循环消亡」的新口径存在张力;因不含闭域关键词,3.3 永不拦截。属表述债,非矛盾(核内 list 发射组织仍在,StartBattle 仍是其末位)。
- 修正方向:清单 #11 扩展为同文件两处(L8 取首项句 + L28 序列终点句 →「备战环唯一完成态/正常出口」口径)。

### F13(低,范围外既有缺陷·随录)strategy-docs/README.md 文件尾两个孤立表格行破坏版式

- 位置:`strategy-docs/README.md` L75-76(19/20 两篇的表格行悬在 §5 文档纪律清单之后,脱离 §2 任何表格)。
- 直调事实:git diff 确认本批只改「策略↔流程契约」行(L52),该两行为既有遗留;但同文件同批在手,顺带归位成本低。不属本批对象面,仅随录。
- 修正方向:两行移回 §2 分篇表格(或按 19/20 篇现状核实后删除/改写)。

## 零发现对象与实际攻击过的面(含直调码点)

1. **对象 2:cw_strategy.py::decide_prep_screen docstring as-built 十句逐句直调核,全部属实**:①签名 `list[CwAction]` + 波批遗留定性(现签名 L121-122);②输入 `session.prep_obs_frame`(bridge L120 读、缺失 L121-125 抛 ValueError)、跨步状态经 strategy_state(sphere_defer_streak/v3_intention);③生产消费端 = cw_screen_prep.py L2029/L2043 与 L2234/L2248 两处同构、每帧 `actions[0]`、尾部动作不消费;④列表 = 决策核三遍编排发射组织(emit→route_tag→truncate,bridge L272-291);⑤空序列合法交回 + stall 兜底归外循环(L2038-2041/L2243-2246);⑥画面转移仅 OpenShop/StartBattle 终结(entry 分类元组 L200-217 + action_exec §1);⑦已退役语义 + `flow/action_exec.md` §2(机械执行无成败回执)/§3(无 fail-stop)指向真实且内容吻合;⑧帧稳定分类在决策核内仍活、辖发射组织(entry L220/L297/L1157 + mandate L1965,流程侧零截断);⑨生命周期机制四件归流程侧(action_key=cw_vocab、deploy_fail_counts=ExecState、stall 门/强制出战=外循环);⑩「观察帧缺失即抛错」= bridge 实码。git diff 亦证:工作区版 = as-built 口径重写,与 design §1「现行文本已是 as-built 口径」声明一致。
2. **对象 3:strategy-docs/README.md「策略↔流程契约」行:数字与指向全部与现行事实一致**——「四身份分离」= flow/README §2.1 ✓;「契约成员 13」= flow/README L40/L84 + 代码直数(abstract 12 + create_state,基类 L97-204)✓;「单动作循环」= flow/README L6/§2.2 ✓;「序列语义为历史注」= flow/README L77-82 历史注节 ✓;指针「README §2」✓。
3. **design.md 码点主张逐条直调**:~L2029/~L2234 调用点、F3 现行文案「策略输出非 list[CwAction](F3)」(L2037/L2242)、空批 detail 文案两处(L2041/L2246)、try/except 两处同构、「空批合法(契约 §4…)」注释两处(L2039/L2244)、lifecycle docstring「终结出口语义 = 空批/…」(L2211)、主循环头注块 L2007-2008(跨行拆句属实)+ 同块「逻辑态未建模的动作同判保守回退」死口径(L2010-2011,R9 已删分支,prep.md §4 佐证)——全部吻合。
4. **landing 正本更新清单 11 项引文/行号逐条直调**:flow/README L17-18(「决策取/首项」跨行拆分属实)/L23/L64、projection_contract L89-90(含「族 B PrepAction 列表」裸名句)、action_exec L28、op-layer L14/L21、prep.md L15/L32/L53、screens/README L130、22_prep_screen L8——引文逐字存在,行号无漂移。
5. **mandate_v1 耦合面申报核验**:帧稳定分类/截断真实调用恰 4 处(bridge L290、entry L297/L1157、mandate L1965)+ 注释提及 3 处(mandate L1298-1299、L1753、L1951-1957)与 §2.3 理由 2 逐一吻合;bridge docstring 三处死引用引文逐字吻合(L109/L114-115/L117-118);action_exec §1 = 词表与注册表节 ✓;flow.py::_consume_prep_direction_frame docstring 自证 drain 删除(L423-430)✓;emit ⑥ 空则补 StartBattle(entry L944)✓;truncate 空输入返回 [](L331)→ §2.5 新锁用例 2「空发射态→None」可行 ✓;flow 中间 ABC 保持 abstract(flow L33)✓。
6. **测试与工具影响面**:sr-od-test 全仓 grep `decide_prep_screen` 仅 test_cw_p2_blood_band.py L215-218 桩子类(`*a, **kw`,raise NotImplementedError,形状免疫);「空批/策略输出非/list[CwAction]/取首项」测试仓与 tools/ 零命中 → §2.5「在册锁零更新义务」与 §2.6「无工具/测试/哨兵依赖旧文案」成立;replay_to_md.py 纯 stdlib 离线渲染、零策略 import → §2.4 零影响成立。
7. **依据指针存活核验**:strategy-work.md §4 含「A/B 报告必带 sim 可观测性声明」「实机/sim 分工」「判读锚点事前写」三项被引主张 ✓;「测试分层」行经 strategy-work §4 指回 SKILL.md ✓;flow/README §2.3 sim 消费面注记、§2.4 归因域限定、§2.1 管理器行封闭集 {mandate_v1} ✓;op-layer §1.3 守卫断言、§1.4 恒可用终结(备战 = 开战)、§4 次门(cw_replay --diff 只重放商店决策面)✓;26_battle_settlement.md = 出战标准载体(readiness_launch_decision)✓。
8. **规范遵循**:迭代四节齐(README/design/landing+正本更新清单)✓;阶段小节七件齐(范围/设计依据/文件面/依赖/优先级建议/完成判据/验收凭据)×3 ✓;固定末阶段 = 正本更新 ✓;无过程叙事(design/landing 正文无「本轮/已改」类措辞)✓;changes/ 引用寿命(三文件只引正本/skill/代码符号,零 changes/ 引用)✓;README 进度与 design §0 状态一致(对抗审中)✓;引用均为持久索引 ✓。
9. **治本三问**:§1 归层表示层成立(消费语义 2026-09-06 已迁移、表示未跟,双向实证);§2 修根 = 契约面形状收口,核内 list 保留有活机制依据(首项选择序 4 调用点实证),非症状补丁;备选 A-D 取舍论证核过无空洞(D 的弃因与 op-layer §1.1 分域表述核验一致);None 通道三点依据中第 1/3 点直调成立、第 2 点前提过强(见 F5);第三方兼容面(B4 封闭集、响亮暴露不做垫片、无静默兼容)边界申报自洽(表述瑕疵见 F10)。
