# T-7 投资环境 修法设计(invest_env)

## 0. 元信息

- 迭代目标:货币战争全画面规范符合性审查(2026-09-22-screen-review)·只设计不落码,待用户裁决
- 状态:F-4/§1.7① 已裁决待落地(用户裁决 2026-09-22:F-4 按观察标准化门修订——规范条已先行入正本 op-layer.md §1.1;局外分支按删除方向收敛,规范条同批入正本);修订后经无前提对抗审(高1中3低5,#1-#8 采纳修订:字段退役拆分仅环境类/碰撞边界入正本/contract 冒烟锁登记/判据直调型 T-37 登记/归一单一源/死码清单等),实体修法方向与代码锚全部核实成立;F-2 补测与整体落地批准仍待用户表态(对抗轨迹:r1 未收敛 6 条→修订→r2 未收敛 3 条→修订→r3 未收敛 1 条低→修订→r4 收敛 0 条)
- 发现源:`.debug/progress/2026-09-22-cw-screen-review/reports/T-7-r1.md`(F-1..F-6;总判定「有问题(高0 中3 低3)」)。涉事代码与代码内文档以仓库现状为真值逐处核读(含对审查报告命中点的复核);本文定位一律符号锚 / 文档节号 + 内容引文(行号仅定位辅助,随代码漂移)。文档路径根 = `docs/develop/sr_od/application/currency_war/`,代码路径根 = `src/sr_od/application/currency_war/`(下文反引号短路径均相对此两根,同迭代设计稿以裸文件名引用)。
- 真值基线 = 本稿撰写时点工作树;落地批动笔前若代码/正本已再变,以落地时点现状重新对账后再动笔,禁按本文过期症状照稿落地(与 T-1/T-3/T-6 稿同款条款)。
- 修法性质:F-1/F-2/F-6 = 文档语义更新;F-3 = 改判非偏差·销项(零修法,§2.3);F-5 = 注释清理;F-4 = 观察标准化门落地 + 动作链收窄纯 idx + 链内防御纵深(用户裁决 2026-09-22 修订扩项,行为变化申报见 §2.4)+ 局外分支删除(§1.7① 裁决并入)。除 F-4/局外删除外全部零行为变化。

## 1. 问题与动机

### 1.1 F-1(中)invest_env.md §4/§6 欢愉契约条件腿归属与正本及代码不符

- 现状症状:`screens/invest_env.md` §4 决策体图选卡分支括注(L51-52)「欢愉契约 provisional 条件腿随获得链回调 on_env_gained 枚举迁移,行为逐位等价」与 §6 环境赠卡条(L87)「欢愉契约 provisional 条件腿亦迁该回调」——代码真值 = `kernel/cw_gain_chain.py::on_env_gained` 仅消费 `ENV_GIFTS` 的 `chars_immediate` + advisor 分道,docstring 自述「欢愉契约条件腿不在本枚举」;条件腿 rider 实驻 `kernel/cw_action_report/pick_planner.py::_grant_joy_conditional`(触发事件 = 头号玩家选项弹窗被处理,即银狼策划选择上报;`active_env` 欢愉契约在册 → `gain_character` 1★ rand=True)。两处声称该腿随 `on_env_gained` 迁移,与正本 `game_state/gain-chain.md` §3 条款和代码行为直接矛盾,误导读者对触发时点(选环境时 vs 头号玩家弹窗处理时)的理解。
- 根因归层:**语义层为主**(条件腿效果腿的归属申报写错)、**约定层为辅**(条件腿正式建模批的收尾正本更新清单漏了画面篇两处残留句——gain-chain.md §3 已改写正确,画面篇未随批同步)。
- 解决到哪:invest_env.md 两处改写为现役归属(§2.1),指针 = gain-chain.md §3。
- 明确不解决:gain-chain.md §3 / `game_state/logic-updates/pick-planner.md` / `screens/planner.md` 等其余正本(本稿已对 `docs/` 树 grep「条件腿|欢愉契约」全量核对,归属错写仅本篇两处);代码零改动;其余环境的条件腿族建模(在册「族批候裁」面,非本稿辖域)。

### 1.2 F-2(中)invest_env.md §9 测试锁宣称的覆盖面与实际不符

- 现状症状(核读证实):§9 把「report 含 refresh 摄入 / 空候选零盲发」记为在册锁面,实际两侧均无 env 覆盖——①`env_refresh_left` 观察写端双腿零断言:行为锁侧 `test_cw_obs_arch_phase_screens.py::_make_env` 把 `read_invest_refresh_counts` 桩为恒 `[]`(obs.refresh=None → report 跳写);report ports 侧 `test_cw_screen_report_ports.py::_case_invest_env` 的 obs 未设 `refresh` 字段、空桩用例只断 `invest_env_opts`;全测试树 grep `env_refresh_left` 仅开局种子字段清单命中(对照 supply 屏同腿在 ports 有值写入锁:`_case_supply_node` 断言 `supply_refresh_left`)。②env 屏无空候选零盲发锁:同形锁在册仅策略屏 `test_invest_strategy_empty_opts_fail_not_blindfire`。行为代码本身合规(报告 §1 表③/⑥),缺的是 §9 宣称与实际覆盖相符。
- 根因归层:**约定层**(文档宣称先行于/超出测试落地,虚增回归信任面)。
- 解决到哪:§9 宣称修正为 as-built(方案②:正本不虚报)+ 锁面缺口如实登记,补测方向一并给出(补测 = 落码,属「待用户认同后落地」面,§2.2)。
- 明确不解决:行为代码(审查已判合规);supply/encounter 屏的既有锁(在册先例,不动);其他屏的锁面缺口(各屏审查辖域)。

### 1.3 F-3(中;经词义定谳与在册判例核:改判非偏差·销项,零修法)invest_env.md §2 画面形态声明与 op-layer §3 分型总表不一致

- 现状症状:§2 首句「**单选族例外**(有选择面零逻辑态账,判据 = README.md §3;投资环境域的例外收窄见 §6)」;正本总表 `screens/op-layer.md` §3 把本屏列为**全形态**。审查报告病面两面,经核均不成立:①括注前提「零逻辑态账」失真——经词义定谳改判非失真(在册定义 = README §3 自文 visit 消费读法,§2.3 判读框架③);②标签与权威总表口径差——在册判例(T-5 审查报告 :118)对该面终判「不构成偏差」且**明文点名 invest_env.md 同款覆盖**(原文引录见 §2.3)。两面均落判例/定谳辖域,F-3 改判**非偏差·销项**:§2 现状行为描述与代码一致,标签 = 模板族层词汇(判例在册),分类权威 = op-layer §3 随文可查,零读者误导面。
- 根因归层:审查取样的约定层判断在两点失准(词义两读取了无在册定义支撑的一读;口径差半未与 T-5 在册判例对账)——非画面篇正本病(§2 现状判读合规,零落地面)。
- 解决到哪:零修法(`screens/invest_env.md` §2 零改动);词义定谳与判读判法保留于 §2.3,作为 T-37 裁「全族标签统一与否」的判读输入;该裁决面唯一落点 = T-37(§1.7②)。
- 明确不解决:op-layer.md §3 与 README.md §2 正文本体(零改动);encounter/supply/invest_strategy 三屏 §2(标签同款在判例覆盖语义内,同判非偏差,零改写义务);T-5 在册判例本体(沿判,零改动)。

### 1.4 F-4(低;用户裁决 2026-09-22 扩项修订修法)名字标准化散落动作侧、观察层零标准化——noop 假成功 + 未注册名带病上报

- 现状症状(核读证实):①**观察层对「读数是否注册表内名字」零校验**——OCR 原文名经 `_read_options` 直进容器 `invest_env_opts`;未注册名在决策打分走中性 fallback(`cw_screen_invest_env.py` 未注册 warning + 中性分)可照选照点,链上 `on_env_gained` 查无效果安静不写,容器留脏值。②名字标准化散落动作侧两处——派发处 `norm_name=normalize_invest_name(chosen)` 一次、report 层 `kernel/cw_action_report/pick_invest_env.py::_canon_invest_name`(含全角冒号归一)再一次。③report 层 noop 分支:`if not canon: return LogicOutcome(applied=True, reason='landing_noop')`——归一后空 = 静默零写但 applied=True,动作 op 照常终结,容器与游戏真实选择偏离且无留证;正本未登记(gain-chain.md §2.1 env 腿无任何拒绝腿;action_ops.md §4.5 PickInvestEnv 行声明出参 reason=`gain_chain_applied`,与 `landing_noop` 私词不符)。④对照策略支,链入口拒绝腿缺失(`kernel/cw_gain_chain.py::gain_invest_strategy` 步 0 = 零写 + 缺陷留证 + `detail='invalid_payload'`,gain-chain.md §2.4-0 在册;env 支无同款)。
- 用户裁决(2026-09-22,经三轮口径对齐定谳):观察内容必须**在观察时**转换成标准注册数据(逐候选:形变归一精确匹配 → LCS 相似匹配兜底);转换不到 = **观察失败**(round_fail 交外循环重观察),不能上报;后续选择动作 op 只上报选择了第几个(idx)。此判法已升格为全域规范先行入正本(op-layer.md §1.1「观察标准化门」,2026-09-22)。
- 根因归层:**语义层 + 契约层**——名字标准化的职责位放错(住动作侧,应住观察侧,规范裁决后已成文);观察→容器的值域契约缺「标准注册名」门;链契约缺无效载荷拒绝腿(策略支已有)为同根末梢。
- 解决到哪:三层修法(§2.4):①观察层标准化门(核心);②动作链收窄纯 idx(`norm_name` 载荷退役、noop 分支删除);③链内无效载荷拒绝腿(防御纵深,镜像策略支)。外加局外分支删除(§1.7① 裁决并入本稿落地批)。
- 明确不解决:kernel 打分的未注册 fallback(标准化后生产不可达,本体不动);链上「未注册名安静不写」末端形态(防线最末端,维持,与策略支 `on_strategy_gained` 同款);`normalize_invest_name` 形变族本体(整体迁观察侧复用)。

### 1.5 F-5(低)审查对象代码文件注释纪律存量违例(AGENTS.md §8)

- 现状症状(报告点名 + 核读补充;施工 = 全文件扫描为准,处置见 §2.5):`operations/cw_screen/cw_screen_invest_env.py`(L5-6/L16 模块头裁定日期、L61 类 docstring 陈旧概述、L69 带宽放宽变更史、L78 裸「3.8」设计件引用、L93/L149「批4 比对收口」×2、L160-161/L188-189/L204-205/L230-232 裁定日期、L242 裸「bug#1」缺陷件引用)+ `operations/cw_op/cw_overlay_pick_action.py`(L282 task#/W、L227 T#、L342 日期+rN、L15-23/L293-295 批史废除史;执行权 = T-6 §2.5)+ `kernel/cw_action_report/pick_invest_env.py`(L7-9 拆分史)+ `kernel/cw_gain_chain.py`(模块头 L29-32 changes/ 过程件引用含内嵌日期、L77-78 缺陷 kind 词表「已随…批退役」句式、`gain_invest_env` docstring L451-453 变更史、on_env_gained docstring L604-607 死索引[pick_invest.py 已拆分退役])+ `kernel/cw_screen_report/invest_env.py`(L50 裁定日期、L54-55 平移史)。
- 根因归层:**约定层**(AGENTS §8 两禁形为后立规范,存量未回溯清理,且无周期性卫生机制)。
- 解决到哪:清理准则沿用 T-3 设计稿 battle_wait.md §2.6 五条(本稿不重立),按文件登记命中面与豁免面;`cw_overlay_pick_action.py` 全文件卫生执行权 = T-6 稿 §2.5 已认领,本稿仅登记命中面并入其全文件扫描一次成文(§1.7③)。
- 明确不解决:CW 全域乃至全仓存量注释卫生(建议另立全仓注释卫生批,与 T-3 §2.6 同族联动面并案裁决);ADR 引用 / 归档帧路径 / 正本指针类合规引用(不在列)。

### 1.6 F-6(低)invest_env.md 正文 as-built 无状态纪律存量

- 现状症状:裁定日期引述「用户裁定 2026-09-21」×4(§2/§3/§6);变更史对照「等价旧『idx + refresh_slots 并载、闸败回退选卡』行为」(§4)与「旧调用形兼容」(§8);退役/升格叙述「原 log 观察通道已升格 obs 正式字段」×2(§3/§6)、「号制已退役,不引 0x」(§1 分发判定,报告记 §2,内容引文定位不歧义);篇头导语(L3)「稳定帧观察」与 §2/§3「零稳定帧等待一次读全」文内自相矛盾(陈旧措辞残留)。
- 根因归层:**约定层**(screens/README.md §2「as-built 无状态」与 AGENTS.md §9 后立纪律,正文未随批回溯收敛)。
- 解决到哪:逐条状态清理(§2.6),裁定语义保留并指正本条款。
- 明确不解决:行为描述主体(与代码一致,零改动);§9 宣称面(归 F-2 不重复立项);F-1 错句内含的「迁移…行为逐位等价」变更史(随 §2.1 改写一并清偿,§2.6 表注衔接)。

### 1.7 同族联动面与跨稿冲突登记(不立修法,提请裁决)

1. **局外防御分支归属冲突(已裁决终结,用户裁定 2026-09-22)**:原分歧 = 本报告 §3.6 判「无 match 局外防御 = 裸空容器 decide_event」在册合规(依据 = 屏文档 §4 自申报 + 投资策略孪生屏同构)vs T-6 稿 §1.1 对孪生屏同款判**流程层违例**(依据 = 决策控制分层铁律 + op-layer.md §1.1,屏文档 as-built 自申报不等于正本背书)。用户裁决:**不支持单独调用具体画面 op 进行调试,相关支持代码不做,规范入正本**——局外分支的独立跑选卡价值不成立,删除方向(T-6 方向①)为唯一解,冲突终结。规范条已入 op-layer.md §1.1「画面 op 不支持局外单独调用」(2026-09-22);T-37 登记改记「已裁决,族内按删除方向收敛」(祈愿/巨星/伙伴/卜者/星徽等纯常量盲发型局外支按同口径归各族稿/T-37 收敛,禁两屏两态)。**本稿修法(并入落地批)**:`operations/cw_screen/cw_screen_invest_env.py::_decide_and_act` 局外 else 分支整段删除(含内嵌 `GameState`/`GAME_STATE_SCHEMA_VERSION` 局部 import,及随 else 死码化的函数头 `config = CurrencyWarConfig(...)` 构造与文件级 `decide_event`/`CurrencyWarConfig` import——现仅 else 分支消费)、match 判空(∨ `match.gs` 缺席,对齐遭遇屏先例宽度 `cw_screen_encounter.py` 局外支三判)提前为早退出口(置于空候选检查之后——空候选 = OCR 读缺 bug 面,契约与局外无关)→ 零决策零点击 round_success 终结交回(遭遇屏在册先例同款);刷新臂守卫 `and match is not None` 死码化删除;`screens/invest_env.md` §4 伪代码行与 §5 终结表同步;补一锁(match=None + 非空候选 → round_success、点击记录为空,T-6 稿 handback 锁同构)。**判据直调型局外支去向登记(T-37)**:T-9 装备稿保留的 kernel 判据直调型局外支,与本正本新规范条「不设任何兜底决策路径」的字面相容性候 T-37 裁(或按正本字面同归删除方向);wish_trial.md §2.2 族级判据建议中「判据直调支可豁免保留」的一半随本裁决失效,失效对账随 T-37——防 T-37 对账时正本规范条与在册稿建议两口令来源冲突。
2. **族面形态标签统一裁决面(F-3 销项后的唯一残留)**:F-3 经词义定谳与在册判例核改判非偏差(§2.3),invest_env/invest_strategy/encounter/supply 各屏 §2 现状均判读合规、零改写义务;「全族画面篇 §2 是否统一前置分类层」= 用户裁决面,**唯一落点 = T-37 汇总登记并由其指派施工稿**(原「invest_strategy §2 补分类层归 T-6 稿增补」指针撤销——T-6 修订版全文无此施工项,指针落空);词义定谳(§2.3 判读框架)为该裁决的判读输入。
3. **共享文件一次成文**:`cw_overlay_pick_action.py` 的 F-5 命中面执行权 = T-6 §2.5(其清单 + 全文件扫描 + T-3 §2.6 准则已覆盖本报告点名各点:L227 T# / L282 task#+W / L342 日期+rN / 模块头批史);两稿禁重复触碰同段,先落者为准、后落者按落地时点现状对账销项。
4. **观察标准化门族面收敛(本稿升格产出的全域义务)**:观察标准化已入正本规范(op-layer.md §1.1「观察标准化门」,用户裁定 2026-09-22),投资环境屏随本稿落地批首个收敛。①投资策略屏孪生同构改造(观察层标准化 + `norm_name` 载荷退役 + `kernel/cw_action_report/pick_invest_strategy.py` 同款纯 idx 收窄 + `cw_vocab.py` 同字段退役)= **T-6 稿扩项**,随 T-37 登记移交,两屏修法口径必须一致;②其余名字类观察屏(角色/装备/事件选项等)的存量收敛 = 各屏审查批/T-37 汇总分配;规范已立、新增禁令即日生效(禁新增未标准化直报)。

- **已核对一致面**:审查报告 §3 十项一致面核对通过,本稿不立修法,仅作为各修法不得触碰的现状边界——落地时禁借清理之名改动这些在码语义(含 §3.6 局外分支现状,至 §1.7① 裁决前不动)。

## 2. 方案

### 2.1 F-1 修法:条件腿归属两处改写为现役契约

逐点位给目标语义(行文由实现者按画面篇既有风格组织,语义唯一):

| # | 位置 | 现状(病句核心) | 目标语义 |
|---|---|---|---|
| 1 | `screens/invest_env.md` §4 决策体图选卡分支括注 | 「session 形参显式传入[局外/测试 = None 登记腿跳过];欢愉契约 provisional 条件腿随获得链回调 on_env_gained 枚举迁移,行为逐位等价)」 | 「session 形参显式传入[局外/测试 = None 登记腿跳过]。环境即时效果腿 = `on_env_gained` 枚举(`ENV_GIFTS` `chars_immediate` 送卡入席 / advisor 申报分道);欢愉契约条件腿**不在该枚举**——触发事件 = 头号玩家选项弹窗被处理(银狼策划选择上报),授予 = 条件腿 rider `kernel/cw_action_report/pick_planner.py::_grant_joy_conditional`(`active_env` 欢愉契约在册 → `gain_character` 1★ rand=True,写端 = rider 链内落位/合成写),正本 = `game_state/gain-chain.md` §3(落点链接复用本篇 §6 既有指针形 `../game_state/gain-chain.md`)」 |
| 2 | 同文件 §6 环境赠卡条 | 「`gain_invest_env` → `on_env_gained` 枚举 → `gain_character`(入席/溢出/升星链;欢愉契约 provisional 条件腿亦迁该回调)」 | 前半不动,句尾括注改:「(入席/溢出/升星链)。欢愉契约条件腿不在本枚举(触发条件/写端/正本 = gain-chain.md §3;见 §4 选卡分支申报)」 |

依据(全点位共用):代码真值 = `kernel/cw_gain_chain.py::on_env_gained`(仅消费 `chars_immediate` + advisor 分道;docstring「欢愉契约条件腿不在本枚举」)+ `kernel/cw_action_report/pick_planner.py::_grant_joy_conditional`(读 `ENV_GIFTS['欢愉契约'].chars_conditional` 名集采样授予,消费 `active_env` 在册判定);规范条款 = `game_state/gain-chain.md` §3 on_env_gained 条「欢愉契约条件腿**不在本枚举**:正式模型 = 银狼策划选择上报落地相的条件腿 rider」。指针落 gain-chain.md §3(条件腿契约唯一正本位);`strategy-docs/13_pick_family.md` 为决策判据面、与效果腿归属无涉,不增指针(防第二源)。「provisional」措辞随改写退役(该腿已按正式模型定谳,gain-chain.md §3 用词 =「正式模型」)。目标文本内文档指针一律纯文字;落点 = screens/invest_env.md,链接 href 按落点文件既有链接折算,禁照抄本稿路径基(同款表注见 §2.3)。

**取舍**:备选 = 仅删两句错句、不补正确归属——放弃:§6 是「状态上报面」,获得链效果腿的归属申报是本节职责;删句留白则读者仍须自行考古触发时点,只修了「错」没修「误导」(报告差距说明的病灶在触发时点理解);补一句 + 指针,零复述链参数细节(候选集/采样/rand 纪律单一源仍在 gain-chain.md §3 与 `cw_investments.py` 数据表)。

### 2.2 F-2 修法:§9 宣称修正为 as-built + 锁面缺口登记

**文档面**(`screens/invest_env.md` §9 测试锁行,一条替换为两条;零代码改动):

> - 测试锁(逐项与测试实存对齐):观察门 miss 早退 + 候选一次读落容器 `invest_env_opts` + obs 挂实例属性 = `test_cw_obs_arch_phase_screens.py::test_invest_env_observe_gate_and_report`;派发即终结 + 派发时点写入对拍(active_env 已写) = 同文件 `test_invest_env_active_env_written_at_dispatch`;机械链与类型分派 + 刷新零效果对账留证(`invest_env.refresh_no_effect`) = `test_cw_unified_action_4.py`(投资 op 锁 + `test_invest_env_refresh_no_effect_reconcile_records_defect`);portal 链与防污染 = `test_cw_yinlang_phase32.py`;命名/sig/写入域完备锁 = `test_cw_screen_report_ports.py`。
> - 锁面缺口(登记,自带消亡判据:**消亡条件 = 对应测试锁在册**,补测落地时由该批摘除本条):①`env_refresh_left` 观察写端双腿(值写入 / 读缺跳写)零断言——观察行为锁的计数读桩恒空、report ports 用例 obs 未设 refresh 字段;②本屏空候选零盲发锁缺位(同形锁在册先例 = 策略屏 `test_invest_strategy_empty_opts_fail_not_blindfire`)。

依据:逐项对齐实测 = `test_cw_obs_arch_phase_screens.py::_make_env`(计数桩恒 `[]`,L225-226)/ `test_cw_screen_report_ports.py`(`_case_invest_env` L223-225 obs 无 refresh、空桩 L325-326 只断 opts、supply 同腿锁 `_case_supply_node` L214-220)/ 全测试树 grep `env_refresh_left` 仅 `test_cw_game_state_opening_seed.py` 字段清单;规范 = screens/README.md §2 模板第 9 节(测试锁文件指针)与「as-built 无状态」纪律、`game_state/fields.md` §3.4.3(该写端应可被锁验证)。

**补测方向(登记于本稿;实现者无需再设计;属「待用户认同后落地」面,落点 = 测试仓)**:

1. `test_cw_screen_report_ports.py::_case_invest_env`:obs 补 `refresh=(2, x, y)` → 期望表补 `{'env_refresh_left': (2, 'logic')}`(supply 同腿先例 = 同文件 `_case_supply_node`);空桩表 `_EMPTY_OBS_CASES['invest_env']` 的 obs 补 `refresh=(3, x, y)` → 期望补 `env_refresh_left=None`(摄入序先例 = 同表 encounter 行:options 空 = 整函数早退不写含 left)。
2. `test_cw_obs_arch_phase_screens.py::_make_env`:`read_invest_refresh_counts` 桩恒 `[]` 参数化(缺省行为不变);观察锁或新增一锁走真计数值,断言 report 落 `env_refresh_left`(值 = 桩读数首条)。
3. env 空候选零盲发锁(建议名 `test_invest_env_empty_opts_fail_not_blindfire`):obs 装载 `options=[]` → act = round_fail 读缺文案、零派发零点击(策略屏同形锁同构,`_make_env` 桩面直接承载)。
4. **缺口登记条的寿命义务**:§9「锁面缺口」条自身 = 会失效的现状快照,故其条文自带消亡判据(消亡条件 = 对应测试锁在册);补测批落地时**同步摘除该条**(摘除义务列入补测批 landing 清单)——防补测落地后 §9 新增 F-6 同类无主存量。依据 = AGENTS.md §9(会失效的现状快照禁入正文)+ screens/README.md §8(篇末缺口申报面在册:「测试锁断档等见各篇文末」)。

**取舍**:方向②(修正宣称)+ 缺口登记,弃方向①(只登记缺口、宣称不动)——正本宣称与实际覆盖相符是 as-built 纪律的直接要求,只登记不修 = §9 继续虚报,回归信任面虚增原样保留(报告 F-2 病灶);补测方向随缺口一并写死 = 补测批无需再设计,但补测是落码,须过用户认同门(本迭代只设计不落码)。备选②的子选项「直接补齐测试」不在本稿——越权落码,同违迭代边界。

### 2.3 F-3 处置:改判非偏差·销项(沿在册判例),判法保留为族面判读框架

**处置 = 沿 T-5 在册判例改判:F-3 零修法、零落地面。**

- **判例如实申报**(依据 = T-5 审查报告 :118 原文,已逐字核对):「『单选族例外』标签沿 README §2 模板三选一并按 §3 括注(visit 内无后续决策消费)口径使用,**族内(invest_env.md)同款,分类权威 op-layer §3 记全形态——不构成偏差**」——判例辖两面:①括注前提按 visit 口径使用合法;②「标签沿用 vs 权威总表记全形态」的口径差 = 非偏差,且明文点名本屏同款覆盖。
- **词义定谳(判读框架,保留)**:①逐屏分类唯一权威 = `screens/op-layer.md` §3(screens/README.md §3 自文背书),「单选族例外」标签 = 模板族层标记不承载分类;②README §2 模板第二节「三选一」= 行文模板菜单非分类总表,括注保留合法——族内先例 = supply.md §2(同判例);③「零逻辑态账」词义 = **visit 消费读法**:在册定义单一源 = README §3 自文「单选族例外:有选择面但零逻辑态账(**选卡/确认即终结,visit 内无后续决策消费逻辑态**)」,该句为此短语唯一正本定义,判例支撑理由即此读法;据此投资/遭遇/补给三域(收窄条款例外三腿①②③,选择事实/后果腿写端均在动作执行侧)括注按在册定义均非失真断言。三句 = T-37 裁族面统一时的判读输入,非本稿修法依据。
- **§2 目标形撤销**:`screens/invest_env.md` §2 **零改动**——「全形态」前置分类层方案作废(取舍);§2 现状行为描述与代码一致,分类权威在 op-layer §3 随文可查。

**显式裁决语句(与 T-5 判例的关系)**:本稿**沿判例、不推翻**——判例已裁「标签口径差」面并明文点名本屏,F-3 残留病面全部落入其辖域,改判非偏差;判法三句与判例同读法(visit 消费),系判例支撑理由的显式化,非新裁定、非第二裁决源。

**取舍(N-1 二选一,取①沿判例)**:

- **取①(沿判例,改判销项)**:判例明文覆盖本屏同款面并终判非偏差,维持修法 = 修判例判定不存在的病(核三治本不成立);撤修法零损失;族内零新态(不制造「全族唯一携带 §3 型名」的孤例)。
- **弃②(保留修法 + 申报推翻判例)**:推翻在册判例须给出判例错误的具体依据,本稿无(其支撑读法经词义定谳核实成立);且前置分类层 = 预支 §1.7② 挂起的 T-37 族面裁决——若裁否,本屏即族内孤例,正触本稿 §1.7① 反对的「两屏两态」。用户若裁族面统一,由 T-37 指派的施工稿落笔,本稿不预支。
- **严重度重估**:F-3 由「中」改判「非偏差·销项」;残留开放面 = 「全族画面篇 §2 标签统一与否」,性质 = 用户裁决面非规范病,唯一落点 = T-37(§1.7②)。
- **孪生与族面**:invest_strategy/encounter/supply 三屏 §2 标签同款,同在判例覆盖语义内,同判非偏差、零改写;原「invest_strategy §2 补分类层归 T-6 稿增补」让渡指针撤销(T-6 修订版全文无此施工项,指针落空,见 §1.7②)。

### 2.4 F-4 修法:观察标准化门落地 + 动作链收窄纯 idx + 链内防御纵深

**① 观察层标准化门(核心,用户裁决 2026-09-22;规范单一源 = op-layer.md §1.1「观察标准化门」)**:

`operations/cw_screen/cw_screen_invest_env.py` 观察链(`_read_options` 候选读出后、组装 obs 前)新增转换步骤,**逐候选**两段:

1. 形变归一:`normalize_invest_name` **单一源**(其 `'：'`→`':'` 全角冒号形变**并入函数本体**——原「形变族 `_INVEST_SEP_VARIANTS` 不含全角冒号、冒号归一由 `_canon_invest_name` 另行承担」的拆分形态随本修法收敛,观察侧/链侧归一自然同源;连带收益 = 策略支步 0 拒绝腿同获冒号族覆盖,原「冒号形变穿透策略支拒绝腿」缝隙一并治愈;现役调用方入参全为已归一名或应归一名,零行为影响);
2. 注册表匹配:归一结果精确命中注册表 → 标准名;不中 → LCS 相似匹配(`one_dragon.utils.str_utils::find_best_match_by_lcs(word, 注册表名集, 阈值)`,阈值常量住代码)→ 命中 = 标准名;
3. 两段皆不中 = 转换失败。

**任一候选转换失败 = 观察 node round_fail 整函数早退**:零写容器、零上报,交外循环重观察重读(与空候选零盲发同判法)。容器 `invest_env_opts` 值域自此收敛为标准注册名(契约登记 = fields.md invest_env_opts 节 + 本屏 §3/§6)。**匹配歧义边界**:两候选命中同一注册名 = 识别质量不足以区分,同判观察失败(卡面与注册表一一对应,重名命中 = 必有误读)。

**② 动作链收窄纯 idx**:

- 派发处 `norm_name=normalize_invest_name(chosen)` 组装删除;
- `kernel/cw_vocab.py` **仅投资环境** param 类的 `norm_name` 字段退役;投资**策略** param 类同字段**不随本批退役**——策略屏派发/上报/测试现役仍消费(删 = TypeError 选卡链崩),其退役与策略屏改造随 T-6 扩项批同批落地(§1.7④);
- `kernel/cw_action_report/pick_invest_env.py`:`_canon_invest_name` 与 noop 分支删除;上报按 `param.idx` 从容器取标准名直传链;**容器缺读/idx 越界 = 响亮失败**(异常上抛,容器写腿零吞错同款——生产不可达:选卡链发生时观察必然已完成);reason 恒 `gain_chain_applied`(与 action_ops.md §4.5 行声明一致,`landing_noop` 私词消失);docstring 改「名字标准化契约 = 观察层(op-layer.md §1.1),本函数零名字转换」。

**③ 链内无效载荷拒绝腿(防御纵深)**:

`kernel/cw_gain_chain.py::gain_invest_env` 增步 0(镜像 `gain_invest_strategy` 步 0 形态,判式同 gain-chain.md §2.4-0):

```python
canon = normalize_invest_name(str(env_name or ''))
if not canon or canon == '?':
    _emit_defect(field_name='active_env',
                 expected='有效投资环境名',
                 actual=f'无效载荷:{env_name!r}',
                 evidence='gain_invest_env', sig=sig,
                 kind=PICK_INVEST_INVALID_PAYLOAD)
    return GainOutcome(placed=False, landing='skipped', merge_levels=0,
                       effects=(), detail='invalid_payload')
```

后续 ①注册写 `canon`(替代现 `env_name` 原样写)②登记腿 ③`on_env_gained` 不变;docstring 增步 0 申报(无效载荷拒绝 = 零写 + 留证,输入校验非防重复保护)。生产路径观察层已保证输入恒标准名,此腿只对 sim/直调域兜底,与策略支对称;缺陷 kind 同词表(缺陷台账判读面单键)。
3. **正本登记面**:`game_state/gain-chain.md` §2.1 插步 0(措辞镜像 §2.4-0:「**无效载荷拒绝(前置)**:归一后名为空/`'?'` = 零写 + 缺陷留证(`kind = pick_invest_invalid_payload`)——无效输入拒绝,非防重复保护」,后续三步语义不变);**同节尾段随步 0 收敛**(「直接写语义(零幂等闸):无条件注册 + 无条件触发效果——…」与步 0 字面冲突,改写为:「直接写语义(零幂等闸):**有效载荷**无条件注册 + 无条件触发效果(无效载荷拒绝见步 0,输入校验非防重复保护)——投资环境不会第二次给相同牌(游戏事实),重复上报只可能是代码 bug,按 bug 治理(action_ops.md §1 增补 2)」);§6 尾句「无效载荷拒绝(§2.4-0)」→「(§2.1-0/§2.4-0)」。`flow/action_ops.md` §4.5 PickInvestEnv 行:补「无效载荷拒绝 = 链内零写留证 `pick_invest_invalid_payload`」与「观察层标准化门 = 标准名直传,上报 = idx,名字自容器标准名单一源(规范 = op-layer.md §1.1)」。`screens/invest_env.md`:§3 观察段补标准化门语义、§4 决策输入改标准名口径、§5 终结表补「观察转换失败 = round_fail 交回重观察」行、§6 active_env 条补括注「(链内无效载荷拒绝 = 零写留证,正本 = gain-chain.md §2.1 步 0)」。

**测试面**(待用户认同后落地):
1. 观察标准化锁:候选含可转换名 → 容器存标准名(LCS 命中路径含内);候选含转换失败名(乱串/未注册)→ round_fail、零点击零写;两候选重复命中同一注册名 → round_fail;
2. 动作纯 idx 上报锁:idx → 链收容器同序标准名;容器缺读/idx 越界 → 响亮失败;锁族指正——param 字段面锁 = `test_cw_action_report_contract.py`(参数冒烟锁遍历全部动作类型以裸容器调真上报函数,随「按 idx 取名」新契约改造:容器播种,或按「容器缺读 = 响亮失败」断言;**该文件必须列入落地批**,否则 F-4 落地冒烟锁必红),`test_cw_screen_report_ports.py` 实辖 obs 类/report 函数在场面、不辖 param 字段;环境类字段退役后字段面锁随行更新;
3. 链拒绝锁:`test_cw_gain_chain.py` 增 env 支拒绝锁——`gain_invest_env(gs, None, '', rand=False, sig)` → `detail == 'invalid_payload'`、`active_env` 值不变、缺陷行 `pick_invest_invalid_payload`(策略支同形先例同文件);
4. 局外 handback 锁:match=None + 非空候选 → round_success、点击记录为空、零派发零上报(§1.7①)。

**行为变化申报**:①垃圾名/未注册名从「照选照点、效果不记账、容器留脏值」变「观察失败零点击零写交回重观察」;②OCR 偶发误读从「可能照选(fallback 分不低时)」变「该访问 round_fail 重读」——随机误读有自愈机会,持续误读或注册表缺数据 = 循环失败至哨兵报警逼修数据(与空候选判法「没有选到就是代码 bug」同款);③名字转换点从动作侧两处收敛为零(观察一处),noop 假成功形态消灭;④局外单跑不再选卡(零决策交回,§1.7① 裁决);⑤生产选卡路径点击行为零变化(标准名命中时,原路径归一名与标准名同值)。

依据:用户裁决 2026-09-22(F-4 观察标准化门三轮口径对齐 + 局外单跑不支持);正本规范 = op-layer.md §1.1「观察标准化门」「画面 op 不支持局外单独调用」两条(2026-09-22 先行入);代码锚 = `pick_invest_env.py`(noop 分支/`_canon_invest_name`)/`cw_screen_invest_env.py`(未注册 warning fallback、`norm_name` 派发组装、局外 else 分支)/`cw_gain_chain.py`(`gain_invest_strategy` 步 0 先例、`gain_invest_env` 现役链体)/`cw_vocab.py`(`norm_name` 字段)/`cw_investments.py::normalize_invest_name`(形变族);工具 = `one_dragon/utils/str_utils.py::find_best_match_by_lcs`;规范 = gain-chain.md §2.1/§2.4-0/§6、action_ops.md §4.5。

**取舍**:修法位置三选——观察层(裁决采纳)vs 决策出口守卫 vs 动作/链侧(原稿方向 A 单独成案)——取观察层:①用户裁定的职责位:「观察的时候就要转成标准注册内容」,转换失败本质是识别质量问题,识别质量归观察域;②防线最前,点击之前零偏离(决策出口/动作/链侧的任何防线都在点击之后,容器与游戏偏离已不可逆);③下游全链(决策打分/动作/上报/链)统一在标准名世界工作,职责单一。链内拒绝腿(原方向 A)降格保留为防御纵深:sim/直调域绕过画面 op 直调链时响亮暴露,与策略支对称,防第三支链式动作逐支重裁(跨件半问)。kernel 打分 fallback 不动:标准化后生产不可达,本体属策略域判据。

### 2.5 F-5 修法:审查对象注释卫生(准则沿用 T-3,登记命中面与豁免面)

**清理准则 = T-3 设计稿 battle_wait.md §2.6 五条**(禁形一·会话局部标识符 / 禁形二·变更史叙述 / 改写方向·「结论→出处→边界」当前时态 / 保留豁免 / 一次成文),本稿不重复定义。范围 = 本稿辖域四文件全文件扫描(`cw_overlay_pick_action.py` 执行权 = T-6 §2.5,§1.7③);验证门见本节末(双层,门一模式 = T-3 模式 + `changes/` 引用扩项)。

**命中面与处置**(已核对命中集 = 报告点名 + 核读补充;施工 = 全文件扫描为准,表列点逐条销项,表外命中按验证门停手令处理;行号为定位辅助):

| 文件 | 点位(现文摘要素) | 处置 |
|---|---|---|
| `cw_screen_invest_env.py` | 类 docstring(L61)「OCR 卡名 → decide_event 打分」 | 准则3 改写方向(陈旧概述收敛当前语义;陈旧非变更史,准则 2 扩展适用,处置方向同):改现役口径「零参决策(候选自容器槽,策略器 `decide_invest_env`;判据 kernel `decide_event`)→ 刷新终结臂 ∨ 选卡确认链派发」 |
| 同上 | L69「放宽 [360,410] 容变;原 [378,408] 漏 y<378 的卡名」 | 准则2 变更史清出;保留当前带宽语义(卡名行 y 带 360-410,卡名 y 随立绘漂移,带宽覆盖实测漂移域,出处改纯语义) |
| 同上 | L93 / L149「批4 比对收口」×2 | 准则1 批号清出;保留「刷新臂只读不比、读数原样携带;比对宿主 = 终结交回出口对账,消费即清」 |
| 同上 | 「用户裁定 2026-09-14/21」日期(L5-6 与 L16 模块 docstring、L160-161、L188-189、L204-205、L230-232;核读补充,报告未点名) | 准则3(用户裁定日期随变更史清出,裁定语义保留并指正本条款):日期与引语清出;指针 = 刷新终结 op-layer.md §1.4、派发即终结/零盲发 op-layer.md §1.1 + action_ops.md §1 增补 2;L5-6 保留「零稳定帧等待一次读全」现役语义(与屏文档 §3 同文) |
| 同上 | L65「实测(2026-08-04):…」 | 准则3:日期清出改纯语义(「实机点验:点立绘/卡名不选中且开详情,描述区 y≈450 才选中,卡底无效」);选中几何判据语义逐字保留 |
| 同上 | L82-83「归档帧 sr-od-test/screens/…/default.webp 亮像素簇质心」 | 豁免保留(归档帧路径 = 持久索引;L84-86 刷新未命中能力退化语义、L88 同值先例指针均保留) |
| 同上 | L78 常量区注「(3.8;执行层时序/几何常量…)」裸「3.8」无文档名设计节引用 | 定性 = 设计件引用(会话局部不可解析):准则1 清出 →「环境刷新执行链常量(执行层时序/几何常量,非策略数值,ADR-0529 先例)」;ADR-0529 引用豁免保留 |
| 同上 | L242「safe_click 带 bug#1 mouse_move 缓解」裸缺陷件编号 | 定性 = 缺陷件引用(会话局部不可解析):准则1「bug#1」清出,保留机制语义「safe_click 自带 mouse_move 缓解」 |
| `kernel/cw_gain_chain.py` | 模块 docstring L29-32「详设 = changes/2026-09-21-invest-landing-chain/details/gain-chain-file-split.md」(changes/ 过程件引用 + 内嵌日期) | 准则1 过程件引用清出(T-3 准则 1 字面辖 .debug 类 gitignore 过程件;changes/ 引用清出判据 = 根 AGENTS.md §9 铁律「代码与正本文档禁引 changes/」)+ 内嵌日期随准则3 清出;收敛为「效果内容住 `cw_gain_effects.py`,本模块模块级查表 + 效果体惰性 import 单向破环;拆分契约正本 = gain-chain.md §8(模块拆分段)」;与 §2.4 修法同文件一次成文。同源登记面:gain-chain.md §8 自身的 changes/ 引用 = 正本禁引面残留,归正本维护(§2.7) |
| 同上 | 缺陷 kind 词表注 L77-78「未观察两 kind(bench/equips)已随开局种子底座与锚定闩批退役——…」(「已随 XX 批退役」句式) | 准则2 批次叙事清出(本稿判据从从严选 T-3 准则 2,不启用 prep.md §2.5.3「退役申报史注句式」豁免——两姊妹稿豁免集差异归 T-37 汇总统一,此处置不依赖该豁免,非两可);保留现役语义 + 正本指针:「未观察两 kind(bench/equips)现役生产不可达:开局种子底座下生产链路阵容/装备域不再有 None,拒落档零写无缺陷发射(词表退役申报正本 = gain-chain.md §6)」 |
| 同上 | on_env_gained docstring L604-605「锚 pick_invest.py 骇客 bench 腿同款口径」、L607「先例 = pick_invest hacker shop_pool decl」(引用目标 = 已拆分退役文件,不可解析) | 定性 = 死索引(引用目标实存性违例,根 AGENTS.md §8「引用必须是持久索引」;与 L78「3.8」/L242「bug#1」定性行同族):死引用清出换现役符号锚/纯语义——前处改「1★ 先验同句式先例(骇客效果体同族,现役 = `cw_gain_effects.py::PICK_INVEST_EFFECTS`)」;后处改「先例 = advisor 申报行同族(正本 = gain-chain.md §3 advisor 条)」 |
| `kernel/cw_screen_report/invest_env.py` | report 函数 docstring L50「用户裁定 2026-09-21」 | 准则3 日期清出;保留「屏上数字即真值」语义(指 fields.md §3.4.3 / op-layer.md §1.4 剩余语义写端);与同文件 L54-55 平移史清理一次成文 |
| `cw_overlay_pick_action.py` | L227「T#103」、L282「task#103 化债,W265」、L342「2026-08-06 r6 stall」、L3/L6 迭代件引用、L15-23/L293-295 批史与废除史 | 执行权 = T-6 §2.5(其全文件扫描 + T-3 §2.6 准则覆盖上述各形);本稿仅登记核对点,禁重复触碰(§1.7③) |
| `kernel/cw_action_report/pick_invest_env.py` | 模块头 L7-9「自 pick_invest.py 拆分(投资两屏迁移批;…废除分步形参)」拆分史段(T-6 §2.5 明文移交本稿) | 准则2:拆分史段删;保留「即时上报形态」段(申报正确)+「本包 → 容器单向依赖」句(目标尾形与 T-6 §2.5 `pick_invest_strategy.py` 行同构);与 §2.4 修法同文件一次成文 |
| `kernel/cw_gain_chain.py` | `gain_invest_env` docstring L451-453「原点卡前写退役…新写端新名不沿用旧名伪装连续」 | 准则2 变更史清出;收敛当前语义「注册 = `active_env` 逻辑写(写端署名 = producer;选择事实产生在动作执行时,契约 = gain-chain.md §2.1)」;与 §2.4 修法同段一次成文 |
| `kernel/cw_screen_report/invest_env.py` | L54-55「原写点『读得才写』闸逐位平移」 | 准则2 平移史清出;保留「names 空 = OCR 未读得,整函数早退不写」现役语义 |

**豁免面**:T-3 §2.6 准则 4 全集适用(ADR 引用;`screen_flow_timing #N`;screen_info 坐标/兜底常量/area 定义注——含本屏「首选 area_center + 常量兜底」关系注 L64-67/L76-77/L87;「实测/实机点验」纯语义描述;归档帧路径)。投资域特有豁免:刷新零效果留证语义(L84-86 偏移错能力退化非事故边界)、`_EXCLUDE` 排除表与 OCR 过滤带语义、变异窗 `ENV_GRACE_S` 定义注(无禁形,零改动)。

**验证门(双层,防命中面/验收夹缝)**:①表列点逐条销项为主(每行处置落地);②机械兜底 grep = T-3 §2.6 门一模式 + `changes/` 过程件引用扩项(依据 = 根 AGENTS.md §9 禁引铁律),四文件零未登记命中(豁免面除外;`cw_overlay_pick_action.py` 按 §1.7③ 归属剔除);定性判据 = **注释内引用目标须实存,不可解析(死索引:引用已退役/不存在的文件、符号、设计件)= 表外命中停手**;扫描出现表外命中 = **停手回本稿提请处置,禁自行拍板豁免**;`uv run ruff check` 通过;`git diff` 确认零逻辑改动(F-4 触碰 `cw_gain_chain.py` 的 guard 块与 `pick_invest_env.py` 分支删除除外,以其自身判据验收)。

### 2.6 F-6 修法:invest_env.md 正文状态清理

| # | 位置 | 现状(引文) | 目标语义 |
|---|---|---|---|
| 1 | 篇头导语(L3) | 「职责:投资环境 overlay 一次访问——稳定帧观察 → …」 | 「稳定帧观察」改「一次读全观察」(与 §2/§3「零稳定帧等待一次读全」同文,消除自相矛盾) |
| 2 | §1 分发判定 | 「阶段一身份分发(号制已退役,不引 0x):id_mark 锚…」 | 「号制已退役,不引 0x」清出 →「阶段一身份分发:id_mark 锚…」(变更史;报告记 §2,内容引文定位不歧义) |
| 3 | §2/§3/§6 | 「用户裁定 2026-09-21」×4(一次读全/选完即交回/零稳定帧等待/写时点) | 日期清出;裁定语义保留并指正本条款——一次读全/零稳定帧 = 句内现役行为描述自足;选完即交回 = op-layer.md §1.1 + README.md §6;写时点 = 动作执行时 = action_ops.md §1 增补 2 + gain-chain.md §2.1/§8 |
| 4 | §4 闸败重调括注 | 「(等价旧「idx + refresh_slots 并载、闸败回退选卡」行为,零选卡漂移)」 | 变更史对照清出;保留「策略侧同帧去重:建议帧首调发建议、紧随重调落选卡,零选卡漂移」 |
| 5 | §4 选卡分支 / §6 环境赠卡条 | F-1 错句(内含「随…枚举迁移,行为逐位等价」变更史) | 随 §2.1 改写一并清偿,不重复立项 |
| 6 | §3 / §6 | 「原 log 观察通道已升格 obs 正式字段」×2 | 删(现役描述「report 摄入写 env_refresh_left」自足) |
| 7 | §8 读缺守卫条 | 「无帧 = 刷新链跳过(旧调用形兼容)」 | 「旧调用形兼容」清出 →「无帧 = 刷新链跳过」 |

依据:AGENTS.md §9(变更历史禁入正文)+ screens/README.md §2 纪律(裁定日期不进正文)+ T-3 §2.6 准则 3(裁定语义保留可指正本条款)。

**取舍**:备选 = 连「用户裁定」语义一并删——放弃:裁定语义(零稳定帧/派发即终结/剩余语义写端/写时点)是行为判据的规范出处,删语义即丢依据;T-3 准则 3 明文保留语义、只清日期与批次叙事。

**验证门**:invest_env.md 全文 grep「2026-09-14|2026-09-21|号制|旧调用形|逐位平移|升格|等价旧|稳定帧观察」零命中(逐条销项);修后行为描述与代码复核一致(报告 §3 一致面为边界,禁借清理改动在码语义)。

### 2.7 落地文件面总表(合并实施对账用)

| 文件 | 修法点位 | 性质 |
|---|---|---|
| `screens/op-layer.md` | §1.1 规范条两枚(观察标准化门 + 画面 op 不支持局外单独调用,**用户裁决 2026-09-22 已先行入正本**) | 正本规范(已入,落地批核对引用即可) |
| `screens/invest_env.md` | F-1(§4/§6)+ F-2(§9)+ F-6(全篇状态清理)+ F-4(§3 观察段/§4 决策输入/§5 终结表/§6 括注)+ §1.7①(§4 伪代码局外行 / §5 终结表局外交回行) | 画面篇 as-built |
| `game_state/gain-chain.md` | F-4(§2.1 步 0 + 同节「无条件注册」尾段收敛 + §6 尾句) | 正本语义更新 |
| `flow/action_ops.md` | F-4(§4.5 PickInvestEnv 行补拒绝腿 + 标准化门/纯 idx 语义) | 正本登记 |
| `game_state/fields.md` | F-4(invest_env_opts 值域收敛标准注册名;具体节落地对账) | 正本语义更新 |
| `kernel/cw_gain_chain.py` | F-4(步 0 guard + 注册写 canon + docstring)+ F-5(同段 docstring 卫生,一次成文) | 行为小变更 + 注释 |
| `kernel/cw_action_report/pick_invest_env.py` | F-4(`_canon_invest_name`/noop 分支删除 + 纯 idx 取名直传链 + docstring)+ F-5(模块头拆分史,一次成文) | 行为小变更 + 注释 |
| `kernel/cw_vocab.py` | F-4(**仅投资环境** param 类 `norm_name` 字段退役;策略类字段归 T-6 扩项批,§1.7④) | 契约收敛 |
| `operations/cw_screen/cw_screen_invest_env.py` | F-4(观察层标准化门 + 局外 else 分支删除 + 派发处 norm_name 组装删除)+ F-5 注释卫生 | 行为变更 + 注释 |
| `kernel/cw_screen_report/invest_env.py` | F-5 注释卫生 | 注释 |
| (执行权 T-6 §2.5)`operations/cw_op/cw_overlay_pick_action.py` | F-5 登记面(§2.5,禁重复触碰) | 注释 |
| (待用户认同)`sr-od-test/.../test_cw_obs_arch_phase_screens.py`、`test_cw_screen_report_ports.py`、`test_cw_action_report_contract.py` | F-2 补测(§2.2 三条)+ F-4 观察标准化锁/纯 idx 上报锁(含 contract 冒烟锁改造)/handback 锁(§2.4 测试面 1/2/4) | 测试 |
| (待用户认同)`sr-od-test/.../test_cw_gain_chain.py` | F-4 env 拒绝锁(§2.4 测试面 3) | 测试 |
| (登记面,不落本稿)全族画面篇 §2 标签统一裁决面(T-37 汇总裁决并指派施工稿;含 invest_strategy.md §2,判例同款覆盖)、gain-chain.md §8 自身 changes/ 引用(正本禁引面残留,归正本维护)、T-6 稿孪生扩项(投资策略屏观察标准化 + norm_name 退役,§1.7④)、其余名字类观察屏标准化收敛分配 | §1.7①②④ / §2.5 | 登记面 |

统一验收:除 F-4/局外删除外全部零行为变化(`git diff` 无逻辑 diff);F-4 以其行为变化申报与测试锁验收;文档面互查——invest_env.md 修后与 op-layer.md §1.1(两新规范条)/§2.2/§3、gain-chain.md §2.1/§3、action_ops.md §4.5、README.md §6 口径一致。
