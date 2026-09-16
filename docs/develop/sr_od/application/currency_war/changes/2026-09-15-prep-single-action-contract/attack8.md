# attack8 — 无前提对抗审查(2026-09-15-prep-single-action-contract)

审查对象:①迭代设计三件(README.md / design.md / landing.md);②`cw_strategy.py::decide_prep_screen` docstring 工作区改动;③`strategy-docs/README.md` 工作区改动(「策略↔流程契约」行接口数表述 + 19/20 两行归位 §2 分篇表)。未读 attack.md–attack7.md(树级 grep 时其行曾出现在结果中,未采信、未作依据)。

## 发现总数:5(高 0 / 中 3 / 低 2)

---

### F1(中)landing 正本更新清单 #17「OpenBox 终结性更正」自身目标面不闭合:同文件还有第二处活反例,批后 §4 与 §5.3 关于 OpenBox 终结性直接互斥

- 位置:`landing.md` L60(清单 #17,只挂 `screens/README.md` §4 词表-注册表总表领取类行 L52);反例 = `screens/README.md` L91(§5.3 备战画面表行「开补给箱(点备战栏箱位)/开秘密典籍 … | 非终结」)。
- 攻击过程:直调 `operations/cw_op/cw_open_box_action.py` L39(`terminal = True`)+ `cw_screen_prep.py::CwScreenPrep._terminal_exit` L2344-2349(OpenBoxOp 分支自证「OpenBox 终结化(R7,批2a):开箱即引入新事实 → 本访问交回」)——OpenBox 现值 = 访问终结。landing #17 只把 §4 L52 领取类行的 OpenBox 改标终结,§5.3 L91 同文件同事实主张(访问终结语义列 =「非终结」)不在条目内;3.3 闭域关键词「首项 / 空批 / list[PrepAction]」对「非终结」结构性零命中,裸名人工复核位也不含它——该反例批后必然存活,§4(OpenBox 终结)与 §5.3(OpenBox 非终结)在同一正本文件内互斥。附带:§6 终结集总表(L122-133)无 OpenBox 行,与 op-layer §1.4「终结集总表 = README.md §6」的封闭总表定位不符(同族 as-built 漂移)。
- 影响:不导致实现错误/行为变更;但 3.3 的验收目标「正本与实现一致」在 #17 条目自身辖域内(OpenBox 终结性陈述)不可达成,属清单条目完备性缺口。
- 修正方向:#17 扩展为「OpenBox 终结性陈述全集」:①§5.3 L91 行按 OpenBox/OpenTome 拆分表述(OpenBox = 访问终结(交回外循环按武装箱选卡分发);OpenTome 维持非终结);②复核 §6 总表是否补 OpenBox 终结行(不补则显式申报缺行理由)。

### F2(中)design §2.2 F3 注释改写指定锚「契约单一源 = flow/action_exec.md §2」依据失真:该节不含被指语义

- 位置:`design.md` L70;被改注释 = `cw_screen_prep.py` L2044 / L2249「F3 校验(契约 §2:参数非法交回留证;M6 边界面——执行前输入契约检查,非动作后判效)」。
- 攻击过程:直调 `flow/action_exec.md` §2(执行契约,L13-24)——内容 = 动作 op 机械执行无成败回执、落地登记注册表、画面 op 级状态、商店编排、发射门;**无**「参数非法交回留证」与「执行前输入契约检查」语义(「F3 validate」在该文件仅 §3 L28 顺带提及)。该语义的活正本 = `screens/prep.md` §4 L33(「F3 validate(参数非法 = 拒绝执行 + 交回留证;执行前输入契约检查,非动作后判效)」)与 `game_state/logic-updates/prep-executor-actions.md` §1 L7(「执行器 `validate` 两层 = 白名单 + 静态参数」)。设计把灭失契约 §2 引用重锚到一个不含该语义的节;若实现者按指示把该锚写进持久注释,等于入库一个可复核即假的指针(两种读法皆失:作注释文本 = 假指针入库;仅作实现者指引 = 指向错误出处)。
- 修正方向:锚改指 `screens/prep.md` §4 或 `game_state/logic-updates/prep-executor-actions.md` §1(或写成纯语义表述不带节指针)。

### F3(中)机械扫尾关键词 `design.md` 存在大小写盲区,且四文件面内有实 escape:flow.py 的灭失设计稿指针族(4 处)既不在枚举 5 处内、也拦不住

- 位置:`design.md` L74-75(扫尾关键词族含小写 `design.md`;changes/ 引用注释「实态 5 处」);escape 实体 = `strategies/impl/flow.py` L105「设计出处 = p2_blood_band_unified_design/DESIGN.md §2.3-5(a)」+ L112/L133/L139「统一设计稿 §4-8 / §5-F4」。
- 攻击过程:①直调该路径归宿:`.debug/temp/currency_war/_archive_20260908/p2_blood_band_unified_design`——已归档且 `.debug/` 不入 git,非持久索引(AGENTS §8 引用铁律同族,与「契约工作副本灭失」同根:代码引用已灭失设计稿);②ripgrep 默认大小写敏感,关键词 `design.md` 对 `DESIGN.md` 零命中——设计为 L2537 裸指针补 `design.md` 的理由(「裸 design.md 指针无其他词可兜」)对 L105 同样成立,关键词规格却接不住;L112/L133/L139 的「统一设计稿」则完全无关键词可兜;③3.1 验收 grep 只作用于 diff 新增/改写行,这 4 行均为未改行,同样盲。设计自称「同族同批清,不留保留申报口子」(L75)+「本扫尾是完备性的机械兜底…禁未处置命中」(L74),对本族既有债(同在本批 flow.py 文件面)枚举与兜底双双失效。
- 修正方向:扫尾关键词族补 `DESIGN\.md` 与「统一设计稿」(或 `(?i)design\.md`);flow.py L105/L112/L133/L139 逐处三分处置(收敛为语义表述——带判定单一源本就是 `HP_BAND_NEAR_DEATH` 常量锚;或显式保留申报)。

### F4(低)design §2.3 理由 2 把 mandate.py L1753 注释定性为「影子面不辖」,与实文不符

- 位置:`design.md` L93;实体 = `mandate_v1/mandate.py` L1753。
- 攻击过程:直调 L1747-1759——该注释位于 M1″ 板满换阵补部署段(生产发射臂),L1753 实文 =「classify_frame_stability,不触发截断、不受 M7 发射序回排辖」;「影子面」在 entry.py 模块头(L37-41)的既定所指 = 换线影子遥测面(should_switch/回锁窗/干旱计数),与此处不是一回事。注释位置与「不辖」语义属实,定性词失真;计数结论(注释提及 3 处)不受影响。
- 修正方向:改「L1753 M1″ 换阵臂注释(不辖声明)」类中性定性。

### F5(低)主循环决策段头注释块(L2007-2011)改写只有方向无定稿文本,块内「输出等价系条件命题——帧级锁按锁纪律重推」半句的去留未交代

- 位置:`design.md` L72(该块改写指令 =「→ 单动作/None 口径」);实体 = `cw_screen_prep.py` L2007-2011。
- 攻击过程:与基类/bridge docstring 不同,该块无 §2.1/§2.3 式定稿关键句;且块内「三遍编排序保持(决策核输出逐帧取首项 = 单动作选择序,**输出等价系条件命题——帧级锁按锁纪律重推**)」的下半句在契约改后语义地位两可(帧级锁不在本批文件面、锁对象本身不受影响,但注释语境是围绕「取首项为何等价」展开的)——实现者需自行裁断整句重组与该半句去留,轻微违反「实现者无需再设计」。有机械扫尾兜底(`取首项` 命中必处置)故仅低。
- 修正方向:补一句定稿(如「决策恰取一个动作/None;输出等价命题与帧级锁注保留/删除」二选一写死)。

---

## 审查对象 2(cw_strategy.py::decide_prep_screen docstring as-built):零发现

十句主张逐句直调全部属实:①签名 `-> list[CwAction]`(L121-122)+ 波批遗留定性(HEAD 版「序列契约 v1,2026-09-03 冻结」,git diff 核对)✓;②输入 = `session.prep_obs_frame`(`cw_strategy_session.py` L201-206,写者白名单/读者声明在档)+ 跨步状态 defer 计数(`entry.py` L485-516 挂 `state_of(session).cw4_counters`)与意向状态机(`flow.py` L391-420 经 `state_of`)同 session ✓;③「单动作循环逐帧取首项、两处同构」(L2029/L2234 调用,L2043/L2248 `actions[0]`)✓;④「列表 = 决策核三遍编排发射组织、相对序决定首项、尾部不消费」(`bridge.py::decide_from_turn` L259-291:emit → route_tag → `truncate_frame_stable`;消费端仅 `[0]`)✓;⑤「空序列合法交回外循环、stall 兜底归外循环防线」(L2038-2041/L2243-2246)✓;⑥「画面转移走终结动作(开箱/开店/出战)」(三者 `terminal=True`:cw_open_box_action L39 / cw_open_shop_action L31 / cw_start_battle_action L42)✓;⑦「已退役语义 + flow/action_exec.md §2(机械执行无成败回执)/§3(无 fail-stop、对账归下一入口)」指针真实且内容吻合 ✓;⑧「帧稳定分类在决策核内仍活(mandate_v1 entry)」(`classify_frame_stability` L220、`truncate_frame_stable` L241)✓;⑨「生命周期四件归框架流程侧」(`action_key` = cw_vocab.py L846;执行失败记忆 = `deploy_fail_counts` 族;stall 门 = flow/README §4;强制出战 = cw_screen_prep L505)✓;⑩「观察帧缺失即抛错」(bridge.py L120-125 ValueError 实码)✓。注释规范合规:中文、引用全为持久索引(文件:节/符号名)、无会话局部标识符、「迁移后/遗留」系现状成因表述非变更史叙事。

## 审查对象 3(strategy-docs/README.md 工作区改动):零发现

①「策略↔流程契约」行「17 接口」→「契约成员 13、单动作循环;序列语义为历史注」:13 = abstract 12 + 工厂 1 与 `flow/README.md` §2(L40/L53-66/L84)一致;单动作循环、§2.2 历史注节、「在其 README §2」指向均实存且口径相符;②19/20 两行:从文尾(§5 之后的孤立表格行)归位进 §2 分篇表(git diff 核对,仅此两处增删),两文件实存,插入位(18 与 22 之间)保序,一句话概述与两篇文首标题相符(「补强通道(接线)重估与 P51 生存折现」「大额结余…必花域」);「flow/ 七篇」实数 7 个 md ✓。已知范围外(分篇表缺 14/15/16/17/21 五行)未重复计。

## 验收判据可执行性与三核补充直调(支持性事实)

- **3.3 闭域检查完备性(独立全树重跑,232 文件、排除 changes/)**:「首项」→ 清单 #1/2/3/4/5/7/8/11/13/14/15 全覆盖 + `proofs/validations/P51_V3_REBUILD.md` L391(「R31-2 首项=1」,拟合器标签序位)豁免正当;「空批」→ flow/README L77/L81(历史注节,豁免正当)+ #6/#8/#9/#10 全覆盖;「list[PrepAction]」→ #2/#7;PrepAction 裸名活正本位仅 `projection_contract.md` L89(#3)与 `action_exec.md` L9(#12),与「已知位」一致。三关键词域内完备可执行(F1 的缺口在关键词域之外)。
- **3.1 验收 grep × 定稿文本互斥性**:关键词集(`空批/取首项/契约 §/契约 v/序列契约/list[CwAction]/结算惰性 drain/§4.1`)对 §2.1 基类定稿句、§2.2 码块与 None 分支注释、新 F3 文案、lifecycle docstring 定稿、§2.3 bridge 五条改写与定稿句、flow.py 两处定稿句逐词过 = 零碰撞;`decide_from_turn -> list[CwAction]`(bridge L262)豁免申报准确(未改行)。判据域「diff 新增行/本批改写行」读法唯一可执行。
- **design 码点/引文逐条直调属实**:两循环 before 段(L2028-2043/L2233-2248)与码块逐行可对;死口径五处(L2039/L2244「契约 §4」、L2044/L2249「契约 §2」、L2211-2212 终结出口枚举含「空批/控制流/逻辑态未建模」、L2007-2008 头注、L2010-2011「逻辑态未建模…保守回退」R9 死口径,L2112-2113/L2312-2313 同函数自证分支已删)、`actions: list = []` L2016/L2220、changes/ 引用恰 5 处(L664/L984/L2103-2106/L2325-2326/L2537)、L984-985 路径笔误(`action-logic-state.md` 实在 `game_state/` 非 `flow/`)、「契约工作副本灭失」自证(entry.py L15-19)。None 通道三点依据:emit ⑥ 空则补 StartBattle(L936-944 `if not out`);可达空边 = truncate 首位 SellBench/DeployMove 名-槽复检截空(L309-324);unknown 首位边不可达(四分类表 11+1+1+4 = 17 全覆盖决策核可发射类;OpenBookcard 仅画面 op 侧发射,entry.py 零引用,`_clear_prep_cards` L2537-2539 实证;备战域词表 18 类 = CW_ACTION_TYPES 备战子集实数)。B4 谓词(非 None 且非 CwAction,旧 list 空否均 fail)推演成立;注册面封闭集 {mandate_v1} = flow/README §2.1 L47。flow.py 无 `decide_prep_screen` 本地声明(纯继承 abstract,无签名需改),边界完整。
- **影响面**:全 src `decide_prep_screen` 消费仅两循环;sim/replay/tools 零消费 prep 面;`replay_to_md.py` 纯 stdlib 离线渲染(零 sr_od import);sr-od-test 仅 `test_cw_p2_blood_band.py` L213-216 `*a, **kw` 桩(形状免疫);旧文案(`空批(本帧无动作)`/`策略输出非`)在测试仓、tools/、skills/(含 cw_sentinel.py 等四脚本)、telemetry/ 全零命中——§2.5/§2.6「零更新义务/无依赖」成立。遥测键族(emitter_*/deploy_emit_*/deploy_exec_*/t1_interest_prep_emit/wanted_leg_*/m1p_*/sphere_defer_*)实码在键;`prep_box/prep_tome/prep_spheres` 系 `Emitted.reason` 路由标签(entry.py L462/L464/L498/L513)。「strategy-work §4」三项被引主张(sim 可观测性声明/锚点事前写/实机-sim 分工)在 skill references/strategy-work.md L51/L53/L55 逐条实存。L1 命令路径实存可执行(`sr-od-test/test/sr_od/application/currency_war/`;`legacy_baseline` 全仓无注册标记,-m 表达式中为无害 no-op 过滤,属已申报 skill 笔误族,不计)。ruff select 含 F(pyproject L63),F841 生效。
- **批外相邻观察(不计发现,均为本批声明族与关键词域之外的既有债)**:`cw_strategy.py` L7 `docs/develop/currency_war/strategy/07_plugin.md` 与 `cw_screen_prep.py` L497 `strategy/03 §7` 指向已删除文档树;`22_prep_screen.md` L3/L34 `../flow/screens-actions-capability.md` 不存在;`mandate.py` L1752 注释仍写「发射载体 = RunDeploy」(类已退役,实码 L1831-1853 产 SellDeployed 原子)。

## 结论

设计与两处工作区改动主体扎实:消费端改写码块可直接落码、None 通道等价论证与行为零变化声明成立、正本更新清单引文逐字无漂移、闭域检查在三关键词域内完备。三处中危集中在**清单/锚点完备性**(F1 OpenBox 终结性第二处反例、F2 F3 重锚失真、F3 扫尾大小写盲区+flow.py 灭失设计稿指针族),均不影响行为、修法明确,并入设计后可继续推进对抗收敛。
