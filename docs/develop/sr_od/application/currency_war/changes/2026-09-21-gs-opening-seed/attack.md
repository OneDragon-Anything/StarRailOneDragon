# gs-opening-seed 设计·对抗攻击报告(核一无前提 / 核二规范 / 核三治本)

> 攻击对象:`design.md`(草案态,单文档方案)+ `landing.md` + `README.md`。
> 规范依据 = `docs/develop/harness/iteration-design.md` §1-§5/§7。纸面对实码,证据全部为
> 仓库现状实读;行号核验基线 = HEAD `619c6cf25`(本迭代设计提交),工作区另有在飞改动处
> 单独注明。共 12 条发现(3 阻断 / 6 应修 / 3 建议)。

---

## 1. 符号/锚全量核验结果(先行声明,不计发现)

以下设计引用的锚逐个实读相符,不作为攻击点:

- `cw_game_state.py:2637` `write_logic_rand` 族校验 `_validate_sig(sig, ('logic_action','logic_hook'))` ✓(但见发现 1 的 mode 词表面)。
- 四处写选择 `write = gs.write_logic_rand if rand else gs.write_logic` 在 HEAD 上精确位于 `cw_gain_chain.py:294/:354/:430/:480` ✓;两处未观察发射点(bench :340-351 / equips :470-479)、`DEFECT_BENCH_UNOBSERVED`/`DEFECT_EQUIPS_UNOBSERVED` 常量(:56/:58)、detail 档 `bench_unobserved`/`equips_unobserved`(:351/:479)、两处【待梳理标记】(:341/:472)均 ✓。
- `cw_reconcile.py:434` `tracked_account_observed=True` 锚定写回点(:433-438,`logic_action` 族)✓;`_reconcile_tracking` 仅在 heavy 段调用(`cw_screen_prep.py:228→244`),设计「heavy 锚定」语义与实码一致 ✓。
- `cw_loop.py` 假局守卫(:1134-1161「从未观察到对局态」)、局终 `_observed = node.value is not None`(:1157/:1565)、`_absorb_selected_difficulty`(:908-924,ctx 值在才写)✓;`effective_node_ord` 双空 None(cw_game_state.py:2822-2834)✓ —— node 族 B 类不种的三处安全件依据成立。
- `cw_investments.py:182` `gold_per_plane_start` (6,8,12)、`ENV_GIFTS`(:1547)✓;`cw_economy.py:109` `REFRESH_COST_BASE = 2` ✓;`cw_observation.py:889` `LEVEL_UP_COST_TABLE` 兜底注 ✓;`cw_opening_hp._AFFIX_HP_DELTA`('开局不利': −20)✓。
- `xp` 种子值 (0,4):权威表 `cw_economy.py:51` `XP_TO_NEXT_LEVEL = {3: 4, ...}` ✓;`level`/`deploy_cap` 种子 3 与表、字段注释「= level + 财富宝钻数」(cw_game_state.py:1891/fields.md:323)一致 ✓;读口缺省 1/1/1(:3339/:3345/:3364)✓。
- `currency_war_invest_env.yml` 恰四区(标识-投资环境/区域-卡牌描述行/按钮-确认/区域-剩余次数行)✓,阵容域物理不可观察主张成立。
- `cw_entry_start.py:435` 流程注实为 :436-437(「简报→投资环境→投资策略→备战」),±5 漂移内 ✓;`cw_screen_prep.py::_observe` heavy → `observe_full(tier='heavy')` → `reconcile_tracking` 链 ✓。
- takeover-intel-pipeline design §2.1 触发谓词 `not gs.plane_bosses.value`(design :49;写门同谓词 plane_intel.py:60)✓ —— plane_bosses 不种的接管触发理由成立。
- fields.md 引用条目:§2.2「非当前画面=None」(:67)、§3.2.9 gold「None=不可读」(:365)、§3.2.13 hp 写入闸(:396-401)、§3.2.16 consumables 死字段清偿指针、§3.6.1 event_overlay 双义禁令、§3.4.3 env_refresh_used「当前零写端在册」均在库 ✓;gain-chain.md §6【待梳理标记】(:138)✓;B/C 类字段注释语义档(lv999 :2088-2092「None=未触发任何变换」、top_bar_raw :2108-2112「原文缺读=不写(禁猜)」、consumables 死字段 :1972-1975)✓。
- `test_cw_gain_chain.py`(HEAD)`test_unobserved_zero_write_with_defect` 在库、`_make_gs(None=保持未观察)` 边界腿、`DEFECT_*` 导入(:27-28)——landing 3.2 点名的改写对象存在 ✓;`test_cw_game_state*.py` 三个文件在库,landing 3.1 验收凭据路径有效 ✓。
- BenchView 9 空槽(capacity 9)构造先例在库(cw_game_state.py:3500-3504 `BenchView(slots=[BenchSlot(kind='empty')]*BENCH_CAPACITY_DEFAULT, ...)`,`BENCH_CAPACITY_DEFAULT=9` :138)✓。

---

## 2. 发现清单

### 发现 1 [阻断] | design §2.3/§2.6-4 | 种子调用形态里的 `mode='seed'` 是非法值,`ChannelSig` 构造期即炸,journal「mode='seed' 行可过滤」申报连带失效

- **问题**:§2.3 写法给死 `sig=ChannelSig(family='logic_action', actor='GsOpeningSeed', screen='', mode='seed')`。实码 `LOGIC_MODES = ('compute',)` 封闭(cw_game_state.py:285),`ChannelSig.__post_init__` 对 logic 族 mode 做构造期校验(:350-355),`mode='seed'` 直接 `ValueError`。设计只核了 family 校验面(:2637 ✓)漏了 mode 词表面;§2.3 journal 面「+≈24 行 `mode='seed'` 行(可过滤)」与 §2.6-4 的 journal 增量申报整段建立在这个非法 mode 上。照设计实现 = 写第一笔种子即炸;按停手令回修 = 定稿门槛未过。
- **证据**:`cw_game_state.py:285`(`LOGIC_MODES: tuple[str, ...] = ('compute',)`)、`:340-355`(`__post_init__` mode 词表校验,logic 族合法集 = `('compute',)`)、`:2637`(设计所引的族校验)。
- **处置方向**:二选一写死——(a) `mode='compute'` + 以 `actor='GsOpeningSeed'` 作 journal 过滤键(零词表变更,申报面同步改);(b) 显式扩 `LOGIC_MODES` 加 `'seed'`(牵动 §3.2.1 mode 词表正本、全部 sig 校验语义,需单独申报)。按 (a) 成本最小。

### 发现 2 [阻断] | design §2.2 hp 行/§2.6-6/§2.6-7 | hp 种子与在册开局先验机制正面冲突:种子值 80 无出处,在册实证 82/62,现役先验写端在役,且种子对可信位门消费零增益

- **问题**:①设计引用 `cw_opening_hp._AFFIX_HP_DELTA` 作 −20 依据,但该模块的本体就是开局 hp 实证表:`OPENING_HP_BASE = 82`(109 局零方差)/开局不利 62(fields.md §3.1.6 在册;cw_opening_hp.py:22/:32)——种子 80 与最强在册证据冲突且未作任何对账说明,§2.6-7「更贴真值」对 hp 不成立。②「开局 hp 未知」已有专用通道在役:`reconcile_hp` 开局分支(cw_reconcile.py:494-511)→ `gs.write_prior(gs.hp, evidence='prior:adr-0559')`(cw_observation.py:2626-2632),A8/108 档给 82/62、其余档诚实 None——先验是 readable=False 的不可信档,语义恰是设计想要的「未验证底座」,设计通篇未提。③种子经 rand 写入后 `hp_decision_trusted_of` 只认 observation/carried(cw_hp_policy.py:64,logic_rand 落不可信侧),窗口内决策消费点(经可信位门的 blood_xp_gate cw_economy.py:802 等)行为与今日 None 完全相同——hp 种子在实际消费面上是纯 journal 噪声 + 覆盖 outcome 行,无申报中的收益。
- **证据**:`kernel/cw_opening_hp.py:22-34`(82/62/−20 实证表 + 「兜底假值毒化遥测」的在册反面论证)、`docs/.../game_state/fields.md:165-169`(§3.1.6 在册先验)、`cw_reconcile.py:494-512`、`cw_observation.py:2284-2292/2616-2636`(先验/carry 写端)、`cw_hp_policy.py:48-64`(可信位只认 observation/carried)。
- **处置方向**:hp 移出 A 类(不种),依据引 §3.1.6/cw_opening_hp——「开局 hp 未验证初值已由先验通道按实证档覆盖,种子值反而在无实证档(多数职级)注入假值」;或坚持种子则 (a) 值改 82 并逐档对齐实证表、(b) 显式裁决与 write_prior 两写端的时序与语义、(c) 申报可信位门下零收益的事实。

### 发现 3 [阻断] | design §2.6-3/§2.6-6 | 「种子走 rand,假值防线不破」不成立:失读处置①(carry)的 None 守卫会把 logic_rand 种子洗成可信 `carried`,hp 可实证可达

- **问题**:`carry()` 的守卫是 `if target.value is None: return`(cw_game_state.py:2544),不查来源——种子(logic_rand,未验证)非 None,任何失读帧的 carry 腿都会把种子值原样换帧成 `source='carried'`,而 carried 是**可信位**(hp_decision_trusted 认 carried,cw_hp_policy.py:64;ADR-0448/0495 的 fail-closed 血线谓词只拦 prior/logic)。可达路径:read_game_state 的 hp 失读支——`_hp_opt=None`(shop-open 帧 spec 无 'hp')→ reconcile_hp 非 A8/108 档返 `(None, False)` → `gs.carry(gs.hp)`(cw_observation.py:2633-2636)。接管局在首个 prep_clean 真读前停在 shop-open 相位时,种子 80 被洗成**可信 carried 80**,血成本闸(blood_xp_gate)按可信 80 放行——今日同帧 hp=None carry no-op 保守跳过。行为差异方向 = 把「诚实未知」翻转成「可信假值」,正击穿设计自己援引的 §8.8 假值防线。gold(:2602-2607)/level(:2608-2613)/deploy_cap(:2647-2657)的失读 carry 腿同型。设计全文未分析 carry 交互;§2.6-3 只说「容器保持种子/链写值」、§2.6-6 只说「种子走 rand 非 observe」——都没覆盖洗白路径。
- **证据**:`cw_game_state.py:2539-2550`(carry 守卫只查 value is None)、`cw_observation.py:2284-2292`(spec 无 'hp' → `_hp_opt=None`)、`:2616-2636`(reconcile_hp → 非 A8/108 → carry)、`cw_hp_policy.py:48-64`(carried 可信)、`cw_economy.py:802`(blood_xp_gate 消费可信位)。
- **处置方向**:三选一并写入设计——(a) carry 守卫收窄为「来源非 logic_rand 才沿用」(kernel 单点改动,与 §2.1「三者全部住 kernel」同域);(b) A 类中「不可信即保守」的域(hp,及 gold/level/deploy_cap 中有可信位消费的)不种或降级;(c) 显式接受洗白并申报(与 fail-closed 在册纪律正面冲突,不建议)。

### 发现 4 [应修] | design §2.2 | 分诊表自称「容器 Field 全集三类」,实有四个 Field 未进任何类;`tracked_account_observed` 是 Field 却被列进「非 Field 簿记」

- **问题**:容器 Field 全量 72 个(代码 `: Field[` 计),A/B/C 三表并集缺 `hp_floor_triggered`(:2096)、`prev_screen`(:2105)、`current_screen`(:2106)、`receipts`(:2130)——实现者无从得知这四个种不种。另「不适用(非 Field 簿记)」清单收入 `tracked_account_observed`,实码它是 Field(:1882 `Field[bool]`);它确实不该种(None=缺省可信,种 False 即拆商店门、种 True 即假锚定,`tracked_unobserved` cw_game_state.py:1693-1701),但归置层错 + 缺 B 类依据句。
- **证据**:全量 `: Field[` 枚举 vs design §2.2 三表 + 不适用清单;`cw_game_state.py:1882/:2096/:2105/:2106/:2130`。
- **处置方向**:四字段补分诊(按设计自身判据:hp_floor_triggered 事件位/上下文对/receipts 回执域均落 B 并给一句依据);`tracked_account_observed` 移入 B 类并补「None=缺省可信,种即拆安全网」依据。

### 发现 5 [应修] | design §2.5/§2.8 + landing 3.2 | 「四处写选择」盘点已被在飞迭代失真(4→5 处),「锚定前 logic_action 写端 census」不完整且与设计自己的 §2.2 矛盾

- **问题**:①HEAD 上四处锚精确成立,但工作区在飞迭代 `2026-09-21-invest-landing-chain`(未提交,+116/−4)已给 `cw_gain_chain.py` 加第 5 处写选择(:313/:373/:449/:499/:552,新增 `gain_invest_strategy`)并新建 `cw_gain_effects.py`——§2.8 相邻批申报只列 tool-gain-report 与队列①,未列该在飞批的文件冲突面;landing 3.2「四处写选择全部改经收口」按现状执行即漏第 5 处。②§2.5 census「现役锚定前可达的 logic_action 写端 = 获得链 + `_absorb_selected_difficulty`」不完整:`briefing.py:52-63`(enemy_affixes/plane_bosses/enemy_difficulty 三写点,`family='logic_action'`)与 `plane_intel.py:25/:60-67`(两写点)都在锚定前可达——它们不收口是安全的(目标域无 observe 写端),但 census 作为封闭清单陈述失实,且与 §2.2 enemy_affixes 行自引「简报即覆写」的同一写端直接矛盾。
- **证据**:`git show HEAD` vs 工作区 `Select-String 'write = gs.write_logic_rand if rand'`(4 处 :294/:354/:430/:480 → 5 处 :313/:373/:449/:499/:552);`git status`(cw_gain_chain.py M、cw_gain_effects.py ??、changes/2026-09-21-invest-landing-chain/ ??);`cw_screen_report/briefing.py:50-63`、`cw_screen_report/plane_intel.py:23-26/:60-67`(均 `family='logic_action'`)。
- **处置方向**:§2.8 补 invest-landing-chain 关系申报(文件冲突面 = cw_gain_chain.py/test_cw_gain_chain.py,landing 3.2 的「四处」改为「全部写选择点(落地时 grep 计数)」);census 改为穷举式清单(获得链全部原语 + `_absorb_selected_difficulty` + briefing/plane_intel 写门,并逐个写明「不收口理由」),与 landing 3.1 的 grep 核查项对齐。

### 发现 6 [应修] | design §2.2 A 表 | 种子值与仓内 sim 开局模型(`cw_sim_opening.apply_opening`)三处冲突未裁决:gold 0 vs 3、bench 空 vs U28 定案开局手牌 4 张、hp 80 vs 查表 82/62

- **问题**:sim 引擎的开局合成是仓内对「开局容器真值」最完整的建模,设计一处未引:①`OPENING_GOLD = 3`(cw_sim_opening.py:52,M01 开局状态域)vs 设计 gold=0;②开局手牌**在容器建立时已在席**——`OPENING_HAND_SIZE = 4`、双费用形状 2:1(U28 定案,:41-46/:96-110),`apply_opening` 把 4 张 1★ 落 bench(:124-143)vs 设计 bench 空 9 槽;§2.2 bench 行「开局手牌发放时点候实机核实」的问题在仓内已有建模答案,设计既不引用也不反驳。③hp 82/62 查表(:62-77)vs 80(发现 2)。若 sim 模型方向正确,「合成池 = 种子空底座 → 少报」(§2.6-1)被系统性放大:窗口内合成推演永远漏掉整个开局手牌;若 sim 是占位口径,设计应写明「sim 开局模型未对实机核、种子取用户裁定值」的显式取舍——现在是两头都没说。
- **证据**:`sim/cw_sim_opening.py:41-54`(:41 HAND_SIZE=4、:46 形状 2:1、:52 GOLD=3、:53 LEVEL=3、:54 DEPLOY_CAP=3)、`:113-143`(apply_opening 写入集)、design §2.2 bench/gold 行(无 sim 引用)。
- **处置方向**:bench/gold/hp 三行补对 sim 开局模型的就地裁决——逐值引用 `cw_sim_opening.py` 常量,采纳或反驳(反驳需给出比 M01/U28 定案更强的依据);bench 若维持空种子,§2.6-1 的「少报」申报按 4 张手牌缺口重写定量口径。

### 发现 7 [应修] | design §2.7/§2.6-4 | 「观察覆盖静默/零失配行」判据与机制不符:种子值≠真值的字段首观察必落 `logic_rand_outcome` 台账行,这是机制内行为而非缺陷

- **问题**:observe() 对 `source='logic_rand'` 且值不等的覆盖**必落一行**(cw_game_state.py:2355-2363,`_emit_defect(kind='logic_rand_outcome')`,「无告警无停机」但**是台账行**)。§2.7 判据「对种子字段 `observe()` 不产生失配缺陷行」按字面实现(断言零 defect 行)对开局手牌非空/词缀非空/hp 偏差等一切种子≠真值字段必假失败。§2.6-4 行为变化申报只计 +≈24 种子行,漏了首观察覆盖种子值差部分的 outcome 行面(每局 ≈ 种子不命中字段数),也未申报这些行落入 `write_logic_rand` docstring 定位的「随机模型校准遥测面」(:2623-2625)的噪声语义。
- **证据**:`cw_game_state.py:2350-2363`(logic_rand 覆盖差 → `logic_rand_outcome` 行)、`:2609-2628`(rand 通道语义与校准面)。
- **处置方向**:§2.7 判据改为「不进失配三分流(零 mismatch 三分流行),差异仅落 `logic_rand_outcome` 台账行」;§2.6 补一条 outcome 行增量申报(量级 ≈ 种子不命中字段数/局)及其对随机校准遥测面的噪声判读提示。

### 发现 8 [应修] | design §2.5/§2.7 + landing 3.2 | 直构容器上 `rand=False` 链写被闩全局改道,测试域「如何建立已锚定前提」未定义 = 实现者再设计点

- **问题**:`_select_write(gs, rand)` 按 `prep_anchored_of(gs)` 判道;直构 `GameState()`(sim/测试/草稿视图)恒 `prep_anchored=False` → **rand=False 的链写也全部走 logic_rand**。HEAD 测试 `test_rand_passthrough_and_flip` 锁「rand=True→logic_rand / rand=False→logic」双臂;landing 3.2 只申报「未观察用例改写为种子路径断言」,未申报 rand 透传用例的改写,也没定义测试/直构容器把闩置为 True 的手段(直接赋值簿记位?经 reconcile?)。「锚定后 rand=False 链写走 logic」(§2.7)在直构容器上按现文不可达。sim 现不消费链(grep 零命中)故引擎域今日无碰撞,但队列①迁链后同题即现。
- **证据**:`cw_gain_chain.py` 四处写选择持直构容器即被改道;`sr-od-test/.../test_cw_gain_chain.py`(HEAD)`test_rand_passthrough_and_flip`;design §2.7/landing 3.2 范围句无对应申报。
- **处置方向**:写死测试域契约——(a) 测试直构容器以何种语句置闩(如 `gs.prep_anchored = True` 直赋,并声明其为测试专口);(b) landing 3.2 范围补「rand 透传用例双臂改写:直构(未闩)断言 logic_rand / 置闩后断言 logic」;(c) §2.5 补一句「直构容器视同未锚定」的显式语义。

### 发现 9 [应修] | design §2.3/§2.4 | `game_state_of` 无「各新建分支汇合处」,None 一次性支的种子行为未定义(测试在依赖它);直构边界枚举漏两处

- **问题**:实码三个新建分支各自独立构造——None 一次性支(:1673,不缓存不装配)、不可弱引用支(:1676-1685)、弱引用支(:1686-1689),无汇合点;「与遥测装配同边界」类比可推出 None 支不种(`_establish_singleton_journal` 只挂后两支),但设计没明说,而「各新建分支汇合处」的字面实现(在 None 支也调 `seed_opening_state`)会种到测试容器——`test_cw_board_derived_and_reorder.py` 经 `game_state_of(None)` 取容器 10+ 处,依赖未写字段,与 §2.3「sim/测试域的 None 分支继续存活」的自我申报冲突。另直构边界枚举(planner/invest_strategy 防御视图、env_economy 探针)漏 `cw_screen_yinlang.py:245` 与 `scalar_projection_state`(cw_game_state.py:3485)两个直构点。
- **证据**:`cw_game_state.py:1670-1690`(三建支形态)、`:1622-1640`(装配只挂缓存单例支)、`sr-od-test/.../test_cw_board_derived_and_reorder.py`(game_state_of(None) 多处)、`cw_screen_yinlang.py:245`。
- **处置方向**:挂点写死为「两个缓存单例建支、与 `_establish_singleton_journal` 同点;`session=None` 一次性支不种」;边界枚举补齐两个漏名直构点(或改为按「不经 `game_state_of` 缓存单例支」的规则式表述)。

### 发现 10 [建议] | design §1/§2.2 | 依据锚失真/不可复现集(三处)

- **问题**:①`shop_refresh_cost` 行「现消费 `value or REFRESH_COST_BASE`」——实码已改 `int(_v) if _v is not None else SHOP_REFRESH_COST`(cw_economy.py:660-663,docstring 明言「原 `or 2` falsy 兜底形态的**消灭形态**」);等价结论碰巧仍成立(种子 2 = 缺省 2),但依据引的是已删除的形态。②§1「全仓 Python 154 处『未观察/unobserved』消费点」不可复现:src 全量行命中 195、含测试仓 329,「消费点」无计数口径;方向性成立,数字无据。③`env_refresh_used`「禁按字段值做决策」在册句与 `round_fresh_buys`「None = 本局未登记」字段注释句,在字段注释(:1938/:1948-1953)与 fields.md §3.4.3/§6.5 相应位置检索均未见原句——引用位至少有一处标错。
- **证据**:`cw_economy.py:653-663`;`grep 未观察|unobserved`(src 195 / src+test 329);`cw_game_state.py:1938/:1948-1953`、fields.md §3.4.3(:720-733)。
- **处置方向**:①依据改指现役 `is not None` 形态(结论不变);②数字补 grep 口径或去数字化;③两条引用落到真实在册位置或改写为语义描述。

### 发现 11 [建议] | design §2.2/§2.3 | front_row/back_row 种子经 `_write_logic_frame` 自动触发 board 派生写,与显式 board 种子重复落行;≈24 行申报未含派生行

- **问题**:行域写必触发 `_resync_board_delta`(cw_game_state.py:2655-2663/:2506-2508),种子写 front_row/back_row(空行)各自动落一条 `evidence='proj_board_resync'` 的 board 派生行(rand),随后 §2.2 又显式种 board——board 双写、journal 实落 ≈26-27 行 vs 申报 ≈24;写序(行域先/board 后)设计未定。
- **证据**:`cw_game_state.py:2642-2663`(_write_logic_frame 行域挂钩)、`:2454-2508`(派生写)。
- **处置方向**:设计写明种子写序与派生行预期;或 board 不单独种(由行域种子派生承担),A 表 board 行改注「经行域种子派生,不直接写」。

### 发现 12 [建议] | landing 3.1/3.2 | 「通用工程门」复述而非引用,且模板所指「§12 通用工程门」在 iteration-design.md 无对应节

- **问题**:landing 两阶段完成判据把工程门展开为「ruff check + pytest 全绿」具体命令——模板(iteration-design.md 附录 C/§3.1)要求「§12 通用工程门(引用,不复述)」;而 iteration-design.md 正文止于 §7,「§12」本身是悬空引用。落地批照 landing 执行没问题,但判据的规范出处链断了。
- **证据**:`docs/develop/harness/iteration-design.md`(全文无 §12)、landing.md:24/:43-45。
- **处置方向**:工程门引用落到真实存在的规范条目(如 sr-od-test/README.md「提交」节或任务书规范的对应节),或在本迭代 landing 内自定义并注明来源。

---

## 3. 已查证为协调的点(攻击过、不成立,留档防复议)

- **active_strategies 种子的消费等价**:全部消费点 `or []`/`or ()`/falsy 形态(cw_economy.py:303/:638-639、cw_comps.py:1611、cw_investments.py:979、cw_intention.py:422/1218、statefn/interest、predicates)——`[]` 与 None 行为逐点等价;`cw_observation.py:2499` 值也 `or []`。种子不引入消费差。
- **relay 阻塞疑虑排除**:四处 `gs.relay`(cw_observation.py:2720-2724)的入值全部取自容器自身(active_strategies_val/active_env_val/plane_bosses_val/enemy_affixes_val = `gs.*.value or 空`,:2489-2500)——自环写法今日即在「空值拒写(:2684-2687)/已有值跳过(:2682)」双门下恒 no-op,种子不改其行为(active_env 消费点也全部 `or ''`/truthy 形,与种子 '' 等价)。
- **`transform_equip_to_privilege` None 面**:种子后 `inv is None` 分支死了,`source_name not in []` 同返 None(cw_effect_inventory.py:1084-1086)——行为等价,§2.8「无涉」申报成立;骇客腿(pick_invest.py:139-147)由「equips 未观察跳写」变「落账」,方向与 §2.6-1 申报一致。
- **B 类不种的安全件面**:假局守卫/effect 账本闸/node 首锚定门全部只依赖 node 族 None(node 不种)✓;plane_bosses 种 `[None]*3` 真值化拆接管实采的谓词论证成立(plane_intel.py:60)。
- **失配路由机制**:种子+链写(logic_rand)被首观察覆盖只落 `logic_rand_outcome` 行、不进三分流(observe :2355-2363)——「锚定前零安灯」机制成立(判据措辞问题归发现 7)。
- **`_absorb_selected_difficulty` 与 C 类一致性**:absorb 仅 `ctx.cw_selected_difficulty` 在场才写(cw_loop.py:913),接管局该值不出现——§2.5「不受影响」与 §2.5 把它列为锚定前写端两说自洽。

## 4. 试读结论(逐阶段「凭这份能开工吗」)

- **3.1 种子底座 + 锚定闩**:**不可开工**——发现 1(调用形态构造即炸)、发现 2/3/6(hp 值与通道、carry 洗白、sim 模型三值冲突未裁决)、发现 4(四字段未分诊)、发现 9(None 支行为未定)。
- **3.2 链接线 + kind 退役**:方向可读,**未裁决前不可定稿**——发现 5(盘点基数 4→5 与 census)、发现 7(判据措辞必产假失败测试)、发现 8(rand 透传用例与测试置闩手段)。
- **末阶段正本更新**:清单结构合规;消费以上两阶段定稿。

## 5. 总结论

**需修订后复审。** 计数:阻断 3(发现 1 调用形态非法 / 发现 2 hp 与在册先验冲突 / 发现 3 carry 洗白破 fail-closed)、应修 6(发现 4-9)、建议 3(发现 10-12)。
核心修正责任:①种子写通道的 mode 与 journal 申报(发现 1);②hp 域整体重裁——移出 A 类或值/通道/两写端时序重定(发现 2/3,一体裁决);③种子值对仓内 sim 开局模型与在飞 invest-landing-chain 盘点的对账(发现 5/6)。其余各条随修订顺手收口。核三:§1「表示层」归层对 A 类域成立、三件套是统一底座而非逐件补丁,治本方向成立;但 rand 通道「策略消费前必须重观察」纪律(Field 注释在册)与种子「供未锚定期直接消费」的语义例外需在正本申报面(fields.md 新小节)显式立据。

---

## r1 处置记录(修订 = design/landing/README 全量改写,本节由编排者记)

| 发现 | 处置 | 落点 |
|---|---|---|
| 1 mode='seed' 非法 | 采纳 (a):mode='compute',journal 过滤键改 `actor='GsOpeningSeed'` | design §2.3/§2.6-4、landing 3.1 |
| 2 hp 与在册先验冲突 | 部分采纳:**hp 留 A 类,值改 82**(用户裁定 2026-09-21,取 `OPENING_HP_BASE` 实证基线;实证域 A8/108、其余档候采集如实申报);三写端时序固定(种子→先验→真读);可信位零增益如实申报。不采纳移出——用户明示 hp=82 | design §2.2 hp 行/§2.6-6、landing 正本清单(§3.1.6) |
| 3 carry 洗白 | 采纳 (a):carry 守卫收窄「来源 logic_rand 不沿用」入方案第四件;hp 主风险面随裁定值与收窄双重收敛;存量影响面申报(现役 rand 写域与 carry 腿不相交,零回归) | design §2.1/§2.5 末条/§2.6-3、landing 3.1 |
| 4 四字段缺分诊 + tracked 误列 | 采纳:四字段入 B(逐条依据);tracked_account_observed 移 B 类并补「种即拆安全网」依据 | design §2.2 |
| 5 写选择 4→5 + census 失实 | 采纳:§2.8 补 invest-landing-chain 冲突面申报;landing 3.2 改「全部写选择点(落地时 grep 计数)」;census 改穷举清单表(briefing/plane_intel 不收口理由逐条) | design §2.5/§2.8、landing 3.2 |
| 6 sim 开局模型三值冲突 | 用户裁决(2026-09-21):gold=3(对齐 M01)、hp=82(对齐实证表)、**bench 空 = 建立时点真值**(用户游戏知识:开局无手牌,1-1 经「开局补给」赠送,细目候实机观察;sim 手牌写点 = 引擎起点 1-1,不同时点无冲突);§2.6-1 少报申报按此时点重写 | design §0 裁定③④/§2.2 bench·gold·hp 行/§2.6-1 |
| 7 零失配行判据失准 | 采纳:判据改「不进失配三分流,差异落 logic_rand_outcome 行」;§2.6-4 补 outcome 行增量与校准面噪声判读提示 | design §2.6-4/§2.7 |
| 8 测试置闩未定义 | 采纳:§2.4 写死专口(直赋 `gs.prep_anchored = True`,测试/直构域专用)+ 直构视同未锚定;landing 3.2 补 rand 透传双臂改写 | design §2.4/§2.7、landing 3.2 |
| 9 None 支未定义 + 直构漏两处 | 采纳:挂点写死两缓存单例建支(None 支不种);直构边界改规则式表述并补银狼屏/scalar_projection | design §2.3 |
| 10 锚失真三处 | 采纳:shop_refresh_cost 依据改现役 `is not None` 形态;「154 处」去数字化;两句引用改语义描述 | design §1/§2.2 |
| 11 board 派生双写 | 采纳 (b):board 不直接种,由行域种子派生承担;写序与派生行申报 | design §2.2/§2.3 |
| 12 工程门悬空 | 采纳:引用落 `sr-od-test/README.md`「提交」节 | landing 3.1/3.2 |
| 核三尾巴(rand 语义例外立据) | 采纳:design §2.6-8 立据义务 + 正本清单 fields.md 新小节 | design §2.6-8、landing 正本清单 |

---

## r2 复攻记录(修订版 = a8254f4b9;锚核验基线上移至 HEAD `0358aa60a`)

> 复攻范围:①12+1 条处置逐条对照修订版核真伪;②修订新增面无前提再攻(carry 收窄 /
> hp 三写端 / 开局补给标注 / journal 过滤键);③试读重跑;④全量同步复查。
> 结论只看证据;所有证据为当前仓库实读(HEAD `0358aa60a`,含 invest-landing-chain
> 主落地提交)。共 4 条新发现(1 阻断 / 1 应修 / 2 建议)。

### 1. r1 处置逐条核验结果

| 发现 | 处置核验 |
|---|---|
| 1 mode='seed' 非法 | ✓ 落对。`mode='compute'` 合法(`LOGIC_MODES=('compute',)`);journal 行实测携带 `'sig': sig.to_json()`(cw_game_state.py:2230),`actor='GsOpeningSeed'` 过滤键可落——design §2.3/§2.6-4/landing 3.1 三处口径一致 |
| 2 hp 与先验冲突 | ✓ 落对。值 82 = `OPENING_HP_BASE`(cw_opening_hp.py:22)逐字对齐;实证域/其余档候采集/可信位零增益均如实申报(design §2.2 hp 行/§2.6-6)。三写端时序沿实码推演**可实现**:`write_prior` 为无条件换帧(:2553-2563,仅 evidence 前缀 + sig 校验,无值/来源守卫)→ 先验腿覆写种子静默无行(source 翻 prior);真读覆 prior 亦静默(observe 三分流只辖 logic/logic_rand)——全链零安灯 ✓ |
| 3 carry 洗白 | ✓ 机制落对(§2.5 末条收窄语义正确:rand 来源非「上次好值」);**✗ 影响面申报错,见 r2 发现 2** |
| 4 四字段 + tracked | ✓ 落对。四字段入 B(:108)依据成立;`tracked_account_observed` 移 B(:110)并给「种即拆安全网」依据;不适用清单已剔除(:122-125) |
| 5 写选择 4→5 + census | ✓ 落对。§2.8 补 invest-landing-chain 冲突面;census 穷举表四组(briefing 三写点/plane_intel 两写门/_absorb)与实码逐一相符且不收口理由成立。小尾巴见 r2 发现 3 |
| 6 sim 三值冲突 | ✓ 落对(用户裁决三值入 §0/A 表)。补充核验:「开局补给」机制在仓**三重在册**——`docs/game/currency_war/research/screen_flow_timing.md:70`(「触发开局补给(给开局角色 + 晶矿)」,时点 = 投资屏选完进 1-1)、sim-redesign design.md:474(「开局手牌来自开局补给独立发牌通道,不走商店」,u07u28 报告)、`screens/wait_one_one.md`(专门等待该动画的 op)——设计只引「用户游戏知识」弱源,见 r2 发现 4 |
| 7 零失配判据 | ✓ 落对(§2.7 改「不进三分流 + outcome 行断言其存在」;§2.6-4 补增量与校准面判读) |
| 8 测试置闩 | ✓ 落对(§2.4 专口直赋 + §2.7/landing 3.2 双臂改写) |
| 9 None 支 + 直构边界 | ✓ 落对(挂点写死两缓存单例支;边界规则式 + 补银狼屏/scalar_projection) |
| 10 锚失真 | ✓ 落(shop_refresh_cost 改现役 `is not None` 形态 ✓;「154 处」去数字化 ✓)。**半条撤回**:round_fresh_buys「None=本局未登记」经复核是字段注释原文(cw_game_state.py:1947),r1 该子项判错,修订版保留引用正确 |
| 11 board 双写 | ✓ 落对(A 表 board「不直接写」走行域派生;≈23+1 与 A 表 23 字段数一致) |
| 12 工程门 | ✓ 落对(引 sr-od-test/README「提交」节) |
| 核三尾巴 | ✓ 落对(§2.6-8 立据 + 正本清单 fields.md 新小节) |

### 2. r2 新发现

#### r2 发现 1 [阻断] | design §2.2 A 表/C 表/§2.8 | 引用已退役字段名:`strategy_refresh_used`/`env_refresh_used` 在锚核验基线 HEAD 已改名退役,且 `strategy_refresh_left` 的 A/C 归类需按新语义重裁

- **发现**:修订版设计提交(a8254f4b9)之后,invest-landing-chain 主落地(`0358aa60a`)把 `env_refresh_used→env_refresh_left`、`strategy_refresh_used→strategy_refresh_left` 改名退役(cw_game_state.py:1939-1940,注释明言「原…改名退役」)。修订版 §2.2 A 表行「`encounter_refresh_used`/`supply_refresh_used`/`strategy_refresh_used` = 0/0/{}」与 C 表行 `env_refresh_used` 各引一个已退役名字(前两者仍在库 :1937-1938 ✓)。3.1 实现者按 A 表直写 `gs.strategy_refresh_used` 即 AttributeError。更深一层:改名不是纯换名——`strategy_refresh_left` 语义变为**剩余次数**且已接观察写端(report_screen_invest_strategy_obs 摄入,读缺键跳写),`{}` 种子值语义(未读?无卡?基线尽?)与旧 `_used` 的「未刷新过」不等价;`env_refresh_left` 同样已接观察写端且「零写端」旧 C 依据失效。归类与种子值都是开放语义选择 = 定稿门槛未过。§2.8 冲突面申报(只列 cw_gain_chain.py/test)漏 `cw_game_state.py`——恰是 3.1 文件面,且改名就落在它上面。
- **证据**:`git show HEAD:.../cw_game_state.py`(:1939-1940 `_left` 两行 + 改名退役注释;:1937-1938 `_used` 两名仍在)、`git log`(a8254f4b9 < 0358aa60a)、design §2.2(:94/:120)/§2.8(:235-238)。
- **处置方向**:A/C 两行按 HEAD 字段名重写——`strategy_refresh_left` 重裁归类(有观察写端 + 剩余语义,种子 `{}` 是否「开局真值」取决于消费口径「剩余 ≤0 = 尽」对空 dict 的读法,需就地给依据)或移 C;`env_refresh_left` 同步;§2.8 冲突面补 `cw_game_state.py`(并注明 0358aa60a 已落,本批 3.1 在其上续作)。

#### r2 发现 2 [应修] | design §2.5 末条(carry 收窄) | 存量影响面申报不成立:carry 腿实为 8 条非 4 条,board 交点使「零存量回归」为假

- **发现**:收窄申报称「gold/level/hp/enemy_difficulty 四条 carry 腿的目标域现无 logic_rand 写端……零存量回归」。实码 carry 腿共 **8 条**(cw_observation.py:2606 gold/:2612 level/:2634 hp/:2642 enemy_difficulty/:2657 deploy_cap/:2659 streak/**:2665 board**/:2706 shop_refresh_cost);其中 **board 的目标域现役就有 logic_rand 写端**——行域 rand 写(`write_logic_rand if rand`,cw_game_state.py:2506 派生挂钩)及 gain 链/骇客标记(在飞批扩员后 bench/front_row/back_row/equips 均有 rand 直写点)触发 `_resync_board_delta` 以 rand 落 board。今日:rand 派生 board + board 失读帧(:2661-2665 `_board_honest` 假支)→ carry 洗成 carried;收窄后 → 保持 logic_rand。行为变化真实存在(源标签 + 后续 observe 的 outcome 行差异),「零存量回归」对 board 不成立。其余七腿目标域经矩阵核(现役 rand 写域 = bench/行域/equips/spheres/board 派生 + pick_supply/pick_planner/tool_use 翻来源,无一属其余七腿)确无交点 ✓——方向正确,申报矩阵需重列。
- **证据**:carry 腿全量 8 处(上行号);board rand 派生(cw_game_state.py:2506-2508);rand 直写域清单(pick_planner.py:98/:189、pick_supply.py:80/:105、tool_use.py:233/:284、cw_gain_effects.py:137、collect_ore.py:108、cw_gain_chain.py:631)。
- **处置方向**:§2.5 影响面句改为穷举矩阵表述——「carry 腿 8 条;rand 写域 ∩ carry 目标域 = {board}(行域派生),该域收窄后失读帧不再洗白 = 存量语义修正(申报,与 §2.6-3 合并);其余七腿零交点」。随附小尾巴:hp None 档(非实证档)经收窄后容器保持种子 rand 态(「诚实 None」在容器面不再可达),§2.2 hp 行括注「或诚实 None」宜补此容器面口径,免实现者误以为要写 None。

#### r2 发现 3 [建议] | design §2.5 census 表 | 「穷举清单」表头字面与在飞批新增的 always-rand 直写点不符

- **发现**:census 表头称「锚定前 logic_action 写端穷举清单」,表内只列「需形态收口的写选择点 + 不收口的 logic 直写点」;在飞批新增的 **always-rand 直写点**(pick_supply/pick_planner/tool_use/collect_ore/pick_equip 等 5 文件 7+ 处,均 logic_action 族)未列——它们天然合规(本就走 rand 通道,规则不辖),但按表头字面属漏穷举,读者无法区分「列全了」与「只列了需裁决的」。
- **证据**:`grep write_logic_rand`(非 sim 域)命中 pick_supply.py:80/:105、pick_planner.py:98/:189、tool_use.py:233/:284、collect_ore.py:108、cw_gain_effects.py:137——均直 rand 形态,不经 `write = … if rand else …` 选择点。
- **处置方向**:表头改「需按通道规则裁决的写端」或补一行「always-rand 直写点(清单)天然合规,不在收口辖域」。

#### r2 发现 4 [建议] | design §0 裁定④/§2.2 bench 行 | 「开局补给」依据可升格:机制在仓三重在册,弱源引用浪费了强证据

- **发现**:bench 行依据只标「用户游戏知识(裁定④)……细目候实机观察」;实仓已有三处独立在册:①`screen_flow_timing.md:70`(实测档:投资屏选完进 1-1 **触发开局补给,给开局角色 + 晶矿**);②sim-redesign design.md:474(u07u28 报告:开局手牌来自「开局补给」独立发牌通道,不走商店);③`screens/wait_one_one.md`(专门等待该动画的 op,含「1-1 不自动开商店」佐证)。三处与裁定④完全同向,且①还给出了种子时点自洽的额外事实:补给含**晶矿**(spheres 行「开局真值」在建立时点成立、1-1 到达经观察覆盖,链路闭合)。设计不引强源 = 依据标注未用最强在册证据。
- **证据**:上行号三处;design §2.2 bench/spheres 行。
- **处置方向**:bench 行依据补引 screen_flow_timing.md #5 + sim-redesign §u07u28(裁定④保留为裁决指针);spheres 行补一句「补给含晶矿(screen_flow_timing #5),1-1 观察覆盖」。

### 3. 全量同步复查(design ↔ landing ↔ attack 处置表 ↔ README)

- design↔landing:3.1 范围覆盖 mode/comput+actor 键/两建支接线/prep_anchored+专口/carry 收窄/census 核对 ✓;3.2 覆盖 grep 计数收口/双臂改写/§2.8 次序协调 ✓;正本更新清单含 §2.6-8 例外立据、fields.md §2.2 carry 收窄行、§3.1.6 hp 三写端 ✓——r1 新增面全部有着落。
- design↔attack 处置表:12+1 条处置落点逐条回指修订版,未见虚报(半条措辞出 入见上表「发现 10」)。
- README:进度行「草案(r1 攻击 12 条处置完毕,候复审)/设计对抗:进行中」与实际状态一致;r2 后需同步更新。
- **失同步一处**:即 r2 发现 1(设计 A/C 表字段名落后于 HEAD 0358aa60a 的 cw_game_state.py 改名)——这是当前唯一 design↔实码失同步点。

### 4. 试读重跑(逐阶段「凭这份能开工吗」)

- **3.1**:r1 阻断面(mode/hp/carry/分诊/None 支/board)全部解除;**唯 r2 发现 1**——A 表 `strategy_refresh_used` 按现 HEAD 不可实现(AttributeError + 归类待裁)。该行修定即可开工。
- **3.2**:rand 双臂/置闩专口/grep 计数/census 均已闭环——**可开工**(依赖 3.1 定稿)。
- **末阶段正本更新**:清单与新增面(§2.6-8/carry/§3.1.6)对齐,随两阶段定稿自洽。

### 5. r2 收敛判定

**需单点修订后定稿。** r1 的 12+1 条处置全部真实落地且落向正确(其中发现 10 半条由 r2 撤回);修订新增面(carry 收窄机制、hp 三写端时序、journal 过滤键、开局补给时点)经实码推演全部成立,唯两处申报面失准。阻断仅 **r2 发现 1**(退役字段名 + 归类重裁 + §2.8 冲突面补 cw_game_state.py)——单点修订;应修 r2 发现 2(carry 影响面矩阵重列)随改;r2 发现 3/4 建议顺手收口。修定后本迭代设计达定稿门槛。

---

## r2 处置记录(单点修订,本节由编排者记)

| 发现 | 处置 | 落点 |
|---|---|---|
| r2-1 退役字段名 + 归类重裁 + 冲突面漏 cw_game_state.py | 采纳:`strategy_refresh_left` 入 A({} = 开局无持卡真值,观察写端读缺键跳写 = 键粒度增量协同);`env_refresh_left` 移 B(剩余语义化已接观察写端,开局基线无在册出处,种猜测值 = 决策面虚构,现场 OCR 自足);`encounter_refresh_used`/`supply_refresh_used` 两名仍在库,0 种子保留;§2.8 冲突面补 `cw_game_state.py` 并注明主落地 0358aa60a 已入库、本批 3.1 在其上续作 | design §2.2 A/C 表/§2.8、landing 3.1 依赖 |
| r2-2 carry 影响面申报错 | 采纳:改 8 腿穷举矩阵(rand 写域 ∩ carry 目标域 = {board} 行域派生 → board 收窄 = 存量语义修正与 §2.6-3 合并;其余七腿零交点);hp 行括注补容器面口径(非实证档先验返 None → 先验腿跳过,容器保持种子随机态至真读) | design §2.5 末条/§2.2 hp 行 |
| r2-3 census 表头字面漏 always-rand | 采纳:表头改「需按通道规则裁决的写端」+ 补 always-rand 直写点行(天然合规,列名备查) | design §2.5 |
| r2-4 开局补给弱源 | 采纳:bench 行依据补三重在册强源(screen_flow_timing.md:70 / sim-redesign design.md:474 / wait_one_one.md);spheres 行补晶矿时点句 | design §2.2 |
