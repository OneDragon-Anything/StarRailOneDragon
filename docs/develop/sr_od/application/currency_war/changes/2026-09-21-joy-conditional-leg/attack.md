# joy-conditional-leg 设计·对抗攻击报告(核一无前提 / 核二规范 / 核三治本)

> 攻击对象:`design.md`(草案态,单文档方案)+ `landing.md` §3.1/末阶段 + `README.md`。
> 规范依据 = `docs/develop/harness/iteration-design.md` §1-§5/§7。纸面对实码,证据全部为
> 仓库现状实读。共 11 条发现(1 阻断 / 6 应修 / 4 建议)。

---

## 1. 符号/锚全量核验结果(先行声明,不计发现)

以下设计引用的锚逐个实读相符,不作为攻击点:

- `cw_invest_data.py:451` 欢愉契约 id=1201 效果原文逐字相符(「获得【银狼LV.999】,她每次触发独立羁绊【头号玩家】选项时,获得【火花】或【开拓者·欢愉】。」)✓
- `cw_investments.py:1575-1581` 欢愉契约 `GiftGrant(chars_immediate=('银狼LV.999',), chars_conditional=(('火花',…),('开拓者·欢愉',…)))` ✓
- `cw_chars.py:150-151` 开拓者·欢愉/火花 4 费在册 ✓;`cw_factions.py:105` 头号玩家 = 银狼LV.999 专属 independent (1,) ✓;原文存档 `docs/game/currency_war/data/characters/银狼LV.999.md` 在库 ✓
- `kernel/cw_action_report/pick_planner.py:58` `report_action_pick_planner_param` 两相形态、落地相门 `EVIDENCE_OVERLAY_CLOSED`(:55/:73)、三腿分派 + 终态兜底(:79-88)与设计引用一致 ✓
- `normalize_invest_name`(cw_investments.py:691-701)仅做分隔符形变归一,'欢愉契约' 无形变字符恒等返回;`active_env` 写入链已归一(pick_invest_env.py:26-50 `_canon_invest_name` → `gain_invest_env` 写 canon 名)——§2.2-4 在册判定 `normalize_invest_name(gs.active_env.value or '') == '欢愉契约'` 行为成立 ✓;开局种子 `''`(cw_game_state.py:1771)≠ 欢愉契约 → 不授予 ✓
- import 方向:pick_planner → cw_gain_chain 无循环(cw_gain_chain.py import 面实读,不反向依赖 cw_action_report)✓;`gain_character(gs, name, star, *, rand, sig, evidence, producer)` 签名与 §2.2-1 调用形态(evidence=`joy_conditional:<单位名>`/producer=`_PLANNER_PRODUCER`)逐参对得上 ✓
- sim 侧:`grep report_action_pick_planner_param|classify_planner_leg`(sim/ 零命中)——「sim 接线不在本批」申报成立;`rng` 缺省 None 下实机两调用点(cw_screen_yinlang.py:214 落地相 / cw_overlay_pick_action.py:418 发射相)均零改动 ✓
- `JOY_PROVISIONAL_KIND` src 内引用 = cw_gain_chain.py 4 处(:90 常量/:616/:640 docstring/:651-653 发射)全在删除面内;test_cw_dead_pair_exit.py 的 `provisional` 是无关模块(sim 校准注入),不构成退役面 ✓
- weaken 退役 src 面 grep:`cw_events.py`(:905-906 词表注释/:908 常量/:1010 分类 docstring/:1030-1031 分支)、`pick_planner.py`(:19-20 模块 docstring/:67 函数 docstring/:88 兜底 reason)、`cw_overlay_pick_action.py:124`(env 注释);`decide_planner` 弱化档打分(:881-884)+ docstring(:844-857)。sim 零消费、cw_screen_yinlang.py 零字面量(不在文件面合理)✓
- 测试断言面:test_cw_yinlang_phase32.py:160(`classify_planner_leg('使后续节点【弱化】')==('weaken','')`)、:273-286(`leg_type='weaken'` 落地相零留证)、:456-475(joy provisional 留证行)——design §2.6/landing 3.1 改写对象在此存在(范围申报问题见发现 5)✓
- weaken 派发分支删除后行为推演:classify 删关键词降级分支 → 含弱化词未知名落 `PLANNER_LEG_UNKNOWN`(:1032 既有 return 兜住);破解芯片碰撞治理(锚先行 :1020-1022)不受影响;report 终态兜底(:88)保留 + reason 改名可落 ✓;decide_planner 删弱化档后未知名卡文按装备档 `_equip_value` 回落(注册表 miss = 0 分,与「未识别 0 分」等价)✓
- 触发前置时序(欢愉契约送 1★ 银狼 → 单级合成 2★ → 弹窗才出现):与 ENV_GIFTS 数据 + gain_character 合成建模自洽;接管局 active_env 无写端、rider 判 '' 不授予——§2.4 边界申报成立 ✓
- 撤闩判据合规:§2.6 已用「对欢愉契约落地调用断言零 provisional 行」等价形式,不触 AGENTS.md 10.4-4 源码扫描禁令 ✓;README 模板合规(无详设删行、attack.md 链接、进度态)✓

---

## 2. 发现清单

### 发现 1 [阻断] | design §2.5-1 + §2.6 双臂判据(+§2.2-3) | rand 通道申报与实码矛盾:rand=True 锚定后仍走 write_logic_rand,「锚定后写 logic 通道走失配网」不成立,§2.6 第二臂判据不可实现

- **问题**:§2.5-1 申报「锚定后写 logic 通道——若模型与真值不符将走失配网(真信号)」;§2.6 双臂判据「`gs.prep_anchored = True` 直赋后 → source=logic」。实码择道口是 `if rand or not prep_anchored_of(gs): return gs.write_logic_rand`(cw_game_state.py:1803)——**rand 形参优先于锚定状态,rand=True 无条件走 logic_rand,与闩无关**。gain_character 链内全部写经 `_select_write(gs, rand)` 继承同一通道,且 test_cw_gain_chain.py:257 已有现成测试锁死该语义(「臂 3:rand=True 恒 logic_rand(与闩无关)」)。照 §2.6 判据写测试必红;照 §2.5-1 理解行为 = 对可验证性的错误申报。实质后果:条件腿授予**锚定后也不进失配三分流**,模型错误(选错候选/星级先验错)不会被失配网暴露,只有 logic_rand_outcome 行 + 首观察静默覆盖——这恰是本批「定谳」质量主张的核心面,申报方向反了。§2.2-3「未锚定期经 anchor_aware_write 亦落 rand,通道一致」回避了锚定后的通道,三处口径互不自洽。
- **证据**:`cw_game_state.py:1790-1805`(anchor_aware_write,`rand or` 短路)、`cw_gain_chain.py:240-251`(_select_write 委托)/:388/:332(链内写全经本口)、`sr-od-test/.../test_cw_gain_chain.py:244-261`(双臂+臂3 既有锁)、正本 gain-chain.md §5「锚定后按 rand 形参(失配网生效)」。
- **处置方向**:§2.5-1/§2.6/§2.2-3 按实码改写——rand=True 全通道 logic_rand(效果体含采样 → 子链 rand=True 纪律的正参推论,引用 gain-chain.md §5),锚定后亦然;可验证性如实申报为「logic_rand_outcome 行 + 观察覆盖,无失配网」;双臂测试第二臂期望改 source=logic_rand(或删臂,改为「闩置位不改变 rand 写通道」断言)。若作者本意是锚定后要确定面,须显式立新裁定并与采样纪律的冲突一起申报——不能维持现文。

### 发现 2 [应修] | design §2.2-1/§2.3 | rider 置于分派前 + 「失败不阻塞各腿」+「零吞错」三句并置,catch 形态未定义 = 实现者再设计点

- **问题**:落地相是顺序函数体(pick_planner.py:73-88);rider 在腿型分派**之前**调用 gain_character,若异常上抛则 equip/upgrade 腿(选项应用)永不执行——授予失败阻塞选项应用,与「失败不阻塞各腿」直接冲突。要兑现「不阻塞」只能在 rider 调用点 try/except,但设计未写 catch 后的行为(留证 kind?log 行?静默?),且捕获吞掉链原语异常与在册「链原语零吞错(真异常该响)」纪律(gain-chain.md §6-1、cw_gain_chain.py:21)存在张力,该 best-effort 例外未申报。三句并置下实现者必自行拍板一个未过审的语义。
- **证据**:pick_planner.py:73-88(落地相顺序结构)、design §2.3 原文、cw_gain_chain.py:21-22(零吞错纪律)/:494-496(gain_character 不包装)、gain-chain.md §6。
- **处置方向**:写死二选一——(a) rider 调用点 try/except + 缺陷留证(如 `kind='joy_conditional_grant_failed'`),显式声明为链零吞错纪律的调用点级 best-effort 例外并给理由(授予与选项应用独立因果);(b) 删除「失败不阻塞」主张,如实申报授予失败会阻断选项应用及其后果。按 (a) 与设计意图一致。

### 发现 3 [应修] | design §2.3「每次弹窗恰一次…零新闩」 | 「恰一次」的保证者与失效通道未申报:act 节点异常重试可二次到达落地相,rider 重复授予走 rand 通道静默

- **问题**:「落地相门即既有家族的每次弹窗恰一次语义,rider 直接受益,零新闩」——落地相门本身无幂等闸(report 函数零判重),「恰一次」实为保证者 =「画面 op 生命周期内正常单次到达重入裁决出口」。失效通道在册:落地相调用前 `_confirm_pending` 已置 False、`_pending_leg`/`_pick_param` 已清空(cw_screen_yinlang.py:205-211),若落地相内部异常上抛(rider 自身/upgrade 腿 merge 不变量 AssertionError/写腿异常,均为零吞错上抛面),act 节点(`node_max_retry_times=5`,:195)重试 → 重走选卡+确认链(对着已关闭的 overlay;PlannerPickOp :404 重新置 `_confirm_pending=True`、cw_screen_yinlang.py:255-256 重建 `_pending_leg`)→ 下一轮重入裁决「入口词不在」→ **落地相第二次执行 → rider 第二次授予**。既有腿同暴露,但锚定后走 write_logic 有失配网可见;rider 走 rand 通道(发现 1)重复授予零告警,只在观察覆盖时静默自愈,journal 与合成已被污染。§2.4 已知边界未列,§2.3 主张未分析该通道。
- **证据**:cw_screen_yinlang.py:195(node_max_retry_times=5)/:204-222(重入裁决出口与载荷消费序)/:255-256(载荷重建)、cw_overlay_pick_action.py:404(`_confirm_pending=True` 重置)、pick_planner.py:118/:216/:231(merge 断言与写腿上抛面)。
- **处置方向**:①最小 = 如实申报边界(「恰一次」依赖 op 正常流;落地相内部异常 + 节点重试路径可二次落地,rider 重复授予走 logic_rand 静默自愈,判读面以 evidence 前缀计数为候校准);或 ②显式裁决幂等(落地相消费一次后实例级拒再入,需新闩 = 推翻「零新闩」主张,须给权衡)。

### 发现 4 [应修] | landing 正本更新清单 | 漏两份 weaken 记账语义正本:`screens/planner.md` 与 `game_state/logic-updates/pick-planner.md`

- **问题**:全仓 grep weaken,正本(非 changes)命中 `docs/develop/sr_od/application/currency_war/screens/planner.md:55`(「…/ unknown·weaken 零记账」)与 `game_state/logic-updates/pick-planner.md:17`(「**weaken**:零记账」)/:41(「…unknown/weaken 零记账」)。weaken 退役后这两份正本失真;landing 正本更新清单只列 gain-chain.md / strategy-env-impacts.md / research,未列它们 → 末阶段按清单执行 = 失真正本残留,违反双层文档流「实现后更新正本」收尾义务(清单是账本唯一源,漏列即永久漏修)。
- **证据**:上行号 grep 实读;landing「正本更新清单」节(3 行)。
- **处置方向**:清单补两行——`screens/planner.md`:落地相记账段 weaken 字样 ← 3.1;`game_state/logic-updates/pick-planner.md`:§分派表与记账段 weaken 条目 ← 3.1。

### 发现 5 [应修] | design §2.6「既有测试随迁」+ landing 3.1 文件面 | test_cw_gain_chain.py 无 joy 临时闩断言,随迁改写对象一半不存在

- **问题**:「`test_cw_gain_chain`/`test_cw_yinlang_phase32` 中 joy 临时闩断言改写」——实读 test_cw_gain_chain.py 全文,`provisional|JOY|欢愉|on_env_gained` 零命中(该文件锁的是链原语/双臂通道/回调枚举,不含临时闩);joy 临时闩断言唯一面 = test_cw_yinlang_phase32.py:456-475(`assert 'joy_contract_provisional' in rows_sink.kinds()`)+ :23-24 文件头注释。申报失实会误导实现者去找不存在的断言(停手令浪费一轮)。
- **证据**:`grep provisional|JOY|翻来源|on_env_gained|欢愉` 于 test_cw_gain_chain.py 零命中;test_cw_yinlang_phase32.py:23-24/:456-475。
- **处置方向**:申报面改为「test_cw_yinlang_phase32 joy 临时闩断言改写;新增 rider 测试(可落 test_cw_gain_chain 或新文件,随批申报)」;landing 文件面同步措辞。

### 发现 6 [应修] | design §2.2-7 | weaken 退役注释面清点不全:pick_planner.py 两处 docstring 与 decide_planner docstring 定序自述不在申报内

- **问题**:§2.2-7「三处一并剔除 + ④注释同步」的「三处」计数与实码不对齐——pick_planner.py 的 weaken 字样除派发分支(:88)外还有模块 docstring(:19-20「**weaken**:零记账(全场弱化为节点态语义…)」)与函数 docstring(:67「unknown·weaken 零记账」);`decide_planner` docstring(:844-857「三层定序结构 = 升费档 > 弱化档 > 装备档」及弱化档整段)是两档制改造的必改面,设计只写了「打分两档制」未点名 docstring。退役不彻底 = grep weaken 残留,恰是裁定③「没找到证据的就是不存在」的显式反信号。
- **证据**:pick_planner.py:19-20/:67/:88;cw_events.py:844-857(decide_planner docstring)/:881-884(打分);design §2.2-7。
- **处置方向**:§2.2-7③ 扩为「pick_planner.py 派发分支 + 两处 docstring 同步」;②补「decide_planner docstring 定序自述同步两档制」;landing 3.1 范围句同步(cw_events.py/pick_planner.py 已在文件面,零文件面变更)。

### 发现 7 [应修] | design §1「明确不解决」(核三) | 条件腿族共 7 条在册,design 未申报族面边界与逐件修架构问题

- **问题**:ENV_GIFTS 中 `chars_conditional` 非空条目共 7 个环境(量子同频契约/公司契约/持续伤害契约/战技点契约/星核猎手契约/欢愉契约/命运圣杯契约/特邀专家:银狼,含 8+ 条件腿单位),全部与欢愉契约同族(「条件腿声明性数据无引擎」)。本批只建模欢愉契约——其独特性 = 唯一有已落地的触发观测面(planner 上报),其余条件腿触发事件(升星时/累计利息/晶矿计数/一役后/圣杯试炼)尚无观测面,范围控制本身合理;但 §1「明确不解决」未列族面,「条件腿建模」的迭代名与根因归层(「条件腿无模型」)读起来覆盖全族。核三「同族问题第二次出现 = 升架构审视」的条件已半触发(第 2 件起),应显式回答:族内其余条目是「逐件建模」还是「统一条件腿建模框架」,排期归宿在哪。
- **证据**:cw_investments.py:1548-1595(ENV_GIFTS 全表,chars_conditional 7 条目);design §1 现状症状 1 /「明确不解决」清单(无族面条目)。
- **处置方向**:§1「明确不解决」补一条「其余条件腿条目(7-2=5 个环境)不在本批——触发观测面均未建模,逐件 vs 统一框架候族批裁决」;或在本批 §2.7 给族批指针。

### 发现 8 [建议] | design §1/§2.2-6 | 引用锚失真两处:「银狼批 design §2.7② 立项」错批;「GainOutcome 的 provisional_mark effects 项」措辞错位

- **问题**:①临时闩立项出处 = changes/2026-09-18-yinlang-exclusive-loop/design.md(:143「欢愉契约(1201) 条件腿——采证期运行协议……kind=joy_contract_provisional」);design 所指「银狼批」(= 交付 report_action_pick_planner_param 的 2026-09-20-yinlang-starup-accounting,§2.7 关系节自证)的 design.md 全文零命中 欢愉/provisional/条件腿——「银狼批 design §2.7② 立项」对不上任何实存内容。②「GainOutcome 的 provisional_mark effects 项」——provisional_mark 不是 GainOutcome 字段,是 on_env_gained 返回 effects 元组里的字符串项(cw_gain_chain.py:649),措辞错位(实现者能猜,但依据标注应准确)。
- **证据**:2026-09-20-yinlang-starup-accounting/design.md grep 零命中;2026-09-18-yinlang-exclusive-loop/design.md:143;cw_gain_chain.py:649。
- **处置方向**:①立项指针改指 2026-09-18 批 design「欢愉契约条件腿——采证期运行协议」节(迁移史 = 2026-09-20 批 landing「provisional 闩随 on_env_gained 迁 kernel」);②措辞改「on_env_gained 返回值中的 provisional_mark 效果名项」。

### 发现 9 [建议] | landing §3.1 设计依据行 | 判据/依赖实际引用 §2.5/§2.7,设计依据行未列,范围声明与引用面不一致

- **问题**:设计依据 =「design.md §2.1-§2.4/§2.6/§2.2-7」;完成判据引「行为对照 design §2.2-**§2.5**」、依赖行引「design **§2.7**」。§2.5(行为变化申报)是验收对照输入、§2.7(tool-gain-report 在飞核查)是开工前置,均应在设计依据行内。
- **证据**:landing §3.1 三行对照。
- **处置方向**:设计依据行补「§2.5/§2.7」。

### 发现 10 [建议] | design §2.6「全腿型计数」 | 判据表述混乱,实现者需猜测试入口集

- **问题**:「落地相四类入口(equip/upgrade/unknown 及已退役 weaken 的历史调用形态)之外,rider 触发以『落地相』为准——equip/upgrade/unknown 三腿均触发 rider…」——「四类入口…之外」与「三腿均触发」的集合关系、「已退役 weaken 的历史调用形态」指什么,均无法从字面复原;实现者要自行裁决测试入口集。
- **证据**:design §2.6 原文;实码腿域 = {equip, upgrade, unknown} ∪ 发射相(退役后)。
- **处置方向**:改封闭清单——「落地相入口 {equip, upgrade, unknown} 各断言 rider 恰一次授予;发射相断言零授予;(可选)leg_type='' 直调落地相断言 rider 仍触发」。

### 发现 11 [建议] | design §1 | 错别字「专属独立羁姻」(羁绊)

- **证据**:design §1「头号玩家 = 银狼LV.999 专属独立羁姻」;注册表规范名 = 羁绊(cw_factions.py:105)。
- **处置方向**:改「羁绊」。

---

## 3. 已查证为协调的点(攻击过、不成立,留档防复议)

- **在册判定的一致性**:active_env 写入链全归一(pick_invest_env.py `_canon_invest_name` 全角冒号 + normalize → gain_invest_env 直写 canon);rider 读口再 normalize 幂等;'欢愉契约' 无 bullet 形变字符 → 判定成立。OCR 将环境名误读到分隔符形变之外(漏授予)属既有识别面,非本批新增。
- **import 无环**:pick_planner 新增 import cw_gain_chain,cw_gain_chain 的 import 面(cw_effect_inventory/cw_exec_state/cw_gain_effects/cw_game_state/cw_investments)不回指 cw_action_report。
- **rng 透传面**:实机两调用点均不传(落地相 cw_screen_yinlang.py:214、发射相 cw_overlay_pick_action.py:418),缺省 None = 实机猜测语义;sim 零消费(grep 证),「sim 接线不在本批」成立;random.choice 形态与 roll_hacker_mod 先例(on_strategy_gained rng 注入)同构。
- **rider 与 upgrade 腿 applied=False 分支共存**:tier_ceiling/source_missing 时弹窗确实出现过,rider 已授予语义正确(触发 = 弹窗,非选项成功)。
- **发射相零触发**:evidence 缺省分支先于 rider 落点 return,意图遥测零写不变。
- **撤闩后 on_env_gained 欢愉契约行为**:仅 chars_immediate 腿(银狼LV.999 经 gain_character 入链),advisor 分道不涉及(advisor=False);ENV_GIFTS 数据不动,chars_conditional 字段保留为声明性档案(消费面 = 本模型 + 判读)。
- **weaken 派发分支删除后的终态兜底**:unknown 分支后的裸 return 保留,reason 更名 `unrouted_leg_zero_write` 可落;leg_type 载荷来源(classify)已无 weaken 产出点,兜底仅防非法值。
- **decide_planner 弱化档删除的决策面影响**:含弱化词未知名回落装备档(_equip_value miss = 0 分),与「未识别 0 分 idx 兜底」等价;§2.5-5「决策影响极小」申报成立。
- **测试随迁的可判定性**:test_cw_yinlang_phase32:160/:283-286/:475 三处断言与 design §2.6 退役锁/撤闩判据一一对应,改写方向可执行(范围申报问题归发现 5)。
- **接管局/3★接管/授予分布/星级先验**:§2.4 四条边界申报与实码及原文锚相符,观察覆盖兜底路径成立。
- **正本 strategy-env-impacts.md 存在**(landing 清单引用真实);gain-chain.md §3 条件腿条目(:122-124)在末阶段更新面内。

## 4. 试读结论(逐阶段「凭这份能开工吗」)

- **3.1 rider + 撤闩 + weaken 退役**:**不可开工**——发现 1(rand 通道申报/判据反实码,测试照写必红)、发现 2(catch 形态未定义,实现者必拍板);发现 3/5/6 增加返工面。
- **末阶段正本更新**:清单缺两份 weaken 正本(发现 4),清零判据按现清单执行即残留失真;补列后随 3.1 定稿自洽。

## 5. 总结论

**需修订后复审。** 计数:阻断 1(发现 1 rand 通道申报与判据反实码——`anchor_aware_write` 的 `rand or` 短路使 rand=True 锚定后仍 logic_rand,§2.5-1 失配网主张与 §2.6 双臂第二臂均不可实现)、应修 6(发现 2-7)、建议 4(发现 8-11)。
核心修正责任:①rand 通道三处口径按实码统一重写(发现 1);②rider 失败语义与「恰一次」边界两项触发正确性申报写死(发现 2/3);③退役面/正本面/测试面三张清点表补齐(发现 4/5/6)。核三:语义层归层成立(触发→授予因果缺失是根,临时闩是测量代偿),本批修根非症状;但条件腿族 7 条在册的族面边界须申报(发现 7),防「逐件修」无声展开。其余各条随修订顺手收口。

---

## r1 处置记录(修订 = design/landing 全量改写,本节由编排者记)

| 发现 | 处置 | 落点 |
|---|---|---|
| 1 rand 通道反实码 | 采纳按实码统一:rand=True **全通道 logic_rand**(rand 形参优先于锚定状态,采样纪律正参推论);可验证性如实改写 = `logic_rand_outcome` 成对校准行 + 观察覆盖,**无失配网**;§2.6 双臂第二臂改「闩置位不改变通道(恒 logic_rand)+ 覆盖时 outcome 行断言」。不立「锚定后确定面」新裁——采样面本义 | design §2.2-3/§2.5-1/§2.6 |
| 2 rider 失败语义 | 采纳 (a):调用点级 best-effort(try/except + log + 缺陷行 `joy_conditional_grant_failed`),显式申报为链零吞错的调用点级显式例外(登记腿同族先例);链内部零吞错不变 | design §2.2-1/§2.3/§2.6 |
| 3 恰一次失效通道 | 采纳 ①:§2.3 改写保证者与失效通道(异常重试 → 载荷重建 → 二次落地 → 重复授予 rand 静默自愈),§2.4 补边界;不做实例级拒再入(新闩成本 > 异常路径收益),判读以 evidence 前缀计数校准 | design §2.3/§2.4 |
| 4 正本清单漏两份 | 采纳:补 `screens/planner.md`/`game_state/logic-updates/pick-planner.md` 两行 | landing 正本清单 |
| 5 测试随迁申报失实 | 采纳:joy 临时闩断言唯一面 = test_cw_yinlang_phase32(:456-475/:23-24);rider 新测试落点随批申报 | design §2.6、landing 3.1 文件面 |
| 6 weaken 注释面清点不全 | 采纳:§2.2-7 扩为全清单(pick_planner 两 docstring + decide_planner docstring 定序自述 + 终态 reason 更名),判据 = 全仓 grep weaken 残留清零 | design §2.2-7 |
| 7 条件腿族面边界 | 采纳:§1 明确不解决补族面申报(7 环境在册,本批仅欢愉契约 = 唯一已落地观测面;逐件 vs 统一框架候族批裁决) | design §1 |
| 8 立项锚错批 + 措辞 | 采纳:立项指针改 2026-09-18 批「采证期运行协议」节;provisional_mark 措辞改「返回值中的效果名项」 | design §1/§2.2-6 |
| 9 设计依据行缺 §2.5/§2.7 | 采纳 | landing 3.1 |
| 10 全腿型计数表述混乱 | 采纳:封闭清单式(equip/upgrade/unknown 各恰一次 + 发射相零 + leg_type='' 兜底形态) | design §2.6 |
| 11 「羁姻」错别字 | 采纳:改「羁绊」 | design §1 |

---

## r2 复攻记录(修订版 = 提交 51518b31e)

> 复攻范围:①11 条处置逐条对照修订版核真伪;②修订新增面无前提再攻(best-effort
> 例外边界/失效通道充分性/族面表述/rand 全通道下校准面自洽性);③试读重跑;
> ④全量同步复查。证据为当前仓库实读。共 5 条新发现(1 阻断 / 1 应修 / 3 建议)。

### 1. r1 处置逐条核验结果

| 发现 | 处置核验 |
|---|---|
| 1 rand 通道反实码 | ✓ design 侧落对:§2.2-3(「rand 形参优先于锚定状态」「全通道 logic_rand,锚定前后同通道」引实码短路形态)/§2.5-1(无失配网辖,采样面本义)/§2.6(「置闩后同路径 source 仍 = logic_rand,与既有臂 3 锁同语义」+ 校准面 = outcome 行断言)三处口径统一且与 `anchor_aware_write` 实码(cw_game_state.py:1803)及 test_cw_gain_chain.py:244-261 既有锁一致。**✗ landing 面漏改,见 r2 发现 1** |
| 2 rider 失败语义 | ✓ 落对。§2.2-1 显式裁定段(try/except + log + `joy_conditional_grant_failed` 缺陷行 + 照常分派;零吞错的调用点级例外显式申报 + 正本 §6 申报承诺)/§2.3 末条/§2.6 失败语义测试(gain_character 注入异常 → 分派照常 + 缺陷行)三处齐。实现细节瑕疵见 r2 发现 5;承诺落点缺清单行见 r2 发现 2 |
| 3 恰一次失效通道 | ✓ 落对。§2.3「正常保证者」与「失效通道如实申报」两段(异常重试 → 载荷重建 → 二次落地 → 重复授予 rand 静默自愈;既有腿同暴露;不做实例级拒再入 + 理由)+ §2.4 边界条。申报充分性再攻:修订采纳 (a) best-effort 后,rider 自身异常已不进重试通道,失效通道触发源收窄为腿型分派内部异常(upgrade 三态守卫外的写腿异常/merge 断言)——修订版「(升费腿有三态守卫、装备腿无)」对照仍成立,二次执行时 rider 随落地相重跑的重复授予面已覆盖。无需追加 |
| 4 正本清单漏两份 | ✓ 落对(screens/planner.md + logic-updates/pick-planner.md 已列,落点段与 grep 实读一致) |
| 5 测试随迁申报失实 | ✓ 落对(唯一面 = test_cw_yinlang_phase32 :456-475/:23-24;rider 新测试落点随批申报,landing 文件面同步) |
| 6 weaken 注释面清点不全 | ✓ 落对(§2.2-7② docstring 定序自述、③ 两处 docstring 补齐)。**新增判据字面缺陷,见 r2 发现 3** |
| 7 族面边界 | ✓ 落对(§1 补族面申报段:观测面理由/候族批裁决/禁逐件无声展开)。**计数继承 r1 笔误,见 r2 发现 4** |
| 8 立项锚 + 措辞 | ✓ 落对(§1 立项出处 = 2026-09-18 批「采证期运行协议」节 + 迁移史指针;§2.2-6「返回值中的 provisional_mark 效果名项」) |
| 9 设计依据行 | ✓ 落对(landing「design.md §2.1-§2.7(含 §2.5 行为变化申报、§2.7 相邻批在飞核查)」) |
| 10 计数判据表述 | ✓ 落对(§2.6 封闭清单:三腿各恰一次 + 发射相零 + `leg_type=''` 直调兜底形态——直调形态语义核过:分派前 rider 已执行,兜底 return 不回退授予 ✓) |
| 11 错别字 | ✓ 落对(§1「独立羁绊」) |

### 2. r2 新发现

#### r2 发现 1 [阻断] | landing §3.1 完成判据第一条 | 残留 r1 旧口径「双臂通道(未闩=rand/置闩=logic)」,与修订版 design §2.6 正面冲突——发现 1 处置在 landing 面不完整

- **发现**:修订版 design §2.6 已按实码改写(「`gs.prep_anchored = True` 直赋后同路径 **source 仍 = logic_rand**」),但 landing §3.1 完成判据第一条仍写「双臂通道(未闩=rand/**置闩=logic**)、在册判定、rng 注入确定性、三腿计数、发射相零触发、时序锁」。阶段小节 = 账本立任务唯一源(iteration-design.md §3.1),照此行立任务 = 验收判据以已被推翻的通道语义为准,worker 按 design 实现则 landing 判据必红、按 landing 判据实现则复活 r1 阻断缺陷——恰是 r1 发现 1 的核心判据面在另一文档残留,全量同步复查义务(硬规则 4)违例。
- **证据**:landing.md:28;design.md §2.6 通道语义条(:178-181);r1 发现 1。
- **处置方向**:该行改「通道语义(rand=True 恒 logic_rand,置闩不改变通道;覆盖校准面 = logic_rand_outcome 行)」,与 design §2.6 逐字对齐;顺手核「验收凭据形式」行「rider 双臂」措辞(双臂仍在,期望同值,可保留)。

#### r2 发现 2 [应修] | landing 正本更新清单 | design §2.2-1 承诺「随正本更新在 gain-chain.md §6 申报 best-effort 例外」,清单 gain-chain.md 行只列 §3 条目——承诺落点无清单行

- **发现**:§2.2-1 明文「随正本更新在 gain-chain.md §6 申报」(调用点级 best-effort 例外),landing 正本更新清单 gain-chain.md 行仅「§3 欢愉契约条件腿条目(临时闩标记面 → planner 触发回调模型,临时闩退役)」。清单 = 末阶段判据单一源、清零 = 收尾完成——§6 失败安全四则的 best-effort 边界扩围不在清单内,末阶段按清单执行即漏修,正本纪律(链零吞错)与新实现(调用点级例外)失配残留。与 r1 发现 4 同型(清单缺口),系发现 2 处置新增的申报面未同步到清单。
- **证据**:design.md §2.2-1 末句;landing.md 正本更新清单 gain-chain.md 行;gain-chain.md §6(现役 best-effort 边界句 :178-180)。
- **处置方向**:清单 gain-chain.md 行扩为「§3 条件腿条目 + §6 失败安全节(调用点级 best-effort 例外申报) ← 3.1」。

#### r2 发现 3 [建议] | design §2.2-7 | 「退役判据 = 全仓 grep weaken 残留清零」字面不可满足,需 src 限定

- **发现**:全仓含 changes/ 历史迭代文档(2026-09-18/2026-09-20 批 design/landing 大量 weaken 字样,寿命 = 迭代、生命周期内不删)与本报告(attack.md 通篇 weaken)——按字面「全仓清零」永不满足。同文档 §2.6 撤闩判据的同类判据写的是「全仓**(src)** 零引用」带限定;两处对照,此处置漏 (src) 限定,验收自查时会产生字面歧义。
- **证据**:design.md §2.2-7 末句 vs §2.6 撤闩条;grep weaken 全仓命中含 changes/×10+ 文件、attack.md 本文件。
- **处置方向**:改「退役判据 = src 全仓 grep weaken 残留清零(sim 零消费已核)」,与 §2.6 撤闩判据限定口径一致。

#### r2 发现 4 [建议] | design §1 族面申报(含 r1 自纠) | chars_conditional 非空环境实为 8 个非 7 个,r1 发现 7 计数笔误被修订版继承

- **发现**:ENV_GIFTS 逐条实数:量子同频契约/公司契约/持续伤害契约/战技点契约/星核猎手契约/欢愉契约/命运圣杯契约/特邀专家:银狼 = **8 个环境**(r1 发现 7 自身括号已列 8 项却写「7 个」,系攻击方计数笔误;修订版「共 7 个环境(…7 项…,含特邀专家:银狼)」同样数字与列举自相矛盾)。事实修正不影响处置方向(族面申报本体已落)。
- **证据**:cw_investments.py:1548-1595 逐条(chars_conditional 非空共 8 条目);design §1 族面段。
- **处置方向**:「7 个环境」改「8 个环境」;本表同时自纠 r1 发现 7 的同笔误。

#### r2 发现 5 [建议] | design §2.2-1 | best-effort 例外的 except 词表与留证行字段内容未就地标注(引用先例可推,一句标注防微拍板)

- **发现**:「rider 调用包 try/except」未写死捕获范围——裸 except(捕 BaseException)是反模式,项目先例 = `except Exception as e:  # noqa: BLE001`(cw_gain_chain.py:470/:585 登记腿两处,恰是设计自引的「同族先例」);缺陷行字段内容(expected/actual 组合式)先例同样在册。语义选择可从引用先例唯一推出,但未就地标注 = 实现者需自行开先例文件对齐,「实现者无需再设计」差最后一步。
- **证据**:cw_gain_chain.py:470-475/:585-591(先例形态);design §2.2-1。
- **处置方向**:补一句「except Exception(对齐登记腿先例形态),缺陷行 expected='条件腿授予成功' actual=异常摘要,evidence=joy_conditional:<单位名>」。

### 3. 修订新增面无前提再攻(未立发现,留档)

- **rand 全通道 logic_rand 下 §2.5-1 校准面自洽性**:推演成立。授予写 bench(logic_rand 整表快照)→ 下一帧 heavy 观察 → `observe` 对 logic_rand 来源值不等覆盖落 `logic_rand_outcome` 行(cw_game_state.py:2479-2487,行内 expected/actual)→「模型选中单位 vs 实见单位」经整表 diff 判读,候选集两成员使 diff 判读可行(§2.4「判读面自证」)。粒度提示:outcome 行的 expected/actual 是整槽表快照而非单位单值,判读需一步整表 diff;bench 其他槽漂移会混入 diff(既有 rand 通道噪声语义,gs-opening-seed 批已在册申报同型面)——建议判读规约注明,非本批缺陷。§2.6 引用的「零 observe_vs_logic_mismatch」kind 名实存(cw_game_state.py:862 缺省 kind),锚真实。
- **失效通道与 best-effort 的联动方向**:采纳 (a) 后 rider 异常被调用点捕获 → act 节点正常完成 → 不进重试 → 授予异常本身不再构成二次落地触发源;通道触发源收窄为分派腿异常,申报(§2.3)仍然充分且偏保守,方向向好。
- **族面表述**:「逐件建模 vs 统一条件腿框架候族批裁决,禁逐件无声展开」边界句成立;计数修正见 r2 发现 4。
- **`leg_type=''` 直调兜底形态测试**:分派前 rider 已执行,终态兜底 return 不回退授予——判据语义成立(实码 pick_planner.py:79-88 顺序结构核过)。

### 4. 全量同步复查(design ↔ landing ↔ 处置表 ↔ README)

- design↔landing:**失同步两处**——r2 发现 1(3.1 完成判据残留「置闩=logic」旧口径,阻断)、r2 发现 2(正本清单缺 gain-chain.md §6 行);其余(范围/文件面/设计依据/验收凭据)逐项对照一致。
- design↔处置表:11 条处置落点逐条回指修订版,未见虚报;两处处置引入的新瑕疵(r2-3 判据字面/r2-4 计数)单列。
- README:「草案(r1 攻击 11 条处置完毕,候复审)」「设计对抗:进行中」与实际状态一致;r2 后需同步更新进度行。

### 5. 试读重跑(逐阶段「凭这份能开工吗」)

- **3.1**:design 侧全部可执行(失败语义/通道语义/触发边界/退役面/测试面均已写死);唯 landing 完成判据第一行按旧口径立任务即自相矛盾(r2 发现 1)——**该行修定即可开工**。
- **末阶段正本更新**:清单补 gain-chain.md §6 行(r2 发现 2)后与实现面自洽;其余条目落点真实。

### 6. r2 收敛判定

**需单点修订后定稿。** r1 的 11 条处置全部真实落地且方向正确;阻断仅 **r2 发现 1**(landing 3.1 完成判据残留旧通道口径,单行修订)+ 应修 **r2 发现 2**(正本清单补一行);建议 r2 发现 3/4/5 顺手收口(一词限定 + 一数修正 + 一句标注)。修订完成后本迭代设计达定稿门槛,无需第三轮全量复攻(两处修订均为机械同步面,无新语义选择)。

---

## r2 处置记录(单点修订,本节由编排者记)

| 发现 | 处置 | 落点 |
|---|---|---|
| r2-1 landing 判据残留旧口径 | 采纳:第一判据改「未闩=rand/置闩后 rand 授予**仍 = logic_rand**(rand 形参优先于闩)」 | landing 3.1 |
| r2-2 正本清单漏 §6 | 采纳:gain-chain.md 行补「+ §6(条件腿授予调用点级 best-effort 例外申报)」 | landing 正本清单 |
| r2-3 grep 判据字面不可满足 | 采纳:改「全仓(src)…changes/ 历史件与本迭代 attack.md 不在判据域」 | design §2.2-7 |
| r2-4 族面计数 7→8 | 采纳(含 r1 笔误自纠) | design §1 |
| r2-5 except 词表未标注 | 采纳:补 `except Exception`(noqa BLE001,先例锚 = cw_gain_chain.py:470/:585 同款) | design §2.2-1 |
| 留档:outcome 行整槽表快照判读 | 采纳:折入 §2.5-1 判读规约(整表 diff,rand 通道既有噪声语义) | design §2.5-1 |
