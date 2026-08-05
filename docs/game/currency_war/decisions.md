# 货币战争 · 决策日志(Decision Log)

> **试点规范(2026-08-03,暂仅货币战争)**:设计文档 = **干净的正文(strategy/)= what** + **本日志 = why**。
> 正文只讲"设计是什么",依据/备选/历史放这里,分开不混写。
>
> **格式**:append-only 按时间倒序(新决策加在顶部)。每条 `D-NN` 紧凑条目:
> - **决策**:一句话 what。
> - **为什么**:why(用户定调/实据/权衡)。
> - **备选**:考虑过什么、为什么不选(**最值钱的字段**,防后人重复扯皮)。
> - **状态**:采用/实验/推翻。反转用 `↺ 推翻 D-XX`。
> - `· §X` 反引到正文(strategy/0N 或 data/)。
>
> **粒度**:密度可变 —— 重磅架构决策多写,权重/数值一句话。不追求一决策一文件(决策多,奢侈)。
> 老条目不改正文(append-only);推翻就新写一条标 supersedes。

---

## D-33 (2026-08-05) maybe_pivot 信号2 加「已成型守卫」(不放弃已完成 comp)· cw_comps
- **决策**:`maybe_pivot` 信号2(ceiling 不可达 → 切 easy)加守卫 `form_progress(target, state) < 1.0` —— target 已成型(board 全 tier 达成)时**豁免**信号2,不因 `typical_form_round > remaining` 切走已完成的 comp。
- **为什么**:原逻辑 `if target.typical_form_round > remaining:` 无视成型度 → 已成型的 target(plane3 后期 remaining 小)会被误判"来不及成型"切走 → 放弃已完成的强 comp 转切 easy,反而变弱。**正确性 bug**(不该放弃已完成 comp),非调参。补 maybe_pivot 信号1+2 测试时发现。
- **备选**:① 不修(推翻:已成型 comp 是最强态,切走=自毁);② 守卫用 `< 0.9` 而非 `< 1.0`(推翻:0.9 近成型仍可能来不及,该让 `form_round>remaining` 判定;只有全成型 1.0 才确定不该切)。
- **状态**:采用。+ 1 测试(`test_maybe_pivot_formed_target_no_ceiling_pivot`:阿雅成型 board={昼之半神:4}+ plane3 round5 remaining≈1 → 不切);cw_comps 30 测试绿。· `cw_comps.maybe_pivot` 信号2。· §03。

## D-32 (2026-08-05) difficulty → hp_safe_threshold 派生(向后兼容,A8 高难保血地基)· cw_state / cw_decisions / config
- **决策**:加 `GameState.difficulty`(A1..A8,匹配开始从难度确认屏检测)+ `CurrencyWarConfig.difficulty_hp_override`(难度→保血阈值映射,默认 A1-A4=40 不变 / A5+ 升阶)+ `effective_hp_threshold(state, config)`(cw_state)。3 处阈值读取统一走它:evaluate → `_phase_weights`、plan → `_refresh_cap`、`maybe_pivot`(0.75×)。**向后兼容**:difficulty 未检测("")或 override 无对应键 → 回退 `hp_safe_threshold`(默认 40 = `HP_DANGER`),行为与加 difficulty 前**完全一致**(detection 未接线时零变化)。
- **为什么**:cw_decisions 长期 TODO(:194「待 difficulty 字段」、:206「待补 A8 difficulty 信号」)—— A8 高难敌人更凶,固定 threshold=40 偏低(过晚弃息保血 → 失血过多);高难应更早保血。**离线地基**:detection(难度确认屏 OCR → `state.difficulty`)是后续 game 接线任务;本改动先把「阈值随难度变」的 plumbing + 派生函数 + GameState 字段就位,detection 落地即生效(不再动决策代码)。关 D-18(hp 阈值统一)的 difficulty 维度。
- **备选**:① 直接改死 `HP_DANGER` 常量(推翻:全局生效、低难也变、不向后兼容,A8/低难该不同阈值);② 加 difficulty 字段但不派生、等 detection 全做完再接(推翻:detection 时要同时改字段+函数+3 处位点,更碎;先做离线地基更稳,且向后兼容不破坏当前未验证跑)。
- **状态**:采用。代码 + 5 新测试绿(`test_effective_hp_threshold_*` ×4 + `test_eval_difficulty_aware_hp_threshold` 集成证 difficulty 改变 eval 行为);现有 cw_decisions/cw_comps 测试向后兼容通过。`DEFAULT_DIFFICULTY_HP`(A5+ 升阶)是**保守起步,待实机校准**(detection 接线后看 A8 实际失血曲线调)。· `cw_state.effective_hp_threshold` / `currency_war_config.DEFAULT_DIFFICULTY_HP` / `cw_decisions` evaluate+plan / `cw_comps.maybe_pivot`。· §02A3。

## D-31 (2026-08-04) 巨星卡死真根因 = bug#1(↺ 推翻 D-30 的"2 步缺 step2")· run_megastar_node
- **决策**:巨星节点卡死 6min 的真根因是 **bug#1**(确认 click 走 `round_by_ocr_and_click`,其 `before_screenshot` 把鼠标移到角 → click 判 drag 被吞 → 确认永不落地 → flat loop 无限 `round_wait` 烧预算),**不是**漏选强化角色。强化角色**可选**(不选也能确认推进)。修 = `RunMegastarNode`:`mouse_move`+`click`(bug#1 零移动缓解,同 invest handler)+ RunNode 验证(overlay 消失=完成)+ 节点预算(点不动 bail,不再 2.5h 烧)。
- **为什么(实机,MCP + VLM 结合)**:① OCR ground truth ——「强化角色未选择」持续在,点确认(MCP `click_game` 直连、无 before_screenshot)后该字消失、overlay 关 = **节点推进了**;② open-prompt VLM —— 看到花火有**金色发光边框 = 已选中**(窄 prompt 之前漏看、误报"没选中"→ 误判缺 step);③ 综上:花火早被 bot 的候选 click 选中,唯一卡点是确认 click 被 bug#1 吞,我直连点确认一发即中。
- **备选**:D-30 的"补选强化角色 step2 / 候选选中机制不明"(↺ 推翻:强化角色可选非卡点;候选早选好了,D-30 的"选中机制不明"是窄-prompt 视觉大模型 漏看金边造成的误判)。
- **状态**:采用。`RunMegastarNode` 代码完成(ruff 净 + 导入/结构验);**行为验证待下次巨星节点**(bug#1 缓解后应一发推进;现游戏已过我手动推进的巨星、在备战 1-6)。· `run_nodes/run_megastar_node.py` / `battle_loop` 0b。
- **方法论(回应用户"prompt 限制 VLM" + "MCP 和 VLM 都用")**:① **VLM 探索未知画面先 OPEN prompt**(描述全部),窄/leading 问法**压制题外输出** —— 我窄 prompt 漏看金边 → 误判"没选中" → 误以为缺 step → 跑去问用户;open prompt 一眼看到金边。② **MCP(OCR ground truth)+ VLM(open 枚举/选中态)+ click(验证交互)三结合** —— 各取所长:OCR 可信、VLM 看非文本元素/状态、click 验行为。③ **这条经验 → `od-dev-screen-onboarding`(open 枚举)+ 视觉大模型 用法 memory(open prompt 先)**。

## D-30 (2026-08-04) 巨星节点机制缺口 + 早期恶性循环(实机发现,待解)· handle_megastar / 策略
- **决策(发现,非定案)**:① 巨星(位面首领,每位面第 6 关)是**2 步节点**(选候选成巨星 + 选强化角色 + 确认),`HandleMegastar` 只做第 1 步 → 确认被拒(「强化角色未选择」)→ 节点永不完成;② 但"候选怎么选中"**机制不明**(点卡片本体 (925,240) / 名字条 (820,333)/(920,343) 均不选;点「详情」能开浮层=点击落地✓;视觉大模型 状态推理不可信;web 搜索无果)→ 需用户/人肉实机观察;③ 更深:bot 早期战力弱 → 输回合 → 穷 → 升不起级 → 弱 comp → 继续输(**恶性循环**),level gate+saving(D-24/D-28)必要非充分。
- **为什么**:实机迭代(plane1 round6)暴露 —— 卡巨星 6min(75+ retry 屏完全不变,会转到 MAX_ITER 2000 ~2.5h);round6 gold=17 lv=4 付不起升级费 30,hp 100→58 在掉血。纯代码永远看不出。
- **备选**:① 凭 视觉大模型 猜巨星选中目标(推翻:视觉大模型 状态/交互推理不可信,memory `onboard-vision-required` 已记);② 跳过巨星(推翻:首领节点不可跳,必打)。
- **状态**:**待解**。巨星选中机制 = 知识缺口(问用户 / 看攻略视频);恶性循环 = 早期战力 + 经济策略问题(需策略迭代)。`RunMegastarNode` 待机制明后建(预算至少 fail-fast 不再 2.5h 烧)。· `handle_megastar` / 策略早期经济。

## D-29 (2026-08-04) RunNode 重构:对局内 op 按节点生命周期划分 · battle_loop / run_nodes
- **决策**:对局内主循环从「flat loop 逐帧重新发现」重构为「外层分类+委派 + RunNode 按节点生命周期 owner」。`RunNode` 基类(**committed-but-verifying + 节点作用域预算**):每轮验证"还在本节点?"(`_in_node`)→ 否=节点完成 `round_success`;是→`_do_action` 做一动作→`round_retry`(计 `node_max_retry_times` 预算;超→FAIL bail,不无限烧)。pilot = `RunSupplyNode`(从 `HandleSupply` 升级,动作不变只套验证+预算)。
- **为什么**:旧 `Handle*` 全是**盲单发**(做一次动作就无条件 `round_success`,从不验证节点真完成 / overlay 消失)→ 动作失败也回 success → 外层 flat loop `round_wait`(**不计 retry**)无限重派 → 卡死烧预算(巨星 6min / invest_strategy 18min / invest_env 卡死,**全这一个模式**)。flat loop 还把"我在哪种节点"和"节点哪一步"两条正交问题塞进一条优先级阶梯 → LCS 噪音 / precedence 脆弱。RunNode 分开:外层只分类(小集合稳定),RunNode 管节点内多阶段 + 验证完成 + 预算。
- **备选**:① 保留 flat loop 只加全局超时(推翻:治标,优先级阶梯/LCS 噪音/无节点作用域卡死判据的根因没解);② 大改成显式状态机(推翻:OneDragon 节点图 + committed-but-verifying 已够,无需另造)。
- **状态**:采用。基类 + `RunSupplyNode` pilot 代码完成(ruff 净 + 导入/结构验),**行为验证待补给屏**(被巨星 D-30 卡,推进不到补给);其余节点(encounter/partner/invest_strategy/invest_env/megastar/combat)待逐个迁移(先零件后整体)。方法论 + 完整设计:`.debug/temp/currency_war/runnode_decomposition.md`(**后续提炼进 od-dev skills** —— op 划分通用方法论)。· `battle_loop` 0e supply 分支 / `run_nodes/run_node.py` / `run_supply_node.py`。

## D-28 (2026-08-04) `_saving_for_level` 对齐 D-24 gate · cw_decisions
- **决策**:`_saving_for_level` = 想升(`level<10 AND (goal=level_up OR level<_expected_level)`)AND `gold<升级费` → 抑制散牌买/刷,攒钱升等级。
- **为什么**:D-24 gate 已按"落后期望也升"(修 chicken-egg:`_DEFAULT_LEVEL_GOAL[4]=roll` → lv4 不升 → 永远到不了 lv5),但 saving 仍按旧"goal=level_up"→ lv4 不攒 → gate 想升却付不起。saving 须与 gate **同口径**。
- **备选**:saving 按 goal=level_up(推翻:与 D-24 gate 不一致,lv4 永远不攒,gate 形同虚设)。
- **状态**:采用(代码 `d5e0aea7`)。· `cw_decisions._saving_for_level`/`_want_level`。**注:必要非充分** —— 实跑 round6 gold=17 仍升 0(太穷付不起 30,见 D-30 恶性循环)。

## D-27 (2026-08-04) RunLoop 事件 overlay 前置检测 + BuyShopCards 兜底 · battle_loop / shop
- **决策**:① RunLoop 把 投资策略/投资环境/补给 检测**移到备战前**(原 step 4 → 0e,与 选择伙伴/巨星/遭遇/未达上限 同列前置);② BuyShopCards guard 加事件 overlay 兜底(检测 投资策略/环境/补给/遭遇/伙伴/确认选择 → fail 交主循环)。
- **为什么**:实跑发现**投资策略屏被误派 BuyShopCards**(「购买经验」从 overlay 后透出 → 备战分支 step1 先命中 → BuyShopCards → overlay 遮商店 → "找不到商店"死循环)。根因:事件 overlay 叠备战、购买经验透出,但事件检测在备战后。事件必须前置(overlay 在就不进备战)。BuyShopCards 兜底防 loop 漏检/其他调用路径。
- **备选**:① 只移 precedence(推翻:BuyShopCards 单查购买经验不够,需 overlay 兜底防其他路径);② BuyShopCards 单查 overlay(推翻:loop 是主路由,precedence 是主修)。两者互补。
- **状态**:采用(纯代码,需游戏验证 —— 下次投资策略屏应路由 HandleInvestStrategy 非 BuyShopCards)。`· battle_loop / shop`。**通用**:overlay 态检测必须在 base 态前(overlay 会让 base 锚点透出)。

## D-26 (2026-08-04) app 中间态接手(state-aware resume)· currency_war_app
- **决策**:`CurrencyWarApp` 各入口 op(`_enter_lobby`/`_start_match`)先检测当前态,已在 CW(大厅「创业指南」或对局中态)就跳过、直接进 `_run_loop`。新 `_in_match` helper(OCR 锚点:购买经验/备战阶段/投资策略/投资环境/补给/遭遇/盛会之星/出战/挑战结束/请选择投资)。
- **为什么**:用户洞见 —— app 原线性流(EnterCurrencyWar→Start→Loop)只认大世界起点,从对局中态(投资策略/备战/战斗)重跑会卡 entry(EnterCurrencyWar 找不到 guide)。实测从投资策略跑 app 失败、只能直接跑 RunLoop 接管。bot crash/重启/手动接管后需从任意态 resume。各 op「已过就 skip」= 幂等 resume。
- **备选**:① app 开头一个 detection node 路由(推翻:每 op 自检更模块化,符既有 node_from 流);② 总从大世界重新进(推翻:丢对局进度 + entry 卡)。
- **状态**:采用(纯代码,需游戏验证 —— 下次从对局中态跑 app 应直接 resume 进 loop)。`· currency_war_app`。**通用洞见**:长流程 app(模拟宇宙/忘却之庭/历战等)都该支持中间态接手(crash/重启后可 resume,非总从头)。

## D-25 (2026-08-04) exit op 事件屏 escape(返回备战界面/Esc 关 overlay)· 入口 op
- **决策**:`exit_currency_war_match` 加事件 overlay escape 分支 —— 「返回备战界面」(投资策略/环境)→ 点回备战;其他事件(补给/遭遇/巨星/详情/可合成列表)→ Esc 关。放备战分支后、retry 前。
- **为什么**:实测从投资策略屏跑 exit → 卡 210s+(事件屏无「放弃并结算」/备战文本 → 全分支不命中 → retry 死循环)。修后:事件屏先 escape 回备战 → 走原 Esc→放弃→结算→大厅。
- **备选**:① exit op 开头无脑 Esc 到备战(推翻:可能误关结算页);② 每事件单独 handler(推翻:exit 只需 escape,不必理解事件)。按文本检测 escape 最小可靠。
- **状态**:采用(纯代码,需游戏验证)。`· 入口 op`

## D-24 (2026-08-04) level gate chicken-egg 修:落后期望等级也升(非仅 goal=level_up)· strategy/02 plan / 03 level_plan
- **决策**:`plan()` 升级 gate 条件从「goal=level_up + 够钱」扩为「够钱 + (goal=level_up **或** 落后期望等级 `_expected_level`)」。
- **为什么**:telemetry 6 局**全「升0次」**(gold 到 74 也不升)。根因:task#18(D-14)gate 只在 goal=level_up 时升,但 `_DEFAULT_LEVEL_GOAL[2,3,4]=roll`(非 level_up)→ gate 在这些等级不触发 → 永远到不了 5+(level_up 等级)→ **chicken-egg 卡低等级** → 弱 comp → 输。CW 起步 lv4 + goal[4]=roll → 永卡 4。「落后期望等级」兜底:不管 goal,等级跟不上节奏 + 够钱 → 升(经济统一论:落后该升)。
- **备选**:① 改 `_DEFAULT_LEVEL_GOAL[3,4]=level_up`(推翻:rigid,只解 lv4;「落后期望」更通用,适用任何掉队);② LevelUp 回归 eval 候选(推翻:task#18 D-14 已证 eval 短视永不选;gate 更稳)。
- **状态**:采用(7 level-up 测试绿,含新 D-24 测试)。**待干净对局验证**:下局应能看到升级(chicken-egg 解)。`· §02 plan / §03 level_plan`

## D-23 (2026-08-04) EnterCurrencyWar wait_lobby 防御性加固(前往参与仍在→重点击)· 入口 op
- **决策**:`wait_lobby` 加分支 —— `前往参与` 仍在(transport click 没落地)→ `round_by_ocr_and_click` 重点击。放「创业指南」(大厅)之后、弹窗/F 分支之前。
- **为什么**:全流程跑卡 `wait_lobby` 重试 37x 失败,根因:停在指南页(「货币战争」分类 + 「前往参与」按钮都在)→ F 分支(`货币战争 AND NOT 前往参与`)被跳过 → 无分支命中 → 死循环。上个节点(前往参与)的 transport click 没落地(bug#1)→ 角色没传送 → 停指南页。重点击兜底。
- **备选**:① 提 node_max_retry(推翻:不解决根因,仍死循环);② 改 F 分支条件(推翻:不该在指南页按 F)。防御性重点击 = happy path 不受影响(传送成功则前往参与消失,分支不触发)。
- **状态**:采用(防御性加固;**需游戏验证** —— 下个干净对局跑 EnterCurrencyWar 看是否还卡)。`· 入口 op`

## D-22 (2026-08-04) hp 阈值统一 config.hp_safe_threshold(D-18 unification 落地)· strategy/02 §A3
- **决策**:加 `config.hp_safe_threshold`(默认 40 = HP_DANGER);`_phase_weights(plane,hp,hp_threshold=HP_DANGER)`、`_refresh_cap(state,hp_threshold)`、`maybe_pivot`(`0.75×threshold`)签名加参数带默认。evaluate/plan 经 `getattr(config,'hp_safe_threshold',HP_DANGER)` 传入。
- **为什么**:02 §A3 要求 hp 阈值单一源(原散落 `HP_DANGER=40` + `maybe_pivot hp<30` 硬编码);A8 高难需调高阈值(difficulty 派生)。**默认 = HP_DANGER → 行为不变**(64 测试绿),但单一源 + difficulty 可调 + 偏移系数集中(转型 0.75×;死局 0.5× / 连败 1.5× 待相应函数实现时补)。
- **备选**:① 直接删 HP_DANGER 全走 config(推翻:默认值仍 40,保留常量作 default + 测试引用更稳);② 不做(推翻:design 02 §A3 指示 + 审计标的 divergence)。
- **状态**:采用(D-18 hp 项落地;64+1 测试绿)。`· §02 §A3`

## D-21 (2026-08-04) optionality_score + α(t) 纯函数(承诺-期权)· strategy/02/03 P1-1+F-3
- **决策**:实现 `optionality_score(state)`(bench 角色属 **≥2 COMP_LIBRARY comp**[``shared_chars ∪ core_chars``]→ 加分,保期权/容错)+ `alpha_t(state)`(总回合 <R_OPEN→0 纯期权 / >R_CLOSE→1 纯承诺,线性)。R_OPEN/R_CLOSE/OPTIONALITY_WEIGHT **值在代码**(阶段 6 实玩校准)。
- **为什么**:A8 方差生存战,过早 commit 单一 comp 遇克/缺牌即死(plane2 死因之一);保 ≥2 comp 可行 → 容错。design P1-1/F-3 标 high。
- **备选**:① 直接集成进 evaluate(推迟:改核心 eval 行为需 P0 游戏验证才稳,先做零件);② 不做(推翻:high 优先 + 直接关系 plane2 生存)。
- **状态**:采用(纯函数 + 2 测试绿;**evaluate 集成延后** —— ``α·target_progress + (1-α)·optionality`` 混合,待 P0 解阻后集成 + 游戏验证)。`· §02/03 P1-1/F-3`

## D-20 (2026-08-04) decide_supply 纯逻辑骨架实现 · strategy/07/08
- **决策**:实现 `decide_supply(options, state, target_comp, config, refresh_used) → SupplyPick`(纯函数,design 07/08 骨架)。规则:带钻(红/蓝)→ 选(基本赢,碾压);全无钻 + 刷新未用 → 刷新找钻;刷新已用 → ``key_equips`` 契合(+10 命脉级)+ 通用装备价值(鞋>电池>花,``_EQUIP_VALUE`` 代码表)。新 ``SupplyOption``(idx/角色/装备/带钻)+ ``SupplyPick``。
- **为什么**:补给节点 naive「选中牌」(``handle_supply``)无视钻/key_equips;design 07/08。钻 = 拿到基本赢(用户),碾压;key_equips comp 相关(D-07)。先纯逻辑(可独立测),handler 接线(``read_supply_options`` OCR + 钻视觉判定)待阶段 5。
- **备选**:① 通用 equip_score(推翻:脱 comp 无意义,D-07);② 等阶段 5 OCR 一起(推翻:纯逻辑可独立测,符合先零件后整体)。
- **状态**:采用(纯逻辑 + 4 测试绿;handler 待 ``read_supply_options`` 阶段 5)。`· §07/08 补给`

## D-19 (2026-08-04) decide_encounter 纯逻辑骨架实现 · strategy/08
- **决策**:实现 `decide_encounter(options, state, target_comp, config, refresh_used) → EncounterPick`(纯函数,design 08 骨架)。规则:未成型→低难度;全分支词缀克 comp(``mechanics_fit``<0.4)+ 刷新未用→刷新换批;成型 + 词缀利 comp(debuff=buff)→高难度拿奖励;刷新已用→按最优选。新 ``EncounterOption``(idx/难度/词缀/奖励)+ ``EncounterPick``(idx/refresh/reason)数据类。
- **为什么**:遭遇节点 naive「选左」(``handle_encounter``)无法表达难度/词缀决策;design 08 标 high。词缀用 ``mechanics_fit``(debuff=buff,D-05)判克/利 comp。先做纯逻辑(阶段 2 骨架,可独立测),handler 接线(OCR ``read_encounter_options``)待阶段 5。
- **备选**:① 扩 ``decide_event`` 白名单(推翻:遭遇是难度档非白名单项,decide_event 表达不了);② 等阶段 5 OCR 一起做(推翻:纯逻辑可独立测 + 早发现 bug,符合"先零件后整体")。
- **状态**:采用(纯逻辑 + 4 测试绿;handler 接线待 ``read_encounter_options`` 阶段 5)。`· §08 遭遇`

## D-18 (2026-08-04) 配置层对齐:经济统一论落地后的取舍 · strategy/02 §A3 + README §A/D
- **决策**:① `economy_mode` **保留**(作 eval 权重微调:interest_first/rush_level 调利息/等级项),不按原 README §D 删除;② `aggression` **删除**(死字段,cw_decisions 不用);③ hp 阈值统一走 `config.hp_safe_threshold`(02 §A3)+ config 重写(forbid/build_around/handoff/difficulty/manage_meta_run)**缓做**(deferred)。
- **为什么**:① level_plan 是**硬 gate**(D-14,主导花费指令),economy_mode 只调 eval 权重(非花费决策)→ 二者**不冲突**(原 README "和 level_plan 打架"的删除理由在 hard-gate 落地后不成立);且 economy_mode 有测试锁定(test_economy_mode_effects),删 = 行为变更 + 破测试,无收益。② aggression 全代码不用,设计早判"虚"已删,代码残留。③ hp 统一 / config 重写是干净但触及 `_phase_weights` 签名 + 测试 + GUI 的重构,非"修漂移",单列任务。
- **备选**:按原 README §A/D 全删 economy_mode/aggression + 一次重写 config(推翻:① economy_mode 删除理由失效;② config 重写大,且 cw_comps 已 `getattr` 防御读取新字段,可增量加不必一次重写)。
- **状态**:采用(①② 已做;③ deferred,见 process_log/insights)。`· §02 §A3 / README §A/D`

## D-17 (2026-08-04) eval / comp_score 权重实跑校准 · strategy/02 §A3 + 03 comp_score
- **决策**:V4.4 research 先验权重经 2026-08-04 实跑(replay 32 局 + bot)校准:`INTEREST_WEIGHT 2→4`、`LEVEL_WEIGHT 3→6`、`SYNERGY_TIER_EXPONENT=1.5`(收敛:深化 delta>散新)、`OFF_TARGET_DISCOUNT 0.3→1.0`(revert,改用 commitment prefilter D-15)、`W_PROG 0.35→0.45` / `W_STR 0.10→0.05`(select_comp 偏好可成型而非纯高强度)、`TARGET_PROGRESS_WEIGHT=15`。
- **为什么**:实跑发现原值致 bot 不攒金(息 delta = 牌 synergy → 无差别买)、不升等级(level benefit < interest loss)、select_comp 锁高强度但不可成型 comp(列车同行 S 但商店没牌 → 不收敛)。提权后 bot 攒到 50 + 升级 + 选可成型 comp。
- **备选**:维持 research 先验占位值(推翻:实跑证明不收敛)。阶段 6 再用 replay 精调最敏感 3-5 维。
- **状态**:采用(实跑驱动,待阶段 6 replay 精调)。`· §02 §A3 / §03`

## D-16 (2026-08-04) shop_supply:select_comp 降权不可得 comp(task#25)· strategy/03
- **决策**:`select_comp` 对核心阵营在当前 shop/board **不可得**的 comp ×0.3 降权(新 helper `shop_supply`)。
- **为什么**:实跑发现 select_comp 锁高强度 comp(列车同行 S=1.0)但商店刷不出其牌 → board 散、永不成型 → plane1 重伤。降权使 select 偏好**可得** comp(万敌 燃血:1 > 列车同行 0 可得)。
- **备选**:① 纯按 comp_score 不考虑可得性(推翻:锁死不可成型 comp);② P1-2 `ENV_COMP_AFFINITY` 硬绑(更强形式,待实玩补全 T0 env 表)。
- **状态**:采用。`· §03 select_comp`

## D-15 (2026-08-04) commitment prefilter + OFF_TARGET_DISCOUNT revert(task#16)· strategy/02
- **决策**:target_comp 设定时,`_best_improving_action` 用 **prefilter** —— shop 有 target 卡(阵营∈target.factions / ∈core_chars)可买时,跳过纯 off-target 散牌(**只 gate 新 buys,不动已持有 board 的 eval**);`OFF_TARGET_DISCOUNT` revert 0.3→1.0(不打折 board synergy)。
- **为什么**:原 OFF_TARGET_DISCOUNT=0.3 打折 board synergy 致 bot 卖成型 off-target 深堆(churn)= regression。prefilter 只影响"买什么新牌"不影响"已堆的怎么评分"→ 聚焦深化 target 且不破坏现有 board。target_comp 参数保留(prefilter 复用,OFF_TARGET_DISCOUNT effect 暂关)。
- **备选**:① OFF_TARGET_DISCOUNT 打折 board(↺ 推翻,致 churn);② 无 commitment(纯 reactive,不聚焦)。
- **状态**:采用。`· §02 commitment`

## D-14 (2026-08-04) level_plan 从"导向"升级为"硬 gate"(task#18)· strategy/03 经济统一论
- **决策**:`plan()` 中 level_plan `action="level_up"` + 够钱 → **直接执行 LevelUp**(每轮 ≤1 级),不进贪心 eval 候选。语义从 D-08 的"导向(eval 权重)"升级为"**花费指令(directive)**"。comp 无 level_plan 时退回通用曲线 `_DEFAULT_LEVEL_GOAL`。
- **为什么**:replay 32 局「升 0 次」根因 —— 贪心 eval 对"花大金升级"的利息损失短视:LevelUp 候选 delta 永负(花 48 金 → 利息档 5→0 损 -20,level_val 仅 +6)→ 永不选中 → bot 卡 lv5-6 → 弱 comp → plane2 死。level_plan 说升 + afford → 信任计划而非短视 eval。tempo 破息在所不惜(升级 = 解锁高费刷新率 + 出战位,关键长期投资)。
- **备选**:① 仅提 LEVEL_WEIGHT 让 eval 自发选升级(部分采用 D-17 提 3→6,但单靠 eval 权重不够稳,hard gate 兜底);② 每 comp 手填 level_plan(保留:comp 有则优先,无则通用曲线兜底,保证所有 comp 有合理经济行为)。
- **状态**:采用。`· §03 经济统一论 / §02 plan`

## D-13 (2026-08-03) 击破 tiers V4.4 修正 2/4/6/9 · data/factions
- **决策**:`击破` FactionInfo tiers 用 `(2,4,6,9)`(原 `(2,4,6,8,10)`)。
- **为什么**:官方赛季文 76641553,V4.4 姬子成专家顾问,tiers 下调。
- **备选**:无(实据,非权衡)。
- **状态**:采用。

## D-12 (2026-08-03) 领域模型注册表 + 单一真相源派生 · 工程化
- **决策**:核心实体建正规 model 类 + 注册表(Character / Faction / Equipment / InvestmentEnv+Strategy);派生关系而非硬编码 —— `ENV_FACTION_MAP`←`INVESTMENT_ENVS.faction`、`DISTINCT_CARDS_PER_COST`←`chars_by_cost`、`Faction.members()`←`CHARACTERS` 反查。
- **为什么**:用户定调工程化质量,别写屎山;单一真相源改一处自动传导(否则多处硬编码易脱节)。
- **备选**:裸 dict + 散字符串(推翻:重复硬编码,改一处要同步多处)。
- **状态**:采用。

## D-11 (2026-08-03) 观测 trend 归一化而非完全划分 · strategy/10
- **决策**:`recent_hp_loss_trend` 用 `hp_delta / expected_drop[node_type]` 归一化,全部样本进**同一条** trend(不按 node_type 完全划分);boss 另留短 trend。
- **为什么**:review r5 的"完全划分"致 boss 观测永久 None + obs 随节点类型震荡;归一化既消除"打 boss 掉得多=我弱"偏差,又不丢样本。
- **备选**:按 node_type 完全划分(↺ 推翻 r5 过度修正;boss 稀疏 + 震荡)。
- **状态**:采用(r6 修 r5)。

## D-10 (2026-08-03) comp_viability 冷启动早返回纯先验 · strategy/10
- **决策**:obs=None(无观测)时直接返回纯先验,不 blend。
- **为什么**:`obs_weight × obs`(0×None)会 TypeError 崩溃;且无观测时纯先验就是最佳估计。
- **备选**:用先验填 None 再 blend(多余,先验已在公式里)。
- **状态**:采用(bug-driven,测试发现)。

## D-09 (2026-08-03) 列车同行(姬子·启行)= bot 默认首选 comp · data/comp_library
- **决策**:V4.4 列车同行 comp 作 bot 默认首选(strength S)。
- **为什么**:A850 挂机流攻略(76824096):"全程自动、不凹开局、适应任何负面环境" —— 完美适配 bot。V4.4 评级真神。
- **备选**:昼神阿雅(已降 B)/命运圣杯红A(S 但联动获取门槛)。
- **状态**:采用。

## D-08 (2026-08-03) 经济统一论:level_plan 驱动超额金 · strategy/03
- **决策**:D牌/买牌/买经验是"花钱的一环",非三件事。维持 ≥50 金(息引擎),**超额(>50 不生息,免费)该花**,花哪由 `target_comp.level_plan[当前等级]` 决定(level_up/roll/stable);tempo(连胜连败/HP危险/战力断档)例外破息。
- **为什么**:用户框架 —— 超额的钱白该花,花哪由成型路线导向。
- **备选**:D牌/买牌/买经验三件独立决策(推翻:割裂,忽略超额金的"免费"性)。
- **状态**:采用。**接法已落地**(`plan` level_plan 硬 gate[D-14] + `select_comp`/`maybe_pivot`[cw_comps] + shop.py 接线;2026-08-04)。

## D-07 (2026-08-03) 一切评分 comp 相关 · strategy/03/07/10
- **决策**:装备/巨星/词缀好坏都挂钩 `target_comp`(`equip_fit`/`mechanics_fit`/`select_megastar`),不设独立绝对评分项。
- **为什么**:反重力皮靴对昼神阿雅(需2靴)是命脉、对别 comp 不一定;知更鸟幸运一击只对暴击队值钱;正当防卫对阿雅是克、对万敌燃血是利。
- **备选**:通用 equip_score + 通用词缀表(推翻:脱离 comp 的绝对评分无意义)。
- **状态**:采用。

## D-06 (2026-08-03) V4.4 阿雅 strength S→B · data/comp_library
- **决策**:V4.4 昼神阿雅 comp strength B(V3.8 曾标 S "最轮椅")。
- **为什么**:米游社合集 76807134 V4.4 评级(试用+0命),阿雅降 B —— 需反重力皮靴×2+速度投资,试用/0命下难成型。
- **备选**:保留 S(与 V4.4 实测 meta 矛盾)。
- **状态**:采用。↺ 推翻 V3.8 "最轮椅 S" 先验。

## D-05 (2026-08-03) debuff 可能是 buff(mechanics_fit 双向)· strategy/10
- **决策**:敌人词缀对 comp 是 counter 还是 synergy,**双向判**(同一词缀对不同 comp 方向相反)。`comp.mechanic_attributes` + 全局 `MECHANIC_COUNTERS`/`MECHANIC_SYNERGIES`。
- **为什么**:正当防卫(反伤)对高频队是克、对燃血队(万敌)是利(反伤让燃血掉血→角斗场记录→伤害更高)。但**永久创伤**(掉血减上限)**克**燃血 —— 反例,故燃血非"所有掉血都利"。
- **备选**:通用高危词缀表(推翻:同词缀不同 comp 方向相反,通用表错)。
- **状态**:采用。

## D-04 (2026-08-03) 持久化/跨局状态默认不碰 · strategy/09
- **决策**:bot 默认**不动**玩家跨局继承(优势布局/钻钞);`manage_meta_run=false`。仅**局内**状态(买/deploy/升/D牌)默认自动。
- **为什么**:防打乱玩家长期投入(优势布局是玩家自己攒的 buff);持久化破坏性操作 opt-in。
- **备选**:默认自动激活最优布局(推翻:风险大,可能毁玩家投入)。
- **状态**:采用。

## D-03 (2026-08-03) 不凹开局重开 · strategy/09
- **决策**:策略**不依赖重开**找好开局;够好就该能"理智"克服任何开局。
- **为什么**:重开是玩家行为不是策略;策略鲁棒性应内含,不该靠重开掩盖。
- **备选**:opening reroll(推翻)。
- **状态**:采用。仅 `handoff=true + 好开局`用例保留"刷好开局交手玩家"。

## D-02 (2026-08-03) 邪道非必需(通关=成型度+装备)· strategy/02/03
- **决策**:不把"邪道装备/特殊 win-con"(物质分解液/反甲/仙舟神君邪道)当 comp 强度关键项;通关能力 = f(成型度 + 装备质量 + 阵型),差别在**成型难度**。
- **为什么**:用户实战 —— 好好构筑阵容+找装备,很多阵容都能通 A8;被攻略带偏("A8 80亿血必须靠邪道")。
- **备选**:标"邪道 A8 专项 S"(↺ 推翻;与实战矛盾)。删 `a8_wincon_holdings`。
- **状态**:采用。

## D-01 (2026-08-03) 砍精确战斗模拟器 + ML,改观测驱动 · strategy/01/10
- **决策**:**不建**战斗模拟器(打前预测赢率/掉血),**不建** ML 训练管线;改用 OCR **观测结果**(每回合掉血/胜负/boss血条)当反馈信号。
- **为什么**:星铁战斗太复杂(回合序/弱点/击破/能量/战技点)OCR 反推不出可信模型;且版本迭代改数值,预测模型会废、维护不起。结果信号扎根在结果上,版本鲁棒。用户定调"像人一样玩"(人看掉血,不算赢率)。
- **备选**:① 精确 sim(推翻:维护成本极高 + 版本废);② ML 训练(推翻:训练价值版本短命,V4.4 训的 V4.5 废);③ 粗可行性启发式(**保留**为 comp_viability 先验,非预测)。
- **状态**:采用。ML 只采集(debug telemetry 序列化决策迹),**不主依赖**。
